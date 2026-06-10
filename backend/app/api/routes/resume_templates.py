from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.repositories.resume_template_repository import ResumeTemplateRepository
from app.schemas.resume_template import (
    ResumeTemplateCreate,
    ResumeTemplateRead,
    ResumeTemplateUpdate,
)

router = APIRouter(prefix="/resume-templates", tags=["resume templates"])


@router.get("", response_model=list[ResumeTemplateRead])
def list_resume_templates(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[ResumeTemplateRead]:
    repository = ResumeTemplateRepository(db)
    return repository.list_by_user(user_id)


@router.post(
    "",
    response_model=ResumeTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_resume_template(
    payload: ResumeTemplateCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ResumeTemplateRead:
    repository = ResumeTemplateRepository(db)
    return repository.create(user_id, payload.model_dump())


@router.get("/{template_id}", response_model=ResumeTemplateRead)
def get_resume_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ResumeTemplateRead:
    repository = ResumeTemplateRepository(db)
    template = repository.get_for_user(user_id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume template not found",
        )

    return template


@router.put("/{template_id}", response_model=ResumeTemplateRead)
def update_resume_template(
    template_id: UUID,
    payload: ResumeTemplateUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ResumeTemplateRead:
    repository = ResumeTemplateRepository(db)
    template = repository.get_for_user(user_id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume template not found",
        )

    return repository.update(template, payload.model_dump(exclude_unset=True))


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    repository = ResumeTemplateRepository(db)
    template = repository.get_for_user(user_id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume template not found",
        )

    repository.delete(template)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{template_id}/set-default", response_model=ResumeTemplateRead)
def set_default_resume_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ResumeTemplateRead:
    repository = ResumeTemplateRepository(db)
    template = repository.get_for_user(user_id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume template not found",
        )

    return repository.set_default(template)
