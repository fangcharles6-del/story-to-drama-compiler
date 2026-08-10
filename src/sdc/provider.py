"""Replaceable asynchronous provider adapters.

The Ark adapter contains no credentials or remote calls at import time.  Tests inject an
``httpx.MockTransport``; the safe worker default remains :class:`FakeProvider`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

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


class SubmissionUnknown(GenerationError):
    """The POST may have been accepted; callers must persist and enter HUMAN_GATE."""


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


class VolcengineArkProvider:
    """Seedance 2.0 HTTP adapter. Signed result URLs are held only in process memory."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = ARK_MODEL,
        base_url: str = ARK_BASE_URL,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("SDC_ARK_API_KEY is required for volcengine_ark")
        self.model = model
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
        self._result_urls: dict[str, str] = {}

    async def submit(self, request: ProviderRequest) -> ProviderSubmission:
        if request.provider != "volcengine_ark" or request.model != self.model:
            raise GenerationError("request profile does not match configured Ark adapter")
        if not 4000 <= request.duration_ms <= 15000:
            raise GenerationError("Ark duration must be between 4000 and 15000 ms")
        payload = {
            "model": request.model,
            "content": [{"type": "text", "text": request.prompt}],
            "duration": request.duration_ms // 1000,
            "ratio": request.aspect_ratio,
            "resolution": request.resolution,
        }
        try:
            response = await self._client.post("/contents/generations/tasks", json=payload)
        except httpx.TransportError as exc:
            raise SubmissionUnknown(
                "Ark submission outcome is unknown; manual review required"
            ) from exc
        if response.status_code in {401, 403}:
            raise GenerationError("Ark authentication or authorization failed")
        if response.status_code >= 400:
            raise GenerationError(f"Ark rejected submission with HTTP {response.status_code}")
        data = response.json()
        task_id = data.get("id") or data.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise SubmissionUnknown(
                "Ark submission response omitted task id; manual review required"
            )
        return ProviderSubmission(
            provider_task_id=task_id, state=ProviderTaskState(data.get("status", "queued"))
        )

    async def inspect(self, provider_task_id: str) -> ProviderTaskSnapshot:
        response = await self._client.get(f"/contents/generations/tasks/{provider_task_id}")
        response.raise_for_status()
        data = response.json()
        state = ProviderTaskState(data["status"])
        content = data.get("content") or {}
        url = content.get("video_url") if isinstance(content, dict) else None
        if isinstance(url, str) and state is ProviderTaskState.SUCCEEDED:
            self._result_urls[provider_task_id] = url
        error = data.get("error") or {}
        failure = None
        if state in {ProviderTaskState.FAILED, ProviderTaskState.EXPIRED}:
            failure = ProviderFailure(
                failure_class=(
                    ProviderFailureClass.EXPIRED
                    if state is ProviderTaskState.EXPIRED
                    else ProviderFailureClass.REMOTE_FAILED
                ),
                code=str(error.get("code", "")) or None,
                message=str(error.get("message", "remote generation failed")),
            )
        usage = data.get("usage") or {}
        return ProviderTaskSnapshot(
            provider_task_id=provider_task_id,
            state=state,
            usage_tokens=usage.get("completion_tokens"),
            failure=failure,
            result_available=bool(url),
        )

    async def download(self, provider_task_id: str, destination: Path) -> DownloadedArtifact:
        if provider_task_id not in self._result_urls:
            snapshot = await self.inspect(provider_task_id)
            if snapshot.state is not ProviderTaskState.SUCCEEDED:
                raise GenerationError("Ark task is not ready for download")
        url = self._result_urls[provider_task_id]
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".part")
        async with self._client.stream("GET", url) as response:
            response.raise_for_status()
            with partial.open("wb") as handle:
                async for chunk in response.aiter_bytes():
                    handle.write(chunk)
        partial.replace(destination)
        return await _evidence(provider_task_id, destination)

    async def cancel(self, provider_task_id: str) -> CancelResult:
        response = await self._client.delete(f"/contents/generations/tasks/{provider_task_id}")
        return CancelResult(provider_task_id=provider_task_id, cancelled=response.is_success)


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
