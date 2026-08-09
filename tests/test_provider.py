from pathlib import Path

import pytest

from sdc.contracts import GenerationJob, RunState
from sdc.provider import FakeProvider, generate_with_limit


def job() -> GenerationJob:
    return GenerationJob(
        id="job_x", shot_id="shot_x", prompt="x", duration_ms=40, idempotency_key="generate_abcdef"
    )


@pytest.mark.asyncio
async def test_single_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    provider = FakeProvider()

    async def fake_generate(j: GenerationJob, output: Path, attempt: int) -> Path:
        calls.append(attempt)
        output.write_bytes(b"candidate")
        return output

    monkeypatch.setattr(provider, "generate", fake_generate)
    result = await generate_with_limit(provider, job(), tmp_path / "one.mp4")
    assert result.state is RunState.SUCCEEDED and calls == [1]


@pytest.mark.asyncio
async def test_stop_2_never_attempts_third(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeProvider(fail_attempts=99)
    calls: list[int] = []
    original = provider.generate

    async def tracked(j: GenerationJob, output: Path, attempt: int) -> Path:
        calls.append(attempt)
        return await original(j, output, attempt)

    monkeypatch.setattr(provider, "generate", tracked)
    result = await generate_with_limit(provider, job(), tmp_path / "none.mp4")
    assert result.state is RunState.STOP_2 and result.path is None and calls == [1, 2]
