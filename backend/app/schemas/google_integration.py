from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GoogleIntegrationStatusRead(BaseModel):
    user_id: UUID
    google_sub: str | None = None
    email: str | None = None
    identity_connected: bool
    drive_connected: bool
    gmail_send_connected: bool
    automation_ready: bool
    granted_scopes: list[str]
    drive_folder_id: str | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
