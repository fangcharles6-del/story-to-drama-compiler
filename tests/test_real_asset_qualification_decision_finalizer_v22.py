from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from pydantic import ValidationError

import sdc.real_asset_qualification_decision_finalizer_v22 as finalizer_module
import sdc.real_asset_qualification_decision_instruction_v22 as instruction_module
import sdc.real_asset_qualification_preparer_v21 as preparer_module
from sdc.compiler import stable_id
from sdc.real_asset_intake import (
    CreativeSampleFrozenRealAssetPackManifest,
    FrozenRealAssetDescriptor,
    FrozenRealAssetPack,
    RealAudioTechnicalRecord,
    RealImageTechnicalRecord,
    build_real_asset_intake_template,
)
from sdc.real_asset_qualification_decision_finalizer_v22 import (
    TrustedLocalDecisionFinalizationError,
    TrustedLocalDecisionPaths,
    TrustedLocalDecisionQuarantineRequired,
    finalize_decision,
    inspect_decision_ready,
    main,
    verify_decision,
)
from sdc.real_asset_qualification_decision_instruction_v22 import (
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
)
from sdc.real_asset_qualification_preparer_v21 import (
    TrustedLocalRequestPaths,
    prepare_request,
)
from sdc.real_asset_qualification_v2 import (
    QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
    QUALIFICATION_V2_POLICY_ID,
    QUALIFICATION_V2_POLICY_VERSION,
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationRequestV2,
    RealAssetQualificationDecisionV2,
    RealAssetQualificationIssueCodeV2,
    RealAssetQualificationV2Error,
    parse_real_asset_qualification_decision_v2_json,
)
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
    build_real_asset_human_findings_v2,
    build_real_asset_human_pack_review_v2,
    build_real_asset_rights_evidence_bundle_v2,
    finalize_real_asset_review_pair_v2,
)

