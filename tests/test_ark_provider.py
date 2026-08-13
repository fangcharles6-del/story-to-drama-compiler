import json
from pathlib import Path

import httpx
import pytest

from sdc.ark_provider import VolcengineArkProvider
from sdc.contracts import InputMaterial, ProviderFailureClass, ProviderRequest, ProviderTaskState
from sdc.provider import ProviderOperationError, SubmissionUnknown

HMAC_API_KEY = "test-ark-api-key"
REQUEST_ID_HMAC = "fddc4155da1f7fe2aad99a69082efa0755279f8967138d15e5fb56a6b56eb114"
TT_LOGID_HMAC = "5805b0ff8b2503b67e37425ae10443d108e4b71e46a20befabad1bff6dfbef3e"
SHORT_SECRET_HMAC = "fbbc63ab555e1e90787002a34e05cf9fe33aa5217c37f03bf906dd887b020ba6"


def request(duration_ms: int = 4000) -> ProviderRequest:
    return ProviderRequest(
        run_id="run",
        job_id="job",
        attempt=1,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        prompt="safe prompt",
        duration_ms=duration_ms,
        aspect_ratio="9:16",
        resolution="1080p",
        generate_audio=False,
        request_fingerprint="a" * 64,
    )


@pytest.mark.asyncio
async def test_ark_submit_inspect_uses_official_boundary() -> None:
    calls: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        if req.method == "POST":
            assert req.headers["authorization"] == "Bearer secret"
            assert json.loads(req.content)["generate_audio"] is False
            return httpx.Response(200, json={"id": "task-1", "status": "queued"})
        return httpx.Response(
            200,
            json={
                "id": "task-1",
                "status": "succeeded",
                "content": {"video_url": "https://signed.invalid/video?token=sensitive"},
                "usage": {"completion_tokens": 7},
            },
        )

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer secret"},
    )
    provider = VolcengineArkProvider("secret", client=client)
    submission = await provider.submit(request())
    snapshot = await provider.inspect(submission.provider_task_id)
    assert submission.state is ProviderTaskState.QUEUED
    assert snapshot.state is ProviderTaskState.SUCCEEDED and snapshot.usage_tokens == 7
    assert "video_url" not in snapshot.model_dump_json()
    assert [item.method for item in calls] == ["POST", "GET"]
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("duration", [3999, 15001])
async def test_invalid_duration_fails_before_post(duration: int) -> None:
    posts = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal posts
        posts += 1
        return httpx.Response(500)

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider("secret", client=client)
    with pytest.raises(Exception, match="duration"):
        await provider.submit(request(duration))
    assert posts == 0
    await client.aclose()


@pytest.mark.asyncio
async def test_lost_post_response_is_submission_unknown_without_retry() -> None:
    posts = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal posts
        posts += 1
        raise httpx.ReadError("lost", request=req)

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider("do-not-leak", client=client)
    with pytest.raises(SubmissionUnknown) as caught:
        await provider.submit(request())
    assert posts == 1 and "do-not-leak" not in str(caught.value)
    assert caught.value.failure_record.http_status is None
    assert caught.value.__context__ is None
    await client.aclose()


@pytest.mark.asyncio
async def test_rejection_keeps_only_bounded_allowlisted_diagnostics() -> None:
    raw_request_id = "req-0123:abc"
    secret_message = (
        "safe prompt Bearer test-ark-api-key https://signed.invalid/video?token=private"
    )

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"code": "InvalidParameter", "message": secret_message}},
            headers={
                "x-request-id": raw_request_id,
                "authorization": "Bearer reflected-secret",
            },
        )

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider(HMAC_API_KEY, client=client)
    with pytest.raises(ProviderOperationError) as caught:
        await provider.submit(request())
    failure = caught.value.failure_record
    assert failure.failure_class is ProviderFailureClass.INVALID_INPUT
    assert failure.http_status == 400
    assert failure.provider_code == "InvalidParameter"
    assert failure.provider_request_id_hmac_sha256 == REQUEST_ID_HMAC
    assert failure.local_message == "provider rejected invalid input"
    serialized = repr(failure) + str(caught.value)
    secrets = (
        raw_request_id,
        secret_message,
        "safe prompt",
        HMAC_API_KEY,
        "reflected-secret",
        "signed.invalid",
    )
    for secret in secrets:
        assert secret not in serialized
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["ContentPolicy", "InvalidParameter", "RateLimitExceeded"])
async def test_error_code_allowlist_accepts_only_exact_known_values(code: str) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"code": code}})

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider("secret", client=client)
    with pytest.raises(ProviderOperationError) as caught:
        await provider.submit(request())
    assert caught.value.failure_record.provider_code == code
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code",
    [
        " InvalidParameter",
        "InvalidParameter ",
        "invalidparameter",
        "sk-test-secret",
        "Bearer short-secret",
        "https://signed.invalid/error?token=private",
        "A" * 129,
        7,
        None,
    ],
)
async def test_error_code_allowlist_rejects_untrusted_or_normalized_values(
    code: object,
) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"code": code}})

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider("secret", client=client)
    with pytest.raises(ProviderOperationError) as caught:
        await provider.submit(request())
    failure = caught.value.failure_record
    assert failure.provider_code is None
    if isinstance(code, str):
        assert code not in repr(failure) + str(caught.value)
    await client.aclose()


