"""KotobaCore CLI entry point (typer)."""

from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from typing import Annotated

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
    no_sentiment: bool = False,
) -> Analyzer:
    return Analyzer(
        mode=mode,
        enable_emotion=not no_emotion,
        enable_sentiment=not no_sentiment,
        enable_intent=not no_intent,
        enable_rag=not no_rag,
        config_path=config,
        user_dict_path=user_dict,
        granularity=granularity,
    )


@app.command()
def version(
    all_components: bool = typer.Option(False, "--all", help="Show every component version as JSON (§8 / NFR-003)"),
    matrix: bool = typer.Option(False, "--matrix", help="Print the compatibility matrix as Markdown (for README)"),
) -> None:
    """Show KotobaCore version (add --all or --matrix for the per-component versions)."""
    if all_components or matrix:
        from kotobacore.versions import compatibility_matrix_markdown, component_versions

        if matrix:
            typer.echo(compatibility_matrix_markdown())
        else:
            typer.echo(json.dumps(component_versions(), ensure_ascii=False, indent=2))
        return
    typer.echo(f"KotobaCore {__version__}")
    typer.echo("Backend: Karuizawa")
    typer.echo("Semantic Layer: enabled")


@app.command()
def analyze(
    text: str,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
    mode: str = typer.Option("C", "--mode", help="Tokenizer mode (accepted for compatibility; Karuizawa has single granularity)"),
    semantic_only: bool = typer.Option(
        False, "--semantic-only", help="Drop tokens / semantic_tokens, keep chunks/emotion/sentiment/intent/rag."
    ),
    no_emotion: bool = typer.Option(False, "--no-emotion", help="Disable emotion analysis"),
    no_intent: bool = typer.Option(False, "--no-intent", help="Disable intent classification"),
    no_sentiment: bool = typer.Option(False, "--no-sentiment", help="Disable sentiment (polarity) module"),
    no_rag: bool = typer.Option(False, "--no-rag", help="Disable RAG optimization"),
    config: str | None = typer.Option(None, "--config", help="Path to YAML config"),
    user_dict: str | None = typer.Option(None, "--dict", help="Path to user dictionary CSV"),
    granularity: str = typer.Option(
        "coarse", "--granularity", help="Token granularity: coarse (semantic units) | fine (語幹/送り仮名/活用語尾)"
    ),
    document: bool = typer.Option(False, "--document", help="Treat input as a multi-sentence document (paragraphs / sentences / document_chunks)"),
    file: bool = typer.Option(False, "--file", help="Read the text from the file at TEXT"),
    reference_date: str | None = typer.Option(None, "--reference-date", help="YYYY-MM-DD for relative dates (今日 / 3日前)"),
) -> None:
    """Analyze Japanese text and emit JSON."""
    analyzer = _make_analyzer(mode, no_emotion, no_intent, no_rag, config, user_dict, granularity, no_sentiment)
    if reference_date:
        analyzer.reference_date = _dt.date.fromisoformat(reference_date)
    if file:
        text = Path(text).read_text(encoding="utf-8")
    result = analyzer.analyze_document(text) if document else analyzer.analyze(text)
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


@app.command()
def query(
    text: str,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
    reference_date: str | None = typer.Option(None, "--reference-date", help="YYYY-MM-DD for relative dates"),
) -> None:
    """Structure a search query into a Query IR (intent / answer_type / target / constraints / keywords)."""
    analyzer = Analyzer(reference_date=_dt.date.fromisoformat(reference_date) if reference_date else None)
    typer.echo(analyzer.analyze_query(text).to_json(pretty=pretty))


