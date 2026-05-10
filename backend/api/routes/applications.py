"""Phase 5 application + interview-prep API.

Endpoints (paths grouped):

Generate / view materials::

    POST   /api/applications/{job_id}                          start a generation
    GET    /api/applications/{id}/generation/{task_id}         poll progress
    GET    /api/applications/{id}/materials                    latest of each type
    PUT    /api/applications/{id}/materials/{type}             save a user edit
    POST   /api/applications/{id}/materials/{type}/regenerate  force-regenerate

Dashboard / status::

    GET    /api/applications                                   list (filter by status)
    GET    /api/applications/{id}                              detail (job + materials)
    PUT    /api/applications/{id}/status                       update status + notes

Interview prep::

    GET    /api/applications/{id}/interview/questions          generate or load cache
    POST   /api/applications/{id}/interview/practice           submit answer + feedback
    GET    /api/applications/{id}/interview/attempts           past practice answers

Role explanation: a synthesized two-paragraph summary of the role from
``LLMProvider.summarize_role`` is cached in the latest
``interview_questions`` material's ``source_meta_json`` under the key
``role_summary``. It's regenerated alongside the questions when the
caller passes ``refresh=true`` or when only one half of the cache is
present.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from api.dependencies import get_llm_provider
from db.models import (
    Application,
    ApplicationMaterial,
    Job,
    PracticeAttempt,
)
from db.session import get_session
from llm import LLMProvider
from services.application_service import (
    MATERIAL_TYPES,
    ApplicationServiceError,
    MaterialType,
    MaterialView,
    generate_application_materials,
    get_all_materials,
    get_latest_material,
    get_or_create_application,
    save_material_edit,
)
from services.generation_progress import (
    GenerationProgress,
    create_entry,
    get_entry,
)
from services.profile_mapper import job_row_to_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/applications", tags=["applications"])


_VALID_STATUSES: set[str] = {"saved", "applied", "skipped", "interview", "offer", "rejected"}
ApplicationStatus = Literal["saved", "applied", "skipped", "interview", "offer", "rejected"]
INTERVIEW_QUESTIONS_TYPE = "interview_questions"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class StartGenerationResponse(BaseModel):
    application_id: int
    task_id: str


class GenerationStatusResponse(BaseModel):
    task_id: str
    application_id: int
    state: str
    company_brief: str
    cv_suggestions: str
    cover_letter: str
    error: str | None


class MaterialResponse(BaseModel):
    type: MaterialType
    content: str
    source_meta: dict | None
    created_at: datetime
    edit_count: int

    @classmethod
    def from_view(cls, view: MaterialView) -> MaterialResponse:
        return cls(
            type=view.type,
            content=view.content,
            source_meta=view.source_meta,
            created_at=view.created_at,
            edit_count=view.edit_count,
        )


class MaterialsBundleResponse(BaseModel):
    application_id: int
    company_brief: MaterialResponse | None
    cv_suggestions: MaterialResponse | None
    cover_letter: MaterialResponse | None


class EditMaterialRequest(BaseModel):
    content: str = Field(min_length=1)


class StatusUpdateRequest(BaseModel):
    status: ApplicationStatus
    notes: str | None = None


class ApplicationSummary(BaseModel):
    id: int
    job_id: int
    title: str
    company: str | None
    location: str | None
    url: str | None
    status: str
    applied_at: datetime | None
    notes: str | None


class ApplicationDetailResponse(BaseModel):
    id: int
    job: dict
    status: str
    applied_at: datetime | None
    notes: str | None
    materials: MaterialsBundleResponse


class InterviewQuestionResponse(BaseModel):
    category: str
    question: str
    what_theyre_assessing: str | None
    difficulty: str | None


class InterviewQuestionBundle(BaseModel):
    application_id: int
    questions: list[InterviewQuestionResponse]
    role_context: str | None = Field(
        default=None,
        description=(
            "Two-paragraph synthesized role summary from "
            "``LLMProvider.summarize_role``, cached on the latest "
            "interview_questions material. Falls back to the raw job "
            "description if synthesis fails."
        ),
    )


class PracticeRequest(BaseModel):
    question: str = Field(min_length=1)
    category: str | None = None
    answer: str = Field(min_length=1)


class PracticeFeedback(BaseModel):
    what_worked: list[str]
    what_to_improve: list[dict]
    sample_stronger_answer: str
    off_topic: bool


class PracticeAttemptResponse(BaseModel):
    id: int
    question: str
    category: str | None
    answer: str
    feedback: PracticeFeedback
    created_at: datetime


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


@router.post("/{job_id}", response_model=StartGenerationResponse)
def start_generation(
    job_id: int,
    background_tasks: BackgroundTasks,
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> StartGenerationResponse:
    try:
        application = get_or_create_application(job_id)
    except ApplicationServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    entry = create_entry(application.id)
    background_tasks.add_task(
        _run_generation,
        application_id=application.id,
        task_id=entry.task_id,
        provider=provider,
    )
    return StartGenerationResponse(application_id=application.id, task_id=entry.task_id)


@router.get(
    "/{application_id}/generation/{task_id}",
    response_model=GenerationStatusResponse,
)
def get_generation_status(application_id: int, task_id: str) -> GenerationStatusResponse:
    entry = get_entry(task_id)
    if entry is None or entry.application_id != application_id:
        raise HTTPException(status_code=404, detail="Unknown generation task.")
    return _status_payload(entry)


@router.post(
    "/{application_id}/materials/{material_type}/regenerate",
    response_model=MaterialResponse,
)
def regenerate(
    application_id: int,
    material_type: str,
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> MaterialResponse:
    if material_type not in MATERIAL_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown material type '{material_type}'.")
    try:
        generate_application_materials(
            provider,
            application_id,
            force=(material_type,),  # type: ignore[arg-type]
        )
    except ApplicationServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    view = get_latest_material(application_id, material_type)  # type: ignore[arg-type]
    if view is None:
        raise HTTPException(status_code=500, detail="Regenerated material is missing.")
    return MaterialResponse.from_view(view)


# ---------------------------------------------------------------------------
# Materials view + edit
# ---------------------------------------------------------------------------


@router.get("/{application_id}/materials", response_model=MaterialsBundleResponse)
def get_materials(application_id: int) -> MaterialsBundleResponse:
    _require_application(application_id)
    materials = get_all_materials(application_id)
    return MaterialsBundleResponse(
        application_id=application_id,
        company_brief=_response_or_none(materials.get("company_brief")),
        cv_suggestions=_response_or_none(materials.get("cv_suggestions")),
        cover_letter=_response_or_none(materials.get("cover_letter")),
    )


@router.put(
    "/{application_id}/materials/{material_type}",
    response_model=MaterialResponse,
)
def edit_material(
    application_id: int, material_type: str, payload: EditMaterialRequest
) -> MaterialResponse:
    if material_type not in MATERIAL_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown material type '{material_type}'.")
    _require_application(application_id)
    try:
        view = save_material_edit(
            application_id,
            material_type,
            payload.content,  # type: ignore[arg-type]
        )
    except ApplicationServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MaterialResponse.from_view(view)


# ---------------------------------------------------------------------------
# Dashboard / status
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ApplicationSummary])
def list_applications(status: str | None = None) -> list[ApplicationSummary]:
    if status is not None and status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown status '{status}'. Valid: {sorted(_VALID_STATUSES)}",
        )
    out: list[ApplicationSummary] = []
    with get_session() as session:
        query = select(Application, Job).join(Job, Job.id == Application.job_id)
        if status is not None:
            query = query.where(Application.status == status)
        query = query.order_by(desc(Application.id))
        for application, job in session.execute(query).all():
            out.append(
                ApplicationSummary(
                    id=application.id,
                    job_id=application.job_id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    url=job.url,
                    status=application.status,
                    applied_at=application.applied_at,
                    notes=application.notes,
                )
            )
    return out


@router.get("/{application_id}", response_model=ApplicationDetailResponse)
def get_application_detail(application_id: int) -> ApplicationDetailResponse:
    application, job = _require_application(application_id, with_job=True)
    materials = get_all_materials(application_id)
    return ApplicationDetailResponse(
        id=application.id,
        job=job_row_to_llm(job).model_dump(mode="json"),
        status=application.status,
        applied_at=application.applied_at,
        notes=application.notes,
        materials=MaterialsBundleResponse(
            application_id=application_id,
            company_brief=_response_or_none(materials.get("company_brief")),
            cv_suggestions=_response_or_none(materials.get("cv_suggestions")),
            cover_letter=_response_or_none(materials.get("cover_letter")),
        ),
    )


@router.put("/{application_id}/status", response_model=ApplicationSummary)
def update_status(application_id: int, payload: StatusUpdateRequest) -> ApplicationSummary:
    application, job = _require_application(application_id, with_job=True)
    with get_session() as session:
        # Re-fetch in this session so we can mutate.
        live = session.get(Application, application.id)
        if live is None:
            raise HTTPException(status_code=404, detail="Application disappeared.")
        live.status = payload.status
        if payload.notes is not None:
            live.notes = payload.notes
        if payload.status == "applied" and live.applied_at is None:
            live.applied_at = datetime.utcnow()
        session.commit()
        session.refresh(live)
        return ApplicationSummary(
            id=live.id,
            job_id=live.job_id,
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            status=live.status,
            applied_at=live.applied_at,
            notes=live.notes,
        )


# ---------------------------------------------------------------------------
# Interview prep
# ---------------------------------------------------------------------------


@router.get(
    "/{application_id}/interview/questions",
    response_model=InterviewQuestionBundle,
)
def get_interview_questions(
    application_id: int,
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    refresh: bool = False,
) -> InterviewQuestionBundle:
    application, job = _require_application(application_id, with_job=True)
    cached_questions, cached_summary = (
        (None, None) if refresh else _load_interview_cache(application_id)
    )

    if cached_questions is None:
        llm_job = job_row_to_llm(job)
        questions = provider.generate_interview_questions(llm_job)
        cached_questions = [q.model_dump() for q in questions]
    else:
        llm_job = None  # only build the LLM Job if we actually need to call out

    if cached_summary is None:
        if llm_job is None:
            llm_job = job_row_to_llm(job)
        cached_summary = _safe_summarize_role(provider, llm_job, fallback=job.description)

    _save_interview_cache(application_id, cached_questions, cached_summary)

    return InterviewQuestionBundle(
        application_id=application_id,
        questions=[InterviewQuestionResponse(**q) for q in cached_questions],
        role_context=cached_summary,
    )


def _safe_summarize_role(provider: LLMProvider, llm_job, *, fallback: str | None) -> str | None:
    """Summarize the role; fall back to the raw description if the call fails."""
    try:
        summary = provider.summarize_role(llm_job)
    except Exception:  # noqa: BLE001 — observability via RecordingProvider; UI gracefully falls back
        logger.exception("summarize_role failed; falling back to raw job description.")
        return fallback
    return summary.strip() or fallback


@router.post(
    "/{application_id}/interview/practice",
    response_model=PracticeAttemptResponse,
)
def submit_practice_answer(
    application_id: int,
    payload: PracticeRequest,
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> PracticeAttemptResponse:
    _require_application(application_id)
    feedback = provider.evaluate_answer(payload.question, payload.answer)
    feedback_payload = feedback.model_dump(mode="json")
    with get_session() as session:
        row = PracticeAttempt(
            application_id=application_id,
            category=payload.category,
            question=payload.question,
            answer=payload.answer,
            feedback_json=feedback_payload,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return PracticeAttemptResponse(
            id=row.id,
            question=row.question,
            category=row.category,
            answer=row.answer,
            feedback=PracticeFeedback(
                what_worked=list(feedback_payload.get("what_worked") or []),
                what_to_improve=list(feedback_payload.get("what_to_improve") or []),
                sample_stronger_answer=feedback_payload.get("sample_stronger_answer", ""),
                off_topic=bool(feedback_payload.get("off_topic")),
            ),
            created_at=row.created_at,
        )


@router.get(
    "/{application_id}/interview/attempts",
    response_model=list[PracticeAttemptResponse],
)
def list_practice_attempts(application_id: int) -> list[PracticeAttemptResponse]:
    _require_application(application_id)
    out: list[PracticeAttemptResponse] = []
    with get_session() as session:
        rows = (
            session.execute(
                select(PracticeAttempt)
                .where(PracticeAttempt.application_id == application_id)
                .order_by(desc(PracticeAttempt.id))
            )
            .scalars()
            .all()
        )
        for row in rows:
            payload = row.feedback_json or {}
            out.append(
                PracticeAttemptResponse(
                    id=row.id,
                    question=row.question,
                    category=row.category,
                    answer=row.answer,
                    feedback=PracticeFeedback(
                        what_worked=list(payload.get("what_worked") or []),
                        what_to_improve=list(payload.get("what_to_improve") or []),
                        sample_stronger_answer=payload.get("sample_stronger_answer", ""),
                        off_topic=bool(payload.get("off_topic")),
                    ),
                    created_at=row.created_at,
                )
            )
    return out


# ---------------------------------------------------------------------------
# Background task wrapper
# ---------------------------------------------------------------------------


def _run_generation(
    *,
    application_id: int,
    task_id: str,
    provider: LLMProvider,
) -> None:
    try:
        generate_application_materials(provider, application_id, task_id=task_id)
    except Exception:  # noqa: BLE001 — task already records the failure
        logger.exception(
            "Application generation failed (application_id=%s, task_id=%s)",
            application_id,
            task_id,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_application(application_id: int, *, with_job: bool = False):
    with get_session() as session:
        application = session.get(Application, application_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Unknown application id.")
        if not with_job:
            session.expunge(application)
            return application
        job = session.get(Job, application.job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Application references missing job.")
        session.expunge(application)
        session.expunge(job)
        return application, job


def _response_or_none(view: MaterialView | None) -> MaterialResponse | None:
    return MaterialResponse.from_view(view) if view is not None else None


def _status_payload(entry: GenerationProgress) -> GenerationStatusResponse:
    return GenerationStatusResponse(
        task_id=entry.task_id,
        application_id=entry.application_id,
        state=entry.state,
        company_brief=entry.company_brief,
        cv_suggestions=entry.cv_suggestions,
        cover_letter=entry.cover_letter,
        error=entry.error,
    )


def _load_interview_cache(
    application_id: int,
) -> tuple[list[dict] | None, str | None]:
    """Return (questions, role_summary) from the latest cached row; both may be None."""
    with get_session() as session:
        row = session.execute(
            select(ApplicationMaterial)
            .where(
                ApplicationMaterial.application_id == application_id,
                ApplicationMaterial.type == INTERVIEW_QUESTIONS_TYPE,
            )
            .order_by(desc(ApplicationMaterial.id))
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            return None, None
        questions: list[dict] | None = None
        if row.content:
            try:
                parsed = json.loads(row.content)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                questions = parsed
        meta = row.source_meta_json or {}
        summary = meta.get("role_summary") if isinstance(meta, dict) else None
        if not isinstance(summary, str) or not summary.strip():
            summary = None
        return questions, summary


def _save_interview_cache(
    application_id: int,
    questions: list[dict],
    role_summary: str | None,
) -> None:
    """Write a fresh cache row. Replacing rather than upserting keeps history."""
    with get_session() as session:
        row = ApplicationMaterial(
            application_id=application_id,
            type=INTERVIEW_QUESTIONS_TYPE,
            content=json.dumps(questions),
            source_meta_json={"role_summary": role_summary} if role_summary else None,
            profile_version=0,
        )
        session.add(row)
        session.commit()
