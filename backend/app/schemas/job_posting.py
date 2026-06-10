from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.job_posting import JobExtractionStatus, JobSource, JobStatus
from app.schemas.generated_resume import GeneratedResumeRead
from app.schemas.github_job_source import GithubJobSourceRead
from app.schemas.job_match import JobMatchRead
from app.schemas.job_status import JobStatusRead


class GeneratedResumeSummaryRead(BaseModel):
    id: UUID
    job_id: UUID
    pdf_path: str | None
    drive_url: str | None
    safety_warnings: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ManualJobCreate(BaseModel):
    company: str
    title: str
    location: str | None = None
    job_url: str | None = None
    description: str | None = None

    @field_validator("company", "title")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("This field is required.")
        return cleaned_value

    @field_validator("location", "job_url", "description")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None


class ManualJobGenerateRequest(BaseModel):
    job_url: str

    @field_validator("job_url")
    @classmethod
    def validate_job_url(cls, value: str) -> str:
        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("Job URL is required.")
        if not (
            cleaned_value.startswith("http://")
            or cleaned_value.startswith("https://")
        ):
            raise ValueError("Job URL must start with http:// or https://.")

        return cleaned_value


class JobPostingUpdate(BaseModel):
    company: str | None = None
    title: str | None = None
    location: str | None = None
    job_url: str | None = None
    description: str | None = None
    raw_text: str | None = None
    source_section: str | None = None
    job_tags: list[str] | None = None
    scan_match_reason: str | None = None
    posted_at: datetime | None = None
    status: JobStatus | None = None

    @field_validator("company", "title")
    @classmethod
    def validate_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("This field is required.")
        return cleaned_value

    @field_validator("location", "job_url", "description", "raw_text", "source_section", "scan_match_reason")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None

    @field_validator("job_tags")
    @classmethod
    def validate_optional_job_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None

        return _clean_text_list(value)


class JobPostingRead(BaseModel):
    id: UUID
    user_id: UUID
    github_source_id: UUID | None
    current_status_id: UUID | None
    source: JobSource
    source_repo_url: str | None
    source_raw_url: str | None
    external_job_id: str | None
    source_section: str | None
    job_tags: list[str]
    scan_match_reason: str | None
    company: str
    title: str
    location: str | None
    job_url: str | None
    description: str | None
    raw_text: str | None
    extracted_description: str | None
    extraction_status: JobExtractionStatus
    extraction_error: str | None
    extracted_at: datetime | None
    posted_at: datetime | None
    discovered_at: datetime
    status: JobStatus
    content_hash: str
    created_at: datetime
    updated_at: datetime
    current_status: JobStatusRead | None = None
    github_source: GithubJobSourceRead | None = None
    latest_match: JobMatchRead | None = None
    latest_generated_resume: GeneratedResumeSummaryRead | None = None

    model_config = ConfigDict(from_attributes=True)


class JobPostingCreateResult(BaseModel):
    job: JobPostingRead
    duplicate: bool
    message: str


class JobExtractionResultRead(BaseModel):
    cleaned_text: str
    page_title: str
    company_guess: str | None
    title_guess: str | None
    location_guess: str | None
    posted_at: datetime | None
    extraction_success: bool
    extraction_method: str
    error_message: str | None


class ManualJobPdfStatus(BaseModel):
    attempted: bool
    success: bool
    skipped: bool
    pdf_path: str | None = None
    download_url: str | None = None
    compiler: str | None = None
    error_message: str | None = None


class ManualJobDriveStatus(BaseModel):
    attempted: bool
    success: bool
    skipped: bool
    drive_url: str | None = None
    error_message: str | None = None


class ManualJobGenerateResult(BaseModel):
    job: JobPostingRead
    extraction_result: JobExtractionResultRead
    match_result: JobMatchRead | None
    generated_resume_result: GeneratedResumeRead | None
    pdf_status: ManualJobPdfStatus | None
    drive_status: ManualJobDriveStatus | None
    duplicate: bool
    errors: list[str]


def _clean_text_list(values: list[str]) -> list[str]:
    cleaned_values: list[str] = []
    seen_values: set[str] = set()
    for value in values:
        cleaned_value = str(value).strip()
        normalized_value = cleaned_value.casefold()
        if cleaned_value == "" or normalized_value in seen_values:
            continue

        cleaned_values.append(cleaned_value)
        seen_values.add(normalized_value)

    return cleaned_values
