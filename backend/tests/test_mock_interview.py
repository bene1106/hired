"""Mock-interview tests: provider stubs, service helpers, and CRUD endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_llm_provider
from api.main import app
from db.migrations import run_migrations
from db.models import Application, Job
from db.session import get_session
from llm.mock import MockProvider
from llm.types import Job as LLMJob
from llm.types import MockInterviewContext, MockQAPair, Profile
from services.mock_interview import (
    normalize_questions,
    prepare_interview_questions,
    target_question_count,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _migrated_clean() -> Iterator[None]:
    run_migrations()
    yield


@pytest.fixture
def mock_provider() -> Iterator[MockProvider]:
    provider = MockProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    try:
        yield provider
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)


def _seed_application(*, status: str = "interview") -> int:
    with get_session() as session:
        job = Job(
            source="manual_url",
            source_id="mi1",
            title="Backend Engineer",
            company="AcmeCo",
            location="Berlin",
            description="Build Python APIs.",
            url="https://example.test/mi1",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        application = Application(job_id=job.id, status=status)
        session.add(application)
        session.commit()
        session.refresh(application)
        return application.id


# ---------------------------------------------------------------------------
# Provider stubs
# ---------------------------------------------------------------------------


def test_mock_generate_questions_is_deterministic_with_intro_first() -> None:
    provider = MockProvider()
    ctx = MockInterviewContext(
        round_number=1, interview_type="technical", duration_minutes=30, num_questions=5
    )
    plan = provider.generate_mock_interview_questions(
        LLMJob(title="Backend Engineer"), Profile(), ctx
    )
    assert len(plan.questions) == 5
    assert plan.questions[0].is_intro is True
    assert all(q.is_intro is False for q in plan.questions[1:])
    assert all(q.rephrasing for q in plan.questions)


def test_mock_evaluate_returns_one_rating_per_answer() -> None:
    provider = MockProvider()
    ctx = MockInterviewContext(
        round_number=1, interview_type="hr", duration_minutes=20, num_questions=4
    )
    pairs = [MockQAPair(question="q1", answer="a1"), MockQAPair(question="q2", answer="a2")]
    evaluation = provider.evaluate_mock_interview(LLMJob(title="X"), ctx, pairs)
    assert len(evaluation.per_question) == 2
    assert 0 <= evaluation.overall_percentage <= 100
    assert evaluation.strengths and evaluation.weaknesses


# ---------------------------------------------------------------------------
# Service helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("duration", "expected"),
    [(1, 3), (18, 3), (30, 5), (60, 10), (120, 12), (600, 12)],
)
def test_target_question_count_bounds(duration: int, expected: int) -> None:
    assert target_question_count(duration) == expected


def test_normalize_questions_forces_intro_and_time_limits() -> None:
    raw = [{"category": "technical", "question": f"q{i}", "rephrasing": f"r{i}"} for i in range(8)]
    norm = normalize_questions(raw, 5)
    assert len(norm) == 5
    assert norm[0]["is_intro"] is True
    assert norm[0]["time_limit_seconds"] == 300
    assert all(q["is_intro"] is False for q in norm[1:])
    assert all(q["time_limit_seconds"] == 180 for q in norm[1:])


def test_prepare_interview_questions_persists(mock_provider: MockProvider) -> None:
    app_id = _seed_application()
    created = client.post(
        f"/api/applications/{app_id}/interviews",
        json={"round_number": 1, "interview_type": "technical", "duration_minutes": 30},
    ).json()
    questions = prepare_interview_questions(app_id, created["id"], mock_provider)
    assert len(questions) == target_question_count(30)
    assert questions[0]["is_intro"] is True


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


def test_create_list_update_delete_interview() -> None:
    app_id = _seed_application()

    created = client.post(
        f"/api/applications/{app_id}/interviews",
        json={
            "round_number": 1,
            "interview_type": "hr",
            "duration_minutes": 45,
            "interviewer_gender": "female",
        },
    )
    assert created.status_code == 200
    iid = created.json()["id"]
    assert created.json()["is_upcoming"] is True
    assert created.json()["question_count"] == 0

    listing = client.get(f"/api/applications/{app_id}/interviews").json()
    assert len(listing) == 1 and listing[0]["id"] == iid

    updated = client.patch(
        f"/api/applications/{app_id}/interviews/{iid}",
        json={"interviewer_gender": "male", "round_number": 2},
    ).json()
    assert updated["interviewer_gender"] == "male"
    assert updated["round_number"] == 2

    assert client.delete(f"/api/applications/{app_id}/interviews/{iid}").status_code == 204
    assert client.get(f"/api/applications/{app_id}/interviews").json() == []


def test_create_interview_rejects_bad_type_and_gender() -> None:
    app_id = _seed_application()
    bad_type = client.post(
        f"/api/applications/{app_id}/interviews",
        json={"round_number": 1, "interview_type": "nonsense", "duration_minutes": 30},
    )
    assert bad_type.status_code == 422
    bad_gender = client.post(
        f"/api/applications/{app_id}/interviews",
        json={
            "round_number": 1,
            "interview_type": "hr",
            "duration_minutes": 30,
            "interviewer_gender": "robot",
        },
    )
    assert bad_gender.status_code == 422


def test_past_interview_is_not_upcoming() -> None:
    app_id = _seed_application()
    past = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    created = client.post(
        f"/api/applications/{app_id}/interviews",
        json={
            "round_number": 1,
            "interview_type": "technical",
            "duration_minutes": 30,
            "scheduled_at": past,
        },
    ).json()
    assert created["is_upcoming"] is False


def test_prepare_questions_endpoint_fills_cache(mock_provider: MockProvider) -> None:
    app_id = _seed_application()
    iid = client.post(
        f"/api/applications/{app_id}/interviews",
        json={"round_number": 1, "interview_type": "technical", "duration_minutes": 30},
    ).json()["id"]

    prepared = client.post(f"/api/applications/{app_id}/interviews/{iid}/questions")
    assert prepared.status_code == 200
    body = prepared.json()
    assert body["question_count"] == target_question_count(30)
    assert body["questions"][0]["is_intro"] is True


def test_updating_duration_invalidates_cached_questions(mock_provider: MockProvider) -> None:
    app_id = _seed_application()
    iid = client.post(
        f"/api/applications/{app_id}/interviews",
        json={"round_number": 1, "interview_type": "technical", "duration_minutes": 30},
    ).json()["id"]
    client.post(f"/api/applications/{app_id}/interviews/{iid}/questions")

    updated = client.patch(
        f"/api/applications/{app_id}/interviews/{iid}",
        json={"duration_minutes": 60},
    ).json()
    assert updated["question_count"] == 0
    assert updated["questions"] is None


# ---------------------------------------------------------------------------
# Mock-interview runs (M2)
# ---------------------------------------------------------------------------


def _create_interview(app_id: int, **overrides: object) -> int:
    body = {"round_number": 1, "interview_type": "technical", "duration_minutes": 30}
    body.update(overrides)
    return client.post(f"/api/applications/{app_id}/interviews", json=body).json()["id"]


def test_start_run_auto_prepares_questions(mock_provider: MockProvider) -> None:
    app_id = _seed_application()
    iid = _create_interview(app_id)

    res = client.post(f"/api/applications/{app_id}/interviews/{iid}/runs")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "in_progress"
    assert body["run_id"] >= 1
    assert len(body["questions"]) == target_question_count(30)
    assert body["questions"][0]["is_intro"] is True


def test_start_run_on_past_interview_is_409(mock_provider: MockProvider) -> None:
    app_id = _seed_application()
    past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    iid = _create_interview(app_id, scheduled_at=past)

    res = client.post(f"/api/applications/{app_id}/interviews/{iid}/runs")
    assert res.status_code == 409


def test_complete_run_saves_transcript_and_marks_completed(mock_provider: MockProvider) -> None:
    app_id = _seed_application()
    iid = _create_interview(app_id)
    run_id = client.post(f"/api/applications/{app_id}/interviews/{iid}/runs").json()["run_id"]

    transcript = [
        {"question": "Tell me about yourself.", "answer": "I build APIs.", "skipped": False},
        {"question": "A hard bug?", "answer": "", "skipped": True, "asked_rephrasing": True},
    ]
    res = client.post(
        f"/api/applications/{app_id}/interviews/{iid}/runs/{run_id}/complete",
        json={"transcript": transcript},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
    assert len(body["transcript"]) == 2
    assert body["transcript"][1]["skipped"] is True
    assert body["evaluation"] is None  # scoring is M3


def test_list_and_get_runs(mock_provider: MockProvider) -> None:
    app_id = _seed_application()
    iid = _create_interview(app_id)
    run_id = client.post(f"/api/applications/{app_id}/interviews/{iid}/runs").json()["run_id"]
    client.post(
        f"/api/applications/{app_id}/interviews/{iid}/runs/{run_id}/complete",
        json={"transcript": [{"question": "q", "answer": "a"}]},
    )

    listing = client.get(f"/api/applications/{app_id}/interviews/{iid}/runs").json()
    assert len(listing) == 1
    assert listing[0]["status"] == "completed"
    assert listing[0]["question_count"] == 1
    assert listing[0]["has_evaluation"] is False

    detail = client.get(f"/api/applications/{app_id}/interviews/{iid}/runs/{run_id}").json()
    assert detail["id"] == run_id
    assert detail["transcript"][0]["answer"] == "a"


def test_get_run_404_for_wrong_interview(mock_provider: MockProvider) -> None:
    app_id = _seed_application()
    iid = _create_interview(app_id)
    run_id = client.post(f"/api/applications/{app_id}/interviews/{iid}/runs").json()["run_id"]
    other_iid = _create_interview(app_id, round_number=2)

    res = client.get(f"/api/applications/{app_id}/interviews/{other_iid}/runs/{run_id}")
    assert res.status_code == 404
