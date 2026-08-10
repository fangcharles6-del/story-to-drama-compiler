"""Add durable asynchronous provider execution state."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    op.add_column("runs", sa.Column("provider_profile", postgresql.JSONB(), nullable=True))
    columns = (
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("request_fingerprint", sa.String(64), nullable=True),
        sa.Column("provider_task_id", sa.String(), nullable=True),
        sa.Column("provider_state", sa.String(), nullable=True),
        sa.Column("attempt_state", sa.String(), nullable=True),
        sa.Column("failure_class", sa.String(), nullable=True),
        sa.Column("usage_tokens", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("artifact_sha256", sa.String(64), nullable=True),
    )
    for column in columns:
        op.add_column("generation_attempts", column)
    op.create_unique_constraint(
        "uq_attempt_provider_task", "generation_attempts", ["provider", "provider_task_id"]
    )
    op.add_column("artifacts", sa.Column("sha256", sa.String(64), nullable=True))
    op.add_column("artifacts", sa.Column("size_bytes", sa.Integer(), nullable=True))
    op.add_column("artifacts", sa.Column("ffprobe", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    for name in ("ffprobe", "size_bytes", "sha256"):
        op.drop_column("artifacts", name)
    op.drop_constraint("uq_attempt_provider_task", "generation_attempts", type_="unique")
    for name in (
        "artifact_sha256",
        "downloaded_at",
        "last_observed_at",
        "submitted_at",
        "usage_tokens",
        "failure_class",
        "attempt_state",
        "provider_state",
        "provider_task_id",
        "request_fingerprint",
        "model",
        "provider",
    ):
        op.drop_column("generation_attempts", name)
    op.drop_column("runs", "provider_profile")
