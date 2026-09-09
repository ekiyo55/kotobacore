"""Intent classifier.

Per 04_内部設計書 §13 and 06_API §12. Rule-based v0.1 implementation that
scores each intent against the normalized text via pattern alternation
(``a|b|c``) from ``intent_rules.csv``.
"""

from __future__ import annotations

import re
from collections import defaultdict

from kotobacore.core.ir import EmotionResult, IntentCandidate, IntentResult, SentimentResult
from kotobacore.dictionary import DictionaryBundle

# Sentence-final question mark → question intent boost. Weaker than a direct
# rule hit (~0.5+) so explicit patterns still dominate.
_QUESTION_MARKS: tuple[str, ...] = ("？", "?")
_QUESTION_BOOST = 0.35

# Emotion-derived fallback: the emotion layer's ATTRIBUTED expressions (after
# token alignment / negation / neutral-topic-word fixes) drive a feedback
# intent when polarity is confident. Deliberately weaker than rule hits so
# specific intents (support_request / question / desire …) win when present.
_EMOTION_BOOST = 0.4
_EMOTION_MIN_CONFIDENCE = 0.45
_INFORM_SCORE = 0.3
_FEEDBACK_ENTITY_TYPES = frozenset({"PRODUCT", "SERVICE", "BRAND", "ORGANIZATION", "WORK"})
_NEGATION_TAILS = ("しない", "しなかった", "しません", "じゃない", "ではない", "くない", "くなかった", "ない", "なかった", "ません", "ず", "ぬ")
# Personal-post cues for share_experience (体験共有): first person, "today/just now", SNS punctuation / emoji
_PERSONAL_RE = re.compile(
    r"私|俺|僕|ぼく|うち|自分|今日|昨日|今朝|今夜|さっき|先週|先日|週末|久しぶり|初めて|てきた|ちゃった|しちゃ|てしまった|できた|"
    r"泣い|笑っ|焦っ|疲れ|眠|やった|ゲット|突破|作った|買った|行った|帰った|届いた|届か|落とした|消えた|空いた|驚いた|泣きそう|"
    r"乗り換えた|戻した|積んだ|減らしたら|したら|してみた|覚えて|迷う|お金ない|しかない|"
    r"母|父|祖母|祖父|おばあちゃん|おじいちゃん|家族|弟|妹|兄|姉|"
    r"[wｗ]{1,}$|[!！…〜～]|[\U0001F300-\U0001FAFF☀-➿]"
)
_FIRST_PERSON_RE = re.compile(r"私|俺|僕|ぼく|うち|自分|わたし")
# Third-person subject (部長は / 彼女は / 村人たちは …): an emotion attributed to someone else is a report (inform)
_THIRD_PERSON_RE = re.compile(r"(?:部長|課長|社長|先生|上司|同僚|彼女|彼|老人|少年|少女|青年|男|女|母|父|村人たち|皆|みんな|一同|田中|[一-龥]{1,3}(?:さん|氏|様|君|くん))(?:は|が|も)")
# Own facts reported in business style (弊社の売上高は…更新しました) are inform even with an evaluative word
_OWN_REPORT_RE = re.compile(r"(?:弊社|当社|我が社|売上|出荷|受注|利益|株価|市場|カバレッジ|稼働|目標未達)")
_FORMAL_END_RE = re.compile(r"(?:ました|しております|いたしました|でした|ております|おります)[。]?$")
# Refusal / complaint about a business object (提案 / 見積 / 採用 / 契約 …) is negative feedback even in formal style
_BUSINESS_OBJECT_RE = re.compile(r"(?:提案|見積|採用|契約|対応|納期|音響|請求|サーバー|価格|品質|スケジュール|会場|コスト|見送)")
_NEGATIVE_EMOTIONS = frozenset({"refusal", "irritation", "anger", "disgust", "sadness", "anxiety"})
# Rhetorical questions carry a stance, not a question (〜すぎん？ / 高くない？ / 何回聞いても / なんで…の)
_RHETORICAL_RE = re.compile(r"(?:すぎ(?:ん|る|)[？?]|くない[？?]|ないの[？?]|何回|何度|なんで|なぜ|どこまでも|何も|じゃん[？?]?$|とか[？?]$|では[？?]$|かよ[？?]?$)")
_DECLARATIVE_END_RE = re.compile(r"(?:[。．.!！]|です|ます|ました|でした|た|だ|る|い|ない|ね|よ|う|す|む|く|ぐ|ぶ|つ|ん|ろ|かった|ている|てる)$")


