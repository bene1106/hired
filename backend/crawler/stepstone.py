"""Stepstone.de job search scraper.

Strategy:
1. Build a stepstone.de search URL from profile roles + locations.
2. GET the search page and parse job cards using stable ``data-at``
   attribute selectors (``job-item-title``, ``job-item-company-name``,
   ``job-item-location``, ``job-item-work-from-home``).
3. Cap at ``query.max_jobs``.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from .base import CrawlQuery, JobSource, RawJob

logger = logging.getLogger(__name__)

_BASE = "https://www.stepstone.de"
_TIMEOUT = 20.0
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# German remote-policy labels used in the UI
_REMOTE_LABELS = {"nur home-office", "vollständig remote", "fully remote"}
_HYBRID_LABELS = {"teilweise home-office", "hybrid"}


class StepstoneSource(JobSource):
    """Searches stepstone.de using profile roles and locations."""

    name = "stepstone"

    def fetch_jobs(self, query: CrawlQuery) -> Iterable[RawJob]:
        role = query.target_roles[0] if query.target_roles else "Software Engineer"
        location = query.target_locations[0] if query.target_locations else "Deutschland"

        # Stepstone uses hyphenated keywords in the path and ?where= for location.
        slug = role.lower().replace(" ", "-")
        url = f"{_BASE}/jobs/{quote_plus(slug)}?where={quote_plus(location)}&sort=2"

        logger.info("Stepstone fetching: %s", url)
        try:
            with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
        except Exception as exc:
            logger.warning("Stepstone fetch failed: %s", exc)
            return

        jobs = _parse_cards(resp.text)
        logger.info("Stepstone: extracted %d jobs (page size=%d)", len(jobs), len(resp.text))
        yield from jobs[: query.max_jobs]


def _parse_cards(html: str) -> list[RawJob]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('article[data-testid="job-item"]')
    jobs: list[RawJob] = []
    for card in cards:
        job = _parse_card(card)
        if job:
            jobs.append(job)
    return jobs


def _parse_card(card) -> RawJob | None:
    # Job ID from the article's id attribute: "job-item-{id}"
    article_id = card.get("id") or ""
    m = re.search(r"job-item-(\d+)", article_id)
    if not m:
        return None
    job_id = m.group(1)

    title_el = card.select_one('[data-at="job-item-title"]')
    if not title_el:
        return None
    title = title_el.get_text(strip=True)
    if not title:
        return None

    href = title_el.get("href") or ""
    url = (_BASE + href) if href.startswith("/") else (href or None)

    company_el = card.select_one('[data-at="job-item-company-name"]')
    company = company_el.get_text(strip=True) if company_el else None

    location_el = card.select_one('[data-at="job-item-location"]')
    location = location_el.get_text(strip=True) if location_el else None

    wfh_el = card.select_one('[data-at="job-item-work-from-home"]')
    wfh_text = wfh_el.get_text(strip=True).lower() if wfh_el else ""
    if wfh_text in _REMOTE_LABELS:
        remote_policy = "remote"
    elif wfh_text in _HYBRID_LABELS:
        remote_policy = "hybrid"
    else:
        remote_policy = _infer_remote(location or "", title)

    snippet_el = card.select_one('[data-at="jobcard-content"]')
    description = snippet_el.get_text(separator="\n", strip=True) if snippet_el else None

    return RawJob(
        source="stepstone",
        source_id=job_id,
        title=title,
        company=company or None,
        location=location or None,
        remote_policy=remote_policy,
        description=description[:30_000] if description else None,
        url=url,
    )


def _infer_remote(location: str, title: str = "") -> str | None:
    combined = (location + " " + title).lower()
    if "remote" in combined or "homeoffice" in combined or "home office" in combined:
        return "remote"
    if "hybrid" in combined:
        return "hybrid"
    return None


__all__ = ["StepstoneSource"]
