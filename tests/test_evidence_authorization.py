import hashlib
import json
import re
import socket
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Self, cast

import pytest
from pydantic import ValidationError

import sdc.evidence_authorization as evidence_authorization
import sdc.evidence_authorization_registry as authorization_registry
import sdc.fresh_evidence as fresh_evidence
from sdc.canary import LiveGateError, build_canary_plan, contract_sha256
from sdc.contracts import (
    CanaryExecution,
    EvidenceBoundCanaryPlan,
    EvidenceBoundLiveAuthorization,
    EvidenceBundle,
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
from sdc.evidence import EvidenceBundleError
from sdc.evidence_authorization import (
    build_evidence_bound_authorization_candidate,
    evidence_bound_runtime_policy_sha256,
    load_evidence_bound_runtime_binding,
)
from sdc.evidence_authorization_registry import ReviewedEvidenceAuthorization
from sdc.fresh_canary_plan import _build_evidence_bound_canary_plan_at
from sdc.fresh_evidence import (
    FreshEvidenceError,
    build_fresh_canary_evidence_bundle,
)
from sdc.fresh_evidence_registry import ReviewedFreshEvidence
from sdc.provider import ark_submission_policy_sha256, request_fingerprint

CAPTURED_AT = datetime(2026, 8, 15, 1, tzinfo=UTC)
PLANNED_AT = CAPTURED_AT + timedelta(hours=1)
AUTHORIZED_AT = PLANNED_AT + timedelta(hours=1)
EXPIRES_AT = AUTHORIZED_AT + timedelta(hours=2)
ENTITLEMENT_VALID_UNTIL = AUTHORIZED_AT + timedelta(hours=4)
VALID_UNTIL = AUTHORIZED_AT + timedelta(hours=6)
CAPABILITY_PDF = b"%PDF-1.7\nauthorization capability evidence\n%%EOF\n"
PRICING_PDF = b"%PDF-1.7\nauthorization pricing evidence\n%%EOF\n"
ENTITLEMENT_ANCHOR = "e" * 64
RUNTIME_RELEASE = "d" * 64
TASK_QUEUE = "sdc-canary-001-evidence-bound"
LEDGER_ID = "sdc-canary-001-ledger"


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz: object = None) -> Self:
        if tz is None:
            return cast(Self, AUTHORIZED_AT.replace(tzinfo=None))
        return cast(Self, AUTHORIZED_AT)


class ExpiringRuntimeDateTime(datetime):
    calls = 0

    @classmethod
    def now(cls, tz: object = None) -> Self:
        cls.calls += 1
        value = AUTHORIZED_AT + timedelta(minutes=1) if cls.calls == 1 else EXPIRES_AT
        if tz is None:
            value = value.replace(tzinfo=None)
        return cast(Self, value)


@dataclass(frozen=True)
class PreparedAuthorization:
    root: Path
    bundle: EvidenceBundle
    capability: ProviderCapabilitySnapshot
    pricing: ProviderPricingSnapshot
    execution: CanaryExecution
    plan: EvidenceBoundCanaryPlan


def _request() -> ProviderRequest:
    draft = ProviderRequest(
        run_id="fresh-authorization-run",
        job_id="fresh-authorization-job",
        attempt=1,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        prompt="A paper lantern glows against a plain midnight background.",
        duration_ms=4000,
        aspect_ratio="9:16",
        resolution="1080p",
        generate_audio=False,
        input_materials=(),
        request_fingerprint="0" * 64,
    )
    return draft.model_copy(update={"request_fingerprint": request_fingerprint(draft)})


