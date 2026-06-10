"""create github scan runs table

Revision ID: 202605190003
Revises: 202605190002
Create Date: 2026-05-19 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202605190003"
down_revision: str | None = "202605190002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "github_scan_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scanned_jobs_count", sa.Integer(), nullable=False),
        sa.Column("inserted_jobs_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_jobs_count", sa.Integer(), nullable=False),
        sa.Column("extraction_success_count", sa.Integer(), nullable=False),
        sa.Column("extraction_failed_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["github_job_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_github_scan_runs_source_id"),
        "github_scan_runs",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_github_scan_runs_user_id"),
        "github_scan_runs",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_github_scan_runs_user_id"), table_name="github_scan_runs")
    op.drop_index(op.f("ix_github_scan_runs_source_id"), table_name="github_scan_runs")
    op.drop_table("github_scan_runs")
