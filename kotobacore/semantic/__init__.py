"""Compatibility shim: use kotobacore.core.entity / kotobacore.core.chunker (deprecated since 0.6.4, removed in 1.1)."""

from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.semantic', 'kotobacore.core.entity / kotobacore.core.chunker')

from kotobacore.core.chunker import chunk
from kotobacore.core.entity import build_semantic_tokens

__all__ = ["build_semantic_tokens", "chunk"]
