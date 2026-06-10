from datetime import datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.scheduler import SchedulerRunStatus, SchedulerTriggerType


class SchedulerPreferenceUpdate(BaseModel):
    enabled: bool
    timezone: str
    morning_enabled: bool
    morning_time: time
    evening_enabled: bool
    evening_time: time
    min_match_score: int = Field(ge=0, le=100)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("Timezone is required.")

        try:
            ZoneInfo(cleaned_value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Use a valid IANA timezone, such as America/New_York.") from error

        return cleaned_value


class SchedulerPreferenceRead(BaseModel):
    id: UUID
    user_id: UUID
    enabled: bool
    timezone: str
    morning_enabled: bool
    morning_time: time
    evening_enabled: bool
    evening_time: time
    min_match_score: int
    next_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SchedulerRunRead(BaseModel):
    id: UUID
    user_id: UUID
    trigger_type: SchedulerTriggerType
    started_at: datetime
    finished_at: datetime | None
    status: SchedulerRunStatus
    total_sources: int
    sources_succeeded: int
    sources_failed: int
    jobs_scanned: int
    jobs_inserted: int
    duplicates_skipped: int
    jobs_matched: int
    resumes_generated: int
    pdfs_compiled: int
    drive_uploads: int
    emails_sent: int
    error_message: str | None
    summary: dict[str, object] | None

    model_config = ConfigDict(from_attributes=True)
