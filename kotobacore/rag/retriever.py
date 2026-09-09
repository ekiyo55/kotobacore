"""Reference retriever adapters (FR-083 参照アダプタ).

KotobaCore never embeds or stores vectors itself; these adapters show how a
retriever consumes the Query IR and the document IR:

- :class:`InMemoryRetriever` — pure-Python reference implementation. Chunks
  are indexed with an *external* ``embed`` callable (any model: e5, OpenAI,
  …); search = cosine similarity → KotobaCore reranking (rag.features).
  Fully testable without a database.
- :class:`PgVectorRetriever` — builds the SQL a pgvector + external
  embedding setup needs (the configuration used by the Spark RAG library:
  pgvector, multilingual-e5-base). It only *generates* statements and
  parameters; execution is left to the caller's psycopg connection so the
  core stays dependency-free.

Both take the same inputs: ``DocumentChunk`` lists from
``Analyzer.analyze_document`` and a ``QueryIR`` from ``Analyzer.analyze_query``.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from kotobacore.core.ir import AnalysisResult, DocumentChunk, QueryIR
from kotobacore.rag.features import ChunkView, rerank_features, rerank_score, retrieval_features

Embedder = Callable[[Sequence[str]], Sequence[Sequence[float]]]


@dataclass
class IndexedChunk:
    doc_id: str
    chunk: DocumentChunk
    view: ChunkView
    vector: list[float] = field(default_factory=list)


@dataclass
class Hit:
    doc_id: str
    chunk_id: int
    text: str
    score: float
    similarity: float | None
    features: dict[str, float | None]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class InMemoryRetriever:
    """Reference hybrid retriever: external embeddings + KotobaCore reranking."""

    def __init__(self, embed: Embedder | None = None, *, weights: dict[str, float] | None = None) -> None:
        self.embed = embed
        self.weights = weights
        self._items: list[IndexedChunk] = []

    def index(self, doc_id: str, doc: AnalysisResult) -> int:
        chunks = doc.document_chunks
        vectors: list[list[float]] = []
        if self.embed is not None and chunks:
            vectors = [list(v) for v in self.embed([c.text for c in chunks])]
        for i, c in enumerate(chunks):
            self._items.append(IndexedChunk(doc_id, c, ChunkView.from_chunk(c, doc), vectors[i] if vectors else []))
        return len(chunks)

    def __len__(self) -> int:
        return len(self._items)

    def search(self, query: QueryIR, *, k: int = 5, candidates: int = 50) -> list[Hit]:
        if not self._items:
            return []
        sims: list[float | None] = [None] * len(self._items)
        if self.embed is not None and any(it.vector for it in self._items):
            qv = list(self.embed([query.normalized_query or query.original])[0])
            sims = [(_cosine(qv, it.vector) if it.vector else None) for it in self._items]
            order = sorted(range(len(self._items)), key=lambda i: -(sims[i] or 0.0))[:candidates]
        else:
            order = list(range(len(self._items)))
        hits: list[Hit] = []
        for i in order:
            it = self._items[i]
            feats = rerank_features(query, it.view)
            score = rerank_score(feats, semantic_similarity=sims[i], weights=self.weights)
            hits.append(Hit(it.doc_id, it.chunk.id, it.chunk.text, score, sims[i], feats))
        hits.sort(key=lambda h: -h.score)
        return hits[:k]


class PgVectorRetriever:
    """SQL generator for a pgvector table fed with KotobaCore chunks.

    Expected table (create with :meth:`ddl`)::

        chunks(id serial, doc_id text, chunk_id int, text text, keywords text[],
               topics text[], entities jsonb, dates text[], embedding vector(N))

    The caller runs the statements with its own connection and embedding model.
    """

    def __init__(self, table: str = "kotobacore_chunks", dim: int = 768) -> None:
        self.table = table
        self.dim = dim

    def ddl(self) -> str:
        return (
            f"CREATE EXTENSION IF NOT EXISTS vector;\n"
            f"CREATE TABLE IF NOT EXISTS {self.table} (\n"
            f"  id serial PRIMARY KEY, doc_id text NOT NULL, chunk_id int NOT NULL, text text NOT NULL,\n"
            f"  keywords text[] DEFAULT '{{}}', topics text[] DEFAULT '{{}}', entities jsonb DEFAULT '[]',\n"
            f"  dates text[] DEFAULT '{{}}', embedding vector({self.dim})\n"
            f");\n"
            f"CREATE INDEX IF NOT EXISTS {self.table}_embedding_idx ON {self.table} USING hnsw (embedding vector_cosine_ops);\n"
            f"CREATE INDEX IF NOT EXISTS {self.table}_keywords_idx ON {self.table} USING gin (keywords);\n"
        )

    def insert_rows(self, doc_id: str, doc: AnalysisResult, vectors: Sequence[Sequence[float]]) -> list[tuple[str, tuple]]:
        """(sql, params) per chunk — pass to ``cursor.execute``."""
        by_id = {e.id: e for e in doc.entities}
        rows: list[tuple[str, tuple]] = []
        sql = (
            f"INSERT INTO {self.table} (doc_id, chunk_id, text, keywords, topics, entities, dates, embedding) "
            f"VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::vector)"
        )
        import json

        for c, vec in zip(doc.document_chunks, vectors):
            ents = [by_id[i] for i in c.entity_ids if i in by_id]
            rows.append((sql, (
                doc_id, c.id, c.text, list(c.keywords), list(c.topics),
                json.dumps([{"type": e.type, "surface": e.surface, "normalized": e.normalized, "value": e.value} for e in ents], ensure_ascii=False),
                [str(e.value or e.normalized) for e in ents if e.type in ("DATE", "TIME") and (e.value or e.normalized)],
                "[" + ",".join(f"{x:.6f}" for x in vec) + "]",
            )))
        return rows

    def search_sql(self, query: QueryIR, *, k: int = 20) -> tuple[str, dict]:
        """Candidate retrieval: cosine order with optional keyword / date filters
        derived from the Query IR (FR-083 filters). Rerank the rows with
        :func:`kotobacore.rag.features.rerank` afterwards."""
        feats = retrieval_features(query)
        where: list[str] = []
        params: dict = {"k": k}
        terms = feats["search_terms"]
        if terms:
            where.append("(keywords && %(terms)s OR text ILIKE ANY(%(like_terms)s))")
            params["terms"] = terms
            params["like_terms"] = [f"%{t}%" for t in terms]
        dates = feats["filters"].get("time")
        if dates:
            where.append("dates && %(dates)s")
            params["dates"] = [str(d) for d in dates]
        sql = (
            f"SELECT doc_id, chunk_id, text, keywords, topics, entities, dates, "
            f"1 - (embedding <=> %(qvec)s::vector) AS similarity FROM {self.table}"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY embedding <=> %(qvec)s::vector LIMIT %(k)s"
        params["qvec"] = None  # caller fills in "[...]" from its embedding model
        return sql, params
