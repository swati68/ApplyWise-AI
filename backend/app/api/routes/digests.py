from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.digest_repository import DigestRepository
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.schemas.digest import DigestSendResponse
from app.services.digest_service import DigestService
from app.services.google_user_services import build_email_service_for_user


router = APIRouter(prefix="/digests", tags=["digests"])


@router.post("/send", response_model=DigestSendResponse)
def send_digest(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DigestSendResponse:
    api_base_url = f"{str(request.base_url).rstrip('/')}{settings.api_prefix}"
    result = DigestService(
        repository=DigestRepository(db),
        email_service=build_email_service_for_user(
            settings=settings,
            google_integration_repository=GoogleIntegrationRepository(db),
            user_id=current_user.id,
        ),
        api_base_url=api_base_url,
    ).send_digest(user=current_user)

    return DigestSendResponse(
        success=result.success,
        recipient_email=result.recipient_email,
        item_count=result.item_count,
        sent_at=result.sent_at,
        error_message=result.error_message,
    )
