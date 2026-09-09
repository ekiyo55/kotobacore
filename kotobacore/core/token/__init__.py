"""Token layer (Karuizawa tokenizer + token normalizer)."""

# Karuizawa segmentation version (§8: bumped whenever segmentation output changes).
# Unified to 1.0 at KotobaCore 1.0.0 (2026-09-09). Pre-1.0 internal lineage, for the record:
#   cascade pipeline (≤ v0.1) → lattice + Viterbi (v0.2) → granularity="fine" (v0.2.6) → onomatopoeia /
#   repetition (v0.2.7) → evaluative-word nodes (v0.5.x) → okurigana variant nodes + 仮定形 tails (v0.6.3, "2.4")
TOKENIZER_VERSION = "1.0"

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