def _looks_personal(text: str) -> bool:
    return bool(_PERSONAL_RE.search(text))


def _is_declarative(text: str) -> bool:
    t = text.strip()
    if len(t) < 4 or t.endswith(("?", "？")):
        return False
    return bool(_DECLARATIVE_END_RE.search(t.rstrip("」』）)\"'")))


def _patterns_for(rule_pattern: str) -> list[str]:
    """Split a rule's ``a|b|c`` pattern into alternatives."""
    return [p.strip() for p in rule_pattern.split("|") if p.strip()]


def classify_intent(
    text: str,
    bundle: DictionaryBundle,
    emotion: EmotionResult | None = None,
    sentiment: SentimentResult | None = None,
    entities: list | None = None,
) -> IntentResult:
    """Classify ``text`` against ``intent_rules.csv``.

    Score per intent is the sum of (rule.score × matches) across all
    alternation patterns. Higher-priority rules contribute proportionally
    more. Two structural signals supplement the rules:

    * a sentence-final ？ boosts ``question``
    * the emotion layer's attributed polarity boosts ``positive_feedback`` /
      ``negative_feedback`` — feedback intent is derived from *attributed*
      emotion, not from raw topic-word substrings (仕様変更/バグ の教訓)

    The top-scoring intent becomes the label; remaining intents are sorted by
    score for ``candidates``.
    """
    if not text or not bundle.intent_rules:
        return IntentResult(label=None, confidence=0.0, candidates=[])

    scores: dict[str, float] = defaultdict(float)
    # words used as names (「感動」という名のパン屋) never trigger a rule (v0.6.6)
    quoted_names = {getattr(e, "surface", "") for e in entities or [] if getattr(e, "source", "") == "quoted"}

    for rule in bundle.intent_rules:
        patterns = _patterns_for(rule.pattern)
        rule_hits = 0
        for p in patterns:
            if not p or p in quoted_names:
                continue
            # Count occurrences, skipping negated ones (感動しない / 良くなかった must not
            # count as positive_feedback — v0.6.5, from the human evaluation set)
            start = 0
            while True:
                k = text.find(p, start)
                if k < 0:
                    break
                if not text[k + len(p):].startswith(_NEGATION_TAILS):
                    rule_hits += 1
                start = k + len(p)
        if rule_hits > 0:
            # Priority scales the score contribution
            priority_weight = max(rule.priority, 1) / 100.0
            scores[rule.intent] += rule.score * rule_hits * priority_weight

    rule_feedback = {k: scores[k] for k in ("positive_feedback", "negative_feedback") if scores.get(k)}  # explicit rule hits (ばかりなのに / ワロタ …)

    # Sentence-final question mark
    if text.rstrip().endswith(_QUESTION_MARKS):
        scores["question"] += _QUESTION_BOOST

    # Sentiment-attributed feedback fallback (Sentiment → Intent is the one
    # allowed module-to-module signal, 設計原則 4). ``emotion`` is accepted
    # for backward compatibility and carries the same polarity.
    # Evaluation polarity (sentiment.csv words) first; affective polarity
    # (emotion words) as the fallback. 2026-09-08 decision: 感情語は極性に含めない.
    # v0.6.5 (人手評価セットに合わせる): 評価語 (sentiment.csv) があれば feedback、感情語だけの
    # 個人的な投稿は share_experience (体験共有)、どの信号も無い平叙文は inform (情報提供)。
    if sentiment is not None and sentiment.polarity in ("positive", "negative") and sentiment.confidence >= _EMOTION_MIN_CONFIDENCE:
        # an evaluation of a product / service / organization is feedback; a personal post
        # evaluating one's own experience (今日のランチ美味しかった😋) is share_experience
        feedback_object = any(getattr(e, "type", None) in _FEEDBACK_ENTITY_TYPES for e in entities or [])
        if _looks_personal(text) and not feedback_object:
            scores["share_experience"] += _EMOTION_BOOST * sentiment.confidence
        else:
            target = "positive_feedback" if sentiment.polarity == "positive" else "negative_feedback"
            scores[target] += _EMOTION_BOOST * sentiment.confidence
    elif emotion is not None and emotion.polarity in ("positive", "negative", "mixed") and emotion.confidence >= _EMOTION_MIN_CONFIDENCE and emotion.primary:
        feedback_object = any(getattr(e, "type", None) in _FEEDBACK_ENTITY_TYPES for e in entities or [])
        third_person = (bool(_THIRD_PERSON_RE.search(text)) or all(getattr(e, "holder", "speaker") != "speaker" for e in emotion.expressions)) and not _FIRST_PERSON_RE.search(text)
        if third_person:
            scores["inform"] += _INFORM_SCORE  # someone else's feeling is reported, not expressed (部長は満足されていました)
        elif emotion.primary in _NEGATIVE_EMOTIONS and not _looks_personal(text) and _BUSINESS_OBJECT_RE.search(text):
            scores["negative_feedback"] += _EMOTION_BOOST * emotion.confidence  # 採用は見送ります / 納得しかねます
        elif feedback_object and emotion.polarity in ("positive", "negative"):
            # affect about a product / service (iPhone買ったけど感動しない) is feedback on it
            target = "positive_feedback" if emotion.polarity == "positive" else "negative_feedback"
            scores[target] += _EMOTION_BOOST * emotion.confidence
        elif _looks_personal(text):
            scores["share_experience"] += _EMOTION_BOOST * emotion.confidence
        else:
            scores["inform"] += _INFORM_SCORE

    # Rhetorical questions (〜すぎん？ / 高くない？ / なんで…の) that carry a stance are not questions (v0.6.6)
    stance = (sentiment is not None and sentiment.polarity in ("positive", "negative")) or (emotion is not None and emotion.primary is not None)
    if "question" in scores and stance and _RHETORICAL_RE.search(text):
        scores.pop("question", None)

    # Feedback vs. report vs. shared experience (v0.6.6, from the human evaluation set):
    #  - a personal post with no product / service / organization to review is share_experience, whatever rule fired
    #  - someone else's feeling (彼女は笑った) or our own facts in report style (弊社の売上高は…更新しました) is inform
    feedback_keys = [k for k in ("positive_feedback", "negative_feedback") if k in scores]
    if feedback_keys:
        has_object = any(getattr(e, "type", None) in _FEEDBACK_ENTITY_TYPES for e in entities or [])
        third = bool(_THIRD_PERSON_RE.search(text)) and not _FIRST_PERSON_RE.search(text)
        own_report = bool(_OWN_REPORT_RE.search(text) and _FORMAL_END_RE.search(text.strip())) and not _looks_personal(text)
        if third or own_report:
            scores["inform"] += max(scores.pop(k) for k in feedback_keys)
        elif _looks_personal(text) and not has_object and not _BUSINESS_OBJECT_RE.search(text) and not rule_feedback:
            # only affect-derived feedback moves; an explicit complaint / praise pattern (ばかりなのに / ワロタ) stays feedback
            scores["share_experience"] += max(scores.pop(k) for k in feedback_keys)

    if not scores:
        if _is_declarative(text):
            # a personal experience told without an affect word (週末に…作った / 先週末、軽井沢に行ってきたんだ) is still shared experience
            label = "share_experience" if (_looks_personal(text) and not _THIRD_PERSON_RE.search(text) and not _FORMAL_END_RE.search(text.strip())) else "inform"
            return IntentResult(label=label, confidence=_INFORM_SCORE, candidates=[IntentCandidate(label=label, confidence=_INFORM_SCORE)])
        return IntentResult(
            label="unknown",
            confidence=0.0,
            candidates=[IntentCandidate(label="unknown", confidence=0.0)],
        )

    # Normalize: cap each intent's score at 1.0 for confidence reporting
    # (the raw score may exceed 1.0 with repeated patterns)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    top_label, top_score = ranked[0]
    confidence = round(min(top_score, 1.0), 3)

    candidates = [
        IntentCandidate(label=label, confidence=round(min(score, 1.0), 3))
        for label, score in ranked
    ]

    return IntentResult(label=top_label, confidence=confidence, candidates=candidates)


