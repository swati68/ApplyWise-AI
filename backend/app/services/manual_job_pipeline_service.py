from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.models.generated_resume import GeneratedResume
from app.models.job_match import JobMatch
from app.models.job_posting import JobExtractionStatus, JobPosting, JobSource, JobStatus
from app.repositories.generated_resume_repository import GeneratedResumeRepository
from app.repositories.job_posting_repository import JobPostingRepository
from app.services.google_drive_service import (
    GoogleDriveConfigurationError,
    GoogleDriveService,
    GoogleDriveUploadError,
    is_google_drive_configured,
)
from app.services.job_match_service import JobMatchService, LowMatchScoreError
from app.services.job_service import compute_content_hash, normalize_identity_text, normalize_url
from app.services.job_status_service import JobStatusService
from app.services.jobs.job_content_extractor import (
    ExtractedJobContent,
    JobContentExtractorService,
)
from app.services.jobs.job_role_filter import JobRoleFilterInput, classify_job_role
from app.services.resume_generation_service import (
    NoDefaultResumeTemplateError,
    ResumeGenerationBlockedError,
    ResumeGenerationService,
)
from app.services.resume_pdf_service import (
    PdfCompileResult,
    ResumePdfService,
    resolve_generated_resume_pdf_path,
)


@dataclass(frozen=True)
class DriveUploadPipelineResult:
    attempted: bool
    success: bool
    skipped: bool
    drive_url: str | None = None
    error_message: str | None = None


@dataclass
class ManualJobPipelineResult:
    job: JobPosting
    duplicate: bool
    extraction_result: ExtractedJobContent
    match_result: JobMatch | None = None
    generated_resume_result: GeneratedResume | None = None
    pdf_result: PdfCompileResult | None = None
    drive_result: DriveUploadPipelineResult | None = None
    errors: list[str] = field(default_factory=list)


