"""Tests for external dictionary loaders (NRC + Gemini)."""

from pathlib import Path

import pytest

from kotobacore.dictionary import (
    DictionaryBundle,
    EmotionEntry,
    EmotionExampleEntry,
    load_bundle_with_external,
    load_gemini_examples,
    load_gemini_examples_dir,
    load_nrc_lexicon,
    load_user_bundle,
)
from kotobacore.dictionary.external import (
    JP_TO_BASE_EMOTION,
    JP_TO_PLUTCHIK,
    NRC_TO_BASE_EMOTION,
    NRC_TO_PLUTCHIK,
)
from kotobacore.errors import DictionaryLoadError

# Paths relative to the repo. dic/ is a SIBLING of the KotobaCore package dir.
_DIC = Path(__file__).resolve().parents[2] / "dic"
NRC_FILE = _DIC / "Japanese-NRC-Emotion-Intensity-Lexicon-v1.txt"
GEMINI_FILE = _DIC / "Japanese-SNS-Emotion-Examples-v1.txt"

skip_if_no_dic = pytest.mark.skipif(
    not _DIC.exists(), reason="External dic/ folder not available in this checkout"
)

# KotobaCore emotion taxonomy (05_辞書設計書 §6.2 + anticipation)
VALID_BASE_EMOTIONS = {
    "joy", "admiration", "moved", "anger", "irritation", "sadness",
    "anxiety", "refusal", "agreement", "exaggeration", "anticipation", "mixed",
}


# ---------------------------------------------------------------------------
# Static mapping tables
# ---------------------------------------------------------------------------


def test_nrc_mapping_table_covers_8_plutchik():
    assert set(NRC_TO_BASE_EMOTION.keys()) == {
        "anger", "anticipation", "disgust", "fear", "joy", "sadness", "surprise", "trust",
    }
    assert set(NRC_TO_PLUTCHIK.values()) == set(NRC_TO_BASE_EMOTION.keys())


def test_jp_mapping_table_covers_common_labels():
    # At minimum we need to map 喜び 悲しみ 怒り (smallest gemini set)
    for label in ["喜び", "悲しみ", "怒り"]:
        assert label in JP_TO_BASE_EMOTION
        assert label in JP_TO_PLUTCHIK


# ---------------------------------------------------------------------------
# NRC loader
# ---------------------------------------------------------------------------


@skip_if_no_dic
def test_load_nrc_lexicon_returns_entries():
    if not NRC_FILE.exists():
        pytest.skip("NRC file not present")
    entries = load_nrc_lexicon(NRC_FILE, min_intensity=0.8)
    assert len(entries) > 0
    for e in entries:
        assert isinstance(e, EmotionEntry)
        assert e.surface
        assert 0.0 <= e.intensity <= 1.0
        assert e.base_emotion in VALID_BASE_EMOTIONS


@skip_if_no_dic
def test_load_nrc_lexicon_filters_low_intensity():
    if not NRC_FILE.exists():
        pytest.skip("NRC file not present")
    high = load_nrc_lexicon(NRC_FILE, min_intensity=0.9)
    low = load_nrc_lexicon(NRC_FILE, min_intensity=0.5)
    assert len(high) < len(low)


def test_load_nrc_lexicon_missing_file(tmp_path: Path):
    with pytest.raises(DictionaryLoadError):
        load_nrc_lexicon(tmp_path / "nope.txt")


def test_load_nrc_lexicon_synthetic(tmp_path: Path):
    p = tmp_path / "nrc.tsv"
    p.write_text(
        "English Word\tEmotion\tEmotion-Intensity-Score\tJapanese Word\n"
        "happy\tjoy\t0.85\t嬉しい\n"
        "angry\tanger\t0.95\t怒り\n"
        "noise\tjoy\t0.10\t低スコア\n"
        "untranslated\tjoy\t0.80\tuntranslated\n",
        encoding="utf-8",
    )
    entries = load_nrc_lexicon(p, min_intensity=0.5)
    surfaces = {e.surface for e in entries}
    assert "嬉しい" in surfaces
    assert "怒り" in surfaces
    assert "低スコア" not in surfaces  # filtered by intensity
    assert "untranslated" not in surfaces  # skip_identical_translation


# ---------------------------------------------------------------------------
# Gemini loader
# ---------------------------------------------------------------------------


