"""Lever public job postings API source.

Fetches all published positions from api.lever.co/v0/postings/{slug}?mode=json.
No authentication required. Each posting includes full HTML description which
we strip to plain text and reassemble from multiple content sections.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from .base import CrawlQuery, JobSource, RawJob
from .location_filter import location_matches

logger = logging.getLogger(__name__)

_API_BASE = "https://api.lever.co/v0/postings"
_TIMEOUT = 20.0
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class LeverSource(JobSource):
    """Fetches every published posting from a Lever company board."""

    name = "lever"

    def __init__(self, company_slug: str) -> None:
        self.company_slug = company_slug.strip().lower()

    def fetch_jobs(self, query: CrawlQuery) -> Iterable[RawJob]:
        url = f"{_API_BASE}/{self.company_slug}?mode=json"
        try:
            with httpx.Client(headers={"User-Agent": _UA}, timeout=_TIMEOUT, follow_redirects=True) as client:
                company_name = _fetch_company_name(self.company_slug, client)
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Lever fetch failed for slug=%s: %s", self.company_slug, exc)
            return

        if not isinstance(data, list):
            logger.warning("Lever returned unexpected shape for slug=%s", self.company_slug)
            return

        for raw in data:
            job = self._parse(raw, company_name)
            if job is not None and location_matches(
                job.location, job.remote_policy, query.target_locations
            ):
                yield job

    def _parse(self, raw: dict, company_name: str | None = None) -> RawJob | None:
        title = (raw.get("text") or "").strip()
        if not title:
            return None

        job_id = raw.get("id") or ""
        hosted_url = raw.get("hostedUrl") or f"https://jobs.lever.co/{self.company_slug}/{job_id}"

        cats = raw.get("categories") or {}
        location = cats.get("location") or None

        # Assemble description from all content sections
        parts: list[str] = []
        for key in ("descriptionPlain", "description"):
            text = raw.get(key) or ""
            if text:
                if "<" in text:
                    try:
                        text = BeautifulSoup(text, "html.parser").get_text(separator="\n").strip()
                    except Exception:
                        pass
                parts.append(text)
                break

        for section in raw.get("lists") or []:
            if not isinstance(section, dict):
                continue
            label = section.get("text") or ""
            items = section.get("content") or ""
            if items and "<" in items:
                try:
                    items = BeautifulSoup(items, "html.parser").get_text(separator="\n").strip()
                except Exception:
                    pass
            chunk = "\n".join(x for x in (label, items) if x)
            if chunk:
                parts.append(chunk)

        additional = raw.get("additional") or ""
        if additional:
            if "<" in additional:
                try:
                    additional = BeautifulSoup(additional, "html.parser").get_text(separator="\n").strip()
                except Exception:
                    pass
            parts.append(additional)

        description = "\n\n".join(p for p in parts if p)

        posted_at: datetime | None = None
        created_ms = raw.get("createdAt")
        if isinstance(created_ms, (int, float)):
            try:
                posted_at = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
            except (ValueError, OSError):
                pass

        return RawJob(
            source=self.name,
            source_id=f"{self.company_slug}:{job_id}",
            title=title,
            company=company_name or self.company_slug.replace("-", " ").title(),
            location=location,
            remote_policy=_infer_remote(location),
            description=description[:30_000] if description else None,
            url=hosted_url,
            posted_at=posted_at,
        )


def _fetch_company_name(slug: str, client: httpx.Client) -> str | None:
    """Scrape the Lever jobs page to get the real company name from og:title."""
    try:
        resp = client.get(f"https://jobs.lever.co/{slug}", timeout=10.0)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # og:title is typically "Jobs at CompanyName"
        tag = soup.find("meta", attrs={"property": "og:title"})
        if tag:
            content = (tag.get("content") or "").strip()
            if content.lower().startswith("jobs at "):
                return content[8:].strip()
            if content:
                return content
        # Fallback: page <title>
        title_tag = soup.find("title")
        if title_tag:
            text = title_tag.get_text().strip()
            if text.lower().startswith("jobs at "):
                return text[8:].strip()
    except Exception:
        pass
    return None


def _infer_remote(location: str | None) -> str | None:
    if location and "remote" in location.lower():
        return "remote"
    return None


__all__ = ["LeverSource"]
