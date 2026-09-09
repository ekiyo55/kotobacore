"""Text ⇄ Token IDs (FR-071).

``encode`` tokenizes with the vocabulary's granularity, maps each piece to its
id, emits ``<nl>`` / ``<sp>`` for the whitespace between tokens (so ``decode``
restores line and word breaks), and falls back to characters for pieces the
vocabulary does not hold — a character the vocabulary has never seen becomes
``<unk>``. ``decode`` returns the *normalized* text (pieces are normalized
surfaces), which is what an LM trained on these ids will emit anyway.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from kotobacore.errors import E601_VOCAB_VERSION_MISMATCH, VocabVersionMismatch
from kotobacore.vocab.build import (
    BOS,
    EOS,
    NL,
    SP,
    UNK,
    VOCAB_FORMAT_VERSION,
    Vocabulary,
    _default_analyzer,
)


@dataclass
class EncodeStats:
    tokens: int = 0  # tokenizer tokens (excluding whitespace)
    whole: int = 0  # tokens encoded as one piece
    char_fallback: int = 0  # tokens split into characters
    unk: int = 0  # characters not in the vocabulary
    ids: int = 0  # total ids emitted (incl. whitespace specials)


class VocabEncoder:
    def __init__(self, vocab: Vocabulary, analyzer=None) -> None:
        # E601 vocab_version_mismatch (§9 / FR-071): ids are only stable within one format major
        mine = VOCAB_FORMAT_VERSION.rsplit("-", 1)[-1].split(".")[0]
        theirs = str(vocab.version).rsplit("-", 1)[-1].split(".")[0]
        if not str(vocab.version).startswith("kotobacore-vocab-") or mine != theirs:
            raise VocabVersionMismatch(f"{E601_VOCAB_VERSION_MISMATCH}: vocabulary {vocab.version!r} is not compatible with {VOCAB_FORMAT_VERSION!r}")
        self.vocab = vocab
        self.analyzer = analyzer or _default_analyzer(vocab.granularity)
        if getattr(self.analyzer, "granularity", vocab.granularity) != vocab.granularity:
            raise ValueError(f"analyzer granularity {self.analyzer.granularity!r} != vocabulary {vocab.granularity!r}")

    # ---- pieces
    def pieces(self, text: str, *, stats: EncodeStats | None = None) -> list[str]:
        """Piece strings for ``text`` (special tokens as their ``<name>`` form)."""
        out: list[str] = []
        tokens = self.analyzer.tokenize(text)
        prev_end = 0
        for t in tokens:
            for ch in text[prev_end:t.begin]:
                if ch == "\n":
                    out.append("<nl>")
                elif ch.isspace():
                    out.append("<sp>")
            prev_end = t.end
            if stats:
                stats.tokens += 1
            if self.vocab.piece_id(t.surface) is not None:
                out.append(t.surface)
                if stats:
                    stats.whole += 1
            else:
                if stats:
                    stats.char_fallback += 1
                for ch in t.surface:
                    if self.vocab.piece_id(ch) is not None:
                        out.append(ch)
                    else:
                        out.append("<unk>")
                        if stats:
                            stats.unk += 1
        for ch in text[prev_end:]:
            if ch == "\n":
                out.append("<nl>")
            elif ch.isspace():
                out.append("<sp>")
        if stats:
            stats.ids += len(out)
        return out

    def encode(self, text: str, *, add_special: bool = False, stats: EncodeStats | None = None) -> list[int]:
        ids = [self.vocab.piece_id(p) if self.vocab.piece_id(p) is not None else UNK for p in self.pieces(text, stats=stats)]
        if add_special:
            ids = [BOS, *ids, EOS]
        return ids

    def decode(self, ids: Sequence[int]) -> str:
        parts: list[str] = []
        for i in ids:
            if i == NL:
                parts.append("\n")
            elif i == SP:
                parts.append(" ")
            elif i == UNK:
                parts.append("�")
            elif i < len(self.vocab.special_tokens):
                continue  # pad / bos / eos / …: no text
            else:
                piece = self.vocab.id_piece(i)
                parts.append(piece if piece is not None else "�")
        return "".join(parts)

    def annotate(self, tokens) -> list[int | None]:
        """Vocabulary id per Token (None when the piece is not in the vocabulary) — the optional IR field of §3.3."""
        return [self.vocab.piece_id(t.surface) for t in tokens]
