# Hired. — Local-First AI Career Agent

**Project Documentation v1.0** · 2026-04-23
Anna Vegera · Benedict Herrnleben · Eren Kocadag · Muhammad Kaleem Ullah

---

## 1. Problem Statement & Vision

### The Problem

Job hunting is broken. Candidates send 50–100 applications, get ghosted, and burn out. Recruiters already use AI to filter CVs — so candidates without AI tools are at a structural disadvantage. At the same time, existing AI career tools force users into one of two bad trade-offs:

- Pay extra: monthly subscriptions on top of the Claude Pro / ChatGPT Plus subscriptions users already have.
- Give up data: upload CVs, application history, and personal preferences to opaque third-party clouds.

### Our Vision

**Hired. is a local-first career agent that runs on the user's machine and uses the AI subscription they already pay for.** The user's CV never leaves their device. Their applications stay theirs. The AI runs through their existing Claude Pro / Claude Max subscription via Claude Code — no extra costs, no data exposure. Users without a subscription can plug in an Anthropic API key, and privacy-focused users can run a fully local model via Ollama.

### Why Now?

- LLMs are finally good enough: Claude can read a CV, match it to a job, write a real cover letter, and run a useful mock interview.
- Local-first AI is feasible: Claude Code, Ollama, and similar tools mean inference can happen without us operating a cloud backend.
- Subscription fatigue is real: users already pay for Claude or ChatGPT and don't want yet another AI bill.

### Stakeholders

We are the primary stakeholders. We are job hunting ourselves and need this tool. The secondary stakeholder group is early-career applicants — students and graduates who already pay for an AI subscription and want AI career support without paying twice.

### Target Users

- Computer science students and tech-adjacent early-career applicants who already use Claude or ChatGPT.
- Privacy-conscious applicants who do not want their CV on a third-party server.
- Anyone with an existing Claude Pro/Max subscription who wants to maximize its value.

### Success Criteria

- We use Hired. ourselves for our own job search this semester.
- A user with Claude Pro can run the full workflow end-to-end at zero additional cost.
- Generated cover letters and match scores feel meaningfully better than what generic prompting produces.

---

## 2. Scope

### Must-Have (MVP)

The core local-first loop that must work at launch:

- **Local installation**: installable desktop app (Tauri) for macOS, Windows, and Linux.
- **AI provider setup**: onboarding wizard to connect Claude Code, Ollama, or an Anthropic API key.
- **Profile setup**: CV upload + onboarding questionnaire (target role, salary, location, priorities); all data stored locally in SQLite.
- **Job ingestion**: manual + scheduled crawler pulling listings from LinkedIn (user-triggered to respect rate limits).
- **First screening**: one-page job summary with apply / save / skip actions.
- **Application material generation**: tailored CV highlights, cover letter, and company research brief.
- **Interview preparation**: role-specific question bank + company info + role explanation.
- **Application dashboard**: table view of all applications with status tracking.

### Nice-to-Have

- AI match scoring & ranked feed (0–100 score per job with rationale).
- Salary benchmark data pulled per role and location.
- Kanban dashboard as alternative view (Discovered → Applied → Interview → Offer → Rejected).
- Easy provider switching between Claude Code, Ollama, and API key.
- Export to PDF for cover letters and CV variants.

### Stretch Goals

- Mock interview chatbot with structured feedback. **Delivered, and extended:
  interviews also run in voice mode with on-device speech (see §5) and an
  audio-reactive interviewer avatar.**
- Rejection analysis — pattern detection over rejected applications.
- Glassdoor / company culture info per job card.
- Multi-language CV and cover letter generation.
- Encrypted backup to user's own cloud (Dropbox/iCloud) — fully optional.

### Explicitly Out of Scope

- Web/mobile version. This is intentionally local-first.
- Recruiter / employer side. Completely separate product.
- Paid subscriptions or monetization.
- Cloud sync between devices.
- Auto-application submission to ATS portals.
- Social features.

### 2.1 Delivered vs. Planned

Status of every scope item above, verified against the code rather than the
plan. ✅ delivered · ⚠️ delivered with a documented change of shape · ❌ not built.