@pytest.mark.asyncio
async def test_short_token_like_request_id_is_persisted_only_as_keyed_hmac() -> None:
    raw_request_id = "sk-short-secret"

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(400, headers={"x-request-id": raw_request_id})

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider(HMAC_API_KEY, client=client)
    with pytest.raises(ProviderOperationError) as caught:
        await provider.submit(request())
    failure = caught.value.failure_record
    assert failure.provider_request_id_hmac_sha256 == SHORT_SECRET_HMAC
    serialized = repr(failure) + str(caught.value)
    assert raw_request_id not in serialized
    assert HMAC_API_KEY not in serialized
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        [(b"x-request-id", b"duplicate-one"), (b"x-request-id", b"duplicate-two")],
        [(b"x-request-id", b"")],
        [(b"x-request-id", b" padded ")],
        [(b"x-request-id", b"bad\x01value")],
        [(b"x-request-id", b"a" * 513)],
        [(b"x-request-id", b" padded "), (b"x-tt-logid", b"ark-log-123")],
    ],
    ids=[
        "duplicate",
        "empty",
        "surrounding-whitespace",
        "control-character",
        "over-512-bytes",
        "invalid-primary-does-not-fall-back",
    ],
)
async def test_untrusted_request_id_headers_are_dropped(
    headers: list[tuple[bytes, bytes]],
) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(400, headers=headers)

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider(HMAC_API_KEY, client=client)
    with pytest.raises(ProviderOperationError) as caught:
        await provider.submit(request())
    assert caught.value.failure_record.provider_request_id_hmac_sha256 is None
    await client.aclose()


@pytest.mark.asyncio
async def test_body_request_id_is_not_a_trusted_diagnostic_source() -> None:
    raw_request_id = "sk-short-secret"

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"request_id": raw_request_id})

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider(HMAC_API_KEY, client=client)
    with pytest.raises(ProviderOperationError) as caught:
        await provider.submit(request())
    failure = caught.value.failure_record
    assert failure.provider_request_id_hmac_sha256 is None
    assert raw_request_id not in repr(failure) + str(caught.value)
    await client.aclose()


@pytest.mark.asyncio
async def test_non_json_rejection_does_not_persist_body() -> None:
    raw_body = b"Bearer raw-secret https://signed.invalid/result?token=private"

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            content=raw_body,
        )

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider("secret", client=client)
    with pytest.raises(ProviderOperationError) as caught:
        await provider.submit(request())
    failure = caught.value.failure_record
    assert failure.http_status == 422
    assert failure.provider_code is None
    assert failure.provider_request_id_hmac_sha256 is None
    assert raw_body.decode() not in repr(failure) + str(caught.value)
    await client.aclose()


@pytest.mark.asyncio
async def test_success_without_task_id_records_only_safe_response_metadata() -> None:
    raw_request_id = "ark-log-123"

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "queued", "message": "safe prompt should not persist"},
            headers={"x-tt-logid": raw_request_id},
        )

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider(HMAC_API_KEY, client=client)
    with pytest.raises(SubmissionUnknown) as caught:
        await provider.submit(request())
    failure = caught.value.failure_record
    assert failure.http_status == 200
    assert failure.provider_request_id_hmac_sha256 == TT_LOGID_HMAC
    serialized = repr(failure) + str(caught.value)
    assert raw_request_id not in serialized
    assert "safe prompt" not in serialized
    await client.aclose()


