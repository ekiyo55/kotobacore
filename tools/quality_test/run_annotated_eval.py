"""Evaluate KotobaCore against the human-annotated sentence set (FR-100 / FR-102).

Input: JSONL, one object per line (AI draft = annotated_v1_draft.jsonl, reviewed = annotated_v1.jsonl):

    {"id", "genre", "text", "tokens" | null, "entities": [{"surface","type"}],
     "sentiment": [{"target","polarity"}], "emotion": [{"holder","about","label"}],
     "intent", "expected_no_emotion", "note"}

Metrics
- Tokenization: boundary precision / recall / F1 (items with ``tokens``)
- Entity: surface-level and surface+type precision / recall / F1
- Sentiment: polarity accuracy (gold majority polarity vs Analyzer.sentiment)
- Emotion: primary-label accuracy on items with a gold label; canary false-positive
  rate on ``expected_no_emotion`` items
- Intent: accuracy (gold ``none`` ⇔ Analyzer ``unknown``/None)

Usage:
    python tools/quality_test/run_annotated_eval.py [--jsonl FILE] [--json OUT] [--md OUT]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kotobacore import Analyzer
from kotobacore._version import __version__

DEFAULT_JSONL = Path(__file__).resolve().parent / "annotated" / "annotated_v1.jsonl"


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4), "tp": tp, "fp": fp, "fn": fn}


def _boundaries(tokens: list[str]) -> set[int]:
    out: set[int] = set()
    pos = 0
    for t in tokens[:-1]:
        pos += len(t)
        out.add(pos)
    return out


def _gold_polarity(item: dict) -> str | None:
    pols = [s["polarity"] for s in item.get("sentiment") or []]
    if not pols:
        return None
    c = Counter(pols)
    return c.most_common(1)[0][0]


def evaluate(items: list[dict], analyzer: Analyzer) -> dict:
    tok = {"tp": 0, "fp": 0, "fn": 0, "n": 0}
    ent_surface = {"tp": 0, "fp": 0, "fn": 0}
    ent_typed = {"tp": 0, "fp": 0, "fn": 0}
    sent = {"correct": 0, "n": 0, "confusion": defaultdict(int)}
    emo = {"correct": 0, "n": 0, "canary_fp": 0, "canary_n": 0}
    intent = {"correct": 0, "n": 0, "confusion": defaultdict(int)}
    target = {"correct": 0, "n": 0}
    per_genre: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    times: list[float] = []
    failures: list[dict] = []

    for item in items:
        text = item["text"]
        genre = item.get("genre", "?")
        t0 = time.perf_counter()
        r = analyzer.analyze(text)
        times.append((time.perf_counter() - t0) * 1000)

        # --- tokenization (only when the text survives normalization unchanged)
        gold_tokens = item.get("tokens")
        if gold_tokens and r.text.normalized == text:
            gold_b = _boundaries(gold_tokens)
            sys_b = {t.end for t in r.tokens[:-1]}
            tp = len(gold_b & sys_b)
            tok["tp"] += tp
            tok["fp"] += len(sys_b - gold_b)
            tok["fn"] += len(gold_b - sys_b)
            tok["n"] += 1
            if gold_b != sys_b:
                failures.append({"id": item["id"], "kind": "tokens", "gold": gold_tokens,
                                 "sys": [t.surface for t in r.tokens]})

        # --- entities (v0.4: Entity list — dictionary / pattern / time / quantity)
        gold_e = {(e["surface"], e["type"]) for e in item.get("entities") or []}
        sys_e = {(en.surface, en.type) for en in r.entities}
        gs, ss = {g[0] for g in gold_e}, {s[0] for s in sys_e}
        ent_surface["tp"] += len(gs & ss)
        ent_surface["fp"] += len(ss - gs)
        ent_surface["fn"] += len(gs - ss)
        ent_typed["tp"] += len(gold_e & sys_e)
        ent_typed["fp"] += len(sys_e - gold_e)
        ent_typed["fn"] += len(gold_e - sys_e)

        # --- sentiment
        gp = _gold_polarity(item)
        sp = r.sentiment.polarity if r.sentiment else None
        sent["n"] += 1
        ok = (gp == sp) or (gp is None and sp in (None, "neutral"))
        sent["correct"] += int(ok)
        sent["confusion"][f"{gp}->{sp}"] += 1
        per_genre[genre]["sentiment_n"] += 1
        per_genre[genre]["sentiment_ok"] += int(ok)
        if not ok:
            failures.append({"id": item["id"], "kind": "sentiment", "gold": gp, "sys": sp, "text": text})

        # --- sentiment target (宛先付き評価, FR-052): gold target vs system target_text
        gold_targets = [s["target"] for s in item.get("sentiment") or [] if s.get("target")]
        if gold_targets and r.sentiment and r.sentiment.expressions:
            target["n"] += 1
            sys_targets = {e.target_text for e in r.sentiment.expressions if e.target_text}
            ok = any(gt in sys_targets or any(st and (st in gt or gt in st) for st in sys_targets) for gt in gold_targets)
            target["correct"] += int(ok)
            if not ok:
                failures.append({"id": item["id"], "kind": "target", "gold": gold_targets, "sys": sorted(sys_targets), "text": text})

        # --- emotion
        gold_labels = [e["label"] for e in item.get("emotion") or []]
        primary = r.emotion.primary if r.emotion else None
        if item.get("expected_no_emotion"):
            emo["canary_n"] += 1
            if primary is not None:
                emo["canary_fp"] += 1
                failures.append({"id": item["id"], "kind": "canary", "sys": primary, "text": text})
        elif gold_labels:
            emo["n"] += 1
            ok = primary in gold_labels
            emo["correct"] += int(ok)
            per_genre[genre]["emotion_n"] += 1
            per_genre[genre]["emotion_ok"] += int(ok)
            if not ok:
                failures.append({"id": item["id"], "kind": "emotion", "gold": gold_labels, "sys": primary, "text": text})

        # --- intent
        gi = item.get("intent") or "none"
        si = r.intent.label if r.intent else None
        if si in (None, "unknown"):
            si = "none"
        intent["n"] += 1
        ok = gi == si
        intent["correct"] += int(ok)
        intent["confusion"][f"{gi}->{si}"] += 1
        per_genre[genre]["intent_n"] += 1
        per_genre[genre]["intent_ok"] += int(ok)

    times.sort()

    def pct(a: int, b: int) -> float:
        return round(100.0 * a / b, 1) if b else 0.0

    return {
        "version": __version__,
        "items": len(items),
        "tokenization": {**_prf(tok["tp"], tok["fp"], tok["fn"]), "items": tok["n"]},
        "entity_surface": _prf(**ent_surface),
        "entity_typed": _prf(**ent_typed),
        "sentiment": {"accuracy": pct(sent["correct"], sent["n"]), "n": sent["n"],
                      "confusion": dict(sorted(sent["confusion"].items()))},
        "emotion": {"accuracy": pct(emo["correct"], emo["n"]), "n": emo["n"],
                    "canary_false_positive": pct(emo["canary_fp"], emo["canary_n"]), "canary_n": emo["canary_n"]},
        "intent": {"accuracy": pct(intent["correct"], intent["n"]), "n": intent["n"],
                   "confusion": dict(sorted(intent["confusion"].items()))},
        "sentiment_target": {"accuracy": pct(target["correct"], target["n"]), "n": target["n"]},
        "per_genre": {
            g: {
                "sentiment_acc": pct(v["sentiment_ok"], v["sentiment_n"]),
                "emotion_acc": pct(v["emotion_ok"], v["emotion_n"]),
                "intent_acc": pct(v["intent_ok"], v["intent_n"]),
            }
            for g, v in sorted(per_genre.items())
        },
        "timing_ms": {"mean": round(sum(times) / len(times), 2) if times else 0.0,
                      "p95": round(times[int(len(times) * 0.95) - 1], 2) if times else 0.0},
        "failures": failures,
    }


def to_markdown(res: dict) -> str:
    lines = [f"# Annotated eval — KotobaCore {res['version']} ({res['items']} items)", ""]
    t = res["tokenization"]
    lines.append(f"| Tokenization ({t['items']} items) | P {t['precision']} / R {t['recall']} / F1 {t['f1']} |")
    for k in ("entity_surface", "entity_typed"):
        e = res[k]
        lines.append(f"| {k} | P {e['precision']} / R {e['recall']} / F1 {e['f1']} |")
    lines.append(f"| Sentiment accuracy | {res['sentiment']['accuracy']}% (n={res['sentiment']['n']}) |")
    lines.append(f"| Emotion accuracy | {res['emotion']['accuracy']}% (n={res['emotion']['n']}), canary FP {res['emotion']['canary_false_positive']}% (n={res['emotion']['canary_n']}) |")
    lines.append(f"| Intent accuracy | {res['intent']['accuracy']}% (n={res['intent']['n']}) |")
    lines.append(f"| Sentiment target accuracy | {res['sentiment_target']['accuracy']}% (n={res['sentiment_target']['n']}) |")
    lines.append(f"| Timing | mean {res['timing_ms']['mean']} ms / p95 {res['timing_ms']['p95']} ms |")
    lines += ["", "## Per genre", "", "| genre | sentiment | emotion | intent |", "|---|---|---|---|"]
    for g, v in res["per_genre"].items():
        lines.append(f"| {g} | {v['sentiment_acc']}% | {v['emotion_acc']}% | {v['intent_acc']}% |")
    lines += ["", f"## Failures ({len(res['failures'])})", ""]
    for f in res["failures"][:200]:
        lines.append(f"- `{f['id']}` {f['kind']}: gold={f.get('gold')} sys={f.get('sys')} {f.get('text', '')}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jsonl", default=str(DEFAULT_JSONL))
    ap.add_argument("--json", metavar="FILE")
    ap.add_argument("--md", metavar="FILE")
    args = ap.parse_args()

    items = [json.loads(line) for line in Path(args.jsonl).read_text(encoding="utf-8").splitlines() if line.strip()]
    res = evaluate(items, Analyzer(reference_date=_dt.date(2026, 9, 8)))
    summary = {k: v for k, v in res.items() if k != "failures"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"failures: {len(res['failures'])}")
    if args.json:
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.md:
        Path(args.md).write_text(to_markdown(res), encoding="utf-8")


if __name__ == "__main__":
    main()
