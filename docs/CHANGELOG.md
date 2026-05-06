# Changelog

All notable user-visible changes to Hired. are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 1 — Foundation: Tauri 2.x shell + React/TS/Tailwind frontend +
  FastAPI sidecar with `/health` endpoint + SQLite + Alembic migrations
  for the initial 7-table schema. CI runs backend + frontend checks on
  every push and the Tauri build matrix on PRs to main and tag pushes.
  Cross-platform bootstrap scripts (`scripts/bootstrap.{sh,ps1}`).
