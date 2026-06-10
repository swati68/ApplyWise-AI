import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.repositories.job_status_history_repository import JobStatusHistoryRepository
from app.repositories.job_status_repository import JobStatusRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import AuthUserRead, UserRead
from app.services.auth_service import (
    AuthService,
    GoogleOAuthError,
    GoogleOAuthNotConfiguredError,
)
from app.services.google_integration_service import status_from_integration
from app.services.job_status_service import JobStatusService

router = APIRouter(prefix="/auth", tags=["auth"])

OAUTH_STATE_COOKIE_NAME = "applywise_oauth_state"


def get_auth_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        settings=settings,
        user_repository=UserRepository(db),
        google_integration_repository=GoogleIntegrationRepository(db),
    )


def set_session_cookie(
    *,
    response: Response,
    settings: Settings,
    token: str,
) -> None:
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=token,
        httponly=True,
        max_age=settings.auth_session_days * 24 * 60 * 60,
        path="/",
        samesite="lax",
        secure=False,
    )


def clear_session_cookie(*, response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_session_cookie_name,
        httponly=True,
        path="/",
        samesite="lax",
        secure=False,
    )


@router.post("/signup", status_code=status.HTTP_410_GONE)
def signup() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Email/password signup has been removed. Continue with Google.",
    )


@router.post("/login", status_code=status.HTTP_410_GONE)
def login() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Email/password login has been removed. Continue with Google.",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> Response:
    clear_session_cookie(response=response, settings=settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AuthUserRead)
def read_auth_user(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuthUserRead:
    return _build_auth_user_read(user=user, db=db)


@router.get("/google/login")
def google_login(
    auth_service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    try:
        authorization_url = auth_service.build_google_authorization_url(state)
    except GoogleOAuthNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    response = RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        max_age=10 * 60,
        path="/",
        samesite="lax",
        secure=False,
    )
    return response


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    expected_state = request.cookies.get(OAUTH_STATE_COOKIE_NAME)
    if (
        expected_state is None
        or state is None
        or not secrets.compare_digest(expected_state, state)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google OAuth state.",
        )
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google OAuth code.",
        )

    try:
        user = auth_service.login_with_google_code(code)
    except GoogleOAuthError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    JobStatusService(
        status_repository=JobStatusRepository(db),
        history_repository=JobStatusHistoryRepository(db),
    ).ensure_default_statuses(user.id)
    auth_user = _build_auth_user_read(user=user, db=db)
    redirect_path = "/dashboard" if auth_user.automation_ready else "/onboarding"

    response = RedirectResponse(
        f"{settings.frontend_url}{redirect_path}",
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/")
    set_session_cookie(
        response=response,
        settings=settings,
        token=auth_service.create_session_token(user),
    )
    return response


def _build_auth_user_read(*, user: User, db: Session) -> AuthUserRead:
    user_data = UserRead.model_validate(user).model_dump()
    integration = GoogleIntegrationRepository(db).get_by_user(user.id)
    if integration is None:
        integration_status = {
            "identity_connected": False,
            "drive_connected": False,
            "gmail_send_connected": False,
            "automation_ready": False,
        }
    else:
        integration_status = status_from_integration(integration)

    return AuthUserRead.model_validate(
        {
            **user_data,
            "identity_connected": bool(integration_status["identity_connected"]),
            "drive_connected": bool(integration_status["drive_connected"]),
            "gmail_send_connected": bool(integration_status["gmail_send_connected"]),
            "automation_ready": bool(integration_status["automation_ready"]),
        }
    )
