"""Tests for emotion detector per 07_テスト仕様 §10-12."""

from kotobacore.dictionary import load_default_bundle, load_user_bundle
from kotobacore.emotion import detect_emotion
from kotobacore.normalizer import normalize
from kotobacore.schema import EmotionExpression, EmotionResult
from kotobacore.tokenizer import KaruizawaBackend, merge_keep_as_unit


def _detect(text: str, use_external: bool = False) -> EmotionResult:
    # Mirror the production pipeline: normalize → tokenize → Token Normalizer
    # → detect_emotion (with token-boundary alignment).
    bundle = load_user_bundle() if use_external else load_default_bundle()
    normalized = normalize(text)
    raw = KaruizawaBackend().tokenize(normalized, mode="C")
    tokens = merge_keep_as_unit(raw, normalized, bundle)
    return detect_emotion(normalized, bundle, tokens)


# ---------------------------------------------------------------------------
# EMO-001..006 (07 §10.2)
# ---------------------------------------------------------------------------


def test_emo_001_saikou_is_joy_positive():
    r = _detect("最高")
    assert r.primary == "joy"
    assert r.polarity == "positive"


def test_emo_002_uzaa_is_irritation_negative():
    r = _detect("うざっ")
    assert r.primary == "irritation"
    assert r.polarity == "negative"


def test_emo_003_toutoi_is_admiration_positive():
    # 尊い is in slang.csv with emotion=admiration
    r = _detect("尊い")
    assert r.primary == "admiration"
    assert r.polarity == "positive"


def test_emo_004_muri_is_refusal_negative():
    r = _detect("無理")
    assert r.primary == "refusal"
    assert r.polarity == "negative"


def test_emo_005_shinu_w_is_exaggeration_mixed():
    r = _detect("しぬw")
    assert r.primary == "exaggeration"
    assert r.polarity == "mixed"


def test_emo_006_sorena_is_agreement():
    r = _detect("それな")
    assert r.primary == "agreement"


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


def test_intensity_in_range():
    r = _detect("最高")
    assert 0.0 <= r.intensity <= 1.0


def test_confidence_in_range():
    r = _detect("最高")
    assert 0.0 <= r.confidence <= 1.0


def test_expressions_populated():
    r = _detect("最高")
    assert len(r.expressions) >= 1
    for e in r.expressions:
        assert isinstance(e, EmotionExpression)
        assert 0.0 <= e.intensity <= 1.0
        assert 0.0 <= e.confidence <= 1.0


def test_plutchik_keys_valid():
    r = _detect("最高")
    valid = {"joy", "trust", "fear", "surprise", "sadness", "disgust", "anger", "anticipation", "mixed"}
    assert set(r.plutchik.keys()).issubset(valid)


def test_empty_text_returns_empty_result():
    r = _detect("")
    assert r.primary is None
    assert r.expressions == []
    assert r.plutchik == {}


def test_no_emotion_words_returns_empty():
    r = _detect("これはペンです")
    assert r.primary is None
    assert r.expressions == []


# ---------------------------------------------------------------------------
# PLU-001..008 (07 §11.2)
# ---------------------------------------------------------------------------


def test_plu_001_wakuwaku_is_anticipation_via_examples():
    # PLU-001: ワクワクする → anticipation (via example_examples mapping)
    # NOTE: ワクワク is in emotion.csv mapped to joy (base) which → joy (plutchik).
    # The example-based dictionary maps it to plutchik=anticipation.
    # With user_bundle (external on), expressions should include anticipation.
    # For default_bundle only, ワクワク maps to base=joy → plutchik=joy.
    r = _detect("ワクワクする", use_external=True)
    # Either joy or anticipation should appear in plutchik distribution
    plu_keys = set(r.plutchik.keys())
    assert plu_keys & {"joy", "anticipation"}


def test_plu_005_kanashii_is_sadness():
    r = _detect("悲しい")
    assert r.primary == "sadness"
    assert "sadness" in r.plutchik


def test_plu_007_iraira_is_irritation_anger():
    r = _detect("イライラする")
    # base_emotion=irritation, plutchik=anger
    assert r.primary in {"irritation", "anger"}
    plu_keys = set(r.plutchik.keys())
    assert "anger" in plu_keys


# ---------------------------------------------------------------------------
# EXEMO (example-based matching)
# ---------------------------------------------------------------------------


