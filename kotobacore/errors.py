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
