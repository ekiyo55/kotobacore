"""Query Understanding (RAG layer, FR-080): natural-language query → QueryIR.

The query is analyzed with the ordinary sentence pipeline (tokens, entities,
sentiment, keywords) and then structured:

- ``intent`` / ``answer_type`` — modules.intent.classify_query_intent
- ``target``      — what the question asks about: the nearest topic-marked
  noun phrase (X は / を / って / とは / について) before the question word
- ``constraints`` — time / location / quantity / organization / person
  filters taken from the entities
- ``expanded_terms`` — synonym.csv expansion of the target and keywords
- ``keywords`` / ``normalized_query`` — rag.optimizer keywords minus
  question words

Same vocabulary as the document IR so a retriever can match the two.
"""

from __future__ import annotations

import re

from kotobacore.core.attribution import _find_topic
from kotobacore.core.ir import AnalysisResult, QueryIR
from kotobacore.dictionary import DictionaryBundle
from kotobacore.modules.intent import classify_query_intent

_QUERY_MARKERS = frozenset({"は", "を", "が", "って", "とは", "について", "に関して", "の", "も"})
# Question words and answer-type nouns: they describe the *kind* of answer,
# not its content, so they are dropped from search terms (場所 / 人 / 何キロ).
_QUESTION_WORDS = re.compile(
    r"^(?:何|なに|いつ|どこ|誰|だれ|いくら|いくつ|どう|どの|どれ|どちら|なぜ|どんな|教えて|ください|下さい|ですか|ますか|"
    r"方法|やり方|理由|違い|一覧|リスト|意味|定義|おすすめ|こと|もの|ため|"
    r"場所|人|名前|数|回数|人数|何.{1,3})$"
)
# Synonym expansion is limited to a few alternatives per word — long
# expansions (場所 → ロケーション / プレイス / 所在地) drown the real terms.
_MAX_EXPANSIONS_PER_WORD = 2
_CONSTRAINT_TYPES = {
    "DATE": "time", "TIME": "time", "LOCATION": "location", "MONEY": "quantity", "QUANTITY": "quantity",
    "ORGANIZATION": "organization", "PERSON": "person", "PRODUCT": "product", "SERVICE": "product", "BRAND": "product",
    "EVENT": "event",
}


def build_query_ir(text: str, result: AnalysisResult, bundle: DictionaryBundle) -> QueryIR:
    normalized = result.text.normalized
    intent, answer_type = classify_query_intent(normalized)

    stopwords = bundle.stopword_set()
    keywords = [k for k in (result.rag.keywords if result.rag else []) if not _QUESTION_WORDS.match(k)]
    # Queries are short: single-character nouns (犬 / 車 / 本) are real keywords here,
    # even though rag.optimizer drops them for documents.
    # Product codes the tokenizer split (MX-500 → MX | 500) are carried as
    # PRODUCT entities; the tokens stay as keywords (the retriever sees the
    # same n-grams either way — duplicating the surface over-weights it).
    prev_surface = ""
    for t in result.tokens:
        after_nani = prev_surface in ("何", "なん", "何度", "幾")
        prev_surface = t.surface
        if after_nani:
            keywords = [k for k in keywords if k != t.surface]  # 何|キロ → drop キロ
            continue
        if (
            "名詞" in t.pos and "代名詞" not in t.pos and "数詞" not in t.pos and t.surface not in stopwords
            and not _QUESTION_WORDS.match(t.surface) and not t.surface.isdigit()
            and not any(t.surface in k for k in keywords)
        ):
            keywords.append(t.surface)

    # ---- target: last topic-marked noun phrase before the end of the query
    target: str | None = None
    tokens = result.tokens
    if tokens and normalized == result.text.original:
        found = _find_topic(tokens, result.entities, stopwords, 0, len(normalized), markers=_QUERY_MARKERS)
        if found is not None:
            b, e = found
            cand = normalized[b:e]
            if not _QUESTION_WORDS.match(cand):
                target = cand
    if target is None and keywords:
        # fall back to the last content keyword that is not an entity value
        ent_surfaces = {e.surface for e in result.entities}
        for k in reversed(keywords):
            if k not in ent_surfaces:
                target = k
                break

    # ---- constraints from entities
    constraints: dict[str, list[str]] = {}
    for ent in result.entities:
        key = _CONSTRAINT_TYPES.get(ent.type)
        if key is None:
            continue
        value = str(ent.value) if ent.value is not None else (ent.normalized or ent.surface)
        constraints.setdefault(key, []).append(value)

    # ---- synonym expansion (N5 意味正規化)
    groups = bundle.synonym_groups()
    smap = bundle.synonym_map()
    expanded: list[str] = []
    entity_surfaces = {e.surface for e in result.entities}
    # Expand the target, the keywords, and the *head* token of compound
    # keywords (経営ミーティング → ミーティング, not 経営): the modifier's
    # synonyms (マネジメント / 運営) are noise for retrieval.
    heads: list[str] = []
    toks = [t for t in result.tokens if "名詞" in t.pos and "代名詞" not in t.pos and "数詞" not in t.pos]
    run: list[str] = []
    for i, t in enumerate(toks):
        run.append(t.surface)
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if nxt is None or nxt.begin != t.end:  # end of a noun run: last token = head
            head = run[-1]
            if head in smap:
                heads.append(head)
            else:
                # head has no synonyms (室 in ミーティング室): fall back to the
                # longest modifier that does (ミーティング → 会議 / 打ち合わせ)
                mods = [w for w in run[:-1] if w in smap]
                if mods:
                    heads.append(max(mods, key=len))
            run = []
    for word in [target, *keywords, *heads]:
        if not word or word in entity_surfaces or _QUESTION_WORDS.match(word):
            continue
        canonical = smap.get(word)
        if canonical is None:
            continue
        added = 0
        for w in groups.get(canonical, []):
            if w != word and w not in expanded and w not in keywords:
                expanded.append(w)
                added += 1
                if added >= _MAX_EXPANSIONS_PER_WORD:
                    break

    return QueryIR(
        original=text,
        normalized_query=" ".join(keywords) if keywords else normalized,
        intent=intent,
        answer_type=answer_type,
        target=target,
        entities=list(result.entities),
        constraints=constraints,
        keywords=keywords,
        expanded_terms=expanded,
        sentiment=result.sentiment.polarity if result.sentiment else None,
    )
