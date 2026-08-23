"""Pure explicit multi-chain coverage for one Fresh Status Evidence Record v3.0.

This module verifies only exact, caller-grouped, in-memory Source Observation sets.  It
performs no filesystem, path, network, Provider, environment-time, wall-clock, persistence,
or execution operation.  Success proves only that the exact Request references in one exact
Evidence Record are covered once by the declared target/ancestor closures and that every
declared chain passed the public Slice 2 verifier.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
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
    FreshStatusExplicitFiniteChainReplayResultV1,
    FreshStatusProvidedSetTerminalShapeV1,
    RealAssetFreshStatusChainReplayV30Error,
    verify_fresh_status_explicit_finite_source_chain_v1,
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
    FreshStatusCategoryV1,
    FreshStatusLimitationCodeV1,
    FreshStatusObservationRefV1,
    FreshStatusSourceKindV1,
    FreshStatusSubjectClosureV1,
    RealAssetFreshStatusEvidenceV30Error,
    build_fresh_status_evidence_record_v1,
    build_fresh_status_instruction_v1,
    build_fresh_status_request_v1,
    verify_fresh_status_evidence_record_internal_v1,
)

FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE: Literal[
    "creative-sample-real-asset-fresh-status-record-chain-coverage-v1"
] = "creative-sample-real-asset-fresh-status-record-chain-coverage-v1"
FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES = 16_777_216

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_COVERAGE_SET_DOMAIN = b"sdc:creative-sample-real-asset-fresh-status-record-chain-coverage-set:v1\0"
_RESULT_PROVENANCE_DOMAIN = (
    b"sdc:creative-sample-real-asset-fresh-status-record-chain-coverage-provenance:v1\0"
)
_RESULT_PROVENANCE_CONTEXT_KEY = "fresh_status_record_chain_coverage_verifier_provenance"
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

FreshStatusRecordChainCoverageErrorCodeV1 = Literal[
    "CHAIN_COLLECTION_CONTRACT_INVALID",
    "CHAIN_COUNT_OUT_OF_RANGE",
    "CHAIN_INPUT_CONTRACT_INVALID",
    "TARGET_COUNT_OUT_OF_RANGE",
    "OBSERVATION_COUNT_OUT_OF_RANGE",
    "AGGREGATE_CANONICAL_BYTES_OUT_OF_RANGE",
    "EVIDENCE_RECORD_INVALID",
    "REQUEST_TARGET_COVERED_MULTIPLE_TIMES",
    "REQUEST_TARGET_ANCHOR_MISMATCH",
    "REQUEST_TARGET_NOT_IN_RECORD",
    "REQUEST_OBSERVATION_NOT_COVERED",
    "CHAIN_REPLAY_FAILED",
    "DUPLICATE_LOGICAL_CHAIN",
    "CROSS_CHAIN_DUPLICATE_OBSERVATION_ID",
    "CROSS_CHAIN_DUPLICATE_OBSERVATION_DOCUMENT_SHA256",
    "CROSS_CHAIN_DUPLICATE_OBSERVATION_CHAIN_SHA256",
    "CROSS_CHAIN_DUPLICATE_OBSERVATION_SET_SHA256",
    "REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN",
    "CHAIN_TARGET_SET_MISMATCH",
    "UNRELATED_SUPPORT_OBSERVATION",
    "RECORD_REBUILD_MISMATCH",
    "INTERNAL_RESULT_INCONSISTENCY",
]


class RealAssetFreshStatusRecordChainCoverageV30Error(RuntimeError):
    """The pure explicit Evidence Record chain-coverage verifier failed closed."""

    code: FreshStatusRecordChainCoverageErrorCodeV1
    replay_code: FreshStatusChainReplayErrorCodeV1 | None

    def __init__(
        self,
        code: FreshStatusRecordChainCoverageErrorCodeV1,
        message: str,
        *,
        replay_code: FreshStatusChainReplayErrorCodeV1 | None = None,
    ) -> None:
        self.code = code
        self.replay_code = replay_code
        suffix = f" (Slice 2 code: {replay_code})" if replay_code is not None else ""
        super().__init__(f"{code}: {message}{suffix}")


class _CoverageModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class _ZeroAuthorityCoverageModel(_CoverageModel):
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


class FreshStatusRecordChainInputV1(_CoverageModel):
    """Non-persistent caller grouping for one explicit source chain and its Request targets."""

    status_category: FreshStatusCategoryV1
    source_kind: FreshStatusSourceKindV1
    source_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    request_target_refs: tuple[FreshStatusObservationRefV1, ...]
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...]


def _ref_key(item: FreshStatusObservationRefV1) -> tuple[str, str, str]:
    return item.observation_id, item.observation_sha256, item.chain_sha256


def _full_ref_key(item: FreshStatusObservationRefV1) -> tuple[str, str, str, str, str]:
    return (
        item.observation_id,
        item.observation_sha256,
        item.status_category,
        item.source_identity_ref_sha256,
        item.chain_sha256,
    )


def _summary_key(
    value: FreshStatusRecordChainCoverageSummaryV1,
) -> tuple[str, str, str, str, str, str, str]:
    return (
        value.status_category,
        value.source_kind,
        value.source_identity_ref_sha256,
        value.genesis_ref.observation_id,
        value.genesis_ref.observation_sha256,
        value.genesis_ref.chain_sha256,
        value.observation_set_sha256,
    )


class FreshStatusRecordChainCoverageSummaryV1(_CoverageModel):
    """Derived non-persistent projection of one freshly replayed explicit source chain."""

    status_category: FreshStatusCategoryV1
    source_kind: FreshStatusSourceKindV1
    source_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    observation_count: int = Field(ge=1, le=FRESH_STATUS_MAX_CHAIN_RECORDS)
    observation_set_sha256: str = Field(pattern=_LOWER_SHA256)
    observation_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        min_length=1,
        max_length=FRESH_STATUS_MAX_CHAIN_RECORDS,
    )
    genesis_ref: FreshStatusObservationRefV1
    provided_set_fork_point_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        max_length=FRESH_STATUS_MAX_CHAIN_RECORDS
    )
    provided_set_terminal_head_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        min_length=1,
        max_length=FRESH_STATUS_MAX_CHAIN_RECORDS,
    )
    provided_set_terminal_shape: FreshStatusProvidedSetTerminalShapeV1
    request_target_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        min_length=1,
        max_length=FRESH_STATUS_MAX_OBSERVATIONS,
    )
    supporting_ancestor_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        max_length=FRESH_STATUS_MAX_CHAIN_RECORDS
    )
    provided_explicit_finite_chain_closure_consistent: Literal[True] = True

    @model_validator(mode="before")
    @classmethod
    def validate_exact_integer(cls, value: object) -> object:
        if isinstance(value, dict) and "observation_count" in value:
            count = value["observation_count"]
            if type(count) is not int:
                raise ValueError("observation_count must be an exact JSON integer")
        return value

    @model_validator(mode="after")
    def validate_summary(self) -> FreshStatusRecordChainCoverageSummaryV1:
        ref_keys = tuple(_ref_key(item) for item in self.observation_refs)
        ids = tuple(item.observation_id for item in self.observation_refs)
        document_digests = tuple(item.observation_sha256 for item in self.observation_refs)
        chain_digests = tuple(item.chain_sha256 for item in self.observation_refs)
        if (
            len(ref_keys) != len(set(ref_keys))
            or len(ids) != len(set(ids))
            or len(document_digests) != len(set(document_digests))
            or len(chain_digests) != len(set(chain_digests))
            or ref_keys != tuple(sorted(ref_keys))
        ):
            raise ValueError("observation_refs must be independently unique and sorted")
        if self.observation_count != len(self.observation_refs):
            raise ValueError("observation_count drifted from observation_refs")
        if any(
            item.status_category != self.status_category
            or item.source_identity_ref_sha256 != self.source_identity_ref_sha256
            for item in self.observation_refs
        ):
            raise ValueError("observation_refs drifted from the chain scope")
        by_key = {_full_ref_key(item): item for item in self.observation_refs}
        for label, subset in (
            ("genesis_ref", (self.genesis_ref,)),
            ("provided_set_fork_point_refs", self.provided_set_fork_point_refs),
            ("provided_set_terminal_head_refs", self.provided_set_terminal_head_refs),
            ("request_target_refs", self.request_target_refs),
            ("supporting_ancestor_refs", self.supporting_ancestor_refs),
        ):
            keys = tuple(_full_ref_key(item) for item in subset)
            if len(keys) != len(set(keys)) or keys != tuple(sorted(keys)):
                raise ValueError(f"{label} must be unique and canonically sorted")
            if any(by_key.get(key) != item for key, item in zip(keys, subset, strict=True)):
                raise ValueError(f"{label} must be an exact subset of observation_refs")
        target_keys = {_full_ref_key(item) for item in self.request_target_refs}
        support_keys = {_full_ref_key(item) for item in self.supporting_ancestor_refs}
        if target_keys & support_keys or target_keys | support_keys != set(by_key):
            raise ValueError("target and supporting refs must partition observation_refs")
        if (
            not {_full_ref_key(item) for item in self.provided_set_terminal_head_refs}
            <= target_keys
        ):
            raise ValueError("every provided-set terminal must be an explicit Request target")
        expected_shape: FreshStatusProvidedSetTerminalShapeV1 = (
            "SINGLE_TERMINAL_HEAD"
            if len(self.provided_set_terminal_head_refs) == 1
            else "MULTIPLE_TERMINAL_HEADS"
        )
        if self.provided_set_terminal_shape != expected_shape:
            raise ValueError("provided-set terminal shape drifted from terminal refs")
        return self


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
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_document(value: BaseModel) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _coverage_set_sha256(
    *,
    evidence_record_id: str,
    evidence_record_sha256: str,
    request_id: str,
    request_sha256: str,
    subject_closure: FreshStatusSubjectClosureV1,
    request_observation_count: int,
    request_observation_refs: tuple[FreshStatusObservationRefV1, ...],
    chain_count: int,
    chain_coverages: tuple[FreshStatusRecordChainCoverageSummaryV1, ...],
    covered_request_observation_count: int,
    provided_observation_count: int,
    supporting_ancestor_observation_count: int,
) -> str:
    payload = {
        "coverage_profile": FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE,
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
        "request_observation_refs": request_observation_refs,
        "chain_count": chain_count,
        "chain_coverages": chain_coverages,
        "covered_request_observation_count": covered_request_observation_count,
        "provided_observation_count": provided_observation_count,
        "supporting_ancestor_observation_count": supporting_ancestor_observation_count,
    }
    return _sha256(_COVERAGE_SET_DOMAIN + _canonical_payload(payload))


def _result_provenance_sha256(value: BaseModel) -> str:
    return _sha256(
        _RESULT_PROVENANCE_DOMAIN
        + _canonical_payload(value.model_dump(mode="json", exclude_none=False))
    )


class FreshStatusEvidenceRecordChainCoverageResultV1(_ZeroAuthorityCoverageModel):
    """Non-persistent process result for one exact Record and explicit chain collection."""

    _verification_provenance: tuple[object, str] | None = PrivateAttr(default=None)

    result_type: Literal["FRESH_STATUS_EVIDENCE_RECORD_CHAIN_COVERAGE_RESULT_V1"] = (
        "FRESH_STATUS_EVIDENCE_RECORD_CHAIN_COVERAGE_RESULT_V1"
    )
    coverage_profile: Literal[
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
    request_observation_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        min_length=1,
        max_length=FRESH_STATUS_MAX_OBSERVATIONS,
    )
    chain_count: int = Field(ge=1, le=FRESH_STATUS_MAX_OBSERVATIONS)
    chain_coverages: tuple[FreshStatusRecordChainCoverageSummaryV1, ...] = Field(
        min_length=1,
        max_length=FRESH_STATUS_MAX_OBSERVATIONS,
    )
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
    provided_evidence_record_request_explicit_chain_coverage_consistent: Literal[True] = True
    provided_evidence_record_rebuild_consistent: Literal[True] = True
    limitation_codes: tuple[FreshStatusLimitationCodeV1, ...] = _ALL_LIMITATION_CODES
    status: Literal["FRESH_STATUS_EVIDENCE_RECORD_CHAIN_COVERAGE_CONSISTENT"] = (
        "FRESH_STATUS_EVIDENCE_RECORD_CHAIN_COVERAGE_CONSISTENT"
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
    ) -> FreshStatusEvidenceRecordChainCoverageResultV1:
        request_keys = tuple(_full_ref_key(item) for item in self.request_observation_refs)
        request_ids = tuple(item.observation_id for item in self.request_observation_refs)
        request_documents = tuple(item.observation_sha256 for item in self.request_observation_refs)
        request_chains = tuple(item.chain_sha256 for item in self.request_observation_refs)
        if (
            len(request_keys) != len(set(request_keys))
            or len(request_ids) != len(set(request_ids))
            or len(request_documents) != len(set(request_documents))
            or len(request_chains) != len(set(request_chains))
            or request_keys != tuple(sorted(request_keys))
        ):
            raise ValueError("request_observation_refs must be independently unique and sorted")
        if self.request_observation_count != len(self.request_observation_refs):
            raise ValueError("request_observation_count drifted from request refs")
        if self.chain_count != len(self.chain_coverages):
            raise ValueError("chain_count drifted from chain_coverages")
        if tuple(sorted(self.chain_coverages, key=_summary_key)) != self.chain_coverages:
            raise ValueError("chain_coverages must use canonical chain order")

        logical_keys = tuple(
            (
                item.status_category,
                item.source_kind,
                item.source_identity_ref_sha256,
                _full_ref_key(item.genesis_ref),
            )
            for item in self.chain_coverages
        )
        if len(logical_keys) != len(set(logical_keys)):
            raise ValueError("chain_coverages contain a duplicate logical chain")

        targets = tuple(
            target for coverage in self.chain_coverages for target in coverage.request_target_refs
        )
        target_keys = tuple(_full_ref_key(item) for item in targets)
        if len(target_keys) != len(set(target_keys)) or set(target_keys) != set(request_keys):
            raise ValueError("chain target refs do not cover the exact Request set once")
        if self.covered_request_observation_count != len(target_keys):
            raise ValueError("covered Request count drifted from chain targets")

        all_refs = tuple(
            item for coverage in self.chain_coverages for item in coverage.observation_refs
        )
        ids = tuple(item.observation_id for item in all_refs)
        documents = tuple(item.observation_sha256 for item in all_refs)
        chains = tuple(item.chain_sha256 for item in all_refs)
        if len(ids) != len(set(ids)):
            raise ValueError("chain coverages contain a duplicate Observation ID")
        if len(documents) != len(set(documents)):
            raise ValueError("chain coverages contain a duplicate Observation document digest")
        if len(chains) != len(set(chains)):
            raise ValueError("chain coverages contain a duplicate Observation chain digest")
        set_digests = tuple(item.observation_set_sha256 for item in self.chain_coverages)
        if len(set_digests) != len(set(set_digests)):
            raise ValueError("chain coverages contain a duplicate Observation-set digest")
        if self.provided_observation_count != len(all_refs):
            raise ValueError("provided_observation_count drifted from chain refs")
        support_count = sum(len(item.supporting_ancestor_refs) for item in self.chain_coverages)
        if self.supporting_ancestor_observation_count != support_count:
            raise ValueError("supporting ancestor count drifted from chain refs")
        if self.limitation_codes != _ALL_LIMITATION_CODES:
            raise ValueError("record chain coverage must retain all seven limitation codes")
        expected_digest = _coverage_set_sha256(
            evidence_record_id=self.evidence_record_id,
            evidence_record_sha256=self.evidence_record_sha256,
            request_id=self.request_id,
            request_sha256=self.request_sha256,
            subject_closure=self.subject_closure,
            request_observation_count=self.request_observation_count,
            request_observation_refs=self.request_observation_refs,
            chain_count=self.chain_count,
            chain_coverages=self.chain_coverages,
            covered_request_observation_count=self.covered_request_observation_count,
            provided_observation_count=self.provided_observation_count,
            supporting_ancestor_observation_count=(self.supporting_ancestor_observation_count),
        )
        if self.coverage_set_sha256 != expected_digest:
            raise ValueError("coverage_set_sha256 drifted from the exact coverage projection")
        if (
            not isinstance(info.context, dict)
            or info.context.get(_RESULT_PROVENANCE_CONTEXT_KEY) is not _RESULT_PROVENANCE_SENTINEL
        ):
            raise ValueError(
                "record chain coverage results may be constructed only by the complete verifier"
            )
        self._verification_provenance = (
            _RESULT_PROVENANCE_SENTINEL,
            _result_provenance_sha256(self),
        )
        return self


def _require_result_provenance(
    value: FreshStatusEvidenceRecordChainCoverageResultV1,
) -> FreshStatusEvidenceRecordChainCoverageResultV1:
    provenance = value._verification_provenance
    expected = (_RESULT_PROVENANCE_SENTINEL, _result_provenance_sha256(value))
    if (
        provenance is None
        or provenance[0] is not _RESULT_PROVENANCE_SENTINEL
        or provenance != expected
    ):
        _raise(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the coverage result lacks verifier-bound in-memory provenance",
        )
    return value


def _raise(
    code: FreshStatusRecordChainCoverageErrorCodeV1,
    message: str,
    *,
    replay_code: FreshStatusChainReplayErrorCodeV1 | None = None,
) -> Never:
    raise RealAssetFreshStatusRecordChainCoverageV30Error(
        code,
        message,
        replay_code=replay_code,
    )


def _strict_chain_input_envelope(value: object) -> FreshStatusRecordChainInputV1:
    if type(value) is not FreshStatusRecordChainInputV1:
        _raise(
            "CHAIN_INPUT_CONTRACT_INVALID",
            "every chain input must be one exact immutable FreshStatusRecordChainInputV1",
        )
    try:
        return FreshStatusRecordChainInputV1.model_validate(value, strict=True)
    except ValidationError as exc:
        raise RealAssetFreshStatusRecordChainCoverageV30Error(
            "CHAIN_INPUT_CONTRACT_INVALID",
            "a chain input violates its strict grouping contract",
        ) from exc


def _input_sort_key(
    chain: FreshStatusRecordChainInputV1,
    observation_document_sha256s: tuple[str, ...],
) -> tuple[str, str, str, tuple[str, ...], tuple[tuple[str, str, str, str, str], ...]]:
    return (
        chain.status_category,
        chain.source_kind,
        chain.source_identity_ref_sha256,
        tuple(sorted(observation_document_sha256s)),
        tuple(sorted(_full_ref_key(item) for item in chain.request_target_refs)),
    )


def _first_duplicate(values: tuple[str, ...]) -> str | None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    return duplicates[0] if duplicates else None


def _aggregate_source_bytes(chains: tuple[FreshStatusRecordChainInputV1, ...]) -> int:
    """Count every supplied Observation occurrence using exact Slice 1 canonical bytes."""

    return sum(len(_canonical_document(item)) for chain in chains for item in chain.observations)


def _require_cross_chain_uniqueness(
    *,
    observation_ref_groups: tuple[tuple[FreshStatusObservationRefV1, ...], ...],
    observation_set_sha256s: tuple[str, ...],
) -> None:
    """Apply the four aggregation collision guards in their frozen error order."""

    all_refs = tuple(item for group in observation_ref_groups for item in group)
    duplicate_id = _first_duplicate(tuple(item.observation_id for item in all_refs))
    if duplicate_id is not None:
        _raise(
            "CROSS_CHAIN_DUPLICATE_OBSERVATION_ID",
            f"Observation ID {duplicate_id} occurs in more than one explicit chain",
        )
    duplicate_document = _first_duplicate(tuple(item.observation_sha256 for item in all_refs))
    if duplicate_document is not None:
        _raise(
            "CROSS_CHAIN_DUPLICATE_OBSERVATION_DOCUMENT_SHA256",
            "an Observation canonical-document digest occurs in more than one chain",
        )
    duplicate_chain = _first_duplicate(tuple(item.chain_sha256 for item in all_refs))
    if duplicate_chain is not None:
        _raise(
            "CROSS_CHAIN_DUPLICATE_OBSERVATION_CHAIN_SHA256",
            "an Observation chain digest occurs in more than one chain",
        )
    duplicate_set = _first_duplicate(observation_set_sha256s)
    if duplicate_set is not None:
        _raise(
            "CROSS_CHAIN_DUPLICATE_OBSERVATION_SET_SHA256",
            "an explicit chain-set digest occurs more than once",
        )


_FullRefKey = tuple[str, str, str, str, str]
_ReplayedChain = tuple[
    FreshStatusRecordChainInputV1,
    FreshStatusExplicitFiniteChainReplayResultV1,
]


def _declared_targets(
    chain: FreshStatusRecordChainInputV1,
) -> tuple[FreshStatusObservationRefV1, ...]:
    return tuple(sorted(chain.request_target_refs, key=_full_ref_key))


def _require_request_targets_resolved_in_all_chains(
    replayed: tuple[_ReplayedChain, ...],
) -> None:
    """Apply the target-resolution guard across every canonical replayed chain."""

    for chain, replay in replayed:
        replay_keys = {_full_ref_key(item) for item in replay.observation_refs}
        unresolved = sorted(
            _full_ref_key(item)
            for item in _declared_targets(chain)
            if _full_ref_key(item) not in replay_keys
        )
        if unresolved:
            _raise(
                "REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN",
                f"Request target {unresolved[0][0]} is absent from its declared chain",
            )


def _require_chain_target_sets_match(
    *,
    replayed: tuple[_ReplayedChain, ...],
    record_keys: frozenset[_FullRefKey],
) -> None:
    """Defensively require each chain's actual Request set to equal its declared targets."""

    for chain, replay in replayed:
        actual_request_refs = tuple(
            sorted(
                (item for item in replay.observation_refs if _full_ref_key(item) in record_keys),
                key=_full_ref_key,
            )
        )
        if actual_request_refs != _declared_targets(chain):
            _raise(
                "CHAIN_TARGET_SET_MISMATCH",
                "a chain's actual Request refs differ from its declared target refs",
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


def verify_fresh_status_evidence_record_explicit_chain_coverage_v1(
    *,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> FreshStatusEvidenceRecordChainCoverageResultV1:
    """Verify exact Request-target coverage by 1..32 explicit in-memory source chains."""

    if type(chains) is not tuple:
        _raise("CHAIN_COLLECTION_CONTRACT_INVALID", "chains must be an exact tuple")
    if not 1 <= len(chains) <= FRESH_STATUS_MAX_OBSERVATIONS:
        _raise("CHAIN_COUNT_OUT_OF_RANGE", "the collection must contain 1..32 chain inputs")

    admitted = tuple(_strict_chain_input_envelope(item) for item in chains)
    if any(
        not 1 <= len(item.request_target_refs) <= FRESH_STATUS_MAX_OBSERVATIONS for item in admitted
    ):
        _raise("TARGET_COUNT_OUT_OF_RANGE", "every chain must declare 1..32 Request targets")
    if any(not 1 <= len(item.observations) <= FRESH_STATUS_MAX_CHAIN_RECORDS for item in admitted):
        _raise("OBSERVATION_COUNT_OUT_OF_RANGE", "every chain must contain 1..64 observations")

    try:
        aggregate_size = _aggregate_source_bytes(admitted)
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise RealAssetFreshStatusRecordChainCoverageV30Error(
            "CHAIN_INPUT_CONTRACT_INVALID",
            "a supplied Observation cannot be rendered as Slice 1 canonical bytes",
        ) from exc
    if aggregate_size > FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES:
        _raise(
            "AGGREGATE_CANONICAL_BYTES_OUT_OF_RANGE",
            "supplied Observation occurrences exceed the 16777216-byte aggregate limit",
        )

    admitted_with_digests: list[tuple[FreshStatusRecordChainInputV1, tuple[str, ...]]] = []
    try:
        for chain in admitted:
            document_digests: list[str] = []
            for observation in chain.observations:
                raw = _canonical_document(observation)
                document_digests.append(_sha256(raw))
            admitted_with_digests.append((chain, tuple(document_digests)))
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise RealAssetFreshStatusRecordChainCoverageV30Error(
            "CHAIN_INPUT_CONTRACT_INVALID",
            "a supplied Observation cannot be rendered as Slice 1 canonical bytes",
        ) from exc
    if type(record) is not CreativeSampleRealAssetFreshStatusEvidenceRecordV1:
        _raise(
            "EVIDENCE_RECORD_INVALID",
            "record must be one exact immutable Fresh Status EvidenceRecord model",
        )
    try:
        strict_record = CreativeSampleRealAssetFreshStatusEvidenceRecordV1.model_validate(
            record,
            strict=True,
        )
        verified_record = verify_fresh_status_evidence_record_internal_v1(strict_record)
        evidence_record_sha256 = _sha256(_canonical_document(verified_record))
    except (
        RealAssetFreshStatusEvidenceV30Error,
        AttributeError,
        TypeError,
        ValidationError,
        ValueError,
    ) as exc:
        raise RealAssetFreshStatusRecordChainCoverageV30Error(
            "EVIDENCE_RECORD_INVALID",
            "the Fresh Status EvidenceRecord failed strict internal replay",
        ) from exc

    record_refs = tuple(verified_record.request.observation_refs)
    record_by_id = {item.observation_id: item for item in record_refs}
    record_keys = frozenset(_full_ref_key(item) for item in record_refs)
    all_targets = tuple(target for chain in admitted for target in chain.request_target_refs)
    target_keys = tuple(_full_ref_key(item) for item in all_targets)
    duplicate_targets = sorted(key for key, count in Counter(target_keys).items() if count > 1)
    if duplicate_targets:
        _raise(
            "REQUEST_TARGET_COVERED_MULTIPLE_TIMES",
            f"Request target {duplicate_targets[0][0]} is declared more than once",
        )
    anchor_mismatches = sorted(
        target.observation_id
        for target in all_targets
        if target.observation_id in record_by_id and record_by_id[target.observation_id] != target
    )
    if anchor_mismatches:
        _raise(
            "REQUEST_TARGET_ANCHOR_MISMATCH",
            f"Request target {anchor_mismatches[0]} drifted from the exact Record reference",
        )
    absent_target_ids = sorted(
        target.observation_id for target in all_targets if target.observation_id not in record_by_id
    )
    if absent_target_ids:
        _raise(
            "REQUEST_TARGET_NOT_IN_RECORD",
            f"Request target {absent_target_ids[0]} is not named by the Record Request",
        )
    missing_record_keys = sorted(record_keys - set(target_keys))
    if missing_record_keys:
        _raise(
            "REQUEST_OBSERVATION_NOT_COVERED",
            f"Request Observation {missing_record_keys[0][0]} has no declared chain target",
        )

    ordered_inputs = tuple(
        sorted(
            admitted_with_digests,
            key=lambda item: _input_sort_key(item[0], item[1]),
        )
    )
    replayed: list[
        tuple[FreshStatusRecordChainInputV1, FreshStatusExplicitFiniteChainReplayResultV1]
    ] = []
    for chain, _ in ordered_inputs:
        try:
            replay = verify_fresh_status_explicit_finite_source_chain_v1(
                subject_closure=verified_record.subject_closure,
                status_category=chain.status_category,
                source_kind=chain.source_kind,
                source_identity_ref_sha256=chain.source_identity_ref_sha256,
                observations=chain.observations,
            )
        except RealAssetFreshStatusChainReplayV30Error as exc:
            raise RealAssetFreshStatusRecordChainCoverageV30Error(
                "CHAIN_REPLAY_FAILED",
                "an explicit source chain failed the public Slice 2 verifier",
                replay_code=exc.code,
            ) from exc
        replayed.append((chain, replay))

    logical_keys = tuple(
        (
            chain.status_category,
            chain.source_kind,
            chain.source_identity_ref_sha256,
            _full_ref_key(replay.genesis_ref),
        )
        for chain, replay in replayed
    )
    duplicate_logical = sorted(key for key, count in Counter(logical_keys).items() if count > 1)
    if duplicate_logical:
        _raise(
            "DUPLICATE_LOGICAL_CHAIN",
            "the collection splits or repeats one scope-and-Genesis logical chain",
        )

    _require_cross_chain_uniqueness(
        observation_ref_groups=tuple(replay.observation_refs for _, replay in replayed),
        observation_set_sha256s=tuple(replay.observation_set_sha256 for _, replay in replayed),
    )

    canonical_replayed = tuple(replayed)
    _require_request_targets_resolved_in_all_chains(canonical_replayed)
    _require_chain_target_sets_match(
        replayed=canonical_replayed,
        record_keys=record_keys,
    )

    chain_materials: list[
        tuple[
            FreshStatusRecordChainInputV1,
            FreshStatusExplicitFiniteChainReplayResultV1,
            tuple[FreshStatusObservationRefV1, ...],
            dict[str, CreativeSampleRealAssetFreshStatusSourceObservationV1],
            set[str],
        ]
    ] = []
    for chain, replay in replayed:
        declared_targets = _declared_targets(chain)
        observations_by_id = {item.observation_id: item for item in chain.observations}
        required_ids: set[str] = set()
        pending = [item.observation_id for item in declared_targets]
        while pending:
            observation_id = pending.pop()
            if observation_id in required_ids:
                continue
            required_ids.add(observation_id)
            observation = observations_by_id[observation_id]
            link = observation.chain_link
            if link.kind == "SUCCESSOR":
                previous_id = link.previous_observation_id
                if previous_id is not None:
                    pending.append(previous_id)
            elif link.kind == "RECONCILIATION":
                pending.extend(item.observation_id for item in link.branch_heads)
        all_ids = set(observations_by_id)
        if required_ids != all_ids:
            unrelated_id = sorted(all_ids - required_ids)[0]
            _raise(
                "UNRELATED_SUPPORT_OBSERVATION",
                f"Observation {unrelated_id} is not a target or ancestor of any declared target",
            )
        chain_materials.append(
            (
                chain,
                replay,
                declared_targets,
                observations_by_id,
                required_ids,
            )
        )

    summary_payloads: list[dict[str, object]] = []
    target_observations: dict[
        _FullRefKey,
        CreativeSampleRealAssetFreshStatusSourceObservationV1,
    ] = {}
    for _chain, replay, declared_targets, observations_by_id, _ in chain_materials:
        target_ids = {item.observation_id for item in declared_targets}
        supporting_refs = tuple(
            sorted(
                (item for item in replay.observation_refs if item.observation_id not in target_ids),
                key=_ref_key,
            )
        )
        for target in declared_targets:
            target_observations[_full_ref_key(target)] = observations_by_id[target.observation_id]
        summary_payloads.append(
            {
                "status_category": replay.status_category,
                "source_kind": replay.source_kind,
                "source_identity_ref_sha256": replay.source_identity_ref_sha256,
                "observation_count": replay.observation_count,
                "observation_set_sha256": replay.observation_set_sha256,
                "observation_refs": replay.observation_refs,
                "genesis_ref": replay.genesis_ref,
                "provided_set_fork_point_refs": replay.provided_set_fork_point_refs,
                "provided_set_terminal_head_refs": replay.provided_set_terminal_head_refs,
                "provided_set_terminal_shape": replay.provided_set_terminal_shape,
                "request_target_refs": declared_targets,
                "supporting_ancestor_refs": supporting_refs,
                "provided_explicit_finite_chain_closure_consistent": True,
            }
        )

    ordered_target_observations = tuple(
        target_observations[_full_ref_key(item)] for item in record_refs
    )
    try:
        rebuilt_request = build_fresh_status_request_v1(
            subject_closure=verified_record.subject_closure,
            preparer_identity_ref_sha256=(verified_record.request.preparer_identity_ref_sha256),
            requested_at=verified_record.request.requested_at,
            request_basis=verified_record.request.request_basis,
            observations=ordered_target_observations,
        )
        rebuilt_instruction = build_fresh_status_instruction_v1(
            request=rebuilt_request,
            observations=ordered_target_observations,
            checker_identity_ref_sha256=(verified_record.instruction.checker_identity_ref_sha256),
            evaluated_at=verified_record.instruction.evaluated_at,
            checker_basis=verified_record.instruction.checker_basis,
        )
        rebuilt_record = build_fresh_status_evidence_record_v1(
            request=rebuilt_request,
            instruction=rebuilt_instruction,
        )
    except RealAssetFreshStatusEvidenceV30Error as exc:
        raise RealAssetFreshStatusRecordChainCoverageV30Error(
            "RECORD_REBUILD_MISMATCH",
            "the exact target Observations could not rebuild the EvidenceRecord",
        ) from exc
    if rebuilt_record != verified_record:
        _raise(
            "RECORD_REBUILD_MISMATCH",
            "the exact target Observations rebuild a different EvidenceRecord",
        )

    try:
        summaries = tuple(
            sorted(
                (
                    FreshStatusRecordChainCoverageSummaryV1.model_validate(
                        payload,
                        strict=True,
                    )
                    for payload in summary_payloads
                ),
                key=_summary_key,
            )
        )
        request_observation_refs = tuple(sorted(record_refs, key=_full_ref_key))
        request_observation_count = len(request_observation_refs)
        chain_count = len(summaries)
        covered_request_observation_count = len(request_observation_refs)
        provided_observation_count = sum(item.observation_count for item in summaries)
        supporting_ancestor_observation_count = sum(
            len(item.supporting_ancestor_refs) for item in summaries
        )
        coverage_set_sha256 = _coverage_set_sha256(
            evidence_record_id=verified_record.record_id,
            evidence_record_sha256=evidence_record_sha256,
            request_id=verified_record.request.request_id,
            request_sha256=verified_record.request_sha256,
            subject_closure=verified_record.subject_closure,
            request_observation_count=request_observation_count,
            request_observation_refs=request_observation_refs,
            chain_count=chain_count,
            chain_coverages=summaries,
            covered_request_observation_count=covered_request_observation_count,
            provided_observation_count=provided_observation_count,
            supporting_ancestor_observation_count=(supporting_ancestor_observation_count),
        )
        result = FreshStatusEvidenceRecordChainCoverageResultV1.model_validate(
            {
                "evidence_record_id": verified_record.record_id,
                "evidence_record_sha256": evidence_record_sha256,
                "request_id": verified_record.request.request_id,
                "request_sha256": verified_record.request_sha256,
                "subject_closure": verified_record.subject_closure,
                "request_observation_count": request_observation_count,
                "request_observation_refs": request_observation_refs,
                "chain_count": chain_count,
                "chain_coverages": summaries,
                "covered_request_observation_count": covered_request_observation_count,
                "provided_observation_count": provided_observation_count,
                "supporting_ancestor_observation_count": (supporting_ancestor_observation_count),
                "coverage_set_sha256": coverage_set_sha256,
                "provided_evidence_record_request_explicit_chain_coverage_consistent": True,
                "provided_evidence_record_rebuild_consistent": True,
                "limitation_codes": _ALL_LIMITATION_CODES,
                **_zero_authority_payload(),
            },
            strict=True,
            context={_RESULT_PROVENANCE_CONTEXT_KEY: _RESULT_PROVENANCE_SENTINEL},
        )
    except ValidationError as exc:
        raise RealAssetFreshStatusRecordChainCoverageV30Error(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the derived non-persistent coverage result is internally inconsistent",
        ) from exc
    return _require_result_provenance(result)


__all__ = [
    "FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE",
    "FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES",
    "FreshStatusRecordChainCoverageErrorCodeV1",
    "FreshStatusRecordChainInputV1",
    "FreshStatusRecordChainCoverageSummaryV1",
    "FreshStatusEvidenceRecordChainCoverageResultV1",
    "RealAssetFreshStatusRecordChainCoverageV30Error",
    "verify_fresh_status_evidence_record_explicit_chain_coverage_v1",
]
