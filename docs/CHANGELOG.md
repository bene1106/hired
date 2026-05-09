# Changelog

All notable user-visible changes to Hired. are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 4 — Job ingestion & ranked feed: clicking **Crawl** opens an
  inline panel where the user pastes job URLs (one per line); the
  backend fetches each URL, extracts metadata via JSON-LD (`JobPosting`
  schema) with Open Graph fallback, persists deduplicated rows on
  `(source, source_id)`, and scores them against the saved profile via
  `LLMProvider.score_job`. Scores are cached on `(profile_version,
  job_id)` and invalidate automatically when the profile is edited. The
  feed renders ranked job cards with a color-coded score badge, a
  2-sentence rationale, matched/missing skill chips, and Apply / Save /
  Skip buttons; a top-of-page filter row switches between All / Saved /
  Applied / Skipped. A best-effort experimental LinkedIn scraper exists
  but is clearly labeled as unreliable in the UI (see ADR-0006).
  Migration `0004` adds `remote_policy`, `salary_min`, `salary_max`,
  `currency` to `jobs` and `profile_version` to `profile` and
  `job_scores`. The eval harness was rebuilt: `eval/goldset.json` now has
  20 manually-labeled CV/job pairs covering SWE, data, design, PM,
  marketing+sales, and four borderline edge cases; `make eval` reports
  precision@5 and MAE; `make bias-audit` swaps candidate names against a
  fixed pair list and flags any pair with >10pt score variance.
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
