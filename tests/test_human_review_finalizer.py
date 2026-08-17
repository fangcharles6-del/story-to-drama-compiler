from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest
from pydantic import ValidationError

from sdc import human_review_finalizer as finalizer_module
from sdc.compiler import stable_id
from sdc.human_review_console import (
    CONTEXT_JSON_NAME,
    CONTEXT_SCRIPT_NAME,
    STATIC_ASSET_NAMES,
    HumanReviewConsoleWorkspace,
    WorkspaceKind,
)
from sdc.human_review_finalizer import (
    CreativeSampleRealAssetHumanPackReviewDraftV2,
    CreativeSampleRealAssetRightsEvidenceDraftV2,
    HumanReviewFinalizerError,
    RealAssetHumanFindingDraftV2,
    check_human_review_pair,
    finalize_human_pack_review,
    finalize_rights_evidence_bundle,
)
from sdc.real_asset_intake import (
    CreativeSampleFrozenRealAssetPackManifest,
    FrozenRealAssetDescriptor,
    FrozenRealAssetPack,
    RealAudioTechnicalRecord,
    RealImageTechnicalRecord,
    _canonical_document,
    _canonical_payload,
    build_real_asset_intake_template,
)
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
    build_real_asset_human_findings_v2,
    build_real_asset_human_pack_review_v2,
    build_real_asset_rights_evidence_bundle_v2,
    finalize_real_asset_review_pair_v2,
    load_real_asset_human_pack_review_v2,
    load_real_asset_review_pair_check_v2,
    load_real_asset_rights_evidence_bundle_v2,
)

REVIEWED_AT_A = "2026-08-17T10:00:00Z"
REVIEWED_AT_B = "2026-08-17T11:00:00Z"
EVALUATED_AT = "2026-08-17T12:00:00Z"


def _digest(label: str) -> str:
    return hashlib.sha256(f"sdc-finalizer-test:{label}".encode()).hexdigest()


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


