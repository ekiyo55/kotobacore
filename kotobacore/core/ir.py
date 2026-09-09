"""KotobaCore data schemas.

Schema definitions per 06_API仕様書 v0.1. All result objects are JSON-serializable
via `to_dict()` / `to_json()`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

# Semantic IR schema. 1.0 = frozen at KotobaCore 1.0.0 (2026-09-09): field additions are minor
# (backward compatible), removals / type changes are major. History: 0.1 flat result → 0.2 document
# hierarchy / entities / query IR → 0.3 predicates / relations / events / topics / chunk context →
# 0.4 coreference / conjugation / components → 1.0 freeze (same fields as 0.4).
SCHEMA_VERSION = "1.0"


@dataclass
class MetaInfo:
    version: str
    schema_version: str
    mode: str
    backend: str
    language: str = "ja"
    # v0.6.4 (NFR-002/003 reproducibility): versions of the components that produced this result
    # (tokenizer / dictionary_set / modules …) — see kotobacore.versions.component_versions()
    components: dict[str, Any] = field(default_factory=dict)


@dataclass
class TextInfo:
    original: str
    normalized: str
    # origin index in ``original`` for each character of ``normalized``
    # (FR-002 位置写像). Token/IR spans are expressed in original coordinates.
    offset_map: list[int] = field(default_factory=list)


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
    # v0.6.3 (FR-002 N4 / FR-010): conjugation type (五段 / 一段 / カ変 / サ変 / 形容詞 / 形容動詞,
    # "五段?" when only a dictionary could settle it) and form (基本形 / 過去 / 否定-過去 / 使役-受身 …)
    conjugation_type: str | None = None
    conjugation_form: str | None = None


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
    # evidence span in original-text coordinates (FR-051 Traceability)
    begin: int = 0
    end: int = 0
    negated: bool = False
    # 宛先付き感情 (FR-052): who feels it and what it is about
    holder: str = "speaker"  # "speaker" or an Entity id
    holder_text: str | None = None
    about: str | None = None  # Entity id when the topic is an entity
    about_text: str | None = None


@dataclass
class EmotionResult:
    primary: str | None
    polarity: str | None
    intensity: float
    confidence: float
    plutchik: dict[str, float] = field(default_factory=dict)
    expressions: list[EmotionExpression] = field(default_factory=list)


@dataclass
class SentimentExpression:
    """One evaluative expression (Sentiment module, FR-062)."""

    text: str
    polarity: str
    intensity: float
    confidence: float
    begin: int = 0
    end: int = 0
    negated: bool = False
    # 宛先付き評価 (FR-052): the evaluated thing — Entity id when available
    target: str | None = None
    target_text: str | None = None


@dataclass
class SentimentResult:
    """Evaluative stance (評価). ``polarity`` is computed from evaluative words
    only (sentiment.csv); ``affect_polarity`` is the polarity implied by
    emotion words (same value as ``EmotionResult.polarity``) — kept apart
    because 怖かった (fear) can still be a positive appraisal of a film."""

    polarity: str | None
    intensity: float
    confidence: float
    expressions: list[SentimentExpression] = field(default_factory=list)
    affect_polarity: str | None = None


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
class Entity:
    """A mention of a thing (FR-030〜034). Spans are original-text coordinates."""

    id: str
    type: str  # PERSON / ORGANIZATION / LOCATION / PRODUCT / BRAND / SERVICE / WORK / EVENT / TOPIC / DATE / TIME / MONEY / QUANTITY …
    surface: str
    begin: int
    end: int
    normalized: str | None = None
    token_ids: list[int] = field(default_factory=list)
    source: str = "dictionary"  # dictionary | pattern | time | quantity
    value: Any = None  # ISO date/time for DATE/TIME, number for MONEY/QUANTITY
    unit: str | None = None
    currency: str | None = None
    confidence: float = 1.0
    # v0.6.2 (FR-034 coreference, document level): id of the cluster's representative
    # mention (== own id for the representative; None when unresolved) and, on the
    # representative, the other surfaces of the cluster (田中さん → 田中).
    canonical_id: str | None = None
    aliases: list[str] = field(default_factory=list)


@dataclass
class Argument:
    """One argument of a predicate (述語項, FR-023)."""

    role: str  # subject / topic / object / goal / location / means / source / until / with / than / time
    text: str
    begin: int
    end: int
    entity_id: str | None = None
    token_ids: list[int] = field(default_factory=list)


@dataclass
class Predicate:
    id: str
    text: str
    lemma: str
    begin: int
    end: int
    token_ids: list[int] = field(default_factory=list)
    clause_index: int = 0
    arguments: list[Argument] = field(default_factory=list)
    negated: bool = False
    voice: str = "active"  # active / passive / causative
    nominal: bool = False  # copula / サ変 predicate on a noun


@dataclass
class Relation:
    """subject --predicate--> argument (FR-040). ``source``/``target`` are Entity ids when available."""

    id: str
    source: str | None
    source_text: str
    relation: str
    role: str
    target: str | None
    target_text: str
    predicate_id: str
    negated: bool = False
    begin: int = 0
    end: int = 0


@dataclass
class Event:
    """One predicate with typed roles (FR-041)."""

    id: str
    type: str
    predicate: str
    predicate_id: str
    agent: str | None = None
    agent_text: str | None = None
    object: str | None = None
    object_text: str | None = None
    goal: str | None = None
    goal_text: str | None = None
    location: str | None = None
    location_text: str | None = None
    time: str | None = None
    time_text: str | None = None
    negated: bool = False
    voice: str = "active"
    begin: int = 0
    end: int = 0


@dataclass
class Topic:
    label: str
    score: float
    count: int = 1
    entity_id: str | None = None
    entity_type: str | None = None
    source: str = "noun"  # entity | noun


@dataclass
class TopicResult:
    topics: list[Topic] = field(default_factory=list)


@dataclass
class Sentence:
    """Sentence node of the Document → Paragraph → Sentence → Token hierarchy."""

    id: int
    begin: int
    end: int
    text: str
    token_ids: list[int] = field(default_factory=list)
    entity_ids: list[str] = field(default_factory=list)
    emotion: EmotionResult | None = None
    sentiment: SentimentResult | None = None
    intent: IntentResult | None = None


@dataclass
class Paragraph:
    id: int
    begin: int
    end: int
    sentence_ids: list[int] = field(default_factory=list)
    heading: bool = False


@dataclass
class DocumentChunk:
    """Retrieval unit produced by Semantic Chunking (FR-081/082)."""

    id: int
    begin: int
    end: int
    text: str
    paragraph_ids: list[int] = field(default_factory=list)
    sentence_ids: list[int] = field(default_factory=list)
    entity_ids: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    summary_hint: str | None = None
    # v0.5.2: enclosing Markdown headings (outermost first) and, for table rows,
    # the table's header row — the context a retriever should index with the text
    heading_path: list[str] = field(default_factory=list)
    context: str = ""

    @property
    def text_with_context(self) -> str:
        return f"{self.context}\n{self.text}" if self.context else self.text


@dataclass
class QueryIR:
    """Structured search query (FR-080/081), same vocabulary as the document IR."""

    original: str
    normalized_query: str
    intent: str
    answer_type: str | None
    target: str | None
    entities: list[Entity] = field(default_factory=list)
    constraints: dict[str, list[str]] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)
    expanded_terms: list[str] = field(default_factory=list)
    sentiment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, pretty: bool = False) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2 if pretty else None)


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
    entities: list[Entity] = field(default_factory=list)
    predicates: list[Predicate] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    emotion: EmotionResult | None = None
    sentiment: SentimentResult | None = None
    intent: IntentResult | None = None
    topics: TopicResult | None = None
    rag: RagResult | None = None
    # Document hierarchy (populated by Analyzer.analyze_document)
    paragraphs: list[Paragraph] = field(default_factory=list)
    sentences: list[Sentence] = field(default_factory=list)
    document_chunks: list[DocumentChunk] = field(default_factory=list)
    errors: list[KotobaError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, pretty: bool = False) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=2 if pretty else None,
        )
