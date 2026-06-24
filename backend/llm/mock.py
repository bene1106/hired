"""MockProvider — deterministic stubs for tests and offline development.

Default behaviour: return realistic, structurally valid stubs for every
`LLMProvider` method without making a single network call.

Tests that need a specific response can override per method:

    provider = MockProvider()
    provider.set_response("score_job", ScoreResult(score=42, rationale="…"))
    provider.score_job(profile, job)  # → the value above

The override is one-shot per call; setting it twice replaces it. Pass `None`
to clear and fall back to the default stub.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .types import (
    AnswerFeedback,
    ChatMessage,
    CompanyBrief,
    CoverLetter,
    ImprovementNote,
    InterviewQuestion,
    Job,
    MockAnswerRating,
    MockInterviewContext,
    MockInterviewEvaluation,
    MockInterviewPlan,
    MockQAPair,
    MockQuestion,
    Profile,
    ScoreResult,
)

_VALID_METHODS = {
    "parse_cv",
    "score_job",
    "research_company",
    "tailor_cv",
    "generate_cover_letter",
    "generate_interview_questions",
    "evaluate_answer",
    "summarize_role",
    "interview_chat_stream",
    "generate_mock_interview_questions",
    "evaluate_mock_interview",
}


class MockProvider:
    """Returns deterministic stub data for every LLMProvider method."""

    def __init__(self) -> None:
        self._overrides: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def set_response(self, method: str, value: Any) -> None:
        """Override the response for `method`. Pass `None` to clear."""
        if method not in _VALID_METHODS:
            raise ValueError(f"Unknown method '{method}'. Valid: {sorted(_VALID_METHODS)}")
        if value is None:
            self._overrides.pop(method, None)
        else:
            self._overrides[method] = value

    def _override(self, method: str) -> Any | None:
        return self._overrides.get(method)

    # ------------------------------------------------------------------
    # LLMProvider methods
    # ------------------------------------------------------------------

    def parse_cv(self, cv_text: str) -> dict:
        if (override := self._override("parse_cv")) is not None:
            return override
        return {
            "name": "Alex K.",
            "email": "alex.k@example.com",
            "phone": None,
            "location": "Berlin, DE",
            "summary": "Backend engineer with a focus on Python web services.",
            "work_experience": [
                {
                    "title": "Backend Engineer",
                    "company": "TechStartup",
                    "location": "Berlin",
                    "start_date": "2024-01",
                    "end_date": "present",
                    "duration_months": 24,
                    "summary": "Built FastAPI services, owned the integration test suite.",
                }
            ],
            "education": [
                {
                    "institution": "TU Berlin",
                    "degree": "B.Sc.",
                    "field": "Computer Science",
                    "start_year": 2020,
                    "end_year": 2023,
                }
            ],
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "React"],
            "languages": [
                {"language": "English", "proficiency": "fluent"},
                {"language": "German", "proficiency": "native"},
            ],
            "certifications": [],
        }

    def score_job(self, profile: Profile, job: Job) -> ScoreResult:
        if (override := self._override("score_job")) is not None:
            return override
        return ScoreResult(
            score=75,
            rationale="Strong match on Python and React; some uncertainty on years of experience.",
            matched_skills=["Python", "React"],
            missing_skills=["Kubernetes"],
            red_flags=[],
        )

    def research_company(self, company: str) -> CompanyBrief:
        if (override := self._override("research_company")) is not None:
            return override
        return CompanyBrief(
            company=company,
            markdown=(
                f"# {company}\n\n"
                "## What they do\nA mock company brief — useful in tests and offline dev.\n\n"
                "## Size & funding\n~50 employees, Series A.\n\n"
                "## Recent news\nNothing notable.\n\n"
                "## Tech stack hints\nPython, React.\n\n"
                "## Culture signals\nRemote-friendly, async-first.\n\n"
                "## Sources\n- Mock data, no live sources.\n"
            ),
            sources=[],
        )

    def tailor_cv(self, profile: Profile, job: Job) -> str:
        if (override := self._override("tailor_cv")) is not None:
            return override
        return (
            "## CV tailoring suggestions (mock)\n\n"
            "1. **Emphasize:** lead with Python/FastAPI experience to mirror the job's stack.\n"
            "2. **Reword:** rephrase the most recent role bullet to highlight API design.\n"
            "3. **Add:** include a one-line summary of the team's domain.\n"
            "4. **Deemphasize:** trim early-career internships unrelated to backend work.\n"
        )

    def generate_cover_letter(self, profile: Profile, job: Job, brief: CompanyBrief) -> CoverLetter:
        if (override := self._override("generate_cover_letter")) is not None:
            return override
        body = (
            f"Dear {brief.company} hiring team,\n\n"
            f"I'm applying for the {job.title} role. My background in Python and FastAPI "
            "lines up with what the team is building, and I'm drawn to the async-first "
            "culture you describe.\n\n"
            "In my last role I built and shipped backend services that powered a small but "
            "demanding user base, and I'm looking for a team where I can keep doing that work.\n\n"
            "Thanks for the consideration — I'd love to talk.\n\n"
            "— Alex"
        )
        return CoverLetter(body=body, word_count=len(body.split()))

    def generate_interview_questions(self, job: Job) -> list[InterviewQuestion]:
        if (override := self._override("generate_interview_questions")) is not None:
            return override
        return [
            InterviewQuestion(
                category="behavioral",
                question="Tell me about a time you disagreed with a teammate on a tech choice.",
                what_theyre_assessing="Conflict handling, communication.",
                difficulty="standard",
            ),
            InterviewQuestion(
                category="technical",
                question="How would you design an idempotent POST endpoint?",
                what_theyre_assessing="API design fundamentals.",
                difficulty="standard",
            ),
            InterviewQuestion(
                category="role_specific",
                question=f"What draws you to a {job.title} role specifically?",
                what_theyre_assessing="Motivation and role fit.",
                difficulty="warmup",
            ),
            InterviewQuestion(
                category="company_fit",
                question=f"Why {job.company or 'this company'}?",
                what_theyre_assessing="Research and intent.",
                difficulty="warmup",
            ),
        ]

    def summarize_role(self, job: Job) -> str:
        if (override := self._override("summarize_role")) is not None:
            return override
        company = job.company or "the company"
        return (
            f"As {job.title} at {company} you'd own end-to-end work on the team's core surface — "
            "writing code, shipping reviews, and pairing with whoever needs context that day. The "
            "posting is light on specifics, so expect the day-to-day to track whatever the team's "
            "current sprint is rather than a clean swim-lane.\n\n"
            "You'll be evaluated mostly on shipped work and clarity in technical discussion: "
            "concrete examples beat abstract claims, and the bar is calibrated to a mid-level IC. "
            "Mock data — the real summary is generated by your configured provider."
        )

    def evaluate_answer(self, question: str, answer: str) -> AnswerFeedback:
        if (override := self._override("evaluate_answer")) is not None:
            return override
        return AnswerFeedback(
            what_worked=["Concrete example", "Clear structure"],
            what_to_improve=[
                ImprovementNote(
                    issue="The result was not quantified.",
                    fix="Add a number or metric showing the outcome.",
                )
            ],
            sample_stronger_answer=(
                "Same story, but ending with: '…and we cut p95 latency from 800ms to 220ms "
                "within two sprints.'"
            ),
            off_topic=False,
        )

    def generate_mock_interview_questions(
        self,
        job: Job,
        profile: Profile,
        context: MockInterviewContext,
    ) -> MockInterviewPlan:
        if (override := self._override("generate_mock_interview_questions")) is not None:
            return override
        # Deterministic: an intro plus a rotating set sized to context.num_questions.
        pool = [
            (
                "behavioral",
                f"Tell me about a challenge you faced relevant to a {job.title} role.",
                "Describe a tough situation from your past work and how you handled it.",
            ),
            (
                "technical",
                "Walk me through how you'd approach a problem central to this role.",
                "How would you tackle a core technical task this job involves?",
            ),
            (
                "role_specific",
                f"What does a strong first 90 days look like as a {job.title}?",
                f"How would you ramp up and add value early in this {job.title} role?",
            ),
            (
                "company_fit",
                f"Why {job.company or 'this company'}?",
                f"What draws you specifically to {job.company or 'this company'}?",
            ),
        ]
        questions = [
            MockQuestion(
                category="behavioral",
                question="To start, tell me a bit about yourself and your background.",
                rephrasing="Walk me through your career so far and what brought you here.",
                time_limit_seconds=300,
                is_intro=True,
            )
        ]
        for i in range(max(0, context.num_questions - 1)):
            cat, q, rephrase = pool[i % len(pool)]
            questions.append(
                MockQuestion(
                    category=cat,  # type: ignore[arg-type]
                    question=q,
                    rephrasing=rephrase,
                    time_limit_seconds=180,
                    is_intro=False,
                )
            )
        return MockInterviewPlan(questions=questions)

    def evaluate_mock_interview(
        self,
        job: Job,
        context: MockInterviewContext,
        qa_pairs: list[MockQAPair],
    ) -> MockInterviewEvaluation:
        if (override := self._override("evaluate_mock_interview")) is not None:
            return override
        ratings = [
            MockAnswerRating(
                question=qa.question,
                rating=70,
                comment="Solid, concrete answer — add a quantified result to make it stronger.",
            )
            for qa in qa_pairs
        ]
        return MockInterviewEvaluation(
            per_question=ratings,
            overall_percentage=70,
            strengths=["Clear structure", "Relevant examples"],
            weaknesses=["Quantify outcomes", "Tie answers more tightly to the role"],
        )

    def interview_chat_stream(
        self,
        messages: list[ChatMessage],
        role_context: str | None = None,
    ) -> Iterator[str]:
        override = self._override("interview_chat_stream")
        if override is not None:
            # Override may be a full string, a list of chunks, or an iterable.
            if isinstance(override, str):
                return iter([override])
            return iter(list(override))

        # Default: respond to the last user turn (if any) with a deterministic,
        # CRITIQUE-AND-FOLLOWUP-shaped reply. Yielded as several chunks so
        # streaming consumers can verify they see more than one event.
        last_user = next((m for m in reversed(messages) if m.role == "user"), None)
        if last_user is None:
            chunks = [
                "Let's start. Tell me about a recent project ",
                "where you owned the design end-to-end — ",
                "what was the trickiest call you had to make?",
            ]
        else:
            preview = (last_user.content or "").strip().split("\n", 1)[0][:80]
            chunks = [
                f'You opened with "{preview}" — ',
                "that's a concrete hook, which is the right instinct.\n\n",
                "The gap is the impact: nothing in the answer tells me what changed ",
                "because of you. An interviewer can't tell whether your work mattered.\n\n",
                "Add one number or one before/after sentence. Lead with it next time.\n\n",
                "Follow-up: what would have happened on this project if you had ",
                "stepped away halfway through?",
            ]
        return iter(chunks)


__all__ = ["MockProvider"]
