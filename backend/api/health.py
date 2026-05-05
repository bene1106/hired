"""Health-check endpoint: confirms the sidecar is up and the DB is reachable."""

from __future__ import annotations

from fastapi import APIRouter

from api import VERSION
from db.session import db_ping

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    db_status = "connected" if db_ping() else "error"
    return {"status": "ok", "db": db_status, "version": VERSION}
