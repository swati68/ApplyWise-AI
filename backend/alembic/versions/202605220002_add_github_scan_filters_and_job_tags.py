"""add github scan filters and job tags

Revision ID: 202605220002
Revises: 202605220001
Create Date: 2026-05-22 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202605220002"
down_revision: str | None = "202605220001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "github_job_sources",
        sa.Column(
            "scan_role_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "github_job_sources",
        sa.Column(
            "include_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "github_job_sources",
        sa.Column(
            "exclude_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "github_job_sources",
        sa.Column("scan_instructions", sa.Text(), nullable=True),
    )

    op.add_column(
        "job_postings",
        sa.Column("source_section", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column(
            "job_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "job_postings",
        sa.Column("scan_match_reason", sa.Text(), nullable=True),
    )

    op.add_column(
        "github_scan_runs",
        sa.Column(
            "rows_skipped_by_filters",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "github_scan_runs",
        sa.Column("jobs_tagged", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("github_scan_runs", "jobs_tagged")
    op.drop_column("github_scan_runs", "rows_skipped_by_filters")
    op.drop_column("job_postings", "scan_match_reason")
    op.drop_column("job_postings", "job_tags")
    op.drop_column("job_postings", "source_section")
    op.drop_column("github_job_sources", "scan_instructions")
    op.drop_column("github_job_sources", "exclude_keywords")
    op.drop_column("github_job_sources", "include_keywords")
    op.drop_column("github_job_sources", "scan_role_tags")