def _pack(seed: str = "primary") -> CreativeSampleFrozenRealAssetPackManifest:
    template = build_real_asset_intake_template()
    descriptors: list[FrozenRealAssetDescriptor] = []
    for requirement in template.requirements:
        media_sha256 = _digest(f"{seed}:media:{requirement.ordinal}")
        size_bytes = 20_000 + requirement.ordinal
        if requirement.kind == "IMAGE":
            image = RealImageTechnicalRecord(
                width=512,
                height=512,
                color_space="RGB",
                distinct_color_count=256,
            )
            audio: RealAudioTechnicalRecord | None = None
            evidence: RealImageTechnicalRecord | RealAudioTechnicalRecord = image
            duration_ms = 0
        else:
            image = None
            duration_ms = 72_000 if requirement.kind == "BGM" else 250
            audio = RealAudioTechnicalRecord(
                channels=2 if requirement.kind == "BGM" else 1,
                duration_ms=duration_ms,
                sample_count=48_000 * duration_ms // 1000,
                rms_millidbfs=-12_000,
                sample_peak_millidbfs=-1_000,
                silence_ppm=10_000,
            )
            evidence = audio
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
                size_bytes=size_bytes,
                duration_ms=duration_ms,
                source_authority="SEPARATELY_APPROVED_LOCAL_GENERATION",
                provenance_record_sha256=_digest(
                    f"{seed}:provenance:{requirement.ordinal}"
                ),
                technical_profile=requirement.technical_profile,
                technical_record_sha256=_technical_digest(
                    kind=requirement.kind,
                    media_sha256=media_sha256,
                    media_size_bytes=size_bytes,
                    profile=requirement.technical_profile,
                    evidence=evidence,
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
        "submission_id": stable_id("real_asset_submission", {"seed": seed}),
        "pilot_pack_id": template.pilot_pack_id,
        "objects": tuple(item.model_dump(mode="json") for item in objects),
        "total_size_bytes": sum(item.size_bytes for item in objects),
        "state": "FROZEN_UNREVIEWED",
        "current_gate": "HUM_GATE".replace("HUM_", "HUMAN_"),
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleFrozenRealAssetPackManifest.model_validate(
        {"pack_id": stable_id("real_asset_pack", payload), **payload},
        strict=True,
    )


@pytest.fixture
def pack() -> CreativeSampleFrozenRealAssetPackManifest:
    return _pack()


def _install_pack_verifier(
    monkeypatch: pytest.MonkeyPatch,
    *,
    root: Path,
    manifests: tuple[CreativeSampleFrozenRealAssetPackManifest, ...],
    on_verify: Callable[[int], None] | None = None,
) -> list[Path]:
    calls: list[Path] = []

    def verify(path: Path) -> FrozenRealAssetPack:
        absolute = path.absolute()
        calls.append(absolute)
        if on_verify is not None:
            on_verify(len(calls))
        index = min(len(calls) - 1, len(manifests) - 1)
        return FrozenRealAssetPack(
            root=absolute,
            manifest_path=absolute / "asset-pack.json",
            manifest=manifests[index],
            created=False,
        )

    monkeypatch.setattr(finalizer_module, "verify_real_asset_candidate_pack", verify)
    return calls


def _install_workspace_verifier(
    monkeypatch: pytest.MonkeyPatch,
    *,
    root: Path,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    workspace_kind: WorkspaceKind,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2 | None = None,
) -> tuple[str, list[tuple[Path, Path, WorkspaceKind, Path | None]]]:
    root.mkdir()
    for marker in (*STATIC_ASSET_NAMES, CONTEXT_JSON_NAME, CONTEXT_SCRIPT_NAME):
        (root / marker).write_bytes(
            f"test-console:{workspace_kind}:{marker}\n".encode()
        )
    context_sha256 = hashlib.sha256((root / CONTEXT_JSON_NAME).read_bytes()).hexdigest()
    evidence_sha256 = (
        hashlib.sha256(_canonical_document(evidence)).hexdigest()
        if evidence is not None
        else None
    )
    calls: list[tuple[Path, Path, WorkspaceKind, Path | None]] = []

    def verify(
        pack_root: Path,
        workspace_root: Path,
        kind: WorkspaceKind,
        *,
        evidence_path: Path | None = None,
    ) -> HumanReviewConsoleWorkspace:
        calls.append((pack_root, workspace_root, kind, evidence_path))
        return HumanReviewConsoleWorkspace(
            root=root.absolute(),
            context_path=root.absolute() / "review-context.json",
            index_path=root.absolute() / "index.html",
            pack_id=pack.pack_id,
            workspace_kind=workspace_kind,
            review_context_sha256=context_sha256,
            evidence_bundle_id=evidence.bundle_id if evidence is not None else None,
            evidence_bundle_sha256=evidence_sha256,
        )

    monkeypatch.setattr(finalizer_module, "verify_human_review_console_workspace", verify)
    return context_sha256, calls


def _write_record(path: Path, label: str) -> str:
    data = f"private-local-record:{label}\n".encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _candidate_evidence(
    pack: CreativeSampleFrozenRealAssetPackManifest,
    *,
    evidence_record_sha256: str,
) -> CreativeSampleRealAssetRightsEvidenceBundleV2:
    return build_real_asset_rights_evidence_bundle_v2(
        pack=pack,
        evidence_record_sha256=evidence_record_sha256,
        copyright_basis="私密证据覆盖精确冻结字节及本次内部短剧评估。",
        likeness_basis="私密证据确认虚构形象与合成声音的适用范围。",
        privacy_basis="私密证据确认逐项完成隐私和个人信息检查。",
        territory="CN",
        use_scope="短剧内部评估、剪辑与另行审批后的生成参考。",
        valid_until="2027-08-17T12:00:00Z",
    )


def _test_review_context_sha256(workspace_kind: WorkspaceKind) -> str:
    return hashlib.sha256(
        f"test-console:{workspace_kind}:{CONTEXT_JSON_NAME}\n".encode()
    ).hexdigest()


def _evidence_draft(
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    *,
    review_context_sha256: str | None = None,
) -> CreativeSampleRealAssetRightsEvidenceDraftV2:
    return CreativeSampleRealAssetRightsEvidenceDraftV2(
        pack_id=evidence.pack_id,
        pack_manifest_sha256=evidence.pack_manifest_sha256,
        review_context_sha256=review_context_sha256
        or _test_review_context_sha256("EVIDENCE"),
        evidence_record_sha256=evidence.evidence_record_sha256,
        asset_bindings=evidence.asset_bindings,
        copyright_basis=evidence.copyright_basis,
        likeness_basis=evidence.likeness_basis,
        privacy_basis=evidence.privacy_basis,
        territory=evidence.territory,
        use_scope=evidence.use_scope,
        valid_until=evidence.valid_until,
    )


def _review_draft(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    role: Literal["REVIEWER_A", "REVIEWER_B"],
    reviewer_ref_sha256: str,
    review_context_sha256: str | None = None,
) -> CreativeSampleRealAssetHumanPackReviewDraftV2:
    findings = tuple(
        RealAssetHumanFindingDraftV2(
            ordinal=descriptor.ordinal,
            requirement_id=descriptor.requirement_id,
            logical_path=descriptor.logical_path,
            media_sha256=descriptor.sha256,
            media_size_bytes=descriptor.size_bytes,
            inspection_confirmed=True,
            content_role_approved=True,
            failed_gates=(),
            exception_finding=None,
        )
        for descriptor in pack.objects
    )
    return CreativeSampleRealAssetHumanPackReviewDraftV2(
        pack_id=pack.pack_id,
        pack_manifest_sha256=hashlib.sha256(_canonical_document(pack)).hexdigest(),
        review_context_sha256=review_context_sha256
        or _test_review_context_sha256(role),
        evidence_bundle_id=evidence.bundle_id,
        evidence_bundle_sha256=hashlib.sha256(_canonical_document(evidence)).hexdigest(),
        reviewer_role=role,
        reviewer_ref_sha256=reviewer_ref_sha256,
        asset_findings=findings,
        provenance_approved=True,
        copyright_approved=True,
        likeness_approved=True,
        privacy_approved=True,
        territory_approved=True,
        use_scope_approved=True,
        decision="APPROVED",
    )


def _write_canonical(path: Path, document: object) -> None:
    path.write_bytes(_canonical_document(document))  # type: ignore[arg-type]


def test_finalize_evidence_hashes_private_record_rechecks_pack_and_writes_new_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    calls = _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    workspace_root = tmp_path / "evidence-workspace"
    _, workspace_calls = _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="EVIDENCE",
    )
    record_path = tmp_path / "private-evidence-record.txt"
    record_sha256 = _write_record(record_path, "evidence")
    candidate = _candidate_evidence(pack, evidence_record_sha256=record_sha256)
    draft_path = tmp_path / "evidence-draft.json"
    _write_canonical(draft_path, _evidence_draft(candidate))
    output = tmp_path / "rights-evidence-bundle.json"

    finalized = finalize_rights_evidence_bundle(
        pack_root=pack_root,
        workspace_root=workspace_root,
        evidence_draft_path=draft_path,
        evidence_record_path=record_path,
        output_path=output,
    )

    assert finalized == candidate
    assert load_real_asset_rights_evidence_bundle_v2(output) == candidate
    assert output.read_bytes() == _canonical_document(candidate)
    assert len(calls) == 2
    assert len(workspace_calls) == 2
    with pytest.raises(HumanReviewFinalizerError, match="new local file"):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=record_path,
            output_path=output,
        )


