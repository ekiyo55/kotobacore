# 人手評価セット レビュー — AI 判定案付き (verdicts_v1_ai.json)

判定 537 件 / 257 文。gold を修正 (F) 55、gold の sentiment 削除 (D) 26、gold 正しい = system 課題 (G) 449、保留 (H) 7

## A. system 課題の内訳（= 対処計画。件数順）

| 分類 | 件数 | 内容 | 対処 |
|---|---|---|---|
| dict | 95 | 辞書に語を追加 | sentiment.csv / emotion.csv に語を追加（候補は各文の判定メモ） |
| rule | 56 | 意図ルール追加・誤発火 | 意図ルール: request (〜いただけますか/〜ください/〜てほしい/〜てくれない？/〜ないで/命令形)、desire (〜たい/〜といいな)、agreement (ほんとそれ/わかった/よね)、pricing (〜円もしたの/家賃上がる/値段の割に)、疑問文での評価語 (いい？) 抑止 |
| ctx | 55 | 文脈推論 (辞書外) | 辞書では取れない。gold は維持し『文脈推論』として計測外に扱うか、例文辞書 (emotion_examples.csv) で近似 |
| tok | 48 | 分割 (トークナイザー) | 分割の癖 (動詞+てる/ても、複合名詞、副詞 別に/いや/うーん)。ラティスの改良課題として記録 |
| cue | 45 | 意図: 個人手がかり (share_experience) | share_experience の個人手がかり拡充（体験動詞 〜てきた/〜した/泣いた/焦った、やった！、絵文字全域、身体状態） |
| ner | 40 | 固有名詞・日付の抽出 | 括弧内固有名 (「」『』)、漢数字の年月、相対日付 (先日/今期/来期/この前/こないだ/子どもの頃)、技術製品名、地名の辞書 |
| adv | 30 | 逆接の節重み・評価語不足 | 逆接後の節に評価語が無いケース。評価語追加で解決するものが大半 |
| rhet | 22 | 修辞疑問 | 修辞疑問 (〜すぎん？/高くない？/何回〜ても) を question にしない・極性を取る |
| canary | 17 | 括弧内の固有名 (canary) | 「」括弧内の語は固有名として感情・評価から除外 |
| neg | 15 | 否定・反語 (litotes) | 否定の反転 (飽きない/破らなかった = positive、期待していない = negative)、原形読みが 〜なってる/〜かった に届かない |
| holder | 15 | 第三者主体 → inform | 主語が第三者 (部長は/彼は/村人たちは) の感情文は inform に（宛先付けの holder を意図に使う） |
| num | 10 | 数値表現 (小数・版番号・桁区切り・単位) | 小数 1.8・版番号 2.3.0・桁区切り 5,000・単位 ms・回数 (一度/二人) の扱い |
| fw | 1 | 全角英数 | 全角英数の店名 (NFKC 後の 123号 を QUANTITY にしない) |

## B. 適用した gold 修正

- sentiment cleared: 26
- intent ← value: 16
- entities ← system: 16
- emotion ← value: 10
- tokens ← system: 7
- entities += : 5
- entities ← value: 1

## C. 保留 / 手動対応

- sns-007/sentiment: adv 文全体の極性を逆接後 (ケーキ:positive) とする gold は妥当。system は positive を返しているので不一致は target 別の集計方法の問題
- sns-025/emotion: ctx 二重否定+逆接。label debatable と note にもある
- tech-048/sentiment: ctx 笑った (joy) vs AI への negative 評価。gold の negative は文脈推論
- literary-004/emotion: ctx 泣いた = sadness/moved は文脈次第 (note どおり)
- literary-017/sentiment: ctx 美しい嘘 の極性は note どおり debatable
- literary-026/sentiment: ctx 語り手の賞賛は文脈推論
- literary-050/emotion: ctx 涙 = moved/sadness

## D. 文ごとの判定

**sns-002** — 新しいiPhone買ったけど正直そこまで感動しない。
- tokens: F:tokens=sys 感動|しない は サ変分割の設計どおり。そこ|まで も許容
- sentiment: G:neg 感動しない (否定) を製品評価として取る = 感情語+製品 Entity → negative の派生 (未実装)

**sns-003** — 明日のライブ、わくわくが止まらない！
- entities: F:entities+=ライブ/EVENT gold の漏れ
- emotion: G:dict わくわく は anticipation 側に寄せる (現 joy)

**sns-004** — 電車遅延でイライラする…また遅刻だよ。
- sentiment: D 感情文 (イライラ)。遅刻 も感情ではない
- intent: G:cue share_experience: 遅刻だよ の『よ』・…' を個人手がかりに

**sns-005** — 隣の猫がにゃーにゃー鳴いてる。
- tokens: G:tok 鳴いてる は 1 語 (動詞+てる の結合漏れ)

**sns-006** — 渋谷のスクランブル交差点、人多すぎて疲れた😩
- tokens: G:tok スクランブル交差点 は複合語、人多すぎて は 人|多すぎて
- sentiment: D 感情文 (疲れた)
- emotion: F:sadness 疲れた は sadness 寄りで system 妥当。irritation は文脈推論

**sns-007** — このカフェ、コーヒーは微妙だけどケーキは神。
- tokens: F:tokens=sys 微妙だ の コピュラ結合は N4 の形容動詞扱い
- sentiment: H:adv 文全体の極性を逆接後 (ケーキ:positive) とする gold は妥当。system は positive を返しているので不一致は target 別の集計方法の問題

**sns-008** — 誰か新宿でおすすめのラーメン屋教えて！
- sentiment: G:rule おすすめ が評価語として発火 (依頼文では評価でない)
- intent: F:support_request 教えて依頼は support_request でも request でも可 → system 採用

**sns-009** — え、ブルースカイズ再結成ってマジ？？
- entities: G:ner 架空バンド名 (辞書外)。接尾辞なし固有名詞は文脈推論

**sns-010** — 3年ぶりに実家帰ったら犬が覚えててくれて泣いた🥲
- tokens: G:tok 年ぶり|に、実家|帰ったら、覚えててくれて 系の結合

**sns-011** — 正直、今回のアップデートは改悪だと思う。
- tokens: F:tokens=sys 改悪だ コピュラ結合
- sentiment: G:dict 改悪 を sentiment.csv (negative) に追加
- emotion: G:ctx irritation は文脈推論
- intent: G:dict 改悪 追加で negative_feedback になる

**sns-013** — 田中さんの新曲、何回聴いても飽きない✨
- tokens: G:tok 聴いても の結合
- sentiment: G:neg 飽きない = 否定で positive (litotes)
- emotion: G:neg 飽きない → admiration は否定反転の設計外
- intent: G:rhet 何回…ても は疑問でない

