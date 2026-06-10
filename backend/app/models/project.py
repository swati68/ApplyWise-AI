from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    bullets: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    links: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
    tags: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=False,
    )
