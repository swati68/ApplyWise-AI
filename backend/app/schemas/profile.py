from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EducationBase(BaseModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    gpa: float | None = None
    location: str | None = None
    description: str | None = None


class EducationCreate(EducationBase):
    pass


class EducationUpdate(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    gpa: float | None = None
    location: str | None = None
    description: str | None = None


class EducationRead(EducationBase):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


class ExperienceBase(BaseModel):
    company: str
    role: str
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    tech_stack: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    tech_stack: list[str] | None = None
    bullets: list[str] | None = None
    tags: list[str] | None = None


class ExperienceRead(ExperienceBase):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tech_stack: list[str] | None = None
    bullets: list[str] | None = None
    links: list[str] | None = None
    tags: list[str] | None = None


class ProjectRead(ProjectBase):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


class SkillBase(BaseModel):
    category: str
    name: str
    proficiency: str | None = None
    tags: list[str] = Field(default_factory=list)


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    category: str | None = None
    name: str | None = None
    proficiency: str | None = None
    tags: list[str] | None = None


class SkillRead(SkillBase):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)
