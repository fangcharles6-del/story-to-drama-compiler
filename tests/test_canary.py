import socket
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from sdc.canary import (
    LiveGateError,
    LiveSubmissionGuard,
    build_canary_plan,
    build_live_authorization,
    contract_sha256,
    freeze_canary_execution,
    main,
    minimum_canary_worst_case_units,
)
from sdc.canary_authorize import main as authorize_main
from sdc.contracts import (
    GenerationJob,
    JobGraph,
    LiveAuthorization,
    PricingInputMode,
    ProviderCapabilitySnapshot,
    ProviderFailureClass,
    ProviderPricingSnapshot,
    ProviderRequest,
    SnapshotStatus,
)
from sdc.provider import ARK_MODEL, request_fingerprint

NOW = datetime(2026, 8, 10, tzinfo=UTC)
VALID_UNTIL = datetime(2026, 9, 10, tzinfo=UTC)


def frozen_request(*, attempt: int = 1, duration_ms: int = 4000) -> ProviderRequest:
    value = ProviderRequest(
        run_id="canary-run",
        job_id="canary-job",
        attempt=attempt,
        provider="volcengine_ark",
        model=ARK_MODEL,
        prompt="one safe canary",
        duration_ms=duration_ms,
        aspect_ratio="9:16",
        resolution="1080p",
        generate_audio=False,
        request_fingerprint="0" * 64,
    )
    return value.model_copy(update={"request_fingerprint": request_fingerprint(value)})


def capability() -> ProviderCapabilitySnapshot:
    return ProviderCapabilitySnapshot(
        snapshot_revision="2026-08-10.1",
        status=SnapshotStatus.CURRENT,
        provider="volcengine_ark",
        model=ARK_MODEL,
        aspect_ratios=("9:16",),
        resolutions=("1080p",),
        fps=24,
        min_duration_ms=4000,
        max_duration_ms=15000,
        source_url="https://www.volcengine.com/docs/82379/1330310",
        source_updated_at=NOW,
        captured_at=NOW,
        valid_until=VALID_UNTIL,
        evidence_sha256="a" * 64,
    )


def pricing() -> ProviderPricingSnapshot:
    return ProviderPricingSnapshot(
        snapshot_revision="2026-08-10.1",
        status=SnapshotStatus.CURRENT,
        provider="volcengine_ark",
        model=ARK_MODEL,
        resolution="1080p",
        input_mode=PricingInputMode.WITHOUT_VIDEO,
        billing_unit="provider-token",
        unit_price_cny=Decimal("0.000001"),
        worst_case_units=Decimal("196425"),
        worst_case_cost_cny=Decimal("0.196425"),
        source_url="https://docs.volcengine.com/docs/82379/1544106",
        source_updated_at=NOW,
        captured_at=NOW,
        valid_until=VALID_UNTIL,
        evidence_sha256="b" * 64,
    )


def authorization(request: ProviderRequest) -> LiveAuthorization:
    return LiveAuthorization(
        authorization_id="SDC-CANARY-001",
        request_fingerprint=request.request_fingerprint,
        capability_snapshot_sha256=contract_sha256(capability()),
        pricing_snapshot_sha256=contract_sha256(pricing()),
        max_cost_cny=Decimal("0.20"),
        expires_at=VALID_UNTIL,
        nonce="c" * 64,
    )


def graph(*jobs: GenerationJob) -> JobGraph:
    values = jobs or (
        GenerationJob(
            id="canary-job",
            shot_id="canary-shot",
            prompt="one safe canary",
            duration_ms=4000,
            idempotency_key="canary-generate",
        ),
    )
    return JobGraph(id="canary-graph", jobs=values)


def test_plan_is_not_authorization_and_allows_zero_posts() -> None:
    plan = build_canary_plan(capability(), pricing(), frozen_request(), Decimal("0.20"), now=NOW)
    assert plan.state == "NOT_AUTHORIZED"
    assert plan.posts_allowed == 0
    assert plan.worst_case_cost_cny == Decimal("0.196425")


def test_canary_cost_floor_includes_one_provider_terminal_frame() -> None:
    request = frozen_request()
    assert minimum_canary_worst_case_units(capability(), request) == Decimal("196425")

    nominal_only = pricing().model_copy(
        update={
            "unit_price_cny": Decimal("0.000051"),
            "worst_case_units": Decimal("194400"),
            "worst_case_cost_cny": Decimal("9.9144"),
        }
    )
    with pytest.raises(LiveGateError, match="one-frame canary billing allowance"):
        build_canary_plan(capability(), nominal_only, request, Decimal("12"), now=NOW)

    calibrated = nominal_only.model_copy(
        update={
            "worst_case_units": Decimal("196425"),
            "worst_case_cost_cny": Decimal("10.017675"),
        }
    )
    plan = build_canary_plan(capability(), calibrated, request, Decimal("10.017675"), now=NOW)
    assert plan.worst_case_cost_cny == Decimal("10.017675")
    with pytest.raises(LiveGateError, match="approved ceiling"):
        build_canary_plan(capability(), calibrated, request, Decimal("10.017674"), now=NOW)

    underpriced = calibrated.model_copy(update={"worst_case_cost_cny": Decimal("10.017674")})
    with pytest.raises(LiveGateError, match="calculated worst-case cost"):
        build_canary_plan(capability(), underpriced, request, Decimal("12"), now=NOW)