@app.command()
def chunk(
    path: str,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
    max_chars: int = typer.Option(400, "--max-chars", help="Upper size of a chunk (never splits inside a sentence)"),
    min_chars: int = typer.Option(80, "--min-chars", help="Size before paragraph / topic boundaries may split"),
) -> None:
    """Semantic-chunk a document file into retrieval units (JSON list)."""
    text = Path(path).read_text(encoding="utf-8")
    chunks = Analyzer().chunk(text, max_chars=max_chars, min_chars=min_chars)
    from dataclasses import asdict

    typer.echo(json.dumps([asdict(c) for c in chunks], ensure_ascii=False, indent=2 if pretty else None))


vocab_app = typer.Typer(help="Vocabulary / Token ID tools (FR-070〜072): build | encode | decode | report")
app.add_typer(vocab_app, name="vocab")


def _read_lines(paths: list[str]) -> list[str]:
    """Lines of the given files (directories: *.txt / *.md recursively)."""
    lines: list[str] = []
    for p in paths:
        path = Path(p)
        files = sorted([*path.rglob("*.txt"), *path.rglob("*.md")]) if path.is_dir() else [path]
        for f in files:
            lines += f.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines


@vocab_app.command("build")
def vocab_build(
    inputs: Annotated[list[str], typer.Argument(help="Text files or directories (*.txt / *.md)")],
    out: str = typer.Option("vocab.json", "--out", help="Vocabulary JSON to write"),
    min_freq: int = typer.Option(1, "--min-freq", help="Minimum frequency for multi-character pieces (characters are always kept)"),
    max_size: int | None = typer.Option(None, "--max-size", help="Cap on multi-character pieces"),
    granularity: str = typer.Option("fine", "--granularity", help="fine (語幹/活用語尾, LM 語彙向け) | coarse"),
    extend: str | None = typer.Option(None, "--extend", help="Append to this existing vocabulary instead of building a new one (ids are kept)"),
) -> None:
    """Build (or extend) a vocabulary from text files."""
    from kotobacore.vocab import Vocabulary, build_vocab, extend_vocab

    lines = _read_lines(inputs)
    if extend:
        vocab = extend_vocab(Vocabulary.load(extend), lines, min_freq=min_freq)
    else:
        vocab = build_vocab(lines, granularity=granularity, min_freq=min_freq, max_size=max_size)
    vocab.save(out)
    typer.echo(f"{out}: {len(vocab)} ids ({sum(1 for e in vocab.entries if 'char' not in e.flags)} word pieces, {len(lines)} lines)")


@vocab_app.command("encode")
def vocab_encode(
    text: str = typer.Argument(..., help="Text, or a file path with --file"),
    vocab: str = typer.Option(..., "--vocab", help="Vocabulary JSON"),
    file: bool = typer.Option(False, "--file", help="Read the text from the file at TEXT"),
    pieces: bool = typer.Option(False, "--pieces", help="Emit piece strings instead of ids"),
    special: bool = typer.Option(False, "--special", help="Wrap with <bos> / <eos>"),
) -> None:
    """Encode text to Token IDs (JSON list)."""
    from kotobacore.vocab import VocabEncoder, Vocabulary

    if file:
        text = Path(text).read_text(encoding="utf-8")
    enc = VocabEncoder(Vocabulary.load(vocab))
    out = enc.pieces(text) if pieces else enc.encode(text, add_special=special)
    typer.echo(json.dumps(out, ensure_ascii=False))


@vocab_app.command("decode")
def vocab_decode(
    ids: str = typer.Argument(..., help='Token IDs as JSON list or space-separated ("12 34 7")'),
    vocab: str = typer.Option(..., "--vocab", help="Vocabulary JSON"),
) -> None:
    """Decode Token IDs back to (normalized) text."""
    from kotobacore.vocab import VocabEncoder, Vocabulary

    values = json.loads(ids) if ids.strip().startswith("[") else [int(x) for x in ids.split()]
    typer.echo(VocabEncoder(Vocabulary.load(vocab)).decode(values))


