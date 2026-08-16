from sqlalchemy import CheckConstraint, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from sdc.persistence import (
    ArtifactRecord,
    AttemptRecord,
    CanaryRuntimeIdentityRecord,
    LiveAuthorizationUseRecord,
)

_ATTEMPT_EVIDENCE_COLUMNS = (
    "evidence_authorization_id",
    "evidence_authorization_sha256",
    "evidence_runtime_release_sha256",
    "evidence_runtime_policy_sha256",
    "evidence_task_queue",
    "evidence_ledger_id",
    "evidence_deployment_id",
    "evidence_claim_event_id",
    "evidence_acceptance_event_id",
    "evidence_claimed_at",
    "evidence_claim_state",
)


def test_current_candidate_uses_postgresql_partial_unique_index() -> None:
    table = ArtifactRecord.__table__
    assert not any(
        {column.name for column in constraint.columns} == {"run_id", "job_id", "is_current"}
        for constraint in table.constraints
    )
    index = next(item for item in table.indexes if item.name == "uq_artifacts_one_current_per_job")
    ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert index.unique
    assert "UNIQUE INDEX" in ddl
    assert "WHERE is_current = true" in ddl
    assert "(run_id, job_id)" in ddl


def test_live_authorization_is_globally_one_use() -> None:
    table = LiveAuthorizationUseRecord.__table__
    assert table.primary_key.columns.keys() == ["authorization_id"]
    fingerprint = table.columns["request_fingerprint"]
    assert fingerprint.unique


def test_evidence_bound_claim_columns_are_complete_but_legacy_rows_remain_valid() -> None:
    table = LiveAuthorizationUseRecord.__table__
    evidence_bound_columns = {
        "authorization_document_type",
        "authorization_sha256",
        "evidence_bound_plan_sha256",
        "execution_sha256",
        "submission_policy_sha256",
        "runtime_policy_sha256",
        "runtime_release_sha256",
        "evidence_bundle_id",
        "evidence_logical_tree_sha256",
        "evidence_valid_until",
        "entitlement_anchor_sha256",
        "entitlement_valid_until",
        "provider_region",
        "task_queue",
        "ledger_id",
        "authorized_at",
        "expires_at",
        "nonce_sha256",
        "claim_state",
    }
    assert evidence_bound_columns <= set(table.columns.keys())
    assert all(table.columns[name].nullable for name in evidence_bound_columns)
    assert {
        "uq_live_auth_authorization_sha256",
        "uq_live_auth_evidence_bound_plan",
        "uq_live_auth_nonce_sha256",
        "uq_live_auth_evidence_bound_attempt",
    } <= {index.name for index in table.indexes}
    constraint = next(
        item
        for item in table.constraints
        if isinstance(item, CheckConstraint) and item.name == "ck_live_auth_evidence_bound_complete"
    )
    expression = str(constraint.sqltext)
    assert "authorization_document_type IS NULL AND authorization_sha256 IS NULL" in expression
    assert all(f"{name} IS NULL" in expression for name in evidence_bound_columns)
    assert "authorization_document_type = 'sdc.evidence-bound-live-authorization'" in expression
    for field in ("authorization_document_type", "provider_region", "claim_state"):
        assert f"{field} IS NOT NULL" in expression

    attempt_index = next(
        index for index in table.indexes if index.name == "uq_live_auth_evidence_bound_attempt"
    )
    assert attempt_index.unique
    assert tuple(column.name for column in attempt_index.columns) == ("run_id", "job_id", "attempt")


def test_provider_failure_diagnostics_are_bounded_nullable_scalars() -> None:
    table = AttemptRecord.__table__
    status = table.columns["provider_http_status"]
    assert isinstance(status.type, Integer) and status.nullable
    for name, length in (
        ("provider_error_code", 128),
        ("provider_request_id_hmac_sha256", 64),
        ("provider_error_message", 256),
    ):
        column = table.columns[name]
        assert isinstance(column.type, String)
        assert column.type.length == length and column.nullable


