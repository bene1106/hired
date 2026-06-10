"""Onboarding-time provider detection, test, and selection endpoints.

Phase 6 unblocks ``claude_code`` and ``ollama`` selection. The setup
flow now persists both ``provider`` and (optionally) ``model`` to
``app_config`` so the factory builds the right adapter on next call,
and exposes ``GET /api/setup/providers`` so the UI can render an
"Experimental" badge for the gray-zone Claude Code option without
hard-coding the list on the frontend.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from typing_extensions import TypedDict

from db.models import AppConfig
from db.session import get_session
from llm import reset_provider_cache
from llm.anthropic_api import ANTHROPIC_API_KEY_NAME
from llm.anthropic_api import DEFAULT_MODEL as ANTHROPIC_DEFAULT_MODEL
from llm.credentials import set_credential
from llm.ollama import DEFAULT_MODEL as OLLAMA_DEFAULT_MODEL
from services.provider_detection import ProviderDetectionResult, detect_all
from services.provider_setup import TestProviderResult, test_provider

router = APIRouter(prefix="/api/setup", tags=["setup"])

_SELECTABLE_PROVIDERS = {"mock", "anthropic_api", "claude_code", "codex_cli", "ollama"}


class ProviderMetadata(TypedDict):
    """One provider option as the onboarding UI renders it.

    ``label`` is the user-visible name. ``is_experimental`` drives the
    yellow "Experimental" badge — the CLI providers (``claude_code`` and
    ``codex_cli``) carry it (per ADR-0005 R-01 / ADR-0010 the CLIs are a
    documented gray zone). ``requires_api_key``
    tells the wizard whether to render the API-key input. ``default_model``
    is what we save to ``app_config`` if the user doesn't override.
    """

    name: str
    label: str
    is_experimental: bool
    requires_api_key: bool
    default_model: str | None


_PROVIDER_METADATA: list[ProviderMetadata] = [
    {
        "name": "anthropic_api",
        "label": "Anthropic API",
        "is_experimental": False,
        "requires_api_key": True,
        "default_model": ANTHROPIC_DEFAULT_MODEL,
    },
    {
        "name": "claude_code",
        "label": "Claude Code",
        "is_experimental": True,
        "requires_api_key": False,
        "default_model": None,
    },
    {
        "name": "codex_cli",
        "label": "OpenAI Codex",
        "is_experimental": True,
        "requires_api_key": False,
        "default_model": None,
    },
    {
        "name": "ollama",
        "label": "Ollama (local)",
        "is_experimental": False,
        "requires_api_key": False,
        "default_model": OLLAMA_DEFAULT_MODEL,
    },
    {
        "name": "mock",
        "label": "Mock (dev only)",
        "is_experimental": False,
        "requires_api_key": False,
        "default_model": None,
    },
]


class TestProviderRequest(BaseModel):
    provider: str = Field(
        ..., description="One of: mock, anthropic_api, claude_code, codex_cli, ollama"
    )
    api_key: str | None = None
    model: str | None = None


class SelectProviderRequest(BaseModel):
    provider: str
    api_key: str | None = None
    model: str | None = None


class SelectProviderResponse(BaseModel):
    provider: str
    model: str | None = None


class UpdateModelRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=128)


class UpdateModelResponse(BaseModel):
    model: str


@router.get("/providers", response_model=list[ProviderMetadata])
def list_providers() -> list[ProviderMetadata]:
    """List every provider the wizard can show, with UI-flavored metadata."""
    return _PROVIDER_METADATA


@router.post("/detect-providers")
def detect_providers() -> ProviderDetectionResult:
    """Probe the local machine for installed/configured providers."""
    return detect_all()


@router.post("/test-provider")
def test_provider_endpoint(payload: TestProviderRequest) -> TestProviderResult:
    """Run a tiny round-trip against the requested provider."""
    return test_provider(payload.provider, payload.api_key, model=payload.model)


@router.post("/select-provider", response_model=SelectProviderResponse)
def select_provider(payload: SelectProviderRequest) -> SelectProviderResponse:
    """Commit the user's provider choice. Persists app_config + keychain."""
    if payload.provider not in _SELECTABLE_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{payload.provider}' is not a known option.",
        )

    if payload.provider == "anthropic_api" and payload.api_key:
        set_credential(ANTHROPIC_API_KEY_NAME, payload.api_key)

    resolved_model = _resolve_model(payload.provider, payload.model)

    with get_session() as session:
        _upsert_config(session, "provider", payload.provider)
        if resolved_model is not None:
            _upsert_config(session, "model", resolved_model)
        session.commit()

    reset_provider_cache()
    return SelectProviderResponse(provider=payload.provider, model=resolved_model)


@router.put("/model", response_model=UpdateModelResponse)
def update_model(payload: UpdateModelRequest) -> UpdateModelResponse:
    """Update only the active model without changing the provider."""
    with get_session() as session:
        _upsert_config(session, "model", payload.model)
        session.commit()
    reset_provider_cache()
    return UpdateModelResponse(model=payload.model)


def _resolve_model(provider: str, requested: str | None) -> str | None:
    """Pick the model to persist for ``provider``.

    A user-supplied ``requested`` always wins. Otherwise we fall back
    to whatever metadata flagged as the default for that provider.
    Mock and Claude Code don't pin a model — claude_code uses whatever
    the CLI is configured for; mock has no concept of a model.
    """
    if requested:
        return requested
    for entry in _PROVIDER_METADATA:
        if entry["name"] == provider:
            return entry["default_model"]
    return None


def _upsert_config(session, key: str, value: str) -> None:
    row = session.execute(select(AppConfig).where(AppConfig.key == key)).scalar_one_or_none()
    if row is None:
        session.add(AppConfig(key=key, value=value))
    else:
        row.value = value
