from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter

from app.core.config import Settings
from app.models.github_job_source import GithubJobSource
from app.models.job_match import JobMatch
from app.models.job_posting import JobPosting
from app.models.user import User
from app.repositories.generated_resume_repository import GeneratedResumeRepository
from app.services.digest_service import DigestService
from app.services.github_job_source_service import GithubJobSourceService
from app.services.google_drive_service import (
    GoogleDriveConfigurationError,
    GoogleDriveService,
    GoogleDriveUploadError,
)
from app.services.job_match_service import JobMatchService, LowMatchScoreError
from app.services.job_status_service import JobStatusService
from app.services.resume_generation_service import (
    NoDefaultResumeTemplateError,
    ResumeGenerationBlockedError,
    ResumeGenerationService,
)
from app.services.resume_pdf_service import ResumePdfService, resolve_generated_resume_pdf_path


@dataclass
class GithubSourcePipelineSummary:
    total_rows_seen: int = 0
    parsed_jobs: int = 0
    rows_skipped_by_filters: int = 0
    inserted_jobs: int = 0
    duplicate_jobs: int = 0
    jobs_tagged: int = 0
    extraction_success_count: int = 0
    extraction_failed_count: int = 0
    jobs_matched: int = 0
    resumes_generated: int = 0
    pdfs_compiled: int = 0
    drive_uploads_successful: int = 0
    emails_sent: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class GithubSourcePipelineService:
    def __init__(
        self,
        *,
        scan_service: GithubJobSourceService,
        match_service: JobMatchService,
        resume_generation_service: ResumeGenerationService,
        pdf_service: ResumePdfService,
        generated_resume_repository: GeneratedResumeRepository,
        digest_service: DigestService,
        settings: Settings,
        drive_service: GoogleDriveService | None = None,
        status_service: JobStatusService | None = None,
    ) -> None:
        self.scan_service = scan_service
        self.match_service = match_service
        self.resume_generation_service = resume_generation_service
        self.pdf_service = pdf_service
        self.generated_resume_repository = generated_resume_repository
        self.digest_service = digest_service
        self.settings = settings
        self.drive_service = drive_service
        self.status_service = status_service

    def run(
        self,
        *,
        source: GithubJobSource,
        user: User,
        min_match_score: int,
    ) -> GithubSourcePipelineSummary:
        started_at = perf_counter()
        summary = GithubSourcePipelineSummary()
        try:
            scan_result = self.scan_service.scan_source(source)
            summary.total_rows_seen = scan_result.total_rows_seen
            summary.parsed_jobs = scan_result.parsed_jobs
            summary.rows_skipped_by_filters = getattr(scan_result, "rows_skipped_by_filters", 0)
            summary.inserted_jobs = scan_result.inserted_jobs
            summary.duplicate_jobs = scan_result.duplicate_jobs
            summary.jobs_tagged = getattr(scan_result, "jobs_tagged", 0)
            summary.extraction_success_count = getattr(scan_result, "extraction_success_count", 0)
            summary.extraction_failed_count = getattr(scan_result, "extraction_failed_count", 0)

            for job in scan_result.inserted_job_records:
                match = self._match_job(job=job, user=user, summary=summary)
                if match is None:
                    continue
                if match.score < min_match_score:
                    continue

                generated_resume = self._generate_resume(job=job, user=user, summary=summary)
                if generated_resume is None:
                    continue

                pdf_path = self._compile_pdf(
                    generated_resume=generated_resume,
                    job=job,
                    summary=summary,
                )
                if pdf_path is None:
                    continue

                self._upload_pdf_to_drive_if_configured(
                    generated_resume=generated_resume,
                    pdf_path=pdf_path,
                    job=job,
                    summary=summary,
                )

            if summary.jobs_matched > 0 or summary.resumes_generated > 0:
                digest_result = self.digest_service.send_digest(user=user)
                if digest_result.success:
                    summary.emails_sent = 1
                elif digest_result.error_message:
                    summary.errors.append(f"Digest email was not sent: {digest_result.error_message}")

            return summary
        finally:
            summary.duration_seconds = round(perf_counter() - started_at, 2)

    def _match_job(
        self,
        *,
        job: JobPosting,
        user: User,
        summary: GithubSourcePipelineSummary,
    ) -> JobMatch | None:
        try:
            match = self.match_service.match_job(user_id=user.id, job=job)
        except LowMatchScoreError as error:
            summary.errors.append(f"Skipped {job.company} - {job.title}: {error}")
            return None
        except Exception as error:
            summary.errors.append(f"Failed to match {job.company} - {job.title}: {error}")
            return None

        if match.match_reason.startswith("Skipped matching"):
            summary.errors.append(f"Skipped matching {job.company} - {job.title}: {match.match_reason}")
            return None

        summary.jobs_matched += 1
        if self.status_service is not None:
            self.status_service.set_status_by_name(
                job=job,
                name="Matched",
                note="Pipeline matched this job.",
            )
        return match

    def _generate_resume(
        self,
        *,
        job: JobPosting,
        user: User,
        summary: GithubSourcePipelineSummary,
    ):
        try:
            generated_resume = self.resume_generation_service.generate_for_job(
                user_id=user.id,
                job=job,
            )
        except (NoDefaultResumeTemplateError, ResumeGenerationBlockedError) as error:
            summary.errors.append(
                f"Resume was not generated for {job.company} - {job.title}: {error}",
            )
            return None
        except Exception as error:
            summary.errors.append(
                f"Resume generation failed for {job.company} - {job.title}: {error}",
            )
            return None

        summary.resumes_generated += 1
        if self.status_service is not None:
            self.status_service.set_status_by_name(
                job=job,
                name="Resume Generated",
                note="Pipeline generated a tailored resume.",
            )
        return generated_resume

    def _compile_pdf(
        self,
        *,
        generated_resume,
        job: JobPosting,
        summary: GithubSourcePipelineSummary,
    ) -> Path | None:
        result = self.pdf_service.compile_pdf(generated_resume)
        if not result.success:
            message = result.error_message or "Unknown PDF compilation error."
            summary.errors.append(
                f"PDF compilation failed for {job.company} - {job.title}: {message}",
            )
            return None

        summary.pdfs_compiled += 1
        refreshed_resume = self.generated_resume_repository.get_for_user(
            generated_resume.user_id,
            generated_resume.id,
        ) or generated_resume
        pdf_path = resolve_generated_resume_pdf_path(refreshed_resume)
        if pdf_path is None:
            summary.errors.append(
                f"PDF was compiled for {job.company} - {job.title}, but the stored path could not be resolved.",
            )

        return pdf_path

    def _upload_pdf_to_drive_if_configured(
        self,
        *,
        generated_resume,
        pdf_path: Path,
        job: JobPosting,
        summary: GithubSourcePipelineSummary,
    ) -> None:
        if self.drive_service is None and not _is_google_drive_configured(self.settings):
            return

        drive_service = self.drive_service or GoogleDriveService(self.settings)
        try:
            upload_result = drive_service.upload_pdf(
                pdf_path=pdf_path,
                file_name=f"applywise-resume-{generated_resume.id}.pdf",
            )
        except (GoogleDriveConfigurationError, GoogleDriveUploadError, FileNotFoundError) as error:
            summary.errors.append(
                f"Google Drive upload failed for {job.company} - {job.title}: {error}",
            )
            return

        self.generated_resume_repository.update(
            generated_resume,
            {"drive_url": upload_result.drive_url},
        )
        summary.drive_uploads_successful += 1


def _is_google_drive_configured(settings: Settings) -> bool:
    return (
        settings.google_drive_service_account_file.strip() != ""
        or settings.google_drive_service_account_json.strip() != ""
    )
