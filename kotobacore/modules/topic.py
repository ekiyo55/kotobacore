"""Topic module (FR-063): what a sentence / document is about.

Open vocabulary (要件定義書 v0.4 §14 #3): topics are

- TOPIC-type dictionary entities (entity.csv, e.g. 円安 / 値上げ) — score 1.0;
- other entities (organizations, products, events …) — score 0.8;
- frequent content nouns — score by frequency × length, normalized to the
  strongest noun.

Reads only Core output (tokens, entities). Used by document chunking
(rag.chunk) for boundary decisions and by reranking (rag.features).
"""

from __future__ import annotations

from collections import Counter

from kotobacore.core.ir import Entity, Token, Topic, TopicResult
from kotobacore.dictionary import DictionaryBundle

_ENTITY_TOPIC_TYPES = {"ORGANIZATION", "PRODUCT", "BRAND", "SERVICE", "WORK", "EVENT", "PERSON", "LOCATION", "TECHNOLOGY", "MODEL", "API"}
_SKIP_TYPES = {"DATE", "TIME", "MONEY", "QUANTITY"}


def detect_topics(
    tokens: list[Token],
    entities: list[Entity],
    bundle: DictionaryBundle,
    *,
    max_topics: int = 5,
) -> TopicResult:
    stopwords = bundle.stopword_set()
    topics: dict[str, Topic] = {}

    for ent in entities:
        if ent.type in _SKIP_TYPES:
            continue
        label = ent.normalized or ent.surface
        score = 1.0 if ent.type == "TOPIC" else (0.8 if ent.type in _ENTITY_TOPIC_TYPES else 0.6)
        cur = topics.get(label)
        if cur is None:
            topics[label] = Topic(label=label, score=score, count=1, entity_id=ent.id, entity_type=ent.type, source="entity")
        else:
            cur.count += 1
            cur.score = min(1.0, cur.score + 0.1)

    covered = set()
    for ent in entities:
        covered.update(ent.token_ids)
    nouns: Counter[str] = Counter()
    for t in tokens:
        if t.id in covered or "名詞" not in t.pos or "代名詞" in t.pos or "数詞" in t.pos:
            continue
        w = t.normalized or t.surface
        if len(w) < 2 or w in stopwords or w.isdigit():
            continue
        nouns[w] += 1
    if nouns:
        raw = {w: c * (1.0 + 0.1 * min(len(w), 6)) for w, c in nouns.items()}
        top = max(raw.values())
        for w, v in raw.items():
            if w in topics:
                continue
            topics[w] = Topic(label=w, score=round(0.7 * v / top, 3), count=nouns[w], entity_id=None, entity_type=None, source="noun")

    ranked = sorted(topics.values(), key=lambda t: (-t.score, -t.count, t.label))
    return TopicResult(topics=ranked[:max_topics])


def merge_topics(results: list[TopicResult], *, max_topics: int = 10) -> TopicResult:
    """Document-level aggregation: sum scores, keep counts, re-rank."""
    merged: dict[str, Topic] = {}
    for r in results:
        for t in r.topics:
            cur = merged.get(t.label)
            if cur is None:
                merged[t.label] = Topic(label=t.label, score=t.score, count=t.count, entity_id=t.entity_id, entity_type=t.entity_type, source=t.source)
            else:
                cur.score += t.score
                cur.count += t.count
                cur.entity_id = cur.entity_id or t.entity_id
    ranked = sorted(merged.values(), key=lambda t: (-t.score, -t.count, t.label))
    top = ranked[0].score if ranked else 1.0
    for t in ranked:
        t.score = round(t.score / top, 3) if top else t.score
    return TopicResult(topics=ranked[:max_topics])
