from collections.abc import Coroutine
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from temporalio.common import RetryPolicy

from sdc.canary_rehearsal import (
    TASK_QUEUE,
    build_rehearsal_activities,
    build_rehearsal_inputs,
)
from sdc.contracts import ProviderTaskState, RunState
from sdc.payloads import DurableResult, SubmitResult, WatchResult
from sdc.provider import FakeProvider
from sdc.workflow import (
    FakeCanaryRehearsalWorkflow,
    download_generation_activity,
    set_run_state_activity,
    submit_canary_generation_activity,
    watch_generation_activity,
)


def test_compose_exposes_only_loopback_ports() -> None:
    compose = Path("docker-compose.yml").read_text()
    assert '"127.0.0.1:5432:5432"' in compose
    assert '"127.0.0.1:7233:7233"' in compose
    assert '"5432:5432"' not in compose.replace('"127.0.0.1:5432:5432"', "")
    assert '"7233:7233"' not in compose.replace('"127.0.0.1:7233:7233"', "")
    assert "0.0.0.0" not in compose


def test_rehearsal_inputs_and_worker_boundary_are_fixed(tmp_path: Path) -> None:
    graph, request = build_rehearsal_inputs("fixed-rehearsal-run")
    activities, provider = build_rehearsal_activities(cast(Any, object()), tmp_path)
    assert TASK_QUEUE == "sdc-canary-001-v01-rehearsal"
    assert len(graph.jobs) == 1
    assert request.run_id == "fixed-rehearsal-run"
    assert request.job_id == graph.jobs[0].id
    assert request.attempt == 1
    assert request.provider == "fake" and request.model == "fake-v1"
    assert request.aspect_ratio == "9:16" and request.resolution == "1080p"
    assert request.duration_ms == 4000 and request.generate_audio is False
    assert request.input_materials == ()
    assert isinstance(provider, FakeProvider)
    assert (provider.width, provider.height, provider.fps) == (1080, 1920, 24)
    assert activities.profile.max_in_flight == 1
    assert activities.live_guard is None


@pytest.mark.asyncio
async def test_fake_provider_rehearsal_makes_no_http_post(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def forbidden_post(*_: object, **__: object) -> None:
        raise AssertionError("FakeProvider rehearsal must not make a Provider HTTP POST")

    monkeypatch.setattr(httpx.AsyncClient, "post", forbidden_post)
    _, request = build_rehearsal_inputs("zero-http-run")
    provider = FakeProvider(width=1080, height=1920, fps=24)
    submission = await provider.submit(request)
    snapshot = await provider.inspect(submission.provider_task_id)
    assert snapshot.state is ProviderTaskState.SUCCEEDED
    assert provider.submit_calls == 1


def test_rehearsal_module_does_not_load_ark_or_key_configuration() -> None:
    source = Path("src/sdc/canary_rehearsal.py").read_text()
    assert "sdc.ark_provider" not in source
    assert "SDC_ARK_API_KEY" not in source
    assert "LiveAuthorization(" not in source
    assert "build_live_authorization" not in source


async def resolved(value: Any) -> Any:
    return value


@pytest.mark.parametrize(
    "failed_definition",
    [
        pytest.param(submit_canary_generation_activity, id="submit"),
        pytest.param(watch_generation_activity, id="watch"),
        pytest.param(download_generation_activity, id="download"),
    ],
)
@pytest.mark.asyncio
async def test_rehearsal_activity_failure_enters_human_gate_without_attempt_two(
    monkeypatch: pytest.MonkeyPatch,
    failed_definition: object,
) -> None:
    graph, request = build_rehearsal_inputs("failure-run")
    activity_calls: list[tuple[object, int]] = []
    policies: list[RetryPolicy] = []
    states: list[RunState] = []

    async def rejected_activity() -> Any:
        raise RuntimeError("simulated rehearsal activity failure")

    def execute_activity(definition: object, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        policies.append(kwargs["retry_policy"])
        if definition is set_run_state_activity:
            states.append(kwargs["args"][1])
            return resolved(None)
        _run_id, item, attempt, *tail = kwargs["args"]
        activity_calls.append((definition, attempt))
        if definition is failed_definition:
            return rejected_activity()
        if definition is submit_canary_generation_activity:
            return resolved(
                SubmitResult(
                    state=RunState.RUNNING,
                    attempt=attempt,
                    provider_task_id="fake-task",
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
    outputs = await FakeCanaryRehearsalWorkflow().run("failure-run", graph, request)
    assert outputs == [DurableResult(state=RunState.HUMAN_GATE, path=None, attempts=1)]
    assert {attempt for _definition, attempt in activity_calls} == {1}
    assert activity_calls.count((submit_canary_generation_activity, 1)) == 1
    assert all(policy.maximum_attempts == 1 for policy in policies)
    assert states == [RunState.RUNNING, RunState.HUMAN_GATE]


def test_windows_runbook_sets_dedicated_queue_and_concurrency_one() -> None:
    script = Path("scripts/Invoke-SdcCanaryRehearsal.ps1").read_text()
    runbook = Path("docs/runbooks/SDC-CANARY-001-LOCAL-REHEARSAL.md").read_text()
    assert '$env:SDC_PROVIDER = "fake"' in script
    assert '$env:SDC_TASK_QUEUE = "sdc-canary-001-v01-rehearsal"' in script
    assert '$env:SDC_ARK_MAX_IN_FLIGHT = "1"' in script
    assert "Invoke-SdcCanaryRehearsal.ps1" in runbook
    assert "-MigrationRoundTrip" in runbook
