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
USER_AGENT = "Mozilla/5.0 (compatible; HiredApp/0.1; +https://github.com/bene1106/hired)"
MAX_DESCRIPTION_CHARS = 30_000

# Separators that commonly join a role and an employer in <title> / og:title:
# "Backend Engineer at AcmeCo", "Senior SRE - Remote - Bitpanda".
# " at " is matched first-occurrence; the punctuation forms are matched
# last-occurrence, because roles legitimately contain hyphens and pipes.
_TITLE_SEP_FIRST = (" at ", " @ ")
_TITLE_SEP_LAST = (" — ", " – ", " | ", " :: ", " • ", " - ")

# ATS hosts that carry the employer in the first path segment
# (boards.greenhouse.io/acme) rather than in the domain.
_ATS_PATH_HOSTS = frozenset(
    {
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "jobs.lever.co",
        "jobs.ashbyhq.com",
        "apply.workable.com",
    }
)

# Aggregators whose domain says nothing about the employer — guessing
# "Linkedin" as the company is worse than leaving it blank.
_GENERIC_HOSTS = frozenset(
    {
        "linkedin.com",
        "indeed.com",
        "glassdoor.com",
        "stepstone.de",
        "xing.com",
        "remotive.com",
        "wellfound.com",
        "angel.co",
        "google.com",
    }
)

# Subdomains that front a careers site without naming the employer.
_CAREER_SUBDOMAINS = frozenset(
    {"jobs", "job", "careers", "career", "apply", "boards", "job-boards", "www", "hiring"}
)


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
    # Well-formed JSON-LD usually names the org, but plenty of postings omit
    # hiringOrganization entirely — fall back to the URL rather than '?'.
    company = _extract_org_name(entry.get("hiringOrganization")) or _company_from_url(url)
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
    raw_title = _meta(soup, "og:title") or (soup.title.string.strip() if soup.title else "")
    description = _meta(soup, "og:description") or ""
    if not description:
        body = soup.find("main") or soup.find("article") or soup.body or soup
        description = body.get_text(separator="\n", strip=True)

    title, company_hint = _split_title_company(raw_title)
    company = _meta(soup, "og:site_name") or company_hint or _company_from_url(url)
    location = _meta(soup, "job:location")  # rare but harmless when absent

    # Some sites set og:title to the employer alone (Bitpanda, issue #20), so
    # the "title" we just derived is really the company. Prefer the page's h1.
    if company and title and title.casefold() == company.casefold():
        heading = soup.find("h1")
        heading_title, _ = _split_title_company(heading.get_text(strip=True) if heading else "")
        title = heading_title

    title = title or "(untitled role)"

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
    tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
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


def _split_title_company(raw: str) -> tuple[str, str | None]:
    """Split "Backend Engineer at AcmeCo" into ("Backend Engineer", "AcmeCo").

    Job pages routinely stuff the employer into og:title. Carrying that
    through means the feed shows "Backend Engineer at AcmeCo" as the role
    (issue #20), and it hides a company name we could otherwise recover.
    """
    text = (raw or "").strip()
    if not text:
        return "", None

    for sep in _TITLE_SEP_FIRST:
        if sep in text:
            left, right = text.split(sep, 1)
            if left.strip() and right.strip():
                return left.strip(), right.strip()

    for sep in _TITLE_SEP_LAST:
        if sep in text:
            left, right = text.rsplit(sep, 1)
            if left.strip() and right.strip():
                return left.strip(), right.strip()

    return text, None


def _titleize(slug: str) -> str:
    cleaned = re.sub(r"[-_]+", " ", slug).strip()
    # Title-case only all-lowercase slugs, so a source that already carries
    # casing keeps it. Hostnames are always lowercase, so "sumup" becomes
    # "Sumup" rather than "SumUp" — a guess, and a clearly better one than '?'.
    return cleaned.title() if cleaned.islower() else cleaned


def _company_from_url(url: str) -> str | None:
    """Last-resort employer guess from the URL.

    The parser frequently finds no company at all, which renders as '?' in
    CompanyMark across feed, Kanban and materials (issue #19). A hostname is
    a far better guess than nothing for the common case of a company-hosted
    or ATS-hosted posting.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower().removeprefix("www.")
    if not host:
        return None

    if host in _ATS_PATH_HOSTS:
        segments = [s for s in parsed.path.split("/") if s]
        return _titleize(segments[0]) if segments else None

    # Aggregators: no useful signal in the domain.
    if any(host == g or host.endswith("." + g) for g in _GENERIC_HOSTS):
        return None

    labels = host.split(".")
    if len(labels) < 2:
        return None
    # Drop the TLD, then any careers-y subdomain prefix: jobs.bitpanda.com → bitpanda
    meaningful = [lab for lab in labels[:-1] if lab not in _CAREER_SUBDOMAINS]
    if not meaningful:
        return None
    return _titleize(meaningful[-1])


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
