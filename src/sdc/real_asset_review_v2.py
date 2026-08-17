"""Offline pack-level human review contracts for frozen Creative Sample media.

Review v2 reduces repeated human entry without weakening the frozen-byte closure.  It does not
create a rights manifest, qualify an asset pack, authorize execution, or integrate with a Provider,
runtime, database, ledger, entitlement, or authorization path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from sdc.compiler import stable_id
from sdc.real_asset_intake import (
    CreativeSampleFrozenRealAssetPackManifest,
    FrozenRealAssetDescriptor,
    RealAssetIntakeError,
    _canonical_document,
    _canonical_payload,
    _logical_path,
    _parse_utc,
    _portable_text,
    _read_strict_json,
    _sha256,
    _utc_seconds,
    _write_new_document,
)

REVIEW_V2_PROFILE: Literal["creative-sample-real-asset-review-v2"] = (
    "creative-sample-real-asset-review-v2"
)

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_PORTABLE_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"

type RightsGateV2 = Literal[
    "PROVENANCE",
    "COPYRIGHT",
    "LIKENESS",
    "PRIVACY",
    "TERRITORY",
    "USE_SCOPE",
    "CONTENT_ROLE",
]
type ReviewPairIssueV2 = Literal[
    "REVIEWER_A_MISSING",
    "REVIEWER_B_MISSING",
    "REVIEWER_IDENTITIES_NOT_DISTINCT",
    "REVIEW_RECORDS_NOT_DISTINCT",
    "REVIEWER_A_NOT_APPROVED",
    "REVIEWER_B_NOT_APPROVED",
    "APPROVALS_DISAGREE",
    "REVIEWER_A_HAS_EXCEPTIONS",
    "REVIEWER_B_HAS_EXCEPTIONS",
    "REVIEWER_A_IN_FUTURE",
    "REVIEWER_B_IN_FUTURE",
    "RIGHTS_EXPIRED",
]

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
_ISSUE_ORDER: tuple[ReviewPairIssueV2, ...] = (
    "REVIEWER_A_MISSING",
    "REVIEWER_B_MISSING",
    "REVIEWER_IDENTITIES_NOT_DISTINCT",
    "REVIEW_RECORDS_NOT_DISTINCT",
    "REVIEWER_A_NOT_APPROVED",
    "REVIEWER_B_NOT_APPROVED",
    "APPROVALS_DISAGREE",
    "REVIEWER_A_HAS_EXCEPTIONS",
    "REVIEWER_B_HAS_EXCEPTIONS",
    "REVIEWER_A_IN_FUTURE",
    "REVIEWER_B_IN_FUTURE",
    "RIGHTS_EXPIRED",
)
_REVIEW_RECORD_DOMAIN = b"sdc:creative-sample-real-asset-human-pack-review:v2\0"


class RealAssetReviewV2Error(RuntimeError):
    """A local Review v2 integrity or closure check failed closed."""


class _ReviewV2Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class RealAssetRightsEvidenceBindingV2(_ReviewV2Model):
    """Mechanical identity of one member of the exact frozen fourteen-object pack."""

    ordinal: Annotated[int, Field(ge=0, le=13)]
    requirement_id: str = Field(pattern=r"^real_asset_requirement_[0-9a-f]{20}$")
    kind: Literal["IMAGE", "VOICE", "BGM"]
    subject_id: str = Field(pattern=_PORTABLE_ID)
    logical_path: str
    object_path: str
    media_type: Literal["image/png", "audio/wav"]
    media_sha256: str = Field(pattern=_LOWER_SHA256)
    media_size_bytes: Annotated[int, Field(gt=0)]
    duration_ms: Annotated[int, Field(ge=0)]
    source_authority: Literal[
        "USER_PROVIDED_LOCAL", "SEPARATELY_APPROVED_LOCAL_GENERATION"
    ]
    provenance_record_sha256: str = Field(pattern=_LOWER_SHA256)
    technical_profile: str = Field(pattern=_PORTABLE_ID)
    technical_record_sha256: str = Field(pattern=_LOWER_SHA256)

    @field_validator("logical_path", "object_path")
    @classmethod
    def validate_paths(cls, value: str) -> str:
        return _logical_path(value)

    @model_validator(mode="after")
    def validate_binding(self) -> RealAssetRightsEvidenceBindingV2:
        if self.object_path != f"objects/{self.media_sha256[:2]}/{self.media_sha256}":
            raise ValueError("review binding object path must derive from its exact media digest")
        if (self.kind == "IMAGE") != (self.media_type == "image/png"):
            raise ValueError("review binding media type must match its exact media kind")
        if (self.kind == "IMAGE") != (self.duration_ms == 0):
            raise ValueError("review binding duration must match its exact media kind")
        return self


class RealAssetReviewExceptionV2(_ReviewV2Model):
    """One human-authored blocking finding for a particular reviewed asset."""

    failed_gates: tuple[RightsGateV2, ...] = Field(min_length=1, max_length=7)
    finding: str = Field(min_length=1, max_length=1000)

    @field_validator("failed_gates")
    @classmethod
    def validate_failed_gates(
        cls, value: tuple[RightsGateV2, ...]
    ) -> tuple[RightsGateV2, ...]:
        if len(value) != len(set(value)):
            raise ValueError("asset review exception gates must be unique")
        if value != tuple(gate for gate in _GATE_ORDER if gate in value):
            raise ValueError("asset review exception gates must use canonical order")
        return value

    @field_validator("finding")
    @classmethod
    def validate_finding(cls, value: str) -> str:
        return _portable_text(value, field="asset review exception")


class RealAssetHumanFindingV2(_ReviewV2Model):
    """Explicit human inspection of one exact frozen binding."""

    binding: RealAssetRightsEvidenceBindingV2
    inspection_confirmed: Literal[True]
    content_role_approved: bool
    exception: RealAssetReviewExceptionV2 | None = None


class CreativeSampleRealAssetRightsEvidenceBundleV2(_ReviewV2Model):
    """One normalized Pack-level declaration, never an approval or authorization."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-rights-evidence-bundle-v2"
    ] = "sdc.creative-sample-real-asset-rights-evidence-bundle-v2"
    profile: Literal["creative-sample-real-asset-review-v2"] = REVIEW_V2_PROFILE
    bundle_id: str = Field(pattern=r"^real_asset_rights_evidence_v2_[0-9a-f]{20}$")
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    pack_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
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
    status: Literal["EVIDENCE_CANDIDATE"] = "EVIDENCE_CANDIDATE"
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
        return _portable_text(value, field="Pack-level rights basis")

    @field_validator("territory")
    @classmethod
    def validate_territory(cls, value: str) -> str:
        return _portable_text(value, field="Pack-level territory", maximum=256)

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, value: str) -> str:
        if value == "PERPETUAL":
            return value
        return _utc_seconds(value, field="valid_until")

    @model_validator(mode="after")
    def validate_bundle(self) -> CreativeSampleRealAssetRightsEvidenceBundleV2:
        if tuple(item.ordinal for item in self.asset_bindings) != tuple(range(14)):
            raise ValueError("rights evidence bindings must use exact canonical ordinals")
        if len({item.requirement_id for item in self.asset_bindings}) != 14:
            raise ValueError("rights evidence requirement bindings must be unique")
        if len({item.logical_path.casefold() for item in self.asset_bindings}) != 14:
            raise ValueError("rights evidence logical paths must be unique")
        if len({item.media_sha256 for item in self.asset_bindings}) != 14:
            raise ValueError("rights evidence media identities must be unique")
        bound_digests = {
            digest
            for item in self.asset_bindings
            for digest in (
                item.media_sha256,
                item.provenance_record_sha256,
                item.technical_record_sha256,
            )
        }
        bound_digests.add(self.pack_manifest_sha256)
        if self.evidence_record_sha256 in bound_digests:
            raise ValueError("evidence record digest must be independent of frozen asset digests")
        expected = stable_id(
            "real_asset_rights_evidence_v2",
            self.model_dump(mode="json", exclude={"bundle_id"}),
        )
        if self.bundle_id != expected:
            raise ValueError("rights evidence bundle ID must bind its complete canonical content")
        return self


