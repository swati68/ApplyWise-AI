from email.message import EmailMessage
import base64
from uuid import UUID

from app.core.config import Settings
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.services.email.smtp_email_service import EmailConfigurationError, EmailSendError
from app.services.google_oauth_credentials_service import (
    GMAIL_SEND_SCOPE,
    GoogleOAuthCredentialsService,
    GoogleUserCredentialsError,
)


class GmailEmailService:
    def __init__(
        self,
        *,
        settings: Settings,
        google_integration_repository: GoogleIntegrationRepository,
        user_id: UUID,
    ) -> None:
        self.settings = settings
        self.google_integration_repository = google_integration_repository
        self.user_id = user_id

    def send_html_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = to_email
        message["To"] = to_email
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        try:
            service = self._gmail_client()
            service.users().messages().send(
                userId="me",
                body={"raw": raw_message},
            ).execute()
        except GoogleUserCredentialsError as error:
            raise EmailConfigurationError(str(error)) from error
        except Exception as error:
            if _is_insufficient_google_permission_error(error):
                self._mark_gmail_disconnected()
                raise EmailConfigurationError(
                    "Gmail send permission is missing. Reconnect Google services from Settings.",
                ) from error
            raise EmailSendError(f"Gmail send failed: {error}") from error

    def _gmail_client(self) -> object:
        try:
            from googleapiclient.discovery import build
        except ImportError as error:
            raise EmailConfigurationError(
                "Google API dependencies are not installed. Run `pip install -r requirements.txt`.",
            ) from error

        credentials = GoogleOAuthCredentialsService(
            settings=self.settings,
            repository=self.google_integration_repository,
        ).get_credentials(
            user_id=self.user_id,
            required_scopes=[GMAIL_SEND_SCOPE],
        )
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def _mark_gmail_disconnected(self) -> None:
        integration = self.google_integration_repository.get_by_user(self.user_id)
        if integration is None:
            return

        self.google_integration_repository.update(
            integration,
            {
                "gmail_send_connected": False,
                "access_token": None,
                "granted_scopes": [
                    scope
                    for scope in integration.granted_scopes
                    if scope != GMAIL_SEND_SCOPE
                ],
            },
        )


def _is_insufficient_google_permission_error(error: Exception) -> bool:
    response = getattr(error, "resp", None)
    status = getattr(response, "status", None)
    content = getattr(error, "content", b"")
    if isinstance(content, bytes):
        content_text = content.decode("utf-8", errors="ignore")
    else:
        content_text = str(content)

    message = f"{error} {content_text}".casefold()
    return status == 403 and (
        "insufficient authentication scopes" in message
        or "insufficientpermissions" in message
        or "insufficient permission" in message
    )
