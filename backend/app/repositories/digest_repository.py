from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.generated_resume import GeneratedResume
from app.models.job_match import JobMatch
from app.models.job_posting import JobPosting


@dataclass(frozen=True)
class JobDigestItem:
    job: JobPosting
    match: JobMatch
    generated_resume: GeneratedResume | None


class DigestRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_latest_matched_jobs(self, user_id: UUID) -> list[JobDigestItem]:
        generated_resumes_by_job_id = self._latest_generated_resumes_by_job_id(user_id)
        statement = (
            select(JobMatch, JobPosting)
            .join(JobPosting, JobPosting.id == JobMatch.job_id)
            .where(JobMatch.user_id == user_id)
            .order_by(JobMatch.created_at.desc())
        )
        seen_job_ids: set[UUID] = set()
        items: list[JobDigestItem] = []
        for match, job in self.db.execute(statement):
            if job.id in seen_job_ids:
                continue

            seen_job_ids.add(job.id)
            items.append(
                JobDigestItem(
                    job=job,
                    match=match,
                    generated_resume=generated_resumes_by_job_id.get(job.id),
                )
            )

        return items

    def _latest_generated_resumes_by_job_id(
        self,
        user_id: UUID,
    ) -> dict[UUID, GeneratedResume]:
        statement = (
            select(GeneratedResume)
            .where(GeneratedResume.user_id == user_id)
            .order_by(GeneratedResume.created_at.desc())
        )
        resumes_by_job_id: dict[UUID, GeneratedResume] = {}
        for generated_resume in self.db.scalars(statement):
            if generated_resume.job_id not in resumes_by_job_id:
                resumes_by_job_id[generated_resume.job_id] = generated_resume

        return resumes_by_job_id
