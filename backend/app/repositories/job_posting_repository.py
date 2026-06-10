from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_posting import JobPosting


class JobPostingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: UUID) -> list[JobPosting]:
        statement = (
            select(JobPosting)
            .where(JobPosting.user_id == user_id)
            .order_by(JobPosting.discovered_at.desc(), JobPosting.company, JobPosting.title)
        )
        return list(self.db.scalars(statement))

    def get_for_user(self, user_id: UUID, job_id: UUID) -> JobPosting | None:
        statement = select(JobPosting).where(
            JobPosting.user_id == user_id,
            JobPosting.id == job_id,
        )
        return self.db.scalar(statement)

    def find_by_job_url(
        self,
        *,
        user_id: UUID,
        job_url: str,
        exclude_job_id: UUID | None = None,
    ) -> JobPosting | None:
        statement = select(JobPosting).where(
            JobPosting.user_id == user_id,
            JobPosting.job_url == job_url,
        )
        if exclude_job_id is not None:
            statement = statement.where(JobPosting.id != exclude_job_id)

        return self.db.scalar(statement)

    def find_by_content_hash(
        self,
        *,
        user_id: UUID,
        content_hash: str,
        exclude_job_id: UUID | None = None,
    ) -> JobPosting | None:
        statement = select(JobPosting).where(
            JobPosting.user_id == user_id,
            JobPosting.content_hash == content_hash,
        )
        if exclude_job_id is not None:
            statement = statement.where(JobPosting.id != exclude_job_id)

        return self.db.scalar(statement)

    def create(self, values: dict[str, object]) -> JobPosting:
        job = JobPosting(**values)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def update(self, job: JobPosting, values: dict[str, object]) -> JobPosting:
        for field, value in values.items():
            setattr(job, field, value)

        self.db.commit()
        self.db.refresh(job)
        return job

    def delete(self, job: JobPosting) -> None:
        self.db.delete(job)
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
