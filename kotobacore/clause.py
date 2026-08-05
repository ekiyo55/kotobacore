"""Clause segmentation — a lightweight first-class primitive.

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
_SOFT_BOUNDARIES: tuple[str, ...] = ("のに",)

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
