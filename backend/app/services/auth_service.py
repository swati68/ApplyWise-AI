import json
from datetime import timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import Settings
from app.core.security import create_session_token, hash_password, verify_password
from app.models.user import User
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.repositories.user_repository import UserRepository

IDENTITY_SCOPES = ["openid", "email", "profile"]


class AuthError(Exception):
    pass


class EmailAlreadyRegisteredError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class GoogleOAuthNotConfiguredError(AuthError):
    pass


class GoogleOAuthError(AuthError):
    pass


class AuthService:
    def __init__(
        self,
        *,
        settings: Settings,
        user_repository: UserRepository,
        google_integration_repository: GoogleIntegrationRepository | None = None,
    ) -> None:
        self.settings = settings
        self.user_repository = user_repository
        self.google_integration_repository = google_integration_repository

    def signup_with_email(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None,
    ) -> User:
        if self.user_repository.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError("Email is already registered.")

        return self.user_repository.create(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
        )

    def login_with_email(self, *, email: str, password: str) -> User:
        user = self.user_repository.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")

        return user

    def create_session_token(self, user: User) -> str:
        return create_session_token(
            user_id=user.id,
            secret_key=self.settings.auth_secret_key,
            expires_delta=timedelta(days=self.settings.auth_session_days),
        )

    def build_google_authorization_url(self, state: str) -> str:
        if (
            self.settings.google_oauth_client_id == ""
            or self.settings.google_oauth_client_secret == ""
        ):
            raise GoogleOAuthNotConfiguredError("Google OAuth is not configured.")

        query = urlencode(
            {
                "client_id": self.settings.google_oauth_client_id,
                "redirect_uri": self.settings.google_oauth_redirect_uri,
                "response_type": "code",
                "scope": " ".join(IDENTITY_SCOPES),
                "state": state,
                "prompt": "select_account",
            }
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    def login_with_google_code(self, code: str) -> User:
        token_payload = self._exchange_google_code(code)
        access_token = token_payload.get("access_token")
        if not isinstance(access_token, str):
            raise GoogleOAuthError("Google did not return an access token.")

        profile = self._fetch_google_profile(access_token)
        google_sub = _require_string(profile, "sub")
        email = _require_string(profile, "email").lower()
        email_verified = profile.get("email_verified")
        full_name = profile.get("name")

        if email_verified is not True and email_verified != "true":
            raise GoogleOAuthError("Google email is not verified.")

        user = self.user_repository.get_by_google_sub(google_sub)
        if user is not None:
            updated_user = self.user_repository.update(
                user,
                {
                    "email": email,
                    "full_name": full_name if isinstance(full_name, str) else user.full_name,
                    "avatar_url": None,
                },
            )
            self._record_google_identity(
                user=updated_user,
                google_sub=google_sub,
                email=email,
                granted_scopes=_scope_list(token_payload.get("scope")),
            )
            return updated_user

        user = self.user_repository.get_by_email(email)
        if user is not None:
            updated_user = self.user_repository.update(
                user,
                {
                    "google_sub": google_sub,
                    "full_name": full_name if isinstance(full_name, str) else user.full_name,
                    "avatar_url": None,
                },
            )
            self._record_google_identity(
                user=updated_user,
                google_sub=google_sub,
                email=email,
                granted_scopes=_scope_list(token_payload.get("scope")),
            )
            return updated_user

        user = self.user_repository.create(
            email=email,
            google_sub=google_sub,
            full_name=full_name if isinstance(full_name, str) else None,
            avatar_url=None,
        )
        self._record_google_identity(
            user=user,
            google_sub=google_sub,
            email=email,
            granted_scopes=_scope_list(token_payload.get("scope")),
        )
        return user

    def _exchange_google_code(self, code: str) -> dict[str, object]:
        payload = urlencode(
            {
                "code": code,
                "client_id": self.settings.google_oauth_client_id,
                "client_secret": self.settings.google_oauth_client_secret,
                "redirect_uri": self.settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        request = Request(
            "https://oauth2.googleapis.com/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        return request_json(request)

    def _fetch_google_profile(self, access_token: str) -> dict[str, object]:
        request = Request(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )
        return request_json(request)

    def _record_google_identity(
        self,
        *,
        user: User,
        google_sub: str,
        email: str,
        granted_scopes: list[str],
    ) -> None:
        if self.google_integration_repository is None:
            return

        integration = self.google_integration_repository.get_by_user(user.id)
        next_scopes = _merge_scopes(
            integration.granted_scopes if integration is not None else [],
            [*IDENTITY_SCOPES, *granted_scopes],
        )
        self.google_integration_repository.upsert_for_user(
            user_id=user.id,
            values={
                "google_sub": google_sub,
                "email": email,
                "identity_connected": True,
                "granted_scopes": next_scopes,
            },
        )


def request_json(request: Request) -> dict[str, object]:
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
    except Exception as error:
        raise GoogleOAuthError("Google OAuth request failed.") from error

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise GoogleOAuthError("Google returned an invalid response.") from error

    if not isinstance(payload, dict):
        raise GoogleOAuthError("Google returned an invalid response.")

    if "error" in payload:
        raise GoogleOAuthError("Google OAuth request was rejected.")

    return payload


def _require_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value == "":
        raise GoogleOAuthError(f"Google profile is missing {key}.")

    return value


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
