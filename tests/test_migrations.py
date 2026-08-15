import ast
from pathlib import Path

from sqlalchemy import CheckConstraint

from sdc.persistence import LiveAuthorizationUseRecord


def _migration_check_expression(source: str) -> str:
    matches = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "create_check_constraint"
        and len(node.args) >= 3
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "ck_live_auth_evidence_bound_complete"
    ]
    assert len(matches) == 1
    expression = ast.literal_eval(matches[0].args[2])
    assert isinstance(expression, str)
    return expression


def test_alembic_online_environment_uses_asyncpg_pattern() -> None:
    source = Path("migrations/env.py").read_text()
    assert "async_engine_from_config" in source
    assert "async with connectable.connect()" in source
    assert "await connection.run_sync(do_run_migrations)" in source
    assert "asyncio.run(run_async_migrations())" in source
    assert "engine_from_config(" not in source.replace("async_engine_from_config(", "")
    assert "postgresql+asyncpg://" in Path("alembic.ini").read_text()


def test_provider_failure_diagnostic_migration_extends_0005_without_backfill() -> None:
    source = Path("migrations/versions/0006_provider_failure_diagnostics.py").read_text()
    assert 'revision = "0006"' in source and 'down_revision = "0005"' in source
    for name in (
        "provider_http_status",
        "provider_error_code",
        "provider_request_id_hmac_sha256",
        "provider_error_message",
    ):
        assert f'Column("{name}"' in source
    assert "nullable=True" in source
    assert "server_default" not in source
    assert "create_index" not in source


def test_evidence_bound_authorization_migration_preserves_legacy_rows() -> None:
    source = Path("migrations/versions/0007_evidence_bound_authorization.py").read_text()
    assert 'revision = "0007"' in source and 'down_revision = "0006"' in source
    columns = (
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
    )
    for name in columns:
        assert f'Column("{name}"' in source
    assert 'op.drop_column("live_authorization_uses", column.name)' in source
    assert source.count("nullable=True") == len(columns)
    assert "server_default" not in source
    assert "UPDATE live_authorization_uses" not in source
    assert "DELETE FROM live_authorization_uses" not in source
    assert "ck_live_auth_evidence_bound_complete" in source
    for index in (
        "uq_live_auth_authorization_sha256",
        "uq_live_auth_evidence_bound_plan",
        "uq_live_auth_nonce_sha256",
        "uq_live_auth_evidence_bound_attempt",
    ):
        assert index in source
    for field in ("authorization_document_type", "provider_region", "claim_state"):
        assert f"{field} IS NOT NULL" in source
    assert "BEFORE TRUNCATE ON live_authorization_uses" in source
    assert "cannot downgrade 0007 while an evidence-bound authorization claim exists" in source
    assert source.index("IF EXISTS (") < source.index(
        "DROP TRIGGER IF EXISTS trg_live_authorization_uses_no_truncate"
    )
    assert source.index("DROP TRIGGER IF EXISTS trg_live_authorization_uses_no_truncate") < (
        source.index("DROP FUNCTION IF EXISTS sdc_reject_live_authorization_use_mutation")
    )


def test_evidence_bound_authorization_check_matches_orm_and_has_balanced_parentheses() -> None:
    source = Path("migrations/versions/0007_evidence_bound_authorization.py").read_text()
    migration_expression = _migration_check_expression(source)
    constraint = next(
        item
        for item in LiveAuthorizationUseRecord.__table__.constraints
        if isinstance(item, CheckConstraint) and item.name == "ck_live_auth_evidence_bound_complete"
    )

    assert migration_expression == str(constraint.sqltext)
    depth = 0
    for character in migration_expression:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            assert depth >= 0
    assert depth == 0
