import asyncio
import re
import uuid
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

BASELINE_ATTEMPT_COLUMNS = (
    "id",
    "run_id",
    "job_id",
    "attempt",
    "state",
    "provider",
    "model",
    "request_fingerprint",
    "provider_task_id",
    "provider_state",
    "attempt_state",
    "failure_class",
    "usage_tokens",
    "submitted_at",
    "last_observed_at",
    "downloaded_at",
    "artifact_sha256",
)
DIAGNOSTIC_COLUMNS = (
    "provider_http_status",
    "provider_error_code",
    "provider_request_id_hmac_sha256",
    "provider_error_message",
)
NULL_DIAGNOSTICS = dict.fromkeys(DIAGNOSTIC_COLUMNS)
LEGACY_AUTHORIZATION_COLUMNS = (
    "authorization_id",
    "run_id",
    "job_id",
    "attempt",
    "request_fingerprint",
    "capability_snapshot_sha256",
    "pricing_snapshot_sha256",
    "max_cost_cny",
    "consumed_at",
)
EVIDENCE_BOUND_AUTHORIZATION_COLUMNS = (
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
NULL_EVIDENCE_BOUND_AUTHORIZATION = dict.fromkeys(EVIDENCE_BOUND_AUTHORIZATION_COLUMNS)


def _quoted_temporary_database_name(name: str) -> str:
    if re.fullmatch(r"sdc_migration_[0-9a-f]{32}", name) is None:
        raise ValueError("refusing to use an unexpected temporary database name")
    return f'"{name}"'


async def _execute_autocommit(database_url: URL, statement: str) -> None:
    engine = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


def _config_for(database_url: URL) -> Config:
    config = Config("alembic.ini")
    rendered_url = database_url.render_as_string(hide_password=False).replace("%", "%%")
    config.set_main_option("sqlalchemy.url", rendered_url)
    return config


@pytest.fixture
def isolated_migration_database() -> Iterator[tuple[Config, URL]]:
    base_config = Config("alembic.ini")
    configured_url = base_config.get_main_option("sqlalchemy.url")
    assert configured_url is not None
    base_url = make_url(configured_url)

    database_name = f"sdc_migration_{uuid.uuid4().hex}"
    quoted_name = _quoted_temporary_database_name(database_name)
    assert database_name != base_url.database
    admin_url = base_url.set(database="postgres")
    temporary_url = base_url.set(database=database_name)

    try:
        asyncio.run(_execute_autocommit(admin_url, f"CREATE DATABASE {quoted_name}"))
        yield _config_for(temporary_url), temporary_url
    finally:
        asyncio.run(
            _execute_autocommit(
                admin_url,
                f"DROP DATABASE IF EXISTS {quoted_name} WITH (FORCE)",
            )
        )


def _attempt_values(label: str, fill: str, minute: int) -> dict[str, object]:
    submitted_at = datetime(2026, 8, 12, 8, minute, tzinfo=UTC)
    return {
        "id": f"attempt-{label}",
        "run_id": f"run-{label}",
        "job_id": f"job-{label}",
        "attempt": 1,
        "state": "HUMAN_GATE",
        "provider": "ark",
        "model": "seedance-test",
        "request_fingerprint": fill * 64,
        "provider_task_id": f"provider-task-{label}",
        "provider_state": "FAILED",
        "attempt_state": "FAILED",
        "failure_class": "REMOTE_FAILED",
        "usage_tokens": 17 + minute,
        "submitted_at": submitted_at,
        "last_observed_at": submitted_at.replace(second=1),
        "downloaded_at": submitted_at.replace(second=2),
        "artifact_sha256": fill.upper() * 64,
    }


async def _insert_attempt(
    database_url: URL,
    baseline: Mapping[str, object],
    diagnostics: Mapping[str, object] | None = None,
) -> None:
    values = dict(baseline)
    if diagnostics is not None:
        values.update(diagnostics)
    columns = ", ".join(values)
    parameters = ", ".join(f":{name}" for name in values)

    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("INSERT INTO runs (id, state) VALUES (:run_id, :run_state)"),
                {"run_id": baseline["run_id"], "run_state": "HUMAN_GATE"},
            )
            await connection.execute(
                text(f"INSERT INTO generation_attempts ({columns}) VALUES ({parameters})"),
                values,
            )
    finally:
        await engine.dispose()


async def _fetch_attempts(database_url: URL, columns: Sequence[str]) -> list[dict[str, object]]:
    selected_columns = ", ".join(columns)
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(f"SELECT {selected_columns} FROM generation_attempts ORDER BY id")
            )
            return [dict(row) for row in result.mappings()]
    finally:
        await engine.dispose()


