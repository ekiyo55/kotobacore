"""Lattice + Viterbi tokenizer (v0.2).

Replaces the 5-pass repair cascade (merge_keep_as_unit →
split_hiragana_tokens → heuristic_proper_noun_merge →
merge_okurigana_compounds → refine_verb_adjective_pos) with a single
dynamic-programming search: candidate token spans ("nodes") are proposed
from several knowledge sources, and the cheapest full segmentation of the
text is selected by Viterbi. Because disambiguation is global, there are no
pass-ordering bugs — a node either wins on cost or it doesn't.

Node sources (all knowledge reused from the cascade's building blocks):

1. Dictionary surfaces  — keep_as_unit + emotion/slang/entity(+alias)
2. Grammar morphemes    — particles / auxiliaries / サ変 forms
3. Verb & adjective     — KANJI stem + okurigana conjugation (走る/美味しい)
4. 交ぜ書き compounds    — KANJI+kana+KANJI(+okurigana) (締め切り/真っ白)
5. Adjective hiragana   — pure-hira conjugations with an い-base lemma
6. Char-category runs   — Karuizawa-style fallback (always available)

Costs are hand-tuned unigram costs (no training data needed):
``cost = CLASS_BASE − CLASS_RATE × len(span)`` — longer, better-informed
nodes win. Sources 1–5 carry POS and dictionary_form directly, so the
downstream semantic layer works unchanged.
"""

from __future__ import annotations

from kotobacore.dictionary import DictionaryBundle
from kotobacore.matching import SurfaceMatcher
from kotobacore.schema import Token
from kotobacore.tokenizer.karuizawa_backend import _char_cat
from kotobacore.tokenizer.token_normalizer import (
    _ADJ_STEMS,
    _GRAMMAR_TAIL_MORPHEMES,
    _PARTICLES_1,
    _PARTICLES_2,
    _SURU_FORMS,
    _TRAILING_OKURIGANA,
    _TRAILING_OKURIGANA_2,
    _adjective_lemma,
    _build_known_hiragana,
    _classify_okurigana,
    _is_all_hiragana,
)

_MERGED_POS = "感動詞-SNS表現"

# --------------------------------------------------------------------------
# Node costs: cost = BASE − RATE × len. Lower total cost wins.
# --------------------------------------------------------------------------
_COST_KAU = (0.0, 30.0)        # keep_as_unit — near-absolute priority (cascade parity)
_COST_DICT = (3.0, 3.0)        # other dictionary surface — mild bonus only
_COST_VERB_ADJ = (4.0, 6.0)    # assembled verb / adjective
_COST_COMPOUND = (6.0, 5.0)    # 交ぜ書き compound noun
_COST_HIRA_ADJ = (5.0, 4.0)    # pure-hira adjective conjugation
_COST_KNOWN_HIRA = (3.0, 3.0)  # known hiragana word (pronoun/adverb…)
_COST_GRAMMAR = (3.0, 2.0)     # particle / auxiliary
_COST_RUN = (7.0, 3.0)         # non-hira category run fallback
_COST_HIRA_RUN = (9.0, 1.0)    # unknown hiragana run fallback
_COST_STRAY_HIRA = 14.0        # single non-particle hiragana (discouraged)
_COST_SUFFIX = (0.0, 6.0)      # honorific / plural suffix after a nominal (さん/ちゃん/たち)
_COST_PROPER = (6.0, 5.0)      # KANJI + small-kana hiragana proper noun (坊っちゃん)

# --------------------------------------------------------------------------
# v0.2.5 additions
# --------------------------------------------------------------------------

# Honorific / plural suffixes that attach to a preceding non-hiragana token
# (田中さん / 花ちゃん / 子供たち). Only proposed when the previous character
# is NOT hiragana, so pure-hiragana words (みなさん / たくさん / ちゃんと) are
# never split.
_NOMINAL_SUFFIXES: frozenset[str] = frozenset({
    "さん", "ちゃん", "くん", "さま", "たち", "ども",
})
_MAX_SUFFIX_LEN = max(len(w) for w in _NOMINAL_SUFFIXES)

