import hashlib
import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.models.job_posting import JobPosting, JobSource, JobStatus
from app.repositories.job_posting_repository import JobPostingRepository
from app.schemas.job_posting import ManualJobCreate
from app.services.job_status_service import JobStatusService


class DuplicateJobPostingError(Exception):
    def __init__(self, job: JobPosting) -> None:
        self.job = job
        super().__init__("A duplicate job posting already exists.")


@dataclass(frozen=True)
class ManualJobCreateResult:
    job: JobPosting
    duplicate: bool
    message: str


class JobPostingService:
    def __init__(
        self,
        repository: JobPostingRepository,
        status_service: JobStatusService | None = None,
    ) -> None:
        self.repository = repository
        self.status_service = status_service

    def create_manual_job(
        self,
        *,
        user_id: UUID,
        payload: ManualJobCreate,
    ) -> ManualJobCreateResult:
        values = payload.model_dump()
        content_hash = compute_content_hash(
            company=payload.company,
            title=payload.title,
            location=payload.location,
            job_url=payload.job_url,
            description=payload.description,
        )

        duplicate = self.find_duplicate(
            user_id=user_id,
            company=payload.company,
            title=payload.title,
            location=payload.location,
            job_url=payload.job_url,
            content_hash=content_hash,
        )
        if duplicate is not None:
            return ManualJobCreateResult(
                job=duplicate,
                duplicate=True,
                message="Duplicate job already exists; returning the existing job.",
            )

        try:
            current_status_id = (
                self.status_service.get_default_status(user_id, "New").id
                if self.status_service is not None
                else None
            )
            job = self.repository.create(
                {
                    **values,
                    "user_id": user_id,
                    "source": JobSource.MANUAL,
                    "status": JobStatus.NEW,
                    "current_status_id": current_status_id,
                    "content_hash": content_hash,
                    "raw_text": payload.description,
                }
            )
            if self.status_service is not None:
                self.status_service.record_initial_status(job=job)
        except IntegrityError:
            self.repository.rollback()
            duplicate = self.find_duplicate(
                user_id=user_id,
                company=payload.company,
                title=payload.title,
                location=payload.location,
                job_url=payload.job_url,
                content_hash=content_hash,
            )
            if duplicate is None:
                raise

            return ManualJobCreateResult(
                job=duplicate,
                duplicate=True,
                message="Duplicate job already exists; returning the existing job.",
            )

        return ManualJobCreateResult(
            job=job,
            duplicate=False,
            message="Job created.",
        )

    def update_job(
        self,
        *,
        job: JobPosting,
        values: dict[str, object],
    ) -> JobPosting:
        next_values = {
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "job_url": job.job_url,
            "description": job.description,
        }
        for field in next_values:
            if field in values:
                next_values[field] = values[field]

        if any(field in values for field in next_values):
            content_hash = compute_content_hash(
                company=str(next_values["company"]),
                title=str(next_values["title"]),
                location=_optional_string(next_values["location"]),
                job_url=_optional_string(next_values["job_url"]),
                description=_optional_string(next_values["description"]),
            )
            duplicate = self.find_duplicate(
                user_id=job.user_id,
                company=str(next_values["company"]),
                title=str(next_values["title"]),
                location=_optional_string(next_values["location"]),
                job_url=_optional_string(next_values["job_url"]),
                content_hash=content_hash,
                exclude_job_id=job.id,
            )
            if duplicate is not None:
                raise DuplicateJobPostingError(duplicate)

            values["content_hash"] = content_hash

        return self.repository.update(job, values)

    def find_duplicate(
        self,
        *,
        user_id: UUID,
        company: str,
        title: str,
        location: str | None,
        job_url: str | None,
        content_hash: str,
        exclude_job_id: UUID | None = None,
    ) -> JobPosting | None:
        if job_url is not None:
            duplicate = self.repository.find_by_job_url(
                user_id=user_id,
                job_url=job_url,
                exclude_job_id=exclude_job_id,
            )
            if duplicate is not None:
                return duplicate

            normalized_job_url = normalize_url(job_url)
            for job in self.repository.list_by_user(user_id):
                if exclude_job_id is not None and job.id == exclude_job_id:
                    continue
                if normalize_url(job.job_url) == normalized_job_url:
                    return job

        duplicate = self.repository.find_by_content_hash(
            user_id=user_id,
            content_hash=content_hash,
            exclude_job_id=exclude_job_id,
        )
        if duplicate is not None:
            return duplicate

        normalized_company = normalize_identity_text(company)
        normalized_title = normalize_identity_text(title)
        normalized_location = normalize_identity_text(location)
        for job in self.repository.list_by_user(user_id):
            if exclude_job_id is not None and job.id == exclude_job_id:
                continue
            if (
                normalize_identity_text(job.company) == normalized_company
                and normalize_identity_text(job.title) == normalized_title
                and normalize_identity_text(job.location) == normalized_location
            ):
                return job

        return None


def compute_content_hash(
    *,
    company: str,
    title: str,
    location: str | None,
    job_url: str | None,
    description: str | None,
) -> str:
    payload = {
        "company": normalize_identity_text(company),
        "title": normalize_identity_text(title),
        "location": normalize_identity_text(location),
        "job_url": normalize_url(job_url),
        "description": (description or "").strip(),
    }
    encoded_payload = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded_payload).hexdigest()


def normalize_identity_text(value: str | None) -> str:
    if value is None:
        return ""

    return re.sub(r"\s+", " ", value.strip()).casefold()


def normalize_url(value: str | None) -> str:
    if value is None:
        return ""

    cleaned_value = value.strip()
    if cleaned_value == "":
        return ""

    parsed_url = urlparse(cleaned_value)
    if parsed_url.scheme == "" or parsed_url.netloc == "":
        return cleaned_value

    path = parsed_url.path.rstrip("/") or "/"
    return urlunparse(
        (
            parsed_url.scheme.casefold(),
            parsed_url.netloc.casefold(),
            path,
            "",
            parsed_url.query,
            "",
        )
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value

    return str(value)
