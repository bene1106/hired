"""Local voice service (M4): Piper TTS + faster-whisper STT.

Everything runs on the user's machine. Models are downloaded on first use into
``~/.hired/models/`` (override with ``HIRED_MODELS_DIR``) so the installer stays
lean and the feature is fully offline afterwards.

The heavy deps (``faster_whisper``, ``piper``) are imported lazily: if they're
not installed the rest of the app keeps working and ``voice_status`` simply
reports ``deps_available=False`` so the UI can hide/disable voice.
"""

from __future__ import annotations

import io
import os
import threading
import wave
from pathlib import Path
from typing import Any

import httpx

WHISPER_MODEL_SIZE = "base"

_PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# One male + one female en_US voice. ``unspecified`` falls back to female.
PIPER_VOICES: dict[str, dict[str, str]] = {
    "female": {
        "name": "en_US-amy-medium",
        "rel": "en/en_US/amy/medium/en_US-amy-medium",
    },
    "male": {
        "name": "en_US-ryan-medium",
        "rel": "en/en_US/ryan/medium/en_US-ryan-medium",
    },
}


def models_dir() -> Path:
    """Where voice models live. Mirrors ``db/session.py``'s ~/.hired convention."""
    override = os.environ.get("HIRED_MODELS_DIR")
    base = Path(override) if override else Path.home() / ".hired" / "models"
    return base


def _whisper_dir() -> Path:
    return models_dir() / "whisper"


def _piper_dir() -> Path:
    return models_dir() / "piper"


def _voice_for(gender: str | None) -> dict[str, str]:
    return PIPER_VOICES.get((gender or "").lower(), PIPER_VOICES["female"])


# ---------------------------------------------------------------------------
# Capability / status
# ---------------------------------------------------------------------------


def deps_available() -> bool:
    """True when both voice libraries import cleanly."""
    try:
        import faster_whisper  # noqa: F401
        import piper  # noqa: F401

        return True
    except Exception:
        return False


def models_ready() -> bool:
    """True when the Whisper model and both Piper voices are present on disk."""
    whisper_present = _whisper_dir().exists() and any(_whisper_dir().iterdir())
    if not whisper_present:
        return False
    for voice in PIPER_VOICES.values():
        onnx = _piper_dir() / f"{voice['name']}.onnx"
        config = _piper_dir() / f"{voice['name']}.onnx.json"
        if not onnx.exists() or not config.exists():
            return False
    return True


# Tiny in-memory prepare-progress tracker (mirrors generation_progress).
_prepare_state: dict[str, Any] = {"state": "idle", "error": None}
_prepare_lock = threading.Lock()


def prepare_state() -> dict[str, Any]:
    with _prepare_lock:
        return dict(_prepare_state)


def voice_status() -> dict[str, Any]:
    return {
        "deps_available": deps_available(),
        "models_ready": models_ready(),
        "prepare_state": prepare_state()["state"],
        "error": prepare_state()["error"],
    }


# ---------------------------------------------------------------------------
# Model download
# ---------------------------------------------------------------------------


def _download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_bytes():
                fh.write(chunk)


def ensure_models() -> None:
    """Download the Whisper model and Piper voices if missing. Idempotent."""
    if not deps_available():
        raise RuntimeError("Voice dependencies are not installed.")

    from faster_whisper import WhisperModel

    _whisper_dir().mkdir(parents=True, exist_ok=True)
    # Instantiating with a download_root pulls the model on first use.
    WhisperModel(
        WHISPER_MODEL_SIZE, device="cpu", compute_type="int8", download_root=str(_whisper_dir())
    )

    for voice in PIPER_VOICES.values():
        for suffix in (".onnx", ".onnx.json"):
            dest = _piper_dir() / f"{voice['name']}{suffix}"
            if not dest.exists():
                _download_file(f"{_PIPER_BASE}/{voice['rel']}{suffix}", dest)


def prepare_models() -> None:
    """Run ``ensure_models`` while tracking progress for the status endpoint."""
    with _prepare_lock:
        if _prepare_state["state"] == "downloading":
            return
        _prepare_state["state"] = "downloading"
        _prepare_state["error"] = None
    try:
        ensure_models()
        with _prepare_lock:
            _prepare_state["state"] = "ready"
    except Exception as exc:  # noqa: BLE001 — surface to the UI, don't crash
        with _prepare_lock:
            _prepare_state["state"] = "error"
            _prepare_state["error"] = str(exc)


# ---------------------------------------------------------------------------
# Inference (lazy-loaded singletons)
# ---------------------------------------------------------------------------

_whisper_model: Any = None
_piper_cache: dict[str, Any] = {}
_model_lock = threading.Lock()


def _whisper() -> Any:
    global _whisper_model
    with _model_lock:
        if _whisper_model is None:
            from faster_whisper import WhisperModel

            _whisper_model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device="cpu",
                compute_type="int8",
                download_root=str(_whisper_dir()),
            )
    return _whisper_model


def _piper(gender: str | None) -> Any:
    voice = _voice_for(gender)
    name = voice["name"]
    with _model_lock:
        if name not in _piper_cache:
            from piper import PiperVoice

            onnx = _piper_dir() / f"{name}.onnx"
            config = _piper_dir() / f"{name}.onnx.json"
            _piper_cache[name] = PiperVoice.load(str(onnx), config_path=str(config))
    return _piper_cache[name]


def transcribe(audio_bytes: bytes) -> str:
    """Transcribe recorded audio (webm/opus or wav) to text."""
    model = _whisper()
    segments, _info = model.transcribe(io.BytesIO(audio_bytes))
    return " ".join(segment.text for segment in segments).strip()


def synthesize(text: str, gender: str | None) -> bytes:
    """Render ``text`` to WAV bytes in the gendered voice."""
    voice = _piper(gender)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        voice.synthesize(text, wav_file)
    return buf.getvalue()
