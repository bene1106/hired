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

Interview prep — Question Bank (Phase 5)::

    GET    /api/applications/{id}/interview/questions          generate or load cache
    POST   /api/applications/{id}/interview/practice           submit answer + feedback
    GET    /api/applications/{id}/interview/attempts           past practice answers

Interview chat — Coach sessions (Phase 8)::

    POST   /api/applications/{id}/interview/sessions                  create
    GET    /api/applications/{id}/interview/sessions                  list
    GET    /api/applications/{id}/interview/sessions/{sid}            transcript
    DELETE /api/applications/{id}/interview/sessions/{sid}            drop
    POST   /api/applications/{id}/interview/sessions/{sid}/messages   SSE chat

The coach surface reuses ``LLMProvider.interview_chat_stream``. Sessions
are persisted in ``InterviewSession.transcript_json`` as
``{"messages": [{"role", "content", "created_at"}, …]}``. The SSE
endpoint streams ``data: {"chunk": ...}`` events and ends with
``data: {"done": true, "message_id": ...}``; the assistant turn is only
appended to the transcript once the stream has finished cleanly, so a
disconnected client never poisons the history with a half-completed
reply.

Role explanation: a synthesized two-paragraph summary of the role from
``LLMProvider.summarize_role`` is cached in the latest
``interview_questions`` material's ``source_meta_json`` under the key
``role_summary``. It's regenerated alongside the questions when the
caller passes ``refresh=true`` or when only one half of the cache is
present. The chat endpoint reuses this cache for ``role_context`` so a
new session inherits the role brief without a duplicate LLM call.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from api.dependencies import get_llm_provider
from db.models import (
    Application,
    ApplicationMaterial,
    Interview,
    InterviewSession,
    Job,
    MockInterviewRun,
    PracticeAttempt,
)
from db.session import get_session
from llm import LLMProvider
from llm.types import ChatMessage
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
from services.mock_interview import (
    VALID_GENDERS,
    VALID_INTERVIEW_TYPES,
    MockInterviewError,
    MockInterviewNotUpcomingError,
    complete_mock_run,
    interview_is_upcoming,
    prepare_interview_questions,
    start_mock_run,
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


class InterviewCreateRequest(BaseModel):
    round_number: int = Field(ge=1)
    interview_type: str
    duration_minutes: int = Field(ge=1)
    interviewer_gender: str = "unspecified"
    scheduled_at: datetime | None = None


class InterviewUpdateRequest(BaseModel):
    round_number: int | None = Field(default=None, ge=1)
    interview_type: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1)
    interviewer_gender: str | None = None
    scheduled_at: datetime | None = None


class InterviewResponse(BaseModel):
    id: int
    application_id: int
    round_number: int
    interview_type: str
    duration_minutes: int
    interviewer_gender: str
    scheduled_at: datetime | None
    is_upcoming: bool
    question_count: int
    questions: list[dict] | None

    @classmethod
    def from_row(cls, row: Interview) -> InterviewResponse:
        questions = None
        if isinstance(row.questions_json, dict):
            raw = row.questions_json.get("questions")
            if isinstance(raw, list):
                questions = raw
        return cls(
            id=row.id,
            application_id=row.application_id,
            round_number=row.round_number,
            interview_type=row.interview_type,
            duration_minutes=row.duration_minutes,
            interviewer_gender=row.interviewer_gender,
            scheduled_at=row.scheduled_at,
            is_upcoming=interview_is_upcoming(row.scheduled_at),
            question_count=len(questions) if questions is not None else 0,
            questions=questions,
        )


class TranscriptItem(BaseModel):
    question: str
    answer: str = ""
    skipped: bool = False
    asked_rephrasing: bool = False


class CompleteRunRequest(BaseModel):
    transcript: list[TranscriptItem]


class RunStartResponse(BaseModel):
    run_id: int
    status: str
    questions: list[dict]


class RunSummaryResponse(BaseModel):
    id: int
    status: str
    started_at: datetime
    completed_at: datetime | None
    question_count: int
    has_evaluation: bool

    @classmethod
    def from_row(cls, row: MockInterviewRun) -> RunSummaryResponse:
        transcript = _transcript_of(row)
        return cls(
            id=row.id,
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            question_count=len(transcript),
            has_evaluation=row.evaluation_json is not None,
        )


class RunDetailResponse(BaseModel):
    id: int
    interview_id: int
    status: str
    started_at: datetime
    completed_at: datetime | None
    transcript: list[dict]
    evaluation: dict | None

    @classmethod
    def from_row(cls, row: MockInterviewRun) -> RunDetailResponse:
        return cls(
            id=row.id,
            interview_id=row.interview_id,
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            transcript=_transcript_of(row),
            evaluation=row.evaluation_json if isinstance(row.evaluation_json, dict) else None,
        )


