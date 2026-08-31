"""Tokenizer backend abstraction for KotobaCore."""

from kotobacore.tokenizer.base import TokenizerBackend
from kotobacore.tokenizer.karuizawa_backend import KaruizawaBackend
from kotobacore.tokenizer.token_normalizer import (
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
