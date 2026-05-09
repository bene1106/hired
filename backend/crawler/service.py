"""Crawl orchestrator — fetches via a ``JobSource``, dedupes, persists.

This is the single chokepoint Phase 4 callers (the API route, eval scripts)
go through. It separates source-specific scraping from the persistence
layer so adding StepStone/Indeed in a later phase is just a new
``JobSource`` subclass.

Dedup contract: ``(source, source_id)`` is unique. We check the DB before
insert rather than relying on the unique constraint to throw — that gives
us a clean count of new vs. duplicate without rolling back per row.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import select

from db.models import Job
from db.session import get_session

from .base import CrawlQuery, JobSource, RawJob

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Summary of a single crawl invocation."""

    source: str
    fetched: int = 0
    new: int = 0
    duplicates: int = 0
    new_job_ids: list[int] = field(default_factory=list)
    error: str | None = None


def crawl(source: JobSource, query: CrawlQuery) -> CrawlResult:
    """Fetch jobs from ``source``, deduplicate against the DB, persist new ones.

    Returns a ``CrawlResult`` summarizing what happened. Never raises for
    routine "source returned nothing" cases — the caller decides what to
    show the user. Hard errors propagate as ``error`` strings so the
    background-task wrapper can surface them in the status endpoint.
    """
    result = CrawlResult(source=source.name)

    try:
        raw_jobs = list(source.fetch_jobs(query))
    except Exception as exc:  # noqa: BLE001 — sources have varied failure modes
        result.error = f"{type(exc).__name__}: {exc}"
        logger.warning("Crawl failed for source=%s: %s", source.name, result.error)
        return result

    result.fetched = len(raw_jobs)
    if not raw_jobs:
        return result

    with get_session() as session:
        existing = _existing_source_ids(session, source.name, [j.source_id for j in raw_jobs])
        for raw in raw_jobs:
            if raw.source_id in existing:
                result.duplicates += 1
                continue
            row = _to_row(raw)
            session.add(row)
            session.flush()  # populate row.id without committing the whole batch
            result.new_job_ids.append(row.id)
            result.new += 1
            existing.add(raw.source_id)
        session.commit()

    logger.info(
        "Crawl finished: source=%s fetched=%d new=%d duplicates=%d",
        source.name,
        result.fetched,
        result.new,
        result.duplicates,
    )
    return result


def _existing_source_ids(session, source: str, source_ids: list[str]) -> set[str]:
    if not source_ids:
        return set()
    rows = session.execute(
        select(Job.source_id).where(Job.source == source, Job.source_id.in_(source_ids))
    ).all()
    return {row[0] for row in rows}


def _to_row(raw: RawJob) -> Job:
    return Job(
        source=raw.source,
        source_id=raw.source_id,
        title=raw.title,
        company=raw.company,
        location=raw.location,
        remote_policy=raw.remote_policy,
        salary_min=raw.salary_min,
        salary_max=raw.salary_max,
        currency=raw.currency,
        description=raw.description,
        url=raw.url,
        posted_at=raw.posted_at,
    )


__all__ = ["CrawlResult", "crawl"]