**Must-have (MVP) — 8/8 delivered**

| Item | Status | Landed | Notes |
|---|---|---|---|
| Local installation (macOS/Windows/Linux) | ✅ | v0.1.1 | Tauri + PyInstaller sidecar, 3-OS CI matrix |
| AI provider setup wizard | ✅ | v0.1.1 | Extended to five providers (see below) |
| Profile setup (CV upload + questionnaire) | ✅ | v0.1.1 | Local SQLite only |
| Job ingestion | ⚠️ | v0.1.1 | Paste-URL is the primary path; LinkedIn scraping is fragile by design — [ADR-0006](adr/0006-crawler-fragility.md) |
| First screening (summary + apply/save/skip) | ✅ | v0.1.1 | |
| Application materials (brief, CV tailoring, cover letter) | ✅ | v0.1.1 | |
| Interview preparation | ✅ | v0.1.1 | Question bank + company info + role summary |
| Application dashboard | ✅ | v0.1.1 → v0.2.0 | Table, then five-column Kanban in Phase 7 |

**Nice-to-have — 4/5 delivered**

| Item | Status | Landed | Notes |
|---|---|---|---|
| AI match scoring & ranked feed | ✅ | v0.1.1 | 0–100 with rationale |
| Kanban dashboard | ✅ | v0.2.0 | |
| Provider switching without restart | ✅ | v0.1.1 | |
| PDF export (cover letter + CV) | ✅ | — | `frontend/src/lib/pdf.ts` |
| Salary benchmark per role/location | ❌ | — | Salary shown when the listing carries it; no benchmark lookup was built |

**Stretch goals — 1 delivered and extended, 1 partial, 3 not built**

| Item | Status | Landed | Notes |
|---|---|---|---|
| Mock interview chatbot with feedback | ✅ | v0.3.0 → unreleased | Delivered, then **extended well past the original goal** — see below |
| Rejection analysis | ⚠️ | v0.4.0 | Heuristic rather than a standalone report: companies/locations you repeatedly reject take −25 in scoring, positively-rated ones +25, and rejected titles/skills are injected into the grading prompt |
| Glassdoor / culture per job card | ❌ | — | |
| Multi-language CV and cover letter | ❌ | — | |
| Encrypted backup to user's own cloud | ❌ | — | |

### 2.2 Delivered Beyond the Original Scope

Work that was never in the plan and shipped anyway:

| Addition | Landed | Why it matters |
|---|---|---|
| **Voice mock interviews** — on-device Piper TTS + faster-whisper STT, timed runs, automatic scoring, audio-reactive interviewer avatar | unreleased | An entire on-device speech subsystem; see §5 |
| **Feedback loop** — thumbs up/down with reasons, `JobInteraction` tracking, feedback injected into the scoring prompt, unread badges | v0.4.0 | Phase 9; closes the learning loop the user stories asked for |
| **Scheduled multi-source crawling** — seven crawler modules (Wellfound, Indeed, Remotive, StepStone, Greenhouse, Lever, LinkedIn); four exposed as schedulable sources with per-source config | v0.4.0 | Reduces reliance on the single fragile LinkedIn path |
| **OpenAI Codex CLI** as a fifth provider | v0.3.6 | [ADR-0010](adr/0010-codex-cli-provider.md) |
| **Streaming interview coach** | v0.3.0 | All adapters stream; Phase 8 |
| **Cost & provider-stats panel** | v0.3.x | Token spend and latency per provider |
| **Web-search-backed company research** | v0.3.7 | Grounds the brief in live sources |

> **Release status.** Shipped in **v0.5.0**, which is the first installer to
> contain the mock-interview work with voice enabled. Voice runtimes (Piper +
> faster-whisper) are bundled into the sidecar; the speech *models* are still
> downloaded on first use into `~/.hired/models/`, so the first voice interview
> needs a one-time download and everything after it runs offline. Installers are
> correspondingly larger — that is the deliberate trade.

---

## 3. User Stories

### Setup & AI Provider

