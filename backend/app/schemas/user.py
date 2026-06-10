from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthUserRead(UserRead):
    identity_connected: bool = False
    drive_connected: bool = False
    gmail_send_connected: bool = False
    automation_ready: bool = False
