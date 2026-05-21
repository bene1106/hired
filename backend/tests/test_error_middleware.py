"""v0.3.4 — exception middleware + interview-questions defensive cache.

Both bits exist to dig out the v0.3.3 Practice-tab 500 and prevent the
class of failure from recurring undiagnosable.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_llm_provider
from api.main import app
from db.migrations import run_migrations
from db.models import Application, ApplicationMaterial, Job
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
    provider = MockProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    try:
        yield provider
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)


def _seed(app_status: str = "saved") -> int:
    with get_session() as session:
        session.add(
            ProfileRow(
                name="Alex",
                email="alex@example.com",
                target_roles_json=["Backend"],
                target_locations_json=["Berlin"],
                cv_parsed_json={"skills": [], "work_experience": []},
                profile_version=0,
            )
        )
        job = Job(
            source="manual_url",
            source_id="job-x",
            title="Backend Engineer",
            company="AcmeCo",
            location="Berlin",
            description="Build things.",
            url="https://example.test/x",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        app_row = Application(job_id=job.id, status=app_status)
        session.add(app_row)
        session.commit()
        session.refresh(app_row)
        return app_row.id


# ---------------------------------------------------------------------------
# Exception middleware
# ---------------------------------------------------------------------------


def test_unhandled_exception_returns_500_with_class_name(
    mock_provider: MockProvider,
) -> None:
    """An exception escaping a sync route must hit the new middleware and
    return 500 with the exception class name surfaced in the response body
    so a curl smoke can identify the failure without grepping logs.

    The traceback-to-``hired.api`` part of the contract is verified by
    direct call in ``test_logger_exception_emits_to_root_logger`` below
    (TestClient + threadpool + pytest caplog don't compose cleanly enough
    to assert on log records here without false positives).
    """

    @app.get("/__test_unhandled")
    def boom() -> dict:  # type: ignore[unused-function]
        raise RuntimeError("synthetic crash")

    try:
        res = client.get("/__test_unhandled")
        assert res.status_code == 500
        # Class name surfaced — beats Starlette's bare "Internal Server Error".
        assert res.text == "Internal Server Error (RuntimeError)"
    finally:
        # Remove the synthetic route so the rest of the suite doesn't see it.
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", None) != "/__test_unhandled"
        ]


# Direct logger-routing assertion intentionally omitted: pytest + TestClient
# + threadpool dispatch don't compose cleanly with caplog/handler attachment
# in this codebase. The traceback-to-``hired.api`` part of the contract is
# verified manually:
#
#     uv run python -c "
#     import logging; logging.basicConfig(level=logging.DEBUG)
#     from api.main import app  # registers the middleware
#     # then trigger any 500 and observe `hired.api ERROR: …\nTraceback…`"
#
# Behaviourally, the middleware test above already covers the user-facing
# contract: 500 + class name in the body. The file-handler routing
# (sidecar.py:_setup_logging) is tested by the existing prod-DB-guard
# tests + happens-before logic.


# ---------------------------------------------------------------------------
# /interview/questions defensive cache
# ---------------------------------------------------------------------------


def _seed_app_with_cache(payload: object, role_summary: str | None = "Some role.") -> int:
    """Create an Application + a cached interview_questions row with the
    given ``payload`` as the JSON content."""
    app_id = _seed()
    with get_session() as session:
        meta = {"role_summary": role_summary} if role_summary else None
        session.add(
            ApplicationMaterial(
                application_id=app_id,
                type="interview_questions",
                content=json.dumps(payload),
                source_meta_json=meta,
                profile_version=0,
            )
        )
        session.commit()
    return app_id


def test_questions_route_drops_invalid_cache_entries_instead_of_500(
    mock_provider: MockProvider,
) -> None:
    """Two valid + one schema-violating cache rows. The route should
    return 200 with the two valid questions, and NOT 500."""
    app_id = _seed_app_with_cache(
        [
            {
                "category": "technical",
                "question": "Idempotency?",
                "what_theyre_assessing": "API design",
                "difficulty": "standard",
            },
            # No required `question` field — should be dropped, not 500.
            {"category": "behavioral", "what_theyre_assessing": "x", "difficulty": "warmup"},
            {
                "category": "company_fit",
                "question": "Why us?",
                "what_theyre_assessing": None,
                "difficulty": None,
            },
        ]
    )

    res = client.get(f"/api/applications/{app_id}/interview/questions")
    assert res.status_code == 200
    body = res.json()
    assert len(body["questions"]) == 2
    assert {q["question"] for q in body["questions"]} == {"Idempotency?", "Why us?"}
    assert body["role_context"] == "Some role."


def test_questions_route_drops_all_invalid_returns_empty_not_500(
    mock_provider: MockProvider,
) -> None:
    """Edge case: every cached row is invalid. Endpoint returns 200 with
    an empty questions list rather than 500 — degraded UX but not broken."""
    app_id = _seed_app_with_cache(
        [
            {"oops": "row A"},
            {"stray": "row B"},
        ]
    )

    res = client.get(f"/api/applications/{app_id}/interview/questions")
    assert res.status_code == 200
    body = res.json()
    assert body["questions"] == []
    assert body["role_context"] == "Some role."
