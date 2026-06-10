from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.education import Education
from app.models.experience import Experience
from app.models.project import Project
from app.models.skill import Skill


class EducationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: UUID) -> list[Education]:
        statement = (
            select(Education)
            .where(Education.user_id == user_id)
            .order_by(Education.start_date.desc().nullslast(), Education.institution)
        )
        return list(self.db.scalars(statement))

    def get_for_user(self, user_id: UUID, education_id: UUID) -> Education | None:
        statement = select(Education).where(
            Education.user_id == user_id,
            Education.id == education_id,
        )
        return self.db.scalar(statement)

    def create(self, user_id: UUID, values: dict[str, object]) -> Education:
        education = Education(user_id=user_id, **values)
        self.db.add(education)
        self.db.commit()
        self.db.refresh(education)
        return education

    def update(
        self,
        education: Education,
        values: dict[str, object],
    ) -> Education:
        for field, value in values.items():
            setattr(education, field, value)

        self.db.commit()
        self.db.refresh(education)
        return education

    def delete(self, education: Education) -> None:
        self.db.delete(education)
        self.db.commit()


class ExperienceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: UUID) -> list[Experience]:
        statement = (
            select(Experience)
            .where(Experience.user_id == user_id)
            .order_by(Experience.start_date.desc().nullslast(), Experience.company)
        )
        return list(self.db.scalars(statement))

    def get_for_user(self, user_id: UUID, experience_id: UUID) -> Experience | None:
        statement = select(Experience).where(
            Experience.user_id == user_id,
            Experience.id == experience_id,
        )
        return self.db.scalar(statement)

    def create(self, user_id: UUID, values: dict[str, object]) -> Experience:
        experience = Experience(user_id=user_id, **values)
        self.db.add(experience)
        self.db.commit()
        self.db.refresh(experience)
        return experience

    def update(
        self,
        experience: Experience,
        values: dict[str, object],
    ) -> Experience:
        for field, value in values.items():
            setattr(experience, field, value)

        self.db.commit()
        self.db.refresh(experience)
        return experience

    def delete(self, experience: Experience) -> None:
        self.db.delete(experience)
        self.db.commit()


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: UUID) -> list[Project]:
        statement = (
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.name)
        )
        return list(self.db.scalars(statement))

    def get_for_user(self, user_id: UUID, project_id: UUID) -> Project | None:
        statement = select(Project).where(
            Project.user_id == user_id,
            Project.id == project_id,
        )
        return self.db.scalar(statement)

    def create(self, user_id: UUID, values: dict[str, object]) -> Project:
        project = Project(user_id=user_id, **values)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def update(self, project: Project, values: dict[str, object]) -> Project:
        for field, value in values.items():
            setattr(project, field, value)

        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.commit()


class SkillRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: UUID) -> list[Skill]:
        statement = (
            select(Skill)
            .where(Skill.user_id == user_id)
            .order_by(Skill.category, Skill.name)
        )
        return list(self.db.scalars(statement))

    def get_for_user(self, user_id: UUID, skill_id: UUID) -> Skill | None:
        statement = select(Skill).where(
            Skill.user_id == user_id,
            Skill.id == skill_id,
        )
        return self.db.scalar(statement)

    def create(self, user_id: UUID, values: dict[str, object]) -> Skill:
        skill = Skill(user_id=user_id, **values)
        self.db.add(skill)
        self.db.commit()
        self.db.refresh(skill)
        return skill

    def update(self, skill: Skill, values: dict[str, object]) -> Skill:
        for field, value in values.items():
            setattr(skill, field, value)

        self.db.commit()
        self.db.refresh(skill)
        return skill

    def delete(self, skill: Skill) -> None:
        self.db.delete(skill)
        self.db.commit()
