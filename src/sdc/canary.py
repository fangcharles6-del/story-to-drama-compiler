"""Zero-network canary planning and fail-closed live submission authorization."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from urllib.parse import urlparse

from pydantic import BaseModel

from sdc.contracts import (
    CanaryExecution,
    CanaryPlan,
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

ARK_PROVIDER = "volcengine_ark"
CANARY_DURATION_MS = 4000
CANARY_FPS = 24
CANARY_WIDTH_PX = 1080
CANARY_HEIGHT_PX = 1920
CANARY_PROVIDER_TAIL_FRAME_ALLOWANCE = 1
ARK_PROVIDER_TOKEN_PIXEL_DIVISOR = Decimal(1024)
CANARY_COST_HARD_LIMIT_CNY = Decimal("15")


class LiveGateError(RuntimeError):
    def __init__(self, failure_class: ProviderFailureClass, message: str) -> None:
        super().__init__(message)
        self.failure_class = failure_class


def contract_sha256(value: BaseModel) -> str:
    payload = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise LiveGateError(ProviderFailureClass.CONFIGURATION, f"{field} must include a timezone")
    return value


def _validate_request(request: ProviderRequest) -> None:
    if request.provider != ARK_PROVIDER or request.model != ARK_MODEL:
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT,
            "canary request must use the pinned Volcengine Ark Seedance 2.0 model",
        )
    if request.attempt != 1:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "live canary permits creative Attempt 1 only",
        )
    if (
        request.duration_ms != CANARY_DURATION_MS
        or request.aspect_ratio != "9:16"
        or request.resolution != "1080p"
    ):
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT,
            "live canary is pinned to 9:16, 1080p, and 4000 ms",
        )
    if request.generate_audio:
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT,
            "live canary requires generate_audio=false",
        )
    if request.input_materials:
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT,
            "live canary is text-only and accepts no input materials",
        )
    if request_fingerprint(request) != request.request_fingerprint:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "request fingerprint does not match the frozen request",
        )


def minimum_canary_worst_case_units(
    capability: ProviderCapabilitySnapshot, request: ProviderRequest
) -> Decimal:
    """Return the calibrated billing floor, including one provider terminal frame."""
    nominal_frames = (
        Decimal(request.duration_ms) * Decimal(capability.fps) / Decimal(1000)
    ).to_integral_value(rounding=ROUND_CEILING)
    billed_frames = nominal_frames + Decimal(CANARY_PROVIDER_TAIL_FRAME_ALLOWANCE)
    pixels_per_frame = Decimal(CANARY_WIDTH_PX * CANARY_HEIGHT_PX)
    return (billed_frames * pixels_per_frame / ARK_PROVIDER_TOKEN_PIXEL_DIVISOR).to_integral_value(
        rounding=ROUND_CEILING
    )


def validate_snapshots(
    capability: ProviderCapabilitySnapshot,
    pricing: ProviderPricingSnapshot,
    request: ProviderRequest,
    cost_ceiling_cny: Decimal,
    *,
    now: datetime | None = None,
) -> None:
    current = now or datetime.now(UTC)
    _aware(current, "current time")
    _validate_request(request)
    if cost_ceiling_cny > CANARY_COST_HARD_LIMIT_CNY:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "canary cost ceiling exceeds the CNY 15 hard limit",
        )
    for source in (capability.source_url, pricing.source_url):
        parsed = urlparse(source)
        if parsed.scheme != "https" or parsed.hostname not in {
            "docs.volcengine.com",
            "www.volcengine.com",
        }:
            raise LiveGateError(
                ProviderFailureClass.CONFIGURATION,
                "snapshot evidence must reference an official Volcengine HTTPS document",
            )
    if capability.status is not SnapshotStatus.CURRENT:
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT, "capability snapshot is not CURRENT"
        )
    if pricing.status is not SnapshotStatus.CURRENT:
        raise LiveGateError(ProviderFailureClass.COST_LIMIT, "pricing snapshot is not CURRENT")
    if current > _aware(capability.valid_until, "capability valid_until"):
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT, "capability snapshot has expired"
        )
    if current > _aware(pricing.valid_until, "pricing valid_until"):
        raise LiveGateError(ProviderFailureClass.COST_LIMIT, "pricing snapshot has expired")
    if capability.provider != request.provider or capability.model != request.model:
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT, "capability snapshot profile mismatch"
        )
    if not capability.min_duration_ms <= request.duration_ms <= capability.max_duration_ms:
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT, "request duration is outside capability"
        )
    if request.aspect_ratio not in capability.aspect_ratios:
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT, "request aspect ratio is outside capability"
        )
    if request.resolution not in capability.resolutions:
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT, "request resolution is outside capability"
        )
    if (
        capability.fps != CANARY_FPS
        or capability.min_duration_ms != 4000
        or capability.max_duration_ms != 15000
    ):
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT,
            "Seedance 2.0 capability must remain 24 fps and 4000..15000 ms",
        )
    # ProviderRequest currently carries image references only, so Ark pricing remains
    # WITHOUT_VIDEO even when input_materials is non-empty.
    expected_input_mode = PricingInputMode.WITHOUT_VIDEO
    if (
        pricing.provider != request.provider
        or pricing.model != request.model
        or pricing.resolution != request.resolution
        or pricing.input_mode is not expected_input_mode
    ):
        raise LiveGateError(ProviderFailureClass.COST_LIMIT, "pricing snapshot profile mismatch")
    if pricing.billing_unit != "provider-token":
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "pricing snapshot billing unit must remain provider-token",
        )
    if pricing.worst_case_cost_cny < pricing.unit_price_cny * pricing.worst_case_units:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "pricing snapshot understates its calculated worst-case cost",
        )
    minimum_worst_case_units = minimum_canary_worst_case_units(capability, request)
    if pricing.worst_case_units < minimum_worst_case_units:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "pricing snapshot omits the one-frame canary billing allowance",
        )
    if pricing.worst_case_cost_cny < pricing.unit_price_cny * minimum_worst_case_units:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "pricing snapshot understates the frame-rounded canary cost",
        )
    if pricing.worst_case_cost_cny > cost_ceiling_cny:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT, "worst-case provider cost exceeds approved ceiling"
        )


def build_canary_plan(
    capability: ProviderCapabilitySnapshot,
    pricing: ProviderPricingSnapshot,
    request: ProviderRequest,
    cost_ceiling_cny: Decimal,
    *,
    now: datetime | None = None,
) -> CanaryPlan:
    planned_at = now or datetime.now(UTC)
    validate_snapshots(capability, pricing, request, cost_ceiling_cny, now=planned_at)
    return CanaryPlan(
        run_id=request.run_id,
        job_id=request.job_id,
        request_fingerprint=request.request_fingerprint,
        capability_snapshot_sha256=contract_sha256(capability),
        pricing_snapshot_sha256=contract_sha256(pricing),
        worst_case_cost_cny=pricing.worst_case_cost_cny,
        approved_cost_ceiling_cny=cost_ceiling_cny,
        planned_at=planned_at,
    )


def freeze_canary_execution(run_id: str, graph: JobGraph) -> CanaryExecution:
    """Freeze the exact one-Job Workflow request without network or authorization side effects."""
    if len(graph.jobs) != 1:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "canary workflow must contain exactly one Job",
        )
    job = graph.jobs[0]
    draft = ProviderRequest(
        run_id=run_id,
        job_id=job.id,
        attempt=1,
        provider=ARK_PROVIDER,
        model=ARK_MODEL,
        prompt=job.prompt,
        duration_ms=job.duration_ms,
        aspect_ratio="9:16",
        resolution="1080p",
        generate_audio=False,
        input_materials=(),
        request_fingerprint="0" * 64,
    )
    request = draft.model_copy(update={"request_fingerprint": request_fingerprint(draft)})
    try:
        return CanaryExecution(run_id=run_id, graph=graph, request=request)
    except ValueError as exc:
        raise LiveGateError(ProviderFailureClass.LIVE_NOT_AUTHORIZED, str(exc)) from exc


def build_live_authorization(
    plan: CanaryPlan,
    execution: CanaryExecution,
    *,
    authorization_id: str,
    max_cost_cny: Decimal,
    expires_at: datetime,
    nonce: str,
) -> LiveAuthorization:
    """Fail closed until an evidence-bound authorization contract is delivered."""
    del plan, execution, authorization_id, max_cost_cny, expires_at, nonce
    raise LiveGateError(
        ProviderFailureClass.LIVE_NOT_AUTHORIZED,
        "legacy authorization generation is retired; evidence-bound authorization is not delivered",
    )


class LiveSubmissionGuard:
    """Validates one separately approved POST; durable consumption belongs to RuntimeStore."""

    def __init__(
        self,
        capability: ProviderCapabilitySnapshot,
        pricing: ProviderPricingSnapshot,
        authorization: LiveAuthorization,
    ) -> None:
        self.capability = capability
        self.pricing = pricing
        self.authorization = authorization
        self.capability_sha256 = contract_sha256(capability)
        self.pricing_sha256 = contract_sha256(pricing)

    def validate(self, request: ProviderRequest, *, now: datetime | None = None) -> None:
        current = now or datetime.now(UTC)
        validate_snapshots(
            self.capability,
            self.pricing,
            request,
            self.authorization.max_cost_cny,
            now=current,
        )
        if self.authorization.max_cost_cny > CANARY_COST_HARD_LIMIT_CNY:
            raise LiveGateError(
                ProviderFailureClass.COST_LIMIT,
                "live authorization exceeds the CNY 15 hard limit",
            )
        if current > _aware(self.authorization.expires_at, "authorization expires_at"):
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED, "live authorization has expired"
            )
        if self.authorization.request_fingerprint != request.request_fingerprint:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                "live authorization does not match request fingerprint",
            )
        if self.authorization.capability_snapshot_sha256 != self.capability_sha256:
            raise LiveGateError(
                ProviderFailureClass.CAPABILITY_DRIFT,
                "live authorization capability snapshot mismatch",
            )
        if self.authorization.pricing_snapshot_sha256 != self.pricing_sha256:
            raise LiveGateError(
                ProviderFailureClass.COST_LIMIT,
                "live authorization pricing snapshot mismatch",
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Retired loose-snapshot Canary planner; use sdc.fresh_canary_plan"
    )
    parser.parse_known_args(argv)
    raise LiveGateError(
        ProviderFailureClass.LIVE_NOT_AUTHORIZED,
        "loose snapshot planning is retired; use the reviewed FRESH evidence planner",
    )


if __name__ == "__main__":
    raise SystemExit(main())
