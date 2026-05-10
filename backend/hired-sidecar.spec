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

# noqa: F821 — Analysis / PYZ / EXE are PyInstaller spec globals.

block_cipher = None

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
        # uvicorn is imported by string in sidecar.main; PyInstaller's
        # static analysis can't see the lazy submodules so list them
        # explicitly. Missing any of these surfaces as a runtime
        # ImportError after launch — slow to debug, cheap to prevent.
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
        # ships them; PyInstaller doesn't need explicit hiddenimports
        # for them because they're not imported during analysis.
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
