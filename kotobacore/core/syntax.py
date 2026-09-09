"""Syntax (Core): clause segmentation, 逆接 weighting and negation scope.

Splits text into clauses at sentence punctuation and adversative (逆接)
conjunctions. Three consumers share the result:

1. Emotion example similarity (ex_sim) is computed against the clause
   containing the expression, not the whole input — long documents no longer
   dilute the char-bigram Jaccard toward zero.
2. Polarity aggregation weights clauses around 逆接: in Japanese the clause
   AFTER the adversative carries the speaker's real stance
   (「難しい判断でしたが成功しました」 → 成功 side wins).
3. Negation scope: a negation morpheme only negates an emotion expression
   within the same clause.

No dictionaries required; pure string rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Hard sentence delimiters — clause boundary, weight-neutral.
_SENTENCE_ENDERS: frozenset[str] = frozenset("。！？!?\n")

# Adversative conjunction markers, longest first. The split happens AFTER the
# marker (the marker stays with the preceding clause).
# たが / だが cover predicate + が (あったが / 駄目だが); ですが / ますが the
# polite forms. Bare が is NOT split on — it is usually the case particle.
# These carry the "clause after wins" weighting (〜だったけど、良かった).
_ADVERSATIVES: tuple[str, ...] = (
    "けれども", "けれど", "ですけど", "だけど", "けど",
    "ですが", "ますが", "だが", "たが",
    "しかし",
)

# Soft boundaries: clause split WITHOUT weighting. のに is adversative but the
# speaker's emotion typically sits in the clause BEFORE it (恨み節 —
# 「せっかく作ったのに」「締め切りが近いのに」), so no re-weighting applies.
# v0.5: continuative verb forms followed by a comma (設立し、/ 行って、) also
# end a clause so that predicate-argument structure sees one predicate per
# clause. Weight-neutral like のに.
_SOFT_BOUNDARIES: tuple[str, ...] = ("のに", "し、", "て、", "で、")

# Weight applied to clauses in a sentence relative to its last adversative.
_PRE_ADVERSATIVE_WEIGHT = 0.7
_POST_ADVERSATIVE_WEIGHT = 1.2


@dataclass
class Clause:
    start: int  # char offset, inclusive
    end: int  # exclusive
    weight: float  # polarity-aggregation weight (1.0 = neutral)


def _find_adversative(text: str, pos: int) -> tuple[int, bool]:
    """Return ``(marker_len, weighted)`` for a boundary at ``pos``, else (0, False)."""
    for marker in _ADVERSATIVES:
        if text.startswith(marker, pos):
            return len(marker), True
    for marker in _SOFT_BOUNDARIES:
        if text.startswith(marker, pos):
            return len(marker), False
    return 0, False


def split_clauses(text: str) -> list[Clause]:
    """Split ``text`` into weighted clauses.

    Sentence punctuation always ends a clause (weight-neutral). Within one
    sentence, adversative markers also end a clause, and every clause before
    the sentence's LAST adversative is down-weighted while the clauses after
    it are up-weighted. Sentences without an adversative stay at weight 1.0.
    """
    if not text:
        return []

    # Pass 1 — collect boundaries: (position_after_boundary, is_adversative)
    clauses: list[Clause] = []
    sentence_clause_idx: list[int] = []  # clause indices of current sentence
    adversative_after: list[bool] = []  # per clause: ends with adversative?

    def _close_sentence() -> None:
        """Apply 逆接 weighting to the finished sentence's clauses."""
        last_adv = -1
        for local_i, ci in enumerate(sentence_clause_idx):
            if adversative_after[local_i]:
                last_adv = local_i
        if last_adv >= 0:
            for local_i, ci in enumerate(sentence_clause_idx):
                clauses[ci].weight = (
                    _PRE_ADVERSATIVE_WEIGHT
                    if local_i <= last_adv
                    else _POST_ADVERSATIVE_WEIGHT
                )
        sentence_clause_idx.clear()
        adversative_after.clear()

    n = len(text)
    clause_start = 0
    i = 0
    while i < n:
        ch = text[i]
        if ch in _SENTENCE_ENDERS:
            # consume a run of enders (。。。 / ！？)
            j = i + 1
            while j < n and text[j] in _SENTENCE_ENDERS:
                j += 1
            if i > clause_start:
                clauses.append(Clause(clause_start, j, 1.0))
                sentence_clause_idx.append(len(clauses) - 1)
                adversative_after.append(False)
            _close_sentence()
            clause_start = j
            i = j
            continue
        adv_len, weighted = _find_adversative(text, i)
        if adv_len and i > clause_start:
            end = i + adv_len
            clauses.append(Clause(clause_start, end, 1.0))
            sentence_clause_idx.append(len(clauses) - 1)
            adversative_after.append(weighted)
            clause_start = end
            i = end
            continue
        i += 1

    if clause_start < n:
        clauses.append(Clause(clause_start, n, 1.0))
        sentence_clause_idx.append(len(clauses) - 1)
        adversative_after.append(False)
    _close_sentence()

    return clauses


