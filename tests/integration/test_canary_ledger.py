from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session
from test_provider_failure_migration import (
    isolated_migration_database as _provider_failure_migration_database,
)

import sdc.evidence_ledger as evidence_ledger
from sdc.contracts import ProviderTaskState, RunState
from sdc.evidence_ledger import (
    ACCEPTANCE_EVENT_TYPE,
    CLAIM_EVENT_TYPE,
    EXPIRY_GUARD_BAND_MS,
    ClaimFailure,
    ClaimHumanGate,
    NewPostPermit,
    PostgresCanaryLedgerStore,
    ResumeOwnedTask,
)
from sdc.persistence import (
    AttemptRecord,
    CanaryRuntimeIdentityRecord,
    EventRecord,
    LiveAuthorizationUseRecord,
    RunRecord,
)

MigrationDatabase = tuple[Config, URL]
isolated_migration_database = _provider_failure_migration_database


@pytest.fixture
def migrated_ledger_database(
    isolated_migration_database: MigrationDatabase,
) -> MigrationDatabase:
    config, database_url = isolated_migration_database
    command.upgrade(config, "head")
    return config, database_url


@dataclass(frozen=True)
class LedgerHarness:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]
    store: PostgresCanaryLedgerStore


@dataclass(frozen=True)
class ClaimCounts:
    attempts: int
    authorizations: int
    events: int


@asynccontextmanager
async def _ledger_harness(database_url: URL) -> AsyncIterator[LedgerHarness]:
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield LedgerHarness(
            engine=engine,
            sessions=sessions,
            store=PostgresCanaryLedgerStore(sessions),
        )
    finally:
        await engine.dispose()


