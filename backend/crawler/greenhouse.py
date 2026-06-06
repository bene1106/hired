"""Greenhouse public jobs-board API source.

Fetches all open positions from the public JSON endpoint at
boards-api.greenhouse.io/v1/boards/{slug}/jobs — no authentication required.
Each job card includes full HTML content which we strip to plain text.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .base import CrawlQuery, JobSource, RawJob
from .location_filter import location_matches

logger = logging.getLogger(__name__)

_API_BASE = "https://boards-api.greenhouse.io/v1/boards"
_TIMEOUT = 20.0
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class GreenhouseSource(JobSource):
    """Fetches every open job from a Greenhouse company board."""

    name = "greenhouse"

    def __init__(self, company_slug: str) -> None:
        self.company_slug = company_slug.strip().lower()

    def fetch_jobs(self, query: CrawlQuery) -> Iterable[RawJob]:
        url = f"{_API_BASE}/{self.company_slug}/jobs?content=true"
        try:
            with httpx.Client(headers={"User-Agent": _UA}, timeout=_TIMEOUT, follow_redirects=True) as client:
                company_name = _fetch_company_name(self.company_slug, client)
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Greenhouse fetch failed for slug=%s: %s", self.company_slug, exc)
            return

        for raw in data.get("jobs") or []:
            job = self._parse(raw, company_name)
            if job is not None and location_matches(
                job.location, job.remote_policy, query.target_locations
            ):
                yield job

    def _parse(self, raw: dict, company_name: str | None = None) -> RawJob | None:
        title = (raw.get("title") or "").strip()
        if not title:
            return None

        job_id = raw.get("id")
        url = raw.get("absolute_url") or f"https://boards.greenhouse.io/{self.company_slug}/jobs/{job_id}"

        loc_obj = raw.get("location") or {}
        location = loc_obj.get("name") if isinstance(loc_obj, dict) else None

        content = raw.get("content") or ""
        if content and "<" in content:
            try:
                content = BeautifulSoup(content, "html.parser").get_text(separator="\n").strip()
            except Exception:
                pass

        posted_at: datetime | None = None
        if raw.get("updated_at"):
            try:
                posted_at = datetime.fromisoformat(raw["updated_at"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        if not company_name:
            company_name = self.company_slug.replace("-", " ").title()

        return RawJob(
            source=self.name,
            source_id=f"{self.company_slug}:{job_id}",
            title=title,
            company=company_name,
            location=location,
            remote_policy=_infer_remote(location),
            description=content[:30_000] if content else None,
            url=url,
            posted_at=posted_at,
        )


def _fetch_company_name(slug: str, client: httpx.Client) -> str | None:
    """Call GET /v1/boards/{slug} to get the real company name."""
    try:
        resp = client.get(f"{_API_BASE}/{slug}")
        resp.raise_for_status()
        data = resp.json()
        name = data.get("name")
        return name.strip() if name else None
    except Exception:
        return None


def _infer_remote(location: str | None) -> str | None:
    if location and "remote" in location.lower():
        return "remote"
    return None


__all__ = ["GreenhouseSource"]
