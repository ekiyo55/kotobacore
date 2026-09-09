"""Build the human review sheet for the annotated evaluation set (FR-100 人手評価セットのレビュー確定).

For each of the 300 AI-drafted items: gold labels next to the current system
output, disagreement flags per aspect (tokens / entities / sentiment / emotion /
intent), and a *review hint* that says what kind of decision the disagreement
needs — most importantly whether it is a per-item labelling question or a
**taxonomy gap** (a gold label the system cannot produce at all, e.g. intent
``inform`` / emotion ``surprise``). Output: Markdown (grouped, decisions first)
and CSV (one row per item, for spreadsheet review).

Usage (repository checkout):
  python tools/quality_test/build_review_sheet.py [--jsonl …] --md OUT.md --csv OUT.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kotobacore import Analyzer  # noqa: E402
from kotobacore._version import __version__  # noqa: E402

HERE = Path(__file__).resolve().parent
SYSTEM_INTENTS = {"admiration", "agreement", "desire", "negative_feedback", "positive_feedback", "pricing_complaint", "question", "request", "support_request",
                  "inform", "share_experience"}  # v0.6.5: inform / share_experience added to match the evaluation set
SYSTEM_EMOTIONS = {"admiration", "agreement", "anger", "anticipation", "anxiety", "exaggeration", "irritation", "joy", "moved", "refusal", "sadness",
                   "surprise", "trust", "disgust"}  # v0.6.5
# Where a gold label has no system counterpart, the mapping a reviewer most likely wants (to be confirmed)
INTENT_MAP_PROPOSAL = {"inform": "none (unknown)", "share_experience": "none (unknown) — or positive/negative_feedback when a stance is present", "none": "none"}
EMOTION_MAP_PROPOSAL = {"surprise": "近接なし → gold 側を維持し system の未対応として記録", "trust": "admiration か agreement に寄せる候補", "disgust": "irritation / anger に寄せる候補"}


def _boundaries(tokens: list[str]) -> set[int]:
    out, pos = set(), 0
    for t in tokens:
        pos += len(t)
        out.add(pos)
    return out


def _gold_polarity(item: dict) -> str | None:
    pols = [s["polarity"] for s in item.get("sentiment") or []]
    if not pols:
        return None
    c = Counter(pols)
    return c.most_common(1)[0][0] if len(c) == 1 or c.most_common(1)[0][1] > len(pols) / 2 else "mixed"


def review_rows(items: list[dict], analyzer: Analyzer) -> list[dict]:
    rows = []
    for item in items:
        text = item["text"]
        r = analyzer.analyze(text)
        row: dict = {"id": item["id"], "genre": item["genre"], "text": text, "note": item.get("note", ""), "flags": [], "hints": []}
        # tokens
        gold_t = item.get("tokens") or []
        sys_t = [t.surface for t in r.tokens]
        row["gold_tokens"], row["sys_tokens"] = " | ".join(gold_t), " | ".join(sys_t)
        if gold_t and "".join(gold_t).replace(" ", "") == "".join(sys_t).replace(" ", "") and gold_t != sys_t:
            gb, sb = _boundaries(gold_t), _boundaries(sys_t)
            row["flags"].append("tokens")
            finer = len(sb - gb); coarser = len(gb - sb)
            row["hints"].append(f"分割: system が gold より {'細かい' if finer > coarser else '粗い' if coarser > finer else '別の切り方'} ({len(gb ^ sb)} 境界差)")
        # entities
        gold_e = {(e["surface"], e["type"]) for e in item.get("entities") or []}
        sys_e = {(e.surface, e.type) for e in r.entities}
        row["gold_entities"] = ", ".join(f"{s}/{t}" for s, t in sorted(gold_e))
        row["sys_entities"] = ", ".join(f"{s}/{t}" for s, t in sorted(sys_e))
        if gold_e != sys_e:
            row["flags"].append("entities")
            miss, extra = gold_e - sys_e, sys_e - gold_e
            same_surface = {s for s, _ in miss} & {s for s, _ in extra}
            if same_surface:
                row["hints"].append(f"Entity 型違い: {sorted(same_surface)}")
            if miss - {(s, t) for s, t in miss if s in same_surface}:
                row["hints"].append("Entity 未検出: " + ", ".join(f"{s}/{t}" for s, t in sorted(miss) if s not in same_surface))
            if extra - {(s, t) for s, t in extra if s in same_surface}:
                row["hints"].append("Entity 過検出 (gold に無い — gold の漏れか system の誤り): " + ", ".join(f"{s}/{t}" for s, t in sorted(extra) if s not in same_surface))
        # sentiment
        gp = _gold_polarity(item)
        sp = r.sentiment.polarity if r.sentiment else None
        row["gold_sentiment"] = "; ".join(f"{s.get('target')}:{s['polarity']}" for s in item.get("sentiment") or []) or "-"
        row["sys_sentiment"] = f"{sp} (affect {r.sentiment.affect_polarity if r.sentiment else None}; " + "; ".join(f"{e.target_text}:{e.polarity}" for e in (r.sentiment.expressions if r.sentiment else [])) + ")"
        # predicate-like tokens that carry the stance (candidates for sentiment.csv / emotion.csv)
        preds = [(t.dictionary_form or t.surface) for t in r.tokens if t.pos.startswith(("形容詞", "形状詞", "動詞")) and len(t.dictionary_form or t.surface) >= 2]
        # dictionary candidates: adjectives / 形状詞 only — verbs (言う / 思う / なる …) are almost never evaluative words
        preds = [(t.dictionary_form or t.surface) for t in r.tokens if t.pos.startswith(("形容詞", "形状詞")) and len(t.dictionary_form or t.surface) >= 2]
        emo_words = [e.text for e in (r.emotion.expressions if r.emotion else [])]
        row["predicates"], row["emotion_words"] = preds, emo_words
        if (gp or None) != (sp or None):
            row["flags"].append("sentiment")
            if gp and not sp:
                if emo_words and not preds:
                    row["hints"].append(f"評価極性: gold あり / system なし。system は感情語 {emo_words} のみ検出 → 感情文なら gold の sentiment を削除、評価なら評価語を追加")
                else:
                    row["hints"].append(f"評価極性: gold あり / system なし。評価語候補 {preds} (sentiment.csv 未収録) / 感情語 {emo_words}")
                row["sentiment_candidates"] = [(p, gp) for p in preds]
            elif sp and not gp:
                row["hints"].append("評価極性: system あり / gold なし — gold の漏れか、system の評価語誤発火")
            else:
                row["hints"].append(f"評価極性: gold {gp} vs system {sp}")
        # emotion
        gold_l = [e["label"] for e in item.get("emotion") or []]
        prim = r.emotion.primary if r.emotion else None
        row["gold_emotion"] = ", ".join(gold_l) or ("(expected_no_emotion)" if item.get("expected_no_emotion") else "-")
        row["sys_emotion"] = prim or "-"
        if item.get("expected_no_emotion"):
            if prim:
                row["flags"].append("canary")
                row["hints"].append(f"カナリア誤検出: system={prim}")
        elif gold_l and prim not in gold_l:
            row["flags"].append("emotion")
            gap = [g for g in gold_l if g not in SYSTEM_EMOTIONS]
            if gap:
                row["hints"].append(f"感情【体系差】gold {gap} は system の体系に無い → {EMOTION_MAP_PROPOSAL.get(gap[0], '写像を決める')}")
            elif prim == "exaggeration":
                row["hints"].append("感情: system の exaggeration (強調表現) は gold 体系に無い — 強調語 (マジで/すぎ/やばい) を感情と数えるかの方針決め")
            elif prim is None:
                row["hints"].append(f"感情: system 未検出 — 感情語候補 {preds} (emotion.csv 未収録なら追加、無ければ gold は文脈推論)")
                row["emotion_candidates"] = [(p, gold_l[0]) for p in preds]
            else:
                row["hints"].append(f"感情: gold {gold_l} vs system {prim}")
        # intent
        gi = item.get("intent") or "none"
        si = r.intent.label if r.intent else None
        row["gold_intent"], row["sys_intent"] = gi, si or "-"
        ok = (gi == "none" and (si in (None, "unknown"))) or gi == si
        if not ok:
            row["flags"].append("intent")
            if gi not in SYSTEM_INTENTS and gi != "none":
                row["hints"].append(f"意図【体系差】gold '{gi}' は system の体系に無い → 提案: {INTENT_MAP_PROPOSAL.get(gi, 'system 側に意図を追加するか gold を none に')}")
            else:
                row["hints"].append(f"意図: gold {gi} vs system {si}")
        row["flag_str"] = ",".join(row["flags"])
        row["hint_str"] = " / ".join(row["hints"])
        rows.append(row)
    return rows


def to_markdown(rows: list[dict], items: list[dict]) -> str:
    n = len(rows)
    flagged = [r for r in rows if r["flags"]]
    kind_counts = Counter(f for r in rows for f in r["flags"])
    gold_intents = Counter(i.get("intent") or "none" for i in items)
    gap_intents = {k: v for k, v in gold_intents.items() if k not in SYSTEM_INTENTS and k != "none"}
    gold_emos = Counter(e["label"] for i in items for e in i.get("emotion") or [])
    gap_emos = {k: v for k, v in gold_emos.items() if k not in SYSTEM_EMOTIONS}
    lines = [f"# 人手評価セット レビューシート — KotobaCore {__version__} / annotated_v1_draft ({n} 文)", "",
             f"不一致あり {len(flagged)} / {n} 文。種類別: " + ", ".join(f"{k} {v}" for k, v in kind_counts.most_common()), "",
             "## 0. 先に決めること（体系差 = 個別判定ではなく方針）", "",
             "| 論点 | 件数 | 提案 |", "|---|---|---|"]
    for k, v in sorted(gap_intents.items(), key=lambda x: -x[1]):
        lines.append(f"| 意図 gold `{k}` は system 体系に無い | {v} | {INTENT_MAP_PROPOSAL.get(k, 'system に意図を追加 or gold を none に')} |")
    for k, v in sorted(gap_emos.items(), key=lambda x: -x[1]):
        lines.append(f"| 感情 gold `{k}` は system 体系に無い | {v} | {EMOTION_MAP_PROPOSAL.get(k, '写像を決める')} |")
    exag = sum(1 for r in rows if r["sys_emotion"] == "exaggeration" and "emotion" in r["flags"])
    lines.append(f"| system の `exaggeration` を感情として数えるか | {exag} | gold に無いラベル。『強調は感情ではない』なら system 側で primary から除外、認めるなら gold に追加 |")
    sent_gold_only = sum(1 for r in rows if "sentiment" in r["flags"] and "gold あり / system なし" in r["hint_str"])
    lines.append(f"| 評価極性: gold あり / system なし | {sent_gold_only} | 2026-09-08 決定『感情語は評価極性に含めない』で gold を再判定 (感情文なら sentiment を空に) |")
    # ---- aggregated dictionary candidates (review the words, not the sentences)
    sent_c: Counter = Counter()
    emo_c: Counter = Counter()
    for r in rows:
        for w, pol in r.get("sentiment_candidates", []):
            sent_c[(w, pol)] += 1
        for w, lab in r.get("emotion_candidates", []):
            emo_c[(w, lab)] += 1
    lines += ["", "## 0.5 辞書追加候補（語で判断すれば文を見ずに済む分）", "",
              f"### sentiment.csv 候補（gold に評価極性あり・system 未検出の文の述語、{len(sent_c)} 語）", "",
              "| 語 | gold 極性 | 文数 | 採否 |", "|---|---|---|---|"]
    lines += [f"| {w} | {pol} | {n} | [ ] 追加 [ ] 感情語(除外) [ ] 評価語ではない |" for (w, pol), n in sent_c.most_common()]
    lines += ["", f"### emotion.csv 候補（gold に感情あり・system 未検出の文の述語、{len(emo_c)} 語）", "",
              "| 語 | gold 感情 | 文数 | 採否 |", "|---|---|---|---|"]
    lines += [f"| {w} | {lab} | {n} | [ ] 追加 [ ] 文脈推論(辞書外) |" for (w, lab), n in emo_c.most_common()]
    lines += ["", "## 1. 個別レビュー（不一致のある文のみ、ジャンル順）", ""]
    by_genre: dict[str, list[dict]] = defaultdict(list)
    for r in flagged:
        by_genre[r["genre"]].append(r)
    for genre in ("sns", "business", "tech", "literary", "conversation"):
        rs = by_genre.get(genre, [])
        if not rs:
            continue
        lines += [f"### {genre} ({len(rs)} 文)", ""]
        for r in rs:
            lines += [f"**{r['id']}** `{r['flag_str']}` — {r['text']}", ""]
            if "tokens" in r["flags"]:
                lines += [f"- tokens gold: {r['gold_tokens']}", f"- tokens sys : {r['sys_tokens']}"]
            if "entities" in r["flags"]:
                lines += [f"- entities gold: {r['gold_entities'] or '-'} / sys: {r['sys_entities'] or '-'}"]
            if "sentiment" in r["flags"]:
                lines += [f"- sentiment gold: {r['gold_sentiment']} / sys: {r['sys_sentiment']}"]
            if "emotion" in r["flags"] or "canary" in r["flags"]:
                lines += [f"- emotion gold: {r['gold_emotion']} / sys: {r['sys_emotion']}"]
            if "intent" in r["flags"]:
                lines += [f"- intent gold: {r['gold_intent']} / sys: {r['sys_intent']}"]
            lines += [f"- 判断メモ: {r['hint_str']}"]
            if r["note"]:
                lines += [f"- 下書きの note: {r['note']}"]
            lines += ["- [ ] gold 正しい　[ ] gold を修正 → ______　[ ] 方針待ち", ""]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jsonl", default=str(HERE / "annotated" / "annotated_v1.jsonl"))  # v0.6.7: the confirmed set (the AI draft stays as annotated_v1_draft.jsonl)
    ap.add_argument("--md", default=str(HERE / "annotated" / "review_sheet_v1.md"))
    ap.add_argument("--csv", default=str(HERE / "annotated" / "review_sheet_v1.csv"))
    args = ap.parse_args()
    items = [json.loads(l) for l in Path(args.jsonl).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = review_rows(items, Analyzer())
    Path(args.md).write_text(to_markdown(rows, items), encoding="utf-8")
    cols = ["id", "genre", "text", "flag_str", "hint_str", "gold_tokens", "sys_tokens", "gold_entities", "sys_entities",
            "gold_sentiment", "sys_sentiment", "gold_emotion", "sys_emotion", "gold_intent", "sys_intent", "note"]
    with Path(args.csv).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols + ["verdict", "corrected_gold"])
        w.writeheader()
        for r in rows:
            w.writerow({**{c: r.get(c, "") for c in cols}, "verdict": "", "corrected_gold": ""})
    flagged = sum(1 for r in rows if r["flags"])
    print(f"{len(rows)} items, {flagged} flagged → {args.md}, {args.csv}")


if __name__ == "__main__":
    main()