- As a Claude Pro user, I want to connect my existing Claude Code installation, so I don't have to pay for API tokens.
- As a privacy-focused user, I want to run a local Ollama model, so my data never leaves my machine.
- As a user without a subscription, I want to plug in an API key, so I can use the app pay-as-you-go.
- As a new user, I want a setup wizard that detects what AI providers I already have installed.

### Profile

- As a recent graduate, I want my CV parsed automatically on upload.
- As a job seeker, I want salary and location preferences saved locally.
- As a career changer, I want to set a target industry that differs from my CV history.

### Job Discovery

- As a student, I want a ranked list of relevant jobs after each crawl.
- As a busy applicant, I want each job card to show a match score with a 2-sentence explanation.
- As a user, I want to thumb-down irrelevant jobs, so the system learns my preferences.

### Application Materials

- As an applicant, I want a tailored cover letter for each job.
- As a job seeker, I want a one-page company brief for each role.
- As an applicant, I want all generated materials editable before use.

### Interview Prep

- As a candidate, I want a list of likely interview questions tailored to the job description.

### Tracking

- As an active applicant, I want a dashboard of all open applications.
- As a privacy-conscious user, I want all application data stored locally only.

---

## 4. System Overview

### Architectural Philosophy

**Hired. is fundamentally a local-first desktop application.** There is no cloud backend operated by us. The user's machine is the entire system. The only network calls leaving the device are (a) the LLM call to whichever provider the user configured, and (b) the LinkedIn crawl when triggered.

### Architecture Layers

The app consists of four logical layers, all running locally:

- **Desktop Shell (Tauri)**: cross-platform window, native APIs, app distribution. Built on Rust + system WebView.
- **Frontend (React + TypeScript + Tailwind)**: all UI — onboarding wizard, job feed, application dashboard, cover letter editor, interview prep.
- **Backend Service (FastAPI sidecar)**: local Python service launched by Tauri as a child process. Handles business logic, LLM routing, crawling, DB access.
- **Data Layer (SQLite)**: a single local DB file in the user's app-data directory.

Communication: Frontend talks to Backend via Tauri IPC + local HTTP. Backend talks to LLM Provider via the LLMProvider interface (see Section 5).

### Key Components

| Component | Technology | Responsibility |
|---|---|---|
| Desktop Shell | Tauri 2.x (Rust) | Cross-platform window, native APIs, distribution |
| Frontend | React 18 + TypeScript + Tailwind + shadcn/ui | All UI |
| Backend Service | FastAPI (Python 3.11) as Tauri sidecar | REST API, business logic, LLM routing |
| Local DB | SQLite (via SQLAlchemy) | All persistent data |
| LLM Router | Custom Python abstraction | Routes AI calls based on user config |
| Claude Code Adapter | Subprocess wrapper around `claude` CLI | Uses user's Claude subscription |
| Ollama Adapter | HTTP client to localhost:11434 | Local model |
| API Key Adapter | Anthropic Python SDK | Pay-as-you-go fallback |
| Crawler | Playwright (Python) | LinkedIn job ingestion |
| Job Scheduler | APScheduler (in-process) | Daily crawl trigger |
| Speech (TTS) | Piper — `en_US-amy-medium` / `en_US-ryan-medium` | On-device interviewer voice, one per gender |
| Speech (STT) | faster-whisper — `base` | On-device transcription of the candidate's spoken answer |

### LLM Provider Abstraction

All AI tasks go through a single Python interface:

```python
class LLMProvider(Protocol):
    def parse_cv(self, cv_text: str) -> CVData: ...
    def score_job(self, profile, job) -> ScoreResult: ...
    def generate_cover_letter(self, profile, job, brief) -> str: ...
    def research_company(self, company: str) -> str: ...
    def generate_interview_questions(self, job) -> List[Question]: ...
    def evaluate_answer(self, question, answer) -> Feedback: ...
```

Concrete implementations:

