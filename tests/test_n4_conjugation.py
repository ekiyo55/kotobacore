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
