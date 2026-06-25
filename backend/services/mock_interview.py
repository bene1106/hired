"""Mock-interview service: question preparation for a specific interview.

Milestone 1 scope: turn an ``Interview`` row into a prepared, normalized set of
questions via the LLM provider, ready for the (future) timed runner. The timed
runner, transcript capture, and evaluation invocation land in later milestones —
the provider methods exist now but evaluation is not yet wired here.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from db.models import Application, Interview, Job, MockInterviewRun
from db.models import Profile as ProfileRow
from db.session import get_session
from llm import LLMProvider
from llm.types import MockInterviewContext, MockInterviewEvaluation, MockQAPair, Profile
from services.profile_mapper import job_row_to_llm, profile_row_to_llm

# Interview metadata the API/UI constrain to these sets.
VALID_INTERVIEW_TYPES: set[str] = {
    "hr",
    "technical",
    "behavioral",
    "system_design",
    "other",
}
VALID_GENDERS: set[str] = {"male", "female", "unspecified"}

# Answer windows enforced regardless of what the LLM returns (see timing spec).
INTRO_TIME_LIMIT_SECONDS = 300
DEFAULT_TIME_LIMIT_SECONDS = 180

_MIN_QUESTIONS = 3
_MAX_QUESTIONS = 12
_MINUTES_PER_QUESTION = 6


class MockInterviewError(Exception):
    """Raised when an interview/run can't be found or prepared."""


class MockInterviewNotUpcomingError(MockInterviewError):
    """Raised when a mock run is requested for a past interview."""


def interview_is_upcoming(scheduled_at: datetime | None) -> bool:
    """Upcoming if unscheduled or scheduled today or later (date granularity)."""
    if scheduled_at is None:
        return True
    return scheduled_at.date() >= datetime.now(UTC).date()


def _questions_of(interview: Interview) -> list[dict]:
    if isinstance(interview.questions_json, dict):
        raw = interview.questions_json.get("questions")
        if isinstance(raw, list):
            return raw
    return []


def target_question_count(duration_minutes: int) -> int:
    """Roughly one question per six minutes, clamped to [3, 12]."""
    raw = round(duration_minutes / _MINUTES_PER_QUESTION)
    return max(_MIN_QUESTIONS, min(_MAX_QUESTIONS, raw))


def normalize_questions(questions: list[dict], target_count: int) -> list[dict]:
    """Force the runner's invariants onto LLM output.

    - The first question is the intro (``is_intro`` true, 300s window).
    - Every other question is non-intro with a 180s window.
    - The list is trimmed to ``target_count`` (never padded; at least one stays).
    """
    trimmed = questions[: max(1, target_count)]
    normalized: list[dict] = []
    for idx, q in enumerate(trimmed):
        is_intro = idx == 0
        normalized.append(
            {
                "category": q.get("category", "behavioral"),
                "question": q.get("question", ""),
                "rephrasing": q.get("rephrasing", q.get("question", "")),
                "time_limit_seconds": (
                    INTRO_TIME_LIMIT_SECONDS if is_intro else DEFAULT_TIME_LIMIT_SECONDS
                ),
                "is_intro": is_intro,
            }
        )
    return normalized


def prepare_interview_questions(
    application_id: int,
    interview_id: int,
    provider: LLMProvider,
) -> list[dict]:
    """Generate, normalize, and persist questions for one interview.

    Returns the normalized question dicts (also stored on the interview row).
    """
    with get_session() as session:
        interview = session.get(Interview, interview_id)
        if interview is None or interview.application_id != application_id:
            raise MockInterviewError("Unknown interview for this application.")
        application = session.get(Application, application_id)
        if application is None:
            raise MockInterviewError("Unknown application id.")
        job = session.get(Job, application.job_id)
        if job is None:
            raise MockInterviewError("Application references missing job.")
        profile_row = session.execute(select(ProfileRow).limit(1)).scalar_one_or_none()

        llm_job = job_row_to_llm(job)
        llm_profile = profile_row_to_llm(profile_row) if profile_row is not None else Profile()
        count = target_question_count(interview.duration_minutes)
        context = MockInterviewContext(
            round_number=interview.round_number,
            interview_type=interview.interview_type,
            duration_minutes=interview.duration_minutes,
            num_questions=count,
        )

        plan = provider.generate_mock_interview_questions(llm_job, llm_profile, context)
        normalized = normalize_questions([q.model_dump(mode="json") for q in plan.questions], count)

        interview.questions_json = {"questions": normalized}
        session.commit()

    return normalized


