"""Dump the HTTP API's OpenAPI document to docs/openapi.json (FR-092 API ドキュメント).

Run after any change to kotobacore/api/server.py:  python tools/gen_openapi.py
Needs the ``api`` extra (FastAPI). The JSON is what ``kotobacore serve`` publishes at /openapi.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    from kotobacore.api import create_app

    spec = create_app().openapi()
    out = ROOT / "docs" / "openapi.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out, "paths:", ", ".join(spec["paths"]))


if __name__ == "__main__":
    main()
