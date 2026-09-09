"""Which queries want a lexical-heavy hybrid (large α) and which an embedding-heavy one?

Reads the candidate caches written by tune_hybrid_rerank.py (tune_syn.pkl /
tune_real.pkl: BM25-normalized + cosine-normalized scores of the top-50 ∪ top-50
per question) and, for every α in a grid, computes the reciprocal rank of the
gold chunk in the fused order (constraint-filter bonus as in run_embed_eval).

The per-question RR curves are then grouped by
  - gold question type (the eval label)          → is "howto" really the problem?
  - predicted intent (modules.intent)           → can KotobaCore see it at query time?
  - lexical anchors in the query (ASCII identifiers, product codes, digits)
  - query length (tokens)
so a query-time α policy can be chosen on synthetic 1-80, checked on 81-200,
and applied once to the real corpus.

Run inside the kotobacore-embed venv after tune_hybrid_rerank.py:
  python tools/rag_eval/analyze_alpha_by_query.py --md OUT

NOTE: the tune_*.pkl caches store chunk indices — regenerate them (delete and
rerun tune_hybrid_rerank.py) after any chunker change.
"""

from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_embed_eval as E  # noqa: E402
import run_rag_eval as R  # noqa: E402
from kotobacore.modules.intent import classify_query_intent  # noqa: E402
from kotobacore.rag.features import hybrid_alpha, query_lexical_anchors  # noqa: E402

ALPHAS = [round(a, 2) for a in np.arange(0.0, 1.01, 0.1)]
PRIVATE = Path("G:/マイドライブ/KotobaCore/rag_eval_private")
_ASCII_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.\-/]{2,}")


def rr_curve(item: dict) -> np.ndarray | None:
    rows = item["rows"]
    if not item["has_gold"] or not any(r["gold"] for r in rows):
        return None
    bn = np.array([r["bn"] for r in rows]); en = np.array([r["en"] for r in rows])
    gold = np.array([r["gold"] for r in rows]); bonus = np.array([1000.0 if r["in_mask"] else 0.0 for r in rows])
    out = np.zeros(len(ALPHAS))
    for k, a in enumerate(ALPHAS):
        s = a * bn + (1 - a) * en + bonus
        gbest = s[gold].max()
        pos = int((s > gbest).sum())
        out[k] = 1.0 / (pos + 1) if pos < 10 else 0.0
    return out


def _margins(item: dict) -> tuple[float, float]:
    """Peakedness of each ranking over the candidate set: 1 − (second-highest normalized score).
    A sharply peaked BM25 (one chunk holds the rare terms) is worth trusting more."""
    bn = sorted((r["bn"] for r in item["rows"]), reverse=True)
    en = sorted((r["en"] for r in item["rows"]), reverse=True)
    mb = 1.0 - (bn[1] if len(bn) > 1 else 0.0)
    me = 1.0 - (en[1] if len(en) > 1 else 0.0)
    return mb, me


def load(name: str, qfile: Path) -> list[dict]:
    items = pickle.loads((E.DEFAULT_CACHE / name).read_bytes())
    qs = {json.loads(l)["qid"]: json.loads(l) for l in qfile.read_text(encoding="utf-8").splitlines() if l.strip()}
    analyzer = R.Analyzer(reference_date=R.REF_DATE)
    out = []
    for it in items:
        q = qs[it["qid"]]
        curve = rr_curve(it)
        if curve is None:
            continue
        qir = analyzer.analyze_query(q["question"])
        intent, _ = classify_query_intent(q["question"])
        anchors = query_lexical_anchors(qir)
        mb, me = _margins(it)
        out.append({
            "qid": it["qid"], "question": q["question"], "type": q["type"], "lexical": q["lexical"], "intent": intent,
            "anchors": anchors, "has_ascii": bool(_ASCII_ID.search(q["question"])), "n_tokens": len(qir.keywords),
            "has_expansion": bool(qir.expanded_terms), "margin_b": mb, "margin_e": me,
            "margin_bin": f"{'b' if mb > me else 'e'}{abs(mb - me) >= 0.1 and '+' or '~'}",
            "policy_alpha": hybrid_alpha(qir), "curve": curve,
        })
    return out


def _snap(a: float) -> float:
    return min(ALPHAS, key=lambda x: abs(x - a))


def policies() -> dict[str, callable]:
    """Candidate query-time α policies. Each maps an analysed item → α."""
    out: dict[str, callable] = {"fixed_0.3": lambda it: 0.3, "fixed_0.4": lambda it: 0.4}
    for ah in (0.5, 0.6, 0.7, 0.8):
        out[f"intent_howto→{ah}"] = lambda it, ah=ah: ah if it["intent"] in ("how_to", "procedure") else 0.3
    for k in (0.5, 1.0, 1.5, 2.0):
        out[f"margin_k{k}"] = lambda it, k=k: _snap(min(0.8, max(0.1, 0.3 + k * (it["margin_b"] - it["margin_e"]))))
    for k in (1.0, 1.5):
        out[f"margin_k{k}+howto0.6"] = lambda it, k=k: _snap(min(0.8, max(0.1, (0.6 if it["intent"] in ("how_to", "procedure") else 0.3) + k * (it["margin_b"] - it["margin_e"]))))
    out["expansion→0.2"] = lambda it: 0.2 if it["has_expansion"] else 0.4
    return out