def start_mock_run(
    application_id: int,
    interview_id: int,
    provider: LLMProvider,
    voice_mode: bool = False,
) -> tuple[int, list[dict]]:
    """Start a timed mock-interview run.

    Rejects past interviews, ensures a question set exists (preparing one if
    needed), inserts an ``in_progress`` run, and returns ``(run_id, questions)``.
    """
    with get_session() as session:
        interview = session.get(Interview, interview_id)
        if interview is None or interview.application_id != application_id:
            raise MockInterviewError("Unknown interview for this application.")
        if not interview_is_upcoming(interview.scheduled_at):
            raise MockInterviewNotUpcomingError(
                "A mock interview can only be started for an upcoming interview."
            )
        questions = _questions_of(interview)

    if not questions:
        questions = prepare_interview_questions(application_id, interview_id, provider)

    with get_session() as session:
        run = MockInterviewRun(
            interview_id=interview_id, status="in_progress", voice_mode=voice_mode
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    return run_id, questions


def complete_mock_run(
    application_id: int,
    interview_id: int,
    run_id: int,
    transcript: list[dict],
) -> None:
    """Persist a finished run's transcript and mark it completed.

    Evaluation/scoring is invoked here in a later milestone; M2 only stores the
    transcript so the run is reviewable.
    """
    with get_session() as session:
        run = session.get(MockInterviewRun, run_id)
        if run is None or run.interview_id != interview_id:
            raise MockInterviewError("Unknown run for this interview.")
        interview = session.get(Interview, interview_id)
        if interview is None or interview.application_id != application_id:
            raise MockInterviewError("Unknown interview for this application.")
        run.transcript_json = {"transcript": transcript}
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        session.commit()


def evaluate_mock_run(
    application_id: int,
    interview_id: int,
    run_id: int,
    provider: LLMProvider,
) -> MockInterviewEvaluation:
    """Score a completed run's transcript and store the evaluation.

    Skipped answers are sent as empty strings (the prompt scores those low).
    The result is persisted to ``evaluation_json`` and returned.
    """
    with get_session() as session:
        run = session.get(MockInterviewRun, run_id)
        if run is None or run.interview_id != interview_id:
            raise MockInterviewError("Unknown run for this interview.")
        interview = session.get(Interview, interview_id)
        if interview is None or interview.application_id != application_id:
            raise MockInterviewError("Unknown interview for this application.")
        application = session.get(Application, application_id)
        if application is None:
            raise MockInterviewError("Unknown application id.")
        job = session.get(Job, application.job_id)
        if job is None:
            raise MockInterviewError("Application references missing job.")

        transcript = []
        if isinstance(run.transcript_json, dict):
            raw = run.transcript_json.get("transcript")
            if isinstance(raw, list):
                transcript = raw
        if not transcript:
            raise MockInterviewError("Run has no transcript to evaluate.")

        llm_job = job_row_to_llm(job)
        context = MockInterviewContext(
            round_number=interview.round_number,
            interview_type=interview.interview_type,
            duration_minutes=interview.duration_minutes,
            num_questions=len(transcript),
        )
        qa_pairs = [
            MockQAPair(question=item.get("question", ""), answer=item.get("answer", ""))
            for item in transcript
        ]

        evaluation = provider.evaluate_mock_interview(llm_job, context, qa_pairs)
        run.evaluation_json = evaluation.model_dump(mode="json")
        session.commit()

    return evaluation
