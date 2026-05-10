"""Application generation pipeline.

Three steps, run sequentially so the UI can render each section as it
lands:

1. **Company brief** — keyed by lower(company). Three jobs at the same
   company → one research call. Profile edits do **not** invalidate this
   (a company is the same company regardless of who applies).
2. **CV tailoring** — keyed by ``(application_id, type, profile_version)``.
   Profile bumps re-run this step on the next generation.
3. **Cover letter** — same key shape as CV tailoring; uses the brief from
   step 1.

Each step writes a row to ``application_materials`` (cv_suggestions /
cover_letter) or ``company_briefs`` (research). Re-running with the same
keys returns the cached row and marks the step ``cached`` in the progress
registry — no provider call.

The orchestrator is the seam tests use to verify caching: pass the same
provider twice with two jobs at the same company and only one
``research_company`` call should land on the provider.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import desc, func, select

from db.models import (
    Application,
    ApplicationMaterial,
    CompanyBrief as CompanyBriefRow,
    Job,
)
from db.models import Profile as ProfileRow
from db.session import get_session
from llm import LLMProvider
from llm.types import CompanyBrief

from .generation_progress import update_entry
from .profile_mapper import job_row_to_llm, profile_row_to_llm

logger = logging.getLogger(__name__)

MaterialType = Literal["company_brief", "cv_suggestions", "cover_letter"]
MATERIAL_TYPES: tuple[MaterialType, ...] = (
    "company_brief",
    "cv_suggestions",
    "cover_letter",
)


@dataclass
class MaterialView:
    """One material type as the API returns it (latest version)."""

    type: MaterialType
    content: str
    source_meta: dict | None
    created_at: datetime
    edit_count: int


class ApplicationServiceError(RuntimeError):
    """Raised when generation cannot proceed (missing profile/job/etc.)."""


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def generate_application_materials(
    provider: LLMProvider,
    application_id: int,
    *,
    task_id: str | None = None,
    force: tuple[MaterialType, ...] = (),
) -> None:
    """Run the three-step generation pipeline for ``application_id``.

    ``force`` lets a caller skip the cache for specific steps — used by the
    Regenerate button on each section. ``task_id`` ties progress updates to
    a registry entry; pass ``None`` to skip progress reporting.
    """
    application, job, profile_row, llm_profile, llm_job = _load_context(application_id)
    profile_version = profile_row.profile_version
    company = (job.company or "").strip()

    if task_id:
        update_entry(task_id, state="running")

    # ----- Step 1: company brief --------------------------------------------------
    brief: CompanyBrief
    if "company_brief" not in force and company and (
        cached := _load_company_brief_cache(company)
    ):
        brief = cached
        _set_step(task_id, "company_brief", "cached")
    elif not company:
        # Job with no company name — synthesize a placeholder so the rest
        # of the pipeline still has something to feed cover-letter generation.
        brief = CompanyBrief(
            company="this company",
            markdown="_No company name was provided for this job._",
            sources=[],
        )
        _persist_material(
            application_id=application_id,
            type_="company_brief",
            content=brief.markdown,
            source_meta={"sources": []},
            profile_version=profile_version,
        )
        _set_step(task_id, "company_brief", "done")
    else:
        _set_step(task_id, "company_brief", "running")
        try:
            brief = provider.research_company(company)
        except Exception as exc:
            logger.exception("research_company failed for %s", company)
            _fail_step(task_id, "company_brief", exc)
            raise
        _save_company_brief_cache(brief)
        _persist_material(
            application_id=application_id,
            type_="company_brief",
            content=brief.markdown,
            source_meta={"sources": list(brief.sources)},
            profile_version=profile_version,
        )
        _set_step(task_id, "company_brief", "done")

    # ----- Step 2: CV tailoring ---------------------------------------------------
    if "cv_suggestions" not in force and (
        _load_material_cache(application_id, "cv_suggestions", profile_version)
    ):
        _set_step(task_id, "cv_suggestions", "cached")
    else:
        _set_step(task_id, "cv_suggestions", "running")
        try:
            cv_text = provider.tailor_cv(llm_profile, llm_job)
        except Exception as exc:
            logger.exception("tailor_cv failed for application %s", application_id)
            _fail_step(task_id, "cv_suggestions", exc)
            raise
        _persist_material(
            application_id=application_id,
            type_="cv_suggestions",
            content=cv_text,
            source_meta=None,
            profile_version=profile_version,
        )
        _set_step(task_id, "cv_suggestions", "done")

    # ----- Step 3: cover letter ---------------------------------------------------
    if "cover_letter" not in force and (
        _load_material_cache(application_id, "cover_letter", profile_version)
    ):
        _set_step(task_id, "cover_letter", "cached")
    else:
        _set_step(task_id, "cover_letter", "running")
        try:
            cover = provider.generate_cover_letter(llm_profile, llm_job, brief)
        except Exception as exc:
            logger.exception("generate_cover_letter failed for application %s", application_id)
            _fail_step(task_id, "cover_letter", exc)
            raise
        _persist_material(
            application_id=application_id,
            type_="cover_letter",
            content=cover.body,
            source_meta=(
                {"word_count": cover.word_count} if cover.word_count is not None else None
            ),
            profile_version=profile_version,
        )
        _set_step(task_id, "cover_letter", "done")

    if task_id:
        update_entry(task_id, state="done", finished_at=datetime.utcnow())


def regenerate_material(
    provider: LLMProvider,
    application_id: int,
    material_type: MaterialType,
) -> MaterialView:
    """Force-regenerate a single material and return the fresh view."""
    if material_type not in MATERIAL_TYPES:
        raise ApplicationServiceError(f"Unknown material type '{material_type}'.")
    generate_application_materials(provider, application_id, force=(material_type,))
    view = get_latest_material(application_id, material_type)
    if view is None:
        raise ApplicationServiceError(
            f"Regeneration succeeded but {material_type} row is missing."
        )
    return view


# ---------------------------------------------------------------------------
# Material reads (used by the routes layer)
# ---------------------------------------------------------------------------


def get_or_create_application(job_id: int) -> Application:
    """Return the existing Application for ``job_id`` or create a 'saved' one."""
    with get_session() as session:
        application = session.execute(
            select(Application).where(Application.job_id == job_id)
        ).scalar_one_or_none()
        if application is not None:
            return application
        job = session.get(Job, job_id)
        if job is None:
            raise ApplicationServiceError(f"Unknown job id {job_id}.")
        application = Application(job_id=job_id, status="saved")
        session.add(application)
        session.commit()
        session.refresh(application)
        return application


def get_latest_material(
    application_id: int, material_type: MaterialType
) -> MaterialView | None:
    with get_session() as session:
        row = session.execute(
            select(ApplicationMaterial)
            .where(
                ApplicationMaterial.application_id == application_id,
                ApplicationMaterial.type == material_type,
            )
            .order_by(desc(ApplicationMaterial.id))
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            return None
        total = session.execute(
            select(func.count(ApplicationMaterial.id)).where(
                ApplicationMaterial.application_id == application_id,
                ApplicationMaterial.type == material_type,
            )
        ).scalar_one()
        return MaterialView(
            type=material_type,
            content=row.content or "",
            source_meta=row.source_meta_json,
            created_at=row.created_at,
            edit_count=max(0, int(total) - 1),
        )


def get_all_materials(application_id: int) -> dict[MaterialType, MaterialView]:
    out: dict[MaterialType, MaterialView] = {}
    for kind in MATERIAL_TYPES:
        view = get_latest_material(application_id, kind)
        if view is not None:
            out[kind] = view
    return out


def save_material_edit(
    application_id: int, material_type: MaterialType, content: str
) -> MaterialView:
    """Append a new row capturing the user's edit; latest = newest row."""
    if material_type not in MATERIAL_TYPES:
        raise ApplicationServiceError(f"Unknown material type '{material_type}'.")

    with get_session() as session:
        previous = session.execute(
            select(ApplicationMaterial)
            .where(
                ApplicationMaterial.application_id == application_id,
                ApplicationMaterial.type == material_type,
            )
            .order_by(desc(ApplicationMaterial.id))
            .limit(1)
        ).scalar_one_or_none()
        # Reuse the previous row's profile_version so the edit doesn't look
        # newer than the cache key. source_meta carried forward; user edits
        # don't invent citations.
        profile_version = previous.profile_version if previous else 0
        source_meta = previous.source_meta_json if previous else None
        row = ApplicationMaterial(
            application_id=application_id,
            type=material_type,
            content=content,
            source_meta_json=source_meta,
            profile_version=profile_version,
        )
        session.add(row)
        session.commit()
    view = get_latest_material(application_id, material_type)
    assert view is not None
    return view


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _load_context(application_id: int):
    with get_session() as session:
        application = session.get(Application, application_id)
        if application is None:
            raise ApplicationServiceError(f"Unknown application id {application_id}.")
        job = session.get(Job, application.job_id)
        if job is None:
            raise ApplicationServiceError(
                f"Application {application_id} references missing job {application.job_id}."
            )
        profile_row = session.execute(select(ProfileRow).limit(1)).scalar_one_or_none()
        if profile_row is None:
            raise ApplicationServiceError("No profile saved yet — cannot generate materials.")
        llm_profile = profile_row_to_llm(profile_row)
        llm_job = job_row_to_llm(job)
        # Detach so callers can use them after the session closes.
        session.expunge(application)
        session.expunge(job)
        session.expunge(profile_row)
    return application, job, profile_row, llm_profile, llm_job


