"""Phase 8 PR B — interview coach session + SSE chat endpoint tests.

These exercise the new ``/interview/sessions`` and
``/interview/sessions/{sid}/messages`` endpoints. The Phase 5 surface
(``/interview/questions``, ``/interview/practice``, ``/interview/attempts``)
is covered by ``test_application_endpoints.py`` and is intentionally NOT
touched here — coexistence is the whole point of PR B.
"""

from __future__ import annotations

import json
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


def _seed_job(*, source_id: str = "j-chat") -> int:
    with get_session() as session:
        job = Job(
            source="manual_url",
            source_id=source_id,
            title="Backend Engineer",
            company="AcmeCo",
            location="Berlin",
            description="Build Python APIs.",
            url=f"https://example.test/{source_id}",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id


def _make_application() -> int:
    _seed_profile()
    job_id = _seed_job()
    return client.post(f"/api/applications/{job_id}").json()["application_id"]


def _parse_sse(raw: str) -> list[dict]:
    """Pull the ``data: …`` JSON payloads out of an SSE response body."""
    events: list[dict] = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


def test_create_session_returns_empty_transcript(mock_provider: MockProvider) -> None:
    app_id = _make_application()
    res = client.post(f"/api/applications/{app_id}/interview/sessions")
    assert res.status_code == 200
    body = res.json()
    assert body["application_id"] == app_id
    assert body["messages"] == []
    assert isinstance(body["id"], int)


def test_create_session_404s_for_unknown_application(mock_provider: MockProvider) -> None:
    res = client.post("/api/applications/99999/interview/sessions")
    assert res.status_code == 404


def test_list_sessions_returns_newest_first(mock_provider: MockProvider) -> None:
    app_id = _make_application()
    first = client.post(f"/api/applications/{app_id}/interview/sessions").json()
    second = client.post(f"/api/applications/{app_id}/interview/sessions").json()

    res = client.get(f"/api/applications/{app_id}/interview/sessions")
    assert res.status_code == 200
    listing = res.json()
    assert [s["id"] for s in listing] == [second["id"], first["id"]]
    for entry in listing:
        assert entry["turn_count"] == 0
        assert entry["preview"] is None
        assert entry["last_message_at"] is not None  # falls back to created_at


def test_get_session_returns_404_for_other_application(
    mock_provider: MockProvider,
) -> None:
    app_a = _make_application()
    _seed_job(source_id="j-chat-2")
    job_b = _seed_job(source_id="j-chat-3")
    app_b = client.post(f"/api/applications/{job_b}").json()["application_id"]

    sid_in_a = client.post(f"/api/applications/{app_a}/interview/sessions").json()["id"]
    res = client.get(f"/api/applications/{app_b}/interview/sessions/{sid_in_a}")
    assert res.status_code == 404


def test_delete_session_removes_row(mock_provider: MockProvider) -> None:
    app_id = _make_application()
    sid = client.post(f"/api/applications/{app_id}/interview/sessions").json()["id"]

    res = client.delete(f"/api/applications/{app_id}/interview/sessions/{sid}")
    assert res.status_code == 204

    res = client.get(f"/api/applications/{app_id}/interview/sessions/{sid}")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Streaming chat
# ---------------------------------------------------------------------------


def test_chat_stream_emits_chunks_and_done_terminator(
    mock_provider: MockProvider,
) -> None:
    app_id = _make_application()
    sid = client.post(f"/api/applications/{app_id}/interview/sessions").json()["id"]

    with client.stream(
        "POST",
        f"/api/applications/{app_id}/interview/sessions/{sid}/messages",
        json={"content": "I built a payment service."},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = response.read().decode("utf-8")

    events = _parse_sse(body)
    # Multiple chunk events followed by exactly one done event.
    chunk_events = [e for e in events if "chunk" in e]
    done_events = [e for e in events if e.get("done") is True]
    assert len(chunk_events) >= 2
    assert len(done_events) == 1
    assert done_events[0]["session_id"] == sid


def test_chat_stream_persists_user_and_assistant_turns(
    mock_provider: MockProvider,
) -> None:
    app_id = _make_application()
    sid = client.post(f"/api/applications/{app_id}/interview/sessions").json()["id"]

    with client.stream(
        "POST",
        f"/api/applications/{app_id}/interview/sessions/{sid}/messages",
        json={"content": "I built a payment service."},
    ) as response:
        response.read()  # drain

    transcript = client.get(f"/api/applications/{app_id}/interview/sessions/{sid}").json()
    assert len(transcript["messages"]) == 2
    user_turn, assistant_turn = transcript["messages"]
    assert user_turn["role"] == "user"
    assert user_turn["content"] == "I built a payment service."
    assert assistant_turn["role"] == "assistant"
    # Mock's CRITIQUE-AND-FOLLOWUP reply quotes the candidate's words.
    assert "I built a payment service" in assistant_turn["content"]
    assert "Follow-up:" in assistant_turn["content"]


def test_chat_stream_continues_multi_turn(mock_provider: MockProvider) -> None:
    app_id = _make_application()
    sid = client.post(f"/api/applications/{app_id}/interview/sessions").json()["id"]

    for user_text in ("First answer.", "Second answer with more detail."):
        with client.stream(
            "POST",
            f"/api/applications/{app_id}/interview/sessions/{sid}/messages",
            json={"content": user_text},
        ) as response:
            response.read()

    transcript = client.get(f"/api/applications/{app_id}/interview/sessions/{sid}").json()
    # Each user turn produces exactly one assistant turn.
    assert len(transcript["messages"]) == 4
    roles = [m["role"] for m in transcript["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_chat_stream_failure_does_not_persist_assistant_turn(
    mock_provider: MockProvider,
) -> None:
    app_id = _make_application()
    sid = client.post(f"/api/applications/{app_id}/interview/sessions").json()["id"]

    def boom(_messages, _role_context=None):
        raise RuntimeError("provider exploded mid-stream")
        yield  # pragma: no cover — make this a generator

    mock_provider.interview_chat_stream = boom  # type: ignore[assignment]

    with client.stream(
        "POST",
        f"/api/applications/{app_id}/interview/sessions/{sid}/messages",
        json={"content": "Trigger the failure."},
    ) as response:
        body = response.read().decode("utf-8")
    events = _parse_sse(body)
    assert any("error" in e for e in events)
    assert not any(e.get("done") for e in events)

    transcript = client.get(f"/api/applications/{app_id}/interview/sessions/{sid}").json()
    # User turn persists so they can retry; assistant turn does not — we
    # never poison the history with a half-completed reply.
    roles = [m["role"] for m in transcript["messages"]]
    assert roles == ["user"]


def test_chat_session_summary_preview_uses_last_user_turn(
    mock_provider: MockProvider,
) -> None:
    app_id = _make_application()
    sid = client.post(f"/api/applications/{app_id}/interview/sessions").json()["id"]

    with client.stream(
        "POST",
        f"/api/applications/{app_id}/interview/sessions/{sid}/messages",
        json={"content": "Tell me about the architecture review I led."},
    ) as response:
        response.read()

    listing = client.get(f"/api/applications/{app_id}/interview/sessions").json()
    entry = next(s for s in listing if s["id"] == sid)
    assert entry["turn_count"] == 2
    assert entry["preview"] == "Tell me about the architecture review I led."


def test_chat_endpoint_uses_cached_role_context_when_available(
    mock_provider: MockProvider,
) -> None:
    app_id = _make_application()
    # Warm the role-summary cache via the existing question-bank surface.
    client.get(f"/api/applications/{app_id}/interview/questions")

    captured: dict[str, object] = {}
    real_stream = mock_provider.interview_chat_stream

    def capturing_stream(messages, role_context=None):
        captured["role_context"] = role_context
        yield from real_stream(messages, role_context)

    mock_provider.interview_chat_stream = capturing_stream  # type: ignore[assignment]

    sid = client.post(f"/api/applications/{app_id}/interview/sessions").json()["id"]
    with client.stream(
        "POST",
        f"/api/applications/{app_id}/interview/sessions/{sid}/messages",
        json={"content": "Ready."},
    ) as response:
        response.read()
    # Mock's summarize_role mentions the job title; the cache layer plumbed
    # that through to the chat endpoint.
    assert isinstance(captured.get("role_context"), str)
    assert "Backend Engineer" in captured["role_context"]  # type: ignore[index]
