# Annotated eval — KotobaCore 0.4.0 (300 items)

| Tokenization (73 items) | P 0.8907 / R 0.9196 / F1 0.9049 |
| entity_surface | P 0.7241 / R 0.6034 / F1 0.6583 |
| entity_typed | P 0.7103 / R 0.592 / F1 0.6458 |
| Sentiment accuracy | 58.3% (n=300) |
| Emotion accuracy | 24.7% (n=182), canary FP 22.7% (n=22) |
| Intent accuracy | 13.0% (n=300) |
| Sentiment target accuracy | 62.5% (n=16) |
| Timing | mean 3.09 ms / p95 4.03 ms |

## Per genre

| genre | sentiment | emotion | intent |
|---|---|---|---|
| business | 63.3% | 30.4% | 18.3% |
| conversation | 48.3% | 19.5% | 20.0% |
| literary | 86.7% | 24.3% | 1.7% |
| sns | 46.7% | 32.6% | 15.0% |
| tech | 46.7% | 17.1% | 10.0% |

## Failures (333)

- `sns-001` emotion: gold=['joy'] sys=exaggeration 今日のランチ、マジで美味しかった😋
- `sns-002` tokens: gold=['新しい', 'iPhone', '買った', 'けど', '正直', 'そこまで', '感動しない', '。'] sys=['新しい', 'iPhone', '買った', 'けど', '正直', 'そこ', 'まで', '感動', 'しない', '。'] 
- `sns-002` sentiment: gold=negative sys=None 新しいiPhone買ったけど正直そこまで感動しない。
- `sns-003` emotion: gold=['anticipation'] sys=joy 明日のライブ、わくわくが止まらない！
- `sns-004` sentiment: gold=negative sys=None 電車遅延でイライラする…また遅刻だよ。
- `sns-005` tokens: gold=['隣', 'の', '猫', 'が', 'にゃーにゃー', '鳴いてる', '。'] sys=['隣', 'の', '猫', 'が', 'にゃーにゃー', '鳴い', 'てる', '。'] 
- `sns-006` tokens: gold=['渋谷', 'の', 'スクランブル交差点', '、', '人', '多すぎて', '疲れた', '😩'] sys=['渋谷', 'の', 'スクランブル', '交差点', '、', '人多すぎて', '疲れた', '😩'] 
- `sns-006` sentiment: gold=negative sys=None 渋谷のスクランブル交差点、人多すぎて疲れた😩
- `sns-006` emotion: gold=['irritation'] sys=sadness 渋谷のスクランブル交差点、人多すぎて疲れた😩
- `sns-007` tokens: gold=['この', 'カフェ', '、', 'コーヒー', 'は', '微妙', 'だ', 'けど', 'ケーキ', 'は', '神', '。'] sys=['この', 'カフェ', '、', 'コーヒー', 'は', '微妙だ', 'けど', 'ケーキ', 'は', '神', '。'] 
- `sns-008` sentiment: gold=None sys=positive 誰か新宿でおすすめのラーメン屋教えて！
- `sns-009` emotion: gold=['surprise'] sys=exaggeration え、ブルースカイズ再結成ってマジ？？
- `sns-010` tokens: gold=['3', '年', 'ぶり', 'に', '実家', '帰ったら', '犬', 'が', '覚えててくれて', '泣いた', '🥲'] sys=['3', '年ぶ', 'り', 'に', '実家帰', 'っ', 'たら', '犬', 'が', '覚えててくれて', '泣いた', '🥲'] 
- `sns-011` tokens: gold=['正直', '、', '今回', 'の', 'アップデート', 'は', '改悪', 'だ', 'と', '思う', '。'] sys=['正直', '、', '今回', 'の', 'アップデート', 'は', '改悪だ', 'と', '思う', '。'] 
- `sns-011` sentiment: gold=negative sys=None 正直、今回のアップデートは改悪だと思う。
- `sns-011` emotion: gold=['irritation'] sys=admiration 正直、今回のアップデートは改悪だと思う。
- `sns-013` tokens: gold=['田中', 'さん', 'の', '新曲', '、', '何回', '聴いても', '飽きない', '✨'] sys=['田中', 'さん', 'の', '新曲', '、', '何回', '聴いて', 'も', '飽きない', '✨'] 
- `sns-013` sentiment: gold=positive sys=None 田中さんの新曲、何回聴いても飽きない✨
- `sns-013` emotion: gold=['admiration'] sys=anticipation 田中さんの新曲、何回聴いても飽きない✨
- `sns-015` tokens: gold=['悪くない', 'ん', 'だ', 'けど', '、', 'リピート', 'は', 'しない', 'か', 'な', '。'] sys=['悪くない', 'んだ', 'けど', '、', 'リピート', 'はしないか', 'な', '。'] 
- `sns-015` sentiment: gold=negative sys=positive 悪くないんだけど、リピートはしないかな。
- `sns-017` emotion: gold=['sadness'] sys=admiration ぴえん🥺推しのグッズ売り切れてた…
- `sns-019` tokens: gold=['なんで', '月曜', 'って', '来る', 'の', '早い', 'ん', 'だろ', '😇'] sys=['なん', 'で', '月曜って', '来る', 'の', '早い', 'んだろ', '😇'] 
- `sns-019` sentiment: gold=negative sys=positive なんで月曜って来るの早いんだろ😇
- `sns-019` target: gold=['月曜'] sys=[] なんで月曜って来るの早いんだろ😇
- `sns-019` emotion: gold=['irritation'] sys=exaggeration なんで月曜って来るの早いんだろ😇
- `sns-020` tokens: gold=['映画', '『', '夜明けの列車', '』', '、', '泣きすぎて', '目', 'が', '腫れた', '。'] sys=['映画', '『', '夜明', 'け', 'の', '列車', '』、', '泣きすぎて', '目', 'が', '腫れた', '。'] 
- `sns-020` sentiment: gold=positive sys=None 映画『夜明けの列車』、泣きすぎて目が腫れた。
- `sns-020` emotion: gold=['moved'] sys=None 映画『夜明けの列車』、泣きすぎて目が腫れた。
- `sns-021` sentiment: gold=positive sys=None 今日はぽかぽか陽気で散歩日和🌸
- `sns-021` emotion: gold=['joy'] sys=None 今日はぽかぽか陽気で散歩日和🌸
- `sns-022` sentiment: gold=negative sys=None 楽しみにしてたのに雨で中止とか、ほんと最悪。
- `sns-022` emotion: gold=['sadness'] sys=anger 楽しみにしてたのに雨で中止とか、ほんと最悪。
- `sns-024` sentiment: gold=positive sys=None マルコ堂の新作プリン、350円でこの味はすごい。
- `sns-025` emotion: gold=['anxiety'] sys=sadness 嬉しくないと言えば嘘になるけど、素直に喜べない。
- `sns-029` sentiment: gold=negative sys=None 3日連続で残業とかブラックすぎん？
- `sns-029` emotion: gold=['irritation'] sys=None 3日連続で残業とかブラックすぎん？
- `sns-030` sentiment: gold=positive sys=None この写真、加工なしでこれ？信じられない😳
- `sns-030` emotion: gold=['surprise'] sys=exaggeration この写真、加工なしでこれ？信じられない😳
- `sns-031` emotion: gold=['surprise'] sys=None ちょっと待って、これ2019年の投稿じゃん。
- `sns-033` sentiment: gold=positive sys=None 全然期待してなかったけど、この漫画めっちゃ面白い！
- `sns-033` emotion: gold=['joy', 'surprise'] sys=exaggeration 全然期待してなかったけど、この漫画めっちゃ面白い！
- `sns-034` sentiment: gold=negative sys=None 値上げばっかりで、もう外食できないよ…
- `sns-034` emotion: gold=['sadness'] sys=None 値上げばっかりで、もう外食できないよ…
- `sns-035` sentiment: gold=positive sys=None 佐藤先生の講演、聞けて本当によかった。
- `sns-036` sentiment: gold=positive sys=None ワンワン吠えてる犬、めっちゃ可愛い🐶
- `sns-036` emotion: gold=['joy'] sys=exaggeration ワンワン吠えてる犬、めっちゃ可愛い🐶
- `sns-039` emotion: gold=['anxiety'] sys=irritation なんか今日はモヤモヤする。理由はわからない。
- `sns-040` canary: gold=None sys=moved 「感動」って名前のパン屋、駅前にできてた。
- `sns-041` sentiment: gold=None sys=positive 来週の花火大会、雨降らないといいな🎆
- `sns-041` emotion: gold=['anticipation', 'anxiety'] sys=None 来週の花火大会、雨降らないといいな🎆
- `sns-042` sentiment: gold=negative sys=None ぶっちゃけ値段の割に量が少なすぎ。
- `sns-042` emotion: gold=['irritation'] sys=None ぶっちゃけ値段の割に量が少なすぎ。
- `sns-043` sentiment: gold=positive sys=None 母の手作り弁当、毎日ありがたい。
- `sns-044` sentiment: gold=positive sys=None 京都の紅葉、写真じゃ伝わらない美しさだった。
- `sns-044` emotion: gold=['admiration'] sys=None 京都の紅葉、写真じゃ伝わらない美しさだった。
- `sns-045` sentiment: gold=positive sys=None え、待って、無理、可愛すぎる🫠
- `sns-045` emotion: gold=['admiration'] sys=refusal え、待って、無理、可愛すぎる🫠
- `sns-046` target: gold=['店長'] sys=['口', '面倒見'] バイト先の店長、口は悪いけど面倒見はいい。
- `sns-046` emotion: gold=['trust'] sys=None バイト先の店長、口は悪いけど面倒見はいい。
- `sns-047` sentiment: gold=negative sys=None リプ欄が荒れてて見るのがしんどい。
- `sns-047` emotion: gold=['disgust'] sys=sadness リプ欄が荒れてて見るのがしんどい。
- `sns-049` sentiment: gold=negative sys=None ぐっすり寝たのに、まだだるい。
- `sns-050` sentiment: gold=positive sys=None 2万円のイヤホン、音は最高だけど耳が痛くなる。
- `sns-050` emotion: gold=['irritation'] sys=joy 2万円のイヤホン、音は最高だけど耳が痛くなる。
- `sns-051` sentiment: gold=positive sys=None ねこがすやすや寝てる。平和。
- `sns-053` sentiment: gold=negative sys=None 昨日のドラマの最終回、納得いかない。
- `sns-053` emotion: gold=['irritation'] sys=None 昨日のドラマの最終回、納得いかない。
- `sns-054` emotion: gold=['anxiety'] sys=exaggeration やばい、財布落とした。誰か見てない？
- `sns-055` sentiment: gold=positive sys=None 新しいバイトの先輩が優しくて安心した。
- `sns-055` emotion: gold=['trust'] sys=agreement 新しいバイトの先輩が優しくて安心した。
- `sns-056` sentiment: gold=negative sys=None 通知がピロピロうるさすぎてミュートした。
- `sns-056` emotion: gold=['irritation'] sys=None 通知がピロピロうるさすぎてミュートした。
- `sns-057` sentiment: gold=positive sys=None ここのタピオカ、正直ブームの時より美味しくなってる。
- `sns-058` sentiment: gold=negative sys=None 今年の夏は暑すぎて外出する気にならない。
- `sns-058` emotion: gold=['irritation'] sys=None 今年の夏は暑すぎて外出する気にならない。
- `business-001` tokens: gold=['お世話', 'に', 'なっております', '。', '株式会社山田商事', 'の', '鈴木', 'です', '。'] sys=['お', '世話', 'になっております', '。', '株式会社山田商事', 'の', '鈴木', 'です', '。'] 
- `business-003` tokens: gold=['来週', 'の', '定例会議', 'は', '水曜', '10', '時', 'に', '変更いたします', '。'] sys=['来週', 'の', '定例会議', 'は', '水曜', '10', '時', 'に', '変更いた', 'します', '。'] 
- `business-004` tokens: gold=['貴社', 'の', 'ご提案', '、', '大変', '魅力的', 'に', '感じております', '。'] sys=['貴社', 'のご', '提案', '、', '大変魅力的', 'に', '感じております', '。'] 
- `business-004` sentiment: gold=positive sys=None 貴社のご提案、大変魅力的に感じております。
- `business-004` emotion: gold=['admiration'] sys=None 貴社のご提案、大変魅力的に感じております。
- `business-005` tokens: gold=['恐れ入ります', 'が', '、', '見積書', 'を', '再送いただけますでしょうか', '。'] sys=['恐れ入ります', 'が', '、', '見積書', 'を', '再送いただけますで', 'しょう', 'か', '。'] 
- `business-006` sentiment: gold=negative sys=None 納期が遅れているのに連絡がないのは困ります。
- `business-006` emotion: gold=['irritation'] sys=None 納期が遅れているのに連絡がないのは困ります。
- `business-008` tokens: gold=['田中', '部長', 'は', '今回', 'の', '結果', 'に', '大変', '満足されていました', '。'] sys=['田中部長', 'は', '今回', 'の', '結果', 'に', '大変満足', 'されていました', '。'] 
- `business-008` sentiment: gold=positive sys=None 田中部長は今回の結果に大変満足されていました。
- `business-009` tokens: gold=['単価', '5,000', '円', 'は', '予算', 'を', '大きく', '超えており', '、', '再検討', 'を', 'お願いします', '。'] sys=['単価', '5', ',', '000', '円', 'は', '予算', 'を', '大きく', '超えて', 'おり', '、', '再検討', 'をお', '願いします', '。'] 
- `business-009` sentiment: gold=negative sys=None 単価5,000円は予算を大きく超えており、再検討をお願いします。
- `business-010` tokens: gold=['会議室', 'の', '空調', 'が', 'ガンガン', '効きすぎて', '寒い', 'です', '。'] sys=['会議室', 'の', '空調', 'が', 'ガンガン', '効きすぎて', '寒いです', '。'] 
- `business-010` sentiment: gold=negative sys=None 会議室の空調がガンガン効きすぎて寒いです。
- `business-010` emotion: gold=['irritation'] sys=None 会議室の空調がガンガン効きすぎて寒いです。
- `business-011` tokens: gold=['新サービス', '「', 'Kanso', '」', 'は', '6月1日', 'より', '提供', '開始いたします', '。'] sys=['新', 'サービス', '「', 'Kanso', '」', 'は', '6', '月', '1', '日', 'より', '提供開始', 'いたします', '。'] 
- `business-012` emotion: gold=['trust'] sys=None 御社の対応は迅速で、大変助かりました。
- `business-013` tokens: gold=['先日', 'の', '説明会', 'に', 'は', '約', '200', '名', 'の', '方', 'に', 'ご参加いただきました', '。'] sys=['先日', 'の', '説明会', 'には', '約', '200', '名', 'の', '方', 'にご', '参加いただきました', '。'] 
- `business-014` tokens: gold=['品質', 'に', '問題', 'は', 'ない', 'ものの', '、', 'コスト面', 'で', '採用', 'は', '見送ります', '。'] sys=['品質', 'に', '問題', 'は', 'ない', 'もの', 'の', '、', 'コスト', '面', 'で', '採用', 'は', '見送ります', '。'] 
- `business-014` sentiment: gold=positive sys=None 品質に問題はないものの、コスト面で採用は見送ります。
- `business-014` emotion: gold=['refusal'] sys=None 品質に問題はないものの、コスト面で採用は見送ります。
- `business-016` tokens: gold=['今期', 'の', '目標', '未達', 'は', '非常に', '残念', 'です', 'が', '、', '原因', 'は', '明確', 'です', '。'] sys=['今期', 'の', '目標未達', 'は', '非常', 'に', '残念', 'です', 'が', '、', '原因', 'は', '明確', 'です', '。'] 
- `business-016` sentiment: gold=negative sys=None 今期の目標未達は非常に残念ですが、原因は明確です。
- `business-017` tokens: gold=['弊社', 'は', '2026年4月', 'に', '大阪支社', 'を', '開設いたしました', '。'] sys=['弊社', 'は', '2026', '年', '4', '月', 'に', '大阪支社', 'を', '開設いた', 'しました', '。'] 
- `business-018` tokens: gold=['ご返信', 'が', '遅くなり', '、', '大変', '申し訳ございません', '。'] sys=['ご', '返信', 'が', '遅く', 'なり', '、', '大変', '申し訳ございません', '。'] 
- `business-019` tokens: gold=['「', '感動', '」', 'は', '当社', 'の', '新型', '加湿器', 'の', 'ブランド名', 'です', '。'] sys=['「', '感動', '」', 'は', '当社', 'の', '新型加湿器', 'の', 'ブランド', '名', 'です', '。'] 
- `business-019` canary: gold=None sys=moved 「感動」は当社の新型加湿器のブランド名です。
- `business-022` sentiment: gold=negative sys=None 正直なところ、今回の提案には期待しておりません。
- `business-023` sentiment: gold=positive sys=None 山本様のご尽力には深く感謝しております。
- `business-023` emotion: gold=['moved'] sys=None 山本様のご尽力には深く感謝しております。
- `business-027` sentiment: gold=negative sys=None 会場の音響が悪く、後方の席では聞き取れませんでした。
- `business-027` emotion: gold=['irritation'] sys=None 会場の音響が悪く、後方の席では聞き取れませんでした。
- `business-030` sentiment: gold=positive sys=None 若手社員の成長ぶりには目を見張るものがあります。
- `business-030` emotion: gold=['admiration'] sys=None 若手社員の成長ぶりには目を見張るものがあります。
- `business-031` sentiment: gold=negative sys=None この価格では利益が出ないため、契約は見送らせていただきます。
- `business-031` emotion: gold=['refusal'] sys=None この価格では利益が出ないため、契約は見送らせていただきます。
- `business-033` emotion: gold=['admiration'] sys=None 御社の新オフィス、とても素敵ですね。
- `business-036` sentiment: gold=positive sys=None 前回の打ち合わせでは有意義なご意見を多数いただき、感謝申し上げます。
- `business-037` sentiment: gold=positive sys=None 決して安くはありませんが、投資に見合う効果が期待できます。
- `business-038` sentiment: gold=negative sys=None 御社サーバーの応答が遅く、業務に支障が出ております。
- `business-038` emotion: gold=['irritation'] sys=None 御社サーバーの応答が遅く、業務に支障が出ております。
- `business-040` sentiment: gold=negative sys=None 上司はこの企画にまったく乗り気ではないようです。
- `business-040` emotion: gold=['refusal'] sys=None 上司はこの企画にまったく乗り気ではないようです。
- `business-042` emotion: gold=['anticipation'] sys=joy 今回のプロジェクトは、社員一同わくわくしながら取り組んでおります。
- `business-046` sentiment: gold=negative sys=None 正直、この見積もりには納得しかねます。
- `business-046` emotion: gold=['refusal'] sys=admiration 正直、この見積もりには納得しかねます。
- `business-048` sentiment: gold=positive sys=None 新人の高橋さんは飲み込みが早く、頼もしい限りです。
- `business-048` emotion: gold=['trust'] sys=admiration 新人の高橋さんは飲み込みが早く、頼もしい限りです。
- `business-051` sentiment: gold=positive sys=None 御社の技術力は業界でも屈指だと認識しております。
- `business-051` emotion: gold=['admiration'] sys=None 御社の技術力は業界でも屈指だと認識しております。
- `business-052` sentiment: gold=negative sys=None 現状のままでは来年度の黒字化は難しいと考えます。
- `business-054` canary: gold=None sys=anger 「怒り」は弊社ゲーム部門の新作タイトルです。
- `business-056` sentiment: gold=positive sys=None 新製品の受注が好調で、生産が追いついておりません。
- `business-057` sentiment: gold=negative sys=None 部長は取引先の対応に激怒していました。
- `business-060` canary: gold=None sys=agreement 「安心」という名の保険商品を来月発売します。
- `tech-001` tokens: gold=['Python3.12', 'で', 'asyncio', 'の', '挙動', 'が', '変わった', 'らしい', '。'] sys=['Python', '3', '.', '12', 'で', 'asyncio', 'の', '挙動', 'が', '変わったらしい', '。'] 
- `tech-002` tokens: gold=['この', 'ライブラリ', '、', 'ドキュメント', 'が', '少なすぎて', '使いにくい', '。'] sys=['この', 'ライブラリ', '、', 'ドキュメント', 'が', '少なす', 'ぎて', '使いにく', 'い', '。'] 
- `tech-002` target: gold=['ライブラリ'] sys=['ドキュメント'] このライブラリ、ドキュメントが少なすぎて使いにくい。
- `tech-002` emotion: gold=['irritation'] sys=None このライブラリ、ドキュメントが少なすぎて使いにくい。
- `tech-004` tokens: gold=['新しい', 'GPU', 'の', 'ベンチマーク', '、', '前世代', 'の', '1.8', '倍', 'で', '驚いた', '。'] sys=['新しい', 'GPU', 'の', 'ベンチマーク', '、', '前世代', 'の', '1', '.', '8', '倍', 'で', '驚いた', '。'] 
- `tech-004` sentiment: gold=positive sys=None 新しいGPUのベンチマーク、前世代の1.8倍で驚いた。
- `tech-004` emotion: gold=['surprise'] sys=exaggeration 新しいGPUのベンチマーク、前世代の1.8倍で驚いた。
- `tech-007` tokens: gold=['TypeScript', 'の', '型エラー', 'が', '100', '件', '以上', '出て', '泣きそう', '。'] sys=['TypeScript', 'の', '型', 'エラー', 'が', '100', '件以上出', 'て', '泣きそう', '。'] 
- `tech-008` tokens: gold=['正直', '、', 'この', 'フレームワーク', 'は', '学習コスト', 'の', '割', 'に', 'メリット', 'が', '薄い', '。'] sys=['正直', '、', 'この', 'フレームワーク', 'は', '学習', 'コスト', 'の', '割', 'に', 'メリット', 'が', '薄い', '。'] 
- `tech-008` sentiment: gold=negative sys=None 正直、このフレームワークは学習コストの割にメリットが薄い。
- `tech-009` tokens: gold=['AWS', 'の', '請求', 'が', '先月', 'より', '3万', '円', 'も', '増えていて', '焦った', '。'] sys=['AWS', 'の', '請求', 'が', '先月', 'より', '3', '万円', 'も', '増えていて', '焦った', '。'] 
- `tech-009` sentiment: gold=negative sys=None AWSの請求が先月より3万円も増えていて焦った。
- `tech-011` tokens: gold=['Rust', 'の', 'コンパイラ', '、', '厳しい', 'けど', '的確', 'で', '信頼できる', '。'] sys=['Rust', 'の', 'コンパイラ', '、', '厳しい', 'けど', '的確', 'で', '信頼', 'できる', '。'] 
- `tech-011` sentiment: gold=positive sys=None Rustのコンパイラ、厳しいけど的確で信頼できる。
- `tech-011` emotion: gold=['trust'] sys=admiration Rustのコンパイラ、厳しいけど的確で信頼できる。
- `tech-012` tokens: gold=['この', 'API', 'の', 'レスポンス', '、', '200', 'ms', 'を', '切らないと', '要件', 'を', '満たせない', '。'] sys=['この', 'API', 'の', 'レスポンス', '、', '200', 'ms', 'を', '切らない', 'と', '要件', 'を', '満たせない', '。'] 
- `tech-013` sentiment: gold=negative sys=None 新しいエディタに乗り換えたけど、結局元に戻した。
- `tech-014` tokens: gold=['LLM', 'の', '出力', 'を', 'そのまま', '本番', 'に', '流す', 'の', 'は', '怖すぎる', '。'] sys=['LLM', 'の', '出力', 'をそのまま', '本番', 'に', '流す', 'の', 'は', '怖', 'すぎる', '。'] 
- `tech-014` sentiment: gold=negative sys=None LLMの出力をそのまま本番に流すのは怖すぎる。
- `tech-014` emotion: gold=['anxiety'] sys=exaggeration LLMの出力をそのまま本番に流すのは怖すぎる。
- `tech-015` tokens: gold=['バージョン', '2.3.0', 'で', 'この', 'バグ', 'は', '修正済み', 'です', '。'] sys=['バージョン', '2', '.', '3', '.', '0', 'で', 'この', 'バグ', 'は', '修正済', 'みです', '。'] 
- `tech-016` tokens: gold=['git', ' ', 'rebase', 'で', '履歴', 'が', '消えた', '。', 'バックアップ', '取ってなかった', '。'] sys=['git', 'rebase', 'で', '履歴', 'が', '消えた', '。', 'バックアップ', '取ってなかった', '。'] 
- `tech-016` emotion: gold=['sadness'] sys=None git rebaseで履歴が消えた。バックアップ取ってなかった。
- `tech-017` sentiment: gold=positive sys=None Kubernetesの設定、ヤマダさんが一晩で直してくれて神。
- `tech-018` tokens: gold=['ログ', 'が', 'だらだら', '流れて', '肝心', 'の', 'エラー', 'が', '見つからない', '。'] sys=['ログ', 'が', 'だらだら', '流れて', '肝心', 'の', 'エラー', 'が', '見つ', 'から', 'ない', '。'] 
- `tech-018` sentiment: gold=negative sys=None ログがだらだら流れて肝心のエラーが見つからない。
- `tech-018` emotion: gold=['irritation'] sys=None ログがだらだら流れて肝心のエラーが見つからない。
- `tech-020` tokens: gold=['「', '驚き', '」', 'は', 'この', 'ゲームエンジン', 'の', 'パーティクル機能', 'の', '名称', 'です', '。'] sys=['「', '驚き', '」', 'は', 'この', 'ゲームエンジン', 'の', 'パーティクル', '機能', 'の', '名称', 'です', '。'] 
- `tech-020` canary: gold=None sys=exaggeration 「驚き」はこのゲームエンジンのパーティクル機能の名称です。
- `tech-021` sentiment: gold=positive sys=None PostgreSQL 16にアップグレードしたら検索が2倍速くなった。
- `tech-021` emotion: gold=['joy'] sys=None PostgreSQL 16にアップグレードしたら検索が2倍速くなった。
- `tech-022` sentiment: gold=negative sys=None このコード、動くけど読めたもんじゃない。
- `tech-022` emotion: gold=['irritation'] sys=None このコード、動くけど読めたもんじゃない。
- `tech-023` sentiment: gold=negative sys=None CIが40分もかかるのはさすがに耐えられない。
- `tech-023` emotion: gold=['irritation'] sys=admiration CIが40分もかかるのはさすがに耐えられない。
- `tech-025` sentiment: gold=negative sys=None 認証周りの実装、正直不安しかない。
- `tech-025` emotion: gold=['anxiety'] sys=admiration 認証周りの実装、正直不安しかない。
- `tech-026` target: gold=['ミライAI'] sys=['値上げ'] ミライAIのAPI、値上げではなく値下げだったので助かる。
- `tech-026` emotion: gold=['joy'] sys=None ミライAIのAPI、値上げではなく値下げだったので助かる。
- `tech-029` sentiment: gold=negative sys=None このエラーメッセージ、何を直せばいいのか全然わからない。
- `tech-029` emotion: gold=['irritation'] sys=None このエラーメッセージ、何を直せばいいのか全然わからない。
- `tech-030` sentiment: gold=positive sys=None 正規表現が一発で通ったときの快感は格別。
- `tech-031` emotion: gold=['anxiety'] sys=None 遅延は解消されたが、根本原因はまだ不明だ。
- `tech-032` sentiment: gold=negative sys=None SDKのv3は破壊的変更が多くて移行が辛い。
- `tech-032` emotion: gold=['irritation'] sys=sadness SDKのv3は破壊的変更が多くて移行が辛い。
- `tech-033` sentiment: gold=negative sys=None ３２ＧＢのメモリを積んだのにまだスワップが発生する。
- `tech-033` emotion: gold=['irritation'] sys=None ３２ＧＢのメモリを積んだのにまだスワップが発生する。
- `tech-034` sentiment: gold=positive sys=None 障害の復旧、佐藤さんの判断が的確だった。
- `tech-034` emotion: gold=['admiration'] sys=None 障害の復旧、佐藤さんの判断が的確だった。
- `tech-035` emotion: gold=['anxiety'] sys=None 本番DBを間違えて消しかけて心臓が止まるかと思った。
- `tech-037` sentiment: gold=positive sys=None このアルゴリズム、計算量O(n²)なのは分かるけど実用上は十分速い。
- `tech-038` sentiment: gold=positive sys=None 新入社員がGitの使い方を1日で覚えて感心した。
- `tech-038` emotion: gold=['admiration'] sys=None 新入社員がGitの使い方を1日で覚えて感心した。
- `tech-039` sentiment: gold=negative sys=None マイクロサービス化、正直やらなきゃよかった。
- `tech-039` emotion: gold=['sadness'] sys=joy マイクロサービス化、正直やらなきゃよかった。
- `tech-041` sentiment: gold=None sys=positive 質問です。Pythonで日本語の文字数を正確に数える方法はありますか？
- `tech-042` sentiment: gold=negative sys=None ライセンス費が年間120万円は中小企業には厳しい。
- `tech-044` sentiment: gold=positive sys=negative 自作のパーサー、遅いけど自分で書いたから愛着がある。
- `tech-044` emotion: gold=['joy'] sys=None 自作のパーサー、遅いけど自分で書いたから愛着がある。
- `tech-045` sentiment: gold=negative sys=None 通知が一晩中ピコピコ鳴り続けて眠れなかった。
- `tech-045` emotion: gold=['irritation'] sys=None 通知が一晩中ピコピコ鳴り続けて眠れなかった。
- `tech-046` sentiment: gold=negative sys=None 型推論が賢すぎて、逆に何が起きているのか追えない。
- `tech-046` emotion: gold=['irritation'] sys=None 型推論が賢すぎて、逆に何が起きているのか追えない。
- `tech-048` sentiment: gold=negative sys=None AIチャットに聞いたら堂々と間違ったコードを出してきて笑った。
- `tech-049` emotion: gold=['admiration'] sys=joy この設計、シンプルで美しい。文句のつけようがない。
- `tech-050` sentiment: gold=None sys=positive エラーが再現しないんですが、どう調べればいいですか？
- `tech-050` emotion: gold=['anxiety'] sys=None エラーが再現しないんですが、どう調べればいいですか？
- `tech-051` emotion: gold=['joy'] sys=None メモリ使用量を40％削減できて、チーム全員でガッツポーズした。
- `tech-054` sentiment: gold=negative sys=None 依存パッケージが300個超えてるの、さすがに多すぎでは？
