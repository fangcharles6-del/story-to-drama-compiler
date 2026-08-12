import asyncio
import os
import uuid
from collections import Counter
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from temporalio import workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.common import RetryPolicy
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from sdc.canary import freeze_canary_execution
from sdc.canary_rehearsal import build_rehearsal_inputs, run_rehearsal
from sdc.compiler import compile_story
from sdc.contracts import (
    DownloadedArtifact,
    GenerationJob,
    ProviderFailure,
    ProviderFailureClass,
    ProviderProfile,
    ProviderSubmission,
    ProviderTaskSnapshot,
    ProviderTaskState,
    RunState,
    StoryBeat,
    StoryInput,
)
from sdc.payloads import DurableResult
from sdc.persistence import (
    ArtifactRecord,
    AttemptRecord,
    EventRecord,
    LiveAuthorizationUseRecord,
    RunRecord,
)
from sdc.provider import GenerationError
from sdc.runtime import PostgresRuntimeStore, RuntimeActivities
from sdc.workflow import CanaryWorkflow, DramaWorkflow, generate_activity

DATABASE_URL = os.environ.get("SDC_DATABASE_URL", "postgresql+asyncpg://sdc:sdc@localhost:5432/sdc")
TEMPORAL_ADDRESS = os.environ.get("SDC_TEMPORAL_ADDRESS", "localhost:7233")


class LocalProvider:
    async def submit(self, request: object) -> ProviderSubmission:
        return ProviderSubmission(
            provider_task_id=f"task-{id(request)}", state=ProviderTaskState.SUCCEEDED
        )

    async def inspect(self, task_id: str) -> ProviderTaskSnapshot:
        return ProviderTaskSnapshot(
            provider_task_id=task_id, state=ProviderTaskState.SUCCEEDED, result_available=True
        )

    async def download(self, task_id: str, output: Path) -> DownloadedArtifact:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"integration-candidate")
        return DownloadedArtifact(
            provider_task_id=task_id,
            path=str(output),
            sha256="a" * 64,
            size_bytes=21,
            ffprobe={"streams": [{"codec_type": "video"}]},
        )

    async def generate(self, _job: object, output: Path, _attempt: int) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"integration-candidate")
        return output


class FailingProvider:
    def __init__(self) -> None:
        self.posts = 0

    async def submit(self, request: object) -> ProviderSubmission:
        self.posts += 1
        return ProviderSubmission(
            provider_task_id=f"failed-{id(request)}", state=ProviderTaskState.QUEUED
        )

    async def inspect(self, task_id: str) -> ProviderTaskSnapshot:
        return ProviderTaskSnapshot(
            provider_task_id=task_id,
            state=ProviderTaskState.FAILED,
            failure=ProviderFailure(
                failure_class=ProviderFailureClass.REMOTE_FAILED, message="planned"
            ),
        )

    async def generate(self, _job: object, _output: Path, _attempt: int) -> Path:
        raise GenerationError("planned integration failure")


class NoCallProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, _job: object, _output: Path, _attempt: int) -> Path:
        self.calls += 1
        raise AssertionError("durable exhaustion must prevent a provider call after restart")


class NoSubmitProvider:
    def __init__(self) -> None:
        self.posts = 0

    async def submit(self, _request: object) -> ProviderSubmission:
        self.posts += 1
        raise AssertionError("mismatched frozen canary request must fail before submit")


