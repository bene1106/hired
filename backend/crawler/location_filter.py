"""Location-based job filtering.

Keeps a job if any of these hold:
  - user has no target_locations configured
  - job location is unknown (None)
  - job is remote (remote_policy=="remote" or "remote" in location string)
  - any user target location word (>3 chars) appears in the job location string
"""

from __future__ import annotations


def location_matches(
    job_location: str | None,
    job_remote_policy: str | None,
    target_locations: list[str],
) -> bool:
    if not target_locations:
        return True
    if job_location is None:
        return True  # unknown location — don't filter out
    if job_remote_policy == "remote":
        return True
    loc_lower = job_location.lower()
    if "remote" in loc_lower:
        return True
    for target in target_locations:
        t = target.lower()
        if "remote" in t:
            continue
        # Match if any significant word from the target appears in job location
        for word in t.split():
            if len(word) > 3 and word in loc_lower:
                return True
    return False


__all__ = ["location_matches"]
