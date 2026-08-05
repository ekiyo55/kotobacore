"""Emotion detector with Plutchik mapping + example-based matching.

Per 05_辞書設計書 §6 and 06_API §11. v0.1 algorithm:

1. Surface-match emotion.csv / slang.csv entries in the normalized text.
2. For each detected emotion expression, look up example sentences in
   emotion_examples.csv (sharing the same ``surface``) and compute a
   character-bigram Jaccard similarity to the input — this is the
   ``example_similarity`` in 05_辞書設計書 §6.9.
3. Compute confidence per 05_辞書設計書 §6.9.3:

       confidence = lexical_score * 0.5 + example_similarity * 0.3
                  + intensity * 0.2

4. Aggregate per Plutchik emotion (sum of confidence-weighted intensity).
5. Primary emotion = highest-intensity expression's ``base_emotion``.
"""

from __future__ import annotations

import re
from collections import defaultdict

from kotobacore.clause import Clause, clause_at, split_clauses
from kotobacore.dictionary import DictionaryBundle
from kotobacore.matching import SurfaceMatcher
from kotobacore.schema import EmotionExpression, EmotionResult, Token
from kotobacore.semantic.builder import BASE_TO_PLUTCHIK

# ---------------------------------------------------------------------------
# Negation scope
# ---------------------------------------------------------------------------

# Negation immediately following an expression (optionally via a particle):
# 好き[じゃない] / 不安[はない] / 元気[がなく] / 嬉しく[ない] …
# Must be matched WITHIN the expression's clause (see kotobacore.clause).
_NEG_AFTER_RE = re.compile(r"(?:は|も|が)?(?:じゃ|では)?な(?:かった|くて|く|い)")

# Token-internal negation: a conjugated-adjective token whose lemma matched
# the lexicon (嬉しくない → lemma 嬉しい) but whose surface is negated.
_NEG_TOKEN_SUFFIXES: tuple[str, ...] = ("くなかった", "くなくて", "くない")

# Positive bases flip to a mild negative reading under negation
# (好きじゃない ≈ 嫌い → sadness). Negated NEGATIVE emotions (不安はない /
# 心配ない) are neutralized — the taxonomy has no "relief", so they drop.
_POSITIVE_BASES: frozenset[str] = frozenset({"joy", "admiration", "moved", "agreement"})

# ---------------------------------------------------------------------------
# Similarity (char-bigram Jaccard) — v0.1 lightweight substitute for
# embedding-based similarity.
# ---------------------------------------------------------------------------


def _bigrams(text: str) -> set[str]:
    if len(text) < 2:
        return {text} if text else set()
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0.0
    return inter / union


# ---------------------------------------------------------------------------
# Surface scanning
# ---------------------------------------------------------------------------


def _polarity_for(base_emotion: str) -> str:
    return {
        "joy": "positive",
        "admiration": "positive",
        "moved": "positive",
        "agreement": "positive",
        "anger": "negative",
        "irritation": "negative",
        "sadness": "negative",
        "anxiety": "negative",
        "refusal": "negative",
        "exaggeration": "mixed",
        "mixed": "mixed",
    }.get(base_emotion, "neutral")


def _plutchik_for(base_emotion: str | None) -> str | None:
    if not base_emotion:
        return None
    return BASE_TO_PLUTCHIK.get(base_emotion)


# ---------------------------------------------------------------------------
# Emotion candidate list — deterministic from the bundle, built once & cached.
# ---------------------------------------------------------------------------


