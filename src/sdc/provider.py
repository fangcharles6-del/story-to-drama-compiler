"""Deterministic provider boundary and offline adapter (Temporal-sandbox safe)."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sdc.contracts import (
    CancelResult,
    DownloadedArtifact,
    GenerationJob,
    ProviderFailure,
    ProviderFailureClass,
    ProviderRequest,
    ProviderSubmission,
    ProviderTaskSnapshot,
    ProviderTaskState,
    RunState,
)

ARK_MODEL = "doubao-seedance-2-0-260128"
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"


class GenerationError(RuntimeError):
    pass


class ProviderOperationError(GenerationError):
    def __init__(
        self, failure_class: ProviderFailureClass, message: str, *, retryable: bool
    ) -> None:
        super().__init__(message)
        self.failure_class = failure_class
        self.retryable = retryable


class SubmissionUnknown(ProviderOperationError):
    """The POST may have been accepted; callers must persist and enter HUMAN_GATE."""

    def __init__(self, message: str) -> None:
        super().__init__(ProviderFailureClass.SUBMISSION_UNKNOWN, message, retryable=False)


class Provider(Protocol):
    async def submit(self, request: ProviderRequest) -> ProviderSubmission: ...
    async def inspect(self, provider_task_id: str) -> ProviderTaskSnapshot: ...
    async def download(self, provider_task_id: str, destination: Path) -> DownloadedArtifact: ...
    async def cancel(self, provider_task_id: str) -> CancelResult: ...


class LegacyProvider(Protocol):
    """BUILD-001/002 local compiler boundary, pending removal after workflow cutover."""

    async def generate(self, job: GenerationJob, output: Path, attempt: int) -> Path: ...


@dataclass
class AttemptResult:
    state: RunState
    path: Path | None
    attempts: int


def request_fingerprint(request: ProviderRequest) -> str:
    """Fingerprint stable request inputs (never adapter commands or credentials)."""
    body = request.model_dump(exclude={"request_fingerprint"}, mode="json")
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


async def _probe(path: Path) -> dict[str, object]:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode:
        raise GenerationError("downloaded artifact failed ffprobe verification")
    value = json.loads(stdout)
    if not isinstance(value, dict) or not value.get("streams"):
        raise GenerationError("downloaded artifact contains no media stream")
    return value


async def _evidence(task_id: str, path: Path) -> DownloadedArtifact:
    data = path.read_bytes()
    return DownloadedArtifact(
        provider_task_id=task_id,
        path=str(path),
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        ffprobe=await _probe(path),
    )


class FakeProvider:
    """Deterministic, entirely offline provider implementing both old and new boundaries."""

    def __init__(self, fail_attempts: int = 0) -> None:
        self.fail_attempts = fail_attempts
        self._requests: dict[str, ProviderRequest] = {}

    async def submit(self, request: ProviderRequest) -> ProviderSubmission:
        task_id = f"fake-{request.request_fingerprint[:24]}"
        self._requests[task_id] = request
        state = (
            ProviderTaskState.FAILED
            if request.attempt <= self.fail_attempts
            else ProviderTaskState.SUCCEEDED
        )
        return ProviderSubmission(provider_task_id=task_id, state=state)

    async def inspect(self, provider_task_id: str) -> ProviderTaskSnapshot:
        request = self._requests[provider_task_id]
        failed = request.attempt <= self.fail_attempts
        return ProviderTaskSnapshot(
            provider_task_id=provider_task_id,
            state=ProviderTaskState.FAILED if failed else ProviderTaskState.SUCCEEDED,
            failure=ProviderFailure(
                failure_class=ProviderFailureClass.REMOTE_FAILED, message="planned offline failure"
            )
            if failed
            else None,
            result_available=not failed,
        )

    async def download(self, provider_task_id: str, destination: Path) -> DownloadedArtifact:
        request = self._requests[provider_task_id]
        destination.parent.mkdir(parents=True, exist_ok=True)
        await self._render(request.job_id, request.duration_ms, destination)
        return await _evidence(provider_task_id, destination)

    async def cancel(self, provider_task_id: str) -> CancelResult:
        return CancelResult(
            provider_task_id=provider_task_id, cancelled=provider_task_id in self._requests
        )

    async def _render(self, key: str, duration_ms: int, output: Path) -> None:
        color = hashlib.sha256(key.encode()).hexdigest()[:6]
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x{color}:s=360x640:r=25:d={duration_ms / 1000}",
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

    # Compatibility for the deterministic compiler and BUILD-001/002 runtime.
    async def generate(self, job: GenerationJob, output: Path, attempt: int) -> Path:
        if attempt <= self.fail_attempts:
            raise GenerationError(f"planned failure {attempt}")
        output.parent.mkdir(parents=True, exist_ok=True)
        await self._render(job.idempotency_key, job.duration_ms, output)
        return output


async def generate_with_limit(provider: object, job: GenerationJob, output: Path) -> AttemptResult:
    """Legacy local gateway: exactly two creative attempts, retained for offline compilation."""
    for attempt in range(1, job.max_attempts + 1):
        try:
            path = await provider.generate(job, output, attempt)  # type: ignore[attr-defined]
            return AttemptResult(RunState.SUCCEEDED, path, attempt)
        except GenerationError:
            if attempt == job.max_attempts:
                return AttemptResult(RunState.STOP_2, None, attempt)
    raise AssertionError("unreachable")
