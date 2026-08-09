from collections.abc import Coroutine
from typing import Any

import pytest
from temporalio.common import RetryPolicy

from sdc.contracts import GenerationJob, JobGraph, RunState
from sdc.payloads import DurableResult
from sdc.workflow import (
    DramaWorkflow,
    generate_activity,
    set_run_state_activity,
)


async def resolved(value: Any) -> Any:
    return value


@pytest.mark.asyncio
async def test_temporal_activity_has_single_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    policies: list[RetryPolicy] = []
    states: list[RunState] = []

    def execute_activity(activity_def: object, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        policies.append(kwargs["retry_policy"])
        if activity_def is set_run_state_activity:
            states.append(kwargs["args"][1])
            return resolved(None)
        _, item = kwargs["args"]
        return resolved(DurableResult(state=RunState.SUCCEEDED, path=item.id, attempts=1))

    monkeypatch.setattr("sdc.workflow.workflow.execute_activity", execute_activity)
    job = GenerationJob(
        id="job_a",
        shot_id="shot_a",
        prompt="prompt",
        duration_ms=1000,
        idempotency_key="generate_a",
    )
    outputs = await DramaWorkflow().run("run_a", JobGraph(id="graph_a", jobs=(job,)))
    assert outputs == [DurableResult(state=RunState.SUCCEEDED, path="job_a", attempts=1)]
    assert states == [RunState.RUNNING, RunState.SUCCEEDED]
    assert len(policies) == 3
    assert all(policy.maximum_attempts == 1 for policy in policies)


@pytest.mark.asyncio
async def test_runtime_id_not_compiled_graph_id(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def execute_activity(activity_def: object, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        if activity_def is set_run_state_activity:
            return resolved(None)
        run_id, item = kwargs["args"]
        seen.append(run_id)
        return resolved(DurableResult(state=RunState.SUCCEEDED, path=item.id, attempts=1))

    monkeypatch.setattr("sdc.workflow.workflow.execute_activity", execute_activity)
    item = GenerationJob(
        id="stable_job",
        shot_id="stable_shot",
        prompt="p",
        duration_ms=1,
        idempotency_key="stable_key",
    )
    graph = JobGraph(id="stable_graph", jobs=(item,))
    await DramaWorkflow().run("run_one", graph)
    await DramaWorkflow().run("run_two", graph)
    assert seen == ["run_one", "run_two"]


@pytest.mark.asyncio
async def test_stop_2_blocks_dependent_jobs_and_persists_gate_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated: list[str] = []
    states: list[RunState] = []

    def execute_activity(activity_def: object, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        if activity_def is set_run_state_activity:
            states.append(kwargs["args"][1])
            return resolved(None)
        _, item = kwargs["args"]
        generated.append(item.id)
        state = RunState.STOP_2 if item.id == "job_parent" else RunState.SUCCEEDED
        return resolved(DurableResult(state=state, path=None, attempts=2))

    monkeypatch.setattr("sdc.workflow.workflow.execute_activity", execute_activity)
    parent = GenerationJob(
        id="job_parent",
        shot_id="shot_parent",
        prompt="parent",
        duration_ms=1,
        idempotency_key="generate_parent",
    )
    child = GenerationJob(
        id="job_child",
        shot_id="shot_child",
        prompt="child",
        duration_ms=1,
        depends_on=(parent.id,),
        idempotency_key="generate_child",
    )

    outputs = await DramaWorkflow().run(
        "run_stop_2", JobGraph(id="graph_stop_2", jobs=(parent, child))
    )

    assert generated == [parent.id]
    assert outputs == [DurableResult(state=RunState.STOP_2, path=None, attempts=2)]
    assert states == [RunState.RUNNING, RunState.STOP_2]
