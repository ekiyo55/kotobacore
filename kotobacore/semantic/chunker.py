"""SemanticChunker.

Per 04_内部設計書 §12, 06_API §10.2. Generates semantic chunks from tokens +
dictionary, applying keep_as_unit rules first and then POS-based grouping
(e.g. consecutive nouns → compound_noun, noun + adjective → 評価表現).

The high-level approach is span-based:

1. Scan the normalized text for dictionary surfaces (longest-match, non-overlap)
   → produces dictionary-driven chunks
2. Fill unclaimed gaps with token-grouped chunks (compound_noun, etc.)
3. Map each chunk to the list of token_ids that fall within its span
"""

from __future__ import annotations

from dataclasses import dataclass

from kotobacore.dictionary import DictionaryBundle, EmotionEntry, EntityEntry, SlangEntry
from kotobacore.schema import SemanticChunk, Token


@dataclass
class _Match:
    start: int  # char offset in normalized text
    end: int  # exclusive
    surface: str
    chunk_type: str
    entry_kind: str  # "entity" | "slang" | "emotion"
    intensity: float


# ---------------------------------------------------------------------------
# Span resolution
# ---------------------------------------------------------------------------


def _entity_chunk_type(e: EntityEntry) -> str:
    return {
        "API": "service",
        "SERVICE": "service",
        "PRODUCT": "service",
        "TECHNOLOGY": "topic",
        "TOPIC": "topic",
        "MODEL": "service",
    }.get(e.type, "entity")


def _emotion_chunk_type(e: EmotionEntry) -> str:
    if e.polarity == "negative":
        return "complaint"
    if e.polarity == "positive":
        return "praise"
    return "slang_emotion"


def _slang_chunk_type(_e: SlangEntry) -> str:
    return "slang_emotion"


def _collect_candidates(bundle: DictionaryBundle) -> list[_Match]:
    """Build candidate match templates (entity/slang/emotion surfaces).

    Deterministic from the bundle, so the result is built once and cached.
    The scan never mutates these templates (it emits fresh _Match objects),
    so sharing the cached list across calls is safe.
    """
    cached = bundle._cache.get("chunk_candidates")
    if cached is not None:
        return cached

    candidates: list[_Match] = []

    for e in bundle.entity:
        if not e.surface:
            continue
        candidates.append(
            _Match(0, 0, e.surface, _entity_chunk_type(e), "entity", 0.9)
        )
        # Aliases (e.g. 東京 for 東京都) are also valid entity surfaces.
        for alias in e.aliases:
            if alias:
                candidates.append(
                    _Match(0, 0, alias, _entity_chunk_type(e), "entity", 0.85)
                )

    for e in bundle.slang:
        if not e.surface:
            continue
        candidates.append(
            _Match(0, 0, e.surface, _slang_chunk_type(e), "slang", e.intensity)
        )

    for e in bundle.emotion:
        if not e.surface:
            continue
        # Single kanji/kana are handled by build_semantic_tokens.
        # Single emojis (U+2600+) are expressive enough to be standalone chunks.
        _single_emoji = len(e.surface) == 1 and ord(e.surface[0]) >= 0x2600
        if len(e.surface) >= 2 or _single_emoji:
            candidates.append(
                _Match(0, 0, e.surface, _emotion_chunk_type(e), "emotion", e.intensity)
            )

    # Longest surface first (greedy longest-match).
    candidates.sort(key=lambda c: -len(c.surface))
    bundle._cache["chunk_candidates"] = candidates
    return candidates


def _scan_dictionary_matches(
    text: str, bundle: DictionaryBundle, tokens: list[Token]
) -> list[_Match]:
    """Greedy non-overlapping longest-match scan over ``text``.

    A match is accepted only when its character span aligns with token
    boundaries (start = some token's begin AND end = some token's end). This
    prevents a short dictionary surface from matching *inside* a larger token —
    e.g. the brand alias "AP" matching within the "API" token.
    """
    if not text or not tokens:
        return []
    token_begins = {t.begin for t in tokens}
    token_ends = {t.end for t in tokens}
    candidates = _collect_candidates(bundle)
    claimed = bytearray(len(text))  # 0 = free, 1 = claimed
    matches: list[_Match] = []

    for cand in candidates:
        surf = cand.surface
        n = len(surf)
        if n == 0:
            continue
        start = 0
        while True:
            pos = text.find(surf, start)
            if pos < 0:
                break
            end_pos = pos + n
            if (
                pos in token_begins
                and end_pos in token_ends
                and not any(claimed[pos:end_pos])
            ):
                matches.append(
                    _Match(pos, end_pos, surf, cand.chunk_type, cand.entry_kind, cand.intensity)
                )
                for i in range(pos, end_pos):
                    claimed[i] = 1
            start = pos + 1

    # dictionary_form pass — match a token's lemma (set by the Token
    # Normalizer's grammar splitter, e.g. おかしく → おかしい) against the
    # candidate surfaces, so conjugated forms become chunks too.
    cand_by_surface: dict[str, _Match] = {}
    for cand in candidates:
        cand_by_surface.setdefault(cand.surface, cand)
    for tok in tokens:
        df = tok.dictionary_form
        if not df or df == tok.surface or df not in cand_by_surface:
            continue
        if any(claimed[tok.begin:tok.end]):
            continue
        cand = cand_by_surface[df]
        matches.append(
            _Match(tok.begin, tok.end, tok.surface, cand.chunk_type,
                   cand.entry_kind, cand.intensity)
        )
        for i in range(tok.begin, tok.end):
            claimed[i] = 1

    matches.sort(key=lambda m: m.start)
    return matches