**sns-014** — フォロワー1万人突破！！みんなありがとう🙏
- intent: G:cue ありがとう+！+絵文字 = share_experience (現 rule が positive_feedback)

**sns-015** — 悪くないんだけど、リピートはしないかな。
- tokens: G:tok んだ|けど, はしないか の分割
- sentiment: G:adv 逆接後の節 (リピートはしない) を negative と取る = 節重みは実装済だが評価語がない
- intent: G:adv 同上

**sns-016** — 【拡散希望】10月5日に代々木公園で保護猫譲渡会やります！
- intent: F:inform 拡散希望 は依頼だが告知文。inform でも可 (note どおり)

**sns-017** — ぴえん🥺推しのグッズ売り切れてた…
- emotion: G:dict ぴえん を sadness に (現 admiration は誤り) — slang.csv 確認

**sns-018** — ＡＢＣストア１２３号店限定のスニーカー、ゲットしたぜ😎
- entities: G:fw 全角英数の店名 + 号店 接尾辞。NFKC 後に 123号 を QUANTITY 化するのは誤り

**sns-019** — なんで月曜って来るの早いんだろ😇
- tokens: G:tok なんで、月曜|って、ん|だろ
- sentiment: D 感情文。月曜:negative は文脈推論
- emotion: G:ctx
- intent: F:share_experience 修辞疑問の愚痴は体験共有として system 採用可

**sns-020** — 映画『夜明けの列車』、泣きすぎて目が腫れた。
- tokens: G:tok 『』内の作品名は 1 語 (ner と連動)
- entities: G:ner 『』括弧内を WORK として抽出 (未実装)
- sentiment: D 感情文 (泣きすぎて)
- emotion: G:dict 泣きすぎ → moved は文脈依存 (泣いた=sadness/moved)。moved 寄せは辞書で難しい → ctx
- intent: G:cue 泣きすぎて 等の体験表現

**sns-021** — 今日はぽかぽか陽気で散歩日和🌸
- sentiment: D 描写文。極性なし
- emotion: G:dict ぽかぽか (joy) 追加
- intent: G:cue 絵文字 🌸 が手がかりに入っていない (範囲外の絵文字)

**sns-022** — 楽しみにしてたのに雨で中止とか、ほんと最悪。
- emotion: F:anger 最悪 は anger/irritation。gold sadness は文脈推論
- intent: F:negative_feedback 中止への不満 = feedback で可

**sns-024** — マルコ堂の新作プリン、350円でこの味はすごい。
- entities: G:ner マルコ堂 = 堂 接尾辞を BRAND/ORG に追加

**sns-025** — 嬉しくないと言えば嘘になるけど、素直に喜べない。
- emotion: H:ctx 二重否定+逆接。label debatable と note にもある
- intent: G:cue

**sns-027** — 推しが尊すぎて生きるのが辛い（良い意味で）
- intent: F:positive_feedback admiration と positive_feedback は近接。system 採用

**sns-029** — 3日連続で残業とかブラックすぎん？
- sentiment: G:dict ブラック (企業) を negative 評価語に
- emotion: G:ctx
- intent: G:rhet 〜すぎん？ は修辞疑問

**sns-030** — この写真、加工なしでこれ？信じられない😳
- sentiment: D 驚き文。写真:positive は文脈推論
- intent: F:share_experience 修辞疑問 → 体験共有で可

**sns-031** — ちょっと待って、これ2019年の投稿じゃん。
- emotion: G:ctx 2019年の投稿じゃん の驚きは文脈推論

**sns-032** — 眠い。とにかく眠い。
- intent: G:cue 眠い (身体状態) の自己申告 = share_experience の手がかり不足

**sns-033** — 全然期待してなかったけど、この漫画めっちゃ面白い！
- emotion: G:neg 期待してなかった は否定 (anticipation 消去) + 面白い (joy) を採るべき
- intent: G:adv 逆接後の評価 (面白い) → positive_feedback

**sns-034** — 値上げばっかりで、もう外食できないよ…
- entities: F:entities+=値上げ/TOPIC 許容 (TOPIC は評価に使わない)
- sentiment: G:dict 値上げばっかり → 値上げ を negative 評価語に
- emotion: G:ctx

**sns-037** — いいね押しすぎて指が疲れた笑
- sentiment: G:rule いいね が評価語として発火 (SNS の『いいね』は名詞)
- intent: G:rule 同上 → share_experience

**sns-039** — なんか今日はモヤモヤする。理由はわからない。
- emotion: G:dict モヤモヤ を anxiety に (現 irritation)
- intent: G:cue 今日は + 個人 → share_experience (現 feedback は感情極性由来)

**sns-040** — 「感動」って名前のパン屋、駅前にできてた。
- entities: G:canary 「」括弧内の固有名化 (未実装)
- emotion: G:canary 同上で感情除外
- intent: G:canary

**sns-041** — 来週の花火大会、雨降らないといいな🎆
- sentiment: G:rule 花火大会 が positive 評価語?? (誤発火の原因調査)
- emotion: G:ctx 願望 (〜といいな) = anticipation は文脈推論
- intent: G:rule 〜といいな = desire ルール追加

**sns-042** — ぶっちゃけ値段の割に量が少なすぎ。
- sentiment: G:dict 少なすぎ を negative に (量の不満)
- emotion: G:ctx
- intent: G:rule 値段の割に → pricing_complaint ルール

**sns-043** — 母の手作り弁当、毎日ありがたい。
- sentiment: G:dict ありがたい を positive 評価語に
- intent: G:cue 母の… 個人手がかり

**sns-044** — 京都の紅葉、写真じゃ伝わらない美しさだった。
- sentiment: G:dict 美しさ を positive 評価語に (美しい はある)
- emotion: G:dict 美しさ → admiration
- intent: G:cue

**sns-045** — え、待って、無理、可愛すぎる🫠
- sentiment: D 感情文
- emotion: G:ctx 無理 のスラング用法 (かわいすぎ が primary になるべき = 可愛すぎる 未収録 → dict)
- intent: F:admiration or positive_feedback 可

**sns-046** — バイト先の店長、口は悪いけど面倒見はいい。
- sentiment: G:adv 逆接後 (面倒見はいい) を優先する集計
- intent: G:adv 同上

**sns-047** — リプ欄が荒れてて見るのがしんどい。
- sentiment: D 感情文 (しんどい)
- emotion: F:sadness しんどい は sadness/irritation。disgust は文脈推論
- intent: G:cue

**sns-048** — フォロバありがとうございます！これからよろしくお願いします🙇
- intent: F:positive_feedback 挨拶の謝意。none でも可だが system 採用

**sns-049** — ぐっすり寝たのに、まだだるい。
- sentiment: D 感情文 (だるい)
- intent: G:cue のに + 個人

