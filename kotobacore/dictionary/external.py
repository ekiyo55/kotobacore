"""External dictionary loaders.

Supports two source formats:

1. NRC Japanese Emotion-Intensity Lexicon (TSV)
   - Columns: ``English Word \t Emotion \t Emotion-Intensity-Score \t Japanese Word``
   - 8 Plutchik emotions: anger / anticipation / disgust / fear / joy / sadness / surprise / trust
   - Source: National Research Council Canada — NRC Word-Emotion Association Lexicon (Japanese)

2. Gemini-formatted CSV (per row: 1 word + multiple example sentences)
   - Columns: ``word,emotion,intensity,context,examples,emojis,combined_text``
   - examples are 「、」 (Japanese full-width comma) separated
   - emotion is Japanese (喜び / 悲しみ / 怒り / 恐れ / 驚き ...)

Each NRC row → ``EmotionEntry``. Each Gemini example sentence → ``EmotionExampleEntry``.
"""

from __future__ import annotations

import csv
from pathlib import Path

from kotobacore.dictionary.loader import (
    DictionaryBundle,
    EmotionEntry,
    EmotionExampleEntry,
    load_dictionary_bundle,
)
from kotobacore.errors import DictionaryLoadError

# ---------------------------------------------------------------------------
# Mapping tables
# ---------------------------------------------------------------------------

# NRC emotion → KotobaCore base_emotion (per 05_辞書設計書 §6.2)
NRC_TO_BASE_EMOTION: dict[str, str] = {
    "anger": "anger",
    "anticipation": "anticipation",
    "disgust": "irritation",
    "fear": "anxiety",
    "joy": "joy",
    "sadness": "sadness",
    "surprise": "exaggeration",
    "trust": "admiration",
}

# NRC emotion → Plutchik (one-to-one)
NRC_TO_PLUTCHIK: dict[str, str] = {
    "anger": "anger",
    "anticipation": "anticipation",
    "disgust": "disgust",
    "fear": "fear",
    "joy": "joy",
    "sadness": "sadness",
    "surprise": "surprise",
    "trust": "trust",
}

# NRC emotion → polarity
NRC_TO_POLARITY: dict[str, str] = {
    "anger": "negative",
    "anticipation": "positive",
    "disgust": "negative",
    "fear": "negative",
    "joy": "positive",
    "sadness": "negative",
    "surprise": "mixed",
    "trust": "positive",
}

# Japanese emotion label → KotobaCore base_emotion
JP_TO_BASE_EMOTION: dict[str, str] = {
    "喜び": "joy",
    "悲しみ": "sadness",
    "怒り": "anger",
    "恐れ": "anxiety",
    "信頼": "admiration",
    "嫌悪": "irritation",
    "驚き": "exaggeration",
    "期待": "anticipation",
    "感動": "moved",
    "拒否": "refusal",
    "同意": "agreement",
}

JP_TO_PLUTCHIK: dict[str, str] = {
    "喜び": "joy",
    "悲しみ": "sadness",
    "怒り": "anger",
    "恐れ": "fear",
    "信頼": "trust",
    "嫌悪": "disgust",
    "驚き": "surprise",
    "期待": "anticipation",
    "感動": "joy",
    "拒否": "disgust",
    "同意": "trust",
}

JP_TO_POLARITY: dict[str, str] = {
    "喜び": "positive",
    "悲しみ": "negative",
    "怒り": "negative",
    "恐れ": "negative",
    "信頼": "positive",
    "嫌悪": "negative",
    "驚き": "mixed",
    "期待": "positive",
    "感動": "positive",
    "拒否": "negative",
    "同意": "positive",
}


# ---------------------------------------------------------------------------
# NRC lexicon loader
# ---------------------------------------------------------------------------