# ---------------------------------------------------------------------------
# POS-based gap chunks
# ---------------------------------------------------------------------------


def _is_noun(tok: Token) -> bool:
    return "名詞" in tok.pos and "代名詞" not in tok.pos


def _is_proper_noun(tok: Token) -> bool:
    return "固有名詞" in tok.pos


def _is_adjective(tok: Token) -> bool:
    return "形容詞" in tok.pos


def _tokens_in_span(tokens: list[Token], start: int, end: int) -> list[Token]:
    return [t for t in tokens if t.begin >= start and t.end <= end]


def _is_stopword_token(tok: Token, stopwords: set[str], sw_prefixes: set[str]) -> bool:
    return tok.surface in stopwords or any(tok.surface.startswith(sw) for sw in sw_prefixes)


def _pos_based_chunks(
    tokens: list[Token],
    gap_start: int,
    gap_end: int,
    next_chunk_id: int,
    stopwords: set[str] = frozenset(),
    sw_prefixes: set[str] = frozenset(),
) -> list[SemanticChunk]:
    """Group tokens in [gap_start, gap_end) into POS-driven chunks.

    Rules (v0.1):
      - Consecutive 名詞 (or 固有名詞) → compound_noun
      - 名詞 + 形容詞 contiguous → praise/complaint candidate (returned as
        chunk_type="topic" with low score; emotion layer adjusts later)
      - Standalone 形容詞 ≥ 3 chars → emotion chunk (handled by single-token
        emotion dict matching upstream)
    Stopword tokens are skipped and break any ongoing noun run.
    """
    relevant = [t for t in tokens if t.begin >= gap_start and t.end <= gap_end]
    chunks: list[SemanticChunk] = []
    cid = next_chunk_id
    i = 0
    n = len(relevant)
    while i < n:
        tok = relevant[i]
        if _is_stopword_token(tok, stopwords, sw_prefixes):
            i += 1
            continue
        if _is_noun(tok):
            # Run of consecutive nouns (stop at stopword tokens)
            run_start = i
            while (
                i + 1 < n
                and _is_noun(relevant[i + 1])
                and relevant[i + 1].begin == relevant[i].end
                and not _is_stopword_token(relevant[i + 1], stopwords, sw_prefixes)
            ):
                i += 1
            run = relevant[run_start : i + 1]
            text = "".join(t.surface for t in run)
            if len(run) >= 2:
                chunks.append(
                    SemanticChunk(
                        id=cid,
                        text=text,
                        type="compound_noun",
                        token_ids=[t.id for t in run],
                        score=0.7,
                    )
                )
                cid += 1
            elif _is_proper_noun(run[0]) or len(text) >= 3:
                # Single proper noun, or a single noun of 3+ chars
                # (e.g. 物価高 / チームメンバー) → topic chunk
                chunks.append(
                    SemanticChunk(
                        id=cid,
                        text=text,
                        type="topic",
                        token_ids=[t.id for t in run],
                        score=0.6,
                    )
                )
                cid += 1
            i += 1
            continue
        i += 1

    return chunks


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def chunk(
    normalized_text: str,
    tokens: list[Token],
    bundle: DictionaryBundle,
) -> list[SemanticChunk]:
    """Produce the SemanticChunk list for ``normalized_text``.

    Token positions are read from ``Token.begin / end``. The chunker assumes
    these positions are aligned with ``normalized_text`` (i.e. the tokenizer
    was fed the normalized text — the Analyzer guarantees this).
    """
    if not normalized_text or not tokens:
        return []

    matches = _scan_dictionary_matches(normalized_text, bundle, tokens)
    stopwords = bundle.stopword_set()
    sw_prefixes = {sw for sw in stopwords if len(sw) >= 2}

    chunks: list[SemanticChunk] = []
    cursor = 0
    cid = 0

    for m in matches:
        # Fill the gap before this match using POS chunks
        if m.start > cursor:
            gap_chunks = _pos_based_chunks(tokens, cursor, m.start, cid, stopwords, sw_prefixes)
            chunks.extend(gap_chunks)
            cid += len(gap_chunks)

        # Build the dictionary-driven chunk
        token_ids = [t.id for t in _tokens_in_span(tokens, m.start, m.end)]
        # If the dictionary surface doesn't align cleanly with token boundaries
        # (e.g. covers part of a token), include all overlapping tokens.
        if not token_ids:
            token_ids = [
                t.id
                for t in tokens
                if (t.begin < m.end and t.end > m.start)
            ]
        score = round(0.6 + 0.4 * m.intensity, 3)
        chunks.append(
            SemanticChunk(
                id=cid,
                text=m.surface,
                type=m.chunk_type,
                token_ids=token_ids,
                score=score,
            )
        )
        cid += 1
        cursor = m.end

    # Tail gap
    if cursor < len(normalized_text):
        tail_chunks = _pos_based_chunks(tokens, cursor, len(normalized_text), cid, stopwords, sw_prefixes)
        chunks.extend(tail_chunks)

    return chunks
