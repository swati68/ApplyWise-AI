from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from uuid import uuid4

from app.repositories.digest_repository import JobDigestItem
from app.services.digest_service import DigestService
from app.services.email.smtp_email_service import EmailConfigurationError


class DigestServiceTests(unittest.TestCase):
    def test_send_digest_includes_matched_jobs_and_resume_links(self) -> None:
        user = SimpleNamespace(
            id=uuid4(),
            email="user@example.com",
            full_name="Test User",
        )
        generated_resume_id = uuid4()
        item = JobDigestItem(
            job=SimpleNamespace(
                id=uuid4(),
                company="Acme",
                title="Backend Engineer",
                location="Remote",
                job_url="https://example.com/job",
            ),
            match=SimpleNamespace(
                id=uuid4(),
                score=88,
                match_reason="Strong Python and FastAPI match.",
                created_at=datetime.now(UTC),
            ),
            generated_resume=SimpleNamespace(
                id=generated_resume_id,
                drive_url=None,
                pdf_path="storage/resumes/user/resume.pdf",
                safety_warnings=["Missing verified Kubernetes experience."],
            ),
        )
        email_service = FakeEmailService()
        service = DigestService(
            repository=FakeDigestRepository([item]),
            email_service=email_service,
            api_base_url="http://localhost:8000/api",
        )

        result = service.send_digest(user=user)

        self.assertTrue(result.success)
        self.assertEqual(result.item_count, 1)
        self.assertEqual(email_service.to_email, "user@example.com")
        self.assertIn("Acme", email_service.html_body)
        self.assertIn("Backend Engineer", email_service.html_body)
        self.assertIn("Strong Python", email_service.html_body)
        self.assertIn(str(generated_resume_id), email_service.html_body)
        self.assertIn("Missing verified Kubernetes", email_service.html_body)

    def test_send_digest_prefers_drive_link_over_local_pdf_link(self) -> None:
        user = SimpleNamespace(
            id=uuid4(),
            email="user@example.com",
            full_name=None,
        )
        item = JobDigestItem(
            job=SimpleNamespace(
                id=uuid4(),
                company="Acme",
                title="Backend Engineer",
                location=None,
                job_url=None,
            ),
            match=SimpleNamespace(
                id=uuid4(),
                score=77,
                match_reason="Relevant API work.",
                created_at=datetime.now(UTC),
            ),
            generated_resume=SimpleNamespace(
                id=uuid4(),
                drive_url="https://drive.google.com/file/d/test/view",
                pdf_path="storage/resumes/user/resume.pdf",
                safety_warnings=[],
            ),
        )
        email_service = FakeEmailService()
        service = DigestService(
            repository=FakeDigestRepository([item]),
            email_service=email_service,
            api_base_url="http://localhost:8000/api",
        )

        result = service.send_digest(user=user)

        self.assertTrue(result.success)
        self.assertIn("https://drive.google.com/file/d/test/view", email_service.html_body)
        self.assertNotIn("/generated-resumes/", email_service.html_body)

    def test_send_digest_returns_configuration_error_without_raising(self) -> None:
        user = SimpleNamespace(
            id=uuid4(),
            email="user@example.com",
            full_name=None,
        )
        service = DigestService(
            repository=FakeDigestRepository([]),
            email_service=FailingEmailService(),
            api_base_url="http://localhost:8000/api",
        )

        result = service.send_digest(user=user)

        self.assertFalse(result.success)
        self.assertEqual(result.item_count, 0)
        self.assertIn("SMTP_HOST", result.error_message or "")


class FakeDigestRepository:
    def __init__(self, items: list[JobDigestItem]) -> None:
        self.items = items

    def list_latest_matched_jobs(self, user_id):
        return self.items


class FakeEmailService:
    def __init__(self) -> None:
        self.to_email = ""
        self.subject = ""
        self.html_body = ""
        self.text_body = ""

    def send_html_email(self, *, to_email, subject, html_body, text_body) -> None:
        self.to_email = to_email
        self.subject = subject
        self.html_body = html_body
        self.text_body = text_body


class FailingEmailService:
    def send_html_email(self, *, to_email, subject, html_body, text_body) -> None:
        raise EmailConfigurationError("SMTP_HOST is required.")


if __name__ == "__main__":
    unittest.main()
