"""Pure Pack-level qualification contracts for synthetic/offline assessment.

This module consumes the exact Human Review v2 closure.  A positive result is scoped only to
asset intake: it does not create a rights manifest, authorize generation, or integrate with a
runtime, Provider, registry, database, ledger, or migration.  The API performs no I/O and never
reads a clock; every UTC second and retained-record digest is explicit caller input.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Literal
from unicodedata import normalize

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from sdc.compiler import stable_id
from sdc.real_asset_intake import CreativeSampleFrozenRealAssetPackManifest
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
    RealAssetReviewV2Error,
    finalize_real_asset_review_pair_v2,
)

QUALIFICATION_V2_PROFILE: Literal[
    "creative-sample-real-asset-qualification-assessment-v2"
] = "creative-sample-real-asset-qualification-assessment-v2"
QUALIFICATION_V2_POLICY_ID: Literal[
    "creative-sample-real-asset-qualification-policy"
] = "creative-sample-real-asset-qualification-policy"
QUALIFICATION_V2_POLICY_VERSION: Literal["2.0.0"] = "2.0.0"
QUALIFICATION_REQUEST_MAX_AGE_SECONDS = 86_400

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_UTC_SECONDS = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_JSON_LIMIT = 1_048_576
_POLICY_DIGEST_DOMAIN = b"sdc:creative-sample-real-asset-qualification-policy:v2\0"


def _canonical_payload(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_document(value: BaseModel) -> bytes:
    return (
        json.dumps(
            value.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


_QUALIFICATION_POLICY_PAYLOAD: dict[str, object] = {
    "policy_id": QUALIFICATION_V2_POLICY_ID,
    "policy_version": QUALIFICATION_V2_POLICY_VERSION,
    "positive_decision": "PASS_ASSET_INTAKE_ONLY",
    "qualification_scope": "ASSET_INTAKE_ONLY",
    "request_max_age_seconds": QUALIFICATION_REQUEST_MAX_AGE_SECONDS,
    "rules": (
        "EXACT_UPSTREAM_CANONICAL_CLOSURE",
        "PAIR_READY_WITHOUT_ISSUES",
        "EVIDENCE_VALID_AT_REQUEST_AND_DECISION",
        "PREPARER_REVIEWERS_QUALIFIER_DISTINCT",
        "RETAINED_RECORD_DIGESTS_NON_ALIASING",
        "NO_MANIFEST_NO_GENERATION_NO_AUTHORIZATION",
    ),
}
QUALIFICATION_V2_POLICY_DOCUMENT_SHA256: Literal[
    "f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031"
] = "f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031"
if (
    _sha256(_POLICY_DIGEST_DOMAIN + _canonical_payload(_QUALIFICATION_POLICY_PAYLOAD))
    != QUALIFICATION_V2_POLICY_DOCUMENT_SHA256
):
    raise RuntimeError("qualification v2 policy payload digest drifted")

type RealAssetQualificationDecisionV2 = Literal[
    "PASS_ASSET_INTAKE_ONLY",
    "REJECTED",
    "NEEDS_HUMAN_REVIEW",
]
type RealAssetQualificationIssueCodeV2 = Literal[
    "EVIDENCE_SCOPE_UNCLEAR",
    "POLICY_REQUIREMENT_NOT_MET",
    "QUALIFIER_REJECTED_ASSET_INTAKE",
    "OTHER_BLOCKING_ISSUE",
]

_QUALIFICATION_ISSUE_ORDER: tuple[RealAssetQualificationIssueCodeV2, ...] = (
    "EVIDENCE_SCOPE_UNCLEAR",
    "POLICY_REQUIREMENT_NOT_MET",
    "QUALIFIER_REJECTED_ASSET_INTAKE",
    "OTHER_BLOCKING_ISSUE",
)


class RealAssetQualificationV2Error(RuntimeError):
    """The pure qualification consumer failed closed."""


class _QualificationV2Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


def _utc_seconds(value: str, *, field: str) -> str:
    if __import__("re").fullmatch(_UTC_SECONDS, value) is None:
        raise ValueError(f"{field} must be canonical UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError(f"{field} must be canonical UTC seconds")
    return value


def _parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _format_utc(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _portable_text(value: str, *, field: str) -> str:
    if not value or len(value) > 1000:
        raise ValueError(f"{field} must contain 1..1000 characters")
    if value != value.strip() or value != normalize("NFC", value):
        raise ValueError(f"{field} must be trimmed NFC text")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field} must not contain control characters")
    return value


class CreativeSampleRealAssetQualificationRequestV2(_QualificationV2Model):
    """An exact, finite request for an independent asset-intake qualification decision."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-qualification-request-v2"
    ] = "sdc.creative-sample-real-asset-qualification-request-v2"
    profile: Literal[
        "creative-sample-real-asset-qualification-assessment-v2"
    ] = QUALIFICATION_V2_PROFILE
    request_id: str = Field(pattern=r"^real_asset_qualification_request_v2_[0-9a-f]{20}$")
    policy_id: Literal[
        "creative-sample-real-asset-qualification-policy"
    ] = QUALIFICATION_V2_POLICY_ID
    policy_version: Literal["2.0.0"] = QUALIFICATION_V2_POLICY_VERSION
    policy_document_sha256: Literal[
        "f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031"
    ] = QUALIFICATION_V2_POLICY_DOCUMENT_SHA256
    requested_at: str
    evaluated_at: str
    request_valid_until: str
    evidence_valid_until: str
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    pack_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    rights_evidence_bundle_id: str = Field(
        pattern=r"^real_asset_rights_evidence_v2_[0-9a-f]{20}$"
    )
    rights_evidence_bundle_sha256: str = Field(pattern=_LOWER_SHA256)
    evidence_retained_record_sha256: str = Field(pattern=_LOWER_SHA256)
    evidence_preparer_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    review_a_id: str = Field(pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$")
    review_a_contract_sha256: str = Field(pattern=_LOWER_SHA256)
    review_a_record_sha256: str = Field(pattern=_LOWER_SHA256)
    reviewer_a_retained_record_sha256: str = Field(pattern=_LOWER_SHA256)
    review_b_id: str = Field(pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$")
    review_b_contract_sha256: str = Field(pattern=_LOWER_SHA256)
    review_b_record_sha256: str = Field(pattern=_LOWER_SHA256)
    reviewer_b_retained_record_sha256: str = Field(pattern=_LOWER_SHA256)
    pair_check_id: str = Field(pattern=r"^real_asset_review_pair_check_v2_[0-9a-f]{20}$")
    pair_check_sha256: str = Field(pattern=_LOWER_SHA256)
    status: Literal["QUALIFICATION_REQUESTED"] = "QUALIFICATION_REQUESTED"
    rights_manifest_created: Literal[False] = False
    rights_qualification_performed: Literal[False] = False
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    eligible_for_real_generation: Literal[False] = False
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @field_validator("requested_at", "evaluated_at", "request_valid_until")
    @classmethod
    def validate_utc_seconds(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=info.field_name or "request timestamp")

    @field_validator("evidence_valid_until")
    @classmethod
    def validate_evidence_valid_until(cls, value: str) -> str:
        if value == "PERPETUAL":
            return value
        return _utc_seconds(value, field="evidence_valid_until")

    @model_validator(mode="after")
    def validate_request(self) -> CreativeSampleRealAssetQualificationRequestV2:
        if self.policy_document_sha256 != QUALIFICATION_V2_POLICY_DOCUMENT_SHA256:
            raise ValueError("qualification request must bind the built-in v2 policy document")
        evaluated = _parse_utc(self.evaluated_at)
        requested = _parse_utc(self.requested_at)
        if evaluated > requested:
            raise ValueError("qualification request cannot precede PairCheck evaluation")
        expected_until = requested + timedelta(seconds=QUALIFICATION_REQUEST_MAX_AGE_SECONDS)
        if self.evidence_valid_until != "PERPETUAL":
            evidence_until = _parse_utc(self.evidence_valid_until)
            if requested >= evidence_until:
                raise ValueError("qualification request cannot use expired rights evidence")
            expected_until = min(expected_until, evidence_until)
        if self.request_valid_until != _format_utc(expected_until):
            raise ValueError("qualification request validity must use the exact policy cap")

        retained = {
            self.evidence_retained_record_sha256,
            self.evidence_preparer_ref_sha256,
            self.reviewer_a_retained_record_sha256,
            self.reviewer_b_retained_record_sha256,
        }
        if len(retained) != 4:
            raise ValueError("evidence preparer and retained A/B records must be distinct")
        contracts = {
            self.pack_manifest_sha256,
            self.rights_evidence_bundle_sha256,
            self.review_a_contract_sha256,
            self.review_b_contract_sha256,
            self.pair_check_sha256,
            self.policy_document_sha256,
            self.review_a_record_sha256,
            self.review_b_record_sha256,
        }
        if len(contracts) != 8 or retained & contracts:
            raise ValueError("qualification request retained records must not alias contracts")
        expected_id = stable_id(
            "real_asset_qualification_request_v2",
            self.model_dump(mode="json", exclude={"request_id"}),
        )
        if self.request_id != expected_id:
            raise ValueError("qualification request ID must bind its complete canonical content")
        return self


class CreativeSampleRealAssetQualificationDecisionV2(_QualificationV2Model):
    """A scoped asset-intake qualification result with zero execution authority."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-qualification-decision-v2"
    ] = "sdc.creative-sample-real-asset-qualification-decision-v2"
    profile: Literal[
        "creative-sample-real-asset-qualification-assessment-v2"
    ] = QUALIFICATION_V2_PROFILE
    decision_id: str = Field(pattern=r"^real_asset_qualification_decision_v2_[0-9a-f]{20}$")
    request_id: str = Field(pattern=r"^real_asset_qualification_request_v2_[0-9a-f]{20}$")
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    policy_id: Literal[
        "creative-sample-real-asset-qualification-policy"
    ] = QUALIFICATION_V2_POLICY_ID
    policy_version: Literal["2.0.0"] = QUALIFICATION_V2_POLICY_VERSION
    policy_document_sha256: Literal[
        "f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031"
    ] = QUALIFICATION_V2_POLICY_DOCUMENT_SHA256
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    rights_evidence_bundle_id: str = Field(
        pattern=r"^real_asset_rights_evidence_v2_[0-9a-f]{20}$"
    )
    review_a_id: str = Field(pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$")
    review_b_id: str = Field(pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$")
    pair_check_id: str = Field(pattern=r"^real_asset_review_pair_check_v2_[0-9a-f]{20}$")
    requested_at: str
    evaluated_at: str
    request_valid_until: str
    evidence_retained_record_sha256: str = Field(pattern=_LOWER_SHA256)
    evidence_preparer_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    reviewer_a_retained_record_sha256: str = Field(pattern=_LOWER_SHA256)
    reviewer_b_retained_record_sha256: str = Field(pattern=_LOWER_SHA256)
    qualifier_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    qualifier_record_sha256: str = Field(pattern=_LOWER_SHA256)
    decision_at: str
    qualification_issue_codes: tuple[RealAssetQualificationIssueCodeV2, ...] = Field(
        default=(),
        max_length=4,
    )
    qualification_basis: str = Field(min_length=1, max_length=1000)
    decision: RealAssetQualificationDecisionV2
    qualification_scope: Literal["ASSET_INTAKE_ONLY"] = "ASSET_INTAKE_ONLY"
    eligible_for_separate_manifest_design_review: bool
    status: Literal["QUALIFICATION_COMPLETE"] = "QUALIFICATION_COMPLETE"
    rights_manifest_created: Literal[False] = False
    rights_qualification_performed: Literal[True] = True
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    eligible_for_real_generation: Literal[False] = False
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @field_validator("requested_at", "evaluated_at", "request_valid_until", "decision_at")
    @classmethod
    def validate_utc_seconds(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=info.field_name or "decision timestamp")

    @field_validator("qualification_basis")
    @classmethod
    def validate_qualification_basis(cls, value: str) -> str:
        return _portable_text(value, field="qualification basis")

    @field_validator("qualification_issue_codes")
    @classmethod
    def validate_qualification_issue_codes(
        cls,
        value: tuple[RealAssetQualificationIssueCodeV2, ...],
    ) -> tuple[RealAssetQualificationIssueCodeV2, ...]:
        if len(value) != len(set(value)):
            raise ValueError("qualification issue codes must be unique")
        if value != tuple(code for code in _QUALIFICATION_ISSUE_ORDER if code in value):
            raise ValueError("qualification issue codes must use canonical order")
        return value

    @model_validator(mode="after")
    def validate_decision(self) -> CreativeSampleRealAssetQualificationDecisionV2:
        if self.policy_document_sha256 != QUALIFICATION_V2_POLICY_DOCUMENT_SHA256:
            raise ValueError("qualification decision must bind the built-in v2 policy document")
        evaluated = _parse_utc(self.evaluated_at)
        requested = _parse_utc(self.requested_at)
        decided = _parse_utc(self.decision_at)
        valid_until = _parse_utc(self.request_valid_until)
        if evaluated > requested or requested > decided:
            raise ValueError("qualification decision timestamps must preserve causal order")
        if decided >= valid_until:
            raise ValueError("qualification decision must precede the exclusive request expiry")
        retained = {
            self.evidence_retained_record_sha256,
            self.evidence_preparer_ref_sha256,
            self.reviewer_a_retained_record_sha256,
            self.reviewer_b_retained_record_sha256,
            self.qualifier_ref_sha256,
            self.qualifier_record_sha256,
        }
        if len(retained) != 6:
            raise ValueError("all retained and four-party identity records must be distinct")
        if self.request_sha256 in retained or self.policy_document_sha256 in retained:
            raise ValueError("qualifier records must not alias the request or policy contract")
        positive = self.decision == "PASS_ASSET_INTAKE_ONLY"
        if positive == bool(self.qualification_issue_codes):
            raise ValueError(
                "positive decisions require no issue; negative decisions require an issue"
            )
        rejected_code = "QUALIFIER_REJECTED_ASSET_INTAKE"
        if self.decision == "REJECTED" and rejected_code not in self.qualification_issue_codes:
            raise ValueError("rejected decisions require the qualifier rejection issue code")
        if (
            self.decision == "NEEDS_HUMAN_REVIEW"
            and rejected_code in self.qualification_issue_codes
        ):
            raise ValueError("human-review decisions cannot contain the qualifier rejection code")
        if self.eligible_for_separate_manifest_design_review is not positive:
            raise ValueError(
                "manifest design eligibility must derive only from the scoped decision"
            )
        expected_id = stable_id(
            "real_asset_qualification_decision_v2",
            self.model_dump(mode="json", exclude={"decision_id"}),
        )
        if self.decision_id != expected_id:
            raise ValueError("qualification decision ID must bind its complete canonical content")
        return self


def _revalidate[ModelT: BaseModel](value: ModelT, model: type[ModelT], *, field: str) -> ModelT:
    try:
        return model.model_validate(value.model_dump(mode="python"), strict=True)
    except ValidationError as exc:
        raise RealAssetQualificationV2Error(f"{field} violates its strict contract") from exc


def _validate_sha256(value: str, *, field: str) -> str:
    if __import__("re").fullmatch(_LOWER_SHA256, value) is None:
        raise RealAssetQualificationV2Error(f"{field} must be a lowercase SHA-256")
    return value


def _revalidate_upstream(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
) -> tuple[
    CreativeSampleFrozenRealAssetPackManifest,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
]:
    pack = _revalidate(pack, CreativeSampleFrozenRealAssetPackManifest, field="frozen Pack")
    evidence = _revalidate(
        evidence,
        CreativeSampleRealAssetRightsEvidenceBundleV2,
        field="Evidence Bundle",
    )
    reviewer_a = _revalidate(
        reviewer_a,
        CreativeSampleRealAssetHumanPackReviewV2,
        field="Reviewer A contract",
    )
    reviewer_b = _revalidate(
        reviewer_b,
        CreativeSampleRealAssetHumanPackReviewV2,
        field="Reviewer B contract",
    )
    pair_check = _revalidate(
        pair_check,
        CreativeSampleRealAssetReviewPairCheckV2,
        field="PairCheck contract",
    )
    try:
        rebuilt_pair = finalize_real_asset_review_pair_v2(
            pack=pack,
            evidence=evidence,
            reviewer_a=reviewer_a,
            reviewer_b=reviewer_b,
            evaluated_at=pair_check.evaluated_at,
        )
    except (RealAssetReviewV2Error, ValidationError, ValueError) as exc:
        raise RealAssetQualificationV2Error("upstream Review v2 closure failed") from exc
    if rebuilt_pair != pair_check:
        raise RealAssetQualificationV2Error("PairCheck drifted from an exact deterministic rebuild")
    if (
        pair_check.status != "READY_FOR_SEPARATE_QUALIFICATION_REVIEW"
        or pair_check.issue_codes
    ):
        raise RealAssetQualificationV2Error("PairCheck is not issue-free and ready")
    return pack, evidence, reviewer_a, reviewer_b, pair_check


def _reserved_upstream_digests(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
) -> set[str]:
    return {
        _sha256(_canonical_document(pack)),
        _sha256(_canonical_document(evidence)),
        _sha256(_canonical_document(reviewer_a)),
        _sha256(_canonical_document(reviewer_b)),
        _sha256(_canonical_document(pair_check)),
        evidence.evidence_record_sha256,
        reviewer_a.reviewer_ref_sha256,
        reviewer_b.reviewer_ref_sha256,
        reviewer_a.review_record_sha256,
        reviewer_b.review_record_sha256,
        QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
        *(descriptor.sha256 for descriptor in pack.objects),
        *(descriptor.provenance_record_sha256 for descriptor in pack.objects),
        *(descriptor.technical_record_sha256 for descriptor in pack.objects),
    }


def build_real_asset_qualification_request_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    evidence_preparer_ref_sha256: str,
    requested_at: str,
) -> CreativeSampleRealAssetQualificationRequestV2:
    """Build a finite request from an exact issue-free v2 closure; no qualification occurs."""

    pack, evidence, reviewer_a, reviewer_b, pair_check = _revalidate_upstream(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
    )
    requested_at = _utc_seconds(requested_at, field="requested_at")
    evidence_preparer_ref_sha256 = _validate_sha256(
        evidence_preparer_ref_sha256,
        field="evidence_preparer_ref_sha256",
    )
    if _parse_utc(pair_check.evaluated_at) > _parse_utc(requested_at):
        raise RealAssetQualificationV2Error("request is in the past relative to PairCheck")
    if evidence.valid_until != "PERPETUAL" and _parse_utc(requested_at) >= _parse_utc(
        evidence.valid_until
    ):
        raise RealAssetQualificationV2Error("request uses expired rights evidence")

    retained = {
        evidence.evidence_record_sha256,
        evidence_preparer_ref_sha256,
        reviewer_a.reviewer_ref_sha256,
        reviewer_b.reviewer_ref_sha256,
    }
    if len(retained) != 4:
        raise RealAssetQualificationV2Error(
            "evidence preparer and A/B retained records must be distinct"
        )
    if evidence_preparer_ref_sha256 in _reserved_upstream_digests(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
    ):
        raise RealAssetQualificationV2Error("evidence preparer reference aliases an input record")

    request_deadline = _parse_utc(requested_at) + timedelta(
        seconds=QUALIFICATION_REQUEST_MAX_AGE_SECONDS
    )
    if evidence.valid_until != "PERPETUAL":
        request_deadline = min(request_deadline, _parse_utc(evidence.valid_until))
    payload: dict[str, object] = {
        "schema_version": "2.0.0",
        "document_type": "sdc.creative-sample-real-asset-qualification-request-v2",
        "profile": QUALIFICATION_V2_PROFILE,
        "policy_id": QUALIFICATION_V2_POLICY_ID,
        "policy_version": QUALIFICATION_V2_POLICY_VERSION,
        "policy_document_sha256": QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
        "requested_at": requested_at,
        "evaluated_at": pair_check.evaluated_at,
        "request_valid_until": _format_utc(request_deadline),
        "evidence_valid_until": evidence.valid_until,
        "pack_id": pack.pack_id,
        "pack_manifest_sha256": _sha256(_canonical_document(pack)),
        "rights_evidence_bundle_id": evidence.bundle_id,
        "rights_evidence_bundle_sha256": _sha256(_canonical_document(evidence)),
        "evidence_retained_record_sha256": evidence.evidence_record_sha256,
        "evidence_preparer_ref_sha256": evidence_preparer_ref_sha256,
        "review_a_id": reviewer_a.review_id,
        "review_a_contract_sha256": _sha256(_canonical_document(reviewer_a)),
        "review_a_record_sha256": reviewer_a.review_record_sha256,
        "reviewer_a_retained_record_sha256": reviewer_a.reviewer_ref_sha256,
        "review_b_id": reviewer_b.review_id,
        "review_b_contract_sha256": _sha256(_canonical_document(reviewer_b)),
        "review_b_record_sha256": reviewer_b.review_record_sha256,
        "reviewer_b_retained_record_sha256": reviewer_b.reviewer_ref_sha256,
        "pair_check_id": pair_check.pair_check_id,
        "pair_check_sha256": _sha256(_canonical_document(pair_check)),
        "status": "QUALIFICATION_REQUESTED",
        "rights_manifest_created": False,
        "rights_qualification_performed": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetQualificationRequestV2.model_validate(
        {
            "request_id": stable_id("real_asset_qualification_request_v2", payload),
            **payload,
        },
        strict=True,
    )


def build_real_asset_qualification_decision_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    request: CreativeSampleRealAssetQualificationRequestV2,
    qualifier_ref_sha256: str,
    qualifier_record_sha256: str,
    decision_at: str,
    qualification_issue_codes: tuple[RealAssetQualificationIssueCodeV2, ...],
    qualification_basis: str,
    decision: RealAssetQualificationDecisionV2,
) -> CreativeSampleRealAssetQualificationDecisionV2:
    """Record an explicit scoped qualification decision; it never creates a manifest."""

    pack, evidence, reviewer_a, reviewer_b, pair_check = _revalidate_upstream(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
    )
    request = _revalidate(
        request,
        CreativeSampleRealAssetQualificationRequestV2,
        field="qualification request",
    )
    rebuilt_request = build_real_asset_qualification_request_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        evidence_preparer_ref_sha256=request.evidence_preparer_ref_sha256,
        requested_at=request.requested_at,
    )
    if rebuilt_request != request:
        raise RealAssetQualificationV2Error("qualification request drifted from exact inputs")

    qualifier_ref_sha256 = _validate_sha256(
        qualifier_ref_sha256,
        field="qualifier_ref_sha256",
    )
    qualifier_record_sha256 = _validate_sha256(
        qualifier_record_sha256,
        field="qualifier_record_sha256",
    )
    decision_at = _utc_seconds(decision_at, field="decision_at")
    if _parse_utc(decision_at) < _parse_utc(request.requested_at):
        raise RealAssetQualificationV2Error("qualification decision predates its request")
    if _parse_utc(decision_at) >= _parse_utc(request.request_valid_until):
        raise RealAssetQualificationV2Error("qualification request expired before decision")
    if decision == "PASS_ASSET_INTAKE_ONLY" and evidence.valid_until != "PERPETUAL":
        if _parse_utc(decision_at) >= _parse_utc(evidence.valid_until):
            raise RealAssetQualificationV2Error("positive decision cannot use expired evidence")

    all_retained = {
        evidence.evidence_record_sha256,
        request.evidence_preparer_ref_sha256,
        reviewer_a.reviewer_ref_sha256,
        reviewer_b.reviewer_ref_sha256,
        qualifier_ref_sha256,
        qualifier_record_sha256,
    }
    if len(all_retained) != 6:
        raise RealAssetQualificationV2Error(
            "evidence, preparer, A/B, qualifier identity and qualifier record must be distinct"
        )
    reserved = _reserved_upstream_digests(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
    ) | {_sha256(_canonical_document(request))}
    if qualifier_ref_sha256 in reserved or qualifier_record_sha256 in reserved:
        raise RealAssetQualificationV2Error("qualifier inputs alias an upstream contract or record")

    request_sha256 = _sha256(_canonical_document(request))
    payload: dict[str, object] = {
        "schema_version": "2.0.0",
        "document_type": "sdc.creative-sample-real-asset-qualification-decision-v2",
        "profile": QUALIFICATION_V2_PROFILE,
        "request_id": request.request_id,
        "request_sha256": request_sha256,
        "policy_id": request.policy_id,
        "policy_version": request.policy_version,
        "policy_document_sha256": request.policy_document_sha256,
        "pack_id": request.pack_id,
        "rights_evidence_bundle_id": request.rights_evidence_bundle_id,
        "review_a_id": request.review_a_id,
        "review_b_id": request.review_b_id,
        "pair_check_id": request.pair_check_id,
        "requested_at": request.requested_at,
        "evaluated_at": request.evaluated_at,
        "request_valid_until": request.request_valid_until,
        "evidence_retained_record_sha256": request.evidence_retained_record_sha256,
        "evidence_preparer_ref_sha256": request.evidence_preparer_ref_sha256,
        "reviewer_a_retained_record_sha256": request.reviewer_a_retained_record_sha256,
        "reviewer_b_retained_record_sha256": request.reviewer_b_retained_record_sha256,
        "qualifier_ref_sha256": qualifier_ref_sha256,
        "qualifier_record_sha256": qualifier_record_sha256,
        "decision_at": decision_at,
        "qualification_issue_codes": qualification_issue_codes,
        "qualification_basis": qualification_basis,
        "decision": decision,
        "qualification_scope": "ASSET_INTAKE_ONLY",
        "eligible_for_separate_manifest_design_review": decision
        == "PASS_ASSET_INTAKE_ONLY",
        "status": "QUALIFICATION_COMPLETE",
        "rights_manifest_created": False,
        "rights_qualification_performed": True,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetQualificationDecisionV2.model_validate(
        {
            "decision_id": stable_id("real_asset_qualification_decision_v2", payload),
            **payload,
        },
        strict=True,
    )


def verify_real_asset_qualification_closure_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    request: CreativeSampleRealAssetQualificationRequestV2,
    decision: CreativeSampleRealAssetQualificationDecisionV2,
) -> CreativeSampleRealAssetQualificationDecisionV2:
    """Rebuild the complete pure closure and return the exact verified decision."""

    decision = _revalidate(
        decision,
        CreativeSampleRealAssetQualificationDecisionV2,
        field="qualification decision",
    )
    rebuilt = build_real_asset_qualification_decision_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
        qualifier_ref_sha256=decision.qualifier_ref_sha256,
        qualifier_record_sha256=decision.qualifier_record_sha256,
        decision_at=decision.decision_at,
        qualification_issue_codes=decision.qualification_issue_codes,
        qualification_basis=decision.qualification_basis,
        decision=decision.decision,
    )
    if rebuilt != decision:
        raise RealAssetQualificationV2Error("qualification decision drifted from exact inputs")
    return decision


def _reject_json_constant(value: str) -> None:
    raise RealAssetQualificationV2Error(f"non-finite JSON number is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RealAssetQualificationV2Error(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _parse_strict_json[ModelT: BaseModel](raw: bytes, model: type[ModelT]) -> ModelT:
    if type(raw) is not bytes or not raw or len(raw) > _JSON_LIMIT:
        raise RealAssetQualificationV2Error("qualification JSON must be bounded non-empty bytes")
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RealAssetQualificationV2Error("qualification JSON is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RealAssetQualificationV2Error("qualification JSON must contain one object")
    try:
        return model.model_validate_json(raw, strict=True)
    except ValidationError as exc:
        raise RealAssetQualificationV2Error(
            "qualification JSON violates its strict contract"
        ) from exc


def parse_real_asset_qualification_request_v2_json(
    raw: bytes,
) -> CreativeSampleRealAssetQualificationRequestV2:
    """Parse one in-memory request while rejecting duplicates and unknown fields."""

    return _parse_strict_json(raw, CreativeSampleRealAssetQualificationRequestV2)


def parse_real_asset_qualification_decision_v2_json(
    raw: bytes,
) -> CreativeSampleRealAssetQualificationDecisionV2:
    """Parse one in-memory decision while rejecting duplicates and unknown fields."""

    return _parse_strict_json(raw, CreativeSampleRealAssetQualificationDecisionV2)


__all__ = [
    "QUALIFICATION_REQUEST_MAX_AGE_SECONDS",
    "QUALIFICATION_V2_POLICY_DOCUMENT_SHA256",
    "QUALIFICATION_V2_POLICY_ID",
    "QUALIFICATION_V2_POLICY_VERSION",
    "QUALIFICATION_V2_PROFILE",
    "CreativeSampleRealAssetQualificationDecisionV2",
    "CreativeSampleRealAssetQualificationRequestV2",
    "RealAssetQualificationDecisionV2",
    "RealAssetQualificationIssueCodeV2",
    "RealAssetQualificationV2Error",
    "build_real_asset_qualification_decision_v2",
    "build_real_asset_qualification_request_v2",
    "parse_real_asset_qualification_decision_v2_json",
    "parse_real_asset_qualification_request_v2_json",
    "verify_real_asset_qualification_closure_v2",
]
