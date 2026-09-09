"""Compatibility shim: moved to kotobacore.modules.emotion (v0.3). Deprecated since 0.6.4, removed in 1.1."""

import kotobacore.modules.emotion as _m
from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.emotion.detector', 'kotobacore.modules.emotion')

globals().update({k: v for k, v in vars(_m).items() if not k.startswith('__')})
del _m
