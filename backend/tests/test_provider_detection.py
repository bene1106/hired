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


def test_test_provider_endpoint_unsupported_provider() -> None:
    response = client.post("/api/setup/test-provider", json={"provider": "claude_code"})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error_kind"] == "unsupported_provider"


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
