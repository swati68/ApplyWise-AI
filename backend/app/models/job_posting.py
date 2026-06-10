from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobSource(str, Enum):
    MANUAL = "manual"
    GITHUB = "github"


class JobStatus(str, Enum):
    NEW = "new"
    MATCHED = "matched"
    RESUME_GENERATED = "resume_generated"
    EMAILED = "emailed"
    ARCHIVED = "archived"
    APPLIED = "applied"


class JobExtractionStatus(str, Enum):
    NOT_STARTED = "not_started"
    SUCCESS = "success"
    FAILED = "failed"


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (
        Index(
            "uq_job_postings_user_job_url",
            "user_id",
            "job_url",
            unique=True,
            postgresql_where=text("job_url IS NOT NULL AND btrim(job_url) <> ''"),
        ),
        Index(
            "uq_job_postings_user_content_hash",
            "user_id",
            "content_hash",
            unique=True,
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
        nullable=False,
    )
    github_source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("github_job_sources.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    current_status_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("job_statuses.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    source: Mapped[JobSource] = mapped_column(
        SqlEnum(
            JobSource,
            name="job_source",
            values_callable=lambda enum_values: [item.value for item in enum_values],
        ),
        nullable=False,
    )
    source_repo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_raw_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    external_job_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_section: Mapped[str | None] = mapped_column(String(512), nullable=True)
    job_tags: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    scan_match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[JobExtractionStatus] = mapped_column(
        SqlEnum(
            JobExtractionStatus,
            name="job_extraction_status",
            values_callable=lambda enum_values: [item.value for item in enum_values],
        ),
        default=JobExtractionStatus.NOT_STARTED,
        server_default=JobExtractionStatus.NOT_STARTED.value,
        nullable=False,
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        SqlEnum(
            JobStatus,
            name="job_status",
            values_callable=lambda enum_values: [item.value for item in enum_values],
        ),
        default=JobStatus.NEW,
        server_default=JobStatus.NEW.value,
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
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
