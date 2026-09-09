"""Compatibility shim: moved to kotobacore.core.ir (v0.3). Deprecated since 0.6.4, removed in 1.1."""

import kotobacore.core.ir as _m
from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.schema', 'kotobacore.core.ir')

globals().update({k: v for k, v in vars(_m).items() if not k.startswith('__')})
del _m
