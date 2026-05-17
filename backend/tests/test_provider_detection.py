"""Provider detection unit + endpoint tests.

We monkeypatch `shutil.which`, `subprocess.run`, and httpx so the tests
never touch the real machine.
"""

from __future__ import annotations

import subprocess
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import app
from services import provider_detection as pd

client = TestClient(app)


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


def test_anthropic_detection_reports_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(pd, "get_credential", lambda _name: None)

    result = pd.detect_anthropic_api()

    assert result == {"key_in_env": True, "key_in_keychain": False}


def test_anthropic_detection_reports_keychain_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(pd, "get_credential", lambda _name: "stored-key")

    result = pd.detect_anthropic_api()

    assert result == {"key_in_env": False, "key_in_keychain": True}


def test_anthropic_detection_neither(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(pd, "get_credential", lambda _name: None)

    assert pd.detect_anthropic_api() == {"key_in_env": False, "key_in_keychain": False}


# ---------------------------------------------------------------------------
# Claude Code
# ---------------------------------------------------------------------------


def test_claude_code_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd.shutil, "which", lambda _name: None)

    assert pd.detect_claude_code() == {"detected": False, "path": None, "version": None}


def test_claude_code_detected_with_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd.shutil, "which", lambda _name: "/usr/local/bin/claude")

    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout="claude 1.2.3\n", stderr=""
        )

    monkeypatch.setattr(pd.subprocess, "run", fake_run)

    result = pd.detect_claude_code()

    assert result == {
        "detected": True,
        "path": "/usr/local/bin/claude",
        "version": "claude 1.2.3",
    }


def test_claude_code_detected_but_version_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd.shutil, "which", lambda _name: "/usr/local/bin/claude")

    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="claude", timeout=5)

    monkeypatch.setattr(pd.subprocess, "run", fake_run)

    result = pd.detect_claude_code()

    assert result == {"detected": True, "path": "/usr/local/bin/claude", "version": None}


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------


def test_ollama_not_running(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(*_args: Any, **_kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(pd.httpx, "get", fake_get)

    assert pd.detect_ollama() == {"detected": False, "models": []}


def test_ollama_running_with_models(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"models": [{"name": "llama3:8b"}, {"name": "mistral"}, {"not_a_model": True}]}

    def fake_get(*_args: Any, **_kwargs: Any) -> httpx.Response:
        return httpx.Response(200, json=payload)

    monkeypatch.setattr(pd.httpx, "get", fake_get)

    result = pd.detect_ollama()

    assert result == {"detected": True, "models": ["llama3:8b", "mistral"]}


def test_ollama_running_but_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(*_args: Any, **_kwargs: Any) -> httpx.Response:
        return httpx.Response(503)

    monkeypatch.setattr(pd.httpx, "get", fake_get)

    assert pd.detect_ollama() == {"detected": False, "models": []}


# ---------------------------------------------------------------------------
# /api/setup endpoints
# ---------------------------------------------------------------------------


def _patch_all_detectors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pd, "detect_anthropic_api", lambda: {"key_in_env": True, "key_in_keychain": False}
    )
    monkeypatch.setattr(
        pd,
        "detect_claude_code",
        lambda: {"detected": False, "path": None, "version": None},
    )
    monkeypatch.setattr(pd, "detect_ollama", lambda: {"detected": False, "models": []})


def test_detect_providers_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all_detectors(monkeypatch)

    response = client.post("/api/setup/detect-providers")

    assert response.status_code == 200
    body = response.json()
    assert body["anthropic_api"] == {"key_in_env": True, "key_in_keychain": False}
    assert body["claude_code"]["detected"] is False
    assert body["ollama"] == {"detected": False, "models": []}


def test_test_provider_endpoint_mock_always_succeeds() -> None:
    response = client.post("/api/setup/test-provider", json={"provider": "mock"})

    assert response.status_code == 200
    body = response.json()
    assert body == {"ok": True, "latency_ms": 0, "error": None, "error_kind": None}


def test_test_provider_endpoint_claude_code_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import provider_setup as ps

    monkeypatch.setattr(ps.shutil, "which", lambda _name: None)

    response = client.post("/api/setup/test-provider", json={"provider": "claude_code"})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error_kind"] == "binary_missing"


def test_test_provider_endpoint_claude_code_version_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import provider_setup as ps

    monkeypatch.setattr(ps.shutil, "which", lambda _name: "/fake/claude")

    def fake_run(*_a: Any, **_k: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="claude 2.0.0\n")

    monkeypatch.setattr(ps.subprocess, "run", fake_run)

    response = client.post("/api/setup/test-provider", json={"provider": "claude_code"})

    body = response.json()
    assert body["ok"] is True
    assert body["error_kind"] is None


def test_test_provider_endpoint_ollama_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import provider_setup as ps

    def fake_get(*_a: Any, **_k: Any) -> httpx.Response:
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(ps.httpx, "get", fake_get)

    response = client.post("/api/setup/test-provider", json={"provider": "ollama"})

    body = response.json()
    assert body["ok"] is False
    assert body["error_kind"] == "network_error"


def test_test_provider_endpoint_ollama_model_not_pulled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import provider_setup as ps

    def fake_get(*_a: Any, **_k: Any) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "mistral"}]})

    monkeypatch.setattr(ps.httpx, "get", fake_get)

    response = client.post(
        "/api/setup/test-provider",
        json={"provider": "ollama", "model": "qwen2.5:14b"},
    )

    body = response.json()
    assert body["ok"] is False
    assert body["error_kind"] == "model_unavailable"
    assert "ollama pull" in body["error"]


