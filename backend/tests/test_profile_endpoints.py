"""Profile CRUD + factory-reset endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api.main import app
from db.migrations import run_migrations
from db.models import (
    AppConfig,
    Application,
    Job,
    ProviderCallLog,
)
from db.models import (
    Profile as ProfileRow,
)
from db.session import get_session
from llm import reset_provider_cache

client = TestClient(app)


@pytest.fixture(autouse=True)
def _migrated_and_clean() -> None:
    run_migrations()
    reset_provider_cache()


# ---------------------------------------------------------------------------
# GET /api/profile
# ---------------------------------------------------------------------------


def test_get_profile_404_when_empty() -> None:
    response = client.get("/api/profile")
    assert response.status_code == 404


def test_get_profile_returns_full_payload_after_post() -> None:
    client.post(
        "/api/profile",
        json={
            "name": "Alex",
            "email": "alex@example.com",
            "target_roles": ["Backend Engineer", "Platform Engineer"],
            "target_locations": ["Berlin", "Remote EU"],
            "target_salary_min": 60000,
            "priorities": ["impact", "growth"],
        },
    )

    response = client.get("/api/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Alex"
    assert body["target_roles"] == ["Backend Engineer", "Platform Engineer"]
    assert body["target_locations"] == ["Berlin", "Remote EU"]
    assert body["target_salary_min"] == 60000
    assert body["priorities"] == ["impact", "growth"]


# ---------------------------------------------------------------------------
# POST /api/profile
# ---------------------------------------------------------------------------


def test_post_profile_partial_update_preserves_other_fields() -> None:
    client.post(
        "/api/profile",
        json={"name": "Alex", "target_roles": ["Backend"], "target_salary_min": 50000},
    )
    client.post("/api/profile", json={"target_salary_min": 70000})

    response = client.get("/api/profile")
    body = response.json()
    assert body["name"] == "Alex"
    assert body["target_roles"] == ["Backend"]
    assert body["target_salary_min"] == 70000


def test_post_profile_rejects_negative_salary() -> None:
    response = client.post("/api/profile", json={"target_salary_min": -1})
    assert response.status_code == 422


def test_post_profile_bumps_profile_version_on_change() -> None:
    first = client.post("/api/profile", json={"name": "Alex"}).json()
    second = client.post("/api/profile", json={"target_roles": ["Backend"]}).json()
    third = client.post("/api/profile", json={}).json()  # no-op — no bump

    assert first["profile_version"] == 1
    assert second["profile_version"] == 2
    assert third["profile_version"] == 2


# ---------------------------------------------------------------------------
# DELETE /api/data/all
# ---------------------------------------------------------------------------


def test_delete_all_data_wipes_db_keychain_and_provider_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Seed every user-touchable table so the wipe has something to delete.
    with get_session() as session:
        session.add(ProfileRow(name="Alex", email="a@b.tld"))
        session.add(Job(source="manual", source_id="abc", title="Backend Engineer"))
        session.add(ProviderCallLog(provider="mock", method="parse_cv", latency_ms=1, success=True))
        session.commit()

    keychain_calls: list[str] = []
    monkeypatch.setattr(
        "api.routes.data.delete_credential",
        lambda name: keychain_calls.append(name),
    )

    cache_resets: list[bool] = []
    monkeypatch.setattr(
        "api.routes.data.reset_provider_cache",
        lambda: cache_resets.append(True),
    )

    response = client.delete("/api/data/all")

    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    with get_session() as session:
        assert session.execute(select(ProfileRow)).first() is None
        assert session.execute(select(Job)).first() is None
        assert session.execute(select(Application)).first() is None
        assert session.execute(select(ProviderCallLog)).first() is None

        config = {row.key: row.value for row in session.execute(select(AppConfig)).scalars()}
    assert config == {"provider": "mock", "model": "claude-opus-4-7"}

    assert keychain_calls == ["anthropic_api_key"]
    assert cache_resets == [True]


def test_delete_all_data_idempotent() -> None:
    # Wipe an already-empty install — should be a clean 200, not a crash.
    response_a = client.delete("/api/data/all")
    response_b = client.delete("/api/data/all")
    assert response_a.status_code == 200
    assert response_b.status_code == 200

    response_get = client.get("/api/profile")
    assert response_get.status_code == 404
