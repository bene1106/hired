# Phase 4 — Job Ingestion & Ranked Feed

**Duration:** Week 4
**Owner suggestion:** Backend Engineer (crawler) + AI Engineer (scoring) + Frontend (feed UI)
**Depends on:** Phases 1–3 complete

## Goal

After this phase, a user clicks "Crawl" and within ~30 seconds sees a ranked list of jobs with match scores and rationales they can decide on (apply / save / skip).

This is the **first end-to-end demo milestone** — show this to the team and prof at end of W4.

## Acceptance Criteria

1. User clicks "Crawl" → status indicator shows "Crawling…"
2. Within 30s for ~20 jobs, sees a feed of job cards
3. Each card shows: title, company, location, match score (0–100), 2-sentence rationale, "Apply / Save / Skip" buttons
4. Cards are sorted by score descending
5. Re-crawling deduplicates against previously-seen jobs
6. Skip / Save / Apply actions update status in DB and remove the card from the feed (or move it to a different view)

## Tasks

### 4.1 Crawler Module

In `backend/crawler/`:

```
linkedin.py    — LinkedIn-specific scraping logic (Playwright)
base.py        — Abstract base for future sources (StepStone, Indeed)
service.py     — Coordinates crawl: dedup, normalize, save
```

Crawler design:
- Uses Playwright in headless mode
- **User-triggered only** (no aggressive scheduler in MVP)
- Search params from profile: target_role, target_location
- Configurable: max jobs per crawl (default 20)
- Random delays between requests (1–3s)
- Respects `robots.txt` (use `requests-robotxt` or roll your own)
- Outputs normalized `Job` records

**Important:** LinkedIn actively blocks scraping. Document this risk clearly. Provide a fallback: user pastes a list of job URLs manually, and the crawler fetches and normalizes those.

### 4.2 Normalization

Each crawled job is normalized to:

```python
{
  "source": "linkedin",
  "source_id": "<linkedin job ID>",
  "title": str,
  "company": str,
  "location": str,
  "remote_policy": "remote" | "hybrid" | "onsite" | None,
  "salary_min": int | None,
  "salary_max": int | None,
  "currency": str | None,
  "description": str,  # full text
  "url": str,
  "posted_at": datetime,
}
```

Dedup check: `(source, source_id)` is unique.

### 4.3 Scoring Pipeline

In `backend/services/scoring_service.py`:

- For each new job, call `LLMProvider.score_job(profile, job)` → returns `ScoreResult`
- Batch jobs (e.g., 5 at a time) to reduce overhead
- Cache results: don't re-score a `(profile_version, job_id)` pair
- Store in `job_scores` table

`ScoreResult` structure:

```python
class ScoreResult(BaseModel):
    score: int  # 0-100
    rationale: str  # 2 sentences max
    matched_skills: list[str]
    missing_skills: list[str]
    red_flags: list[str]  # things that might be deal-breakers
```

### 4.4 Goldset Evaluation

Expand `eval/goldset.json` to **20 manually-labeled CV/job pairs**:

- Mix of strong matches (expected score 80+), borderline (50–70), poor (<40)
- Include diverse roles: SWE, data, design, product
- Each entry: profile, job, expected score range, must-mention skills

Add `eval/run_eval.py`:
- Runs the configured provider against the goldset
- Computes precision@5 (top 5 jobs by score should mostly be high-expected)
- Computes mean absolute error from expected score range
- Prints results table

Add `make eval` target.

### 4.5 Bias Audit

In `eval/bias_audit.py`:

- For each job in the goldset, swap the candidate's name (e.g., John → Aisha, Aisha → John)
- Re-score
- Report score variance — should be <10pt for any pair

This is a key part of Section 7 of the project doc (Ethics). Even if not perfect, **measuring is what matters for the grade.**

### 4.6 Feed API

```
POST /api/jobs/crawl
  Body: {"max_jobs": int} (optional, default 20)
  Returns: {"job_id": str}  # background task ID
  
GET /api/jobs/crawl/status/{job_id}
  Returns: {"status": "running"|"done"|"error", "progress": int, "total": int}

GET /api/jobs/feed
  Query: ?limit=20&min_score=0&exclude_status=skipped
  Returns: list of {job, score, rationale, status}

POST /api/jobs/{id}/action
  Body: {"action": "apply"|"save"|"skip"}
  Returns: updated job state
```

Use FastAPI BackgroundTasks for the crawl trigger; long-running tasks need progress reporting.

### 4.7 Feed UI

In `frontend/src/feed/`:

- "Crawl" button in top bar; clicking starts crawl, button shows "Crawling… 12/20"
- Job cards stack vertically; each card:
  - Score badge (color-coded: green ≥75, yellow 50–74, gray <50)
  - Title + company + location
  - Rationale (2 lines)
  - Skills chips (matched in green, missing in muted)
  - Action buttons: Apply (primary), Save, Skip
- Empty state with friendly copy
- Filter dropdown: "All / Saved / Skipped / Applied"

### 4.8 Caching

In `backend/services/cache_service.py`:

- Simple in-memory + DB-backed cache for `score_job` results
- Key: hash of `(profile_id, profile_version, job_id)`
- TTL: until profile is edited (then invalidate)

This protects against re-scoring on every page load.

## Verification Steps

1. Manual smoke: click Crawl with profile set up → see 10+ scored jobs in feed
2. Skip a job → it disappears from main feed; visible in "Skipped" filter
3. Re-crawl → no duplicates appear
4. `make eval` runs goldset, reports precision and MAE
5. `make bias-audit` runs name-swap, reports variance
6. Coverage: backend ≥80%, scoring service ≥90%
7. CI green; PR merged

## Risks Specific to This Phase

| Risk | Mitigation |
|------|-----------|
| LinkedIn detects/blocks scraping | Manual fallback (paste URLs); document clearly in UI |
| Scoring is slow (20 jobs × 5s = 100s) | Batch + parallel; show progress; allow user to interact with already-scored jobs |
| LLM gives inconsistent scores | Few-shot examples in prompt; eval against goldset to detect drift |
| Bias in scoring | Measure with audit; surface variance in PR description |

## Out of Scope

- Multi-source crawling (only LinkedIn for now; structure allows StepStone later)
- Application generation (Phase 5)
- Salary benchmarks (Phase 6 nice-to-have)

## Phase Demo Script

When this phase is done, prep a 3-minute internal demo:
1. Open the app (already onboarded)
2. Click Crawl
3. Watch progress
4. Show the ranked feed
5. Demonstrate skip → it disappears
6. Show the bias audit results

This is also the script for the **mid-semester demo** to the prof.
