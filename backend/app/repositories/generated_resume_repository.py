from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.generated_resume import GeneratedResume


class GeneratedResumeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, object]) -> GeneratedResume:
        generated_resume = GeneratedResume(**values)
        self.db.add(generated_resume)
        self.db.commit()
        self.db.refresh(generated_resume)
        return generated_resume

    def get_for_user(self, user_id: UUID, resume_id: UUID) -> GeneratedResume | None:
        statement = select(GeneratedResume).where(
            GeneratedResume.user_id == user_id,
            GeneratedResume.id == resume_id,
        )
        return self.db.scalar(statement)

    def get_latest_for_job(
        self,
        user_id: UUID,
        job_id: UUID,
    ) -> GeneratedResume | None:
        statement = (
            select(GeneratedResume)
            .where(
                GeneratedResume.user_id == user_id,
                GeneratedResume.job_id == job_id,
            )
            .order_by(GeneratedResume.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def update(
        self,
        generated_resume: GeneratedResume,
        values: dict[str, object],
    ) -> GeneratedResume:
        for field, value in values.items():
            setattr(generated_resume, field, value)

        self.db.commit()
        self.db.refresh(generated_resume)
        return generated_resume