def test_finalize_evidence_rejects_record_binding_and_pack_drift_before_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    record_path = tmp_path / "private-evidence-record.txt"
    record_sha256 = _write_record(record_path, "evidence")
    candidate = _candidate_evidence(pack, evidence_record_sha256=record_sha256)
    draft = _evidence_draft(candidate)
    draft_path = tmp_path / "evidence-draft.json"
    _write_canonical(draft_path, draft)
    workspace_root = tmp_path / "evidence-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="EVIDENCE",
    )

    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    record_path.write_bytes(b"changed private record")
    output = tmp_path / "must-not-exist.json"
    with pytest.raises(HumanReviewFinalizerError, match="SHA-256"):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=record_path,
            output_path=output,
        )
    assert not output.exists()

    record_path.unlink()
    _write_record(record_path, "evidence")
    changed_pack = _pack("changed-after-first-verification")
    _install_pack_verifier(
        monkeypatch,
        root=pack_root,
        manifests=(pack, changed_pack),
    )
    with pytest.raises(HumanReviewFinalizerError, match="drifted during"):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=record_path,
            output_path=output,
        )
    assert not output.exists()


def test_finalize_evidence_rechecks_private_record_identity_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    record_path = tmp_path / "private-evidence-record.txt"
    record_sha256 = _write_record(record_path, "evidence")

    def mutate_after_first_record_read(call_number: int) -> None:
        if call_number == 2:
            _rewrite_same_bytes_with_new_identity(record_path)

    _install_pack_verifier(
        monkeypatch,
        root=pack_root,
        manifests=(pack,),
        on_verify=mutate_after_first_record_read,
    )
    workspace_root = tmp_path / "evidence-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="EVIDENCE",
    )
    candidate = _candidate_evidence(pack, evidence_record_sha256=record_sha256)
    draft_path = tmp_path / "evidence-draft.json"
    _write_canonical(draft_path, _evidence_draft(candidate))
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="drifted during"):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=record_path,
            output_path=output,
        )
    assert not output.exists()


def test_finalize_evidence_rejects_copied_workspace_file_as_private_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    workspace_root = tmp_path / "evidence-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="EVIDENCE",
    )
    record_path = tmp_path / "copied-review-context.json"
    record_path.write_bytes((workspace_root / CONTEXT_JSON_NAME).read_bytes())
    candidate = _candidate_evidence(
        pack,
        evidence_record_sha256=hashlib.sha256(record_path.read_bytes()).hexdigest(),
    )
    draft_path = tmp_path / "evidence-draft.json"
    _write_canonical(draft_path, _evidence_draft(candidate))
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="workspace files"):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=record_path,
            output_path=output,
        )
    assert not output.exists()


def test_finalize_review_uses_explicit_time_role_record_and_exact_ui_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    calls = _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    evidence_record = tmp_path / "evidence-record.txt"
    evidence_sha = _write_record(evidence_record, "evidence")
    evidence = _candidate_evidence(pack, evidence_record_sha256=evidence_sha)
    evidence_path = tmp_path / "evidence.json"
    _write_canonical(evidence_path, evidence)
    workspace_root = tmp_path / "reviewer-a-workspace"
    _, workspace_calls = _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="REVIEWER_A",
        evidence=evidence,
    )
    reviewer_record = tmp_path / "reviewer-a-record.txt"
    reviewer_sha = _write_record(reviewer_record, "reviewer-a")
    draft = _review_draft(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewer_ref_sha256=reviewer_sha,
    )
    draft_path = tmp_path / "review-a-draft.json"
    _write_canonical(draft_path, draft)
    output = tmp_path / "review-a.json"

    review = finalize_human_pack_review(
        pack_root=pack_root,
        workspace_root=workspace_root,
        evidence_bundle_path=evidence_path,
        review_draft_path=draft_path,
        reviewer_record_path=reviewer_record,
        expected_role="REVIEWER_A",
        output_path=output,
        reviewed_at=REVIEWED_AT_A,
    )

    assert review.reviewed_at == REVIEWED_AT_A
    assert review.reviewer_role == "REVIEWER_A"
    assert review.reviewer_ref_sha256 == reviewer_sha
    assert all(item.inspection_confirmed for item in review.findings)
    assert all(item.content_role_approved for item in review.findings)
    assert load_real_asset_human_pack_review_v2(output) == review
    assert len(calls) == 2
    assert len(workspace_calls) == 2

    ui_payload = draft.model_dump(mode="json")
    assert ui_payload["document_type"].endswith("-draft")
    assert ui_payload["profile"] == "creative-sample-real-asset-human-review-v2"
    assert ui_payload["pack_manifest_sha256"] == hashlib.sha256(
        _canonical_document(pack)
    ).hexdigest()
    assert ui_payload["review_context_sha256"] == _test_review_context_sha256(
        "REVIEWER_A"
    )
    assert ui_payload["evidence_bundle_sha256"] == hashlib.sha256(
        _canonical_document(evidence)
    ).hexdigest()
    assert all("failed_gates" in finding for finding in ui_payload["asset_findings"])
    missing_failed_gates = draft.model_dump(mode="json")
    del missing_failed_gates["asset_findings"][0]["failed_gates"]
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetHumanPackReviewDraftV2.model_validate(
            missing_failed_gates,
            strict=False,
        )


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("role", "reviewer workspace"),
        ("reviewer-record", "SHA-256"),
        ("pack-manifest", "manifest digest drifted"),
    ],
)
def test_finalize_review_fails_closed_on_role_record_or_manifest_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    mutation: str,
    match: str,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    evidence = _candidate_evidence(
        pack,
        evidence_record_sha256=_digest("evidence-record"),
    )
    evidence_path = tmp_path / "evidence.json"
    _write_canonical(evidence_path, evidence)
    workspace_root = tmp_path / "reviewer-a-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="REVIEWER_A",
        evidence=evidence,
    )
    reviewer_record = tmp_path / "reviewer-record.txt"
    reviewer_sha = _write_record(reviewer_record, "reviewer")
    draft = _review_draft(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewer_ref_sha256=reviewer_sha,
    )
    payload = draft.model_dump(mode="python")
    expected_role: Literal["REVIEWER_A", "REVIEWER_B"] = "REVIEWER_A"
    if mutation == "role":
        expected_role = "REVIEWER_B"
    elif mutation == "reviewer-record":
        reviewer_record.write_bytes(b"different reviewer record")
    else:
        payload["pack_manifest_sha256"] = "0" * 64
        draft = CreativeSampleRealAssetHumanPackReviewDraftV2.model_validate(
            payload, strict=True
        )
    draft_path = tmp_path / "draft.json"
    _write_canonical(draft_path, draft)
    output = tmp_path / "must-not-exist.json"
    with pytest.raises(HumanReviewFinalizerError, match=match):
        finalize_human_pack_review(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_bundle_path=evidence_path,
            review_draft_path=draft_path,
            reviewer_record_path=reviewer_record,
            expected_role=expected_role,
            output_path=output,
            reviewed_at=REVIEWED_AT_A,
        )
    assert not output.exists()


