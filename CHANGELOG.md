# Changelog

All notable changes to KotobaCore will be documented in this file.

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