def _build_emotion_candidates(
    bundle: DictionaryBundle,
) -> list[tuple[str, str, str, float, float, str]]:
    """Build the (surface, base_emotion, polarity, intensity, lex_weight, source)
    candidate list from emotion.csv ∪ slang.csv ∪ NRC ∪ example-based sources."""
    candidates: list[tuple[str, str, str, float, float, str]] = []

    for e in bundle.emotion:
        candidates.append(
            (e.surface, e.base_emotion, e.polarity, e.intensity, 1.0, "emotion")
        )
    for s in bundle.slang:
        candidates.append(
            (s.surface, s.emotion, _polarity_for(s.emotion), s.intensity, 0.9, "slang")
        )
    # External lexicon (NRC etc.) — discounted lex_weight; skip 1-char surfaces.
    for e in bundle.external_emotion:
        if len(e.surface) < 2:
            continue
        candidates.append(
            (e.surface, e.base_emotion, e.polarity, e.intensity, 0.5, "external")
        )

    # SNS example-based candidates for polysemous words absent from the above.
    # Surfaces curated in emotion.csv are excluded (internal entries win).
    internal_surfaces: set[str] = {e.surface for e in bundle.emotion}
    covered: set[tuple[str, str]] = {(c[0], c[1]) for c in candidates}
    for ex in bundle.emotion_examples:
        if ex.surface in internal_surfaces:
            continue
        key = (ex.surface, ex.base_emotion)
        if key in covered:
            continue
        covered.add(key)
        candidates.append(
            (ex.surface, ex.base_emotion, _polarity_for(ex.base_emotion),
             ex.intensity, 0.3, "examples")
        )

    # Longest surface first — longer matches win when spans overlap.
    candidates.sort(key=lambda c: -len(c[0]))
    return candidates


def _get_emotion_candidates(
    bundle: DictionaryBundle,
) -> list[tuple[str, str, str, float, float, str]]:
    c = bundle._cache.get("emotion_candidates")
    if c is None:
        c = _build_emotion_candidates(bundle)
        bundle._cache["emotion_candidates"] = c
    return c


def _get_emotion_matcher(bundle: DictionaryBundle) -> SurfaceMatcher:
    m = bundle._cache.get("emotion_matcher")
    if m is None:
        m = SurfaceMatcher([c[0] for c in _get_emotion_candidates(bundle)])
        bundle._cache["emotion_matcher"] = m
    return m


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------


