"""v0.5: predicate-argument structure (FR-023), relations / events (FR-040/041),
topics (FR-063), retrieval / reranking features (FR-083/084), reference retrievers."""

import datetime

from kotobacore import Analyzer
from kotobacore.core.syntax import negation_after, split_clauses
from kotobacore.rag import (
    ChunkView,
    InMemoryRetriever,
    PgVectorRetriever,
    rerank,
    rerank_features,
    rerank_score,
    retrieval_features,
)

REF = datetime.date(2026, 9, 8)


def _a() -> Analyzer:
    return Analyzer(use_external_dictionaries=False, reference_date=REF)


# ---------------------------------------------------------------- predicates


def test_predicate_arguments_with_case_particles():
    r = _a().analyze("昨日、田中さんが新しいカフェに行った。")
    assert len(r.predicates) == 1
    p = r.predicates[0]
    assert p.text == "行った"
    roles = {a.role: a.text for a in p.arguments}
    assert roles["subject"] == "田中さん"
    assert roles["goal"] == "カフェ"
    assert roles["time"] == "昨日"
    subj = next(a for a in p.arguments if a.role == "subject")
    assert subj.entity_id and subj.entity_id.startswith("e")


def test_continuative_clause_gives_one_predicate_per_clause():
    r = _a().analyze("株式会社山田商事は2025年度に大阪支社を設立し、佐藤部長が説明会を開いた。")
    texts = [p.text for p in r.predicates]
    assert texts == ["設立し", "開いた"]
    first = {a.role: a.text for a in r.predicates[0].arguments}
    assert first["subject"] == "株式会社山田商事" and first["object"] == "大阪支社" and first["time"] == "2025年度"
    second = {a.role: a.text for a in r.predicates[1].arguments}
    assert second["subject"] == "佐藤部長" and second["object"] == "説明会"


def test_nominal_and_negated_predicates():
    r = _a().analyze("ケーキは神。会議は中止になった。私はそれを買わない。")
    by = {p.text: p for p in r.predicates}
    assert by["神"].nominal is True and {a.role: a.text for a in by["神"].arguments}["subject"] == "ケーキ"
    assert by["なった"].lemma == "なる"  # v0.6.3 N4: predicates carry the verb lemma
    assert by["買わない"].negated is True


def test_passive_voice():
    r = _a().analyze("新製品は10月に発売されます。")
    p = r.predicates[0]
    assert p.voice == "passive" and p.lemma == "発売"
    assert {a.role: a.text for a in p.arguments}["time"] == "10月"


# ---------------------------------------------------------------- relations / events


def test_events_and_relations():
    r = _a().analyze("株式会社山田商事は2025年度に大阪支社を設立した。")
    ev = r.events[0]
    assert ev.type == "FOUND" and ev.agent_text == "株式会社山田商事" and ev.object_text == "大阪支社" and ev.time_text == "2025年度"
    assert ev.agent and ev.object and ev.time  # entity ids
    rel = r.relations[0]
    assert (rel.source_text, rel.relation, rel.role, rel.target_text) == ("株式会社山田商事", "FOUND", "object", "大阪支社")


def test_event_type_fallback_and_state():
    r = _a().analyze("このカメラは軽い。田中さんが東京に引っ越した。")
    types = {e.predicate: e.type for e in r.events}
    assert types.get("軽い") == "STATE"
    assert any(t == "MOVE" for t in types.values())


def test_verb_negation_reaches_emotion_and_sentiment():
    text = "新しいiPhoneには感動しない。"
    assert negation_after(text, text.index("感動") + 2, split_clauses(text)[0]) == len("しない")
    r = _a().analyze(text)
    assert r.emotion.expressions and r.emotion.expressions[0].negated is True
    assert r.sentiment.affect_polarity == "negative"


def test_document_merges_predicates_events_topics():
    doc = "# 概要\n株式会社山田商事は大阪支社を設立した。\n\n田中部長は説明会を開いた。"
    d = _a().analyze_document(doc)
    assert [p.id for p in d.predicates] == ["p1", "p2"]
    assert [e.id for e in d.events] == ["ev1", "ev2"]
    assert all(e.predicate_id in {p.id for p in d.predicates} for e in d.events)
    assert d.topics is not None and d.topics.topics
    assert d.events[0].agent in {e.id for e in d.entities}


