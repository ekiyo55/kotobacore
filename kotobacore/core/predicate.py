"""Predicate-argument structure, relations and events (Core, FR-023 / 040 / 041).

No dependency parser (設計原則 2). Per clause (core.syntax) the predicate is
the last content word — a verb / adjective token, or a noun carrying a
copula / サ変 tail (設立し, 発売されます, 中止になった, ケーキは神) — and its
arguments are the noun phrases in front of it that are marked with a case
particle:

    が → subject      は / も → topic (subject when no が)   を → object
    に / へ → goal    で → location (LOCATION entity) or means
    から → source     まで → until     と → with     より → than
    DATE / TIME entities → time (whatever the particle)

Relations (FR-040) pair the subject with every other argument through the
predicate; events (FR-041) are one per predicate with typed roles. Event
types come from a small verb lexicon (行く → GO, 発表 → ANNOUNCE …) and fall
back to the predicate lemma.

Positions are normalized-text coordinates; the Analyzer remaps them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from kotobacore.core.ir import Argument, Entity, Event, Predicate, Relation, Token
from kotobacore.core.syntax import Clause

# ---------------------------------------------------------------------------
# Tail / particle inventories
# ---------------------------------------------------------------------------

_AUX_RE = re.compile(
    r"^(?:"
    r"(?:に)?な(?:る|った|ります|りました|らない|らなかった)"
    r"|(?:さ|し|でき)?(?:れ|せ)?(?:る|た|て|ます|ました|ません|ませんでした|ない|なかった|なくて|ず|ている|ていた|てる|てた|ていない|てない|ておく|ておいた)"
    r"|し(?:て|た|ます|ました|ない|なかった|よう|たい|たかった)?|する|でき(?:る|た|ない|なかった|ます|ました)"
    r"|だ|です|だった|でした|である|でしょう|だろう|じゃない|ではない|じゃなかった|ではなかった|ですね|ですよ"
    r"|(?:い|あ)(?:る|た|ます|ました|ません|りません|りました|ります)"
    r"|たい|たかった|ほしい|らしい|そうだ|そうです|ようだ|ようです|みたい|かもしれない|かもしれません|はず|べき"
    r"|ね|よ|な|わ|ぞ|か|かな|かしら|っけ"
    r")$"
)
_CONJ_END = frozenset({"けど", "けれど", "けれども", "が", "ので", "から", "し", "て", "ても", "のに", "ば", "たら", "なら", "と", "ながら", "つつ", "ため", "ために"})
_CASE_ROLE = {"が": "subject", "は": "topic", "も": "topic", "を": "object", "に": "goal", "へ": "goal",
              "で": "location", "から": "source", "まで": "until", "と": "with", "より": "than", "には": "goal", "では": "location", "とは": "with"}
_NEG_RE = re.compile(r"(?:ない|なかった|なくて|ません|ませんでした|ず|ぬ)$")

# Event type lexicon: predicate surface prefix → type (longest prefix wins).
_EVENT_TYPES: dict[str, str] = {
    "行": "GO", "来": "COME", "帰": "RETURN", "戻": "RETURN", "到着": "ARRIVE", "出発": "DEPART", "訪問": "VISIT", "訪れ": "VISIT",
    "買": "BUY", "購入": "BUY", "売": "SELL", "販売": "SELL", "発売": "RELEASE", "支払": "PAY", "払": "PAY", "注文": "ORDER", "予約": "RESERVE",
    "会": "MEET", "見": "SEE", "観": "SEE", "聞": "HEAR", "言": "SAY", "話": "TALK", "書": "WRITE", "読": "READ", "送": "SEND", "受け": "RECEIVE", "届": "DELIVER",
    "作": "MAKE", "使": "USE", "食べ": "EAT", "飲": "DRINK", "開": "OPEN", "開催": "HOLD", "開く": "HOLD", "開い": "HOLD", "設立": "FOUND", "発表": "ANNOUNCE",
    "導入": "ADOPT", "出席": "ATTEND", "参加": "ATTEND", "決定": "DECIDE", "決め": "DECIDE", "発生": "OCCUR", "起き": "OCCUR", "起こ": "OCCUR",
    "開始": "START", "始め": "START", "始ま": "START", "終了": "END", "終わ": "END", "中止": "CANCEL", "契約": "CONTRACT", "提携": "PARTNER", "買収": "ACQUIRE",
    "評価": "EVALUATE", "検討": "CONSIDER", "報告": "REPORT", "依頼": "REQUEST", "承認": "APPROVE", "採用": "HIRE", "退職": "RESIGN", "就任": "APPOINT",
    "移転": "MOVE", "引っ越": "MOVE", "壊": "BREAK", "故障": "BREAK", "修理": "REPAIR", "更新": "UPDATE", "変更": "CHANGE", "追加": "ADD", "削除": "DELETE",
    "登録": "REGISTER", "なっ": "BECOME", "なる": "BECOME", "泣": "CRY", "笑": "LAUGH", "喜": "REJOICE", "怒": "GET_ANGRY", "驚": "SURPRISE",
    "働": "WORK", "勤め": "WORK", "学": "STUDY", "勉強": "STUDY", "教え": "TEACH", "紹介": "INTRODUCE", "説明": "EXPLAIN", "提案": "PROPOSE", "実施": "CONDUCT", "公開": "PUBLISH", "投稿": "POST",
}


@dataclass
class _NP:
    begin: int
    end: int
    token_ids: list[int]


def _is_nounish(tok: Token) -> bool:
    return tok.pos.startswith(("名詞", "接尾辞")) and "代名詞" not in tok.pos


def _np_before(tokens: list[Token], idx: int, lo: int) -> _NP | None:
    """Noun phrase ending at token idx (inclusive), extended left over adjacent nouns."""
    if idx < 0 or not _is_nounish(tokens[idx]):
        return None
    k = idx
    while k - 1 >= 0 and tokens[k - 1].end == tokens[k].begin and tokens[k - 1].begin >= lo and (
        _is_nounish(tokens[k - 1]) or tokens[k - 1].pos.startswith("連体詞") or tokens[k - 1].surface in ("の",)
    ):
        # 「AのB」 is kept as one phrase only when A is a noun as well
        if tokens[k - 1].surface == "の":
            if not (k - 2 >= 0 and _is_nounish(tokens[k - 2]) and tokens[k - 2].end == tokens[k - 1].begin):
                break
            k -= 2
            continue
        k -= 1
    # drop a leading 連体詞 (この / あの) from the span
    while k < idx and tokens[k].pos.startswith("連体詞"):
        k += 1
    return _NP(tokens[k].begin, tokens[idx].end, [t.id for t in tokens[k : idx + 1]])


def _entity_covering(entities: list[Entity], b: int, e: int) -> Entity | None:
    best: Entity | None = None
    for ent in entities:
        overlaps = ent.begin <= e and ent.end >= b and (ent.begin <= b or ent.end >= e)
        if overlaps and (best is None or (ent.end - ent.begin) > (best.end - best.begin)):
            best = ent
    return best


def _event_type(surface: str, pos: str, nominal: bool) -> str:
    best = ""
    for key in _EVENT_TYPES:
        if surface.startswith(key) and len(key) > len(best):
            best = key
    if best:
        return _EVENT_TYPES[best]
    if pos.startswith("形容詞") or nominal:
        return "STATE"
    return surface


def extract_predicates(
    text: str,
    tokens: list[Token],
    entities: list[Entity],
    clauses: list[Clause],
) -> tuple[list[Predicate], list[Relation], list[Event]]:
    predicates: list[Predicate] = []
    relations: list[Relation] = []
    events: list[Event] = []
    if not tokens:
        return predicates, relations, events

    # sentence-final clause detection (for copula-less nominal predicates)
    def _is_final(ci: int) -> bool:
        c = clauses[ci]
        return ci + 1 >= len(clauses) or text[c.end - 1 : c.end] in "。！？!?\n" or clauses[ci + 1].start > c.end

    for ci, clause in enumerate(clauses):
        ctoks = [t for t in tokens if t.begin >= clause.start and t.end <= clause.end and not t.pos.startswith(("記号", "空白"))]
        if not ctoks:
            continue
        idx = len(ctoks) - 1
        tail: list[Token] = []
        # peel conjunctive particles and auxiliary tails from the right
        while idx >= 0:
            t = ctoks[idx]
            if t.pos.startswith("助詞") and (t.surface in _CONJ_END or _AUX_RE.match(t.surface)):
                tail.insert(0, t)
                idx -= 1
                continue
            if t.pos.startswith("助動詞"):
                tail.insert(0, t)
                idx -= 1
                continue
            break
        if idx < 0:
            continue
        head = ctoks[idx]
        aux = [t for t in tail if not (t.surface in _CONJ_END and not _AUX_RE.match(t.surface))]
        nominal = False
        if head.pos.startswith(("動詞", "形容詞", "形状詞")):
            pass
        elif _is_nounish(head) and (aux or _is_final(ci)):
            # サ変 / copula predicate (設立 + し, 中止 + になった, ケーキは神)
            if not aux and not any(t.surface in ("は", "が", "も") for t in ctoks[:idx]):
                continue
            nominal = True
        else:
            continue

        pred_end = aux[-1].end if aux else head.end
        pred_tokens = [head, *aux]
        surface = text[head.begin:pred_end]
        lemma = head.dictionary_form or head.surface
        negated = bool(_NEG_RE.search(surface)) or any(_NEG_RE.search(t.surface) for t in aux)
        voice = "active"
        if any(t.surface.startswith(("され", "れ")) or "される" in t.surface for t in aux) or "され" in head.surface or "られ" in head.surface:
            voice = "passive"
        elif any(t.surface.startswith("させ") for t in aux):
            voice = "causative"

        # ---- arguments
        args: list[Argument] = []
        used: set[int] = set()
        for j in range(idx - 1, -1, -1):
            t = ctoks[j]
            if not t.pos.startswith("助詞") or t.surface not in _CASE_ROLE:
                continue
            k = tokens.index(t)
            np = _np_before(tokens, k - 1, clause.start)
            if np is None or np.begin in used:
                continue
            used.add(np.begin)
            role = _CASE_ROLE[t.surface]
            ent = _entity_covering(entities, np.begin, np.end)
            if ent is not None and ent.type in ("DATE", "TIME"):
                role = "time"
            elif role == "location" and not (ent is not None and ent.type == "LOCATION"):
                role = "means" if ent is None else "location"
            args.append(Argument(role=role, text=text[np.begin:np.end], begin=np.begin, end=np.end,
                                 entity_id=ent.id if ent else None, token_ids=np.token_ids))
        # bare DATE/TIME entities in the clause without a particle → time
        for ent in entities:
            if ent.type in ("DATE", "TIME") and clause.start <= ent.begin and ent.end <= head.begin and ent.begin not in used:
                used.add(ent.begin)
                args.append(Argument(role="time", text=ent.surface, begin=ent.begin, end=ent.end, entity_id=ent.id, token_ids=list(ent.token_ids)))
        args.sort(key=lambda a: a.begin)
        # topic becomes the subject when no が-subject exists
        if not any(a.role == "subject" for a in args):
            for a in args:
                if a.role == "topic":
                    a.role = "subject"
                    break

        pid = f"p{len(predicates) + 1}"
        predicates.append(Predicate(
            id=pid, text=surface, lemma=lemma, begin=head.begin, end=pred_end,
            token_ids=[t.id for t in pred_tokens], clause_index=ci, arguments=args,
            negated=negated, voice=voice, nominal=nominal,
        ))

        # ---- event
        etype = _event_type(head.surface, head.pos, nominal)
        by_role: dict[str, Argument] = {}
        for a in args:
            by_role.setdefault(a.role, a)
        subj = by_role.get("subject")
        obj = by_role.get("object")
        goal = by_role.get("goal")
        loc = by_role.get("location")
        tim = by_role.get("time")
        if nominal and subj is not None and obj is None and goal is None:
            # 「ケーキは神」: the predicate noun is the attribute of the subject
            attr_text = head.surface
        else:
            attr_text = None
        events.append(Event(
            id=f"ev{len(events) + 1}", type=etype, predicate=lemma, predicate_id=pid,
            agent=subj.entity_id if subj else None, agent_text=subj.text if subj else None,
            object=obj.entity_id if obj else None, object_text=obj.text if obj else (attr_text),
            goal=goal.entity_id if goal else None, goal_text=goal.text if goal else None,
            location=loc.entity_id if loc else None, location_text=loc.text if loc else None,
            time=tim.entity_id if tim else None, time_text=tim.text if tim else None,
            negated=negated, voice=voice, begin=clause.start, end=clause.end,
        ))

        # ---- relations: subject → other arguments through the predicate
        if subj is not None:
            for a in args:
                if a is subj or a.role in ("time", "topic"):
                    continue
                relations.append(Relation(
                    id=f"r{len(relations) + 1}",
                    source=subj.entity_id, source_text=subj.text,
                    relation=etype if etype not in ("STATE",) else lemma,
                    role=a.role,
                    target=a.entity_id, target_text=a.text,
                    predicate_id=pid, negated=negated, begin=clause.start, end=clause.end,
                ))
    return predicates, relations, events