def _capability() -> ProviderCapabilitySnapshot:
    return ProviderCapabilitySnapshot(
        snapshot_revision="2026-08-15.authorization-test",
        status=SnapshotStatus.CURRENT,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        aspect_ratios=("9:16",),
        resolutions=("1080p",),
        fps=24,
        min_duration_ms=4000,
        max_duration_ms=15000,
        source_url="https://docs.volcengine.com/docs/82379/1330310?lang=zh",
        source_updated_at=CAPTURED_AT - timedelta(days=1),
        captured_at=CAPTURED_AT,
        valid_until=VALID_UNTIL,
        evidence_sha256=hashlib.sha256(CAPABILITY_PDF).hexdigest(),
    )


def _pricing() -> ProviderPricingSnapshot:
    return ProviderPricingSnapshot(
        snapshot_revision="2026-08-15.authorization-test",
        status=SnapshotStatus.CURRENT,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        resolution="1080p",
        input_mode=PricingInputMode.WITHOUT_VIDEO,
        billing_unit="provider-token",
        unit_price_cny=Decimal("0.000001"),
        worst_case_units=Decimal("196425"),
        worst_case_cost_cny=Decimal("0.196425"),
        source_url="https://docs.volcengine.com/docs/82379/1544106?lang=zh",
        source_updated_at=CAPTURED_AT - timedelta(days=1),
        captured_at=CAPTURED_AT + timedelta(minutes=5),
        valid_until=VALID_UNTIL,
        evidence_sha256=hashlib.sha256(PRICING_PDF).hexdigest(),
    )


def _prepare(root: Path, monkeypatch: pytest.MonkeyPatch) -> PreparedAuthorization:
    capability = _capability()
    pricing = _pricing()
    bundle, data_by_path = build_fresh_canary_evidence_bundle(
        capability_snapshot_bytes=capability.model_dump_json(indent=2).encode(),
        capability_evidence_bytes=CAPABILITY_PDF,
        pricing_snapshot_bytes=pricing.model_dump_json(indent=2).encode(),
        pricing_evidence_bytes=PRICING_PDF,
    )
    object_root = root / "objects"
    for member in bundle.content.members:
        target = object_root / member.object_sha256[:2] / member.object_sha256
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data_by_path[member.logical_path])
    manifest = root / "bundles" / f"{bundle.bundle_id}.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    anchor = ReviewedFreshEvidence(
        bundle_id=bundle.bundle_id,
        logical_tree_sha256=bundle.content.resolved_logical_tree_sha256,
        capability_snapshot_sha256=contract_sha256(capability),
        pricing_snapshot_sha256=contract_sha256(pricing),
        reviewed_at=bundle.content.created_at,
        valid_until=bundle.content.valid_until,
    )
    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", (anchor,))

    request = _request()
    job = GenerationJob(
        id=request.job_id,
        shot_id="fresh-authorization-shot",
        prompt=request.prompt,
        duration_ms=request.duration_ms,
        idempotency_key="fresh-authorization-generate",
    )
    execution = CanaryExecution(
        run_id=request.run_id,
        graph=JobGraph(id="fresh-authorization-graph", jobs=(job,)),
        request=request,
    )
    plan = _build_evidence_bound_canary_plan_at(
        evidence_root=root,
        reviewed_bundle_id=bundle.bundle_id,
        request=request,
        cost_ceiling_cny=Decimal("0.20"),
        planned_at=PLANNED_AT,
    )
    return PreparedAuthorization(root, bundle, capability, pricing, execution, plan)


def _candidate(
    prepared: PreparedAuthorization,
    **updates: object,
) -> EvidenceBoundLiveAuthorization:
    values: dict[str, object] = {
        "evidence_root": prepared.root,
        "reviewed_bundle_id": prepared.bundle.bundle_id,
        "plan": prepared.plan,
        "execution": prepared.execution,
        "authorization_id": "SDC-CANARY-001-EVIDENCE-BOUND-01",
        "entitlement_anchor_sha256": ENTITLEMENT_ANCHOR,
        "entitlement_valid_until": ENTITLEMENT_VALID_UNTIL,
        "runtime_release_sha256": RUNTIME_RELEASE,
        "task_queue": TASK_QUEUE,
        "ledger_id": LEDGER_ID,
        "max_cost_cny": Decimal("0.20"),
        "expires_at": EXPIRES_AT,
        "nonce": "f" * 64,
        "authorized_at": AUTHORIZED_AT,
    }
    values.update(updates)
    return build_evidence_bound_authorization_candidate(**values)  # type: ignore[arg-type]


