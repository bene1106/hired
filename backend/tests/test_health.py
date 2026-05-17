"""Smoke test for the /health endpoint."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api import VERSION
from api.main import app


@pytest.mark.asyncio
async def test_health_returns_ok_and_db_connected() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    # Assert against the package VERSION rather than a hardcoded string so
    # a version bump doesn't need a test edit (it did for 0.1.1).
    assert response.json() == {
        "status": "ok",
        "db": "connected",
        "version": VERSION,
    }
