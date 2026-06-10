from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from app.models.job_posting import JobExtractionStatus
from app.services.resume_generation_service import (
    NoDefaultResumeTemplateError,
    ResumeGenerationBlockedError,
    ResumeGenerationService,
)


class ResumeGenerationServiceTests(unittest.TestCase):
    def test_generates_resume_from_existing_match_and_default_template(self) -> None:
        user_id = uuid4()
        job = _job(user_id=user_id)
        match = _match(user_id=user_id, job_id=job.id)
        generated_repository = FakeGeneratedResumeRepository()
        match_repository = FakeJobMatchRepository(latest_match=match)
        template = _template(user_id=user_id)
        service = _service(
            generated_repository=generated_repository,
            match_repository=match_repository,
            template_repository=FakeResumeTemplateRepository(template),
        )
        captured_job_context: dict[str, object] = {}

        def fake_tailor(profile_json, job_json, latex_template):
            captured_job_context.update(job_json)
            return {
                "tailored_latex": "\\documentclass{article}\\begin{document}Tailored\\end{document}",
                "selected_experiences": ["Backend Engineer at Acme"],
                "selected_projects": ["API Platform"],
                "selected_skills": ["Python"],
                "change_summary": ["Selected backend API experience."],
                "safety_warnings": [],
            }

        with patch(
            "app.services.resume_generation_service.tailor_latex_resume",
            side_effect=fake_tailor,
        ):
            generated_resume = service.generate_for_job(user_id=user_id, job=job)

        self.assertEqual(generated_resume.user_id, user_id)
        self.assertEqual(generated_resume.job_id, job.id)
        self.assertEqual(generated_resume.resume_template_id, template.id)
        self.assertEqual(generated_resume.selected_skills, ["Python"])
        self.assertEqual(
            captured_job_context["job"]["extracted_description"],
            job.extracted_description,
        )
        self.assertNotIn("raw_text", captured_job_context["job"])

    def test_runs_match_when_no_match_exists(self) -> None:
        user_id = uuid4()
        job = _job(user_id=user_id)
        match_repository = FakeJobMatchRepository(latest_match=None)
        service = _service(match_repository=match_repository)

        with patch(
            "app.services.job_match_service.extract_job_requirements",
            return_value={
                "required_skills": ["Python"],
                "preferred_skills": [],
                "responsibilities": ["Build API services."],
                "keywords": ["Python"],
            },
        ), patch(
            "app.services.resume_generation_service.tailor_latex_resume",
            return_value={
                "tailored_latex": "\\documentclass{article}\\begin{document}Tailored\\end{document}",
                "selected_experiences": [],
                "selected_projects": [],
                "selected_skills": ["Python"],
                "change_summary": [],
                "safety_warnings": [],
            },
        ):
            generated_resume = service.generate_for_job(user_id=user_id, job=job)

        self.assertIsNotNone(match_repository.latest_match)
        self.assertEqual(generated_resume.job_id, job.id)

    def test_missing_default_template_blocks_generation(self) -> None:
        user_id = uuid4()
        job = _job(user_id=user_id)
        service = _service(
            match_repository=FakeJobMatchRepository(
                latest_match=_match(user_id=user_id, job_id=job.id),
            ),
            template_repository=FakeResumeTemplateRepository(None),
        )

        with self.assertRaises(NoDefaultResumeTemplateError):
            service.generate_for_job(user_id=user_id, job=job)

    def test_skipped_match_blocks_generation(self) -> None:
        user_id = uuid4()
        job = _job(
            user_id=user_id,
            extracted_description=None,
            job_url=None,
        )
        service = _service(match_repository=FakeJobMatchRepository(latest_match=None))

        with self.assertRaises(ResumeGenerationBlockedError) as error:
            service.generate_for_job(user_id=user_id, job=job)

        self.assertIn("Skipped matching", str(error.exception))

    def test_unverified_ai_bullets_fall_back_to_original_template(self) -> None:
        user_id = uuid4()
        job = _job(user_id=user_id)
        template = _template(
            user_id=user_id,
            latex_content=(
                "\\documentclass{article}\\begin{document}"
                "\\begin{itemize}\\item Original template bullet.\\end{itemize}"
                "\\end{document}"
            ),
        )
        service = _service(
            match_repository=FakeJobMatchRepository(
                latest_match=_match(user_id=user_id, job_id=job.id),
            ),
            template_repository=FakeResumeTemplateRepository(template),
        )

        with patch(
            "app.services.resume_generation_service.tailor_latex_resume",
            return_value={
                "tailored_latex": (
                    "\\documentclass{article}\\begin{document}"
                    "\\begin{itemize}\\item Invented production impact.\\end{itemize}"
                    "\\end{document}"
                ),
                "selected_experiences": [],
                "selected_projects": [],
                "selected_skills": ["Python"],
                "change_summary": [],
                "safety_warnings": [],
            },
        ):
            generated_resume = service.generate_for_job(user_id=user_id, job=job)

        self.assertEqual(generated_resume.tailored_latex, template.latex_content)
        self.assertIn("not copied from the saved profile", generated_resume.safety_warnings[0])


