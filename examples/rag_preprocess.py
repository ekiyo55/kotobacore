"""KotobaCore — RAG preprocessing example.

Shows how to use KotobaCore's RAG optimizer to extract high-quality
keywords and search queries from Japanese text before indexing or
similarity search.

Typical use cases:
  - Document indexing: extract keywords to store alongside embeddings
  - Query expansion: enrich user queries for better recall
  - Summary hint generation for metadata fields
"""

from kotobacore import Analyzer

analyzer = Analyzer()

# ── ドキュメントインデックス時のキーワード抽出 ──────────────────
documents = [
    "東京都渋谷区のAIスタートアップが、自然言語処理を活用した新しい検索エンジンを発表しました。",
    "機械学習モデルのファインチューニングにはGPUメモリが重要で、学習率の調整も効果的です。",
    "OpenAI APIのgpt-4oは高精度だが、課金コストが高いため予算管理が必要です。",
]

print("=== ドキュメントのキーワード抽出 ===")
for doc in documents:
    result = analyzer.analyze(doc)
    rag = result.rag
    print(f"\n文書: {doc[:40]}...")
    print(f"  keywords:     {rag.keywords}")
    print(f"  search_query: {rag.search_query!r}")
    if rag.summary_hint:
        print(f"  summary_hint: {rag.summary_hint!r}")
    if rag.semantic_phrases:
        print(f"  phrases:      {rag.semantic_phrases}")

# ── クエリ拡張（検索時）──────────────────────────────────────
queries = [
    "APIのコスト削減方法を教えて",
    "感情分析の精度を上げたい",
    "RAGシステムの構築について相談したい",
]

print("\n\n=== クエリ拡張 ===")
for query in queries:
    result = analyzer.analyze(query)
    rag = result.rag
    intent = result.intent
    print(f"\nクエリ: {query!r}")
    print(f"  拡張キーワード: {rag.keywords}")
    print(f"  検索クエリ:     {rag.search_query!r}")
    print(f"  意図:           {intent.label} ({intent.confidence:.2f})")

# ── RAG専用モード（感情・意図を無効化して高速化）─────────────────
print("\n\n=== RAG専用モード ===")
rag_only = Analyzer(
    enable_emotion=False,
    enable_intent=False,
)
result = rag_only.analyze("Transformerモデルのアテンション機構について詳しく知りたい")
print(f"  keywords: {result.rag.keywords}")
print(f"  query:    {result.rag.search_query!r}")
