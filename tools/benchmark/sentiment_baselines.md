# Sentiment / emotion baseline comparison — KotobaCore 1.0.0

gold: 人手アノテーション v1 300 文 (5 ジャンル)。極性 = 表現の多数決 (無し = None)、感情 = gold ラベルのいずれかに一致で正解。速度 = 文あたり ms (warm, best of 3、ベースラインは mooma サーバー、+NRC 行のみローカル PC)

| tool | polarity acc (all) | polarity acc (polarized only) | emotion acc | canary FP | ms/sentence | note |
|---|---|---|---|---|---|---|
| KotobaCore 1.0.0 (同梱辞書のみ = pip install の状態、mooma で実行) | 83.0% (n=300) | 71.6% (n=102) | 83.5% (n=182) | 0.0% (n=22) | 2.109 | 辞書同梱 CSV、依存ゼロ。宛先付き (target / holder / about) だが本表は文単位のみ |
| KotobaCore 1.0.0 (+NRC 939 語、ローカル dic/ 併用) | 83.0% (n=300) | 71.6% (n=102) | 84.1% (n=182) | 0.0% (n=22) | 1.324 | NRC Emotion Intensity Lexicon はライセンス上非同梱。README の人手評価値 (感情 84.1%) はこの構成 |
| oseti 0.4 (評価極性辞書 + MeCab/ipadic) | 47.7% (n=300) | 48.0% (n=102) | — | — | 2.021 | 文ごとのスコア [-1, 1] の平均符号。0 / 該当なし = neutral |
| pymlask 0.3 (ML-Ask 感情辞書 + MeCab/ipadic) | 61.0% (n=300) | 23.5% (n=102) | 23.1% (n=182) | 27.3% (n=22) | 0.938 | orientation → 極性、representative 感情を ML_ASK_MAP で gold 体系に写像 |
| asari 0.2 (TF-IDF + 線形分類、二値) | 26.3% (n=300) | 77.5% (n=102) | — | — | 3.517 | positive / negative しか返さない |
| asari 0.2 (TF-IDF + 線形分類、二値) / 確信度 < 0.75 → neutral | 46.3% (n=300) | 62.7% (n=102) | — | — | 3.505 | positive / negative しか返さないので確信度で neutral を補う |

注: gold の極性は「評価表現のある文だけ」に付いている (残りは None = neutral 扱い)。二値分類器は None の文で必ず外すので、polarized only 列も併記。
ML-Ask の 10 感情は gold 体系 (Plutchik 8 + irritation / anxiety / admiration / moved / refusal / agreement) と一対一でないため、ML_ASK_MAP の多対多写像で「いずれか一致」を正解にしている (ML-Ask 有利)。
本表は文単位の極性・主感情のみ。KotobaCore の宛先付き評価 (target / holder / about) は他ライブラリに対応物が無く比較対象外。
