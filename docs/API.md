# KotobaCore API ドキュメント（FR-090〜092）

対象: KotobaCore 0.6.x。Python API・CLI・HTTP API の 3 つの入口は同じ Analyzer を使い、同じ Semantic IR（`docs/IR_SCHEMA.md`）を返します。

## 1. Python API（FR-091）

```python
from kotobacore import Analyzer

a = Analyzer()                                   # 既定: 4 モジュール (intent / emotion / sentiment / topic) 有効、coarse 分割
r = a.analyze("今日のランチ、マジで美味しかった😋")   # 1 文 → AnalysisResult
d = a.analyze_document(markdown_text)             # 文書 → 段落 / 文 / document_chunks / 共参照 (analyze の上位集合)
m = a.analyze_mail(mail_text)                     # メール（v1.1）: 定型句を見分けて、文書全体の意図・極性・キーワードから外す
q = a.analyze_query("東京支店の今年度の売上目標はいくら？")   # → QueryIR (intent / answer_type / target / constraints / keywords)
chunks = a.chunk(markdown_text, max_chars=400)    # → list[DocumentChunk]
tokens = a.tokenize("走った", granularity="fine")  # → list[Token]
terms = a.search_terms("損害賠償請求訴訟が提起された")  # → list[SearchTerm] 検索用索引語（v1.1）
```

**メール（v1.1、schema 1.1）**: `analyze_mail(text)` は `analyze_document` と同じ結果に、各文の `Sentence.boilerplate`（salutation 宛名 / greeting 挨拶 / self_intro 自己紹介 / closing 結び / signature 署名 / quote 引用、本文は None）を付け、定型句の文を文書全体の意図・極性・感情・キーワードから外す。結びの「よろしくお願いいたします」で通知メールが依頼になる、宛名がキーワードの先頭になる、といった誤りを防ぐ。文・トークン・位置は全文をそのまま覆う。CLI は `kotobacore analyze --mail`。定型句と判定するのは文全体が決まり文句のときだけ（「早急に確認をお願いします」は本文）。

**意図の軸（v1.1、schema 1.1）**: `r.intent.axes` は意図のラベルを独立した 4 つの軸に分けたもの。`speech_act`（question / request / statement）、`evaluation`（positive / negative / none、評価語による）、`target`（object / self / none：商品・サービス・組織など対象物への評価か、書き手自身の体験か）、`holder`（speaker / third_party）。業務の区分は使う側で組み合わせる（例: request かつ negative ＝ 苦情）。人手評価 300 文での正答率は 発話の種類 89.7%・評価の極性 82.0%・評価の対象 82.4%（評価が検出された文で）。11 区分の `label` は互換のため従来どおり。

**検索用索引語（v1.1）**: `search_terms(text, lower=True, surface=True, lemma=True, parts=True, synonyms=False)` はキーワード検索（BM25 等）の索引に入れる語を返します。内容語ごとに `token`（正規化形＝エンティティの正式名称・表記ゆれ正規化済み）、`surface`（表層が違うとき）、`lemma`（動詞・形容詞の原形）、`part`（複合語の構成語: 文字種の切れ目・中黒・漢字複合語の分割・中に含まれる辞書語）、`synonym`（任意、synonym.csv）を出し、助詞・助動詞・記号は除きます。各要素は `SearchTerm(term, kind, begin, end, token_id)` で、`begin` / `end` は元テキストの位置（ハイライト用）。例: 損害賠償請求訴訟 → 損害賠償請求訴訟 / 損害 / 賠償 / 請求 / 訴訟、連結EBITDA → 連結ebitda / 連結 / ebitda、D&O保険（辞書の別名）→ 役員賠償責任保険 / d&o保険 / d&o / 保険。IR（schema 1.0）は変えません。

`Analyzer(...)` の主な引数:

| 引数 | 既定 | 意味 |
|---|---|---|
| `enable_emotion` / `enable_sentiment` / `enable_intent` / `enable_topics` | True | モジュールの有効化（§3.4 モジュール契約。無効でも IR は完全） |
| `enable_entities` / `enable_predicates` / `enable_coreference` | True | Core 層の Entity / 述語項 / 文書内共参照 |
| `granularity` | `"coarse"` | `"fine"` で語幹・送り仮名・活用語尾に分解（`docs/TOKENIZATION.md`） |
| `reference_date` | None | 相対日付（今日 / 来年度）を ISO に解決する基準日 |
| `user_dict_path` | None | ユーザー辞書（v1.1）: `entity.csv` 形式の CSV（必須列は `surface` のみ）、同梱形式の CSV を置いたフォルダ、`builtin:dd`（同梱の業種別辞書）。リストで複数可（先が優先）。同梱辞書より優先。別名は `Token.normalized` で正式名称になる |
| `config_path` | None | 設定ファイル（v1.1、YAML）。未指定なら `KOTOBACORE_CONFIG` → `./kotobacore.yaml` → `~/.config/kotobacore/config.yaml` の順に探す。`dictionaries:` に並べた辞書を読み込む（`docs/USER_DICTIONARY.md`） |
| `use_config` | True | False で設定ファイルを探さない |

返り値は dataclass。`r.to_dict()` / `r.to_json(pretty=True)` で JSON。`r.errors` は回復可能エラー（§9、`E1xx〜E4xx`）で、解析は止まりません。bytes を渡すと UTF-8 として復号し、壊れていれば `E101` を積んで続行します。

