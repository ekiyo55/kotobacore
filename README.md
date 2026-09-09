# KotobaCore

[![CI](https://github.com/ekiyo55/kotobacore/actions/workflows/ci.yml/badge.svg)](https://github.com/ekiyo55/kotobacore/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/kotobacore)](https://pypi.org/project/kotobacore/)
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
  └─ 正規化 N1 文字 (NFKC / SNS表現保持) → N2 表記 (normalization.csv)
       ※ 正規化で文字数が変わっても、出力の全 span は原文の位置を指す (位置写像)
       └─ トークナイズ — Karuizawa (外部依存ゼロの内蔵トークナイザー)
          v0.2〜 格子+Viterbi の一発分割 (辞書表層/文法形態素/活用組み立て/
          交ぜ書き複合語をノード提案し、接続コスト付き最良経路探索で確定)
            └─ Core: 文・段落境界 / 節分割・否定スコープ・逆接重み / Entity (辞書+パターン+日時+数量)
                     / 述語項構造 → Relation・Event (v0.5) / 感情・評価語マッチ + 宛先付け / 句チャンク
                 ├─ Emotion   感情検出 + Plutchik 8軸 (holder / about 付き)
                 ├─ Sentiment 評価語のみの極性 (感情語は affect_polarity に分離、target 付き)
                 ├─ Intent    意図分類 (SNS 向け + Query 向け体系)
                 ├─ Topic     主題 (エンティティ + 頻出名詞、v0.5)
                 └─ RAG       キーワード抽出 / Query IR / 文書チャンク / Reranking 特徴量・参照リトリーバ (v0.5)
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
| `entity.csv` | 1802 | 固有表現（人名・ブランド・組織・地名・作品・サービス等）と TOPIC（一般概念名詞: 円安 / 値上げ / すもも 等）。`aliases` 列で別名表記も認識 | surface, type, normalized, aliases, priority, keep_as_unit |
| `emotion.csv` | 521 | 感情語。11 カテゴリ（joy / sadness / admiration / refusal / moved / anger / anxiety / exaggeration / anticipation / irritation / agreement）を Plutchik 8 軸へマップ | surface, base_emotion, polarity, intensity, keep_as_unit |
| `slang.csv` | 203 | SNS・ネットスラング（草 / しぬw / ワロタ 等） | surface, normalized, meaning, emotion, category, intensity, keep_as_unit |
| `stopwords.csv` | 113 | チャンク・キーワードから除外する助詞・副詞・接続詞 | surface, category |
| `normalization.csv` | 182 | 表記ゆれ正規化（法人略号 / 記号 / 引用符 / 旧字体→新字体 / カタカナ長音 サーバ→サーバー / ヴ→バ行）。最長一致・冪等 | source, target, type |
| `sentiment.csv` | 215 | 感情カテゴリを持たない評価語（いまいち / 微妙 / 使いやすい / 高すぎる 等）。Sentiment モジュール用、否定で極性反転 | surface, polarity, intensity |
| `synonym.csv` | 218 | 同義語グループ（顧客\|クライアント\|お客様 等）。`Analyzer.canonical()` / `synonyms()` | canonical, synonyms, domain |
| `intent_rules.csv` | 9 | 意図分類ルール（pricing_complaint / support_request / positive_feedback / negative_feedback / agreement / admiration / desire / question / request） | intent, pattern, score, priority |
| `emotion_examples.csv` | 17 | 例文ベース感情マッチ（surface 一致しない文の確信度を補強）の手書きシード | surface, base_emotion, plutchik_emotion, polarity, intensity, example |
| `Japanese-SNS-Emotion-Examples-v1.txt` | 546 語 / 約 2,746 例文 | SNS 感情例文集（喜び・悲しみ・怒り・恐れ・驚き等）。例文ベースの Jaccard 類似度マッチに使用 | word, emotion, intensity, context, examples, emojis |

`entity.csv` の内訳は組織 571（日本の主要企業 400 社超・行政機関・国際機関）/ トピック 363（歴史・宗教・言語・食・祝日等）/ 地名 279（国名 117 含む）/ 人名 272 / ブランド 195 / 作品 59 / サービス 39 ほか。

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

### トークン粒度 (`granularity`)

既定の `coarse` は意味単位 (思い出した / 締め切り) を 1 トークンに保ちます。
言語モデルの語彙を作る用途などで細かい表層が欲しい場合は `fine` を指定すると、
組み立てた動詞・形容詞・交ぜ書き複合語・未知ひらがなランを
語幹 / 送り仮名 / 活用語尾に分解します (辞書エンティティは割りません)。

```python
Analyzer(granularity="fine").tokenize("思い出した")
# 思(動詞-語幹) い(送り仮名) 出(動詞-語幹) した(動詞-活用語尾)
```

`analyze()` の chunks / emotion / intent / rag は粒度に関係なく coarse で計算されます。

### N4 語形正規化 (v0.6.3)

```python
[(t.surface, t.dictionary_form, t.conjugation_type, t.conjugation_form) for t in a.tokenize("食べさせられなかったので待っています")]
# [('食べさせられなかったので', '食べる', '一段', '使役-受身-否定-過去-接続-理由'), ('待っています', '待つ', '五段', '進行-丁寧')]
[(t.surface, t.normalized) for t in a.tokenize("申込みと見積と引落")]   # 送り仮名揺れ → 本則形 (okurigana.csv)
# [('申込み', '申し込み'), ('と', 'と'), ('見積', '見積もり'), ('と', 'と'), ('引落', '引き落とし')]
```

辞書なしの規則で原形・活用型（五段 / 一段 / カ変 / サ変 / 形容詞 / 形容動詞）・活用形を付けます。辞書でしか決まらない曖昧（走った → 走る／走つ／走う）は最頻パターンで解き `五段?` と表示します。

## Entity / 宛先 / 文書 / Query IR (v0.4)

```python
import datetime
from kotobacore import Analyzer

a = Analyzer(reference_date=datetime.date(2026, 9, 8))
r = a.analyze("株式会社山田商事の佐藤部長は10月5日に45億円の予算を発表した。コーヒーはいまいちだけどケーキは神。")
[(e.surface, e.type, e.value) for e in r.entities]
# [('株式会社山田商事','ORGANIZATION',None), ('佐藤部長','PERSON',None), ('10月5日','DATE','2026-10-05'), ('45億円','MONEY',4500000000.0)]
[(s.text, s.polarity, s.target_text) for s in r.sentiment.expressions]
# [('いまいちだ','negative','コーヒー'), ('神','positive','ケーキ')]

q = a.analyze_query("東京支店の2025年度の売上目標はいくら？")
q.intent, q.answer_type, q.target, q.constraints
# ('search_value', 'MONEY', '売上目標', {'organization': ['東京支店'], 'time': ['FY2025']})

d = a.analyze_document(open("report.md", encoding="utf-8").read())
d.paragraphs, d.sentences, d.document_chunks   # 階層 IR と検索用チャンク
```

```python
# v0.6.2: 文書内の Entity 共参照 (FR-034) — 田中太郎さん / 田中さん / 田中、株式会社北斗物流 / 北斗物流 / 北斗 / 同社 を同じ canonical_id に
d = a.analyze_document("株式会社北斗物流は新倉庫を開設した。\n北斗は来年も投資する。\n同社の社長は佐藤氏だ。")
[(e.surface, e.source, e.canonical_id) for e in d.entities if e.type == "ORGANIZATION"]
# [('株式会社北斗物流','pattern','e1'), ('北斗','coreference','e1'), ('同社','coreference','e1')]
from kotobacore.core.coreference import coreference_clusters
coreference_clusters(d.entities)   # 代表 (aliases 付き) を先頭にしたクラスタ一覧

# v0.5: 述語項構造 → Event / Relation、Reranking
r = a.analyze("株式会社山田商事は2025年度に大阪支社を設立した。")
r.events[0]      # Event(type='FOUND', agent_text='株式会社山田商事', object_text='大阪支社', time_text='2025年度', ...)
r.relations[0]   # Relation(source_text='株式会社山田商事', relation='FOUND', role='object', target_text='大阪支社', ...)

from kotobacore.rag import ChunkView, rerank, InMemoryRetriever
views = [ChunkView.from_chunk(c, d) for c in d.document_chunks]
rerank(q, views)                       # [(chunk_index, score, {entity_match, keyword_overlap, intent_match, time_match, ...}), ...]
ret = InMemoryRetriever(embed=my_embedding_fn)   # Embedding は外部モデルを注入
ret.index("doc1", d); ret.search(q, k=3)
```

CLI: `kotobacore query "…"` / `kotobacore chunk report.md --max-chars 400` / `kotobacore analyze --document --file report.md`

## Vocab — 語彙表と Token ID (v0.6、任意モジュール)

日本語 LM を自作するときの語彙。`fine` 粒度（語幹 / 送り仮名 / 活用語尾）から語彙表を作り、テキストを整数 id 列に符号化・復号します。
語彙データはパッケージに同梱しません。IR は vocab なしで完全です。参照語彙（fine / coarse、`kotobacore-vocab-1.0` 形式）は別リポジトリ `kotobacore-vocab` で配布します。

```python
from kotobacore.vocab import build_vocab, extend_vocab, VocabEncoder, vocab_report

vocab = build_vocab(open("corpus.txt", encoding="utf-8"), min_freq=2)   # id 0-9 は <pad> <unk> <bos> <eos> <sep> <mask> <cls> <nl> <sp> <reserved>
vocab.save("vocab.json")                                                 # 以降は頻度降順。コーパスの全文字も語彙に入る（未知語は文字へフォールバック）
enc = VocabEncoder(vocab)
ids = enc.encode("東京に行った。\n私は走った", add_special=True)         # [<bos>, 東京, に, 行, った, 。, <nl>, 私, は, 走, った, <eos>]
enc.decode(ids)                                                          # '東京に行った。\n私は走った'（正規化後テキスト）
extend_vocab(vocab, more_texts)                                          # 追記のみ。既存 id は変わらない
vocab_report(vocab, held_out_texts)                                      # coverage / OOV / <unk> 率 / 頻度分布 / 汚染候補（記号連結・同字反復・半角カナ・異常長…）
```

CLI: `kotobacore vocab build corpus/ --out vocab.json --min-freq 2` / `kotobacore vocab encode "…" --vocab vocab.json` / `kotobacore vocab decode "[2, 15, 7]" --vocab vocab.json` / `kotobacore vocab report held_out/ --vocab vocab.json --md report.md`

## HTTP API (v0.6.1、extra `api`)

```bash
pip install "kotobacore[api]"
KOTOBACORE_API_TOKEN=secret kotobacore serve --port 8590 --rate-limit 120   # /docs に OpenAPI
curl -s -X POST http://127.0.0.1:8590/query -H "Authorization: Bearer secret" \
     -H "Content-Type: application/json" -d '{"text":"東京支店の今年度の売上目標はいくら？","reference_date":"2026-09-08"}'
```

`POST /analyze`（`document` / `reference_date` / `semantic_only`）・`/query`・`/chunk`・`/tokenize`、`GET /health` `/version`。
Bearer トークン認証とクライアント別レート制限は任意（環境変数または `--token` / `--rate-limit`）。アクセスログは出さず、エラー応答に入力文を含めません。
エラーは `{"error": {"code": "E701 unauthorized", "message": "…"}}` の形（E1xx 入力 / E7xx API）。Python からは `from kotobacore.api import create_app` で FastAPI アプリを組み込めます。

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
  "sentiment": {
    "polarity": "negative",
    "affect_polarity": "negative",
    "intensity": 0.7,
    "expressions": [{"text": "高すぎ", "polarity": "negative", "target_text": "課金", "begin": 10, "end": 13, "negated": false}]
  },
  "entities": [
    {"id": "e1", "type": "SERVICE", "surface": "クラウドAPI", "begin": 0, "end": 7, "source": "dictionary"}
  ],
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
kotobacore tokenize "思い出した" --granularity fine
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

実測（`tools/benchmark/compare_baselines.py`、人手アノテーション 100 文の分割境界、速度は 300 文 × 3 周 warm。gold は KotobaCore の意味単位なので短単位の形態素解析器は R が高く P が低く出ます）:

| tool | boundary F1 | ms/文 | 辞書サイズ |
|---|---|---|---|
| KotobaCore coarse (Karuizawa 2.4) | 0.894 | 0.27 | 0.3 MB |
| SudachiPy C | 0.875 | 0.04 | 218 MB |
| janome (IPADIC) | 0.865 | 0.71 | 211 MB |



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

**v1.0.0**（2026-09-09、**IR schema 1.0 凍結・全構成要素の版を 1.0 に統一**。Vocab モジュール・HTTP API・Entity 共参照・N4 語形正規化〈動詞原形＋活用型/活用形、送り仮名揺れ〉・互換性マトリクス／旧 import 非推奨化・感情体系 surprise/trust/disgust と意図 inform/share_experience・括弧内固有名・人手評価セット由来の辞書拡充・§9 エラー処理〈回復可能エラーは IR.errors に積んで継続〉）。人手アノテーション 300 文（確定版 annotated_v1）で Sentiment 83% / Emotion 84% / Intent 70% / Entity F1 0.86。NFR-001: 10 万文 110 秒（908 文/s）、1 文平均 1.1 ms、1 万字文書 0.72 秒。6500例文の品質評価で 極性正確度 97% 台 / 処理エラー 0件。人手アノテーション実文 300 文 (下書き) で
Entity F1 0.66・分割境界 F1 0.91・評価極性 63%。RAG 検索評価: 自作 24 文書・200 問 (妨害込み 447 チャンク) で MRR 0.769 → 0.846、実務文書 30 件 (5,174 チャンク・120 問) で 0.570 → 0.720
(コードフェンス・番号リストを壊さないチャンク + 見出しパス/導入文の文脈 + Query IR + 制約フィルタ + 再ランク〈回答の形一致を含む〉)。外部 Embedding (e5-base) とのハイブリッドでは 実務 0.777 / 自作 0.868。処理速度は 1文あたり平均 1〜3ms（外部依存ゼロ）。**352 テスト全 PASS**。

v0.5 の主な変更: 述語項構造 → Event / Relation（係り受け解析器なし）、Topic モジュール、Reranking 特徴量と参照リトリーバ
（インメモリ / pgvector SQL）、動詞否定、評価語のラティス登録。v0.4: Entity 層、宛先付き評価・感情、文書階層、Query IR、Semantic Chunking。

v0.3 の主な変更: パッケージを Core (`kotobacore.core`) と IR 上のモジュール
(`kotobacore.modules` = emotion / sentiment / intent) に再配置（旧 import パスは維持）、
正規化の位置写像（出力 span は常に原文基準）、Sentiment モジュールの分離と評価語辞書、
否定スコープの Core 移設、同義語辞書、人手アノテーション評価ランナー。

v0.2 の主な変更: Karuizawa の格子+Viterbi 一発分割（bigram 接続コストで
「すもももももももものうち」も完全解）、否定スコープ処理（好きじゃない → negative）、
節分割による逆接考慮（〜でしたが成功しました → positive）、Aho-Corasick 統一マッチ層。
詳細は [CHANGELOG](CHANGELOG.md) を参照。

---

## ドキュメント

- `docs/API.md` — Python API / CLI / HTTP API（認証・レート制限・エラー形）
- `docs/openapi.json` — HTTP API の OpenAPI 3.1（`tools/gen_openapi.py` で生成、`/docs` と同じ内容）
- `docs/IR_SCHEMA.md` — Semantic IR の全フィールド（`tools/gen_schema_doc.py` で dataclass から生成。schema 1.0）
- `docs/TOKENIZATION.md` — 分割基準（coarse = 意味単位 / fine = 語幹・送り仮名・活用語尾）と既知の癖
- `CHANGELOG.md` — 版ごとの変更と計測値

## 互換性マトリクス (v1.0.0、`kotobacore version --matrix` の出力)

1.0.0 で全構成要素を 1.0 に統一しました（IR schema は凍結。旧番号の系譜は各モジュールのコメントと `resources/dict/versions.json` の `history` に残しています）。

| 対象 | 版 | 互換ポリシー |
|---|---|---|
| KotobaCore 本体 | 1.0.0 | SemVer。1.0 以降、破壊変更はメジャーのみ |
| IR Schema | 1.0（凍結） | フィールド追加は後方互換、削除・型変更はメジャー |
| Tokenizer (Karuizawa) | 1.0 | 分割結果が変わる変更で上げる |
| 辞書セット | 1.0 | 追加はパッチ、意味変更はマイナー。各 CSV の版は resources/dict/versions.json |
| Intent / Emotion / Sentiment / Topic module | 1.0 | モジュール単位で独立 |
| Vocabulary format | kotobacore-vocab-1.0 | 同一メジャー内は追記のみ。語彙データは非同梱 |
| HTTP API | 1.0 | パス・レスポンス形の破壊変更でメジャー |
| 旧 import パス | deprecated 0.6.4 → removed 1.1 | kotobacore.schema / normalizer / tokenizer / semantic / emotion / intent / clause / matching |

解析結果の `meta.components` に tokenizer / dictionary_set / modules の版が刻まれます（再現性）。旧 import パスは `DeprecationWarning` を出しつつ v1.0 まで動作し、v1.1 で削除します。`kotobacore.compat`（Karuizawa 互換 API）は継続します。

## ライセンス

Apache License 2.0
