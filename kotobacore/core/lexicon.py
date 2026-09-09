"""Affect lexicon matching (Core) — shared by the Emotion and Sentiment modules.

Per 要件定義書 v0.4 §3.3 / 設計原則 4: modules read only Core output. The
dictionary matching, token alignment, negation scope (core.syntax) and
逆接 clause weighting all live here; the Emotion module aggregates the
resulting expressions into a Plutchik distribution, the Sentiment module
aggregates them into a polarity. Both see exactly the same scored spans.

Scoring (05_辞書設計書 §6.9.3):

    confidence = lexical_score * 0.5 + example_similarity * 0.3 + intensity * 0.2
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from kotobacore.core.entity import BASE_TO_PLUTCHIK
from kotobacore.core.ir import Token
from kotobacore.core.matching import SurfaceMatcher
from kotobacore.core.syntax import (
    Clause,
    clause_at,
    is_negated_surface,
    negation_after,
    split_clauses,
)
from kotobacore.dictionary import DictionaryBundle

# Positive bases flip to a mild negative reading under negation
# (好きじゃない ≈ 嫌い → sadness). Negated NEGATIVE emotions (不安はない /
# 心配ない) are neutralized — the taxonomy has no "relief", so they drop.
_POSITIVE_BASES: frozenset[str] = frozenset({"joy", "admiration", "moved", "agreement", "trust"})
# Intensifiers (マジで / めっちゃ / すぎる / やばい): they never outrank a real emotion
# as the primary (v0.6.5); alone they still count (しぬw → exaggeration).
_INTENSIFIER_BASES: frozenset[str] = frozenset({"exaggeration"})

# Pseudo base_emotion for evaluative words (sentiment.csv). They carry a
# polarity but no Plutchik category; the Emotion module ignores them.
EVALUATION = "evaluation"


@dataclass
class ScoredExpression:
    """One lexicon hit after negation / clause scoping (normalized-text coords)."""

    text: str
    base_emotion: str
    plutchik_emotion: str | None
    polarity: str
    intensity: float
    confidence: float
    begin: int
    end: int
    clause_weight: float = 1.0
    negated: bool = False
    matched_examples: list[str] = field(default_factory=list)
    # attribution (core.attribution): evaluated / felt-about thing and holder
    target_id: str | None = None
    target_text: str | None = None
    holder_id: str | None = None
    holder_text: str | None = None


# ---------------------------------------------------------------------------
# Similarity (char-bigram Jaccard) — lightweight substitute for embeddings.
# ---------------------------------------------------------------------------


def bigrams(text: str) -> set[str]:
    if len(text) < 2:
        return {text} if text else set()
    return {text[i : i + 2] for i in range(len(text) - 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0.0
    return inter / union


# ---------------------------------------------------------------------------
# Emotion taxonomy helpers
# ---------------------------------------------------------------------------


def polarity_for(base_emotion: str) -> str:
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
        "surprise": "mixed",
        "trust": "positive",
        "disgust": "negative",
        "mixed": "mixed",
    }.get(base_emotion, "neutral")


def plutchik_for(base_emotion: str | None) -> str | None:
    if not base_emotion:
        return None
    return BASE_TO_PLUTCHIK.get(base_emotion)


# ---------------------------------------------------------------------------
# Candidate list — deterministic from the bundle, built once & cached.
# ---------------------------------------------------------------------------

Candidate = tuple[str, str, str, float, float, str]
# NRC translations that are not emotion words in Japanese usage (v0.6.5)
_EXTERNAL_STOPLIST: frozenset[str] = frozenset({"正直", "正直な", "正直に", "正直者"})


def _build_candidates(bundle: DictionaryBundle) -> list[Candidate]:
    """(surface, base_emotion, polarity, intensity, lex_weight, source) from
    emotion.csv ∪ slang.csv ∪ NRC ∪ example-based sources."""
    candidates: list[Candidate] = []

    for e in bundle.emotion:
        candidates.append((e.surface, e.base_emotion, e.polarity, e.intensity, 1.0, "emotion"))
    for s in bundle.slang:
        candidates.append((s.surface, s.emotion, polarity_for(s.emotion), s.intensity, 0.9, "slang"))
    # External lexicon (NRC etc.) — discounted lex_weight; skip 1-char surfaces and
    # known mistranslations (正直 = "honestly", an adverb, not admiration — it
    # out-scored real emotions in 7 of the 300 evaluation sentences, v0.6.5).
    for e in bundle.external_emotion:
        if len(e.surface) < 2 or e.surface in _EXTERNAL_STOPLIST:
            continue
        candidates.append((e.surface, e.base_emotion, e.polarity, e.intensity, 0.5, "external"))

    # Evaluative words without an emotion category (sentiment.csv). Emotion
    # entries win on identical surfaces (they are listed first and the sort
    # below is stable).
    internal_surfaces: set[str] = {e.surface for e in bundle.emotion}
    slang_surfaces: set[str] = {s.surface for s in bundle.slang}
    for se in bundle.sentiment:
        if se.surface in internal_surfaces or se.surface in slang_surfaces:
            continue
        candidates.append((se.surface, EVALUATION, se.polarity, se.intensity, 1.0, "sentiment"))

    # SNS example-based candidates for polysemous words absent from the above.
    covered: set[tuple[str, str]] = {(c[0], c[1]) for c in candidates}
    for ex in bundle.emotion_examples:
        if ex.surface in internal_surfaces:
            continue
        key = (ex.surface, ex.base_emotion)
        if key in covered:
            continue
        covered.add(key)
        candidates.append(
            (ex.surface, ex.base_emotion, polarity_for(ex.base_emotion), ex.intensity, 0.3, "examples")
        )

    # Longest surface first — longer matches win when spans overlap.
    candidates.sort(key=lambda c: -len(c[0]))
    return candidates


def get_candidates(bundle: DictionaryBundle) -> list[Candidate]:
    c = bundle._cache.get("emotion_candidates")
    if c is None:
        c = _build_candidates(bundle)
        bundle._cache["emotion_candidates"] = c
    return c


def get_matcher(bundle: DictionaryBundle) -> SurfaceMatcher:
    m = bundle._cache.get("emotion_matcher")
    if m is None:
        m = SurfaceMatcher([c[0] for c in get_candidates(bundle)])
        bundle._cache["emotion_matcher"] = m
    return m


# ---------------------------------------------------------------------------
# Main scoring pass
# ---------------------------------------------------------------------------


def score_affect_expressions(
    text: str,
    bundle: DictionaryBundle,
    tokens: list[Token] | None = None,
) -> list[ScoredExpression]:
    """Find and score every affect expression in normalized ``text``.

    When ``tokens`` is supplied, a surface match is only accepted if its
    character span aligns with token boundaries — this prevents accidental
    substring hits (NRC ``はい`` inside ``お昼はいつも``). Negation is resolved
    within the expression's clause (core.syntax) and the clause's 逆接 weight
    is attached to each expression.
    """
    if not text:
        return []

    token_begins: set[int] = set()
    token_ends: set[int] = set()
    pos_to_token_idx: dict[int, int] = {}
    if tokens:
        for idx, t in enumerate(tokens):
            token_begins.add(t.begin)
            token_ends.add(t.end)
            for p in range(t.begin, t.end):
                pos_to_token_idx[p] = idx

    def _aligned(start: int, end: int) -> bool:
        if not tokens:
            return True
        if start in token_begins and end in token_ends:
            return True
        # Suffix of a single token (long HIRAGANA-run merges: たまらない inside
        # しくてたまらない). The END must sit on a token boundary so prefixes
        # such as はい at the start of はいつもの are rejected.
        return (
            end - start >= 2
            and end in token_ends
            and start in pos_to_token_idx
            and (end - 1) in pos_to_token_idx
            and pos_to_token_idx[start] == pos_to_token_idx[end - 1]
        )

    examples_by_surface = bundle.emotion_examples_by_surface()
    input_bigrams = bigrams(text)
    results: list[ScoredExpression] = []

    clauses = split_clauses(text)
    _clause_bigrams: dict[int, set[str]] = {}

    def _bigrams_for(clause: Clause | None) -> set[str]:
        if clause is None:
            return input_bigrams
        bg = _clause_bigrams.get(clause.start)
        if bg is None:
            bg = bigrams(text[clause.start : clause.end])
            _clause_bigrams[clause.start] = bg
        return bg

    candidates = get_candidates(bundle)
    claimed = bytearray(len(text))
    # spans claimed by *emotion* expressions only (v0.6.5): an evaluation surface
    # (美味しかった in sentiment.csv) must not block the emotion reading of the
    # same word via its lemma (美味しい → joy) — the two overlay each other
    claimed_emo = bytearray(len(text))

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
        clause = clause_at(clauses, start)

        # --- negation (core.syntax) --------------------------------------
        neg_len = 0 if internal_neg else negation_after(text, end, clause)
        negated = bool(internal_neg or neg_len)
        span_end = end
        if negated:
            if base_emotion in _POSITIVE_BASES:
                # 好きじゃない ≈ 嫌い — flip to a mild negative reading.
                base_emotion = "sadness"
                polarity = "negative"
                intensity = round(intensity * 0.8, 3)
            elif base_emotion == EVALUATION:
                # 良くない → negative; 悪くない → mild positive (litotes).
                if polarity == "positive":
                    polarity = "negative"
                    intensity = round(intensity * 0.8, 3)
                else:
                    polarity = "positive"
                    intensity = round(intensity * 0.5, 3)
            else:
                # 不安はない / 心配ない — neutralized; span stays claimed.
                return
            if neg_len:
                display_text = text[start : end + neg_len]
                span_end = end + neg_len
            if neg_len:
                for i in range(end, end + neg_len):
                    claimed[i] = 1

        # --- example similarity (clause-scoped) ---------------------------
        scope_bigrams = _bigrams_for(clause)
        ex_sim_per_emotion: dict[str, float] = defaultdict(float)
        matched_ids: list[str] = []
        for ex in examples_by_surface.get(ex_key, []):
            sim = jaccard(scope_bigrams, bigrams(ex.example))
            if sim > 0.05:  # noise floor
                matched_ids.append(ex.example_id)
            ex_sim_per_emotion[ex.base_emotion] = max(ex_sim_per_emotion[ex.base_emotion], sim)
        ex_sim = ex_sim_per_emotion.get(base_emotion, 0.0)

        confidence = min(max(lex_weight * 0.5 + ex_sim * 0.3 + intensity * 0.2, 0.0), 1.0)

        results.append(
            ScoredExpression(
                text=display_text,
                base_emotion=base_emotion,
                plutchik_emotion=plutchik_for(base_emotion),
                polarity=polarity,
                intensity=intensity,
                confidence=round(confidence, 3),
                begin=start,
                end=span_end,
                clause_weight=clause.weight if clause else 1.0,
                negated=negated,
                matched_examples=matched_ids,
            )
        )

    # Single Aho-Corasick pass — matches arrive longest-surface-first.
    for rank, pos, end in get_matcher(bundle).find_all(text):
        surface, base_emotion, polarity, intensity, lex_weight, _source = candidates[rank]
        if not _aligned(pos, end):
            continue
        # an evaluation claim (最高だった, sentiment.csv) does not block the emotion word inside it
        # (最高 → joy); evaluations themselves never overlap any claim
        if any((claimed if base_emotion == EVALUATION else claimed_emo)[pos:end]):
            continue
        for i in range(pos, end):
            claimed[i] = 1
            if base_emotion != EVALUATION:
                claimed_emo[i] = 1
        _emit(surface, surface, base_emotion, polarity, intensity, lex_weight, pos, end, internal_neg=False)

    # dictionary_form pass: conjugated verbs / adjectives via their lemma.
    if tokens:
        lex_by_surface = bundle._cache.get("lexicon_by_surface")
        if lex_by_surface is None:  # built once per bundle (v0.6.8: was rebuilt per sentence)
            lex_by_surface = {}
            for surf, base_emotion, polarity, intensity, lex_weight, _src in candidates:
                lex_by_surface.setdefault(surf, (base_emotion, polarity, intensity, lex_weight))
            bundle._cache["lexicon_by_surface"] = lex_by_surface
        sent_by_surface = bundle.sentiment_by_surface()
        for tok in tokens:
            df = tok.dictionary_form
            if not df or df == tok.surface or df not in lex_by_surface:
                continue
            base_emotion, polarity, intensity, lex_weight = lex_by_surface[df]
            # an emotion reading may sit on top of an evaluation claim (美味しかった: EVALUATION by
            # surface + joy by lemma); an evaluation reading never duplicates any claim
            blocked = claimed if base_emotion == EVALUATION else claimed_emo
            if any(blocked[tok.begin : tok.end]):
                continue
            # a lemma that is both an emotion word and an evaluative word (面白い) yields both
            # readings for the conjugated surface (面白くない → sadness + negative evaluation)
            sent_entry = sent_by_surface.get(df) if base_emotion != EVALUATION else None
            if sent_entry is not None and not any(claimed[tok.begin : tok.end]):
                _emit(tok.surface, df, EVALUATION, sent_entry.polarity, sent_entry.intensity, 1.0,
                      tok.begin, tok.end, internal_neg=is_negated_surface(tok.surface))
            for i in range(tok.begin, tok.end):
                claimed[i] = 1
                if base_emotion != EVALUATION:
                    claimed_emo[i] = 1
            _emit(
                tok.surface, df, base_emotion, polarity, intensity, lex_weight,
                tok.begin, tok.end, internal_neg=is_negated_surface(tok.surface),
            )

    _overlay_evaluations(text, results, bundle)
    return results


def _overlay_evaluations(text: str, results: list[ScoredExpression], bundle: DictionaryBundle) -> None:
    """Emotion words that are also evaluative (最高 / 高すぎ / 課金高すぎ ⊃ 高すぎ).

    2026-09-08 policy: only sentiment.csv words count as evaluation. When an
    emotion / slang expression contains such a word, add an EVALUATION
    expression on that sub-span so the Sentiment module sees it while the
    Emotion module keeps the emotion. The longest contained sentiment.csv
    surface wins; a suffix match records the preceding part of the token as
    the evaluated thing (課金高すぎ → target 課金).
    """
    sent_map = bundle.sentiment_by_surface()
    if not sent_map or not results:
        return
    max_len = max(len(k) for k in sent_map)
    existing_eval = {(e.begin, e.end) for e in results if e.base_emotion == EVALUATION}
    overlay: list[ScoredExpression] = []
    for e in results:
        if e.base_emotion == EVALUATION:
            continue
        if any(b <= e.begin and e.end <= en for b, en in existing_eval):
            continue  # the surface pass already produced the evaluation for this span (美味しかった)
        span = text[e.begin:e.end]
        hit: tuple[int, str] | None = None
        # single-character sentiment words (神) only when they are the whole expression
        min_len = 1 if len(span) == 1 else 2
        for ln in range(min(len(span), max_len), min_len - 1, -1):
            for start in range(len(span) - ln + 1):
                sub = span[start : start + ln]
                if sub in sent_map:
                    hit = (start, sub)
                    break
            if hit:
                break
        if hit is None:
            continue
        start, sub = hit
        entry = sent_map[sub]
        polarity = entry.polarity
        intensity = entry.intensity
        if e.negated:
            if polarity == "positive":
                polarity, intensity = "negative", round(intensity * 0.8, 3)
            else:
                polarity, intensity = "positive", round(intensity * 0.5, 3)
        prefix = span[:start]
        overlay.append(
            ScoredExpression(
                text=sub,
                base_emotion=EVALUATION,
                plutchik_emotion=None,
                polarity=polarity,
                intensity=intensity,
                confidence=e.confidence,
                begin=e.begin + start,
                end=e.begin + start + len(sub),
                clause_weight=e.clause_weight,
                negated=e.negated,
                target_text=prefix if len(prefix) >= 2 and not prefix.endswith(("が", "は", "を", "に", "の")) else None,
            )
        )
    # Appended, not re-sorted: the Emotion module breaks ties by match order
    # (longest surface first), which must stay identical to v0.2.
    results.extend(overlay)


# ---------------------------------------------------------------------------
# Shared aggregation helpers (pure functions over ScoredExpression)
# ---------------------------------------------------------------------------


def primary_index(expressions: list[ScoredExpression]) -> int:
    """Index of the dominant expression: intensity × confidence × clause weight.

    逆接 weighting means the clause after けど/ですが/のに… dominates.
    """
    candidates = [i for i, e in enumerate(expressions) if e.base_emotion not in _INTENSIFIER_BASES] or list(range(len(expressions)))
    return max(
        candidates,
        key=lambda i: expressions[i].intensity * expressions[i].confidence * expressions[i].clause_weight,
    )


def aggregate_polarity(expressions: list[ScoredExpression]) -> str | None:
    """Majority polarity weighted by confidence × clause weight.

    When the vote contradicts the primary expression's polarity and the
    margin is thin, trust the primary (keeps primary/polarity consistent).
    """
    if not expressions:
        return None
    primary = expressions[primary_index(expressions)]
    score: dict[str, float] = defaultdict(float)
    for exp in expressions:
        score[exp.polarity] += exp.confidence * exp.clause_weight
    polarity = max(score, key=score.get)
    if polarity != primary.polarity:
        top = score[polarity]
        second = score.get(primary.polarity, 0.0)
        if top > 0 and (top - second) / top < 0.2:
            polarity = primary.polarity
    return polarity


def aggregate_intensity(expressions: list[ScoredExpression]) -> float:
    if not expressions:
        return 0.0
    return round(
        sum(e.intensity * e.confidence for e in expressions) / max(1.0, sum(e.confidence for e in expressions)),
        3,
    )


def aggregate_confidence(expressions: list[ScoredExpression]) -> float:
    if not expressions:
        return 0.0
    return round(sum(e.confidence for e in expressions) / len(expressions), 3)
