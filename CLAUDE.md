# Hired. — Local-First AI Career Agent

## What This Project Is

Hired. is a desktop app that helps users find jobs, generate tailored applications, and prep for interviews. The defining constraint: **everything runs locally on the user's machine**. No cloud backend operated by us.

## Architecture (One-Line Summary)

Tauri shell + React frontend + FastAPI sidecar (Python) + SQLite + pluggable LLM provider (Claude Code CLI / Ollama / Anthropic API).

Full architecture lives in `docs/PROJECT_DOC.md`. Read it before making structural changes.

## Repository Layout

```
hired/
├── src-tauri/          # Rust shell, app config, distribution
├── frontend/           # React + TypeScript + Tailwind
├── backend/            # Python FastAPI sidecar
│   ├── llm/            # LLM provider adapters
│   ├── prompts/        # Versioned prompt templates
│   ├── crawler/        # Playwright-based job ingestion
│   ├── db/             # SQLAlchemy models + migrations
│   └── api/            # FastAPI routes
├── eval/               # Goldset for evaluation
├── docs/               # Project doc, ADRs, build guide
├── .claude/
│   ├── specs/          # Phase implementation specs (read these before each phase)
│   └── commands/       # Slash commands for recurring workflows
└── CLAUDE.md           # This file
```

## Build & Run

```bash
# Backend (from /backend)
uv sync                        # install Python deps
uv run pytest                  # run tests
uv run uvicorn api.main:app --reload --port 8765

# Frontend (from /frontend)
pnpm install
pnpm test                      # run Vitest
pnpm dev                       # dev server

# Full app (from repo root)
pnpm tauri dev                 # launches Tauri shell with sidecar
```

## Code Conventions

- **Python**: Python 3.11+, type hints required, ruff for linting/formatting, pytest for tests
- **TypeScript**: strict mode, no `any`, ESLint + Prettier
- **Imports**: absolute imports from package roots, no deep relative paths
- **Tests**: every public function has a unit test; integration tests use the MockProvider
- **Commits**: conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`)

## Always Do

- Read the relevant phase spec in `.claude/specs/` before starting a phase
- Run `pytest` and `pnpm test` before claiming a task is complete
- **Run lint AND format checks before pushing** — CI runs both, and
  format-only failures have already burned us twice (Phase 3, Phase 4).
  Use the full CI mirror:
  - Backend: `cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
  - Frontend: `cd frontend && pnpm typecheck && pnpm lint && pnpm format:check && pnpm test --run`
- Use the LLMProvider interface, never call adapter implementations directly from business logic
- Write tests against `MockProvider`, not real LLM providers (faster, deterministic, no API costs)
- Update `docs/CHANGELOG.md` for any user-visible change
- When adding a new prompt, save it as a versioned file in `backend/prompts/` and reference it by name

## Git Workflow (always)

- Commit after every meaningful unit of work — don't accumulate huge changesets
- Conventional commits: `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`, `test: ...`, `chore: ...`
- One logical change per commit (e.g., "feat: add CV parsing endpoint" — not "feat: phase 3 progress")
- Run tests before committing; never commit failing code
- After completing each phase, push to origin: `git push origin main`
- If unsure whether to commit: commit. Granularity is cheap, lost work is expensive.

## Never Do

- Hardcode API keys or secrets — always use the OS keychain abstraction in `backend/llm/credentials.py`
- Send PII to logs (use the redaction helper in `backend/observability/logging.py`)
- Bypass the LLMProvider interface to call a provider directly
- Mutate user data without writing to SQLite first (single source of truth)
- Add a cloud-hosted dependency (this project is local-first by design)
- Skip tests because "this is a small change" — run them anyway

## Decision Hierarchy When Uncertain

1. Check the relevant `.claude/specs/PHASE_*.md` — phase specs are authoritative for what to build
2. Check `docs/PROJECT_DOC.md` for architecture and scope decisions
3. Check `docs/adr/` for documented past decisions
4. If still unclear, **stop and ask** — don't guess on architecture or scope

## Working in Phases

This project is built in 6 phases. The current phase is tracked in `docs/CURRENT_PHASE.md`. Each phase has a spec in `.claude/specs/` with explicit acceptance criteria. **Do not start a new phase before the previous one's tests pass and acceptance criteria are met.**

| Phase | Focus | Spec |
|-------|-------|------|
| 1 | Foundation: repo, CI, schema, Tauri+FastAPI handshake | `PHASE_1_foundation.md` |
| 2 | LLM provider abstraction + MockProvider + AnthropicAPIAdapter | `PHASE_2_llm_layer.md` |
| 3 | Profile setup: CV upload, parsing, onboarding wizard | `PHASE_3_profile.md` |
| 4 | Job ingestion + scoring + ranked feed | `PHASE_4_jobs.md` |
| 5 | Application materials + dashboard + interview prep | `PHASE_5_applications.md` |
| 6 | ClaudeCodeAdapter + OllamaAdapter + packaging + polish | `PHASE_6_polish.md` |

## Critical: LLM Provider Behavior

The LLMProvider interface is the heart of the app. Three rules:

1. **Business logic only ever sees `LLMProvider`**, never a concrete adapter
2. **MockProvider is the default in tests**, returning deterministic stub data
3. **Provider is configured once at startup** from `~/.hired/config.toml` and injected via FastAPI dependency

If you find yourself importing `ClaudeCodeAdapter` or `OllamaAdapter` outside of `backend/llm/`, you're doing something wrong.

## When Tests Fail

1. Read the failure message; don't just retry
2. If a test fails because the spec changed, update the test (not the spec)
3. If a test fails because the implementation is wrong, fix the implementation
4. **Never** mark a test as `@skip` to "make it green" without an issue link explaining why
