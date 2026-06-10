from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobMatch(Base):
    __tablename__ = "job_matches"

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
    job_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    exact_skill_matches: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    fuzzy_skill_matches: Mapped[list[dict[str, object]]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    missing_skills: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    relevant_experiences: Mapped[list[dict[str, object]]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    relevant_projects: Mapped[list[dict[str, object]]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    match_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
