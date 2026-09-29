"""v0.6.3: N4 語形正規化 — verb / adjective lemma, 活用型・活用形, okurigana variant normalization (FR-002 N4 / FR-010)."""

from kotobacore import Analyzer
from kotobacore.core.token.conjugation import analyze_adjective, analyze_verb

_A = Analyzer(enable_emotion=False, enable_sentiment=False, enable_intent=False, enable_rag=False)


def _tok(text):
    return {t.surface: t for t in _A.tokenize(text)}


def test_verb_lemmas_and_types():
    cases = {
        "書いた": ("書く", "五段", "過去"), "泳いだ": ("泳ぐ", "五段", "過去"), "食べた": ("食べる", "一段", "過去"),
        "起きた": ("起きる", "一段", "過去"), "来た": ("来る", "カ変", "過去"), "書かない": ("書く", "五段", "否定"),
        "来なかった": ("来る", "カ変", "否定-過去"), "見ない": ("見る", "一段", "否定"), "見ます": ("見る", "一段", "丁寧"),
        "食べさせられなかった": ("食べる", "一段", "使役-受身-否定-過去"), "書こう": ("書く", "五段", "意志"),
        "食べよう": ("食べる", "一段", "意志"), "書く": ("書く", "五段", "基本形"), "待った": ("待つ", "五段", "過去"),
        "買った": ("買う", "五段", "過去"), "飛んだ": ("飛ぶ", "五段", "過去"), "死んだ": ("死ぬ", "五段", "過去"),
        "起きます": ("起きる", "一段", "丁寧"), "扱う": ("扱う", "五段", "基本形"), "待っています": ("待つ", "五段", "進行-丁寧"),
        "した": ("する", "サ変", "過去"), "静かだった": ("静かだ", "形容動詞", "過去"),
        # 一段 stems ending in れ / せ are not 五段 passive / causative (v0.6.5 fix)
        "疲れた": ("疲れる", "一段", "過去"), "忘れた": ("忘れる", "一段", "過去"), "晴れた": ("晴れる", "一段", "過去"),
        "任せた": ("任せる", "一段", "過去"), "書かれた": ("書く", "五段", "受身-過去"), "書かせた": ("書く", "五段", "使役-過去"),
    }
    for surface, (lemma, ctype, form) in cases.items():
        info = analyze_verb(surface)
        assert info is not None, surface
        assert (info.lemma, info.conjugation_type, info.conjugation_form) == (lemma, ctype, form), (surface, info)
    # dictionary-only ambiguities are labelled, not hidden
    info = analyze_verb("走った")
    assert info.lemma == "走る" and info.conjugation_type == "五段?"
    info = analyze_verb("読んだ")
    assert info.lemma == "読む" and info.conjugation_type == "五段?"


def test_adjective_forms():
    assert analyze_adjective("美味しかった").lemma == "美味しい" and analyze_adjective("美味しかった").conjugation_form == "過去"
    assert analyze_adjective("高くない").conjugation_form == "否定" and analyze_adjective("高くない").conjugation_type == "形容詞"
    assert analyze_adjective("高ければ").conjugation_form == "仮定" and analyze_adjective("高い").conjugation_form == "基本形"


def test_tokens_carry_lemma_and_conjugation():
    toks = _tok("走ったので食べさせられなかった。美味しかった。")
    # the lattice glues the conjunctive particle onto the verb (走ったので); N4 peels it into the form label
    assert toks["走ったので"].dictionary_form == "走る" and toks["走ったので"].conjugation_form == "過去-接続-理由"
    t = toks["食べさせられなかった"]
    assert t.dictionary_form == "食べる" and t.conjugation_type == "一段" and t.conjugation_form == "使役-受身-否定-過去"
    a = toks["美味しかった"]
    assert a.dictionary_form == "美味しい" and a.conjugation_type == "形容詞" and a.conjugation_form == "過去"
    # nouns carry nothing
    assert all(t.conjugation_type is None for t in _A.tokenize("東京と大阪"))


def test_conditional_forms_assemble():
    toks = _tok("走れば食べれば書けば")
    assert {"走れば", "食べれば", "書けば"} <= set(toks)
    assert toks["書けば"].dictionary_form == "書く" and toks["書けば"].conjugation_form == "仮定"
    assert toks["食べれば"].dictionary_form == "食べる"