def test_canary_rejects_capability_fps_drift() -> None:
    with pytest.raises(LiveGateError, match="24 fps"):
        build_canary_plan(
            capability().model_copy(update={"fps": 25}),
            pricing(),
            frozen_request(),
            Decimal("0.20"),
            now=NOW,
        )


def test_exact_execution_freezes_single_job_and_request_fingerprint() -> None:
    execution = freeze_canary_execution("canary-run", graph())
    assert execution.run_id == execution.request.run_id == "canary-run"
    assert execution.graph.jobs[0].id == execution.request.job_id
    assert execution.request.duration_ms == 4000
    assert execution.request.generate_audio is False
    assert execution.request.input_materials == ()
    assert request_fingerprint(execution.request) == execution.request.request_fingerprint


def test_exact_execution_rejects_multiple_jobs_before_workflow() -> None:
    extra = graph().jobs[0].model_copy(update={"id": "second-job"})
    with pytest.raises(LiveGateError, match="exactly one Job"):
        freeze_canary_execution("canary-run", graph(graph().jobs[0], extra))


@pytest.mark.parametrize(
    ("provider_request", "cost", "failure_class"),
    [
        (frozen_request(attempt=2), Decimal("0.20"), ProviderFailureClass.LIVE_NOT_AUTHORIZED),
        (frozen_request(duration_ms=15001), Decimal("0.20"), ProviderFailureClass.CAPABILITY_DRIFT),
        (frozen_request(), Decimal("0.09"), ProviderFailureClass.COST_LIMIT),
        (frozen_request(), Decimal("15.01"), ProviderFailureClass.COST_LIMIT),
    ],
)
def test_plan_fails_closed_before_live_submission(
    provider_request: ProviderRequest, cost: Decimal, failure_class: ProviderFailureClass
) -> None:
    with pytest.raises(LiveGateError) as caught:
        build_canary_plan(capability(), pricing(), provider_request, cost, now=NOW)
    assert caught.value.failure_class is failure_class


def test_authorization_is_bound_to_exact_snapshots_and_request() -> None:
    request = frozen_request()
    guard = LiveSubmissionGuard(capability(), pricing(), authorization(request))
    guard.validate(request, now=NOW)
    with pytest.raises(LiveGateError, match="fingerprint"):
        guard.validate(request.model_copy(update={"prompt": "different"}), now=NOW)


def test_legacy_authorization_generation_is_retired() -> None:
    plan = build_canary_plan(capability(), pricing(), frozen_request(), Decimal("15"), now=NOW)
    execution = freeze_canary_execution("canary-run", graph())
    with pytest.raises(LiveGateError, match="legacy authorization generation is retired"):
        build_live_authorization(
            plan,
            execution,
            authorization_id="SDC-CANARY-001",
            max_cost_cny=Decimal("15"),
            expires_at=VALID_UNTIL,
            nonce="d" * 64,
        )


def test_canary_rejects_unknown_billing_unit_before_cost_arithmetic() -> None:
    with pytest.raises(LiveGateError, match="billing unit"):
        build_canary_plan(
            capability(),
            pricing().model_copy(update={"billing_unit": "unknown-unit"}),
            frozen_request(),
            Decimal("0.20"),
            now=NOW,
        )


def test_loose_snapshot_cli_is_retired_before_files_or_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_: object, **__: object) -> None:
        raise AssertionError("dry-run must not touch the network")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    output = tmp_path / "plan.json"
    with pytest.raises(LiveGateError, match="loose snapshot planning is retired"):
        main(
            [
                "--capability",
                str(tmp_path / "missing-capability.json"),
                "--pricing",
                str(tmp_path / "missing-pricing.json"),
                "--request",
                str(tmp_path / "missing-request.json"),
                "--max-cost-cny",
                "0.20",
                "--output",
                str(output),
            ]
        )
    assert not output.exists()


def test_legacy_authorizer_cli_is_disabled_before_input_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_: object, **__: object) -> None:
        raise AssertionError("canary preparation must not touch the network")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    authorization_path = tmp_path / "authorization.json"
    with pytest.raises(LiveGateError, match="authorization generation is disabled"):
        authorize_main(
            [
                "--plan",
                str(tmp_path / "missing-plan.json"),
                "--execution",
                str(tmp_path / "missing-execution.json"),
                "--authorization-id",
                "SDC-CANARY-001",
                "--max-cost-cny",
                "15",
                "--expires-at",
                VALID_UNTIL.isoformat(),
                "--nonce",
                "e" * 64,
                "--output",
                str(authorization_path),
            ]
        )
    assert not authorization_path.exists()
