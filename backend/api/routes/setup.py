"""Onboarding-time provider detection, test, and selection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from db.models import AppConfig
from db.session import get_session
from llm import reset_provider_cache
from llm.anthropic_api import ANTHROPIC_API_KEY_NAME
from llm.credentials import set_credential
from services.provider_detection import ProviderDetectionResult, detect_all
from services.provider_setup import TestProviderResult, test_provider

router = APIRouter(prefix="/api/setup", tags=["setup"])

_SUPPORTED_PROVIDERS_PHASE_3 = {"mock", "anthropic_api"}


class TestProviderRequest(BaseModel):
    provider: str = Field(..., description="One of: mock, anthropic_api, claude_code, ollama")
    api_key: str | None = None


class SelectProviderRequest(BaseModel):
    provider: str
    api_key: str | None = None


class SelectProviderResponse(BaseModel):
    provider: str


@router.post("/detect-providers")
def detect_providers() -> ProviderDetectionResult:
    """Probe the local machine for installed/configured providers."""
    return detect_all()


@router.post("/test-provider")
def test_provider_endpoint(payload: TestProviderRequest) -> TestProviderResult:
    """Run a tiny round-trip against the requested provider."""
    return test_provider(payload.provider, payload.api_key)


@router.post("/select-provider", response_model=SelectProviderResponse)
def select_provider(payload: SelectProviderRequest) -> SelectProviderResponse:
    """Commit the user's provider choice. Persists app_config + keychain."""
    if payload.provider not in _SUPPORTED_PROVIDERS_PHASE_3:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{payload.provider}' is not selectable yet (Phase 6).",
        )

    if payload.provider == "anthropic_api" and payload.api_key:
        set_credential(ANTHROPIC_API_KEY_NAME, payload.api_key)

    with get_session() as session:
        row = session.execute(
            select(AppConfig).where(AppConfig.key == "provider")
        ).scalar_one_or_none()
        if row is None:
            session.add(AppConfig(key="provider", value=payload.provider))
        else:
            row.value = payload.provider
        session.commit()

    reset_provider_cache()
    return SelectProviderResponse(provider=payload.provider)