@skip_if_no_dic
def test_load_gemini_examples_real_file():
    if not GEMINI_FILE.exists():
        pytest.skip("SNS examples file not present")
    # 統合済み Japanese-SNS-Emotion-Examples-v1.txt（多数の語 × 例文）
    entries = load_gemini_examples(GEMINI_FILE)
    assert len(entries) >= 30
    for e in entries:
        assert isinstance(e, EmotionExampleEntry)
        assert e.surface
        assert e.example
        assert e.example_id.startswith("GEM-")
        assert e.base_emotion in VALID_BASE_EMOTIONS


@skip_if_no_dic
def test_load_gemini_examples_single_file_loads_all():
    if not GEMINI_FILE.exists():
        pytest.skip("Japanese-SNS-Emotion-Examples-v1.txt not present")
    entries = load_gemini_examples(GEMINI_FILE)
    # Merged & deduplicated file should have many entries
    assert len(entries) >= 200
    # IDs should be globally unique
    ids = [e.example_id for e in entries]
    assert len(ids) == len(set(ids)), "duplicate example_ids"


def test_load_gemini_examples_synthetic(tmp_path: Path):
    p = tmp_path / "g.csv"
    p.write_text(
        "word,emotion,intensity,context,examples,emojis,combined_text\n"
        '最高,喜び,1.0,ctx,"今日最高、最高すぎ、最高の一日",✨,combined\n'
        '萎える,悲しみ,0.6,日常,"萎える、雨で萎えた",😩,combined\n',
        encoding="utf-8",
    )
    entries = load_gemini_examples(p, id_prefix="TST")
    # 3 + 2 = 5 example sentences
    assert len(entries) == 5
    assert entries[0].surface == "最高"
    assert entries[0].base_emotion == "joy"
    assert entries[0].plutchik_emotion == "joy"
    assert entries[0].polarity == "positive"
    assert entries[0].example_id.startswith("TST-r")
    assert "最高" in entries[0].example_id


def test_load_gemini_examples_skips_unknown_emotion(tmp_path: Path):
    p = tmp_path / "g.csv"
    p.write_text(
        "word,emotion,intensity,context,examples,emojis,combined_text\n"
        '謎,未定義感情,0.5,ctx,"例1、例2",,combined\n'
        '最高,喜び,0.9,ctx,"a、b",,c\n',
        encoding="utf-8",
    )
    entries = load_gemini_examples(p)
    surfaces = {e.surface for e in entries}
    assert "謎" not in surfaces  # unknown emotion → skipped
    assert "最高" in surfaces


def test_load_gemini_examples_missing_required_column(tmp_path: Path):
    p = tmp_path / "g.csv"
    p.write_text("word,emotion\n最高,喜び\n", encoding="utf-8")
    with pytest.raises(DictionaryLoadError):
        load_gemini_examples(p)


def test_load_gemini_examples_dir_missing_dir(tmp_path: Path):
    with pytest.raises(DictionaryLoadError):
        load_gemini_examples_dir(tmp_path / "nope")


# ---------------------------------------------------------------------------
# Bundle assembly
# ---------------------------------------------------------------------------


@skip_if_no_dic
def test_load_user_bundle_merges_internal_and_external():
    bundle = load_user_bundle()
    assert isinstance(bundle, DictionaryBundle)
    # Internal seed
    assert len(bundle.emotion) > 10  # seed emotion.csv has ~20 entries
    # External NRC entries go to external_emotion (kept separate)
    assert len(bundle.external_emotion) > 10
    assert len(bundle.emotion_examples) > 10


def test_load_bundle_with_external_internal_priority(tmp_path: Path):
    # Internal dict
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "emotion.csv").write_text(
        "surface,base_emotion,polarity,intensity,keep_as_unit\n"
        "最高,joy,positive,0.9,true\n",
        encoding="utf-8",
    )
    # External NRC
    nrc = tmp_path / "nrc.tsv"
    nrc.write_text(
        "English Word\tEmotion\tEmotion-Intensity-Score\tJapanese Word\n"
        "best\tjoy\t0.95\t最高\n"  # collides with internal
        "great\tjoy\t0.80\t素晴らしい\n",
        encoding="utf-8",
    )
    bundle = load_bundle_with_external(seed, nrc_path=nrc, internal_priority=True)

    # internal bundle.emotion: just 最高
    surfaces_internal = [e.surface for e in bundle.emotion]
    assert surfaces_internal == ["最高"]
    assert surfaces_internal.count("最高") == 1

    # external_emotion: 素晴らしい (最高 collision was dropped by internal_priority)
    surfaces_external = [e.surface for e in bundle.external_emotion]
    assert "素晴らしい" in surfaces_external
    assert "最高" not in surfaces_external