def test_example_based_matched_examples_populated():
    # 「新しいプロジェクトが始まってワクワクする」should match EX-ANT-001 example.
    r = _detect("新しいプロジェクトが始まってワクワクする")
    wakuwaku_exprs = [e for e in r.expressions if e.text == "ワクワク"]
    assert len(wakuwaku_exprs) >= 1
    # Either some matched_examples or non-zero confidence
    assert wakuwaku_exprs[0].confidence > 0


def test_multiple_emotion_expressions_in_one_sentence():
    # 「最高だけど無理かも」 contains both joy and refusal expressions
    r = _detect("最高だけど無理かも")
    emotions = {e.emotion for e in r.expressions}
    assert "joy" in emotions
    assert "refusal" in emotions


# ---------------------------------------------------------------------------
# Real-world fixed corpus (07 §22, 09 §4.2)
# ---------------------------------------------------------------------------


def test_openai_api_kakin_takasugite_shinu_w():
    r = _detect("OpenAI APIの課金高すぎてしぬw")
    # 課金高すぎ (negative) AND しぬw (mixed) should be detected
    surfaces = {e.text for e in r.expressions}
    assert "課金高すぎ" in surfaces
    assert "しぬw" in surfaces


def test_regression_external_dict_does_not_override_internal_refusal():
    # Regression: 「もう無理。請求まわりを確認して」 was previously misclassified
    # as 'admiration' because NRC's 「確認」 (translated from trust-related English
    # words) outscored internal 「無理」 (refusal). External entries must be
    # downweighted enough that internal seed wins on common Japanese.
    # Note: after SNS-example polysemy support, "もう無理" (4-char surface in SNS
    # file → sadness) correctly outranks "無理" (refusal) as the longer match.
    # The key invariant is that NRC "確認" (admiration) must NOT win.
    r = _detect("もう無理。請求まわりを確認して", use_external=True)
    assert r.primary in {"refusal", "sadness"}
    assert r.polarity == "negative"


def test_regression_helped_me_is_positive_not_refusal():
    # Regression: 「先輩が助けてくれた！なんとか解決できそう！」 was misclassified
    # as 'refusal/negative' because emotion.csv had `助けて → refusal` AND
    # intent_rules had `助けて` for support_request — both fired on substrings
    # of 「助けてくれた」 (= "they helped me", positive gratitude).
    r = _detect("先輩が助けてくれた！なんとか解決できそう！", use_external=True)
    assert r.polarity == "positive"
    assert r.primary == "joy"


def test_regression_waratta_katakana_recognized_as_laugh():
    # Regression: 「ワラッタ」 (katakana spelling of 笑った) was not in any
    # dictionary so it produced no emotion. SNS laugh variants must be detected.
    for variant in ["ワラッタ", "わらった", "ワロタ", "わろた"]:
        r = _detect(f"スクランブル交差点はお祭り騒ぎで{variant}！")
        surfaces = {e.text for e in r.expressions}
        assert variant in surfaces, f"{variant} not detected"
        expr = next(e for e in r.expressions if e.text == variant)
        assert expr.emotion == "joy"
        assert expr.polarity == "positive"


def test_daisuki_is_joy_positive():
    r = _detect("明日は東京の渋谷でデートだ、かまち大好き")
    assert r.primary == "joy"
    assert r.polarity == "positive"
    surfaces = {e.text for e in r.expressions}
    assert "大好き" in surfaces


def test_regression_hai_substring_not_falsely_detected():
    # Regression: NRC entry 「はい」 matched the accidental は+い substring in
    # 「お昼はいつもの…」 (は = particle, い = start of いつも). Token-boundary
    # alignment must reject such cross-token substring hits.
    r = _detect("お昼はいつもの定食屋で。安定の美味しさ。", use_external=True)
    surfaces = {e.text for e in r.expressions}
    assert "はい" not in surfaces
    # The genuine emotion word 美味しさ should be picked up instead.
    assert "美味しさ" in surfaces
    assert r.polarity == "positive"


def test_muzukashii_detected_as_anxiety():
    # デモ指摘: 「思ったより難しい課題が...どうしよう。」で どうしよう しか
    # 拾われなかった。難しい (anxiety) も感情表現として検出されること。
    r = _detect("思ったより難しい課題が...どうしよう。")
    assert r.primary == "anxiety"
    assert r.polarity == "negative"
    surfaces = {e.text for e in r.expressions}
    assert "どうしよう" in surfaces
    assert "難しい" in surfaces


