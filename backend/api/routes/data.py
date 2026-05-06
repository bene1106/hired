"""Destructive endpoint: factory-reset the local install.

The Settings UI exposes this behind a two-step "delete everything" confirm.
After it runs, the next launch should look exactly like a fresh install:

- All user-owned tables truncated.
- ``app_config`` reset to its initial seeds (provider=mock, default model).
- The Anthropic API key removed from the OS keychain (no orphaned secrets
  left behind, per the Phase 3 kickoff decision).
- The cached LLM provider invalidated so the next request rebuilds.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import delete

from db.models import (
    AppConfig,
    Application,
    ApplicationMaterial,
    InterviewSession,
    Job,
    JobScore,
    Profile,
    ProviderCallLog,
)
from db.session import get_session
from llm import reset_provider_cache
from llm.anthropic_api import ANTHROPIC_API_KEY_NAME
from llm.credentials import delete_credential

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["data"])

# Order matters: child rows before parents, even with ON DELETE CASCADE,
# so the DELETE statements remain straightforward to reason about.
_TABLES_IN_DELETE_ORDER = (
    InterviewSession,
    ApplicationMaterial,
    Application,
    JobScore,
    Job,
    Profile,
    ProviderCallLog,
)

_DEFAULT_APP_CONFIG = (
    ("provider", "mock"),
    ("model", "claude-opus-4-7"),
)


class DataWipeResponse(BaseModel):
    deleted: bool = True


@router.delete("/data/all", response_model=DataWipeResponse)
def delete_all_data() -> DataWipeResponse:
    with get_session() as session:
        for model in _TABLES_IN_DELETE_ORDER:
            session.execute(delete(model))

        # app_config is the last to go, then re-seeded so the next request
        # finds the same defaults a brand-new install would.
        session.execute(delete(AppConfig))
        for key, value in _DEFAULT_APP_CONFIG:
            session.add(AppConfig(key=key, value=value))

        session.commit()

    delete_credential(ANTHROPIC_API_KEY_NAME)
    reset_provider_cache()
    logger.info("Local data wiped and provider cache reset.")
    return DataWipeResponse()
