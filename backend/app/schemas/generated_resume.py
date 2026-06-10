from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GeneratedResumeRead(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    resume_template_id: UUID | None
    tailored_latex: str
    selected_experiences: list[str]
    selected_projects: list[str]
    selected_skills: list[str]
    change_summary: list[str]
    safety_warnings: list[str]
    pdf_path: str | None
    drive_url: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GeneratedResumePdfCompileResult(BaseModel):
    success: bool
    resume_id: UUID
    pdf_path: str | None = None
    download_url: str | None = None
    compiler: str | None = None
    logs: str | None = None
    error_message: str | None = None


class GeneratedResumeDriveUploadResult(BaseModel):
    success: bool
    resume_id: UUID
    drive_url: str | None = None
    drive_file_id: str | None = None
    folder_id: str | None = None
    error_message: str | None = None