def test_finalize_review_rechecks_private_record_identity_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    evidence = _candidate_evidence(
        pack,
        evidence_record_sha256=_digest("evidence-record"),
    )
    evidence_path = tmp_path / "evidence.json"
    _write_canonical(evidence_path, evidence)
    reviewer_record = tmp_path / "reviewer-a-record.txt"
    reviewer_sha256 = _write_record(reviewer_record, "reviewer-a")

    def mutate_after_first_record_read(call_number: int) -> None:
        if call_number == 2:
            _rewrite_same_bytes_with_new_identity(reviewer_record)

    _install_pack_verifier(
        monkeypatch,
        root=pack_root,
        manifests=(pack,),
        on_verify=mutate_after_first_record_read,
    )
    workspace_root = tmp_path / "reviewer-a-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="REVIEWER_A",
        evidence=evidence,
    )
    draft = _review_draft(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewer_ref_sha256=reviewer_sha256,
    )
    draft_path = tmp_path / "reviewer-a-draft.json"
    _write_canonical(draft_path, draft)
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="drifted during"):
        finalize_human_pack_review(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_bundle_path=evidence_path,
            review_draft_path=draft_path,
            reviewer_record_path=reviewer_record,
            expected_role="REVIEWER_A",
            output_path=output,
            reviewed_at=REVIEWED_AT_A,
        )
    assert not output.exists()


def test_finalize_review_rejects_copied_workspace_file_as_reviewer_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    evidence = _candidate_evidence(
        pack,
        evidence_record_sha256=_digest("evidence-record"),
    )
    evidence_path = tmp_path / "evidence.json"
    _write_canonical(evidence_path, evidence)
    workspace_root = tmp_path / "reviewer-a-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="REVIEWER_A",
        evidence=evidence,
    )
    reviewer_record = tmp_path / "copied-review-context.json"
    reviewer_record.write_bytes((workspace_root / CONTEXT_JSON_NAME).read_bytes())
    reviewer_sha256 = hashlib.sha256(reviewer_record.read_bytes()).hexdigest()
    draft = _review_draft(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewer_ref_sha256=reviewer_sha256,
    )
    draft_path = tmp_path / "reviewer-a-draft.json"
    _write_canonical(draft_path, draft)
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="workspace files"):
        finalize_human_pack_review(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_bundle_path=evidence_path,
            review_draft_path=draft_path,
            reviewer_record_path=reviewer_record,
            expected_role="REVIEWER_A",
            output_path=output,
            reviewed_at=REVIEWED_AT_A,
        )
    assert not output.exists()


@pytest.mark.parametrize("aliased_contract", ("evidence", "draft"))
def test_finalize_review_rejects_reviewer_record_path_aliasing_contract_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    aliased_contract: str,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    evidence = _candidate_evidence(
        pack,
        evidence_record_sha256=_digest("evidence-record"),
    )
    evidence_path = tmp_path / "evidence.json"
    _write_canonical(evidence_path, evidence)
    workspace_root = tmp_path / "reviewer-a-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="REVIEWER_A",
        evidence=evidence,
    )
    reviewer_sha256 = _digest("unrelated-reviewer-reference")
    draft = _review_draft(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewer_ref_sha256=reviewer_sha256,
    )
    draft_path = tmp_path / "reviewer-a-draft.json"
    _write_canonical(draft_path, draft)
    reviewer_record_path = evidence_path if aliased_contract == "evidence" else draft_path
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="must not alias"):
        finalize_human_pack_review(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_bundle_path=evidence_path,
            review_draft_path=draft_path,
            reviewer_record_path=reviewer_record_path,
            expected_role="REVIEWER_A",
            output_path=output,
            reviewed_at=REVIEWED_AT_A,
        )
    assert not output.exists()


def test_finalize_evidence_rejects_private_record_path_aliasing_draft(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    workspace_root = tmp_path / "evidence-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="EVIDENCE",
    )
    candidate = _candidate_evidence(
        pack,
        evidence_record_sha256=_digest("unrelated-evidence-reference"),
    )
    draft_path = tmp_path / "evidence-draft.json"
    _write_canonical(draft_path, _evidence_draft(candidate))
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="must not alias"):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=draft_path,
            output_path=output,
        )
    assert not output.exists()


def _approved_review(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    role: Literal["REVIEWER_A", "REVIEWER_B"],
    reviewed_at: str,
    reviewer_ref_sha256: str | None = None,
) -> CreativeSampleRealAssetHumanPackReviewV2:
    return build_real_asset_human_pack_review_v2(
        pack=pack,
        evidence=evidence,
        reviewer_role=role,
        reviewer_ref_sha256=reviewer_ref_sha256 or _digest(f"reviewer:{role}"),
        reviewed_at=reviewed_at,
        findings=build_real_asset_human_findings_v2(
            pack=pack,
            confirmed_ordinals=tuple(range(14)),
            content_role_approvals=(True,) * 14,
        ),
        provenance_approved=True,
        copyright_approved=True,
        likeness_approved=True,
        privacy_approved=True,
        territory_approved=True,
        use_scope_approved=True,
        decision="APPROVED",
    )


