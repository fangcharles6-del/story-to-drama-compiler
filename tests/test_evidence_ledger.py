from __future__ import annotations

import ast
import copy
import hashlib
import pickle
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import get_args

import pytest

import sdc.evidence_ledger as evidence_ledger
from sdc.ark_entitlement_registry import REVIEWED_ARK_ENTITLEMENT_EVIDENCE
from sdc.contracts import ProviderTaskState
from sdc.evidence_authorization_registry import REVIEWED_EVIDENCE_AUTHORIZATIONS

AUTHORIZED_AT = datetime(2026, 8, 16, 1, 0, tzinfo=UTC)
EXPIRES_AT = AUTHORIZED_AT + timedelta(hours=1)
EVIDENCE_VALID_UNTIL = AUTHORIZED_AT + timedelta(hours=2)
ENTITLEMENT_VALID_UNTIL = AUTHORIZED_AT + timedelta(hours=3)

DIGEST_FIELDS = (
    "authorization_sha256",
    "plan_sha256",
    "execution_sha256",
    "submission_policy_sha256",
    "runtime_policy_sha256",
    "runtime_release_sha256",
    "evidence_bundle_id",
    "evidence_logical_tree_sha256",
    "entitlement_anchor_sha256",
    "request_fingerprint",
    "capability_snapshot_sha256",
    "pricing_snapshot_sha256",
    "nonce_sha256",
)


def _sha256(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _binding() -> evidence_ledger._EvidenceBoundClaimBinding:
    return evidence_ledger._EvidenceBoundClaimBinding(
        authorization_id="authorization-canary-001",
        authorization_sha256=_sha256("authorization"),
        plan_sha256=_sha256("plan"),
        execution_sha256=_sha256("execution"),
        submission_policy_sha256=_sha256("submission-policy"),
        runtime_policy_sha256=_sha256("runtime-policy"),
        runtime_release_sha256=_sha256("runtime-release"),
        evidence_bundle_id=_sha256("evidence-bundle"),
        evidence_logical_tree_sha256=_sha256("evidence-tree"),
        evidence_valid_until=EVIDENCE_VALID_UNTIL,
        entitlement_anchor_sha256=_sha256("entitlement-anchor"),
        entitlement_valid_until=ENTITLEMENT_VALID_UNTIL,
        task_queue="sdc-canary-evidence-bound",
        ledger_id="sdc-canary-ledger",
        deployment_id="sdc-canary-deployment",
        run_id="sdc-canary-run-001",
        job_id="sdc-canary-job-001",
        request_fingerprint=_sha256("request"),
        capability_snapshot_sha256=_sha256("capability"),
        pricing_snapshot_sha256=_sha256("pricing"),
        worst_case_cost_cny=Decimal("0.20"),
        max_cost_cny=Decimal("1.00"),
        authorized_at=AUTHORIZED_AT,
        expires_at=EXPIRES_AT,
        nonce_sha256=_sha256("nonce"),
    )


def _permit() -> evidence_ledger._NewPostPermit:
    return evidence_ledger._NewPostPermit(
        evidence_ledger._PERMIT_FACTORY,
        authorization_sha256=_sha256("authorization"),
        claim_event_id="claim-event-001",
        claimed_at=AUTHORIZED_AT,
        binding=_binding(),
    )


def _set_attribute(target: object, name: str, value: object) -> None:
    setattr(target, name, value)


def _delete_attribute(target: object, name: str) -> None:
    delattr(target, name)


def _changed_binding(**changes: object) -> evidence_ledger._EvidenceBoundClaimBinding:
    # The field name is deliberately data-driven so one parameterized test covers every bound
    # identity. Dataclasses' generated typing cannot express that field/value relationship.
    return replace(_binding(), **changes)  # type: ignore[arg-type]


def test_private_binding_accepts_exact_values_normalizes_utc_and_is_immutable() -> None:
    china_standard_time = timezone(timedelta(hours=8))
    binding = replace(
        _binding(),
        authorized_at=AUTHORIZED_AT.astimezone(china_standard_time),
        expires_at=EXPIRES_AT.astimezone(china_standard_time),
        evidence_valid_until=EVIDENCE_VALID_UNTIL.astimezone(china_standard_time),
        entitlement_valid_until=ENTITLEMENT_VALID_UNTIL.astimezone(china_standard_time),
    )

    assert binding.authorized_at == AUTHORIZED_AT
    assert binding.expires_at == EXPIRES_AT
    assert binding.evidence_valid_until == EVIDENCE_VALID_UNTIL
    assert binding.entitlement_valid_until == ENTITLEMENT_VALID_UNTIL
    assert all(
        value.tzinfo is UTC
        for value in (
            binding.authorized_at,
            binding.expires_at,
            binding.evidence_valid_until,
            binding.entitlement_valid_until,
        )
    )
    with pytest.raises(FrozenInstanceError):
        _set_attribute(binding, "ledger_id", "replacement-ledger")


@pytest.mark.parametrize("field", DIGEST_FIELDS)
def test_private_binding_rejects_every_malformed_digest(field: str) -> None:
    with pytest.raises(ValueError, match=rf"{field} must be lowercase SHA-256"):
        _changed_binding(**{field: "A" * 64})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("authorization_id", ""),
        ("authorization_id", "-leading-dash"),
        ("task_queue", "queue/with/slash"),
        ("ledger_id", "x" * 129),
        ("deployment_id", "deployment\ncontrol"),
    ],
)
def test_private_binding_rejects_nonportable_control_identifiers(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ValueError, match=rf"{field} is not a portable identifier"):
        _changed_binding(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_id", ""),
        ("run_id", "r" * 257),
        ("job_id", "job\ncontrol"),
    ],
)
def test_private_binding_rejects_invalid_run_and_job_identifiers(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ValueError, match=rf"{field} is invalid"):
        _changed_binding(**{field: value})


