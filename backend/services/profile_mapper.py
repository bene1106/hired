"""Convert ``db.models.Profile``/``Job`` rows into the ``llm.types`` shapes.

The DB and the LLM layer have deliberately different shapes:

- The DB stores the canonical user state (plural target roles, parsed CV
  JSON, separate salary min/max columns on jobs).
- The LLM layer takes a flatter, prompt-friendly view (single target_role,
  skills/work_experience extracted from the parsed CV, salary as one
  preformatted string).

Keeping the conversion here means scoring/eval/feed can all share one
implementation, and we can tweak the LLM-facing shape without touching
the persistence layer.
"""

from __future__ import annotations

from typing import Any

from db.models import Job as JobRow
from db.models import Profile as ProfileRow
from llm.types import Job as LLMJob
from llm.types import Profile as LLMProfile
from llm.types import WorkExperience


def profile_row_to_llm(row: ProfileRow) -> LLMProfile:
    parsed: dict[str, Any] = row.cv_parsed_json or {}

    skills = _string_list(parsed.get("skills"))
    work = [
        WorkExperience(
            role=str(entry.get("title") or entry.get("role") or "Unknown role"),
            company=_optional_str(entry.get("company")),
            duration_months=_optional_int(entry.get("duration_months")),
            summary=_optional_str(entry.get("summary")),
        )
        for entry in (parsed.get("work_experience") or [])
        if isinstance(entry, dict)
    ]

    target_roles = list(row.target_roles_json or [])
    target_locations = list(row.target_locations_json or [])

    return LLMProfile(
        name=row.name,
        email=row.email,
        target_role=target_roles[0] if target_roles else None,
        target_locations=target_locations,
        target_salary_min=row.target_salary_min,
        skills=skills,
        work_experience=work,
        cv_text=row.cv_text,
    )


def job_row_to_llm(row: JobRow) -> LLMJob:
    return LLMJob(
        title=row.title,
        company=row.company,
        location=row.location,
        remote_policy=row.remote_policy,
        salary_range=_format_salary(row.salary_min, row.salary_max, row.currency),
        description=row.description,
        url=row.url,
        posted_at=row.posted_at,
    )


def _format_salary(min_: int | None, max_: int | None, currency: str | None) -> str | None:
    if min_ is None and max_ is None:
        return None
    cur = currency or ""
    if min_ is not None and max_ is not None:
        return f"{cur} {min_}-{max_}".strip()
    only = min_ if min_ is not None else max_
    return f"{cur} {only}".strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if isinstance(v, (str, int, float))]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


__all__ = ["job_row_to_llm", "profile_row_to_llm"]
