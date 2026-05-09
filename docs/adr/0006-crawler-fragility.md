# ADR-0006: Manual URL Paste Is the Primary Crawler Path

## Status: Accepted

## Context

Phase 4 needs a way to ingest job postings into the local database so the
LLM can score them. The phase spec names LinkedIn as the first target
source. There are two ways we could approach this:

1. **Build a robust LinkedIn scraper** as the primary path. Fall back to
   manual entry only if LinkedIn breaks.
2. **Treat manual URL paste as the primary path** and ship a best-effort
   LinkedIn scraper as an experimental nice-to-have.

We chose option 2. This ADR records why.

## Why LinkedIn-first is a bad bet

- **They actively block scrapers.** LinkedIn has an entire team focused on
  detecting and challenging non-human traffic. A scraper that works on
  Tuesday can be blocked by Friday — sometimes silently, returning empty
  HTML or a CAPTCHA wall instead of a clean 4xx.
- **The DOM changes often.** Every CSS-selector-based scraper is a
  maintenance burden. We do not have the team to chase those changes.
- **Their ToS prohibits automated access without permission.** Even if a
  scraper works, the legal posture is uncomfortable. (We are a local-first
  app with no centralized scraping, so the user's individual access is
  governed by their own LinkedIn account — but we should not encourage
  ToS-noncompliant behavior in the UI.)
- **It blocks the demo.** The Phase 4 acceptance criterion is "user clicks
  Crawl → ranked feed in 30s." If LinkedIn returns an empty page during
  the prof demo, the demo fails. We need a path that always works.

## What we ship instead

**Primary: manual URL paste.** The user copies a job URL from any board
(LinkedIn, Lever, Greenhouse, Workday, company career sites) and pastes
it into the UI. Our crawler fetches each URL with a plain HTTP client,
extracts metadata via JSON-LD (`JobPosting` schema, used by most
applicant-tracking systems) or Open Graph tags, and stores normalized
records.

This works on every job board we have tested and degrades gracefully —
worst case we get the page title and the `<main>` text, which the LLM
scorer can still handle.

**Secondary: experimental LinkedIn scraper.** A Playwright-driven source
exists in `backend/crawler/linkedin.py`. It is clearly marked experimental
in the code, in the UI ("LinkedIn scraping is unreliable. Paste job URLs
directly for reliable results."), and in the phase docs. When it fails
(`LinkedInUnavailable` is raised) the orchestrator falls through to manual
URLs without a hard error.

## Consequences

- **The primary user gesture is "paste URLs."** The UI must make this
  cheap and ergonomic — a single multiline textbox with one URL per line.
- **No background scheduling.** Ever. Crawls are user-triggered only,
  matching the spec. We will revisit if and only if a future phase
  introduces an authenticated source with a programmatic API.
- **`(source, source_id)` is the dedup key.** For manual URLs we derive a
  stable `source_id` from a SHA-256 hash of the URL — the same URL pasted
  twice deduplicates cleanly across crawls.
- **We do not ship a scheduler or a robots.txt crawler-of-record.**
  `httpx` requests one URL the user explicitly handed us; that is closer
  to a browser fetch than to bulk crawling, and the manual nature is the
  point.

## Rejected alternatives

- **JobSpy / linkedin-jobs-scraper / open-source scrapers** — same
  fragility risk, plus an extra dep we would have to vendor or trust.
- **Paid job APIs (Adzuna, Reed, USAJOBS).** Would solve the reliability
  problem but is a cloud-hosted dependency, which is the one thing
  Hired.'s architecture explicitly disallows (see ADR-0001).
- **OAuth-authenticated LinkedIn API.** Restricted access; you need a
  partnership. Not realistic for this project.
