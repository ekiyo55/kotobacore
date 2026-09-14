"""Retrieval and reranking features (RAG layer, FR-083 / FR-084).

KotobaCore does not run a retriever or a reranker itself; it hands a
retriever the structured signals it needs and scores a (query, chunk) pair
on the signals the IR makes available:

    score = w_entity  × entity_match
          + w_keyword × keyword_overlap
          + w_intent  × intent_match
          + w_time    × time_match
          + w_topic   × topic_match
          + w_sentiment × sentiment_match
          + w_semantic  × semantic_similarity   (supplied by the caller — embeddings are external)

Weights are configurable (v1.0 requirement: "実際の重みは設定可能とする").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from kotobacore.core.ir import AnalysisResult, DocumentChunk, QueryIR

# Defaults chosen on the tools/rag_eval set (2026-09-08): fitted on questions
# 1-80 (MRR 0.791 → 0.824) and validated on 81-200 (0.802 → 0.825). The
# retriever's own score (lexical or vector) stays the strongest signal; entity
# / answer-type matches are hints, not vetoes — heavy entity weights punished
# gold chunks whose numbers or abbreviations were not recognized as entities.
DEFAULT_WEIGHTS: dict[str, float] = {
    "entity_match": 0.10,
    "keyword_overlap": 0.20,
    "intent_match": 0.10,
    "time_match": 0.10,
    "topic_match": 0.05,
    "sentiment_match": 0.00,
    "semantic_similarity": 0.40,
}

# Hybrid path (a real embedding similarity AND a fused retrieval score are
# available): the fused ranking itself is the dominant feature; entity /
# keyword / answer-type matches are small corrections. Tuned on the synthetic
# questions 1-80, validated on 81-200, checked once on the real corpus
# (tools/rag_eval/tune_hybrid_rerank.py, 2026-09-08). Selected automatically
# by rerank_score() when ``retrieval_score`` is given.
HYBRID_WEIGHTS: dict[str, float] = {
    "retrieval_score": 0.35,
    "semantic_similarity": 0.10,
    "lexical_similarity": 0.00,
    "entity_match": 0.00,
    "keyword_overlap": 0.15,
    "intent_match": 0.05,
    "time_match": 0.00,
    "topic_match": 0.00,
    "sentiment_match": 0.00,
}

EXPANSION_WEIGHT = 0.15  # weight of a synonym expansion relative to a typed query term (rag_eval 2026-09-08: neutral on real docs, +0.02 MRR on the synthetic set)

# ---- hybrid fusion weight α (share of the lexical score in α·bm25 + (1-α)·cos)
# Fixed on purpose. tools/rag_eval/analyze_alpha_by_query.py (2026-09-09) tried
# query-time policies — by predicted intent (how_to → lexical-heavy), by ASCII
# identifiers / product codes in the query, by synonym availability, by the
# peakedness of each ranking — and none beat a fixed α on synthetic train AND
# validation AND the real corpus at once (oracle by gold question type is only
# +0.03 MRR). The how-to weakness is handled on the rerank side instead
# (answer_form_match).
HYBRID_ALPHA = 0.3
_ASCII_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_.\-/]{2,}")
_ANCHOR_ENTITY_TYPES = frozenset({"PRODUCT", "SERVICE", "BRAND"})


def query_lexical_anchors(query: QueryIR) -> str:
    """Diagnostic label for a query's lexical anchors: ``identifier`` (an ASCII
    token such as a file name, command, host or product code), ``product``
    (a PRODUCT / SERVICE / BRAND entity), or ``none``."""
    if _ASCII_IDENTIFIER.search(query.original):
        return "identifier"
    if any(e.type in _ANCHOR_ENTITY_TYPES for e in query.entities):
        return "product"
    return "none"


def hybrid_alpha(query: QueryIR) -> float:
    """Weight of the lexical score in a hybrid (BM25 + embedding) fusion for this query.
    Currently the constant ``HYBRID_ALPHA`` (see the note above); the query is
    accepted so callers can plug in a policy later without changing call sites."""
    del query
    return HYBRID_ALPHA

_ANSWER_TYPE_ENTITY = {"MONEY": {"MONEY"}, "DATE": {"DATE", "TIME"}, "LOCATION": {"LOCATION"}, "PERSON": {"PERSON"}, "NUMBER": {"QUANTITY", "MONEY"}}

# Answer *form* cues for TEXT-type intents (v0.5.3). A how-to question wants a
# chunk that reads like a procedure (command, steps, "→", してください), a
# why-question wants a causal chunk, and so on. Real-corpus finding
# (2026-09-09): for how_to / procedure queries intent_match was always None,
# so checklists and spec tables outranked the one chunk holding the command.
_ANSWER_FORM_CUES: dict[str, re.Pattern[str]] = {
    "how_to": re.compile(
        r"```|^\s*[$#>] |^\s*(?:\d+[.)]|[①-⑩]|[-*] )|→|"
        r"手順|対処|対応|方法|やり方|手続|設定|再起動|再初期化|初期化|実行|削除|インストール|登録|切り替え|切替|変更|"
        r"してください|して下さい|すること|する場合|した場合|ときは|時は|コマンド|クリック|選択|入力|押す|押して",
        re.MULTILINE,
    ),
    "reason": re.compile(r"ため|原因|理由|背景|なぜ|から|ので|により|によって|起因|要因|狙い|目的|きっかけ|経緯"),
    "compare": re.compile(r"違い|違う|一方|に対して|比較|vs|対比|より|差|メリット|デメリット|長所|短所|利点|欠点|同じ|異なる"),
    "definition": re.compile(r"とは|である|を指す|の略|意味|定義|と呼ぶ|というのは|とも言う|略称|正式名称|概要|とは何"),
    "condition": re.compile(r"場合|とき|時|条件|禁止|必須|必ず|してはならない|不可|可能|できる|できない|限り|以上|以下|未満|超え|除く|対象"),
}
_ANSWER_FORM_CUES["procedure"] = _ANSWER_FORM_CUES["how_to"]
_ANSWER_FORM_CUES["specification"] = re.compile(r"\|.*\||仕様|形式|フォーマット|構成|項目|カラム|フィールド|型|単位|byte|バイト|文字|桁")
_ANSWER_FORM_MIN_HITS = 2  # distinct cue matches for a full score (1 hit → 0.5)


def answer_form_match(intent: str, text: str) -> float | None:
    """How much a chunk *reads like* the answer form the intent asks for
    (None when the intent has no form cues, e.g. lookup / search_value)."""
    pat = _ANSWER_FORM_CUES.get(intent)
    if pat is None:
        return None
    hits = len({m.group(0) for m in pat.finditer(text)})
    return min(1.0, hits / _ANSWER_FORM_MIN_HITS)


def retrieval_features(query: QueryIR) -> dict:
    """Signals a retriever can use for lexical / vector search and filtering (FR-083)."""
    return {
        "normalized_query": query.normalized_query,
        "keywords": list(query.keywords),
        "expanded_terms": list(query.expanded_terms),
        "search_terms": list(dict.fromkeys([*query.keywords, *query.expanded_terms])),
        "entities": [
            {"type": e.type, "surface": e.surface, "normalized": e.normalized, "value": e.value}
            for e in query.entities
        ],
        "intent": query.intent,
        "answer_type": query.answer_type,
        "target": query.target,
        "filters": {k: list(v) for k, v in query.constraints.items()},
        "sentiment": query.sentiment,
    }


@dataclass
class ChunkView:
    """The pieces of a chunk the reranker looks at (built from a document IR)."""

    text: str
    entities: list[tuple[str, str, str | None, object]] = field(default_factory=list)  # (type, surface, normalized, value)
    keywords: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    sentiment: str | None = None
    entity_types: set[str] = field(default_factory=set)

    @classmethod
    def from_chunk(cls, chunk: DocumentChunk, doc: AnalysisResult) -> ChunkView:
        by_id = {e.id: e for e in doc.entities}
        ents = [by_id[i] for i in chunk.entity_ids if i in by_id]
        sentiment: str | None = None
        votes: dict[str, int] = {}
        for sid in chunk.sentence_ids:
            s = doc.sentences[sid] if sid < len(doc.sentences) else None
            if s is not None and s.sentiment and s.sentiment.polarity:
                votes[s.sentiment.polarity] = votes.get(s.sentiment.polarity, 0) + 1
        if votes:
            sentiment = max(votes, key=votes.get)
        return cls(
            text=chunk.text_with_context,
            entities=[(e.type, e.surface, e.normalized, e.value) for e in ents],
            keywords=list(chunk.keywords),
            topics=list(chunk.topics),
            sentiment=sentiment,
            entity_types={e.type for e in ents},
        )

    @classmethod
    def from_result(cls, result: AnalysisResult) -> ChunkView:
        topics = [t.label for t in result.topics.topics] if result.topics else []
        return cls(
            text=result.text.original,
            entities=[(e.type, e.surface, e.normalized, e.value) for e in result.entities],
            keywords=list(result.rag.keywords) if result.rag else [],
            topics=topics,
            sentiment=result.sentiment.polarity if result.sentiment else None,
            entity_types={e.type for e in result.entities},
        )


def _fiscal_year(iso: str) -> str | None:
    """FY of an ISO date / month (April start): 2026-04-01 → FY2026, 2027-03 → FY2026."""
    if len(iso) < 7 or not iso[:4].isdigit() or not iso[5:7].isdigit():
        return f"FY{iso[:4]}" if len(iso) == 4 and iso.isdigit() else None
    y, m = int(iso[:4]), int(iso[5:7])
    return f"FY{y if m >= 4 else y - 1}"


def time_compatible(constraint: str, value: str) -> bool:
    """Does a chunk DATE/TIME value satisfy a query time constraint?

    Granularity-aware: FY2026 ⟷ any date in 2026-04 … 2027-03 or the year
    2026; 2026 ⟷ any 2026-xx-xx; 2026-10 ⟷ 2026-10-05; exact otherwise.
    """
    c, v = str(constraint), str(value)
    if c == v:
        return True
    if c.startswith("FY"):
        return v == c or (_fiscal_year(v) == c) or (len(v) == 4 and v == c[2:])
    if v.startswith("FY"):
        return _fiscal_year(c) == v
    if len(c) == 4 and c.isdigit():
        return v[:4] == c
    if len(c) == 7 and c[4] == "-":
        return v[:7] == c
    return False


def rrf_fuse(*rankings: list[int], k: int = 60) -> list[int]:
    """Reciprocal-rank fusion of several rankings (ids). Robust way to add a
    synonym-expanded query on top of the raw one without letting expansion
    noise override exact matches."""
    score: dict[int, float] = {}
    for ranking in rankings:
        for pos, i in enumerate(ranking):
            score[i] = score.get(i, 0.0) + 1.0 / (k + pos + 1)
    return sorted(score, key=lambda i: -score[i])


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


_ASCII_WORD = re.compile(r"^[A-Za-z0-9_]+$")
_ASCII_WORD_CHAR = re.compile(r"[A-Za-z0-9_]")


def _contains_term(term: str, text: str) -> bool:
    """Substring containment, but boundary-safe for ASCII identifier-like terms
    (e.g. product codes, API names): "AP" must not match inside "API". Plain
    Japanese terms fall back to raw substring containment — CJK text has no
    reliable word-boundary marker, so this only guards the case that actually
    produced false positives (Zenn#4: keyword/entity overlap on a dictionary
    fragment like "AP" ⊂ "API")."""
    if not term:
        return False
    if not _ASCII_WORD.match(term):
        return term in text
    start = 0
    while True:
        idx = text.find(term, start)
        if idx == -1:
            return False
        before = text[idx - 1] if idx > 0 else ""
        after_pos = idx + len(term)
        after = text[after_pos] if after_pos < len(text) else ""
        if not _ASCII_WORD_CHAR.match(before) and not _ASCII_WORD_CHAR.match(after):
            return True
        start = idx + 1


def rerank_features(query: QueryIR, chunk: ChunkView) -> dict[str, float | None]:
    """Per-signal match scores in [0, 1]; None when the query carries no such signal."""
    text = chunk.text
    # entity_match: query entities found in the chunk (by normalized value, surface, or text containment)
    if query.entities:
        hits = 0
        chunk_keys = set()
        for typ, surf, norm, value in chunk.entities:
            chunk_keys.update({surf, norm or "", str(value) if value is not None else ""})
        for qe in query.entities:
            keys = {qe.surface, qe.normalized or "", str(qe.value) if qe.value is not None else ""} - {""}
            if keys & chunk_keys or any(k and _contains_term(k, text) for k in keys):
                hits += 1
        entity_match: float | None = hits / len(query.entities)
    else:
        entity_match = None

    # keyword_overlap: query terms (+ synonyms) vs chunk keywords / text
    # keyword_overlap: the query's own terms count fully, synonym expansions
    # only EXPANSION_WEIGHT — an expansion that misses must not dilute a chunk
    # that matches the words the user actually typed.
    own = set(query.keywords)
    if query.target:
        own.add(query.target)
    exp = set(query.expanded_terms) - own
    if own or exp:
        hit_own = sum(1 for t in own if t in chunk.keywords or _contains_term(t, text))
        hit_exp = sum(1 for t in exp if t in chunk.keywords or _contains_term(t, text))
        denom = len(own) + EXPANSION_WEIGHT * len(exp)
        keyword_overlap: float | None = (hit_own + EXPANSION_WEIGHT * hit_exp) / denom if denom else None
    else:
        keyword_overlap = None

    # intent_match: does the chunk contain the kind of answer the query asks for?
    # Typed answers (MONEY / DATE / …) → the chunk has such an entity;
    # TEXT answers (how_to / reason / compare / definition / condition / …) → the
    # chunk reads like that kind of answer (answer_form_match).
    wanted = _ANSWER_TYPE_ENTITY.get(query.answer_type or "")
    if wanted:
        intent_match: float | None = 1.0 if chunk.entity_types & wanted else 0.0
    else:
        intent_match = answer_form_match(query.intent, text)

    # time_match: query time constraints vs chunk DATE/TIME values
    q_times = set(query.constraints.get("time", []))
    if q_times:
        c_times = {str(v) for typ, _s, n, v in chunk.entities if typ in ("DATE", "TIME") for v in (v, n) if v}
        hit = any(time_compatible(q, c) for q in q_times for c in c_times) or any(t in text for t in q_times)
        time_match: float | None = 1.0 if hit else 0.0
    else:
        time_match = None

    # topic_match: query target / keywords vs chunk topics
    q_topics = set(query.keywords)
    if query.target:
        q_topics.add(query.target)
    topic_match = _jaccard(q_topics, set(chunk.topics)) if q_topics and chunk.topics else (None if not q_topics else 0.0)
    if topic_match is not None and topic_match == 0.0 and any(t in " ".join(chunk.topics) for t in q_topics):
        topic_match = 0.5

    # sentiment_match
    if query.sentiment in ("positive", "negative"):
        sentiment_match: float | None = 1.0 if chunk.sentiment == query.sentiment else (0.0 if chunk.sentiment else 0.5)
    else:
        sentiment_match = None

    return {
        "entity_match": entity_match,
        "keyword_overlap": keyword_overlap,
        "intent_match": intent_match,
        "time_match": time_match,
        "topic_match": topic_match,
        "sentiment_match": sentiment_match,
    }


def rerank_score(
    features: dict[str, float | None],
    *,
    semantic_similarity: float | None = None,
    lexical_similarity: float | None = None,
    retrieval_score: float | None = None,
    weights: dict[str, float] | None = None,
) -> float:
    """Weighted sum over the available signals, renormalized to the weights present.

    Two weight sets are built in:
    - lexical path (default): ``semantic_similarity`` carries the retriever's
      own score (BM25 normalized, or a vector similarity) — DEFAULT_WEIGHTS;
    - hybrid path: when ``retrieval_score`` (the fused, normalized retrieval
      score) is given, HYBRID_WEIGHTS is used automatically — the fused
      ranking dominates and IR matches only nudge it.
    ``weights`` overrides individual entries of whichever set is active.
    """
    w = dict(HYBRID_WEIGHTS if retrieval_score is not None else DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)
    feats = dict(features)
    feats["semantic_similarity"] = semantic_similarity
    feats["lexical_similarity"] = lexical_similarity
    feats["retrieval_score"] = retrieval_score
    total = 0.0
    wsum = 0.0
    for name, value in feats.items():
        if value is None or name not in w:
            continue
        total += w[name] * value
        wsum += w[name]
    return round(total / wsum, 4) if wsum else 0.0


def rerank(
    query: QueryIR,
    chunks: list[ChunkView],
    *,
    similarities: list[float] | None = None,
    weights: dict[str, float] | None = None,
) -> list[tuple[int, float, dict[str, float | None]]]:
    """Score every chunk; returns (index, score, features) sorted by score desc."""
    out: list[tuple[int, float, dict[str, float | None]]] = []
    for i, c in enumerate(chunks):
        f = rerank_features(query, c)
        sim = similarities[i] if similarities is not None and i < len(similarities) else None
        out.append((i, rerank_score(f, semantic_similarity=sim, weights=weights), f))
    out.sort(key=lambda x: -x[1])
    return out
