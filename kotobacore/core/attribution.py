"""Attribution (Core): who evaluates / feels what (FR-052 宛先付き評価・感情).

Given the scored affect expressions (core.lexicon), the entities (core.ner)
and the clause structure (core.syntax), attach to every expression

- ``target``  — the thing being evaluated / felt about: the nearest
  topic-marked noun (X は / が / も / って / なんて …) before the expression in
  the same clause, else the nearest noun in the clause, else the topic of the
  previous clause (「コーヒーはいまいちだけどケーキは神」 → 神 ← ケーキ);
- ``holder``  — the experiencer of an emotion: a PERSON entity marked as
  subject (X は / が) in the same clause, otherwise ``"speaker"``.

Heuristic and shallow by design (no dependency parser — 設計原則 2). All
positions are normalized-text coordinates; the Analyzer remaps them.
"""

from __future__ import annotations

from kotobacore.core.ir import Entity, Token
from kotobacore.core.lexicon import ScoredExpression
from kotobacore.core.syntax import Clause, clause_at

_TOPIC_MARKERS = frozenset({"は", "が", "も", "って", "なんて", "とか", "なら", "については", "に関しては", "の方は", "のほうは"})
_SUBJECT_MARKERS = frozenset({"は", "が", "も"})
_PRONOUNS = frozenset({"これ", "それ", "あれ", "ここ", "そこ", "こっち", "そっち", "私", "僕", "俺", "自分", "彼", "彼女"})


def _is_noun(tok: Token, stopwords: set[str]) -> bool:
    if "名詞" not in tok.pos or "代名詞" in tok.pos:
        return False
    if tok.surface in stopwords or tok.surface in _PRONOUNS:
        return False
    return len(tok.surface) >= 1 and not tok.surface.isdigit()


def _entity_at(entities: list[Entity], begin: int, end: int) -> Entity | None:
    for e in entities:
        if e.begin <= begin and end <= e.end:
            return e
    return None


def _noun_phrase_start(tokens: list[Token], idx: int, clause: Clause | None) -> int:
    """Walk left over adjacent noun tokens (新作 + プリン → 新作プリン)."""
    k = idx
    while k - 1 >= 0 and tokens[k - 1].end == tokens[k].begin and "名詞" in tokens[k - 1].pos and "代名詞" not in tokens[k - 1].pos and "数詞" not in tokens[k - 1].pos:
        if clause is not None and tokens[k - 1].begin < clause.start:
            break
        k -= 1
    return k


def _find_topic(
    tokens: list[Token], entities: list[Entity], stopwords: set[str], lo: int, hi: int, *, markers: frozenset[str]
) -> tuple[int, int] | None:
    """Nearest noun in [lo, hi) followed by a marker particle; else nearest noun."""
    marked: tuple[int, int] | None = None
    plain: tuple[int, int] | None = None
    for i, tok in enumerate(tokens):
        if tok.begin < lo or tok.end > hi:
            continue
        if not _is_noun(tok, stopwords):
            continue
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        start = tokens[_noun_phrase_start(tokens, i, None)].begin
        if start < lo:
            start = tok.begin
        span = (start, tok.end)
        if nxt is not None and nxt.begin == tok.end and nxt.surface in markers and "助詞" in nxt.pos:
            marked = span  # keep the last (nearest) one
        plain = span
    return marked or plain


def attach_attribution(
    text: str,
    tokens: list[Token],
    entities: list[Entity],
    clauses: list[Clause],
    scored: list[ScoredExpression],
    stopwords: set[str],
) -> None:
    """Fill target_* / holder_* on every ScoredExpression in place."""
    if not scored:
        return
    person_spans = [(e.begin, e.end, e) for e in entities if e.type == "PERSON"]

    for exp in scored:
        clause = clause_at(clauses, exp.begin)
        lo = clause.start if clause else 0
        if exp.target_text:
            continue  # preset by the lexicon overlay (課金高すぎ → 課金)
        # ---- target: same clause, before the expression
        found = _find_topic(tokens, entities, stopwords, lo, exp.begin, markers=_TOPIC_MARKERS)
        if found is None and clause is not None:
            # carry the previous clause's topic (逆接 / 並列)
            idx = clauses.index(clause)
            if idx > 0:
                prev = clauses[idx - 1]
                found = _find_topic(tokens, entities, stopwords, prev.start, prev.end, markers=_TOPIC_MARKERS)
        if found is None and clause is not None:
            # after the expression within the clause (〜な コーヒー): nearest following noun
            found = _find_topic(tokens, entities, stopwords, exp.end, clause.end, markers=frozenset())
            # only accept a directly adjacent noun (adjective + noun)
            if found is not None and found[0] != exp.end:
                found = None
        if found is not None:
            b, e = found
            ent = _entity_at(entities, b, e)
            exp.target_id = ent.id if ent else None
            exp.target_text = ent.surface if ent else text[b:e]

        # ---- holder: PERSON entity marked as subject in the same clause
        holder: Entity | None = None
        for b, e, ent in person_spans:
            if b < lo or e > exp.begin:
                continue
            nxt = next((t for t in tokens if t.begin == e), None)
            if nxt is not None and nxt.surface in _SUBJECT_MARKERS and "助詞" in nxt.pos:
                holder = ent
        if holder is not None:
            exp.holder_id = holder.id
            exp.holder_text = holder.surface
            # a person-subject topic is the holder, not the target
            if exp.target_id == holder.id:
                exp.target_id = None
                exp.target_text = None
        else:
            exp.holder_id = None
            exp.holder_text = None