REQUESTED_AT = "2026-08-18T10:30:00Z"
DECISION_AT = "2026-08-18T10:40:00Z"
OBSERVED_AT = "2026-08-18T10:45:00Z"
REVIEW_A_AT = "2026-08-17T10:00:00Z"
REVIEW_B_AT = "2026-08-17T10:10:00Z"
EVALUATED_AT = "2026-08-17T11:00:00Z"
VALID_UNTIL = "2026-08-20T00:00:00Z"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_payload(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _canonical_document(value: object) -> bytes:
    assert hasattr(value, "model_dump")
    return (
        json.dumps(
            value.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode()


def _technical_digest(
    *,
    kind: str,
    media_sha256: str,
    media_size_bytes: int,
    profile: str,
    evidence: RealImageTechnicalRecord | RealAudioTechnicalRecord,
) -> str:
    return _sha(
        b"sdc:real-asset-technical-record:v1\0"
        + _canonical_payload(
            {
                "kind": kind,
                "media_sha256": media_sha256,
                "media_size_bytes": media_size_bytes,
                "profile": profile,
                "evidence": evidence.model_dump(mode="json"),
            }
        )
    )


def _make_pack() -> tuple[CreativeSampleFrozenRealAssetPackManifest, tuple[bytes, ...]]:
    template = build_real_asset_intake_template()
    media_bytes = tuple(
        f"synthetic-decision-media-{ordinal}:".encode()
        + bytes([ordinal + 1]) * (90 + ordinal)
        for ordinal in range(14)
    )
    descriptors: list[FrozenRealAssetDescriptor] = []
    for requirement, raw in zip(template.requirements, media_bytes, strict=True):
        media_sha256 = _sha(raw)
        if requirement.kind == "IMAGE":
            image = RealImageTechnicalRecord(
                width=512,
                height=512,
                color_space="RGB",
                distinct_color_count=256,
            )
            audio = None
            technical: RealImageTechnicalRecord | RealAudioTechnicalRecord = image
            duration_ms = 0
        else:
            duration_ms = 72_000 if requirement.kind == "BGM" else 250
            image = None
            audio = RealAudioTechnicalRecord(
                channels=2 if requirement.kind == "BGM" else 1,
                duration_ms=duration_ms,
                sample_count=48_000 * duration_ms // 1000,
                rms_millidbfs=-12_000,
                sample_peak_millidbfs=-1_000,
                silence_ppm=10_000,
            )
            technical = audio
        descriptors.append(
            FrozenRealAssetDescriptor(
                ordinal=requirement.ordinal,
                requirement_id=requirement.requirement_id,
                kind=requirement.kind,
                subject_id=requirement.subject_id,
                logical_path=requirement.logical_path,
                object_path=f"objects/{media_sha256[:2]}/{media_sha256}",
                media_type=requirement.media_type,
                sha256=media_sha256,
                size_bytes=len(raw),
                duration_ms=duration_ms,
                source_authority="SEPARATELY_APPROVED_LOCAL_GENERATION",
                provenance_record_sha256=_sha(
                    f"synthetic-decision-provenance-{requirement.ordinal}".encode()
                ),
                technical_profile=requirement.technical_profile,
                technical_record_sha256=_technical_digest(
                    kind=requirement.kind,
                    media_sha256=media_sha256,
                    media_size_bytes=len(raw),
                    profile=requirement.technical_profile,
                    evidence=technical,
                ),
                image=image,
                audio=audio,
            )
        )
    objects = tuple(descriptors)
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-frozen-real-asset-pack",
        "profile": "creative-sample-real-asset-intake-v1",
        "template_id": template.template_id,
        "submission_id": stable_id("real_asset_submission", {"fixture": "finalizer-v22"}),
        "pilot_pack_id": template.pilot_pack_id,
        "objects": tuple(item.model_dump(mode="json") for item in objects),
        "total_size_bytes": sum(item.size_bytes for item in objects),
        "state": "FROZEN_UNREVIEWED",
        "current_gate": "HUMAN_GATE",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    pack = CreativeSampleFrozenRealAssetPackManifest.model_validate(
        {"pack_id": stable_id("real_asset_pack", payload), **payload},
        strict=True,
    )
    return pack, media_bytes


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path.resolve()


def _decision_output(tmp_path: Path, name: str) -> Path:
    parent = (tmp_path / "decision-area").resolve()
    parent.mkdir(exist_ok=True)
    return parent / name


def _build_instruction(
    *,
    request: CreativeSampleRealAssetQualificationRequestV2,
    qualifier_ref_sha256: str,
    decision: RealAssetQualificationDecisionV2 = "PASS_ASSET_INTAKE_ONLY",
    issues: tuple[RealAssetQualificationIssueCodeV2, ...] = (),
    basis: str = "合成离线资格审查指令仅确认精确资产摄取范围。",
    decision_at: str = DECISION_AT,
    request_sha256: str | None = None,
) -> CreativeSampleRealAssetQualificationDecisionInstructionV22:
    payload: dict[str, object] = {
        "schema_version": "2.2.0",
        "document_type": (
            "sdc.creative-sample-real-asset-qualification-decision-instruction-v2.2"
        ),
        "profile": "creative-sample-real-asset-qualification-decision-finalization-v2.2",
        "request_id": request.request_id,
        "request_sha256": request_sha256 or _sha(_canonical_document(request)),
        "policy_id": QUALIFICATION_V2_POLICY_ID,
        "policy_version": QUALIFICATION_V2_POLICY_VERSION,
        "policy_document_sha256": QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
        "qualification_scope": "ASSET_INTAKE_ONLY",
        "qualifier_role": "INDEPENDENT_QUALIFIER",
        "qualifier_ref_sha256": qualifier_ref_sha256,
        "decision_at": decision_at,
        "decision": decision,
        "qualification_issue_codes": issues,
        "qualification_basis": basis,
        "status": "DECISION_INSTRUCTION_RECORDED",
        "rights_manifest_created": False,
        "rights_qualification_performed": False,
        "eligible_for_separate_manifest_design_review": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetQualificationDecisionInstructionV22.model_validate(
        {
            "instruction_id": stable_id(
                "real_asset_qualification_decision_instruction_v22",
                payload,
            ),
            **payload,
        },
        strict=True,
    )


@dataclass(frozen=True)
class SyntheticDecisionClosure:
    paths: TrustedLocalDecisionPaths
    pack: CreativeSampleFrozenRealAssetPackManifest
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2
    pair_check: CreativeSampleRealAssetReviewPairCheckV2
    request: CreativeSampleRealAssetQualificationRequestV2
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22


@pytest.fixture
def closure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SyntheticDecisionClosure:
    pack, media_bytes = _make_pack()
    pack_root = (tmp_path / pack.pack_id).resolve()
    pack_root.mkdir()
    media_paths: list[Path] = []
    for descriptor, raw in zip(pack.objects, media_bytes, strict=True):
        media_paths.append(_write(pack_root / Path(descriptor.object_path), raw))
    manifest_path = _write(pack_root / "asset-pack.json", _canonical_document(pack))

    evidence_record = _write(
        tmp_path / "records" / "evidence-retained.txt",
        b"synthetic finalizer retained evidence record",
    )
    preparer_ref = _write(
        tmp_path / "records" / "evidence-preparer-ref.txt",
        b"synthetic finalizer independent evidence preparer",
    )
    reviewer_a_record = _write(
        tmp_path / "records" / "reviewer-a-retained.txt",
        b"synthetic finalizer reviewer A retained identity",
    )
    reviewer_b_record = _write(
        tmp_path / "records" / "reviewer-b-retained.txt",
        b"synthetic finalizer reviewer B retained identity",
    )
    evidence = build_real_asset_rights_evidence_bundle_v2(
        pack=pack,
        evidence_record_sha256=_sha(evidence_record.read_bytes()),
        copyright_basis="合成测试权利记录覆盖精确冻结字节。",
        likeness_basis="合成测试确认虚构形象及离线声音范围。",
        privacy_basis="合成测试确认逐项隐私检查。",
        territory="CN",
        use_scope="仅用于本地 finalizer 合成测试。",
        valid_until=VALID_UNTIL,
    )
    findings = build_real_asset_human_findings_v2(
        pack=pack,
        confirmed_ordinals=tuple(range(14)),
        content_role_approvals=(True,) * 14,
    )
    reviewer_a = build_real_asset_human_pack_review_v2(
        pack=pack,
        evidence=evidence,
        reviewer_role="REVIEWER_A",
        reviewer_ref_sha256=_sha(reviewer_a_record.read_bytes()),
        reviewed_at=REVIEW_A_AT,
        findings=findings,
        provenance_approved=True,
        copyright_approved=True,
        likeness_approved=True,
        privacy_approved=True,
        territory_approved=True,
        use_scope_approved=True,
        decision="APPROVED",
    )
    reviewer_b = build_real_asset_human_pack_review_v2(
        pack=pack,
        evidence=evidence,
        reviewer_role="REVIEWER_B",
        reviewer_ref_sha256=_sha(reviewer_b_record.read_bytes()),
        reviewed_at=REVIEW_B_AT,
        findings=findings,
        provenance_approved=True,
        copyright_approved=True,
        likeness_approved=True,
        privacy_approved=True,
        territory_approved=True,
        use_scope_approved=True,
        decision="APPROVED",
    )
    pair_check = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        evaluated_at=EVALUATED_AT,
    )
    evidence_path = _write(
        tmp_path / "contracts" / "evidence.json",
        _canonical_document(evidence),
    )
    reviewer_a_path = _write(
        tmp_path / "contracts" / "reviewer-a.json",
        _canonical_document(reviewer_a),
    )
    reviewer_b_path = _write(
        tmp_path / "contracts" / "reviewer-b.json",
        _canonical_document(reviewer_b),
    )
    pair_check_path = _write(
        tmp_path / "contracts" / "pair-check.json",
        _canonical_document(pair_check),
    )
    request_inputs = TrustedLocalRequestPaths(
        pack_root=pack_root,
        pack_manifest=manifest_path,
        media_paths=tuple(media_paths),
        evidence_bundle=evidence_path,
        reviewer_a=reviewer_a_path,
        reviewer_b=reviewer_b_path,
        pair_check=pair_check_path,
        evidence_retained_record=evidence_record,
        evidence_preparer_ref=preparer_ref,
        reviewer_a_retained_record=reviewer_a_record,
        reviewer_b_retained_record=reviewer_b_record,
    )

    def verify(root: Path) -> FrozenRealAssetPack:
        if root != pack_root:
            raise AssertionError("synthetic verifier received a different root")
        return FrozenRealAssetPack(
            root=pack_root,
            manifest_path=manifest_path,
            manifest=pack,
            created=False,
        )

    monkeypatch.setattr(preparer_module, "verify_real_asset_candidate_pack", verify)
    monkeypatch.setattr(finalizer_module, "verify_real_asset_candidate_pack", verify)

    request_path = (tmp_path / "request-area" / "request-v2.json").resolve()
    request_path.parent.mkdir()
    request = prepare_request(request_inputs, request_path, requested_at=REQUESTED_AT)
    qualifier_ref = _write(
        tmp_path / "qualifier-area" / "qualifier-ref.txt",
        b"synthetic finalizer independent qualifier identity",
    )
    instruction = _build_instruction(
        request=request,
        qualifier_ref_sha256=_sha(qualifier_ref.read_bytes()),
    )
    instruction_path = _write(
        tmp_path / "qualifier-area" / "decision-instruction-v22.json",
        _canonical_document(instruction),
    )
    return SyntheticDecisionClosure(
        paths=TrustedLocalDecisionPaths(
            request_inputs=request_inputs,
            request=request_path,
            qualifier_ref=qualifier_ref,
            qualifier_decision_record=instruction_path,
        ),
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
        instruction=instruction,
    )


def _cli_args(paths: TrustedLocalDecisionPaths) -> list[str]:
    request = paths.request_inputs
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
            "--request",
            str(paths.request),
            "--qualifier-ref",
            str(paths.qualifier_ref),
            "--qualifier-decision-record",
            str(paths.qualifier_decision_record),
        )
    )
    return values


def _replace_instruction(
    closure: SyntheticDecisionClosure,
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
) -> TrustedLocalDecisionPaths:
    closure.paths.qualifier_decision_record.write_bytes(_canonical_document(instruction))
    return closure.paths


def test_instruction_is_strict_stable_zero_authority_contract(
    closure: SyntheticDecisionClosure,
) -> None:
    instruction = closure.instruction
    assert instruction.instruction_id == stable_id(
        "real_asset_qualification_decision_instruction_v22",
        instruction.model_dump(mode="json", exclude={"instruction_id"}),
    )
    assert instruction.qualifier_role == "INDEPENDENT_QUALIFIER"
    assert instruction.qualification_scope == "ASSET_INTAKE_ONLY"
    assert instruction.rights_manifest_created is False
    assert instruction.rights_qualification_performed is False
    assert instruction.eligible_for_separate_manifest_design_review is False
    assert instruction.current_gate == "HUMAN_GATE"
    assert instruction.provider_state == "NOT_AUTHORIZED"
    assert instruction.execution_authorized is False
    assert instruction.posts_allowed == instruction.provider_requests == 0
    assert "qualifier_record_sha256" not in type(instruction).model_fields


@pytest.mark.parametrize(
    ("decision", "issues"),
    (
        ("PASS_ASSET_INTAKE_ONLY", ("OTHER_BLOCKING_ISSUE",)),
        ("REJECTED", ("POLICY_REQUIREMENT_NOT_MET",)),
        ("NEEDS_HUMAN_REVIEW", ("QUALIFIER_REJECTED_ASSET_INTAKE",)),
    ),
)
def test_instruction_rejects_inconsistent_decision_semantics(
    closure: SyntheticDecisionClosure,
    decision: RealAssetQualificationDecisionV2,
    issues: tuple[RealAssetQualificationIssueCodeV2, ...],
) -> None:
    payload = closure.instruction.model_dump(mode="python", exclude={"instruction_id"})
    payload.update(decision=decision, qualification_issue_codes=issues)
    payload["instruction_id"] = stable_id(
        "real_asset_qualification_decision_instruction_v22",
        {key: value for key, value in payload.items() if key != "instruction_id"},
    )
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetQualificationDecisionInstructionV22.model_validate(
            payload,
            strict=True,
        )


def test_instruction_validates_identity_policy_role_time_and_portable_basis(
    closure: SyntheticDecisionClosure,
) -> None:
    base = closure.instruction.model_dump(mode="python")
    mutations: tuple[tuple[str, object], ...] = (
        ("instruction_id", "real_asset_qualification_decision_instruction_v22_" + "0" * 20),
        ("policy_version", "9.9.9"),
        ("qualifier_role", "REVIEWER_A"),
        ("qualifier_ref_sha256", "A" * 64),
        ("decision_at", "2026-08-18T10:40:00+00:00"),
        ("qualification_basis", " leading"),
        ("qualification_basis", "e\u0301"),
        ("qualification_basis", "control\ntext"),
        ("qualification_basis", "字" * 1001),
    )
    for field, value in mutations:
        payload = {**base, field: value}
        if field != "instruction_id":
            payload["instruction_id"] = stable_id(
                "real_asset_qualification_decision_instruction_v22",
                {key: item for key, item in payload.items() if key != "instruction_id"},
            )
        with pytest.raises(ValidationError):
            CreativeSampleRealAssetQualificationDecisionInstructionV22.model_validate(
                payload,
                strict=True,
            )


def test_pass_instruction_must_explicitly_supply_even_an_empty_issue_tuple(
    closure: SyntheticDecisionClosure,
) -> None:
    payload = closure.instruction.model_dump(mode="python")
    del payload["qualification_issue_codes"]
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetQualificationDecisionInstructionV22.model_validate(
            payload,
            strict=True,
        )
    schema = CreativeSampleRealAssetQualificationDecisionInstructionV22.model_json_schema()
    assert "qualification_issue_codes" in schema["required"]


@pytest.mark.parametrize(
    ("decision", "issues"),
    (
        ("PASS_ASSET_INTAKE_ONLY", ()),
        ("REJECTED", ("QUALIFIER_REJECTED_ASSET_INTAKE",)),
        ("NEEDS_HUMAN_REVIEW", ("OTHER_BLOCKING_ISSUE",)),
    ),
)
def test_all_three_instruction_outcomes_have_valid_canonical_forms(
    closure: SyntheticDecisionClosure,
    decision: RealAssetQualificationDecisionV2,
    issues: tuple[RealAssetQualificationIssueCodeV2, ...],
) -> None:
    instruction = _build_instruction(
        request=closure.request,
        qualifier_ref_sha256=closure.instruction.qualifier_ref_sha256,
        decision=decision,
        issues=issues,
        basis=f"合成离线资格审查指令记录{decision}范围。",
    )
    assert instruction.decision == decision
    assert instruction.qualification_issue_codes == issues
    assert instruction.rights_qualification_performed is False


def test_inspect_never_builds_a_candidate_and_writes_nothing(
    closure: SyntheticDecisionClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("inspect must never call the decision builder")

    monkeypatch.setattr(finalizer_module, "build_real_asset_qualification_decision_v2", explode)
    before = tuple(closure.paths.qualifier_decision_record.parent.iterdir())
    inspected = inspect_decision_ready(closure.paths, observed_at=OBSERVED_AT)
    after = tuple(closure.paths.qualifier_decision_record.parent.iterdir())
    assert inspected == closure.instruction
    assert before == after
    assert inspected.rights_qualification_performed is False


def test_finalize_and_verify_exact_scoped_zero_execution_authority(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
) -> None:
    output = _decision_output(tmp_path, "decision-v2.json")
    finalized = finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    verified = verify_decision(closure.paths, output)
    assert finalized == verified
    assert parse_real_asset_qualification_decision_v2_json(output.read_bytes()) == finalized
    assert output.read_bytes() == _canonical_document(finalized)
    assert finalized.decision == "PASS_ASSET_INTAKE_ONLY"
    assert finalized.qualification_scope == "ASSET_INTAKE_ONLY"
    assert finalized.rights_manifest_created is False
    assert finalized.rights_qualification_performed is True
    assert finalized.current_gate == "HUMAN_GATE"
    assert finalized.provider_state == "NOT_AUTHORIZED"
    assert finalized.eligible_for_real_generation is False
    assert finalized.execution_authorized is False
    assert finalized.posts_allowed == finalized.provider_requests == 0


def test_all_three_outcomes_finalize_with_identical_zero_execution_boundary(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
) -> None:
    cases: tuple[
        tuple[RealAssetQualificationDecisionV2, tuple[RealAssetQualificationIssueCodeV2, ...]],
        ...,
    ] = (
        ("PASS_ASSET_INTAKE_ONLY", ()),
        ("REJECTED", ("QUALIFIER_REJECTED_ASSET_INTAKE",)),
        ("NEEDS_HUMAN_REVIEW", ("OTHER_BLOCKING_ISSUE",)),
    )
    for ordinal, (outcome, issues) in enumerate(cases):
        instruction = _build_instruction(
            request=closure.request,
            qualifier_ref_sha256=closure.instruction.qualifier_ref_sha256,
            decision=outcome,
            issues=issues,
            basis=f"合成离线资格审查指令第{ordinal}项仅限资产摄取。",
        )
        _replace_instruction(closure, instruction)
        finalized = finalize_decision(
            closure.paths,
            _decision_output(tmp_path, f"decision-case-{ordinal}.json"),
            observed_at=OBSERVED_AT,
        )
        assert finalized.decision == outcome
        assert finalized.rights_manifest_created is False
        assert finalized.current_gate == "HUMAN_GATE"
        assert finalized.provider_state == "NOT_AUTHORIZED"
        assert finalized.eligible_for_real_generation is False
        assert finalized.execution_authorized is False
        assert finalized.posts_allowed == finalized.provider_requests == 0


def test_finalize_builder_runs_exactly_once_after_second_complete_capture(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    original_capture = finalizer_module._capture_ready
    original_builder = finalizer_module.build_real_asset_qualification_decision_v2

    def capture(*args: object, **kwargs: object) -> object:
        events.append("capture")
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    def build(*args: object, **kwargs: object) -> object:
        events.append("build")
        return original_builder(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(finalizer_module, "_capture_ready", capture)
    monkeypatch.setattr(finalizer_module, "build_real_asset_qualification_decision_v2", build)
    finalize_decision(
        closure.paths,
        _decision_output(tmp_path, "single-builder.json"),
        observed_at=OBSERVED_AT,
    )
    assert events == ["capture", "capture", "build", "capture"]


def test_explicit_time_order_is_enforced_but_verify_is_historical(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
) -> None:
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="later than observed"):
        inspect_decision_ready(closure.paths, observed_at="2026-08-18T10:39:59Z")
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="canonical UTC"):
        inspect_decision_ready(closure.paths, observed_at="2026-08-18 10:45:00Z")
    with pytest.raises(TrustedLocalDecisionFinalizationError):
        inspect_decision_ready(closure.paths, observed_at="2026-08-19T10:30:00Z")

    output = _decision_output(tmp_path, "historical-decision.json")
    finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    assert verify_decision(closure.paths, output).decision_at == DECISION_AT
    source = inspect.getsource(finalizer_module)
    assert "datetime.now" not in source
    assert "datetime.utcnow" not in source
    assert "time.time" not in source


@pytest.mark.parametrize("mutation", ("duplicate", "unknown", "noncanonical"))
def test_instruction_json_is_strict_and_canonical(
    closure: SyntheticDecisionClosure,
    mutation: str,
) -> None:
    path = closure.paths.qualifier_decision_record
    raw = path.read_bytes()
    if mutation == "duplicate":
        path.write_bytes(b'{"status":"DECISION_INSTRUCTION_RECORDED",' + raw[1:])
        match = "duplicate JSON"
    else:
        payload = closure.instruction.model_dump(mode="json")
        if mutation == "unknown":
            payload["unknown"] = True
            path.write_bytes(
                (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
            )
            match = "strict contract"
        else:
            path.write_bytes((json.dumps(payload, ensure_ascii=False) + "\n").encode())
            match = "not canonical"
    with pytest.raises(TrustedLocalDecisionFinalizationError, match=match):
        inspect_decision_ready(closure.paths, observed_at=OBSERVED_AT)


def test_instruction_raw_boundary_rejects_bom_non_utf8_nonfinite_and_oversize(
    closure: SyntheticDecisionClosure,
) -> None:
    path = closure.paths.qualifier_decision_record
    canonical = _canonical_document(closure.instruction)
    invalid = (
        b"\xef\xbb\xbf" + canonical,
        b"\xff\xfe" + canonical,
        canonical.replace(b'"posts_allowed": 0', b'"posts_allowed": NaN'),
        b"{" + b" " * 1_048_576 + b"}",
    )
    for raw in invalid:
        path.write_bytes(raw)
        with pytest.raises(TrustedLocalDecisionFinalizationError):
            inspect_decision_ready(closure.paths, observed_at=OBSERVED_AT)
    path.write_bytes(canonical)


def test_instruction_request_and_qualifier_bindings_are_exact(
    closure: SyntheticDecisionClosure,
) -> None:
    mismatched_request = _build_instruction(
        request=closure.request,
        qualifier_ref_sha256=closure.instruction.qualifier_ref_sha256,
        request_sha256="1" * 64,
    )
    _replace_instruction(closure, mismatched_request)
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="exact request"):
        inspect_decision_ready(closure.paths, observed_at=OBSERVED_AT)


def test_source_path_physical_and_digest_aliases_fail_closed(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
) -> None:
    copied_request = _write(
        tmp_path / "qualifier-copy" / "qualifier-ref.txt",
        closure.paths.request.read_bytes(),
    )
    alias_instruction = _build_instruction(
        request=closure.request,
        qualifier_ref_sha256=_sha(copied_request.read_bytes()),
    )
    instruction_path = _write(
        tmp_path / "qualifier-copy" / "instruction-v22.json",
        _canonical_document(alias_instruction),
    )
    aliased = replace(
        closure.paths,
        qualifier_ref=copied_request,
        qualifier_decision_record=instruction_path,
    )
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="digest alias"):
        inspect_decision_ready(aliased, observed_at=OBSERVED_AT)

    hardlink = (tmp_path / "qualifier-hardlink" / "qualifier-ref.txt").resolve()
    hardlink.parent.mkdir()
    try:
        os.link(closure.paths.qualifier_ref, hardlink)
    except OSError:
        pytest.skip("hard links are unavailable on this host")
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="non-linked"):
        inspect_decision_ready(
            replace(closure.paths, qualifier_ref=hardlink),
            observed_at=OBSERVED_AT,
        )


