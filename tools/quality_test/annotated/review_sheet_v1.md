# 人手評価セット レビューシート — KotobaCore 0.6.6 / annotated_v1_draft (300 文)

不一致あり 220 / 300 文。種類別: intent 130, sentiment 71, entities 63, tokens 59, emotion 39

## 0. 先に決めること（体系差 = 個別判定ではなく方針）

| 論点 | 件数 | 提案 |
|---|---|---|
| system の `exaggeration` を感情として数えるか | 1 | gold に無いラベル。『強調は感情ではない』なら system 側で primary から除外、認めるなら gold に追加 |
| 評価極性: gold あり / system なし | 44 | 2026-09-08 決定『感情語は評価極性に含めない』で gold を再判定 (感情文なら sentiment を空に) |

## 0.5 辞書追加候補（語で判断すれば文を見ずに済む分）

### sentiment.csv 候補（gold に評価極性あり・system 未検出の文の述語、8 語）

| 語 | gold 極性 | 文数 | 採否 |
|---|---|---|---|
| 新しい | negative | 3 | [ ] 追加 [ ] 感情語(除外) [ ] 評価語ではない |
| だるい | negative | 1 | [ ] 追加 [ ] 感情語(除外) [ ] 評価語ではない |
| 新しい | positive | 1 | [ ] 追加 [ ] 感情語(除外) [ ] 評価語ではない |
| 厳しい | negative | 1 | [ ] 追加 [ ] 感情語(除外) [ ] 評価語ではない |
| 聞い | negative | 1 | [ ] 追加 [ ] 感情語(除外) [ ] 評価語ではない |
| 広い | negative | 1 | [ ] 追加 [ ] 感情語(除外) [ ] 評価語ではない |
| 明るい | negative | 1 | [ ] 追加 [ ] 感情語(除外) [ ] 評価語ではない |
| してない | positive | 1 | [ ] 追加 [ ] 感情語(除外) [ ] 評価語ではない |

### emotion.csv 候補（gold に感情あり・system 未検出の文の述語、5 語）

| 語 | gold 感情 | 文数 | 採否 |
|---|---|---|---|
| 小さい | sadness | 1 | [ ] 追加 [ ] 文脈推論(辞書外) |
| 匂い | moved | 1 | [ ] 追加 [ ] 文脈推論(辞書外) |
| いい | anxiety | 1 | [ ] 追加 [ ] 文脈推論(辞書外) |
| 一番おいしい | admiration | 1 | [ ] 追加 [ ] 文脈推論(辞書外) |
| 高い | surprise | 1 | [ ] 追加 [ ] 文脈推論(辞書外) |

## 1. 個別レビュー（不一致のある文のみ、ジャンル順）

### sns (46 文)

**sns-002** `tokens,sentiment` — 新しいiPhone買ったけど正直そこまで感動しない。

- tokens gold: 新しい | iPhone | 買った | けど | 正直 | そこまで | 感動しない | 。
- tokens sys : 新しい | iPhone | 買った | けど | 正直 | そこ | まで | 感動 | しない | 。
- sentiment gold: iPhone:negative / sys: None (affect negative; )
- 判断メモ: 分割: system が gold より 細かい (2 境界差) / 評価極性: gold あり / system なし。評価語候補 ['新しい'] (sentiment.csv 未収録) / 感情語 ['感動しない']
- 下書きの note: negated 感動; clause after けど carries stance; no clear emotion label
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-003** `entities` — 明日のライブ、わくわくが止まらない！

- entities gold: 明日/DATE / sys: ライブ/EVENT, 明日/DATE
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): ライブ/EVENT
- 下書きの note: onomatopoeia わくわく; 止まらない is not a negated emotion
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-004** `sentiment,intent` — 電車遅延でイライラする…また遅刻だよ。

