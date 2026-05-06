"""Onboarding-time provider detection and test endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.provider_detection import ProviderDetectionResult, detect_all
from services.provider_setup import TestProviderResult, test_provider

router = APIRouter(prefix="/api/setup", tags=["setup"])


class TestProviderRequest(BaseModel):
    provider: str = Field(..., description="One of: mock, anthropic_api, claude_code, ollama")
    api_key: str | None = None


@router.post("/detect-providers")
def detect_providers() -> ProviderDetectionResult:
    """Probe the local machine for installed/configured providers."""
    return detect_all()


@router.post("/test-provider")
def test_provider_endpoint(payload: TestProviderRequest) -> TestProviderResult:
    """Run a tiny round-trip against the requested provider."""
    return test_provider(payload.provider, payload.api_key)
