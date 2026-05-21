"""FastAPI application entry point.

Run in dev with::

    uv run uvicorn api.main:app --reload --port 8765
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from api import VERSION
from api.health import router as health_router
from api.routes.applications import router as applications_router
from api.routes.data import router as data_router
from api.routes.jobs import router as jobs_router
from api.routes.profile import router as profile_router
from api.routes.setup import router as setup_router
from api.routes.stats import router as stats_router
from db.migrations import run_migrations
from llm.errors import LLMAuthError


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    run_migrations()
    yield


app = FastAPI(title="Hired. backend", version=VERSION, lifespan=lifespan)

_log = logging.getLogger("hired.api")


@app.exception_handler(LLMAuthError)
async def handle_llm_auth_error(_request: Request, exc: LLMAuthError) -> JSONResponse:
    """v0.3.5: surface a missing/invalid Anthropic key as a structured 401.

    Without this, ``Depends(get_llm_provider)`` raising ``LLMAuthError``
    bubbles to the catch-all middleware which returns 500 plaintext.
    The frontend can't distinguish "the user's credential dropped out
    of the keychain" from any other unhandled crash — it just shows a
    "Failed to fetch" wall. With a known status + ``error_kind`` the
    frontend can route the user to Settings → Switch Provider directly.
    """
    _log.warning("LLMAuthError surfaced as 401: %s", exc)
    return JSONResponse(
        status_code=401,
        content={
            "detail": str(exc) or "Anthropic key is not configured. Re-enter it in Settings.",
            "error_kind": "missing_api_key",
        },
    )


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


@app.middleware("http")
async def log_unhandled_exceptions(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """v0.3.4: surface escaping exceptions to ``sidecar.log``.

    Until this landed, any exception that escaped a sync route handler
    became Starlette's plaintext ``Internal Server Error`` body with no
    traceback anywhere we could find — uvicorn's default handler dumps
    to stderr but the PyInstaller-bundled binary's stderr is captured by
    Tauri's shell plugin in a way that swallowed the traceback in the
    field (verified by tailing the Tauri log around a repro: zero new
    bytes). That left v0.3.3's Practice-tab 500 undiagnosable from logs.

    This middleware logs the full traceback through ``hired.api`` which
    sidecar.py routes to ``~/.hired/logs/sidecar.log`` AND stdout, so
    the next time something blows up we get the cause without needing
    to ship another diagnostic build. We re-raise so FastAPI still
    returns the 500 — the user-facing behaviour is unchanged; only
    observability improves.
    """
    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001 — we log + re-raise; nothing swallowed
        tb = traceback.format_exc()
        _log.error(
            "unhandled exception on %s %s: %s\n%s",
            request.method,
            request.url.path,
            exc,
            tb,
        )
        # Surface the class name in the response body so a curl smoke
        # can identify the exception type without grepping logs. Stays
        # short — the full traceback is the log line above.
        return PlainTextResponse(
            f"Internal Server Error ({type(exc).__name__})",
            status_code=500,
        )


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
