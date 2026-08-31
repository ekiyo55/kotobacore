"""Tests for dictionary loader per 07_テスト仕様 §15."""

import csv
from pathlib import Path

import pytest

from kotobacore.dictionary import (
    DictionaryBundle,
    EmotionEntry,
    EmotionExampleEntry,
    EntityEntry,
    IntentRule,
    SlangEntry,
    StopwordEntry,
    load_default_bundle,
    load_dictionary_bundle,
)
from kotobacore.dictionary.loader import (
    load_emotion,
    load_emotion_examples,
    load_entity,
    load_intent_rules,
    load_slang,
    load_stopwords,
)
from kotobacore.errors import DictionaryLoadError


def test_dict_001_slang_loads():
    # DICT-001: slang.csv loads with required columns
    bundle = load_default_bundle()
    assert len(bundle.slang) > 0
    s = bundle.slang[0]
    assert isinstance(s, SlangEntry)
    assert s.surface
    assert 0.0 <= s.intensity <= 1.0


def test_dict_002_emotion_intensity_in_range():
    # DICT-002: emotion.csv intensity ∈ [0.0, 1.0]
    bundle = load_default_bundle()
    assert len(bundle.emotion) > 0
    for e in bundle.emotion:
        assert isinstance(e, EmotionEntry)
        assert 0.0 <= e.intensity <= 1.0


def test_dict_003_entity_priority_is_int():
    # DICT-003: entity.csv priority is int
    bundle = load_default_bundle()
    assert len(bundle.entity) > 0
    for e in bundle.entity:
        assert isinstance(e, EntityEntry)
        assert isinstance(e.priority, int)


def test_dict_004_intent_score_in_range():
    # DICT-004: intent_rules.csv score ∈ [0.0, 1.0]
    bundle = load_default_bundle()
    assert len(bundle.intent_rules) > 0
    for r in bundle.intent_rules:
        assert isinstance(r, IntentRule)
        assert 0.0 <= r.score <= 1.0


def test_dict_005_emotion_examples_has_example_id():
    # DICT-005: emotion_examples.csv has example_id
    bundle = load_default_bundle()
    assert len(bundle.emotion_examples) > 0
    for e in bundle.emotion_examples:
        assert isinstance(e, EmotionExampleEntry)
        assert e.example_id


def test_stopwords_load():
    bundle = load_default_bundle()
    assert len(bundle.stopwords) > 0
    for s in bundle.stopwords:
        assert isinstance(s, StopwordEntry)
    # particles must be in stopwords
    surfaces = {s.surface for s in bundle.stopwords}
    assert {"の", "は", "が"}.issubset(surfaces)


def test_bundle_lookup_helpers():
    bundle = load_default_bundle()
    slang_map = bundle.slang_by_surface()
    assert "草" in slang_map
    stopwords = bundle.stopword_set()
    assert "の" in stopwords
    keep_units = bundle.keep_as_unit_surfaces()
    assert "しぬw" in keep_units


def test_entity_aliases_parsed():
    bundle = load_default_bundle()
    openai = next(e for e in bundle.entity if e.surface == "OpenAI API")
    assert "OpenAIAPI" in openai.aliases
    assert "OpenAI api" in openai.aliases


def test_intensity_out_of_range_raises(tmp_path: Path):
    csv_path = tmp_path / "emotion.csv"
    csv_path.write_text(
        "surface,base_emotion,polarity,intensity,keep_as_unit\nbad,joy,positive,1.5,false\n",
        encoding="utf-8",
    )
    with pytest.raises(DictionaryLoadError):
        load_emotion(csv_path)


def test_missing_column_raises(tmp_path: Path):
    csv_path = tmp_path / "emotion.csv"
    # 'keep_as_unit' missing
    csv_path.write_text(
        "surface,base_emotion,polarity,intensity\nbad,joy,positive,0.5\n",
        encoding="utf-8",
    )
    with pytest.raises(DictionaryLoadError):
        load_emotion(csv_path)


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(DictionaryLoadError):
        load_emotion(tmp_path / "nonexistent.csv")


def test_load_dictionary_bundle_from_custom_dir(tmp_path: Path):
    # Create minimal slang.csv only
    (tmp_path / "slang.csv").write_text(
        "surface,normalized,meaning,emotion,category,intensity,keep_as_unit\n"
        "test,テスト,test,joy,sns,0.5,true\n",
        encoding="utf-8",
    )
    bundle = load_dictionary_bundle(tmp_path)
    assert len(bundle.slang) == 1
    # Other dicts should be empty (files don't exist)
    assert bundle.emotion == []
    assert bundle.entity == []


def test_missing_directory_raises(tmp_path: Path):
    with pytest.raises(DictionaryLoadError):
        load_dictionary_bundle(tmp_path / "doesnotexist")


def test_intent_rules_have_priority():
    bundle = load_default_bundle()
    for r in bundle.intent_rules:
        assert isinstance(r.priority, int)
        assert r.priority >= 0


# ---------------------------------------------------------------------------
# v0.2.7: かな表記ゆれの自動吸収 (カタカナ⇔ひらがな variant)
# ---------------------------------------------------------------------------


def test_kana_variants_expanded_for_pure_kana_surfaces():
    bundle = load_default_bundle()
    emotion_surfaces = {e.surface for e in bundle.emotion}
    # カタカナ収録語のひらがな variant が自動登録される
    assert "ワクワク" in emotion_surfaces
    assert "わくわく" in emotion_surfaces
    assert "いらいら" in emotion_surfaces
    # variant は元エントリと同じ感情を持つ
    by_surface = bundle.emotion_by_surface()
    assert by_surface["わくわく"].base_emotion == by_surface["ワクワク"].base_emotion


def test_kana_variants_skip_short_surfaces():
    # 2文字スラング (キタ 等) は folding しない — 来た→きた と衝突するため
    bundle = load_default_bundle()
    slang_surfaces = {s.surface for s in bundle.slang}
    assert "キタ" in slang_surfaces
    assert "きた" not in slang_surfaces
