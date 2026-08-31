"""Token Normalizer.

Per 04_内部設計書 §3.1: sits between the Tokenizer Backend and the Semantic
Layer. Its v0.1 job is to enforce ``keep_as_unit`` — surfaces flagged in
slang.csv / emotion.csv with ``keep_as_unit=true`` must appear as a single
token even when the backend splits them.

Example
-------
Karuizawa tokenizes ``しぬw`` as ``しぬ`` (hiragana) / ``w`` (latin). ``しぬw``
is a ``keep_as_unit`` slang entry, so the Token Normalizer merges those 2
tokens back into one ``しぬw`` token.

When a keep_as_unit surface starts *inside* a larger backend token (e.g.
``わらった`` falls within a long hiragana run), the normalizer first splits
that token at the span boundary, then merges the resulting pieces.

A second pass ``split_hiragana_tokens`` segments long HIRAGANA runs that
Karuizawa leaves as single tokens.  It uses emotion/slang dictionary entries
and a hardcoded set of pronouns/adverbs as anchors, then strips particles
from the gaps between those anchors.
"""

from __future__ import annotations

import re

from kotobacore.dictionary import DictionaryBundle
from kotobacore.matching import SurfaceMatcher
from kotobacore.schema import Token

# POS assigned to a merged keep_as_unit token. SNS emotional expressions
# grammatically behave like interjections (感動詞).
_MERGED_POS = "感動詞-SNS表現"

# ---------------------------------------------------------------------------
# Constants for heuristic proper-noun detection
# ---------------------------------------------------------------------------

# Single-character particles to isolate from trailing HIRAGANA runs.
_PARTICLES_1: frozenset[str] = frozenset("はがをにのもでとへかなやねよわぞぜ")

# Two-character compound particles (checked before single-char to prefer longer match).
_PARTICLES_2: frozenset[str] = frozenset({
    "から", "まで", "より", "けど", "ので", "のに", "には", "では",
    "とは", "って", "ても", "ては", "でも", "ほど", "だけ", "さえ",
    "しか", "ずつ", "なら", "たら",
})

# Small-form kana that can never begin a standalone Japanese word — these
# signals that the HIRAGANA token is a suffix of the preceding KANJI token
# (e.g. 坊っちゃん).
_SMALL_KANA: frozenset[str] = frozenset("っゃゅょぁぃぅぇぉゎゕゖ")

# HIRAGANA-body prefixes that look like small kana but are actually verb
# conjugation forms (past tense った, conjunctive って). These must NOT trigger
# the proper-noun merge even though they start with っ.
_GRAMMAR_VERB_PREFIXES: frozenset[str] = frozenset({"った", "って"})

# Pure verb negation tails. When stripping a leading particle would leave only
# one of these as the body, the "particle" is actually verb okurigana
# (分 + からなくて — 分かる, not 分 + から[particle] + なくて): a real particle
# is never followed by a bare negation form. Skip the strip in that case.
_VERB_NEG_TAILS: frozenset[str] = frozenset({
    "ない", "なく", "なくて", "なかった", "なければ", "ず",
})

# Leading particles that are unambiguously separable from a HIRAGANA body
# following a nominal token (e.g. 大谷翔平+はすごい → は+すごい).
# Only the most common, unambiguous ones are listed — は,が,を,に,も,へ.
# の/で/と are excluded: they appear frequently inside compound words.
_PARTICLES_1_LEADING: frozenset[str] = frozenset("はがをにもへ")
_PARTICLES_2_LEADING: frozenset[str] = frozenset({
    "から", "まで", "より", "には", "では", "とは", "でも",
})


def _strip_leading_particle(surface: str) -> tuple[str, str]:
    """Return ``(particle, body)``; ``particle`` is empty when none detected."""
    if len(surface) >= 3 and surface[:2] in _PARTICLES_2_LEADING:
        return surface[:2], surface[2:]
    if len(surface) >= 2 and surface[0] in _PARTICLES_1_LEADING:
        return surface[0], surface[1:]
    return "", surface


def _strip_trailing_particle(surface: str) -> tuple[str, str]:
    """Return ``(body, particle)``; ``particle`` is empty when none detected."""
    if len(surface) >= 3 and surface[-2:] in _PARTICLES_2:
        return surface[:-2], surface[-2:]
    if len(surface) >= 2 and surface[-1] in _PARTICLES_1:
        return surface[:-1], surface[-1]
    return surface, ""


