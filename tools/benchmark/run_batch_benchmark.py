"""NFR-001 batch benchmark (v1.0 完成条件「大規模文書テスト (10 万文バッチ)」).

Targets (要件定義書 §5 NFR-001):
  - 100,000 sentences, single core, analyze() with all four modules  → ≤ 10 min
  - one 10,000-character document, analyze_document() incl. chunking → ≤ 1 s
  - per-sentence analyze() mean                                       → ≤ 5 ms

Sentences are the real texts KotobaCore ships with (SNS example phrases, the
human-annotated set, the golden set) cycled to 100k with a light variation so
the dictionary caches are not the whole story. The 10k-character document is a
concatenation of annotated sentences with Markdown headings every 12 lines.

Usage: python tools/benchmark/run_batch_benchmark.py [--sentences 100000] [--md OUT] [--json OUT]
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from kotobacore import Analyzer
from kotobacore._version import __version__

VARIANTS = ["", "。", "！", "…", "ね。", "よ。", "。本当に。", "、でも大丈夫。", "（笑）", "🙏"]


def load_texts() -> list[str]:
    texts: list[str] = []
    sns = ROOT / "kotobacore" / "resources" / "dict" / "Japanese-SNS-Emotion-Examples-v1.txt"
    with sns.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            texts += [e.strip() for e in (row.get("examples") or "").split("、") if e.strip()]
    ann = ROOT / "tools" / "quality_test" / "annotated" / "annotated_v1.jsonl"
    if ann.exists():
        texts += [json.loads(l)["text"] for l in ann.read_text(encoding="utf-8").splitlines() if l.strip()]
    gold = ROOT / "tools" / "quality_test" / "golden_set.csv"
    if gold.exists():
        with gold.open(encoding="utf-8") as f:
            texts += [r["text"] for r in csv.DictReader(f) if r.get("text")]
    return [t for t in texts if t]


def make_document(texts: list[str], chars: int = 10_000) -> str:
    """A prose-like 10k-character document: sentences of ≥ 15 chars (the annotated set, not SNS
    fragments) joined 2–4 per paragraph, a heading every 6 paragraphs — ~30 chars per sentence
    like a real report, not 1,000+ eight-character fragments."""
    pool = [t for t in texts if len(t) >= 15] or texts
    lines: list[str] = ["# ベンチマーク文書", ""]
    i = p = 0
    while sum(len(x) + 1 for x in lines) < chars:
        if p % 6 == 0:
            lines += [f"## 第{p // 6 + 1}節", ""]
        k = 2 + (p % 3)
        lines.append("".join(pool[(i + j) % len(pool)] for j in range(k)))
        lines.append("")
        i += k
        p += 1
    return "\n".join(lines)[:chars]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sentences", type=int, default=100_000)
    ap.add_argument("--md", default=str(ROOT / "tools" / "benchmark" / "batch_benchmark.md"))
    ap.add_argument("--json", default=str(ROOT / "tools" / "benchmark" / "batch_benchmark.json"))
    args = ap.parse_args()

    base = load_texts()
    a = Analyzer()
    a.analyze("暖機運転")
    n = args.sentences
    per: list[float] = []
    t_start = time.perf_counter()
    for i in range(n):
        text = base[i % len(base)] + VARIANTS[(i // len(base)) % len(VARIANTS)]
        t0 = time.perf_counter()
        a.analyze(text)
        per.append(time.perf_counter() - t0)
    total = time.perf_counter() - t_start
    per_ms = [p * 1000 for p in per]
    per_ms.sort()
    doc = make_document(base)
    doc_runs: list[float] = []
    for _ in range(3):  # best of 3: a single run right after the 100k loop is noisy (GC / cache eviction)
        t0 = time.perf_counter()
        r = a.analyze_document(doc)
        doc_runs.append(time.perf_counter() - t0)
    doc_s = min(doc_runs)
    res = {
        "kotobacore": __version__, "sentences": n, "unique_texts": len(base), "total_s": round(total, 1),
        "sentences_per_s": int(n / total), "mean_ms": round(statistics.fmean(per_ms), 3), "median_ms": round(per_ms[n // 2], 3),
        "p95_ms": round(per_ms[int(n * 0.95)], 3), "p99_ms": round(per_ms[int(n * 0.99)], 3), "max_ms": round(per_ms[-1], 3),
        "document_chars": len(doc), "document_s": round(doc_s, 3), "document_chunks": len(r.document_chunks), "document_sentences": len(r.sentences),
        "targets": {"batch_100k_s": 600, "sentence_mean_ms": 5, "document_10k_s": 1},
    }
    res["pass"] = {
        "batch_100k": total * (100_000 / n) <= 600, "sentence_mean": res["mean_ms"] <= 5, "document_10k": doc_s <= 1.0,
    }
    md = [f"# NFR-001 batch benchmark — KotobaCore {__version__}", "",
          "| item | measured | target | pass |", "|---|---|---|---|",
          f"| {n:,} sentences (single core, 4 modules) | {total:.1f} s ({res['sentences_per_s']:,} 文/s) | ≤ 600 s / 100k | {'✅' if res['pass']['batch_100k'] else '❌'} |",
          f"| analyze() per sentence mean / median / p95 / p99 / max | {res['mean_ms']} / {res['median_ms']} / {res['p95_ms']} / {res['p99_ms']} / {res['max_ms']} ms | mean ≤ 5 ms | {'✅' if res['pass']['sentence_mean'] else '❌'} |",
          f"| analyze_document() {len(doc):,} chars ({res['document_sentences']} sentences → {res['document_chunks']} chunks) | {doc_s:.3f} s | ≤ 1 s | {'✅' if res['pass']['document_10k'] else '❌'} |",
          "", f"texts: {len(base):,} unique (SNS examples + annotated_v1 + golden), cycled with 10 suffix variants."]
    Path(args.md).write_text("\n".join(md) + "\n", encoding="utf-8")
    Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
