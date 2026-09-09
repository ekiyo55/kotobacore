"""HTTP API (FR-092) — FastAPI application exposing analyze / query / chunk / tokenize.

Optional extra: ``pip install kotobacore[api]``. The core package never imports
FastAPI; this subpackage is loaded only by ``kotobacore serve`` or by
``create_app()``.
"""

from kotobacore.api.server import create_app

__all__ = ["create_app"]