def _write_runtime_inputs(
    root: Path,
    prepared: PreparedAuthorization,
    authorization: EvidenceBoundLiveAuthorization | LiveAuthorization,
) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    plan_path = root / "plan.json"
    execution_path = root / "execution.json"
    authorization_path = root / "authorization.json"
    plan_path.write_text(prepared.plan.model_dump_json(indent=2), encoding="utf-8")
    execution_path.write_text(prepared.execution.model_dump_json(indent=2), encoding="utf-8")
    authorization_path.write_text(authorization.model_dump_json(indent=2), encoding="utf-8")
    return plan_path, execution_path, authorization_path


def _reviewed_authorization(
    authorization: EvidenceBoundLiveAuthorization,
    **updates: object,
) -> ReviewedEvidenceAuthorization:
    authorization_sha256 = contract_sha256(authorization)
    reviewed = ReviewedEvidenceAuthorization(
        authorization_sha256=authorization_sha256,
        authorization_id=authorization.authorization_id,
        plan_sha256=authorization.plan_sha256,
        execution_sha256=authorization.execution_sha256,
        evidence_bundle_id=authorization.evidence_bundle_id,
        request_fingerprint=authorization.request_fingerprint,
        runtime_release_sha256=authorization.runtime_release_sha256,
        entitlement_anchor_sha256=authorization.entitlement_anchor_sha256,
        max_cost_cny=authorization.max_cost_cny,
        reviewed_at=AUTHORIZED_AT + timedelta(seconds=30),
        expires_at=authorization.expires_at,
    )
    return replace(reviewed, **updates)


def _approve(
    monkeypatch: pytest.MonkeyPatch,
    authorization: EvidenceBoundLiveAuthorization,
) -> str:
    reviewed = _reviewed_authorization(authorization)
    monkeypatch.setattr(
        authorization_registry,
        "REVIEWED_EVIDENCE_AUTHORIZATIONS",
        (reviewed,),
    )
    return reviewed.authorization_sha256


def _load_binding(
    prepared: PreparedAuthorization,
    paths: tuple[Path, Path, Path],
    authorization_sha256: str,
):
    plan_path, execution_path, authorization_path = paths
    return load_evidence_bound_runtime_binding(
        evidence_root=prepared.root,
        reviewed_bundle_id=prepared.bundle.bundle_id,
        plan_path=plan_path,
        execution_path=execution_path,
        authorization_path=authorization_path,
        approved_authorization_sha256=authorization_sha256,
        runtime_release_sha256=RUNTIME_RELEASE,
        task_queue=TASK_QUEUE,
        ledger_id=LEDGER_ID,
        entitlement_anchor_sha256=ENTITLEMENT_ANCHOR,
        at=AUTHORIZED_AT + timedelta(minutes=1),
    )


def test_candidate_binds_plan_execution_evidence_entitlement_and_runtime_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path, monkeypatch)
    authorization = _candidate(prepared)

    assert authorization.document_type == "sdc.evidence-bound-live-authorization"
    assert authorization.plan_sha256 == contract_sha256(prepared.plan)
    assert authorization.execution_sha256 == contract_sha256(prepared.execution)
    assert authorization.submission_policy_sha256 == ark_submission_policy_sha256(
        prepared.execution.request
    )
    assert authorization.runtime_policy_sha256 == evidence_bound_runtime_policy_sha256(
        task_queue=TASK_QUEUE,
        ledger_id=LEDGER_ID,
    )
    assert authorization.evidence_bundle_id == prepared.bundle.bundle_id
    assert authorization.entitlement_anchor_sha256 == ENTITLEMENT_ANCHOR
    assert authorization.max_posts == 1 and authorization.attempt == 1
    assert authorization.expires_at < authorization.evidence_valid_until
    assert (
        EvidenceBoundLiveAuthorization.model_validate_json(authorization.model_dump_json())
        == authorization
    )


