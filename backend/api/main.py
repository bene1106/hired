"""FastAPI application entry point.

Run in dev with::

    uv run uvicorn api.main:app --reload --port 8765
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from api import VERSION
from api.health import router as health_router
from api.routes.applications import router as applications_router
from api.routes.data import router as data_router
from api.routes.jobs import router as jobs_router
from api.routes.profile import router as profile_router
from api.routes.setup import router as setup_router
from api.routes.stats import router as stats_router
from db.migrations import run_migrations


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    run_migrations()
    yield


app = FastAPI(title="Hired. backend", version=VERSION, lifespan=lifespan)

_log = logging.getLogger("hired.api")


@app.middleware("http")
async def log_origin(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Diagnostic (v0.1.1): record the webview Origin on every request.

    The packaged Windows build failed with "Failed to fetch" while
    curl/browser worked — the classic signature of a CORS origin the
    backend doesn't allow. The Tauri webview origin is platform-specific
    (`tauri://localhost` on macOS/Linux, `http://tauri.localhost` on
    Windows/Android), so logging the exact inbound Origin makes the
    mismatch unambiguous in the field instead of a guess. Path is logged
    too; query strings/bodies are not (no PII in logs).
    """
    origin = request.headers.get("origin", "<none>")
    _log.info("request method=%s path=%s origin=%s", request.method, request.url.path, origin)
    return await call_next(request)


# The Tauri webview calls the sidecar from a platform-specific origin:
#   - macOS / Linux:        tauri://localhost
#   - Windows / Android:    http://tauri.localhost   (WebView2/Chromium)
#   - `pnpm tauri dev`:     http://localhost:<vite-port>
# The Windows form (`http://tauri.localhost`) is what shipped broken in
# v0.1.0 — it matches none of the old branches, so CORSMiddleware never
# emitted Access-Control-Allow-Origin and every in-app fetch was blocked
# by the browser even though the request reached the backend. Allow the
# tauri.localhost host explicitly (http and https) alongside the dev and
# loopback origins. Still a narrow allowlist — not `*`.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^(tauri://localhost"
        r"|https?://tauri\.localhost"
        r"|http://localhost(:\d+)?"
        r"|http://127\.0\.0\.1(:\d+)?)$"
    ),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(setup_router)
app.include_router(profile_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(stats_router)
app.include_router(data_router)
