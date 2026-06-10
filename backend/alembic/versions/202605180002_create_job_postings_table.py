"""create job postings table

Revision ID: 202605180002
Revises: 202605180001
Create Date: 2026-05-18 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202605180002"
down_revision: str | None = "202605180001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


job_source_enum = postgresql.ENUM(
    "manual",
    "github",
    name="job_source",
    create_type=False,
)
job_status_enum = postgresql.ENUM(
    "new",
    "matched",
    "resume_generated",
    "emailed",
    "archived",
    "applied",
    name="job_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    job_source_enum.create(bind, checkfirst=True)
    job_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", job_source_enum, nullable=False),
        sa.Column("source_repo_url", sa.String(length=2048), nullable=True),
        sa.Column("source_raw_url", sa.String(length=2048), nullable=True),
        sa.Column("external_job_id", sa.String(length=512), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("job_url", sa.String(length=2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            job_status_enum,
            server_default="new",
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_postings_user_id"),
        "job_postings",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "uq_job_postings_user_content_hash",
        "job_postings",
        ["user_id", "content_hash"],
        unique=True,
    )
    op.create_index(
        "uq_job_postings_user_job_url",
        "job_postings",
        ["user_id", "job_url"],
        unique=True,
        postgresql_where=sa.text("job_url IS NOT NULL AND btrim(job_url) <> ''"),
    )


def downgrade() -> None:
    op.drop_index("uq_job_postings_user_job_url", table_name="job_postings")
    op.drop_index("uq_job_postings_user_content_hash", table_name="job_postings")
    op.drop_index(op.f("ix_job_postings_user_id"), table_name="job_postings")
    op.drop_table("job_postings")

    bind = op.get_bind()
    job_status_enum.drop(bind, checkfirst=True)
    job_source_enum.drop(bind, checkfirst=True)
