"""Local voice API (M4): TTS + STT + model setup.

All work happens in the sidecar via ``services.voice`` (Piper + faster-whisper).
Models download on first use; until then ``GET /status`` reports what's missing
so the UI can offer a one-time "Set up voice" step.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from services import voice

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB — generous for a single answer.


class VoiceStatusResponse(BaseModel):
    deps_available: bool
    models_ready: bool
    prepare_state: str
    error: str | None


class TtsRequest(BaseModel):
    text: str
    gender: str | None = None


class SttResponse(BaseModel):
    text: str


@router.get("/status", response_model=VoiceStatusResponse)
def get_status() -> VoiceStatusResponse:
    return VoiceStatusResponse(**voice.voice_status())


@router.post("/prepare", response_model=VoiceStatusResponse)
def prepare(background: BackgroundTasks) -> VoiceStatusResponse:
    if not voice.deps_available():
        raise HTTPException(
            status_code=503,
            detail="Voice dependencies are not installed in this build.",
        )
    if not voice.models_ready() and voice.prepare_state()["state"] != "downloading":
        background.add_task(voice.prepare_models)
    return VoiceStatusResponse(**voice.voice_status())


@router.post("/tts")
def text_to_speech(payload: TtsRequest) -> Response:
    if not voice.deps_available() or not voice.models_ready():
        raise HTTPException(status_code=503, detail="Voice models are not ready.")
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty.")
    try:
        audio = voice.synthesize(payload.text, payload.gender)
    except Exception as exc:  # noqa: BLE001
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc
    return Response(content=audio, media_type="audio/wav")


@router.post("/stt", response_model=SttResponse)
async def speech_to_text(
    file: Annotated[UploadFile, File(description="Recorded answer audio")],
) -> SttResponse:
    if not voice.deps_available() or not voice.models_ready():
        raise HTTPException(status_code=503, detail="Voice models are not ready.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty audio upload.")
    if len(data) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio too large.")
    try:
        text = voice.transcribe(data)
    except Exception as exc:  # noqa: BLE001
        logger.exception("STT transcription failed")
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}") from exc
    return SttResponse(text=text)