# す-verb conjugations after a KANJI-ending 交ぜ書き compound (思い出+した /
# 引き出+して). Plain KANJI + した stays サ変 (勉強|した) — this set is only
# consulted for compounds, never for single-run stems.
_SU_VERB_TAILS: frozenset[str] = frozenset({
    "した", "して", "します", "しない", "したい", "しません", "しました",
    "してる", "していた", "している", "しておく", "しよう", "せば",
})

# Small-form kana that can never begin a standalone Japanese word. A hiragana
# run starting with one of these right after a KANJI run is the tail of a
# cross-script proper noun (坊っちゃん) — ported from the cascade's
# heuristic_proper_noun_merge, which the v0.2 lattice had dropped.
_SMALL_KANA: frozenset[str] = frozenset("っゃゅょぁぃぅぇぉゎ")

# Bodies that look like small-kana proper-noun tails but are verb/adjective
# conjugation (言って / 買った / 走っちゃう / 子供っぽい) — never merge.
_PROPER_EXCLUDE_PREFIXES: tuple[str, ...] = (
    "った", "って", "っちゃう", "っちゃっ", "っちゃい", "っちゃえ", "っちま",
    "っぽ", "っとく", "っとい", "っとけ", "っつ",
)

# Characters at which a small-kana proper-noun body is cut (particle / copula
# boundary): 坊っちゃん|は / 坊っちゃん|だ.
_PROPER_BODY_TERMINATORS: frozenset[str] = _PARTICLES_1 | frozenset("だ")

# Multi-character compound particles written in pure hiragana (として is
# deliberately absent — it would split 落と|して). Without these
# the lattice splits における → に|おけ|る, where the SNS interjection おけ
# wrongly fires emotion=trust (found 2026-08-20 in the mini-GPT experiments).
_COMPOUND_PARTICLES: frozenset[str] = frozenset({
    "における", "において", "においては", "においても",
    "にとって", "にとっては", "について", "については",
    "によって", "により", "によると", "によれば",
    "とともに",
    "にわたって", "にわたり", "につれて", "にしては", "をもって",
})
# Pure-hiragana function words with their own POS. Without these the run
# fallback glues a conjunction to the first char of the next word
# (けれどもそ|の|とき / しかしまだ) and greetings split (こんにち|は).
_FUNCTION_WORDS: dict[str, str] = {}
for _w in ("しかし", "けれども", "けれど", "そうして", "そして", "だが", "ただし",
           "それで", "それから", "また", "つまり", "すなわち", "やがて",
           "ところが", "さて", "ところで", "それでも", "しかも", "なぜなら",
           "したがって", "ゆえに", "および", "または", "あるいは", "ならびに",
           "なお", "そこで", "すると", "だから", "でも"):
    _FUNCTION_WORDS[_w] = "接続詞"
for _w in ("この", "その", "あの", "どの", "こんな", "そんな", "あんな", "どんな"):
    _FUNCTION_WORDS[_w] = "連体詞"
for _w in ("まだ", "もう", "もはや", "やはり", "やっぱり", "なかなか", "ちょうど",
           "ずっと", "きっと", "たぶん", "まったく", "ぜんぜん", "いつも",
           "すぐ", "すこし", "ちょっと", "とても", "かなり", "すでに", "ついに",
           "やがて", "しばらく", "もちろん", "たしかに", "ただ", "なんだか"):
    _FUNCTION_WORDS.setdefault(_w, "副詞")
for _w in ("こんにちは", "こんばんは", "おはよう", "おやすみ", "さようなら",
           "ただいま", "おかえり", "いただきます", "ごちそうさま", "はじめまして"):
    _FUNCTION_WORDS[_w] = "感動詞-一般"
_MAX_FUNCTION_LEN = max(len(w) for w in _FUNCTION_WORDS)

# Copula tails so しかし|そう|だ does not lose to the whole-run fallback.
_COPULA_TAILS: frozenset[str] = frozenset({
    "そうだ", "ようだ", "のだ", "んだ", "だろう", "だった", "だって",
    "である", "であった", "であろう", "でしょ", "なのだ",
})

# Subset claimed ahead of keep_as_unit surfaces: the SNS interjection おけ is
# keep_as_unit, so における can only win if it is claimed first. Kept minimal
# on purpose — として would wrongly claim 落と|して.
_PRIORITY_PARTICLES: frozenset[str] = frozenset({
    "における", "において", "においては", "においても",
})