def _transcript_of(row: MockInterviewRun) -> list[dict]:
    if isinstance(row.transcript_json, dict):
        raw = row.transcript_json.get("transcript")
        if isinstance(raw, list):
            return raw
    return []


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


class ChatTurnResponse(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime | None


class InterviewSessionSummary(BaseModel):
    id: int
    application_id: int
    created_at: datetime
    last_message_at: datetime | None
    turn_count: int
    preview: str | None


class InterviewSessionDetail(BaseModel):
    id: int
    application_id: int
    created_at: datetime
    messages: list[ChatTurnResponse]


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1)


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
# Mock interviews (per-application interview records + prepared questions)
# ---------------------------------------------------------------------------


def _validate_interview_fields(interview_type: str | None, gender: str | None) -> None:
    if interview_type is not None and interview_type not in VALID_INTERVIEW_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"interview_type must be one of {sorted(VALID_INTERVIEW_TYPES)}.",
        )
    if gender is not None and gender not in VALID_GENDERS:
        raise HTTPException(
            status_code=422,
            detail=f"interviewer_gender must be one of {sorted(VALID_GENDERS)}.",
        )


@router.post("/{application_id}/interviews", response_model=InterviewResponse)
def create_interview(application_id: int, payload: InterviewCreateRequest) -> InterviewResponse:
    _require_application(application_id)
    _validate_interview_fields(payload.interview_type, payload.interviewer_gender)
    with get_session() as session:
        row = Interview(
            application_id=application_id,
            round_number=payload.round_number,
            interview_type=payload.interview_type,
            duration_minutes=payload.duration_minutes,
            interviewer_gender=payload.interviewer_gender,
            scheduled_at=payload.scheduled_at,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return InterviewResponse.from_row(row)


@router.get("/{application_id}/interviews", response_model=list[InterviewResponse])
def list_interviews(application_id: int) -> list[InterviewResponse]:
    _require_application(application_id)
    with get_session() as session:
        rows = (
            session.execute(
                select(Interview)
                .where(Interview.application_id == application_id)
                .order_by(Interview.round_number, Interview.id)
            )
            .scalars()
            .all()
        )
        return [InterviewResponse.from_row(r) for r in rows]


@router.patch(
    "/{application_id}/interviews/{interview_id}",
    response_model=InterviewResponse,
)
def update_interview(
    application_id: int,
    interview_id: int,
    payload: InterviewUpdateRequest,
) -> InterviewResponse:
    _require_application(application_id)
    _validate_interview_fields(payload.interview_type, payload.interviewer_gender)
    with get_session() as session:
        row = session.get(Interview, interview_id)
        if row is None or row.application_id != application_id:
            raise HTTPException(status_code=404, detail="Unknown interview for this application.")
        # If type or duration changes, the cached questions no longer fit — drop
        # them so the next prepare call regenerates a matching set.
        invalidates = (
            payload.interview_type is not None and payload.interview_type != row.interview_type
        ) or (
            payload.duration_minutes is not None
            and payload.duration_minutes != row.duration_minutes
        )
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        if invalidates:
            row.questions_json = None
        session.commit()
        session.refresh(row)
        return InterviewResponse.from_row(row)


@router.delete("/{application_id}/interviews/{interview_id}", status_code=204)
def delete_interview(application_id: int, interview_id: int) -> None:
    _require_application(application_id)
    with get_session() as session:
        row = session.get(Interview, interview_id)
        if row is None or row.application_id != application_id:
            raise HTTPException(status_code=404, detail="Unknown interview for this application.")
        session.delete(row)
        session.commit()


@router.post(
    "/{application_id}/interviews/{interview_id}/questions",
    response_model=InterviewResponse,
)
def prepare_interview_questions_route(
    application_id: int,
    interview_id: int,
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> InterviewResponse:
    _require_application(application_id)
    try:
        prepare_interview_questions(application_id, interview_id, provider)
    except MockInterviewError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    with get_session() as session:
        row = session.get(Interview, interview_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Interview disappeared.")
        return InterviewResponse.from_row(row)


def _require_interview(application_id: int, interview_id: int) -> None:
    with get_session() as session:
        interview = session.get(Interview, interview_id)
        if interview is None or interview.application_id != application_id:
            raise HTTPException(status_code=404, detail="Unknown interview for this application.")


@router.post(
    "/{application_id}/interviews/{interview_id}/runs",
    response_model=RunStartResponse,
)
def start_interview_run(
    application_id: int,
    interview_id: int,
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> RunStartResponse:
    _require_application(application_id)
    try:
        run_id, questions = start_mock_run(application_id, interview_id, provider)
    except MockInterviewNotUpcomingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MockInterviewError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RunStartResponse(run_id=run_id, status="in_progress", questions=questions)


@router.post(
    "/{application_id}/interviews/{interview_id}/runs/{run_id}/complete",
    response_model=RunDetailResponse,
)
def complete_interview_run(
    application_id: int,
    interview_id: int,
    run_id: int,
    payload: CompleteRunRequest,
) -> RunDetailResponse:
    _require_application(application_id)
    try:
        complete_mock_run(
            application_id,
            interview_id,
            run_id,
            [item.model_dump() for item in payload.transcript],
        )
    except MockInterviewError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    with get_session() as session:
        run = session.get(MockInterviewRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run disappeared.")
        return RunDetailResponse.from_row(run)


@router.get(
    "/{application_id}/interviews/{interview_id}/runs",
    response_model=list[RunSummaryResponse],
)
def list_interview_runs(application_id: int, interview_id: int) -> list[RunSummaryResponse]:
    _require_application(application_id)
    _require_interview(application_id, interview_id)
    with get_session() as session:
        rows = (
            session.execute(
                select(MockInterviewRun)
                .where(MockInterviewRun.interview_id == interview_id)
                .order_by(desc(MockInterviewRun.id))
            )
            .scalars()
            .all()
        )
        return [RunSummaryResponse.from_row(r) for r in rows]


@router.get(
    "/{application_id}/interviews/{interview_id}/runs/{run_id}",
    response_model=RunDetailResponse,
)
def get_interview_run(
    application_id: int,
    interview_id: int,
    run_id: int,
) -> RunDetailResponse:
    _require_application(application_id)
    _require_interview(application_id, interview_id)
    with get_session() as session:
        run = session.get(MockInterviewRun, run_id)
        if run is None or run.interview_id != interview_id:
            raise HTTPException(status_code=404, detail="Unknown run for this interview.")
        return RunDetailResponse.from_row(run)


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

    # v0.3.4: log + sanitize per-question cached entries before re-serialising.
    # Phase 8 PR B didn't touch this handler's logic, but the v0.3.3 RC smoke
    # produced a 500 here despite local TestClient + uvicorn runs returning
    # 200 on the same DB snapshot — so the failure had to be inside the
    # cached-row → ``InterviewQuestionResponse`` conversion in the
    # PyInstaller bundle. Building each entry through ``model_validate``
    # surfaces ``ValidationError`` with the offending field for the new
    # exception middleware to log, and the try/except below tags the
    # offending row id so we can find it in the DB. Cached rows that fail
    # validation are dropped from the response — better an empty Practice
    # tab than a 500 wall.
    safe_questions: list[InterviewQuestionResponse] = []
    for idx, raw in enumerate(cached_questions):
        try:
            safe_questions.append(InterviewQuestionResponse.model_validate(raw))
        except Exception:  # noqa: BLE001 — log, then drop the bad row
            logger.exception(
                "interview cache row dropped (app=%s idx=%s payload_keys=%s)",
                application_id,
                idx,
                sorted((raw or {}).keys()) if isinstance(raw, dict) else type(raw).__name__,
            )

    _save_interview_cache(application_id, cached_questions, cached_summary)

    return InterviewQuestionBundle(
        application_id=application_id,
        questions=safe_questions,
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
# Interview chat — coach sessions (Phase 8)
# ---------------------------------------------------------------------------


@router.post(
    "/{application_id}/interview/sessions",
    response_model=InterviewSessionDetail,
)
def create_interview_session(application_id: int) -> InterviewSessionDetail:
    _require_application(application_id)
    with get_session() as session:
        row = InterviewSession(
            application_id=application_id,
            transcript_json={"messages": []},
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _session_to_detail(row)


@router.get(
    "/{application_id}/interview/sessions",
    response_model=list[InterviewSessionSummary],
)
def list_interview_sessions(application_id: int) -> list[InterviewSessionSummary]:
    _require_application(application_id)
    out: list[InterviewSessionSummary] = []
    with get_session() as session:
        rows = (
            session.execute(
                select(InterviewSession)
                .where(InterviewSession.application_id == application_id)
                .order_by(desc(InterviewSession.id))
            )
            .scalars()
            .all()
        )
        for row in rows:
            messages = _messages_from_transcript(row.transcript_json)
            preview = _preview_for(messages)
            last_at = _last_message_at(messages) or row.created_at
            out.append(
                InterviewSessionSummary(
                    id=row.id,
                    application_id=row.application_id,
                    created_at=row.created_at,
                    last_message_at=last_at,
                    turn_count=len(messages),
                    preview=preview,
                )
            )
    return out


@router.get(
    "/{application_id}/interview/sessions/{session_id}",
    response_model=InterviewSessionDetail,
)
def get_interview_session(application_id: int, session_id: int) -> InterviewSessionDetail:
    _require_application(application_id)
    with get_session() as session:
        row = _require_session(session, application_id, session_id)
        return _session_to_detail(row)


@router.delete(
    "/{application_id}/interview/sessions/{session_id}",
    status_code=204,
)
def delete_interview_session(application_id: int, session_id: int) -> None:
    _require_application(application_id)
    with get_session() as session:
        row = _require_session(session, application_id, session_id)
        session.delete(row)
        session.commit()


@router.post("/{application_id}/interview/sessions/{session_id}/messages")
def post_chat_message(
    application_id: int,
    session_id: int,
    payload: ChatMessageRequest,
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> StreamingResponse:
    _require_application(application_id)
    with get_session() as session:
        row = _require_session(session, application_id, session_id)
        history = _messages_from_transcript(row.transcript_json)
    role_context = _load_role_context_for_chat(application_id)

    # Append the user turn synchronously so a disconnected client doesn't
    # lose their own message; the assistant turn is only persisted once the
    # stream completes cleanly.
    user_turn = ChatMessage(
        role="user",
        content=payload.content,
        created_at=datetime.now(UTC),
    )
    persisted_messages = [*history, user_turn]
    _persist_transcript(session_id, persisted_messages)

    return StreamingResponse(
        _stream_chat_reply(
            provider=provider,
            session_id=session_id,
            history=persisted_messages,
            role_context=role_context,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _stream_chat_reply(
    *,
    provider: LLMProvider,
    session_id: int,
    history: list[ChatMessage],
    role_context: str | None,
) -> Iterator[bytes]:
    """SSE generator: yields chunk events, persists assistant turn on success.

    Errors during streaming become a single ``data: {"error": ...}`` event
    and the assistant turn is not persisted. The user turn is already in the
    transcript at this point, so retrying becomes "ask the coach again with
    the same input."
    """
    collected: list[str] = []
    try:
        for chunk in provider.interview_chat_stream(history, role_context):
            collected.append(chunk)
            yield _sse_event({"chunk": chunk})
    except Exception as exc:  # noqa: BLE001 — surface as one SSE event then stop
        logger.exception("interview_chat_stream failed (session_id=%s)", session_id)
        yield _sse_event({"error": str(exc)})
        return

    assistant_turn = ChatMessage(
        role="assistant",
        content="".join(collected),
        created_at=datetime.now(UTC),
    )
    _persist_transcript(session_id, [*history, assistant_turn])
    yield _sse_event({"done": True, "session_id": session_id})


def _sse_event(payload: dict) -> bytes:
    return f"data: {json.dumps(payload, default=str)}\n\n".encode()


def _require_session(session, application_id: int, session_id: int) -> InterviewSession:
    row = session.get(InterviewSession, session_id)
    if row is None or row.application_id != application_id:
        raise HTTPException(status_code=404, detail="Unknown interview session.")
    return row


def _messages_from_transcript(transcript: dict | None) -> list[ChatMessage]:
    if not isinstance(transcript, dict):
        return []
    raw = transcript.get("messages")
    if not isinstance(raw, list):
        return []
    out: list[ChatMessage] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        created_at = entry.get("created_at")
        parsed_at = _parse_iso(created_at) if isinstance(created_at, str) else None
        out.append(ChatMessage(role=role, content=content, created_at=parsed_at))
    return out


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _persist_transcript(session_id: int, messages: list[ChatMessage]) -> None:
    payload = {
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": (m.created_at or datetime.now(UTC)).isoformat(),
            }
            for m in messages
        ]
    }
    with get_session() as session:
        row = session.get(InterviewSession, session_id)
        if row is None:
            return
        row.transcript_json = payload
        session.commit()


def _session_to_detail(row: InterviewSession) -> InterviewSessionDetail:
    messages = _messages_from_transcript(row.transcript_json)
    return InterviewSessionDetail(
        id=row.id,
        application_id=row.application_id,
        created_at=row.created_at,
        messages=[
            ChatTurnResponse(role=m.role, content=m.content, created_at=m.created_at)
            for m in messages
        ],
    )


def _preview_for(messages: list[ChatMessage]) -> str | None:
    # Show the candidate's most recent question/answer in the session list —
    # easier to recognise than the coach's reply.
    for m in reversed(messages):
        if m.role == "user":
            first_line = m.content.strip().split("\n", 1)[0]
            return first_line[:120]
    return None


def _last_message_at(messages: list[ChatMessage]) -> datetime | None:
    for m in reversed(messages):
        if m.created_at is not None:
            return m.created_at
    return None


def _load_role_context_for_chat(application_id: int) -> str | None:
    """Reuse the role summary cached on the latest interview_questions material.

    Falls back to None — the coach prompt handles missing context gracefully.
    Deliberately does NOT trigger a fresh ``summarize_role`` call: if the
    Question Bank hasn't been opened yet, the chat starts with no role context
    rather than blocking on an LLM call before the first message streams.
    """
    _questions, summary = _load_interview_cache(application_id)
    return summary


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