**sns-050** — 2万円のイヤホン、音は最高だけど耳が痛くなる。
- sentiment: G:adv 逆接後 (耳が痛くなる) を negative に
- emotion: G:adv 同上
- intent: G:adv

**sns-051** — ねこがすやすや寝てる。平和。
- sentiment: G:dict 平和 を positive 評価語に
- intent: G:cue

**sns-052** — 誰か一緒にマラソン出ない？12月の湘南のやつ。
- entities: G:ner 湘南 を entity.csv に
- intent: G:rhet 〜出ない？ の誘い = question ルール (否定疑問)

**sns-053** — 昨日のドラマの最終回、納得いかない。
- sentiment: G:dict 納得いかない を negative 評価語に
- emotion: G:ctx
- intent: G:dict 同上

**sns-054** — やばい、財布落とした。誰か見てない？
- emotion: G:ctx 財布落とした → anxiety は文脈推論。やばい は強調

**sns-055** — 新しいバイトの先輩が優しくて安心した。
- intent: G:cue 安心した (感情) + 個人 → share_experience。先輩 が PERSON 扱いでない

**sns-056** — 通知がピロピロうるさすぎてミュートした。
- sentiment: G:dict うるさすぎ を negative 評価語に
- emotion: G:dict うるさい を irritation に
- intent: G:cue

**sns-057** — ここのタピオカ、正直ブームの時より美味しくなってる。
- sentiment: G:neg 美味しくなってる は評価 (原形読みが 〜なってる に届かない)
- emotion: G:dict 同上 → joy/admiration
- intent: G:dict

**sns-058** — 今年の夏は暑すぎて外出する気にならない。
- entities: F:entities=今年/DATE 今年の夏 は句。system 妥当
- sentiment: G:dict 暑すぎ を negative 評価語に
- emotion: G:ctx
- intent: G:cue

**business-001** — お世話になっております。株式会社山田商事の鈴木です。
- tokens: G:tok お世話|に|なっております
- entities: G:ner 鈴木です の 人名 (接尾辞なし)
- intent: F:inform 挨拶文は inform で可

**business-002** — 2025年度の売上は前年比12％増の45億円となりました。
- entities: F:entities=sys 12％ は NFKC 後 12% で同一

**business-003** — 来週の定例会議は水曜10時に変更いたします。
- tokens: G:tok 変更いたします の結合

**business-004** — 貴社のご提案、大変魅力的に感じております。
- tokens: G:tok ご提案、大変|魅力的
- sentiment: G:dict 魅力的 を positive 評価語に
- emotion: G:dict 魅力的 → admiration
- intent: G:dict

**business-005** — 恐れ入りますが、見積書を再送いただけますでしょうか。
- tokens: G:tok 再送いただけますでしょうか
- intent: G:rule 〜いただけますでしょうか = request ルール

**business-006** — 納期が遅れているのに連絡がないのは困ります。
- sentiment: G:dict 困ります を negative 評価語に
- emotion: G:dict 困る → irritation
- intent: G:dict

**business-007** — ㈱ミライ電機との契約は3月末で終了予定です。
- entities: F:entities=sys ㈱ は N1 で 株式会社 に展開 (仕様どおり)、3月末 は 3月 で可

**business-008** — 田中部長は今回の結果に大変満足されていました。
- tokens: G:tok 田中|部長、大変|満足されていました
- intent: G:holder 第三者 (部長は) の感情は inform

**business-009** — 単価5,000円は予算を大きく超えており、再検討をお願いします。
- tokens: G:num 5,000 の桁区切りを 1 語に
- sentiment: G:dict 大きく超え を negative 評価に (難)
- intent: F:request pricing_complaint と request の複合。system 採用可

**business-010** — 会議室の空調がガンガン効きすぎて寒いです。
- tokens: F:tokens=sys 寒いです の結合は許容
- sentiment: G:dict 寒い/効きすぎ を negative 評価語に
- emotion: G:ctx
- intent: G:dict

**business-011** — 新サービス「Kanso」は6月1日より提供開始いたします。
- tokens: G:tok 新サービス、6月1日、開始いたします
- entities: G:ner 「」括弧内 = SERVICE/PRODUCT 抽出 (未実装)

**business-012** — 御社の対応は迅速で、大変助かりました。
- emotion: G:dict 助かりました を trust に

**business-013** — 先日の説明会には約200名の方にご参加いただきました。
- tokens: G:tok には、ご参加いただきました
- entities: G:ner 先日 を DATE に

**business-014** — 品質に問題はないものの、コスト面で採用は見送ります。
- tokens: G:tok ものの、コスト面
- sentiment: G:adv 見送ります = 判断 negative (評価語なし)
- emotion: G:dict 見送る → refusal
- intent: G:adv

**business-015** — 本件、佐藤様にもＣＣでご共有いただけますか。
- intent: G:rule 〜いただけますか = request

**business-016** — 今期の目標未達は非常に残念ですが、原因は明確です。
- tokens: G:tok 目標|未達、非常に
- entities: G:ner 今期 を DATE に
- sentiment: D 感情文 (残念)
- intent: G:adv 感情は前節、後節は中立 → inform (逆接で後節優先が裏目)

**business-017** — 弊社は2026年4月に大阪支社を開設いたしました。
- tokens: G:tok 2026年4月、開設いたしました

**business-018** — ご返信が遅くなり、大変申し訳ございません。
- tokens: G:tok ご返信、遅くなり
- intent: F:inform 謝罪文は inform で可

**business-019** — 「感動」は当社の新型加湿器のブランド名です。
- tokens: G:tok 新型|加湿器、ブランド名
- entities: G:canary 「」括弧内固有名
- emotion: G:canary
- intent: G:canary

**business-020** — 出荷数は月間３０００台を超える見込みです。
- entities: F:entities=sys 全角数字は NFKC で同一

**business-021** — 来期の予算案について、ご意見をお聞かせください。
- entities: G:ner 来期 を DATE に
- intent: G:rule お聞かせください = request

**business-022** — 正直なところ、今回の提案には期待しておりません。
- sentiment: G:neg 期待しておりません = anticipation 否定 → negative 評価 (派生未実装)
- intent: G:neg

**business-023** — 山本様のご尽力には深く感謝しております。
- sentiment: G:dict 感謝 を positive 評価に (感謝しております)
- emotion: G:dict 感謝 → moved

**business-025** — 新工場の稼働開始は来年3月を予定しております。
- entities: F:entities=sys 来年3月 は 来年+3月 で可。新工場/ORGANIZATION は誤り → G:ner

**business-026** — 御社製品「ハヤブサ」の不具合報告が3件届いております。
- entities: G:ner 「」括弧内 PRODUCT

**business-027** — 会場の音響が悪く、後方の席では聞き取れませんでした。
- sentiment: G:dict 悪く (悪い の連用) を評価に = 原形読み
- emotion: G:ctx
- intent: G:dict