- sentiment gold: 電車遅延:negative / sys: None (affect negative; )
- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['イライラする'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold share_experience vs system negative_feedback
- 下書きの note: onomatopoeia イライラ
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-005** `tokens` — 隣の猫がにゃーにゃー鳴いてる。

- tokens gold: 隣 | の | 猫 | が | にゃーにゃー | 鳴いてる | 。
- tokens sys : 隣 | の | 猫 | が | にゃーにゃー | 鳴い | てる | 。
- 判断メモ: 分割: system が gold より 細かい (1 境界差)
- 下書きの note: canary: animal sound, no emotion
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-006** `tokens,emotion` — 渋谷のスクランブル交差点、人多すぎて疲れた😩

- tokens gold: 渋谷 | の | スクランブル交差点 | 、 | 人 | 多すぎて | 疲れた | 😩
- tokens sys : 渋谷 | の | スクランブル | 交差点 | 、 | 人多すぎて | 疲れた | 😩
- emotion gold: irritation / sys: sadness
- 判断メモ: 分割: system が gold より 別の切り方 (2 境界差) / 感情: gold ['irritation'] vs system sadness
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-007** `tokens,sentiment` — このカフェ、コーヒーは微妙だけどケーキは神。

- tokens gold: この | カフェ | 、 | コーヒー | は | 微妙 | だ | けど | ケーキ | は | 神 | 。
- tokens sys : この | カフェ | 、 | コーヒー | は | 微妙だ | けど | ケーキ | は | 神 | 。
- sentiment gold: コーヒー:negative; ケーキ:positive / sys: positive (affect positive; コーヒー:negative; ケーキ:positive)
- 判断メモ: 分割: system が gold より 粗い (1 境界差) / 評価極性: gold mixed vs system positive
- 下書きの note: adversative with two targets; overall stance follows けど clause (ケーキ)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-008** `sentiment,intent` — 誰か新宿でおすすめのラーメン屋教えて！

- sentiment gold: - / sys: positive (affect None; 新宿:positive)
- intent gold: request / sys: support_request
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 意図: gold request vs system support_request
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-009** `entities` — え、ブルースカイズ再結成ってマジ？？

- entities gold: ブルースカイズ/ORGANIZATION / sys: -
- 判断メモ: Entity 未検出: ブルースカイズ/ORGANIZATION
- 下書きの note: fictional band name
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-010** `tokens` — 3年ぶりに実家帰ったら犬が覚えててくれて泣いた🥲

- tokens gold: 3 | 年 | ぶり | に | 実家 | 帰ったら | 犬 | が | 覚えててくれて | 泣いた | 🥲
- tokens sys : 3 | 年ぶ | り | に | 実家帰 | っ | たら | 犬 | が | 覚えててくれて | 泣いた | 🥲
- 判断メモ: 分割: system が gold より 細かい (5 境界差)
- 下書きの note: 泣いた here is being moved, not sadness
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-011** `tokens,emotion` — 正直、今回のアップデートは改悪だと思う。

- tokens gold: 正直 | 、 | 今回 | の | アップデート | は | 改悪 | だ | と | 思う | 。
- tokens sys : 正直 | 、 | 今回 | の | アップデート | は | 改悪だ | と | 思う | 。
- emotion gold: irritation / sys: -
- 判断メモ: 分割: system が gold より 粗い (1 境界差) / 感情: system 未検出 — 感情語候補 [] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-013** `tokens,sentiment,emotion,intent` — 田中さんの新曲、何回聴いても飽きない✨

- tokens gold: 田中 | さん | の | 新曲 | 、 | 何回 | 聴いても | 飽きない | ✨
- tokens sys : 田中 | さん | の | 新曲 | 、 | 何回 | 聴いて | も | 飽きない | ✨
- sentiment gold: 新曲:positive / sys: None (affect positive; )
- emotion gold: admiration / sys: anticipation
- intent gold: admiration / sys: share_experience
- 判断メモ: 分割: system が gold より 細かい (1 境界差) / 評価極性: gold あり / system なし。system は感情語 ['✨'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 感情: gold ['admiration'] vs system anticipation / 意図: gold admiration vs system share_experience
- 下書きの note: negation 飽きない is positive
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-014** `intent` — フォロワー1万人突破！！みんなありがとう🙏

- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 意図: gold share_experience vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-015** `tokens,sentiment,intent` — 悪くないんだけど、リピートはしないかな。

- tokens gold: 悪くない | ん | だ | けど | 、 | リピート | は | しない | か | な | 。
- tokens sys : 悪くない | んだ | けど | 、 | リピート | はしないか | な | 。
- sentiment gold: None:negative / sys: positive (affect None; None:positive)
- intent gold: negative_feedback / sys: positive_feedback
- 判断メモ: 分割: system が gold より 粗い (3 境界差) / 評価極性: gold negative vs system positive / 意図: gold negative_feedback vs system positive_feedback
- 下書きの note: 悪くない is mildly positive but けど clause (won't repeat) wins
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-016** `intent` — 【拡散希望】10月5日に代々木公園で保護猫譲渡会やります！

- intent gold: request / sys: desire
- 判断メモ: 意図: gold request vs system desire
- 下書きの note: 拡散希望 = request to share; could also be inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-017** `emotion` — ぴえん🥺推しのグッズ売り切れてた…

- emotion gold: sadness / sys: admiration
- 判断メモ: 感情: gold ['sadness'] vs system admiration
- 下書きの note: SNS slang ぴえん
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-018** `entities` — ＡＢＣストア１２３号店限定のスニーカー、ゲットしたぜ😎

- entities gold: ＡＢＣストア１２３号店/ORGANIZATION / sys: 123号/QUANTITY
- 判断メモ: Entity 未検出: ＡＢＣストア１２３号店/ORGANIZATION / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 123号/QUANTITY
- 下書きの note: full-width alphanumerics
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-019** `tokens,sentiment,emotion,intent` — なんで月曜って来るの早いんだろ😇

- tokens gold: なんで | 月曜 | って | 来る | の | 早い | ん | だろ | 😇
- tokens sys : なん | で | 月曜って | 来る | の | 早い | んだろ | 😇
- sentiment gold: 月曜:negative / sys: positive (affect mixed; None:positive)
- emotion gold: irritation / sys: exaggeration
- intent gold: none / sys: share_experience
- 判断メモ: 分割: system が gold より 粗い (3 境界差) / 評価極性: gold negative vs system positive / 感情: system の exaggeration (強調表現) は gold 体系に無い — 強調語 (マジで/すぎ/やばい) を感情と数えるかの方針決め / 意図: gold none vs system share_experience
- 下書きの note: rhetorical question, not a real question
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-020** `tokens,sentiment,intent` — 映画『夜明けの列車』、泣きすぎて目が腫れた。

- tokens gold: 映画 | 『 | 夜明けの列車 | 』 | 、 | 泣きすぎて | 目 | が | 腫れた | 。
- tokens sys : 映画 | 『 | 夜明 | け | の | 列車 | 』、 | 泣きすぎ | て | 目が腫れた | 。
- sentiment gold: 夜明けの列車:positive / sys: None (affect positive; )
- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 分割: system が gold より 細かい (7 境界差) / 評価極性: gold あり / system なし。system は感情語 ['目が腫れた', '泣きすぎ'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold share_experience vs system positive_feedback
- 下書きの note: fictional film title
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-021** `sentiment` — 今日はぽかぽか陽気で散歩日和🌸

- sentiment gold: None:positive / sys: None (affect positive; )
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['ぽかぽか'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加
- 下書きの note: onomatopoeia ぽかぽか
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-022** `emotion,intent` — 楽しみにしてたのに雨で中止とか、ほんと最悪。

- emotion gold: sadness / sys: anger
- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 感情: gold ['sadness'] vs system anger / 意図: gold share_experience vs system negative_feedback
- 下書きの note: のに adversative; 楽しみ negated by outcome
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-024** `entities` — マルコ堂の新作プリン、350円でこの味はすごい。

- entities gold: 350円/MONEY, マルコ堂/BRAND / sys: 350円/MONEY
- 判断メモ: Entity 未検出: マルコ堂/BRAND
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-025** `emotion,intent` — 嬉しくないと言えば嘘になるけど、素直に喜べない。

- emotion gold: anxiety / sys: sadness
- intent gold: share_experience / sys: inform
- 判断メモ: 感情: gold ['anxiety'] vs system sadness / 意図: gold share_experience vs system inform
- 下書きの note: double negation = actually happy, but けど clause (cannot rejoice) wins; label debatable
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-027** `intent` — 推しが尊すぎて生きるのが辛い（良い意味で）

- intent gold: admiration / sys: positive_feedback
- 判断メモ: 意図: gold admiration vs system positive_feedback
- 下書きの note: 辛い is not sadness here (fan slang)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-029** `emotion` — 3日連続で残業とかブラックすぎん？

- emotion gold: irritation / sys: -
- 判断メモ: 感情: system 未検出 — 感情語候補 [] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- 下書きの note: rhetorical question
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-030** `sentiment,intent` — この写真、加工なしでこれ？信じられない😳

- sentiment gold: 写真:positive / sys: None (affect mixed; )
- intent gold: question / sys: share_experience
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['信じられない', '😳'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold question vs system share_experience
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-031** `emotion,intent` — ちょっと待って、これ2019年の投稿じゃん。

- emotion gold: surprise / sys: -
- intent gold: inform / sys: request
- 判断メモ: 感情: system 未検出 — 感情語候補 [] (emotion.csv 未収録なら追加、無ければ gold は文脈推論) / 意図: gold inform vs system request
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-033** `intent` — 全然期待してなかったけど、この漫画めっちゃ面白い！

- intent gold: positive_feedback / sys: share_experience
- 判断メモ: 意図: gold positive_feedback vs system share_experience
- 下書きの note: negated expectation + けど
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-034** `entities` — 値上げばっかりで、もう外食できないよ…

- entities gold: - / sys: 値上げ/TOPIC
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): 値上げ/TOPIC
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-037** `sentiment` — いいね押しすぎて指が疲れた笑

- sentiment gold: - / sys: negative (affect positive; None:positive; 指:negative)
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-039** `sentiment,intent` — なんか今日はモヤモヤする。理由はわからない。

- sentiment gold: - / sys: negative (affect negative; 理由:negative)
- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 意図: gold share_experience vs system negative_feedback
- 下書きの note: onomatopoeia モヤモヤ
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-040** `intent` — 「感動」って名前のパン屋、駅前にできてた。

- intent gold: inform / sys: positive_feedback
- 判断メモ: 意図: gold inform vs system positive_feedback
- 下書きの note: canary: 感動 is a shop name
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-041** `sentiment` — 来週の花火大会、雨降らないといいな🎆

- sentiment gold: - / sys: positive (affect positive; 花火大会:positive)
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-044** `sentiment,emotion,intent` — 京都の紅葉、写真じゃ伝わらない美しさだった。

- sentiment gold: 紅葉:positive / sys: None (affect None; )
- emotion gold: admiration / sys: -
- intent gold: share_experience / sys: inform
- 判断メモ: 評価極性: gold あり / system なし。評価語候補 [] (sentiment.csv 未収録) / 感情語 [] / 感情: system 未検出 — 感情語候補 [] (emotion.csv 未収録なら追加、無ければ gold は文脈推論) / 意図: gold share_experience vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-045** `sentiment,emotion,intent` — え、待って、無理、可愛すぎる🫠

- sentiment gold: None:positive / sys: None (affect negative; )
- emotion gold: admiration / sys: refusal
- intent gold: admiration / sys: negative_feedback
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['すぎる', '無理'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 感情: gold ['admiration'] vs system refusal / 意図: gold admiration vs system negative_feedback
- 下書きの note: 無理 is slang for overwhelming cuteness, not refusal
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-046** `sentiment,intent` — バイト先の店長、口は悪いけど面倒見はいい。

- sentiment gold: 店長:positive / sys: negative (affect positive; 口:negative; 口:negative)
- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 評価極性: gold positive vs system negative / 意図: gold share_experience vs system negative_feedback
- 下書きの note: adversative; けど clause positive
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-047** `sentiment,emotion,intent` — リプ欄が荒れてて見るのがしんどい。

- sentiment gold: リプ欄:negative / sys: None (affect negative; )
- emotion gold: disgust / sys: sadness
- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['しんどい'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 感情: gold ['disgust'] vs system sadness / 意図: gold share_experience vs system negative_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-048** `intent` — フォロバありがとうございます！これからよろしくお願いします🙇

- intent gold: none / sys: positive_feedback
- 判断メモ: 意図: gold none vs system positive_feedback
- 下書きの note: greeting/gratitude
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-049** `sentiment,intent` — ぐっすり寝たのに、まだだるい。

- sentiment gold: None:negative / sys: None (affect negative; )
- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 評価極性: gold あり / system なし。評価語候補 ['だるい'] (sentiment.csv 未収録) / 感情語 ['だるい'] / 意図: gold share_experience vs system negative_feedback
- 下書きの note: onomatopoeia ぐっすり; のに adversative
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-050** `sentiment,emotion,intent` — 2万円のイヤホン、音は最高だけど耳が痛くなる。

- sentiment gold: 音:positive; イヤホン:negative / sys: positive (affect positive; 音:positive)
- emotion gold: irritation / sys: joy
- intent gold: negative_feedback / sys: positive_feedback
- 判断メモ: 評価極性: gold mixed vs system positive / 感情: gold ['irritation'] vs system joy / 意図: gold negative_feedback vs system positive_feedback
- 下書きの note: adversative; overall stance follows けど clause
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-051** `intent` — ねこがすやすや寝てる。平和。

- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 意図: gold share_experience vs system positive_feedback
- 下書きの note: kana-only; onomatopoeia すやすや; 平和 is evaluative so not a canary
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-052** `entities,intent` — 誰か一緒にマラソン出ない？12月の湘南のやつ。

- entities gold: 12月/DATE, 湘南/LOCATION / sys: 12月/DATE
- intent gold: question / sys: inform
- 判断メモ: Entity 未検出: 湘南/LOCATION / 意図: gold question vs system inform
- 下書きの note: invitation
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-053** `intent` — 昨日のドラマの最終回、納得いかない。

- intent gold: negative_feedback / sys: share_experience
- 判断メモ: 意図: gold negative_feedback vs system share_experience
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-055** `intent` — 新しいバイトの先輩が優しくて安心した。

- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 意図: gold share_experience vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-056** `intent` — 通知がピロピロうるさすぎてミュートした。

- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 意図: gold share_experience vs system negative_feedback
- 下書きの note: onomatopoeia ピロピロ
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-057** `emotion` — ここのタピオカ、正直ブームの時より美味しくなってる。

- emotion gold: admiration / sys: -
- 判断メモ: 感情: system 未検出 — 感情語候補 [] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**sns-058** `entities,intent` — 今年の夏は暑すぎて外出する気にならない。

- entities gold: 今年の夏/DATE / sys: 今年/DATE
- intent gold: share_experience / sys: negative_feedback
- 判断メモ: Entity 未検出: 今年の夏/DATE / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 今年/DATE / 意図: gold share_experience vs system negative_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

### business (41 文)

**business-001** `tokens,entities,intent` — お世話になっております。株式会社山田商事の鈴木です。

- tokens gold: お世話 | に | なっております | 。 | 株式会社山田商事 | の | 鈴木 | です | 。
- tokens sys : お | 世話 | になっております | 。 | 株式会社山田商事 | の | 鈴木 | です | 。
- entities gold: 株式会社山田商事/ORGANIZATION, 鈴木/PERSON / sys: 株式会社山田商事/ORGANIZATION
- intent gold: none / sys: inform
- 判断メモ: 分割: system が gold より 別の切り方 (2 境界差) / Entity 未検出: 鈴木/PERSON / 意図: gold none vs system inform
- 下書きの note: mail greeting
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-002** `entities` — 2025年度の売上は前年比12％増の45億円となりました。

- entities gold: 12％/QUANTITY, 2025年度/DATE, 45億円/MONEY / sys: 12%/QUANTITY, 2025年度/DATE, 45億円/MONEY
- 判断メモ: Entity 未検出: 12％/QUANTITY / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 12%/QUANTITY
- 下書きの note: factual growth report, no explicit evaluation
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-003** `tokens` — 来週の定例会議は水曜10時に変更いたします。

- tokens gold: 来週 | の | 定例会議 | は | 水曜 | 10 | 時 | に | 変更いたします | 。
- tokens sys : 来週 | の | 定例会議 | は | 水曜 | 10 | 時 | に | 変更いた | します | 。
- 判断メモ: 分割: system が gold より 細かい (1 境界差)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-004** `tokens` — 貴社のご提案、大変魅力的に感じております。

- tokens gold: 貴社 | の | ご提案 | 、 | 大変 | 魅力的 | に | 感じております | 。
- tokens sys : 貴社 | のご | 提案 | 、 | 大変魅力的 | に | 感じております | 。
- 判断メモ: 分割: system が gold より 粗い (3 境界差)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-005** `tokens` — 恐れ入りますが、見積書を再送いただけますでしょうか。

- tokens gold: 恐れ入ります | が | 、 | 見積書 | を | 再送いただけますでしょうか | 。
- tokens sys : 恐れ入ります | が | 、 | 見積書 | を | 再送いただけますで | しょう | か | 。
- 判断メモ: 分割: system が gold より 細かい (2 境界差)
- 下書きの note: が here is a softener, not adversative
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-007** `entities` — ㈱ミライ電機との契約は3月末で終了予定です。

- entities gold: 3月末/DATE, ㈱ミライ電機/ORGANIZATION / sys: 3月/DATE, 株式会社ミライ電機/ORGANIZATION
- 判断メモ: Entity 未検出: 3月末/DATE, ㈱ミライ電機/ORGANIZATION / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 3月/DATE, 株式会社ミライ電機/ORGANIZATION
- 下書きの note: ㈱ abbreviation
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-008** `tokens,intent` — 田中部長は今回の結果に大変満足されていました。

- tokens gold: 田中 | 部長 | は | 今回 | の | 結果 | に | 大変 | 満足されていました | 。
- tokens sys : 田中部長 | は | 今回 | の | 結果 | に | 大変満足 | されていました | 。
- intent gold: inform / sys: positive_feedback
- 判断メモ: 分割: system が gold より 粗い (3 境界差) / 意図: gold inform vs system positive_feedback
- 下書きの note: third-party holder
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-009** `tokens,sentiment,intent` — 単価5,000円は予算を大きく超えており、再検討をお願いします。

- tokens gold: 単価 | 5,000 | 円 | は | 予算 | を | 大きく | 超えており | 、 | 再検討 | を | お願いします | 。
- tokens sys : 単価 | 5 | , | 000 | 円 | は | 予算 | を | 大きく | 超えて | おり | 、 | 再検討 | をお | 願いします | 。
- sentiment gold: 単価:negative / sys: None (affect None; )
- intent gold: pricing_complaint / sys: request
- 判断メモ: 分割: system が gold より 細かい (5 境界差) / 評価極性: gold あり / system なし。評価語候補 [] (sentiment.csv 未収録) / 感情語 [] / 意図: gold pricing_complaint vs system request
- 下書きの note: also a request
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-010** `tokens` — 会議室の空調がガンガン効きすぎて寒いです。

- tokens gold: 会議室 | の | 空調 | が | ガンガン | 効きすぎて | 寒い | です | 。
- tokens sys : 会議室 | の | 空調 | が | ガンガン | 効きすぎ | て | 寒いです | 。
- 判断メモ: 分割: system が gold より 別の切り方 (2 境界差)
- 下書きの note: onomatopoeia ガンガン
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-011** `tokens` — 新サービス「Kanso」は6月1日より提供開始いたします。

- tokens gold: 新サービス | 「 | Kanso | 」 | は | 6月1日 | より | 提供 | 開始いたします | 。
- tokens sys : 新 | サービス | 「 | Kanso | 」 | は | 6 | 月 | 1 | 日 | より | 提供開始 | いたします | 。
- 判断メモ: 分割: system が gold より 細かい (6 境界差)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-013** `tokens` — 先日の説明会には約200名の方にご参加いただきました。

- tokens gold: 先日 | の | 説明会 | に | は | 約 | 200 | 名 | の | 方 | に | ご参加いただきました | 。
- tokens sys : 先日 | の | 説明会 | には | 約 | 200 | 名 | の | 方 | にご | 参加いただきました | 。
- 判断メモ: 分割: system が gold より 粗い (3 境界差)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-014** `tokens,sentiment,intent` — 品質に問題はないものの、コスト面で採用は見送ります。

- tokens gold: 品質 | に | 問題 | は | ない | ものの | 、 | コスト面 | で | 採用 | は | 見送ります | 。
- tokens sys : 品質 | に | 問題 | は | ない | もの | の | 、 | コスト | 面 | で | 採用 | は | 見送ります | 。
- sentiment gold: 品質:positive; None:negative / sys: None (affect negative; )
- intent gold: negative_feedback / sys: inform
- 判断メモ: 分割: system が gold より 細かい (2 境界差) / 評価極性: gold あり / system なし。system は感情語 ['見送ります'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold negative_feedback vs system inform
- 下書きの note: ものの adversative; overall decision negative
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-016** `tokens,sentiment,intent` — 今期の目標未達は非常に残念ですが、原因は明確です。

- tokens gold: 今期 | の | 目標 | 未達 | は | 非常に | 残念 | です | が | 、 | 原因 | は | 明確 | です | 。
- tokens sys : 今期 | の | 目標未達 | は | 非常 | に | 残念 | です | が | 、 | 原因 | は | 明確 | です | 。
- sentiment gold: 目標未達:negative / sys: None (affect negative; )
- intent gold: inform / sys: negative_feedback
- 判断メモ: 分割: system が gold より 別の切り方 (2 境界差) / 評価極性: gold あり / system なし。system は感情語 ['残念'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold inform vs system negative_feedback
- 下書きの note: adversative but emotion sits in the first clause; second clause is neutral
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-017** `tokens` — 弊社は2026年4月に大阪支社を開設いたしました。

- tokens gold: 弊社 | は | 2026年4月 | に | 大阪支社 | を | 開設いたしました | 。
- tokens sys : 弊社 | は | 2026 | 年 | 4 | 月 | に | 大阪支社 | を | 開設いた | しました | 。
- 判断メモ: 分割: system が gold より 細かい (4 境界差)
- 下書きの note: 大阪 alone could also be LOCATION
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-018** `tokens,intent` — ご返信が遅くなり、大変申し訳ございません。

- tokens gold: ご返信 | が | 遅くなり | 、 | 大変 | 申し訳ございません | 。
- tokens sys : ご | 返信 | が | 遅く | なり | 、 | 大変申し訳ございません | 。
- intent gold: none / sys: inform
- 判断メモ: 分割: system が gold より 細かい (3 境界差) / 意図: gold none vs system inform
- 下書きの note: apology; no label in the emotion set (could be mild sadness)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-019** `tokens,intent` — 「感動」は当社の新型加湿器のブランド名です。

- tokens gold: 「 | 感動 | 」 | は | 当社 | の | 新型 | 加湿器 | の | ブランド名 | です | 。
- tokens sys : 「 | 感動 | 」 | は | 当社 | の | 新型加湿器 | の | ブランド | 名 | です | 。
- intent gold: inform / sys: positive_feedback
- 判断メモ: 分割: system が gold より 別の切り方 (2 境界差) / 意図: gold inform vs system positive_feedback
- 下書きの note: canary: 感動 as brand name
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-020** `entities` — 出荷数は月間３０００台を超える見込みです。

- entities gold: ３０００台/QUANTITY / sys: 3000台/QUANTITY
- 判断メモ: Entity 未検出: ３０００台/QUANTITY / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 3000台/QUANTITY
- 下書きの note: full-width digits
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-022** `sentiment,intent` — 正直なところ、今回の提案には期待しておりません。

- sentiment gold: 提案:negative / sys: None (affect negative; )
- intent gold: negative_feedback / sys: inform
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['期待しておりません'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold negative_feedback vs system inform
- 下書きの note: negated anticipation; no emotion label assigned
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-023** `sentiment,emotion` — 山本様のご尽力には深く感謝しております。

- sentiment gold: 山本様:positive / sys: None (affect None; )
- emotion gold: moved / sys: -
- 判断メモ: 評価極性: gold あり / system なし。評価語候補 [] (sentiment.csv 未収録) / 感情語 [] / 感情: system 未検出 — 感情語候補 [] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- 下書きの note: gratitude mapped to moved
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-025** `entities` — 新工場の稼働開始は来年3月を予定しております。

- entities gold: 来年3月/DATE / sys: 3月/DATE, 新工場/ORGANIZATION, 来年/DATE
- 判断メモ: Entity 未検出: 来年3月/DATE / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 3月/DATE, 新工場/ORGANIZATION, 来年/DATE
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-027** `sentiment,intent` — 会場の音響が悪く、後方の席では聞き取れませんでした。

- sentiment gold: 音響:negative / sys: None (affect negative; )
- intent gold: negative_feedback / sys: inform
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['聞き取れません'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold negative_feedback vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-029** `entities` — 株主総会は6月27日午前10時より東京本社で開催します。

- entities gold: 6月27日/DATE, 午前10時/TIME, 東京本社/LOCATION, 株主総会/EVENT / sys: 6月27日/DATE, 午前10時/TIME, 東京本社/ORGANIZATION, 株主総会/TOPIC
- 判断メモ: Entity 型違い: ['東京本社', '株主総会']
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-030** `intent` — 若手社員の成長ぶりには目を見張るものがあります。

- intent gold: admiration / sys: positive_feedback
- 判断メモ: 意図: gold admiration vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-032** `entities` — システム障害により、本日午後の受付を停止しております。

- entities gold: 午後/TIME, 本日/DATE / sys: 本日/DATE
- 判断メモ: Entity 未検出: 午後/TIME
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-034** `intent` — 佐々木課長は退職の報告を聞いて動揺されていました。

- intent gold: inform / sys: request
- 判断メモ: 意図: gold inform vs system request
- 下書きの note: third-party holder
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-035** `entities` — 経費精算の締切は毎月25日です。ご注意ください。

- entities gold: 毎月25日/DATE / sys: 25日/QUANTITY
- 判断メモ: Entity 未検出: 毎月25日/DATE / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 25日/QUANTITY
- 下書きの note: inform + ご注意ください; request chosen
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-037** `sentiment,intent` — 決して安くはありませんが、投資に見合う効果が期待できます。

- sentiment gold: None:positive / sys: None (affect positive; )
- intent gold: positive_feedback / sys: inform
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['期待できます'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold positive_feedback vs system inform
- 下書きの note: adversative; が clause positive
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-038** `intent` — 御社サーバーの応答が遅く、業務に支障が出ております。

- intent gold: support_request / sys: negative_feedback
- 判断メモ: 意図: gold support_request vs system negative_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-039** `entities` — 第3四半期の営業利益は8億円で着地しました。

- entities gold: 8億円/MONEY, 第3四半期/DATE / sys: 8億円/MONEY
- 判断メモ: Entity 未検出: 第3四半期/DATE
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-040** `sentiment` — 上司はこの企画にまったく乗り気ではないようです。

- sentiment gold: 企画:negative / sys: None (affect negative; )
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['乗り気ではない'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加
- 下書きの note: negation ではない; stance belongs to 上司
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-043** `sentiment,intent` — 弊社の売上高は3年連続で過去最高を更新しました。

- sentiment gold: - / sys: positive (affect positive; 売上高:positive)
- intent gold: inform / sys: positive_feedback
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 意図: gold inform vs system positive_feedback
- 下書きの note: positive fact, no explicit evaluation
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-044** `entities` — 展示会「テックフェア2026」への出展を決定しました。

- entities gold: テックフェア2026/EVENT / sys: テックフェア2026/PRODUCT, 展示会/EVENT
- 判断メモ: Entity 型違い: ['テックフェア2026'] / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 展示会/EVENT
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-046** `intent` — 正直、この見積もりには納得しかねます。

- intent gold: pricing_complaint / sys: negative_feedback
- 判断メモ: 意図: gold pricing_complaint vs system negative_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-049** `entities` — 当社の株価は発表後に一時５％下落しました。

- entities gold: ５％/QUANTITY / sys: 5%/QUANTITY
- 判断メモ: Entity 未検出: ５％/QUANTITY / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 5%/QUANTITY
- 下書きの note: full-width digits
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-051** `intent` — 御社の技術力は業界でも屈指だと認識しております。

- intent gold: admiration / sys: positive_feedback
- 判断メモ: 意図: gold admiration vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-052** `intent` — 現状のままでは来年度の黒字化は難しいと考えます。

- intent gold: inform / sys: negative_feedback
- 判断メモ: 意図: gold inform vs system negative_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-054** `entities,intent` — 「怒り」は弊社ゲーム部門の新作タイトルです。

- entities gold: 怒り/WORK / sys: 怒り/ORGANIZATION
- intent gold: inform / sys: negative_feedback
- 判断メモ: Entity 型違い: ['怒り'] / 意図: gold inform vs system negative_feedback
- 下書きの note: canary: 怒り is a game title
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-055** `sentiment,intent` — 提案内容は悪くないのですが、スケジュールが現実的ではありません。

- sentiment gold: 提案内容:positive; スケジュール:negative / sys: positive (affect None; 提案内容:positive)
- intent gold: negative_feedback / sys: positive_feedback
- 判断メモ: 評価極性: gold mixed vs system positive / 意図: gold negative_feedback vs system positive_feedback
- 下書きの note: 悪くない positive; が clause negative and wins overall
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-056** `intent` — 新製品の受注が好調で、生産が追いついておりません。

- intent gold: inform / sys: question
- 判断メモ: 意図: gold inform vs system question
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-057** `sentiment,intent` — 部長は取引先の対応に激怒していました。

- sentiment gold: 対応:negative / sys: None (affect negative; )
- intent gold: inform / sys: negative_feedback
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['激怒していました'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold inform vs system negative_feedback
- 下書きの note: 部長 is a title, not a named PERSON
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**business-059** `entities` — Ｂ２Ｂ向けＳａａＳ市場は年率２０％で成長しています。

- entities gold: ２０％/QUANTITY / sys: 20%/QUANTITY
- 判断メモ: Entity 未検出: ２０％/QUANTITY / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 20%/QUANTITY
- 下書きの note: full-width alphanumerics
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

### tech (48 文)

**tech-001** `tokens,entities` — Python3.12でasyncioの挙動が変わったらしい。

- tokens gold: Python3.12 | で | asyncio | の | 挙動 | が | 変わった | らしい | 。
- tokens sys : Python | 3 | . | 12 | で | asyncio | の | 挙動 | が | 変わったらしい | 。
- entities gold: Python3.12/PRODUCT, asyncio/PRODUCT / sys: -
- 判断メモ: 分割: system が gold より 細かい (4 境界差) / Entity 未検出: Python3.12/PRODUCT, asyncio/PRODUCT
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-002** `tokens` — このライブラリ、ドキュメントが少なすぎて使いにくい。

- tokens gold: この | ライブラリ | 、 | ドキュメント | が | 少なすぎて | 使いにくい | 。
- tokens sys : この | ライブラリ | 、 | ドキュメント | が | 少なすぎ | て | 使いにくい | 。
- 判断メモ: 分割: system が gold より 細かい (1 境界差)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-003** `entities,intent` — Dockerコンテナが起動直後に落ちるんだけど原因わかる？

- entities gold: Docker/PRODUCT / sys: -
- intent gold: question / sys: agreement
- 判断メモ: Entity 未検出: Docker/PRODUCT / 意図: gold question vs system agreement
- 下書きの note: けど is connective here, not adversative stance
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-004** `tokens,sentiment,intent` — 新しいGPUのベンチマーク、前世代の1.8倍で驚いた。

- tokens gold: 新しい | GPU | の | ベンチマーク | 、 | 前世代 | の | 1.8 | 倍 | で | 驚いた | 。
- tokens sys : 新しい | GPU | の | ベンチマーク | 、 | 前世代 | の | 1 | . | 8 | 倍 | で | 驚いた | 。
- sentiment gold: GPU:positive / sys: None (affect mixed; )
- intent gold: share_experience / sys: inform
- 判断メモ: 分割: system が gold より 細かい (2 境界差) / 評価極性: gold あり / system なし。評価語候補 ['新しい'] (sentiment.csv 未収録) / 感情語 ['驚いた'] / 意図: gold share_experience vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-006** `intent` — メモリリークの原因、ようやく特定できてスッキリした！

- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 意図: gold share_experience vs system positive_feedback
- 下書きの note: onomatopoeia スッキリ
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-007** `tokens,entities,intent` — TypeScriptの型エラーが100件以上出て泣きそう。

- tokens gold: TypeScript | の | 型エラー | が | 100 | 件 | 以上 | 出て | 泣きそう | 。
- tokens sys : TypeScript | の | 型 | エラー | が | 100 | 件以上出 | て | 泣きそう | 。
- entities gold: 100件/QUANTITY, TypeScript/PRODUCT / sys: 100件/QUANTITY
- intent gold: share_experience / sys: inform
- 判断メモ: 分割: system が gold より 別の切り方 (4 境界差) / Entity 未検出: TypeScript/PRODUCT / 意図: gold share_experience vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-008** `tokens` — 正直、このフレームワークは学習コストの割にメリットが薄い。

- tokens gold: 正直 | 、 | この | フレームワーク | は | 学習コスト | の | 割 | に | メリット | が | 薄い | 。
- tokens sys : 正直 | 、 | この | フレームワーク | は | 学習 | コスト | の | 割 | に | メリットが薄い | 。
- 判断メモ: 分割: system が gold より 粗い (3 境界差)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-009** `tokens,entities,sentiment,intent` — AWSの請求が先月より3万円も増えていて焦った。

- tokens gold: AWS | の | 請求 | が | 先月 | より | 3万 | 円 | も | 増えていて | 焦った | 。
- tokens sys : AWS | の | 請求 | が | 先月 | より | 3 | 万円 | も | 増えていて | 焦った | 。
- entities gold: 3万円/MONEY, AWS/SERVICE, 先月/DATE / sys: 3万円/MONEY, 先月/DATE, 請求/SERVICE
- sentiment gold: 請求:negative / sys: None (affect negative; )
- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 分割: system が gold より 別の切り方 (2 境界差) / Entity 未検出: AWS/SERVICE / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 請求/SERVICE / 評価極性: gold あり / system なし。system は感情語 ['焦った'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold share_experience vs system negative_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-010** `entities` — ＣＰＵ使用率が９０％を超えたらアラートを送る設定にした。

- entities gold: ９０％/QUANTITY / sys: 90%/QUANTITY
- 判断メモ: Entity 未検出: ９０％/QUANTITY / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 90%/QUANTITY
- 下書きの note: full-width alphanumerics
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-011** `entities,intent` — Rustのコンパイラ、厳しいけど的確で信頼できる。

- entities gold: Rust/PRODUCT / sys: -
- intent gold: positive_feedback / sys: admiration
- 判断メモ: Entity 未検出: Rust/PRODUCT / 意図: gold positive_feedback vs system admiration
- 下書きの note: adversative; けど clause positive
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-012** `tokens,entities` — このAPIのレスポンス、200msを切らないと要件を満たせない。

- tokens gold: この | API | の | レスポンス | 、 | 200 | ms | を | 切らないと | 要件 | を | 満たせない | 。
- tokens sys : この | API | の | レスポンス | 、 | 200 | ms | を | 切らない | と | 要件 | を | 満たせない | 。
- entities gold: 200ms/QUANTITY / sys: 200m/QUANTITY
- 判断メモ: 分割: system が gold より 細かい (1 境界差) / Entity 未検出: 200ms/QUANTITY / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 200m/QUANTITY
- 下書きの note: negations are conditional/factual, not stance
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-013** `sentiment,intent` — 新しいエディタに乗り換えたけど、結局元に戻した。

- sentiment gold: エディタ:negative / sys: None (affect None; )
- intent gold: share_experience / sys: inform
- 判断メモ: 評価極性: gold あり / system なし。評価語候補 ['新しい'] (sentiment.csv 未収録) / 感情語 [] / 意図: gold share_experience vs system inform
- 下書きの note: adversative; implied negative stance toward the new editor
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-014** `tokens,entities,sentiment` — LLMの出力をそのまま本番に流すのは怖すぎる。

- tokens gold: LLM | の | 出力 | を | そのまま | 本番 | に | 流す | の | は | 怖すぎる | 。
- tokens sys : LLM | の | 出力 | をそのまま | 本番 | に | 流す | の | は | 怖すぎる | 。
- entities gold: - / sys: LLM/TECHNOLOGY
- sentiment gold: None:negative / sys: None (affect negative; )
- 判断メモ: 分割: system が gold より 粗い (1 境界差) / Entity 過検出 (gold に無い — gold の漏れか system の誤り): LLM/TECHNOLOGY / 評価極性: gold あり / system なし。system は感情語 ['怖すぎる'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-015** `tokens` — バージョン2.3.0でこのバグは修正済みです。

- tokens gold: バージョン | 2.3.0 | で | この | バグ | は | 修正済み | です | 。
- tokens sys : バージョン | 2 | . | 3 | . | 0 | で | この | バグ | は | 修正済 | みです | 。
- 判断メモ: 分割: system が gold より 細かい (6 境界差)
- 下書きの note: version number not typed as an entity
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-016** `tokens,entities` — git rebaseで履歴が消えた。バックアップ取ってなかった。

- tokens gold: git |   | rebase | で | 履歴 | が | 消えた | 。 | バックアップ | 取ってなかった | 。
- tokens sys : git | rebase | で | 履歴が消えた | 。 | バックアップ | 取ってなかった | 。
- entities gold: git/PRODUCT / sys: -
- 判断メモ: 分割: system が gold より 粗い (11 境界差) / Entity 未検出: git/PRODUCT
- 下書きの note: space as token; negation 取ってなかった
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-017** `entities,intent` — Kubernetesの設定、ヤマダさんが一晩で直してくれて神。

- entities gold: Kubernetes/PRODUCT, ヤマダさん/PERSON / sys: ヤマダさん/PERSON
- intent gold: admiration / sys: positive_feedback
- 判断メモ: Entity 未検出: Kubernetes/PRODUCT / 意図: gold admiration vs system positive_feedback
- 下書きの note: katakana surname
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-018** `intent` — ログがだらだら流れて肝心のエラーが見つからない。

- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 意図: gold share_experience vs system negative_feedback
- 下書きの note: onomatopoeia だらだら
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-019** `entities,intent` — 誰かReactでの無限ループの直し方教えてくれませんか？

- entities gold: React/PRODUCT / sys: -
- intent gold: support_request / sys: question
- 判断メモ: Entity 未検出: React/PRODUCT / 意図: gold support_request vs system question
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-020** `tokens,entities` — 「驚き」はこのゲームエンジンのパーティクル機能の名称です。

- tokens gold: 「 | 驚き | 」 | は | この | ゲームエンジン | の | パーティクル機能 | の | 名称 | です | 。
- tokens sys : 「 | 驚き | 」 | は | この | ゲームエンジン | の | パーティクル | 機能 | の | 名称 | です | 。
- entities gold: 驚き/PRODUCT / sys: 驚き/WORK
- 判断メモ: 分割: system が gold より 細かい (1 境界差) / Entity 型違い: ['驚き']
- 下書きの note: canary: 驚き is a feature name
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-021** `entities` — PostgreSQL 16にアップグレードしたら検索が2倍速くなった。

- entities gold: 2倍/QUANTITY, PostgreSQL 16/PRODUCT / sys: 2倍/QUANTITY
- 判断メモ: Entity 未検出: PostgreSQL 16/PRODUCT
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-023** `intent` — CIが40分もかかるのはさすがに耐えられない。

- intent gold: negative_feedback / sys: positive_feedback
- 判断メモ: 意図: gold negative_feedback vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-024** `entities,intent` — 週末にRaspberry Piで温度センサーのロガーを作った。

- entities gold: Raspberry Pi/PRODUCT, 週末/DATE / sys: 週末/DATE
- intent gold: share_experience / sys: inform
- 判断メモ: Entity 未検出: Raspberry Pi/PRODUCT / 意図: gold share_experience vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-025** `sentiment,emotion,intent` — 認証周りの実装、正直不安しかない。

- sentiment gold: None:negative / sys: None (affect positive; )
- emotion gold: anxiety / sys: admiration
- intent gold: share_experience / sys: inform
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['しかない', '不安'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 感情: gold ['anxiety'] vs system admiration / 意図: gold share_experience vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-026** `entities,emotion,intent` — ミライAIのAPI、値上げではなく値下げだったので助かる。

- entities gold: ミライAI/ORGANIZATION / sys: 値上げ/TOPIC
- emotion gold: joy / sys: trust
- intent gold: positive_feedback / sys: pricing_complaint
- 判断メモ: Entity 未検出: ミライAI/ORGANIZATION / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 値上げ/TOPIC / 感情: gold ['joy'] vs system trust / 意図: gold positive_feedback vs system pricing_complaint
- 下書きの note: negation ではなく contrasts; fictional company
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-028** `entities` — 単体テストのカバレッジが95％に到達した。

- entities gold: 95％/QUANTITY / sys: 95%/QUANTITY
- 判断メモ: Entity 未検出: 95％/QUANTITY / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 95%/QUANTITY
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-029** `sentiment,intent` — このエラーメッセージ、何を直せばいいのか全然わからない。

- sentiment gold: エラーメッセージ:negative / sys: positive (affect negative; 何:positive; 全然:negative)
- intent gold: negative_feedback / sys: question
- 判断メモ: 評価極性: gold negative vs system positive / 意図: gold negative_feedback vs system question
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-030** `intent` — 正規表現が一発で通ったときの快感は格別。

- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 意図: gold share_experience vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-032** `emotion` — SDKのv3は破壊的変更が多くて移行が辛い。

- emotion gold: irritation / sys: sadness
- 判断メモ: 感情: gold ['irritation'] vs system sadness
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-033** `entities,sentiment,intent` — ３２ＧＢのメモリを積んだのにまだスワップが発生する。

- entities gold: ３２ＧＢ/QUANTITY / sys: 32GB/QUANTITY
- sentiment gold: None:negative / sys: None (affect negative; )
- intent gold: share_experience / sys: inform
- 判断メモ: Entity 未検出: ３２ＧＢ/QUANTITY / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 32GB/QUANTITY / 評価極性: gold あり / system なし。system は感情語 ['スワップが発生'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold share_experience vs system inform
- 下書きの note: のに adversative; full-width
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-034** `emotion` — 障害の復旧、佐藤さんの判断が的確だった。

- emotion gold: admiration / sys: trust
- 判断メモ: 感情: gold ['admiration'] vs system trust
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-035** `intent` — 本番DBを間違えて消しかけて心臓が止まるかと思った。

- intent gold: share_experience / sys: inform
- 判断メモ: 意図: gold share_experience vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-036** `entities` — Linuxカーネル6.8のリリースノートを読んでいる。

- entities gold: Linuxカーネル6.8/PRODUCT / sys: -
- 判断メモ: Entity 未検出: Linuxカーネル6.8/PRODUCT
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-037** `entities` — このアルゴリズム、計算量O(n²)なのは分かるけど実用上は十分速い。

- entities gold: - / sys: 十分/QUANTITY
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): 十分/QUANTITY
- 下書きの note: adversative; けど clause positive
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-038** `entities` — 新入社員がGitの使い方を1日で覚えて感心した。

- entities gold: 1日/QUANTITY, Git/PRODUCT / sys: 1日/QUANTITY
- 判断メモ: Entity 未検出: Git/PRODUCT
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-039** `intent` — マイクロサービス化、正直やらなきゃよかった。

- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 意図: gold share_experience vs system positive_feedback
- 下書きの note: regret mapped to sadness
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-041** `entities,sentiment` — 質問です。Pythonで日本語の文字数を正確に数える方法はありますか？

- entities gold: Python/PRODUCT / sys: 日本語/TOPIC
- sentiment gold: - / sys: positive (affect None; 文字数:positive)
- 判断メモ: Entity 未検出: Python/PRODUCT / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 日本語/TOPIC / 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-042** `sentiment` — ライセンス費が年間120万円は中小企業には厳しい。

- sentiment gold: ライセンス費:negative / sys: None (affect None; )
- 判断メモ: 評価極性: gold あり / system なし。評価語候補 ['厳しい'] (sentiment.csv 未収録) / 感情語 []
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-043** `intent` — フロント側の実装が終わったので、APIの仕様を確定させてほしい。

- intent gold: request / sys: inform
- 判断メモ: 意図: gold request vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-044** `intent` — 自作のパーサー、遅いけど自分で書いたから愛着がある。

- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 意図: gold share_experience vs system negative_feedback
- 下書きの note: adversative; けど clause positive
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-046** `intent` — 型推論が賢すぎて、逆に何が起きているのか追えない。

- intent gold: negative_feedback / sys: question
- 判断メモ: 意図: gold negative_feedback vs system question
- 下書きの note: 賢すぎて reads as complaint
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-048** `sentiment,intent` — AIチャットに聞いたら堂々と間違ったコードを出してきて笑った。

- sentiment gold: AIチャット:negative / sys: None (affect positive; )
- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 評価極性: gold あり / system なし。評価語候補 ['聞い'] (sentiment.csv 未収録) / 感情語 ['笑った'] / 意図: gold share_experience vs system positive_feedback
- 下書きの note: amusement mapped to joy despite negative sentiment
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-049** `emotion` — この設計、シンプルで美しい。文句のつけようがない。

- emotion gold: admiration / sys: joy
- 判断メモ: 感情: gold ['admiration'] vs system joy
- 下書きの note: negation 文句のつけようがない is positive
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-050** `sentiment` — エラーが再現しないんですが、どう調べればいいですか？

- sentiment gold: - / sys: positive (affect negative; エラー:positive)
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火
- 下書きの note: negation 再現しない is factual
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-051** `entities,intent` — メモリ使用量を40％削減できて、チーム全員でガッツポーズした。

- entities gold: 40％/QUANTITY / sys: 40%/QUANTITY
- intent gold: share_experience / sys: inform
- 判断メモ: Entity 未検出: 40％/QUANTITY / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 40%/QUANTITY / 意図: gold share_experience vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-054** `intent` — 依存パッケージが300個超えてるの、さすがに多すぎでは？

- intent gold: question / sys: positive_feedback
- 判断メモ: 意図: gold question vs system positive_feedback
- 下書きの note: rhetorical question with negative stance
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-058** `intent` — ログ出力を減らしたらディスク容量が2TB空いた。

- intent gold: share_experience / sys: inform
- 判断メモ: 意図: gold share_experience vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-059** `sentiment,emotion,intent` — レガシーコードを触るのは嫌だが、避けては通れない。

- sentiment gold: レガシーコード:negative / sys: None (affect negative; )
- emotion gold: disgust / sys: irritation
- intent gold: inform / sys: negative_feedback
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['嫌だ'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 感情: gold ['disgust'] vs system irritation / 意図: gold inform vs system negative_feedback
- 下書きの note: adversative but the feeling sits in the first clause; second clause is resignation
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**tech-060** `sentiment,intent` — パスワードを平文で保存してるって聞いてぞっとした。

- sentiment gold: None:negative / sys: None (affect negative; )
- intent gold: share_experience / sys: request
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['ぞっとした'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold share_experience vs system request
- 下書きの note: ぞっと mimetic; could also be anxiety
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

### literary (43 文)

**literary-002** `tokens` — 彼女は嬉しくなかった。ただ、静かに頷いた。

- tokens gold: 彼女 | は | 嬉しくなかった | 。 | ただ | 、 | 静かに | 頷いた | 。
- tokens sys : 彼女 | は | 嬉しくなかった | 。 | ただ | 、 | 静 | か | に | 頷いた | 。
- 判断メモ: 分割: system が gold より 細かい (2 境界差)
- 下書きの note: 嬉しくない -> mild sadness; holder is the character
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-003** `tokens,sentiment,intent` — 春の光が、古い縁側にやわらかく落ちていた。

- tokens gold: 春 | の | 光 | が | 、 | 古い | 縁側 | に | やわらかく | 落ちていた | 。
- tokens sys : 春 | の | 光 | が | 、 | 古い | 縁側 | にやわらかく | 落ちていた | 。
- sentiment gold: - / sys: negative (affect None; 光:negative)
- intent gold: inform / sys: negative_feedback
- 判断メモ: 分割: system が gold より 粗い (1 境界差) / 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 意図: gold inform vs system negative_feedback
- 下書きの note: neutral description
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-004** `entities,emotion,intent` — 田中は手紙を読み終えると、声を上げて泣いた。

- entities gold: 田中/PERSON / sys: -
- emotion gold: sadness / sys: moved
- intent gold: inform / sys: share_experience
- 判断メモ: Entity 未検出: 田中/PERSON / 感情: gold ['sadness'] vs system moved / 意図: gold inform vs system share_experience
- 下書きの note: could also be moved; context missing
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-005** `tokens` — 遠くで犬がわんわんと吠えている。それだけの夜だった。

- tokens gold: 遠く | で | 犬 | が | わんわん | と | 吠えている | 。 | それ | だけ | の | 夜 | だった | 。
- tokens sys : 遠くで | 犬 | が | わんわん | と | 吠えている | 。 | それ | だけ | の | 夜だった | 。
- 判断メモ: 分割: system が gold より 粗い (2 境界差)
- 下書きの note: canary: animal sound
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-006** `tokens` — 少年は、初めて見る雪に目を輝かせた。

- tokens gold: 少年 | は | 、 | 初めて | 見る | 雪 | に | 目 | を | 輝かせた | 。
- tokens sys : 少年 | は | 、 | 初めて | 見る雪 | に | 目を輝かせた | 。
- 判断メモ: 分割: system が gold より 粗い (3 境界差)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-007** `tokens,intent` — 悪くない人生だった、と老人は呟いた。

- tokens gold: 悪くない | 人生 | だった | 、 | と | 老人 | は | 呟いた | 。
- tokens sys : 悪くない | 人生だった | 、 | と | 老人 | は | 呟いた | 。
- intent gold: inform / sys: positive_feedback
- 判断メモ: 分割: system が gold より 粗い (1 境界差) / 意図: gold inform vs system positive_feedback
- 下書きの note: 悪くない -> positive sentiment, no emotion
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-008** `tokens,entities,intent` — 昭和五十二年の夏、ぼくらは川で一日中泳いでいた。

- tokens gold: 昭和五十二年 | の | 夏 | 、 | ぼくら | は | 川 | で | 一日中 | 泳いでいた | 。
- tokens sys : 昭和五十二年 | の | 夏 | 、 | ぼく | ら | は | 川 | で | 一日 | 中泳いでいた | 。
- entities gold: 一日中/QUANTITY, 昭和五十二年/DATE / sys: 一日/QUANTITY, 五十二年/QUANTITY
- intent gold: share_experience / sys: inform
- 判断メモ: 分割: system が gold より 細かい (3 境界差) / Entity 未検出: 一日中/QUANTITY, 昭和五十二年/DATE / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 一日/QUANTITY, 五十二年/QUANTITY / 意図: gold share_experience vs system inform
- 下書きの note: era-name date in kanji numerals
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-009** `emotion` — 母の背中は、思っていたよりずっと小さかった。

- emotion gold: sadness / sys: -
- 判断メモ: 感情: system 未検出 — 感情語候補 ['小さい'] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- 下書きの note: implicit emotion; could be moved
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-010** `tokens` — 彼は怒っていたわけではない。ただ、疲れていたのだ。

- tokens gold: 彼 | は | 怒っていた | わけ | で | は | ない | 。 | ただ | 、 | 疲れていた | の | だ | 。
- tokens sys : 彼 | は | 怒っていたわけで | は | ない | 。 | ただ | 、 | 疲れていたのだ | 。
- 判断メモ: 分割: system が gold より 粗い (4 境界差)
- 下書きの note: negated anger; fatigue is not an emotion label
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-011** `tokens` — 京都の路地に降るしとしと雨が、彼を少しだけ寂しくさせた。

- tokens gold: 京都 | の | 路地 | に | 降る | しとしと | 雨 | が | 、 | 彼 | を | 少し | だけ | 寂しくさせた | 。
- tokens sys : 京都 | の | 路地 | に | 降る | しとしと | 雨 | が | 、 | 彼 | を | 少し | だけ | 寂しく | させた | 。
- 判断メモ: 分割: system が gold より 細かい (1 境界差)
- 下書きの note: onomatopoeia しとしと with emotion (not a canary)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-012** `tokens` — 『月影の庭』を書き上げたとき、彼女は三十歳になっていた。

- tokens gold: 『 | 月影の庭 | 』 | を | 書き上げた | とき | 、 | 彼女 | は | 三十 | 歳 | に | なっていた | 。
- tokens sys : 『 | 月影 | の | 庭 | 』 | を | 書き上げた | とき | 、 | 彼女 | は | 三十歳 | に | なっていた | 。
- 判断メモ: 分割: system が gold より 細かい (3 境界差)
- 下書きの note: fictional title
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-013** `emotion` — 祖父の時計は、今も胸の奥でこちこちと鳴っている。

- emotion gold: moved / sys: -
- 判断メモ: 感情: system 未検出 — 感情語候補 [] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- 下書きの note: metaphorical; onomatopoeia こちこち carries nostalgia
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-014** `tokens` — 彼女の笑顔を見た瞬間、胸のつかえがすっと消えた。

- tokens gold: 彼女 | の | 笑顔 | を | 見た | 瞬間 | 、 | 胸 | の | つかえ | が | すっと | 消えた | 。
- tokens sys : 彼女 | の | 笑顔 | を | 見た瞬間 | 、 | 胸のつかえが | すっと消えた | 。
- 判断メモ: 分割: system が gold より 粗い (5 境界差)
- 下書きの note: mimetic すっと
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-015** `tokens` — 期待していた返事は来なかった。それでも、彼は待ち続けた。

- tokens gold: 期待していた | 返事 | は | 来なかった | 。 | それでも | 、 | 彼 | は | 待ち続けた | 。
- tokens sys : 期待 | していた | 返事 | は | 来なかった | 。 | それでも | 、 | 彼 | は | 待ち続けた | 。
- 判断メモ: 分割: system が gold より 細かい (1 境界差)
- 下書きの note: negation 来なかった; それでも adversative
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-016** `tokens,emotion` — 東京駅の雑踏の中で、彼はふと故郷の匂いを思い出した。

- tokens gold: 東京駅 | の | 雑踏 | の | 中 | で | 、 | 彼 | は | ふと | 故郷 | の | 匂い | を | 思い出した | 。
- tokens sys : 東京駅 | の | 雑踏 | の | 中 | で | 、 | 彼 | はふ | と | 故郷 | の | 匂い | を | 思い出した | 。
- emotion gold: moved / sys: -
- 判断メモ: 分割: system が gold より 別の切り方 (2 境界差) / 感情: system 未検出 — 感情語候補 ['匂い'] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- 下書きの note: nostalgia mapped to moved
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-017** `tokens` — それは、たしかに美しい嘘だった。

- tokens gold: それ | は | 、 | たしかに | 美しい | 嘘 | だった | 。
- tokens sys : それ | は | 、 | たしかに | 美しい | 嘘だった | 。
- 判断メモ: 分割: system が gold より 粗い (1 境界差)
- 下書きの note: evaluative adjective on a negative noun; polarity debatable
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-018** `tokens,sentiment,emotion,intent` — 娘が生まれた日、男は初めて神に感謝した。

- tokens gold: 娘 | が | 生まれた | 日 | 、 | 男 | は | 初めて | 神 | に | 感謝した | 。
- tokens sys : 娘 | が | 生まれた | 日 | 、 | 男 | は | 初めて | 神 | に | 感謝 | した | 。
- sentiment gold: - / sys: positive (affect positive; 男:positive; 男:positive)
- emotion gold: moved / sys: admiration
- intent gold: inform / sys: positive_feedback
- 判断メモ: 分割: system が gold より 細かい (1 境界差) / 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 感情: gold ['moved'] vs system admiration / 意図: gold inform vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-019** `tokens,entities` — 「もう二度と会わない」と、彼女は言った。

- tokens gold: 「 | もう | 二度と | 会わない | 」 | と | 、 | 彼女 | は | 言った | 。
- tokens sys : 「 | もう | 二度と会わない | 」 | と | 、 | 彼女 | は | 言った | 。
- entities gold: - / sys: 二度/QUANTITY
- 判断メモ: 分割: system が gold より 粗い (1 境界差) / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 二度/QUANTITY
- 下書きの note: negation inside quote
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-020** `tokens,entities` — 五月の風が、カーテンをふわりと揺らした。

- tokens gold: 五月 | の | 風 | が | 、 | カーテン | を | ふわり | と | 揺らした | 。
- tokens sys : 五月 | の | 風 | が | 、 | カーテン | をふわり | と | 揺らした | 。
- entities gold: 五月/DATE / sys: -
- 判断メモ: 分割: system が gold より 粗い (1 境界差) / Entity 未検出: 五月/DATE
- 下書きの note: canary: mimetic ふわり, pure description
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-021** `entities,intent` — 老人は孫に、「手紙をもう一度読んでくれないか」と頼んだ。

- entities gold: - / sys: 一度/QUANTITY
- intent gold: request / sys: inform
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): 一度/QUANTITY / 意図: gold request vs system inform
- 下書きの note: request inside quote by 老人
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-023** `entities,sentiment,emotion` — 彼は約束を破らなかった。ただ一度も、だ。

- entities gold: - / sys: 一度/QUANTITY
- sentiment gold: 彼:positive / sys: None (affect positive; )
- emotion gold: trust / sys: admiration
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): 一度/QUANTITY / 評価極性: gold あり / system なし。system は感情語 ['約束'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 感情: gold ['trust'] vs system admiration
- 下書きの note: negation 破らなかった is positive
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-024** `entities` — 十年ぶりの再会に、二人は言葉を失った。

- entities gold: 十年/QUANTITY / sys: 二人/QUANTITY, 十年/QUANTITY
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): 二人/QUANTITY
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-026** `sentiment` — 彼女の声は震えていたが、瞳は少しも揺らがなかった。

- sentiment gold: 彼女:positive / sys: None (affect negative; )
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['震えていた'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加
- 下書きの note: adversative; second clause conveys resolve (no label), narrator admires
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-027** `emotion,intent` — 父は何も言わず、ただ私の頭に手を置いた。

- emotion gold: moved / sys: -
- intent gold: inform / sys: question
- 判断メモ: 感情: system 未検出 — 感情語候補 [] (emotion.csv 未収録なら追加、無ければ gold は文脈推論) / 意図: gold inform vs system question
- 下書きの note: implicit
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-029** `intent` — その知らせを聞いて、村人たちは怒りに震えた。

- intent gold: inform / sys: negative_feedback
- 判断メモ: 意図: gold inform vs system negative_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-030** `intent` — 子どもの頃、ぼくは夏休みが永遠に続くと信じていた。

- intent gold: share_experience / sys: inform
- 判断メモ: 意図: gold share_experience vs system inform
- 下書きの note: 信じていた is belief, not trust emotion
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-031** `emotion,intent` — 「ありがとう」と言えなかったことを、彼は今も悔やんでいる。

- emotion gold: sadness / sys: joy
- intent gold: inform / sys: positive_feedback
- 判断メモ: 感情: gold ['sadness'] vs system joy / 意図: gold inform vs system positive_feedback
- 下書きの note: negation 言えなかった; regret -> sadness
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-032** `sentiment,emotion,intent` — 「もう少しだけ、ここにいてもいい？」と彼女は小さく言った。

- sentiment gold: - / sys: positive (affect None; None:positive)
- emotion gold: anxiety / sys: -
- intent gold: request / sys: positive_feedback
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 感情: system 未検出 — 感情語候補 ['いい'] (emotion.csv 未収録なら追加、無ければ gold は文脈推論) / 意図: gold request vs system positive_feedback
- 下書きの note: permission request inside quote
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-035** `emotion,intent` — 逃げるのは嫌だった。けれど、戦うのはもっと嫌だった。

- emotion gold: refusal / sys: irritation
- intent gold: inform / sys: negative_feedback
- 判断メモ: 感情: gold ['refusal'] vs system irritation / 意図: gold inform vs system negative_feedback
- 下書きの note: けれど adversative; both clauses negative, second stronger
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-037** `intent` — 兄の死から三年、母はまだ兄の部屋を片付けられずにいる。

- intent gold: inform / sys: share_experience
- 判断メモ: 意図: gold inform vs system share_experience
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-038** `entities,sentiment,intent` — 彼の作った料理は、正直に言えば、うまくはなかった。

- entities gold: - / sys: 料理/TOPIC
- sentiment gold: 料理:negative / sys: None (affect negative; )
- intent gold: inform / sys: share_experience
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): 料理/TOPIC / 評価極性: gold あり / system なし。system は感情語 ['うまくはなかった'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold inform vs system share_experience
- 下書きの note: negation うまくはなかった
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-039** `intent` — 満員電車の中で、青年はふいに泣きたくなった。

- intent gold: inform / sys: share_experience
- 判断メモ: 意図: gold inform vs system share_experience
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-040** `intent` — 手のひらの小さな貝殻が、彼女には宝物に思えた。

- intent gold: inform / sys: positive_feedback
- 判断メモ: 意図: gold inform vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-041** `entities` — 一九九五年一月、街は一夜にして姿を変えた。

- entities gold: 一九九五年一月/DATE / sys: 一九九五年/QUANTITY
- 判断メモ: Entity 未検出: 一九九五年一月/DATE / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 一九九五年/QUANTITY
- 下書きの note: kanji-numeral date
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-043** `intent` — 犬は主人の帰りを、門の前でじっと待っていた。

- intent gold: inform / sys: request
- 判断メモ: 意図: gold inform vs system request
- 下書きの note: mimetic じっと; animal as holder
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-045** `entities` — 秋祭りの夜、太鼓の音がどんどん響いて、子どもたちは飛び跳ねた。

- entities gold: 秋祭り/EVENT / sys: -
- 判断メモ: Entity 未検出: 秋祭り/EVENT
- 下書きの note: onomatopoeia どんどん; joy is implicit
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-049** `sentiment,intent` — 新しい家は広くて明るかったが、どこか落ち着かなかった。

- sentiment gold: 新しい家:negative / sys: None (affect negative; )
- intent gold: inform / sys: question
- 判断メモ: 評価極性: gold あり / system なし。評価語候補 ['新しい', '広い', '明るい'] (sentiment.csv 未収録) / 感情語 ['落ち着かなかった'] / 意図: gold inform vs system question
- 下書きの note: adversative; が clause negative
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-051** `emotion` — 「行くな」と言えば、彼は行かなかっただろう。

- emotion gold: sadness / sys: -
- 判断メモ: 感情: system 未検出 — 感情語候補 [] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- 下書きの note: counterfactual regret
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-052** `intent` — 病室の窓から見える桜に、彼女は小さく笑った。

- intent gold: inform / sys: positive_feedback
- 判断メモ: 意図: gold inform vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-053** `intent` — 三千円の古い辞書が、彼の人生を変えた。

- intent gold: inform / sys: positive_feedback
- 判断メモ: 意図: gold inform vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-055** `entities` — 北の町では、十一月にはもう雪が積もる。

- entities gold: 十一月/DATE / sys: -
- 判断メモ: Entity 未検出: 十一月/DATE
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-057** `intent` — 何も変わっていないようで、すべてが変わっていた。

- intent gold: inform / sys: question
- 判断メモ: 意図: gold inform vs system question
- 下書きの note: ambiguous mood; no label assigned
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**literary-058** `entities,emotion` — 祖母の作る味噌汁は、世界で一番おいしかった。

- entities gold: - / sys: 一番/QUANTITY
- emotion gold: admiration / sys: -
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): 一番/QUANTITY / 感情: system 未検出 — 感情語候補 ['一番おいしい'] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

### conversation (42 文)

**conversation-001** `sentiment` — ねえ、今日の夕飯何がいい？

- sentiment gold: - / sys: positive (affect None; 夕飯何:positive)
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-002** `sentiment,intent` — えー、またカレー？昨日も食べたじゃん。

- sentiment gold: カレー:negative / sys: None (affect negative; )
- intent gold: negative_feedback / sys: share_experience
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['えー、また'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold negative_feedback vs system share_experience
- 下書きの note: complaint, not a real question
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-003** `tokens,sentiment,intent` — 別に怒ってないよ。ただちょっと疲れてるだけ。

- tokens gold: 別に | 怒ってない | よ | 。 | ただ | ちょっと | 疲れてる | だけ | 。
- tokens sys : 別 | に | 怒ってない | よ | 。 | ただ | ちょっと | 疲れてる | だけ | 。
- sentiment gold: - / sys: negative (affect negative; 別:negative)
- intent gold: inform / sys: share_experience
- 判断メモ: 分割: system が gold より 細かい (1 境界差) / 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 意図: gold inform vs system share_experience
- 下書きの note: negated anger; may actually be irritated (tone), left empty
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-004** `emotion,intent` — ごめん、明日の約束、やっぱり行けなくなった。

- emotion gold: sadness / sys: admiration
- intent gold: inform / sys: share_experience
- 判断メモ: 感情: gold ['sadness'] vs system admiration / 意図: gold inform vs system share_experience
- 下書きの note: apology; negation 行けなくなった
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-005** `intent` — やった！テスト90点だった！

- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 意図: gold share_experience vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-007** `tokens,intent` — その話、前にも聞いたけど、何回聞いても面白いね。

- tokens gold: その | 話 | 、 | 前 | に | も | 聞いた | けど | 、 | 何回 | 聞いても | 面白い | ね | 。
- tokens sys : その | 話 | 、 | 前 | に | も | 聞いた | けど | 、 | 何回 | 聞いて | も | 面白い | ね | 。
- intent gold: positive_feedback / sys: request
- 判断メモ: 分割: system が gold より 細かい (1 境界差) / 意図: gold positive_feedback vs system request
- 下書きの note: adversative; けど clause positive
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-008** `entities` — マジで？あの二人、別れたの？

- entities gold: - / sys: 二人/QUANTITY
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): 二人/QUANTITY
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-009** `tokens,sentiment,intent` — うーん、悪くはないけど、もう少し安いと嬉しいな。

- tokens gold: うーん | 、 | 悪くはない | けど | 、 | もう | 少し | 安い | と | 嬉しい | な | 。
- tokens sys : う | ー | ん | 、 | 悪くはない | けど | 、 | もう | 少し | 安い | と | 嬉しい | な | 。
- sentiment gold: None:negative / sys: positive (affect positive; ー:positive)
- intent gold: pricing_complaint / sys: positive_feedback
- 判断メモ: 分割: system が gold より 細かい (2 境界差) / 評価極性: gold negative vs system positive / 意図: gold pricing_complaint vs system positive_feedback
- 下書きの note: 悪くはない positive, but けど clause (price) wins; 嬉しい is conditional, not felt
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-010** `sentiment,intent` — お母さん、田中くんの家に泊まってもいい？

- sentiment gold: - / sys: positive (affect None; 家:positive)
- intent gold: request / sys: question
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 意図: gold request vs system question
- 下書きの note: permission request
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-013** `sentiment,intent` — え、それ本気で言ってる？ちょっと引くわ。

- sentiment gold: None:negative / sys: None (affect negative; )
- intent gold: negative_feedback / sys: inform
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['引くわ'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold negative_feedback vs system inform
- 下書きの note: rhetorical question
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-014** `tokens,entities,intent` — 先週末、家族で軽井沢に行ってきたんだ。

- tokens gold: 先週末 | 、 | 家族 | で | 軽井沢 | に | 行ってきた | ん | だ | 。
- tokens sys : 先週末 | 、 | 家族 | で | 軽井沢 | に | 行ってきたんだ | 。
- entities gold: 先週末/DATE, 軽井沢/LOCATION / sys: 先週末/DATE
- intent gold: share_experience / sys: inform
- 判断メモ: 分割: system が gold より 粗い (2 境界差) / Entity 未検出: 軽井沢/LOCATION / 意図: gold share_experience vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-015** `tokens,sentiment,intent` — いや、それは違うと思うな。

- tokens gold: いや | 、 | それ | は | 違う | と | 思う | な | 。
- tokens sys : い | や | 、 | それ | は | 違うと思う | な | 。
- sentiment gold: None:negative / sys: None (affect negative; )
- intent gold: negative_feedback / sys: inform
- 判断メモ: 分割: system が gold より 粗い (3 境界差) / 評価極性: gold あり / system なし。system は感情語 ['違うと思う'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold negative_feedback vs system inform
- 下書きの note: disagreement
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-017** `tokens` — 猫がゴロゴロ喉鳴らしてる。

- tokens gold: 猫 | が | ゴロゴロ | 喉 | 鳴らしてる | 。
- tokens sys : 猫 | が | ゴロゴロ | 喉鳴らしてる | 。
- 判断メモ: 分割: system が gold より 粗い (1 境界差)
- 下書きの note: canary: animal sound
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-018** `tokens,emotion` — 来月の家賃、また5000円上がるんだって。ありえない。

- tokens gold: 来月 | の | 家賃 | 、 | また | 5000 | 円 | 上がる | ん | だって | 。 | ありえない | 。
- tokens sys : 来月 | の | 家賃 | 、 | また | 5000 | 円上 | がるんだ | って | 。 | ありえない | 。
- emotion gold: anger / sys: refusal
- 判断メモ: 分割: system が gold より 粗い (5 境界差) / 感情: gold ['anger'] vs system refusal
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-020** `tokens,entities,intent` — 山田さんって、いつも笑顔で感じいいよね。

- tokens gold: 山田 | さん | って | 、 | いつも | 笑顔 | で | 感じ | いい | よ | ね | 。
- tokens sys : 山田さんって | 、 | いつも | 笑顔 | で | 感じいい | よ | ね | 。
- entities gold: 山田さん/PERSON / sys: -
- intent gold: positive_feedback / sys: question
- 判断メモ: 分割: system が gold より 粗い (3 境界差) / Entity 未検出: 山田さん/PERSON / 意図: gold positive_feedback vs system question
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-021** `entities,intent` — ちょっと、聞いてる？さっきから返事ないんだけど。

- entities gold: - / sys: さっき/DATE
- intent gold: question / sys: request
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): さっき/DATE / 意図: gold question vs system request
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-022** `sentiment` — えっと、駅までどう行けばいいですか？

- sentiment gold: - / sys: positive (affect mixed; None:positive)
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-023** `sentiment` — この映画、期待してなかったけど泣いちゃった。

- sentiment gold: 映画:positive / sys: None (affect positive; )
- 判断メモ: 評価極性: gold あり / system なし。評価語候補 ['してない'] (sentiment.csv 未収録) / 感情語 ['泣いちゃった', '期待']
- 下書きの note: negated expectation + けど; 泣いた = moved
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-025** `emotion,intent` — 別に嬉しくないし。……まあ、ちょっとは嬉しいけど。

- emotion gold: joy / sys: sadness
- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 感情: gold ['joy'] vs system sadness / 意図: gold share_experience vs system positive_feedback
- 下書きの note: negation retracted; けど clause (mild joy) wins
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-026** `sentiment,intent` — 大丈夫だよ、心配しないで。私がついてる。

- sentiment gold: - / sys: positive (affect positive; None:positive)
- intent gold: inform / sys: request
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 意図: gold inform vs system request
- 下書きの note: reassurance; 心配しないで is directed at listener, not speaker's anxiety
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-030** `sentiment,intent` — 何でいつも私ばっかり片付けなきゃいけないの？

- sentiment gold: None:negative / sys: None (affect negative; )
- intent gold: negative_feedback / sys: share_experience
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['私ばっかり'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold negative_feedback vs system share_experience
- 下書きの note: rhetorical question
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-031** `sentiment` — この前のパン屋、また行きたいね。

- sentiment gold: パン屋:positive / sys: None (affect positive; )
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['また行きたい'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-033** `sentiment,intent` — あー、もうイライラする。なんで伝わらないの。

- sentiment gold: None:negative / sys: None (affect negative; )
- intent gold: share_experience / sys: negative_feedback
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['イライラする', 'なんで'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold share_experience vs system negative_feedback
- 下書きの note: onomatopoeia イライラ
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-034** `entities,sentiment,intent` — 昨日のライブ、めっちゃ楽しかったよ！

- entities gold: 昨日/DATE / sys: ライブ/EVENT, 昨日/DATE
- sentiment gold: ライブ:positive / sys: None (affect positive; )
- intent gold: share_experience / sys: positive_feedback
- 判断メモ: Entity 過検出 (gold に無い — gold の漏れか system の誤り): ライブ/EVENT / 評価極性: gold あり / system なし。system は感情語 ['楽しかった', 'めっちゃ'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold share_experience vs system positive_feedback
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-035** `sentiment,intent` — 正直、あの人のこと苦手なんだよね。

- sentiment gold: あの人:negative / sys: None (affect negative; )
- intent gold: inform / sys: agreement
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['だよね', '苦手'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold inform vs system agreement
- 下書きの note: 苦手 is mild; disgust may be too strong
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-037** `entities,emotion` — それ、３０００円もしたの？高くない？

- entities gold: ３０００円/MONEY / sys: 3000円/MONEY
- emotion gold: surprise / sys: -
- 判断メモ: Entity 未検出: ３０００円/MONEY / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 3000円/MONEY / 感情: system 未検出 — 感情語候補 ['高い'] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- 下書きの note: 高くない？ is rhetorical (= too expensive); full-width digits
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-038** `sentiment,intent` — 全然大丈夫。気にしないで。

- sentiment gold: - / sys: positive (affect None; None:positive)
- intent gold: inform / sys: request
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 意図: gold inform vs system request
- 下書きの note: reassurance
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-041** `intent` — うそでしょ、もう12月？一年早すぎる。

- intent gold: share_experience / sys: inform
- 判断メモ: 意図: gold share_experience vs system inform
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-042** `sentiment,intent` — 佐藤さん、また遅刻？いい加減にしてほしい。

- sentiment gold: 佐藤さん:negative / sys: positive (affect negative; 遅刻:positive)
- intent gold: negative_feedback / sys: request
- 判断メモ: 評価極性: gold negative vs system positive / 意図: gold negative_feedback vs system request
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-044** `entities` — 今度の日曜、暇？一緒に映画行かない？

- entities gold: 今度の日曜/DATE / sys: 日曜/DATE
- 判断メモ: Entity 未検出: 今度の日曜/DATE / Entity 過検出 (gold に無い — gold の漏れか system の誤り): 日曜/DATE
- 下書きの note: invitation
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-045** `sentiment,intent` — いやいや、それは無理。絶対無理。

- sentiment gold: None:negative / sys: None (affect negative; )
- intent gold: inform / sys: negative_feedback
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['無理', '無理'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold inform vs system negative_feedback
- 下書きの note: flat refusal; no dedicated intent
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-046** `intent` — え、ほんとに？おめでとう！すごいじゃん！

- intent gold: admiration / sys: positive_feedback
- 判断メモ: 意図: gold admiration vs system positive_feedback
- 下書きの note: congratulation
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-047** `intent` — ちょっと待って、財布どこに置いたっけ。

- intent gold: question / sys: request
- 判断メモ: 意図: gold question vs system request
- 下書きの note: self-directed question
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-049** `sentiment,intent` — なんか今日、顔色悪くない？大丈夫？

- sentiment gold: - / sys: positive (affect negative; 今日:positive)
- intent gold: question / sys: share_experience
- 判断メモ: 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 意図: gold question vs system share_experience
- 下書きの note: 悪くない？ here is rhetorical (= looks bad), opposite of the 悪くない idiom
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-051** `intent` — おばあちゃんの家、いつ行っても落ち着くんだよね。

- intent gold: share_experience / sys: agreement
- 判断メモ: 意図: gold share_experience vs system agreement
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-052** `sentiment,intent` — 弟が「宿題やった」って言うけど、絶対やってない。

- sentiment gold: 弟:negative / sys: None (affect positive; )
- intent gold: inform / sys: positive_feedback
- 判断メモ: 評価極性: gold あり / system なし。system は感情語 ['やった'] のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加 / 意図: gold inform vs system positive_feedback
- 下書きの note: けど adversative; suspicion has no label
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-053** `intent` — ごめん、今日はちょっと気分が乗らない。

- intent gold: inform / sys: share_experience
- 判断メモ: 意図: gold inform vs system share_experience
- 下書きの note: mild; also a refusal
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-054** `intent` — このスープ、味薄くない？

- intent gold: question / sys: negative_feedback
- 判断メモ: 意図: gold question vs system negative_feedback
- 下書きの note: 薄くない？ is rhetorical (= too thin)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-055** `intent` — 田舎の夜って、虫がりんりん鳴いてて風情あるよね。

- intent gold: share_experience / sys: positive_feedback
- 判断メモ: 意図: gold share_experience vs system positive_feedback
- 下書きの note: animal sound with emotion (not a canary)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-058** `entities,intent` — 給料日前でお金ない。ラーメン一杯800円でも迷う。

- entities gold: 800円/MONEY, 一杯/QUANTITY, 給料日前/DATE / sys: 800円/MONEY, 給料日前/DATE
- intent gold: share_experience / sys: inform
- 判断メモ: Entity 未検出: 一杯/QUANTITY / 意図: gold share_experience vs system inform
- 下書きの note: negation お金ない is factual
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-059** `entities,sentiment,emotion` — 明日、雨降らないといいね。運動会だし。

- entities gold: 明日/DATE, 運動会/EVENT / sys: 明日/DATE
- sentiment gold: - / sys: positive (affect positive; 明日:positive)
- emotion gold: anxiety / sys: anticipation
- 判断メモ: Entity 未検出: 運動会/EVENT / 評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火 / 感情: gold ['anxiety'] vs system anticipation
- 下書きの note: could also be anticipation
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

**conversation-060** `emotion` — よし、決めた。来年こそ海外行く。

- emotion gold: anticipation / sys: -
- 判断メモ: 感情: system 未検出 — 感情語候補 [] (emotion.csv 未収録なら追加、無ければ gold は文脈推論)
- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち

