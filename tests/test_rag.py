"""Tests for RAG optimizer per 07_テスト仕様 §14."""

from kotobacore.dictionary import load_default_bundle
from kotobacore.emotion import detect_emotion
from kotobacore.intent import classify_intent
from kotobacore.normalizer import normalize
from kotobacore.rag import optimize_rag
from kotobacore.semantic import build_semantic_tokens, chunk
from kotobacore.tokenizer import KaruizawaBackend


def _pipeline_rag(text: str):
    bundle = load_default_bundle()
    normalized = normalize(text)
    tokens = KaruizawaBackend().tokenize(normalized, mode="C")
    sem_tokens = build_semantic_tokens(tokens, bundle)
    chunks = chunk(normalized, tokens, bundle)
    emo = detect_emotion(normalized, bundle)
    intent = classify_intent(normalized, bundle)
    return optimize_rag(
        normalized_text=normalized,
        tokens=tokens,
        semantic_tokens=sem_tokens,
        chunks=chunks,
        emotion=emo,
        intent=intent,
        bundle=bundle,
    )


# ---------------------------------------------------------------------------
# RAG-001..004 (07 §14.2)
# ---------------------------------------------------------------------------


def test_rag_001_openai_api_kakin_keywords():
    # RAG-001: "OpenAI APIの課金高すぎ" → OpenAI API / 課金 / 料金 / 高い
    r = _pipeline_rag("OpenAI APIの課金高すぎ")
    assert "OpenAI API" in r.keywords
    # 課金 should appear directly or via 課金高すぎ chunk
    assert any("課金" in kw for kw in r.keywords)


def test_rag_003_social_faq_keywords():
    # RAG-003: "社内FAQをRAG化したい"
    r = _pipeline_rag("社内FAQをRAG化したい")
    keys = set(r.keywords)
    assert "社内FAQ" in keys or any("FAQ" in k for k in keys)
    assert "RAG" in keys


def test_rag_004_billing_check():
    # RAG-004: "請求まわりを確認して" → 請求
    r = _pipeline_rag("請求まわりを確認して")
    assert any("請求" in k for k in r.keywords)


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


def test_rag_keywords_not_empty_for_content():
    r = _pipeline_rag("ChatGPTの回答精度を改善したい")
    assert len(r.keywords) > 0


def test_rag_stopwords_excluded():
    r = _pipeline_rag("OpenAI APIの課金高すぎ")
    # の / は / が / を should NOT appear as keywords
    for sw in ("の", "は", "が", "を"):
        assert sw not in r.keywords


def test_rag_search_query_is_keywords_joined():
    r = _pipeline_rag("OpenAI APIの課金高すぎ")
    assert r.search_query == " ".join(r.keywords)


def test_rag_proper_nouns_prioritized_first():
    r = _pipeline_rag("OpenAI APIの課金高すぎ")
    assert r.keywords[0] == "OpenAI API"  # Entity should be top


def test_rag_summary_hint_set_when_emotion_present():
    r = _pipeline_rag("OpenAI APIの課金高すぎ")
    assert r.summary_hint is not None
    assert len(r.summary_hint) > 0


def test_rag_empty_text_returns_empty():
    bundle = load_default_bundle()
    r = optimize_rag(
        normalized_text="",
        tokens=[],
        semantic_tokens=[],
        chunks=[],
        emotion=None,
        intent=None,
        bundle=bundle,
    )
    assert r.keywords == []
    assert r.search_query == ""


def test_rag_semantic_phrases_contain_chunks():
    r = _pipeline_rag("OpenAI APIの課金高すぎ")
    assert "OpenAI API" in r.semantic_phrases
