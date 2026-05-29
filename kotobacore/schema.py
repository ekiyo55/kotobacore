"""KotobaCore data schemas.

Schema definitions per 06_API仕様書 v0.1. All result objects are JSON-serializable
via `to_dict()` / `to_json()`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "0.1"


@dataclass
class MetaInfo:
    version: str
    schema_version: str
    mode: str
    backend: str
    language: str = "ja"


@dataclass
class TextInfo:
    original: str
    normalized: str


@dataclass
class Token:
    id: int
    surface: str
    normalized: str
    dictionary_form: str | None
    reading: str | None
    pos: str
    begin: int
    end: int
    unknown: bool = False


@dataclass
class SemanticToken:
    token_id: int
    surface: str
    semantic_type: str | None
    entity_type: str | None
    emotion: str | None
    plutchik_emotion: str | None
    confidence: float


@dataclass
class SemanticChunk:
    id: int
    text: str
    type: str
    token_ids: list[int]
    score: float


@dataclass
class EmotionExpression:
    text: str
    emotion: str
    plutchik_emotion: str | None
    polarity: str
    intensity: float
    confidence: float
    matched_examples: list[str] = field(default_factory=list)


@dataclass
class EmotionResult:
    primary: str | None
    polarity: str | None
    intensity: float
    confidence: float
    plutchik: dict[str, float] = field(default_factory=dict)
    expressions: list[EmotionExpression] = field(default_factory=list)


@dataclass
class IntentCandidate:
    label: str
    confidence: float


@dataclass
class IntentResult:
    label: str | None
    confidence: float
    candidates: list[IntentCandidate] = field(default_factory=list)


@dataclass
class RagResult:
    keywords: list[str] = field(default_factory=list)
    search_query: str = ""
    summary_hint: str | None = None
    semantic_phrases: list[str] = field(default_factory=list)


@dataclass
class KotobaError:
    code: str
    level: str
    message: str
    position: int | None
    recoverable: bool


@dataclass
class AnalysisResult:
    meta: MetaInfo
    text: TextInfo
    tokens: list[Token] = field(default_factory=list)
    semantic_tokens: list[SemanticToken] = field(default_factory=list)
    chunks: list[SemanticChunk] = field(default_factory=list)
    emotion: EmotionResult | None = None
    intent: IntentResult | None = None
    rag: RagResult | None = None
    errors: list[KotobaError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, pretty: bool = False) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=2 if pretty else None,
        )
