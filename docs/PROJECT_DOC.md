# Hired. — Local-First AI Career Agent

**Project Documentation v1.1** · first drafted 2026-04-23, revised 2026-07-20
Anna Vegera · Benedict Herrnleben · Eren Kocadag · Muhammad Kaleem Ullah

> Describes the shipped system as of **v0.5.0**. Where something was planned but
> not built, this document says so rather than describing the plan as if it were
> the product.

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
| Mock interview chatbot with feedback | ✅ | v0.3.0 → v0.5.0 | Delivered, then **extended well past the original goal** — see below |
| Rejection analysis | ⚠️ | v0.4.0 | Heuristic rather than a standalone report: companies/locations you repeatedly reject take −25 in scoring, positively-rated ones +25, and rejected titles/skills are injected into the grading prompt |
| Glassdoor / culture per job card | ❌ | — | |
| Multi-language CV and cover letter | ❌ | — | |
| Encrypted backup to user's own cloud | ❌ | — | |

### 2.2 Delivered Beyond the Original Scope

Work that was never in the plan and shipped anyway:

| Addition | Landed | Why it matters |
|---|---|---|
| **Voice mock interviews** — on-device Piper TTS + faster-whisper STT, timed runs, automatic scoring, audio-reactive interviewer avatar | v0.5.0 | An entire on-device speech subsystem; see §5 |
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

**Hired. is fundamentally a local-first desktop application.** There is no cloud backend operated by us. The user's machine is the entire system. Network calls leaving the device are limited to: (a) the LLM call to whichever provider the user configured — which for company research includes a server-side web search on the provider's side; (b) job-source crawls when triggered; and (c) a one-time download of the speech models from Hugging Face the first time voice is used.

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
| Crawler | httpx + BeautifulSoup (seven sources); Playwright for LinkedIn only | Job ingestion — paste-URL is the primary path |
| Job Scheduler | APScheduler (in-process) | Daily crawl trigger |
| Speech (TTS) | Piper — `en_US-amy-medium` / `en_US-ryan-medium` | On-device interviewer voice, one per gender |
| Speech (STT) | faster-whisper — `base` | On-device transcription of the candidate's spoken answer |

### LLM Provider Abstraction

All AI tasks go through a single Python interface:

```python
class LLMProvider(Protocol):
    # Profile & scoring
    def parse_cv(self, cv_text: str) -> CVData: ...
    def score_job(self, profile, job) -> ScoreResult: ...
    # Application materials
    def research_company(self, company: str) -> str: ...
    def tailor_cv(self, profile, job) -> CVSuggestions: ...
    def generate_cover_letter(self, profile, job, brief) -> str: ...
    def summarize_role(self, job) -> str: ...
    # Interview prep and coaching
    def generate_interview_questions(self, job) -> list[Question]: ...
    def evaluate_answer(self, question, answer) -> Feedback: ...
    def interview_chat_stream(self, messages) -> Iterator[str]: ...
    # Mock interviews
    def generate_mock_interview_questions(self, interview) -> list[Question]: ...
    def evaluate_mock_interview(self, transcript) -> MockInterviewResult: ...
```

Eleven methods, added over six phases. Every one is implemented by all five
adapters, which is what keeps provider switching a configuration change rather
than a code path.

Concrete implementations:

- **AnthropicAPIAdapter** — Anthropic Python SDK with a user-provided API key. The canonical path, and the only one billed per token.
- **ClaudeCodeAdapter** — invokes the `claude` CLI via subprocess; the user's Claude subscription handles billing.
- **CodexCLIAdapter** — invokes the `codex` CLI the same way against a ChatGPT subscription ([ADR-0010](adr/0010-codex-cli-provider.md)).
- **OllamaAdapter** — POSTs to a local Ollama HTTP endpoint; fully offline.
- **MockProvider** — deterministic stub, the default in tests, which is why 333 backend tests run with no network and no cost.

Switching providers is a single setting change in the UI; no app restart.

### Data Flow

**Provider Setup Flow:**
1. User opens app → onboarding wizard launches.
2. App scans PATH for the `claude` and `codex` CLIs, checks for a stored Anthropic key, and pings localhost:11434 to detect Ollama.
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
2. Pasted URLs are fetched directly, or an enabled source is crawled (Wellfound, Indeed, Remotive, StepStone; Greenhouse and Lever by board URL). LinkedIn uses Playwright and is the fragile path, not the default.
3. Jobs normalized and deduplicated.
4. New jobs scored via LLM provider.
5. Ranked feed appears in UI.

---

## 5. LLM Integration Strategy

### Provider Strategy

