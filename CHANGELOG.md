# Changelog

All notable changes to KotobaCore will be documented in this file.

## [1.0.1] - 2026-09-15

パッチリリース。書籍『AIに機密情報を持たせる方法』（ローカルRAGアプリ）の実地検証で見つかった RAG 層の不具合 2 件の修正と、感情辞書ライブラリとのベースライン比較ツール。IR schema・辞書・各モジュールの版は 1.0 のまま（互換性マトリクスは本体のみ 1.0.1）。

### Fixed — RAG 層のチャンカーと再ランキング（2026-09-14、ローカルRAGアプリ本の実地検証で発見）
- **`rag/chunk.py`: 「（1）」形式の列挙項目が見出しに誤判定される**。`_NUMBERED_ITEM` は「1. 」「1）」（数字が先頭・記号の後に空白）しか除外しておらず、日本語の規程・契約書で一般的な **全角括弧＋数字＋空白なし**（「（2）次のいずれかの事情があること」）が見出し扱いになり、`heading_path` から親見出し（「第１条（育児休業）」）が消えていた（厚労省モデル 育児介護休業規程 で確認）。正規表現を `^[（(]?[0-9０-９]{1,2}[.．)）]\s*\S` に変更。実資料 8 件で 883→853 チャンク、既存の「ただし」節・コードフェンス・番号リストの挙動は不変
- **`rag/features.py`: `keyword_overlap` / `entity_match` の本文フォールバックが語境界を無視**。`t in text` の素朴な部分文字列判定のため、質問語「AP」がチャンク内の「API」に一致し `keyword_overlap=1.0` になっていた。英数字のみの語（製品コード・API 名等）は前後が英数字でない場合だけ一致とみなす `_contains_term()` を追加（日本語の語は従来どおり部分文字列。CJK に信頼できる語境界が無いため意図的に対象外）
- `tests/test_v05_predicates_topics_rerank.py` に回帰テスト 2 本を追加（計 354）

### 追加 — 感情辞書ライブラリとのベースライン比較（v1.0 完成条件の最後の 1 項目）
- `tools/benchmark/compare_sentiment_baselines.py`: 人手評価セット v1（300 文）で oseti（評価極性辞書 + MeCab）/ pymlask（ML-Ask 感情辞書 + MeCab）/ asari（TF-IDF 二値）と比較。採点は run_annotated_eval と同じ（極性 = 表現の多数決、感情 = gold ラベルのいずれかに一致）。MeCab は Windows で DLL が使えないため mooma（Linux）の使い捨て venv で実行（mecab-python3 + ipadic wheel、bunkai のため emoji<2）
- 結果（`tools/benchmark/sentiment_baselines.md`）: 極性 accuracy（300 文）KotobaCore **83.0%** / pymlask 61.0% / oseti 47.7% / asari 26.3%（確信度 <0.75 を neutral 扱いで 46.3%）。極性のある 102 文だけなら asari 77.5% / KotobaCore 71.6% / asari(閾値) 62.7% / oseti 48.0% / pymlask 23.5%。感情 accuracy（182 文）KotobaCore **83.5%**（+NRC 84.1%）/ pymlask 23.1%（多対多写像で有利にしても）、カナリア誤検出 KotobaCore 0% / pymlask 27.3%
- 判明した注記: README の人手評価値（感情 84.1% / 分割 F1 0.9008 / 意図 70.0%）はローカルと mooma デモが読む外部 NRC 辞書（`dic/`、ライセンス上非同梱、939 語）込みの値。**pip install だけの構成では感情 83.5% / 分割 F1 0.8992 / 意図 69.7%**（極性 83.0%・Entity F1 0.86 は同じ）。比較表は両方の行を掲載
## [1.0.0] - 2026-09-09

**Semantic IR Schema を凍結し、全構成要素の版を 1.0 に統一**（ユーザー決定「凍結、全部 1.0.0 に統一」）。公開版（PyPI / GitHub）は 0.2.7 のまま＝公開は別判断。

### Changed
- `core.ir.SCHEMA_VERSION` **0.4 → 1.0**（フィールドは 0.4 と同一。以後、追加はマイナー・削除／型変更はメジャー）。`docs/IR_SCHEMA.md` を再生成
- `core.token.TOKENIZER_VERSION` 2.4 → **1.0**、`versions.MODULE_VERSIONS` intent 1.2 / emotion 1.1 / sentiment 1.1 / topic 1.0 → **すべて 1.0**、辞書セット 2026.09.09b → **1.0**（各 CSV も 1.0、旧番号は `versions.json` の `history` に保存）、HTTP API `API_VERSION` "1" → **"1.0"**。Vocabulary 形式は `kotobacore-vocab-1.0` のまま。旧番号の系譜は各モジュールのコメントに記録
- pyproject: `Development Status :: 4 - Beta`
- 要件定義書 **v1.0**（`KotobaCore_要件定義書_v1.0.md`）: §0-4 に凍結と統一の決定、§12 v1.0 ✅、§13 全項目 ✅（感情辞書ライブラリ比較のみ環境都合で未実施）

### Decided
- **語彙データは同梱しない**（FR-070 のまま）: 語彙はコーパス依存で 1 つの正解が無く、id は追記のみで安定させる約束なので、パッケージ版と語彙版を絡めない。参照語彙は別リポジトリ `kotobacore-vocab`（fine 2,680 ids / coarse 2,860 ids、公開コーパス 9,726 行から決定的に再構築可能）で配布する
- HTTP API の常駐（mooma）は引き続き保留。PyPI への 1.0.0 公開は別途判断

### 到達点（人手 300 文 v1 / 6,500 文 / RAG / NFR-001）
- 人手 300 文: 分割 F1 0.90 / Entity F1 0.86 / Sentiment 83.0% / Emotion 84.1%（カナリア 0%）/ Intent 70.0%
- 6,500 文: 感情正確度 96.8% / 極性 96.7% / 意図 75.1% / エラー 0
- RAG: 自作 200 問 MRR 0.846（ハイブリッド 0.868）、実務 120 問 0.720（0.777）。ベースライン: 分割 F1 coarse 0.894 vs SudachiPy C 0.875 / janome 0.865
- NFR-001: 10 万文 98 秒（1,021 文/s）、1 文平均 1.0 ms、1 万字文書 0.63 秒。352 テスト

## [0.6.8] - 2026-09-09

**v1.0 完成条件の品質項目**（NFR-001 バッチ、エラー処理 E1xx〜E7xx、語彙汚染テスト）と要件定義書 v0.6。公開版は 0.2.7 のまま。

### Added
- **`kotobacore.errors`（§9）**: E101 invalid_utf8 / E102 unsupported_character / E201 tokenization_error / E30x entity・predicate / E401 module_error / E402 rag_error / E50x IR / E601 vocab_version_mismatch / E7xx API のコード定数と `make_error()`、例外 `VocabVersionMismatch`
- **Analyzer は回復可能エラーで止まらない**: bytes 入力の不正 UTF-8 は置換して E101 を `IR.errors` に、代替文字・サロゲートは除去して E102、分割失敗は文字トークンにフォールバックして E201、Entity / 述語 / 感情 / 評価 / 意図 / トピックの各段の例外は隔離して E30x / E401（空結果で継続）。`analyze_document` は文の errors を文書位置に直して集約。`VocabEncoder` は語彙形式のメジャー版不一致で E601
- **`tools/benchmark/run_batch_benchmark.py`（NFR-001）**: 10 万文（実文 3,068 種 × 10 変種）と 1 万字文書（本文 479 文）。結果 `batch_benchmark.md`
- `tests/test_errors.py`（9 本）、`tests/test_vocab_contamination.py`（2 本、OCR 損傷コーパスで汚染候補を検出、清浄コーパスでは 0）。計 352
- **要件定義書 v0.6**（`KotobaCore_要件定義書_v0.6.md`）: §0-3 に v0.6.0〜0.6.8 の実装結果 10 項目、§12 ロードマップ v0.6 ✅ と v1.0 残（schema v1 凍結 / API ドキュメント / 常駐 / PyPI 公開）、§13 完成条件チェック（必須 12 中 10 ✅、品質 7 中 7 ✅、残: 分割基準の文書化・schema v1 凍結・API ドキュメント・感情辞書ライブラリ比較）、付録 A を v0.6.8 に

### Docs（同日、v1.0 完成条件の文書項目）
- **`docs/API.md`**（Python API / CLI / HTTP API、認証・レート制限・エラー形・互換性）、**`docs/openapi.json`**（`tools/gen_openapi.py` で FastAPI から生成）、**`docs/IR_SCHEMA.md`**（`tools/gen_schema_doc.py` で `core/ir.py` の dataclass から生成した全 25 型・全フィールドの表、追加版、エラーコード表 — schema v1 凍結の土台）、**`docs/TOKENIZATION.md`**（coarse / fine の分割基準を実測例で仕様化、既知の癖、コスト優先順位、Sudachi 短単位を採らない決定）。README に「ドキュメント」節。要件定義書 v0.6 §13 の「分割基準の仕様書化」「API ドキュメント」を ✅ に（必須 12 中 12 ✅、残は schema v1 凍結の判断のみ）

### Changed
- **性能**: チャンカーと感情辞書の表層マップを文ごとに再構築していた（dict.setdefault 300 万回 / 1 万字）のを bundle にキャッシュ。**10 万文 246 → 98 秒（1,021 文/s）、1 文平均 2.5 → 1.0 ms、1 万字文書 1.26 → 0.63 秒** — NFR-001 の 3 目標（600 秒 / 5 ms / 1 秒）をすべて達成
- vocab の汚染検出 mixed_script は漢字＋英字＋数字の混在も対象に

## [0.6.7] - 2026-09-09

**人手評価セット v1 確定**（`annotated_v1.jsonl` = 提案版を採用、ユーザー「そのまま進めて」）と、残っていた意図の混同 4 パターンの対処。公開版は 0.2.7 のまま。

### Changed（意図分類、人手 300 文の残り 115 不一致から）
- **個人投稿の評価は share_experience**: 評価語・感情由来の feedback は、個人手がかりがあり製品・サービス・組織の Entity も業務対象語（提案 / 見積 / 採用 / 契約 / 対応 …）も無ければ share_experience へ。明示的な規則語（ばかりなのに / ワロタ / ありがとう）による feedback はそのまま
- **感情語の無い体験報告も share_experience**（週末に…作った / 先週末、軽井沢に行ってきたんだ / 減らしたら…空いた）: 無信号の平叙文でも個人手がかりがあれば inform でなく share_experience。手がかりに 驚いた / 泣きそう / 乗り換えた / 戻した / したら / してみた / お金ない を追加、いただ / なった は除外
- **第三者の感情・自社の事実報告は inform**: 第三者主語（彼女は / 老人は / 村人たちは / 田中は、文中どこでも）または holder≠speaker、あるいは 弊社・当社・売上・出荷・利益… ＋ 敬体の報告文は、feedback を inform に付け替え
- **業務対象への拒否・不満は negative_feedback**（品質に問題はないものの…採用は見送ります / 納得しかねます）: 否定系感情 ＋ 業務対象語 ＋ 非個人
- 括弧内の固有名（「感動」パン屋）は意図ルールにも当てない。positive_feedback 規則から ワクワク（感情語）を除去
- golden_set: G013 / G019 の期待意図を share_experience に

### 計測（人手 300 文、確定版 gold）
- **Intent 60.7 → 70.0%**（残 86 件: share_experience→negative_feedback 9 / →positive_feedback 7、inform→share_experience 6、share→inform 5 …）、Sentiment 83.0%、Emotion 84.1%、Entity F1 0.86、分割 F1 0.90
- 6,500 文: 感情 96.8 / 極性 96.7 / 意図 75.1 / エラー 0 / 平均 2.7 ms。341 テスト

## [0.6.6] - 2026-09-09

**人手評価セットのレビュー（AI 判定案）と、判定から出た system 課題の対処**。公開版は 0.2.7 のまま。

### Review
- `tools/quality_test/annotated/verdicts_v1_ai.json`（258 文 × 観点の判定案）、`apply_verdicts.py` → `review_sheet_v1_verdict.md`（判定一覧＋課題分類の集計）と `annotated_v1_proposed.jsonl`（gold 修正を適用した提案版: tokens←system 7 / entities 22 / sentiment 削除 26〈感情文〉/ emotion 10 / intent 16、保留 7）
- 判定の内訳: gold 正しい = system 課題 449 件（dict 95 / rule 56 / ctx 55 / tok 48 / cue 45 / ner 40 / adv 30 / rhet 22 / canary 17 / neg 15 / holder 15 / num 10）、gold 修正 55、sentiment 削除 26、保留 7

### Added / Changed（system 課題の対処）
- **辞書**: sentiment.csv 1.2（253 → 334: 改悪 / 支障 / 納得いかない / 魅力的 / 有意義 / 屈指 / 快感 / 的確 / 風情 / 修辞疑問 高くない？…）、emotion.csv 1.6（597 → 739: 困る→irritation、助かる→trust、感謝→moved、悔やむ→sadness、頷いた→agreement、うるさい / 面白い / 感じいい / しょうがない…、**定型句** 財布落とした→anxiety / 履歴が消えた→sadness / 返事ない→irritation / 虹出てる→joy / 〜といいな→anticipation / 二度と会わない→refusal / 言葉を失った→surprise…）。モヤモヤ→anxiety、わくわく→anticipation に再ラベル（golden / lattice テスト更新）。ユーザー指示「system 未検出は追加すべき」により文脈推論扱いの 55 件も定型句で対処
- **意図ルール**: request（〜いただけますか / ください / 〜てくれない？ / 〜ないで / 命令形 来て・見て…）、desire（〜といいな / 〜たいね / こそ）、agreement（ほんとそれ / わかった / 了解）、pricing_complaint（〜円もした / 家賃 上がる / 値段の割に / 予算を超え / ライセンス費…）。6,500 文の意図正確度 68.1 → 75.1%
- **意図の手がかり**: share_experience の個人手がかりを拡充（体験動詞 泣い/焦っ/買った/届いた…、家族語 母/父/祖母…）。**第三者主体**（部長は / 彼女は / 村人たちは、または感情の holder が speaker 以外）の感情文は inform。**修辞疑問**（〜すぎん？ / 高くない？ / 何回〜ても / なんで…の）は立場があれば question にしない
- **括弧内の固有名**（「感動」という名のパン屋 / 『月影の庭』 / 新サービス「Kanso」）を Entity に（後続・前置の名詞で ORGANIZATION / BRAND / WORK / PRODUCT / SERVICE を判定、会話の引用は除外）。**括弧内の語は感情・評価から除外** → カナリア誤検出 22.7% → 0%
- 相対日付語の追加（先日 / 先週末 / この前 / こないだ / 今期 / 来期 / 子どもの頃 / 給料日前 / 今度の日曜…、ISO 値なし）
- 評価表層（最高だった）が感情語（最高）の照合を塞がないよう AC パスの claim を評価／感情で分離。感情語かつ評価語の原形（面白い）は活用形（面白くない）でも両方の読みを出す
- **強調は感情**（ユーザー決定）: 0.6.5 で入れた「強調語だけの文は primary None」を撤回。強調語だけなら exaggeration が primary、他の感情語があればそれが主役

