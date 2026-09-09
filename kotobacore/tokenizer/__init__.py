"""Compatibility shim: use kotobacore.core.token (deprecated since 0.6.4, removed in 1.1)."""

from kotobacore._compat import deprecated_module as _dep

_dep('kotobacore.tokenizer', 'kotobacore.core.token')

from kotobacore.core.token.base import TokenizerBackend
from kotobacore.core.token.karuizawa_backend import KaruizawaBackend
from kotobacore.core.token.token_normalizer import (
    fold_emphatic_reduplication,
    heuristic_proper_noun_merge,
    merge_keep_as_unit,
    merge_okurigana_compounds,
    refine_verb_adjective_pos,
    split_hiragana_tokens,
)

__all__ = [
    "KaruizawaBackend",
    "TokenizerBackend",
    "fold_emphatic_reduplication",
    "heuristic_proper_noun_merge",
    "merge_keep_as_unit",
    "merge_okurigana_compounds",
    "refine_verb_adjective_pos",
    "split_hiragana_tokens",
]
