from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from uuid import uuid4

from app.core.config import Settings
from app.services.github_source_pipeline_service import GithubSourcePipelineService
from app.services.resume_pdf_service import PDF_STORAGE_ROOT


class GithubSourcePipelineServiceTests(unittest.TestCase):
    def test_pipeline_matches_generates_compiles_uploads_and_sends_digest(self) -> None:
        user = SimpleNamespace(id=uuid4(), email="user@example.com", full_name="User")
        source = SimpleNamespace(id=uuid4(), user_id=user.id)
        high_score_job = _job(user.id, "Acme", "Backend Engineer")
        low_score_job = _job(user.id, "Beta", "Frontend Engineer")
        generated_resume = SimpleNamespace(
            id=uuid4(),
            user_id=user.id,
            job_id=high_score_job.id,
            pdf_path=None,
            drive_url=None,
        )
        PDF_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=PDF_STORAGE_ROOT) as temp_dir_name:
            pdf_path = Path(temp_dir_name) / "resume.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            generated_resume_repository = FakeGeneratedResumeRepository(
                generated_resume=generated_resume,
                pdf_path=str(pdf_path),
            )
            service = GithubSourcePipelineService(
                scan_service=FakeScanService(
                    inserted_jobs=[high_score_job, low_score_job],
                    total_rows_seen=4,
                    parsed_jobs=3,
                    duplicate_jobs=1,
                ),
                match_service=FakeMatchService(
                    scores={
                        high_score_job.id: 85,
                        low_score_job.id: 55,
                    }
                ),
                resume_generation_service=FakeResumeGenerationService(generated_resume),
                pdf_service=FakePdfService(success=True),
                generated_resume_repository=generated_resume_repository,
                digest_service=FakeDigestService(success=True),
                settings=Settings(
                    google_drive_service_account_json='{"client_email":"service@example.com"}',
                ),
                drive_service=FakeGoogleDriveService(),
            )

            result = service.run(
                source=source,
                user=user,
                min_match_score=70,
            )

        self.assertEqual(result.total_rows_seen, 4)
        self.assertEqual(result.parsed_jobs, 3)
        self.assertEqual(result.inserted_jobs, 2)
        self.assertEqual(result.duplicate_jobs, 1)
        self.assertEqual(result.jobs_matched, 2)
        self.assertEqual(result.resumes_generated, 1)
        self.assertEqual(result.pdfs_compiled, 1)
        self.assertEqual(result.drive_uploads_successful, 1)
        self.assertEqual(result.emails_sent, 1)
        self.assertEqual(result.errors, [])
        self.assertEqual(generated_resume.drive_url, "https://drive.google.com/file/d/test/view")

    def test_pipeline_records_skipped_match_and_digest_error(self) -> None:
        user = SimpleNamespace(id=uuid4(), email="user@example.com", full_name="User")
        job = _job(user.id, "Acme", "Backend Engineer")
        service = GithubSourcePipelineService(
            scan_service=FakeScanService(
                inserted_jobs=[job],
                total_rows_seen=1,
                parsed_jobs=1,
                duplicate_jobs=0,
            ),
            match_service=FakeMatchService(skipped_job_ids={job.id}),
            resume_generation_service=FakeResumeGenerationService(None),
            pdf_service=FakePdfService(success=True),
            generated_resume_repository=FakeGeneratedResumeRepository(),
            digest_service=FakeDigestService(success=False),
            settings=Settings(),
        )

        result = service.run(
            source=SimpleNamespace(id=uuid4(), user_id=user.id),
            user=user,
            min_match_score=70,
        )

        self.assertEqual(result.jobs_matched, 0)
        self.assertEqual(result.resumes_generated, 0)
        self.assertEqual(result.emails_sent, 0)
        self.assertEqual(len(result.errors), 2)
        self.assertIn("Skipped matching", result.errors[0])
        self.assertIn("Digest email was not sent", result.errors[1])


class FakeScanService:
    def __init__(
        self,
        *,
        inserted_jobs,
        total_rows_seen,
        parsed_jobs,
        duplicate_jobs,
    ) -> None:
        self.inserted_jobs = inserted_jobs
        self.total_rows_seen = total_rows_seen
        self.parsed_jobs = parsed_jobs
        self.duplicate_jobs = duplicate_jobs

    def scan_source(self, source):
        return SimpleNamespace(
            total_rows_seen=self.total_rows_seen,
            parsed_jobs=self.parsed_jobs,
            inserted_jobs=len(self.inserted_jobs),
            inserted_job_records=self.inserted_jobs,
            duplicate_jobs=self.duplicate_jobs,
        )


class FakeMatchService:
    def __init__(self, scores=None, skipped_job_ids=None) -> None:
        self.scores = scores or {}
        self.skipped_job_ids = skipped_job_ids or set()

    def match_job(self, *, user_id, job):
        if job.id in self.skipped_job_ids:
            return SimpleNamespace(
                id=uuid4(),
                user_id=user_id,
                job_id=job.id,
                score=0,
                match_reason="Skipped matching because extraction failed.",
            )

        return SimpleNamespace(
            id=uuid4(),
            user_id=user_id,
            job_id=job.id,
            score=self.scores[job.id],
            match_reason="Score components: exact skills 40.0/40.",
        )


class FakeResumeGenerationService:
    def __init__(self, generated_resume) -> None:
        self.generated_resume = generated_resume

    def generate_for_job(self, *, user_id, job):
        return self.generated_resume


class FakePdfService:
    def __init__(self, *, success: bool) -> None:
        self.success = success

    def compile_pdf(self, generated_resume):
        return SimpleNamespace(
            success=self.success,
            error_message=None if self.success else "Compile failed.",
        )


class FakeGeneratedResumeRepository:
    def __init__(self, generated_resume=None, pdf_path: str | None = None) -> None:
        self.generated_resume = generated_resume
        self.pdf_path = pdf_path

    def get_for_user(self, user_id, resume_id):
        if self.generated_resume is None:
            return None

        self.generated_resume.pdf_path = self.pdf_path
        return self.generated_resume

    def update(self, generated_resume, values):
        for field, value in values.items():
            setattr(generated_resume, field, value)
        return generated_resume


class FakeGoogleDriveService:
    def upload_pdf(self, *, pdf_path, file_name):
        return SimpleNamespace(
            drive_url="https://drive.google.com/file/d/test/view",
        )


class FakeDigestService:
    def __init__(self, *, success: bool) -> None:
        self.success = success

    def send_digest(self, *, user):
        return SimpleNamespace(
            success=self.success,
            error_message=None if self.success else "SMTP_HOST is required.",
        )


def _job(user_id, company: str, title: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        company=company,
        title=title,
    )


if __name__ == "__main__":
    unittest.main()
