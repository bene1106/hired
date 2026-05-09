"""In-process crawl progress registry.

A user clicks Crawl → we hand back a job id and start the work in a
background task. The UI polls ``GET /api/jobs/crawl/status/{id}`` to
render a progress indicator.

**Lifetime constraint:** progress lives in a module-level dict. It
resets on backend restart. The Phase 4 spec accepts this for MVP — a
crawl that loses its status on restart is a small UX cost compared to
adding a persistence layer for ephemeral state. If this ever becomes
painful in real use, persist to ``app_config`` or a dedicated table.

The registry is bounded (``_MAX_ENTRIES``) and entries get evicted in
insertion order to keep memory predictable across many crawls.
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

CrawlState = Literal["queued", "running", "done", "error"]

_MAX_ENTRIES = 50


@dataclass
class CrawlProgress:
    job_id: str
    state: CrawlState = "queued"
    fetched: int = 0
    total: int = 0
    new: int = 0
    duplicates: int = 0
    scored: int = 0
    error: str | None = None
    new_job_ids: list[int] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


class _ProgressRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, CrawlProgress] = OrderedDict()

    def create(self) -> CrawlProgress:
        with self._lock:
            entry = CrawlProgress(job_id=uuid.uuid4().hex)
            self._entries[entry.job_id] = entry
            while len(self._entries) > _MAX_ENTRIES:
                self._entries.popitem(last=False)
            return entry

    def get(self, job_id: str) -> CrawlProgress | None:
        with self._lock:
            return self._entries.get(job_id)

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            entry = self._entries.get(job_id)
            if entry is None:
                return
            for key, value in fields.items():
                setattr(entry, key, value)

    def reset(self) -> None:
        """Clear all entries — used by tests."""
        with self._lock:
            self._entries.clear()


_REGISTRY = _ProgressRegistry()


def create_entry() -> CrawlProgress:
    return _REGISTRY.create()


def get_entry(job_id: str) -> CrawlProgress | None:
    return _REGISTRY.get(job_id)


def update_entry(job_id: str, **fields) -> None:
    _REGISTRY.update(job_id, **fields)


def reset_registry() -> None:
    _REGISTRY.reset()


__all__ = [
    "CrawlProgress",
    "CrawlState",
    "create_entry",
    "get_entry",
    "reset_registry",
    "update_entry",
]
