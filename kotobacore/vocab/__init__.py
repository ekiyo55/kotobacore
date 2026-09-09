"""Vocab — optional Token-layer module (FR-070〜072): vocabulary tables, Token IDs, vocabulary quality.

Built for Japanese LM work (e.g. a from-scratch mini-GPT): a vocabulary is
built from KotobaCore's *fine* tokenization (語幹 / 送り仮名 / 活用語尾), text is
encoded to integer ids and decoded back, and a report flags coverage / OOV /
contamination. The IR never depends on this package (§3.3): ``vocab`` reads
Token-layer output only. Vocabulary *data* is never shipped with the package.
"""

from kotobacore.vocab.build import (
    SPECIAL_TOKENS,
    VOCAB_FORMAT_VERSION,
    VocabEntry,
    Vocabulary,
    build_vocab,
    extend_vocab,
)
from kotobacore.vocab.encode import VocabEncoder
from kotobacore.vocab.evaluate import report_markdown, vocab_report

__all__ = [
    "SPECIAL_TOKENS", "VOCAB_FORMAT_VERSION", "VocabEncoder", "VocabEntry", "Vocabulary",
    "build_vocab", "extend_vocab", "report_markdown", "vocab_report",
]
