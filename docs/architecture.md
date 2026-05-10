# Hired. — Architecture

This document is a one-page overview. The full design rationale lives in [`PROJECT_DOC.md`](PROJECT_DOC.md); per-phase implementation specs live in [`../.claude/specs/`](../.claude/specs/).

## One-line summary

> Tauri shell + React frontend + FastAPI sidecar (Python) + SQLite + pluggable LLM provider.

## Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│  Tauri shell (Rust, src-tauri/)                                    │
│  ─ window chrome, distribution, sidecar lifecycle                  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  React + TypeScript + Tailwind (frontend/)               │      │
│  │  ─ onboarding wizard, feed, dashboard, generate, prep    │      │
│  └──────────────────────────────────────────────────────────┘      │
│         │                                                          │
│         │  HTTP  (CORS allow-list: tauri://localhost +              │
│         │         http://localhost:* for dev)                      │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  FastAPI sidecar (backend/, packaged via PyInstaller)    │      │
│  │                                                          │      │
│  │  api/        — routes (setup, profile, jobs, apps, …)    │      │
│  │  services/   — business logic (apps, scoring, cost, …)   │      │
│  │  llm/        — provider abstraction (see below)          │      │
│  │  prompts/    — versioned .md prompt templates            │      │
│  │  crawler/    — JobSource ABC, ManualURL + LinkedIn       │      │
│  │  db/         — SQLAlchemy models + Alembic migrations    │      │
│  │  observability/ — logging, redaction, RecordingProvider  │      │
│  └──────────────────────────────────────────────────────────┘      │
│         │                                                          │
│         ├─► SQLite (~/.hired/db.sqlite, single source of truth)    │
│         └─► OS keychain (Keychain Access / Credential Manager /    │
│             Secret Service) — API keys never persisted in DB       │
└────────────────────────────────────────────────────────────────────┘
                          ▲
                          │ adapter calls
              ┌───────────┼─────────────────┬────────────┐
              ▼           ▼                 ▼            ▼
       Anthropic API  Claude Code CLI    Ollama      Mock (tests)
       (httpx + SDK)  (subprocess)       (httpx)     (deterministic)
```

## Key invariants

1. **Business logic only sees `LLMProvider`.** Concrete adapters live in `backend/llm/` and are never imported elsewhere. The factory in `backend/llm/__init__.py` reads the configured provider + model from `app_config` once and caches the built provider for the rest of the process.
2. **SQLite is the single source of truth** for every user-owned write. UI state, in-flight task progress, and cached LLM responses all materialise from rows in SQLite (or in-process dicts that reset on restart, where MVP allows).
3. **All API keys live in the OS keychain**, accessed via `backend/llm/credentials.py`. Nothing else reads or writes them. The `Delete everything` button calls `delete_credential` for every known key.
4. **Prompts are versioned files** (`backend/prompts/<name>.md`) loaded by name. Adding a new task means writing a new `.md`, not editing adapter code.
5. **Tests use `MockProvider` by default.** Real LLM calls are gated behind a `pytest.mark.integration` marker that's skipped unless run explicitly.

## Layers and what they own

| Layer        | Owns                                              | Doesn't touch                  |
|--------------|---------------------------------------------------|--------------------------------|
| `api/`       | HTTP routing, request/response shapes, deps      | DB writes, LLM calls           |
| `services/`  | Business logic, caching policy, transactions     | HTTP framework, raw SQL        |
| `llm/`       | Provider adapters, prompt rendering, error types | DB, HTTP routing               |
| `db/`        | Schema, migrations, session lifecycle            | LLM, HTTP                      |
| `frontend/`  | UI state, optimistic updates, msw test handlers  | Direct SQLite, raw LLM         |

## Multi-provider switching

The cost panel in Settings adapts to the active provider:

| Provider       | Label          | What the UI shows                                                  |
|----------------|----------------|--------------------------------------------------------------------|
| `anthropic_api` | `priced`        | `$0.27 today · $1.42 this week` (computed from token counts × rates) |
| `claude_code`  | `subscription` | `$0.00 (subscription)` — billed via Claude.ai plan                  |
| `ollama`       | `local`        | `$0.00 (local)` — runs on the user's hardware                       |
| `mock`         | `unknown`      | `—` — mock provider doesn't produce token counts                    |

Switching providers is free: `POST /api/setup/select-provider` updates `app_config`, calls `reset_provider_cache()`, and the next request lands in the new adapter. No restart needed.

## Build & distribution

- **Dev**: `pnpm tauri dev` runs the Vite frontend, the Tauri shell, and `uv run uvicorn` against the backend source tree.
- **Release**: `git tag v… && git push --tags` triggers `.github/workflows/release.yml`. Per OS we PyInstaller-bundle the sidecar (`backend/hired-sidecar.spec`), copy it under `src-tauri/binaries/hired-sidecar-<triple>(.exe)`, then `tauri-action` runs `pnpm tauri build` and uploads the resulting installers to a draft GitHub release.

Builds are unsigned. See `docs/install/{macos,windows,linux}.md` for first-launch workarounds.
