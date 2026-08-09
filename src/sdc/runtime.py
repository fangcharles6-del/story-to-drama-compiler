"""Durable activity integration for Temporal, PostgreSQL, and provider adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

from sdc.compiler import stable_id
from sdc.contracts import GenerationJob, RunState
from sdc.persistence import ArtifactRecord, AttemptRecord, EventRecord, RunRecord
from sdc.provider import GenerationError, Provider


@dataclass(frozen=True)
class DurableResult:
    state: RunState
    path: str | None
    attempts: int


class RuntimeStore(Protocol):
    async def ensure_run(self, run_id: str) -> None: ...

    async def reserve_attempt(
        self, run_id: str, job_id: str, maximum: int = 2
    ) -> int | None: ...

    async def finish_attempt(
        self, run_id: str, job: GenerationJob, attempt: int, state: RunState, path: Path | None
    ) -> None: ...


class PostgresRuntimeStore:
    """Small transaction boundary used by activities; every write is idempotent."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def ensure_run(self, run_id: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                insert(RunRecord)
                .values(id=run_id, state=RunState.RUNNING.value)
                .on_conflict_do_nothing(index_elements=[RunRecord.id])
            )

    async def reserve_attempt(self, run_id: str, job_id: str, maximum: int = 2) -> int | None:
        """Atomically reserve the next attempt, returning ``None`` after exhaustion."""
        async with self._sessions.begin() as session:
            # Serialise reservations for all jobs in a run. This is deliberately simple and
            # makes concurrent Temporal activity deliveries safe without process-local locks.
            await session.execute(
                select(RunRecord.id).where(RunRecord.id == run_id).with_for_update()
            )
            used = await session.scalar(
                select(func.count())
                .select_from(AttemptRecord)
                .where(AttemptRecord.job_id == job_id)
            )
            attempt = int(used or 0) + 1
            if attempt > maximum:
                return None
            await session.execute(
                insert(AttemptRecord).values(
                    id=stable_id("attempt", [run_id, job_id, attempt]),
                    run_id=run_id,
                    job_id=job_id,
                    attempt=attempt,
                    state=RunState.RUNNING.value,
                )
            )
            return attempt

    async def finish_attempt(
        self, run_id: str, job: GenerationJob, attempt: int, state: RunState, path: Path | None
    ) -> None:
        event_key = f"{job.idempotency_key}:attempt:{attempt}:{state.value}"
        async with self._sessions.begin() as session:
            await session.execute(
                update(AttemptRecord)
                .where(AttemptRecord.job_id == job.id, AttemptRecord.attempt == attempt)
                .values(state=state.value)
            )
            if path is not None:
                await session.execute(
                    update(ArtifactRecord)
                    .where(ArtifactRecord.job_id == job.id, ArtifactRecord.is_current.is_(True))
                    .values(is_current=False)
                )
                await session.execute(
                    insert(ArtifactRecord)
                    .values(
                        id=stable_id("artifact", [job.id, attempt]),
                        job_id=job.id,
                        attempt=attempt,
                        idempotency_key=f"{job.idempotency_key}:candidate:{attempt}",
                        path=str(path),
                        is_current=True,
                    )
                    .on_conflict_do_update(
                        index_elements=[ArtifactRecord.idempotency_key],
                        set_={"path": str(path), "is_current": True},
                    )
                )
            await session.execute(
                insert(EventRecord)
                .values(
                    id=stable_id("event", event_key),
                    run_id=run_id,
                    event_type="candidate.generated" if path else "candidate.failed",
                    state=state.value,
                    occurred_at=datetime.now(UTC),
                    idempotency_key=event_key,
                    payload={"job_id": job.id, "attempt": attempt},
                )
                .on_conflict_do_nothing(index_elements=[EventRecord.idempotency_key])
            )


class RuntimeActivities:
    """Worker-owned dependency injection; no provider or database globals are required."""

    def __init__(self, store: RuntimeStore, provider: Provider, output_root: Path) -> None:
        self.store = store
        self.provider = provider
        self.output_root = output_root

    @activity.defn(name="generate")
    async def generate(self, run_id: str, job: GenerationJob) -> DurableResult:
        await self.store.ensure_run(run_id)
        while (
            attempt := await self.store.reserve_attempt(run_id, job.id, job.max_attempts)
        ) is not None:
            output = self.output_root / run_id / f"{job.id}-{attempt}.mp4"
            try:
                path = await self.provider.generate(job, output, attempt)
            except GenerationError:
                state = RunState.STOP_2 if attempt == job.max_attempts else RunState.RETRYING
                await self.store.finish_attempt(run_id, job, attempt, state, None)
                if state is RunState.STOP_2:
                    return DurableResult(state, None, attempt)
            else:
                await self.store.finish_attempt(run_id, job, attempt, RunState.SUCCEEDED, path)
                return DurableResult(RunState.SUCCEEDED, str(path), attempt)
        return DurableResult(RunState.STOP_2, None, job.max_attempts)
