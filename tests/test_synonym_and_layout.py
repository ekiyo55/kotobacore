"""synonym.csv (FR-003), Syntax negation helpers (FR-022) and the v0.3 layout."""

import re
from pathlib import Path

from kotobacore import Analyzer
from kotobacore.core.syntax import is_negated_surface, negation_after, split_clauses
from kotobacore.dictionary import load_default_bundle

PKG = Path(__file__).resolve().parents[1] / "kotobacore"


# ---------------------------------------------------------------- synonym


def test_synonym_dictionary_loads():
    bundle = load_default_bundle()
    assert len(bundle.synonym) >= 150
    m = bundle.synonym_map()
    assert m["ミーティング"] == "会議"
    assert m["会議"] == "会議"
    groups = bundle.synonym_groups()
    assert groups["会議"][0] == "会議"
    assert "ミーティング" in groups["会議"]


def test_synonym_words_are_unique():
    bundle = load_default_bundle()
    seen: set[str] = set()
    for e in bundle.synonym:
        for w in [e.canonical, *e.synonyms]:
            assert w not in seen, w
            seen.add(w)


def test_analyzer_synonym_api():
    a = Analyzer()
    assert a.canonical("デッドライン") == "締め切り"
    assert a.canonical("未登録語") == "未登録語"
    assert a.synonyms("ミーティング")[0] == "会議"
    assert a.synonyms("未登録語") == ["未登録語"]


def test_sentiment_dictionary_loads():
    bundle = load_default_bundle()
    assert len(bundle.sentiment) >= 150
    assert bundle.sentiment_by_surface()["いまいち"].polarity == "negative"


# ---------------------------------------------------------------- syntax negation


def test_negation_after_within_clause():
    text = "好きじゃないけど便利"
    clauses = split_clauses(text)
    assert negation_after(text, 2, clauses[0]) == len("じゃない")
    assert negation_after(text, 2, None) == len("じゃない")
    assert negation_after("便利", 2) == 0


def test_negation_does_not_cross_clause_boundary():
    text = "便利。ない"
    clauses = split_clauses(text)
    assert negation_after(text, 2, clauses[0]) == 0


def test_is_negated_surface():
    assert is_negated_surface("嬉しくない")
    assert is_negated_surface("楽しくなかった")
    assert not is_negated_surface("嬉しい")


# ---------------------------------------------------------------- layout rules (設計原則 4 / §3.3)


def _imports(path: Path) -> set[str]:
    src = path.read_text(encoding="utf-8")
    return set(re.findall(r"^(?:from|import)\s+(kotobacore[\w.]*)", src, flags=re.MULTILINE))


def test_core_does_not_import_modules_or_rag():
    for py in (PKG / "core").rglob("*.py"):
        for imp in _imports(py):
            assert not imp.startswith("kotobacore.modules"), (py, imp)
            assert not imp.startswith("kotobacore.rag"), (py, imp)


def test_modules_do_not_import_each_other():
    for py in (PKG / "modules").glob("*.py"):
        if py.name == "__init__.py":
            continue
        for imp in _imports(py):
            assert not imp.startswith("kotobacore.modules"), (py, imp)


def test_legacy_import_paths_still_work():
    from kotobacore.clause import split_clauses as legacy_split
    from kotobacore.emotion import detect_emotion  # noqa: F401
    from kotobacore.intent import classify_intent  # noqa: F401
    from kotobacore.normalizer import normalize  # noqa: F401
    from kotobacore.schema import Token  # noqa: F401
    from kotobacore.semantic import build_semantic_tokens, chunk  # noqa: F401
    from kotobacore.tokenizer.lattice import lattice_tokenize  # noqa: F401

    assert legacy_split is split_clauses
