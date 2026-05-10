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
    # Defer the uvicorn import so a frozen binary boots fast and so a
    # syntax error in api.* shows up in the bootloader logs rather than
    # being lost in import-time noise.
    import uvicorn

    host = os.environ.get("HIRED_HOST", "127.0.0.1")
    port = int(os.environ.get("HIRED_PORT", "8765"))
    log_level = os.environ.get("HIRED_LOG_LEVEL", "info")

    # Print READY BEFORE we hand off to uvicorn — the marker needs to
    # land before the blocking event loop starts. The Tauri readiness
    # probe (when added) will look for this exact string.
    print(f"hired-sidecar listening on http://{host}:{port}", flush=True)

    # Importing through the dotted string keeps reload semantics intact
    # in dev mode; PyInstaller picks up the dependency via hidden imports.
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
