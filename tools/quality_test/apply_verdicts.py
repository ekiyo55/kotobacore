"""Apply the AI verdicts (verdicts_v1_ai.json) to the review sheet and the annotated draft.

Outputs
  annotated/review_sheet_v1_verdict.md   per-item verdicts + a tally of system-issue categories (the fix plan)
  annotated/annotated_v1_proposed.jsonl  the draft with the machine-applicable gold edits applied
                                         (F:tokens=sys, F:entities=sys / +=, F:<emotion>, F:<intent>, D)
  stdout                                 counts

Verdict codes (per aspect T/E/S/M/I): G:<cat> gold correct → system issue of category <cat>;
F:<value> fix gold; D delete gold sentiment (2026-09-08 polarity definition); H:<why> hold.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent / "annotated"
VERDICTS = HERE / "verdicts_v1_ai.json"
REVIEW_CSV = HERE / "review_sheet_v1.csv"
DRAFT = HERE / "annotated_v1_draft.jsonl"
OUT_MD = HERE / "review_sheet_v1_verdict.md"
OUT_JSONL = HERE / "annotated_v1_proposed.jsonl"

ASPECT = {"T": "tokens", "E": "entities", "S": "sentiment", "M": "emotion", "I": "intent"}
CAT_LABEL = {
    "tok": "分割 (トークナイザー)", "ner": "固有名詞・日付の抽出", "dict": "辞書に語を追加", "ctx": "文脈推論 (辞書外)",
    "adv": "逆接の節重み・評価語不足", "neg": "否定・反語 (litotes)", "cue": "意図: 個人手がかり (share_experience)", "rule": "意図ルール追加・誤発火",
    "holder": "第三者主体 → inform", "rhet": "修辞疑問", "fw": "全角英数", "canary": "括弧内の固有名 (canary)", "num": "数値表現 (小数・版番号・桁区切り・単位)",
}
EMOTIONS = {"joy", "sadness", "anger", "irritation", "anxiety", "admiration", "moved", "anticipation", "trust", "surprise", "disgust", "refusal", "agreement", "exaggeration"}
INTENTS = {"inform", "share_experience", "positive_feedback", "negative_feedback", "pricing_complaint", "question", "request", "support_request", "admiration", "agreement", "desire", "none"}


def parse(v: str) -> tuple[str, str, str]:
    """→ (code, value, note). 'G:dict わくわく…' → ('G', 'dict', 'わくわく…'); 'F:inform 挨拶' → ('F', 'inform', '挨拶')."""
    head, _, note = v.partition(" ")
    code, _, value = head.partition(":")
    return code, value, note


def main() -> None:
    verdicts = {k: v for k, v in json.loads(VERDICTS.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    review = {r["id"]: r for r in csv.DictReader(REVIEW_CSV.open(encoding="utf-8-sig"))}
    items = [json.loads(l) for l in DRAFT.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_id = {it["id"]: it for it in items}

    codes: Counter = Counter()
    cats: Counter = Counter()
    cat_items: dict[str, list[str]] = defaultdict(list)
    applied: Counter = Counter()
    held: list[str] = []
    for iid, asp in verdicts.items():
        it = by_id.get(iid)
        row = review.get(iid, {})
        if it is None:
            continue
        for a, v in asp.items():
            code, value, note = parse(v)
            codes[f"{code}:{ASPECT[a]}"] += 1
            if code == "G":
                cats[value] += 1
                cat_items[value].append(f"{iid}/{ASPECT[a]}")
            elif code == "H":
                held.append(f"{iid}/{ASPECT[a]}: {value} {note}")
            elif code == "D" and a == "S":
                it["sentiment"] = []
                applied["sentiment cleared"] += 1
            elif code == "F":
                if a == "T" and value == "tokens=sys":
                    it["tokens"] = [t for t in row.get("sys_tokens", "").split(" | ") if t]
                    applied["tokens ← system"] += 1
                elif a == "E" and value == "entities=sys":
                    it["entities"] = [{"surface": s.rsplit("/", 1)[0], "type": s.rsplit("/", 1)[1]} for s in row.get("sys_entities", "").split(", ") if "/" in s]
                    applied["entities ← system"] += 1
                elif a == "E" and value.startswith("entities+="):
                    surf, typ = value[len("entities+="):].rsplit("/", 1)
                    if not any(e["surface"] == surf for e in it.get("entities") or []):
                        it.setdefault("entities", []).append({"surface": surf, "type": typ})
                    applied["entities += "] += 1
                elif a == "E" and value.startswith("entities="):
                    surf, typ = value[len("entities="):].rsplit("/", 1)
                    it["entities"] = [{"surface": surf, "type": typ}]
                    applied["entities ← value"] += 1
                elif a == "M" and value in EMOTIONS:
                    prev = (it.get("emotion") or [{}])[0]
                    it["emotion"] = [{"holder": prev.get("holder", "speaker"), "about": prev.get("about"), "label": value}]
                    applied["emotion ← value"] += 1
                elif a == "I" and value in INTENTS:
                    it["intent"] = value
                    applied["intent ← value"] += 1
                else:
                    held.append(f"{iid}/{ASPECT[a]}: F not machine-applicable: {value} {note}")
    OUT_JSONL.write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items), encoding="utf-8")

    lines = ["# 人手評価セット レビュー — AI 判定案付き (verdicts_v1_ai.json)", "",
             f"判定 {sum(codes.values())} 件 / {len(verdicts)} 文。gold を修正 (F) {sum(v for k, v in codes.items() if k.startswith('F'))}、"
             f"gold の sentiment 削除 (D) {sum(v for k, v in codes.items() if k.startswith('D'))}、gold 正しい = system 課題 (G) {sum(v for k, v in codes.items() if k.startswith('G'))}、保留 (H) {sum(v for k, v in codes.items() if k.startswith('H'))}", "",
             "## A. system 課題の内訳（= 対処計画。件数順）", "", "| 分類 | 件数 | 内容 | 対処 |", "|---|---|---|---|"]
    fix = {
        "dict": "sentiment.csv / emotion.csv に語を追加（候補は各文の判定メモ）",
        "ner": "括弧内固有名 (「」『』)、漢数字の年月、相対日付 (先日/今期/来期/この前/こないだ/子どもの頃)、技術製品名、地名の辞書",
        "cue": "share_experience の個人手がかり拡充（体験動詞 〜てきた/〜した/泣いた/焦った、やった！、絵文字全域、身体状態）",
        "rule": "意図ルール: request (〜いただけますか/〜ください/〜てほしい/〜てくれない？/〜ないで/命令形)、desire (〜たい/〜といいな)、agreement (ほんとそれ/わかった/よね)、pricing (〜円もしたの/家賃上がる/値段の割に)、疑問文での評価語 (いい？) 抑止",
        "ctx": "辞書では取れない。gold は維持し『文脈推論』として計測外に扱うか、例文辞書 (emotion_examples.csv) で近似",
        "adv": "逆接後の節に評価語が無いケース。評価語追加で解決するものが大半",
        "holder": "主語が第三者 (部長は/彼は/村人たちは) の感情文は inform に（宛先付けの holder を意図に使う）",
        "tok": "分割の癖 (動詞+てる/ても、複合名詞、副詞 別に/いや/うーん)。ラティスの改良課題として記録",
        "neg": "否定の反転 (飽きない/破らなかった = positive、期待していない = negative)、原形読みが 〜なってる/〜かった に届かない",
        "rhet": "修辞疑問 (〜すぎん？/高くない？/何回〜ても) を question にしない・極性を取る",
        "canary": "「」括弧内の語は固有名として感情・評価から除外",
        "num": "小数 1.8・版番号 2.3.0・桁区切り 5,000・単位 ms・回数 (一度/二人) の扱い",
        "fw": "全角英数の店名 (NFKC 後の 123号 を QUANTITY にしない)",
    }
    for cat, n in cats.most_common():
        lines.append(f"| {cat} | {n} | {CAT_LABEL.get(cat, cat)} | {fix.get(cat, '')} |")
    lines += ["", "## B. 適用した gold 修正", ""] + [f"- {k}: {v}" for k, v in applied.most_common()]
    lines += ["", "## C. 保留 / 手動対応", ""] + [f"- {h}" for h in held]
    lines += ["", "## D. 文ごとの判定", ""]
    for iid, asp in verdicts.items():
        it = by_id.get(iid)
        if it is None:
            continue
        lines.append(f"**{iid}** — {it['text']}")
        for a, v in asp.items():
            lines.append(f"- {ASPECT[a]}: {v}")
        lines.append("")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("codes:", dict(codes))
    print("system-issue categories:", cats.most_common())
    print("applied:", dict(applied))
    print("held:", len(held))
    print("->", OUT_MD, OUT_JSONL)


if __name__ == "__main__":
    main()
