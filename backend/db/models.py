"""SQLAlchemy ORM models — single source of truth for the schema.

The initial Alembic migration creates these tables; later phases add columns
and indexes via further migrations. Tables are deliberately bare in Phase 1:
the goal is to lock in the structure so Phase 3+ can populate them.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    target_roles_json: Mapped[list | None] = mapped_column(JSON)
    target_locations_json: Mapped[list | None] = mapped_column(JSON)
    target_salary_min: Mapped[int | None] = mapped_column(Integer)
    priorities_json: Mapped[list | None] = mapped_column(JSON)
    phone: Mapped[str | None] = mapped_column(String(64))
    skills_json: Mapped[list | None] = mapped_column(JSON)
    work_formats_json: Mapped[list | None] = mapped_column(JSON)
    cv_text: Mapped[str | None] = mapped_column(Text)
    cv_parsed_json: Mapped[dict | None] = mapped_column(JSON)
    # Bumped on every profile mutation. Score cache keys on this so a profile
    # edit invalidates stale scores without a manual cache-clear step.
    profile_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CrawlSource(Base):
    """One configured job source — a Greenhouse/Lever company board or a
    Wellfound/Indeed keyword search. The background scheduler checks each
    enabled row against ``last_checked_at + interval_hours`` to decide
    whether a run is due."""

    __tablename__ = "crawl_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # "greenhouse" | "lever" | "wellfound" | "indeed"
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # company board slug for greenhouse/lever; null for wellfound/indeed
    company_slug: Mapped[str | None] = mapped_column(String(255))
    # human-readable display name shown in the UI
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    # null on success; last error message on failure
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_jobs_source_source_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    remote_policy: Mapped[str | None] = mapped_column(String(32))
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(8))
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2048))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class JobScore(Base):
    __tablename__ = "job_scores"
    __table_args__ = (
        Index("ix_job_scores_job_id", "job_id"),
        Index("ix_job_scores_profile_version_job_id", "profile_version", "job_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    profile_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale_json: Mapped[dict | None] = mapped_column(JSON)
    scored_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class JobInteraction(Base):
    __tablename__ = "job_interactions"
    __table_args__ = (UniqueConstraint("job_id", name="uq_job_interactions_job_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    feedback_signal: Mapped[int | None] = mapped_column(Integer)
    feedback_reason: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)


class ApplicationMaterial(Base):
    __tablename__ = "application_materials"
    __table_args__ = (Index("ix_application_materials_application_type", "application_id", "type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    # Citations/URLs surfaced alongside the markdown body (company briefs use
    # this; cv_suggestions and cover_letter rows leave it null).
    source_meta_json: Mapped[dict | None] = mapped_column(JSON)
    # Mirrors profile.profile_version at generation time. CV tailoring and
    # cover letters fall out of cache when the profile bumps; company briefs
    # ignore this column (they live in their own table, see CompanyBrief).
    profile_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class CompanyBrief(Base):
    """Cached company research keyed by case-insensitive company name."""

    __tablename__ = "company_briefs"
    __table_args__ = (UniqueConstraint("company_lower", name="uq_company_briefs_company_lower"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_lower: Mapped[str] = mapped_column(String(255), nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    sources_json: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class PracticeAttempt(Base):
    __tablename__ = "practice_attempts"
    __table_args__ = (Index("ix_practice_attempts_application_id", "application_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str | None] = mapped_column(String(32))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    transcript_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Interview(Base):
    """A concrete interview an application has been invited to.

    One application has many interviews (round 1, 2, …). ``questions_json``
    caches the mock-interview question set prepared ahead of time so the timed
    runner has them ready with no LLM latency at start. ``scheduled_at`` drives
    the "upcoming vs past" gating for whether a mock run can be started.
    """

    __tablename__ = "interviews"
    __table_args__ = (Index("ix_interviews_application_id", "application_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    interview_type: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    interviewer_gender: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="unspecified", default="unspecified"
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    questions_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class MockInterviewRun(Base):
    """One attempt at a timed mock interview for a given interview.

    ``transcript_json`` holds the ordered question/answer records captured by the
    runner; ``evaluation_json`` is filled later (M3) when the answers are scored.
    ``voice_mode`` is stored for the later voice feature (M4) and defaults off.
    """

    __tablename__ = "mock_interview_runs"
    __table_args__ = (Index("ix_mock_interview_runs_interview_id", "interview_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="in_progress", default="in_progress"
    )
    voice_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0", default=False
    )
    transcript_json: Mapped[dict | None] = mapped_column(JSON)
    evaluation_json: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class AppConfig(Base):
    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)


class ProviderCallLog(Base):
    """One row per LLMProvider method call. Powers Settings observability."""

    __tablename__ = "provider_call_log"
    __table_args__ = (Index("ix_provider_call_log_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
