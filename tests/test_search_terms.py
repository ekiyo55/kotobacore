"""Search index terms (v1.1, DD evaluation report §7-3)."""

from kotobacore import Analyzer

CSV = (
    "surface,type,normalized,aliases,priority,keep_as_unit\n"
    "連結EBITDA,TOPIC,連結EBITDA,Consolidated EBITDA,90,true\n"
    "役員賠償責任保険,TOPIC,役員賠償責任保険,D&O保険,90,true\n"
    "ネガティブ・プレッジ条項,TOPIC,ネガティブ・プレッジ条項,担保提供制限条項,95,true\n"
)


def _terms(a, text, kind=None):
    return [t.term for t in a.search_terms(text) if kind is None or t.kind == kind]


def test_compound_and_parts():
    a = Analyzer()
    terms = _terms(a, "損害賠償請求訴訟が提起された")
    assert terms[:5] == ["損害賠償請求訴訟", "損害", "賠償", "請求", "訴訟"]
    assert "が" not in terms and "た" not in terms  # function words dropped


def test_dictionary_word_parts_surface_and_lemma(tmp_path):
    p = tmp_path / "dd.csv"
    p.write_text(CSV, encoding="utf-8")
    a = Analyzer(user_dict_path=str(p))
    # a long dictionary word still yields its parts (EBITDA alone hits it)
    assert {"連結ebitda", "連結", "ebitda"} <= set(_terms(a, "連結EBITDAを算定した"))
    # alias → canonical name AND the written form
    t = _terms(a, "D&O保険を確認")
    assert "役員賠償責任保険" in t and "d&o保険" in t and "d&o" in t and "保険" in t
    # katakana compound split at the middle dot
    assert {"ネガティブ", "プレッジ", "条項"} <= set(_terms(a, "ネガティブ・プレッジ条項", "part"))
    # verbs: lemma, no fragments
    t = a.search_terms("残業代が払われていない")
    assert [x.term for x in t if x.kind == "lemma"] == ["払う"]
    assert not any(x.kind == "part" and x.token_id == 2 for x in t)


def test_offsets_point_into_original_text():
    a = Analyzer()
    s = "ＳＰＡの損害賠償請求訴訟"
    for x in a.search_terms(s, lower=False):
        assert x.end > x.begin
    part = next(x for x in a.search_terms(s) if x.term == "請求")
    assert s[part.begin:part.end] == "請求"


def test_options():
    a = Analyzer()
    assert _terms(a, "損害賠償請求訴訟") != [t.term for t in a.search_terms("損害賠償請求訴訟", parts=False)]
    assert [t.term for t in a.search_terms("損害賠償請求訴訟", parts=False)] == ["損害賠償請求訴訟"]
    assert [t.term for t in a.search_terms("EBITDA", lower=False)] == ["EBITDA"]


def test_cli_terms_plain():
    from typer.testing import CliRunner

    from kotobacore.cli.main import app

    r = CliRunner().invoke(app, ["terms", "損害賠償請求訴訟", "--plain"])
    assert r.exit_code == 0, r.output
    assert r.output.split() == ["損害賠償請求訴訟", "損害", "賠償", "請求", "訴訟"]
