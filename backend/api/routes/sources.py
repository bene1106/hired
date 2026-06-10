"""Job source management API.

Endpoints:
  GET  /api/sources                   — list all configured sources
  POST /api/sources                   — add a new source
  PUT  /api/sources/{id}              — update label / enabled / company_slug
  DELETE /api/sources/{id}            — remove a source
  POST /api/sources/{id}/run-now      — trigger a single source immediately
  POST /api/sources/run-now           — trigger all enabled sources immediately
  GET  /api/sources/config            — read global scheduler config (interval_hours)
  PUT  /api/sources/config            — write global scheduler config
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from db.models import AppConfig
from db.models import CrawlSource as CrawlSourceRow
from db.session import get_session
from services.source_scheduler import get_source_phase, is_running, run_all_now, run_source_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sources", tags=["sources"])

SourceType = Literal["wellfound", "indeed", "remotive", "stepstone"]

_DEFAULT_INTERVAL = 6


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CrawlSourceResponse(BaseModel):
    id: int
    source_type: str
    company_slug: str | None
    label: str
    enabled: bool
    last_checked_at: datetime | None
    last_error: str | None
    is_running: bool
    crawl_phase: str | None
    created_at: datetime

    @classmethod
    def from_row(cls, row: CrawlSourceRow) -> CrawlSourceResponse:
        return cls(
            id=row.id,
            source_type=row.source_type,
            company_slug=row.company_slug,
            label=row.label,
            enabled=row.enabled,
            last_checked_at=row.last_checked_at,
            last_error=row.last_error,
            is_running=is_running(row.id),
            crawl_phase=get_source_phase(row.id),
            created_at=row.created_at,
        )


class CreateSourceRequest(BaseModel):
    source_type: SourceType
    company_slug: str | None = Field(default=None, max_length=255)
    label: str | None = Field(default=None, max_length=255)
    enabled: bool = True


class UpdateSourceRequest(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    enabled: bool | None = None
    company_slug: str | None = Field(default=None, max_length=255)


class SourceConfigResponse(BaseModel):
    interval_hours: int


class UpdateSourceConfigRequest(BaseModel):
    interval_hours: int = Field(ge=0, le=168)  # 0 = disabled, max 1 week


class RunNowResponse(BaseModel):
    started: list[int]


# ---------------------------------------------------------------------------
# Routes — order matters: /run-now and /config must come before /{id}
# ---------------------------------------------------------------------------


@router.get("/config", response_model=SourceConfigResponse)
def get_config() -> SourceConfigResponse:
    with get_session() as session:
        row = session.execute(
            select(AppConfig.value).where(AppConfig.key == "source_interval_hours")
        ).scalar_one_or_none()
    try:
        hours = int(row) if row else _DEFAULT_INTERVAL
    except (ValueError, TypeError):
        hours = _DEFAULT_INTERVAL
    return SourceConfigResponse(interval_hours=hours)


@router.put("/config", response_model=SourceConfigResponse)
def update_config(payload: UpdateSourceConfigRequest) -> SourceConfigResponse:
    with get_session() as session:
        row = session.execute(
            select(AppConfig).where(AppConfig.key == "source_interval_hours")
        ).scalar_one_or_none()
        if row is None:
            row = AppConfig(key="source_interval_hours", value=str(payload.interval_hours))
            session.add(row)
        else:
            row.value = str(payload.interval_hours)
        session.commit()
    return SourceConfigResponse(interval_hours=payload.interval_hours)


@router.post("/run-now", response_model=RunNowResponse)
def trigger_all() -> RunNowResponse:
    started = run_all_now()
    return RunNowResponse(started=started)


@router.get("", response_model=list[CrawlSourceResponse])
def list_sources() -> list[CrawlSourceResponse]:
    with get_session() as session:
        rows = (
            session.execute(
                select(CrawlSourceRow).order_by(CrawlSourceRow.source_type, CrawlSourceRow.id)
            )
            .scalars()
            .all()
        )
        return [CrawlSourceResponse.from_row(r) for r in rows]


@router.post("", response_model=CrawlSourceResponse, status_code=201)
def create_source(payload: CreateSourceRequest) -> CrawlSourceResponse:
    label = payload.label or payload.source_type

    with get_session() as session:
        row = CrawlSourceRow(
            source_type=payload.source_type,
            company_slug=None,
            label=label,
            enabled=payload.enabled,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return CrawlSourceResponse.from_row(row)


@router.put("/{source_id}", response_model=CrawlSourceResponse)
def update_source(source_id: int, payload: UpdateSourceRequest) -> CrawlSourceResponse:
    with get_session() as session:
        row = session.get(CrawlSourceRow, source_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Source not found.")
        if payload.label is not None:
            row.label = payload.label
        if payload.enabled is not None:
            row.enabled = payload.enabled
        if payload.company_slug is not None:
            row.company_slug = payload.company_slug
        session.commit()
        session.refresh(row)
        return CrawlSourceResponse.from_row(row)


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int) -> None:
    with get_session() as session:
        row = session.get(CrawlSourceRow, source_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Source not found.")
        session.delete(row)
        session.commit()


@router.post("/{source_id}/run-now", response_model=RunNowResponse)
def trigger_one(source_id: int) -> RunNowResponse:
    with get_session() as session:
        row = session.get(CrawlSourceRow, source_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Source not found.")

    run_source_now(source_id)
    return RunNowResponse(started=[source_id])