def test_okurigana_variants_normalize_and_tokenize_whole():
    toks = _A.tokenize("申し込みと申込みと申込、見積もりと見積、引き落としと引落と引落し、買物")
    surfaces = [t.surface for t in toks]
    for s in ("申し込み", "申込み", "申込", "見積もり", "見積", "引き落とし", "引落", "引落し", "買物"):
        assert s in surfaces, (s, surfaces)
    by = {t.surface: t for t in toks}
    assert by["申込み"].normalized == by["申込"].normalized == by["申し込み"].normalized == "申し込み"
    assert by["見積"].normalized == "見積もり" and by["引落"].normalized == by["引落し"].normalized == "引き落とし"
    assert by["買物"].normalized == "買い物"
    # surfaces are untouched (N3〜N5 never rewrite surface)
    assert by["引落"].surface == "引落" and by["引落"].begin >= 0


def test_okurigana_normalized_reaches_chunk_keywords():
    d = _A.analyze_document("# 申込\n\n申込の受付は締切まで。\n\n引落は毎月27日。")
    kws = {k for c in d.document_chunks for k in c.keywords}
    assert "申し込み" in kws and "引き落とし" in kws


def test_lemma_through_passive_and_negated_progressive():
    # v1.1 (DD evaluation report §7-6): 払われていない → 払う (was 払われている)
    from kotobacore.core.token.conjugation import analyze_conjugation

    cases = {
        "払われていない": "払う", "織り込まれていない": "織り込む", "扱われている": "扱う",
        "採用していない": "採用する", "言われていた": "言う", "読んでいない": "読む",
        "行った": "行く", "忘れていない": "忘れる", "晴れている": "晴れる", "茹でた": "茹でる",
    }
    for surface, lemma in cases.items():
        assert analyze_conjugation(surface, "動詞-一般").lemma == lemma, surface


def test_lemma_rules_v11_sudachi_agreement():
    # v1.1: long-standing lemma errors found by comparing with Sudachi's dictionary_form
    from kotobacore.core.token.conjugation import analyze_conjugation

    verb = {
        "捨てた": "捨てる", "見捨てられる": "見捨てる", "申し立てる": "申し立てる",  # 一段 て-stem (was 捨る)
        "泣きそう": "泣く", "昇天しそう": "昇天する", "美味しそう": "美味しい",  # そう (was 泣きす)
        "面白すぎて": "面白い", "楽しみすぎて": "楽しむ", "押しすぎて": "押す", "疲れすぎてる": "疲れる",
        "出てしまった": "出る", "助けてくれて": "助ける", "感じております": "感じる", "止まらなくなった": "止まる",
        "落ちるんだ": "落ちる", "転職したんだ": "転職する", "冷えるよう": "冷える",  # was 落ちるむ / 冷えるる
        "情けない": "情けない", "仕方ない": "仕方ない", "冷たい": "冷たい", "必要ない": "必要ない",  # was 情ける / 冷る
        "激しく": "激しい", "間違った": "間違う", "傘持った": "傘持つ", "生まれた": "生まれる",
        "満たせない": "満たせる", "報われない": "報う", "存在しない": "存在する", "勉強させる": "勉強する",
        "聞い": "聞く", "思い": "思う", "見た": "見る", "来た": "来る",
    }
    for surface, lemma in verb.items():
        assert analyze_conjugation(surface, "動詞-一般").lemma == lemma, surface
    # 若しく(は) is the conjunction もしくは, not an adjective 若しい (regression fixed in 1.1.0a13)
    assert analyze_conjugation("若しく", "形容詞-一般") is None
    assert analyze_conjugation("若しく", "動詞-一般") is None
    adj = {"やばい": "やばい", "すごく": "すごい", "誇らしく": "誇らしい", "厚く": "厚い", "高かった": "高い",
           "思い": "思う", "受かった": "受かる", "関わりたくない": "関わる"}
    for surface, lemma in adj.items():
        assert analyze_conjugation(surface, "形容詞-一般").lemma == lemma, surface


