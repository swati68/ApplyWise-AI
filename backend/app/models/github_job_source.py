from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GithubJobSource(Base):
    __tablename__ = "github_job_sources"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_github_job_sources_name_not_empty",
        ),
        CheckConstraint(
            "length(btrim(repo_url)) > 0",
            name="ck_github_job_sources_repo_url_not_empty",
        ),
        CheckConstraint(
            "length(btrim(raw_readme_url)) > 0",
            name="ck_github_job_sources_raw_readme_url_not_empty",
        ),
        CheckConstraint(
            "length(btrim(branch)) > 0",
            name="ck_github_job_sources_branch_not_empty",
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    raw_readme_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    scan_role_tags: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    include_keywords: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    exclude_keywords: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    scan_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
