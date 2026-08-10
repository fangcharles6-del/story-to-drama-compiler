from collections.abc import Coroutine
from typing import Any

import pytest
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from sdc.contracts import GenerationJob, JobGraph, ProviderTaskState, RunState
from sdc.payloads import DurableResult, SubmitResult, WatchResult
from sdc.workflow import (
    DramaWorkflow,
    download_generation_activity,
    set_run_state_activity,
    submit_generation_activity,
    watch_generation_activity,
)


async def resolved(value: Any) -> Any:
    return value


def job(job_id: str = "job_a", depends_on: tuple[str, ...] = ()) -> GenerationJob:
    return GenerationJob(
        id=job_id,
        shot_id=f"shot_{job_id}",
        prompt="prompt",
        duration_ms=1000,
        depends_on=depends_on,
        idempotency_key=f"generate_{job_id}",
    )


@pytest.mark.asyncio
async def test_temporal_boundaries_have_safe_retry_policies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policies: list[tuple[object, RetryPolicy]] = []
    states: list[RunState] = []

    def execute_activity(definition: object, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        policies.append((definition, kwargs["retry_policy"]))
        if definition is set_run_state_activity:
            states.append(kwargs["args"][1])
            return resolved(None)
        run_id, item, attempt, *tail = kwargs["args"]
        if definition is submit_generation_activity:
            return resolved(
                SubmitResult(
                    state=RunState.RUNNING, attempt=attempt, provider_task_id=f"task-{run_id}"
                )
            )
        if definition is watch_generation_activity:
            return resolved(
                WatchResult(
                    attempt=attempt,
                    provider_task_id=tail[0],
                    task_state=ProviderTaskState.SUCCEEDED,
                )
            )
        assert definition is download_generation_activity
        return resolved(DurableResult(state=RunState.SUCCEEDED, path=item.id, attempts=attempt))

    monkeypatch.setattr("sdc.workflow.workflow.execute_activity", execute_activity)
    outputs = await DramaWorkflow().run("run_a", JobGraph(id="graph_a", jobs=(job(),)))
    assert outputs[0].state is RunState.SUCCEEDED
    assert states == [RunState.RUNNING, RunState.SUCCEEDED]
    submit_policy = next(
        policy for definition, policy in policies if definition is submit_generation_activity
    )
    assert submit_policy.maximum_attempts == 1
    assert (
        next(
            policy for definition, policy in policies if definition is watch_generation_activity
        ).maximum_attempts
        == 8
    )
    assert (
        next(
            policy for definition, policy in policies if definition is download_generation_activity
        ).maximum_attempts
        == 8
    )


@pytest.mark.asyncio
async def test_workflow_imports_in_temporal_sandbox() -> None:
    SandboxedWorkflowRunner().prepare_workflow(workflow._Definition.must_from_class(DramaWorkflow))


@pytest.mark.asyncio
async def test_runtime_id_not_compiled_graph_id(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def execute_activity(definition: object, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        if definition is set_run_state_activity:
            return resolved(None)
        run_id, item, attempt, *tail = kwargs["args"]
        if definition is submit_generation_activity:
            seen.append(run_id)
            return resolved(
                SubmitResult(
                    state=RunState.RUNNING, attempt=attempt, provider_task_id=f"task-{run_id}"
                )
            )
        if definition is watch_generation_activity:
            return resolved(
                WatchResult(
                    attempt=attempt,
                    provider_task_id=tail[0],
                    task_state=ProviderTaskState.SUCCEEDED,
                )
            )
        return resolved(DurableResult(state=RunState.SUCCEEDED, path=item.id, attempts=attempt))

    monkeypatch.setattr("sdc.workflow.workflow.execute_activity", execute_activity)
    graph = JobGraph(id="stable_graph", jobs=(job("stable_job"),))
    await DramaWorkflow().run("run_one", graph)
    await DramaWorkflow().run("run_two", graph)
    assert seen == ["run_one", "run_two"]


@pytest.mark.asyncio
async def test_stop_2_blocks_dependent_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    submissions: list[tuple[str, int]] = []
    states: list[RunState] = []

    def execute_activity(definition: object, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        if definition is set_run_state_activity:
            states.append(kwargs["args"][1])
            return resolved(None)
        run_id, item, attempt, *tail = kwargs["args"]
        if definition is submit_generation_activity:
            submissions.append((item.id, attempt))
            return resolved(
                SubmitResult(
                    state=RunState.RUNNING, attempt=attempt, provider_task_id=f"task-{attempt}"
                )
            )
        assert definition is watch_generation_activity
        return resolved(
            WatchResult(
                attempt=attempt, provider_task_id=tail[0], task_state=ProviderTaskState.FAILED
            )
        )

    monkeypatch.setattr("sdc.workflow.workflow.execute_activity", execute_activity)
    parent = job("parent")
    child = job("child", (parent.id,))
    outputs = await DramaWorkflow().run("run", JobGraph(id="graph", jobs=(parent, child)))
    assert outputs == [DurableResult(state=RunState.STOP_2, path=None, attempts=2)]
    assert submissions == [("parent", 1), ("parent", 2)]
    assert states == [RunState.RUNNING, RunState.STOP_2]
