"""Embedding × KotobaCore hybrid retrieval evaluation (FR-085 Embedding 連携の効果測定).

Adds embedding conditions on top of tools/rag_eval/run_rag_eval.py (which is
left unchanged). Embeddings come from an external sentence-transformers model
(default intfloat/multilingual-e5-base, the model used by the Spark RAG
library); KotobaCore itself stays dependency-free — run this with the
``kotobacore-embed`` venv.

Conditions (all index the chunk text WITH heading / table context):
  A   bm25              lexical baseline (raw question)
  E   kotobacore_lex    bm25 + Query IR terms + constraint filter + rerank   (existing full path)
  H   emb               cosine over passage embeddings
  I   emb+rerank        top-20 by cosine → KotobaCore rerank (semantic_similarity = cosine)
  J   rrf(bm25,emb)     reciprocal-rank fusion of A and H
  K   hybrid            min-max normalized  α·bm25 + (1-α)·cos  (α = ALPHA, 0.4)
  L   hybrid+rerank     K → constraint filter → KotobaCore rerank
  M   full              rrf(bm25_ir_weighted, emb) → filter → rerank   (everything KotobaCore has + embedding)

Usage (from the repo root, inside the embed venv):
  python tools/rag_eval/run_embed_eval.py --corpus … --questions … [--distractors …] [--model …] --json OUT --md OUT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_rag_eval as R  # noqa: E402
from kotobacore._version import __version__  # noqa: E402
from kotobacore.rag.features import EXPANSION_WEIGHT, HYBRID_ALPHA, rerank_features, rerank_score, rrf_fuse  # noqa: E402

DEFAULT_MODEL = "intfloat/multilingual-e5-base"
DEFAULT_CACHE = Path("G:/マイドライブ/KotobaCore/rag_eval_private/cache")
TOP = 20
ALPHA = HYBRID_ALPHA  # bm25 weight in the hybrid — the library constant (0.3); analyze_alpha_by_query.py: no query-time policy beats it


# ---------------------------------------------------------------- embeddings (external model, cached)


class Embedder:
    def __init__(self, model_name: str, cache_dir: Path) -> None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device="cpu")
        self.cache_dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.is_e5 = "e5" in model_name.lower()

    def _key(self, kind: str, texts: list[str]) -> Path:
        h = hashlib.sha1((self.model_name + "\n" + kind + "\n" + "\n".join(texts)).encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{kind}_{h}.npy"

    def encode(self, texts: list[str], kind: str, batch: int = 32) -> np.ndarray:
        path = self._key(kind, texts)
        if path.exists():
            return np.load(path)
        prefix = ("query: " if kind == "query" else "passage: ") if self.is_e5 else ""
        vecs = self.model.encode([prefix + t for t in texts], batch_size=batch, normalize_embeddings=True, show_progress_bar=False)
        vecs = np.asarray(vecs, dtype=np.float32)
        np.save(path, vecs)
        return vecs


def _minmax(scores: dict[int, float]) -> dict[int, float]:
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    if hi - lo < 1e-9:
        return dict.fromkeys(scores, 1.0)
    return {i: (s - lo) / (hi - lo) for i, s in scores.items()}


# ---------------------------------------------------------------- evaluation


def evaluate(corpus: list[dict], questions: list[dict], distractors: list[str] | None, model_name: str, cache_dir: Path) -> dict:
    analyzer = R.Analyzer(reference_date=R.REF_DATE)
    t0 = time.perf_counter()
    chunks, _ = R.build_chunks(analyzer, corpus)
    for k, text in enumerate(distractors or []):
        res = analyzer.analyze_document(text)
        for c in res.document_chunks:
            chunks.append(R.Chunk(len(chunks), f"noise{k}", c.id, c.text, R.ChunkView.from_chunk(c, res)))
    t_chunk = time.perf_counter() - t0

    index_text = [c.view.text for c in chunks]
    bm25 = R.BM25([R.bigrams(t) for t in index_text])

    emb = Embedder(model_name, cache_dir)
    t0 = time.perf_counter()
    P = emb.encode(index_text, "passage")
    t_index = time.perf_counter() - t0
    t0 = time.perf_counter()
    Q = emb.encode([q["question"] for q in questions], "query")
    t_query = time.perf_counter() - t0

    golds = [R.gold_chunks(chunks, q["doc_id"], q["answer"]) for q in questions]

    def rerank_with(qir, ranked: list[tuple[int, float]], sims: dict[int, float], lex: dict[int, float] | None = None) -> list[int]:
        """lex=None → lexical-style rerank (similarity only, DEFAULT_WEIGHTS);
        lex given → hybrid path: retrieval_score = the fused score handed in as
        ``ranked``, plus cos / bm25 normalized → HYBRID_WEIGHTS (auto-switch)."""
        top = ranked[:TOP]
        if not top:
            return []
        norm = _minmax({i: sims.get(i, 0.0) for i, _ in top})
        if lex is None:
            scored = [(i, rerank_score(rerank_features(qir, chunks[i].view), semantic_similarity=norm[i])) for i, _ in top]
        else:
            rs = _minmax({i: s for i, s in top})
            ln = _minmax({i: lex.get(i, 0.0) for i, _ in top})
            scored = [(i, rerank_score(rerank_features(qir, chunks[i].view), semantic_similarity=norm[i], lexical_similarity=ln[i], retrieval_score=rs[i])) for i, _ in top]
        scored.sort(key=lambda x: -x[1])
        return [i for i, _ in scored] + [i for i, _ in ranked[TOP:]]

    conds: dict[str, list[list[int]]] = {k: [] for k in "AEHIJKLM"}
    alpha_grid: dict[float, list[list[int]]] = {a: [] for a in (0.3, 0.5, 0.7)}
    for qi, q in enumerate(questions):
        qir = analyzer.analyze_query(q["question"])
        raw = R.bigrams(q["question"])
        own = [bg for t in [*qir.keywords, *([qir.target] if qir.target else [])] for bg in R.bigrams(t)]
        exp = [bg for t in qir.expanded_terms for bg in R.bigrams(t)]
        mask = R.constraint_mask(qir, chunks)
        mset = set(mask) if mask is not None else None

        a = bm25.rank(raw)
        rankA = [i for i, _ in a]
        # existing full lexical path (E)
        c = bm25.rank_weighted([(raw, 1.0), (own, R.OWN_TERM_WEIGHT), (exp, EXPANSION_WEIGHT)])
        d = [(i, s) for i, s in c if mset is None or i in mset]
        rest = [i for i, _ in c if mset is not None and i not in mset]
        rankE = R.rerank_top(qir, d, chunks) + rest

        cos = P @ Q[qi]
        sims = {i: float(cos[i]) for i in range(len(chunks))}
        h = sorted(sims.items(), key=lambda x: -x[1])
        rankH = [i for i, _ in h]
        rankI = rerank_with(qir, h, sims)
        rankJ = rrf_fuse(rankA, rankH)
        # hybrid: min-max over the union of top-50 of each
        cand = {i for i, _ in a[:50]} | {i for i, _ in h[:50]}
        bn = _minmax({i: s for i, s in a if i in cand})
        en = _minmax({i: sims[i] for i in cand})
        for alpha, store in alpha_grid.items():
            fused = sorted(((i, alpha * bn.get(i, 0.0) + (1 - alpha) * en.get(i, 0.0)) for i in cand), key=lambda x: -x[1])
            store.append([i for i, _ in fused])
        kfused = sorted(((i, ALPHA * bn.get(i, 0.0) + (1 - ALPHA) * en.get(i, 0.0)) for i in cand), key=lambda x: -x[1])
        rankK = [i for i, _ in kfused]
        kf = [(i, s) for i, s in kfused if mset is None or i in mset]
        krest = [i for i, _ in kfused if mset is not None and i not in mset]
        rankL = rerank_with(qir, kf, sims, lex=dict(a)) + krest
        # M: everything — fuse the weighted lexical ranking with the embedding, filter, rerank
        fusedM = rrf_fuse([i for i, _ in c], rankH)
        # RRF score as the fused retrieval score for the hybrid rerank path
        rrf_score = {i: 1.0 / (60 + p + 1) for p, i in enumerate(fusedM)}
        mf = [(i, rrf_score[i]) for i in fusedM if mset is None or i in mset]
        mrest = [i for i in fusedM if mset is not None and i not in mset]
        rankM = rerank_with(qir, mf, sims, lex=dict(c)) + mrest

        for k, rk in zip("AEHIJKLM", (rankA, rankE, rankH, rankI, rankJ, rankK, rankL, rankM)):
            conds[k].append(rk)

    labels = {"A": "bm25", "E": "kotobacore_lex", "H": "emb", "I": "emb+rerank", "J": "rrf(bm25,emb)",
              "K": f"hybrid(α={ALPHA})", "L": "hybrid+filter+rerank", "M": "full(rrf(lex_ir,emb)+filter+rerank)"}
    overall = {labels[k]: R.metrics(v, golds) for k, v in conds.items()}
    alphas = {f"hybrid(α={a})": R.metrics(v, golds) for a, v in alpha_grid.items()}

    def by(field: str) -> dict:
        out: dict = {}
        for val in sorted({q[field] for q in questions}):
            idx = [i for i, q in enumerate(questions) if q[field] == val]
            out[val] = {labels[k]: R.metrics([conds[k][i] for i in idx], [golds[i] for i in idx]) for k in "AEHILM"}
        return out

    return {
        "version": __version__, "model": model_name, "docs": len(corpus), "chunks": len(chunks), "questions": len(questions),
        "gold_missing": [q["qid"] for q, g in zip(questions, golds) if not g],
        "timing_s": {"chunking": round(t_chunk, 1), "index_embedding": round(t_index, 1), "query_embedding": round(t_query, 2)},
        "overall": overall, "alpha_grid": alphas, "by_lexical": by("lexical"), "by_type": by("type"),
    }


def to_markdown(res: dict) -> str:
    lines = [f"# Embedding × KotobaCore — {res['model']} / KotobaCore {res['version']}", "",
             f"docs {res['docs']} / chunks {res['chunks']} / questions {res['questions']} / gold missing {len(res['gold_missing'])} | "
             f"chunking {res['timing_s']['chunking']}s, index embedding {res['timing_s']['index_embedding']}s, query embedding {res['timing_s']['query_embedding']}s", "",
             "| condition | R@1 | R@3 | R@5 | MRR@10 |", "|---|---|---|---|---|"]
    for k, m in res["overall"].items():
        lines.append(f"| {k} | {m['recall@1']} | {m['recall@3']} | {m['recall@5']} | {m['mrr@10']} |")
    lines += ["", "## hybrid α grid (α = weight of bm25)", "", "| α | R@1 | R@3 | R@5 | MRR@10 |", "|---|---|---|---|---|"]
    for k, m in res["alpha_grid"].items():
        lines.append(f"| {k} | {m['recall@1']} | {m['recall@3']} | {m['recall@5']} | {m['mrr@10']} |")
    cols = ["bm25", "kotobacore_lex", "emb", "emb+rerank", "hybrid+filter+rerank", "full(rrf(lex_ir,emb)+filter+rerank)"]
    for title, key in (("By lexical relation (R@3)", "by_lexical"), ("By question type (R@3)", "by_type")):
        lines += ["", f"## {title}", "", "| group | n | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
        for g, d in res[key].items():
            lines.append(f"| {g} | {d['bm25']['n']} | " + " | ".join(str(d[c]["recall@3"]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=str(R.HERE / "data" / "rag_corpus.jsonl"))
    ap.add_argument("--questions", default=str(R.HERE / "data" / "rag_questions_200.jsonl"))
    ap.add_argument("--distractors", metavar="JSONL")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    ap.add_argument("--json", metavar="FILE")
    ap.add_argument("--md", metavar="FILE")
    args = ap.parse_args()
    corpus = [json.loads(line) for line in Path(args.corpus).read_text(encoding="utf-8").splitlines() if line.strip()]
    questions = [json.loads(line) for line in Path(args.questions).read_text(encoding="utf-8").splitlines() if line.strip()]
    distractors = None
    if args.distractors:
        distractors = [json.loads(line)["text"] for line in Path(args.distractors).read_text(encoding="utf-8").splitlines() if line.strip()]
    res = evaluate(corpus, questions, distractors, args.model, Path(args.cache_dir))
    print(json.dumps({k: v for k, v in res.items() if k in ("model", "chunks", "questions", "timing_s", "overall")}, ensure_ascii=False, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.md:
        Path(args.md).write_text(to_markdown(res), encoding="utf-8")


if __name__ == "__main__":
    main()
