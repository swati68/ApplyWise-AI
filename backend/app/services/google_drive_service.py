from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable

from app.core.config import PROJECT_ROOT, Settings


DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"


class GoogleDriveConfigurationError(Exception):
    pass


class GoogleDriveUploadError(Exception):
    pass


@dataclass(frozen=True)
class GoogleDriveUploadResult:
    file_id: str
    drive_url: str
    folder_id: str | None


class GoogleDriveService:
    def __init__(
        self,
        settings: Settings,
        *,
        credentials: object | None = None,
        default_folder_id: str | None = None,
        drive_client: object | None = None,
        media_upload_factory: Callable[[Path], object] | None = None,
    ) -> None:
        self.settings = settings
        self.credentials = credentials
        self.default_folder_id = default_folder_id
        self.drive_client = drive_client
        self.media_upload_factory = media_upload_factory or _build_media_upload

    def upload_pdf(
        self,
        *,
        pdf_path: Path,
        file_name: str,
        folder_id: str | None = None,
    ) -> GoogleDriveUploadResult:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF does not exist: {pdf_path}")

        selected_folder_id = (
            _clean_optional_text(folder_id)
            or _clean_optional_text(self.default_folder_id)
            or _clean_optional_text(
                self.settings.google_drive_folder_id,
            )
        )
        metadata: dict[str, object] = {
            "name": file_name,
            "mimeType": "application/pdf",
        }
        if selected_folder_id is not None:
            metadata["parents"] = [selected_folder_id]

        try:
            response = (
                self._drive_client()
                .files()
                .create(
                    body=metadata,
                    media_body=self.media_upload_factory(pdf_path),
                    fields="id, webViewLink, webContentLink",
                )
                .execute()
            )
        except GoogleDriveConfigurationError:
            raise
        except Exception as error:
            raise GoogleDriveUploadError(f"Google Drive upload failed: {error}") from error

        file_id = _clean_optional_text(response.get("id") if isinstance(response, dict) else None)
        if file_id is None:
            raise GoogleDriveUploadError("Google Drive upload did not return a file id.")

        drive_url = _clean_optional_text(
            response.get("webViewLink") if isinstance(response, dict) else None,
        ) or _clean_optional_text(
            response.get("webContentLink") if isinstance(response, dict) else None,
        )
        if drive_url is None:
            drive_url = f"https://drive.google.com/file/d/{file_id}/view"

        return GoogleDriveUploadResult(
            file_id=file_id,
            drive_url=drive_url,
            folder_id=selected_folder_id,
        )

    def _drive_client(self) -> object:
        if self.drive_client is not None:
            return self.drive_client

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as error:
            raise GoogleDriveConfigurationError(
                "Google Drive dependencies are not installed. Run `pip install -r requirements.txt`.",
            ) from error

        credentials = self.credentials
        if credentials is None:
            credentials = _build_service_account_credentials(
                settings=self.settings,
                service_account_module=service_account,
            )
        self.drive_client = build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )
        return self.drive_client


def is_google_drive_configured(settings: Settings) -> bool:
    return (
        _clean_optional_text(settings.google_drive_service_account_file) is not None
        or _clean_optional_text(settings.google_drive_service_account_json) is not None
    )


def _build_service_account_credentials(
    *,
    settings: Settings,
    service_account_module,
) -> object:
    service_account_file = _clean_optional_text(settings.google_drive_service_account_file)
    if service_account_file is not None:
        credential_path = _resolve_credential_path(service_account_file)
        if not credential_path.exists():
            raise GoogleDriveConfigurationError(
                f"Google Drive service account file was not found: {credential_path}",
            )

        return service_account_module.Credentials.from_service_account_file(
            str(credential_path),
            scopes=[DRIVE_FILE_SCOPE],
        )

    service_account_json = _clean_optional_text(settings.google_drive_service_account_json)
    if service_account_json is not None:
        try:
            credential_info = json.loads(service_account_json)
        except json.JSONDecodeError as error:
            raise GoogleDriveConfigurationError(
                "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON is not valid JSON.",
            ) from error

        return service_account_module.Credentials.from_service_account_info(
            credential_info,
            scopes=[DRIVE_FILE_SCOPE],
        )

    raise GoogleDriveConfigurationError(
        "Google Drive is not configured. Set GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE "
        "or GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON in .env.",
    )


def _build_media_upload(pdf_path: Path) -> object:
    from googleapiclient.http import MediaFileUpload

    return MediaFileUpload(
        str(pdf_path),
        mimetype="application/pdf",
        resumable=False,
    )


def _resolve_credential_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned_value = value.strip()
    return cleaned_value or None
