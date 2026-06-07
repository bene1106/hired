"""Profile + CV endpoints — used by the onboarding wizard and Settings."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from api.dependencies import get_llm_provider
from db.models import Profile as ProfileRow
from db.session import get_session
from llm import LLMProvider
from services.cv_service import (
    MAX_UPLOAD_BYTES,
    CVUploadError,
    extract_pdf_text,
    parse_cv_with_provider,
    upsert_profile_with_cv,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["profile"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ProfileResponse(BaseModel):
    """Full profile shape returned by ``GET /api/profile``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    email: str | None
    phone: str | None
    target_roles: list[str]
    target_locations: list[str]
    target_salary_min: int | None
    priorities: list[str]
    skills: list[str]
    work_formats: list[str]
    cv_text: str | None
    cv_parsed_json: dict[str, Any] | None
    profile_version: int

    @classmethod
    def from_row(cls, row: ProfileRow) -> ProfileResponse:
        # skills_json is the authoritative editable list; fall back to
        # cv_parsed_json["skills"] only when the user hasn't explicitly saved one.
        skills: list[str] = row.skills_json or (
            (row.cv_parsed_json or {}).get("skills") or []
        )
        return cls(
            id=row.id,
            name=row.name,
            email=row.email,
            phone=row.phone,
            target_roles=row.target_roles_json or [],
            target_locations=row.target_locations_json or [],
            target_salary_min=row.target_salary_min,
            priorities=row.priorities_json or [],
            skills=skills,
            work_formats=row.work_formats_json or [],
            cv_text=row.cv_text,
            cv_parsed_json=row.cv_parsed_json,
            profile_version=row.profile_version or 0,
        )


class ProfileUpdate(BaseModel):
    """Body for ``POST /api/profile``. All fields optional; missing → unchanged."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    target_roles: list[str] | None = None
    target_locations: list[str] | None = None
    target_salary_min: int | None = Field(default=None, ge=0)
    priorities: list[str] | None = None
    skills: list[str] | None = None
    work_formats: list[str] | None = None


class CVTextRequest(BaseModel):
    cv_text: str = Field(..., min_length=1)


class CVParseResponse(BaseModel):
    parsed: dict[str, Any]
    profile: ProfileResponse


# ---------------------------------------------------------------------------
# Profile CRUD (full set lands in the next commit)
# ---------------------------------------------------------------------------


@router.post("/profile/cv", response_model=CVParseResponse)
def post_cv_text(
    payload: CVTextRequest,
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> CVParseResponse:
    """Parse a pasted-in CV text. Persists raw + structured forms."""
    try:
        parsed = parse_cv_with_provider(provider, payload.cv_text)
    except CVUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = upsert_profile_with_cv(payload.cv_text, parsed)
    return CVParseResponse(parsed=parsed, profile=ProfileResponse.from_row(row))


@router.post("/profile/cv/upload", response_model=CVParseResponse)
async def post_cv_upload(
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    file: Annotated[UploadFile, File(description="PDF CV (≤5 MB)")],
) -> CVParseResponse:
    """Parse an uploaded PDF CV. Persists raw text + structured form."""
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"PDF is {len(data)} bytes; max is {MAX_UPLOAD_BYTES} (5 MB).",
        )

    content_type = (file.content_type or "").lower()
    if not (content_type == "application/pdf" or (file.filename or "").lower().endswith(".pdf")):
        raise HTTPException(
            status_code=415,
            detail="Only PDF uploads are supported.",
        )

    try:
        cv_text = extract_pdf_text(data)
    except CVUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        parsed = parse_cv_with_provider(provider, cv_text)
    except CVUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    row = upsert_profile_with_cv(cv_text, parsed)
    return CVParseResponse(parsed=parsed, profile=ProfileResponse.from_row(row))


@router.get("/profile", response_model=ProfileResponse)
def get_profile() -> ProfileResponse:
    """Return the single profile row. 404 if onboarding hasn't run yet."""
    row = _read_profile_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No profile saved yet.")
    return ProfileResponse.from_row(row)


@router.post("/profile", response_model=ProfileResponse)
def post_profile(payload: ProfileUpdate) -> ProfileResponse:
    """Upsert the single profile row with whichever fields the user provided."""
    with get_session() as session:
        row = session.execute(select(ProfileRow).limit(1)).scalar_one_or_none()
        if row is None:
            row = ProfileRow()
            session.add(row)

        mutated = False
        if payload.name is not None:
            row.name = payload.name
            mutated = True
        if payload.email is not None:
            row.email = payload.email
            mutated = True
        if payload.phone is not None:
            row.phone = payload.phone
            mutated = True
        if payload.target_roles is not None:
            row.target_roles_json = payload.target_roles
            mutated = True
        if payload.target_locations is not None:
            row.target_locations_json = payload.target_locations
            mutated = True
        if payload.target_salary_min is not None:
            row.target_salary_min = payload.target_salary_min
            mutated = True
        if payload.priorities is not None:
            row.priorities_json = payload.priorities
            mutated = True
        if payload.skills is not None:
            row.skills_json = payload.skills
            mutated = True
        if payload.work_formats is not None:
            row.work_formats_json = payload.work_formats
            mutated = True

        # Bump on any real change so the score cache invalidates.
        if mutated:
            row.profile_version = (row.profile_version or 0) + 1

        session.commit()
        session.refresh(row)
        return ProfileResponse.from_row(row)


def _read_profile_or_none() -> ProfileRow | None:
    with get_session() as session:
        return session.execute(select(ProfileRow).limit(1)).scalar_one_or_none()