@dataclass(frozen=True)
class _PairMaterial:
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2
    evidence_path: Path
    reviewer_a_path: Path
    reviewer_b_path: Path
    evidence_record_path: Path
    reviewer_a_record_path: Path
    reviewer_b_record_path: Path


def _pair_material(
    tmp_path: Path,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> _PairMaterial:
    evidence_record_path = tmp_path / "private-evidence-record.txt"
    reviewer_a_record_path = tmp_path / "private-reviewer-a-record.txt"
    reviewer_b_record_path = tmp_path / "private-reviewer-b-record.txt"
    evidence_record_sha256 = _write_record(evidence_record_path, "evidence")
    reviewer_a_ref = _write_record(reviewer_a_record_path, "reviewer-a")
    reviewer_b_ref = _write_record(reviewer_b_record_path, "reviewer-b")
    evidence = _candidate_evidence(
        pack,
        evidence_record_sha256=evidence_record_sha256,
    )
    reviewer_a = _approved_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at=REVIEWED_AT_A,
        reviewer_ref_sha256=reviewer_a_ref,
    )
    reviewer_b = _approved_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at=REVIEWED_AT_B,
        reviewer_ref_sha256=reviewer_b_ref,
    )
    evidence_path = tmp_path / "evidence.json"
    reviewer_a_path = tmp_path / "reviewer-a.json"
    reviewer_b_path = tmp_path / "reviewer-b.json"
    _write_canonical(evidence_path, evidence)
    _write_canonical(reviewer_a_path, reviewer_a)
    _write_canonical(reviewer_b_path, reviewer_b)
    return _PairMaterial(
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        evidence_path=evidence_path,
        reviewer_a_path=reviewer_a_path,
        reviewer_b_path=reviewer_b_path,
        evidence_record_path=evidence_record_path,
        reviewer_a_record_path=reviewer_a_record_path,
        reviewer_b_record_path=reviewer_b_record_path,
    )


def _rewrite_same_bytes_with_new_identity(path: Path) -> None:
    before = path.stat()
    data = path.read_bytes()
    path.write_bytes(data)
    os.utime(
        path,
        ns=(before.st_atime_ns, before.st_mtime_ns + 2_000_000_000),
    )


def test_check_pair_rechecks_pack_and_writes_only_zero_authority_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    calls = _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    evidence_record_path = tmp_path / "private-evidence-record.txt"
    reviewer_a_record_path = tmp_path / "private-reviewer-a-record.txt"
    reviewer_b_record_path = tmp_path / "private-reviewer-b-record.txt"
    evidence_record_sha256 = _write_record(evidence_record_path, "evidence")
    reviewer_a_ref = _write_record(reviewer_a_record_path, "reviewer-a")
    reviewer_b_ref = _write_record(reviewer_b_record_path, "reviewer-b")
    evidence = _candidate_evidence(
        pack,
        evidence_record_sha256=evidence_record_sha256,
    )
    reviewer_a = _approved_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at=REVIEWED_AT_A,
        reviewer_ref_sha256=reviewer_a_ref,
    )
    reviewer_b = _approved_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at=REVIEWED_AT_B,
        reviewer_ref_sha256=reviewer_b_ref,
    )
    evidence_path = tmp_path / "evidence.json"
    reviewer_a_path = tmp_path / "reviewer-a.json"
    reviewer_b_path = tmp_path / "reviewer-b.json"
    _write_canonical(evidence_path, evidence)
    _write_canonical(reviewer_a_path, reviewer_a)
    _write_canonical(reviewer_b_path, reviewer_b)
    output = tmp_path / "pair-check.json"

    check = check_human_review_pair(
        pack_root=pack_root,
        evidence_bundle_path=evidence_path,
        evidence_record_path=evidence_record_path,
        reviewer_a_path=reviewer_a_path,
        reviewer_a_record_path=reviewer_a_record_path,
        reviewer_b_path=reviewer_b_path,
        reviewer_b_record_path=reviewer_b_record_path,
        output_path=output,
        evaluated_at=EVALUATED_AT,
    )

    assert check.status == "READY_FOR_SEPARATE_QUALIFICATION_REVIEW"
    assert check.rights_manifest_created is False
    assert check.rights_qualification_performed is False
    assert check.current_gate == "HUMAN_GATE"
    assert check.provider_state == "NOT_AUTHORIZED"
    assert check.execution_authorized is False
    assert check.posts_allowed == check.provider_requests == 0
    assert load_real_asset_review_pair_check_v2(output) == check
    assert len(calls) == 2


@pytest.mark.parametrize(
    "record_name",
    ("evidence_record_path", "reviewer_a_record_path", "reviewer_b_record_path"),
)
def test_check_pair_rechecks_all_private_record_identities_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    record_name: str,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    material = _pair_material(tmp_path, pack)
    record_path = getattr(material, record_name)

    def mutate_after_first_record_reads(call_number: int) -> None:
        if call_number == 2:
            _rewrite_same_bytes_with_new_identity(record_path)

    _install_pack_verifier(
        monkeypatch,
        root=pack_root,
        manifests=(pack,),
        on_verify=mutate_after_first_record_reads,
    )
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="drifted during"):
        check_human_review_pair(
            pack_root=pack_root,
            evidence_bundle_path=material.evidence_path,
            evidence_record_path=material.evidence_record_path,
            reviewer_a_path=material.reviewer_a_path,
            reviewer_a_record_path=material.reviewer_a_record_path,
            reviewer_b_path=material.reviewer_b_path,
            reviewer_b_record_path=material.reviewer_b_record_path,
            output_path=output,
            evaluated_at=EVALUATED_AT,
        )
    assert not output.exists()


