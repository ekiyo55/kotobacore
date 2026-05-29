#!/usr/bin/env python3
"""KotobaCore ベンチマーク (09_評価仕様書 §18 準拠)。

Usage (venv アクティブ状態で):
    cd G:\\マイドライブ\\KotobaCore\\KotobaCore
    python tools/benchmark/run_benchmark.py
    python tools/benchmark/run_benchmark.py --json result.json
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from kotobacore._version import __version__
from kotobacore.analyzer import Analyzer
from kotobacore.compat.karuizawa_compat import KaruizawaTokenizer, TokenMode

# ---------------------------------------------------------------------------
# Ground truth — 09_評価仕様書 §4.2 / §6-§15
# ---------------------------------------------------------------------------

FIXED_CORPUS: list[str] = [
    "OpenAI APIの課金高すぎてしぬw",
    "このアニメ尊すぎて泣いた",
    "もう無理。請求まわりを確認して",
    "今日は新しいプロジェクトがスタート！ワクワクする！",
    "チームメンバーとの初ミーティング。みんな頼もしい！",
    "お昼はいつもの定食屋で。安定の美味しさ。",
    "思ったより難しい課題が...どうしよう。",
    "また仕様変更？さっき決めたばかりなのに...",
    "締め切りが近いのにバグが出た。もう無理かも...",
    "先輩が助けてくれた！なんとか解決できそう！",
    "今日は本当に色々あったけど、良いチームで良かった。",
    "社内FAQをRAG化したい",
    "ChatGPTの回答精度を改善したい",
    "東京都に行った",
]

# KPI1: Emotion Preservation Rate (§6)
# target_surface が result.emotion.expressions[*].text に存在するか
EMOTION_PRESERVATION_CASES: list[tuple[str, str]] = [
    ("OpenAI APIの課金高すぎてしぬw",       "しぬw"),     # slang.csv: exaggeration
    ("このアニメ尊すぎて泣いた",             "泣いた"),    # emotion.csv: moved
    ("うざっ！本当に困る",                   "うざっ"),    # emotion.csv: irritation
    ("もう無理！",                           "もう無理"),  # SNS辞書: sadness (v0.1.5〜「もう無理」は精神的限界=sadness)
    ("無理かも...",                          "無理かも"),  # emotion.csv: refusal
    ("ワクワクする！",                        "ワクワク"),  # emotion.csv: joy
    ("みんな頼もしい！",                      "頼もしい"), # emotion.csv: admiration
    ("どうしよう、どうすれば...",             "どうしよう"), # emotion.csv: anxiety
    ("このアニメ尊すぎて泣いた",             "尊すぎ"),    # emotion.csv / slang.csv: admiration
    ("これ最高！",                           "最高"),      # emotion.csv: joy
    ("最悪な一日だった",                     "最悪"),      # emotion.csv: anger
]

# KPI2: Slang Recognition Rate (§7)
# slang_surface が expressions または chunks に存在するか
SLANG_CASES: list[tuple[str, str]] = [
    ("草",                               "草"),        # slang.csv: joy
    ("OpenAI APIの課金高すぎてしぬw",    "しぬw"),     # slang.csv: exaggeration
    ("それな",                           "それな"),    # slang.csv: agreement
    ("えぐい",                           "えぐい"),    # slang.csv: mixed
    ("このアニメ尊すぎて泣いた",          "尊すぎ"),    # slang.csv: admiration
    ("無理すぎ",                          "無理すぎ"), # slang.csv: refusal
    ("www",                              "www"),       # slang.csv: joy
]

# KPI3: Semantic Chunk Accuracy (§8)
# expected_chunks の各要素が result.chunks[*].text に存在するか
CHUNK_CASES: list[tuple[str, list[str]]] = [
    ("OpenAI APIの課金高すぎてしぬw",      ["OpenAI API", "しぬw"]),
    ("社内FAQをRAG化したい",               ["社内FAQ", "RAG"]),
    ("ChatGPTの回答精度を改善したい",       ["ChatGPT"]),
    ("東京都に行った",                      ["東京都"]),
    ("このアニメ尊すぎて泣いた",            ["尊すぎ"]),
]

# KPI4: RAG Keyword Precision (§9)
# 返却された keyword が relevant に含まれる割合
# relevance 判定: case-insensitive 完全一致 または部分文字列マッチ
RAG_KEYWORD_CASES: list[tuple[str, set[str]]] = [
    (
        "OpenAI APIの課金高すぎ",
        {"OpenAI", "API", "OpenAI API", "課金", "課金高すぎ"},
    ),
    (
        "社内FAQをRAG化したい",
        {"FAQ", "RAG", "社内", "社内FAQ", "したい"},
    ),
    (
        "ChatGPTの回答精度を改善したい",
        {"ChatGPT", "回答", "精度", "改善", "改善したい", "回答精度"},
    ),
]

# KPI5: Intent Classification Accuracy (§10)
# 正解 intent との一致
INTENT_CASES: list[tuple[str, str]] = [
    ("OpenAI APIの課金高すぎてしぬw",            "pricing_complaint"),
    ("もう無理。請求まわりを確認して",             "support_request"),
    ("先輩が助けてくれた！なんとか解決できそう！",  "positive_feedback"),
    ("また仕様変更？さっき決めたばかりなのに...",   "negative_feedback"),
    ("社内FAQをRAG化したい",                      "desire"),
    ("ChatGPTの回答精度を改善したい",              "desire"),
    ("今日は新しいプロジェクトがスタート！ワクワクする！", "positive_feedback"),
    ("チームメンバーとの初ミーティング。みんな頼もしい！", "admiration"),
]

# KPI6: Plutchik Mapping Accuracy (§11)
# primary emotion の plutchik_emotion が acceptable に含まれるか
PLUTCHIK_CASES: list[tuple[str, set[str]]] = [
    ("OpenAI APIの課金高すぎてしぬw",                {"anger", "surprise"}),
    ("このアニメ尊すぎて泣いた",                      {"joy", "trust"}),
    ("もう無理。請求まわりを確認して",                 {"disgust", "anger", "fear", "sadness"}),
    ("今日は新しいプロジェクトがスタート！ワクワクする！", {"joy", "anticipation"}),
    ("先輩が助けてくれた！なんとか解決できそう！",      {"joy", "trust"}),
    ("また仕様変更？さっき決めたばかりなのに...",       {"anger", "surprise", "disgust"}),
]

# JSON Schema 必須キー (§14)
JSON_REQUIRED_KEYS = [
    "meta", "text", "tokens", "semantic_tokens",
    "chunks", "emotion", "intent", "rag", "errors",
]

# 性能目標 (§15)
_PERF_BASE = (
    "日本語意味理解エンジンのKotobaCoreは、形態素解析を基盤として"
    "感情分析・意図分類・RAGキーワード最適化を統合的に提供します。"
    "スラング認識、Plutchik感情モデル、例文ベースのマッチングを組み合わせて"
    "高精度な日本語テキスト解析を実現します。"
)
PERF_SHORT_TEXT     = "最高の一日だった"   # <50 chars
PERF_LONG_TEXT      = _PERF_BASE * 7       # ~980 chars
PERF_SHORT_LIMIT_MS = 50
PERF_LONG_LIMIT_MS  = 300
DICT_LOAD_LIMIT_MS  = 1000

# §18 合格ライン
THRESHOLDS: dict[str, float] = {
    "emotion_preservation_rate":      0.80,
    "slang_recognition_rate":         0.75,
    "semantic_chunk_accuracy":        0.70,
    "rag_keyword_precision":          0.70,
    "intent_classification_accuracy": 0.65,
    "plutchik_mapping_accuracy":      0.75,
    "karuizawa_compatibility_rate":   0.90,
    "json_schema_validity":           1.00,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _expr_surfaces(result) -> set[str]:
    if not result.emotion:
        return set()
    return {e.text for e in result.emotion.expressions}


def _chunk_texts(result) -> set[str]:
    return {c.text for c in result.chunks}


def _recognized(result, surface: str) -> bool:
    return surface in _expr_surfaces(result) or surface in _chunk_texts(result)


def _primary_plutchik(result) -> str | None:
    if not result.emotion or not result.emotion.expressions:
        return None
    best = max(result.emotion.expressions, key=lambda e: e.intensity * e.confidence)
    return best.plutchik_emotion


def _keyword_relevant(keyword: str, relevant: set[str]) -> bool:
    kl = keyword.lower()
    for r in relevant:
        rl = r.lower()
        if kl == rl or kl in rl or rl in kl:
            return True
    return False


# ---------------------------------------------------------------------------
# KPI 計測関数
# ---------------------------------------------------------------------------

def kpi1_emotion_preservation(az: Analyzer) -> tuple[float, list[dict]]:
    details = []
    for text, surface in EMOTION_PRESERVATION_CASES:
        r = az.analyze(text)
        hit = surface in _expr_surfaces(r)
        details.append({"text": text, "surface": surface, "hit": hit})
    return sum(d["hit"] for d in details) / len(details), details


def kpi2_slang_recognition(az: Analyzer) -> tuple[float, list[dict]]:
    details = []
    for text, slang in SLANG_CASES:
        r = az.analyze(text)
        hit = _recognized(r, slang)
        details.append({"text": text, "slang": slang, "hit": hit})
    return sum(d["hit"] for d in details) / len(details), details


def kpi3_chunk_accuracy(az: Analyzer) -> tuple[float, list[dict]]:
    total_exp = total_hit = 0
    details = []
    for text, expected in CHUNK_CASES:
        r = az.analyze(text)
        ct = _chunk_texts(r)
        found = [c for c in expected if c in ct]
        total_exp += len(expected)
        total_hit += len(found)
        details.append({
            "text": text,
            "expected": expected,
            "found": found,
            "accuracy": round(len(found) / len(expected), 3),
        })
    return (total_hit / total_exp if total_exp else 0.0), details


def kpi4_rag_precision(az: Analyzer) -> tuple[float, list[dict]]:
    precisions: list[float] = []
    details = []
    for text, relevant in RAG_KEYWORD_CASES:
        r = az.analyze(text)
        returned = list(r.rag.keywords) if r.rag else []
        if not returned:
            prec = 0.0
        else:
            hits = sum(1 for k in returned if _keyword_relevant(k, relevant))
            prec = hits / len(returned)
        precisions.append(prec)
        details.append({
            "text": text,
            "returned": returned,
            "relevant_sample": sorted(relevant),
            "precision": round(prec, 3),
        })
    return (sum(precisions) / len(precisions) if precisions else 0.0), details


def kpi5_intent_accuracy(az: Analyzer) -> tuple[float, list[dict]]:
    details = []
    for text, expected in INTENT_CASES:
        r = az.analyze(text)
        actual = r.intent.label if r.intent else None
        hit = actual == expected
        details.append({"text": text, "expected": expected, "actual": actual, "hit": hit})
    return sum(d["hit"] for d in details) / len(details), details


def kpi6_plutchik_accuracy(az: Analyzer) -> tuple[float, list[dict]]:
    details = []
    for text, acceptable in PLUTCHIK_CASES:
        r = az.analyze(text)
        plutchik = _primary_plutchik(r)
        hit = (plutchik in acceptable) if plutchik else False
        details.append({
            "text": text,
            "acceptable": sorted(acceptable),
            "actual": plutchik,
            "hit": hit,
        })
    return sum(d["hit"] for d in details) / len(details), details


def kpi7_karuizawa_compat() -> tuple[float, list[dict]]:
    details: list[dict] = []

    def record(name: str, fn):
        try:
            result = fn()
            details.append({"api": name, "ok": True})
            return result
        except Exception as exc:
            details.append({"api": name, "ok": False, "error": str(exc)})
            return None

    t = record("KaruizawaTokenizer", lambda: KaruizawaTokenizer())

    if t is None:
        for name in [
            "tokenize", "TokenMode.A", "TokenMode.B", "TokenMode.C",
            "surface", "part_of_speech", "dictionary_form",
            "normalized_form", "reading_form",
        ]:
            details.append({"api": name, "ok": False, "error": "KaruizawaTokenizer failed"})
    else:
        tokens_c = record("tokenize", lambda: t.tokenize("東京都に行った", TokenMode.C))
        record("TokenMode.A", lambda: t.tokenize("東京都に行った", TokenMode.A))
        record("TokenMode.B", lambda: t.tokenize("東京都に行った", TokenMode.B))
        record("TokenMode.C", lambda: t.tokenize("東京都に行った", TokenMode.C))

        m0 = tokens_c[0] if tokens_c else None
        record("surface",         lambda: m0.surface())
        record("part_of_speech",  lambda: m0.part_of_speech())
        record("dictionary_form", lambda: m0.dictionary_form())
        record("normalized_form", lambda: m0.normalized_form())
        record("reading_form",    lambda: m0.reading_form())

    rate = sum(1 for entry in details if entry["ok"]) / len(details) if details else 0.0
    return rate, details


def kpi8_json_schema(az: Analyzer) -> tuple[float, list[dict]]:
    details = []
    for text in FIXED_CORPUS[:5]:
        r = az.analyze(text)
        d = r.to_dict()
        missing = [k for k in JSON_REQUIRED_KEYS if k not in d]
        details.append({"text": text, "missing": missing, "valid": not missing})
    return sum(1 for entry in details if entry["valid"]) / len(details), details


def kpi9_performance(az: Analyzer) -> dict:
    az.analyze("テスト")  # warm-up (辞書ロード済み状態にする)

    t_short = []
    for _ in range(5):
        t0 = time.perf_counter()
        az.analyze(PERF_SHORT_TEXT)
        t_short.append((time.perf_counter() - t0) * 1000)
    avg_short = sum(t_short) / len(t_short)

    t_long = []
    for _ in range(3):
        t0 = time.perf_counter()
        az.analyze(PERF_LONG_TEXT)
        t_long.append((time.perf_counter() - t0) * 1000)
    avg_long = sum(t_long) / len(t_long)

    t0 = time.perf_counter()
    Analyzer().analyze("テスト")  # 辞書ロード込みの新規インスタンス
    dict_ms = (time.perf_counter() - t0) * 1000

    return {
        "short_text_chars":   len(PERF_SHORT_TEXT),
        "short_text_avg_ms":  round(avg_short, 1),
        "short_text_pass":    avg_short <= PERF_SHORT_LIMIT_MS,
        "long_text_chars":    len(PERF_LONG_TEXT),
        "long_text_avg_ms":   round(avg_long, 1),
        "long_text_pass":     avg_long <= PERF_LONG_LIMIT_MS,
        "dict_load_ms":       round(dict_ms, 1),
        "dict_load_pass":     dict_ms <= DICT_LOAD_LIMIT_MS,
    }


# ---------------------------------------------------------------------------
# メインランナー
# ---------------------------------------------------------------------------

_KPI_DEFS = [
    # (表示ラベル,           スコアキー,                           閾値表示)
    ("KPI1  Emotion Preservation Rate",      "emotion_preservation_rate",      "≥80%"),
    ("KPI2  Slang Recognition Rate",         "slang_recognition_rate",         "≥75%"),
    ("KPI3  Semantic Chunk Accuracy",        "semantic_chunk_accuracy",        "≥70%"),
    ("KPI4  RAG Keyword Precision",          "rag_keyword_precision",          "≥70%"),
    ("KPI5  Intent Classification Accuracy", "intent_classification_accuracy", "≥65%"),
    ("KPI6  Plutchik Mapping Accuracy",      "plutchik_mapping_accuracy",      "≥75%"),
    ("KPI7  Karuizawa Compatibility Rate",   "karuizawa_compatibility_rate",   "≥90%"),
    ("KPI8  JSON Schema Validity",           "json_schema_validity",           "100%"),
]


def run() -> dict:
    print("KotobaCore Benchmark\n")
    az = Analyzer()

    score_map: dict[str, float] = {}
    detail_map: dict[str, list] = {}

    runners = [
        ("KPI1  Emotion Preservation Rate",      lambda: kpi1_emotion_preservation(az), "emotion_preservation_rate"),
        ("KPI2  Slang Recognition Rate",         lambda: kpi2_slang_recognition(az),    "slang_recognition_rate"),
        ("KPI3  Semantic Chunk Accuracy",        lambda: kpi3_chunk_accuracy(az),        "semantic_chunk_accuracy"),
        ("KPI4  RAG Keyword Precision",          lambda: kpi4_rag_precision(az),         "rag_keyword_precision"),
        ("KPI5  Intent Classification Accuracy", lambda: kpi5_intent_accuracy(az),       "intent_classification_accuracy"),
        ("KPI6  Plutchik Mapping Accuracy",      lambda: kpi6_plutchik_accuracy(az),     "plutchik_mapping_accuracy"),
        ("KPI7  Karuizawa Compatibility Rate",   kpi7_karuizawa_compat,                  "karuizawa_compatibility_rate"),
        ("KPI8  JSON Schema Validity",           lambda: kpi8_json_schema(az),           "json_schema_validity"),
    ]

    for label, fn, key in runners:
        print(f"  {label}...", end=" ", flush=True)
        score, details = fn()
        score_map[key] = score
        detail_map[key] = details
        print(f"{score:.0%}")

    print("  KPI9  Processing Latency...", end=" ", flush=True)
    perf = kpi9_performance(az)
    print("done")

    # 合否判定
    kpi_pass = all(score_map[k] >= THRESHOLDS[k] for k in THRESHOLDS)
    perf_pass = perf["short_text_pass"] and perf["long_text_pass"] and perf["dict_load_pass"]
    all_pass = kpi_pass and perf_pass

    # レポート出力
    print()
    print("=" * 68)
    print(f"KotobaCore v{__version__} Benchmark Report")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 68)
    for label, key, threshold in _KPI_DEFS:
        score = score_map[key]
        status = "PASS" if score >= THRESHOLDS[key] else "FAIL"
        print(f"  {label:<44} {score:5.0%}  ({threshold})  [{status}]")

    def _pf(ok: bool) -> str:
        return "PASS" if ok else "FAIL"

    print()
    print("  KPI9  Processing Latency")
    print(f"    Short ({perf['short_text_chars']:4d} chars): {perf['short_text_avg_ms']:7.1f} ms  (≤{PERF_SHORT_LIMIT_MS}ms)   [{_pf(perf['short_text_pass'])}]")
    print(f"    Long  ({perf['long_text_chars']:4d} chars): {perf['long_text_avg_ms']:7.1f} ms  (≤{PERF_LONG_LIMIT_MS}ms)  [{_pf(perf['long_text_pass'])}]")
    print(f"    Dict load:          {perf['dict_load_ms']:7.1f} ms  (≤{DICT_LOAD_LIMIT_MS}ms) [{_pf(perf['dict_load_pass'])}]")

    print()
    print(f"  Overall: [{'PASS' if all_pass else 'FAIL'}]")
    print("=" * 68)

    # FAIL 詳細
    failed_kpis = [
        (label, key)
        for label, key, _ in _KPI_DEFS
        if score_map[key] < THRESHOLDS[key]
    ]
    if failed_kpis:
        print("\n--- FAIL 詳細 ---")
        for label, key in failed_kpis:
            print(f"\n{label}:")
            for entry in detail_map[key]:
                if not entry.get("hit", True):
                    for k, v in entry.items():
                        if k != "hit":
                            print(f"    {k}: {v}")
                    print(f"    → FAIL")

    return {
        "meta": {
            "kotobacore_version": __version__,
            "date": datetime.now().isoformat(),
            "python_version": sys.version.split()[0],
        },
        "scores": {k: round(v, 4) for k, v in score_map.items()},
        "performance": perf,
        "passed": all_pass,
        "details": detail_map,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="KotobaCore ベンチマーク (09_評価仕様書 §18 準拠)")
    parser.add_argument("--json", metavar="FILE", help="結果を JSON ファイルに保存")
    args = parser.parse_args()

    report = run()

    if args.json:
        out = Path(args.json)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nReport saved → {out}")


if __name__ == "__main__":
    main()
