"""KotobaCore — semantic chunk example.

Shows how KotobaCore splits Japanese text into meaningful semantic units
rather than simple morpheme sequences. Useful for search indexing, RAG
document segmentation, and NLP preprocessing pipelines.
"""

from kotobacore import Analyzer

analyzer = Analyzer()

texts = [
    "東京都渋谷区でAIスタートアップが新サービスを発表した",
    "今日のランチは渋谷の老舗ラーメン屋で醤油ラーメンを食べた",
    "OpenAI APIの課金高すぎてしぬw",
]

for text in texts:
    result = analyzer.analyze(text)

    print(f"\n入力: {text!r}")
    print(f"  トークン数: {len(result.tokens)}")
    print(f"  チャンク数: {len(result.chunks)}")
    print("  チャンク一覧:")
    for chunk in result.chunks:
        token_surfaces = [
            result.tokens[tid].surface
            for tid in chunk.token_ids
            if tid < len(result.tokens)
        ]
        print(
            f"    [{chunk.id}] {chunk.text!r:<20} "
            f"type={chunk.type:<20} score={chunk.score:.2f} "
            f"tokens={token_surfaces}"
        )

# ── チャンクのみ取り出したい場合 ──────────────────────────────
print("\n=== チャンクテキストだけ取り出す ===")
result = analyzer.analyze("機械学習モデルの精度改善について相談したい")
chunk_texts = [c.text for c in result.chunks]
print(f"  {chunk_texts}")
