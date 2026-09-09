"""Rerank feature ablation on the cached hybrid candidates (old features vs. current code).

tune_hybrid_rerank.py caches, per question, the BM25 ∪ embedding top-50 candidates
with their normalized scores and the rerank features *as computed at cache time*.
This tool rebuilds the chunks with the current code, recomputes rerank_features
for the same candidates, and reports hybrid(α)+rerank MRR for

  cached features  (what the code produced when the cache was written)
  current features (the code under test)
  current features × intent_match weight grid   (chosen on syn 1-80 → syn 81-200 → real once)

overall and by question type / predicted intent, plus the lexical path
(BM25 top-20 → rerank with DEFAULT_WEIGHTS) old vs. new.

Run inside the kotobacore-embed venv (numpy) after tune_hybrid_rerank.py:
  python tools/rag_eval/rerank_ablation.py --md OUT [--json OUT]

NOTE: the caches store chunk *indices*. After any chunker change (v0.5.4 fences /
numbered lists) delete rag_eval_private/cache/tune_*.pkl and rerun
tune_hybrid_rerank.py first, otherwise the rows point at the wrong chunks.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_embed_eval as E  # noqa: E402
import run_rag_eval as R  # noqa: E402
from kotobacore._version import __version__  # noqa: E402
from kotobacore.rag.features import DEFAULT_WEIGHTS, HYBRID_WEIGHTS, rerank_features, rerank_score  # noqa: E402

PRIVATE = Path("G:/マイドライブ/KotobaCore/rag_eval_private")
ALPHA = 0.3
TOP = 20
INTENT_GRID = (0.0, 0.05, 0.10, 0.15, 0.20, 0.30)


def rebuild(corpus: list[dict], distractors: list[str] | None) -> list[R.Chunk]:
    analyzer = R.Analyzer(reference_date=R.REF_DATE)
    chunks, _ = R.build_chunks(analyzer, corpus)
    for k, text in enumerate(distractors or []):
        res = analyzer.analyze_document(text)
        for c in res.document_chunks:
            chunks.append(R.Chunk(len(chunks), f"noise{k}", c.id, c.text, R.ChunkView.from_chunk(c, res)))
    return chunks


def load(pkl: str, qfile: Path, corpus: list[dict], distractors: list[str] | None) -> list[dict]:
    items = pickle.loads((E.DEFAULT_CACHE / pkl).read_bytes())
    qs = {json.loads(l)["qid"]: json.loads(l) for l in qfile.read_text(encoding="utf-8").splitlines() if l.strip()}
    chunks = rebuild(corpus, distractors)
    analyzer = R.Analyzer(reference_date=R.REF_DATE)
    out = []
    for it in items:
        if not it["has_gold"] or not any(r["gold"] for r in it["rows"]):
            continue
        q = qs[it["qid"]]
        qir = analyzer.analyze_query(q["question"])
        rows = []
        for r in it["rows"]:
            rows.append({**r, "new_feats": rerank_features(qir, chunks[r["idx"]].view)})
        out.append({"qid": it["qid"], "question": q["question"], "type": q["type"], "intent": qir.intent, "rows": rows})
    return out


def _rr(order: list[dict]) -> float:
    for p, r in enumerate(order[:10]):
        if r["gold"]:
            return 1.0 / (p + 1)
    return 0.0


def hybrid_rerank_rr(item: dict, feats_key: str | None, weights: dict[str, float] | None = None, alpha: float = ALPHA) -> float:
    rows = item["rows"]
    fused = {id(r): alpha * r["bn"] + (1 - alpha) * r["en"] for r in rows}
    order = sorted(rows, key=lambda r: -(fused[id(r)] + (1000 if r["in_mask"] else 0)))
    if feats_key is None:
        return _rr(order)
    top = order[:TOP]
    rs = E._minmax({id(r): fused[id(r)] for r in top})
    scored = [(r, rerank_score(r[feats_key], semantic_similarity=r["en"], lexical_similarity=r["bn"], retrieval_score=rs[id(r)], weights=weights)) for r in top]
    scored.sort(key=lambda x: -x[1])
    return _rr([r for r, _ in scored] + order[TOP:])


def lexical_rerank_rr(item: dict, feats_key: str | None) -> float:
    """BM25 order (candidates that came from the BM25 top-50 have bn>0) → DEFAULT_WEIGHTS rerank of the top-20."""
    rows = sorted(item["rows"], key=lambda r: -r["bn"])
    if feats_key is None:
        return _rr(rows)
    top = rows[:TOP]
    scored = [(r, rerank_score(r[feats_key], semantic_similarity=r["bn"])) for r in top]
    scored.sort(key=lambda x: -x[1])
    return _rr([r for r, _ in scored] + rows[TOP:])


def mean(items: list[dict], fn) -> float:
    return round(float(np.mean([fn(it) for it in items])), 4) if items else float("nan")


def by_group(items: list[dict], key: str, fns: dict[str, callable]) -> list[tuple[str, int, dict[str, float]]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        groups[str(it[key])].append(it)
    return [(g, len(v), {n: mean(v, f) for n, f in fns.items()}) for g, v in sorted(groups.items())]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", metavar="FILE")
    ap.add_argument("--json", metavar="FILE")
    args = ap.parse_args()

    syn_corpus = [json.loads(l) for l in (R.HERE / "data" / "rag_corpus.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    noise = [json.loads(l)["text"] for l in (R.HERE.parent / "quality_test" / "annotated" / "annotated_v1_draft.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    real_corpus = [json.loads(l) for l in (PRIVATE / "corpus_real.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    syn = load("tune_syn.pkl", R.HERE / "data" / "rag_questions_200.jsonl", syn_corpus, noise)
    real = load("tune_real.pkl", PRIVATE / "questions_real.jsonl", real_corpus, None)
    sets = {"syn_train_1_80": [x for x in syn if int(x["qid"][1:]) <= 80], "syn_val_81_200": [x for x in syn if int(x["qid"][1:]) > 80], "real_120": real}

    base_fns = {
        "hybrid_only": lambda it: hybrid_rerank_rr(it, None),
        "hyb+rerank(cached feats)": lambda it: hybrid_rerank_rr(it, "feats"),
        "hyb+rerank(current)": lambda it: hybrid_rerank_rr(it, "new_feats"),
        "bm25_only": lambda it: lexical_rerank_rr(it, None),
        "lex+rerank(cached)": lambda it: lexical_rerank_rr(it, "feats"),
        "lex+rerank(current)": lambda it: lexical_rerank_rr(it, "new_feats"),
    }
    grid_fns = {f"intent_w={w}": (lambda it, w=w: hybrid_rerank_rr(it, "new_feats", weights={"intent_match": w})) for w in INTENT_GRID}

    result = {"version": __version__, "alpha": ALPHA, "hybrid_weights": HYBRID_WEIGHTS, "default_weights": DEFAULT_WEIGHTS, "sets": {}}
    lines = [f"# Rerank ablation — KotobaCore {__version__} (hybrid α={ALPHA}, top-{TOP} rerank)", ""]
    lines += ["## overall MRR@10", "", "| set | n | " + " | ".join(base_fns) + " |", "|---|---|" + "---|" * len(base_fns)]
    for name, items in sets.items():
        row = {n: mean(items, f) for n, f in base_fns.items()}
        result["sets"][name] = {"n": len(items), "overall": row}
        lines.append(f"| {name} | {len(items)} | " + " | ".join(f"{row[n]:.4f}" for n in base_fns) + " |")
    lines += ["", "## intent_match weight grid (current features, hybrid path; choose on syn_train → check syn_val → real once)", "",
              "| set | " + " | ".join(grid_fns) + " |", "|---|" + "---|" * len(grid_fns)]
    for name, items in sets.items():
        row = {n: mean(items, f) for n, f in grid_fns.items()}
        result["sets"][name]["intent_grid"] = row
        lines.append(f"| {name} | " + " | ".join(f"{row[n]:.4f}" for n in grid_fns) + " |")
    cols = ["hybrid_only", "hyb+rerank(cached feats)", "hyb+rerank(current)", "lex+rerank(cached)", "lex+rerank(current)"]
    for name, items in sets.items():
        for key in ("type", "intent"):
            lines += ["", f"## {name} by {key} (MRR@10)", "", "| group | n | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
            rows = by_group(items, key, {c: base_fns[c] for c in cols})
            result["sets"][name][f"by_{key}"] = {g: {"n": n, **m} for g, n, m in rows}
            for g, n, m in rows:
                lines.append(f"| {g} | {n} | " + " | ".join(f"{m[c]:.3f}" for c in cols) + " |")
    text = "\n".join(lines) + "\n"
    print(text)
    if args.md:
        Path(args.md).write_text(text, encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
