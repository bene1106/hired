"""Scoring pipeline — calls ``LLMProvider.score_job`` and persists results.

Three concerns live here:

1. **Cache lookup.** Before calling the provider, check ``job_scores`` for
   a row at the current ``(profile_version, job_id)``. If one exists,
   return it. This is what protects the feed against re-scoring on every
   page load.
2. **Batched parallel scoring.** The provider call is blocking (HTTPS to
   Anthropic), so we run a small thread pool — five concurrent calls is
   plenty for the 20-job MVP and well below any provider rate limit.
3. **Persistence.** New ``ScoreResult`` rows are written in a single
   commit per batch.

The function is profile-version-aware: when the user edits their profile,
``profile_version`` bumps and old cache rows are simply ignored. They are
not deleted — keeping the history is cheap and useful for the eval
harness later.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Application, Job
from db.models import JobScore as JobScoreRow
from db.models import Profile as ProfileRow
from db.session import get_session
from llm import LLMProvider
from llm.types import ScoreResult

from .profile_mapper import job_row_to_llm, profile_row_to_llm

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 5


@dataclass
class ScoredJob:
    """One row in the feed: the persisted job + its score + any user action."""

    job: Job
    score: int
    rationale: str
    matched_skills: list[str]
    missing_skills: list[str]
    red_flags: list[str]
    status: str | None  # None = no action yet; otherwise applied/saved/skipped


def score_jobs(
    provider: LLMProvider,
    job_ids: list[int],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[ScoredJob]:
    """Score ``job_ids`` against the current profile, using the cache when possible.

    Returns one ``ScoredJob`` per id in the same order. If a job_id doesn't
    exist (e.g., deleted between dispatch and scoring), it is silently
    dropped from the result.
    """
    if not job_ids:
        return []

    with get_session() as session:
        profile = _read_profile(session)
        if profile is None:
            raise ScoringError("No profile saved yet — cannot score jobs.")
        profile_version = profile.profile_version
        llm_profile = profile_row_to_llm(profile)
        jobs = _load_jobs(session, job_ids)
        cached = _load_cached_scores(session, profile_version, [j.id for j in jobs])

    to_score = [j for j in jobs if j.id not in cached]
    fresh: dict[int, ScoreResult] = {}
    if to_score:
        fresh = _score_in_parallel(provider, llm_profile, to_score, batch_size)
        with get_session() as session:
            for job in to_score:
                result = fresh.get(job.id)
                if result is None:
                    continue
                session.add(
                    JobScoreRow(
                        job_id=job.id,
                        profile_version=profile_version,
                        score=result.score,
                        rationale_json=result.model_dump(),
                    )
                )
            session.commit()

    with get_session() as session:
        statuses = _load_statuses(session, [j.id for j in jobs])

    out: list[ScoredJob] = []
    for job in jobs:
        result = cached.get(job.id) or fresh.get(job.id)
        if result is None:
            continue
        out.append(
            ScoredJob(
                job=job,
                score=result.score,
                rationale=result.rationale,
                matched_skills=list(result.matched_skills),
                missing_skills=list(result.missing_skills),
                red_flags=list(result.red_flags),
                status=statuses.get(job.id),
            )
        )
    return out


class ScoringError(RuntimeError):
    """Raised when scoring is impossible (no profile, etc.)."""


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _read_profile(session: Session) -> ProfileRow | None:
    return session.execute(select(ProfileRow).limit(1)).scalar_one_or_none()


def _load_jobs(session: Session, job_ids: list[int]) -> list[Job]:
    rows = session.execute(select(Job).where(Job.id.in_(job_ids))).scalars().all()
    by_id = {row.id: row for row in rows}
    # Preserve caller order — the feed cares about it.
    return [by_id[i] for i in job_ids if i in by_id]


def _load_cached_scores(
    session: Session, profile_version: int, job_ids: list[int]
) -> dict[int, ScoreResult]:
    if not job_ids:
        return {}
    rows = (
        session.execute(
            select(JobScoreRow)
            .where(
                JobScoreRow.profile_version == profile_version,
                JobScoreRow.job_id.in_(job_ids),
            )
            .order_by(JobScoreRow.scored_at.desc())
        )
        .scalars()
        .all()
    )
    out: dict[int, ScoreResult] = {}
    for row in rows:
        if row.job_id in out:
            continue  # keep the most recent (DESC ordered)
        payload = row.rationale_json or {}
        try:
            out[row.job_id] = ScoreResult.model_validate(
                {**payload, "score": payload.get("score", row.score)}
            )
        except Exception:  # noqa: BLE001 — corrupt cache row, ignore and re-score
            logger.warning("Discarding corrupt cached score for job_id=%s", row.job_id)
    return out


def _load_statuses(session: Session, job_ids: list[int]) -> dict[int, str]:
    if not job_ids:
        return {}
    rows = session.execute(
        select(Application.job_id, Application.status).where(Application.job_id.in_(job_ids))
    ).all()
    return {job_id: status for job_id, status in rows}


def _score_in_parallel(
    provider: LLMProvider,
    llm_profile,
    jobs: list[Job],
    batch_size: int,
) -> dict[int, ScoreResult]:
    """Run ``provider.score_job`` over ``jobs`` with bounded concurrency."""
    out: dict[int, ScoreResult] = {}

    def _one(job: Job) -> tuple[int, ScoreResult | None]:
        try:
            llm_job = job_row_to_llm(job)
            return job.id, provider.score_job(llm_profile, llm_job)
        except Exception as exc:  # noqa: BLE001 — one bad job shouldn't kill the batch
            logger.warning("score_job failed for job_id=%s: %s", job.id, exc)
            return job.id, None

    with ThreadPoolExecutor(max_workers=max(1, batch_size)) as pool:
        for job_id, result in pool.map(_one, jobs):
            if result is not None:
                out[job_id] = result
    return out


__all__ = ["DEFAULT_BATCH_SIZE", "ScoredJob", "ScoringError", "score_jobs"]