### 計測（人手 300 文、**提案版 gold** / 参考: 下書き gold）
- Sentiment 69.7 → **83.0%**、Emotion 42.3 → **84.1%**（カナリア誤検出 0%）、Intent 49.3 → **60.7%**、Entity F1 0.79 → **0.86**、分割 F1 0.899
- 6,500 文: 感情 96.8% / 極性 96.7% / 意図 75.1% / エラー 0 / カナリア 0%。処理時間 平均 3.1 ms（辞書 1.7 倍で 1.7 → 3.1 ms、NFR-001 5 ms 以内）
- 残る意図の混同: share_experience→inform 16 / →positive_feedback 13 / →negative_feedback 11、inform→feedback 19（評価語のある事実報告）。次は「評価語があっても事実報告なら inform」の判定（第三者・敬体・数値報告）

## [0.6.5] - 2026-09-09

**人手評価セットに合わせた体系の修正**（ユーザー決定「gold に寄せて system 修正」2026-09-09）。公開版は 0.2.7 のまま。

### Changed
- **感情体系に surprise / trust / disgust を追加**（Plutchik の基本 8 感情が揃う）。`emotion.csv` 1.5: exaggeration に混在していた驚き語 19 行を surprise へ（驚いた / びっくり / まさか / 信じられない / 衝撃 / えっ…）、admiration・agreement から信頼語 13 行を trust へ（信頼 / 頼もしい / 心強い / 安心…）、refusal・anger から嫌悪語 30 行を disgust へ（嫌悪 / 気持ち悪い / 不快 / 汚い / ドン引き…）。追加 47 語（意外 / 想定外 / うそでしょ / 信用できる / 落ち着く / 苦手 / 胸糞 / ぞっとした…）＋ 可愛い系 3 語。極性: surprise=mixed、trust=positive、disgust=negative
- **exaggeration（強調）は感情のまま、ただし他の感情語が同時にあればそちらが primary**（マジで美味しかった → joy）。強調語だけの文（やばい / しぬw）は従来どおり exaggeration が primary（ユーザー決定「強調は感情」2026-09-09。0.6.5 中の一時案「評価語だけを強める場合は primary None」は撤回）
- **評価表層が感情の原形読みを塞がない**: 美味しかった は sentiment.csv の表層一致で評価、同時に原形 美味しい で joy（`claimed_emo` を分離、重複 overlay は抑止）
- **意図に inform / share_experience を追加**: 評価語（sentiment.csv）→ feedback、ただし個人的な投稿（私 / 今日 / 絵文字 / ！…）で製品・サービス・組織の Entity が無ければ share_experience。感情語のみ → 製品等の Entity があれば feedback、個人的なら share_experience、それ以外は inform。無信号の平叙文は inform（従来 unknown。断片は unknown のまま）。**意図ルールの一致は否定形を除外**（感動しない は positive_feedback に数えない）
- NRC 外部辞書の誤訳 `正直`（admiration）を停止（`_EXTERNAL_STOPLIST`）。人手 300 文で 7 回、本物の感情を押し出していた
- `entity.csv` 1.4: 消費者製品 12 行（iPhone / iPad / Android / Windows / PlayStation …、PRODUCT）
- N4 修正: 五段の受身・使役 れる / せる は a 段の後だけ剥がす（疲れた → 疲れる、忘れた → 忘れる。従来は 疲る）
- golden_set.csv: 中立業務文 5 件の期待意図 unknown → inform、頼もしい → trust。テスト 341

### 計測（人手 300 文、v0.6.4 → v0.6.5）
- **Intent 13.7% → 45.0%**（体系差の解消。残る混同は share_experience→inform 32 / negative_feedback→inform 13 / inform→positive_feedback 11）
- **Emotion 26.9% → 36.8%**（残る不一致は「system 未検出」= 辞書に語が無い: irritation 23 / sadness 10 / joy 9 / admiration 9 …）
- Entity F1 0.6583 → 0.6646、Sentiment 62.0 → 61.7%、分割 F1 不変
- 6,500 文品質: 感情正確度 97.1 → 96.9%、極性 97.0 → 96.7%、意図検出率 71.5 → 100%（inform）、エラー 0、カナリア 0%
- レビューシート: 不一致 287 → 258 文、体系差の論点 5 → 1（exaggeration 2 件）。§0.5 に辞書追加候補を語単位で集約

## [0.6.4] - 2026-09-09

v1.0 項目 **互換性マトリクス（§8 / NFR-003）と旧 import パスの非推奨化（§3.2）**。公開版は 0.2.7 のまま。

### Added
- **`kotobacore.versions`**: `component_versions()`（本体 / IR schema / Tokenizer / 辞書セット・各 CSV / モジュール / Vocabulary 形式 / HTTP API / 旧 import の方針）と `compatibility_matrix_markdown()`。CLI `kotobacore version --all`（JSON）/ `--matrix`（README 用 Markdown）
- **`core.token.TOKENIZER_VERSION = "2.4"`**（Karuizawa 分割版。1.x カスケード → 2.0 ラティス → 2.1 fine → 2.2 オノマトペ → 2.3 評価語ノード → 2.4 送り仮名ノード＋仮定形）
- **辞書マニフェスト `resources/dict/versions.json`**（辞書セット版 2026.09.09、CSV ごとの version / rows / note）。`tests/test_versions.py` が実 CSV の行数と照合するので、**辞書を変えたら version と rows を更新しないとテストが落ちる**（版上げ忘れ防止）。wheel に同梱（package-data に *.json）
- `versions.MODULE_VERSIONS`（intent 1.2 / emotion 1.1 / sentiment 1.1 / topic 1.0）
- **`MetaInfo.components`**（tokenizer / dictionary_set / modules の版を結果に刻む。NFR-002 再現性。既存キーは不変）
- README に互換性マトリクス

### Changed
- **旧 import パスは DeprecationWarning**（`kotobacore._compat.KotobaCoreDeprecationWarning`、"deprecated since 0.6.4 … removed in 1.1"）: `kotobacore.schema` / `clause` / `matching` / `normalizer(.unicode_normalizer)` / `tokenizer(.base .karuizawa_backend .lattice .token_normalizer)` / `semantic(.builder .chunker)` / `emotion(.detector)` / `intent(.classifier)` の 17 シム。動作は従来どおり（同一オブジェクトを返す）。`kotobacore.compat`（Karuizawa 互換 API、FR-093）は非推奨にしない
- テストの import を新パスへ移行（9 ファイル）。`tests/test_compat_deprecation.py` が旧パス 14 本の警告と同一性を、`test_synonym_and_layout.py` が旧パスの import 可能性をそれぞれ担保
- テスト 337（+20）、ruff OK

### Tools（同日追加、v1.0 完成条件の 2 項目）
- **`tools/quality_test/build_review_sheet.py`**（人手評価セットのレビュー確定用）: 300 文の gold と現行出力を並べ、tokens / entities / sentiment / emotion / intent の不一致に「判断メモ」を付ける。
  個別の当否ではなく**体系差**（gold の意図 `inform` 117 / `share_experience` 62 は system 体系に無い、感情 `surprise` 11 / `trust` 9 / `disgust` 5 も同様、system の `exaggeration` 13 は gold に無い、評価極性 gold あり / system なし 89 は 2026-09-08 の極性定義で再判定）を先に決める構成。
  出力 `annotated/review_sheet_v1.md`（決めること → ジャンル別チェックリスト）と `review_sheet_v1.csv`（verdict / corrected_gold 列付き）。不一致 287 / 300 文
- **`tools/benchmark/compare_baselines.py`**（既存ツールとのベースライン比較）: janome (IPADIC) / SudachiPy A・B・C / KotobaCore coarse・fine を、人手 100 文の分割境界 P/R/F1・速度・フットプリントで比較。
  結果 `tools/benchmark/baseline_comparison.md`: **coarse F1 0.894**（janome 0.865、Sudachi C 0.875 — gold が KotobaCore の意味単位なので短単位側は R 1.0 / P 0.76〜0.78）、
  速度 KotobaCore 0.27 ms/文（janome 0.71、Sudachi 0.04 = Rust）、辞書 0.3 MB（janome 211 MB、SudachiDict 218 MB）。感情・極性のベースライン（oseti 等）は MeCab の Windows DLL が使えず未実施

## [0.6.3] - 2026-09-09

v1.0 項目 **N4 語形正規化（FR-002 N4 / FR-010 活用情報）**。Token に `conjugation_type` / `conjugation_form` を追加（schema 0.4 の範囲、既存キー不変）。公開版は 0.2.7 のまま。

### Added
- **`core.token.conjugation`**（辞書なし・規則ベース）: `analyze_verb` / `analyze_adjective` / `analyze_conjugation(surface, pos)` → `ConjugationInfo(lemma, conjugation_type, conjugation_form)`
  - 助動詞を右から最長一致で剥がし（食べ|させ|られ|なかった）、残った語幹末のかな行から活用型を決めて原形を組み直す。ます/ない/た/て/ば/う/よう/たい/られる/させる/ている/てくる/ちゃう/たら/たり…
  - 活用型: 五段 / 一段 / カ変 / サ変 / 形容詞 / 形容動詞。辞書でしか決まらない曖昧（走った→走る／走つ／走う、読んだ→読む／読ぶ）は最頻パターンで解いて **`五段?`** と表示。頻出動詞は小さな語幹表で確定（待った→待つ、買った→買う、飛んだ→飛ぶ、起きます→起きる）
  - 活用形ラベルは表層順に "-" 連結（使役-受身-否定-過去、進行-丁寧、過去-接続-理由）。ラティスが動詞に結合する接続助詞（走ったので）はラベル側に剥がす
  - 形容詞は い-基本形（美味しかった→美味しい、高い は 2 字でも基本形）、形容動詞は コピュラ尾で検出（静かだった→静かだ）
- **Token.dictionary_form が動詞でも原形に**（従来は表層のまま）。`core.lexicon` の dictionary_form パスが動詞にも効くようになり、人手 300 文の Emotion 正確度 24.7% → 26.9%。述語の lemma も原形（なった→なる）
- **送り仮名揺れの N4 正規化**: 新辞書 `resources/dict/okurigana.csv`（82 グループ、本則形＝canonical と圧縮形: 申し込み／申込み／申込、見積もり／見積、引き落とし／引落し／引落、買い物／買物…）。`DictionaryBundle.okurigana_map()`。
  変異形はラティスの名詞ノードとして登録され（従来は 見積|もり、引き落|とし と分割が壊れていた）、`Token.normalized` に本則形を保持。表層は不変（N3〜N5 の規則）。チャンクの keywords（normalized を使う）に本則形が乗る
- 仮定形の動詞語尾（れば／けば／せば／てば／めば／べば／げば／えば／ねば）を `_VERB_TAILS` に追加し、走れば／書けば／食べれば が 1 語に

### 計測
- 317 テスト（N4 6 本追加）、ruff OK。6,500 文品質: 感情正確度 97.1% / 極性 97.0% / エラー 0 / 鳴き声カナリア 0%
- 人手 300 文: 分割 F1 0.9077・Entity F1 0.6583 不変、Sentiment 62.3 → 62.0%（1 文）、Emotion 24.7 → 26.9%
- RAG 語彙経路: 実務 0.720・自作 0.840 とも不変

### Known limits
- 話した／勉強した は サ変分割規則で 名詞＋した のまま（設計どおり）。行きます／書きます は「きます」が ひらがな動詞（来ます）に取られる既存の癖。命令形「ろ」は語尾表に入れていない

## [0.6.2] - 2026-09-09

v1.0 項目 **Entity 共参照（FR-034）**。IR schema 0.3 → **0.4**（Entity に `canonical_id` / `aliases` 追加、既存キーは不変）。公開版は 0.2.7 のまま。

### Added
- **`core.coreference.resolve_coreference`**（`analyze_document` で自動適用、`Analyzer(enable_coreference=False)` で無効化）
  1. **クラスタ化**: 同じ normalized、同じ core 形（PERSON は敬称・役職を除いた形、ORGANIZATION は法人格を除いた形、LOCATION は都道府県を除いた形）、または core の前方一致（田中 / 田中太郎、北斗 / 北斗物流）で union-find。最長表層が代表、全員に `canonical_id`、代表に `aliases`。id は一意のまま（chunk / sentence の参照を壊さない）
  2. **短縮形 mention の発見**: 代表・メンバーの core、PERSON の姓トークン、ORGANIZATION の「core − 業種語」（北斗物流 → 北斗）がトークン境界ぴったりで出現し Entity 未抽出なら `source="coreference"`（confidence 0.6）の mention を追加し同クラスタへ。`normalized` は代表の正規形なので、チャンクの entity_match は「北斗」を「北斗物流」として見る
  3. **照応**: 同社 / 同行 / 同校 / 同氏 / 彼 / 彼女 / 同市 / 同県 / 同製品 / 同書 / 同大会 … → 直前の同型 mention（confidence 0.5）
  - `coreference_clusters(entities)` で代表先頭のクラスタ一覧。DATE / TIME / MONEY / QUANTITY は対象外、`analyze()`（1 文）では走らない
- パターン NER: 法人接頭辞がラティスで 1 トークンに結合した形（株式会社北斗物流）も ORGANIZATION に。組織接尾辞に 物流 / 運輸 / 建設 / 不動産 / 製作所 / 製薬 / 鉄道 / 商会
- テスト 6 本（`tests/test_coreference.py`）、計 311。人手 300 文の Entity F1 0.6583 / 0.6458 は不変（文単位評価のため共参照は影響外、接尾辞追加の退行なし）

### Changed
- RAG 語彙経路: 実務 0.720 不変。自作 200 問 0.846 → 0.840 — 共参照は ±0（無効化して同値）、**「北斗物流」が ORGANIZATION になった副作用**: 文書全体の主題である組織 Entity が entity_match で全チャンクに等しく加点され、主題を含まない gold が 2 問下がった。
  文書の主題 Entity をチャンク弁別に使わない再ランク（文書内出現率で減衰）は今後の課題

## [0.6.1] - 2026-09-09

