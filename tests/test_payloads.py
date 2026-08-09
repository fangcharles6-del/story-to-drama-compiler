import pytest
from temporalio.contrib.pydantic import pydantic_data_converter

from sdc.compiler import compile_story
from sdc.contracts import JobGraph, StoryBeat, StoryInput


@pytest.mark.asyncio
async def test_temporal_pydantic_v2_converter_round_trip() -> None:
    graph = compile_story(StoryInput(title="payload", beats=(StoryBeat(text="beat"),)))[3]
    payloads = await pydantic_data_converter.encode([graph])
    decoded = await pydantic_data_converter.decode(payloads, [JobGraph])
    assert decoded == [graph]
