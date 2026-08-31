"""Karuizawa tokenizer compatibility layer.

Public API:

    from kotobacore.compat import KaruizawaTokenizer, KaruizawaToken, TokenMode

    t = KaruizawaTokenizer()
    tokens = t.tokenize("東京都に行った", TokenMode.C)

Per 06_API仕様書 §16.
"""

from __future__ import annotations

from kotobacore.dictionary import DictionaryBundle, load_default_bundle
from kotobacore.tokenizer.karuizawa_backend import KaruizawaBackend
from kotobacore.tokenizer.token_normalizer import (
    fold_emphatic_reduplication,
    heuristic_proper_noun_merge,
    merge_keep_as_unit,
    merge_okurigana_compounds,
    refine_verb_adjective_pos,
    split_hiragana_tokens,
)


class TokenMode:
    """Tokenizer mode constants (accepted for API compatibility; Karuizawa has single granularity)."""

    A = "A"
    B = "B"
    C = "C"


class KaruizawaToken:
    """Thin wrapper exposing morpheme-style methods around a Token."""

    __slots__ = ("_t",)

    def __init__(self, token) -> None:
        self._t = token

    def surface(self) -> str:
        return self._t.surface

    def part_of_speech(self) -> tuple[str, ...]:
        return tuple(self._t.pos.split("-"))

    def dictionary_form(self) -> str:
        return self._t.dictionary_form

    def normalized_form(self) -> str:
        return self._t.normalized

    def reading_form(self) -> str:
        return self._t.reading or self._t.surface

    def begin(self) -> int:
        return self._t.begin

    def end(self) -> int:
        return self._t.end

    def __repr__(self) -> str:
        return f"KaruizawaToken({self.surface()!r})"


class KaruizawaTokenizer:
    """Karuizawa tokenizer with a morpheme-style API."""

    def __init__(self) -> None:
        self._backend = KaruizawaBackend()
        self._bundle: DictionaryBundle | None = None

    def _get_bundle(self) -> DictionaryBundle:
        if self._bundle is None:
            self._bundle = load_default_bundle()
        return self._bundle

    def tokenize(self, text: str, mode: str = TokenMode.C) -> list[KaruizawaToken]:
        bundle = self._get_bundle()
        raw = self._backend.tokenize(text, mode=mode)
        tokens = merge_keep_as_unit(raw, text, bundle)
        tokens = fold_emphatic_reduplication(tokens)
        tokens = split_hiragana_tokens(tokens, bundle)
        tokens = heuristic_proper_noun_merge(tokens, text)
        tokens = merge_okurigana_compounds(tokens)
        tokens = refine_verb_adjective_pos(tokens, bundle)
        return [KaruizawaToken(t) for t in tokens]
