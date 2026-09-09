"""Sentiment module — evaluative polarity over Core affect expressions.

Per 要件定義書 v0.4 FR-062 and the 2026-09-08 decision: **emotion words do
not count toward sentiment**. ``polarity`` / ``expressions`` come from
evaluative words only (sentiment.csv: いまいち / 使いやすい / 高すぎる …);
the polarity implied by emotion words is reported separately as
``affect_polarity`` (equal to ``EmotionResult.polarity``). 「わくわくが止まら
ない」 therefore has polarity=None, affect_polarity=positive.

Both modules consume the same :func:`kotobacore.core.lexicon.score_affect_expressions`
output. Target attribution (宛先付き評価, FR-052) comes from core.attribution.
"""

from __future__ import annotations

from kotobacore.core.ir import SentimentExpression, SentimentResult, Token
from kotobacore.core.lexicon import (
    EVALUATION,
    ScoredExpression,
    aggregate_confidence,
    aggregate_intensity,
    aggregate_polarity,
    score_affect_expressions,
)
from kotobacore.dictionary import DictionaryBundle


def _empty() -> SentimentResult:
    return SentimentResult(polarity=None, intensity=0.0, confidence=0.0, expressions=[])


def detect_sentiment(
    text: str,
    bundle: DictionaryBundle,
    tokens: list[Token] | None = None,
    scored: list[ScoredExpression] | None = None,
) -> SentimentResult:
    """Aggregate affect expressions in normalized ``text`` into a SentimentResult."""
    if not text:
        return _empty()
    if scored is None:
        scored = score_affect_expressions(text, bundle, tokens)
    if not scored:
        return _empty()
    evaluative = [e for e in scored if e.base_emotion == EVALUATION]
    affective = [e for e in scored if e.base_emotion != EVALUATION]
    expressions = [
        SentimentExpression(
            text=e.text,
            polarity=e.polarity,
            intensity=e.intensity,
            confidence=e.confidence,
            begin=e.begin,
            end=e.end,
            negated=e.negated,
            target=e.target_id,
            target_text=e.target_text,
        )
        for e in evaluative
    ]
    return SentimentResult(
        polarity=aggregate_polarity(evaluative),
        intensity=aggregate_intensity(evaluative),
        confidence=aggregate_confidence(evaluative),
        expressions=expressions,
        affect_polarity=aggregate_polarity(affective),
    )
