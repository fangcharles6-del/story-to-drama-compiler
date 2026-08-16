"""PostgreSQL persistence models for durable runtime state.

The database is not the workflow engine, but it is the durable, queryable boundary used by
activities.  In particular, attempt reservations are unique so activity redelivery cannot turn
into an unrecorded third provider call.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False)
    provider_profile: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)


class EventRecord(Base):
    __tablename__ = "run_events"
    __table_args__ = (UniqueConstraint("run_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class ArtifactRecord(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("run_id", "idempotency_key"),
        Index(
            "uq_artifacts_one_current_per_job",
            "run_id",
            "job_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    is_current: Mapped[bool] = mapped_column(default=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ffprobe: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)


class AttemptRecord(Base):
    """A provider attempt reserved before the non-idempotent remote operation starts."""

    __tablename__ = "generation_attempts"
    __table_args__ = (
        UniqueConstraint("run_id", "job_id", "attempt"),
        UniqueConstraint("provider", "provider_task_id"),
        CheckConstraint(
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
            "evidence_claimed_at IS NOT NULL AND "
            "evidence_claim_state IS NOT NULL AND "
            "evidence_claim_state = 'POST_IN_FLIGHT' AND attempt = 1 AND "
            "provider IS NOT NULL AND provider = 'volcengine_ark' AND "
            "model IS NOT NULL AND model = 'doubao-seedance-2-0-260128' AND "
            "request_fingerprint IS NOT NULL AND "
            "request_fingerprint ~ '^[0-9a-f]{64}$' AND attempt_state IS NOT NULL AND ("
            "(provider_task_id IS NULL AND submitted_at IS NULL AND "
            "evidence_acceptance_event_id IS NULL AND "
            "attempt_state IN ('POST_IN_FLIGHT', 'SUBMISSION_UNKNOWN', 'HUMAN_GATE')) OR ("
            "provider_task_id IS NOT NULL AND submitted_at IS NOT NULL AND "
            "evidence_acceptance_event_id IS NOT NULL AND "
            "attempt_state IN ('SUBMITTED', 'WATCHING', 'DOWNLOADING', 'VERIFIED', "
            "'FAILED', 'SUBMISSION_UNKNOWN', 'HUMAN_GATE'))))",
            name="ck_attempt_evidence_bound_claim_complete",
        ),
        Index(
            "uq_attempt_evidence_authorization_id",
            "evidence_authorization_id",
            unique=True,
            postgresql_where=text("evidence_authorization_id IS NOT NULL"),
        ),
        Index(
            "uq_attempt_evidence_authorization_sha256",
            "evidence_authorization_sha256",
            unique=True,
            postgresql_where=text("evidence_authorization_sha256 IS NOT NULL"),
        ),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    request_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_task_id: Mapped[str | None] = mapped_column(String, nullable=True)
    provider_state: Mapped[str | None] = mapped_column(String, nullable=True)
    attempt_state: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_class: Mapped[str | None] = mapped_column(String, nullable=True)
    provider_http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_request_id_hmac_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_error_message: Mapped[str | None] = mapped_column(String(256), nullable=True)
    usage_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    artifact_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_authorization_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey(
            "live_authorization_uses.authorization_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    evidence_authorization_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_runtime_release_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_runtime_policy_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_task_queue: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence_ledger_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence_deployment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence_claim_event_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("run_events.id", deferrable=True, initially="DEFERRED"),
        nullable=True,
    )
    evidence_acceptance_event_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("run_events.id", deferrable=True, initially="DEFERRED"),
        nullable=True,
    )
    evidence_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence_claim_state: Mapped[str | None] = mapped_column(String(32), nullable=True)


class LiveAuthorizationUseRecord(Base):
    """Append-only proof that a one-POST authorization was consumed before submit."""

    __tablename__ = "live_authorization_uses"
    __table_args__ = (
        CheckConstraint(
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
            "expires_at IS NOT NULL AND nonce_sha256 IS NOT NULL AND "
            "claim_state IS NOT NULL AND claim_state = 'POST_IN_FLIGHT' "
            "AND attempt = 1 AND max_cost_cny > 0 AND max_cost_cny <= 15 "
            "AND authorized_at < expires_at AND expires_at <= evidence_valid_until "
            "AND expires_at <= entitlement_valid_until"
            ")",
            name="ck_live_auth_evidence_bound_complete",
        ),
        Index(
            "uq_live_auth_authorization_sha256",
            "authorization_sha256",
            unique=True,
            postgresql_where=text("authorization_sha256 IS NOT NULL"),
        ),
        Index(
            "uq_live_auth_evidence_bound_plan",
            "evidence_bound_plan_sha256",
            unique=True,
            postgresql_where=text("evidence_bound_plan_sha256 IS NOT NULL"),
        ),
        Index(
            "uq_live_auth_nonce_sha256",
            "nonce_sha256",
            unique=True,
            postgresql_where=text("nonce_sha256 IS NOT NULL"),
        ),
        Index(
            "uq_live_auth_evidence_bound_attempt",
            "run_id",
            "job_id",
            "attempt",
            unique=True,
            postgresql_where=text(
                "authorization_document_type = 'sdc.evidence-bound-live-authorization'"
            ),
        ),
    )
    authorization_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    capability_snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pricing_snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    max_cost_cny: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    authorization_document_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    authorization_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_bound_plan_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    execution_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submission_policy_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    runtime_policy_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    runtime_release_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_bundle_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_logical_tree_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    entitlement_anchor_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entitlement_valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    provider_region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    task_queue: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ledger_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nonce_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    claim_state: Mapped[str | None] = mapped_column(String(32), nullable=True)


class CanaryRuntimeIdentityRecord(Base):
    """Immutable singleton binding the Canary ledger to one reviewed deployment."""

    __tablename__ = "canary_runtime_identity"
    __table_args__ = (
        CheckConstraint("singleton_id = 1", name="ck_canary_runtime_identity_singleton"),
        CheckConstraint(
            "provider = 'volcengine_ark' AND "
            "model = 'doubao-seedance-2-0-260128' AND "
            "region = 'cn-beijing' AND "
            "operation = 'contents.generations.tasks.create'",
            name="ck_canary_runtime_identity_route",
        ),
        CheckConstraint(
            "runtime_release_sha256 ~ '^[0-9a-f]{64}$' AND "
            "runtime_policy_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_canary_runtime_identity_digests",
        ),
        CheckConstraint(
            "ledger_id ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$' AND "
            "deployment_id ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$' AND "
            "task_queue ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'",
            name="ck_canary_runtime_identity_names",
        ),
        CheckConstraint(
            "claim_to_socket_max_ms = 10000 AND expiry_guard_band_ms = 30000",
            name="ck_canary_runtime_identity_deadlines",
        ),
        UniqueConstraint("ledger_id", name="uq_canary_runtime_identity_ledger"),
        UniqueConstraint("deployment_id", name="uq_canary_runtime_identity_deployment"),
    )
    singleton_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    ledger_id: Mapped[str] = mapped_column(String(128), nullable=False)
    deployment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    runtime_release_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    runtime_policy_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    task_queue: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    claim_to_socket_max_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    expiry_guard_band_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


@event.listens_for(EventRecord, "before_update")
@event.listens_for(EventRecord, "before_delete")
def prohibit_event_mutation(*_: object) -> None:
    raise ValueError("run events are append-only")


@event.listens_for(LiveAuthorizationUseRecord, "before_update")
@event.listens_for(LiveAuthorizationUseRecord, "before_delete")
def prohibit_authorization_use_mutation(*_: object) -> None:
    raise ValueError("live authorization uses are append-only")


@event.listens_for(CanaryRuntimeIdentityRecord, "before_update")
@event.listens_for(CanaryRuntimeIdentityRecord, "before_delete")
def prohibit_canary_runtime_identity_mutation(*_: object) -> None:
    raise ValueError("Canary runtime identity is append-only")