**business-028** — 誠に恐縮ですが、納品日を1週間延ばしていただけないでしょうか。
- intent: G:rule 〜いただけないでしょうか = request

**business-029** — 株主総会は6月27日午前10時より東京本社で開催します。
- entities: F:entities=sys 東京本社 ORG / 株主総会 TOPIC は許容

**business-030** — 若手社員の成長ぶりには目を見張るものがあります。
- sentiment: G:dict 目を見張る を positive に
- emotion: G:dict 目を見張る → admiration
- intent: G:dict

**business-031** — この価格では利益が出ないため、契約は見送らせていただきます。
- sentiment: G:dict 利益が出ない → negative (難)
- emotion: G:dict 見送らせていただきます → refusal
- intent: G:rule この価格では = pricing_complaint

**business-032** — システム障害により、本日午後の受付を停止しております。
- entities: G:ner 午後 を TIME に

**business-033** — 御社の新オフィス、とても素敵ですね。
- emotion: G:dict 素敵 (漢字) を admiration に (すてき はある)

**business-035** — 経費精算の締切は毎月25日です。ご注意ください。
- entities: G:ner 毎月25日 を DATE に (現 QUANTITY)
- intent: G:rule ご注意ください = request

**business-036** — 前回の打ち合わせでは有意義なご意見を多数いただき、感謝申し上げます。
- sentiment: G:dict 有意義 を positive 評価に

**business-037** — 決して安くはありませんが、投資に見合う効果が期待できます。
- sentiment: G:adv 逆接後 (効果が期待できます) positive
- intent: G:adv

**business-038** — 御社サーバーの応答が遅く、業務に支障が出ております。
- sentiment: G:dict 支障 を negative 評価に
- emotion: G:ctx
- intent: G:rule 支障が出ております = support_request

**business-039** — 第3四半期の営業利益は8億円で着地しました。
- entities: G:ner 第3四半期 を DATE に

**business-040** — 上司はこの企画にまったく乗り気ではないようです。
- sentiment: G:neg 乗り気ではない = 否定で negative (乗り気 未収録)
- emotion: G:holder 上司の態度 → refusal は文脈推論

**business-042** — 今回のプロジェクトは、社員一同わくわくしながら取り組んでおります。
- emotion: G:dict わくわく → anticipation

**business-043** — 弊社の売上高は3年連続で過去最高を更新しました。
- sentiment: G:rule 過去最高 が評価語発火 (事実報告)。D でも可
- intent: G:holder 事実報告は inform

**business-044** — 展示会「テックフェア2026」への出展を決定しました。
- entities: F:entities+=展示会/EVENT 許容

**business-045** — 社内報の新コーナー「よろこび」への投稿を募集します。
- entities: G:canary 「」括弧内 WORK
- intent: G:rule 募集します = request

**business-046** — 正直、この見積もりには納得しかねます。
- sentiment: G:dict 納得しかねます を negative に
- emotion: G:dict → refusal
- intent: G:rule 見積もり + 納得しかねる = pricing_complaint

**business-049** — 当社の株価は発表後に一時５％下落しました。
- entities: F:entities=sys 全角 % は同一

**business-051** — 御社の技術力は業界でも屈指だと認識しております。
- sentiment: G:dict 屈指 を positive に
- emotion: G:dict 屈指 → admiration
- intent: G:dict

**business-052** — 現状のままでは来年度の黒字化は難しいと考えます。
- intent: G:holder 難しいと考えます は見通し = inform (難しい が評価語発火)

**business-054** — 「怒り」は弊社ゲーム部門の新作タイトルです。
- entities: G:canary 「」括弧内 WORK
- emotion: G:canary
- intent: G:canary

**business-055** — 提案内容は悪くないのですが、スケジュールが現実的ではありません。
- sentiment: G:adv 逆接後 (現実的ではありません) negative
- intent: G:adv

**business-056** — 新製品の受注が好調で、生産が追いついておりません。
- sentiment: G:dict 好調 を positive に
- intent: G:rhet 追いついておりません は疑問でない (？ なし) → question 誤り原因調査

**business-057** — 部長は取引先の対応に激怒していました。
- sentiment: D 感情文 (激怒)
- intent: G:holder 部長は = 第三者 → inform

**business-059** — Ｂ２Ｂ向けＳａａＳ市場は年率２０％で成長しています。
- entities: F:entities=sys 全角は同一

**business-060** — 「安心」という名の保険商品を来月発売します。
- entities: G:canary 「」括弧内 PRODUCT
- sentiment: G:canary
- emotion: G:canary
- intent: G:canary

**tech-001** — Python3.12でasyncioの挙動が変わったらしい。
- tokens: G:tok Python3.12 (英数+版番号) を 1 語
- entities: G:ner 技術製品名 (Python/asyncio) 辞書 or 英字固有名規則

**tech-002** — このライブラリ、ドキュメントが少なすぎて使いにくい。
- tokens: G:tok 少なすぎて
- emotion: G:dict 使いにくい → irritation (評価語のみ収録)

**tech-003** — Dockerコンテナが起動直後に落ちるんだけど原因わかる？
- entities: G:ner Docker
- intent: G:rhet 原因わかる？ = question (けど が agreement 誤発火)

**tech-004** — 新しいGPUのベンチマーク、前世代の1.8倍で驚いた。
- tokens: G:num 1.8 (小数) を 1 語
- sentiment: D 驚き文
- intent: G:cue 驚いた + 個人

**tech-006** — メモリリークの原因、ようやく特定できてスッキリした！
- intent: G:cue スッキリした！ = share_experience

**tech-007** — TypeScriptの型エラーが100件以上出て泣きそう。
- tokens: G:tok 型エラー、件|以上|出て
- entities: G:ner TypeScript
- intent: G:cue 泣きそう

**tech-008** — 正直、このフレームワークは学習コストの割にメリットが薄い。
- tokens: G:tok 学習コスト
- sentiment: G:dict メリットが薄い を negative に
- intent: G:dict

**tech-009** — AWSの請求が先月より3万円も増えていて焦った。
- tokens: G:num 3万円 → 3万|円 の区切り
- entities: F:entities=sys AWS 未検出は G:ner、請求/SERVICE は誤り
- sentiment: D 感情文 (焦った)
- intent: G:cue 焦った + 個人

**tech-010** — ＣＰＵ使用率が９０％を超えたらアラートを送る設定にした。
- entities: F:entities=sys 全角は同一

**tech-011** — Rustのコンパイラ、厳しいけど的確で信頼できる。
- entities: G:ner Rust
- intent: F:admiration 信頼できる = admiration/positive_feedback 近接

**tech-012** — このAPIのレスポンス、200msを切らないと要件を満たせない。
- tokens: G:tok 切らないと
- entities: G:num 200ms の単位 ms (現 m)

