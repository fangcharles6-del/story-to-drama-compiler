"""Submission entrypoint: each invocation creates a new runtime identity."""

import argparse
import asyncio
import json
import os
import uuid
from pathlib import Path

from temporalio.client import Client, WorkflowHandle
from temporalio.contrib.pydantic import pydantic_data_converter

from sdc.compiler import compile_story
from sdc.contracts import StoryInput
from sdc.payloads import DurableResult
from sdc.workflow import DramaWorkflow


async def submit(
    graph_path: Path | None = None,
) -> WorkflowHandle[DramaWorkflow, list[DurableResult]]:
    """Compile and submit a story with a fresh run ID used as the Temporal workflow ID."""
    source = graph_path or Path("examples/minimal_story.json")
    story = StoryInput.model_validate(json.loads(source.read_text()))
    graph = compile_story(story)[3]
    run_id = f"run_{uuid.uuid4().hex}"
    client = await Client.connect(
        os.environ.get("SDC_TEMPORAL_ADDRESS", "localhost:7233"),
        data_converter=pydantic_data_converter,
    )
    return await client.start_workflow(
        DramaWorkflow.run,
        args=[run_id, graph],
        id=run_id,
        task_queue=os.environ.get("SDC_TASK_QUEUE", "sdc-generation"),
    )


async def _main(path: Path | None) -> None:
    handle = await submit(path)
    print(handle.id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("story", nargs="?", type=Path)
    args = parser.parse_args()
    asyncio.run(_main(args.story))
