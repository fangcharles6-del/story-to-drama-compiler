"""Pure joint closure and explicit-chain replay for one Fresh Status Record v3.0.

This module composes the public Slice 3 chain-coverage verifier with the public Slice 1
upstream-closure verifier in one in-memory call.  It performs no filesystem, path, CLI,
network, Provider, environment-time, wall-clock, persistence, credential, or execution
operation.  Success proves only consistency of the exact objects and explicit finite chains
provided to this invocation; it grants no authority and makes no global or currentness claim.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal, Never

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationError,
    ValidationInfo,
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
    FRESH_STATUS_MAX_CHAIN_RECORDS,
    FRESH_STATUS_MAX_OBSERVATIONS,
    CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    CreativeSampleRealAssetFreshStatusSourceObservationV1,
    FreshStatusLimitationCodeV1,
    FreshStatusObservationRefV1,
    FreshStatusSubjectClosureV1,
    RealAssetFreshStatusEvidenceV30Error,
    derive_fresh_status_observation_chain_sha256_v1,
    verify_fresh_status_evidence_record_closure_v1,
)
from sdc.real_asset_fresh_status_record_chain_coverage_v30 import (
    FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE,
    FreshStatusEvidenceRecordChainCoverageResultV1,
    FreshStatusRecordChainCoverageErrorCodeV1,
    FreshStatusRecordChainInputV1,
    RealAssetFreshStatusRecordChainCoverageV30Error,
    verify_fresh_status_evidence_record_explicit_chain_coverage_v1,
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
from sdc.real_asset_use_plan_v26 import (
    CreativeSampleRealAssetUsePlanV1,
    RealAssetUsePlanV26Error,
)
from sdc.real_asset_use_scope_review_v26 import (
    CreativeSampleRealAssetUseScopeReviewRecordV1,
    RealAssetUseScopeReviewV26Error,
)

FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE: Literal[
    "creative-sample-real-asset-fresh-status-record-joint-replay-v1"
] = "creative-sample-real-asset-fresh-status-record-joint-replay-v1"

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_JOINT_REPLAY_DOMAIN = b"sdc:creative-sample-real-asset-fresh-status-record-joint-replay-set:v1\0"
_RESULT_PROVENANCE_DOMAIN = (
    b"sdc:creative-sample-real-asset-fresh-status-record-joint-replay-provenance:v1\0"
)
_RESULT_PROVENANCE_CONTEXT_KEY = "fresh_status_record_joint_replay_verifier_provenance"
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

FreshStatusRecordJointReplayErrorCodeV1 = Literal[
    "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
    "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
    "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
    "INTERNAL_RESULT_INCONSISTENCY",
]


class RealAssetFreshStatusRecordJointReplayV30Error(RuntimeError):
    """The pure joint Record replay failed closed."""

    code: FreshStatusRecordJointReplayErrorCodeV1
    coverage_code: FreshStatusRecordChainCoverageErrorCodeV1 | None
    replay_code: FreshStatusChainReplayErrorCodeV1 | None

    def __init__(
        self,
        code: FreshStatusRecordJointReplayErrorCodeV1,
        message: str,
        *,
        coverage_code: FreshStatusRecordChainCoverageErrorCodeV1 | None = None,
        replay_code: FreshStatusChainReplayErrorCodeV1 | None = None,
    ) -> None:
        self.code = code
        self.coverage_code = coverage_code
        self.replay_code = replay_code
        nested = ""
        if coverage_code is not None:
            nested += f" (Slice 3 code: {coverage_code})"
        if replay_code is not None:
            nested += f" (Slice 2 code: {replay_code})"
        super().__init__(f"{code}: {message}{nested}")


class _JointReplayModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class _ZeroAuthorityJointReplayModel(_JointReplayModel):
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


_FullRefKey = tuple[str, str, str, str, str]


def _full_ref_key(item: FreshStatusObservationRefV1) -> _FullRefKey:
    return (
        item.observation_id,
        item.observation_sha256,
        item.status_category,
        item.source_identity_ref_sha256,
        item.chain_sha256,
    )


def _observation_full_ref_key(
    item: CreativeSampleRealAssetFreshStatusSourceObservationV1,
) -> _FullRefKey:
    return (
        item.observation_id,
        _sha256(_canonical_document(item)),
        item.status_category,
        item.source_identity_ref_sha256,
        derive_fresh_status_observation_chain_sha256_v1(item),
    )


def _joint_replay_sha256(
    *,
    evidence_record_id: str,
    evidence_record_sha256: str,
    request_id: str,
    request_sha256: str,
    subject_closure: FreshStatusSubjectClosureV1,
    request_observation_count: int,
    chain_count: int,
    covered_request_observation_count: int,
    provided_observation_count: int,
    supporting_ancestor_observation_count: int,
    coverage_set_sha256: str,
) -> str:
    projection = {
        "joint_replay_profile": FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE,
        "source_record_chain_coverage_profile": (FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE),
        "source_chain_replay_profile": FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE,
        "source_evidence_profile": FRESH_STATUS_EVIDENCE_V1_PROFILE,
        "source_evidence_policy_version": FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
        "source_evidence_policy_document_sha256": (FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256),
        "evidence_record_id": evidence_record_id,
        "evidence_record_sha256": evidence_record_sha256,
        "request_id": request_id,
        "request_sha256": request_sha256,
        "subject_closure": subject_closure,
        "request_observation_count": request_observation_count,
        "chain_count": chain_count,
        "covered_request_observation_count": covered_request_observation_count,
        "provided_observation_count": provided_observation_count,
        "supporting_ancestor_observation_count": supporting_ancestor_observation_count,
        "coverage_set_sha256": coverage_set_sha256,
    }
    return _sha256(_JOINT_REPLAY_DOMAIN + _canonical_payload(projection))


def _result_provenance_sha256(value: BaseModel) -> str:
    return _sha256(
        _RESULT_PROVENANCE_DOMAIN
        + _canonical_payload(value.model_dump(mode="json", exclude_none=False))
    )


class FreshStatusEvidenceRecordJointReplayResultV1(_ZeroAuthorityJointReplayModel):
    """Non-persistent process result for one freshly joined Slice 3 and Slice 1 replay."""

    _verification_provenance: tuple[object, str] | None = PrivateAttr(default=None)

    result_type: Literal["FRESH_STATUS_EVIDENCE_RECORD_JOINT_REPLAY_RESULT_V1"] = (
        "FRESH_STATUS_EVIDENCE_RECORD_JOINT_REPLAY_RESULT_V1"
    )
    joint_replay_profile: Literal[
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
    subject_closure: FreshStatusSubjectClosureV1
    request_observation_count: int = Field(ge=1, le=FRESH_STATUS_MAX_OBSERVATIONS)
    chain_count: int = Field(ge=1, le=FRESH_STATUS_MAX_OBSERVATIONS)
    covered_request_observation_count: int = Field(ge=1, le=FRESH_STATUS_MAX_OBSERVATIONS)
    provided_observation_count: int = Field(
        ge=1,
        le=FRESH_STATUS_MAX_OBSERVATIONS * FRESH_STATUS_MAX_CHAIN_RECORDS,
    )
    supporting_ancestor_observation_count: int = Field(
        ge=0,
        le=FRESH_STATUS_MAX_OBSERVATIONS * FRESH_STATUS_MAX_CHAIN_RECORDS,
    )
    coverage_set_sha256: str = Field(pattern=_LOWER_SHA256)
    joint_replay_sha256: str = Field(pattern=_LOWER_SHA256)
    provided_upstream_object_closure_consistent: Literal[True] = True
    provided_evidence_record_request_explicit_chain_coverage_consistent: Literal[True] = True
    provided_evidence_record_rebuild_consistent: Literal[True] = True
    limitation_codes: tuple[FreshStatusLimitationCodeV1, ...] = _ALL_LIMITATION_CODES
    status: Literal["FRESH_STATUS_EVIDENCE_RECORD_JOINT_REPLAY_CONSISTENT"] = (
        "FRESH_STATUS_EVIDENCE_RECORD_JOINT_REPLAY_CONSISTENT"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_exact_integers(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        for field in (
            "request_observation_count",
            "chain_count",
            "covered_request_observation_count",
            "provided_observation_count",
            "supporting_ancestor_observation_count",
        ):
            if field in value and type(value[field]) is not int:
                raise ValueError(f"{field} must be an exact JSON integer")
        return value

    @model_validator(mode="after")
    def validate_result(
        self,
        info: ValidationInfo,
    ) -> FreshStatusEvidenceRecordJointReplayResultV1:
        if self.request_observation_count != self.covered_request_observation_count:
            raise ValueError("covered Request count drifted from the Request count")
        if self.provided_observation_count != (
            self.covered_request_observation_count + self.supporting_ancestor_observation_count
        ):
            raise ValueError("provided Observation count drifted from target and ancestor counts")
        if self.limitation_codes != _ALL_LIMITATION_CODES:
            raise ValueError("joint replay must retain all seven limitation codes")
        expected_digest = _joint_replay_sha256(
            evidence_record_id=self.evidence_record_id,
            evidence_record_sha256=self.evidence_record_sha256,
            request_id=self.request_id,
            request_sha256=self.request_sha256,
            subject_closure=self.subject_closure,
            request_observation_count=self.request_observation_count,
            chain_count=self.chain_count,
            covered_request_observation_count=self.covered_request_observation_count,
            provided_observation_count=self.provided_observation_count,
            supporting_ancestor_observation_count=(self.supporting_ancestor_observation_count),
            coverage_set_sha256=self.coverage_set_sha256,
        )
        if self.joint_replay_sha256 != expected_digest:
            raise ValueError("joint_replay_sha256 drifted from the exact joint projection")
        if (
            not isinstance(info.context, dict)
            or info.context.get(_RESULT_PROVENANCE_CONTEXT_KEY) is not _RESULT_PROVENANCE_SENTINEL
        ):
            raise ValueError("joint replay results may be constructed only by the verifier")
        self._verification_provenance = (
            _RESULT_PROVENANCE_SENTINEL,
            _result_provenance_sha256(self),
        )
        return self


def _raise(
    code: FreshStatusRecordJointReplayErrorCodeV1,
    message: str,
    *,
    coverage_code: FreshStatusRecordChainCoverageErrorCodeV1 | None = None,
    replay_code: FreshStatusChainReplayErrorCodeV1 | None = None,
) -> Never:
    raise RealAssetFreshStatusRecordJointReplayV30Error(
        code,
        message,
        coverage_code=coverage_code,
        replay_code=replay_code,
    )


def _require_result_provenance(
    value: FreshStatusEvidenceRecordJointReplayResultV1,
) -> FreshStatusEvidenceRecordJointReplayResultV1:
    provenance = value._verification_provenance
    expected = (_RESULT_PROVENANCE_SENTINEL, _result_provenance_sha256(value))
    if (
        provenance is None
        or provenance[0] is not _RESULT_PROVENANCE_SENTINEL
        or provenance != expected
    ):
        _raise(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the joint replay result lacks verifier-bound in-memory provenance",
        )
    return value


def _derive_request_target_observations(
    *,
    request_observation_refs: tuple[FreshStatusObservationRefV1, ...],
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...]:
    """Derive only exact five-field Request targets from the freshly replayed chains."""

    try:
        request_keys = tuple(_full_ref_key(item) for item in request_observation_refs)
        targets: dict[_FullRefKey, CreativeSampleRealAssetFreshStatusSourceObservationV1] = {}
        for chain in chains:
            observations_by_key: dict[
                _FullRefKey,
                CreativeSampleRealAssetFreshStatusSourceObservationV1,
            ] = {}
            for observation in chain.observations:
                observation_key = _observation_full_ref_key(observation)
                if observation_key in observations_by_key:
                    _raise(
                        "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
                        "one chain resolves the same exact Observation anchor more than once",
                    )
                observations_by_key[observation_key] = observation
            for target_ref in chain.request_target_refs:
                target_key = _full_ref_key(target_ref)
                resolved_observation = observations_by_key.get(target_key)
                if resolved_observation is None:
                    _raise(
                        "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
                        "a declared Request target does not resolve by all five reference fields",
                    )
                if target_key in targets:
                    _raise(
                        "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
                        "one exact Request target resolves more than once",
                    )
                targets[target_key] = resolved_observation
        if (
            len(request_keys) != len(set(request_keys))
            or set(targets) != set(request_keys)
            or len(targets) != len(request_keys)
        ):
            _raise(
                "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
                "derived target Observations do not equal the exact Record Request set",
            )
        return tuple(targets[key] for key in request_keys)
    except RealAssetFreshStatusRecordJointReplayV30Error:
        raise
    except (
        RealAssetFreshStatusEvidenceV30Error,
        AttributeError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        raise RealAssetFreshStatusRecordJointReplayV30Error(
            "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
            "Request target Observations could not be derived by exact five-field anchors",
        ) from exc


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
    coverage: FreshStatusEvidenceRecordChainCoverageResultV1,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    evidence_record_sha256: str,
) -> None:
    if (
        coverage.evidence_record_id != record.record_id
        or coverage.evidence_record_sha256 != evidence_record_sha256
        or coverage.request_id != record.request.request_id
        or coverage.request_sha256 != record.request_sha256
        or coverage.subject_closure != record.subject_closure
        or coverage.request_observation_count != len(record.request.observation_refs)
    ):
        _raise(
            "INTERNAL_RESULT_INCONSISTENCY",
            "fresh Slice 3 and Slice 1 results disagree on their joint Record anchors",
        )


def verify_fresh_status_evidence_record_joint_replay_v1(
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
) -> FreshStatusEvidenceRecordJointReplayResultV1:
    """Freshly replay exact chain coverage and the complete provided upstream closure."""

    try:
        coverage = verify_fresh_status_evidence_record_explicit_chain_coverage_v1(
            record=record,
            chains=chains,
        )
    except RealAssetFreshStatusRecordChainCoverageV30Error as exc:
        raise RealAssetFreshStatusRecordJointReplayV30Error(
            "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
            "the Record failed the public Slice 3 explicit-chain coverage verifier",
            coverage_code=exc.code,
            replay_code=exc.replay_code,
        ) from exc

    target_observations = _derive_request_target_observations(
        request_observation_refs=coverage.request_observation_refs,
        chains=chains,
    )

    try:
        verified_record = verify_fresh_status_evidence_record_closure_v1(
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
            observations=target_observations,
            record=record,
        )
    except (
        RealAssetFreshStatusEvidenceV30Error,
        RealAssetUseScopeReviewV26Error,
        RealAssetUsePlanV26Error,
        AttributeError,
        TypeError,
        ValidationError,
        ValueError,
    ) as exc:
        raise RealAssetFreshStatusRecordJointReplayV30Error(
            "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
            "the exact provided upstream objects failed the public Slice 1 closure verifier",
        ) from exc

    try:
        evidence_record_sha256 = _sha256(_canonical_document(verified_record))
        _require_joint_anchors(
            coverage=coverage,
            record=verified_record,
            evidence_record_sha256=evidence_record_sha256,
        )
        joint_replay_sha256 = _joint_replay_sha256(
            evidence_record_id=verified_record.record_id,
            evidence_record_sha256=evidence_record_sha256,
            request_id=verified_record.request.request_id,
            request_sha256=verified_record.request_sha256,
            subject_closure=verified_record.subject_closure,
            request_observation_count=coverage.request_observation_count,
            chain_count=coverage.chain_count,
            covered_request_observation_count=(coverage.covered_request_observation_count),
            provided_observation_count=coverage.provided_observation_count,
            supporting_ancestor_observation_count=(coverage.supporting_ancestor_observation_count),
            coverage_set_sha256=coverage.coverage_set_sha256,
        )
        result = FreshStatusEvidenceRecordJointReplayResultV1.model_validate(
            {
                "evidence_record_id": verified_record.record_id,
                "evidence_record_sha256": evidence_record_sha256,
                "request_id": verified_record.request.request_id,
                "request_sha256": verified_record.request_sha256,
                "subject_closure": verified_record.subject_closure,
                "request_observation_count": coverage.request_observation_count,
                "chain_count": coverage.chain_count,
                "covered_request_observation_count": (coverage.covered_request_observation_count),
                "provided_observation_count": coverage.provided_observation_count,
                "supporting_ancestor_observation_count": (
                    coverage.supporting_ancestor_observation_count
                ),
                "coverage_set_sha256": coverage.coverage_set_sha256,
                "joint_replay_sha256": joint_replay_sha256,
                "provided_upstream_object_closure_consistent": True,
                "provided_evidence_record_request_explicit_chain_coverage_consistent": True,
                "provided_evidence_record_rebuild_consistent": True,
                "limitation_codes": _ALL_LIMITATION_CODES,
                **_zero_authority_payload(),
            },
            strict=True,
            context={_RESULT_PROVENANCE_CONTEXT_KEY: _RESULT_PROVENANCE_SENTINEL},
        )
    except RealAssetFreshStatusRecordJointReplayV30Error:
        raise
    except (AttributeError, TypeError, UnicodeError, ValidationError, ValueError) as exc:
        raise RealAssetFreshStatusRecordJointReplayV30Error(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the derived non-persistent joint replay result is internally inconsistent",
        ) from exc
    return _require_result_provenance(result)


__all__ = [
    "FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE",
    "FreshStatusRecordJointReplayErrorCodeV1",
    "FreshStatusEvidenceRecordJointReplayResultV1",
    "RealAssetFreshStatusRecordJointReplayV30Error",
    "verify_fresh_status_evidence_record_joint_replay_v1",
]