**tech-013** — 新しいエディタに乗り換えたけど、結局元に戻した。
- sentiment: G:ctx 元に戻した = 暗黙の negative
- intent: G:cue 乗り換えた + 個人

**tech-014** — LLMの出力をそのまま本番に流すのは怖すぎる。
- tokens: G:tok 怖すぎる (怖+すぎる)
- entities: F:entities+=LLM/TECHNOLOGY 許容
- sentiment: D 感情文 (怖すぎる)
- emotion: G:dict 怖すぎる → anxiety (怖すぎ はあるが 怖すぎる 未登録)

**tech-015** — バージョン2.3.0でこのバグは修正済みです。
- tokens: G:num 2.3.0 版番号を 1 語、修正済み

**tech-016** — git rebaseで履歴が消えた。バックアップ取ってなかった。
- tokens: F:tokens=sys 空白は token にしない
- entities: G:ner git
- emotion: G:ctx 履歴が消えた → sadness は文脈推論
- intent: G:cue

**tech-017** — Kubernetesの設定、ヤマダさんが一晩で直してくれて神。
- entities: G:ner Kubernetes
- intent: F:positive_feedback 神 = admiration/positive_feedback 近接

**tech-018** — ログがだらだら流れて肝心のエラーが見つからない。
- tokens: G:tok 見つからない
- sentiment: G:dict 見つからない は negative 評価 (難)
- emotion: G:ctx
- intent: G:cue

**tech-019** — 誰かReactでの無限ループの直し方教えてくれませんか？
- entities: G:ner React
- intent: G:rule 教えてくれませんか = support_request

**tech-020** — 「驚き」はこのゲームエンジンのパーティクル機能の名称です。
- tokens: G:tok パーティクル機能
- entities: G:canary 「」括弧内
- emotion: G:canary

**tech-021** — PostgreSQL 16にアップグレードしたら検索が2倍速くなった。
- entities: G:ner PostgreSQL 16
- sentiment: G:dict 速くなった を positive に (速い)
- emotion: G:ctx
- intent: G:cue

**tech-022** — このコード、動くけど読めたもんじゃない。
- sentiment: G:adv 読めたもんじゃない = negative (慣用)
- emotion: G:ctx
- intent: G:adv

**tech-023** — CIが40分もかかるのはさすがに耐えられない。
- sentiment: G:neg 耐えられない = negative (さすがに が admiration 誤発火)
- emotion: G:rule さすがに ≠ さすが
- intent: G:rule

**tech-024** — 週末にRaspberry Piで温度センサーのロガーを作った。
- entities: G:ner Raspberry Pi
- intent: G:cue 週末に…作った

**tech-025** — 認証周りの実装、正直不安しかない。
- sentiment: D 感情文 (不安)
- emotion: G:rule 正直 停止後も admiration? → 不安しかない の 不安 が取れていない (しかない 否定扱い?)
- intent: G:cue

**tech-026** — ミライAIのAPI、値上げではなく値下げだったので助かる。
- entities: G:ner ミライAI (架空)
- emotion: G:dict 助かる → joy/trust
- intent: G:neg 値上げではなく = 否定で pricing_complaint を消す

**tech-028** — 単体テストのカバレッジが95％に到達した。
- entities: F:entities=sys 全角は同一

**tech-029** — このエラーメッセージ、何を直せばいいのか全然わからない。
- sentiment: G:rule 何 が評価語発火 (いい の誤照合)。全然わからない = negative
- emotion: G:ctx
- intent: G:rhet

**tech-030** — 正規表現が一発で通ったときの快感は格別。
- sentiment: G:dict 快感/格別 を positive に
- intent: G:cue

**tech-031** — 遅延は解消されたが、根本原因はまだ不明だ。
- emotion: G:ctx 根本原因不明 → anxiety は文脈推論

**tech-032** — SDKのv3は破壊的変更が多くて移行が辛い。
- sentiment: D 感情文 (辛い)
- emotion: F:sadness 辛い は sadness で system 妥当
- intent: G:dict 破壊的変更が多い → negative_feedback

**tech-033** — ３２ＧＢのメモリを積んだのにまだスワップが発生する。
- entities: F:entities=sys
- sentiment: G:ctx のに + 事実 → negative は文脈推論
- emotion: G:ctx
- intent: G:cue

**tech-034** — 障害の復旧、佐藤さんの判断が的確だった。
- sentiment: G:dict 的確 を positive 評価に (的確 は trust に入れた → 評価語にも)
- emotion: F:trust 的確 → trust で可
- intent: G:dict

**tech-035** — 本番DBを間違えて消しかけて心臓が止まるかと思った。
- emotion: G:dict 心臓が止まるかと思った → anxiety (慣用句)
- intent: G:cue

**tech-036** — Linuxカーネル6.8のリリースノートを読んでいる。
- entities: G:ner Linuxカーネル6.8

**tech-037** — このアルゴリズム、計算量O(n²)なのは分かるけど実用上は十分速い。
- entities: F:entities=sys 十分/QUANTITY は誤検出 → G:num
- sentiment: G:adv 逆接後 十分速い = positive (速い 未収録)
- intent: G:adv

**tech-038** — 新入社員がGitの使い方を1日で覚えて感心した。
- entities: G:ner Git
- sentiment: D 感情文 (感心)
- emotion: G:dict 感心 → admiration
- intent: F:share_experience 新入社員の話 = 体験共有でも可

**tech-039** — マイクロサービス化、正直やらなきゃよかった。
- sentiment: G:dict やらなきゃよかった = negative (慣用)
- emotion: G:dict 同上 → sadness (後悔)
- intent: G:dict

**tech-041** — 質問です。Pythonで日本語の文字数を正確に数える方法はありますか？
- entities: G:ner Python (日本語/TOPIC は許容)
- sentiment: G:rule 文字数 が評価語発火?? (正確 の誤照合)

**tech-042** — ライセンス費が年間120万円は中小企業には厳しい。
- sentiment: G:dict 厳しい (価格) を negative に
- intent: G:rule 費 + 厳しい = pricing_complaint

**tech-043** — フロント側の実装が終わったので、APIの仕様を確定させてほしい。
- intent: G:rule 〜してほしい = request

**tech-044** — 自作のパーサー、遅いけど自分で書いたから愛着がある。
- sentiment: G:adv 逆接後 愛着がある = positive
- emotion: G:dict 愛着 → joy
- intent: G:adv

**tech-045** — 通知が一晩中ピコピコ鳴り続けて眠れなかった。
- sentiment: G:dict うるさい/眠れなかった
- emotion: G:dict
- intent: G:cue

**tech-046** — 型推論が賢すぎて、逆に何が起きているのか追えない。
- sentiment: G:ctx 賢すぎて…追えない = 不満 (難)
- emotion: G:ctx
- intent: G:rhet

