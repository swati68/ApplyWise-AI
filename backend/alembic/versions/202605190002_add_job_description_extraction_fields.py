"""add job description extraction fields

Revision ID: 202605190002
Revises: 202605190001
Create Date: 2026-05-19 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202605190002"
down_revision: str | None = "202605190001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


job_extraction_status = sa.Enum(
    "not_started",
    "success",
    "failed",
    name="job_extraction_status",
)


def upgrade() -> None:
    job_extraction_status.create(op.get_bind(), checkfirst=True)
    op.add_column("job_postings", sa.Column("extracted_description", sa.Text(), nullable=True))
    op.add_column(
        "job_postings",
        sa.Column(
            "extraction_status",
            job_extraction_status,
            server_default="not_started",
            nullable=False,
        ),
    )
    op.add_column("job_postings", sa.Column("extraction_error", sa.Text(), nullable=True))
    op.add_column(
        "job_postings",
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_postings", "extracted_at")
    op.drop_column("job_postings", "extraction_error")
    op.drop_column("job_postings", "extraction_status")
    op.drop_column("job_postings", "extracted_description")
    job_extraction_status.drop(op.get_bind(), checkfirst=True)
