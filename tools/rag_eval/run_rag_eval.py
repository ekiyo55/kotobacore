"""RAG retrieval evaluation: how much do Query IR, filters and reranking add? (FR-102 §19.5)

Data (JSONL):
  corpus:    {"doc_id","title","genre","text"}
  questions: {"qid","question","doc_id","answer" (exact substring of the doc),"type","lexical"}

Pipeline under test
  chunks   = Analyzer.analyze_document(doc).document_chunks   (KotobaCore Semantic Chunking)
  gold     = the chunk(s) of doc_id that contain ``answer``
  retriever = char-bigram BM25 (pure Python, no KotobaCore) — stands in for a
              lexical / vector retriever so the *delta* from KotobaCore is isolated

Conditions
  A  bm25_raw            question text as typed
  B  bm25_raw+rerank     A, top-20 re-ranked with KotobaCore rerank features
  C  bm25_ir             question + Query IR search terms (keywords + synonym expansion + target)
  D  bm25_ir+filter      C, candidates filtered by Query IR constraints (time / location), soft fallback
  E  bm25_ir+filter+rerank   D re-ranked (full KotobaCore path)
  F  tfidf_raw           cosine over char-bigram TF-IDF (vector-search stand-in)
  G  tfidf_raw+rerank

Metrics: Recall@1 / @3 / @5, MRR@10, overall and by question ``type`` / ``lexical``.

Usage:
  python tools/rag_eval/run_rag_eval.py --corpus X.jsonl --questions Y.jsonl [--json OUT] [--md OUT]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kotobacore import Analyzer  # noqa: E402
from kotobacore._version import __version__  # noqa: E402
from kotobacore.core.ir import QueryIR  # noqa: E402
from kotobacore.rag.features import EXPANSION_WEIGHT, ChunkView, rerank_features, rerank_score, time_compatible  # noqa: E402

HERE = Path(__file__).resolve().parent
REF_DATE = _dt.date(2026, 9, 8)
TOP_CANDIDATES = 20
RAW_WEIGHT = 1  # how many times the raw question bigrams are repeated vs. expanded terms
RERANK_WEIGHTS: dict[str, float] | None = None
WITH_CONTEXT = True  # index heading path / table header with the chunk text
OWN_TERM_WEIGHT = 0.25  # weight of Query IR keywords / target on top of the raw question


# ---------------------------------------------------------------- lexical baseline (no KotobaCore)


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def bigrams(text: str) -> list[str]:
    t = "".join(ch for ch in _norm(text) if not ch.isspace() and ch not in "。、！？!?「」『』（）()・…,.:;")
    if len(t) < 2:
        return [t] if t else []
    return [t[i : i + 2] for i in range(len(t) - 1)]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.docs = docs
        self.N = len(docs)
        self.avgdl = sum(len(d) for d in docs) / max(1, self.N)
        self.tf = [Counter(d) for d in docs]
        df: Counter[str] = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def score(self, query: list[str], i: int) -> float:
        tf = self.tf[i]
        dl = len(self.docs[i])
        s = 0.0
        for t in query:
            if t not in tf:
                continue
            f = tf[t]
            s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    def rank(self, query: list[str], mask: list[int] | None = None) -> list[tuple[int, float]]:
        idx = mask if mask is not None else range(self.N)
        scored = [(i, self.score(query, i)) for i in idx]
        scored.sort(key=lambda x: -x[1])
        return scored

    def rank_weighted(self, groups: list[tuple[list[str], float]], mask: list[int] | None = None) -> list[tuple[int, float]]:
        """Weighted query: Σ weight × BM25(group terms). Raw terms 1.0, expansions EXPANSION_WEIGHT."""
        idx = mask if mask is not None else range(self.N)
        scored = [(i, sum(w * self.score(terms, i) for terms, w in groups if terms)) for i in idx]
        scored.sort(key=lambda x: -x[1])
        return scored


class TfidfCosine:
    def __init__(self, docs: list[list[str]]) -> None:
        self.N = len(docs)
        df: Counter[str] = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {t: math.log((self.N + 1) / (n + 1)) + 1 for t, n in df.items()}
        self.vecs = [self._vec(d) for d in docs]

    def _vec(self, terms: list[str]) -> dict[str, float]:
        tf = Counter(terms)
        v = {t: (1 + math.log(c)) * self.idf.get(t, math.log(self.N + 1) + 1) for t, c in tf.items()}
        n = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / n for t, x in v.items()}

    def rank(self, query: list[str], mask: list[int] | None = None) -> list[tuple[int, float]]:
        q = self._vec(query)
        idx = mask if mask is not None else range(self.N)
        scored = []
        for i in idx:
            d = self.vecs[i]
            scored.append((i, sum(w * d.get(t, 0.0) for t, w in q.items())))
        scored.sort(key=lambda x: -x[1])
        return scored


# ---------------------------------------------------------------- data


@dataclass
class Chunk:
    idx: int
    doc_id: str
    chunk_id: int
    text: str
    view: ChunkView


def build_chunks(analyzer: Analyzer, corpus: list[dict]) -> tuple[list[Chunk], dict]:
    chunks: list[Chunk] = []
    docs: dict[str, object] = {}
    for d in corpus:
        res = analyzer.analyze_document(d["text"])
        docs[d["doc_id"]] = res
        for c in res.document_chunks:
            chunks.append(Chunk(len(chunks), d["doc_id"], c.id, c.text, ChunkView.from_chunk(c, res)))
    return chunks, docs


def gold_chunks(chunks: list[Chunk], doc_id: str, answer: str) -> set[int]:
    a = _norm(answer)
    hits = {c.idx for c in chunks if c.doc_id == doc_id and a in _norm(c.text)}
    if hits:
        return hits
    # answer crosses a chunk boundary → the chunk with the longest overlap
    best, best_len = None, 0
    for c in chunks:
        if c.doc_id != doc_id:
            continue
        t = _norm(c.text)
        for k in range(len(a), 3, -1):
            if a[:k] in t or a[-k:] in t:
                if k > best_len:
                    best, best_len = c.idx, k
                break
    return {best} if best is not None else set()


# ---------------------------------------------------------------- KotobaCore query side


def ir_terms(q: QueryIR) -> list[str]:
    terms = list(dict.fromkeys([*q.keywords, *q.expanded_terms, *( [q.target] if q.target else [])]))
    return terms


def constraint_mask(q: QueryIR, chunks: list[Chunk]) -> list[int] | None:
    """Soft filter: keep chunks satisfying time / location constraints; None when no constraint or no survivor."""
    times = set(q.constraints.get("time", []))
    locs = set(q.constraints.get("location", []))
    if not times and not locs:
        return None
    keep: list[int] = []
    for c in chunks:
        ok = True
        if times:
            c_times = {str(v) for typ, _s, n, v in c.view.entities if typ in ("DATE", "TIME") for v in (v, n) if v}
            ok = any(time_compatible(t, v) for t in times for v in c_times) or any(t in c.text for t in times)
        if ok and locs:
            ok = any(loc in c.text for loc in locs)
        if ok:
            keep.append(c.idx)
    return keep or None


def rerank_top(q: QueryIR, ranked: list[tuple[int, float]], chunks: list[Chunk]) -> list[int]:
    top = ranked[:TOP_CANDIDATES]
    if not top:
        return []
    mx = max(s for _, s in top) or 1.0
    scored = []
    for i, s in top:
        f = rerank_features(q, chunks[i].view)
        scored.append((i, rerank_score(f, semantic_similarity=s / mx, weights=RERANK_WEIGHTS)))
    scored.sort(key=lambda x: -x[1])
    return [i for i, _ in scored] + [i for i, _ in ranked[TOP_CANDIDATES:]]


# ---------------------------------------------------------------- evaluation


def metrics(rankings: list[list[int]], golds: list[set[int]]) -> dict[str, float]:
    n = len(rankings)
    r1 = r3 = r5 = 0
    mrr = 0.0
    for rk, g in zip(rankings, golds):
        if not g:
            continue
        pos = next((p for p, i in enumerate(rk[:10]) if i in g), None)
        if pos is not None:
            mrr += 1.0 / (pos + 1)
            r1 += pos < 1
            r3 += pos < 3
            r5 += pos < 5
    return {"recall@1": round(100 * r1 / n, 1), "recall@3": round(100 * r3 / n, 1), "recall@5": round(100 * r5 / n, 1), "mrr@10": round(mrr / n, 3), "n": n}


def evaluate(corpus: list[dict], questions: list[dict], distractors: list[str] | None = None) -> dict:
    analyzer = Analyzer(reference_date=REF_DATE)
    chunks, _docs = build_chunks(analyzer, corpus)
    for k, text in enumerate(distractors or []):
        res = analyzer.analyze_document(text)
        for c in res.document_chunks:
            chunks.append(Chunk(len(chunks), f"noise{k}", c.id, c.text, ChunkView.from_chunk(c, res)))
    index_text = [(c.view.text if WITH_CONTEXT else c.text) for c in chunks]
    bm25 = BM25([bigrams(t) for t in index_text])
    tfidf = TfidfCosine([bigrams(t) for t in index_text])

    golds = [gold_chunks(chunks, q["doc_id"], q["answer"]) for q in questions]
    missing = [q["qid"] for q, g in zip(questions, golds) if not g]

    conds = {k: [] for k in ("A", "B", "C", "D", "E", "F", "G")}
    per_q: list[dict] = []
    for q in questions:
        qir = analyzer.analyze_query(q["question"])
        raw = bigrams(q["question"])
        mask = constraint_mask(qir, chunks)

        a = bm25.rank(raw)
        f = tfidf.rank(raw)
        rankA = [i for i, _ in a]
        rankB = rerank_top(qir, a, chunks)
        # C: weighted query — the typed words keep full weight, Query IR terms
        # (target / keywords) add 0.5, synonym expansions add EXPANSION_WEIGHT.
        own_terms = [bg for t in [*qir.keywords, *([qir.target] if qir.target else [])] for bg in bigrams(t)]
        exp_terms = [bg for t in qir.expanded_terms for bg in bigrams(t)]
        groups = [(raw, 1.0), (own_terms, OWN_TERM_WEIGHT), (exp_terms, EXPANSION_WEIGHT)]
        c = bm25.rank_weighted(groups)
        rankC = [i for i, _ in c]
        if mask is not None:
            mset = set(mask)
            d = [(i, sc) for i, sc in c if i in mset]
            rest = [i for i in rankC if i not in mset]
        else:
            d, rest = c, []
        rankD = [i for i, _ in d] + rest
        rankE = rerank_top(qir, d, chunks) + rest
        rankF = [i for i, _ in f]
        rankG = rerank_top(qir, f, chunks)
        for k, rk in zip("ABCDEFG", (rankA, rankB, rankC, rankD, rankE, rankF, rankG)):
            conds[k].append(rk)
        gold = golds[len(per_q)]
        def _pos(rk: list[int]) -> int | None:
            return next((p for p, i in enumerate(rk[:10]) if i in gold), None)
        top_e = chunks[rankE[0]] if rankE else None
        per_q.append({"qid": q["qid"], "type": q["type"], "lexical": q["lexical"], "intent": qir.intent,
                      "terms": ir_terms(qir), "filtered": mask is not None,
                      # v0.5.4: gold rank (0-based, None = outside top-10) per condition, for question-level diffs between versions
                      "rank": {"bm25_raw": _pos(rankA), "bm25_ir": _pos(rankC), "bm25_ir+filter+rerank": _pos(rankE)},
                      "gold_chunks": sorted(gold), "top1": (top_e.doc_id + ": " + top_e.text[:80].replace("\n", " / ")) if top_e else None})

    labels = {"A": "bm25_raw", "B": "bm25_raw+rerank", "C": "bm25_ir", "D": "bm25_ir+filter", "E": "bm25_ir+filter+rerank",
              "F": "tfidf_raw", "G": "tfidf_raw+rerank"}
    overall = {labels[k]: metrics(v, golds) for k, v in conds.items()}

    def by(field: str) -> dict:
        out: dict = {}
        for val in sorted({q[field] for q in questions}):
            idx = [i for i, q in enumerate(questions) if q[field] == val]
            out[val] = {labels[k]: metrics([conds[k][i] for i in idx], [golds[i] for i in idx]) for k in ("A", "C", "E", "F", "G")}
        return out

    return {
        "version": __version__, "docs": len(corpus), "chunks": len(chunks), "questions": len(questions),
        "gold_missing": missing, "overall": overall, "by_type": by("type"), "by_lexical": by("lexical"),
        "per_question": per_q,
    }


def to_markdown(res: dict) -> str:
    lines = [f"# RAG retrieval eval — KotobaCore {res['version']}", "",
             f"docs {res['docs']} / chunks {res['chunks']} / questions {res['questions']} / gold missing {len(res['gold_missing'])}", "",
             "| condition | R@1 | R@3 | R@5 | MRR@10 |", "|---|---|---|---|---|"]
    for k, m in res["overall"].items():
        lines.append(f"| {k} | {m['recall@1']} | {m['recall@3']} | {m['recall@5']} | {m['mrr@10']} |")
    for title, key in (("By question type", "by_type"), ("By lexical relation", "by_lexical")):
        lines += ["", f"## {title} (R@3)", "", "| group | n | bm25_raw | bm25_ir | bm25_ir+filter+rerank | tfidf_raw | tfidf_raw+rerank |", "|---|---|---|---|---|---|---|"]
        for g, d in res[key].items():
            n = d["bm25_raw"]["n"]
            lines.append(f"| {g} | {n} | {d['bm25_raw']['recall@3']} | {d['bm25_ir']['recall@3']} | {d['bm25_ir+filter+rerank']['recall@3']} | {d['tfidf_raw']['recall@3']} | {d['tfidf_raw+rerank']['recall@3']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=str(HERE / "data" / "rag_corpus.jsonl"))
    ap.add_argument("--questions", default=str(HERE / "data" / "rag_questions.jsonl"))
    ap.add_argument("--json", metavar="FILE")
    ap.add_argument("--md", metavar="FILE")
    ap.add_argument("--distractors", metavar="JSONL", help="extra JSONL whose 'text' fields become noise chunks")
    ap.add_argument("--raw-weight", type=int, default=1)
    ap.add_argument("--sem-weight", type=float, default=None, help="rerank weight of the lexical score (default 0.2)")
    ap.add_argument("--no-context", action="store_true", help="index chunk text only (no heading path / table header)")
    args = ap.parse_args()
    global RAW_WEIGHT, RERANK_WEIGHTS, WITH_CONTEXT
    RAW_WEIGHT = args.raw_weight
    WITH_CONTEXT = not args.no_context
    if args.sem_weight is not None:
        RERANK_WEIGHTS = {"semantic_similarity": args.sem_weight}
    corpus = [json.loads(line) for line in Path(args.corpus).read_text(encoding="utf-8").splitlines() if line.strip()]
    questions = [json.loads(line) for line in Path(args.questions).read_text(encoding="utf-8").splitlines() if line.strip()]
    distractors = None
    if args.distractors:
        distractors = [json.loads(line)["text"] for line in Path(args.distractors).read_text(encoding="utf-8").splitlines() if line.strip()]
    res = evaluate(corpus, questions, distractors)
    print(json.dumps({k: v for k, v in res.items() if k not in ("per_question", "by_type", "by_lexical")}, ensure_ascii=False, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.md:
        Path(args.md).write_text(to_markdown(res), encoding="utf-8")


if __name__ == "__main__":
    main()
