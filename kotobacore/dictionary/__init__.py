"""Dictionary loading and management for KotobaCore."""

from kotobacore.dictionary.external import (
    load_bundle_with_external,
    load_gemini_examples,
    load_gemini_examples_dir,
    load_nrc_lexicon,
    load_user_bundle,
)
from kotobacore.dictionary.loader import (
    DictionaryBundle,
    EmotionEntry,
    EmotionExampleEntry,
    EntityEntry,
    IntentRule,
    SentimentEntry,
    SlangEntry,
    StopwordEntry,
    SynonymEntry,
    apply_user_dictionary,
    load_default_bundle,
    load_dictionary_bundle,
    load_user_entities,
)

__all__ = [
    "DictionaryBundle",
    "EmotionEntry",
    "EmotionExampleEntry",
    "EntityEntry",
    "IntentRule",
    "SentimentEntry",
    "SlangEntry",
    "StopwordEntry",
    "SynonymEntry",
    "apply_user_dictionary",
    "load_bundle_with_external",
    "load_default_bundle",
    "load_dictionary_bundle",
    "load_gemini_examples",
    "load_gemini_examples_dir",
    "load_nrc_lexicon",
    "load_user_bundle",
    "load_user_entities",
]
