"""PyInstaller entry point for the Hired. backend sidecar.

The Tauri shell launches this binary as a child process per the
``externalBin`` config in ``src-tauri/tauri.conf.json``. The shell
expects the sidecar to:

    1. Listen on ``127.0.0.1:8765`` (overridable via env)
    2. Survive its own startup migrations — the lifespan handler in
       ``api.main`` runs ``run_migrations()`` against ``~/.hired/db.sqlite``
    3. Print a structured "READY" line on stdout so a future Tauri
       readiness probe can wait without sleep-polling. (We don't probe
       yet; the frontend retries the health check on a short interval.)

Run from source for parity with ``pnpm tauri dev`` invocations::

    uv run python -m sidecar

PyInstaller bundle::

    cd backend && uv run pyinstaller hired-sidecar.spec --clean --noconfirm

The bundled binary lands at ``backend/dist/hired-sidecar`` (Linux/macOS)
or ``backend/dist/hired-sidecar.exe`` (Windows). The release workflow
renames it with a Tauri target-triple suffix before copying it into
``src-tauri/binaries/`` for the actual ``tauri build``.
"""

from __future__ import annotations

import os


def main() -> int:
    import traceback

    import uvicorn

    # Import the app OBJECT, not the "api.main:app" string. uvicorn's
    # string form does a late importlib lookup that PyInstaller's static
    # analysis can't see, so the frozen binary shipped without the `api`
    # package and died with `ModuleNotFoundError: No module named 'api'`.
    # Importing it here makes PyInstaller follow the full graph
    # (api → routes → services → llm → db). We don't need reload, so
    # passing the object loses nothing.
    from api.main import app
    from db.migrations import run_migrations

    host = os.environ.get("HIRED_HOST", "127.0.0.1")
    port = int(os.environ.get("HIRED_PORT", "8765"))
    log_level = os.environ.get("HIRED_LOG_LEVEL", "info")

    # Run migrations HERE rather than relying solely on the FastAPI
    # lifespan handler. uvicorn swallows a lifespan exception into a
    # generic "Application startup failed" with no traceback, which made
    # a frozen-binary migration failure look like an indefinite hang.
    # Doing it up-front means a packaging regression fails loudly with a
    # real traceback on stderr instead of a silent stuck process. The
    # lifespan still calls run_migrations() too; it's idempotent.
    print("hired-sidecar: applying migrations…", flush=True)
    try:
        run_migrations()
    except Exception:  # noqa: BLE001 — surface the real cause, then exit non-zero
        print("hired-sidecar: migrations FAILED", flush=True)
        traceback.print_exc()
        return 1
    print("hired-sidecar: migrations applied", flush=True)

    # Print READY BEFORE we hand off to uvicorn — the marker needs to
    # land before the blocking event loop starts. The Tauri readiness
    # probe (when added) will look for this exact string.
    print(f"hired-sidecar listening on http://{host}:{port}", flush=True)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        reload=False,
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