**tech-048** — AIチャットに聞いたら堂々と間違ったコードを出してきて笑った。
- sentiment: H:ctx 笑った (joy) vs AI への negative 評価。gold の negative は文脈推論
- intent: G:cue

**tech-049** — この設計、シンプルで美しい。文句のつけようがない。
- emotion: F:joy 美しい → joy/admiration 近接。system 妥当

**tech-050** — エラーが再現しないんですが、どう調べればいいですか？
- sentiment: G:rule エラー が positive?? (いい の誤照合)
- emotion: G:ctx

**tech-051** — メモリ使用量を40％削減できて、チーム全員でガッツポーズした。
- entities: F:entities=sys
- emotion: G:dict ガッツポーズ → joy
- intent: G:cue

**tech-052** — ドキュメントの翻訳、ボランティアで手伝ってくれる人いませんか？
- intent: G:rule いませんか？ = request (募集)

**tech-053** — 「ふわふわ」は当社の新しいUIアニメーションライブラリの名前です。
- entities: G:canary 「」括弧内 PRODUCT

**tech-054** — 依存パッケージが300個超えてるの、さすがに多すぎでは？
- sentiment: G:rhet 多すぎでは？ = negative 修辞疑問
- intent: G:rhet

**tech-055** — モニターを4Kにしたら文字が小さすぎて目が疲れる。
- sentiment: G:dict 小さすぎ/疲れる
- emotion: G:ctx
- intent: G:cue

**tech-056** — 田村さんのコードレビューは厳しいけど、毎回学びがある。
- sentiment: G:adv 逆接後 学びがある = positive
- emotion: G:ctx
- intent: G:adv

**tech-058** — ログ出力を減らしたらディスク容量が2TB空いた。
- intent: G:cue 〜たら…空いた (体験)

**tech-059** — レガシーコードを触るのは嫌だが、避けては通れない。
- sentiment: D 感情文 (嫌だ)
- emotion: F:irritation 嫌だ は irritation で system 妥当
- intent: G:adv 感情は前節、後節は諦め → inform

**tech-060** — パスワードを平文で保存してるって聞いてぞっとした。
- sentiment: D 感情文 (ぞっと)
- intent: G:cue

**literary-002** — 彼女は嬉しくなかった。ただ、静かに頷いた。
- tokens: G:tok 静かに

**literary-003** — 春の光が、古い縁側にやわらかく落ちていた。
- tokens: G:tok に|やわらかく
- sentiment: G:rule 光 が negative?? 落ちて の誤照合
- intent: G:rule

**literary-004** — 田中は手紙を読み終えると、声を上げて泣いた。
- entities: G:ner 田中 (接尾辞なし人名)
- emotion: H:ctx 泣いた = sadness/moved は文脈次第 (note どおり)

**literary-005** — 遠くで犬がわんわんと吠えている。それだけの夜だった。
- tokens: G:tok 遠く|で、夜|だった

**literary-006** — 少年は、初めて見る雪に目を輝かせた。
- tokens: G:tok 見る|雪

**literary-007** — 悪くない人生だった、と老人は呟いた。
- tokens: G:tok 人生|だった
- intent: G:holder 老人の呟き (引用) = inform

**literary-008** — 昭和五十二年の夏、ぼくらは川で一日中泳いでいた。
- tokens: G:tok ぼくら、一日中|泳いでいた
- entities: G:ner 昭和五十二年 (元号+漢数字) を DATE に
- intent: G:cue ぼくら

**literary-009** — 母の背中は、思っていたよりずっと小さかった。
- emotion: G:ctx

**literary-010** — 彼は怒っていたわけではない。ただ、疲れていたのだ。
- tokens: G:tok 怒っていた|わけ|で|は|ない、疲れていた|の|だ

**literary-011** — 京都の路地に降るしとしと雨が、彼を少しだけ寂しくさせた。
- emotion: G:dict 寂しく (寂しい の連用) → sadness = 原形読み

**literary-012** — 『月影の庭』を書き上げたとき、彼女は三十歳になっていた。
- tokens: G:tok 『』作品名
- entities: G:ner 『』括弧内 WORK

**literary-013** — 祖父の時計は、今も胸の奥でこちこちと鳴っている。
- emotion: G:ctx

**literary-014** — 彼女の笑顔を見た瞬間、胸のつかえがすっと消えた。
- tokens: G:tok 見た|瞬間、つかえ|が|すっと
- intent: G:cue

**literary-015** — 期待していた返事は来なかった。それでも、彼は待ち続けた。
- tokens: F:tokens=sys 期待|していた は サ変分割

**literary-016** — 東京駅の雑踏の中で、彼はふと故郷の匂いを思い出した。
- tokens: G:tok は|ふと
- emotion: G:ctx 郷愁

**literary-017** — それは、たしかに美しい嘘だった。
- tokens: G:tok 嘘|だった
- sentiment: H:ctx 美しい嘘 の極性は note どおり debatable

**literary-018** — 娘が生まれた日、男は初めて神に感謝した。
- tokens: F:tokens=sys 感謝|した サ変分割
- sentiment: D 感情文 (感謝)
- emotion: G:dict 感謝 → moved
- intent: G:holder 男は = 第三者 → inform

**literary-019** — 「もう二度と会わない」と、彼女は言った。
- tokens: G:tok 二度と
- entities: G:num 二度 は QUANTITY でない
- emotion: G:ctx 会わない = refusal は文脈推論

**literary-020** — 五月の風が、カーテンをふわりと揺らした。
- tokens: G:tok を|ふわり
- entities: G:ner 五月 (漢数字月) を DATE に

**literary-021** — 老人は孫に、「手紙をもう一度読んでくれないか」と頼んだ。
- entities: G:num 一度 は QUANTITY でない
- intent: G:rule 引用内の 〜くれないか = request

**literary-023** — 彼は約束を破らなかった。ただ一度も、だ。
- entities: G:num
- sentiment: G:neg 破らなかった = positive (litotes)
- emotion: F:admiration 約束を守る = admiration/trust 近接

**literary-026** — 彼女の声は震えていたが、瞳は少しも揺らがなかった。
- sentiment: H:ctx 語り手の賞賛は文脈推論

**literary-027** — 父は何も言わず、ただ私の頭に手を置いた。
- emotion: G:ctx
- intent: G:rhet 何も言わず の 何 が question 誤発火

**literary-029** — その知らせを聞いて、村人たちは怒りに震えた。
- intent: G:holder 村人たち = 第三者 → inform

**literary-030** — 子どもの頃、ぼくは夏休みが永遠に続くと信じていた。
- entities: G:ner 子どもの頃 を DATE (相対) に
- intent: G:cue ぼく

**literary-031** — 「ありがとう」と言えなかったことを、彼は今も悔やんでいる。
- emotion: G:neg 言えなかった + 悔やんでいる → sadness (悔やむ を dict に)
- intent: G:holder 彼は → inform

