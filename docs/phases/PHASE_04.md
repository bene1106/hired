# Phase 4 — Job Ingestion & Ranked Feed — MVP (shipped in v0.1.1)

**Status:** ✅ DONE

## Scope

Jobs einlesen, gegen das Profil scoren und als gerankten Feed anzeigen.
Primärpfad ist manuelles URL-Einfügen; LinkedIn-Scraping nur experimentell.

Spec: `.claude/specs/PHASE_4_jobs.md`

## Real erledigt

- Migration `0004_phase4_jobs_scoring.py`: `remote_policy`, `salary_min`,
  `salary_max`, `currency` auf `jobs`; `profile_version` auf `profile` und
  `job_scores` (Scores invalidieren automatisch bei Profil-Edit).
- `backend/crawler/`: `JobSource`-ABC + `RawJob`; primär `ManualURLSource`
  (httpx + BeautifulSoup, JSON-LD `JobPosting` zuerst, Open-Graph-Fallback);
  experimentell `LinkedInSource` (Playwright, wirft `LinkedInUnavailable`);
  `service.crawl()` mit Dedup auf `(source, source_id)`.
- `services/profile_mapper.py` (DB-Rows → `llm.types`-Shapes).
- `services/scoring_service.py` — liest gecachte Scores, scort Misses über
  5-Thread-Pool, persistiert pro `(profile_version, job_id)`.
- `services/crawl_progress.py` — in-process Registry (resettet bei Neustart).
- Endpoints: `POST /api/jobs/crawl`, `GET /api/jobs/crawl/status/{job_id}`,
  `GET /api/jobs/feed` (Filter + min-score), `POST /api/jobs/{id}/action`
  (apply/save/skip → upsert Application).
- Frontend `feed/{FeedScreen,JobCard}.tsx`: Inline-Crawl-Panel, Status-Poll,
  Filterzeile All/Saved/Applied/Skipped, Score-Badges + Skill-Chips.
- `eval/goldset.json` von 3 → 20 Einträgen; `eval/run_eval.py`
  (in-range-rate, MAE, precision@5) + `eval/bias_audit.py`; Root-`Makefile`.

PR: #5 (`feat/phase-4-jobs`) · ADR: `docs/adr/0006-crawler-fragility.md`

## Offen

- Zwei Backend-Backlog-Bugs aus dem Parser sind als Issues offen:
  - #19 — unzuverlässiger Company-Name-Parser → `CompanyMark` zeigt „?".
  - #20 — Role-Title mis-parsed (z. B. Bitpanda → Firmenname im Titel).

## Out-of-scope / Deferrals

- **Live-LinkedIn-Scraping** ist fragil by design; Default-Quelle ist
  `manual_url`, LinkedIn ist `?source=linkedin`-Opt-in.
- **Background-Progress** in in-process Dict (resettet bei Neustart).
- **Eval gegen MockProvider** ist strukturell, aber die Zahlen sind nicht
  aussagekräftig — echte Eval via `make eval PROVIDER=anthropic_api`.
