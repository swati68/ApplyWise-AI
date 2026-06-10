from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class JobStatusCreate(BaseModel):
    name: str
    color: str | None = None
    sort_order: int = 0
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("Status name is required.")
        return cleaned_value

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None


class JobStatusUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    sort_order: int | None = None
    is_default: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("Status name is required.")
        return cleaned_value

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None


class JobStatusRead(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    color: str | None
    sort_order: int
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobStatusHistoryRead(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    from_status_id: UUID | None
    to_status_id: UUID
    note: str | None
    changed_at: datetime
    from_status: JobStatusRead | None = None
    to_status: JobStatusRead

    model_config = ConfigDict(from_attributes=True)


class JobStatusChangeRequest(BaseModel):
    status_id: UUID
    note: str | None = None

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None
