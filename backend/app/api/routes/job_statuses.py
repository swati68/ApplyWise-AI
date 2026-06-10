from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.repositories.job_posting_repository import JobPostingRepository
from app.repositories.job_status_history_repository import JobStatusHistoryRepository
from app.repositories.job_status_repository import JobStatusRepository
from app.schemas.job_status import JobStatusCreate, JobStatusRead, JobStatusUpdate
from app.services.job_status_service import JobStatusService

router = APIRouter(prefix="/job-statuses", tags=["job statuses"])


@router.get("", response_model=list[JobStatusRead])
def list_job_statuses(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[JobStatusRead]:
    service = _status_service(db)
    return service.ensure_default_statuses(user_id)


@router.post("", response_model=JobStatusRead, status_code=status.HTTP_201_CREATED)
def create_job_status(
    payload: JobStatusCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobStatusRead:
    repository = JobStatusRepository(db)
    existing_status = repository.find_by_name(user_id, payload.name)
    if existing_status is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A job status with this name already exists.",
        )

    return repository.create(user_id, payload.model_dump())


@router.put("/{status_id}", response_model=JobStatusRead)
def update_job_status(
    status_id: UUID,
    payload: JobStatusUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobStatusRead:
    repository = JobStatusRepository(db)
    job_status = repository.get_for_user(user_id, status_id)
    if job_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job status not found.",
        )

    values = payload.model_dump(exclude_unset=True)
    next_name = values.get("name")
    if isinstance(next_name, str):
        existing_status = repository.find_by_name(user_id, next_name)
        if existing_status is not None and existing_status.id != status_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A job status with this name already exists.",
            )

    return repository.update(job_status, values)


@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_status(
    status_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    repository = JobStatusRepository(db)
    job_status = repository.get_for_user(user_id, status_id)
    if job_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job status not found.",
        )

    try:
        repository.delete(job_status)
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This status is used by jobs or status history and cannot be deleted.",
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _status_service(db: Session) -> JobStatusService:
    return JobStatusService(
        status_repository=JobStatusRepository(db),
        history_repository=JobStatusHistoryRepository(db),
        job_repository=JobPostingRepository(db),
    )
