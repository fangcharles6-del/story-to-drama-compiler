"""Scope all durable provider state and idempotency to a runtime run."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.add_column("artifacts", sa.Column("run_id", sa.String(), nullable=True))
    # Existing rows predate runtime run identity. Their owning run cannot be inferred safely;
    # discard them rather than incorrectly associating durable provider output.
    op.execute("DELETE FROM artifacts")
    op.alter_column("artifacts", "run_id", nullable=False)
    op.create_foreign_key("fk_artifacts_run_id_runs", "artifacts", "runs", ["run_id"], ["id"])

    op.drop_constraint("run_events_idempotency_key_key", "run_events", type_="unique")
    op.create_unique_constraint(
        "uq_run_events_run_id_idempotency_key", "run_events", ["run_id", "idempotency_key"]
    )
    op.drop_constraint("artifacts_idempotency_key_key", "artifacts", type_="unique")
    op.create_unique_constraint(
        "uq_artifacts_run_id_idempotency_key", "artifacts", ["run_id", "idempotency_key"]
    )
    op.drop_constraint(
        "generation_attempts_job_id_attempt_key", "generation_attempts", type_="unique"
    )
    op.create_unique_constraint(
        "uq_generation_attempts_run_job_attempt",
        "generation_attempts",
        ["run_id", "job_id", "attempt"],
    )
    op.drop_index("uq_artifacts_one_current_per_job", table_name="artifacts")
    op.create_index(
        "uq_artifacts_one_current_per_job",
        "artifacts",
        ["run_id", "job_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_artifacts_one_current_per_job", table_name="artifacts")
    op.create_index(
        "uq_artifacts_one_current_per_job",
        "artifacts",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.drop_constraint(
        "uq_generation_attempts_run_job_attempt", "generation_attempts", type_="unique"
    )
    op.create_unique_constraint(
        "generation_attempts_job_id_attempt_key", "generation_attempts", ["job_id", "attempt"]
    )
    op.drop_constraint("uq_artifacts_run_id_idempotency_key", "artifacts", type_="unique")
    op.create_unique_constraint("artifacts_idempotency_key_key", "artifacts", ["idempotency_key"])
    op.drop_constraint("uq_run_events_run_id_idempotency_key", "run_events", type_="unique")
    op.create_unique_constraint("run_events_idempotency_key_key", "run_events", ["idempotency_key"])
    op.drop_constraint("fk_artifacts_run_id_runs", "artifacts", type_="foreignkey")
    op.drop_column("artifacts", "run_id")
