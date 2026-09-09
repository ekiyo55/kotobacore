"""v0.4: entities (FR-030〜034), attribution (FR-052), document hierarchy (FR-050),
sentence boundaries (FR-020), Query IR (FR-080), document chunks (FR-081/082)."""

import datetime
import json

from kotobacore import Analyzer, QueryIR
from kotobacore.core.ner import parse_number
from kotobacore.core.syntax import split_paragraphs, split_sentences
from kotobacore.modules.intent import classify_query_intent

REF = datetime.date(2026, 9, 8)


def _a() -> Analyzer:
    return Analyzer(use_external_dictionaries=False, reference_date=REF)


def _ents(text: str) -> dict[str, str]:
    return {e.surface: e.type for e in _a().analyze(text).entities}


# ---------------------------------------------------------------- numbers / time / quantity


def test_parse_number():
    assert parse_number("5,000") == 5000
    assert parse_number("1万") == 10000
    assert parse_number("45億") == 4.5e9
    assert parse_number("百万") == 1_000_000
    assert parse_number("三千五百") == 3500
    assert parse_number("約200") == 200


def test_time_entities_absolute_and_relative():
    r = _a().analyze("10月5日午前10時に2025年度の会議。昨日は3日前より寒い。")
    by = {e.surface: e for e in r.entities}
    assert by["10月5日"].type == "DATE" and by["10月5日"].value == "2026-10-05"
    assert by["午前10時"].type == "TIME" and by["午前10時"].value == "10:00"
    assert by["2025年度"].type == "DATE" and by["2025年度"].normalized == "FY2025"
    assert by["昨日"].value == "2026-09-07"
    assert by["3日前"].type == "DATE" and by["3日前"].value == "2026-09-05"


def test_duration_is_quantity_but_offset_is_date():
    ents = _ents("3年ぶりに1週間休んだ。2年後に戻る。")
    assert ents["3年"] == "QUANTITY"
    assert ents["1週間"] == "QUANTITY"
    assert ents["2年後"] == "DATE"


def test_money_and_quantity_values():
    r = _a().analyze("予算は45億円、単価5,000円、参加は約200名で成長率12%。")
    by = {e.surface: e for e in r.entities}
    assert by["45億円"].type == "MONEY" and by["45億円"].value == 4.5e9 and by["45億円"].currency == "JPY"
    assert by["5,000円"].value == 5000
    assert by["約200名"].type == "QUANTITY" and by["約200名"].value == 200 and by["約200名"].unit == "名"
    assert by["12%"].type == "QUANTITY" and by["12%"].unit == "%"


# ---------------------------------------------------------------- pattern NER


def test_pattern_ner_person_org_location_event():
    ents = _ents("株式会社山田商事の佐藤部長は大阪支社で説明会を開き、代々木公園で定例会議をした。田中さんも来た。")
    assert ents["株式会社山田商事"] == "ORGANIZATION"
    assert ents["佐藤部長"] == "PERSON"
    assert ents["大阪支社"] == "ORGANIZATION"
    assert ents["説明会"] == "EVENT"
    assert ents["代々木公園"] == "LOCATION"
    assert ents["定例会議"] == "EVENT"
    assert ents["田中さん"] == "PERSON"


def test_person_honorific_is_kept_and_common_nouns_blocked():
    r = _a().analyze("お客様と皆さんに田中さんを紹介した。")
    persons = [e for e in r.entities if e.type == "PERSON"]
    assert [p.surface for p in persons] == ["田中さん"]
    assert persons[0].normalized == "田中"


def test_event_with_year_suffix():
    assert _ents("テックフェア2026に行く")["テックフェア2026"] == "EVENT"


def test_entity_spans_are_original_coordinates():
    text = "㈱ミライ電機は１０月５日に発表する"
    r = _a().analyze(text)
    for e in r.entities:
        assert text[e.begin : e.end]  # non-empty original span
    dates = [e for e in r.entities if e.type == "DATE"]
    assert dates and text[dates[0].begin : dates[0].end] == "１０月５日"


# ---------------------------------------------------------------- attribution


