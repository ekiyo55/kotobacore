"""Analyzer: KotobaCore main entry point.

Per 04_内部設計書 §5 and 06_API §4. Phase 13 wires all preceding phases:

    normalize → tokenize → semantic_tokens → chunks → emotion → intent → rag
"""

from __future__ import annotations

import datetime as _dt
import os

from kotobacore._version import __version__
from kotobacore.core.attribution import attach_attribution
from kotobacore.core.chunker import chunk as _chunk
from kotobacore.core.coreference import resolve_coreference
from kotobacore.core.entity import build_semantic_tokens
from kotobacore.core.ir import (
    SCHEMA_VERSION,
    AnalysisResult,
    EmotionResult,
    Entity,
    Event,
    IntentCandidate,
    IntentResult,
    KotobaError,
    MetaInfo,
    Paragraph,
    Predicate,
    QueryIR,
    RagResult,
    Relation,
    Sentence,
    SentimentResult,
    TextInfo,
    Token,
    TopicResult,
)
from kotobacore.core.lexicon import score_affect_expressions
from kotobacore.core.ner import extract_entities
from kotobacore.core.predicate import extract_predicates
from kotobacore.core.syntax import is_heading_line, split_clauses, split_paragraphs, split_sentences
from kotobacore.core.text import NormalizedText, normalize_with_map
from kotobacore.core.token import (
    KaruizawaBackend,
    TokenizerBackend,
    fold_emphatic_reduplication,
    heuristic_proper_noun_merge,
    merge_keep_as_unit,
    merge_okurigana_compounds,
    refine_verb_adjective_pos,
    split_hiragana_tokens,
)
from kotobacore.core.token.lattice import lattice_tokenize
from kotobacore.dictionary import (
    DictionaryBundle,
    load_default_bundle,
    load_user_bundle,
)
from kotobacore.errors import (
    E101_INVALID_UTF8,
    E102_UNSUPPORTED_CHARACTER,
    E201_TOKENIZATION_ERROR,
    E301_SENTENCE_BOUNDARY_ERROR,
    E302_ENTITY_ERROR,
    E303_PREDICATE_ERROR,
    E401_MODULE_ERROR,
    make_error,
)
from kotobacore.modules.emotion import detect_emotion
from kotobacore.modules.intent import classify_intent
from kotobacore.modules.sentiment import detect_sentiment
from kotobacore.modules.topic import detect_topics, merge_topics
from kotobacore.rag import optimize_rag
from kotobacore.rag.chunk import chunk_document
from kotobacore.rag.query import build_query_ir
from kotobacore.versions import component_versions

_COMPONENT_META: dict | None = None


def _component_meta() -> dict:
    """Component versions stamped into MetaInfo (NFR-002 reproducibility); computed once."""
    global _COMPONENT_META
    if _COMPONENT_META is None:
        v = component_versions(with_dictionaries=False)
        _COMPONENT_META = {"tokenizer": v["tokenizer"], "dictionary_set": v["dictionary_set"], "modules": v["modules"]}
    return dict(_COMPONENT_META)


def _char_tokens(text: str) -> list[Token]:
    """E201 fallback: one token per non-space character so downstream stages still run."""
    out: list[Token] = []
    for i, ch in enumerate(text):
        if ch.isspace():
            continue
        out.append(Token(id=len(out), surface=ch, normalized=ch, dictionary_form=ch, reading=None, pos="記号" if not ch.isalnum() else "名詞-普通名詞-一般", begin=i, end=i + 1, unknown=True))
    return out


