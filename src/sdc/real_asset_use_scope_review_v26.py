"""Pure small-team Use Scope Review v2.6 with one record and three modules.

Request, Instruction, and Decision remain distinct immutable contracts even though the final
artifact is one ReviewRecord.  Identity-reference digests provide procedural evidence only;
they are not cryptographic proof that two natural people acted.  A trusted-local adapter must
later reopen two explicitly selected identity-reference files if stronger assurance is needed.

Nothing in this module grants Provider, generation, runtime, posting, cost, or publication
authority.  The module performs no file, network, or wall-clock I/O.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from sdc.compiler import stable_id
from sdc.real_asset_intake import CreativeSampleFrozenRealAssetPackManifest
from sdc.real_asset_qualification_decision_instruction_v22 import (
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
)
from sdc.real_asset_qualification_v2 import (
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationRequestV2,
)
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
)
from sdc.real_asset_rights_manifest_v24 import CreativeSampleRealAssetRightsManifestV2
from sdc.real_asset_use_plan_v26 import (
    CreativeSampleRealAssetUsePlanV1,
    verify_real_asset_use_plan_closure_v1,
)

USE_SCOPE_REVIEW_V1_PROFILE: Literal[
    "creative-sample-real-asset-use-scope-review-v2.6"
] = "creative-sample-real-asset-use-scope-review-v2.6"
USE_SCOPE_REVIEW_V1_POLICY_ID: Literal[
    "creative-sample-real-asset-use-scope-review-policy"
] = "creative-sample-real-asset-use-scope-review-policy"
USE_SCOPE_REVIEW_V1_POLICY_VERSION: Literal["2.6.0"] = "2.6.0"
USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256: Literal[
    "0a2745b52d92335e8894b79ee7ff5588dea79d5bbfd021489c45c3bec5f7a969"
] = "0a2745b52d92335e8894b79ee7ff5588dea79d5bbfd021489c45c3bec5f7a969"

REQUEST_VALIDITY_SECONDS = 86_400
REVIEW_VALIDITY_SECONDS = 2_592_000

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_UTC_SECONDS = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_JSON_LIMIT = 2_097_152
_POLICY_DOMAIN = b"sdc:creative-sample-real-asset-use-scope-review-policy:v2.6\0"

UseScopeGateV1 = Literal[
    "COPYRIGHT_USE_SCOPE",
    "LIKENESS_USE_SCOPE",
    "PRIVACY_USE_SCOPE",
    "TERRITORY_USE_SCOPE",
    "CONTENT_ROLE_USE_SCOPE",
    "OFFLINE_ONLY_RESTRICTIONS",
]
UseScopeDispositionV1 = Literal[
    "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY",
    "NEEDS_REVISION",
    "REJECTED",
]
UseScopeIssueCodeV1 = Literal[
    "COPYRIGHT_USE_SCOPE_NOT_CONFIRMED",
    "LIKENESS_USE_SCOPE_NOT_CONFIRMED",
    "PRIVACY_USE_SCOPE_NOT_CONFIRMED",
    "TERRITORY_USE_SCOPE_NOT_CONFIRMED",
    "CONTENT_ROLE_USE_SCOPE_NOT_CONFIRMED",
    "OFFLINE_ONLY_RESTRICTIONS_NOT_CONFIRMED",
    "CHECKER_REJECTED_USE_SCOPE",
]

_GATE_ORDER: tuple[UseScopeGateV1, ...] = (
    "COPYRIGHT_USE_SCOPE",
    "LIKENESS_USE_SCOPE",
    "PRIVACY_USE_SCOPE",
    "TERRITORY_USE_SCOPE",
    "CONTENT_ROLE_USE_SCOPE",
    "OFFLINE_ONLY_RESTRICTIONS",
)
_GATE_ISSUES: dict[UseScopeGateV1, UseScopeIssueCodeV1] = {
    "COPYRIGHT_USE_SCOPE": "COPYRIGHT_USE_SCOPE_NOT_CONFIRMED",
    "LIKENESS_USE_SCOPE": "LIKENESS_USE_SCOPE_NOT_CONFIRMED",
    "PRIVACY_USE_SCOPE": "PRIVACY_USE_SCOPE_NOT_CONFIRMED",
    "TERRITORY_USE_SCOPE": "TERRITORY_USE_SCOPE_NOT_CONFIRMED",
    "CONTENT_ROLE_USE_SCOPE": "CONTENT_ROLE_USE_SCOPE_NOT_CONFIRMED",
    "OFFLINE_ONLY_RESTRICTIONS": "OFFLINE_ONLY_RESTRICTIONS_NOT_CONFIRMED",
}
_ISSUE_ORDER: tuple[UseScopeIssueCodeV1, ...] = (
    *(_GATE_ISSUES[gate] for gate in _GATE_ORDER),
    "CHECKER_REJECTED_USE_SCOPE",
)


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


_REVIEW_POLICY_PAYLOAD: dict[str, object] = {
    "gate_order": _GATE_ORDER,
    "policy_id": USE_SCOPE_REVIEW_V1_POLICY_ID,
    "policy_version": USE_SCOPE_REVIEW_V1_POLICY_VERSION,
    "request_validity_seconds": REQUEST_VALIDITY_SECONDS,
    "requested_outcome_scope": "PROVIDER_PROPOSAL_DESIGN_ONLY",
    "review_scope": "OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY",
    "review_validity_seconds": REVIEW_VALIDITY_SECONDS,
    "rules": (
        "EXACT_USE_PLAN_AND_MANIFEST_CLOSURE",
        "MAKER_CHECKER_PROCEDURAL_SEPARATION",
        "REQUEST_WINDOW_EXCLUSIVE",
        "EVIDENCE_VALID_AT_REQUEST_AND_CHECK",
        "FIXED_GATE_ORDER",
        "PASS_REQUIRES_ALL_GATES_APPROVED",
        "NEGATIVE_REQUIRES_FAILED_GATE",
        "REJECTION_REQUIRES_EXPLICIT_DISPOSITION",
        "PROVIDER_PROPOSAL_ELIGIBILITY_ONLY",
        "NO_REMOTE_PROCESSING_RETENTION_TRAINING_PUBLICATION",
        "NO_PROVIDER_APPROVAL_GENERATION_EXECUTION_AUTHORIZATION",
    ),
}
if _sha256(_POLICY_DOMAIN + _canonical_payload(_REVIEW_POLICY_PAYLOAD)) != (
    USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256
):
    raise RuntimeError("Use Scope Review v1 policy payload digest drifted")


class RealAssetUseScopeReviewV26Error(RuntimeError):
    """The pure Use Scope Review v2.6 consumer failed closed."""


def _utc_seconds(value: str, *, field: str) -> str:
    if re.fullmatch(_UTC_SECONDS, value) is None:
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
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _portable_text(value: str, *, field: str, maximum: int = 2000) -> str:
    if not value or len(value) > maximum or value != value.strip():
        raise ValueError(f"{field} must contain 1..{maximum} trimmed characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field} must not contain control characters")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError(f"{field} must use NFC-normalized Unicode")
    return value


class _ReviewModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class _ZeroAuthorityReviewModel(_ReviewModel):
    rights_qualification_performed: Literal[True] = True
    rights_manifest_created: Literal[True] = True
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    eligible_for_separate_provider_approval: Literal[False] = False
    provider_approval_granted: Literal[False] = False
    eligible_for_real_generation: Literal[False] = False
    generation_authorized: Literal[False] = False
    execution_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    remote_processing_allowed: Literal[False] = False
    retention_allowed: Literal[False] = False
    training_allowed: Literal[False] = False
    publication_allowed: Literal[False] = False
    authorized_attempts: Literal[0] = 0
    authorized_cost_cny: Literal[0] = 0
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @model_validator(mode="before")
    @classmethod
    def validate_exact_scalar_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        for field in (
            "rights_qualification_performed",
            "rights_manifest_created",
            "eligible_for_separate_provider_approval",
            "provider_approval_granted",
            "eligible_for_real_generation",
            "generation_authorized",
            "execution_authorized",
            "publication_authorized",
            "remote_processing_allowed",
            "retention_allowed",
            "training_allowed",
            "publication_allowed",
            "use_scope_review_performed",
            "eligible_for_separate_provider_proposal",
        ):
            if field in value and type(value[field]) is not bool:
                raise ValueError(f"{field} must be an exact JSON boolean")
        for field in (
            "authorized_attempts",
            "authorized_cost_cny",
            "posts_allowed",
            "provider_requests",
        ):
            if field in value and (type(value[field]) is not int or value[field] != 0):
                raise ValueError(f"{field} must be the exact JSON integer zero")
        return value


class UseScopeGateResultV1(_ReviewModel):
    gate: UseScopeGateV1
    approved: bool
    note: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def validate_approved_type(cls, value: object) -> object:
        if isinstance(value, dict) and "approved" in value and type(value["approved"]) is not bool:
            raise ValueError("gate approved must be an exact JSON boolean")
        return value

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _portable_text(value, field="gate note", maximum=1000)

    @model_validator(mode="after")
    def validate_gate(self) -> UseScopeGateResultV1:
        if self.approved and self.note is not None:
            raise ValueError("an approved gate must not contain a failure note")
        if not self.approved and self.note is None:
            raise ValueError("a failed gate requires a Checker-authored note")
        return self


class CreativeSampleRealAssetUseScopeReviewRequestV1(_ZeroAuthorityReviewModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-use-scope-review-request-v1"
    ] = "sdc.creative-sample-real-asset-use-scope-review-request-v1"
    profile: Literal[
        "creative-sample-real-asset-use-scope-review-v2.6"
    ] = USE_SCOPE_REVIEW_V1_PROFILE
    request_id: str = Field(pattern=r"^real_asset_use_scope_request_v1_[0-9a-f]{20}$")
    review_policy_id: Literal[
        "creative-sample-real-asset-use-scope-review-policy"
    ] = USE_SCOPE_REVIEW_V1_POLICY_ID
    review_policy_version: Literal["2.6.0"] = USE_SCOPE_REVIEW_V1_POLICY_VERSION
    review_policy_document_sha256: Literal[
        "0a2745b52d92335e8894b79ee7ff5588dea79d5bbfd021489c45c3bec5f7a969"
    ] = USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256
    use_plan_id: str = Field(pattern=r"^real_asset_use_plan_v1_[0-9a-f]{20}$")
    use_plan_sha256: str = Field(pattern=_LOWER_SHA256)
    rights_manifest_id: str = Field(
        pattern=r"^real_asset_rights_manifest_v2_[0-9a-f]{20}$"
    )
    rights_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    rights_manifest_at: str
    evidence_valid_until: str
    maker_role: Literal["MAKER"] = "MAKER"
    maker_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    requested_at: str
    request_valid_until: str
    request_basis: str = Field(min_length=1, max_length=2000)
    review_scope: Literal[
        "OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY"
    ] = "OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY"
    requested_outcome_scope: Literal[
        "PROVIDER_PROPOSAL_DESIGN_ONLY"
    ] = "PROVIDER_PROPOSAL_DESIGN_ONLY"
    use_scope_review_performed: Literal[False] = False
    eligible_for_separate_provider_proposal: Literal[False] = False
    status: Literal["USE_SCOPE_REVIEW_REQUESTED"] = "USE_SCOPE_REVIEW_REQUESTED"

    @field_validator("rights_manifest_at", "requested_at", "request_valid_until")
    @classmethod
    def validate_times(cls, value: str, info: object) -> str:
        name = getattr(info, "field_name", None) or "review timestamp"
        return _utc_seconds(value, field=name)

    @field_validator("evidence_valid_until")
    @classmethod
    def validate_evidence_time(cls, value: str) -> str:
        if value == "PERPETUAL":
            return value
        return _utc_seconds(value, field="evidence_valid_until")

    @field_validator("request_basis")
    @classmethod
    def validate_basis(cls, value: str) -> str:
        return _portable_text(value, field="Maker request basis")

    @model_validator(mode="after")
    def validate_request(self) -> CreativeSampleRealAssetUseScopeReviewRequestV1:
        requested = _parse_utc(self.requested_at)
        if requested < _parse_utc(self.rights_manifest_at):
            raise ValueError("Use Scope request cannot predate the Rights Manifest")
        if _parse_utc(self.request_valid_until) != requested + timedelta(
            seconds=REQUEST_VALIDITY_SECONDS
        ):
            raise ValueError("Use Scope request must use the fixed exclusive 24-hour window")
        if self.evidence_valid_until != "PERPETUAL" and requested >= _parse_utc(
            self.evidence_valid_until
        ):
            raise ValueError("rights evidence is not valid at the request boundary")
        if self.maker_identity_ref_sha256 in {
            self.use_plan_sha256,
            self.rights_manifest_sha256,
            self.review_policy_document_sha256,
        }:
            raise ValueError("Maker reference must not alias a content or policy digest")
        expected = stable_id(
            "real_asset_use_scope_request_v1",
            self.model_dump(mode="json", exclude={"request_id"}),
        )
        if self.request_id != expected:
            raise ValueError("Use Scope request ID must bind its complete canonical content")
        return self


class CreativeSampleRealAssetUseScopeReviewInstructionV1(_ZeroAuthorityReviewModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-use-scope-review-instruction-v1"
    ] = "sdc.creative-sample-real-asset-use-scope-review-instruction-v1"
    profile: Literal[
        "creative-sample-real-asset-use-scope-review-v2.6"
    ] = USE_SCOPE_REVIEW_V1_PROFILE
    instruction_id: str = Field(pattern=r"^real_asset_use_scope_instruction_v1_[0-9a-f]{20}$")
    review_policy_id: Literal[
        "creative-sample-real-asset-use-scope-review-policy"
    ] = USE_SCOPE_REVIEW_V1_POLICY_ID
    review_policy_version: Literal["2.6.0"] = USE_SCOPE_REVIEW_V1_POLICY_VERSION
    review_policy_document_sha256: Literal[
        "0a2745b52d92335e8894b79ee7ff5588dea79d5bbfd021489c45c3bec5f7a969"
    ] = USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256
    request_id: str = Field(pattern=r"^real_asset_use_scope_request_v1_[0-9a-f]{20}$")
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    use_plan_id: str = Field(pattern=r"^real_asset_use_plan_v1_[0-9a-f]{20}$")
    use_plan_sha256: str = Field(pattern=_LOWER_SHA256)
    rights_manifest_id: str = Field(
        pattern=r"^real_asset_rights_manifest_v2_[0-9a-f]{20}$"
    )
    rights_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    maker_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    checker_role: Literal["CHECKER"] = "CHECKER"
    checker_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    requested_at: str
    request_valid_until: str
    evidence_valid_until: str
    evaluated_at: str
    review_scope: Literal[
        "OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY"
    ] = "OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY"
    requested_outcome_scope: Literal[
        "PROVIDER_PROPOSAL_DESIGN_ONLY"
    ] = "PROVIDER_PROPOSAL_DESIGN_ONLY"
    gate_results: tuple[UseScopeGateResultV1, ...] = Field(min_length=6, max_length=6)
    disposition: UseScopeDispositionV1
    checker_basis: str = Field(min_length=1, max_length=2000)
    use_scope_review_performed: Literal[False] = False
    eligible_for_separate_provider_proposal: Literal[False] = False
    status: Literal["USE_SCOPE_CHECK_RECORDED"] = "USE_SCOPE_CHECK_RECORDED"

    @field_validator("requested_at", "request_valid_until", "evaluated_at")
    @classmethod
    def validate_times(cls, value: str, info: object) -> str:
        name = getattr(info, "field_name", None) or "review timestamp"
        return _utc_seconds(value, field=name)

    @field_validator("evidence_valid_until")
    @classmethod
    def validate_evidence_time(cls, value: str) -> str:
        if value == "PERPETUAL":
            return value
        return _utc_seconds(value, field="evidence_valid_until")

    @field_validator("checker_basis")
    @classmethod
    def validate_basis(cls, value: str) -> str:
        return _portable_text(value, field="Checker basis")

    @model_validator(mode="after")
    def validate_instruction(self) -> CreativeSampleRealAssetUseScopeReviewInstructionV1:
        if tuple(item.gate for item in self.gate_results) != _GATE_ORDER:
            raise ValueError("Use Scope gates must use the fixed policy order")
        approvals = tuple(item.approved for item in self.gate_results)
        if self.disposition == "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY" and not all(approvals):
            raise ValueError("a positive disposition requires every Use Scope gate to pass")
        if self.disposition != "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY" and all(approvals):
            raise ValueError("a negative disposition requires at least one failed gate")
        if self.maker_identity_ref_sha256 == self.checker_identity_ref_sha256:
            raise ValueError("Maker and Checker references must be procedurally distinct")
        requested = _parse_utc(self.requested_at)
        if _parse_utc(self.request_valid_until) != requested + timedelta(
            seconds=REQUEST_VALIDITY_SECONDS
        ):
            raise ValueError("Checker instruction must retain the fixed request window")
        checked = _parse_utc(self.evaluated_at)
        if checked < requested or checked >= _parse_utc(self.request_valid_until):
            raise ValueError("Checker instruction is outside the exclusive request window")
        if self.evidence_valid_until != "PERPETUAL" and checked >= _parse_utc(
            self.evidence_valid_until
        ):
            raise ValueError("rights evidence is not valid at the Checker boundary")
        if self.checker_identity_ref_sha256 in {
            self.request_sha256,
            self.use_plan_sha256,
            self.rights_manifest_sha256,
            self.review_policy_document_sha256,
        }:
            raise ValueError("Checker reference must not alias a content or policy digest")
        expected = stable_id(
            "real_asset_use_scope_instruction_v1",
            self.model_dump(mode="json", exclude={"instruction_id"}),
        )
        if self.instruction_id != expected:
            raise ValueError("Use Scope instruction ID must bind its complete canonical content")
        return self


class CreativeSampleRealAssetUseScopeReviewDecisionV1(_ZeroAuthorityReviewModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-use-scope-review-decision-v1"
    ] = "sdc.creative-sample-real-asset-use-scope-review-decision-v1"
    profile: Literal[
        "creative-sample-real-asset-use-scope-review-v2.6"
    ] = USE_SCOPE_REVIEW_V1_PROFILE
    decision_id: str = Field(pattern=r"^real_asset_use_scope_decision_v1_[0-9a-f]{20}$")
    review_policy_id: Literal[
        "creative-sample-real-asset-use-scope-review-policy"
    ] = USE_SCOPE_REVIEW_V1_POLICY_ID
    review_policy_version: Literal["2.6.0"] = USE_SCOPE_REVIEW_V1_POLICY_VERSION
    review_policy_document_sha256: Literal[
        "0a2745b52d92335e8894b79ee7ff5588dea79d5bbfd021489c45c3bec5f7a969"
    ] = USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256
    request_id: str = Field(pattern=r"^real_asset_use_scope_request_v1_[0-9a-f]{20}$")
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    instruction_id: str = Field(pattern=r"^real_asset_use_scope_instruction_v1_[0-9a-f]{20}$")
    instruction_sha256: str = Field(pattern=_LOWER_SHA256)
    use_plan_id: str = Field(pattern=r"^real_asset_use_plan_v1_[0-9a-f]{20}$")
    use_plan_sha256: str = Field(pattern=_LOWER_SHA256)
    rights_manifest_id: str = Field(
        pattern=r"^real_asset_rights_manifest_v2_[0-9a-f]{20}$"
    )
    rights_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    maker_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    checker_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    requested_at: str
    request_valid_until: str
    evaluated_at: str
    decision_at: str
    evidence_valid_until: str
    review_valid_until: str
    review_scope: Literal[
        "OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY"
    ] = "OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY"
    requested_outcome_scope: Literal[
        "PROVIDER_PROPOSAL_DESIGN_ONLY"
    ] = "PROVIDER_PROPOSAL_DESIGN_ONLY"
    decision: UseScopeDispositionV1
    issue_codes: tuple[UseScopeIssueCodeV1, ...] = Field(max_length=7)
    decision_basis: str = Field(min_length=1, max_length=2000)
    use_scope_review_performed: Literal[True] = True
    eligible_for_separate_provider_proposal: bool
    status: Literal["USE_SCOPE_REVIEW_COMPLETE"] = "USE_SCOPE_REVIEW_COMPLETE"

    @field_validator(
        "requested_at",
        "request_valid_until",
        "evaluated_at",
        "decision_at",
        "review_valid_until",
    )
    @classmethod
    def validate_times(cls, value: str, info: object) -> str:
        name = getattr(info, "field_name", None) or "review timestamp"
        return _utc_seconds(value, field=name)

    @field_validator("evidence_valid_until")
    @classmethod
    def validate_evidence_time(cls, value: str) -> str:
        if value == "PERPETUAL":
            return value
        return _utc_seconds(value, field="evidence_valid_until")

    @field_validator("decision_basis")
    @classmethod
    def validate_basis(cls, value: str) -> str:
        return _portable_text(value, field="Use Scope decision basis")

    @model_validator(mode="after")
    def validate_decision(self) -> CreativeSampleRealAssetUseScopeReviewDecisionV1:
        if self.evaluated_at != self.decision_at:
            raise ValueError("Decision time must be the exact Checker instruction time")
        requested = _parse_utc(self.requested_at)
        decision = _parse_utc(self.decision_at)
        if _parse_utc(self.request_valid_until) != requested + timedelta(
            seconds=REQUEST_VALIDITY_SECONDS
        ):
            raise ValueError("Decision must retain the fixed request window")
        if decision < requested or decision >= _parse_utc(self.request_valid_until):
            raise ValueError("Decision is outside the exclusive request window")
        expected_horizon = decision + timedelta(seconds=REVIEW_VALIDITY_SECONDS)
        if self.evidence_valid_until != "PERPETUAL":
            evidence_end = _parse_utc(self.evidence_valid_until)
            if decision >= evidence_end:
                raise ValueError("rights evidence is not valid at the Decision boundary")
            expected_horizon = min(expected_horizon, evidence_end)
        if _parse_utc(self.review_valid_until) != expected_horizon:
            raise ValueError("Decision review horizon drifted from policy and Evidence")
        if len(self.issue_codes) != len(set(self.issue_codes)) or tuple(
            sorted(self.issue_codes, key=_ISSUE_ORDER.index)
        ) != self.issue_codes:
            raise ValueError("Use Scope issue codes must be unique and in policy order")
        positive = self.decision == "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY"
        if self.eligible_for_separate_provider_proposal is not positive:
            raise ValueError("only the positive decision may allow separate proposal design")
        if positive and self.issue_codes:
            raise ValueError("positive Use Scope decision cannot retain blocking issues")
        if not positive and not self.issue_codes:
            raise ValueError("negative Use Scope decision must retain blocking issues")
        if self.decision == "REJECTED" and "CHECKER_REJECTED_USE_SCOPE" not in self.issue_codes:
            raise ValueError("rejected Use Scope decision requires its dedicated issue code")
        if self.decision != "REJECTED" and "CHECKER_REJECTED_USE_SCOPE" in self.issue_codes:
            raise ValueError("only a rejected Use Scope decision may carry the rejection code")
        expected = stable_id(
            "real_asset_use_scope_decision_v1",
            self.model_dump(mode="json", exclude={"decision_id"}),
        )
        if self.decision_id != expected:
            raise ValueError("Use Scope decision ID must bind its complete canonical content")
        return self


class CreativeSampleRealAssetUseScopeReviewRecordV1(_ReviewModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-use-scope-review-record-v1"
    ] = "sdc.creative-sample-real-asset-use-scope-review-record-v1"
    profile: Literal[
        "creative-sample-real-asset-use-scope-review-v2.6"
    ] = USE_SCOPE_REVIEW_V1_PROFILE
    record_id: str = Field(pattern=r"^real_asset_use_scope_review_record_v1_[0-9a-f]{20}$")
    review_policy_id: Literal[
        "creative-sample-real-asset-use-scope-review-policy"
    ] = USE_SCOPE_REVIEW_V1_POLICY_ID
    review_policy_version: Literal["2.6.0"] = USE_SCOPE_REVIEW_V1_POLICY_VERSION
    review_policy_document_sha256: Literal[
        "0a2745b52d92335e8894b79ee7ff5588dea79d5bbfd021489c45c3bec5f7a969"
    ] = USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256
    use_plan_id: str = Field(pattern=r"^real_asset_use_plan_v1_[0-9a-f]{20}$")
    use_plan_sha256: str = Field(pattern=_LOWER_SHA256)
    request: CreativeSampleRealAssetUseScopeReviewRequestV1
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    instruction: CreativeSampleRealAssetUseScopeReviewInstructionV1
    instruction_sha256: str = Field(pattern=_LOWER_SHA256)
    decision: CreativeSampleRealAssetUseScopeReviewDecisionV1
    decision_sha256: str = Field(pattern=_LOWER_SHA256)

    @model_validator(mode="after")
    def validate_record(self) -> CreativeSampleRealAssetUseScopeReviewRecordV1:
        if self.request_sha256 != _sha256(_canonical_document(self.request)):
            raise ValueError("ReviewRecord request digest drifted")
        if self.instruction_sha256 != _sha256(_canonical_document(self.instruction)):
            raise ValueError("ReviewRecord instruction digest drifted")
        if self.decision_sha256 != _sha256(_canonical_document(self.decision)):
            raise ValueError("ReviewRecord decision digest drifted")
        if self.use_plan_id != self.request.use_plan_id or self.use_plan_sha256 != (
            self.request.use_plan_sha256
        ):
            raise ValueError("ReviewRecord does not bind one exact Use Plan")
        if (
            self.instruction.request_id != self.request.request_id
            or self.instruction.request_sha256 != self.request_sha256
            or self.decision.request_id != self.request.request_id
            or self.decision.request_sha256 != self.request_sha256
            or self.decision.instruction_id != self.instruction.instruction_id
            or self.decision.instruction_sha256 != self.instruction_sha256
        ):
            raise ValueError("ReviewRecord module digest chain is broken")
        expected = stable_id(
            "real_asset_use_scope_review_record_v1",
            self.model_dump(mode="json", exclude={"record_id"}),
        )
        if self.record_id != expected:
            raise ValueError("ReviewRecord ID must bind all three modules and digests")
        return self


def _revalidate[ModelT: BaseModel](
    value: ModelT, model: type[ModelT], *, field: str
) -> ModelT:
    try:
        before = _canonical_document(value)
        rebuilt = model.model_validate(value.model_dump(mode="python"), strict=True)
        after = _canonical_document(rebuilt)
    except (AttributeError, TypeError, ValueError) as exc:
        raise RealAssetUseScopeReviewV26Error(f"{field} violates its strict contract") from exc
    if before != after:
        raise RealAssetUseScopeReviewV26Error(
            f"{field} changes canonical bytes during strict revalidation"
        )
    return rebuilt


def _identity_content_digests(plan: CreativeSampleRealAssetUsePlanV1) -> set[str]:
    closure = plan.manifest_closure
    return {
        _sha256(_canonical_document(plan)),
        plan.plan_policy_document_sha256,
        closure.pack_manifest_sha256,
        closure.evidence_sha256,
        closure.review_a_sha256,
        closure.review_b_sha256,
        closure.pair_check_sha256,
        closure.qualification_request_sha256,
        closure.qualification_instruction_sha256,
        closure.qualification_decision_sha256,
        closure.rights_manifest_sha256,
        *(item.media_sha256 for item in plan.media_mappings),
        *(item.provenance_record_sha256 for item in plan.media_mappings),
        *(item.technical_record_sha256 for item in plan.media_mappings),
    }


def build_use_scope_review_request_v1(
    *,
    use_plan: CreativeSampleRealAssetUsePlanV1,
    maker_identity_ref_sha256: str,
    requested_at: str,
    request_basis: str,
) -> CreativeSampleRealAssetUseScopeReviewRequestV1:
    """Build the Maker-owned Request module from one exact Use Plan."""

    use_plan = _revalidate(use_plan, CreativeSampleRealAssetUsePlanV1, field="Use Plan")
    try:
        requested_at = _utc_seconds(requested_at, field="requested_at")
    except ValueError as exc:
        raise RealAssetUseScopeReviewV26Error("requested_at is invalid") from exc
    if re.fullmatch(_LOWER_SHA256, maker_identity_ref_sha256) is None:
        raise RealAssetUseScopeReviewV26Error("Maker reference must be one lowercase SHA-256")
    if maker_identity_ref_sha256 in _identity_content_digests(use_plan):
        raise RealAssetUseScopeReviewV26Error(
            "Maker reference aliases Use Plan, closure, policy, or media content"
        )
    request_valid_until = _format_utc(
        _parse_utc(requested_at) + timedelta(seconds=REQUEST_VALIDITY_SECONDS)
    )
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-use-scope-review-request-v1",
        "profile": USE_SCOPE_REVIEW_V1_PROFILE,
        "review_policy_id": USE_SCOPE_REVIEW_V1_POLICY_ID,
        "review_policy_version": USE_SCOPE_REVIEW_V1_POLICY_VERSION,
        "review_policy_document_sha256": USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256,
        "use_plan_id": use_plan.plan_id,
        "use_plan_sha256": _sha256(_canonical_document(use_plan)),
        "rights_manifest_id": use_plan.manifest_closure.rights_manifest_id,
        "rights_manifest_sha256": use_plan.manifest_closure.rights_manifest_sha256,
        "rights_manifest_at": use_plan.manifest_closure.rights_manifest_at,
        "evidence_valid_until": use_plan.manifest_closure.evidence_valid_until,
        "maker_role": "MAKER",
        "maker_identity_ref_sha256": maker_identity_ref_sha256,
        "requested_at": requested_at,
        "request_valid_until": request_valid_until,
        "request_basis": request_basis,
        "review_scope": "OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY",
        "requested_outcome_scope": "PROVIDER_PROPOSAL_DESIGN_ONLY",
        "use_scope_review_performed": False,
        "eligible_for_separate_provider_proposal": False,
        "status": "USE_SCOPE_REVIEW_REQUESTED",
        "rights_qualification_performed": True,
        "rights_manifest_created": True,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_separate_provider_approval": False,
        "provider_approval_granted": False,
        "eligible_for_real_generation": False,
        "generation_authorized": False,
        "execution_authorized": False,
        "publication_authorized": False,
        "remote_processing_allowed": False,
        "retention_allowed": False,
        "training_allowed": False,
        "publication_allowed": False,
        "authorized_attempts": 0,
        "authorized_cost_cny": 0,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    try:
        return CreativeSampleRealAssetUseScopeReviewRequestV1.model_validate(
            {"request_id": stable_id("real_asset_use_scope_request_v1", payload), **payload},
            strict=True,
        )
    except ValidationError as exc:
        raise RealAssetUseScopeReviewV26Error("Use Scope request could not be built") from exc


def build_use_scope_review_instruction_v1(
    *,
    request: CreativeSampleRealAssetUseScopeReviewRequestV1,
    checker_identity_ref_sha256: str,
    evaluated_at: str,
    gate_results: tuple[UseScopeGateResultV1, ...],
    disposition: UseScopeDispositionV1,
    checker_basis: str,
) -> CreativeSampleRealAssetUseScopeReviewInstructionV1:
    """Build the Checker-owned Instruction bound to the exact Request bytes."""

    request = _revalidate(
        request,
        CreativeSampleRealAssetUseScopeReviewRequestV1,
        field="Use Scope request",
    )
    try:
        evaluated_at = _utc_seconds(evaluated_at, field="evaluated_at")
    except ValueError as exc:
        raise RealAssetUseScopeReviewV26Error("evaluated_at is invalid") from exc
    if re.fullmatch(_LOWER_SHA256, checker_identity_ref_sha256) is None:
        raise RealAssetUseScopeReviewV26Error("Checker reference must be one lowercase SHA-256")
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-use-scope-review-instruction-v1",
        "profile": USE_SCOPE_REVIEW_V1_PROFILE,
        "review_policy_id": USE_SCOPE_REVIEW_V1_POLICY_ID,
        "review_policy_version": USE_SCOPE_REVIEW_V1_POLICY_VERSION,
        "review_policy_document_sha256": USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256,
        "request_id": request.request_id,
        "request_sha256": _sha256(_canonical_document(request)),
        "use_plan_id": request.use_plan_id,
        "use_plan_sha256": request.use_plan_sha256,
        "rights_manifest_id": request.rights_manifest_id,
        "rights_manifest_sha256": request.rights_manifest_sha256,
        "maker_identity_ref_sha256": request.maker_identity_ref_sha256,
        "checker_role": "CHECKER",
        "checker_identity_ref_sha256": checker_identity_ref_sha256,
        "requested_at": request.requested_at,
        "request_valid_until": request.request_valid_until,
        "evidence_valid_until": request.evidence_valid_until,
        "evaluated_at": evaluated_at,
        "review_scope": request.review_scope,
        "requested_outcome_scope": request.requested_outcome_scope,
        "gate_results": tuple(item.model_dump(mode="json") for item in gate_results),
        "disposition": disposition,
        "checker_basis": checker_basis,
        "use_scope_review_performed": False,
        "eligible_for_separate_provider_proposal": False,
        "status": "USE_SCOPE_CHECK_RECORDED",
        "rights_qualification_performed": True,
        "rights_manifest_created": True,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_separate_provider_approval": False,
        "provider_approval_granted": False,
        "eligible_for_real_generation": False,
        "generation_authorized": False,
        "execution_authorized": False,
        "publication_authorized": False,
        "remote_processing_allowed": False,
        "retention_allowed": False,
        "training_allowed": False,
        "publication_allowed": False,
        "authorized_attempts": 0,
        "authorized_cost_cny": 0,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    try:
        return CreativeSampleRealAssetUseScopeReviewInstructionV1.model_validate(
            {
                "instruction_id": stable_id(
                    "real_asset_use_scope_instruction_v1", payload
                ),
                **{**payload, "gate_results": gate_results},
            },
            strict=True,
        )
    except ValidationError as exc:
        raise RealAssetUseScopeReviewV26Error("Use Scope instruction could not be built") from exc


def _issue_codes(
    instruction: CreativeSampleRealAssetUseScopeReviewInstructionV1,
) -> tuple[UseScopeIssueCodeV1, ...]:
    issues: list[UseScopeIssueCodeV1] = [
        _GATE_ISSUES[result.gate] for result in instruction.gate_results if not result.approved
    ]
    if instruction.disposition == "REJECTED":
        issues.append("CHECKER_REJECTED_USE_SCOPE")
    return tuple(issues)


def compile_use_scope_review_decision_v1(
    *,
    request: CreativeSampleRealAssetUseScopeReviewRequestV1,
    instruction: CreativeSampleRealAssetUseScopeReviewInstructionV1,
) -> CreativeSampleRealAssetUseScopeReviewDecisionV1:
    """Compile the Decision; no caller-supplied decision or decision time is accepted."""

    request = _revalidate(
        request,
        CreativeSampleRealAssetUseScopeReviewRequestV1,
        field="Use Scope request",
    )
    instruction = _revalidate(
        instruction,
        CreativeSampleRealAssetUseScopeReviewInstructionV1,
        field="Use Scope instruction",
    )
    request_sha = _sha256(_canonical_document(request))
    if (
        instruction.request_id != request.request_id
        or instruction.request_sha256 != request_sha
        or instruction.use_plan_id != request.use_plan_id
        or instruction.use_plan_sha256 != request.use_plan_sha256
        or instruction.rights_manifest_id != request.rights_manifest_id
        or instruction.rights_manifest_sha256 != request.rights_manifest_sha256
        or instruction.maker_identity_ref_sha256 != request.maker_identity_ref_sha256
        or instruction.requested_at != request.requested_at
        or instruction.request_valid_until != request.request_valid_until
        or instruction.evidence_valid_until != request.evidence_valid_until
        or instruction.review_scope != request.review_scope
        or instruction.requested_outcome_scope != request.requested_outcome_scope
    ):
        raise RealAssetUseScopeReviewV26Error(
            "Use Scope instruction does not bind the exact Request"
        )
    checked = _parse_utc(instruction.evaluated_at)
    horizon = checked + timedelta(seconds=REVIEW_VALIDITY_SECONDS)
    if request.evidence_valid_until != "PERPETUAL":
        horizon = min(horizon, _parse_utc(request.evidence_valid_until))
    review_valid_until = _format_utc(horizon)
    issues = _issue_codes(instruction)
    instruction_sha = _sha256(_canonical_document(instruction))
    positive = instruction.disposition == "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY"
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-use-scope-review-decision-v1",
        "profile": USE_SCOPE_REVIEW_V1_PROFILE,
        "review_policy_id": USE_SCOPE_REVIEW_V1_POLICY_ID,
        "review_policy_version": USE_SCOPE_REVIEW_V1_POLICY_VERSION,
        "review_policy_document_sha256": USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256,
        "request_id": request.request_id,
        "request_sha256": request_sha,
        "instruction_id": instruction.instruction_id,
        "instruction_sha256": instruction_sha,
        "use_plan_id": request.use_plan_id,
        "use_plan_sha256": request.use_plan_sha256,
        "rights_manifest_id": request.rights_manifest_id,
        "rights_manifest_sha256": request.rights_manifest_sha256,
        "maker_identity_ref_sha256": request.maker_identity_ref_sha256,
        "checker_identity_ref_sha256": instruction.checker_identity_ref_sha256,
        "requested_at": request.requested_at,
        "request_valid_until": request.request_valid_until,
        "evaluated_at": instruction.evaluated_at,
        "decision_at": instruction.evaluated_at,
        "evidence_valid_until": request.evidence_valid_until,
        "review_valid_until": review_valid_until,
        "review_scope": request.review_scope,
        "requested_outcome_scope": request.requested_outcome_scope,
        "decision": instruction.disposition,
        "issue_codes": issues,
        "decision_basis": instruction.checker_basis,
        "use_scope_review_performed": True,
        "eligible_for_separate_provider_proposal": positive,
        "status": "USE_SCOPE_REVIEW_COMPLETE",
        "rights_qualification_performed": True,
        "rights_manifest_created": True,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_separate_provider_approval": False,
        "provider_approval_granted": False,
        "eligible_for_real_generation": False,
        "generation_authorized": False,
        "execution_authorized": False,
        "publication_authorized": False,
        "remote_processing_allowed": False,
        "retention_allowed": False,
        "training_allowed": False,
        "publication_allowed": False,
        "authorized_attempts": 0,
        "authorized_cost_cny": 0,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    try:
        return CreativeSampleRealAssetUseScopeReviewDecisionV1.model_validate(
            {"decision_id": stable_id("real_asset_use_scope_decision_v1", payload), **payload},
            strict=True,
        )
    except ValidationError as exc:
        raise RealAssetUseScopeReviewV26Error("Use Scope decision could not be compiled") from exc


def build_use_scope_review_record_v1(
    *,
    request: CreativeSampleRealAssetUseScopeReviewRequestV1,
    instruction: CreativeSampleRealAssetUseScopeReviewInstructionV1,
) -> CreativeSampleRealAssetUseScopeReviewRecordV1:
    """Assemble one create-new candidate Record from the two independently formed modules."""

    decision = compile_use_scope_review_decision_v1(
        request=request,
        instruction=instruction,
    )
    request_sha = _sha256(_canonical_document(request))
    instruction_sha = _sha256(_canonical_document(instruction))
    decision_sha = _sha256(_canonical_document(decision))
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-use-scope-review-record-v1",
        "profile": USE_SCOPE_REVIEW_V1_PROFILE,
        "review_policy_id": USE_SCOPE_REVIEW_V1_POLICY_ID,
        "review_policy_version": USE_SCOPE_REVIEW_V1_POLICY_VERSION,
        "review_policy_document_sha256": USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256,
        "use_plan_id": request.use_plan_id,
        "use_plan_sha256": request.use_plan_sha256,
        "request": request.model_dump(mode="json"),
        "request_sha256": request_sha,
        "instruction": instruction.model_dump(mode="json"),
        "instruction_sha256": instruction_sha,
        "decision": decision.model_dump(mode="json"),
        "decision_sha256": decision_sha,
    }
    try:
        return CreativeSampleRealAssetUseScopeReviewRecordV1.model_validate(
            {
                "record_id": stable_id(
                    "real_asset_use_scope_review_record_v1", payload
                ),
                **{
                    **payload,
                    "request": request,
                    "instruction": instruction,
                    "decision": decision,
                },
            },
            strict=True,
        )
    except ValidationError as exc:
        raise RealAssetUseScopeReviewV26Error("Use Scope ReviewRecord could not be built") from exc


def verify_use_scope_review_record_internal_v1(
    record: CreativeSampleRealAssetUseScopeReviewRecordV1,
) -> CreativeSampleRealAssetUseScopeReviewRecordV1:
    """Verify only the self-contained three-module digest chain."""

    record = _revalidate(
        record,
        CreativeSampleRealAssetUseScopeReviewRecordV1,
        field="Use Scope ReviewRecord",
    )
    rebuilt = build_use_scope_review_record_v1(
        request=record.request,
        instruction=record.instruction,
    )
    if rebuilt != record:
        raise RealAssetUseScopeReviewV26Error("ReviewRecord drifted from its module chain")
    return record


def verify_use_scope_review_record_closure_v1(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    qualification_request: CreativeSampleRealAssetQualificationRequestV2,
    qualification_instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
    qualification_decision: CreativeSampleRealAssetQualificationDecisionV2,
    rights_manifest: CreativeSampleRealAssetRightsManifestV2,
    use_plan: CreativeSampleRealAssetUsePlanV1,
    record: CreativeSampleRealAssetUseScopeReviewRecordV1,
) -> CreativeSampleRealAssetUseScopeReviewRecordV1:
    """Verify the complete upstream closure, Use Plan, and three-module Record."""

    use_plan = verify_real_asset_use_plan_closure_v1(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        qualification_request=qualification_request,
        qualification_instruction=qualification_instruction,
        qualification_decision=qualification_decision,
        rights_manifest=rights_manifest,
        use_plan=use_plan,
    )
    record = verify_use_scope_review_record_internal_v1(record)
    if record.use_plan_id != use_plan.plan_id or record.use_plan_sha256 != _sha256(
        _canonical_document(use_plan)
    ):
        raise RealAssetUseScopeReviewV26Error("ReviewRecord drifted from the exact Use Plan")
    rebuilt_request = build_use_scope_review_request_v1(
        use_plan=use_plan,
        maker_identity_ref_sha256=record.request.maker_identity_ref_sha256,
        requested_at=record.request.requested_at,
        request_basis=record.request.request_basis,
    )
    if rebuilt_request != record.request:
        raise RealAssetUseScopeReviewV26Error(
            "ReviewRecord Request drifted from the exact verified Use Plan"
        )
    rebuilt_instruction = build_use_scope_review_instruction_v1(
        request=rebuilt_request,
        checker_identity_ref_sha256=record.instruction.checker_identity_ref_sha256,
        evaluated_at=record.instruction.evaluated_at,
        gate_results=record.instruction.gate_results,
        disposition=record.instruction.disposition,
        checker_basis=record.instruction.checker_basis,
    )
    if rebuilt_instruction != record.instruction:
        raise RealAssetUseScopeReviewV26Error(
            "ReviewRecord Instruction drifted from the exact rebuilt Request"
        )
    rebuilt_record = build_use_scope_review_record_v1(
        request=rebuilt_request,
        instruction=rebuilt_instruction,
    )
    if rebuilt_record != record:
        raise RealAssetUseScopeReviewV26Error(
            "ReviewRecord drifted from its complete verified closure"
        )
    if record.request.maker_identity_ref_sha256 in _identity_content_digests(use_plan) or (
        record.instruction.checker_identity_ref_sha256 in _identity_content_digests(use_plan)
    ):
        raise RealAssetUseScopeReviewV26Error(
            "Maker or Checker reference aliases closure, policy, or media content"
        )
    return record


def verify_use_scope_review_current_v1(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    qualification_request: CreativeSampleRealAssetQualificationRequestV2,
    qualification_instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
    qualification_decision: CreativeSampleRealAssetQualificationDecisionV2,
    rights_manifest: CreativeSampleRealAssetRightsManifestV2,
    use_plan: CreativeSampleRealAssetUsePlanV1,
    record: CreativeSampleRealAssetUseScopeReviewRecordV1,
    observed_at: str,
) -> CreativeSampleRealAssetUseScopeReviewRecordV1:
    """Check temporal proposal-design eligibility against the complete historical closure.

    This pure check cannot establish the absence of a later hold, revocation, complaint,
    dispute, or policy change.  Those conditions require separately designed fresh evidence.
    """

    record = verify_use_scope_review_record_closure_v1(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        qualification_request=qualification_request,
        qualification_instruction=qualification_instruction,
        qualification_decision=qualification_decision,
        rights_manifest=rights_manifest,
        use_plan=use_plan,
        record=record,
    )
    try:
        observed_at = _utc_seconds(observed_at, field="observed_at")
    except ValueError as exc:
        raise RealAssetUseScopeReviewV26Error("observed_at is invalid") from exc
    if (
        record.decision.decision != "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY"
        or _parse_utc(observed_at) < _parse_utc(record.decision.decision_at)
        or _parse_utc(observed_at) >= _parse_utc(record.decision.review_valid_until)
    ):
        raise RealAssetUseScopeReviewV26Error(
            "Use Scope record is not currently eligible for separate proposal design"
        )
    return record


def extract_use_scope_request_v1(
    record: CreativeSampleRealAssetUseScopeReviewRecordV1,
) -> tuple[CreativeSampleRealAssetUseScopeReviewRequestV1, bytes]:
    record = verify_use_scope_review_record_internal_v1(record)
    return record.request, _canonical_document(record.request)


def extract_use_scope_instruction_v1(
    record: CreativeSampleRealAssetUseScopeReviewRecordV1,
) -> tuple[CreativeSampleRealAssetUseScopeReviewInstructionV1, bytes]:
    record = verify_use_scope_review_record_internal_v1(record)
    return record.instruction, _canonical_document(record.instruction)


def extract_use_scope_decision_v1(
    record: CreativeSampleRealAssetUseScopeReviewRecordV1,
) -> tuple[CreativeSampleRealAssetUseScopeReviewDecisionV1, bytes]:
    record = verify_use_scope_review_record_internal_v1(record)
    return record.decision, _canonical_document(record.decision)


def _reject_json_constant(value: str) -> None:
    raise RealAssetUseScopeReviewV26Error(f"non-finite JSON number is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RealAssetUseScopeReviewV26Error(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _parse_model[ModelT: BaseModel](
    raw: bytes, model: type[ModelT], *, label: str
) -> ModelT:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > _JSON_LIMIT
        or raw.startswith(b"\xef\xbb\xbf")
    ):
        raise RealAssetUseScopeReviewV26Error(f"{label} JSON must be bounded BOM-free bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise RealAssetUseScopeReviewV26Error(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RealAssetUseScopeReviewV26Error(f"{label} JSON must contain one object")
    try:
        candidate = model.model_validate_json(raw, strict=False)
        parsed = model.model_validate(candidate.model_dump(mode="python"), strict=True)
    except ValidationError as exc:
        raise RealAssetUseScopeReviewV26Error(f"{label} violates its strict contract") from exc
    if raw != _canonical_document(parsed):
        raise RealAssetUseScopeReviewV26Error(f"{label} is not the exact canonical document")
    return parsed


def parse_use_scope_review_request_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetUseScopeReviewRequestV1:
    return _parse_model(
        raw,
        CreativeSampleRealAssetUseScopeReviewRequestV1,
        label="Use Scope request",
    )


def parse_use_scope_review_instruction_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetUseScopeReviewInstructionV1:
    return _parse_model(
        raw,
        CreativeSampleRealAssetUseScopeReviewInstructionV1,
        label="Use Scope instruction",
    )


def parse_use_scope_review_decision_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetUseScopeReviewDecisionV1:
    return _parse_model(
        raw,
        CreativeSampleRealAssetUseScopeReviewDecisionV1,
        label="Use Scope decision",
    )


def parse_use_scope_review_record_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetUseScopeReviewRecordV1:
    return _parse_model(
        raw,
        CreativeSampleRealAssetUseScopeReviewRecordV1,
        label="Use Scope ReviewRecord",
    )


__all__ = [
    "REQUEST_VALIDITY_SECONDS",
    "REVIEW_VALIDITY_SECONDS",
    "USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256",
    "USE_SCOPE_REVIEW_V1_POLICY_ID",
    "USE_SCOPE_REVIEW_V1_POLICY_VERSION",
    "USE_SCOPE_REVIEW_V1_PROFILE",
    "CreativeSampleRealAssetUseScopeReviewDecisionV1",
    "CreativeSampleRealAssetUseScopeReviewInstructionV1",
    "CreativeSampleRealAssetUseScopeReviewRecordV1",
    "CreativeSampleRealAssetUseScopeReviewRequestV1",
    "RealAssetUseScopeReviewV26Error",
    "UseScopeGateResultV1",
    "build_use_scope_review_instruction_v1",
    "build_use_scope_review_record_v1",
    "build_use_scope_review_request_v1",
    "compile_use_scope_review_decision_v1",
    "extract_use_scope_decision_v1",
    "extract_use_scope_instruction_v1",
    "extract_use_scope_request_v1",
    "parse_use_scope_review_decision_v1_json",
    "parse_use_scope_review_instruction_v1_json",
    "parse_use_scope_review_record_v1_json",
    "parse_use_scope_review_request_v1_json",
    "verify_use_scope_review_current_v1",
    "verify_use_scope_review_record_closure_v1",
    "verify_use_scope_review_record_internal_v1",
]
