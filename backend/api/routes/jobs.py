"""Phase 4 feed API — crawl trigger, status polling, ranked feed, actions.

Four endpoints:

- ``POST /api/jobs/crawl`` — kicks off a crawl + score pipeline as a
  FastAPI BackgroundTask. Returns a job id the UI polls.
- ``GET /api/jobs/crawl/status/{job_id}`` — current progress for a crawl.
  Note: progress state lives in an in-process dict and **resets on
  backend restart**. Acceptable for MVP per ADR-0006.
- ``GET /api/jobs/feed`` — ranked list of scored jobs, with filter by
  status (apply / save / skip / no-action).
- ``POST /api/jobs/{id}/action`` — record the user's apply/save/skip
  decision so the card leaves the main feed.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from api.dependencies import get_llm_provider
from crawler.base import CrawlQuery
from crawler.linkedin import LinkedInSource, LinkedInUnavailableError
from crawler.manual_urls import ManualURLSource
from crawler.service import crawl
from db.models import Application, Job
from db.models import JobScore as JobScoreRow
from db.models import Profile as ProfileRow
from db.session import get_session
from llm import LLMProvider
from services.crawl_progress import (
    CrawlPhase,
    CrawlState,
    create_entry,
    get_entry,
    update_entry,
)
from services.scoring_service import ScoringError, score_jobs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

ActionLiteral = Literal["apply", "save", "skip"]
_ACTION_TO_STATUS = {"apply": "applied", "save": "saved", "skip": "skipped"}
_VALID_STATUSES = set(_ACTION_TO_STATUS.values())

SourceLiteral = Literal["manual_url", "linkedin"]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CrawlRequest(BaseModel):
    source: SourceLiteral = "manual_url"
    urls: list[str] = Field(default_factory=list)
    max_jobs: int = Field(default=20, ge=1, le=100)


class CrawlResponse(BaseModel):
    job_id: str


class CrawlStatusResponse(BaseModel):
    job_id: str
    state: CrawlState
    phase: CrawlPhase | None
    fetched: int
    total: int
    new: int
    duplicates: int
    scored: int
    error: str | None


class FeedItem(BaseModel):
    job_id: int
    title: str
    company: str | None
    location: str | None
    remote_policy: str | None
    url: str | None
    score: int
    rationale: str
    matched_skills: list[str]
    missing_skills: list[str]
    red_flags: list[str]
    status: str | None  # None | applied | saved | skipped


class JobActionRequest(BaseModel):
    action: ActionLiteral


class JobActionResponse(BaseModel):
    job_id: int
    status: str


# ---------------------------------------------------------------------------
# POST /api/jobs/crawl
# ---------------------------------------------------------------------------


@router.post("/crawl", response_model=CrawlResponse)
def trigger_crawl(
    payload: CrawlRequest,
    background_tasks: BackgroundTasks,
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> CrawlResponse:
    if payload.source == "manual_url" and not payload.urls:
        raise HTTPException(
            status_code=400,
            detail="manual_url crawl requires at least one URL.",
        )

    entry = create_entry()
    background_tasks.add_task(
        _run_crawl_pipeline,
        job_id=entry.job_id,
        source=payload.source,
        urls=list(payload.urls),
        max_jobs=payload.max_jobs,
        provider=provider,
    )
    return CrawlResponse(job_id=entry.job_id)


@router.get("/crawl/status/{job_id}", response_model=CrawlStatusResponse)
def get_crawl_status(job_id: str) -> CrawlStatusResponse:
    entry = get_entry(job_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Unknown crawl job id.")
    return CrawlStatusResponse(
        job_id=entry.job_id,
        state=entry.state,
        phase=entry.phase,
        fetched=entry.fetched,
        total=entry.total,
        new=entry.new,
        duplicates=entry.duplicates,
        scored=entry.scored,
        error=entry.error,
    )


# ---------------------------------------------------------------------------
# GET /api/jobs/feed
# ---------------------------------------------------------------------------


@router.get("/feed", response_model=list[FeedItem])
def get_feed(
    limit: int = 20,
    min_score: int = 0,
    exclude_status: str | None = "skipped",
) -> list[FeedItem]:
    """Return scored jobs sorted by score descending.

    ``exclude_status=skipped`` (the default) hides skipped jobs from the
    main feed. Pass ``exclude_status=`` (empty) to see everything; pass
    a specific status to see only that bucket via the filter dropdown.
    """
    if limit < 1:
        limit = 20
    if limit > 100:
        limit = 100

    with get_session() as session:
        profile_version = _current_profile_version(session)
        latest_scores = _latest_scores_subquery(profile_version)

        rows = session.execute(
            select(Job, JobScoreRow, Application)
            .select_from(latest_scores)
            .join(JobScoreRow, JobScoreRow.id == latest_scores.c.score_id)
            .join(Job, Job.id == JobScoreRow.job_id)
            .outerjoin(Application, Application.job_id == Job.id)
            .where(JobScoreRow.score >= min_score)
            .order_by(desc(JobScoreRow.score), Job.id)
            .limit(limit)
        ).all()

    items: list[FeedItem] = []
    for job, score_row, application in rows:
        status = application.status if application else None
        if exclude_status and status == exclude_status:
            continue
        rationale_payload = score_row.rationale_json or {}
        items.append(
            FeedItem(
                job_id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                remote_policy=job.remote_policy,
                url=job.url,
                score=score_row.score,
                rationale=rationale_payload.get("rationale", ""),
                matched_skills=list(rationale_payload.get("matched_skills") or []),
                missing_skills=list(rationale_payload.get("missing_skills") or []),
                red_flags=list(rationale_payload.get("red_flags") or []),
                status=status,
            )
        )
    return items


# ---------------------------------------------------------------------------
# POST /api/jobs/{id}/action
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# GET /api/jobs/scoring-status  (v0.3.5)
# ---------------------------------------------------------------------------
#
# Drives the Feed empty-state copy: "No jobs yet. Click Crawl…" vs.
# "N jobs in the DB are missing scores against your current profile —
# re-score them." Without this endpoint the frontend can't tell the
# difference between "fresh install" and "you re-onboarded and your old
# jobs need a re-score."


class ScoringStatusResponse(BaseModel):
    jobs_total: int
    jobs_with_current_score: int
    rescore_candidate_count: int
    profile_version: int


@router.get("/scoring-status", response_model=ScoringStatusResponse)
def get_scoring_status() -> ScoringStatusResponse:
    with get_session() as session:
        profile_version = _current_profile_version(session)
        jobs_total = session.execute(select(func.count()).select_from(Job)).scalar_one()
        scored = session.execute(
            select(func.count(func.distinct(JobScoreRow.job_id))).where(
                JobScoreRow.profile_version == profile_version
            )
        ).scalar_one()
    return ScoringStatusResponse(
        jobs_total=jobs_total,
        jobs_with_current_score=scored,
        rescore_candidate_count=max(0, jobs_total - scored),
        profile_version=profile_version,
    )


# ---------------------------------------------------------------------------
# POST /api/jobs/rescore  (v0.3.5)
# ---------------------------------------------------------------------------
#
# Re-score every job that lacks a JobScore at the current profile_version.
# Used by the Feed's "Re-score existing jobs" button (shown only when
# jobs_total > 0 AND visible_count == 0). Synchronous + capped to keep the
# user-facing wait bounded; the LLM provider's RecordingProvider logs each
# row to ``provider_call_log`` so cost stays visible.


class RescoreResponse(BaseModel):
    rescored: int
    total_candidates: int
    capped: bool


_RESCORE_MAX_JOBS = 50


@router.post("/rescore", response_model=RescoreResponse)
def rescore_jobs(
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> RescoreResponse:
    with get_session() as session:
        profile_version = _current_profile_version(session)
        scored_ids = {
            row[0]
            for row in session.execute(
                select(JobScoreRow.job_id).where(JobScoreRow.profile_version == profile_version)
            ).all()
        }
        candidate_ids = [
            row[0] for row in session.execute(select(Job.id)).all() if row[0] not in scored_ids
        ]

    if not candidate_ids:
        return RescoreResponse(rescored=0, total_candidates=0, capped=False)

    total_candidates = len(candidate_ids)
    capped = total_candidates > _RESCORE_MAX_JOBS
    batch = candidate_ids[:_RESCORE_MAX_JOBS]

    try:
        scored = score_jobs(provider, batch)
    except ScoringError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Rescore complete: requested=%d total_candidates=%d capped=%s rescored=%d",
        len(batch),
        total_candidates,
        capped,
        len(scored),
    )
    return RescoreResponse(
        rescored=len(scored),
        total_candidates=total_candidates,
        capped=capped,
    )


@router.post("/{job_id}/action", response_model=JobActionResponse)
def post_job_action(job_id: int, payload: JobActionRequest) -> JobActionResponse:
    new_status = _ACTION_TO_STATUS[payload.action]
    with get_session() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Unknown job id.")
        application = session.execute(
            select(Application).where(Application.job_id == job_id)
        ).scalar_one_or_none()
        if application is None:
            application = Application(job_id=job_id, status=new_status)
            session.add(application)
        else:
            application.status = new_status
        session.commit()
        session.refresh(application)
    return JobActionResponse(job_id=job_id, status=new_status)


# ---------------------------------------------------------------------------
# Background pipeline
# ---------------------------------------------------------------------------


def _run_crawl_pipeline(
    *,
    job_id: str,
    source: SourceLiteral,
    urls: list[str],
    max_jobs: int,
    provider: LLMProvider,
) -> None:
    """Crawl, persist, score. Updates the in-process progress registry."""
    update_entry(job_id, state="running", phase="crawling", total=max_jobs)

    try:
        query = _build_query(urls=urls, max_jobs=max_jobs)
        crawl_source = _build_source(source)

        crawl_result = crawl(crawl_source, query)
    except LinkedInUnavailableError as exc:
        update_entry(
            job_id,
            state="error",
            error=f"LinkedIn is unavailable ({exc}). Paste URLs manually.",
        )
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Crawl pipeline failed")
        update_entry(job_id, state="error", error=f"{type(exc).__name__}: {exc}")
        return

    if crawl_result.error:
        update_entry(
            job_id,
            state="error",
            error=crawl_result.error,
            fetched=crawl_result.fetched,
            new=crawl_result.new,
            duplicates=crawl_result.duplicates,
        )
        return

    update_entry(
        job_id,
        fetched=crawl_result.fetched,
        new=crawl_result.new,
        duplicates=crawl_result.duplicates,
        new_job_ids=list(crawl_result.new_job_ids),
        total=max(crawl_result.fetched, max_jobs),
    )

    # v0.3.5: existing job rows whose score is at a stale profile_version
    # get rescored alongside fresh inserts. Before this fix, re-pasting a
    # known URL after re-onboarding (which bumps profile_version) hit the
    # dedup path and ended the pipeline at "scored=0" — the feed would
    # show an empty state even though the job was in the DB.
    ids_to_score = list(crawl_result.new_job_ids) + list(crawl_result.rescore_job_ids)
    if not ids_to_score:
        update_entry(job_id, state="done", phase=None, scored=0, finished_at=_utcnow())
        return

    update_entry(job_id, phase="scoring")
    try:
        scored = score_jobs(provider, ids_to_score)
    except ScoringError as exc:
        update_entry(job_id, state="error", error=str(exc), finished_at=_utcnow())
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scoring failed in crawl pipeline")
        update_entry(
            job_id, state="error", error=f"{type(exc).__name__}: {exc}", finished_at=_utcnow()
        )
        return

    update_entry(job_id, state="done", phase=None, scored=len(scored), finished_at=_utcnow())


def _build_query(*, urls: list[str], max_jobs: int) -> CrawlQuery:
    target_roles: list[str] = []
    target_locations: list[str] = []
    with get_session() as session:
        row = session.execute(select(ProfileRow).limit(1)).scalar_one_or_none()
        if row is not None:
            target_roles = list(row.target_roles_json or [])
            target_locations = list(row.target_locations_json or [])
    return CrawlQuery(
        target_roles=target_roles,
        target_locations=target_locations,
        max_jobs=max_jobs,
        urls=urls,
    )


def _build_source(source: SourceLiteral):
    if source == "manual_url":
        return ManualURLSource()
    if source == "linkedin":
        return LinkedInSource()
    raise HTTPException(status_code=400, detail=f"Unknown source '{source}'.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_profile_version(session: Session) -> int:
    row = session.execute(select(ProfileRow).limit(1)).scalar_one_or_none()
    return (row.profile_version or 0) if row else 0


def _latest_scores_subquery(profile_version: int):
    """Subquery returning the most recent score row per job at this version.

    SQLite-safe: ``MAX(id)`` grouped by ``job_id`` works on every backend we
    target. The scoring service writes one row per (version, job) — this
    just keeps us defensive against any duplicate inserts that slip in.
    """
    return (
        select(
            JobScoreRow.job_id,
            func.max(JobScoreRow.id).label("score_id"),
        )
        .where(JobScoreRow.profile_version == profile_version)
        .group_by(JobScoreRow.job_id)
        .subquery("latest_scores")
    )


def _utcnow():
    from datetime import datetime

    return datetime.utcnow()
