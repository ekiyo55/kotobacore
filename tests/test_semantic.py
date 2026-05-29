"""Tests for SemanticToken builder + SemanticChunker per 07_テスト仕様 §8, §9."""

from kotobacore import Analyzer
from kotobacore.schema import SemanticChunk, SemanticToken


def _pipeline(text: str):
    """Helper: run the full production pipeline and return
    (tokens, semantic_tokens, chunks).

    Uses Analyzer.analyze() so the Token Normalizer (keep_as_unit merge /
    ひらがな分割 / 固有名詞マージ / 動詞品詞補正) is applied — the chunker's
    token-boundary alignment requires properly normalized tokens.
    """
    r = Analyzer().analyze(text)
    return r.tokens, r.semantic_tokens, r.chunks


# ---------------------------------------------------------------------------
# SemanticToken Builder
# ---------------------------------------------------------------------------


def test_semtok_001_openai_api_is_service_or_entity():
    # SEMTOK-001: OpenAI API → service chunk
    # NOTE: Karuizawa splits "OpenAI API" into ["OpenAI", "API"] (space dropped).
    # Per-token semantic_token won't catch multi-word entries; the Chunker layer
    # handles span matching. Test at chunk level.
    _, _, chunks = _pipeline("OpenAI APIを使う")
    openai_chunks = [c for c in chunks if c.text == "OpenAI API"]
    assert len(openai_chunks) == 1
    assert openai_chunks[0].type == "service"


def test_semtok_002_chatgpt_is_product():
    _, sem_tokens, _ = _pipeline("ChatGPTが好きだ")
    has_product = any(
        st.entity_type == "PRODUCT" or st.semantic_type == "product"
        for st in sem_tokens
    )
    assert has_product


def test_semtok_005_shinu_w_is_slang_chunk():
    # SEMTOK-005: しぬw is split by Karuizawa (しぬ / w), so the
    # per-token semantic_token layer misses it. The Chunker layer recovers
    # the surface via the slang dictionary (keep_as_unit=true).
    _, _, chunks = _pipeline("しぬw")
    shinu_chunks = [c for c in chunks if c.text == "しぬw"]
    assert len(shinu_chunks) == 1
    assert shinu_chunks[0].type == "slang_emotion"


def test_semantic_token_confidence_in_range():
    _, sem_tokens, _ = _pipeline("OpenAI APIの課金高すぎてしぬw")
    for st in sem_tokens:
        assert isinstance(st, SemanticToken)
        assert 0.0 <= st.confidence <= 1.0


def test_emotion_token_has_plutchik():
    _, sem_tokens, _ = _pipeline("最高")
    emo_tokens = [st for st in sem_tokens if st.emotion]
    assert len(emo_tokens) >= 1
    for st in emo_tokens:
        assert st.plutchik_emotion in {
            "joy", "trust", "fear", "surprise", "sadness",
            "disgust", "anger", "anticipation", "mixed",
        }


# ---------------------------------------------------------------------------
# SemanticChunker
# ---------------------------------------------------------------------------


def test_chunk_001_openai_api_complaint_shinu():
    # CHUNK-001: OpenAI APIの課金高すぎてしぬw
    #            → OpenAI API / 課金高すぎ / しぬw
    _, _, chunks = _pipeline("OpenAI APIの課金高すぎてしぬw")
    texts = [c.text for c in chunks]
    assert "OpenAI API" in texts
    assert "課金高すぎ" in texts
    assert "しぬw" in texts


def test_chunks_are_dataclass_instances():
    _, _, chunks = _pipeline("最高")
    for c in chunks:
        assert isinstance(c, SemanticChunk)
        assert isinstance(c.token_ids, list)
        assert 0.0 <= c.score <= 1.0


def test_chunk_score_set():
    _, _, chunks = _pipeline("OpenAI APIの課金高すぎてしぬw")
    assert all(c.score > 0 for c in chunks)


def test_no_overlapping_chunks():
    # Each token_id appears in at most one chunk
    _, _, chunks = _pipeline("OpenAI APIの課金高すぎてしぬw")
    seen: set[int] = set()
    for c in chunks:
        for tid in c.token_ids:
            assert tid not in seen, f"token {tid} appears in multiple chunks"
            seen.add(tid)


def test_empty_text_no_chunks():
    _, _, chunks = _pipeline("")
    assert chunks == []


def test_keep_as_unit_shinu_w_not_split():
    # KEEP_AS_UNIT: しぬw must appear as a single chunk
    _, _, chunks = _pipeline("マジしぬw")
    shinu_chunks = [c for c in chunks if c.text == "しぬw"]
    assert len(shinu_chunks) == 1
    assert shinu_chunks[0].type == "slang_emotion"


def test_complaint_chunk_type_for_negative_emotion():
    _, _, chunks = _pipeline("課金高すぎ")
    complaint_chunks = [c for c in chunks if c.text == "課金高すぎ"]
    assert len(complaint_chunks) == 1
    assert complaint_chunks[0].type == "complaint"


def test_long_single_noun_becomes_topic_chunk():
    # Karuizawa keeps チームメンバー as one kanji token; long single nouns
    # become "topic" chunks rather than "compound_noun".
    _, _, chunks = _pipeline("チームメンバー")
    assert len(chunks) >= 1
    types = {c.type for c in chunks}
    assert "topic" in types or "compound_noun" in types


def test_compound_noun_for_split_nouns():
    # 課金システム — two separate nouns in mode C
    _, _, chunks = _pipeline("課金システム")
    types = {c.type for c in chunks}
    assert "compound_noun" in types or "topic" in types
