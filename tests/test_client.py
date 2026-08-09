from pathlib import Path
from typing import Any

import pytest

from sdc.client import submit


@pytest.mark.asyncio
async def test_submission_uses_unique_run_as_workflow_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    story = tmp_path / "story.json"
    story.write_text('{"title":"t","beats":[{"text":"b"}]}')
    calls: list[dict[str, Any]] = []

    class Client:
        async def start_workflow(self, *_args: object, **kwargs: Any) -> object:
            calls.append(kwargs)
            return object()

    async def connect(*_args: object, **_kwargs: object) -> Client:
        return Client()

    monkeypatch.setattr("sdc.client.Client.connect", connect)
    await submit(story)
    await submit(story)
    assert calls[0]["id"] == calls[0]["args"][0]
    assert calls[1]["id"] == calls[1]["args"][0]
    assert calls[0]["id"] != calls[1]["id"]
    assert calls[0]["args"][1].id == calls[1]["args"][1].id
