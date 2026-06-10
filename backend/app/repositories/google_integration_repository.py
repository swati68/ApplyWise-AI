from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.google_integration import GoogleIntegration


class GoogleIntegrationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user(self, user_id: UUID) -> GoogleIntegration | None:
        statement = select(GoogleIntegration).where(GoogleIntegration.user_id == user_id)
        return self.db.scalar(statement)

    def create(self, values: dict[str, object]) -> GoogleIntegration:
        integration = GoogleIntegration(**values)
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def update(
        self,
        integration: GoogleIntegration,
        values: dict[str, object],
    ) -> GoogleIntegration:
        for field, value in values.items():
            setattr(integration, field, value)

        self.db.commit()
        self.db.refresh(integration)
        return integration

    def upsert_for_user(
        self,
        *,
        user_id: UUID,
        values: dict[str, object],
    ) -> GoogleIntegration:
        integration = self.get_by_user(user_id)
        if integration is None:
            return self.create({"user_id": user_id, **values})

        return self.update(integration, values)
