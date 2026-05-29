def test_import_kotobacore():
    import kotobacore

    assert kotobacore is not None


def test_import_public_api():
    from kotobacore import (
        AnalysisResult,
        Analyzer,
        EmotionResult,
        IntentResult,
        RagResult,
        SemanticChunk,
        SemanticToken,
        Token,
    )

    assert Analyzer is not None
    assert AnalysisResult is not None
    assert Token is not None
    assert SemanticToken is not None
    assert SemanticChunk is not None
    assert EmotionResult is not None
    assert IntentResult is not None
    assert RagResult is not None
