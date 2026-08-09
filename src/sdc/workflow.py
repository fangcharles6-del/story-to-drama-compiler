"""Temporal production orchestration skeleton using dependency-aware parallel batches."""

import asyncio
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from sdc.contracts import GenerationJob, JobGraph


@activity.defn(name="generate")
async def generate_activity(run_id: str, job: GenerationJob) -> str:
    """Workflow signature only; workers register ``RuntimeActivities.generate``."""
    raise RuntimeError(f"activity {run_id}/{job.id} was not replaced by a worker adapter")


@workflow.defn
class DramaWorkflow:
    @workflow.run
    async def run(self, graph: JobGraph) -> list[str]:
        pending = {job.id: job for job in graph.jobs}
        done: set[str] = set()
        outputs: list[str] = []
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
                        args=[graph.id, job],
                        start_to_close_timeout=timedelta(minutes=15),
                        # The gateway owns the two attempts and STOP-2. Temporal must not
                        # silently turn them into a third generation attempt.
                        retry_policy=RetryPolicy(maximum_attempts=1),
                    )
                    for job in ready
                )
            )
            outputs.extend(batch)
            done.update(j.id for j in ready)
            for job in ready:
                del pending[job.id]
        return outputs
