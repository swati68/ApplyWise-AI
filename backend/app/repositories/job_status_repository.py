from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job_status import JobStatus


class JobStatusRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: UUID) -> list[JobStatus]:
        statement = (
            select(JobStatus)
            .where(JobStatus.user_id == user_id)
            .order_by(JobStatus.sort_order, JobStatus.name)
        )
        return list(self.db.scalars(statement))

    def get_for_user(self, user_id: UUID, status_id: UUID) -> JobStatus | None:
        statement = select(JobStatus).where(
            JobStatus.user_id == user_id,
            JobStatus.id == status_id,
        )
        return self.db.scalar(statement)

    def find_by_name(self, user_id: UUID, name: str) -> JobStatus | None:
        statement = select(JobStatus).where(
            JobStatus.user_id == user_id,
            func.lower(JobStatus.name) == name.strip().lower(),
        )
        return self.db.scalar(statement)

    def create(self, user_id: UUID, values: dict[str, object]) -> JobStatus:
        status = JobStatus(user_id=user_id, **values)
        self.db.add(status)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise

        self.db.refresh(status)
        return status

    def update(self, status: JobStatus, values: dict[str, object]) -> JobStatus:
        for field, value in values.items():
            setattr(status, field, value)

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise

        self.db.refresh(status)
        return status

    def delete(self, status: JobStatus) -> None:
        self.db.delete(status)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
