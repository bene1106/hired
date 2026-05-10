"""In-process generation progress registry.

The user clicks Apply → we kick off a background task that produces the
three application materials (company brief, CV tailoring, cover letter).
The UI polls ``GET /api/applications/{id}/generation/{task_id}`` for a
sequential reveal as each step finishes.

Same lifetime trade-off as ``crawl_progress``: state lives in a
module-level dict and resets on backend restart. Acceptable for MVP —
generation completes in tens of seconds, so a restart mid-flight is a
rare loss. Promote to a persisted table if it ever bites a real user.

The state field tracks which steps are done so the UI can render each
section as it lands instead of waiting for the whole pipeline.
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

GenerationState = Literal["queued", "running", "done", "error"]
StepName = Literal["company_brief", "cv_suggestions", "cover_letter"]
StepState = Literal["pending", "running", "done", "error", "cached"]

_MAX_ENTRIES = 50


@dataclass
class GenerationProgress:
    task_id: str
    application_id: int
    state: GenerationState = "queued"
    company_brief: StepState = "pending"
    cv_suggestions: StepState = "pending"
    cover_letter: StepState = "pending"
    error: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


class _ProgressRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, GenerationProgress] = OrderedDict()

    def create(self, application_id: int) -> GenerationProgress:
        with self._lock:
            entry = GenerationProgress(
                task_id=uuid.uuid4().hex, application_id=application_id
            )
            self._entries[entry.task_id] = entry
            while len(self._entries) > _MAX_ENTRIES:
                self._entries.popitem(last=False)
            return entry

    def get(self, task_id: str) -> GenerationProgress | None:
        with self._lock:
            return self._entries.get(task_id)

    def update(self, task_id: str, **fields) -> None:
        with self._lock:
            entry = self._entries.get(task_id)
            if entry is None:
                return
            for key, value in fields.items():
                setattr(entry, key, value)

    def reset(self) -> None:
        """Clear all entries — used by tests."""
        with self._lock:
            self._entries.clear()


_REGISTRY = _ProgressRegistry()


def create_entry(application_id: int) -> GenerationProgress:
    return _REGISTRY.create(application_id)


def get_entry(task_id: str) -> GenerationProgress | None:
    return _REGISTRY.get(task_id)


def update_entry(task_id: str, **fields) -> None:
    _REGISTRY.update(task_id, **fields)


def reset_registry() -> None:
    _REGISTRY.reset()


__all__ = [
    "GenerationProgress",
    "GenerationState",
    "StepName",
    "StepState",
    "create_entry",
    "get_entry",
    "reset_registry",
    "update_entry",
]
