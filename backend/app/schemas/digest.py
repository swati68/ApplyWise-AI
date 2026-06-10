from datetime import datetime

from pydantic import BaseModel


class DigestSendResponse(BaseModel):
    success: bool
    recipient_email: str
    item_count: int
    sent_at: datetime | None = None
    error_message: str | None = None
