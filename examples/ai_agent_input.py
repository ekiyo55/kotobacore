"""KotobaCore — AI agent input preprocessing example.

Before sending Japanese user messages to an LLM or AI agent, KotobaCore
can enrich the payload with:
  - Semantic keywords for retrieval context injection
  - Intent label for routing to specialized handlers
  - Emotion/polarity for tone-aware response generation
  - Normalized text to strip noise before embedding

This example shows a typical preprocessing function for an AI agent pipeline.
"""

from __future__ import annotations

import json

from kotobacore import Analyzer

analyzer = Analyzer()


def preprocess_for_agent(user_message: str) -> dict:
    """Analyze a user message and return structured context for an AI agent."""
    result = analyzer.analyze(user_message)
    emo = result.emotion
    intent = result.intent
    rag = result.rag

    return {
        "original": result.text.original,
        "normalized": result.text.normalized,
        "intent": {
            "label": intent.label,
            "confidence": round(intent.confidence, 3),
        },
        "emotion": {
            "primary": emo.primary,
            "polarity": emo.polarity,
            "intensity": round(emo.intensity, 3),
        },
        "rag": {
            "keywords": rag.keywords,
            "search_query": rag.search_query,
            "summary_hint": rag.summary_hint,
        },
        "chunks": [c.text for c in result.chunks],
    }


# ── ユーザーメッセージのサンプル ──────────────────────────────
messages = [
    "OpenAI APIのコストを削減したいんだけど、何かいい方法ある?",
    "最近の機械学習モデルについて教えてほしい",
    "このサービス最悪、全然使えない。返金してほしい",
    "ありがとうございます！すごく助かりました！",
    "RAGシステムの構築を始めたいんですが何から手をつければいいですか",
]

print("=" * 70)
for msg in messages:
    ctx = preprocess_for_agent(msg)
    print(f"\nユーザー: {ctx['original']!r}")
    print(f"  intent:   {ctx['intent']['label']} ({ctx['intent']['confidence']})")
    print(f"  emotion:  {ctx['emotion']['primary']} / {ctx['emotion']['polarity']} "
          f"(intensity={ctx['emotion']['intensity']})")
    print(f"  keywords: {ctx['rag']['keywords']}")
    print(f"  query:    {ctx['rag']['search_query']!r}")
    print(f"  chunks:   {ctx['chunks']}")

# ── システムプロンプトへの注入例 ─────────────────────────────
print("\n\n=== システムプロンプト注入例 ===")
user_msg = "APIの課金が高すぎて困っています。安くする方法を教えてください。"
ctx = preprocess_for_agent(user_msg)

system_injection = f"""[ユーザーコンテキスト]
- 意図: {ctx['intent']['label']}
- 感情: {ctx['emotion']['primary']} ({ctx['emotion']['polarity']})
- キーワード: {', '.join(ctx['rag']['keywords'])}
- 検索クエリ: {ctx['rag']['search_query']}
"""

print("注入するコンテキスト:")
print(system_injection)

# JSON として渡す場合
print("JSON形式:")
print(json.dumps(ctx, ensure_ascii=False, indent=2))
