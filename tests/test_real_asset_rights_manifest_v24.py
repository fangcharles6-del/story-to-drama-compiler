from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from sdc.compiler import stable_id
from sdc.real_asset_intake import (
    CreativeSampleFrozenRealAssetPackManifest,
    FrozenRealAssetDescriptor,
    RealAudioTechnicalRecord,
    RealImageTechnicalRecord,
    build_real_asset_intake_template,
)
from sdc.real_asset_qualification_decision_instruction_v22 import (
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
)
from sdc.real_asset_qualification_v2 import (
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationRequestV2,
    build_real_asset_qualification_decision_v2,
    build_real_asset_qualification_request_v2,
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
from sdc.real_asset_rights_manifest_v24 import (
    RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256,
    RIGHTS_MANIFEST_V2_POLICY_ID,
    RIGHTS_MANIFEST_V2_POLICY_VERSION,
    RIGHTS_MANIFEST_V2_PROFILE,
    CreativeSampleRealAssetRightsManifestV2,
    RealAssetRightsManifestV24Error,
    build_real_asset_rights_manifest_v2,
    parse_real_asset_rights_manifest_v2_json,
    verify_real_asset_rights_manifest_closure_v2,
)

MANIFEST_FIELDS = tuple(CreativeSampleRealAssetRightsManifestV2.model_fields)

REVIEW_A_AT = "2026-08-17T10:00:00Z"
REVIEW_B_AT = "2026-08-17T10:10:00Z"
EVALUATED_AT = "2026-08-17T11:00:00Z"
REQUESTED_AT = "2026-08-17T12:00:00Z"
DECISION_AT = "2026-08-17T13:00:00Z"
MANIFEST_AT = "2026-08-19T12:00:00Z"
VALID_UNTIL = "2026-08-20T00:00:00Z"


def _digest(label: str) -> str:
    return hashlib.sha256(f"sdc-rights-manifest-v24-test:{label}".encode()).hexdigest()


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
            value.model_dump(mode="json"),  # type: ignore[union-attr]
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
    return hashlib.sha256(
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
    ).hexdigest()


def _make_pack(
    label: str = "primary",
    *,
    first_provenance_sha256: str | None = None,
) -> CreativeSampleFrozenRealAssetPackManifest:
    template = build_real_asset_intake_template()
    descriptors: list[FrozenRealAssetDescriptor] = []
    for requirement in template.requirements:
        media_sha256 = _digest(f"{label}:media:{requirement.ordinal}")
        media_size_bytes = 10_000 + requirement.ordinal
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
                size_bytes=media_size_bytes,
                duration_ms=duration_ms,
                source_authority="SEPARATELY_APPROVED_LOCAL_GENERATION",
                provenance_record_sha256=(
                    first_provenance_sha256
                    if requirement.ordinal == 0 and first_provenance_sha256 is not None
                    else _digest(f"{label}:provenance:{requirement.ordinal}")
                ),
                technical_profile=requirement.technical_profile,
                technical_record_sha256=_technical_digest(
                    kind=requirement.kind,
                    media_sha256=media_sha256,
                    media_size_bytes=media_size_bytes,
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
        "submission_id": stable_id("real_asset_submission", {"fixture": label}),
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
    return CreativeSampleFrozenRealAssetPackManifest.model_validate(
        {"pack_id": stable_id("real_asset_pack", payload), **payload},
        strict=True,
    )


def _make_evidence(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    *,
    valid_until: str = VALID_UNTIL,
) -> CreativeSampleRealAssetRightsEvidenceBundleV2:
    return build_real_asset_rights_evidence_bundle_v2(
        pack=pack,
        evidence_record_sha256=_digest(f"evidence:{valid_until}"),
        copyright_basis="合成测试权利记录覆盖精确冻结字节。",
        likeness_basis="合成测试记录确认虚构形象和离线声音范围。",
        privacy_basis="合成测试记录确认逐项隐私检查。",
        territory="CN",
        use_scope="仅用于本地资产入库资格测试。",
        valid_until=valid_until,
    )


def _make_review(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    role: str,
    reviewed_at: str,
) -> CreativeSampleRealAssetHumanPackReviewV2:
    findings = build_real_asset_human_findings_v2(
        pack=pack,
        confirmed_ordinals=tuple(range(14)),
        content_role_approvals=(True,) * 14,
    )
    return build_real_asset_human_pack_review_v2(
        pack=pack,
        evidence=evidence,
        reviewer_role=role,  # type: ignore[arg-type]
        reviewer_ref_sha256=_digest(f"reviewer:{role}:{evidence.valid_until}"),
        reviewed_at=reviewed_at,
        findings=findings,
        provenance_approved=True,
        copyright_approved=True,
        likeness_approved=True,
        privacy_approved=True,
        territory_approved=True,
        use_scope_approved=True,
        decision="APPROVED",
        rejection_reason=None,
    )


@dataclass(frozen=True)
class ReviewClosure:
    pack: CreativeSampleFrozenRealAssetPackManifest
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2
    pair_check: CreativeSampleRealAssetReviewPairCheckV2


def _make_review_closure(*, valid_until: str = VALID_UNTIL) -> ReviewClosure:
    pack = _make_pack()
    evidence = _make_evidence(pack, valid_until=valid_until)
    reviewer_a = _make_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at=REVIEW_A_AT,
    )
    reviewer_b = _make_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at=REVIEW_B_AT,
    )
    pair_check = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        evaluated_at=EVALUATED_AT,
    )
    return ReviewClosure(pack, evidence, reviewer_a, reviewer_b, pair_check)


