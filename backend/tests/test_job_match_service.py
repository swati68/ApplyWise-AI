from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from app.models.job_posting import JobExtractionStatus
from app.services.job_match_service import JobMatchService, LowMatchScoreError
from app.services.jobs.job_content_extractor import ExtractedJobContent


class JobMatchServiceTests(unittest.TestCase):
    def test_matching_uses_extracted_description_not_raw_row_text(self) -> None:
        user_id = uuid4()
        job = _job(
            user_id=user_id,
            extracted_description="Full JD requires Python and FastAPI for API services.",
            raw_text="GitHub table row mentions Kubernetes only.",
        )
        match_repository = FakeJobMatchRepository()
        service = JobMatchService(match_repository)

        with patch(
            "app.services.job_match_service.extract_job_requirements",
            return_value={
                "required_skills": ["Python"],
                "preferred_skills": ["FastAPI"],
                "responsibilities": ["Build API services."],
                "keywords": ["Python", "FastAPI"],
            },
        ) as extract_requirements:
            match = service.match_job(user_id=user_id, job=job)

        extract_requirements.assert_called_once_with(
            "Full JD requires Python and FastAPI for API services.",
        )
        self.assertGreater(match.score, 0)
        self.assertEqual(match.exact_skill_matches, ["Python", "FastAPI"])
        self.assertNotIn("Kubernetes", match.match_reason)

    def test_missing_description_is_extracted_before_matching(self) -> None:
        user_id = uuid4()
        job = _job(
            user_id=user_id,
            extracted_description=None,
            job_url="https://example.com/job",
        )
        match_repository = FakeJobMatchRepository()
        job_repository = FakeJobPostingRepository()
        extractor = FakeJobContentExtractor(
            ExtractedJobContent(
                cleaned_text="Extracted JD requires Python for backend APIs.",
                page_title="Backend Engineer",
                company_guess="Example",
                extraction_success=True,
                extraction_method="test",
            )
        )
        service = JobMatchService(
            match_repository,
            job_repository=job_repository,
            extractor=extractor,
        )

        with patch(
            "app.services.job_match_service.extract_job_requirements",
            return_value={
                "required_skills": ["Python"],
                "preferred_skills": [],
                "responsibilities": ["Build APIs."],
                "keywords": ["Python"],
            },
        ) as extract_requirements:
            match = service.match_job(user_id=user_id, job=job)

        self.assertEqual(extractor.seen_urls, ["https://example.com/job"])
        self.assertEqual(job.extraction_status, JobExtractionStatus.SUCCESS)
        self.assertEqual(job.extracted_description, "Extracted JD requires Python for backend APIs.")
        extract_requirements.assert_called_once_with(
            "Extracted JD requires Python for backend APIs.",
        )
        self.assertGreater(match.score, 0)

    def test_extraction_failure_skips_matching_and_stores_reason(self) -> None:
        user_id = uuid4()
        job = _job(
            user_id=user_id,
            extracted_description=None,
            job_url="https://example.com/blocked",
            raw_text="GitHub row says Python.",
        )
        match_repository = FakeJobMatchRepository()
        job_repository = FakeJobPostingRepository()
        extractor = FakeJobContentExtractor(
            ExtractedJobContent(
                cleaned_text="Blocked",
                page_title="Blocked",
                company_guess=None,
                extraction_success=False,
                extraction_method="test",
                error_message="Could not extract a meaningful job description.",
            )
        )
        service = JobMatchService(
            match_repository,
            job_repository=job_repository,
            extractor=extractor,
        )

        with patch("app.services.job_match_service.extract_job_requirements") as extract_requirements:
            match = service.match_job(user_id=user_id, job=job)

        extract_requirements.assert_not_called()
        self.assertEqual(match.score, 0)
        self.assertEqual(job.extraction_status, JobExtractionStatus.FAILED)
        self.assertIn("Skipped matching", match.match_reason)
        self.assertIn("extraction failed", match.match_reason)

    def test_missing_url_skips_matching_without_using_raw_text(self) -> None:
        user_id = uuid4()
        job = _job(
            user_id=user_id,
            extracted_description=None,
            job_url=None,
            raw_text="GitHub row says Python and FastAPI.",
        )
        service = JobMatchService(FakeJobMatchRepository())

        with patch("app.services.job_match_service.extract_job_requirements") as extract_requirements:
            match = service.match_job(user_id=user_id, job=job)

        extract_requirements.assert_not_called()
        self.assertEqual(match.score, 0)
        self.assertIn("no job URL", match.match_reason)

    def test_low_score_match_is_not_stored(self) -> None:
        user_id = uuid4()
        job = _job(
            user_id=user_id,
            extracted_description="Full JD requires Kubernetes operators and embedded Rust firmware.",
        )
        match_repository = FakeJobMatchRepository()
        service = JobMatchService(match_repository)

        with patch(
            "app.services.job_match_service.extract_job_requirements",
            return_value={
                "required_skills": ["Kubernetes operators", "embedded Rust"],
                "preferred_skills": [],
                "responsibilities": ["Maintain firmware and cluster operators."],
                "keywords": ["Kubernetes", "Rust", "firmware"],
            },
        ):
            with self.assertRaises(LowMatchScoreError):
                service.match_job(user_id=user_id, job=job)

        self.assertEqual(match_repository.created_matches, [])


class FakeJobMatchRepository:
    def __init__(self) -> None:
        self.created_matches: list[SimpleNamespace] = []

    def list_user_skills(self, user_id):
        return [
            SimpleNamespace(
                id=uuid4(),
                user_id=user_id,
                name="Python",
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
                tech_stack=["Python", "FastAPI"],
                bullets=["Built Python API services."],
            )
        ]

    def list_user_projects(self, user_id):
        return [
            SimpleNamespace(
                id=uuid4(),
                user_id=user_id,
                name="API Platform",
                description="Backend APIs",
                tech_stack=["Python"],
                bullets=["Implemented FastAPI services."],
            )
        ]

    def create(self, values: dict[str, object]) -> SimpleNamespace:
        match = SimpleNamespace(id=uuid4(), created_at=datetime.now(UTC), **values)
        self.created_matches.append(match)
        return match


class FakeJobPostingRepository:
    def update(self, job: SimpleNamespace, values: dict[str, object]) -> SimpleNamespace:
        for field, value in values.items():
            setattr(job, field, value)
        return job


class FakeJobContentExtractor:
    def __init__(self, result: ExtractedJobContent) -> None:
        self.result = result
        self.seen_urls: list[str] = []

    def extract_job_content(self, job_url: str) -> ExtractedJobContent:
        self.seen_urls.append(job_url)
        return self.result


def _job(
    *,
    user_id,
    extracted_description,
    job_url="https://example.com/job",
    raw_text="",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        company="Example",
        title="Backend Engineer",
        location="Remote",
        job_url=job_url,
        description=None,
        raw_text=raw_text,
        extracted_description=extracted_description,
        extraction_status=JobExtractionStatus.NOT_STARTED,
        extraction_error=None,
        extracted_at=None,
    )


if __name__ == "__main__":
    unittest.main()
