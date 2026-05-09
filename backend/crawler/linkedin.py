"""LinkedIn search source — **experimental**, see ADR-0006.

LinkedIn actively blocks automated traffic. This source uses a public,
unauthenticated job-search URL fetched through Playwright (so JavaScript-
rendered content is captured), with random per-request delays. It is
explicitly best-effort: every Phase 4 entry point that uses it surfaces a
"may break — paste URLs manually for reliable results" affordance.

If Playwright is not installed (browser binaries missing), or LinkedIn
returns a challenge page, ``fetch_jobs`` raises ``LinkedInUnavailable`` so
the caller can fall back to the manual-URL path without a hard failure.
"""

from __future__ import annotations

import hashlib
import logging
import random
import re
import time
from collections.abc import Iterable
from urllib.parse import quote_plus

from .base import CrawlQuery, JobSource, RawJob

logger = logging.getLogger(__name__)


class LinkedInUnavailable(RuntimeError):
    """Raised when Playwright/LinkedIn is unreachable. Caller should fall back."""


_LINKEDIN_SEARCH_URL = (
    "https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}"
)


class LinkedInSource(JobSource):
    """Best-effort LinkedIn scraper. **Experimental.**"""

    name = "linkedin"

    def __init__(
        self,
        *,
        delay_range: tuple[float, float] = (1.0, 3.0),
        page_factory=None,
    ) -> None:
        # ``page_factory`` lets tests inject a fake "page" object that exposes
        # ``goto`` and ``content``. Real callers go through Playwright.
        self._delay_range = delay_range
        self._page_factory = page_factory

    def fetch_jobs(self, query: CrawlQuery) -> Iterable[RawJob]:
        keywords = ", ".join(query.target_roles) or "software engineer"
        location = (query.target_locations[0] if query.target_locations else "") or "Remote"
        url = _LINKEDIN_SEARCH_URL.format(
            keywords=quote_plus(keywords), location=quote_plus(location)
        )

        page_factory = self._page_factory or _default_playwright_page_factory
        try:
            html = page_factory(url)
        except LinkedInUnavailable:
            raise
        except Exception as exc:  # pragma: no cover — Playwright failure modes
            raise LinkedInUnavailable(f"LinkedIn fetch failed: {exc}") from exc

        time.sleep(random.uniform(*self._delay_range))

        for raw in _parse_search_html(html, query.max_jobs):
            yield raw


def _default_playwright_page_factory(url: str) -> str:
    """Fetch ``url`` with a headless browser and return the page HTML.

    Imported lazily so the rest of the backend doesn't pay the Playwright
    cost on import. If the user hasn't run ``playwright install`` we raise
    ``LinkedInUnavailable`` and the orchestrator falls back.
    """
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise LinkedInUnavailable("Playwright is not installed.") from exc

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/121.0 Safari/537.36"
                    )
                )
                page = context.new_page()
                page.goto(url, timeout=20_000, wait_until="domcontentloaded")
                return page.content()
            finally:
                browser.close()
    except PlaywrightError as exc:  # pragma: no cover
        raise LinkedInUnavailable(f"Playwright error: {exc}") from exc


# ---------------------------------------------------------------------------
# HTML parsing — kept simple. LinkedIn's DOM changes; we only depend on the
# anchor-href shape (`/jobs/view/<id>`) and the public card structure.
# ---------------------------------------------------------------------------

_JOB_ID_RE = re.compile(r"/jobs/view/(\d+)")


def _parse_search_html(html: str, max_jobs: int) -> Iterable[RawJob]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    seen_ids: set[str] = set()
    cards = soup.select("a.base-card__full-link, a.job-card-list__title")
    if not cards:
        cards = soup.find_all("a", href=_JOB_ID_RE)

    for card in cards:
        href = card.get("href") or ""
        match = _JOB_ID_RE.search(href)
        if not match:
            continue
        job_id = match.group(1)
        if job_id in seen_ids:
            continue
        seen_ids.add(job_id)

        title = (card.get_text() or "").strip() or "(untitled role)"
        container = card.find_parent("div") or card
        company_node = container.select_one(
            ".base-search-card__subtitle, .job-card-container__primary-description"
        )
        location_node = container.select_one(
            ".job-search-card__location, .job-card-container__metadata-item"
        )

        yield RawJob(
            source=LinkedInSource.name,
            source_id=job_id,
            title=title[:512],
            company=(company_node.get_text(strip=True) if company_node else None),
            location=(location_node.get_text(strip=True) if location_node else None),
            url=href.split("?")[0],
            description=None,  # search cards don't include the body
        )

        if len(seen_ids) >= max_jobs:
            return


def hash_search_query(query: CrawlQuery) -> str:
    """Stable digest for logging — never embedded in source_id."""
    payload = f"{query.target_roles}|{query.target_locations}|{query.max_jobs}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


__all__ = ["LinkedInSource", "LinkedInUnavailable"]
