from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.digest_repository import DigestRepository
from app.repositories.generated_resume_repository import GeneratedResumeRepository
from app.repositories.github_job_source_repository import GithubJobSourceRepository
from app.repositories.github_scan_run_repository import GithubScanRunRepository
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_posting_repository import JobPostingRepository
from app.repositories.job_status_history_repository import JobStatusHistoryRepository
from app.repositories.job_status_repository import JobStatusRepository
from app.repositories.profile_repository import (
    EducationRepository,
    ExperienceRepository,
    ProjectRepository,
    SkillRepository,
)
from app.repositories.resume_template_repository import ResumeTemplateRepository
from app.services.digest_service import DigestService
from app.services.github_job_source_service import GithubJobSourceService
from app.services.github_source_pipeline_service import GithubSourcePipelineService
from app.services.google_user_services import (
    build_drive_service_for_user,
    build_email_service_for_user,
)
from app.services.job_match_service import JobMatchService
from app.services.job_status_service import JobStatusService
from app.services.resume_generation_service import ResumeGenerationService
from app.services.resume_pdf_service import ResumePdfService


def build_github_source_pipeline_service(
    *,
    db: Session,
    settings: Settings,
    user_id,
    api_base_url: str,
) -> GithubSourcePipelineService:
    job_repository = JobPostingRepository(db)
    job_match_repository = JobMatchRepository(db)
    generated_resume_repository = GeneratedResumeRepository(db)
    status_service = JobStatusService(
        status_repository=JobStatusRepository(db),
        history_repository=JobStatusHistoryRepository(db),
        job_repository=job_repository,
    )

    return GithubSourcePipelineService(
        scan_service=GithubJobSourceService(
            source_repository=GithubJobSourceRepository(db),
            job_repository=job_repository,
            scan_run_repository=GithubScanRunRepository(db),
            status_service=status_service,
        ),
        match_service=JobMatchService(
            job_match_repository,
            job_repository=job_repository,
        ),
        resume_generation_service=ResumeGenerationService(
            generated_resume_repository=generated_resume_repository,
            job_repository=job_repository,
            job_match_repository=job_match_repository,
            resume_template_repository=ResumeTemplateRepository(db),
            education_repository=EducationRepository(db),
            experience_repository=ExperienceRepository(db),
            project_repository=ProjectRepository(db),
            skill_repository=SkillRepository(db),
        ),
        pdf_service=ResumePdfService(generated_resume_repository),
        generated_resume_repository=generated_resume_repository,
        digest_service=DigestService(
            repository=DigestRepository(db),
            email_service=build_email_service_for_user(
                settings=settings,
                google_integration_repository=GoogleIntegrationRepository(db),
                user_id=user_id,
            ),
            api_base_url=api_base_url,
        ),
        settings=settings,
        drive_service=build_drive_service_for_user(
            settings=settings,
            google_integration_repository=GoogleIntegrationRepository(db),
            user_id=user_id,
        ),
        status_service=status_service,
    )
