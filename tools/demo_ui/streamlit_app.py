"""KotobaCore Streamlit Demo UI.

Run locally:

    streamlit run tools/demo_ui/streamlit_app.py

Run on a server (head-less, bound to localhost for reverse-proxy):

    streamlit run tools/demo_ui/streamlit_app.py \\
        --server.port 8588 \\
        --server.address 127.0.0.1 \\
        --server.headless true \\
        --browser.gatherUsageStats false
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from kotobacore import Analyzer
from kotobacore._version import __version__

# ---------------------------------------------------------------------------
# Cached analyzer (one per session)
# ---------------------------------------------------------------------------


@st.cache_resource
def get_analyzer(
    mode: str,
    enable_semantic_chunk: bool,
    enable_emotion: bool,
    enable_intent: bool,
    enable_rag: bool,
    use_external_dictionaries: bool,
    granularity: str,
) -> Analyzer:
    return Analyzer(
        mode=mode,
        enable_semantic_chunk=enable_semantic_chunk,
        enable_emotion=enable_emotion,
        enable_intent=enable_intent,
        enable_rag=enable_rag,
        use_external_dictionaries=use_external_dictionaries,
        granularity=granularity,
    )


# ---------------------------------------------------------------------------
# Fixed evaluation corpus (per 07_テスト仕様 §21 / 09_評価仕様 §4.2)
# ---------------------------------------------------------------------------


FIXED_CORPUS: list[tuple[str, list[str]]] = [
    (
        "Sentiment（評価語: 感情語とは別に「何をどう評価しているか」を取る）",
        [
            "このカメラは軽くて使いやすいが、バッテリーの持ちは微妙。",
            "対応が丁寧で助かった。ただ料金は高すぎる。",
            "サーバーは速いけど管理画面は分かりにくい。",
        ],
    ),
    (
        "Entity / Event（v0.4〜: 人名・組織・地名・日時・金額・数量、述語項）",
        [
            "株式会社山田商事は2025年度に大阪支社を設立し、佐藤部長が10月5日午前10時に説明会を開いた。",
            "昨日、田中さんが代々木公園の新しいカフェに行ったけど、コーヒーはいまいちで残念だった。",
            "予算は45億円、参加は約200名で、前年度比12%増を見込む。",
            "東京支店の売上目標はいくら？",
        ],
    ),

    ("基本", [
        "クラウドAPIの課金高すぎてしぬw",
        "このアニメ尊すぎて泣いた",
        "もう無理。請求まわりを確認して",
        "今日は新しいプロジェクトがスタート！ワクワクする！",
        "チームメンバーとの初ミーティング。みんな頼もしい！",
        "お昼はいつもの定食屋で。安定の美味しさ。",
        "思ったより難しい課題が...どうしよう。",
        "また仕様変更？さっき決めたばかりなのに...",
        "締め切りが近いのにバグが出た。もう無理かも...",
        "先輩が助けてくれた！なんとか解決できそう！",
        "社内FAQをRAG化したい",
        "ChatGPTの回答精度を改善したい",
        "東京都に行った",
    ]),
    # v0.2.7: かな表記ゆれ / 反復1トークン化 / 促音強調形 / 鳴き声=感情なし
    ("オノマトペ (v0.2.7)", [
        "わくわくするけど、ちょっとどきどきする",
        "渋滞にはまってイライラ。もやもやが止まらない",
        "明日の発表会、ワックワクが止まらない！",
        "猫がにゃーにゃー鳴いててキュンキュンした",
        "雨がしとしと降る中、犬がわんわん吠えている",
    ]),
    ("Plutchik 全8軸", [
        "新機能の発表まじかよ、びっくりした。でも課金高すぎてありえない、ムカつく。バグも怖いし不安。前のUIの方が良かったな、残念。ただ次のアップデートは楽しみにしてる。開発チームは信頼してるし最高！",
        "このアニメ号泣した、感動。でも怖いシーンでびっくりした。許せない展開に怒り感じたし、主人公が死んで悲しい。ドン引きする描写もあったけど、尊い関係性に癒やされた。続編めちゃ楽しみ！",
        "プロジェクト大成功でやったー！でも途中の仕様変更がありえなくてキレそうだった。締め切り怖すぎてパニックだったし、チームの一人が辞めて悲しかった。あの上司の判断にドン引き。さすがリーダーが最後は救ってくれた。次のフェーズも期待してる。",
    ]),
]


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


st.set_page_config(
    page_title="KotobaCore Demo",
    page_icon="🇯🇵",
    layout="wide",
)

st.title("KotobaCore Demo UI")
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] { font-size: 1rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.caption(
    f"Japanese semantic understanding engine — v{__version__} · "
    "tokenize / entities / predicates·events / semantic chunk / emotion + Plutchik / sentiment / intent / topics / query IR / document chunks / rerank"
)

# ---------------------------------------------------------------------------
# Sidebar — settings
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Settings")

    mode = st.selectbox(
        "分割モード (Split mode)",
        ["A", "B", "C"],
        index=2,
        help=(
            "Karuizawa トークナイザーはモードを無視します (単一粒度)。\n\n"
            "A / B / C は API 互換性のために受け付けますが動作は同じです。"
        ),
    )

    with st.expander("分割モードを詳しく", expanded=False):
        st.markdown(
            """
