"""Detect which LLM providers the user already has on their machine.

Powers the onboarding wizard's "pick a provider" step. All checks are
defensive: any failure (missing binary, refused connection, malformed
response) returns ``detected: false`` instead of raising.

- **Anthropic API**: presence of ``ANTHROPIC_API_KEY`` env var or a
  matching keychain entry. We do not validate the key here — that's
  ``test_provider`` (one round-trip to the API).
- **Claude Code**: ``shutil.which("claude")`` then ``claude --version``.
- **Codex CLI**: ``shutil.which("codex")`` then ``codex --version`` and
  ``codex login status`` (so the UI can say "installed but not logged in").
- **Ollama**: HTTP GET ``http://localhost:11434/api/tags``; if 200, list
  the model names.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess

import httpx
from typing_extensions import TypedDict

from llm.anthropic_api import ANTHROPIC_API_KEY_NAME
from llm.codex_cli import CODEX_CLI_NAME
from llm.credentials import get_credential
from llm.openai_api import OPENAI_API_KEY_NAME

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/tags"
_VERSION_TIMEOUT_S = 5.0
_OLLAMA_TIMEOUT_S = 2.0


class AnthropicDetection(TypedDict):
    key_in_env: bool
    key_in_keychain: bool


class OpenAiDetection(TypedDict):
    key_in_env: bool
    key_in_keychain: bool


class ClaudeCodeDetection(TypedDict):
    detected: bool
    path: str | None
    version: str | None


class CodexCliDetection(TypedDict):
    detected: bool
    path: str | None
    version: str | None
    logged_in: bool


class OllamaDetection(TypedDict):
    detected: bool
    models: list[str]


class ProviderDetectionResult(TypedDict):
    anthropic_api: AnthropicDetection
    openai_api: OpenAiDetection
    claude_code: ClaudeCodeDetection
    codex_cli: CodexCliDetection
    ollama: OllamaDetection


def detect_anthropic_api() -> AnthropicDetection:
    """Check whether an Anthropic API key is reachable from env or keychain."""
    key_in_env = bool(os.environ.get("ANTHROPIC_API_KEY"))
    key_in_keychain = get_credential(ANTHROPIC_API_KEY_NAME) is not None
    return {"key_in_env": key_in_env, "key_in_keychain": key_in_keychain}


def detect_openai_api() -> OpenAiDetection:
    """Check whether an OpenAI API key is reachable from env or keychain."""
    key_in_env = bool(os.environ.get("OPENAI_API_KEY"))
    key_in_keychain = get_credential(OPENAI_API_KEY_NAME) is not None
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


def detect_codex_cli() -> CodexCliDetection:
    """Locate the ``codex`` CLI, read its version, and check login status."""
    path = shutil.which(CODEX_CLI_NAME)
    if not path:
        return {"detected": False, "path": None, "version": None, "logged_in": False}
    return {
        "detected": True,
        "path": path,
        "version": _codex_version(path),
        "logged_in": _codex_logged_in(path),
    }


def _codex_version(path: str) -> str | None:
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=_VERSION_TIMEOUT_S,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("codex --version failed: %s", exc)
        return None
    return (result.stdout or result.stderr or "").strip() or None


def _codex_logged_in(path: str) -> bool:
    """Best-effort: ``codex login status`` exits 0 + "Logged in …" when authed."""
    try:
        result = subprocess.run(
            [path, "login", "status"],
            capture_output=True,
            text=True,
            timeout=_VERSION_TIMEOUT_S,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("codex login status failed: %s", exc)
        return False
    if result.returncode != 0:
        return False
    out = (result.stdout or result.stderr or "").lower()
    # "Not logged in" also contains "logged in", so exclude it explicitly.
    return "logged in" in out and "not logged in" not in out


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
        "openai_api": detect_openai_api(),
        "claude_code": detect_claude_code(),
        "codex_cli": detect_codex_cli(),
        "ollama": detect_ollama(),
    }


__all__ = [
    "AnthropicDetection",
    "ClaudeCodeDetection",
    "CodexCliDetection",
    "OllamaDetection",
    "OpenAiDetection",
    "ProviderDetectionResult",
    "detect_all",
    "detect_anthropic_api",
    "detect_claude_code",
    "detect_codex_cli",
    "detect_ollama",
    "detect_openai_api",
]
