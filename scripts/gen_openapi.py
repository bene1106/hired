"""Regenerate docs/api.openapi.json from the live FastAPI app.

Run via `make openapi` from the repo root. CI runs `make openapi-check`, which
regenerates and fails if the committed schema differs — the schema went stale
once (2026-05-29 → 2026-06-25, 19 missing paths) and that gap is what this
guard exists to prevent.

Importing `api.main` opens a DB session, so the Makefile target sets
HIRED_DB_URL to a scratch file. Never let this touch ~/.hired/data.db.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "docs" / "api.openapi.json"

# Running this by path puts scripts/ on sys.path, not backend/ — add it so the
# `api` package resolves regardless of the caller's cwd.
sys.path.insert(0, str(REPO_ROOT / "backend"))


def main() -> int:
    from api.main import app

    spec = app.openapi()
    # newline="" keeps LF on Windows too. Without it, a Windows-generated file
    # is CRLF and CI's `openapi-check` on ubuntu diffs against it forever.
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)} — {len(spec['paths'])} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
