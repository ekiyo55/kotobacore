"""Compatibility shim: moved to kotobacore.core.token.token_normalizer (v0.3). Deprecated since 0.6.4, removed in 1.1."""

import kotobacore.core.token.token_normalizer as _m
from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.tokenizer.token_normalizer', 'kotobacore.core.token.token_normalizer')

globals().update({k: v for k, v in vars(_m).items() if not k.startswith('__')})
del _m
