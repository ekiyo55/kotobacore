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

import re

from kotobacore.core.ir import Token
from kotobacore.core.matching import SurfaceMatcher
from kotobacore.core.token.conjugation import analyze_conjugation
from kotobacore.core.token.karuizawa_backend import _char_cat
from kotobacore.core.token.token_normalizer import (
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
    _reduplication_length,
    fold_emphatic_reduplication,
)
from kotobacore.dictionary import DictionaryBundle

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
_COST_HIRA_VERB = (6.0, 3.0)   # pure-hiragana verb (あります / かかる / なった)
_COST_FIXED = (3.0, 3.0)       # fixed KANJI+kana words (同じ / 大きな)
_COST_REDUP = (5.0, 3.0)       # onomatopoeic reduplication (しとしと / もやもや)

# v0.2.6 — over-merge control (LM-vocabulary feedback, 2026-08-28):
# a verb / compound stem may start mid-KANJI-run (突然|云い出した) but never
# span more than _MAX_STEM_KANJI kanji; starting mid-run costs a small penalty
# so 走り出した (1-kanji stem) is unaffected.
_MAX_STEM_KANJI = 2
_MID_STEM_PENALTY = 4.0
# _classify_okurigana only inspects the ending, so an arbitrarily long
# hiragana run ending in る/た passes as "verb" (張+りのあるまでどうかやって
# もらいたい). Real conjugations top out around 8 chars (られませんでした).
_MAX_OKURIGANA = 9
_MAX_HIRA_VERB_TAIL = 5

# KANJI words that commonly sit directly before a verb with no particle
# (昨日買った / 突然云い出した / 毎日走る). A mid-run stem is only proposed
# when the run prefix is one of these or a dictionary surface — an
# unconditional split would invent 昨|日買った.
_PREFIX_NOUNS: frozenset[str] = frozenset({
    "突然", "昨日", "今日", "明日", "毎日", "毎朝", "毎晩", "毎週", "毎月", "毎年",
    "今朝", "今夜", "今晩", "今回", "前回", "次回", "毎回", "最初", "最後", "結局",
    "実際", "本当", "全部", "一番", "一度", "二度", "何度", "何回", "何時", "何日",
    "一日", "一人", "二人", "三人", "自分", "先日", "当日", "翌日", "早速", "偶然",
    "当然", "勿論", "大変", "一緒", "一体", "一生", "一瞬", "大抵", "多分", "直接",
    "急遽", "先程", "先週", "来週", "去年", "今年", "来年", "午前", "午後", "夕方",
    "深夜", "早朝", "普段", "時々", "度々", "始終", "終日", "連日", "最近", "以前",
    "以来", "以後", "同時", "再度", "再三", "近頃", "今度", "一応", "一切", "全然",
})

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

# Pure-hiragana verb stems (v0.2.6). Tail is validated by _classify_okurigana,
# so あ+ります / かか+った / な+って all resolve. Single-char stems that collide
# with grammar words are deliberately absent (し→した, み→みたい, よ→よく).
_HIRA_VERB_STEMS: frozenset[str] = frozenset({
    "あ", "い", "な", "く", "う",
    "かか", "でき", "もら", "くれ", "おも", "わか", "つく", "つか",
    "たべ", "かえ", "はじま", "はじめ", "おわ", "かんが", "つづ", "いき",
    "おこ", "おき", "すわ", "なが", "もど", "まも", "たす", "はな", "はたら",
    "あそ", "うご", "つた", "あつま", "あつめ", "うま", "おし", "おぼ", "かん",
    "きま", "きめ", "こま", "さが", "しら", "とど",
    "にげ", "のこ", "ひろ", "ふえ", "まよ", "むか", "もち",
    "やす", "よろこ", "わす", "わら",
})
_MAX_HIRA_VERB = max(len(w) for w in _HIRA_VERB_STEMS) + 8

# Fixed KANJI+kana words that the okurigana assembler would otherwise absorb
# into a verb (同+じである → 同じ|である).
_FIXED_WORDS: dict[str, str] = {
    "同じ": "形状詞", "同じく": "副詞", "大きな": "連体詞", "小さな": "連体詞",
    "色んな": "連体詞", "様々": "形状詞", "色々": "副詞", "初めて": "副詞",
    "全く": "副詞", "既に": "副詞", "更に": "副詞", "再び": "副詞", "常に": "副詞",
    "必ず": "副詞", "少し": "副詞", "直ぐ": "副詞", "殆ど": "副詞",
}
_MAX_FIXED_LEN = max(len(w) for w in _FIXED_WORDS)

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
    "しまう", "しまった", "しまって", "しまいます", "しまえ",
})

# Subset claimed ahead of keep_as_unit surfaces: the SNS interjection おけ is
# keep_as_unit, so における can only win if it is claimed first. Kept minimal
# on purpose — として would wrongly claim 落と|して.
# v1.1 (DD evaluation): nominalised 連用形 — KANJI stem + ONE okurigana kana
# used as a noun or clause-final verb (見込み / 残り / 漏れ / 支払い / 受け /
# 向け / 及び / 期限|切れ). _classify_okurigana rejects a lone kana, so these
# fell apart into stem + stray hiragana (見込|み). し (サ変) and に/て/で (particles)
# are excluded on purpose.
_RENYOU_KANA = frozenset("いきちびみりれけえめ")
# what may follow the kana: a particle / conjunction start, or any non-hiragana
_RENYOU_NEXT_HIRA = frozenset("のはがをにとでもへやか")
_RENYOU_BONUS = 3.5  # below an assembled verb/adjective of the same span (高い stays 形容詞)