@vocab_app.command("report")
def vocab_report_cmd(
    inputs: Annotated[list[str], typer.Argument(help="Text files or directories to measure against")],
    vocab: str = typer.Option(..., "--vocab", help="Vocabulary JSON"),
    out_json: str | None = typer.Option(None, "--json", help="Write the full report JSON here"),
    out_md: str | None = typer.Option(None, "--md", help="Write a Markdown summary here"),
    top: int = typer.Option(20, "--top", help="Contamination candidates to list"),
) -> None:
    """Coverage / OOV / frequency distribution / contamination candidates (FR-072)."""
    from kotobacore.vocab import Vocabulary, report_markdown, vocab_report

    rep = vocab_report(Vocabulary.load(vocab), _read_lines(inputs), top=top)
    if out_json:
        Path(out_json).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    if out_md:
        Path(out_md).write_text(report_markdown(rep), encoding="utf-8")
    typer.echo(json.dumps({k: rep[k] for k in ("vocab", "coverage", "distribution")} | {"contamination": rep["contamination"]["count"]}, ensure_ascii=False, indent=2))


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address (use 0.0.0.0 behind a reverse proxy)"),
    port: int = typer.Option(8590, "--port", help="TCP port"),
    token: str | None = typer.Option(None, "--token", help="Bearer token required on POST endpoints (default: env KOTOBACORE_API_TOKEN)"),
    rate_limit: int | None = typer.Option(None, "--rate-limit", help="Requests per minute per client (default: env KOTOBACORE_RATE_LIMIT)"),
    max_chars: int = typer.Option(200_000, "--max-chars", help="Reject texts longer than this"),
    reference_date: str | None = typer.Option(None, "--reference-date", help="Default YYYY-MM-DD for relative dates"),
) -> None:
    """Run the HTTP API (FR-092). Requires `pip install kotobacore[api]`."""
    try:
        import uvicorn

        from kotobacore.api import create_app
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise typer.BadParameter(f"the HTTP API needs the 'api' extra: pip install kotobacore[api] ({exc})") from exc
    analyzer = Analyzer(reference_date=_dt.date.fromisoformat(reference_date) if reference_date else None)
    api = create_app(analyzer, api_token=token, rate_limit=rate_limit, max_chars=max_chars)
    typer.echo(f"KotobaCore API {__version__} on http://{host}:{port}  (docs: /docs, auth: {'on' if token or os.environ.get('KOTOBACORE_API_TOKEN') else 'off'})")
    uvicorn.run(api, host=host, port=port, log_level="info", access_log=False)  # access_log off: never log request bodies / texts


@app.command()
def eval(
    kind: str = typer.Argument("annotated", help="annotated | quality"),
    jsonl: str | None = typer.Option(None, "--jsonl", help="Annotated JSONL (default: tools/quality_test/annotated/annotated_v1.jsonl)"),
    out_json: str | None = typer.Option(None, "--json", help="Write full result JSON here"),
    out_md: str | None = typer.Option(None, "--md", help="Write Markdown summary here"),
) -> None:
    """Run the evaluation suites (FR-102). Requires the repository checkout (tools/)."""
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[2]
    if kind == "annotated":
        script = root / "tools" / "quality_test" / "run_annotated_eval.py"
        args = [sys.executable, "-X", "utf8", str(script)]
        if jsonl:
            args += ["--jsonl", jsonl]
        if out_json:
            args += ["--json", out_json]
        if out_md:
            args += ["--md", out_md]
    elif kind == "quality":
        script = root / "tools" / "quality_test" / "run_quality_test_5000.py"
        args = [sys.executable, "-X", "utf8", str(script)]
        if out_json:
            args += ["--json", out_json]
        if out_md:
            args += ["--md", out_md]
    else:
        raise typer.BadParameter("kind must be annotated | quality")
    if not script.exists():
        raise typer.Exit(code=typer.echo(f"evaluation script not found: {script}") or 1)
    raise typer.Exit(code=subprocess.call(args))


if __name__ == "__main__":  # must stay last: commands defined below this line would not be registered under `python -m`
    app()
