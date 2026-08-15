"""Worker-only Volcengine Ark HTTP adapter.

This module must never be imported by workflow modules: it imports the non-deterministic HTTP
stack and is constructed only by ``sdc.worker``.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from sdc.contracts import (
    CancelResult,
    DownloadedArtifact,
    ProviderFailure,
    ProviderFailureClass,
    ProviderRequest,
    ProviderSubmission,
    ProviderTaskSnapshot,
    ProviderTaskState,
)
from sdc.provider import (
    ARK_BASE_URL,
    ARK_MODEL,
    ARK_SUBMIT_PATH,
    GenerationError,
    ProviderOperationError,
    SubmissionUnknown,
    _evidence,
    ark_submit_payload,
)

_TASK_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_REQUEST_ID_HEADERS = ("x-request-id", "x-tt-logid")
_REQUEST_ID_HMAC_DOMAIN = b"sdc:volcengine_ark:request-id:v1\0"
_KNOWN_ARK_ERROR_CODES = frozenset(
    {
        "ContentPolicy",
        "InvalidParameter",
        "RateLimitExceeded",
    }
)


def _safe_task_id(value: object) -> str | None:
    return value if isinstance(value, str) and _TASK_ID.fullmatch(value) else None


def _safe_error_code(value: object) -> str | None:
    return value if isinstance(value, str) and value in _KNOWN_ARK_ERROR_CODES else None


def _request_id_hmac_sha256(response: httpx.Response, api_key: bytes) -> str | None:
    """HMAC one bounded allowlisted header value; never persist the provider value itself."""
    for name in _REQUEST_ID_HEADERS:
        values = response.headers.get_list(name)
        if not values:
            continue
        # A malformed preferred header is not permission to fall back to a different one.
        if len(values) != 1:
            return None
        value = values[0]
        encoded = value.encode("utf-8")
        if (
            value != value.strip()
            or not 1 <= len(encoded) <= 512
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
        ):
            return None
        payload = _REQUEST_ID_HMAC_DOMAIN + name.encode("ascii") + b"\0" + encoded
        return hmac.new(api_key, payload, hashlib.sha256).hexdigest()
    return None


def _safe_response_diagnostics(
    response: httpx.Response, api_key: bytes, data: dict[str, Any] | None = None
) -> tuple[str | None, str | None]:
    request_id_hmac_sha256 = _request_id_hmac_sha256(response, api_key)
    if data is None:
        try:
            candidate = response.json()
        except (TypeError, ValueError):
            candidate = None
        data = candidate if isinstance(candidate, dict) else None
    error = data.get("error") if data is not None else None
    code = _safe_error_code(error.get("code")) if isinstance(error, dict) else None
    return code, request_id_hmac_sha256


class VolcengineArkProvider:
    """Official Seedance 2.0 adapter; credentials never reach result-host requests."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = ARK_MODEL,
        base_url: str = ARK_BASE_URL,
        client: httpx.AsyncClient | None = None,
        download_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("SDC_ARK_API_KEY is required for volcengine_ark")
        if model != ARK_MODEL:
            raise ValueError(f"Ark model is pinned to {ARK_MODEL}")
        self.model = model
        self._diagnostic_hmac_key = api_key.encode("utf-8")
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
            follow_redirects=False,
            trust_env=False,
        )
        # Deliberately separate: Ark Authorization must not be sent to signed/CDN origins.
        self._download_client = download_client or httpx.AsyncClient(
            timeout=60,
            follow_redirects=False,
            trust_env=False,
        )
        self._result_urls: dict[str, str] = {}

    async def submit(self, request: ProviderRequest) -> ProviderSubmission:
        if request.provider != "volcengine_ark" or request.model != self.model:
            raise ProviderOperationError(
                ProviderFailureClass.CONFIGURATION,
                "request profile does not match configured Ark adapter",
                retryable=False,
            )
        if not 4000 <= request.duration_ms <= 15000:
            raise ProviderOperationError(
                ProviderFailureClass.INVALID_INPUT,
                "Ark duration must be between 4000 and 15000 ms",
                retryable=False,
            )
        payload = ark_submit_payload(request)
        response: httpx.Response | None = None
        try:
            response = await self._client.post(ARK_SUBMIT_PATH, json=payload)
        except httpx.TransportError:
            pass
        if response is None:
            raise SubmissionUnknown(
                "Ark submission outcome is unknown; manual review required"
            )
        code, request_id_hmac_sha256 = _safe_response_diagnostics(
            response, self._diagnostic_hmac_key
        )
        if response.status_code in {401, 403}:
            raise ProviderOperationError(
                ProviderFailureClass.AUTHENTICATION,
                "Ark authentication or authorization failed",
                retryable=False,
                code=code,
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            )
        if response.status_code == 429 or response.status_code >= 500:
            # A response proves that this request was not accepted as a task. The activity still
            # has maximum_attempts=1; policy may explicitly reschedule this same reservation.
            raise ProviderOperationError(
                ProviderFailureClass.TRANSIENT,
                "Ark explicitly rejected submission",
                retryable=True,
                code=code,
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            )
        if response.status_code >= 400:
            raise ProviderOperationError(
                ProviderFailureClass.INVALID_INPUT,
                "Ark explicitly rejected submission",
                retryable=False,
                code=code,
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            )
        try:
            candidate = response.json()
        except (TypeError, ValueError):
            candidate = None
        if not isinstance(candidate, dict):
            raise SubmissionUnknown(
                "Ark submission response was invalid; manual review required",
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            ) from None
        data = candidate
        task_id = _safe_task_id(data.get("id") or data.get("task_id"))
        if task_id is None:
            raise SubmissionUnknown(
                "Ark submission response omitted a safe task id; manual review required",
                code=code,
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            )
        state: ProviderTaskState | None = None
        try:
            state = ProviderTaskState(data.get("status", "queued"))
        except (TypeError, ValueError):
            pass
        if state is None:
            raise SubmissionUnknown(
                "Ark submission response had an invalid state; manual review required",
                code=code,
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            )
        return ProviderSubmission(
            provider_task_id=task_id,
            state=state,
        )

    async def inspect(self, provider_task_id: str) -> ProviderTaskSnapshot:
        response: httpx.Response | None = None
        try:
            response = await self._client.get(f"/contents/generations/tasks/{provider_task_id}")
        except httpx.TransportError:
            pass
        if response is None:
            raise ProviderOperationError(
                ProviderFailureClass.TRANSIENT, "Ark inspection transport failure", retryable=True
            )
        code, request_id_hmac_sha256 = _safe_response_diagnostics(
            response, self._diagnostic_hmac_key
        )
        if response.status_code == 429 or response.status_code >= 500:
            raise ProviderOperationError(
                ProviderFailureClass.TRANSIENT,
                "Ark inspection was explicitly rejected",
                retryable=True,
                code=code,
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            )
        if response.status_code in {401, 403}:
            raise ProviderOperationError(
                ProviderFailureClass.AUTHENTICATION,
                "Ark inspection authentication failed",
                retryable=False,
                code=code,
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            )
        if response.status_code >= 400:
            raise ProviderOperationError(
                ProviderFailureClass.INVALID_INPUT,
                "Ark inspection was explicitly rejected",
                retryable=False,
                code=code,
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            )
        try:
            candidate = response.json()
        except (TypeError, ValueError):
            candidate = None
        if not isinstance(candidate, dict):
            raise ProviderOperationError(
                ProviderFailureClass.TRANSIENT,
                "Ark inspection response was invalid",
                retryable=True,
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            ) from None
        data = candidate
        state: ProviderTaskState | None = None
        try:
            state = ProviderTaskState(data["status"])
        except (KeyError, TypeError, ValueError):
            pass
        if state is None:
            raise ProviderOperationError(
                ProviderFailureClass.TRANSIENT,
                "Ark inspection response had an invalid state",
                retryable=True,
                http_status=response.status_code,
                request_id_hmac_sha256=request_id_hmac_sha256,
            )
        content = data.get("content") or {}
        url = content.get("video_url") if isinstance(content, dict) else None
        if isinstance(url, str) and state is ProviderTaskState.SUCCEEDED:
            self._result_urls[provider_task_id] = url
        failure = None
        if state in {ProviderTaskState.FAILED, ProviderTaskState.EXPIRED}:
            failure = ProviderFailure(
                failure_class=(
                    ProviderFailureClass.EXPIRED
                    if state is ProviderTaskState.EXPIRED
                    else ProviderFailureClass.REMOTE_FAILED
                ),
                code=code,
                message=(
                    "Ark generation expired"
                    if state is ProviderTaskState.EXPIRED
                    else "Ark generation failed"
                ),
            )
        usage = data.get("usage") or {}
        return ProviderTaskSnapshot(
            provider_task_id=provider_task_id,
            state=state,
            usage_tokens=usage.get("completion_tokens") if isinstance(usage, dict) else None,
            failure=failure,
            result_available=bool(url),
        )

    async def download(self, provider_task_id: str, destination: Path) -> DownloadedArtifact:
        if provider_task_id not in self._result_urls:
            snapshot = await self.inspect(provider_task_id)
            if snapshot.state is not ProviderTaskState.SUCCEEDED:
                raise GenerationError("Ark task is not ready for download")
        url = self._result_urls[provider_task_id]
        if urlparse(url).scheme not in {"http", "https"}:
            raise GenerationError("Ark result URL has an unsupported scheme")
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".part")
        try:
            async with self._download_client.stream("GET", url) as response:
                if response.status_code == 429 or response.status_code >= 500:
                    raise ProviderOperationError(
                        ProviderFailureClass.TRANSIENT,
                        "artifact download was explicitly rejected",
                        retryable=True,
                        http_status=response.status_code,
                    )
                if response.status_code >= 400:
                    raise ProviderOperationError(
                        ProviderFailureClass.INVALID_INPUT,
                        "artifact host explicitly rejected download",
                        retryable=False,
                        http_status=response.status_code,
                    )
                with partial.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        handle.write(chunk)
            # Verify the unpublished temporary file, then atomically expose it.
            evidence = await _evidence(provider_task_id, partial)
            partial.replace(destination)
            return evidence.model_copy(update={"path": str(destination)})
        except httpx.TransportError:
            partial.unlink(missing_ok=True)
            raise ProviderOperationError(
                ProviderFailureClass.TRANSIENT,
                "artifact download transport failure",
                retryable=True,
            ) from None
        except Exception:
            partial.unlink(missing_ok=True)
            raise

    async def cancel(self, provider_task_id: str) -> CancelResult:
        response = await self._client.delete(f"/contents/generations/tasks/{provider_task_id}")
        return CancelResult(provider_task_id=provider_task_id, cancelled=response.is_success)
