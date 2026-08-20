"""Synthetic-only helpers for downstream Pack-level v2 contract tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

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
    CreativeSampleRealAssetRightsManifestV2,
    build_real_asset_rights_manifest_v2,
)

REVIEW_A_AT = "2026-08-17T10:00:00Z"
REVIEW_B_AT = "2026-08-17T10:10:00Z"
EVALUATED_AT = "2026-08-17T11:00:00Z"
QUALIFICATION_REQUESTED_AT = "2026-08-17T12:00:00Z"
DECISION_AT = "2026-08-17T13:00:00Z"
MANIFEST_AT = "2026-08-19T12:00:00Z"
VALID_UNTIL = "2026-12-31T00:00:00Z"


def digest(label: str) -> str:
    return hashlib.sha256(f"sdc-use-plan-v26-test:{label}".encode()).hexdigest()


def canonical_payload(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def canonical_document(value: object) -> bytes:
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
        + canonical_payload(
            {
                "kind": kind,
                "media_sha256": media_sha256,
                "media_size_bytes": media_size_bytes,
                "profile": profile,
                "evidence": evidence.model_dump(mode="json"),
            }
        )
    ).hexdigest()


def make_pack(label: str = "primary") -> CreativeSampleFrozenRealAssetPackManifest:
    template = build_real_asset_intake_template()
    descriptors: list[FrozenRealAssetDescriptor] = []
    for requirement in template.requirements:
        media_sha256 = digest(f"{label}:media:{requirement.ordinal}")
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
            duration_ms = 72_000 if requirement.kind == "BGM" else (
                (requirement.end_ms or 0) - (requirement.start_ms or 0)
            )
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
                provenance_record_sha256=digest(
                    f"{label}:provenance:{requirement.ordinal}"
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
    valid_until: str,
) -> CreativeSampleRealAssetRightsEvidenceBundleV2:
    return build_real_asset_rights_evidence_bundle_v2(
        pack=pack,
        evidence_record_sha256=digest(f"evidence:{valid_until}"),
        copyright_basis="合成测试权利记录覆盖精确冻结字节。",
        likeness_basis="合成测试记录确认虚构形象和离线声音范围。",
        privacy_basis="合成测试记录确认逐项隐私检查。",
        territory="CN",
        use_scope="仅用于本地样片用途规划与权利对齐测试。",
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
        reviewer_ref_sha256=digest(f"reviewer:{role}:{evidence.valid_until}"),
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
class CompleteClosure:
    pack: CreativeSampleFrozenRealAssetPackManifest
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2
    pair_check: CreativeSampleRealAssetReviewPairCheckV2
    request: CreativeSampleRealAssetQualificationRequestV2
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22
    decision: CreativeSampleRealAssetQualificationDecisionV2
    manifest: CreativeSampleRealAssetRightsManifestV2


def make_complete_closure(*, valid_until: str = VALID_UNTIL) -> CompleteClosure:
    pack = make_pack()
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
    request = build_real_asset_qualification_request_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        evidence_preparer_ref_sha256=digest("evidence-preparer"),
        requested_at=QUALIFICATION_REQUESTED_AT,
    )
    instruction_payload: dict[str, object] = {
        "schema_version": "2.2.0",
        "document_type": (
            "sdc.creative-sample-real-asset-qualification-decision-instruction-v2.2"
        ),
        "profile": "creative-sample-real-asset-qualification-decision-finalization-v2.2",
        "request_id": request.request_id,
        "request_sha256": hashlib.sha256(canonical_document(request)).hexdigest(),
        "policy_id": request.policy_id,
        "policy_version": request.policy_version,
        "policy_document_sha256": request.policy_document_sha256,
        "qualification_scope": "ASSET_INTAKE_ONLY",
        "qualifier_role": "INDEPENDENT_QUALIFIER",
        "qualifier_ref_sha256": digest("qualifier-ref"),
        "decision_at": DECISION_AT,
        "decision": "PASS_ASSET_INTAKE_ONLY",
        "qualification_issue_codes": (),
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
    instruction = CreativeSampleRealAssetQualificationDecisionInstructionV22.model_validate(
        {
            "instruction_id": stable_id(
                "real_asset_qualification_decision_instruction_v22",
                instruction_payload,
            ),
            **instruction_payload,
        },
        strict=True,
    )
    decision = build_real_asset_qualification_decision_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
        qualifier_ref_sha256=instruction.qualifier_ref_sha256,
        qualifier_record_sha256=hashlib.sha256(canonical_document(instruction)).hexdigest(),
        decision_at=instruction.decision_at,
        qualification_issue_codes=instruction.qualification_issue_codes,
        qualification_basis=instruction.qualification_basis,
        decision=instruction.decision,
    )
    manifest = build_real_asset_rights_manifest_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
        instruction=instruction,
        decision=decision,
        manifest_at=MANIFEST_AT,
    )
    return CompleteClosure(
        pack,
        evidence,
        reviewer_a,
        reviewer_b,
        pair_check,
        request,
        instruction,
        decision,
        manifest,
    )