def test_qualifier_digests_cannot_alias_nonfile_reserved_closure_records(
    closure: SyntheticDecisionClosure,
) -> None:
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="reserved closure"):
        finalizer_module._assert_qualifier_digest_closure(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            request=closure.request,
            qualifier_ref_sha256=closure.pack.objects[0].provenance_record_sha256,
            qualifier_record_sha256="2" * 64,
        )


def test_symlink_and_mutable_alias_inputs_fail_closed_when_supported(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
) -> None:
    mutable = _write(
        tmp_path / "qualifier-alias" / "qualifier-latest.txt",
        closure.paths.qualifier_ref.read_bytes(),
    )
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="mutable alias"):
        inspect_decision_ready(
            replace(closure.paths, qualifier_ref=mutable),
            observed_at=OBSERVED_AT,
        )

    linked = (tmp_path / "qualifier-alias" / "linked-ref.txt").resolve()
    try:
        linked.symlink_to(closure.paths.qualifier_ref)
    except OSError:
        pytest.skip("symbolic links are unavailable on this host")
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="safe local path"):
        inspect_decision_ready(
            replace(closure.paths, qualifier_ref=linked),
            observed_at=OBSERVED_AT,
        )


def test_mutable_alias_tokens_cover_request_qualifier_and_instruction_paths(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
) -> None:
    cases = (
        (
            "request",
            _write(
                tmp_path / "request-area-copy" / "request-latest.json",
                closure.paths.request.read_bytes(),
            ),
        ),
        (
            "qualifier_ref",
            _write(
                tmp_path / "qualifier-area-copy" / "qualifier-current.txt",
                closure.paths.qualifier_ref.read_bytes(),
            ),
        ),
        (
            "qualifier_decision_record",
            _write(
                tmp_path / "instruction-area-copy" / "instruction-newest.json",
                closure.paths.qualifier_decision_record.read_bytes(),
            ),
        ),
    )
    for field, path in cases:
        with pytest.raises(TrustedLocalDecisionFinalizationError, match="mutable alias"):
            finalizer_module._normalize_paths(replace(closure.paths, **{field: path}))


