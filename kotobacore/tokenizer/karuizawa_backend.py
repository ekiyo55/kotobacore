"""Compatibility shim: moved to kotobacore.core.token.karuizawa_backend (v0.3). Deprecated since 0.6.4, removed in 1.1."""

import kotobacore.core.token.karuizawa_backend as _m
from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.tokenizer.karuizawa_backend', 'kotobacore.core.token.karuizawa_backend')

globals().update({k: v for k, v in vars(_m).items() if not k.startswith('__')})
del _m
