from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GithubScanRun(Base):
    __tablename__ = "github_scan_runs"

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
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("github_job_sources.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    scanned_jobs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inserted_jobs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_jobs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_skipped_by_filters: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_tagged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extraction_success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extraction_failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