RAG 層（`kotobacore.rag`）: `ChunkView.from_chunk` / `rerank(query, views)` / `retrieval_features(query)` / `InMemoryRetriever(embed)` / `PgVectorRetriever(...).search_sql(query)`、`HYBRID_ALPHA`（0.3 固定）、`answer_form_match`。Embedding は外部注入（NFR-004）。

Vocab（`kotobacore.vocab`、任意モジュール）: `build_vocab` / `extend_vocab` / `VocabEncoder.encode|decode` / `vocab_report`。語彙ファイルの形式は `kotobacore-vocab-1.0`、メジャー版が違えば `VocabVersionMismatch`（E601）。

版情報: `kotobacore.versions.component_versions()` / `compatibility_matrix_markdown()`。旧 import パス（`kotobacore.schema` など）は 0.6.4 から `DeprecationWarning`、1.1 で削除。`kotobacore.compat`（Karuizawa 互換 API）は継続。

## 2. CLI（FR-090）

```
kotobacore analyze  "テキスト" [--document] [--file] [--pretty] [--semantic-only] [--granularity fine] [--reference-date YYYY-MM-DD] [--no-emotion …]
kotobacore tokenize "テキスト" [--granularity coarse|fine] [--dict user.csv]
kotobacore terms    "テキスト" [--dict user.csv] [--synonyms] [--plain]   # 検索用索引語（v1.1）
kotobacore config   [--config kotobacore.yaml]                         # 有効な設定ファイル・辞書・同梱の業種別辞書（v1.1）
kotobacore normalize "テキスト"
kotobacore query    "検索クエリ" [--reference-date YYYY-MM-DD]
kotobacore chunk    report.md [--max-chars 400] [--min-chars 80]
kotobacore vocab    build corpus/ --out vocab.json [--min-freq 2] [--max-size N] [--extend vocab.json]
kotobacore vocab    encode "テキスト" --vocab vocab.json [--pieces] [--special]
kotobacore vocab    decode "[2, 15, 7]" --vocab vocab.json
kotobacore vocab    report held_out/ --vocab vocab.json [--md report.md] [--json report.json]
kotobacore serve    [--host 127.0.0.1] [--port 8590] [--token …] [--rate-limit N] [--max-chars N] [--reference-date …]
kotobacore eval     annotated|quality [--jsonl …] [--json …] [--md …]
kotobacore version  [--all | --matrix]
```

出力はすべて JSON（`--pretty` で整形）。`eval` はリポジトリの checkout が必要です。

## 3. HTTP API（FR-092）

インストール: `pip install "kotobacore[api]"`（FastAPI + uvicorn）。起動: `kotobacore serve --port 8590`。OpenAPI は `/docs`（Swagger UI）と `/openapi.json`。リポジトリの `docs/openapi.json` は `tools/gen_openapi.py` の出力です。

| method | path | body | returns |
|---|---|---|---|
| GET | `/health` | – | `{"status":"ok"}`（認証不要） |
| GET | `/version` | – | kotobacore / schema / api / backend / auth / rate_limit |
| POST | `/analyze` | `{"text", "document"?: bool, "reference_date"?: "YYYY-MM-DD", "semantic_only"?: bool}` | AnalysisResult JSON |
| POST | `/query` | `{"text", "reference_date"?}` | QueryIR JSON |
| POST | `/chunk` | `{"text", "max_chars"?: 400, "min_chars"?: 80}` | `[DocumentChunk, …]` |
| POST | `/tokenize` | `{"text", "granularity"?: "coarse"\|"fine"}` | `[Token, …]` |

```bash
curl -s -X POST http://127.0.0.1:8590/analyze -H "Content-Type: application/json" \
     -H "Authorization: Bearer $KOTOBACORE_API_TOKEN" \
     -d '{"text":"東京支店の売上目標は3億円だ。","reference_date":"2026-09-08"}'
```

セキュリティ（§10）:

- **認証**: `KOTOBACORE_API_TOKEN`（または `--token`）を設定すると POST は `Authorization: Bearer <token>` 必須。`/health` は開放。
- **レート制限**: `KOTOBACORE_RATE_LIMIT`（または `--rate-limit`）= クライアント IP あたり毎分の回数（固定 60 秒窓）。
- **入力長**: `--max-chars`（既定 200,000 文字）超は 413。
- アクセスログは出しません。エラー応答に入力文は含みません。入力文書は外部へ送りません。

エラー形（§9）: `{"error": {"code": "E701 unauthorized", "message": "…"}}`

| status | code |
|---|---|
| 401 | E701 unauthorized |
| 429 | E702 rate_limited |
| 413 | E101 input_too_large |
| 422 | E102 empty_input / E103 invalid_reference_date / FastAPI の検証エラー |
| 500 | E700 api_error（例外型名のみ、本文は含まない） |

リクエスト単位の `reference_date` は共有 Analyzer に残りません（ロック＋復元）。同時実行は 1 プロセス 1 Analyzer で直列化されるので、スループットが要る場合はワーカー数を増やしてください（`uvicorn kotobacore.api.server:create_app --factory --workers N` 相当）。

## 4. 互換性

`kotobacore version --matrix` の表（README「互換性マトリクス」）を正とします。IR は `meta.schema_version`（現行 0.4）で識別し、フィールド追加は後方互換、削除・型変更はメジャー更新です。
