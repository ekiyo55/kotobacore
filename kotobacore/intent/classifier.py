"""Compatibility shim: moved to kotobacore.modules.intent (v0.3). Deprecated since 0.6.4, removed in 1.1."""

import kotobacore.modules.intent as _m
from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.intent.classifier', 'kotobacore.modules.intent')

globals().update({k: v for k, v in vars(_m).items() if not k.startswith('__')})
del _m
