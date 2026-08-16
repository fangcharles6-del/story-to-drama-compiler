"""Add the atomic evidence-bound Canary claim ledger."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"


_ATTEMPT_COLUMNS = (
    sa.Column("evidence_authorization_id", sa.String(128), nullable=True),
    sa.Column("evidence_authorization_sha256", sa.String(64), nullable=True),
    sa.Column("evidence_runtime_release_sha256", sa.String(64), nullable=True),
    sa.Column("evidence_runtime_policy_sha256", sa.String(64), nullable=True),
    sa.Column("evidence_task_queue", sa.String(128), nullable=True),
    sa.Column("evidence_ledger_id", sa.String(128), nullable=True),
    sa.Column("evidence_deployment_id", sa.String(128), nullable=True),
    sa.Column("evidence_claim_event_id", sa.String(), nullable=True),
    sa.Column("evidence_acceptance_event_id", sa.String(), nullable=True),
    sa.Column("evidence_claimed_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("evidence_claim_state", sa.String(32), nullable=True),
)

_ATTEMPT_CLAIM_CHECK = (
    "(evidence_authorization_id IS NULL AND "
    "evidence_authorization_sha256 IS NULL AND "
    "evidence_runtime_release_sha256 IS NULL AND "
    "evidence_runtime_policy_sha256 IS NULL AND "
    "evidence_task_queue IS NULL AND evidence_ledger_id IS NULL AND "
    "evidence_deployment_id IS NULL AND evidence_claim_event_id IS NULL AND "
    "evidence_acceptance_event_id IS NULL AND "
    "evidence_claimed_at IS NULL AND evidence_claim_state IS NULL AND "
    "attempt_state IS DISTINCT FROM 'POST_IN_FLIGHT') OR ("
    "evidence_authorization_id IS NOT NULL AND "
    "evidence_authorization_sha256 IS NOT NULL AND "
    "evidence_runtime_release_sha256 IS NOT NULL AND "
    "evidence_runtime_policy_sha256 IS NOT NULL AND "
    "evidence_task_queue IS NOT NULL AND evidence_ledger_id IS NOT NULL AND "
    "evidence_deployment_id IS NOT NULL AND evidence_claim_event_id IS NOT NULL AND "
    "evidence_claimed_at IS NOT NULL AND evidence_claim_state IS NOT NULL AND "
    "evidence_claim_state = 'POST_IN_FLIGHT' AND attempt = 1 AND "
    "provider IS NOT NULL AND provider = 'volcengine_ark' AND "
    "model IS NOT NULL AND model = 'doubao-seedance-2-0-260128' AND "
    "request_fingerprint IS NOT NULL AND request_fingerprint ~ '^[0-9a-f]{64}$' AND "
    "attempt_state IS NOT NULL AND ((provider_task_id IS NULL AND submitted_at IS NULL AND "
    "evidence_acceptance_event_id IS NULL AND "
    "attempt_state IN ('POST_IN_FLIGHT', 'SUBMISSION_UNKNOWN', 'HUMAN_GATE')) OR ("
    "provider_task_id IS NOT NULL AND submitted_at IS NOT NULL AND "
    "evidence_acceptance_event_id IS NOT NULL AND "
    "attempt_state IN ('SUBMITTED', 'WATCHING', 'DOWNLOADING', 'VERIFIED', 'FAILED', "
    "'SUBMISSION_UNKNOWN', 'HUMAN_GATE')))"
    ")"
)


def upgrade() -> None:
    op.create_table(
        "canary_runtime_identity",
        sa.Column("singleton_id", sa.SmallInteger(), primary_key=True, autoincrement=False),
        sa.Column("ledger_id", sa.String(128), nullable=False),
        sa.Column("deployment_id", sa.String(128), nullable=False),
        sa.Column("runtime_release_sha256", sa.String(64), nullable=False),
        sa.Column("runtime_policy_sha256", sa.String(64), nullable=False),
        sa.Column("task_queue", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("region", sa.String(32), nullable=False),
        sa.Column("operation", sa.String(128), nullable=False),
        sa.Column("claim_to_socket_max_ms", sa.Integer(), nullable=False),
        sa.Column("expiry_guard_band_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "singleton_id = 1",
            name="ck_canary_runtime_identity_singleton",
        ),
        sa.CheckConstraint(
            "provider = 'volcengine_ark' AND "
            "model = 'doubao-seedance-2-0-260128' AND "
            "region = 'cn-beijing' AND "
            "operation = 'contents.generations.tasks.create'",
            name="ck_canary_runtime_identity_route",
        ),
        sa.CheckConstraint(
            "runtime_release_sha256 ~ '^[0-9a-f]{64}$' AND "
            "runtime_policy_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_canary_runtime_identity_digests",
        ),
        sa.CheckConstraint(
            "ledger_id ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$' AND "
            "deployment_id ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$' AND "
            "task_queue ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'",
            name="ck_canary_runtime_identity_names",
        ),
        sa.CheckConstraint(
            "claim_to_socket_max_ms = 10000 AND expiry_guard_band_ms = 30000",
            name="ck_canary_runtime_identity_deadlines",
        ),
        sa.UniqueConstraint("ledger_id", name="uq_canary_runtime_identity_ledger"),
        sa.UniqueConstraint("deployment_id", name="uq_canary_runtime_identity_deployment"),
    )

    for column in _ATTEMPT_COLUMNS:
        op.add_column("generation_attempts", column)
    op.create_foreign_key(
        "fk_attempt_evidence_authorization_id",
        "generation_attempts",
        "live_authorization_uses",
        ["evidence_authorization_id"],
        ["authorization_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_foreign_key(
        "fk_attempt_evidence_claim_event_id",
        "generation_attempts",
        "run_events",
        ["evidence_claim_event_id"],
        ["id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_foreign_key(
        "fk_attempt_evidence_acceptance_event_id",
        "generation_attempts",
        "run_events",
        ["evidence_acceptance_event_id"],
        ["id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_check_constraint(
        "ck_attempt_evidence_bound_claim_complete",
        "generation_attempts",
        _ATTEMPT_CLAIM_CHECK,
    )
    op.create_index(
        "uq_attempt_evidence_authorization_id",
        "generation_attempts",
        ["evidence_authorization_id"],
        unique=True,
        postgresql_where=sa.text("evidence_authorization_id IS NOT NULL"),
    )
    op.create_index(
        "uq_attempt_evidence_authorization_sha256",
        "generation_attempts",
        ["evidence_authorization_sha256"],
        unique=True,
        postgresql_where=sa.text("evidence_authorization_sha256 IS NOT NULL"),
    )

    op.execute(
        """
        CREATE FUNCTION sdc_reject_canary_runtime_identity_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'canary_runtime_identity is append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_canary_runtime_identity_append_only
        BEFORE UPDATE OR DELETE ON canary_runtime_identity
        FOR EACH ROW EXECUTE FUNCTION sdc_reject_canary_runtime_identity_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_canary_runtime_identity_no_truncate
        BEFORE TRUNCATE ON canary_runtime_identity
        FOR EACH STATEMENT EXECUTE FUNCTION sdc_reject_canary_runtime_identity_mutation()
        """
    )

    op.execute(
        """
        CREATE FUNCTION sdc_protect_evidence_bound_attempt()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.evidence_authorization_id IS NOT NULL OR
                   OLD.evidence_authorization_sha256 IS NOT NULL OR
                   OLD.evidence_runtime_release_sha256 IS NOT NULL OR
                   OLD.evidence_runtime_policy_sha256 IS NOT NULL OR
                   OLD.evidence_task_queue IS NOT NULL OR
                   OLD.evidence_ledger_id IS NOT NULL OR
                   OLD.evidence_deployment_id IS NOT NULL OR
                   OLD.evidence_claim_event_id IS NOT NULL OR
                   OLD.evidence_acceptance_event_id IS NOT NULL OR
                   OLD.evidence_claimed_at IS NOT NULL OR
                   OLD.evidence_claim_state IS NOT NULL OR
                   OLD.attempt_state = 'POST_IN_FLIGHT' THEN
                    RAISE EXCEPTION 'evidence-bound generation attempt cannot be deleted';
                END IF;
                RETURN OLD;
            END IF;
            IF (
                OLD.evidence_authorization_id IS NOT NULL OR
                OLD.evidence_authorization_sha256 IS NOT NULL OR
                OLD.evidence_runtime_release_sha256 IS NOT NULL OR
                OLD.evidence_runtime_policy_sha256 IS NOT NULL OR
                OLD.evidence_task_queue IS NOT NULL OR
                OLD.evidence_ledger_id IS NOT NULL OR
                OLD.evidence_deployment_id IS NOT NULL OR
                OLD.evidence_claim_event_id IS NOT NULL OR
                OLD.evidence_acceptance_event_id IS NOT NULL OR
                OLD.evidence_claimed_at IS NOT NULL OR
                OLD.evidence_claim_state IS NOT NULL OR
                OLD.attempt_state = 'POST_IN_FLIGHT' OR
                NEW.evidence_authorization_id IS NOT NULL OR
                NEW.evidence_authorization_sha256 IS NOT NULL OR
                NEW.evidence_runtime_release_sha256 IS NOT NULL OR
                NEW.evidence_runtime_policy_sha256 IS NOT NULL OR
                NEW.evidence_task_queue IS NOT NULL OR
                NEW.evidence_ledger_id IS NOT NULL OR
                NEW.evidence_deployment_id IS NOT NULL OR
                NEW.evidence_claim_event_id IS NOT NULL OR
                NEW.evidence_acceptance_event_id IS NOT NULL OR
                NEW.evidence_claimed_at IS NOT NULL OR
                NEW.evidence_claim_state IS NOT NULL OR
                NEW.attempt_state = 'POST_IN_FLIGHT'
            ) AND (
                NEW.id IS DISTINCT FROM OLD.id OR
                NEW.run_id IS DISTINCT FROM OLD.run_id OR
                NEW.job_id IS DISTINCT FROM OLD.job_id OR
                NEW.attempt IS DISTINCT FROM OLD.attempt OR
                NEW.provider IS DISTINCT FROM OLD.provider OR
                NEW.model IS DISTINCT FROM OLD.model OR
                NEW.request_fingerprint IS DISTINCT FROM OLD.request_fingerprint OR
                NEW.evidence_authorization_id IS DISTINCT FROM OLD.evidence_authorization_id OR
                NEW.evidence_authorization_sha256 IS DISTINCT FROM
                    OLD.evidence_authorization_sha256 OR
                NEW.evidence_runtime_release_sha256 IS DISTINCT FROM
                    OLD.evidence_runtime_release_sha256 OR
                NEW.evidence_runtime_policy_sha256 IS DISTINCT FROM
                    OLD.evidence_runtime_policy_sha256 OR
                NEW.evidence_task_queue IS DISTINCT FROM OLD.evidence_task_queue OR
                NEW.evidence_ledger_id IS DISTINCT FROM OLD.evidence_ledger_id OR
                NEW.evidence_deployment_id IS DISTINCT FROM OLD.evidence_deployment_id OR
                NEW.evidence_claim_event_id IS DISTINCT FROM OLD.evidence_claim_event_id OR
                NEW.evidence_claimed_at IS DISTINCT FROM OLD.evidence_claimed_at OR
                NEW.evidence_claim_state IS DISTINCT FROM OLD.evidence_claim_state OR
                (
                    OLD.evidence_acceptance_event_id IS NOT NULL AND
                    NEW.evidence_acceptance_event_id IS DISTINCT FROM
                        OLD.evidence_acceptance_event_id
                ) OR
                (
                    OLD.provider_task_id IS NOT NULL AND
                    NEW.provider_task_id IS DISTINCT FROM OLD.provider_task_id
                ) OR
                (
                    OLD.submitted_at IS NOT NULL AND
                    NEW.submitted_at IS DISTINCT FROM OLD.submitted_at
                )
            ) THEN
                RAISE EXCEPTION 'evidence-bound generation attempt identity is immutable';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_evidence_bound_attempt_identity
        BEFORE UPDATE OR DELETE ON generation_attempts
        FOR EACH ROW EXECUTE FUNCTION sdc_protect_evidence_bound_attempt()
        """
    )
    op.execute(
        """
        CREATE FUNCTION sdc_reject_evidence_bound_attempt_truncate()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM generation_attempts
                WHERE evidence_authorization_id IS NOT NULL
                   OR evidence_authorization_sha256 IS NOT NULL
                   OR evidence_runtime_release_sha256 IS NOT NULL
                   OR evidence_runtime_policy_sha256 IS NOT NULL
                   OR evidence_task_queue IS NOT NULL
                   OR evidence_ledger_id IS NOT NULL
                   OR evidence_deployment_id IS NOT NULL
                   OR evidence_claim_event_id IS NOT NULL
                   OR evidence_acceptance_event_id IS NOT NULL
                   OR evidence_claimed_at IS NOT NULL
                   OR evidence_claim_state IS NOT NULL
                   OR attempt_state = 'POST_IN_FLIGHT'
            ) THEN
                RAISE EXCEPTION 'generation_attempts contains evidence-bound claim state';
            END IF;
            RETURN NULL;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_evidence_bound_attempt_no_truncate
        BEFORE TRUNCATE ON generation_attempts
        FOR EACH STATEMENT EXECUTE FUNCTION sdc_reject_evidence_bound_attempt_truncate()
        """
    )

    op.execute(
        """
        CREATE FUNCTION sdc_reject_run_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'run_events is append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_run_events_append_only
        BEFORE UPDATE OR DELETE ON run_events
        FOR EACH ROW EXECUTE FUNCTION sdc_reject_run_event_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_run_events_no_truncate
        BEFORE TRUNCATE ON run_events
        FOR EACH STATEMENT EXECUTE FUNCTION sdc_reject_run_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE canary_runtime_identity, generation_attempts, "
        "live_authorization_uses, run_events IN ACCESS EXCLUSIVE MODE"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM canary_runtime_identity) OR EXISTS (
                SELECT 1 FROM generation_attempts
                WHERE evidence_authorization_id IS NOT NULL
                   OR evidence_authorization_sha256 IS NOT NULL
                   OR evidence_runtime_release_sha256 IS NOT NULL
                   OR evidence_runtime_policy_sha256 IS NOT NULL
                   OR evidence_task_queue IS NOT NULL
                   OR evidence_ledger_id IS NOT NULL
                   OR evidence_deployment_id IS NOT NULL
                   OR evidence_claim_event_id IS NOT NULL
                   OR evidence_acceptance_event_id IS NOT NULL
                   OR evidence_claimed_at IS NOT NULL
                   OR evidence_claim_state IS NOT NULL
                   OR attempt_state = 'POST_IN_FLIGHT'
            ) OR EXISTS (
                SELECT 1 FROM live_authorization_uses
                WHERE authorization_document_type =
                    'sdc.evidence-bound-live-authorization'
            ) OR EXISTS (
                SELECT 1 FROM run_events
                WHERE event_type IN (
                    'provider.evidence_bound_claimed',
                    'provider.evidence_bound_submission_accepted'
                )
            ) THEN
                RAISE EXCEPTION
                    'cannot downgrade 0008 while evidence-bound Canary ledger state exists';
            END IF;
        END;
        $$
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trg_run_events_no_truncate ON run_events")
    op.execute("DROP TRIGGER IF EXISTS trg_run_events_append_only ON run_events")
    op.execute("DROP FUNCTION IF EXISTS sdc_reject_run_event_mutation()")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_evidence_bound_attempt_no_truncate ON generation_attempts"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_evidence_bound_attempt_identity ON generation_attempts")
    op.execute("DROP FUNCTION IF EXISTS sdc_reject_evidence_bound_attempt_truncate()")
    op.execute("DROP FUNCTION IF EXISTS sdc_protect_evidence_bound_attempt()")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_canary_runtime_identity_no_truncate ON canary_runtime_identity"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_canary_runtime_identity_append_only ON canary_runtime_identity"
    )
    op.execute("DROP FUNCTION IF EXISTS sdc_reject_canary_runtime_identity_mutation()")

    op.drop_index(
        "uq_attempt_evidence_authorization_sha256",
        table_name="generation_attempts",
    )
    op.drop_index(
        "uq_attempt_evidence_authorization_id",
        table_name="generation_attempts",
    )
    op.drop_constraint(
        "ck_attempt_evidence_bound_claim_complete",
        "generation_attempts",
        type_="check",
    )
    op.drop_constraint(
        "fk_attempt_evidence_acceptance_event_id",
        "generation_attempts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_attempt_evidence_claim_event_id",
        "generation_attempts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_attempt_evidence_authorization_id",
        "generation_attempts",
        type_="foreignkey",
    )
    for column in reversed(_ATTEMPT_COLUMNS):
        op.drop_column("generation_attempts", column.name)
    op.drop_table("canary_runtime_identity")