| Mode | 粒度 | 例: 「選挙管理委員会」 |
|---|---|---|
| A | 短単位 | 選挙 / 管理 / 委員 / 会 |
| B | 中間単位 | 選挙 / 管理委員会 |
| **C** | **長単位 (既定)** | **選挙管理委員会** |

KotobaCore の chunker は辞書照合 (`クラウドAPI` 等) を先に行うので、
A モードでも entity / slang は壊れません。普通名詞の刻み方だけが変わります。
"""
        )

    granularity = st.radio(
        "トークン粒度 (granularity)",
        ["coarse", "fine"],
        index=0,
        horizontal=True,
        help=(
            "coarse (既定): 意味単位を保つ長め分割 (思い出した / 締め切り)。\n\n"
            "fine: LM 語彙向けに 語幹 / 送り仮名 / 活用語尾 へ分解 (思|い|出|した)。"
            "Tokens タブだけが細かくなり、chunks / emotion / intent / RAG は常に "
            "coarse で計算されます。"
        ),
    )

    st.divider()
    st.subheader("機能トグル")
    enable_semantic_chunk = st.checkbox(
        "Semantic chunk を有効化",
        value=True,
        help=(
            "意味単位 chunk を生成する。OFF にすると chunks / semantic_tokens が空になります "
            "(emotion / intent / rag は normalized text から独立に動作)。"
        ),
    )
    enable_emotion = st.checkbox(
        "Emotion 解析を有効化",
        value=True,
        help=(
            "emotion.csv / slang.csv の surface match と "
            "emotion_examples.csv の例文類似度から感情とPlutchik分布を算出します。"
        ),
    )
    enable_intent = st.checkbox(
        "Intent 分類を有効化",
        value=True,
        help=(
            "intent_rules.csv のパターンマッチで pricing_complaint / support_request / "
            "positive_feedback / negative_feedback / agreement / admiration / question / "
            "request / unknown の 9 種から推定。"
        ),
    )
    doc_mode = st.checkbox(
        "文書モード (Document mode)",
        value=True,
        help="Document → Paragraph → Sentence の階層で解析し、検索用チャンク (document_chunks) も生成します。1 文でも結果は単文解析と同じなので常時オン推奨。オフにすると単文 API (analyze) の出力になります。",
    )
    reference_date_str = st.text_input(
        "基準日 (Reference date, YYYY-MM-DD)",
        value="",
        help="今日 / 昨日 / 3日前 などの相対日付を ISO 日付に解決するための基準日。空欄なら解決しません。",
    )
    enable_rag = st.checkbox(
        "RAG キーワード抽出を有効化",
        value=True,
        help=(
            "RAG 向けキーワード・検索クエリ・semantic phrases・要約ヒントを生成します。"
            "stopwords.csv で除外語フィルタ。"
        ),
    )
    use_external = st.checkbox(
        "外部辞書 (NRC) を使用",
        value=True,
        help=(
            "サーバーの dic/ 配下に置いた NRC Emotion-Intensity Lexicon (9,829 語) を"
            "取り込みます。NRC は内部 seed より lex_weight を下げて補助的に使用します。\n\n"
            "SNS 感情例文集 (546 語 / 約 2,746 例文) は v0.1.12 からパッケージ同梱で、"
            "この設定に関わらず常に有効です。"
        ),
    )

    with st.expander("結果の見方", expanded=False):
        st.markdown(
            """
