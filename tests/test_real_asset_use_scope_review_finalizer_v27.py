from __future__ import annotations

import ast
import inspect
import json
import os
from dataclasses import FrozenInstanceError, dataclass
from pathlib import Path
from typing import get_type_hints

import pytest
from test_real_asset_rights_manifest_finalizer_v25 import (
    MANIFEST_AT,
    SyntheticManifestClosure,
)
from test_real_asset_rights_manifest_finalizer_v25 import (
    closure as _manifest_closure_fixture,
)

import sdc.real_asset_use_scope_review_finalizer_v27 as review_boundary
from sdc.real_asset_rights_manifest_finalizer_v25 import (
    TrustedLocalRightsManifestFinalizationError,
    finalize_manifest,
)
from sdc.real_asset_use_plan_finalizer_v27 import (
    TrustedLocalUsePlanPaths,
    finalize_use_plan,
    inspect_use_plan_ready,
)
from sdc.real_asset_use_plan_v26 import (
    USE_PLAN_V1_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetUsePlanV1,
)
from sdc.real_asset_use_scope_review_finalizer_v27 import (
    TrustedLocalUsePlanArtifactPaths,
    TrustedLocalUseScopeReviewFinalizationError,
    TrustedLocalUseScopeReviewInstructionPaths,
    TrustedLocalUseScopeReviewQuarantineRequired,
    TrustedLocalUseScopeReviewRequestPaths,
    TrustedLocalUseScopeReviewVerificationPaths,
    UseScopeReviewInstructionPreflightV27,
    UseScopeReviewRequestPreflightV27,
    finalize_review_record,
    main,
    preflight_review_instruction,
    preflight_review_request,
    verify_review_record,
)
from sdc.real_asset_use_scope_review_v26 import (
    CreativeSampleRealAssetUseScopeReviewRecordV1,
    RealAssetUseScopeReviewV26Error,
    parse_use_scope_review_record_v1_json,
)

REQUESTED_AT = "2026-08-19T12:01:00Z"
EVALUATED_AT = "2026-08-19T12:02:00Z"
_GATES = (
    "COPYRIGHT_USE_SCOPE",
    "LIKENESS_USE_SCOPE",
    "PRIVACY_USE_SCOPE",
    "TERRITORY_USE_SCOPE",
    "CONTENT_ROLE_USE_SCOPE",
    "OFFLINE_ONLY_RESTRICTIONS",
)


@dataclass(frozen=True, slots=True)
class SyntheticReviewClosure:
    manifest_closure: SyntheticManifestClosure
    plan_paths: TrustedLocalUsePlanPaths
    plan_artifact_paths: TrustedLocalUsePlanArtifactPaths
    plan: CreativeSampleRealAssetUsePlanV1
    request_paths: TrustedLocalUseScopeReviewRequestPaths
    instruction_paths: TrustedLocalUseScopeReviewInstructionPaths
    verification_paths: TrustedLocalUseScopeReviewVerificationPaths
    maker_input: Path
    checker_input: Path


def _canonical(value: object) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _write_private_json(path: Path, value: object) -> None:
    raw = _canonical(value)
    if path.exists():
        path.unlink()
    descriptor: int | None = None
    parent_guard: tuple[int, bool] | None = None
    try:
        if os.name == "nt":
            identity = review_boundary._plan_boundary._directory_identity(
                path.parent,
                field="synthetic authoring parent",
            )
            target = review_boundary._plan_boundary._OutputTarget(
                path=path,
                parent=path.parent,
                parent_physical_identity=(identity[0], identity[1]),
            )
            parent_guard = review_boundary._plan_boundary._acquire_parent_guard(target)
            descriptor = review_boundary._plan_boundary._open_windows_exclusive_artifact(
                target,
                parent_guard[0],
            )
        else:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600,
            )
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            assert written > 0
            offset += written
        os.fsync(descriptor)
        review_boundary._plan_boundary._assert_owner_only_descriptor(descriptor)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_guard is not None:
            if parent_guard[1]:
                review_boundary._plan_boundary._manifest_boundary._close_windows_handle(
                    parent_guard[0]
                )
            else:
                os.close(parent_guard[0])


def _all_pass_checker() -> dict[str, object]:
    return {
        "checker_basis": "六项离线用途范围均与精确计划及权利证据一致。",
        "disposition": "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY",
        "gate_results": [{"approved": True, "gate": gate, "note": None} for gate in _GATES],
    }


def _negative_checker(disposition: str) -> dict[str, object]:
    gates = [{"approved": True, "gate": gate, "note": None} for gate in _GATES]
    gates[0] = {
        "approved": False,
        "gate": "COPYRIGHT_USE_SCOPE",
        "note": "合成测试：版权用途范围仍需修订。",
    }
    return {
        "checker_basis": "合成测试中的负面审查事实。",
        "disposition": disposition,
        "gate_results": gates,
    }


