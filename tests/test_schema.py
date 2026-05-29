import json

from kotobacore import Analyzer
from kotobacore.schema import SCHEMA_VERSION


def test_schema_version():
    assert SCHEMA_VERSION == "0.1"


def test_analyze_returns_result():
    import kotobacore

    analyzer = Analyzer()
    result = analyzer.analyze("最高")

    assert result.meta.version == kotobacore.__version__
    assert result.meta.schema_version == "0.1"
    assert result.text.original == "最高"
    assert isinstance(result.tokens, list)
    assert isinstance(result.semantic_tokens, list)
    assert isinstance(result.chunks, list)
    assert result.emotion is not None
    assert result.intent is not None
    assert result.rag is not None
    assert isinstance(result.errors, list)


def test_analysis_result_to_dict_has_all_top_level_keys():
    analyzer = Analyzer()
    result = analyzer.analyze("最高")
    d = result.to_dict()

    required = {
        "meta",
        "text",
        "tokens",
        "semantic_tokens",
        "chunks",
        "emotion",
        "intent",
        "rag",
        "errors",
    }
    assert required.issubset(set(d.keys()))


def test_analysis_result_to_json_parses():
    analyzer = Analyzer()
    result = analyzer.analyze("最高")
    parsed = json.loads(result.to_json())

    assert "meta" in parsed
    assert "text" in parsed
    assert parsed["meta"]["schema_version"] == "0.1"


def test_analysis_result_to_json_pretty():
    analyzer = Analyzer()
    result = analyzer.analyze("最高")
    text = result.to_json(pretty=True)
    assert "\n" in text  # pretty includes indentation
