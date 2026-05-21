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
    "Profile",
    "ScoreResult",
    "WorkExperience",
]
