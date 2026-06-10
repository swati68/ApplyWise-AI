from uuid import UUID

from app.core.config import Settings
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.services.email.gmail_email_service import GmailEmailService
from app.services.email.smtp_email_service import SmtpEmailService
from app.services.google_drive_service import GoogleDriveService
from app.services.google_oauth_credentials_service import (
    DRIVE_FILE_SCOPE,
    GoogleOAuthCredentialsService,
    GoogleUserCredentialsError,
)


def build_drive_service_for_user(
    *,
    settings: Settings,
    google_integration_repository: GoogleIntegrationRepository,
    user_id: UUID,
) -> GoogleDriveService | None:
    integration = google_integration_repository.get_by_user(user_id)
    if integration is None or not integration.drive_connected:
        return None

    try:
        credentials = GoogleOAuthCredentialsService(
            settings=settings,
            repository=google_integration_repository,
        ).get_credentials(
            user_id=user_id,
            required_scopes=[DRIVE_FILE_SCOPE],
        )
    except GoogleUserCredentialsError:
        return None

    return GoogleDriveService(
        settings,
        credentials=credentials,
        default_folder_id=integration.drive_folder_id,
    )


def build_email_service_for_user(
    *,
    settings: Settings,
    google_integration_repository: GoogleIntegrationRepository,
    user_id: UUID,
) -> GmailEmailService | SmtpEmailService:
    integration = google_integration_repository.get_by_user(user_id)
    if integration is not None and integration.gmail_send_connected:
        return GmailEmailService(
            settings=settings,
            google_integration_repository=google_integration_repository,
            user_id=user_id,
        )

    return SmtpEmailService(settings)