def _split_at_boundaries(
    tokens: list[Token],
    spans: list[tuple[int, int, str]],
    text: str,
) -> list[Token]:
    """Split tokens whose interior is crossed by a span start or end position.

    Karuizawa groups all consecutive same-category characters into one token.
    A keep_as_unit surface that begins or ends mid-token is unreachable by
    the merge step — split the enclosing token first so boundaries align.
    """
    boundaries: set[int] = set()
    for sb, se, _ in spans:
        boundaries.add(sb)
        boundaries.add(se)

    result: list[Token] = []
    for tok in tokens:
        inner = sorted(b for b in boundaries if tok.begin < b < tok.end)
        if not inner:
            result.append(tok)
            continue
        prev = tok.begin
        for b in inner:
            surface = text[prev:b]
            result.append(Token(
                id=tok.id,
                surface=surface,
                normalized=surface,
                dictionary_form=surface,
                reading=None,
                pos=tok.pos,
                begin=prev,
                end=b,
                unknown=tok.unknown,
            ))
            prev = b
        surface = text[prev:tok.end]
        result.append(Token(
            id=tok.id,
            surface=surface,
            normalized=surface,
            dictionary_form=surface,
            reading=None,
            pos=tok.pos,
            begin=prev,
            end=tok.end,
            unknown=tok.unknown,
        ))
    return result


# ---------------------------------------------------------------------------
# Hiragana particle / word segmentation pass
# ---------------------------------------------------------------------------

# Closed-class words (pronouns, demonstratives, common adverbs) that serve as
# reliable anchors when splitting long hiragana runs.  Content words from
# emotion.csv / slang.csv are added at runtime by _build_known_hiragana().
_HIRAGANA_KNOWN_WORDS: frozenset[str] = frozenset({
    # Pronouns / demonstratives
    "これ", "それ", "あれ", "どれ",
    "ここ", "そこ", "あそこ", "どこ",
    "こちら", "そちら", "あちら", "どちら",
    "こんな", "そんな", "あんな", "どんな",
    "こんなに", "そんなに", "あんなに", "どんなに",
    "だれ", "なに", "なん",
    "あなた", "きみ", "かれ", "かのじょ",
    "わたし", "わたくし", "ぼく", "おれ", "われ", "われわれ",
    "みんな", "みな", "かれら",
    # Frequent adverbs (prevent false particle splits inside them)
    "とても", "すごく", "めっちゃ", "めちゃ",
    "もっと", "もっとも",
    "ちょっと", "すこし",
    "ぜんぜん", "まったく", "まるで",
    "やっぱり", "やはり",
    "もちろん", "きっと", "たぶん", "おそらく",
    "なんか", "なんとなく",
    "いつも", "よく",
    "ほんとう", "ほんとに", "ほんと",
    "たしかに", "たしか",
    "あまり", "あんまり",
    "だいたい", "たいてい",
    "しっかり", "ゆっくり", "のんびり", "ちゃんと",
    # Common hiragana nouns
    "もの", "こと", "とき", "ところ", "ひと", "うち",
    # Common auxiliaries (anchor so adjacent particles are cleanly split)
    "できる", "できた", "できない",
    "わかる", "わかった", "わからない",
})

# Sentence-final particles safe to strip from the tail of a hiragana token.
# Only ね / よ — both are virtually never the final mora of a content word.
_PARTICLES_FINAL: frozenset[str] = frozenset("ねよ")


# ---------------------------------------------------------------------------
# Grammar-aware splitting of unrecognised hiragana runs
# ---------------------------------------------------------------------------

# Auxiliary / inflectional morphemes that attach to the END of a verb or
# adjective. When found contiguously at the tail of a hiragana run that has no
# dictionary anchor, they are peeled off so the content stem ahead of them is
# isolated. Adjective conjugation endings (く / かった / しい …) are deliberately
# EXCLUDED — they must stay attached to their stem.
_GRAMMAR_TAIL_MORPHEMES: frozenset[str] = frozenset({
    "みたい", "らしい", "そう", "よう", "です", "ます", "ました", "ません",
    "でした", "でしょう", "ましょう", "ください",
    "ている", "ていた", "ていて", "ています", "てる", "てた", "てて",
    "てくる", "てきた", "ていく", "ちゃう", "じゃう", "ちゃった", "じゃった",
    "られる", "させる", "れる", "せる",
    "なっ", "なる", "なら", "なり", "なれ",
    "ない", "なく", "なくて", "なかった",
    "たい", "たく", "たかった",
    "けど", "から", "ので", "のに", "たら", "ても", "でも", "ながら", "って",
})

# Adjective conjugation endings, longest first, paired with the minimum stem
# length required before the ending.
_ADJ_ENDINGS: tuple[tuple[str, int], ...] = (
    ("くなかった", 1), ("くない", 1), ("かった", 1), ("ければ", 1),
    ("くて", 1), ("しい", 1), ("く", 2), ("い", 2),
)


def _adjective_lemma(s: str) -> str | None:
    """Return the い-base lemma if ``s`` is an adjective conjugation, else None."""
    if len(s) < 3:
        return None
    for ending, stem_min in _ADJ_ENDINGS:
        if s.endswith(ending) and len(s) - len(ending) >= stem_min:
            if ending == "い":
                return s
            stem = s[: -len(ending)]
            return stem + ("しい" if ending == "しい" else "い")
    return None


