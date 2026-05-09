"""Manual URL paste source — the primary, reliable Phase 4 ingestion path.

The user pastes a list of job URLs (LinkedIn, Lever, Greenhouse, Workday,
or anything else) into the UI. We fetch each one, extract structured
metadata where possible (Open Graph + JobPosting JSON-LD), and fall back
to the raw page title + body text otherwise.

The LLM scoring layer is robust to messy descriptions — it doesn't need
clean structure, only enough text to reason about. Our job here is to
get that text into the DB without losing the URL of record.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Iterable
from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .base import CrawlQuery, JobSource, RawJob

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 15.0
USER_AGENT = (
    "Mozilla/5.0 (compatible; HiredApp/0.1; +https://github.com/bene1106/hired)"
)
MAX_DESCRIPTION_CHARS = 30_000


class ManualURLSource(JobSource):
    """Fetches a fixed list of job URLs supplied by the user."""

    name = "manual_url"

    def __init__(self, client: httpx.Client | None = None) -> None:
        # The injected client makes this cheap to test without spinning up
        # a real network stack — pass an httpx.Client(transport=MockTransport).
        self._client = client

    def fetch_jobs(self, query: CrawlQuery) -> Iterable[RawJob]:
        urls = [u.strip() for u in query.urls if u.strip()]
        if not urls:
            return
        urls = urls[: query.max_jobs]

        client = self._client or httpx.Client(
            timeout=DEFAULT_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        owns_client = self._client is None
        try:
            for url in urls:
                try:
                    job = self._fetch_one(client, url)
                except (httpx.HTTPError, ValueError) as exc:
                    logger.warning("Skipping %s: %s", url, exc)
                    continue
                if job is not None:
                    yield job
        finally:
            if owns_client:
                client.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _fetch_one(self, client: httpx.Client, url: str) -> RawJob | None:
        response = client.get(url)
        response.raise_for_status()
        html = response.text
        if not html.strip():
            return None
        return parse_html_to_job(html, url)


def parse_html_to_job(html: str, url: str) -> RawJob:
    """Best-effort job extraction from arbitrary HTML.

    Order of preference:
    1. JSON-LD ``JobPosting`` (Greenhouse, Lever, Workday, well-tagged sites)
    2. Open Graph + meta tags + page title fallbacks
    3. Page title + body text — never fails as long as the HTML parses
    """
    soup = BeautifulSoup(html, "html.parser")

    job = _try_json_ld(soup, url)
    if job is not None:
        return job

    return _fallback_meta(soup, url)


def _try_json_ld(soup: BeautifulSoup, url: str) -> RawJob | None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.string or script.get_text() or ""
        if not text.strip():
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            if entry.get("@type") != "JobPosting":
                continue
            return _from_json_ld(entry, url)
    return None


def _from_json_ld(entry: dict, url: str) -> RawJob:
    title = (entry.get("title") or "").strip() or "(untitled role)"
    company = _extract_org_name(entry.get("hiringOrganization"))
    location = _extract_location(entry.get("jobLocation"))
    remote_policy = _normalize_remote_policy(entry)
    salary_min, salary_max, currency = _extract_salary(entry.get("baseSalary"))
    description = _strip_html(entry.get("description") or "")
    posted_at = _parse_iso(entry.get("datePosted"))

    return RawJob(
        source=ManualURLSource.name,
        source_id=_url_to_source_id(url),
        title=title,
        company=company,
        location=location,
        remote_policy=remote_policy,
        salary_min=salary_min,
        salary_max=salary_max,
        currency=currency,
        description=_truncate(description),
        url=url,
        posted_at=posted_at,
    )


def _fallback_meta(soup: BeautifulSoup, url: str) -> RawJob:
    title = _meta(soup, "og:title") or (soup.title.string.strip() if soup.title else "(untitled)")
    description = _meta(soup, "og:description") or ""
    if not description:
        body = soup.find("main") or soup.find("article") or soup.body or soup
        description = body.get_text(separator="\n", strip=True)

    company = _meta(soup, "og:site_name")
    location = _meta(soup, "job:location")  # rare but harmless when absent

    return RawJob(
        source=ManualURLSource.name,
        source_id=_url_to_source_id(url),
        title=title.strip()[:512],
        company=company,
        location=location,
        description=_truncate(description),
        url=url,
    )


def _meta(soup: BeautifulSoup, prop: str) -> str | None:
    tag = soup.find("meta", attrs={"property": prop}) or soup.find(
        "meta", attrs={"name": prop}
    )
    if tag is None:
        return None
    content = tag.get("content")
    return content.strip() if content else None


def _strip_html(text: str) -> str:
    return BeautifulSoup(text, "html.parser").get_text(separator="\n", strip=True)


def _truncate(text: str) -> str:
    if len(text) > MAX_DESCRIPTION_CHARS:
        return text[:MAX_DESCRIPTION_CHARS]
    return text


def _extract_org_name(value: object) -> str | None:
    if isinstance(value, dict):
        name = value.get("name")
        return name.strip() if isinstance(name, str) else None
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return _extract_org_name(value[0])
    return None


def _extract_location(value: object) -> str | None:
    entries = value if isinstance(value, list) else [value]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        addr = entry.get("address")
        if isinstance(addr, dict):
            parts = [
                addr.get("addressLocality"),
                addr.get("addressRegion"),
                addr.get("addressCountry"),
            ]
            joined = ", ".join(p for p in parts if isinstance(p, str) and p.strip())
            if joined:
                return joined
        name = entry.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _normalize_remote_policy(entry: dict) -> str | None:
    job_location_type = entry.get("jobLocationType")
    if isinstance(job_location_type, str) and "telecommute" in job_location_type.lower():
        return "remote"
    title = (entry.get("title") or "").lower()
    description = (entry.get("description") or "").lower()
    if "remote" in title or "remote" in description[:500]:
        return "remote"
    if "hybrid" in title or "hybrid" in description[:500]:
        return "hybrid"
    return None


_SALARY_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def _extract_salary(value: object) -> tuple[int | None, int | None, str | None]:
    if not isinstance(value, dict):
        return None, None, None
    currency = value.get("currency") if isinstance(value.get("currency"), str) else None
    payload = value.get("value")
    if isinstance(payload, dict):
        return (
            _coerce_money(payload.get("minValue")),
            _coerce_money(payload.get("maxValue")),
            currency,
        )
    if isinstance(payload, (int, float)):
        amount = int(payload)
        return amount, amount, currency
    return None, None, currency


def _coerce_money(raw: object) -> int | None:
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str):
        match = _SALARY_NUMBER.search(raw.replace(",", ""))
        if match:
            try:
                return int(float(match.group(0)))
            except ValueError:
                return None
    return None


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        # Normalize trailing Z to +00:00 for fromisoformat in Python 3.11.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _url_to_source_id(url: str) -> str:
    """Stable, short, unique-per-URL ID. We keep the host visible for debug."""
    parsed = urlparse(url)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    host = parsed.netloc or "unknown"
    return f"{host}:{digest}"


__all__ = ["ManualURLSource", "parse_html_to_job"]