_PRIORITY_PARTICLES: frozenset[str] = frozenset({
    "における", "において", "においては", "においても",
    # v1.1 (DD evaluation): kanji compound particles — without them the kanji
    # is stranded as a noun (本件に|関|して / 契約に|基|づき).
    "に関して", "に関しては", "に関し", "に関する",
    "に対して", "に対しては", "に対し", "に対する",
    "に基づき", "に基づいて", "に基づく",
    "に伴い", "に伴って", "に伴う",
    "に際して", "に際し",
    "に応じて", "に応じた",
    "に従い", "に従って",
    "を通じて", "を通して",
    "に加えて", "に比べて", "に向けて", "に向けた",
})


def _is_kana_or_choon(c: str) -> bool:
    """Hiragana / katakana / prolonged-sound mark ー."""
    o = ord(c)
    return 0x3041 <= o <= 0x3096 or 0x30A1 <= o <= 0x30F6 or o == 0x30FC


class _Node:
    __slots__ = ("cost", "dform", "end", "fine", "pos", "run", "start")

    def __init__(
        self, start: int, end: int, pos: str, dform: str | None, cost: float,
        fine: bool = False, run: bool = False,
    ):
        self.start = start
        self.end = end
        self.pos = pos
        self.dform = dform
        self.cost = cost
        # True for assembled nodes (verb/adjective/交ぜ書き/hiragana verb) that
        # granularity="fine" may split into 語幹 / 送り仮名 / 活用語尾.
        self.fine = fine
        # True for plain character-category run nodes (no dictionary backing);
        # granularity="fine" may split an all-kanji one into words (v1.0.2).
        self.run = run


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
        (bundle.sentiment, False),  # v0.5: evaluative words (いまいち / 使いやすい) become lattice nodes too
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
            elif entries is bundle.sentiment and _is_all_hiragana(surf) and _adjective_lemma(surf) != surf:
                # Evaluative hiragana words (いまいち / だめ) behave like 形状詞: they take だ/で/な
                pos, dform = "形状詞", surf
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
    # N4 okurigana variants (申込み / 見積 / 引落): whole-word noun nodes whose
    # dform is the canonical 本則 spelling (v0.6.3). Without them the compact
    # spellings split into stem + stray hiragana (見積|もり).
    for e in bundle.okurigana:
        for surf in (e.canonical, *e.variants):
            if surf and len(surf) >= 2 and surf not in seen:
                seen.add(surf)
                patterns.append(surf)
                payloads.append(("名詞-普通名詞-一般", e.canonical, _COST_DICT))

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
    ) | frozenset(
        e.surface for e in bundle.sentiment
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


def _is_hira_verb(seg: str, known_hira: frozenset[str] = frozenset()) -> bool:
    """True when ``seg`` is stem+tail for a known pure-hiragana verb (かかります).

    A known hiragana content word starting at the same position and longer
    than the stem (うんざり vs stem う) always wins — the verb is rejected.
    """
    for ln in range(min(len(seg), 10), 1, -1):
        if seg[:ln] in known_hira:
            return False
    for st_len in range(min(len(seg) - 1, 4), 0, -1):
        stem = seg[:st_len]
        if stem in _HIRA_VERB_STEMS:
            oku = seg[st_len:]
            if st_len == 1 and len(oku) < 2:
                continue
            if len(oku) <= _MAX_HIRA_VERB_TAIL and _classify_okurigana(oku) == "verb":
                return True
    return False


# v1.1 (DD evaluation report §5.1): numeric expressions claimed as whole tokens,
# the same way keep_as_unit surfaces are — a boundary inside them is never right.
#   1,234 / 1,234.5 / 32.5      numbers with a thousands separator or a decimal
#   2026/9/29 / 2026-09-29       dates
#   第12条 / 第3項 / 第2号       article references, one token per level
#   △ / ▲ before a number        accounting minus sign (split from a bracket: (△56)
#   % / ％ after a number, and 、 。 — punctuation never glues to a symbol ()、 / %、)
#   unit after a number when the kanji run goes on: 3|日間|停止, 100|万円|未満
# Plain digits and units stay separate tokens (2026 / 年 / 4 / 月) as before.
_NUM_CLAIMS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?<![0-9.,])[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?(?![0-9]|,[0-9])"), "名詞-数詞"),
    (re.compile(r"(?<![0-9.])[0-9]+\.[0-9]+(?![0-9.])"), "名詞-数詞"),
    (re.compile(r"(?<![0-9])[0-9]{4}[/-][0-9]{1,2}[/-][0-9]{1,2}(?![0-9])"), "名詞-数詞"),
    (re.compile(r"第[0-9]+(?:条|項|号|章|節|款|目|編)(?:の[0-9]+)?"), "名詞-普通名詞-一般"),
    (re.compile(r"[△▲](?=[0-9])"), "記号"),
    (re.compile(r"(?<=[0-9])[%％]"), "記号"),
    # 、。 never glue to a neighbouring symbol (1,234)、 / 32.5%、)
    (re.compile(r"[、。]"), "記号"),
)
_NUM_UNITS = sorted(
    ("日間", "か月", "ヶ月", "カ月", "箇月", "週間", "時間", "年間", "年度", "月期", "月末", "日", "年", "月",
     "分", "秒", "件", "名", "人", "社", "個", "回", "倍", "歳", "円", "期", "割", "台", "店", "本", "枚", "株",
     "点", "位", "部", "階", "番", "行", "字", "頁"),
    key=len, reverse=True,
)
# number scale words that may precede a unit (1|万人|突破 / 1,234|百万円) or stand alone (3|億)
_NUM_SCALES = ("百万", "千万", "万", "億", "兆", "千", "百")
_UNIT_AFTER_NUM = re.compile(
    "(?<=[0-9])(?:(?:" + "|".join(_NUM_SCALES) + ")?(?:" + "|".join(_NUM_UNITS) + ")|" + "|".join(_NUM_SCALES) + ")"
)


