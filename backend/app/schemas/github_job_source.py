from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GithubJobSourceBase(BaseModel):
    name: str
    repo_url: str
    raw_readme_url: str
    branch: str = "main"
    enabled: bool = True
    scan_role_tags: list[str] = Field(default_factory=list)
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    scan_instructions: str | None = None

    @field_validator("name", "branch")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("This field is required.")
        return cleaned_value

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, value: str) -> str:
        cleaned_value = value.strip()
        parsed_url = urlparse(cleaned_value)
        if parsed_url.scheme != "https" or parsed_url.netloc.casefold() != "github.com":
            raise ValueError("Repository URL must be a GitHub HTTPS URL.")
        return cleaned_value

    @field_validator("raw_readme_url")
    @classmethod
    def validate_raw_readme_url(cls, value: str) -> str:
        cleaned_value = value.strip()
        parsed_url = urlparse(cleaned_value)
        allowed_hosts = {"raw.githubusercontent.com", "github.com"}
        if parsed_url.scheme != "https" or parsed_url.netloc.casefold() not in allowed_hosts:
            raise ValueError("Raw README URL must be a GitHub HTTPS raw markdown URL.")
        if parsed_url.netloc.casefold() == "github.com" and "/raw/" not in parsed_url.path:
            raise ValueError("GitHub README URL must point to raw markdown content.")
        if not parsed_url.path.casefold().endswith(".md"):
            raise ValueError("Raw README URL must point to a markdown file.")
        return cleaned_value

    @field_validator("scan_role_tags", "include_keywords", "exclude_keywords")
    @classmethod
    def validate_text_list(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value)

    @field_validator("scan_instructions")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None


class GithubJobSourceCreate(GithubJobSourceBase):
    pass


class GithubJobSourceUpdate(BaseModel):
    name: str | None = None
    repo_url: str | None = None
    raw_readme_url: str | None = None
    branch: str | None = None
    enabled: bool | None = None
    scan_role_tags: list[str] | None = None
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    scan_instructions: str | None = None

    @field_validator("name", "branch")
    @classmethod
    def validate_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("This field is required.")
        return cleaned_value

    @field_validator("repo_url")
    @classmethod
    def validate_optional_repo_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return GithubJobSourceBase.validate_repo_url(value)

    @field_validator("raw_readme_url")
    @classmethod
    def validate_optional_raw_readme_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return GithubJobSourceBase.validate_raw_readme_url(value)

    @field_validator("scan_role_tags", "include_keywords", "exclude_keywords")
    @classmethod
    def validate_optional_text_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None

        return _clean_text_list(value)

    @field_validator("scan_instructions")
    @classmethod
    def validate_optional_scan_instructions(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()
        return cleaned_value or None


class GithubJobSourceRead(GithubJobSourceBase):
    id: UUID
    user_id: UUID
    last_scanned_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GithubScanRunRead(BaseModel):
    id: UUID
    user_id: UUID
    source_id: UUID
    scanned_jobs_count: int
    inserted_jobs_count: int
    duplicate_jobs_count: int
    rows_skipped_by_filters: int
    jobs_tagged: int
    extraction_success_count: int
    extraction_failed_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GithubJobSourceScanResult(BaseModel):
    source: GithubJobSourceRead
    scan_run: GithubScanRunRead
    total_rows_seen: int = 0
    parsed_jobs: int = 0
    scanned_jobs: int
    inserted_jobs: int
    duplicate_jobs: int
    rows_skipped_by_filters: int
    jobs_tagged: int
    extraction_success_count: int
    extraction_failed_count: int
    matched_jobs: int
    generated_resumes: int
    uploaded_pdfs: int
    message: str


class GithubSourcePipelineResult(BaseModel):
    total_rows_seen: int
    parsed_jobs: int
    rows_skipped_by_filters: int
    inserted_jobs: int
    duplicate_jobs: int
    jobs_tagged: int
    extraction_success_count: int
    extraction_failed_count: int
    jobs_matched: int
    resumes_generated: int
    pdfs_compiled: int
    drive_uploads_successful: int
    emails_sent: int
    duration_seconds: float
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
