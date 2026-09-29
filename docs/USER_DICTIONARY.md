# ユーザー辞書と業種別辞書（v1.1）

KotobaCore は同梱辞書（`kotobacore/resources/dict/`）に加えて、**利用者が作った辞書**を読み込めます。社内用語・製品名・取引先名・業界用語を登録すると、次の 3 つが効きます。

- **分割**: 登録した語は 1 トークンになる（`keep_as_unit`）。例: 「D&O保険」「源泉徴収漏れ」
- **正規化**: 別名（`aliases`）で書かれていても `Token.normalized` が見出し語（`normalized`）にそろう。例: 「D&O保険」→「役員賠償責任保険」、「PPA」→「取得原価の配分」
- **Entity / 検索**: `analyze()` の Entity に載り、`search_terms()` の索引語にも出る（別名の元の書き方も `surface` として残る）

同梱の **業種別辞書** `builtin:dd`（M&A デューデリジェンス、409 見出し）は、辞書の作り方のサンプルも兼ねています（`kotobacore/resources/dict/domains/dd.csv`）。

---

## 1. 辞書ファイルの作り方

形式は同梱の `entity.csv` と同じ UTF-8 の CSV です。**必須の列は `surface` だけ**で、ほかは省略できます。

```csv
surface,type,normalized,aliases,priority,keep_as_unit
役員賠償責任保険,TOPIC,役員賠償責任保険,D&O保険|D&O Insurance,90,true
みなと精機株式会社,ORGANIZATION,みなと精機株式会社,みなと精機|MNT,95,true
源泉徴収漏れ,,,,,
```

| 列 | 省略時 | 意味 |
|---|---|---|
| `surface` | （必須） | 見出し語。本文にこの文字列があれば 1 語として扱う |
| `type` | `TERM` | 種別。Entity の `type` に出る（PERSON / ORGANIZATION / PRODUCT / TOPIC など自由） |
| `normalized` | `surface` と同じ | 正規化形。見出し語・別名のどれで書かれても `Token.normalized` がこの値になる |
| `aliases` | なし | 別名。`\|` 区切り。略語・英語表記・旧称・言い換え |
| `priority` | `100` | 優先度（大きいほど優先） |
| `keep_as_unit` | `true` | `true` なら必ず 1 トークン（ほかの分割候補より優先）。短い一般語は `false` を推奨 |

### 作るときのコツ（DD 辞書を見直したときの基準）

1. **別名には「同じもの」だけを入れる。** 別名は正規化形が見出し語に置き換わります。上位語・下位語・関連語を入れると、検索で別の概念が混ざります。
   - よくない例: 「サイバー攻撃」の別名に「ランサムウェア」、「退職給付引当金」の別名に「退職給付債務」、「市場規模」の別名に「TAM」
   - こうした語は **それぞれ独立した見出し** にします。
2. **多義語・一般語を別名にしない。** 「障害」「組合」「HD」「PE」「強み」のような語は、別の意味でも使われます。
3. **2 字以下の一般語は `keep_as_unit` を `false` に。** `true` のままだと、「配当」が「配当金」を「配当 / 金」に割るなど、ほかの複合語を割ることがあります。
4. **表記ゆれは辞書に書かなくてよい。** 全角・半角（ＥＢＩＴＤＡ）、カタカナの長音やウエ／ウェ、送り仮名の有無（引き当て金／引当金）は本文の正規化で吸収されます。
5. **見出し語と別名の重複をなくす。** 同じ文字列が 2 つの見出しに出ると、どちらに寄るかが辞書の順番で決まってしまいます。
6. **フォルダでまとめて渡すこともできる。** 同梱と同じファイル名（`entity.csv` / `synonym.csv` / `normalization.csv` / `okurigana.csv` / `sentiment.csv` / `emotion.csv` / `slang.csv` / `stopwords.csv`）で置いたフォルダを指定すると、各辞書に追加されます。

作った辞書は次のコマンドで確かめられます。

```
kotobacore tokenize "D&O保険の更新とMNT向けの売上" --dict my_terms.csv
kotobacore terms    "D&O保険の更新とMNT向けの売上" --dict my_terms.csv --plain
```

---

## 2. 設定ファイルに書いて自動で読み込む

設定ファイル（YAML）の `dictionaries` に並べておくと、`Analyzer()`・CLI・HTTP API・デモ UI のどれでも、コードを変えずに読み込まれます。

```yaml
# kotobacore.yaml
dictionaries:
  - ./dict/my_terms.csv   # 自社用語（先に書いたものほど優先）
  - ./dict/legal/         # 同梱形式の CSV を置いたフォルダ
  - builtin:dd            # 同梱の業種別辞書（M&A デューデリジェンス）
```

- **相対パス**は設定ファイルのあるフォルダから解決します。`~` も使えます。
- **優先順位**: `Analyzer(user_dict_path=...)` で渡した辞書 → 設定ファイルに先に書いた辞書 → 後に書いた辞書 → 同梱辞書。
- 見本: `examples/kotobacore.yaml` と `examples/dictionaries/my_terms.csv`

### 設定ファイルの探し方（最初に見つかったものを使う）

1. `Analyzer(config_path="...")`、CLI の `--config`
2. 環境変数 `KOTOBACORE_CONFIG`（`none` にすると探さない）
3. カレントディレクトリの `kotobacore.yaml`
4. `~/.config/kotobacore/config.yaml`

設定ファイルを無視したいときは `Analyzer(use_config=False)` を使います。

### 読み込まれている設定を確かめる

```
kotobacore config
```

使われている設定ファイル、辞書ごとのパス・存在・件数、同梱の業種別辞書の一覧を JSON で表示します。

---

## 3. Python から直接指定する

```python
from kotobacore import Analyzer

a = Analyzer(user_dict_path="my_terms.csv")                        # 1 つ
a = Analyzer(user_dict_path=["my_terms.csv", "builtin:dd"])        # 複数（先が優先）
a = Analyzer(config_path="conf/kotobacore.yaml")                   # 設定ファイルを明示
a.dictionary_paths()                                               # 有効な辞書（優先順）
```

`kotobacore.dictionary.apply_user_dictionary(bundle, path)` で、辞書バンドルに直接マージすることもできます（元のバンドルは変更されず、新しいバンドルが返ります）。

---

## 4. 業種別辞書 `builtin:dd`

| 項目 | 内容 |
|---|---|
| ファイル | `kotobacore/resources/dict/domains/dd.csv`（目録: `domains.json`） |
| 件数 | 409 見出し・別名 615 |
| 分野 | M&A 手続・ストラクチャー / 財務・会計 / 税務 / 法務・契約・規制 / 人事労務 / 事業・IT・ESG |
| 例 | D&O保険 → 役員賠償責任保険、PPA → 取得原価の配分、担保提供制限条項 → ネガティブ・プレッジ、BCP → 事業継続計画、みなし残業代 → 固定残業代 |

自社や業界の辞書を作るときは、`dd.csv` をコピーして書き換えるのが近道です。
