"""Vocabulary construction (FR-070 / FR-071).

A :class:`Vocabulary` is a list of *pieces* (fine-granularity token surfaces on
the normalized text) with integer ids:

- ids 0–9 are reserved for special tokens (:data:`SPECIAL_TOKENS`);
- word pieces follow in descending frequency (ties broken by the piece text)
  so a build is deterministic for the same corpus and settings;
- every distinct non-space character of the corpus is also a piece ("char"
  flag, exempt from ``min_freq``) so unknown words fall back to characters
  and nothing is dropped as OOV (FR-071);
- :func:`extend_vocab` only *appends* — existing ids never change within a
  vocabulary version.

Vocabulary data is never shipped inside the package; save / load are JSON.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from kotobacore._version import __version__

VOCAB_FORMAT_VERSION = "kotobacore-vocab-1.0"
SPECIAL_TOKENS: tuple[str, ...] = ("<pad>", "<unk>", "<bos>", "<eos>", "<sep>", "<mask>", "<cls>", "<nl>", "<sp>", "<reserved>")
PAD, UNK, BOS, EOS, SEP, MASK, CLS, NL, SP, RESERVED = range(10)
FIRST_ID = len(SPECIAL_TOKENS)


@dataclass
class VocabEntry:
    piece: str
    id: int
    freq: int
    pos: str
    flags: list[str] = field(default_factory=list)


@dataclass
class Vocabulary:
    version: str = VOCAB_FORMAT_VERSION
    granularity: str = "fine"
    normalization_version: str = f"kotobacore-{__version__}"
    kotobacore_version: str = __version__
    min_freq: int = 1
    special_tokens: list[str] = field(default_factory=lambda: list(SPECIAL_TOKENS))
    entries: list[VocabEntry] = field(default_factory=list)

    # ---- lookups (built lazily, invalidated by _reindex)
    def __post_init__(self) -> None:
        self._reindex()

    def _reindex(self) -> None:
        self._piece_to_id: dict[str, int] = {p: i for i, p in enumerate(self.special_tokens)}
        self._piece_to_id.update({e.piece: e.id for e in self.entries})
        self._id_to_piece: dict[int, str] = {i: p for p, i in self._piece_to_id.items()}

    def __len__(self) -> int:
        return len(self.special_tokens) + len(self.entries)

    def piece_id(self, piece: str) -> int | None:
        return self._piece_to_id.get(piece)

    def id_piece(self, idx: int) -> str | None:
        return self._id_to_piece.get(idx)

    @property
    def next_id(self) -> int:
        return max((e.id for e in self.entries), default=FIRST_ID - 1) + 1

    # ---- (de)serialization
    def to_dict(self) -> dict:
        return {
            "version": self.version, "granularity": self.granularity, "normalization_version": self.normalization_version,
            "kotobacore_version": self.kotobacore_version, "min_freq": self.min_freq, "special_tokens": list(self.special_tokens),
            "entries": [asdict(e) for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Vocabulary:
        return cls(
            version=data["version"], granularity=data.get("granularity", "fine"),
            normalization_version=data.get("normalization_version", ""), kotobacore_version=data.get("kotobacore_version", ""),
            min_freq=data.get("min_freq", 1), special_tokens=list(data.get("special_tokens", SPECIAL_TOKENS)),
            entries=[VocabEntry(**e) for e in data.get("entries", [])],
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> Vocabulary:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


# ---------------------------------------------------------------- building


def _default_analyzer(granularity: str):
    from kotobacore.analyzer import Analyzer

    return Analyzer(granularity=granularity, enable_emotion=False, enable_sentiment=False, enable_intent=False, enable_rag=False)


def _piece_flags(piece: str, pos: str, unknown: bool) -> list[str]:
    flags: list[str] = []
    if len(piece) == 1:
        flags.append("char")
    if unknown:
        flags.append("unknown")
    if piece.isascii():
        flags.append("ascii")
    if piece.isdigit():
        flags.append("digit")
    if pos.startswith("記号") or (not piece.isalnum() and not any("぀" <= c <= "鿿" for c in piece)):
        flags.append("symbol")
    return flags


def count_pieces(texts: Iterable[str], analyzer, *, count_chars: bool = True) -> tuple[Counter[str], dict[str, Counter[str]], set[str]]:
    """Frequency of fine pieces, their POS votes, and the set of pieces the tokenizer flagged unknown."""
    freq: Counter[str] = Counter()
    pos_votes: dict[str, Counter[str]] = defaultdict(Counter)
    unknown: set[str] = set()
    for text in texts:
        if not text or not text.strip():
            continue
        for t in analyzer.tokenize(text):
            freq[t.surface] += 1
            pos_votes[t.surface][t.pos] += 1
            if t.unknown:
                unknown.add(t.surface)
        if count_chars:
            for ch in analyzer.normalize(text):
                if not ch.isspace() and len(ch) == 1:
                    freq.setdefault(ch, 0)  # every character is a piece even with freq 0 as a *word*
                    pos_votes[ch].setdefault("文字", 0)
    return freq, pos_votes, unknown


def build_vocab(
    texts: Iterable[str],
    *,
    analyzer=None,
    granularity: str = "fine",
    min_freq: int = 1,
    max_size: int | None = None,
) -> Vocabulary:
    """Build a vocabulary from ``texts`` (FR-070).

    ``min_freq`` applies to multi-character pieces; single characters are always
    kept (FR-071 character fallback). ``max_size`` caps the number of
    multi-character pieces (most frequent first); it never removes characters.
    """
    analyzer = analyzer or _default_analyzer(granularity)
    freq, pos_votes, unknown = count_pieces(texts, analyzer)
    words = [(p, f) for p, f in freq.items() if len(p) > 1 and f >= min_freq]
    words.sort(key=lambda x: (-x[1], x[0]))
    if max_size is not None:
        words = words[:max_size]
    chars = sorted(((p, f) for p, f in freq.items() if len(p) == 1), key=lambda x: (-x[1], x[0]))
    entries: list[VocabEntry] = []
    next_id = FIRST_ID
    for piece, f in [*words, *chars]:
        pos = pos_votes[piece].most_common(1)[0][0] if pos_votes[piece] else "文字"
        entries.append(VocabEntry(piece=piece, id=next_id, freq=f, pos=pos, flags=_piece_flags(piece, pos, piece in unknown)))
        next_id += 1
    return Vocabulary(granularity=analyzer.granularity, min_freq=min_freq, entries=entries)


def extend_vocab(vocab: Vocabulary, texts: Iterable[str], *, analyzer=None, min_freq: int | None = None) -> Vocabulary:
    """Append the new pieces of ``texts`` to ``vocab`` (FR-071: ids are never reassigned).

    Frequencies of existing pieces are updated in place (metadata only). New
    multi-character pieces need ``min_freq`` (default: the vocabulary's) and get
    ids after the current maximum; new characters are always added.
    """
    analyzer = analyzer or _default_analyzer(vocab.granularity)
    min_freq = vocab.min_freq if min_freq is None else min_freq
    freq, pos_votes, unknown = count_pieces(texts, analyzer)
    by_piece = {e.piece: e for e in vocab.entries}
    for piece, f in freq.items():
        if piece in by_piece:
            by_piece[piece].freq += f
    new = [(p, f) for p, f in freq.items() if p not in by_piece and (len(p) == 1 or f >= min_freq)]
    new.sort(key=lambda x: (-x[1], x[0]))
    next_id = vocab.next_id
    for piece, f in new:
        pos = pos_votes[piece].most_common(1)[0][0] if pos_votes[piece] else "文字"
        vocab.entries.append(VocabEntry(piece=piece, id=next_id, freq=f, pos=pos, flags=_piece_flags(piece, pos, piece in unknown)))
        next_id += 1
    vocab._reindex()
    return vocab
