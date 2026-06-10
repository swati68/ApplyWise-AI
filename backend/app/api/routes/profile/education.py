from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.repositories.profile_repository import EducationRepository
from app.schemas.profile import EducationCreate, EducationRead, EducationUpdate

router = APIRouter(prefix="/profile/education", tags=["profile: education"])


@router.get("", response_model=list[EducationRead])
def list_education(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[EducationRead]:
    repository = EducationRepository(db)
    return repository.list_by_user(user_id)


@router.post(
    "",
    response_model=EducationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_education(
    payload: EducationCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> EducationRead:
    repository = EducationRepository(db)
    return repository.create(user_id, payload.model_dump())


@router.put("/{education_id}", response_model=EducationRead)
def update_education(
    education_id: UUID,
    payload: EducationUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> EducationRead:
    repository = EducationRepository(db)
    education = repository.get_for_user(user_id, education_id)
    if education is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education not found",
        )

    return repository.update(education, payload.model_dump(exclude_unset=True))


@router.delete("/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_education(
    education_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    repository = EducationRepository(db)
    education = repository.get_for_user(user_id, education_id)
    if education is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education not found",
        )

    repository.delete(education)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
