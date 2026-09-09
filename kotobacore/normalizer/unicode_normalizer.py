"""Compatibility shim: moved to kotobacore.core.text (v0.3). Deprecated since 0.6.4, removed in 1.1."""

import kotobacore.core.text as _m
from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.normalizer.unicode_normalizer', 'kotobacore.core.text')

globals().update({k: v for k, v in vars(_m).items() if not k.startswith('__')})
del _m
