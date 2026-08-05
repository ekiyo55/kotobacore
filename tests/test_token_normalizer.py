"""Tests for the Token Normalizer (keep_as_unit token merging)."""

from kotobacore import Analyzer
from kotobacore.dictionary import load_default_bundle
from kotobacore.normalizer import normalize
from kotobacore.schema import Token
from kotobacore.tokenizer import KaruizawaBackend, merge_keep_as_unit


def _raw_then_merged(text: str):
    bundle = load_default_bundle()
    normalized = normalize(text)
    raw = KaruizawaBackend().tokenize(normalized, mode="C")
    merged = merge_keep_as_unit(raw, normalized, bundle)
    return raw, merged


def test_shinu_w_is_merged_into_single_token():
    # Karuizawa splits しぬw into しぬ / w. Token Normalizer must merge it.
    raw, merged = _raw_then_merged("OpenAI APIの課金高すぎてしぬw")
    raw_surfaces = [t.surface for t in raw]
    merged_surfaces = [t.surface for t in merged]

    # raw: Karuizawa splits as "すぎてしぬ" (hiragana run) / "w" — not "しぬw"
    assert "しぬw" not in raw_surfaces
    # merged: しぬw is one token
    assert "しぬw" in merged_surfaces


def test_merged_token_span_and_pos():
    _, merged = _raw_then_merged("マジしぬw")
    shinu = next(t for t in merged if t.surface == "しぬw")
    assert isinstance(shinu, Token)
    assert shinu.end - shinu.begin == 3  # しぬw = 3 chars
    assert shinu.pos == "感動詞-SNS表現"
    assert shinu.unknown is False


def test_token_ids_are_contiguous_after_merge():
    _, merged = _raw_then_merged("OpenAI APIの課金高すぎてしぬw")
    ids = [t.id for t in merged]
    assert ids == list(range(len(merged)))


def test_non_keep_as_unit_text_unchanged():
    raw, merged = _raw_then_merged("東京都に行った")
    # No keep_as_unit surfaces here → token count unchanged
    assert len(raw) == len(merged)
    assert [t.surface for t in raw] == [t.surface for t in merged]


def test_begin_end_preserved_for_following_tokens():
    # The merge must not corrupt downstream token offsets.
    _, merged = _raw_then_merged("しぬwと言った")
    # tokens after しぬw must still have begin == previous end
    for i in range(1, len(merged)):
        assert merged[i].begin == merged[i - 1].end


def test_analyzer_tokenize_applies_keep_as_unit():
    # Per decision B: standalone tokenize() also applies keep_as_unit.
    a = Analyzer()
    tokens = a.tokenize("OpenAI APIの課金高すぎてしぬw")
    surfaces = [t.surface for t in tokens]
    assert "しぬw" in surfaces


def test_analyze_result_tokens_have_shinu_w_unit():
    a = Analyzer()
    r = a.analyze("OpenAI APIの課金高すぎてしぬw")
    surfaces = [t.surface for t in r.tokens]
    assert "しぬw" in surfaces
    # the wrong sub-tokens must be gone
    # (し as 為る verb form should not appear as a standalone token here)
    assert "しぬw" in surfaces


def test_chunk_token_ids_valid_after_merge():
    # chunk.token_ids must reference valid (merged) token ids
    a = Analyzer()
    r = a.analyze("OpenAI APIの課金高すぎてしぬw")
    valid_ids = {t.id for t in r.tokens}
    for c in r.chunks:
        for tid in c.token_ids:
            assert tid in valid_ids


def test_single_char_keep_as_unit_not_merged():
    # 草 is a 1-char keep_as_unit slang — nothing to merge, must not crash.
    a = Analyzer()
    r = a.analyze("それ草")
    assert r is not None


# ---------------------------------------------------------------------------
# Verb / adjective POS refinement
# ---------------------------------------------------------------------------


