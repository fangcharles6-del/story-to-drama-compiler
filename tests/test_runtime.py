from pathlib import Path

import pytest

from sdc.contracts import GenerationJob, RunState
from sdc.provider import FakeProvider, GenerationError
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
