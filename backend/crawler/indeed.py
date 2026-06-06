"""Indeed.de job search scraper — BeautifulSoup only, no Playwright.

Search strategy:
1. Build a de.indeed.com search URL from the user's target_roles and
   target_locations (falls back to "Berlin" if no locations configured).
2. GET the page; try to extract the embedded ``__INDEED_DATA__`` /
   ``window.mosaic.providerData`` JSON first (more reliable than CSS selectors
   because Indeed frequently rewrites their DOM).
3. Fall back to parsing ``<a>`` job-card links from the HTML.
4. For each discovered job URL, fetch the detail page to get the full
   description, again preferring the embedded JSON.

Conservative scraping:
- 2–4 second random delay between requests.
- Realistic User-Agent.
- Cap at ``query.max_jobs`` total.
- No pagination beyond the first results page (keeps server load minimal).
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from collections.abc import Iterable
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from .base import CrawlQuery, JobSource, RawJob
from .location_filter import location_matches

logger = logging.getLogger(__name__)

_BASE = "https://de.indeed.com"
_TIMEOUT = 20.0
_MIN_DELAY = 2.0
_MAX_DELAY = 4.0
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class IndeedSource(JobSource):
    """Searches de.indeed.com using profile roles and locations."""

    name = "indeed"

    def fetch_jobs(self, query: CrawlQuery) -> Iterable[RawJob]:
        role = query.target_roles[0] if query.target_roles else "Software Engineer"
        location = query.target_locations[0] if query.target_locations else "Berlin"

        search_url = (
            f"{_BASE}/jobs"
            f"?q={quote_plus(role)}"
            f"&l={quote_plus(location)}"
            "&fromage=14"
            "&sort=date"
        )

        with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            job_urls = self._discover_urls(client, search_url, limit=query.max_jobs)
            for url in job_urls:
                _sleep()
                job = self._fetch_detail(client, url, role, location)
                if job is not None and location_matches(
                    job.location, job.remote_policy, query.target_locations
                ):
                    yield job

    # ------------------------------------------------------------------
    # URL discovery
    # ------------------------------------------------------------------

    def _discover_urls(self, client: httpx.Client, search_url: str, limit: int) -> list[str]:
        try:
            resp = client.get(search_url)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Indeed search page fetch failed: %s", exc)
            return []

        html = resp.text
        urls: list[str] = []

        # Attempt 1: extract job keys from mosaic provider JSON blob
        urls = _extract_urls_from_script(html)

        # Attempt 2: parse anchor tags
        if not urls:
            urls = _extract_urls_from_html(html)

        return urls[:limit]

    # ------------------------------------------------------------------
    # Detail page fetch
    # ------------------------------------------------------------------

    def _fetch_detail(
        self, client: httpx.Client, url: str, role: str, location: str
    ) -> RawJob | None:
        try:
            resp = client.get(url)
            resp.raise_for_status()
        except Exception as exc:
            logger.debug("Indeed detail fetch failed for %s: %s", url, exc)
            return None

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        title = _og_or_title(soup, html)
        if not title:
            return None

        company = (
            _jsonld_company(html)
            or _text(soup, '[data-testid="inlineHeader-companyName"]')
            or _text(soup, '[data-company-name]')
        )
        job_location = _text(soup, '[data-testid="job-location"]') or location

        description = _extract_description(soup)

        # source_id: stable hash of the URL path (job key)
        m = re.search(r"jk=([a-f0-9]+)", url)
        source_id = m.group(1) if m else url[-32:]

        return RawJob(
            source=self.name,
            source_id=source_id,
            title=title,
            company=company,
            location=job_location,
            remote_policy=_infer_remote(job_location, title),
            description=description[:30_000] if description else None,
            url=url,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sleep() -> None:
    time.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))


def _extract_urls_from_script(html: str) -> list[str]:
    """Try to pull job keys from Indeed's embedded JSON blobs."""
    urls: list[str] = []
    # Pattern: jobKeys array embedded in window._initialData or mosaic data
    for pattern in (
        r'"jobKeys"\s*:\s*(\[[^\]]+\])',
        r'"jobKey"\s*:\s*"([a-f0-9]{16})"',
    ):
        for m in re.finditer(pattern, html):
            raw = m.group(1)
            if raw.startswith("["):
                try:
                    keys = json.loads(raw)
                    for k in keys:
                        urls.append(f"{_BASE}/rc/clk?jk={k}")
                except json.JSONDecodeError:
                    pass
            else:
                urls.append(f"{_BASE}/rc/clk?jk={raw}")
    return list(dict.fromkeys(urls))  # deduplicate, preserve order


def _extract_urls_from_html(html: str) -> list[str]:
    """Fallback: find job-card anchors in the rendered HTML."""
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for a in soup.select('a[href*="/rc/clk"], a[href*="/pagead/clk"], a[data-jk]'):
        href = a.get("href") or ""
        if href.startswith("/"):
            href = urljoin(_BASE, href)
        if href and href not in urls:
            urls.append(href)
    return urls


def _og_or_title(soup: BeautifulSoup, html: str) -> str:
    og = _meta(soup, "og:title")
    if og:
        # Strip " - Company | Indeed" suffix
        og = re.sub(r"\s*[-|].*$", "", og).strip()
        return og
    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text().strip()
        return re.sub(r"\s*[-|].*$", "", text).strip()
    return ""


def _jsonld_company(html: str) -> str:
    """Extract hiringOrganization.name from JSON-LD JobPosting schema."""
    for m in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(m.group(1))
            if not isinstance(data, dict):
                continue
            if data.get("@type") == "JobPosting":
                org = data.get("hiringOrganization") or {}
                name = org.get("name") if isinstance(org, dict) else None
                if name:
                    return name.strip()
        except (json.JSONDecodeError, AttributeError):
            continue
    return ""


def _meta(soup: BeautifulSoup, prop: str) -> str:
    tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return (tag.get("content") or "").strip() if tag else ""


def _text(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else ""


def _extract_description(soup: BeautifulSoup) -> str:
    for selector in (
        "#jobDescriptionText",
        '[data-testid="jobsearch-JobComponent-description"]',
        ".jobsearch-jobDescriptionText",
        "article",
    ):
        el = soup.select_one(selector)
        if el:
            return el.get_text(separator="\n").strip()
    return ""


def _infer_remote(location: str, title: str = "") -> str | None:
    combined = (location + " " + title).lower()
    if "remote" in combined:
        return "remote"
    if "hybrid" in combined:
        return "hybrid"
    return None


__all__ = ["IndeedSource"]
