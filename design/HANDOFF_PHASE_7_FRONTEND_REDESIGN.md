# Hired. — Phase 7: Frontend Redesign Handoff

**Status as of 2026-05-18:** v0.1.1 is live and public. The app works end-to-end across all phases (1-6). This document hands off everything needed to start Phase 7 — a frontend redesign — in a fresh chat session.

The design is already extracted and analyzed below.

---

## 0. How to use this document

Paste this entire file into a new chat as your first message, followed by:

> "Read this handoff. We're starting Phase 7. The design is already analyzed below. I'll also upload the full design ZIP so you can see the actual JSX components."

The new assistant will have full context to plan and execute Phase 7.

---

## 1. Project at a glance

**Hired.** is a local-first AI career agent — a desktop application that helps with job search end-to-end. Built as a university software engineering project but pivoted to a personal tool. The user (Bene/bene1106) intends to use it for their own job/internship search.

- **Repo:** https://github.com/bene1106/hired
- **Local path:** `D:\AAAAA_BEWERBUNGS_KI\hired\`
- **Latest release:** v0.1.1 (public, working, all installers built)
- **User language:** German (project code/docs are English)
- **User profile:** B.Sc. CS student at FU Berlin, building this for their own job search
- **OS:** Windows 11 (PowerShell)

### Stack

```
Tauri 2.x (Rust shell)
├── React 18 + TypeScript (strict) + Vite + Tailwind + shadcn/ui frontend
└── FastAPI (Python 3.11) sidecar bundled via PyInstaller
    ├── SQLite at ~/.hired/db.sqlite
    ├── OS keychain for secrets
    └── LLM provider abstraction (Anthropic API, Claude Code CLI, Ollama, Mock)
```

### Architecture principle

**Local-first.** CV, jobs, applications, and API keys never leave the user's machine. Pluggable LLM provider abstraction with ~95% provider-agnostic UI.

---

## 2. What's been built (Phases 1–6, all complete)

### Phase 1: Foundation (PR #1)
Tauri shell + React + FastAPI + SQLite + Alembic + CI matrix (3 OS).

### Phase 2: LLM Provider Layer (PR #2)
Pydantic types, `LLMProvider` Protocol, MockProvider, AnthropicAPIAdapter, OS-keychain credentials, factory + caching, prompt loader.

### Phase 3: Profile + Onboarding (PR #3 + #4)
**5-step Onboarding Wizard** (Welcome → Provider → Upload CV → Review → Done), CV parsing pipeline (PDF→text), Settings screen with two-step wipe.

### Phase 4: Crawler + Scoring + Feed (PR #5)
ManualURLSource (httpx + BS4, JSON-LD), LinkedInSource fallback, scoring with profile_version cache, Feed API.

### Phase 5: Application Materials + Dashboard + Interview Prep (PR #6)
Application service orchestrator, generation_progress, pricing, cost_service. 11 application API routes. GeneratePage (sequential reveal), Dashboard (table view), ApplicationDetail (status switcher), InterviewPrep (4 categorized question banks).

### Phase 6: Multi-Provider + Packaging + Polish (PR #7)
Claude Code adapter (subprocess), Ollama adapter (HTTP), PyInstaller bundling, GitHub Actions release.yml matrix builds.

### Hotfix v0.1.1 (PR #8)
Critical packaging bug fixed:
- **CORS:** allowed `http(s)://tauri.localhost` (Windows webview origin)
- **Single-instance guard:** prevented orphaned sidecar processes
- **Fetch retry:** AppGate retries with backoff
- **Production logging:** Tauri log plugin now active in release builds

End-to-end manual test passed with real Anthropic provider on a Goldman Sachs Summer Analyst URL.

---

## 3. The design — what we already know

The design ships as a static HTML+JSX preview (React 18 + Babel standalone, no build step in the preview). The full package is in the ZIP.

### Visual identity

**Theme:** Light "warm off-white + deep ink + muted green" — also has a Dark variant.

