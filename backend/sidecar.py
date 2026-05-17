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

import logging
import logging.handlers
import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    """True when running inside the PyInstaller bundle (vs. ``uv run``)."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _setup_logging() -> Path:
    """Send sidecar + app logs to ``~/.hired/logs/sidecar.log``.

    A packaged GUI app has no console the user can read, and v0.1.0
    registered the Tauri log plugin only in debug builds — so a frozen
    sidecar that crashed or lost the port race left no trace anywhere.
    A rotating file the user can attach to a bug report fixes that. We
    also keep a stdout handler: the Tauri shell plugin drains the
    sidecar's stdout, so these lines reach the Tauri log too.
    """
    log_dir = Path.home() / ".hired" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "sidecar.log"

    handlers: list[logging.Handler] = [
        logging.handlers.RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,  # override any handler uvicorn/imports installed
    )
    return log_path


def main() -> int:
    import traceback

    log_path = _setup_logging()
    log = logging.getLogger("hired.sidecar")
    log.info("sidecar starting pid=%s frozen=%s log=%s", os.getpid(), _is_frozen(), log_path)

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
    log.info("applying migrations…")
    try:
        run_migrations()
    except Exception:  # noqa: BLE001 — surface the real cause, then exit non-zero
        log.exception("migrations FAILED")
        traceback.print_exc()
        return 1
    log.info("migrations applied")

    # Log READY BEFORE we hand off to uvicorn — the marker needs to land
    # before the blocking event loop starts. The Tauri readiness probe
    # (when added) will look for this exact string.
    log.info("hired-sidecar listening on http://%s:%s", host, port)

    # Catch the bind failure explicitly. When a previous run's sidecar
    # was orphaned (Tauri's shell plugin doesn't kill the child on app
    # exit), a fresh sidecar can't bind 8765 and uvicorn raises
    # OSError/WinError 10048. v0.1.0 let that exception escape into a
    # silent non-zero exit with nothing in any log — exactly the
    # "3 hired-sidecar.exe processes, backend still answers" symptom.
    # Now it's a loud, attributable log line.
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=log_level,
            reload=False,
            access_log=False,
        )
    except OSError:
        log.exception(
            "could not bind %s:%s — is another hired-sidecar already running?",
            host,
            port,
        )
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