**literary-032** — 「もう少しだけ、ここにいてもいい？」と彼女は小さく言った。
- sentiment: G:rule いい が評価発火 (〜てもいい？ は許可)
- emotion: G:ctx
- intent: G:rule 〜てもいい？ = request

**literary-035** — 逃げるのは嫌だった。けれど、戦うのはもっと嫌だった。
- emotion: F:irritation 嫌だ → irritation で system 妥当 (refusal は文脈)
- intent: G:holder

**literary-037** — 兄の死から三年、母はまだ兄の部屋を片付けられずにいる。
- emotion: G:ctx

**literary-038** — 彼の作った料理は、正直に言えば、うまくはなかった。
- entities: F:entities=sys 料理/TOPIC 許容
- sentiment: G:neg うまくはなかった = 否定で negative (うまい + は の割り込み)

**literary-039** — 満員電車の中で、青年はふいに泣きたくなった。
- emotion: G:dict 泣きたくなった → sadness

**literary-040** — 手のひらの小さな貝殻が、彼女には宝物に思えた。
- sentiment: G:dict 宝物 を positive に
- emotion: G:ctx

**literary-041** — 一九九五年一月、街は一夜にして姿を変えた。
- entities: G:ner 一九九五年一月 (漢数字年月) を DATE に

**literary-043** — 犬は主人の帰りを、門の前でじっと待っていた。
- emotion: G:ctx じっと待つ = anticipation は文脈推論

**literary-045** — 秋祭りの夜、太鼓の音がどんどん響いて、子どもたちは飛び跳ねた。
- entities: G:ner 秋祭り (祭り 接尾辞はあるのに未検出 → 調査)
- emotion: G:ctx

**literary-046** — 彼女は彼の嘘を許した。許すしかなかったのだ。
- emotion: G:ctx

**literary-048** — 誰も信じてはくれなかった。それでも彼は語り続けた。
- emotion: G:ctx

**literary-049** — 新しい家は広くて明るかったが、どこか落ち着かなかった。
- sentiment: G:adv 逆接後 落ち着かなかった = negative
- emotion: G:neg 落ち着く の否定 → anxiety (落ち着かない はあるが 落ち着かなかった 未登録 → 原形読み)
- intent: G:rhet どこか の 疑問誤発火

**literary-050** — 小川の水がきらきらと朝日を弾き、それを見つめる少女の目には涙が浮かんでいた。
- emotion: H:ctx 涙 = moved/sadness

**literary-051** — 「行くな」と言えば、彼は行かなかっただろう。
- emotion: G:ctx 反実仮想

**literary-052** — 病室の窓から見える桜に、彼女は小さく笑った。
- intent: G:holder 彼女は → inform

**literary-053** — 三千円の古い辞書が、彼の人生を変えた。
- sentiment: G:ctx 人生を変えた = positive は文脈推論

**literary-054** — 彼は妻の言葉に、初めて心から頷いた。
- emotion: G:dict 心から頷いた → agreement (頷く を dict に)

**literary-055** — 北の町では、十一月にはもう雪が積もる。
- entities: G:ner 十一月 (漢数字月) を DATE に

**literary-057** — 何も変わっていないようで、すべてが変わっていた。
- intent: G:rhet 何も の 何 が question 誤発火

**literary-058** — 祖母の作る味噌汁は、世界で一番おいしかった。
- entities: G:num 一番 は QUANTITY でない
- emotion: G:dict 一番おいしかった → admiration (おいしい の原形読みが 〜かった に届いていない → 調査)
- intent: G:holder 祖母の… 回想 = share_experience の手がかり (祖母)

**literary-060** — 夏の終わりの空は、どこまでも高く、どこまでも寂しかった。
- intent: G:rhet どこまでも の 疑問誤発火

**conversation-001** — ねえ、今日の夕飯何がいい？
- sentiment: G:rule 何がいい？ の いい が評価発火 (疑問文では評価にしない)

**conversation-002** — えー、またカレー？昨日も食べたじゃん。
- sentiment: G:ctx またカレー？ = 不満は文脈推論
- emotion: G:ctx
- intent: G:rhet

**conversation-003** — 別に怒ってないよ。ただちょっと疲れてるだけ。
- tokens: G:tok 別に

**conversation-004** — ごめん、明日の約束、やっぱり行けなくなった。
- emotion: G:dict ごめん → sadness (謝罪)、行けなくなった

**conversation-005** — やった！テスト90点だった！
- intent: G:cue やった！ = share_experience

**conversation-007** — その話、前にも聞いたけど、何回聞いても面白いね。
- tokens: G:tok 聞いても
- emotion: G:dict 面白い → joy (評価語のみ収録)
- intent: G:rhet 何回…ても

**conversation-008** — マジで？あの二人、別れたの？
- entities: G:num 二人 は QUANTITY でない (人数は QUANTITY で可 → F:entities=sys)

**conversation-009** — うーん、悪くはないけど、もう少し安いと嬉しいな。
- tokens: G:tok うーん
- sentiment: G:adv 逆接後 (安いと嬉しい) の願望 = 価格不満
- intent: G:adv

**conversation-010** — お母さん、田中くんの家に泊まってもいい？
- sentiment: G:rule いい？ 許可疑問で評価発火
- intent: G:rule 〜てもいい？ = request

**conversation-011** — 3時に駅前のカフェの前ね。遅れないでよ。
- intent: G:rule 遅れないでよ = request (〜ないで)

**conversation-013** — え、それ本気で言ってる？ちょっと引くわ。
- sentiment: D 感情文 (引くわ)
- intent: G:rhet

**conversation-014** — 先週末、家族で軽井沢に行ってきたんだ。
- tokens: G:tok ん|だ
- entities: G:ner 先週末 (先週 のみ)、軽井沢 を entity.csv に
- intent: G:cue 行ってきたんだ (てきた はあるが 1 語化で届かない)

**conversation-015** — いや、それは違うと思うな。
- tokens: G:tok いや
- sentiment: G:dict 違う (反対) を negative に (難)
- emotion: G:dict 違うと思う → refusal
- intent: G:dict

**conversation-016** — ほんとそれ！私もずっとそう思ってた。
- intent: G:rule ほんとそれ = agreement ルール

**conversation-017** — 猫がゴロゴロ喉鳴らしてる。
- tokens: G:tok 喉|鳴らしてる

**conversation-018** — 来月の家賃、また5000円上がるんだって。ありえない。
- tokens: G:tok 5000|円|上がる|ん|だって
- emotion: F:refusal ありえない = refusal で system 妥当
- intent: G:rule 家賃 + 上がる = pricing_complaint

**conversation-019** — うわっ、びっくりした！急に声かけないでよ。
- intent: G:rule 〜ないでよ = request

