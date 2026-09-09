"""v0.6.5: taxonomy aligned to the human evaluation set — surprise / trust / disgust emotions,
exaggeration demoted to an intensifier, inform / share_experience intents."""

from kotobacore import Analyzer

_A = Analyzer()


def _emo(text):
    r = _A.analyze(text)
    return r.emotion.primary if r.emotion else None, r.emotion.polarity if r.emotion else None


def test_surprise_words_are_surprise_not_exaggeration():
    for text in ("新しいGPUのベンチマーク、前世代の1.8倍で驚いた。", "うわっ、びっくりした！", "「まさか、あなたが」と、彼女は息を呑んだ。", "この写真、加工なしでこれ？信じられない"):
        primary, _ = _emo(text)
        assert primary == "surprise", (text, primary)


def test_trust_and_disgust_exist():
    assert _emo("新しいバイトの先輩が優しくて安心した。")[0] in ("trust", "joy")
    assert _emo("Rustのコンパイラ、厳しいけど的確で信頼できる。")[0] == "trust"
    assert _emo("あの人のこと苦手なんだよね。")[0] == "disgust"
    primary, polarity = _emo("正直、気持ち悪い。")
    assert primary == "disgust" and polarity == "negative"


def test_exaggeration_never_outranks_a_real_emotion():
    assert _emo("今日のランチ、マジで美味しかった😋")[0] == "joy"
    assert _emo("ワンワン吠えてる犬、めっちゃ可愛い🐶")[0] == "joy"
    # alone it still counts (golden set: しぬw)
    assert _emo("しぬw")[0] == "exaggeration"


def test_intent_feedback_vs_share_experience_vs_inform():
    def intent(text):
        return _A.analyze(text).intent.label

    assert intent("新しいiPhone買ったけど正直そこまで感動しない。") in ("negative_feedback", "share_experience")
    assert intent("今日のランチ、マジで美味しかった😋") == "share_experience"  # emotion only + personal cues
    assert intent("2025年度の売上は前年比12％増の45億円となりました。") == "inform"  # declarative, no signal
    assert intent("来週の定例会議は水曜10時に変更いたします。") == "inform"
    assert intent("このカフェの接客、対応が雑で使いにくい。") == "negative_feedback"  # evaluative word → feedback
    assert intent("返金はいつになりますか？") == "question"
    assert intent("KotobaCore") == "unknown"  # a fragment is still unknown
