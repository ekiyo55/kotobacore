"""Vocabulary evaluation and contamination detection (FR-072).

``vocab_report`` measures a vocabulary against texts — coverage (tokens
encoded as one piece), OOV (tokens that fell back to characters), ``<unk>``
rate, frequency distribution — and lists *contamination candidates*: pieces that
look like OCR damage, glued symbol runs, abnormal lengths, repeated characters
or NFKC duplicates. Candidates are hints for a human to review; nothing is
removed automatically.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable

from kotobacore.vocab.build import Vocabulary, _default_analyzer
from kotobacore.vocab.encode import EncodeStats, VocabEncoder

_SYMBOL_RUN = re.compile(r"[^\w\s぀-ヿ㐀-鿿]{3,}")
_REPEAT = re.compile(r"(.)\1{3,}")
_HALFWIDTH_KANA = re.compile(r"[｡-ﾟ]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f�﻿]")
_MIXED_GARBAGE = re.compile(r"(?=.*[぀-ヿ一-鿿])(?=.*[A-Za-z])(?=.*\d)")  # kana/kanji + latin + digit glued in one piece
ABNORMAL_LENGTH = 12


def contamination_reasons(piece: str, flags: Iterable[str]) -> list[str]:
    flags = set(flags)
    reasons: list[str] = []
    if _CONTROL.search(piece):
        reasons.append("control_char")
    if _HALFWIDTH_KANA.search(piece):
        reasons.append("halfwidth_kana")  # NFKC should have folded these — OCR / encoding damage
    if _SYMBOL_RUN.search(piece):
        reasons.append("symbol_run")
    if _REPEAT.search(piece):
        reasons.append("repeated_char")
    if len(piece) >= ABNORMAL_LENGTH and "ascii" not in flags:
        reasons.append("abnormal_length")
    if len(piece) > 1 and _MIXED_GARBAGE.search(piece):
        reasons.append("mixed_script")
    if unicodedata.normalize("NFKC", piece) != piece:
        reasons.append("not_nfkc")
    return reasons


def vocab_report(vocab: Vocabulary, texts: Iterable[str], *, analyzer=None, top: int = 20) -> dict:
    analyzer = analyzer or _default_analyzer(vocab.granularity)
    enc = VocabEncoder(vocab, analyzer)
    stats = EncodeStats()
    piece_use: Counter[str] = Counter()
    n_texts = 0
    for text in texts:
        if not text or not text.strip():
            continue
        n_texts += 1
        for p in enc.pieces(text, stats=stats):
            piece_use[p] += 1
    n_tok = stats.tokens or 1
    n_ids = stats.ids or 1

    entries = vocab.entries
    words = [e for e in entries if "char" not in e.flags]
    total_freq = sum(e.freq for e in entries) or 1
    top10 = sum(e.freq for e in sorted(entries, key=lambda e: -e.freq)[:10])
    singletons = sum(1 for e in words if e.freq == 1)
    length_hist = Counter(min(len(e.piece), 10) for e in entries)
    pos_hist = Counter(e.pos.split("-")[0] for e in entries)
    unused = [e.piece for e in words if piece_use.get(e.piece, 0) == 0]

    contamination = []
    nfkc_groups: dict[str, list[str]] = {}
    for e in entries:
        nfkc_groups.setdefault(unicodedata.normalize("NFKC", e.piece), []).append(e.piece)
        reasons = contamination_reasons(e.piece, e.flags)
        if reasons:
            contamination.append({"piece": e.piece, "id": e.id, "freq": e.freq, "reasons": reasons})
    duplicates = [v for v in nfkc_groups.values() if len(v) > 1]
    contamination.sort(key=lambda c: (-len(c["reasons"]), -c["freq"]))

    return {
        "vocab": {"version": vocab.version, "granularity": vocab.granularity, "size": len(vocab), "words": len(words),
                  "chars": len(entries) - len(words), "min_freq": vocab.min_freq, "kotobacore_version": vocab.kotobacore_version},
        "texts": n_texts,
        "coverage": {
            "tokens": stats.tokens, "whole_piece_rate": round(stats.whole / n_tok, 4), "oov_token_rate": round(stats.char_fallback / n_tok, 4),
            "unk_id_rate": round(stats.unk / n_ids, 4), "ids_per_token": round(stats.ids / n_tok, 3),
        },
        "distribution": {
            "top10_freq_share": round(top10 / total_freq, 4), "singleton_word_share": round(singletons / (len(words) or 1), 4),
            "unused_word_pieces": len(unused), "length_histogram": {str(k): v for k, v in sorted(length_hist.items())},
            "pos_histogram": dict(pos_hist.most_common()),
        },
        "contamination": {"count": len(contamination), "rate": round(len(contamination) / (len(entries) or 1), 4),
                          "candidates": contamination[:top], "nfkc_duplicates": duplicates[:top]},
    }


def report_markdown(rep: dict) -> str:
    v, c, d, k = rep["vocab"], rep["coverage"], rep["distribution"], rep["contamination"]
    lines = [
        f"# Vocabulary report — {v['version']} ({v['granularity']}, KotobaCore {v['kotobacore_version']})", "",
        f"size {v['size']} (words {v['words']} / chars {v['chars']}, min_freq {v['min_freq']}) | texts {rep['texts']}", "",
        "| metric | value |", "|---|---|",
        f"| tokens | {c['tokens']} |", f"| whole-piece rate (coverage) | {c['whole_piece_rate']} |",
        f"| OOV token rate (char fallback) | {c['oov_token_rate']} |", f"| <unk> id rate | {c['unk_id_rate']} |",
        f"| ids per token | {c['ids_per_token']} |", f"| top-10 frequency share | {d['top10_freq_share']} |",
        f"| singleton word share | {d['singleton_word_share']} |", f"| unused word pieces | {d['unused_word_pieces']} |",
        f"| contamination candidates | {k['count']} ({k['rate']}) |", "",
        "## piece length histogram", "", "| length | pieces |", "|---|---|",
    ]
    lines += [f"| {ln} | {n} |" for ln, n in d["length_histogram"].items()]
    lines += ["", "## POS", "", "| pos | pieces |", "|---|---|"]
    lines += [f"| {p} | {n} |" for p, n in d["pos_histogram"].items()]
    lines += ["", "## contamination candidates", "", "| piece | id | freq | reasons |", "|---|---|---|---|"]
    lines += [f"| {x['piece']} | {x['id']} | {x['freq']} | {', '.join(x['reasons'])} |" for x in k["candidates"]]
    if k["nfkc_duplicates"]:
        lines += ["", "## NFKC duplicates", ""] + [f"- {' / '.join(g)}" for g in k["nfkc_duplicates"]]
    return "\n".join(lines) + "\n"
