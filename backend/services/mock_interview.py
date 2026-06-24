"""Mock-interview service: question preparation for a specific interview.

Milestone 1 scope: turn an ``Interview`` row into a prepared, normalized set of
questions via the LLM provider, ready for the (future) timed runner. The timed
runner, transcript capture, and evaluation invocation land in later milestones —
the provider methods exist now but evaluation is not yet wired here.
"""

from __future__ import annotations

from sqlalchemy import select

from db.models import Application, Interview, Job
from db.models import Profile as ProfileRow
from db.session import get_session
from llm import LLMProvider
from llm.types import MockInterviewContext, Profile
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
    """Raised when an interview can't be found or prepared."""


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