def test_new_and_legacy_authorization_contracts_are_mutually_incompatible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path, monkeypatch)
    authorization = _candidate(prepared)
    legacy = LiveAuthorization(
        authorization_id="legacy",
        request_fingerprint=prepared.execution.request.request_fingerprint,
        capability_snapshot_sha256=prepared.plan.capability_snapshot_sha256,
        pricing_snapshot_sha256=prepared.plan.pricing_snapshot_sha256,
        max_cost_cny=Decimal("0.20"),
        expires_at=EXPIRES_AT,
        nonce="a" * 64,
    )

    with pytest.raises(ValidationError):
        LiveAuthorization.model_validate(authorization.model_dump(mode="python"))
    with pytest.raises(ValidationError):
        EvidenceBoundLiveAuthorization.model_validate(legacy.model_dump(mode="python"))


def test_authorization_contract_rejects_entitlement_anchor_reuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path, monkeypatch)
    authorization = _candidate(prepared)
    forbidden_anchors = (
        authorization.evidence_bundle_id,
        authorization.evidence_logical_tree_sha256,
        authorization.capability_snapshot_sha256,
        authorization.pricing_snapshot_sha256,
    )

    for anchor in forbidden_anchors:
        payload = authorization.model_dump(mode="python")
        payload["entitlement_anchor_sha256"] = anchor
        with pytest.raises(ValidationError, match="independent reviewed anchor"):
            EvidenceBoundLiveAuthorization.model_validate(payload)


def test_candidate_rejects_plan_cost_entitlement_and_expiry_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path, monkeypatch)

    with pytest.raises(LiveGateError, match="exact Canary execution"):
        _candidate(
            prepared,
            plan=prepared.plan.model_copy(update={"run_id": "different-run"}),
        )
    with pytest.raises(LiveGateError, match="independent reviewed anchor"):
        _candidate(prepared, entitlement_anchor_sha256=prepared.bundle.bundle_id)
    with pytest.raises(LiveGateError, match="cover worst case"):
        _candidate(prepared, max_cost_cny=Decimal("0.19"))
    with pytest.raises(LiveGateError, match="inside evidence and entitlement validity"):
        _candidate(prepared, expires_at=ENTITLEMENT_VALID_UNTIL + timedelta(seconds=1))


def test_empty_authorization_registry_fails_before_runtime_artifact_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path / "fresh", monkeypatch)
    authorization = _candidate(prepared)
    monkeypatch.setattr(
        authorization_registry,
        "REVIEWED_EVIDENCE_AUTHORIZATIONS",
        (),
    )

    with pytest.raises(LiveGateError, match="not in the Git-reviewed registry"):
        load_evidence_bound_runtime_binding(
            evidence_root=prepared.root,
            reviewed_bundle_id=prepared.bundle.bundle_id,
            plan_path=tmp_path / "must-not-read-plan.json",
            execution_path=tmp_path / "must-not-read-execution.json",
            authorization_path=tmp_path / "must-not-read-authorization.json",
            approved_authorization_sha256=contract_sha256(authorization),
            runtime_release_sha256=RUNTIME_RELEASE,
            task_queue=TASK_QUEUE,
            ledger_id=LEDGER_ID,
            entitlement_anchor_sha256=ENTITLEMENT_ANCHOR,
            at=AUTHORIZED_AT + timedelta(minutes=1),
        )


