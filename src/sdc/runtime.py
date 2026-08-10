"""Worker-side durable activity integration.

This module imports only the deterministic provider protocol. Network adapters are injected by the
worker entry point, keeping Temporal workflow sandbox imports free of HTTP libraries.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

from sdc.compiler import stable_id
from sdc.contracts import (
    DownloadedArtifact,
    GenerationJob,
    ProviderAttemptState,
    ProviderFailureClass,
    ProviderProfile,
    ProviderRequest,
    ProviderSubmission,
    ProviderTaskSnapshot,
    RunState,
)
from sdc.payloads import DurableResult, SubmitResult, WatchResult
from sdc.persistence import ArtifactRecord, AttemptRecord, EventRecord, RunRecord
from sdc.provider import (
    GenerationError,
    LegacyProvider,
    Provider,
    ProviderOperationError,
    SubmissionUnknown,
)


def _heartbeat(*details: object) -> None:
    """Heartbeat in a worker context while keeping direct adapter unit tests simple."""
    try:
        activity.heartbeat(*details)
    except RuntimeError:
        # Temporal raises outside an activity context; persistence remains the recovery source.
        pass


class RuntimeStore(Protocol):
    async def ensure_run(self, run_id: str) -> None: ...
    async def set_run_state(self, run_id: str, state: RunState) -> None: ...
    async def freeze_profile(self, run_id: str, profile: ProviderProfile) -> None: ...
    async def reserve_attempt(self, run_id: str, job_id: str, maximum: int = 2) -> int | None: ...
    async def finish_attempt(
        self, run_id: str, job: GenerationJob, attempt: int, state: RunState, path: Path | None
    ) -> None: ...
    async def reserve_provider_attempt(self, request: ProviderRequest) -> SubmitResult: ...
    async def record_submission(
        self, request: ProviderRequest, submission: ProviderSubmission
    ) -> None: ...
    async def record_submission_failure(
        self, request: ProviderRequest, failure_class: ProviderFailureClass
    ) -> None: ...
    async def record_observation(
        self, run_id: str, job_id: str, attempt: int, snapshot: ProviderTaskSnapshot
    ) -> None: ...
    async def record_download(
        self, run_id: str, job: GenerationJob, attempt: int, artifact: DownloadedArtifact
    ) -> None: ...


class PostgresRuntimeStore:
    """Idempotent persistence.

    Reservations prevent activity redelivery from issuing another POST.
    """

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def ensure_run(self, run_id: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                insert(RunRecord)
                .values(id=run_id, state=RunState.RUNNING.value)
                .on_conflict_do_nothing(index_elements=[RunRecord.id])
            )

    async def set_run_state(self, run_id: str, state: RunState) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(RunRecord).where(RunRecord.id == run_id).values(state=state.value)
            )

    async def freeze_profile(self, run_id: str, profile: ProviderProfile) -> None:
        serialized = profile.model_dump(mode="json")
        async with self._sessions.begin() as session:
            current = await session.scalar(
                select(RunRecord.provider_profile).where(RunRecord.id == run_id).with_for_update()
            )
            if current is not None and current != serialized:
                raise ValueError("provider profile is already frozen for this run")
            await session.execute(
                update(RunRecord).where(RunRecord.id == run_id).values(provider_profile=serialized)
            )

    async def _event(
        self,
        session: AsyncSession,
        run_id: str,
        event_type: str,
        state: RunState,
        key: str,
        payload: dict[str, object],
    ) -> None:
        # Payloads are deliberately composed from identifiers/state/evidence only. Prompts and
        # signed input/result URLs are never accepted by this boundary.
        await session.execute(
            insert(EventRecord)
            .values(
                id=stable_id("event", [run_id, key]),
                run_id=run_id,
                event_type=event_type,
                state=state.value,
                occurred_at=datetime.now(UTC),
                idempotency_key=key,
                payload=payload,
            )
            .on_conflict_do_nothing(
                index_elements=[EventRecord.run_id, EventRecord.idempotency_key]
            )
        )

    async def reserve_attempt(self, run_id: str, job_id: str, maximum: int = 2) -> int | None:
        async with self._sessions.begin() as session:
            await session.execute(
                select(RunRecord.id).where(RunRecord.id == run_id).with_for_update()
            )
            used = await session.scalar(
                select(func.count())
                .select_from(AttemptRecord)
                .where(AttemptRecord.run_id == run_id, AttemptRecord.job_id == job_id)
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

    async def reserve_provider_attempt(self, request: ProviderRequest) -> SubmitResult:
        async with self._sessions.begin() as session:
            await session.execute(
                select(RunRecord.id).where(RunRecord.id == request.run_id).with_for_update()
            )
            existing = await session.scalar(
                select(AttemptRecord).where(
                    AttemptRecord.run_id == request.run_id,
                    AttemptRecord.job_id == request.job_id,
                    AttemptRecord.attempt == request.attempt,
                )
            )
            if existing is not None:
                state = (
                    RunState.HUMAN_GATE
                    if existing.attempt_state
                    in {
                        ProviderAttemptState.HUMAN_GATE.value,
                        ProviderAttemptState.SUBMISSION_UNKNOWN.value,
                    }
                    else RunState.RUNNING
                )
                return SubmitResult(
                    state=state, attempt=request.attempt, provider_task_id=existing.provider_task_id
                )
            await session.execute(
                insert(AttemptRecord).values(
                    id=stable_id("attempt", [request.run_id, request.job_id, request.attempt]),
                    run_id=request.run_id,
                    job_id=request.job_id,
                    attempt=request.attempt,
                    state=RunState.RUNNING.value,
                    provider=request.provider,
                    model=request.model,
                    request_fingerprint=request.request_fingerprint,
                    attempt_state=ProviderAttemptState.RESERVED.value,
                )
            )
            await self._event(
                session,
                request.run_id,
                "provider.attempt_reserved",
                RunState.RUNNING,
                f"{request.job_id}:{request.attempt}:reserved",
                {
                    "job_id": request.job_id,
                    "attempt": request.attempt,
                    "provider": request.provider,
                    "model": request.model,
                    "request_fingerprint": request.request_fingerprint,
                    "input_sha256": ",".join(m.sha256 for m in request.input_materials),
                },
            )
            return SubmitResult(state=RunState.RUNNING, attempt=request.attempt)

    async def record_submission(
        self, request: ProviderRequest, submission: ProviderSubmission
    ) -> None:
        now = datetime.now(UTC)
        async with self._sessions.begin() as session:
            await session.execute(
                update(AttemptRecord)
                .where(
                    AttemptRecord.run_id == request.run_id,
                    AttemptRecord.job_id == request.job_id,
                    AttemptRecord.attempt == request.attempt,
                )
                .values(
                    provider_task_id=submission.provider_task_id,
                    provider_state=submission.state.value,
                    attempt_state=ProviderAttemptState.SUBMITTED.value,
                    submitted_at=now,
                    last_observed_at=now,
                )
            )
            await self._event(
                session,
                request.run_id,
                "provider.submission_accepted",
                RunState.RUNNING,
                f"{request.job_id}:{request.attempt}:submitted",
                {
                    "job_id": request.job_id,
                    "attempt": request.attempt,
                    "provider_task_id": submission.provider_task_id,
                },
            )

    async def record_submission_failure(
        self, request: ProviderRequest, failure_class: ProviderFailureClass
    ) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(AttemptRecord)
                .where(
                    AttemptRecord.run_id == request.run_id,
                    AttemptRecord.job_id == request.job_id,
                    AttemptRecord.attempt == request.attempt,
                )
                .values(
                    state=RunState.HUMAN_GATE.value,
                    failure_class=failure_class.value,
                    attempt_state=(
                        ProviderAttemptState.SUBMISSION_UNKNOWN.value
                        if failure_class is ProviderFailureClass.SUBMISSION_UNKNOWN
                        else ProviderAttemptState.HUMAN_GATE.value
                    ),
                )
            )
            await session.execute(
                update(RunRecord)
                .where(RunRecord.id == request.run_id)
                .values(state=RunState.HUMAN_GATE.value)
            )
            event_type = (
                "provider.submission_unknown"
                if failure_class is ProviderFailureClass.SUBMISSION_UNKNOWN
                else "provider.attempt_failed"
            )
            await self._event(
                session,
                request.run_id,
                event_type,
                RunState.HUMAN_GATE,
                f"{request.job_id}:{request.attempt}:{failure_class.value}",
                {
                    "job_id": request.job_id,
                    "attempt": request.attempt,
                    "failure_class": failure_class.value,
                },
            )

    async def record_observation(
        self, run_id: str, job_id: str, attempt: int, snapshot: ProviderTaskSnapshot
    ) -> None:
        now = datetime.now(UTC)
        values: dict[str, object] = {
            "provider_state": snapshot.state.value,
            "attempt_state": ProviderAttemptState.WATCHING.value,
            "last_observed_at": now,
            "usage_tokens": snapshot.usage_tokens,
        }
        if snapshot.failure:
            values["failure_class"] = snapshot.failure.failure_class.value
            values["attempt_state"] = ProviderAttemptState.FAILED.value
            values["state"] = RunState.STOP_2.value if attempt == 2 else RunState.RETRYING.value
        async with self._sessions.begin() as session:
            await session.execute(
                update(AttemptRecord)
                .where(
                    AttemptRecord.run_id == run_id,
                    AttemptRecord.job_id == job_id,
                    AttemptRecord.attempt == attempt,
                )
                .values(**values)
            )
            await self._event(
                session,
                run_id,
                "provider.status_observed",
                RunState.RUNNING,
                f"{job_id}:{attempt}:observed:{snapshot.state.value}",
                {
                    "job_id": job_id,
                    "attempt": attempt,
                    "provider_task_id": snapshot.provider_task_id,
                    "provider_state": snapshot.state.value,
                },
            )
            if snapshot.failure:
                failure_state = RunState.STOP_2 if attempt == 2 else RunState.RETRYING
                await self._event(
                    session,
                    run_id,
                    "provider.attempt_failed",
                    failure_state,
                    f"{job_id}:{attempt}:failed:{snapshot.failure.failure_class.value}",
                    {
                        "job_id": job_id,
                        "attempt": attempt,
                        "provider_task_id": snapshot.provider_task_id,
                        "failure_class": snapshot.failure.failure_class.value,
                    },
                )

    async def record_download(
        self, run_id: str, job: GenerationJob, attempt: int, artifact: DownloadedArtifact
    ) -> None:
        now = datetime.now(UTC)
        async with self._sessions.begin() as session:
            await session.execute(
                update(AttemptRecord)
                .where(
                    AttemptRecord.run_id == run_id,
                    AttemptRecord.job_id == job.id,
                    AttemptRecord.attempt == attempt,
                )
                .values(
                    state=RunState.SUCCEEDED.value,
                    attempt_state=ProviderAttemptState.VERIFIED.value,
                    downloaded_at=now,
                    artifact_sha256=artifact.sha256,
                )
            )
            await session.execute(
                update(ArtifactRecord)
                .where(
                    ArtifactRecord.run_id == run_id,
                    ArtifactRecord.job_id == job.id,
                    ArtifactRecord.is_current.is_(True),
                )
                .values(is_current=False)
            )
            await session.execute(
                insert(ArtifactRecord)
                .values(
                    id=stable_id("artifact", [run_id, job.id, attempt]),
                    run_id=run_id,
                    job_id=job.id,
                    attempt=attempt,
                    idempotency_key=f"{job.idempotency_key}:candidate:{attempt}",
                    path=artifact.path,
                    is_current=True,
                    sha256=artifact.sha256,
                    size_bytes=artifact.size_bytes,
                    ffprobe=artifact.ffprobe,
                )
                .on_conflict_do_update(
                    index_elements=[ArtifactRecord.run_id, ArtifactRecord.idempotency_key],
                    set_={
                        "path": artifact.path,
                        "is_current": True,
                        "sha256": artifact.sha256,
                        "size_bytes": artifact.size_bytes,
                        "ffprobe": artifact.ffprobe,
                    },
                )
            )
            common = {
                "job_id": job.id,
                "attempt": attempt,
                "provider_task_id": artifact.provider_task_id,
                "sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes,
            }
            await self._event(
                session,
                run_id,
                "provider.artifact_downloaded",
                RunState.RUNNING,
                f"{job.id}:{attempt}:downloaded",
                common,
            )
            await self._event(
                session,
                run_id,
                "provider.artifact_verified",
                RunState.SUCCEEDED,
                f"{job.id}:{attempt}:verified",
                common,
            )

    async def finish_attempt(
        self, run_id: str, job: GenerationJob, attempt: int, state: RunState, path: Path | None
    ) -> None:
        # BUILD-002 compatibility path used only by injected LegacyProvider tests/demo.
        event_key = f"{job.idempotency_key}:attempt:{attempt}:{state.value}"
        async with self._sessions.begin() as session:
            await session.execute(
                update(AttemptRecord)
                .where(
                    AttemptRecord.run_id == run_id,
                    AttemptRecord.job_id == job.id,
                    AttemptRecord.attempt == attempt,
                )
                .values(state=state.value)
            )
            if path is not None:
                await session.execute(
                    update(ArtifactRecord)
                    .where(
                        ArtifactRecord.run_id == run_id,
                        ArtifactRecord.job_id == job.id,
                        ArtifactRecord.is_current.is_(True),
                    )
                    .values(is_current=False)
                )
                await session.execute(
                    insert(ArtifactRecord)
                    .values(
                        id=stable_id("artifact", [run_id, job.id, attempt]),
                        run_id=run_id,
                        job_id=job.id,
                        attempt=attempt,
                        idempotency_key=f"{job.idempotency_key}:candidate:{attempt}",
                        path=str(path),
                        is_current=True,
                    )
                    .on_conflict_do_update(
                        index_elements=[ArtifactRecord.run_id, ArtifactRecord.idempotency_key],
                        set_={"path": str(path), "is_current": True},
                    )
                )
            await self._event(
                session,
                run_id,
                "candidate.generated" if path else "candidate.failed",
                state,
                event_key,
                {"job_id": job.id, "attempt": attempt},
            )


class RuntimeActivities:
    def __init__(
        self,
        store: RuntimeStore,
        provider: Provider | LegacyProvider,
        output_root: Path,
        profile: ProviderProfile | None = None,
    ) -> None:
        self.store, self.provider, self.output_root = store, provider, output_root
        self.profile = profile or ProviderProfile(
            provider="fake", model="fake-v1", min_duration_ms=1, max_duration_ms=60_000
        )

    def _request(self, run_id: str, job: GenerationJob, attempt: int) -> ProviderRequest:
        fingerprint_inputs = {
            "run_id": run_id,
            "job_id": job.id,
            "attempt": attempt,
            "provider": self.profile.provider,
            "model": self.profile.model,
            "prompt": job.prompt,
            "duration_ms": job.duration_ms,
            "aspect_ratio": self.profile.aspect_ratio,
            "resolution": self.profile.resolution,
            "input_materials": (),
        }
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_inputs, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ProviderRequest(
            run_id=run_id,
            job_id=job.id,
            attempt=attempt,
            provider=self.profile.provider,
            model=self.profile.model,
            prompt=job.prompt,
            duration_ms=job.duration_ms,
            aspect_ratio=self.profile.aspect_ratio,
            resolution=self.profile.resolution,
            input_materials=(),
            request_fingerprint=fingerprint,
        )

    @activity.defn(name="set_run_state")
    async def set_run_state(self, run_id: str, state: RunState) -> None:
        await self.store.ensure_run(run_id)
        await self.store.set_run_state(run_id, state)

    @activity.defn(name="submit_generation")
    async def submit_generation(
        self, run_id: str, job: GenerationJob, attempt: int
    ) -> SubmitResult:
        await self.store.ensure_run(run_id)
        await self.store.freeze_profile(run_id, self.profile)
        request = self._request(run_id, job, attempt)
        reserved = await self.store.reserve_provider_attempt(request)
        if reserved.provider_task_id or reserved.state is RunState.HUMAN_GATE:
            return reserved
        for explicit_rejection in range(3):
            try:
                submission = await self.provider.submit(request)  # type: ignore[union-attr]
                break
            except SubmissionUnknown:
                await self.store.record_submission_failure(
                    request, ProviderFailureClass.SUBMISSION_UNKNOWN
                )
                return SubmitResult(state=RunState.HUMAN_GATE, attempt=attempt)
            except ProviderOperationError as exc:
                # Only an explicit response proving no task was accepted may retry this POST.
                # Transport ambiguity is SubmissionUnknown and can never enter this branch.
                if exc.retryable and explicit_rejection < 2:
                    await asyncio.sleep(2**explicit_rejection)
                    continue
                await self.store.record_submission_failure(request, exc.failure_class)
                return SubmitResult(state=RunState.HUMAN_GATE, attempt=attempt)
        await self.store.record_submission(request, submission)
        return SubmitResult(
            state=RunState.RUNNING, attempt=attempt, provider_task_id=submission.provider_task_id
        )

    @activity.defn(name="watch_generation")
    async def watch_generation(
        self, run_id: str, job: GenerationJob, attempt: int, provider_task_id: str
    ) -> WatchResult:
        _heartbeat(provider_task_id)
        snapshot = await self.provider.inspect(provider_task_id)  # type: ignore[union-attr]
        await self.store.record_observation(run_id, job.id, attempt, snapshot)
        _heartbeat(provider_task_id, snapshot.state.value)
        return WatchResult(
            attempt=attempt,
            provider_task_id=provider_task_id,
            task_state=snapshot.state,
            failure_class=snapshot.failure.failure_class if snapshot.failure else None,
        )

    @activity.defn(name="download_generation")
    async def download_generation(
        self, run_id: str, job: GenerationJob, attempt: int, provider_task_id: str
    ) -> DurableResult:
        destination = self.output_root / run_id / f"{job.id}-{attempt}.mp4"
        _heartbeat(provider_task_id, "downloading")
        artifact = await self.provider.download(provider_task_id, destination)  # type: ignore[union-attr]
        await self.store.record_download(run_id, job, attempt, artifact)
        _heartbeat(provider_task_id, "verified")
        return DurableResult(state=RunState.SUCCEEDED, path=artifact.path, attempts=attempt)

    @activity.defn(name="generate")
    async def generate(self, run_id: str, job: GenerationJob) -> DurableResult:
        """Legacy compatibility activity; production workflow uses the three safe boundaries."""
        await self.store.ensure_run(run_id)
        while (
            attempt := await self.store.reserve_attempt(run_id, job.id, job.max_attempts)
        ) is not None:
            output = self.output_root / run_id / f"{job.id}-{attempt}.mp4"
            try:
                path = await self.provider.generate(job, output, attempt)  # type: ignore[union-attr]
            except GenerationError:
                state = RunState.STOP_2 if attempt == job.max_attempts else RunState.RETRYING
                await self.store.finish_attempt(run_id, job, attempt, state, None)
                if state is RunState.STOP_2:
                    return DurableResult(state=state, path=None, attempts=attempt)
            else:
                await self.store.finish_attempt(run_id, job, attempt, RunState.SUCCEEDED, path)
                return DurableResult(state=RunState.SUCCEEDED, path=str(path), attempts=attempt)
        return DurableResult(state=RunState.STOP_2, path=None, attempts=job.max_attempts)
