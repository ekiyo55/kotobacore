"""KotobaCore: Japanese semantic understanding engine."""

from kotobacore._version import __version__
from kotobacore.analyzer import Analyzer
from kotobacore.errors import (
    BackendInitializeError,
    ConfigError,
    DictionaryLoadError,
    KotobaCoreError,
)
from kotobacore.schema import (
    AnalysisResult,
    EmotionExpression,
    EmotionResult,
    IntentCandidate,
    IntentResult,
    KotobaError,
    MetaInfo,
    RagResult,
    SemanticChunk,
    SemanticToken,
    TextInfo,
    Token,
)

__all__ = [
    "__version__",
    "Analyzer",
    "AnalysisResult",
    "BackendInitializeError",
    "ConfigError",
    "DictionaryLoadError",
    "EmotionExpression",
    "EmotionResult",
    "IntentCandidate",
    "IntentResult",
    "KotobaCoreError",
    "KotobaError",
    "MetaInfo",
    "RagResult",
    "SemanticChunk",
    "SemanticToken",
    "TextInfo",
    "Token",
]
