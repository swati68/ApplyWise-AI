from datetime import UTC
from uuid import UUID

from app.core.config import Settings
from app.models.google_integration import GoogleIntegration
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.services.encryption_service import EncryptionService


GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


class GoogleUserCredentialsError(Exception):
    pass


class GoogleOAuthCredentialsService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: GoogleIntegrationRepository,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.encryption_service = EncryptionService(settings.auth_secret_key)

    def get_credentials(
        self,
        *,
        user_id: UUID,
        required_scopes: list[str],
    ) -> object:
        integration = self.repository.get_by_user(user_id)
        if integration is None:
            raise GoogleUserCredentialsError("Google services are not connected.")

        self._validate_integration(integration, required_scopes)
        access_token = self.encryption_service.decrypt(integration.access_token)
        refresh_token = self.encryption_service.decrypt(integration.refresh_token)
        if access_token is None and refresh_token is None:
            raise GoogleUserCredentialsError("Google tokens are missing. Reconnect Google services.")

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
        except ImportError as error:
            raise GoogleUserCredentialsError(
                "Google OAuth dependencies are not installed. Run `pip install -r requirements.txt`.",
            ) from error

        expiry = integration.token_expiry
        if expiry is not None and expiry.tzinfo is not None:
            expiry = expiry.astimezone(UTC).replace(tzinfo=None)

        credentials = Credentials(
            token=None if refresh_token is not None else access_token,
            refresh_token=refresh_token,
            token_uri=GOOGLE_TOKEN_URI,
            client_id=self.settings.google_oauth_client_id,
            client_secret=self.settings.google_oauth_client_secret,
            scopes=required_scopes,
        )
        credentials.expiry = expiry

        if refresh_token is None:
            if credentials.valid:
                return credentials
            raise GoogleUserCredentialsError("Google refresh token is missing. Reconnect Google services.")

        try:
            credentials.refresh(Request())
        except Exception as error:
            raise GoogleUserCredentialsError(
                "Google token refresh failed. Reconnect Google services.",
            ) from error

        self.repository.update(
            integration,
            {
                "access_token": self.encryption_service.encrypt(credentials.token),
                "token_expiry": (
                    credentials.expiry.replace(tzinfo=UTC)
                    if credentials.expiry is not None
                    else None
                ),
            },
        )
        return credentials

    def _validate_integration(
        self,
        integration: GoogleIntegration,
        required_scopes: list[str],
    ) -> None:
        missing_scopes = [
            scope for scope in required_scopes if scope not in integration.granted_scopes
        ]
        if missing_scopes:
            raise GoogleUserCredentialsError("Required Google permissions are not connected.")

        if DRIVE_FILE_SCOPE in required_scopes and not integration.drive_connected:
            raise GoogleUserCredentialsError("Google Drive is not connected.")
        if GMAIL_SEND_SCOPE in required_scopes and not integration.gmail_send_connected:
            raise GoogleUserCredentialsError("Gmail is not connected.")
