from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.repositories.profile_repository import SkillRepository
from app.schemas.profile import SkillCreate, SkillRead, SkillUpdate

router = APIRouter(prefix="/profile/skills", tags=["profile: skills"])


@router.get("", response_model=list[SkillRead])
def list_skills(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[SkillRead]:
    repository = SkillRepository(db)
    return repository.list_by_user(user_id)


@router.post(
    "",
    response_model=SkillRead,
    status_code=status.HTTP_201_CREATED,
)
def create_skill(
    payload: SkillCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> SkillRead:
    repository = SkillRepository(db)
    return repository.create(user_id, payload.model_dump())


@router.put("/{skill_id}", response_model=SkillRead)
def update_skill(
    skill_id: UUID,
    payload: SkillUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> SkillRead:
    repository = SkillRepository(db)
    skill = repository.get_for_user(user_id, skill_id)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )

    return repository.update(skill, payload.model_dump(exclude_unset=True))


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    repository = SkillRepository(db)
    skill = repository.get_for_user(user_id, skill_id)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )

    repository.delete(skill)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