def test_test_provider_endpoint_ollama_model_present(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import provider_setup as ps

    def fake_get(*_a: Any, **_k: Any) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "qwen2.5:14b"}]})

    monkeypatch.setattr(ps.httpx, "get", fake_get)

    response = client.post(
        "/api/setup/test-provider",
        json={"provider": "ollama", "model": "qwen2.5:14b"},
    )

    body = response.json()
    assert body["ok"] is True
    assert body["error_kind"] is None


def test_test_provider_endpoint_missing_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from llm import credentials

    monkeypatch.setattr(credentials, "get_credential", lambda _name: None)

    response = client.post(
        "/api/setup/test-provider",
        json={"provider": "anthropic_api", "api_key": None},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error_kind"] == "missing_api_key"


# ---------------------------------------------------------------------------
# /api/setup/select-provider
# ---------------------------------------------------------------------------


def test_select_provider_persists_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy import select as sa_select

    from db.migrations import run_migrations
    from db.models import AppConfig
    from db.session import get_session

    run_migrations()

    response = client.post("/api/setup/select-provider", json={"provider": "mock", "api_key": None})

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["model"] is None

    with get_session() as session:
        provider = session.execute(
            sa_select(AppConfig.value).where(AppConfig.key == "provider")
        ).scalar_one()
    assert provider == "mock"


def test_select_provider_anthropic_stores_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from db.migrations import run_migrations

    run_migrations()

    stored: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "api.routes.setup.set_credential",
        lambda name, value: stored.append((name, value)),
    )

    response = client.post(
        "/api/setup/select-provider",
        json={"provider": "anthropic_api", "api_key": "sk-ant-XXXX"},
    )

    assert response.status_code == 200
    assert stored == [("anthropic_api_key", "sk-ant-XXXX")]
    body = response.json()
    assert body["provider"] == "anthropic_api"
    assert body["model"] == "claude-opus-4-7"


def test_select_provider_claude_code_now_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    from db.migrations import run_migrations

    run_migrations()

    response = client.post(
        "/api/setup/select-provider",
        json={"provider": "claude_code", "api_key": None},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "claude_code"
    assert body["model"] is None  # claude_code uses whatever the CLI is configured for


def test_select_provider_ollama_persists_model(monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy import select as sa_select

    from db.migrations import run_migrations
    from db.models import AppConfig
    from db.session import get_session

    run_migrations()

    response = client.post(
        "/api/setup/select-provider",
        json={"provider": "ollama", "model": "llama3.2:3b"},
    )
    assert response.status_code == 200
    assert response.json() == {"provider": "ollama", "model": "llama3.2:3b"}

    with get_session() as session:
        rows = session.execute(
            sa_select(AppConfig.key, AppConfig.value).where(
                AppConfig.key.in_(["provider", "model"])
            )
        ).all()
    config = dict(rows)
    assert config["provider"] == "ollama"
    assert config["model"] == "llama3.2:3b"


def test_select_provider_rejects_unknown_provider() -> None:
    response = client.post(
        "/api/setup/select-provider", json={"provider": "not-a-thing", "api_key": None}
    )
    assert response.status_code == 400


def test_list_providers_returns_metadata_with_experimental_flag() -> None:
    response = client.get("/api/setup/providers")
    assert response.status_code == 200
    body = response.json()
    by_name = {entry["name"]: entry for entry in body}
    assert by_name["claude_code"]["is_experimental"] is True
    assert by_name["anthropic_api"]["is_experimental"] is False
    assert by_name["ollama"]["default_model"] == "qwen2.5:14b"
    assert by_name["anthropic_api"]["requires_api_key"] is True
