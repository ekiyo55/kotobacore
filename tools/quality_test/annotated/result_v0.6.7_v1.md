# Annotated eval — KotobaCore 0.6.7 (300 items)

| Tokenization (73 items) | P 0.8976 / R 0.904 / F1 0.9008 |
| entity_surface | P 0.9085 / R 0.8142 / F1 0.8588 |
| entity_typed | P 0.8902 / R 0.7978 / F1 0.8415 |
| Sentiment accuracy | 83.0% (n=300) |
| Emotion accuracy | 84.1% (n=182), canary FP 0.0% (n=22) |
| Intent accuracy | 70.0% (n=300) |
| Sentiment target accuracy | 56.7% (n=67) |
| Timing | mean 6.3 ms / p95 4.25 ms |

## Per genre

| genre | sentiment | emotion | intent |
|---|---|---|---|
| business | 86.7% | 95.7% | 83.3% |
| conversation | 75.0% | 87.8% | 56.7% |
| literary | 88.3% | 73.0% | 78.3% |
| sns | 80.0% | 76.1% | 63.3% |
| tech | 85.0% | 94.3% | 68.3% |

## Failures (162)

- `sns-002` sentiment: gold=negative sys=None 新しいiPhone買ったけど正直そこまで感動しない。
- `sns-005` tokens: gold=['隣', 'の', '猫', 'が', 'にゃーにゃー', '鳴いてる', '。'] sys=['隣', 'の', '猫', 'が', 'にゃーにゃー', '鳴い', 'てる', '。'] 
- `sns-006` tokens: gold=['渋谷', 'の', 'スクランブル交差点', '、', '人', '多すぎて', '疲れた', '😩'] sys=['渋谷', 'の', 'スクランブル', '交差点', '、', '人多すぎて', '疲れた', '😩'] 
- `sns-006` sentiment: gold=None sys=negative 渋谷のスクランブル交差点、人多すぎて疲れた😩
- `sns-007` sentiment: gold=negative sys=positive このカフェ、コーヒーは微妙だけどケーキは神。
- `sns-008` sentiment: gold=None sys=positive 誰か新宿でおすすめのラーメン屋教えて！
- `sns-010` tokens: gold=['3', '年', 'ぶり', 'に', '実家', '帰ったら', '犬', 'が', '覚えててくれて', '泣いた', '🥲'] sys=['3', '年ぶ', 'り', 'に', '実家帰', 'っ', 'たら', '犬', 'が', '覚えててくれて', '泣いた', '🥲'] 
- `sns-011` emotion: gold=['irritation'] sys=None 正直、今回のアップデートは改悪だと思う。
- `sns-013` tokens: gold=['田中', 'さん', 'の', '新曲', '、', '何回', '聴いても', '飽きない', '✨'] sys=['田中', 'さん', 'の', '新曲', '、', '何回', '聴いて', 'も', '飽きない', '✨'] 
- `sns-013` sentiment: gold=positive sys=None 田中さんの新曲、何回聴いても飽きない✨
- `sns-013` emotion: gold=['admiration'] sys=anticipation 田中さんの新曲、何回聴いても飽きない✨
- `sns-015` tokens: gold=['悪くない', 'ん', 'だ', 'けど', '、', 'リピート', 'は', 'しない', 'か', 'な', '。'] sys=['悪くない', 'んだ', 'けど', '、', 'リピート', 'はしないか', 'な', '。'] 
- `sns-015` sentiment: gold=negative sys=positive 悪くないんだけど、リピートはしないかな。
- `sns-017` emotion: gold=['sadness'] sys=admiration ぴえん🥺推しのグッズ売り切れてた…
- `sns-019` tokens: gold=['なんで', '月曜', 'って', '来る', 'の', '早い', 'ん', 'だろ', '😇'] sys=['なん', 'で', '月曜って', '来る', 'の', '早い', 'んだろ', '😇'] 
- `sns-019` sentiment: gold=None sys=positive なんで月曜って来るの早いんだろ😇
- `sns-019` emotion: gold=['irritation'] sys=exaggeration なんで月曜って来るの早いんだろ😇
- `sns-020` tokens: gold=['映画', '『', '夜明けの列車', '』', '、', '泣きすぎて', '目', 'が', '腫れた', '。'] sys=['映画', '『', '夜明', 'け', 'の', '列車', '』、', '泣きすぎ', 'て', '目が腫れた', '。'] 
- `sns-024` target: gold=['新作プリン'] sys=['味'] マルコ堂の新作プリン、350円でこの味はすごい。
- `sns-025` emotion: gold=['anxiety'] sys=sadness 嬉しくないと言えば嘘になるけど、素直に喜べない。
- `sns-029` emotion: gold=['irritation'] sys=None 3日連続で残業とかブラックすぎん？
- `sns-031` emotion: gold=['surprise'] sys=None ちょっと待って、これ2019年の投稿じゃん。
- `sns-034` target: gold=['値上げ'] sys=[] 値上げばっかりで、もう外食できないよ…
- `sns-035` target: gold=['講演'] sys=['本当'] 佐藤先生の講演、聞けて本当によかった。
- `sns-037` sentiment: gold=None sys=negative いいね押しすぎて指が疲れた笑
- `sns-039` sentiment: gold=None sys=negative なんか今日はモヤモヤする。理由はわからない。
- `sns-041` sentiment: gold=None sys=positive 来週の花火大会、雨降らないといいな🎆
- `sns-044` sentiment: gold=positive sys=None 京都の紅葉、写真じゃ伝わらない美しさだった。
- `sns-044` emotion: gold=['admiration'] sys=None 京都の紅葉、写真じゃ伝わらない美しさだった。
- `sns-045` emotion: gold=['admiration'] sys=refusal え、待って、無理、可愛すぎる🫠
- `sns-046` sentiment: gold=positive sys=negative バイト先の店長、口は悪いけど面倒見はいい。
- `sns-046` target: gold=['店長'] sys=['口'] バイト先の店長、口は悪いけど面倒見はいい。
- `sns-050` emotion: gold=['irritation'] sys=joy 2万円のイヤホン、音は最高だけど耳が痛くなる。
- `sns-057` target: gold=['タピオカ'] sys=['時'] ここのタピオカ、正直ブームの時より美味しくなってる。
- `sns-057` emotion: gold=['admiration'] sys=None ここのタピオカ、正直ブームの時より美味しくなってる。
- `business-001` tokens: gold=['お世話', 'に', 'なっております', '。', '株式会社山田商事', 'の', '鈴木', 'です', '。'] sys=['お', '世話', 'になっております', '。', '株式会社山田商事', 'の', '鈴木', 'です', '。'] 
- `business-003` tokens: gold=['来週', 'の', '定例会議', 'は', '水曜', '10', '時', 'に', '変更いたします', '。'] sys=['来週', 'の', '定例会議', 'は', '水曜', '10', '時', 'に', '変更いた', 'します', '。'] 
- `business-004` tokens: gold=['貴社', 'の', 'ご提案', '、', '大変', '魅力的', 'に', '感じております', '。'] sys=['貴社', 'のご', '提案', '、', '大変魅力的', 'に', '感じております', '。'] 
- `business-005` tokens: gold=['恐れ入ります', 'が', '、', '見積書', 'を', '再送いただけますでしょうか', '。'] sys=['恐れ入ります', 'が', '、', '見積書', 'を', '再送いただけますで', 'しょう', 'か', '。'] 
- `business-008` tokens: gold=['田中', '部長', 'は', '今回', 'の', '結果', 'に', '大変', '満足されていました', '。'] sys=['田中部長', 'は', '今回', 'の', '結果', 'に', '大変満足', 'されていました', '。'] 
- `business-008` target: gold=['結果'] sys=[] 田中部長は今回の結果に大変満足されていました。
- `business-009` tokens: gold=['単価', '5,000', '円', 'は', '予算', 'を', '大きく', '超えており', '、', '再検討', 'を', 'お願いします', '。'] sys=['単価', '5', ',', '000', '円', 'は', '予算', 'を', '大きく', '超えて', 'おり', '、', '再検討', 'をお', '願いします', '。'] 
- `business-009` sentiment: gold=negative sys=None 単価5,000円は予算を大きく超えており、再検討をお願いします。
- `business-011` tokens: gold=['新サービス', '「', 'Kanso', '」', 'は', '6月1日', 'より', '提供', '開始いたします', '。'] sys=['新', 'サービス', '「', 'Kanso', '」', 'は', '6', '月', '1', '日', 'より', '提供開始', 'いたします', '。'] 
- `business-013` tokens: gold=['先日', 'の', '説明会', 'に', 'は', '約', '200', '名', 'の', '方', 'に', 'ご参加いただきました', '。'] sys=['先日', 'の', '説明会', 'には', '約', '200', '名', 'の', '方', 'にご', '参加いただきました', '。'] 
- `business-014` tokens: gold=['品質', 'に', '問題', 'は', 'ない', 'ものの', '、', 'コスト面', 'で', '採用', 'は', '見送ります', '。'] sys=['品質', 'に', '問題', 'は', 'ない', 'もの', 'の', '、', 'コスト', '面', 'で', '採用', 'は', '見送ります', '。'] 
- `business-014` sentiment: gold=positive sys=None 品質に問題はないものの、コスト面で採用は見送ります。
- `business-016` tokens: gold=['今期', 'の', '目標', '未達', 'は', '非常に', '残念', 'です', 'が', '、', '原因', 'は', '明確', 'です', '。'] sys=['今期', 'の', '目標未達', 'は', '非常', 'に', '残念', 'です', 'が', '、', '原因', 'は', '明確', 'です', '。'] 
- `business-017` tokens: gold=['弊社', 'は', '2026年4月', 'に', '大阪支社', 'を', '開設いたしました', '。'] sys=['弊社', 'は', '2026', '年', '4', '月', 'に', '大阪支社', 'を', '開設いた', 'しました', '。'] 
- `business-018` tokens: gold=['ご返信', 'が', '遅くなり', '、', '大変', '申し訳ございません', '。'] sys=['ご', '返信', 'が', '遅く', 'なり', '、', '大変申し訳ございません', '。'] 
- `business-019` tokens: gold=['「', '感動', '」', 'は', '当社', 'の', '新型', '加湿器', 'の', 'ブランド名', 'です', '。'] sys=['「', '感動', '」', 'は', '当社', 'の', '新型加湿器', 'の', 'ブランド', '名', 'です', '。'] 
- `business-022` sentiment: gold=negative sys=None 正直なところ、今回の提案には期待しておりません。
- `business-023` sentiment: gold=positive sys=None 山本様のご尽力には深く感謝しております。
- `business-023` emotion: gold=['moved'] sys=None 山本様のご尽力には深く感謝しております。
- `business-027` sentiment: gold=negative sys=None 会場の音響が悪く、後方の席では聞き取れませんでした。
- `business-037` sentiment: gold=positive sys=None 決して安くはありませんが、投資に見合う効果が期待できます。
- `business-038` target: gold=['サーバー'] sys=['応答'] 御社サーバーの応答が遅く、業務に支障が出ております。
- `business-040` sentiment: gold=negative sys=None 上司はこの企画にまったく乗り気ではないようです。
- `business-043` sentiment: gold=None sys=positive 弊社の売上高は3年連続で過去最高を更新しました。
- `business-048` target: gold=['高橋さん'] sys=['飲み込み'] 新人の高橋さんは飲み込みが早く、頼もしい限りです。
- `business-056` target: gold=['新製品'] sys=['受注'] 新製品の受注が好調で、生産が追いついておりません。
- `tech-001` tokens: gold=['Python3.12', 'で', 'asyncio', 'の', '挙動', 'が', '変わった', 'らしい', '。'] sys=['Python', '3', '.', '12', 'で', 'asyncio', 'の', '挙動', 'が', '変わったらしい', '。'] 
- `tech-002` tokens: gold=['この', 'ライブラリ', '、', 'ドキュメント', 'が', '少なすぎて', '使いにくい', '。'] sys=['この', 'ライブラリ', '、', 'ドキュメント', 'が', '少なすぎ', 'て', '使いにくい', '。'] 
- `tech-002` target: gold=['ライブラリ'] sys=['ドキュメント'] このライブラリ、ドキュメントが少なすぎて使いにくい。
- `tech-004` tokens: gold=['新しい', 'GPU', 'の', 'ベンチマーク', '、', '前世代', 'の', '1.8', '倍', 'で', '驚いた', '。'] sys=['新しい', 'GPU', 'の', 'ベンチマーク', '、', '前世代', 'の', '1', '.', '8', '倍', 'で', '驚いた', '。'] 
- `tech-007` tokens: gold=['TypeScript', 'の', '型エラー', 'が', '100', '件', '以上', '出て', '泣きそう', '。'] sys=['TypeScript', 'の', '型', 'エラー', 'が', '100', '件以上出', 'て', '泣きそう', '。'] 
- `tech-008` tokens: gold=['正直', '、', 'この', 'フレームワーク', 'は', '学習コスト', 'の', '割', 'に', 'メリット', 'が', '薄い', '。'] sys=['正直', '、', 'この', 'フレームワーク', 'は', '学習', 'コスト', 'の', '割', 'に', 'メリットが薄い', '。'] 
- `tech-009` tokens: gold=['AWS', 'の', '請求', 'が', '先月', 'より', '3万', '円', 'も', '増えていて', '焦った', '。'] sys=['AWS', 'の', '請求', 'が', '先月', 'より', '3', '万円', 'も', '増えていて', '焦った', '。'] 
- `tech-012` tokens: gold=['この', 'API', 'の', 'レスポンス', '、', '200', 'ms', 'を', '切らないと', '要件', 'を', '満たせない', '。'] sys=['この', 'API', 'の', 'レスポンス', '、', '200', 'ms', 'を', '切らない', 'と', '要件', 'を', '満たせない', '。'] 
- `tech-013` sentiment: gold=negative sys=None 新しいエディタに乗り換えたけど、結局元に戻した。
- `tech-014` tokens: gold=['LLM', 'の', '出力', 'を', 'そのまま', '本番', 'に', '流す', 'の', 'は', '怖すぎる', '。'] sys=['LLM', 'の', '出力', 'をそのまま', '本番', 'に', '流す', 'の', 'は', '怖すぎる', '。'] 
- `tech-015` tokens: gold=['バージョン', '2.3.0', 'で', 'この', 'バグ', 'は', '修正済み', 'です', '。'] sys=['バージョン', '2', '.', '3', '.', '0', 'で', 'この', 'バグ', 'は', '修正済', 'みです', '。'] 
- `tech-016` tokens: gold=['git', 'rebase', 'で', '履歴が消えた', '。', 'バックアップ', '取ってなかった', '。'] sys=['git', 'rebase', 'で', '履歴が消えた', '。', 'バックアップ', '取ってなかった', '。'] 
- `tech-017` target: gold=['ヤマダさん'] sys=['一晩'] Kubernetesの設定、ヤマダさんが一晩で直してくれて神。
- `tech-018` target: gold=['ログ'] sys=['エラー'] ログがだらだら流れて肝心のエラーが見つからない。
- `tech-020` tokens: gold=['「', '驚き', '」', 'は', 'この', 'ゲームエンジン', 'の', 'パーティクル機能', 'の', '名称', 'です', '。'] sys=['「', '驚き', '」', 'は', 'この', 'ゲームエンジン', 'の', 'パーティクル', '機能', 'の', '名称', 'です', '。'] 
- `tech-021` target: gold=['PostgreSQL 16'] sys=['検索'] PostgreSQL 16にアップグレードしたら検索が2倍速くなった。
- `tech-023` target: gold=['CI'] sys=['40分'] CIが40分もかかるのはさすがに耐えられない。
- `tech-025` emotion: gold=['anxiety'] sys=admiration 認証周りの実装、正直不安しかない。
- `tech-026` target: gold=['ミライAI'] sys=['値上げ'] ミライAIのAPI、値上げではなく値下げだったので助かる。
- `tech-026` emotion: gold=['joy'] sys=trust ミライAIのAPI、値上げではなく値下げだったので助かる。
- `tech-029` sentiment: gold=negative sys=positive このエラーメッセージ、何を直せばいいのか全然わからない。
- `tech-029` target: gold=['エラーメッセージ'] sys=['何', '全然'] このエラーメッセージ、何を直せばいいのか全然わからない。
- `tech-032` sentiment: gold=None sys=negative SDKのv3は破壊的変更が多くて移行が辛い。
- `tech-033` sentiment: gold=negative sys=None ３２ＧＢのメモリを積んだのにまだスワップが発生する。
- `tech-034` target: gold=['佐藤さん'] sys=['判断'] 障害の復旧、佐藤さんの判断が的確だった。
- `tech-037` target: gold=['アルゴリズム'] sys=['実用上'] このアルゴリズム、計算量O(n²)なのは分かるけど実用上は十分速い。
- `tech-038` sentiment: gold=None sys=positive 新入社員がGitの使い方を1日で覚えて感心した。
- `tech-039` target: gold=['マイクロサービス化'] sys=['正直'] マイクロサービス化、正直やらなきゃよかった。
- `tech-041` sentiment: gold=None sys=positive 質問です。Pythonで日本語の文字数を正確に数える方法はありますか？
- `tech-042` sentiment: gold=negative sys=None ライセンス費が年間120万円は中小企業には厳しい。
- `tech-046` target: gold=['型推論'] sys=['何'] 型推論が賢すぎて、逆に何が起きているのか追えない。
- `tech-048` sentiment: gold=negative sys=None AIチャットに聞いたら堂々と間違ったコードを出してきて笑った。
- `tech-050` sentiment: gold=None sys=positive エラーが再現しないんですが、どう調べればいいですか？
- `tech-056` target: gold=['コードレビュー'] sys=['毎回'] 田村さんのコードレビューは厳しいけど、毎回学びがある。
- `literary-002` tokens: gold=['彼女', 'は', '嬉しくなかった', '。', 'ただ', '、', '静かに', '頷いた', '。'] sys=['彼女', 'は', '嬉しくなかった', '。', 'ただ', '、', '静', 'か', 'に', '頷いた', '。'] 
- `literary-003` tokens: gold=['春', 'の', '光', 'が', '、', '古い', '縁側', 'に', 'やわらかく', '落ちていた', '。'] sys=['春', 'の', '光', 'が', '、', '古い', '縁側', 'にやわらかく', '落ちていた', '。'] 
- `literary-003` sentiment: gold=None sys=negative 春の光が、古い縁側にやわらかく落ちていた。
- `literary-004` emotion: gold=['sadness'] sys=moved 田中は手紙を読み終えると、声を上げて泣いた。
- `literary-005` tokens: gold=['遠く', 'で', '犬', 'が', 'わんわん', 'と', '吠えている', '。', 'それ', 'だけ', 'の', '夜', 'だった', '。'] sys=['遠くで', '犬', 'が', 'わんわん', 'と', '吠えている', '。', 'それ', 'だけ', 'の', '夜だった', '。'] 
- `literary-006` tokens: gold=['少年', 'は', '、', '初めて', '見る', '雪', 'に', '目', 'を', '輝かせた', '。'] sys=['少年', 'は', '、', '初めて', '見る雪', 'に', '目を輝かせた', '。'] 
- `literary-007` tokens: gold=['悪くない', '人生', 'だった', '、', 'と', '老人', 'は', '呟いた', '。'] sys=['悪くない', '人生だった', '、', 'と', '老人', 'は', '呟いた', '。'] 
- `literary-007` target: gold=['人生'] sys=[] 悪くない人生だった、と老人は呟いた。
- `literary-008` tokens: gold=['昭和五十二年', 'の', '夏', '、', 'ぼくら', 'は', '川', 'で', '一日中', '泳いでいた', '。'] sys=['昭和五十二年', 'の', '夏', '、', 'ぼく', 'ら', 'は', '川', 'で', '一日', '中泳いでいた', '。'] 
- `literary-009` emotion: gold=['sadness'] sys=None 母の背中は、思っていたよりずっと小さかった。
- `literary-010` tokens: gold=['彼', 'は', '怒っていた', 'わけ', 'で', 'は', 'ない', '。', 'ただ', '、', '疲れていた', 'の', 'だ', '。'] sys=['彼', 'は', '怒っていたわけで', 'は', 'ない', '。', 'ただ', '、', '疲れていたのだ', '。'] 
- `literary-011` tokens: gold=['京都', 'の', '路地', 'に', '降る', 'しとしと', '雨', 'が', '、', '彼', 'を', '少し', 'だけ', '寂しくさせた', '。'] sys=['京都', 'の', '路地', 'に', '降る', 'しとしと', '雨', 'が', '、', '彼', 'を', '少し', 'だけ', '寂しく', 'させた', '。'] 
- `literary-012` tokens: gold=['『', '月影の庭', '』', 'を', '書き上げた', 'とき', '、', '彼女', 'は', '三十', '歳', 'に', 'なっていた', '。'] sys=['『', '月影', 'の', '庭', '』', 'を', '書き上げた', 'とき', '、', '彼女', 'は', '三十歳', 'に', 'なっていた', '。'] 
- `literary-013` emotion: gold=['moved'] sys=None 祖父の時計は、今も胸の奥でこちこちと鳴っている。
- `literary-014` tokens: gold=['彼女', 'の', '笑顔', 'を', '見た', '瞬間', '、', '胸', 'の', 'つかえ', 'が', 'すっと', '消えた', '。'] sys=['彼女', 'の', '笑顔', 'を', '見た瞬間', '、', '胸のつかえが', 'すっと消えた', '。'] 
- `literary-016` tokens: gold=['東京駅', 'の', '雑踏', 'の', '中', 'で', '、', '彼', 'は', 'ふと', '故郷', 'の', '匂い', 'を', '思い出した', '。'] sys=['東京駅', 'の', '雑踏', 'の', '中', 'で', '、', '彼', 'はふ', 'と', '故郷', 'の', '匂い', 'を', '思い出した', '。'] 
- `literary-016` emotion: gold=['moved'] sys=None 東京駅の雑踏の中で、彼はふと故郷の匂いを思い出した。
- `literary-017` tokens: gold=['それ', 'は', '、', 'たしかに', '美しい', '嘘', 'だった', '。'] sys=['それ', 'は', '、', 'たしかに', '美しい', '嘘だった', '。'] 
- `literary-017` target: gold=['嘘'] sys=[] それは、たしかに美しい嘘だった。
- `literary-018` sentiment: gold=None sys=positive 娘が生まれた日、男は初めて神に感謝した。
- `literary-018` emotion: gold=['moved'] sys=admiration 娘が生まれた日、男は初めて神に感謝した。
- `literary-019` tokens: gold=['「', 'もう', '二度と', '会わない', '」', 'と', '、', '彼女', 'は', '言った', '。'] sys=['「', 'もう', '二度と会わない', '」', 'と', '、', '彼女', 'は', '言った', '。'] 
- `literary-020` tokens: gold=['五月', 'の', '風', 'が', '、', 'カーテン', 'を', 'ふわり', 'と', '揺らした', '。'] sys=['五月', 'の', '風', 'が', '、', 'カーテン', 'をふわり', 'と', '揺らした', '。'] 
- `literary-023` sentiment: gold=positive sys=None 彼は約束を破らなかった。ただ一度も、だ。
- `literary-026` sentiment: gold=positive sys=None 彼女の声は震えていたが、瞳は少しも揺らがなかった。
- `literary-027` emotion: gold=['moved'] sys=None 父は何も言わず、ただ私の頭に手を置いた。
- `literary-031` emotion: gold=['sadness'] sys=joy 「ありがとう」と言えなかったことを、彼は今も悔やんでいる。
- `literary-032` sentiment: gold=None sys=positive 「もう少しだけ、ここにいてもいい？」と彼女は小さく言った。
- `literary-032` emotion: gold=['anxiety'] sys=None 「もう少しだけ、ここにいてもいい？」と彼女は小さく言った。
- `literary-038` sentiment: gold=negative sys=None 彼の作った料理は、正直に言えば、うまくはなかった。
- `literary-049` sentiment: gold=negative sys=None 新しい家は広くて明るかったが、どこか落ち着かなかった。
- `literary-051` emotion: gold=['sadness'] sys=None 「行くな」と言えば、彼は行かなかっただろう。
- `literary-058` emotion: gold=['admiration'] sys=None 祖母の作る味噌汁は、世界で一番おいしかった。
- `conversation-001` sentiment: gold=None sys=positive ねえ、今日の夕飯何がいい？
- `conversation-002` sentiment: gold=negative sys=None えー、またカレー？昨日も食べたじゃん。
- `conversation-003` tokens: gold=['別に', '怒ってない', 'よ', '。', 'ただ', 'ちょっと', '疲れてる', 'だけ', '。'] sys=['別', 'に', '怒ってない', 'よ', '。', 'ただ', 'ちょっと', '疲れてる', 'だけ', '。'] 
- `conversation-003` sentiment: gold=None sys=negative 別に怒ってないよ。ただちょっと疲れてるだけ。
- `conversation-004` emotion: gold=['sadness'] sys=admiration ごめん、明日の約束、やっぱり行けなくなった。
- `conversation-007` tokens: gold=['その', '話', '、', '前', 'に', 'も', '聞いた', 'けど', '、', '何回', '聞いても', '面白い', 'ね', '。'] sys=['その', '話', '、', '前', 'に', 'も', '聞いた', 'けど', '、', '何回', '聞いて', 'も', '面白い', 'ね', '。'] 
- `conversation-007` target: gold=['話'] sys=['何回'] その話、前にも聞いたけど、何回聞いても面白いね。
- `conversation-009` tokens: gold=['うーん', '、', '悪くはない', 'けど', '、', 'もう', '少し', '安い', 'と', '嬉しい', 'な', '。'] sys=['う', 'ー', 'ん', '、', '悪くはない', 'けど', '、', 'もう', '少し', '安い', 'と', '嬉しい', 'な', '。'] 
- `conversation-009` sentiment: gold=negative sys=positive うーん、悪くはないけど、もう少し安いと嬉しいな。
- `conversation-010` sentiment: gold=None sys=positive お母さん、田中くんの家に泊まってもいい？
- `conversation-014` tokens: gold=['先週末', '、', '家族', 'で', '軽井沢', 'に', '行ってきた', 'ん', 'だ', '。'] sys=['先週末', '、', '家族', 'で', '軽井沢', 'に', '行ってきたんだ', '。'] 
- `conversation-015` tokens: gold=['いや', '、', 'それ', 'は', '違う', 'と', '思う', 'な', '。'] sys=['い', 'や', '、', 'それ', 'は', '違うと思う', 'な', '。'] 
- `conversation-015` sentiment: gold=negative sys=None いや、それは違うと思うな。
- `conversation-017` tokens: gold=['猫', 'が', 'ゴロゴロ', '喉', '鳴らしてる', '。'] sys=['猫', 'が', 'ゴロゴロ', '喉鳴らしてる', '。'] 
- `conversation-018` tokens: gold=['来月', 'の', '家賃', '、', 'また', '5000', '円', '上がる', 'ん', 'だって', '。', 'ありえない', '。'] sys=['来月', 'の', '家賃', '、', 'また', '5000', '円上', 'がるんだ', 'って', '。', 'ありえない', '。'] 
- `conversation-018` target: gold=['家賃'] sys=['円上'] 来月の家賃、また5000円上がるんだって。ありえない。
- `conversation-020` tokens: gold=['山田', 'さん', 'って', '、', 'いつも', '笑顔', 'で', '感じ', 'いい', 'よ', 'ね', '。'] sys=['山田さんって', '、', 'いつも', '笑顔', 'で', '感じいい', 'よ', 'ね', '。'] 
- `conversation-020` target: gold=['山田さん'] sys=['感じ'] 山田さんって、いつも笑顔で感じいいよね。
- `conversation-022` sentiment: gold=None sys=positive えっと、駅までどう行けばいいですか？
- `conversation-025` emotion: gold=['joy'] sys=sadness 別に嬉しくないし。……まあ、ちょっとは嬉しいけど。
- `conversation-026` sentiment: gold=None sys=positive 大丈夫だよ、心配しないで。私がついてる。
- `conversation-030` sentiment: gold=negative sys=None 何でいつも私ばっかり片付けなきゃいけないの？
- `conversation-031` sentiment: gold=positive sys=None この前のパン屋、また行きたいね。
- `conversation-037` emotion: gold=['surprise'] sys=None それ、３０００円もしたの？高くない？
- `conversation-038` sentiment: gold=None sys=positive 全然大丈夫。気にしないで。
- `conversation-042` sentiment: gold=negative sys=positive 佐藤さん、また遅刻？いい加減にしてほしい。
- `conversation-042` target: gold=['佐藤さん'] sys=['遅刻'] 佐藤さん、また遅刻？いい加減にしてほしい。
- `conversation-043` target: gold=['アプリ'] sys=['無料'] このアプリ、無料なのにすごく便利だね。
- `conversation-049` sentiment: gold=None sys=positive なんか今日、顔色悪くない？大丈夫？
- `conversation-052` sentiment: gold=negative sys=None 弟が「宿題やった」って言うけど、絶対やってない。
- `conversation-055` target: gold=['田舎の夜'] sys=['虫'] 田舎の夜って、虫がりんりん鳴いてて風情あるよね。
- `conversation-059` sentiment: gold=None sys=positive 明日、雨降らないといいね。運動会だし。
- `conversation-059` emotion: gold=['anxiety'] sys=anticipation 明日、雨降らないといいね。運動会だし。
- `conversation-060` emotion: gold=['anticipation'] sys=None よし、決めた。来年こそ海外行く。
