"""Feed API tests — crawl trigger, status, feed listing, action recording.

The crawl background task runs synchronously inside FastAPI's TestClient
(BackgroundTasks executes after the response returns), so by the time
TestClient.post() returns, the pipeline is already done. That's exactly
the deterministic behavior we want for tests.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api.main import app
from db.migrations import run_migrations
from db.models import Application, Job
from db.models import JobScore as JobScoreRow
from db.models import Profile as ProfileRow
from db.session import get_session
from llm.mock import MockProvider
from llm.types import ScoreResult
from services.crawl_progress import reset_registry
from services.scoring_service import score_jobs

client = TestClient(app)


JSON_LD_HTML = """
<html><head>
<script type="application/ld+json">
{"@type":"JobPosting","title":"Backend Engineer","description":"Python role.",
 "hiringOrganization":{"name":"AcmeCo"},
 "jobLocation":{"address":{"addressLocality":"Berlin"}}}
</script></head></html>
"""


@pytest.fixture(autouse=True)
def _migrated_and_clean() -> None:
    run_migrations()
    reset_registry()
    yield
    reset_registry()


@pytest.fixture
def _seeded_profile() -> int:
    with get_session() as session:
        row = ProfileRow(
            name="Alex K.",
            target_roles_json=["Backend Engineer"],
            target_locations_json=["Berlin"],
            cv_parsed_json={"skills": ["Python"]},
            profile_version=0,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


@pytest.fixture
def _mock_provider() -> MockProvider:
    """Override the LLM provider for the crawl pipeline with a deterministic mock."""
    provider = MockProvider()
    with patch("api.routes.jobs.get_llm_provider", return_value=provider):
        # Have to also override the dependency since FastAPI caches it per-request.
        app.dependency_overrides = {
            **app.dependency_overrides,
        }
        from api.dependencies import get_llm_provider

        app.dependency_overrides[get_llm_provider] = lambda: provider
        try:
            yield provider
        finally:
            app.dependency_overrides.pop(get_llm_provider, None)


# ---------------------------------------------------------------------------
# POST /api/jobs/crawl + GET /api/jobs/crawl/status/{id}
# ---------------------------------------------------------------------------


def test_crawl_rejects_manual_url_without_urls(_seeded_profile: int) -> None:
    response = client.post("/api/jobs/crawl", json={"source": "manual_url", "urls": []})
    assert response.status_code == 400


def test_crawl_runs_pipeline_and_persists_scored_jobs(
    _seeded_profile: int,
    _mock_provider: MockProvider,
) -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, html=JSON_LD_HTML))

    # Wire the manual_url source to use the mock transport — the pipeline
    # constructs ManualURLSource() with no client, so we patch the class default.
    with patch("api.routes.jobs.ManualURLSource") as mock_cls:
        mock_cls.return_value = _make_manual_source_with_transport(transport)
        response = client.post(
            "/api/jobs/crawl",
            json={
                "source": "manual_url",
                "urls": [
                    "https://acme.example/jobs/1",
                    "https://acme.example/jobs/2",
                ],
                "max_jobs": 5,
            },
        )

    assert response.status_code == 200
    crawl_id = response.json()["job_id"]

    status = client.get(f"/api/jobs/crawl/status/{crawl_id}").json()
    assert status["state"] == "done"
    assert status["new"] == 2
    assert status["duplicates"] == 0
    assert status["scored"] == 2

    with get_session() as session:
        jobs = session.execute(select(Job)).scalars().all()
        scores = session.execute(select(JobScoreRow)).scalars().all()
    assert len(jobs) == 2
    assert len(scores) == 2


def test_crawl_status_404_for_unknown_id() -> None:
    response = client.get("/api/jobs/crawl/status/does-not-exist")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/jobs/feed
# ---------------------------------------------------------------------------


def test_feed_returns_jobs_sorted_by_score_desc(_seeded_profile: int) -> None:
    job_ids = _seed_three_jobs()

    provider = MockProvider()
    provider.set_response("score_job", ScoreResult(score=80, rationale="strong"))
    score_jobs(provider, [job_ids[0]])
    provider.set_response("score_job", ScoreResult(score=40, rationale="weak"))
    score_jobs(provider, [job_ids[1]])
    provider.set_response("score_job", ScoreResult(score=60, rationale="ok"))
    score_jobs(provider, [job_ids[2]])

    feed = client.get("/api/jobs/feed").json()
    scores = [item["score"] for item in feed]
    assert scores == sorted(scores, reverse=True)
    assert scores == [80, 60, 40]


def test_feed_excludes_skipped_by_default(_seeded_profile: int) -> None:
    job_ids = _seed_three_jobs()
    score_jobs(MockProvider(), job_ids)

    client.post(f"/api/jobs/{job_ids[0]}/action", json={"action": "skip"})

    default_feed = client.get("/api/jobs/feed").json()
    assert all(item["job_id"] != job_ids[0] for item in default_feed)
    assert len(default_feed) == 2

    skipped_only = client.get("/api/jobs/feed?exclude_status=").json()
    assert any(item["job_id"] == job_ids[0] for item in skipped_only)


def test_feed_min_score_filter(_seeded_profile: int) -> None:
    job_ids = _seed_three_jobs()
    provider = MockProvider()
    provider.set_response("score_job", ScoreResult(score=20, rationale="low"))
    score_jobs(provider, [job_ids[0]])
    provider.set_response("score_job", ScoreResult(score=85, rationale="high"))
    score_jobs(provider, [job_ids[1]])
    provider.set_response("score_job", ScoreResult(score=55, rationale="mid"))
    score_jobs(provider, [job_ids[2]])

    response = client.get("/api/jobs/feed?min_score=50").json()
    assert len(response) == 2
    assert all(item["score"] >= 50 for item in response)


def test_feed_uses_only_current_profile_version(_seeded_profile: int) -> None:
    job_ids = _seed_three_jobs()
    score_jobs(MockProvider(), job_ids)

    # Bump profile version → old scores should drop out of the feed.
    with get_session() as session:
        row = session.execute(select(ProfileRow).limit(1)).scalar_one()
        row.profile_version = 5
        session.commit()

    response = client.get("/api/jobs/feed").json()
    assert response == []  # no scores at version=5 yet


# ---------------------------------------------------------------------------
# POST /api/jobs/{id}/action
# ---------------------------------------------------------------------------


def test_post_action_creates_application_row(_seeded_profile: int) -> None:
    [job_id] = _seed_three_jobs()[:1]
    response = client.post(f"/api/jobs/{job_id}/action", json={"action": "save"})
    assert response.status_code == 200
    assert response.json() == {"job_id": job_id, "status": "saved"}

    with get_session() as session:
        application = session.execute(select(Application)).scalar_one()
    assert application.status == "saved"
    assert application.job_id == job_id


def test_post_action_updates_existing_row(_seeded_profile: int) -> None:
    [job_id] = _seed_three_jobs()[:1]
    client.post(f"/api/jobs/{job_id}/action", json={"action": "save"})
    client.post(f"/api/jobs/{job_id}/action", json={"action": "apply"})

    with get_session() as session:
        rows = session.execute(select(Application)).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "applied"


def test_post_action_rejects_unknown_job_id(_seeded_profile: int) -> None:
    response = client.post("/api/jobs/99999/action", json={"action": "save"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_three_jobs() -> list[int]:
    ids = []
    with get_session() as session:
        for i in range(3):
            row = Job(
                source="manual_url",
                source_id=f"acme:{i}",
                title=f"Backend {i}",
                company="AcmeCo",
                location="Berlin",
                description="Python role.",
            )
            session.add(row)
            session.flush()
            ids.append(row.id)
        session.commit()
    return ids


def _make_manual_source_with_transport(transport: httpx.MockTransport):
    from crawler.manual_urls import ManualURLSource

    return ManualURLSource(client=httpx.Client(transport=transport))


# ---------------------------------------------------------------------------
# v0.3.5 — /scoring-status + /rescore
# ---------------------------------------------------------------------------


def test_scoring_status_with_no_jobs(_seeded_profile: int) -> None:
    """Fresh install: zero jobs, zero candidates. Empty-state stays at the
    default ``Click Crawl…`` copy (frontend reads ``rescore_candidate_count``
    to decide whether to show the rescore button)."""
    res = client.get("/api/jobs/scoring-status")
    assert res.status_code == 200
    body = res.json()
    assert body["jobs_total"] == 0
    assert body["jobs_with_current_score"] == 0
    assert body["rescore_candidate_count"] == 0


def test_scoring_status_with_stale_scores(_seeded_profile: int) -> None:
    """Re-onboarding bumps profile_version past the stored JobScore rows.
    Endpoint reports how many jobs need a fresh score."""
    job_ids = _seed_three_jobs()
    # Score 2 of the 3 jobs at the CURRENT profile_version.
    with get_session() as session:
        profile = session.execute(select(ProfileRow).limit(1)).scalar_one()
        for jid in job_ids[:2]:
            session.add(
                JobScoreRow(
                    job_id=jid,
                    profile_version=profile.profile_version,
                    score=70,
                    rationale_json={"score": 70, "rationale": ""},
                )
            )
        # The third job gets a STALE score at version -1.
        session.add(
            JobScoreRow(
                job_id=job_ids[2],
                profile_version=profile.profile_version - 1,
                score=70,
                rationale_json={"score": 70, "rationale": ""},
            )
        )
        session.commit()

    res = client.get("/api/jobs/scoring-status").json()
    assert res["jobs_total"] == 3
    assert res["jobs_with_current_score"] == 2
    assert res["rescore_candidate_count"] == 1


def test_rescore_scores_missing_jobs_against_current_profile(
    _seeded_profile: int, _mock_provider: MockProvider
) -> None:
    """Endpoint catches up everything not at the current profile_version."""
    _seed_three_jobs()
    _mock_provider.set_response(
        "score_job",
        ScoreResult(
            score=88,
            rationale="catch-up",
            matched_skills=["Python"],
            missing_skills=[],
            red_flags=[],
        ),
    )

    res = client.post("/api/jobs/rescore")
    assert res.status_code == 200
    body = res.json()
    assert body["rescored"] == 3
    assert body["total_candidates"] == 3
    assert body["capped"] is False

    # Subsequent call: every job now has a current-version score, nothing
    # to do — the response is honest about that.
    res2 = client.post("/api/jobs/rescore").json()
    assert res2["rescored"] == 0
    assert res2["total_candidates"] == 0


def test_rescore_caps_large_backlogs(_seeded_profile: int, _mock_provider: MockProvider) -> None:
    """A 60-job backlog with a 50-job cap: ``capped`` flag tells the frontend
    to either run rescore again or surface the partial state honestly."""
    from db.models import Job as JobRow

    with get_session() as session:
        for i in range(60):
            session.add(
                JobRow(
                    source="manual_url",
                    source_id=f"bulk:{i}",
                    title=f"Job {i}",
                    description="x",
                )
            )
        session.commit()

    res = client.post("/api/jobs/rescore").json()
    assert res["total_candidates"] == 60
    assert res["rescored"] == 50
    assert res["capped"] is True


# ---------------------------------------------------------------------------
# POST /api/jobs/{id}/interact
# ---------------------------------------------------------------------------


def test_post_interact_records_read_at(_seeded_profile: int) -> None:
    [job_id] = _seed_three_jobs()[:1]

    # 1. Job should initially be unread in the feed
    score_jobs(MockProvider(), [job_id])
    feed_before = client.get("/api/jobs/feed").json()
    assert len(feed_before) == 1
    assert feed_before[0]["unread"] is True

    # 2. Interact with the job (mark as read)
    response = client.post(f"/api/jobs/{job_id}/interact", json={"action": "read"})
    assert response.status_code == 200

    # 3. Check db interaction
    from db.models import JobInteraction

    with get_session() as session:
        interaction = session.execute(
            select(JobInteraction).where(JobInteraction.job_id == job_id)
        ).scalar_one()
        assert interaction.read_at is not None
        assert interaction.feedback_signal is None
        assert interaction.feedback_reason is None

    # 4. Job should now be read in the feed
    feed_after = client.get("/api/jobs/feed").json()
    assert feed_after[0]["unread"] is False


def test_post_interact_records_feedback(_seeded_profile: int) -> None:
    [job_id] = _seed_three_jobs()[:1]

    # 1. Provide feedback
    response = client.post(
        f"/api/jobs/{job_id}/interact", json={"action": "thumbs_down", "reason": "tech_stack"}
    )
    assert response.status_code == 200

    # 2. Check interaction in DB
    from db.models import JobInteraction

    with get_session() as session:
        interaction = session.execute(
            select(JobInteraction).where(JobInteraction.job_id == job_id)
        ).scalar_one()
        assert interaction.read_at is not None  # It should implicitly mark as read
        assert interaction.feedback_signal == -1
        assert interaction.feedback_reason == "tech_stack"

    # 3. Job feed should include feedback state
    score_jobs(MockProvider(), [job_id])
    feed = client.get("/api/jobs/feed").json()
    assert feed[0]["feedback_signal"] == -1
    assert feed[0]["feedback_reason"] == "tech_stack"
    assert feed[0]["unread"] is False


def test_post_interact_rejects_unknown_job_id(_seeded_profile: int) -> None:
    response = client.post("/api/jobs/99999/interact", json={"action": "read"})
    assert response.status_code == 404
