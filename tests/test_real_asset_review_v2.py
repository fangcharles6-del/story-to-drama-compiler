from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from sdc import real_asset_review_v2 as review_module
from sdc.compiler import stable_id
from sdc.real_asset_intake import (
    CreativeSampleFrozenRealAssetPackManifest,
    FrozenRealAssetDescriptor,
    RealAudioTechnicalRecord,
    RealImageTechnicalRecord,
    _canonical_document,
    _canonical_payload,
    build_real_asset_intake_template,
)
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
    RealAssetHumanFindingV2,
    RealAssetReviewExceptionV2,
    RealAssetReviewV2Error,
    build_real_asset_human_findings_v2,
    build_real_asset_human_pack_review_v2,
    build_real_asset_rights_evidence_bundle_v2,
    finalize_real_asset_review_pair_v2,
    load_real_asset_human_pack_review_v2,
    load_real_asset_review_pair_check_v2,
    load_real_asset_rights_evidence_bundle_v2,
    write_new_real_asset_review_v2_document,
)

EVALUATED_AT = "2026-08-17T12:00:00Z"
VALID_UNTIL = "2027-08-17T12:00:00Z"


def _digest(label: str) -> str:
    return hashlib.sha256(f"sdc-review-v2-test:{label}".encode()).hexdigest()


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


@pytest.fixture(scope="module")
def pack() -> CreativeSampleFrozenRealAssetPackManifest:
    template = build_real_asset_intake_template()
    descriptors: list[FrozenRealAssetDescriptor] = []
    for requirement in template.requirements:
        media_sha256 = _digest(f"media:{requirement.ordinal}")
        media_size_bytes = 10_000 + requirement.ordinal
        if requirement.kind == "IMAGE":
            created_image = RealImageTechnicalRecord(
                width=512,
                height=512,
                color_space="RGB",
                distinct_color_count=256,
            )
            image_record: RealImageTechnicalRecord | None = created_image
            audio_record: RealAudioTechnicalRecord | None = None
            technical_evidence: RealImageTechnicalRecord | RealAudioTechnicalRecord = created_image
            duration_ms = 0
        else:
            duration_ms = 72_000 if requirement.kind == "BGM" else 250
            image_record = None
            audio_record = RealAudioTechnicalRecord(
                channels=2 if requirement.kind == "BGM" else 1,
                duration_ms=duration_ms,
                sample_count=48_000 * duration_ms // 1000,
                rms_millidbfs=-12_000,
                sample_peak_millidbfs=-1_000,
                silence_ppm=10_000,
            )
            technical_evidence = audio_record
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
                provenance_record_sha256=_digest(f"provenance:{requirement.ordinal}"),
                technical_profile=requirement.technical_profile,
                technical_record_sha256=_technical_digest(
                    kind=requirement.kind,
                    media_sha256=media_sha256,
                    media_size_bytes=media_size_bytes,
                    profile=requirement.technical_profile,
                    evidence=technical_evidence,
                ),
                image=image_record,
                audio=audio_record,
            )
        )
    objects = tuple(descriptors)
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-frozen-real-asset-pack",
        "profile": "creative-sample-real-asset-intake-v1",
        "template_id": template.template_id,
        "submission_id": stable_id("real_asset_submission", {"fixture": "review-v2"}),
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


