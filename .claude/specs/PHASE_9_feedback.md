# Phase 9 — Feedback Loop & Unread Badges

**Duration:** Planned (Next Phase)
**Depends on:** Phases 1–8 complete

## Goal

After this phase, users can provide explicit thumbs-up/thumbs-down feedback on jobs. This feedback is used in a token-efficient, hybrid scoring system (heuristics + LLM rolling window) to improve the ranked feed over time. Additionally, new jobs receive an "unread" badge that persists until the user interacts with the job, improving feed organization.

## Acceptance Criteria

1. **Database**: A new `job_interactions` table exists to store `job_id`, `read_at`, `feedback_signal` (1, -1, null), and `feedback_reason` (e.g., 'company', 'location', 'tech_stack').
2. **Unread Badges**:
   - The Feed UI displays a counter indicating "X neue Einträge" for jobs where `read_at` is null.
   - JobCards display an unread indicator (e.g., a blue dot).
   - Any interaction (thumbs up/down, click link, skip, save, apply) automatically sets `read_at`.
   - A "Mark all as read" or individual "Mark as read" functionality exists.
3. **Hybrid Scoring - Heuristic (0 tokens)**:
   - **Company Threshold**: If a company accumulates 5 net-negative votes (negative minus positive) OR is explicitly rejected via the "Company" pill ≥2 times, subsequent jobs from this company automatically receive a `-25 point` penalty after the LLM scores them.
   - **Location Rejection**: If a user selects "Location" as the reason for rejecting a job, future jobs with the exact same location string receive a `-25 point` penalty.
4. **Hybrid Scoring - LLM Prompting (~65 tokens)**:
   - **Job Titles**: The prompt injects a rolling window of the last 5 positively rated job titles and the last 5 negatively rated job titles.
   - **Tech-Stack**: If a job is rejected due to "Tech-Stack", its `matched_skills` are aggregated. The prompt receives the Top 10 most frequently rejected skills.
5. **UI (JobCard)**:
   - Thumbs up / Thumbs down buttons on the card.
   - When thumbs down is clicked, an inline row of small pills appears: "Location", "Tech-Stack", "Company". The user can click one or ignore it.

## Tasks

### 9.1 Database & API

In `backend/db/models.py` & `backend/db/migrations.py`:
- Create `JobInteraction` model with fields:
  - `id` (int, PK)
  - `job_id` (int, FK)
  - `read_at` (datetime | null)
  - `feedback_signal` (int | null)  # 1 for up, -1 for down
  - `feedback_reason` (str | null)

In `backend/api/routes/jobs.py`:
- Add `POST /api/jobs/{id}/interact` endpoint accepting `{ action: "read" | "thumbs_up" | "thumbs_down", reason?: "company" | "location" | "tech_stack" }`.
- Update `GET /api/jobs/feed` to join `JobInteraction` and return `read_at`, `feedback_signal`, and include total unread count.

### 9.2 Scoring Service (Hybrid Logic)

In `backend/services/scoring_service.py` & `backend/llm/`:
- Add queries to fetch rolling window of titles (last 5 up, last 5 down) and top 10 rejected skills.
- Update `LLMProvider.score_job` prompts to include these signals.
- After receiving `ScoreResult` from the LLM, apply heuristic penalties:
  - Check if `job.company` has $\ge 5$ net negative votes or $\ge 2$ explicit company rejections $\rightarrow$ apply -25 pts and add red flag ("You previously rejected this employer").
  - Check if `job.location` matches explicitly rejected locations $\rightarrow$ apply -25 pts.

### 9.3 Frontend UI

In `frontend/src/feed/JobCard.tsx`:
- Add `UnreadBadge`.
- Add `ThumbsUp` / `ThumbsDown` buttons.
- On `ThumbsDown`, reveal inline pills for reason selection.
- Any interaction calls the `/interact` endpoint to mark as read.

In `frontend/src/feed/FeedScreen.tsx`:
- Display unread counter.
- Add "Mark all as read" button.

## Verification Steps

1. **Unread Flow**: Crawl new jobs $\rightarrow$ see unread badges and counter $\rightarrow$ click link $\rightarrow$ badge disappears and counter decrements.
2. **LLM Rolling Window**: Vote 6 jobs positively. Verify the LLM prompt only receives the last 5 titles.
3. **Heuristic Penalty**: Vote 5 jobs from "Cyberdyne" negatively. Crawl a 6th job from "Cyberdyne". Verify its score is severely penalized (-25) with the correct red flag.
4. **Tests**: Pytest and Vitest cover the new components and scoring logic.