| Provider | Best for | Cost | Privacy | Status |
|---|---|---|---|---|
| Anthropic API | Users without a subscription | Pay-per-token | High | Canonical |
| Claude Code | Users with a Claude Pro/Max subscription | $0 extra | High | Experimental (R-01) |
| OpenAI Codex CLI | Users with a ChatGPT subscription | $0 extra | High | Experimental (R-01) |
| Ollama | Privacy-focused users with capable hardware | $0 | Maximum — nothing leaves the device | Supported |
| Mock | Tests and CI | $0 | N/A | Default in tests |

The two CLI providers exist because of the project's central premise: a user who
already pays for Claude or ChatGPT should not pay a second time to use this app.

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

- **Caching:** company research briefs are cached per company and reused across applications; the generation pipeline marks the step `cached` rather than re-calling the model (`services/application_service.py`).
- **Token caps per task:** each task has its own `max_tokens` ceiling, so a runaway generation cannot silently burn budget.
- **Cost tracking:** token spend for today and the past week, with per-provider attribution, in the Settings panel. Meaningful in API mode; the CLI and Ollama paths report calls and latency instead, since neither bills per token.
- **Latency-aware UI:** loading states are written per provider, because a 10-second API call and a 90-second Ollama call need different affordances.

### Safety

- Prompt injection mitigation: CV text is treated as untrusted input — wrapped in delimiters, with the system prompt instructed to ignore instructions inside it, and structured output validated (`backend/prompts/parse_cv.md`).
- API key storage: OS keychain via `backend/llm/credentials.py` (Keychain / Credential Manager / Secret Service). Keys are never written to the database or config file.
- Local-only data: nothing is transmitted except the prompt for a single call.
- **Not built:** automatic PII redaction in log output. Logs stay on the user's machine and are not collected, which lowers the exposure, but a redaction helper was planned and never implemented.

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
| Distribution | Runtimes are bundled into the sidecar as of v0.5.0; the *models* still download on first use into `~/.hired/models/`, so the feature is offline after one download. Bundling the runtimes grew installers roughly 3–4x — the deliberate trade |
| Degradation | `faster_whisper` and `piper` are imported lazily; if absent — an unbundled build, or a stripped install — `voice_status` reports `deps_available=False` and the UI falls back to text mode rather than erroring |
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

**Onboarding Wizard**: Four provider cards — Anthropic API, Claude Code, OpenAI Codex, Ollama — with auto-detection, experimental badges on the two CLI options, and install links for what is missing.

**Loading States**: Adapt to expected latency:
- Anthropic API: 5–15s, "~10 seconds"
- Claude Code / OpenAI Codex: 10–30s, "~20 seconds, via your subscription"
- Ollama: 20–90s, progress bar, Cancel button

**Settings & Footer**: Active provider always visible with status, latency, usage. Cost tracking only meaningful in API mode.

### Accessibility

- Keyboard navigation throughout, including dashboard rows that were previously mouse-only.
- WCAG AA colour contrast on the shipped palette.
- Screen-reader labels; `aria-live` on loading regions and `role="alert"` on inline errors.
- Audited manually against the source in Phase 6, with findings and fixes recorded in `docs/accessibility-audit.md`. That audit is explicit about its limits: no live `axe-core` run and no screen-reader testing were performed.

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
- Job crawling reads only public listing pages, and only when the user triggers a crawl or enables a scheduled source.
- Uninstall removes 100% of user data.

### Bias

LLMs show measurable bias in hiring tasks. We measure and mitigate:

- Transparent rationale on every score — a score never appears without its reasoning.
- A name-swap bias audit ships in `eval/bias_audit.py` and runs via `make bias-audit`.
- **Not built:** optional CV anonymization before scoring. It was planned (risk R-06) and remains the intended mitigation, but no anonymization path exists in the code today.
- **Not yet run:** the bias audit has only been exercised against `MockProvider`, so no real variance figure has been recorded.

### Transparency & User Control

- Every output shown to user before any external use.
- No auto-apply, no auto-send.
- Match score never appears without rationale.
- Permanent local data deletion in one click.

---

## 8. External Services

| Service | Role | Tier |
|---|---|---|
| Anthropic API | LLM provider (canonical path) | Pay-per-token |
| Anthropic Claude Code CLI | LLM provider via the user's own subscription | User's subscription |
| OpenAI Codex CLI | LLM provider via the user's own subscription | User's subscription |
| Ollama | LLM provider, fully local | Free, runs locally |
| Anthropic web-search tool | Grounds company research in live sources | Billed with the call |
| Hugging Face | One-time download of Piper voice models | Free |
| Job sources (public pages) | Wellfound, Indeed, Remotive, StepStone, Greenhouse, Lever, LinkedIn | Free |
| GitHub | Source hosting, CI, releases | Free |

No Supabase, Redis, Vercel, Railway, Apify, or Pinecone in this architecture.