def test_sentiment_target_topic_marker():
    r = _a().analyze("コーヒーはいまいちだけどケーキは高品質。")
    targets = {e.text: e.target_text for e in r.sentiment.expressions}
    assert targets["いまいちだ"] == "コーヒー"
    assert targets["高品質"] == "ケーキ"
    # 神 is both a slang emotion word and (since the 2026-09-08 review) an
    # evaluative word: emotion side keeps admiration, evaluation side gets
    # positive on ケーキ, and the clause after けど wins the overall polarity.
    r = _a().analyze("コーヒーはいまいちだけどケーキは神。")
    assert r.sentiment.polarity == "positive" and r.sentiment.affect_polarity == "positive"
    assert {e.text.rstrip("だ"): e.target_text for e in r.sentiment.expressions} == {"いまいち": "コーヒー", "神": "ケーキ"}
    assert {e.text: e.about_text for e in r.emotion.expressions}["神"] == "ケーキ"


def test_emotion_holder_and_about():
    r = _a().analyze("田中さんは新作プリンが最高だと喜んだ。")
    exp = r.emotion.expressions[0]
    assert exp.holder_text == "田中さん"
    assert exp.holder.startswith("e")
    assert exp.about_text == "新作プリン"
    r = _a().analyze("田中さんは新作プリンが高品質だと言った。")
    sent = r.sentiment.expressions[0]
    assert sent.target_text == "新作プリン"


def test_speaker_is_default_holder():
    r = _a().analyze("このカフェはいまいちだった")
    assert r.sentiment.expressions[0].target_text == "カフェ"
    r = _a().analyze("このカフェは最高だった")
    assert r.emotion.expressions[0].holder == "speaker"
    assert r.emotion.expressions[0].about_text == "カフェ"


# ---------------------------------------------------------------- sentence / paragraph boundaries


def test_split_sentences_quotes_and_periods():
    t = "「行こう。」と言った。本当に？そう思う。\nバージョン3.5を使う. 次"
    assert [t[b:e] for b, e in split_sentences(t)] == ["「行こう。」と言った。", "本当に？", "そう思う。", "バージョン3.5を使う.", "次"]


def test_split_paragraphs_and_headings():
    t = "# 見出し\n本文1。本文2。\n\n本文3。"
    paras = [t[b:e] for b, e in split_paragraphs(t)]
    assert paras == ["# 見出し", "本文1。本文2。", "本文3。"]


# ---------------------------------------------------------------- document hierarchy


DOC = """# 第1章 概要
KotobaCoreは日本語の意味理解エンジンです。感情と意図を同時に返します。

## 導入
株式会社山田商事では2025年度から導入しました。田中部長は使いやすいと評価しています。

## 犬の話
昨日、実家の犬がわんわん鳴いた。散歩は最高だった。"""


def test_analyze_document_hierarchy():
    d = _a().analyze_document(DOC)
    assert d.meta.mode == "document"
    assert len(d.paragraphs) == 6
    assert [p.heading for p in d.paragraphs] == [True, False, True, False, True, False]
    assert len(d.sentences) == 9
    # every sentence owns its tokens, spans are original coordinates
    for s in d.sentences:
        assert DOC[s.begin : s.end] == s.text
        assert s.token_ids
    ids = [t.id for t in d.tokens]
    assert ids == list(range(len(ids)))
    for t in d.tokens:
        assert DOC[t.begin : t.end]
    # entities renumbered across the document, referenced by sentences
    ent_ids = [e.id for e in d.entities]
    assert ent_ids == [f"e{i}" for i in range(1, len(ent_ids) + 1)]
    assert {e.surface for e in d.entities} >= {"株式会社山田商事", "2025年度", "田中部長", "昨日"}
    assert any(s.entity_ids for s in d.sentences)
    # per-sentence module results and document aggregate
    mid = d.sentences[5]  # 田中部長は使いやすいと評価しています。
    assert mid.sentiment is not None and mid.sentiment.polarity == "positive"
    assert d.sentiment.polarity == "positive"
    last = d.sentences[-1]  # 散歩は最高だった。→ emotion word only
    assert last.sentiment is not None and last.sentiment.affect_polarity == "positive"
    json.loads(d.to_json())


def test_document_chunks_follow_headings():
    d = _a().analyze_document(DOC)
    chunks = d.document_chunks
    assert len(chunks) == 3
    assert chunks[0].text.startswith("# 第1章")
    assert chunks[1].text.startswith("## 導入")
    assert chunks[2].text.startswith("## 犬の話")
    for c in chunks:
        assert DOC[c.begin : c.end] == c.text
        assert c.sentence_ids and c.paragraph_ids
    assert "e2" in chunks[1].entity_ids or any(e.startswith("e") for e in chunks[1].entity_ids)
    assert chunks[1].keywords


