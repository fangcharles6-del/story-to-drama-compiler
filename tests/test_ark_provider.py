
import httpx
import pytest

from sdc.contracts import ProviderRequest, ProviderTaskState
from sdc.provider import SubmissionUnknown, VolcengineArkProvider


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
        request_fingerprint="a" * 64,
    )


@pytest.mark.asyncio
async def test_ark_submit_inspect_uses_official_boundary() -> None:
    calls: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        if req.method == "POST":
            assert req.headers["authorization"] == "Bearer secret"
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
    await client.aclose()
