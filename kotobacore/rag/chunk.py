"""Semantic Chunking (RAG layer, FR-081 / FR-082): document → retrieval units.

Boundaries are decided, in order, by

1. headings (a heading paragraph always starts a new chunk and is prepended
   to the chunk that follows it);
2. paragraph boundaries once the chunk has reached ``min_chars``;
3. topic shift: the noun-set overlap (Jaccard) between the chunk so far and
   the next sentence falls below ``topic_threshold`` while no entity
   continues — only after ``min_chars``;
4. size: adding the sentence would exceed ``max_chars`` (a single sentence
   longer than ``max_chars`` becomes its own chunk — fixed-length splitting
   is never applied inside a sentence).

Each chunk carries paragraph / sentence / entity ids, keywords (frequent
nouns), topics (TOPIC entities + top keywords) and a summary hint (first
sentence) — FR-082.
"""

from __future__ import annotations

import re
from collections import Counter

from kotobacore.core.ir import AnalysisResult, DocumentChunk, Sentence
from kotobacore.core.syntax import is_fence_line
from kotobacore.dictionary import DictionaryBundle

_MD_HEADING = re.compile(r"^(#{1,6})\s*(.+?)\s*#*\s*$")
# "1. 50〜100発話を人手でラベル付け" — a Markdown ordered-list item, not a section label
_NUMBERED_ITEM = re.compile(r"^[0-9０-９]{1,2}[.．)）]\s+\S")
_CODE_LEAD_MAX = 80  # chars of the sentence introducing a code block carried as chunk context


def _heading_level(text: str) -> int:
    """Markdown # count; other heading markers (【 ■ 第N章 …) count as level 2."""
    m = _MD_HEADING.match(text.strip())
    if m:
        return len(m.group(1))
    return 2


def _heading_label(text: str) -> str:
    m = _MD_HEADING.match(text.strip())
    return m.group(2) if m else text.strip()


def _is_table_row(text: str) -> bool:
    t = text.strip()
    return t.startswith("|") and t.count("|") >= 2


def _is_table_separator(text: str) -> bool:
    t = text.strip().replace("|", "").replace(":", "").replace("-", "").replace(" ", "")
    return _is_table_row(text) and t == ""