# ---------------------------------------------------------------------------
# Query intent taxonomy (FR-060 / FR-080) — search-oriented, separate from
# the SNS feedback intents above. Returns (intent, answer_type).
# ---------------------------------------------------------------------------

_QUERY_RULES: list[tuple[str, str | None, re.Pattern[str]]] = [
    ("definition", "TEXT", re.compile(r"とは(?:何|なに|どういう|$|[?？])|って(?:何|なに|どういう)|の意味|の定義|とはどんな")),
    # order: compare / reason cues that contain どう (どう違う / どうして) must win over the how_to どう rule
    ("compare", "TEXT", re.compile(r"違い|どう違う|何が違う|比較|どっち|どちらが|どちらの|vs|対比|メリット|デメリット")),
    ("reason", "TEXT", re.compile(r"なぜ|何故|どうして|理由|原因|なんで|どうなる|どうなった")),
    # v0.5.3: noun-phrase how-to queries seen in the real corpus (〜の書き方 / 〜するコマンド / 〜に必要な操作 / どう保管する)
    ("how_to", "TEXT", re.compile(
        r"方法|やり方|どうやって|どうやれば|どうすれば|手順|の仕方|するには|にはどう|書き方|直し方|使い方|作り方|設定方法|"
        r"コマンド|操作|登録する|どう(?!して|いう|なる|なっ|し(?:た|て)|違|ち|も|で|見|思)",
    )),
    # v0.5.3: trouble-shooting phrasings (〜になる時の対処 / 〜エラーの解決策 / 〜への対応 / 〜の対策)
    ("procedure", "TEXT", re.compile(r"対処|解決策|解決方法|対策|(?:の|への|時の|ときの)対応\s*$|復旧|直す|トラブルシュート")),
    ("search_value", "MONEY", re.compile(r"いくら|価格|値段|料金|金額|費用|単価|売上|予算|コスト")),
    ("search_value", "DATE", re.compile(r"いつ|何時(?:頃|ごろ)?|何日|何年|何月|時期|期限|締め切り|納期|日程")),
    ("search_value", "LOCATION", re.compile(r"どこ|何処|場所|所在地|住所|どちらで")),
    ("search_value", "PERSON", re.compile(r"誰|だれ|どなた|担当者|責任者")),
    ("search_value", "NUMBER", re.compile(r"何人|何件|何台|何個|いくつ|何回|何%|何％|何割|数は|人数|件数|台数|割合|比率|目標")),
    ("list", "LIST", re.compile(r"一覧|リスト|教えて|挙げて|まとめ|おすすめ|お勧め|候補|例を|ありますか")),
    # ---- business / technical document questions (v0.5.2, from the real-corpus eval)
    ("search_value", "DATE", re.compile(r"(?:改訂|改定|施行|リリース|公開|開始|終了|導入|移行|更新)日|いつから|いつまで|日程|スケジュール")),
    ("search_value", "NUMBER", re.compile(r"行数|日数|件数|回数|台数|人数|上限|下限|最大|最小|範囲|サイズ|容量|桁|秒数|分数|時間数|ポート番号|バージョン|何[個件台人回日秒分桁]|レート|割合|比率")),
    ("search_value", "PERSON", re.compile(r"担当|作成者|著者|責任者|まとめた|承認者|所有者|オーナー|管理者は")),
    ("search_value", "LOCATION", re.compile(r"パス|ディレクトリ|フォルダ|ホスト|URL|保存先|置き場|場所|配置|どこに|どこで")),
    ("condition", "TEXT", re.compile(r"条件|とみなされ|場合は|ときは|要件|前提|制約|ルール|規定|規則|禁止")),
    ("procedure", "TEXT", re.compile(r"流れ|進め方|対処|対応方法|復旧|手続|設定方法|使い方")),
    ("specification", "TEXT", re.compile(r"仕様|方式|形式|フォーマット|構成|設計|項目|カラム|フィールド|型")),
]
_WH_RE = re.compile(r"何|なに|いつ|どこ|誰|だれ|いくら|いくつ|どう|どの|どれ|どちら|なぜ|どんな")


def classify_query_intent(text: str) -> tuple[str, str | None]:
    """Classify a search query into (intent, answer_type).

    intents: definition / how_to / reason / compare / search_value / list /
    condition / procedure / specification / yes_no / lookup. answer_type: TEXT / MONEY / DATE / LOCATION / PERSON /
    NUMBER / LIST / BOOLEAN / None.
    """
    t = text.strip()
    if not t:
        return "lookup", None
    for intent, answer_type, pat in _QUERY_RULES:
        if pat.search(t):
            return intent, answer_type
    if t.endswith(("か", "か?", "か？", "?", "？", "ですか", "ますか", "でしょうか")) and not _WH_RE.search(t):
        return "yes_no", "BOOLEAN"
    return "lookup", None