| タブ | 内容 |
|---|---|
| **Chunks** | 意味単位の塊 (service / complaint / praise / slang_emotion / compound_noun ...) |
| **Emotion** | 主要感情 / 極性 / Plutchik 8 感情分布 / 検出された個別表現 |
| **Entities** | 人名・組織・地名・イベント・日付・時刻・金額・数量 (辞書 + パターン + 規則、v0.4) |
| **Events** | 述語と項 (誰が・何を・いつ・どこで) / Event 型 / Relation (v0.5) |
| **Sentiment** | 評価の極性 (v0.3〜 感情と分離) / 評価表現 / 否定反転 / 宛先 (target) / 原文位置 |
| **Query IR** | 入力を検索クエリとして構造化 (意図・回答型・対象・制約・同義語展開、v0.4) |
| **Document** | 文書モード時の段落 / 文ごとの解析 / 検索チャンク (v0.4) |
| **Intent** | 意図ラベル + 候補一覧 |
| **RAG** | キーワード / 検索クエリ / semantic phrases / 要約ヒント |
| **Tokens** | Karuizawa の形態素解析結果 |
| **Raw JSON** | API として呼び出した時に返ってくる完全な構造化データ |
"""
        )

    st.divider()
    st.markdown("**固定コーパス** — クリックで入力欄へ転送:")
    _btn_idx = 0
    for section, sentences in FIXED_CORPUS:
        st.caption(section)
        for sentence in sentences:
            _btn_idx += 1
            if st.button(sentence, key=f"sample-{_btn_idx}", use_container_width=True):
                # Update the text_area's session_state key directly (NOT a
                # separate key) so the change takes effect on the next rerun.
                st.session_state["text_input_box"] = sentence
                st.rerun()


# ---------------------------------------------------------------------------
# Input area
# ---------------------------------------------------------------------------


# One-time default; subsequent reads/writes go through the widget's key.
if "text_input_box" not in st.session_state:
    st.session_state["text_input_box"] = "クラウドAPIの課金高すぎてしぬw"

text = st.text_area(
    "Input Japanese text",
    height=120,
    key="text_input_box",
)

analyze_clicked = st.button("Analyze", type="primary")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# --- Japanese label maps (UI display only; JSON keeps English taxonomy) ---

_EMOTION_JA = {
    "joy": "喜び",
    "admiration": "称賛",
    "moved": "感動",
    "anger": "怒り",
    "irritation": "苛立ち",
    "sadness": "悲しみ",
    "anxiety": "不安",
    "refusal": "拒否",
    "agreement": "同意",
    "exaggeration": "誇張",
    "anticipation": "期待/願望",
    "mixed": "混合",
}

_ENTITY_JA = {
    "PERSON": "人名", "ORGANIZATION": "組織", "LOCATION": "地名", "PRODUCT": "製品", "BRAND": "ブランド",
    "SERVICE": "サービス", "WORK": "作品", "EVENT": "イベント", "TOPIC": "トピック", "DATE": "日付",
    "TIME": "時刻", "MONEY": "金額", "QUANTITY": "数量", "TECHNOLOGY": "技術", "MODEL": "モデル", "API": "API",
}

_POLARITY_JA = {
    "positive": "肯定的",
    "negative": "否定的",
    "mixed": "中立/混合",
    "neutral": "中立",
}

_PLUTCHIK_JA = {
    "joy": "喜び",
    "trust": "信頼",
    "fear": "恐れ",
    "surprise": "驚き",
    "sadness": "悲しみ",
    "disgust": "嫌悪",
    "anger": "怒り",
    "anticipation": "期待",
    "mixed": "混合",
}

_INTENT_JA = {
    "pricing_complaint": "料金不満",
    "support_request": "サポート要求",
    "positive_feedback": "好意的反応",
    "negative_feedback": "否定的反応",
    "agreement": "同意",
    "admiration": "称賛",
    "desire": "願望",
    "question": "質問",
    "request": "依頼",
    "unknown": "不明",
}

_CHUNK_TYPE_JA = {
    "service": "サービス",
    "product": "製品",
    "technology": "技術",
    "entity": "固有表現",
    "compound_noun": "複合名詞",
    "topic": "話題",
    "complaint": "不満",
    "praise": "称賛",
    "slang_emotion": "SNS感情",
    "request": "依頼",
}


def _emotion_emoji(emotion: str | None) -> str:
    # moved (感動) is positive — distinguish from sadness which uses 😢.
    return {
        "joy": "😊",
        "admiration": "🙌",
        "moved": "🥹",
        "anger": "😠",
        "irritation": "😤",
        "sadness": "😢",
        "anxiety": "😨",
        "refusal": "🙅",
        "agreement": "🤝",
        "exaggeration": "💥",
        "anticipation": "🤩",
        "mixed": "🌀",
    }.get(emotion or "", "")


def _polarity_color(polarity: str | None) -> str:
    return {
        "positive": "🟢",
        "negative": "🔴",
        "mixed": "🟡",
        "neutral": "⚪",
    }.get(polarity or "", "")


def _chunk_type_emoji(t: str) -> str:
    return {
        "service": "🛠️",
        "product": "📦",
        "technology": "🔧",
        "entity": "🏷️",
        "compound_noun": "🔗",
        "topic": "💬",
        "complaint": "😠",
        "praise": "🌟",
        "slang_emotion": "🗯️",
    }.get(t, "·")


def _bilingual(value: str | None, ja_map: dict[str, str]) -> str:
    """Render ' 日本語 (english) ' — falls back gracefully for unknown values."""
    if not value:
        return "—"
    ja = ja_map.get(value)
    return f"{ja} ({value})" if ja else value


# ---------------------------------------------------------------------------
# Run analysis
# ---------------------------------------------------------------------------


if analyze_clicked and text.strip():
    analyzer = get_analyzer(
        mode=mode,
        enable_semantic_chunk=enable_semantic_chunk,
        enable_emotion=enable_emotion,
        enable_intent=enable_intent,
        enable_rag=enable_rag,
        use_external_dictionaries=use_external,
        granularity=granularity,
    )

    if reference_date_str.strip():
        try:
            import datetime as _dt  # noqa: PLC0415

            analyzer.reference_date = _dt.date.fromisoformat(reference_date_str.strip())
        except ValueError:
            st.warning("基準日は YYYY-MM-DD 形式で入力してください。無視して続行します。")
            analyzer.reference_date = None
    else:
        analyzer.reference_date = None

    with st.spinner("Analyzing..."):
        result = analyzer.analyze_document(text) if doc_mode else analyzer.analyze(text)

    # ----------- Summary row
    cols = st.columns(4)

    primary = result.emotion.primary if result.emotion else None
    polarity = result.sentiment.polarity if result.sentiment else None
    affect_polarity = result.sentiment.affect_polarity if result.sentiment else (result.emotion.polarity if result.emotion else None)
    intent_label = result.intent.label if result.intent else None

    with cols[0]:
        if primary:
            primary_display = f"{_emotion_emoji(primary)} {_bilingual(primary, _EMOTION_JA)}"
        else:
            primary_display = "感情表現がありません"
        st.metric("主要な感情 (Primary emotion)", primary_display)
    with cols[1]:
        st.metric(
            "評価極性 (Sentiment)",
            f"{_polarity_color(polarity)} {_bilingual(polarity, _POLARITY_JA)}",
            delta=f"感情極性 {_bilingual(affect_polarity, _POLARITY_JA)}" if affect_polarity else None,
            delta_color="off",
        )
    with cols[2]:
        st.metric(
            "意図 (Intent)",
            _bilingual(intent_label, _INTENT_JA),
            delta=f"{result.intent.confidence if result.intent else 0:.2f}",
        )
    with cols[3]:
        st.metric("チャンク数 (Chunks)", len(result.chunks))

    # ----------- Tabs
    (tab_chunks, tab_entities, tab_events, tab_emotion, tab_sentiment, tab_intent, tab_rag,
     tab_query, tab_document, tab_tokens, tab_json) = st.tabs(
        ["Chunks", "Entities", "Events", "Emotion", "Sentiment", "Intent", "RAG", "Query IR", "Document", "Tokens", "Raw JSON"]
    )

    # ----- Events tab (v0.5: 述語項構造 / Relation / Event)
    with tab_events:
        if result.predicates:
            st.subheader("述語と項 (Predicate-argument)")
            pred_rows = [
                {
                    "id": p_.id,
                    "述語": p_.text,
                    "原形": p_.lemma,
                    "項 (role: text)": " / ".join(f"{a.role}: {a.text}" + (f" [{a.entity_id}]" if a.entity_id else "") for a in p_.arguments) or "—",
                    "否定": "✔" if p_.negated else "",
                    "態": p_.voice,
                    "名詞述語": "✔" if p_.nominal else "",
                }
                for p_ in result.predicates
            ]
            st.dataframe(pred_rows, use_container_width=True, hide_index=True)
            st.subheader("Events (誰が・何を・いつ・どこで)")
            ev_rows = [
                {
                    "id": e.id, "type": e.type, "述語": e.predicate,
                    "agent": e.agent_text or "", "object": e.object_text or "", "goal": e.goal_text or "",
                    "location": e.location_text or "", "time": e.time_text or "",
                    "否定": "✔" if e.negated else "", "態": e.voice,
                }
                for e in result.events
            ]
            st.dataframe(ev_rows, use_container_width=True, hide_index=True)
            if result.relations:
                st.subheader("Relations (主語 → 述語 → 項)")
                rel_rows = [
                    {"id": r_.id, "source": r_.source_text + (f" [{r_.source}]" if r_.source else ""),
                     "relation": r_.relation, "role": r_.role,
                     "target": r_.target_text + (f" [{r_.target}]" if r_.target else ""), "否定": "✔" if r_.negated else ""}
                    for r_ in result.relations
                ]
                st.dataframe(rel_rows, use_container_width=True, hide_index=True)
            st.caption("係り受け解析器は使わず、節ごとの末尾述語と格助詞 (が/は/を/に/で/から/と) から取る浅い構造です (要件 FR-023/040/041)。")
        else:
            st.info("述語は検出されませんでした。")

    # ----- Entities tab (v0.4: 辞書 / パターン / 日時 / 数量)
    with tab_entities:
        if result.entities:
            ent_rows = [
                {
                    "id": e.id,
                    "種別 (type)": f"{_ENTITY_JA.get(e.type, '')} ({e.type})",
                    "表層 (surface)": e.surface,
                    "正規化 (normalized)": e.normalized or "",
                    "値 (value)": "" if e.value is None else str(e.value),
                    "単位": e.unit or "",
                    "通貨": e.currency or "",
                    "出所 (source)": e.source,
                    "原文位置": f"{e.begin}-{e.end}",
                }
                for e in result.entities
            ]
            st.dataframe(ent_rows, use_container_width=True, hide_index=True)
            st.caption("DATE/TIME の値は基準日を与えると ISO 日付に解決されます。PERSON は敬称込みの表層と敬称なしの正規化形を持ちます。")
        else:
            st.info("エンティティは検出されませんでした。")

    # ----- Chunks tab
    with tab_chunks:
        if result.chunks:
            chunk_rows: list[dict[str, Any]] = []
            for c in result.chunks:
                chunk_rows.append(
                    {
                        "種別 (type)": f"{_chunk_type_emoji(c.type)} {_bilingual(c.type, _CHUNK_TYPE_JA)}",
                        "テキスト (text)": c.text,
                        "スコア (score)": c.score,
                        "token_ids": ",".join(map(str, c.token_ids)),
                    }
                )
            st.dataframe(chunk_rows, use_container_width=True, hide_index=True)
        else:
            st.info("チャンクは生成されませんでした。")

    # ----- Emotion tab
    with tab_emotion:
        if result.emotion and result.emotion.expressions:
            cols2 = st.columns([2, 3])

            with cols2[0]:
                st.subheader("Plutchik 8感情分布")
                if result.emotion.plutchik:
                    # Relabel bar chart keys to bilingual
                    plu_labeled = {
                        f"{_PLUTCHIK_JA.get(k, k)} ({k})": v
                        for k, v in result.emotion.plutchik.items()
                    }
                    st.bar_chart(plu_labeled)
                else:
                    st.info("Plutchik シグナルなし。")

            with cols2[1]:
                st.subheader("検出された感情表現 (Expressions)")
                expr_rows = [
                    {
                        "表現 (text)": e.text,
                        "感情 (emotion)": _bilingual(e.emotion, _EMOTION_JA),
                        "Plutchik": _bilingual(e.plutchik_emotion, _PLUTCHIK_JA),
                        "極性 (polarity)": _bilingual(e.polarity, _POLARITY_JA),
                        "主体 (holder)": e.holder_text or e.holder,
                        "対象 (about)": e.about_text or "",
                        "強度": e.intensity,
                        "確信度": e.confidence,
                        "一致例文": ", ".join(e.matched_examples[:3])
                        + ("..." if len(e.matched_examples) > 3 else ""),
                    }
                    for e in result.emotion.expressions
                ]
                st.dataframe(expr_rows, use_container_width=True, hide_index=True)

            st.write(
                f"全体強度 (intensity): **{result.emotion.intensity:.3f}** · "
                f"確信度 (confidence): **{result.emotion.confidence:.3f}**"
            )
        else:
            st.info("感情は検出されませんでした。")

    # ----- Sentiment tab (v0.3: 評価の極性。感情と分離、否定で反転)
    with tab_sentiment:
        if result.sentiment and result.sentiment.expressions:
            st.subheader(
                f"極性: {_polarity_color(result.sentiment.polarity)} "
                f"{_bilingual(result.sentiment.polarity, _POLARITY_JA)}"
            )
            sent_rows = [
                {
                    "表現 (text)": e.text,
                    "極性 (polarity)": _bilingual(e.polarity, _POLARITY_JA),
                    "否定 (negated)": "✔" if e.negated else "",
                    "宛先 (target)": (e.target_text or "") + (f" [{e.target}]" if e.target else ""),
                    "強度": e.intensity,
                    "確信度": e.confidence,
                    "原文位置": f"{e.begin}-{e.end}",
                }
                for e in result.sentiment.expressions
            ]
            st.dataframe(sent_rows, use_container_width=True, hide_index=True)
            st.write(
                f"全体強度 (intensity): **{result.sentiment.intensity:.3f}** · "
                f"確信度 (confidence): **{result.sentiment.confidence:.3f}**"
            )
            st.caption("評価語 (sentiment.csv: いまいち / 使いやすい 等) は感情カテゴリを持たず、ここだけに現れます。")
        else:
            st.info("評価表現 (評価語) は検出されませんでした。")
        if result.sentiment and result.sentiment.affect_polarity:
            st.write(
                f"感情語由来の極性 (affect_polarity): "
                f"{_polarity_color(result.sentiment.affect_polarity)} "
                f"{_bilingual(result.sentiment.affect_polarity, _POLARITY_JA)} — 評価極性には含めません (2026-09-08 方針)。"
            )

    # ----- Intent tab
    with tab_intent:
        if result.intent and result.intent.candidates:
            st.subheader(f"判定結果: {_bilingual(result.intent.label, _INTENT_JA)}")
            cand_rows = [
                {
                    "意図 (label)": _bilingual(c.label, _INTENT_JA),
                    "確信度 (confidence)": c.confidence,
                }
                for c in result.intent.candidates
            ]
            st.dataframe(cand_rows, use_container_width=True, hide_index=True)
        else:
            st.info("意図は分類されませんでした。")

    # ----- RAG tab
    with tab_rag:
        if result.rag:
            st.subheader("Keywords")
            if result.rag.keywords:
                st.code(" / ".join(result.rag.keywords), language="text")
            st.subheader("Search query")
            st.code(result.rag.search_query or "(empty)", language="text")
            st.subheader("Summary hint")
            st.write(result.rag.summary_hint or "—")
            st.subheader("Semantic phrases")
            for sp in result.rag.semantic_phrases:
                st.write(f"- {sp}")
        else:
            st.info("RAG disabled.")

    # ----- Topics (v0.5 FR-063) shown under the RAG tab
    with tab_rag:
        if result.topics and result.topics.topics:
            st.subheader("Topics (主題)")
            st.dataframe(
                [{"label": t.label, "score": t.score, "count": t.count, "source": t.source, "entity": t.entity_id or ""} for t in result.topics.topics],
                use_container_width=True, hide_index=True,
            )

    # ----- Query IR tab (v0.4 FR-080): the input read as a search query
    with tab_query:
        try:
            q = analyzer.analyze_query(text if not doc_mode else text.splitlines()[0])
            qc = st.columns(4)
            qc[0].metric("意図 (intent)", q.intent)
            qc[1].metric("回答型 (answer_type)", q.answer_type or "—")
            qc[2].metric("対象 (target)", q.target or "—")
            qc[3].metric("極性 (sentiment)", q.sentiment or "—")
            st.write("**normalized_query**:", q.normalized_query)
            st.write("**keywords**:", ", ".join(q.keywords) or "—")
            st.write("**expanded_terms (同義語展開)**:", ", ".join(q.expanded_terms) or "—")
            st.write("**constraints**:", q.constraints or "—")
            st.caption("文書 IR と同じ語彙 (entities / intent / sentiment / keywords) で質問を構造化し、Retriever に渡せる形にします。")
            with st.expander("Query IR JSON"):
                st.code(q.to_json(pretty=True), language="json")
            if doc_mode and result.document_chunks:
                from kotobacore.rag import ChunkView, rerank  # noqa: PLC0415

                st.subheader("Rerank (v0.5): 1 行目を質問として文書チャンクを再ランク")
                views = [ChunkView.from_chunk(c, result) for c in result.document_chunks]
                ranked = rerank(q, views)
                st.dataframe(
                    [
                        {
                            "chunk": i, "score": sc,
                            **{k: ("—" if v is None else round(v, 2)) for k, v in f.items()},
                            "text": result.document_chunks[i].text[:60],
                        }
                        for i, sc, f in ranked
                    ],
                    use_container_width=True, hide_index=True,
                )
                st.caption("Embedding 類似度は外部から渡す設計のためここでは未使用。特徴量 (entity / keyword / intent / time / topic / sentiment) のみの点数です。")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Query IR の生成に失敗しました: {exc}")

    # ----- Document tab (v0.4 FR-050 / FR-081): hierarchy and retrieval chunks
    with tab_document:
        if not doc_mode:
            st.info("サイドバーの「文書モード」を有効にすると、段落 / 文 / 検索チャンクを表示します。")
        else:
            st.subheader(f"段落 {len(result.paragraphs)} · 文 {len(result.sentences)} · チャンク {len(result.document_chunks)}")
            sent_rows = [
                {
                    "id": s_.id,
                    "文": s_.text,
                    "極性": (s_.sentiment.polarity if s_.sentiment else None) or "",
                    "感情": (s_.emotion.primary if s_.emotion else None) or "",
                    "意図": (s_.intent.label if s_.intent else None) or "",
                    "entities": ", ".join(s_.entity_ids),
                }
                for s_ in result.sentences
            ]
            st.dataframe(sent_rows, use_container_width=True, hide_index=True)
            st.subheader("Document chunks (検索単位)")
            for c in result.document_chunks:
                with st.expander(f"chunk {c.id} · 文 {c.sentence_ids} · {c.summary_hint or ''}"):
                    st.write(c.text)
                    st.caption(
                        f"keywords: {', '.join(c.keywords)} | topics: {', '.join(c.topics)} | "
                        f"entities: {', '.join(c.entity_ids)} | 原文位置 {c.begin}-{c.end}"
                    )

    # ----- Tokens tab
    with tab_tokens:
        if result.tokens:
            tok_rows = [
                {
                    "id": t.id,
                    "surface": t.surface,
                    "normalized": t.normalized,
                    "pos": t.pos,
                    "begin": t.begin,
                    "end": t.end,
                    "unknown": t.unknown,
                }
                for t in result.tokens
            ]
            st.dataframe(tok_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No tokens.")

    # ----- Raw JSON tab
    with tab_json:
        st.code(result.to_json(pretty=True), language="json")

elif analyze_clicked:
    st.warning("Please enter some text.")
else:
    st.info("Enter text above and click **Analyze**, or pick a fixed-corpus sample from the sidebar.")
