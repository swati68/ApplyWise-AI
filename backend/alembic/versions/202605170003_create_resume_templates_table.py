"""create resume templates table

Revision ID: 202605170003
Revises: 202605170002
Create Date: 2026-05-17 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202605170003"
down_revision: str | None = "202605170002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resume_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("latex_content", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(latex_content)) > 0",
            name="ck_resume_templates_latex_content_not_empty",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_resume_templates_user_id"),
        "resume_templates",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "uq_resume_templates_one_default_per_user",
        "resume_templates",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_resume_templates_one_default_per_user",
        table_name="resume_templates",
    )
    op.drop_index(op.f("ix_resume_templates_user_id"), table_name="resume_templates")
    op.drop_table("resume_templates")
