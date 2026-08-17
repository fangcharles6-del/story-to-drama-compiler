"""Trusted, offline finalization of draft-only Creative Sample human reviews.

The static console emits untrusted drafts.  This module independently re-verifies the frozen
pack, hashes explicitly supplied private records, rebuilds strict Review v2 contracts, and writes
only new local files outside Git.  It cannot create a rights manifest or perform qualification.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sdc.creative_media import CreativeMediaError, validate_local_path
from sdc.human_review_console import (
    CONTEXT_JSON_NAME,
    CONTEXT_SCRIPT_NAME,
    STATIC_ASSET_NAMES,
    HumanReviewConsoleError,
    HumanReviewConsoleWorkspace,
    WorkspaceKind,
    verify_human_review_console_workspace,
)
from sdc.real_asset_intake import (
    CreativeSampleFrozenRealAssetPackManifest,
    FrozenRealAssetDescriptor,
    FrozenRealAssetPack,
    RealAssetIntakeError,
    _canonical_document,
    _logical_path,
    _portable_text,
    _read_strict_json,
    _sha256,
    _utc_seconds,
    verify_real_asset_candidate_pack,
)
from sdc.real_asset_media import RealAssetMediaError, SafeLocalFile, read_safe_local_file
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
    RealAssetReviewExceptionV2,
    RealAssetReviewV2Error,
    RealAssetRightsEvidenceBindingV2,
    RightsGateV2,
    build_real_asset_human_findings_v2,
    build_real_asset_human_pack_review_v2,
    build_real_asset_rights_evidence_bundle_v2,
    finalize_real_asset_review_pair_v2,
    load_real_asset_human_pack_review_v2,
    load_real_asset_rights_evidence_bundle_v2,
    write_new_real_asset_review_v2_document,
)

DRAFT_PROFILE: Literal["creative-sample-real-asset-human-review-v2"] = (
    "creative-sample-real-asset-human-review-v2"
)
MAX_PRIVATE_RECORD_BYTES = 64 * 1024 * 1024
_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_GATE_ORDER: tuple[RightsGateV2, ...] = (
    "PROVENANCE",
    "COPYRIGHT",
    "LIKENESS",
    "PRIVACY",
    "TERRITORY",
    "USE_SCOPE",
    "CONTENT_ROLE",
)
_GATE_TO_FIELD: dict[RightsGateV2, str] = {
    "PROVENANCE": "provenance_approved",
    "COPYRIGHT": "copyright_approved",
    "LIKENESS": "likeness_approved",
    "PRIVACY": "privacy_approved",
    "TERRITORY": "territory_approved",
    "USE_SCOPE": "use_scope_approved",
}
_CONSOLE_WORKSPACE_MARKERS = frozenset(
    (*STATIC_ASSET_NAMES, CONTEXT_JSON_NAME, CONTEXT_SCRIPT_NAME)
)


class HumanReviewFinalizerError(RuntimeError):
    """A trusted local finalization step failed closed."""


class _DraftModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class CreativeSampleRealAssetRightsEvidenceDraftV2(_DraftModel):
    """Complete console draft accepted by ``finalize-evidence``."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-rights-evidence-bundle-v2-draft"
    ] = "sdc.creative-sample-real-asset-rights-evidence-bundle-v2-draft"
    profile: Literal["creative-sample-real-asset-human-review-v2"] = DRAFT_PROFILE
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    pack_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    review_context_sha256: str = Field(pattern=_LOWER_SHA256)
    evidence_record_sha256: str = Field(pattern=_LOWER_SHA256)
    asset_bindings: tuple[RealAssetRightsEvidenceBindingV2, ...] = Field(
        min_length=14, max_length=14
    )
    copyright_basis: str = Field(min_length=1, max_length=1000)
    likeness_basis: str = Field(min_length=1, max_length=1000)
    privacy_basis: str = Field(min_length=1, max_length=1000)
    territory: str = Field(min_length=1, max_length=256)
    use_scope: str = Field(min_length=1, max_length=1000)
    valid_until: str
    status: Literal["DRAFT"] = "DRAFT"
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @field_validator(
        "copyright_basis", "likeness_basis", "privacy_basis", "use_scope"
    )
    @classmethod
    def validate_basis_text(cls, value: str) -> str:
        return _portable_text(value, field="evidence draft rights basis")

    @field_validator("territory")
    @classmethod
    def validate_territory(cls, value: str) -> str:
        return _portable_text(value, field="evidence draft territory", maximum=256)

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, value: str) -> str:
        if value == "PERPETUAL":
            return value
        return _utc_seconds(value, field="valid_until")

    @model_validator(mode="after")
    def validate_bindings(self) -> CreativeSampleRealAssetRightsEvidenceDraftV2:
        if tuple(item.ordinal for item in self.asset_bindings) != tuple(range(14)):
            raise ValueError("evidence draft bindings must use exact canonical ordinals")
        if len({item.requirement_id for item in self.asset_bindings}) != 14:
            raise ValueError("evidence draft requirements must be unique")
        if len({item.media_sha256 for item in self.asset_bindings}) != 14:
            raise ValueError("evidence draft media identities must be unique")
        return self


