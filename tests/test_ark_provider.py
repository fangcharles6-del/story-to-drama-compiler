from pathlib import Path

import httpx
import pytest

from sdc.ark_provider import VolcengineArkProvider
from sdc.contracts import InputMaterial, ProviderRequest, ProviderTaskState
from sdc.provider import SubmissionUnknown


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


@pytest.mark.asyncio
async def test_input_materials_map_to_image_url_without_hash_in_request() -> None:
    bodies: list[dict[str, object]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        bodies.append(__import__("json").loads(req.content))
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
