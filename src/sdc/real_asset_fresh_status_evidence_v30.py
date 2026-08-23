"""Pure Fresh Hold / Revocation / Status Evidence contracts v3.0.

This module builds and verifies deterministic, immutable, zero-authority status-evidence
documents from explicitly supplied model objects and timestamps.  It performs no filesystem,
network, Provider, environment-time, or wall-clock I/O.  A consistent record proves only the
canonical closure supplied to these functions; it does not prove source authenticity,
completeness, reality currentness, legal effect, or execution authority.
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
from sdc.real_asset_use_plan_v26 import CreativeSampleRealAssetUsePlanV1
from sdc.real_asset_use_scope_review_v26 import (
    CreativeSampleRealAssetUseScopeReviewRecordV1,
    verify_use_scope_review_record_closure_v1,
)

FRESH_STATUS_EVIDENCE_V1_PROFILE: Literal[
    "creative-sample-real-asset-fresh-status-evidence-v3.0"
] = "creative-sample-real-asset-fresh-status-evidence-v3.0"
FRESH_STATUS_EVIDENCE_V1_POLICY_ID: Literal[
    "creative-sample-real-asset-fresh-status-evidence-policy"
] = "creative-sample-real-asset-fresh-status-evidence-policy"
FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION: Literal["3.0.0"] = "3.0.0"
FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256: Literal[
    "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"
] = "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"

FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE: Literal[
    "creative-sample-real-asset-fresh-status-subject-closure-v1"
] = "creative-sample-real-asset-fresh-status-subject-closure-v1"
FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE_DOCUMENT_SHA256: Literal[
    "76d151b7a73dcef7aafa6a928e20e024f353ead30fa91a0b7522078eca3f3c7e"
] = "76d151b7a73dcef7aafa6a928e20e024f353ead30fa91a0b7522078eca3f3c7e"

FRESH_STATUS_MAX_WINDOW_SECONDS = 86_400
FRESH_STATUS_MAX_OBSERVATIONS = 32
FRESH_STATUS_MAX_CHAIN_RECORDS = 64
FRESH_STATUS_MAX_RECONCILIATION_HEADS = 8
FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS = 1_000
FRESH_STATUS_AUTHORING_INPUT_MAX_BYTES = 65_536
FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES = 262_144
FRESH_STATUS_RECORD_MAX_BYTES = 2_097_152
FRESH_STATUS_JSON_MAX_DEPTH = 32
FRESH_STATUS_EVIDENCE_SCOPE: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"] = (
    "EXPLICIT_FINITE_BOUND_SET_ONLY"
)

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_UTC_SECONDS = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_PORTABLE_CODE = r"^[A-Z][A-Z0-9_]{0,127}$"
_MEDIA_TYPE = r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,63}/[a-z0-9][a-z0-9!#$&^_.+-]{0,63}$"
_POLICY_DOMAIN = b"sdc:creative-sample-real-asset-fresh-status-evidence-policy:v3.0\0"
_CLOSURE_PROFILE_DOMAIN = b"sdc:creative-sample-real-asset-fresh-status-closure-profile:v1\0"
_CHAIN_DOMAIN = b"sdc:creative-sample-real-asset-fresh-status-chain:v1\0"

FreshStatusCategoryV1 = Literal[
    "HOLD_ACTIVE",
    "REVOCATION_EFFECTIVE",
    "COMPLAINT_OPEN",
    "DISPUTE_OPEN",
    "RIGHTS_BASIS_CURRENT",
    "IDENTITY_BINDING_CURRENT",
    "POLICY_COMPATIBILITY_CURRENT",
]
FreshStatusClaimValueV1 = Literal[
    "PRESENT",
    "ABSENT_WITH_EVIDENCE",
    "UNKNOWN",
    "NOT_ASSESSED",
    "CONFLICT",
]
FreshStatusAssessmentEffectV1 = Literal[
    "BLOCKING",
    "NON_BLOCKING_WITHIN_BOUND_WINDOW",
    "INDETERMINATE",
]
FreshStatusDispositionV1 = Literal[
    "BLOCKING_STATUS_RECORDED",
    "INSUFFICIENT_OR_CONFLICTING_EVIDENCE",
    "NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET",
]
FreshStatusChainLinkKindV1 = Literal["GENESIS", "SUCCESSOR", "RECONCILIATION"]
FreshStatusBasisCodeV1 = Literal[
    "HOLD_IMPOSED",
    "HOLD_RELEASED",
    "REVOCATION_ISSUED",
    "RIGHTS_REINSTATED",
    "COMPLAINT_RECEIVED",
    "COMPLAINT_RESOLVED",
    "DISPUTE_OPENED",
    "DISPUTE_RESOLVED",
    "RIGHTS_GRANTED_OR_RENEWED",
    "RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED",
    "IDENTITY_VERIFIED_OR_REBOUND",
    "IDENTITY_EXPIRED_REVOKED_OR_SUPERSEDED",
    "POLICY_REVIEWED_COMPATIBLE",
    "POLICY_CHANGED_OR_INCOMPATIBLE",
    "INITIAL_STATUS_UNKNOWN",
    "INITIAL_STATUS_NOT_ASSESSED",
    "STATUS_RECONFIRMED",
    "STATUS_BECAME_UNKNOWN",
    "CONFLICT_IDENTIFIED",
    "CONFLICT_RECONCILED",
]
FreshStatusSourceKindV1 = Literal[
    "RIGHTS_HOLDER_DECLARATION",
    "LICENSOR_DECLARATION",
    "INTERNAL_HOLD_RECORD",
    "REVOCATION_NOTICE",
    "COMPLAINT_RECORD",
    "DISPUTE_RECORD",
    "IDENTITY_BINDING_RECORD",
    "POLICY_EVALUATION_RECORD",
]
FreshStatusLimitationCodeV1 = Literal[
    "SOURCE_AUTHENTICITY_NOT_PROVEN",
    "SOURCE_COMPLETENESS_NOT_PROVEN",
    "CHAIN_COMPLETENESS_NOT_PROVEN",
    "REALITY_CURRENTNESS_NOT_PROVEN",
    "SCOPE_LIMITED_TO_DECLARED_SUBJECT",
    "TIME_WINDOW_LIMITED",
    "LEGAL_EFFECT_NOT_DETERMINED",
]

_CATEGORY_ORDER: tuple[FreshStatusCategoryV1, ...] = (
    "HOLD_ACTIVE",
    "REVOCATION_EFFECTIVE",
    "COMPLAINT_OPEN",
    "DISPUTE_OPEN",
    "RIGHTS_BASIS_CURRENT",
    "IDENTITY_BINDING_CURRENT",
    "POLICY_COMPATIBILITY_CURRENT",
)
_SOURCE_KIND_ORDER: tuple[FreshStatusSourceKindV1, ...] = (
    "RIGHTS_HOLDER_DECLARATION",
    "LICENSOR_DECLARATION",
    "INTERNAL_HOLD_RECORD",
    "REVOCATION_NOTICE",
    "COMPLAINT_RECORD",
    "DISPUTE_RECORD",
    "IDENTITY_BINDING_RECORD",
    "POLICY_EVALUATION_RECORD",
)
_LIMITATION_CODE_ORDER: tuple[FreshStatusLimitationCodeV1, ...] = (
    "SOURCE_AUTHENTICITY_NOT_PROVEN",
    "SOURCE_COMPLETENESS_NOT_PROVEN",
    "CHAIN_COMPLETENESS_NOT_PROVEN",
    "REALITY_CURRENTNESS_NOT_PROVEN",
    "SCOPE_LIMITED_TO_DECLARED_SUBJECT",
    "TIME_WINDOW_LIMITED",
    "LEGAL_EFFECT_NOT_DETERMINED",
)
_MANDATORY_LIMITATION_CODES: tuple[FreshStatusLimitationCodeV1, ...] = (
    "SOURCE_AUTHENTICITY_NOT_PROVEN",
    "SOURCE_COMPLETENESS_NOT_PROVEN",
    "CHAIN_COMPLETENESS_NOT_PROVEN",
    "REALITY_CURRENTNESS_NOT_PROVEN",
)
_BASIS_CODE_ORDER: tuple[FreshStatusBasisCodeV1, ...] = (
    "HOLD_IMPOSED",
    "HOLD_RELEASED",
    "REVOCATION_ISSUED",
    "RIGHTS_REINSTATED",
    "COMPLAINT_RECEIVED",
    "COMPLAINT_RESOLVED",
    "DISPUTE_OPENED",
    "DISPUTE_RESOLVED",
    "RIGHTS_GRANTED_OR_RENEWED",
    "RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED",
    "IDENTITY_VERIFIED_OR_REBOUND",
    "IDENTITY_EXPIRED_REVOKED_OR_SUPERSEDED",
    "POLICY_REVIEWED_COMPATIBLE",
    "POLICY_CHANGED_OR_INCOMPATIBLE",
    "INITIAL_STATUS_UNKNOWN",
    "INITIAL_STATUS_NOT_ASSESSED",
    "STATUS_RECONFIRMED",
    "STATUS_BECAME_UNKNOWN",
    "CONFLICT_IDENTIFIED",
    "CONFLICT_RECONCILED",
)
_DETERMINED_BASIS_BY_CATEGORY: dict[
    FreshStatusCategoryV1, tuple[FreshStatusBasisCodeV1, FreshStatusBasisCodeV1]
] = {
    "HOLD_ACTIVE": ("HOLD_IMPOSED", "HOLD_RELEASED"),
    "REVOCATION_EFFECTIVE": ("REVOCATION_ISSUED", "RIGHTS_REINSTATED"),
    "COMPLAINT_OPEN": ("COMPLAINT_RECEIVED", "COMPLAINT_RESOLVED"),
    "DISPUTE_OPEN": ("DISPUTE_OPENED", "DISPUTE_RESOLVED"),
    "RIGHTS_BASIS_CURRENT": (
        "RIGHTS_GRANTED_OR_RENEWED",
        "RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED",
    ),
    "IDENTITY_BINDING_CURRENT": (
        "IDENTITY_VERIFIED_OR_REBOUND",
        "IDENTITY_EXPIRED_REVOKED_OR_SUPERSEDED",
    ),
    "POLICY_COMPATIBILITY_CURRENT": (
        "POLICY_REVIEWED_COMPATIBLE",
        "POLICY_CHANGED_OR_INCOMPATIBLE",
    ),
}
_ADVERSE_CATEGORIES = frozenset(
    {"HOLD_ACTIVE", "REVOCATION_EFFECTIVE", "COMPLAINT_OPEN", "DISPUTE_OPEN"}
)
_ALLOWED_SUCCESSORS: dict[str, frozenset[str]] = {
    "NOT_ASSESSED": frozenset({"UNKNOWN", "PRESENT", "ABSENT_WITH_EVIDENCE", "CONFLICT"}),
    "UNKNOWN": frozenset({"PRESENT", "ABSENT_WITH_EVIDENCE", "CONFLICT"}),
    "PRESENT": frozenset({"PRESENT", "ABSENT_WITH_EVIDENCE", "UNKNOWN", "CONFLICT"}),
    "ABSENT_WITH_EVIDENCE": frozenset({"ABSENT_WITH_EVIDENCE", "PRESENT", "UNKNOWN", "CONFLICT"}),
    "CONFLICT": frozenset(),
}


def _canonical_payload(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def _canonical_document(value: BaseModel) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


_FRESH_STATUS_POLICY_PAYLOAD: dict[str, object] = {
    "basis_code_order": _BASIS_CODE_ORDER,
    "determined_basis_by_category": tuple(
        (category, *_DETERMINED_BASIS_BY_CATEGORY[category]) for category in _CATEGORY_ORDER
    ),
    "category_order": _CATEGORY_ORDER,
    "claim_values": (
        "PRESENT",
        "ABSENT_WITH_EVIDENCE",
        "UNKNOWN",
        "NOT_ASSESSED",
        "CONFLICT",
    ),
    "dispositions": (
        "BLOCKING_STATUS_RECORDED",
        "INSUFFICIENT_OR_CONFLICTING_EVIDENCE",
        "NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET",
    ),
    "evidence_scope": FRESH_STATUS_EVIDENCE_SCOPE,
    "limits": {
        "basis_note_codepoints": FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS,
        "authoring_input_bytes": FRESH_STATUS_AUTHORING_INPUT_MAX_BYTES,
        "json_depth": FRESH_STATUS_JSON_MAX_DEPTH,
        "max_chain_records": FRESH_STATUS_MAX_CHAIN_RECORDS,
        "max_observations": FRESH_STATUS_MAX_OBSERVATIONS,
        "max_reconciliation_heads": FRESH_STATUS_MAX_RECONCILIATION_HEADS,
        "max_window_seconds": FRESH_STATUS_MAX_WINDOW_SECONDS,
        "record_bytes": FRESH_STATUS_RECORD_MAX_BYTES,
        "source_observation_bytes": FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES,
    },
    "limitation_code_order": _LIMITATION_CODE_ORDER,
    "mandatory_limitation_codes": _MANDATORY_LIMITATION_CODES,
    "policy_id": FRESH_STATUS_EVIDENCE_V1_POLICY_ID,
    "policy_version": FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
    "rules": (
        "EXPLICIT_FINITE_SUBJECT_CLOSURE",
        "SEPARATE_PREPARER_CHECKER_COMPILER_MODULES",
        "DOMAIN_SEPARATED_STABLE_IDS_AND_CHAIN_DIGESTS",
        "GENESIS_SUCCESSOR_RECONCILIATION_ONLY",
        "NO_AUTOMATIC_FORK_SELECTION_OR_GLOBAL_TRUTH_CLAIM",
        "EXPLICIT_UTC_SECONDS_WITH_HALF_OPEN_WINDOWS",
        "NO_IMPLICIT_CLOCK_NETWORK_PROVIDER_OR_FILESYSTEM",
        "BLOCKING_DOMINATES_INDETERMINATE",
        "ALL_SEVEN_NON_BLOCKING_REQUIRED_FOR_NO_BLOCKING_DISPOSITION",
        "HUMAN_GATE_ZERO_AUTHORITY_ALWAYS",
        "MATCHING_BASIS_CODE_REQUIRED",
        "REQUEST_WINDOW_CAPS_DECISION_HORIZON",
        "REQUEST_OBSERVATION_SET_MUST_EQUAL_INSTRUCTION_UNION",
    ),
    "source_kind_order": _SOURCE_KIND_ORDER,
    "successor_matrix": tuple(
        (state, tuple(sorted(successors)))
        for state, successors in sorted(_ALLOWED_SUCCESSORS.items())
    ),
}
_SUBJECT_CLOSURE_PROFILE_PAYLOAD: dict[str, object] = {
    "fields": (
        "pack_id",
        "pack_manifest_sha256",
        "rights_manifest_id",
        "rights_manifest_sha256",
        "use_plan_id",
        "use_plan_sha256",
        "use_scope_review_record_id",
        "use_scope_review_record_sha256",
    ),
    "profile": FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE,
    "rules": ("ID_SHA256_PAIRS_REQUIRED", "COMPLETE_UPSTREAM_REPLAY_REQUIRED"),
}
_ACTUAL_POLICY_DOCUMENT_SHA256 = _sha256(
    _POLICY_DOMAIN + _canonical_payload(_FRESH_STATUS_POLICY_PAYLOAD)
)
if _ACTUAL_POLICY_DOCUMENT_SHA256 != FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256:
    raise RuntimeError(
        "Fresh Status Evidence v3.0 policy payload digest drifted: "
        f"{_ACTUAL_POLICY_DOCUMENT_SHA256}"
    )
if _sha256(_CLOSURE_PROFILE_DOMAIN + _canonical_payload(_SUBJECT_CLOSURE_PROFILE_PAYLOAD)) != (
    FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE_DOCUMENT_SHA256
):
    raise RuntimeError("Fresh Status subject-closure profile payload digest drifted")


class RealAssetFreshStatusEvidenceV30Error(RuntimeError):
    """The pure Fresh Status Evidence v3.0 consumer failed closed."""


def _json_identity_projection(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_identity_projection(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return tuple(_json_identity_projection(item) for item in value)
    return value


def _stable_contract_id(kind: str, payload: dict[str, object]) -> str:
    try:
        return stable_id(kind, _json_identity_projection(payload))
    except (TypeError, ValueError) as exc:
        raise RealAssetFreshStatusEvidenceV30Error(
            f"{kind} identity projection is not canonical JSON"
        ) from exc


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


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _portable_text(value: str, *, field: str, maximum: int) -> str:
    if type(value) is not str or not value or len(value) > maximum or value != value.strip():
        raise ValueError(f"{field} must contain 1..{maximum} trimmed Unicode code points")
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise ValueError(f"{field} must not contain control characters")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError(f"{field} must use NFC-normalized Unicode")
    return value


def _assessment_effect(
    category: FreshStatusCategoryV1, claim: FreshStatusClaimValueV1
) -> FreshStatusAssessmentEffectV1:
    if claim in {"UNKNOWN", "NOT_ASSESSED", "CONFLICT"}:
        return "INDETERMINATE"
    if category in _ADVERSE_CATEGORIES:
        return "BLOCKING" if claim == "PRESENT" else "NON_BLOCKING_WITHIN_BOUND_WINDOW"
    return "NON_BLOCKING_WITHIN_BOUND_WINDOW" if claim == "PRESENT" else "BLOCKING"


def _expected_basis_code(
    *,
    category: FreshStatusCategoryV1,
    claim: FreshStatusClaimValueV1,
    chain_kind: FreshStatusChainLinkKindV1,
    previous_claim: FreshStatusClaimValueV1 | None,
) -> FreshStatusBasisCodeV1:
    if chain_kind == "GENESIS":
        if previous_claim is not None:
            raise ValueError("GENESIS cannot declare a previous claim")
        if claim == "PRESENT":
            return _DETERMINED_BASIS_BY_CATEGORY[category][0]
        if claim == "ABSENT_WITH_EVIDENCE":
            return _DETERMINED_BASIS_BY_CATEGORY[category][1]
        if claim == "UNKNOWN":
            return "INITIAL_STATUS_UNKNOWN"
        if claim == "NOT_ASSESSED":
            return "INITIAL_STATUS_NOT_ASSESSED"
        return "CONFLICT_IDENTIFIED"
    if chain_kind == "RECONCILIATION":
        if previous_claim is not None:
            raise ValueError("RECONCILIATION cannot declare one previous claim")
        if claim == "NOT_ASSESSED":
            raise ValueError("RECONCILIATION cannot return to NOT_ASSESSED")
        return "CONFLICT_IDENTIFIED" if claim == "CONFLICT" else "CONFLICT_RECONCILED"
    if previous_claim is None:
        raise ValueError("SUCCESSOR must declare its previous claim")
    if claim not in _ALLOWED_SUCCESSORS[previous_claim]:
        raise ValueError("illegal Fresh Status state transition")
    if claim == "CONFLICT":
        return "CONFLICT_IDENTIFIED"
    if claim == "PRESENT":
        if previous_claim == "PRESENT":
            return "STATUS_RECONFIRMED"
        return _DETERMINED_BASIS_BY_CATEGORY[category][0]
    if claim == "ABSENT_WITH_EVIDENCE":
        if previous_claim == "ABSENT_WITH_EVIDENCE":
            return "STATUS_RECONFIRMED"
        return _DETERMINED_BASIS_BY_CATEGORY[category][1]
    if claim == "UNKNOWN":
        if previous_claim == "NOT_ASSESSED":
            return "INITIAL_STATUS_UNKNOWN"
        return "STATUS_BECAME_UNKNOWN"
    raise ValueError("SUCCESSOR cannot return to NOT_ASSESSED")


class _FreshStatusModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class _ZeroAuthorityFreshStatusModel(_FreshStatusModel):
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


class FreshStatusSubjectClosureV1(_FreshStatusModel):
    closure_profile: Literal["creative-sample-real-asset-fresh-status-subject-closure-v1"] = (
        FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE
    )
    closure_profile_document_sha256: Literal[
        "76d151b7a73dcef7aafa6a928e20e024f353ead30fa91a0b7522078eca3f3c7e"
    ] = FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE_DOCUMENT_SHA256
    closure_id: str = Field(pattern=r"^real_asset_fresh_status_subject_closure_v1_[0-9a-f]{20}$")
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    pack_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    rights_manifest_id: str = Field(pattern=r"^real_asset_rights_manifest_v2_[0-9a-f]{20}$")
    rights_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    use_plan_id: str = Field(pattern=r"^real_asset_use_plan_v1_[0-9a-f]{20}$")
    use_plan_sha256: str = Field(pattern=_LOWER_SHA256)
    use_scope_review_record_id: str = Field(
        pattern=r"^real_asset_use_scope_review_record_v1_[0-9a-f]{20}$"
    )
    use_scope_review_record_sha256: str = Field(pattern=_LOWER_SHA256)

    @model_validator(mode="after")
    def validate_closure(self) -> FreshStatusSubjectClosureV1:
        digests = (
            self.pack_manifest_sha256,
            self.rights_manifest_sha256,
            self.use_plan_sha256,
            self.use_scope_review_record_sha256,
        )
        if len(digests) != len(set(digests)):
            raise ValueError("Fresh Status subject closure digests must be pairwise distinct")
        expected = stable_id(
            "real_asset_fresh_status_subject_closure_v1",
            self.model_dump(mode="json", exclude={"closure_id"}),
        )
        if self.closure_id != expected:
            raise ValueError("Fresh Status subject closure ID must bind every ID/SHA anchor")
        return self


class FreshStatusObservationRefV1(_FreshStatusModel):
    observation_id: str = Field(pattern=r"^real_asset_fresh_status_observation_v1_[0-9a-f]{20}$")
    observation_sha256: str = Field(pattern=_LOWER_SHA256)
    status_category: FreshStatusCategoryV1
    source_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    chain_sha256: str = Field(pattern=_LOWER_SHA256)


class FreshStatusChainHeadRefV1(_FreshStatusModel):
    observation_id: str = Field(pattern=r"^real_asset_fresh_status_observation_v1_[0-9a-f]{20}$")
    observation_sha256: str = Field(pattern=_LOWER_SHA256)
    chain_sha256: str = Field(pattern=_LOWER_SHA256)


class FreshStatusChainLinkV1(_FreshStatusModel):
    kind: FreshStatusChainLinkKindV1
    previous_observation_id: str | None = Field(
        default=None, pattern=r"^real_asset_fresh_status_observation_v1_[0-9a-f]{20}$"
    )
    previous_observation_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    previous_chain_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    previous_claim_value: FreshStatusClaimValueV1 | None = None
    branch_heads: tuple[FreshStatusChainHeadRefV1, ...] = Field(
        default=(), max_length=FRESH_STATUS_MAX_RECONCILIATION_HEADS
    )

    @model_validator(mode="after")
    def validate_link(self) -> FreshStatusChainLinkV1:
        previous = (
            self.previous_observation_id,
            self.previous_observation_sha256,
            self.previous_chain_sha256,
            self.previous_claim_value,
        )
        if self.kind == "GENESIS":
            if any(item is not None for item in previous) or self.branch_heads:
                raise ValueError("GENESIS must not bind a predecessor or branch head")
        elif self.kind == "SUCCESSOR":
            if any(item is None for item in previous) or self.branch_heads:
                raise ValueError("SUCCESSOR must bind exactly one complete predecessor")
        else:
            if any(item is not None for item in previous):
                raise ValueError("RECONCILIATION must not use singular predecessor fields")
            if not 2 <= len(self.branch_heads) <= FRESH_STATUS_MAX_RECONCILIATION_HEADS:
                raise ValueError("RECONCILIATION must bind 2..8 branch heads")
            keys = tuple(
                (item.observation_id, item.observation_sha256, item.chain_sha256)
                for item in self.branch_heads
            )
            ids = tuple(item.observation_id for item in self.branch_heads)
            document_digests = tuple(item.observation_sha256 for item in self.branch_heads)
            chain_digests = tuple(item.chain_sha256 for item in self.branch_heads)
            if (
                len(keys) != len(set(keys))
                or len(ids) != len(set(ids))
                or len(document_digests) != len(set(document_digests))
                or len(chain_digests) != len(set(chain_digests))
                or keys != tuple(sorted(keys))
            ):
                raise ValueError("RECONCILIATION branch heads must be unique and sorted")
        return self


class FreshStatusCategoryResultV1(_FreshStatusModel):
    status_category: FreshStatusCategoryV1
    claim_value: FreshStatusClaimValueV1
    assessment_effect: FreshStatusAssessmentEffectV1
    observation_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        max_length=FRESH_STATUS_MAX_OBSERVATIONS
    )
    relied_on_observation_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        max_length=FRESH_STATUS_MAX_OBSERVATIONS
    )
    result_valid_until: str

    @field_validator("result_valid_until")
    @classmethod
    def validate_time(cls, value: str) -> str:
        return _utc_seconds(value, field="result_valid_until")

    @model_validator(mode="after")
    def validate_result(self) -> FreshStatusCategoryResultV1:
        all_keys = tuple(
            (item.observation_id, item.observation_sha256) for item in self.observation_refs
        )
        relied_keys = tuple(
            (item.observation_id, item.observation_sha256)
            for item in self.relied_on_observation_refs
        )
        all_ids = tuple(item.observation_id for item in self.observation_refs)
        all_digests = tuple(item.observation_sha256 for item in self.observation_refs)
        relied_ids = tuple(item.observation_id for item in self.relied_on_observation_refs)
        relied_digests = tuple(item.observation_sha256 for item in self.relied_on_observation_refs)
        if (
            len(all_keys) != len(set(all_keys))
            or len(all_ids) != len(set(all_ids))
            or len(all_digests) != len(set(all_digests))
            or all_keys != tuple(sorted(all_keys))
        ):
            raise ValueError("category observation refs must be unique and sorted")
        if (
            len(relied_keys) != len(set(relied_keys))
            or len(relied_ids) != len(set(relied_ids))
            or len(relied_digests) != len(set(relied_digests))
            or relied_keys != tuple(sorted(relied_keys))
        ):
            raise ValueError("relied-on observation refs must be unique and sorted")
        all_by_key = dict(zip(all_keys, self.observation_refs, strict=True))
        if any(
            all_by_key.get(key) != item
            for key, item in zip(relied_keys, self.relied_on_observation_refs, strict=True)
        ):
            raise ValueError(
                "relied-on observation refs must exactly match their complete category refs"
            )
        if any(
            item.status_category != self.status_category
            for item in (*self.observation_refs, *self.relied_on_observation_refs)
        ):
            raise ValueError("category result contains an observation from another category")
        if self.assessment_effect != _assessment_effect(self.status_category, self.claim_value):
            raise ValueError("category assessment effect drifted from fixed policy")
        if not self.relied_on_observation_refs and self.claim_value != "NOT_ASSESSED":
            raise ValueError("a category without usable observations must be NOT_ASSESSED")
        if self.relied_on_observation_refs and self.claim_value == "NOT_ASSESSED":
            raise ValueError("a category with usable observations cannot be NOT_ASSESSED")
        return self


class CreativeSampleRealAssetFreshStatusSourceObservationV1(_ZeroAuthorityFreshStatusModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-fresh-status-source-observation-v1"] = (
        "sdc.creative-sample-real-asset-fresh-status-source-observation-v1"
    )
    profile: Literal["creative-sample-real-asset-fresh-status-evidence-v3.0"] = (
        FRESH_STATUS_EVIDENCE_V1_PROFILE
    )
    policy_id: Literal["creative-sample-real-asset-fresh-status-evidence-policy"] = (
        FRESH_STATUS_EVIDENCE_V1_POLICY_ID
    )
    policy_version: Literal["3.0.0"] = FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION
    policy_document_sha256: Literal[
        "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"
    ] = FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256
    observation_id: str = Field(pattern=r"^real_asset_fresh_status_observation_v1_[0-9a-f]{20}$")
    subject_closure: FreshStatusSubjectClosureV1
    status_category: FreshStatusCategoryV1
    claim_value: FreshStatusClaimValueV1
    source_kind: FreshStatusSourceKindV1
    source_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    source_object_sha256: str = Field(pattern=_LOWER_SHA256)
    source_object_size_bytes: int = Field(ge=1)
    source_media_type: str = Field(pattern=_MEDIA_TYPE)
    source_locator_ref_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    source_event_at: str
    observed_at: str
    valid_from: str
    valid_until: str
    basis_code: FreshStatusBasisCodeV1 = Field(pattern=_PORTABLE_CODE)
    basis_note: str = Field(min_length=1, max_length=FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS)
    limitation_codes: tuple[FreshStatusLimitationCodeV1, ...] = Field(
        min_length=len(_MANDATORY_LIMITATION_CODES), max_length=len(_LIMITATION_CODE_ORDER)
    )
    chain_link: FreshStatusChainLinkV1
    status: Literal["FRESH_STATUS_SOURCE_OBSERVATION_RECORDED"] = (
        "FRESH_STATUS_SOURCE_OBSERVATION_RECORDED"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_exact_integer(cls, value: object) -> object:
        if isinstance(value, dict) and "source_object_size_bytes" in value:
            size = value["source_object_size_bytes"]
            if type(size) is not int or size < 1:
                raise ValueError("source_object_size_bytes must be an exact positive JSON integer")
        return value

    @field_validator("source_event_at", "observed_at", "valid_from", "valid_until")
    @classmethod
    def validate_times(cls, value: str, info: object) -> str:
        name = getattr(info, "field_name", None) or "Fresh Status timestamp"
        return _utc_seconds(value, field=name)

    @field_validator("basis_note")
    @classmethod
    def validate_basis_note(cls, value: str) -> str:
        return _portable_text(
            value, field="Fresh Status basis note", maximum=FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS
        )

    @model_validator(mode="after")
    def validate_observation(self) -> CreativeSampleRealAssetFreshStatusSourceObservationV1:
        limitations = self.limitation_codes
        if len(limitations) != len(set(limitations)) or limitations != tuple(
            sorted(limitations, key=_LIMITATION_CODE_ORDER.index)
        ):
            raise ValueError("limitation codes must be unique and in canonical policy order")
        if not set(_MANDATORY_LIMITATION_CODES) <= set(limitations):
            raise ValueError("every SourceObservation must retain the four mandatory limitations")
        expected_basis = _expected_basis_code(
            category=self.status_category,
            claim=self.claim_value,
            chain_kind=self.chain_link.kind,
            previous_claim=self.chain_link.previous_claim_value,
        )
        if self.basis_code != expected_basis:
            raise ValueError("basis_code does not match the fixed state-transition policy")
        event = _parse_utc(self.source_event_at)
        observed = _parse_utc(self.observed_at)
        valid_from = _parse_utc(self.valid_from)
        valid_until = _parse_utc(self.valid_until)
        if event > observed:
            raise ValueError("source_event_at cannot be later than observed_at")
        if valid_from >= valid_until:
            raise ValueError("Fresh Status validity must use a non-empty half-open interval")
        if valid_until - valid_from > timedelta(seconds=FRESH_STATUS_MAX_WINDOW_SECONDS):
            raise ValueError("Fresh Status validity exceeds the fixed 86400-second maximum")
        digests = {
            self.subject_closure.pack_manifest_sha256,
            self.subject_closure.rights_manifest_sha256,
            self.subject_closure.use_plan_sha256,
            self.subject_closure.use_scope_review_record_sha256,
            self.policy_document_sha256,
            self.subject_closure.closure_profile_document_sha256,
        }
        source_digests = {self.source_identity_ref_sha256, self.source_object_sha256}
        if self.source_locator_ref_sha256 is not None:
            source_digests.add(self.source_locator_ref_sha256)
        if len(source_digests) != 2 + (self.source_locator_ref_sha256 is not None):
            raise ValueError("source identity, object, and locator digests must be distinct")
        if source_digests & digests:
            raise ValueError("source digests must not alias subject or policy content")
        if self.chain_link.previous_observation_id == self.observation_id:
            raise ValueError("a SourceObservation cannot reference itself as predecessor")
        if any(head.observation_id == self.observation_id for head in self.chain_link.branch_heads):
            raise ValueError("a SourceObservation cannot reconcile itself")
        expected = stable_id(
            "real_asset_fresh_status_observation_v1",
            self.model_dump(mode="json", exclude={"observation_id"}),
        )
        if self.observation_id != expected:
            raise ValueError("SourceObservation ID must bind its complete canonical content")
        return self


class CreativeSampleRealAssetFreshStatusRequestV1(_ZeroAuthorityFreshStatusModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-fresh-status-request-v1"] = (
        "sdc.creative-sample-real-asset-fresh-status-request-v1"
    )
    profile: Literal["creative-sample-real-asset-fresh-status-evidence-v3.0"] = (
        FRESH_STATUS_EVIDENCE_V1_PROFILE
    )
    policy_id: Literal["creative-sample-real-asset-fresh-status-evidence-policy"] = (
        FRESH_STATUS_EVIDENCE_V1_POLICY_ID
    )
    policy_version: Literal["3.0.0"] = FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION
    policy_document_sha256: Literal[
        "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"
    ] = FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256
    request_id: str = Field(pattern=r"^real_asset_fresh_status_request_v1_[0-9a-f]{20}$")
    subject_closure: FreshStatusSubjectClosureV1
    preparer_role: Literal["STATUS_PREPARER"] = "STATUS_PREPARER"
    preparer_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    requested_at: str
    request_valid_until: str
    request_basis: str = Field(min_length=1, max_length=FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS)
    observation_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        min_length=1, max_length=FRESH_STATUS_MAX_OBSERVATIONS
    )
    status: Literal["FRESH_STATUS_REVIEW_REQUESTED"] = "FRESH_STATUS_REVIEW_REQUESTED"

    @field_validator("requested_at", "request_valid_until")
    @classmethod
    def validate_times(cls, value: str, info: object) -> str:
        name = getattr(info, "field_name", None) or "Fresh Status request timestamp"
        return _utc_seconds(value, field=name)

    @field_validator("request_basis")
    @classmethod
    def validate_basis(cls, value: str) -> str:
        return _portable_text(
            value,
            field="Fresh Status request basis",
            maximum=FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS,
        )

    @model_validator(mode="after")
    def validate_request(self) -> CreativeSampleRealAssetFreshStatusRequestV1:
        requested = _parse_utc(self.requested_at)
        if _parse_utc(self.request_valid_until) != requested + timedelta(
            seconds=FRESH_STATUS_MAX_WINDOW_SECONDS
        ):
            raise ValueError("Fresh Status request must use the fixed exclusive 24-hour window")
        keys = tuple(
            (item.observation_id, item.observation_sha256) for item in self.observation_refs
        )
        ids = tuple(item.observation_id for item in self.observation_refs)
        digests = tuple(item.observation_sha256 for item in self.observation_refs)
        if (
            len(keys) != len(set(keys))
            or len(ids) != len(set(ids))
            or len(digests) != len(set(digests))
            or keys != tuple(sorted(keys))
        ):
            raise ValueError("request observation refs must be unique and sorted by ID/SHA")
        if self.preparer_identity_ref_sha256 in {
            self.policy_document_sha256,
            self.subject_closure.pack_manifest_sha256,
            self.subject_closure.rights_manifest_sha256,
            self.subject_closure.use_plan_sha256,
            self.subject_closure.use_scope_review_record_sha256,
            *(item.observation_sha256 for item in self.observation_refs),
        }:
            raise ValueError("Preparer identity reference aliases content or policy bytes")
        expected = stable_id(
            "real_asset_fresh_status_request_v1",
            self.model_dump(mode="json", exclude={"request_id"}),
        )
        if self.request_id != expected:
            raise ValueError("Fresh Status Request ID must bind its complete canonical content")
        return self


class CreativeSampleRealAssetFreshStatusInstructionV1(_ZeroAuthorityFreshStatusModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-fresh-status-instruction-v1"] = (
        "sdc.creative-sample-real-asset-fresh-status-instruction-v1"
    )
    profile: Literal["creative-sample-real-asset-fresh-status-evidence-v3.0"] = (
        FRESH_STATUS_EVIDENCE_V1_PROFILE
    )
    policy_id: Literal["creative-sample-real-asset-fresh-status-evidence-policy"] = (
        FRESH_STATUS_EVIDENCE_V1_POLICY_ID
    )
    policy_version: Literal["3.0.0"] = FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION
    policy_document_sha256: Literal[
        "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"
    ] = FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256
    instruction_id: str = Field(pattern=r"^real_asset_fresh_status_instruction_v1_[0-9a-f]{20}$")
    request_id: str = Field(pattern=r"^real_asset_fresh_status_request_v1_[0-9a-f]{20}$")
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    subject_closure: FreshStatusSubjectClosureV1
    preparer_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    checker_role: Literal["STATUS_CHECKER"] = "STATUS_CHECKER"
    checker_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    requested_at: str
    request_valid_until: str
    evaluated_at: str
    category_results: tuple[FreshStatusCategoryResultV1, ...] = Field(
        min_length=len(_CATEGORY_ORDER), max_length=len(_CATEGORY_ORDER)
    )
    checker_basis: str = Field(min_length=1, max_length=FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS)
    status: Literal["FRESH_STATUS_CHECK_RECORDED"] = "FRESH_STATUS_CHECK_RECORDED"

    @field_validator("requested_at", "request_valid_until", "evaluated_at")
    @classmethod
    def validate_times(cls, value: str, info: object) -> str:
        name = getattr(info, "field_name", None) or "Fresh Status instruction timestamp"
        return _utc_seconds(value, field=name)

    @field_validator("checker_basis")
    @classmethod
    def validate_basis(cls, value: str) -> str:
        return _portable_text(
            value,
            field="Fresh Status Checker basis",
            maximum=FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS,
        )

    @model_validator(mode="after")
    def validate_instruction(self) -> CreativeSampleRealAssetFreshStatusInstructionV1:
        if tuple(item.status_category for item in self.category_results) != _CATEGORY_ORDER:
            raise ValueError("category results must use the complete fixed policy order")
        requested = _parse_utc(self.requested_at)
        if _parse_utc(self.request_valid_until) != requested + timedelta(
            seconds=FRESH_STATUS_MAX_WINDOW_SECONDS
        ):
            raise ValueError("Instruction must retain the fixed request window")
        evaluated = _parse_utc(self.evaluated_at)
        if evaluated < requested or evaluated >= _parse_utc(self.request_valid_until):
            raise ValueError("Fresh Status instruction is outside the request window")
        for result in self.category_results:
            if result.relied_on_observation_refs and _parse_utc(result.result_valid_until) <= (
                evaluated
            ):
                raise ValueError("a relied-on category result must remain valid after evaluation")
            if not result.relied_on_observation_refs and result.result_valid_until != (
                self.evaluated_at
            ):
                raise ValueError("an unassessed category result must expire at evaluated_at")
        if self.preparer_identity_ref_sha256 == self.checker_identity_ref_sha256:
            raise ValueError("Preparer and Checker references must be procedurally distinct")
        if self.checker_identity_ref_sha256 in {
            self.policy_document_sha256,
            self.request_sha256,
            self.subject_closure.pack_manifest_sha256,
            self.subject_closure.rights_manifest_sha256,
            self.subject_closure.use_plan_sha256,
            self.subject_closure.use_scope_review_record_sha256,
        }:
            raise ValueError("Checker identity reference aliases content or policy bytes")
        expected = stable_id(
            "real_asset_fresh_status_instruction_v1",
            self.model_dump(mode="json", exclude={"instruction_id"}),
        )
        if self.instruction_id != expected:
            raise ValueError("Fresh Status Instruction ID must bind its canonical content")
        return self


class CreativeSampleRealAssetFreshStatusDecisionV1(_ZeroAuthorityFreshStatusModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-fresh-status-decision-v1"] = (
        "sdc.creative-sample-real-asset-fresh-status-decision-v1"
    )
    profile: Literal["creative-sample-real-asset-fresh-status-evidence-v3.0"] = (
        FRESH_STATUS_EVIDENCE_V1_PROFILE
    )
    policy_id: Literal["creative-sample-real-asset-fresh-status-evidence-policy"] = (
        FRESH_STATUS_EVIDENCE_V1_POLICY_ID
    )
    policy_version: Literal["3.0.0"] = FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION
    policy_document_sha256: Literal[
        "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"
    ] = FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256
    decision_id: str = Field(pattern=r"^real_asset_fresh_status_decision_v1_[0-9a-f]{20}$")
    request_id: str = Field(pattern=r"^real_asset_fresh_status_request_v1_[0-9a-f]{20}$")
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    instruction_id: str = Field(pattern=r"^real_asset_fresh_status_instruction_v1_[0-9a-f]{20}$")
    instruction_sha256: str = Field(pattern=_LOWER_SHA256)
    subject_closure: FreshStatusSubjectClosureV1
    evaluated_at: str
    decision_at: str
    status_valid_until: str
    disposition: FreshStatusDispositionV1
    category_results: tuple[FreshStatusCategoryResultV1, ...] = Field(
        min_length=len(_CATEGORY_ORDER), max_length=len(_CATEGORY_ORDER)
    )
    blocking_categories: tuple[FreshStatusCategoryV1, ...] = Field(max_length=7)
    indeterminate_categories: tuple[FreshStatusCategoryV1, ...] = Field(max_length=7)
    status: Literal["FRESH_STATUS_EVIDENCE_DECISION_RECORDED"] = (
        "FRESH_STATUS_EVIDENCE_DECISION_RECORDED"
    )

    @field_validator("evaluated_at", "decision_at", "status_valid_until")
    @classmethod
    def validate_times(cls, value: str, info: object) -> str:
        name = getattr(info, "field_name", None) or "Fresh Status decision timestamp"
        return _utc_seconds(value, field=name)

    @model_validator(mode="after")
    def validate_decision(self) -> CreativeSampleRealAssetFreshStatusDecisionV1:
        if self.evaluated_at != self.decision_at:
            raise ValueError("Decision time must equal the explicit Checker evaluation time")
        if _parse_utc(self.status_valid_until) < _parse_utc(self.decision_at):
            raise ValueError("status_valid_until cannot predate decision_at")
        if tuple(item.status_category for item in self.category_results) != _CATEGORY_ORDER:
            raise ValueError("Decision category results must retain fixed policy order")
        expected_blocking = tuple(
            item.status_category
            for item in self.category_results
            if item.assessment_effect == "BLOCKING"
        )
        expected_indeterminate = tuple(
            item.status_category
            for item in self.category_results
            if item.assessment_effect == "INDETERMINATE"
        )
        if self.blocking_categories != expected_blocking:
            raise ValueError("blocking categories drifted from category results")
        if self.indeterminate_categories != expected_indeterminate:
            raise ValueError("indeterminate categories drifted from category results")
        if expected_blocking:
            expected_disposition = "BLOCKING_STATUS_RECORDED"
        elif expected_indeterminate:
            expected_disposition = "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"
        else:
            expected_disposition = "NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET"
        if self.disposition != expected_disposition:
            raise ValueError("Decision disposition drifted from fixed compiler policy")
        expected = stable_id(
            "real_asset_fresh_status_decision_v1",
            self.model_dump(mode="json", exclude={"decision_id"}),
        )
        if self.decision_id != expected:
            raise ValueError("Fresh Status Decision ID must bind its canonical content")
        return self


class CreativeSampleRealAssetFreshStatusEvidenceRecordV1(_ZeroAuthorityFreshStatusModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-fresh-status-evidence-record-v1"] = (
        "sdc.creative-sample-real-asset-fresh-status-evidence-record-v1"
    )
    profile: Literal["creative-sample-real-asset-fresh-status-evidence-v3.0"] = (
        FRESH_STATUS_EVIDENCE_V1_PROFILE
    )
    policy_id: Literal["creative-sample-real-asset-fresh-status-evidence-policy"] = (
        FRESH_STATUS_EVIDENCE_V1_POLICY_ID
    )
    policy_version: Literal["3.0.0"] = FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION
    policy_document_sha256: Literal[
        "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"
    ] = FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256
    record_id: str = Field(pattern=r"^real_asset_fresh_status_evidence_record_v1_[0-9a-f]{20}$")
    subject_closure: FreshStatusSubjectClosureV1
    request: CreativeSampleRealAssetFreshStatusRequestV1
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    instruction: CreativeSampleRealAssetFreshStatusInstructionV1
    instruction_sha256: str = Field(pattern=_LOWER_SHA256)
    decision: CreativeSampleRealAssetFreshStatusDecisionV1
    decision_sha256: str = Field(pattern=_LOWER_SHA256)

    @model_validator(mode="after")
    def validate_record(self) -> CreativeSampleRealAssetFreshStatusEvidenceRecordV1:
        if self.request_sha256 != _sha256(_canonical_document(self.request)):
            raise ValueError("EvidenceRecord Request digest drifted")
        if self.instruction_sha256 != _sha256(_canonical_document(self.instruction)):
            raise ValueError("EvidenceRecord Instruction digest drifted")
        if self.decision_sha256 != _sha256(_canonical_document(self.decision)):
            raise ValueError("EvidenceRecord Decision digest drifted")
        if not (
            self.subject_closure
            == self.request.subject_closure
            == self.instruction.subject_closure
            == self.decision.subject_closure
        ):
            raise ValueError("EvidenceRecord modules do not bind one subject closure")
        if (
            self.instruction.request_id != self.request.request_id
            or self.instruction.request_sha256 != self.request_sha256
            or self.decision.request_id != self.request.request_id
            or self.decision.request_sha256 != self.request_sha256
            or self.decision.instruction_id != self.instruction.instruction_id
            or self.decision.instruction_sha256 != self.instruction_sha256
        ):
            raise ValueError("EvidenceRecord module digest chain is broken")
        if (
            self.instruction.preparer_identity_ref_sha256
            != self.request.preparer_identity_ref_sha256
            or self.instruction.requested_at != self.request.requested_at
            or self.instruction.request_valid_until != self.request.request_valid_until
        ):
            raise ValueError("EvidenceRecord Instruction metadata drifted from Request")
        instruction_refs = tuple(
            sorted(
                (
                    item
                    for result in self.instruction.category_results
                    for item in result.observation_refs
                ),
                key=lambda item: (item.observation_id, item.observation_sha256),
            )
        )
        if instruction_refs != self.request.observation_refs:
            raise ValueError(
                "EvidenceRecord Instruction does not cover the exact Request observation set"
            )
        if (
            self.decision.category_results != self.instruction.category_results
            or self.decision.evaluated_at != self.instruction.evaluated_at
            or self.decision.decision_at != self.instruction.evaluated_at
        ):
            raise ValueError("EvidenceRecord Decision drifted from Instruction results")
        relied_until = tuple(
            item.result_valid_until
            for item in self.instruction.category_results
            if item.relied_on_observation_refs
        )
        expected_status_valid_until = (
            min((self.request.request_valid_until, *relied_until))
            if relied_until
            else self.instruction.evaluated_at
        )
        if self.decision.status_valid_until != expected_status_valid_until:
            raise ValueError("EvidenceRecord Decision horizon drifted from explicit evidence")
        expected = stable_id(
            "real_asset_fresh_status_evidence_record_v1",
            self.model_dump(mode="json", exclude={"record_id"}),
        )
        if self.record_id != expected:
            raise ValueError("EvidenceRecord ID must bind all three modules and digests")
        return self


def _revalidate[ModelT: BaseModel](value: ModelT, model: type[ModelT], *, field: str) -> ModelT:
    try:
        before = _canonical_document(value)
        rebuilt = model.model_validate(value.model_dump(mode="python"), strict=True)
        after = _canonical_document(rebuilt)
    except (AttributeError, TypeError, ValidationError, ValueError) as exc:
        raise RealAssetFreshStatusEvidenceV30Error(f"{field} violates its strict contract") from exc
    if before != after:
        raise RealAssetFreshStatusEvidenceV30Error(
            f"{field} changes canonical bytes during strict revalidation"
        )
    return rebuilt


def _bounded_document[ModelT: BaseModel](
    value: ModelT, *, maximum_bytes: int, label: str
) -> ModelT:
    try:
        size = len(_canonical_document(value))
    except (TypeError, UnicodeError, ValueError) as exc:
        raise RealAssetFreshStatusEvidenceV30Error(
            f"{label} cannot be rendered as canonical UTF-8"
        ) from exc
    if size > maximum_bytes:
        raise RealAssetFreshStatusEvidenceV30Error(
            f"{label} exceeds its {maximum_bytes}-byte canonical limit"
        )
    return value


def _observation_ref(
    observation: CreativeSampleRealAssetFreshStatusSourceObservationV1,
) -> FreshStatusObservationRefV1:
    return FreshStatusObservationRefV1(
        observation_id=observation.observation_id,
        observation_sha256=_sha256(_canonical_document(observation)),
        status_category=observation.status_category,
        source_identity_ref_sha256=observation.source_identity_ref_sha256,
        chain_sha256=derive_fresh_status_observation_chain_sha256_v1(observation),
    )


def _sorted_observations(
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...]:
    if not 1 <= len(observations) <= FRESH_STATUS_MAX_OBSERVATIONS:
        raise RealAssetFreshStatusEvidenceV30Error("1..32 SourceObservations are required")
    rebuilt = tuple(
        _revalidate(
            item,
            CreativeSampleRealAssetFreshStatusSourceObservationV1,
            field="observation",
        )
        for item in observations
    )
    keys = tuple((item.observation_id, _sha256(_canonical_document(item))) for item in rebuilt)
    ids = tuple(item[0] for item in keys)
    digests = tuple(item[1] for item in keys)
    if (
        len(keys) != len(set(keys))
        or len(ids) != len(set(ids))
        or len(digests) != len(set(digests))
    ):
        raise RealAssetFreshStatusEvidenceV30Error("SourceObservations must be unique")
    return tuple(
        item
        for _, item in sorted(
            zip(keys, rebuilt, strict=True),
            key=lambda pair: pair[0],
        )
    )


def build_fresh_status_subject_closure_v1(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    rights_manifest: CreativeSampleRealAssetRightsManifestV2,
    use_plan: CreativeSampleRealAssetUsePlanV1,
    use_scope_review_record: CreativeSampleRealAssetUseScopeReviewRecordV1,
) -> FreshStatusSubjectClosureV1:
    """Bind the four public subject artifacts; full upstream replay is a separate verifier."""

    pack = _revalidate(pack, CreativeSampleFrozenRealAssetPackManifest, field="Frozen Pack")
    rights_manifest = _revalidate(
        rights_manifest, CreativeSampleRealAssetRightsManifestV2, field="Rights Manifest"
    )
    use_plan = _revalidate(use_plan, CreativeSampleRealAssetUsePlanV1, field="Use Plan")
    use_scope_review_record = _revalidate(
        use_scope_review_record,
        CreativeSampleRealAssetUseScopeReviewRecordV1,
        field="Use Scope ReviewRecord",
    )
    if rights_manifest.pack_id != pack.pack_id:
        raise RealAssetFreshStatusEvidenceV30Error("Rights Manifest does not bind the Frozen Pack")
    if (
        use_plan.manifest_closure.pack_id != pack.pack_id
        or use_plan.manifest_closure.pack_manifest_sha256 != _sha256(_canonical_document(pack))
        or use_plan.manifest_closure.rights_manifest_id != rights_manifest.manifest_id
        or use_plan.manifest_closure.rights_manifest_sha256
        != _sha256(_canonical_document(rights_manifest))
    ):
        raise RealAssetFreshStatusEvidenceV30Error(
            "Use Plan does not bind the exact Frozen Pack and Rights Manifest"
        )
    if (
        use_scope_review_record.use_plan_id != use_plan.plan_id
        or use_scope_review_record.use_plan_sha256 != _sha256(_canonical_document(use_plan))
    ):
        raise RealAssetFreshStatusEvidenceV30Error(
            "Use Scope ReviewRecord does not bind the exact Use Plan"
        )
    payload: dict[str, object] = {
        "closure_profile": FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE,
        "closure_profile_document_sha256": (
            FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE_DOCUMENT_SHA256
        ),
        "pack_id": pack.pack_id,
        "pack_manifest_sha256": _sha256(_canonical_document(pack)),
        "rights_manifest_id": rights_manifest.manifest_id,
        "rights_manifest_sha256": _sha256(_canonical_document(rights_manifest)),
        "use_plan_id": use_plan.plan_id,
        "use_plan_sha256": _sha256(_canonical_document(use_plan)),
        "use_scope_review_record_id": use_scope_review_record.record_id,
        "use_scope_review_record_sha256": _sha256(_canonical_document(use_scope_review_record)),
    }
    try:
        return FreshStatusSubjectClosureV1.model_validate(
            {
                "closure_id": _stable_contract_id(
                    "real_asset_fresh_status_subject_closure_v1", payload
                ),
                **payload,
            },
            strict=True,
        )
    except ValidationError as exc:
        raise RealAssetFreshStatusEvidenceV30Error(
            "Fresh Status subject closure could not be built"
        ) from exc


def derive_fresh_status_observation_chain_sha256_v1(
    observation: CreativeSampleRealAssetFreshStatusSourceObservationV1,
) -> str:
    """Derive a non-authorizing chain handle from one exact canonical Observation."""

    observation = _revalidate(
        observation,
        CreativeSampleRealAssetFreshStatusSourceObservationV1,
        field="SourceObservation",
    )
    return _sha256(_CHAIN_DOMAIN + _canonical_document(observation))


def _same_source_chain(
    first: CreativeSampleRealAssetFreshStatusSourceObservationV1,
    second: CreativeSampleRealAssetFreshStatusSourceObservationV1,
) -> bool:
    return (
        first.subject_closure == second.subject_closure
        and first.status_category == second.status_category
        and first.source_kind == second.source_kind
        and first.source_identity_ref_sha256 == second.source_identity_ref_sha256
        and first.profile == second.profile
        and first.policy_version == second.policy_version
    )


def build_fresh_status_source_observation_v1(
    *,
    subject_closure: FreshStatusSubjectClosureV1,
    status_category: FreshStatusCategoryV1,
    claim_value: FreshStatusClaimValueV1,
    source_kind: FreshStatusSourceKindV1,
    source_identity_ref_sha256: str,
    source_object_sha256: str,
    source_object_size_bytes: int,
    source_media_type: str,
    source_event_at: str,
    observed_at: str,
    valid_from: str,
    valid_until: str,
    basis_code: FreshStatusBasisCodeV1,
    basis_note: str,
    limitation_codes: tuple[FreshStatusLimitationCodeV1, ...],
    source_locator_ref_sha256: str | None = None,
    chain_kind: FreshStatusChainLinkKindV1 = "GENESIS",
    predecessor: CreativeSampleRealAssetFreshStatusSourceObservationV1 | None = None,
    reconciliation_heads: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...] = (),
) -> CreativeSampleRealAssetFreshStatusSourceObservationV1:
    """Build one Observation with GENESIS, one-step SUCCESSOR, or structural reconciliation."""

    subject_closure = _revalidate(
        subject_closure, FreshStatusSubjectClosureV1, field="subject closure"
    )
    if chain_kind == "GENESIS":
        if predecessor is not None or reconciliation_heads:
            raise RealAssetFreshStatusEvidenceV30Error(
                "GENESIS cannot receive predecessor or reconciliation heads"
            )
        chain_link = FreshStatusChainLinkV1(kind="GENESIS")
    elif chain_kind == "SUCCESSOR":
        if predecessor is None or reconciliation_heads:
            raise RealAssetFreshStatusEvidenceV30Error(
                "SUCCESSOR requires exactly one explicit predecessor"
            )
        predecessor = _revalidate(
            predecessor,
            CreativeSampleRealAssetFreshStatusSourceObservationV1,
            field="predecessor SourceObservation",
        )
        candidate_key = (
            subject_closure,
            status_category,
            source_kind,
            source_identity_ref_sha256,
        )
        predecessor_key = (
            predecessor.subject_closure,
            predecessor.status_category,
            predecessor.source_kind,
            predecessor.source_identity_ref_sha256,
        )
        if candidate_key != predecessor_key:
            raise RealAssetFreshStatusEvidenceV30Error(
                "SUCCESSOR must retain the exact subject/category/source chain key"
            )
        if claim_value not in _ALLOWED_SUCCESSORS[predecessor.claim_value]:
            raise RealAssetFreshStatusEvidenceV30Error("illegal Fresh Status state transition")
        chain_link = FreshStatusChainLinkV1(
            kind="SUCCESSOR",
            previous_observation_id=predecessor.observation_id,
            previous_observation_sha256=_sha256(_canonical_document(predecessor)),
            previous_chain_sha256=derive_fresh_status_observation_chain_sha256_v1(predecessor),
            previous_claim_value=predecessor.claim_value,
        )
    elif chain_kind == "RECONCILIATION":
        if predecessor is not None or not (
            2 <= len(reconciliation_heads) <= FRESH_STATUS_MAX_RECONCILIATION_HEADS
        ):
            raise RealAssetFreshStatusEvidenceV30Error(
                "RECONCILIATION requires 2..8 explicit branch heads"
            )
        heads = tuple(
            _revalidate(
                item,
                CreativeSampleRealAssetFreshStatusSourceObservationV1,
                field="reconciliation branch head",
            )
            for item in reconciliation_heads
        )
        candidate_key = (
            subject_closure,
            status_category,
            source_kind,
            source_identity_ref_sha256,
        )
        if any(
            (
                item.subject_closure,
                item.status_category,
                item.source_kind,
                item.source_identity_ref_sha256,
            )
            != candidate_key
            for item in heads
        ):
            raise RealAssetFreshStatusEvidenceV30Error(
                "RECONCILIATION heads must share the candidate source-chain key"
            )
        refs = tuple(
            sorted(
                (
                    FreshStatusChainHeadRefV1(
                        observation_id=item.observation_id,
                        observation_sha256=_sha256(_canonical_document(item)),
                        chain_sha256=derive_fresh_status_observation_chain_sha256_v1(item),
                    )
                    for item in heads
                ),
                key=lambda item: (
                    item.observation_id,
                    item.observation_sha256,
                    item.chain_sha256,
                ),
            )
        )
        if (
            len(refs) != len({item.observation_id for item in refs})
            or len(refs) != len({item.observation_sha256 for item in refs})
            or len(refs) != len({item.chain_sha256 for item in refs})
        ):
            raise RealAssetFreshStatusEvidenceV30Error(
                "RECONCILIATION branch heads must use distinct IDs and digests"
            )
        chain_link = FreshStatusChainLinkV1(kind="RECONCILIATION", branch_heads=refs)
    else:
        raise RealAssetFreshStatusEvidenceV30Error("unknown Fresh Status chain kind")
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-fresh-status-source-observation-v1",
        "profile": FRESH_STATUS_EVIDENCE_V1_PROFILE,
        "policy_id": FRESH_STATUS_EVIDENCE_V1_POLICY_ID,
        "policy_version": FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
        "policy_document_sha256": FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256,
        "subject_closure": subject_closure,
        "status_category": status_category,
        "claim_value": claim_value,
        "source_kind": source_kind,
        "source_identity_ref_sha256": source_identity_ref_sha256,
        "source_object_sha256": source_object_sha256,
        "source_object_size_bytes": source_object_size_bytes,
        "source_media_type": source_media_type,
        "source_locator_ref_sha256": source_locator_ref_sha256,
        "source_event_at": source_event_at,
        "observed_at": observed_at,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "basis_code": basis_code,
        "basis_note": basis_note,
        "limitation_codes": limitation_codes,
        "chain_link": chain_link,
        "status": "FRESH_STATUS_SOURCE_OBSERVATION_RECORDED",
        **_zero_authority_payload(),
    }
    try:
        return _bounded_document(
            CreativeSampleRealAssetFreshStatusSourceObservationV1.model_validate(
                {
                    "observation_id": _stable_contract_id(
                        "real_asset_fresh_status_observation_v1", payload
                    ),
                    **payload,
                },
                strict=True,
            ),
            maximum_bytes=FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES,
            label="SourceObservation",
        )
    except ValidationError as exc:
        raise RealAssetFreshStatusEvidenceV30Error("SourceObservation could not be built") from exc


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


def verify_fresh_status_source_observation_internal_v1(
    observation: CreativeSampleRealAssetFreshStatusSourceObservationV1,
) -> CreativeSampleRealAssetFreshStatusSourceObservationV1:
    return _revalidate(
        observation,
        CreativeSampleRealAssetFreshStatusSourceObservationV1,
        field="SourceObservation",
    )


def verify_fresh_status_source_observation_link_v1(
    *,
    observation: CreativeSampleRealAssetFreshStatusSourceObservationV1,
    predecessors: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> CreativeSampleRealAssetFreshStatusSourceObservationV1:
    """Verify only the explicitly supplied single link; this is not full-chain verification."""

    observation = verify_fresh_status_source_observation_internal_v1(observation)
    predecessors = tuple(
        verify_fresh_status_source_observation_internal_v1(item) for item in predecessors
    )
    link = observation.chain_link
    if link.kind == "GENESIS":
        if predecessors:
            raise RealAssetFreshStatusEvidenceV30Error("GENESIS must receive no predecessor")
        return observation
    if link.kind == "SUCCESSOR":
        if len(predecessors) != 1:
            raise RealAssetFreshStatusEvidenceV30Error(
                "SUCCESSOR verification requires one predecessor"
            )
        previous = predecessors[0]
        expected = (
            previous.observation_id,
            _sha256(_canonical_document(previous)),
            derive_fresh_status_observation_chain_sha256_v1(previous),
            previous.claim_value,
        )
        actual = (
            link.previous_observation_id,
            link.previous_observation_sha256,
            link.previous_chain_sha256,
            link.previous_claim_value,
        )
        if actual != expected or not _same_source_chain(observation, previous):
            raise RealAssetFreshStatusEvidenceV30Error(
                "SUCCESSOR does not bind the exact same-chain predecessor"
            )
        if observation.claim_value not in _ALLOWED_SUCCESSORS[previous.claim_value]:
            raise RealAssetFreshStatusEvidenceV30Error("illegal Fresh Status state transition")
        return observation
    expected_heads = tuple(
        sorted(
            (
                FreshStatusChainHeadRefV1(
                    observation_id=item.observation_id,
                    observation_sha256=_sha256(_canonical_document(item)),
                    chain_sha256=derive_fresh_status_observation_chain_sha256_v1(item),
                )
                for item in predecessors
            ),
            key=lambda item: (item.observation_id, item.observation_sha256, item.chain_sha256),
        )
    )
    if link.branch_heads != expected_heads or not all(
        _same_source_chain(observation, item) for item in predecessors
    ):
        raise RealAssetFreshStatusEvidenceV30Error(
            "RECONCILIATION does not bind the exact supplied same-chain branch heads"
        )
    return observation


def build_fresh_status_request_v1(
    *,
    subject_closure: FreshStatusSubjectClosureV1,
    preparer_identity_ref_sha256: str,
    requested_at: str,
    request_basis: str,
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> CreativeSampleRealAssetFreshStatusRequestV1:
    """Build the Preparer-owned Request from one explicit finite Observation set."""

    subject_closure = _revalidate(
        subject_closure, FreshStatusSubjectClosureV1, field="subject closure"
    )
    observations = _sorted_observations(observations)
    if any(item.subject_closure != subject_closure for item in observations):
        raise RealAssetFreshStatusEvidenceV30Error(
            "every SourceObservation must bind the exact Request subject closure"
        )
    try:
        requested_at = _utc_seconds(requested_at, field="requested_at")
        request_valid_until = _format_utc(
            _parse_utc(requested_at) + timedelta(seconds=FRESH_STATUS_MAX_WINDOW_SECONDS)
        )
    except (OverflowError, ValueError) as exc:
        raise RealAssetFreshStatusEvidenceV30Error("requested_at is invalid") from exc
    refs = tuple(_observation_ref(item) for item in observations)
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-fresh-status-request-v1",
        "profile": FRESH_STATUS_EVIDENCE_V1_PROFILE,
        "policy_id": FRESH_STATUS_EVIDENCE_V1_POLICY_ID,
        "policy_version": FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
        "policy_document_sha256": FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256,
        "subject_closure": subject_closure,
        "preparer_role": "STATUS_PREPARER",
        "preparer_identity_ref_sha256": preparer_identity_ref_sha256,
        "requested_at": requested_at,
        "request_valid_until": request_valid_until,
        "request_basis": request_basis,
        "observation_refs": refs,
        "status": "FRESH_STATUS_REVIEW_REQUESTED",
        **_zero_authority_payload(),
    }
    try:
        return _bounded_document(
            CreativeSampleRealAssetFreshStatusRequestV1.model_validate(
                {
                    "request_id": _stable_contract_id(
                        "real_asset_fresh_status_request_v1", payload
                    ),
                    **payload,
                },
                strict=True,
            ),
            maximum_bytes=FRESH_STATUS_RECORD_MAX_BYTES,
            label="Fresh Status Request",
        )
    except ValidationError as exc:
        raise RealAssetFreshStatusEvidenceV30Error(
            "Fresh Status Request could not be built"
        ) from exc


def _category_result(
    *,
    category: FreshStatusCategoryV1,
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
    evaluated_at: str,
) -> FreshStatusCategoryResultV1:
    all_items = tuple(item for item in observations if item.status_category == category)
    evaluated = _parse_utc(evaluated_at)
    usable = tuple(
        item
        for item in all_items
        if item.claim_value != "NOT_ASSESSED"
        and max(_parse_utc(item.observed_at), _parse_utc(item.valid_from))
        <= evaluated
        < _parse_utc(item.valid_until)
    )
    claims = {item.claim_value for item in usable}
    successor_predecessors = tuple(
        item.chain_link.previous_observation_id
        for item in usable
        if item.chain_link.kind == "SUCCESSOR"
    )
    explicit_fork = len(successor_predecessors) != len(set(successor_predecessors))
    if not usable:
        claim: FreshStatusClaimValueV1 = "NOT_ASSESSED"
        valid_until = evaluated_at
    elif len(claims) == 1 and not explicit_fork:
        claim = usable[0].claim_value
        valid_until = min(item.valid_until for item in usable)
    else:
        claim = "CONFLICT"
        valid_until = min(item.valid_until for item in usable)
    return FreshStatusCategoryResultV1(
        status_category=category,
        claim_value=claim,
        assessment_effect=_assessment_effect(category, claim),
        observation_refs=tuple(_observation_ref(item) for item in all_items),
        relied_on_observation_refs=tuple(_observation_ref(item) for item in usable),
        result_valid_until=valid_until,
    )


def _observations_match_request(
    request: CreativeSampleRealAssetFreshStatusRequestV1,
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...]:
    observations = _sorted_observations(observations)
    refs = tuple(_observation_ref(item) for item in observations)
    if refs != request.observation_refs:
        raise RealAssetFreshStatusEvidenceV30Error(
            "explicit SourceObservations do not match the exact Request set"
        )
    if any(item.subject_closure != request.subject_closure for item in observations):
        raise RealAssetFreshStatusEvidenceV30Error(
            "SourceObservation subject closure drifted from Request"
        )
    return observations


def build_fresh_status_instruction_v1(
    *,
    request: CreativeSampleRealAssetFreshStatusRequestV1,
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
    checker_identity_ref_sha256: str,
    evaluated_at: str,
    checker_basis: str,
) -> CreativeSampleRealAssetFreshStatusInstructionV1:
    """Build the Checker module; category results are derived, not caller-selected."""

    request = _revalidate(
        request, CreativeSampleRealAssetFreshStatusRequestV1, field="Fresh Status Request"
    )
    observations = _observations_match_request(request, observations)
    try:
        evaluated_at = _utc_seconds(evaluated_at, field="evaluated_at")
    except ValueError as exc:
        raise RealAssetFreshStatusEvidenceV30Error("evaluated_at is invalid") from exc
    results = tuple(
        _category_result(category=category, observations=observations, evaluated_at=evaluated_at)
        for category in _CATEGORY_ORDER
    )
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-fresh-status-instruction-v1",
        "profile": FRESH_STATUS_EVIDENCE_V1_PROFILE,
        "policy_id": FRESH_STATUS_EVIDENCE_V1_POLICY_ID,
        "policy_version": FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
        "policy_document_sha256": FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256,
        "request_id": request.request_id,
        "request_sha256": _sha256(_canonical_document(request)),
        "subject_closure": request.subject_closure,
        "preparer_identity_ref_sha256": request.preparer_identity_ref_sha256,
        "checker_role": "STATUS_CHECKER",
        "checker_identity_ref_sha256": checker_identity_ref_sha256,
        "requested_at": request.requested_at,
        "request_valid_until": request.request_valid_until,
        "evaluated_at": evaluated_at,
        "category_results": results,
        "checker_basis": checker_basis,
        "status": "FRESH_STATUS_CHECK_RECORDED",
        **_zero_authority_payload(),
    }
    try:
        return _bounded_document(
            CreativeSampleRealAssetFreshStatusInstructionV1.model_validate(
                {
                    "instruction_id": _stable_contract_id(
                        "real_asset_fresh_status_instruction_v1", payload
                    ),
                    **payload,
                },
                strict=True,
            ),
            maximum_bytes=FRESH_STATUS_RECORD_MAX_BYTES,
            label="Fresh Status Instruction",
        )
    except ValidationError as exc:
        raise RealAssetFreshStatusEvidenceV30Error(
            "Fresh Status Instruction could not be built"
        ) from exc


def compile_fresh_status_decision_v1(
    *,
    request: CreativeSampleRealAssetFreshStatusRequestV1,
    instruction: CreativeSampleRealAssetFreshStatusInstructionV1,
) -> CreativeSampleRealAssetFreshStatusDecisionV1:
    """Compile the zero-authority Decision; no caller-supplied disposition is accepted."""

    request = _revalidate(
        request, CreativeSampleRealAssetFreshStatusRequestV1, field="Fresh Status Request"
    )
    instruction = _revalidate(
        instruction,
        CreativeSampleRealAssetFreshStatusInstructionV1,
        field="Fresh Status Instruction",
    )
    request_sha = _sha256(_canonical_document(request))
    if (
        instruction.request_id != request.request_id
        or instruction.request_sha256 != request_sha
        or instruction.subject_closure != request.subject_closure
        or instruction.preparer_identity_ref_sha256 != request.preparer_identity_ref_sha256
        or instruction.requested_at != request.requested_at
        or instruction.request_valid_until != request.request_valid_until
    ):
        raise RealAssetFreshStatusEvidenceV30Error(
            "Fresh Status Instruction does not bind the exact Request"
        )
    instruction_refs = tuple(
        sorted(
            (item for result in instruction.category_results for item in result.observation_refs),
            key=lambda item: (item.observation_id, item.observation_sha256),
        )
    )
    if instruction_refs != request.observation_refs:
        raise RealAssetFreshStatusEvidenceV30Error(
            "Instruction category results do not cover the exact Request observation set"
        )
    blocking = tuple(
        item.status_category
        for item in instruction.category_results
        if item.assessment_effect == "BLOCKING"
    )
    indeterminate = tuple(
        item.status_category
        for item in instruction.category_results
        if item.assessment_effect == "INDETERMINATE"
    )
    if blocking:
        disposition: FreshStatusDispositionV1 = "BLOCKING_STATUS_RECORDED"
    elif indeterminate:
        disposition = "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"
    else:
        disposition = "NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET"
    relied_until = tuple(
        item.result_valid_until
        for item in instruction.category_results
        if item.relied_on_observation_refs
    )
    status_valid_until = (
        min((request.request_valid_until, *relied_until))
        if relied_until
        else instruction.evaluated_at
    )
    instruction_sha = _sha256(_canonical_document(instruction))
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-fresh-status-decision-v1",
        "profile": FRESH_STATUS_EVIDENCE_V1_PROFILE,
        "policy_id": FRESH_STATUS_EVIDENCE_V1_POLICY_ID,
        "policy_version": FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
        "policy_document_sha256": FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256,
        "request_id": request.request_id,
        "request_sha256": request_sha,
        "instruction_id": instruction.instruction_id,
        "instruction_sha256": instruction_sha,
        "subject_closure": request.subject_closure,
        "evaluated_at": instruction.evaluated_at,
        "decision_at": instruction.evaluated_at,
        "status_valid_until": status_valid_until,
        "disposition": disposition,
        "category_results": instruction.category_results,
        "blocking_categories": blocking,
        "indeterminate_categories": indeterminate,
        "status": "FRESH_STATUS_EVIDENCE_DECISION_RECORDED",
        **_zero_authority_payload(),
    }
    try:
        return _bounded_document(
            CreativeSampleRealAssetFreshStatusDecisionV1.model_validate(
                {
                    "decision_id": _stable_contract_id(
                        "real_asset_fresh_status_decision_v1", payload
                    ),
                    **payload,
                },
                strict=True,
            ),
            maximum_bytes=FRESH_STATUS_RECORD_MAX_BYTES,
            label="Fresh Status Decision",
        )
    except ValidationError as exc:
        raise RealAssetFreshStatusEvidenceV30Error(
            "Fresh Status Decision could not be compiled"
        ) from exc


def build_fresh_status_evidence_record_v1(
    *,
    request: CreativeSampleRealAssetFreshStatusRequestV1,
    instruction: CreativeSampleRealAssetFreshStatusInstructionV1,
) -> CreativeSampleRealAssetFreshStatusEvidenceRecordV1:
    """Assemble one three-module Record candidate from exact Request and Instruction bytes."""

    decision = compile_fresh_status_decision_v1(request=request, instruction=instruction)
    request_sha = _sha256(_canonical_document(request))
    instruction_sha = _sha256(_canonical_document(instruction))
    decision_sha = _sha256(_canonical_document(decision))
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-fresh-status-evidence-record-v1",
        "profile": FRESH_STATUS_EVIDENCE_V1_PROFILE,
        "policy_id": FRESH_STATUS_EVIDENCE_V1_POLICY_ID,
        "policy_version": FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
        "policy_document_sha256": FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256,
        "subject_closure": request.subject_closure,
        "request": request,
        "request_sha256": request_sha,
        "instruction": instruction,
        "instruction_sha256": instruction_sha,
        "decision": decision,
        "decision_sha256": decision_sha,
        **_zero_authority_payload(),
    }
    try:
        return _bounded_document(
            CreativeSampleRealAssetFreshStatusEvidenceRecordV1.model_validate(
                {
                    "record_id": _stable_contract_id(
                        "real_asset_fresh_status_evidence_record_v1", payload
                    ),
                    **payload,
                },
                strict=True,
            ),
            maximum_bytes=FRESH_STATUS_RECORD_MAX_BYTES,
            label="Fresh Status EvidenceRecord",
        )
    except ValidationError as exc:
        raise RealAssetFreshStatusEvidenceV30Error(
            "Fresh Status EvidenceRecord could not be built"
        ) from exc


def verify_fresh_status_evidence_record_internal_v1(
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
) -> CreativeSampleRealAssetFreshStatusEvidenceRecordV1:
    """Verify only the self-contained three-module digest chain."""

    record = _revalidate(
        record,
        CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
        field="Fresh Status EvidenceRecord",
    )
    rebuilt = build_fresh_status_evidence_record_v1(
        request=record.request,
        instruction=record.instruction,
    )
    if rebuilt != record:
        raise RealAssetFreshStatusEvidenceV30Error(
            "Fresh Status EvidenceRecord drifted from its module chain"
        )
    return record


def verify_fresh_status_evidence_record_closure_v1(
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
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
) -> CreativeSampleRealAssetFreshStatusEvidenceRecordV1:
    """Replay the complete upstream closure and explicit finite Observation set."""

    use_scope_review_record = verify_use_scope_review_record_closure_v1(
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
        record=use_scope_review_record,
    )
    expected_closure = build_fresh_status_subject_closure_v1(
        pack=pack,
        rights_manifest=rights_manifest,
        use_plan=use_plan,
        use_scope_review_record=use_scope_review_record,
    )
    record = verify_fresh_status_evidence_record_internal_v1(record)
    if record.subject_closure != expected_closure:
        raise RealAssetFreshStatusEvidenceV30Error(
            "Fresh Status EvidenceRecord drifted from the complete upstream closure"
        )
    observations = _observations_match_request(record.request, observations)
    rebuilt_request = build_fresh_status_request_v1(
        subject_closure=expected_closure,
        preparer_identity_ref_sha256=record.request.preparer_identity_ref_sha256,
        requested_at=record.request.requested_at,
        request_basis=record.request.request_basis,
        observations=observations,
    )
    rebuilt_instruction = build_fresh_status_instruction_v1(
        request=rebuilt_request,
        observations=observations,
        checker_identity_ref_sha256=record.instruction.checker_identity_ref_sha256,
        evaluated_at=record.instruction.evaluated_at,
        checker_basis=record.instruction.checker_basis,
    )
    rebuilt_record = build_fresh_status_evidence_record_v1(
        request=rebuilt_request,
        instruction=rebuilt_instruction,
    )
    if rebuilt_record != record:
        raise RealAssetFreshStatusEvidenceV30Error(
            "Fresh Status EvidenceRecord drifted from its explicit complete closure"
        )
    return record


def extract_fresh_status_request_v1(
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
) -> tuple[CreativeSampleRealAssetFreshStatusRequestV1, bytes]:
    record = verify_fresh_status_evidence_record_internal_v1(record)
    return record.request, _canonical_document(record.request)


def extract_fresh_status_instruction_v1(
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
) -> tuple[CreativeSampleRealAssetFreshStatusInstructionV1, bytes]:
    record = verify_fresh_status_evidence_record_internal_v1(record)
    return record.instruction, _canonical_document(record.instruction)


def extract_fresh_status_decision_v1(
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
) -> tuple[CreativeSampleRealAssetFreshStatusDecisionV1, bytes]:
    record = verify_fresh_status_evidence_record_internal_v1(record)
    return record.decision, _canonical_document(record.decision)


def _reject_json_constant(value: str) -> None:
    raise RealAssetFreshStatusEvidenceV30Error(f"non-finite JSON number is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RealAssetFreshStatusEvidenceV30Error(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _json_depth(value: object) -> int:
    if isinstance(value, dict):
        return 1 + max((_json_depth(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((_json_depth(item) for item in value), default=0)
    return 0


def _parse_model[ModelT: BaseModel](
    raw: bytes,
    model: type[ModelT],
    *,
    label: str,
    maximum_bytes: int,
) -> ModelT:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > maximum_bytes
        or raw.startswith(b"\xef\xbb\xbf")
    ):
        raise RealAssetFreshStatusEvidenceV30Error(f"{label} JSON must be bounded BOM-free bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
        depth = _json_depth(value)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        RealAssetFreshStatusEvidenceV30Error,
        ValueError,
    ) as exc:
        raise RealAssetFreshStatusEvidenceV30Error(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RealAssetFreshStatusEvidenceV30Error(f"{label} JSON must contain one object")
    if depth > FRESH_STATUS_JSON_MAX_DEPTH:
        raise RealAssetFreshStatusEvidenceV30Error(f"{label} exceeds JSON depth 32")
    try:
        candidate = model.model_validate_json(raw, strict=False)
        parsed = model.model_validate(candidate.model_dump(mode="python"), strict=True)
    except ValidationError as exc:
        raise RealAssetFreshStatusEvidenceV30Error(f"{label} violates its strict contract") from exc
    if raw != _canonical_document(parsed):
        raise RealAssetFreshStatusEvidenceV30Error(f"{label} is not the exact canonical document")
    return parsed


def parse_fresh_status_source_observation_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetFreshStatusSourceObservationV1:
    return _parse_model(
        raw,
        CreativeSampleRealAssetFreshStatusSourceObservationV1,
        label="Fresh Status SourceObservation",
        maximum_bytes=FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES,
    )


def parse_fresh_status_request_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetFreshStatusRequestV1:
    return _parse_model(
        raw,
        CreativeSampleRealAssetFreshStatusRequestV1,
        label="Fresh Status Request",
        maximum_bytes=FRESH_STATUS_RECORD_MAX_BYTES,
    )


def parse_fresh_status_instruction_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetFreshStatusInstructionV1:
    return _parse_model(
        raw,
        CreativeSampleRealAssetFreshStatusInstructionV1,
        label="Fresh Status Instruction",
        maximum_bytes=FRESH_STATUS_RECORD_MAX_BYTES,
    )


def parse_fresh_status_decision_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetFreshStatusDecisionV1:
    return _parse_model(
        raw,
        CreativeSampleRealAssetFreshStatusDecisionV1,
        label="Fresh Status Decision",
        maximum_bytes=FRESH_STATUS_RECORD_MAX_BYTES,
    )


def parse_fresh_status_evidence_record_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetFreshStatusEvidenceRecordV1:
    return _parse_model(
        raw,
        CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
        label="Fresh Status EvidenceRecord",
        maximum_bytes=FRESH_STATUS_RECORD_MAX_BYTES,
    )


__all__ = (
    "FRESH_STATUS_EVIDENCE_V1_PROFILE",
    "FRESH_STATUS_EVIDENCE_V1_POLICY_ID",
    "FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION",
    "FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256",
    "FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE",
    "FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE_DOCUMENT_SHA256",
    "FRESH_STATUS_MAX_WINDOW_SECONDS",
    "FRESH_STATUS_MAX_OBSERVATIONS",
    "FRESH_STATUS_MAX_CHAIN_RECORDS",
    "FRESH_STATUS_MAX_RECONCILIATION_HEADS",
    "FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS",
    "FRESH_STATUS_AUTHORING_INPUT_MAX_BYTES",
    "FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES",
    "FRESH_STATUS_RECORD_MAX_BYTES",
    "FRESH_STATUS_JSON_MAX_DEPTH",
    "FRESH_STATUS_EVIDENCE_SCOPE",
    "FreshStatusCategoryV1",
    "FreshStatusClaimValueV1",
    "FreshStatusAssessmentEffectV1",
    "FreshStatusDispositionV1",
    "FreshStatusChainLinkKindV1",
    "FreshStatusBasisCodeV1",
    "FreshStatusSourceKindV1",
    "FreshStatusLimitationCodeV1",
    "FreshStatusSubjectClosureV1",
    "FreshStatusObservationRefV1",
    "FreshStatusChainHeadRefV1",
    "FreshStatusChainLinkV1",
    "FreshStatusCategoryResultV1",
    "CreativeSampleRealAssetFreshStatusSourceObservationV1",
    "CreativeSampleRealAssetFreshStatusRequestV1",
    "CreativeSampleRealAssetFreshStatusInstructionV1",
    "CreativeSampleRealAssetFreshStatusDecisionV1",
    "CreativeSampleRealAssetFreshStatusEvidenceRecordV1",
    "RealAssetFreshStatusEvidenceV30Error",
    "build_fresh_status_subject_closure_v1",
    "derive_fresh_status_observation_chain_sha256_v1",
    "build_fresh_status_source_observation_v1",
    "verify_fresh_status_source_observation_internal_v1",
    "verify_fresh_status_source_observation_link_v1",
    "build_fresh_status_request_v1",
    "build_fresh_status_instruction_v1",
    "compile_fresh_status_decision_v1",
    "build_fresh_status_evidence_record_v1",
    "verify_fresh_status_evidence_record_internal_v1",
    "verify_fresh_status_evidence_record_closure_v1",
    "extract_fresh_status_request_v1",
    "extract_fresh_status_instruction_v1",
    "extract_fresh_status_decision_v1",
    "parse_fresh_status_source_observation_v1_json",
    "parse_fresh_status_request_v1_json",
    "parse_fresh_status_instruction_v1_json",
    "parse_fresh_status_decision_v1_json",
    "parse_fresh_status_evidence_record_v1_json",
)