@pytest.mark.parametrize("contract_name", ("evidence", "reviewer_a", "reviewer_b"))
def test_check_pair_reloads_all_canonical_contracts_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    contract_name: str,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    material = _pair_material(tmp_path, pack)

    def mutate_contract_after_first_reads(call_number: int) -> None:
        if call_number != 2:
            return
        if contract_name == "evidence":
            replacement = _candidate_evidence(
                pack,
                evidence_record_sha256=_digest("replacement-evidence-record"),
            )
            _write_canonical(material.evidence_path, replacement)
        elif contract_name == "reviewer_a":
            _write_canonical(material.reviewer_a_path, material.reviewer_b)
        else:
            _write_canonical(material.reviewer_b_path, material.reviewer_a)

    _install_pack_verifier(
        monkeypatch,
        root=pack_root,
        manifests=(pack,),
        on_verify=mutate_contract_after_first_reads,
    )
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="contracts drifted"):
        check_human_review_pair(
            pack_root=pack_root,
            evidence_bundle_path=material.evidence_path,
            evidence_record_path=material.evidence_record_path,
            reviewer_a_path=material.reviewer_a_path,
            reviewer_a_record_path=material.reviewer_a_record_path,
            reviewer_b_path=material.reviewer_b_path,
            reviewer_b_record_path=material.reviewer_b_record_path,
            output_path=output,
            evaluated_at=EVALUATED_AT,
        )
    assert not output.exists()


@pytest.mark.parametrize(
    ("record_name", "contract_name"),
    tuple(
        (record_name, contract_name)
        for record_name in ("evidence", "reviewer_a", "reviewer_b")
        for contract_name in ("evidence", "reviewer_a", "reviewer_b")
    ),
)
def test_check_pair_private_record_paths_cannot_alias_any_contract_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    record_name: str,
    contract_name: str,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    material = _pair_material(tmp_path, pack)
    record_paths = {
        "evidence": material.evidence_record_path,
        "reviewer_a": material.reviewer_a_record_path,
        "reviewer_b": material.reviewer_b_record_path,
    }
    contract_paths = {
        "evidence": material.evidence_path,
        "reviewer_a": material.reviewer_a_path,
        "reviewer_b": material.reviewer_b_path,
    }
    record_paths[record_name] = contract_paths[contract_name]
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="must not alias Pack"):
        check_human_review_pair(
            pack_root=pack_root,
            evidence_bundle_path=material.evidence_path,
            evidence_record_path=record_paths["evidence"],
            reviewer_a_path=material.reviewer_a_path,
            reviewer_a_record_path=record_paths["reviewer_a"],
            reviewer_b_path=material.reviewer_b_path,
            reviewer_b_record_path=record_paths["reviewer_b"],
            output_path=output,
            evaluated_at=EVALUATED_AT,
        )
    assert not output.exists()


def test_check_pair_rejects_copied_review_contract_as_cross_role_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    evidence_record_path = tmp_path / "private-evidence-record.txt"
    reviewer_a_record_path = tmp_path / "private-reviewer-a-record.txt"
    reviewer_b_record_path = tmp_path / "copied-reviewer-a-contract.json"
    evidence_record_sha256 = _write_record(evidence_record_path, "evidence")
    reviewer_a_ref = _write_record(reviewer_a_record_path, "reviewer-a")
    evidence = _candidate_evidence(
        pack,
        evidence_record_sha256=evidence_record_sha256,
    )
    reviewer_a = _approved_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at=REVIEWED_AT_A,
        reviewer_ref_sha256=reviewer_a_ref,
    )
    reviewer_b_record_path.write_bytes(_canonical_document(reviewer_a))
    reviewer_b = _approved_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at=REVIEWED_AT_B,
        reviewer_ref_sha256=hashlib.sha256(
            reviewer_b_record_path.read_bytes()
        ).hexdigest(),
    )
    evidence_path = tmp_path / "evidence.json"
    reviewer_a_path = tmp_path / "reviewer-a.json"
    reviewer_b_path = tmp_path / "reviewer-b.json"
    _write_canonical(evidence_path, evidence)
    _write_canonical(reviewer_a_path, reviewer_a)
    _write_canonical(reviewer_b_path, reviewer_b)
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="digests must not alias"):
        check_human_review_pair(
            pack_root=pack_root,
            evidence_bundle_path=evidence_path,
            evidence_record_path=evidence_record_path,
            reviewer_a_path=reviewer_a_path,
            reviewer_a_record_path=reviewer_a_record_path,
            reviewer_b_path=reviewer_b_path,
            reviewer_b_record_path=reviewer_b_record_path,
            output_path=output,
            evaluated_at=EVALUATED_AT,
        )
    assert not output.exists()