def test_adverbial_kanji_adjective_lemma_does_not_feed_emotion():
    # 遅くなって: lemma 遅い is for search; the emotion / evaluation layer keeps the pre-1.1 reading
    from kotobacore import Analyzer

    r = Analyzer().analyze("ごめんね、遅くなって。")
    tok = next(t for t in r.tokens if t.surface == "遅く")
    assert tok.dictionary_form == "遅い"
    assert r.intent.label != "negative_feedback"


def test_notation_variants_share_tokens_v11():
    # v1.1 (DD evaluation report §7-7): katakana and okurigana variants tokenize alike
    from kotobacore import Analyzer

    a = Analyzer()

    def norm(s):
        return [t.normalized for t in a.tokenize(s) if not t.pos.startswith(("助詞", "記号"))]

    for x, y in [
        ("ランサムウエア", "ランサムウェア"), ("ウィルス対策", "ウイルス対策"), ("ルータ交換", "ルーター交換"),
        ("退職給付引き当て金", "退職給付引当金"), ("売り上げ高", "売上高"), ("取り引き先", "取引先"),
        ("繰り越し欠損金", "繰越欠損金"), ("未払い残業代", "未払残業代"), ("申し込み", "申込み"),
    ]:
        assert norm(x) == norm(y), (x, y)
    # okurigana stays when no kanji follows
    assert a.tokenize("引き当てを行う")[0].surface == "引き当て"
    # a dictionary word with okurigana inside a kanji run
    assert [t.surface for t in a.tokenize("偽装請け負い")] == ["偽装", "請け負い"]


def test_length_changing_normalization_keeps_original_span():
    # v1.1: サーバ→サーバー used to map the token to a 1-char original span
    from kotobacore import Analyzer

    for s, first in [("サーバの設定", "サーバ"), ("ルータの設定", "ルータ"), ("退職給付引き当て金", "退職給付引き当て金"),
                     ("(株)山田商事", "(株)山田商事")]:
        t = Analyzer().tokenize(s)[0]
        assert s[t.begin:t.end] == first, s


def test_complaint_vocabulary_and_polite_adjectives_v11():
    # v1.1: 遅いです (adjective + polite copula) keeps the adjective lemma, complaint words are negative
    from kotobacore import Analyzer
    from kotobacore.core.token.conjugation import analyze_conjugation

    assert analyze_conjugation("遅いです", "動詞-一般").lemma == "遅い"
    assert analyze_conjugation("美味しかったです", "動詞-一般").lemma == "美味しい"
    a = Analyzer(use_external_dictionaries=False, use_config=False)
    r = a.analyze("先週届いた商品が破損していました。電話しても全くつながらず、対応があまりにも遅いです。")
    assert r.sentiment.polarity == "negative"
    assert {"破損", "つながらず", "遅いです"} <= {e.text for e in r.sentiment.expressions}
    assert a.analyze("今月の請求書が二重請求になっていて、非常に不愉快です。").sentiment.polarity == "negative"
    # words used neutrally in reports, laws and apologies are not in the lexicon
    assert a.analyze("弊社の手違いでご迷惑をおかけし、誠に申し訳ございません。").sentiment.polarity is None
    assert a.analyze("心身の故障により職務を執行できない者").sentiment.polarity is None


def test_request_with_negative_evaluation_is_a_complaint_v11():
    # v1.1: 否定の評価を伴う依頼は苦情 (negative_feedback); the request stays as the next candidate
    from kotobacore import Analyzer

    a = Analyzer(use_external_dictionaries=False, use_config=False)
    r = a.analyze("先週届いた商品が破損していました。電話しても全くつながらず、対応があまりにも遅いです。至急返金してください。")
    assert r.intent.label == "negative_feedback"
    assert [c.label for c in r.intent.candidates][:2] == ["negative_feedback", "request"]
    # a plain request, a notice, a negated evaluation and someone else's complaint stay as they were
    assert a.analyze("来月導入予定のプリンター20台について、お見積りをお願いできますでしょうか。").intent.label == "request"
    assert a.analyze("9月分のご請求書を添付にてお送りいたします。ご確認のほどよろしくお願いいたします。").intent.label == "request"
    assert a.analyze("対応は遅くないので、引き続きよろしくお願いします。").intent.label == "request"
    assert a.analyze("部長は対応が遅いと不満でした。至急ご確認ください。").intent.label != "negative_feedback"

