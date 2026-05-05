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
pnpm tauri dev            # opens the app window
```

Requires Node 20+, Python 3.11+, and a Rust toolchain.

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
