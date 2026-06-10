from dataclasses import dataclass
from datetime import UTC, datetime

from app.models.user import User
from app.repositories.digest_repository import DigestRepository, JobDigestItem
from app.services.email.digest_template import (
    render_digest_html_email,
    render_digest_text_email,
)
from app.services.email.smtp_email_service import (
    EmailConfigurationError,
    EmailSendError,
    SmtpEmailService,
)


@dataclass(frozen=True)
class DigestSendResult:
    success: bool
    recipient_email: str
    item_count: int
    sent_at: datetime | None
    error_message: str | None


class DigestService:
    def __init__(
        self,
        *,
        repository: DigestRepository,
        email_service: SmtpEmailService,
        api_base_url: str,
    ) -> None:
        self.repository = repository
        self.email_service = email_service
        self.api_base_url = api_base_url.rstrip("/")

    def send_digest(self, *, user: User) -> DigestSendResult:
        items = self.repository.list_latest_matched_jobs(user.id)
        download_url_by_resume_id = _download_urls_by_resume_id(
            items=items,
            api_base_url=self.api_base_url,
        )
        html_body = render_digest_html_email(
            recipient_name=user.full_name,
            items=items,
            download_url_by_resume_id=download_url_by_resume_id,
        )
        text_body = render_digest_text_email(
            recipient_name=user.full_name,
            items=items,
            download_url_by_resume_id=download_url_by_resume_id,
        )
        try:
            self.email_service.send_html_email(
                to_email=user.email,
                subject=f"ApplyWise AI digest: {len(items)} matched job{'s' if len(items) != 1 else ''}",
                html_body=html_body,
                text_body=text_body,
            )
        except (EmailConfigurationError, EmailSendError) as error:
            return DigestSendResult(
                success=False,
                recipient_email=user.email,
                item_count=len(items),
                sent_at=None,
                error_message=str(error),
            )

        return DigestSendResult(
            success=True,
            recipient_email=user.email,
            item_count=len(items),
            sent_at=datetime.now(UTC),
            error_message=None,
        )


def _download_urls_by_resume_id(
    *,
    items: list[JobDigestItem],
    api_base_url: str,
) -> dict[str, str]:
    urls: dict[str, str] = {}
    for item in items:
        generated_resume = item.generated_resume
        if generated_resume is None or not generated_resume.pdf_path:
            continue

        urls[str(generated_resume.id)] = (
            f"{api_base_url}/generated-resumes/{generated_resume.id}/download"
        )

    return urls
