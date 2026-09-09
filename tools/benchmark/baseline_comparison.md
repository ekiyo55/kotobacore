# Baseline comparison — KotobaCore 0.6.4 (Karuizawa 2.4)

gold: 人手アノテーション 100 文の分割 (KotobaCore coarse 基準)、速度: 300 文 × 3 周 (warm)

| tool | boundary P | R | F1 | tokens/sentence | ms/sentence | tokens/s | note |
|---|---|---|---|---|---|---|---|
| KotobaCore coarse (Karuizawa 2.4) | 0.8815 | 0.906 | 0.8936 | 10.85 | 0.269 | 40409 | 意味単位 (行った 1 語)。辞書同梱 CSV、依存ゼロ |
| KotobaCore fine | 0.7515 | 0.9338 | 0.8328 | 13.53 | 0.256 | 52872 | 語幹 / 送り仮名 / 活用語尾 (LM 語彙用) |
| janome (IPADIC) | 0.763 | 0.9971 | 0.8645 | 13.85 | 0.708 | 19547 | 純 Python 形態素解析器、IPADIC 内蔵 |
| SudachiPy A | 0.763 | 1.0 | 0.8656 | 14.0 | 0.034 | 409032 | SudachiDict core, 分割単位 A |
| SudachiPy B | 0.7755 | 1.0 | 0.8735 | 13.78 | 0.044 | 313048 | SudachiDict core, 分割単位 B |
| SudachiPy C | 0.7772 | 1.0 | 0.8746 | 13.72 | 0.044 | 311638 | SudachiDict core, 分割単位 C |

## footprint

| component | size |
|---|---|
| KotobaCore dict (resources/dict) | 0.3 MB |
| janome package | 211.3 MB |
| sudachidict_core | 217.5 MB |
| sudachipy | 3.4 MB |

## not run

- (解消 2026-09-09) sentiment / emotion baselines は mooma (Linux) の使い捨て venv で実施 → `sentiment_baselines.md` (`compare_sentiment_baselines.py`)

注: gold は KotobaCore の粗い意味単位 (行った / 美味しかった = 1 語) なので、短単位の形態素解析器は再現率が高く精度が低く出る。
境界再現率 (R) は「その道具の出力に gold の境界が含まれているか」で、細かく切る道具ほど有利。F1 は基準の差を含んだ比較。

## sentiment / emotion (2026-09-09, KotobaCore 1.0.0, mooma で実施)

| tool | polarity acc (all) | polarity acc (polarized only) | emotion acc | canary FP | ms/sentence | note |
|---|---|---|---|---|---|---|
| KotobaCore 1.0.0 (同梱辞書のみ = pip install の状態、mooma で実行) | 83.0% (n=300) | 71.6% (n=102) | 83.5% (n=182) | 0.0% (n=22) | 2.109 | 辞書同梱 CSV、依存ゼロ。宛先付き (target / holder / about) だが本表は文単位のみ |
| KotobaCore 1.0.0 (+NRC 939 語、ローカル dic/ 併用) | 83.0% (n=300) | 71.6% (n=102) | 84.1% (n=182) | 0.0% (n=22) | 1.324 | NRC Emotion Intensity Lexicon はライセンス上非同梱。README の人手評価値 (感情 84.1%) はこの構成 |
| oseti 0.4 (評価極性辞書 + MeCab/ipadic) | 47.7% (n=300) | 48.0% (n=102) | — | — | 2.021 | 文ごとのスコア [-1, 1] の平均符号。0 / 該当なし = neutral |
| pymlask 0.3 (ML-Ask 感情辞書 + MeCab/ipadic) | 61.0% (n=300) | 23.5% (n=102) | 23.1% (n=182) | 27.3% (n=22) | 0.938 | orientation → 極性、representative 感情を ML_ASK_MAP で gold 体系に写像 |
| asari 0.2 (TF-IDF + 線形分類、二値) | 26.3% (n=300) | 77.5% (n=102) | — | — | 3.517 | positive / negative しか返さない |
| asari 0.2 (TF-IDF + 線形分類、二値) / 確信度 < 0.75 → neutral | 46.3% (n=300) | 62.7% (n=102) | — | — | 3.505 | positive / negative しか返さないので確信度で neutral を補う |

詳細と注記は `sentiment_baselines.md` / `sentiment_baselines.json`。
