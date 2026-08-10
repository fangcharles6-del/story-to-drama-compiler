"""Zero-network canary planning and fail-closed live submission authorization."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel

from sdc.contracts import (
    CanaryPlan,
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
        raise LiveGateError(
            ProviderFailureClass.CONFIGURATION, f"{field} must include a timezone"
        )
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
    if request.aspect_ratio != "9:16" or request.resolution != "1080p":
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT,
            "live canary is pinned to 9:16 at 1080p",
        )
    if request_fingerprint(request) != request.request_fingerprint:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "request fingerprint does not match the frozen request",
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
    if capability.min_duration_ms != 4000 or capability.max_duration_ms != 15000:
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT,
            "Seedance 2.0 output duration capability must remain 4000..15000 ms",
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
    if pricing.worst_case_cost_cny < pricing.unit_price_cny * pricing.worst_case_units:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "pricing snapshot understates its calculated worst-case cost",
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


def _load[ModelT: BaseModel](path: Path, model: type[ModelT]) -> ModelT:
    return model.model_validate_json(path.read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a zero-network Ark canary plan")
    parser.add_argument("--capability", type=Path, required=True)
    parser.add_argument("--pricing", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--max-cost-cny", type=Decimal, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--frozen-request-output", type=Path)
    args = parser.parse_args(argv)
    request = _load(args.request, ProviderRequest)
    expected_fingerprint = request_fingerprint(request)
    if request.request_fingerprint not in {"0" * 64, expected_fingerprint}:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "input request contains a mismatched non-placeholder fingerprint",
        )
    request = request.model_copy(update={"request_fingerprint": expected_fingerprint})
    plan = build_canary_plan(
        _load(args.capability, ProviderCapabilitySnapshot),
        _load(args.pricing, ProviderPricingSnapshot),
        request,
        args.max_cost_cny,
    )
    rendered = plan.model_dump_json(indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    if args.frozen_request_output:
        args.frozen_request_output.parent.mkdir(parents=True, exist_ok=True)
        args.frozen_request_output.write_text(request.model_dump_json(indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
