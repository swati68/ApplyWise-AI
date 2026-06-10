"""add custom job status tracking

Revision ID: 202605210001
Revises: 202605190004
Create Date: 2026-05-21 00:00:00.000000

"""
from collections.abc import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202605210001"
down_revision: str | None = "202605190004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEFAULT_STATUSES: tuple[tuple[str, str, int], ...] = (
    ("New", "#64748b", 10),
    ("Matched", "#2563eb", 20),
    ("Resume Generated", "#7c3aed", 30),
    ("Applied", "#059669", 40),
    ("Phone Screen", "#0891b2", 50),
    ("Interview 1", "#ea580c", 60),
    ("Interview 2", "#c2410c", 70),
    ("Offer", "#16a34a", 80),
    ("Rejected", "#dc2626", 90),
    ("Archived", "#71717a", 100),
)


LEGACY_STATUS_TO_DEFAULT_NAME: dict[str, str] = {
    "new": "New",
    "matched": "Matched",
    "resume_generated": "Resume Generated",
    "emailed": "Resume Generated",
    "applied": "Applied",
    "archived": "Archived",
}


def upgrade() -> None:
    op.create_table(
        "job_statuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
            name="ck_job_statuses_name_not_empty",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_statuses_user_id"),
        "job_statuses",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "uq_job_statuses_user_name",
        "job_statuses",
        ["user_id", "name"],
        unique=True,
    )

    op.add_column(
        "job_postings",
        sa.Column("github_source_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("current_status_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_job_postings_github_source_id"),
        "job_postings",
        ["github_source_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_postings_current_status_id"),
        "job_postings",
        ["current_status_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_job_postings_github_source_id_github_job_sources",
        "job_postings",
        "github_job_sources",
        ["github_source_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_job_postings_current_status_id_job_statuses",
        "job_postings",
        "job_statuses",
        ["current_status_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "job_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_status_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["from_status_id"], ["job_statuses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_status_id"], ["job_statuses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_status_history_from_status_id"),
        "job_status_history",
        ["from_status_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_status_history_job_id"),
        "job_status_history",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_status_history_to_status_id"),
        "job_status_history",
        ["to_status_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_status_history_user_id"),
        "job_status_history",
        ["user_id"],
        unique=False,
    )

    _seed_default_statuses()
    _backfill_job_statuses()
    _backfill_github_source_ids()


def downgrade() -> None:
    op.drop_index(op.f("ix_job_status_history_user_id"), table_name="job_status_history")
    op.drop_index(op.f("ix_job_status_history_to_status_id"), table_name="job_status_history")
    op.drop_index(op.f("ix_job_status_history_job_id"), table_name="job_status_history")
    op.drop_index(op.f("ix_job_status_history_from_status_id"), table_name="job_status_history")
    op.drop_table("job_status_history")

    op.drop_constraint(
        "fk_job_postings_current_status_id_job_statuses",
        "job_postings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_job_postings_github_source_id_github_job_sources",
        "job_postings",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_job_postings_current_status_id"), table_name="job_postings")
    op.drop_index(op.f("ix_job_postings_github_source_id"), table_name="job_postings")
    op.drop_column("job_postings", "current_status_id")
    op.drop_column("job_postings", "github_source_id")

    op.drop_index("uq_job_statuses_user_name", table_name="job_statuses")
    op.drop_index(op.f("ix_job_statuses_user_id"), table_name="job_statuses")
    op.drop_table("job_statuses")


def _seed_default_statuses() -> None:
    bind = op.get_bind()
    user_rows = bind.execute(sa.text("SELECT id FROM users")).mappings().all()
    for user_row in user_rows:
        for name, color, sort_order in DEFAULT_STATUSES:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO job_statuses (
                        id,
                        user_id,
                        name,
                        color,
                        sort_order,
                        is_default
                    )
                    VALUES (:id, :user_id, :name, :color, :sort_order, true)
                    ON CONFLICT (user_id, name) DO NOTHING
                    """
                ),
                {
                    "id": uuid4(),
                    "user_id": user_row["id"],
                    "name": name,
                    "color": color,
                    "sort_order": sort_order,
                },
            )


def _backfill_job_statuses() -> None:
    bind = op.get_bind()
    for legacy_status, status_name in LEGACY_STATUS_TO_DEFAULT_NAME.items():
        bind.execute(
            sa.text(
                """
                UPDATE job_postings AS jp
                SET current_status_id = js.id
                FROM job_statuses AS js
                WHERE js.user_id = jp.user_id
                  AND js.name = :status_name
                  AND jp.status = :legacy_status
                  AND jp.current_status_id IS NULL
                """
            ),
            {
                "status_name": status_name,
                "legacy_status": legacy_status,
            },
        )

    job_rows = bind.execute(
        sa.text(
            """
            SELECT id, user_id, current_status_id
            FROM job_postings
            WHERE current_status_id IS NOT NULL
            """
        )
    ).mappings().all()
    for job_row in job_rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO job_status_history (
                    id,
                    user_id,
                    job_id,
                    from_status_id,
                    to_status_id,
                    note
                )
                VALUES (
                    :id,
                    :user_id,
                    :job_id,
                    NULL,
                    :to_status_id,
                    'Initial status from legacy field.'
                )
                """
            ),
            {
                "id": uuid4(),
                "user_id": job_row["user_id"],
                "job_id": job_row["id"],
                "to_status_id": job_row["current_status_id"],
            },
        )


def _backfill_github_source_ids() -> None:
    op.execute(
        """
        UPDATE job_postings AS jp
        SET github_source_id = source_match.id
        FROM (
            SELECT DISTINCT ON (user_id, repo_url, raw_readme_url)
                id,
                user_id,
                repo_url,
                raw_readme_url
            FROM github_job_sources
            ORDER BY user_id, repo_url, raw_readme_url, updated_at DESC
        ) AS source_match
        WHERE jp.source = 'github'
          AND jp.user_id = source_match.user_id
          AND jp.source_repo_url = source_match.repo_url
          AND jp.source_raw_url = source_match.raw_readme_url
          AND jp.github_source_id IS NULL
        """
    )