@pytest.fixture(scope="module")
def evidence(
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> CreativeSampleRealAssetRightsEvidenceBundleV2:
    return build_real_asset_rights_evidence_bundle_v2(
        pack=pack,
        evidence_record_sha256=_digest("private-rights-evidence-record"),
        copyright_basis="私有记录逐项覆盖精确冻结字节及本次内部短剧评估。",
        likeness_basis="私有记录确认虚构形象及允许的本地合成声音使用范围。",
        privacy_basis="私有记录确认逐项完成隐私与个人信息检查。",
        territory="CN",
        use_scope="短剧内部评估、剪辑、合成及另行审批后的生成参考。",
        valid_until=VALID_UNTIL,
    )


def _review(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    role: str,
    reviewed_at: str,
    reviewer_ref_sha256: str | None = None,
    content_role_approvals: tuple[bool, ...] = (True,) * 14,
    exceptions: tuple[tuple[int, RealAssetReviewExceptionV2], ...] = (),
    provenance_approved: bool = True,
    copyright_approved: bool = True,
    likeness_approved: bool = True,
    privacy_approved: bool = True,
    territory_approved: bool = True,
    use_scope_approved: bool = True,
    decision: str = "APPROVED",
    rejection_reason: str | None = None,
) -> CreativeSampleRealAssetHumanPackReviewV2:
    findings = build_real_asset_human_findings_v2(
        pack=pack,
        confirmed_ordinals=tuple(range(14)),
        content_role_approvals=content_role_approvals,
        exceptions=exceptions,
    )
    return build_real_asset_human_pack_review_v2(
        pack=pack,
        evidence=evidence,
        reviewer_role=role,  # type: ignore[arg-type]
        reviewer_ref_sha256=reviewer_ref_sha256 or _digest(f"reviewer:{role}"),
        reviewed_at=reviewed_at,
        findings=findings,
        provenance_approved=provenance_approved,
        copyright_approved=copyright_approved,
        likeness_approved=likeness_approved,
        privacy_approved=privacy_approved,
        territory_approved=territory_approved,
        use_scope_approved=use_scope_approved,
        decision=decision,  # type: ignore[arg-type]
        rejection_reason=rejection_reason,
    )


def test_bundle_is_deterministic_exact_fourteen_and_zero_authority(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    rebuilt = build_real_asset_rights_evidence_bundle_v2(
        pack=pack,
        evidence_record_sha256=evidence.evidence_record_sha256,
        copyright_basis=evidence.copyright_basis,
        likeness_basis=evidence.likeness_basis,
        privacy_basis=evidence.privacy_basis,
        territory=evidence.territory,
        use_scope=evidence.use_scope,
        valid_until=evidence.valid_until,
    )

    assert rebuilt == evidence
    assert evidence.pack_manifest_sha256 == hashlib.sha256(
        _canonical_document(pack)
    ).hexdigest()
    assert tuple(item.ordinal for item in evidence.asset_bindings) == tuple(range(14))
    assert tuple(item.media_sha256 for item in evidence.asset_bindings) == tuple(
        item.sha256 for item in pack.objects
    )
    assert evidence.current_gate == "HUMAN_GATE"
    assert evidence.provider_state == "NOT_AUTHORIZED"
    assert evidence.execution_authorized is False
    assert evidence.posts_allowed == evidence.provider_requests == 0


def test_evidence_and_reviewer_digest_domains_cannot_alias_pack_or_asset_records(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    common = {
        "pack": pack,
        "copyright_basis": evidence.copyright_basis,
        "likeness_basis": evidence.likeness_basis,
        "privacy_basis": evidence.privacy_basis,
        "territory": evidence.territory,
        "use_scope": evidence.use_scope,
        "valid_until": evidence.valid_until,
    }
    for reserved_digest in (
        evidence.pack_manifest_sha256,
        pack.objects[0].sha256,
        pack.objects[0].provenance_record_sha256,
        pack.objects[0].technical_record_sha256,
    ):
        with pytest.raises(ValidationError, match="independent"):
            build_real_asset_rights_evidence_bundle_v2(
                evidence_record_sha256=reserved_digest,
                **common,  # type: ignore[arg-type]
            )

    findings = build_real_asset_human_findings_v2(
        pack=pack,
        confirmed_ordinals=tuple(range(14)),
        content_role_approvals=(True,) * 14,
    )
    for reserved_digest in (
        evidence.evidence_record_sha256,
        evidence.pack_manifest_sha256,
        hashlib.sha256(_canonical_document(evidence)).hexdigest(),
    ):
        with pytest.raises(RealAssetReviewV2Error, match="independent"):
            build_real_asset_human_pack_review_v2(
                pack=pack,
                evidence=evidence,
                reviewer_role="REVIEWER_A",
                reviewer_ref_sha256=reserved_digest,
                reviewed_at="2026-08-17T10:00:00Z",
                findings=findings,
                provenance_approved=True,
                copyright_approved=True,
                likeness_approved=True,
                privacy_approved=True,
                territory_approved=True,
                use_scope_approved=True,
                decision="APPROVED",
            )
    with pytest.raises(ValidationError, match="independent"):
        build_real_asset_human_pack_review_v2(
            pack=pack,
            evidence=evidence,
            reviewer_role="REVIEWER_A",
            reviewer_ref_sha256=pack.objects[0].sha256,
            reviewed_at="2026-08-17T10:00:00Z",
            findings=findings,
            provenance_approved=True,
            copyright_approved=True,
            likeness_approved=True,
            privacy_approved=True,
            territory_approved=True,
            use_scope_approved=True,
            decision="APPROVED",
        )


def test_findings_require_fourteen_explicit_inspections_and_content_results(
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    with pytest.raises(RealAssetReviewV2Error, match="fourteen assets.*confirmation"):
        build_real_asset_human_findings_v2(
            pack=pack,
            confirmed_ordinals=tuple(range(13)),
            content_role_approvals=(True,) * 14,
        )
    with pytest.raises(RealAssetReviewV2Error, match="content-role"):
        build_real_asset_human_findings_v2(
            pack=pack,
            confirmed_ordinals=tuple(range(14)),
            content_role_approvals=(True,) * 13,
        )
    binding = build_real_asset_human_findings_v2(
        pack=pack,
        confirmed_ordinals=tuple(range(14)),
        content_role_approvals=(True,) * 14,
    )[0].binding
    with pytest.raises(ValidationError):
        RealAssetHumanFindingV2.model_validate(
            {"binding": binding, "content_role_approved": True},
            strict=True,
        )
    schema = RealAssetHumanFindingV2.model_json_schema()
    assert "inspection_confirmed" in schema["required"]


def test_two_approved_pack_reviews_finalize_ready_but_grant_zero_authority(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    reviewer_a = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at="2026-08-17T10:00:00Z",
    )
    reviewer_b = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at="2026-08-17T11:00:00Z",
    )
    check = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        evaluated_at=EVALUATED_AT,
    )

    assert len(reviewer_a.findings) == len(reviewer_b.findings) == 14
    assert all(item.inspection_confirmed for item in reviewer_a.findings)
    assert all(item.content_role_approved for item in reviewer_a.findings)
    assert reviewer_a.review_record_sha256 != reviewer_b.review_record_sha256
    assert check.status == "READY_FOR_SEPARATE_QUALIFICATION_REVIEW"
    assert check.issue_codes == ()
    assert check.review_count == 2
    assert check.rights_manifest_created is False
    assert check.rights_qualification_performed is False
    assert check.current_gate == "HUMAN_GATE"
    assert check.provider_state == "NOT_AUTHORIZED"
    assert check.execution_authorized is False
    assert check.posts_allowed == check.provider_requests == 0
    assert finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        evaluated_at=EVALUATED_AT,
    ) == check


@pytest.mark.parametrize("alias_direction", ("A_USES_B", "B_USES_A"))
def test_pair_rejects_cross_role_reviewer_reference_aliasing_review_contract(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    alias_direction: str,
) -> None:
    normal_a = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at="2026-08-17T10:00:00Z",
    )
    normal_b = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at="2026-08-17T11:00:00Z",
    )
    if alias_direction == "A_USES_B":
        reviewer_a = _review(
            pack=pack,
            evidence=evidence,
            role="REVIEWER_A",
            reviewer_ref_sha256=hashlib.sha256(
                _canonical_document(normal_b)
            ).hexdigest(),
            reviewed_at="2026-08-17T10:00:00Z",
        )
        reviewer_b = normal_b
    else:
        reviewer_a = normal_a
        reviewer_b = _review(
            pack=pack,
            evidence=evidence,
            role="REVIEWER_B",
            reviewer_ref_sha256=hashlib.sha256(
                _canonical_document(normal_a)
            ).hexdigest(),
            reviewed_at="2026-08-17T11:00:00Z",
        )

    with pytest.raises(RealAssetReviewV2Error, match="must not alias canonical"):
        finalize_real_asset_review_pair_v2(
            pack=pack,
            evidence=evidence,
            reviewer_a=reviewer_a,
            reviewer_b=reviewer_b,
            evaluated_at=EVALUATED_AT,
        )


