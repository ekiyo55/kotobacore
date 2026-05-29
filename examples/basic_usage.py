"""KotobaCore — basic usage example.

Demonstrates the core analyze() pipeline end-to-end:
  normalize → tokenize → semantic chunks → emotion → intent → RAG keywords
"""

from kotobacore import Analyzer

analyzer = Analyzer()

text = "OpenAI APIの課金高すぎてしぬw"
result = analyzer.analyze(text)

# ── テキスト情報 ──────────────────────────────────────────
print("=== テキスト ===")
print(f"  入力:     {result.text.original}")
print(f"  正規化後: {result.text.normalized}")

# ── トークン ─────────────────────────────────────────────
print("\n=== トークン ===")
for tok in result.tokens:
    print(f"  [{tok.id:2d}] {tok.surface:<12} pos={tok.pos}")

# ── セマンティックチャンク ──────────────────────────────────
print("\n=== チャンク ===")
for chunk in result.chunks:
    print(f"  [{chunk.id}] {chunk.text!r:<20} type={chunk.type}  score={chunk.score:.2f}")

# ── 感情 ─────────────────────────────────────────────────
emo = result.emotion
print("\n=== 感情 ===")
print(f"  primary={emo.primary}  polarity={emo.polarity}  intensity={emo.intensity:.2f}")
if emo.plutchik:
    print(f"  Plutchik: {emo.plutchik}")

# ── 意図 ─────────────────────────────────────────────────
intent = result.intent
print("\n=== 意図 ===")
print(f"  label={intent.label}  confidence={intent.confidence:.2f}")

# ── RAG キーワード ────────────────────────────────────────
rag = result.rag
print("\n=== RAG ===")
print(f"  keywords:     {rag.keywords}")
print(f"  search_query: {rag.search_query!r}")

# ── JSON 出力 ────────────────────────────────────────────
print("\n=== JSON (先頭200文字) ===")
print(result.to_json(pretty=True)[:200], "...")
