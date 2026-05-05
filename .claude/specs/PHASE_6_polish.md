# Phase 6 — Multi-Provider, Packaging & Polish

**Duration:** Weeks 7–8
**Owner suggestion:** AI Engineer (adapters) + Backend (packaging) + Team (polish)
**Depends on:** Phases 1–5 complete (MVP works end-to-end)

## Goal

By end of Phase 6:
- ClaudeCodeAdapter and OllamaAdapter work, user can switch freely
- App builds and installs on macOS, Windows, Linux from GitHub Releases
- Accessibility audit done, UX polish complete
- Final demo + presentation ready

## Acceptance Criteria

1. User with Claude Pro can switch to Claude Code in Settings → app continues working without changes elsewhere
2. User with Ollama installed can switch to Ollama → cover letters generate (even if slower/lower quality)
3. Anyone can download the installer from GitHub Releases for their OS and run it without compiling from source
4. WCAG AA accessibility audit passes on key screens
5. Final 5-min demo video recorded and presentable

## Tasks

### 6.1 ClaudeCodeAdapter

In `backend/llm/claude_code.py`:

- Wraps the `claude` CLI via `subprocess.run`
- Detects CLI presence at startup; raises clear error if not found
- Passes `--print --output-format json` for parseable output
- Per-call timeout: 120s
- Implements the same `LLMProvider` interface as the API adapter
- Loads same prompt templates (might need slight tweaks for CLI quirks)

**Important — UI signaling:**
- Add a `"experimental"` flag to provider metadata
- Settings UI shows a yellow "Experimental" badge for Claude Code
- Onboarding includes a clear notice: "Hired. uses your local Claude Code installation. Your usage counts against your Claude subscription. Subject to Anthropic's terms."

### 6.2 OllamaAdapter

In `backend/llm/ollama.py`:

- HTTP client to `http://localhost:11434/api/generate` (and `/api/chat` for chat-style)
- Model selection from app config; default `qwen2.5:14b` for capable hardware, fallback `llama3.2:3b` for low-end
- Capability detection: check available models; warn if recommended model not present
- Timeout: 180s (local can be slow)
- Loads same prompts; **may need adjusted few-shot examples** for smaller models

**Latency expectations:** explicitly document and surface. UI shows "may take up to 90s" + Cancel button.

### 6.3 Provider Switching UI

Update Settings → Provider section:
- Live status: "Currently using: Claude Code · ✓ Healthy · 18s avg latency · 47 calls today"
- "Switch provider" → re-launches setup flow inline (modal)
- Switching persists immediately in DB
- Cost section adapts: API shows $, Claude Code shows "subscription", Ollama shows "local"

### 6.4 Cross-Platform Packaging

Set up Tauri build for all 3 OSes via GitHub Actions:

```yaml
# .github/workflows/release.yml
on:
  push:
    tags: ['v*']

jobs:
  build:
    strategy:
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - ... build Tauri app ...
      - upload artifact to release
```

**Sidecar binary:**
- FastAPI backend bundled as a single binary using `pyinstaller`
- Tauri config points to the bundled binary

**macOS signing:**
- Try Apple Developer ID if team has access ($99/year)
- Otherwise: ship unsigned with clear instructions ("Open Hired.app via right-click → Open the first time")
- Document the workaround in `docs/install/macos.md`

**Windows signing:**
- Same — ship unsigned initially with SmartScreen workaround instructions
- Document in `docs/install/windows.md`

**Linux:**
- AppImage (works on most distros)
- Bonus: `.deb` for Debian/Ubuntu via `tauri-bundler`

### 6.5 Accessibility Audit

- Run axe-core on key screens (onboarding, feed, application generation, dashboard)
- Fix all critical/serious issues:
  - Keyboard navigation (Tab order, focus traps in modals, Esc closes)
  - ARIA labels for icon-only buttons
  - Color contrast (WCAG AA minimum)
  - Screen reader announcements for loading states (`aria-live`)
- Document audit results in `docs/accessibility-audit.md`

### 6.6 README & API Docs

- Polish `README.md` with:
  - Hero shot (screenshot of the app)
  - 3-line elevator pitch
  - "Get Started" with download links + minimal setup
  - Tech stack
  - Contributing
- API docs: FastAPI auto-generates OpenAPI; export to `docs/api.md` via `redoc-cli`
- Add `docs/architecture.md` with the architecture diagram from the project doc

### 6.7 Stretch Goals (only if time permits)

- **Mock interview chatbot**: full conversation with feedback; spec is just an extension of `evaluate_answer`
- **Salary benchmark**: integrate with a free salary API or scrape (very risky for time)
- **Rejection pattern analysis**: query past rejections, ask LLM for patterns
- **Multi-language**: prompt-level support for German cover letters

Discuss as a team in W6 sync: pick at most 1 stretch goal. Prioritize polish over more features.

### 6.8 Demo Video

Record a 5-minute screen capture demo:
- Same script as final presentation
- Voice over (one team member, English or German)
- Edit minimally: cuts only, no fancy transitions
- Upload to YouTube unlisted; link in README and presentation deck

### 6.9 Final Bug Bash

Two days before final presentation:
- Each team member uses the app for 1 hour as a real user
- File issues for everything broken or weird
- Triage: must-fix vs nice-to-have
- Fix must-fixes; document nice-to-haves as known issues

## Verification Steps

1. Fresh user on macOS, Windows, Linux can install + use the app
2. Switching providers works without app restart
3. axe-core audit: 0 critical, 0 serious issues on main screens
4. Demo video recorded and watched by full team — no surprises
5. Final presentation deck rehearsed at least once
6. CI green; v1.0.0 tagged; release page populated

## Out of Scope (Explicit)

These remain out even in stretch:
- Web/mobile version
- Cloud sync
- Recruiter side
- Auto-application submission

## Phase Demo

This phase's demo IS the final presentation. See Section 12 of project doc for the script.

## Reflection

After this phase, write `docs/postmortem.md`:
- What worked
- What didn't
- What we'd do differently
- Lessons for the next project

This is a strong final touch for the documentation grade.