def test_review_digest_and_stable_id_reject_any_mutation(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    review = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at="2026-08-17T10:00:00Z",
    )
    payload = review.model_dump(mode="python")
    payload["reviewed_at"] = "2026-08-17T10:00:01Z"
    with pytest.raises(ValidationError, match="record digest"):
        CreativeSampleRealAssetHumanPackReviewV2.model_validate(payload, strict=True)

    bundle_payload = evidence.model_dump(mode="python")
    bundle_payload["territory"] = "CN-HK"
    with pytest.raises(ValidationError, match="bundle ID"):
        CreativeSampleRealAssetRightsEvidenceBundleV2.model_validate(
            bundle_payload, strict=True
        )


def test_exception_requires_its_exact_gate_to_fail_and_blocks_pair_readiness(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    exception = RealAssetReviewExceptionV2(
        failed_gates=("CONTENT_ROLE",),
        finding="对白内容与冻结角色不一致，停止本项复核。",
    )
    bad_findings = build_real_asset_human_findings_v2(
        pack=pack,
        confirmed_ordinals=tuple(range(14)),
        content_role_approvals=(True,) * 14,
        exceptions=((0, exception),),
    )
    with pytest.raises(ValidationError, match="content-role exception"):
        build_real_asset_human_pack_review_v2(
            pack=pack,
            evidence=evidence,
            reviewer_role="REVIEWER_A",
            reviewer_ref_sha256=_digest("reviewer:A:bad"),
            reviewed_at="2026-08-17T10:00:00Z",
            findings=bad_findings,
            provenance_approved=True,
            copyright_approved=True,
            likeness_approved=True,
            privacy_approved=True,
            territory_approved=True,
            use_scope_approved=True,
            decision="REJECTED",
            rejection_reason="素材角色检查未通过。",
        )

    content_results = (False,) + (True,) * 13
    reviewer_a = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at="2026-08-17T10:00:00Z",
        content_role_approvals=content_results,
        exceptions=((0, exception),),
        decision="REJECTED",
        rejection_reason="素材角色检查未通过。",
    )
    reviewer_b = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at="2026-08-17T11:00:00Z",
    )
    check = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        evaluated_at=EVALUATED_AT,
    )
    assert check.status == "DISAGREEMENT"
    assert "REVIEWER_A_NOT_APPROVED" in check.issue_codes
    assert "APPROVALS_DISAGREE" in check.issue_codes
    assert "REVIEWER_A_HAS_EXCEPTIONS" in check.issue_codes
    assert check.execution_authorized is False


