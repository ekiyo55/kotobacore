"""Tests for intent classifier per 07_テスト仕様 §13."""

from kotobacore.dictionary import load_default_bundle
from kotobacore.intent import classify_intent
from kotobacore.normalizer import normalize
from kotobacore.schema import IntentCandidate, IntentResult


def _classify(text: str) -> IntentResult:
    return classify_intent(normalize(text), load_default_bundle())


# ---------------------------------------------------------------------------
# INT-001..005 (07 §13.2)
# ---------------------------------------------------------------------------


def test_int_001_pricing_complaint():
    r = _classify("OpenAI APIの課金高すぎ")
    assert r.label == "pricing_complaint"
    assert r.confidence > 0


def test_int_002_support_request():
    r = _classify("請求まわりを確認して")
    assert r.label == "support_request"


def test_int_003_positive_feedback():
    r = _classify("このアニメ最高")
    assert r.label in {"positive_feedback", "admiration"}


def test_int_004_negative_feedback():
    r = _classify("仕様変更が多くてつらい")
    assert r.label == "negative_feedback"


def test_int_005_agreement():
    r = _classify("それな")
    assert r.label == "agreement"


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


def test_intent_returns_candidates_list():
    r = _classify("OpenAI APIの課金高すぎ")
    assert isinstance(r.candidates, list)
    assert len(r.candidates) >= 1
    for c in r.candidates:
        assert isinstance(c, IntentCandidate)
        assert 0.0 <= c.confidence <= 1.0


def test_intent_confidence_in_range():
    r = _classify("OpenAI APIの課金高すぎ")
    assert 0.0 <= r.confidence <= 1.0


def test_unknown_intent_for_neutral_text():
    r = _classify("今日は晴れています")
    assert r.label == "unknown"
    assert r.confidence == 0.0


def test_empty_text_unknown():
    r = classify_intent("", load_default_bundle())
    assert r.label is None or r.label == "unknown"
    assert r.confidence == 0.0


def test_candidates_sorted_by_confidence_desc():
    r = _classify("OpenAI APIの課金高すぎてつらい")
    confidences = [c.confidence for c in r.candidates]
    assert confidences == sorted(confidences, reverse=True)


def test_helped_me_is_positive_feedback_not_support_request():
    # Regression: 助けてくれた is gratitude, not a help-request.
    r = _classify("先輩が助けてくれた！なんとか解決できそう！")
    assert r.label == "positive_feedback"


def test_help_me_alone_still_support_request():
    # Make sure we didn't break the canonical case: 「助けてください」 should still
    # fire support_request.
    r = _classify("助けてください！")
    assert r.label == "support_request"


def test_laugh_expression_is_positive_feedback():
    # SNS laugh variants should classify as positive_feedback.
    for variant in ["ワラッタ", "わらった", "ワロタ", "わろた"]:
        r = _classify(f"スクランブル交差点お祭り騒ぎで{variant}！")
        assert r.label == "positive_feedback", f"{variant} → {r.label}"


def test_daisuki_is_positive_feedback():
    r = _classify("明日は東京の渋谷でデートだ、かまち大好き")
    assert r.label == "positive_feedback"
    assert r.confidence > 0


def test_tabako_does_not_falsely_trigger_positive():
    # bare 「草」 is intentionally excluded from the pattern so that words
    # containing 草 (煙草 = cigarette etc.) do not false-fire positive_feedback.
    r = _classify("煙草を買ってきた")
    assert r.label != "positive_feedback"


# ---------------------------------------------------------------------------
# v0.1.15: 中立トピック語の除去 + 文末形式 + 感情連動
# ---------------------------------------------------------------------------


def test_neutral_topic_words_do_not_trigger_feedback():
    # 仕様変更/バグ/高い は不満とは限らない — 中立文は unknown
    from kotobacore import Analyzer
    a = Analyzer()
    for s in ["バグを修正しました", "仕様変更を反映しました。", "高い山に登る"]:
        r = a.analyze(s)
        assert r.intent.label == "unknown", f"{s}: {r.intent.label}"


def test_sentence_final_question_mark():
    from kotobacore import Analyzer
    r = Analyzer().analyze("また仕様変更？")
    assert r.intent.label == "question"


def test_emotion_derived_feedback():
    # ルール未マッチでも感情層の帰属済み極性から feedback を導出
    from kotobacore import Analyzer
    r = Analyzer().analyze("楽しかった一日")
    assert r.intent.label == "positive_feedback"


def test_rule_hits_beat_emotion_fallback():
    # 明示的な support_request が感情由来 negative_feedback に勝つ
    from kotobacore import Analyzer
    r = Analyzer().analyze("もう無理。請求まわりを確認して")
    assert r.intent.label == "support_request"
