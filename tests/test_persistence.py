from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from sdc.persistence import ArtifactRecord, AttemptRecord, LiveAuthorizationUseRecord


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
        if isinstance(item, CheckConstraint)
        and item.name == "ck_live_auth_evidence_bound_complete"
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
