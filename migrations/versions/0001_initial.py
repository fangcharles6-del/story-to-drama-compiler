"""Initial run, event, and artifact records.

The ArtifactRecord metadata creates a PostgreSQL partial unique index on job_id where
is_current=true. Unlike a (job_id, is_current) constraint, this permits any number of historical
is_current=false candidates while enforcing exactly one current row at the database boundary.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("state", sa.String(), nullable=False),
    )
    op.create_table(
        "run_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False, unique=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False, unique=True),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "uq_artifacts_one_current_per_job",
        "artifacts",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("run_events")
    op.drop_table("runs")