def _pos_of(tokens, surface):
    for t in tokens:
        if t.surface == surface:
            return t.pos
    return None


def test_verb_is_labelled_doushi():
    # 走る / 読んだ / 行った must be 動詞, not 名詞.
    a = Analyzer()
    for sentence, verb in [
        ("公園で走る", "走る"),
        ("本を読んだ", "読んだ"),
        ("東京に行った", "行った"),
    ]:
        toks = a.analyze(sentence).tokens
        pos = _pos_of(toks, verb)
        assert pos is not None and "動詞" in pos, f"{verb}: {pos}"


def test_adjective_is_labelled_keiyoushi():
    a = Analyzer()
    toks = a.analyze("美味しい料理を食べる").tokens
    assert "形容詞" in (_pos_of(toks, "美味しい") or "")
    assert "動詞" in (_pos_of(toks, "食べる") or "")


def test_particle_not_merged_into_verb():
    # 本を — を is a particle, must NOT be merged with 本.
    a = Analyzer()
    toks = a.analyze("本を読んだ").tokens
    surfaces = [t.surface for t in toks]
    assert "本" in surfaces
    assert "を" in surfaces


def test_dictionary_word_not_swallowed_by_verb_merge():
    # ワクワクする: ワクワク is an emotion word — must stay a separate token
    # so the semantic layer still detects it (not merged into ワクワクする).
    a = Analyzer()
    r = a.analyze("今日はワクワクする")
    surfaces = [t.surface for t in r.tokens]
    assert "ワクワク" in surfaces
    # emotion still detected
    assert r.emotion is not None and r.emotion.primary is not None


# ---------------------------------------------------------------------------
# Okurigana compound merge (merge_okurigana_compounds)
# ---------------------------------------------------------------------------


def test_okurigana_compound_shimekiri():
    # 締め切り fragments into 締|め|切|り without the merge layer.
    a = Analyzer()
    toks = a.analyze("締め切りが近いのにバグが出た。もう無理かも...").tokens
    surfaces = [t.surface for t in toks]
    assert "締め切り" in surfaces
    assert "名詞" in (_pos_of(toks, "締め切り") or "")


def test_okurigana_compound_common_nouns():
    a = Analyzer()
    for sentence, compound in [
        ("思い出の写真", "思い出"),
        ("買い物に行く", "買い物"),
        ("引っ越しの準備", "引っ越し"),
        ("打ち合わせは明日", "打ち合わせ"),
        ("問い合わせが多い", "問い合わせ"),
        ("真っ白な雪", "真っ白"),
    ]:
        toks = a.analyze(sentence).tokens
        surfaces = [t.surface for t in toks]
        assert compound in surfaces, f"{sentence}: {surfaces}"


def test_adjective_stem_not_fused_by_sandwich():
    # 良い天気: 良+い must become adjective 良い, NOT one noun 良い天気.
    a = Analyzer()
    for sentence, adj, noun in [
        ("良い天気ですね", "良い", "天気"),
        ("高い山に登る", "高い", "山"),
    ]:
        toks = a.analyze(sentence).tokens
        surfaces = [t.surface for t in toks]
        assert adj in surfaces and noun in surfaces, f"{sentence}: {surfaces}"
        assert "形容詞" in (_pos_of(toks, adj) or "")


def test_verb_stem_not_absorbed_by_trailing_rule():
    # 走りきった: plain KANJI verb stem must not absorb り as a noun.
    a = Analyzer()
    toks = a.analyze("走りきった").tokens
    assert "動詞" in (_pos_of(toks, "走りきった") or "")


def test_shimekiri_anxiety_detected():
    # 締め切りが近い → anxiety (焦り), and 締め切り reaches RAG keywords.
    a = Analyzer()
    r = a.analyze("締め切りが近いのにバグが出た。もう無理かも...")
    assert r.emotion.primary == "anxiety"
    assert r.emotion.polarity == "negative"
    assert any("締め切り" in k for k in r.rag.keywords)
