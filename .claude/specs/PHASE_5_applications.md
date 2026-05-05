# Phase 5 — Application Materials, Dashboard & Interview Prep

**Duration:** Weeks 5–6
**Owner suggestion:** Frontend + AI Engineer
**Depends on:** Phases 1–4 complete

## Goal

This phase delivers the rest of the user-facing value:
- Click "Apply" on a job → get tailored CV highlights, cover letter, and company brief
- See all applications in a dashboard
- For each application, get interview prep (questions, company info, role explanation)

After this phase, the **MVP is feature-complete**. Phase 6 is polish + extra providers.

## Acceptance Criteria

End-to-end flow:
1. From the feed (Phase 4), user clicks "Apply" on a job
2. Within ~30s (API mode) sees:
   - Company research brief (1 page, with sources)
   - CV tailoring suggestions (which experiences to emphasize)
   - Generated cover letter (editable)
3. Edits cover letter, clicks "Mark applied"
4. Application appears in Dashboard with status "Applied"
5. From the application, user opens "Interview prep" → sees role-specific questions and company info
6. User can answer a question, get feedback

## Tasks

### 5.1 Generation Pipeline

In `backend/services/application_service.py`:

```python
def generate_application_materials(application_id: int) -> ApplicationMaterials:
    profile = get_profile()
    job = get_job(application.job_id)
    
    # Step 1: Company research (cached per company)
    brief = cached_research(job.company) or provider.research_company(job.company)
    
    # Step 2: CV tailoring  
    cv_suggestions = provider.tailor_cv(profile, job)
    
    # Step 3: Cover letter (uses brief)
    cover_letter = provider.generate_cover_letter(profile, job, brief)
    
    return ApplicationMaterials(brief=brief, cv_suggestions=cv_suggestions, cover_letter=cover_letter)
```

**Important caching:** company research is keyed by company name (case-insensitive). 5 jobs at the same company → 1 research call, not 5. Major cost saver.

### 5.2 Material Storage

Store each generated material in `application_materials` table:
- `type`: `"company_brief" | "cv_suggestions" | "cover_letter"`
- `content`: text (markdown)
- `source_meta`: JSON with sources (URLs, citations) for company brief

Materials are **versioned** — when the user edits, save a new row. Allow viewing history.

### 5.3 API Endpoints

```
POST /api/applications/{job_id}
  Triggers material generation (background task).
  Returns: {"application_id": int, "task_id": str}
  
GET /api/applications/{id}/materials
  Returns: latest version of each material type
  
PUT /api/applications/{id}/materials/{type}
  Body: {"content": str}
  Saves user edits
  
GET /api/applications
  Query: ?status=applied|saved|interview|offer|rejected
  Returns: list of applications with summary

PUT /api/applications/{id}/status
  Body: {"status": str, "notes": str|null}
  Updates application status
```

### 5.4 Application Generation UI

`frontend/src/applications/GeneratePage.tsx`:

- Triggered when user clicks "Apply" on a job in feed
- Shows three sections (sequential reveal as each finishes):
  1. **Company brief** — markdown render with source links
  2. **CV tailoring** — bullet list of suggestions
  3. **Cover letter** — editable rich-text-ish editor (use a simple textarea with Markdown preview side-by-side initially; later upgrade to TipTap if time)
- Each section has a "Regenerate" button (calls API again)
- Footer: "Mark applied" button → marks application status, navigates to dashboard

### 5.5 Application Dashboard

`frontend/src/applications/Dashboard.tsx`:

- Default view: table with columns (Company, Role, Applied On, Status, Actions)
- Status pill: color-coded
- Filter by status, sort by date
- Click row → opens detail view
- Optional Kanban view if time permits (Discovered → Applied → Interview → Offer → Rejected)

### 5.6 Interview Prep

In `frontend/src/applications/InterviewPrep.tsx`:

For each application:
- **Role explanation**: 2 paragraphs synthesized from job description (one LLM call, cached)
- **Company info**: reuse the company brief from application generation
- **Question bank**: ~10 likely interview questions, generated via `LLMProvider.generate_interview_questions(job)`
  - Categorized: Technical, Behavioral, Role-specific, Company-fit
- **Practice mode**: click a question → text area for answer → submit → get feedback via `LLMProvider.evaluate_answer`
- Track which questions the user has practiced (just store in DB)

### 5.7 Privacy Hooks

When the user marks an application as "rejected":
- Optional prompt: "Want to log why? (Helps you spot patterns later)"
- This data stays local — only used for the rejection-analysis stretch goal

### 5.8 Cost Display (API mode)

If the active provider is `anthropic_api`:
- Track token usage per request (provider returns it)
- Show estimated cost in the generation UI: "This generation cost ~$0.08"
- Show running total in Settings: "Today: $1.27 · This week: $4.50"

For Claude Code and Ollama, show "$0.00 (subscription)" or "$0.00 (local)".

### 5.9 Tests

- Unit tests for cache (company research key matching, case-insensitive)
- Integration tests for generation pipeline (with MockProvider)
- E2E test: feed → apply → materials shown → edit → mark applied (use Playwright in test mode)

### 5.10 Edit-First Workflow

**This is core to the ethics story** (Section 7 of project doc):
- Materials are never auto-sent anywhere
- Every generated artifact opens in an editor view
- User must explicitly click "Mark applied" — there's no auto-submit
- Show edit count: "Edited 3 times since generation" (small text)

## Verification Steps

1. End-to-end: open app → crawl → apply on a job → see all 3 materials → edit cover letter → mark applied → see in dashboard
2. Open same job's application → click Interview Prep → see questions → answer one → get feedback
3. Apply to a 2nd job at the same company → company brief is cached (no duplicate research call — verify via logs)
4. Edit profile → next material generation reflects new info (cache invalidated)
5. Coverage ≥80%
6. CI green; PR merged

## Phase Demo Script (this is the demo for end-of-W6 internal review)

5-min live demo:
1. Onboarded app, feed has jobs (set up beforehand)
2. Click Apply on top job → wait, narrate what's happening
3. Show generated materials, edit cover letter inline
4. Mark applied → land in dashboard
5. Click that application → open Interview Prep → answer one question
6. Show Settings → cost tracking ($0.20 spent today, etc.)

## Out of Scope

- Mock interview chatbot (stretch goal — Phase 6)
- Multi-language generation (stretch — Phase 6)
- Rejection pattern analysis (stretch — Phase 6)
- Direct ATS submission (explicitly out of scope of project)