@pytest.mark.parametrize("workspace_kind", ("EVIDENCE", "REVIEWER_A", "REVIEWER_B"))
def test_check_pair_output_cannot_modify_any_console_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    workspace_kind: WorkspaceKind,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    workspace_root = tmp_path / workspace_kind.lower()
    workspace_root.mkdir()
    for marker in (*STATIC_ASSET_NAMES, CONTEXT_JSON_NAME, CONTEXT_SCRIPT_NAME):
        (workspace_root / marker).write_bytes(b"console-marker\n")
    output = workspace_root / "pair-check.json"

    with pytest.raises(HumanReviewFinalizerError, match="any human-review console"):
        check_human_review_pair(
            pack_root=pack_root,
            evidence_bundle_path=tmp_path / "unused-evidence.json",
            evidence_record_path=tmp_path / "unused-evidence-record.txt",
            reviewer_a_path=tmp_path / "unused-reviewer-a.json",
            reviewer_a_record_path=tmp_path / "unused-reviewer-a-record.txt",
            reviewer_b_path=tmp_path / "unused-reviewer-b.json",
            reviewer_b_record_path=tmp_path / "unused-reviewer-b-record.txt",
            output_path=output,
            evaluated_at=EVALUATED_AT,
        )
    assert not output.exists()


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("missing", "safe local path"),
        ("drift", "SHA-256"),
        ("reuse", "must be distinct"),
        ("console", "outside every human-review console"),
    ],
)
def test_check_pair_rejects_missing_drifted_reused_or_console_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    mutation: str,
    match: str,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    evidence_record_path = tmp_path / "private-evidence-record.txt"
    reviewer_a_record_path = tmp_path / "private-reviewer-a-record.txt"
    reviewer_b_record_path = tmp_path / "private-reviewer-b-record.txt"
    evidence_record_sha256 = _write_record(evidence_record_path, "evidence")
    reviewer_a_ref = _write_record(reviewer_a_record_path, "reviewer-a")
    reviewer_b_ref = _write_record(reviewer_b_record_path, "reviewer-b")
    evidence = _candidate_evidence(
        pack,
        evidence_record_sha256=evidence_record_sha256,
    )
    reviewer_a = _approved_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at=REVIEWED_AT_A,
        reviewer_ref_sha256=reviewer_a_ref,
    )
    reviewer_b = _approved_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at=REVIEWED_AT_B,
        reviewer_ref_sha256=reviewer_b_ref,
    )
    evidence_path = tmp_path / "evidence.json"
    reviewer_a_path = tmp_path / "reviewer-a.json"
    reviewer_b_path = tmp_path / "reviewer-b.json"
    _write_canonical(evidence_path, evidence)
    _write_canonical(reviewer_a_path, reviewer_a)
    _write_canonical(reviewer_b_path, reviewer_b)
    if mutation == "missing":
        reviewer_b_record_path.unlink()
    elif mutation == "drift":
        reviewer_a_record_path.write_bytes(b"drifted reviewer record\n")
    elif mutation == "reuse":
        reviewer_b_record_path = reviewer_a_record_path
    else:
        workspace_root = tmp_path / "unrelated-console-workspace"
        workspace_root.mkdir()
        for marker in (*STATIC_ASSET_NAMES, CONTEXT_JSON_NAME, CONTEXT_SCRIPT_NAME):
            (workspace_root / marker).write_bytes(b"console-marker\n")
        reviewer_b_record_path = workspace_root / "private-reviewer-b-record.txt"
        _write_record(reviewer_b_record_path, "reviewer-b")
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match=match):
        check_human_review_pair(
            pack_root=pack_root,
            evidence_bundle_path=evidence_path,
            evidence_record_path=evidence_record_path,
            reviewer_a_path=reviewer_a_path,
            reviewer_a_record_path=reviewer_a_record_path,
            reviewer_b_path=reviewer_b_path,
            reviewer_b_record_path=reviewer_b_record_path,
            output_path=output,
            evaluated_at=EVALUATED_AT,
        )
    assert not output.exists()


def test_cli_prints_safe_compact_summaries_for_all_three_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    evidence = _candidate_evidence(
        pack,
        evidence_record_sha256=_digest("private-evidence-record"),
    )
    review_a = _approved_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewed_at=REVIEWED_AT_A,
    )
    review_b = _approved_review(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_B",
        reviewed_at=REVIEWED_AT_B,
    )
    pair = finalize_real_asset_review_pair_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=review_a,
        reviewer_b=review_b,
        evaluated_at=EVALUATED_AT,
    )
    monkeypatch.setattr(
        finalizer_module,
        "finalize_rights_evidence_bundle",
        lambda **_: evidence,
    )
    monkeypatch.setattr(
        finalizer_module,
        "finalize_human_pack_review",
        lambda **_: review_a,
    )
    monkeypatch.setattr(finalizer_module, "check_human_review_pair", lambda **_: pair)
    monkeypatch.setattr(finalizer_module, "_current_utc_seconds", lambda: EVALUATED_AT)

    commands = (
        (
            [
                "finalize-evidence",
                "--pack-root",
                str(tmp_path / "pack"),
                "--workspace",
                str(tmp_path / "evidence-workspace"),
                "--draft",
                str(tmp_path / "draft"),
                "--evidence-record",
                str(tmp_path / "record"),
                "--output",
                str(tmp_path / "evidence.json"),
            ],
            evidence.bundle_id,
        ),
        (
            [
                "finalize-review",
                "--pack-root",
                str(tmp_path / "pack"),
                "--workspace",
                str(tmp_path / "reviewer-a-workspace"),
                "--evidence",
                str(tmp_path / "evidence"),
                "--draft",
                str(tmp_path / "draft"),
                "--reviewer-record",
                str(tmp_path / "record"),
                "--expected-role",
                "REVIEWER_A",
                "--output",
                str(tmp_path / "review.json"),
            ],
            review_a.review_id,
        ),
        (
            [
                "check-pair",
                "--pack-root",
                str(tmp_path / "pack"),
                "--evidence",
                str(tmp_path / "evidence"),
                "--evidence-record",
                str(tmp_path / "evidence-record"),
                "--reviewer-a",
                str(tmp_path / "review-a"),
                "--reviewer-a-record",
                str(tmp_path / "reviewer-a-record"),
                "--reviewer-b",
                str(tmp_path / "review-b"),
                "--reviewer-b-record",
                str(tmp_path / "reviewer-b-record"),
                "--output",
                str(tmp_path / "pair.json"),
            ],
            pair.pair_check_id,
        ),
    )
    for argv, document_id in commands:
        assert finalizer_module._main(argv) == 0
        line = capsys.readouterr().out
        assert line.endswith("\n") and "\n" not in line[:-1]
        summary = json.loads(line)
        assert summary["document_id"] == document_id
        assert summary["pack_id"] == pack.pack_id
        assert summary["current_gate"] == "HUMAN_GATE"
        assert summary["provider_state"] == "NOT_AUTHORIZED"
        assert summary["execution_authorized"] is False
        assert summary["posts_allowed"] == summary["provider_requests"] == 0
        assert evidence.copyright_basis not in line
        assert evidence.evidence_record_sha256 not in line


