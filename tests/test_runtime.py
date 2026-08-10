from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from sdc.canary import LiveSubmissionGuard, contract_sha256
from sdc.contracts import (
    GenerationJob,
    LiveAuthorization,
    PricingInputMode,
    ProviderCapabilitySnapshot,
    ProviderFailureClass,
    ProviderPricingSnapshot,
    ProviderProfile,
    ProviderRequest,
    ProviderSubmission,
    ProviderTaskState,
    RunState,
    SnapshotStatus,
)
from sdc.payloads import SubmitResult
from sdc.provider import (
    ARK_MODEL,
    FakeProvider,
    GenerationError,
    ProviderOperationError,
    SubmissionUnknown,
    request_fingerprint,
)
from sdc.runtime import RuntimeActivities


class MemoryStore:
    def __init__(self) -> None:
        self.attempts = 0
        self.finished: list[tuple[int, RunState, Path | None]] = []

    async def ensure_run(self, run_id: str) -> None:
        assert run_id

    async def reserve_attempt(self, run_id: str, job_id: str, maximum: int = 2) -> int | None:
        if self.attempts >= maximum:
            return None
        self.attempts += 1
        return self.attempts

    async def finish_attempt(
        self,
        run_id: str,
        job: GenerationJob,
        attempt: int,
        state: RunState,
        path: Path | None,
    ) -> None:
        self.finished.append((attempt, state, path))


class FailOnceProvider:
    async def generate(self, job: GenerationJob, output: Path, attempt: int) -> Path:
        if attempt == 1:
            raise GenerationError("planned")
        output.parent.mkdir(parents=True)
        output.write_bytes(b"candidate")
        return output


def job() -> GenerationJob:
    return GenerationJob(
        id="job_a",
        shot_id="shot_a",
        prompt="prompt",
        duration_ms=10,
        idempotency_key="generate_a",
    )


@pytest.mark.asyncio
async def test_activity_resumes_from_durable_attempt_count(tmp_path: Path) -> None:
    store = MemoryStore()
    activity = RuntimeActivities(store, FailOnceProvider(), tmp_path)
    result = await activity.generate("run_a", job())
    assert result.state is RunState.SUCCEEDED
    assert result.attempts == 2
    assert [item[:2] for item in store.finished] == [
        (1, RunState.RETRYING),
        (2, RunState.SUCCEEDED),
    ]


@pytest.mark.asyncio
async def test_activity_cannot_make_third_call_after_restart(tmp_path: Path) -> None:
    store = MemoryStore()
    store.attempts = 2
    provider = FakeProvider()
    activity = RuntimeActivities(store, provider, tmp_path)
    result = await activity.generate("run_a", job())
    assert result == result.__class__(state=RunState.STOP_2, path=None, attempts=2)
    assert store.finished == []


class AsyncMemoryStore:
    def __init__(self) -> None:
        self.reservation: SubmitResult | None = None
        self.failure: ProviderFailureClass | None = None
        self.profile: ProviderProfile | None = None
        self.authorization_consumed = False

    async def ensure_run(self, run_id: str) -> None:
        pass

    async def freeze_profile(self, run_id: str, profile: ProviderProfile) -> None:
        self.profile = profile

    async def reserve_provider_attempt(self, request: ProviderRequest) -> SubmitResult:
        if self.failure is not None:
            return SubmitResult(state=RunState.HUMAN_GATE, attempt=request.attempt)
        if self.reservation is None:
            self.reservation = SubmitResult(state=RunState.RUNNING, attempt=request.attempt)
        return self.reservation

    async def record_submission_failure(
        self, request: ProviderRequest, failure_class: ProviderFailureClass
    ) -> None:
        self.failure = failure_class

    async def record_submission(
        self, request: ProviderRequest, submission: ProviderSubmission
    ) -> None:
        self.reservation = SubmitResult(
            state=RunState.RUNNING,
            attempt=request.attempt,
            provider_task_id=submission.provider_task_id,
        )

    async def consume_live_authorization(self, *_: object) -> bool:
        if self.authorization_consumed:
            return False
        self.authorization_consumed = True
        return True

    async def record_live_gate_failure(
        self, request: ProviderRequest, failure_class: ProviderFailureClass
    ) -> None:
        self.failure = failure_class


class UnknownProvider:
    def __init__(self) -> None:
        self.posts = 0

    async def submit(self, request: ProviderRequest) -> ProviderSubmission:
        self.posts += 1
        raise SubmissionUnknown("unknown")


@pytest.mark.asyncio
async def test_submission_unknown_is_persisted_and_never_posted_again(tmp_path: Path) -> None:
    store = AsyncMemoryStore()
    provider = UnknownProvider()
    activities = RuntimeActivities(store, provider, tmp_path)  # type: ignore[arg-type]
    first = await activities.submit_generation("run", job(), 1)
    second = await activities.submit_generation("run", job(), 1)
    assert first.state is RunState.HUMAN_GATE and second.state is RunState.HUMAN_GATE
    assert store.failure is ProviderFailureClass.SUBMISSION_UNKNOWN
    assert provider.posts == 1


class AcceptedProvider:
    def __init__(self) -> None:
        self.posts = 0

    async def submit(self, request: ProviderRequest) -> ProviderSubmission:
        self.posts += 1
        return ProviderSubmission(provider_task_id="task-stable", state=ProviderTaskState.QUEUED)


