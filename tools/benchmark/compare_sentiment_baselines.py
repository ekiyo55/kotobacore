"""Sentiment / emotion baseline comparison (v1.0 完成条件「感情辞書ライブラリとの比較」).

Compares KotobaCore with existing Japanese sentiment / emotion libraries on the
human-annotated set (tools/quality_test/annotated/annotated_v1.jsonl), using the
same scoring as tools/quality_test/run_annotated_eval.py:

- polarity accuracy over all items: gold = majority polarity of the annotated
  sentiment expressions (None when the sentence carries no sentiment);
  a prediction is correct when it equals the gold polarity, or when gold is
  None and the tool says neutral / nothing;
- polarity accuracy on polarized items only (gold positive / negative) — fairer
  for binary classifiers that never answer "neutral";
- emotion accuracy on items with a gold emotion label: correct when the tool's
  primary emotion is one of the gold labels (ML-Ask's 10 emotions are mapped
  onto the gold taxonomy, see ML_ASK_MAP; the mapping is deliberately generous);
- canary false-positive rate on ``expected_no_emotion`` items;
- ms per sentence (warm, best of 3 passes).

Baselines (each optional — reported as "not run" when the import fails):
- oseti   : 日本語評価極性辞書 (東北大 乾・岡崎研) + MeCab, sentence scores in [-1, 1]
- pymlask : ML-Ask (Ptaszynski) 感情辞書 + MeCab, 10 emotions + orientation
- asari   : 機械学習 (TF-IDF + 線形分類器) の positive / negative 二値

They need MeCab (mecab-python3 + ipadic wheel); on Windows the DLL does not load,
so this script is meant to run on Linux (mooma) in a throw-away venv.

Usage: python tools/benchmark/compare_sentiment_baselines.py [--md OUT] [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from kotobacore import Analyzer
from kotobacore._version import __version__

ANNOTATED = ROOT / "tools" / "quality_test" / "annotated" / "annotated_v1.jsonl"

# ML-Ask emotion -> gold labels it may legitimately stand for (generous, many-to-many).
ML_ASK_MAP: dict[str, set[str]] = {
    "yorokobi": {"joy", "moved", "admiration"},
    "ikari": {"anger", "irritation"},
    "aware": {"sadness"},
    "kowagari": {"anxiety", "fear"},
    "haji": {"shame"},
    "suki": {"joy", "admiration", "trust"},
    "iya": {"disgust", "irritation", "refusal"},
    "takaburi": {"anticipation", "surprise"},
    "yasu": {"trust", "relief"},
    "odoroki": {"surprise"},
}


def _gold_polarity(item: dict) -> str | None:
    pols = [s["polarity"] for s in item.get("sentiment") or []]
    return Counter(pols).most_common(1)[0][0] if pols else None


# ----------------------------------------------------------------- tools
class Tool:
    name: str
    note: str
    has_emotion = False

    def polarity(self, text: str) -> str | None:  # positive / negative / neutral / None
        raise NotImplementedError

    def emotions(self, text: str) -> set[str]:  # gold-taxonomy labels the tool asserts (empty = none)
        return set()


class KotobaCoreTool(Tool):
    has_emotion = True

    def __init__(self) -> None:
        self.an = Analyzer()
        nrc = len(self.an._get_bundle().external_emotion)  # NRC lexicon is license-restricted: only present when an external dic/ is found
        self.name = f"KotobaCore {__version__}" + (f" (+NRC {nrc} 語)" if nrc else " (同梱辞書のみ = pip install の状態)")
        self.note = "辞書同梱 CSV、依存ゼロ。宛先付き (target / holder / about) だが本表は文単位のみ"

    def _run(self, text: str):
        return self.an.analyze(text)

    def polarity(self, text: str) -> str | None:
        r = self._run(text)
        return r.sentiment.polarity if r.sentiment else None

    def emotions(self, text: str) -> set[str]:
        r = self._run(text)
        return {r.emotion.primary} if r.emotion and r.emotion.primary else set()


class OsetiTool(Tool):
    def __init__(self) -> None:
        import ipadic
        import oseti

        self.name = "oseti 0.4 (評価極性辞書 + MeCab/ipadic)"
        self.note = "文ごとのスコア [-1, 1] の平均符号。0 / 該当なし = neutral"
        self.an = oseti.Analyzer(mecab_args=ipadic.MECAB_ARGS)

    def polarity(self, text: str) -> str | None:
        scores = self.an.analyze(text)
        if not scores:
            return "neutral"
        mean = sum(scores) / len(scores)
        return "positive" if mean > 0 else "negative" if mean < 0 else "neutral"


class MLAskTool(Tool):
    has_emotion = True

    def __init__(self) -> None:
        import ipadic
        import mlask

        self.name = "pymlask 0.3 (ML-Ask 感情辞書 + MeCab/ipadic)"
        self.note = "orientation → 極性、representative 感情を ML_ASK_MAP で gold 体系に写像"
        self.an = mlask.MLAsk(ipadic.MECAB_ARGS)

    def polarity(self, text: str) -> str | None:
        r = self.an.analyze(text)
        if not r.get("emotion"):
            return "neutral"
        o = r.get("orientation") or "NEUTRAL"
        return {"POSITIVE": "positive", "NEGATIVE": "negative"}.get(o, "neutral")

    def emotions(self, text: str) -> set[str]:
        r = self.an.analyze(text)
        if not r.get("emotion"):
            return set()
        rep = r.get("representative")
        keys = [rep[0]] if rep else list(r["emotion"].keys())
        out: set[str] = set()
        for k in keys:
            out |= ML_ASK_MAP.get(k, set())
        return out


class AsariTool(Tool):
    def __init__(self, neutral_below: float | None = None) -> None:
        from asari.api import Sonar

        self.neutral_below = neutral_below
        self.name = "asari 0.2 (TF-IDF + 線形分類、二値)" + (f" / 確信度 < {neutral_below} → neutral" if neutral_below else "")
        self.note = "positive / negative しか返さない" + ("ので確信度で neutral を補う" if neutral_below else "")
        self.an = Sonar()

    def polarity(self, text: str) -> str | None:
        r = self.an.ping(text)
        top = r["top_class"]
        conf = max(c["confidence"] for c in r["classes"])
        if self.neutral_below and conf < self.neutral_below:
            return "neutral"
        return top


# ----------------------------------------------------------------- evaluation
def evaluate(tool: Tool, items: list[dict]) -> dict:
    pol_n = pol_ok = polz_n = polz_ok = 0
    emo_n = emo_ok = can_n = can_fp = 0
    confusion: Counter[str] = Counter()
    failures: list[dict] = []
    for it in items:
        text = it["text"]
        gp = _gold_polarity(it)
        sp = tool.polarity(text)
        ok = (gp == sp) or (gp is None and sp in (None, "neutral"))
        pol_n += 1
        pol_ok += int(ok)
        confusion[f"{gp}->{sp}"] += 1
        if gp is not None:
            polz_n += 1
            polz_ok += int(gp == sp)
        if not ok and len(failures) < 40:
            failures.append({"id": it["id"], "kind": "polarity", "gold": gp, "sys": sp, "text": text})
        if tool.has_emotion:
            gold = [e["label"] for e in it.get("emotion") or []]
            pred = tool.emotions(text)
            if it.get("expected_no_emotion"):
                can_n += 1
                can_fp += int(bool(pred))
            elif gold:
                emo_n += 1
                emo_ok += int(bool(pred & set(gold)))
    # speed: best of 3 warm passes
    best = float("inf")
    for _ in range(3):
        t0 = time.perf_counter()
        for it in items:
            tool.polarity(it["text"])
        best = min(best, (time.perf_counter() - t0) / len(items) * 1000)

    def pct(a: int, b: int) -> float | None:
        return round(a / b * 100, 1) if b else None

    return {
        "tool": tool.name,
        "note": tool.note,
        "polarity_acc_all": pct(pol_ok, pol_n),
        "polarity_n": pol_n,
        "polarity_acc_polarized": pct(polz_ok, polz_n),
        "polarized_n": polz_n,
        "emotion_acc": pct(emo_ok, emo_n) if tool.has_emotion else None,
        "emotion_n": emo_n if tool.has_emotion else None,
        "canary_fp": pct(can_fp, can_n) if tool.has_emotion else None,
        "canary_n": can_n if tool.has_emotion else None,
        "ms_per_sentence": round(best, 3),
        "confusion": dict(confusion),
        "failures": failures,
    }


def to_markdown(results: list[dict], not_run: list[tuple[str, str]], n_items: int) -> str:
    lines = [
        f"# Sentiment / emotion baseline comparison — KotobaCore {__version__}",
        "",
        f"gold: 人手アノテーション v1 {n_items} 文 (5 ジャンル)。極性 = 表現の多数決 (無し = None)、感情 = gold ラベルのいずれかに一致で正解。速度 = 文あたり ms (warm, best of 3)",
        "",
        "| tool | polarity acc (all) | polarity acc (polarized only) | emotion acc | canary FP | ms/sentence | note |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        emo = f"{r['emotion_acc']}% (n={r['emotion_n']})" if r["emotion_acc"] is not None else "—"
        can = f"{r['canary_fp']}% (n={r['canary_n']})" if r["canary_fp"] is not None else "—"
        lines.append(
            f"| {r['tool']} | {r['polarity_acc_all']}% (n={r['polarity_n']}) | {r['polarity_acc_polarized']}% (n={r['polarized_n']}) | {emo} | {can} | {r['ms_per_sentence']} | {r['note']} |"
        )
    if not_run:
        lines += ["", "## not run", ""] + [f"- {name}: {reason}" for name, reason in not_run]
    lines += [
        "",
        "注: gold の極性は「評価表現のある文だけ」に付いている (残りは None = neutral 扱い)。二値分類器は None の文で必ず外すので、polarized only 列も併記。",
        "ML-Ask の 10 感情は gold 体系 (Plutchik 8 + irritation / anxiety / admiration / moved / refusal / agreement) と一対一でないため、ML_ASK_MAP の多対多写像で「いずれか一致」を正解にしている (ML-Ask 有利)。",
        "本表は文単位の極性・主感情のみ。KotobaCore の宛先付き評価 (target / holder / about) は他ライブラリに対応物が無く比較対象外。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotated", default=str(ANNOTATED))
    ap.add_argument("--md")
    ap.add_argument("--json")
    args = ap.parse_args()
    warnings.filterwarnings("ignore")
    items = [json.loads(line) for line in Path(args.annotated).read_text(encoding="utf-8").splitlines() if line.strip()]

    tools: list[Tool] = [KotobaCoreTool()]
    not_run: list[tuple[str, str]] = []
    for name, factory in (
        ("oseti", OsetiTool),
        ("pymlask", MLAskTool),
        ("asari", AsariTool),
        ("asari (neutral < 0.75)", lambda: AsariTool(neutral_below=0.75)),
    ):
        try:
            tools.append(factory())
        except Exception as exc:  # noqa: BLE001 - optional baselines
            not_run.append((name, f"{type(exc).__name__}: {str(exc)[:120]}"))

    results = [evaluate(t, items) for t in tools]
    md = to_markdown(results, not_run, len(items))
    print(md)
    if args.md:
        Path(args.md).write_text(md, encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps({"kotobacore": __version__, "items": len(items), "results": results, "not_run": not_run}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
