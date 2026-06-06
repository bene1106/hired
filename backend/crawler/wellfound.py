"""Wellfound (formerly AngelList Talent) job search scraper.

Wellfound is a Next.js single-page application — most content is rendered
client-side via GraphQL calls. This scraper takes a best-effort approach
WITHOUT Selenium/Playwright:

  1. Fetch the search page HTML.
  2. Try to parse the ``__NEXT_DATA__`` JSON embedded by the SSR pass.
     Wellfound does server-render some initial state; whether it includes
     job listings depends on their current deployment.
  3. If no jobs are found in ``__NEXT_DATA__``, log an informative warning
     so the user knows why the source returned zero results (bot protection
     or JS-only rendering) rather than silently returning an empty list.

Users who find Wellfound returns zero results should add specific job
listing URLs to the manual-URL source instead.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from .base import CrawlQuery, JobSource, RawJob
from .location_filter import location_matches

logger = logging.getLogger(__name__)

_BASE = "https://wellfound.com"
_TIMEOUT = 20.0
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class WellfoundSource(JobSource):
    """Searches wellfound.com using profile roles and Berlin as location."""

    name = "wellfound"

    def fetch_jobs(self, query: CrawlQuery) -> Iterable[RawJob]:
        role = query.target_roles[0] if query.target_roles else ""
        location = query.target_locations[0] if query.target_locations else "Berlin"

        # Build a role slug: "software engineer" → "software-engineer"
        role_slug = re.sub(r"\s+", "-", role.lower().strip()) if role else ""
        search_url = f"{_BASE}/jobs?locations={quote_plus(location)}"
        if role_slug:
            search_url += f"&roles={quote_plus(role_slug)}"

        try:
            with httpx.Client(
                headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True
            ) as client:
                resp = client.get(search_url)
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:
            logger.warning("Wellfound fetch failed: %s", exc)
            return

        all_jobs = list(_parse_next_data(html, query.max_jobs))
        jobs = [
            j for j in all_jobs
            if location_matches(j.location, j.remote_policy, query.target_locations)
        ]
        if not jobs:
            logger.warning(
                "Wellfound returned 0 jobs for role=%r location=%r. "
                "Wellfound is heavily client-side rendered; the SSR payload "
                "may not include job listings in this deployment. "
                "Add specific listing URLs via the manual-URL source as a fallback.",
                role,
                location,
            )
        yield from jobs


# ---------------------------------------------------------------------------
# __NEXT_DATA__ parser
# ---------------------------------------------------------------------------


def _parse_next_data(html: str, limit: int) -> Iterable[RawJob]:
    """Extract jobs from the Next.js server-side data blob, if present."""
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not m:
        return

    try:
        data: dict = json.loads(m.group(1))
    except json.JSONDecodeError:
        return

    # Walk the page props looking for job listing arrays
    page_props = data.get("props", {}).get("pageProps", {})
    jobs_raw = _find_jobs_array(page_props)

    count = 0
    for raw in jobs_raw:
        if count >= limit:
            break
        job = _parse_job(raw)
        if job is not None:
            yield job
            count += 1


def _find_jobs_array(obj: object, depth: int = 0) -> list[dict]:
    """Recursively search for a list of dicts that look like job postings."""
    if depth > 6:
        return []
    if isinstance(obj, list):
        # Heuristic: if the first element has "title" and ("url" or "slug"), it's jobs
        if obj and isinstance(obj[0], dict):
            keys = set(obj[0].keys())
            if ("title" in keys or "jobTitle" in keys) and (
                "url" in keys or "slug" in keys or "id" in keys
            ):
                return [x for x in obj if isinstance(x, dict)]
        # Recurse into list items
        for item in obj:
            found = _find_jobs_array(item, depth + 1)
            if found:
                return found
    if isinstance(obj, dict):
        for val in obj.values():
            found = _find_jobs_array(val, depth + 1)
            if found:
                return found
    return []


def _parse_job(raw: dict) -> RawJob | None:
    title = (raw.get("title") or raw.get("jobTitle") or "").strip()
    if not title:
        return None

    company_obj = raw.get("company") or raw.get("startup") or {}
    company = (
        company_obj.get("name") if isinstance(company_obj, dict) else None
    ) or raw.get("companyName") or ""

    job_id = str(raw.get("id") or raw.get("slug") or "")
    slug = raw.get("slug") or job_id
    company_slug = (
        company_obj.get("slug") if isinstance(company_obj, dict) else None
    ) or ""
    url = raw.get("url") or (
        f"{_BASE}/jobs/{company_slug}/{slug}" if company_slug and slug else ""
    )

    location_obj = raw.get("location") or raw.get("locationData") or {}
    location = (
        location_obj.get("displayName") if isinstance(location_obj, dict) else None
    ) or raw.get("locationName") or raw.get("location") or None
    if isinstance(location, dict):
        location = location.get("displayName") or None

    description = raw.get("description") or raw.get("jobDescription") or ""
    if description and "<" in description:
        try:
            description = BeautifulSoup(description, "html.parser").get_text(separator="\n").strip()
        except Exception:
            pass

    remote = raw.get("remote") or raw.get("isRemote") or False
    remote_policy = "remote" if remote else _infer_remote(str(location or ""))

    return RawJob(
        source="wellfound",
        source_id=f"wellfound:{job_id}" if job_id else f"wellfound:{hash(url)}",
        title=title,
        company=company or None,
        location=str(location) if location else None,
        remote_policy=remote_policy,
        description=description[:30_000] if description else None,
        url=url or None,
    )


def _infer_remote(location: str) -> str | None:
    if "remote" in location.lower():
        return "remote"
    return None


__all__ = ["WellfoundSource"]