@pytest.mark.parametrize("basename", ("pass.json", "rejected.json", "needs-human-review.json"))
def test_instruction_basename_never_discloses_its_outcome(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    basename: str,
) -> None:
    disclosed = _write(
        tmp_path / "opaque-instruction-area" / basename,
        closure.paths.qualifier_decision_record.read_bytes(),
    )
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="outcome"):
        inspect_decision_ready(
            replace(closure.paths, qualifier_decision_record=disclosed),
            observed_at=OBSERVED_AT,
        )


def test_hardlinks_cover_each_new_private_input_class_when_supported(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
) -> None:
    originals = (
        ("request", closure.paths.request),
        ("qualifier_ref", closure.paths.qualifier_ref),
        ("qualifier_decision_record", closure.paths.qualifier_decision_record),
    )
    for field, original in originals:
        linked = (tmp_path / f"hardlink-{field}" / original.name).resolve()
        linked.parent.mkdir()
        try:
            os.link(original, linked)
        except OSError:
            pytest.skip("hard links are unavailable on this host")
        try:
            with pytest.raises(TrustedLocalDecisionFinalizationError):
                inspect_decision_ready(
                    replace(closure.paths, **{field: linked}),
                    observed_at=OBSERVED_AT,
                )
        finally:
            linked.unlink(missing_ok=True)


