"""Goldset evaluation harness.

Runs the configured ``LLMProvider`` against every entry in
``eval/goldset.json`` and prints two aggregate metrics:

- **Precision@5** — of the five highest-scored entries, how many had an
  ``expected_score_range`` whose maximum is ≥ 75 (i.e. the labeler thought
  this was a strong match). 1.0 means the top-5 ranking matches the
  labeler perfectly.
- **MAE** — mean absolute error, where each entry's error is its distance
  from its expected range (0 if inside the range).

Usage::

    python eval/run_eval.py                        # uses app_config provider
    python eval/run_eval.py --provider mock        # explicit override
    python eval/run_eval.py --provider anthropic_api

The script does not need a backend running — it imports the provider
factory directly.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

# Add the backend to the import path so we can use the provider factory.
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "backend"))

from llm import LLMProvider, MockProvider  # noqa: E402
from llm.types import Job, Profile, ScoreResult, WorkExperience  # noqa: E402

GOLDSET_PATH = _REPO / "eval" / "goldset.json"
TOP_K = 5
STRONG_MATCH_THRESHOLD = 75


@dataclass
class EvalRow:
    id: str
    category: str
    actual_score: int
    expected_low: int
    expected_high: int
    distance: int
    in_range: bool
    rationale: str
    matched_skills: list[str]
    missing_terms: list[str]


def main() -> int:
    args = _parse_args()
    provider = _build_provider(args.provider)

    goldset = json.loads(GOLDSET_PATH.read_text(encoding="utf-8"))
    rows: list[EvalRow] = []

    for entry in goldset:
        profile = _profile_from_entry(entry["profile"])
        job = _job_from_entry(entry["job"])
        try:
            result = provider.score_job(profile, job)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {entry['id']}: score_job raised {exc}")
            continue
        rows.append(_row_from_result(entry, result))

    _print_table(rows)
    metrics = _summarize(rows)
    _print_metrics(metrics, args.provider or "configured")
    return 0


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scoring eval against the goldset.")
    parser.add_argument(
        "--provider",
        choices=["mock", "anthropic_api"],
        default=None,
        help="Override the configured provider. Default reads app_config.",
    )
    return parser.parse_args()


def _build_provider(override: str | None) -> LLMProvider:
    if override == "mock":
        return MockProvider()
    if override == "anthropic_api":
        from llm.anthropic_api import DEFAULT_MODEL, AnthropicAPIAdapter

        return AnthropicAPIAdapter(model=DEFAULT_MODEL)

    # No override → use the same factory the running app does.
    from llm import get_provider

    return get_provider()


# ---------------------------------------------------------------------------
# Conversions
# ---------------------------------------------------------------------------


def _profile_from_entry(payload: dict) -> Profile:
    return Profile(
        name=payload.get("name"),
        target_role=payload.get("target_role"),
        target_locations=list(payload.get("target_locations") or []),
        target_salary_min=payload.get("target_salary_min"),
        skills=list(payload.get("skills") or []),
        work_experience=[
            WorkExperience(**we) for we in (payload.get("work_experience") or [])
        ],
    )


def _job_from_entry(payload: dict) -> Job:
    return Job(
        title=payload["title"],
        company=payload.get("company"),
        location=payload.get("location"),
        remote_policy=payload.get("remote_policy"),
        salary_range=payload.get("salary_range"),
        description=payload.get("description"),
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _row_from_result(entry: dict, result: ScoreResult) -> EvalRow:
    lo, hi = entry["expected_score_range"]
    score = result.score
    if lo <= score <= hi:
        distance, in_range = 0, True
    else:
        distance = lo - score if score < lo else score - hi
        in_range = False

    must_mention = entry.get("must_mention_in_rationale", [])
    rationale_lower = result.rationale.lower()
    missing_terms = [term for term in must_mention if term.lower() not in rationale_lower]

    return EvalRow(
        id=entry["id"],
        category=entry.get("category", "?"),
        actual_score=score,
        expected_low=lo,
        expected_high=hi,
        distance=distance,
        in_range=in_range,
        rationale=result.rationale,
        matched_skills=list(result.matched_skills),
        missing_terms=missing_terms,
    )


@dataclass
class EvalMetrics:
    n: int
    in_range_rate: float
    mae: float
    precision_at_k: float
    must_mention_coverage: float


def _summarize(rows: list[EvalRow]) -> EvalMetrics:
    if not rows:
        return EvalMetrics(0, 0.0, 0.0, 0.0, 0.0)

    in_range_rate = sum(1 for r in rows if r.in_range) / len(rows)
    mae = statistics.fmean(r.distance for r in rows)

    top_k = sorted(rows, key=lambda r: r.actual_score, reverse=True)[:TOP_K]
    precision_at_k = (
        sum(1 for r in top_k if r.expected_high >= STRONG_MATCH_THRESHOLD) / len(top_k)
    )

    total_required = sum(len(r.missing_terms) + 1 for r in rows)  # +1 protects /0
    total_missing = sum(len(r.missing_terms) for r in rows)
    coverage = 1.0 - (total_missing / total_required) if total_required else 1.0

    return EvalMetrics(
        n=len(rows),
        in_range_rate=in_range_rate,
        mae=mae,
        precision_at_k=precision_at_k,
        must_mention_coverage=coverage,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _print_table(rows: list[EvalRow]) -> None:
    print()
    print(f"{'ID':28} {'CAT':10} {'ACTUAL':>7} {'RANGE':>9} {'DIST':>5} {'OK':>3} {'MISS':>5}")
    print("-" * 80)
    for row in rows:
        ok = "Y" if row.in_range else " "
        rng = f"{row.expected_low}-{row.expected_high}"
        miss = ",".join(row.missing_terms) if row.missing_terms else "-"
        print(
            f"{row.id:28} {row.category:10} {row.actual_score:>7} {rng:>9} "
            f"{row.distance:>5} {ok:>3} {miss:>5}"
        )


def _print_metrics(metrics: EvalMetrics, provider_name: str) -> None:
    print()
    print(f"Provider: {provider_name}")
    print(f"Entries scored:        {metrics.n}")
    print(f"In-range rate:         {metrics.in_range_rate:.0%}")
    print(f"MAE (distance):        {metrics.mae:.1f} pts")
    print(f"Precision@{TOP_K}:           {metrics.precision_at_k:.0%}")
    print(f"Must-mention coverage: {metrics.must_mention_coverage:.0%}")


if __name__ == "__main__":
    sys.exit(main())
