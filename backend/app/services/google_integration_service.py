from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

from app.core.config import Settings
from app.models.google_integration import GoogleIntegration
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.services.auth_service import GoogleOAuthError, request_json
from app.services.encryption_service import EncryptionService


IDENTITY_SCOPES = ["openid", "email", "profile"]
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
AUTOMATION_SCOPES = [DRIVE_FILE_SCOPE, GMAIL_SEND_SCOPE]


class GoogleIntegrationService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: GoogleIntegrationRepository,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.encryption_service = EncryptionService(settings.auth_secret_key)

    def get_status(self, user_id: UUID) -> dict[str, object]:
        integration = self.repository.get_by_user(user_id)
        if integration is None:
            return {
                "user_id": user_id,
                "google_sub": None,
                "email": None,
                "identity_connected": False,
                "drive_connected": False,
                "gmail_send_connected": False,
                "automation_ready": False,
                "granted_scopes": [],
                "drive_folder_id": None,
                "updated_at": None,
            }

        return status_from_integration(integration)

    def build_connect_url(self, state: str) -> str:
        if (
            self.settings.google_oauth_client_id == ""
            or self.settings.google_oauth_client_secret == ""
        ):
            raise GoogleOAuthError("Google OAuth is not configured.")

        query = urlencode(
            {
                "client_id": self.settings.google_oauth_client_id,
                "redirect_uri": self.settings.google_integration_redirect_uri,
                "response_type": "code",
                "scope": " ".join(AUTOMATION_SCOPES),
                "state": state,
                "access_type": "offline",
                "prompt": "consent",
                "include_granted_scopes": "true",
            }
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    def connect_with_code(self, *, user_id: UUID, code: str) -> GoogleIntegration:
        token_payload = self._exchange_google_code(code)
        access_token = _optional_string(token_payload.get("access_token"))
        refresh_token = _optional_string(token_payload.get("refresh_token"))
        expires_in = token_payload.get("expires_in")
        if access_token is None:
            raise GoogleOAuthError("Google did not return an access token.")

        granted_scopes = _scope_list(token_payload.get("scope"))
        if not granted_scopes:
            granted_scopes = self._fetch_access_token_scopes(access_token)
        if not granted_scopes:
            raise GoogleOAuthError("Google did not confirm the requested permissions.")

        integration = self.repository.get_by_user(user_id)
        if integration is None:
            raise GoogleOAuthError("Google identity must be connected before services.")

        next_scopes = _merge_scopes(
            _identity_scopes_from(integration.granted_scopes),
            granted_scopes,
        )
        values: dict[str, object] = {
            "drive_connected": DRIVE_FILE_SCOPE in granted_scopes,
            "gmail_send_connected": GMAIL_SEND_SCOPE in granted_scopes,
            "granted_scopes": next_scopes,
            "access_token": self.encryption_service.encrypt(access_token),
        }
        if refresh_token is not None:
            values["refresh_token"] = self.encryption_service.encrypt(refresh_token)
        if isinstance(expires_in, int):
            values["token_expiry"] = datetime.now(UTC) + timedelta(seconds=expires_in)

        return self.repository.update(integration, values)

    def disconnect(self, user_id: UUID) -> GoogleIntegration | None:
        integration = self.repository.get_by_user(user_id)
        if integration is None:
            return None

        identity_scopes = [
            scope for scope in integration.granted_scopes if scope in IDENTITY_SCOPES
        ]
        return self.repository.update(
            integration,
            {
                "drive_connected": False,
                "gmail_send_connected": False,
                "access_token": None,
                "refresh_token": None,
                "token_expiry": None,
                "granted_scopes": identity_scopes,
                "drive_folder_id": None,
            },
        )

    def _exchange_google_code(self, code: str) -> dict[str, object]:
        payload = urlencode(
            {
                "code": code,
                "client_id": self.settings.google_oauth_client_id,
                "client_secret": self.settings.google_oauth_client_secret,
                "redirect_uri": self.settings.google_integration_redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        from urllib.request import Request

        request = Request(
            "https://oauth2.googleapis.com/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        return request_json(request)

    def _fetch_access_token_scopes(self, access_token: str) -> list[str]:
        from urllib.request import Request

        request = Request(
            f"https://oauth2.googleapis.com/tokeninfo?{urlencode({'access_token': access_token})}",
            method="GET",
        )
        return _scope_list(request_json(request).get("scope"))


def status_from_integration(integration: GoogleIntegration) -> dict[str, object]:
    # TODO: include profile completion and default template checks in readiness.
    automation_ready = (
        integration.identity_connected
        and integration.drive_connected
        and integration.gmail_send_connected
    )
    return {
        "user_id": integration.user_id,
        "google_sub": integration.google_sub,
        "email": integration.email,
        "identity_connected": integration.identity_connected,
        "drive_connected": integration.drive_connected,
        "gmail_send_connected": integration.gmail_send_connected,
        "automation_ready": automation_ready,
        "granted_scopes": integration.granted_scopes,
        "drive_folder_id": integration.drive_folder_id,
        "updated_at": integration.updated_at,
    }


def _scope_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [scope for scope in value.split() if scope]
    if isinstance(value, list):
        return [str(scope) for scope in value if str(scope).strip()]

    return []


def _merge_scopes(current_scopes: list[str], next_scopes: list[str]) -> list[str]:
    merged_scopes: list[str] = []
    seen_scopes: set[str] = set()
    for scope in [*current_scopes, *next_scopes]:
        if scope in seen_scopes:
            continue
        merged_scopes.append(scope)
        seen_scopes.add(scope)

    return merged_scopes


def _identity_scopes_from(scopes: list[str]) -> list[str]:
    return [
        scope
        for scope in scopes
        if scope in IDENTITY_SCOPES
        or scope
        in {
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        }
    ]


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value != "" else None