class ManualJobPipelineService:
    def __init__(
        self,
        *,
        job_repository: JobPostingRepository,
        match_service: JobMatchService,
        resume_generation_service: ResumeGenerationService,
        generated_resume_repository: GeneratedResumeRepository,
        pdf_service: ResumePdfService,
        settings: Settings,
        extractor: JobContentExtractorService | None = None,
        drive_service: GoogleDriveService | None = None,
        status_service: JobStatusService | None = None,
    ) -> None:
        self.job_repository = job_repository
        self.match_service = match_service
        self.resume_generation_service = resume_generation_service
        self.generated_resume_repository = generated_resume_repository
        self.pdf_service = pdf_service
        self.settings = settings
        self.extractor = extractor or JobContentExtractorService()
        self.drive_service = drive_service
        self.status_service = status_service

    def run(self, *, user_id: UUID, job_url: str) -> ManualJobPipelineResult:
        cleaned_job_url = normalize_url(job_url)
        url_duplicate = self._find_duplicate_by_url(user_id, cleaned_job_url)

        if url_duplicate is not None:
            extraction_result = self._extract_or_reuse_existing_content(
                url_duplicate,
                cleaned_job_url,
            )
            job = self._update_existing_job_from_extraction(
                url_duplicate,
                cleaned_job_url,
                extraction_result,
            )
            duplicate = True
        else:
            extraction_result = self.extractor.extract_job_content(cleaned_job_url)
            job, duplicate = self._create_or_reuse_job(
                user_id=user_id,
                job_url=cleaned_job_url,
                extraction_result=extraction_result,
            )

        result = ManualJobPipelineResult(
            job=job,
            duplicate=duplicate,
            extraction_result=extraction_result,
        )
        result.match_result = self._match_job(user_id=user_id, job=job, result=result)
        if _is_skipped_match(result.match_result):
            return result

        result.generated_resume_result = self._get_or_generate_resume(
            user_id=user_id,
            job=job,
            result=result,
        )
        if result.generated_resume_result is None:
            return result

        result.pdf_result = self._compile_pdf_if_needed(
            generated_resume=result.generated_resume_result,
            result=result,
        )
        refreshed_resume = self.generated_resume_repository.get_for_user(
            user_id,
            result.generated_resume_result.id,
        )
        if refreshed_resume is not None:
            result.generated_resume_result = refreshed_resume

        result.drive_result = self._upload_to_drive_if_possible(
            generated_resume=result.generated_resume_result,
            result=result,
        )
        return result

    def _find_duplicate_by_url(self, user_id: UUID, job_url: str) -> JobPosting | None:
        exact_match = self.job_repository.find_by_job_url(
            user_id=user_id,
            job_url=job_url,
        )
        if exact_match is not None:
            return exact_match

        normalized_job_url = normalize_url(job_url)
        for job in self.job_repository.list_by_user(user_id):
            if normalize_url(job.job_url) == normalized_job_url:
                return job

        return None

    def _extract_or_reuse_existing_content(
        self,
        job: JobPosting,
        job_url: str,
    ) -> ExtractedJobContent:
        if (
            job.extraction_status == JobExtractionStatus.SUCCESS
            and _clean_optional_text(job.extracted_description) is not None
        ):
            return ExtractedJobContent(
                cleaned_text=str(job.extracted_description),
                page_title=job.title,
                company_guess=job.company,
                extraction_success=True,
                extraction_method="stored_job_posting",
                raw_html=None,
                error_message=None,
                title_guess=job.title,
                location_guess=job.location,
                posted_at=job.posted_at,
            )

        return self.extractor.extract_job_content(job_url)

    def _create_or_reuse_job(
        self,
        *,
        user_id: UUID,
        job_url: str,
        extraction_result: ExtractedJobContent,
    ) -> tuple[JobPosting, bool]:
        values = _job_values_from_extraction(
            user_id=user_id,
            job_url=job_url,
            extraction_result=extraction_result,
        )
        if self.status_service is not None:
            values["current_status_id"] = self.status_service.get_default_status(
                user_id,
                "New",
            ).id
        content_duplicate = self.job_repository.find_by_content_hash(
            user_id=user_id,
            content_hash=str(values["content_hash"]),
        )
        if content_duplicate is not None:
            return (
                self._update_existing_job_from_extraction(
                    content_duplicate,
                    job_url,
                    extraction_result,
                ),
                True,
            )

        try:
            job = self.job_repository.create(values)
            if self.status_service is not None:
                self.status_service.record_initial_status(job=job)
            return job, False
        except IntegrityError:
            self.job_repository.rollback()
            duplicate = self._find_duplicate_by_url(user_id, job_url)
            if duplicate is not None:
                return (
                    self._update_existing_job_from_extraction(
                        duplicate,
                        job_url,
                        extraction_result,
                    ),
                    True,
                )
            raise

    def _update_existing_job_from_extraction(
        self,
        job: JobPosting,
        job_url: str,
        extraction_result: ExtractedJobContent,
    ) -> JobPosting:
        update_values = _job_extraction_update_values(
            job=job,
            job_url=job_url,
            extraction_result=extraction_result,
        )
        content_hash = update_values.get("content_hash")
        if isinstance(content_hash, str):
            duplicate = self.job_repository.find_by_content_hash(
                user_id=job.user_id,
                content_hash=content_hash,
                exclude_job_id=job.id,
            )
            if duplicate is not None:
                update_values.pop("content_hash")

        if not update_values:
            return job

        return self.job_repository.update(job, update_values)

    def _match_job(
        self,
        *,
        user_id: UUID,
        job: JobPosting,
        result: ManualJobPipelineResult,
    ) -> JobMatch | None:
        try:
            match = self.match_service.match_job(user_id=user_id, job=job)
        except LowMatchScoreError as error:
            result.errors.append(str(error))
            return None
        except Exception as error:
            result.errors.append(f"Profile match failed: {error}")
            return None

        if _is_skipped_match(match):
            result.errors.append(match.match_reason)
            return match

        self._set_pipeline_status(job, "Matched", JobStatus.MATCHED)
        return match

    def _get_or_generate_resume(
        self,
        *,
        user_id: UUID,
        job: JobPosting,
        result: ManualJobPipelineResult,
    ) -> GeneratedResume | None:
        existing_resume = self.generated_resume_repository.get_latest_for_job(
            user_id,
            job.id,
        )
        if existing_resume is not None:
            self._set_pipeline_status(
                job,
                "Resume Generated",
                JobStatus.RESUME_GENERATED,
            )
            return existing_resume

        try:
            generated_resume = self.resume_generation_service.generate_for_job(
                user_id=user_id,
                job=job,
            )
        except (NoDefaultResumeTemplateError, ResumeGenerationBlockedError) as error:
            result.errors.append(f"Resume generation was not completed: {error}")
            return None
        except Exception as error:
            result.errors.append(f"Resume generation failed: {error}")
            return None

        self._set_pipeline_status(
            job,
            "Resume Generated",
            JobStatus.RESUME_GENERATED,
        )
        return generated_resume

    def _set_pipeline_status(
        self,
        job: JobPosting,
        status_name: str,
        fallback_status: JobStatus,
    ) -> JobPosting:
        if self.status_service is None:
            return self.job_repository.update(job, {"status": fallback_status})

        return self.status_service.set_status_by_name(
            job=job,
            name=status_name,
            note=f"Pipeline marked job as {status_name}.",
        ).job

    def _compile_pdf_if_needed(
        self,
        *,
        generated_resume: GeneratedResume,
        result: ManualJobPipelineResult,
    ) -> PdfCompileResult:
        existing_pdf_path = resolve_generated_resume_pdf_path(generated_resume)
        if existing_pdf_path is not None and existing_pdf_path.exists():
            return PdfCompileResult(
                success=True,
                resume_id=generated_resume.id,
                pdf_path=generated_resume.pdf_path,
                download_url=f"/api/generated-resumes/{generated_resume.id}/download",
                compiler=None,
                logs=None,
                error_message=None,
            )

        compile_result = self.pdf_service.compile_pdf(generated_resume)
        if not compile_result.success:
            result.errors.append(
                f"PDF compilation failed: {compile_result.error_message or 'Unknown error.'}",
            )
        return compile_result

    def _upload_to_drive_if_possible(
        self,
        *,
        generated_resume: GeneratedResume,
        result: ManualJobPipelineResult,
    ) -> DriveUploadPipelineResult:
        if self.drive_service is None and not is_google_drive_configured(self.settings):
            return DriveUploadPipelineResult(
                attempted=False,
                success=False,
                skipped=True,
                error_message="Google Drive is not configured.",
            )

        if _clean_optional_text(generated_resume.drive_url) is not None:
            return DriveUploadPipelineResult(
                attempted=False,
                success=True,
                skipped=True,
                drive_url=generated_resume.drive_url,
            )

        pdf_path = resolve_generated_resume_pdf_path(generated_resume)
        if pdf_path is None or not pdf_path.exists():
            return DriveUploadPipelineResult(
                attempted=False,
                success=False,
                skipped=True,
                error_message="PDF is not available for Google Drive upload.",
            )

        drive_service = self.drive_service or GoogleDriveService(self.settings)
        try:
            upload_result = drive_service.upload_pdf(
                pdf_path=Path(pdf_path),
                file_name=f"applywise-resume-{generated_resume.id}.pdf",
            )
        except (GoogleDriveConfigurationError, GoogleDriveUploadError, FileNotFoundError) as error:
            result.errors.append(f"Google Drive upload failed: {error}")
            return DriveUploadPipelineResult(
                attempted=True,
                success=False,
                skipped=False,
                error_message=str(error),
            )

        updated_resume = self.generated_resume_repository.update(
            generated_resume,
            {"drive_url": upload_result.drive_url},
        )
        result.generated_resume_result = updated_resume
        return DriveUploadPipelineResult(
            attempted=True,
            success=True,
            skipped=False,
            drive_url=updated_resume.drive_url,
            error_message=None,
        )


