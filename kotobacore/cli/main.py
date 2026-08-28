"""KotobaCore CLI entry point (typer)."""

from __future__ import annotations

import json

import typer

from kotobacore._version import __version__
from kotobacore.analyzer import Analyzer

app = typer.Typer(help="KotobaCore CLI - Japanese semantic understanding engine")


def _make_analyzer(
    mode: str,
    no_emotion: bool,
    no_intent: bool,
    no_rag: bool,
    config: str | None,
    user_dict: str | None,
    granularity: str = "coarse",
) -> Analyzer:
    return Analyzer(
        mode=mode,
        enable_emotion=not no_emotion,
        enable_intent=not no_intent,
        enable_rag=not no_rag,
        config_path=config,
        user_dict_path=user_dict,
        granularity=granularity,
    )


@app.command()
def version() -> None:
    """Show KotobaCore version."""
    typer.echo(f"KotobaCore {__version__}")
    typer.echo("Backend: Karuizawa")
    typer.echo("Semantic Layer: enabled")


@app.command()
def analyze(
    text: str,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
    mode: str = typer.Option("C", "--mode", help="Tokenizer mode (accepted for compatibility; Karuizawa has single granularity)"),
    semantic_only: bool = typer.Option(
        False, "--semantic-only", help="Drop tokens / semantic_tokens, keep chunks/emotion/intent/rag."
    ),
    no_emotion: bool = typer.Option(False, "--no-emotion", help="Disable emotion analysis"),
    no_intent: bool = typer.Option(False, "--no-intent", help="Disable intent classification"),
    no_rag: bool = typer.Option(False, "--no-rag", help="Disable RAG optimization"),
    config: str | None = typer.Option(None, "--config", help="Path to YAML config"),
    user_dict: str | None = typer.Option(None, "--dict", help="Path to user dictionary CSV"),
    granularity: str = typer.Option(
        "coarse", "--granularity", help="Token granularity: coarse (semantic units) | fine (語幹/送り仮名/活用語尾)"
    ),
) -> None:
    """Analyze Japanese text and emit JSON."""
    analyzer = _make_analyzer(mode, no_emotion, no_intent, no_rag, config, user_dict, granularity)
    result = analyzer.analyze(text)
    payload = result.to_dict()

    if semantic_only:
        payload.pop("tokens", None)
        payload.pop("semantic_tokens", None)

    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None))


@app.command()
def tokenize(
    text: str,
    mode: str = typer.Option("C", "--mode", help="Tokenizer mode (accepted for compatibility)"),
    pretty: bool = typer.Option(False, "--pretty"),
    granularity: str = typer.Option(
        "coarse", "--granularity", help="Token granularity: coarse (semantic units) | fine (語幹/送り仮名/活用語尾)"
    ),
) -> None:
    """Emit token list only."""
    analyzer = Analyzer(mode=mode, granularity=granularity)
    tokens = analyzer.tokenize(text)
    # Token may be dataclass list or empty (Phase 5 fills in).
    if tokens and hasattr(tokens[0], "__dict__"):
        from dataclasses import asdict as _asdict
        data = [_asdict(t) for t in tokens]
    else:
        data = tokens
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2 if pretty else None))


@app.command()
def normalize(text: str) -> None:
    """Emit normalized text only."""
    analyzer = Analyzer()
    typer.echo(analyzer.normalize(text))


if __name__ == "__main__":
    app()