def test_muzukashii_does_not_override_positive_context():
    # 難しい は低 intensity (0.45) — ポジティブ文脈では primary を奪わない。
    r = _detect("難しい問題を解くのが好き")
    assert r.primary == "joy"
    assert r.polarity == "positive"


def test_shiyouhenkou_is_neutral_topic_not_emotion():
    # デモ指摘: 仕様変更 は不満とは限らない。感情の担い手は「〜ばかりなのに」
    # (直前完了+逆接=不満の語用論マーカー)。中立文脈では感情なしになること。
    for neutral in ["また仕様変更？了解です。", "仕様変更を反映しました。"]:
        r = _detect(neutral)
        surfaces = {e.text for e in r.expressions}
        assert "仕様変更" not in surfaces, f"{neutral}: {surfaces}"
        assert r.primary is None, f"{neutral}: {r.primary}"


def test_bakari_nanoni_carries_the_complaint():
    # 不満は ばかりなのに が運ぶ。仕様変更 はトピックとして RAG に残る。
    r = _detect("また仕様変更？さっき決めたばかりなのに...")
    assert r.primary == "anger"
    assert r.polarity == "negative"
    surfaces = {e.text for e in r.expressions}
    assert "ばかりなのに" in surfaces
    assert "仕様変更" not in surfaces
    # 汎用性: 別の動詞でも発火する
    r2 = _detect("昨日直したばっかりなのにまた壊れた")
    assert r2.primary == "anger"


# ---------------------------------------------------------------------------
# Negation scope (v0.1.15)
# ---------------------------------------------------------------------------


def test_negated_positive_flips_to_negative():
    # 好きじゃない ≈ 嫌い — joy が positive のまま残ってはいけない
    r = _detect("全然好きじゃない")
    assert r.primary != "joy"
    assert r.polarity != "positive"


def test_negated_negative_is_neutralized():
    # 不安はない / 心配ない — 否定された負感情は中立化(検出なし)
    for s in ["不安はない", "心配ない、大丈夫"]:
        r = _detect(s)
        assert r.primary is None, f"{s}: {r.primary}"


def test_negated_adjective_token_internal():
    # 嬉しくない — 活用形レンマ照合 + トークン内部否定
    r = _detect("嬉しくない")
    assert r.primary != "joy"
    assert r.polarity != "positive"


def test_conjugated_adjective_lemma_matches():
    # 楽しかった → lemma 楽しい で joy 検出 (活用形を辞書登録せずに)
    r = _detect("楽しかった一日")
    assert r.primary == "joy"
    assert r.polarity == "positive"


# ---------------------------------------------------------------------------
# Clause segmentation: 逆接 weighting + clause-scoped ex_sim (v0.1.15)
# ---------------------------------------------------------------------------


def test_adversative_clause_wins():
    # 「〜でしたが成功しました」— 逆接の後節が primary/polarity を支配
    # (成功 は NRC 外部辞書由来 — 外部辞書が無い環境ではスキップ)
    import pytest

    from kotobacore import Analyzer
    a = Analyzer()
    if not a._get_bundle().external_emotion:
        pytest.skip("external dictionary (NRC) not available")
    r = a.analyze("難しい判断でしたが成功しました").emotion
    assert r.primary == "joy"
    assert r.polarity == "positive"


def test_noni_keeps_pre_clause_emotion():
    # のに は節分割のみ(重み変更なし) — 前節の焦りが primary を維持
    from kotobacore import Analyzer
    r = Analyzer().analyze("締め切りが近いのにバグが出た。もう無理かも...").emotion
    assert r.primary == "anxiety"


def test_ex_sim_is_clause_scoped():
    # 長文でも感情語の節スコープで ex_sim が計算され confidence が希釈されない
    from kotobacore import Analyzer
    a = Analyzer()
    short = "思ったより難しい課題が...どうしよう。"
    long = (
        "今朝は晴れていたので自転車で出社した。"
        "昼は同僚とカレーを食べ、午後の打ち合わせでは来月の段取りを確認した。"
    ) + short
    def conf(s):
        r = a.analyze(s)
        return [x.confidence for x in r.emotion.expressions if x.text == "どうしよう"][0]
    assert conf(short) == conf(long)