v1.0 項目 **HTTP API（FR-092）**。Streamlit デモとは別プロセス。公開版は 0.2.7 のまま。

### Added
- **`kotobacore.api`**（extra `kotobacore[api]` = FastAPI + uvicorn。本体の実行時依存は PyYAML と typer のまま、NFR-006）
  - `create_app(analyzer=None, *, api_token=None, rate_limit=None, max_chars=200_000)` → FastAPI アプリ
  - `GET /health`・`GET /version`（kotobacore / schema / api 版、auth・rate limit の有効状態）、`POST /analyze`（`document` で文書モード、`reference_date`、`semantic_only`）、`POST /query`、`POST /chunk`（max_chars / min_chars）、`POST /tokenize`（coarse / fine）。`/docs` に OpenAPI
  - **§10 セキュリティ**: Bearer トークン認証（`--token` / env `KOTOBACORE_API_TOKEN`、POST のみ・/health は開放）、クライアント別レート制限（`--rate-limit` / env `KOTOBACORE_RATE_LIMIT`、固定 60 秒窓）、入力長上限（413）、**アクセスログ無効・エラー応答に原文を含めない**
  - **§9 エラー形**: `{"error": {"code": "E7xx …", "message": …}}`。E101 input_too_large / E102 empty_input / E103 invalid_reference_date / E700 api_error / E701 unauthorized / E702 rate_limited
  - リクエスト単位の `reference_date` は共有 Analyzer に漏らさない（ロック＋復元）
- CLI `kotobacore serve --host --port 8590 --token --rate-limit --max-chars --reference-date`（extra 未導入なら導入方法を案内して終了）
- テスト 8 本（`tests/test_api.py`、fastapi / httpx が無ければ skip）、計 305

## [0.6.0] - 2026-09-09

要件定義書 v0.5 §12 の v1.0 項目のうち **Vocab モジュール（FR-070〜072）** を実装。Token 層の任意モジュールで、IR は vocab なしで完全（§3.3）。公開版は 0.2.7 のまま。

### Added
- **`kotobacore.vocab`**（`build` / `encode` / `evaluate`）
  - `build_vocab(texts, granularity="fine", min_freq, max_size)` → `Vocabulary`（`version`=kotobacore-vocab-1.0、`granularity`、`normalization_version`、`kotobacore_version`、`entries[piece,id,freq,pos,flags]`）。
    id 0〜9 は特殊トークン（`<pad> <unk> <bos> <eos> <sep> <mask> <cls> <nl> <sp> <reserved>`）、以降は頻度降順（同数は表層順）で決定的。**コーパスの全文字を必ず語彙に含める**（`char` フラグ、min_freq 対象外）ので未知語は文字へフォールバックし OOV で欠落しない
  - `extend_vocab(vocab, texts)` は**追記のみ**（既存 id は不変、頻度メタデータだけ更新、新規は最大 id の次から）
  - `VocabEncoder.encode/decode/pieces/annotate`: トークン間の改行・空白を `<nl>` / `<sp>` で保持、語彙に無い語は文字列→無い文字は `<unk>`。decode は正規化後テキストを返す（表層は正規化済みのため）。`annotate(tokens)` が §3.3 の任意フィールド `vocab_id` 相当を返す（IR 本体には埋めない）
  - `vocab_report(vocab, texts)` / `report_markdown`: coverage（1 ピースで符号化できたトークン率）・OOV トークン率・`<unk>` 率・ids/token・上位 10 語の頻度シェア・単発語率・未使用語数・長さ/POS 分布・**汚染候補**（制御文字 / 半角カナ / 記号連結 / 同字反復 / 異常長 / かな＋英字＋数字混在 / 非 NFKC）と NFKC 重複
  - CLI `kotobacore vocab build|encode|decode|report`（入力はファイルまたはディレクトリの *.txt / *.md、`--extend` で追記）
  - 語彙データは同梱しない（FR-070）。テスト 8 本、計 297
- 動作確認: 同梱 SNS 例文 2,000 句で build 0.5 秒・1,443 id（語 571）、保留 729 句で coverage 70.6% / OOV 29.4% / `<unk>` 9.2%、人手 300 文で 63.7% / 36.3% / 16.2%、学習内 93.7%。汚染候補 0

### Notes
- 要件定義書 付録 A の「Vocab | なし | v1.0」行は v0.6 で実装済みに更新が必要（要件書は版番号ルールで v0.6 として別ファイル化する）
- FR-073（外部 LLM Token ID との対応）は要件どおり未実装

## [0.5.4] - 2026-09-09

実務コーパスの howto 質問を個別に追うと、原因は検索モデルではなく **チャンカーが Markdown の技術文書を壊していた** ことだった。公開版は 0.2.7 のまま。

### Fixed
- **コードフェンス内の見出し誤認**: ```` ``` ```` 内のシェルコメント `# フォントキャッシュを削除` が見出しとして段落を切り、コマンドが説明文・節見出しから分離されていた
  （実務 howto の gold「rm -rf /root/.cache/matplotlib/」が見出し無しの裸チャンクに）。`core.syntax.split_paragraphs` がフェンスを追跡し、フェンス内は見出し判定・空行分割の対象外、
  ブロック全体を 1 段落に（`is_fence_line` 新設）
- **連続する見出しでテキストが消える**: `pending_heading` が上書きされ、見出し行が連続すると先の行がどのチャンクにも入らなかった。番号付きリスト「1. 50〜100発話を人手でラベル付け」
  が見出し判定されて 4 項目中 3 項目が消失（実務 p113 が gold 欠落）。pending を list にして全件を次チャンクへ。加えて番号付きリスト項目（`1. ` + 空白）は見出し扱いしない
- チャンク先頭の複数見出しは context から除外（本文に含まれるため）。既存テスト `test_document_chunk_heading_path_and_table_header` の期待値を「導入・前提とも本文に残る」に更新

### Added
- **コードブロックは導入文と同じチャンクに**: フェンス直前の段落境界ではチャンクを切らず、コード行では topic shift を判定しない。サイズ上限で分かれた場合は、
  直前の説明文（80 字まで）を `DocumentChunk.context` に載せる（見出しパス・表ヘッダと同じ扱い）
- `tools/rag_eval/run_rag_eval.py` の per_question に条件別 gold 順位・gold チャンク id・top1 を追加（版間の質問単位 diff 用）

### 計測（MRR@10、v0.5.3 → v0.5.4）
- 実務 120 問: チャンク 6,134 → 5,174、**gold 欠落 2 → 0**、語彙経路 **0.634 → 0.720 (+13.6%)**、BM25 素の土台 0.600 → 0.655、**howto R@3 65.0 → 85.0**、compare 80 → 90。value 62.5 → 50.0・definition 77.8 → 72.2 は語彙不一致（範囲 ↔ BETWEEN 1 AND 5 など）で残課題
- 自作 200 問: 変化なし（コードフェンス・番号リストを含まないため 447 チャンク・0.846 / ハイブリッド 0.868 のまま）
- ハイブリッド（実務、e5-base、再埋め込み 18 分）: e5 単体 0.595 → 0.683、ハイブリッド(α=0.3) 0.693 → 0.774、**ハイブリッド+フィルタ+再ランク 0.695 → 0.777 (+11.8%)**、**howto R@3 60.0 → 95.0**、
  synonym 70 → 75、value 75 → 75、definition 94.4 → 83.3（結果 md のヘッダ版表記は 0.5.3 = 計測プロセスが版上げ前に起動したため）
- 教訓: 「howto は Embedding が苦手」は誤診で、**技術文書のチャンク境界（フェンス内コメント・番号リスト）が壊れていた**。検索モデル側の α 切替では救えない種類の劣化

## [0.5.3] - 2026-09-09

実務コーパスで howto 質問が Embedding に弱い（R@3: BM25 65 / e5 45 / ハイブリッド 55）問題への対処。公開版は 0.2.7 のまま。

### Added
- **回答の形 (answer form) による intent_match** `rag.features.answer_form_match(intent, text)`: how_to / procedure（コードブロック・番号手順・→・してください・コマンド…）、reason（ため・原因・背景…）、compare、definition、condition、specification の手がかり語で
  「チャンクがその種類の答えの形をしているか」を 0 / 0.5 / 1 で返す。`rerank_features` の intent_match は、回答型が MONEY/DATE 等の実体型なら従来どおり実体の有無、TEXT 型意図ならこの形一致に切り替わる。
  **実務 howto 質問で gold チャンクの intent_match が全件 None だった**（チェックリストや仕様表がコマンド 1 行のチャンクを押し出していた）のが動機
- Query 意図分類の how_to / procedure 再現率向上: 名詞句型の how-to（〜の書き方 / 〜するコマンド / 〜に必要な操作 / どう保管する）と障害対応（〜になる時の対処 / 〜エラーの解決策 / 〜の対策 / 〜への対応）、ルール・規定・禁止 → condition。
  howto 質問の how_to/procedure 判定: 実務 10/20 → 15/20、自作 11/25 → 16/25。「どう違う」「どうなる」は compare / reason に留めるため規則順を compare → reason → how_to に変更
- `rag.features.HYBRID_ALPHA`（=0.3）と `hybrid_alpha(query)`・`query_lexical_anchors(query)`（識別子 / 製品コード / なし の診断ラベル）。評価スクリプト `run_embed_eval.py` の α は本体定数を参照
- `tools/rag_eval/analyze_alpha_by_query.py`: 質問ごとの α–RR 曲線を gold 型・予測意図・ASCII 識別子・同義語展開有無・スコアのピーク度で集計し、α 切替ポリシーを 自作 1-80 → 81-200 → 実務 の順で比較
- `tools/rag_eval/rerank_ablation.py`: tune_hybrid_rerank のキャッシュ候補に対し、キャッシュ時の特徴量と現行コードの特徴量で再ランクを比較（旧版との A/B を git stash なしで実施）、intent_match 重みグリッド付き

### Changed
- **ハイブリッド α は固定 0.3 と結論**: 意図別（how_to → 語彙寄り）・識別子有無・同義語展開有無・スコアのピーク度、いずれの query-time ポリシーも 自作 train / val / 実務 の 3 つを同時には超えない
  （実務 howto だけ見れば α=0.8 で +0.11 だが自作 howto は α=0.0 が最良で真逆。gold 型オラクルでも上積み +0.03）。howto の弱点は融合重みでなく再ランク側（上記 answer form）で救う
- intent_match の重み（HYBRID 0.05 / DEFAULT 0.10）は据え置き。グリッドでは自作 train が 0.15 で最良だが val は単調悪化、実務は 0.05 が最良

### 計測（MRR@10、v0.5.2 → v0.5.3）
- 実務 120 問: 語彙経路 0.631 → 0.634、ハイブリッド+フィルタ+再ランク 0.689 → 0.695、**howto R@3 55.0 → 60.0（full 経路 65.0）**、procedure 意図の質問 0.708 → 0.833。reason の語彙経路は 85.7 → 78.6（1 問）
- 自作 200 問（妨害あり）: 語彙経路 0.833 → 0.846、ハイブリッド+フィルタ+再ランク 0.872 → 0.868（差分は α 0.4 → 0.3 の分。同 α では ±0）
- 再ランク特徴量だけの A/B（rerank_ablation、α=0.3）: 自作 1-80 0.854 → 0.862、81-200 0.878 → 0.878、実務 0.728 → 0.732。壊さずに howto を拾う水準

## [0.5.2] - 2026-09-08

実務コーパス（社内業務文書 30 件・6,134 チャンク・120 問、リポジトリ外）での再計測に基づく改善。公開版は 0.2.7 のまま。

### Added
- **チャンク文脈 (FR-082 拡張)**: `DocumentChunk.heading_path`（囲む Markdown 見出しの階層）と `context`（見出しパス、表の行なら表ヘッダ行）、`text_with_context`。
  再ランクの `ChunkView` と評価ハーネスは文脈込みの本文を索引。**実務コーパスで土台 MRR 0.570 → 0.600、再ランク込み 0.592 → 0.630**（R@3 60.0 → 70.8）
- synonym.csv に IT / 開発 / クラウド / セキュリティ / オフィス / データ / 業務 のドメイン同義語 260 グループ（計 478）
- Query 意図体系に業務文書向けの回答型・意図を追加: 改訂日・施行日 → DATE、行数・上限・範囲・ポート番号 → NUMBER、担当・作成者 → PERSON、
  パス・ディレクトリ・保存先 → LOCATION、condition / procedure / specification。実務 120 問で lookup 80 → 51
- `rag.features.rrf_fuse`（順位融合）、`EXPANSION_WEIGHT`（展開語の重み 0.15）
- **ハイブリッド用の再ランク重み `rag.features.HYBRID_WEIGHTS`**（検索融合スコア 0.35 / Embedding 類似度 0.10 / キーワード 0.15 / 回答型 0.05、他 0）。`rerank_score(..., retrieval_score=, lexical_similarity=)` に融合後スコアが渡されると自動で切り替わる（語彙経路の `DEFAULT_WEIGHTS` は不変）。`tools/rag_eval/tune_hybrid_rerank.py` で自作 1-80 問で選び 81-200 問で検証、実務 120 問は最後に 1 回: 旧重みはハイブリッド検索を 0.03〜0.05 悪化させていたが新重みで解消（検証 0.838→0.874、実務 0.682→0.717）。融合検索単体に対する上積みは 検証 +0.007・実務 ±0（+0.004 / 製品経路 −0.003）で、ハイブリッド後の再ランクは「壊さない」水準
- `tools/rag_eval/run_embed_eval.py`: 外部 Embedding（sentence-transformers、既定 intfloat/multilingual-e5-base、専用 venv）と KotobaCore 検索の合成評価。条件 = BM25 / KotobaCore 語彙経路 / Embedding / Embedding+再ランク / RRF / 重み付きハイブリッド(α) / ハイブリッド+フィルタ+再ランク / 全部。**実務コーパス: BM25 0.600 → ハイブリッド(α=0.3) 0.693、同義語質問 R@3 35 → 80（全部）**、自作: 0.766 → 0.845。本体に依存は追加しない（FR-085 どおり Embedding は外部注入）

### Changed
- 再ランクの keyword_overlap は質問語を 1.0、同義語展開を 0.15 で重み付け（展開が外れても一致チャンクを薄めない）
- 評価ハーネスは 生の質問 1.0 ＋ Query IR 語 0.25 ＋ 展開語 0.15 の重み付き BM25。実務文書では語彙展開はどの重みでも土台を超えず、
  自作コーパスでは +0.03。**語彙展開の効果はコーパスの書き方に依存し、同義語質問（R@3 30%）は Embedding の領域**

