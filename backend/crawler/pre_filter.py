"""Pre-filtering logic applied before inserting scraped jobs into the DB.

Filters out jobs that clearly don't match the user's profile preferences so
we don't waste LLM scoring budget on irrelevant postings.

Designed to have a low false-negative rate (err on the side of inclusion) —
edge cases should pass through to LLM scoring rather than being silently
dropped.
"""

from __future__ import annotations

from db.models import Profile

from .base import RawJob

_STOP_WORDS = {"and", "or", "the", "for", "with", "in", "at", "of", "a", "an"}


def pre_filter(raw: RawJob, profile: Profile | None) -> bool:
    """Return True if the job should be kept (inserted / forwarded to scoring)."""
    if profile is None:
        return True

    target_roles = list(profile.target_roles_json or [])
    target_locations = list(profile.target_locations_json or [])
    work_formats = list(profile.work_formats_json or [])

    # Skip internships unless user explicitly targets them.
    intern_wanted = any("intern" in r.lower() for r in target_roles)
    if not intern_wanted and _is_internship(raw.title):
        return False

    # Role filter: title must share at least one meaningful keyword with a target role.
    if target_roles and not _role_matches(raw.title, target_roles):
        return False

    # Location filter: job must be in a preferred location (or remote, if wanted).
    if target_locations and not _location_matches(
        raw.location, raw.remote_policy, target_locations
    ):
        return False

    # Work format filter: only apply when format is known on both sides.
    return not (
        work_formats
        and raw.remote_policy
        and raw.remote_policy.lower() not in [f.lower() for f in work_formats]
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_internship(title: str) -> bool:
    return "intern" in title.lower()


def _role_matches(title: str, target_roles: list[str]) -> bool:
    title_lower = title.lower()
    for role in target_roles:
        keywords = [w for w in role.lower().split() if len(w) > 2 and w not in _STOP_WORDS]
        if any(kw in title_lower for kw in keywords):
            return True
    return False


def _location_matches(
    location: str | None,
    remote_policy: str | None,
    target_locations: list[str],
) -> bool:
    # Unknown location: can't rule it out — let LLM scoring decide.
    if location is None:
        return True
    if remote_policy == "remote":
        return True
    loc_lower = location.lower()
    if "remote" in loc_lower:
        return True
    for tl in target_locations:
        tl_lower = tl.lower()
        if "remote" in tl_lower:
            continue
        if any(len(w) > 3 and w in loc_lower for w in tl_lower.split()):
            return True
    return False


__all__ = ["pre_filter"]