def _job_values_from_extraction(
    *,
    user_id: UUID,
    job_url: str,
    extraction_result: ExtractedJobContent,
) -> dict[str, object]:
    company = _guess_company(extraction_result, job_url)
    title = _guess_title(extraction_result)
    location = _clean_optional_text(extraction_result.location_guess)
    extracted_description = (
        extraction_result.cleaned_text if extraction_result.extraction_success else None
    )
    raw_text = _clean_optional_text(extraction_result.cleaned_text)
    content_hash = compute_content_hash(
        company=company,
        title=title,
        location=location,
        job_url=job_url,
        description=extracted_description,
    )
    classification = classify_job_role(
        JobRoleFilterInput(
            title=title,
            raw_text=raw_text,
            description=extracted_description,
        ),
    )

    return {
        "user_id": user_id,
        "source": JobSource.MANUAL,
        "company": company,
        "title": title,
        "location": location,
        "job_url": job_url,
        "description": None,
        "raw_text": raw_text,
        "extracted_description": extracted_description,
        "extraction_status": _extraction_status(extraction_result),
        "extraction_error": extraction_result.error_message,
        "extracted_at": datetime.now(UTC),
        "posted_at": extraction_result.posted_at,
        "job_tags": classification.job_tags,
        "scan_match_reason": classification.reason,
        "status": JobStatus.NEW,
        "content_hash": content_hash,
    }


