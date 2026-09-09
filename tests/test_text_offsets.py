"""FR-002 (v0.4): N1/N2 normalization keeps a map back to original offsets."""

from kotobacore import Analyzer
from kotobacore.core.text import NormalizedText, normalize, normalize_with_map


def _check_map(nt: NormalizedText) -> None:
    assert len(nt.origin) == len(nt.normalized)
    assert all(0 <= o < len(nt.original) for o in nt.origin)
    assert all(a <= b for a, b in zip(nt.origin, nt.origin[1:]))  # monotone
    for j in range(len(nt.normalized)):
        b, e = nt.to_original_span(j, j + 1)
        assert b < e <= len(nt.original)


def test_identity_when_nothing_changes():
    nt = normalize_with_map("東京に行った。")
    assert nt.normalized == "東京に行った。"
    assert nt.origin == list(range(7))
    assert nt.to_original_span(3, 6) == (3, 6)


def test_nfkc_expansion_points_at_source_char():
    nt = normalize_with_map("㈱テスト")
    assert nt.normalized == "(株)テスト"
    assert nt.origin[:3] == [0, 0, 0]
    assert nt.to_original_span(0, 3) == (0, 1)
    _check_map(nt)


def test_nfkc_contraction_halfwidth_dakuten():
    nt = normalize_with_map("ﾊﾟﾝﾀﾞ")
    assert nt.normalized == "パンダ"
    assert nt.origin == [0, 2, 3]
    assert nt.to_original_span(0, 1) == (0, 1)
    assert nt.to_original_span(2, 3) == (3, 4)
    _check_map(nt)


def test_fullwidth_alnum_is_one_to_one():
    nt = normalize_with_map("ＡＢＣ１２３")
    assert nt.normalized == "ABC123"
    assert nt.origin == [0, 1, 2, 3, 4, 5]


def test_crlf_and_control_chars():
    nt = normalize_with_map("a\r\nb\x00c")
    assert nt.normalized == "a\nbc"
    assert nt.origin == [0, 1, 3, 5]
    assert normalize("a\r\nb") == "a\nb"


def test_hyphen_between_katakana_becomes_long_vowel():
    nt = normalize_with_map("コ-ヒ-を飲む")
    assert nt.normalized.startswith("コーヒ")
    assert len(nt.origin) == len(nt.normalized)


def test_n2_rules_longest_match_and_idempotent():
    rules = {"(株)": "株式会社", "プリンタ": "プリンター", "サーバ": "サーバー"}
    nt = normalize_with_map("㈱ABCのプリンターとサーバとユーザビリティ", rules)
    assert nt.normalized == "株式会社ABCのプリンターとサーバーとユーザビリティ"
    assert nt.to_original_span(0, 4) == (0, 1)  # 株式会社 ← ㈱
    _check_map(nt)
    # applying again changes nothing
    again = normalize_with_map(nt.normalized, rules)
    assert again.normalized == nt.normalized


def test_n2_katakana_rule_needs_word_end():
    rules = {"ユーザ": "ユーザー"}
    assert normalize_with_map("ユーザビリティ", rules).normalized == "ユーザビリティ"
    assert normalize_with_map("ユーザ登録", rules).normalized == "ユーザー登録"


def test_analyzer_token_spans_are_original_coordinates():
    a = Analyzer()
    text = "㈱ＡＢＣは昨日コ-ヒ-を飲んだ"
    r = a.analyze(text)
    assert r.text.original == text
    assert len(r.text.offset_map) == len(r.text.normalized)
    for tok in r.tokens:
        assert 0 <= tok.begin < tok.end <= len(text)
    assert text[r.tokens[0].begin : r.tokens[0].end] == "㈱"
    assert r.tokens[0].surface == "株式会社"
    # 昨日 is untouched by normalization → identical span
    kinou = next(t for t in r.tokens if t.surface == "昨日")
    assert text[kinou.begin : kinou.end] == "昨日"


def test_tokenize_remaps_too():
    a = Analyzer()
    toks = a.tokenize("ＡＢＣを見た")
    assert toks[0].surface == "ABC"
    assert (toks[0].begin, toks[0].end) == (0, 3)


def test_bundled_normalization_rules_apply():
    a = Analyzer()
    assert a.normalize("髙橋さんは(一社)日本協会の“理事”だ") == '高橋さんは一般社団法人日本協会の"理事"だ'
    assert a.normalize("ヴァイオリン") == "バイオリン"
