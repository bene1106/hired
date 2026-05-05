# Phase 1 — Foundation

**Duration:** Week 1
**Owner suggestion:** Anna + Bene (Backend/Architecture lead)
**Status:** _Update in `docs/CURRENT_PHASE.md` when starting/completing_

## Goal

Set up the skeleton: a Tauri app that launches, contains a FastAPI sidecar, talks to a SQLite database, and renders a placeholder React UI. **No business logic yet.** Just the plumbing.

This phase is the most boring but the most important — everything later depends on it working cleanly.

## Acceptance Criteria

A reviewer can run the following on a fresh checkout and have it work:

```bash
git clone <repo>
cd hired
./scripts/bootstrap.sh    # installs all deps
pnpm tauri dev            # opens app window
```

The app window must:
- Show "Hired." title bar
- Render a placeholder React page with a "Health check" button
- Clicking the button calls the FastAPI sidecar at `localhost:8765/health`
- Display the response: `{"status": "ok", "db": "connected", "version": "0.1.0"}`

CI must pass on push:
- Linting: `ruff check`, `eslint`, `tsc --noEmit`
- Tests: `pytest` (>=1 test) and `pnpm test` (>=1 test)
- Build: `pnpm tauri build` succeeds for the host OS

## Tasks

### 1.1 Repository Bootstrap

- [ ] `git init` at repo root, add `.gitignore` (Python, Node, Rust, OS files, `~/.hired/`)
- [ ] Create `README.md` with one-paragraph project description + "see `docs/PROJECT_DOC.md` for full spec"
- [ ] Add `LICENSE` (MIT)
- [ ] Add `docs/PROJECT_DOC.md` (the user provides this — copy it in)
- [ ] Add `docs/CHANGELOG.md` with `## [Unreleased]` section
- [ ] Add `docs/CURRENT_PHASE.md` with "Phase 1 — Foundation"
- [ ] Add `docs/adr/0001-local-first-architecture.md` (template provided below)

### 1.2 Tauri Shell

- [ ] Initialize Tauri 2.x project in `src-tauri/`
- [ ] Configure `tauri.conf.json`:
  - App name: "Hired."
  - Identifier: `dev.hired.app`
  - Window: 1280x800, resizable down to 800x600
  - Icon placeholder (use Tauri default for now)
- [ ] Configure FastAPI as Tauri sidecar (Tauri's `externalBin` + sidecar binary path)

### 1.3 Frontend Skeleton

- [ ] Set up `frontend/` with Vite + React 18 + TypeScript (strict)
- [ ] Add Tailwind CSS + shadcn/ui (init only; components added as needed)
- [ ] Single page: shows "Hired." title and a "Run health check" button
- [ ] Button hits `http://localhost:8765/health` and shows the JSON response
- [ ] ESLint + Prettier configured; one Vitest test (e.g., button renders)

### 1.4 Backend Skeleton

- [ ] Set up `backend/` with `pyproject.toml` (use `uv` as package manager)
- [ ] Dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pytest`, `httpx`, `ruff`
- [ ] FastAPI app in `backend/api/main.py` with one route: `GET /health`
- [ ] Health route returns `{"status": "ok", "db": "connected", "version": "0.1.0"}` after a trivial DB query
- [ ] One pytest test for the health endpoint using `httpx.AsyncClient`

### 1.5 Database Schema (Initial)

- [ ] Set up Alembic for migrations, target: SQLite at `~/.hired/data.db`
- [ ] Initial migration creates these tables (empty schemas, just structure):
  - `profile` (id, name, email, target_role, target_salary_min, target_location, cv_text, cv_parsed_json, created_at, updated_at)
  - `jobs` (id, source, source_id, title, company, location, description, url, posted_at, ingested_at)
  - `job_scores` (id, job_id, score, rationale_json, scored_at)
  - `applications` (id, job_id, status, applied_at, notes)
  - `application_materials` (id, application_id, type, content, created_at)
  - `interview_sessions` (id, application_id, transcript_json, created_at)
  - `app_config` (key, value) — for storing provider config, etc.
- [ ] Seed: a single row in `app_config` with `provider=mock` for default
- [ ] On startup, FastAPI runs pending migrations automatically

### 1.6 CI/CD

- [ ] GitHub Actions workflow `.github/workflows/ci.yml`:
  - Runs on every push and PR to `main`
  - Jobs: `lint`, `test-backend`, `test-frontend`, `build` (matrix: ubuntu, macos, windows)
  - Caches `uv`, `pnpm`, and Rust dependencies
- [ ] All jobs must pass before phase is complete

### 1.7 Bootstrap Script

- [ ] `scripts/bootstrap.sh` (and `.ps1` for Windows):
  - Checks Node 20+, Python 3.11+, Rust toolchain
  - Runs `pnpm install`, `uv sync`, `cd src-tauri && cargo fetch`
  - Runs initial DB migration
  - Prints "Setup complete. Run `pnpm tauri dev` to start."

### 1.8 ADR-0001 Template

Write `docs/adr/0001-local-first-architecture.md`:

```markdown
# ADR-0001: Local-First Architecture

## Status: Accepted

## Context
We need to decide where user data and AI inference happen. Options: cloud-hosted SaaS, hybrid (cloud backend + local frontend), or fully local-first.

## Decision
Fully local-first. Tauri desktop app, SQLite local DB, AI calls go directly from user's machine to whichever provider they configured (Claude Code, Ollama, Anthropic API).

## Consequences
- ✅ Strong privacy story — no third-party cloud touches user data
- ✅ Users can use existing AI subscriptions (no extra cost)
- ✅ No backend infrastructure for us to operate or pay for
- ❌ Cross-platform packaging is harder (signed builds for 3 OSes)
- ❌ No multi-device sync (out of scope by design)
- ❌ Crawler runs from user IP, more likely to hit rate limits
```

## Verification Steps

Before marking this phase complete:

1. `./scripts/bootstrap.sh` works on a fresh clone (test in a clean directory)
2. `pnpm tauri dev` opens a window
3. Health-check button works and shows real DB-backed response
4. CI is green on `main`
5. `docs/CURRENT_PHASE.md` updated to "Phase 1 complete; Phase 2 starting"
6. PR merged to `main` with title `feat: phase 1 — foundation`

## What's Out of Scope for Phase 1

- LLM integration (that's Phase 2)
- CV parsing or upload UI (Phase 3)
- Crawler (Phase 4)
- Any actual feature

Resist the urge to "just add" things. Phase 1 done well makes Phase 2 trivial.