async def _present_diagnostic_columns(database_url: URL) -> set[str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'generation_attempts'
                      AND column_name IN (
                          'provider_http_status',
                          'provider_error_code',
                          'provider_request_id_hmac_sha256',
                          'provider_error_message'
                      )
                    """
                )
            )
            return set(result.scalars())
    finally:
        await engine.dispose()


async def _current_revision(database_url: URL) -> str:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            assert isinstance(revision, str)
            return revision
    finally:
        await engine.dispose()


def _authorization_values(
    label: str,
    fill: str,
    *,
    evidence_bound: bool,
) -> dict[str, object]:
    authorized_at = datetime(2026, 8, 15, 3, tzinfo=UTC)
    values: dict[str, object] = {
        "authorization_id": f"authorization-{label}",
        "run_id": f"authorization-run-{label}",
        "job_id": f"authorization-job-{label}",
        "attempt": 1,
        "request_fingerprint": fill * 64,
        "capability_snapshot_sha256": fill * 64,
        "pricing_snapshot_sha256": fill * 64,
        "max_cost_cny": Decimal("0.20"),
        "consumed_at": authorized_at,
    }
    if evidence_bound:
        values.update(
            {
                "authorization_document_type": "sdc.evidence-bound-live-authorization",
                "authorization_sha256": fill * 64,
                "evidence_bound_plan_sha256": fill * 64,
                "execution_sha256": fill * 64,
                "submission_policy_sha256": fill * 64,
                "runtime_policy_sha256": fill * 64,
                "runtime_release_sha256": fill * 64,
                "evidence_bundle_id": fill * 64,
                "evidence_logical_tree_sha256": fill * 64,
                "evidence_valid_until": authorized_at.replace(hour=9),
                "entitlement_anchor_sha256": fill * 64,
                "entitlement_valid_until": authorized_at.replace(hour=8),
                "provider_region": "cn-beijing",
                "task_queue": "sdc-canary-evidence-bound",
                "ledger_id": "sdc-canary-ledger",
                "authorized_at": authorized_at,
                "expires_at": authorized_at.replace(hour=5),
                "nonce_sha256": fill * 64,
                "claim_state": "POST_IN_FLIGHT",
            }
        )
    return values


async def _insert_authorization(database_url: URL, values: Mapping[str, object]) -> None:
    columns = ", ".join(values)
    parameters = ", ".join(f":{name}" for name in values)
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO runs (id, state) VALUES (:run_id, 'HUMAN_GATE') "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"run_id": values["run_id"]},
            )
            await connection.execute(
                text(f"INSERT INTO live_authorization_uses ({columns}) VALUES ({parameters})"),
                values,
            )
    finally:
        await engine.dispose()


async def _authorization_rows(
    database_url: URL,
    columns: Sequence[str],
) -> list[dict[str, object]]:
    selected = ", ".join(columns)
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(f"SELECT {selected} FROM live_authorization_uses ORDER BY authorization_id")
            )
            return [dict(row) for row in result.mappings()]
    finally:
        await engine.dispose()


async def _execute_statement(database_url: URL, statement: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


def test_provider_failure_diagnostics_preserve_attempts_across_migration_round_trip(
    isolated_migration_database: tuple[Config, URL],
) -> None:
    config, database_url = isolated_migration_database
    expected_head = ScriptDirectory.from_config(config).get_current_head()
    assert expected_head is not None
    legacy_attempt = _attempt_values("legacy", "a", 0)
    diagnostic_attempt = _attempt_values("diagnostic", "b", 1)
    diagnostics = {
        "provider_http_status": 400,
        "provider_error_code": "InvalidParameter",
        "provider_request_id_hmac_sha256": "c" * 64,
        "provider_error_message": "provider rejected the request",
    }

    command.upgrade(config, "0005")
    asyncio.run(_insert_attempt(database_url, legacy_attempt))

    command.upgrade(config, "0006")
    assert asyncio.run(_current_revision(database_url)) == "0006"
    assert asyncio.run(_present_diagnostic_columns(database_url)) == set(DIAGNOSTIC_COLUMNS)
    assert asyncio.run(
        _fetch_attempts(database_url, (*BASELINE_ATTEMPT_COLUMNS, *DIAGNOSTIC_COLUMNS))
    ) == [{**legacy_attempt, **NULL_DIAGNOSTICS}]

    asyncio.run(_insert_attempt(database_url, diagnostic_attempt, diagnostics))
    assert asyncio.run(
        _fetch_attempts(database_url, (*BASELINE_ATTEMPT_COLUMNS, *DIAGNOSTIC_COLUMNS))
    ) == [
        {**diagnostic_attempt, **diagnostics},
        {**legacy_attempt, **NULL_DIAGNOSTICS},
    ]

    command.downgrade(config, "0005")
    assert asyncio.run(_current_revision(database_url)) == "0005"
    assert asyncio.run(_present_diagnostic_columns(database_url)) == set()
    assert asyncio.run(_fetch_attempts(database_url, BASELINE_ATTEMPT_COLUMNS)) == [
        diagnostic_attempt,
        legacy_attempt,
    ]

    command.upgrade(config, "head")
    assert asyncio.run(_current_revision(database_url)) == expected_head
    assert asyncio.run(_present_diagnostic_columns(database_url)) == set(DIAGNOSTIC_COLUMNS)
    assert asyncio.run(
        _fetch_attempts(database_url, (*BASELINE_ATTEMPT_COLUMNS, *DIAGNOSTIC_COLUMNS))
    ) == [
        {**diagnostic_attempt, **NULL_DIAGNOSTICS},
        {**legacy_attempt, **NULL_DIAGNOSTICS},
    ]


def test_evidence_bound_authorization_migration_is_strict_and_legacy_lossless(
    isolated_migration_database: tuple[Config, URL],
) -> None:
    config, database_url = isolated_migration_database
    legacy = _authorization_values("legacy", "a", evidence_bound=False)
    valid = _authorization_values("valid", "f", evidence_bound=True)

    command.upgrade(config, "0006")
    asyncio.run(_insert_authorization(database_url, legacy))
    command.upgrade(config, "0007")
    assert asyncio.run(_current_revision(database_url)) == "0007"
    assert asyncio.run(
        _authorization_rows(
            database_url,
            (*LEGACY_AUTHORIZATION_COLUMNS, *EVIDENCE_BOUND_AUTHORIZATION_COLUMNS),
        )
    ) == [{**legacy, **NULL_EVIDENCE_BOUND_AUTHORIZATION}]

    partial_legacy = _authorization_values("partial", "b", evidence_bound=False)
    partial_legacy["authorization_sha256"] = "b" * 64
    with pytest.raises(IntegrityError):
        asyncio.run(_insert_authorization(database_url, partial_legacy))

    for label, fill, field in (
        ("null-document", "c", "authorization_document_type"),
        ("null-region", "d", "provider_region"),
        ("null-claim", "e", "claim_state"),
    ):
        invalid = _authorization_values(label, fill, evidence_bound=True)
        invalid[field] = None
        with pytest.raises(IntegrityError):
            asyncio.run(_insert_authorization(database_url, invalid))

    asyncio.run(_insert_authorization(database_url, valid))
    for label, fill, field in (
        ("duplicate-authorization", "2", "authorization_sha256"),
        ("duplicate-plan", "3", "evidence_bound_plan_sha256"),
        ("duplicate-nonce", "4", "nonce_sha256"),
    ):
        duplicate_identity = _authorization_values(label, fill, evidence_bound=True)
        duplicate_identity[field] = valid[field]
        with pytest.raises(IntegrityError):
            asyncio.run(_insert_authorization(database_url, duplicate_identity))

    duplicate_attempt = _authorization_values("duplicate-attempt", "1", evidence_bound=True)
    duplicate_attempt.update(
        run_id=valid["run_id"],
        job_id=valid["job_id"],
        attempt=valid["attempt"],
    )
    with pytest.raises(IntegrityError):
        asyncio.run(_insert_authorization(database_url, duplicate_attempt))

    for statement in (
        "UPDATE live_authorization_uses SET max_cost_cny = max_cost_cny",
        "DELETE FROM live_authorization_uses",
        "TRUNCATE live_authorization_uses",
    ):
        with pytest.raises(DBAPIError):
            asyncio.run(_execute_statement(database_url, statement))

    with pytest.raises(DBAPIError, match="cannot downgrade 0007"):
        command.downgrade(config, "0006")
    assert asyncio.run(_current_revision(database_url)) == "0007"
    assert asyncio.run(
        _authorization_rows(
            database_url,
            (*LEGACY_AUTHORIZATION_COLUMNS, *EVIDENCE_BOUND_AUTHORIZATION_COLUMNS),
        )
    ) == [
        {**legacy, **NULL_EVIDENCE_BOUND_AUTHORIZATION},
        valid,
    ]


def test_evidence_bound_authorization_migration_round_trip_is_lossless_for_legacy_rows(
    isolated_migration_database: tuple[Config, URL],
) -> None:
    config, database_url = isolated_migration_database
    legacy = _authorization_values("legacy", "a", evidence_bound=False)

    command.upgrade(config, "0005")
    asyncio.run(_insert_authorization(database_url, legacy))
    command.upgrade(config, "0007")
    assert asyncio.run(
        _authorization_rows(
            database_url,
            (*LEGACY_AUTHORIZATION_COLUMNS, *EVIDENCE_BOUND_AUTHORIZATION_COLUMNS),
        )
    ) == [{**legacy, **NULL_EVIDENCE_BOUND_AUTHORIZATION}]

    command.downgrade(config, "0006")
    assert asyncio.run(_current_revision(database_url)) == "0006"
    assert asyncio.run(_authorization_rows(database_url, LEGACY_AUTHORIZATION_COLUMNS)) == [legacy]

    command.upgrade(config, "0007")
    assert asyncio.run(
        _authorization_rows(
            database_url,
            (*LEGACY_AUTHORIZATION_COLUMNS, *EVIDENCE_BOUND_AUTHORIZATION_COLUMNS),
        )
    ) == [{**legacy, **NULL_EVIDENCE_BOUND_AUTHORIZATION}]
