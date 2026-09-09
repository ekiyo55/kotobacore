"""v0.6.4: component versions / compatibility matrix (§8, NFR-003) and the dictionary manifest."""

import json

from typer.testing import CliRunner

import kotobacore
from kotobacore import Analyzer
from kotobacore.cli.main import app
from kotobacore.core.ir import SCHEMA_VERSION
from kotobacore.core.token import TOKENIZER_VERSION
from kotobacore.versions import (
    MODULE_VERSIONS,
    compatibility_matrix_markdown,
    component_versions,
    dictionary_manifest,
    dictionary_row_counts,
)


def test_dictionary_manifest_matches_bundled_csvs():
    """Every bundled CSV is in the manifest and its row count is current — editing a dictionary means bumping its version AND rows."""
    manifest = dictionary_manifest()
    actual = dictionary_row_counts()
    assert manifest["set_version"] != "unknown"
    assert set(manifest["files"]) == set(actual), (set(manifest["files"]) ^ set(actual))
    for name, rows in actual.items():
        meta = manifest["files"][name]
        assert meta["rows"] == rows, f"{name}: manifest rows {meta['rows']} != actual {rows} — bump version and rows in resources/dict/versions.json"
        assert meta["version"]


def test_component_versions_complete():
    v = component_versions()
    assert v["kotobacore"] == kotobacore.__version__ and v["schema"] == SCHEMA_VERSION and v["tokenizer"] == TOKENIZER_VERSION
    assert set(v["modules"]) == {"intent", "emotion", "sentiment", "topic"} == set(MODULE_VERSIONS)
    assert v["vocab_format"].startswith("kotobacore-vocab-") and v["legacy_imports"]["removed_in"] == "1.1"
    assert "okurigana.csv" in v["dictionaries"] and "emotion.csv" in v["dictionaries"]
    md = compatibility_matrix_markdown()
    assert md.startswith("| 対象 | 版 | 互換ポリシー |") and "Tokenizer (Karuizawa)" in md and TOKENIZER_VERSION in md


def test_meta_carries_component_versions():
    a = Analyzer()
    for r in (a.analyze("最高"), a.analyze_document("最高。\n\n最悪。")):
        assert r.meta.components["tokenizer"] == TOKENIZER_VERSION
        assert r.meta.components["dictionary_set"] == dictionary_manifest()["set_version"]
        assert r.meta.components["modules"]["emotion"] == MODULE_VERSIONS["emotion"]
    payload = json.loads(a.analyze("最高").to_json())
    assert payload["meta"]["components"]["tokenizer"] == TOKENIZER_VERSION


def test_cli_version_all_and_matrix():
    runner = CliRunner()
    r = runner.invoke(app, ["version", "--all"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["kotobacore"] == kotobacore.__version__ and "dictionaries" in data
    r = runner.invoke(app, ["version", "--matrix"])
    assert r.exit_code == 0 and "| 対象 | 版 | 互換ポリシー |" in r.output
    r = runner.invoke(app, ["version"])
    assert r.exit_code == 0 and kotobacore.__version__ in r.output
