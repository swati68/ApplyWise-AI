"""create scheduler tables

Revision ID: 202606100001
Revises: 202605250001
Create Date: 2026-06-10 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202606100001"
down_revision: str | None = "202605250001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


trigger_type_enum = postgresql.ENUM(
    "manual",
    "scheduled_morning",
    "scheduled_evening",
    name="scheduler_trigger_type",
    create_type=False,
)
run_status_enum = postgresql.ENUM(
    "running",
    "success",
    "partial_success",
    "failed",
    name="scheduler_run_status",
    create_type=False,
)


def upgrade() -> None:
    trigger_type_enum.create(op.get_bind(), checkfirst=True)
    run_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_scheduler_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "timezone",
            sa.String(length=128),
            server_default="America/New_York",
            nullable=False,
        ),
        sa.Column(
            "morning_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "morning_time",
            sa.Time(),
            server_default="08:00",
            nullable=False,
        ),
        sa.Column(
            "evening_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "evening_time",
            sa.Time(),
            server_default="18:00",
            nullable=False,
        ),
        sa.Column(
            "min_match_score",
            sa.Integer(),
            server_default="50",
            nullable=False,
        ),
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
            "min_match_score >= 0 AND min_match_score <= 100",
            name="ck_user_scheduler_preferences_min_match_score_range",
        ),
        sa.CheckConstraint(
            "length(btrim(timezone)) > 0",
            name="ck_user_scheduler_preferences_timezone_not_empty",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_scheduler_preferences_user_id"),
    )
    op.create_index(
        op.f("ix_user_scheduler_preferences_user_id"),
        "user_scheduler_preferences",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "scheduler_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_type", trigger_type_enum, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            run_status_enum,
            server_default="running",
            nullable=False,
        ),
        sa.Column("total_sources", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sources_succeeded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sources_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("jobs_scanned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("jobs_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duplicates_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("jobs_matched", sa.Integer(), server_default="0", nullable=False),
        sa.Column("resumes_generated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pdfs_compiled", sa.Integer(), server_default="0", nullable=False),
        sa.Column("drive_uploads", sa.Integer(), server_default="0", nullable=False),
        sa.Column("emails_sent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scheduler_runs_user_id"),
        "scheduler_runs",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduler_runs_user_id"), table_name="scheduler_runs")
    op.drop_table("scheduler_runs")
    op.drop_index(
        op.f("ix_user_scheduler_preferences_user_id"),
        table_name="user_scheduler_preferences",
    )
    op.drop_table("user_scheduler_preferences")
    run_status_enum.drop(op.get_bind(), checkfirst=True)
    trigger_type_enum.drop(op.get_bind(), checkfirst=True)
