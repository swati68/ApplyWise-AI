from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.repositories.profile_repository import ProjectRepository
from app.schemas.profile import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/profile/projects", tags=["profile: projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[ProjectRead]:
    repository = ProjectRepository(db)
    return repository.list_by_user(user_id)


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ProjectRead:
    repository = ProjectRepository(db)
    return repository.create(user_id, payload.model_dump())


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ProjectRead:
    repository = ProjectRepository(db)
    project = repository.get_for_user(user_id, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return repository.update(project, payload.model_dump(exclude_unset=True))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    repository = ProjectRepository(db)
    project = repository.get_for_user(user_id, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    repository.delete(project)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
