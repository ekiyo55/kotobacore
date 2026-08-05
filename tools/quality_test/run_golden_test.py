"""実文ゴールデンセット回帰テスト.

テンプレート生成の 5000 例文テストが検出できない「実文の失敗」を捕まえる
回帰網。デモや実運用で指摘が出るたびに ``golden_set.csv`` へ 1 行追加する。

CSV 列 (空欄 = そのチェックをスキップ):
    emotion      期待 primary。``a|b`` で複数許容、``none`` は「感情なし」
    polarity     期待 polarity。``a|b`` 可
    intent       期待 intent label。``a|b`` 可、``unknown`` も指定可
    rag_includes RAG keywords に含まれるべき語。``a|b`` は「いずれか1つ」

実行:  python tools/quality_test/run_golden_test.py
終了コード: 全 PASS で 0、1 件でも FAIL で 1 (CI 組み込み用)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kotobacore import Analyzer  # noqa: E402


def _alts(cell: str) -> list[str]:
    return [a.strip() for a in cell.split("|") if a.strip()]


def check_row(a: Analyzer, row: dict[str, str]) -> list[str]:
    """Return a list of failure descriptions (empty = row passes)."""
    failures: list[str] = []
    r = a.analyze(row["text"])

    if row["emotion"]:
        want = _alts(row["emotion"])
        got = r.emotion.primary if r.emotion else None
        got_label = got if got is not None else "none"
        if got_label not in want:
            failures.append(f"emotion: got={got_label} want={row['emotion']}")

    if row["polarity"]:
        want = _alts(row["polarity"])
        got = (r.emotion.polarity if r.emotion else None) or "none"
        if got not in want:
            failures.append(f"polarity: got={got} want={row['polarity']}")

    if row["intent"]:
        want = _alts(row["intent"])
        got = (r.intent.label if r.intent else None) or "none"
        if got not in want:
            failures.append(f"intent: got={got} want={row['intent']}")

    if row["rag_includes"]:
        keywords = r.rag.keywords if r.rag else []
        want = _alts(row["rag_includes"])
        if not any(any(w in k for k in keywords) for w in want):
            failures.append(f"rag: {row['rag_includes']} not in {keywords}")

    return failures


def main() -> int:
    csv_path = Path(__file__).parent / "golden_set.csv"
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    a = Analyzer()
    # 外部辞書 (NRC) が無い環境 (CI 等) では needs_external=1 の行をスキップ
    has_external = bool(a._get_bundle().external_emotion)

    total = 0
    skipped = 0
    failed: list[tuple[str, str, list[str]]] = []
    per_category: dict[str, list[int]] = {}

    for row in rows:
        if (row.get("needs_external") or "").strip() == "1" and not has_external:
            skipped += 1
            continue
        total += 1
        fails = check_row(a, row)
        cat = row["category"]
        per_category.setdefault(cat, [0, 0])
        per_category[cat][1] += 1
        if fails:
            failed.append((row["id"], row["text"], fails))
        else:
            per_category[cat][0] += 1

    print("=" * 66)
    suffix = f" (外部辞書なしのため {skipped} 件スキップ)" if skipped else ""
    print(f"実文ゴールデンセット  {total - len(failed)}/{total} PASS{suffix}")
    print("=" * 66)
    for cat, (ok, n) in per_category.items():
        mark = "✅" if ok == n else "❌"
        print(f"  {mark} {cat}: {ok}/{n}")
    if failed:
        print("-" * 66)
        for gid, text, fails in failed:
            print(f"  [{gid}] {text}")
            for msg in fails:
                print(f"      {msg}")
    print("=" * 66)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
