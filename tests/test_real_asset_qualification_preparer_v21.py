from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

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
from sdc.real_asset_qualification_preparer_v21 import (
    TrustedLocalRequestPaths,
    TrustedLocalRequestPreparationError,
    inspect_ready,
    main,
    prepare_request,
    verify_request,
)
from sdc.real_asset_qualification_v2 import (
    CreativeSampleRealAssetQualificationRequestV2,
    RealAssetQualificationV2Error,
    parse_real_asset_qualification_request_v2_json,
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

NOW = "2026-08-18T10:30:00Z"
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


def _make_pack() -> tuple[CreativeSampleFrozenRealAssetPackManifest, tuple[bytes, ...]]:
    template = build_real_asset_intake_template()
    media_bytes = tuple(
        f"synthetic-media-{ordinal}:".encode() + bytes([ordinal + 1]) * (80 + ordinal)
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
                    f"synthetic-provenance-{requirement.ordinal}".encode()
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
        "submission_id": stable_id("real_asset_submission", {"fixture": "preparer-v21"}),
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


@dataclass(frozen=True)
class SyntheticClosure:
    paths: TrustedLocalRequestPaths
    pack: CreativeSampleFrozenRealAssetPackManifest
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2
    pair_check: CreativeSampleRealAssetReviewPairCheckV2
    verifier_calls: list[Path]


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path.resolve()


def _request_output(tmp_path: Path, name: str) -> Path:
    parent = (tmp_path / "request-outputs").resolve()
    parent.mkdir(exist_ok=True)
    return parent / name


@pytest.fixture
def closure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SyntheticClosure:
    pack, media_bytes = _make_pack()
    pack_root = (tmp_path / pack.pack_id).resolve()
    pack_root.mkdir()
    media_paths: list[Path] = []
    for descriptor, raw in zip(pack.objects, media_bytes, strict=True):
        media_paths.append(_write(pack_root / Path(descriptor.object_path), raw))
    manifest_path = _write(pack_root / "asset-pack.json", _canonical_document(pack))

    evidence_record = _write(
        tmp_path / "records" / "evidence-retained.txt",
        b"synthetic retained evidence record",
    )
    preparer_ref = _write(
        tmp_path / "records" / "evidence-preparer-ref.txt",
        b"synthetic independent evidence preparer",
    )
    reviewer_a_record = _write(
        tmp_path / "records" / "reviewer-a-retained.txt",
        b"synthetic reviewer A retained identity",
    )
    reviewer_b_record = _write(
        tmp_path / "records" / "reviewer-b-retained.txt",
        b"synthetic reviewer B retained identity",
    )
    evidence = build_real_asset_rights_evidence_bundle_v2(
        pack=pack,
        evidence_record_sha256=_sha(evidence_record.read_bytes()),
        copyright_basis="合成测试权利记录覆盖精确冻结字节。",
        likeness_basis="合成测试确认虚构形象及离线声音范围。",
        privacy_basis="合成测试确认逐项隐私检查。",
        territory="CN",
        use_scope="仅用于本地 prepare-only 合成测试。",
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
    paths = TrustedLocalRequestPaths(
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
    calls: list[Path] = []

    def verify(root: Path) -> FrozenRealAssetPack:
        calls.append(root)
        if root != pack_root:
            raise AssertionError("synthetic verifier received a different root")
        return FrozenRealAssetPack(
            root=pack_root,
            manifest_path=manifest_path,
            manifest=pack,
            created=False,
        )

    monkeypatch.setattr(preparer_module, "verify_real_asset_candidate_pack", verify)
    return SyntheticClosure(
        paths=paths,
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        verifier_calls=calls,
    )


def _cli_args(paths: TrustedLocalRequestPaths) -> list[str]:
    values = [
        "--pack-root",
        str(paths.pack_root),
        "--pack-manifest",
        str(paths.pack_manifest),
    ]
    for path in paths.media_paths:
        values.extend(("--media-path", str(path)))
    values.extend(
        (
            "--evidence",
            str(paths.evidence_bundle),
            "--reviewer-a",
            str(paths.reviewer_a),
            "--reviewer-b",
            str(paths.reviewer_b),
            "--pair-check",
            str(paths.pair_check),
            "--evidence-retained-record",
            str(paths.evidence_retained_record),
            "--evidence-preparer-ref",
            str(paths.evidence_preparer_ref),
            "--reviewer-a-retained-record",
            str(paths.reviewer_a_retained_record),
            "--reviewer-b-retained-record",
            str(paths.reviewer_b_retained_record),
        )
    )
    return values


def test_inspect_prepare_and_verify_exact_zero_authority_closure(
    closure: SyntheticClosure,
    tmp_path: Path,
) -> None:
    inspected = inspect_ready(closure.paths, requested_at=NOW)
    output = _request_output(tmp_path, "request-v2.json")
    prepared = prepare_request(closure.paths, output, requested_at=NOW)
    verified = verify_request(closure.paths, output, observed_at=NOW)

    assert inspected == prepared == verified
    assert parse_real_asset_qualification_request_v2_json(output.read_bytes()) == prepared
    assert output.read_bytes() == _canonical_document(prepared)
    assert prepared.status == "QUALIFICATION_REQUESTED"
    assert prepared.rights_manifest_created is False
    assert prepared.rights_qualification_performed is False
    assert prepared.current_gate == "HUMAN_GATE"
    assert prepared.provider_state == "NOT_AUTHORIZED"
    assert prepared.eligible_for_real_generation is False
    assert prepared.execution_authorized is False
    assert prepared.posts_allowed == prepared.provider_requests == 0
    assert len(closure.verifier_calls) == 7


def test_timestamps_are_explicit_canonical_and_no_wall_clock_is_read(
    closure: SyntheticClosure,
    tmp_path: Path,
) -> None:
    source = inspect.getsource(preparer_module)
    assert "datetime.now" not in source
    assert "datetime.utcnow" not in source
    assert "time.time" not in source
    inspect_ready(closure.paths, requested_at=NOW)
    output = _request_output(tmp_path, "clock-request.json")
    prepare_request(closure.paths, output, requested_at=NOW)
    verify_request(closure.paths, output, observed_at=NOW)
    with pytest.raises(TrustedLocalRequestPreparationError, match="canonical UTC"):
        inspect_ready(closure.paths, requested_at="2026-08-18T10:30:00+00:00")
    with pytest.raises(TrustedLocalRequestPreparationError, match="canonical UTC"):
        verify_request(closure.paths, output, observed_at="2026-08-18 10:30:00Z")


def test_verify_rejects_future_and_expired_request(
    closure: SyntheticClosure,
    tmp_path: Path,
) -> None:
    output = _request_output(tmp_path, "finite-request.json")
    prepare_request(closure.paths, output, requested_at=NOW)
    with pytest.raises(TrustedLocalRequestPreparationError, match="future"):
        verify_request(
            closure.paths,
            output,
            observed_at="2026-08-18T10:29:59Z",
        )
    with pytest.raises(TrustedLocalRequestPreparationError, match="expired"):
        verify_request(
            closure.paths,
            output,
            observed_at="2026-08-19T10:30:00Z",
        )


@pytest.mark.parametrize("count", (0, 13, 15))
def test_exactly_fourteen_explicit_manifest_ordered_media_are_required(
    closure: SyntheticClosure,
    count: int,
) -> None:
    supplied = closure.paths.media_paths[:count]
    if count == 15:
        supplied = (*closure.paths.media_paths, closure.paths.evidence_bundle)
    with pytest.raises(TrustedLocalRequestPreparationError, match="fourteen"):
        inspect_ready(replace(closure.paths, media_paths=tuple(supplied)), requested_at=NOW)

    swapped = list(closure.paths.media_paths)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    with pytest.raises(TrustedLocalRequestPreparationError, match="manifest order"):
        inspect_ready(replace(closure.paths, media_paths=tuple(swapped)), requested_at=NOW)


def test_manifest_and_every_input_must_be_explicit_absolute_and_separated(
    closure: SyntheticClosure,
) -> None:
    with pytest.raises(TrustedLocalRequestPreparationError, match="exact manifest"):
        inspect_ready(
            replace(closure.paths, pack_manifest=closure.paths.evidence_bundle),
            requested_at=NOW,
        )
    with pytest.raises(TrustedLocalRequestPreparationError, match="absolute"):
        inspect_ready(
            replace(closure.paths, evidence_bundle=Path("evidence.json")),
            requested_at=NOW,
        )
    with pytest.raises(TrustedLocalRequestPreparationError, match="outside the frozen Pack"):
        inspect_ready(
            replace(closure.paths, evidence_bundle=closure.paths.pack_manifest),
            requested_at=NOW,
        )


def test_mutable_alias_tokens_are_rejected_for_every_input_class(
    closure: SyntheticClosure,
    tmp_path: Path,
) -> None:
    aliased_pack = (tmp_path / "pack-latest").resolve()
    with pytest.raises(TrustedLocalRequestPreparationError, match="mutable alias"):
        inspect_ready(
            replace(closure.paths, pack_root=aliased_pack),
            requested_at=NOW,
        )

    aliased_contract = _write(
        closure.paths.evidence_bundle.with_name("evidence-current.json"),
        closure.paths.evidence_bundle.read_bytes(),
    )
    with pytest.raises(TrustedLocalRequestPreparationError, match="mutable alias"):
        inspect_ready(
            replace(closure.paths, evidence_bundle=aliased_contract),
            requested_at=NOW,
        )

    aliased_record = _write(
        closure.paths.evidence_preparer_ref.with_name("preparer-newest.txt"),
        closure.paths.evidence_preparer_ref.read_bytes(),
    )
    with pytest.raises(TrustedLocalRequestPreparationError, match="mutable alias"):
        inspect_ready(
            replace(closure.paths, evidence_preparer_ref=aliased_record),
            requested_at=NOW,
        )

    request = _request_output(tmp_path, "stable-request.json")
    prepare_request(closure.paths, request, requested_at=NOW)
    aliased_request = _write(
        request.with_name("request-latest.json"),
        request.read_bytes(),
    )
    with pytest.raises(TrustedLocalRequestPreparationError, match="mutable alias"):
        verify_request(closure.paths, aliased_request, observed_at=NOW)


def test_git_tree_symlink_and_hardlink_inputs_fail_closed(
    closure: SyntheticClosure,
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    with pytest.raises(TrustedLocalRequestPreparationError, match="Git tree"):
        inspect_ready(closure.paths, requested_at=NOW)
    (tmp_path / ".git").rmdir()

    linked = (tmp_path / "records" / "hardlinked-preparer.txt").resolve()
    try:
        os.link(closure.paths.evidence_preparer_ref, linked)
    except OSError:
        pytest.skip("hard links are unavailable on this host")
    with pytest.raises(TrustedLocalRequestPreparationError, match="non-linked"):
        inspect_ready(
            replace(closure.paths, evidence_preparer_ref=linked),
            requested_at=NOW,
        )


def test_symlink_input_fails_closed_when_supported(
    closure: SyntheticClosure,
    tmp_path: Path,
) -> None:
    linked = (tmp_path / "records" / "linked-preparer.txt").resolve()
    try:
        linked.symlink_to(closure.paths.evidence_preparer_ref)
    except OSError:
        pytest.skip("symbolic links are unavailable on this host")
    with pytest.raises(TrustedLocalRequestPreparationError, match="safe local path"):
        inspect_ready(
            replace(closure.paths, evidence_preparer_ref=linked),
            requested_at=NOW,
        )


def test_digest_alias_and_record_contract_mismatch_fail_closed(
    closure: SyntheticClosure,
    tmp_path: Path,
) -> None:
    alias = _write(
        tmp_path / "records" / "copied-evidence.txt",
        closure.paths.evidence_retained_record.read_bytes(),
    )
    with pytest.raises(TrustedLocalRequestPreparationError, match="digest alias"):
        inspect_ready(
            replace(closure.paths, evidence_preparer_ref=alias),
            requested_at=NOW,
        )

    mismatch = _write(
        tmp_path / "records" / "different-reviewer-a.txt",
        b"different synthetic reviewer",
    )
    with pytest.raises(TrustedLocalRequestPreparationError, match="digest disagrees"):
        inspect_ready(
            replace(closure.paths, reviewer_a_retained_record=mismatch),
            requested_at=NOW,
        )


def test_duplicate_noncanonical_or_unknown_contract_json_fails_closed(
    closure: SyntheticClosure,
) -> None:
    original = closure.paths.pair_check.read_bytes()
    duplicate = (
        b'{"status":"READY_FOR_SEPARATE_QUALIFICATION_REVIEW",'
        + original[1:]
    )
    closure.paths.pair_check.write_bytes(duplicate)
    with pytest.raises(TrustedLocalRequestPreparationError, match="duplicate JSON"):
        inspect_ready(closure.paths, requested_at=NOW)


@pytest.mark.parametrize("mutation", ("unknown", "noncanonical"))
def test_unknown_and_noncanonical_contract_json_fail_closed(
    closure: SyntheticClosure,
    mutation: str,
) -> None:
    payload = closure.evidence.model_dump(mode="json")
    if mutation == "unknown":
        payload["unknown"] = True
        raw = (
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode()
        match = "strict contract"
    else:
        raw = (json.dumps(payload, ensure_ascii=False) + "\n").encode()
        match = "not canonical"
    closure.paths.evidence_bundle.write_bytes(raw)
    with pytest.raises(TrustedLocalRequestPreparationError, match=match):
        inspect_ready(closure.paths, requested_at=NOW)


def test_nonready_paircheck_with_issues_fails_closed(
    closure: SyntheticClosure,
) -> None:
    incomplete = finalize_real_asset_review_pair_v2(
        pack=closure.pack,
        evidence=closure.evidence,
        reviewer_a=closure.reviewer_a,
        reviewer_b=None,
        evaluated_at=EVALUATED_AT,
    )
    assert incomplete.status != "READY_FOR_SEPARATE_QUALIFICATION_REVIEW"
    assert incomplete.issue_codes
    closure.paths.pair_check.write_bytes(_canonical_document(incomplete))
    with pytest.raises(TrustedLocalRequestPreparationError, match="not issue-free and ready"):
        inspect_ready(closure.paths, requested_at=NOW)


def test_prepare_is_new_only_rejects_mutable_alias_and_pack_overlap(
    closure: SyntheticClosure,
    tmp_path: Path,
) -> None:
    existing = _write(
        _request_output(tmp_path, "existing-request.json"),
        b"do not overwrite",
    )
    with pytest.raises(TrustedLocalRequestPreparationError, match="new file"):
        prepare_request(closure.paths, existing, requested_at=NOW)
    assert existing.read_bytes() == b"do not overwrite"

    latest = _request_output(tmp_path, "qualification-request-latest.json")
    with pytest.raises(TrustedLocalRequestPreparationError, match="mutable alias"):
        prepare_request(closure.paths, latest, requested_at=NOW)
    assert not latest.exists()

    inside_pack = (closure.paths.pack_root / "request.json").resolve()
    with pytest.raises(TrustedLocalRequestPreparationError, match="outside the Pack"):
        prepare_request(closure.paths, inside_pack, requested_at=NOW)
    assert not inside_pack.exists()

    same_contract_parent = closure.paths.evidence_bundle.parent / "request.json"
    with pytest.raises(TrustedLocalRequestPreparationError, match="trust area"):
        prepare_request(closure.paths, same_contract_parent, requested_at=NOW)
    nested_record_parent = closure.paths.evidence_retained_record.parent / "nested-output"
    nested_record_parent.mkdir()
    with pytest.raises(TrustedLocalRequestPreparationError, match="trust area"):
        prepare_request(
            closure.paths,
            nested_record_parent / "request.json",
            requested_at=NOW,
        )
    containing_parent = tmp_path / "request-in-containing-parent.json"
    with pytest.raises(TrustedLocalRequestPreparationError, match="trust area"):
        prepare_request(closure.paths, containing_parent, requested_at=NOW)


@pytest.mark.parametrize("relationship", ("equal", "nested", "containing"))
def test_verify_request_parent_requires_an_independent_trust_area(
    closure: SyntheticClosure,
    tmp_path: Path,
    relationship: str,
) -> None:
    source = _request_output(tmp_path, "source-request.json")
    prepare_request(closure.paths, source, requested_at=NOW)
    contract_parent = closure.paths.evidence_bundle.parent
    if relationship == "equal":
        target = contract_parent / "verified-request.json"
    elif relationship == "nested":
        nested = contract_parent / "nested-request-area"
        nested.mkdir()
        target = nested / "verified-request.json"
    else:
        target = tmp_path / "verified-request.json"
    _write(target, source.read_bytes())
    with pytest.raises(TrustedLocalRequestPreparationError, match="trust area"):
        verify_request(closure.paths, target, observed_at=NOW)


@pytest.mark.parametrize(
    "failure",
    ("short-write", "fsync", "parent-fsync", "parse"),
)
def test_create_failure_removes_only_this_operation_partial_file(
    closure: SyntheticClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    output = _request_output(tmp_path, f"create-failure-{failure}.json")
    if failure == "short-write":
        original_write = os.write
        calls = 0

        def short_write(descriptor: int, data: bytes) -> int:
            nonlocal calls
            calls += 1
            if calls == 1:
                return original_write(descriptor, data[:17])
            return 0

        monkeypatch.setattr(os, "write", short_write)
    elif failure == "fsync":

        def reject_fsync(descriptor: int) -> None:
            del descriptor
            raise OSError("synthetic fsync failure")

        monkeypatch.setattr(os, "fsync", reject_fsync)
    elif failure == "parent-fsync":
        if os.name == "nt":

            def reject_parent_fsync(created: object) -> None:
                del created
                raise OSError("synthetic parent fsync failure")

            monkeypatch.setattr(
                preparer_module,
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

        def reject_request(raw: bytes) -> CreativeSampleRealAssetQualificationRequestV2:
            del raw
            raise RealAssetQualificationV2Error("synthetic parser failure")

        monkeypatch.setattr(
            preparer_module,
            "parse_real_asset_qualification_request_v2_json",
            reject_request,
        )
    with pytest.raises(TrustedLocalRequestPreparationError):
        prepare_request(closure.paths, output, requested_at=NOW)
    assert not output.exists()


def test_delete_failure_cannot_leave_a_valid_request_artifact(
    closure: SyntheticClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _request_output(tmp_path, "delete-failure.json")
    original_capture = preparer_module._capture_ready
    calls = 0

    def fail_after_create(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TrustedLocalRequestPreparationError("synthetic post-create failure")
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(preparer_module, "_capture_ready", fail_after_create)
    if os.name == "nt":
        monkeypatch.setattr(
            preparer_module,
            "_delete_open_windows_request",
            lambda descriptor: False,
        )
    else:
        monkeypatch.setattr(
            preparer_module,
            "_unlink_open_posix_request",
            lambda created, identity: False,
        )
    with pytest.raises(TrustedLocalRequestPreparationError):
        prepare_request(closure.paths, output, requested_at=NOW)
    assert output.exists()
    assert output.read_bytes() in {b"", b"\0"}
    with pytest.raises(RealAssetQualificationV2Error):
        parse_real_asset_qualification_request_v2_json(output.read_bytes())


def test_truncate_and_delete_failure_fallback_poison_is_not_a_valid_request(
    closure: SyntheticClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _request_output(tmp_path, "truncate-delete-failure.json")
    original_capture = preparer_module._capture_ready
    calls = 0

    def fail_after_create(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TrustedLocalRequestPreparationError("synthetic post-create failure")
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    def reject_truncate(descriptor: int, length: int) -> None:
        del descriptor, length
        raise OSError("synthetic truncate failure")

    monkeypatch.setattr(preparer_module, "_capture_ready", fail_after_create)
    monkeypatch.setattr(os, "ftruncate", reject_truncate)
    if os.name == "nt":
        monkeypatch.setattr(
            preparer_module,
            "_delete_open_windows_request",
            lambda descriptor: False,
        )
    else:
        monkeypatch.setattr(
            preparer_module,
            "_unlink_open_posix_request",
            lambda created, identity: False,
        )
    with pytest.raises(TrustedLocalRequestPreparationError):
        prepare_request(closure.paths, output, requested_at=NOW)
    poisoned = output.read_bytes()
    assert poisoned.startswith(b"\0")
    with pytest.raises(RealAssetQualificationV2Error):
        parse_real_asset_qualification_request_v2_json(poisoned)


def test_both_rollback_mechanisms_false_are_reported_not_silenced(
    closure: SyntheticClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _request_output(tmp_path, "rollback-both-false.json")
    original_capture = preparer_module._capture_ready
    calls = 0

    def fail_after_create(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TrustedLocalRequestPreparationError("synthetic post-create failure")
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(preparer_module, "_capture_ready", fail_after_create)
    monkeypatch.setattr(
        preparer_module,
        "_invalidate_open_request",
        lambda descriptor: False,
    )
    if os.name == "nt":
        monkeypatch.setattr(
            preparer_module,
            "_delete_open_windows_request",
            lambda descriptor: False,
        )
    else:
        monkeypatch.setattr(
            preparer_module,
            "_unlink_open_posix_request",
            lambda created, identity: False,
        )
    with pytest.raises(TrustedLocalRequestPreparationError, match="rollback failed closed"):
        prepare_request(closure.paths, output, requested_at=NOW)


def test_output_parent_swap_is_detected_before_create(
    closure: SyntheticClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _request_output(tmp_path, "parent-swap.json")
    parent = output.parent
    moved_parent = parent.with_name("request-outputs-original")
    original_capture = preparer_module._capture_ready
    calls = 0

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        result = original_capture(*args, **kwargs)  # type: ignore[arg-type]
        calls += 1
        if calls == 2:
            parent.rename(moved_parent)
            parent.mkdir()
        return result

    monkeypatch.setattr(preparer_module, "_capture_ready", capture)
    with pytest.raises(TrustedLocalRequestPreparationError, match="parent identity"):
        prepare_request(closure.paths, output, requested_at=NOW)
    assert not output.exists()
    assert not (moved_parent / output.name).exists()


def test_parent_is_revalidated_again_after_guard_and_before_exclusive_open(
    closure: SyntheticClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _request_output(tmp_path, "guarded-parent-order.json")
    events: list[str] = []
    original_revalidate = preparer_module._revalidate_output_target
    original_acquire = preparer_module._acquire_parent_guard
    original_open = preparer_module._open_exclusive_request

    def revalidate(*args: object, **kwargs: object) -> None:
        events.append("revalidate")
        original_revalidate(*args, **kwargs)  # type: ignore[arg-type]

    def acquire(*args: object, **kwargs: object) -> tuple[int, bool]:
        events.append("acquire")
        return original_acquire(*args, **kwargs)  # type: ignore[arg-type]

    def open_request(*args: object, **kwargs: object) -> int:
        events.append("open")
        return original_open(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(preparer_module, "_revalidate_output_target", revalidate)
    monkeypatch.setattr(preparer_module, "_acquire_parent_guard", acquire)
    monkeypatch.setattr(preparer_module, "_open_exclusive_request", open_request)
    prepare_request(closure.paths, output, requested_at=NOW)
    assert events[:4] == ["revalidate", "acquire", "revalidate", "open"]


def test_replacement_during_failure_is_never_deleted_as_this_operations_file(
    closure: SyntheticClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _request_output(tmp_path, "replacement-race.json")
    replacement = _write(output.parent / "independent-replacement.bin", b"independent replacement")
    original_capture = preparer_module._capture_ready
    calls = 0
    replacement_succeeded = False

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls, replacement_succeeded
        calls += 1
        if calls == 3:
            try:
                os.replace(replacement, output)
            except PermissionError:
                raise OSError("replacement denied by retained exact handle") from None
            replacement_succeeded = True
        return original_capture(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(preparer_module, "_capture_ready", capture)
    with pytest.raises(TrustedLocalRequestPreparationError):
        prepare_request(closure.paths, output, requested_at=NOW)
    if replacement_succeeded:
        assert output.read_bytes() == b"independent replacement"
    else:
        assert not output.exists()
        assert replacement.read_bytes() == b"independent replacement"


@pytest.mark.parametrize("mutate_on_call", (2, 3))
def test_prewrite_and_postwrite_toctou_drift_leave_no_request(
    closure: SyntheticClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate_on_call: int,
) -> None:
    calls = 0
    record = closure.paths.evidence_preparer_ref
    original_bytes = record.read_bytes()

    def verify(root: Path) -> FrozenRealAssetPack:
        nonlocal calls
        calls += 1
        if calls == mutate_on_call:
            replacement = record.with_suffix(".replacement")
            replacement.write_bytes(original_bytes)
            os.replace(replacement, record)
        return FrozenRealAssetPack(
            root=closure.paths.pack_root,
            manifest_path=closure.paths.pack_manifest,
            manifest=closure.pack,
            created=False,
        )

    monkeypatch.setattr(preparer_module, "verify_real_asset_candidate_pack", verify)
    output = _request_output(tmp_path, f"drift-{mutate_on_call}.json")
    with pytest.raises(TrustedLocalRequestPreparationError, match="drifted"):
        prepare_request(closure.paths, output, requested_at=NOW)
    assert not output.exists()


def test_tampered_existing_request_and_request_alias_fail_closed(
    closure: SyntheticClosure,
    tmp_path: Path,
) -> None:
    output = _request_output(tmp_path, "request-to-tamper.json")
    request = prepare_request(closure.paths, output, requested_at=NOW)
    payload = request.model_dump(mode="json")
    payload["unknown"] = True
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TrustedLocalRequestPreparationError, match="strict contract"):
        verify_request(closure.paths, output, observed_at=NOW)

    with pytest.raises(TrustedLocalRequestPreparationError, match="alias"):
        verify_request(
            closure.paths,
            closure.paths.evidence_bundle,
            observed_at=NOW,
        )


def test_cli_has_exact_commands_no_sensitive_finalizer_inputs_and_redacts_output(
    closure: SyntheticClosure,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = inspect.getsource(preparer_module)
    assert source.count('add_parser("inspect-ready")') == 1
    assert source.count('add_parser("prepare-request")') == 1
    assert source.count('add_parser("verify-request")') == 1
    for forbidden in (
        "--decision",
        "--basis",
        "--qualifier",
        "build_real_asset_qualification_decision_v2",
        "human_review_finalizer",
        ".glob(",
        ".rglob(",
    ):
        assert forbidden not in source

    assert main(
        ["inspect-ready", *_cli_args(closure.paths), "--requested-at", NOW]
    ) == 0
    stdout = capsys.readouterr().out
    summary = json.loads(stdout)
    assert summary["operation"] == "inspect-ready"
    assert summary["status"] == "READY_FOR_REQUEST_PREPARATION"
    assert "request_id" not in summary
    assert summary["current_gate"] == "HUMAN_GATE"
    assert summary["provider_state"] == "NOT_AUTHORIZED"
    assert summary["execution_authorized"] is False
    assert summary["posts_allowed"] == summary["provider_requests"] == 0
    assert str(tmp_path) not in stdout
    assert closure.evidence.copyright_basis not in stdout
    for digest in (
        closure.evidence.evidence_record_sha256,
        closure.reviewer_a.reviewer_ref_sha256,
        closure.reviewer_b.reviewer_ref_sha256,
    ):
        assert digest not in stdout

    output = _request_output(tmp_path, "cli-request.json")
    assert main(
        [
            "prepare-request",
            *_cli_args(closure.paths),
            "--output",
            str(output),
            "--requested-at",
            NOW,
        ]
    ) == 0
    capsys.readouterr()
    assert main(
        [
            "verify-request",
            *_cli_args(closure.paths),
            "--request",
            str(output),
            "--observed-at",
            NOW,
        ]
    ) == 0


def test_cli_failure_is_generic_and_does_not_echo_private_values(
    closure: SyntheticClosure,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad = replace(closure.paths, evidence_preparer_ref=Path("private-record.txt"))
    assert main(
        ["inspect-ready", *_cli_args(bad), "--requested-at", NOW]
    ) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "private-record" not in captured.err
    assert "SHA" not in captured.err
    assert "FAILED_CLOSED" in captured.err


@pytest.mark.parametrize("case", ("command", "unknown-flag", "timestamp"))
def test_cli_parser_errors_never_echo_private_markers(
    closure: SyntheticClosure,
    capsys: pytest.CaptureFixture[str],
    case: str,
) -> None:
    marker = "PRIVATE-MARKER-DO-NOT-ECHO"
    if case == "command":
        argv = [marker]
    elif case == "unknown-flag":
        argv = [
            "inspect-ready",
            *_cli_args(closure.paths),
            "--requested-at",
            NOW,
            "--private-marker",
            marker,
        ]
    else:
        argv = [
            "inspect-ready",
            *_cli_args(closure.paths),
            "--requested-at",
            marker,
        ]
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert marker not in captured.err
    assert "usage:" not in captured.err
    assert json.loads(captured.err)["status"] == "FAILED_CLOSED"


def test_cli_unknown_exception_is_redacted_without_traceback(
    closure: SyntheticClosure,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = "PRIVATE-UNKNOWN-EXCEPTION-MARKER"

    def fail(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError(marker)

    monkeypatch.setattr(preparer_module, "inspect_ready", fail)
    assert main(
        ["inspect-ready", *_cli_args(closure.paths), "--requested-at", NOW]
    ) == 2
    captured = capsys.readouterr()
    assert marker not in captured.err
    assert "Traceback" not in captured.err
    assert json.loads(captured.err)["status"] == "FAILED_CLOSED"


def test_ast_dependency_surface_is_local_prepare_only() -> None:
    tree = ast.parse(inspect.getsource(preparer_module))
    imported_modules: set[str] = set()
    imported_qualification_names: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.add(node.module or "")
            if node.module == "sdc.real_asset_qualification_v2":
                imported_qualification_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)

    forbidden_import_roots = {
        "http",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    assert not {
        module.split(".", 1)[0] for module in imported_modules
    } & forbidden_import_roots
    forbidden_sdc_fragments = {
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
    }
    assert not any(
        fragment in module.casefold()
        for module in imported_modules
        for fragment in forbidden_sdc_fragments
    )
    assert imported_qualification_names == {
        "CreativeSampleRealAssetQualificationRequestV2",
        "RealAssetQualificationV2Error",
        "build_real_asset_qualification_request_v2",
        "parse_real_asset_qualification_request_v2_json",
    }
    assert not {
        "getenv",
        "popen",
        "run",
        "system",
        "urlopen",
    } & called_names
    assert not any(
        fragment in name.casefold()
        for name in called_names
        for fragment in (
            "qualification_decision",
            "rights_manifest",
            "qualify_real_asset",
        )
    )


def test_request_type_remains_frozen_zero_authority(
    closure: SyntheticClosure,
) -> None:
    request = inspect_ready(closure.paths, requested_at=NOW)
    assert isinstance(request, CreativeSampleRealAssetQualificationRequestV2)
    assert request.model_dump(mode="json") | {
        "rights_manifest_created": False,
        "rights_qualification_performed": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    } == request.model_dump(mode="json")
