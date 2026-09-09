"""Document-level entity coreference (FR-034, v0.6.2).

Three passes over the entities of one document (original-text coordinates):

1. **Clustering** — mentions of the same thing are linked (union-find) when they
   share a normalized form, share a *core* form (honorific / title stripped for
   PERSON, legal prefix / suffix stripped for ORGANIZATION, 都道府県 stripped for
   LOCATION), or one core is a prefix of the other (田中 / 田中太郎, 北斗 / 北斗物流).
   The longest surface is the representative; every member gets
   ``canonical_id`` = representative id and the representative lists the other
   surfaces in ``aliases``.
2. **Alias mentions** — short forms of a representative (its core, its members'
   cores, the family-name token of a PERSON) that occur in the text as whole
   tokens but were not extracted as entities become new mentions
   (``source="coreference"``, lower confidence) in the same cluster — the
   retrieval side then sees 北斗 as 北斗物流.
3. **Anaphora** — 同社 / 同氏 / 彼 / 同市 / 同製品 … resolve to the nearest
   preceding mention of the matching type.

Entity ids stay unique (chunks and sentences reference them); the shared
identity is ``canonical_id``. Nothing here depends on the modules layer.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from kotobacore.core.ir import Entity, Sentence, Token
from kotobacore.core.ner import _LEGAL_PREFIX, _ORG_SUFFIX, _PERSON_SUFFIX

COREF_TYPES = frozenset({"PERSON", "ORGANIZATION", "LOCATION", "PRODUCT", "BRAND", "SERVICE", "WORK", "EVENT", "TOPIC"})
_PREFIX_LINK_TYPES = frozenset({"PERSON", "ORGANIZATION", "PRODUCT", "BRAND", "WORK"})
_ALIAS_TYPES = frozenset({"PERSON", "ORGANIZATION", "PRODUCT", "BRAND", "WORK"})
_LOC_STRIP = ("都", "道", "府", "県")
_PERSON_SUFFIXES = tuple(sorted(_PERSON_SUFFIX, key=len, reverse=True))
_ORG_LEGAL = tuple(sorted(set(_LEGAL_PREFIX) | {"株式会社", "有限会社", "合同会社"}, key=len, reverse=True))
_GENERIC_ORG_WORDS = frozenset(_ORG_SUFFIX)  # 商事 / 銀行 / 支店 … alone never identify an organization
_ANAPHORA: dict[str, str] = {
    "同社": "ORGANIZATION", "同行": "ORGANIZATION", "同校": "ORGANIZATION", "同店": "ORGANIZATION", "同グループ": "ORGANIZATION",
    "同氏": "PERSON", "彼": "PERSON", "彼女": "PERSON", "同人物": "PERSON", "同選手": "PERSON", "同監督": "PERSON",
    "同市": "LOCATION", "同県": "LOCATION", "同町": "LOCATION", "同地": "LOCATION", "同地域": "LOCATION", "同国": "LOCATION",
    "同製品": "PRODUCT", "同商品": "PRODUCT", "同機": "PRODUCT", "同モデル": "PRODUCT", "同サービス": "SERVICE",
    "同書": "WORK", "同作": "WORK", "同作品": "WORK", "同イベント": "EVENT", "同大会": "EVENT",
}
_KANJI_RE = re.compile(r"^[一-龿々〆]+$")


# ---------------------------------------------------------------- core forms


def core_form(entity_type: str, surface: str) -> str:
    """The identifying part of a mention: 田中さん → 田中, 株式会社山田商事 → 山田商事, 東京都 → 東京."""
    s = surface.strip()
    if entity_type == "PERSON":
        changed = True
        while changed:
            changed = False
            for suf in _PERSON_SUFFIXES:
                if s.endswith(suf) and len(s) > len(suf) + 1:
                    s = s[: -len(suf)]
                    changed = True
                    break
        return s
    if entity_type == "ORGANIZATION":
        for pre in _ORG_LEGAL:
            if s.startswith(pre) and len(s) > len(pre) + 1:
                s = s[len(pre):]
                break
        for suf in _ORG_LEGAL:
            if s.endswith(suf) and len(s) > len(suf) + 1:
                s = s[: -len(suf)]
                break
        return s.strip("・ 　")
    if entity_type == "LOCATION":
        for suf in _LOC_STRIP:
            if s.endswith(suf) and len(s) > 2:
                return s[:-1]
        return s
    return s


def _same_family(a: Entity, b: Entity) -> bool:
    if a.type == b.type:
        return True
    return {a.type, b.type} <= {"ORGANIZATION", "BRAND"} or {a.type, b.type} <= {"PRODUCT", "BRAND", "SERVICE"}


def _linked(a: Entity, b: Entity, ca: str, cb: str) -> bool:
    if not _same_family(a, b):
        return False
    if a.normalized and b.normalized and a.normalized == b.normalized:
        return True
    if ca and ca == cb:
        return True
    if a.type in _PREFIX_LINK_TYPES and b.type in _PREFIX_LINK_TYPES:
        short, long_ = (ca, cb) if len(ca) <= len(cb) else (cb, ca)
        if len(short) >= 2 and short != long_ and long_.startswith(short) and short not in _GENERIC_ORG_WORDS:
            return True
    return False


# ---------------------------------------------------------------- token search helpers


def _token_runs(tokens: list[Token], form: str, start_at: dict[int, int]) -> Iterable[tuple[int, int, list[int]]]:
    """Spans (begin, end, token_ids) where consecutive token surfaces concatenate to ``form``."""
    for i, t in enumerate(tokens):
        if not form.startswith(t.surface):
            continue
        acc = t.surface
        ids = [t.id]
        j = i
        while len(acc) < len(form) and j + 1 < len(tokens) and tokens[j + 1].begin == tokens[j].end:
            j += 1
            acc += tokens[j].surface
            ids.append(tokens[j].id)
            if not form.startswith(acc):
                break
        if acc == form:
            yield t.begin, tokens[j].end, ids


def _overlaps(begin: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(b < end and e > begin for b, e in spans)


def _family_name(rep: Entity, tokens: list[Token]) -> str | None:
    """First noun token of a PERSON mention when the name is made of several tokens (田中|太郎 → 田中)."""
    inside = [t for t in tokens if t.id in set(rep.token_ids)]
    if len(inside) >= 2 and "名詞" in inside[0].pos and len(inside[0].surface) >= 2 and _KANJI_RE.match(inside[0].surface):
        return inside[0].surface
    return None


# ---------------------------------------------------------------- main


def resolve_coreference(
    text: str,
    tokens: list[Token],
    entities: list[Entity],
    sentences: list[Sentence],
    stopwords: set[str] | None = None,
) -> list[Entity]:
    """Cluster ``entities`` in place and return the *new* mentions (alias / anaphora),
    already appended to ``entities`` and to the owning sentence's ``entity_ids``."""
    stopwords = stopwords or set()
    cands = [e for e in entities if e.type in COREF_TYPES]
    if not cands:
        return []
    cores = {e.id: core_form(e.type, e.surface) for e in cands}

    parent = {e.id: e.id for e in cands}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, a in enumerate(cands):
        for b in cands[i + 1:]:
            if _linked(a, b, cores[a.id], cores[b.id]):
                union(a.id, b.id)

    clusters: dict[str, list[Entity]] = {}
    for e in cands:
        clusters.setdefault(find(e.id), []).append(e)
    by_id = {e.id: e for e in entities}
    reps: dict[str, Entity] = {}
    for members in clusters.values():
        rep = max(members, key=lambda e: (len(e.surface), -e.begin))
        reps[rep.id] = rep
        for m in members:
            m.canonical_id = rep.id
        rep.aliases = sorted({m.surface for m in members if m.surface != rep.surface}, key=lambda s: (-len(s), s))

    taken = [(e.begin, e.end) for e in entities]
    new: list[Entity] = []
    next_idx = len(entities) + 1

    def add_mention(begin: int, end: int, ids: list[int], etype: str, rep: Entity, confidence: float) -> None:
        nonlocal next_idx
        ent = Entity(
            id=f"e{next_idx}", type=etype, surface=text[begin:end], begin=begin, end=end,
            normalized=rep.normalized or rep.surface, token_ids=ids, source="coreference",
            confidence=confidence, canonical_id=rep.id,
        )
        next_idx += 1
        entities.append(ent)
        by_id[ent.id] = ent
        new.append(ent)
        taken.append((begin, end))
        if ent.surface != rep.surface and ent.surface not in rep.aliases:
            rep.aliases.append(ent.surface)
        for s in sentences:
            if s.begin <= begin and end <= s.end:
                s.entity_ids.append(ent.id)
                break

    # ---- 2. alias mentions: short forms of the representative that occur as whole tokens
    for rep in reps.values():
        if rep.type not in _ALIAS_TYPES:
            continue
        members = [m for m in cands if m.canonical_id == rep.id]
        forms = {cores[m.id] for m in members} | {core_form(rep.type, s) for s in rep.aliases}
        fam = _family_name(rep, tokens) if rep.type == "PERSON" else None
        if fam:
            forms.add(fam)
        if rep.type in ("ORGANIZATION", "BRAND"):
            # abbreviation = core minus a trailing generic business word (北斗物流 → 北斗, 山田商事 → 山田)
            for f in list(forms):
                for suf in sorted(_GENERIC_ORG_WORDS, key=len, reverse=True):
                    if f.endswith(suf) and len(f) - len(suf) >= 2:
                        forms.add(f[: -len(suf)])
                        break
        for form in sorted(forms, key=len, reverse=True):
            if len(form) < 2 or form == rep.surface or form in stopwords or form in _GENERIC_ORG_WORDS:
                continue
            for begin, end, ids in _token_runs(tokens, form, {}):
                if _overlaps(begin, end, taken):
                    continue
                add_mention(begin, end, ids, rep.type, rep, 0.6)

    # ---- 3. anaphora: 同社 / 同氏 / 彼 … → nearest preceding mention of that type
    for word in sorted(_ANAPHORA, key=len, reverse=True):
        etype = _ANAPHORA[word]
        for begin, end, ids in _token_runs(tokens, word, {}):
            if _overlaps(begin, end, taken):
                continue
            before = [e for e in entities if e.end <= begin and e.type == etype and e.canonical_id]
            if not before:
                continue
            ante = max(before, key=lambda e: e.end)
            rep = by_id.get(ante.canonical_id or ante.id, ante)
            add_mention(begin, end, ids, etype, rep, 0.5)

    entities.sort(key=lambda e: (e.begin, e.end))
    return new


def coreference_clusters(entities: list[Entity]) -> list[list[Entity]]:
    """Mentions grouped by ``canonical_id`` (representative first), clusters of size ≥ 2 only."""
    groups: dict[str, list[Entity]] = {}
    for e in entities:
        if e.canonical_id:
            groups.setdefault(e.canonical_id, []).append(e)
    out = []
    for rep_id, members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=lambda e: (e.id != rep_id, e.begin))
        out.append(members)
    out.sort(key=lambda g: g[0].begin)
    return out