def _grammar_split(text: str) -> list[tuple[str, str, str]]:
    """Split an unrecognised hiragana run into ``[content, grammar-tail]``.

    Peels known auxiliary morphemes from the right; the surviving head is the
    content stem. When the head is an adjective conjugation it is labelled
    ``形容詞-一般`` with its い-base as ``dictionary_form``.

    Returns ``(surface, pos, dictionary_form)`` triples — a single unchanged
    element when nothing can be peeled.
    """
    n = len(text)
    if n < 4:
        return [(text, "助詞", text)]

    end = n
    while end >= 2:
        matched = 0
        for length in range(min(5, end), 1, -1):
            if text[end - length:end] in _GRAMMAR_TAIL_MORPHEMES:
                matched = length
                break
        if not matched:
            break
        end -= matched

    if end == n:
        # nothing peeled — relabel the whole run if it is an adjective
        lemma = _adjective_lemma(text)
        return [(text, "形容詞-一般", lemma)] if lemma else [(text, "助詞", text)]
    if end < 2:
        return [(text, "助詞", text)]

    head, tail = text[:end], text[end:]
    lemma = _adjective_lemma(head)
    head_seg = (head, "形容詞-一般", lemma) if lemma else (head, "助詞", head)
    return [head_seg, (tail, "助詞", tail)]


def _build_known_hiragana(bundle: DictionaryBundle) -> frozenset[str]:
    """Merge bundle all-hiragana surfaces with the hardcoded word list.

    Deterministic from the bundle → built once and cached on it.
    """
    cached = bundle._cache.get("known_hiragana")
    if cached is not None:
        return cached
    words: set[str] = set(_HIRAGANA_KNOWN_WORDS)
    for e in bundle.emotion:
        if len(e.surface) >= 2 and all(0x3040 <= ord(c) <= 0x309F for c in e.surface):
            words.add(e.surface)
    for s in bundle.slang:
        if len(s.surface) >= 2 and all(0x3040 <= ord(c) <= 0x309F for c in s.surface):
            words.add(s.surface)
    result = frozenset(words)
    bundle._cache["known_hiragana"] = result
    return result


def _reduplication_length(surface: str, pos: int) -> int:
    """Length of an XYXY / XYZXYZ reduplication starting at ``pos`` (0 if none).

    Japanese onomatopoeia overwhelmingly takes the reduplicated form
    (しとしと / もやもや / おもいおもい). Recognising the pattern keeps such
    runs intact as one word even when absent from the lexicon. The 3-char
    unit is tried first so おもいおもい does not split as お|もいもい.
    Same-char pairs (ののの…) are excluded — those are fillers, not words.
    """
    n = len(surface)
    if pos + 6 <= n and surface[pos:pos + 3] == surface[pos + 3:pos + 6] \
            and len(set(surface[pos:pos + 3])) > 1:
        return 6
    if pos + 4 <= n and surface[pos:pos + 2] == surface[pos + 2:pos + 4] \
            and surface[pos] != surface[pos + 1]:
        return 4
    return 0


def _find_hiragana_anchors(
    surface: str, known_words: frozenset[str]
) -> list[tuple[int, int]]:
    """Left-to-right longest-match scan for known-word / reduplication spans."""
    n = len(surface)
    claimed = bytearray(n)
    spans: list[tuple[int, int]] = []
    pos = 0
    while pos < n:
        best = 0
        for length in range(min(10, n - pos), 1, -1):
            if surface[pos:pos + length] in known_words and not any(claimed[pos:pos + length]):
                best = length
                break
        if not best:
            best = _reduplication_length(surface, pos)
        if best:
            end = pos + best
            spans.append((pos, end))
            for i in range(pos, end):
                claimed[i] = 1
            pos = end
        else:
            pos += 1
    return spans


def _split_hiragana_gap(gap: str) -> list[str]:
    """Break inter-anchor gap text into known-words and particles.

    Particles are consumed only when unambiguous:
    - 2-char compound particles take priority over 1-char.
    - A 1-char particle is NOT consumed when followed by a small-form kana
      (っゃゅょ…) — that signals a content-word mora, not a particle boundary
      (e.g. "や" in "やっぱり" must not be split off as a particle).
    - Unknown content that cannot be classified is kept intact as a single
      segment rather than being forced through further heuristics.
    """
    if not gap:
        return []
    result: list[str] = []
    pos = 0
    n = len(gap)
    while pos < n:
        # Try known word (length ≥ 2, longest first) — catches adverbs/pronouns
        best_kw = 0
        for length in range(min(6, n - pos), 1, -1):
            if gap[pos:pos + length] in _HIRAGANA_KNOWN_WORDS:
                best_kw = length
                break
        if best_kw:
            result.append(gap[pos:pos + best_kw])
            pos += best_kw
            continue
        # Try 2-char compound particle
        if pos + 2 <= n and gap[pos:pos + 2] in _PARTICLES_2:
            result.append(gap[pos:pos + 2])
            pos += 2
            continue
        # Try 1-char particle — small-kana guard prevents splitting "やっ…"
        if gap[pos] in _PARTICLES_1 and not (
            pos + 1 < n and gap[pos + 1] in _SMALL_KANA
        ):
            result.append(gap[pos])
            pos += 1
            continue
        # Unknown content: emit the rest as one segment and stop
        result.append(gap[pos:])
        break
    return result


