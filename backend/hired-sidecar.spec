# PyInstaller spec for the Hired. backend sidecar.
#
# Build (from `backend/`)::
#
#     uv run pyinstaller hired-sidecar.spec --clean --noconfirm
#
# Outputs `dist/hired-sidecar` (Linux/macOS) or `dist/hired-sidecar.exe`
# (Windows). The CI release workflow renames the binary with a Tauri
# target-triple suffix and copies it under `src-tauri/binaries/`.
#
# The data tuples below ship the Alembic migrations, alembic.ini, and
# the prompts directory next to the binary. `db/migrations.py` and
# `llm/prompts.py` already detect the PyInstaller `_MEIPASS` path so no
# code changes are needed at runtime.

# noqa: F821 — Analysis / PYZ / EXE / collect_submodules are PyInstaller
# spec globals injected by PyInstaller's exec environment.

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# sidecar.py imports `from api.main import app`, so PyInstaller follows
# api → routes → most of services/llm/db statically. But two graph
# edges are invisible to static analysis and have to be forced:
#   1. llm/__init__.py._build_inner_provider() does LAZY imports of the
#      adapter modules INSIDE the function body (so MockProvider users
#      don't pay the anthropic SDK import cost). PyInstaller doesn't
#      follow imports inside function bodies.
#   2. Alembic walks alembic/versions/ and imports each migration file
#      dynamically at upgrade() time.
# collect_submodules() sweeps every one of our app packages so a new
# route/service/adapter/migration can't silently fall out of the bundle.
_app_modules = (
    collect_submodules("api")
    + collect_submodules("db")
    + collect_submodules("services")
    + collect_submodules("llm")
    + collect_submodules("crawler")
    + collect_submodules("observability")
)

a = Analysis(
    ["sidecar.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("alembic", "alembic"),
        ("alembic.ini", "."),
        ("prompts", "prompts"),
    ],
    hiddenimports=[
        *_app_modules,
        # Adapter modules imported lazily inside llm/__init__.py — named
        # again here belt-and-suspenders even though collect_submodules
        # ("llm") already covers them, so the intent is greppable.
        "llm.anthropic_api",
        "llm.claude_code",
        "llm.ollama",
        # uvicorn selects its loop/protocol/lifespan impls at runtime;
        # static analysis can't see those. Missing any surfaces as a
        # runtime ImportError after launch — slow to debug, cheap to
        # prevent.
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # Alembic loads migration modules dynamically — it walks the
        # versions/ dir and imports each file. The `datas` entry above
        # ships the files; these cover Alembic's own runtime machinery.
        "alembic",
        "alembic.config",
        "alembic.runtime.migration",
        "alembic.script",
        # Pydantic v2 has split its core into pydantic_core which sometimes
        # gets missed on edge platforms.
        "pydantic_core",
        # keyring's backend is selected at runtime — name the most
        # likely platforms so the binary can read/write the OS keychain
        # on a fresh machine.
        "keyring.backends.Windows",
        "keyring.backends.macOS",
        "keyring.backends.SecretService",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Heavyweight optional deps that aren't needed inside the
        # bundled sidecar. Playwright in particular ships its own
        # browser binaries; if the user wants live LinkedIn crawling
        # they install Playwright themselves outside the bundle.
        "playwright",
        "tkinter",
        "matplotlib",
        # M4 voice (faster-whisper + Piper) is lazily imported in
        # services/voice.py and excluded from the bundle for now —
        # ctranslate2/onnxruntime/av are large and platform-specific.
        # Packaged builds report voice "unavailable"; bundling it is a
        # tracked follow-up. Dev gets voice via the `voice` extra.
        "faster_whisper",
        "piper",
        "ctranslate2",
        "onnxruntime",
        "av",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="hired-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX shrinks the binary a lot but flags antivirus on Windows. Keep
    # it off for now; if size becomes a problem we'll revisit.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
