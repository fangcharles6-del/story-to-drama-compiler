"""Persist provider attempt reservations and candidate attempt numbers."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.add_column(
        "artifacts", sa.Column("attempt", sa.Integer(), server_default="1", nullable=False)
    )
    op.alter_column("artifacts", "attempt", server_default=None)
    op.create_table(
        "generation_attempts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.UniqueConstraint("job_id", "attempt"),
    )


def downgrade() -> None:
    op.drop_table("generation_attempts")
    op.drop_column("artifacts", "attempt")
