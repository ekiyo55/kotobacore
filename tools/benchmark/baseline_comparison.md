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

- sentiment/emotion baselines (oseti, asari…): MeCab の Windows DLL がロードできず未実施 (mecab-python3 ImportError)

注: gold は KotobaCore の粗い意味単位 (行った / 美味しかった = 1 語) なので、短単位の形態素解析器は再現率が高く精度が低く出る。
境界再現率 (R) は「その道具の出力に gold の境界が含まれているか」で、細かく切る道具ほど有利。F1 は基準の差を含んだ比較。