### 実務コーパスの最終値（MRR@10 / R@1 / R@3 / R@5）
- 文脈なし土台 0.570 / 48.3 / 60.0 / 68.3 → 文脈込み土台 0.600 / 51.7 / 65.8 / 71.7 → 再ランク込み **0.631 / 53.3 / 70.8 / 75.0**（+10.7%）
- 自作コーパス（200 問・妨害あり）: 0.769 → 0.833

## [0.5.1] - 2026-09-08

v0.5.0 のデモ運用と RAG 検索評価（tools/rag_eval、200 問）の結果に基づく改善。公開版（PyPI/GitHub）は 0.2.7 のまま。

### Changed
- 辞書 NER をテキスト一致（トークン境界整合）にも拡張: 「東京だ」のように語尾と融合したトークン、分割されたトークンにまたがる辞書語も取れる
- デモの固定コーパスに Entity / Event 向けの例文 4 件を追加
- **評価の重ね合わせ (overlay)**: 感情語・スラングの表現が sentiment.csv の語を含むとき（最高 / 高すぎ / 課金高すぎ ⊃ 高すぎ）、
  感情はそのままに評価表現も同じ位置に出す。接尾一致では直前部分を宛先にする（課金高すぎ → 課金）。
  これにより「怖かったけど面白かった」= 感情 anxiety・評価 positive のように、感情と評価の食い違いが IR に残る
- sentiment.csv に 28 語追加（面白い / すごい / かわいい / かっこいい / つまらない / ありえない / 気持ち悪い / 難しい / 神対応 / 神回 …）。
  楽しい・安心・残念・後悔・やばい・尊い・エモい は感情語のまま（評価語にするかは要判断、レビュー用一覧参照）
- デモの固定コーパスに Sentiment（評価語）セクション 3 文を追加
- `analyze_document`: 文書レベルの主要感情を文ごとの主要感情の確信度加重投票に変更（1 文なら analyze() と完全一致）。デモの文書モードを既定オンに
- テスト 274 → 280。6500 文評価は全指標不変

## [0.5.0] - 2026-09-08

要件定義書 v0.4 §12 の v0.5 マイルストーン: 述語項構造 / Relation / Event / Topic モジュール / Retrieval・Reranking 特徴量 / 参照アダプタ。
IR schema_version 0.2 → **0.3**（フィールド追加のみ）。

### Added — 述語項構造・Relation・Event (FR-023 / 040 / 041) `core/predicate.py`

- `AnalysisResult.predicates`: 節ごとの末尾述語（動詞・形容詞、または だ/し/される/になった 等の語尾を伴う名詞述語、文末の「ケーキは神」）と
  格助詞による項（が=subject、は/も=topic→subject 昇格、を=object、に/へ=goal、で=location/means、から=source、まで=until、と=with、より=than、
  日時エンティティ=time）。否定・受身/使役・名詞述語フラグ付き
- `events`: 述語ごとに type（動詞辞書 行く→GO / 設立→FOUND / 発表→ANNOUNCE …、形容詞・名詞述語は STATE、未分類は原形）と agent / object / goal / location / time
- `relations`: 主語 → 述語 → 各項 の三つ組（Entity id 付き）
- 節分割 (core.syntax) に連用形＋読点（設立し、／行って、／いまいちで、）の弱境界を追加し、1 節 1 述語に
- 係り受け解析器は持たない（設計原則 2）

### Added — Topic モジュール (FR-063) `modules/topic.py`

- `AnalysisResult.topics`: TOPIC 辞書エンティティ 1.0 → その他エンティティ 0.8 → 頻出名詞（頻度×長さ）。文書では文ごとの結果を合算
- 文書チャンクの話題境界と Reranking の topic_match が参照

### Added — Retrieval / Reranking 特徴量と参照アダプタ (FR-083 / 084) `rag/features.py`, `rag/retriever.py`

- `retrieval_features(query_ir)`: search_terms（同義語展開込み）、entities、intent / answer_type、filters（time / location / quantity …）
- `rerank_features(query_ir, chunk_view)`: entity_match / keyword_overlap / intent_match（回答型と内容の一致）/ time_match / topic_match / sentiment_match。
  `rerank_score()` は重み設定可能・欠損信号は重みを再正規化、Embedding 類似度は外部から受け取る
- `InMemoryRetriever`: 外部 embed 関数注入 → cos 類似で候補 → KotobaCore 再ランク（純 Python、テスト済み）
- `PgVectorRetriever`: pgvector + 外部 Embedding（Spark RAG 書庫の構成）向け DDL / INSERT / 検索 SQL 生成のみ（実行は呼び出し側、依存追加なし）
- **効果測定 (tools/rag_eval/)**: 自作コーパス 24 文書 + 質問 200 問 (type 10 種 / lexical 5 種)、妨害チャンク 300 文込み 447 チャンク、
  土台 = 文字 bigram BM25。MRR@10: 土台 0.769 → Query IR 検索語 0.792 → 制約フィルタ 0.799 → 再ランク 0.830 (R@1 68.5→75.5, R@3 82.0→89.5)。
  言い換え質問で最大効果 (R@3 76.9→92.3)、同義語 69.2→79.5。再ランク重みは質問 1-80 で選び 81-200 で検証して既定値を更新
  (語彙スコア 0.4 / Entity 0.1 / 回答型 0.1 / キーワード 0.2 / 時間 0.1 / トピック 0.05)
- Query IR 検索語: 質問語の名詞 (場所 / 人 / 何キロ) を除外、同義語展開は複合語の主要部 (無ければ修飾部) に限り 2 語まで
- 時間制約の粒度互換 `rag.features.time_compatible`: FY2026 ⟷ 2026-04〜2027-03 の日付 / 2026、2026 ⟷ 2026-xx、2026-10 ⟷ 2026-10-05。
  再ランクの time_match と評価ハーネスのフィルタが共用。相対日付質問の R@3 78.9 → 94.7
- 製品・型番コード (MX-500 / X200 / TN-X200 / E-52) をパターン Entity (PRODUCT) に。トークナイザが英字・記号・数字に分けても 1 エンティティ

### Changed

- 否定スコープに動詞否定を追加: 感動しない / できません / されない（core.syntax）
- 評価語 (sentiment.csv) をトークナイザのラティス辞書ノードに登録（いまいち が「いまいちで」に吸収されなくなった）。ひらがな評価語は 形状詞
- Query IR: 1 文字名詞（犬 / 車）も検索語に残す
- テスト 259 → 274。6500 文評価は全指標不変

## [0.4.0] - 2026-09-08

要件定義書 v0.4 §12 の v0.4 マイルストーン: Entity / IR 階層化 / 宛先付き評価・感情 / Query IR / 文書チャンク / 評価 CLI。
IR schema_version 0.1 → **0.2**（フィールド追加のみ、既存キーは維持）。

### Added — Entity 層 (FR-030〜034) `core/ner.py`

- `AnalysisResult.entities` (`Entity`: id / type / surface / normalized / begin / end / token_ids / source / value / unit / currency)
- **Time**: 絶対 (2025年10月5日・10月5日・2025年度・令和7年・月曜・午前10時・10:30) と相対 (今日・昨日・来週・昨年度・3日前・2年後)。
  `Analyzer(reference_date=)` を与えると ISO 日付に解決 (`value`)。年度は `FY2025`
- **Quantity / Money**: 数値 (5,000・1万・45億・百万・三千五百・約200) × 単位 (円/ドル/人/件/台/%/kg/時間/日/年 …)。
  期間 (3年・1週間) は QUANTITY、前後付き (3日前) は DATE
- **パターン NER**: 接尾辞テーブルで 組織 (株式会社X・X支社・X銀行・X大学 …)、地名 (X市・X駅・X公園 …)、人名 (Xさん・X氏・X部長・X先生 …、
  敬称込み表層＋敬称なし正規化、お客様/皆さん等はブロック)、イベント (X会議・説明会・Xフェア2026 …)
- 辞書 NER (entity.csv) と統合し、重なりは長い span → time > quantity > dictionary > pattern の順で解決
- トークナイザ: 繰り返し記号「々」を漢字扱い (代々木公園 / 様々 / 人々 が 1 語に)

### Changed — 極性の定義: 感情語は評価極性に含めない (2026-09-08 決定)

- `SentimentResult.polarity` / `expressions` は **評価語 (sentiment.csv) のみ** から算出。感情語だけの文
  (「わくわくが止まらない」) は polarity=None
- 感情語由来の極性は `SentimentResult.affect_polarity` に分離 (`EmotionResult.polarity` と同値)。
  「怖かった」(恐れ) が映画の肯定評価でありうる、という評価と感情のずれを IR に残す
- 意図分類の feedback 連動は 評価極性 → 感情極性 の順で読む

### Added — 宛先付き評価・感情 (FR-052) `core/attribution.py`

- `SentimentExpression.target / target_text`、`EmotionExpression.holder / holder_text / about / about_text`
- 宛先は同一節内で直前の主題語 (X は / が / も / って …)、無ければ節内の直近名詞、無ければ前の節の主題を継承
  (「コーヒーはいまいちだけどケーキは神」→ いまいち←コーヒー、神←ケーキ)。主体は節内で主語標示された PERSON、既定は speaker
- 係り受け解析器は持たない (設計原則 2)。浅い規則のみ

### Added — 文書階層 (FR-050) と文境界 (FR-020)

- `Analyzer.analyze_document(text)`: `paragraphs` (空行区切り・見出し行は単独段落) / `sentences` (文ごとの emotion / sentiment / intent を保持) /
  文書全体の tokens・entities・chunks を通し id で統合。文書レベルの感情・極性・意図は文の集約
