from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FuzzySkillMatch(BaseModel):
    required_skill: str
    profile_skill: str
    score: int


class RelevantProfileItem(BaseModel):
    id: UUID
    label: str
    score: float


class JobMatchRead(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    score: int
    exact_skill_matches: list[str]
    fuzzy_skill_matches: list[FuzzySkillMatch]
    missing_skills: list[str]
    relevant_experiences: list[RelevantProfileItem]
    relevant_projects: list[RelevantProfileItem]
    match_reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
