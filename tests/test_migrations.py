import ast
import hashlib
from pathlib import Path

from sqlalchemy import CheckConstraint

from sdc.persistence import AttemptRecord, LiveAuthorizationUseRecord

_RELEASED_0007_SHA256 = "42e7292e68e9da11cb47da68fbd108584415760dcd8e9387149b0147d6fc816c"
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


def _assigned_string(source: str, name: str) -> str:
    matches = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    ]
    assert len(matches) == 1
    value = ast.literal_eval(matches[0].value)
    assert isinstance(value, str)
    return value


def _attempt_column_calls(source: str) -> tuple[ast.Call, ...]:
    matches = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_ATTEMPT_COLUMNS"
            for target in node.targets
        )
    ]
    assert len(matches) == 1 and isinstance(matches[0].value, ast.Tuple)
    calls = tuple(matches[0].value.elts)
    assert all(isinstance(item, ast.Call) for item in calls)
    return calls  # type: ignore[return-value]


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


def test_released_0007_migration_is_byte_stable() -> None:
    content = Path("migrations/versions/0007_evidence_bound_authorization.py").read_bytes()
    normalized = content.replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == _RELEASED_0007_SHA256


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


def test_atomic_canary_ledger_migration_adds_only_nullable_attempt_claim_columns() -> None:
    source = Path("migrations/versions/0008_atomic_canary_ledger.py").read_text()
    assert 'revision = "0008"' in source and 'down_revision = "0007"' in source

    calls = _attempt_column_calls(source)
    names: list[str] = []
    for call in calls:
        assert call.args and isinstance(call.args[0], ast.Constant)
        names.append(call.args[0].value)
        nullable = next(keyword.value for keyword in call.keywords if keyword.arg == "nullable")
        assert isinstance(nullable, ast.Constant) and nullable.value is True
        assert not any(keyword.arg == "server_default" for keyword in call.keywords)
    assert tuple(names) == _ATTEMPT_EVIDENCE_COLUMNS

    assert 'op.add_column("generation_attempts", column)' in source
    assert 'op.add_column("live_authorization_uses"' not in source
    assert 'op.alter_column("live_authorization_uses"' not in source
    assert "UPDATE generation_attempts SET" not in source
    assert "DELETE FROM generation_attempts" not in source
    assert "server_default" not in source


def test_atomic_canary_attempt_check_closes_sql_null_bypasses() -> None:
    source = Path("migrations/versions/0008_atomic_canary_ledger.py").read_text()
    expression = _assigned_string(source, "_ATTEMPT_CLAIM_CHECK")

    assert all(f"{name} IS NULL" in expression for name in _ATTEMPT_EVIDENCE_COLUMNS)
    assert "attempt_state IS DISTINCT FROM 'POST_IN_FLIGHT'" in expression
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


def test_atomic_canary_attempt_check_matches_orm_exactly() -> None:
    source = Path("migrations/versions/0008_atomic_canary_ledger.py").read_text()
    migration_expression = _assigned_string(source, "_ATTEMPT_CLAIM_CHECK")
    constraint = next(
        item
        for item in AttemptRecord.__table__.constraints
        if isinstance(item, CheckConstraint)
        and item.name == "ck_attempt_evidence_bound_claim_complete"
    )
    assert migration_expression == str(constraint.sqltext)


def test_atomic_canary_identity_table_is_exact_and_migration_stays_inert() -> None:
    source = Path("migrations/versions/0008_atomic_canary_ledger.py").read_text()
    assert 'op.create_table(\n        "canary_runtime_identity"' in source
    for name in (
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
    ):
        assert f'Column("{name}"' in source
    for constraint in (
        "ck_canary_runtime_identity_singleton",
        "ck_canary_runtime_identity_route",
        "ck_canary_runtime_identity_digests",
        "ck_canary_runtime_identity_names",
        "ck_canary_runtime_identity_deadlines",
        "uq_canary_runtime_identity_ledger",
        "uq_canary_runtime_identity_deployment",
    ):
        assert constraint in source
    for exact_value in (
        "provider = 'volcengine_ark'",
        "model = 'doubao-seedance-2-0-260128'",
        "region = 'cn-beijing'",
        "operation = 'contents.generations.tasks.create'",
        "claim_to_socket_max_ms = 10000",
        "expiry_guard_band_ms = 30000",
    ):
        assert exact_value in source
    assert "op.bulk_insert" not in source
    assert "INSERT INTO canary_runtime_identity" not in source


