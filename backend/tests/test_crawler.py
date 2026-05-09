"""Crawler tests — manual URL parsing, LinkedIn parsing, orchestrator dedup.

LinkedIn fetch is exercised with a fake page factory so no real network or
Playwright browser is required.
"""

from __future__ import annotations

from textwrap import dedent

import httpx
import pytest

from crawler.base import CrawlQuery
from crawler.linkedin import LinkedInSource, LinkedInUnavailable
from crawler.manual_urls import ManualURLSource, parse_html_to_job
from crawler.service import crawl
from db.migrations import run_migrations
from db.models import Job
from db.session import get_session
from sqlalchemy import select


# ---------------------------------------------------------------------------
# manual_urls — JSON-LD path
# ---------------------------------------------------------------------------

JSON_LD_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "JobPosting",
  "title": "Senior Backend Engineer",
  "description": "<p>Build distributed systems in Python.</p>",
  "datePosted": "2025-04-01T00:00:00Z",
  "hiringOrganization": {"@type": "Organization", "name": "AcmeCo"},
  "jobLocation": {
    "@type": "Place",
    "address": {
      "addressLocality": "Berlin",
      "addressCountry": "DE"
    }
  },
  "jobLocationType": "TELECOMMUTE",
  "baseSalary": {
    "@type": "MonetaryAmount",
    "currency": "EUR",
    "value": {"@type": "QuantitativeValue", "minValue": 70000, "maxValue": 90000}
  }
}
</script>
</head><body>Hello</body></html>
"""


def test_parse_html_to_job_extracts_json_ld() -> None:
    job = parse_html_to_job(JSON_LD_HTML, "https://acmeco.example/jobs/42")
    assert job.title == "Senior Backend Engineer"
    assert job.company == "AcmeCo"
    assert job.location == "Berlin, DE"
    assert job.remote_policy == "remote"
    assert job.salary_min == 70000
    assert job.salary_max == 90000
    assert job.currency == "EUR"
    assert "distributed systems" in (job.description or "")
    assert job.url == "https://acmeco.example/jobs/42"
    assert job.posted_at is not None
    assert job.source == "manual_url"
    # source_id is host-prefixed and stable
    assert job.source_id.startswith("acmeco.example:")


def test_parse_html_to_job_falls_back_to_meta_tags() -> None:
    html = dedent(
        """
        <html><head>
            <title>Job Title — AcmeCo</title>
            <meta property="og:title" content="Backend Engineer at AcmeCo">
            <meta property="og:description" content="We build APIs in Python.">
            <meta property="og:site_name" content="AcmeCo">
        </head><body><main>Backend engineering role.</main></body></html>
        """
    )
    job = parse_html_to_job(html, "https://acmeco.example/r/abc")
    assert job.title == "Backend Engineer at AcmeCo"
    assert job.company == "AcmeCo"
    assert "Python" in (job.description or "")


def test_parse_html_to_job_handles_minimal_html() -> None:
    job = parse_html_to_job("<html><body>Just a job</body></html>", "https://x.test/y")
    assert job.title == "(untitled)" or job.title  # never empty
    assert "Just a job" in (job.description or "")


def test_manual_url_source_uses_injected_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html=JSON_LD_HTML)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    source = ManualURLSource(client=client)
    query = CrawlQuery(urls=["https://acmeco.example/jobs/42"], max_jobs=10)

    jobs = list(source.fetch_jobs(query))
    assert len(jobs) == 1
    assert jobs[0].title == "Senior Backend Engineer"


def test_manual_url_source_skips_failing_urls() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "ok" in str(request.url):
            return httpx.Response(200, html=JSON_LD_HTML)
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = ManualURLSource(client=client)
    query = CrawlQuery(
        urls=["https://acmeco.example/ok/1", "https://acmeco.example/bad/2"], max_jobs=10
    )

    jobs = list(source.fetch_jobs(query))
    assert len(jobs) == 1


def test_manual_url_source_respects_max_jobs() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, html=JSON_LD_HTML)))
    source = ManualURLSource(client=client)
    query = CrawlQuery(
        urls=[f"https://acmeco.example/{i}" for i in range(10)], max_jobs=3
    )
    jobs = list(source.fetch_jobs(query))
    assert len(jobs) == 3


# ---------------------------------------------------------------------------
# LinkedIn — fake page factory; no real browser
# ---------------------------------------------------------------------------

LINKEDIN_HTML = """
<html><body>
<ul>
  <li>
    <div>
      <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/4111?ref=x">
        Backend Engineer
      </a>
      <h4 class="base-search-card__subtitle">AcmeCo</h4>
      <span class="job-search-card__location">Berlin, Germany</span>
    </div>
  </li>
  <li>
    <div>
      <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/4222">
        Senior Engineer
      </a>
      <h4 class="base-search-card__subtitle">BetaCorp</h4>
      <span class="job-search-card__location">Munich, Germany</span>
    </div>
  </li>
</ul>
</body></html>
"""


def test_linkedin_source_parses_search_html() -> None:
    source = LinkedInSource(
        delay_range=(0.0, 0.0),
        page_factory=lambda url: LINKEDIN_HTML,
    )
    query = CrawlQuery(target_roles=["Backend Engineer"], target_locations=["Berlin"], max_jobs=10)

    jobs = list(source.fetch_jobs(query))
    assert len(jobs) == 2
    assert jobs[0].source_id == "4111"
    assert jobs[0].company == "AcmeCo"
    assert jobs[0].location == "Berlin, Germany"
    assert jobs[1].source_id == "4222"


def test_linkedin_source_propagates_unavailable() -> None:
    def boom(url: str) -> str:
        raise LinkedInUnavailable("playwright not installed")

    source = LinkedInSource(delay_range=(0.0, 0.0), page_factory=boom)
    with pytest.raises(LinkedInUnavailable):
        list(source.fetch_jobs(CrawlQuery(max_jobs=1)))


def test_linkedin_source_respects_max_jobs() -> None:
    source = LinkedInSource(
        delay_range=(0.0, 0.0),
        page_factory=lambda url: LINKEDIN_HTML,
    )
    jobs = list(source.fetch_jobs(CrawlQuery(max_jobs=1)))
    assert len(jobs) == 1


# ---------------------------------------------------------------------------
# Orchestrator — dedup + persist
# ---------------------------------------------------------------------------


def test_crawl_persists_new_jobs_and_dedupes_on_repeat() -> None:
    run_migrations()

    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, html=JSON_LD_HTML))
    )
    source = ManualURLSource(client=client)
    query = CrawlQuery(urls=["https://acmeco.example/jobs/42"], max_jobs=5)

    first = crawl(source, query)
    assert first.fetched == 1
    assert first.new == 1
    assert first.duplicates == 0

    second = crawl(source, query)
    assert second.fetched == 1
    assert second.new == 0
    assert second.duplicates == 1

    with get_session() as session:
        rows = session.execute(select(Job)).scalars().all()
    assert len(rows) == 1
    assert rows[0].title == "Senior Backend Engineer"
    assert rows[0].source == "manual_url"


def test_crawl_returns_error_on_fetch_failure() -> None:
    run_migrations()

    class Boom:
        name = "boom"

        def fetch_jobs(self, query):
            raise RuntimeError("connection refused")

    result = crawl(Boom(), CrawlQuery(max_jobs=1))
    assert result.error is not None
    assert "connection refused" in result.error
    assert result.new == 0