**Not integrated:** earlier drafts listed Sentry for error tracking. It was never
wired up — there is no Sentry dependency or DSN in the codebase, and errors are
surfaced locally through the typed `LLMError` hierarchy and the provider-stats
panel instead.

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

### 9.1 What Actually Happened

The eight-week plan covered the MVP, and the MVP landed roughly on it. Work then
continued past the plan for three more phases, so the honest record is:

| Release | Date | Contents |
|---|---|---|
| v0.1.1 | 2026-05-17 | MVP feature-complete — Phases 1–6, the whole eight-week plan |
| v0.2.0 | 2026-05-19 | Phase 7 — frontend redesign, design system, Kanban |
| v0.3.0 | 2026-05-21 | Phase 8 — streaming interview coach, editable preferences |
| v0.3.1–v0.3.5 | 2026-05-21 | Release-candidate smoke fixes |
| v0.3.6 | 2026-05-31 | OpenAI Codex CLI provider (ADR-0010) |
| v0.3.7 | 2026-05-31 | Web-search-backed company research |
| v0.3.8 | 2026-06-07 | Application-detail layout |
| v0.4.0 | 2026-06-14 | Phase 9 — feedback loop. **Never tagged**, so no installer exists |
| v0.4.1 | 2026-07-19 | First published build carrying Phase 9 and multi-source crawling |
| v0.5.0 | 2026-07-20 | Voice bundled into installers; company/title parser fixes |

Two deviations worth naming rather than hiding:

- **No v1.0.0 was released.** The plan called for one in week 8. Versioning
  stayed in `0.x` because the crawler remains fragile by design (ADR-0006) and
  we did not want a `1.0` to imply a stability we had not earned.
- **v0.4.0 was written up but never tagged.** The changelog entry existed for
  five weeks before anyone noticed no installer had been produced — caught
  during a documentation audit, and the reason `v0.4.1` exists.

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

Targets were set at the start of the project. The result column records what was
actually measured — including where it was not.

| Metric | Target | Result |
|---|---|---|
| Match relevance | ≥75% precision@5 on 20-pair goldset | **Not measured.** The harness (`eval/run_eval.py`) and a 20-entry goldset exist and run, but only ever against `MockProvider`, so the numbers are structural rather than real |
| Cover letter latency (Claude Code) | ≤20s end-to-end | Not systematically measured; per-call latency is recorded and shown in the provider-stats panel |
| Cover letter latency (Ollama, qwen2.5:14b) | ≤60s end-to-end | Not systematically measured |
| Test coverage | ≥80% | **Partly met.** 333 backend tests and 149 frontend tests pass. Backend source-only line coverage is ~75%; the frontend has no coverage tooling configured |
| Cross-platform build | 100% on Mac/Win/Linux | **Met.** The v0.5.0 gate built installers on all three platforms; the packaged Windows sidecar was launched and verified to report voice available |
| Usability (SUS score) | ≥70 | **Not measured.** No usability study was run |
| Bias variance | <10pt on name-swap test | **Not measured.** `eval/bias_audit.py` implements the name-swap audit but has only run against `MockProvider` |

Recording the unmeasured rows honestly is deliberate. The evaluation harness is
real and reusable; what is missing is a run against a live provider, which is
the first thing to do if this project continues.

### Demo Script

- 00:00 — Open installed app; local-first pitch (30s)
- 00:30 — Onboarding wizard, provider auto-detection (1 min)
- 01:30 — Upload CV, set priorities (1 min)
- 02:30 — Ranked job feed with match scores; thumb one down to show the feedback loop (1 min)
- 03:30 — Generate cover letter live, edit (1.5 min)
- 05:00 — Application dashboard (30s)
- 05:30 — **Voice mock interview** — the interviewer speaks, answer out loud, show the transcript and scored feedback (1 min)
- 06:30 — Closing + Q&A

### Presentation & Demo Assets

Produced and available; not stored in the repository because of file size.

| Asset | Location |
|---|---|
| Final presentation video | `presentation/final/final_presentation.mp4` |
| Feature walkthroughs | `presentation/final/` — on-device desktop app + unified LLM layer; the on-device voice stack |
| Mid-term video | `presentation/mid-term/` — full, short, and per-section cuts |
| Slide decks | `presentation/` — pitch deck, mid-term deck, speaker scripts |
| Speaking scripts (in repo) | `docs/midterm-presentation-script.md`, `docs/slide-speaking-scripts.md` |

### Backup Plan

- Pre-recorded demo video — **done**, see above, so a live-demo failure costs nothing.
- Static screenshot deck as a second fallback.
- Test run on the presentation laptop the day before.
- Seed the demo database in advance so no step depends on a live LLM call completing on time.

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