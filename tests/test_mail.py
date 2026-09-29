"""Business-mail boilerplate handling (v1.1, Analyzer.analyze_mail)."""

from kotobacore import Analyzer
from kotobacore.core.mail import boilerplate_kinds
from kotobacore.core.syntax import split_sentences

MAIL = """株式会社サンプル
営業部 田中様

いつもお世話になっております。
ABC株式会社の山田です。

9月分のご請求書を添付にてお送りいたします。
お支払期日は10月31日となっております。

ご確認のほどよろしくお願いいたします。

--
ABC株式会社 山田太郎
TEL: 03-1234-5678"""


def _kinds(text):
    ss = [text[b:e] for b, e in split_sentences(text)]
    return list(zip(ss, boilerplate_kinds(ss)))


def test_boilerplate_kinds():
    k = dict(_kinds(MAIL))
    assert k["営業部 田中様"] == "salutation" and k["株式会社サンプル"] == "salutation"
    assert k["いつもお世話になっております。"] == "greeting"
    assert k["ABC株式会社の山田です。"] == "self_intro"
    assert k["ご確認のほどよろしくお願いいたします。"] == "closing"
    assert k["TEL: 03-1234-5678"] == "signature" and k["--"] == "signature"
    assert k["9月分のご請求書を添付にてお送りいたします。"] is None
    # a real request is content, a bare sign-off name after the closing is the signature, quotes are quotes
    k = dict(_kinds("お疲れ様です。\n早急に確認をお願いします。\nよろしくお願いします。\n佐藤\n> 先日の件、承知しました。"))
    assert k["早急に確認をお願いします。"] is None and k["佐藤"] == "signature" and k["> 先日の件、承知しました。"] == "quote"


def test_analyze_mail_uses_content_sentences_only():
    a = Analyzer(use_external_dictionaries=False, use_config=False)
    d = a.analyze_document(MAIL)
    m = a.analyze_mail(MAIL)
    assert m.meta.mode == "mail"
    # keywords come from the body; a closing that asks for an action (ご確認のほど…) keeps the request (1.1.0a17)
    assert d.intent.axes.speech_act == "request"
    assert m.intent.axes.speech_act == "request" and m.intent.label == "inform"
    # a pure sign-off does not make the notice a request
    p = a.analyze_mail(MAIL.replace("ご確認のほどよろしくお願いいたします。", "今後ともよろしくお願いいたします。"))
    assert p.intent.axes.speech_act == "statement"
    assert m.rag.keywords[0] != "株式会社サンプル" and "請求書" in m.rag.keywords
    # the whole text is still analysed: sentences, tokens and positions cover everything
    assert len(m.sentences) == len(d.sentences) and len(m.tokens) == len(d.tokens)
    assert [s.boilerplate for s in m.sentences][:4] == ["salutation", "salutation", "greeting", "self_intro"]
    # a complaint mail stays a complaint
    c = a.analyze_mail(MAIL.replace("9月分のご請求書を添付にてお送りいたします。\nお支払期日は10月31日となっております。",
                                    "届いた商品が破損していました。至急返金してください。"))
    assert c.intent.label == "negative_feedback" and c.intent.axes.evaluation == "negative"


def test_real_mail_shapes_v11a17():
    # found on real mails (aimail evaluation): a body line starting with メール, a URL line and a
    # section separator are content; Outlook / Gmail reply headers open the quote
    k = dict(_kinds("お世話になっております。\nメール確認いたしました。\n資料は下記からご覧ください。\nhttps://example.com/doc\n"
                    "----------\n納期は来週です。\n----------\nよろしくお願いいたします。\n山田"))
    assert k["メール確認いたしました。"] is None and k["https://example.com/doc"] is None
    assert k["----------"] is None and k["納期は来週です。"] is None and k["山田"] == "signature"
    k = dict(_kinds("承知しました。\n\nFrom: 山田 <y@example.com>\nSent: Monday, September 1, 2026 10:00 AM\n"
                    "To: 佐藤\nSubject: 見積の件\n見積をお願いします。"))
    assert k["承知しました。"] is None and k["From: 山田 <y@example.com>"] == "quote" and k["見積をお願いします。"] == "quote"
    k = dict(_kinds("了解です。\n2026年9月1日(月) 10:00 山田 太郎 <y@example.com>:\n明日伺います。"))
    assert k["了解です。"] is None and k["明日伺います。"] == "quote"
    # a signature is a short block with contact details at the end
    k = dict(_kinds("明日伺います。\n--\nABC株式会社\n山田太郎\nTEL: 03-1234-5678\nMail: y@example.com"))
    assert k["明日伺います。"] is None and k["--"] == "signature" and k["Mail: y@example.com"] == "signature"


def test_url_is_not_split_and_formula_words_v11a17():
    # a ? inside a URL no longer ends a sentence (every tracking link became a "question")
    t = "詳細は下記をご覧ください。\nhttps://example.com/a?id=3&utm=mail\nURLはhttps://x.jp/a.htmlです。次。"
    assert [t[b:e] for b, e in split_sentences(t)] == [
        "詳細は下記をご覧ください。", "https://example.com/a?id=3&utm=mail", "URLはhttps://x.jp/a.htmlです。", "次。"]
    a = Analyzer(use_external_dictionaries=False, use_config=False)
    # いつも / どうぞ / 何卒 / 〜かどうか are not questions
    for s in ("いつもお世話になっております。", "どうぞよろしくお願いいたします。", "確認済みかどうかを記録する。"):
        assert a.analyze(s).intent.axes.speech_act != "question", s
    assert a.analyze("いつ届きますか。").intent.axes.speech_act == "question"
    # more closing / greeting formulas; organisation-looking words inside other words are not a self-introduction
    k = dict(_kinds("いつもお世話になりありがとうございます。\n本件承知しました。\n今後ともどうぞよろしくお願いします。\n"
                    "これは外部連携のテストです。\n以上です。"))
    assert k["いつもお世話になりありがとうございます。"] == "greeting" and k["今後ともどうぞよろしくお願いします。"] == "closing"
    assert k["以上です。"] == "closing" and k["これは外部連携のテストです。"] is None and k["本件承知しました。"] is None
