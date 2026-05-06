"""Shared FastAPI dependencies.

Routes never import provider adapters directly — they ask for an
``LLMProvider`` via ``Depends(get_llm_provider)`` and get whatever the
factory built at startup. This is the seam tests use to swap a
``MockProvider`` in.
"""

from __future__ import annotations

from llm import LLMProvider, get_provider


def get_llm_provider() -> LLMProvider:
    return get_provider()