class FakeGeneratedResumeRepository:
    def create(self, values: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(id=uuid4(), created_at=datetime.now(UTC), **values)


class FakeJobRepository:
    def update(self, job: SimpleNamespace, values: dict[str, object]) -> SimpleNamespace:
        for field, value in values.items():
            setattr(job, field, value)
        return job


class FakeJobMatchRepository:
    def __init__(self, latest_match: SimpleNamespace | None) -> None:
        self.latest_match = latest_match

    def get_latest_for_job(self, user_id, job_id):
        return self.latest_match

    def list_user_skills(self, user_id):
        return [
            SimpleNamespace(
                id=uuid4(),
                user_id=user_id,
                category="Programming",
                name="Python",
                proficiency=None,
                tags=["FastAPI"],
            )
        ]

    def list_user_experiences(self, user_id):
        return [
            SimpleNamespace(
                id=uuid4(),
                user_id=user_id,
                company="Acme",
                role="Backend Engineer",
                location="Remote",
                start_date=None,
                end_date=None,
                is_current=True,
                tech_stack=["Python"],
                bullets=["Built API services."],
                tags=[],
            )
        ]

    def list_user_projects(self, user_id):
        return [
            SimpleNamespace(
                id=uuid4(),
                user_id=user_id,
                name="API Platform",
                description="Backend API system",
                tech_stack=["Python"],
                bullets=["Created FastAPI services."],
                links=[],
                tags=[],
            )
        ]

    def create(self, values: dict[str, object]) -> SimpleNamespace:
        self.latest_match = SimpleNamespace(id=uuid4(), created_at=datetime.now(UTC), **values)
        return self.latest_match


class FakeResumeTemplateRepository:
    def __init__(self, template: SimpleNamespace | None) -> None:
        self.template = template

    def get_default_for_user(self, user_id):
        return self.template


class FakeProfileRepository:
    def __init__(self, values: list[SimpleNamespace]) -> None:
        self.values = values

    def list_by_user(self, user_id):
        return self.values


def _service(
    *,
    generated_repository: FakeGeneratedResumeRepository | None = None,
    match_repository: FakeJobMatchRepository | None = None,
    template_repository: FakeResumeTemplateRepository | None = None,
) -> ResumeGenerationService:
    return ResumeGenerationService(
        generated_resume_repository=generated_repository or FakeGeneratedResumeRepository(),
        job_repository=FakeJobRepository(),
        job_match_repository=match_repository
        or FakeJobMatchRepository(latest_match=_match(user_id=uuid4(), job_id=uuid4())),
        resume_template_repository=template_repository
        or FakeResumeTemplateRepository(_template(user_id=uuid4())),
        education_repository=FakeProfileRepository(
            [
                SimpleNamespace(
                    id=uuid4(),
                    institution="Example University",
                    degree="BS",
                    field_of_study="Computer Science",
                    start_date=None,
                    end_date=None,
                    gpa=None,
                    location=None,
                    description=None,
                )
            ]
        ),
        experience_repository=FakeProfileRepository([]),
        project_repository=FakeProfileRepository([]),
        skill_repository=FakeProfileRepository(
            [
                SimpleNamespace(
                    id=uuid4(),
                    category="Programming",
                    name="Python",
                    proficiency=None,
                    tags=[],
                )
            ]
        ),
    )


def _job(
    *,
    user_id,
    extracted_description="Full JD requires Python and API development.",
    job_url="https://example.com/job",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        company="Example",
        title="Backend Engineer",
        location="Remote",
        job_url=job_url,
        extracted_description=extracted_description,
        extraction_status=JobExtractionStatus.SUCCESS
        if extracted_description
        else JobExtractionStatus.NOT_STARTED,
        extraction_error=None,
        extracted_at=datetime.now(UTC) if extracted_description else None,
    )


def _match(user_id, job_id) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        job_id=job_id,
        score=75,
        exact_skill_matches=["Python"],
        fuzzy_skill_matches=[],
        missing_skills=[],
        relevant_experiences=[],
        relevant_projects=[],
        match_reason="Score components: exact skills 40.0/40.",
        created_at=datetime.now(UTC),
    )


def _template(
    user_id,
    latex_content="\\documentclass{article}\\begin{document}Base\\end{document}",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        latex_content=latex_content,
        is_default=True,
    )


if __name__ == "__main__":
    unittest.main()