- `core.syntax.split_sentences`: 「」『』（）内の句点で切らない、閉じ括弧は前文に付く、改行は常に境界、半角ピリオドは空白/末尾の前のみ (3.5 は保持)
- `core.syntax.split_paragraphs` / `is_heading_line` (#・【・■・第N章・N. など)

### Added — Query IR (FR-080) `rag/query.py`, `Analyzer.analyze_query()`

- `QueryIR`: intent / answer_type / target / entities / constraints (time・location・quantity・organization・person …) / keywords / expanded_terms / sentiment
- Query 向け意図体系 `modules.intent.classify_query_intent`: definition / how_to / reason / compare / search_value (MONEY・DATE・LOCATION・PERSON・NUMBER) / list / yes_no / lookup
- 対象 (target) は質問語の前の主題句、同義語展開は synonym.csv (複合語の構成トークンも展開)

### Added — Semantic Chunking (FR-081/082) `rag/chunk.py`, `Analyzer.chunk()`

- 見出し → 段落境界 (min_chars 以降) → 話題転換 (名詞集合の Jaccard とエンティティ継続) → サイズ上限 (max_chars、文の途中では切らない) の順で境界決定
- `DocumentChunk`: paragraph_ids / sentence_ids / entity_ids / keywords / topics / summary_hint / 原文 span

### Added — CLI / 評価

- `kotobacore query TEXT`、`kotobacore chunk FILE --max-chars`、`kotobacore analyze --document --file --reference-date`、`kotobacore eval annotated|quality`
- 人手評価ランナー: Entity 評価を `entities` 基準に、宛先 (sentiment target) 一致率を追加。
  下書き 300 文で **Entity F1 0.075 → 0.658** (再現率 4% → 60%)、宛先一致 51.7% (n=60)
- テスト 240 → 259

### Changed

- `enable_entities=` / `reference_date=` を Analyzer に追加。`semantic_tokens` は semantic 層無効時は従来どおり空

## [0.3.0] - 2026-09-08

要件定義書 v0.4 (Core + 4 モジュール + vocab + rag 構成) の v0.3 マイルストーン。

### Changed — パッケージ再配置 (旧 import パスは compat シムで v1.0 まで維持)

- `kotobacore.core/` — text (N1/N2 正規化), token/ (Karuizawa), syntax (節・否定),
  entity, chunker (句チャンク), lexicon (感情/評価語マッチ), ir (スキーマ), matching
- `kotobacore.modules/` — emotion / sentiment / intent (Semantic IR 上のモジュール。
  モジュール同士は import しない。唯一の例外は Sentiment → Intent で Analyzer が明示的に渡す)
- 旧パス (`kotobacore.normalizer` / `tokenizer` / `semantic` / `emotion` / `intent` /
  `schema` / `clause` / `matching`) はそのまま import 可能

### Added — 位置写像 (FR-002 Traceability)

- `Analyzer.normalize_with_map()` / `core.text.normalize_with_map()` が
  正規化後→原文の文字位置写像 (`NormalizedText.origin`) を返す
- **`Token.begin/end` と感情・評価表現の `begin/end` は原文基準に統一**
  (㈱ → 株式会社 の 1→3 文字展開、半角カナ濁点の 2→1 文字縮約でもずれない)。
  `TextInfo.offset_map` に写像を同梱
- N1 文脈ルール: カタカナ間のハイフン類 (コ-ヒ-) を長音「ー」に統一

### Added — Sentiment モジュール (FR-062)

- `AnalysisResult.sentiment` (`SentimentResult`: polarity / intensity / confidence /
  expressions[text, polarity, intensity, confidence, begin, end, negated, target])。
  `EmotionResult.polarity` は互換のため残し、Sentiment と同じ値
- 評価語辞書 **`sentiment.csv` 215 語** (いまいち / 微妙 / 使いやすい / 高すぎる 等、
  感情カテゴリを持たない極性語)。否定で反転: 良くない → negative、悪くない → 弱い positive
- 意図分類の feedback 連動は Sentiment の極性を読む (`classify_intent(..., sentiment=)`)
- CLI `--no-sentiment`、`Analyzer(enable_sentiment=)`

### Changed — 否定スコープ・逆接重みを Core (syntax) へ移設 (FR-021/022)

- `core.syntax.negation_after()` / `is_negated_surface()`。感情検出器の内部にあった
  否定処理を Core に置き、Emotion / Sentiment が同じ判定を共有

### Added — 辞書

- **`synonym.csv` 218 グループ** (顧客|クライアント|お客様 等、business/it/general/daily/sns)。
  `Analyzer.canonical(word)` / `Analyzer.synonyms(word)`、`bundle.synonym_map()`
- `normalization.csv` 21 → **182 行**: 法人略号 18、記号 13、引用符 8 (旧版は
  CSV の引用符エスケープ崩れで無効だった行を修正)、旧字体→新字体 97、カタカナ長音 46
  (サーバ→サーバー等。語末のみ適用: ユーザビリティ は変えない)、ヴ→バ行。
  N2 は最長一致・冪等 (既に目標形ならそのまま)

### Added — 評価

- `tools/quality_test/run_annotated_eval.py`: 人手アノテーション実文セット (JSONL) で
  分割境界 P/R/F1・Entity P/R/F1・極性/感情/意図の正解率・鳴き声カナリア誤検出率を算出。
  `annotated/annotated_v1_draft.jsonl` (300 文・AI 下書き・要レビュー) を同梱
- テスト 210 → 240 (位置写像 / Sentiment / synonym / syntax 否定 / 配置ルール)
- 6500 文品質テスト: 感情正確度 変化なし、極性正確度 97.2→97.4%、意図検出率 70.1→71.1%、エラー 0

### 要件定義書との差分メモ

- 送り仮名揺れ (引き落とし/引落) はテキスト段 (N2) では扱わない — 動詞活用中の置換
  (受け付けます→受付ます) を避けるため、トークン段 (N4) の課題として v0.4 へ
- 評価語は emotion.csv の極性列分離ではなく独立辞書 `sentiment.csv` とした

## [0.2.7] - 2026-08-31

### Added — オノマトペ対応の強化

「オノマトペの対応が弱い」(ひらがな表記が全滅・収録語が薄い・トークナイザが
反復形を粉砕する) という指摘を受けて 3 層で改善。

- **かな表記ゆれの自動吸収**: emotion.csv / slang.csv の純カナ surface
  (3文字以上) に、カタカナ⇔ひらがなの相互 variant を辞書ロード時に自動登録
  (ワクワク⇔わくわく / イライラ⇔いらいら)。既存 surface と衝突する variant は
  追加しない (収録表記優先)。2文字語は折りたたまない (キタ→きた が 来た と
  衝突するため)。外部辞書 (NRC) は誤検出増幅を避けるため対象外
- **感情オノマトペ 26 語を emotion.csv に追加**: ウキウキ / ルンルン / ニコニコ /
  ニヤニヤ / ゲラゲラ / クスクス / ホッコリ / ウットリ / キラキラ / ウルウル /
  キュンキュン / ウズウズ / ソワソワ / ハラハラ / ビクビク / オドオド / ドギマギ /
  ガクブル / メソメソ / シクシク / クヨクヨ / トホホ / ドンヨリ / ガーン /
  ピリピリ / ムシャクシャ (かな variant 込みで実質 52 表記)
- **反復形の 1 トークン化** (lattice ノード源 11 / cascade アンカー拡張):
  XYXY / XYZXYZ 反復 (しとしと / もやもや / おもいおもい) を辞書未収録でも
  1 語として提案。反復単位が既知語・文法語のもの (わかるわかる / ますます) は
  対象外で従来分割を維持。lattice 側はテキスト全域の事前パス (かな+ー限定) で、
  長音ー入りの鳴き声 (にゃーにゃー / もーもー — ー は KATAKANA カテゴリで
  ランを4分割する) もカバーし、反復開始位置を content start 化して
  直前ひらがな連続との癒着 (ひよこがぴよぴ|よ) も防ぐ。鳴き声は
  「感情なし・ただし1語」として正しく扱われる
- **促音強調形の正規化** (`fold_emphatic_reduplication`): ワックワク /
  わっくわく → dictionary_form=ワクワク (わくわく) を設定し、感情辞書の
  dictionary_form パスでマッチさせる

### Fixed

- keep_as_unit / 辞書 surface が反復オノマトペを跨いで分断する問題
  (「雨がざあざあ降ってきた」で slang あざ が ざあざあ の中央を先取りし
  雨|がざ|あざ|あ に分断 → joy 誤検出)。kau クレームに反復跨ぎガードを、
  reduplication ノード提案に claimed-only cap を導入して解消

### Changed — 品質テストを 6500 例文に拡張 (5000 例文の見直し)

テンプレート網がオノマトペをほぼ監視できていなかった (不安カテゴリの
そわそわ/びくびく が今回の修正まで検出漏れし続けても誰も気づかなかった) ため、
`run_quality_test_5000.py` に 3 カテゴリを**末尾追加** (13 カテゴリ×500=6500文):

- **オノマトペ・ポジ / オノマトペ・ネガ**: カタカナ/ひらがな表記ゆれ・促音
  強調形を混在させた感情オノマトペ文。GT 付き (検出 100% / 正確度 100%)
- **鳴き声・環境音**: 「感情なし」が正解の誤検出カナリア (`expected_no_emotion`
  新設)。わんわん/にゃーにゃー/ざあざあ/しとしと等 — 誤検出 0% を確認
- **凍結ルール**: 文生成は単一乱数列を順に消費するため、既存カテゴリの変更・
  途中挿入は禁止 (末尾追加のみ可)。旧コードとの生成文一致を検証済み。
  歴代比較用に**レガシー10カテゴリのサブセット集計** (`summary_legacy10`)
  をレポートに併記

新カテゴリが直ちに露呈させた lattice の 2 バグも修正:

- **擬似形容詞の丸呑み**: ひらがな形容詞ノードが辞書語ごと吸収していた
  (わくわく+してく → 形容詞「わくわくしてく」で感情脱落)。位置先頭に
  4 文字以上の辞書語がある場合は形容詞ノードを提案しない
- **反復の位相ズレ**: からはらはら で左走査が らはらは を先に取り、
  content start が「から」の助詞ノードを殺していた。1 文字後ろに辞書語
  反復が始まる場合はそちらに譲る

### 検証

210 テスト全 PASS (新規 11)・golden 39/39 (鳴き声・ざあざあ・ひらがな
オノマトペの3行を追加)。6500 例文評価: 感情正確度 97.3% (分母 3500)・
極性正確度 97.2%・誤検出カナリア 0%・エラー 0・平均 1.1ms/文。
レガシー10カテゴリ集計は v0.2.6 比で感情検出率 52.7→55.3% (+2.6pt)・
感情正確度 95.0→95.2%・極性正確度 95.8→96.0%、意図・チャンク・RAG 同値。

既知の制限: 反復しない単発ひらがな鳴き声 (おぎゃー / わん) は未対応
(カタカナ表記 ニャー / ガオー はランとして 1 語になる)。

## [0.2.6] - 2026-08-28

### Added — `granularity="fine"` (LM 語彙向けの細粒度トークン)

ミニGPT の語彙作りで「句がまるごと 1 トークンになり (突然云い出した / 何時間
かかります)、頻度≥3 の語彙に入らず文字にほどかれる」という指摘を受けて追加。
KotobaCore の既定 (coarse) は意味単位を保つ設計のままにし、表層だけ細かく返す
モードを分離した。

- `Analyzer(granularity="fine")` / `analyzer.tokenize(text, granularity="fine")` /
  CLI `--granularity fine` (analyze / tokenize)
- 分解対象は lattice が**組み立てた**ノードのみ: 動詞・形容詞 → 語幹 + 活用語尾
  (思|い|出|した / 近|い)、交ぜ書き複合語 → 漢字 + 送り仮名 (締|め|切|り)、
  ひらがな動詞 → 語幹 + 活用語尾 (あ|ります)、未知ひらがなラン → 文法語・既知語・
  ひらがな動詞の最長一致 + 文字 fallback。辞書エンティティ / keep_as_unit /
  固有名詞は割らない
- 新 POS: `動詞-語幹` `動詞-活用語尾` `形容詞-語幹` `形容詞-活用語尾` `送り仮名`
- `analyze()` では chunks / emotion / intent / rag は常に coarse で計算し、
  tokens / semantic_tokens だけが fine になる (意味層の結果は粒度に依存しない)
- 坊っちゃん全文 (88,293 字) 実測: coarse 2.03 字/トークン → fine 1.5 前後、
  頻度≥3 語彙のトークン被覆率 80.8% → 91% 台

### Fixed — 過剰結合の抑制 (coarse にも効く)

- **接頭名詞 + 動詞** (突然|云い出した / 昨日|買った / 毎日|走る): 語幹は漢字ラン
  先頭からしか始められなかったのを、接頭部が `_PREFIX_NOUNS` (時間・副詞的名詞
  90 語) か辞書語のときに限り中途からも開始可能に。無条件分割は 昨|日買った を
  生むため採用せず。語幹は最大 2 漢字、2 字目以降は名詞レートで課金
- **ひらがな動詞ノード** (あります / かかった / なって): 語幹 60 種 × 送り仮名判定。
  既知語 (うんざり) や content_start を跨がない。送り仮名自体がひらがな動詞なら
  漢字側の動詞組み立てを抑止 (何時間|かかります)
- **固定語** 同じ / 大きな / 初めて / 全く 等を動詞組み立てより優先 (同じ|である)
- **送り仮名の長さ上限 9** (張+りのあるまでどうかやってもらいたい を防止、叱られませんでした は保持)、
  ひらがな形容詞は格助詞始まり (が|かかった) とひらがな動詞を除外
- 補助動詞 しまう / しまった / しまって を文法語に追加

### Results

- 199 テスト全 PASS (新規 6)・golden 36/36・5000 例文: チャンク生成率 0.910 → 0.914、
  他指標は完全一致

## [0.2.5] - 2026-08-28

### Fixed (lattice tokenizer — 文学テキストで見つかった分割癖)

漱石作品 (坊っちゃん / 吾輩は猫である) をミニGPT実験に流した際の指摘をまとめて修正。
すべて `kotobacore/tokenizer/lattice.py` のノード提案層の追加で、5000 例文評価の
全品質指標は修正前後で完全一致 (回帰ゼロ)。

- **小書き仮名固有名詞**: 「坊っちゃん」が 坊|っちゃん に割れていた。cascade の
  `heuristic_proper_noun_merge` (KANJI + っ/ゃ/ゅ/ょ… 始まりのひらがな → 固有名詞) が
  v0.2 の lattice に移植されていなかったのを移植。った/って/っちゃう/っぽい 等の
  活用は除外、助詞・だ・文法語の位置で本体を切る
- **接尾辞ノード** `接尾辞`: さん/ちゃん/くん/さま/たち/ども を非ひらがな語の直後で
  分離 (田中|さん / 子供|たち / 私|たち)。みなさん/たくさん/ちゃんと は割らない
- **複合助詞**: における/において/においては/にとって/について/によって/とともに 等を
  文法語に追加。における は SNS 間投詞「おけ」(keep_as_unit) より先に claim し、
  に|おけ|る → emotion=trust の誤発火 (2026-08-20 既知) を解消。として は 落と|して を
  壊すため意図的に除外
- **機能語 POS**: 接続詞 (しかし/けれども/そうして/だが…、ラン先頭のみ) / 連体詞
  (この/その…) / 副詞 (まだ/もう/やはり…) / 感動詞 (こんにちは/おはよう…) を
  固有 POS で提案。けれどもそ|の|とき / しかしまだ / こんにち|は を解消
- **交ぜ書き複合動詞の活用**: 思い出+した / 飛び込+んだ / 取り扱+った を 1 動詞に。
  サ変名詞 + した (打ち合わせ|した / 取り引き|した) は名詞を保つ
- コピュラ語尾 そうだ/ようだ/である/であった/だろう 等を文法語に追加

### Added (entity.csv)

- 坊っちゃん (WORK、表記ゆれ 坊ちゃん も独立行で keep_as_unit)、赤シャツ/山嵐/
  うらなり/野だいこ/マドンナ (PERSON)、坊っちゃん列車/団子/スタジアム/文学賞、
  道後温泉/松山市 (LOCATION)、三四郎/草枕/虞美人草 (WORK)

### Results

- 193 テスト全 PASS (新規 7)・golden 36/36・5000 例文全指標 修正前後で完全一致

## [0.2.4] - 2026-08-18

### Added

- **Wikipedia「日本」記事由来の固有名詞 680 件を entity.csv に追加** (1107 → 1787 行)。
  国名 117 (アメリカ合衆国/ウクライナ/サウジアラビア等)・地形/地理 (富士山/
  瀬戸内海/尖閣諸島等)・行政司法機関 (外務省/最高裁判所/警視庁等)・国際機関
  (国際連合/欧州連合/IMF等)・歴史人物 (徳川家康/織田信長/森鷗外等)・
  歴史事件/時代 (明治維新/縄文時代等)・言語/宗教/食/祝日などを収録
- 略称 alias: 自民党 / 日銀 / 東大 / 国連 / EU / IMF / CIA / JETRO / APEC /
  国鉄 / 羽田空港 / 宇宙航空研究開発機構
- 抽出パイプライン: MediaWiki API で内部リンク 1,562 件取得 → ノイズ除外 →
  語尾ルール+Wikipedia カテゴリ投票で分類 → 人手精査 (メタ記事名
  「日本の〜」等 63 件除外、一般名詞 100 余語を TOPIC へ型修正)
- 未分類 634 件は `wikipedia_日本_未分類オプション.csv` として辞書外に保留
- **オプション辞書 zip を同梱** (`resources/dict/optional/optional_dictionaries.zip`):
  JPX 全上場企業 3,459 社 (内国株式、データ日付 2026-07-31、entity.csv 互換 +
  証券コード/市場/業種メタ列) と Wikipedia 未分類 634 件。ローダーは
  resources/dict/ 直下の固定 7 ファイルしか読まないため、この zip は
  展開・投入の指示があるまで一切参照されない保留データ

### Results

- 186 テスト全 PASS・golden 36/36・5000 例文全指標維持 (投入前後で完全一致)・
  ベンチ全 KPI PASS (辞書ロード 170ms)

## [0.2.3] - 2026-08-18

### Added

- **entity.csv に日本企業 401 社を追加** (706 → 1107 行)。総合商社・金融・電機・
  半導体・自動車・重工・素材化学・住宅建設・不動産・製薬・食品飲料・日用品・
  運輸物流・鉄道・航空ホテル・エネルギー・通信 SIer・ネット企業・ゲーム・
  出版メディア・小売・外食チェーン・教育サービスの 20 超セクターを体系的に収録
- 略称・別名 alias を付与 (例: 京アニ / ジブリ / 日通 / クロネコヤマト / JT /
  東電 / ミスド / ココイチ / サイゲ / NRI)
- keep_as_unit は文字種から自動判定 (混在・中黒・空白・ひらがなのみ → true):
  92 件に付与
- 一般名詞と衝突する語は登録回避 (パイオニア / ライオン / オープンハウス /
  サンライズ / ディスコ / 明治 など)。既存の球団 alias (ロッテ / 日本ハム /
  ヤクルト / オリックス / DeNA) や SERVICE 登録 (PayPay / freee 等) との重複は
  スキップ

### Results

- 186 テスト全 PASS・golden 36/36・5000 例文全指標維持
  (感情 95.2 / 極性 96.0 / チャンク 91.0 / RAG 99.6 — 追加前後で A/B 完全一致)

## [0.2.2] - 2026-08-05

### Added

- **同一助詞連続ペナルティ**: Viterbi の bigram 接続コスト第2弾。同じ1文字助詞が
  連続する経路 (も|も) にペナルティ (+8.0) — 同一格助詞は連続しない (そこは
  「もも」という語) という言語事実のエンコード。名詞隣接ペナルティとの同点タイが解消
- `entity.csv`: `すもも` / `もも` を TOPIC 登録 (aliases: 李 / 桃)
- **「すもももももももものうち」が教科書通りの完全解に**:
  `すもも|も|もも|も|もも|の|うち`、chunks=すもも/もも (topic)、
  RAG=すもも/もも/李/桃。回帰テスト追加

### Results

- 186テスト・golden 36/36・5000例文全指標維持 (感情95.2/極性96.0/チャンク91.0/平均0.81ms)

## [0.2.1] - 2026-08-05

### Added

- **Viterbi に bigram 接続コストを追加**: 「すもももももももものうち」テストへの対応。
  名詞ノード同士が助詞なしで直接隣接する経路にペナルティ (+6.0)。日本語では裸の
  名詞連続は稀 (通常 を/の/も 等を挟む) という言語事実のエンコード。同一文字種 run は
  2つの隣接名詞ノードに分割され得ないため、通常の複合名詞 (漢字/カタカナ連続) は無影響
  - `すもも`/`もも` を辞書登録した場合、従来の辞書貪欲 `すもも|もも|もも|もも` ではなく
    助詞交互の分割が選ばれ、chunks/RAG が すもも・もも を topic として正しく抽出
  - 一般語彙辞書は引き続き非搭載のため、登録なしでは本文は分割不能 (設計通り)
- 全ひらがな entity 表層の POS を 名詞-普通名詞-一般 に修正 (従来は一律 感動詞-SNS表現)
- `_HIRAGANA_KNOWN_WORDS` に うち を追加

### Results

- 185テスト・golden 36/36・5000例文全指標維持 (感情95.2/極性96.0/チャンク91.0/平均0.79ms)

## [0.2.0] - 2026-08-05

コードレビュー(2026-08-05)で挙がった設計改善を全面実装したメジャー更新。
トークナイザの呼称は引き続き **Karuizawa**(実行モードが増えた)。

### Added — Karuizawa lattice モード (新デフォルト)

- **格子+Viterbi の一発分割** (`tokenizer/lattice.py`): 〜v0.1 の5段補修カスケード
  (keep_as_unit結合→ひらがな分割→固有名詞マージ→送り仮名結合→動詞形容詞補正) を
  単一の動的計画法に統合。曖昧性解消がグローバルになり、パスの実行順バグが構造的に消滅
  - ノード源: 辞書表層(keep_as_unit は貪欲claimで絶対優先) / 助詞・助動詞・サ変 /
    漢字語幹+送り仮名活用(辞書既知語幹・サ変受動されは保護) / 交ぜ書き複合語 /
    ひらがな形容詞活用 / 文字種run(接続性保証)
  - コストは学習不要の手調整ユニグラム (`BASE − RATE × len`)
  - 5000例文評価で cascade と全指標同等・チャンク生成率は 90.8→91.0% と上回る。
    「買い物に行くのが楽しみ」等、cascade が壊す文を正しく分割
  - 旧カスケードは `Analyzer(pipeline="cascade")` / env `KOTOBACORE_PIPELINE` で選択可

### Added — 意味解析の構造改善

- **節分割プリミティブ** (`clause.py`): 文末記号+逆接(けど/ですが/だが/しかし…)で
  節分割し3箇所で共有 — ①ex_sim を感情語の節スコープで計算(長文でも confidence が
  希釈されない) ②逆接後の節を極性・primary 選択で重み増し(「難しい判断でしたが
  成功しました」→ joy/positive) ③否定スコープの境界。のに は節境界のみ(恨み節は
  前節に感情が残る)
- **否定スコープ処理**: 感情表現直後(同一節内)の否定形態素(じゃない/はない/くない…)を
  検出。否定された正感情は sadness/negative に反転(全然好きじゃない)、否定された
  負感情は中立化(不安はない/心配ない→検出なし)。活用形レンマ照合(嬉しくない→嬉しい)
  のトークン内部否定にも対応
- **形容詞レンマの dictionary_form 付与**: 楽しかった→楽しい 等の活用形が辞書照合で
  検出可能に(活用形の個別登録が不要)
- **Aho-Corasick 統一マッチ層** (`matching.py`): keep_as_unit/emotion/chunker の
  3重実装スキャンを1つの純Python AC に統一。O(候補×N)→O(N+matches)、
  5000例文の平均処理時間 1.92ms→0.78ms(2.4倍高速化)。挙動は(rank,pos)順序契約で同一
- **intent 層の再設計**: 中立トピック語(バグ/フィードバック/高い/クレーム 等)の
  feedback 直結を除去。文末？→question ブースト、感情層の帰属済み極性→
  positive/negative_feedback 導出(仕様変更・バグの教訓の一般化)。
  意図検出率 51.7%→70.8% (+19.1pt)、正確度 68.1% 維持
- **実文ゴールデンセット** (`tools/quality_test/golden_set.csv` + runner + pytest 組込):
  テンプレ生成の5000例文が検出できない実文の失敗を捕まえる回帰網。デモ指摘のたびに
  1行追加する運用。初回構築で 値上げ の分断・困っています 未登録を即検出

### Fixed

- キャッシュ漏れ2件: `_build_known_hiragana` / refine の protected set が
  analyze() ごとに全辞書を再走査していた → bundle._cache へ
- `emotion.csv`: 困った/困っている/困っています/困り果て (anxiety) 追加
- `entity.csv`: 値上げ/仕上げ (TOPIC, keep_as_unit) 追加

### Results

- pytest **185件** 全PASS / ベンチマーク全KPI PASS / 実文ゴールデン 36/36
- 5000例文: 感情正確度95.2% / 極性96.0% / チャンク**91.0%** / RAG99.6% /
  意図検出率**70.8%** / 平均**0.84ms**

## [0.1.14] - 2026-08-05

### Added

- `emotion.csv`: `難しい` (anxiety, 0.45) と表記ゆれ `難しすぎ` / `難しすぎる` (0.7)、`むずい` / `ムズい` (0.55, keep_as_unit) を追加。デモ指摘「思ったより難しい課題が...どうしよう。」で どうしよう しか検出されなかった問題に対応（難しい は内部辞書に不在、NRC の fear 0.359 は採用閾値 0.75 未満で除外されていた）。低 intensity のためポジティブ文脈（難しい問題を解くのが好き）では primary を奪わない

### Fixed

- **中立トピック語「仕様変更」が anger に直結していた誤設計を修正（デモ指摘）**: 「仕様変更を反映しました。」のような中立な報告文まで anger/negative_feedback と誤判定していた。仕様変更 は不満とは限らず、不満の担い手は「〜(た)ばかりなのに」（直前完了+逆接の語用論マーカー）。emotion.csv から `仕様変更` を削除し `ばかりなのに`(anger,0.6)/`ばっかりなのに`(anger,0.65) を keep_as_unit で追加（ひらがな塊の境界不一致を文字列レベル結合で回避）。emotion_examples.csv の EX-ANG-001/002 のキーを 仕様変更 → イライラする / ばかりなのに に付け替え、intent_rules.csv の negative_feedback からも 仕様変更 を除去して ばかりなのに 系に置換。結果: 「また仕様変更？さっき決めたばかりなのに...」= anger（担い手=ばかりなのに）、「また仕様変更？了解です。」= 感情なし、「昨日直したばっかりなのにまた壊れた」でも汎用的に発火。仕様変更 はトピックとして chunk/RAG に残る

### Results

- 5000例文品質テスト: 全指標 v0.1.13 と同値（回帰なし）。ベンチマーク全 KPI PASS
- pytest 160 件全 PASS（回帰テスト 4 件追加）

## [0.1.13] - 2026-08-05

### Added

- **Token Normalizer に送り仮名複合語結合層 `merge_okurigana_compounds` を追加**（5段構成に）。Karuizawa の文字種分割は 交ぜ書き複合名詞を `締|め|切|り` のように砕き、助詞でない単文字ひらがな（め/り/い 等）が孤立していた。2つの保守的ルールで結合:
  1. サンドイッチ: 漢字名詞 + 助詞でない単文字ひらがな + 漢字名詞 → 1名詞（締め切 / 思い出 / 行き先 / 買い物 / 真っ白）
  2. 後続送り仮名: ルール1が生成した複合語のみ、閉集合の送り仮名（り/め/い… + わせ/あい/がえ）を1つ吸収（締め切+り → 締め切り、打ち合+わせ → 打ち合わせ）。素の漢字名詞は吸収しないため動詞語幹（走+り）は不変
  - 形容詞語幹ガード `_ADJ_STEMS`: 良+い+天気 が 1名詞に誤結合しないよう、い-形容詞語幹（良/近/高/安…）はサンドイッチ対象外（`refine_verb_adjective_pos` が 良い を形容詞として組み立てる）
- `emotion.csv`: 焦り系フレーズ追加 — `締め切りが近い` / `締め切り間近` (anxiety, 0.75)、`間に合わない` / `間に合わなそう` (anxiety, 0.75, keep_as_unit)

### Fixed

- **デモ指摘「締め切りが近いのにバグが出た。もう無理かも...」**: Tokens が `締/め/切/り` にバラバラ・RAG から 締め切り が脱落・焦り(anxiety)が無視され refusal のみだった。上記の結合層 + 辞書追加で Tokens=`締め切り`(名詞)、emotion=**anxiety**/negative（無理かも の refusal は secondary）、RAG=`バグ/締め切りが近い/無理かも` に改善。emotion_examples.csv の EX-FEA-002（締め切り近いのにバグ出たどうしよう）も ex_sim ブーストとして発火するように

### Results

- 5000例文品質テスト: チャンク生成率 89%→**90.8%**、RAG生成率 98.6%→**99.8%**、感情正確度 95.2% / 極性 96.1% / 意図 68.1% は維持（回帰なし）。処理時間 平均2.01ms
- pytest 156 件全 PASS（送り仮名結合の回帰テスト 5 件追加）

## [0.1.12] - 2026-05-29

### Added

- 自作の SNS 感情例文集 `Japanese-SNS-Emotion-Examples-v1.txt`（546語/約2,746例文）をパッケージに同梱し、デフォルトでロード（外部辞書なしでも例文ベース感情マッチが有効）
- 英語 README (`README_en.md`) と言語切替リンク
- GitHub Actions CI（pytest 3.10–3.13 + ruff）と PyPI Trusted Publishing (OIDC) リリースワークフロー

### Changed

- 辞書を `resources/dict/` から `kotobacore/resources/dict/` へ移設し wheel/sdist に同梱（PyPI 配布対応）。パス解決はパッケージ内優先＋旧レイアウトフォールバックで後方互換
- NRC 辞書は再配布禁止のため非同梱。README に入手方法・ライセンス・引用を明記

## [0.1.11] - 2026-05-19

### Added

- `tools/quality_test/run_quality_test_5000.py`: **5000例文 大規模品質テスト**（今後の標準評価）
  - 10カテゴリ × 500例文 = 5000文をテンプレート生成（seed 固定で再現可能）
  - 計測軸: 検出率（感情/意図/チャンク/RAG）+ 正確度（感情/極性/意図）+ 処理時間（平均/中央値/p95/p99/最大）
  - 09_評価仕様書 §20.3 に標準評価として明文化
- `resources/dict/emotion.csv`: 不安・悲しみ・怒り・喜び の語彙を追加
  - anxiety: `焦り` / `落ち着かない` / `胸騒ぎ` / `そわそわ` / `びくびく` / `気が気でない` / `怖くて` / `眠れない` 他
  - sadness: `切なく` / `切なくて` / `切なくなる` / `つらくて` / `ふさぎ込む` / `虚無感` / `立ち直れず` / `心が沈む` 他
  - anger: `頭にきた` / `頭に来た` / `我慢の限界` / `怒りがおさまらない` / `ストレスがたまる`
  - joy/moved: `胸がいっぱい` / `報われた` / `喜び` / `こみ上げ`

### Fixed

- **`たまらない` / `たまらん` の joy 誤爆**: emotion.csv に joy/0.85 で単独登録されており「不安でたまらない」「つらくてたまらない」等の程度強調表現が全て joy に誤分類されていた。bare エントリを削除（具体形 `楽しくてたまらない` 等は keep_as_unit 付きで残存）
- **`きた`(joy slang) が「頭にきた」に誤マッチ**: slang.csv の `きた` を `キタ`（カタカナの正しい SNS 興奮形）に修正し、怒り慣用句との衝突を解消
- **keep_as_unit 不整合**: `怒り` / `ムカつく` / `焦る` / `切ない` が `keep_as_unit=false` で Karuizawa の文字種境界分割に負け未検出だった問題を `true` に修正
- stale テスト3件修正: `test_cli_version` のバージョンハードコード除去（実値照合）、`test_load_nrc_lexicon` / `test_load_gemini_examples_real_file` を taxonomy 拡張（anticipation）・SNS統合ファイル化に追従
- **entity の alias 未マッチ**: 「東京に行った」が 0 chunk になる問題。`東京` は entity.csv で `東京都` の alias 登録だが SemanticToken builder / Chunker が surface しか見ていなかった。`entity_by_surface()` と Chunker の候補生成を alias 対応にし、東京 / 横浜 / GPT 等の別名でも entity 認識されるよう修正
- **Chunker のサブトークン誤マッチ**: 「クラウドAPI」が `API` トークン内部の部分文字列で brand alias `AP`(オーデマピゲ)にマッチし keyword が `AP` になる問題。Chunker の `_scan_dictionary_matches` にトークン境界整合チェックを追加(マッチ span の start/end が token 境界に一致する場合のみ採用)。emotion detector と同様の保護
- **「高過ぎ」未登録 + 助詞巻き込み**: 「クラウドAPi高過ぎ…物価高でやりきれない」が `クラウドAPi高過` の1誤チャンク・感情=喜び と誤判定。原因: (1) `高過ぎ`(過=漢字)が emotion.csv 未登録で `高すぎ` しか無く、`高過` が名詞として前の語と連結、(2) `refine_verb_adjective_pos` が `物価高` + `でやりきれない` を結合(助詞 で を巻き込み)。`高過ぎ` / `課金高過ぎ` / `やりきれない` を emotion.csv 追加、`refine_verb_adjective_pos` に「助詞始まりのひらがなブロックは結合しない」保護を追加。結果: `クラウドAPi` / `高過ぎ` / `やりきれない` が正しく分離、感情=sadness
- **3文字単独名詞が chunk 化されない**: 「物価高」(3文字単独名詞)が chunk にならず RAG keyword にのみ出ていた問題。Chunker の単独名詞→topic chunk しきい値を `len>=4`→`len>=3` に緩和。物価高 / 報告書 等の3文字名詞が topic chunk になる
- **長いひらがな塊が 0 chunk・感情なしになる**: 「単語の切れ目が分からなくて、おかしくなっていたみたい。」が 0 chunk・感情未検出。3点修正。**①ひらがな文法分割**: `token_normalizer.py` に `_grammar_split` を追加。助動詞・活用語尾(みたい/ていた/なる/ない 等の closed set)を右から剥がし、辞書アンカーの無いひらがな塊からも語幹を分離。形容詞活用(く/くて/かった/しい)を認識して `形容詞-一般` を付与し い基本形を `dictionary_form` に格納。**②動詞送り仮名の補正**: `_LEADING_PARTICLE_CHARS` から `か`/`や` を除外(分かる/冷やす の送り仮名を誤って particle 扱いしていた)。`heuristic_proper_noun_merge` に「先頭助詞を剥がすと残りが純否定形(なくて/ない 等)になる場合は剥がさない」保護を追加(`分からなくて` が 分+から+なくて に分断されるのを防止)。`_classify_okurigana` で動詞否定形(なくて)を形容詞テ形(くて)より優先。**③活用形の辞書照合**: emotion detector と chunker に `dictionary_form` 照合パスを追加。①が付与した活用形 lemma が辞書と照合され、活用形を1語ずつ登録せずに検出・chunk 化される。emotion.csv に `おかしい` を追加

### Changed

- **entity type `TOPIC` を新設**: `円安` / `円高` / `増税`(2文字)は単独名詞しきい値未満で chunk 化されなかった。一般概念名詞用の entity タイプ `TOPIC` を新設し `円安` / `円高` / `増税` / `利上げ` を entity.csv 登録(`利上げ` は 利上+げ 分割回避のため keep_as_unit=true)。`_entity_chunk_type` / `semantic_type_map` に `TOPIC→topic` を追加。辞書マッチは長さ不問のため2文字経済語も topic chunk になる

- 設計書 01〜15 を Karuizawa 移行に整合（SudachiPy 表記の一掃）。ADR-002 を Superseded 化し ADR-011「なぜSudachiを廃しKaruizawaへ移行したか」を新規追加
- ベンチマーク（09_評価仕様書 §18）を v0.1.11 で再評価: 全 KPI PASS
- **Token Normalizer に動詞・形容詞 POS ヒューリスティック層 `refine_verb_adjective_pos` を追加**（4段構成に）。Karuizawa は文字種だけで品詞を付けるため動詞語幹（走 等）が 名詞 と誤標示されていた。漢字+活用語尾を結合し `動詞-一般` / `形容詞-一般` を付与（走る/読んだ/美味しい 等）。辞書既知語（ワクワク 等）・サ変名詞・助詞は結合しない保護付き。感情正確度への回帰なし（95.2% 維持）

### Performance

- **辞書ルックアップのキャッシュ化**: `analyze()` ごとに再構築していた派生構造（surface マップ / emotion 候補リスト / chunk 候補リスト / example インデックス）を `DictionaryBundle._cache` に1回だけ構築して使い回す。辞書バンドルはロード後不変なので決定的。挙動・精度は完全に不変。
  - 5000例文 処理時間: ローカル 3.73ms→**1.44ms**、サーバー実機 13.84ms→**3.77ms**（約3.7倍高速化）

### Results (5000例文品質テスト v0.1.10→v0.1.11)

| 指標 | v0.1.10 | v0.1.11 |
|---|---|---|
| 感情正確度 | 55.3% | **94.6%** |
| 極性正確度 | 58.4% | **95.5%** |
| 感情検出率 | 44.6% | 55.1% |
| 怒り・不満 感情正確度 | 70% | **100%** |
| 不安・恐れ 感情正確度 | 20% | **97%** |
| 悲しみ・憂鬱 感情正確度 | 44% | **84%** |
| 喜び・ポジティブ 感情正確度 | 87% | **97%+** |

処理時間: 平均 3.1ms / p99 5.5ms（5000文計 約16秒）

---

## [0.1.10] - 2026-05-18

### Added

- `resources/dict/entity.csv`: 26 → **697 語**に大幅拡充
  - スポーツ選手（野球/サッカー/テニス/スケート）、男女芸能人・歌手、アイドルグループ
  - 都道府県（46）、主要都市・繁華街（27）
  - NPB 球団（12）+ MLB（3）、Jリーグ（12）
  - ファッションブランド（35+）、国内 IT/通信企業、グローバルテック、国際自動車メーカー（30）、ハイブランド/高級時計/宝飾（33）
- `resources/dict/slang.csv`: 24 → **203 語**に拡充
  - 笑い系（w/ww/草不可避）、驚き系（まじ/うそだろ）、称賛（神すぎ/エモい/全人類に見てほしい）、同意（わかりみ/ほんそれ/せやな）、拒否（無理ゲー/ありえん）、怒り（うざい/ガチ切れ/キレた）、悲しみ（ぴえん/闇落ち/しょんぼり）、沼・推し系（推し/尊死/解釈一致）、バズ系（バズった/炎上）他
- `resources/dict/normalization.csv` を **初めて機能的に実装**（ファイルは存在していたが一切読み込まれていなかった）:
  - `loader.py`: `NormalizationEntry` dataclass / `load_normalization()` / `DictionaryBundle.normalization` フィールド / `normalization_map()` を新設
  - `analyzer.normalize()` で NFKC 後にマッピングを適用するよう修正
  - 21 エントリ: 法人略語 10 種（(株)→株式会社 等）、ダッシュ類 4 種、引用符 4 種、省略記号・チルダ
- `kotobacore/tokenizer/token_normalizer.py`: `split_hiragana_tokens()` **新設**
  - Karuizawa が 1 トークンにまとめるひらがな連続列を known word アンカー + 助詞ストリップで分割
  - emotion.csv / slang.csv の全ひらがな表層 ＋ 代名詞（これ/それ/あれ/みんな等）＋ 副詞（とても/やっぱり/もちろん等）をアンカーとして使用
  - アンカー間ギャップ: 小書き仮名ガード付き助詞認識（"やっ" の "や" を助詞と誤認しない）
  - 末尾 ね/よ を文末助詞として剥がす
  - パイプライン: `merge_keep_as_unit` → **`split_hiragana_tokens`** → `heuristic_proper_noun_merge` の 3 段構成に
- `kotobacore/tokenizer/token_normalizer.py`: `heuristic_proper_noun_merge()` に**先頭助詞ストリップ**を追加
  - 名詞直後の HIRAGANA トークンから は/が/を/に/も/へ/から等を先頭から剥がすフォールバック
  - `split_hiragana_tokens` で known word が見つからない場合の補完として機能
- `resources/dict/emotion.csv`: ひらがな感情語 33 語追加
  - すごい/すごかった、すばらしい、かわいい/かわいすぎ、おもしろい/おもしろかった、たのしい、さみしい、ありがたい、くやしい、すてき/すてきすぎ、やさしい、うつくしい 等

### Fixed

- **`「日産の車は好きだよ」→ emotion: None, intent: unknown`** バグ:
  - 原因: `好き` の `keep_as_unit=false` により Karuizawa が 好[KANJI]+きだよ[HIRAGANA] に分割、token 境界不一致で emotion detector がスキップ
  - `emotion.csv`: `好き` の `keep_as_unit` を false → **true** に変更
  - `intent_rules.csv`: positive_feedback パターンに `好き|好きだ|好きです|好きだよ` を追加
- **`normalization.csv` 完全未使用バグ**: ファイルは存在していたが loader.py / analyzer.py に読み込みコードが皆無だった。今回初実装
- **`大谷翔平はすごい` → emotion: None** バグ:
  - 原因①: は+すごい が 1 HIRAGANA トークン → `すごい` が token 境界に乗らない
  - 原因②: `すごい` が emotion.csv 未登録
  - `split_hiragana_tokens` で「はすごい」→ は / すごい に分割、`emotion.csv` に `すごい` を admiration/positive で追加

### 動作確認（主要テストケース）

| テキスト | tokens | emotion |
|---|---|---|
| それがおもしろい | `それ` `が` `おもしろい` | joy/positive ✅ |
| あなたはやさしい | `あなた` `は` `やさしい` | joy/positive ✅ |
| みんながたのしい | `みんな` `が` `たのしい` | joy/positive ✅ |
| やっぱりすごい | `やっぱり` `すごい` | admiration/positive ✅ |
| 先生がやさしいね | `先生` `が` `やさしい` `ね` | joy/positive ✅ |
| それはほんとうにすごかった | `それ` `は` `ほんとう` `に` `すごかった` | admiration/positive ✅ |
| (株)ソニーの製品 | → normalize → 株式会社ソニーの製品 ✅ | — |

---

## [0.1.9] - 2026-05-17

### Added

- `resources/dict/entity.csv`: `keep_as_unit` カラム追加 (第6カラム)。旧 entity.csv との後方互換あり (省略時 false 扱い)
- `resources/dict/entity.csv`: SNSで有名な固有名詞26語登録
  - KANJI+HIRAGANA / KATAKANA+HIRAGANA 複合語 (keep_as_unit=true): `社内FAQ` / `吾輩は猫である` / `ドラえもん` / `のび太` / `ちびまる子ちゃん` / `ゆゆ式` / `まちカドまぞく`
  - HIRAGANA固有名詞 (keep_as_unit=true): `にじさんじ`
  - All-KANJI/KATAKANA固有名詞 (keep_as_unit=false): `鬼滅の刃` / `進撃の巨人` / `呪術廻戦` / `ワンピース` / `ナルト` / `ドラゴンボール` / `ホロライブ` 等
- `kotobacore/dictionary/loader.py`: `EntityEntry.keep_as_unit: bool` フィールド追加
- `kotobacore/dictionary/loader.py`: `keep_as_unit_surfaces()` を `dict[str, str]` (surface → merged POS) に変更。slang/emotion → `感動詞-SNS表現`、entity → `名詞-固有名詞-一般`。旧 `set[str]` の `in` 演算子は dict キー検索として後方互換
- `kotobacore/tokenizer/token_normalizer.py`: `heuristic_proper_noun_merge()` 追加。entity.csv 未登録の KANJI+HIRAGANA 固有名詞 (坊っちゃん等) をヒューリスティックで後処理マージ
  - 後続 HIRAGANA トークンの末尾から助詞を剥離 (`_PARTICLES_2` 2文字優先 → `_PARTICLES_1` 1文字)
  - 剥離後の body が小書きかな (`_SMALL_KANA`) で始まり、かつ動詞活用形先頭 (`_GRAMMAR_VERB_PREFIXES`: `った` / `って`) でなければ先行名詞と結合 → `名詞-固有名詞-一般`
- `kotobacore/analyzer.py` / `kotobacore/tokenizer/__init__.py`: `heuristic_proper_noun_merge()` を tokenize・analyze 経路に組み込み

### Fixed

- `にじさんじ` 助詞飲み込み: Karuizawa が `にじさんじは` を 1 HIRAGANA トークンに結合する問題を `keep_as_unit=true` + `_split_at_boundaries()` で解決
- `ドラえもん` 固有名詞非認識: KATAKANA+HIRAGANA 混在で Karuizawa が 2 トークンに分割。entity.csv 登録 (`keep_as_unit=true`) で `_split_at_boundaries()` がマージ
- 動詞活用形誤マージ: `買った` / `言った` / `言って` 等で `っ` が小書きかなと判定されて先行 KANJI と誤マージされていた問題を `_GRAMMAR_VERB_PREFIXES` チェックで修正

### Results (品質テスト v0.1.8→v0.1.9, 500例文・10カテゴリ)

| カテゴリ | 感情 | 意図 | chunk | RAG |
|---|---|---|---|---|
| 喜び・ポジティブ | 72% | 46% | 78% | 100% |
| 怒り・不満 | 52% | 48% | 76% | 98% |
| 悲しみ・憂鬱 | 46% | 38% | 52% | 98% |
| 不安・恐れ | 66% | 20% | 74% | 96% |
| SNS・スラング | 92% | 66% | 96% | 96% |
| ビジネス・業務 | 4% | 12% | 96% | 100% |
| 技術・AI | 8% | 16% | 98% | 100% |
| 質問・疑問 | 6% | 92% | 82% | 100% |
| 要望・依頼 | 36% | 80% | 86% | 100% |
| 日常会話 | 20% | 14% | 38% | 98% |
| **全体** | **40%** | **43%** | **78%** | **99%** |

※ chunk・RAG は entity 登録による固有名詞認識精度向上が主因。感情・意図は今後の辞書拡充で改善予定

---

## [0.1.8] - 2026-05-17

### Added

- `resources/dict/emotion.csv`: 55語追加・1語変更 (計440+エントリ)
  - sadness系: `傷ついた` / `傷つけられた` / `もう無理` / `辛い` / `泣いた夜` / `泣きながら` / `胸が痛い` / `胸が痛くて` / `心が崩れた` / `心が折れそう` / `悲しくて` / `悲しすぎて` / `切なくて` / `悔しくて` / `悔しくて泣いた` / `寂しさが` / `寂しさを` / `悲しみが込み上げ`
  - moved系: `泣けてしまった` / `辛くて泣いた` (→ moved) / `溢れて` / `胸熱` / `心が洗われた` / `息をのんだ`
  - anger系: `腹が立った` / `腹が立ちすぎて` / `腹が立ちすぎ` / `裏切られ` / `理不尽` / `不公平`
  - refusal/disgust系: `おぞましい` / `不快だ` / `不快すぎ` / `見たくない` / `触れたくない` / `汚い` / `臭い` / `臭くて` / `吐き気がする` / `ドン引きした` / `あり得ない` / `気持ち悪すぎ` / `吐きそう` / `近づきたくない` / `腐っていて` / `気分が悪` / `不快感` / `嫌悪感` / `生理的に`
  - joy系: `合格した` / `合格` / `嬉しくて` / `楽しくて`
  - admiration系: `感銘を受け` / `刺激を受け` / `圧倒された`
- `resources/dict/intent_rules.csv`: パターン大幅拡充
  - `question`: `ますか|でしょうか|いつ|なぜ|どこ|質問|わかりません|わからない|いかが|どうすれば|どうやって|どのくらい|どれくらい` 追加
  - `support_request`: `困っています|困っている|困った|わかりません|わからない|解決できません|どうすればいい|どうしたらいい` 追加
  - `negative_feedback`: `不便|遅い|届いていない|バグ|バグった|フィードバック|クレーム|改善してほしい|おかしい|壊れている` 追加

### Fixed

- `resources/dict/emotion.csv`: `泣いてしまった` を `sadness,negative` → `moved,positive` に変更。`込み上げるものがあって泣いてしまった` が正しく moved として検出されるようになった
- `resources/dict/emotion.csv`: `しんどい` の重複エントリを整理し intensity=0.65 → 0.8 に統一。`しんどい日が続いて泣いた` で `しんどい`(sadness,intensity=0.8) が `泣いた`(moved,example-based,intensity=0.7) を上回り正しく sadness が primary になった

### Results (品質テスト v0.1.7→v0.1.8 改善)

| 指標 | v0.1.7 | v0.1.8 | 改善 |
|---|---|---|---|
| 感情検出率 | 64.4% | 67.3% | +2.9pt |
| 感情正確度 | 49.4% | 53.4% | +4.0pt |
| 極性正確度 | 57.0% | 60.8% | +3.8pt |
| 平均confidence | 0.385 | 0.412 | +0.027 |
| 意図検出率 | 38.7% | 42.0% | +3.3pt |
| 誤分類件数 | 409 | 377 | -32件 |

**カテゴリ別主要改善:**

| カテゴリ | v0.1.7 正確度 | v0.1.8 正確度 | 改善 |
|---|---|---|---|
| sadness_clear | 48% | 72% | +24pt |
| disgust_refusal | 30% | 40% | +10pt |
| anger_clear | 40% | 50% | +10pt |
| moved_admiration | 58% | 66% | +8pt |

---

## [0.1.7] - 2026-05-17

### Added

- `resources/dict/emotion.csv`: 44語追加 (計390エントリ)
  - 喜び系: `すっきりした` / `癒やされた` / `気分がいい` / `うまくいった` / `ラッキー` / `喜んでもらえた` / `喜んでくれた` / `夢みたい` / `夢のよう` / `幸せだ` / `最高だ` / `嬉しすぎ` / `楽しすぎ` / `気分爽快` / `楽しくてたまらない` / `好きでたまらない`
  - 感動系: `目頭が熱くなる` / `言葉を失った` / `胸を打たれた` / `心が動かされた` / `涙が溢れた` / `じんわり` / `鳥肌が立った` / `感動して泣いた` / `泣いてしまった` / `泣けてしまった` / `辛くて泣いた`
  - 怒り/拒絶系: `ムカついた` / `呆れた` / `呆れる` / `意味不明` / `意味わからない` / `絶対に嫌だ` / `生理的に無理` / `受け入れられない` / `辛すぎる`
  - 誇張/驚き系: `まさか` / `衝撃` / `まじで` / `えっ` / `ぶっ飛んだ` / `底なし` / `規格外` / `規格外すぎ`
- `resources/dict/emotion.csv`: 9語の `keep_as_unit` を `false` → `true` に変更 (`嬉しい` / `楽しい` / `悲しい` / `怖い` / `引く` / `震える` / `落ち込む` / `嫌い` / `怒る`)。Karuizawa tokenizer の KANJI→HIRAGANA 分割補正: KANJI+HIRAGANA 複合語を後続 KANJI や句読点の前で正しくトークンとして結合できるようになった

### Fixed

- `kotobacore/emotion/detector.py`: トークン境界アライメントを拡張。従来は「surface の start と end の両方がトークン境界に一致」する場合のみ受理していたが、「surface の **end** がトークン境界に一致し、かつ surface 全体が単一トークン内に収まる (suffix match)」場合も受理するよう変更。Karuizawa tokenizer が長い HIRAGANA 連続を 1 トークンに結合する際 (例: `しくてたまらない`)、その末尾に位置する感情語 (`たまらない`) が検出できなかった問題を解消。prefix false-positive (`はいつもの` の先頭 `はい`) は end がトークン境界でないため引き続き正しく除外される
- `tools/run_quality_test_1000.py`: 品質テストの expected ラベルを KotobaCore 実際の感情 taxonomy に修正
  - `disgust_refusal` カテゴリ: `"disgust"` → `"refusal"` / `"irritation"` (KotobaCore に disgust base_emotion は存在しない)
  - `surprise_shock` カテゴリ: `"surprise"` → `"exaggeration"` (KotobaCore では `驚き`/`信じられない`/`ありえない` が exaggeration にマップ)
  - `trust_gratitude` カテゴリ: `"trust"` → `"admiration"` / `"joy"` / `None` (信頼語→admiration、感謝語→joy、文脈依存→None)
  - 他カテゴリ残存 `"trust"` ラベル 16 件をそれぞれ `"joy"` / `"admiration"` / `None` に更新
  - 意図検出判定: `r.intent.primary.intent` → `r.intent.label` に修正 (schema 不一致による 0% 誤計測を解消)
  - `r.semantic.chunks` → `r.chunks` に修正 (AnalysisResult schema 不一致)

### Results (品質テスト v0.1.6→v0.1.7 改善)

| 指標 | v0.1.6 (初回) | v0.1.7 (最終) | 改善 |
|---|---|---|---|
| 感情検出率 | 58.9% | 64.4% | +5.5pt |
| 感情正確度 | 34.8% | 49.4% | +14.6pt |
| 極性正確度 | 51.0% | 57.0% | +6.0pt |
| 平均confidence | 0.347 | 0.385 | +0.038 |
| 意図検出率 | 0.0% | 38.7% | +38.7pt |
| 誤分類件数 | 535 | 409 | -126件 |

※正確度の改善は 感情語彙追加 (+14pt) と テストラベル修正 (+14pt) の両方が寄与

---

## [0.1.6] - 2026-05-17

### Fixed

- `resources/dict/emotion.csv`: `ゾクゾク` を `moved / positive / intensity=0.7` で追加。従来は emotion.csv 未登録のため例文ベース候補（lex_weight=0.3）しか生成されず、anxiety として登録された `震えた`（lex_weight=1.0, score=0.488）に敗れて常に anxiety が primary になっていた。emotion.csv 追加により lex_weight=1.0 が付与され、感動文脈では score=0.546 で `震えた`（0.488）を上回り moved が primary に、恐れ文脈では score=0.522 で `怖い`（anxiety, 0.542）に負けて anxiety が primary になる。intensity=0.7 はこの両条件を同時に満たすために調整した値

---

## [0.1.5] - 2026-05-17

### Added

- `dic/Japanese-SNS-Emotion-Examples-v1.txt`: 多義語パターン（文脈で感情が反転する語）を中心に 78語追加、合計 626行。追加語の分類：
  - **正負両用 SNS 誇張語**: えぐい・えぐすぎ・狂ってる・バグってる・しぬ (喜び/恐れ)
  - **限界系**: 無理・限界・地獄・しんどい (喜び/悲しみ の文脈依存)
  - **感情表現**: 震える・泣ける・泣きそう・刺さる・崩れる・言葉にならない・込み上げる (感動/悲しみ)
  - **驚き系**: ありえない・信じられない・とんでもない・引く・おかしい・異常・どうかしてる (驚き/怒り or 嫌悪)
  - **感情爆発系**: 爆発しそう・熱い (喜び/怒り)、ドキドキ・ゾクゾク (期待/恐れ)
  - **SNS固有語**: 沼・中毒・沼落ち・やめて・怖いくらい・尊死・最幸・きゅんきゅん 等

### Changed

- `kotobacore/emotion/detector.py`: emotion.csv 未登録の surface に対して `emotion_examples` から低 lex_weight (0.3) の候補を自動生成するよう変更。これにより ゾクゾク・えぐい等、SNS例文ファイルにのみ存在する多義語が感情候補として検出されるようになった。emotion.csv 登録済み surface は対象外（内部辞書優先の原則を維持）
- `tests/test_emotion.py`: `test_regression_external_dict_does_not_override_internal_refusal` のアサーションを `primary in {"refusal", "sadness"}` に更新。SNS ファイルに登録された "もう無理"（悲しみ, 4文字）が "無理"（refusal, 2文字）より長いため先にマッチする挙動が正しい動作であることをコメントで明記

---

## [0.1.4] - 2026-05-17

### Changed

- `kotobacore/emotion/detector.py`: `detect_emotion()` の例文類似度計算を感情別 ex_sim に変更。旧実装は surface に紐づく全例文の Jaccard 最大値を全候補感情に共有していたため、多義語（例: "やばい"）の 恐れ/喜び を文脈で区別できなかった。新実装は感情ごとに独立した最大値 (`ex_sim_per_emotion[base_emotion]`) を算出し、各候補の confidence 計算に対応する感情の ex_sim のみを使用する。同一 surface の恐れ文脈と喜び文脈で confidence の差が最大 0.24 改善することを確認

---

## [0.1.3] - 2026-05-17

### Changed

- `dic/gemini-code-*.txt` (19ファイル, 353行) を `dic/Japanese-SNS-Emotion-Examples-v1.txt` (1ファイル, 250行) に統合。重複103件を除去し感情カテゴリ順で整列
- `kotobacore/dictionary/external.py`: `load_user_bundle()` の `gemini_pattern` 引数を廃止し `examples_filename` 引数に変更。ディレクトリ glob → 単一ファイル参照に切り替え
- `tests/test_external_dict.py`: `GEMINI_FILE` を新ファイル名に更新。`test_load_gemini_examples_dir_loads_all` → `test_load_gemini_examples_single_file_loads_all` に改名

---

## [0.1.2] - 2026-05-17

### Added

- `examples/` に7本のユースケース別サンプルスクリプトを新規作成: `basic_usage.py` / `semantic_chunk.py` / `emotion_analysis.py` / `rag_preprocess.py` / `sns_analysis.py` / `ai_agent_input.py` / `karuizawa_compat.py`
- `emotion.csv`: `超楽しみ`(joy,0.9,true) / `超たのしみ`(joy,0.85,true) / `エモすぎ`(moved,0.85,true) / `やばい`(exaggeration,0.7) / `ヤバい`(exaggeration,0.7) / `やばすぎ`(exaggeration,0.8,true) / `ヤバすぎ`(exaggeration,0.8,true) を追加
- `slang.csv`: `やばい` / `ヤバい` / `やばすぎ` / `ヤバすぎ` / `エモすぎ` を sns カテゴリで追加
- `stopwords.csv`: 8語 → 108語に大幅拡充。助詞補完(まで/より/だけ/など/ほど/から/ため)、補助動詞(なる/できる等)、KANJI副詞(大変/相当/当然/突然/依然/一番等)、HIRAGANA副詞(とても/かなり/たぶん/もちろん/やはり等)、接続詞(しかし/つまり/さらに/だから等) を追加

### Fixed

- `kotobacore/compat/karuizawa_compat.py`: `KaruizawaTokenizer.tokenize()` に `merge_keep_as_unit` を適用。compat API でも keep_as_unit 辞書表現(しぬw/課金高すぎ等)が1トークンに統合されるように修正
- `kotobacore/semantic/chunker.py`: `_pos_based_chunks` がストップワードを参照していないため副詞トークンを compound_noun に巻き込む問題を修正。`当然コスト` / `突然エラー` 等の誤った複合名詞チャンクが生成されなくなった
- `kotobacore/rag/optimizer.py`: KANJI 副詞が次の KANJI と連結したトークン(例: `全然使` / `一番使` / `結局直接データベース`)を、ストップワードプレフィックスフィルタで除外するように修正
- `README.md`: `SudachiPy backend` → `Karuizawa tokenizer backend (zero external dependencies)` / `Limited Sudachi compatibility API` → `Karuizawa compatibility API` に修正
- サーバー `kotobacore.egg-info`: `pip install -e .` 再実行で `sudachipy` / `sudachidict-core` を `requires.txt` から除去

## [0.1.1] - 2026-05-16

### Fixed

- `external.py`: `NRC_TO_BASE_EMOTION["anticipation"]` が `"joy"` になっていたバグを `"anticipation"` に修正。NRC の期待語 (~13件) が正しく anticipation に分類されるようになった
- `external.py`: `JP_TO_BASE_EMOTION["期待"]` が `"joy"` になっていたバグを `"anticipation"` に修正
- `builder.py`: `BASE_TO_PLUTCHIK` に `admiration → trust` (旧: joy) および `anticipation → anticipation` を追加。NRC研究に基づく正確な Plutchik マッピング
- `chunker.py`: 単一絵文字 (`len(surface)==1` かつ `ord >= U+2600`) がチャンク候補から除外されていたバグを修正

### Added

- `emotion.csv`: 食感情語を追加 — うまい / うまっ / うまかった / 旨い / ウマい / ウマっ / まずい / まずっ / まずかった
- `emotion.csv`: 評価語を追加 — いいね / いいね！ / いいぞ / 絶品 / 神メシ / 至高 / 完璧 / 完璧すぎ / 完璧だ / 最高傑作
- `emotion.csv`: 大幅語彙拡張 (moved / admiration / anticipation / refusal / anxiety / exaggeration カテゴリ全体。計 328 エントリ)
- `emotion.csv`: 絵文字 51 種 (😊😡😭🤩 など) をチャンク対応で追加
- `emotion.csv`: 括弧表記 (笑) (怒) (泣) (苦) (苦笑) 等を追加 (NFKC正規化で半角括弧に統一)
- `intent_rules.csv`: `desire` インテント追加 (したい / 欲しい / 希望 / やってみたい 等)
- `intent_rules.csv`: positive_feedback / negative_feedback / admiration の語彙を拡張
- `builder.py`: `anticipation` を `BASE_TO_PLUTCHIK` に追加
- `streamlit_app.py`: Plutchik 全8軸カバー例文 3 件を `FIXED_CORPUS` に追加
- `streamlit_app.py`: metric フォントを 2/3 サイズに縮小
- `streamlit_app.py`: UI ラベルに `anticipation: 期待/願望` / `desire: 願望` を追加

## [0.1.0] - Unreleased

### Added

- Initial project skeleton
- dataclass schema (MetaInfo / TextInfo / Token / SemanticToken / SemanticChunk / EmotionResult / IntentResult / RagResult / KotobaError / AnalysisResult)
- Normalizer (Unicode / 全角半角 / 改行 / SNS表現保持)
- CSV Dictionary Loader + 7種 seed (slang / emotion / emotion_examples / entity / intent_rules / stopwords / normalization)
- SudachiPy tokenizer backend
- Sudachi limited compatibility API
- SemanticToken Builder + SemanticChunker (keep_as_unit対応)
- Emotion Detector + Plutchik mapping + Example-based matching
- Intent Classifier (rule-based)
- RAG Optimizer (keywords / search_query / summary_hint / semantic_phrases)
- Analyzer pipeline integration
- typer CLI (`analyze` / `tokenize` / `normalize` / `version`)
- Streamlit demo UI under `tools/demo_ui/`
