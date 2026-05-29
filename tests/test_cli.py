import json

from typer.testing import CliRunner

from kotobacore.cli.main import app

runner = CliRunner()


def test_cli_version():
    import kotobacore

    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "KotobaCore" in result.output
    # バージョンはハードコードせず実値と照合する
    assert kotobacore.__version__ in result.output


def test_cli_analyze_returns_json():
    result = runner.invoke(app, ["analyze", "最高"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "meta" in payload
    assert payload["text"]["original"] == "最高"


def test_cli_analyze_pretty():
    result = runner.invoke(app, ["analyze", "最高", "--pretty"])
    assert result.exit_code == 0
    assert "\n" in result.output


def test_cli_analyze_semantic_only_drops_tokens():
    result = runner.invoke(app, ["analyze", "最高", "--semantic-only"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "tokens" not in payload
    assert "semantic_tokens" not in payload
    assert "chunks" in payload
    assert "emotion" in payload


def test_cli_normalize():
    result = runner.invoke(app, ["normalize", "Test"])
    assert result.exit_code == 0
    assert "Test" in result.output


def test_cli_tokenize_returns_tokens():
    result = runner.invoke(app, ["tokenize", "東京都"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert len(payload) >= 1
    # Token dataclass fields
    first = payload[0]
    assert "surface" in first
    assert "begin" in first
    assert "end" in first
    assert "pos" in first
