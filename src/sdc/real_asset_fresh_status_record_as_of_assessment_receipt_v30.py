"""Immutable historical Fresh Status as-of assessment Receipt contracts v3.0.

This module builds and verifies one persistent, deterministic Receipt by freshly invoking the
public Slice 5 explicit-``as_of`` assessment in the same in-memory call.  It accepts no detached
Slice 2--5 result and performs no filesystem, path, CLI, environment, wall-clock, network,
Provider, persistence, credential, entitlement, or execution operation.

A verified Receipt proves only that its exact historical projection can be reproduced from the
exact objects, explicit finite chains, and explicit ``as_of`` supplied to the verifier.  It does
not prove source authenticity or completeness, hidden-branch absence, present reality, legal
effect, Provider availability, or any authority to act.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from sdc.compiler import stable_id
from sdc.real_asset_fresh_status_chain_replay_v30 import (
    FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE,
    FreshStatusChainReplayErrorCodeV1,
)
from sdc.real_asset_fresh_status_evidence_v30 import (
    FRESH_STATUS_EVIDENCE_SCOPE,
    FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256,
    FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
    FRESH_STATUS_EVIDENCE_V1_PROFILE,
    CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    FreshStatusCategoryV1,
    FreshStatusDispositionV1,
    FreshStatusLimitationCodeV1,
    FreshStatusSubjectClosureV1,
)
from sdc.real_asset_fresh_status_record_as_of_assessment_v30 import (
    _RESULT_PROVENANCE_SENTINEL as _SLICE5_RESULT_PROVENANCE_SENTINEL,
)
from sdc.real_asset_fresh_status_record_as_of_assessment_v30 import (
    FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1,
    FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE,
    FreshStatusAsOfWindowStateV1,
    FreshStatusEvidenceRecordAsOfAssessmentResultV1,
    FreshStatusRecordAsOfAssessmentErrorCodeV1,
    RealAssetFreshStatusRecordAsOfAssessmentV30Error,
    assess_fresh_status_evidence_record_as_of_v1,
)
from sdc.real_asset_fresh_status_record_chain_coverage_v30 import (
    FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE,
    FreshStatusRecordChainCoverageErrorCodeV1,
    FreshStatusRecordChainInputV1,
)
from sdc.real_asset_fresh_status_record_joint_replay_v30 import (
    FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE,
    FreshStatusRecordJointReplayErrorCodeV1,
)
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
from sdc.real_asset_use_plan_v26 import CreativeSampleRealAssetUsePlanV1
from sdc.real_asset_use_scope_review_v26 import CreativeSampleRealAssetUseScopeReviewRecordV1

FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_V1_PROFILE: Literal[
    "creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1"
] = "creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1"
FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES = 65_536

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_UTC_SECONDS = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_AS_OF_ASSESSMENT_DOMAIN = (
    b"sdc:creative-sample-real-asset-fresh-status-record-as-of-assessment:v1\0"
)
_ASSESSMENT_RESULT_PROVENANCE_DOMAIN = (
    b"sdc:creative-sample-real-asset-fresh-status-record-as-of-assessment-provenance:v1\0"
)

_CATEGORY_ORDER: tuple[FreshStatusCategoryV1, ...] = (
    "HOLD_ACTIVE",
    "REVOCATION_EFFECTIVE",
    "COMPLAINT_OPEN",
    "DISPUTE_OPEN",
    "RIGHTS_BASIS_CURRENT",
    "IDENTITY_BINDING_CURRENT",
    "POLICY_COMPATIBILITY_CURRENT",
)
_CATEGORY_ORDER_INDEX = {category: index for index, category in enumerate(_CATEGORY_ORDER)}
_ALL_LIMITATION_CODES: tuple[FreshStatusLimitationCodeV1, ...] = (
    "SOURCE_AUTHENTICITY_NOT_PROVEN",
    "SOURCE_COMPLETENESS_NOT_PROVEN",
    "CHAIN_COMPLETENESS_NOT_PROVEN",
    "REALITY_CURRENTNESS_NOT_PROVEN",
    "SCOPE_LIMITED_TO_DECLARED_SUBJECT",
    "TIME_WINDOW_LIMITED",
    "LEGAL_EFFECT_NOT_DETERMINED",
)

FreshStatusRecordAsOfAssessmentReceiptErrorCodeV1 = Literal[
    "RECEIPT_CONTRACT_INVALID",
    "AS_OF_ASSESSMENT_REPLAY_FAILED",
    "ASSESSMENT_RESULT_INCONSISTENT",
    "INTERNAL_RECEIPT_INCONSISTENCY",
    "RECEIPT_REPLAY_MISMATCH",
]


class RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error(RuntimeError):
    """The pure historical as-of assessment Receipt operation failed closed."""

    code: FreshStatusRecordAsOfAssessmentReceiptErrorCodeV1
    assessment_code: FreshStatusRecordAsOfAssessmentErrorCodeV1 | None
    joint_replay_code: FreshStatusRecordJointReplayErrorCodeV1 | None
    coverage_code: FreshStatusRecordChainCoverageErrorCodeV1 | None
    replay_code: FreshStatusChainReplayErrorCodeV1 | None

    def __init__(
        self,
        code: FreshStatusRecordAsOfAssessmentReceiptErrorCodeV1,
        message: str,
        *,
        assessment_code: FreshStatusRecordAsOfAssessmentErrorCodeV1 | None = None,
        joint_replay_code: FreshStatusRecordJointReplayErrorCodeV1 | None = None,
        coverage_code: FreshStatusRecordChainCoverageErrorCodeV1 | None = None,
        replay_code: FreshStatusChainReplayErrorCodeV1 | None = None,
    ) -> None:
        self.code = code
        self.assessment_code = assessment_code
        self.joint_replay_code = joint_replay_code
        self.coverage_code = coverage_code
        self.replay_code = replay_code
        nested = ""
        if assessment_code is not None:
            nested += f" (Slice 5 code: {assessment_code})"
        if joint_replay_code is not None:
            nested += f" (Slice 4 code: {joint_replay_code})"
        if coverage_code is not None:
            nested += f" (Slice 3 code: {coverage_code})"
        if replay_code is not None:
            nested += f" (Slice 2 code: {replay_code})"
        super().__init__(f"{code}: {message}{nested}")


class _AssessmentReceiptModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class _ZeroAuthorityAssessmentReceiptModel(_AssessmentReceiptModel):
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"] = FRESH_STATUS_EVIDENCE_SCOPE
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    generation_authorized: Literal[False] = False
    execution_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    remote_processing_allowed: Literal[False] = False
    retention_allowed: Literal[False] = False
    training_allowed: Literal[False] = False
    publication_allowed: Literal[False] = False
    automated_execution_allowed: Literal[False] = False
    authorized_attempts: Literal[0] = 0
    authorized_cost_cny: Literal[0] = 0
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0
    usage_restriction: Literal["MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"] = (
        "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_zero_authority_scalar_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        for field in (
            "generation_authorized",
            "execution_authorized",
            "publication_authorized",
            "remote_processing_allowed",
            "retention_allowed",
            "training_allowed",
            "publication_allowed",
            "automated_execution_allowed",
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


def _json_projection(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_projection(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return tuple(_json_projection(item) for item in value)
    return value


def _canonical_payload(value: object) -> bytes:
    return json.dumps(
        _json_projection(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_document(value: BaseModel) -> bytes:
    return (
        json.dumps(
            value.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_source_document(value: BaseModel) -> bytes:
    return (
        json.dumps(
            value.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _utc_seconds(value: str, *, field: str) -> str:
    if type(value) is not str or re.fullmatch(_UTC_SECONDS, value) is None:
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


def _as_of_assessment_sha256(
    *,
    evidence_record_id: str,
    evidence_record_sha256: str,
    request_id: str,
    request_sha256: str,
    decision_id: str,
    decision_sha256: str,
    subject_closure: FreshStatusSubjectClosureV1,
    coverage_set_sha256: str,
    joint_replay_sha256: str,
    as_of: str,
    evaluated_at: str,
    status_valid_until: str,
    window_semantics: str,
    recorded_disposition: FreshStatusDispositionV1,
    recorded_blocking_categories: tuple[FreshStatusCategoryV1, ...],
    recorded_indeterminate_categories: tuple[FreshStatusCategoryV1, ...],
    as_of_window_state: FreshStatusAsOfWindowStateV1,
) -> str:
    projection = {
        "assessment_profile": FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE,
        "source_joint_replay_profile": FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE,
        "source_record_chain_coverage_profile": FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE,
        "source_chain_replay_profile": FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE,
        "source_evidence_profile": FRESH_STATUS_EVIDENCE_V1_PROFILE,
        "source_evidence_policy_version": FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
        "source_evidence_policy_document_sha256": FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256,
        "evidence_record_id": evidence_record_id,
        "evidence_record_sha256": evidence_record_sha256,
        "request_id": request_id,
        "request_sha256": request_sha256,
        "decision_id": decision_id,
        "decision_sha256": decision_sha256,
        "subject_closure": subject_closure,
        "coverage_set_sha256": coverage_set_sha256,
        "joint_replay_sha256": joint_replay_sha256,
        "as_of": as_of,
        "evaluated_at": evaluated_at,
        "status_valid_until": status_valid_until,
        "window_semantics": window_semantics,
        "recorded_disposition": recorded_disposition,
        "recorded_blocking_categories": recorded_blocking_categories,
        "recorded_indeterminate_categories": recorded_indeterminate_categories,
        "as_of_window_state": as_of_window_state,
    }
    return _sha256(_AS_OF_ASSESSMENT_DOMAIN + _canonical_payload(projection))


def _assessment_result_provenance_sha256(
    value: FreshStatusEvidenceRecordAsOfAssessmentResultV1,
) -> str:
    return _sha256(
        _ASSESSMENT_RESULT_PROVENANCE_DOMAIN
        + _canonical_payload(value.model_dump(mode="json", exclude_none=False))
    )


def _stable_receipt_id(payload: dict[str, object]) -> str:
    return stable_id(
        "real_asset_fresh_status_record_as_of_assessment_receipt_v1",
        _json_projection(payload),
    )


class CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1(
    _ZeroAuthorityAssessmentReceiptModel
):
    """Immutable historical Receipt for one exact freshly replayed Slice 5 assessment."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1"
    ] = "sdc.creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1"
    profile: Literal[
        "creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1"
    ] = FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_V1_PROFILE
    receipt_id: str = Field(
        pattern=r"^real_asset_fresh_status_record_as_of_assessment_receipt_v1_[0-9a-f]{20}$"
    )
    receipt_purpose: Literal["HISTORICAL_EXPLICIT_AS_OF_ASSESSMENT_ONLY"] = (
        "HISTORICAL_EXPLICIT_AS_OF_ASSESSMENT_ONLY"
    )
    reliance_requirement: Literal["FULL_CLOSURE_AND_EXPLICIT_AS_OF_REPLAY_REQUIRED"] = (
        "FULL_CLOSURE_AND_EXPLICIT_AS_OF_REPLAY_REQUIRED"
    )
    present_currentness_asserted: Literal[False] = False
    source_assessment_result_type: Literal[
        "FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_RESULT_V1"
    ] = "FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_RESULT_V1"
    source_assessment_status: Literal["FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_COMPLETED"] = (
        "FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_COMPLETED"
    )
    assessment_profile: Literal[
        "creative-sample-real-asset-fresh-status-record-as-of-assessment-v1"
    ] = FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE
    source_joint_replay_profile: Literal[
        "creative-sample-real-asset-fresh-status-record-joint-replay-v1"
    ] = FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE
    source_record_chain_coverage_profile: Literal[
        "creative-sample-real-asset-fresh-status-record-chain-coverage-v1"
    ] = FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE
    source_chain_replay_profile: Literal[
        "creative-sample-real-asset-fresh-status-explicit-chain-replay-v1"
    ] = FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE
    source_evidence_profile: Literal["creative-sample-real-asset-fresh-status-evidence-v3.0"] = (
        FRESH_STATUS_EVIDENCE_V1_PROFILE
    )
    source_evidence_policy_version: Literal["3.0.0"] = FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION
    source_evidence_policy_document_sha256: Literal[
        "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"
    ] = FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256
    evidence_record_id: str = Field(
        pattern=r"^real_asset_fresh_status_evidence_record_v1_[0-9a-f]{20}$"
    )
    evidence_record_sha256: str = Field(pattern=_LOWER_SHA256)
    request_id: str = Field(pattern=r"^real_asset_fresh_status_request_v1_[0-9a-f]{20}$")
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    decision_id: str = Field(pattern=r"^real_asset_fresh_status_decision_v1_[0-9a-f]{20}$")
    decision_sha256: str = Field(pattern=_LOWER_SHA256)
    subject_closure: FreshStatusSubjectClosureV1
    coverage_set_sha256: str = Field(pattern=_LOWER_SHA256)
    joint_replay_sha256: str = Field(pattern=_LOWER_SHA256)
    as_of: str
    evaluated_at: str
    status_valid_until: str
    window_semantics: Literal["EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE"] = (
        FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1
    )
    recorded_disposition: FreshStatusDispositionV1
    recorded_blocking_categories: tuple[FreshStatusCategoryV1, ...] = Field(max_length=7)
    recorded_indeterminate_categories: tuple[FreshStatusCategoryV1, ...] = Field(max_length=7)
    as_of_window_state: FreshStatusAsOfWindowStateV1
    as_of_assessment_sha256: str = Field(pattern=_LOWER_SHA256)
    provided_record_joint_replay_consistent: Literal[True] = True
    explicit_as_of_window_assessment_consistent: Literal[True] = True
    limitation_codes: tuple[FreshStatusLimitationCodeV1, ...] = _ALL_LIMITATION_CODES
    status: Literal["FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_RECORDED"] = (
        "FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_RECORDED"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_receipt_scalar_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        if (
            "present_currentness_asserted" in value
            and type(value["present_currentness_asserted"]) is not bool
        ):
            raise ValueError("present_currentness_asserted must be an exact JSON boolean")
        return value

    @field_validator("as_of", "evaluated_at", "status_valid_until")
    @classmethod
    def validate_times(cls, value: str, info: object) -> str:
        name = getattr(info, "field_name", None) or "Receipt timestamp"
        return _utc_seconds(value, field=name)

    @model_validator(mode="after")
    def validate_receipt(
        self,
    ) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
        evaluated_at = _parse_utc(self.evaluated_at)
        status_valid_until = _parse_utc(self.status_valid_until)
        as_of = _parse_utc(self.as_of)
        if status_valid_until < evaluated_at:
            raise ValueError("status_valid_until cannot predate evaluated_at")
        if as_of < evaluated_at:
            raise ValueError("as_of cannot predate evaluated_at in a historical Receipt")
        expected_state: FreshStatusAsOfWindowStateV1 = (
            "WITHIN_EXPLICIT_BOUND_WINDOW" if as_of < status_valid_until else "EXPIRED_NOT_CURRENT"
        )
        if self.as_of_window_state != expected_state:
            raise ValueError("as_of_window_state drifted from the frozen half-open window")

        blocking = self.recorded_blocking_categories
        indeterminate = self.recorded_indeterminate_categories
        if len(blocking) != len(set(blocking)) or len(indeterminate) != len(set(indeterminate)):
            raise ValueError("recorded Decision category projections must be unique")
        if set(blocking) & set(indeterminate):
            raise ValueError("recorded blocking and indeterminate categories must be disjoint")
        if blocking != tuple(sorted(blocking, key=_CATEGORY_ORDER_INDEX.__getitem__)):
            raise ValueError("recorded blocking categories must retain fixed policy order")
        if indeterminate != tuple(sorted(indeterminate, key=_CATEGORY_ORDER_INDEX.__getitem__)):
            raise ValueError("recorded indeterminate categories must retain fixed policy order")
        expected_disposition: FreshStatusDispositionV1
        if blocking:
            expected_disposition = "BLOCKING_STATUS_RECORDED"
        elif indeterminate:
            expected_disposition = "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"
        else:
            expected_disposition = "NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET"
        if self.recorded_disposition != expected_disposition:
            raise ValueError("recorded disposition drifted from the exact Decision categories")
        if self.limitation_codes != _ALL_LIMITATION_CODES:
            raise ValueError("historical Receipt must retain all seven limitation codes")

        expected_assessment_sha256 = _as_of_assessment_sha256(
            evidence_record_id=self.evidence_record_id,
            evidence_record_sha256=self.evidence_record_sha256,
            request_id=self.request_id,
            request_sha256=self.request_sha256,
            decision_id=self.decision_id,
            decision_sha256=self.decision_sha256,
            subject_closure=self.subject_closure,
            coverage_set_sha256=self.coverage_set_sha256,
            joint_replay_sha256=self.joint_replay_sha256,
            as_of=self.as_of,
            evaluated_at=self.evaluated_at,
            status_valid_until=self.status_valid_until,
            window_semantics=self.window_semantics,
            recorded_disposition=self.recorded_disposition,
            recorded_blocking_categories=self.recorded_blocking_categories,
            recorded_indeterminate_categories=self.recorded_indeterminate_categories,
            as_of_window_state=self.as_of_window_state,
        )
        if self.as_of_assessment_sha256 != expected_assessment_sha256:
            raise ValueError("as_of_assessment_sha256 drifted from the frozen Slice 5 projection")
        expected_id = _stable_receipt_id(self.model_dump(mode="json", exclude={"receipt_id"}))
        if self.receipt_id != expected_id:
            raise ValueError("Receipt ID must bind every other Receipt field")
        if len(_canonical_document(self)) > FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES:
            raise ValueError("Receipt exceeds the frozen canonical document byte limit")
        return self


def _raise(
    code: FreshStatusRecordAsOfAssessmentReceiptErrorCodeV1,
    message: str,
    *,
    assessment_code: FreshStatusRecordAsOfAssessmentErrorCodeV1 | None = None,
    joint_replay_code: FreshStatusRecordJointReplayErrorCodeV1 | None = None,
    coverage_code: FreshStatusRecordChainCoverageErrorCodeV1 | None = None,
    replay_code: FreshStatusChainReplayErrorCodeV1 | None = None,
) -> Never:
    raise RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error(
        code,
        message,
        assessment_code=assessment_code,
        joint_replay_code=joint_replay_code,
        coverage_code=coverage_code,
        replay_code=replay_code,
    )


def _zero_authority_payload() -> dict[str, object]:
    return {
        "evidence_scope": FRESH_STATUS_EVIDENCE_SCOPE,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "generation_authorized": False,
        "execution_authorized": False,
        "publication_authorized": False,
        "remote_processing_allowed": False,
        "retention_allowed": False,
        "training_allowed": False,
        "publication_allowed": False,
        "automated_execution_allowed": False,
        "authorized_attempts": 0,
        "authorized_cost_cny": 0,
        "posts_allowed": 0,
        "provider_requests": 0,
        "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION",
    }


def _assessment_zero_authority_consistent(
    result: FreshStatusEvidenceRecordAsOfAssessmentResultV1,
) -> bool:
    return all(
        getattr(result, field, object()) == expected
        and type(getattr(result, field, object())) is type(expected)
        for field, expected in _zero_authority_payload().items()
    )


def _require_assessment_result(
    *,
    result: object,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    as_of: str,
) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
    if type(result) is not FreshStatusEvidenceRecordAsOfAssessmentResultV1:
        _raise(
            "ASSESSMENT_RESULT_INCONSISTENT",
            "the public Slice 5 assessor returned an unexpected result type",
        )
    assert isinstance(result, FreshStatusEvidenceRecordAsOfAssessmentResultV1)
    try:
        evidence_record_sha256 = _sha256(_canonical_source_document(record))
        decision_sha256 = _sha256(_canonical_source_document(record.decision))
        expected_state: FreshStatusAsOfWindowStateV1 = (
            "WITHIN_EXPLICIT_BOUND_WINDOW"
            if _parse_utc(as_of) < _parse_utc(record.decision.status_valid_until)
            else "EXPIRED_NOT_CURRENT"
        )
        expected_digest = _as_of_assessment_sha256(
            evidence_record_id=record.record_id,
            evidence_record_sha256=evidence_record_sha256,
            request_id=record.request.request_id,
            request_sha256=record.request_sha256,
            decision_id=record.decision.decision_id,
            decision_sha256=decision_sha256,
            subject_closure=record.subject_closure,
            coverage_set_sha256=result.coverage_set_sha256,
            joint_replay_sha256=result.joint_replay_sha256,
            as_of=as_of,
            evaluated_at=record.decision.evaluated_at,
            status_valid_until=record.decision.status_valid_until,
            window_semantics=FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1,
            recorded_disposition=record.decision.disposition,
            recorded_blocking_categories=record.decision.blocking_categories,
            recorded_indeterminate_categories=record.decision.indeterminate_categories,
            as_of_window_state=expected_state,
        )
        provenance = result._verification_provenance
        provenance_consistent = (
            isinstance(provenance, tuple)
            and len(provenance) == 2
            and provenance[0] is _SLICE5_RESULT_PROVENANCE_SENTINEL
            and type(provenance[1]) is str
            and provenance[1] == _assessment_result_provenance_sha256(result)
        )
        fixed_projection_consistent = (
            result.result_type == "FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_RESULT_V1"
            and result.assessment_profile == FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE
            and result.source_joint_replay_profile == FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE
            and result.source_record_chain_coverage_profile
            == FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE
            and result.source_chain_replay_profile == FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE
            and result.source_evidence_profile == FRESH_STATUS_EVIDENCE_V1_PROFILE
            and result.source_evidence_policy_version == FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION
            and result.source_evidence_policy_document_sha256
            == FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256
            and result.evidence_record_id == record.record_id
            and result.evidence_record_sha256 == evidence_record_sha256
            and result.request_id == record.request.request_id
            and result.request_sha256 == record.request_sha256
            and result.decision_id == record.decision.decision_id
            and result.decision_sha256 == decision_sha256
            and result.subject_closure == record.subject_closure
            and re.fullmatch(_LOWER_SHA256, result.coverage_set_sha256) is not None
            and re.fullmatch(_LOWER_SHA256, result.joint_replay_sha256) is not None
            and result.as_of == as_of
            and result.evaluated_at == record.decision.evaluated_at
            and result.status_valid_until == record.decision.status_valid_until
            and result.window_semantics == FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1
            and result.recorded_disposition == record.decision.disposition
            and result.recorded_blocking_categories == record.decision.blocking_categories
            and result.recorded_indeterminate_categories == record.decision.indeterminate_categories
            and result.as_of_window_state == expected_state
            and result.as_of_assessment_sha256 == expected_digest
            and result.provided_record_joint_replay_consistent is True
            and result.explicit_as_of_window_assessment_consistent is True
            and result.limitation_codes == _ALL_LIMITATION_CODES
            and result.status == "FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_COMPLETED"
            and _assessment_zero_authority_consistent(result)
            and provenance_consistent
        )
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error(
            "ASSESSMENT_RESULT_INCONSISTENT",
            "the live Slice 5 result could not yield the frozen Receipt projection",
        ) from exc
    if not fixed_projection_consistent:
        _raise(
            "ASSESSMENT_RESULT_INCONSISTENT",
            "the live Slice 5 result drifted from exact source anchors or zero-authority state",
        )
    return result


def _receipt_payload_from_result(
    result: FreshStatusEvidenceRecordAsOfAssessmentResultV1,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "document_type": (
            "sdc.creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1"
        ),
        "profile": FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_V1_PROFILE,
        "receipt_purpose": "HISTORICAL_EXPLICIT_AS_OF_ASSESSMENT_ONLY",
        "reliance_requirement": "FULL_CLOSURE_AND_EXPLICIT_AS_OF_REPLAY_REQUIRED",
        "present_currentness_asserted": False,
        "source_assessment_result_type": result.result_type,
        "source_assessment_status": result.status,
        "assessment_profile": result.assessment_profile,
        "source_joint_replay_profile": result.source_joint_replay_profile,
        "source_record_chain_coverage_profile": result.source_record_chain_coverage_profile,
        "source_chain_replay_profile": result.source_chain_replay_profile,
        "source_evidence_profile": result.source_evidence_profile,
        "source_evidence_policy_version": result.source_evidence_policy_version,
        "source_evidence_policy_document_sha256": result.source_evidence_policy_document_sha256,
        "evidence_record_id": result.evidence_record_id,
        "evidence_record_sha256": result.evidence_record_sha256,
        "request_id": result.request_id,
        "request_sha256": result.request_sha256,
        "decision_id": result.decision_id,
        "decision_sha256": result.decision_sha256,
        "subject_closure": result.subject_closure,
        "coverage_set_sha256": result.coverage_set_sha256,
        "joint_replay_sha256": result.joint_replay_sha256,
        "as_of": result.as_of,
        "evaluated_at": result.evaluated_at,
        "status_valid_until": result.status_valid_until,
        "window_semantics": result.window_semantics,
        "recorded_disposition": result.recorded_disposition,
        "recorded_blocking_categories": result.recorded_blocking_categories,
        "recorded_indeterminate_categories": result.recorded_indeterminate_categories,
        "as_of_window_state": result.as_of_window_state,
        "as_of_assessment_sha256": result.as_of_assessment_sha256,
        "provided_record_joint_replay_consistent": (result.provided_record_joint_replay_consistent),
        "explicit_as_of_window_assessment_consistent": (
            result.explicit_as_of_window_assessment_consistent
        ),
        "limitation_codes": result.limitation_codes,
        "status": "FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_RECORDED",
        **_zero_authority_payload(),
    }


def _compile_receipt(
    *,
    result: object,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    as_of: str,
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
    result = _require_assessment_result(result=result, record=record, as_of=as_of)
    try:
        payload = _receipt_payload_from_result(result)
        receipt_id = _stable_receipt_id(payload)
        return CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_validate(
            {"receipt_id": receipt_id, **payload},
            strict=True,
        )
    except RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error:
        raise
    except (AttributeError, TypeError, UnicodeError, ValidationError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error(
            "INTERNAL_RECEIPT_INCONSISTENCY",
            "the exact live Slice 5 projection could not form a bounded immutable Receipt",
        ) from exc


def _strict_receipt(
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
    try:
        if type(receipt) is not CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
            raise TypeError("receipt must be the exact Receipt V1 contract type")
        before = _canonical_document(receipt)
        rebuilt = CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_validate(
            receipt.model_dump(mode="python"),
            strict=True,
        )
        after = _canonical_document(rebuilt)
    except (AttributeError, TypeError, UnicodeError, ValidationError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error(
            "RECEIPT_CONTRACT_INVALID",
            "receipt violates its exact strict immutable bounded contract",
        ) from exc
    if receipt != rebuilt or before != after:
        _raise(
            "RECEIPT_CONTRACT_INVALID",
            "receipt changes model identity or canonical bytes during strict revalidation",
        )
    return receipt


def _fresh_assessment(
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
    use_scope_review_record: CreativeSampleRealAssetUseScopeReviewRecordV1,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    as_of: str,
) -> object:
    try:
        return assess_fresh_status_evidence_record_as_of_v1(
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
            use_scope_review_record=use_scope_review_record,
            record=record,
            chains=chains,
            as_of=as_of,
        )
    except RealAssetFreshStatusRecordAsOfAssessmentV30Error as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error(
            "AS_OF_ASSESSMENT_REPLAY_FAILED",
            "the exact closure failed the public Slice 5 explicit-as-of assessment",
            assessment_code=exc.code,
            joint_replay_code=exc.joint_replay_code,
            coverage_code=exc.coverage_code,
            replay_code=exc.replay_code,
        ) from exc


def build_fresh_status_record_as_of_assessment_receipt_v1(
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
    use_scope_review_record: CreativeSampleRealAssetUseScopeReviewRecordV1,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    as_of: str,
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
    """Build one immutable Receipt after exactly one fresh public Slice 5 assessment."""

    result = _fresh_assessment(
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
        use_scope_review_record=use_scope_review_record,
        record=record,
        chains=chains,
        as_of=as_of,
    )
    return _compile_receipt(result=result, record=record, as_of=as_of)


def verify_fresh_status_record_as_of_assessment_receipt_closure_v1(
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
    use_scope_review_record: CreativeSampleRealAssetUseScopeReviewRecordV1,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
    """Verify one Receipt by one fresh public Slice 5 replay at the Receipt's exact ``as_of``."""

    receipt = _strict_receipt(receipt)
    result = _fresh_assessment(
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
        use_scope_review_record=use_scope_review_record,
        record=record,
        chains=chains,
        as_of=receipt.as_of,
    )
    expected = _compile_receipt(result=result, record=record, as_of=receipt.as_of)
    try:
        if (
            receipt != expected
            or receipt.receipt_id != expected.receipt_id
            or _canonical_document(receipt) != _canonical_document(expected)
        ):
            _raise(
                "RECEIPT_REPLAY_MISMATCH",
                "receipt does not equal the exact freshly rebuilt historical projection",
            )
    except RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error:
        raise
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error(
            "INTERNAL_RECEIPT_INCONSISTENCY",
            "exact canonical Receipt comparison could not be completed",
        ) from exc
    return receipt


__all__ = [
    "FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_V1_PROFILE",
    "FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES",
    "FreshStatusRecordAsOfAssessmentReceiptErrorCodeV1",
    "CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1",
    "RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error",
    "build_fresh_status_record_as_of_assessment_receipt_v1",
    "verify_fresh_status_record_as_of_assessment_receipt_closure_v1",
]
