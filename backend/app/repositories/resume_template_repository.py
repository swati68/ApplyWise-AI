from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.resume_template import ResumeTemplate


class ResumeTemplateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: UUID) -> list[ResumeTemplate]:
        statement = (
            select(ResumeTemplate)
            .where(ResumeTemplate.user_id == user_id)
            .order_by(ResumeTemplate.is_default.desc(), ResumeTemplate.updated_at.desc())
        )
        return list(self.db.scalars(statement))

    def get_for_user(
        self,
        user_id: UUID,
        template_id: UUID,
    ) -> ResumeTemplate | None:
        statement = select(ResumeTemplate).where(
            ResumeTemplate.user_id == user_id,
            ResumeTemplate.id == template_id,
        )
        return self.db.scalar(statement)

    def get_default_for_user(self, user_id: UUID) -> ResumeTemplate | None:
        statement = select(ResumeTemplate).where(
            ResumeTemplate.user_id == user_id,
            ResumeTemplate.is_default.is_(True),
        )
        return self.db.scalar(statement)

    def create(self, user_id: UUID, values: dict[str, object]) -> ResumeTemplate:
        if values.get("is_default") is True:
            self._unset_user_defaults(user_id)

        template = ResumeTemplate(user_id=user_id, **values)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def update(
        self,
        template: ResumeTemplate,
        values: dict[str, object],
    ) -> ResumeTemplate:
        if values.get("is_default") is True:
            self._unset_user_defaults(template.user_id)

        for field, value in values.items():
            setattr(template, field, value)

        self.db.commit()
        self.db.refresh(template)
        return template

    def delete(self, template: ResumeTemplate) -> None:
        self.db.delete(template)
        self.db.commit()

    def set_default(self, template: ResumeTemplate) -> ResumeTemplate:
        self._unset_user_defaults(template.user_id)
        template.is_default = True
        self.db.commit()
        self.db.refresh(template)
        return template

    def _unset_user_defaults(self, user_id: UUID) -> None:
        statement = (
            update(ResumeTemplate)
            .where(ResumeTemplate.user_id == user_id)
            .values(is_default=False)
        )
        self.db.execute(statement)
