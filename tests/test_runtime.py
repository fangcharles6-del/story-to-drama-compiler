from pathlib import Path

import pytest

from sdc.contracts import (
    GenerationJob,
    ProviderFailureClass,
    ProviderProfile,
    ProviderRequest,
    ProviderSubmission,
    ProviderTaskState,
    RunState,
)
from sdc.payloads import SubmitResult
from sdc.provider import (
    ARK_MODEL,
    FakeProvider,
    GenerationError,
    ProviderAttemptFailure,
    ProviderOperationError,
    SubmissionUnknown,
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
        self.failure: ProviderAttemptFailure | None = None
        self.profile: ProviderProfile | None = None
        self.authorization_consumed = False
        self.reservation_calls = 0
        self.authorization_consume_calls = 0

    async def ensure_run(self, run_id: str) -> None:
        pass

    async def freeze_profile(self, run_id: str, profile: ProviderProfile) -> None:
        self.profile = profile

    async def reserve_provider_attempt(self, request: ProviderRequest) -> SubmitResult:
        self.reservation_calls += 1
        if self.failure is not None:
            return SubmitResult(state=RunState.HUMAN_GATE, attempt=request.attempt)
        if self.reservation is None:
            self.reservation = SubmitResult(state=RunState.RUNNING, attempt=request.attempt)
        return self.reservation

    async def record_submission_failure(
        self, request: ProviderRequest, failure: ProviderAttemptFailure
    ) -> None:
        self.failure = failure

    async def record_submission(
        self, request: ProviderRequest, submission: ProviderSubmission
    ) -> None:
        self.reservation = SubmitResult(
            state=RunState.RUNNING,
            attempt=request.attempt,
            provider_task_id=submission.provider_task_id,
        )

    async def consume_live_authorization(self, *_: object) -> bool:
        self.authorization_consume_calls += 1
        if self.authorization_consumed:
            return False
        self.authorization_consumed = True
        return True

    async def record_live_gate_failure(
        self, request: ProviderRequest, failure_class: ProviderFailureClass
    ) -> None:
        self.failure = ProviderAttemptFailure(failure_class=failure_class)


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
    assert store.failure is not None
    assert store.failure.failure_class is ProviderFailureClass.SUBMISSION_UNKNOWN
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


@pytest.mark.asyncio
async def test_frozen_workflow_request_mismatch_fails_before_post(tmp_path: Path) -> None:
    store = AsyncMemoryStore()
    provider = AcceptedProvider()
    item = job().model_copy(update={"duration_ms": 4000})
    activities = RuntimeActivities(
        store,
        provider,  # type: ignore[arg-type]
        tmp_path,
        ProviderProfile(provider="volcengine_ark", model=ARK_MODEL),
    )
    frozen = activities._request("canary-run", item, 1).model_copy(
        update={"request_fingerprint": "f" * 64}
    )
    result = await activities.submit_canary_generation("canary-run", item, 1, frozen)
    assert result.state is RunState.HUMAN_GATE
    assert store.failure is not None
    assert store.failure.failure_class is ProviderFailureClass.LIVE_NOT_AUTHORIZED
    assert store.reservation is None and provider.posts == 0


@pytest.mark.parametrize(
    ("entrypoint", "attempt"),
    [
        pytest.param("generic", 1, id="generic-attempt-1"),
        pytest.param("generic", 2, id="generic-attempt-2"),
        pytest.param("canary", 1, id="canary-attempt-1"),
        pytest.param("canary", 2, id="canary-attempt-2"),
    ],
)
@pytest.mark.asyncio
async def test_ark_runtime_is_unconditionally_disabled_before_reserve_consume_or_post(
    tmp_path: Path,
    entrypoint: str,
    attempt: int,
) -> None:
    store = AsyncMemoryStore()
    provider = AcceptedProvider()
    item = job().model_copy(update={"duration_ms": 4000})
    activities = RuntimeActivities(
        store,
        provider,
        tmp_path,
        ProviderProfile(provider="volcengine_ark", model=ARK_MODEL),
        object(),
    )  # type: ignore[arg-type]
    if entrypoint == "generic":
        result = await activities.submit_generation("run", item, attempt)
    else:
        frozen = activities._request("run", item, attempt)
        result = await activities.submit_canary_generation("run", item, attempt, frozen)

    assert result.state is RunState.HUMAN_GATE
    assert store.failure is not None
    assert store.failure.failure_class is ProviderFailureClass.LIVE_NOT_AUTHORIZED
    assert store.reservation_calls == 0
    assert store.authorization_consume_calls == 0
    assert store.reservation is None
    assert store.authorization_consumed is False
    assert provider.posts == 0


class ArkDirectCallStore:
    def __init__(self) -> None:
        self.run_states: list[tuple[str, RunState]] = []
        self.legacy_reservation_calls = 0
        self.provider_reservation_calls = 0

    async def ensure_run(self, run_id: str) -> None:
        assert run_id == "run"

    async def set_run_state(self, run_id: str, state: RunState) -> None:
        self.run_states.append((run_id, state))

    async def reserve_attempt(
        self, run_id: str, job_id: str, maximum: int = 2
    ) -> int | None:
        self.legacy_reservation_calls += 1
        raise AssertionError("disabled Ark activity must not reserve a legacy attempt")

    async def reserve_provider_attempt(self, request: ProviderRequest) -> SubmitResult:
        self.provider_reservation_calls += 1
        raise AssertionError("disabled Ark activity must not reserve a provider attempt")


class ArkDirectCallProvider:
    def __init__(self) -> None:
        self.inspect_calls = 0
        self.download_calls = 0
        self.generate_calls = 0

    async def inspect(self, provider_task_id: str) -> None:
        self.inspect_calls += 1
        raise AssertionError("disabled Ark activity must not inspect a task")

    async def download(self, provider_task_id: str, destination: Path) -> None:
        self.download_calls += 1
        raise AssertionError("disabled Ark activity must not download an artifact")

    async def generate(self, item: GenerationJob, output: Path, attempt: int) -> None:
        self.generate_calls += 1
        raise AssertionError("disabled Ark activity must not call legacy generate")


@pytest.mark.parametrize("entrypoint", ["watch", "download", "generate"])
@pytest.mark.asyncio
async def test_ark_direct_runtime_entrypoints_fail_closed_without_provider_io_or_reservation(
    tmp_path: Path,
    entrypoint: str,
) -> None:
    store = ArkDirectCallStore()
    provider = ArkDirectCallProvider()
    item = job().model_copy(update={"duration_ms": 4000})
    activities = RuntimeActivities(
        store,
        provider,
        tmp_path,
        ProviderProfile(provider="volcengine_ark", model=ARK_MODEL),
    )  # type: ignore[arg-type]

    if entrypoint == "watch":
        watch = await activities.watch_generation("run", item, 1, "ark-task")
        assert watch.task_state is ProviderTaskState.FAILED
        assert watch.failure_class is ProviderFailureClass.LIVE_NOT_AUTHORIZED
    elif entrypoint == "download":
        download = await activities.download_generation("run", item, 1, "ark-task")
        assert download.state is RunState.HUMAN_GATE
        assert download.path is None
        assert download.attempts == 1
    else:
        generated = await activities.generate("run", item)
        assert generated.state is RunState.HUMAN_GATE
        assert generated.path is None
        assert generated.attempts == 0

    assert store.run_states == [("run", RunState.HUMAN_GATE)]
    assert store.legacy_reservation_calls == 0
    assert store.provider_reservation_calls == 0
    assert provider.inspect_calls == 0
    assert provider.download_calls == 0
    assert provider.generate_calls == 0


class ExplicitRejectProvider:
    def __init__(self) -> None:
        self.posts = 0

    async def submit(self, request: ProviderRequest) -> ProviderSubmission:
        self.posts += 1
        raise ProviderOperationError(
            ProviderFailureClass.TRANSIENT,
            "explicit rejection",
            retryable=True,
            code="RateLimitExceeded",
            http_status=429,
            request_id_hmac_sha256="a" * 64,
        )


@pytest.mark.asyncio
async def test_disabled_ark_runtime_never_reaches_retryable_provider_rejection(
    tmp_path: Path,
) -> None:
    store = AsyncMemoryStore()
    provider = ExplicitRejectProvider()
    item = job().model_copy(update={"duration_ms": 4000})
    activities = RuntimeActivities(
        store,
        provider,
        tmp_path,
        ProviderProfile(provider="volcengine_ark", model=ARK_MODEL),
    )  # type: ignore[arg-type]
    frozen = activities._request("run", item, 1)
    result = await activities.submit_canary_generation("run", item, 1, frozen)
    assert result.state is RunState.HUMAN_GATE
    assert store.failure == ProviderAttemptFailure(
        failure_class=ProviderFailureClass.LIVE_NOT_AUTHORIZED,
    )
    assert store.reservation_calls == 0
    assert store.authorization_consume_calls == 0
    assert provider.posts == 0
