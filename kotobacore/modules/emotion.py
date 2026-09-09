"""Emotion module — Plutchik aggregation over Core affect expressions.

Per 要件定義書 v0.4 FR-061. The dictionary matching, token alignment,
negation and 逆接 clause weighting live in :mod:`kotobacore.core.lexicon`
(shared with the Sentiment module); this module only aggregates:

4. Plutchik distribution = Σ confidence × intensity × clause weight
5. Primary emotion = dominant expression's ``base_emotion``

``EmotionResult.polarity`` is the affective polarity (emotion words only);
the Sentiment module reports it as ``affect_polarity`` and keeps its own
``polarity`` for evaluative words.
"""

from __future__ import annotations

from collections import defaultdict

from kotobacore.core.ir import EmotionExpression, EmotionResult, Token
from kotobacore.core.lexicon import (
    EVALUATION,
    ScoredExpression,
    aggregate_confidence,
    aggregate_intensity,
    aggregate_polarity,
    primary_index,
    score_affect_expressions,
)
from kotobacore.core.lexicon import (
    _build_candidates as _build_emotion_candidates,  # noqa: F401
)

# Backward-compatible aliases (tests / tools imported these from the detector).
from kotobacore.core.lexicon import bigrams as _bigrams  # noqa: F401
from kotobacore.core.lexicon import get_candidates as _get_emotion_candidates  # noqa: F401
from kotobacore.core.lexicon import get_matcher as _get_emotion_matcher  # noqa: F401
from kotobacore.core.lexicon import jaccard as _jaccard  # noqa: F401
from kotobacore.core.lexicon import plutchik_for as _plutchik_for  # noqa: F401
from kotobacore.core.lexicon import polarity_for as _polarity_for  # noqa: F401
from kotobacore.dictionary import DictionaryBundle


def _empty() -> EmotionResult:
    return EmotionResult(primary=None, polarity=None, intensity=0.0, confidence=0.0, plutchik={}, expressions=[])


def detect_emotion(
    text: str,
    bundle: DictionaryBundle,
    tokens: list[Token] | None = None,
    scored: list[ScoredExpression] | None = None,
) -> EmotionResult:
    """Aggregate affect expressions in normalized ``text`` into an EmotionResult.

    ``scored`` lets the Analyzer run the Core scoring once and hand the same
    expressions to both the Emotion and Sentiment modules.
    """
    if not text:
        return _empty()
    if scored is None:
        scored = score_affect_expressions(text, bundle, tokens)
    # Emotion words only: evaluative words (sentiment.csv) belong to the
    # Sentiment module. ``polarity`` here is the affective polarity and is
    # mirrored as ``SentimentResult.affect_polarity``.
    scored = [e for e in scored if e.base_emotion != EVALUATION]
    if not scored:
        return _empty()
    # 強調は感情 (ユーザー決定 2026-09-09): exaggeration stays a real primary when it is the only
    # emotion expression (やばい / マジで); with another emotion present that one leads
    # (primary_index demotes intensifiers: マジで美味しかった → joy).
    polarity = aggregate_polarity(scored)

    expressions = [
        EmotionExpression(
            text=e.text,
            emotion=e.base_emotion,
            plutchik_emotion=e.plutchik_emotion,
            polarity=e.polarity,
            intensity=e.intensity,
            confidence=e.confidence,
            matched_examples=list(e.matched_examples),
            begin=e.begin,
            end=e.end,
            negated=e.negated,
            holder=e.holder_id or "speaker",
            holder_text=e.holder_text,
            about=e.target_id,
            about_text=e.target_text,
        )
        for e in scored
    ]

    plutchik_dist: dict[str, float] = defaultdict(float)
    for e in scored:
        plutchik_dist[e.plutchik_emotion or "mixed"] += e.intensity * e.confidence * e.clause_weight
    max_v = max(plutchik_dist.values())
    if max_v > 0:
        plutchik = {k: round(v / max_v, 3) for k, v in plutchik_dist.items()}
    else:
        plutchik = dict.fromkeys(plutchik_dist, 0.0)

    primary = scored[primary_index(scored)]
    return EmotionResult(
        primary=primary.base_emotion,
        polarity=polarity,
        intensity=aggregate_intensity(scored),
        confidence=aggregate_confidence(scored),
        plutchik=plutchik,
        expressions=expressions,
    )
