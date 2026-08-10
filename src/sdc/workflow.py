"""Deterministic Temporal orchestration for durable asynchronous provider tasks."""

import asyncio
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from sdc.contracts import (
    CanaryExecution,
    GenerationJob,
    JobGraph,
    ProviderRequest,
    ProviderTaskState,
    RunState,
)
from sdc.payloads import DurableResult, SubmitResult, WatchResult


@activity.defn(name="submit_generation")
async def submit_generation_activity(
    run_id: str,
    job: GenerationJob,
    attempt: int,
    frozen_request: ProviderRequest | None = None,
) -> SubmitResult:
    raise RuntimeError(f"submit activity {run_id}/{job.id}/{attempt} was not replaced")


@activity.defn(name="watch_generation")
async def watch_generation_activity(
    run_id: str, job: GenerationJob, attempt: int, provider_task_id: str
) -> WatchResult:
    raise RuntimeError(f"watch activity {run_id}/{job.id}/{provider_task_id} was not replaced")


@activity.defn(name="download_generation")
async def download_generation_activity(
    run_id: str, job: GenerationJob, attempt: int, provider_task_id: str
) -> DurableResult:
    raise RuntimeError(f"download activity {run_id}/{job.id}/{provider_task_id} was not replaced")


# Kept as an activity signature for BUILD-002 replay/integration compatibility only.
@activity.defn(name="generate")
async def generate_activity(run_id: str, job: GenerationJob) -> DurableResult:
    raise RuntimeError(f"activity {run_id}/{job.id} was not replaced by a worker adapter")


@activity.defn(name="set_run_state")
async def set_run_state_activity(run_id: str, state: RunState) -> None:
    raise RuntimeError(
        f"state activity {run_id}/{state.value} was not replaced by a worker adapter"
    )


@workflow.defn
class DramaWorkflow:
    async def _set_run_state(self, run_id: str, state: RunState) -> None:
        await workflow.execute_activity(
            set_run_state_activity,
            args=[run_id, state],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )

    async def _generate(
        self, run_id: str, job: GenerationJob, frozen_request: ProviderRequest | None = None
    ) -> DurableResult:
        attempts = (1,) if frozen_request is not None else range(1, job.max_attempts + 1)
        for attempt in attempts:
            # This is the only activity that may create a paid task. Never let Temporal redeliver
            # it automatically after an ambiguous outcome.
            submit_args: list[object] = [run_id, job, attempt]
            if frozen_request is not None:
                submit_args.append(frozen_request)
            submitted = await workflow.execute_activity(
                submit_generation_activity,
                args=submit_args,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            if submitted.state is RunState.HUMAN_GATE or not submitted.provider_task_id:
                return DurableResult(state=RunState.HUMAN_GATE, path=None, attempts=attempt)
            task_id = submitted.provider_task_id
            while True:
                # Technical retries address only the persisted task id and never reserve an Attempt.
                watched = await workflow.execute_activity(
                    watch_generation_activity,
                    args=[run_id, job, attempt, task_id],
                    start_to_close_timeout=timedelta(minutes=2),
                    heartbeat_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(
                        maximum_attempts=8,
                        initial_interval=timedelta(seconds=1),
                        maximum_interval=timedelta(seconds=30),
                    ),
                )
                if watched.task_state in {ProviderTaskState.QUEUED, ProviderTaskState.RUNNING}:
                    await workflow.sleep(timedelta(seconds=2))
                    continue
                if watched.task_state is ProviderTaskState.SUCCEEDED:
                    return await workflow.execute_activity(
                        download_generation_activity,
                        args=[run_id, job, attempt, task_id],
                        start_to_close_timeout=timedelta(minutes=15),
                        heartbeat_timeout=timedelta(seconds=30),
                        retry_policy=RetryPolicy(
                            maximum_attempts=8,
                            initial_interval=timedelta(seconds=1),
                            maximum_interval=timedelta(seconds=30),
                        ),
                    )
                if watched.task_state in {ProviderTaskState.FAILED, ProviderTaskState.EXPIRED}:
                    if frozen_request is not None:
                        return DurableResult(state=RunState.HUMAN_GATE, path=None, attempts=attempt)
                    break
                return DurableResult(state=RunState.HUMAN_GATE, path=None, attempts=attempt)
        if frozen_request is not None:
            return DurableResult(state=RunState.HUMAN_GATE, path=None, attempts=1)
        return DurableResult(state=RunState.STOP_2, path=None, attempts=job.max_attempts)

    @workflow.run
    async def run(
        self,
        run_id: str,
        graph: JobGraph,
        canary_request: ProviderRequest | None = None,
    ) -> list[DurableResult]:
        if canary_request is not None:
            CanaryExecution(run_id=run_id, graph=graph, request=canary_request)
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
                    *(self._generate(run_id, job, canary_request) for job in ready)
                )
                outputs.extend(batch)
                terminal = next(
                    (
                        item.state
                        for item in batch
                        if item.state in {RunState.STOP_2, RunState.HUMAN_GATE}
                    ),
                    None,
                )
                if terminal is not None:
                    await self._set_run_state(run_id, terminal)
                    return outputs
                done.update(j.id for j in ready)
                for job in ready:
                    del pending[job.id]
        except Exception:
            await self._set_run_state(run_id, RunState.FAILED)
            raise
        await self._set_run_state(run_id, RunState.SUCCEEDED)
        return outputs
