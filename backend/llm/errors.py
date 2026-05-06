"""Typed exceptions raised by LLM provider adapters.

Adapters translate provider-specific errors (anthropic.APIError, ConnectionError,
JSON parse errors, ...) into one of these types so callers can catch them
without depending on a specific SDK.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base for every error raised across the LLM provider boundary."""


class LLMAuthError(LLMError):
    """Missing or invalid credentials (e.g., absent API key, 401 from provider)."""


class LLMRateLimitError(LLMError):
    """Provider rejected the request because of rate limits or quota."""


class LLMNetworkError(LLMError):
    """Connection failure, DNS error, timeout — anything below the application layer."""


class LLMResponseError(LLMError):
    """Provider returned a response we couldn't parse into the expected shape."""


__all__ = [
    "LLMAuthError",
    "LLMError",
    "LLMNetworkError",
    "LLMRateLimitError",
    "LLMResponseError",
]
