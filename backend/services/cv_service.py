"""CV upload + parse pipeline.

Three concerns live here:

1. Convert raw uploads (PDF bytes or pasted text) into a single CV string.
   PDFs go through ``pypdf``; the page texts are joined with double newlines
   so role boundaries survive the round-trip.
2. Send that string through the configured ``LLMProvider.parse_cv`` and
   return the structured dict.
3. Persist both the raw text and the parsed JSON to the single ``profile``
   row. Phase 3 only ever has one profile per local install.

Two safety constraints from the phase spec:
- Reject uploads larger than ``MAX_UPLOAD_BYTES`` (5MB) before any decode.
- Truncate the LLM input to ``MAX_LLM_CHARS`` (30 KB).

Prompt-injection mitigation lives in the parse_cv prompt itself: it wraps
``{{cv_text}}`` in ``<CV>...</CV>`` and instructs the model to treat the
contents as data. We don't add a second layer here.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import select

from db.models import Profile as ProfileRow
from db.session import get_session
from llm import LLMProvider

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_LLM_CHARS = 30_000


class CVUploadError(ValueError):
    """Raised for invalid uploads (too big, undecodable, etc.)."""


class PdfExtractionError(CVUploadError):
    """Raised when pypdf can't read the file."""


def extract_pdf_text(data: bytes) -> str:
    """Extract text from a PDF byte string. Joins pages with blank lines."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise CVUploadError(f"PDF is {len(data)} bytes; max is {MAX_UPLOAD_BYTES} (5 MB).")
    try:
        reader = PdfReader(io.BytesIO(data))
        chunks = [page.extract_text() or "" for page in reader.pages]
    except (PdfReadError, ValueError, KeyError) as exc:
        raise PdfExtractionError(f"Could not parse PDF: {exc}") from exc

    text = "\n\n".join(chunk for chunk in chunks if chunk.strip())
    if not text.strip():
        raise PdfExtractionError("PDF contained no extractable text.")
    return text


def parse_cv_with_provider(provider: LLMProvider, cv_text: str) -> dict[str, Any]:
    """Truncate and forward the CV text to the configured provider."""
    if not cv_text or not cv_text.strip():
        raise CVUploadError("CV text is empty.")
    truncated = cv_text[:MAX_LLM_CHARS]
    return provider.parse_cv(truncated)


def upsert_profile_with_cv(cv_text: str, parsed: dict[str, Any]) -> ProfileRow:
    """Write the raw + parsed CV onto the single profile row.

    Pre-fills ``name`` and ``email`` from the parsed payload only if the
    profile row doesn't already have them; the user gets to edit these in
    Step 4 of the wizard, but we want sensible defaults populated.
    """
    with get_session() as session:
        row = session.execute(select(ProfileRow).limit(1)).scalar_one_or_none()
        if row is None:
            row = ProfileRow()
            session.add(row)

        row.cv_text = cv_text
        row.cv_parsed_json = parsed
        if not row.name and parsed.get("name"):
            row.name = parsed["name"]
        if not row.email and parsed.get("email"):
            row.email = parsed["email"]

        # CV re-upload changes the skill/experience signal the scorer sees,
        # so bump profile_version to invalidate cached scores.
        row.profile_version = (row.profile_version or 0) + 1

        session.commit()
        session.refresh(row)
        return row


__all__ = [
    "MAX_LLM_CHARS",
    "MAX_UPLOAD_BYTES",
    "CVUploadError",
    "PdfExtractionError",
    "extract_pdf_text",
    "parse_cv_with_provider",
    "upsert_profile_with_cv",
]