@pytest.mark.parametrize(
    "field",
    (
        "authorized_at",
        "expires_at",
        "evidence_valid_until",
        "entitlement_valid_until",
    ),
)
def test_private_binding_rejects_naive_datetimes(field: str) -> None:
    with pytest.raises(ValueError, match=rf"{field} must include a timezone"):
        _changed_binding(**{field: AUTHORIZED_AT.replace(tzinfo=None)})


def test_private_binding_rejects_invalid_authorization_and_evidence_windows() -> None:
    with pytest.raises(ValueError, match="authorization window is invalid"):
        replace(_binding(), expires_at=AUTHORIZED_AT)

    with pytest.raises(ValueError, match="authorization exceeds an evidence deadline"):
        replace(_binding(), evidence_valid_until=EXPIRES_AT - timedelta(microseconds=1))

    with pytest.raises(ValueError, match="authorization exceeds an evidence deadline"):
        replace(_binding(), entitlement_valid_until=EXPIRES_AT - timedelta(microseconds=1))


@pytest.mark.parametrize(
    ("worst_case", "maximum", "message"),
    [
        (Decimal("0"), Decimal("1.00"), "worst-case cost must be positive"),
        (Decimal("-0.01"), Decimal("1.00"), "worst-case cost must be positive"),
        (Decimal("1.01"), Decimal("1.00"), "does not cover the reviewed bounded cost"),
        (Decimal("0.20"), Decimal("15.000001"), "does not cover the reviewed bounded cost"),
    ],
)
def test_private_binding_rejects_unbounded_or_uncovered_costs(
    worst_case: Decimal,
    maximum: Decimal,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(
            _binding(),
            worst_case_cost_cny=worst_case,
            max_cost_cny=maximum,
        )


@pytest.mark.parametrize("factory", [None, object(), "factory"])
def test_post_permit_rejects_direct_construction(factory: object) -> None:
    with pytest.raises(TypeError, match="only follow a newly committed claim"):
        evidence_ledger._NewPostPermit(
            factory,
            authorization_sha256=_sha256("authorization"),
            claim_event_id="claim-event-001",
            claimed_at=AUTHORIZED_AT,
            binding=_binding(),
        )


def test_post_permit_cannot_be_copied_deepcopied_or_pickled() -> None:
    permit = _permit()

    with pytest.raises(TypeError, match="cannot be copied"):
        copy.copy(permit)
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.deepcopy(permit)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(permit)

    result = evidence_ledger.NewPostPermit(
        disposition="NEW_POST_PERMIT",
        permit=permit,
    )
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.deepcopy(result)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(result)


def test_post_permit_is_single_consumption_even_through_a_copied_result_wrapper() -> None:
    permit = _permit()
    result = evidence_ledger.NewPostPermit(
        disposition="NEW_POST_PERMIT",
        permit=permit,
    )
    copied_result = copy.copy(result)
    assert copied_result.permit is permit

    result.permit.consume()
    with pytest.raises(RuntimeError, match="already consumed"):
        copied_result.permit.consume()


def test_consumed_permit_issues_one_non_authorizing_submitted_receipt() -> None:
    permit = _permit()
    with pytest.raises(RuntimeError, match="must be consumed"):
        permit.submitted_receipt("task-001", ProviderTaskState.QUEUED)

    permit.consume()
    receipt = permit.submitted_receipt("task-001", ProviderTaskState.QUEUED)
    assert receipt._provider_task_id == "task-001"
    assert receipt._provider_state == ProviderTaskState.QUEUED.value
    with pytest.raises(AttributeError, match="immutable"):
        _set_attribute(permit, "_authorization_sha256", _sha256("replacement"))
    with pytest.raises(AttributeError, match="immutable"):
        _set_attribute(receipt, "_provider_task_id", "task-replacement")
    with pytest.raises(AttributeError, match="immutable"):
        _delete_attribute(permit, "_authorization_sha256")
    with pytest.raises(AttributeError, match="immutable"):
        _delete_attribute(receipt, "_provider_task_id")
    with pytest.raises(RuntimeError, match="already issued"):
        permit.submitted_receipt("task-001", ProviderTaskState.QUEUED)
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.copy(receipt)
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.deepcopy(receipt)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(receipt)


def test_submitted_receipt_rejects_malformed_task_or_loose_provider_state() -> None:
    permit = _permit()
    permit.consume()
    with pytest.raises(ValueError, match="task ID is malformed"):
        permit.submitted_receipt("task/unsafe", ProviderTaskState.QUEUED)
    with pytest.raises(TypeError, match="must be a ProviderTaskState"):
        permit.submitted_receipt("task-001", "queued")  # type: ignore[arg-type]


def test_claim_result_types_are_closed_frozen_and_have_exact_dispositions() -> None:
    permit_result = evidence_ledger.NewPostPermit(
        disposition="NEW_POST_PERMIT",
        permit=_permit(),
    )
    owned = evidence_ledger.ResumeOwnedTask(
        disposition="RESUME_OWNED_TASK",
        run_id="run-001",
        job_id="job-001",
        attempt=1,
        provider_task_id="task-001",
        authorization_sha256=_sha256("authorization"),
        request_fingerprint=_sha256("request"),
        submitted_at=AUTHORIZED_AT,
    )
    human_gate = evidence_ledger.ClaimHumanGate(
        disposition="HUMAN_GATE",
        failure=evidence_ledger.ClaimFailure.SUBMISSION_UNKNOWN,
        detail="no safely owned task",
    )

    assert set(get_args(evidence_ledger.CanaryClaimResult)) == {
        evidence_ledger.NewPostPermit,
        evidence_ledger.ResumeOwnedTask,
        evidence_ledger.ClaimHumanGate,
    }
    assert permit_result.disposition == "NEW_POST_PERMIT"
    assert owned.disposition == "RESUME_OWNED_TASK"
    assert human_gate.disposition == "HUMAN_GATE"
    with pytest.raises(FrozenInstanceError):
        _set_attribute(human_gate, "detail", "changed")


def test_private_capabilities_are_not_public_exports() -> None:
    public = set(evidence_ledger.__all__)
    assert {
        "CanaryClaimResult",
        "ClaimFailure",
        "ClaimHumanGate",
        "NewPostPermit",
        "PostgresCanaryLedgerStore",
        "ResumeOwnedTask",
    } <= public
    assert {
        "_EvidenceBoundClaimBinding",
        "_NewPostPermit",
        "_PERMIT_FACTORY",
        "_PendingPermit",
        "_SubmittedClaimReceipt",
    }.isdisjoint(public)


def test_positive_entitlement_and_authorization_registries_remain_empty() -> None:
    assert REVIEWED_ARK_ENTITLEMENT_EVIDENCE == ()
    assert REVIEWED_EVIDENCE_AUTHORIZATIONS == ()


def test_ledger_module_has_no_runtime_provider_worker_temporal_or_http_imports() -> None:
    module_path = evidence_ledger.__file__
    assert module_path is not None
    tree = ast.parse(Path(module_path).read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    dynamic_import_calls: list[int] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                dynamic_import_calls.append(node.lineno)
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                dynamic_import_calls.append(node.lineno)

    forbidden_prefixes = (
        "aiohttp",
        "http",
        "httpx",
        "requests",
        "socket",
        "temporalio",
        "urllib",
        "sdc.ark_provider",
        "sdc.client",
        "sdc.provider",
        "sdc.runtime",
        "sdc.worker",
    )
    forbidden_imports = {
        imported
        for imported in imported_modules
        if any(
            imported == prefix or imported.startswith(f"{prefix}.") for prefix in forbidden_prefixes
        )
    }
    registry_imports = {imported for imported in imported_modules if imported.endswith("_registry")}

    assert forbidden_imports == set()
    assert registry_imports == set()
    assert dynamic_import_calls == []