@pytest.mark.asyncio
async def test_restart_reuses_persisted_task_id_without_second_post(tmp_path: Path) -> None:
    store = AsyncMemoryStore()
    provider = AcceptedProvider()
    first_worker = RuntimeActivities(store, provider, tmp_path)  # type: ignore[arg-type]
    first = await first_worker.submit_generation("run", job(), 1)
    second_worker = RuntimeActivities(store, provider, tmp_path)  # type: ignore[arg-type]
    resumed = await second_worker.submit_generation("run", job(), 1)
    assert first.provider_task_id == resumed.provider_task_id == "task-stable"
    assert provider.posts == 1


def live_guard(run_id: str, item: GenerationJob) -> LiveSubmissionGuard:
    now = datetime(2026, 8, 10, tzinfo=UTC)
    request = ProviderRequest(
        run_id=run_id,
        job_id=item.id,
        attempt=1,
        provider="volcengine_ark",
        model=ARK_MODEL,
        prompt=item.prompt,
        duration_ms=item.duration_ms,
        aspect_ratio="9:16",
        resolution="1080p",
        request_fingerprint="0" * 64,
    )
    request = request.model_copy(update={"request_fingerprint": request_fingerprint(request)})
    capability = ProviderCapabilitySnapshot(
        snapshot_revision="test",
        status=SnapshotStatus.CURRENT,
        provider="volcengine_ark",
        model=ARK_MODEL,
        aspect_ratios=("9:16",),
        resolutions=("1080p",),
        fps=24,
        min_duration_ms=4000,
        max_duration_ms=15000,
        source_url="https://www.volcengine.com/docs/82379/1330310",
        source_updated_at=now,
        captured_at=now,
        valid_until=datetime(2030, 1, 1, tzinfo=UTC),
        evidence_sha256="a" * 64,
    )
    pricing = ProviderPricingSnapshot(
        snapshot_revision="test",
        status=SnapshotStatus.CURRENT,
        provider="volcengine_ark",
        model=ARK_MODEL,
        resolution="1080p",
        input_mode=PricingInputMode.WITHOUT_VIDEO,
        billing_unit="token",
        unit_price_cny=Decimal("0.000001"),
        worst_case_units=Decimal("100000"),
        worst_case_cost_cny=Decimal("0.10"),
        source_url="https://docs.volcengine.com/docs/82379/1544106",
        source_updated_at=now,
        captured_at=now,
        valid_until=datetime(2030, 1, 1, tzinfo=UTC),
        evidence_sha256="b" * 64,
    )
    authorization = LiveAuthorization(
        authorization_id="SDC-CANARY-001",
        request_fingerprint=request.request_fingerprint,
        capability_snapshot_sha256=contract_sha256(capability),
        pricing_snapshot_sha256=contract_sha256(pricing),
        max_cost_cny=Decimal("0.20"),
        expires_at=datetime(2030, 1, 1, tzinfo=UTC),
        nonce="c" * 64,
    )
    return LiveSubmissionGuard(capability, pricing, authorization)


@pytest.mark.asyncio
async def test_live_authorization_is_consumed_before_only_post(tmp_path: Path) -> None:
    store = AsyncMemoryStore()
    provider = AcceptedProvider()
    item = job().model_copy(update={"duration_ms": 4000})
    profile = ProviderProfile(provider="volcengine_ark", model=ARK_MODEL)
    activities = RuntimeActivities(
        store, provider, tmp_path, profile, live_guard("run", item)
    )  # type: ignore[arg-type]
    first = await activities.submit_generation("run", item, 1)
    assert first.provider_task_id == "task-stable"
    assert store.authorization_consumed and provider.posts == 1

    # Simulate restart after authorization consumption but before a task ID was durably visible.
    store.reservation = SubmitResult(state=RunState.RUNNING, attempt=1)
    second = await activities.submit_generation("run", item, 1)
    assert second.state is RunState.HUMAN_GATE
    assert store.failure is ProviderFailureClass.LIVE_NOT_AUTHORIZED
    assert provider.posts == 1


@pytest.mark.asyncio
async def test_live_profile_without_authorization_makes_zero_posts(tmp_path: Path) -> None:
    store = AsyncMemoryStore()
    provider = AcceptedProvider()
    item = job().model_copy(update={"duration_ms": 4000})
    activities = RuntimeActivities(
        store,
        provider,
        tmp_path,
        ProviderProfile(provider="volcengine_ark", model=ARK_MODEL),
    )  # type: ignore[arg-type]
    result = await activities.submit_generation("run", item, 1)
    assert result.state is RunState.HUMAN_GATE
    assert store.failure is ProviderFailureClass.LIVE_NOT_AUTHORIZED
    assert provider.posts == 0


class ExplicitRejectProvider:
    def __init__(self) -> None:
        self.posts = 0

    async def submit(self, request: ProviderRequest) -> ProviderSubmission:
        self.posts += 1
        raise ProviderOperationError(
            ProviderFailureClass.TRANSIENT, "explicit rejection", retryable=True
        )


@pytest.mark.asyncio
async def test_live_canary_explicit_rejection_is_not_posted_twice(tmp_path: Path) -> None:
    store = AsyncMemoryStore()
    provider = ExplicitRejectProvider()
    item = job().model_copy(update={"duration_ms": 4000})
    activities = RuntimeActivities(
        store,
        provider,
        tmp_path,
        ProviderProfile(provider="volcengine_ark", model=ARK_MODEL),
        live_guard("run", item),
    )  # type: ignore[arg-type]
    result = await activities.submit_generation("run", item, 1)
    assert result.state is RunState.HUMAN_GATE
    assert store.failure is ProviderFailureClass.TRANSIENT
    assert provider.posts == 1