def _split_hiragana_tail(tail: str) -> list[str]:
    """Strip a trailing sentence-final particle (ね / よ) from a tail segment."""
    if len(tail) >= 2 and tail[-1] in _PARTICLES_FINAL:
        return [tail[:-1], tail[-1]]
    return [tail]


def _segment_hiragana_surface(
    surface: str, known_words: frozenset[str]
) -> list[tuple[str, str, str]]:
    """Segment a pure-hiragana surface into ``(surface, pos, dictionary_form)``.

    Known content words act as split anchors; gaps between them are split into
    particles; an unrecognised run (or a long trailing remainder) is handed to
    the grammar splitter. Returns a single unchanged triple when no
    segmentation applies.
    """
    if len(surface) < 2:
        return [(surface, "助詞", surface)]
    spans = _find_hiragana_anchors(surface, known_words)
    if not spans:
        return _grammar_split(surface)

    result: list[tuple[str, str, str]] = []
    prev_end = 0
    for start, end in spans:
        if start > prev_end:
            result.extend(
                (s, "助詞", s) for s in _split_hiragana_gap(surface[prev_end:start])
            )
        anchor = surface[start:end]
        result.append((anchor, "助詞", anchor))
        prev_end = end

    tail = surface[prev_end:]
    if tail:
        if len(tail) >= 4:
            result.extend(_grammar_split(tail))
        else:
            result.extend((s, "助詞", s) for s in _split_hiragana_tail(tail))

    return [t for t in result if t[0]]


# Sokuon-emphasised onomatopoeia: ワ[ッ]クワク → base form ワクワク.
_EMPHATIC_REDUP_RE = re.compile(r"^([ぁ-ゖァ-ヶ])[っッ]([ぁ-ゖァ-ヶ])\1\2$")


def fold_emphatic_reduplication(tokens: list[Token]) -> list[Token]:
    """Set dictionary_form for sokuon-emphasised reduplications (in place).

    ワックワク → ワクワク / いっらいら → いらいら. Only dictionary_form is
    rewritten — the surface stays as typed — so the emotion detector's
    dictionary_form pass matches the base form against the lexicon. Runs
    BEFORE split_hiragana_tokens, which leaves rewritten tokens intact.
    """
    for tok in tokens:
        m = _EMPHATIC_REDUP_RE.match(tok.surface)
        if m:
            tok.dictionary_form = (m.group(1) + m.group(2)) * 2
    return tokens


def split_hiragana_tokens(
    tokens: list[Token],
    bundle: DictionaryBundle,
) -> list[Token]:
    """Segment long hiragana tokens at particle / known-word boundaries.

    Called AFTER ``merge_keep_as_unit`` (keep_as_unit surfaces already
    protected) and BEFORE ``heuristic_proper_noun_merge``.

    Pure-hiragana tokens (Karuizawa pos == 助詞) of length ≥ 2 are segmented
    using known content words from emotion.csv / slang.csv as anchors, plus
    a hardcoded set of pronouns, demonstratives, and common adverbs.

    Tokens whose surface is already a known word are left untouched.
    """
    known_words = _build_known_hiragana(bundle)

    result: list[Token] = []
    for tok in tokens:
        if tok.pos != "助詞" or len(tok.surface) < 2:
            result.append(tok)
            continue
        if tok.surface in known_words:
            result.append(tok)
            continue
        if tok.dictionary_form and tok.dictionary_form != tok.surface:
            # Already lemmatized upstream (e.g. fold_emphatic_reduplication) —
            # the run is a recognised word; don't segment it.
            result.append(tok)
            continue

        segments = _segment_hiragana_surface(tok.surface, known_words)
        if len(segments) == 1:
            seg, pos, dform = segments[0]
            if pos == tok.pos:
                result.append(tok)
            else:
                # grammar splitter reclassified the whole run (e.g. 形容詞)
                result.append(Token(
                    id=tok.id,
                    surface=seg,
                    normalized=seg,
                    dictionary_form=dform,
                    reading=None,
                    pos=pos,
                    begin=tok.begin,
                    end=tok.end,
                    unknown=tok.unknown,
                ))
            continue

        offset = tok.begin
        for seg, pos, dform in segments:
            seg_end = offset + len(seg)
            result.append(Token(
                id=tok.id,
                surface=seg,
                normalized=seg,
                dictionary_form=dform,
                reading=None,
                pos=pos,
                begin=offset,
                end=seg_end,
                unknown=tok.unknown,
            ))
            offset = seg_end

    for new_id, t in enumerate(result):
        t.id = new_id
    return result


