"""Compatibility shim: use kotobacore.core.text (deprecated since 0.6.4, removed in 2.0)."""

from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.normalizer', 'kotobacore.core.text')

from kotobacore.core.text import normalize

__all__ = ["normalize"]
