from types import SimpleNamespace
import unittest
from uuid import uuid4

from app.core.config import Settings
from app.models.job_posting import JobExtractionStatus, JobSource, JobStatus
from app.services.jobs.job_content_extractor import ExtractedJobContent
from app.services.manual_job_pipeline_service import ManualJobPipelineService
from app.services.resume_pdf_service import PdfCompileResult


class ManualJobPipelineServiceTests(unittest.TestCase):
    def test_pipeline_creates_url_job_and_runs_generation_steps(self) -> None:
        user_id = uuid4()
        generated_resume = _generated_resume(user_id=user_id)
        job_repository = FakeJobRepository()
        service = ManualJobPipelineService(
            job_repository=job_repository,
            match_service=FakeMatchService(),
            resume_generation_service=FakeResumeGenerationService(generated_resume),
            generated_resume_repository=FakeGeneratedResumeRepository(generated_resume),
            pdf_service=FakePdfService(success=True),
            settings=Settings(),
            extractor=FakeExtractor(_extracted_content()),
        )

        result = service.run(
            user_id=user_id,
            job_url="https://example.com/careers/backend-engineer/",
        )

        self.assertFalse(result.duplicate)
        self.assertEqual(result.job.company, "Acme Systems")
        self.assertEqual(result.job.title, "Backend Engineer")
        self.assertEqual(result.job.location, "New York, NY")
        self.assertEqual(result.job.extraction_status, JobExtractionStatus.SUCCESS)
        self.assertEqual(result.match_result.score, 88)
        self.assertEqual(result.generated_resume_result.id, generated_resume.id)
        self.assertTrue(result.pdf_result.success)
        self.assertTrue(result.drive_result.skipped)
        self.assertEqual(result.errors, [])

    def test_pipeline_reuses_duplicate_url_and_still_generates_resume(self) -> None:
        user_id = uuid4()
        existing_job = _job(
            user_id=user_id,
            job_url="https://example.com/careers/backend-engineer",
            company="example.com",
            title="Job posting",
        )
        generated_resume = _generated_resume(user_id=user_id, job_id=existing_job.id)
        service = ManualJobPipelineService(
            job_repository=FakeJobRepository(existing_jobs=[existing_job]),
            match_service=FakeMatchService(),
            resume_generation_service=FakeResumeGenerationService(generated_resume),
            generated_resume_repository=FakeGeneratedResumeRepository(generated_resume),
            pdf_service=FakePdfService(success=False),
            settings=Settings(),
            extractor=FakeExtractor(_extracted_content()),
        )

        result = service.run(
            user_id=user_id,
            job_url="https://example.com/careers/backend-engineer/",
        )

        self.assertTrue(result.duplicate)
        self.assertEqual(result.job.id, existing_job.id)
        self.assertEqual(result.job.company, "Acme Systems")
        self.assertEqual(result.job.title, "Backend Engineer")
        self.assertIsNotNone(result.generated_resume_result)
        self.assertFalse(result.pdf_result.success)
        self.assertIn("PDF compilation failed", result.errors[0])


class FakeJobRepository:
    def __init__(self, existing_jobs=None) -> None:
        self.jobs = existing_jobs or []

    def list_by_user(self, user_id):
        return [job for job in self.jobs if job.user_id == user_id]

    def find_by_job_url(self, *, user_id, job_url, exclude_job_id=None):
        for job in self.list_by_user(user_id):
            if exclude_job_id is not None and job.id == exclude_job_id:
                continue
            if job.job_url == job_url:
                return job
        return None

    def find_by_content_hash(self, *, user_id, content_hash, exclude_job_id=None):
        for job in self.list_by_user(user_id):
            if exclude_job_id is not None and job.id == exclude_job_id:
                continue
            if job.content_hash == content_hash:
                return job
        return None

    def create(self, values):
        job = SimpleNamespace(id=uuid4(), **values)
        self.jobs.append(job)
        return job

    def update(self, job, values):
        for field, value in values.items():
            setattr(job, field, value)
        return job

    def rollback(self):
        return None


class FakeExtractor:
    def __init__(self, result: ExtractedJobContent) -> None:
        self.result = result

    def extract_job_content(self, job_url: str) -> ExtractedJobContent:
        return self.result


class FakeMatchService:
    def match_job(self, *, user_id, job):
        return SimpleNamespace(
            id=uuid4(),
            user_id=user_id,
            job_id=job.id,
            score=88,
            exact_skill_matches=[],
            fuzzy_skill_matches=[],
            missing_skills=[],
            relevant_experiences=[],
            relevant_projects=[],
            match_reason="Score components: exact skills 40.0/40.",
            created_at=None,
        )


class FakeResumeGenerationService:
    def __init__(self, generated_resume) -> None:
        self.generated_resume = generated_resume

    def generate_for_job(self, *, user_id, job):
        self.generated_resume.job_id = job.id
        return self.generated_resume


class FakeGeneratedResumeRepository:
    def __init__(self, generated_resume) -> None:
        self.generated_resume = generated_resume
        self.latest_resume = None

    def get_latest_for_job(self, user_id, job_id):
        return self.latest_resume

    def get_for_user(self, user_id, resume_id):
        return self.generated_resume

    def update(self, generated_resume, values):
        for field, value in values.items():
            setattr(generated_resume, field, value)
        return generated_resume


class FakePdfService:
    def __init__(self, *, success: bool) -> None:
        self.success = success

    def compile_pdf(self, generated_resume):
        return PdfCompileResult(
            success=self.success,
            resume_id=generated_resume.id,
            pdf_path="storage/resumes/test.pdf" if self.success else None,
            download_url=f"/api/generated-resumes/{generated_resume.id}/download"
            if self.success
            else None,
            compiler="tectonic",
            logs=None,
            error_message=None if self.success else "Compile failed.",
        )


def _extracted_content() -> ExtractedJobContent:
    return ExtractedJobContent(
        cleaned_text="Responsibilities\nBuild APIs.\n\nRequirements\nPython and SQL.",
        page_title="Backend Engineer | Acme",
        company_guess="Acme Systems",
        extraction_success=True,
        extraction_method="json_ld_job_posting",
        title_guess="Backend Engineer",
        location_guess="New York, NY",
    )


def _job(
    *,
    user_id,
    job_url: str,
    company: str,
    title: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        source=JobSource.MANUAL,
        source_repo_url=None,
        source_raw_url=None,
        external_job_id=None,
        company=company,
        title=title,
        location=None,
        job_url=job_url,
        description=None,
        raw_text=None,
        extracted_description=None,
        extraction_status=JobExtractionStatus.NOT_STARTED,
        extraction_error=None,
        extracted_at=None,
        posted_at=None,
        discovered_at=None,
        status=JobStatus.NEW,
        content_hash="old-hash",
        created_at=None,
        updated_at=None,
    )


def _generated_resume(*, user_id, job_id=None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        job_id=job_id or uuid4(),
        resume_template_id=uuid4(),
        tailored_latex="\\documentclass{article}\\begin{document}Test\\end{document}",
        selected_experiences=[],
        selected_projects=[],
        selected_skills=[],
        change_summary=[],
        safety_warnings=[],
        pdf_path=None,
        drive_url=None,
        created_at=None,
    )


if __name__ == "__main__":
    unittest.main()
