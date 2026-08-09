"""Temporal production orchestration using dependency-aware parallel batches."""

import asyncio
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from sdc.contracts import GenerationJob, JobGraph, RunState
from sdc.payloads import DurableResult


@activity.defn(name="generate")
async def generate_activity(run_id: str, job: GenerationJob) -> DurableResult:
    """Workflow signature only; workers register ``RuntimeActivities.generate``."""
    raise RuntimeError(f"activity {run_id}/{job.id} was not replaced by a worker adapter")


@activity.defn(name="set_run_state")
async def set_run_state_activity(run_id: str, state: RunState) -> None:
    """Workflow signature only; workers register ``RuntimeActivities.set_run_state``."""
    raise RuntimeError(f"state activity {run_id}/{state.value} was not replaced by a worker adapter")


@workflow.defn
class DramaWorkflow:
    async def _set_run_state(self, run_id: str, state: RunState) -> None:
        await workflow.execute_activity(
            set_run_state_activity,
            args=[run_id, state],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )

    @workflow.run
    async def run(self, run_id: str, graph: JobGraph) -> list[DurableResult]:
        await self._set_run_state(run_id, RunState.RUNNING)
        pending = {job.id: job for job in graph.jobs}
        done: set[str] = set()
        outputs: list[DurableResult] = []
        try:
            while pending:
                ready = sorted(
                    (j for j in pending.values() if set(j.depends_on) <= done), key=lambda j: j.id
                )
                if not ready:
                    raise ValueError("job graph contains a cycle or unknown dependency")
                batch = await asyncio.gather(
                    *(
                        workflow.execute_activity(
                            generate_activity,
                            args=[run_id, job],
                            start_to_close_timeout=timedelta(minutes=15),
                            # The gateway owns the two attempts and STOP-2. Temporal must not
                            # silently turn them into a third generation attempt.
                            retry_policy=RetryPolicy(maximum_attempts=1),
                        )
                        for job in ready
                    )
                )
                outputs.extend(batch)
                if any(item.state is RunState.STOP_2 for item in batch):
                    # STOP-2 is terminal for automatic execution. Dependent jobs remain
                    # undispatched until an explicit human decision starts a new action.
                    await self._set_run_state(run_id, RunState.STOP_2)
                    return outputs
                done.update(j.id for j in ready)
                for job in ready:
                    del pending[job.id]
        except Exception:
            await self._set_run_state(run_id, RunState.FAILED)
            raise
        await self._set_run_state(run_id, RunState.SUCCEEDED)
        return outputs
