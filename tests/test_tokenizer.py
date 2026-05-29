"""Tokenizer backend tests per 07_テスト仕様 §6."""

from kotobacore import Analyzer
from kotobacore.schema import Token
from kotobacore.tokenizer import KaruizawaBackend


def test_tok_001_tokenize_preserves_tokyo_to():
    # TOK-001: 東京都に行った — all kanji run stays together as one token
    backend = KaruizawaBackend()
    tokens = backend.tokenize("東京都に行った", mode="C")
    surfaces = [t.surface for t in tokens]
    assert "東京都" in surfaces


def test_tok_003_tokenize_charging():
    # TOK-003: 課金高すぎ — Karuizawa splits on character-category boundary:
    # kanji run "課金高" + hiragana run "すぎ"
    backend = KaruizawaBackend()
    tokens = backend.tokenize("課金高すぎ", mode="C")
    surfaces = [t.surface for t in tokens]
    assert "課金高" in surfaces
    assert "すぎ" in surfaces


def test_tokens_have_begin_end():
    backend = KaruizawaBackend()
    tokens = backend.tokenize("東京都に行った", mode="C")
    assert len(tokens) > 0
    for t in tokens:
        assert isinstance(t, Token)
        assert t.begin >= 0
        assert t.end >= t.begin


def test_unknown_word_does_not_crash():
    backend = KaruizawaBackend()
    tokens = backend.tokenize("ペポロロン", mode="C")
    assert isinstance(tokens, list)


def test_empty_text_returns_empty_list():
    backend = KaruizawaBackend()
    assert backend.tokenize("", mode="C") == []


def test_mode_ignored():
    # Karuizawa accepts mode param but ignores it (single granularity level)
    backend = KaruizawaBackend()
    a = backend.tokenize("北海道大学", mode="A")
    c = backend.tokenize("北海道大学", mode="C")
    assert [t.surface for t in a] == [t.surface for t in c]


def test_analyzer_tokenize_integration():
    a = Analyzer(mode="C")
    tokens = a.tokenize("東京都に行った")
    assert len(tokens) > 0
    assert all(isinstance(t, Token) for t in tokens)


def test_analyzer_tokenize_uses_normalizer():
    # 全角文字でも正規化されてから tokenize される
    a = Analyzer(mode="C")
    tokens = a.tokenize("Ｔｅｓｔ")
    # 正規化後 "Test" になっているはず
    text_joined = "".join(t.surface for t in tokens)
    assert "Test" in text_joined
