"""Sentiment module (FR-062) — separated from Emotion, shared Core scoring."""

from kotobacore import Analyzer, SentimentResult
from kotobacore.core.lexicon import EVALUATION, score_affect_expressions
from kotobacore.dictionary import load_default_bundle
from kotobacore.modules import detect_emotion, detect_sentiment


def _analyzer() -> Analyzer:
    return Analyzer(use_external_dictionaries=False)


def test_sentiment_present_in_result_and_json():
    r = _analyzer().analyze("この製品は本当に便利で助かる")
    assert isinstance(r.sentiment, SentimentResult)
    assert r.sentiment.polarity == "positive"
    assert "sentiment" in r.to_dict()
    assert r.to_dict()["sentiment"]["polarity"] == "positive"


def test_evaluative_word_without_emotion():
    r = _analyzer().analyze("コーヒーはいまいちだった")
    assert r.sentiment.polarity == "negative"
    assert any(e.text.startswith("いまいち") for e in r.sentiment.expressions)
    # evaluative-only words carry no Plutchik category and no affective polarity
    assert r.emotion.primary is None
    assert r.emotion.expressions == []
    assert r.emotion.polarity is None
    assert r.sentiment.affect_polarity is None


def test_negation_flips_evaluation():
    a = _analyzer()
    neg = a.analyze("この製品は良くない")
    assert neg.sentiment.polarity == "negative"
    assert neg.sentiment.expressions[0].negated is True
    pos = a.analyze("対応は悪くなかった")
    assert pos.sentiment.polarity == "positive"
    assert pos.sentiment.expressions[0].negated is True


def test_affect_polarity_mirrors_emotion_and_is_separate():
    a = _analyzer()
    for text in ["最高に嬉しい", "不安で仕方ない", "つまらないけど便利だった", "残念だけど仕方ない"]:
        r = a.analyze(text)
        assert r.emotion.polarity == r.sentiment.affect_polarity, text
    # emotion words alone do not make an evaluation (2026-09-08 decision)
    r = a.analyze("明日のライブ、わくわくが止まらない！")
    assert r.sentiment.polarity is None
    assert r.sentiment.expressions == []
    assert r.sentiment.affect_polarity == "positive"
    assert r.emotion.primary is not None


def test_adversative_clause_wins():
    r = _analyzer().analyze("嬉しくないけど便利")
    assert r.sentiment.polarity == "positive"
    assert r.emotion.primary == "sadness"


def test_intent_reads_sentiment():
    a = _analyzer()
    assert a.analyze("コーヒーはいまいちだった").intent.label == "negative_feedback"
    assert a.analyze("対応が丁寧で助かった").intent.label == "positive_feedback"


def test_disable_sentiment():
    a = Analyzer(use_external_dictionaries=False, enable_sentiment=False)
    r = a.analyze("コーヒーはいまいちだった")
    assert r.sentiment.polarity is None
    assert r.sentiment.expressions == []


def test_modules_agree_on_shared_scored_expressions():
    bundle = load_default_bundle()
    text = "サービスは最高だったが料金が高すぎる"
    a = _analyzer()
    tokens = a.tokenize(text)
    scored = score_affect_expressions(text, bundle, tokens)
    emo = detect_emotion(text, bundle, tokens, scored=scored)
    sen = detect_sentiment(text, bundle, tokens, scored=scored)
    assert emo.polarity == sen.affect_polarity
    assert sen.polarity == "negative"  # 高すぎる (evaluative) after the adversative
    assert {e.base_emotion for e in scored} >= {EVALUATION} or emo.expressions


def test_expression_spans_are_original_coordinates():
    text = "ＡＢＣ社の対応はいまいち"
    r = _analyzer().analyze(text)
    exp = r.sentiment.expressions[0]
    assert text[exp.begin : exp.end].startswith("いまいち")


def test_overlay_emotion_word_that_is_also_evaluative():
    r = _analyzer().analyze("クラウドAPIの課金高すぎてしぬw")
    # emotion side keeps the slang / emotion reading
    assert r.emotion.primary is not None
    # evaluation side sees 高すぎ inside 課金高すぎ, with the token prefix as target
    ev = [e for e in r.sentiment.expressions if e.text == "高すぎ"]
    assert ev and ev[0].polarity == "negative" and ev[0].target_text == "課金"
    assert r.sentiment.polarity == "negative"


def test_overlay_positive_and_negated():
    r = _analyzer().analyze("ケーキは最高だった")
    assert r.emotion.primary == "joy"
    # v0.6.6: sentiment.csv lists the conjugated surface too (最高だった), so the evaluation text may be the longer form
    assert any(e.text.startswith("最高") and e.polarity == "positive" and e.target_text == "ケーキ" for e in r.sentiment.expressions)
    r = _analyzer().analyze("この映画は面白くない")
    assert r.sentiment.polarity == "negative" and r.sentiment.expressions[0].negated is True