def _make_request(
    closure: ReviewClosure,
) -> CreativeSampleRealAssetQualificationRequestV2:
    return build_real_asset_qualification_request_v2(
        pack=closure.pack,
        evidence=closure.evidence,
        reviewer_a=closure.reviewer_a,
        reviewer_b=closure.reviewer_b,
        pair_check=closure.pair_check,
        evidence_preparer_ref_sha256=_digest("evidence-preparer"),
        requested_at=REQUESTED_AT,
    )


def _make_instruction(
    request: CreativeSampleRealAssetQualificationRequestV2,
    *,
    decision: str = "PASS_ASSET_INTAKE_ONLY",
) -> CreativeSampleRealAssetQualificationDecisionInstructionV22:
    issues = (
        ()
        if decision == "PASS_ASSET_INTAKE_ONLY"
        else (
            ("POLICY_REQUIREMENT_NOT_MET", "QUALIFIER_REJECTED_ASSET_INTAKE")
            if decision == "REJECTED"
            else ("POLICY_REQUIREMENT_NOT_MET",)
        )
    )
    payload: dict[str, object] = {
        "schema_version": "2.2.0",
        "document_type": (
            "sdc.creative-sample-real-asset-qualification-decision-instruction-v2.2"
        ),
        "profile": "creative-sample-real-asset-qualification-decision-finalization-v2.2",
        "request_id": request.request_id,
        "request_sha256": hashlib.sha256(_canonical_document(request)).hexdigest(),
        "policy_id": request.policy_id,
        "policy_version": request.policy_version,
        "policy_document_sha256": request.policy_document_sha256,
        "qualification_scope": "ASSET_INTAKE_ONLY",
        "qualifier_role": "INDEPENDENT_QUALIFIER",
        "qualifier_ref_sha256": _digest("qualifier-ref"),
        "decision_at": DECISION_AT,
        "decision": decision,
        "qualification_issue_codes": issues,
        "qualification_basis": "独立资格审查员仅确认合成资产入库范围。",
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


def _make_decision(
    closure: ReviewClosure,
    request: CreativeSampleRealAssetQualificationRequestV2,
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
) -> CreativeSampleRealAssetQualificationDecisionV2:
    return build_real_asset_qualification_decision_v2(
        pack=closure.pack,
        evidence=closure.evidence,
        reviewer_a=closure.reviewer_a,
        reviewer_b=closure.reviewer_b,
        pair_check=closure.pair_check,
        request=request,
        qualifier_ref_sha256=instruction.qualifier_ref_sha256,
        qualifier_record_sha256=hashlib.sha256(_canonical_document(instruction)).hexdigest(),
        decision_at=instruction.decision_at,
        qualification_issue_codes=instruction.qualification_issue_codes,
        qualification_basis=instruction.qualification_basis,
        decision=instruction.decision,
    )


@dataclass(frozen=True)
class CompleteClosure:
    review: ReviewClosure
    request: CreativeSampleRealAssetQualificationRequestV2
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22
    decision: CreativeSampleRealAssetQualificationDecisionV2


def _make_complete_closure(
    *,
    valid_until: str = VALID_UNTIL,
    decision: str = "PASS_ASSET_INTAKE_ONLY",
) -> CompleteClosure:
    review = _make_review_closure(valid_until=valid_until)
    request = _make_request(review)
    instruction = _make_instruction(request, decision=decision)
    qualification_decision = _make_decision(review, request, instruction)
    return CompleteClosure(review, request, instruction, qualification_decision)


@pytest.fixture(scope="module")
def closure() -> CompleteClosure:
    return _make_complete_closure()


def _build(
    closure: CompleteClosure,
    *,
    manifest_at: str = MANIFEST_AT,
) -> CreativeSampleRealAssetRightsManifestV2:
    return build_real_asset_rights_manifest_v2(
        pack=closure.review.pack,
        evidence=closure.review.evidence,
        reviewer_a=closure.review.reviewer_a,
        reviewer_b=closure.review.reviewer_b,
        pair_check=closure.review.pair_check,
        request=closure.request,
        instruction=closure.instruction,
        decision=closure.decision,
        manifest_at=manifest_at,
    )


def _verify(
    closure: CompleteClosure,
    manifest: CreativeSampleRealAssetRightsManifestV2,
) -> CreativeSampleRealAssetRightsManifestV2:
    return verify_real_asset_rights_manifest_closure_v2(
        pack=closure.review.pack,
        evidence=closure.review.evidence,
        reviewer_a=closure.review.reviewer_a,
        reviewer_b=closure.review.reviewer_b,
        pair_check=closure.review.pair_check,
        request=closure.request,
        instruction=closure.instruction,
        decision=closure.decision,
        manifest=manifest,
    )


@pytest.fixture(scope="module")
def manifest(closure: CompleteClosure) -> CreativeSampleRealAssetRightsManifestV2:
    return _build(closure)


def test_positive_closure_builds_deterministic_inert_manifest(
    closure: CompleteClosure,
) -> None:
    upstream = (
        closure.review.pack,
        closure.review.evidence,
        closure.review.reviewer_a,
        closure.review.reviewer_b,
        closure.review.pair_check,
        closure.request,
        closure.instruction,
        closure.decision,
    )
    before = tuple(_canonical_document(value) for value in upstream)
    first = _build(closure)
    second = _build(closure)

    assert first == second
    assert _verify(closure, first) == first
    assert first.schema_version == "2.4.0"
    assert first.profile == RIGHTS_MANIFEST_V2_PROFILE
    assert first.manifest_policy_id == RIGHTS_MANIFEST_V2_POLICY_ID
    assert first.manifest_policy_version == RIGHTS_MANIFEST_V2_POLICY_VERSION
    assert first.manifest_policy_document_sha256 == RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256
    assert first.qualification_decision == "PASS_ASSET_INTAKE_ONLY"
    assert first.qualification_scope == "ASSET_INTAKE_ONLY"
    assert first.eligible_for_separate_manifest_design_review is True
    assert first.rights_qualification_performed is True
    assert first.rights_manifest_created is True
    assert first.current_gate == "HUMAN_GATE"
    assert first.provider_state == "NOT_AUTHORIZED"
    assert first.eligible_for_real_generation is False
    assert first.execution_authorized is False
    assert first.posts_allowed == first.provider_requests == 0
    assert first.manifest_at > closure.request.request_valid_until
    assert before == tuple(_canonical_document(value) for value in upstream)
    with pytest.raises(ValidationError):
        first.execution_authorized = True  # type: ignore[misc]


def test_manifest_binds_every_canonical_contract_id_and_record(
    closure: CompleteClosure,
) -> None:
    manifest = _build(closure)
    review = closure.review
    bindings = (
        (manifest.pack_id, review.pack.pack_id),
        (manifest.rights_evidence_bundle_id, review.evidence.bundle_id),
        (manifest.review_a_id, review.reviewer_a.review_id),
        (manifest.review_b_id, review.reviewer_b.review_id),
        (manifest.pair_check_id, review.pair_check.pair_check_id),
        (manifest.request_id, closure.request.request_id),
        (manifest.instruction_id, closure.instruction.instruction_id),
        (manifest.decision_id, closure.decision.decision_id),
    )
    assert all(actual == expected for actual, expected in bindings)
    assert manifest.pack_manifest_sha256 == hashlib.sha256(
        _canonical_document(review.pack)
    ).hexdigest()
    assert manifest.rights_evidence_bundle_sha256 == hashlib.sha256(
        _canonical_document(review.evidence)
    ).hexdigest()
    assert manifest.review_a_contract_sha256 == hashlib.sha256(
        _canonical_document(review.reviewer_a)
    ).hexdigest()
    assert manifest.review_b_contract_sha256 == hashlib.sha256(
        _canonical_document(review.reviewer_b)
    ).hexdigest()
    assert manifest.pair_check_sha256 == hashlib.sha256(
        _canonical_document(review.pair_check)
    ).hexdigest()
    assert manifest.request_sha256 == hashlib.sha256(
        _canonical_document(closure.request)
    ).hexdigest()
    assert manifest.instruction_sha256 == hashlib.sha256(
        _canonical_document(closure.instruction)
    ).hexdigest()
    assert manifest.decision_sha256 == hashlib.sha256(
        _canonical_document(closure.decision)
    ).hexdigest()
    assert manifest.qualifier_record_sha256 == manifest.instruction_sha256
    assert manifest.review_a_record_sha256 == closure.request.review_a_record_sha256
    assert manifest.review_b_record_sha256 == closure.request.review_b_record_sha256


@pytest.mark.parametrize("decision", ["REJECTED", "NEEDS_HUMAN_REVIEW"])
def test_every_non_positive_decision_fails_closed(decision: str) -> None:
    negative = _make_complete_closure(decision=decision)
    with pytest.raises(RealAssetRightsManifestV24Error, match="not eligible"):
        _build(negative)


def test_instruction_or_upstream_drift_fails_closed(
    closure: CompleteClosure,
) -> None:
    forged_instruction = closure.instruction.model_copy(
        update={"qualification_basis": "不同但格式有效的合成依据。"}
    )
    with pytest.raises(RealAssetRightsManifestV24Error, match="instruction"):
        build_real_asset_rights_manifest_v2(
            pack=closure.review.pack,
            evidence=closure.review.evidence,
            reviewer_a=closure.review.reviewer_a,
            reviewer_b=closure.review.reviewer_b,
            pair_check=closure.review.pair_check,
            request=closure.request,
            instruction=forged_instruction,
            decision=closure.decision,
            manifest_at=MANIFEST_AT,
        )

    false_eligibility = closure.decision.model_copy(
        update={"eligible_for_separate_manifest_design_review": False}
    )
    with pytest.raises(RealAssetRightsManifestV24Error, match="qualification decision"):
        build_real_asset_rights_manifest_v2(
            pack=closure.review.pack,
            evidence=closure.review.evidence,
            reviewer_a=closure.review.reviewer_a,
            reviewer_b=closure.review.reviewer_b,
            pair_check=closure.review.pair_check,
            request=closure.request,
            instruction=closure.instruction,
            decision=false_eligibility,
            manifest_at=MANIFEST_AT,
        )

    with pytest.raises(RealAssetRightsManifestV24Error, match="closure"):
        build_real_asset_rights_manifest_v2(
            pack=_make_pack("drifted"),
            evidence=closure.review.evidence,
            reviewer_a=closure.review.reviewer_a,
            reviewer_b=closure.review.reviewer_b,
            pair_check=closure.review.pair_check,
            request=closure.request,
            instruction=closure.instruction,
            decision=closure.decision,
            manifest_at=MANIFEST_AT,
        )

    forged_pack = closure.review.pack.model_copy(
        update={"total_size_bytes": closure.review.pack.total_size_bytes + 1}
    )
    with pytest.raises(RealAssetRightsManifestV24Error, match="frozen Pack"):
        build_real_asset_rights_manifest_v2(
            pack=forged_pack,
            evidence=closure.review.evidence,
            reviewer_a=closure.review.reviewer_a,
            reviewer_b=closure.review.reviewer_b,
            pair_check=closure.review.pair_check,
            request=closure.request,
            instruction=closure.instruction,
            decision=closure.decision,
            manifest_at=MANIFEST_AT,
        )


@pytest.mark.parametrize(
    ("target", "field", "cross_typed_value"),
    [
        ("pack", "execution_authorized", 0),
        ("pack", "posts_allowed", False),
        ("decision", "rights_qualification_performed", 1),
        ("instruction", "rights_qualification_performed", 0),
    ],
)
def test_upstream_model_copy_cross_types_cannot_normalize_silently(
    closure: CompleteClosure,
    target: str,
    field: str,
    cross_typed_value: object,
) -> None:
    pack = closure.review.pack
    instruction = closure.instruction
    decision = closure.decision
    if target == "pack":
        pack = pack.model_copy(update={field: cross_typed_value})
    elif target == "instruction":
        instruction = instruction.model_copy(update={field: cross_typed_value})
    else:
        decision = decision.model_copy(update={field: cross_typed_value})

    with pytest.raises(RealAssetRightsManifestV24Error, match="strict|canonical bytes"):
        build_real_asset_rights_manifest_v2(
            pack=pack,
            evidence=closure.review.evidence,
            reviewer_a=closure.review.reviewer_a,
            reviewer_b=closure.review.reviewer_b,
            pair_check=closure.review.pair_check,
            request=closure.request,
            instruction=instruction,
            decision=decision,
            manifest_at=MANIFEST_AT,
        )


def test_unmodified_upstream_models_preserve_canonical_bytes(
    closure: CompleteClosure,
) -> None:
    manifest = _build(closure)
    assert manifest.pack_manifest_sha256 == hashlib.sha256(
        _canonical_document(closure.review.pack)
    ).hexdigest()
    assert manifest.instruction_sha256 == hashlib.sha256(
        _canonical_document(closure.instruction)
    ).hexdigest()
    assert manifest.decision_sha256 == hashlib.sha256(
        _canonical_document(closure.decision)
    ).hexdigest()


@pytest.mark.parametrize(
    ("first_provenance_sha256", "error"),
    [
        (RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256, "alias Pack object records"),
        (_digest("primary:provenance:1"), "must be fully distinct"),
    ],
)
def test_pack_object_records_are_unique_and_cannot_alias_manifest_closure_digests(
    first_provenance_sha256: str,
    error: str,
) -> None:
    pack = _make_pack(first_provenance_sha256=first_provenance_sha256)
    evidence = _make_evidence(pack)
    reviewer_a = _make_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at=REVIEW_A_AT,
    )
    reviewer_b = _make_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at=REVIEW_B_AT,
    )
    pair_check = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        evaluated_at=EVALUATED_AT,
    )
    review = ReviewClosure(pack, evidence, reviewer_a, reviewer_b, pair_check)
    request = _make_request(review)
    instruction = _make_instruction(request)
    decision = _make_decision(review, request, instruction)
    aliased = CompleteClosure(review, request, instruction, decision)

    with pytest.raises(RealAssetRightsManifestV24Error, match=error):
        _build(aliased)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "request_id",
            "real_asset_qualification_request_v2_00000000000000000000",
        ),
        ("request_sha256", _digest("different-request")),
        ("policy_version", "1.0.0"),
        ("qualifier_ref_sha256", _digest("different-qualifier")),
        ("decision_at", "2026-08-17T13:00:01Z"),
        ("decision", "NEEDS_HUMAN_REVIEW"),
        ("qualification_issue_codes", ("POLICY_REQUIREMENT_NOT_MET",)),
        ("qualification_basis", "不同但格式有效的合成依据。"),
    ],
)
def test_each_retained_instruction_binding_drift_fails_closed(
    closure: CompleteClosure,
    field: str,
    value: object,
) -> None:
    forged = closure.instruction.model_copy(update={field: value})
    with pytest.raises(RealAssetRightsManifestV24Error, match="instruction"):
        build_real_asset_rights_manifest_v2(
            pack=closure.review.pack,
            evidence=closure.review.evidence,
            reviewer_a=closure.review.reviewer_a,
            reviewer_b=closure.review.reviewer_b,
            pair_check=closure.review.pair_check,
            request=closure.request,
            instruction=forged,
            decision=closure.decision,
            manifest_at=MANIFEST_AT,
        )


