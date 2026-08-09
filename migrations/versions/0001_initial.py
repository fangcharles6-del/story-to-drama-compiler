"""Initial run, event, and artifact records.

The ArtifactRecord metadata creates a PostgreSQL partial unique index on job_id where
is_current=true. Unlike a (job_id, is_current) constraint, this permits any number of historical
is_current=false candidates while enforcing exactly one current row at the database boundary.
"""

from alembic import op

from sdc.persistence import Base

revision = "0001"
down_revision = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
