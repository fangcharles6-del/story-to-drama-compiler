"""Pure explicit-``as_of`` Fresh Status Record assessment for v3.0.

This module freshly composes the public Slice 4 joint replay with one exact caller-supplied
assessment instant.  It performs no filesystem, path, CLI, environment, network, Provider,
wall-clock, persistence, credential, or execution operation.  A successful result states only
whether the replayed Record's frozen half-open technical window contains that explicit instant;
it does not prove reality currentness, source completeness, legal effect, or authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Literal, Never

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

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
from sdc.real_asset_fresh_status_record_chain_coverage_v30 import (
    FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE,
    FreshStatusRecordChainCoverageErrorCodeV1,
    FreshStatusRecordChainInputV1,
)
from sdc.real_asset_fresh_status_record_joint_replay_v30 import (
    FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE,
    FreshStatusEvidenceRecordJointReplayResultV1,
    FreshStatusRecordJointReplayErrorCodeV1,
    RealAssetFreshStatusRecordJointReplayV30Error,
    verify_fresh_status_evidence_record_joint_replay_v1,
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

FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE: Literal[
    "creative-sample-real-asset-fresh-status-record-as-of-assessment-v1"
] = "creative-sample-real-asset-fresh-status-record-as-of-assessment-v1"
FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1: Literal[
    "EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE"
] = "EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE"

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_UTC_SECONDS = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_AS_OF_ASSESSMENT_DOMAIN = (
    b"sdc:creative-sample-real-asset-fresh-status-record-as-of-assessment:v1\0"
)
_RESULT_PROVENANCE_DOMAIN = (
    b"sdc:creative-sample-real-asset-fresh-status-record-as-of-assessment-provenance:v1\0"
)
_RESULT_PROVENANCE_CONTEXT_KEY = "fresh_status_record_as_of_assessment_verifier_provenance"
_RESULT_PROVENANCE_SENTINEL = object()

_ALL_LIMITATION_CODES: tuple[FreshStatusLimitationCodeV1, ...] = (
    "SOURCE_AUTHENTICITY_NOT_PROVEN",
    "SOURCE_COMPLETENESS_NOT_PROVEN",
    "CHAIN_COMPLETENESS_NOT_PROVEN",
    "REALITY_CURRENTNESS_NOT_PROVEN",
    "SCOPE_LIMITED_TO_DECLARED_SUBJECT",
    "TIME_WINDOW_LIMITED",
    "LEGAL_EFFECT_NOT_DETERMINED",
)

FreshStatusAsOfWindowStateV1 = Literal[
    "WITHIN_EXPLICIT_BOUND_WINDOW",
    "EXPIRED_NOT_CURRENT",
]
FreshStatusRecordAsOfAssessmentErrorCodeV1 = Literal[
    "AS_OF_CONTRACT_INVALID",
    "RECORD_JOINT_REPLAY_FAILED",
    "AS_OF_PRECEDES_RECORD_EVALUATION",
    "INTERNAL_RESULT_INCONSISTENCY",
]


class RealAssetFreshStatusRecordAsOfAssessmentV30Error(RuntimeError):
    """The pure explicit-``as_of`` Record assessment failed closed."""

    code: FreshStatusRecordAsOfAssessmentErrorCodeV1
    joint_replay_code: FreshStatusRecordJointReplayErrorCodeV1 | None
    coverage_code: FreshStatusRecordChainCoverageErrorCodeV1 | None
    replay_code: FreshStatusChainReplayErrorCodeV1 | None

    def __init__(
        self,
        code: FreshStatusRecordAsOfAssessmentErrorCodeV1,
        message: str,
        *,
        joint_replay_code: FreshStatusRecordJointReplayErrorCodeV1 | None = None,
        coverage_code: FreshStatusRecordChainCoverageErrorCodeV1 | None = None,
        replay_code: FreshStatusChainReplayErrorCodeV1 | None = None,
    ) -> None:
        self.code = code
        self.joint_replay_code = joint_replay_code
        self.coverage_code = coverage_code
        self.replay_code = replay_code
        nested = ""
        if joint_replay_code is not None:
            nested += f" (Slice 4 code: {joint_replay_code})"
        if coverage_code is not None:
            nested += f" (Slice 3 code: {coverage_code})"
        if replay_code is not None:
            nested += f" (Slice 2 code: {replay_code})"
        super().__init__(f"{code}: {message}{nested}")


class _AsOfAssessmentModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class _ZeroAuthorityAsOfAssessmentModel(_AsOfAssessmentModel):
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
        "source_record_chain_coverage_profile": (FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE),
        "source_chain_replay_profile": FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE,
        "source_evidence_profile": FRESH_STATUS_EVIDENCE_V1_PROFILE,
        "source_evidence_policy_version": FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
        "source_evidence_policy_document_sha256": (FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256),
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


def _result_provenance_sha256(value: BaseModel) -> str:
    return _sha256(
        _RESULT_PROVENANCE_DOMAIN
        + _canonical_payload(value.model_dump(mode="json", exclude_none=False))
    )


class FreshStatusEvidenceRecordAsOfAssessmentResultV1(_ZeroAuthorityAsOfAssessmentModel):
    """Non-persistent process result for one freshly replayed Record at one explicit instant."""

    _verification_provenance: tuple[object, str] | None = PrivateAttr(default=None)

    result_type: Literal["FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_RESULT_V1"] = (
        "FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_RESULT_V1"
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
    status: Literal["FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_COMPLETED"] = (
        "FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_COMPLETED"
    )

    @field_validator("as_of", "evaluated_at", "status_valid_until")
    @classmethod
    def validate_times(cls, value: str, info: object) -> str:
        name = getattr(info, "field_name", None) or "Fresh Status assessment timestamp"
        return _utc_seconds(value, field=name)

    @model_validator(mode="after")
    def validate_result(
        self,
        info: ValidationInfo,
    ) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
        evaluated_at = _parse_utc(self.evaluated_at)
        status_valid_until = _parse_utc(self.status_valid_until)
        as_of = _parse_utc(self.as_of)
        if status_valid_until < evaluated_at:
            raise ValueError("status_valid_until cannot predate evaluated_at")
        if as_of < evaluated_at:
            raise ValueError("as_of cannot predate evaluated_at in an assessment result")
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
            raise ValueError("as-of assessment must retain all seven limitation codes")

        expected_digest = _as_of_assessment_sha256(
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
        if self.as_of_assessment_sha256 != expected_digest:
            raise ValueError("as_of_assessment_sha256 drifted from the exact assessment projection")
        if (
            not isinstance(info.context, dict)
            or info.context.get(_RESULT_PROVENANCE_CONTEXT_KEY) is not _RESULT_PROVENANCE_SENTINEL
        ):
            raise ValueError("as-of assessment results may be constructed only by the verifier")
        self._verification_provenance = (
            _RESULT_PROVENANCE_SENTINEL,
            _result_provenance_sha256(self),
        )
        return self


def _raise(
    code: FreshStatusRecordAsOfAssessmentErrorCodeV1,
    message: str,
    *,
    joint_replay_code: FreshStatusRecordJointReplayErrorCodeV1 | None = None,
    coverage_code: FreshStatusRecordChainCoverageErrorCodeV1 | None = None,
    replay_code: FreshStatusChainReplayErrorCodeV1 | None = None,
) -> Never:
    raise RealAssetFreshStatusRecordAsOfAssessmentV30Error(
        code,
        message,
        joint_replay_code=joint_replay_code,
        coverage_code=coverage_code,
        replay_code=replay_code,
    )


def _require_result_provenance(
    value: FreshStatusEvidenceRecordAsOfAssessmentResultV1,
) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
    provenance = value._verification_provenance
    expected = (_RESULT_PROVENANCE_SENTINEL, _result_provenance_sha256(value))
    if (
        provenance is None
        or provenance[0] is not _RESULT_PROVENANCE_SENTINEL
        or provenance != expected
    ):
        _raise(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the as-of assessment result lacks verifier-bound in-memory provenance",
        )
    return value


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


def _require_joint_anchors(
    *,
    joint_replay: FreshStatusEvidenceRecordJointReplayResultV1,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    evidence_record_sha256: str,
    decision_sha256: str,
) -> None:
    if type(joint_replay) is not FreshStatusEvidenceRecordJointReplayResultV1:
        _raise(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the public Slice 4 verifier returned an unexpected result type",
        )
    if (
        joint_replay.evidence_record_id != record.record_id
        or joint_replay.evidence_record_sha256 != evidence_record_sha256
        or joint_replay.request_id != record.request.request_id
        or joint_replay.request_sha256 != record.request_sha256
        or joint_replay.subject_closure != record.subject_closure
        or record.decision_sha256 != decision_sha256
    ):
        _raise(
            "INTERNAL_RESULT_INCONSISTENCY",
            "fresh Slice 4 replay and the supplied Record disagree on assessment anchors",
        )


def assess_fresh_status_evidence_record_as_of_v1(
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
) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
    """Freshly replay one complete Record closure and assess its window at explicit ``as_of``."""

    try:
        as_of = _utc_seconds(as_of, field="as_of")
        parsed_as_of = _parse_utc(as_of)
    except (TypeError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentV30Error(
            "AS_OF_CONTRACT_INVALID",
            "as_of must be one exact valid canonical UTC-seconds string",
        ) from exc

    try:
        joint_replay = verify_fresh_status_evidence_record_joint_replay_v1(
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
        )
    except RealAssetFreshStatusRecordJointReplayV30Error as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentV30Error(
            "RECORD_JOINT_REPLAY_FAILED",
            "the Record failed the public Slice 4 joint replay verifier",
            joint_replay_code=exc.code,
            coverage_code=exc.coverage_code,
            replay_code=exc.replay_code,
        ) from exc

    try:
        evidence_record_sha256 = _sha256(_canonical_document(record))
        decision_sha256 = _sha256(_canonical_document(record.decision))
        _require_joint_anchors(
            joint_replay=joint_replay,
            record=record,
            evidence_record_sha256=evidence_record_sha256,
            decision_sha256=decision_sha256,
        )
        evaluated_at = _utc_seconds(record.decision.evaluated_at, field="evaluated_at")
        status_valid_until = _utc_seconds(
            record.decision.status_valid_until,
            field="status_valid_until",
        )
        parsed_evaluated_at = _parse_utc(evaluated_at)
        parsed_status_valid_until = _parse_utc(status_valid_until)
        if parsed_status_valid_until < parsed_evaluated_at:
            _raise(
                "INTERNAL_RESULT_INCONSISTENCY",
                "the freshly replayed Record has an impossible Decision horizon",
            )
    except RealAssetFreshStatusRecordAsOfAssessmentV30Error:
        raise
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentV30Error(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the freshly replayed Record could not yield exact assessment anchors",
        ) from exc

    if parsed_as_of < parsed_evaluated_at:
        _raise(
            "AS_OF_PRECEDES_RECORD_EVALUATION",
            "as_of predates the Record's explicit evaluation instant",
        )

    as_of_window_state: FreshStatusAsOfWindowStateV1 = (
        "WITHIN_EXPLICIT_BOUND_WINDOW"
        if parsed_as_of < parsed_status_valid_until
        else "EXPIRED_NOT_CURRENT"
    )

    try:
        as_of_assessment_sha256 = _as_of_assessment_sha256(
            evidence_record_id=record.record_id,
            evidence_record_sha256=evidence_record_sha256,
            request_id=record.request.request_id,
            request_sha256=record.request_sha256,
            decision_id=record.decision.decision_id,
            decision_sha256=decision_sha256,
            subject_closure=record.subject_closure,
            coverage_set_sha256=joint_replay.coverage_set_sha256,
            joint_replay_sha256=joint_replay.joint_replay_sha256,
            as_of=as_of,
            evaluated_at=evaluated_at,
            status_valid_until=status_valid_until,
            window_semantics=FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1,
            recorded_disposition=record.decision.disposition,
            recorded_blocking_categories=record.decision.blocking_categories,
            recorded_indeterminate_categories=record.decision.indeterminate_categories,
            as_of_window_state=as_of_window_state,
        )
        result = FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_validate(
            {
                "evidence_record_id": record.record_id,
                "evidence_record_sha256": evidence_record_sha256,
                "request_id": record.request.request_id,
                "request_sha256": record.request_sha256,
                "decision_id": record.decision.decision_id,
                "decision_sha256": decision_sha256,
                "subject_closure": record.subject_closure,
                "coverage_set_sha256": joint_replay.coverage_set_sha256,
                "joint_replay_sha256": joint_replay.joint_replay_sha256,
                "as_of": as_of,
                "evaluated_at": evaluated_at,
                "status_valid_until": status_valid_until,
                "window_semantics": FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1,
                "recorded_disposition": record.decision.disposition,
                "recorded_blocking_categories": record.decision.blocking_categories,
                "recorded_indeterminate_categories": record.decision.indeterminate_categories,
                "as_of_window_state": as_of_window_state,
                "as_of_assessment_sha256": as_of_assessment_sha256,
                "provided_record_joint_replay_consistent": True,
                "explicit_as_of_window_assessment_consistent": True,
                "limitation_codes": _ALL_LIMITATION_CODES,
                **_zero_authority_payload(),
            },
            strict=True,
            context={_RESULT_PROVENANCE_CONTEXT_KEY: _RESULT_PROVENANCE_SENTINEL},
        )
    except RealAssetFreshStatusRecordAsOfAssessmentV30Error:
        raise
    except (AttributeError, TypeError, UnicodeError, ValidationError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentV30Error(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the derived non-persistent as-of assessment result is internally inconsistent",
        ) from exc
    return _require_result_provenance(result)


__all__ = [
    "FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE",
    "FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1",
    "FreshStatusAsOfWindowStateV1",
    "FreshStatusRecordAsOfAssessmentErrorCodeV1",
    "FreshStatusEvidenceRecordAsOfAssessmentResultV1",
    "RealAssetFreshStatusRecordAsOfAssessmentV30Error",
    "assess_fresh_status_evidence_record_as_of_v1",
]
