from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.scheduler import SchedulerTriggerType
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.repositories.scheduler_repository import (
    SchedulerRunRepository,
    UserSchedulerPreferenceRepository,
)
from app.schemas.scheduler import (
    SchedulerPreferenceRead,
    SchedulerPreferenceUpdate,
    SchedulerRunRead,
)
from app.services.google_integration_service import GoogleIntegrationService
from app.services.scheduler_service import (
    SchedulerAutomationService,
    SchedulerNotReadyError,
    SchedulerRunAlreadyInProgressError,
    calculate_next_run_at,
)


router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/preferences", response_model=SchedulerPreferenceRead)
def read_scheduler_preferences(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> SchedulerPreferenceRead:
    preference = UserSchedulerPreferenceRepository(db).get_or_create_for_user(user_id)
    return _preference_read(preference)


@router.put("/preferences", response_model=SchedulerPreferenceRead)
def update_scheduler_preferences(
    payload: SchedulerPreferenceUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
) -> SchedulerPreferenceRead:
    if payload.enabled:
        integration_status = GoogleIntegrationService(
            settings=settings,
            repository=GoogleIntegrationRepository(db),
        ).get_status(user_id)
        if not (
            bool(integration_status["drive_connected"])
            and bool(integration_status["gmail_send_connected"])
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Connect Google Drive and Gmail permissions before enabling automation.",
            )

    repository = UserSchedulerPreferenceRepository(db)
    preference = repository.get_or_create_for_user(user_id)
    updated_preference = repository.update(preference, payload.model_dump())
    return _preference_read(updated_preference)


@router.get("/runs", response_model=list[SchedulerRunRead])
def list_scheduler_runs(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[SchedulerRunRead]:
    return SchedulerRunRepository(db).list_recent_by_user(user_id)


@router.post("/run-now", response_model=SchedulerRunRead)
def run_scheduler_now(
    request: Request,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
) -> SchedulerRunRead:
    service = SchedulerAutomationService(
        db=db,
        settings=settings,
        api_base_url=f"{str(request.base_url).rstrip('/')}{settings.api_prefix}",
    )
    try:
        return service.run_for_user(
            user_id=user_id,
            trigger_type=SchedulerTriggerType.MANUAL,
        )
    except SchedulerRunAlreadyInProgressError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except SchedulerNotReadyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


def _preference_read(preference) -> SchedulerPreferenceRead:
    preference_read = SchedulerPreferenceRead.model_validate(preference)
    preference_read.next_run_at = calculate_next_run_at(preference)
    return preference_read
