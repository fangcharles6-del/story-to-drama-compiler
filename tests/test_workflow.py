from collections.abc import Coroutine
from typing import Any

import pytest
from temporalio.common import RetryPolicy

from sdc.contracts import GenerationJob, JobGraph
from sdc.workflow import DramaWorkflow


@pytest.mark.asyncio
async def test_temporal_activity_has_single_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    policies: list[RetryPolicy] = []

    async def result(job_id: str) -> str:
        return job_id

    def execute_activity(_activity: object, **kwargs: Any) -> Coroutine[Any, Any, str]:
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
    outputs = await DramaWorkflow().run(JobGraph(id="graph_a", jobs=(job,)))
    assert outputs == ["job_a"]
    assert len(policies) == 1
    assert policies[0].maximum_attempts == 1