- **ClaudeCodeAdapter** — invokes `claude` CLI via subprocess; user's Claude subscription handles billing.
- **OllamaAdapter** — POSTs to local Ollama HTTP endpoint.
- **AnthropicAPIAdapter** — uses Anthropic Python SDK with user-provided API key.
- **MockProvider** — deterministic stub used in CI tests.

Switching providers is a single setting change in the UI; no app restart.

### Data Flow

**Provider Setup Flow:**
1. User opens app → onboarding wizard launches.
2. App scans for `claude` CLI in PATH and pings localhost:11434 to detect Ollama.
3. Wizard shows detected providers.
4. User picks one; adapter config written to local config file.
5. Test call validates the adapter.

**Application Material Generation Flow:**
1. User clicks "Apply" on a job in the local UI.
2. Backend reads job + profile from SQLite.
3. LLMProvider called via configured adapter.
4. Three sequential calls: company research → CV tailoring → cover letter.
5. Outputs written to local SQLite.
6. User reviews and edits before using.

**Job Discovery Flow:**
1. User triggers crawl manually OR daily scheduler fires.
2. Playwright fetches LinkedIn listings.
3. Jobs normalized and deduplicated.
4. New jobs scored via LLM provider.
5. Ranked feed appears in UI.

---

## 5. LLM Integration Strategy

### Provider Strategy

| Provider | Best for | Cost | Privacy |
|---|---|---|---|
| Claude Code | Users with Pro/Max subscription | $0 extra | High |
| Ollama | Privacy-focused with capable hardware | $0 | Maximum |
| API Key | Users without subscriptions | Pay-per-token | High |

### Important: Claude Code Subscription Use

Claude Code is officially designed as a coding agent tool. Using it as a programmatic backend for a third-party app sits in a documented gray zone. Our position:

- The user always installs and configures Claude Code themselves.
- Hired. invokes the user's local CLI on the user's own machine.
- We never centralize, proxy, or rate-limit-bypass.
- Clear notice in setup about ToS implications.
- Claude Code labeled "Experimental" in the UI; API-key path is canonical.

This is documented as Risk R-01.

### Prompting Strategy

- All prompts in `/backend/prompts/` as versioned `.md` files.
- Each task has a system prompt + user prompt template.
- Structured outputs via JSON Schema where applicable.
- Few-shot examples for ambiguous tasks.
- Provider-specific overrides allowed but minimized.

### Grounding & Hallucination Mitigation

- CV data and job descriptions always provided in context — never relied on from model memory.
- Company research includes source attribution.
- Edit-first workflow — every generated artifact opens in an editor.
- No autonomous external actions.

### Cost & Performance

- Caching: company research briefs cached per company.
- Token caps per task.
- Cost display in API mode.
- Latency-aware UI loading states.

### Safety

- Prompt injection mitigation: CV uploads sanitized, wrapped in delimiters, structured output validated.
- API key storage: OS keychain (Keychain/Credential Manager/Secret Service).
- PII redacted from logs.

### On-Device Speech (Voice Mock Interviews)

The mock interview can run in voice mode: the interviewer speaks, the candidate
answers out loud, and the answer is transcribed and evaluated. **No audio ever
leaves the machine** — both models run locally, which is the same constraint
that drives the rest of the architecture applied to a modality where cloud APIs
are the default.

| Concern | Decision |
|---|---|
| TTS | Piper, `en_US-amy-medium` / `en_US-ryan-medium` — one voice per interviewer gender |
| STT | faster-whisper, `base` — smallest model that transcribes interview answers reliably |
| Distribution | Models download on first use into `~/.hired/models/`, not bundled — keeps the installer lean and the feature offline afterwards |
| Degradation | `faster_whisper` and `piper` are imported lazily; if absent, `voice_status` reports `deps_available=False` and the UI hides voice rather than erroring |
| Setup UX | `GET /api/voice/status` reports what is missing so the app can offer a one-time "Set up voice" step with download progress |
| Input cap | Audio uploads limited to 25 MB per answer |

The interviewer avatar is audio-reactive (speaking/listening states per gender).
It is **not** a deepfake: the original brief floated a synthesized-video
recruiter and simultaneously listed deepfaked mock interviews as out of scope.
What shipped is static photography driven by real audio amplitude.