def _load_company_brief_cache(company: str) -> CompanyBrief | None:
    key = company.strip().lower()
    if not key:
        return None
    with get_session() as session:
        row = session.execute(
            select(CompanyBriefRow).where(CompanyBriefRow.company_lower == key)
        ).scalar_one_or_none()
        if row is None:
            return None
        return CompanyBrief(
            company=company,
            markdown=row.markdown,
            sources=list(row.sources_json or []),
        )


def _save_company_brief_cache(brief: CompanyBrief) -> None:
    key = (brief.company or "").strip().lower()
    if not key:
        return
    with get_session() as session:
        existing = session.execute(
            select(CompanyBriefRow).where(CompanyBriefRow.company_lower == key)
        ).scalar_one_or_none()
        if existing is not None:
            existing.markdown = brief.markdown
            existing.sources_json = list(brief.sources)
        else:
            session.add(
                CompanyBriefRow(
                    company_lower=key,
                    markdown=brief.markdown,
                    sources_json=list(brief.sources),
                )
            )
        session.commit()


def _load_material_cache(
    application_id: int, material_type: MaterialType, profile_version: int
) -> str | None:
    with get_session() as session:
        row = session.execute(
            select(ApplicationMaterial)
            .where(
                ApplicationMaterial.application_id == application_id,
                ApplicationMaterial.type == material_type,
                ApplicationMaterial.profile_version == profile_version,
            )
            .order_by(desc(ApplicationMaterial.id))
            .limit(1)
        ).scalar_one_or_none()
        return row.content if row is not None and row.content else None


def _persist_material(
    *,
    application_id: int,
    type_: MaterialType,
    content: str,
    source_meta: dict | None,
    profile_version: int,
) -> None:
    with get_session() as session:
        row = ApplicationMaterial(
            application_id=application_id,
            type=type_,
            content=content,
            source_meta_json=source_meta,
            profile_version=profile_version,
        )
        session.add(row)
        session.commit()


def _set_step(task_id: str | None, step: str, value: str) -> None:
    if task_id is None:
        return
    update_entry(task_id, **{step: value})


def _fail_step(task_id: str | None, step: str, exc: BaseException) -> None:
    if task_id is None:
        return
    update_entry(task_id, **{step: "error"})
    update_entry(task_id, state="error", error=f"{step}: {exc}", finished_at=datetime.utcnow())


__all__ = [
    "ApplicationServiceError",
    "MATERIAL_TYPES",
    "MaterialType",
    "MaterialView",
    "generate_application_materials",
    "get_all_materials",
    "get_latest_material",
    "get_or_create_application",
    "regenerate_material",
    "save_material_edit",
]
