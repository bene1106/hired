# Hired.

A local-first desktop AI career agent. Hired. helps users find jobs, generate
tailored applications, and prep for interviews — all on the user's own machine.
No cloud backend, no third-party data collection, no subscription fees beyond
whichever AI provider the user already has (Claude Code, Ollama, or the
Anthropic API).

See [`docs/PROJECT_DOC.md`](docs/PROJECT_DOC.md) for the full architecture and
product specification, and [`CLAUDE.md`](CLAUDE.md) for build and contribution
conventions.

## Quickstart

```bash
git clone <repo>
cd hired
./scripts/bootstrap.sh    # macOS/Linux  — or scripts\bootstrap.ps1 on Windows
```

Requires Node 20+, Python 3.11+, and a Rust toolchain.

## Development

Until Phase 6 lands the bundled sidecar, dev runs the FastAPI backend
and the Tauri shell as **two separate processes**. Open two terminals:

```bash
# Terminal 1 — backend sidecar (FastAPI on :8765)
cd backend
uv run uvicorn api.main:app --reload --port 8765

# Terminal 2 — Tauri shell with the React frontend
pnpm tauri dev
```

The frontend talks to the backend over `http://localhost:8765` in both
dev and (eventually) prod, so the only difference Phase 6 will make is
that the sidecar starts itself. See
[ADR-0001](docs/adr/0001-local-first-architecture.md) for the
architectural foundation, and the Phase 1 scope notes in
[`docs/CURRENT_PHASE.md`](docs/CURRENT_PHASE.md) for why bundling was
deferred.

For backend-only or frontend-only loops, see the per-package commands
in [`CLAUDE.md`](CLAUDE.md#build--run).

### Troubleshooting

- **"Backend not reachable"** in the app window — the FastAPI sidecar
  isn't running on port 8765. Start Terminal 1 (above) and reload the
  app. If the port is already in use, set `VITE_BACKEND_URL` for the
  frontend and `--port` for uvicorn to a free one.
- **CORS errors in the browser/Tauri webview** — the backend allows any
  `localhost` origin; if you're hitting it from a non-localhost URL,
  it'll be blocked. Check the origin shown in the error and adjust
  `app.add_middleware(CORSMiddleware, ...)` in `backend/api/main.py`.
- **Health-check fails immediately on launch** — the SQLite DB at
  `~/.hired/data.db` may have been created by a future migration that
  this branch doesn't have. Either check out the matching branch or
  remove `~/.hired/` to re-bootstrap.

## Repository Layout

| Path           | Contents                                              |
|----------------|-------------------------------------------------------|
| `src-tauri/`   | Rust shell, app config, distribution                  |
| `frontend/`    | React + TypeScript + Tailwind                         |
| `backend/`     | Python FastAPI sidecar (LLM, prompts, crawler, db, api) |
| `eval/`        | Goldset for prompt evaluation                         |
| `docs/`        | Project doc, ADRs, build guide, changelog             |
| `.claude/`     | Phase specs and slash commands for the build process  |

## License

MIT — see [`LICENSE`](LICENSE).
