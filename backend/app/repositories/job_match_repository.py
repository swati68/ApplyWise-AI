from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.experience import Experience
from app.models.job_match import JobMatch
from app.models.project import Project
from app.models.skill import Skill


class JobMatchRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_latest_for_job(self, user_id: UUID, job_id: UUID) -> JobMatch | None:
        statement = (
            select(JobMatch)
            .where(JobMatch.user_id == user_id, JobMatch.job_id == job_id)
            .order_by(JobMatch.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def list_user_skills(self, user_id: UUID) -> list[Skill]:
        statement = select(Skill).where(Skill.user_id == user_id).order_by(Skill.name)
        return list(self.db.scalars(statement))

    def list_user_experiences(self, user_id: UUID) -> list[Experience]:
        statement = (
            select(Experience)
            .where(Experience.user_id == user_id)
            .order_by(Experience.start_date.desc().nullslast(), Experience.company)
        )
        return list(self.db.scalars(statement))

    def list_user_projects(self, user_id: UUID) -> list[Project]:
        statement = select(Project).where(Project.user_id == user_id).order_by(Project.name)
        return list(self.db.scalars(statement))

    def create(self, values: dict[str, object]) -> JobMatch:
        match = JobMatch(**values)
        self.db.add(match)
        self.db.commit()
        self.db.refresh(match)
        return match
