"""Crawler base types — the abstract source contract every adapter implements.

A ``JobSource`` knows how to take a ``CrawlQuery`` (the user's profile-driven
search params plus a cap) and produce a stream of ``RawJob`` records. The
orchestrator handles deduplication and persistence — sources only worry
about fetching and normalizing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CrawlQuery:
    """What the user is looking for. Sources translate this to their own API."""

    target_roles: list[str] = field(default_factory=list)
    target_locations: list[str] = field(default_factory=list)
    max_jobs: int = 20
    # Source-specific hints. ``manual_urls`` reads ``urls``; LinkedIn ignores it.
    urls: list[str] = field(default_factory=list)


@dataclass
class RawJob:
    """One scraped job, normalized to the shape the DB expects.

    ``source`` + ``source_id`` together must be globally unique within the
    source — the DB enforces this and the orchestrator dedupes against
    existing rows before insert.
    """

    source: str
    source_id: str
    title: str
    company: str | None = None
    location: str | None = None
    remote_policy: str | None = None  # "remote" | "hybrid" | "onsite" | None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    description: str | None = None
    url: str | None = None
    posted_at: datetime | None = None


class JobSource(ABC):
    """Abstract source. Concrete subclasses live alongside this file."""

    name: str  # Stable identifier persisted as ``jobs.source``.

    @abstractmethod
    def fetch_jobs(self, query: CrawlQuery) -> Iterable[RawJob]:
        """Yield up to ``query.max_jobs`` ``RawJob`` records."""


__all__ = ["CrawlQuery", "JobSource", "RawJob"]