# v1.1: the suffix 等 after a word is its own token (監査|等、備付け|等、発生|等) — except in words
# that end with 等 (平等 / 同等 / 彼等) and before し (等しい)
_TO_SUFFIX = re.compile(r"(?<=[\u4e00-\u9fff\u3005\u3041-\u3093\u30a1-\u30f6\u30fc])等(?![\u4e00-\u9fff\u3005し])")
_TO_WORDS = frozenset((
    "平等", "同等", "対等", "均等", "上等", "高等", "優等", "劣等", "初等", "中等", "特等", "下等", "一等", "二等", "三等",
    "親等", "彼等", "我等", "何等", "吾等", "汝等", "是等", "此等", "其等", "之等", "不等", "次等", "郎等", "郎党",
))


def _numeric_claims(text: str) -> list[tuple[int, int, str]]:
    out = [(m.start(), m.end(), pos) for rx, pos in _NUM_CLAIMS for m in rx.finditer(text)]
    out += [(m.start(), m.end(), "接尾辞-名詞的-一般") for m in _TO_SUFFIX.finditer(text)
            if text[max(0, m.start() - 1):m.end()] not in _TO_WORDS]
    # the LONGEST unit after the number, claimed only when more kanji follow (3|日間|停止,
    # but 1,234|百万円（ and 3|月期|と keep the lattice's usual reading)
    out += [(m.start(), m.end(), "名詞-普通名詞-一般") for m in _UNIT_AFTER_NUM.finditer(text)
            if m.end() < len(text) and _char_cat(text[m.end()]) == "KANJI"]
    return sorted(out, key=lambda x: (x[0], -(x[1] - x[0])))


