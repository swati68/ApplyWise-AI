from datetime import datetime, time
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Time, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SchedulerTriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULED_MORNING = "scheduled_morning"
    SCHEDULED_EVENING = "scheduled_evening"


class SchedulerRunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class UserSchedulerPreference(Base):
    __tablename__ = "user_scheduler_preferences"
    __table_args__ = (
        CheckConstraint(
            "min_match_score >= 0 AND min_match_score <= 100",
            name="ck_user_scheduler_preferences_min_match_score_range",
        ),
        CheckConstraint(
            "length(btrim(timezone)) > 0",
            name="ck_user_scheduler_preferences_timezone_not_empty",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        unique=True,
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(128),
        default="America/New_York",
        server_default="America/New_York",
        nullable=False,
    )
    morning_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    morning_time: Mapped[time] = mapped_column(
        Time(),
        default=time(8, 0),
        server_default="08:00",
        nullable=False,
    )
    evening_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    evening_time: Mapped[time] = mapped_column(
        Time(),
        default=time(18, 0),
        server_default="18:00",
        nullable=False,
    )
    min_match_score: Mapped[int] = mapped_column(
        Integer,
        default=50,
        server_default="50",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SchedulerRun(Base):
    __tablename__ = "scheduler_runs"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    trigger_type: Mapped[SchedulerTriggerType] = mapped_column(
        SqlEnum(
            SchedulerTriggerType,
            name="scheduler_trigger_type",
            values_callable=lambda enum_values: [item.value for item in enum_values],
        ),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[SchedulerRunStatus] = mapped_column(
        SqlEnum(
            SchedulerRunStatus,
            name="scheduler_run_status",
            values_callable=lambda enum_values: [item.value for item in enum_values],
        ),
        default=SchedulerRunStatus.RUNNING,
        server_default=SchedulerRunStatus.RUNNING.value,
        nullable=False,
    )
    total_sources: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_succeeded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_matched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resumes_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pdfs_compiled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    drive_uploads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    summary: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
