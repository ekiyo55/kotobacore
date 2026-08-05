"""Analyzer: KotobaCore main entry point.

Per 04_内部設計書 §5 and 06_API §4. Phase 13 wires all preceding phases:

    normalize → tokenize → semantic_tokens → chunks → emotion → intent → rag
"""

from __future__ import annotations

import os

from kotobacore._version import __version__
from kotobacore.dictionary import (
    DictionaryBundle,
    load_default_bundle,
    load_user_bundle,
)
from kotobacore.emotion import detect_emotion
from kotobacore.intent import classify_intent
from kotobacore.normalizer import normalize as _normalize
from kotobacore.rag import optimize_rag
from kotobacore.schema import (
    SCHEMA_VERSION,
    AnalysisResult,
    EmotionResult,
    IntentResult,
    MetaInfo,
    RagResult,
    TextInfo,
    Token,
)
from kotobacore.semantic import build_semantic_tokens
from kotobacore.semantic import chunk as _chunk
from kotobacore.tokenizer import (
    KaruizawaBackend,
    TokenizerBackend,
    heuristic_proper_noun_merge,
    merge_keep_as_unit,
    merge_okurigana_compounds,
    refine_verb_adjective_pos,
    split_hiragana_tokens,
)
from kotobacore.tokenizer.lattice import lattice_tokenize


class Analyzer:
    """Main entry point for KotobaCore."""

    def __init__(
        self,
        mode: str = "C",
        backend: str = "karuizawa",
        enable_semantic_chunk: bool = True,
        enable_emotion: bool = True,
        enable_intent: bool = True,
        enable_rag: bool = True,
        config_path: str | None = None,
        user_dict_path: str | None = None,
        use_external_dictionaries: bool = True,
        pipeline: str | None = None,
    ) -> None:
        self.mode = mode
        self.backend = backend
        # Karuizawa の実行モード: "lattice" (v0.2 デフォルト — 格子+Viterbi の
        # 一発分割) または "cascade" (〜v0.1 の5段補修パス、互換用に残置)。
        # 環境変数 KOTOBACORE_PIPELINE で比較評価時に切替可能。
        self.pipeline = pipeline or os.environ.get("KOTOBACORE_PIPELINE", "lattice")
        self.enable_semantic_chunk = enable_semantic_chunk
        self.enable_emotion = enable_emotion
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
        text = _normalize(text)
        for src, tgt in self._get_bundle().normalization_map().items():
            text = text.replace(src, tgt)
        return text

    def tokenize(self, text: str) -> list[Token]:
        if not text:
            return []
        normalized = self.normalize(text)
        bundle = self._get_bundle()
        if self.pipeline == "lattice":
            return lattice_tokenize(normalized, bundle)
        raw = self._get_backend().tokenize(normalized, mode=self.mode)
        tokens = merge_keep_as_unit(raw, normalized, bundle)
        tokens = split_hiragana_tokens(tokens, bundle)
        tokens = heuristic_proper_noun_merge(tokens, normalized)
        tokens = merge_okurigana_compounds(tokens)
        return refine_verb_adjective_pos(tokens, bundle)

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------
    def analyze(self, text: str) -> AnalysisResult:
        normalized = self.normalize(text)
        bundle = self._get_bundle()

        # Tokenize → Token Normalizer (keep_as_unit merge, per 04_内部設計書 §3.1)
        tokens: list[Token] = []
        if text:
            if self.pipeline == "lattice":
                tokens = lattice_tokenize(normalized, bundle)
            else:
                raw = self._get_backend().tokenize(normalized, mode=self.mode)
                tokens = merge_keep_as_unit(raw, normalized, bundle)
                tokens = split_hiragana_tokens(tokens, bundle)
                tokens = heuristic_proper_noun_merge(tokens, normalized)
                tokens = merge_okurigana_compounds(tokens)
                tokens = refine_verb_adjective_pos(tokens, bundle)

        # SemanticToken builder (always when chunks enabled OR for downstream)
        semantic_tokens = []
        chunks = []
        if self.enable_semantic_chunk and tokens:
            semantic_tokens = build_semantic_tokens(tokens, bundle)
            chunks = _chunk(normalized, tokens, bundle)

        emotion_result: EmotionResult | None = None
        if self.enable_emotion:
            emotion_result = detect_emotion(normalized, bundle, tokens)
        else:
            emotion_result = EmotionResult(
                primary=None, polarity=None, intensity=0.0, confidence=0.0,
                plutchik={}, expressions=[],
            )

        intent_result: IntentResult | None = None
        if self.enable_intent:
            intent_result = classify_intent(normalized, bundle, emotion_result)
        else:
            intent_result = IntentResult(label=None, confidence=0.0, candidates=[])

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

        return AnalysisResult(
            meta=MetaInfo(
                version=__version__,
                schema_version=SCHEMA_VERSION,
                mode="semantic",
                backend=self.backend,
            ),
            text=TextInfo(original=text, normalized=normalized),
            tokens=tokens,
            semantic_tokens=semantic_tokens,
            chunks=chunks,
            emotion=emotion_result,
            intent=intent_result,
            rag=rag_result,
            errors=[],
        )

    def analyze_batch(self, texts: list[str]) -> list[AnalysisResult]:
        return [self.analyze(t) for t in texts]
