"""Tokenizer backend abstraction.

Per 04_内部設計書 §7. The semantic layer must not depend on a specific
backend implementation; this base class defines the contract.
"""

from __future__ import annotations

from kotobacore.schema import Token


class TokenizerBackend:
    """Abstract tokenizer backend."""

    def tokenize(self, text: str, mode: str = "C") -> list[Token]:
        raise NotImplementedError
