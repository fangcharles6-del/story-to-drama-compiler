"""Initial run, event, and artifact records."""

from alembic import op

from sdc.persistence import Base

revision = "0001"
down_revision = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