class _Node:
    __slots__ = ("cost", "dform", "end", "pos", "start")

    def __init__(self, start: int, end: int, pos: str, dform: str | None, cost: float):
        self.start = start
        self.end = end
        self.pos = pos
        self.dform = dform
        self.cost = cost


def _cost(table: tuple[float, float], length: int) -> float:
    base, rate = table
    return base - rate * length


# --------------------------------------------------------------------------
# Cached, bundle-derived resources
# --------------------------------------------------------------------------


def _lattice_resources(bundle: DictionaryBundle):
    """(matcher, payloads) for all dictionary surfaces, cached on the bundle."""
    res = bundle._cache.get("lattice_resources")
    if res is not None:
        return res

    kau = bundle.keep_as_unit_surfaces()  # {surface: pos}
    patterns: list[str] = []
    payloads: list[tuple[str, str | None, tuple[float, float]]] = []  # (pos, dform, cost)

    seen: set[str] = set()
    # Priority compound particles first (see _PRIORITY_PARTICLES).
    for surf in sorted(_PRIORITY_PARTICLES, key=lambda s: -len(s)):
        seen.add(surf)
        patterns.append(surf)
        payloads.append(("助詞", surf, _COST_KAU))
    # keep_as_unit surfaces next, longest first — their pattern ranks then
    # reproduce merge_keep_as_unit's greedy longest-match claiming exactly.
    for surf in sorted((s for s in kau if len(s) >= 2), key=lambda s: -len(s)):
        if surf in seen:
            continue
        seen.add(surf)
        patterns.append(surf)
        payloads.append((kau[surf], surf, _COST_KAU))
    n_kau = len(patterns)

    def _classify_dict_surface(surf: str) -> tuple[str, str | None]:
        lemma = _adjective_lemma(surf)
        if lemma == surf:  # い-adjective in base form (美味しい / 難しい)
            return "形容詞-一般", surf
        if _is_all_hiragana(surf):
            return _MERGED_POS, surf
        return "名詞-普通名詞-一般", surf

    for entries, is_entity in (
        (bundle.emotion, False),
        (bundle.slang, False),
        (bundle.entity, True),
    ):
        for e in entries:
            surf = e.surface
            if not surf or len(surf) < 2 or surf in seen:
                continue
            seen.add(surf)
            if is_entity:
                # Entities are nouns even when written in hiragana (もも 等)
                pos, dform = "名詞-普通名詞-一般", surf
            else:
                pos, dform = _classify_dict_surface(surf)
            patterns.append(surf)
            payloads.append((pos, dform, _COST_DICT))
    for e in bundle.entity:
        for alias in e.aliases:
            if alias and len(alias) >= 2 and alias not in seen:
                seen.add(alias)
                patterns.append(alias)
                payloads.append(("名詞-普通名詞-一般", alias, _COST_DICT))

    matcher = SurfaceMatcher(patterns)
    known_hira = _build_known_hiragana(bundle)
    # Same protection set as refine_verb_adjective_pos: a verb/adjective node
    # must never absorb a dictionary-known stem (満足+している → 満足 stays a
    # separate token so the semantic layer can match it).
    protected: frozenset[str] = frozenset(
        e.surface for e in bundle.emotion
    ) | frozenset(
        e.surface for e in bundle.external_emotion
    ) | frozenset(
        s.surface for s in bundle.slang
    ) | frozenset(
        e.surface for e in bundle.entity
    )
    res = (matcher, payloads, known_hira, n_kau, protected)
    bundle._cache["lattice_resources"] = res
    return res


# --------------------------------------------------------------------------
# Node proposal
# --------------------------------------------------------------------------

_GRAMMAR_WORDS: frozenset[str] = (
    _GRAMMAR_TAIL_MORPHEMES | _SURU_FORMS | _PARTICLES_2 | _COMPOUND_PARTICLES
    | _COPULA_TAILS
)
_MAX_GRAMMAR_LEN = max(len(w) for w in _GRAMMAR_WORDS)


def _category_runs(text: str) -> list[tuple[int, int, str]]:
    """Maximal same-category runs as (start, end, category)."""
    runs: list[tuple[int, int, str]] = []
    if not text:
        return runs
    start = 0
    cat = _char_cat(text[0])
    for i in range(1, len(text)):
        c = _char_cat(text[i])
        if c != cat:
            runs.append((start, i, cat))
            start, cat = i, c
    runs.append((start, len(text), cat))
    return runs


