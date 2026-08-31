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
    "tokenize / semantic chunk / emotion + Plutchik / intent / RAG keywords"
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

    with st.spinner("Analyzing..."):
        result = analyzer.analyze(text)

    # ----------- Summary row
    cols = st.columns(4)

    primary = result.emotion.primary if result.emotion else None
    polarity = result.emotion.polarity if result.emotion else None
    intent_label = result.intent.label if result.intent else None

    with cols[0]:
        if primary:
            primary_display = f"{_emotion_emoji(primary)} {_bilingual(primary, _EMOTION_JA)}"
        else:
            primary_display = "感情表現がありません"
        st.metric("主要な感情 (Primary emotion)", primary_display)
    with cols[1]:
        st.metric(
            "極性 (Polarity)",
            f"{_polarity_color(polarity)} {_bilingual(polarity, _POLARITY_JA)}",
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
    tab_chunks, tab_emotion, tab_intent, tab_rag, tab_tokens, tab_json = st.tabs(
        ["Chunks", "Emotion", "Intent", "RAG", "Tokens", "Raw JSON"]
    )

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