def merge_keep_as_unit(
    tokens: list[Token],
    normalized_text: str,
    bundle: DictionaryBundle,
) -> list[Token]:
    """Merge backend tokens that fall inside a ``keep_as_unit`` surface span.

    When a span start or end falls mid-token (as happens with Karuizawa's
    character-category splitting), the overlapping token is first split at that
    boundary, then the resulting pieces are merged as normal. Single tokens that
    already cover the span exactly are relabeled to ``_MERGED_POS``.

    Token ids are renumbered contiguously. ``begin`` / ``end`` offsets are
    preserved.
    """
    if not tokens or not normalized_text:
        return tokens

    kau_surface_pos = bundle.keep_as_unit_surfaces()  # {surface: merged_pos}
    # Only surfaces >= 2 chars can ever be split across tokens. The sorted
    # list + its Aho-Corasick matcher are deterministic → cached on the bundle.
    kau_scan = bundle._cache.get("kau_scan")
    if kau_scan is None:
        surfaces = sorted((s for s in kau_surface_pos if len(s) >= 2), key=lambda s: -len(s))
        kau_scan = (surfaces, SurfaceMatcher(surfaces) if surfaces else None)
        bundle._cache["kau_scan"] = kau_scan
    surfaces, matcher = kau_scan
    if not surfaces:
        return tokens

    # Find non-overlapping keep_as_unit spans (longest-match first — the
    # (rank, pos) match order reproduces the previous per-surface find loops).
    claimed = bytearray(len(normalized_text))
    spans: list[tuple[int, int, str]] = []
    for rank, pos, end in matcher.find_all(normalized_text):
        if not any(claimed[pos:end]):
            spans.append((pos, end, surfaces[rank]))
            for i in range(pos, end):
                claimed[i] = 1

    if not spans:
        return tokens

    # Split tokens at span boundaries so every span aligns with token edges.
    expanded = _split_at_boundaries(tokens, spans, normalized_text)

    span_by_begin = {b: (b, e, s) for (b, e, s) in spans}

    result: list[Token] = []
    new_id = 0
    i = 0
    n = len(expanded)
    while i < n:
        tok = expanded[i]
        span = span_by_begin.get(tok.begin)
        if span is not None:
            mb, me, msurf = span
            # Collect all tokens fully contained in [mb, me)
            covered: list[Token] = []
            j = i
            while j < n and expanded[j].begin >= mb and expanded[j].end <= me:
                covered.append(expanded[j])
                j += 1
            # Merge if the span is fully covered by ≥1 token(s) ending at me.
            if covered and covered[-1].end == me:
                result.append(
                    Token(
                        id=new_id,
                        surface=msurf,
                        normalized=msurf,
                        dictionary_form=msurf,
                        reading=None,
                        pos=kau_surface_pos.get(msurf, _MERGED_POS),
                        begin=mb,
                        end=me,
                        unknown=False,
                    )
                )
                new_id += 1
                i = j
                continue

        result.append(
            Token(
                id=new_id,
                surface=tok.surface,
                normalized=tok.normalized,
                dictionary_form=tok.dictionary_form,
                reading=tok.reading,
                pos=tok.pos,
                begin=tok.begin,
                end=tok.end,
                unknown=tok.unknown,
            )
        )
        new_id += 1
        i += 1

    return result


# ---------------------------------------------------------------------------
# Okurigana compound merge (runs AFTER heuristic_proper_noun_merge)
# ---------------------------------------------------------------------------

# Okurigana that may close a compound produced by the sandwich merge
# (締め切 + り).  Deliberately excludes verb-inflection endings (た/て/ろ …)
# so plain verb stems (走 + り) are never absorbed.
_TRAILING_OKURIGANA: frozenset[str] = frozenset("りめいえみけきげしせち")

# 2-char okurigana tails that close a compound (打ち合 + わせ → 打ち合わせ).
_TRAILING_OKURIGANA_2: frozenset[str] = frozenset({"わせ", "あい", "がえ"})

# Adjective stems: KANJI + い forms an i-adjective (良い/近い/高い …), which
# refine_verb_adjective_pos must assemble — the sandwich rule stays out.
# Without this guard 良+い+天気 would wrongly fuse into one noun 良い天気.
_ADJ_STEMS: frozenset[str] = frozenset(
    "良悪近遠高安低強弱早速遅古濃薄深浅広狭長短多軽重丸白黒赤青若旨"
    "細太固硬堅暗偉凄酷淡荒粗緩鋭鈍賢幼熱暑寒痛甘辛苦渋眠怖無憎醜聡"
) | frozenset({"上手"})