**Color tokens (light mode):**
```css
--bg: #F6F3EE          /* warm off-white, paper */
--bg-sunk: #EFEBE3     /* recessed surfaces */
--surface: #FFFDF9     /* cards */
--surface-2: #FAF6EF   /* inputs */
--line: #E4DED2
--line-strong: #CFC7B6
--ink: #1A1A17         /* deep near-black ink */
--ink-2: #3A3832
--ink-3: #6B6A62
--ink-4: #9A988E
--accent: #4F6B4A      /* muted green */
--accent-2: #6E8A65
--accent-soft: #DDE5D3
--accent-tint: #EBF0E2
--warn: #B5571E        /* warm terracotta — for skip/reject */
--warn-soft: #F1E0D3
--brand-orange: #ff6b35 /* logo accent dot */
--brand-ink: #1a1a1a   /* logo mark fill */
--info: #5B6F86
--info-soft: #DEE5EE
```

**Dark mode tokens are also defined** (in `data-theme="dark"` CSS block). Worth implementing both — it's an obvious user expectation.

**Typography:**
- **Sans:** Inter Tight (400/500/600/700)
- **Mono:** JetBrains Mono (400/500) — used for `.mono`/`.tnum` numeric details
- **Serif display:** Fraunces (opsz/wght 9..144, 900) — used for headings like "Let's get your agent ready"
- **Brand:** Archivo Black (900) — wordmark only
- `font-feature-settings: "ss01", "cv11"` enabled
- `font-variant-numeric: tabular-nums` for numbers

**Radii:** `--radius: 10px` (default), `6px` small, `16px` large

**Shadows:** Three levels (sm/md/lg) — subtle, warm, layered

**Animations:**
- `fade-up` (0.5s ease) — main entry transition for screens
- `shimmer` — skeleton loading
- `subtle-bounce`, `pulse-dot`, `ring-fill` — micro-interactions

### Brand mark

The logo is built with two reusable React components in `src/logo.jsx`:

- `HiredMark` — black circle with serif "h" (Fraunces 900) + orange accent dot bottom-right
- `HiredWordmark` — "Hired." in Archivo Black with orange period
- `HiredStacked` — combined mark + wordmark, used on onboarding hero

Sizes are proportional to a 110px reference.

### Layout

App shell is a **2-column grid**: `244px sidebar | flexible main`.

Sidebar (`src/sidebar.jsx`) contains:
- Brand mark + wordmark + "Career Agent" tagline (mono caps)
- 6 nav items: Job Feed, Current Job, Materials, Interview Prep, Applications, Profile
- Badge counters on some items ("12 new", "13")
- Theme toggle (sun/moon)

Main content (`src/app.jsx`) switches between 6 screens:
1. **Feed** — job cards in a scrollable list
2. **Detail** — single job view with apply CTA
3. **Materials** — cover letter + CV tweak generation, with progress ring
4. **Interview** — chat-style coach with category tabs
5. **Kanban** — drag-and-drop applications board (5 columns)
6. **Onboarding** — 4-step wizard (Upload → Review → Prefs → Priorities)

### Component inventory (from src/*.jsx files)

```
data.jsx        — Mock data (JOBS, APPLICATIONS, INTERVIEW_CATEGORIES, etc.)
                  Used by all screens via window.__DATA__
primitives.jsx  — Icon set (~30 line icons), shared hooks
logo.jsx        — HiredMark, HiredWordmark, HiredStacked, CompanyMark
sidebar.jsx     — Left navigation
feed.jsx        — JobCard + Feed list with save/skip/apply actions
detail.jsx     — Single job detail page with hero + description + apply
materials.jsx   — Cover-letter + CV generator with tabs and progress ring
interview.jsx   — Chat-based coach with confidence slider, category tabs
kanban.jsx      — 5-column drag-and-drop board (Discovered/Applied/Interview/Offer/Rejected)
onboarding.jsx  — 4-step wizard
app.jsx         — Root component, theme state, screen router, tweaks panel
```

### Design language summary

- **Tone:** confident, warm, restrained — not playful, not corporate
- **Typography hierarchy:** Fraunces serif for headlines, Inter Tight for body, JetBrains Mono for tabular/numeric
- **Color use:** mostly neutrals; accent green for positive states; warm terracotta for skip/reject only
- **Density:** medium — generous whitespace but not airy
- **Motion:** subtle, purposeful (fade-up on enter, no decorative animation)
- **Icons:** minimal 1.5px-stroke line icons, internally consistent
- **Empty states:** designed (not afterthoughts)