# ---------------------------------------------------------------- topics


def test_topics_prefer_entities_then_frequent_nouns():
    r = _a().analyze("円安で値上げが続く。値上げは家計に響く。")
    labels = [t.label for t in r.topics.topics]
    assert "円安" in labels or "値上げ" in labels
    top = r.topics.topics[0]
    assert top.score <= 1.0 and top.count >= 1


# ---------------------------------------------------------------- retrieval / rerank features


DOC = """## 東京支店の業績
東京支店の2025年度の売上目標は45億円です。前年度比12%増を狙います。

## 犬の話
昨日、実家の犬がわんわん鳴いた。散歩はいまいちだった。"""


def test_retrieval_features_and_rerank_prefers_matching_chunk():
    a = _a()
    doc = a.analyze_document(DOC)
    q = a.analyze_query("東京支店の2025年度の売上目標はいくら？")
    feats = retrieval_features(q)
    assert feats["answer_type"] == "MONEY" and "FY2025" in feats["filters"]["time"]
    assert "売上目標" in feats["search_terms"]
    views = [ChunkView.from_chunk(c, doc) for c in doc.document_chunks]
    ranked = rerank(q, views)
    best_idx, best_score, best_feats = ranked[0]
    assert "売上目標" in views[best_idx].text
    assert best_feats["intent_match"] == 1.0 and best_feats["time_match"] == 1.0
    assert best_score > ranked[-1][1]


def test_rerank_score_renormalizes_missing_signals():
    f = {"entity_match": 1.0, "keyword_overlap": None, "intent_match": None, "time_match": None, "topic_match": None, "sentiment_match": None}
    assert rerank_score(f) == 1.0
    assert rerank_score(f, semantic_similarity=0.0) < 1.0
    custom = rerank_score(f, semantic_similarity=0.0, weights={"entity_match": 0.5, "semantic_similarity": 0.5})
    assert custom == 0.5


def test_rerank_features_sentiment_and_topic():
    a = _a()
    doc = a.analyze_document(DOC)
    q = a.analyze_query("散歩はいまいちだった？")
    view = ChunkView.from_chunk(doc.document_chunks[-1], doc)
    f = rerank_features(q, view)
    assert f["sentiment_match"] == 1.0
    assert f["keyword_overlap"] is not None and f["keyword_overlap"] > 0


def test_in_memory_retriever_with_fake_embedding():
    a = _a()
    doc = a.analyze_document(DOC)

    def embed(texts):
        # toy embedding: bag of a few characters → deterministic vectors
        keys = "東京支店売上目標億円犬散歩鳴"
        return [[float(t.count(ch)) for ch in keys] for t in texts]

    ret = InMemoryRetriever(embed)
    assert ret.index("doc1", doc) == len(doc.document_chunks)
    hits = ret.search(a.analyze_query("東京支店の売上目標はいくら？"), k=2)
    assert hits and "売上目標" in hits[0].text
    assert hits[0].similarity is not None and hits[0].score >= hits[-1].score


def test_in_memory_retriever_without_embedding_uses_features_only():
    a = _a()
    ret = InMemoryRetriever()
    ret.index("doc1", a.analyze_document(DOC))
    hits = ret.search(a.analyze_query("犬はどうした？"), k=1)
    assert hits and "犬" in hits[0].text and hits[0].similarity is None


def test_pgvector_sql_generation():
    a = _a()
    doc = a.analyze_document(DOC)
    pg = PgVectorRetriever(table="t", dim=4)
    assert "vector(4)" in pg.ddl()
    rows = pg.insert_rows("doc1", doc, [[0.1, 0.2, 0.3, 0.4]] * len(doc.document_chunks))
    assert len(rows) == len(doc.document_chunks) and rows[0][0].startswith("INSERT INTO t")
    sql, params = pg.search_sql(a.analyze_query("東京支店の2025年度の売上目標はいくら？"), k=7)
    assert "embedding <=> %(qvec)s::vector" in sql and params["k"] == 7
    assert "dates && %(dates)s" in sql and "FY2025" in params["dates"]


def test_time_compatible_granularity():
    from kotobacore.rag.features import time_compatible

    assert time_compatible("FY2026", "2026-04-01") and not time_compatible("FY2026", "2026-03-31")
    assert time_compatible("FY2025", "2026-01-15")
    assert time_compatible("2027", "2027-05-01") and time_compatible("2026-10", "2026-10-05")
    assert time_compatible("FY2026", "2026") and not time_compatible("2026-10", "2026-11-01")