@pytest.mark.parametrize(
    ("field", "message"),
    [
        pytest.param("authorization_id", "duplicate authorization ID", id="authorization-id"),
        pytest.param("plan_sha256", "duplicate plan digest", id="plan"),
        pytest.param("execution_sha256", "duplicate execution digest", id="execution"),
        pytest.param(
            "request_fingerprint",
            "duplicate request fingerprint",
            id="request-fingerprint",
        ),
    ],
)
def test_authorization_registry_rejects_duplicate_one_use_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    message: str,
) -> None:
    prepared = _prepare(tmp_path, monkeypatch)
    authorization = _candidate(prepared)
    reviewed = _reviewed_authorization(authorization)
    distinct = replace(
        reviewed,
        authorization_sha256="1" * 64,
        authorization_id="SDC-CANARY-001-EVIDENCE-BOUND-OTHER",
        plan_sha256="2" * 64,
        execution_sha256="3" * 64,
        request_fingerprint="4" * 64,
    )
    duplicate = replace(distinct, **{field: getattr(reviewed, field)})
    monkeypatch.setattr(
        authorization_registry,
        "REVIEWED_EVIDENCE_AUTHORIZATIONS",
        (reviewed, duplicate),
    )

    with pytest.raises(LiveGateError, match=message):
        authorization_registry.require_reviewed_evidence_authorization(
            reviewed.authorization_sha256,
            at=AUTHORIZED_AT + timedelta(minutes=1),
        )


def test_runtime_loader_revalidates_registry_cas_and_exact_authorization_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path / "fresh", monkeypatch)
    authorization = _candidate(prepared)
    paths = _write_runtime_inputs(tmp_path / "runtime", prepared, authorization)
    approved = _approve(monkeypatch, authorization)

    guard = _load_binding(prepared, paths, approved)
    guard.validate(prepared.execution.request, now=AUTHORIZED_AT + timedelta(minutes=2))
    with pytest.raises(LiveGateError, match="does not match the authorized Canary execution"):
        guard.validate(
            prepared.execution.request.model_copy(update={"prompt": "different"}),
            now=AUTHORIZED_AT + timedelta(minutes=2),
        )

    reviewed_registry = fresh_evidence.REVIEWED_FRESH_EVIDENCE
    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", ())
    with pytest.raises(FreshEvidenceError, match="Git-reviewed"):
        _load_binding(prepared, paths, approved)
    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", reviewed_registry)

    first_object = prepared.bundle.content.objects[0]
    object_path = prepared.root / "objects" / first_object.sha256[:2] / first_object.sha256
    object_path.write_bytes(b"tampered")
    with pytest.raises(EvidenceBundleError, match="size|digest"):
        _load_binding(prepared, paths, approved)


def test_runtime_loader_rejects_independently_approved_but_misbound_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path / "fresh", monkeypatch)
    authorization = _candidate(prepared).model_copy(
        update={"runtime_release_sha256": "c" * 64}
    )
    paths = _write_runtime_inputs(tmp_path / "runtime", prepared, authorization)
    approved = _approve(monkeypatch, authorization)

    with pytest.raises(LiveGateError, match="runtime_release_sha256 mismatch"):
        _load_binding(prepared, paths, approved)


def test_runtime_loader_rejects_review_that_predates_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path / "fresh", monkeypatch)
    authorization = _candidate(prepared)
    paths = _write_runtime_inputs(tmp_path / "runtime", prepared, authorization)
    reviewed = _reviewed_authorization(
        authorization,
        reviewed_at=authorization.authorized_at - timedelta(seconds=1),
    )
    monkeypatch.setattr(
        authorization_registry,
        "REVIEWED_EVIDENCE_AUTHORIZATIONS",
        (reviewed,),
    )

    with pytest.raises(LiveGateError, match="Git review predates"):
        _load_binding(prepared, paths, reviewed.authorization_sha256)