---

## 4. CRITICAL DELTA: design vs. current app

The design and the current app are **structurally different** in several places. Don't assume one-to-one mapping. Decide intentionally.

### Onboarding mismatch

| Current (5 steps) | Design (4 steps) |
|---|---|
| 1. Welcome | (none — design jumps in) |
| 2. Provider | (none — design has no LLM-provider concept) |
| 3. Upload CV | 1. Upload CV |
| 4. Profile (Review) | 2. Review profile |
| 5. Done | 3. Preferences (NEW) |
| | 4. Priorities (NEW) |

**Decision needed:** the design assumes the user already has an LLM provider configured. Hired's whole architecture revolves around the multi-provider abstraction — the Provider step CANNOT be removed.

**Recommended approach:**
- Keep Hired's 5-step onboarding sequence (Welcome → Provider → Upload CV → Review → Done)
- Adopt the design's visual language for the steps that overlap (Upload CV, Review)
- Add Preferences and Priorities as a 6th screen, AFTER onboarding finishes — i.e., on the main app post-onboarding (a "Preferences" or "Settings → Targeting" pane)
- OR: implement Prefs/Priorities as steps 4 and 5 of the wizard, making it 7 steps total (might be too long)

The Provider step needs its own visual treatment in the new design language — it doesn't exist in the design package.

### No "Provider Selection" UI in the design

The design package has no equivalent to ProviderStep.tsx. The new design will need a Provider screen designed from first principles, using the design tokens and component patterns from the package.

**Recommended approach:** mirror the structure of the design's UploadStep — centered card, hero icon, three or four provider tiles (Anthropic, Claude Code, Ollama, Mock), test connection button per tile, "Continue" CTA.

### Screen-naming differences

| Design | Current code |
|---|---|
| Job Feed | FeedScreen.tsx |
| Current Job | (no direct equivalent) |
| Materials | GeneratePage.tsx + ApplicationDetail.tsx (currently split) |
| Interview Prep | InterviewPrep.tsx |
| Applications | Dashboard.tsx (table) → would become Kanban (5-column) |
| Profile | (no current screen — settings has it indirectly) |

**Decision needed:** does the design's Kanban (drag-and-drop, 5 columns) replace the current Dashboard (table view), or supplement it? The Kanban is more visual but loses the table's information density. Bene's preference matters here.

### Job card semantics

The design's JobCard has:
- Save action (heart icon, with toast)
- Skip action (separate from "not interested")
- Up/down feedback ("how did this match feel?")
- Score with 3 weighted reasons + rationale text

Current JobCard.tsx has:
- Save, Skip, Apply actions (per Phase 4 spec)
- Score number (no weighted reasons)
- No feedback up/down

**Decision needed:** add feedback up/down + weighted reasons to the backend? Or visually mimic them with the current data shape? The feedback action implies a new API endpoint.

### Materials screen integration

The design's Materials screen is a single combined view with tabs (Cover Letter / CV / Notes), a progress ring during generation, an editable text area, and an inline "Regenerate" button.

The current app splits this between GeneratePage (sequential reveal during generation) and ApplicationDetail (post-generation editing). These should probably merge into one screen following the design.

### Interview Prep style

The design's interview screen is a **chat-style coach** with:
- Category tabs at the top
- Coach messages with feedback bullets
- User typing input
- Confidence slider (1-5)

The current InterviewPrep.tsx is more list-based with question banks per category.

**Decision (settled):** The chat-style coach is **NOT** in scope for Phase 7. It requires a new streaming backend endpoint, a new prompt pipeline, and conversation history storage — none of which are frontend work.

**What Phase 7 does instead:**
- Keep the existing Question Bank structure (4 categories, curated questions, practice mode)
- Apply the new visual language (Fraunces headlines, card patterns, design tokens)
- Reuse design components where they fit without the chat (category tabs, layout)
- The design's `interview.jsx` chat UI sits idle in the design package — it will be revived in Phase 8

**Phase 8 will:** ship the full chat-style coach. See §17 for the full scope.

### Out of scope for Phase 7 (deferred to specific later phases)

These design features imply backend changes. Each is assigned to a specific future phase, not "Phase 8" as a catch-all:

