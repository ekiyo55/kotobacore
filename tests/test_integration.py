"""End-to-end integration tests for Analyzer.

Validates the full pipeline against the固定評価文 in 07_テスト §21 / 09_評価 §4.2.
"""

import json

import kotobacore
from kotobacore import Analyzer


def test_full_pipeline_openai_api_complaint():
    a = Analyzer()
    r = a.analyze("OpenAI APIの課金高すぎてしぬw")

    # tokens populated
    assert len(r.tokens) > 0
    # semantic_tokens populated
    assert len(r.semantic_tokens) > 0
    # chunks include service + complaint + slang_emotion
    chunk_texts = {c.text: c.type for c in r.chunks}
    assert "OpenAI API" in chunk_texts
    assert chunk_texts["OpenAI API"] == "service"
    assert "課金高すぎ" in chunk_texts
    assert chunk_texts["課金高すぎ"] == "complaint"
    assert "しぬw" in chunk_texts
    assert chunk_texts["しぬw"] == "slang_emotion"

    # emotion detected, polarity negative-leaning
    assert r.emotion is not None
    assert r.emotion.primary in {"anger", "exaggeration"}

    # intent: pricing_complaint
    assert r.intent.label == "pricing_complaint"
    assert r.intent.confidence > 0

    # RAG: OpenAI API should be first keyword
    assert r.rag.keywords[0] == "OpenAI API"
    assert any("課金" in k for k in r.rag.keywords)


def test_full_pipeline_anime_admiration():
    a = Analyzer()
    r = a.analyze("このアニメ尊すぎて泣いた")

    # Should detect admiration emotion
    emotions = {e.emotion for e in r.emotion.expressions}
    assert "admiration" in emotions or r.emotion.primary == "admiration"


def test_full_pipeline_support_request():
    a = Analyzer()
    r = a.analyze("もう無理。請求まわりを確認して")

    assert r.intent.label == "support_request"
    # 請求 should be in RAG keywords
    assert any("請求" in k for k in r.rag.keywords)


def test_full_pipeline_wakuwaku_anticipation():
    a = Analyzer()
    r = a.analyze("今日は新しいプロジェクトがスタート！ワクワクする！")

    # joy or anticipation should appear
    plu_keys = set(r.emotion.plutchik.keys())
    assert plu_keys & {"joy", "anticipation"}


def test_full_pipeline_returns_valid_json():
    a = Analyzer()
    r = a.analyze("OpenAI APIの課金高すぎてしぬw")

    payload = r.to_json()
    parsed = json.loads(payload)

    # Top-level keys per 06_API §6.1
    for key in {"meta", "text", "tokens", "semantic_tokens", "chunks",
                "emotion", "intent", "rag", "errors"}:
        assert key in parsed


def test_disable_emotion():
    a = Analyzer(enable_emotion=False)
    r = a.analyze("最高")
    assert r.emotion.primary is None
    assert r.emotion.expressions == []


def test_disable_intent():
    a = Analyzer(enable_intent=False)
    r = a.analyze("それな")
    assert r.intent.label is None


def test_disable_rag():
    a = Analyzer(enable_rag=False)
    r = a.analyze("OpenAI APIの課金高すぎ")
    assert r.rag.keywords == []
    assert r.rag.search_query == ""


def test_disable_semantic_chunk():
    a = Analyzer(enable_semantic_chunk=False)
    r = a.analyze("OpenAI APIの課金高すぎ")
    assert r.chunks == []
    assert r.semantic_tokens == []
    # But tokens still produced (used by emotion/intent/rag)
    assert len(r.tokens) > 0


def test_unknown_word_does_not_crash():
    a = Analyzer()
    r = a.analyze("ペポロロンが好き")
    assert r is not None


def test_empty_text_returns_valid_result():
    a = Analyzer()
    r = a.analyze("")
    assert r.text.original == ""
    assert r.tokens == []
    assert r.chunks == []


def test_batch_analyze():
    a = Analyzer()
    results = a.analyze_batch(["最高", "うざっ", "それな"])
    assert len(results) == 3
    assert all(r.text.original for r in results)


# 07 §21 固定評価文セット — sanity check each one analyzes without error
FIXED_CORPUS = [
    "OpenAI APIの課金高すぎてしぬw",
    "このアニメ尊すぎて泣いた",
    "もう無理。請求まわりを確認して",
    "今日は新しいプロジェクトがスタート！ワクワクする！",
    "チームメンバーとの初ミーティング。みんな頼もしい！",
    "また仕様変更？さっき決めたばかりなのに...",
    "社内FAQをRAG化したい",
    "ChatGPTの回答精度を改善したい",
    "東京都に行った",
]


def test_fixed_corpus_analyzes_without_error():
    a = Analyzer()
    for sentence in FIXED_CORPUS:
        r = a.analyze(sentence)
        # Each must produce a valid JSON
        json.loads(r.to_json())
        # Each must have meta
        assert r.meta.version == kotobacore.__version__
        assert r.meta.schema_version == "0.1"
