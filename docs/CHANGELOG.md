# Changelog

All notable user-visible changes to Hired. are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 3 — Profile setup & onboarding: a five-step wizard (welcome →
  pick provider → upload CV → review profile → done) is now the entry
  point for first-time users; the main app shell and Settings screen
  exist behind it. PDF or pasted CVs are extracted with `pypdf`, parsed
  via `LLMProvider.parse_cv`, and persisted alongside structured
  profile fields. Settings lets users switch providers, edit their
  profile, and "Delete everything" — a two-step destructive action that
  truncates the DB **and** clears the keychain entry so no secrets are
  left behind. Migration `0003` reshapes the profile schema for plural
  preferences (`target_roles_json`, `target_locations_json`,
  `priorities_json`) and adds `provider_call_log` for the Settings UI.
- Phase 2 — LLM provider layer: `LLMProvider` Protocol with seven
  methods (`parse_cv`, `score_job`, `research_company`, `tailor_cv`,
  `generate_cover_letter`, `generate_interview_questions`,
  `evaluate_answer`); `MockProvider` for tests and offline use;
  `AnthropicAPIAdapter` against the public Anthropic API; OS-keychain
  credentials helper; provider factory keyed on `app_config.provider`
  with `model` configurable per provider. ADR-0005 records why we
  shipped the API adapter first. Goldset bootstrapped with 3 examples
  in `eval/goldset.json`.
- Phase 1 — Foundation: Tauri 2.x shell + React/TS/Tailwind frontend +
  FastAPI sidecar with `/health` endpoint + SQLite + Alembic migrations
  for the initial 7-table schema. CI runs backend + frontend checks on
  every push and the Tauri build matrix on PRs to main and tag pushes.
  Cross-platform bootstrap scripts (`scripts/bootstrap.{sh,ps1}`).
