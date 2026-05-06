# Current Phase

Phase 1 complete (PR #1 awaiting merge); Phase 2 — LLM provider layer ready
to start once merged.

PR: https://github.com/bene1106/hired/pull/1
Spec for the next phase: `.claude/specs/PHASE_2_llm_layer.md`

## Phase 1 — completed checklist

- [x] Repo bootstrap: `.gitignore`, `.gitattributes`, `LICENSE` (MIT, Benedict
  Herrnleben), project `README.md`, `docs/CHANGELOG.md`, ADR-0001.
- [x] Tauri 2.x shell at `src-tauri/` (identifier `dev.hired.app`, window
  1280x800, min 800x600). `cargo check` + `cargo clippy -D warnings` clean.
- [x] React + TS strict + Vite + Tailwind + shadcn init at `frontend/`.
  Single page renders the title and the "Run health check" button. ESLint
  flat config, Prettier, Vitest — 1 test passes.
- [x] FastAPI sidecar at `backend/` with `GET /health` returning the
  spec-mandated JSON after a real DB query. ruff + pytest — 3 tests pass.
- [x] Initial Alembic migration creates the 7 tables and seeds
  `app_config` with `provider=mock`. Migrations auto-run on FastAPI
  startup via lifespan handler.
- [x] CI workflow at `.github/workflows/ci.yml`: backend + frontend checks
  on every push; full Tauri build matrix (ubuntu/macos/windows) gated to
  PRs targeting main and tag pushes (per the cost decision).
- [x] Cross-platform `scripts/bootstrap.{sh,ps1}` — verified end-to-end
  on this Windows machine.

## Scope reductions logged during Phase 1

- **Sidecar bundling deferred to Phase 6.** PyInstaller-bundling the
  FastAPI sidecar into the Tauri build proved to be a big cross-platform
  CI lift; we deferred it. In Phase 1 the user runs `uvicorn` separately
  during dev; the frontend hits `http://localhost:8765` either way. See
  the strikethrough note in `.claude/specs/PHASE_1_foundation.md` task 1.2.
