# Phase 1 — Foundation — MVP (shipped in v0.1.1)

**Status:** ✅ DONE

> Versionshinweis: Phasen 1–6 wurden als zusammenhängende MVP-Entwicklung
> gebaut und ohne eigene Zwischen-Tags gemerged. Der erste veröffentlichte
> Tag ist `v0.1.1` (2026-05-17). Im CHANGELOG sind alle sechs Phasen unter
> dem Eintrag `[0.1.1]` gesammelt.

## Scope

Projekt-Grundgerüst: Tauri-Shell + React/TS-Frontend + FastAPI-Sidecar +
SQLite + CI. Der Tauri↔FastAPI-Handshake steht.

Spec: `.claude/specs/PHASE_1_foundation.md`

## Real erledigt

- Repo-Bootstrap: `.gitignore`, `.gitattributes`, `LICENSE` (MIT, Benedict
  Herrnleben), `README.md`, `docs/CHANGELOG.md`, ADR-0001.
- Tauri 2.x Shell unter `src-tauri/` (Identifier `dev.hired.app`, Fenster
  1280×800, min 800×600). `cargo check` + `cargo clippy -D warnings` clean.
- React + TS (strict) + Vite + Tailwind + shadcn unter `frontend/`. ESLint
  flat config, Prettier, Vitest.
- FastAPI-Sidecar unter `backend/` mit `GET /health` (echte DB-Query).
  ruff + pytest grün.
- Erste Alembic-Migration `0001_initial_schema.py` legt die 7 Tabellen an
  und seedet `app_config` mit `provider=mock`. Migrationen laufen beim
  FastAPI-Start automatisch (lifespan handler).
- CI unter `.github/workflows/ci.yml`: Backend- + Frontend-Checks bei jedem
  Push; voller Tauri-Build-Matrix (ubuntu/macos/windows) auf PRs nach main
  und Tag-Pushes.
- Cross-Platform `scripts/bootstrap.{sh,ps1}`.

PR: #1 (`feat/phase-1-foundation`) · ADR: `docs/adr/0001-local-first-architecture.md`

## Offen

Keine — Phase abgeschlossen.

## Out-of-scope / Deferrals

- **Sidecar-Bundling** (PyInstaller in den Tauri-Build) wurde nach Phase 6
  verschoben. In Phase 1 läuft `uvicorn` separat im Dev; das Frontend trifft
  `http://localhost:8765`.
