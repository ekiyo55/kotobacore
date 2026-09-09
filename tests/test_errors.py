"""v0.6.8: error handling (要件定義書 §9, v1.0 完成条件「エラー処理テスト (E1xx〜E7xx)」).

Recoverable errors never stop the analysis: the stage falls back or is skipped and a
KotobaError (code / level / message / position / recoverable) lands in IR.errors."""

import pytest

from kotobacore import Analyzer
from kotobacore.errors import (
    E101_INVALID_UTF8,
    E102_UNSUPPORTED_CHARACTER,
    E201_TOKENIZATION_ERROR,
    E302_ENTITY_ERROR,
    E401_MODULE_ERROR,
    E601_VOCAB_VERSION_MISMATCH,
    VocabVersionMismatch,
    make_error,
)


def test_e1xx_invalid_utf8_bytes_are_decoded_and_recorded():
    a = Analyzer()
    r = a.analyze("最高".encode() + b"\xff\xfe" + "だった".encode())
    assert any(e.code == E101_INVALID_UTF8 and e.recoverable and e.position == 6 for e in r.errors)
    assert r.emotion.primary == "joy"  # the analysis still ran on the repaired text
    assert a.analyze("最高".encode()).errors == []  # valid bytes: no error


def test_e1xx_unsupported_character_is_stripped_and_recorded():
    r = Analyzer().analyze("嬉しい\ud83dね")  # lone surrogate
    assert any(e.code == E102_UNSUPPORTED_CHARACTER for e in r.errors)
    assert "\ud83d" not in r.text.original and r.emotion.primary == "joy"


def test_non_text_input_is_a_type_error():
    with pytest.raises(TypeError):
        Analyzer().analyze(123)  # type: ignore[arg-type]


def test_e201_tokenization_failure_falls_back_to_characters(monkeypatch):
    import kotobacore.analyzer as mod

    def boom(*_a, **_k):
        raise RuntimeError("lattice exploded")

    monkeypatch.setattr(mod, "lattice_tokenize", boom)
    r = Analyzer().analyze("東京に行った")
    assert any(e.code == E201_TOKENIZATION_ERROR and "lattice exploded" in e.message for e in r.errors)
    assert [t.surface for t in r.tokens] == list("東京に行った")  # character fallback, spans intact
    assert r.tokens[-1].end == 6 and r.meta.schema_version


def test_e3xx_e4xx_stage_exceptions_are_isolated(monkeypatch):
    import kotobacore.analyzer as mod

    def boom(*_a, **_k):
        raise ValueError("entity stage broke")

    monkeypatch.setattr(mod, "extract_entities", boom)
    monkeypatch.setattr(mod, "detect_emotion", boom)
    r = Analyzer().analyze("田中さんが東京で最高の一日を過ごした。")
    codes = {e.code for e in r.errors}
    assert E302_ENTITY_ERROR in codes and E401_MODULE_ERROR in codes
    assert r.entities == [] and r.emotion is not None and r.emotion.primary is None
    assert r.sentiment is not None and r.intent is not None and r.tokens  # the rest of the pipeline still ran
    assert all(e.recoverable and e.level == "warning" for e in r.errors)


def test_document_collects_sentence_errors_with_document_positions():
    r = Analyzer().analyze_document("一行目。\n" + "二行目は\ud83dです。")
    assert any(e.code == E102_UNSUPPORTED_CHARACTER and e.position is not None and e.position >= 5 for e in r.errors)
    assert len(r.sentences) == 2


def test_errors_serialize_in_json():
    r = Analyzer().analyze(b"\xff")
    payload = r.to_dict()
    assert payload["errors"] and payload["errors"][0]["code"].startswith("E101")


def test_e6xx_vocab_version_mismatch():
    from kotobacore.vocab import VocabEncoder, Vocabulary, build_vocab

    v = build_vocab(["東京に行った。"])
    v.version = "kotobacore-vocab-2.0"
    with pytest.raises(VocabVersionMismatch, match="E601"):
        VocabEncoder(v)
    v.version = "something-else"
    with pytest.raises(VocabVersionMismatch):
        VocabEncoder(v)
    ok = Vocabulary.from_dict(build_vocab(["東京に行った。"]).to_dict())
    assert VocabEncoder(ok).encode("東京")  # same major → fine
    assert E601_VOCAB_VERSION_MISMATCH.startswith("E601")


def test_make_error_shape():
    e = make_error("E999 test", "msg", position=3, recoverable=False)
    assert (e.code, e.level, e.position, e.recoverable) == ("E999 test", "error", 3, False)