def _job_extraction_update_values(
    *,
    job: JobPosting,
    job_url: str,
    extraction_result: ExtractedJobContent,
) -> dict[str, object]:
    extracted_description = (
        extraction_result.cleaned_text if extraction_result.extraction_success else None
    )
    update_values: dict[str, object] = {
        "job_url": job_url,
        "raw_text": _clean_optional_text(extraction_result.cleaned_text) or job.raw_text,
        "extracted_description": extracted_description,
        "extraction_status": _extraction_status(extraction_result),
        "extraction_error": extraction_result.error_message,
        "extracted_at": datetime.now(UTC),
    }
    if extraction_result.posted_at is not None:
        update_values["posted_at"] = extraction_result.posted_at

    company_guess = _clean_optional_text(extraction_result.company_guess)
    if company_guess is not None and _is_auto_placeholder(job.company):
        update_values["company"] = company_guess

    title_guess = _clean_optional_text(extraction_result.title_guess)
    if title_guess is not None and _is_auto_placeholder(job.title):
        update_values["title"] = title_guess

    location_guess = _clean_optional_text(extraction_result.location_guess)
    if location_guess is not None and _clean_optional_text(job.location) is None:
        update_values["location"] = location_guess

    next_company = str(update_values.get("company", job.company))
    next_title = str(update_values.get("title", job.title))
    next_location = update_values.get("location", job.location)
    update_values["content_hash"] = compute_content_hash(
        company=next_company,
        title=next_title,
        location=str(next_location) if next_location is not None else None,
        job_url=job_url,
        description=extracted_description,
    )
    classification = classify_job_role(
        JobRoleFilterInput(
            title=next_title,
            raw_text=str(update_values.get("raw_text") or job.raw_text or ""),
            description=extracted_description,
        ),
    )
    current_tags = getattr(job, "job_tags", [])
    merged_tags = _merge_text_lists(current_tags, classification.job_tags)
    if merged_tags != (current_tags or []):
        update_values["job_tags"] = merged_tags
    if getattr(job, "scan_match_reason", None) is None:
        update_values["scan_match_reason"] = classification.reason
    return update_values


def _extraction_status(extraction_result: ExtractedJobContent) -> JobExtractionStatus:
    return (
        JobExtractionStatus.SUCCESS
        if extraction_result.extraction_success
        else JobExtractionStatus.FAILED
    )


def _guess_company(extraction_result: ExtractedJobContent, job_url: str) -> str:
    company_guess = _clean_optional_text(extraction_result.company_guess)
    if company_guess is not None:
        return company_guess

    host = urlparse(job_url).netloc
    return host.removeprefix("www.") or "Unknown company"


def _guess_title(extraction_result: ExtractedJobContent) -> str:
    for value in [extraction_result.title_guess, extraction_result.page_title]:
        cleaned_value = _clean_optional_text(value)
        if cleaned_value is not None:
            return cleaned_value

    return "Job posting"


def _is_auto_placeholder(value: str | None) -> bool:
    normalized_value = normalize_identity_text(value)
    return normalized_value in {
        "",
        "job posting",
        "unknown company",
    } or normalized_value.endswith(".com")


def _is_skipped_match(match: JobMatch | None) -> bool:
    return match is not None and match.match_reason.startswith("Skipped matching")


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned_value = value.strip()
    return cleaned_value or None


def _merge_text_lists(current_values: list[str] | None, next_values: list[str]) -> list[str]:
    merged_values: list[str] = []
    seen_values: set[str] = set()
    for value in [*(current_values or []), *next_values]:
        cleaned_value = str(value).strip()
        normalized_value = cleaned_value.casefold()
        if cleaned_value == "" or normalized_value in seen_values:
            continue
        merged_values.append(cleaned_value)
        seen_values.add(normalized_value)

    return merged_values
