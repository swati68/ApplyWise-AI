from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class ResumeTemplateBase(BaseModel):
    name: str
    latex_content: str
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("Template name is required.")
        return cleaned_value

    @field_validator("latex_content")
    @classmethod
    def validate_latex_content(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("Template content cannot be empty.")
        return value


class ResumeTemplateCreate(ResumeTemplateBase):
    pass


class ResumeTemplateUpdate(BaseModel):
    name: str | None = None
    latex_content: str | None = None
    is_default: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("Template name is required.")
        return cleaned_value

    @field_validator("latex_content")
    @classmethod
    def validate_latex_content(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if value.strip() == "":
            raise ValueError("Template content cannot be empty.")
        return value


class ResumeTemplateRead(ResumeTemplateBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
