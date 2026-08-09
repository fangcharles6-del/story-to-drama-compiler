from collections.abc import Coroutine
from typing import Any

import pytest
from temporalio.common import RetryPolicy

from sdc.contracts import GenerationJob, JobGraph, RunState
from sdc.payloads import DurableResult
from sdc.workflow import DramaWorkflow


@pytest.mark.asyncio
async def test_temporal_activity_has_single_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    policies: list[RetryPolicy] = []

    async def result(job_id: str) -> DurableResult:
        return DurableResult(state=RunState.SUCCEEDED, path=job_id, attempts=1)

    def execute_activity(_activity: object, **kwargs: Any) -> Coroutine[Any, Any, DurableResult]:
        policies.append(kwargs["retry_policy"])
        _, job = kwargs["args"]
        return result(job.id)

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
    assert len(policies) == 1
    assert policies[0].maximum_attempts == 1


@pytest.mark.asyncio
async def test_runtime_id_not_compiled_graph_id(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    async def result(job_id: str) -> DurableResult:
        return DurableResult(state=RunState.SUCCEEDED, path=job_id, attempts=1)

    def execute_activity(_activity: object, **kwargs: Any) -> Coroutine[Any, Any, DurableResult]:
        run_id, job = kwargs["args"]
        seen.append(run_id)
        return result(job.id)

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
