"""OS-keychain wrapper for secrets.

Hired. is local-first: API keys belong in the user's keychain, never in a
config file or environment variable that lives on disk. The `keyring` package
abstracts macOS Keychain, Windows Credential Manager, and Linux Secret
Service behind one API.

We deliberately keep this module tiny so it's easy to monkeypatch in tests.

Service name `dev.hired.app` mirrors the Tauri bundle identifier so
credentials show up alongside the app in OS keychain UIs.

⚠️ Never log credential values. Functions accept and return strings, but only
the credential `name` may appear in logs.
"""

from __future__ import annotations

import contextlib

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

SERVICE_NAME = "dev.hired.app"


def get_credential(name: str) -> str | None:
    """Read a credential from the OS keychain. Returns None if absent."""
    try:
        return keyring.get_password(SERVICE_NAME, name)
    except KeyringError:
        return None


def set_credential(name: str, value: str) -> None:
    """Store a credential in the OS keychain.

    Raises KeyringError if the keychain backend rejects the write.
    """
    keyring.set_password(SERVICE_NAME, name, value)


def delete_credential(name: str) -> None:
    """Remove a credential. No-op if it doesn't exist."""
    with contextlib.suppress(PasswordDeleteError):
        keyring.delete_password(SERVICE_NAME, name)


__all__ = ["SERVICE_NAME", "delete_credential", "get_credential", "set_credential"]