def test_media_paths_are_explicit_absolute_and_manifest_ordered(
    closure: SyntheticDecisionClosure,
) -> None:
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="fourteen"):
        inspect_decision_ready(
            replace(
                closure.paths,
                request_inputs=replace(
                    closure.paths.request_inputs,
                    media_paths=closure.paths.request_inputs.media_paths[:13],
                ),
            ),
            observed_at=OBSERVED_AT,
        )
    swapped = list(closure.paths.request_inputs.media_paths)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="closure failed"):
        inspect_decision_ready(
            replace(
                closure.paths,
                request_inputs=replace(
                    closure.paths.request_inputs,
                    media_paths=tuple(swapped),
                ),
            ),
            observed_at=OBSERVED_AT,
        )
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="absolute"):
        inspect_decision_ready(
            replace(closure.paths, qualifier_ref=Path("qualifier-ref.txt")),
            observed_at=OBSERVED_AT,
        )


def test_finalize_is_create_new_and_decision_parent_is_separate(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
) -> None:
    existing = _write(_decision_output(tmp_path, "existing.json"), b"do not overwrite")
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="new file"):
        finalize_decision(closure.paths, existing, observed_at=OBSERVED_AT)
    assert existing.read_bytes() == b"do not overwrite"

    same = closure.paths.qualifier_ref.parent / "decision.json"
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="trust area"):
        finalize_decision(closure.paths, same, observed_at=OBSERVED_AT)
    nested_parent = closure.paths.request.parent / "nested-decisions"
    nested_parent.mkdir()
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="trust area"):
        finalize_decision(
            closure.paths,
            nested_parent / "decision.json",
            observed_at=OBSERVED_AT,
        )
    containing = tmp_path / "decision.json"
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="trust area"):
        finalize_decision(closure.paths, containing, observed_at=OBSERVED_AT)

    disclosed = _decision_output(tmp_path, "decision-pass.json")
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="outcome"):
        finalize_decision(closure.paths, disclosed, observed_at=OBSERVED_AT)


def test_created_decision_uses_private_mode_where_posix_modes_apply(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
) -> None:
    output = _decision_output(tmp_path, "private-mode.json")
    finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    if os.name != "nt":
        assert output.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("relationship", ("equal", "nested", "containing"))
def test_verify_decision_parent_is_also_separate(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    relationship: str,
) -> None:
    source = _decision_output(tmp_path, "source-decision.json")
    finalize_decision(closure.paths, source, observed_at=OBSERVED_AT)
    if relationship == "equal":
        target = closure.paths.qualifier_ref.parent / "copied-decision.json"
    elif relationship == "nested":
        parent = closure.paths.request.parent / "nested-verify"
        parent.mkdir()
        target = parent / "copied-decision.json"
    else:
        target = tmp_path / "copied-decision.json"
    _write(target, source.read_bytes())
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="trust area"):
        verify_decision(closure.paths, target)