def _has_kanji(s: str) -> bool:
    return any(
        0x4E00 <= ord(c) <= 0x9FFF or 0x3400 <= ord(c) <= 0x4DBF for c in s
    )


def merge_okurigana_compounds(tokens: list[Token]) -> list[Token]:
    """Merge 交ぜ書き compound nouns split at okurigana boundaries.

    Karuizawa splits by character category, so KANJI+HIRAGANA+KANJI compound
    nouns fragment into e.g. 締|め|切|り — the 1-char hiragana stranded as
    助詞 even though め/り are not particles.  Runs after
    ``heuristic_proper_noun_merge`` (which has already isolated trailing
    particles: りが → り + が).  Two conservative rules:

    1. Sandwich: KANJI noun + single non-particle hiragana + KANJI noun
       → one 名詞-普通名詞-一般 token (締め切 / 思い出 / 行き先 / 真っ白).
       Genuine particles (_PARTICLES_1: は/が/の/に …) never trigger it, and
       adjective stems (_ADJ_STEMS: 良+い+天気 …) are left for
       ``refine_verb_adjective_pos`` to assemble as adjectives.
    2. Trailing: a compound produced by rule 1 may absorb ONE following
       okurigana from a closed set (締め切 + り → 締め切り).  Plain KANJI
       nouns do not absorb trailing hiragana, so verb stems stay intact.
    """
    if not tokens:
        return tokens

    result: list[Token] = []
    compound_flags: list[bool] = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        is_single = len(tok.surface) == 1
        if (
            tok.pos == "助詞"
            and _is_all_hiragana(tok.surface)
            and (
                (is_single and tok.surface not in _PARTICLES_1)
                or tok.surface in _TRAILING_OKURIGANA_2
            )
            and result
            and result[-1].end == tok.begin
        ):
            prev = result[-1]
            prev_ok = (
                prev.pos.startswith("名詞-普通名詞")
                and _has_kanji(prev.surface)
                and not (tok.surface == "い" and prev.surface in _ADJ_STEMS)
            )
            nxt = tokens[i + 1] if i + 1 < n else None
            if (
                is_single
                and prev_ok
                and nxt is not None
                and tok.end == nxt.begin
                and nxt.pos.startswith("名詞-普通名詞")
                and _has_kanji(nxt.surface)
            ):
                # Rule 1: sandwich merge  prev + okurigana + next
                result.pop()
                compound_flags.pop()
                surf = prev.surface + tok.surface + nxt.surface
                result.append(
                    Token(
                        id=prev.id,
                        surface=surf,
                        normalized=surf,
                        dictionary_form=surf,
                        reading=None,
                        pos="名詞-普通名詞-一般",
                        begin=prev.begin,
                        end=nxt.end,
                        unknown=False,
                    )
                )
                compound_flags.append(True)
                i += 2
                continue
            if compound_flags[-1] and (
                tok.surface in _TRAILING_OKURIGANA
                or tok.surface in _TRAILING_OKURIGANA_2
            ):
                # Rule 2: close the compound with its final okurigana
                prev = result.pop()
                compound_flags.pop()
                surf = prev.surface + tok.surface
                result.append(
                    Token(
                        id=prev.id,
                        surface=surf,
                        normalized=surf,
                        dictionary_form=surf,
                        reading=None,
                        pos="名詞-普通名詞-一般",
                        begin=prev.begin,
                        end=tok.end,
                        unknown=False,
                    )
                )
                compound_flags.append(True)
                i += 1
                continue
        result.append(tok)
        compound_flags.append(False)
        i += 1

    for new_id, t in enumerate(result):
        t.id = new_id
    return result


# ---------------------------------------------------------------------------
# Heuristic proper-noun merge (runs AFTER merge_keep_as_unit)
# ---------------------------------------------------------------------------