class CreativeSampleRealAssetHumanPackReviewV2(_ReviewV2Model):
    """One complete human review of all fourteen exact frozen members."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-human-pack-review-v2"
    ] = "sdc.creative-sample-real-asset-human-pack-review-v2"
    profile: Literal["creative-sample-real-asset-review-v2"] = REVIEW_V2_PROFILE
    review_id: str = Field(pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$")
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    rights_evidence_bundle_id: str = Field(
        pattern=r"^real_asset_rights_evidence_v2_[0-9a-f]{20}$"
    )
    reviewer_role: Literal["REVIEWER_A", "REVIEWER_B"]
    reviewer_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    review_record_sha256: str = Field(pattern=_LOWER_SHA256)
    reviewed_at: str
    findings: tuple[RealAssetHumanFindingV2, ...] = Field(min_length=14, max_length=14)
    provenance_approved: bool
    copyright_approved: bool
    likeness_approved: bool
    privacy_approved: bool
    territory_approved: bool
    use_scope_approved: bool
    rejection_reason: str | None = Field(default=None, min_length=1, max_length=1000)
    decision: Literal["APPROVED", "REJECTED"]
    status: Literal["REVIEW_COMPLETE"] = "REVIEW_COMPLETE"
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @field_validator("reviewed_at")
    @classmethod
    def validate_reviewed_at(cls, value: str) -> str:
        return _utc_seconds(value, field="reviewed_at")

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _portable_text(value, field="Pack review rejection reason")

    @model_validator(mode="after")
    def validate_review(self) -> CreativeSampleRealAssetHumanPackReviewV2:
        bindings = tuple(item.binding for item in self.findings)
        if tuple(item.ordinal for item in bindings) != tuple(range(14)):
            raise ValueError("human review findings must use exact canonical ordinals")
        if len({item.requirement_id for item in bindings}) != 14:
            raise ValueError("human review findings must bind unique requirements")
        if len({item.media_sha256 for item in bindings}) != 14:
            raise ValueError("human review findings must bind unique media identities")
        bound_digests = {
            digest
            for item in bindings
            for digest in (
                item.media_sha256,
                item.provenance_record_sha256,
                item.technical_record_sha256,
            )
        }
        if self.reviewer_ref_sha256 in bound_digests:
            raise ValueError("reviewer reference must be independent of frozen asset digests")

        outcomes = _review_outcomes(self)
        exceptions = tuple(
            item.exception for item in self.findings if item.exception is not None
        )
        for finding in self.findings:
            if finding.exception is None:
                continue
            for gate in finding.exception.failed_gates:
                if gate == "CONTENT_ROLE":
                    if finding.content_role_approved:
                        raise ValueError(
                            "a content-role exception requires that exact finding to fail"
                        )
                elif bool(getattr(self, _GATE_TO_FIELD[gate])):
                    raise ValueError("an asset exception gate must fail at Pack level")
        if self.decision == "APPROVED":
            if not all(outcomes):
                raise ValueError("an approved Pack review requires every rights gate to pass")
            if exceptions:
                raise ValueError("an approved Pack review cannot retain an asset exception")
            if self.rejection_reason is not None:
                raise ValueError("an approved Pack review cannot contain a rejection reason")
        else:
            if all(outcomes):
                raise ValueError("a rejected Pack review must identify a failed rights gate")
            if self.rejection_reason is None:
                raise ValueError("a rejected Pack review requires a human-authored reason")

        record_payload = self.model_dump(
            mode="json", exclude={"review_id", "review_record_sha256"}
        )
        expected_record = _sha256(_REVIEW_RECORD_DOMAIN + _canonical_payload(record_payload))
        if self.review_record_sha256 != expected_record:
            raise ValueError("review record digest must bind the exact human Pack review")
        expected_id = stable_id(
            "real_asset_pack_review_v2",
            self.model_dump(mode="json", exclude={"review_id"}),
        )
        if self.review_id != expected_id:
            raise ValueError("human Pack review ID must bind its complete canonical content")
        return self


class CreativeSampleRealAssetReviewPairCheckV2(_ReviewV2Model):
    """A zero-authority report over the two Pack reviews, not qualification."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-review-pair-check-v2"
    ] = "sdc.creative-sample-real-asset-review-pair-check-v2"
    profile: Literal["creative-sample-real-asset-review-v2"] = REVIEW_V2_PROFILE
    pair_check_id: str = Field(pattern=r"^real_asset_review_pair_check_v2_[0-9a-f]{20}$")
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    rights_evidence_bundle_id: str = Field(
        pattern=r"^real_asset_rights_evidence_v2_[0-9a-f]{20}$"
    )
    review_a_id: str | None = Field(
        default=None, pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$"
    )
    review_b_id: str | None = Field(
        default=None, pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$"
    )
    review_a_record_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    review_b_record_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    review_count: Annotated[int, Field(ge=0, le=2)]
    evaluated_at: str
    asset_count: Literal[14] = 14
    issue_codes: tuple[ReviewPairIssueV2, ...] = Field(default=(), max_length=12)
    status: Literal[
        "INCOMPLETE",
        "DISAGREEMENT",
        "READY_FOR_SEPARATE_QUALIFICATION_REVIEW",
    ]
    rights_manifest_created: Literal[False] = False
    rights_qualification_performed: Literal[False] = False
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @field_validator("evaluated_at")
    @classmethod
    def validate_evaluated_at(cls, value: str) -> str:
        return _utc_seconds(value, field="evaluated_at")

    @field_validator("issue_codes")
    @classmethod
    def validate_issue_codes(
        cls, value: tuple[ReviewPairIssueV2, ...]
    ) -> tuple[ReviewPairIssueV2, ...]:
        if len(value) != len(set(value)):
            raise ValueError("review pair issue codes must be unique")
        if value != tuple(issue for issue in _ISSUE_ORDER if issue in value):
            raise ValueError("review pair issue codes must use canonical order")
        return value

    @model_validator(mode="after")
    def validate_pair_check(self) -> CreativeSampleRealAssetReviewPairCheckV2:
        references = (
            (self.review_a_id, self.review_a_record_sha256),
            (self.review_b_id, self.review_b_record_sha256),
        )
        if any((review_id is None) != (record is None) for review_id, record in references):
            raise ValueError("review ID and record digest must be present together")
        if self.review_count != sum(review_id is not None for review_id, _ in references):
            raise ValueError("review pair count must match its exact review references")
        missing_codes = {
            issue for issue in self.issue_codes if issue.endswith("_MISSING")
        }
        if self.status == "INCOMPLETE":
            expected_missing = {
                issue
                for issue, review_id in (
                    ("REVIEWER_A_MISSING", self.review_a_id),
                    ("REVIEWER_B_MISSING", self.review_b_id),
                )
                if review_id is None
            }
            if missing_codes != expected_missing or not expected_missing:
                raise ValueError("incomplete pair check must identify every missing review")
        elif self.status == "READY_FOR_SEPARATE_QUALIFICATION_REVIEW":
            if self.review_count != 2 or self.issue_codes:
                raise ValueError("ready pair check requires two exact reviews and no issue")
        elif self.review_count != 2 or not self.issue_codes or missing_codes:
            raise ValueError("disagreement requires two reviews and a non-missing issue")

        expected = stable_id(
            "real_asset_review_pair_check_v2",
            self.model_dump(mode="json", exclude={"pair_check_id"}),
        )
        if self.pair_check_id != expected:
            raise ValueError("review pair check ID must bind its complete canonical content")
        return self


