"""Background source scheduler.

Runs a daemon thread that wakes every ``_TICK_SECONDS`` (15 min), loads
enabled ``CrawlSource`` rows, and runs any that are due (``last_checked_at``
is null or older than the configured interval). Scoring piggybacks on the
same ``score_jobs`` call used by the manual crawl pipeline.

The ``SourceScheduler`` singleton is started in ``api.main``'s lifespan and
stopped on shutdown. Routes can call ``run_source_now()`` / ``run_all_now()``
to trigger an immediate out-of-schedule run.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

from db.models import AppConfig
from db.models import CrawlSource as CrawlSourceRow
from db.session import get_session

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_TICK_SECONDS = 900  # how often the scheduler wakes to check for due sources
_DEFAULT_INTERVAL_HOURS = 6

# In-process set of source IDs currently being crawled (resets on restart).
_running: set[int] = set()
_running_phase: dict[int, str] = {}  # source_id → "crawling" | "scoring"
_running_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class SourceScheduler:
    """Daemon thread that periodically runs due job sources."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="source-scheduler")
        self._thread.start()
        logger.info("Source scheduler started (tick=%ds)", _TICK_SECONDS)

    def stop(self) -> None:
        self._stop.set()
        logger.info("Source scheduler stopping")

    def _loop(self) -> None:
        # First tick after a short delay so the app finishes startup.
        if self._stop.wait(timeout=30):
            return
        while True:
            try:
                _tick()
            except Exception:
                logger.exception("Source scheduler tick raised unexpectedly")
            if self._stop.wait(timeout=_TICK_SECONDS):
                break


def run_source_now(source_id: int) -> bool:
    """Run a single source in a background thread. Returns False if already running."""
    with _running_lock:
        if source_id in _running:
            return False
        _running.add(source_id)
        _running_phase[source_id] = "crawling"

    thread = threading.Thread(
        target=_run_one_safe,
        args=(source_id,),
        daemon=True,
        name=f"source-run-{source_id}",
    )
    thread.start()
    return True


def run_all_now() -> list[int]:
    """Run all enabled sources that are not already running. Returns started IDs."""
    with get_session() as session:
        rows = (
            session.execute(select(CrawlSourceRow).where(CrawlSourceRow.enabled.is_(True)))
            .scalars()
            .all()
        )

    started: list[int] = []
    for row in rows:
        if run_source_now(row.id):
            started.append(row.id)
    return started


def is_running(source_id: int) -> bool:
    with _running_lock:
        return source_id in _running