| Feature | Why deferred | Target phase |
|---|---|---|
| Feedback up/down on job cards | Needs `POST /api/jobs/{id}/feedback` + scoring algorithm rework + DB schema change | **Phase 9 — Learning from feedback** |
| Chat-style interview coach | Needs `POST /api/interview/chat` with streaming + new prompt pipeline + conversation history storage | **Phase 8 — Interactive interview coach** |
| "12 new" unread badge in sidebar | Needs unread tracking in DB + badge state sync across screens | **Phase 9** (alongside feedback learning) |
| Editable Preferences / Priorities steps | Design has them in onboarding; recommend separate Settings section instead | **Phase 8** (as Settings sub-page) |
| Custom company avatars | Currently CompanyMark uses initials; design accepts logos | **Phase 10+** (nice-to-have) |

These features must **NOT** be stubbed visually in Phase 7. Adding dead buttons (UI present, no behavior) creates a worse UX than not having them at all. Better to ship without them and add later when they actually work.

---

## 5. Recommended approach for Phase 7

### Strategy: "Adopt the design language, not the design exactly"

1. **Lift all design tokens** (colors, fonts, radii, shadows) into Tailwind config
2. **Add the brand assets** (HiredMark, HiredWordmark logo components) — they're well-designed
3. **Restyle existing screens** using the design's visual language, keeping current architecture
4. **Adopt new components from the design** that don't conflict with existing flow (sidebar, card patterns, empty states)
5. **Reject or stub design features** that imply backend changes
6. **Implement dark mode** since the design defines it cleanly
7. **Keep Hired's 5-step onboarding sequence**, restyling it with the design's visual language

### Slicing plan (suggested PR order)

This could ship as **one big PR** or **multiple smaller PRs**. Smaller is safer:

**PR A: Design foundation** (`feat/phase-7a-design-tokens`)
- Tailwind config update with design tokens (colors, fonts, radii, shadows)
- Custom CSS variables for theme switching (light/dark)
- Font loading (Inter Tight, JetBrains Mono, Fraunces, Archivo)
- Theme toggle hook + localStorage persistence
- HiredMark, HiredWordmark, HiredStacked logo components

No screen changes yet. CI green. Mergeable on its own.

**PR B: Layout + Sidebar** (`feat/phase-7b-layout`)
- 2-column app shell (sidebar + main)
- Sidebar component with nav items + badge slot + theme toggle
- Route container that uses the shell
- All existing screens render INSIDE the shell unchanged

Existing screens look the same; only the chrome around them is new. Mergeable on its own.

**PR C: Onboarding redesign** (`feat/phase-7c-onboarding`)
- Welcome, Provider, Upload CV, Review, Done — all five steps restyled
- New stepper UI (numbered circles with active/complete states)
- Hero typography (Fraunces serif headlines)
- Card pattern from the design

