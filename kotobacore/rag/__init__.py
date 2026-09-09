"""RAG optimization layer for KotobaCore."""

from kotobacore.rag.chunk import chunk_document
from kotobacore.rag.features import (
    HYBRID_ALPHA,
    ChunkView,
    answer_form_match,
    hybrid_alpha,
    query_lexical_anchors,
    rerank,
    rerank_features,
    rerank_score,
    retrieval_features,
    rrf_fuse,
)
from kotobacore.rag.optimizer import optimize_rag
from kotobacore.rag.query import build_query_ir
from kotobacore.rag.retriever import InMemoryRetriever, PgVectorRetriever

__all__ = [
    "HYBRID_ALPHA", "ChunkView", "InMemoryRetriever", "PgVectorRetriever", "answer_form_match", "build_query_ir",
    "chunk_document", "hybrid_alpha", "optimize_rag", "query_lexical_anchors", "rerank", "rerank_features",
    "rerank_score", "retrieval_features", "rrf_fuse",
]