@workflow.defn
class RestartProbeWorkflow:
    def __init__(self) -> None:
        self._phase = "starting"
        self._resume = False

    @workflow.run
    async def run(self, run_id: str, job: GenerationJob) -> list[DurableResult]:
        first = await workflow.execute_activity(
            generate_activity,
            args=[run_id, job],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        self._phase = "waiting"
        await workflow.wait_condition(lambda: self._resume)
        second = await workflow.execute_activity(
            generate_activity,
            args=[run_id, job],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        return [first, second]

    @workflow.query
    def phase(self) -> str:
        return self._phase

    @workflow.signal
    async def resume(self) -> None:
        self._resume = True


async def wait_until_waiting(
    handle: WorkflowHandle[RestartProbeWorkflow, list[DurableResult]],
) -> None:
    for _ in range(100):
        try:
            if await handle.query(RestartProbeWorkflow.phase) == "waiting":
                return
        except Exception:
            pass
        await asyncio.sleep(0.05)
    raise AssertionError("workflow did not reach the restart boundary")


@pytest.mark.asyncio
async def test_two_same_story_runs_are_isolated_and_reach_succeeded_state(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(DATABASE_URL)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    graph = compile_story(
        StoryInput(title="same", beats=(StoryBeat(text="beat", duration_ms=40),))
    )[3]
    queue = f"integration-{uuid.uuid4().hex}"
    client = await Client.connect(TEMPORAL_ADDRESS, data_converter=pydantic_data_converter)

    async def execute(run_id: str) -> list[DurableResult]:
        activities = RuntimeActivities(PostgresRuntimeStore(sessions), LocalProvider(), tmp_path)  # type: ignore[arg-type]
        async with Worker(
            client,
            task_queue=queue,
            workflows=[DramaWorkflow],
            activities=[
                activities.submit_generation,
                activities.watch_generation,
                activities.download_generation,
                activities.set_run_state,
            ],
        ):
            return await client.execute_workflow(
                DramaWorkflow.run, args=[run_id, graph], id=run_id, task_queue=queue
            )

    run_one, run_two = f"run_{uuid.uuid4().hex}", f"run_{uuid.uuid4().hex}"
    first = await execute(run_one)
    second = await execute(run_two)
    assert first and second

    async with sessions() as session:
        run_ids = [run_one, run_two]
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AttemptRecord)
                .where(AttemptRecord.run_id.in_(run_ids))
            )
            == 2
        )
        attempts = (
            await session.scalars(select(AttemptRecord).where(AttemptRecord.run_id.in_(run_ids)))
        ).all()
        assert {(item.run_id, item.job_id, item.attempt) for item in attempts} == {
            (run_one, graph.jobs[0].id, 1),
            (run_two, graph.jobs[0].id, 1),
        }
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ArtifactRecord)
                .where(ArtifactRecord.run_id.in_(run_ids))
            )
            == 2
        )
        artifacts = (
            await session.scalars(select(ArtifactRecord).where(ArtifactRecord.run_id.in_(run_ids)))
        ).all()
        assert {(item.run_id, item.job_id, item.is_current) for item in artifacts} == {
            (run_one, graph.jobs[0].id, True),
            (run_two, graph.jobs[0].id, True),
        }
        events = (
            await session.scalars(select(EventRecord).where(EventRecord.run_id.in_(run_ids)))
        ).all()
        assert len(events) == 10
        expected_event_types = {
            "provider.attempt_reserved",
            "provider.submission_accepted",
            "provider.status_observed",
            "provider.artifact_downloaded",
            "provider.artifact_verified",
        }
        assert Counter((item.run_id, item.event_type) for item in events) == Counter(
            {(run_id, event_type): 1 for run_id in run_ids for event_type in expected_event_types}
        )
        states = (
            await session.scalars(
                select(RunRecord.state).where(RunRecord.id.in_([run_one, run_two]))
            )
        ).all()
        assert states == [RunState.SUCCEEDED.value, RunState.SUCCEEDED.value]
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
        client,
        task_queue=queue,
        workflows=[DramaWorkflow],
        activities=[
            activities.submit_generation,
            activities.watch_generation,
            activities.download_generation,
            activities.set_run_state,
        ],
    ):
        results = await client.execute_workflow(
            DramaWorkflow.run, args=[run_id, graph], id=run_id, task_queue=queue
        )
    assert results[0].state is RunState.STOP_2
    result = await activities.generate(run_id, graph.jobs[0])
    assert result.state is RunState.STOP_2
    async with sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AttemptRecord)
                .where(AttemptRecord.run_id == run_id)
            )
            == 2
        )
        assert await session.scalar(select(RunRecord.state).where(RunRecord.id == run_id)) == (
            RunState.STOP_2.value
        )
    await engine.dispose()


@pytest.mark.asyncio
async def test_frozen_canary_request_crosses_temporal_and_fails_closed_on_profile_mismatch(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(DATABASE_URL)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    graph = compile_story(
        StoryInput(title="canary", beats=(StoryBeat(text="safe", duration_ms=4000),))
    )[3]
    run_id, queue = f"canary_{uuid.uuid4().hex}", f"integration-{uuid.uuid4().hex}"
    execution = freeze_canary_execution(run_id, graph)
    client = await Client.connect(TEMPORAL_ADDRESS, data_converter=pydantic_data_converter)
    provider = NoSubmitProvider()
    activities = RuntimeActivities(PostgresRuntimeStore(sessions), provider, tmp_path)  # type: ignore[arg-type]
    async with Worker(
        client,
        task_queue=queue,
        workflows=[CanaryWorkflow],
        activities=[
            activities.submit_canary_generation,
            activities.watch_generation,
            activities.download_generation,
            activities.set_run_state,
        ],
    ):
        results = await client.execute_workflow(
            CanaryWorkflow.run,
            args=[execution],
            id=execution.run_id,
            task_queue=queue,
        )
    assert results == [DurableResult(state=RunState.HUMAN_GATE, path=None, attempts=1)]
    assert provider.posts == 0
    async with sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AttemptRecord)
                .where(AttemptRecord.run_id == run_id)
            )
            == 0
        )
        assert await session.scalar(select(RunRecord.state).where(RunRecord.id == run_id)) == (
            RunState.HUMAN_GATE.value
        )
    await engine.dispose()


