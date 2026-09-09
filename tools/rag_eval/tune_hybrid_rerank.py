"""Tune KotobaCore rerank weights for the HYBRID (BM25 + embedding) path.

Why: the lexical defaults (features.DEFAULT_WEIGHTS) were fitted with BM25 as
the only similarity signal. With a real embedding, the fused retrieval score
is much stronger and the old weights let entity / keyword hints override it
(real corpus: hybrid 0.678 → +rerank 0.651).

Protocol (no peeking at the real corpus while choosing):
  1. synthetic questions 1-80  → coarse grid, then a fine grid around the top → 3 candidates
  2. synthetic questions 81-200 → validation (generalization check)
  3. real corpus 120 questions  → applied ONCE at the end with the chosen weights

Features per candidate (union of BM25 top-50 and embedding top-50):
  retrieval_score   min-max(α·bm25_n + (1-α)·cos_n)   (the fused ranking itself)
  semantic_similarity  cos_n,  lexical_similarity  bm25_n
  entity_match / keyword_overlap / intent_match / time_match / topic_match / sentiment_match (rag.features)
Constraint-filter semantics as in run_embed_eval: chunks passing the Query IR
time / location filter are ranked first.

Run inside the kotobacore-embed venv:
  python tools/rag_eval/tune_hybrid_rerank.py --json OUT --md OUT
"""

from __future__ import annotations

import argparse
import itertools
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_embed_eval as E  # noqa: E402
import run_rag_eval as R  # noqa: E402
from kotobacore.rag.features import DEFAULT_WEIGHTS, rerank_features  # noqa: E402

FEATS = ["retrieval_score", "semantic_similarity", "lexical_similarity", "entity_match", "keyword_overlap",
         "intent_match", "time_match", "topic_match", "sentiment_match"]
ALPHAS = (0.2, 0.3, 0.4)
PRIVATE = Path("G:/マイドライブ/KotobaCore/rag_eval_private")


# ---------------------------------------------------------------- data preparation (cached)


def prepare(corpus: list[dict], questions: list[dict], distractors: list[str] | None, cache: Path, model: str) -> list[dict]:
    """Per question: candidate rows with raw signals and features; cached as pickle."""
    if cache.exists():
        return pickle.loads(cache.read_bytes())
    analyzer = R.Analyzer(reference_date=R.REF_DATE)
    chunks, _ = R.build_chunks(analyzer, corpus)
    for k, text in enumerate(distractors or []):
        res = analyzer.analyze_document(text)
        for c in res.document_chunks:
            chunks.append(R.Chunk(len(chunks), f"noise{k}", c.id, c.text, R.ChunkView.from_chunk(c, res)))
    index_text = [c.view.text for c in chunks]
    bm25 = R.BM25([R.bigrams(t) for t in index_text])
    emb = E.Embedder(model, E.DEFAULT_CACHE)
    P = emb.encode(index_text, "passage")
    Q = emb.encode([q["question"] for q in questions], "query")
    out = []
    for qi, q in enumerate(questions):
        qir = analyzer.analyze_query(q["question"])
        gold = R.gold_chunks(chunks, q["doc_id"], q["answer"])
        mask = R.constraint_mask(qir, chunks)
        mset = set(mask) if mask is not None else None
        a = bm25.rank(R.bigrams(q["question"]))
        cos = P @ Q[qi]
        h = sorted(((i, float(cos[i])) for i in range(len(chunks))), key=lambda x: -x[1])
        cand = [i for i, _ in a[:50]]
        cand += [i for i, _ in h[:50] if i not in set(cand)]
        bscore = dict(a)
        bn = E._minmax({i: bscore.get(i, 0.0) for i in cand})
        en = E._minmax({i: float(cos[i]) for i in cand})
        rows = []
        for i in cand:
            f = rerank_features(qir, chunks[i].view)
            rows.append({"idx": i, "bn": bn[i], "en": en[i], "feats": f, "in_mask": (mset is None) or (i in mset), "gold": i in gold})
        out.append({"qid": q["qid"], "type": q["type"], "lexical": q["lexical"], "rows": rows, "has_gold": bool(gold),
                    "has_mask": mset is not None})
    cache.write_bytes(pickle.dumps(out))
    return out


# ---------------------------------------------------------------- vectorized scoring