def detect_emotion(
    text: str,
    bundle: DictionaryBundle,
    tokens: list[Token] | None = None,
) -> EmotionResult:
    """Detect emotion in ``text`` and return ``EmotionResult``.

    ``text`` should be the normalized text. When ``tokens`` is supplied, a
    surface match is only accepted if its character span aligns with token
    (morpheme) boundaries — this prevents accidental substring hits, e.g. the
    NRC entry ``はい`` matching ``...お昼はいつも...`` where は and い belong to
    different tokens.
    """
    if not text:
        return EmotionResult(
            primary=None, polarity=None, intensity=0.0, confidence=0.0,
            plutchik={}, expressions=[],
        )

    # Token-boundary alignment sets. A match [s, e) is token-aligned when:
    #   (a) s is some token's begin AND e is some token's end  (spans whole tokens), OR
    #   (b) the surface [s, e) is fully contained within a single token.
    # Case (b) handles the Karuizawa tokenizer's tendency to merge long HIRAGANA
    # runs into one token (e.g. "しくてたまらない") — an emotion word like
    # "たまらない" that ends at the same position as the token is still valid.
    token_begins: set[int] = set()
    token_ends: set[int] = set()
    pos_to_token_idx: dict[int, int] = {}  # char pos → token index
    if tokens:
        for idx, t in enumerate(tokens):
            token_begins.add(t.begin)
            token_ends.add(t.end)
            for p in range(t.begin, t.end):
                pos_to_token_idx[p] = idx

    def _aligned(start: int, end: int) -> bool:
        if not tokens:
            return True  # no token info → fall back to plain substring match
        # Case (a): exact token-boundary alignment (start AND end on boundaries)
        if start in token_begins and end in token_ends:
            return True
        # Case (b): the surface is a suffix of a single token (end aligns with
        # a token end, and the whole surface lies within that token).  This
        # handles the Karuizawa tokenizer's long HIRAGANA-run merges, e.g.
        # "たまらない" inside "しくてたまらない" — the token ends at the same
        # position as "たまらない", so it is a true suffix of the token.
        # We deliberately require the END to be on a token boundary (not the
        # start) to avoid prefix false-positives such as "はい" matching the
        # start of the "はいつもの" token.
        return (end - start >= 2
                and end in token_ends
                and start in pos_to_token_idx
                and (end - 1) in pos_to_token_idx
                and pos_to_token_idx[start] == pos_to_token_idx[end - 1])

    # Examples grouped by surface — cached on the bundle.
    examples_by_surface = bundle.emotion_examples_by_surface()

    input_bigrams = _bigrams(text)
    expressions: list[EmotionExpression] = []
    clause_weights: list[float] = []  # parallel to expressions

    # Clause segmentation — ex_sim scope, 逆接 weighting, negation boundary.
    clauses = split_clauses(text)
    _clause_bigrams: dict[int, set[str]] = {}

    def _bigrams_for(clause: Clause | None) -> set[str]:
        if clause is None:
            return input_bigrams
        bg = _clause_bigrams.get(clause.start)
        if bg is None:
            bg = _bigrams(text[clause.start:clause.end])
            _clause_bigrams[clause.start] = bg
        return bg

    # Emotion candidate list (emotion.csv ∪ slang.csv ∪ NRC ∪ example-based),
    # sorted longest-surface-first. Deterministic from the bundle → cached.
    candidates = _get_emotion_candidates(bundle)

    # Track already-claimed character positions to avoid double-counting
    # (e.g. "課金高すぎ" claims positions covering "高すぎ").
    claimed = bytearray(len(text))

    def _emit(
        display_text: str,
        ex_key: str,
        base_emotion: str,
        polarity: str,
        intensity: float,
        lex_weight: float,
        start: int,
        end: int,
        internal_neg: bool,
    ) -> None:
        """Score one candidate span, applying negation and clause scoping."""
        clause = clause_at(clauses, start)

        # --- negation ---------------------------------------------------
        neg_len = 0
        if not internal_neg:
            m = _NEG_AFTER_RE.match(text, end)
            if m and (clause is None or m.end() <= clause.end):
                neg_len = m.end() - end
        if internal_neg or neg_len:
            if base_emotion in _POSITIVE_BASES:
                # 好きじゃない ≈ 嫌い — flip to a mild negative reading.
                base_emotion = "sadness"
                polarity = "negative"
                intensity = round(intensity * 0.8, 3)
                if neg_len:
                    display_text = text[start:end + neg_len]
            else:
                # 不安はない / 心配ない — neutralized; span stays claimed.
                return
            if neg_len:
                for i in range(end, end + neg_len):
                    claimed[i] = 1

        # --- example similarity (clause-scoped) -------------------------
        scope_bigrams = _bigrams_for(clause)
        ex_sim_per_emotion: dict[str, float] = defaultdict(float)
        matched_ids: list[str] = []
        for ex in examples_by_surface.get(ex_key, []):
            sim = _jaccard(scope_bigrams, _bigrams(ex.example))
            if sim > 0.05:  # noise floor
                matched_ids.append(ex.example_id)
            ex_sim_per_emotion[ex.base_emotion] = max(
                ex_sim_per_emotion[ex.base_emotion], sim
            )
        ex_sim = ex_sim_per_emotion.get(base_emotion, 0.0)

        # Confidence formula from 05_辞書設計書 §6.9.3
        confidence = min(max(lex_weight * 0.5 + ex_sim * 0.3 + intensity * 0.2, 0.0), 1.0)

        expressions.append(
            EmotionExpression(
                text=display_text,
                emotion=base_emotion,
                plutchik_emotion=_plutchik_for(base_emotion),
                polarity=polarity,
                intensity=intensity,
                confidence=round(confidence, 3),
                matched_examples=matched_ids,
            )
        )
        clause_weights.append(clause.weight if clause else 1.0)

    # Single Aho-Corasick pass over the text — matches arrive in
    # (candidate_rank, position) order, i.e. longest-surface-first claiming,
    # identical to the previous per-candidate str.find loops.
    for rank, pos, end in _get_emotion_matcher(bundle).find_all(text):
        surface, base_emotion, polarity, intensity, lex_weight, _source = candidates[rank]
        if not _aligned(pos, end):
            continue
        if any(claimed[pos:end]):
            continue
        for i in range(pos, end):
            claimed[i] = 1
        _emit(surface, surface, base_emotion, polarity, intensity,
              lex_weight, pos, end, internal_neg=False)

    # dictionary_form pass: the Token Normalizer labels conjugated verbs /
    # adjectives with their lemma (おかしく → おかしい, 楽しかった → 楽しい).
    # Match those lemmas against the lexicon so inflected forms are detected
    # without registering every conjugation as its own surface.
    if tokens:
        lex_by_surface: dict[str, tuple[str, str, float, float]] = {}
        for surf, base_emotion, polarity, intensity, lex_weight, _src in candidates:
            lex_by_surface.setdefault(surf, (base_emotion, polarity, intensity, lex_weight))
        for tok in tokens:
            df = tok.dictionary_form
            if not df or df == tok.surface or df not in lex_by_surface:
                continue
            if any(claimed[tok.begin:tok.end]):
                continue
            for i in range(tok.begin, tok.end):
                claimed[i] = 1
            base_emotion, polarity, intensity, lex_weight = lex_by_surface[df]
            internal_neg = tok.surface.endswith(_NEG_TOKEN_SUFFIXES)
            _emit(tok.surface, df, base_emotion, polarity, intensity,
                  lex_weight, tok.begin, tok.end, internal_neg=internal_neg)

    if not expressions:
        return EmotionResult(
            primary=None, polarity=None, intensity=0.0, confidence=0.0,
            plutchik={}, expressions=[],
        )

    # Aggregate Plutchik distribution (confidence × intensity × clause weight)
    plutchik_dist: dict[str, float] = defaultdict(float)
    for exp, w in zip(expressions, clause_weights):
        key = exp.plutchik_emotion or "mixed"
        plutchik_dist[key] += exp.intensity * exp.confidence * w

    # Normalize Plutchik distribution to [0, 1] (relative)
    max_v = max(plutchik_dist.values())
    if max_v > 0:
        plutchik = {k: round(v / max_v, 3) for k, v in plutchik_dist.items()}
    else:
        plutchik = {k: 0.0 for k in plutchik_dist}

    # Primary = highest intensity × confidence × clause weight expression.
    # 逆接 weighting means the clause after けど/ですが/のに… dominates.
    primary_idx = max(
        range(len(expressions)),
        key=lambda i: expressions[i].intensity * expressions[i].confidence * clause_weights[i],
    )
    primary_exp = expressions[primary_idx]
    overall_intensity = round(
        sum(e.intensity * e.confidence for e in expressions)
        / max(1.0, sum(e.confidence for e in expressions)),
        3,
    )
    overall_confidence = round(
        sum(e.confidence for e in expressions) / len(expressions), 3
    )

    # Polarity: majority vote weighted by confidence × clause weight. When the
    # vote contradicts the primary expression's polarity and the margin is
    # thin, trust the primary (keeps primary/polarity mutually consistent).
    polarity_score: dict[str, float] = defaultdict(float)
    for exp, w in zip(expressions, clause_weights):
        polarity_score[exp.polarity] += exp.confidence * w
    polarity = max(polarity_score, key=polarity_score.get)
    if polarity != primary_exp.polarity:
        top = polarity_score[polarity]
        second = polarity_score.get(primary_exp.polarity, 0.0)
        if top > 0 and (top - second) / top < 0.2:
            polarity = primary_exp.polarity

    return EmotionResult(
        primary=primary_exp.emotion,
        polarity=polarity,
        intensity=overall_intensity,
        confidence=overall_confidence,
        plutchik=plutchik,
        expressions=expressions,
    )
