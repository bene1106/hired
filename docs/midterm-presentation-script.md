# Hired. — Midterm Presentation Script
**Format:** 5-minute recorded video + ~2-min live Q&A on June 4  
**Deadline:** June 3, 23:59

---

## TIMING GUIDE

| Section | Target | Cumulative |
|---|---|---|
| Problem & User | 0:30 | 0:30 |
| Live Demo | 2:30 | 3:00 |
| Architecture / LLM | 1:00 | 4:00 |
| Lessons Learned & Next Steps | 1:00 | 5:00 |

---

## SECTION 1 — THE PROBLEM & YOUR USER (0:00–0:30)

> *Start screen-recording. Camera overlay on. Jump straight in — no title card.*

---

**[SPEAKER — casual, direct]**

"Imagine you're a CS student, you already pay for Claude Pro, and you're applying for jobs. You're sending out 50 applications, writing cover letters by hand, losing track of which company you even applied to — and meanwhile, recruiters are already filtering your CV with AI.

That's the gap Hired. fills. It's a desktop app that runs entirely on your machine — your CV never leaves your device — and it uses the AI subscription you *already* pay for. No extra bill. No cloud we operate. Just a local career agent that does the grunt work for you."

---

## SECTION 2 — LIVE DEMO (0:30–3:00)

> *The demo IS the presentation. Walk at a calm pace. Narrate what you're doing, not what the button says.*

### 2a. Onboarding & Provider Setup (0:30–1:00)

**[Open the installed Hired. app — not the dev server. Show it launching natively.]**

"When you first open Hired., it detects what AI you already have installed — here it found my Anthropic API key and the Claude Code CLI. I'll pick the API adapter for this demo so you can see the speeds.

[Click through the provider step — show the badge, the test-call passing]

The setup takes about 30 seconds. That's it."

---

### 2b. Profile — CV Upload (1:00–1:25)

**[Navigate to CV upload step in onboarding or Settings → Edit Profile]**

"Now I drop in my CV as a PDF. The backend parses it — name, experience, skills — and stores everything locally in SQLite. Nothing goes anywhere except the single parse call to the LLM.

[Watch the parse complete — show the filled-in profile card]

I can edit any field before saving."

---

### 2c. Job Discovery — Paste a URL, Get a Score (1:25–2:00)

**[Navigate to the Feed / Crawl panel]**

"Here's how job discovery works. I paste a job listing URL — let's use a real software engineering role — and hit Crawl.

[Paste URL, trigger crawl, watch progress bar]

The backend fetches the page, extracts the job data, then runs it through the LLM scorer against my profile. In about 10 seconds I get a match score — 82 out of 100 — with a two-sentence rationale: which skills match, what's missing.

[Show the job card with green score badge and skill chips]

I can Save it, Skip it, or go straight to Apply."

---

### 2d. Application Material Generation (2:00–2:40)

**[Click Apply on the job card]**

"This is the core of the app. I click Apply and the backend runs three sequential LLM calls: first it researches the company, then tailors my CV highlights to this specific role, then writes a cover letter.

[Watch the progress steps appear — research → tailor → cover letter]

I can watch each step land in real time. And the cover letter opens right here in an editable split view — markdown on the left, preview on the right. I can tweak it before I ever send it. Nothing auto-submits anywhere.

[Edit one line of the cover letter]

When I'm happy, I hit 'Mark applied' and it lands in the dashboard."

---

### 2e. Dashboard + Interview Prep (2:40–3:00)

**[Switch to Dashboard, then briefly to Interview Prep]**

"The dashboard shows every application with a filterable status column — Applied, Interview, Offer, Rejected.

[Click into an application → Interview Prep tab]

And if I get an interview, I open the Interview Prep tab. It generates role-specific questions grouped by category, I can practice answers, and the interactive coach gives me streamed feedback in real time — like a chat with an interviewer."

---

## SECTION 3 — ARCHITECTURE & LLM INTEGRATION (3:00–4:00)

> *Switch to the architecture diagram slide. Keep camera overlay on.*

---

**[Show the architecture diagram — see below for the visual]**

"The architecture is four layers, all local.

The **Tauri shell** is the native desktop window — Rust under the hood, cross-platform. It launches a **FastAPI sidecar** as a child process — that's our Python backend handling all the business logic. The frontend is React talking to that local HTTP service. And all persistent data lives in a single **SQLite file** on the user's machine.

The key design decision is the **LLMProvider interface** — one Python Protocol that every AI task goes through. Behind it we have four concrete adapters: the Anthropic API, Claude Code CLI, Ollama for fully local inference, and a new OpenAI Codex CLI adapter we just shipped. Switching providers is a single setting, no restart.