def test_manifest_time_is_explicit_causal_and_evidence_bounded(
    closure: CompleteClosure,
) -> None:
    assert _build(closure, manifest_at=DECISION_AT).manifest_at == DECISION_AT
    with pytest.raises(RealAssetRightsManifestV24Error, match="predate"):
        _build(closure, manifest_at="2026-08-17T12:59:59Z")
    with pytest.raises(RealAssetRightsManifestV24Error, match="expired"):
        _build(closure, manifest_at=VALID_UNTIL)
    with pytest.raises(RealAssetRightsManifestV24Error, match="canonical UTC"):
        _build(closure, manifest_at="2026-08-19T12:00:00+00:00")

    perpetual = _make_complete_closure(valid_until="PERPETUAL")
    assert _build(perpetual, manifest_at="2030-01-01T00:00:00Z").evidence_valid_until == (
        "PERPETUAL"
    )


def test_parser_is_bounded_strict_and_rejects_ambiguous_or_forged_json(
    closure: CompleteClosure,
) -> None:
    manifest = _build(closure)
    raw = _canonical_document(manifest)
    assert parse_real_asset_rights_manifest_v2_json(raw) == manifest

    missing = manifest.model_dump(mode="json")
    del missing["decision_id"]
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict contract"):
        parse_real_asset_rights_manifest_v2_json(json.dumps(missing).encode())
    unknown = manifest.model_dump(mode="json")
    unknown["unknown"] = True
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict contract"):
        parse_real_asset_rights_manifest_v2_json(json.dumps(unknown).encode())
    duplicate = (
        "{"
        + json.dumps("manifest_id")
        + ":"
        + json.dumps(manifest.manifest_id)
        + ","
        + raw.decode()[1:]
    ).encode()
    with pytest.raises(RealAssetRightsManifestV24Error, match="duplicate JSON key"):
        parse_real_asset_rights_manifest_v2_json(duplicate)
    with pytest.raises(RealAssetRightsManifestV24Error, match="non-finite"):
        parse_real_asset_rights_manifest_v2_json(b'{"value":NaN}')
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict UTF-8"):
        parse_real_asset_rights_manifest_v2_json(b"\xef\xbb\xbf" + raw)
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict UTF-8"):
        parse_real_asset_rights_manifest_v2_json(b"\xff")
    deeply_nested = b"[" * 2000 + b"0" + b"]" * 2000
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict UTF-8"):
        parse_real_asset_rights_manifest_v2_json(deeply_nested)
    excessive_integer = b'{"value":' + b"1" * 5000 + b"}"
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict UTF-8"):
        parse_real_asset_rights_manifest_v2_json(excessive_integer)
    with pytest.raises(RealAssetRightsManifestV24Error, match="one object"):
        parse_real_asset_rights_manifest_v2_json(b"[]")
    coerced = manifest.model_dump(mode="json")
    coerced["posts_allowed"] = "0"
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict contract"):
        parse_real_asset_rights_manifest_v2_json(json.dumps(coerced).encode())
    forged = manifest.model_dump(mode="json")
    forged["execution_authorized"] = True
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict contract"):
        parse_real_asset_rights_manifest_v2_json(json.dumps(forged).encode())
    with pytest.raises(RealAssetRightsManifestV24Error, match="bounded"):
        parse_real_asset_rights_manifest_v2_json(b" " * 1_048_577)
    with pytest.raises(RealAssetRightsManifestV24Error, match="bounded"):
        parse_real_asset_rights_manifest_v2_json(bytearray(raw))  # type: ignore[arg-type]