@pytest.mark.asyncio
async def test_success_with_untrusted_task_or_state_fails_with_safe_diagnostics() -> None:
    unsafe_values = (
        {"id": "https://signed.invalid/task?token=secret", "status": "queued"},
        {"id": "task-safe", "status": "safe prompt Bearer secret"},
    )
    for body in unsafe_values:

        def handler(req: httpx.Request, response_body: dict[str, str] = body) -> httpx.Response:
            return httpx.Response(200, json=response_body)

        client = httpx.AsyncClient(
            base_url="https://mock.invalid/api/v3",
            transport=httpx.MockTransport(handler),
        )
        provider = VolcengineArkProvider("secret", client=client)
        with pytest.raises(SubmissionUnknown) as caught:
            await provider.submit(request())
        serialized = repr(caught.value.failure_record) + str(caught.value)
        assert "signed.invalid" not in serialized
        assert "safe prompt" not in serialized
        assert caught.value.failure_record.http_status == 200
        await client.aclose()


@pytest.mark.asyncio
async def test_remote_failure_does_not_copy_provider_message() -> None:
    reflected = "safe prompt Bearer secret https://signed.invalid/output?token=private"

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "task",
                "status": "failed",
                "error": {"code": "ContentPolicy", "message": reflected},
            },
            headers={"x-request-id": "req-remote-failure"},
        )

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider("secret", client=client)
    snapshot = await provider.inspect("task")
    assert snapshot.failure is not None
    assert snapshot.failure.code == "ContentPolicy"
    assert snapshot.failure.message == "Ark generation failed"
    assert "req-remote-failure" not in snapshot.model_dump_json()
    assert reflected not in snapshot.model_dump_json()
    await client.aclose()


@pytest.mark.asyncio
async def test_input_materials_map_to_image_url_without_hash_in_request() -> None:
    bodies: list[dict[str, object]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(req.content))
        return httpx.Response(200, json={"id": "task", "status": "queued"})

    client = httpx.AsyncClient(
        base_url="https://mock.invalid/api/v3", transport=httpx.MockTransport(handler)
    )
    provider = VolcengineArkProvider("secret", client=client)
    material_request = request().model_copy(
        update={
            "input_materials": (
                InputMaterial(
                    reference="https://signed.invalid/input?token=secret", sha256="b" * 64
                ),
            )
        }
    )
    await provider.submit(material_request)
    content = bodies[0]["content"]
    assert isinstance(content, list)
    assert {
        "type": "image_url",
        "image_url": "https://signed.invalid/input?token=secret",
    } in content
    assert "b" * 64 not in str(bodies[0])
    await client.aclose()


@pytest.mark.asyncio
async def test_cross_origin_download_has_no_ark_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sdc.contracts import DownloadedArtifact

    seen: list[httpx.Request] = []

    def ark_handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "succeeded",
                "content": {"video_url": "https://cdn.invalid/video?signature=private"},
            },
        )

    def download_handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, content=b"video")

    ark = httpx.AsyncClient(
        base_url="https://ark.invalid/api/v3",
        transport=httpx.MockTransport(ark_handler),
        headers={"Authorization": "Bearer secret"},
    )
    downloads = httpx.AsyncClient(transport=httpx.MockTransport(download_handler))

    async def evidence(task_id: str, path: Path) -> DownloadedArtifact:
        return DownloadedArtifact(
            provider_task_id=task_id,
            path=str(path),
            sha256="c" * 64,
            size_bytes=5,
            ffprobe={"streams": [{}]},
        )

    monkeypatch.setattr("sdc.ark_provider._evidence", evidence)
    provider = VolcengineArkProvider("secret", client=ark, download_client=downloads)
    result = await provider.download("task", tmp_path / "result.mp4")
    assert result.path.endswith("result.mp4") and (tmp_path / "result.mp4").read_bytes() == b"video"
    assert "authorization" not in seen[0].headers
    assert "signature" not in result.model_dump_json()
    await ark.aclose()
    await downloads.aclose()