def matrices(items: list[dict], alpha: float) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """Per question: (F [cand×feat], present [cand×feat] 1/0, gold [cand], bonus [cand])."""
    mats = []
    for it in items:
        rows = it["rows"]
        fused = np.array([alpha * r["bn"] + (1 - alpha) * r["en"] for r in rows])
        lo, hi = fused.min(), fused.max()
        rs = (fused - lo) / (hi - lo) if hi - lo > 1e-9 else np.ones_like(fused)
        F = np.zeros((len(rows), len(FEATS)))
        P = np.zeros((len(rows), len(FEATS)))
        for k, r in enumerate(rows):
            vals = {"retrieval_score": rs[k], "semantic_similarity": r["en"], "lexical_similarity": r["bn"], **r["feats"]}
            for j, name in enumerate(FEATS):
                v = vals.get(name)
                if v is not None:
                    F[k, j] = v
                    P[k, j] = 1.0
        gold = np.array([r["gold"] for r in rows], dtype=bool)
        bonus = np.array([1000.0 if r["in_mask"] else 0.0 for r in rows])
        mats.append((F, P, gold, bonus))
    return mats


def evaluate_weights(mats, W: np.ndarray) -> dict[str, np.ndarray]:
    """W: [combos × feat]. Returns arrays over combos: mrr, r1, r3, r5 (means over questions with gold)."""
    n = 0
    mrr = np.zeros(W.shape[0]); r1 = np.zeros(W.shape[0]); r3 = np.zeros(W.shape[0]); r5 = np.zeros(W.shape[0])
    for F, P, gold, bonus in mats:
        if not gold.any():
            continue
        n += 1
        num = F @ W.T                     # cand × combos
        den = P @ W.T                     # weights present per candidate
        den[den == 0] = 1.0
        score = num / den + bonus[:, None]
        gbest = score[gold].max(axis=0)   # combos
        pos = (score > gbest[:, None].T).sum(axis=0)  # number of candidates strictly better
        mrr += np.where(pos < 10, 1.0 / (pos + 1), 0.0)
        r1 += pos < 1; r3 += pos < 3; r5 += pos < 5
    return {"mrr": mrr / n, "r1": 100 * r1 / n, "r3": 100 * r3 / n, "r5": 100 * r5 / n, "n": n}


def eval_single(items, alpha, weights: dict[str, float] | None, subset=None) -> dict:
    """weights None → no rerank (fused order + filter bonus)."""
    it = items if subset is None else [x for x in items if subset(x)]
    mats = matrices(it, alpha)
    if weights is None:
        w = np.zeros((1, len(FEATS))); w[0, 0] = 1.0
    else:
        w = np.array([[weights.get(f, 0.0) for f in FEATS]])
    r = evaluate_weights(mats, w)
    return {k: (round(float(v[0]), 4) if k != "n" else v) for k, v in r.items()}


def lexical_defaults_as_hybrid() -> dict[str, float]:
    """Current DEFAULT_WEIGHTS applied the old way: cos as 'semantic_similarity', no retrieval_score."""
    w = {k: v for k, v in DEFAULT_WEIGHTS.items()}
    w["retrieval_score"] = 0.0
    w["lexical_similarity"] = 0.0
    return w


# ---------------------------------------------------------------- grid search


def grid(space: dict[str, list[float]]) -> tuple[np.ndarray, list[dict]]:
    keys = list(space)
    combos = list(itertools.product(*[space[k] for k in keys]))
    W = np.array([[dict(zip(keys, c)).get(f, 0.0) for f in FEATS] for c in combos])
    return W, [dict(zip(keys, c)) for c in combos]


def search(items_A, items_B, alphas=ALPHAS) -> dict:
    coarse = {
        "retrieval_score": [0.4, 0.6, 0.8, 1.0], "semantic_similarity": [0.0, 0.1, 0.2], "lexical_similarity": [0.0, 0.1, 0.2],
        "entity_match": [0.0, 0.1], "keyword_overlap": [0.0, 0.1, 0.2], "intent_match": [0.0, 0.05, 0.1],
        "time_match": [0.0, 0.1], "topic_match": [0.0, 0.05], "sentiment_match": [0.0],
    }
    results = []
    for alpha in alphas:
        matsA = matrices(items_A, alpha)
        W, combos = grid(coarse)
        rA = evaluate_weights(matsA, W)
        order = np.argsort(-rA["mrr"])[:5]
        for o in order:
            results.append((alpha, float(rA["mrr"][o]), combos[o]))
    results.sort(key=lambda x: -x[1])
    # fine grid around the top 3 coarse results
    fine_results = []
    for alpha, _m, base in results[:3]:
        space = {}
        for k, v in base.items():
            if k == "sentiment_match":
                space[k] = [0.0]
            else:
                space[k] = sorted({round(max(0.0, v + d), 3) for d in (-0.05, 0.0, 0.05)})
        matsA = matrices(items_A, alpha)
        W, combos = grid(space)
        rA = evaluate_weights(matsA, W)
        o = int(np.argmax(rA["mrr"]))
        fine_results.append((alpha, float(rA["mrr"][o]), combos[o]))
    fine_results.sort(key=lambda x: -x[1])
    # validate the 3 candidates on B
    cands = []
    for alpha, mA, w in fine_results[:3]:
        vB = eval_single(items_B, alpha, w)
        cands.append({"alpha": alpha, "weights": w, "train_mrr": round(mA, 4), "val": vB})
    return {"coarse_top": [(a, round(m, 4), w) for a, m, w in results[:5]], "candidates": cands}


