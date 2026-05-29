"""Intent classifier.

Per 04_内部設計書 §13 and 06_API §12. Rule-based v0.1 implementation that
scores each intent against the normalized text via pattern alternation
(``a|b|c``) from ``intent_rules.csv``.
"""

from __future__ import annotations

from collections import defaultdict

from kotobacore.dictionary import DictionaryBundle
from kotobacore.schema import IntentCandidate, IntentResult


def _patterns_for(rule_pattern: str) -> list[str]:
    """Split a rule's ``a|b|c`` pattern into alternatives."""
    return [p.strip() for p in rule_pattern.split("|") if p.strip()]


def classify_intent(text: str, bundle: DictionaryBundle) -> IntentResult:
    """Classify ``text`` against ``intent_rules.csv``.

    Score per intent is the sum of (rule.score × matches) across all
    alternation patterns. Higher-priority rules contribute proportionally
    more. The top-scoring intent becomes the label; remaining intents are
    sorted by score for ``candidates``.
    """
    if not text or not bundle.intent_rules:
        return IntentResult(label=None, confidence=0.0, candidates=[])

    scores: dict[str, float] = defaultdict(float)

    for rule in bundle.intent_rules:
        patterns = _patterns_for(rule.pattern)
        rule_hits = 0
        for p in patterns:
            if not p:
                continue
            if p in text:
                # Count multiple occurrences (gives signal for repeated patterns)
                rule_hits += text.count(p)
        if rule_hits > 0:
            # Priority scales the score contribution
            priority_weight = max(rule.priority, 1) / 100.0
            scores[rule.intent] += rule.score * rule_hits * priority_weight

    if not scores:
        return IntentResult(
            label="unknown",
            confidence=0.0,
            candidates=[IntentCandidate(label="unknown", confidence=0.0)],
        )

    # Normalize: cap each intent's score at 1.0 for confidence reporting
    # (the raw score may exceed 1.0 with repeated patterns)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    top_label, top_score = ranked[0]
    confidence = round(min(top_score, 1.0), 3)

    candidates = [
        IntentCandidate(label=label, confidence=round(min(score, 1.0), 3))
        for label, score in ranked
    ]

    return IntentResult(label=top_label, confidence=confidence, candidates=candidates)