**PR D: Feed + JobCard** (`feat/phase-7d-feed`)
- Feed list with new card design
- CompanyMark component (initial in colored circle)
- Score display with weighted reasons (stubbed if backend doesn't return them)
- Save/Skip actions with toast feedback

**PR E: Job Detail + Materials** (`feat/phase-7e-application`)
- Merge GeneratePage + ApplicationDetail into one Materials screen
- Tabs (Cover Letter / CV / Notes)
- Progress ring during generation
- Inline regenerate

**PR F: Dashboard → Kanban** (`feat/phase-7f-applications`)
- 5-column board (Discovered, Applied, Interview, Offer, Rejected)
- Card components for each application
- Drag-and-drop (HTML5 DnD, the design uses it)
- Status updates via existing API

**PR G: Interview Prep + Settings** (`feat/phase-7g-rest`)
- Restyle InterviewPrep (keep question-bank structure, adopt visual language)
- Restyle Settings (provider switcher, wipe confirmation)
- Empty states, error states

**PR H: Polish + Release** (`feat/phase-7h-polish`)
- Loading states, skeletons
- Error states
- Animation tuning
- Accessibility re-audit
- Tag v0.2.0

### Alternative: one mega-PR

If the slicing feels like overhead, this CAN go as one big PR — but expect 5+ days of work and a longer review cycle. The slicing is recommended.

### Out of scope for Phase 7 (specific phase assignments)

These should be filed as issues with explicit phase tags:

| Feature | Backend work | Target phase |
|---|---|---|
| Feedback up/down on job cards | New endpoint, DB schema, scoring rework | **Phase 9 — Learning from feedback** |
| Chat-style interview coach | Streaming endpoint, new prompt, conversation storage | **Phase 8 — Interactive interview coach** |
| "12 new" unread badge | Unread tracking in DB | **Phase 9** |
| Editable preferences/priorities | Settings sub-page (the design's onboarding steps 3 and 4) | **Phase 8** (as Settings extension) |
| Custom company avatars | Logo fetching/caching | **Phase 10+** |

Important: **don't visually stub these in Phase 7**. Adding dead buttons that don't work creates worse UX than not having them at all.

---

## 6. Repository layout (current, before Phase 7)

```
hired/
├── src-tauri/               # Rust shell, distribution, app config
│   ├── src/lib.rs          # sidecar spawn, single-instance, logging
│   ├── tauri.conf.json     # version, security (csp: null), bundle config
│   └── Cargo.toml          # version 0.1.1
├── frontend/               # React + TS + Tailwind + shadcn/ui
│   └── src/
│       ├── lib/
│       │   ├── api.ts      # BACKEND_URL, fetch wrapper, full api.* object
│       │   └── types.ts    # all TypeScript types matching backend Pydantic
│       ├── components/
│       │   ├── onboarding/ # ProviderStep, etc.
│       │   ├── SettingsScreen.tsx
│       │   └── ui/         # shadcn primitives (button, badge, dialog, etc.)
│       ├── feed/
│       │   ├── FeedScreen.tsx
│       │   └── JobCard.tsx
│       ├── applications/
│       │   ├── GeneratePage.tsx
│       │   ├── Dashboard.tsx
│       │   ├── ApplicationDetail.tsx
│       │   └── InterviewPrep.tsx
│       ├── App.tsx         # React Router v6 routes
│       └── AppGate.tsx     # boot probe with retry/backoff
├── backend/                # Python FastAPI sidecar
│   ├── api/
│   ├── llm/
│   ├── prompts/
│   └── sidecar.py
├── eval/
├── docs/
└── .github/workflows/
    ├── ci.yml
    └── release.yml
```

---

## 7. Decisions that are SETTLED (don't revisit unless Bene says so)

- Tauri 2.x + React + FastAPI + SQLite stack
- Provider abstraction with Adapter Pattern + Strategy Pattern
- PR-per-phase workflow with **"Create a merge commit"** (never squash)
- All stretch goals skipped, no demo video, ship unsigned binaries
- Manual URL paste is primary crawler input (LinkedIn experimental fallback)
- Cover letter prompt v2 with anti-self-deprecation rule + 3 few-shot examples
- summarize_role implemented in Phase 6
- Version scheme: 0.1.x (early stage). v1.0.0 was burned (broken packaging bug, deleted)
- Action semantics: Skip removes from "All" view. Save/Apply keep card visible.
- `tauri-plugin-single-instance` is wired in; sidecar reaped on app exit
- CORS allow_origin_regex includes `http(s)://tauri.localhost` (critical)
- Production logging writes to `~/.hired/logs/sidecar.log` and Tauri log dir
- AppGate fetch retry with backoff (don't remove)
- **shadcn/ui stays as the component foundation** — restyle within it, don't rip it out

---

## 8. User profile & working style

### Communication style
- Direct, low-tolerance for fluff
- Calls out inconsistencies immediately
- Wants concrete step-by-step instructions without preamble when context is established
- Prefers internal consistency — don't walk back prior guidance without acknowledging it
- Pushes back on patronizing suggestions (no "take a break" / "energy check" defaults)

### Quality bar
- Accuracy over confidence — challenges unverified claims
- Catches subtle bugs others miss (found prompt self-deprecation creep that earlier reviewers missed)
- Senior-level engineering judgment

### Workflow
- Uses Claude Code CLI with `--dangerously-skip-permissions`
- Structured phase-based workflow with spec files, CLAUDE.md, slash commands
- Two terminals during dev (uvicorn + tauri dev); sidecar bundling works only in installed builds

### Stack quirks
- pnpm (standalone installer)
- uv (Astral installer)
- Rust: rustup 1.29, cargo 1.95, rustc 1.95, MSVC
- Python 3.11, Node 20+
- No Ollama installed locally (correctly auto-detected as "Not running")

---

## 9. Open questions for Bene at the start of the new session

Most scope decisions are settled — see §18 for the confirmed list. Only these remain genuinely open:

1. **Slicing strategy:** one mega-PR or 8 small PRs (PR A-H from §5)? Smaller is safer but more overhead. Bene's call.
2. **Dark mode timing:** ship both light + dark in v0.2.0, or light first then dark in v0.3.0? Design has full dark tokens defined — implementing both isn't much extra work, but it's testing surface area.
3. **Target version:** v0.2.0 confirmed? (Minor bump for visible feature; v0.1.x stays for early-stage signal.)
4. **Manual install test on Windows only:** Bene is the only tester (no Mac/Linux access). Acceptable to ship Mac/Linux builds untested?
5. **Font loading strategy:** Google Fonts via CDN (current design uses this) vs. local fonts shipped with the build? CDN is simpler but means external network at runtime. Local fonts are bigger but offline-clean.

Settled (do NOT re-ask):
- Onboarding stays 5 steps with Provider Step (§4)
- Kanban replaces Dashboard table (§18)
- Materials merges GeneratePage + ApplicationDetail (§18)
- Feedback up/down deferred to Phase 9 (§4, §17)
- Chat-style interview coach deferred to Phase 8 (§4, §17)
- Unread badges deferred to Phase 9 (§4, §17)
- shadcn/ui stays as component foundation (§7)

---

## 10. Known gotchas / lessons from the journey so far

These are real bugs that happened. They might happen again during Phase 7.

### v1.0.0 packaging bug (resolved in v0.1.1, MUST stay fixed)
- Packaged Windows build loads webview from `http://tauri.localhost`
- FastAPI CORS must allow this origin (it does, in `backend/api/main.py`)
- If Phase 7 changes anything about the webview origin or fetch logic, re-test packaged build

### Sidecar lifecycle (resolved in v0.1.1)
- PyInstaller onefile spawns 2 procs/launch
- `tauri-plugin-single-instance` is wired in; don't remove
- Sidecar is reaped on app exit (`taskkill /T` on Windows); don't remove

### Cold-start race (resolved in v0.1.1)
- Frontend's first `/health` probe can hit before sidecar is ready
- `AppGate.tsx` retries with backoff; don't remove

### Test stability
- Frontend Vitest tests can be flaky on main branch (one race condition in `SettingsScreen.test.tsx`)
- Backend tests are stable (206 passing, 1 skipped)

### CI quirks
- Tauri build matrix runs on push to main and pull_request (3 OS each)
- PR-gate workflow uploads installer artifacts; you can download a Windows installer from a PR artifact without merging
- Release workflow on tag push creates draft release; needs manual publish

### Font loading in packaged builds
- Design uses Google Fonts (Inter Tight, JetBrains Mono, Fraunces, Archivo)
- Packaged Tauri builds may have CSP restrictions on external fonts — verify in installer
- Alternative: ship fonts locally in `frontend/public/fonts/`

### Tauri-specific styling
- Packaged build's webview is WebView2 on Windows
- CSS that works in dev (Vite over localhost) usually works in packaged builds too — but verify

### Bene's UX preferences (inferred from session)
- Prefers clarity over cleverness in UI copy
- Wants progress visible (he liked the sequential reveal in GeneratePage)
- Doesn't want emojis in core UI (only in casual contexts)
- Wants the app to feel like a tool, not a toy

---

## 11. Quick reference: commands

### Dev (two terminals)
```powershell
# Terminal 1 — backend
cd D:\AAAAA_BEWERBUNGS_KI\hired\backend
uv run uvicorn api.main:app --port 8765

# Terminal 2 — frontend + Tauri
cd D:\AAAAA_BEWERBUNGS_KI\hired
pnpm tauri dev
```

### CI mirror (run before pushing)
```powershell
# Backend
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest -q

# Frontend
cd ../frontend
pnpm typecheck
pnpm lint
pnpm format:check
pnpm test --run
```

### Reset local state (for testing fresh onboarding)
```powershell
Move-Item "$env:USERPROFILE\.hired" "$env:USERPROFILE\.hired.backup_$(Get-Date -Format yyyyMMddHHmmss)" -Force -ErrorAction SilentlyContinue
```

### Installer test
```powershell
Stop-Process -Name "hired*" -Force -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\Hired." -Recurse -Force -ErrorAction SilentlyContinue
# Download new build from PR artifact or Release, install, run from Start menu
```

### Git workflow (per phase convention)
```powershell
git checkout main
git pull origin main
git checkout -b feat/phase-7a-design-tokens   # or whatever slice

# ... work ...

git add .
git commit -m "feat(frontend): <description>"
git push -u origin feat/phase-7a-design-tokens

# Open PR via gh CLI or GitHub UI
# After approval + green CI:
# Use "Create a merge commit" (NOT squash)
# After ALL slices merge:
# Tag v0.2.0, push tag → release.yml builds installers → manually publish
```

---

## 12. Where everything lives

| Thing | Location |
|---|---|
| GitHub repo | https://github.com/bene1106/hired |
| Latest release | https://github.com/bene1106/hired/releases/tag/v0.1.1 |
| Local clone | `D:\AAAAA_BEWERBUNGS_KI\hired\` |
| User data | `%USERPROFILE%\.hired\` |
| Logs | `%USERPROFILE%\.hired\logs\` and `%LOCALAPPDATA%\dev.hired.desktop\logs\` |
| Installer (installed) | `%LOCALAPPDATA%\Hired.\` |
| Project constitution | `CLAUDE.md` (repo root) |
| Phase tracker | `docs/CURRENT_PHASE.md` |
| Architecture | `docs/architecture.md` |
| ADRs | `docs/adr/000{1-7}*.md` |
| API spec | `docs/api.md`, `docs/api.openapi.json` |
| Changelog | `docs/CHANGELOG.md` |

---

## 13. The design package contents

The new session will receive the full ZIP. Files:

```
Hired.html          — Entry HTML with all design tokens (CSS vars), Google Fonts links, Babel script tags
src/
  data.jsx          — All mock data (JOBS, APPLICATIONS, INTERVIEW_CATEGORIES, PARSED_PROFILE, SAMPLE_CHAT)
  primitives.jsx    — Icon set (~30 line icons, 1.5px stroke), shared React imports
  logo.jsx          — HiredMark, HiredWordmark, HiredStacked, CompanyMark
  sidebar.jsx       — Left navigation with brand, nav items, theme toggle
  feed.jsx          — JobCard + Feed list (191 lines)
  detail.jsx        — Single job hero + description + apply (108 lines)
  materials.jsx     — Cover letter + CV tabs, progress ring, regenerate (288 lines)
  interview.jsx     — Chat coach with categories, confidence slider (218 lines)
  kanban.jsx        — 5-column drag-and-drop board (208 lines)
  onboarding.jsx    — 4-step wizard (303 lines)
  app.jsx           — Root, theme state, screen router, tweaks panel (63 lines)
uploads/
  hired_logo_03.html — Standalone logo exploration page
```

The new session should read these files first, before any planning.

---

## 14. First prompt for the new session

After pasting this handoff, Bene should say:

> "Read this handoff. I'm uploading the design ZIP as well — extract it, read every JSX file, then propose the Phase 7 plan. Specifically: (1) confirm the slicing strategy from §5, (2) propose answers to the open questions in §9, (3) flag anything in the design that you think doesn't translate cleanly to my existing architecture. Don't write any code yet."

That forces a planning step before code.

---

## 15. Tone for the new session

Bene works best when the assistant:
- Skips unnecessary preamble
- Gives concrete next steps with copy-pasteable commands
- Numbers options when there's a choice to make
- Pushes back when something feels wrong
- Doesn't apologize for code unless the user is unnecessarily rude
- Avoids self-deprecating phrases
- Doesn't recommend "taking breaks" or do "energy checks"
- Treats v0.1.1 → v0.2.0 as a confident progression

---

## 16. End state target for Phase 7

When Phase 7 is done:
- All PRs (A through H, or one mega-PR) merged to main
- v0.2.0 tagged and released (Public, not Draft)
- All screens use the new design consistently
- Light + Dark mode both work (or one is shipped with the other in v0.3.0, per Bene's call)
- All backend/business logic untouched
- CI is green (frontend tests updated where DOM changed)
- Installer tested end-to-end on Windows
- ADR-0008 added: "Phase 7 frontend redesign — design source, tokens, component mapping"
- CHANGELOG entry for v0.2.0
- Screenshots in README showing the new look
- The app feels meaningfully different to use — not just repainted

---

## 17. Phase roadmap beyond v0.2.0

Phase 7 is the visual upgrade. Other features are mapped to later phases so each ships clean rather than half-built.

### Phase 7 — Visual redesign (v0.2.0)
Pure frontend redesign. Backend untouched.

### Phase 8 — Interactive interview coach (v0.3.0)
Replace the static question-bank UI with a chat-style coach that critiques user answers in real time.
- New endpoint: `POST /api/applications/{id}/interview/chat` with streaming
- New prompt: `backend/prompts/interview_coach.md`
- Conversation history storage (new table or extend `practice_attempts`)
- UI: chat interface from design's `interview.jsx` — already designed, just unused in Phase 7
- Optional: "Preferences" / "Priorities" Settings sub-page (the unused design onboarding steps 3 and 4)

### Phase 9 — Learning from feedback (v0.4.0)
Make the score algorithm adapt to user preferences over time.
- Feedback up/down buttons on job cards (Phase 7 doesn't ship these)
- New endpoint: `POST /api/jobs/{id}/feedback`
- New DB table: `job_feedback (job_id, action, timestamp)`
- Score algorithm rework: blend CV-match score with feedback signal
- Optional: vector embedding of liked vs disliked jobs for nearest-neighbor scoring
- Unread tracking + "X new" sidebar badges (uses same iteration)

### Phase 10+ — Nice-to-haves
- Custom company avatars (logo fetching/caching)
- Multi-user mode (currently single-user)
- Export applications as PDF
- Calendar integration for interview scheduling

### Why this split

The temptation in Phase 7 will be "while I'm in there, let me add this small thing." Resist it.

- Each future phase should be **mergeable in 5-10 days**
- Each future phase should ship **one new capability** done right, not three half-built
- Visual stubs that don't work are **worse than nothing** — they teach users buttons can be useless

The user (Bene) values "tools, not toys" — every feature should actually do its job.

---

## 18. Confirmed scope decisions for Phase 7

From the conversation that produced this handoff, these are settled:

### ÜBERNEHMEN (in Phase 7)
- ✅ Onboarding 5-Step structure with new visual (Welcome → Provider → Upload → Review → Done)
- ✅ Provider Step — newly designed in the visual language (no design template exists; mirror UploadStep pattern)
- ✅ 2-column app shell with sidebar (from design)
- ✅ Sidebar component with nav items + theme toggle
- ✅ Feed + JobCard restyled (Save/Skip/Apply actions kept, no up/down)
- ✅ Materials screen — **merge** GeneratePage + ApplicationDetail into one (from design)
- ✅ Kanban — **replaces** Dashboard table (uses existing `updateApplicationStatus` endpoint, no backend changes)
- ✅ Interview Prep — Question Bank kept, visual restyle only (no chat coach yet)
- ✅ Settings — new visual
- ✅ Dark mode (light + dark both shipped in v0.2.0)
- ✅ Empty states + error states
- ✅ Brand assets (HiredMark, HiredWordmark, HiredStacked)
- ✅ Typography (Inter Tight, JetBrains Mono, Fraunces, Archivo Black)

### NICHT ÜBERNEHMEN (deferred)
- ❌ Feedback up/down buttons on job cards → Phase 9
- ❌ Chat-style interview coach → Phase 8
- ❌ "12 new" unread badge in sidebar → Phase 9
- ❌ Editable Preferences/Priorities as onboarding steps 6+7 → Phase 8 as Settings sub-page
- ❌ Custom company avatars → Phase 10+

The new session should treat these as final unless Bene explicitly opens them up.

---

**End of handoff.** The design is solid; the scope is settled; the gap analysis is documented. Plan well before coding.
