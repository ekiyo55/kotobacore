"""v0.6.8: 語彙汚染テスト (v1.0 完成条件、FR-072) — an OCR / scrape-damaged corpus must surface as contamination
candidates in vocab_report, and the clean pieces must stay clean."""

from kotobacore import Analyzer
from kotobacore.vocab import build_vocab, vocab_report
from kotobacore.vocab.evaluate import contamination_reasons

_FINE = Analyzer(granularity="fine", enable_emotion=False, enable_sentiment=False, enable_intent=False, enable_rag=False)

CLEAN = ["東京に行った。", "美味しいパンを買った。", "会議は十時からです。", "犬が走った。"] * 3
DIRTY = [
    "東京ｦ出発シﾀ。",            # halfwidth katakana (NFKC folds most; ｦ/ｼ/ﾀ exercise the detector)
    "ああああああ、すごい！！！！！",  # repeated character + symbol run
    "価格は１２３４５６７８９０１２３４円です",  # abnormal-length digit run
    "abc漢字123混在token",        # mixed script inside one piece
    "エラーコード",           # control character
]


def test_contamination_reasons_cover_each_damage_kind():
    assert "halfwidth_kana" in contamination_reasons("ｼﾀ", [])
    assert "repeated_char" in contamination_reasons("ああああああ", [])
    assert "symbol_run" in contamination_reasons("！！！！！", [])
    assert "abnormal_length" in contamination_reasons("１２３４５６７８９０１２３４", [])
    assert "control_char" in contamination_reasons("エラーコード", [])
    assert "mixed_script" in contamination_reasons("abc漢字123混在", [])
    assert contamination_reasons("東京", []) == [] and contamination_reasons("走った", []) == []


def test_dirty_corpus_yields_candidates_and_clean_corpus_does_not():
    clean_vocab = build_vocab(CLEAN, analyzer=_FINE)
    rep_clean = vocab_report(clean_vocab, CLEAN, analyzer=_FINE)
    assert rep_clean["contamination"]["count"] == 0

    dirty_vocab = build_vocab(CLEAN + DIRTY, analyzer=_FINE)
    rep = vocab_report(dirty_vocab, CLEAN + DIRTY, analyzer=_FINE)
    reasons = {r for c in rep["contamination"]["candidates"] for r in c["reasons"]}
    assert rep["contamination"]["count"] >= 1  # the fine tokenizer splits most damage into characters; what survives as a piece is flagged
    assert reasons & {"repeated_char", "symbol_run", "abnormal_length", "control_char", "mixed_script", "halfwidth_kana"}
    # contamination rate is reported against the whole vocabulary and stays small for a mostly clean corpus
    assert 0 < rep["contamination"]["rate"] < 0.2
    # clean pieces are not flagged
    flagged = {c["piece"] for c in rep["contamination"]["candidates"]}
    assert "東京" not in flagged and "美味しい" not in flagged