@pytest.mark.parametrize("missing_field", MANIFEST_FIELDS)
def test_every_manifest_field_is_required_by_parser_and_model_constructor(
    manifest: CreativeSampleRealAssetRightsManifestV2,
    missing_field: str,
) -> None:
    assert len(MANIFEST_FIELDS) == 49
    payload = manifest.model_dump(mode="json")
    del payload[missing_field]
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict contract"):
        parse_real_asset_rights_manifest_v2_json(json.dumps(payload).encode())
    with pytest.raises(ValidationError, match="Field required"):
        CreativeSampleRealAssetRightsManifestV2(**payload)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "cross_typed_value"),
    [
        ("eligible_for_separate_manifest_design_review", 1),
        ("rights_qualification_performed", 1),
        ("rights_manifest_created", 1),
        ("eligible_for_real_generation", 0),
        ("execution_authorized", 0),
        ("posts_allowed", False),
        ("posts_allowed", 0.0),
        ("provider_requests", False),
        ("provider_requests", 0.0),
    ],
)
def test_cross_typed_fixed_scalars_fail_parser_and_direct_validation(
    manifest: CreativeSampleRealAssetRightsManifestV2,
    field: str,
    cross_typed_value: object,
) -> None:
    payload = manifest.model_dump(mode="json")
    payload[field] = cross_typed_value
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict contract"):
        parse_real_asset_rights_manifest_v2_json(json.dumps(payload).encode())
    with pytest.raises(ValidationError, match="exact JSON"):
        CreativeSampleRealAssetRightsManifestV2.model_validate(payload, strict=True)


