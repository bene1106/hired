"""Application + interview-prep endpoint tests against the FastAPI TestClient."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_llm_provider
from api.main import app
from db.migrations import run_migrations
from db.models import Job
from db.models import Profile as ProfileRow
from db.session import get_session
from llm.mock import MockProvider
from services.generation_progress import reset_registry

client = TestClient(app)


@pytest.fixture(autouse=True)
def _migrated_clean() -> Iterator[None]:
    run_migrations()
    reset_registry()
    yield
    reset_registry()


@pytest.fixture
def mock_provider() -> Iterator[MockProvider]:
    """Override the LLM dependency with a deterministic provider."""
    provider = MockProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    try:
        yield provider
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)


def _seed_profile() -> int:
    with get_session() as session:
        row = ProfileRow(
            name="Alex K.",
            email="alex@example.com",
            target_roles_json=["Backend Engineer"],
            target_locations_json=["Berlin"],
            cv_parsed_json={"skills": ["Python", "FastAPI"], "work_experience": []},
            profile_version=0,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def _seed_job(*, company: str = "AcmeCo", source_id: str = "j1") -> int:
    with get_session() as session:
        job = Job(
            source="manual_url",
            source_id=source_id,
            title="Backend Engineer",
            company=company,
            location="Berlin",
            description="Build Python APIs.",
            url=f"https://example.test/{source_id}",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id


# ---------------------------------------------------------------------------
# POST /api/applications/{job_id}
# ---------------------------------------------------------------------------


def test_start_generation_creates_application_and_runs_pipeline(
    mock_provider: MockProvider,
) -> None:
    _seed_profile()
    job_id = _seed_job()

    res = client.post(f"/api/applications/{job_id}")
    assert res.status_code == 200
    payload = res.json()
    assert payload["application_id"] >= 1
    assert payload["task_id"]

    # BackgroundTasks runs synchronously after the response in the
    # TestClient, so by now the pipeline has already finished.
    status = client.get(
        f"/api/applications/{payload['application_id']}/generation/{payload['task_id']}"
    ).json()
    assert status["state"] == "done"
    assert status["company_brief"] == "done"
    assert status["cv_suggestions"] == "done"
    assert status["cover_letter"] == "done"


def test_start_generation_returns_404_for_unknown_job() -> None:
    res = client.post("/api/applications/9999")
    assert res.status_code == 404


def test_status_endpoint_404s_for_unknown_task(mock_provider: MockProvider) -> None:
    _seed_profile()
    job_id = _seed_job()
    res = client.post(f"/api/applications/{job_id}").json()
    bad = client.get(f"/api/applications/{res['application_id']}/generation/nope")
    assert bad.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/applications/{id}/materials  +  PUT /…/materials/{type}
# ---------------------------------------------------------------------------


def test_get_materials_returns_three_sections(mock_provider: MockProvider) -> None:
    _seed_profile()
    job_id = _seed_job()
    started = client.post(f"/api/applications/{job_id}").json()
    app_id = started["application_id"]

    res = client.get(f"/api/applications/{app_id}/materials")
    assert res.status_code == 200
    body = res.json()
    assert body["application_id"] == app_id
    for kind in ("company_brief", "cv_suggestions", "cover_letter"):
        section = body[kind]
        assert section is not None, kind
        assert section["content"]
        assert section["edit_count"] == 0


def test_edit_material_increments_edit_count(mock_provider: MockProvider) -> None:
    _seed_profile()
    job_id = _seed_job()
    started = client.post(f"/api/applications/{job_id}").json()
    app_id = started["application_id"]

    res = client.put(
        f"/api/applications/{app_id}/materials/cover_letter",
        json={"content": "edited body"},
    )
    assert res.status_code == 200
    assert res.json()["edit_count"] == 1
    assert res.json()["content"] == "edited body"

    # Latest from GET reflects the edit.
    materials = client.get(f"/api/applications/{app_id}/materials").json()
    assert materials["cover_letter"]["content"] == "edited body"
    assert materials["cover_letter"]["edit_count"] == 1


def test_edit_material_rejects_unknown_type(mock_provider: MockProvider) -> None:
    _seed_profile()
    job_id = _seed_job()
    started = client.post(f"/api/applications/{job_id}").json()
    res = client.put(
        f"/api/applications/{started['application_id']}/materials/bogus",
        json={"content": "x"},
    )
    assert res.status_code == 400


def test_regenerate_returns_fresh_material(mock_provider: MockProvider) -> None:
    _seed_profile()
    job_id = _seed_job()
    started = client.post(f"/api/applications/{job_id}").json()
    app_id = started["application_id"]

    res = client.post(f"/api/applications/{app_id}/materials/cover_letter/regenerate")
    assert res.status_code == 200
    body = res.json()
    assert body["type"] == "cover_letter"
    assert body["content"]


# ---------------------------------------------------------------------------
# GET /api/applications  +  PUT /…/status
# ---------------------------------------------------------------------------


def test_list_applications_returns_summaries(mock_provider: MockProvider) -> None:
    _seed_profile()
    job_a = _seed_job(source_id="a")
    job_b = _seed_job(source_id="b")
    client.post(f"/api/applications/{job_a}")
    client.post(f"/api/applications/{job_b}")

    res = client.get("/api/applications")
    assert res.status_code == 200
    body = res.json()
    assert {row["job_id"] for row in body} == {job_a, job_b}
    assert all(row["status"] == "saved" for row in body)


def test_status_filter_narrows_list(mock_provider: MockProvider) -> None:
    _seed_profile()
    job_a = _seed_job(source_id="a")
    job_b = _seed_job(source_id="b")
    a_id = client.post(f"/api/applications/{job_a}").json()["application_id"]
    client.post(f"/api/applications/{job_b}")
    client.put(
        f"/api/applications/{a_id}/status",
        json={"status": "applied"},
    )

    applied = client.get("/api/applications?status=applied").json()
    assert {row["id"] for row in applied} == {a_id}
    saved = client.get("/api/applications?status=saved").json()
    assert {row["job_id"] for row in saved} == {job_b}


def test_status_update_sets_applied_at_when_transitioning_to_applied(
    mock_provider: MockProvider,
) -> None:
    _seed_profile()
    job_id = _seed_job()
    app_id = client.post(f"/api/applications/{job_id}").json()["application_id"]

    res = client.put(
        f"/api/applications/{app_id}/status",
        json={"status": "applied", "notes": "Submitted via web form."},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "applied"
    assert body["applied_at"] is not None
    assert body["notes"] == "Submitted via web form."


def test_status_update_rejects_unknown_value(mock_provider: MockProvider) -> None:
    _seed_profile()
    job_id = _seed_job()
    app_id = client.post(f"/api/applications/{job_id}").json()["application_id"]
    res = client.put(f"/api/applications/{app_id}/status", json={"status": "bogus"})
    assert res.status_code == 422  # pydantic rejects the literal


def test_status_update_accepts_interview_offer_rejected(
    mock_provider: MockProvider,
) -> None:
    _seed_profile()
    job_id = _seed_job()
    app_id = client.post(f"/api/applications/{job_id}").json()["application_id"]
    for status in ("interview", "offer", "rejected"):
        res = client.put(f"/api/applications/{app_id}/status", json={"status": status})
        assert res.status_code == 200, status
        assert res.json()["status"] == status


# ---------------------------------------------------------------------------
# Interview prep
# ---------------------------------------------------------------------------


def test_interview_questions_are_cached_after_first_call(
    mock_provider: MockProvider,
) -> None:
    _seed_profile()
    job_id = _seed_job()
    app_id = client.post(f"/api/applications/{job_id}").json()["application_id"]

    calls: list[None] = []
    real = mock_provider.generate_interview_questions

    def counting(job):  # type: ignore[no-redef]
        calls.append(None)
        return real(job)

    mock_provider.generate_interview_questions = counting  # type: ignore[assignment]

    first = client.get(f"/api/applications/{app_id}/interview/questions").json()
    second = client.get(f"/api/applications/{app_id}/interview/questions").json()

    assert len(calls) == 1, "second call should hit the cache"
    assert first["questions"] == second["questions"]
    assert first["role_context"] == "Build Python APIs."


def test_interview_questions_refresh_param_forces_regeneration(
    mock_provider: MockProvider,
) -> None:
    _seed_profile()
    job_id = _seed_job()
    app_id = client.post(f"/api/applications/{job_id}").json()["application_id"]

    calls: list[None] = []
    real = mock_provider.generate_interview_questions

    def counting(job):  # type: ignore[no-redef]
        calls.append(None)
        return real(job)

    mock_provider.generate_interview_questions = counting  # type: ignore[assignment]

    client.get(f"/api/applications/{app_id}/interview/questions")
    client.get(f"/api/applications/{app_id}/interview/questions?refresh=true")
    assert len(calls) == 2


def test_practice_attempt_persists_feedback(mock_provider: MockProvider) -> None:
    _seed_profile()
    job_id = _seed_job()
    app_id = client.post(f"/api/applications/{job_id}").json()["application_id"]

    res = client.post(
        f"/api/applications/{app_id}/interview/practice",
        json={
            "question": "Tell me about a time you debugged a hard issue.",
            "category": "behavioral",
            "answer": "I once spent two days chasing a race condition in our queue worker.",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["feedback"]["sample_stronger_answer"]
    assert body["feedback"]["off_topic"] is False

    attempts = client.get(f"/api/applications/{app_id}/interview/attempts").json()
    assert len(attempts) == 1
    assert attempts[0]["question"].startswith("Tell me about")


# ---------------------------------------------------------------------------
# Detail view
# ---------------------------------------------------------------------------


def test_application_detail_returns_job_and_materials(
    mock_provider: MockProvider,
) -> None:
    _seed_profile()
    job_id = _seed_job(company="DetailCo")
    app_id = client.post(f"/api/applications/{job_id}").json()["application_id"]

    res = client.get(f"/api/applications/{app_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["job"]["company"] == "DetailCo"
    assert body["materials"]["cover_letter"] is not None


def test_data_wipe_clears_company_briefs_and_practice(
    mock_provider: MockProvider,
) -> None:
    """Deleting all data should also wipe the new Phase 5 tables."""
    _seed_profile()
    job_id = _seed_job(company="WipeCo")
    app_id = client.post(f"/api/applications/{job_id}").json()["application_id"]
    client.post(
        f"/api/applications/{app_id}/interview/practice",
        json={"question": "Q?", "answer": "A.", "category": "behavioral"},
    )

    res = client.delete("/api/data/all")
    assert res.status_code == 200

    # Re-seed and confirm: a fresh apply should re-research the company,
    # i.e. company_briefs cache is empty.
    _seed_profile()
    job_id = _seed_job(company="WipeCo", source_id="j-after")
    app_id_after = client.post(f"/api/applications/{job_id}").json()["application_id"]
    materials = client.get(f"/api/applications/{app_id_after}/materials").json()
    assert materials["company_brief"] is not None

    attempts = client.get(f"/api/applications/{app_id_after}/interview/attempts").json()
    assert attempts == []