For prompting: every prompt lives as a versioned markdown file in `/backend/prompts/`. We use structured JSON output for scoring, few-shot examples for the cover letter, and every generated artifact is grounded in the actual CV and job description — never from model memory. The user reviews everything before it's used."

---

## SECTION 4 — LESSONS LEARNED & NEXT STEPS (4:00–5:00)

---

**[Back to screen or just camera]**

"Three things that surprised us.

**First — LinkedIn is basically unscrappable.** We built a Playwright crawler, it worked for two days, then LinkedIn changed their DOM and rate-limited us. Our fix: make manual URL paste the primary path, with LinkedIn as a clearly-labeled experimental option. Honest about the limitation, still useful.

**Second — the LLM abstraction paid off immediately.** When we added the Ollama adapter in Phase 6 and the Codex adapter in the last sprint, we touched zero business logic. Just a new file, a few tests, done. The interface investment from Week 2 kept every later addition clean.

**Third — SQLite is genuinely enough.** We debated Postgres early on. We never needed it. One file, zero ops overhead, instant uninstall.

**For the final stretch:** we want to add a bias audit toggle — CV anonymization before scoring — since we know LLMs show measurable bias in hiring tasks. We also want to land cross-platform packaging properly, get the Tauri installers signed so users don't have to click through Gatekeeper warnings, and do a real usability test with people who aren't us.

The app is live, the core loop works end-to-end, and we're using it ourselves for our own job search this semester — which is the success criterion we wrote on day one."

---

> *Stop recording.*

---

## ARCHITECTURE DIAGRAM (for slide)

Use this as your one diagram — paste into Keynote/PowerPoint/Canva or render it:

```
┌─────────────────────────────────────────────────────────────────┐
│                        User's Machine                           │
│                                                                 │
│  ┌──────────────┐   IPC + HTTP   ┌──────────────────────────┐  │
│  │  Tauri Shell │◄──────────────►│   FastAPI Sidecar        │  │
│  │  (Rust)      │                │   (Python 3.11)          │  │
│  │              │                │                          │  │
│  │  React UI    │                │  ┌────────────────────┐  │  │
│  │  TypeScript  │                │  │  LLMProvider       │  │  │
│  │  Tailwind    │                │  │  (Protocol)        │  │  │
│  └──────────────┘                │  └────────┬───────────┘  │  │
│                                  │           │               │  │
│                                  │    ┌──────┴──────┐        │  │
│                                  │    ▼             ▼        │  │
│                                  │  Anthropic  ClaudeCode    │  │
│                                  │  API Adpt   CLI Adpt      │  │
│                                  │    ▼             ▼        │  │
│                                  │  Ollama     Codex CLI     │  │
│                                  │  Adapter    Adapter       │  │
│                                  │                          │  │
│                                  │  ┌────────────────────┐  │  │
│                                  │  │  SQLite            │  │  │
│                                  │  │  ~/.hired/data.db  │  │  │
│                                  │  └────────────────────┘  │  │
│                                  └──────────────────────────┘  │
│                                                                 │
│  Network calls OUT: LLM provider only + job URLs on user req.  │
└─────────────────────────────────────────────────────────────────┘
```

**Caption for slide:** *"Every component runs on the user's device. The only outbound traffic is the LLM call and job page fetches — both user-initiated."*

---

## DEMO PREP CHECKLIST

- [ ] App installed (not dev server) — Tauri binary
- [ ] Real PDF CV ready to drag-in
- [ ] Two job URLs bookmarked (one strong match, one weak)
- [ ] API key configured and tested — do a dummy call 10 min before
- [ ] Quiet room, headset or decent mic
- [ ] Camera overlay enabled in OBS/Loom/QuickTime
- [ ] Watch recording back once before submitting

## Q&A PREP — LIKELY QUESTIONS

**"Why not just use ChatGPT for this?"**  
Generic prompting has no memory of your CV across sessions, no structured scoring, no dashboard. Hired. is an end-to-end workflow, not a chat window.

**"What happens with the user's data?"**  
Everything stays in `~/.hired/data.db`. We never see it. Uninstall deletes it completely. The only data that leaves the device is the content of a single LLM call — and only when the user triggers an action.

**"How do you handle LLM hallucinations in company research?"**  
We ground every call with the actual job description and CV in context. Company research is displayed with a note that the user should verify facts. The edit-first workflow means nothing reaches an employer without user review.

**"How do you evaluate quality?"**  
We have a goldset of 20 CV/job pairs with hand-labeled expected scores. We track precision@5, MAE, and run a bias audit that swaps candidate names and checks for >10pt score variance.

**"What about LinkedIn blocking your crawler?"**  
Manual URL paste is the primary path. LinkedIn scraping is an opt-in experimental feature with a clear warning in the UI. We documented this as Risk R-02 from day one.
