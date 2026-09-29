"""Search index terms (v1.1) — tokens for a keyword (BM25) index.

External evaluation (DD RAG, 2026-09-29, report §7-3): a keyword index needs
both a long compound and its parts (損害賠償請求訴訟 → 損害賠償請求訴訟 +
損害賠償 + 請求 + 訴訟), and both the canonical name and the written form
(D&O保険 → 役員賠償責任保険 + D&O保険). ``build_search_terms`` turns a
token list into such terms without touching the frozen IR:

* ``token``   the token's normalized form (canonical entity name, N2/N4 spelling)
* ``surface`` the written form when it differs from ``token``
* ``lemma``   dictionary form of a verb / adjective (払われていない → 払う)
* ``part``    pieces of a compound: script runs (連結EBITDA → 連結 / EBITDA,
              ネガティブ・プレッジ条項 → ネガティブ / プレッジ / 条項),
              kanji-compound words (損害 / 賠償 / 請求 / 訴訟, the same splitter as
              granularity="fine") and dictionary words inside it (損害賠償)
* ``synonym`` synonym.csv group members (opt-in)

Function words (particles, auxiliaries, symbols, whitespace) are dropped.
Every term carries original-text offsets for highlighting; a part gets its
own offsets when the token's written form maps 1:1 onto the original text,
the token's span otherwise.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from kotobacore.core.ir import Token
from kotobacore.core.token.lattice import _kanji_lexicon, _split_kanji_compound
from kotobacore.dictionary import DictionaryBundle

DROP_POS = ("助詞", "助動詞", "記号", "補助記号", "空白", "接尾辞")
# katakana without the middle dot ・ (U+30FB), so ネガティブ・プレッジ splits at it
_SCRIPT_RUN = re.compile(r"[0-9A-Za-z&]+|[\u4e00-\u9fff\u3005]+|[\u30a1-\u30fa\u30fc-\u30ff]+|[\u3041-\u309f]+")
_KANJI_RUN = re.compile(r"[一-鿿々]{3,}")
_MAX_LEX = 6


@dataclass
class SearchTerm:
    term: str
    kind: str  # token / surface / lemma / part / synonym
    begin: int
    end: int
    token_id: int


def _key(s: str, lower: bool) -> str:
    s = unicodedata.normalize("NFKC", s)
    return s.lower() if lower else s


def _parts(surface: str, lex: frozenset[str]) -> list[tuple[int, int]]:
    """(start, end) pieces of a compound written form, relative to ``surface``."""
    out: list[tuple[int, int]] = []
    runs = [(m.start(), m.end()) for m in _SCRIPT_RUN.finditer(surface)]
    if len(runs) > 1:
        out += [r for r in runs if r[1] - r[0] >= 2 and not surface[r[0]:r[1]].isdigit()]
    for m in _KANJI_RUN.finditer(surface):
        base, run = m.start(), m.group(0)
        pieces = _split_kanji_compound(run, lex - {run})  # a dictionary word is split too (未払残業代)
        if len(pieces) > 1:
            out += [(base + a, base + b) for a, b in pieces]
        # dictionary words inside the run (損害賠償 in 損害賠償請求訴訟)
        for i in range(len(run)):
            for ln in range(min(_MAX_LEX, len(run) - i), 1, -1):
                if (i, i + ln) != (0, len(run)) and run[i:i + ln] in lex:
                    out.append((base + i, base + i + ln))
    seen: set[tuple[int, int]] = set()
    uniq = []
    for p in out:
        if p[1] - p[0] >= 2 and p != (0, len(surface)) and p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def build_search_terms(
    tokens: list[Token],
    bundle: DictionaryBundle,
    *,
    lower: bool = True,
    surface: bool = True,
    lemma: bool = True,
    parts: bool = True,
    synonyms: bool = False,
) -> list[SearchTerm]:
    lex = _kanji_lexicon(bundle)[0] if parts else frozenset()
    syn_map = bundle.synonym_map() if synonyms else {}
    syn_groups = bundle.synonym_groups() if synonyms else {}
    out: list[SearchTerm] = []
    for tok in tokens:
        if (tok.pos or "").startswith(DROP_POS) or not tok.surface.strip():
            continue
        seen: set[str] = set()

        def add(text: str, kind: str, b: int, e: int, seen: set[str] = seen, tok_id: int = tok.id) -> None:
            k = _key(text, lower)
            if k and k not in seen and any(ch.isalnum() for ch in k):
                seen.add(k)
                out.append(SearchTerm(k, kind, b, e, tok_id))

        add(tok.normalized or tok.surface, "token", tok.begin, tok.end)
        if surface:
            add(tok.surface, "surface", tok.begin, tok.end)
        if lemma and (tok.pos or "").startswith(("動詞", "形容詞")) and tok.dictionary_form:
            add(tok.dictionary_form, "lemma", tok.begin, tok.end)
        if parts and (tok.pos or "").startswith("名詞"):
            one_to_one = len(tok.surface) == tok.end - tok.begin
            for a, b in _parts(tok.surface, lex):
                pb, pe = (tok.begin + a, tok.begin + b) if one_to_one else (tok.begin, tok.end)
                add(tok.surface[a:b], "part", pb, pe)
        if synonyms:
            canon = syn_map.get(tok.normalized or tok.surface)
            for w in syn_groups.get(canon, []) if canon else []:
                add(w, "synonym", tok.begin, tok.end)
    return out
