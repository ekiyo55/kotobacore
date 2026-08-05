"""RAG Optimizer.

Per 04_内部設計書 §14 and 06_API §13. Produces ``RagResult`` with:

* ``keywords``         – ranked retrieval keywords (固有名詞 → 複合名詞 → 名詞 → 感情語)
* ``search_query``     – space-joined keyword string
* ``summary_hint``     – short one-line semantic description
* ``semantic_phrases`` – semantically meaningful phrases (chunks)

Stopwords from ``stopwords.csv`` are filtered out. Entity aliases are
also surfaced as additional keywords.
"""

from __future__ import annotations

from kotobacore.dictionary import DictionaryBundle
from kotobacore.schema import (
    EmotionResult,
    IntentResult,
    RagResult,
    SemanticChunk,
    SemanticToken,
    Token,
)

# Priority tiers for keyword ranking (lower = higher priority)
_PRIORITY_ENTITY = 1
_PRIORITY_COMPOUND = 2
_PRIORITY_TOPIC = 3
_PRIORITY_PROPER_NOUN = 4
_PRIORITY_NOUN = 5
_PRIORITY_EMOTION = 6

_CHUNK_TYPE_PRIORITY = {
    "service": _PRIORITY_ENTITY,
    "product": _PRIORITY_ENTITY,
    "technology": _PRIORITY_ENTITY,
    "entity": _PRIORITY_ENTITY,
    "compound_noun": _PRIORITY_COMPOUND,
    "topic": _PRIORITY_TOPIC,
    "complaint": _PRIORITY_EMOTION,
    "praise": _PRIORITY_EMOTION,
    "slang_emotion": _PRIORITY_EMOTION,
}


def _emotion_to_summary_word(emotion: str | None) -> str:
    return {
        "joy": "喜び",
        "admiration": "称賛",
        "moved": "感動",
        "anger": "怒り",
        "irritation": "苛立ち",
        "sadness": "悲しみ",
        "anxiety": "不安",
        "refusal": "拒否",
        "agreement": "同意",
        "exaggeration": "誇張",
        "mixed": "混合感情",
    }.get(emotion or "", "")


def optimize_rag(
    *,
    normalized_text: str,
    tokens: list[Token],
    semantic_tokens: list[SemanticToken],
    chunks: list[SemanticChunk],
    emotion: EmotionResult | None,
    intent: IntentResult | None,
    bundle: DictionaryBundle,
) -> RagResult:
    """Build a ``RagResult`` from analyzer outputs.

    The function is deterministic and cheap — it works purely on the
    structured outputs of earlier phases (no further dictionary scanning).
    """
    stopwords = bundle.stopword_set()

    candidates: list[tuple[int, int, str]] = []  # (priority, -length, surface)

    # ---------------------------------------------------------------- chunks
    for c in chunks:
        if not c.text or c.text in stopwords:
            continue
        prio = _CHUNK_TYPE_PRIORITY.get(c.type, _PRIORITY_NOUN)
        candidates.append((prio, -len(c.text), c.text))

    # --------------------------------------------- tokens not covered by chunks
    covered_token_ids = {tid for c in chunks for tid in c.token_ids}
    # Pre-build 2-char+ stopwords for prefix matching (catches KANJI adverb+verb fusions
    # e.g. 全然使 from 全然使えない where Karuizawa groups all KANJI into one token)
    sw_prefixes = {sw for sw in stopwords if len(sw) >= 2}
    for tok in tokens:
        if tok.id in covered_token_ids:
            continue
        surface = tok.surface
        normalized = tok.normalized or surface
        if surface in stopwords or normalized in stopwords:
            continue
        if len(surface.strip()) < 2:
            continue
        if any(surface.startswith(sw) for sw in sw_prefixes):
            continue
        pos = tok.pos
        if "固有名詞" in pos:
            candidates.append((_PRIORITY_PROPER_NOUN, -len(surface), surface))
        elif "名詞" in pos and "代名詞" not in pos:
            candidates.append((_PRIORITY_NOUN, -len(surface), surface))

    # ---------------------------- entity aliases for matched entity surfaces
    entity_map = {e.surface: e for e in bundle.entity}
    for c in chunks:
        if c.text in entity_map:
            ent = entity_map[c.text]
            for alias in ent.aliases:
                if alias and alias != c.text and alias not in stopwords:
                    candidates.append((_PRIORITY_ENTITY + 1, -len(alias), alias))

    # ----------------------------------------------------- emotion keywords
    if emotion and emotion.expressions:
        for exp in emotion.expressions:
            if exp.text and exp.text not in stopwords:
                candidates.append((_PRIORITY_EMOTION, -len(exp.text), exp.text))

    # ---------------------- ranking + dedup (preserve highest-priority first)
    candidates.sort()  # tuple sort: by priority asc, then length desc
    seen: set[str] = set()
    keywords: list[str] = []
    for _prio, _neglen, surface in candidates:
        if surface in seen:
            continue
        seen.add(surface)
        keywords.append(surface)

    # ---------------------------------------------------- semantic phrases
    semantic_phrases: list[str] = []
    for c in chunks:
        if (c.type in {"service", "product", "compound_noun", "topic", "entity"}
                and c.text not in semantic_phrases and c.text not in stopwords):
            semantic_phrases.append(c.text)

    # ------------------------------------------------------- summary hint
    summary_hint: str | None = None
    primary_topic = semantic_phrases[0] if semantic_phrases else (keywords[0] if keywords else None)
    primary_emotion = _emotion_to_summary_word(emotion.primary) if emotion else ""
    intent_label = intent.label if intent and intent.label not in (None, "unknown") else None

    parts: list[str] = []
    if primary_topic:
        parts.append(f"{primary_topic}に関する")
    if primary_emotion:
        parts.append(primary_emotion)
    if intent_label:
        parts.append(f"({intent_label})")
    if parts:
        summary_hint = "".join(parts).strip()

    search_query = " ".join(keywords)

    return RagResult(
        keywords=keywords,
        search_query=search_query,
        summary_hint=summary_hint,
        semantic_phrases=semantic_phrases,
    )