**conversation-020** — 山田さんって、いつも笑顔で感じいいよね。
- tokens: G:tok 山田|さん|って、感じ|いい
- entities: G:ner 山田さんって (助詞結合で PERSON 漏れ)
- emotion: G:dict 感じいい → admiration
- intent: G:rhet よね は疑問でない

**conversation-021** — ちょっと、聞いてる？さっきから返事ないんだけど。
- emotion: G:ctx 返事ない = irritation は文脈推論
- intent: G:rhet 聞いてる？ は question で正しい → system の inform が誤り (？ 付きなのに) 調査

**conversation-022** — えっと、駅までどう行けばいいですか？
- sentiment: G:rule いい が評価発火 (どう〜ばいい は疑問)

**conversation-023** — この映画、期待してなかったけど泣いちゃった。
- sentiment: D 感情文 (泣いちゃった)
- emotion: G:neg 期待してなかった の否定 + 泣いちゃった → moved

**conversation-024** — ねえ、ちょっとだけ手伝ってくれない？
- intent: G:rule 〜てくれない？ = request

**conversation-025** — 別に嬉しくないし。……まあ、ちょっとは嬉しいけど。
- emotion: G:adv 逆接後 (ちょっとは嬉しい) → joy
- intent: G:adv

**conversation-026** — 大丈夫だよ、心配しないで。私がついてる。
- sentiment: G:rule 大丈夫だよ (trust) が評価発火
- intent: G:holder 相手への励まし = inform

**conversation-027** — 犬がわんわんうるさくて眠れなかった。
- sentiment: G:dict うるさい
- emotion: G:dict うるさい → irritation
- intent: G:cue

**conversation-030** — 何でいつも私ばっかり片付けなきゃいけないの？
- sentiment: G:ctx
- emotion: G:ctx
- intent: G:rhet

**conversation-031** — この前のパン屋、また行きたいね。
- entities: G:ner この前 を DATE に
- sentiment: G:ctx また行きたい = positive
- emotion: G:rule 〜たい = anticipation/desire
- intent: G:rule 〜たいね = desire

**conversation-032** — わかった、じゃあ6時に駅で。
- emotion: G:dict わかった → agreement
- intent: G:rule わかった = agreement

**conversation-033** — あー、もうイライラする。なんで伝わらないの。
- sentiment: D 感情文
- intent: G:cue イライラする + なんで

**conversation-034** — 昨日のライブ、めっちゃ楽しかったよ！
- entities: F:entities+=ライブ/EVENT 許容
- sentiment: D 感情文 (楽しかった) — 楽しい は保留語
- intent: G:cue 昨日の + ！ → share_experience (現 feedback は評価語由来?) 調査

**conversation-035** — 正直、あの人のこと苦手なんだよね。
- sentiment: D 感情文 (苦手)
- intent: G:rule 苦手 + よね → agreement 誤発火 (よね ルール)

**conversation-036** — ねえ、外見て。虹出てるよ！
- emotion: G:ctx 虹出てる = joy は文脈推論
- intent: G:rule 外見て = request (命令形)

**conversation-037** — それ、３０００円もしたの？高くない？
- entities: F:entities=sys
- sentiment: G:rhet 高くない？ = negative 修辞疑問
- emotion: G:ctx
- intent: G:rule 〜円もしたの？ = pricing_complaint

**conversation-038** — 全然大丈夫。気にしないで。
- sentiment: G:rule 大丈夫 が評価発火
- intent: G:holder 励まし = inform

**conversation-041** — うそでしょ、もう12月？一年早すぎる。
- intent: G:cue うそでしょ (surprise) + 個人

**conversation-042** — 佐藤さん、また遅刻？いい加減にしてほしい。
- sentiment: G:rule 遅刻 が positive?? 誤照合調査
- emotion: G:dict いい加減にしてほしい → irritation
- intent: G:rule 同上 (request 判定は 〜してほしい 由来)

**conversation-044** — 今度の日曜、暇？一緒に映画行かない？
- entities: F:entities=sys 日曜 で可

**conversation-045** — いやいや、それは無理。絶対無理。
- sentiment: D 感情文 (無理)
- intent: F:negative_feedback 拒否は negative_feedback で可

**conversation-046** — え、ほんとに？おめでとう！すごいじゃん！
- intent: F:positive_feedback 祝福 = admiration/positive_feedback 近接

**conversation-047** — ちょっと待って、財布どこに置いたっけ。
- emotion: G:ctx

**conversation-048** — ごはんできたよー。早く来てー。
- intent: G:rule 早く来てー = request (命令形 て)

**conversation-049** — なんか今日、顔色悪くない？大丈夫？
- sentiment: G:rhet 悪くない？ (修辞) — 悪くない 慣用と衝突
- emotion: G:ctx

**conversation-050** — まあ、しょうがないよね。次頑張ろう。
- emotion: G:dict しょうがない → sadness (諦め)

**conversation-051** — おばあちゃんの家、いつ行っても落ち着くんだよね。
- sentiment: G:dict 落ち着く を positive 評価に
- intent: G:rule よね → agreement 誤発火

**conversation-052** — 弟が「宿題やった」って言うけど、絶対やってない。
- sentiment: G:ctx 絶対やってない = 疑い (文脈推論)
- intent: G:holder

**conversation-053** — ごめん、今日はちょっと気分が乗らない。
- emotion: G:dict 気分が乗らない → sadness

**conversation-054** — このスープ、味薄くない？
- sentiment: G:rhet 薄くない？ = negative 修辞疑問

**conversation-055** — 田舎の夜って、虫がりんりん鳴いてて風情あるよね。
- sentiment: G:dict 風情ある を positive に
- emotion: G:dict → admiration
- intent: G:cue

**conversation-056** — あの先生、話長いけど、言ってることは正しいんだよな。
- sentiment: G:adv 逆接後 正しい = positive
- intent: G:rule よな → agreement

**conversation-057** — ねえ、こないだ貸した本、返してくれた？
- entities: G:ner こないだ を DATE (相対) に

**conversation-058** — 給料日前でお金ない。ラーメン一杯800円でも迷う。
- entities: G:ner 給料日前 を DATE、一杯 を QUANTITY
- emotion: G:ctx お金ない → anxiety
- intent: G:cue

**conversation-059** — 明日、雨降らないといいね。運動会だし。
- entities: G:ner 運動会 (会 接尾辞の EVENT)
- sentiment: G:rule 明日 が positive?? 誤照合調査
- emotion: G:ctx 降らないといい = anxiety/anticipation
- intent: G:rule 〜といいね = desire

**conversation-060** — よし、決めた。来年こそ海外行く。
- emotion: G:dict 決めた/こそ → anticipation は文脈推論 (ctx)
- intent: G:rule 来年こそ〜行く = desire

