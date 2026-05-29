"""Public entry point for the LLM provider layer.

Business logic should only ever import:

    from backend.llm import get_provider
    from backend.llm.types import Profile, Job, ScoreResult, ...

`get_provider()` reads the configured provider + model from `app_config`,
constructs the adapter, and caches it for the rest of the process. Tests
can use `reset_provider_cache()` between cases.

The factory keeps every concrete adapter import scoped to this module.
"""

from __future__ import annotations

from sqlalchemy import select

from db.models import AppConfig
from db.session import get_session

from .base import LLMProvider
from .errors import LLMAuthError, LLMError, LLMNetworkError, LLMRateLimitError, LLMResponseError
from .mock import MockProvider
from .recorder import RecordingProvider
from .types import (
    AnswerFeedback,
    ChatMessage,
    ChatRole,
    CompanyBrief,
    CoverLetter,
    ImprovementNote,
    InterviewCategory,
    InterviewDifficulty,
    InterviewQuestion,
    Job,
    Profile,
    ScoreResult,
    WorkExperience,
)

_provider_cache: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Return the configured LLM provider, building it on first call."""
    global _provider_cache
    if _provider_cache is None:
        _provider_cache = _build_provider()
    return _provider_cache


def reset_provider_cache() -> None:
    """Clear the cached provider. Call after `provider`/`model` config changes."""
    global _provider_cache
    _provider_cache = None


def _read_config() -> tuple[str, str | None]:
    """Read (provider, model) from app_config. Defaults to ('mock', None)."""
    with get_session() as session:
        rows = session.execute(
            select(AppConfig.key, AppConfig.value).where(AppConfig.key.in_(["provider", "model"]))
        ).all()
    config = {key: value for key, value in rows}
    provider = config.get("provider") or "mock"
    model = config.get("model")
    return provider, model


def _build_provider() -> LLMProvider:
    provider_name, model = _read_config()
    inner = _build_inner_provider(provider_name, model)
    return RecordingProvider(inner, provider_name)


def _build_inner_provider(provider_name: str, model: str | None) -> LLMProvider:
    if provider_name == "mock":
        return MockProvider()

    if provider_name == "anthropic_api":
        # Imported lazily so MockProvider users don't pay the SDK import cost.
        from .anthropic_api import DEFAULT_MODEL, AnthropicAPIAdapter

        return AnthropicAPIAdapter(model=model or DEFAULT_MODEL)

    if provider_name == "claude_code":
        from .claude_code import ClaudeCodeAdapter

        return ClaudeCodeAdapter()

    if provider_name == "codex_cli":
        from .codex_cli import CodexCLIAdapter

        # No model is passed: Codex uses its own ``~/.codex/config.toml``
        # default so the app-wide ``app_config.model`` (an Anthropic default)
        # never leaks into the ``codex -m`` flag. Mirrors ClaudeCodeAdapter.
        return CodexCLIAdapter()

    if provider_name == "ollama":
        from .ollama import DEFAULT_MODEL as OLLAMA_DEFAULT_MODEL
        from .ollama import OllamaAdapter

        return OllamaAdapter(model=model or OLLAMA_DEFAULT_MODEL)

    raise LLMError(
        f"Unknown provider '{provider_name}'. Set app_config.provider to one of "
        "'mock', 'anthropic_api', 'claude_code', 'codex_cli', or 'ollama'."
    )


__all__ = [
    "AnswerFeedback",
    "ChatMessage",
    "ChatRole",
    "CompanyBrief",
    "CoverLetter",
    "ImprovementNote",
    "InterviewCategory",
    "InterviewDifficulty",
    "InterviewQuestion",
    "Job",
    "LLMAuthError",
    "LLMError",
    "LLMNetworkError",
    "LLMProvider",
    "LLMRateLimitError",
    "LLMResponseError",
    "MockProvider",
    "Profile",
    "RecordingProvider",
    "ScoreResult",
    "WorkExperience",
    "get_provider",
    "reset_provider_cache",
]
