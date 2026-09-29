"""Config file and bundled domain dictionaries (v1.1)."""

import pytest

from kotobacore import Analyzer
from kotobacore.config import domain_dictionaries, load_config, resolve_dictionary
from kotobacore.errors import DictionaryLoadError


def _surfaces(a, text):
    return [t.surface for t in a.tokenize(text)]


def test_builtin_dd_dictionary():
    assert "dd" in domain_dictionaries()
    a = Analyzer(use_config=False, user_dict_path="builtin:dd")
    toks = a.tokenize("D&O保険とPPAの範囲")
    assert toks[0].surface == "D&O保険" and toks[0].normalized == "役員賠償責任保険"
    assert any(t.normalized == "取得原価の配分" for t in toks)
    with pytest.raises(DictionaryLoadError):
        resolve_dictionary("builtin:nope")


def test_config_file_lists_dictionaries(tmp_path, monkeypatch):
    (tmp_path / "dict").mkdir()
    (tmp_path / "dict" / "mine.csv").write_text("surface,aliases\nみなと精機株式会社,MNT\n", encoding="utf-8")
    (tmp_path / "kotobacore.yaml").write_text("dictionaries:\n  - ./dict/mine.csv\n  - builtin:dd\n", encoding="utf-8")
    monkeypatch.delenv("KOTOBACORE_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)  # ./kotobacore.yaml is found automatically
    a = Analyzer()
    assert a.config.path.name == "kotobacore.yaml"
    assert len(a.dictionary_paths()) == 2
    toks = a.tokenize("MNT向けのD&O保険")
    assert toks[0].normalized == "みなと精機株式会社"
    assert toks[-1].normalized == "役員賠償責任保険"
    # use_config=False ignores it
    assert Analyzer(use_config=False).tokenize("MNT向け")[0].normalized == "MNT"


def test_config_precedence_and_env(tmp_path, monkeypatch):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text("surface,type\n山田商事,ORG_FIRST\n", encoding="utf-8")
    second.write_text("surface,type\n山田商事,ORG_SECOND\n", encoding="utf-8")
    cfg = tmp_path / "conf.yaml"
    cfg.write_text(f"dictionaries:\n  - {first.name}\n  - {second.name}\n", encoding="utf-8")
    monkeypatch.setenv("KOTOBACORE_CONFIG", str(cfg))
    a = Analyzer()
    assert a._get_bundle().entity_by_surface()["山田商事"].type == "ORG_FIRST"  # earlier entry wins
    # an explicit user_dict_path beats the config file
    b = Analyzer(user_dict_path=str(second))
    assert b._get_bundle().entity_by_surface()["山田商事"].type == "ORG_SECOND"
    monkeypatch.setenv("KOTOBACORE_CONFIG", "none")
    assert load_config().path is None


def test_config_errors(tmp_path, monkeypatch):
    monkeypatch.delenv("KOTOBACORE_CONFIG", raising=False)
    with pytest.raises(DictionaryLoadError):
        Analyzer(config_path=str(tmp_path / "missing.yaml"))
    bad = tmp_path / "bad.yaml"
    bad.write_text("dictionaries: {a: 1}\n", encoding="utf-8")
    with pytest.raises(DictionaryLoadError):
        Analyzer(config_path=str(bad))


def test_cli_config_command(tmp_path, monkeypatch):
    import json

    from typer.testing import CliRunner

    from kotobacore.cli.main import app

    (tmp_path / "kotobacore.yaml").write_text("dictionaries:\n  - builtin:dd\n", encoding="utf-8")
    monkeypatch.delenv("KOTOBACORE_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(app, ["config"])
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["config"].endswith("kotobacore.yaml") and out["dictionaries"][0]["entries"] >= 400
    assert "dd" in out["builtin"]
