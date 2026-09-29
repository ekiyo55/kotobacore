"""User dictionary (user_dict_path / --dict) and canonical entity names (v1.1).

Evaluation report (DD RAG, 2026-09-29) §6/§7-1/§7-2: user_dict_path was accepted
but ignored, and entity aliases kept their own surface in Token.normalized.
"""

import pytest

from kotobacore import Analyzer
from kotobacore.dictionary import apply_user_dictionary, load_default_bundle
from kotobacore.errors import DictionaryLoadError

CSV = (
    "surface,type,normalized,aliases,priority,keep_as_unit\n"
    "役員賠償責任保険,TOPIC,役員賠償責任保険,D&O保険|D&O Insurance,95,true\n"
    "取得原価の配分,TOPIC,取得原価の配分,PPA|パーチェス・プライス・アロケーション,90,true\n"
)


def _surfaces(a, text):
    return [t.surface for t in a.tokenize(text)]


def test_user_dict_file_is_applied(tmp_path):
    p = tmp_path / "dd.csv"
    p.write_text(CSV, encoding="utf-8")
    plain = Analyzer()
    user = Analyzer(user_dict_path=str(p))
    assert _surfaces(plain, "D&O保険に加入する")[0] != "D&O保険"
    toks = user.tokenize("D&O保険に加入する")
    assert toks[0].surface == "D&O保険"
    # alias → canonical name in normalized
    assert toks[0].normalized == "役員賠償責任保険"
    assert user.tokenize("PPAの結果")[0].normalized == "取得原価の配分"
    # the Entity layer sees the user term too
    ents = user.analyze("D&O保険に加入する").entities
    hit = [e for e in ents if e.surface == "D&O保険"]
    assert hit and hit[0].normalized == "役員賠償責任保険"


def test_user_dict_minimal_columns(tmp_path):
    p = tmp_path / "terms.csv"
    p.write_text("surface\n源泉徴収漏れ\n", encoding="utf-8")
    a = Analyzer(user_dict_path=str(p))
    t = a.tokenize("源泉徴収漏れがある")[0]
    assert t.surface == "源泉徴収漏れ" and t.normalized == "源泉徴収漏れ"


def test_user_dict_directory_and_precedence(tmp_path):
    (tmp_path / "entity.csv").write_text(
        "surface,type,normalized,aliases,priority,keep_as_unit\n東京都,ORG,東京都庁,,100,true\n",
        encoding="utf-8",
    )
    base = load_default_bundle()
    merged = apply_user_dictionary(base, tmp_path)
    assert merged is not base
    assert merged.entity_by_surface()["東京都"].type == "ORG"
    # bundled bundle untouched, duplicate surface dropped
    assert base.entity_by_surface()["東京都"].type != "ORG"
    assert sum(1 for e in merged.entity if e.surface == "東京都") == 1


def test_user_dict_missing_path_raises(tmp_path):
    with pytest.raises(DictionaryLoadError):
        Analyzer(user_dict_path=str(tmp_path / "nope.csv")).tokenize("テスト")


def test_bundled_entity_alias_normalized():
    # bundled entity.csv aliases also carry the canonical name
    b = load_default_bundle()
    m = b.entity_normalized_map()
    assert m and all(k != v for k, v in m.items())


def test_cli_tokenize_accepts_dict(tmp_path):
    import json

    from typer.testing import CliRunner

    from kotobacore.cli.main import app

    p = tmp_path / "dd.csv"
    p.write_text(CSV, encoding="utf-8")
    r = CliRunner().invoke(app, ["tokenize", "D&O保険に加入する", "--dict", str(p)])
    assert r.exit_code == 0, r.output
    toks = json.loads(r.output)
    assert toks[0]["surface"] == "D&O保険"
    assert toks[0]["normalized"] == "役員賠償責任保険"
