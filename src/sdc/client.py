"""Submission entrypoint: each invocation creates a new runtime identity."""

import argparse
import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

from temporalio.client import Client, WorkflowHandle
from temporalio.contrib.pydantic import pydantic_data_converter

from sdc.compiler import compile_story
from sdc.contracts import CanaryExecution, StoryInput
from sdc.payloads import DurableResult
from sdc.workflow import CanaryWorkflow, DramaWorkflow


async def submit(
    graph_path: Path | None = None,
    *,
    canary_execution_path: Path | None = None,
) -> WorkflowHandle[Any, list[DurableResult]]:
    """Submit a normal fresh run or one separately frozen exact canary payload."""
    if canary_execution_path is not None:
        if graph_path is not None:
            raise ValueError("story and canary execution inputs are mutually exclusive")
        execution = CanaryExecution.model_validate_json(canary_execution_path.read_text())
        run_id = execution.run_id
    else:
        source = graph_path or Path("examples/minimal_story.json")
        story = StoryInput.model_validate(json.loads(source.read_text()))
        graph = compile_story(story)[3]
        run_id = f"run_{uuid.uuid4().hex}"
    client = await Client.connect(
        os.environ.get("SDC_TEMPORAL_ADDRESS", "localhost:7233"),
        data_converter=pydantic_data_converter,
    )
    task_queue = os.environ.get("SDC_TASK_QUEUE", "sdc-generation")
    if canary_execution_path is not None:
        return await client.start_workflow(
            CanaryWorkflow.run,
            args=[execution],
            id=run_id,
            task_queue=task_queue,
        )
    return await client.start_workflow(
        DramaWorkflow.run, args=[run_id, graph], id=run_id, task_queue=task_queue
    )


async def _main(path: Path | None, canary_execution: Path | None) -> None:
    handle = await submit(path, canary_execution_path=canary_execution)
    print(handle.id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("story", nargs="?", type=Path)
    inputs.add_argument("--canary-execution", type=Path)
    args = parser.parse_args()
    asyncio.run(_main(args.story, args.canary_execution))
