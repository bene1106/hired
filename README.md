# Hired.

> Find jobs, write tailored applications, and prep for interviews, entirely on your own machine. No cloud backend, no third-party data collection, no subscription beyond whichever LLM you already have.

Hired. is a desktop app (macOS · Windows · Linux) that runs your job search end-to-end against a local SQLite database and a pluggable LLM provider. Plug in **Claude Code**, **Ollama**, or the **Anthropic API**; switch any time without losing data.

## Screenshots

v0.2.0 introduces a full redesign, a warm off-white / deep-ink / muted-green
visual language with light **and** dark mode, a two-column app shell, a redesigned
onboarding wizard, a restyled ranked feed, a unified materials screen, and a
five-column Kanban board for applications.

<!-- TODO(v0.2.0 release): capture on the release candidate in the packaged
     Windows build and drop the images in docs/screenshots/. Slots:
     - onboarding (provider step, light)         docs/screenshots/onboarding.png
     - job feed with matches (light)             docs/screenshots/feed.png
     - materials screen (generate, dark)         docs/screenshots/materials.png
     - applications Kanban board (dark)          docs/screenshots/kanban.png
     Headless CI cannot render the GUI, so capture is a manual RC step. -->

## Get started

### Pre-built installers

Download the latest installer for your OS from the [Releases page](https://github.com/bene1106/hired/releases):

| OS      | Installer                                            |
|---------|------------------------------------------------------|
| macOS   | `Hired._<version>_aarch64.dmg`                       |
| Windows | `Hired._<version>_x64-setup.exe` or `…_x64_en-US.msi` |
| Linux   | `Hired._<version>_amd64.AppImage` (or `.deb`)        |

Builds are currently **unsigned**; your OS will prompt the first time you launch:

- **macOS**: right-click the app → *Open*. See [`docs/install/macos.md`](docs/install/macos.md).
- **Windows**: SmartScreen → *More info* → *Run anyway*. See [`docs/install/windows.md`](docs/install/windows.md).
- **Linux**: AppImage → `chmod +x` once. See [`docs/install/linux.md`](docs/install/linux.md).

### Build from source

```bash
git clone https://github.com/bene1106/hired
cd hired
./scripts/bootstrap.sh    # macOS/Linux, or scripts\bootstrap.ps1 on Windows
pnpm tauri dev            # opens the app window
```

Requires Node 20+, Python 3.11+, and a Rust toolchain.

## How it works

1. **Pick a provider** during onboarding. The wizard probes for an Anthropic API key, the local `claude` CLI, and a running Ollama server, and lets you test each end-to-end before committing.
2. **Upload your CV.** PDF or paste; it's parsed once into a structured profile and stored locally.
3. **Crawl jobs.** Paste URLs (the reliable path) or kick off an experimental LinkedIn run. Jobs are deduped and scored against your profile.
4. **Apply.** Hired. researches the company, tailors your CV, and drafts a cover letter, all editable side-by-side with a live markdown preview.
5. **Interview prep.** A cached question bank per application plus a practice mode that critiques your answers.

The defining constraint is local-first: your CV, jobs, applications, and API keys never leave your machine. The keychain stores secrets via the OS-native API (Keychain Access / Credential Manager / Secret Service).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Tauri shell (Rust)                                      │
│  └─ React + TS + Tailwind frontend (Vite)               │
│       │                                                 │
│       ▼  HTTP                                           │
│  FastAPI sidecar (Python, bundled via PyInstaller)      │
│  ├─ LLM provider abstraction                            │
│  │   ├─ AnthropicAPIAdapter                             │
│  │   ├─ ClaudeCodeAdapter (subprocess wrapper)          │
│  │   ├─ OllamaAdapter      (HTTP to localhost:11434)    │
│  │   └─ MockProvider       (default in tests)           │
│  ├─ SQLite (~/.hired/db.sqlite, single source of truth) │
│  └─ OS keychain (API keys never persisted in DB)        │
└─────────────────────────────────────────────────────────┘
```

The full architecture lives in [`docs/architecture.md`](docs/architecture.md). Per-phase implementation specs are under [`.claude/specs/`](.claude/specs/).

## Repository layout

| Path           | Contents                                              |
|----------------|-------------------------------------------------------|
| `src-tauri/`   | Rust shell, app config, distribution                  |
| `frontend/`    | React + TypeScript + Tailwind                         |
| `backend/`     | Python FastAPI sidecar (LLM, prompts, crawler, db, api) |
| `eval/`        | Goldset for prompt evaluation                         |
| `docs/`        | Project doc, ADRs, install guides, changelog          |
| `.claude/`     | Phase specs and slash commands for the build process  |

## Tech stack

- **Frontend**: React 18, TypeScript (strict), Vite, Tailwind, shadcn/ui, MSW for tests
- **Backend**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, httpx, keyring
- **LLM**: Anthropic SDK · Claude Code CLI subprocess · Ollama HTTP API
- **Shell**: Tauri 2.x (Rust), packaged via `tauri-action` + PyInstaller
- **CI**: GitHub Actions, ruff + ESLint + Prettier + pytest + Vitest

## Contributing

Conventional commits (`feat:`, `fix:`, `docs:`, …); one logical change per commit; tests must pass locally before PR.

The CI mirror is the contract:

```bash
# Backend
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest -q

# Frontend
cd frontend && pnpm typecheck && pnpm lint && pnpm format:check && pnpm test --run
```

See [`CLAUDE.md`](CLAUDE.md) for the full conventions, decision hierarchy, and phase tracker.

## License

MIT, see [`LICENSE`](LICENSE).