class RealAssetHumanFindingDraftV2(_DraftModel):
    """One complete console finding with an optional explicit exception."""

    ordinal: Annotated[int, Field(ge=0, le=13)]
    requirement_id: str = Field(pattern=r"^real_asset_requirement_[0-9a-f]{20}$")
    logical_path: str
    media_sha256: str = Field(pattern=_LOWER_SHA256)
    media_size_bytes: Annotated[int, Field(gt=0)]
    inspection_confirmed: Literal[True]
    content_role_approved: bool
    failed_gates: tuple[RightsGateV2, ...]
    exception_finding: str | None = Field(default=None, min_length=1, max_length=1000)

    @field_validator("logical_path")
    @classmethod
    def validate_logical_path(cls, value: str) -> str:
        return _logical_path(value)

    @field_validator("failed_gates")
    @classmethod
    def validate_failed_gates(
        cls, value: tuple[RightsGateV2, ...]
    ) -> tuple[RightsGateV2, ...]:
        if len(value) != len(set(value)):
            raise ValueError("draft exception gates must be unique")
        if value != tuple(gate for gate in _GATE_ORDER if gate in value):
            raise ValueError("draft exception gates must use canonical order")
        return value

    @field_validator("exception_finding")
    @classmethod
    def validate_exception_finding(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _portable_text(value, field="draft asset exception")

    @model_validator(mode="after")
    def validate_exception(self) -> RealAssetHumanFindingDraftV2:
        if (self.exception_finding is None) != (not self.failed_gates):
            raise ValueError("draft exception finding and failed gates must be present together")
        if self.content_role_approved:
            if "CONTENT_ROLE" in self.failed_gates:
                raise ValueError("approved content role cannot declare a content-role exception")
        elif self.exception_finding is None or "CONTENT_ROLE" not in self.failed_gates:
            raise ValueError("failed content role requires an explicit content-role exception")
        return self


class CreativeSampleRealAssetHumanPackReviewDraftV2(_DraftModel):
    """Complete one-reviewer console draft accepted by ``finalize-review``."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-human-pack-review-v2-draft"
    ] = "sdc.creative-sample-real-asset-human-pack-review-v2-draft"
    profile: Literal["creative-sample-real-asset-human-review-v2"] = DRAFT_PROFILE
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    pack_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    review_context_sha256: str = Field(pattern=_LOWER_SHA256)
    evidence_bundle_id: str = Field(
        pattern=r"^real_asset_rights_evidence_v2_[0-9a-f]{20}$"
    )
    evidence_bundle_sha256: str = Field(pattern=_LOWER_SHA256)
    reviewer_role: Literal["REVIEWER_A", "REVIEWER_B"]
    reviewer_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    asset_findings: tuple[RealAssetHumanFindingDraftV2, ...] = Field(
        min_length=14, max_length=14
    )
    provenance_approved: bool
    copyright_approved: bool
    likeness_approved: bool
    privacy_approved: bool
    territory_approved: bool
    use_scope_approved: bool
    rejection_reason: str | None = Field(default=None, min_length=1, max_length=1000)
    decision: Literal["APPROVED", "REJECTED"]
    status: Literal["DRAFT"] = "DRAFT"
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _portable_text(value, field="review draft rejection reason")

    @model_validator(mode="after")
    def validate_review(self) -> CreativeSampleRealAssetHumanPackReviewDraftV2:
        if tuple(item.ordinal for item in self.asset_findings) != tuple(range(14)):
            raise ValueError("review draft findings must use exact canonical ordinals")
        if len({item.requirement_id for item in self.asset_findings}) != 14:
            raise ValueError("review draft requirements must be unique")
        if len({item.media_sha256 for item in self.asset_findings}) != 14:
            raise ValueError("review draft media identities must be unique")
        pack_outcomes = _draft_pack_outcomes(self)
        content_outcomes = tuple(item.content_role_approved for item in self.asset_findings)
        has_exception = any(item.exception_finding is not None for item in self.asset_findings)
        for finding in self.asset_findings:
            for gate in finding.failed_gates:
                if gate != "CONTENT_ROLE" and bool(getattr(self, _GATE_TO_FIELD[gate])):
                    raise ValueError("an asset exception gate must also fail at Pack level")
        if self.decision == "APPROVED":
            if not all((*pack_outcomes, *content_outcomes)):
                raise ValueError("approved review draft requires every human gate to pass")
            if has_exception:
                raise ValueError("approved review draft cannot retain an asset exception")
            if self.rejection_reason is not None:
                raise ValueError("approved review draft cannot contain a rejection reason")
        else:
            if all((*pack_outcomes, *content_outcomes)):
                raise ValueError("rejected review draft must identify a failed human gate")
            if self.rejection_reason is None:
                raise ValueError("rejected review draft requires a human-authored reason")
        return self


def _draft_pack_outcomes(
    draft: CreativeSampleRealAssetHumanPackReviewDraftV2,
) -> tuple[bool, ...]:
    return (
        draft.provenance_approved,
        draft.copyright_approved,
        draft.likeness_approved,
        draft.privacy_approved,
        draft.territory_approved,
        draft.use_scope_approved,
    )


def _nearest_git_root(path: Path) -> Path | None:
    cursor = path if os.path.lexists(path) and path.is_dir() else path.parent
    while True:
        if os.path.lexists(cursor / ".git"):
            return cursor
        parent = cursor.parent
        if parent == cursor:
            return None
        cursor = parent


def _safe_path_outside_git(path: Path, *, must_exist: bool, field: str) -> Path:
    try:
        absolute = validate_local_path(path, must_exist=must_exist)
        if not must_exist:
            validate_local_path(absolute.parent, must_exist=True)
    except CreativeMediaError as exc:
        raise HumanReviewFinalizerError(f"{field} is not a safe local path") from exc
    if _nearest_git_root(absolute) is not None:
        raise HumanReviewFinalizerError(f"{field} must remain outside every Git worktree")
    return absolute


def _containing_console_workspace(path: Path) -> Path | None:
    cursor = path.parent
    while True:
        contains_all_markers = True
        for marker in _CONSOLE_WORKSPACE_MARKERS:
            try:
                (cursor / marker).lstat()
            except FileNotFoundError:
                contains_all_markers = False
                break
            except OSError as exc:
                raise HumanReviewFinalizerError(
                    "finalized output parent chain could not be checked safely"
                ) from exc
        if contains_all_markers:
            return cursor
        parent = cursor.parent
        if parent == cursor:
            return None
        cursor = parent


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _prepare_output(
    path: Path,
    *,
    pack_root: Path,
    workspace_root: Path | None = None,
) -> Path:
    target = _safe_path_outside_git(path, must_exist=False, field="finalized output")
    if os.path.lexists(target):
        raise HumanReviewFinalizerError("finalized output must be one new local file")
    if target == pack_root or target.is_relative_to(pack_root):
        raise HumanReviewFinalizerError("finalized output must not modify the frozen asset pack")
    if _containing_console_workspace(target) is not None:
        raise HumanReviewFinalizerError(
            "finalized output must not modify any human-review console workspace"
        )
    if workspace_root is not None and (
        target == workspace_root or target.is_relative_to(workspace_root)
    ):
        raise HumanReviewFinalizerError(
            "finalized output must not modify the verified review workspace"
        )
    return target


def _load_draft(path: Path, model: type[_DraftModel]) -> _DraftModel:
    absolute = _safe_path_outside_git(path, must_exist=True, field="review draft")
    try:
        return cast(_DraftModel, _read_strict_json(absolute, model))
    except RealAssetIntakeError as exc:
        raise HumanReviewFinalizerError("review draft is not strict canonical JSON") from exc


def _validated_private_record_path(
    path: Path,
    *,
    field: str,
    pack_root: Path,
    workspace_root: Path | None = None,
) -> Path:
    absolute = _safe_path_outside_git(path, must_exist=True, field=field)
    if absolute == pack_root or absolute.is_relative_to(pack_root):
        raise HumanReviewFinalizerError(f"{field} must remain outside the frozen asset pack")
    if _containing_console_workspace(absolute) is not None:
        raise HumanReviewFinalizerError(
            f"{field} must remain outside every human-review console workspace"
        )
    if workspace_root is not None and (
        absolute == workspace_root or absolute.is_relative_to(workspace_root)
    ):
        raise HumanReviewFinalizerError(
            f"{field} must remain outside the verified review workspace"
        )
    return absolute


def _verify_private_record_sha256(
    absolute: Path,
    *,
    expected_sha256: str,
    field: str,
) -> SafeLocalFile:
    try:
        record = read_safe_local_file(absolute, max_bytes=MAX_PRIVATE_RECORD_BYTES)
    except RealAssetMediaError as exc:
        raise HumanReviewFinalizerError(f"{field} is not a stable private local record") from exc
    if record.sha256 != expected_sha256:
        raise HumanReviewFinalizerError(f"{field} SHA-256 does not match the canonical draft")
    return record


def _read_private_record(
    path: Path,
    *,
    expected_sha256: str,
    field: str,
    pack_root: Path,
    workspace_root: Path | None = None,
) -> SafeLocalFile:
    absolute = _validated_private_record_path(
        path,
        field=field,
        pack_root=pack_root,
        workspace_root=workspace_root,
    )
    return _verify_private_record_sha256(
        absolute,
        expected_sha256=expected_sha256,
        field=field,
    )


def _assert_private_record_unchanged(
    before: SafeLocalFile,
    after: SafeLocalFile,
    *,
    field: str,
) -> None:
    if (
        before.path != after.path
        or before.identity != after.identity
        or before.sha256 != after.sha256
        or before.size_bytes != after.size_bytes
    ):
        raise HumanReviewFinalizerError(
            f"{field} drifted during local finalization"
        )


def _pack_snapshot(pack_root: Path) -> FrozenRealAssetPack:
    absolute = _safe_path_outside_git(pack_root, must_exist=True, field="frozen pack")
    try:
        return verify_real_asset_candidate_pack(absolute)
    except RealAssetIntakeError as exc:
        raise HumanReviewFinalizerError("frozen pack verification failed") from exc


def _workspace_snapshot(
    *,
    pack_root: Path,
    workspace_root: Path,
    workspace_kind: WorkspaceKind,
    evidence_path: Path | None = None,
) -> HumanReviewConsoleWorkspace:
    try:
        return verify_human_review_console_workspace(
            pack_root,
            workspace_root,
            workspace_kind,
            evidence_path=evidence_path,
        )
    except (HumanReviewConsoleError, RealAssetIntakeError) as exc:
        raise HumanReviewFinalizerError(
            "human-review console workspace verification failed"
        ) from exc


def _assert_workspace_unchanged(
    before: HumanReviewConsoleWorkspace,
    after: HumanReviewConsoleWorkspace,
) -> None:
    if before != after:
        raise HumanReviewFinalizerError(
            "human-review console workspace drifted during local finalization"
        )


def _workspace_file_digests(
    workspace: HumanReviewConsoleWorkspace,
) -> frozenset[str]:
    digests: set[str] = set()
    for name in _CONSOLE_WORKSPACE_MARKERS:
        try:
            snapshot = read_safe_local_file(
                workspace.root / name,
                max_bytes=MAX_PRIVATE_RECORD_BYTES,
            )
        except RealAssetMediaError as exc:
            raise HumanReviewFinalizerError(
                "verified review workspace files could not be rehashed safely"
            ) from exc
        digests.add(snapshot.sha256)
    if workspace.review_context_sha256 not in digests:
        raise HumanReviewFinalizerError(
            "verified review workspace context digest is inconsistent"
        )
    return frozenset(digests)


def _assert_pack_unchanged(before: FrozenRealAssetPack, after: FrozenRealAssetPack) -> None:
    if (
        before.root != after.root
        or before.manifest != after.manifest
        or _sha256(_canonical_document(before.manifest))
        != _sha256(_canonical_document(after.manifest))
    ):
        raise HumanReviewFinalizerError("frozen pack drifted during local finalization")


def _binding_from_descriptor(
    descriptor: FrozenRealAssetDescriptor,
) -> RealAssetRightsEvidenceBindingV2:
    return RealAssetRightsEvidenceBindingV2(
        ordinal=descriptor.ordinal,
        requirement_id=descriptor.requirement_id,
        kind=descriptor.kind,
        subject_id=descriptor.subject_id,
        logical_path=descriptor.logical_path,
        object_path=descriptor.object_path,
        media_type=descriptor.media_type,
        media_sha256=descriptor.sha256,
        media_size_bytes=descriptor.size_bytes,
        duration_ms=descriptor.duration_ms,
        source_authority=descriptor.source_authority,
        provenance_record_sha256=descriptor.provenance_record_sha256,
        technical_profile=descriptor.technical_profile,
        technical_record_sha256=descriptor.technical_record_sha256,
    )


def _pack_bindings(
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> tuple[RealAssetRightsEvidenceBindingV2, ...]:
    return tuple(_binding_from_descriptor(descriptor) for descriptor in pack.objects)


def _verify_evidence_against_pack(
    *,
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
    if rebuilt != evidence:
        raise HumanReviewFinalizerError("rights evidence bundle drifted from the frozen pack")


def _load_evidence(
    path: Path,
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> CreativeSampleRealAssetRightsEvidenceBundleV2:
    absolute = _safe_path_outside_git(path, must_exist=True, field="rights evidence bundle")
    try:
        evidence = load_real_asset_rights_evidence_bundle_v2(absolute)
    except RealAssetReviewV2Error as exc:
        raise HumanReviewFinalizerError("rights evidence bundle is not canonical") from exc
    _verify_evidence_against_pack(pack=pack, evidence=evidence)
    return evidence


def _load_review(
    path: Path,
    *,
    field: str,
) -> CreativeSampleRealAssetHumanPackReviewV2:
    absolute = _safe_path_outside_git(path, must_exist=True, field=field)
    try:
        return load_real_asset_human_pack_review_v2(absolute)
    except RealAssetReviewV2Error as exc:
        raise HumanReviewFinalizerError(f"{field} is not canonical") from exc


def finalize_rights_evidence_bundle(
    *,
    pack_root: Path,
    workspace_root: Path,
    evidence_draft_path: Path,
    evidence_record_path: Path,
    output_path: Path,
) -> CreativeSampleRealAssetRightsEvidenceBundleV2:
    """Finalize one canonical evidence draft after independent record and Pack checks."""

    before = _pack_snapshot(pack_root)
    workspace = _workspace_snapshot(
        pack_root=before.root,
        workspace_root=workspace_root,
        workspace_kind="EVIDENCE",
    )
    workspace_digests = _workspace_file_digests(workspace)
    target = _prepare_output(
        output_path,
        pack_root=before.root,
        workspace_root=workspace.root,
    )
    draft_contract_path = _safe_path_outside_git(
        evidence_draft_path,
        must_exist=True,
        field="review draft",
    )
    draft = cast(
        CreativeSampleRealAssetRightsEvidenceDraftV2,
        _load_draft(draft_contract_path, CreativeSampleRealAssetRightsEvidenceDraftV2),
    )
    if draft.pack_id != before.manifest.pack_id or workspace.pack_id != draft.pack_id:
        raise HumanReviewFinalizerError("evidence draft binds a different frozen pack")
    if workspace.workspace_kind != "EVIDENCE":
        raise HumanReviewFinalizerError("evidence finalization requires an EVIDENCE workspace")
    if draft.review_context_sha256 != workspace.review_context_sha256:
        raise HumanReviewFinalizerError("evidence draft review context digest drifted")
    if draft.evidence_record_sha256 in workspace_digests:
        raise HumanReviewFinalizerError(
            "private evidence record must not alias verified workspace files"
        )
    expected_manifest_sha256 = _sha256(_canonical_document(before.manifest))
    if draft.pack_manifest_sha256 != expected_manifest_sha256:
        raise HumanReviewFinalizerError("evidence draft pack manifest digest drifted")
    if draft.asset_bindings != _pack_bindings(before.manifest):
        raise HumanReviewFinalizerError("evidence draft bindings drifted from the fourteen objects")
    evidence_record_path_absolute = _validated_private_record_path(
        evidence_record_path,
        field="private evidence record",
        pack_root=before.root,
        workspace_root=workspace.root,
    )
    if _paths_overlap(evidence_record_path_absolute, draft_contract_path):
        raise HumanReviewFinalizerError(
            "private evidence record must not alias its evidence draft"
        )
    evidence_record = _verify_private_record_sha256(
        evidence_record_path_absolute,
        expected_sha256=draft.evidence_record_sha256,
        field="private evidence record",
    )
    evidence = build_real_asset_rights_evidence_bundle_v2(
        pack=before.manifest,
        evidence_record_sha256=draft.evidence_record_sha256,
        copyright_basis=draft.copyright_basis,
        likeness_basis=draft.likeness_basis,
        privacy_basis=draft.privacy_basis,
        territory=draft.territory,
        use_scope=draft.use_scope,
        valid_until=draft.valid_until,
    )
    after = _pack_snapshot(before.root)
    _assert_pack_unchanged(before, after)
    workspace_after = _workspace_snapshot(
        pack_root=after.root,
        workspace_root=workspace.root,
        workspace_kind="EVIDENCE",
    )
    _assert_workspace_unchanged(workspace, workspace_after)
    if _workspace_file_digests(workspace_after) != workspace_digests:
        raise HumanReviewFinalizerError(
            "human-review console workspace files drifted during local finalization"
        )
    evidence_record_after = _read_private_record(
        evidence_record.path,
        expected_sha256=draft.evidence_record_sha256,
        field="private evidence record",
        pack_root=after.root,
        workspace_root=workspace_after.root,
    )
    _assert_private_record_unchanged(
        evidence_record,
        evidence_record_after,
        field="private evidence record",
    )
    try:
        write_new_real_asset_review_v2_document(target, evidence)
    except RealAssetReviewV2Error as exc:
        raise HumanReviewFinalizerError("evidence bundle could not be published new-only") from exc
    return evidence


def _expected_draft_findings(
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> tuple[tuple[int, str, str, str, int], ...]:
    return tuple(
        (
            descriptor.ordinal,
            descriptor.requirement_id,
            descriptor.logical_path,
            descriptor.sha256,
            descriptor.size_bytes,
        )
        for descriptor in pack.objects
    )


def _draft_finding_identities(
    draft: CreativeSampleRealAssetHumanPackReviewDraftV2,
) -> tuple[tuple[int, str, str, str, int], ...]:
    return tuple(
        (
            finding.ordinal,
            finding.requirement_id,
            finding.logical_path,
            finding.media_sha256,
            finding.media_size_bytes,
        )
        for finding in draft.asset_findings
    )


def _exceptions_from_draft(
    draft: CreativeSampleRealAssetHumanPackReviewDraftV2,
) -> tuple[tuple[int, RealAssetReviewExceptionV2], ...]:
    return tuple(
        (
            finding.ordinal,
            RealAssetReviewExceptionV2(
                failed_gates=finding.failed_gates,
                finding=finding.exception_finding,
            ),
        )
        for finding in draft.asset_findings
        if finding.exception_finding is not None
    )


def finalize_human_pack_review(
    *,
    pack_root: Path,
    workspace_root: Path,
    evidence_bundle_path: Path,
    review_draft_path: Path,
    reviewer_record_path: Path,
    expected_role: Literal["REVIEWER_A", "REVIEWER_B"],
    output_path: Path,
    reviewed_at: str,
) -> CreativeSampleRealAssetHumanPackReviewV2:
    """Finalize one reviewer draft; ``reviewed_at`` is explicit and never read here."""

    reviewed_at = _utc_seconds(reviewed_at, field="reviewed_at")
    before = _pack_snapshot(pack_root)
    evidence_contract_path = _safe_path_outside_git(
        evidence_bundle_path,
        must_exist=True,
        field="rights evidence bundle",
    )
    review_draft_contract_path = _safe_path_outside_git(
        review_draft_path,
        must_exist=True,
        field="review draft",
    )
    workspace = _workspace_snapshot(
        pack_root=before.root,
        workspace_root=workspace_root,
        workspace_kind=expected_role,
        evidence_path=evidence_contract_path,
    )
    workspace_digests = _workspace_file_digests(workspace)
    target = _prepare_output(
        output_path,
        pack_root=before.root,
        workspace_root=workspace.root,
    )
    evidence = _load_evidence(evidence_contract_path, pack=before.manifest)
    draft = cast(
        CreativeSampleRealAssetHumanPackReviewDraftV2,
        _load_draft(
            review_draft_contract_path,
            CreativeSampleRealAssetHumanPackReviewDraftV2,
        ),
    )
    if draft.pack_id != before.manifest.pack_id or workspace.pack_id != draft.pack_id:
        raise HumanReviewFinalizerError("review draft binds a different frozen pack")
    if workspace.workspace_kind != expected_role:
        raise HumanReviewFinalizerError(
            "review finalization requires the expected reviewer workspace"
        )
    if draft.review_context_sha256 != workspace.review_context_sha256:
        raise HumanReviewFinalizerError("review draft review context digest drifted")
    if draft.reviewer_ref_sha256 in workspace_digests:
        raise HumanReviewFinalizerError(
            "private reviewer record must not alias verified workspace files"
        )
    if draft.pack_manifest_sha256 != _sha256(_canonical_document(before.manifest)):
        raise HumanReviewFinalizerError("review draft pack manifest digest drifted")
    evidence_document_sha256 = _sha256(_canonical_document(evidence))
    if (
        draft.evidence_bundle_id != evidence.bundle_id
        or workspace.evidence_bundle_id != evidence.bundle_id
    ):
        raise HumanReviewFinalizerError("review draft binds a different rights evidence bundle")
    if (
        draft.evidence_bundle_sha256 != evidence_document_sha256
        or workspace.evidence_bundle_sha256 != evidence_document_sha256
    ):
        raise HumanReviewFinalizerError("review draft evidence bundle digest drifted")
    if draft.reviewer_role != expected_role:
        raise HumanReviewFinalizerError("review draft does not match the expected reviewer role")
    if draft.reviewer_ref_sha256 in {
        evidence.evidence_record_sha256,
        evidence.pack_manifest_sha256,
        evidence_document_sha256,
    }:
        raise HumanReviewFinalizerError(
            "reviewer reference must be independent of Pack and rights evidence records"
        )
    if _draft_finding_identities(draft) != _expected_draft_findings(before.manifest):
        raise HumanReviewFinalizerError("review draft findings drifted from the fourteen objects")
    reviewer_record_path_absolute = _validated_private_record_path(
        reviewer_record_path,
        field="private reviewer record",
        pack_root=before.root,
        workspace_root=workspace.root,
    )
    if any(
        _paths_overlap(reviewer_record_path_absolute, contract_path)
        for contract_path in (evidence_contract_path, review_draft_contract_path)
    ):
        raise HumanReviewFinalizerError(
            "private reviewer record must not alias evidence or review draft contracts"
        )
    reviewer_record = _verify_private_record_sha256(
        reviewer_record_path_absolute,
        expected_sha256=draft.reviewer_ref_sha256,
        field="private reviewer record",
    )
    findings = build_real_asset_human_findings_v2(
        pack=before.manifest,
        confirmed_ordinals=tuple(finding.ordinal for finding in draft.asset_findings),
        content_role_approvals=tuple(
            finding.content_role_approved for finding in draft.asset_findings
        ),
        exceptions=_exceptions_from_draft(draft),
    )
    review = build_real_asset_human_pack_review_v2(
        pack=before.manifest,
        evidence=evidence,
        reviewer_role=expected_role,
        reviewer_ref_sha256=draft.reviewer_ref_sha256,
        reviewed_at=reviewed_at,
        findings=findings,
        provenance_approved=draft.provenance_approved,
        copyright_approved=draft.copyright_approved,
        likeness_approved=draft.likeness_approved,
        privacy_approved=draft.privacy_approved,
        territory_approved=draft.territory_approved,
        use_scope_approved=draft.use_scope_approved,
        decision=draft.decision,
        rejection_reason=draft.rejection_reason,
    )
    after = _pack_snapshot(before.root)
    _assert_pack_unchanged(before, after)
    workspace_after = _workspace_snapshot(
        pack_root=after.root,
        workspace_root=workspace.root,
        workspace_kind=expected_role,
        evidence_path=evidence_contract_path,
    )
    _assert_workspace_unchanged(workspace, workspace_after)
    if _workspace_file_digests(workspace_after) != workspace_digests:
        raise HumanReviewFinalizerError(
            "human-review console workspace files drifted during local finalization"
        )
    reviewer_record_after = _read_private_record(
        reviewer_record.path,
        expected_sha256=draft.reviewer_ref_sha256,
        field="private reviewer record",
        pack_root=after.root,
        workspace_root=workspace_after.root,
    )
    _assert_private_record_unchanged(
        reviewer_record,
        reviewer_record_after,
        field="private reviewer record",
    )
    try:
        write_new_real_asset_review_v2_document(target, review)
    except RealAssetReviewV2Error as exc:
        raise HumanReviewFinalizerError(
            "human Pack review could not be published new-only"
        ) from exc
    return review


def check_human_review_pair(
    *,
    pack_root: Path,
    evidence_bundle_path: Path,
    evidence_record_path: Path,
    reviewer_a_path: Path,
    reviewer_a_record_path: Path,
    reviewer_b_path: Path,
    reviewer_b_record_path: Path,
    output_path: Path,
    evaluated_at: str,
) -> CreativeSampleRealAssetReviewPairCheckV2:
    """Create a zero-authority A/B PairCheck after a second exact Pack verification."""

    evaluated_at = _utc_seconds(evaluated_at, field="evaluated_at")
    before = _pack_snapshot(pack_root)
    target = _prepare_output(output_path, pack_root=before.root)
    evidence_contract_path = _safe_path_outside_git(
        evidence_bundle_path,
        must_exist=True,
        field="rights evidence bundle",
    )
    reviewer_a_contract_path = _safe_path_outside_git(
        reviewer_a_path,
        must_exist=True,
        field="Reviewer A contract",
    )
    reviewer_b_contract_path = _safe_path_outside_git(
        reviewer_b_path,
        must_exist=True,
        field="Reviewer B contract",
    )
    evidence = _load_evidence(evidence_contract_path, pack=before.manifest)
    reviewer_a = _load_review(reviewer_a_contract_path, field="Reviewer A contract")
    reviewer_b = _load_review(reviewer_b_contract_path, field="Reviewer B contract")
    record_specs = (
        (
            evidence_record_path,
            evidence.evidence_record_sha256,
            "private evidence record",
        ),
        (
            reviewer_a_record_path,
            reviewer_a.reviewer_ref_sha256,
            "private Reviewer A record",
        ),
        (
            reviewer_b_record_path,
            reviewer_b.reviewer_ref_sha256,
            "private Reviewer B record",
        ),
    )
    record_paths = tuple(
        _validated_private_record_path(path, field=field, pack_root=before.root)
        for path, _, field in record_specs
    )
    if len(set(record_paths)) != 3:
        raise HumanReviewFinalizerError(
            "evidence and reviewer private record paths must be distinct"
        )
    contract_paths = (
        before.root,
        before.manifest_path,
        evidence_contract_path,
        reviewer_a_contract_path,
        reviewer_b_contract_path,
    )
    if any(
        _paths_overlap(record_path, contract_path)
        for record_path in record_paths
        for contract_path in contract_paths
    ):
        raise HumanReviewFinalizerError(
            "private record paths must not alias Pack, evidence, or reviewer contracts"
        )
    contract_document_digests = {
        _sha256(_canonical_document(evidence)),
        _sha256(_canonical_document(reviewer_a)),
        _sha256(_canonical_document(reviewer_b)),
    }
    retained_record_digests = {
        evidence.evidence_record_sha256,
        reviewer_a.reviewer_ref_sha256,
        reviewer_b.reviewer_ref_sha256,
    }
    if contract_document_digests & retained_record_digests:
        raise HumanReviewFinalizerError(
            "private record digests must not alias evidence or reviewer contracts"
        )
    record_snapshots = tuple(
        _verify_private_record_sha256(
            absolute,
            expected_sha256=expected_sha256,
            field=field,
        )
        for absolute, (_, expected_sha256, field) in zip(
            record_paths, record_specs, strict=True
        )
    )
    try:
        pair_check = finalize_real_asset_review_pair_v2(
            pack=before.manifest,
            evidence=evidence,
            reviewer_a=reviewer_a,
            reviewer_b=reviewer_b,
            evaluated_at=evaluated_at,
        )
    except RealAssetReviewV2Error as exc:
        raise HumanReviewFinalizerError("human review pair does not close over the pack") from exc
    after = _pack_snapshot(before.root)
    _assert_pack_unchanged(before, after)
    evidence_after = _load_evidence(evidence_contract_path, pack=after.manifest)
    reviewer_a_after = _load_review(
        reviewer_a_contract_path,
        field="Reviewer A contract",
    )
    reviewer_b_after = _load_review(
        reviewer_b_contract_path,
        field="Reviewer B contract",
    )
    if (
        evidence_after != evidence
        or reviewer_a_after != reviewer_a
        or reviewer_b_after != reviewer_b
    ):
        raise HumanReviewFinalizerError(
            "evidence or reviewer contracts drifted during PairCheck finalization"
        )
    record_snapshots_after = tuple(
        _read_private_record(
            snapshot.path,
            expected_sha256=expected_sha256,
            field=field,
            pack_root=after.root,
        )
        for snapshot, (_, expected_sha256, field) in zip(
            record_snapshots, record_specs, strict=True
        )
    )
    for record_before, record_after, (_, _, field) in zip(
        record_snapshots,
        record_snapshots_after,
        record_specs,
        strict=True,
    ):
        _assert_private_record_unchanged(
            record_before,
            record_after,
            field=field,
        )
    try:
        write_new_real_asset_review_v2_document(target, pair_check)
    except RealAssetReviewV2Error as exc:
        raise HumanReviewFinalizerError("review PairCheck could not be published new-only") from exc
    return pair_check


def _current_utc_seconds() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Finalize offline Creative Sample review drafts")
    commands = parser.add_subparsers(dest="command", required=True)

    evidence = commands.add_parser("finalize-evidence")
    evidence.add_argument("--pack-root", type=Path, required=True)
    evidence.add_argument("--workspace", type=Path, required=True)
    evidence.add_argument("--draft", type=Path, required=True)
    evidence.add_argument("--evidence-record", type=Path, required=True)
    evidence.add_argument("--output", type=Path, required=True)

    review = commands.add_parser("finalize-review")
    review.add_argument("--pack-root", type=Path, required=True)
    review.add_argument("--workspace", type=Path, required=True)
    review.add_argument("--evidence", type=Path, required=True)
    review.add_argument("--draft", type=Path, required=True)
    review.add_argument("--reviewer-record", type=Path, required=True)
    review.add_argument(
        "--expected-role", choices=("REVIEWER_A", "REVIEWER_B"), required=True
    )
    review.add_argument("--output", type=Path, required=True)

    pair = commands.add_parser("check-pair")
    pair.add_argument("--pack-root", type=Path, required=True)
    pair.add_argument("--evidence", type=Path, required=True)
    pair.add_argument("--evidence-record", type=Path, required=True)
    pair.add_argument("--reviewer-a", type=Path, required=True)
    pair.add_argument("--reviewer-a-record", type=Path, required=True)
    pair.add_argument("--reviewer-b", type=Path, required=True)
    pair.add_argument("--reviewer-b-record", type=Path, required=True)
    pair.add_argument("--output", type=Path, required=True)
    return parser


def _main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "finalize-evidence":
        evidence_document = finalize_rights_evidence_bundle(
            pack_root=args.pack_root,
            workspace_root=args.workspace,
            evidence_draft_path=args.draft,
            evidence_record_path=args.evidence_record,
            output_path=args.output,
        )
        summary: dict[str, object] = {
            "command": args.command,
            "document_id": evidence_document.bundle_id,
            "output": str(args.output.absolute()),
            "pack_id": evidence_document.pack_id,
        }
    elif args.command == "finalize-review":
        review_document = finalize_human_pack_review(
            pack_root=args.pack_root,
            workspace_root=args.workspace,
            evidence_bundle_path=args.evidence,
            review_draft_path=args.draft,
            reviewer_record_path=args.reviewer_record,
            expected_role=args.expected_role,
            output_path=args.output,
            reviewed_at=_current_utc_seconds(),
        )
        summary = {
            "command": args.command,
            "document_id": review_document.review_id,
            "output": str(args.output.absolute()),
            "pack_id": review_document.pack_id,
            "reviewer_role": review_document.reviewer_role,
        }
    else:
        pair_document = check_human_review_pair(
            pack_root=args.pack_root,
            evidence_bundle_path=args.evidence,
            evidence_record_path=args.evidence_record,
            reviewer_a_path=args.reviewer_a,
            reviewer_a_record_path=args.reviewer_a_record,
            reviewer_b_path=args.reviewer_b,
            reviewer_b_record_path=args.reviewer_b_record,
            output_path=args.output,
            evaluated_at=_current_utc_seconds(),
        )
        summary = {
            "command": args.command,
            "document_id": pair_document.pair_check_id,
            "output": str(args.output.absolute()),
            "pack_id": pair_document.pack_id,
            "status": pair_document.status,
        }
    summary.update(
        {
            "current_gate": "HUMAN_GATE",
            "execution_authorized": False,
            "posts_allowed": 0,
            "provider_requests": 0,
            "provider_state": "NOT_AUTHORIZED",
        }
    )
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


__all__ = [
    "CreativeSampleRealAssetHumanPackReviewDraftV2",
    "CreativeSampleRealAssetRightsEvidenceDraftV2",
    "HumanReviewFinalizerError",
    "RealAssetHumanFindingDraftV2",
    "check_human_review_pair",
    "finalize_human_pack_review",
    "finalize_rights_evidence_bundle",
]


if __name__ == "__main__":
    raise SystemExit(_main())
