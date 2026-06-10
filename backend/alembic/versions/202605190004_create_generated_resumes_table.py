"""create generated resumes table

Revision ID: 202605190004
Revises: 202605190003
Create Date: 2026-05-19 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202605190004"
down_revision: str | None = "202605190003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generated_resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tailored_latex", sa.Text(), nullable=False),
        sa.Column(
            "selected_experiences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "selected_projects",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "selected_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "change_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "safety_warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("pdf_path", sa.String(length=2048), nullable=True),
        sa.Column("drive_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["resume_template_id"],
            ["resume_templates.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generated_resumes_job_id"),
        "generated_resumes",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_resumes_resume_template_id"),
        "generated_resumes",
        ["resume_template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_resumes_user_id"),
        "generated_resumes",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_generated_resumes_user_id"),
        table_name="generated_resumes",
    )
    op.drop_index(
        op.f("ix_generated_resumes_resume_template_id"),
        table_name="generated_resumes",
    )
    op.drop_index(
        op.f("ix_generated_resumes_job_id"),
        table_name="generated_resumes",
    )
    op.drop_table("generated_resumes")
