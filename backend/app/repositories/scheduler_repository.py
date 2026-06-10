from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduler import (
    SchedulerRun,
    SchedulerRunStatus,
    SchedulerTriggerType,
    UserSchedulerPreference,
)


class UserSchedulerPreferenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user(self, user_id: UUID) -> UserSchedulerPreference | None:
        statement = select(UserSchedulerPreference).where(
            UserSchedulerPreference.user_id == user_id,
        )
        return self.db.scalar(statement)

    def get_or_create_for_user(self, user_id: UUID) -> UserSchedulerPreference:
        preference = self.get_by_user(user_id)
        if preference is not None:
            return preference

        preference = UserSchedulerPreference(user_id=user_id)
        self.db.add(preference)
        self.db.commit()
        self.db.refresh(preference)
        return preference

    def list_enabled(self) -> list[UserSchedulerPreference]:
        statement = (
            select(UserSchedulerPreference)
            .where(UserSchedulerPreference.enabled.is_(True))
            .order_by(UserSchedulerPreference.updated_at.asc())
        )
        return list(self.db.scalars(statement))

    def update(
        self,
        preference: UserSchedulerPreference,
        values: dict[str, object],
    ) -> UserSchedulerPreference:
        for field, value in values.items():
            setattr(preference, field, value)

        self.db.commit()
        self.db.refresh(preference)
        return preference


class SchedulerRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_running_by_user(self, user_id: UUID) -> SchedulerRun | None:
        statement = select(SchedulerRun).where(
            SchedulerRun.user_id == user_id,
            SchedulerRun.status == SchedulerRunStatus.RUNNING,
        )
        return self.db.scalar(statement)

    def list_recent_by_user(self, user_id: UUID, limit: int = 20) -> list[SchedulerRun]:
        statement = (
            select(SchedulerRun)
            .where(SchedulerRun.user_id == user_id)
            .order_by(SchedulerRun.started_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement))

    def has_run_between(
        self,
        *,
        user_id: UUID,
        trigger_type: SchedulerTriggerType,
        started_from: datetime,
        started_to: datetime,
    ) -> bool:
        statement = select(SchedulerRun.id).where(
            SchedulerRun.user_id == user_id,
            SchedulerRun.trigger_type == trigger_type,
            SchedulerRun.started_at >= started_from,
            SchedulerRun.started_at < started_to,
        )
        return self.db.scalar(statement) is not None

    def create(self, values: dict[str, object]) -> SchedulerRun:
        run = SchedulerRun(**values)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def update(self, run: SchedulerRun, values: dict[str, object]) -> SchedulerRun:
        for field, value in values.items():
            setattr(run, field, value)

        self.db.commit()
        self.db.refresh(run)
        return run
