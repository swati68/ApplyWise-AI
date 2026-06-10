from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.repositories.profile_repository import ExperienceRepository
from app.schemas.profile import ExperienceCreate, ExperienceRead, ExperienceUpdate

router = APIRouter(prefix="/profile/experience", tags=["profile: experience"])


@router.get("", response_model=list[ExperienceRead])
def list_experience(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[ExperienceRead]:
    repository = ExperienceRepository(db)
    return repository.list_by_user(user_id)


@router.post(
    "",
    response_model=ExperienceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_experience(
    payload: ExperienceCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ExperienceRead:
    repository = ExperienceRepository(db)
    return repository.create(user_id, payload.model_dump())


@router.put("/{experience_id}", response_model=ExperienceRead)
def update_experience(
    experience_id: UUID,
    payload: ExperienceUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ExperienceRead:
    repository = ExperienceRepository(db)
    experience = repository.get_for_user(user_id, experience_id)
    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found",
        )

    return repository.update(experience, payload.model_dump(exclude_unset=True))


@router.delete("/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experience(
    experience_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    repository = ExperienceRepository(db)
    experience = repository.get_for_user(user_id, experience_id)
    if experience is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found",
        )

    repository.delete(experience)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
