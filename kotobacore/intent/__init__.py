"""Compatibility shim: use kotobacore.modules.intent (deprecated since 0.6.4, removed in 1.1)."""

from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.intent', 'kotobacore.modules.intent')

from kotobacore.modules.intent import classify_intent

__all__ = ["classify_intent"]
