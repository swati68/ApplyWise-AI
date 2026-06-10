from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from app.core.config import Settings
from app.services.google_drive_service import (
    GoogleDriveConfigurationError,
    GoogleDriveService,
)


class GoogleDriveServiceTests(unittest.TestCase):
    def test_upload_pdf_sends_file_to_configured_folder_and_returns_drive_url(self) -> None:
        drive_client = FakeDriveClient(
            {
                "id": "drive-file-id",
                "webViewLink": "https://drive.google.com/file/d/drive-file-id/view",
            }
        )
        settings = Settings(
            google_drive_folder_id="configured-folder",
        )
        service = GoogleDriveService(
            settings,
            drive_client=drive_client,
            media_upload_factory=lambda path: SimpleNamespace(path=path),
        )

        with tempfile.TemporaryDirectory() as temp_dir_name:
            pdf_path = Path(temp_dir_name) / "resume.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")

            result = service.upload_pdf(
                pdf_path=pdf_path,
                file_name="resume.pdf",
            )

        self.assertEqual(result.file_id, "drive-file-id")
        self.assertEqual(
            result.drive_url,
            "https://drive.google.com/file/d/drive-file-id/view",
        )
        self.assertEqual(result.folder_id, "configured-folder")
        self.assertEqual(drive_client.created_body["parents"], ["configured-folder"])
        self.assertEqual(drive_client.created_body["mimeType"], "application/pdf")

    def test_upload_pdf_allows_explicit_folder_override(self) -> None:
        drive_client = FakeDriveClient({"id": "file-id"})
        service = GoogleDriveService(
            Settings(google_drive_folder_id="configured-folder"),
            drive_client=drive_client,
            media_upload_factory=lambda path: SimpleNamespace(path=path),
        )

        with tempfile.TemporaryDirectory() as temp_dir_name:
            pdf_path = Path(temp_dir_name) / "resume.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            result = service.upload_pdf(
                pdf_path=pdf_path,
                file_name="resume.pdf",
                folder_id="explicit-folder",
            )

        self.assertEqual(result.folder_id, "explicit-folder")
        self.assertEqual(drive_client.created_body["parents"], ["explicit-folder"])
        self.assertEqual(result.drive_url, "https://drive.google.com/file/d/file-id/view")

    def test_missing_pdf_is_not_uploaded(self) -> None:
        service = GoogleDriveService(
            Settings(),
            drive_client=FakeDriveClient({"id": "file-id"}),
        )

        with self.assertRaises(FileNotFoundError):
            service.upload_pdf(
                pdf_path=Path("/tmp/applywise-does-not-exist.pdf"),
                file_name="resume.pdf",
            )

    def test_missing_credentials_raise_configuration_error(self) -> None:
        service = GoogleDriveService(Settings())

        with self.assertRaises(GoogleDriveConfigurationError):
            service._drive_client()


class FakeDriveClient:
    def __init__(self, response: dict[str, str]) -> None:
        self.response = response
        self.created_body: dict[str, object] = {}

    def files(self):
        return self

    def create(self, *, body, media_body, fields):
        self.created_body = body
        return self

    def execute(self):
        return self.response


if __name__ == "__main__":
    unittest.main()