def group_table(items: list[dict], key: str) -> list[tuple[str, int, list[float], float, float]]:
    groups: dict[str, list[np.ndarray]] = defaultdict(list)
    for it in items:
        groups[str(it[key])].append(it["curve"])
    rows = []
    for g, curves in sorted(groups.items()):
        m = np.mean(curves, axis=0)
        best = ALPHAS[int(np.argmax(m))]
        rows.append((g, len(curves), [round(float(x), 3) for x in m], best, round(float(m.max() - m[ALPHAS.index(0.3)]), 3)))
    return rows


def policy_mrr(items: list[dict], alpha_of) -> float:
    return float(np.mean([it["curve"][ALPHAS.index(round(alpha_of(it), 2))] for it in items]))


def fmt_table(title: str, rows) -> list[str]:
    lines = [f"### {title}", "", "| group | n | " + " | ".join(f"α{a}" for a in ALPHAS) + " | best α | gain vs 0.3 |", "|---|---|" + "---|" * (len(ALPHAS) + 2)]
    for g, n, curve, best, gain in rows:
        lines.append(f"| {g} | {n} | " + " | ".join(f"{x:.3f}" for x in curve) + f" | {best} | {gain:+.3f} |")
    return lines + [""]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", metavar="FILE")
    ap.add_argument("--json", metavar="FILE")
    args = ap.parse_args()
    syn = load("tune_syn.pkl", R.HERE / "data" / "rag_questions_200.jsonl")
    real = load("tune_real.pkl", PRIVATE / "questions_real.jsonl")
    sets = {"syn_train_1_80": [x for x in syn if int(x["qid"].lstrip("q")) <= 80] if syn and syn[0]["qid"].startswith("q") else syn[:80],
            "syn_val_81_200": [x for x in syn if int(x["qid"].lstrip("q")) > 80] if syn and syn[0]["qid"].startswith("q") else syn[80:],
            "real_120": real}
    lines = ["# Hybrid α by query — which queries want lexical vs. embedding", ""]
    summary = {}
    for name, items in sets.items():
        lines += [f"## {name} (n={len(items)})", ""]
        overall = np.mean([it["curve"] for it in items], axis=0)
        lines += ["overall MRR by α: " + ", ".join(f"α{a}={m:.3f}" for a, m in zip(ALPHAS, overall)), ""]
        for key, title in (("type", "by gold question type"), ("intent", "by predicted intent"), ("has_ascii", "by ASCII identifier in query"),
                           ("anchors", "by lexical anchors (features.query_lexical_anchors)"), ("lexical", "by lexical relation"),
                           ("has_expansion", "by synonym expansion available"), ("margin_bin", "by score peakedness (b=BM25 sharper, e=embedding sharper, +=gap≥0.1)")):
            lines += fmt_table(title, group_table(items, key))
        fixed = {a: round(float(overall[ALPHAS.index(a)]), 4) for a in (0.3, 0.4, 0.5)}
        pol = round(policy_mrr(items, lambda it: it["policy_alpha"]), 4)
        oracle_type = {g: b for g, _n, _c, b, _g in group_table(items, "type")}
        oracle = round(policy_mrr(items, lambda it, o=oracle_type: o[it["type"]]), 4)
        lines += [f"fixed α: {fixed} | **policy hybrid_alpha(): {pol}** | oracle-by-gold-type: {oracle}", ""]
        summary[name] = {"fixed": fixed, "policy": pol}
        # the worst policy misses: questions where the policy α loses ≥0.3 RR vs. the best α
        misses = sorted(items, key=lambda it: -(it["curve"].max() - it["curve"][ALPHAS.index(round(it["policy_alpha"], 2))]))[:8]
        lines += ["policy misses (question / type / intent / anchors / policy α / RR@policy → best α RR):", ""]
        for it in misses:
            k = ALPHAS.index(round(it["policy_alpha"], 2))
            lines.append(f"- {it['question']} / {it['type']} / {it['intent']} / {it['anchors']} / α={it['policy_alpha']} / {it['curve'][k]:.2f} → α{ALPHAS[int(np.argmax(it['curve']))]} {it['curve'].max():.2f}")
        lines.append("")
    # ---- policy comparison: choose on syn_train, check on syn_val, apply once to real
    pols = policies()
    lines += ["## α policies (MRR; choose on syn_train_1_80 → check syn_val_81_200 → real_120 once)", "",
              "| policy | " + " | ".join(sets) + " | howto(real) |", "|---|" + "---|" * (len(sets) + 1)]
    ptab = {}
    for name, fn in pols.items():
        row = {s: round(policy_mrr(items, fn), 4) for s, items in sets.items()}
        row["howto_real"] = round(policy_mrr([x for x in sets["real_120"] if x["type"] == "howto"], fn), 4)
        ptab[name] = row
        lines.append(f"| {name} | " + " | ".join(f"{row[s]:.4f}" for s in sets) + f" | {row['howto_real']:.4f} |")
    lines.append("")
    summary["policies"] = ptab
    text = "\n".join(lines)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.md:
        Path(args.md).write_text(text, encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