def test_runtime_loader_rechecks_expiry_after_all_artifact_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path / "fresh", monkeypatch)
    authorization = _candidate(prepared)
    paths = _write_runtime_inputs(tmp_path / "runtime", prepared, authorization)
    approved = _approve(monkeypatch, authorization)
    ExpiringRuntimeDateTime.calls = 0
    monkeypatch.setattr(evidence_authorization, "datetime", ExpiringRuntimeDateTime)

    plan_path, execution_path, authorization_path = paths
    with pytest.raises(LiveGateError, match="authorization has expired"):
        load_evidence_bound_runtime_binding(
            evidence_root=prepared.root,
            reviewed_bundle_id=prepared.bundle.bundle_id,
            plan_path=plan_path,
            execution_path=execution_path,
            authorization_path=authorization_path,
            approved_authorization_sha256=approved,
            runtime_release_sha256=RUNTIME_RELEASE,
            task_queue=TASK_QUEUE,
            ledger_id=LEDGER_ID,
            entitlement_anchor_sha256=ENTITLEMENT_ANCHOR,
        )
    assert ExpiringRuntimeDateTime.calls == 2


def test_runtime_loader_accepts_neither_legacy_plan_nor_legacy_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path / "fresh", monkeypatch)
    current_authorization = _candidate(prepared)
    approved = _approve(monkeypatch, current_authorization)
    legacy_plan = build_canary_plan(
        prepared.capability,
        prepared.pricing,
        prepared.execution.request,
        Decimal("0.20"),
        now=PLANNED_AT,
    )
    legacy_plan_path = tmp_path / "legacy-plan.json"
    legacy_plan_path.write_text(legacy_plan.model_dump_json(indent=2), encoding="utf-8")
    with pytest.raises(LiveGateError, match="invalid planner JSON input"):
        load_evidence_bound_runtime_binding(
            evidence_root=prepared.root,
            reviewed_bundle_id=prepared.bundle.bundle_id,
            plan_path=legacy_plan_path,
            execution_path=tmp_path / "must-not-read-execution.json",
            authorization_path=tmp_path / "must-not-read-authorization.json",
            approved_authorization_sha256=approved,
            runtime_release_sha256=RUNTIME_RELEASE,
            task_queue=TASK_QUEUE,
            ledger_id=LEDGER_ID,
            entitlement_anchor_sha256=ENTITLEMENT_ANCHOR,
            at=AUTHORIZED_AT + timedelta(minutes=1),
        )

    legacy_authorization = LiveAuthorization(
        authorization_id="legacy",
        request_fingerprint=prepared.execution.request.request_fingerprint,
        capability_snapshot_sha256=prepared.plan.capability_snapshot_sha256,
        pricing_snapshot_sha256=prepared.plan.pricing_snapshot_sha256,
        max_cost_cny=Decimal("0.20"),
        expires_at=EXPIRES_AT,
        nonce="a" * 64,
    )
    paths = _write_runtime_inputs(tmp_path / "legacy-runtime", prepared, legacy_authorization)
    with pytest.raises(LiveGateError, match="invalid planner JSON input"):
        _load_binding(prepared, paths, approved)


@pytest.mark.parametrize(
    "component",
    [
        "canary",
        "evidence-cas",
        "evidence-current",
        "v02-r2",
        "v02-r3",
        "v02-r4",
        "v02-r5",
        "v02-r6",
        "v02-r6-live",
        "CANARY",
        "canary.",
        "canary ",
        "V02-R6-LIVE. ",
    ],
)
def test_candidate_output_rejects_protected_archive_components(
    tmp_path: Path,
    component: str,
) -> None:
    output = tmp_path / component / "authorization-candidate.json"

    with pytest.raises(LiveGateError, match="must not be written") as exc_info:
        evidence_authorization._reject_protected_authorization_output(
            output,
            resolve_aliases=False,
        )

    assert exc_info.value.failure_class is ProviderFailureClass.CONFIGURATION
    assert not output.exists()


