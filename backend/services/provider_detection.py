"""Detect which LLM providers the user already has on their machine.

Powers the onboarding wizard's "pick a provider" step. All checks are
defensive: any failure (missing binary, refused connection, malformed
response) returns ``detected: false`` instead of raising.

- **Anthropic API**: presence of ``ANTHROPIC_API_KEY`` env var or a
  matching keychain entry. We do not validate the key here — that's
  ``test_provider`` (one round-trip to the API).
- **Claude Code**: ``shutil.which("claude")`` then ``claude --version``.
- **Ollama**: HTTP GET ``http://localhost:11434/api/tags``; if 200, list
  the model names.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import TypedDict

import httpx

from llm.anthropic_api import ANTHROPIC_API_KEY_NAME
from llm.credentials import get_credential

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/tags"
_VERSION_TIMEOUT_S = 5.0
_OLLAMA_TIMEOUT_S = 2.0


class AnthropicDetection(TypedDict):
    key_in_env: bool
    key_in_keychain: bool


class ClaudeCodeDetection(TypedDict):
    detected: bool
    path: str | None
    version: str | None


class OllamaDetection(TypedDict):
    detected: bool
    models: list[str]


class ProviderDetectionResult(TypedDict):
    anthropic_api: AnthropicDetection
    claude_code: ClaudeCodeDetection
    ollama: OllamaDetection


def detect_anthropic_api() -> AnthropicDetection:
    """Check whether an Anthropic API key is reachable from env or keychain."""
    key_in_env = bool(os.environ.get("ANTHROPIC_API_KEY"))
    key_in_keychain = get_credential(ANTHROPIC_API_KEY_NAME) is not None
    return {"key_in_env": key_in_env, "key_in_keychain": key_in_keychain}


def detect_claude_code() -> ClaudeCodeDetection:
    """Locate the ``claude`` CLI and run ``claude --version`` if found."""
    path = shutil.which("claude")
    if not path:
        return {"detected": False, "path": None, "version": None}

    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=_VERSION_TIMEOUT_S,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("claude --version failed: %s", exc)
        return {"detected": True, "path": path, "version": None}

    version = (result.stdout or result.stderr or "").strip() or None
    return {"detected": True, "path": path, "version": version}


def detect_ollama() -> OllamaDetection:
    """Hit the local Ollama API; return the list of installed model names."""
    try:
        response = httpx.get(OLLAMA_URL, timeout=_OLLAMA_TIMEOUT_S)
    except httpx.HTTPError as exc:
        logger.debug("ollama not reachable: %s", exc)
        return {"detected": False, "models": []}

    if response.status_code != 200:
        return {"detected": False, "models": []}

    try:
        payload = response.json()
    except ValueError:
        return {"detected": True, "models": []}

    models = payload.get("models") or []
    names = [m.get("name") for m in models if isinstance(m, dict) and m.get("name")]
    return {"detected": True, "models": names}


def detect_all() -> ProviderDetectionResult:
    """Run every detector. None of them raises."""
    return {
        "anthropic_api": detect_anthropic_api(),
        "claude_code": detect_claude_code(),
        "ollama": detect_ollama(),
    }


__all__ = [
    "AnthropicDetection",
    "ClaudeCodeDetection",
    "OllamaDetection",
    "ProviderDetectionResult",
    "detect_all",
    "detect_anthropic_api",
    "detect_claude_code",
    "detect_ollama",
]
