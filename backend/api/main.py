"""FastAPI application entry point.

Run in dev with::

    uv run uvicorn api.main:app --reload --port 8765
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import VERSION
from api.health import router as health_router

app = FastAPI(title="Hired. backend", version=VERSION)

# The Tauri webview runs the React frontend on a `tauri://` (prod) or
# `http://localhost:<vite-port>` (dev) origin. Both need to call the sidecar
# at localhost:8765, so allow any localhost origin.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(tauri://localhost|http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?)$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