type ReviewV2Document = (
    CreativeSampleRealAssetRightsEvidenceBundleV2
    | CreativeSampleRealAssetHumanPackReviewV2
    | CreativeSampleRealAssetReviewPairCheckV2
)


def _review_outcomes(review: CreativeSampleRealAssetHumanPackReviewV2) -> tuple[bool, ...]:
    return (
        review.provenance_approved,
        review.copyright_approved,
        review.likeness_approved,
        review.privacy_approved,
        review.territory_approved,
        review.use_scope_approved,
        *(item.content_role_approved for item in review.findings),
    )


def _revalidate_model[ModelT: BaseModel](
    value: ModelT,
    model: type[ModelT],
    *,
    field: str,
) -> ModelT:
    try:
        return model.model_validate(value.model_dump(mode="python"), strict=True)
    except ValidationError as exc:
        raise RealAssetReviewV2Error(f"{field} does not match its strict v2 contract") from exc


def _revalidate_pack(
    pack: CreativeSampleFrozenRealAssetPackManifest,
) -> CreativeSampleFrozenRealAssetPackManifest:
    return _revalidate_model(
        pack,
        CreativeSampleFrozenRealAssetPackManifest,
        field="frozen asset pack",
    )


def _revalidate_evidence(
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> CreativeSampleRealAssetRightsEvidenceBundleV2:
    return _revalidate_model(
        evidence,
        CreativeSampleRealAssetRightsEvidenceBundleV2,
        field="rights evidence bundle",
    )


def _revalidate_review(
    review: CreativeSampleRealAssetHumanPackReviewV2,
) -> CreativeSampleRealAssetHumanPackReviewV2:
    return _revalidate_model(
        review,
        CreativeSampleRealAssetHumanPackReviewV2,
        field="human Pack review",
    )


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


def _verify_evidence_closure(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
) -> None:
    pack = _revalidate_pack(pack)
    evidence = _revalidate_evidence(evidence)
    if evidence.pack_id != pack.pack_id:
        raise RealAssetReviewV2Error("rights evidence binds a different frozen asset pack")
    if evidence.pack_manifest_sha256 != _sha256(_canonical_document(pack)):
        raise RealAssetReviewV2Error("rights evidence pack manifest digest drifted")
    if evidence.asset_bindings != _pack_bindings(pack):
        raise RealAssetReviewV2Error(
            "rights evidence does not close over the exact fourteen objects"
        )


def _verify_human_review_closure(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    review: CreativeSampleRealAssetHumanPackReviewV2,
    expected_role: Literal["REVIEWER_A", "REVIEWER_B"] | None = None,
) -> None:
    pack = _revalidate_pack(pack)
    evidence = _revalidate_evidence(evidence)
    review = _revalidate_review(review)
    if review.pack_id != pack.pack_id:
        raise RealAssetReviewV2Error("human review binds a different frozen asset pack")
    if review.rights_evidence_bundle_id != evidence.bundle_id:
        raise RealAssetReviewV2Error("human review binds a different rights evidence bundle")
    if expected_role is not None and review.reviewer_role != expected_role:
        raise RealAssetReviewV2Error("human review occupies the wrong independent reviewer role")
    if tuple(item.binding for item in review.findings) != evidence.asset_bindings:
        raise RealAssetReviewV2Error(
            "human review findings drifted from the exact fourteen objects"
        )


def build_real_asset_rights_evidence_bundle_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence_record_sha256: str,
    copyright_basis: str,
    likeness_basis: str,
    privacy_basis: str,
    territory: str,
    use_scope: str,
    valid_until: str,
) -> CreativeSampleRealAssetRightsEvidenceBundleV2:
    """Normalize caller-supplied Pack evidence; this performs no human approval."""

    pack = _revalidate_pack(pack)
    payload: dict[str, object] = {
        "schema_version": "2.0.0",
        "document_type": "sdc.creative-sample-real-asset-rights-evidence-bundle-v2",
        "profile": REVIEW_V2_PROFILE,
        "pack_id": pack.pack_id,
        "pack_manifest_sha256": _sha256(_canonical_document(pack)),
        "evidence_record_sha256": evidence_record_sha256,
        "asset_bindings": tuple(item.model_dump(mode="json") for item in _pack_bindings(pack)),
        "copyright_basis": copyright_basis,
        "likeness_basis": likeness_basis,
        "privacy_basis": privacy_basis,
        "territory": territory,
        "use_scope": use_scope,
        "valid_until": valid_until,
        "status": "EVIDENCE_CANDIDATE",
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetRightsEvidenceBundleV2.model_validate(
        {
            "bundle_id": stable_id("real_asset_rights_evidence_v2", payload),
            **payload,
        },
        strict=True,
    )


def build_real_asset_human_findings_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    confirmed_ordinals: tuple[int, ...],
    content_role_approvals: tuple[bool, ...],
    exceptions: tuple[tuple[int, RealAssetReviewExceptionV2], ...] = (),
) -> tuple[RealAssetHumanFindingV2, ...]:
    """Bind explicit human confirmations; it never checks boxes on the caller's behalf."""

    pack = _revalidate_pack(pack)
    if confirmed_ordinals != tuple(range(14)):
        raise RealAssetReviewV2Error("all fourteen assets require explicit ordered confirmation")
    if len(content_role_approvals) != 14:
        raise RealAssetReviewV2Error("all fourteen assets require an explicit content-role result")
    exception_by_ordinal: dict[int, RealAssetReviewExceptionV2] = {}
    for ordinal, exception in exceptions:
        if ordinal < 0 or ordinal >= 14:
            raise RealAssetReviewV2Error(
                "asset review exception ordinal is outside the frozen pack"
            )
        if ordinal in exception_by_ordinal:
            raise RealAssetReviewV2Error("one asset cannot contain duplicate exception containers")
        exception_by_ordinal[ordinal] = exception
    return tuple(
        RealAssetHumanFindingV2(
            binding=_binding_from_descriptor(descriptor),
            inspection_confirmed=True,
            content_role_approved=content_role_approvals[descriptor.ordinal],
            exception=exception_by_ordinal.get(descriptor.ordinal),
        )
        for descriptor in pack.objects
    )


