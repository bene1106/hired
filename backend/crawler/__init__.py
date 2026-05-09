"""Job ingestion sources + the crawl orchestrator.

The crawler is **user-triggered only** — there is no scheduler in MVP.
Two sources ship in Phase 4:

- ``manual_urls`` — fetches arbitrary job URLs and extracts metadata. This is
  the **primary** path; it works against any board the user can copy a link
  from and is the path documented in the UI.
- ``linkedin`` — best-effort Playwright scraper. Experimental and clearly
  labeled as such; LinkedIn actively blocks scraping and the page DOM
  changes often. See ADR-0006.

The orchestrator (``service.crawl``) is source-agnostic: it takes any
``JobSource`` and persists deduplicated, normalized rows to ``jobs``.
"""

from .base import JobSource, RawJob
from .service import CrawlResult, crawl

__all__ = ["CrawlResult", "JobSource", "RawJob", "crawl"]
