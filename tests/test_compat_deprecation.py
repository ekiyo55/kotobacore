"""v0.6.4: the pre-v0.3 import paths still work but warn (deprecated 0.6.4, removed 1.1 — 要件定義書 §3.2)."""

import importlib
import sys
import warnings

import pytest

from kotobacore._compat import KotobaCoreDeprecationWarning

# (old module, new module, attribute that must resolve to the same object)
CASES = [
    ("kotobacore.schema", "kotobacore.core.ir", "Token"),
    ("kotobacore.clause", "kotobacore.core.syntax", "split_clauses"),
    ("kotobacore.matching", "kotobacore.core.matching", "SurfaceMatcher"),
    ("kotobacore.normalizer", "kotobacore.core.text", "normalize"),
    ("kotobacore.normalizer.unicode_normalizer", "kotobacore.core.text", "normalize"),
    ("kotobacore.tokenizer", "kotobacore.core.token", "KaruizawaBackend"),
    ("kotobacore.tokenizer.lattice", "kotobacore.core.token.lattice", "lattice_tokenize"),
    ("kotobacore.tokenizer.token_normalizer", "kotobacore.core.token.token_normalizer", "merge_keep_as_unit"),
    ("kotobacore.semantic", "kotobacore.core.chunker", "chunk"),
    ("kotobacore.semantic.builder", "kotobacore.core.entity", "build_semantic_tokens"),
    ("kotobacore.emotion", "kotobacore.modules.emotion", "detect_emotion"),
    ("kotobacore.emotion.detector", "kotobacore.modules.emotion", "detect_emotion"),
    ("kotobacore.intent", "kotobacore.modules.intent", "classify_intent"),
    ("kotobacore.intent.classifier", "kotobacore.modules.intent", "classify_intent"),
]


def _fresh_import(name: str):
    sys.modules.pop(name, None)
    return importlib.import_module(name)


@pytest.mark.parametrize("old, new, attr", CASES)
def test_old_path_warns_and_resolves(old, new, attr):
    with pytest.warns(KotobaCoreDeprecationWarning, match="deprecated since KotobaCore 0.6.4"):
        legacy = _fresh_import(old)
    current = importlib.import_module(new)
    assert getattr(legacy, attr) is getattr(current, attr)


def test_new_paths_do_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error", KotobaCoreDeprecationWarning)
        for name in ("kotobacore.core.ir", "kotobacore.core.token", "kotobacore.modules.emotion", "kotobacore.rag", "kotobacore.compat"):
            _fresh_import(name)


def test_karuizawa_compat_api_is_not_deprecated():
    """FR-093: kotobacore.compat (Karuizawa 互換 API) stays supported."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", KotobaCoreDeprecationWarning)
        mod = _fresh_import("kotobacore.compat")
    assert hasattr(mod, "KaruizawaTokenizer")
