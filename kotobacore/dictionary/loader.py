"""CSV dictionary loader for KotobaCore.

Per 05_辞書設計書 v0.1. All CSVs are UTF-8 encoded, with a header row.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from kotobacore.errors import DictionaryLoadError

# ---------------------------------------------------------------------------
# Row dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SlangEntry:
    surface: str
    normalized: str
    meaning: str
    emotion: str  # emotion taxonomy value (per 05 §6.2). NOT polarity.
    category: str
    intensity: float
    keep_as_unit: bool


@dataclass
class EmotionEntry:
    surface: str
    base_emotion: str
    polarity: str
    intensity: float
    keep_as_unit: bool


@dataclass
class EmotionExampleEntry:
    surface: str
    base_emotion: str
    plutchik_emotion: str
    polarity: str
    intensity: float
    example: str
    example_id: str
    priority: int


@dataclass
class EntityEntry:
    surface: str
    type: str  # entity_type: PRODUCT / API / LOCATION ...
    normalized: str
    aliases: list[str]
    priority: int
    keep_as_unit: bool = False


@dataclass
class IntentRule:
    intent: str
    pattern: str  # 'a|b|c' alternation
    score: float
    priority: int


@dataclass
class StopwordEntry:
    surface: str
    category: str


@dataclass
class NormalizationEntry:
    source: str
    target: str
    type: str


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------


@dataclass
class DictionaryBundle:
    slang: list[SlangEntry] = field(default_factory=list)
    emotion: list[EmotionEntry] = field(default_factory=list)
    # External-sourced emotion entries (NRC lexicon etc.). Kept separately so
    # the detector can apply a lower confidence weight — external translations
    # tend to over-fire on common Japanese vocabulary.
    external_emotion: list[EmotionEntry] = field(default_factory=list)
    emotion_examples: list[EmotionExampleEntry] = field(default_factory=list)
    entity: list[EntityEntry] = field(default_factory=list)
    intent_rules: list[IntentRule] = field(default_factory=list)
    stopwords: list[StopwordEntry] = field(default_factory=list)
    normalization: list[NormalizationEntry] = field(default_factory=list)

    # Lazy cache for derived lookup structures. The bundle is immutable after
    # loading, so every derived structure (surface maps, candidate lists …) is
    # built once on first use and reused — avoids rebuilding them per analyze().
    # Consumers (detector / chunker) may also stash their own derived data here.
    _cache: dict = field(default_factory=dict, repr=False, compare=False)

    # ------------------------------------------------------------------
    # Lookup helpers — computed once, then served from _cache
    # ------------------------------------------------------------------
    def slang_by_surface(self) -> dict[str, SlangEntry]:
        c = self._cache.get("slang_by_surface")
        if c is None:
            c = {e.surface: e for e in self.slang}
            self._cache["slang_by_surface"] = c
        return c

    def emotion_by_surface(self) -> dict[str, EmotionEntry]:
        c = self._cache.get("emotion_by_surface")
        if c is None:
            c = {e.surface: e for e in self.emotion}
            self._cache["emotion_by_surface"] = c
        return c

    def entity_by_surface(self) -> dict[str, EntityEntry]:
        """Map surface AND aliases → EntityEntry. Primary surfaces win on collision."""
        c = self._cache.get("entity_by_surface")
        if c is None:
            c = {}
            # aliases first so that a primary surface overrides any colliding alias
            for e in self.entity:
                for alias in e.aliases:
                    if alias:
                        c[alias] = e
            for e in self.entity:
                if e.surface:
                    c[e.surface] = e
            self._cache["entity_by_surface"] = c
        return c

    def emotion_examples_by_surface(self) -> dict[str, list[EmotionExampleEntry]]:
        """Map surface → list of example entries (for example-based matching)."""
        c = self._cache.get("emotion_examples_by_surface")
        if c is None:
            c = {}
            for ex in self.emotion_examples:
                c.setdefault(ex.surface, []).append(ex)
            self._cache["emotion_examples_by_surface"] = c
        return c

    def stopword_set(self) -> set[str]:
        c = self._cache.get("stopword_set")
        if c is None:
            c = {e.surface for e in self.stopwords}
            self._cache["stopword_set"] = c
        return c

    def normalization_map(self) -> dict[str, str]:
        """Return {source: target} for all normalization rules (applied after NFKC)."""
        c = self._cache.get("normalization_map")
        if c is None:
            c = {e.source: e.target for e in self.normalization}
            self._cache["normalization_map"] = c
        return c

    def keep_as_unit_surfaces(self) -> dict[str, str]:
        """Return {surface: merged_pos} for all keep_as_unit entries.

        Slang/emotion expressions → 感動詞-SNS表現
        Entity entries → 名詞-固有名詞-一般
        """
        c = self._cache.get("keep_as_unit_surfaces")
        if c is None:
            c = {}
            for e in self.slang:
                if e.keep_as_unit:
                    c[e.surface] = "感動詞-SNS表現"
            for e in self.emotion:
                if e.keep_as_unit:
                    c[e.surface] = "感動詞-SNS表現"
            for e in self.entity:
                if e.keep_as_unit:
                    c[e.surface] = "名詞-固有名詞-一般"
            self._cache["keep_as_unit_surfaces"] = c
        return c


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _to_bool(s: str) -> bool:
    v = s.strip().lower()
    if v in {"true", "1", "yes", "y"}:
        return True
    if v in {"false", "0", "no", "n", ""}:
        return False
    raise DictionaryLoadError(f"Invalid bool value: {s!r}")


def _to_float_range(s: str, *, field: str) -> float:
    try:
        v = float(s)
    except ValueError as e:
        raise DictionaryLoadError(f"{field}: cannot parse {s!r} as float") from e
    if not (0.0 <= v <= 1.0):
        raise DictionaryLoadError(f"{field}: value {v} out of [0.0, 1.0]")
    return v


def _to_int(s: str, *, field: str) -> int:
    try:
        return int(s)
    except ValueError as e:
        raise DictionaryLoadError(f"{field}: cannot parse {s!r} as int") from e


def _open_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise DictionaryLoadError(f"Dictionary file not found: {path}")
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader]
    except OSError as e:
        raise DictionaryLoadError(f"Failed to read {path}: {e}") from e
    return rows


def _require_columns(rows: list[dict[str, str]], required: set[str], *, file: str) -> None:
    if not rows:
        return
    missing = required - set(rows[0].keys())
    if missing:
        raise DictionaryLoadError(f"{file}: missing required columns: {sorted(missing)}")


# ---------------------------------------------------------------------------
# Per-file loaders
# ---------------------------------------------------------------------------


def load_slang(path: Path) -> list[SlangEntry]:
    rows = _open_csv(path)
    _require_columns(
        rows,
        {"surface", "normalized", "meaning", "emotion", "category", "intensity", "keep_as_unit"},
        file=path.name,
    )
    out: list[SlangEntry] = []
    for i, row in enumerate(rows, start=2):
        out.append(
            SlangEntry(
                surface=row["surface"],
                normalized=row["normalized"],
                meaning=row["meaning"],
                emotion=row["emotion"],
                category=row["category"],
                intensity=_to_float_range(row["intensity"], field=f"{path.name}:row{i}:intensity"),
                keep_as_unit=_to_bool(row["keep_as_unit"]),
            )
        )
    return out


def load_emotion(path: Path) -> list[EmotionEntry]:
    rows = _open_csv(path)
    _require_columns(
        rows,
        {"surface", "base_emotion", "polarity", "intensity", "keep_as_unit"},
        file=path.name,
    )
    out: list[EmotionEntry] = []
    for i, row in enumerate(rows, start=2):
        out.append(
            EmotionEntry(
                surface=row["surface"],
                base_emotion=row["base_emotion"],
                polarity=row["polarity"],
                intensity=_to_float_range(row["intensity"], field=f"{path.name}:row{i}:intensity"),
                keep_as_unit=_to_bool(row["keep_as_unit"]),
            )
        )
    return out


def load_emotion_examples(path: Path) -> list[EmotionExampleEntry]:
    rows = _open_csv(path)
    _require_columns(
        rows,
        {
            "surface",
            "base_emotion",
            "plutchik_emotion",
            "polarity",
            "intensity",
            "example",
            "example_id",
            "priority",
        },
        file=path.name,
    )
    out: list[EmotionExampleEntry] = []
    for i, row in enumerate(rows, start=2):
        out.append(
            EmotionExampleEntry(
                surface=row["surface"],
                base_emotion=row["base_emotion"],
                plutchik_emotion=row["plutchik_emotion"],
                polarity=row["polarity"],
                intensity=_to_float_range(row["intensity"], field=f"{path.name}:row{i}:intensity"),
                example=row["example"],
                example_id=row["example_id"],
                priority=_to_int(row["priority"], field=f"{path.name}:row{i}:priority"),
            )
        )
    return out


def load_entity(path: Path) -> list[EntityEntry]:
    rows = _open_csv(path)
    _require_columns(
        rows,
        {"surface", "type", "normalized", "aliases", "priority"},
        file=path.name,
    )
    out: list[EntityEntry] = []
    for i, row in enumerate(rows, start=2):
        aliases_raw = row["aliases"] or ""
        aliases = [a.strip() for a in aliases_raw.split("|") if a.strip()]
        out.append(
            EntityEntry(
                surface=row["surface"],
                type=row["type"],
                normalized=row["normalized"],
                aliases=aliases,
                priority=_to_int(row["priority"], field=f"{path.name}:row{i}:priority"),
                keep_as_unit=_to_bool(row.get("keep_as_unit", "false")),
            )
        )
    return out


def load_intent_rules(path: Path) -> list[IntentRule]:
    rows = _open_csv(path)
    _require_columns(
        rows,
        {"intent", "pattern", "score", "priority"},
        file=path.name,
    )
    out: list[IntentRule] = []
    for i, row in enumerate(rows, start=2):
        out.append(
            IntentRule(
                intent=row["intent"],
                pattern=row["pattern"],
                score=_to_float_range(row["score"], field=f"{path.name}:row{i}:score"),
                priority=_to_int(row["priority"], field=f"{path.name}:row{i}:priority"),
            )
        )
    return out


def load_stopwords(path: Path) -> list[StopwordEntry]:
    rows = _open_csv(path)
    _require_columns(rows, {"surface", "category"}, file=path.name)
    return [StopwordEntry(surface=row["surface"], category=row["category"]) for row in rows]


def load_normalization(path: Path) -> list[NormalizationEntry]:
    rows = _open_csv(path)
    _require_columns(rows, {"source", "target", "type"}, file=path.name)
    return [NormalizationEntry(source=row["source"], target=row["target"], type=row["type"]) for row in rows]


# ---------------------------------------------------------------------------
# Bundle loader
# ---------------------------------------------------------------------------


# Seed dictionaries ship inside the package (``kotobacore/resources/dict``) so
# they are included in wheels / sdists. The legacy top-level ``resources/dict``
# (next to the package) is kept as a fallback for older editable layouts.
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _resolve_default_dict_dir() -> Path:
    candidates = [
        _PACKAGE_ROOT / "resources" / "dict",         # packaged (wheel/sdist/editable)
        _PACKAGE_ROOT.parent / "resources" / "dict",  # legacy top-level layout
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


_DEFAULT_DICT_DIR = _resolve_default_dict_dir()


def load_dictionary_bundle(dict_dir: Path | str) -> DictionaryBundle:
    """Load all 6 dictionary files from ``dict_dir`` into a bundle.

    Missing optional files are tolerated (treated as empty). slang / emotion /
    entity / intent_rules / stopwords / emotion_examples are all looked for.
    """
    base = Path(dict_dir)
    if not base.exists():
        raise DictionaryLoadError(f"Dictionary directory not found: {base}")

    bundle = DictionaryBundle()
    pairs = [
        ("slang.csv", "slang", load_slang),
        ("emotion.csv", "emotion", load_emotion),
        ("emotion_examples.csv", "emotion_examples", load_emotion_examples),
        ("entity.csv", "entity", load_entity),
        ("intent_rules.csv", "intent_rules", load_intent_rules),
        ("stopwords.csv", "stopwords", load_stopwords),
        ("normalization.csv", "normalization", load_normalization),
    ]
    for filename, attr, loader in pairs:
        path = base / filename
        if path.exists():
            setattr(bundle, attr, loader(path))
        # Missing optional files → empty list (default_factory).

    return bundle


def load_default_bundle() -> DictionaryBundle:
    """Load bundle from the package-bundled ``resources/dict`` directory."""
    return load_dictionary_bundle(_DEFAULT_DICT_DIR)
