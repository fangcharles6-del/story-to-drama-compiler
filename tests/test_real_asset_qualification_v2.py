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
from sdc.real_asset_qualification_v2 import (
    QUALIFICATION_REQUEST_MAX_AGE_SECONDS,
    QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationRequestV2,
    RealAssetQualificationV2Error,
    build_real_asset_qualification_decision_v2,
    build_real_asset_qualification_request_v2,
    parse_real_asset_qualification_decision_v2_json,
    parse_real_asset_qualification_request_v2_json,
    verify_real_asset_qualification_closure_v2,
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

REVIEW_A_AT = "2026-08-17T10:00:00Z"
REVIEW_B_AT = "2026-08-17T10:10:00Z"
EVALUATED_AT = "2026-08-17T11:00:00Z"
REQUESTED_AT = "2026-08-17T12:00:00Z"
DECISION_AT = "2026-08-17T13:00:00Z"
VALID_UNTIL = "2026-08-20T00:00:00Z"


def _digest(label: str) -> str:
    return hashlib.sha256(f"sdc-qualification-v2-test:{label}".encode()).hexdigest()


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


def _make_pack(label: str = "primary") -> CreativeSampleFrozenRealAssetPackManifest:
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
                provenance_record_sha256=_digest(
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
    approved: bool = True,
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
        provenance_approved=approved,
        copyright_approved=True,
        likeness_approved=True,
        privacy_approved=True,
        territory_approved=True,
        use_scope_approved=True,
        decision="APPROVED" if approved else "REJECTED",
        rejection_reason=None if approved else "合成测试拒绝。",
    )


@dataclass(frozen=True)
class Closure:
    pack: CreativeSampleFrozenRealAssetPackManifest
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2
    pair_check: CreativeSampleRealAssetReviewPairCheckV2


def _make_closure(*, valid_until: str = VALID_UNTIL) -> Closure:
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
    return Closure(pack, evidence, reviewer_a, reviewer_b, pair_check)


@pytest.fixture(scope="module")
def closure() -> Closure:
    return _make_closure()


def _request(closure: Closure) -> CreativeSampleRealAssetQualificationRequestV2:
    return build_real_asset_qualification_request_v2(
        pack=closure.pack,
        evidence=closure.evidence,
        reviewer_a=closure.reviewer_a,
        reviewer_b=closure.reviewer_b,
        pair_check=closure.pair_check,
        evidence_preparer_ref_sha256=_digest("evidence-preparer"),
        requested_at=REQUESTED_AT,
    )


def _decision(
    closure: Closure,
    request: CreativeSampleRealAssetQualificationRequestV2,
    *,
    decision_at: str = DECISION_AT,
    decision: str = "PASS_ASSET_INTAKE_ONLY",
) -> CreativeSampleRealAssetQualificationDecisionV2:
    return build_real_asset_qualification_decision_v2(
        pack=closure.pack,
        evidence=closure.evidence,
        reviewer_a=closure.reviewer_a,
        reviewer_b=closure.reviewer_b,
        pair_check=closure.pair_check,
        request=request,
        qualifier_ref_sha256=_digest("qualifier-ref"),
        qualifier_record_sha256=_digest("qualifier-record"),
        decision_at=decision_at,
        qualification_issue_codes=(
            ()
            if decision == "PASS_ASSET_INTAKE_ONLY"
            else (
                ("POLICY_REQUIREMENT_NOT_MET", "QUALIFIER_REJECTED_ASSET_INTAKE")
                if decision == "REJECTED"
                else ("POLICY_REQUIREMENT_NOT_MET",)
            )
        ),
        qualification_basis="独立资格审查员仅确认资产入库范围测试通过。",
        decision=decision,  # type: ignore[arg-type]
    )


def test_exact_closure_is_deterministic_scoped_and_zero_authority(closure: Closure) -> None:
    upstream_before = tuple(
        _canonical_document(value)
        for value in (
            closure.pack,
            closure.evidence,
            closure.reviewer_a,
            closure.reviewer_b,
            closure.pair_check,
        )
    )
    request = _request(closure)
    rebuilt_request = _request(closure)
    decision = _decision(closure, request)

    assert rebuilt_request == request
    assert request.policy_document_sha256 == QUALIFICATION_V2_POLICY_DOCUMENT_SHA256
    assert QUALIFICATION_REQUEST_MAX_AGE_SECONDS == 86_400
    assert request.request_valid_until == "2026-08-18T12:00:00Z"
    assert request.status == "QUALIFICATION_REQUESTED"
    assert request.rights_qualification_performed is False
    assert decision.decision == "PASS_ASSET_INTAKE_ONLY"
    assert decision.qualification_scope == "ASSET_INTAKE_ONLY"
    assert decision.status == "QUALIFICATION_COMPLETE"
    assert decision.rights_qualification_performed is True
    assert decision.rights_manifest_created is False
    assert decision.eligible_for_separate_manifest_design_review is True
    assert decision.current_gate == "HUMAN_GATE"
    assert decision.provider_state == "NOT_AUTHORIZED"
    assert decision.eligible_for_real_generation is False
    assert decision.execution_authorized is False
    assert decision.posts_allowed == decision.provider_requests == 0
    assert verify_real_asset_qualification_closure_v2(
        pack=closure.pack,
        evidence=closure.evidence,
        reviewer_a=closure.reviewer_a,
        reviewer_b=closure.reviewer_b,
        pair_check=closure.pair_check,
        request=request,
        decision=decision,
    ) == decision
    assert upstream_before == tuple(
        _canonical_document(value)
        for value in (
            closure.pack,
            closure.evidence,
            closure.reviewer_a,
            closure.reviewer_b,
            closure.pair_check,
        )
    )
    with pytest.raises(ValidationError):
        decision.posts_allowed = 1  # type: ignore[misc]


def test_contract_sha_id_and_record_bindings_are_exact(closure: Closure) -> None:
    request = _request(closure)
    decision = _decision(closure, request)

    assert request.pack_manifest_sha256 == hashlib.sha256(
        _canonical_document(closure.pack)
    ).hexdigest()
    assert request.rights_evidence_bundle_sha256 == hashlib.sha256(
        _canonical_document(closure.evidence)
    ).hexdigest()
    assert request.review_a_contract_sha256 == hashlib.sha256(
        _canonical_document(closure.reviewer_a)
    ).hexdigest()
    assert request.review_b_contract_sha256 == hashlib.sha256(
        _canonical_document(closure.reviewer_b)
    ).hexdigest()
    assert request.pair_check_sha256 == hashlib.sha256(
        _canonical_document(closure.pair_check)
    ).hexdigest()
    assert decision.request_sha256 == hashlib.sha256(_canonical_document(request)).hexdigest()

    request_payload = request.model_dump(mode="python")
    request_payload["evidence_preparer_ref_sha256"] = _digest("other-preparer")
    with pytest.raises(ValidationError, match="request ID"):
        CreativeSampleRealAssetQualificationRequestV2.model_validate(
            request_payload,
            strict=True,
        )
    decision_payload = decision.model_dump(mode="python")
    decision_payload["qualification_basis"] = "不同但格式有效的人工依据。"
    with pytest.raises(ValidationError, match="decision ID"):
        CreativeSampleRealAssetQualificationDecisionV2.model_validate(
            decision_payload,
            strict=True,
        )


def test_drift_issues_and_reviewer_role_conflicts_fail_closed(closure: Closure) -> None:
    with pytest.raises(RealAssetQualificationV2Error, match="closure"):
        build_real_asset_qualification_request_v2(
            pack=_make_pack("drifted"),
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            evidence_preparer_ref_sha256=_digest("evidence-preparer"),
            requested_at=REQUESTED_AT,
        )

    with pytest.raises(RealAssetQualificationV2Error, match="closure"):
        build_real_asset_qualification_request_v2(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_b,
            reviewer_b=closure.reviewer_a,
            pair_check=closure.pair_check,
            evidence_preparer_ref_sha256=_digest("evidence-preparer"),
            requested_at=REQUESTED_AT,
        )

    rejected_b = _make_review(
        pack=closure.pack,
        evidence=closure.evidence,
        role="REVIEWER_B",
        reviewed_at=REVIEW_B_AT,
        approved=False,
    )
    issue_pair = finalize_real_asset_review_pair_v2(
        pack=closure.pack,
        evidence=closure.evidence,
        reviewer_a=closure.reviewer_a,
        reviewer_b=rejected_b,
        evaluated_at=EVALUATED_AT,
    )
    assert issue_pair.issue_codes
    with pytest.raises(RealAssetQualificationV2Error, match="not issue-free"):
        build_real_asset_qualification_request_v2(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=rejected_b,
            pair_check=issue_pair,
            evidence_preparer_ref_sha256=_digest("evidence-preparer"),
            requested_at=REQUESTED_AT,
        )


def test_expiry_and_future_boundaries_are_exclusive_and_fail_closed() -> None:
    closure = _make_closure(valid_until="2026-08-17T12:30:00Z")
    request = _request(closure)
    assert request.request_valid_until == "2026-08-17T12:30:00Z"

    with pytest.raises(RealAssetQualificationV2Error, match="expired before decision"):
        _decision(closure, request, decision_at="2026-08-17T12:30:00Z")
    needs_human = _decision(
        closure,
        request,
        decision_at="2026-08-17T12:29:59Z",
        decision="NEEDS_HUMAN_REVIEW",
    )
    assert needs_human.eligible_for_separate_manifest_design_review is False

    with pytest.raises(RealAssetQualificationV2Error, match="past relative to PairCheck"):
        build_real_asset_qualification_request_v2(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            evidence_preparer_ref_sha256=_digest("evidence-preparer"),
            requested_at="2026-08-17T10:59:59Z",
        )
    with pytest.raises(RealAssetQualificationV2Error, match="expired rights evidence"):
        build_real_asset_qualification_request_v2(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            evidence_preparer_ref_sha256=_digest("evidence-preparer"),
            requested_at="2026-08-17T12:30:00Z",
        )

    perpetual_closure = _make_closure(valid_until="PERPETUAL")
    perpetual_request = _request(perpetual_closure)
    assert perpetual_request.request_valid_until == "2026-08-18T12:00:00Z"
    with pytest.raises(RealAssetQualificationV2Error, match="expired before decision"):
        _decision(
            perpetual_closure,
            perpetual_request,
            decision_at="2026-08-18T12:00:00Z",
        )


def test_preparer_qualifier_and_all_retained_records_must_be_independent(
    closure: Closure,
) -> None:
    with pytest.raises(RealAssetQualificationV2Error, match="must be distinct"):
        build_real_asset_qualification_request_v2(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            evidence_preparer_ref_sha256=closure.reviewer_a.reviewer_ref_sha256,
            requested_at=REQUESTED_AT,
        )
    request = _request(closure)
    common = {
        "pack": closure.pack,
        "evidence": closure.evidence,
        "reviewer_a": closure.reviewer_a,
        "reviewer_b": closure.reviewer_b,
        "pair_check": closure.pair_check,
        "request": request,
        "decision_at": DECISION_AT,
        "qualification_issue_codes": (),
        "qualification_basis": "独立资格审查员完成合成测试。",
        "decision": "PASS_ASSET_INTAKE_ONLY",
    }
    with pytest.raises(RealAssetQualificationV2Error, match="must be distinct"):
        build_real_asset_qualification_decision_v2(
            qualifier_ref_sha256=closure.reviewer_a.reviewer_ref_sha256,
            qualifier_record_sha256=_digest("qualifier-record"),
            **common,  # type: ignore[arg-type]
        )
    with pytest.raises(RealAssetQualificationV2Error, match="alias"):
        build_real_asset_qualification_decision_v2(
            qualifier_ref_sha256=_digest("qualifier-ref"),
            qualifier_record_sha256=closure.pack.objects[0].sha256,
            **common,  # type: ignore[arg-type]
        )


def test_strict_json_rejects_duplicates_unknown_fields_and_forged_authority(
    closure: Closure,
) -> None:
    request = _request(closure)
    decision = _decision(closure, request)
    request_raw = _canonical_document(request)
    decision_raw = _canonical_document(decision)
    assert parse_real_asset_qualification_request_v2_json(request_raw) == request
    assert parse_real_asset_qualification_decision_v2_json(decision_raw) == decision

    request_unknown = request.model_dump(mode="json")
    request_unknown["unknown"] = True
    with pytest.raises(RealAssetQualificationV2Error, match="strict contract"):
        parse_real_asset_qualification_request_v2_json(
            json.dumps(request_unknown).encode()
        )
    duplicate = (
        "{"
        + json.dumps("request_id")
        + ":"
        + json.dumps(request.request_id)
        + ","
        + request_raw.decode()[1:]
    ).encode()
    with pytest.raises(RealAssetQualificationV2Error, match="duplicate JSON key"):
        parse_real_asset_qualification_request_v2_json(duplicate)

    forged = decision.model_dump(mode="json")
    forged["execution_authorized"] = True
    with pytest.raises(RealAssetQualificationV2Error, match="strict contract"):
        parse_real_asset_qualification_decision_v2_json(json.dumps(forged).encode())
    forged["execution_authorized"] = False
    forged["rights_manifest_created"] = True
    with pytest.raises(RealAssetQualificationV2Error, match="strict contract"):
        parse_real_asset_qualification_decision_v2_json(json.dumps(forged).encode())


def test_policy_is_fixed_and_source_has_no_io_runtime_or_v1_qualifier(closure: Closure) -> None:
    request = _request(closure)
    payload = request.model_dump(mode="python")
    payload["policy_document_sha256"] = _digest("untrusted-policy")
    with pytest.raises(ValidationError, match="policy_document_sha256"):
        CreativeSampleRealAssetQualificationRequestV2.model_validate(payload, strict=True)
    payload = request.model_dump(mode="python")
    payload["policy_version"] = "1.0.0"
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetQualificationRequestV2.model_validate(payload, strict=True)

    request_schema = CreativeSampleRealAssetQualificationRequestV2.model_json_schema()
    decision_schema = CreativeSampleRealAssetQualificationDecisionV2.model_json_schema()
    assert request_schema["properties"]["policy_document_sha256"]["const"] == (
        QUALIFICATION_V2_POLICY_DOCUMENT_SHA256
    )
    assert decision_schema["properties"]["policy_document_sha256"]["const"] == (
        QUALIFICATION_V2_POLICY_DOCUMENT_SHA256
    )

    decision = _decision(closure, request)
    decision_payload = decision.model_dump(mode="python")
    decision_payload["qualification_issue_codes"] = ("POLICY_REQUIREMENT_NOT_MET",)
    with pytest.raises(ValidationError, match="positive decisions require no issue"):
        CreativeSampleRealAssetQualificationDecisionV2.model_validate(
            decision_payload,
            strict=True,
        )
    decision_payload = decision.model_dump(mode="python")
    decision_payload["decision"] = "REJECTED"
    decision_payload["eligible_for_separate_manifest_design_review"] = False
    with pytest.raises(ValidationError, match="negative decisions require an issue"):
        CreativeSampleRealAssetQualificationDecisionV2.model_validate(
            decision_payload,
            strict=True,
        )
    decision_payload["qualification_issue_codes"] = ("POLICY_REQUIREMENT_NOT_MET",)
    with pytest.raises(ValidationError, match="require the qualifier rejection"):
        CreativeSampleRealAssetQualificationDecisionV2.model_validate(
            decision_payload,
            strict=True,
        )
    decision_payload["decision"] = "NEEDS_HUMAN_REVIEW"
    decision_payload["qualification_issue_codes"] = (
        "QUALIFIER_REJECTED_ASSET_INTAKE",
    )
    with pytest.raises(ValidationError, match="cannot contain the qualifier rejection"):
        CreativeSampleRealAssetQualificationDecisionV2.model_validate(
            decision_payload,
            strict=True,
        )
    assert _decision(closure, request, decision="REJECTED").decision == "REJECTED"
    assert (
        _decision(closure, request, decision="NEEDS_HUMAN_REVIEW").decision
        == "NEEDS_HUMAN_REVIEW"
    )
    decision_payload["decision"] = "REJECTED"
    decision_payload["qualification_issue_codes"] = (
        "POLICY_REQUIREMENT_NOT_MET",
        "POLICY_REQUIREMENT_NOT_MET",
    )
    with pytest.raises(ValidationError, match="must be unique"):
        CreativeSampleRealAssetQualificationDecisionV2.model_validate(
            decision_payload,
            strict=True,
        )
    decision_payload["qualification_issue_codes"] = (
        "OTHER_BLOCKING_ISSUE",
        "POLICY_REQUIREMENT_NOT_MET",
    )
    with pytest.raises(ValidationError, match="canonical order"):
        CreativeSampleRealAssetQualificationDecisionV2.model_validate(
            decision_payload,
            strict=True,
        )

    source = inspect.getsource(__import__(
        "sdc.real_asset_qualification_v2",
        fromlist=["real_asset_qualification_v2"],
    ))
    for forbidden in (
        "CreativeSampleRealAssetRightsManifest",
        "qualify_real_asset_candidate_pack",
        "datetime.now",
        "datetime.utcnow",
        "Path(",
        "requests.",
        "httpx.",
        "provider_requests = 1",
    ):
        assert forbidden not in source