def test_missing_reviewer_future_review_expiry_and_same_identity_fail_closed(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    reviewer_a = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at="2026-08-17T10:00:00Z",
    )
    incomplete = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=None,
        evaluated_at=EVALUATED_AT,
    )
    assert incomplete.status == "INCOMPLETE"
    assert incomplete.issue_codes == ("REVIEWER_B_MISSING",)

    same_identity_b = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at="2026-08-17T13:00:00Z",
        reviewer_ref_sha256=reviewer_a.reviewer_ref_sha256,
    )
    disputed = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=same_identity_b,
        evaluated_at=EVALUATED_AT,
    )
    assert disputed.status == "DISAGREEMENT"
    assert "REVIEWER_IDENTITIES_NOT_DISTINCT" in disputed.issue_codes
    assert "REVIEWER_B_IN_FUTURE" in disputed.issue_codes

    expired_evidence = build_real_asset_rights_evidence_bundle_v2(
        pack=pack,
        evidence_record_sha256=evidence.evidence_record_sha256,
        copyright_basis=evidence.copyright_basis,
        likeness_basis=evidence.likeness_basis,
        privacy_basis=evidence.privacy_basis,
        territory=evidence.territory,
        use_scope=evidence.use_scope,
        valid_until=EVALUATED_AT,
    )
    expired_a = _review(
        pack=pack,
        evidence=expired_evidence,
        role="REVIEWER_A",
        reviewed_at="2026-08-17T10:00:00Z",
    )
    expired_b = _review(
        pack=pack,
        evidence=expired_evidence,
        role="REVIEWER_B",
        reviewed_at="2026-08-17T11:00:00Z",
    )
    expired = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=expired_evidence,
        reviewer_a=expired_a,
        reviewer_b=expired_b,
        evaluated_at=EVALUATED_AT,
    )
    assert expired.status == "DISAGREEMENT"
    assert "RIGHTS_EXPIRED" in expired.issue_codes