def test_canary_runtime_identity_is_one_exact_immutable_route() -> None:
    table = CanaryRuntimeIdentityRecord.__table__
    assert table.name == "canary_runtime_identity"
    assert tuple(table.primary_key.columns.keys()) == ("singleton_id",)
    assert isinstance(table.columns.singleton_id.type, SmallInteger)
    assert {
        "singleton_id",
        "ledger_id",
        "deployment_id",
        "runtime_release_sha256",
        "runtime_policy_sha256",
        "task_queue",
        "provider",
        "model",
        "region",
        "operation",
        "claim_to_socket_max_ms",
        "expiry_guard_band_ms",
        "created_at",
    } == set(table.columns.keys())
    assert all(not column.nullable for column in table.columns)
    assert table.columns.created_at.type.timezone is True

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert set(checks) == {
        "ck_canary_runtime_identity_singleton",
        "ck_canary_runtime_identity_route",
        "ck_canary_runtime_identity_digests",
        "ck_canary_runtime_identity_names",
        "ck_canary_runtime_identity_deadlines",
    }
    assert "singleton_id = 1" in checks["ck_canary_runtime_identity_singleton"]
    route = checks["ck_canary_runtime_identity_route"]
    for exact_value in (
        "provider = 'volcengine_ark'",
        "model = 'doubao-seedance-2-0-260128'",
        "region = 'cn-beijing'",
        "operation = 'contents.generations.tasks.create'",
    ):
        assert exact_value in route
    deadlines = checks["ck_canary_runtime_identity_deadlines"]
    assert "claim_to_socket_max_ms = 10000" in deadlines
    assert "expiry_guard_band_ms = 30000" in deadlines

    unique_columns = {
        tuple(column.name for column in constraint.columns): constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_columns[("ledger_id",)] == "uq_canary_runtime_identity_ledger"
    assert unique_columns[("deployment_id",)] == "uq_canary_runtime_identity_deployment"


def test_attempt_evidence_claim_is_all_null_or_complete_post_in_flight() -> None:
    table = AttemptRecord.__table__
    assert all(table.columns[name].nullable for name in _ATTEMPT_EVIDENCE_COLUMNS)
    constraint = next(
        item
        for item in table.constraints
        if isinstance(item, CheckConstraint)
        and item.name == "ck_attempt_evidence_bound_claim_complete"
    )
    expression = str(constraint.sqltext)

    # Released attempts remain compatible: all new columns are nullable and the old branch
    # explicitly requires the complete absence of Canary claim state.
    assert all(f"{name} IS NULL" in expression for name in _ATTEMPT_EVIDENCE_COLUMNS)
    assert "attempt_state IS DISTINCT FROM 'POST_IN_FLIGHT'" in expression

    # SQL CHECK accepts UNKNOWN, so every nullable discriminator used by the claimed branch must
    # first be proven non-NULL before an equality/regex assertion can close the branch.
    for name in (
        *_ATTEMPT_EVIDENCE_COLUMNS,
        "attempt_state",
        "provider",
        "model",
        "request_fingerprint",
    ):
        assert f"{name} IS NOT NULL" in expression
    assert "evidence_claim_state = 'POST_IN_FLIGHT'" in expression
    assert "attempt = 1" in expression
    assert "provider = 'volcengine_ark'" in expression
    assert "model = 'doubao-seedance-2-0-260128'" in expression
    assert "request_fingerprint ~ '^[0-9a-f]{64}$'" in expression
    assert "provider_task_id IS NULL AND submitted_at IS NULL" in expression
    assert "attempt_state IN ('POST_IN_FLIGHT', 'SUBMISSION_UNKNOWN', 'HUMAN_GATE')" in expression
    assert "provider_task_id IS NOT NULL AND submitted_at IS NOT NULL" in expression
    assert (
        "attempt_state IN ('SUBMITTED', 'WATCHING', 'DOWNLOADING', 'VERIFIED', "
        "'FAILED', 'SUBMISSION_UNKNOWN', 'HUMAN_GATE')"
    ) in expression


def test_attempt_evidence_claim_has_deferred_ownership_links_and_partial_uniques() -> None:
    table = AttemptRecord.__table__
    expected_foreign_keys = {
        "evidence_authorization_id": "live_authorization_uses.authorization_id",
        "evidence_claim_event_id": "run_events.id",
        "evidence_acceptance_event_id": "run_events.id",
    }
    for column_name, target in expected_foreign_keys.items():
        foreign_keys = tuple(table.columns[column_name].foreign_keys)
        assert len(foreign_keys) == 1
        foreign_key = foreign_keys[0]
        assert foreign_key.target_fullname == target
        assert foreign_key.deferrable is True
        assert foreign_key.initially == "DEFERRED"

    for name, column_name in (
        ("uq_attempt_evidence_authorization_id", "evidence_authorization_id"),
        ("uq_attempt_evidence_authorization_sha256", "evidence_authorization_sha256"),
    ):
        index = next(item for item in table.indexes if item.name == name)
        assert index.unique
        assert tuple(column.name for column in index.columns) == (column_name,)
        ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
        assert "UNIQUE INDEX" in ddl
        assert f"WHERE {column_name} IS NOT NULL" in ddl
