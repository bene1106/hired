"""Application generation pipeline tests, all against MockProvider."""

from __future__ import annotations

import pytest

from db.migrations import run_migrations
from db.models import Application, Job
from db.models import Profile as ProfileRow
from db.session import get_session
from llm.mock import MockProvider
from llm.types import CompanyBrief, CoverLetter
from services.application_service import (
    MATERIAL_TYPES,
    ApplicationServiceError,
    generate_application_materials,
    get_all_materials,
    get_latest_material,
    get_or_create_application,
    save_material_edit,
)
from services.generation_progress import create_entry, get_entry, reset_registry


@pytest.fixture(autouse=True)
def _migrated() -> None:
    run_migrations()
    reset_registry()


# ---------------------------------------------------------------------------
# Provider that counts calls so we can assert the cache works
# ---------------------------------------------------------------------------


class CountingProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls: dict[str, int] = {}

    def _bump(self, name: str) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1

    def research_company(self, company):  # type: ignore[override]
        self._bump("research_company")
        return super().research_company(company)

    def tailor_cv(self, profile, job):  # type: ignore[override]
        self._bump("tailor_cv")
        return super().tailor_cv(profile, job)

    def generate_cover_letter(self, profile, job, brief):  # type: ignore[override]
        self._bump("generate_cover_letter")
        return super().generate_cover_letter(profile, job, brief)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_profile(version: int = 0) -> int:
    with get_session() as session:
        row = ProfileRow(
            name="Alex K.",
            email="alex@example.com",
            target_roles_json=["Backend Engineer"],
            target_locations_json=["Berlin"],
            cv_parsed_json={"skills": ["Python", "FastAPI"], "work_experience": []},
            profile_version=version,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def _seed_job(*, company: str = "AcmeCo", source_id: str = "j1") -> int:
    with get_session() as session:
        job = Job(
            source="manual_url",
            source_id=source_id,
            title="Backend Engineer",
            company=company,
            location="Berlin",
            description="Build APIs.",
            url=f"https://example.test/{source_id}",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job.id


def _bump_profile_version() -> int:
    with get_session() as session:
        profile = session.query(ProfileRow).first()
        assert profile is not None
        profile.profile_version += 1
        session.commit()
        return profile.profile_version


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_generate_writes_three_material_rows() -> None:
    _seed_profile()
    job_id = _seed_job()
    application = get_or_create_application(job_id)

    provider = CountingProvider()
    generate_application_materials(provider, application.id)

    materials = get_all_materials(application.id)
    assert set(materials.keys()) == set(MATERIAL_TYPES)
    assert provider.calls == {
        "research_company": 1,
        "tailor_cv": 1,
        "generate_cover_letter": 1,
    }


def test_company_brief_cache_is_case_insensitive_per_company() -> None:
    _seed_profile()
    job_a = _seed_job(company="AcmeCo", source_id="a")
    job_b = _seed_job(company="acmeco", source_id="b")  # casing differs
    job_c = _seed_job(company="AcmeCo", source_id="c")

    app_a = get_or_create_application(job_a)
    app_b = get_or_create_application(job_b)
    app_c = get_or_create_application(job_c)

    provider = CountingProvider()
    generate_application_materials(provider, app_a.id)
    generate_application_materials(provider, app_b.id)
    generate_application_materials(provider, app_c.id)

    # Three jobs, one company → exactly one research call.
    assert provider.calls["research_company"] == 1
    # CV tailoring + cover letter run per application, so 3 each.
    assert provider.calls["tailor_cv"] == 3
    assert provider.calls["generate_cover_letter"] == 3


def test_profile_version_invalidates_cv_and_cover_letter_but_not_brief() -> None:
    _seed_profile()
    job_id = _seed_job()
    application = get_or_create_application(job_id)

    provider = CountingProvider()
    generate_application_materials(provider, application.id)
    _bump_profile_version()
    generate_application_materials(provider, application.id)

    assert provider.calls["research_company"] == 1  # company brief still cached
    assert provider.calls["tailor_cv"] == 2
    assert provider.calls["generate_cover_letter"] == 2


def test_second_run_with_no_changes_reuses_cache() -> None:
    _seed_profile()
    job_id = _seed_job()
    application = get_or_create_application(job_id)

    provider = CountingProvider()
    generate_application_materials(provider, application.id)
    generate_application_materials(provider, application.id)

    assert provider.calls == {
        "research_company": 1,
        "tailor_cv": 1,
        "generate_cover_letter": 1,
    }


def test_force_regenerates_only_named_step() -> None:
    _seed_profile()
    job_id = _seed_job()
    application = get_or_create_application(job_id)

    provider = CountingProvider()
    generate_application_materials(provider, application.id)
    generate_application_materials(provider, application.id, force=("cover_letter",))

    assert provider.calls["research_company"] == 1
    assert provider.calls["tailor_cv"] == 1
    assert provider.calls["generate_cover_letter"] == 2


def test_progress_registry_records_step_states() -> None:
    _seed_profile()
    job_id = _seed_job()
    application = get_or_create_application(job_id)

    entry = create_entry(application.id)
    generate_application_materials(MockProvider(), application.id, task_id=entry.task_id)

    snap = get_entry(entry.task_id)
    assert snap is not None
    assert snap.state == "done"
    assert snap.company_brief == "done"
    assert snap.cv_suggestions == "done"
    assert snap.cover_letter == "done"
    assert snap.error is None


def test_progress_records_cached_steps_on_second_run() -> None:
    _seed_profile()
    job_id = _seed_job()
    application = get_or_create_application(job_id)

    entry1 = create_entry(application.id)
    generate_application_materials(MockProvider(), application.id, task_id=entry1.task_id)
    entry2 = create_entry(application.id)
    generate_application_materials(MockProvider(), application.id, task_id=entry2.task_id)

    snap = get_entry(entry2.task_id)
    assert snap is not None
    assert snap.state == "done"
    assert snap.company_brief == "cached"
    assert snap.cv_suggestions == "cached"
    assert snap.cover_letter == "cached"


def test_save_material_edit_appends_new_row_and_increments_edit_count() -> None:
    _seed_profile()
    job_id = _seed_job()
    application = get_or_create_application(job_id)

    generate_application_materials(MockProvider(), application.id)
    initial = get_latest_material(application.id, "cover_letter")
    assert initial is not None
    assert initial.edit_count == 0

    edited = save_material_edit(application.id, "cover_letter", "My edited cover letter.")
    assert edited.content == "My edited cover letter."
    assert edited.edit_count == 1

    edited_again = save_material_edit(application.id, "cover_letter", "Another revision.")
    assert edited_again.edit_count == 2


def test_generate_raises_when_profile_missing() -> None:
    job_id = _seed_job()
    with get_session() as session:
        application = Application(job_id=job_id, status="saved")
        session.add(application)
        session.commit()
        session.refresh(application)
        app_id = application.id

    with pytest.raises(ApplicationServiceError):
        generate_application_materials(MockProvider(), app_id)


def test_generate_propagates_provider_failure_and_marks_step_error() -> None:
    _seed_profile()
    job_id = _seed_job()
    application = get_or_create_application(job_id)

    provider = MockProvider()

    def boom(_company: str):  # noqa: ANN001 — patch signature
        raise RuntimeError("anthropic exploded")

    provider.research_company = boom  # type: ignore[assignment]
    entry = create_entry(application.id)

    with pytest.raises(RuntimeError, match="anthropic exploded"):
        generate_application_materials(provider, application.id, task_id=entry.task_id)

    snap = get_entry(entry.task_id)
    assert snap is not None
    assert snap.state == "error"
    assert snap.company_brief == "error"
    assert snap.error and "anthropic exploded" in snap.error


def test_get_or_create_application_is_idempotent() -> None:
    _seed_profile()
    job_id = _seed_job()
    a = get_or_create_application(job_id)
    b = get_or_create_application(job_id)
    assert a.id == b.id
    assert a.status == "saved"


def test_brief_with_user_edits_uses_brief_markdown_for_cover_letter() -> None:
    """Sanity: cover letter receives the (possibly cached) CompanyBrief, not raw text."""
    _seed_profile()
    job_id = _seed_job(company="MockCo")
    app = get_or_create_application(job_id)

    captured: dict = {}

    provider = MockProvider()
    real = provider.generate_cover_letter

    def capture(profile, job, brief):  # type: ignore[no-redef]
        captured["brief"] = brief
        return real(profile, job, brief)

    provider.generate_cover_letter = capture  # type: ignore[assignment]
    # Pre-populate the company-brief cache with a recognisable marker so
    # we can assert the orchestrator passed the cached version through.
    provider.set_response(
        "research_company",
        CompanyBrief(company="MockCo", markdown="# MockCo unique-marker", sources=["s1"]),
    )
    generate_application_materials(provider, app.id)

    assert isinstance(captured["brief"], CompanyBrief)
    assert "unique-marker" in captured["brief"].markdown


def test_cover_letter_word_count_persists_in_source_meta() -> None:
    _seed_profile()
    job_id = _seed_job()
    app = get_or_create_application(job_id)
    provider = MockProvider()
    provider.set_response(
        "generate_cover_letter",
        CoverLetter(body="A short cover letter body.", word_count=5),
    )
    generate_application_materials(provider, app.id)
    view = get_latest_material(app.id, "cover_letter")
    assert view is not None
    assert view.source_meta == {"word_count": 5}
