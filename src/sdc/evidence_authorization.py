"""Offline evidence-bound authorization candidates and fail-closed runtime validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sdc.canary import (
    CANARY_COST_HARD_LIMIT_CNY,
    LiveGateError,
    contract_sha256,
    validate_snapshots,
)
from sdc.contracts import (
    CanaryExecution,
    EvidenceBoundCanaryPlan,
    EvidenceBoundLiveAuthorization,
    ProviderFailureClass,
    ProviderRequest,
)
from sdc.evidence_authorization_registry import (
    ReviewedEvidenceAuthorization,
    require_reviewed_evidence_authorization,
)
from sdc.fresh_canary_plan import _load_contract, _preflight_new_outputs, _write_new
from sdc.fresh_evidence import (
    FreshCanaryEvidence,
    load_trusted_fresh_canary_evidence,
    require_trusted_fresh_evidence_anchor,
)
from sdc.provider import (
    ARK_BASE_URL,
    ARK_REGION,
    ARK_SUBMIT_PATH,
    ark_submission_policy_sha256,
)

_PROTECTED_AUTHORIZATION_OUTPUT_COMPONENTS = frozenset(
    {
        "canary",
        "evidence-cas",
        "evidence-current",
        "v02-r2",
        "v02-r3",
        "v02-r4",
        "v02-r5",
        "v02-r6",
        "v02-r6-live",
    }
)


def _reject_protected_authorization_output(path: Path, *, resolve_aliases: bool) -> None:
    absolute = path.absolute()
    if str(absolute).startswith(("\\\\", "//")):
        raise LiveGateError(
            ProviderFailureClass.CONFIGURATION,
            "authorization candidates must use a local filesystem path",
        )
    candidates = (absolute.resolve(strict=False),) if resolve_aliases else (absolute,)
    for candidate in candidates:
        components = {part.rstrip(" .").casefold() for part in candidate.parts}
        if components & _PROTECTED_AUTHORIZATION_OUTPUT_COMPONENTS:
            raise LiveGateError(
                ProviderFailureClass.CONFIGURATION,
                "authorization candidates must not be written into evidence, Canary, "
                "or live archives",
            )

def evidence_bound_runtime_policy_sha256(*, task_queue: str, ledger_id: str) -> str:
    """Hash the exact fail-closed runtime policy reviewed for a one-POST Canary."""
    descriptor = {
        "provider": "volcengine_ark",
        "region": ARK_REGION,
        "base_url": ARK_BASE_URL,
        "submit_path": ARK_SUBMIT_PATH,
        "task_queue": task_queue,
        "ledger_id": ledger_id,
        "requires_frozen_canary_request": True,
        "creative_attempt": 1,
        "max_submit_calls": 1,
        "worker_activity_concurrency": 1,
        "legacy_plan_allowed": False,
        "legacy_authorization_allowed": False,
        "generic_submit_activity_allowed": False,
    }
    encoded = json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(b"sdc:evidence-bound-runtime-policy:1.0.0\0" + encoded).hexdigest()


def _require_aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise LiveGateError(
            ProviderFailureClass.CONFIGURATION,
            f"{field} must include a timezone",
        )
    return value.astimezone(UTC)


def _validate_plan_and_evidence(
    plan: EvidenceBoundCanaryPlan,
    execution: CanaryExecution,
    evidence: FreshCanaryEvidence,
) -> None:
    capability_sha256 = contract_sha256(evidence.capability)
    pricing_sha256 = contract_sha256(evidence.pricing)
    if (
        plan.evidence_bundle_id != evidence.bundle_id
        or plan.evidence_logical_tree_sha256 != evidence.logical_tree_sha256
        or plan.evidence_valid_until.astimezone(UTC) != evidence.valid_until.astimezone(UTC)
        or plan.capability_snapshot_sha256 != capability_sha256
        or plan.pricing_snapshot_sha256 != pricing_sha256
    ):
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT,
            "evidence-bound plan does not match the reviewed FRESH bundle",
        )
    request = execution.request
    if (
        plan.run_id != execution.run_id
        or plan.run_id != request.run_id
        or plan.job_id != request.job_id
        or plan.attempt != request.attempt
        or plan.request_fingerprint != request.request_fingerprint
    ):
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "evidence-bound plan does not match the exact Canary execution",
        )
    if plan.worst_case_cost_cny != evidence.pricing.worst_case_cost_cny:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "evidence-bound plan cost does not match reviewed pricing",
        )


def _validate_authorization_binding(
    *,
    evidence: FreshCanaryEvidence,
    plan: EvidenceBoundCanaryPlan,
    execution: CanaryExecution,
    authorization: EvidenceBoundLiveAuthorization,
    reviewed_authorization: ReviewedEvidenceAuthorization,
    runtime_release_sha256: str,
    task_queue: str,
    ledger_id: str,
    entitlement_anchor_sha256: str,
) -> None:
    _validate_plan_and_evidence(plan, execution, evidence)
    expected_authorization_sha256 = contract_sha256(authorization)
    if reviewed_authorization.authorization_sha256 != expected_authorization_sha256:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "authorization candidate digest is not independently approved",
        )
    expected = {
        "plan_sha256": contract_sha256(plan),
        "execution_sha256": contract_sha256(execution),
        "submission_policy_sha256": ark_submission_policy_sha256(execution.request),
        "runtime_policy_sha256": evidence_bound_runtime_policy_sha256(
            task_queue=task_queue,
            ledger_id=ledger_id,
        ),
        "runtime_release_sha256": runtime_release_sha256,
        "evidence_bundle_id": evidence.bundle_id,
        "evidence_logical_tree_sha256": evidence.logical_tree_sha256,
        "entitlement_anchor_sha256": entitlement_anchor_sha256,
        "task_queue": task_queue,
        "ledger_id": ledger_id,
        "run_id": plan.run_id,
        "job_id": plan.job_id,
        "request_fingerprint": plan.request_fingerprint,
        "capability_snapshot_sha256": plan.capability_snapshot_sha256,
        "pricing_snapshot_sha256": plan.pricing_snapshot_sha256,
    }
    for field, expected_value in expected.items():
        if getattr(authorization, field) != expected_value:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                f"evidence-bound authorization {field} mismatch",
            )
    reviewed_expected = {
        "authorization_id": authorization.authorization_id,
        "plan_sha256": authorization.plan_sha256,
        "execution_sha256": authorization.execution_sha256,
        "evidence_bundle_id": authorization.evidence_bundle_id,
        "request_fingerprint": authorization.request_fingerprint,
        "runtime_release_sha256": authorization.runtime_release_sha256,
        "entitlement_anchor_sha256": authorization.entitlement_anchor_sha256,
        "max_cost_cny": authorization.max_cost_cny,
        "expires_at": authorization.expires_at,
    }
    for field, reviewed_value in reviewed_expected.items():
        if getattr(reviewed_authorization, field) != reviewed_value:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                f"Git-reviewed authorization {field} mismatch",
            )
    if authorization.authorized_at < plan.planned_at.astimezone(UTC):
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "authorization predates the evidence-bound plan",
        )
    if reviewed_authorization.reviewed_at.astimezone(UTC) < authorization.authorized_at:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "Git review predates the authorization candidate",
        )
    if authorization.evidence_valid_until != plan.evidence_valid_until.astimezone(UTC):
        raise LiveGateError(
            ProviderFailureClass.CAPABILITY_DRIFT,
            "authorization evidence expiry does not match the plan",
        )
    if authorization.worst_case_cost_cny != plan.worst_case_cost_cny:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "authorization worst-case cost does not match the plan",
        )
    if authorization.max_cost_cny > plan.approved_cost_ceiling_cny:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "authorization cost exceeds the reviewed planning ceiling",
        )


def build_evidence_bound_authorization_candidate(
    *,
    evidence_root: Path,
    reviewed_bundle_id: str,
    plan: EvidenceBoundCanaryPlan,
    execution: CanaryExecution,
    authorization_id: str,
    entitlement_anchor_sha256: str,
    entitlement_valid_until: datetime,
    runtime_release_sha256: str,
    task_queue: str,
    ledger_id: str,
    max_cost_cny: Decimal,
    expires_at: datetime,
    nonce: str,
    authorized_at: datetime | None = None,
) -> EvidenceBoundLiveAuthorization:
    """Create an inert candidate; its canonical digest still needs independent approval."""
    current = _require_aware(authorized_at or datetime.now(UTC), "authorized_at")
    entitlement_expiry = _require_aware(
        entitlement_valid_until,
        "entitlement_valid_until",
    )
    expiry = _require_aware(expires_at, "expires_at")
    evidence = load_trusted_fresh_canary_evidence(
        manifest_path=evidence_root / "bundles" / f"{reviewed_bundle_id}.json",
        object_root=evidence_root / "objects",
        expected_bundle_id=reviewed_bundle_id,
        at=current,
    )
    _validate_plan_and_evidence(plan, execution, evidence)
    if current < plan.planned_at.astimezone(UTC):
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "authorization cannot predate its evidence-bound plan",
        )
    if current >= entitlement_expiry:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "entitlement evidence is not current at authorization time",
        )
    if entitlement_anchor_sha256 in {
        evidence.bundle_id,
        evidence.logical_tree_sha256,
        plan.capability_snapshot_sha256,
        plan.pricing_snapshot_sha256,
    }:
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "entitlement must use an independent reviewed anchor",
        )
    if not plan.worst_case_cost_cny <= max_cost_cny <= plan.approved_cost_ceiling_cny:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "authorization cost must cover worst case without exceeding the plan ceiling",
        )
    if max_cost_cny > CANARY_COST_HARD_LIMIT_CNY:
        raise LiveGateError(
            ProviderFailureClass.COST_LIMIT,
            "authorization cost exceeds the Canary hard limit",
        )
    if not current < expiry <= min(evidence.valid_until, entitlement_expiry):
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "authorization expiry must remain inside evidence and entitlement validity",
        )
    validate_snapshots(
        evidence.capability,
        evidence.pricing,
        execution.request,
        max_cost_cny,
        now=current,
    )
    return EvidenceBoundLiveAuthorization(
        authorization_id=authorization_id,
        plan_sha256=contract_sha256(plan),
        execution_sha256=contract_sha256(execution),
        submission_policy_sha256=ark_submission_policy_sha256(execution.request),
        runtime_policy_sha256=evidence_bound_runtime_policy_sha256(
            task_queue=task_queue,
            ledger_id=ledger_id,
        ),
        runtime_release_sha256=runtime_release_sha256,
        evidence_bundle_id=evidence.bundle_id,
        evidence_logical_tree_sha256=evidence.logical_tree_sha256,
        evidence_valid_until=evidence.valid_until,
        entitlement_anchor_sha256=entitlement_anchor_sha256,
        entitlement_valid_until=entitlement_expiry,
        task_queue=task_queue,
        ledger_id=ledger_id,
        run_id=plan.run_id,
        job_id=plan.job_id,
        request_fingerprint=plan.request_fingerprint,
        capability_snapshot_sha256=plan.capability_snapshot_sha256,
        pricing_snapshot_sha256=plan.pricing_snapshot_sha256,
        worst_case_cost_cny=plan.worst_case_cost_cny,
        max_cost_cny=max_cost_cny,
        authorized_at=current,
        expires_at=expiry,
        nonce=nonce,
    )


class _EvidenceBoundSubmissionGuard:
    """Validated, inert runtime binding; production Worker wiring remains disabled."""

    def __init__(
        self,
        *,
        evidence: FreshCanaryEvidence,
        plan: EvidenceBoundCanaryPlan,
        execution: CanaryExecution,
        authorization: EvidenceBoundLiveAuthorization,
        reviewed_authorization: ReviewedEvidenceAuthorization,
        runtime_release_sha256: str,
        task_queue: str,
        ledger_id: str,
        entitlement_anchor_sha256: str,
    ) -> None:
        _validate_authorization_binding(
            evidence=evidence,
            plan=plan,
            execution=execution,
            authorization=authorization,
            reviewed_authorization=reviewed_authorization,
            runtime_release_sha256=runtime_release_sha256,
            task_queue=task_queue,
            ledger_id=ledger_id,
            entitlement_anchor_sha256=entitlement_anchor_sha256,
        )
        self.evidence = evidence
        self.plan = plan
        self.execution = execution
        self.authorization = authorization
        self.authorization_sha256 = reviewed_authorization.authorization_sha256

    def validate(self, request: ProviderRequest, *, now: datetime | None = None) -> None:
        current = _require_aware(now or datetime.now(UTC), "current time")
        if current < self.authorization.authorized_at:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                "evidence-bound authorization is not active yet",
            )
        if current >= min(
            self.authorization.expires_at,
            self.authorization.evidence_valid_until,
            self.authorization.entitlement_valid_until,
        ):
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                "evidence-bound authorization has expired",
            )
        if request != self.execution.request:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                "runtime request does not match the authorized Canary execution",
            )
        if ark_submission_policy_sha256(request) != self.authorization.submission_policy_sha256:
            raise LiveGateError(
                ProviderFailureClass.LIVE_NOT_AUTHORIZED,
                "Ark submission policy drifted after authorization",
            )
        validate_snapshots(
            self.evidence.capability,
            self.evidence.pricing,
            request,
            self.authorization.max_cost_cny,
            now=current,
        )


def load_evidence_bound_runtime_binding(
    *,
    evidence_root: Path,
    reviewed_bundle_id: str,
    plan_path: Path,
    execution_path: Path,
    authorization_path: Path,
    approved_authorization_sha256: str,
    runtime_release_sha256: str,
    task_queue: str,
    ledger_id: str,
    entitlement_anchor_sha256: str,
    at: datetime | None = None,
) -> _EvidenceBoundSubmissionGuard:
    """Load only the new contract after positive registry lookup; never accepts legacy unions."""
    current = _require_aware(at or datetime.now(UTC), "current time")
    require_trusted_fresh_evidence_anchor(reviewed_bundle_id, at=current)
    reviewed_authorization = require_reviewed_evidence_authorization(
        approved_authorization_sha256,
        at=current,
    )
    plan = _load_contract(plan_path, EvidenceBoundCanaryPlan)
    execution = _load_contract(execution_path, CanaryExecution)
    authorization = _load_contract(authorization_path, EvidenceBoundLiveAuthorization)
    evidence = load_trusted_fresh_canary_evidence(
        manifest_path=evidence_root / "bundles" / f"{reviewed_bundle_id}.json",
        object_root=evidence_root / "objects",
        expected_bundle_id=reviewed_bundle_id,
        at=current,
    )
    guard = _EvidenceBoundSubmissionGuard(
        evidence=evidence,
        plan=plan,
        execution=execution,
        authorization=authorization,
        reviewed_authorization=reviewed_authorization,
        runtime_release_sha256=runtime_release_sha256,
        task_queue=task_queue,
        ledger_id=ledger_id,
        entitlement_anchor_sha256=entitlement_anchor_sha256,
    )
    completion = current if at is not None else datetime.now(UTC)
    guard.validate(execution.request, now=completion)
    return guard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an inert evidence-bound authorization candidate without execution"
    )
    parser.add_argument("--fresh-evidence-root", type=Path, required=True)
    parser.add_argument("--reviewed-evidence-bundle-id", required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--entitlement-anchor-sha256", required=True)
    parser.add_argument("--entitlement-valid-until", type=datetime.fromisoformat, required=True)
    parser.add_argument("--runtime-release-sha256", required=True)
    parser.add_argument("--task-queue", required=True)
    parser.add_argument("--ledger-id", required=True)
    parser.add_argument("--max-cost-cny", type=Decimal, required=True)
    parser.add_argument("--expires-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    authorized_at = datetime.now(UTC)
    require_trusted_fresh_evidence_anchor(
        args.reviewed_evidence_bundle_id,
        at=authorized_at,
    )
    plan = _load_contract(args.plan, EvidenceBoundCanaryPlan)
    execution = _load_contract(args.execution, CanaryExecution)
    authorization = build_evidence_bound_authorization_candidate(
        evidence_root=args.fresh_evidence_root,
        reviewed_bundle_id=args.reviewed_evidence_bundle_id,
        plan=plan,
        execution=execution,
        authorization_id=args.authorization_id,
        entitlement_anchor_sha256=args.entitlement_anchor_sha256,
        entitlement_valid_until=args.entitlement_valid_until,
        runtime_release_sha256=args.runtime_release_sha256,
        task_queue=args.task_queue,
        ledger_id=args.ledger_id,
        max_cost_cny=args.max_cost_cny,
        expires_at=args.expires_at,
        nonce=secrets.token_hex(32),
        authorized_at=authorized_at,
    )
    _reject_protected_authorization_output(args.output, resolve_aliases=False)
    _preflight_new_outputs((args.output,))
    _reject_protected_authorization_output(args.output, resolve_aliases=True)
    completion = datetime.now(UTC)
    if completion >= min(
        authorization.expires_at,
        authorization.evidence_valid_until,
        authorization.entitlement_valid_until,
    ):
        raise LiveGateError(
            ProviderFailureClass.LIVE_NOT_AUTHORIZED,
            "authorization candidate expired before it could be written",
        )
    _write_new(args.output, authorization.model_dump_json(indent=2) + "\n")
    print(
        json.dumps(
            {
                "mode": "candidate-only-not-approved",
                "authorization_id": authorization.authorization_id,
                "authorization_sha256": contract_sha256(authorization),
                "expires_at": authorization.expires_at.isoformat(),
                "max_posts": authorization.max_posts,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
