"""Provider gateway and deterministic local implementation."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sdc.contracts import GenerationJob, RunState


class GenerationError(RuntimeError):
    pass


class Provider(Protocol):
    async def generate(self, job: GenerationJob, output: Path, attempt: int) -> Path: ...


@dataclass
class AttemptResult:
    state: RunState
    path: Path | None
    attempts: int


class FakeProvider:
    """Makes one reproducible MP4 candidate per job using ffmpeg lavfi."""

    def __init__(self, fail_attempts: int = 0) -> None:
        self.fail_attempts = fail_attempts

    async def generate(self, job: GenerationJob, output: Path, attempt: int) -> Path:
        if attempt <= self.fail_attempts:
            raise GenerationError(f"planned failure {attempt}")
        output.parent.mkdir(parents=True, exist_ok=True)
        color = job.idempotency_key[-6:]
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x{color}:s=360x640:r=25:d={job.duration_ms / 1000}",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        if await proc.wait() != 0:
            raise GenerationError("ffmpeg failed")
        return output


async def generate_with_limit(
    provider: Provider, job: GenerationJob, output: Path
) -> AttemptResult:
    """Try at most twice; a third automatic generation is impossible by construction."""
    for attempt in range(1, job.max_attempts + 1):
        try:
            return AttemptResult(
                RunState.SUCCEEDED, await provider.generate(job, output, attempt), attempt
            )
        except GenerationError:
            if attempt == job.max_attempts:
                return AttemptResult(RunState.STOP_2, None, attempt)
    raise AssertionError("unreachable")
