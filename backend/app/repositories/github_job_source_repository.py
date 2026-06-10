from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.github_job_source import GithubJobSource


class GithubJobSourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: UUID) -> list[GithubJobSource]:
        statement = (
            select(GithubJobSource)
            .where(GithubJobSource.user_id == user_id)
            .order_by(GithubJobSource.enabled.desc(), GithubJobSource.updated_at.desc())
        )
        return list(self.db.scalars(statement))

    def list_enabled_by_user(self, user_id: UUID) -> list[GithubJobSource]:
        statement = (
            select(GithubJobSource)
            .where(
                GithubJobSource.user_id == user_id,
                GithubJobSource.enabled.is_(True),
            )
            .order_by(GithubJobSource.updated_at.desc())
        )
        return list(self.db.scalars(statement))

    def get_for_user(
        self,
        user_id: UUID,
        source_id: UUID,
    ) -> GithubJobSource | None:
        statement = select(GithubJobSource).where(
            GithubJobSource.user_id == user_id,
            GithubJobSource.id == source_id,
        )
        return self.db.scalar(statement)

    def create(self, user_id: UUID, values: dict[str, object]) -> GithubJobSource:
        source = GithubJobSource(user_id=user_id, **values)
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def update(
        self,
        source: GithubJobSource,
        values: dict[str, object],
    ) -> GithubJobSource:
        for field, value in values.items():
            setattr(source, field, value)

        self.db.commit()
        self.db.refresh(source)
        return source

    def mark_scanned(
        self,
        source: GithubJobSource,
        scanned_at: datetime,
    ) -> GithubJobSource:
        source.last_scanned_at = scanned_at
        self.db.commit()
        self.db.refresh(source)
        return source

    def delete(self, source: GithubJobSource) -> None:
        self.db.delete(source)
        self.db.commit()