@pytest.fixture
def review_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> SyntheticReviewClosure:
    manifest_factory = _manifest_closure_fixture.__wrapped__
    manifest_closure: SyntheticManifestClosure = manifest_factory(tmp_path, monkeypatch)

    manifest_parent = (tmp_path / "rights-manifest-area").resolve()
    manifest_parent.mkdir()
    manifest_path = manifest_parent / "rights-manifest-v2.json"
    finalize_manifest(manifest_closure.paths, manifest_path, manifest_at=MANIFEST_AT)

    plan_paths = TrustedLocalUsePlanPaths(
        manifest_sources=manifest_closure.paths,
        rights_manifest=manifest_path,
    )
    readiness = inspect_use_plan_ready(plan_paths)
    plan_parent = (tmp_path / "use-plan-area").resolve()
    plan_parent.mkdir()
    plan_path = plan_parent / "use-plan-v1.json"
    plan = finalize_use_plan(
        plan_paths,
        plan_path,
        expected_plan_id=readiness.plan_id,
        expected_plan_sha256=readiness.plan_sha256,
    )
    plan_artifact_paths = TrustedLocalUsePlanArtifactPaths(
        sources=plan_paths,
        use_plan=plan_path,
    )

    maker_identity_parent = (tmp_path / "maker-identity-area").resolve()
    maker_identity_parent.mkdir()
    maker_identity = maker_identity_parent / "maker-reference.bin"
    maker_identity.write_bytes(b"synthetic maker identity reference v2.7")
    maker_input_parent = (tmp_path / "maker-authoring-area").resolve()
    maker_input_parent.mkdir()
    maker_input = maker_input_parent / "maker-input.json"
    _write_private_json(
        maker_input,
        {"request_basis": "请求审查精确离线用途计划与既有权利范围的一致性。"},
    )

    checker_identity_parent = (tmp_path / "checker-identity-area").resolve()
    checker_identity_parent.mkdir()
    checker_identity = checker_identity_parent / "checker-reference.bin"
    checker_identity.write_bytes(b"synthetic checker identity reference v2.7")
    checker_input_parent = (tmp_path / "checker-authoring-area").resolve()
    checker_input_parent.mkdir()
    checker_input = checker_input_parent / "checker-input.json"
    _write_private_json(checker_input, _all_pass_checker())

    request_paths = TrustedLocalUseScopeReviewRequestPaths(
        plan=plan_artifact_paths,
        maker_identity_ref=maker_identity,
        maker_input=maker_input,
    )
    instruction_paths = TrustedLocalUseScopeReviewInstructionPaths(
        request=request_paths,
        checker_identity_ref=checker_identity,
        checker_input=checker_input,
    )
    verification_paths = TrustedLocalUseScopeReviewVerificationPaths(
        plan=plan_artifact_paths,
        maker_identity_ref=maker_identity,
        checker_identity_ref=checker_identity,
    )
    return SyntheticReviewClosure(
        manifest_closure=manifest_closure,
        plan_paths=plan_paths,
        plan_artifact_paths=plan_artifact_paths,
        plan=plan,
        request_paths=request_paths,
        instruction_paths=instruction_paths,
        verification_paths=verification_paths,
        maker_input=maker_input,
        checker_input=checker_input,
    )


def _approved_anchors(
    closure: SyntheticReviewClosure,
) -> tuple[UseScopeReviewRequestPreflightV27, UseScopeReviewInstructionPreflightV27]:
    request = preflight_review_request(closure.request_paths, requested_at=REQUESTED_AT)
    instruction = preflight_review_instruction(
        closure.instruction_paths,
        requested_at=REQUESTED_AT,
        evaluated_at=EVALUATED_AT,
        expected_request_id=request.request_id,
        expected_request_sha256=request.request_sha256,
    )
    return request, instruction


def _record_output(tmp_path: Path, name: str = "review-record-v1.json") -> Path:
    parent = (tmp_path / "review-record-area").resolve()
    parent.mkdir(exist_ok=True)
    return parent / name


def _cli_plan_args(paths: TrustedLocalUsePlanPaths) -> list[str]:
    manifest = paths.manifest_sources
    request = manifest.decision_inputs.request_inputs
    values = [
        "--pack-root",
        str(request.pack_root),
        "--pack-manifest",
        str(request.pack_manifest),
    ]
    for path in request.media_paths:
        values.extend(("--media-path", str(path)))
    values.extend(
        (
            "--evidence",
            str(request.evidence_bundle),
            "--reviewer-a",
            str(request.reviewer_a),
            "--reviewer-b",
            str(request.reviewer_b),
            "--pair-check",
            str(request.pair_check),
            "--evidence-retained-record",
            str(request.evidence_retained_record),
            "--evidence-preparer-ref",
            str(request.evidence_preparer_ref),
            "--reviewer-a-retained-record",
            str(request.reviewer_a_retained_record),
            "--reviewer-b-retained-record",
            str(request.reviewer_b_retained_record),
            "--qualification-request",
            str(manifest.decision_inputs.request),
            "--qualifier-ref",
            str(manifest.decision_inputs.qualifier_ref),
            "--qualification-instruction",
            str(manifest.decision_inputs.qualifier_decision_record),
            "--qualification-decision",
            str(manifest.decision),
            "--rights-manifest-file",
            str(paths.rights_manifest),
        )
    )
    return values


