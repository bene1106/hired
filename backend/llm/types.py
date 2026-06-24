"""Pydantic types passed across the LLM provider boundary.

These are intentionally separate from `backend.db.models` (the persistence
layer). The DB stores the canonical user/job state; the LLM layer consumes a
flattened, prompt-friendly shape. Adapters and business logic both speak this
shape, so it stays stable even if the DB schema evolves.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkExperience(BaseModel):
    role: str
    company: str | None = None
    duration_months: int | None = None
    summary: str | None = None


class Profile(BaseModel):
    """Candidate profile as the LLM sees it."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    email: str | None = None
    target_role: str | None = None
    target_locations: list[str] = Field(default_factory=list)
    target_salary_min: int | None = None
    skills: list[str] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    cv_text: str | None = None


class Job(BaseModel):
    """Job posting as the LLM sees it."""

    model_config = ConfigDict(extra="ignore")

    title: str
    company: str | None = None
    location: str | None = None
    remote_policy: str | None = None
    salary_range: str | None = None
    description: str | None = None
    url: str | None = None
    posted_at: datetime | None = None


class ScoreResult(BaseModel):
    """Output of `LLMProvider.score_job`."""

    score: int = Field(ge=0, le=100)
    rationale: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)


class CompanyBrief(BaseModel):
    """Output of `LLMProvider.research_company`.

    The prompt returns a markdown document; we keep that as the canonical
    payload and surface a few derived fields adapters can fill in.
    """

    company: str
    markdown: str
    sources: list[str] = Field(default_factory=list)


class CoverLetter(BaseModel):
    """Output of `LLMProvider.generate_cover_letter`. Plain text body."""

    body: str
    word_count: int | None = None


InterviewCategory = Literal["technical", "behavioral", "role_specific", "company_fit"]
InterviewDifficulty = Literal["warmup", "standard", "deep"]


class InterviewQuestion(BaseModel):
    """One element of `LLMProvider.generate_interview_questions`."""

    category: InterviewCategory
    question: str
    what_theyre_assessing: str | None = None
    difficulty: InterviewDifficulty | None = None


class ImprovementNote(BaseModel):
    issue: str
    fix: str


class AnswerFeedback(BaseModel):
    """Output of `LLMProvider.evaluate_answer`."""

    what_worked: list[str] = Field(default_factory=list)
    what_to_improve: list[ImprovementNote] = Field(default_factory=list, min_length=1)
    sample_stronger_answer: str
    off_topic: bool = False


class MockInterviewContext(BaseModel):
    """Metadata describing the specific interview a mock run simulates.

    Drives both question generation (count/slant proportionate to duration and
    type) and evaluation (so the rubric matches an HR vs. technical round).
    ``interview_type`` is a free-form string at this layer — the API/UI
    constrain it to the known set.
    """

    round_number: int = Field(ge=1)
    interview_type: str
    duration_minutes: int = Field(ge=1)
    # How many questions to produce. Computed by the service (proportionate to
    # duration); included here so adapters can render it without importing the
    # service layer.
    num_questions: int = Field(ge=1, default=5)


class MockQuestion(BaseModel):
    """One element of `LLMProvider.generate_mock_interview_questions`.

    ``rephrasing`` is generated up front so the timed runner can re-ask a
    skipped question with no mid-interview LLM latency. ``time_limit_seconds``
    is the max answer window; the intro question gets a longer one.
    """

    category: InterviewCategory
    question: str
    rephrasing: str
    time_limit_seconds: int = Field(ge=15)
    is_intro: bool = False


class MockInterviewPlan(BaseModel):
    """Output of `LLMProvider.generate_mock_interview_questions`."""

    questions: list[MockQuestion] = Field(default_factory=list, min_length=1)


class MockQAPair(BaseModel):
    """A question paired with the candidate's transcribed answer."""

    question: str
    answer: str


class MockAnswerRating(BaseModel):
    """Per-question score within a mock-interview evaluation."""

    question: str
    rating: int = Field(ge=0, le=100)
    comment: str


class MockInterviewEvaluation(BaseModel):
    """Output of `LLMProvider.evaluate_mock_interview`."""

    per_question: list[MockAnswerRating] = Field(default_factory=list)
    overall_percentage: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


ChatRole = Literal["user", "assistant"]


class ChatMessage(BaseModel):
    """One turn in an interview-coach conversation.

    ``role`` uses provider-native labels (``user`` / ``assistant``) so adapters
    can pass the list straight through to their underlying chat API. The DB
    layer (``InterviewSession.transcript_json``) stores the same shape — we
    deliberately don't introduce a domain alias like ``coach`` because every
    translation point would have to map it back.
    """

    role: ChatRole
    content: str
    created_at: datetime | None = None


__all__ = [
    "AnswerFeedback",
    "ChatMessage",
    "ChatRole",
    "CompanyBrief",
    "CoverLetter",
    "ImprovementNote",
    "InterviewCategory",
    "InterviewDifficulty",
    "InterviewQuestion",
    "Job",
    "MockAnswerRating",
    "MockInterviewContext",
    "MockInterviewEvaluation",
    "MockInterviewPlan",
    "MockQAPair",
    "MockQuestion",
    "Profile",
    "ScoreResult",
    "WorkExperience",
]
