# KotobaCore

[![CI](https://github.com/ekiyo55/kotobacore/actions/workflows/ci.yml/badge.svg)](https://github.com/ekiyo55/kotobacore/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

[English](README_en.md) | **日本語**

日本語テキストの意味を構造化データに変換するセマンティックエンジン。  
LLM前処理・RAG・SNS解析・AIエージェント入力に使えます。

---

## 何ができるか

```python
from kotobacore import Analyzer

result = Analyzer().analyze("クラウドAPIの課金高すぎてしぬw")
```

```
chunks   : ["クラウドAPI", "課金高すぎ", "しぬw"]
emotion  : anger / negative  (Plutchik: anger+disgust)
intent   : pricing_complaint
keywords : ["クラウドAPI", "課金"]
```

単なるトークナイザーではなく、**感情・意図・RAGキーワードまで一括で返す**のが特徴です。

---

## パイプライン

```
入力テキスト
  └─ 正規化 (NFKC / SNS表現保持)
       └─ トークナイズ (外部依存ゼロの内蔵トークナイザー)
            └─ セマンティックチャンク生成
                 ├─ 感情検出 + Plutchik 8軸マッピング
                 ├─ 意図分類
                 └─ RAGキーワード抽出
```

---

## 感情モデル — Plutchik の感情の輪

KotobaCore は心理学者 Robert Plutchik が提唱した **8基本感情モデル** をベースにしています。  
怒り・恐れ・喜び・悲しみ・信頼・嫌悪・驚き・期待の8軸で感情を分類し、  
テキストの感情を `primary / polarity / plutchik_axes` として構造化して返します。

| Plutchik 軸 | KotobaCore カテゴリ | 例 |
|---|---|---|
| joy | joy / moved / admiration | 嬉しい, 感動した, 誇らしい |
| anger | anger / refusal | ムカつく, 無理, 許せない |
| sadness | sadness / anxiety | 悲しい, 不安, 心配 |
| surprise | surprise / exaggeration | まじか, やばい, しぬw |
| anticipation | anticipation / desire | 楽しみ, したい, 欲しい |
| trust | admiration | 尊い, 信頼, 神対応 |
| fear | anxiety | 怖い, 恐怖, ゾッとした |
| disgust | refusal | 最悪, 気持ち悪い, 無理 |

---

## 内蔵辞書

KotobaCore の判定は機械学習モデルではなく、**同梱の人手メンテナンス辞書（プレーンな CSV）** に基づきます。
モデルのダウンロードや学習は不要で、CSV を編集するだけで語彙・ルールを追加・調整できます（`resources/dict/`）。

| 辞書ファイル | 件数 | 役割 | 主な列 |
|---|---:|---|---|
| `entity.csv` | 701 | 固有表現（人名・ブランド・組織・地名・作品・サービス等）。`aliases` 列で別名表記も認識 | surface, type, normalized, aliases, priority, keep_as_unit |
| `emotion.csv` | 507 | 感情語。11 カテゴリ（joy / sadness / admiration / refusal / moved / anger / anxiety / exaggeration / anticipation / irritation / agreement）を Plutchik 8 軸へマップ | surface, base_emotion, polarity, intensity, keep_as_unit |
| `slang.csv` | 203 | SNS・ネットスラング（草 / しぬw / ワロタ 等） | surface, normalized, meaning, emotion, category, intensity, keep_as_unit |
| `stopwords.csv` | 113 | チャンク・キーワードから除外する助詞・副詞・接続詞 | surface, category |
| `normalization.csv` | 21 | 表記ゆれ正規化（(株) → 株式会社 等） | source, target, type |
| `intent_rules.csv` | 9 | 意図分類ルール（pricing_complaint / support_request / positive_feedback / negative_feedback / agreement / admiration / desire / question / request） | intent, pattern, score, priority |
| `emotion_examples.csv` | 17 | 例文ベース感情マッチ（surface 一致しない文の確信度を補強）の手書きシード | surface, base_emotion, plutchik_emotion, polarity, intensity, example |
| `Japanese-SNS-Emotion-Examples-v1.txt` | 546 語 / 約 2,746 例文 | SNS 感情例文集（喜び・悲しみ・怒り・恐れ・驚き等）。例文ベースの Jaccard 類似度マッチに使用 | word, emotion, intensity, context, examples, emojis |

`entity.csv` の内訳は人名 230 / ブランド 140 / 組織 132 / 地名 89 / 作品 59 / サービス 39 ほか。

`Japanese-SNS-Emotion-Examples-v1.txt` も `resources/dict/` に同梱され、デフォルトで読み込まれます（外部辞書なしでも例文マッチが効きます）。
各行の `examples`（「、」区切りの複数例文）が展開され、入力文との bigram Jaccard 類似度で感情の confidence を補強します。

### 任意の外部辞書（NRC、非同梱）

唯一の **非同梱** 辞書が **NRC Emotion Intensity Lexicon**（約 9,800 語 / 8 Plutchik 感情の強度辞書）です。
`dic/`（環境変数 `KOTOBACORE_DIC_DIR` で指定）に置くと、内部辞書に無い感情語を **検出語彙として追加** します
（内部辞書 `lex_weight=1.0` に対し外部は `0.5` の低めの重みで、文学的・稀少語を補完）。**無くても内蔵辞書だけで動作します。**

感情の confidence は `lex_weight × 0.5 + ex_sim × 0.3 + intensity × 0.2` で算出され、
NRC は第1項（検出語彙）、同梱の SNS 例文は第2項（類似度）に効きます。

#### NRC 辞書の入手方法

> **⚠️ ライセンス注意**: NRC Emotion Intensity Lexicon は **再配布が禁止** されているため本リポジトリには含まれません。
> 各自で公式ページから入手してください。**非商用の研究用途は無償**ですが、**商用利用には NRC の商用ライセンスが別途必要** です。
> 利用時は下記の引用と帰属表示が求められます。必ず[公式ページの利用規約](https://saifmohammad.com/WebPages/AffectIntensity.htm)をご自身で確認してください。

1. 公式ページ **NRC Emotion/Affect Intensity Lexicon** から辞書を入手します（多言語自動翻訳版に日本語が含まれます）。
   - https://saifmohammad.com/WebPages/AffectIntensity.htm
2. 日本語訳データを次の **タブ区切り (TSV) 4 列** 形式に整え、`dic/` に配置します。
   ```
   English Word<TAB>Emotion<TAB>Emotion-Intensity-Score<TAB>Japanese Word
   ```
   - ファイル名: `dic/Japanese-NRC-Emotion-Intensity-Lexicon-v1.txt`
   - `Emotion` は 8 軸（anger / anticipation / disgust / fear / joy / sadness / surprise / trust）
3. `dic/` の場所は次の順で探索されます: 環境変数 `KOTOBACORE_DIC_DIR` → `<project>/dic` → `<project>/../dic`。

**引用（必須）**:

```bibtex
@inproceedings{LREC18-AIL,
  author    = {Mohammad, Saif M.},
  title     = {Word Affect Intensities},
  booktitle = {Proceedings of the 11th Edition of the Language Resources
               and Evaluation Conference (LREC-2018)},
  year      = {2018},
  address   = {Miyazaki, Japan}
}
```

**帰属表示の例**: "This product makes use of the NRC Emotion Intensity Lexicon, created by Saif M. Mohammad at the National Research Council Canada."

```python
from kotobacore.dictionary import load_user_bundle
bundle = load_user_bundle()   # 内蔵 seed + 同梱 SNS 例文 + (あれば) dic/ の NRC を統合
```

---

## インストール

```bash
git clone https://github.com/ekiyo55/kotobacore.git
cd kotobacore
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .[dev,ui]
```

---

## Python API

```python
from kotobacore import Analyzer

result = Analyzer().analyze("クラウドAPIの課金高すぎてしぬw")
print(result.to_json())
```

## 出力 JSON 構造

```json
{
  "chunks": [
    {"id": 0, "text": "クラウドAPI", "type": "service",      "score": 0.96},
    {"id": 1, "text": "課金高すぎ",  "type": "complaint",    "score": 0.88},
    {"id": 2, "text": "しぬw",       "type": "slang_emotion","score": 0.88}
  ],
  "emotion": {
    "primary": "anger",
    "polarity": "negative",
    "intensity": 0.82,
    "plutchik_axes": ["anger", "disgust"]
  },
  "intent": {"label": "pricing_complaint", "score": 0.85},
  "rag": {
    "keywords": ["クラウドAPI", "課金"],
    "search_query": "クラウドAPI 課金",
    "summary_hint": "pricing complaint about cloud API"
  }
}
```

---

## CLI

```bash
kotobacore analyze "今日のランチが絶品だった" --pretty
kotobacore tokenize "東京都に行った"
kotobacore version
```

---

## Demo UI

```bash
streamlit run tools/demo_ui/streamlit_app.py
# → http://localhost:8501
```

公開デモ: https://kotobacore.mooma.style/

---

## 他ライブラリとの比較

| ライブラリ | トークナイズ | 感情解析 | 意図分類 | RAGキーワード | 外部依存 |
|---|:---:|:---:|:---:|:---:|---|
| MeCab / SudachiPy | ✅ | ❌ | ❌ | ❌ | C++/辞書 |
| GiNZA (spaCy) | ✅ | ❌ | ❌ | ❌ | spaCy モデル |
| oseti / asari | ❌ | ポジ/ネガのみ | ❌ | ❌ | 辞書/ML |
| BERT系 (transformers) | ✅ | ✅ | △ | ❌ | モデル数GB |
| **KotobaCore** | ✅ | **Plutchik 8軸** | **✅** | **✅** | **ゼロ** |

KotobaCoreが埋めているのは「感情・意図・RAGキーワードを一つのパイプラインで構造化JSON化する」領域です。

---

## ステータス

v0.1.11 pre-alpha。5000例文の品質評価で 感情正確度 95.2% / 極性正確度 96.1% / 意図正確度 68.1%、処理エラー 0件。
処理速度はサーバー実機で 1文あたり平均 3.77ms（p99 21.83ms、外部依存ゼロ）。149 テスト全 PASS。

---

## ライセンス

Apache License 2.0
