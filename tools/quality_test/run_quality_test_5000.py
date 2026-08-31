"""KotobaCore 例文品質テスト（v0.1.10〜 標準評価）。

13カテゴリ × 500例文 = 6500文をテンプレート生成し、Analyzer に通す。

計測:
  - 検出率   : 感情 / 意図 / チャンク / RAGキーワード が出力されたか
  - 正確度   : カテゴリの ground-truth（期待感情 / 極性 / 意図）と一致したか。
               expected_no_emotion カテゴリは「感情なし」が正解（誤検出の監視）
  - 処理時間 : analyze() 1文あたりの所要時間（平均 / 中央値 / p95 / p99 / 最大）

文生成は seed 固定で再現性あり。結果は JSON と Markdown に出力する。

⚠️ カテゴリ凍結ルール: 文生成は CATEGORIES の順に単一乱数列を消費するため、
既存カテゴリのテンプレート・プールを1語でも変更したり途中に挿入したりすると
以降の全例文が変わり、歴代バージョンとの数値比較が壊れる。**変更は末尾への
カテゴリ追加のみ可**。歴代比較 (v0.1.10〜v0.2.6 の「5000例文」数値) は
レガシー10カテゴリのサブセット集計 (summary_legacy10) で行う。

Usage:
    python tools/quality_test/run_quality_test_5000.py --json out.json --md out.md
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

SEED = 20260518
PER_CATEGORY = 500


# ---------------------------------------------------------------------------
# カテゴリ定義
# ---------------------------------------------------------------------------
@dataclass
class Category:
    name: str
    templates: list[str]
    pools: dict[str, list[str]]
    # ground-truth（None の軸は正確度スコア対象外）
    expected_polarity: str | None = None
    acceptable_emotions: set[str] | None = None
    expected_intents: set[str] | None = None
    # True: 「感情なし」が正解 — 感情が出たら誤検出として正確度を減点
    expected_no_emotion: bool = False


CATEGORIES: list[Category] = [
    # ───────────────────────────────────────────── 1. 喜び・ポジティブ
    Category(
        name="喜び・ポジティブ",
        expected_polarity="positive",
        acceptable_emotions={"joy", "admiration", "moved", "agreement"},
        templates=[
            "{topic}が{good}て{joy}。",
            "{person}に{helped}て{joy}。",
            "{event}、{joy}。",
            "ずっと{wanted}たことが叶って{joy}。",
            "今日は{topic}が{good}、{joynoun}。",
            "{topic}を{achieved}、{joy}。",
            "{person}と{event2}、{joy}。",
        ],
        pools={
            "topic": ["プロジェクト", "試験", "発表", "新しい仕事", "趣味のイラスト",
                      "家庭菜園", "資格の勉強", "チームの企画", "引っ越し", "部活の大会",
                      "料理", "朝のジョギング", "副業", "ダイエット", "新居探し",
                      "旅行の計画", "卒業制作", "商談", "面接", "研究発表"],
            "good": ["うまくいっ", "成功し", "無事に終わっ", "評価され", "形になっ",
                     "認められ", "実を結ん", "軌道に乗っ", "高く評価され"],
            "joy": ["本当に嬉しい", "最高の気分だ", "とても幸せだ", "感動した",
                    "誇らしい気持ちだ", "楽しくてたまらない", "心から満足している",
                    "胸がいっぱいになった", "やったと叫びたくなった"],
            "joynoun": ["達成感でいっぱいだ", "幸福感に包まれた", "充実感があった",
                        "喜びがこみ上げた", "報われた気がした"],
            "person": ["先輩", "同僚", "友人", "家族", "上司", "チームのみんな",
                       "恩師", "近所の人", "後輩", "パートナー"],
            "helped": ["助けてもらっ", "応援してもらっ", "支えてもらっ",
                       "励ましてもらっ", "褒めてもらっ", "認めてもらっ"],
            "event": ["念願のライブに行けて", "久しぶりに旧友と再会できて",
                      "欲しかった物が手に入って", "子どもの成長を見られて",
                      "目標を達成できて", "良い知らせが届いて", "夢が一つ実現して"],
            "event2": ["楽しい時間を過ごせて", "一緒に成功を祝えて",
                       "美味しい食事を囲めて", "笑い合えて", "旅行に行けて"],
            "wanted": ["行きたかっ", "やりたかっ", "挑戦したかっ", "会いたかっ",
                       "学びたかっ"],
            "achieved": ["やり遂げて", "クリアして", "完成させて", "乗り越えて",
                         "最後までやりきって"],
        },
    ),
    # ───────────────────────────────────────────── 2. 怒り・不満
    Category(
        name="怒り・不満",
        expected_polarity="negative",
        acceptable_emotions={"anger", "irritation", "refusal"},
        templates=[
            "{cause}て本当に{angry}。",
            "{target}の{badpoint}に{angry}。",
            "また{cause}、{angry}。",
            "{cause}て{angry2}。",
            "{target}が{badaction}て、{angry}。",
            "なんで{cause}んだ、{angry}。",
        ],
        pools={
            "cause": ["約束を破られ", "順番を抜かされ", "理由もなく残業を強制され",
                      "何度も同じミスを繰り返され", "話を最後まで聞いてもらえなく",
                      "勝手に予定を変更され", "連絡が来なく", "雑な対応をされ",
                      "値上げを一方的に通告され", "成果を横取りされ"],
            "angry": ["腹が立つ", "ムカつく", "許せない", "本当に頭にきた",
                      "怒りがおさまらない", "理不尽だと感じる", "イライラする"],
            "angry2": ["うんざりしている", "我慢の限界だ", "不満でいっぱいだ",
                       "ストレスがたまる一方だ"],
            "target": ["あの店員", "担当者", "上司", "隣の人", "取引先",
                       "サポート窓口", "同僚", "運営", "管理会社"],
            "badpoint": ["対応の悪さ", "言い方", "態度", "不誠実さ",
                         "ルーズな仕事ぶり", "身勝手さ", "説明不足"],
            "badaction": ["約束を破っ", "嘘をつい", "責任を押し付け",
                          "手を抜い", "後回しにし", "言い訳ばかりし"],
        },
    ),
    # ───────────────────────────────────────────── 3. 悲しみ・憂鬱
    Category(
        name="悲しみ・憂鬱",
        expected_polarity="negative",
        acceptable_emotions={"sadness", "moved"},
        templates=[
            "{cause}て{sad}。",
            "{cause}、{sad2}。",
            "{loss}を失って{sad}。",
            "{cause}てから{sad2}。",
            "どうしても{cause}て{sad}。",
            "{loss}のことを思い出すと{sad}。",
        ],
        pools={
            "cause": ["大切な人と別れ", "ペットが亡くなっ", "努力が報われなく",
                      "期待を裏切られ", "孤独を感じ", "夢をあきらめ",
                      "誰にも理解されなく", "失敗を引きずっ", "悪い知らせを聞い",
                      "別れの言葉を告げられ", "一人きりで過ごし", "前向きになれなく",
                      "涙をこらえきれなく", "居場所をなくし"],
            "sad": ["とても悲しい", "胸が痛い", "涙が止まらない", "切なくなる",
                    "心が沈む", "つらくてたまらない", "悲しくて言葉が出ない",
                    "もう笑えない"],
            "sad2": ["気分が落ち込んでいる", "何も手につかない", "ふさぎ込んでいる",
                     "虚無感に襲われている", "毎日が憂鬱だ", "立ち直れずにいる",
                     "気力が湧かない"],
            "loss": ["大切な思い出", "幼い頃の友人", "祖父母", "長年の習慣",
                     "かけがえのない時間", "古い写真", "実家",
                     "信じていた友情", "戻らない日々", "あの頃の面影"],
        },
    ),
    # ───────────────────────────────────────────── 4. 不安・恐れ
    Category(
        name="不安・恐れ",
        expected_polarity="negative",
        acceptable_emotions={"anxiety"},
        templates=[
            "{cause}て{anx}。",
            "{cause}、{anx2}。",
            "もし{risk}たらと思うと{anx}。",
            "{cause}てから{anx2}。",
            "{event}が近づくにつれて{anx}。",
            "{risk}ないか{anx}。",
        ],
        pools={
            "cause": ["将来のことを考え", "結果が分からなく", "健康診断の結果を待っ",
                      "知らない場所に行くと決まっ", "大事な決断を迫られ",
                      "周りの反応が読めなく", "うまくいく自信がなく",
                      "先行きが見えなく", "準備が間に合うか分からなく",
                      "責任の重さを感じ", "うまく説明できる気がしなく",
                      "予想外のことが起き"],
            "anx": ["不安でたまらない", "とても心配だ", "落ち着かない",
                    "胸騒ぎがする", "怖くて仕方がない", "焦りを感じる",
                    "緊張している", "気が気でない"],
            "anx2": ["気持ちが落ち着かない", "夜も眠れない", "そわそわしている",
                     "緊張で手が震える", "焦りでいっぱいだ",
                     "ずっとびくびくしている", "胸騒ぎがおさまらない"],
            "risk": ["失敗し", "間違え", "嫌われ", "取り残され", "体調を崩し",
                     "見捨てられ", "うまく話せ", "迷惑をかけ", "期待に応えられ",
                     "間に合わ", "怒られ"],
            "event": ["試験", "発表", "面接", "手術", "引っ越し", "初出社",
                      "大事な会議", "受験", "本番", "締め切り"],
        },
    ),
    # ───────────────────────────────────────────── 5. SNS・スラング
    Category(
        name="SNS・スラング",
        expected_polarity=None,
        acceptable_emotions=None,  # 多義・混合のため検出率のみ計測
        templates=[
            "{thing}まじで{slang}",
            "{thing}{slang}、{slang2}",
            "{thing}が{slang}んだけど",
            "{event}て{slang}",
            "{thing}{slang2}わかる人いる？",
            "今日の{thing}、{slang}",
        ],
        pools={
            "thing": ["この曲", "推しのライブ", "新作アニメ", "今日のごはん",
                      "あのドラマ", "新しいゲーム", "先輩の対応", "このカフェ",
                      "今朝のニュース", "友達の話", "ペットの動画", "夜景"],
            "slang": ["尊い", "えぐい", "やばい", "神", "しんどい", "エモい",
                      "ワロタ", "草", "最高すぎ", "無理", "沼", "尊すぎ"],
            "slang2": ["しぬw", "ぴえん", "それな", "わかりみが深い", "語彙力消えた",
                       "優勝", "天才すぎる", "解釈一致"],
            "event": ["まさかの展開きて", "推しが供給くれ", "神回き", "バズっ",
                      "コラボ発表され", "限定グッズ買え"],
        },
    ),
    # ───────────────────────────────────────────── 6. ビジネス・業務
    Category(
        name="ビジネス・業務",
        expected_polarity=None,
        acceptable_emotions=None,  # 中立文・感情正確度は対象外
        templates=[
            "{subject}の{doc}を{action}してください。",
            "{date}までに{subject}の{doc}を{action}します。",
            "{subject}について{meeting}を実施します。",
            "{doc}の{action}が完了しました。",
            "{subject}の進捗を{report}します。",
            "{meeting}の議事録を{action}しました。",
        ],
        pools={
            "subject": ["第二四半期予算", "新製品プロモーション", "システム移行",
                        "採用計画", "顧客満足度調査", "在庫管理", "販売戦略",
                        "人事評価", "コスト削減施策", "業務フロー改善"],
            "doc": ["資料", "report", "見積書", "提案書", "計画書", "報告書",
                    "議事録", "仕様書", "スケジュール"],
            "action": ["共有", "確認", "提出", "更新", "レビュー", "承認", "修正"],
            "date": ["今週末", "月末", "明日", "来週火曜", "本日中", "次回会議まで"],
            "meeting": ["定例ミーティング", "キックオフ", "進捗会議",
                        "レビュー会", "打ち合わせ"],
            "report": ["報告", "共有", "更新"],
        },
    ),
    # ───────────────────────────────────────────── 7. 技術・AI
    Category(
        name="技術・AI",
        expected_polarity=None,
        acceptable_emotions=None,
        templates=[
            "{tech}を使って{task}を実装した。",
            "{tech}の{aspect}を{improve}したい。",
            "{task}に{tech}を導入する。",
            "{tech}と{tech2}を組み合わせて{task}を行う。",
            "{tech}の{aspect}に課題がある。",
            "{task}のために{tech}を検証中だ。",
        ],
        pools={
            "tech": ["OpenAI API", "ChatGPT", "Claude", "RAG", "LLM",
                     "ベクトル検索", "Transformer", "埋め込みモデル",
                     "ファインチューニング", "プロンプト設計"],
            "tech2": ["MySQL", "ChromaDB", "Redis", "Docker", "Python",
                      "形態素解析器", "全文検索エンジン"],
            "task": ["社内文書検索", "チャットボット", "要約システム",
                     "感情分析", "意図分類", "FAQ応答", "レコメンド機能",
                     "ナレッジ管理", "コード補完"],
            "aspect": ["回答精度", "応答速度", "コスト", "再現性",
                       "スケーラビリティ", "メモリ使用量", "検索精度"],
            "improve": ["改善", "最適化", "向上", "削減", "安定化"],
        },
    ),
    # ───────────────────────────────────────────── 8. 質問・疑問
    Category(
        name="質問・疑問",
        expected_polarity=None,
        acceptable_emotions=None,
        expected_intents={"question"},
        templates=[
            "{topic}は{qword}ですか？",
            "{topic}について教えてください。",
            "{topic}は{qword}でしょうか？",
            "どうすれば{topic2}できますか？",
            "{topic}の{aspect}が分かりません。",
            "{topic2}にはどうしたらいいですか？",
            "{topic}は{qword}になりますか？",
        ],
        pools={
            "topic": ["この機能の使い方", "申請の手順", "料金プラン",
                      "返品の方法", "登録方法", "解約条件", "サポート時間",
                      "対応OS", "保証期間", "支払い方法", "配送日数",
                      "キャンセル料", "更新のタイミング", "無料体験の範囲",
                      "アカウントの種類", "ログイン方法", "ポイントの有効期限",
                      "領収書の発行", "問い合わせ窓口", "推奨環境"],
            "topic2": ["パスワードを再設定", "アカウントを統合", "データを移行",
                       "通知をオフに", "プランを変更", "領収書を発行",
                       "二段階認証を設定", "支払い方法を変更", "退会",
                       "メールアドレスを変更", "請求書をダウンロード",
                       "サブアカウントを追加", "言語設定を変更", "履歴を確認"],
            "qword": ["いつ", "どこ", "なぜ", "いくら", "どれ", "何"],
            "aspect": ["設定", "条件", "対象範囲", "手順", "期限",
                       "料金", "適用条件", "必要書類"],
        },
    ),
    # ───────────────────────────────────────────── 9. 要望・依頼
    Category(
        name="要望・依頼",
        expected_polarity=None,
        acceptable_emotions=None,
        expected_intents={"request", "desire", "support_request"},
        templates=[
            "{target}を{action}してほしいです。",
            "{target}を{action}していただけますか。",
            "できれば{target}を{action}してください。",
            "{target}を{want}たいです。",
            "{target}の{action}をお願いします。",
            "{target}を{action}してもらえると助かります。",
        ],
        pools={
            "target": ["この不具合", "納期", "デザイン", "見積もり", "資料",
                       "アカウント設定", "請求内容", "仕様", "スケジュール",
                       "マニュアル", "価格設定", "契約条件", "画面のレイアウト",
                       "通知設定", "サポート体制", "返品ポリシー",
                       "メニュー構成", "操作手順"],
            "action": ["修正", "確認", "改善", "対応", "更新", "見直し", "調整",
                       "簡略化", "再検討"],
            "want": ["改善し", "見直し", "相談し", "変更し", "検討し", "提案し"],
        },
    ),
    # ───────────────────────────────────────────── 10. 日常会話
    Category(
        name="日常会話",
        expected_polarity=None,
        acceptable_emotions=None,
        templates=[
            "{time}は{place}で{activity}。",
            "{person}と{place}に行ってきた。",
            "{time}{food}を食べた。",
            "{person}が{place}に来るらしい。",
            "{time}は{weather}から{activity2}。",
            "{place}まで{activity}つもりだ。",
        ],
        pools={
            "time": ["今日", "昨日", "週末", "明日", "午後", "今朝", "夕方"],
            "place": ["近所の公園", "駅前のカフェ", "いつものスーパー",
                      "図書館", "実家", "美容院", "商店街", "海辺", "本屋"],
            "activity": ["散歩した", "買い物をした", "のんびり過ごした",
                         "友達と会った", "本を読んだ", "写真を撮った"],
            "activity2": ["出かけることにした", "家で過ごすことにした",
                          "予定を変更した", "洗濯をした"],
            "person": ["友達", "兄", "母", "同僚", "近所の人", "いとこ"],
            "food": ["定食", "パスタ", "ラーメン", "サンドイッチ", "カレー",
                     "おにぎり", "うどん"],
            "weather": ["雨だった", "天気が良かった", "風が強かった", "暑かった"],
        },
    ),
    # ─────────────────────────────────────── 11. オノマトペ・ポジ (v0.2.7 追加)
    # ⚠️ 11〜13 は v0.2.7 で末尾追加。ここより上の10カテゴリ (レガシー) は凍結。
    Category(
        name="オノマトペ・ポジ",
        expected_polarity="positive",
        acceptable_emotions={"joy", "anticipation", "moved", "admiration"},
        templates=[
            "{event}て、{ono}する。",
            "{eventn}のことを考えるだけで{ono}してくる。",
            "{eventn}が近づいてきて{ono}する。",
            "{ono}しながら{eventn}を待っている。",
            "{eventn}が決まって{ono}が止まらない。",
            "{event}てからずっと{ono}している。",
        ],
        pools={
            # カタカナ / ひらがな表記ゆれ + 促音強調形 (ワックワク) を混在させる
            "ono": ["ワクワク", "わくわく", "ウキウキ", "うきうき",
                    "キュンキュン", "きゅんきゅん", "ウズウズ", "うずうず",
                    "ワックワク"],
            "event": ["新しいプロジェクトが始まっ", "旅行の日程が決まっ",
                      "週末の予定が立っ", "新作の発表を見", "予約が取れ",
                      "気になる企画を聞い", "発売日が発表され", "当選の連絡が来",
                      "新しい趣味を見つけ", "久しぶりの再会が決まっ"],
            "eventn": ["旅行", "ライブ", "発売日", "引っ越し", "デート",
                       "文化祭", "発表会", "誕生日", "連休", "初出勤",
                       "温泉旅行", "新学期"],
        },
    ),
    # ─────────────────────────────────────── 12. オノマトペ・ネガ (v0.2.7 追加)
    Category(
        name="オノマトペ・ネガ",
        expected_polarity="negative",
        acceptable_emotions={"irritation", "anger", "sadness", "anxiety"},
        templates=[
            "{cause}て、{ono}する。",
            "{cause}てから{ono}が止まらない。",
            "朝から{ono}しっぱなしだ。",
            "{cause}て、ずっと{ono}している。",
            "{causeru}たびに{ono}する。",
            "{ono}して{result}。",
        ],
        pools={
            "causeru": ["渋滞にはまる", "小言を言われる", "連絡を待つ",
                        "その話を聞く", "残業になる", "月末が来る",
                        "電話が鳴る", "上司と話す"],
            "ono": ["イライラ", "いらいら", "ムカムカ", "むかむか",
                    "モヤモヤ", "もやもや", "ソワソワ", "そわそわ",
                    "ハラハラ", "はらはら", "ビクビク", "びくびく",
                    "メソメソ", "めそめそ", "クヨクヨ", "くよくよ",
                    "ヒヤヒヤ", "ひやひや", "ピリピリ", "ぴりぴり",
                    "ムシャクシャ", "むしゃくしゃ"],
            "cause": ["渋滞にはまっ", "連絡が来なく", "結果待ちが続い",
                      "小言を言われ", "仕事が進まなく", "昔の失敗を思い出し",
                      "隣の工事がうるさく", "予定が二転三転し", "返事が遅れ",
                      "物価が上がっ"],
            "result": ["眠れない", "集中できない", "仕事が手につかない"],
        },
    ),
    # ─────────────────────────────── 13. 鳴き声・環境音 (v0.2.7 追加・感情なしが正解)
    Category(
        name="鳴き声・環境音",
        expected_no_emotion=True,
        templates=[
            "{animal}が{cry}鳴いている。",
            "{animal}が{cry}と鳴いた。",
            "外で{animal}が{cry}鳴いていた。",
            "{time}から{animal}が{cry}鳴いている。",
            "どこかから{cry}という鳴き声が聞こえる。",
            "雨が{rain}降っている。",
            "{time}から雨が{rain}降っている。",
            "窓の外で風が{wind}吹いている。",
            "{animal}の鳴き声で目が覚めた。",
        ],
        pools={
            "animal": ["犬", "猫", "ひよこ", "カラス", "牛", "ヤギ",
                       "カエル", "スズメ", "ニワトリ", "セミ"],
            "time": ["今朝", "さっき", "夕方", "明け方", "昨夜"],
            "cry": ["ワンワン", "わんわん", "ニャーニャー", "にゃーにゃー",
                    "ピヨピヨ", "ぴよぴよ", "カーカー", "モーモー", "もーもー",
                    "メエメエ", "ケロケロ", "けろけろ", "チュンチュン", "ミンミン"],
            "rain": ["しとしと", "ざあざあ", "ぱらぱら", "ポツポツ",
                     "しとしとと", "ざーざー"],
            "wind": ["びゅうびゅう", "ヒューヒュー", "そよそよ", "ごうごう"],
        },
    ),
]

# v0.1.10〜v0.2.6 の歴代「5000例文」数値と比較するためのレガシー10カテゴリ。
_LEGACY10_NAMES: tuple[str, ...] = (
    "喜び・ポジティブ", "怒り・不満", "悲しみ・憂鬱", "不安・恐れ",
    "SNS・スラング", "ビジネス・業務", "技術・AI", "質問・疑問",
    "要望・依頼", "日常会話",
)


# ---------------------------------------------------------------------------
# 文生成
# ---------------------------------------------------------------------------
def _fill(template: str, pools: dict[str, list[str]], rng: random.Random) -> str:
    out = template
    # {slot} を順次置換（同名 slot は同一文内で同じ値）
    chosen: dict[str, str] = {}
    while "{" in out:
        start = out.index("{")
        end = out.index("}", start)
        slot = out[start + 1 : end]
        if slot not in chosen:
            chosen[slot] = rng.choice(pools[slot])
        out = out[:start] + chosen[slot] + out[end + 1 :]
    return out


def generate_corpus(rng: random.Random) -> dict[str, list[str]]:
    """各カテゴリ PER_CATEGORY 文を一意になるよう生成する。"""
    corpus: dict[str, list[str]] = {}
    for cat in CATEGORIES:
        seen: set[str] = set()
        sentences: list[str] = []
        attempts = 0
        max_attempts = PER_CATEGORY * 200
        while len(sentences) < PER_CATEGORY and attempts < max_attempts:
            attempts += 1
            tmpl = rng.choice(cat.templates)
            s = _fill(tmpl, cat.pools, rng)
            if s not in seen:
                seen.add(s)
                sentences.append(s)
        if len(sentences) < PER_CATEGORY:
            raise RuntimeError(
                f"カテゴリ '{cat.name}' は {len(sentences)} 文しか生成できません"
                f"（テンプレート/語彙プールの組合せ不足）"
            )
        corpus[cat.name] = sentences
    return corpus


# ---------------------------------------------------------------------------
# 集計
# ---------------------------------------------------------------------------
@dataclass
class CatResult:
    name: str
    total: int = 0
    # 検出率
    emotion_detected: int = 0
    intent_detected: int = 0
    chunk_generated: int = 0
    rag_generated: int = 0
    # 正確度（分母は scorable 件数）
    emotion_correct: int = 0
    emotion_scorable: int = 0
    polarity_correct: int = 0
    polarity_scorable: int = 0
    intent_correct: int = 0
    intent_scorable: int = 0
    # 補助
    total_chunks: int = 0
    total_keywords: int = 0
    times_ms: list[float] = field(default_factory=list)
    errors: int = 0
    samples: list[dict] = field(default_factory=list)


def _pct(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


def run(output_json: Path | None, output_md: Path | None) -> None:
    from kotobacore import Analyzer
    from kotobacore._version import __version__

    rng = random.Random(SEED)
    corpus = generate_corpus(rng)
    total_texts = sum(len(v) for v in corpus.values())

    analyzer = Analyzer()
    analyzer.analyze("ウォームアップ")  # 辞書ロードを事前に済ませる

    cat_by_name = {c.name: c for c in CATEGORIES}
    results: list[CatResult] = []
    processed = 0

    for cat_name, texts in corpus.items():
        spec = cat_by_name[cat_name]
        cr = CatResult(name=cat_name, total=len(texts))
        for text in texts:
            processed += 1
            if processed % 250 == 0:
                print(f"\r  [{processed}/{total_texts}] {cat_name}", end="", flush=True)

            try:
                t0 = time.perf_counter()
                r = analyzer.analyze(text)
                elapsed = (time.perf_counter() - t0) * 1000
                cr.times_ms.append(elapsed)

                emo = r.emotion
                intent = r.intent
                chunks = r.chunks
                rag = r.rag

                emo_det = emo is not None and emo.primary is not None
                int_det = intent is not None and intent.label not in (None, "unknown")
                chk_det = len(chunks) > 0
                rag_det = len(rag.keywords) > 0

                cr.emotion_detected += emo_det
                cr.intent_detected += int_det
                cr.chunk_generated += chk_det
                cr.rag_generated += rag_det
                cr.total_chunks += len(chunks)
                cr.total_keywords += len(rag.keywords)

                # 正確度
                if spec.expected_no_emotion:
                    # 「感情なし」が正解のカテゴリ — 検出されたら誤検出
                    cr.emotion_scorable += 1
                    if not emo_det:
                        cr.emotion_correct += 1
                elif spec.acceptable_emotions is not None:
                    cr.emotion_scorable += 1
                    if emo and emo.primary in spec.acceptable_emotions:
                        cr.emotion_correct += 1
                if spec.expected_polarity is not None:
                    cr.polarity_scorable += 1
                    if emo and emo.polarity == spec.expected_polarity:
                        cr.polarity_correct += 1
                if spec.expected_intents is not None:
                    cr.intent_scorable += 1
                    if intent and intent.label in spec.expected_intents:
                        cr.intent_correct += 1

                if len(cr.samples) < 5:
                    cr.samples.append({
                        "text": text,
                        "emotion": emo.primary if emo else None,
                        "polarity": emo.polarity if emo else None,
                        "intent": intent.label if intent else None,
                        "chunks": [c.text for c in chunks][:5],
                        "keywords": list(rag.keywords)[:5],
                        "time_ms": round(elapsed, 2),
                    })
            except Exception as e:  # noqa: BLE001
                cr.errors += 1
                if len(cr.samples) < 5:
                    cr.samples.append({"text": text, "error": str(e)})
        results.append(cr)

    print()

    # 全体時間集計
    all_times = [t for cr in results for t in cr.times_ms]
    all_times_sorted = sorted(all_times)

    def _percentile(data: list[float], p: float) -> float:
        if not data:
            return 0.0
        k = int(round((len(data) - 1) * p))
        return data[k]

    time_stats = {
        "count": len(all_times),
        "mean_ms": round(statistics.mean(all_times), 3) if all_times else 0.0,
        "median_ms": round(statistics.median(all_times), 3) if all_times else 0.0,
        "p95_ms": round(_percentile(all_times_sorted, 0.95), 3),
        "p99_ms": round(_percentile(all_times_sorted, 0.99), 3),
        "min_ms": round(min(all_times), 3) if all_times else 0.0,
        "max_ms": round(max(all_times), 3) if all_times else 0.0,
        "total_s": round(sum(all_times) / 1000, 2),
    }

    # 全体集計
    def _aggregate(subset: list[CatResult]) -> dict:
        return {
            "total": sum(c.total for c in subset),
            "emotion_detected": sum(c.emotion_detected for c in subset),
            "intent_detected": sum(c.intent_detected for c in subset),
            "chunk_generated": sum(c.chunk_generated for c in subset),
            "rag_generated": sum(c.rag_generated for c in subset),
            "emotion_correct": sum(c.emotion_correct for c in subset),
            "emotion_scorable": sum(c.emotion_scorable for c in subset),
            "polarity_correct": sum(c.polarity_correct for c in subset),
            "polarity_scorable": sum(c.polarity_scorable for c in subset),
            "intent_correct": sum(c.intent_correct for c in subset),
            "intent_scorable": sum(c.intent_scorable for c in subset),
            "errors": sum(c.errors for c in subset),
        }

    g = _aggregate(results)
    # レガシー10カテゴリのサブセット集計 — v0.2.6 以前の「5000例文」数値と直接比較可
    g10 = _aggregate([c for c in results if c.name in _LEGACY10_NAMES])

    data = {
        "meta": {
            "kotobacore_version": __version__,
            "date": datetime.now().isoformat(),
            "python_version": sys.version.split()[0],
            "seed": SEED,
            "total": total_texts,
            "categories": len(CATEGORIES),
            "per_category": PER_CATEGORY,
        },
        "summary": {
            "emotion_detection_rate": _pct(g["emotion_detected"], g["total"]),
            "intent_detection_rate": _pct(g["intent_detected"], g["total"]),
            "chunk_generation_rate": _pct(g["chunk_generated"], g["total"]),
            "rag_generation_rate": _pct(g["rag_generated"], g["total"]),
            "emotion_accuracy": _pct(g["emotion_correct"], g["emotion_scorable"]),
            "polarity_accuracy": _pct(g["polarity_correct"], g["polarity_scorable"]),
            "intent_accuracy": _pct(g["intent_correct"], g["intent_scorable"]),
            "errors": g["errors"],
        },
        # レガシー10カテゴリのみの集計 (v0.2.6 以前の 5000例文 数値と直接比較可)
        "summary_legacy10": {
            "total": g10["total"],
            "emotion_detection_rate": _pct(g10["emotion_detected"], g10["total"]),
            "intent_detection_rate": _pct(g10["intent_detected"], g10["total"]),
            "chunk_generation_rate": _pct(g10["chunk_generated"], g10["total"]),
            "rag_generation_rate": _pct(g10["rag_generated"], g10["total"]),
            "emotion_accuracy": _pct(g10["emotion_correct"], g10["emotion_scorable"]),
            "polarity_accuracy": _pct(g10["polarity_correct"], g10["polarity_scorable"]),
            "intent_accuracy": _pct(g10["intent_correct"], g10["intent_scorable"]),
            "errors": g10["errors"],
        },
        "timing": time_stats,
        "categories": [],
    }
    for c in results:
        data["categories"].append({
            "name": c.name,
            "total": c.total,
            "emotion_detection_rate": _pct(c.emotion_detected, c.total),
            "intent_detection_rate": _pct(c.intent_detected, c.total),
            "chunk_generation_rate": _pct(c.chunk_generated, c.total),
            "rag_generation_rate": _pct(c.rag_generated, c.total),
            "emotion_accuracy": _pct(c.emotion_correct, c.emotion_scorable),
            "polarity_accuracy": _pct(c.polarity_correct, c.polarity_scorable),
            "intent_accuracy": _pct(c.intent_correct, c.intent_scorable),
            "avg_chunks": round(c.total_chunks / c.total, 2),
            "avg_keywords": round(c.total_keywords / c.total, 2),
            "mean_time_ms": round(statistics.mean(c.times_ms), 3) if c.times_ms else 0.0,
            "errors": c.errors,
            "samples": c.samples,
        })

    if output_json:
        output_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON saved → {output_json}")

    # ── Markdown ──
    md: list[str] = [
        f"# KotobaCore {total_texts}例文 品質テスト結果",
        "",
        f"> 実施日: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> KotobaCore: v{__version__} / 総例文数: {total_texts} / カテゴリ: {len(CATEGORIES)} / seed: {SEED}",
        "",
        "---",
        "",
        "## 1. 全体サマリー",
        "",
        "| 指標 | 値 |",
        "|---|---|",
        f"| 総例文数 | {g['total']} 件 |",
        f"| 感情検出率 | {data['summary']['emotion_detection_rate']*100:.1f}% |",
        f"| 意図検出率 | {data['summary']['intent_detection_rate']*100:.1f}% |",
        f"| チャンク生成率 | {data['summary']['chunk_generation_rate']*100:.1f}% |",
        f"| RAGキーワード生成率 | {data['summary']['rag_generation_rate']*100:.1f}% |",
        f"| 感情正確度 | {data['summary']['emotion_accuracy']*100:.1f}% (分母 {g['emotion_scorable']}) |",
        f"| 極性正確度 | {data['summary']['polarity_accuracy']*100:.1f}% (分母 {g['polarity_scorable']}) |",
        f"| 意図正確度 | {data['summary']['intent_accuracy']*100:.1f}% (分母 {g['intent_scorable']}) |",
        f"| エラー件数 | {g['errors']} 件 |",
        "",
        "### レガシー10カテゴリ集計 (v0.2.6 以前の 5000例文 数値と比較用)",
        "",
        "| 指標 | 値 |",
        "|---|---|",
        f"| 総例文数 | {g10['total']} 件 |",
        f"| 感情検出率 | {data['summary_legacy10']['emotion_detection_rate']*100:.1f}% |",
        f"| 感情正確度 | {data['summary_legacy10']['emotion_accuracy']*100:.1f}% (分母 {g10['emotion_scorable']}) |",
        f"| 極性正確度 | {data['summary_legacy10']['polarity_accuracy']*100:.1f}% (分母 {g10['polarity_scorable']}) |",
        f"| 意図正確度 | {data['summary_legacy10']['intent_accuracy']*100:.1f}% (分母 {g10['intent_scorable']}) |",
        "",
        "## 2. 処理時間",
        "",
        "| 指標 | 値 (ms) |",
        "|---|---|",
        f"| 平均 | {time_stats['mean_ms']} |",
        f"| 中央値 | {time_stats['median_ms']} |",
        f"| p95 | {time_stats['p95_ms']} |",
        f"| p99 | {time_stats['p99_ms']} |",
        f"| 最小 | {time_stats['min_ms']} |",
        f"| 最大 | {time_stats['max_ms']} |",
        f"| 合計 | {time_stats['total_s']} 秒 ({time_stats['count']} 文) |",
        "",
        "## 3. カテゴリ別",
        "",
        "| カテゴリ | 感情検出 | 意図検出 | chunk | RAG | 感情正確 | 極性正確 | 意図正確 | 平均ms |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in data["categories"]:
        def f(key: str) -> str:
            return f"{c[key]*100:.0f}%" if c[key] else "-"
        md.append(
            f"| {c['name']} "
            f"| {c['emotion_detection_rate']*100:.0f}% "
            f"| {c['intent_detection_rate']*100:.0f}% "
            f"| {c['chunk_generation_rate']*100:.0f}% "
            f"| {c['rag_generation_rate']*100:.0f}% "
            f"| {f('emotion_accuracy')} "
            f"| {f('polarity_accuracy')} "
            f"| {f('intent_accuracy')} "
            f"| {c['mean_time_ms']:.2f} |"
        )
    md += [
        "",
        "※ 正確度の '-' は当カテゴリで対象外（中立カテゴリ等）",
        "※ 鳴き声・環境音 カテゴリの感情正確度は「感情なし=正解」の率"
        "（100% から下がった分が誤検出）",
        "",
    ]

    if output_md:
        output_md.write_text("\n".join(md), encoding="utf-8")
        print(f"Markdown saved → {output_md}")

    # ── コンソール ──
    s = data["summary"]
    s10 = data["summary_legacy10"]
    print("\n" + "=" * 66)
    print(f"KotobaCore v{__version__}  {total_texts}例文品質テスト")
    print("=" * 66)
    print(f"  感情検出率   : {s['emotion_detection_rate']*100:5.1f}%")
    print(f"  意図検出率   : {s['intent_detection_rate']*100:5.1f}%")
    print(f"  チャンク生成率: {s['chunk_generation_rate']*100:5.1f}%")
    print(f"  RAG生成率    : {s['rag_generation_rate']*100:5.1f}%")
    print(f"  感情正確度   : {s['emotion_accuracy']*100:5.1f}%  (分母 {g['emotion_scorable']})")
    print(f"  極性正確度   : {s['polarity_accuracy']*100:5.1f}%  (分母 {g['polarity_scorable']})")
    print(f"  意図正確度   : {s['intent_accuracy']*100:5.1f}%  (分母 {g['intent_scorable']})")
    print(f"  エラー件数   : {g['errors']}")
    print("-" * 66)
    print("  [レガシー10カテゴリ集計 — v0.2.6 以前の 5000例文 と比較用]")
    print(f"  感情検出率 {s10['emotion_detection_rate']*100:.1f}% / "
          f"感情正確度 {s10['emotion_accuracy']*100:.1f}% / "
          f"極性正確度 {s10['polarity_accuracy']*100:.1f}% / "
          f"意図正確度 {s10['intent_accuracy']*100:.1f}%")
    # 誤検出カナリア: 鳴き声・環境音の感情検出率 (0% が理想)
    for c in results:
        if c.name == "鳴き声・環境音":
            print(f"  [誤検出カナリア] 鳴き声・環境音の感情検出率 "
                  f"{_pct(c.emotion_detected, c.total)*100:.1f}% (0% が理想)")
    print("-" * 66)
    print(f"  処理時間  平均 {time_stats['mean_ms']:.2f}ms / 中央 {time_stats['median_ms']:.2f}ms "
          f"/ p95 {time_stats['p95_ms']:.2f}ms / p99 {time_stats['p99_ms']:.2f}ms / 最大 {time_stats['max_ms']:.2f}ms")
    print(f"  合計 {time_stats['total_s']:.1f}秒 / {time_stats['count']}文")
    print("=" * 66)


def main() -> None:
    parser = argparse.ArgumentParser(description="KotobaCore 例文品質テスト (13カテゴリ×500)")
    parser.add_argument("--json", metavar="FILE", help="JSON出力先")
    parser.add_argument("--md", metavar="FILE", help="Markdown出力先")
    args = parser.parse_args()
    run(
        output_json=Path(args.json) if args.json else None,
        output_md=Path(args.md) if args.md else None,
    )


if __name__ == "__main__":
    main()