@pytest.mark.parametrize("mutate_after_capture", (1, 2))
def test_prewrite_and_postwrite_drift_leave_no_valid_decision(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate_after_capture: int,
) -> None:
    original_capture = finalizer_module._capture_ready
    calls = 0
    instruction_path = closure.paths.qualifier_decision_record
    raw = instruction_path.read_bytes()

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        result = original_capture(*args, **kwargs)  # type: ignore[arg-type]
        calls += 1
        if calls == mutate_after_capture:
            replacement = instruction_path.with_suffix(".replacement")
            replacement.write_bytes(raw)
            os.replace(replacement, instruction_path)
        return result

    monkeypatch.setattr(finalizer_module, "_capture_ready", capture)
    output = _decision_output(tmp_path, f"drift-{mutate_after_capture}.json")
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="drifted"):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    assert not output.exists()


def test_request_identity_drift_before_write_leaves_no_decision(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_capture = finalizer_module._capture_ready
    request_path = closure.paths.request
    raw = request_path.read_bytes()
    calls = 0

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        result = original_capture(*args, **kwargs)  # type: ignore[arg-type]
        calls += 1
        if calls == 1:
            replacement = request_path.with_suffix(".replacement")
            replacement.write_bytes(raw)
            os.replace(replacement, request_path)
        return result

    monkeypatch.setattr(finalizer_module, "_capture_ready", capture)
    output = _decision_output(tmp_path, "request-drift.json")
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="drifted"):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    assert not output.exists()


def test_output_parent_identity_swap_is_detected_before_create(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _decision_output(tmp_path, "parent-swap.json")
    parent = output.parent
    moved = parent.with_name("decision-area-original")
    original_capture = finalizer_module._capture_ready
    calls = 0

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        result = original_capture(*args, **kwargs)  # type: ignore[arg-type]
        calls += 1
        if calls == 2:
            parent.rename(moved)
            parent.mkdir()
        return result

    monkeypatch.setattr(finalizer_module, "_capture_ready", capture)
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="parent identity"):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    assert not output.exists()
    assert not (moved / output.name).exists()