def test_candidate_output_rejects_resolved_alias_into_protected_archive(tmp_path: Path) -> None:
    protected = tmp_path / "canary"
    protected.mkdir()
    alias = tmp_path / "apparently-safe-output"
    alias.symlink_to(protected, target_is_directory=True)
    output = alias / "authorization-candidate.json"
    assert "canary" not in {part.rstrip(" .").casefold() for part in output.absolute().parts}
    assert output.resolve(strict=False).parent == protected.resolve()

    with pytest.raises(LiveGateError, match="must not be written") as exc_info:
        evidence_authorization._reject_protected_authorization_output(
            output,
            resolve_aliases=True,
        )

    assert exc_info.value.failure_class is ProviderFailureClass.CONFIGURATION
    assert not output.exists()


def test_candidate_output_allows_dedicated_unprotected_candidate_namespace(
    tmp_path: Path,
) -> None:
    output = tmp_path / "live-candidates" / "authorization-candidate.json"

    evidence_authorization._reject_protected_authorization_output(
        output,
        resolve_aliases=False,
    )
    evidence_authorization._reject_protected_authorization_output(
        output,
        resolve_aliases=True,
    )

    assert not output.exists()


def test_candidate_cli_is_offline_and_writes_only_an_unapproved_new_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prepared = _prepare(tmp_path / "fresh", monkeypatch)
    plan_path = tmp_path / "plan.json"
    execution_path = tmp_path / "execution.json"
    output_paths = (
        tmp_path / "authorization-candidate-1.json",
        tmp_path / "authorization-candidate-2.json",
    )
    plan_path.write_text(prepared.plan.model_dump_json(indent=2), encoding="utf-8")
    execution_path.write_text(prepared.execution.model_dump_json(indent=2), encoding="utf-8")

    def forbidden_network(*_: object, **__: object) -> None:
        raise AssertionError("authorization candidate generation must remain offline")

    monkeypatch.setattr(socket, "create_connection", forbidden_network)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden_network)
    monkeypatch.setattr(evidence_authorization, "datetime", FrozenDateTime)
    generated_nonces = iter(("b" * 64, "c" * 64))

    def token_hex(size: int) -> str:
        assert size == 32
        return next(generated_nonces)

    monkeypatch.setattr(evidence_authorization.secrets, "token_hex", token_hex)
    authorizations: list[EvidenceBoundLiveAuthorization] = []
    for index, output_path in enumerate(output_paths, start=1):
        assert (
            evidence_authorization.main(
                [
                    "--fresh-evidence-root",
                    str(prepared.root),
                    "--reviewed-evidence-bundle-id",
                    prepared.bundle.bundle_id,
                    "--plan",
                    str(plan_path),
                    "--execution",
                    str(execution_path),
                    "--authorization-id",
                    f"SDC-CANARY-001-EVIDENCE-BOUND-CLI-{index}",
                    "--entitlement-anchor-sha256",
                    ENTITLEMENT_ANCHOR,
                    "--entitlement-valid-until",
                    ENTITLEMENT_VALID_UNTIL.isoformat(),
                    "--runtime-release-sha256",
                    RUNTIME_RELEASE,
                    "--task-queue",
                    TASK_QUEUE,
                    "--ledger-id",
                    LEDGER_ID,
                    "--max-cost-cny",
                    "0.20",
                    "--expires-at",
                    EXPIRES_AT.isoformat(),
                    "--output",
                    str(output_path),
                ]
            )
            == 0
        )

        authorization = EvidenceBoundLiveAuthorization.model_validate_json(
            output_path.read_text(encoding="utf-8")
        )
        report = json.loads(capsys.readouterr().out)
        assert report["mode"] == "candidate-only-not-approved"
        assert report["authorization_sha256"] == contract_sha256(authorization)
        assert authorization.max_posts == 1
        assert re.fullmatch(r"[0-9a-f]{64}", authorization.nonce)
        authorizations.append(authorization)

    assert {authorization.nonce for authorization in authorizations} == {"b" * 64, "c" * 64}