def _nouns(result: AnalysisResult, sentence: Sentence, stopwords: set[str]) -> list[str]:
    by_id = {t.id: t for t in result.tokens}
    out: list[str] = []
    for tid in sentence.token_ids:
        t = by_id.get(tid)
        if t is None or "名詞" not in t.pos or "代名詞" in t.pos or "数詞" in t.pos:
            continue
        if len(t.surface) < 2 or t.surface in stopwords:
            continue
        out.append(t.normalized or t.surface)
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def chunk_document(
    result: AnalysisResult,
    bundle: DictionaryBundle,
    *,
    max_chars: int = 400,
    min_chars: int = 80,
    topic_threshold: float = 0.05,
) -> list[DocumentChunk]:
    if not result.sentences:
        return []
    stopwords = bundle.stopword_set()
    text = result.text.original
    sent_para = {sid: p.id for p in result.paragraphs for sid in p.sentence_ids}
    # Ordered-list items ("1. …") are list lines, not section headings (v0.5.4)
    heading_paras = {p.id for p in result.paragraphs if p.heading and not _NUMBERED_ITEM.match(text[p.begin:p.end].strip())}
    ent_by_id = {e.id: e for e in result.entities}

    chunks: list[DocumentChunk] = []
    cur: list[Sentence] = []
    cur_nouns: Counter[str] = Counter()
    cur_ents: set[str] = set()
    pending_headings: list[Sentence] = []  # consecutive heading lines waiting for the next chunk (none is dropped)
    heading_stack: list[tuple[int, str]] = []  # (level, label)
    cur_path: list[str] = []
    table_header: str | None = None
    cur_table_header: str | None = None
    in_code = False  # inside a fenced code block
    last_prose: str | None = None  # the sentence that introduces the next code block
    cur_code_lead: str | None = None  # lead-in carried as context when a chunk starts with / inside code

    def _flush() -> None:
        nonlocal cur, cur_nouns, cur_ents
        if not cur:
            return
        begin, end = cur[0].begin, cur[-1].end
        keywords = [w for w, _ in cur_nouns.most_common(10)]
        entity_ids = sorted(cur_ents, key=lambda i: ent_by_id[i].begin)
        topics = [ent_by_id[i].surface for i in entity_ids if ent_by_id[i].type == "TOPIC"]
        for k in keywords[:3]:
            if k not in topics:
                topics.append(k)
        # headings the chunk starts with are in its text already — keep them out of the context
        own_labels: set[str] = set()
        for s in cur:
            if sent_para.get(s.id) not in heading_paras:
                break
            own_labels.add(_heading_label(s.text))
        first = cur[len(own_labels)].text if len(cur) > len(own_labels) else cur[0].text
        path = [h for h in cur_path if h not in own_labels]
        context_parts = list(path)
        starts_with_row = _is_table_row(cur[0].text) and cur[0].text.strip() != cur_table_header and not _is_table_separator(cur[0].text)
        if cur_table_header and starts_with_row:
            context_parts.append(cur_table_header)
        if cur_code_lead and cur_code_lead not in text[begin:end]:
            context_parts.append(cur_code_lead)
        chunks.append(
            DocumentChunk(
                id=len(chunks), begin=begin, end=end, text=text[begin:end],
                paragraph_ids=sorted({sent_para[s.id] for s in cur if s.id in sent_para}),
                sentence_ids=[s.id for s in cur],
                entity_ids=entity_ids, keywords=keywords, topics=topics,
                summary_hint=first[:60],
                heading_path=list(cur_path), context=" > ".join(context_parts),
            )
        )
        cur, cur_nouns, cur_ents = [], Counter(), set()

    def _size() -> int:
        return (cur[-1].end - cur[0].begin) if cur else 0

    prev_para: int | None = None
    for s in result.sentences:
        pid = sent_para.get(s.id)
        if pid in heading_paras and not in_code:
            _flush()
            level = _heading_level(s.text)
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, _heading_label(s.text)))
            cur_path = [label for _lv, label in heading_stack]
            pending_headings.append(s)
            prev_para = pid
            table_header = None
            last_prose = None
            continue
        fence = is_fence_line(s.text)
        opening_fence = fence and not in_code
        # table header tracking: the first row of a table (followed by a separator row)
        if not _is_table_row(s.text):
            table_header = None
        elif table_header is None and not _is_table_separator(s.text):
            table_header = s.text.strip()
        nouns = _nouns(result, s, stopwords)
        ents = set(s.entity_ids)
        new_para = prev_para is not None and pid != prev_para
        if cur:
            size = _size()
            too_big = size + (s.end - cur[-1].end) > max_chars
            topic_shift = (
                size >= min_chars
                and not in_code
                and not opening_fence
                and _jaccard(set(cur_nouns), set(nouns)) < topic_threshold
                and not (cur_ents & ents)
                and bool(nouns)
            )
            # a code block stays with the sentence that introduces it: the paragraph
            # boundary in front of an opening fence is not a chunk boundary
            para_break = new_para and not opening_fence and not in_code
            if too_big or (para_break and size >= min_chars) or (topic_shift and new_para) or (topic_shift and size >= 2 * min_chars):
                _flush()
        if pending_headings and not cur:
            cur.extend(pending_headings)
            pending_headings = []
        if not cur:
            cur_table_header = table_header if (_is_table_row(s.text) and table_header != s.text.strip()) else None
            cur_code_lead = last_prose if (opening_fence or in_code) else None
        cur.append(s)
        cur_nouns.update(nouns)
        cur_ents |= ents
        prev_para = pid
        if fence:
            in_code = not in_code
        elif not in_code and not _is_table_row(s.text):
            last_prose = s.text.strip()[:_CODE_LEAD_MAX]
    if pending_headings and not cur:
        cur.extend(pending_headings)
    _flush()
    return chunks