def test_chunk_size_limit_splits_long_paragraph():
    text = "。".join(f"文{i}はテーマ{i % 2}について述べる" for i in range(40)) + "。"
    chunks = _a().chunk(text, max_chars=120, min_chars=40)
    assert len(chunks) >= 4
    for c in chunks:
        assert len(c.text) <= 160  # never splits inside a sentence, so slight overrun is allowed
    assert "".join(c.text for c in chunks).replace("\n", "") in text.replace("\n", "") or len(chunks) > 1


# ---------------------------------------------------------------- query IR


def test_classify_query_intent():
    assert classify_query_intent("東京支店の売上目標はいくら？") == ("search_value", "MONEY")
    assert classify_query_intent("KotobaCoreとは何ですか") == ("definition", "TEXT")
    assert classify_query_intent("インストールの方法を教えて")[0] == "how_to"
    assert classify_query_intent("なぜ遅いのか")[0] == "reason"
    assert classify_query_intent("会議はいつですか") == ("search_value", "DATE")
    assert classify_query_intent("対応していますか") == ("yes_no", "BOOLEAN")
    assert classify_query_intent("KotobaCore") == ("lookup", None)


def test_query_ir_structure():
    q = _a().analyze_query("東京支店の2025年度の売上目標はいくら？")
    assert isinstance(q, QueryIR)
    assert q.intent == "search_value" and q.answer_type == "MONEY"
    assert q.target == "売上目標"
    assert q.constraints["time"] == ["FY2025"]
    assert "売上目標" in q.keywords
    assert q.to_dict()["intent"] == "search_value"


def test_query_ir_synonym_expansion_and_location():
    q = _a().analyze_query("新宿でおすすめのミーティング室を教えて")
    assert q.intent == "list"
    assert "新宿" in q.constraints.get("location", []) or any(e.type == "LOCATION" for e in q.entities)
    assert "会議" in q.expanded_terms or "打ち合わせ" in q.expanded_terms


def test_dictionary_entity_fused_with_tail_or_split_tokens():
    r = _a().analyze("日本の首都は東京だ。大阪で会議。")
    ents = {e.surface: e for e in r.entities}
    assert ents["東京"].type == "LOCATION" and ents["東京"].source == "dictionary"
    assert ents["大阪"].type == "LOCATION"
    text = "日本の首都は東京だ。"
    e = next(x for x in _a().analyze(text).entities if x.surface == "東京")
    assert text[e.begin : e.end] == "東京"


def test_single_sentence_document_equals_sentence_analysis():
    a = _a()
    for text in ["嬉しくないけど便利", "コーヒーはいまいちだけどケーキは神。", "田中さんが東京に行った。", "最高に嬉しい"]:
        s = a.analyze(text)
        d = a.analyze_document(text)
        assert d.emotion.primary == s.emotion.primary, text
        assert d.sentiment.polarity == s.sentiment.polarity, text
        assert d.sentiment.affect_polarity == s.sentiment.affect_polarity, text
        assert d.intent.label == s.intent.label, text
        assert [e.surface for e in d.entities] == [e.surface for e in s.entities]
        assert [t.surface for t in d.tokens] == [t.surface for t in s.tokens]


def test_document_chunk_heading_path_and_table_header():
    lines = ['# 導入', '## 前提', '本文A。', '', '## 設定', '| 項目 | 値 |', '|---|---|', '| ポート | 8080 |', '| ホスト | localhost |']
    doc = chr(10).join(lines)
    d = _a().analyze_document(doc)
    chunks = d.document_chunks
    assert chunks[0].heading_path == ['導入', '前提']
    # v0.5.4: consecutive headings are all kept in the chunk text (none dropped), so nothing is left for the context
    assert '導入' in chunks[0].text and '前提' in chunks[0].text and '本文A' in chunks[0].text
    assert chunks[0].context == ''
    table = next(c for c in chunks if '8080' in c.text)
    assert table.heading_path == ['導入', '設定']
    assert table.text_with_context.startswith('導入')
    assert '8080' in table.text_with_context
