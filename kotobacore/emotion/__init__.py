"""Compatibility shim: use kotobacore.modules.emotion (deprecated since 0.6.4, removed in 1.1)."""

from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.emotion', 'kotobacore.modules.emotion')

from kotobacore.modules.emotion import detect_emotion

__all__ = ["detect_emotion"]
