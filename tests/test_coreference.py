"""v0.6.2: document-level entity coreference (FR-034) — clustering, alias mentions, anaphora."""

import datetime

from kotobacore import Analyzer
from kotobacore.core.coreference import COREF_TYPES, coreference_clusters, core_form


def _a():
    return Analyzer(reference_date=datetime.date(2026, 9, 8))


def _by_surface(entities, surface):
    return [e for e in entities if e.surface == surface]


def test_core_form():
    assert core_form("PERSON", "田中さん") == "田中" and core_form("PERSON", "田中部長") == "田中"
    assert core_form("ORGANIZATION", "株式会社山田商事") == "山田商事"
    assert core_form("LOCATION", "東京都") == "東京" and core_form("LOCATION", "大阪市") == "大阪市"  # 市 is not stripped (府 ≠ 市)
    assert core_form("PRODUCT", "MX-500") == "MX-500"


def test_person_honorific_and_full_name_cluster_with_alias_mentions():
    doc = "田中太郎さんが東京支店に着任した。\n田中さんは新しい方針を示した。\n田中の判断は早い。"
    d = _a().analyze_document(doc)
    persons = [e for e in d.entities if e.type == "PERSON"]
    canon = {e.canonical_id for e in persons}
    assert len(canon) == 1 and None not in canon, [(e.surface, e.canonical_id, e.source) for e in persons]
    rep = next(e for e in persons if e.id == e.canonical_id)
    assert rep.surface == "田中太郎さん"
    surfaces = {e.surface for e in persons}
    assert {"田中太郎さん", "田中さん", "田中"} <= surfaces
    bare = _by_surface(d.entities, "田中")[0]
    assert bare.source == "coreference" and bare.normalized in ("田中太郎さん", rep.normalized)
    assert "田中" in rep.aliases and "田中さん" in rep.aliases
    # the alias mention belongs to the sentence it occurs in
    sent = next(s for s in d.sentences if s.begin <= bare.begin < s.end)
    assert bare.id in sent.entity_ids


def test_organization_legal_form_and_abbreviation():
    doc = "株式会社北斗物流は2026年に新倉庫を開設した。\n北斗物流の売上は好調だ。\n北斗は来年も投資を続ける。\n同社の社長は佐藤氏だ。"
    d = _a().analyze_document(doc)
    orgs = [e for e in d.entities if e.type == "ORGANIZATION"]
    assert {e.canonical_id for e in orgs} == {orgs[0].canonical_id} and orgs[0].canonical_id is not None
    surfaces = {e.surface for e in orgs}
    assert {"株式会社北斗物流", "北斗物流", "北斗", "同社"} <= surfaces, surfaces
    same = _by_surface(d.entities, "同社")[0]
    assert same.source == "coreference" and same.normalized == "北斗物流"  # the representative's normalized form (legal prefix stripped by NER)
    clusters = coreference_clusters(d.entities)
    assert any(c[0].surface == "株式会社北斗物流" and len(c) >= 4 for c in clusters)


def test_unrelated_entities_stay_separate():
    doc = "田中さんと鈴木さんが会った。\n鈴木部長は大阪支社にいる。\n東京都と大阪府の両方で開催する。"
    d = _a().analyze_document(doc)
    tanaka = _by_surface(d.entities, "田中さん")[0]
    suzuki = _by_surface(d.entities, "鈴木さん")[0]
    assert tanaka.canonical_id != suzuki.canonical_id
    assert _by_surface(d.entities, "鈴木部長")[0].canonical_id == suzuki.canonical_id
    tokyo = [e for e in d.entities if e.surface in ("東京都", "東京")]
    osaka = [e for e in d.entities if e.surface in ("大阪府", "大阪")]
    assert tokyo and osaka and tokyo[0].canonical_id != osaka[0].canonical_id


def test_dates_and_amounts_are_not_clustered_and_single_sentence_unchanged():
    d = _a().analyze_document("売上は3億円で、2026年4月1日に発表した。")
    for e in d.entities:
        if e.type not in COREF_TYPES:
            assert e.canonical_id is None and e.aliases == []
    s = _a().analyze("田中さんが来た。")
    assert all(e.canonical_id is None for e in s.entities)  # analyze() = one sentence, no document pass


def test_chunks_see_alias_mentions_through_normalized_form():
    doc = "# 北斗物流の概要\n\n北斗物流は札幌の運送会社だ。\n\n## 投資\n\n北斗は2027年に新倉庫を建てる。"
    d = _a().analyze_document(doc)
    by_id = {e.id: e for e in d.entities}
    invest = next(c for c in d.document_chunks if "新倉庫" in c.text)
    norms = {by_id[i].normalized for i in invest.entity_ids if i in by_id}
    assert "北斗物流" in norms  # the 北斗 mention carries the canonical name
