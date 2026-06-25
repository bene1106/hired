"""Voice API tests. The heavy libs are monkeypatched so CI never downloads
models or imports faster-whisper/piper."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import app
from services import voice

client = TestClient(app)


@pytest.fixture
def voice_ready(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Pretend deps + models are present and stub inference."""
    monkeypatch.setattr(voice, "deps_available", lambda: True)
    monkeypatch.setattr(voice, "models_ready", lambda: True)
    monkeypatch.setattr(voice, "synthesize", lambda text, gender: b"RIFFfake-wav-bytes")
    monkeypatch.setattr(voice, "transcribe", lambda audio: "transcribed answer")
    yield


def test_status_reports_unavailable_without_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice, "deps_available", lambda: False)
    monkeypatch.setattr(voice, "models_ready", lambda: False)
    body = client.get("/api/voice/status").json()
    assert body["deps_available"] is False
    assert body["models_ready"] is False


def test_prepare_503_when_deps_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice, "deps_available", lambda: False)
    res = client.post("/api/voice/prepare")
    assert res.status_code == 503


def test_tts_returns_wav_audio(voice_ready: None) -> None:
    res = client.post("/api/voice/tts", json={"text": "Hello there", "gender": "female"})
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/wav"
    assert res.content == b"RIFFfake-wav-bytes"


def test_tts_422_on_empty_text(voice_ready: None) -> None:
    res = client.post("/api/voice/tts", json={"text": "   ", "gender": "male"})
    assert res.status_code == 422


def test_tts_503_when_models_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice, "deps_available", lambda: True)
    monkeypatch.setattr(voice, "models_ready", lambda: False)
    res = client.post("/api/voice/tts", json={"text": "Hi", "gender": "female"})
    assert res.status_code == 503


def test_stt_transcribes_uploaded_audio(voice_ready: None) -> None:
    res = client.post(
        "/api/voice/stt",
        files={"file": ("answer.webm", b"fake-audio-bytes", "audio/webm")},
    )
    assert res.status_code == 200
    assert res.json()["text"] == "transcribed answer"


def test_stt_422_on_empty_upload(voice_ready: None) -> None:
    res = client.post(
        "/api/voice/stt",
        files={"file": ("answer.webm", b"", "audio/webm")},
    )
    assert res.status_code == 422


def test_voice_for_maps_gender() -> None:
    assert voice._voice_for("male")["name"] == "en_US-ryan-medium"
    assert voice._voice_for("female")["name"] == "en_US-amy-medium"
    # Unknown/None falls back to the female voice.
    assert voice._voice_for(None)["name"] == "en_US-amy-medium"
    assert voice._voice_for("unspecified")["name"] == "en_US-amy-medium"
