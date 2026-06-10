"""Remotive public API source.

Fetches remote jobs from remotive.com/api/remote-jobs — no authentication
required. Filters by the user's target roles via the ``search`` parameter.
Description is HTML; we strip tags to plain text before storing.
"""

from __future__ import annotations

import contextlib
import logging
import re
from collections.abc import Iterable
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup

from .base import CrawlQuery, JobSource, RawJob

logger = logging.getLogger(__name__)

_API = "https://remotive.com/api/remote-jobs"
_TIMEOUT = 20.0
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class RemotiveSource(JobSource):
    """Fetches remote jobs from remotive.com using profile role keywords."""

    name = "remotive"

    def fetch_jobs(self, query: CrawlQuery) -> Iterable[RawJob]:
        role = query.target_roles[0] if query.target_roles else "Software Engineer"

        params = {"search": role, "limit": min(query.max_jobs, 100)}
        try:
            with httpx.Client(
                headers={"User-Agent": _UA}, timeout=_TIMEOUT, follow_redirects=True
            ) as client:
                resp = client.get(_API, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Remotive fetch failed: %s", exc)
            return

        jobs = data.get("jobs") or []
        for item in jobs[: query.max_jobs]:
            job = _parse_job(item)
            if job is not None:
                yield job


def _parse_job(item: dict) -> RawJob | None:
    job_id = item.get("id")
    title = (item.get("title") or "").strip()
    if not job_id or not title:
        return None

    company = (item.get("company_name") or "").strip() or None
    location = (item.get("candidate_required_location") or "").strip() or None
    url = (item.get("url") or "").strip() or None
    salary_str = (item.get("salary") or "").strip()
    salary_min, salary_max, currency = _parse_salary(salary_str)
    description_html = item.get("description") or ""
    description = BeautifulSoup(description_html, "html.parser").get_text("\n").strip() or None

    pub_date: datetime | None = None
    pub_str = item.get("publication_date") or ""
    if pub_str:
        with contextlib.suppress(ValueError):
            pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).astimezone(UTC)

    return RawJob(
        source="remotive",
        source_id=str(job_id),
        title=title,
        company=company,
        location=location,
        remote_policy="remote",
        salary_min=salary_min,
        salary_max=salary_max,
        currency=currency,
        description=description[:30_000] if description else None,
        url=url,
        posted_at=pub_date,
    )


def _parse_salary(raw: str) -> tuple[int | None, int | None, str | None]:
    """Best-effort parse of free-form salary strings like '$80k-$120k USD'."""
    if not raw:
        return None, None, None
    currency: str | None = None
    if "$" in raw or "USD" in raw.upper():
        currency = "USD"
    elif "€" in raw or "EUR" in raw.upper():
        currency = "EUR"
    elif "£" in raw or "GBP" in raw.upper():
        currency = "GBP"

    nums = re.findall(r"[\d,]+(?:\.\d+)?[kK]?", raw)
    values: list[int] = []
    for n in nums:
        n = n.replace(",", "")
        if n.lower().endswith("k"):
            with contextlib.suppress(ValueError):
                values.append(int(float(n[:-1]) * 1000))
        else:
            with contextlib.suppress(ValueError):
                v = int(float(n))
                if v > 100:  # ignore noise like "2024"
                    values.append(v)

    if len(values) >= 2:
        return min(values), max(values), currency
    if len(values) == 1:
        return values[0], None, currency
    return None, None, currency


__all__ = ["RemotiveSource"]