def _cli_request_args(closure: SyntheticReviewClosure) -> list[str]:
    return [
        *_cli_plan_args(closure.plan_paths),
        "--use-plan-file",
        str(closure.plan_artifact_paths.use_plan),
        "--maker-identity-ref",
        str(closure.request_paths.maker_identity_ref),
        "--maker-input",
        str(closure.maker_input),
        "--requested-at",
        REQUESTED_AT,
    ]


def _exact_cli_payload(**members: object) -> bytes:
    payload = {
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
        "provider_state": "NOT_AUTHORIZED",
        **members,
    }
    return (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def _finalize(
    closure: SyntheticReviewClosure,
    output: Path,
) -> CreativeSampleRealAssetUseScopeReviewRecordV1:
    request, instruction = _approved_anchors(closure)
    return finalize_review_record(
        closure.instruction_paths,
        output,
        requested_at=REQUESTED_AT,
        evaluated_at=EVALUATED_AT,
        expected_request_id=request.request_id,
        expected_request_sha256=request.request_sha256,
        expected_instruction_id=instruction.instruction_id,
        expected_instruction_sha256=instruction.instruction_sha256,
        expected_decision_id=instruction.decision_id,
        expected_decision_sha256=instruction.decision_sha256,
        expected_record_id=instruction.record_id,
        expected_record_sha256=instruction.record_sha256,
    )


def test_public_surface_signatures_and_frozen_operational_values() -> None:
    assert review_boundary.__all__ == [
        "TrustedLocalUsePlanArtifactPaths",
        "TrustedLocalUseScopeReviewRequestPaths",
        "TrustedLocalUseScopeReviewInstructionPaths",
        "TrustedLocalUseScopeReviewVerificationPaths",
        "UseScopeReviewRequestPreflightV27",
        "UseScopeReviewInstructionPreflightV27",
        "TrustedLocalUseScopeReviewFinalizationError",
        "TrustedLocalUseScopeReviewQuarantineRequired",
        "preflight_review_request",
        "preflight_review_instruction",
        "finalize_review_record",
        "verify_review_record",
        "main",
    ]
    assert issubclass(
        TrustedLocalUseScopeReviewQuarantineRequired,
        TrustedLocalUseScopeReviewFinalizationError,
    )
    dataclass_fields = {
        TrustedLocalUsePlanArtifactPaths: ("sources", "use_plan"),
        TrustedLocalUseScopeReviewRequestPaths: (
            "plan",
            "maker_identity_ref",
            "maker_input",
        ),
        TrustedLocalUseScopeReviewInstructionPaths: (
            "request",
            "checker_identity_ref",
            "checker_input",
        ),
        TrustedLocalUseScopeReviewVerificationPaths: (
            "plan",
            "maker_identity_ref",
            "checker_identity_ref",
        ),
        UseScopeReviewRequestPreflightV27: (
            "status",
            "request_id",
            "request_sha256",
        ),
        UseScopeReviewInstructionPreflightV27: (
            "status",
            "instruction_id",
            "instruction_sha256",
            "decision_id",
            "decision_sha256",
            "record_id",
            "record_sha256",
        ),
    }
    for dataclass_type, fields in dataclass_fields.items():
        assert dataclass_type.__dataclass_params__.frozen is True
        assert dataclass_type.__slots__ == fields
        assert tuple(get_type_hints(dataclass_type)) == fields
    assert str(inspect.signature(preflight_review_request)) == (
        "(paths: 'TrustedLocalUseScopeReviewRequestPaths', *, requested_at: 'str') -> "
        "'UseScopeReviewRequestPreflightV27'"
    )
    assert str(inspect.signature(preflight_review_instruction)) == (
        "(paths: 'TrustedLocalUseScopeReviewInstructionPaths', *, requested_at: 'str', "
        "evaluated_at: 'str', expected_request_id: 'str', expected_request_sha256: 'str') "
        "-> 'UseScopeReviewInstructionPreflightV27'"
    )
    assert str(inspect.signature(finalize_review_record)) == (
        "(paths: 'TrustedLocalUseScopeReviewInstructionPaths', output_path: 'Path', *, "
        "requested_at: 'str', evaluated_at: 'str', expected_request_id: 'str', "
        "expected_request_sha256: 'str', expected_instruction_id: 'str', "
        "expected_instruction_sha256: 'str', expected_decision_id: 'str', "
        "expected_decision_sha256: 'str', expected_record_id: 'str', "
        "expected_record_sha256: 'str') -> "
        "'CreativeSampleRealAssetUseScopeReviewRecordV1'"
    )
    assert str(inspect.signature(verify_review_record)) == (
        "(paths: 'TrustedLocalUseScopeReviewVerificationPaths', record_path: 'Path') -> "
        "'CreativeSampleRealAssetUseScopeReviewRecordV1'"
    )
    assert str(inspect.signature(main)) == "(argv: 'list[str] | None' = None) -> 'int'"
    summary = UseScopeReviewRequestPreflightV27(
        "REVIEW_REQUEST_READY_FOR_CHECKER_PREFLIGHT", "request", "0" * 64
    )
    with pytest.raises(FrozenInstanceError):
        summary.status = "changed"  # type: ignore[misc]


def test_review_ast_prohibits_clock_network_discovery_and_authority() -> None:
    source = inspect.getsource(review_boundary)
    tree = ast.parse(source)
    for token in (
        ".glob(",
        ".rglob(",
        "os.walk(",
        "os.scandir(",
        "datetime.now(",
        "datetime.utcnow(",
        "requests.",
        "httpx.",
        "observed_at",
        "compile_use_scope_review_decision_v1",
        "verify_use_scope_review_current_v1",
    ):
        assert token not in source
    forbidden_import_fragments = {
        "authorization",
        "entitlement",
        "ledger",
        "migration",
        "provider",
        "runtime",
        "temporal",
        "worker",
    }
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    assert not {
        name
        for name in imports
        if any(fragment in name.casefold() for fragment in forbidden_import_fragments)
    }
    commands = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_parser"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }
    assert commands == {
        "preflight-review-request",
        "preflight-review-instruction",
        "finalize-review-record",
        "verify-review-record",
    }


def test_positive_three_stage_flow_creates_only_one_canonical_record(
    review_closure: SyntheticReviewClosure,
    tmp_path: Path,
) -> None:
    before = set(tmp_path.rglob("*"))
    request, instruction = _approved_anchors(review_closure)
    after_preflight = set(tmp_path.rglob("*"))
    assert after_preflight == before
    assert request.status == "REVIEW_REQUEST_READY_FOR_CHECKER_PREFLIGHT"
    assert instruction.status == "REVIEW_INSTRUCTION_READY_FOR_RECORD_FINALIZATION"

    output = _record_output(tmp_path)
    record = finalize_review_record(
        review_closure.instruction_paths,
        output,
        requested_at=REQUESTED_AT,
        evaluated_at=EVALUATED_AT,
        expected_request_id=request.request_id,
        expected_request_sha256=request.request_sha256,
        expected_instruction_id=instruction.instruction_id,
        expected_instruction_sha256=instruction.instruction_sha256,
        expected_decision_id=instruction.decision_id,
        expected_decision_sha256=instruction.decision_sha256,
        expected_record_id=instruction.record_id,
        expected_record_sha256=instruction.record_sha256,
    )
    assert output.read_bytes() == _canonical(record)
    assert parse_use_scope_review_record_v1_json(output.read_bytes()) == record
    assert record.request.request_id == request.request_id
    assert record.instruction.instruction_id == instruction.instruction_id
    assert record.decision.decision_id == instruction.decision_id
    assert record.record_id == instruction.record_id
    assert record.current_gate if hasattr(record, "current_gate") else True
    assert record.decision.execution_authorized is False
    assert record.decision.provider_requests == record.decision.posts_allowed == 0

    verified = verify_review_record(review_closure.verification_paths, output)
    assert verified == record


def test_instruction_guard_runs_before_instruction_builder(
    review_closure: SyntheticReviewClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = preflight_review_request(review_closure.request_paths, requested_at=REQUESTED_AT)

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("Instruction builder must not run")

    monkeypatch.setattr(review_boundary, "build_use_scope_review_instruction_v1", forbidden)
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        preflight_review_instruction(
            review_closure.instruction_paths,
            requested_at=REQUESTED_AT,
            evaluated_at=EVALUATED_AT,
            expected_request_id=request.request_id,
            expected_request_sha256="0" * 64,
        )


def test_finalize_builder_and_anchor_guard_order_is_exact(
    review_closure: SyntheticReviewClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, instruction = _approved_anchors(review_closure)
    events: list[str] = []
    original_build_request = review_boundary._build_request
    original_require_anchor = review_boundary._require_anchor
    original_build_instruction = review_boundary._build_instruction
    original_build_record = review_boundary.build_use_scope_review_record_v1

    def build_request(*args: object, **kwargs: object) -> object:
        events.append("Request build")
        return original_build_request(*args, **kwargs)

    def require_anchor(*args: object, **kwargs: object) -> None:
        field = kwargs.get("field")
        assert field in {"Request", "Instruction", "Decision", "Record"}
        events.append(f"{field} guard")
        original_require_anchor(*args, **kwargs)

    def build_instruction(*args: object, **kwargs: object) -> object:
        events.append("Instruction build")
        return original_build_instruction(*args, **kwargs)

    def build_record(*args: object, **kwargs: object) -> object:
        events.append("Record build")
        return original_build_record(*args, **kwargs)

    monkeypatch.setattr(review_boundary, "_build_request", build_request)
    monkeypatch.setattr(review_boundary, "_require_anchor", require_anchor)
    monkeypatch.setattr(review_boundary, "_build_instruction", build_instruction)
    monkeypatch.setattr(
        review_boundary,
        "build_use_scope_review_record_v1",
        build_record,
    )
    output = _record_output(tmp_path)
    finalized = finalize_review_record(
        review_closure.instruction_paths,
        output,
        requested_at=REQUESTED_AT,
        evaluated_at=EVALUATED_AT,
        expected_request_id=request.request_id,
        expected_request_sha256=request.request_sha256,
        expected_instruction_id=instruction.instruction_id,
        expected_instruction_sha256=instruction.instruction_sha256,
        expected_decision_id=instruction.decision_id,
        expected_decision_sha256=instruction.decision_sha256,
        expected_record_id=instruction.record_id,
        expected_record_sha256=instruction.record_sha256,
    )
    assert output.read_bytes() == _canonical(finalized)
    assert events == [
        "Request build",
        "Request guard",
        "Instruction build",
        "Instruction guard",
        "Record build",
        "Decision guard",
        "Record guard",
    ]
    assert events.count("Record build") == 1


@pytest.mark.parametrize(
    "field",
    (
        "expected_request_id",
        "expected_request_sha256",
        "expected_instruction_id",
        "expected_instruction_sha256",
        "expected_decision_id",
        "expected_decision_sha256",
        "expected_record_id",
        "expected_record_sha256",
    ),
)
def test_each_wrong_anchor_fails_before_output_creation(
    review_closure: SyntheticReviewClosure,
    tmp_path: Path,
    field: str,
) -> None:
    request, instruction = _approved_anchors(review_closure)
    values = {
        "expected_request_id": request.request_id,
        "expected_request_sha256": request.request_sha256,
        "expected_instruction_id": instruction.instruction_id,
        "expected_instruction_sha256": instruction.instruction_sha256,
        "expected_decision_id": instruction.decision_id,
        "expected_decision_sha256": instruction.decision_sha256,
        "expected_record_id": instruction.record_id,
        "expected_record_sha256": instruction.record_sha256,
    }
    original = values[field]
    values[field] = ("f" if original[-1] != "f" else "e").join((original[:-1], ""))
    output = _record_output(tmp_path)
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        finalize_review_record(
            review_closure.instruction_paths,
            output,
            requested_at=REQUESTED_AT,
            evaluated_at=EVALUATED_AT,
            **values,
        )
    assert not output.exists()


@pytest.mark.parametrize("disposition", ("NEEDS_REVISION", "REJECTED"))
def test_valid_negative_record_is_preserved_as_zero_authority_audit_fact(
    review_closure: SyntheticReviewClosure,
    tmp_path: Path,
    disposition: str,
) -> None:
    _write_private_json(review_closure.checker_input, _negative_checker(disposition))
    output = _record_output(tmp_path)
    record = _finalize(review_closure, output)
    assert record.decision.decision == disposition
    assert record.decision.eligible_for_separate_provider_proposal is False
    assert record.decision.execution_authorized is False
    assert record.decision.provider_state == "NOT_AUTHORIZED"
    assert verify_review_record(review_closure.verification_paths, output) == record


def test_verify_never_opens_authoring_inputs(
    review_closure: SyntheticReviewClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _record_output(tmp_path)
    record = _finalize(review_closure, output)
    review_closure.maker_input.unlink()
    review_closure.checker_input.unlink()

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("historical verification opened an authoring input")

    monkeypatch.setattr(review_boundary, "_read_maker_authoring", forbidden)
    monkeypatch.setattr(review_boundary, "_read_checker_authoring", forbidden)
    assert verify_review_record(review_closure.verification_paths, output) == record


@pytest.mark.parametrize(
    "mutator",
    (
        lambda value: {**value, "unexpected": False},
        lambda value: {key: item for key, item in value.items() if key != "request_basis"},
    ),
)
def test_maker_authoring_requires_exact_members(
    review_closure: SyntheticReviewClosure,
    mutator: object,
) -> None:
    value = {"request_basis": "合成请求依据。"}
    _write_private_json(review_closure.maker_input, mutator(value))  # type: ignore[operator]
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        preflight_review_request(review_closure.request_paths, requested_at=REQUESTED_AT)


@pytest.mark.parametrize("damage", ("missing-note", "reordered", "string-boolean"))
def test_checker_authoring_requires_explicit_typed_ordered_gate_members(
    review_closure: SyntheticReviewClosure,
    damage: str,
) -> None:
    value = _all_pass_checker()
    gates = value["gate_results"]
    assert isinstance(gates, list)
    if damage == "missing-note":
        del gates[0]["note"]
    elif damage == "reordered":
        gates[0], gates[1] = gates[1], gates[0]
    else:
        gates[0]["approved"] = "true"
    _write_private_json(review_closure.checker_input, value)
    request = preflight_review_request(review_closure.request_paths, requested_at=REQUESTED_AT)
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        preflight_review_instruction(
            review_closure.instruction_paths,
            requested_at=REQUESTED_AT,
            evaluated_at=EVALUATED_AT,
            expected_request_id=request.request_id,
            expected_request_sha256=request.request_sha256,
        )


def test_authoring_permissions_are_checked_before_first_read(
    review_closure: SyntheticReviewClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authoring_reads = 0

    if review_closure.maker_input.exists():
        review_closure.maker_input.unlink()
    review_closure.maker_input.write_bytes(
        _canonical({"request_basis": "合成测试中的宽权限输入。"})
    )
    if os.name != "nt":
        review_closure.maker_input.chmod(0o644)
    maker_identity = (
        review_closure.maker_input.stat().st_dev,
        review_closure.maker_input.stat().st_ino,
    )

    original_read = os.read

    def counted_read(descriptor: int, size: int) -> bytes:
        nonlocal authoring_reads
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) == maker_identity:
            authoring_reads += 1
        return original_read(descriptor, size)

    monkeypatch.setattr(os, "read", counted_read)
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        preflight_review_request(review_closure.request_paths, requested_at=REQUESTED_AT)
    assert authoring_reads == 0


def test_identity_digest_alias_and_same_identity_are_rejected(
    review_closure: SyntheticReviewClosure,
) -> None:
    review_closure.instruction_paths.checker_identity_ref.write_bytes(
        review_closure.request_paths.maker_identity_ref.read_bytes()
    )
    request = preflight_review_request(review_closure.request_paths, requested_at=REQUESTED_AT)
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        preflight_review_instruction(
            review_closure.instruction_paths,
            requested_at=REQUESTED_AT,
            evaluated_at=EVALUATED_AT,
            expected_request_id=request.request_id,
            expected_request_sha256=request.request_sha256,
        )


def _inject_hard_link_during_read(
    monkeypatch: pytest.MonkeyPatch,
    *,
    target: Path,
    link_path: Path,
) -> list[bool]:
    target_identity = (target.stat().st_dev, target.stat().st_ino)
    original_read = os.read
    triggered = [False]

    def read(descriptor: int, size: int) -> bytes:
        opened = os.fstat(descriptor)
        if not triggered[0] and (opened.st_dev, opened.st_ino) == target_identity:
            os.link(target, link_path)
            triggered[0] = True
        return original_read(descriptor, size)

    monkeypatch.setattr(os, "read", read)
    return triggered


def test_identity_link_count_drift_during_read_fails_closed(
    review_closure: SyntheticReviewClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    triggered = _inject_hard_link_during_read(
        monkeypatch,
        target=review_closure.request_paths.maker_identity_ref,
        link_path=review_closure.request_paths.maker_identity_ref.parent / "maker-link.bin",
    )
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        preflight_review_request(review_closure.request_paths, requested_at=REQUESTED_AT)
    assert triggered == [True]


def test_record_link_count_drift_fails_verify_without_reading_authoring(
    review_closure: SyntheticReviewClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _record_output(tmp_path)
    _finalize(review_closure, output)
    review_closure.maker_input.unlink()
    review_closure.checker_input.unlink()

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("verification must not read authoring input")

    monkeypatch.setattr(review_boundary, "_read_maker_authoring", forbidden)
    monkeypatch.setattr(review_boundary, "_read_checker_authoring", forbidden)
    triggered = _inject_hard_link_during_read(
        monkeypatch,
        target=output,
        link_path=output.parent / "record-link.json",
    )
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        verify_review_record(review_closure.verification_paths, output)
    assert triggered == [True]


def test_authoring_and_candidate_record_cannot_alias_plan_reserved_digests(
    review_closure: SyntheticReviewClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    representative_plan_digest = review_closure.plan.planned_spec_document_sha256
    reserved_targets = (
        USE_PLAN_V1_POLICY_DOCUMENT_SHA256,
        representative_plan_digest,
    )
    maker_raw = review_closure.maker_input.read_bytes()
    original_sha256 = review_boundary._sha256

    for reserved_digest in reserved_targets:
        with monkeypatch.context() as patch:
            patch.setattr(
                review_boundary,
                "_sha256",
                lambda raw, target=reserved_digest: (
                    target if raw == maker_raw else original_sha256(raw)
                ),
            )
            with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
                preflight_review_request(review_closure.request_paths, requested_at=REQUESTED_AT)

    request = preflight_review_request(review_closure.request_paths, requested_at=REQUESTED_AT)
    record_marker = b'"document_type": "sdc.creative-sample-real-asset-use-scope-review-record-v1"'
    for reserved_digest in reserved_targets:
        with monkeypatch.context() as patch:
            patch.setattr(
                review_boundary,
                "_sha256",
                lambda raw, target=reserved_digest: (
                    target if record_marker in raw else original_sha256(raw)
                ),
            )
            with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
                preflight_review_instruction(
                    review_closure.instruction_paths,
                    requested_at=REQUESTED_AT,
                    evaluated_at=EVALUATED_AT,
                    expected_request_id=request.request_id,
                    expected_request_sha256=request.request_sha256,
                )


def test_malformed_anchor_is_rejected_before_any_path_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("private paths must not be inspected")

    monkeypatch.setattr(review_boundary, "_normalize_instruction_paths", forbidden)
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        preflight_review_instruction(
            object(),  # type: ignore[arg-type]
            requested_at=REQUESTED_AT,
            evaluated_at=EVALUATED_AT,
            expected_request_id="malformed",
            expected_request_sha256="0" * 64,
        )


@pytest.mark.parametrize(
    ("requested_at", "evaluated_at"),
    (
        ("2026-08-19T11:59:59Z", EVALUATED_AT),
        (REQUESTED_AT, "2026-08-19T12:00:59Z"),
        (REQUESTED_AT, "2026-08-20T12:01:00Z"),
        ("2026-08-19T12:01:00.000Z", EVALUATED_AT),
    ),
)
def test_time_boundaries_fail_closed(
    review_closure: SyntheticReviewClosure,
    requested_at: str,
    evaluated_at: str,
) -> None:
    if requested_at == REQUESTED_AT:
        request = preflight_review_request(review_closure.request_paths, requested_at=REQUESTED_AT)
        with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
            preflight_review_instruction(
                review_closure.instruction_paths,
                requested_at=requested_at,
                evaluated_at=evaluated_at,
                expected_request_id=request.request_id,
                expected_request_sha256=request.request_sha256,
            )
    else:
        with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
            preflight_review_request(review_closure.request_paths, requested_at=requested_at)


def test_output_is_create_new_and_forbidden_filename_tokens_fail(
    review_closure: SyntheticReviewClosure,
    tmp_path: Path,
) -> None:
    existing = _record_output(tmp_path)
    existing.write_bytes(b"independent winner")
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        _finalize(review_closure, existing)
    assert existing.read_bytes() == b"independent winner"

    normalized = review_boundary._normalize_instruction_paths(review_closure.instruction_paths)
    accepted = existing.parent / "mixed-case-review-record.JSON"
    assert review_boundary._review_output_target(accepted, paths=normalized).path == accepted
    for name in (
        "review-pass-record.json",
        "review-needs-record.json",
        "review-rejected-record.json",
        "review-revision-record.json",
        "review-approved-record.json",
        "review-authorized-record.json",
        "review-paſs-record.json",
        "review-record.json:stream",
    ):
        forbidden = existing.parent / name
        with pytest.raises(
            (
                TrustedLocalUseScopeReviewFinalizationError,
                TrustedLocalRightsManifestFinalizationError,
            )
        ):
            review_boundary._review_output_target(forbidden, paths=normalized)
        assert not forbidden.exists()

    for token in ("latest", "CURRENT", "NeWeSt"):
        mutable_parent = (tmp_path / token).resolve()
        mutable_parent.mkdir()
        with pytest.raises(
            (
                TrustedLocalUseScopeReviewFinalizationError,
                TrustedLocalRightsManifestFinalizationError,
            )
        ):
            review_boundary._review_output_target(
                mutable_parent / "review-record-v1.json",
                paths=normalized,
            )


def test_postwrite_failure_rolls_back_without_a_valid_record(
    review_closure: SyntheticReviewClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _record_output(tmp_path)
    request, instruction = _approved_anchors(review_closure)
    original_capture = review_boundary._capture_instruction_snapshot
    calls = 0

    def fail_postwrite(
        paths: TrustedLocalUseScopeReviewInstructionPaths,
    ) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TrustedLocalUseScopeReviewFinalizationError("synthetic postwrite failure")
        return original_capture(paths)

    monkeypatch.setattr(review_boundary, "_capture_instruction_snapshot", fail_postwrite)
    with pytest.raises(TrustedLocalUseScopeReviewFinalizationError):
        finalize_review_record(
            review_closure.instruction_paths,
            output,
            requested_at=REQUESTED_AT,
            evaluated_at=EVALUATED_AT,
            expected_request_id=request.request_id,
            expected_request_sha256=request.request_sha256,
            expected_instruction_id=instruction.instruction_id,
            expected_instruction_sha256=instruction.instruction_sha256,
            expected_decision_id=instruction.decision_id,
            expected_decision_sha256=instruction.decision_sha256,
            expected_record_id=instruction.record_id,
            expected_record_sha256=instruction.record_sha256,
        )
    if output.exists():
        with pytest.raises(RealAssetUseScopeReviewV26Error):
            parse_use_scope_review_record_v1_json(output.read_bytes())


def test_quarantine_error_is_translated_to_review_type(
    review_closure: SyntheticReviewClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _record_output(tmp_path)

    def quarantine(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise review_boundary._plan_boundary.TrustedLocalUsePlanQuarantineRequired(
            "synthetic quarantine"
        )

    monkeypatch.setattr(review_boundary._plan_boundary, "_create_new_artifact", quarantine)
    with pytest.raises(TrustedLocalUseScopeReviewQuarantineRequired):
        _finalize(review_closure, output)


def test_cli_malformed_expected_value_fails_before_path_construction(
    capfdbinary: pytest.CaptureFixture[bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(args: object) -> None:
        del args
        raise AssertionError("private path construction must not run")

    monkeypatch.setattr(review_boundary, "_instruction_paths_from_namespace", forbidden)
    result = main(
        [
            "preflight-review-instruction",
            "--expected-request-id",
            "malformed",
        ]
    )
    captured = capfdbinary.readouterr()
    assert result == 2
    assert captured.out == b""
    assert captured.err == b'{"error":"FAILED_CLOSED"}\n'


def test_each_cli_success_is_exact_utf8_json_with_one_lf(
    review_closure: SyntheticReviewClosure,
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    request_args = _cli_request_args(review_closure)
    assert main(["preflight-review-request", *request_args]) == 0
    captured = capfdbinary.readouterr()
    assert captured.err == b""
    request_payload = json.loads(captured.out)
    assert captured.out == _exact_cli_payload(**request_payload)
    assert request_payload["operation"] == "preflight-review-request"
    assert request_payload["status"] == "REVIEW_REQUEST_READY_FOR_CHECKER_PREFLIGHT"

    instruction_args = [
        *request_args,
        "--expected-request-id",
        request_payload["request_id"],
        "--expected-request-sha256",
        request_payload["request_sha256"],
        "--checker-identity-ref",
        str(review_closure.instruction_paths.checker_identity_ref),
        "--checker-input",
        str(review_closure.checker_input),
        "--evaluated-at",
        EVALUATED_AT,
    ]
    assert main(["preflight-review-instruction", *instruction_args]) == 0
    captured = capfdbinary.readouterr()
    assert captured.err == b""
    instruction_payload = json.loads(captured.out)
    assert captured.out == _exact_cli_payload(**instruction_payload)
    assert instruction_payload["operation"] == "preflight-review-instruction"

    output = _record_output(tmp_path)
    finalize_args = [
        *instruction_args,
        "--expected-instruction-id",
        instruction_payload["instruction_id"],
        "--expected-instruction-sha256",
        instruction_payload["instruction_sha256"],
        "--expected-decision-id",
        instruction_payload["decision_id"],
        "--expected-decision-sha256",
        instruction_payload["decision_sha256"],
        "--expected-record-id",
        instruction_payload["record_id"],
        "--expected-record-sha256",
        instruction_payload["record_sha256"],
        "--output",
        str(output),
    ]
    assert main(["finalize-review-record", *finalize_args]) == 0
    captured = capfdbinary.readouterr()
    assert captured.err == b""
    assert captured.out == _exact_cli_payload(
        operation="finalize-review-record",
        status="USE_SCOPE_REVIEW_RECORD_FINALIZED",
    )

    verify_args = [
        *_cli_plan_args(review_closure.plan_paths),
        "--use-plan-file",
        str(review_closure.plan_artifact_paths.use_plan),
        "--maker-identity-ref",
        str(review_closure.request_paths.maker_identity_ref),
        "--checker-identity-ref",
        str(review_closure.instruction_paths.checker_identity_ref),
        "--review-record-file",
        str(output),
    ]
    assert main(["verify-review-record", *verify_args]) == 0
    captured = capfdbinary.readouterr()
    assert captured.err == b""
    assert captured.out == _exact_cli_payload(
        operation="verify-review-record",
        status="USE_SCOPE_REVIEW_RECORD_HISTORICALLY_VERIFIED",
    )

    rejected_argv = (
        ["preflight-review-request", *request_args, "--force"],
        [
            "preflight-review-request",
            *request_args,
            "--maker-input",
            str(review_closure.maker_input),
        ],
        [
            "preflight-review-request",
            *_cli_plan_args(review_closure.plan_paths),
            "--use-plan-file",
            str(review_closure.plan_artifact_paths.use_plan),
            "--maker-identi",
            str(review_closure.request_paths.maker_identity_ref),
        ],
        [
            "preflight-review-instruction",
            *instruction_args,
            "--expected-request-id",
            request_payload["request_id"],
        ],
    )
    for argv in rejected_argv:
        assert main(argv) == 2
        captured = capfdbinary.readouterr()
        assert captured.out == b""
        assert captured.err == b'{"error":"FAILED_CLOSED"}\n'


def test_cli_rejects_unreviewed_bypass_and_quarantine_is_exact(
    capfdbinary: pytest.CaptureFixture[bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert main(["verify-review-record", "--force"]) == 2
    captured = capfdbinary.readouterr()
    assert captured.out == b""
    assert captured.err == b'{"error":"FAILED_CLOSED"}\n'

    assert main(["--help"]) == 2
    captured = capfdbinary.readouterr()
    assert captured.out == b""
    assert captured.err == b'{"error":"FAILED_CLOSED"}\n'

    def quarantine(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise TrustedLocalUseScopeReviewQuarantineRequired("synthetic")

    monkeypatch.setattr(review_boundary, "verify_review_record", quarantine)
    monkeypatch.setattr(
        review_boundary,
        "_plan_artifact_paths_from_namespace",
        lambda args: object(),
    )
    # Parsing still requires the exact reviewed option set; exercise direct summary mapping instead.
    assert (
        review_boundary._failure_summary("ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED")
        == '{"error":"ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"}'
    )