_RUN_POS = {
    "KANJI": "名詞-普通名詞-一般",
    "KATAKANA": "名詞-普通名詞-一般",
    "LATIN": "名詞-普通名詞-一般",
    "DIGIT": "名詞-数詞",
    "HIRAGANA": "助詞",
    "SYMBOL": "記号",
    "SPACE": "空白",
}


def _propose_nodes(text: str, bundle: DictionaryBundle) -> list[list[_Node]]:
    """Return nodes grouped by start position."""
    n = len(text)
    by_start: list[list[_Node]] = [[] for _ in range(n)]
    matcher, payloads, known_hira, n_kau, protected = _lattice_resources(bundle)
    all_matches = matcher.find_all(text)

    # keep_as_unit spans are claimed greedily first (longest-match, as in
    # merge_keep_as_unit) and every other node that CROSSES a claimed span is
    # suppressed — the cascade's "keep_as_unit wins outright" semantics.
    claimed = bytearray(n)
    for rank, s, e in all_matches:
        if rank < n_kau and not any(claimed[s:e]):
            pos, dform, cost_t = payloads[rank]
            by_start[s].append(_Node(s, e, pos, dform, _cost(cost_t, e - s)))
            for i in range(s, e):
                claimed[i] = 1

    def _free(s: int, e: int) -> bool:
        return not any(claimed[s:e])

    # Positions where a dictionary / known-hiragana content word begins —
    # okurigana extension must stop there so a verb node never swallows an
    # emotion word embedded in the hiragana run (通告されて|うんざり|している).
    content_start = bytearray(n)
    for rank, s, e in all_matches:
        if rank >= n_kau and e - s >= 2:
            content_start[s] = 1

    def _cap(s: int, e: int) -> int:
        """Largest end ≤ e such that [s, end) is free of claimed chars."""
        for i in range(s, e):
            if claimed[i]:
                return i
        return e

    # 1. Other dictionary surfaces
    for rank, s, e in all_matches:
        if rank < n_kau or not _free(s, e):
            continue
        pos, dform, cost_t = payloads[rank]
        by_start[s].append(_Node(s, e, pos, dform, _cost(cost_t, e - s)))

    runs = _category_runs(text)
    run_of: list[tuple[int, int, str]] = [None] * n  # type: ignore[list-item]
    for r in runs:
        for i in range(r[0], r[1]):
            run_of[i] = r

    for rs0, re0, cat0 in runs:
        if cat0 != "HIRAGANA":
            continue
        for p in range(rs0, re0):
            for ln in range(min(10, re0 - p), 1, -1):
                if text[p:p + ln] in known_hira:
                    content_start[p] = 1
                    break

    for i in range(n):
        if claimed[i]:
            continue  # inside a keep_as_unit span — only the kau node covers it
        rs, re_, cat = run_of[i]
        cap = _cap(i, re_)  # run end, truncated at the next claimed char

        # 6. Category-run fallback: from i to the (capped) end of the current
        # run, plus a 1-char node at every position so the lattice stays fully
        # connected when a better node ends mid-run (課金高すぎ|て|しぬw).
        if cat == "HIRAGANA":
            # The run fallback also stops before an embedded content word so
            # されてうんざりしている cannot swallow うんざり whole.
            for p in range(i + 1, cap):
                if content_start[p]:
                    cap = p
                    break
        length = cap - i
        if cat == "HIRAGANA":
            ch = text[i]
            ch_cost = _cost(_COST_GRAMMAR, 1) if ch in _PARTICLES_1 else _COST_STRAY_HIRA
            by_start[i].append(_Node(i, i + 1, "助詞", ch, ch_cost))
            if length > 1:
                by_start[i].append(
                    _Node(i, cap, "助詞", text[i:cap], _cost(_COST_HIRA_RUN, length))
                )
                # Same run with a trailing particle isolated (あった|けど /
                # まわり|を) — small bonus so the split beats the unsplit run.
                if length > 2 and text[cap - 2:cap] in _PARTICLES_2:
                    by_start[i].append(
                        _Node(i, cap - 2, "助詞", text[i:cap - 2],
                              _cost(_COST_HIRA_RUN, length - 2) - 1.5)
                    )
                if length > 1 and text[cap - 1] in _PARTICLES_1:
                    by_start[i].append(
                        _Node(i, cap - 1, "助詞", text[i:cap - 1],
                              _cost(_COST_HIRA_RUN, length - 1) - 2.5)
                    )
        else:
            if length > 1:
                by_start[i].append(_Node(i, i + 1, _RUN_POS[cat], text[i], 8.0))
            by_start[i].append(
                _Node(i, cap, _RUN_POS[cat], text[i:cap], _cost(_COST_RUN, length))
            )

        if cat == "HIRAGANA":
            # 2. Grammar morphemes (particles ≥2 / auxiliaries / サ変)
            for ln in range(min(_MAX_GRAMMAR_LEN, cap - i), 1, -1):
                seg = text[i:i + ln]
                if seg in _GRAMMAR_WORDS:
                    by_start[i].append(_Node(i, i + ln, "助詞", seg, _cost(_COST_GRAMMAR, ln)))
            # 9. Function words with their own POS (接続詞 / 連体詞 / 副詞 / 感動詞)
            for ln in range(min(_MAX_FUNCTION_LEN, cap - i), 1, -1):
                seg = text[i:i + ln]
                fpos = _FUNCTION_WORDS.get(seg)
                # Conjunctions only at a run head (sentence start / after
                # punctuation) — mid-run だが would split からだ|が.
                if fpos is not None and not (fpos == "接続詞" and i != rs):
                    by_start[i].append(_Node(i, i + ln, fpos, seg, _cost(_COST_KNOWN_HIRA, ln)))
            # 7. Honorific / plural suffix right after a non-hiragana token
            # (田中|さん / 花|ちゃん / 子供|たち). Previous char must not be
            # hiragana so みなさん / ちゃんと stay whole.
            if i == rs and i > 0 and run_of[i - 1] is not None \
                    and run_of[i - 1][2] not in ("HIRAGANA", "SPACE", "SYMBOL"):
                for ln in range(min(_MAX_SUFFIX_LEN, cap - i), 1, -1):
                    seg = text[i:i + ln]
                    if seg in _NOMINAL_SUFFIXES:
                        by_start[i].append(
                            _Node(i, i + ln, "接尾辞", seg, _cost(_COST_SUFFIX, ln))
                        )
            # known hiragana content words (pronouns / adverbs / dict words)
            for ln in range(min(10, cap - i), 1, -1):
                seg = text[i:i + ln]
                if seg in known_hira:
                    by_start[i].append(_Node(i, i + ln, "助詞", seg, _cost(_COST_KNOWN_HIRA, ln)))
            # 5. Pure-hira adjective conjugation (おかしく → おかしい).
            # Bare-い endings are excluded — any hiragana run ending in い
            # would otherwise masquerade as an adjective (なっていたみたい).
            for ln in range(min(8, cap - i), 2, -1):
                seg = text[i:i + ln]
                if seg.endswith(("く", "くて", "かった", "ければ", "くない", "くなかった", "しい")):
                    lemma = _adjective_lemma(seg)
                    if lemma:
                        # Bare く is adverbial (うまく話せない) unless a
                        # change-of-state verb follows (おかしくなっていた) —
                        # only then may the lemma feed the emotion lexicon.
                        if seg.endswith("く") and not seg.endswith("くて") \
                                and text[i + ln:i + ln + 2] not in ("なっ", "なる", "なり", "なれ"):
                            lemma = seg
                        by_start[i].append(
                            _Node(i, i + ln, "形容詞-一般", lemma, _cost(_COST_HIRA_ADJ, ln))
                        )

        # Verb/adjective and compound stems start at the KANJI run head only —
        # the cascade merges the whole preceding kanji token, so a mid-run
        # suffix stem (満|足している) would be an invention, not parity.
        if cat == "KANJI" and i == rs and cap == re_:
            # 3. Verb / adjective: KANJI stem [i, re_) + okurigana conjugation
            if re_ < n and run_of[re_][2] == "HIRAGANA":
                hs, he, _hc = run_of[re_]
                stem = text[i:re_]
                if stem in protected:
                    hs = he  # dictionary-known stem — no verb/adj node
                he_eff = min(he, _cap(hs, he))
                for p in range(hs + 1, he_eff):
                    if content_start[p]:
                        he_eff = p  # stop before an embedded content word
                        break
                for h in range(hs + 1, he_eff + 1):
                    if not _free(hs, h):
                        break
                    oku = text[hs:h]
                    # サ変 passive (理解される / 通告されて) — like _SURU_FORMS,
                    # the noun carries the meaning; keep it a separate token.
                    if oku.startswith(("され", "きり")):
                        break
                    kind = _classify_okurigana(oku)
                    if not kind:
                        continue
                    surf = stem + oku
                    if kind == "adj":
                        dform = _adjective_lemma(surf) or surf
                        pos = "形容詞-一般"
                    else:
                        dform = surf
                        pos = "動詞-一般"
                    by_start[i].append(
                        _Node(i, h, pos, dform, _cost(_COST_VERB_ADJ, h - i))
                    )

            # 8. Cross-script proper noun: KANJI + hiragana body starting with
            # a small kana (坊っちゃん). Body ends at the first particle /
            # copula char or grammar word; verb conjugations are excluded.
            if re_ < n and run_of[re_][2] == "HIRAGANA":
                hs, he, _hc = run_of[re_]
                he_eff = min(he, _cap(hs, he))
                if he_eff - hs >= 2 and text[hs] in _SMALL_KANA:
                    body_end = he_eff
                    for p in range(hs + 1, he_eff):
                        if text[p] in _PROPER_BODY_TERMINATORS or any(
                            text[p:p + ln] in _GRAMMAR_WORDS
                            for ln in range(2, min(_MAX_GRAMMAR_LEN, he_eff - p) + 1)
                        ):
                            body_end = p
                            break
                    body = text[hs:body_end]
                    if len(body) >= 2 and not body.startswith(_PROPER_EXCLUDE_PREFIXES) \
                            and _free(i, body_end):
                        by_start[i].append(
                            _Node(i, body_end, "名詞-固有名詞-一般", text[i:body_end],
                                  _cost(_COST_PROPER, body_end - i))
                        )

            # 4. 交ぜ書き compound: KANJI+ kana KANJI+ (+ trailing okurigana)
            if re_ < n and run_of[re_][2] == "HIRAGANA":
                hs, he, _hc = run_of[re_]
                if he - hs >= 1:
                    conn = text[hs]
                    conn_ok = (
                        conn not in _PARTICLES_1
                        and not (conn == "い" and text[i:re_] in _ADJ_STEMS)
                    )
                    if conn_ok and hs + 1 < n and run_of[hs + 1] is not None \
                            and run_of[hs + 1][2] == "KANJI" and hs + 1 == he:
                        _k2s, k2e, _ = run_of[hs + 1]
                        end = k2e
                        if _free(i, end):
                            by_start[i].append(
                                _Node(i, end, "名詞-普通名詞-一般", text[i:end],
                                      _cost(_COST_COMPOUND, end - i))
                            )
                            # compound verb conjugation (思い出+した / 飛び込+んだ /
                            # 取り扱+った) — same okurigana rules as source 3.
                            if (
                                end < n
                                and run_of[end] is not None
                                and run_of[end][2] == "HIRAGANA"
                                and text[i:end + 1] not in protected
                                and text[i:end + 2] not in protected
                            ):
                                hs2, he2, _ = run_of[end]
                                he2_eff = min(he2, _cap(hs2, he2))
                                for p in range(hs2 + 1, he2_eff):
                                    if content_start[p]:
                                        he2_eff = p
                                        break
                                for h in range(hs2 + 1, he2_eff + 1):
                                    oku = text[hs2:h]
                                    if oku.startswith(("され", "きり")):
                                        break
                                    # noun-closing okurigana + サ変 (打ち合わせ|した /
                                    # 取り引き|した) — the compound stays a noun.
                                    if oku[:2] in _TRAILING_OKURIGANA_2 or (
                                        oku[0] in _TRAILING_OKURIGANA
                                        and oku[1:] in _SU_VERB_TAILS
                                    ):
                                        break
                                    if _classify_okurigana(oku) == "verb" or oku in _SU_VERB_TAILS:
                                        by_start[i].append(
                                            _Node(i, h, "動詞-一般", text[i:h],
                                                  _cost(_COST_VERB_ADJ, h - i))
                                        )
                            # trailing okurigana (締め切+り / 打ち合+わせ)
                            if end < n and run_of[end] is not None \
                                    and run_of[end][2] == "HIRAGANA":
                                t2 = text[end:end + 2]
                                t1 = text[end:end + 1]
                                if t2 in _TRAILING_OKURIGANA_2 and _free(end, end + 2):
                                    by_start[i].append(
                                        _Node(i, end + 2, "名詞-普通名詞-一般",
                                              text[i:end + 2],
                                              _cost(_COST_COMPOUND, end + 2 - i))
                                    )
                                if t1 in _TRAILING_OKURIGANA and _free(end, end + 1):
                                    by_start[i].append(
                                        _Node(i, end + 1, "名詞-普通名詞-一般",
                                              text[i:end + 1],
                                              _cost(_COST_COMPOUND, end + 1 - i))
                                    )

    return by_start