def heuristic_proper_noun_merge(
    tokens: list[Token],
    text: str,
) -> list[Token]:
    """Best-effort merge for KANJI + HIRAGANA proper-noun compounds.

    Addresses the Karuizawa tokenizer's inability to recognize cross-class
    proper nouns not registered in entity.csv (e.g. 坊っちゃん).

    Rules applied for each HIRAGANA token immediately following a nominal token:

    1. Strip a trailing particle (2-char _PARTICLES_2 first, then 1-char
       _PARTICLES_1) to isolate it.
    2. If the remaining HIRAGANA body begins with a small-form kana (っ ゃ ゅ ょ
       etc.), it cannot start an independent Japanese word → merge with the
       preceding KANJI token into 名詞-固有名詞-一般.
    3. If no merge: emit body + particle as separate 助詞 tokens — still an
       improvement over the original single swallowed token.
    """
    if not tokens:
        return tokens

    result: list[Token] = []
    for tok in tokens:
        prev = result[-1] if result else None
        prev_is_adjacent_nominal = (
            prev is not None
            and "名詞" in prev.pos
            and prev.end == tok.begin
        )

        if tok.pos != "助詞" or not prev_is_adjacent_nominal or len(tok.surface) < 2:
            result.append(tok)
            continue

        body, particle = _strip_trailing_particle(tok.surface)

        is_grammar_verb = len(body) >= 2 and body[:2] in _GRAMMAR_VERB_PREFIXES
        if body and body[0] in _SMALL_KANA and not is_grammar_verb:
            # Merge preceding nominal + HIRAGANA body → proper-noun token
            prev_tok = result.pop()
            new_surf = prev_tok.surface + body
            new_end = tok.begin + len(body)
            result.append(
                Token(
                    id=prev_tok.id,
                    surface=new_surf,
                    normalized=new_surf,
                    dictionary_form=new_surf,
                    reading=None,
                    pos="名詞-固有名詞-一般",
                    begin=prev_tok.begin,
                    end=new_end,
                    unknown=False,
                )
            )
            if particle:
                result.append(
                    Token(
                        id=prev_tok.id + 1,
                        surface=particle,
                        normalized=particle,
                        dictionary_form=particle,
                        reading=None,
                        pos="助詞",
                        begin=new_end,
                        end=tok.end,
                        unknown=False,
                    )
                )
        elif particle:
            # No merge — just isolate the trailing particle
            body_end = tok.end - len(particle)
            result.append(
                Token(
                    id=tok.id,
                    surface=body,
                    normalized=body,
                    dictionary_form=body,
                    reading=None,
                    pos="助詞",
                    begin=tok.begin,
                    end=body_end,
                    unknown=tok.unknown,
                )
            )
            result.append(
                Token(
                    id=tok.id + 1,
                    surface=particle,
                    normalized=particle,
                    dictionary_form=particle,
                    reading=None,
                    pos="助詞",
                    begin=body_end,
                    end=tok.end,
                    unknown=False,
                )
            )
        else:
            # No small-kana merge, no trailing particle.
            # Try stripping a leading particle (は/が/を/に/も/へ/から…).
            leading_p, body_core = _strip_leading_particle(body)
            if leading_p and body_core and body_core not in _VERB_NEG_TAILS:
                leading_end = tok.begin + len(leading_p)
                result.append(
                    Token(
                        id=tok.id,
                        surface=leading_p,
                        normalized=leading_p,
                        dictionary_form=leading_p,
                        reading=None,
                        pos="助詞",
                        begin=tok.begin,
                        end=leading_end,
                        unknown=False,
                    )
                )
                result.append(
                    Token(
                        id=tok.id + 1,
                        surface=body_core,
                        normalized=body_core,
                        dictionary_form=body_core,
                        reading=None,
                        pos=tok.pos,
                        begin=leading_end,
                        end=tok.end,
                        unknown=tok.unknown,
                    )
                )
            else:
                result.append(tok)

    # Renumber ids contiguously
    for new_id, t in enumerate(result):
        t.id = new_id
    return result


# ---------------------------------------------------------------------------
# Verb / adjective POS refinement (runs LAST in the pipeline)
# ---------------------------------------------------------------------------

# HIRAGANA blocks that are particles (NOT verb/adjective okurigana).
_PARTICLE_SURFACES: frozenset[str] = frozenset({
    "は", "が", "を", "に", "で", "と", "へ", "も", "や", "か", "の",
    "ね", "よ", "さ", "わ", "ぞ", "ぜ", "な", "こそ",
    "から", "まで", "より", "など", "でも", "しか", "だけ", "ほど",
    "くらい", "ぐらい", "ばかり", "ながら", "けれど", "のに", "ので",
    "とか", "には", "では", "へは", "とは", "からは", "までは",
})

# Adjective conjugation tails (checked before verb).
_ADJ_TAILS: tuple[str, ...] = ("しい", "かった", "くて", "ければ", "くない", "くなかった")

# Verb conjugation tails (multi-char) and final chars (single-char).
_VERB_TAILS: tuple[str, ...] = (
    "ない", "なかった", "なくて", "ます", "ました", "ません", "ましょう",
    "れる", "られる", "せる", "させる", "たい", "たく", "たかった",
    "よう", "ている", "ていた", "ていて", "てきた", "ちゃう", "じゃう",
)
_VERB_FINAL_CHARS: frozenset[str] = frozenset("るたてだでうくぐすつぶむぬ")

