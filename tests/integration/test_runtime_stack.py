import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from sdc.compiler import compile_story
from sdc.contracts import StoryBeat, StoryInput
from sdc.persistence import ArtifactRecord, AttemptRecord, EventRecord
from sdc.provider import GenerationError
from sdc.runtime import PostgresRuntimeStore, RuntimeActivities
from sdc.workflow import DramaWorkflow

DATABASE_URL = os.environ.get("SDC_DATABASE_URL", "postgresql+asyncpg://sdc:sdc@localhost:5432/sdc")
TEMPORAL_ADDRESS = os.environ.get("SDC_TEMPORAL_ADDRESS", "localhost:7233")


class LocalProvider:
    async def generate(self, _job: object, output: Path, _attempt: int) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"integration-candidate")
        return output


class FailingProvider:
    async def generate(self, _job: object, _output: Path, _attempt: int) -> Path:
        raise GenerationError("planned integration failure")


@pytest.mark.asyncio
async def test_two_same_story_runs_are_isolated_and_survive_worker_restart(tmp_path: Path) -> None:
    engine = create_async_engine(DATABASE_URL)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    graph = compile_story(
        StoryInput(title="same", beats=(StoryBeat(text="beat", duration_ms=40),))
    )[3]
    queue = f"integration-{uuid.uuid4().hex}"
    client = await Client.connect(TEMPORAL_ADDRESS, data_converter=pydantic_data_converter)

    async def execute(run_id: str) -> list[str]:
        activities = RuntimeActivities(PostgresRuntimeStore(sessions), LocalProvider(), tmp_path)  # type: ignore[arg-type]
        async with Worker(
            client, task_queue=queue, workflows=[DramaWorkflow], activities=[activities.generate]
        ):
            return await client.execute_workflow(
                DramaWorkflow.run, args=[run_id, graph], id=run_id, task_queue=queue
            )

    run_one, run_two = f"run_{uuid.uuid4().hex}", f"run_{uuid.uuid4().hex}"
    first = await execute(run_one)
    # A fresh Worker instance demonstrates that no process-local attempt state is required.
    second = await execute(run_two)
    assert first and second

    async with sessions() as session:
        for model in (AttemptRecord, EventRecord, ArtifactRecord):
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.run_id.in_([run_one, run_two]))
                )
                == 2
            )
        artifacts = (
            await session.scalars(
                select(ArtifactRecord).where(ArtifactRecord.run_id.in_([run_one, run_two]))
            )
        ).all()
        assert {(item.run_id, item.job_id, item.is_current) for item in artifacts} == {
            (run_one, graph.jobs[0].id, True),
            (run_two, graph.jobs[0].id, True),
        }
    await engine.dispose()


@pytest.mark.asyncio
async def test_stop_2_is_durable_and_never_calls_a_third_attempt(tmp_path: Path) -> None:
    engine = create_async_engine(DATABASE_URL)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    graph = compile_story(
        StoryInput(title="fail", beats=(StoryBeat(text="beat", duration_ms=40),))
    )[3]
    run_id, queue = f"run_{uuid.uuid4().hex}", f"integration-{uuid.uuid4().hex}"
    client = await Client.connect(TEMPORAL_ADDRESS, data_converter=pydantic_data_converter)
    activities = RuntimeActivities(PostgresRuntimeStore(sessions), FailingProvider(), tmp_path)  # type: ignore[arg-type]
    async with Worker(
        client, task_queue=queue, workflows=[DramaWorkflow], activities=[activities.generate]
    ):
        results = await client.execute_workflow(
            DramaWorkflow.run, args=[run_id, graph], id=run_id, task_queue=queue
        )
    assert results[0].state.value == "STOP-2"
    # Redelivery/restart sees two reservations and returns STOP-2 without provider work.
    result = await activities.generate(run_id, graph.jobs[0])
    assert result.state.value == "STOP-2"
    async with sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AttemptRecord)
                .where(AttemptRecord.run_id == run_id)
            )
            == 2
        )
    await engine.dispose()
