"""Tests for normalizer per 07_テスト仕様 §5."""

from kotobacore.normalizer import normalize


def test_norm_001_zenkaku_alphanumeric_to_ascii():
    # NORM-001: Ｔｅｓｔ１２３ → Test123
    assert normalize("Ｔｅｓｔ１２３") == "Test123"


def test_norm_002_halfwidth_katakana_to_fullwidth():
    # NORM-002: ｶﾀｶﾅ → カタカナ
    assert normalize("ｶﾀｶﾅ") == "カタカナ"


def test_norm_003_circled_digit():
    # NORM-003: ① → 1
    assert normalize("①") == "1"


def test_norm_004_crlf_to_lf():
    # NORM-004: \r\n → \n
    assert normalize("改行\r\nテスト") == "改行\nテスト"


def test_norm_005_sns_expression_preserved():
    # NORM-005: しぬwww must NOT be over-normalized
    assert normalize("しぬwww") == "しぬwww"


def test_norm_006_emoji_preserved():
    # NORM-006: emoji must NOT be stripped
    assert normalize("😊最高") == "😊最高"


def test_empty_string():
    assert normalize("") == ""


def test_control_chars_stripped_except_newline_tab():
    # NUL is C-category but not in allowlist
    raw = "ab\x00cd"
    assert normalize(raw) == "abcd"
    # tab is preserved
    assert normalize("a\tb") == "a\tb"


def test_lone_cr_to_lf():
    assert normalize("a\rb") == "a\nb"


def test_normalize_idempotent():
    text = "OpenAI APIの課金高すぎてしぬw 😊"
    once = normalize(text)
    twice = normalize(once)
    assert once == twice


def test_analyzer_uses_normalizer():
    from kotobacore import Analyzer

    a = Analyzer()
    result = a.analyze("Ｔｅｓｔ")
    assert result.text.original == "Ｔｅｓｔ"
    assert result.text.normalized == "Test"