# --------------------------------------------------------------------------
# Viterbi (with a minimal bigram connection cost)
# --------------------------------------------------------------------------

# Bigram connection costs — two small pieces of Japanese grammar:
#
# * Two directly adjacent NOUN nodes without a particle between them are rare
#   (nouns normally connect via を/の/も…) → noun→noun adjacency penalty.
#   Same-script runs can never split into two adjacent noun nodes, so
#   ordinary compound nouns (single KANJI/KATAKANA runs) are unaffected.
# * The SAME single-char particle never repeats back-to-back (も|も is not
#   grammatical — もも there is a word) → same-particle repetition penalty.
#
# Together these resolve the classic すもももももももものうち to
# すもも|も|もも|も|もも|の|うち (given すもも/もも in the dictionary),
# instead of the dictionary-greedy すもも|もも|もも|もも.
_NOUN_ADJ_PENALTY = 6.0
_SAME_PARTICLE_PENALTY = 8.0

_ST_NOUN = "N"
_ST_OTHER = "O"


def _node_state(node: _Node, text: str) -> str | tuple[str, str]:
    if node.pos.startswith("名詞"):
        return _ST_NOUN
    if node.pos == "助詞" and node.end - node.start == 1:
        ch = text[node.start]
        if ch in _PARTICLES_1:
            return ("P", ch)
    return _ST_OTHER


