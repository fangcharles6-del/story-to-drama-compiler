"""Bind live authorization claims to reviewed evidence and immutable runtime policy."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"


_COLUMNS = (
    sa.Column("authorization_document_type", sa.String(64), nullable=True),
    sa.Column("authorization_sha256", sa.String(64), nullable=True),
    sa.Column("evidence_bound_plan_sha256", sa.String(64), nullable=True),
    sa.Column("execution_sha256", sa.String(64), nullable=True),
    sa.Column("submission_policy_sha256", sa.String(64), nullable=True),
    sa.Column("runtime_policy_sha256", sa.String(64), nullable=True),
    sa.Column("runtime_release_sha256", sa.String(64), nullable=True),
    sa.Column("evidence_bundle_id", sa.String(64), nullable=True),
    sa.Column("evidence_logical_tree_sha256", sa.String(64), nullable=True),
    sa.Column("evidence_valid_until", sa.DateTime(timezone=True), nullable=True),
    sa.Column("entitlement_anchor_sha256", sa.String(64), nullable=True),
    sa.Column("entitlement_valid_until", sa.DateTime(timezone=True), nullable=True),
    sa.Column("provider_region", sa.String(32), nullable=True),
    sa.Column("task_queue", sa.String(128), nullable=True),
    sa.Column("ledger_id", sa.String(128), nullable=True),
    sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("nonce_sha256", sa.String(64), nullable=True),
    sa.Column("claim_state", sa.String(32), nullable=True),
)


def upgrade() -> None:
    for column in _COLUMNS:
        op.add_column("live_authorization_uses", column)
    op.create_check_constraint(
        "ck_live_auth_evidence_bound_complete",
        "live_authorization_uses",
        "(authorization_document_type IS NULL AND authorization_sha256 IS NULL AND "
        "evidence_bound_plan_sha256 IS NULL AND execution_sha256 IS NULL AND "
        "submission_policy_sha256 IS NULL AND runtime_policy_sha256 IS NULL AND "
        "runtime_release_sha256 IS NULL AND evidence_bundle_id IS NULL AND "
        "evidence_logical_tree_sha256 IS NULL AND evidence_valid_until IS NULL AND "
        "entitlement_anchor_sha256 IS NULL AND entitlement_valid_until IS NULL AND "
        "provider_region IS NULL AND task_queue IS NULL AND ledger_id IS NULL AND "
        "authorized_at IS NULL AND expires_at IS NULL AND nonce_sha256 IS NULL AND "
        "claim_state IS NULL) OR ("
        "authorization_document_type IS NOT NULL AND "
        "authorization_document_type = 'sdc.evidence-bound-live-authorization' AND "
        "authorization_sha256 IS NOT NULL AND evidence_bound_plan_sha256 IS NOT NULL AND "
        "execution_sha256 IS NOT NULL AND submission_policy_sha256 IS NOT NULL AND "
        "runtime_policy_sha256 IS NOT NULL AND runtime_release_sha256 IS NOT NULL AND "
        "evidence_bundle_id IS NOT NULL AND evidence_logical_tree_sha256 IS NOT NULL AND "
        "evidence_valid_until IS NOT NULL AND entitlement_anchor_sha256 IS NOT NULL AND "
        "entitlement_valid_until IS NOT NULL AND provider_region IS NOT NULL AND "
        "provider_region = 'cn-beijing' AND "
        "task_queue IS NOT NULL AND ledger_id IS NOT NULL AND authorized_at IS NOT NULL AND "
        "expires_at IS NOT NULL AND nonce_sha256 IS NOT NULL AND claim_state IS NOT NULL AND "
        "claim_state = 'POST_IN_FLIGHT' "
        "AND attempt = 1 AND max_cost_cny > 0 AND max_cost_cny <= 15 "
        "AND authorized_at < expires_at AND expires_at <= evidence_valid_until "
        "AND expires_at <= entitlement_valid_until"
        "))",
    )
    op.create_index(
        "uq_live_auth_authorization_sha256",
        "live_authorization_uses",
        ["authorization_sha256"],
        unique=True,
        postgresql_where=sa.text("authorization_sha256 IS NOT NULL"),
    )
    op.create_index(
        "uq_live_auth_evidence_bound_plan",
        "live_authorization_uses",
        ["evidence_bound_plan_sha256"],
        unique=True,
        postgresql_where=sa.text("evidence_bound_plan_sha256 IS NOT NULL"),
    )
    op.create_index(
        "uq_live_auth_nonce_sha256",
        "live_authorization_uses",
        ["nonce_sha256"],
        unique=True,
        postgresql_where=sa.text("nonce_sha256 IS NOT NULL"),
    )
    op.create_index(
        "uq_live_auth_evidence_bound_attempt",
        "live_authorization_uses",
        ["run_id", "job_id", "attempt"],
        unique=True,
        postgresql_where=sa.text(
            "authorization_document_type = 'sdc.evidence-bound-live-authorization'"
        ),
    )
    op.execute(
        """
        CREATE FUNCTION sdc_reject_live_authorization_use_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'live_authorization_uses is append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_live_authorization_uses_append_only
        BEFORE UPDATE OR DELETE ON live_authorization_uses
        FOR EACH ROW EXECUTE FUNCTION sdc_reject_live_authorization_use_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_live_authorization_uses_no_truncate
        BEFORE TRUNCATE ON live_authorization_uses
        FOR EACH STATEMENT EXECUTE FUNCTION sdc_reject_live_authorization_use_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM live_authorization_uses
                WHERE authorization_document_type = 'sdc.evidence-bound-live-authorization'
            ) THEN
                RAISE EXCEPTION
                    'cannot downgrade 0007 while an evidence-bound authorization claim exists';
            END IF;
        END;
        $$
        """
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_live_authorization_uses_no_truncate "
        "ON live_authorization_uses"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_live_authorization_uses_append_only ON live_authorization_uses"
    )
    op.execute("DROP FUNCTION IF EXISTS sdc_reject_live_authorization_use_mutation()")
    for name in (
        "uq_live_auth_evidence_bound_attempt",
        "uq_live_auth_nonce_sha256",
        "uq_live_auth_evidence_bound_plan",
        "uq_live_auth_authorization_sha256",
    ):
        op.drop_index(name, table_name="live_authorization_uses")
    op.drop_constraint(
        "ck_live_auth_evidence_bound_complete",
        "live_authorization_uses",
        type_="check",
    )
    for column in reversed(_COLUMNS):
        op.drop_column("live_authorization_uses", column.name)
