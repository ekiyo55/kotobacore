"""Text Foundation (N1 文字正規化 + N2 表記正規化) with original-offset tracking.

Per 要件定義書 v0.4 FR-002 the normalization pipeline is:

    N1 文字正規化  line endings → control chars → NFKC → NFKC 例外 (context rules)
    N2 表記正規化  dictionary rules (normalization.csv), longest match, idempotent
    (tokenizer)
    N3〜N5         token-level (see core.token / core.entity)

N1 and N2 change the character count (㈱ → (株) is 1→3, ｶﾞ → ガ is 2→1), so
every step here carries an *origin map*: for each character of the output,
the index of the original character it came from. :class:`NormalizedText`
exposes that map so IR spans can always be expressed in original-text
coordinates (設計原則 3 Traceability).

Design notes (04_内部設計書 §6, kept from v0.1):
- NFKC for 全角/半角 / 丸数字 unification
- DO NOT over-normalize SNS expressions like しぬwww
- DO NOT strip emoji (NFKC keeps them)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

_ALLOWED_CONTROL = {"\n", "\t"}

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class NormalizedText:
    """Normalized text plus the map back to the original string.

    ``origin[j]`` is the index in ``original`` of the character that produced
    ``normalized[j]``. When one original character expanded into several
    (㈱ → (株)) they all point at the same original index; when several
    collapsed into one (ｶﾞ → ガ) the output points at the first of them.
    """

    original: str
    normalized: str
    origin: list[int] = field(default_factory=list)

    def to_original_span(self, nbegin: int, nend: int) -> tuple[int, int]:
        """Convert a half-open span on ``normalized`` to original coordinates.

        The end is the original index *after* the character that produced
        ``normalized[nend - 1]``, so spans are never empty for non-empty input.
        """
        n = len(self.origin)
        if n == 0:
            return 0, 0
        nbegin = max(0, min(nbegin, n))
        if nend <= nbegin:
            pos = self.origin[nbegin] if nbegin < n else len(self.original)
            return pos, pos
        nend = min(nend, n)
        return self.origin[nbegin], self.origin[nend - 1] + 1


# ---------------------------------------------------------------------------
# N1 文字正規化
# ---------------------------------------------------------------------------

# Characters that NFKC may *compose* with the preceding character. A run
# boundary is never placed in front of one of these, so each run can be
# normalized independently and still equal NFKC of the whole string.
_HALFWIDTH_VOICED = {"ﾞ", "ﾟ"}  # ﾞ ﾟ


def _is_composing(ch: str) -> bool:
    if ch in _HALFWIDTH_VOICED:
        return True
    cat = unicodedata.category(ch)
    if cat.startswith("M"):
        return True
    cp = ord(ch)
    # Hangul jamo (L/V/T) can compose into syllables.
    return 0x1100 <= cp <= 0x11FF or 0x3130 <= cp <= 0x318F or 0xA960 <= cp <= 0xA97F or 0xD7B0 <= cp <= 0xD7FF


def _nfkc_with_map(chars: list[str], origin: list[int]) -> tuple[list[str], list[int]]:
    """NFKC over ``chars`` keeping an origin index per output character."""
    if not chars:
        return [], []
    text = "".join(chars)
    full = unicodedata.normalize("NFKC", text)
    if full == text:
        return chars, origin

    out_chars: list[str] = []
    out_origin: list[int] = []
    # Split into runs that normalize independently.
    run_start = 0
    n = len(chars)
    for i in range(1, n + 1):
        if i < n and _is_composing(chars[i]):
            continue
        run = text[run_start:i]
        norm = unicodedata.normalize("NFKC", run)
        if len(norm) == len(run):
            out_chars.extend(norm)
            out_origin.extend(origin[run_start:i])
        else:
            out_chars.extend(norm)
            out_origin.extend([origin[run_start]] * len(norm))
        run_start = i

    if "".join(out_chars) != full:
        # Rare: composition crossed a run boundary. Fall back to the exact
        # (quadratic) prefix method.
        out_chars, out_origin = [], []
        prev_len = 0
        for i in range(n):
            cur = unicodedata.normalize("NFKC", text[: i + 1])
            if len(cur) > prev_len:
                out_chars.extend(cur[prev_len:])
                out_origin.extend([origin[i]] * (len(cur) - prev_len))
            elif len(cur) < prev_len:
                out_chars = list(cur)
                out_origin = out_origin[: len(cur)]
            else:
                # same length — the tail may have changed (composition)
                out_chars = list(cur)
            prev_len = len(cur)
    return out_chars, out_origin


# NFKC exception (context) rules — applied after NFKC.
_KATAKANA_RE = re.compile(r"[ァ-ヺー]")
# Hyphen-like characters that between katakana mean the long vowel mark.
_HYPHEN_LIKE = {"-", "‐", "‑", "‒", "–", "—", "―", "−"}


def _apply_n1_context_rules(chars: list[str]) -> None:
    """In-place 1:1 character fixes that need context (origin map unchanged)."""
    n = len(chars)
    for i in range(1, n - 1):
        if chars[i] in _HYPHEN_LIKE and _KATAKANA_RE.match(chars[i - 1]) and _KATAKANA_RE.match(chars[i + 1]):
            chars[i] = "ー"  # ー


def _n1(text: str) -> tuple[list[str], list[int]]:
    chars: list[str] = []
    origin: list[int] = []
    i = 0
    n = len(text)
    # 1. line endings (CRLF → LF, CR → LF) and 2. control characters
    while i < n:
        ch = text[i]
        if ch == "\r":
            chars.append("\n")
            origin.append(i)
            if i + 1 < n and text[i + 1] == "\n":
                i += 2
            else:
                i += 1
            continue
        if ch in _ALLOWED_CONTROL or unicodedata.category(ch)[0] != "C":
            chars.append(ch)
            origin.append(i)
        i += 1
    # 3. NFKC
    chars, origin = _nfkc_with_map(chars, origin)
    # 4. context exceptions
    _apply_n1_context_rules(chars)
    return chars, origin


# ---------------------------------------------------------------------------
# N2 表記正規化
# ---------------------------------------------------------------------------


_PATTERN_CACHE: dict[int, tuple[tuple[str, ...], re.Pattern[str] | None, dict[str, str], int]] = {}


def _compile_rules(rules: dict[str, str]) -> re.Pattern[str] | None:
    key = id(rules)
    cached = _PATTERN_CACHE.get(key)
    # v1.1 speed-up: the cache keeps a reference to the rule map itself, so its id cannot be reused by
    # another dict while cached; a hit is "the same object, same size" instead of rebuilding the source
    # tuple on every call (rule maps come from the bundle cache and are not mutated)
    if cached is not None and cached[2] is rules and cached[3] == len(rules):
        return cached[1]
    sources = tuple(s for s in rules if s)
    pattern: re.Pattern[str] | None = None
    if sources:
        ordered = sorted(sources, key=len, reverse=True)  # longest match first
        pattern = re.compile("|".join(re.escape(s) for s in ordered))
    if len(_PATTERN_CACHE) > 16:
        _PATTERN_CACHE.clear()
    _PATTERN_CACHE[key] = (sources, pattern, rules, len(rules))
    return pattern


def _n2(chars: list[str], origin: list[int], rules: dict[str, str]) -> tuple[list[str], list[int]]:
    pattern = _compile_rules(rules)
    if pattern is None or not chars:
        return chars, origin
    text = "".join(chars)
    out_chars: list[str] = []
    out_origin: list[int] = []
    pos = 0
    for m in pattern.finditer(text):
        src = m.group(0)
        tgt = rules[src]
        # Idempotence guard: if the target already stands here (プリンタ→プリンター
        # on a text that already reads プリンター), leave it alone.
        if tgt != src and text.startswith(tgt, m.start()):
            continue
        # Long-vowel rules (サーバ→サーバー) only apply at a katakana word end:
        # ユーザビリティ must not become ユーザービリティ.
        if (
            tgt.startswith(src)
            and _KATAKANA_RE.match(src[-1])
            and m.end() < len(text)
            and _KATAKANA_RE.match(text[m.end()])
        ):
            continue
        out_chars.extend(chars[pos : m.start()])
        out_origin.extend(origin[pos : m.start()])
        if len(tgt) == len(src):
            out_chars.extend(tgt)
            out_origin.extend(origin[m.start() : m.end()])
        else:
            # v1.1: each target char takes the origin of the source char at the same
            # index (capped at the last one), so サーバ→サーバー spans all of サーバ
            # (was: every char on origin[m.start()], giving a 1-char original span)
            out_chars.extend(tgt)
            out_origin.extend(origin[m.start() + min(k, len(src) - 1)] for k in range(len(tgt)))
        pos = m.end()
    out_chars.extend(chars[pos:])
    out_origin.extend(origin[pos:])
    return out_chars, out_origin


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _n2_compact(chars: list[str], origin: list[int], rules: dict[str, str]) -> tuple[list[str], list[int]]:
    """N2b (v1.1): okurigana spelling → all-kanji spelling when a kanji follows (引き当て金 → 引当金)."""
    pattern = _compile_rules(rules)
    if pattern is None or not chars:
        return chars, origin
    text = "".join(chars)
    out_chars: list[str] = []
    out_origin: list[int] = []
    pos = 0
    for m in pattern.finditer(text):
        if m.end() >= len(text) or not _is_cjk(text[m.end()]):
            continue  # 引き当てを行う keeps its okurigana; only compounds are compacted
        tgt = rules[m.group(0)]
        out_chars.extend(chars[pos : m.start()])
        out_origin.extend(origin[pos : m.start()])
        # keep each target kanji on the original position of the same kanji
        src_idx = [m.start() + i for i, ch in enumerate(m.group(0)) if not ("ぁ" <= ch <= "ゖ")]
        for k, ch in enumerate(tgt):
            out_chars.append(ch)
            out_origin.append(origin[src_idx[k]] if k < len(src_idx) else origin[m.start()])
        pos = m.end()
    out_chars.extend(chars[pos:])
    out_origin.extend(origin[pos:])
    return out_chars, out_origin


def _is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff" or ch == "々"


def normalize_with_map(
    text: str, rules: dict[str, str] | None = None, compact_rules: dict[str, str] | None = None
) -> NormalizedText:
    """Run N1 (+ N2 when ``rules`` is given, + N2b when ``compact_rules`` is given)."""
    if not text:
        return NormalizedText(original=text, normalized=text, origin=[])
    chars, origin = _n1(text)
    if rules:
        chars, origin = _n2(chars, origin, rules)
    if compact_rules:
        chars, origin = _n2_compact(chars, origin, compact_rules)
    return NormalizedText(original=text, normalized="".join(chars), origin=origin)


def normalize(text: str) -> str:
    """Return the N1-normalized form of ``text`` (no dictionary rules).

    Kept for backward compatibility; the transformation is intentionally
    conservative and should not change user-visible semantics for SNS/emoji
    content.
    """
    if not text:
        return text
    return normalize_with_map(text).normalized
