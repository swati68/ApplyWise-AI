"""create github job sources table

Revision ID: 202605190001
Revises: 202605180003
Create Date: 2026-05-19 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202605190001"
down_revision: str | None = "202605180003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "github_job_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("repo_url", sa.String(length=2048), nullable=False),
        sa.Column("raw_readme_url", sa.String(length=2048), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_github_job_sources_name_not_empty",
        ),
        sa.CheckConstraint(
            "length(btrim(repo_url)) > 0",
            name="ck_github_job_sources_repo_url_not_empty",
        ),
        sa.CheckConstraint(
            "length(btrim(raw_readme_url)) > 0",
            name="ck_github_job_sources_raw_readme_url_not_empty",
        ),
        sa.CheckConstraint(
            "length(btrim(branch)) > 0",
            name="ck_github_job_sources_branch_not_empty",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_github_job_sources_user_id"),
        "github_job_sources",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_github_job_sources_user_id"), table_name="github_job_sources")
    op.drop_table("github_job_sources")
