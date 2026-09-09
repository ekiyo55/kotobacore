"""Baseline comparison with existing Japanese tokenizers (v1.0 完成条件「既存ツールとのベースライン比較」).

Compares KotobaCore (coarse / fine) with janome (IPADIC) and SudachiPy (A / B / C)
on the human-annotated set (tools/quality_test/annotated):

- tokenization: boundary precision / recall / F1 against the gold segmentation
  (gold follows KotobaCore's *coarse* standard — 「行った」「美味しかった」1 語 — so
  morphological analyzers that split finer show high recall / lower precision;
  the table also reports "gold-boundary recall" alone for a fairer view of
  whether each tool at least contains the semantic-unit boundaries)
- speed: ms per sentence over the 300 texts (warm), and tokens / s
- footprint: dictionary size on disk, external dependencies

Emotion / sentiment baselines (oseti etc.) need MeCab, which has no working
Windows wheel in this environment — reported as "not run".

Usage: python tools/benchmark/compare_baselines.py [--md OUT] [--json OUT]
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from kotobacore import Analyzer
from kotobacore._version import __version__
from kotobacore.core.token import TOKENIZER_VERSION

ANNOTATED = ROOT / "tools" / "quality_test" / "annotated" / "annotated_v1_draft.jsonl"


def _boundaries(tokens: list[str]) -> set[int]:
    out, pos = set(), 0
    for t in tokens:
        pos += len(t)
        out.add(pos)
    return out


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return round(p, 4), round(r, 4), round(f, 4)


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) if path.exists() else 0


def tokenizers() -> dict[str, tuple[callable, str]]:
    """name → (tokenize(text) -> list[str], description)."""
    out: dict[str, tuple[callable, str]] = {}
    a = Analyzer(enable_emotion=False, enable_sentiment=False, enable_intent=False, enable_rag=False)
    af = Analyzer(granularity="fine", enable_emotion=False, enable_sentiment=False, enable_intent=False, enable_rag=False)
    out[f"KotobaCore coarse (Karuizawa {TOKENIZER_VERSION})"] = (lambda t: [x.surface for x in a.tokenize(t)], "意味単位 (行った 1 語)。辞書同梱 CSV、依存ゼロ")
    out["KotobaCore fine"] = (lambda t: [x.surface for x in af.tokenize(t)], "語幹 / 送り仮名 / 活用語尾 (LM 語彙用)")
    try:
        jt = importlib.import_module("janome.tokenizer")
        tok = jt.Tokenizer()
        out["janome (IPADIC)"] = (lambda t: [x.surface for x in tok.tokenize(t)], "純 Python 形態素解析器、IPADIC 内蔵")
    except Exception as exc:  # noqa: BLE001
        out["janome (IPADIC)"] = (None, f"not available: {type(exc).__name__}")
    try:
        sp = importlib.import_module("sudachipy")
        d = sp.Dictionary()
        tk = d.create()
        for mode in ("A", "B", "C"):
            m = getattr(sp.SplitMode, mode)
            out[f"SudachiPy {mode}"] = ((lambda t, m=m, tk=tk: [x.surface() for x in tk.tokenize(t, m)]), f"SudachiDict core, 分割単位 {mode}")
    except Exception as exc:  # noqa: BLE001
        out["SudachiPy"] = (None, f"not available: {type(exc).__name__}")
    return out


def evaluate(items: list[dict]) -> dict:
    gold_items = [(i["text"], i["tokens"]) for i in items if i.get("tokens") and "".join(i["tokens"]).replace(" ", "") == i["text"].replace(" ", "")]
    texts = [i["text"] for i in items]
    res: dict = {"kotobacore": __version__, "tokenizer_version": TOKENIZER_VERSION, "gold_items": len(gold_items), "texts": len(texts), "tools": {}}
    for name, (fn, desc) in tokenizers().items():
        if fn is None:
            res["tools"][name] = {"description": desc, "status": "not run"}
            continue
        tp = fp = fn_ = 0
        for text, gold in gold_items:
            gb = _boundaries(gold)
            sb = _boundaries(fn(text))
            tp += len(gb & sb); fp += len(sb - gb); fn_ += len(gb - sb)
        p, r, f = _prf(tp, fp, fn_)
        # speed (warm): 3 passes over the 300 texts
        fn(texts[0])
        t0 = time.perf_counter()
        n_tok = 0
        for _ in range(3):
            for t in texts:
                n_tok += len(fn(t))
        dt = time.perf_counter() - t0
        res["tools"][name] = {
            "description": desc, "status": "ok", "boundary_precision": p, "boundary_recall": r, "boundary_f1": f,
            "ms_per_sentence": round(1000 * dt / (3 * len(texts)), 3), "tokens_per_s": int(n_tok / dt),
            "tokens_per_sentence": round(n_tok / (3 * len(texts)), 2),
        }
    # footprints
    foot: dict[str, str] = {"KotobaCore dict (resources/dict)": f"{_dir_size(ROOT / 'kotobacore' / 'resources' / 'dict') / 1e6:.1f} MB"}
    for mod, label in (("janome", "janome package"), ("sudachidict_core", "sudachidict_core"), ("sudachipy", "sudachipy")):
        try:
            m = importlib.import_module(mod)
            foot[label] = f"{_dir_size(Path(m.__file__).resolve().parent) / 1e6:.1f} MB"
        except Exception:  # noqa: BLE001
            foot[label] = "n/a"
    res["footprint"] = foot
    res["not_run"] = {"sentiment/emotion baselines (oseti, asari…)": "MeCab の Windows DLL がロードできず未実施 (mecab-python3 ImportError)"}
    return res


def to_markdown(res: dict) -> str:
    lines = [f"# Baseline comparison — KotobaCore {res['kotobacore']} (Karuizawa {res['tokenizer_version']})", "",
             f"gold: 人手アノテーション {res['gold_items']} 文の分割 (KotobaCore coarse 基準)、速度: {res['texts']} 文 × 3 周 (warm)", "",
             "| tool | boundary P | R | F1 | tokens/sentence | ms/sentence | tokens/s | note |", "|---|---|---|---|---|---|---|---|"]
    for name, t in res["tools"].items():
        if t["status"] != "ok":
            lines.append(f"| {name} | - | - | - | - | - | - | {t['description']} |")
            continue
        lines.append(f"| {name} | {t['boundary_precision']} | {t['boundary_recall']} | {t['boundary_f1']} | {t['tokens_per_sentence']} | {t['ms_per_sentence']} | {t['tokens_per_s']} | {t['description']} |")
    lines += ["", "## footprint", "", "| component | size |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in res["footprint"].items()]
    lines += ["", "## not run", ""] + [f"- {k}: {v}" for k, v in res["not_run"].items()]
    lines += ["", "注: gold は KotobaCore の粗い意味単位 (行った / 美味しかった = 1 語) なので、短単位の形態素解析器は再現率が高く精度が低く出る。",
              "境界再現率 (R) は「その道具の出力に gold の境界が含まれているか」で、細かく切る道具ほど有利。F1 は基準の差を含んだ比較。"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jsonl", default=str(ANNOTATED))
    ap.add_argument("--md", default=str(ROOT / "tools" / "benchmark" / "baseline_comparison.md"))
    ap.add_argument("--json", default=str(ROOT / "tools" / "benchmark" / "baseline_comparison.json"))
    args = ap.parse_args()
    items = [json.loads(l) for l in Path(args.jsonl).read_text(encoding="utf-8").splitlines() if l.strip()]
    res = evaluate(items)
    Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.md).write_text(to_markdown(res), encoding="utf-8")
    print(to_markdown(res))


if __name__ == "__main__":
    main()