### Evaluation

- Goldset: 20 manually labeled CV/job pairs.
- Continuous metrics: thumbs-down rate, user-edit ratio of cover letters.
- Bias audit: scoring delta when CV name/pronouns swapped.

---

## 6. UI/UX Design

### Design Philosophy

The UI is provider-agnostic in the workflow and provider-aware in setup, status, and timing. ~95% of the app looks identical across providers. The remaining ~5% — onboarding, settings, footer status, loading states — is intentionally provider-aware.

### Provider-Agnostic Screens (95%)

- CV upload and profile setup.
- Job feed.
- Application dashboard.
- Cover letter editor.
- Interview prep.

### Provider-Aware Screens

**Onboarding Wizard**: Three provider cards with auto-detection, recommendation/experimental badges, install links.

**Loading States**: Adapt to expected latency:
- Anthropic API: 5–15s, "~10 seconds"
- Claude Code: 10–30s, "~20 seconds, via your subscription"
- Ollama: 20–90s, progress bar, Cancel button

**Settings & Footer**: Active provider always visible with status, latency, usage. Cost tracking only meaningful in API mode.

### Accessibility

- Keyboard navigation throughout.
- WCAG AA color contrast.
- Screen-reader labels.
- aria-live for loading states.

### Responsive Design

Desktop only (≥1024px width). Resizable down to 800x600. No mobile responsiveness.

---

## 7. Ethics, Privacy & Bias

### Privacy

- All user data lives in `~/.hired/data.db`. No cloud component operated by us.
- Only the specific prompt + context for a single LLM call leaves the device.
- **Voice is fully on-device.** Recorded answers are transcribed by a local
  faster-whisper model and synthesized by local Piper voices; no audio is ever
  uploaded. Speech models are cached in `~/.hired/models/` after first download.
- LinkedIn crawl: only public listing data fetched.
- Uninstall removes 100% of user data.

### Bias

LLMs show measurable bias in hiring tasks. We measure and mitigate:

- Optional CV anonymization for scoring.
- Transparent rationale on every score.
- Bias audit on goldset.

### Transparency & User Control

- Every output shown to user before any external use.
- No auto-apply, no auto-send.
- Match score never appears without rationale.
- Permanent local data deletion in one click.

---

## 8. External Services

| Service | Role | Tier |
|---|---|---|
| Anthropic Claude Code CLI | Default LLM provider option | User's subscription |
| Ollama | Local LLM provider option | Free, runs locally |
| Anthropic API | Fallback LLM provider | Pay-per-token |
| LinkedIn (public) | Job source | Free |
| GitHub | Source + releases | Free |
| Sentry (opt-in) | Error tracking | Free tier |

No Supabase, Redis, Vercel, Railway, or Apify in this architecture.

---

## 9. Project Plan

8-week plan. W1–2 = local foundation; W3–6 = feature delivery; W7–8 = polish and packaging.

| Week | Milestone |
|---|---|
| 1 | Repo, CI, Tauri shell, FastAPI skeleton |
| 2 | LLM Provider abstraction + MockProvider + AnthropicAPIAdapter |
| 3 | CV upload, profile setup, onboarding wizard |
| 4 | LinkedIn crawler + job scoring + ranked feed (first end-to-end demo) |
| 5 | Application material generation + dashboard |
| 6 | Interview prep + ClaudeCodeAdapter + OllamaAdapter (MVP complete) |
| 7 | Cross-platform packaging, accessibility, polish |
| 8 | Final release v1.0 |

### Decision-Making

- ADRs in `/docs/adr/`.
- Weekly 30-min sync; blockers resolved by majority.
- Features slipping >3 days → discussed in next sync.
- All scope changes in CHANGELOG.md.

---

## 10. Roles & Responsibilities