# する (サ変) conjugations. A noun + する is a サ変動詞 whose noun carries the
# meaning/emotion (ワクワクする / 緊張する 等)。結合すると感情語の surface 一致が
# 壊れるため、これらの okurigana では結合しない（名詞を独立トークンとして残す）。
_SURU_FORMS: frozenset[str] = frozenset({
    "する", "した", "して", "してる", "してた", "してて", "します",
    "しました", "しません", "しよう", "すれば", "された", "される",
    "させる", "させた", "できる", "できた", "できない", "できて", "できず",
})


# Particle characters that never begin a verb/adjective okurigana block.
# A hiragana block starting with one of these is "particle + rest" (e.g.
# 物価高 + で + やりきれない), so the preceding noun must NOT be merged into it.
# か / や are intentionally EXCLUDED: they are common verb okurigana initials
# (分かる / 預かる, 冷やす / 増やす), so rejecting them would block legitimate
# 名詞→動詞 補正.
_LEADING_PARTICLE_CHARS: frozenset[str] = frozenset("はがをにへもとので")


def _is_all_hiragana(s: str) -> bool:
    return bool(s) and all(0x3040 <= ord(c) <= 0x309F for c in s)


def _classify_okurigana(h: str) -> str:
    """Classify a HIRAGANA okurigana block: 'verb' / 'adj' / '' (neither)."""
    if not h or h in _PARTICLE_SURFACES or h in _SURU_FORMS:
        return ""
    # A block starting with a particle (で / に / は …) is not okurigana —
    # it delimits the noun from what follows. Do not merge.
    if h[0] in _LEADING_PARTICLE_CHARS:
        return ""
    # Adjective negation (高くない) ends in ない but conjugates through く.
    if h.endswith(("くない", "くなかった")):
        return "adj"
    # Verb negation (分からなくて) ends in な-row forms — NOT an adjective even
    # though なくて ends in the adjective て-form ending くて.
    if h.endswith(("ない", "なく", "なくて", "なかった")):
        return "verb"
    if h == "い" or h.endswith(_ADJ_TAILS):
        return "adj"
    if h.endswith(_VERB_TAILS) or h[-1] in _VERB_FINAL_CHARS:
        return "verb"
    return ""


def refine_verb_adjective_pos(
    tokens: list[Token], bundle: DictionaryBundle
) -> list[Token]:
    """Re-label default-noun tokens that are actually verbs / adjectives.

    Karuizawa assigns POS purely by character category, so a verb stem such as
    走 (in 走る) or an adjective stem 美味 (in 美味しい) is tagged 名詞. This
    pass detects a ``名詞-普通名詞-一般`` token immediately followed by a
    contiguous HIRAGANA okurigana block whose form indicates a verb or
    adjective conjugation, merges the pair, and assigns ``動詞-一般`` /
    ``形容詞-一般``.

    Intentionally conservative:

    * Particles (を / に / で …) and ambiguous okurigana (e.g. 祭り の り) are
      left untouched.
    * A token whose surface is a **known dictionary word** (emotion / slang /
      entity) is never merged — merging would destroy the surface match the
      semantic layer relies on (e.g. ワクワク + する, 満足 + している).
    """
    if not tokens:
        return tokens

    # Surfaces that must stay intact so the semantic layer can match them.
    # Deterministic from the bundle → built once and cached on it.
    protected: set[str] | None = bundle._cache.get("refine_protected")
    if protected is None:
        protected = set()
        protected.update(e.surface for e in bundle.emotion)
        protected.update(e.surface for e in bundle.external_emotion)
        protected.update(s.surface for s in bundle.slang)
        protected.update(e.surface for e in bundle.entity)
        bundle._cache["refine_protected"] = protected

    result: list[Token] = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if (
            i + 1 < n
            and tok.pos == "名詞-普通名詞-一般"
            and tok.surface not in protected
            and tok.end == tokens[i + 1].begin
            and _is_all_hiragana(tokens[i + 1].surface)
        ):
            nxt = tokens[i + 1]
            kind = _classify_okurigana(nxt.surface)
            if kind:
                new_surf = tok.surface + nxt.surface
                # Adjectives get their い-base lemma as dictionary_form
                # (嬉しくない → 嬉しい, 楽しかった → 楽しい) so the semantic
                # layer can match conjugated forms against the lexicon.
                dform = new_surf
                if kind == "adj":
                    dform = _adjective_lemma(new_surf) or new_surf
                result.append(
                    Token(
                        id=tok.id,
                        surface=new_surf,
                        normalized=new_surf,
                        dictionary_form=dform,
                        reading=None,
                        pos="動詞-一般" if kind == "verb" else "形容詞-一般",
                        begin=tok.begin,
                        end=nxt.end,
                        unknown=False,
                    )
                )
                i += 2
                continue
        result.append(tok)
        i += 1

    for new_id, t in enumerate(result):
        t.id = new_id
    return result
