from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_status_history import JobStatusHistory


class JobStatusHistoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_job(self, user_id: UUID, job_id: UUID) -> list[JobStatusHistory]:
        statement = (
            select(JobStatusHistory)
            .where(
                JobStatusHistory.user_id == user_id,
                JobStatusHistory.job_id == job_id,
            )
            .order_by(JobStatusHistory.changed_at.desc())
        )
        return list(self.db.scalars(statement))

    def create(self, values: dict[str, object]) -> JobStatusHistory:
        history = JobStatusHistory(**values)
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history
