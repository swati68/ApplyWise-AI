from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.repositories.generated_resume_repository import GeneratedResumeRepository
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.schemas.generated_resume import (
    GeneratedResumeDriveUploadResult,
    GeneratedResumePdfCompileResult,
)
from app.services.google_drive_service import (
    GoogleDriveConfigurationError,
    GoogleDriveService,
    GoogleDriveUploadError,
)
from app.services.google_user_services import build_drive_service_for_user
from app.services.resume_pdf_service import (
    ResumePdfService,
    resolve_generated_resume_pdf_path,
)


router = APIRouter(prefix="/generated-resumes", tags=["generated-resumes"])


@router.post(
    "/{resume_id}/compile-pdf",
    response_model=GeneratedResumePdfCompileResult,
)
def compile_generated_resume_pdf(
    resume_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> GeneratedResumePdfCompileResult:
    repository = GeneratedResumeRepository(db)
    generated_resume = repository.get_for_user(user_id, resume_id)
    if generated_resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated resume not found.",
        )

    result = ResumePdfService(repository).compile_pdf(generated_resume)
    return GeneratedResumePdfCompileResult(
        success=result.success,
        resume_id=result.resume_id,
        pdf_path=result.pdf_path,
        download_url=result.download_url,
        compiler=result.compiler,
        logs=result.logs,
        error_message=result.error_message,
    )


@router.get("/{resume_id}/download")
def download_generated_resume_pdf(
    resume_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> FileResponse:
    generated_resume = GeneratedResumeRepository(db).get_for_user(user_id, resume_id)
    if generated_resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated resume not found.",
        )

    pdf_path = resolve_generated_resume_pdf_path(generated_resume)
    if pdf_path is None or not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated resume PDF has not been compiled yet.",
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"applywise-resume-{generated_resume.id}.pdf",
    )


@router.post(
    "/{resume_id}/upload-drive",
    response_model=GeneratedResumeDriveUploadResult,
)
def upload_generated_resume_to_drive(
    resume_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
) -> GeneratedResumeDriveUploadResult:
    repository = GeneratedResumeRepository(db)
    generated_resume = repository.get_for_user(user_id, resume_id)
    if generated_resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated resume not found.",
        )

    pdf_path = resolve_generated_resume_pdf_path(generated_resume)
    if pdf_path is None or not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Compile this generated resume PDF before uploading it to Google Drive.",
        )

    try:
        drive_service = build_drive_service_for_user(
            settings=settings,
            google_integration_repository=GoogleIntegrationRepository(db),
            user_id=user_id,
        ) or GoogleDriveService(settings)
        upload_result = drive_service.upload_pdf(
            pdf_path=pdf_path,
            file_name=f"applywise-resume-{generated_resume.id}.pdf",
        )
    except GoogleDriveConfigurationError as error:
        return GeneratedResumeDriveUploadResult(
            success=False,
            resume_id=generated_resume.id,
            error_message=str(error),
        )
    except GoogleDriveUploadError as error:
        return GeneratedResumeDriveUploadResult(
            success=False,
            resume_id=generated_resume.id,
            error_message=str(error),
        )

    updated_resume = repository.update(
        generated_resume,
        {"drive_url": upload_result.drive_url},
    )
    return GeneratedResumeDriveUploadResult(
        success=True,
        resume_id=updated_resume.id,
        drive_url=updated_resume.drive_url,
        drive_file_id=upload_result.file_id,
        folder_id=upload_result.folder_id,
        error_message=None,
    )
