"""Crawl orchestrator — fetches via a ``JobSource``, dedupes, persists.

This is the single chokepoint Phase 4 callers (the API route, eval scripts)
go through. It separates source-specific scraping from the persistence
layer so adding StepStone/Indeed in a later phase is just a new
``JobSource`` subclass.

Dedup contract: ``(source, source_id)`` is unique. We check the DB before
insert rather than relying on the unique constraint to throw — that gives
us a clean count of new vs. duplicate without rolling back per row.

v0.3.5: a duplicate match no longer ends the line for a job. We also
check whether the existing row already has a ``JobScore`` at the user's
current ``profile_version`` — if not, the job id is forwarded to the
caller via ``rescore_job_ids`` so the pipeline can score it against
the current profile. Before this fix, re-onboarding (which bumps
``profile_version``) plus a re-paste of an already-known URL would
leave the job permanently un-scored in the feed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import select

from db.models import Job, JobScore
from db.models import Profile as ProfileRow
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
    # v0.3.5: job ids that were already in the DB but lacked a score at
    # the current ``profile_version``. The caller scores these alongside
    # ``new_job_ids`` so a re-onboarding + re-paste-URL flow doesn't
    # produce an empty feed.
    rescore_job_ids: list[int] = field(default_factory=list)
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
        existing_map = _existing_source_id_map(
            session, source.name, [j.source_id for j in raw_jobs]
        )
        profile_version = _current_profile_version(session)
        scored_at_current = _job_ids_scored_at(
            session, profile_version, list(existing_map.values())
        )

        for raw in raw_jobs:
            if raw.source_id in existing_map:
                result.duplicates += 1
                job_id = existing_map[raw.source_id]
                if job_id not in scored_at_current:
                    result.rescore_job_ids.append(job_id)
                continue
            row = _to_row(raw)
            session.add(row)
            session.flush()  # populate row.id without committing the whole batch
            result.new_job_ids.append(row.id)
            result.new += 1
            existing_map[raw.source_id] = row.id
        session.commit()

    logger.info(
        "Crawl finished: source=%s fetched=%d new=%d duplicates=%d rescore=%d",
        source.name,
        result.fetched,
        result.new,
        result.duplicates,
        len(result.rescore_job_ids),
    )
    return result


def _existing_source_id_map(session, source: str, source_ids: list[str]) -> dict[str, int]:
    """Return a ``source_id → job_id`` map for rows that already exist.

    v0.3.5 replaces the v0.1 ``_existing_source_ids`` (set-of-source_ids)
    so the crawler can identify which ``Job`` rows correspond to the
    duplicates it just saw and feed their ids back to scoring.
    """
    if not source_ids:
        return {}
    rows = session.execute(
        select(Job.source_id, Job.id).where(Job.source == source, Job.source_id.in_(source_ids))
    ).all()
    return {source_id: job_id for source_id, job_id in rows}


def _current_profile_version(session) -> int:
    row = session.execute(select(ProfileRow.profile_version).limit(1)).scalar_one_or_none()
    return row or 0


def _job_ids_scored_at(session, profile_version: int, job_ids: list[int]) -> set[int]:
    """Subset of ``job_ids`` that already have a JobScore at ``profile_version``."""
    if not job_ids:
        return set()
    rows = session.execute(
        select(JobScore.job_id).where(
            JobScore.profile_version == profile_version,
            JobScore.job_id.in_(job_ids),
        )
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
