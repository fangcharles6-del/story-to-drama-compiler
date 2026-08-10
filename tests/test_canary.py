import socket
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from sdc.canary import (
    LiveGateError,
    LiveSubmissionGuard,
    build_canary_plan,
    contract_sha256,
    main,
)
from sdc.contracts import (
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
        worst_case_units=Decimal("100000"),
        worst_case_cost_cny=Decimal("0.10"),
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


def test_plan_is_not_authorization_and_allows_zero_posts() -> None:
    plan = build_canary_plan(
        capability(), pricing(), frozen_request(), Decimal("0.20"), now=NOW
    )
    assert plan.state == "NOT_AUTHORIZED"
    assert plan.posts_allowed == 0
    assert plan.worst_case_cost_cny == Decimal("0.10")


@pytest.mark.parametrize(
    ("request", "cost", "failure_class"),
    [
        (frozen_request(attempt=2), Decimal("0.20"), ProviderFailureClass.LIVE_NOT_AUTHORIZED),
        (frozen_request(duration_ms=15001), Decimal("0.20"), ProviderFailureClass.CAPABILITY_DRIFT),
        (frozen_request(), Decimal("0.09"), ProviderFailureClass.COST_LIMIT),
    ],
)
def test_plan_fails_closed_before_live_submission(
    request: ProviderRequest, cost: Decimal, failure_class: ProviderFailureClass
) -> None:
    with pytest.raises(LiveGateError) as caught:
        build_canary_plan(capability(), pricing(), request, cost, now=NOW)
    assert caught.value.failure_class is failure_class


def test_authorization_is_bound_to_exact_snapshots_and_request() -> None:
    request = frozen_request()
    guard = LiveSubmissionGuard(capability(), pricing(), authorization(request))
    guard.validate(request, now=NOW)
    with pytest.raises(LiveGateError, match="fingerprint"):
        guard.validate(frozen_request(duration_ms=5000), now=NOW)


def test_cli_dry_run_performs_no_network_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_: object, **__: object) -> None:
        raise AssertionError("dry-run must not touch the network")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    request = frozen_request()
    files = {
        "capability": capability(),
        "pricing": pricing(),
        "request": request,
    }
    paths: dict[str, Path] = {}
    for name, value in files.items():
        paths[name] = tmp_path / f"{name}.json"
        paths[name].write_text(value.model_dump_json())
    output = tmp_path / "plan.json"
    assert (
        main(
            [
                "--capability",
                str(paths["capability"]),
                "--pricing",
                str(paths["pricing"]),
                "--request",
                str(paths["request"]),
                "--max-cost-cny",
                "0.20",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert '"state": "NOT_AUTHORIZED"' in output.read_text()
    assert '"posts_allowed": 0' in output.read_text()
