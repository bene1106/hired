# Hired. — Backend Sidecar

FastAPI app that runs locally on the user's machine. The Tauri shell talks to
it over `http://localhost:8765`.

## Layout

```
backend/
├── api/         # FastAPI app + routes
├── db/          # SQLAlchemy engine, session, models
├── llm/         # LLM provider adapters and prompt loader (Phase 2+)
├── prompts/     # Versioned prompt templates (Phase 2+)
├── alembic/     # DB migrations (added in Phase 1, task 1.5)
└── tests/       # pytest
```

## Develop

From this directory:

```bash
uv sync                                                 # install deps
uv run uvicorn api.main:app --reload --port 8765        # dev server
uv run pytest                                           # tests
uv run ruff check .                                     # lint
uv run ruff format .                                    # format
```

## Database

SQLite at `~/.hired/data.db` (created on first run). Override with the
`HIRED_DB_URL` env var, e.g. `sqlite:///./scratch.db` or `:memory:` (used by
the test suite via `tests/conftest.py`).