def test_verify_revalidates_untrusted_model_copy_and_exact_rebuild(
    closure: CompleteClosure,
) -> None:
    manifest = _build(closure)
    forged_authority = manifest.model_copy(update={"execution_authorized": True})
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict contract"):
        _verify(closure, forged_authority)

    forged_binding = manifest.model_copy(
        update={"decision_sha256": _digest("different-decision")}
    )
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict contract"):
        _verify(closure, forged_binding)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("eligible_for_separate_manifest_design_review", False),
        ("rights_qualification_performed", False),
        ("rights_manifest_created", False),
        ("current_gate", "OPEN"),
        ("provider_state", "AUTHORIZED"),
        ("eligible_for_real_generation", True),
        ("execution_authorized", True),
        ("posts_allowed", 1),
        ("provider_requests", 1),
    ],
)
def test_verify_rejects_every_forged_authority_field(
    closure: CompleteClosure,
    field: str,
    value: object,
) -> None:
    forged = _build(closure).model_copy(update={field: value})
    with pytest.raises(RealAssetRightsManifestV24Error, match="strict contract"):
        _verify(closure, forged)


def test_contract_policy_is_fixed_and_source_exposes_no_live_or_v1_boundary(
    closure: CompleteClosure,
) -> None:
    manifest = _build(closure)
    payload = manifest.model_dump(mode="python")
    payload["manifest_policy_document_sha256"] = _digest("untrusted-policy")
    with pytest.raises(ValidationError, match="manifest_policy_document_sha256"):
        CreativeSampleRealAssetRightsManifestV2.model_validate(payload, strict=True)
    schema = CreativeSampleRealAssetRightsManifestV2.model_json_schema()
    assert schema["properties"]["manifest_policy_document_sha256"]["const"] == (
        RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256
    )
    assert schema["properties"]["rights_manifest_created"]["const"] is True
    assert schema["properties"]["execution_authorized"]["const"] is False

    assert manifest.manifest_id == stable_id(
        "real_asset_rights_manifest_v2",
        manifest.model_dump(mode="json", exclude={"manifest_id"}),
    )
    forged_id = manifest.model_dump(mode="python")
    forged_id["manifest_id"] = "real_asset_rights_manifest_v2_00000000000000000000"
    with pytest.raises(ValidationError, match="rights manifest ID"):
        CreativeSampleRealAssetRightsManifestV2.model_validate(forged_id, strict=True)

    source = inspect.getsource(
        __import__(
            "sdc.real_asset_rights_manifest_v24",
            fromlist=["real_asset_rights_manifest_v24"],
        )
    )
    for forbidden in (
        "build_real_asset_rights_manifest,",
        "build_real_asset_rights_manifest(",
        "CreativeSampleRealAssetRightsManifest,",
        "qualify_real_asset_candidate_pack",
        "datetime.now",
        "datetime.utcnow",
        "from pathlib import Path",
        "open(",
        "requests.",
        "httpx.",
        "import argparse",
        "def main(",
        "if __name__",
        "provider_requests = 1",
    ):
        assert forbidden not in source
