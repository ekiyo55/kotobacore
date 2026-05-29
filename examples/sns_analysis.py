"""KotobaCore — SNS text analysis example.

Japanese SNS text contains slang, abbreviations, and emoticons that
standard morphological analyzers handle poorly. KotobaCore's slang
dictionary and Token Normalizer treat these as single semantic units.

Examples: しぬw / 草 / ワロタ / わらった / 大草原 / 神対応 / エモい
"""

from kotobacore import Analyzer

analyzer = Analyzer()

# ── 代表的なSNS表現サンプル ──────────────────────────────────
sns_texts = [
    "OpenAI APIの課金高すぎてしぬw",
    "騒ぎでわらった大草原",
    "神対応すぎて泣ける",
    "エモすぎてやばい",
    "それ草",
    "マジでムカつく最悪",
    "明日の発表まじ不安すぎてパニック",
]

print("=" * 70)
for text in sns_texts:
    result = analyzer.analyze(text)
    emo = result.emotion

    # SNS表現が1トークンとして正しく認識されているか確認
    slang_tokens = [
        t for t in result.tokens if t.pos == "感動詞-SNS表現"
    ]

    print(f"\n入力: {text!r}")
    print(f"  感情: {emo.primary} / {emo.polarity}  (intensity={emo.intensity:.2f})")
    print(f"  意図: {result.intent.label}")
    print(f"  RAG keywords: {result.rag.keywords}")

    if slang_tokens:
        print(f"  SNS表現トークン: {[t.surface for t in slang_tokens]}")

    chunk_texts = [c.text for c in result.chunks]
    print(f"  チャンク: {chunk_texts}")

# ── バッチ処理（タイムライン分析など）──────────────────────────
print("\n\n=== バッチ処理 ===")
timeline = [
    "今日のランチ最高すぎた！",
    "電車遅延でマジ最悪",
    "新機能リリースしたら神対応って言われてワロタ",
    "明日の締め切りやばい焦る",
]

results = analyzer.analyze_batch(timeline)
print(f"{'テキスト':<25} {'感情':<12} {'極性':<10} {'強度':>5}")
print("-" * 60)
for r in results:
    emo = r.emotion
    print(
        f"{r.text.original:<25} "
        f"{str(emo.primary):<12} "
        f"{str(emo.polarity):<10} "
        f"{emo.intensity:>5.2f}"
    )