def clause_at(clauses: list[Clause], pos: int) -> Clause | None:
    """Return the clause containing char position ``pos`` (None if outside)."""
    for c in clauses:
        if c.start <= pos < c.end:
            return c
    return None


# ---------------------------------------------------------------------------
# Negation scope (moved here from the emotion detector in v0.3 so that the
# Emotion, Sentiment and Intent modules share one definition — FR-022)
# ---------------------------------------------------------------------------

# Negation immediately following an expression (optionally via a particle):
# 好き[じゃない] / 不安[はない] / 元気[がなく] / 嬉しく[ない] …
_NEG_AFTER_RE = re.compile(r"(?:は|も|が)?(?:じゃ|では)?(?:し|でき|され|せ)?(?:な(?:かった|くて|く|い)|ません(?:でした)?|ず)")

# Token-internal negation: a conjugated-adjective token whose lemma matched
# the lexicon (嬉しくない → lemma 嬉しい) but whose surface is negated.
_NEG_TOKEN_SUFFIXES: tuple[str, ...] = ("くなかった", "くなくて", "くない", "しない", "しなかった", "しません", "できない", "できません", "されない", "されません")


def negation_after(text: str, end: int, clause: Clause | None = None) -> int:
    """Length of a negation suffix starting at ``end``, or 0.

    The negation must lie within ``clause`` (when given): a negation in the
    next clause does not reach back over a clause boundary.
    """
    m = _NEG_AFTER_RE.match(text, end)
    if m and (clause is None or m.end() <= clause.end):
        return m.end() - end
    return 0


def is_negated_surface(surface: str) -> bool:
    """True when a single token surface carries its own negation (嬉しくない)."""
    return surface.endswith(_NEG_TOKEN_SUFFIXES)


# ---------------------------------------------------------------------------
# Sentence / paragraph boundaries (FR-020, v0.4)
# ---------------------------------------------------------------------------

_OPEN_QUOTES = "「『（(【［[〈《"
_CLOSE_QUOTES = "」』）)】］]〉》"
_STRONG_ENDERS = frozenset("。！？!?")
# Line-initial markers that make the line a heading / list item.
_HEADING_PREFIXES: tuple[str, ...] = ("#", "【", "■", "●", "◆", "▼", "▶", "◇", "□", "○", "◎", "☆", "★")
_BULLET_PREFIXES: tuple[str, ...] = ("・", "-", "*", "•", "‐", "–")
_HEADING_RE = re.compile(r"^(?:第\s*[0-9０-９一二三四五六七八九十]+\s*[章節条部項]|[0-9０-９]{1,2}[.．、)）]|[(（][0-9０-９]{1,2}[)）])")


def is_heading_line(line: str) -> bool:
    """True when ``line`` looks like a heading or a numbered section label."""
    t = line.strip()
    if not t:
        return False
    if t.startswith(_HEADING_PREFIXES):
        return True
    return bool(_HEADING_RE.match(t)) and len(t) <= 60 and not t.endswith(tuple(_STRONG_ENDERS))


