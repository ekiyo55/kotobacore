"""v0.6.1: HTTP API (FR-092) — analyze / query / chunk / tokenize, bearer auth, rate limit, size cap, error shape (§9/§10)."""

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from kotobacore import Analyzer  # noqa: E402
from kotobacore.api import create_app  # noqa: E402
from kotobacore.api.server import RateLimiter  # noqa: E402

_ANALYZER = Analyzer()


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(_ANALYZER, api_token=None, rate_limit=None))


def test_health_and_version(client):
    assert client.get("/health").json() == {"status": "ok"}
    v = client.get("/version").json()
    import kotobacore

    assert v["kotobacore"] == kotobacore.__version__ and v["api"] == "1.0" and v["auth"] is False


def test_analyze_sentence_and_document(client):
    r = client.post("/analyze", json={"text": "東京支店の売上目標は3億円だ。"})
    assert r.status_code == 200
    body = r.json()
    assert body["text"]["original"].startswith("東京支店") and any(e["type"] == "MONEY" for e in body["entities"])
    r = client.post("/analyze", json={"text": "# 導入\n\n本文A。\n\n## 設定\n\n本文B。", "document": True, "semantic_only": True})
    assert r.status_code == 200
    body = r.json()
    assert "tokens" not in body and len(body["document_chunks"]) >= 1 and body["meta"]["mode"] == "document"


def test_query_with_reference_date(client):
    r = client.post("/query", json={"text": "東京支店の今年度の売上目標はいくら？", "reference_date": "2026-09-08"})
    assert r.status_code == 200
    q = r.json()
    assert q["intent"] == "search_value" and q["answer_type"] == "MONEY" and "FY2026" in q["constraints"].get("time", [])
    # the per-request reference date must not leak into the shared analyzer
    assert _ANALYZER.reference_date is None or _ANALYZER.reference_date != __import__("datetime").date(2026, 9, 8)


def test_chunk_and_tokenize(client):
    r = client.post("/chunk", json={"text": "### 手順\n\n説明：\n\n```bash\nmake restart\n```\n", "max_chars": 400, "min_chars": 80})
    assert r.status_code == 200
    chunks = r.json()
    assert chunks and "make restart" in chunks[0]["text"] and chunks[0]["heading_path"] == ["手順"]
    r = client.post("/tokenize", json={"text": "東京に行った", "granularity": "fine"})
    assert r.status_code == 200 and [t["surface"] for t in r.json()][-2:] == ["行", "った"]
    r = client.post("/tokenize", json={"text": "東京に行った"})
    assert r.status_code == 200 and [t["surface"] for t in r.json()][-1] == "行った"
    assert client.post("/tokenize", json={"text": "x", "granularity": "medium"}).status_code == 422


def test_error_shapes(client):
    r = client.post("/analyze", json={"text": "   "})
    assert r.status_code == 422 and r.json()["error"]["code"].startswith("E102")
    r = client.post("/query", json={"text": "いつ？", "reference_date": "2026/09/08"})
    assert r.status_code == 422 and r.json()["error"]["code"].startswith("E103")
    small = TestClient(create_app(_ANALYZER, max_chars=10))
    r = small.post("/analyze", json={"text": "あ" * 11})
    assert r.status_code == 413 and r.json()["error"]["code"].startswith("E101")
    # the error message never echoes the input
    assert "あ" not in r.text


def test_bearer_token_auth():
    c = TestClient(create_app(_ANALYZER, api_token="s3cret"))
    assert c.get("/health").status_code == 200  # health stays open
    r = c.post("/analyze", json={"text": "最高"})
    assert r.status_code == 401 and r.json()["error"]["code"].startswith("E701")
    assert c.post("/analyze", json={"text": "最高"}, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert c.post("/analyze", json={"text": "最高"}, headers={"Authorization": "Bearer s3cret"}).status_code == 200
    assert c.get("/version").json()["auth"] is True


def test_rate_limit():
    c = TestClient(create_app(_ANALYZER, rate_limit=2))
    assert c.post("/query", json={"text": "a"}).status_code == 200
    assert c.post("/query", json={"text": "a"}).status_code == 200
    r = c.post("/query", json={"text": "a"})
    assert r.status_code == 429 and r.json()["error"]["code"].startswith("E702")
    rl = RateLimiter(2)
    assert rl.allow("k", now=0.0) and rl.allow("k", now=1.0) and not rl.allow("k", now=2.0)
    assert rl.allow("k", now=61.0)  # window slid


def test_env_configuration(monkeypatch):
    monkeypatch.setenv("KOTOBACORE_API_TOKEN", "envtok")
    monkeypatch.setenv("KOTOBACORE_RATE_LIMIT", "5")
    c = TestClient(create_app(_ANALYZER))
    v = c.get("/version").json()
    assert v["auth"] is True and v["rate_limit_per_minute"] == 5
    assert c.post("/query", json={"text": "a"}, headers={"Authorization": "Bearer envtok"}).status_code == 200