def _prefix_score(prefix: str, lex: frozenset[str]) -> int:
    """How word-like a kanji prefix left of a 連用形 stem is (higher = better).

    dictionary word > ends in a 1-kanji suffix (使用料 / 物流株式会社) >
    even length (期限 / 源泉徴収 — Sino-Japanese words come in 2-kanji units).
    """
    if prefix in lex:
        return 3
    if len(prefix) >= 2 and prefix[-1] in _KANJI_SUFFIXES:
        return 2
    return 1 if len(prefix) % 2 == 0 else 0


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
            # Never claim a span that straddles an XYXY reduplication — the
            # slang あざ must not steal the middle of ざあざあ (which would
            # both shatter the onomatopoeia and fire a false emotion).
            if s >= 1 and e < n and text[s - 1:e - 1] == text[s + 1:e + 1] \
                    and text[s - 1] != text[s]:
                continue
            pos, dform, cost_t = payloads[rank]
            by_start[s].append(_Node(s, e, pos, dform, _cost(cost_t, e - s)))
            for i in range(s, e):
                claimed[i] = 1
    # v1.1: numeric expressions (1,234 / 32.5 / 2026/9/29 / 第12条 / 3|日間|停止)
    num_claim_ends: list[int] = []
    for s0, e0, pos in _numeric_claims(text):
        if not any(claimed[s0:e0]):
            by_start[s0].append(_Node(s0, e0, pos, text[s0:e0], _cost(_COST_KAU, e0 - s0)))
            for i in range(s0, e0):
                claimed[i] = 1
            num_claim_ends.append(e0)

    def _free(s: int, e: int) -> bool:
        return not any(claimed[s:e])

    # Positions where a dictionary / known-hiragana content word begins —
    # okurigana extension must stop there so a verb node never swallows an
    # emotion word embedded in the hiragana run (通告されて|うんざり|している).
    content_start = bytearray(n)
    dict_spans: set[tuple[int, int]] = set()
    for rank, s, e in all_matches:
        if rank >= n_kau and e - s >= 2:
            content_start[s] = 1
            dict_spans.add((s, e))
    mid_ok = bytearray(n)  # positions where a mid-KANJI-run stem may start
    for e0 in num_claim_ends:  # a verb may start right after a claimed unit (3件|届いております)
        if e0 < n:
            mid_ok[e0] = 1

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

    # v1.1: a dictionary word with okurigana that starts inside a KANJI run
    # (偽装|請け負い / 退職|引き継ぎ) — give the path a node for the run part
    # before it; pure-kanji words embedded in a run are left alone.
    for s1, e1 in dict_spans:
        rs1, re1, cat1 = run_of[s1]
        if cat1 == "KANJI" and rs1 < s1 and e1 > re1 and _free(rs1, s1):
            by_start[rs1].append(
                _Node(rs1, s1, _RUN_POS["KANJI"], text[rs1:s1], _cost(_COST_RUN, s1 - rs1), run=True)
            )

    for rs0, re0, cat0 in runs:
        if cat0 != "HIRAGANA":
            continue
        for p in range(rs0, re0):
            for ln in range(min(10, re0 - p), 1, -1):
                if text[p:p + ln] in known_hira:
                    content_start[p] = 1
                    break

    # 11. Onomatopoeic reduplication (しとしと / もやもや) — a text-wide
    # pre-pass, kana + ー only, because the pattern may straddle run
    # boundaries: the prolonged-sound mark ー is a KATAKANA-category char, so
    # にゃーにゃー / もーもー span four runs. Spans are also marked as content
    # starts so the hiragana run fallback cannot swallow the text leading up
    # to them (ひよこが|ぴよぴよ). The reduplicated unit must not itself be a
    # known / grammar word so わかる|わかる and ます|ます keep their ordinary
    # segmentation.
    i2 = 0
    while i2 < n:
        if claimed[i2] or not _is_kana_or_choon(text[i2]):
            i2 += 1
            continue
        rl = _reduplication_length(text, i2)
        if rl and _free(i2, i2 + rl) \
                and all(_is_kana_or_choon(c) for c in text[i2:i2 + rl]):
            # Phase correction: in からはらはら the shifted pattern らはらは
            # matches first, but the dictionary word はらはら starts one char
            # later — yield to it (its own node + content start handle it).
            if text[i2:i2 + rl] not in known_hira and any(
                text[i2 + 1:i2 + 1 + ln] in known_hira for ln in (4, 6)
            ):
                i2 += 1
                continue
            unit = text[i2:i2 + rl // 2]
            if unit not in known_hira and unit not in _GRAMMAR_WORDS:
                by_start[i2].append(
                    _Node(i2, i2 + rl, "副詞", text[i2:i2 + rl],
                          _cost(_COST_REDUP, rl))
                )
                content_start[i2] = 1
                i2 += rl
                continue
        # Sokuon-emphasised reduplication (わっくわく / ワックワク) —
        # dictionary_form carries the base form (わくわく) for the emotion
        # lexicon's dictionary_form pass.
        if i2 + 5 <= n and text[i2 + 1] in "っッ" \
                and text[i2] == text[i2 + 3] and text[i2 + 2] == text[i2 + 4] \
                and text[i2] != text[i2 + 2] and _free(i2, i2 + 5) \
                and all(_is_kana_or_choon(c) for c in text[i2:i2 + 5]):
            by_start[i2].append(
                _Node(i2, i2 + 5, "副詞", (text[i2] + text[i2 + 2]) * 2,
                      _cost(_COST_REDUP, 5))
            )
            content_start[i2] = 1
            i2 += 5
            continue
        i2 += 1

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
                    _Node(i, cap, "助詞", text[i:cap], _cost(_COST_HIRA_RUN, length),
                          fine=True)
                )
                # Same run with a trailing particle isolated (あった|けど /
                # まわり|を) — small bonus so the split beats the unsplit run.
                if length > 2 and text[cap - 2:cap] in _PARTICLES_2:
                    by_start[i].append(
                        _Node(i, cap - 2, "助詞", text[i:cap - 2],
                              _cost(_COST_HIRA_RUN, length - 2) - 1.5, fine=True)
                    )
                if length > 1 and text[cap - 1] in _PARTICLES_1:
                    by_start[i].append(
                        _Node(i, cap - 1, "助詞", text[i:cap - 1],
                              _cost(_COST_HIRA_RUN, length - 1) - 2.5, fine=True)
                    )
        else:
            # v1.1: a run of middle dots only (利払い前・税引き前) is punctuation, not a katakana noun
            rpos = "記号" if all(ch == "・" for ch in text[i:cap]) else _RUN_POS[cat]
            if length > 1:
                by_start[i].append(_Node(i, i + 1, "記号" if text[i] == "・" else _RUN_POS[cat], text[i], 8.0, run=True))
            by_start[i].append(
                _Node(i, cap, rpos, text[i:cap], _cost(_COST_RUN, length), run=True)
            )
            # KANJI run prefix (突然|云い出した / 何|時間かかる): the run minus
            # the 1–2 kanji that a following verb / compound stem may take.
            if cat == "KANJI" and i == rs and cap == re_ and re_ < n \
                    and run_of[re_] is not None and run_of[re_][2] == "HIRAGANA" \
                    and text[rs:re_] not in protected:
                for k in (1, 2):
                    pe = re_ - k
                    if pe - i >= 1 and (
                        text[i:pe] in _PREFIX_NOUNS or (i, pe) in dict_spans
                    ):
                        mid_ok[pe] = 1
                        by_start[i].append(
                            _Node(i, pe, _RUN_POS[cat], text[i:pe],
                                  _cost(_COST_RUN, pe - i) + 1.0, run=True)
                        )
        # Fixed KANJI+kana words (同じ / 大きな) — any script boundary
        for ln in range(min(_MAX_FIXED_LEN, n - i), 1, -1):
            seg = text[i:i + ln]
            fpos = _FIXED_WORDS.get(seg)
            if fpos is not None and _free(i, i + ln):
                by_start[i].append(_Node(i, i + ln, fpos, seg, _cost(_COST_FIXED, ln)))

        if cat == "HIRAGANA":
            # 2. Grammar morphemes (particles ≥2 / auxiliaries / サ変)
            for ln in range(min(_MAX_GRAMMAR_LEN, cap - i), 1, -1):
                seg = text[i:i + ln]
                if seg in _GRAMMAR_WORDS:
                    by_start[i].append(_Node(i, i + ln, "助詞", seg, _cost(_COST_GRAMMAR, ln)))
            # 10. Pure-hiragana verbs (あります / かかった / なって)
            if not any(text[i:i + ln] in known_hira for ln in range(2, min(10, cap - i) + 1)):
                for st_len in range(min(n - i, 4), 0, -1):
                    stem = text[i:i + st_len]
                    if stem not in _HIRA_VERB_STEMS:
                        continue
                    for h in range(i + st_len + 1, min(cap, i + st_len + _MAX_HIRA_VERB_TAIL) + 1):
                        if content_start[h - 1] and h - 1 > i:
                            break  # never swallow an embedded content word
                        oku = text[i + st_len:h]
                        if st_len == 1 and len(oku) < 2:
                            continue
                        if _classify_okurigana(oku) != "verb":
                            continue
                        surf = text[i:h]
                        if surf in _GRAMMAR_WORDS:
                            continue
                        by_start[i].append(
                            _Node(i, h, "動詞-一般", surf, _cost(_COST_HIRA_VERB, h - i),
                                  fine=True)
                        )
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
            # A dictionary word (≥4 chars) starting here must not be absorbed
            # into a pseudo-adjective (わくわく+してく → 形容詞 わくわくしてく).
            dict_word_here = any(
                text[i:i + ln] in known_hira
                for ln in range(4, min(10, cap - i) + 1)
            )
            for ln in range(min(8, cap - i), 2, -1):
                if dict_word_here:
                    break
                seg = text[i:i + ln]
                if seg[0] in "がをへ" or _is_hira_verb(seg, known_hira):
                    continue
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
        fixed_here = cat == "KANJI" and any(
            text[i:i + ln] in _FIXED_WORDS
            for ln in range(2, min(_MAX_FIXED_LEN, n - i) + 1)
        )
        if cat == "KANJI" and cap == re_ and not fixed_here and (
            i == rs or mid_ok[i]
        ):
            mid_pen = 0.0 if i == rs else _MID_STEM_PENALTY
            # 3. Verb / adjective: KANJI stem [i, re_) + okurigana conjugation
            if re_ < n and run_of[re_][2] == "HIRAGANA":
                hs, he, _hc = run_of[re_]
                stem = text[i:re_]
                if stem in protected or (i == rs and re_ - i > _MAX_STEM_KANJI):
                    hs = he  # dictionary-known stem / over-long stem — no verb/adj node
                he_eff = min(he, _cap(hs, he))
                for p in range(hs + 1, he_eff):
                    if content_start[p]:
                        he_eff = p  # stop before an embedded content word
                        break
                for h in range(hs + 1, min(he_eff, hs + _MAX_OKURIGANA) + 1):
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
                    if kind == "verb" and _is_hira_verb(oku, known_hira):
                        continue  # 何時間|かかります — the verb is the hiragana part
                    surf = stem + oku
                    if kind == "adj":
                        dform = _adjective_lemma(surf) or surf
                        pos = "形容詞-一般"
                    else:
                        dform = surf
                        pos = "動詞-一般"
                    # stem kanji beyond the first count at the noun-run rate so a
                    # 2-kanji stem does not out-pull prefix|verb (突然|云い出した)
                    stem_extra = 3.0 * (len(stem) - 1)
                    by_start[i].append(
                        _Node(i, h, pos, dform,
                              _cost(_COST_VERB_ADJ, h - i) + mid_pen + stem_extra,
                              fine=True)
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
                            and run_of[hs + 1][2] == "KANJI" and hs + 1 == he \
                            and re_ - i <= _MAX_STEM_KANJI:
                        _k2s, k2e, _ = run_of[hs + 1]
                        end = k2e
                        if _free(i, end):
                            by_start[i].append(
                                _Node(i, end, "名詞-普通名詞-一般", text[i:end],
                                      _cost(_COST_COMPOUND, end - i) + mid_pen, fine=True)
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
                                for h in range(hs2 + 1, min(he2_eff, hs2 + _MAX_OKURIGANA) + 1):
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
                                                  _cost(_COST_VERB_ADJ, h - i) + mid_pen,
                                                  fine=True)
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
                                              _cost(_COST_COMPOUND, end + 2 - i) + mid_pen,
                                              fine=True)
                                    )
                                if t1 in _TRAILING_OKURIGANA and _free(end, end + 1):
                                    by_start[i].append(
                                        _Node(i, end + 1, "名詞-普通名詞-一般",
                                              text[i:end + 1],
                                              _cost(_COST_COMPOUND, end + 1 - i) + mid_pen,
                                              fine=True)
                                    )

    # 12. Nominalised 連用形 (見込み / 源泉徴収|漏れ / 使用料|支払い / 現金|及び).
    # The stem is the last 1–2 kanji of a KANJI run; when it starts mid-run the
    # rest of the run gets its own run node so the path can reach the stem.
    # A 2-kanji run is one stem (見込み); in a longer run the stem length is
    # chosen by how word-like the remaining prefix is (_prefix_score).
    kanji_lex = _kanji_lexicon(bundle)[0]
    for rs, re_, cat in runs:
        if cat != "KANJI" or re_ >= n or text[re_] not in _RENYOU_KANA:
            continue
        nxt = re_ + 1
        if nxt < n and run_of[nxt][2] == "HIRAGANA" and text[nxt] not in _RENYOU_NEXT_HIRA:
            continue  # 関して / 受けた / 漏れる — a conjugation, not a noun
        if nxt < n and run_of[nxt][2] == "KANJI" and text[re_] != "び":
            continue  # 打ち|合わせ is a 交ぜ書き compound; only 及び / 並び link to a kanji word
        if not _free(re_, nxt):
            continue
        run_len = re_ - rs
        if run_len <= 2:
            stems = (run_len,)
        else:
            p1, p2 = text[rs:re_ - 1], text[rs:re_ - 2]
            stems = (1,) if _prefix_score(p1, kanji_lex) >= _prefix_score(p2, kanji_lex) else (2,)
        for stem_len in stems:
            st = re_ - stem_len
            if st < rs or not _free(st, re_) or text[st:re_] in protected:
                continue
            by_start[st].append(
                _Node(st, nxt, "名詞-普通名詞-一般", text[st:nxt],
                      _cost(_COST_COMPOUND, nxt - st) - _RENYOU_BONUS, fine=True)
            )
            if st > rs and _free(rs, st):
                by_start[rs].append(
                    _Node(rs, st, _RUN_POS["KANJI"], text[rs:st],
                          _cost(_COST_RUN, st - rs), run=True)
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


def _split_unknown_hiragana(
    base: int, surface: str, known_hira: frozenset[str]
) -> list[tuple[int, int, str]]:
    """Greedy longest-match segmentation of an unknown hiragana run (fine mode).

    The coarse lattice keeps such runs whole (りのあるまでどうかやってもらいたい)
    because no dictionary node covers them. For LM vocabularies we split at
    grammar words / known words / function words / hiragana verbs, falling
    back to single characters — the same "character fallback" a subword
    tokenizer would apply, but with the grammar pieces kept intact.
    """
    n = len(surface)
    out: list[tuple[int, int, str]] = []
    i = 0
    while i < n:
        hit = None
        for ln in range(min(10, n - i), 1, -1):
            seg = surface[i:i + ln]
            if seg in _GRAMMAR_WORDS or seg in _COPULA_TAILS:
                hit = (ln, "助詞")
            elif seg in _FUNCTION_WORDS:
                hit = (ln, _FUNCTION_WORDS[seg])
            elif seg in known_hira:
                hit = (ln, "助詞")
            elif _is_hira_verb(seg, known_hira):
                hit = (ln, "動詞-一般")
            if hit:
                break
        if hit is None:
            out.append((base + i, base + i + 1, "助詞"))
            i += 1
        else:
            out.append((base + i, base + i + hit[0], hit[1]))
            i += hit[0]
    return out


def _fine_pieces(
    node: _Node, text: str, known_hira: frozenset[str] = frozenset()
) -> list[tuple[int, int, str]]:
    """Split an assembled node into (start, end, pos) pieces.

    * KANJI runs → 語幹 (動詞/形容詞) or 名詞
    * inner hiragana runs → 送り仮名
    * final hiragana run of a 動詞/形容詞 → 活用語尾
    * pure-hiragana verb → stem (longest _HIRA_VERB_STEMS match) + 活用語尾
    """
    surface = text[node.start:node.end]
    head = node.pos.split("-")[0]
    if node.pos == "助詞" and _is_all_hiragana(surface):
        return _split_unknown_hiragana(node.start, surface, known_hira)
    if head in ("動詞", "形容詞"):
        stem_pos, tail_pos = f"{head}-語幹", f"{head}-活用語尾"
    else:
        stem_pos, tail_pos = "名詞-普通名詞-一般", "送り仮名"
    if _is_all_hiragana(surface):
        for st_len in range(min(len(surface) - 1, 4), 0, -1):
            if surface[:st_len] in _HIRA_VERB_STEMS:
                return [
                    (node.start, node.start + st_len, stem_pos),
                    (node.start + st_len, node.end, tail_pos),
                ]
        return [(node.start, node.end, node.pos)]
    runs = _category_runs(surface)
    pieces: list[tuple[int, int, str]] = []
    for idx, (rs, re_, cat) in enumerate(runs):
        if cat == "HIRAGANA":
            last = idx == len(runs) - 1
            pos = tail_pos if last and head in ("動詞", "形容詞") else "送り仮名"
            if last and re_ - rs > 4:
                # a long tail is conjugation + auxiliaries (られませんでした):
                # keep the first grammar piece as 活用語尾, split the rest
                sub = _split_unknown_hiragana(node.start + rs, surface[rs:re_], known_hira)
                pieces.append((sub[0][0], sub[0][1], pos))
                pieces.extend(sub[1:])
                continue
        else:
            pos = stem_pos
        pieces.append((node.start + rs, node.start + re_, pos))
    return pieces


# --------------------------------------------------------------------------
# fine: kanji compound splitting (v1.0.2 / tokenizer 1.1)
# --------------------------------------------------------------------------

# One-kanji affixes that stand alone inside a compound. A kanji run of odd
# length needs a 1-char piece or a 3-kanji word somewhere; suffixes belong at
# the end of a word (東京都|知事 / 理事|会 / 合理|的 / 満足|感 / 感染|症),
# prefixes at the head of a longer run (新|制度改革).
_KANJI_SUFFIXES: frozenset[str] = frozenset(
    "的性化者会都府県市区町村党省庁局部課係長員家業法型式率費料力品用感派様済勢"
    "内外中後上下間別界学論史際圏層群類版号回数量額値点線面体物所場院館社店"
    "症病薬機器具製賞展祭戦権制案書税金時簿"
)
_KANJI_PREFIXES: frozenset[str] = frozenset("新旧再非不未無超副総第初最諸両当同現元全各毎前本")
# suffixes that almost never end a 2-kanji word themselves win a tie (源泉|所得|税, not 源泉|所|得税)
_KANJI_STRONG_SUFFIXES: frozenset[str] = frozenset("的性化者省庁税法率費料症感製済勢派様")
# Built-in pieces that the bundled dictionaries do not list as words
# (company-type words: 株式会社|山田|商事, not 株式|会社|…).
_KANJI_BUILTIN_WORDS: frozenset[str] = frozenset(
    ("株式会社", "有限会社", "合同会社", "合資会社", "合名会社", "財団法人", "社団法人")
)
_MIN_SPLIT_KANJI = 3
# Kanji numerals: a run with two in a row is a number / date (一九九五年一月,
# 三十代) — kept whole like digit runs.
_KANJI_NUMERALS = "〇一二三四五六七八九十百千万億兆"
_KANJI_NUMERAL_PAIR = re.compile(f"[{_KANJI_NUMERALS}]{{2}}")
_MAX_LEX_KANJI = 6
_KC_LEX = 1.0       # known all-kanji dictionary word
_KC_ATTESTED = 1.6  # 2-kanji word attested standalone in the bundled texts (v1.1)
_KC_TWO = 2.0       # unknown 2-kanji chunk (the typical Sino-Japanese word)
_KC_SUFFIX = 2.4    # 1-kanji suffix after the head (tie-break: suffix beats prefix)
_KC_STRONG_SUFFIX = 2.35  # strong suffix: wins a tie against a weaker one elsewhere
_KC_PREFIX = 2.5    # 1-kanji prefix at the head
_KC_THREE = 4.45    # unknown 3-kanji word (雰囲気 / 出来事 / 不動産): kept whole unless
#                     a suffix split (満足|感 = 4.4) is cheaper — a bare 3-kanji run
#                     is usually one word, so prefix splits (新|制度 = 4.5) lose
_KC_THREE_LONG = 4.9  # same inside a 4+ kanji run (不|動産|投資|信託 beats 不動|産投|資信託)
_KC_ONE = 4.0       # any other single kanji (+0.01 per char before the end)


_ATTESTED: frozenset[str] | None = None


def _attested_kanji_words() -> frozenset[str]:
    """2-kanji words that stand alone (between non-kanji) in the bundled dictionaries and SNS examples.

    A soft word list for the compound splitter (v1.1): without one, 2-kanji chunks
    fall on the wrong boundary (設立|時募|集株|式). Built only from resources that ship
    with the package — no evaluation data.
    """
    global _ATTESTED
    if _ATTESTED is None:
        from kotobacore.dictionary.loader import _DEFAULT_DICT_DIR

        rx = re.compile(r"(?<![\u4e00-\u9fff\u3005])[\u4e00-\u9fff\u3005]{2}(?![\u4e00-\u9fff\u3005])")
        words: set[str] = set()
        for p in [*sorted(_DEFAULT_DICT_DIR.glob("*.csv")), *sorted(_DEFAULT_DICT_DIR.glob("domains/*.csv")),
                  *sorted(_DEFAULT_DICT_DIR.glob("*.txt"))]:
            try:
                words.update(rx.findall(p.read_text(encoding="utf-8")))
            except OSError:
                continue
        _ATTESTED = frozenset(words)
    return _ATTESTED


def _is_kanji_run(surface: str) -> bool:
    return bool(surface) and all(_char_cat(ch) == "KANJI" for ch in surface)


def _kanji_lexicon(bundle: DictionaryBundle) -> tuple[frozenset[str], frozenset[str]]:
    """(all-kanji dictionary words usable as pieces, surfaces never split)."""
    res = bundle._cache.get("kanji_lexicon")
    if res is not None:
        return res
    words: set[str] = set()
    for e in (*bundle.emotion, *bundle.external_emotion, *bundle.slang, *bundle.sentiment):
        words.add(e.surface)
    for e in bundle.entity:
        words.add(e.surface)
        words.update(e.aliases)
    for e in bundle.okurigana:
        words.add(e.canonical)
        words.update(e.variants)
    for e in bundle.synonym:
        words.add(e.canonical)
        words.update(e.synonyms)
    for e in bundle.stopwords:
        words.add(e.surface)
    words.update(bundle.keep_as_unit_surfaces())
    keep = frozenset(w for w in words if w and _is_kanji_run(w))
    lex = frozenset(w for w in keep if 2 <= len(w) <= _MAX_LEX_KANJI) | _KANJI_BUILTIN_WORDS
    res = (lex, keep)
    bundle._cache["kanji_lexicon"] = res
    return res


def _split_kanji_compound(surface: str, lex: frozenset[str]) -> list[tuple[int, int]]:
    """Cheapest segmentation of an all-kanji compound into word-sized pieces.

    Known dictionary words win, unknown stretches fall back to 2-kanji chunks
    (自然|言語|処理), odd leftovers become 1-kanji affixes (理事|会 / 満足|感) or,
    failing that, one 3-kanji word (雰囲気 / 語彙|力|消失 / 力不足).
    A piece never ends right before the iteration mark 々 (代々木 stays whole).
    """
    n = len(surface)
    inf = float("inf")
    best = [0.0] + [inf] * n
    back = [0] * (n + 1)
    for i in range(n):
        if best[i] == inf:
            continue
        for ln in range(1, min(_MAX_LEX_KANJI, n - i) + 1):
            if i + ln < n and surface[i + ln] == "々":
                continue
            seg = surface[i:i + ln]
            if ln >= 2 and seg in lex:
                c = _KC_LEX
            elif ln == 2 and seg in _attested_kanji_words():
                c = _KC_ATTESTED
            elif ln == 2 or (ln == 3 and seg[1] == "々"):
                c = _KC_TWO
            elif ln == 3:
                c = _KC_THREE if n == 3 else _KC_THREE_LONG
            elif ln == 1:
                if i > 0 and seg in _KANJI_SUFFIXES:
                    c = _KC_STRONG_SUFFIX if seg in _KANJI_STRONG_SUFFIXES else _KC_SUFFIX
                elif i == 0 and seg in _KANJI_PREFIXES:
                    c = _KC_PREFIX
                else:
                    c = _KC_ONE + 0.01 * (n - 1 - i)
            else:
                continue
            if best[i] + c < best[i + ln]:
                best[i + ln] = best[i] + c
                back[i + ln] = i
    if best[n] == inf:
        return [(0, n)]
    out: list[tuple[int, int]] = []
    j = n
    while j > 0:
        out.append((back[j], j))
        j = back[j]
    out.reverse()
    return out


def lattice_tokenize(
    text: str, bundle: DictionaryBundle, granularity: str = "coarse"
) -> list[Token]:
    """Tokenize ``text`` by cheapest-path search over the proposal lattice.

    ``granularity``: "coarse" (default — semantic units: 思い出した / 締め切り)
    or "fine" (assembled verbs / adjectives / 交ぜ書き compounds are split into
    語幹・送り仮名・活用語尾, and all-kanji compounds of 3+ chars with no
    dictionary backing are split into word-sized pieces 自然|言語|処理 — for
    language-model vocabularies where ~2 chars per token is too long).
    Dictionary entities and keep_as_unit surfaces are never split.
    """
    n = len(text)
    if n == 0:
        return []

    by_start = _propose_nodes(text, bundle)
    known_hira = _lattice_resources(bundle)[2]

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
    fine = granularity == "fine"
    oku_map = bundle.okurigana_map()
    ent_norm = bundle.entity_normalized_map()
    oku_nouns = bundle._cache.get("okurigana_nouns")
    if oku_nouns is None:  # built once per bundle (rebuilding it per call cost ~7% of analyze())
        oku_nouns = frozenset(v for e in bundle.okurigana if e.pos.startswith("名詞") for v in (e.canonical, *e.variants))
        bundle._cache["okurigana_nouns"] = oku_nouns
    kanji_lex, kanji_keep = _kanji_lexicon(bundle) if fine else (frozenset(), frozenset())
    for node in path:
        if node.pos == "空白":
            continue
        if fine and node.fine:
            spans = _fine_pieces(node, text, known_hira)
        elif fine and node.run \
                and node.end - node.start >= _MIN_SPLIT_KANJI \
                and _is_kanji_run(text[node.start:node.end]) \
                and text[node.start:node.end] not in kanji_keep                 and not _KANJI_NUMERAL_PAIR.search(text[node.start:node.end]):
            spans = [
                (node.start + a, node.start + b, node.pos)
                for a, b in _split_kanji_compound(text[node.start:node.end], kanji_lex)
            ]
        else:
            spans = [(node.start, node.end, node.pos)]
        for ps, pe, ppos in spans:
            surface = text[ps:pe]
            whole = ps == node.start and pe == node.end
            dform = (node.dform or surface) if whole else surface
            ctype = cform = None
            if whole and ppos.startswith("動詞") and surface in oku_nouns:
                # v1.1: an okurigana-dictionary noun (割当て / 見積り) is a noun, lemma = canonical spelling
                ppos, dform = "名詞-普通名詞-一般", oku_map[surface]
            if whole and ppos.startswith(("動詞", "形容詞")):
                # N4: lemma / 活用型 / 活用形 for assembled verbs and adjectives
                info = analyze_conjugation(surface, ppos)
                if info is not None:
                    ctype, cform = info.conjugation_type, info.conjugation_form
                    if dform == surface or (
                        ppos.startswith("形容詞") and info.conjugation_type != "形容詞"
                    ):
                        # v1.1: a 形容詞 node whose surface is really a verb (関わりたくない → 関わる)
                        dform = info.lemma
            tokens.append(
                Token(
                    id=len(tokens),
                    surface=surface,
                    # N4: okurigana variants share one normalized spelling (引落 → 引き落とし);
                    # v1.1: entity aliases carry the canonical name (D&O保険 → 役員賠償責任保険)
                    normalized=(ent_norm.get(surface) or oku_map.get(surface, surface)) if whole else surface,
                    dictionary_form=dform,
                    reading=None,
                    pos=ppos,
                    begin=ps,
                    end=pe,
                    unknown=(ppos == "記号"),
                    conjugation_type=ctype,
                    conjugation_form=cform,
                )
            )
    # Katakana emphatic reduplication (ワックワク) survives as a single
    # category-run token — rewrite its dictionary_form to the base form.
    return fold_emphatic_reduplication(tokens)
