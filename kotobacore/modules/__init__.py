"""KotobaCore modules on top of the Semantic IR: intent / emotion / sentiment / topic.

Modules read only Core output (設計原則 4); the single allowed cross-module
signal is Sentiment → Intent, passed explicitly by the Analyzer.
"""

from kotobacore.modules.emotion import detect_emotion
from kotobacore.modules.intent import classify_intent
from kotobacore.modules.sentiment import detect_sentiment
from kotobacore.modules.topic import detect_topics, merge_topics

__all__ = ["classify_intent", "detect_emotion", "detect_sentiment", "detect_topics", "merge_topics"]
