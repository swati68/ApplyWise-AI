import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.schemas.google_integration import GoogleIntegrationStatusRead
from app.services.auth_service import GoogleOAuthError
from app.services.google_integration_service import GoogleIntegrationService


router = APIRouter(prefix="/integrations/google", tags=["google-integrations"])

GOOGLE_INTEGRATION_STATE_COOKIE_NAME = "applywise_google_integration_state"


def get_google_integration_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GoogleIntegrationService:
    return GoogleIntegrationService(
        settings=settings,
        repository=GoogleIntegrationRepository(db),
    )


@router.get("/status", response_model=GoogleIntegrationStatusRead)
def read_google_integration_status(
    current_user: User = Depends(get_current_user),
    service: GoogleIntegrationService = Depends(get_google_integration_service),
) -> GoogleIntegrationStatusRead:
    return GoogleIntegrationStatusRead.model_validate(
        service.get_status(current_user.id),
    )


@router.get("/connect")
def connect_google_services(
    current_user: User = Depends(get_current_user),
    service: GoogleIntegrationService = Depends(get_google_integration_service),
) -> RedirectResponse:
    _ = current_user
    state = secrets.token_urlsafe(32)
    try:
        authorization_url = service.build_connect_url(state)
    except GoogleOAuthError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    response = RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=GOOGLE_INTEGRATION_STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        max_age=10 * 60,
        path="/",
        samesite="lax",
        secure=False,
    )
    return response


@router.get("/callback")
def google_services_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    current_user: User = Depends(get_current_user),
    service: GoogleIntegrationService = Depends(get_google_integration_service),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    expected_state = request.cookies.get(GOOGLE_INTEGRATION_STATE_COOKIE_NAME)
    if (
        expected_state is None
        or state is None
        or not secrets.compare_digest(expected_state, state)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google integration OAuth state.",
        )
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google OAuth code.",
        )

    try:
        service.connect_with_code(user_id=current_user.id, code=code)
    except GoogleOAuthError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    response = RedirectResponse(
        f"{settings.frontend_url}/onboarding",
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie(GOOGLE_INTEGRATION_STATE_COOKIE_NAME, path="/")
    return response


@router.post("/disconnect", response_model=GoogleIntegrationStatusRead)
def disconnect_google_services(
    current_user: User = Depends(get_current_user),
    service: GoogleIntegrationService = Depends(get_google_integration_service),
) -> GoogleIntegrationStatusRead:
    service.disconnect(current_user.id)
    return GoogleIntegrationStatusRead.model_validate(
        service.get_status(current_user.id),
    )