| Role | Person | Duties |
|---|---|---|
| Project Lead + Architect (AI/Backend) | Anna Vegera + Benedict Herrnleben | System architecture, ADRs, LLM provider design, prompt engineering, sprint planning |
| Frontend Engineer + UX Lead | Eren Kocadag | Tauri/React UI, design system, UX flows and wireframes, onboarding, feed, Kanban, interview-prep screens |
| AI Engineer + Integration (primary) | Muhammad Kaleem Ullah | On-device speech stack (Piper TTS + faster-whisper STT), voice mock-interview pipeline, model selection and download/caching strategy, CV parsing and generation prompts, eval harness |
| Backend Engineer (supporting) | Muhammad Kaleem Ullah | FastAPI endpoints, DB schema and migrations, packaging, CI/CD |

Contribution is not measured by commit count. Substantial parts of this project
never took the form of a commit — the Phase 7 design system (`design/Hred.v2/`
plus a 33 KB handoff document), the slide decks, and the mid-term and final
demo videos are all team output that lives outside the git history.

### Shared Responsibilities

- Tests for your modules (≥80% coverage).
- Review one PR per week.
- Update GitHub project board.
- Document your module.
- Attend weekly sync.

---

## 11. Risk Register

| ID | Risk | Prob. | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Anthropic ToS gray zone for Claude Code as backend | Medium | High | Document clearly, user installs CLI themselves, API-key fallback |
| R-02 | LinkedIn blocks crawler from user IPs | High | High | Manual user-triggered crawls, randomized delays, fallback to pasted URLs |
| R-03 | Cross-platform packaging issues | High | Medium | Start packaging tests in W1; document per OS |
| R-04 | Claude Code CLI behavior changes | Medium | High | Pin version; integration tests; abstract behind adapter |
| R-05 | LLM hallucinates company facts | High | Medium | Source attribution; user reviews before use |
| R-06 | Bias in scoring | Medium | High | Bias audit; CV anonymization mode |
| R-07 | Ollama model quality too low | High | Medium | Document min model recommendation; capability warning |
| R-08 | Team member unavailable | Medium | Medium | Pair coding; documentation requirements |
| R-09 | Scope creep from stretch goals | High | Medium | MVP-only until W6 |
| R-10 | GDPR concerns | Low | Medium | Privacy-by-design (local-only) |
| R-11 | macOS code-signing without Developer ID | Medium | Medium | Investigate Apple Developer ID early; fallback install docs |

---

## 12. Evaluation & Demo

### Success Metrics

| Metric | Target |
|---|---|
| Match relevance | ≥75% precision@5 on 20-pair goldset |
| Cover letter latency (Claude Code) | ≤20s end-to-end |
| Cover letter latency (Ollama, qwen2.5:14b) | ≤60s end-to-end |
| Test coverage | ≥80% |
| Cross-platform install success | 100% on Mac/Win/Linux |
| Usability (SUS score) | ≥70 |
| Bias variance | <10pt on name-swap test |

### Demo Script

- 00:00 — Open installed app; local-first pitch (30s)
- 00:30 — Onboarding wizard, provider auto-detection (1 min)
- 01:30 — Upload CV, set priorities (1 min)
- 02:30 — Ranked job feed with match scores (1 min)
- 03:30 — Generate cover letter live, edit (1.5 min)
- 05:00 — Application dashboard (30s)
- 05:30 — Interview prep with feedback (30s)
- 06:00 — Closing + Q&A

### Backup Plan

- Pre-recorded demo video.
- Static screenshot deck.
- Test run on presentation laptop the day before.

---

## 13. Appendices

- **A.** Design system & wireframes — `/design/Hred.v2/Hired.html` (interactive
  reference build) and `/design/HANDOFF_PHASE_7_FRONTEND_REDESIGN.md`
- **B.** ADR Index — `/docs/adr/README.md`
- **C.** API Reference — `/docs/api.md`, with the machine-readable OpenAPI 3.1
  schema (50 paths) at `/docs/api.openapi.json`
- **D.** Prompt Library — `/backend/prompts/`
- **E.** Goldset for Evaluation — `/eval/goldset.json`
- **F.** Install & Distribution Guides — `/docs/install/` (per-OS: macOS,
  Windows, Linux); build-from-source steps in `/README.md`
- **G.** Presentation & Demo — see §12