def test_product_code_entities_and_query_keywords():
    a = _a()
    ents = {e.surface: e.type for e in a.analyze("エアクリア MX-500 と PrintMaster X200、トナー TN-X200").entities}
    assert ents["MX-500"] == "PRODUCT" and ents["X200"] == "PRODUCT" and ents["TN-X200"] == "PRODUCT"
    q = a.analyze_query("MX-500の価格はいくら")
    assert any(e.surface == "MX-500" and e.type == "PRODUCT" for e in q.entities)
    assert q.constraints.get("product") == ["MX-500"]


def test_rerank_score_hybrid_auto_switch():
    from kotobacore.rag.features import DEFAULT_WEIGHTS, HYBRID_WEIGHTS

    f = {"entity_match": 0.0, "keyword_overlap": 0.0, "intent_match": None, "time_match": None, "topic_match": None, "sentiment_match": None}
    # lexical path unchanged: BM25 handed in as semantic_similarity, DEFAULT_WEIGHTS
    lex = rerank_score(f, semantic_similarity=1.0)
    assert abs(lex - DEFAULT_WEIGHTS["semantic_similarity"] / (DEFAULT_WEIGHTS["semantic_similarity"] + DEFAULT_WEIGHTS["entity_match"] + DEFAULT_WEIGHTS["keyword_overlap"])) < 1e-3
    # hybrid path: retrieval_score present → HYBRID_WEIGHTS, fused score dominates
    hyb = rerank_score(f, semantic_similarity=0.0, retrieval_score=1.0)
    present = HYBRID_WEIGHTS["retrieval_score"] + HYBRID_WEIGHTS["semantic_similarity"] + HYBRID_WEIGHTS["entity_match"] + HYBRID_WEIGHTS["keyword_overlap"] + HYBRID_WEIGHTS["lexical_similarity"]
    assert abs(hyb - HYBRID_WEIGHTS["retrieval_score"] / present) < 1e-3
    assert hyb > 0.5
    # explicit override still works on the hybrid set
    assert rerank_score(f, retrieval_score=1.0, weights={"retrieval_score": 1.0, "semantic_similarity": 0.0, "entity_match": 0.0, "keyword_overlap": 0.0, "lexical_similarity": 0.0}) == 1.0


# ---- v0.5.3: answer-form intent match for TEXT intents, how-to query recall, fixed hybrid α


def test_answer_form_match_procedural_vs_table():
    from kotobacore.rag.features import answer_form_match

    proc = "### 8.3 起動しない\n- 起動直後に落ちる → `%APPDATA%\\mdediter\\config.json` を削除してリセット"
    table = "| 項目 | 値 |\n|---|---|\n| DB | PostgreSQL 17 |\n| ORM | Drizzle |"
    assert answer_form_match("how_to", proc) == 1.0
    assert answer_form_match("procedure", proc) == 1.0
    assert answer_form_match("how_to", table) == 0.0
    assert answer_form_match("reason", "移転したのは家賃が高かったためで、背景には人員増もある") == 1.0
    assert answer_form_match("lookup", proc) is None and answer_form_match("search_value", proc) is None


def test_rerank_features_intent_match_for_how_to_query():
    a = _a()
    q = a.analyze_query("mdediterが起動直後に落ちる時の対処")
    assert q.intent == "procedure"
    proc = ChunkView(text="### 8.3 起動しない\n- 起動直後に落ちる → config.json を削除してリセット")
    spec = ChunkView(text="| 項目 | 値 |\n| DB | PostgreSQL 17 |\n| ORM | Drizzle |")
    assert rerank_features(q, proc)["intent_match"] == 1.0
    assert rerank_features(q, spec)["intent_match"] == 0.0
    # typed answers keep the entity-based match
    q2 = a.analyze_query("東京支店の売上目標はいくら？")
    assert rerank_features(q2, ChunkView(text="売上目標は 3 億円", entity_types={"MONEY"}))["intent_match"] == 1.0


