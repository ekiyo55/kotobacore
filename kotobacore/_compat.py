"""Deprecation helper for the pre-v0.3 import paths (kotobacore.schema / normalizer / tokenizer / semantic / emotion / intent / clause / matching).

Policy (要件定義書 §3.2): the old paths stay importable through v1.0, warn from
0.6.4, and are removed in 1.1. The warning fires once per old module, at import.
"""

from __future__ import annotations

import warnings

DEPRECATED_SINCE = "0.6.4"
REMOVED_IN = "1.1"


class KotobaCoreDeprecationWarning(DeprecationWarning):
    """Import-path deprecation raised by the compatibility shims."""


def deprecated_module(old: str, new: str) -> None:
    warnings.warn(
        f"{old} is deprecated since KotobaCore {DEPRECATED_SINCE} and will be removed in {REMOVED_IN}; import {new} instead",
        KotobaCoreDeprecationWarning,
        stacklevel=3,
    )