class Analyzer:
    """Main entry point for KotobaCore."""

    def __init__(
        self,
        mode: str = "C",
        backend: str = "karuizawa",
        enable_semantic_chunk: bool = True,
        enable_emotion: bool = True,
        enable_sentiment: bool = True,
        enable_intent: bool = True,
        enable_rag: bool = True,
        config_path: str | None = None,
        user_dict_path: str | None = None,
        use_external_dictionaries: bool = True,
        pipeline: str | None = None,
        granularity: str = "coarse",
        enable_entities: bool = True,
        reference_date: _dt.date | None = None,
        enable_predicates: bool = True,
        enable_topics: bool = True,
        enable_coreference: bool = True,
    ) -> None:
        self.mode = mode
        self.backend = backend
        # Document-level entity coreference (FR-034, analyze_document only)
        self.enable_coreference = enable_coreference
        # Karuizawa の実行モード: "lattice" (v0.2 デフォルト — 格子+Viterbi の
        # 一発分割) または "cascade" (〜v0.1 の5段補修パス、互換用に残置)。
        # 環境変数 KOTOBACORE_PIPELINE で比較評価時に切替可能。
        self.pipeline = pipeline or os.environ.get("KOTOBACORE_PIPELINE", "lattice")
        # トークン粒度: "coarse" (意味単位、既定) / "fine" (語幹・送り仮名・活用語尾に
        # 分解 — LM 語彙用途)。lattice パイプラインのみ有効。analyze() では
        # 意味層 (chunks/emotion/intent/rag) は常に coarse トークンで計算し、
        # tokens / semantic_tokens だけが fine になる。
        if granularity not in ("coarse", "fine"):
            raise ValueError(f"Unknown granularity: {granularity}")
        self.granularity = granularity
        self.enable_semantic_chunk = enable_semantic_chunk
        self.enable_emotion = enable_emotion
        self.enable_sentiment = enable_sentiment
        self.enable_entities = enable_entities
        self.enable_predicates = enable_predicates
        self.enable_topics = enable_topics
        # Reference date for relative time expressions (今日 / 3日前 / 来週).
        self.reference_date = reference_date
        self.enable_intent = enable_intent
        self.enable_rag = enable_rag
        self.config_path = config_path
        self.user_dict_path = user_dict_path
        self.use_external_dictionaries = use_external_dictionaries

        self._backend: TokenizerBackend | None = None
        self._bundle: DictionaryBundle | None = None

    # ------------------------------------------------------------------
    # Lazy initialization
    # ------------------------------------------------------------------
    def _get_backend(self) -> TokenizerBackend:
        if self._backend is None:
            if self.backend == "karuizawa":
                self._backend = KaruizawaBackend()
            else:
                raise ValueError(f"Unknown backend: {self.backend}")
        return self._backend

    def _get_bundle(self) -> DictionaryBundle:
        if self._bundle is None:
            if self.use_external_dictionaries:
                try:
                    self._bundle = load_user_bundle()
                except Exception:  # noqa: BLE001
                    # Fall back to internal seed if external dic/ is missing
                    self._bundle = load_default_bundle()
            else:
                self._bundle = load_default_bundle()
        return self._bundle

    # ------------------------------------------------------------------
    # Step-wise entry points
    # ------------------------------------------------------------------
    def normalize(self, text: str) -> str:
        """N1 + N2 normalization (see core.text). Returns the normalized string."""
        return self.normalize_with_map(text).normalized

    def normalize_with_map(self, text: str) -> NormalizedText:
        """N1 + N2 normalization keeping the map back to original offsets."""
        return normalize_with_map(text, self._get_bundle().normalization_map())

    @staticmethod
    def _remap_tokens(tokens: list[Token], nt: NormalizedText) -> list[Token]:
        """Rewrite Token.begin/end from normalized to original coordinates."""
        if nt.normalized == nt.original:
            return tokens
        for tok in tokens:
            tok.begin, tok.end = nt.to_original_span(tok.begin, tok.end)
        return tokens

    def canonical(self, word: str) -> str:
        """N5 意味正規化: canonical form of ``word`` per synonym.csv (or itself)."""
        return self._get_bundle().synonym_map().get(word, word)

    def synonyms(self, word: str) -> list[str]:
        """All words in ``word``'s synonym group (canonical first), or [word]."""
        bundle = self._get_bundle()
        canonical = bundle.synonym_map().get(word)
        if canonical is None:
            return [word]
        return list(bundle.synonym_groups().get(canonical, [canonical]))

    def tokenize(self, text: str, granularity: str | None = None) -> list[Token]:
        if not text:
            return []
        nt = self.normalize_with_map(text)
        normalized = nt.normalized
        bundle = self._get_bundle()
        if self.pipeline == "lattice":
            tokens = lattice_tokenize(normalized, bundle, granularity or self.granularity)
        else:
            raw = self._get_backend().tokenize(normalized, mode=self.mode)
            tokens = merge_keep_as_unit(raw, normalized, bundle)
            tokens = fold_emphatic_reduplication(tokens)
            tokens = split_hiragana_tokens(tokens, bundle)
            tokens = heuristic_proper_noun_merge(tokens, normalized)
            tokens = merge_okurigana_compounds(tokens)
            tokens = refine_verb_adjective_pos(tokens, bundle)
        return self._remap_tokens(tokens, nt)

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------
    def analyze(self, text: str) -> AnalysisResult:
        errors: list[KotobaError] = []
        # E1xx input (§9): bytes are decoded leniently and the damage is recorded, never fatal
        if isinstance(text, (bytes, bytearray)):
            raw = bytes(text)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                text = raw.decode("utf-8", errors="replace")
                errors.append(make_error(E101_INVALID_UTF8, f"invalid UTF-8 at byte {exc.start}; replaced", position=exc.start))
        elif not isinstance(text, str):
            raise TypeError(f"analyze() expects str or bytes, got {type(text).__name__}")
        if "�" in text or any(0xD800 <= ord(c) <= 0xDFFF for c in text):
            pos = next((i for i, c in enumerate(text) if c == "�" or 0xD800 <= ord(c) <= 0xDFFF), None)
            if not errors:
                errors.append(make_error(E102_UNSUPPORTED_CHARACTER, "replacement / surrogate character in input", position=pos))
            text = "".join(c for c in text if not (0xD800 <= ord(c) <= 0xDFFF))

        def _guard(code: str, stage: str, fn, default):
            """Run one stage; on an unexpected exception record a recoverable error and use ``default``."""
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001 — isolation is the point (§9: 解析は原則として停止しない)
                errors.append(make_error(code, f"{stage}: {type(exc).__name__}: {exc}"))
                return default

        nt = self.normalize_with_map(text)
        normalized = nt.normalized
        bundle = self._get_bundle()

        # Tokenize → Token Normalizer (keep_as_unit merge, per 04_内部設計書 §3.1)
        tokens: list[Token] = []
        if text:
            if self.pipeline == "lattice":
                try:
                    tokens = lattice_tokenize(normalized, bundle)
                except Exception as exc:  # noqa: BLE001 — E201: fall back to character tokens, keep going
                    errors.append(make_error(E201_TOKENIZATION_ERROR, f"lattice: {type(exc).__name__}: {exc}"))
                    tokens = _char_tokens(normalized)
            else:
                raw = self._get_backend().tokenize(normalized, mode=self.mode)
                tokens = merge_keep_as_unit(raw, normalized, bundle)
                tokens = fold_emphatic_reduplication(tokens)
                tokens = split_hiragana_tokens(tokens, bundle)
                tokens = heuristic_proper_noun_merge(tokens, normalized)
                tokens = merge_okurigana_compounds(tokens)
                tokens = refine_verb_adjective_pos(tokens, bundle)

        # SemanticToken builder (chunks and entities both read it)
        semantic_tokens = []
        chunks = []
        if (self.enable_semantic_chunk or self.enable_entities) and tokens:
            semantic_tokens = build_semantic_tokens(tokens, bundle)
        if self.enable_semantic_chunk and tokens:
            chunks = _chunk(normalized, tokens, bundle)
        entity_semantic_tokens = semantic_tokens
        if not self.enable_semantic_chunk:
            semantic_tokens = []  # only exposed when the semantic layer is enabled

        # Entities (dictionary / pattern / time / quantity) — FR-030〜034
        entities: list[Entity] = []
        if self.enable_entities and tokens:
            entities = _guard(E302_ENTITY_ERROR, "entities", lambda: extract_entities(normalized, tokens, entity_semantic_tokens, bundle, self.reference_date), [])

        clauses = _guard(E301_SENTENCE_BOUNDARY_ERROR, "clauses", lambda: split_clauses(normalized), []) if tokens else []

        # Predicate-argument structure → relations / events (FR-023 / 040 / 041)
        predicates: list[Predicate] = []
        relations: list[Relation] = []
        events: list[Event] = []
        if self.enable_predicates and tokens:
            predicates, relations, events = _guard(E303_PREDICATE_ERROR, "predicates", lambda: extract_predicates(normalized, tokens, entities, clauses), ([], [], []))

        # Topics (FR-063)
        topic_result: TopicResult | None = _guard(E401_MODULE_ERROR, "topic", lambda: detect_topics(tokens, entities, bundle), TopicResult()) if (self.enable_topics and tokens) else TopicResult()

        # Core affect scoring runs once; Emotion and Sentiment aggregate it.
        scored = []
        if (self.enable_emotion or self.enable_sentiment) and text:
            scored = score_affect_expressions(normalized, bundle, tokens)
            # v0.6.6: a quoted name (「感動」という名のパン屋 / 「怒り」は新作タイトル) is not an affect
            # word — drop expressions that sit inside a quoted-name entity (canary cases)
            quoted = [(e.begin, e.end) for e in entities if e.source == "quoted"]
            if quoted:
                scored = [s for s in scored if not any(b <= s.begin and s.end <= e for b, e in quoted)]
            # 宛先付け (FR-052): target / holder per expression
            attach_attribution(normalized, tokens, entities, clauses, scored, bundle.stopword_set())

        emotion_result: EmotionResult | None = None
        if self.enable_emotion:
            emotion_result = _guard(E401_MODULE_ERROR, "emotion", lambda: detect_emotion(normalized, bundle, tokens, scored=scored),
                                    EmotionResult(primary=None, polarity=None, intensity=0.0, confidence=0.0, plutchik={}, expressions=[]))
        else:
            emotion_result = EmotionResult(
                primary=None, polarity=None, intensity=0.0, confidence=0.0,
                plutchik={}, expressions=[],
            )

        sentiment_result: SentimentResult | None = None
        if self.enable_sentiment:
            sentiment_result = _guard(E401_MODULE_ERROR, "sentiment", lambda: detect_sentiment(normalized, bundle, tokens, scored=scored),
                                      SentimentResult(polarity=None, intensity=0.0, confidence=0.0, expressions=[]))
        else:
            sentiment_result = SentimentResult(polarity=None, intensity=0.0, confidence=0.0, expressions=[])

        intent_result: IntentResult | None = None
        if self.enable_intent:
            intent_result = _guard(E401_MODULE_ERROR, "intent", lambda: classify_intent(
                normalized, bundle, emotion_result,
                sentiment=sentiment_result if self.enable_sentiment else None,
                entities=entities,
            ), IntentResult(label="unknown", confidence=0.0, candidates=[]))
        else:
            intent_result = IntentResult(label=None, confidence=0.0, candidates=[])

        if self.granularity == "fine" and self.pipeline == "lattice" and tokens:
            tokens = lattice_tokenize(normalized, bundle, "fine")
            if self.enable_semantic_chunk:
                semantic_tokens = build_semantic_tokens(tokens, bundle)

        rag_result: RagResult | None = None
        if self.enable_rag:
            rag_result = optimize_rag(
                normalized_text=normalized,
                tokens=tokens,
                semantic_tokens=semantic_tokens,
                chunks=chunks,
                emotion=emotion_result,
                intent=intent_result,
                bundle=bundle,
            )
        else:
            rag_result = RagResult()

        # Spans in the IR are expressed in original-text coordinates (FR-002).
        tokens = self._remap_tokens(tokens, nt)
        if nt.normalized != nt.original:
            for exp in list(emotion_result.expressions) + list(sentiment_result.expressions):
                exp.begin, exp.end = nt.to_original_span(exp.begin, exp.end)
            for ent in entities:
                ent.begin, ent.end = nt.to_original_span(ent.begin, ent.end)
            for pr in predicates:
                pr.begin, pr.end = nt.to_original_span(pr.begin, pr.end)
                for arg in pr.arguments:
                    arg.begin, arg.end = nt.to_original_span(arg.begin, arg.end)
            for item in [*relations, *events]:
                item.begin, item.end = nt.to_original_span(item.begin, item.end)

        return AnalysisResult(
            meta=MetaInfo(
                version=__version__,
                schema_version=SCHEMA_VERSION,
                mode="semantic",
                backend=self.backend,
                components=_component_meta(),
            ),
            text=TextInfo(original=text, normalized=normalized, offset_map=nt.origin),
            tokens=tokens,
            semantic_tokens=semantic_tokens,
            chunks=chunks,
            entities=entities,
            predicates=predicates,
            relations=relations,
            events=events,
            emotion=emotion_result,
            sentiment=sentiment_result,
            intent=intent_result,
            topics=topic_result,
            rag=rag_result,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Document hierarchy (FR-050) and Query IR (FR-080)
    # ------------------------------------------------------------------
    def analyze_document(self, text: str, document_id: str | None = None) -> AnalysisResult:
        """Analyze a multi-sentence document.

        Sentences (core.syntax.split_sentences) are analyzed one by one with
        :meth:`analyze`; their tokens / entities / phrase chunks are merged
        with document-wide ids and original-text spans. Paragraphs, sentences
        (each carrying its own emotion / sentiment / intent) and document
        chunks (rag.chunk) populate the hierarchy; the document-level
        emotion / sentiment / intent are aggregates over the sentences.
        """
        nt = self.normalize_with_map(text)
        normalized = nt.normalized
        bundle = self._get_bundle()

        sent_spans = split_sentences(normalized)
        para_spans = split_paragraphs(normalized)

        tokens: list[Token] = []
        entities: list[Entity] = []
        predicates: list[Predicate] = []
        relations: list[Relation] = []
        events: list[Event] = []
        topic_results: list[TopicResult] = []
        chunks = []
        semantic_tokens = []
        sentences: list[Sentence] = []
        keywords: list[str] = []
        phrases: list[str] = []
        emo_expr, sen_expr = [], []
        plutchik_sum: dict[str, float] = {}
        polarity_score: dict[str, float] = {}
        affect_score: dict[str, float] = {}
        intent_score: dict[str, float] = {}

        doc_errors: list[KotobaError] = []
        for sid, (nb, ne) in enumerate(sent_spans):
            ob, oe = nt.to_original_span(nb, ne)
            piece = text[ob:oe]
            r = self.analyze(piece)
            for err in r.errors:  # sentence-level recoverable errors bubble up with document positions
                err.position = (err.position + ob) if err.position is not None else None
                doc_errors.append(err)
            tok_offset = len(tokens)
            ent_offset = len(entities)
            id_map: dict[str, str] = {}
            for t in r.tokens:
                t.id += tok_offset
                t.begin += ob
                t.end += ob
                tokens.append(t)
            for st in r.semantic_tokens:
                st.token_id += tok_offset
                semantic_tokens.append(st)
            for c in r.chunks:
                c.id += len(chunks)
                c.token_ids = [i + tok_offset for i in c.token_ids]
                chunks.append(c)
            for k, e in enumerate(r.entities, 1):
                new_id = f"e{ent_offset + k}"
                id_map[e.id] = new_id
                e.id = new_id
                e.begin += ob
                e.end += ob
                e.token_ids = [i + tok_offset for i in e.token_ids]
                entities.append(e)
            pid_map: dict[str, str] = {}
            for pr in r.predicates:
                new_pid = f"p{len(predicates) + 1}"
                pid_map[pr.id] = new_pid
                pr.id = new_pid
                pr.begin += ob
                pr.end += ob
                pr.token_ids = [i + tok_offset for i in pr.token_ids]
                for arg in pr.arguments:
                    arg.begin += ob
                    arg.end += ob
                    arg.entity_id = id_map.get(arg.entity_id or "", arg.entity_id)
                    arg.token_ids = [i + tok_offset for i in arg.token_ids]
                predicates.append(pr)
            for rel in r.relations:
                rel.id = f"r{len(relations) + 1}"
                rel.begin += ob
                rel.end += ob
                rel.predicate_id = pid_map.get(rel.predicate_id, rel.predicate_id)
                rel.source = id_map.get(rel.source or "", rel.source)
                rel.target = id_map.get(rel.target or "", rel.target)
                relations.append(rel)
            for ev in r.events:
                ev.id = f"ev{len(events) + 1}"
                ev.begin += ob
                ev.end += ob
                ev.predicate_id = pid_map.get(ev.predicate_id, ev.predicate_id)
                for attr in ("agent", "object", "goal", "location", "time"):
                    val = getattr(ev, attr)
                    if val:
                        setattr(ev, attr, id_map.get(val, val))
                events.append(ev)
            if r.topics:
                for tp in r.topics.topics:
                    if tp.entity_id:
                        tp.entity_id = id_map.get(tp.entity_id, tp.entity_id)
                topic_results.append(r.topics)
            for exp in r.emotion.expressions if r.emotion else []:
                exp.begin += ob
                exp.end += ob
                exp.about = id_map.get(exp.about or "", exp.about)
                if exp.holder != "speaker":
                    exp.holder = id_map.get(exp.holder, exp.holder)
                emo_expr.append(exp)
            for exp in r.sentiment.expressions if r.sentiment else []:
                exp.begin += ob
                exp.end += ob
                exp.target = id_map.get(exp.target or "", exp.target)
                sen_expr.append(exp)
            if r.emotion:
                for k, v in r.emotion.plutchik.items():
                    plutchik_sum[k] = plutchik_sum.get(k, 0.0) + v * max(r.emotion.confidence, 0.1)
            if r.sentiment and r.sentiment.polarity:
                polarity_score[r.sentiment.polarity] = polarity_score.get(r.sentiment.polarity, 0.0) + max(r.sentiment.confidence, 0.1)
            if r.emotion and r.emotion.polarity:
                affect_score[r.emotion.polarity] = affect_score.get(r.emotion.polarity, 0.0) + max(r.emotion.confidence, 0.1)
            if r.intent and r.intent.label and r.intent.label != "unknown":
                intent_score[r.intent.label] = intent_score.get(r.intent.label, 0.0) + r.intent.confidence
            if r.rag:
                keywords += [k for k in r.rag.keywords if k not in keywords]
                phrases += [k for k in r.rag.semantic_phrases if k not in phrases]
            sentences.append(
                Sentence(
                    id=sid, begin=ob, end=oe, text=piece,
                    token_ids=[t.id for t in r.tokens],
                    entity_ids=[e.id for e in r.entities],
                    emotion=r.emotion, sentiment=r.sentiment, intent=r.intent,
                )
            )

        # ---- document-level entity coreference (FR-034): cluster mentions, add alias /
        # anaphora mentions (source="coreference"), before chunks read the entities
        if self.enable_entities and self.enable_coreference and entities:
            resolve_coreference(text, tokens, entities, sentences, bundle.stopword_set())

        paragraphs: list[Paragraph] = []
        for pid, (pb, pe) in enumerate(para_spans):
            ob, oe = nt.to_original_span(pb, pe)
            sids = [s.id for s, (nb, ne) in zip(sentences, sent_spans) if nb >= pb and ne <= pe]
            paragraphs.append(Paragraph(id=pid, begin=ob, end=oe, sentence_ids=sids, heading=is_heading_line(normalized[pb:pe])))

        # ---- document-level aggregates
        # Primary emotion: confidence-weighted vote over the sentence-level
        # primaries (each already 逆接-weighted), so a one-sentence document
        # gives exactly what analyze() gives.
        primary_votes: dict[str, float] = {}
        for sent in sentences:
            if sent.emotion and sent.emotion.primary:
                primary_votes[sent.emotion.primary] = primary_votes.get(sent.emotion.primary, 0.0) + max(sent.emotion.confidence, 0.1)
        primary = max(primary_votes, key=primary_votes.get) if primary_votes else None
        max_p = max(plutchik_sum.values()) if plutchik_sum else 0.0
        plutchik = {k: round(v / max_p, 3) for k, v in plutchik_sum.items()} if max_p > 0 else {}
        polarity = max(polarity_score, key=polarity_score.get) if polarity_score else None
        affect_polarity = max(affect_score, key=affect_score.get) if affect_score else None
        emotion_result = EmotionResult(
            primary=primary, polarity=affect_polarity,
            intensity=round(sum(e.intensity for e in emo_expr) / len(emo_expr), 3) if emo_expr else 0.0,
            confidence=round(sum(e.confidence for e in emo_expr) / len(emo_expr), 3) if emo_expr else 0.0,
            plutchik=plutchik, expressions=emo_expr,
        )
        sentiment_result = SentimentResult(
            polarity=polarity,
            intensity=round(sum(e.intensity for e in sen_expr) / len(sen_expr), 3) if sen_expr else 0.0,
            confidence=round(sum(e.confidence for e in sen_expr) / len(sen_expr), 3) if sen_expr else 0.0,
            expressions=sen_expr,
            affect_polarity=affect_polarity,
        )
        ranked = sorted(intent_score.items(), key=lambda kv: -kv[1])
        intent_result = IntentResult(
            label=ranked[0][0] if ranked else "unknown",
            confidence=round(min(ranked[0][1], 1.0), 3) if ranked else 0.0,
            candidates=[IntentCandidate(label=k, confidence=round(min(v, 1.0), 3)) for k, v in ranked],
        )
        rag_result = RagResult(keywords=keywords, search_query=" ".join(keywords[:8]), summary_hint=None, semantic_phrases=phrases)

        if len(sentences) == 1 and sentences[0].emotion is not None:
            # One sentence: reuse the sentence-level module results verbatim.
            emotion_result = sentences[0].emotion
            sentiment_result = sentences[0].sentiment or sentiment_result
            intent_result = sentences[0].intent or intent_result

        result = AnalysisResult(
            meta=MetaInfo(version=__version__, schema_version=SCHEMA_VERSION, mode="document", backend=self.backend, components=_component_meta()),
            text=TextInfo(original=text, normalized=normalized, offset_map=nt.origin),
            tokens=tokens, semantic_tokens=semantic_tokens, chunks=chunks, entities=entities,
            predicates=predicates, relations=relations, events=events,
            emotion=emotion_result, sentiment=sentiment_result, intent=intent_result,
            topics=merge_topics(topic_results), rag=rag_result,
            paragraphs=paragraphs, sentences=sentences, errors=doc_errors,
        )
        result.document_chunks = chunk_document(result, bundle)
        return result

    def analyze_query(self, text: str) -> QueryIR:
        """Structure a search query (FR-080) using the same vocabulary as the document IR."""
        result = self.analyze(text)
        return build_query_ir(text, result, self._get_bundle())

    def chunk(self, text: str, **kwargs):
        """Semantic document chunking (FR-081). Returns list[DocumentChunk]."""
        result = self.analyze_document(text)
        if kwargs:
            return chunk_document(result, self._get_bundle(), **kwargs)
        return result.document_chunks

    def analyze_batch(self, texts: list[str]) -> list[AnalysisResult]:
        return [self.analyze(t) for t in texts]
