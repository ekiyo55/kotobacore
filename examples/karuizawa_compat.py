"""KotobaCore — Karuizawa tokenizer compatibility API example.

KotobaCore ships a lightweight built-in tokenizer called Karuizawa.
The `kotobacore.compat` module exposes a morpheme-style API so that
code originally written for SudachiPy can be adapted with minimal changes.

Karuizawa splits on Unicode character-category boundaries:
  KANJI / KATAKANA / HIRAGANA / LATIN / DIGIT / SYMBOL

Unlike SudachiPy, Karuizawa has zero external dependencies and requires
no dictionary download.
"""

from kotobacore.compat import KaruizawaTokenizer, TokenMode

tokenizer = KaruizawaTokenizer()

# ── 基本トークン化 ────────────────────────────────────────────
text = "OpenAI APIの課金高すぎてしぬw"
morphemes = tokenizer.tokenize(text, TokenMode.C)

print(f"入力: {text!r}")
print(f"トークン数: {len(morphemes)}")
print()
print(f"{'surface':<14} {'dictionary_form':<14} {'reading':<12} pos")
print("-" * 60)
for m in morphemes:
    pos_str = "-".join(m.part_of_speech())
    print(
        f"{m.surface():<14} "
        f"{m.dictionary_form():<14} "
        f"{m.reading_form():<12} "
        f"{pos_str}"
    )

# ── 文字カテゴリ境界の確認 ──────────────────────────────────
print("\n\n=== 文字カテゴリ境界の確認 ===")
samples = [
    "東京Tokyo2024",           # KANJI+LATIN+DIGIT
    "カタカナhiraganaＡBC",     # KATAKANA+HIRAGANA+LATIN(全角)
    "価格：1,980円（税込）",    # KANJI+SYMBOL+DIGIT+KANJI+SYMBOL
]

for s in samples:
    morphemes = tokenizer.tokenize(s, TokenMode.C)
    surfaces = [m.surface() for m in morphemes]
    print(f"  {s!r} → {surfaces}")

# ── span (begin/end) の確認 ────────────────────────────────
print("\n\n=== span 確認 ===")
text = "東京都に行く"
morphemes = tokenizer.tokenize(text, TokenMode.C)
for m in morphemes:
    print(f"  [{m.begin():2d}:{m.end():2d}] {m.surface()!r}")

# ── TokenMode (A/B/C はすべて同じ結果) ───────────────────────
print("\n\n=== TokenMode (A=B=C、常に同一粒度) ===")
text = "自然言語処理"
for mode in (TokenMode.A, TokenMode.B, TokenMode.C):
    morphemes = tokenizer.tokenize(text, mode)
    surfaces = [m.surface() for m in morphemes]
    print(f"  Mode {mode}: {surfaces}")
