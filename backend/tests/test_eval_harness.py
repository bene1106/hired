"""Smoke tests for the eval scripts.

Both scripts run as standalone CLIs but we want CI to fail fast if
someone breaks the goldset shape or one of the conversion helpers. We
exec the scripts as subprocesses against MockProvider so the test stays
deterministic and offline.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GOLDSET = REPO / "eval" / "goldset.json"


def test_goldset_has_twenty_entries_with_required_fields() -> None:
    entries = json.loads(GOLDSET.read_text(encoding="utf-8"))
    assert len(entries) == 20

    for entry in entries:
        assert {"id", "category", "profile", "job", "expected_score_range"}.issubset(entry)
        lo, hi = entry["expected_score_range"]
        assert 0 <= lo <= hi <= 100
        assert entry["job"]["title"]


def test_run_eval_against_mock_provider_completes_cleanly() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "eval" / "run_eval.py"), "--provider", "mock"],
        capture_output=True,
        text=True,
        cwd=REPO / "backend",
    )
    assert result.returncode == 0, result.stderr
    assert "Entries scored:" in result.stdout
    assert "Precision@5" in result.stdout


def test_bias_audit_against_mock_provider_completes_cleanly() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "eval" / "bias_audit.py"), "--provider", "mock"],
        capture_output=True,
        text=True,
        cwd=REPO / "backend",
    )
    assert result.returncode == 0, result.stderr
    assert "Pairs evaluated:" in result.stdout
    # MockProvider always returns the same score, so variance must be zero.
    assert "Max variance:      0 pts" in result.stdout
