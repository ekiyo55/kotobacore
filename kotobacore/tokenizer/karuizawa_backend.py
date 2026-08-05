"""Karuizawa tokenizer backend — zero external dependencies.

Splits on character-category boundaries (kanji / katakana / hiragana /
latin / digit / symbol).  The ``mode`` parameter is accepted for API
compatibility but ignored: Karuizawa has a single granularity level.
"""

from __future__ import annotations

from kotobacore.schema import Token
from kotobacore.tokenizer.base import TokenizerBackend

_CAT_KANJI    = "KANJI"
_CAT_KATAKANA = "KATAKANA"
_CAT_HIRAGANA = "HIRAGANA"
_CAT_LATIN    = "LATIN"
_CAT_DIGIT    = "DIGIT"
_CAT_SYMBOL   = "SYMBOL"
_CAT_SPACE    = "SPACE"

# POS strings — must contain "名詞" / "助詞" substrings so that downstream
# consumers (semantic/builder.py checks ``"名詞" in pos``) work correctly.
_POS: dict[str, str] = {
    _CAT_KANJI:    "名詞-普通名詞-一般",
    _CAT_KATAKANA: "名詞-普通名詞-一般",
    _CAT_LATIN:    "名詞-普通名詞-一般",
    _CAT_DIGIT:    "名詞-数詞",
    _CAT_HIRAGANA: "助詞",
    _CAT_SYMBOL:   "記号",
    _CAT_SPACE:    "空白",
}


def _char_cat(ch: str) -> str:
    cp = ord(ch)
    # Hiragana U+3040–U+309F
    if 0x3040 <= cp <= 0x309F:
        return _CAT_HIRAGANA
    # Katakana: standard U+30A0–U+30FF, phonetic ext U+31F0–U+31FF, half-width U+FF65–U+FF9F
    if 0x30A0 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF or 0xFF65 <= cp <= 0xFF9F:
        return _CAT_KATAKANA
    # CJK Unified Ideographs (kanji) and compatibility ideographs
    if (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            or 0xF900 <= cp <= 0xFAFF or 0x20000 <= cp <= 0x2A6DF):
        return _CAT_KANJI
    # ASCII letters + full-width Latin (Ａ-Ｚ ａ-ｚ)
    if (0x41 <= cp <= 0x5A or 0x61 <= cp <= 0x7A
            or 0xFF21 <= cp <= 0xFF3A or 0xFF41 <= cp <= 0xFF5A):
        return _CAT_LATIN
    # ASCII digits + full-width digits ０-９
    if 0x30 <= cp <= 0x39 or 0xFF10 <= cp <= 0xFF19:
        return _CAT_DIGIT
    # Whitespace
    if ch in (' ', '\t', '\n', '\r') or cp in (0x3000, 0x00A0):
        return _CAT_SPACE
    return _CAT_SYMBOL


def _make_token(tok_id: int, text: str, begin: int, end: int, cat: str) -> Token:
    surface = text[begin:end]
    return Token(
        id=tok_id,
        surface=surface,
        normalized=surface,
        dictionary_form=surface,
        reading=None,
        pos=_POS[cat],
        begin=begin,
        end=end,
        unknown=(cat in (_CAT_SYMBOL, _CAT_SPACE)),
    )


class KaruizawaBackend(TokenizerBackend):
    """Character-category boundary tokenizer.  No external dependencies."""

    def tokenize(self, text: str, mode: str = "C") -> list[Token]:
        if not text:
            return []

        raw: list[Token] = []
        seg_start = 0
        seg_cat = _char_cat(text[0])

        for i, ch in enumerate(text):
            cat = _char_cat(ch)
            if cat != seg_cat:
                raw.append(_make_token(len(raw), text, seg_start, i, seg_cat))
                seg_start = i
                seg_cat = cat

        raw.append(_make_token(len(raw), text, seg_start, len(text), seg_cat))

        # Drop whitespace-only segments; renumber ids to be contiguous.
        result = [t for t in raw if t.pos != "空白"]
        for new_id, t in enumerate(result):
            t.id = new_id
        return result