@pytest.mark.parametrize(
    "record_location,match",
    [
        ("pack", "outside the frozen asset pack"),
        ("workspace", "outside every human-review console workspace"),
    ],
)
def test_private_evidence_record_cannot_be_inside_pack_or_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    record_location: str,
    match: str,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    workspace_root = tmp_path / "evidence-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="EVIDENCE",
    )
    record_parent = pack_root if record_location == "pack" else workspace_root
    record_path = record_parent / "private-evidence-record.txt"
    record_sha256 = _write_record(record_path, record_location)
    candidate = _candidate_evidence(pack, evidence_record_sha256=record_sha256)
    draft_path = tmp_path / "evidence-draft.json"
    _write_canonical(draft_path, _evidence_draft(candidate))
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match=match):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=record_path,
            output_path=output,
        )
    assert not output.exists()


def test_finalized_output_cannot_modify_verified_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    workspace_root = tmp_path / "evidence-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="EVIDENCE",
    )
    record_path = tmp_path / "private-evidence-record.txt"
    record_sha256 = _write_record(record_path, "evidence")
    candidate = _candidate_evidence(pack, evidence_record_sha256=record_sha256)
    draft_path = tmp_path / "evidence-draft.json"
    _write_canonical(draft_path, _evidence_draft(candidate))
    output = workspace_root / "finalized-evidence.json"

    with pytest.raises(HumanReviewFinalizerError, match="human-review console workspace"):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=record_path,
            output_path=output,
        )
    assert not output.exists()


def test_evidence_finalizer_rejects_review_context_digest_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    workspace_root = tmp_path / "evidence-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="EVIDENCE",
    )
    record_path = tmp_path / "private-evidence-record.txt"
    record_sha256 = _write_record(record_path, "evidence")
    candidate = _candidate_evidence(pack, evidence_record_sha256=record_sha256)
    draft = _evidence_draft(candidate).model_dump(mode="python")
    draft["review_context_sha256"] = "0" * 64
    draft_path = tmp_path / "evidence-draft.json"
    _write_canonical(
        draft_path,
        CreativeSampleRealAssetRightsEvidenceDraftV2.model_validate(draft, strict=True),
    )
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="review context digest drifted"):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=record_path,
            output_path=output,
        )
    assert not output.exists()


def test_review_finalizer_rejects_evidence_bundle_digest_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    evidence = _candidate_evidence(
        pack,
        evidence_record_sha256=_digest("evidence-record"),
    )
    evidence_path = tmp_path / "evidence.json"
    _write_canonical(evidence_path, evidence)
    workspace_root = tmp_path / "reviewer-a-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="REVIEWER_A",
        evidence=evidence,
    )
    reviewer_record = tmp_path / "reviewer-a-record.txt"
    reviewer_sha256 = _write_record(reviewer_record, "reviewer-a")
    draft = _review_draft(
        pack=pack,
        evidence=evidence,
        role="REVIEWER_A",
        reviewer_ref_sha256=reviewer_sha256,
    ).model_dump(mode="python")
    draft["evidence_bundle_sha256"] = "0" * 64
    draft_path = tmp_path / "reviewer-a-draft.json"
    _write_canonical(
        draft_path,
        CreativeSampleRealAssetHumanPackReviewDraftV2.model_validate(
            draft, strict=True
        ),
    )
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(HumanReviewFinalizerError, match="evidence bundle digest drifted"):
        finalize_human_pack_review(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_bundle_path=evidence_path,
            review_draft_path=draft_path,
            reviewer_record_path=reviewer_record,
            expected_role="REVIEWER_A",
            output_path=output,
            reviewed_at=REVIEWED_AT_A,
        )
    assert not output.exists()


def test_private_record_and_output_must_remain_outside_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> None:
    pack_root = tmp_path / "frozen-pack"
    pack_root.mkdir()
    _install_pack_verifier(monkeypatch, root=pack_root, manifests=(pack,))
    workspace_root = tmp_path / "evidence-workspace"
    _install_workspace_verifier(
        monkeypatch,
        root=workspace_root,
        pack=pack,
        workspace_kind="EVIDENCE",
    )
    repository_root = Path(__file__).resolve().parents[1]
    repository_record = repository_root / "pyproject.toml"
    candidate = _candidate_evidence(
        pack,
        evidence_record_sha256=hashlib.sha256(repository_record.read_bytes()).hexdigest(),
    )
    draft_path = tmp_path / "draft.json"
    _write_canonical(draft_path, _evidence_draft(candidate))
    output = tmp_path / "out.json"
    with pytest.raises(HumanReviewFinalizerError, match="outside every Git"):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=repository_record,
            output_path=output,
        )
    assert not output.exists()

    private_record = tmp_path / "record.txt"
    _write_record(private_record, "outside-git")
    repository_output = repository_root / "must-never-create-finalized-review.json"
    with pytest.raises(HumanReviewFinalizerError, match="outside every Git"):
        finalize_rights_evidence_bundle(
            pack_root=pack_root,
            workspace_root=workspace_root,
            evidence_draft_path=draft_path,
            evidence_record_path=private_record,
            output_path=repository_output,
        )
    assert not repository_output.exists()


def test_finalizer_has_no_env_network_service_manifest_or_qualification_path() -> None:
    source = inspect.getsource(finalizer_module)
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert "qualify_real_asset_candidate_pack" not in source
    assert "build_real_asset_rights_manifest" not in source
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
