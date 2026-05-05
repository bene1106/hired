# Phase 3 — Profile Setup & Onboarding

**Duration:** Week 3
**Owner suggestion:** Frontend + AI Engineer (paired)
**Depends on:** Phases 1, 2 complete

## Goal

Build the first user-facing flow: a new user opens Hired., picks an LLM provider, uploads their CV, sets preferences, and ends up at an empty job feed. The full app feels "real" by the end of this phase.

## Acceptance Criteria

A new user can:
1. Launch the app fresh (no `~/.hired/` data)
2. Step through the onboarding wizard:
   - Welcome → pick provider (with auto-detect of API key in env or prompt to enter)
   - Upload CV (PDF or text) → see parsed structured profile
   - Confirm/edit profile fields (target role, salary, location, priorities)
3. Land at the main app screen showing "No jobs yet — run a crawl"
4. Reopen the app: skip onboarding, land directly at main screen
5. Open Settings → see active provider, switch provider, edit profile

## Tasks

### 3.1 Onboarding Wizard (Frontend)

In `frontend/src/onboarding/`:

- **Step 1 — Welcome**: brief intro, "Get started" button
- **Step 2 — Provider Setup**:
  - Three cards: Anthropic API (recommended), Claude Code (experimental), Ollama (privacy)
  - Auto-detect status (call backend `/api/setup/detect-providers`)
  - Disable cards for providers not detected, show "Install" link
  - For API: text input for key, "Test connection" button → calls backend `/api/setup/test-provider`
- **Step 3 — CV Upload**:
  - Drop zone for PDF/text, or paste text
  - Submit → POST to `/api/profile/cv` → backend parses → returns structured data
  - Show loading state with provider-aware latency message (e.g., "~10s with API")
- **Step 4 — Profile Review**:
  - Form pre-filled with parsed CV data
  - Editable fields: name, email, target role(s), target salary range, target locations, priorities (multi-select)
  - Submit → POST to `/api/profile`
- **Step 5 — Done**: "You're all set" → navigate to main app

Use shadcn/ui components. Apply provider-aware loading states from the design spec (see `docs/PROJECT_DOC.md` Section 6).

### 3.2 Backend Endpoints

In `backend/api/routes/`:

```
POST /api/setup/detect-providers
  Returns: {"anthropic_api": {"key_in_env": bool}, "claude_code": {"detected": bool, "path": str|null}, "ollama": {"detected": bool, "models": list}}

POST /api/setup/test-provider
  Body: {"provider": str, "api_key": str|null}
  Returns: {"ok": bool, "latency_ms": int, "error": str|null}

POST /api/profile/cv
  Body: {"cv_text": str} or multipart with PDF
  Returns: parsed profile dict (uses LLMProvider.parse_cv)

POST /api/profile
  Body: full profile dict
  Returns: saved profile
  
GET /api/profile
  Returns: current profile or 404
```

### 3.3 CV Parsing Pipeline

In `backend/services/cv_service.py`:

- For PDF: extract text with `pypdf` (no LLM needed for text extraction)
- For text: pass through
- Pass text to `LLMProvider.parse_cv()` → returns structured dict
- Store both `cv_text` (raw) and `cv_parsed_json` (structured) in `profile` table

The parsed structure should include: name, email, summary, work_experience (list), education (list), skills (list), languages (list).

### 3.4 Provider Detection

In `backend/services/provider_detection.py`:

- Anthropic API: check `ANTHROPIC_API_KEY` env var; check keychain
- Claude Code: `which claude` → if found, run `claude --version` → return path + version
- Ollama: HTTP GET `http://localhost:11434/api/tags` → list models if responsive

Return structured result for each. Don't crash if any check fails — return `detected: false`.

### 3.5 Settings Screen

After onboarding, the Settings screen should let the user:
- See current active provider with status (last call latency, total calls today)
- Switch provider (re-runs the provider setup flow but inline)
- Edit profile (re-renders Step 4 of wizard)
- Wipe all local data ("Delete everything" with two-step confirmation) → calls `DELETE /api/data/all`

### 3.6 Main App Skeleton

The main app screen (post-onboarding) is a basic shell:
- Top bar: "Hired." logo, "Crawl" button, settings gear
- Main area: empty state "No jobs yet — click Crawl to find some" 
- Footer: provider status indicator (small text + colored dot)

This shell will be filled in Phase 4. For now it just needs to exist and route correctly.

### 3.7 Frontend Tests

- Onboarding wizard renders each step
- Form validation rejects bad inputs (empty CV, malformed email)
- Provider detection card disables when not detected
- Mock API client used in tests (Vitest + msw)

### 3.8 Backend Tests

- CV parsing: integration test with MockProvider (returns stub structured data)
- Profile CRUD endpoints
- Provider detection: mock filesystem and HTTP for deterministic results

## Verification Steps

1. Fresh `~/.hired/` removed, `pnpm tauri dev` shows wizard
2. Complete wizard end-to-end with MockProvider — lands at main screen
3. Restart app — skips wizard, lands at main screen
4. Switch to API provider in Settings, complete wizard for that provider — works
5. "Delete everything" wipes DB cleanly, app re-shows wizard
6. CI green; `docs/CURRENT_PHASE.md` updated; PR merged

## Out of Scope

- Job feed (Phase 4)
- Application generation (Phase 5)
- Full polish and edge cases (Phase 6)

## Important Notes

- **CV parsing is a first encounter with prompt injection risk.** Wrap user CV text in clear delimiters in the prompt (e.g., `<CV>...</CV>`) and instruct the LLM to treat it as untrusted data
- **PDFs can be huge.** Limit upload to 5MB; truncate text to 30KB before sending to LLM
- **Test with messy CVs** — multilingual, weird formatting, missing sections — make sure parsing degrades gracefully