def test_atomic_canary_claim_links_and_uniques_are_deferred_and_partial() -> None:
    source = Path("migrations/versions/0008_atomic_canary_ledger.py").read_text()
    for name, target in (
        ("fk_attempt_evidence_authorization_id", "live_authorization_uses"),
        ("fk_attempt_evidence_claim_event_id", "run_events"),
        ("fk_attempt_evidence_acceptance_event_id", "run_events"),
    ):
        start = source.index(f'"{name}"')
        block = source[start : source.index("    )", start) + 5]
        assert f'"{target}"' in block
        assert "deferrable=True" in block
        assert 'initially="DEFERRED"' in block

    for name, column in (
        ("uq_attempt_evidence_authorization_id", "evidence_authorization_id"),
        ("uq_attempt_evidence_authorization_sha256", "evidence_authorization_sha256"),
    ):
        start = source.index(f'"{name}"')
        block = source[start : source.index("    )", start) + 5]
        assert f'["{column}"]' in block
        assert "unique=True" in block
        assert f'"{column} IS NOT NULL"' in block


def test_atomic_canary_ledger_has_database_append_only_and_truncate_guards() -> None:
    source = Path("migrations/versions/0008_atomic_canary_ledger.py").read_text()
    for trigger in (
        "trg_canary_runtime_identity_append_only",
        "trg_canary_runtime_identity_no_truncate",
        "trg_evidence_bound_attempt_identity",
        "trg_evidence_bound_attempt_no_truncate",
        "trg_run_events_append_only",
        "trg_run_events_no_truncate",
    ):
        assert f"CREATE TRIGGER {trigger}" in source
        assert f"DROP TRIGGER IF EXISTS {trigger}" in source
    assert "evidence-bound generation attempt identity is immutable" in source
    assert "generation_attempts contains evidence-bound claim state" in source
    assert "run_events is append-only" in source


def test_atomic_canary_downgrade_fails_closed_before_removing_guards() -> None:
    source = Path("migrations/versions/0008_atomic_canary_ledger.py").read_text()
    preflight = source.index(
        "cannot downgrade 0008 while evidence-bound Canary ledger state exists"
    )
    lock = source.index(
        '"LOCK TABLE canary_runtime_identity, generation_attempts, "\n'
        '        "live_authorization_uses, run_events IN ACCESS EXCLUSIVE MODE"'
    )
    first_drop = source.index("DROP TRIGGER IF EXISTS", preflight)
    assert lock < preflight < first_drop
    for marker in (
        "SELECT 1 FROM canary_runtime_identity",
        "attempt_state = 'POST_IN_FLIGHT'",
        "'sdc.evidence-bound-live-authorization'",
        "'provider.evidence_bound_claimed'",
        "'provider.evidence_bound_submission_accepted'",
    ):
        assert marker in source[:first_drop]

    for trigger, function in (
        ("trg_run_events_no_truncate", "sdc_reject_run_event_mutation"),
        ("trg_evidence_bound_attempt_no_truncate", "sdc_protect_evidence_bound_attempt"),
        (
            "trg_canary_runtime_identity_no_truncate",
            "sdc_reject_canary_runtime_identity_mutation",
        ),
    ):
        assert source.index(f"DROP TRIGGER IF EXISTS {trigger}", first_drop) < source.index(
            f"DROP FUNCTION IF EXISTS {function}", first_drop
        )

    assert source.index('op.drop_index(\n        "uq_attempt_evidence_authorization_sha256"') < (
        source.index('op.drop_constraint(\n        "ck_attempt_evidence_bound_claim_complete"')
    )
    claim_check_drop = source.index(
        'op.drop_constraint(\n        "ck_attempt_evidence_bound_claim_complete"'
    )
    assert claim_check_drop < source.index(
        'op.drop_constraint(\n        "fk_attempt_evidence_claim_event_id"'
    )
    assert source.index('op.drop_constraint(\n        "fk_attempt_evidence_authorization_id"') < (
        source.index('op.drop_column("generation_attempts", column.name)')
    )
    assert source.index('op.drop_column("generation_attempts", column.name)') < source.index(
        'op.drop_table("canary_runtime_identity")'
    )
    assert "for column in reversed(_ATTEMPT_COLUMNS)" in source