@pytest.mark.parametrize("failure", ("short-write", "fsync", "parent-fsync", "parse"))
def test_create_failure_never_leaves_a_valid_decision(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    output = _decision_output(tmp_path, f"create-failure-{failure}.json")
    if failure == "short-write":
        original_write = os.write
        calls = 0

        def short_write(descriptor: int, data: bytes) -> int:
            nonlocal calls
            calls += 1
            if calls == 1:
                return original_write(descriptor, data[:19])
            return 0

        monkeypatch.setattr(os, "write", short_write)
    elif failure == "fsync":

        def reject_fsync(descriptor: int) -> None:
            del descriptor
            raise OSError("synthetic file fsync failure")

        monkeypatch.setattr(os, "fsync", reject_fsync)
    elif failure == "parent-fsync":
        if os.name == "nt":

            def reject_parent_fsync(created: object) -> None:
                del created
                raise OSError("synthetic parent fsync failure")

            monkeypatch.setattr(
                finalizer_module,
                "_fsync_parent_directory",
                reject_parent_fsync,
            )
        else:
            original_fsync = os.fsync
            fsync_calls = 0

            def fail_second_fsync(descriptor: int) -> None:
                nonlocal fsync_calls
                fsync_calls += 1
                if fsync_calls == 2:
                    raise OSError("synthetic parent fsync failure")
                original_fsync(descriptor)

            monkeypatch.setattr(os, "fsync", fail_second_fsync)
    else:

        def reject_decision(raw: bytes) -> CreativeSampleRealAssetQualificationDecisionV2:
            del raw
            raise RealAssetQualificationV2Error("synthetic parser failure")

        monkeypatch.setattr(
            finalizer_module,
            "parse_real_asset_qualification_decision_v2_json",
            reject_decision,
        )
    with pytest.raises(TrustedLocalDecisionFinalizationError):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    assert not output.exists()


def test_delete_failure_can_only_leave_an_invalidated_artifact(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _decision_output(tmp_path, "delete-failure.json")
    original_capture = finalizer_module._capture_ready
    calls = 0

    def fail_after_create(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TrustedLocalDecisionFinalizationError("synthetic post-create failure")
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(finalizer_module, "_capture_ready", fail_after_create)
    if os.name == "nt":
        monkeypatch.setattr(finalizer_module, "_delete_open_windows_decision", lambda value: False)
    else:
        monkeypatch.setattr(
            finalizer_module,
            "_unlink_open_posix_decision",
            lambda created, identity: False,
        )
    with pytest.raises(TrustedLocalDecisionFinalizationError):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    assert output.exists()
    assert output.read_bytes() in {b"", b"\0"}
    with pytest.raises(RealAssetQualificationV2Error):
        parse_real_asset_qualification_decision_v2_json(output.read_bytes())


def test_truncate_and_delete_failure_fallback_poison_is_not_valid(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _decision_output(tmp_path, "truncate-delete-failure.json")
    original_capture = finalizer_module._capture_ready
    calls = 0

    def fail_after_create(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TrustedLocalDecisionFinalizationError("synthetic post-create failure")
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    def reject_truncate(descriptor: int, length: int) -> None:
        del descriptor, length
        raise OSError("synthetic truncate failure")

    monkeypatch.setattr(finalizer_module, "_capture_ready", fail_after_create)
    monkeypatch.setattr(os, "ftruncate", reject_truncate)
    if os.name == "nt":
        monkeypatch.setattr(finalizer_module, "_delete_open_windows_decision", lambda value: False)
    else:
        monkeypatch.setattr(
            finalizer_module,
            "_unlink_open_posix_decision",
            lambda created, identity: False,
        )
    with pytest.raises(TrustedLocalDecisionFinalizationError):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    assert output.read_bytes().startswith(b"\0")
    with pytest.raises(RealAssetQualificationV2Error):
        parse_real_asset_qualification_decision_v2_json(output.read_bytes())


def test_primary_invalidation_and_delete_failure_trigger_exact_fd_emergency_poison(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _decision_output(tmp_path, "rollback-both-false.json")
    original_capture = finalizer_module._capture_ready
    calls = 0

    def fail_after_create(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TrustedLocalDecisionFinalizationError("synthetic post-create failure")
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(finalizer_module, "_capture_ready", fail_after_create)
    monkeypatch.setattr(finalizer_module, "_invalidate_open_decision", lambda value: False)
    if os.name == "nt":
        monkeypatch.setattr(finalizer_module, "_delete_open_windows_decision", lambda value: False)
    else:
        monkeypatch.setattr(
            finalizer_module,
            "_unlink_open_posix_decision",
            lambda created, identity: False,
        )
    with pytest.raises(TrustedLocalDecisionFinalizationError):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    assert output.read_bytes().startswith(b"\0")
    with pytest.raises(RealAssetQualificationV2Error):
        parse_real_asset_qualification_decision_v2_json(output.read_bytes())


def test_total_exact_media_rollback_failure_requires_explicit_quarantine(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _decision_output(tmp_path, "rollback-quarantine.json")
    original_capture = finalizer_module._capture_ready
    calls = 0

    def fail_after_create(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TrustedLocalDecisionFinalizationError("synthetic post-create failure")
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(finalizer_module, "_capture_ready", fail_after_create)
    monkeypatch.setattr(finalizer_module, "_invalidate_open_decision", lambda value: False)
    monkeypatch.setattr(
        finalizer_module,
        "_emergency_poison_open_decision",
        lambda value: False,
    )
    if os.name == "nt":
        monkeypatch.setattr(finalizer_module, "_delete_open_windows_decision", lambda value: False)
    else:
        monkeypatch.setattr(
            finalizer_module,
            "_unlink_open_posix_decision",
            lambda created, identity: False,
        )
    with pytest.raises(TrustedLocalDecisionQuarantineRequired, match="requires quarantine"):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)


def test_cli_exposes_fixed_nonprivate_quarantine_status(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = _decision_output(tmp_path, "cli-quarantine.json")
    original_capture = finalizer_module._capture_ready
    calls = 0

    def fail_after_create(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TrustedLocalDecisionFinalizationError("private synthetic failure")
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(finalizer_module, "_capture_ready", fail_after_create)
    monkeypatch.setattr(finalizer_module, "_invalidate_open_decision", lambda value: False)
    monkeypatch.setattr(
        finalizer_module,
        "_emergency_poison_open_decision",
        lambda value: False,
    )
    if os.name == "nt":
        monkeypatch.setattr(finalizer_module, "_delete_open_windows_decision", lambda value: False)
    else:
        monkeypatch.setattr(
            finalizer_module,
            "_unlink_open_posix_decision",
            lambda created, identity: False,
        )
    assert main(
        [
            "finalize-decision",
            *_cli_args(closure.paths),
            "--output",
            str(output),
            "--observed-at",
            OBSERVED_AT,
        ]
    ) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    summary = json.loads(captured.err)
    assert summary["status"] == "ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"
    assert summary["current_gate"] == "HUMAN_GATE"
    assert summary["provider_state"] == "NOT_AUTHORIZED"
    assert summary["execution_authorized"] is False
    assert summary["posts_allowed"] == summary["provider_requests"] == 0
    assert str(tmp_path) not in captured.err
    assert closure.instruction.decision not in captured.err


def test_commit_guard_close_failure_maps_to_quarantine_required(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _decision_output(tmp_path, "commit-close-quarantine.json")
    original_close_guard = finalizer_module._close_parent_guard

    def close_then_fail(created: object) -> None:
        original_close_guard(created)  # type: ignore[arg-type]
        raise OSError("synthetic guard close completion failure")

    monkeypatch.setattr(finalizer_module, "_close_parent_guard", close_then_fail)
    with pytest.raises(TrustedLocalDecisionQuarantineRequired):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)


@pytest.mark.parametrize("interrupt", (KeyboardInterrupt, SystemExit))
def test_postwrite_base_exception_rolls_back_before_propagation(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupt: type[BaseException],
) -> None:
    output = _decision_output(tmp_path, f"base-exception-{interrupt.__name__}.json")
    original_capture = finalizer_module._capture_ready
    calls = 0

    def interrupt_after_create(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise interrupt()
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(finalizer_module, "_capture_ready", interrupt_after_create)
    with pytest.raises(interrupt):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    assert not output.exists()


def test_create_time_base_exception_closes_guard_and_removes_partial(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _decision_output(tmp_path, "create-base-exception.json")
    original_write = os.write
    calls = 0

    def interrupt_first_write(descriptor: int, data: bytes) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise KeyboardInterrupt
        return original_write(descriptor, data)

    monkeypatch.setattr(os, "write", interrupt_first_write)
    with pytest.raises(KeyboardInterrupt):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    assert not output.exists()


def test_replacement_during_failure_is_never_deleted_as_created_decision(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _decision_output(tmp_path, "replacement-race.json")
    replacement_path = _write(
        output.parent / "independent-replacement.bin",
        b"independent replacement",
    )
    original_capture = finalizer_module._capture_ready
    calls = 0
    replacement_succeeded = False

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls, replacement_succeeded
        calls += 1
        if calls == 3:
            try:
                os.replace(replacement_path, output)
            except PermissionError:
                raise OSError("replacement denied by retained exact handle") from None
            replacement_succeeded = True
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(finalizer_module, "_capture_ready", capture)
    with pytest.raises(TrustedLocalDecisionFinalizationError):
        finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    if replacement_succeeded:
        assert output.read_bytes() == b"independent replacement"
    else:
        assert not output.exists()
        assert replacement_path.read_bytes() == b"independent replacement"


def test_existing_decision_and_instruction_tampering_fail_closed(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
) -> None:
    output = _decision_output(tmp_path, "tamper.json")
    finalized = finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    payload = finalized.model_dump(mode="json")
    payload["unknown"] = True
    output.write_bytes(
        (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    )
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="strict contract"):
        verify_decision(closure.paths, output)

    output.write_bytes(_canonical_document(finalized))
    changed = _build_instruction(
        request=closure.request,
        qualifier_ref_sha256=closure.instruction.qualifier_ref_sha256,
        decision="NEEDS_HUMAN_REVIEW",
        issues=("OTHER_BLOCKING_ISSUE",),
        basis="合成离线资格审查指令要求继续人工处理。",
    )
    _replace_instruction(closure, changed)
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="exact retained instruction"):
        verify_decision(closure.paths, output)


def test_decision_identity_drift_during_historical_verify_fails_closed(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _decision_output(tmp_path, "verify-drift.json")
    finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    raw = output.read_bytes()
    original_capture = finalizer_module._capture_ready
    calls = 0

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        result = original_capture(*args, **kwargs)  # type: ignore[arg-type]
        calls += 1
        if calls == 1:
            replacement = output.with_suffix(".replacement")
            replacement.write_bytes(raw)
            os.replace(replacement, output)
        return result

    monkeypatch.setattr(finalizer_module, "_capture_ready", capture)
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="drifted"):
        verify_decision(closure.paths, output)


def test_verify_replays_nonfile_reserved_digest_publication_invariant(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _decision_output(tmp_path, "reserved-replay.json")
    finalize_decision(closure.paths, output, observed_at=OBSERVED_AT)
    decision_sha256 = _sha(output.read_bytes())
    original_reserved = finalizer_module._reserved_digest_closure

    def reserved(*args: object, **kwargs: object) -> set[str]:
        return original_reserved(*args, **kwargs) | {decision_sha256}  # type: ignore[arg-type]

    monkeypatch.setattr(finalizer_module, "_reserved_digest_closure", reserved)
    with pytest.raises(TrustedLocalDecisionFinalizationError, match="reserved closure"):
        verify_decision(closure.paths, output)


def test_cli_surface_and_success_summaries_never_disclose_outcome_or_basis(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = inspect.getsource(finalizer_module)
    assert source.count('add_parser("inspect-decision-ready")') == 1
    assert source.count('add_parser("finalize-decision")') == 1
    assert source.count('add_parser("verify-decision")') == 1
    for forbidden in (
        'add_argument("--decision")',
        'add_argument("--basis")',
        'add_argument("--qualification-basis")',
        'add_argument("--issue")',
        'add_argument("--decision-at")',
        ".glob(",
        ".rglob(",
    ):
        assert forbidden not in source

    assert main(
        [
            "inspect-decision-ready",
            *_cli_args(closure.paths),
            "--observed-at",
            OBSERVED_AT,
        ]
    ) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "READY_FOR_DECISION_FINALIZATION"
    assert summary["rights_qualification_performed"] is False
    assert "decision_id" not in summary

    output = _decision_output(tmp_path, "cli-decision.json")
    assert main(
        [
            "finalize-decision",
            *_cli_args(closure.paths),
            "--output",
            str(output),
            "--observed-at",
            OBSERVED_AT,
        ]
    ) == 0
    finalized_stdout = capsys.readouterr().out
    finalized_summary = json.loads(finalized_stdout)
    assert finalized_summary["rights_qualification_performed"] is True
    assert "decision_id" in finalized_summary
    assert closure.instruction.decision not in finalized_stdout
    assert closure.instruction.qualification_basis not in finalized_stdout
    assert str(tmp_path) not in finalized_stdout
    assert main(
        [
            "verify-decision",
            *_cli_args(closure.paths),
            "--decision-file",
            str(output),
        ]
    ) == 0
    verified_stdout = capsys.readouterr().out
    assert closure.instruction.decision not in verified_stdout
    assert closure.instruction.qualification_basis not in verified_stdout


@pytest.mark.parametrize("case", ("command", "unknown-flag", "observed-at"))
def test_cli_parser_and_failures_do_not_echo_private_markers(
    closure: SyntheticDecisionClosure,
    capsys: pytest.CaptureFixture[str],
    case: str,
) -> None:
    marker = "PRIVATE-FINALIZER-MARKER-DO-NOT-ECHO"
    if case == "command":
        argv = [marker]
    elif case == "unknown-flag":
        argv = [
            "inspect-decision-ready",
            *_cli_args(closure.paths),
            "--observed-at",
            OBSERVED_AT,
            "--private-marker",
            marker,
        ]
    else:
        argv = [
            "inspect-decision-ready",
            *_cli_args(closure.paths),
            "--observed-at",
            marker,
        ]
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert marker not in captured.err
    assert "usage:" not in captured.err
    assert json.loads(captured.err)["status"] == "FAILED_CLOSED"


def test_cli_unknown_exception_is_generic_without_traceback(
    closure: SyntheticDecisionClosure,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    marker = "PRIVATE-UNKNOWN-FINALIZER-EXCEPTION"

    def fail(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError(marker)

    monkeypatch.setattr(finalizer_module, "inspect_decision_ready", fail)
    assert main(
        [
            "inspect-decision-ready",
            *_cli_args(closure.paths),
            "--observed-at",
            OBSERVED_AT,
        ]
    ) == 2
    captured = capsys.readouterr()
    assert marker not in captured.err
    assert "Traceback" not in captured.err
    assert json.loads(captured.err)["status"] == "FAILED_CLOSED"


@pytest.mark.parametrize("interrupt", (KeyboardInterrupt, SystemExit))
def test_cli_operation_base_exceptions_are_redacted_failures_not_success(
    closure: SyntheticDecisionClosure,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    interrupt: type[BaseException],
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise interrupt()

    monkeypatch.setattr(finalizer_module, "inspect_decision_ready", fail)
    assert main(
        [
            "inspect-decision-ready",
            *_cli_args(closure.paths),
            "--observed-at",
            OBSERVED_AT,
        ]
    ) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["status"] == "FAILED_CLOSED"


@pytest.mark.parametrize("interrupt", (KeyboardInterrupt, SystemExit))
def test_cli_postwrite_base_exception_rolls_back_and_redacts(
    closure: SyntheticDecisionClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    interrupt: type[BaseException],
) -> None:
    output = _decision_output(tmp_path, f"cli-interrupt-{interrupt.__name__}.json")
    original_capture = finalizer_module._capture_ready
    calls = 0

    def interrupt_after_create(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise interrupt()
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(finalizer_module, "_capture_ready", interrupt_after_create)
    assert main(
        [
            "finalize-decision",
            *_cli_args(closure.paths),
            "--output",
            str(output),
            "--observed-at",
            OBSERVED_AT,
        ]
    ) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["status"] == "FAILED_CLOSED"
    assert "Traceback" not in captured.err
    assert str(tmp_path) not in captured.err
    assert closure.instruction.decision not in captured.err
    assert closure.instruction.qualification_basis not in captured.err
    assert not output.exists()


def test_cli_help_remains_normal_system_exit_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["-h"])
    assert raised.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert captured.err == ""


def test_dependency_surface_is_local_and_instruction_contract_is_pure() -> None:
    finalizer_tree = ast.parse(inspect.getsource(finalizer_module))
    instruction_tree = ast.parse(inspect.getsource(instruction_module))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(finalizer_tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    assert not {
        module.split(".", 1)[0] for module in imported
    } & {"http", "requests", "socket", "subprocess", "urllib"}
    assert not any(
        fragment in module.casefold()
        for module in imported
        for fragment in (
            "ark",
            "authorization",
            "entitlement",
            "ledger",
            "migration",
            "postgres",
            "provider",
            "runtime",
            "temporal",
            "worker",
        )
    )
    assert not {"getenv", "input", "popen", "putenv", "system"} & called
    assert "build_real_asset_rights_manifest" not in called
    assert "qualify_real_asset_candidate_pack" not in called
    pure_import_roots = {
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(instruction_tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".", 1)[0]
        for node in ast.walk(instruction_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not pure_import_roots & {"argparse", "ctypes", "os", "pathlib", "sys"}