def build_real_asset_human_pack_review_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_role: Literal["REVIEWER_A", "REVIEWER_B"],
    reviewer_ref_sha256: str,
    reviewed_at: str,
    findings: tuple[RealAssetHumanFindingV2, ...],
    provenance_approved: bool,
    copyright_approved: bool,
    likeness_approved: bool,
    privacy_approved: bool,
    territory_approved: bool,
    use_scope_approved: bool,
    decision: Literal["APPROVED", "REJECTED"],
    rejection_reason: str | None = None,
) -> CreativeSampleRealAssetHumanPackReviewV2:
    """Build one explicit complete review without reading a clock or choosing a conclusion."""

    pack = _revalidate_pack(pack)
    evidence = _revalidate_evidence(evidence)
    _verify_evidence_closure(pack=pack, evidence=evidence)
    if reviewer_ref_sha256 in {
        evidence.evidence_record_sha256,
        evidence.pack_manifest_sha256,
        _sha256(_canonical_document(evidence)),
    }:
        raise RealAssetReviewV2Error(
            "reviewer reference must be independent of Pack and rights evidence records"
        )
    payload: dict[str, object] = {
        "schema_version": "2.0.0",
        "document_type": "sdc.creative-sample-real-asset-human-pack-review-v2",
        "profile": REVIEW_V2_PROFILE,
        "pack_id": pack.pack_id,
        "rights_evidence_bundle_id": evidence.bundle_id,
        "reviewer_role": reviewer_role,
        "reviewer_ref_sha256": reviewer_ref_sha256,
        "reviewed_at": reviewed_at,
        "findings": tuple(item.model_dump(mode="python") for item in findings),
        "provenance_approved": provenance_approved,
        "copyright_approved": copyright_approved,
        "likeness_approved": likeness_approved,
        "privacy_approved": privacy_approved,
        "territory_approved": territory_approved,
        "use_scope_approved": use_scope_approved,
        "rejection_reason": rejection_reason,
        "decision": decision,
        "status": "REVIEW_COMPLETE",
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    review_record_sha256 = _sha256(
        _REVIEW_RECORD_DOMAIN + _canonical_payload(payload)
    )
    payload_with_record = {**payload, "review_record_sha256": review_record_sha256}
    review = CreativeSampleRealAssetHumanPackReviewV2.model_validate(
        {
            "review_id": stable_id("real_asset_pack_review_v2", payload_with_record),
            **payload_with_record,
        },
        strict=True,
    )
    _verify_human_review_closure(pack=pack, evidence=evidence, review=review)
    return review


def finalize_real_asset_review_pair_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2 | None,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2 | None,
    evaluated_at: str,
) -> CreativeSampleRealAssetReviewPairCheckV2:
    """Assess the local A/B closure and report readiness for a separate future review only."""

    pack = _revalidate_pack(pack)
    evidence = _revalidate_evidence(evidence)
    reviewer_a = _revalidate_review(reviewer_a) if reviewer_a is not None else None
    reviewer_b = _revalidate_review(reviewer_b) if reviewer_b is not None else None
    evaluated_at = _utc_seconds(evaluated_at, field="evaluated_at")
    evaluated = _parse_utc(evaluated_at)
    _verify_evidence_closure(pack=pack, evidence=evidence)
    if reviewer_a is not None:
        _verify_human_review_closure(
            pack=pack,
            evidence=evidence,
            review=reviewer_a,
            expected_role="REVIEWER_A",
        )
    if reviewer_b is not None:
        _verify_human_review_closure(
            pack=pack,
            evidence=evidence,
            review=reviewer_b,
            expected_role="REVIEWER_B",
        )

    reviews = tuple(
        review for review in (reviewer_a, reviewer_b) if review is not None
    )
    reviewer_reference_digests = {
        review.reviewer_ref_sha256 for review in reviews
    }
    if reviewer_reference_digests & {
        evidence.evidence_record_sha256,
        evidence.pack_manifest_sha256,
    }:
        raise RealAssetReviewV2Error(
            "reviewer references must be independent of Pack and rights evidence records"
        )
    canonical_contract_digests = {
        _sha256(_canonical_document(evidence)),
        *(_sha256(_canonical_document(review)) for review in reviews),
    }
    retained_record_digests = {
        evidence.evidence_record_sha256,
        *reviewer_reference_digests,
    }
    if canonical_contract_digests & retained_record_digests:
        raise RealAssetReviewV2Error(
            "retained evidence and reviewer references must not alias canonical contracts"
        )

    issues: set[ReviewPairIssueV2] = set()
    if reviewer_a is None:
        issues.add("REVIEWER_A_MISSING")
    if reviewer_b is None:
        issues.add("REVIEWER_B_MISSING")
    if reviewer_a is not None:
        if reviewer_a.decision != "APPROVED":
            issues.add("REVIEWER_A_NOT_APPROVED")
        if any(item.exception is not None for item in reviewer_a.findings):
            issues.add("REVIEWER_A_HAS_EXCEPTIONS")
        if _parse_utc(reviewer_a.reviewed_at) > evaluated:
            issues.add("REVIEWER_A_IN_FUTURE")
    if reviewer_b is not None:
        if reviewer_b.decision != "APPROVED":
            issues.add("REVIEWER_B_NOT_APPROVED")
        if any(item.exception is not None for item in reviewer_b.findings):
            issues.add("REVIEWER_B_HAS_EXCEPTIONS")
        if _parse_utc(reviewer_b.reviewed_at) > evaluated:
            issues.add("REVIEWER_B_IN_FUTURE")
    if reviewer_a is not None and reviewer_b is not None:
        if reviewer_a.reviewer_ref_sha256 == reviewer_b.reviewer_ref_sha256:
            issues.add("REVIEWER_IDENTITIES_NOT_DISTINCT")
        if reviewer_a.review_record_sha256 == reviewer_b.review_record_sha256:
            issues.add("REVIEW_RECORDS_NOT_DISTINCT")
        if _review_outcomes(reviewer_a) != _review_outcomes(reviewer_b):
            issues.add("APPROVALS_DISAGREE")
    if evidence.valid_until != "PERPETUAL" and evaluated >= _parse_utc(evidence.valid_until):
        issues.add("RIGHTS_EXPIRED")

    ordered_issues = tuple(issue for issue in _ISSUE_ORDER if issue in issues)
    review_count = int(reviewer_a is not None) + int(reviewer_b is not None)
    if review_count < 2:
        status = "INCOMPLETE"
    elif ordered_issues:
        status = "DISAGREEMENT"
    else:
        status = "READY_FOR_SEPARATE_QUALIFICATION_REVIEW"
    payload: dict[str, object] = {
        "schema_version": "2.0.0",
        "document_type": "sdc.creative-sample-real-asset-review-pair-check-v2",
        "profile": REVIEW_V2_PROFILE,
        "pack_id": pack.pack_id,
        "rights_evidence_bundle_id": evidence.bundle_id,
        "review_a_id": reviewer_a.review_id if reviewer_a is not None else None,
        "review_b_id": reviewer_b.review_id if reviewer_b is not None else None,
        "review_a_record_sha256": (
            reviewer_a.review_record_sha256 if reviewer_a is not None else None
        ),
        "review_b_record_sha256": (
            reviewer_b.review_record_sha256 if reviewer_b is not None else None
        ),
        "review_count": review_count,
        "evaluated_at": evaluated_at,
        "asset_count": 14,
        "issue_codes": ordered_issues,
        "status": status,
        "rights_manifest_created": False,
        "rights_qualification_performed": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetReviewPairCheckV2.model_validate(
        {
            "pair_check_id": stable_id("real_asset_review_pair_check_v2", payload),
            **payload,
        },
        strict=True,
    )


def load_real_asset_rights_evidence_bundle_v2(
    path: Path,
) -> CreativeSampleRealAssetRightsEvidenceBundleV2:
    try:
        return cast(
            CreativeSampleRealAssetRightsEvidenceBundleV2,
            _read_strict_json(path, CreativeSampleRealAssetRightsEvidenceBundleV2),
        )
    except RealAssetIntakeError as exc:
        raise RealAssetReviewV2Error(str(exc)) from exc


def load_real_asset_human_pack_review_v2(
    path: Path,
) -> CreativeSampleRealAssetHumanPackReviewV2:
    try:
        return cast(
            CreativeSampleRealAssetHumanPackReviewV2,
            _read_strict_json(path, CreativeSampleRealAssetHumanPackReviewV2),
        )
    except RealAssetIntakeError as exc:
        raise RealAssetReviewV2Error(str(exc)) from exc


def load_real_asset_review_pair_check_v2(
    path: Path,
) -> CreativeSampleRealAssetReviewPairCheckV2:
    try:
        return cast(
            CreativeSampleRealAssetReviewPairCheckV2,
            _read_strict_json(path, CreativeSampleRealAssetReviewPairCheckV2),
        )
    except RealAssetIntakeError as exc:
        raise RealAssetReviewV2Error(str(exc)) from exc


def write_new_real_asset_review_v2_document(path: Path, value: ReviewV2Document) -> Path:
    """Publish one canonical local contract using exclusive new-file creation."""

    validated: ReviewV2Document
    if isinstance(value, CreativeSampleRealAssetRightsEvidenceBundleV2):
        validated = _revalidate_evidence(value)
    elif isinstance(value, CreativeSampleRealAssetHumanPackReviewV2):
        validated = _revalidate_review(value)
    elif isinstance(value, CreativeSampleRealAssetReviewPairCheckV2):
        validated = _revalidate_model(
            value,
            CreativeSampleRealAssetReviewPairCheckV2,
            field="review PairCheck",
        )
    else:
        raise RealAssetReviewV2Error("only a top-level Review v2 document may be published")
    try:
        _write_new_document(path, validated)
    except RealAssetIntakeError as exc:
        raise RealAssetReviewV2Error(str(exc)) from exc
    return path.absolute()


__all__ = [
    "CreativeSampleRealAssetHumanPackReviewV2",
    "CreativeSampleRealAssetReviewPairCheckV2",
    "CreativeSampleRealAssetRightsEvidenceBundleV2",
    "RealAssetHumanFindingV2",
    "RealAssetReviewExceptionV2",
    "RealAssetReviewV2Error",
    "RealAssetRightsEvidenceBindingV2",
    "build_real_asset_human_findings_v2",
    "build_real_asset_human_pack_review_v2",
    "build_real_asset_rights_evidence_bundle_v2",
    "finalize_real_asset_review_pair_v2",
    "load_real_asset_human_pack_review_v2",
    "load_real_asset_review_pair_check_v2",
    "load_real_asset_rights_evidence_bundle_v2",
    "write_new_real_asset_review_v2_document",
]