def _sha256(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


async def _database_now(sessions: async_sessionmaker[AsyncSession]) -> datetime:
    async with sessions() as session:
        current = await session.scalar(select(text("clock_timestamp()")))
    assert isinstance(current, datetime)
    assert current.tzinfo is not None and current.utcoffset() is not None
    return current.astimezone(UTC)


def _binding(
    label: str,
    database_now: datetime,
    *,
    deadline: datetime | None = None,
) -> evidence_ledger._EvidenceBoundClaimBinding:
    selected_deadline = deadline or database_now + timedelta(minutes=5)
    return evidence_ledger._EvidenceBoundClaimBinding(
        authorization_id=f"authorization-{label}",
        authorization_sha256=_sha256(f"{label}:authorization"),
        plan_sha256=_sha256(f"{label}:plan"),
        execution_sha256=_sha256(f"{label}:execution"),
        submission_policy_sha256=_sha256(f"{label}:submission-policy"),
        runtime_policy_sha256=_sha256("shared:runtime-policy"),
        runtime_release_sha256=_sha256("shared:runtime-release"),
        evidence_bundle_id=_sha256(f"{label}:evidence-bundle"),
        evidence_logical_tree_sha256=_sha256(f"{label}:evidence-tree"),
        evidence_valid_until=selected_deadline,
        entitlement_anchor_sha256=_sha256(f"{label}:entitlement-anchor"),
        entitlement_valid_until=selected_deadline,
        task_queue="sdc-canary-evidence-bound",
        ledger_id="sdc-canary-ledger",
        deployment_id="sdc-canary-deployment",
        run_id=f"run-{label}",
        job_id=f"job-{label}",
        request_fingerprint=_sha256(f"{label}:request"),
        capability_snapshot_sha256=_sha256(f"{label}:capability"),
        pricing_snapshot_sha256=_sha256(f"{label}:pricing"),
        worst_case_cost_cny=Decimal("0.20"),
        max_cost_cny=Decimal("1.00"),
        authorized_at=database_now - timedelta(minutes=1),
        expires_at=selected_deadline,
        nonce_sha256=_sha256(f"{label}:nonce"),
    )


async def _seed_runtime(
    harness: LedgerHarness,
    bindings: tuple[evidence_ledger._EvidenceBoundClaimBinding, ...],
    database_now: datetime,
    *,
    include_identity: bool = True,
) -> None:
    assert bindings
    first = bindings[0]
    async with harness.sessions.begin() as session:
        if include_identity:
            session.add(
                CanaryRuntimeIdentityRecord(
                    singleton_id=evidence_ledger.CANARY_LEDGER_SINGLETON_ID,
                    ledger_id=first.ledger_id,
                    deployment_id=first.deployment_id,
                    runtime_release_sha256=first.runtime_release_sha256,
                    runtime_policy_sha256=first.runtime_policy_sha256,
                    task_queue=first.task_queue,
                    provider=evidence_ledger.CANARY_PROVIDER,
                    model=evidence_ledger.CANARY_MODEL,
                    region=evidence_ledger.CANARY_REGION,
                    operation=evidence_ledger.CANARY_OPERATION,
                    claim_to_socket_max_ms=evidence_ledger.CLAIM_TO_SOCKET_MAX_MS,
                    expiry_guard_band_ms=evidence_ledger.EXPIRY_GUARD_BAND_MS,
                    created_at=database_now,
                )
            )
        session.add_all(
            RunRecord(id=binding.run_id, state=RunState.RUNNING.value) for binding in bindings
        )


async def _claim_counts(
    sessions: async_sessionmaker[AsyncSession],
    binding: evidence_ledger._EvidenceBoundClaimBinding,
) -> ClaimCounts:
    async with sessions() as session:
        attempts = await session.scalar(
            select(func.count())
            .select_from(AttemptRecord)
            .where(AttemptRecord.run_id == binding.run_id)
        )
        authorizations = await session.scalar(
            select(func.count())
            .select_from(LiveAuthorizationUseRecord)
            .where(LiveAuthorizationUseRecord.run_id == binding.run_id)
        )
        events = await session.scalar(
            select(func.count())
            .select_from(EventRecord)
            .where(EventRecord.run_id == binding.run_id)
        )
    return ClaimCounts(
        attempts=int(attempts or 0),
        authorizations=int(authorizations or 0),
        events=int(events or 0),
    )


async def _claim_rows(
    sessions: async_sessionmaker[AsyncSession],
    binding: evidence_ledger._EvidenceBoundClaimBinding,
) -> tuple[AttemptRecord, LiveAuthorizationUseRecord, EventRecord]:
    async with sessions() as session:
        attempt = await session.scalar(
            select(AttemptRecord).where(AttemptRecord.run_id == binding.run_id)
        )
        authorization = await session.scalar(
            select(LiveAuthorizationUseRecord).where(
                LiveAuthorizationUseRecord.run_id == binding.run_id
            )
        )
        claim_event = await session.scalar(
            select(EventRecord).where(
                EventRecord.run_id == binding.run_id,
                EventRecord.event_type == CLAIM_EVENT_TYPE,
            )
        )
    assert attempt is not None
    assert authorization is not None
    assert claim_event is not None
    return attempt, authorization, claim_event


def _receipt(
    result: NewPostPermit,
    provider_task_id: str,
) -> evidence_ledger._SubmittedClaimReceipt:
    result.permit.consume()
    return result.permit.submitted_receipt(
        provider_task_id,
        ProviderTaskState.QUEUED,
    )


def _manual_receipt(
    binding: evidence_ledger._EvidenceBoundClaimBinding,
    permit: evidence_ledger._NewPostPermit,
    provider_task_id: str,
    *,
    claim_event_id: str | None = None,
) -> evidence_ledger._SubmittedClaimReceipt:
    return evidence_ledger._SubmittedClaimReceipt(
        evidence_ledger._PERMIT_FACTORY,
        binding=binding,
        authorization_sha256=binding.authorization_sha256,
        claim_event_id=claim_event_id or permit.claim_event_id,
        claimed_at=permit.claimed_at,
        provider_task_id=provider_task_id,
        provider_state=ProviderTaskState.QUEUED.value,
    )


async def _execute(database_url: URL, statement: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


async def _scalar(database_url: URL, statement: str) -> object:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return await connection.scalar(text(statement))
    finally:
        await engine.dispose()


async def _current_revision(database_url: URL) -> str:
    revision = await _scalar(database_url, "SELECT version_num FROM alembic_version")
    assert isinstance(revision, str)
    return revision


@pytest.mark.asyncio
async def test_0008_starts_with_empty_identity_and_cannot_claim_without_it(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("empty-identity", database_now)
        await _seed_runtime(
            harness,
            (binding,),
            database_now,
            include_identity=False,
        )

        result = await harness.store.claim_evidence_bound_canary(binding)

        assert isinstance(result, ClaimHumanGate)
        assert result.failure is ClaimFailure.NOT_FOUND
        async with harness.sessions() as session:
            identity_count = await session.scalar(
                select(func.count()).select_from(CanaryRuntimeIdentityRecord)
            )
        assert identity_count == 0
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(0, 0, 0)


@pytest.mark.asyncio
async def test_successful_claim_commits_three_records_with_one_database_timestamp(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("atomic", database_now)
        await _seed_runtime(harness, (binding,), database_now)

        result = await harness.store.claim_evidence_bound_canary(binding)

        assert isinstance(result, NewPostPermit)
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(1, 1, 1)
        attempt, authorization, claim_event = await _claim_rows(harness.sessions, binding)
        assert attempt.attempt == 1
        assert attempt.attempt_state == evidence_ledger.POST_IN_FLIGHT
        assert authorization.claim_state == evidence_ledger.POST_IN_FLIGHT
        assert claim_event.event_type == CLAIM_EVENT_TYPE
        assert attempt.evidence_claimed_at is not None
        assert (
            attempt.evidence_claimed_at.astimezone(UTC)
            == authorization.consumed_at.astimezone(UTC)
            == claim_event.occurred_at.astimezone(UTC)
            == result.permit.claimed_at
        )


@pytest.mark.asyncio
async def test_server_time_guard_is_strict_before_equal_and_after_thirty_seconds(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        guard = timedelta(milliseconds=EXPIRY_GUARD_BAND_MS)
        equal_binding = _binding("guard-exact", database_now, deadline=database_now + guard)
        exact_failure = harness.store._validate_claim_time(equal_binding, database_now)
        assert exact_failure is not None
        assert exact_failure.failure is ClaimFailure.NOT_CURRENT

        before = _binding(
            "guard-before",
            database_now,
            deadline=database_now + guard + timedelta(seconds=60),
        )
        equal = equal_binding
        after = _binding(
            "guard-after",
            database_now,
            deadline=database_now + guard - timedelta(microseconds=1),
        )
        await _seed_runtime(harness, (before, equal, after), database_now)

        before_result = await harness.store.claim_evidence_bound_canary(before)
        equal_result = await harness.store.claim_evidence_bound_canary(equal)
        after_result = await harness.store.claim_evidence_bound_canary(after)

        assert isinstance(before_result, NewPostPermit)
        for result in (equal_result, after_result):
            assert isinstance(result, ClaimHumanGate)
            assert result.failure is ClaimFailure.NOT_CURRENT
        assert await _claim_counts(harness.sessions, before) == ClaimCounts(1, 1, 1)
        assert await _claim_counts(harness.sessions, equal) == ClaimCounts(0, 0, 0)
        assert await _claim_counts(harness.sessions, after) == ClaimCounts(0, 0, 0)


@pytest.mark.asyncio
async def test_two_connections_race_to_exactly_one_permit_and_one_unknown_replay(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("race", database_now)
        await _seed_runtime(harness, (binding,), database_now)

        first, second = await asyncio.gather(
            harness.store.claim_evidence_bound_canary(binding),
            harness.store.claim_evidence_bound_canary(binding),
        )

        permits = [result for result in (first, second) if isinstance(result, NewPostPermit)]
        gates = [result for result in (first, second) if isinstance(result, ClaimHumanGate)]
        assert len(permits) == len(gates) == 1
        assert gates[0].failure is ClaimFailure.SUBMISSION_UNKNOWN
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(1, 1, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reject_table",
    ("generation_attempts", "live_authorization_uses", "run_events"),
)
async def test_injected_insert_trigger_rolls_back_attempt_authorization_and_event(
    reject_table: str,
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding(f"rollback-{reject_table.replace('_', '-')}", database_now)
        await _seed_runtime(harness, (binding,), database_now)
        function_name = f"sdc_test_reject_{reject_table}"
        trigger_name = f"trg_test_reject_{reject_table}"
        async with harness.engine.begin() as connection:
            await connection.execute(
                text(
                    f"""
                    CREATE FUNCTION {function_name}() RETURNS trigger
                    LANGUAGE plpgsql AS $$
                    BEGIN
                        RAISE EXCEPTION 'injected claim insert failure';
                    END;
                    $$
                    """
                )
            )
            await connection.execute(
                text(
                    f"""
                    CREATE TRIGGER {trigger_name}
                    BEFORE INSERT ON {reject_table}
                    FOR EACH ROW EXECUTE FUNCTION {function_name}()
                    """
                )
            )

        result = await harness.store.claim_evidence_bound_canary(binding)

        assert isinstance(result, ClaimHumanGate)
        assert result.failure is ClaimFailure.COMMIT_RESULT_UNKNOWN
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(0, 0, 0)


@pytest.mark.asyncio
async def test_replay_without_task_is_permanently_unknown_and_read_only(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("replay-no-task", database_now)
        await _seed_runtime(harness, (binding,), database_now)
        first = await harness.store.claim_evidence_bound_canary(binding)
        assert isinstance(first, NewPostPermit)
        before = await _claim_counts(harness.sessions, binding)

        replay = await harness.store.claim_evidence_bound_canary(binding)
        classified = await harness.store.classify_evidence_bound_canary(binding)

        for result in (replay, classified):
            assert isinstance(result, ClaimHumanGate)
            assert result.failure is ClaimFailure.SUBMISSION_UNKNOWN
        assert await _claim_counts(harness.sessions, binding) == before == ClaimCounts(1, 1, 1)


@pytest.mark.asyncio
async def test_record_owned_task_is_atomic_same_task_idempotent_and_different_task_conflicts(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("owned", database_now)
        await _seed_runtime(harness, (binding,), database_now)
        claimed = await harness.store.claim_evidence_bound_canary(binding)
        assert isinstance(claimed, NewPostPermit)
        receipt = _receipt(claimed, "task-owned-001")

        owned = await harness.store.record_owned_task(receipt)
        assert isinstance(owned, ResumeOwnedTask)
        assert owned.provider_task_id == "task-owned-001"
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(1, 1, 2)
        async with harness.sessions() as session:
            attempt = await session.scalar(
                select(AttemptRecord).where(AttemptRecord.run_id == binding.run_id)
            )
            acceptance = await session.scalar(
                select(EventRecord).where(
                    EventRecord.run_id == binding.run_id,
                    EventRecord.event_type == ACCEPTANCE_EVENT_TYPE,
                )
            )
        assert attempt is not None and acceptance is not None
        assert attempt.provider_task_id == "task-owned-001"
        assert attempt.attempt_state == "SUBMITTED"
        assert attempt.submitted_at is not None
        assert attempt.submitted_at.astimezone(UTC) == acceptance.occurred_at.astimezone(UTC)

        repeated = await harness.store.record_owned_task(receipt)
        assert repeated == owned
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(1, 1, 2)

        different_receipt = _manual_receipt(binding, claimed.permit, "task-owned-002")
        conflict = await harness.store.record_owned_task(different_receipt)
        assert isinstance(conflict, ClaimHumanGate)
        assert conflict.failure is ClaimFailure.CONFLICT
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(1, 1, 2)

        wrong_claim = _manual_receipt(
            binding,
            claimed.permit,
            "task-owned-001",
            claim_event_id="wrong-claim-event",
        )
        wrong_result = await harness.store.record_owned_task(wrong_claim)
        assert isinstance(wrong_result, ClaimHumanGate)
        assert wrong_result.failure is ClaimFailure.CONFLICT


@pytest.mark.asyncio
async def test_record_owned_task_rolls_back_update_when_acceptance_event_insert_fails(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("owned-rollback", database_now)
        await _seed_runtime(harness, (binding,), database_now)
        claimed = await harness.store.claim_evidence_bound_canary(binding)
        assert isinstance(claimed, NewPostPermit)
        receipt = _receipt(claimed, "task-owned-rollback")
        async with harness.engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    CREATE FUNCTION sdc_test_reject_acceptance_event() RETURNS trigger
                    LANGUAGE plpgsql AS $$
                    BEGIN
                        IF NEW.event_type = 'provider.evidence_bound_submission_accepted' THEN
                            RAISE EXCEPTION 'injected acceptance event failure';
                        END IF;
                        RETURN NEW;
                    END;
                    $$
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    CREATE TRIGGER trg_test_reject_acceptance_event
                    BEFORE INSERT ON run_events
                    FOR EACH ROW EXECUTE FUNCTION sdc_test_reject_acceptance_event()
                    """
                )
            )

        result = await harness.store.record_owned_task(receipt)

        assert isinstance(result, ClaimHumanGate)
        assert result.failure is ClaimFailure.SUBMISSION_UNKNOWN
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(1, 1, 1)
        async with harness.sessions() as session:
            attempt = await session.scalar(
                select(AttemptRecord).where(AttemptRecord.run_id == binding.run_id)
            )
        assert attempt is not None
        assert attempt.provider_task_id is None
        assert attempt.submitted_at is None
        assert attempt.attempt_state == evidence_ledger.POST_IN_FLIGHT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_state",
    (ProviderTaskState.FAILED, ProviderTaskState.CANCELLED, ProviderTaskState.EXPIRED),
)
async def test_terminal_task_is_owned_once_but_never_returned_as_resumable(
    provider_state: ProviderTaskState,
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding(f"terminal-{provider_state.value}", database_now)
        await _seed_runtime(harness, (binding,), database_now)
        claimed = await harness.store.claim_evidence_bound_canary(binding)
        assert isinstance(claimed, NewPostPermit)
        claimed.permit.consume()
        receipt = claimed.permit.submitted_receipt(
            f"task-terminal-{provider_state.value}",
            provider_state,
        )

        result = await harness.store.record_owned_task(receipt)
        replay = await harness.store.classify_evidence_bound_canary(binding)

        for classified in (result, replay):
            assert isinstance(classified, ClaimHumanGate)
            assert classified.failure is ClaimFailure.NOT_ELIGIBLE
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(1, 1, 2)


@pytest.mark.asyncio
async def test_provider_task_id_is_globally_owned_by_only_one_claim(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        first_binding = _binding("global-owner-one", database_now)
        second_binding = _binding("global-owner-two", database_now)
        await _seed_runtime(harness, (first_binding, second_binding), database_now)
        first_claim = await harness.store.claim_evidence_bound_canary(first_binding)
        second_claim = await harness.store.claim_evidence_bound_canary(second_binding)
        assert isinstance(first_claim, NewPostPermit)
        assert isinstance(second_claim, NewPostPermit)

        first_owned = await harness.store.record_owned_task(
            _receipt(first_claim, "task-global-001")
        )
        second_owned = await harness.store.record_owned_task(
            _receipt(second_claim, "task-global-001")
        )

        assert isinstance(first_owned, ResumeOwnedTask)
        assert isinstance(second_owned, ClaimHumanGate)
        assert second_owned.failure is ClaimFailure.CONFLICT
        assert await _claim_counts(harness.sessions, first_binding) == ClaimCounts(1, 1, 2)
        assert await _claim_counts(harness.sessions, second_binding) == ClaimCounts(1, 1, 1)


@pytest.mark.asyncio
async def test_wrong_event_id_extra_event_and_partial_attempt_fail_closed(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        wrong_id = _binding("wrong-event-id", database_now)
        extra_event = _binding("extra-event", database_now)
        partial = _binding("partial-attempt", database_now)
        await _seed_runtime(harness, (wrong_id, extra_event, partial), database_now)

        async with harness.sessions.begin() as session:
            session.add(
                EventRecord(
                    id="wrong-deterministic-event-id",
                    run_id=wrong_id.run_id,
                    event_type=CLAIM_EVENT_TYPE,
                    state=RunState.RUNNING.value,
                    occurred_at=database_now,
                    idempotency_key="wrong-event-key",
                    payload=harness.store._claim_event_payload(wrong_id),
                )
            )
            session.add(
                AttemptRecord(
                    id="partial-attempt-row",
                    run_id=partial.run_id,
                    job_id=partial.job_id,
                    attempt=1,
                    state=RunState.RUNNING.value,
                    provider=evidence_ledger.CANARY_PROVIDER,
                    model=evidence_ledger.CANARY_MODEL,
                    request_fingerprint=partial.request_fingerprint,
                    attempt_state="RESERVED",
                )
            )

        claimed = await harness.store.claim_evidence_bound_canary(extra_event)
        assert isinstance(claimed, NewPostPermit)
        async with harness.sessions.begin() as session:
            session.add(
                EventRecord(
                    id="extra-claim-event-id",
                    run_id=extra_event.run_id,
                    event_type=CLAIM_EVENT_TYPE,
                    state=RunState.RUNNING.value,
                    occurred_at=database_now,
                    idempotency_key="extra-claim-event-key",
                    payload=harness.store._claim_event_payload(extra_event),
                )
            )

        for binding in (wrong_id, extra_event, partial):
            classified = await harness.store.classify_evidence_bound_canary(binding)
            assert isinstance(classified, ClaimHumanGate)
            assert classified.failure is ClaimFailure.CORRUPTION

        wrong_identity = replace(extra_event, ledger_id="another-ledger")
        identity_result = await harness.store.classify_evidence_bound_canary(wrong_identity)
        assert isinstance(identity_result, ClaimHumanGate)
        assert identity_result.failure is ClaimFailure.LEDGER_MISMATCH


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identity_field",
    (
        "authorization_id",
        "authorization_sha256",
        "request_fingerprint",
        "plan_sha256",
        "execution_sha256",
    ),
)
async def test_cross_run_or_wrong_type_event_reusing_claim_identity_blocks_new_permit(
    migrated_ledger_database: MigrationDatabase,
    identity_field: str,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding(f"cross-run-event-{identity_field.replace('_', '-')}", database_now)
        event_run_id = f"other-run-{identity_field}"
        await _seed_runtime(harness, (binding,), database_now)
        async with harness.sessions.begin() as session:
            session.add(RunRecord(id=event_run_id, state=RunState.RUNNING.value))
            await session.flush()
            session.add(
                EventRecord(
                    id=f"cross-run-wrong-type-event-{identity_field}",
                    run_id=event_run_id,
                    event_type="audit.unexpected_claim_identity",
                    state=RunState.RUNNING.value,
                    occurred_at=database_now,
                    idempotency_key=f"cross-run-wrong-type-event-{identity_field}",
                    payload={identity_field: getattr(binding, identity_field)},
                )
            )

        result = await harness.store.claim_evidence_bound_canary(binding)

        assert isinstance(result, ClaimHumanGate)
        assert result.failure is ClaimFailure.CORRUPTION
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(0, 0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked_resource", ["run", "ledger_identity"])
async def test_lock_wait_crossing_expiry_reads_database_time_only_after_all_locks(
    migrated_ledger_database: MigrationDatabase,
    blocked_resource: str,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        initial_now = await _database_now(harness.sessions)
        initial_binding = _binding("lock-expiry", initial_now)
        await _seed_runtime(harness, (initial_binding,), initial_now)

        async with harness.engine.connect() as blocker:
            transaction = await blocker.begin()
            if blocked_resource == "run":
                await blocker.execute(
                    select(RunRecord.id)
                    .where(RunRecord.id == initial_binding.run_id)
                    .with_for_update()
                )
            else:
                await blocker.execute(
                    select(CanaryRuntimeIdentityRecord.singleton_id)
                    .where(
                        CanaryRuntimeIdentityRecord.singleton_id
                        == evidence_ledger.CANARY_LEDGER_SINGLETON_ID
                    )
                    .with_for_update()
                )
            start_time = await blocker.scalar(select(text("clock_timestamp()")))
            assert isinstance(start_time, datetime)
            deadline = start_time.astimezone(UTC) + timedelta(
                milliseconds=EXPIRY_GUARD_BAND_MS + 400
            )
            binding = replace(
                initial_binding,
                expires_at=deadline,
                evidence_valid_until=deadline,
                entitlement_valid_until=deadline,
            )
            claim_task = asyncio.create_task(harness.store.claim_evidence_bound_canary(binding))
            await asyncio.sleep(0.1)
            assert not claim_task.done()
            await asyncio.sleep(0.5)
            await transaction.commit()

        result = await claim_task
        assert isinstance(result, ClaimHumanGate)
        assert result.failure is ClaimFailure.NOT_CURRENT
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(0, 0, 0)


@pytest.mark.asyncio
async def test_commit_result_unknown_never_returns_permit_and_classifies_committed_claim(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("commit-unknown", database_now)
        await _seed_runtime(harness, (binding,), database_now)

        class LoseCommitAcknowledgementSession(Session):
            pass

        state = {"armed": True}

        def lose_first_commit_acknowledgement(_session: Session) -> None:
            if state["armed"]:
                state["armed"] = False
                raise OperationalError(
                    "COMMIT",
                    {},
                    OSError("injected lost commit acknowledgement"),
                    connection_invalidated=True,
                )

        event.listen(
            LoseCommitAcknowledgementSession,
            "after_commit",
            lose_first_commit_acknowledgement,
        )
        unknown_sessions = async_sessionmaker(
            harness.engine,
            expire_on_commit=False,
            sync_session_class=LoseCommitAcknowledgementSession,
        )
        unknown_store = PostgresCanaryLedgerStore(unknown_sessions)

        result = await unknown_store.claim_evidence_bound_canary(binding)

        assert state["armed"] is False
        assert isinstance(result, ClaimHumanGate)
        assert result.failure is ClaimFailure.SUBMISSION_UNKNOWN
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(1, 1, 1)
        classified = await harness.store.classify_evidence_bound_canary(binding)
        assert isinstance(classified, ClaimHumanGate)
        assert classified.failure is ClaimFailure.SUBMISSION_UNKNOWN


@pytest.mark.asyncio
async def test_ownership_commit_result_unknown_recovers_only_the_same_durable_task(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("ownership-commit-unknown", database_now)
        await _seed_runtime(harness, (binding,), database_now)
        claimed = await harness.store.claim_evidence_bound_canary(binding)
        assert isinstance(claimed, NewPostPermit)
        receipt = _receipt(claimed, "task-ownership-commit-unknown")

        class LoseOwnershipCommitAcknowledgementSession(Session):
            pass

        state = {"armed": True}

        def lose_first_commit_acknowledgement(_session: Session) -> None:
            if state["armed"]:
                state["armed"] = False
                raise OperationalError(
                    "COMMIT",
                    {},
                    OSError("injected lost ownership commit acknowledgement"),
                    connection_invalidated=True,
                )

        event.listen(
            LoseOwnershipCommitAcknowledgementSession,
            "after_commit",
            lose_first_commit_acknowledgement,
        )
        unknown_sessions = async_sessionmaker(
            harness.engine,
            expire_on_commit=False,
            sync_session_class=LoseOwnershipCommitAcknowledgementSession,
        )
        unknown_store = PostgresCanaryLedgerStore(unknown_sessions)

        recovered = await unknown_store.record_owned_task(receipt)

        assert state["armed"] is False
        assert isinstance(recovered, ResumeOwnedTask)
        assert recovered.provider_task_id == "task-ownership-commit-unknown"
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(1, 1, 2)
        repeated = await harness.store.record_owned_task(receipt)
        assert repeated == recovered
        assert await _claim_counts(harness.sessions, binding) == ClaimCounts(1, 1, 2)


@pytest.mark.asyncio
async def test_claim_ledger_rows_are_database_append_only_and_truncate_protected(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("append-only", database_now)
        await _seed_runtime(harness, (binding,), database_now)
        claimed = await harness.store.claim_evidence_bound_canary(binding)
        assert isinstance(claimed, NewPostPermit)

    statements = (
        "UPDATE canary_runtime_identity SET ledger_id = 'replacement-ledger'",
        "DELETE FROM canary_runtime_identity",
        "TRUNCATE canary_runtime_identity",
        "UPDATE generation_attempts SET evidence_ledger_id = 'replacement-ledger'",
        "DELETE FROM generation_attempts",
        "TRUNCATE generation_attempts",
        "UPDATE live_authorization_uses SET max_cost_cny = max_cost_cny",
        "DELETE FROM live_authorization_uses",
        "TRUNCATE live_authorization_uses",
        "UPDATE run_events SET state = state",
        "DELETE FROM run_events",
        "TRUNCATE run_events",
    )
    for statement in statements:
        with pytest.raises(DBAPIError):
            await _execute(database_url, statement)


@pytest.mark.asyncio
async def test_attempt_trigger_rejects_legacy_conversion_partial_deletion_and_owned_rebinding(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("attempt-trigger", database_now)
        await _seed_runtime(harness, (binding,), database_now)
        async with harness.sessions.begin() as session:
            session.add(
                AttemptRecord(
                    id="legacy-attempt-trigger",
                    run_id=binding.run_id,
                    job_id="legacy-job-trigger",
                    attempt=1,
                    state=RunState.RUNNING.value,
                    provider="fake",
                    model="legacy-model",
                    request_fingerprint=_sha256("legacy-trigger-request"),
                    attempt_state="RESERVED",
                )
            )

        with pytest.raises(DBAPIError, match="identity is immutable"):
            await _execute(
                database_url,
                "UPDATE generation_attempts SET "
                "evidence_authorization_id = 'legacy-conversion' "
                "WHERE id = 'legacy-attempt-trigger'",
            )

        claimed = await harness.store.claim_evidence_bound_canary(binding)
        assert isinstance(claimed, NewPostPermit)
        receipt = _receipt(claimed, "task-trigger-owned")
        owned = await harness.store.record_owned_task(receipt)
        assert isinstance(owned, ResumeOwnedTask)
        for assignment in (
            "provider_task_id = 'task-trigger-replacement'",
            "submitted_at = submitted_at + interval '1 second'",
            "evidence_acceptance_event_id = 'replacement-event'",
        ):
            with pytest.raises(DBAPIError, match="identity is immutable"):
                await _execute(
                    database_url,
                    f"UPDATE generation_attempts SET {assignment} "
                    f"WHERE id = '{evidence_ledger._attempt_id(binding)}'",
                )

    # Simulate a damaged pre-existing row. Even without the completeness constraint, the database
    # mutation trigger must preserve it for HUMAN_GATE reconciliation.
    await _execute(
        database_url,
        "ALTER TABLE generation_attempts DROP CONSTRAINT ck_attempt_evidence_bound_claim_complete",
    )
    await _execute(
        database_url,
        """
        INSERT INTO generation_attempts (
            id, run_id, job_id, attempt, state, evidence_runtime_release_sha256
        ) VALUES (
            'partial-evidence-attempt', 'run-attempt-trigger', 'partial-job', 1,
            'RUNNING', repeat('e', 64)
        )
        """,
    )
    with pytest.raises(DBAPIError, match="cannot be deleted"):
        await _execute(
            database_url,
            "DELETE FROM generation_attempts WHERE id = 'partial-evidence-attempt'",
        )


@pytest.mark.asyncio
async def test_partial_evidence_attempt_alone_blocks_truncate(
    migrated_ledger_database: MigrationDatabase,
) -> None:
    _, database_url = migrated_ledger_database
    await _execute(
        database_url,
        "INSERT INTO runs (id, state) VALUES ('partial-only-run', 'RUNNING')",
    )
    await _execute(
        database_url,
        "ALTER TABLE generation_attempts DROP CONSTRAINT ck_attempt_evidence_bound_claim_complete",
    )
    await _execute(
        database_url,
        """
        INSERT INTO generation_attempts (
            id, run_id, job_id, attempt, state, evidence_runtime_policy_sha256
        ) VALUES (
            'partial-only-attempt', 'partial-only-run', 'partial-only-job', 1,
            'RUNNING', repeat('f', 64)
        )
        """,
    )

    with pytest.raises(DBAPIError, match="contains evidence-bound claim state"):
        await _execute(database_url, "TRUNCATE generation_attempts")


def test_0008_empty_migration_round_trip(
    isolated_migration_database: MigrationDatabase,
) -> None:
    config, database_url = isolated_migration_database
    command.upgrade(config, "0008")
    assert asyncio.run(_current_revision(database_url)) == "0008"
    assert asyncio.run(_scalar(database_url, "SELECT count(*) FROM canary_runtime_identity")) == 0
    command.downgrade(config, "0007")
    assert asyncio.run(_current_revision(database_url)) == "0007"
    assert (
        asyncio.run(_scalar(database_url, "SELECT to_regclass('canary_runtime_identity')")) is None
    )

    command.upgrade(config, "0008")
    assert asyncio.run(_current_revision(database_url)) == "0008"
    assert asyncio.run(_scalar(database_url, "SELECT count(*) FROM canary_runtime_identity")) == 0


def test_0008_legacy_rows_are_lossless_across_upgrade_downgrade_and_upgrade(
    isolated_migration_database: MigrationDatabase,
) -> None:
    config, database_url = isolated_migration_database
    command.upgrade(config, "0007")
    asyncio.run(
        _execute(database_url, "INSERT INTO runs (id, state) VALUES ('legacy-run', 'RUNNING')")
    )
    asyncio.run(
        _execute(
            database_url,
            """
            INSERT INTO generation_attempts (
                id, run_id, job_id, attempt, state, provider, model,
                request_fingerprint, attempt_state
            ) VALUES (
                'legacy-attempt', 'legacy-run', 'legacy-job', 1, 'RUNNING',
                'fake', 'legacy-model', repeat('a', 64), 'RESERVED'
            )
            """,
        )
    )
    asyncio.run(
        _execute(
            database_url,
            """
            INSERT INTO live_authorization_uses (
                authorization_id, run_id, job_id, attempt, request_fingerprint,
                capability_snapshot_sha256, pricing_snapshot_sha256, max_cost_cny,
                consumed_at
            ) VALUES (
                'legacy-authorization', 'legacy-run', 'legacy-job', 1,
                repeat('b', 64), repeat('c', 64), repeat('d', 64), 1.0,
                '2026-08-16T00:00:00+00'
            )
            """,
        )
    )
    asyncio.run(
        _execute(
            database_url,
            """
            INSERT INTO run_events (
                id, run_id, event_type, state, occurred_at, idempotency_key, payload
            ) VALUES (
                'legacy-event', 'legacy-run', 'legacy.event', 'RUNNING',
                '2026-08-16T00:00:00+00', 'legacy-event', '{"kind":"legacy"}'::jsonb
            )
            """,
        )
    )

    command.upgrade(config, "0008")
    assert (
        asyncio.run(
            _scalar(
                database_url,
                "SELECT count(*) FROM generation_attempts "
                "WHERE id = 'legacy-attempt' AND evidence_authorization_id IS NULL "
                "AND evidence_acceptance_event_id IS NULL",
            )
        )
        == 1
    )
    assert (
        asyncio.run(
            _scalar(
                database_url,
                "SELECT event_type || ':' || state || ':' || (payload->>'kind') "
                "FROM run_events WHERE id = 'legacy-event'",
            )
        )
        == "legacy.event:RUNNING:legacy"
    )
    command.downgrade(config, "0007")
    assert (
        asyncio.run(
            _scalar(
                database_url,
                "SELECT count(*) FROM generation_attempts "
                "WHERE id = 'legacy-attempt' AND attempt_state = 'RESERVED'",
            )
        )
        == 1
    )
    assert (
        asyncio.run(
            _scalar(
                database_url,
                "SELECT event_type || ':' || state || ':' || (payload->>'kind') "
                "FROM run_events WHERE id = 'legacy-event'",
            )
        )
        == "legacy.event:RUNNING:legacy"
    )
    assert (
        asyncio.run(
            _scalar(
                database_url,
                "SELECT count(*) FROM live_authorization_uses "
                "WHERE authorization_id = 'legacy-authorization'",
            )
        )
        == 1
    )
    command.upgrade(config, "0008")
    assert asyncio.run(_current_revision(database_url)) == "0008"


async def _seed_identity_for_downgrade(database_url: URL) -> None:
    async with _ledger_harness(database_url) as harness:
        database_now = await _database_now(harness.sessions)
        binding = _binding("downgrade-block", database_now)
        await _seed_runtime(harness, (binding,), database_now)


def test_0008_downgrade_fails_closed_when_runtime_identity_exists(
    isolated_migration_database: MigrationDatabase,
) -> None:
    config, database_url = isolated_migration_database
    command.upgrade(config, "0008")
    asyncio.run(_seed_identity_for_downgrade(database_url))

    with pytest.raises(DBAPIError, match="cannot downgrade 0008"):
        command.downgrade(config, "0007")

    assert asyncio.run(_current_revision(database_url)) == "0008"
    assert asyncio.run(_scalar(database_url, "SELECT count(*) FROM canary_runtime_identity")) == 1
