"""Unit tests for backend.services.cv_service."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import app
from db.migrations import run_migrations
from db.models import Profile as ProfileRow
from db.session import get_session
from llm import MockProvider, reset_provider_cache
from services import cv_service
from services.cv_service import (
    MAX_LLM_CHARS,
    MAX_UPLOAD_BYTES,
    CVUploadError,
    PdfExtractionError,
    extract_pdf_text,
    parse_cv_with_provider,
    upsert_profile_with_cv,
)


@pytest.fixture(autouse=True)
def _migrated_and_reset_provider() -> None:
    """Every test in this module hits the DB and the LLM factory."""
    run_migrations()
    reset_provider_cache()


# ---------------------------------------------------------------------------
# extract_pdf_text — pypdf monkeypatched so we don't need a fixture PDF
# ---------------------------------------------------------------------------


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakeReader:
    def __init__(self, *pages: str) -> None:
        self.pages = [_FakePage(t) for t in pages]


def test_extract_pdf_text_joins_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cv_service, "PdfReader", lambda _stream: _FakeReader("page one", "page two")
    )

    text = extract_pdf_text(b"%PDF-fake")

    assert text == "page one\n\npage two"


def test_extract_pdf_text_rejects_oversize_upload() -> None:
    big = b"\x00" * (MAX_UPLOAD_BYTES + 1)
    with pytest.raises(CVUploadError, match="max is"):
        extract_pdf_text(big)


def test_extract_pdf_text_raises_on_blank_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cv_service, "PdfReader", lambda _stream: _FakeReader("", "  \n"))

    with pytest.raises(PdfExtractionError, match="no extractable text"):
        extract_pdf_text(b"%PDF-fake")


def test_extract_pdf_text_wraps_pypdf_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    from pypdf.errors import PdfReadError

    def boom(_stream: Any) -> Any:
        raise PdfReadError("malformed")

    monkeypatch.setattr(cv_service, "PdfReader", boom)

    with pytest.raises(PdfExtractionError, match="Could not parse PDF"):
        extract_pdf_text(b"%PDF-fake")


# ---------------------------------------------------------------------------
# parse_cv_with_provider
# ---------------------------------------------------------------------------


def test_parse_cv_with_provider_truncates_to_30k() -> None:
    captured: dict[str, str] = {}

    class CapturingProvider(MockProvider):
        def parse_cv(self, cv_text: str) -> dict:
            captured["cv_text"] = cv_text
            return super().parse_cv(cv_text)

    long_text = "x" * (MAX_LLM_CHARS + 100)
    result = parse_cv_with_provider(CapturingProvider(), long_text)

    assert isinstance(result, dict)
    assert len(captured["cv_text"]) == MAX_LLM_CHARS


def test_parse_cv_with_provider_rejects_blank() -> None:
    with pytest.raises(CVUploadError, match="empty"):
        parse_cv_with_provider(MockProvider(), "   ")


# ---------------------------------------------------------------------------
# upsert_profile_with_cv
# ---------------------------------------------------------------------------


def test_upsert_creates_profile_when_missing() -> None:
    run_migrations()
    parsed = {"name": "Alex", "email": "alex@example.com", "skills": ["Python"]}
    row = upsert_profile_with_cv("raw cv text", parsed)

    assert row.id is not None
    assert row.cv_text == "raw cv text"
    assert row.cv_parsed_json == parsed
    assert row.name == "Alex"
    assert row.email == "alex@example.com"


def test_upsert_does_not_overwrite_existing_name(monkeypatch: pytest.MonkeyPatch) -> None:
    run_migrations()
    with get_session() as session:
        session.add(ProfileRow(name="User-Edited Name", email="user@host.tld"))
        session.commit()

    parsed = {"name": "Parsed Name", "email": "parsed@example.com"}
    row = upsert_profile_with_cv("raw", parsed)

    assert row.name == "User-Edited Name"
    assert row.email == "user@host.tld"


# ---------------------------------------------------------------------------
# /api/profile/cv (text) — happy + sad path
# ---------------------------------------------------------------------------


client = TestClient(app)


def test_post_cv_text_returns_parsed_payload_and_persists() -> None:
    response = client.post("/api/profile/cv", json={"cv_text": "Alex K. — backend engineer"})

    assert response.status_code == 200
    body = response.json()
    assert body["parsed"]["name"]
    assert body["profile"]["cv_text"] == "Alex K. — backend engineer"
    assert body["profile"]["cv_parsed_json"]["name"]


def test_post_cv_text_rejects_empty_body() -> None:
    response = client.post("/api/profile/cv", json={"cv_text": ""})
    assert response.status_code == 422  # Pydantic min_length


# ---------------------------------------------------------------------------
# /api/profile/cv/upload — multipart PDF
# ---------------------------------------------------------------------------


def test_post_cv_upload_round_trips_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cv_service, "PdfReader", lambda _stream: _FakeReader("Pretend CV content"))

    response = client.post(
        "/api/profile/cv/upload",
        files={"file": ("cv.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["cv_text"] == "Pretend CV content"


def test_post_cv_upload_rejects_oversize() -> None:
    blob = b"\x00" * (MAX_UPLOAD_BYTES + 1)
    response = client.post(
        "/api/profile/cv/upload",
        files={"file": ("cv.pdf", blob, "application/pdf")},
    )

    assert response.status_code == 413


def test_post_cv_upload_rejects_non_pdf() -> None:
    response = client.post(
        "/api/profile/cv/upload",
        files={"file": ("cv.docx", b"not a pdf", "application/msword")},
    )

    assert response.status_code == 415
