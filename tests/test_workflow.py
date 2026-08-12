from collections.abc import Coroutine
from typing import Any

import pytest
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from sdc.canary import freeze_canary_execution
from sdc.contracts import GenerationJob, JobGraph, ProviderTaskState, RunState
from sdc.payloads import DurableResult, SubmitResult, WatchResult
from sdc.workflow import (
    CanaryWorkflow,
    DramaWorkflow,
    FakeCanaryRehearsalWorkflow,
    download_generation_activity,
    set_run_state_activity,
    submit_canary_generation_activity,
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
    SandboxedWorkflowRunner().prepare_workflow(workflow._Definition.must_from_class(CanaryWorkflow))
    SandboxedWorkflowRunner().prepare_workflow(
        workflow._Definition.must_from_class(FakeCanaryRehearsalWorkflow)
    )


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


@pytest.mark.asyncio
async def test_canary_workflow_passes_frozen_request_and_never_attempts_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canary_job = job("canary-job").model_copy(update={"duration_ms": 4000})
    graph = JobGraph(id="canary-graph", jobs=(canary_job,))
    execution = freeze_canary_execution("canary-run", graph)
    submissions: list[tuple[int, object]] = []
    states: list[RunState] = []

    def execute_activity(definition: object, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        if definition is set_run_state_activity:
            states.append(kwargs["args"][1])
            return resolved(None)
        _run_id, _item, attempt, *tail = kwargs["args"]
        if definition is submit_canary_generation_activity:
            submissions.append((attempt, tail[0]))
            return resolved(
                SubmitResult(
                    state=RunState.RUNNING,
                    attempt=attempt,
                    provider_task_id="task-canary",
                )
            )
        assert definition is watch_generation_activity
        return resolved(
            WatchResult(
                attempt=attempt,
                provider_task_id=tail[0],
                task_state=ProviderTaskState.FAILED,
            )
        )

    monkeypatch.setattr("sdc.workflow.workflow.execute_activity", execute_activity)
    outputs = await CanaryWorkflow().run(execution)
    assert outputs == [DurableResult(state=RunState.HUMAN_GATE, path=None, attempts=1)]
    assert submissions == [(1, execution.request)]
    assert states == [RunState.RUNNING, RunState.HUMAN_GATE]


@pytest.mark.parametrize(
    "failed_definition",
    [
        pytest.param(submit_canary_generation_activity, id="submit"),
        pytest.param(watch_generation_activity, id="watch"),
        pytest.param(download_generation_activity, id="download"),
    ],
)
@pytest.mark.asyncio
async def test_canary_activity_exceptions_enter_human_gate_without_resubmission(
    monkeypatch: pytest.MonkeyPatch,
    failed_definition: object,
) -> None:
    canary_job = job("canary-job").model_copy(update={"duration_ms": 4000})
    execution = freeze_canary_execution(
        "canary-run",
        JobGraph(id="canary-graph", jobs=(canary_job,)),
    )
    provider_calls: list[tuple[object, int]] = []
    states: list[RunState] = []

    async def rejected_activity() -> Any:
        raise RuntimeError("simulated activity failure")

    def execute_activity(definition: object, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        if definition is set_run_state_activity:
            states.append(kwargs["args"][1])
            return resolved(None)
        _run_id, item, attempt, *tail = kwargs["args"]
        provider_calls.append((definition, attempt))
        if definition is failed_definition:
            return rejected_activity()
        if definition is submit_canary_generation_activity:
            return resolved(
                SubmitResult(
                    state=RunState.RUNNING,
                    attempt=attempt,
                    provider_task_id="task-canary",
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
    outputs = await CanaryWorkflow().run(execution)

    assert outputs == [DurableResult(state=RunState.HUMAN_GATE, path=None, attempts=1)]
    assert provider_calls.count((submit_canary_generation_activity, 1)) == 1
    assert {attempt for _definition, attempt in provider_calls} == {1}
    assert all(
        definition is not submit_generation_activity
        for definition, _attempt in provider_calls
    )
    assert states == [RunState.RUNNING, RunState.HUMAN_GATE]
