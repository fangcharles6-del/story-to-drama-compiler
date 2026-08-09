"""Temporal production orchestration skeleton using dependency-aware parallel batches."""

import asyncio
from datetime import timedelta

from temporalio import activity, workflow

from sdc.contracts import GenerationJob, JobGraph


@activity.defn
async def generate_activity(job: GenerationJob) -> str:
    """Gateway integration seam; workers inject the concrete provider implementation."""
    return job.id


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
                        job,
                        start_to_close_timeout=timedelta(minutes=15),
                        retry_policy=None,
                    )
                    for job in ready
                )
            )
            outputs.extend(batch)
            done.update(j.id for j in ready)
            for job in ready:
                del pending[job.id]
        return outputs
