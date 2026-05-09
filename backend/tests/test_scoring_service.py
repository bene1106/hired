"""Scoring pipeline + cache tests, all against MockProvider."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from db.migrations import run_migrations
from db.models import Job, JobScore
from db.models import Profile as ProfileRow
from db.session import get_session
from llm.mock import MockProvider
from llm.types import ScoreResult
from services.scoring_service import ScoringError, score_jobs


@pytest.fixture(autouse=True)
def _migrated() -> None:
    run_migrations()


def _seed_profile(version: int = 0) -> int:
    with get_session() as session:
        row = ProfileRow(
            name="Alex K.",
            email="alex@example.com",
            target_roles_json=["Backend Engineer"],
            target_locations_json=["Berlin"],
            cv_parsed_json={
                "skills": ["Python", "FastAPI"],
                "work_experience": [
                    {"title": "Backend Intern", "company": "TechCo", "duration_months": 6}
                ],
            },
            profile_version=version,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def _seed_jobs(n: int = 3) -> list[int]:
    ids: list[int] = []
    with get_session() as session:
        for i in range(n):
            job = Job(
                source="manual_url",
                source_id=f"acmeco:{i}",
                title=f"Backend Engineer {i}",
                company="AcmeCo",
                location="Berlin",
                description="Build APIs in Python.",
                url=f"https://acme.example/jobs/{i}",
            )
            session.add(job)
            session.flush()
            ids.append(job.id)
        session.commit()
    return ids


def test_score_jobs_persists_one_row_per_job() -> None:
    _seed_profile()
    job_ids = _seed_jobs(3)

    results = score_jobs(MockProvider(), job_ids)
    assert len(results) == 3
    assert all(0 <= r.score <= 100 for r in results)
    assert results[0].rationale  # MockProvider returns a non-empty stub

    with get_session() as session:
        rows = session.execute(select(JobScore)).scalars().all()
    assert len(rows) == 3
    assert {r.profile_version for r in rows} == {0}


def test_score_jobs_uses_cache_on_second_call() -> None:
    _seed_profile()
    job_ids = _seed_jobs(2)
    provider = MockProvider()

    score_jobs(provider, job_ids)

    # Force a different cached value so we can detect cache vs. live call.
    with get_session() as session:
        rows = session.execute(select(JobScore)).scalars().all()
        for row in rows:
            row.score = 42
            row.rationale_json = {**(row.rationale_json or {}), "score": 42, "rationale": "from cache"}
        session.commit()

    second = score_jobs(provider, job_ids)
    assert all(r.score == 42 for r in second)
    assert all(r.rationale == "from cache" for r in second)

    with get_session() as session:
        count = session.execute(select(JobScore)).scalars().all()
    assert len(count) == 2  # no new rows written


def test_score_jobs_rescore_after_profile_version_bump() -> None:
    _seed_profile(version=1)
    job_ids = _seed_jobs(1)
    provider = MockProvider()

    score_jobs(provider, job_ids)

    # Simulate a profile edit: bump the version.
    with get_session() as session:
        row = session.execute(select(ProfileRow).limit(1)).scalar_one()
        row.profile_version = 2
        session.commit()

    score_jobs(provider, job_ids)

    with get_session() as session:
        rows = session.execute(select(JobScore).order_by(JobScore.id)).scalars().all()
    assert len(rows) == 2
    assert {r.profile_version for r in rows} == {1, 2}


def test_score_jobs_uses_provider_override_when_no_cache() -> None:
    _seed_profile()
    job_ids = _seed_jobs(1)

    provider = MockProvider()
    provider.set_response(
        "score_job",
        ScoreResult(
            score=88,
            rationale="Strong match on stated stack.",
            matched_skills=["Python"],
            missing_skills=["Rust"],
            red_flags=[],
        ),
    )

    [scored] = score_jobs(provider, job_ids)
    assert scored.score == 88
    assert scored.matched_skills == ["Python"]


def test_score_jobs_skips_unknown_ids() -> None:
    _seed_profile()
    job_ids = _seed_jobs(2)

    results = score_jobs(MockProvider(), job_ids + [99999])
    assert len(results) == 2  # phantom id silently dropped


def test_score_jobs_raises_when_no_profile() -> None:
    job_ids = _seed_jobs(1)
    with pytest.raises(ScoringError):
        score_jobs(MockProvider(), job_ids)


def test_score_jobs_preserves_caller_order() -> None:
    _seed_profile()
    job_ids = _seed_jobs(3)
    reversed_ids = list(reversed(job_ids))

    results = score_jobs(MockProvider(), reversed_ids)
    assert [r.job.id for r in results] == reversed_ids


def test_score_jobs_returns_empty_for_empty_input() -> None:
    _seed_profile()
    assert score_jobs(MockProvider(), []) == []


def test_score_jobs_skips_provider_failures_per_job() -> None:
    _seed_profile()
    job_ids = _seed_jobs(2)

    class FlakyProvider(MockProvider):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def score_job(self, profile, job):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("transient model failure")
            return super().score_job(profile, job)

    results = score_jobs(FlakyProvider(), job_ids)
    # One job got a usable score, the failing one is dropped silently.
    assert len(results) == 1


def test_score_jobs_recovers_from_corrupt_cache_row() -> None:
    _seed_profile()
    [job_id] = _seed_jobs(1)

    # Seed a cached row with malformed rationale_json so the loader has to skip
    # it and fall through to a live score_job call.
    from db.models import JobScore as JobScoreRow

    with get_session() as session:
        session.add(
            JobScoreRow(
                job_id=job_id,
                profile_version=0,
                score=42,
                rationale_json={"score": "not-a-number"},  # ScoreResult will reject this
            )
        )
        session.commit()

    [result] = score_jobs(MockProvider(), [job_id])
    # Mock returns a valid stub at score=75; the corrupt row was discarded.
    assert result.score == 75
