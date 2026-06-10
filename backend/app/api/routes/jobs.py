from uuid import UUID
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.job_posting import JobExtractionStatus
from app.repositories.generated_resume_repository import GeneratedResumeRepository
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.repositories.github_job_source_repository import GithubJobSourceRepository
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
from app.schemas.generated_resume import GeneratedResumeRead
from app.schemas.github_job_source import GithubJobSourceRead
from app.schemas.job_match import JobMatchRead
from app.schemas.job_posting import (
    GeneratedResumeSummaryRead,
    JobPostingCreateResult,
    JobPostingRead,
    JobPostingUpdate,
    ManualJobDriveStatus,
    ManualJobCreate,
    ManualJobGenerateRequest,
    ManualJobGenerateResult,
    ManualJobPdfStatus,
    JobExtractionResultRead,
)
from app.schemas.job_status import JobStatusChangeRequest, JobStatusHistoryRead, JobStatusRead
from app.services.jobs.job_content_extractor import JobContentExtractorService
from app.services.job_match_service import JobMatchService, LowMatchScoreError
from app.services.job_service import DuplicateJobPostingError, JobPostingService
from app.services.job_status_service import JobStatusService
from app.services.google_user_services import build_drive_service_for_user
from app.services.manual_job_pipeline_service import (
    DriveUploadPipelineResult,
    ManualJobPipelineResult,
    ManualJobPipelineService,
)
from app.services.resume_generation_service import (
    NoDefaultResumeTemplateError,
    ResumeGenerationBlockedError,
    ResumeGenerationService,
)
from app.services.resume_pdf_service import PdfCompileResult, ResumePdfService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobPostingRead])
def list_jobs(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[JobPostingRead]:
    repository = JobPostingRepository(db)
    status_service = _status_service(db, repository)
    jobs = [
        status_service.ensure_job_current_status(job)
        for job in repository.list_by_user(user_id)
    ]
    return [_build_job_read(job, db=db) for job in jobs]


@router.post(
    "/manual",
    response_model=JobPostingCreateResult,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_job(
    payload: ManualJobCreate,
    response: Response,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobPostingCreateResult:
    job_repository = JobPostingRepository(db)
    service = JobPostingService(
        job_repository,
        status_service=_status_service(db, job_repository),
    )
    result = service.create_manual_job(user_id=user_id, payload=payload)
    if result.duplicate:
        response.status_code = status.HTTP_200_OK

    return JobPostingCreateResult(
        job=_build_job_read(result.job, db=db),
        duplicate=result.duplicate,
        message=result.message,
    )


@router.post("/manual/generate", response_model=ManualJobGenerateResult)
def generate_manual_job_from_url(
    payload: ManualJobGenerateRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
) -> ManualJobGenerateResult:
    job_repository = JobPostingRepository(db)
    generated_resume_repository = GeneratedResumeRepository(db)
    job_match_repository = JobMatchRepository(db)
    service = ManualJobPipelineService(
        job_repository=job_repository,
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
        generated_resume_repository=generated_resume_repository,
        pdf_service=ResumePdfService(generated_resume_repository),
        settings=settings,
        drive_service=build_drive_service_for_user(
            settings=settings,
            google_integration_repository=GoogleIntegrationRepository(db),
            user_id=user_id,
        ),
        status_service=_status_service(db, job_repository),
    )
    result = service.run(user_id=user_id, job_url=payload.job_url)
    return _manual_job_generate_result_from_service(
        result,
        job_read=_build_job_read(result.job, db=db),
    )


@router.post("/{job_id}/match", response_model=JobMatchRead)
def match_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobMatchRead:
    job_repository = JobPostingRepository(db)
    job = job_repository.get_for_user(user_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found.",
        )

    service = JobMatchService(
        JobMatchRepository(db),
        job_repository=job_repository,
    )
    try:
        match = service.match_job(user_id=user_id, job=job)
    except LowMatchScoreError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    if not match.match_reason.startswith("Skipped matching"):
        _status_service(db, job_repository).set_status_by_name(
            job=job,
            name="Matched",
            note="Manual match analysis completed.",
        )
    return match


@router.post(
    "/{job_id}/generate-resume",
    response_model=GeneratedResumeRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_resume_for_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> GeneratedResumeRead:
    job_repository = JobPostingRepository(db)
    job = job_repository.get_for_user(user_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found.",
        )

    service = ResumeGenerationService(
        generated_resume_repository=GeneratedResumeRepository(db),
        job_repository=job_repository,
        job_match_repository=JobMatchRepository(db),
        resume_template_repository=ResumeTemplateRepository(db),
        education_repository=EducationRepository(db),
        experience_repository=ExperienceRepository(db),
        project_repository=ProjectRepository(db),
        skill_repository=SkillRepository(db),
    )
    try:
        generated_resume = service.generate_for_job(user_id=user_id, job=job)
        _status_service(db, job_repository).set_status_by_name(
            job=job,
            name="Resume Generated",
            note="Tailored resume generated.",
        )
        return generated_resume
    except NoDefaultResumeTemplateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ResumeGenerationBlockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except LowMatchScoreError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post("/{job_id}/extract-description", response_model=JobPostingRead)
def extract_job_description(
    job_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobPostingRead:
    repository = JobPostingRepository(db)
    job = repository.get_for_user(user_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found.",
        )
    if job.job_url is None or job.job_url.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job posting does not have a URL to extract.",
        )

    extracted_content = JobContentExtractorService().extract_job_content(job.job_url)
    extraction_status = (
        JobExtractionStatus.SUCCESS
        if extracted_content.extraction_success
        else JobExtractionStatus.FAILED
    )
    values: dict[str, object] = {
        "extracted_description": extracted_content.cleaned_text or None,
        "extraction_status": extraction_status,
        "extraction_error": extracted_content.error_message,
        "extracted_at": datetime.now(UTC),
    }
    if extracted_content.posted_at is not None:
        values["posted_at"] = extracted_content.posted_at

    updated_job = repository.update(job, values)
    return _build_job_read(updated_job, db=db)


@router.get("/{job_id}", response_model=JobPostingRead)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobPostingRead:
    repository = JobPostingRepository(db)
    job = repository.get_for_user(user_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found.",
        )

    ensured_job = _status_service(db, repository).ensure_job_current_status(job)
    return _build_job_read(ensured_job, db=db)


@router.put("/{job_id}", response_model=JobPostingRead)
def update_job(
    job_id: UUID,
    payload: JobPostingUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobPostingRead:
    repository = JobPostingRepository(db)
    job = repository.get_for_user(user_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found.",
        )

    service = JobPostingService(repository)
    try:
        updated_job = service.update_job(
            job=job,
            values=payload.model_dump(exclude_unset=True),
        )
        return _build_job_read(updated_job, db=db)
    except DuplicateJobPostingError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "A duplicate job posting already exists.",
                "duplicate_job_id": str(error.job.id),
            },
        ) from error


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    repository = JobPostingRepository(db)
    job = repository.get_for_user(user_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found.",
        )

    repository.delete(job)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{job_id}/status-history", response_model=list[JobStatusHistoryRead])
def get_job_status_history(
    job_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[JobStatusHistoryRead]:
    job_repository = JobPostingRepository(db)
    job = job_repository.get_for_user(user_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found.",
        )

    status_repository = JobStatusRepository(db)
    statuses_by_id = {
        job_status.id: job_status
        for job_status in status_repository.list_by_user(user_id)
    }
    history_repository = JobStatusHistoryRepository(db)
    return [
        _build_status_history_read(history, statuses_by_id)
        for history in history_repository.list_for_job(user_id, job_id)
    ]


@router.post("/{job_id}/status", response_model=JobPostingRead)
def change_job_status(
    job_id: UUID,
    payload: JobStatusChangeRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobPostingRead:
    job_repository = JobPostingRepository(db)
    job = job_repository.get_for_user(user_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found.",
        )

    status_repository = JobStatusRepository(db)
    next_status = status_repository.get_for_user(user_id, payload.status_id)
    if next_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job status not found.",
        )

    result = _status_service(db, job_repository).change_status(
        job=job,
        status=next_status,
        note=payload.note,
    )
    return _build_job_read(result.job, db=db)


def _manual_job_generate_result_from_service(
    result: ManualJobPipelineResult,
    *,
    job_read: JobPostingRead,
) -> ManualJobGenerateResult:
    return ManualJobGenerateResult(
        job=job_read,
        extraction_result=JobExtractionResultRead(
            cleaned_text=result.extraction_result.cleaned_text,
            page_title=result.extraction_result.page_title,
            company_guess=result.extraction_result.company_guess,
            title_guess=result.extraction_result.title_guess,
            location_guess=result.extraction_result.location_guess,
            posted_at=result.extraction_result.posted_at,
            extraction_success=result.extraction_result.extraction_success,
            extraction_method=result.extraction_result.extraction_method,
            error_message=result.extraction_result.error_message,
        ),
        match_result=(
            JobMatchRead.model_validate(result.match_result)
            if result.match_result is not None
            else None
        ),
        generated_resume_result=(
            GeneratedResumeRead.model_validate(result.generated_resume_result)
            if result.generated_resume_result is not None
            else None
        ),
        pdf_status=_manual_pdf_status(result.pdf_result),
        drive_status=_manual_drive_status(result.drive_result),
        duplicate=result.duplicate,
        errors=result.errors,
    )


def _manual_pdf_status(result: PdfCompileResult | None) -> ManualJobPdfStatus | None:
    if result is None:
        return None

    skipped = result.success and result.compiler is None
    return ManualJobPdfStatus(
        attempted=not skipped,
        success=result.success,
        skipped=skipped,
        pdf_path=result.pdf_path,
        download_url=result.download_url,
        compiler=result.compiler,
        error_message=result.error_message,
    )


def _manual_drive_status(
    result: DriveUploadPipelineResult | None,
) -> ManualJobDriveStatus | None:
    if result is None:
        return None

    return ManualJobDriveStatus(
        attempted=result.attempted,
        success=result.success,
        skipped=result.skipped,
        drive_url=result.drive_url,
        error_message=result.error_message,
    )


def _status_service(
    db: Session,
    job_repository: JobPostingRepository | None = None,
) -> JobStatusService:
    return JobStatusService(
        status_repository=JobStatusRepository(db),
        history_repository=JobStatusHistoryRepository(db),
        job_repository=job_repository,
    )


def _build_job_read(job, *, db: Session) -> JobPostingRead:
    status_repository = JobStatusRepository(db)
    current_status = (
        status_repository.get_for_user(job.user_id, job.current_status_id)
        if job.current_status_id is not None
        else None
    )
    github_source = (
        GithubJobSourceRepository(db).get_for_user(job.user_id, job.github_source_id)
        if job.github_source_id is not None
        else None
    )
    latest_match = JobMatchRepository(db).get_latest_for_job(job.user_id, job.id)
    latest_generated_resume = GeneratedResumeRepository(db).get_latest_for_job(
        job.user_id,
        job.id,
    )

    return JobPostingRead.model_validate(job).model_copy(
        update={
            "current_status": (
                JobStatusRead.model_validate(current_status)
                if current_status is not None
                else None
            ),
            "github_source": (
                GithubJobSourceRead.model_validate(github_source)
                if github_source is not None
                else None
            ),
            "latest_match": (
                JobMatchRead.model_validate(latest_match)
                if latest_match is not None
                else None
            ),
            "latest_generated_resume": (
                GeneratedResumeSummaryRead.model_validate(latest_generated_resume)
                if latest_generated_resume is not None
                else None
            ),
        },
    )


def _build_status_history_read(
    history,
    statuses_by_id,
) -> JobStatusHistoryRead:
    from_status = (
        statuses_by_id.get(history.from_status_id)
        if history.from_status_id is not None
        else None
    )
    to_status = statuses_by_id.get(history.to_status_id)
    if to_status is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Status history references a missing status.",
        )

    return JobStatusHistoryRead(
        id=history.id,
        user_id=history.user_id,
        job_id=history.job_id,
        from_status_id=history.from_status_id,
        to_status_id=history.to_status_id,
        note=history.note,
        changed_at=history.changed_at,
        from_status=(
            JobStatusRead.model_validate(from_status)
            if from_status is not None
            else None
        ),
        to_status=JobStatusRead.model_validate(to_status),
    )