# ---------------------------------------------------------------- reporting


def report_table(items, alpha, weights_sets: dict[str, dict | None], subset=None) -> dict:
    return {name: eval_single(items, alpha, w, subset) for name, w in weights_sets.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=E.DEFAULT_MODEL)
    ap.add_argument("--json", metavar="FILE")
    ap.add_argument("--md", metavar="FILE")
    args = ap.parse_args()
    t0 = time.perf_counter()

    syn_corpus = [json.loads(l) for l in (R.HERE / "data" / "rag_corpus.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    syn_q = [json.loads(l) for l in (R.HERE / "data" / "rag_questions_200.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    noise = [json.loads(l)["text"] for l in (R.HERE.parent / "quality_test" / "annotated" / "annotated_v1_draft.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    real_corpus = [json.loads(l) for l in (PRIVATE / "corpus_real.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    real_q = [json.loads(l) for l in (PRIVATE / "questions_real.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    syn = prepare(syn_corpus, syn_q, noise, E.DEFAULT_CACHE / "tune_syn.pkl", args.model)
    real = prepare(real_corpus, real_q, None, E.DEFAULT_CACHE / "tune_real.pkl", args.model)
    A, B = syn[:80], syn[80:]

    found = search(A, B)
    chosen = max(found["candidates"], key=lambda c: c["val"]["mrr"])  # the candidate that generalizes best
    old = lexical_defaults_as_hybrid()

    def block(items, alpha, new_w):
        sets = {"hybrid_only": None, "old_weights": old, "new_weights": new_w}
        out = {"overall": report_table(items, alpha, sets)}
        for grp, field in (("synonym", "lexical"), ("paraphrase", "lexical"), ("howto", "type")):
            out[grp] = report_table(items, alpha, sets, subset=lambda x, g=grp, f=field: x[f] == g)
        return out

    alpha = chosen["alpha"]
    result = {
        "model": args.model, "alphas": ALPHAS, "features": FEATS, "search": found, "chosen": chosen,
        "old_weights_as_hybrid": old,
        "train_1_80": block(A, alpha, chosen["weights"]),
        "val_81_200": block(B, alpha, chosen["weights"]),
        "real_120": block(real, alpha, chosen["weights"]),
        "alpha_sweep_real_hybrid_only": {a: eval_single(real, a, None) for a in ALPHAS},
        "alpha_sweep_val_hybrid_only": {a: eval_single(B, a, None) for a in ALPHAS},
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    if args.md:
        lines = [f"# Hybrid rerank weight tuning — {args.model}", "", f"chosen α={alpha}, weights={chosen['weights']}", ""]
        for name in ("train_1_80", "val_81_200", "real_120"):
            b = result[name]
            lines += [f"## {name}", "", "| set | hybrid_only MRR/R@1/R@3 | old_weights | new_weights |", "|---|---|---|---|"]
            for grp in ("overall", "synonym", "paraphrase", "howto"):
                row = b[grp]
                fmt = lambda m: f"{m['mrr']:.3f} / {m['r1']:.1f} / {m['r3']:.1f} (n={m['n']})"
                lines.append(f"| {grp} | {fmt(row['hybrid_only'])} | {fmt(row['old_weights'])} | {fmt(row['new_weights'])} |")
            lines.append("")
        lines += ["## candidates (train → val)", ""]
        for c in found["candidates"]:
            lines.append(f"- α={c['alpha']} train {c['train_mrr']} → val {c['val']['mrr']} : {c['weights']}")
        Path(args.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("chosen", "elapsed_s")}, ensure_ascii=False, indent=2, default=float))


if __name__ == "__main__":
    main()
