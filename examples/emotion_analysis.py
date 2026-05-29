"""KotobaCore — emotion analysis example.

Demonstrates emotion detection with Plutchik wheel mapping.
KotobaCore detects primary emotion, polarity, intensity, and maps
to Plutchik's 8 basic emotions (joy, trust, fear, surprise, sadness,
disgust, anger, anticipation).
"""

from kotobacore import Analyzer

analyzer = Analyzer()

samples = [
    # (text, 期待される感情)
    ("OpenAI APIの課金高すぎてしぬw",          "anger / negative"),
    ("明日は東京でデートだ、超楽しみ！",         "joy / positive"),
    ("友達に裏切られてマジで悲しい",             "sadness / negative"),
    ("突然の地震でパニックになった",             "fear / negative"),
    ("先輩が助けてくれた！なんとか解決できそう！", "joy / positive"),
    ("もう無理。請求まわりを確認して",           "refusal / negative"),
]

print("=" * 60)
for text, expected in samples:
    result = analyzer.analyze(text)
    emo = result.emotion

    print(f"\n入力: {text!r}")
    print(f"  期待: {expected}")
    print(f"  結果: primary={emo.primary}  polarity={emo.polarity}")
    print(f"        intensity={emo.intensity:.2f}  confidence={emo.confidence:.2f}")

    if emo.plutchik:
        top = sorted(emo.plutchik.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"  Plutchik top3: {top}")

    if emo.expressions:
        expr = emo.expressions[0]
        print(f"  マッチ表現: {expr.text!r} ({expr.emotion})")

# ── 感情のみ検出（他の処理を無効化してコスト削減）──────────────
print("\n\n=== 感情専用モード ===")
emotion_only = Analyzer(
    enable_semantic_chunk=False,
    enable_intent=False,
    enable_rag=False,
)
result = emotion_only.analyze("最高すぎて泣ける")
emo = result.emotion
print(f"  テキスト: {result.text.original!r}")
print(f"  primary={emo.primary}  polarity={emo.polarity}  intensity={emo.intensity:.2f}")
