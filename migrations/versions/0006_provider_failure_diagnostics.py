"""Add bounded provider failure diagnostics to generation attempts."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade() -> None:
    op.add_column(
        "generation_attempts", sa.Column("provider_http_status", sa.Integer(), nullable=True)
    )
    op.add_column(
        "generation_attempts", sa.Column("provider_error_code", sa.String(128), nullable=True)
    )
    op.add_column(
        "generation_attempts",
        sa.Column("provider_request_id_hmac_sha256", sa.String(64), nullable=True),
    )
    op.add_column(
        "generation_attempts", sa.Column("provider_error_message", sa.String(256), nullable=True)
    )


def downgrade() -> None:
    for name in (
        "provider_error_message",
        "provider_request_id_hmac_sha256",
        "provider_error_code",
        "provider_http_status",
    ):
        op.drop_column("generation_attempts", name)
