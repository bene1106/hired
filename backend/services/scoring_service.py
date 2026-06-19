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

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from db.models import Application, Job, JobInteraction
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
        heuristics, llm_ctx = _build_feedback_context(session)

    if (
        llm_ctx["positive_titles"]
        or llm_ctx["negative_titles"]
        or llm_ctx["rejected_skills"]
        or llm_ctx["liked_skills"]
    ):
        feedback_str = "\n\n--- USER FEEDBACK PREFERENCES ---\n"
        if llm_ctx["positive_titles"]:
            titles = ", ".join(llm_ctx["positive_titles"])
            feedback_str += f"The user recently LIKED jobs with these titles: {titles}\n"
        if llm_ctx["negative_titles"]:
            titles = ", ".join(llm_ctx["negative_titles"])
            feedback_str += f"The user recently REJECTED jobs with these titles: {titles}\n"
        if llm_ctx["rejected_skills"]:
            skills = ", ".join(llm_ctx["rejected_skills"])
            feedback_str += (
                f"The user explicitly REJECTED jobs because they require these skills: {skills}\n"
            )
        if llm_ctx["liked_skills"]:
            skills = ", ".join(llm_ctx["liked_skills"])
            feedback_str += (
                f"The user explicitly LIKED jobs because they feature these skills: {skills}\n"
            )
        feedback_str += (
            "Please heavily penalize jobs that match the rejected titles or skills, "
            "and boost jobs matching the liked titles or skills."
        )
        llm_profile.cv_text = (llm_profile.cv_text or "") + feedback_str

    to_score = [j for j in jobs if j.id not in cached]
    fresh: dict[int, ScoreResult] = {}
    if to_score:
        fresh = _score_in_parallel(provider, llm_profile, to_score, batch_size)

        # Apply heuristics to fresh scores
        for job in to_score:
            result = fresh.get(job.id)
            if result is None:
                continue

            if job.company and job.company in heuristics["companies"]:
                result.score = max(0, result.score - 25)
                result.red_flags.append("You previously rejected this employer")

            if job.company and job.company in heuristics["positive_companies"]:
                result.score = min(100, result.score + 25)

            if job.location and job.location in heuristics["locations"]:
                result.score = max(0, result.score - 25)
                result.red_flags.append(f"You explicitly rejected the location: {job.location}")

            if job.location and job.location in heuristics["positive_locations"]:
                result.score = min(100, result.score + 25)

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


def _build_feedback_context(session: Session) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    # Heuristics: companies with >= 5 net negative votes
    stmt = (
        select(Job.company, func.sum(JobInteraction.feedback_signal).label("net_votes"))
        .join(JobInteraction, JobInteraction.job_id == Job.id)
        .where(Job.company.is_not(None))
        .group_by(Job.company)
    )
    rows = session.execute(stmt).all()
    heuristic_companies = {
        row.company for row in rows if row.net_votes is not None and row.net_votes <= -5
    }

    # Explicit company rejections >= 2
    stmt2 = (
        select(Job.company, func.count(JobInteraction.id).label("rejections"))
        .join(JobInteraction, JobInteraction.job_id == Job.id)
        .where(
            JobInteraction.feedback_signal == -1,
            JobInteraction.feedback_reason == "company",
            Job.company.is_not(None),
        )
        .group_by(Job.company)
    )
    rows2 = session.execute(stmt2).all()
    heuristic_companies.update({row.company for row in rows2 if row.rejections >= 2})

    # Positive companies
    stmt2_pos = (
        select(Job.company)
        .join(JobInteraction, JobInteraction.job_id == Job.id)
        .where(
            JobInteraction.feedback_signal == 1,
            JobInteraction.feedback_reason == "company",
            Job.company.is_not(None),
        )
    )
    positive_companies = {row.company for row in session.execute(stmt2_pos).all()}

    # Locations explicitly rejected
    stmt3 = (
        select(Job.location)
        .join(JobInteraction, JobInteraction.job_id == Job.id)
        .where(
            JobInteraction.feedback_signal == -1,
            JobInteraction.feedback_reason == "location",
            Job.location.is_not(None),
        )
    )
    rows3 = session.execute(stmt3).all()
    heuristic_locations = {row.location for row in rows3}

    # Locations explicitly liked
    stmt3_pos = (
        select(Job.location)
        .join(JobInteraction, JobInteraction.job_id == Job.id)
        .where(
            JobInteraction.feedback_signal == 1,
            JobInteraction.feedback_reason == "location",
            Job.location.is_not(None),
        )
    )
    positive_locations = {row.location for row in session.execute(stmt3_pos).all()}

    # LLM context: last 5 positive titles
    stmt_pos = (
        select(Job.title)
        .join(JobInteraction, JobInteraction.job_id == Job.id)
        .where(JobInteraction.feedback_signal == 1)
        .order_by(desc(JobInteraction.updated_at))
        .limit(5)
    )
    pos_titles = [row.title for row in session.execute(stmt_pos).all()]

    # LLM context: last 5 negative titles
    stmt_neg = (
        select(Job.title)
        .join(JobInteraction, JobInteraction.job_id == Job.id)
        .where(JobInteraction.feedback_signal == -1, JobInteraction.feedback_reason.is_(None))
        .order_by(desc(JobInteraction.updated_at))
        .limit(5)
    )
    neg_titles = [row.title for row in session.execute(stmt_neg).all()]

    # LLM context: top 10 rejected skills
    stmt_skills = (
        select(JobScoreRow.rationale_json)
        .join(JobInteraction, JobInteraction.job_id == JobScoreRow.job_id)
        .where(JobInteraction.feedback_signal == -1, JobInteraction.feedback_reason == "tech_stack")
    )
    skill_rows = session.execute(stmt_skills).all()
    from collections import Counter

    skill_counter = Counter()
    for row in skill_rows:
        if row.rationale_json and "matched_skills" in row.rationale_json:
            skill_counter.update(row.rationale_json["matched_skills"])
    top_rejected_skills = [skill for skill, count in skill_counter.most_common(10)]

    # LLM context: top 10 liked skills
    stmt_skills_pos = (
        select(JobScoreRow.rationale_json)
        .join(JobInteraction, JobInteraction.job_id == JobScoreRow.job_id)
        .where(JobInteraction.feedback_signal == 1, JobInteraction.feedback_reason == "tech_stack")
    )
    skill_rows_pos = session.execute(stmt_skills_pos).all()
    skill_counter_pos = Counter()
    for row in skill_rows_pos:
        if row.rationale_json and "matched_skills" in row.rationale_json:
            skill_counter_pos.update(row.rationale_json["matched_skills"])
    top_liked_skills = [skill for skill, count in skill_counter_pos.most_common(10)]

    return (
        {
            "companies": heuristic_companies,
            "locations": heuristic_locations,
            "positive_companies": positive_companies,
            "positive_locations": positive_locations,
        },
        {
            "positive_titles": pos_titles,
            "negative_titles": neg_titles,
            "rejected_skills": top_rejected_skills,
            "liked_skills": top_liked_skills,
        },
    )


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
