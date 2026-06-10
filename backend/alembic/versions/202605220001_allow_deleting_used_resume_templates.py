"""allow deleting used resume templates

Revision ID: 202605220001
Revises: 202605210001
Create Date: 2026-05-22 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202605220001"
down_revision: str | None = "202605210001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "generated_resumes_resume_template_id_fkey",
        "generated_resumes",
        type_="foreignkey",
    )
    op.alter_column(
        "generated_resumes",
        "resume_template_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        "generated_resumes_resume_template_id_fkey",
        "generated_resumes",
        "resume_templates",
        ["resume_template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "generated_resumes_resume_template_id_fkey",
        "generated_resumes",
        type_="foreignkey",
    )
    op.alter_column(
        "generated_resumes",
        "resume_template_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        "generated_resumes_resume_template_id_fkey",
        "generated_resumes",
        "resume_templates",
        ["resume_template_id"],
        ["id"],
        ondelete="RESTRICT",
    )