def load_nrc_lexicon(
    path: Path | str,
    *,
    min_intensity: float = 0.5,
    skip_identical_translation: bool = True,
) -> list[EmotionEntry]:
    """Load NRC Japanese Emotion-Intensity Lexicon (TSV) into ``EmotionEntry`` list.

    Parameters
    ----------
    path:
        Path to ``Japanese-NRC-Emotion-Intensity-Lexicon-v1.txt`` (TSV).
    min_intensity:
        Filter threshold to reduce low-signal rows. Default 0.5.
    skip_identical_translation:
        When the Japanese column equals the English source (e.g., ``gofuckyourself``)
        the row is likely an untranslated noise entry and is dropped.

    Notes
    -----
    NRC has 8 emotions (Plutchik). KotobaCore's base taxonomy lacks
    ``anticipation`` — it is folded into ``joy``. Plutchik is preserved
    one-to-one for downstream use.
    """
    p = Path(path)
    if not p.exists():
        raise DictionaryLoadError(f"NRC lexicon not found: {p}")

    entries: list[EmotionEntry] = []
    with p.open("r", encoding="utf-8") as f:
        header = f.readline()  # skip
        if not header.lower().startswith("english"):
            raise DictionaryLoadError(f"Unexpected NRC header: {header!r}")

        for lineno, raw in enumerate(f, start=2):
            line = raw.rstrip("\r\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            eng, emo, score_str, jp = parts[0], parts[1], parts[2], parts[3].strip()

            try:
                score = float(score_str)
            except ValueError:
                continue
            if score < min_intensity:
                continue

            base = NRC_TO_BASE_EMOTION.get(emo)
            if base is None:
                continue

            if not jp:
                continue
            if skip_identical_translation and jp == eng:
                continue

            entries.append(
                EmotionEntry(
                    surface=jp,
                    base_emotion=base,
                    polarity=NRC_TO_POLARITY.get(emo, "neutral"),
                    intensity=min(max(score, 0.0), 1.0),
                    keep_as_unit=False,
                )
            )
    return entries


# ---------------------------------------------------------------------------
# Gemini-format CSV loader
# ---------------------------------------------------------------------------


def load_gemini_examples(
    path: Path | str,
    *,
    id_prefix: str | None = None,
) -> list[EmotionExampleEntry]:
    """Load one Gemini-format CSV → list of ``EmotionExampleEntry``.

    The ``examples`` column is split on 「、」 (full-width comma). One sentence
    becomes one ``EmotionExampleEntry``. ``example_id`` is auto-assigned as
    ``{id_prefix or 'GEM'}-{surface}-{NN}``.

    Unknown emotion labels are skipped (with no exception, so a corrupt row
    does not block the whole file).
    """
    p = Path(path)
    if not p.exists():
        raise DictionaryLoadError(f"Gemini examples file not found: {p}")

    prefix = id_prefix or "GEM"
    entries: list[EmotionExampleEntry] = []

    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"word", "emotion", "intensity", "examples"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise DictionaryLoadError(
                f"{p.name}: missing required columns (need {sorted(required)})"
            )

        for row_idx, row in enumerate(reader, start=1):
            word = (row.get("word") or "").strip()
            jp_emo = (row.get("emotion") or "").strip()
            examples_raw = (row.get("examples") or "").strip()

            if not word or not jp_emo or not examples_raw:
                continue

            base = JP_TO_BASE_EMOTION.get(jp_emo)
            if base is None:
                # Unknown emotion label → skip the row (don't pollute taxonomy)
                continue
            plutchik = JP_TO_PLUTCHIK.get(jp_emo, base)
            polarity = JP_TO_POLARITY.get(jp_emo, "neutral")

            try:
                intensity = float(row["intensity"])
            except (ValueError, KeyError):
                continue
            intensity = min(max(intensity, 0.0), 1.0)

            # Strip quotes if csv.DictReader leaves them; also split on 「、」.
            sentences = [s.strip() for s in examples_raw.split("、") if s.strip()]
            for idx, sentence in enumerate(sentences, start=1):
                entries.append(
                    EmotionExampleEntry(
                        surface=word,
                        base_emotion=base,
                        plutchik_emotion=plutchik,
                        polarity=polarity,
                        intensity=intensity,
                        example=sentence,
                        # Include row_idx so the same word in multiple rows produces unique IDs.
                        example_id=f"{prefix}-r{row_idx:03d}-{word}-{idx:03d}",
                        priority=int(intensity * 100),
                    )
                )
    return entries


def load_gemini_examples_dir(
    directory: Path | str,
    *,
    pattern: str = "gemini-code-*.txt",
) -> list[EmotionExampleEntry]:
    """Load every Gemini-format CSV under ``directory`` matching ``pattern``.

    Files are loaded in sorted name order so the result is deterministic.
    ``example_id`` is prefixed per file (timestamp suffix used as prefix) to
    keep IDs globally unique.
    """
    d = Path(directory)
    if not d.exists():
        raise DictionaryLoadError(f"Gemini examples directory not found: {d}")

    out: list[EmotionExampleEntry] = []
    for path in sorted(d.glob(pattern)):
        # Use the filename's numeric suffix as ID prefix for uniqueness.
        # gemini-code-1778827733587.txt → GEM-1778827733587
        stem = path.stem
        suffix = stem.split("-")[-1] if "-" in stem else stem
        prefix = f"GEM-{suffix}"
        out.extend(load_gemini_examples(path, id_prefix=prefix))
    return out


# ---------------------------------------------------------------------------
# Bundle assembly with externals
# ---------------------------------------------------------------------------


def load_bundle_with_external(
    dict_dir: Path | str,
    *,
    nrc_path: Path | str | None = None,
    gemini_path: Path | str | None = None,
    gemini_dir: Path | str | None = None,
    gemini_pattern: str = "gemini-code-*.txt",
    nrc_min_intensity: float = 0.5,
    internal_priority: bool = True,
) -> DictionaryBundle:
    """Load the internal bundle, then merge external sources.

    Parameters
    ----------
    dict_dir:
        Internal seed dictionaries (CSV files shipped with the package).
    nrc_path:
        Optional path to the NRC TSV lexicon.
    gemini_path:
        Optional single Gemini-format CSV path.
    gemini_dir:
        Optional directory of Gemini-format CSVs (loaded via ``gemini_pattern``).
    nrc_min_intensity:
        Threshold below which NRC rows are skipped.
    internal_priority:
        When True (default), internal entries take precedence: external entries
        whose ``surface`` already appears internally are dropped to avoid
        contradictory metadata. When False, all entries are kept (later ones
        win in dictionary lookups built downstream).
    """
    bundle = load_dictionary_bundle(dict_dir)

    if nrc_path:
        nrc_entries = load_nrc_lexicon(nrc_path, min_intensity=nrc_min_intensity)
        if internal_priority:
            existing = {e.surface for e in bundle.emotion}
            nrc_entries = [e for e in nrc_entries if e.surface not in existing]
        # External entries go to a separate list so the detector can apply
        # a lower lexical weight — NRC translations tend to over-fire on
        # common Japanese vocabulary (e.g. 確認 / 請求 etc).
        bundle.external_emotion.extend(nrc_entries)

    extra_examples: list[EmotionExampleEntry] = []
    if gemini_path:
        extra_examples.extend(load_gemini_examples(gemini_path))
    if gemini_dir:
        extra_examples.extend(load_gemini_examples_dir(gemini_dir, pattern=gemini_pattern))

    if extra_examples:
        if internal_priority:
            existing_ids = {e.example_id for e in bundle.emotion_examples}
            extra_examples = [e for e in extra_examples if e.example_id not in existing_ids]
        bundle.emotion_examples.extend(extra_examples)

    return bundle


# ---------------------------------------------------------------------------
# Convenience: load the user's local dic/ folder
# ---------------------------------------------------------------------------


def _default_user_dic_dir() -> Path | None:
    """Locate the external ``dic/`` directory across deployment layouts.

    Checked in order:

    1. ``$KOTOBACORE_DIC_DIR`` environment variable
    2. ``<project root>/dic``   (in-tree layout — e.g. /opt/kotobacore/dic on server)
    3. ``<project root>/../dic``  (sibling layout — local dev: G:\\...\\KotobaCore\\dic)

    Returns ``None`` if no candidate directory exists. Callers should treat
    ``None`` as "no external dictionaries available".
    """
    import os

    env = os.environ.get("KOTOBACORE_DIC_DIR")
    if env:
        env_path = Path(env)
        if env_path.exists():
            return env_path

    pkg_root = Path(__file__).resolve().parents[2]  # project root (sibling of `kotobacore/`)
    candidates = [pkg_root / "dic", pkg_root.parent / "dic"]
    for c in candidates:
        if c.exists():
            return c
    return None


def load_user_bundle(
    dict_dir: Path | str | None = None,
    *,
    nrc_filename: str = "Japanese-NRC-Emotion-Intensity-Lexicon-v1.txt",
    examples_filename: str = "Japanese-SNS-Emotion-Examples-v1.txt",
    nrc_min_intensity: float = 0.75,
) -> DictionaryBundle:
    """One-shot: load internal seed + NRC lexicon + SNS emotion examples in dic/.

    Defaults assume the layout::

        <project>/resources/dict/*.csv                      (internal seed)
        <dic>/Japanese-NRC-Emotion-Intensity-Lexicon-v1.txt
        <dic>/Japanese-SNS-Emotion-Examples-v1.txt
    """
    from kotobacore.dictionary.loader import _DEFAULT_DICT_DIR

    seed_dir = Path(dict_dir) if dict_dir else _DEFAULT_DICT_DIR
    user_dic = _default_user_dic_dir()

    if user_dic is None:
        return load_dictionary_bundle(seed_dir)

    nrc_path = user_dic / nrc_filename if (user_dic / nrc_filename).exists() else None
    examples_path = user_dic / examples_filename if (user_dic / examples_filename).exists() else None

    return load_bundle_with_external(
        seed_dir,
        nrc_path=nrc_path,
        gemini_path=examples_path,
        nrc_min_intensity=nrc_min_intensity,
    )
