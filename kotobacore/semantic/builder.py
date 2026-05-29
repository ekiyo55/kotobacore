"""SemanticToken builder.

Per 04_内部設計書 §10-11 and 06_API §9. Assigns semantic_type / entity_type /
emotion / plutchik_emotion / confidence to each token via dictionary lookup
followed by POS-based fallback.
"""

from __future__ import annotations

from kotobacore.dictionary import DictionaryBundle
from kotobacore.dictionary.external import JP_TO_PLUTCHIK
from kotobacore.schema import SemanticToken, Token

# ---------------------------------------------------------------------------
# Plutchik mapping from KotobaCore base emotion → Plutchik
# (mirrors 05_辞書設計書 §6.6.3)
# ---------------------------------------------------------------------------
BASE_TO_PLUTCHIK: dict[str, str] = {
    "joy": "joy",
    "admiration": "trust",       # Plutchik: admiration = high-intensity trust (NRC confirms)
    "moved": "joy",
    "anger": "anger",
    "irritation": "anger",       # annoyance = low-intensity anger (NRC: fedup→anger/0.734)
    "sadness": "sadness",
    "anxiety": "fear",
    "refusal": "disgust",
    "agreement": "trust",
    "exaggeration": "surprise",
    "anticipation": "anticipation",  # NRC 8th primary emotion: 期待/憧れ等
    "mixed": "mixed",
}


def _plutchik_for(base_emotion: str | None) -> str | None:
    if not base_emotion:
        return None
    return BASE_TO_PLUTCHIK.get(base_emotion)


def build_semantic_tokens(
    tokens: list[Token], bundle: DictionaryBundle
) -> list[SemanticToken]:
    """Build SemanticTokens from Tokens + Dictionary.

    Priority order (highest first):
      1. user_dictionary (future)
      2. slang.csv
      3. emotion.csv
      4. entity.csv
      5. POS-based fallback

    Per 05_辞書設計書 §12.1. Lookup is on the token's surface, then the
    normalized form as a fallback.
    """
    slang_map = bundle.slang_by_surface()
    emotion_map = bundle.emotion_by_surface()
    entity_map = bundle.entity_by_surface()

    out: list[SemanticToken] = []
    for tok in tokens:
        surface = tok.surface
        normalized = tok.normalized or surface

        # 1. slang (SNS表現)
        slang = slang_map.get(surface) or slang_map.get(normalized)
        if slang:
            out.append(
                SemanticToken(
                    token_id=tok.id,
                    surface=surface,
                    semantic_type="slang",
                    entity_type=None,
                    emotion=slang.emotion,
                    plutchik_emotion=_plutchik_for(slang.emotion),
                    confidence=0.85,
                )
            )
            continue

        # 2. emotion (single-token entries — multi-token like "課金高すぎ" won't match here
        #              but will be picked up by the chunker)
        emotion = emotion_map.get(surface) or emotion_map.get(normalized)
        if emotion:
            out.append(
                SemanticToken(
                    token_id=tok.id,
                    surface=surface,
                    semantic_type="emotion",
                    entity_type=None,
                    emotion=emotion.base_emotion,
                    plutchik_emotion=_plutchik_for(emotion.base_emotion),
                    confidence=0.85,
                )
            )
            continue

        # 3. entity
        entity = entity_map.get(surface) or entity_map.get(normalized)
        if entity:
            semantic_type_map = {
                "API": "service",
                "SERVICE": "service",
                "PRODUCT": "product",
                "TECHNOLOGY": "technology",
                "TOPIC": "topic",
                "MODEL": "product",
                "PERSON": "entity",
                "ORGANIZATION": "entity",
                "LOCATION": "entity",
                "EVENT": "entity",
                "COMPANY": "entity",
            }
            out.append(
                SemanticToken(
                    token_id=tok.id,
                    surface=surface,
                    semantic_type=semantic_type_map.get(entity.type, "entity"),
                    entity_type=entity.type,
                    emotion=None,
                    plutchik_emotion=None,
                    confidence=0.9,
                )
            )
            continue

        # 4. POS-based fallback
        pos = tok.pos
        if "固有名詞" in pos:
            out.append(_pos_token(tok, semantic_type="entity", entity_type=None, conf=0.6))
        elif "形容詞" in pos:
            # Adjectives are evaluation candidates — leave emotion unset, chunker may upgrade.
            out.append(_pos_token(tok, semantic_type="emotion", entity_type=None, conf=0.4))
        elif "名詞" in pos and "代名詞" not in pos:
            out.append(_pos_token(tok, semantic_type=None, entity_type=None, conf=0.0))
        else:
            out.append(_pos_token(tok, semantic_type=None, entity_type=None, conf=0.0))

    return out


def _pos_token(
    tok: Token, *, semantic_type: str | None, entity_type: str | None, conf: float
) -> SemanticToken:
    return SemanticToken(
        token_id=tok.id,
        surface=tok.surface,
        semantic_type=semantic_type,
        entity_type=entity_type,
        emotion=None,
        plutchik_emotion=None,
        confidence=conf,
    )


# Re-export for convenience
__all__ = ["BASE_TO_PLUTCHIK", "build_semantic_tokens"]
# Suppress unused-import warning for JP_TO_PLUTCHIK (kept for downstream consumers)
_ = JP_TO_PLUTCHIK