def get_source_phase(source_id: int) -> str | None:
    with _running_lock:
        return _running_phase.get(source_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _tick() -> None:
    """Check all enabled sources and run any that are due."""
    interval_hours = _read_interval_hours()
    if interval_hours == 0:
        return  # scheduler disabled by user
    cutoff = datetime.now(tz=UTC) - timedelta(hours=interval_hours)

    with get_session() as session:
        rows = (
            session.execute(select(CrawlSourceRow).where(CrawlSourceRow.enabled.is_(True)))
            .scalars()
            .all()
        )
        due = [r for r in rows if r.last_checked_at is None or _as_utc(r.last_checked_at) < cutoff]

    logger.debug("Scheduler tick: %d source(s) due out of %d enabled", len(due), len(rows))
    for row in due:
        run_source_now(row.id)


def _run_one_safe(source_id: int) -> None:
    """Wrapper that always clears _running even if _run_one raises."""
    try:
        _run_one(source_id)
    except Exception:
        logger.exception("Unhandled error running source id=%d", source_id)
    finally:
        with _running_lock:
            _running.discard(source_id)
            _running_phase.pop(source_id, None)


def _run_one(source_id: int) -> None:
    """Fetch jobs for a single CrawlSource row and score any new ones."""
    from crawler.service import CrawlResult, crawl
    from llm import get_provider
    from services.scoring_service import ScoringError, score_jobs

    with get_session() as session:
        row = session.get(CrawlSourceRow, source_id)
        if row is None or not row.enabled:
            return
        source_type = row.source_type
        company_slug = row.company_slug

    query = _build_query()

    try:
        source = _build_source(source_type, company_slug)
    except ValueError as exc:
        _mark_done(source_id, error=str(exc))
        return

    logger.info("Running source id=%d type=%s slug=%s", source_id, source_type, company_slug)
    with _running_lock:
        _running_phase[source_id] = "crawling"
    result: CrawlResult = crawl(source, query)

    if result.error:
        _mark_done(source_id, error=result.error)
        return

    ids_to_score = list(result.new_job_ids) + list(result.rescore_job_ids)
    if not ids_to_score:
        company_name = _get_company_from_jobs(result.new_job_ids)
        _mark_done(source_id, error=None, company_name=company_name)
        return

    with _running_lock:
        _running_phase[source_id] = "scoring"
    try:
        provider = get_provider()
        score_jobs(provider, ids_to_score)
    except ScoringError as exc:
        _mark_done(source_id, error=f"Scoring failed: {exc}")
        return
    except Exception as exc:  # noqa: BLE001
        _mark_done(source_id, error=f"{type(exc).__name__}: {exc}")
        return

    company_name = _get_company_from_jobs(result.new_job_ids)
    _mark_done(source_id, error=None, company_name=company_name)
    logger.info(
        "Source id=%d done: fetched=%d new=%d scored=%d",
        source_id,
        result.fetched,
        result.new,
        len(ids_to_score),
    )


def _build_source(source_type: str, company_slug: str | None):  # noqa: ARG001
    from crawler.indeed import IndeedSource
    from crawler.remotive import RemotiveSource
    from crawler.stepstone import StepstoneSource
    from crawler.wellfound import WellfoundSource

    if source_type == "wellfound":
        return WellfoundSource()
    if source_type == "indeed":
        return IndeedSource()
    if source_type == "remotive":
        return RemotiveSource()
    if source_type == "stepstone":
        return StepstoneSource()
    raise ValueError(f"Unknown source_type '{source_type}'")


def _build_query():
    from db.models import Profile as ProfileRow

    with get_session() as session:
        profile = session.execute(select(ProfileRow).limit(1)).scalar_one_or_none()
        if profile is None:
            from crawler.base import CrawlQuery

            return CrawlQuery()
        from crawler.base import CrawlQuery

        return CrawlQuery(
            target_roles=list(profile.target_roles_json or []),
            target_locations=list(profile.target_locations_json or []),
            max_jobs=25,
        )


def _mark_done(source_id: int, error: str | None, company_name: str | None = None) -> None:
    with get_session() as session:
        row = session.get(CrawlSourceRow, source_id)
        if row is not None:
            row.last_checked_at = datetime.now(tz=UTC)
            row.last_error = error
            # Auto-label: if the source label still looks like the slug (never
            # customised), replace it with the real company name from the jobs.
            if company_name and row.company_slug:
                slug_as_label = row.company_slug.lower()
                if row.label.lower() == slug_as_label:
                    row.label = company_name
            session.commit()


def _get_company_from_jobs(job_ids: list[int]) -> str | None:
    """Read the company name from the first job in the list."""
    if not job_ids:
        return None
    from db.models import Job

    with get_session() as session:
        job = session.get(Job, job_ids[0])
        return job.company if job else None


def _read_interval_hours() -> int:
    with get_session() as session:
        row = session.execute(
            select(AppConfig.value).where(AppConfig.key == "source_interval_hours")
        ).scalar_one_or_none()
    try:
        return int(row) if row else _DEFAULT_INTERVAL_HOURS
    except (ValueError, TypeError):
        return _DEFAULT_INTERVAL_HOURS


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


__all__ = ["SourceScheduler", "get_source_phase", "is_running", "run_all_now", "run_source_now"]