@pytest.mark.asyncio
async def test_same_workflow_resumes_on_fresh_worker_without_third_provider_call(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(DATABASE_URL)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    graph = compile_story(
        StoryInput(title="restart", beats=(StoryBeat(text="beat", duration_ms=40),))
    )[3]
    run_id, queue = f"run_{uuid.uuid4().hex}", f"integration-{uuid.uuid4().hex}"
    client = await Client.connect(TEMPORAL_ADDRESS, data_converter=pydantic_data_converter)
    first_activities = RuntimeActivities(
        PostgresRuntimeStore(sessions), FailingProvider(), tmp_path
    )  # type: ignore[arg-type]

    async with Worker(
        client,
        task_queue=queue,
        workflows=[RestartProbeWorkflow],
        activities=[first_activities.generate],
    ):
        handle = await client.start_workflow(
            RestartProbeWorkflow.run,
            args=[run_id, graph.jobs[0]],
            id=run_id,
            task_queue=queue,
        )
        await wait_until_waiting(handle)

    no_call_provider = NoCallProvider()
    second_activities = RuntimeActivities(
        PostgresRuntimeStore(sessions), no_call_provider, tmp_path
    )  # type: ignore[arg-type]
    async with Worker(
        client,
        task_queue=queue,
        workflows=[RestartProbeWorkflow],
        activities=[second_activities.generate],
    ):
        await handle.signal(RestartProbeWorkflow.resume)
        results = await handle.result()

    assert [item.state for item in results] == [RunState.STOP_2, RunState.STOP_2]
    assert no_call_provider.calls == 0
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


@pytest.mark.asyncio
async def test_fake_canary_rehearsal_crosses_postgres_and_temporal(tmp_path: Path) -> None:
    run_id = f"sdc-canary-001-v01-rehearsal-{uuid.uuid4().hex}"
    report = await run_rehearsal(
        run_id=run_id,
        database_url=DATABASE_URL,
        temporal_address=TEMPORAL_ADDRESS,
        output_root=tmp_path,
    )
    assert report.state is RunState.SUCCEEDED
    assert report.task_queue == "sdc-canary-001-v01-rehearsal"
    assert report.runs == report.jobs == report.attempts == 1
    assert report.maximum_attempt == report.current_candidates == 1
    assert report.provider_submit_calls == 1 and report.provider_http_posts == 0
    assert report.live_authorizations == 0 and report.activity_max_concurrency == 1
    assert (report.width, report.height, report.fps, report.duration_ms) == (1080, 1920, 24, 4000)
    assert report.generate_audio is False and report.text_only is True


@pytest.mark.asyncio
async def test_fake_canary_activity_restart_reuses_attempt_one_without_resubmit(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(DATABASE_URL)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    run_id = f"sdc-canary-001-v01-restart-{uuid.uuid4().hex}"
    graph, request = build_rehearsal_inputs(run_id)
    profile = ProviderProfile(
        provider="fake",
        model="fake-v1",
        min_duration_ms=4000,
        max_duration_ms=4000,
        max_in_flight=1,
    )
    first_worker = RuntimeActivities(
        PostgresRuntimeStore(sessions),
        LocalProvider(),
        tmp_path,
        profile,
    )  # type: ignore[arg-type]
    first = await first_worker.submit_canary_generation(run_id, graph.jobs[0], 1, request)
    assert first.provider_task_id is not None

    no_submit = NoSubmitProvider()
    restarted_worker = RuntimeActivities(
        PostgresRuntimeStore(sessions),
        no_submit,
        tmp_path,
        profile,
    )  # type: ignore[arg-type]
    resumed = await restarted_worker.submit_canary_generation(run_id, graph.jobs[0], 1, request)
    assert resumed.provider_task_id == first.provider_task_id
    assert no_submit.posts == 0
    async with sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AttemptRecord)
                .where(AttemptRecord.run_id == run_id)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.max(AttemptRecord.attempt)).where(AttemptRecord.run_id == run_id)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(LiveAuthorizationUseRecord)
                .where(LiveAuthorizationUseRecord.run_id == run_id)
            )
            == 0
        )
    await engine.dispose()