def is_bullet_line(line: str) -> bool:
    t = line.lstrip()
    return t.startswith(_BULLET_PREFIXES) and len(t) > 1 and t[1:2] in (" ", "　", "") or t[:1] == "・"


def split_sentences(text: str) -> list[tuple[int, int]]:
    """Return sentence spans ``(begin, end)`` (half-open, whitespace-trimmed).

    Rules (FR-020):
    - 。！？!? end a sentence, but not inside 「」『』（）【】 quotes
      (「行こう。」と言った。 is one sentence);
    - a closing quote right after the ender stays with the sentence;
    - a newline always ends a sentence (headings / bullets become sentences);
    - a half-width period ends a sentence only when followed by whitespace or
      the end of text and not preceded by a digit (3.5 stays whole).
    """
    spans: list[tuple[int, int]] = []
    n = len(text)
    start = 0
    depth = 0
    i = 0

    def _emit(b: int, e: int) -> None:
        while b < e and text[b].isspace():
            b += 1
        while e > b and text[e - 1].isspace():
            e -= 1
        if e > b:
            spans.append((b, e))

    while i < n:
        ch = text[i]
        if ch == "\n":
            _emit(start, i)
            start = i + 1
            depth = 0
            i += 1
            continue
        if ch in _OPEN_QUOTES:
            depth += 1
        elif ch in _CLOSE_QUOTES:
            depth = max(0, depth - 1)
        elif depth == 0 and (ch in _STRONG_ENDERS or (ch == "." and (i + 1 >= n or text[i + 1].isspace()) and not (i > 0 and text[i - 1].isdigit()))):
            j = i + 1
            while j < n and (text[j] in _STRONG_ENDERS or text[j] in _CLOSE_QUOTES or text[j] == "."):
                j += 1
            _emit(start, j)
            start = j
            i = j
            continue
        i += 1
    _emit(start, n)
    return spans


_FENCE_RE = re.compile(r"^\s*(```|~~~)")


def is_fence_line(line: str) -> bool:
    """True for a Markdown code-fence line (``` or ~~~, optionally with a language tag)."""
    return bool(_FENCE_RE.match(line))


def split_paragraphs(text: str) -> list[tuple[int, int]]:
    """Return paragraph spans: blocks separated by blank lines; a heading line
    is always its own paragraph. A fenced code block (``` … ```) is one
    paragraph: inside it nothing is a heading (a shell comment ``# …`` is not
    a section) and blank lines do not split it (v0.5.4)."""
    spans: list[tuple[int, int]] = []
    pos = 0
    n = len(text)
    block_start: int | None = None
    in_code = False
    while pos <= n:
        nl = text.find("\n", pos)
        line_end = n if nl < 0 else nl
        line = text[pos:line_end]
        if is_fence_line(line):
            if not in_code:
                # opening fence: close the running prose block, start the code block
                if block_start is not None:
                    spans.append((block_start, pos))
                block_start = pos
                in_code = True
            else:
                spans.append((block_start if block_start is not None else pos, line_end))
                block_start = None
                in_code = False
        elif in_code:
            pass  # everything inside the fence belongs to the code paragraph
        elif not line.strip():
            if block_start is not None:
                spans.append((block_start, pos))
                block_start = None
        elif is_heading_line(line):
            if block_start is not None:
                spans.append((block_start, pos))
            spans.append((pos, line_end))
            block_start = None
        elif block_start is None:
            block_start = pos
        if nl < 0:
            break
        pos = nl + 1
    if block_start is not None:
        spans.append((block_start, n))
    # trim whitespace
    out: list[tuple[int, int]] = []
    for b, e in spans:
        while b < e and text[b].isspace():
            b += 1
        while e > b and text[e - 1].isspace():
            e -= 1
        if e > b:
            out.append((b, e))
    return out
