from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_id
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.github_job_source_repository import GithubJobSourceRepository
from app.repositories.github_scan_run_repository import GithubScanRunRepository
from app.repositories.job_posting_repository import JobPostingRepository
from app.repositories.job_status_history_repository import JobStatusHistoryRepository
from app.repositories.job_status_repository import JobStatusRepository
from app.schemas.github_job_source import (
    GithubJobSourceCreate,
    GithubJobSourceRead,
    GithubJobSourceScanResult,
    GithubScanRunRead,
    GithubSourcePipelineResult,
    GithubJobSourceUpdate,
)
from app.services.github_job_source_service import (
    DisabledGithubSourceError,
    GithubJobSourceService,
    GithubSourceScanError,
)
from app.services.github_pipeline_factory import build_github_source_pipeline_service
from app.services.job_status_service import JobStatusService

router = APIRouter(prefix="/github-sources", tags=["github sources"])


@router.get("", response_model=list[GithubJobSourceRead])
def list_github_sources(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[GithubJobSourceRead]:
    repository = GithubJobSourceRepository(db)
    return repository.list_by_user(user_id)


@router.post(
    "",
    response_model=GithubJobSourceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_github_source(
    payload: GithubJobSourceCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> GithubJobSourceRead:
    repository = GithubJobSourceRepository(db)
    return repository.create(user_id, payload.model_dump())


@router.put("/{source_id}", response_model=GithubJobSourceRead)
def update_github_source(
    source_id: UUID,
    payload: GithubJobSourceUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> GithubJobSourceRead:
    repository = GithubJobSourceRepository(db)
    source = repository.get_for_user(user_id, source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub source not found.",
        )

    return repository.update(source, payload.model_dump(exclude_unset=True))


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_github_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    repository = GithubJobSourceRepository(db)
    source = repository.get_for_user(user_id, source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub source not found.",
        )

    repository.delete(source)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{source_id}/scan", response_model=GithubJobSourceScanResult)
def scan_github_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> GithubJobSourceScanResult:
    repository = GithubJobSourceRepository(db)
    source = repository.get_for_user(user_id, source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub source not found.",
        )

    service = GithubJobSourceService(
        source_repository=repository,
        job_repository=JobPostingRepository(db),
        scan_run_repository=GithubScanRunRepository(db),
        status_service=_status_service(db),
    )
    try:
        result = service.scan_source(source)
    except DisabledGithubSourceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except GithubSourceScanError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return GithubJobSourceScanResult(
        source=GithubJobSourceRead.model_validate(result.source),
        scan_run=GithubScanRunRead.model_validate(result.scan_run),
        total_rows_seen=result.total_rows_seen,
        parsed_jobs=result.parsed_jobs,
        scanned_jobs=result.scanned_jobs,
        inserted_jobs=result.inserted_jobs,
        duplicate_jobs=result.duplicate_jobs,
        rows_skipped_by_filters=result.rows_skipped_by_filters,
        jobs_tagged=result.jobs_tagged,
        extraction_success_count=result.extraction_success_count,
        extraction_failed_count=result.extraction_failed_count,
        matched_jobs=result.matched_jobs,
        generated_resumes=result.generated_resumes,
        uploaded_pdfs=result.uploaded_pdfs,
        message=result.message,
    )


@router.post("/{source_id}/run-pipeline", response_model=GithubSourcePipelineResult)
def run_github_source_pipeline(
    source_id: UUID,
    request: Request,
    min_match_score: int = Query(default=70, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> GithubSourcePipelineResult:
    source_repository = GithubJobSourceRepository(db)
    source = source_repository.get_for_user(current_user.id, source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub source not found.",
        )

    pipeline_service = build_github_source_pipeline_service(
        db=db,
        settings=settings,
        user_id=current_user.id,
        api_base_url=f"{str(request.base_url).rstrip('/')}{settings.api_prefix}",
    )
    try:
        result = pipeline_service.run(
            source=source,
            user=current_user,
            min_match_score=min_match_score,
        )
    except DisabledGithubSourceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except GithubSourceScanError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return GithubSourcePipelineResult(
        total_rows_seen=result.total_rows_seen,
        parsed_jobs=result.parsed_jobs,
        rows_skipped_by_filters=result.rows_skipped_by_filters,
        inserted_jobs=result.inserted_jobs,
        duplicate_jobs=result.duplicate_jobs,
        jobs_tagged=result.jobs_tagged,
        extraction_success_count=result.extraction_success_count,
        extraction_failed_count=result.extraction_failed_count,
        jobs_matched=result.jobs_matched,
        resumes_generated=result.resumes_generated,
        pdfs_compiled=result.pdfs_compiled,
        drive_uploads_successful=result.drive_uploads_successful,
        emails_sent=result.emails_sent,
        duration_seconds=result.duration_seconds,
        errors=result.errors,
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
