"""Add durable one-use live provider authorizations."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    op.create_table(
        "live_authorization_uses",
        sa.Column("authorization_id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("capability_snapshot_sha256", sa.String(64), nullable=False),
        sa.Column("pricing_snapshot_sha256", sa.String(64), nullable=False),
        sa.Column("max_cost_cny", sa.Numeric(18, 6), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("live_authorization_uses")