def test_query_intent_noun_phrase_how_to_and_trouble():
    from kotobacore.modules.intent import classify_query_intent

    assert classify_query_intent("pmk.plot-os.comのSSL証明書取得コマンド")[0] == "how_to"
    assert classify_query_intent("Sparkのenv変更後に必要な操作")[0] == "how_to"
    assert classify_query_intent("AIモジュールで特定プロバイダーを指定して思考生成する書き方")[0] == "how_to"
    assert classify_query_intent("newtodoのマスター鍵とDBダンプはどう保管する")[0] == "how_to"
    assert classify_query_intent("git pullがdesktop.iniエラーになる時の対処")[0] == "procedure"
    assert classify_query_intent("Invalid Client IDエラーの解決策")[0] == "procedure"
    assert classify_query_intent("労災の再発を防ぐための対策")[0] == "procedure"
    assert classify_query_intent("USBメモリなどの外部記憶媒体の使用ルール")[0] == "condition"
    # どう-phrases that are not how-to keep their own intent
    assert classify_query_intent("hilightの切り抜き動画はPR動画とどう違う")[0] == "compare"
    assert classify_query_intent("Apacheの設定順序を守らないとどうなる")[0] == "reason"
    assert classify_query_intent("犬はどうした？")[0] == "lookup"
    assert classify_query_intent("対応していますか") == ("yes_no", "BOOLEAN")


def test_chunker_keeps_code_block_with_its_lead_in_and_ignores_fenced_headings():
    """v0.5.4: a shell comment inside ``` is not a heading; the command stays with the sentence introducing it."""
    from kotobacore.core.syntax import split_paragraphs

    doc = chr(10).join([
        "### 切り替え手順", "", "providerを変更して高速再起動：", "", "```bash", "# キャッシュを削除して再生成", "ENV=prd make restart-ecs", "```",
        "", "### 次の節", "", "本文。",
    ])
    paras = [doc[b:e] for b, e in split_paragraphs(doc)]
    assert any(p.startswith("```bash") and p.endswith("```") for p in paras)  # the fence is one paragraph
    assert not any(p.startswith("# キャッシュ") for p in paras)
    d = _a().analyze_document(doc)
    cmd = next(c for c in d.document_chunks if "make restart-ecs" in c.text)
    assert "高速再起動" in cmd.text and cmd.heading_path == ["切り替え手順"]
    assert not any(c.heading_path and c.heading_path[-1].startswith("キャッシュ") for c in d.document_chunks)


def test_chunker_code_lead_in_context_when_split():
    lead = "providerを変更して高速再起動："
    body = chr(10).join(["# " + "x" * 60 for _ in range(6)])  # a long code block that cannot fit with the lead-in
    doc = chr(10).join(["### 手順", "", "あ" * 300 + "。", lead, "", "```bash", body, "make restart", "```"])
    d = _a().analyze_document(doc)
    cmd = next(c for c in d.document_chunks if "make restart" in c.text)
    assert lead not in cmd.text  # split away by the size limit …
    assert lead[:40] in cmd.context and cmd.text_with_context.startswith("手順")  # … but carried as context


def test_chunker_keeps_every_numbered_list_item():
    doc = chr(10).join(["## 進め方", "", "まずは：", "", "1. 50〜100発話を人手でラベル付け", "2. 迷ったケースをメモ", "3. ルール文を修正", "4. もう一度50発話", "", "### 迷ったら", "", "前後の流れで見る。"])
    d = _a().analyze_document(doc)
    joined = chr(10).join(c.text for c in d.document_chunks)
    for item in ("1. 50〜100発話を人手でラベル付け", "2. 迷ったケースをメモ", "3. ルール文を修正", "4. もう一度50発話"):
        assert item in joined
    assert not any("50〜100発話" in h for c in d.document_chunks for h in c.heading_path)  # list items are not section headings


def test_hybrid_alpha_is_fixed_and_anchors_are_diagnostic():
    from kotobacore.rag.features import HYBRID_ALPHA, hybrid_alpha, query_lexical_anchors

    a = _a()
    q_id = a.analyze_query("git pullがdesktop.iniエラーになる時の対処")
    q_plain = a.analyze_query("有給を取得するやり方は")
    assert query_lexical_anchors(q_id) == "identifier" and query_lexical_anchors(q_plain) == "none"
    assert hybrid_alpha(q_id) == hybrid_alpha(q_plain) == HYBRID_ALPHA == 0.3