def test_contextual_pack_or_finding_drift_is_a_hard_error(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    drifted_evidence = evidence.model_copy(
        update={"pack_manifest_sha256": "0" * 64}
    )
    with pytest.raises(RealAssetReviewV2Error, match="strict v2 contract|manifest digest drifted"):
        finalize_real_asset_review_pair_v2(
            pack=pack,
            evidence=drifted_evidence,
            reviewer_a=None,
            reviewer_b=None,
            evaluated_at=EVALUATED_AT,
        )


def test_tampered_model_copy_cannot_be_ready_built_or_written(
    tmp_path: Path,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    reviewer_a = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at="2026-08-17T10:00:00Z",
    )
    reviewer_b = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at="2026-08-17T11:00:00Z",
    )
    tampered_finding = reviewer_a.findings[0].model_copy(
        update={"inspection_confirmed": False}
    )
    tampered_review = reviewer_a.model_copy(
        update={"findings": (tampered_finding, *reviewer_a.findings[1:])}
    )
    with pytest.raises(RealAssetReviewV2Error, match="strict v2 contract"):
        finalize_real_asset_review_pair_v2(
            pack=pack,
            evidence=evidence,
            reviewer_a=tampered_review,
            reviewer_b=reviewer_b,
            evaluated_at=EVALUATED_AT,
        )
    with pytest.raises(ValidationError):
        build_real_asset_human_pack_review_v2(
            pack=pack,
            evidence=evidence,
            reviewer_role="REVIEWER_A",
            reviewer_ref_sha256=_digest("reviewer:tampered-finding"),
            reviewed_at="2026-08-17T10:00:00Z",
            findings=(tampered_finding, *reviewer_a.findings[1:]),
            provenance_approved=True,
            copyright_approved=True,
            likeness_approved=True,
            privacy_approved=True,
            territory_approved=True,
            use_scope_approved=True,
            decision="APPROVED",
        )
    review_output = tmp_path / "tampered-review.json"
    with pytest.raises(RealAssetReviewV2Error, match="strict v2 contract"):
        write_new_real_asset_review_v2_document(review_output, tampered_review)
    assert not review_output.exists()

    tampered_evidence = evidence.model_copy(update={"territory": "CN-HK"})
    evidence_output = tmp_path / "tampered-evidence.json"
    with pytest.raises(RealAssetReviewV2Error, match="strict v2 contract"):
        write_new_real_asset_review_v2_document(evidence_output, tampered_evidence)
    assert not evidence_output.exists()

    review = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at="2026-08-17T10:00:00Z",
    )
    first = review.findings[0]
    drifted_binding = first.binding.model_copy(update={"media_size_bytes": 1})
    drifted_finding = first.model_copy(update={"binding": drifted_binding})
    drifted_review = review.model_copy(
        update={"findings": (drifted_finding, *review.findings[1:])}
    )
    with pytest.raises(RealAssetReviewV2Error, match="strict v2 contract|findings drifted"):
        finalize_real_asset_review_pair_v2(
            pack=pack,
            evidence=evidence,
            reviewer_a=drifted_review,
            reviewer_b=None,
            evaluated_at=EVALUATED_AT,
        )


def test_strict_loaders_and_writer_are_canonical_local_and_new_only(
    tmp_path: Path,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    reviewer_a = _review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at="2026-08-17T10:00:00Z",
    )
    check = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=None,
        evaluated_at=EVALUATED_AT,
    )
    documents = (
        ("evidence.json", evidence, load_real_asset_rights_evidence_bundle_v2),
        ("review-a.json", reviewer_a, load_real_asset_human_pack_review_v2),
        ("pair-check.json", check, load_real_asset_review_pair_check_v2),
    )
    for name, document, loader in documents:
        path = tmp_path / name
        assert write_new_real_asset_review_v2_document(path, document) == path.absolute()
        assert path.read_bytes() == _canonical_document(document)
        assert loader(path) == document
        with pytest.raises(RealAssetReviewV2Error, match="new local file"):
            write_new_real_asset_review_v2_document(path, document)

    noncanonical = tmp_path / "noncanonical.json"
    noncanonical.write_text(
        json.dumps(evidence.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    with pytest.raises(RealAssetReviewV2Error, match="canonical"):
        load_real_asset_rights_evidence_bundle_v2(noncanonical)


def test_pair_check_contract_rejects_fake_ready_or_authority(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    incomplete = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=None,
        reviewer_b=None,
        evaluated_at=EVALUATED_AT,
    )
    payload = incomplete.model_dump(mode="python")
    payload["status"] = "READY_FOR_SEPARATE_QUALIFICATION_REVIEW"
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetReviewPairCheckV2.model_validate(payload, strict=True)
    payload = incomplete.model_dump(mode="python")
    payload["execution_authorized"] = True
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetReviewPairCheckV2.model_validate(payload, strict=True)


def test_review_v2_has_no_clock_network_provider_or_authority_dependency() -> None:
    source = inspect.getsource(review_module)
    assert "datetime.now" not in source
    assert "utcnow" not in source
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert "qualify_real_asset_candidate_pack" not in source
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    assert imported.isdisjoint(
        {
            "aiohttp",
            "asyncpg",
            "httpx",
            "requests",
            "socket",
            "sqlalchemy",
            "temporalio",
            "urllib",
            "sdc.ark_provider",
            "sdc.evidence_authorization",
            "sdc.evidence_ledger",
            "sdc.persistence",
            "sdc.temporal_workflows",
            "sdc.worker",
        }
    )