def lattice_tokenize(text: str, bundle: DictionaryBundle) -> list[Token]:
    """Tokenize ``text`` by cheapest-path search over the proposal lattice."""
    n = len(text)
    if n == 0:
        return []

    by_start = _propose_nodes(text, bundle)

    # DP over (position, state of last emitted node). States: noun / single
    # particle (by char) / other — just enough context for the two bigram
    # connection costs above.
    best: list[dict] = [{} for _ in range(n + 1)]
    back: list[dict] = [{} for _ in range(n + 1)]
    best[0][_ST_OTHER] = 0.0

    for i in range(n):
        states = best[i]
        if not states:
            continue
        for node in by_start[i]:
            nstate = _node_state(node, text)
            for pstate, base in states.items():
                c = base + node.cost
                if pstate == _ST_NOUN and nstate == _ST_NOUN:
                    c += _NOUN_ADJ_PENALTY
                elif pstate == nstate and isinstance(nstate, tuple):
                    c += _SAME_PARTICLE_PENALTY
                cur = best[node.end].get(nstate)
                if cur is None or c < cur:
                    best[node.end][nstate] = c
                    back[node.end][nstate] = (node, pstate)

    if not best[n]:
        return []  # unreachable — should not happen (runs cover all)

    # Reconstruct from the cheapest terminal state
    state = min(best[n], key=best[n].get)
    path: list[_Node] = []
    pos = n
    while pos > 0:
        node, state = back[pos][state]
        path.append(node)
        pos = node.start
    path.reverse()

    tokens: list[Token] = []
    for node in path:
        surface = text[node.start:node.end]
        if node.pos == "空白":
            continue
        tokens.append(
            Token(
                id=len(tokens),
                surface=surface,
                normalized=surface,
                dictionary_form=node.dform or surface,
                reading=None,
                pos=node.pos,
                begin=node.start,
                end=node.end,
                unknown=(node.pos == "記号"),
            )
        )
    return tokens
