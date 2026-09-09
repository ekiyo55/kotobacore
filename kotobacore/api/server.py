"""FastAPI application for KotobaCore (FR-092).

Endpoints
    GET  /health              liveness
    GET  /version             KotobaCore / schema / API versions
    POST /analyze             {text, document?, reference_date?} → Semantic IR (AnalysisResult JSON)
    POST /query               {text, reference_date?}            → Query IR
    POST /chunk               {text, max_chars?, min_chars?}     → document chunks
    POST /tokenize            {text, granularity?}               → tokens

Security (§10): optional bearer-token auth (``api_token`` / KOTOBACORE_API_TOKEN),
optional per-client rate limit (``rate_limit`` requests per minute /
KOTOBACORE_RATE_LIMIT), a request size cap (``max_chars``), and request bodies
are never logged. Errors follow §9: ``{"error": {"code": "E7xx …", "message": …}}``.

The analyzer is built once per app; a separate process from the Streamlit demo.
"""

from __future__ import annotations

import datetime as _dt
import os
import threading
import time
from collections import deque
from dataclasses import asdict
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from kotobacore._version import __version__
from kotobacore.analyzer import Analyzer
from kotobacore.core.ir import SCHEMA_VERSION

API_VERSION = "1.0"  # unified to 1.0 at KotobaCore 1.0.0; path / response-shape breaks bump the major
DEFAULT_MAX_CHARS = 200_000


# ---------------------------------------------------------------- request models


class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Japanese text")
    document: bool = Field(False, description="Multi-paragraph document → paragraphs / sentences / document_chunks")
    reference_date: str | None = Field(None, description="YYYY-MM-DD for relative dates (今日 / 来月)")
    semantic_only: bool = Field(False, description="Drop tokens / semantic_tokens from the response")


class QueryRequest(BaseModel):
    text: str
    reference_date: str | None = None


class ChunkRequest(BaseModel):
    text: str
    max_chars: int = Field(400, ge=40, le=5000)
    min_chars: int = Field(80, ge=0, le=5000)


class TokenizeRequest(BaseModel):
    text: str
    granularity: str = Field("coarse", pattern="^(coarse|fine)$")


# ---------------------------------------------------------------- errors


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


class RateLimiter:
    """Fixed-window (60 s) request counter per client key; thread-safe, in-memory."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] >= 60.0:
                q.popleft()
            if len(q) >= self.per_minute:
                return False
            q.append(now)
            return True


# ---------------------------------------------------------------- app factory


def create_app(
    analyzer: Analyzer | None = None,
    *,
    api_token: str | None = None,
    rate_limit: int | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> FastAPI:
    """Build the FastAPI app. ``api_token`` / ``rate_limit`` default to the
    KOTOBACORE_API_TOKEN / KOTOBACORE_RATE_LIMIT environment variables."""
    token = api_token if api_token is not None else (os.environ.get("KOTOBACORE_API_TOKEN") or None)
    if rate_limit is None:
        env_rl = os.environ.get("KOTOBACORE_RATE_LIMIT")
        rate_limit = int(env_rl) if env_rl and env_rl.isdigit() else None
    limiter = RateLimiter(rate_limit) if rate_limit else None
    base = analyzer or Analyzer()
    fine = Analyzer(granularity="fine", enable_emotion=False, enable_sentiment=False, enable_intent=False, enable_rag=False)
    lock = threading.Lock()  # the analyzer keeps per-call state (reference_date); serialize calls

    app = FastAPI(title="KotobaCore API", version=API_VERSION, description=__doc__, docs_url="/docs", redoc_url=None)
    app.state.analyzer = base
    app.state.limiter = limiter

    async def guard(request: Request) -> None:
        if token:
            auth = request.headers.get("authorization", "")
            if not (auth.startswith("Bearer ") and auth[7:].strip() == token):
                raise HTTPException(status_code=401, detail={"code": "E701 unauthorized", "message": "missing or invalid bearer token"})
        if limiter is not None:
            client = request.client.host if request.client else "unknown"
            if not limiter.allow(client):
                raise HTTPException(status_code=429, detail={"code": "E702 rate_limited", "message": f"more than {rate_limit} requests per minute"})

    def check_size(text: str) -> None:
        if len(text) > max_chars:
            raise HTTPException(status_code=413, detail={"code": "E101 input_too_large", "message": f"text exceeds {max_chars} characters"})
        if not text.strip():
            raise HTTPException(status_code=422, detail={"code": "E102 empty_input", "message": "text is empty"})

    def parse_date(value: str | None) -> _dt.date | None:
        if not value:
            return None
        try:
            return _dt.date.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "E103 invalid_reference_date", "message": "reference_date must be YYYY-MM-DD"}) from exc

    @app.exception_handler(HTTPException)
    async def _http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": f"E7{exc.status_code % 100:02d} api_error", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        # never echo the input text back; the message names only the exception type
        return _error(500, "E700 api_error", f"internal error: {type(exc).__name__}")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/version")
    async def version() -> dict[str, Any]:
        return {"kotobacore": __version__, "schema": SCHEMA_VERSION, "api": API_VERSION, "backend": base.backend,
                "auth": bool(token), "rate_limit_per_minute": rate_limit}

    @app.post("/analyze", dependencies=[Depends(guard)])
    async def analyze(req: AnalyzeRequest) -> dict[str, Any]:
        check_size(req.text)
        ref = parse_date(req.reference_date)
        with lock:
            prev = base.reference_date
            try:
                if ref is not None:
                    base.reference_date = ref
                result = base.analyze_document(req.text) if req.document else base.analyze(req.text)
            finally:
                base.reference_date = prev
        payload = result.to_dict()
        if req.semantic_only:
            payload.pop("tokens", None)
            payload.pop("semantic_tokens", None)
        return payload

    @app.post("/query", dependencies=[Depends(guard)])
    async def query(req: QueryRequest) -> dict[str, Any]:
        check_size(req.text)
        ref = parse_date(req.reference_date)
        with lock:
            prev = base.reference_date
            try:
                if ref is not None:
                    base.reference_date = ref
                return base.analyze_query(req.text).to_dict()
            finally:
                base.reference_date = prev

    @app.post("/chunk", dependencies=[Depends(guard)])
    async def chunk(req: ChunkRequest) -> list[dict[str, Any]]:
        check_size(req.text)
        with lock:
            chunks = base.chunk(req.text, max_chars=req.max_chars, min_chars=req.min_chars)
        return [asdict(c) for c in chunks]

    @app.post("/tokenize", dependencies=[Depends(guard)])
    async def tokenize(req: TokenizeRequest) -> list[dict[str, Any]]:
        check_size(req.text)
        a = fine if req.granularity == "fine" else base
        with lock:
            return [asdict(t) for t in a.tokenize(req.text)]

    return app
