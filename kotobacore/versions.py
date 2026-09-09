"""Component versions and the compatibility matrix (要件定義書 §8 / NFR-003).

KotobaCore is versioned per component, independently:

- core (this package)             ``kotobacore.__version__``        SemVer; 0.x minors may break
- IR schema                       ``core.ir.SCHEMA_VERSION``       field additions are compatible, removals / type changes are major
- tokenizer (Karuizawa)           ``core.token.TOKENIZER_VERSION`` bumped whenever segmentation output changes
- dictionaries (per CSV)          ``resources/dict/versions.json`` additions = patch, meaning changes = minor;
                                  the manifest also records row counts so a forgotten bump fails ``tests/test_versions.py``
- modules                         :data:`MODULE_VERSIONS`           independent per module (intent / emotion / sentiment / topic)
- vocabulary file format          ``vocab.VOCAB_FORMAT_VERSION``   append-only within a major
- HTTP API                        ``api.server.API_VERSION``
- legacy import paths             deprecated since ``_compat.DEPRECATED_SINCE``, removed in ``_compat.REMOVED_IN``

``component_versions()`` returns everything as one dict (what ``kotobacore version --all``
prints and what ``MetaInfo.components`` carries); ``compatibility_matrix_markdown()``
renders the README table.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from kotobacore._compat import DEPRECATED_SINCE, REMOVED_IN
from kotobacore._version import __version__
from kotobacore.core.ir import SCHEMA_VERSION
from kotobacore.core.token import TOKENIZER_VERSION

# Unified to 1.0 at KotobaCore 1.0.0 (2026-09-09). Pre-1.0 lineage: intent 1.2 (query intents 0.5.2,
# noun-phrase how-to 0.5.3, inform / share_experience 0.6.5), emotion 1.1 (holder / about 0.4.0,
# surprise / trust / disgust 0.6.5), sentiment 1.1 (split 0.3.0, overlay 0.5.1), topic 1.0 (0.5.0).
MODULE_VERSIONS: dict[str, str] = {"intent": "1.0", "emotion": "1.0", "sentiment": "1.0", "topic": "1.0"}
DICT_DIR = Path(__file__).resolve().parent / "resources" / "dict"
MANIFEST = DICT_DIR / "versions.json"


def dictionary_manifest() -> dict:
    """The dictionary manifest: {"set_version": …, "files": {name: {"version", "rows", "note"}}}."""
    if not MANIFEST.exists():
        return {"set_version": "unknown", "files": {}}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def dictionary_row_counts(dict_dir: Path = DICT_DIR) -> dict[str, int]:
    """Actual data-row counts of the bundled CSV dictionaries (header excluded)."""
    out: dict[str, int] = {}
    for path in sorted(dict_dir.glob("*.csv")):
        with path.open("r", encoding="utf-8", newline="") as f:
            out[path.name] = sum(1 for _ in csv.DictReader(f))
    return out


def component_versions(*, with_dictionaries: bool = True) -> dict:
    manifest = dictionary_manifest()
    info: dict = {
        "kotobacore": __version__,
        "schema": SCHEMA_VERSION,
        "tokenizer": TOKENIZER_VERSION,
        "dictionary_set": manifest.get("set_version", "unknown"),
        "modules": dict(MODULE_VERSIONS),
        "vocab_format": _vocab_format_version(),
        "api": _api_version(),
        "legacy_imports": {"deprecated_since": DEPRECATED_SINCE, "removed_in": REMOVED_IN},
    }
    if with_dictionaries:
        info["dictionaries"] = {name: meta.get("version", "?") for name, meta in manifest.get("files", {}).items()}
    return info


def _vocab_format_version() -> str:
    from kotobacore.vocab.build import (
        VOCAB_FORMAT_VERSION,
    )

    return VOCAB_FORMAT_VERSION


def _api_version() -> str:
    try:
        from kotobacore.api.server import API_VERSION
    except ImportError:
        return "1.0 (fastapi not installed)"
    return API_VERSION


def compatibility_matrix_markdown() -> str:
    v = component_versions()
    rows = [
        ("KotobaCore 本体", v["kotobacore"], "SemVer。0.x はマイナーで破壊変更可、1.0 以降はメジャーのみ"),
        ("IR Schema", v["schema"], "フィールド追加は後方互換、削除・型変更はメジャー"),
        ("Tokenizer (Karuizawa)", v["tokenizer"], "分割結果が変わる変更で上げる"),
        ("辞書セット", v["dictionary_set"], "追加はパッチ、意味変更はマイナー。各 CSV の版は resources/dict/versions.json"),
        ("Intent module", v["modules"]["intent"], "モジュール単位で独立"),
        ("Emotion module", v["modules"]["emotion"], "モジュール単位で独立"),
        ("Sentiment module", v["modules"]["sentiment"], "モジュール単位で独立"),
        ("Topic module", v["modules"]["topic"], "モジュール単位で独立"),
        ("Vocabulary format", v["vocab_format"], "同一メジャー内は追記のみ"),
        ("HTTP API", str(v["api"]), "パス・レスポンス形の破壊変更でメジャー"),
        ("旧 import パス", f"deprecated {v['legacy_imports']['deprecated_since']} → removed {v['legacy_imports']['removed_in']}",
         "kotobacore.schema / normalizer / tokenizer / semantic / emotion / intent / clause / matching"),
    ]
    lines = ["| 対象 | 版 | 互換ポリシー |", "|---|---|---|"]
    lines += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    return "\n".join(lines) + "\n"
