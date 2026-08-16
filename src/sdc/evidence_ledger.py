"""Atomic PostgreSQL ledger for the inert evidence-bound Canary claim.

This module deliberately contains no Worker, Temporal, Provider, secret, or network integration.
It only proves the durable claim boundary described by SDC-ADR-018.  A successful transaction
returns a process-local permit, but no supported runtime consumes that permit in this delivery.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from threading import Lock
from typing import Final, Literal, NoReturn, SupportsIndex

from sqlalchemy import insert, or_, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sdc.compiler import stable_id
from sdc.contracts import ProviderTaskState, RunState
from sdc.persistence import (
    AttemptRecord,
    CanaryRuntimeIdentityRecord,
    EventRecord,
    LiveAuthorizationUseRecord,
    RunRecord,
)

CANARY_LEDGER_SINGLETON_ID: Final = 1
CANARY_PROVIDER: Final = "volcengine_ark"
CANARY_MODEL: Final = "doubao-seedance-2-0-260128"
CANARY_REGION: Final = "cn-beijing"
CANARY_OPERATION: Final = "contents.generations.tasks.create"
CANARY_ATTEMPT: Final = 1
POST_IN_FLIGHT: Final = "POST_IN_FLIGHT"
CLAIM_TO_SOCKET_MAX_MS: Final = 10_000
EXPIRY_GUARD_BAND_MS: Final = 30_000
CLAIM_EVENT_TYPE: Final = "provider.evidence_bound_claimed"
ACCEPTANCE_EVENT_TYPE: Final = "provider.evidence_bound_submission_accepted"

_RESUMABLE_ATTEMPT_STATES: Final = frozenset({"SUBMITTED", "WATCHING", "DOWNLOADING", "VERIFIED"})
_KNOWN_PROVIDER_STATES: Final = frozenset(state.value for state in ProviderTaskState)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_PERMIT_FACTORY: Final = object()
_NO_EXISTING: Final = object()


class ClaimFailure(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    NOT_CURRENT = "NOT_CURRENT"
    LEDGER_MISMATCH = "LEDGER_MISMATCH"
    SUBMISSION_UNKNOWN = "SUBMISSION_UNKNOWN"
    CONFLICT = "CONFLICT"
    CORRUPTION = "CORRUPTION"
    TRANSACTION_REJECTED = "TRANSACTION_REJECTED"
    COMMIT_RESULT_UNKNOWN = "COMMIT_RESULT_UNKNOWN"


@dataclass(frozen=True, slots=True)
class ClaimHumanGate:
    disposition: Literal["HUMAN_GATE"]
    failure: ClaimFailure
    detail: str


@dataclass(frozen=True, slots=True)
class ResumeOwnedTask:
    disposition: Literal["RESUME_OWNED_TASK"]
    run_id: str
    job_id: str
    attempt: Literal[1]
    provider_task_id: str
    authorization_sha256: str
    request_fingerprint: str
    submitted_at: datetime


class _NewPostPermit:
    """Non-serializable, single-consumption proof of one newly committed claim."""

    __slots__ = (
        "_authorization_sha256",
        "_claim_event_id",
        "_claimed_at",
        "_consumed",
        "_binding",
        "_lock",
        "_receipt_issued",
    )

    def __init__(
        self,
        factory: object,
        *,
        authorization_sha256: str,
        claim_event_id: str,
        claimed_at: datetime,
        binding: _EvidenceBoundClaimBinding,
    ) -> None:
        if factory is not _PERMIT_FACTORY:
            raise TypeError("a post permit can only follow a newly committed claim")
        self._authorization_sha256 = authorization_sha256
        self._claim_event_id = claim_event_id
        self._claimed_at = claimed_at
        self._binding = binding
        self._consumed = False
        self._receipt_issued = False
        self._lock = Lock()

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(self, name):
            raise AttributeError("post permit fields are immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, _name: str) -> NoReturn:
        raise AttributeError("post permit fields are immutable")

    @property
    def authorization_sha256(self) -> str:
        return self._authorization_sha256

    @property
    def claim_event_id(self) -> str:
        return self._claim_event_id

    @property
    def claimed_at(self) -> datetime:
        return self._claimed_at

    def consume(self) -> None:
        """Consume the process-local capability exactly once without performing I/O."""
        with self._lock:
            if self._consumed:
                raise RuntimeError("post permit was already consumed")
            object.__setattr__(self, "_consumed", True)

    def submitted_receipt(
        self,
        provider_task_id: str,
        provider_state: ProviderTaskState,
    ) -> _SubmittedClaimReceipt:
        """Issue one non-authorizing receipt after this permit has been consumed."""
        if _TASK_ID.fullmatch(provider_task_id) is None:
            raise ValueError("Provider task ID is malformed")
        if not isinstance(provider_state, ProviderTaskState):
            raise TypeError("Provider state must be a ProviderTaskState")
        with self._lock:
            if not self._consumed:
                raise RuntimeError("post permit must be consumed before recording acceptance")
            if self._receipt_issued:
                raise RuntimeError("a submitted claim receipt was already issued")
            object.__setattr__(self, "_receipt_issued", True)
            return _SubmittedClaimReceipt(
                _PERMIT_FACTORY,
                binding=self._binding,
                authorization_sha256=self._authorization_sha256,
                claim_event_id=self._claim_event_id,
                claimed_at=self._claimed_at,
                provider_task_id=provider_task_id,
                provider_state=provider_state.value,
            )

    def __copy__(self) -> NoReturn:
        raise TypeError("post permits cannot be copied")

    def __deepcopy__(self, _memo: dict[int, object]) -> NoReturn:
        raise TypeError("post permits cannot be copied")

    def __reduce_ex__(self, _protocol: SupportsIndex) -> NoReturn:
        raise TypeError("post permits cannot be serialized")


@dataclass(frozen=True, slots=True)
class NewPostPermit:
    disposition: Literal["NEW_POST_PERMIT"]
    permit: _NewPostPermit


CanaryClaimResult = NewPostPermit | ResumeOwnedTask | ClaimHumanGate


class _SubmittedClaimReceipt:
    """Process-local proof of one safely parsed response; it cannot authorize another POST."""

    __slots__ = (
        "_authorization_sha256",
        "_binding",
        "_claim_event_id",
        "_claimed_at",
        "_provider_state",
        "_provider_task_id",
    )

    def __init__(
        self,
        factory: object,
        *,
        binding: _EvidenceBoundClaimBinding,
        authorization_sha256: str,
        claim_event_id: str,
        claimed_at: datetime,
        provider_task_id: str,
        provider_state: str,
    ) -> None:
        if factory is not _PERMIT_FACTORY:
            raise TypeError("a submitted claim receipt can only follow a consumed post permit")
        self._binding = binding
        self._authorization_sha256 = authorization_sha256
        self._claim_event_id = claim_event_id
        self._claimed_at = claimed_at
        self._provider_task_id = provider_task_id
        self._provider_state = provider_state

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(self, name):
            raise AttributeError("submitted claim receipt fields are immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, _name: str) -> NoReturn:
        raise AttributeError("submitted claim receipt fields are immutable")

    def __copy__(self) -> NoReturn:
        raise TypeError("submitted claim receipts cannot be copied")

    def __deepcopy__(self, _memo: dict[int, object]) -> NoReturn:
        raise TypeError("submitted claim receipts cannot be copied")

    def __reduce_ex__(self, _protocol: SupportsIndex) -> NoReturn:
        raise TypeError("submitted claim receipts cannot be serialized")


@dataclass(frozen=True, slots=True)
class _EvidenceBoundClaimBinding:
    """Inert values supplied by the future private trust loader; not a live authority."""

    authorization_id: str
    authorization_sha256: str
    plan_sha256: str
    execution_sha256: str
    submission_policy_sha256: str
    runtime_policy_sha256: str
    runtime_release_sha256: str
    evidence_bundle_id: str
    evidence_logical_tree_sha256: str
    evidence_valid_until: datetime
    entitlement_anchor_sha256: str
    entitlement_valid_until: datetime
    task_queue: str
    ledger_id: str
    deployment_id: str
    run_id: str
    job_id: str
    request_fingerprint: str
    capability_snapshot_sha256: str
    pricing_snapshot_sha256: str
    worst_case_cost_cny: Decimal
    max_cost_cny: Decimal
    authorized_at: datetime
    expires_at: datetime
    nonce_sha256: str

    def __post_init__(self) -> None:
        for field in (
            "authorization_sha256",
            "plan_sha256",
            "execution_sha256",
            "submission_policy_sha256",
            "runtime_policy_sha256",
            "runtime_release_sha256",
            "evidence_bundle_id",
            "evidence_logical_tree_sha256",
            "entitlement_anchor_sha256",
            "request_fingerprint",
            "capability_snapshot_sha256",
            "pricing_snapshot_sha256",
            "nonce_sha256",
        ):
            if _SHA256.fullmatch(str(getattr(self, field))) is None:
                raise ValueError(f"{field} must be lowercase SHA-256")
        for field in (
            "authorization_id",
            "task_queue",
            "ledger_id",
            "deployment_id",
        ):
            if _IDENTIFIER.fullmatch(str(getattr(self, field))) is None:
                raise ValueError(f"{field} is not a portable identifier")
        for field in ("run_id", "job_id"):
            value = str(getattr(self, field))
            if not value or len(value) > 256 or any(ord(character) < 32 for character in value):
                raise ValueError(f"{field} is invalid")
        for field in (
            "evidence_valid_until",
            "entitlement_valid_until",
            "authorized_at",
            "expires_at",
        ):
            value = getattr(self, field)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field} must include a timezone")
            object.__setattr__(self, field, value.astimezone(UTC))
        if self.authorized_at >= self.expires_at:
            raise ValueError("authorization window is invalid")
        if self.expires_at > min(self.evidence_valid_until, self.entitlement_valid_until):
            raise ValueError("authorization exceeds an evidence deadline")
        if self.worst_case_cost_cny <= 0:
            raise ValueError("worst-case cost must be positive")
        if self.max_cost_cny < self.worst_case_cost_cny or self.max_cost_cny > Decimal("15"):
            raise ValueError("authorization cost does not cover the reviewed bounded cost")


@dataclass(frozen=True, slots=True)
class _PendingPermit:
    authorization_sha256: str
    claim_event_id: str
    claimed_at: datetime


@dataclass(frozen=True, slots=True)
class _PendingOwnedTask:
    provider_task_id: str
    provider_state: str
    submitted_at: datetime


@dataclass(frozen=True, slots=True)
class _LedgerRows:
    attempts: tuple[AttemptRecord, ...]
    authorizations: tuple[LiveAuthorizationUseRecord, ...]
    claim_events: tuple[EventRecord, ...]
    acceptance_events: tuple[EventRecord, ...]
    unexpected_events: tuple[EventRecord, ...]


def _claim_event_key(binding: _EvidenceBoundClaimBinding) -> str:
    return f"{binding.job_id}:{CANARY_ATTEMPT}:evidence-bound-claim"


def _claim_event_id(binding: _EvidenceBoundClaimBinding) -> str:
    return stable_id("event", [binding.run_id, _claim_event_key(binding)])


def _acceptance_event_key(binding: _EvidenceBoundClaimBinding) -> str:
    return f"{binding.job_id}:{CANARY_ATTEMPT}:evidence-bound-submitted"


def _acceptance_event_id(binding: _EvidenceBoundClaimBinding) -> str:
    return stable_id("event", [binding.run_id, _acceptance_event_key(binding)])


def _attempt_id(binding: _EvidenceBoundClaimBinding) -> str:
    return stable_id("attempt", [binding.run_id, binding.job_id, CANARY_ATTEMPT])


def _utc_equal(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return left is right
    if left.tzinfo is None or left.utcoffset() is None:
        return False
    if right.tzinfo is None or right.utcoffset() is None:
        return False
    return left.astimezone(UTC) == right.astimezone(UTC)


def _human_gate(failure: ClaimFailure, detail: str) -> ClaimHumanGate:
    return ClaimHumanGate(disposition="HUMAN_GATE", failure=failure, detail=detail)


class PostgresCanaryLedgerStore:
    """Dedicated, non-retrying PostgreSQL boundary for one evidence-bound Canary POST."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def claim_evidence_bound_canary(
        self,
        binding: _EvidenceBoundClaimBinding,
    ) -> CanaryClaimResult:
        pending: _PendingPermit | None = None
        try:
            async with self._sessions() as session:
                async with session.begin():
                    run = await session.scalar(
                        select(RunRecord).where(RunRecord.id == binding.run_id).with_for_update()
                    )
                    if run is None:
                        return _human_gate(ClaimFailure.NOT_FOUND, "exact Run does not exist")

                    identity = await session.scalar(
                        select(CanaryRuntimeIdentityRecord)
                        .where(
                            CanaryRuntimeIdentityRecord.singleton_id == CANARY_LEDGER_SINGLETON_ID
                        )
                        .with_for_update()
                    )
                    if identity is None:
                        return _human_gate(
                            ClaimFailure.NOT_FOUND,
                            "Canary ledger identity is not configured",
                        )
                    ledger_failure = self._validate_identity(identity, binding)
                    if ledger_failure is not None:
                        return ledger_failure

                    db_now = await session.scalar(select(text("clock_timestamp()")))
                    if not isinstance(db_now, datetime):
                        return _human_gate(
                            ClaimFailure.CORRUPTION,
                            "database clock did not return a timestamp",
                        )
                    if db_now.tzinfo is None or db_now.utcoffset() is None:
                        return _human_gate(
                            ClaimFailure.CORRUPTION,
                            "database clock returned a naive timestamp",
                        )
                    db_now = db_now.astimezone(UTC)

                    existing = await self._classify_rows(
                        session,
                        binding,
                        run_state=run.state,
                    )
                    if existing is not _NO_EXISTING:
                        assert isinstance(existing, (ResumeOwnedTask, ClaimHumanGate))
                        return existing

                    if run.state != RunState.RUNNING.value:
                        return _human_gate(
                            ClaimFailure.NOT_ELIGIBLE,
                            "Run is not eligible for a new Canary claim",
                        )
                    current_failure = self._validate_claim_time(binding, db_now)
                    if current_failure is not None:
                        return current_failure

                    claim_event_id = _claim_event_id(binding)
                    await session.execute(
                        insert(AttemptRecord).values(
                            id=_attempt_id(binding),
                            run_id=binding.run_id,
                            job_id=binding.job_id,
                            attempt=CANARY_ATTEMPT,
                            state=RunState.RUNNING.value,
                            provider=CANARY_PROVIDER,
                            model=CANARY_MODEL,
                            request_fingerprint=binding.request_fingerprint,
                            attempt_state=POST_IN_FLIGHT,
                            evidence_authorization_id=binding.authorization_id,
                            evidence_authorization_sha256=binding.authorization_sha256,
                            evidence_runtime_release_sha256=binding.runtime_release_sha256,
                            evidence_runtime_policy_sha256=binding.runtime_policy_sha256,
                            evidence_task_queue=binding.task_queue,
                            evidence_ledger_id=binding.ledger_id,
                            evidence_deployment_id=binding.deployment_id,
                            evidence_claim_event_id=claim_event_id,
                            evidence_claimed_at=db_now,
                            evidence_claim_state=POST_IN_FLIGHT,
                        )
                    )
                    await session.execute(
                        insert(LiveAuthorizationUseRecord).values(
                            authorization_id=binding.authorization_id,
                            run_id=binding.run_id,
                            job_id=binding.job_id,
                            attempt=CANARY_ATTEMPT,
                            request_fingerprint=binding.request_fingerprint,
                            capability_snapshot_sha256=binding.capability_snapshot_sha256,
                            pricing_snapshot_sha256=binding.pricing_snapshot_sha256,
                            max_cost_cny=binding.max_cost_cny,
                            consumed_at=db_now,
                            authorization_document_type=("sdc.evidence-bound-live-authorization"),
                            authorization_sha256=binding.authorization_sha256,
                            evidence_bound_plan_sha256=binding.plan_sha256,
                            execution_sha256=binding.execution_sha256,
                            submission_policy_sha256=binding.submission_policy_sha256,
                            runtime_policy_sha256=binding.runtime_policy_sha256,
                            runtime_release_sha256=binding.runtime_release_sha256,
                            evidence_bundle_id=binding.evidence_bundle_id,
                            evidence_logical_tree_sha256=(binding.evidence_logical_tree_sha256),
                            evidence_valid_until=binding.evidence_valid_until,
                            entitlement_anchor_sha256=binding.entitlement_anchor_sha256,
                            entitlement_valid_until=binding.entitlement_valid_until,
                            provider_region=CANARY_REGION,
                            task_queue=binding.task_queue,
                            ledger_id=binding.ledger_id,
                            authorized_at=binding.authorized_at,
                            expires_at=binding.expires_at,
                            nonce_sha256=binding.nonce_sha256,
                            claim_state=POST_IN_FLIGHT,
                        )
                    )
                    await session.execute(
                        insert(EventRecord).values(
                            id=claim_event_id,
                            run_id=binding.run_id,
                            event_type=CLAIM_EVENT_TYPE,
                            state=RunState.RUNNING.value,
                            occurred_at=db_now,
                            idempotency_key=_claim_event_key(binding),
                            payload=self._claim_event_payload(binding),
                        )
                    )
                    pending = _PendingPermit(
                        authorization_sha256=binding.authorization_sha256,
                        claim_event_id=claim_event_id,
                        claimed_at=db_now,
                    )
        except IntegrityError:
            return await self._classify_after_failure(binding, ClaimFailure.CONFLICT)
        except DBAPIError:
            return await self._classify_after_failure(
                binding,
                ClaimFailure.COMMIT_RESULT_UNKNOWN,
            )
        except asyncio.CancelledError:
            raise
        except SQLAlchemyError:
            return await self._classify_after_failure(
                binding,
                ClaimFailure.TRANSACTION_REJECTED,
            )

        if pending is None:
            return _human_gate(
                ClaimFailure.COMMIT_RESULT_UNKNOWN,
                "claim transaction completed without a durable permit result",
            )
        return NewPostPermit(
            disposition="NEW_POST_PERMIT",
            permit=_NewPostPermit(
                _PERMIT_FACTORY,
                authorization_sha256=pending.authorization_sha256,
                claim_event_id=pending.claim_event_id,
                claimed_at=pending.claimed_at,
                binding=binding,
            ),
        )

    async def record_owned_task(
        self,
        receipt: _SubmittedClaimReceipt,
    ) -> ResumeOwnedTask | ClaimHumanGate:
        """Atomically bind one safely parsed task ID to its exact committed claim."""
        if not isinstance(receipt, _SubmittedClaimReceipt):
            return _human_gate(
                ClaimFailure.NOT_ELIGIBLE,
                "task ownership requires a private submitted claim receipt",
            )
        binding = receipt._binding
        if not self._receipt_matches_binding(receipt, binding):
            return _human_gate(
                ClaimFailure.CONFLICT,
                "submitted claim receipt does not match the durable claim binding",
            )

        pending: _PendingOwnedTask | None = None
        try:
            async with self._sessions() as session:
                async with session.begin():
                    run = await session.scalar(
                        select(RunRecord).where(RunRecord.id == binding.run_id).with_for_update()
                    )
                    if run is None:
                        return _human_gate(ClaimFailure.NOT_FOUND, "exact Run does not exist")
                    identity = await session.scalar(
                        select(CanaryRuntimeIdentityRecord)
                        .where(
                            CanaryRuntimeIdentityRecord.singleton_id == CANARY_LEDGER_SINGLETON_ID
                        )
                        .with_for_update()
                    )
                    if identity is None:
                        return _human_gate(
                            ClaimFailure.NOT_FOUND,
                            "Canary ledger identity is not configured",
                        )
                    ledger_failure = self._validate_identity(identity, binding)
                    if ledger_failure is not None:
                        return ledger_failure

                    rows = await self._load_rows(session, binding, lock_attempts=True)
                    classified = self._classify_loaded_rows(
                        rows,
                        binding,
                        run_state=run.state,
                    )
                    if isinstance(classified, ResumeOwnedTask):
                        if classified.provider_task_id != receipt._provider_task_id:
                            return _human_gate(
                                ClaimFailure.CONFLICT,
                                "durable claim already owns a different Provider task",
                            )
                        return classified
                    if not (
                        isinstance(classified, ClaimHumanGate)
                        and classified.failure == ClaimFailure.SUBMISSION_UNKNOWN
                    ):
                        if classified is _NO_EXISTING:
                            return _human_gate(
                                ClaimFailure.CORRUPTION,
                                "submitted receipt has no durable claim",
                            )
                        assert isinstance(classified, ClaimHumanGate)
                        return classified

                    attempt = rows.attempts[0]
                    if (
                        attempt.attempt_state != POST_IN_FLIGHT
                        or attempt.state != RunState.RUNNING.value
                        or attempt.provider_task_id is not None
                        or attempt.provider_state is not None
                        or attempt.submitted_at is not None
                        or rows.acceptance_events
                    ):
                        return _human_gate(
                            ClaimFailure.CORRUPTION,
                            "claim is not in the exact pre-ownership state",
                        )

                    db_now = await session.scalar(select(text("clock_timestamp()")))
                    if not isinstance(db_now, datetime):
                        return _human_gate(
                            ClaimFailure.CORRUPTION,
                            "database clock did not return a timestamp",
                        )
                    if db_now.tzinfo is None or db_now.utcoffset() is None:
                        return _human_gate(
                            ClaimFailure.CORRUPTION,
                            "database clock returned a naive timestamp",
                        )
                    db_now = db_now.astimezone(UTC)

                    updated_id = await session.scalar(
                        update(AttemptRecord)
                        .where(
                            AttemptRecord.id == _attempt_id(binding),
                            AttemptRecord.run_id == binding.run_id,
                            AttemptRecord.job_id == binding.job_id,
                            AttemptRecord.attempt == CANARY_ATTEMPT,
                            AttemptRecord.attempt_state == POST_IN_FLIGHT,
                            AttemptRecord.provider_task_id.is_(None),
                            AttemptRecord.submitted_at.is_(None),
                            AttemptRecord.evidence_authorization_id == binding.authorization_id,
                            AttemptRecord.evidence_authorization_sha256
                            == binding.authorization_sha256,
                            AttemptRecord.evidence_claim_event_id == receipt._claim_event_id,
                            AttemptRecord.evidence_claimed_at == receipt._claimed_at,
                        )
                        .values(
                            provider_task_id=receipt._provider_task_id,
                            provider_state=receipt._provider_state,
                            attempt_state="SUBMITTED",
                            submitted_at=db_now,
                            evidence_acceptance_event_id=_acceptance_event_id(binding),
                        )
                        .returning(AttemptRecord.id)
                    )
                    if updated_id != _attempt_id(binding):
                        raise RuntimeError("ownership update did not affect exactly one claim")
                    await session.execute(
                        insert(EventRecord).values(
                            id=_acceptance_event_id(binding),
                            run_id=binding.run_id,
                            event_type=ACCEPTANCE_EVENT_TYPE,
                            state=RunState.RUNNING.value,
                            occurred_at=db_now,
                            idempotency_key=_acceptance_event_key(binding),
                            payload=self._acceptance_event_payload(
                                binding,
                                provider_task_id=receipt._provider_task_id,
                                provider_state=receipt._provider_state,
                            ),
                        )
                    )
                    pending = _PendingOwnedTask(
                        provider_task_id=receipt._provider_task_id,
                        provider_state=receipt._provider_state,
                        submitted_at=db_now,
                    )
        except IntegrityError:
            return await self._classify_owned_after_failure(
                receipt,
                ClaimFailure.CONFLICT,
            )
        except DBAPIError:
            return await self._classify_owned_after_failure(
                receipt,
                ClaimFailure.COMMIT_RESULT_UNKNOWN,
            )
        except asyncio.CancelledError:
            raise
        except (RuntimeError, SQLAlchemyError):
            return await self._classify_owned_after_failure(
                receipt,
                ClaimFailure.TRANSACTION_REJECTED,
            )

        if pending is None:
            return _human_gate(
                ClaimFailure.COMMIT_RESULT_UNKNOWN,
                "ownership transaction completed without a durable result",
            )
        if pending.provider_state in {"failed", "cancelled", "expired"}:
            return _human_gate(
                ClaimFailure.NOT_ELIGIBLE,
                "owned Provider task was accepted in a terminal failure state",
            )
        return ResumeOwnedTask(
            disposition="RESUME_OWNED_TASK",
            run_id=binding.run_id,
            job_id=binding.job_id,
            attempt=CANARY_ATTEMPT,
            provider_task_id=pending.provider_task_id,
            authorization_sha256=binding.authorization_sha256,
            request_fingerprint=binding.request_fingerprint,
            submitted_at=pending.submitted_at,
        )

    async def classify_evidence_bound_canary(
        self,
        binding: _EvidenceBoundClaimBinding,
    ) -> ResumeOwnedTask | ClaimHumanGate:
        """Classify durable state in a transaction that PostgreSQL enforces as read-only."""
        try:
            async with self._sessions() as session:
                async with session.begin():
                    await session.execute(
                        text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                    )
                    run = await session.scalar(
                        select(RunRecord).where(RunRecord.id == binding.run_id)
                    )
                    if run is None:
                        return _human_gate(ClaimFailure.NOT_FOUND, "exact Run does not exist")
                    identity = await session.scalar(
                        select(CanaryRuntimeIdentityRecord).where(
                            CanaryRuntimeIdentityRecord.singleton_id == CANARY_LEDGER_SINGLETON_ID
                        )
                    )
                    if identity is None:
                        return _human_gate(
                            ClaimFailure.NOT_FOUND,
                            "Canary ledger identity is not configured",
                        )
                    ledger_failure = self._validate_identity(identity, binding)
                    if ledger_failure is not None:
                        return ledger_failure
                    result = await self._classify_rows(
                        session,
                        binding,
                        run_state=run.state,
                    )
                    if result is _NO_EXISTING:
                        return _human_gate(
                            ClaimFailure.NOT_FOUND,
                            "no durable evidence-bound claim exists",
                        )
                    assert isinstance(result, (ResumeOwnedTask, ClaimHumanGate))
                    return result
        except (DBAPIError, SQLAlchemyError):
            return _human_gate(
                ClaimFailure.COMMIT_RESULT_UNKNOWN,
                "durable claim state could not be classified",
            )

    async def _classify_after_failure(
        self,
        binding: _EvidenceBoundClaimBinding,
        absent_failure: ClaimFailure,
    ) -> ResumeOwnedTask | ClaimHumanGate:
        classified = await self.classify_evidence_bound_canary(binding)
        if isinstance(classified, ClaimHumanGate) and classified.failure == ClaimFailure.NOT_FOUND:
            return _human_gate(
                absent_failure,
                "claim transaction failed without a safely classifiable result",
            )
        return classified

    async def _classify_owned_after_failure(
        self,
        receipt: _SubmittedClaimReceipt,
        absent_failure: ClaimFailure,
    ) -> ResumeOwnedTask | ClaimHumanGate:
        classified = await self.classify_evidence_bound_canary(receipt._binding)
        if isinstance(classified, ResumeOwnedTask):
            if classified.provider_task_id == receipt._provider_task_id:
                return classified
            return _human_gate(
                ClaimFailure.CONFLICT,
                "ownership transaction conflicts with a different Provider task",
            )
        if classified.failure == ClaimFailure.NOT_FOUND:
            return _human_gate(
                absent_failure,
                "ownership transaction failed without a safely classifiable result",
            )
        if (
            absent_failure == ClaimFailure.CONFLICT
            and classified.failure == ClaimFailure.SUBMISSION_UNKNOWN
        ):
            return _human_gate(
                ClaimFailure.CONFLICT,
                "Provider task ownership conflicts with another durable claim",
            )
        return classified

    @staticmethod
    def _receipt_matches_binding(
        receipt: _SubmittedClaimReceipt,
        binding: _EvidenceBoundClaimBinding,
    ) -> bool:
        return (
            receipt._binding is binding
            and receipt._authorization_sha256 == binding.authorization_sha256
            and receipt._claim_event_id == _claim_event_id(binding)
            and receipt._provider_state in _KNOWN_PROVIDER_STATES
            and _TASK_ID.fullmatch(receipt._provider_task_id) is not None
        )

    @staticmethod
    def _claim_event_payload(binding: _EvidenceBoundClaimBinding) -> dict[str, object]:
        return {
            "attempt": CANARY_ATTEMPT,
            "authorization_id": binding.authorization_id,
            "authorization_sha256": binding.authorization_sha256,
            "deployment_id": binding.deployment_id,
            "entitlement_anchor_sha256": binding.entitlement_anchor_sha256,
            "evidence_bundle_id": binding.evidence_bundle_id,
            "evidence_logical_tree_sha256": binding.evidence_logical_tree_sha256,
            "execution_sha256": binding.execution_sha256,
            "job_id": binding.job_id,
            "ledger_id": binding.ledger_id,
            "plan_sha256": binding.plan_sha256,
            "request_fingerprint": binding.request_fingerprint,
            "runtime_policy_sha256": binding.runtime_policy_sha256,
            "runtime_release_sha256": binding.runtime_release_sha256,
            "submission_policy_sha256": binding.submission_policy_sha256,
            "task_queue": binding.task_queue,
        }

    @staticmethod
    def _acceptance_event_payload(
        binding: _EvidenceBoundClaimBinding,
        *,
        provider_task_id: str,
        provider_state: str,
    ) -> dict[str, object]:
        return {
            "attempt": CANARY_ATTEMPT,
            "authorization_sha256": binding.authorization_sha256,
            "job_id": binding.job_id,
            "provider_state": provider_state,
            "provider_task_id": provider_task_id,
            "request_fingerprint": binding.request_fingerprint,
        }

    @staticmethod
    def _validate_identity(
        identity: CanaryRuntimeIdentityRecord,
        binding: _EvidenceBoundClaimBinding,
    ) -> ClaimHumanGate | None:
        expected = {
            "ledger_id": binding.ledger_id,
            "deployment_id": binding.deployment_id,
            "runtime_release_sha256": binding.runtime_release_sha256,
            "runtime_policy_sha256": binding.runtime_policy_sha256,
            "task_queue": binding.task_queue,
            "provider": CANARY_PROVIDER,
            "model": CANARY_MODEL,
            "region": CANARY_REGION,
            "operation": CANARY_OPERATION,
            "claim_to_socket_max_ms": CLAIM_TO_SOCKET_MAX_MS,
            "expiry_guard_band_ms": EXPIRY_GUARD_BAND_MS,
        }
        if identity.singleton_id != CANARY_LEDGER_SINGLETON_ID or any(
            getattr(identity, field) != value for field, value in expected.items()
        ):
            return _human_gate(
                ClaimFailure.LEDGER_MISMATCH,
                "durable Canary ledger identity does not match the reviewed binding",
            )
        return None

    @staticmethod
    def _validate_claim_time(
        binding: _EvidenceBoundClaimBinding,
        db_now: datetime,
    ) -> ClaimHumanGate | None:
        if db_now < binding.authorized_at:
            return _human_gate(
                ClaimFailure.NOT_CURRENT,
                "authorization is not active at database time",
            )
        guarded = db_now + timedelta(milliseconds=EXPIRY_GUARD_BAND_MS)
        if any(
            guarded >= deadline
            for deadline in (
                binding.expires_at,
                binding.evidence_valid_until,
                binding.entitlement_valid_until,
            )
        ):
            return _human_gate(
                ClaimFailure.NOT_CURRENT,
                "database time is inside the exclusive Canary expiry guard band",
            )
        return None

    async def _classify_rows(
        self,
        session: AsyncSession,
        binding: _EvidenceBoundClaimBinding,
        *,
        run_state: str,
    ) -> object | ResumeOwnedTask | ClaimHumanGate:
        rows = await self._load_rows(session, binding, lock_attempts=False)
        return self._classify_loaded_rows(rows, binding, run_state=run_state)

    async def _load_rows(
        self,
        session: AsyncSession,
        binding: _EvidenceBoundClaimBinding,
        *,
        lock_attempts: bool,
    ) -> _LedgerRows:
        attempt_query = select(AttemptRecord).where(
            or_(
                (
                    (AttemptRecord.run_id == binding.run_id)
                    & (AttemptRecord.job_id == binding.job_id)
                ),
                AttemptRecord.evidence_authorization_id == binding.authorization_id,
                AttemptRecord.evidence_authorization_sha256 == binding.authorization_sha256,
                AttemptRecord.request_fingerprint == binding.request_fingerprint,
            )
        )
        if lock_attempts:
            attempt_query = attempt_query.with_for_update()
        attempts = tuple((await session.scalars(attempt_query)).all())
        authorizations = tuple(
            (
                await session.scalars(
                    select(LiveAuthorizationUseRecord).where(
                        or_(
                            LiveAuthorizationUseRecord.authorization_id == binding.authorization_id,
                            LiveAuthorizationUseRecord.authorization_sha256
                            == binding.authorization_sha256,
                            LiveAuthorizationUseRecord.evidence_bound_plan_sha256
                            == binding.plan_sha256,
                            LiveAuthorizationUseRecord.nonce_sha256 == binding.nonce_sha256,
                            LiveAuthorizationUseRecord.request_fingerprint
                            == binding.request_fingerprint,
                            (
                                (LiveAuthorizationUseRecord.run_id == binding.run_id)
                                & (LiveAuthorizationUseRecord.job_id == binding.job_id)
                                & (LiveAuthorizationUseRecord.attempt == CANARY_ATTEMPT)
                            ),
                        )
                    )
                )
            ).all()
        )
        event_types = (CLAIM_EVENT_TYPE, ACCEPTANCE_EVENT_TYPE)
        expected_event_ids = (_claim_event_id(binding), _acceptance_event_id(binding))
        events = tuple(
            (
                await session.scalars(
                    select(EventRecord).where(
                        or_(
                            EventRecord.id.in_(expected_event_ids),
                            (
                                (EventRecord.run_id == binding.run_id)
                                & or_(
                                    EventRecord.event_type.like("provider.%"),
                                    EventRecord.event_type.like("canary.%"),
                                )
                            ),
                            EventRecord.payload.contains(
                                {"authorization_id": binding.authorization_id}
                            ),
                            EventRecord.payload.contains(
                                {"authorization_sha256": binding.authorization_sha256}
                            ),
                            EventRecord.payload.contains(
                                {"request_fingerprint": binding.request_fingerprint}
                            ),
                            EventRecord.payload.contains({"plan_sha256": binding.plan_sha256}),
                            EventRecord.payload.contains(
                                {"execution_sha256": binding.execution_sha256}
                            ),
                        )
                    )
                )
            ).all()
        )
        return _LedgerRows(
            attempts=attempts,
            authorizations=authorizations,
            claim_events=tuple(event for event in events if event.event_type == CLAIM_EVENT_TYPE),
            acceptance_events=tuple(
                event for event in events if event.event_type == ACCEPTANCE_EVENT_TYPE
            ),
            unexpected_events=tuple(
                event for event in events if event.event_type not in event_types
            ),
        )

    def _classify_loaded_rows(
        self,
        rows: _LedgerRows,
        binding: _EvidenceBoundClaimBinding,
        *,
        run_state: str,
    ) -> object | ResumeOwnedTask | ClaimHumanGate:
        if (
            not rows.attempts
            and not rows.authorizations
            and not rows.claim_events
            and not rows.acceptance_events
            and not rows.unexpected_events
        ):
            return _NO_EXISTING
        if rows.unexpected_events:
            return _human_gate(
                ClaimFailure.CORRUPTION,
                "a deterministic Canary event ID has an unexpected event type",
            )
        if (
            len(rows.attempts) != 1
            or len(rows.authorizations) != 1
            or len(rows.claim_events) != 1
            or len(rows.acceptance_events) > 1
        ):
            return _human_gate(
                ClaimFailure.CORRUPTION,
                "durable Canary claim is partial or has conflicting rows",
            )

        attempt = rows.attempts[0]
        authorization = rows.authorizations[0]
        claim_event = rows.claim_events[0]
        acceptance_event = rows.acceptance_events[0] if rows.acceptance_events else None
        if not self._attempt_matches(attempt, binding) or not self._authorization_matches(
            authorization,
            binding,
        ):
            return _human_gate(
                ClaimFailure.CONFLICT,
                "durable Canary claim identity drifted",
            )
        if not self._claim_event_matches(claim_event, authorization, attempt, binding):
            return _human_gate(
                ClaimFailure.CORRUPTION,
                "durable Canary claim event is incomplete or inconsistent",
            )

        if attempt.provider_task_id is None:
            if (
                acceptance_event is not None
                or attempt.submitted_at is not None
                or attempt.provider_state is not None
                or attempt.evidence_acceptance_event_id is not None
            ):
                return _human_gate(
                    ClaimFailure.CORRUPTION,
                    "submission ownership is partial",
                )
            if attempt.attempt_state not in {
                POST_IN_FLIGHT,
                "SUBMISSION_UNKNOWN",
                "HUMAN_GATE",
            } or attempt.state not in {
                RunState.RUNNING.value,
                RunState.HUMAN_GATE.value,
            }:
                return _human_gate(
                    ClaimFailure.CORRUPTION,
                    "claim without ownership has an invalid durable state",
                )
            if run_state not in {RunState.RUNNING.value, RunState.HUMAN_GATE.value}:
                return _human_gate(
                    ClaimFailure.CONFLICT,
                    "Run state conflicts with an unowned Canary claim",
                )
            return _human_gate(
                ClaimFailure.SUBMISSION_UNKNOWN,
                "authorization was consumed without a durably owned task",
            )

        if _TASK_ID.fullmatch(attempt.provider_task_id) is None:
            return _human_gate(
                ClaimFailure.CORRUPTION,
                "owned Provider task ID is malformed",
            )
        if attempt.submitted_at is None or acceptance_event is None:
            return _human_gate(
                ClaimFailure.CORRUPTION,
                "owned Provider task is missing durable acceptance state",
            )
        if attempt.evidence_acceptance_event_id != _acceptance_event_id(binding):
            return _human_gate(
                ClaimFailure.CORRUPTION,
                "owned Provider task is not bound to its acceptance event",
            )
        if not self._acceptance_event_matches(acceptance_event, attempt, binding):
            return _human_gate(
                ClaimFailure.CORRUPTION,
                "owned Provider task acceptance event drifted",
            )
        if attempt.attempt_state not in _RESUMABLE_ATTEMPT_STATES:
            return _human_gate(
                ClaimFailure.NOT_ELIGIBLE,
                "owned Provider task is not in a read-only recoverable state",
            )
        if attempt.provider_state in {"failed", "cancelled", "expired"}:
            return _human_gate(
                ClaimFailure.NOT_ELIGIBLE,
                "owned Provider task is in a terminal failure state",
            )
        if not self._owned_state_pair_is_valid(attempt, run_state=run_state):
            return _human_gate(
                ClaimFailure.CORRUPTION,
                "owned Provider task state pairing is invalid",
            )
        return ResumeOwnedTask(
            disposition="RESUME_OWNED_TASK",
            run_id=binding.run_id,
            job_id=binding.job_id,
            attempt=CANARY_ATTEMPT,
            provider_task_id=attempt.provider_task_id,
            authorization_sha256=binding.authorization_sha256,
            request_fingerprint=binding.request_fingerprint,
            submitted_at=attempt.submitted_at.astimezone(UTC),
        )

    @staticmethod
    def _attempt_matches(
        attempt: AttemptRecord,
        binding: _EvidenceBoundClaimBinding,
    ) -> bool:
        return (
            attempt.id == _attempt_id(binding)
            and attempt.run_id == binding.run_id
            and attempt.job_id == binding.job_id
            and attempt.attempt == CANARY_ATTEMPT
            and attempt.provider == CANARY_PROVIDER
            and attempt.model == CANARY_MODEL
            and attempt.request_fingerprint == binding.request_fingerprint
            and attempt.evidence_authorization_id == binding.authorization_id
            and attempt.evidence_authorization_sha256 == binding.authorization_sha256
            and attempt.evidence_runtime_release_sha256 == binding.runtime_release_sha256
            and attempt.evidence_runtime_policy_sha256 == binding.runtime_policy_sha256
            and attempt.evidence_task_queue == binding.task_queue
            and attempt.evidence_ledger_id == binding.ledger_id
            and attempt.evidence_deployment_id == binding.deployment_id
            and attempt.evidence_claim_event_id == _claim_event_id(binding)
            and attempt.evidence_claim_state == POST_IN_FLIGHT
        )

    @staticmethod
    def _authorization_matches(
        authorization: LiveAuthorizationUseRecord,
        binding: _EvidenceBoundClaimBinding,
    ) -> bool:
        return (
            authorization.authorization_id == binding.authorization_id
            and authorization.run_id == binding.run_id
            and authorization.job_id == binding.job_id
            and authorization.attempt == CANARY_ATTEMPT
            and authorization.request_fingerprint == binding.request_fingerprint
            and authorization.capability_snapshot_sha256 == binding.capability_snapshot_sha256
            and authorization.pricing_snapshot_sha256 == binding.pricing_snapshot_sha256
            and authorization.max_cost_cny == binding.max_cost_cny
            and authorization.authorization_document_type == "sdc.evidence-bound-live-authorization"
            and authorization.authorization_sha256 == binding.authorization_sha256
            and authorization.evidence_bound_plan_sha256 == binding.plan_sha256
            and authorization.execution_sha256 == binding.execution_sha256
            and authorization.submission_policy_sha256 == binding.submission_policy_sha256
            and authorization.runtime_policy_sha256 == binding.runtime_policy_sha256
            and authorization.runtime_release_sha256 == binding.runtime_release_sha256
            and authorization.evidence_bundle_id == binding.evidence_bundle_id
            and authorization.evidence_logical_tree_sha256 == binding.evidence_logical_tree_sha256
            and _utc_equal(authorization.evidence_valid_until, binding.evidence_valid_until)
            and authorization.entitlement_anchor_sha256 == binding.entitlement_anchor_sha256
            and _utc_equal(
                authorization.entitlement_valid_until,
                binding.entitlement_valid_until,
            )
            and authorization.provider_region == CANARY_REGION
            and authorization.task_queue == binding.task_queue
            and authorization.ledger_id == binding.ledger_id
            and _utc_equal(authorization.authorized_at, binding.authorized_at)
            and _utc_equal(authorization.expires_at, binding.expires_at)
            and authorization.nonce_sha256 == binding.nonce_sha256
            and authorization.claim_state == POST_IN_FLIGHT
        )

    @staticmethod
    def _claim_event_matches(
        event: EventRecord,
        authorization: LiveAuthorizationUseRecord,
        attempt: AttemptRecord,
        binding: _EvidenceBoundClaimBinding,
    ) -> bool:
        expected_payload = PostgresCanaryLedgerStore._claim_event_payload(binding)
        return (
            event.id == _claim_event_id(binding)
            and event.run_id == binding.run_id
            and event.event_type == CLAIM_EVENT_TYPE
            and event.state == RunState.RUNNING.value
            and event.idempotency_key == _claim_event_key(binding)
            and event.payload == expected_payload
            and _utc_equal(event.occurred_at, authorization.consumed_at)
            and _utc_equal(event.occurred_at, attempt.evidence_claimed_at)
        )

    @staticmethod
    def _acceptance_event_matches(
        event: EventRecord,
        attempt: AttemptRecord,
        binding: _EvidenceBoundClaimBinding,
    ) -> bool:
        provider_state = event.payload.get("provider_state")
        if not isinstance(provider_state, str) or provider_state not in _KNOWN_PROVIDER_STATES:
            return False
        if attempt.provider_task_id is None:
            return False
        if attempt.attempt_state == "SUBMITTED" and provider_state != attempt.provider_state:
            return False
        expected_payload = PostgresCanaryLedgerStore._acceptance_event_payload(
            binding,
            provider_task_id=attempt.provider_task_id,
            provider_state=provider_state,
        )
        return (
            event.id == _acceptance_event_id(binding)
            and event.run_id == binding.run_id
            and event.event_type == ACCEPTANCE_EVENT_TYPE
            and event.state == RunState.RUNNING.value
            and event.idempotency_key == _acceptance_event_key(binding)
            and event.payload == expected_payload
            and _utc_equal(event.occurred_at, attempt.submitted_at)
        )

    @staticmethod
    def _owned_state_pair_is_valid(attempt: AttemptRecord, *, run_state: str) -> bool:
        if attempt.provider_state not in _KNOWN_PROVIDER_STATES:
            return False
        if attempt.attempt_state == "SUBMITTED":
            return (
                attempt.state == RunState.RUNNING.value
                and run_state == RunState.RUNNING.value
                and attempt.provider_state in {"queued", "running", "succeeded"}
            )
        if attempt.attempt_state == "WATCHING":
            return (
                attempt.state == RunState.RUNNING.value
                and run_state == RunState.RUNNING.value
                and attempt.provider_state in {"queued", "running"}
            )
        if attempt.attempt_state == "DOWNLOADING":
            return (
                attempt.state == RunState.RUNNING.value
                and run_state == RunState.RUNNING.value
                and attempt.provider_state == "succeeded"
            )
        if attempt.attempt_state == "VERIFIED":
            return (
                attempt.state == RunState.SUCCEEDED.value
                and run_state == RunState.SUCCEEDED.value
                and attempt.provider_state == "succeeded"
            )
        return False


__all__ = [
    "CANARY_ATTEMPT",
    "CANARY_LEDGER_SINGLETON_ID",
    "CANARY_MODEL",
    "CANARY_OPERATION",
    "CANARY_PROVIDER",
    "CANARY_REGION",
    "CLAIM_TO_SOCKET_MAX_MS",
    "EXPIRY_GUARD_BAND_MS",
    "CanaryClaimResult",
    "ClaimFailure",
    "ClaimHumanGate",
    "NewPostPermit",
    "PostgresCanaryLedgerStore",
    "ResumeOwnedTask",
]
