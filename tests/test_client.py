from pathlib import Path
from typing import Any

import pytest

from sdc.canary import freeze_canary_execution
from sdc.client import submit
from sdc.compiler import compile_story
from sdc.contracts import StoryBeat, StoryInput


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


@pytest.mark.asyncio
async def test_canary_submission_uses_frozen_identity_and_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    graph = compile_story(
        StoryInput(title="canary", beats=(StoryBeat(text="safe", duration_ms=4000),))
    )[3]
    execution = freeze_canary_execution("canary-run-fixed", graph)
    execution_path = tmp_path / "execution.json"
    execution_path.write_text(execution.model_dump_json())
    calls: list[dict[str, Any]] = []

    class Client:
        async def start_workflow(self, *_args: object, **kwargs: Any) -> object:
            calls.append(kwargs)
            return object()

    async def connect(*_args: object, **_kwargs: object) -> Client:
        return Client()

    monkeypatch.setattr("sdc.client.Client.connect", connect)
    await submit(canary_execution_path=execution_path)
    assert calls[0]["id"] == "canary-run-fixed"
    assert calls[0]["args"] == [execution]
