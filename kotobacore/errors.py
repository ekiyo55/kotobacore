"""KotobaCore exception hierarchy."""

from __future__ import annotations


class KotobaCoreError(Exception):
    """Base exception for KotobaCore."""


class ConfigError(KotobaCoreError):
    """Raised when configuration is invalid."""


class DictionaryLoadError(KotobaCoreError):
    """Raised when dictionary loading fails."""


class BackendInitializeError(KotobaCoreError):
    """Raised when tokenizer backend initialization fails."""


class VocabVersionMismatch(KotobaCoreError):
    """E601: the vocabulary file's format major version differs from this KotobaCore's (vocab_version_mismatch)."""


# ---------------------------------------------------------------------------
# Error codes (要件定義書 §9). Analysis never stops on a recoverable error: the
# stage is skipped (or falls back) and a KotobaError is appended to IR.errors.
# ---------------------------------------------------------------------------
E101_INVALID_UTF8 = "E101 invalid_utf8"
E102_UNSUPPORTED_CHARACTER = "E102 unsupported_character"
E201_TOKENIZATION_ERROR = "E201 tokenization_error"
E202_DICTIONARY_LOAD_ERROR = "E202 dictionary_load_error"
E301_SENTENCE_BOUNDARY_ERROR = "E301 sentence_boundary_error"
E302_ENTITY_ERROR = "E302 entity_error"
E303_PREDICATE_ERROR = "E303 predicate_error"
E401_MODULE_ERROR = "E401 module_error"
E402_RAG_ERROR = "E402 rag_error"
E501_INVALID_IR = "E501 invalid_ir"
E502_SCHEMA_VERSION_MISMATCH = "E502 schema_version_mismatch"
E601_VOCAB_VERSION_MISMATCH = "E601 vocab_version_mismatch"
E602_UNKNOWN_TOKEN = "E602 unknown_token"
E700_API_ERROR = "E700 api_error"
E701_UNAUTHORIZED = "E701 unauthorized"
E702_RATE_LIMITED = "E702 rate_limited"


def make_error(code: str, message: str, *, position: int | None = None, recoverable: bool = True, level: str | None = None):
    """Build a ``core.ir.KotobaError`` (imported lazily to keep this module dependency-free)."""
    from kotobacore.core.ir import KotobaError

    return KotobaError(code=code, level=level or ("warning" if recoverable else "error"), message=message, position=position, recoverable=recoverable)
