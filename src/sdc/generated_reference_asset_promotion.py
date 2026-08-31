"""Offline, deterministic generated-reference eligible-asset promotion boundary.

The module is deliberately pure: it accepts exact typed values and retained bytes, performs
complete ADR-042/043/044 replay, and returns immutable evidence values.  It performs no I/O,
clock lookup, Provider/Runtime call, persistence, publication, or active-Bible mutation.
"""

# ruff: noqa: E501 -- the reviewed policy JSON contains frozen long string values.

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, ClassVar, Literal, NoReturn, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from sdc.contracts import CharacterAssetVersion, CharacterBible, SceneAssetVersion, SceneBible
from sdc.generated_reference_candidate import (
    CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
    CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
    CreativeSampleGeneratedReferenceCandidateV1,
    CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    GeneratedReferenceQualificationEvidenceInput,
)
from sdc.generated_reference_rights_current_status import (
    CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
    CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
    CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
    CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    CreativeSampleGeneratedReferenceRightsManifestV1,
    GeneratedReferenceAsOfAssessmentError,
    GeneratedReferenceChainCoverageError,
    GeneratedReferenceChainReplayError,
    GeneratedReferenceCurrentStatusExplicitChainInput,
    GeneratedReferenceCurrentStatusObservationInput,
    GeneratedReferenceCurrentStatusSubjectClosureV1,
    GeneratedReferenceJointReplayError,
    GeneratedReferenceReceiptError,
    GeneratedReferenceReviewedRightsScopeV1,
    GeneratedReferenceRightsCurrentStatusError,
    GeneratedReferenceRightsManifestEvidenceInput,
    GeneratedReferenceRightsScopeProposalV1,
    build_generated_reference_current_status_subject_closure,
    generated_reference_contract_document_bytes,
    generated_reference_current_status_chain_sha256,
    process_generated_reference_current_status_record_as_of_assessment,
    verify_generated_reference_current_status_evidence_record,
    verify_generated_reference_current_status_record_as_of_assessment_receipt,
    verify_generated_reference_rights_manifest,
)
from sdc.visual_reference_prompt_compiler import CreativeSampleReferenceVisualPromptArtifactV1

_FROZEN_PROMOTION_POLICY_ID = "sdc.generated-reference-asset-promotion-policy"
_FROZEN_PROMOTION_POLICY_VERSION = "1.0.0"
_FROZEN_PROMOTION_POLICY_DOCUMENT_SHA256 = (
    "94375b15ceb47d216611adf8d32eb5bac5a5f7544268ff07eca3f59919a4f9f1"
)
GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_ID = _FROZEN_PROMOTION_POLICY_ID
GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_VERSION = _FROZEN_PROMOTION_POLICY_VERSION
GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256 = (
    _FROZEN_PROMOTION_POLICY_DOCUMENT_SHA256
)

GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN = (
    b"sdc:generated-reference-asset-promotion-review-payload:v1\0"
)
GENERATED_REFERENCE_PRIMARY_ASSET_VERSION_PROJECTION_SHA256_DOMAIN = (
    b"sdc:generated-reference-primary-asset-version-projection:v1\0"
)
GENERATED_REFERENCE_PRIMARY_ASSET_BINDING_SHA256_DOMAIN = (
    b"sdc:generated-reference-primary-asset-binding:v1\0"
)
GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST_SHA256_DOMAIN = (
    b"sdc:generated-reference-asset-promotion-request:v1\0"
)
GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_SHA256_DOMAIN = (
    b"sdc:generated-reference-asset-promotion-decision:v1\0"
)
GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_SHA256_DOMAIN = (
    b"sdc:generated-reference-eligible-asset-sidecar:v1\0"
)

PROMOTION_GATE_ORDER = (
    "EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
    "EXACT_SUCCESSFUL_OUTCOME_AND_ARTIFACT",
    "POSITIVE_UNEXPIRED_QUALIFICATION",
    "VALID_GENERATED_RIGHTS_MANIFEST",
    "CURRENT_STATUS_AT_PROMOTION",
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT",
    "REVIEWED_RIGHTS_SCOPE_UNCHANGED",
    "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED",
    "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED",
    "PROMOTION_ROLE_SEPARATION",
)

PROMOTION_ISSUE_CODE_ORDER = (
    "STATUS_NOT_CURRENT_AT_PROMOTION",
    "PRIMARY_BINDING_NO_LONGER_ACTIVE",
    "PRIMARY_SIDECAR_ASSOCIATION_NOT_APPROVED",
    "COMPOSITE_UNSPLIT_ROLE_DEFERRAL_NOT_ACKNOWLEDGED",
)

_COMPILER_GATE_BASES = (
    "COMPILER_REVALIDATED_EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
    "COMPILER_REVALIDATED_EXACT_SUCCESSFUL_OUTCOME_AND_ARTIFACT",
    "COMPILER_REVALIDATED_POSITIVE_UNEXPIRED_QUALIFICATION",
    "COMPILER_REVALIDATED_VALID_GENERATED_RIGHTS_MANIFEST",
    "COMPILER_REPLAYED_GENERATED_CURRENT_STATUS_AT_PROMOTION",
    "COMPILER_REVALIDATED_FINAL_SUPPLIED_PRIMARY_ASSET_BINDING",
    "COMPILER_REVALIDATED_EXACT_MANIFEST_REVIEWED_RIGHTS_SCOPE",
    None,
    None,
    "COMPILER_REVALIDATED_PROMOTION_ROLE_SEPARATION",
)

_POLICY_JSON = r'''{
  "canonical_codec": "ADR_040_PERSISTENT_AND_COMPACT_CANONICAL_JSON",
  "decision_mapping": {
    "all_pass": "APPROVE_ELIGIBLE_ASSET_SIDECAR",
    "any_fail": "REJECT_ELIGIBLE_ASSET_SIDECAR",
    "otherwise": "INDETERMINATE_ELIGIBLE_ASSET_SIDECAR"
  },
  "final_record_prior_target_anchor": "OBSERVATION_ID_PLUS_OBSERVATION_SHA256_PLUS_CHAIN_SHA256_ORDINAL_EXCLUDED",
  "final_record_prior_target_coverage_rule": "EACH_PRIOR_TARGET_REMAINS_FINAL_TARGET_OR_IS_COMPLETE_ANCESTOR_OF_FINAL_SUCCESSOR_OR_RECONCILIATION_TARGET_WITH_EVERY_PRIOR_BRANCH_COVERED",
  "final_record_rule": "SAME_OR_NEW_COMPLETE_RECORD_SAME_STATUS_SUBJECT_MONOTONIC_OCCURRENCE_AND_BRANCH_CLOSURE_NO_DISCOVERY",
  "gate_order": [
    "EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
    "EXACT_SUCCESSFUL_OUTCOME_AND_ARTIFACT",
    "POSITIVE_UNEXPIRED_QUALIFICATION",
    "VALID_GENERATED_RIGHTS_MANIFEST",
    "CURRENT_STATUS_AT_PROMOTION",
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT",
    "REVIEWED_RIGHTS_SCOPE_UNCHANGED",
    "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED",
    "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED",
    "PROMOTION_ROLE_SEPARATION"
  ],
  "gate_source_result_mapping": {
    "CURRENT_STATUS_AT_PROMOTION": {
      "basis": "COMPILER_REPLAYED_GENERATED_CURRENT_STATUS_AT_PROMOTION",
      "result_mapping": {
        "CURRENT": "PASS",
        "EXPIRED": "FAIL",
        "HELD": "FAIL",
        "INDETERMINATE": "INDETERMINATE",
        "REVOKED": "FAIL"
      },
      "source": "COMPILER_DERIVED"
    },
    "EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA": {
      "basis": "COMPILER_REVALIDATED_EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "EXACT_SUCCESSFUL_OUTCOME_AND_ARTIFACT": {
      "basis": "COMPILER_REVALIDATED_EXACT_SUCCESSFUL_OUTCOME_AND_ARTIFACT",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED": {
      "allowed_results": ["PASS", "FAIL", "INDETERMINATE"],
      "basis": "BOUNDED_CHECKER_TEXT",
      "source": "CHECKER_ACTION"
    },
    "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED": {
      "allowed_results": ["PASS", "FAIL", "INDETERMINATE"],
      "basis": "BOUNDED_CHECKER_TEXT",
      "source": "CHECKER_ACTION"
    },
    "POSITIVE_UNEXPIRED_QUALIFICATION": {
      "basis": "COMPILER_REVALIDATED_POSITIVE_UNEXPIRED_QUALIFICATION",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "PROMOTION_ROLE_SEPARATION": {
      "basis": "COMPILER_REVALIDATED_PROMOTION_ROLE_SEPARATION",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "REVIEWED_RIGHTS_SCOPE_UNCHANGED": {
      "basis": "COMPILER_REVALIDATED_EXACT_MANIFEST_REVIEWED_RIGHTS_SCOPE",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT": {
      "basis": "COMPILER_REVALIDATED_FINAL_SUPPLIED_PRIMARY_ASSET_BINDING",
      "result_mapping": {"DIFFERENT_ACTIVE_BINDING": "FAIL", "EXACT_MATCH": "PASS"},
      "source": "COMPILER_DERIVED"
    },
    "VALID_GENERATED_RIGHTS_MANIFEST": {
      "basis": "COMPILER_REVALIDATED_VALID_GENERATED_RIGHTS_MANIFEST",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    }
  },
  "human_gate_order": [
    "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED",
    "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED"
  ],
  "issue_code_order": [
    "STATUS_NOT_CURRENT_AT_PROMOTION",
    "PRIMARY_BINDING_NO_LONGER_ACTIVE",
    "PRIMARY_SIDECAR_ASSOCIATION_NOT_APPROVED",
    "COMPOSITE_UNSPLIT_ROLE_DEFERRAL_NOT_ACKNOWLEDGED"
  ],
  "issue_mapping": {
    "CURRENT_STATUS_AT_PROMOTION": "STATUS_NOT_CURRENT_AT_PROMOTION",
    "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED": "COMPOSITE_UNSPLIT_ROLE_DEFERRAL_NOT_ACKNOWLEDGED",
    "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED": "PRIMARY_SIDECAR_ASSOCIATION_NOT_APPROVED",
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT": "PRIMARY_BINDING_NO_LONGER_ACTIVE"
  },
  "legacy_primary_asset_projection_codec": "RELEASED_V1_CREATIVE_STABLE_ID_COMPACT_JSON_NO_ADDITIONAL_NORMALIZATION",
  "policy_id": "sdc.generated-reference-asset-promotion-policy",
  "policy_version": "1.0.0",
  "primary_binding_rule": "REQUEST_BINDING_EQUALS_UPSTREAM_EXPECTED_FINAL_BINDING_SELF_CONSISTENT_SAME_SUBJECT_PURPOSE_GATE_COMPARED_FULL_LEGACY_DIGEST_NO_MUTATION",
  "promotion_request_max_age_seconds": 86400,
  "promotion_scope": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_ONLY",
  "representation": "TYPED_ELIGIBLE_ASSET_SIDECAR",
  "request_deadline_rule": "MIN_REQUESTED_AT_PLUS_86400_QUALIFICATION_MANIFEST_REQUEST_STATUS_EXCLUSIVE",
  "request_status_rule": "FRESH_JOINT_REPLAY_CURRENT_AT_EXACT_REQUESTED_AT",
  "resource_limits": {
    "formal_document_max_bytes": 262144,
    "formal_document_min_bytes": 1,
    "generic_container_max_items": 64,
    "human_basis_max_characters": 1000,
    "human_basis_min_characters": 1,
    "human_identity_max_bytes": 16384,
    "human_identity_min_bytes": 1,
    "nesting_depth_max": 16,
    "png_max_bytes": 67108864,
    "png_min_bytes": 1,
    "retained_record_max_bytes": 262144,
    "retained_record_min_bytes": 1
  },
  "reviewer_rule": {
    "promotion_checker_must_differ_from": [
      "PROMOTION_MAKER",
      "QUALIFICATION_QUALIFIER",
      "MANIFEST_CHECKER",
      "REQUEST_STATUS_CHECKER",
      "FINAL_STATUS_CHECKER"
    ],
    "promotion_maker_may_equal_any_upstream_role": true,
    "retained_identity_claim": "RECORD_SEPARATION_ONLY_NOT_IDENTITY_AUTHENTICATION"
  },
  "role_binding_rule": "DEFERRED_TO_SEPARATE_REVIEW",
  "scope_rule": "EXACT_MANIFEST_REVIEWED_SCOPE_NO_CHANGE",
  "sidecar_atomicity_rule": "POSITIVE_DECISION_AND_SIDECAR_SAME_PURE_CALL_NO_PARTIAL_OUTPUT",
  "status_rule": "FRESH_JOINT_REPLAY_AT_EXACT_PROMOTION_AT_CURRENT_REQUIRED_ONLY_FOR_POSITIVE",
  "supersession_rule": "NO_SUPERSESSION_OR_LATEST_SELECTION_IN_V1",
  "time_rule": "REQUEST_STATUS_RECEIPT_AS_OF_EQUALS_REQUESTED_AS_OF_EQUALS_REQUESTED_AT_EQUALS_MAKER_PREPARED_AT_AND_DECISION_AT_EQUALS_CHECKER_REVIEWED_AT_EQUALS_PROMOTION_AT_EQUALS_PROMOTION_STATUS_RECEIPT_AS_OF",
  "zero_authority_rule": "ALL_PROVIDER_RUNTIME_ASSET_USE_PUBLICATION_RETENTION_TRAINING_AUTHORITY_FALSE_OR_ZERO"
}'''

_PROMOTION_POLICY = cast(dict[str, object], json.loads(_POLICY_JSON))

_LOWER_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_PORTABLE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_UTC_SECONDS_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_MAX_FORMAL_DOCUMENT_BYTES = 262_144
_MAX_JSON_DEPTH = 16
_MAX_CONTAINER_ITEMS = 64

LowerSha256 = Annotated[str, Field(pattern=_LOWER_SHA256_PATTERN)]
PortableId = Annotated[str, Field(pattern=_PORTABLE_ID_PATTERN)]
HumanBasis = Annotated[str, Field(min_length=1, max_length=1000)]
AssetPurpose = Literal["CHARACTER_REFERENCE_ASSET", "SCENE_REFERENCE_ASSET"]
GateResult = Literal["PASS", "FAIL", "INDETERMINATE"]
PromotionStatus = Literal["CURRENT", "EXPIRED", "REVOKED", "HELD", "INDETERMINATE"]

_BIDI_CONTROL_CODEPOINTS = frozenset(
    {
        0x061C,
        0x200E,
        0x200F,
        0x202A,
        0x202B,
        0x202C,
        0x202D,
        0x202E,
        0x2066,
        0x2067,
        0x2068,
        0x2069,
    }
)

_ADR044_REPLAY_ERRORS = (
    GeneratedReferenceRightsCurrentStatusError,
    GeneratedReferenceChainReplayError,
    GeneratedReferenceChainCoverageError,
    GeneratedReferenceJointReplayError,
    GeneratedReferenceAsOfAssessmentError,
    GeneratedReferenceReceiptError,
)


GeneratedReferenceAssetPromotionErrorCodeV1 = Literal[
    "EXACT_INPUT_TYPE_REQUIRED",
    "DOCUMENT_RESOURCE_LIMIT_EXCEEDED",
    "CANONICAL_JSON_REQUIRED",
    "CONTRACT_FIELD_INVALID",
    "POLICY_IDENTITY_MISMATCH",
    "SEMANTIC_ID_OR_DIGEST_MISMATCH",
    "UPSTREAM_CLOSURE_MISMATCH",
    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
    "TIME_WINDOW_INVALID_OR_EXPIRED",
    "ROLE_SEPARATION_VIOLATION",
    "STATUS_REPLAY_FAILED",
    "PROMOTION_GATE_NOT_PASS",
    "AUTHORITY_SURFACE_NONZERO",
    "PROHIBITED_BOUNDARY_CONNECTION",
]

_GENERATED_REFERENCE_ASSET_PROMOTION_ERROR_PRIORITY: tuple[
    GeneratedReferenceAssetPromotionErrorCodeV1, ...
] = (
    "EXACT_INPUT_TYPE_REQUIRED",
    "DOCUMENT_RESOURCE_LIMIT_EXCEEDED",
    "CANONICAL_JSON_REQUIRED",
    "CONTRACT_FIELD_INVALID",
    "POLICY_IDENTITY_MISMATCH",
    "SEMANTIC_ID_OR_DIGEST_MISMATCH",
    "UPSTREAM_CLOSURE_MISMATCH",
    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
    "TIME_WINDOW_INVALID_OR_EXPIRED",
    "ROLE_SEPARATION_VIOLATION",
    "STATUS_REPLAY_FAILED",
    "PROMOTION_GATE_NOT_PASS",
    "AUTHORITY_SURFACE_NONZERO",
    "PROHIBITED_BOUNDARY_CONNECTION",
)


class GeneratedReferenceAssetPromotionError(ValueError):
    """Stable outer failure category for the ADR-045 pure boundary."""

    code: GeneratedReferenceAssetPromotionErrorCodeV1

    def __init__(
        self, code: GeneratedReferenceAssetPromotionErrorCodeV1, message: str
    ) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _fail(code: GeneratedReferenceAssetPromotionErrorCodeV1, message: str) -> NoReturn:
    raise GeneratedReferenceAssetPromotionError(code, message)


def _invalid(message: str) -> NoReturn:
    raise ValueError(message)


def _canonical_string(value: str, *, field: str) -> str:
    if type(value) is not str:
        _invalid(f"{field} must be an exact string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must contain Unicode scalar values") from exc
    if unicodedata.normalize("NFC", value) != value:
        _invalid(f"{field} must already use Unicode NFC")
    if value.startswith("\ufeff") or "\r" in value:
        _invalid(f"{field} contains a BOM or CR")
    for character in value:
        if (
            unicodedata.category(character) in {"Cc", "Cs"}
            or ord(character) in _BIDI_CONTROL_CODEPOINTS
        ):
            _invalid(f"{field} contains a prohibited control character")
    return value


def _human_text(value: str, *, field: str) -> str:
    value = _canonical_string(value, field=field)
    if value != value.strip() or not 1 <= len(value) <= 1000:
        _invalid(f"{field} must contain 1..1000 trimmed code points")
    return value


def _parse_utc(value: str, *, field: str) -> datetime:
    _canonical_string(value, field=field)
    if re.fullmatch(_UTC_SECONDS_PATTERN, value) is None:
        _invalid(f"{field} must be a UTC second timestamp")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"{field} is not a real UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        _invalid(f"{field} must use canonical UTC seconds")
    return parsed


def _utc_seconds(value: str, info: ValidationInfo) -> str:
    _parse_utc(value, field=str(info.field_name))
    return value


def _validate_json_tree(value: object, *, field: str = "value", depth: int = 1) -> None:
    if depth > _MAX_JSON_DEPTH:
        _invalid(f"{field} exceeds maximum nesting depth")
    if value is None or type(value) in {bool, int, str}:
        if type(value) is str:
            _canonical_string(value, field=field)
        return
    if type(value) is float:
        _invalid(f"{field} contains a float")
    if type(value) in {list, tuple}:
        items = cast(Sequence[object], value)
        if len(items) > _MAX_CONTAINER_ITEMS:
            _invalid(f"{field} has too many items")
        for index, item in enumerate(items):
            _validate_json_tree(item, field=f"{field}[{index}]", depth=depth + 1)
        return
    if type(value) is dict:
        mapping = cast(dict[str, object], value)
        if len(mapping) > 128 if depth == 1 else len(mapping) > _MAX_CONTAINER_ITEMS:
            _invalid(f"{field} has too many members")
        for key, item in mapping.items():
            _canonical_string(key, field=f"{field} key")
            _validate_json_tree(item, field=f"{field}.{key}", depth=depth + 1)
        return
    _invalid(f"{field} is outside the canonical JSON type set")


def _compact_json(value: object) -> bytes:
    _validate_json_tree(value)
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _persistent_json(value: object) -> bytes:
    _validate_json_tree(value)
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _legacy_compact_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _semantic_sha256(domain: bytes, projection: object) -> str:
    return hashlib.sha256(domain + _compact_json(projection)).hexdigest()


def _raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _invalid(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _arrays_to_tuples(value: object) -> object:
    if type(value) is list:
        return tuple(_arrays_to_tuples(item) for item in cast(list[object], value))
    if type(value) is dict:
        return {
            key: _arrays_to_tuples(item)
            for key, item in cast(dict[str, object], value).items()
        }
    return value


def _explicit_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return {
            name: _explicit_value(getattr(value, name))
            for name in type(value).model_fields
        }
    if type(value) is tuple:
        return [_explicit_value(item) for item in cast(tuple[object, ...], value)]
    if type(value) is list:
        return [_explicit_value(item) for item in cast(list[object], value)]
    if type(value) is dict:
        return {
            key: _explicit_value(item)
            for key, item in cast(dict[str, object], value).items()
        }
    return value


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )
    _document_max_bytes: ClassVar[int] = _MAX_FORMAL_DOCUMENT_BYTES

    @model_validator(mode="before")
    @classmethod
    def _reject_subclasses(cls, value: object) -> object:
        if isinstance(value, cls) and type(value) is not cls:
            _invalid(f"{cls.__name__} subclasses are not admitted")
        return value

    @classmethod
    def model_validate_json(cls, json_data: str | bytes | bytearray, **kwargs: object) -> Self:
        if kwargs:
            _invalid("model_validate_json options are not supported")
        if type(json_data) is str:
            raw = json_data.encode("utf-8")
        elif type(json_data) is bytes:
            raw = json_data
        elif type(json_data) is bytearray:
            raw = bytes(json_data)
        else:
            _invalid("formal JSON must be str, bytes, or bytearray")
        if not 1 <= len(raw) <= cls._document_max_bytes:
            _invalid("formal document exceeds byte limits")
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
            _invalid("formal JSON must be UTF-8 without BOM/CR and end in one LF")
        try:
            parsed = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_json_no_duplicates,
                parse_constant=lambda item: _invalid(f"non-finite number: {item}"),
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("formal JSON is invalid") from exc
        _validate_json_tree(parsed)
        value = cls.model_validate(_arrays_to_tuples(parsed))
        if _persistent_json(_explicit_value(value)) != raw:
            _invalid("formal JSON is not canonical")
        return value


class _ZeroAuthorityModel(_StrictFrozenModel):
    authority_scope: Literal["THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY"]
    current_gate: Literal["HUMAN_GATE"]
    provider_state: Literal["NOT_AUTHORIZED"]
    generation_authorized: Literal[False]
    execution_authorized: Literal[False]
    publication_authorized: Literal[False]
    remote_processing_allowed: Literal[False]
    retention_allowed: Literal[False]
    training_allowed: Literal[False]
    publication_allowed: Literal[False]
    automated_execution_allowed: Literal[False]
    authorized_attempts: Literal[0]
    authorized_cost_cny: Literal[0]
    posts_allowed: Literal[0]
    provider_requests: Literal[0]
    grants_rights: Literal[False]
    grants_qualification: Literal[False]
    grants_execution_authority: Literal[False]
    eligible_for_asset_promotion: Literal[False]
    replaces_rights_manifest: Literal[False]
    usage_restriction: Literal["MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"]


_ZERO_AUTHORITY_VALUES: dict[str, object] = {
    "authority_scope": "THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY",
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
    "grants_rights": False,
    "grants_qualification": False,
    "grants_execution_authority": False,
    "eligible_for_asset_promotion": False,
    "replaces_rights_manifest": False,
    "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION",
}


def _zero_authority_values() -> dict[str, object]:
    return dict(_ZERO_AUTHORITY_VALUES)


class GeneratedReferencePromotionPrimaryAssetBindingV1(_StrictFrozenModel):
    binding_profile: Literal["sdc.generated-reference-promotion-primary-asset-binding.v1"]
    primary_asset_binding_sha256: LowerSha256
    asset_purpose: AssetPurpose
    subject_id: PortableId
    asset_version_id: PortableId
    legacy_asset_version_projection_sha256: LowerSha256
    version: Annotated[int, Field(ge=1)]
    content_sha256: LowerSha256
    media_type: Literal["image/png"]
    approval_ref: PortableId
    provenance: Literal["IMPORTED_APPROVED_MEDIA"]
    bible_active_asset_version_id: PortableId

    @model_validator(mode="after")
    def _identity(self) -> Self:
        if self.asset_version_id != self.bible_active_asset_version_id:
            _invalid("primary binding must name the Bible-active AssetVersion")
        expected = _semantic_sha256(
            GENERATED_REFERENCE_PRIMARY_ASSET_BINDING_SHA256_DOMAIN,
            _primary_binding_projection_unchecked(self),
        )
        if self.primary_asset_binding_sha256 != expected:
            _invalid("primary AssetVersion binding digest mismatch")
        return self


class GeneratedReferencePromotionGateResultV1(_StrictFrozenModel):
    ordinal: Annotated[int, Field(ge=0, le=9)]
    gate: Literal[
        "EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
        "EXACT_SUCCESSFUL_OUTCOME_AND_ARTIFACT",
        "POSITIVE_UNEXPIRED_QUALIFICATION",
        "VALID_GENERATED_RIGHTS_MANIFEST",
        "CURRENT_STATUS_AT_PROMOTION",
        "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT",
        "REVIEWED_RIGHTS_SCOPE_UNCHANGED",
        "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED",
        "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED",
        "PROMOTION_ROLE_SEPARATION",
    ]
    result: GateResult
    basis: HumanBasis

    @field_validator("basis")
    @classmethod
    def _basis(cls, value: str) -> str:
        return _human_text(value, field="basis")

    @model_validator(mode="after")
    def _canonical_gate(self) -> Self:
        if self.gate != PROMOTION_GATE_ORDER[self.ordinal]:
            _invalid("Promotion gate ordinal/order mismatch")
        return self


class CreativeSampleGeneratedReferenceAssetPromotionRequestV1(_ZeroAuthorityModel):
    schema_version: Literal["1.0.0"]
    document_type: Literal["sdc.creative-sample-generated-reference-asset-promotion-request-v1"]
    request_scope: Literal["GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_ONLY"]
    request_id: PortableId
    request_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-asset-promotion-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "94375b15ceb47d216611adf8d32eb5bac5a5f7544268ff07eca3f59919a4f9f1"
    ]
    promotion_review_payload_sha256: LowerSha256
    reference_prompt_artifact_sha256: LowerSha256
    provider_attempt_outcome_id: PortableId
    provider_attempt_outcome_sha256: LowerSha256
    candidate_id: PortableId
    candidate_sha256: LowerSha256
    output_ordinal: Literal[0]
    media_type: Literal["image/png"]
    media_content_sha256: LowerSha256
    media_size_bytes: Annotated[int, Field(ge=1, le=67_108_864)]
    media_technical_record_sha256: LowerSha256
    qualification_request_id: PortableId
    qualification_request_sha256: LowerSha256
    qualification_decision_id: PortableId
    qualification_decision_sha256: LowerSha256
    qualification_decision_at: str
    qualification_valid_until: str
    manifest_id: PortableId
    manifest_sha256: LowerSha256
    manifest_at: str
    manifest_valid_until: str
    reviewed_rights_scope: GeneratedReferenceReviewedRightsScopeV1
    status_subject_closure_id: PortableId
    status_subject_closure_sha256: LowerSha256
    requested_status_record_id: PortableId
    requested_status_record_sha256: LowerSha256
    requested_status_receipt_id: PortableId
    requested_status_receipt_sha256: LowerSha256
    requested_explicit_chain_set_sha256: LowerSha256
    requested_coverage_set_sha256: LowerSha256
    requested_joint_replay_sha256: LowerSha256
    requested_as_of_assessment_sha256: LowerSha256
    requested_as_of: str
    requested_as_of_status: Literal["CURRENT"]
    requested_status_valid_until: str
    requested_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
    maker_identity_ref_sha256: LowerSha256
    maker_action_sha256: LowerSha256
    maker_prepared_at: str
    requested_at: str
    request_valid_until: str
    request_basis: HumanBasis
    requested_representation: Literal["TYPED_ELIGIBLE_ASSET_SIDECAR"]
    composite_media_unsplit: Literal[True]
    role_assignment_embedded: Literal[False]
    bible_mutation_requested: Literal[False]
    provider_input_requested: Literal[False]
    promotion_performed: Literal[False]
    sidecar_materialized: Literal[False]
    eligible_for_separate_role_binding_review: Literal[False]
    status: Literal["GENERATED_REFERENCE_ASSET_PROMOTION_REQUESTED"]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    _times = field_validator(
        "qualification_decision_at",
        "qualification_valid_until",
        "manifest_at",
        "manifest_valid_until",
        "requested_as_of",
        "requested_status_valid_until",
        "maker_prepared_at",
        "requested_at",
        "request_valid_until",
    )(_utc_seconds)

    @field_validator("request_basis")
    @classmethod
    def _basis(cls, value: str) -> str:
        return _human_text(value, field="request_basis")

    @model_validator(mode="after")
    def _closure(self) -> Self:
        _validate_request_contract(self)
        return self


class CreativeSampleGeneratedReferenceAssetPromotionDecisionV1(_ZeroAuthorityModel):
    schema_version: Literal["1.0.0"]
    document_type: Literal["sdc.creative-sample-generated-reference-asset-promotion-decision-v1"]
    decision_scope: Literal["GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_ONLY"]
    decision_id: PortableId
    decision_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-asset-promotion-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "94375b15ceb47d216611adf8d32eb5bac5a5f7544268ff07eca3f59919a4f9f1"
    ]
    promotion_review_payload_sha256: LowerSha256
    request_id: PortableId
    request_sha256: LowerSha256
    reference_prompt_artifact_sha256: LowerSha256
    provider_attempt_outcome_id: PortableId
    provider_attempt_outcome_sha256: LowerSha256
    candidate_id: PortableId
    candidate_sha256: LowerSha256
    media_content_sha256: LowerSha256
    qualification_request_id: PortableId
    qualification_request_sha256: LowerSha256
    qualification_decision_id: PortableId
    qualification_decision_sha256: LowerSha256
    qualification_valid_until: str
    manifest_id: PortableId
    manifest_sha256: LowerSha256
    manifest_valid_until: str
    reviewed_rights_scope: GeneratedReferenceReviewedRightsScopeV1
    requested_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
    promotion_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
    status_subject_closure_id: PortableId
    status_subject_closure_sha256: LowerSha256
    promotion_status_record_id: PortableId
    promotion_status_record_sha256: LowerSha256
    promotion_status_receipt_id: PortableId
    promotion_status_receipt_sha256: LowerSha256
    promotion_explicit_chain_set_sha256: LowerSha256
    promotion_coverage_set_sha256: LowerSha256
    promotion_joint_replay_sha256: LowerSha256
    promotion_as_of_assessment_sha256: LowerSha256
    promotion_as_of_status: PromotionStatus
    promotion_status_valid_until: str
    checker_identity_ref_sha256: LowerSha256
    checker_action_sha256: LowerSha256
    checker_reviewed_at: str
    decision_at: str
    promotion_at: str
    gate_results: Annotated[
        tuple[GeneratedReferencePromotionGateResultV1, ...], Field(min_length=10, max_length=10)
    ]
    promotion_issue_codes: Annotated[
        tuple[
            Literal[
                "STATUS_NOT_CURRENT_AT_PROMOTION",
                "PRIMARY_BINDING_NO_LONGER_ACTIVE",
                "PRIMARY_SIDECAR_ASSOCIATION_NOT_APPROVED",
                "COMPOSITE_UNSPLIT_ROLE_DEFERRAL_NOT_ACKNOWLEDGED",
            ],
            ...,
        ],
        Field(max_length=4),
    ]
    promotion_basis: HumanBasis
    decision: Literal[
        "APPROVE_ELIGIBLE_ASSET_SIDECAR",
        "REJECT_ELIGIBLE_ASSET_SIDECAR",
        "INDETERMINATE_ELIGIBLE_ASSET_SIDECAR",
    ]
    sidecar_materialization_allowed: bool
    promotion_review_performed: Literal[True]
    sidecar_id_embedded: Literal[False]
    role_assignment_embedded: Literal[False]
    provider_input_eligible: Literal[False]
    status: Literal["GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_RECORDED"]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    _times = field_validator(
        "qualification_valid_until",
        "manifest_valid_until",
        "promotion_status_valid_until",
        "checker_reviewed_at",
        "decision_at",
        "promotion_at",
    )(_utc_seconds)

    @field_validator("promotion_basis")
    @classmethod
    def _basis(cls, value: str) -> str:
        return _human_text(value, field="promotion_basis")

    @model_validator(mode="after")
    def _closure(self) -> Self:
        _validate_decision_contract(self)
        return self


class CreativeSampleGeneratedReferenceEligibleAssetSidecarV1(_ZeroAuthorityModel):
    schema_version: Literal["1.0.0"]
    document_type: Literal["sdc.creative-sample-generated-reference-eligible-asset-sidecar-v1"]
    sidecar_scope: Literal["GENERATED_REFERENCE_POST_PROMOTION_HISTORICAL_EVIDENCE_ONLY"]
    sidecar_id: PortableId
    sidecar_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-asset-promotion-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "94375b15ceb47d216611adf8d32eb5bac5a5f7544268ff07eca3f59919a4f9f1"
    ]
    request_id: PortableId
    request_sha256: LowerSha256
    decision_id: PortableId
    decision_sha256: LowerSha256
    reference_prompt_artifact_sha256: LowerSha256
    provider_attempt_outcome_id: PortableId
    provider_attempt_outcome_sha256: LowerSha256
    candidate_id: PortableId
    candidate_sha256: LowerSha256
    output_ordinal: Literal[0]
    media_type: Literal["image/png"]
    media_content_sha256: LowerSha256
    media_size_bytes: Annotated[int, Field(ge=1, le=67_108_864)]
    media_technical_record_sha256: LowerSha256
    qualification_request_id: PortableId
    qualification_request_sha256: LowerSha256
    qualification_decision_id: PortableId
    qualification_decision_sha256: LowerSha256
    qualification_valid_until: str
    manifest_id: PortableId
    manifest_sha256: LowerSha256
    manifest_valid_until: str
    reviewed_rights_scope: GeneratedReferenceReviewedRightsScopeV1
    primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
    status_subject_closure_id: PortableId
    status_subject_closure_sha256: LowerSha256
    promotion_status_record_id: PortableId
    promotion_status_record_sha256: LowerSha256
    promotion_status_receipt_id: PortableId
    promotion_status_receipt_sha256: LowerSha256
    promotion_explicit_chain_set_sha256: LowerSha256
    promotion_coverage_set_sha256: LowerSha256
    promotion_joint_replay_sha256: LowerSha256
    promotion_as_of_assessment_sha256: LowerSha256
    promotion_as_of_status: Literal["CURRENT"]
    promotion_at: str
    promotion_status_valid_until: str
    promotion_evidence_valid_until: str
    origin_claim: Literal["CALLER_ASSERTED_PROVIDER_GENERATED_REFERENCE_MEDIA"]
    origin_assurance: Literal[
        "QUALIFIED_RIGHTS_REVIEWED_AND_CURRENT_ONLY_AT_EXACT_PROMOTION_AT_NOT_PROVIDER_AUTHENTICATED"
    ]
    sidecar_state: Literal["GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_RECORDED"]
    promotion_performed: Literal[True]
    eligible_for_separate_role_binding_review: Literal[True]
    primary_asset_binding_replaced: Literal[False]
    bible_active_binding_changed: Literal[False]
    asset_version_v1_created: Literal[False]
    composite_media_unsplit: Literal[True]
    role_assignment_embedded: Literal[False]
    provider_input_eligible: Literal[False]
    present_currentness_asserted: Literal[False]
    perpetual_eligibility_asserted: Literal[False]
    supersedes_sidecar: Literal[False]
    status: Literal["GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_RECORDED"]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    _times = field_validator(
        "qualification_valid_until",
        "manifest_valid_until",
        "promotion_at",
        "promotion_status_valid_until",
        "promotion_evidence_valid_until",
    )(_utc_seconds)

    @model_validator(mode="after")
    def _closure(self) -> Self:
        _validate_sidecar_contract(self)
        return self


_SELF_FIELDS: dict[type[BaseModel], tuple[str, str]] = {
    CreativeSampleGeneratedReferenceAssetPromotionRequestV1: ("request_id", "request_sha256"),
    CreativeSampleGeneratedReferenceAssetPromotionDecisionV1: (
        "decision_id",
        "decision_sha256",
    ),
    CreativeSampleGeneratedReferenceEligibleAssetSidecarV1: ("sidecar_id", "sidecar_sha256"),
}

_IDENTITY_SPECS: dict[type[BaseModel], tuple[str, str, str, bytes]] = {
    CreativeSampleGeneratedReferenceAssetPromotionRequestV1: (
        "request_id",
        "request_sha256",
        "generated_reference_asset_promotion_request_v1_",
        GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST_SHA256_DOMAIN,
    ),
    CreativeSampleGeneratedReferenceAssetPromotionDecisionV1: (
        "decision_id",
        "decision_sha256",
        "generated_reference_asset_promotion_decision_v1_",
        GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_SHA256_DOMAIN,
    ),
    CreativeSampleGeneratedReferenceEligibleAssetSidecarV1: (
        "sidecar_id",
        "sidecar_sha256",
        "generated_reference_eligible_asset_sidecar_v1_",
        GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_SHA256_DOMAIN,
    ),
}


def generated_reference_asset_promotion_policy_projection() -> dict[str, object]:
    """Return an isolated copy of the frozen 5,394-byte policy projection."""

    _verify_policy_identity()
    return cast(dict[str, object], json.loads(json.dumps(_PROMOTION_POLICY)))


def _rights_scope_projection(value: GeneratedReferenceReviewedRightsScopeV1) -> dict[str, object]:
    if type(value) is not GeneratedReferenceReviewedRightsScopeV1:
        _invalid("reviewed_rights_scope must have its exact ADR-044 inline type")
    return {
        "territory_scope": list(value.territory_scope),
        "allowed_use_scope": list(value.allowed_use_scope),
        "reviewed_scope_valid_until": value.reviewed_scope_valid_until,
        "output_copyright_and_commercial_scope_basis": (
            value.output_copyright_and_commercial_scope_basis
        ),
        "likeness_privacy_and_sensitive_data_basis": (
            value.likeness_privacy_and_sensitive_data_basis
        ),
        "brand_and_protected_content_basis": value.brand_and_protected_content_basis,
        "retention_and_deletion_basis": value.retention_and_deletion_basis,
        "training_use_prohibition_basis": value.training_use_prohibition_basis,
        "review_basis": value.review_basis,
    }


def _zero_authority_projection(value: _ZeroAuthorityModel) -> dict[str, object]:
    return {name: getattr(value, name) for name in _ZERO_AUTHORITY_VALUES}


def generated_reference_primary_asset_version_projection(
    value: CharacterAssetVersion | SceneAssetVersion,
) -> dict[str, object]:
    """Return the exact released V1 identity projection, including visual description."""

    if type(value) is CharacterAssetVersion:
        validated = _revalidate_external_model(value, CharacterAssetVersion, field="asset_version")
        character = cast(CharacterAssetVersion, validated)
        return {
            "approval_ref": character.approval_ref,
            "character_id": character.character_id,
            "content_sha256": character.content_sha256,
            "media_type": character.media_type,
            "provenance": character.provenance,
            "version": character.version,
            "visual_description": character.visual_description,
        }
    if type(value) is SceneAssetVersion:
        validated = _revalidate_external_model(value, SceneAssetVersion, field="asset_version")
        scene = cast(SceneAssetVersion, validated)
        return {
            "approval_ref": scene.approval_ref,
            "content_sha256": scene.content_sha256,
            "media_type": scene.media_type,
            "provenance": scene.provenance,
            "scene_id": scene.scene_id,
            "version": scene.version,
            "visual_description": scene.visual_description,
        }
    _fail("EXACT_INPUT_TYPE_REQUIRED", "asset_version must be one exact released V1 type")


def generated_reference_primary_asset_version_projection_sha256(
    value: CharacterAssetVersion | SceneAssetVersion,
) -> str:
    projection = generated_reference_primary_asset_version_projection(value)
    return hashlib.sha256(
        GENERATED_REFERENCE_PRIMARY_ASSET_VERSION_PROJECTION_SHA256_DOMAIN
        + _legacy_compact_json(projection)
    ).hexdigest()


def _primary_binding_projection_unchecked(
    value: GeneratedReferencePromotionPrimaryAssetBindingV1,
) -> dict[str, object]:
    return {
        "binding_profile": value.binding_profile,
        "asset_purpose": value.asset_purpose,
        "subject_id": value.subject_id,
        "asset_version_id": value.asset_version_id,
        "legacy_asset_version_projection_sha256": value.legacy_asset_version_projection_sha256,
        "version": value.version,
        "content_sha256": value.content_sha256,
        "media_type": value.media_type,
        "approval_ref": value.approval_ref,
        "provenance": value.provenance,
        "bible_active_asset_version_id": value.bible_active_asset_version_id,
    }


def generated_reference_promotion_primary_asset_binding_projection(
    value: GeneratedReferencePromotionPrimaryAssetBindingV1,
) -> dict[str, object]:
    validated = cast(
        GeneratedReferencePromotionPrimaryAssetBindingV1,
        _exact_model(
            value,
            GeneratedReferencePromotionPrimaryAssetBindingV1,
            field="primary_asset_binding",
        ),
    )
    return _primary_binding_projection_unchecked(validated)


def generated_reference_promotion_primary_asset_binding_sha256(
    value: GeneratedReferencePromotionPrimaryAssetBindingV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_PRIMARY_ASSET_BINDING_SHA256_DOMAIN,
        generated_reference_promotion_primary_asset_binding_projection(value),
    )


def _gate_projection(value: GeneratedReferencePromotionGateResultV1) -> dict[str, object]:
    return {
        "ordinal": value.ordinal,
        "gate": value.gate,
        "result": value.result,
        "basis": value.basis,
    }


def _request_projection_unchecked(
    value: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
) -> dict[str, object]:
    projection: dict[str, object] = {
        "schema_version": value.schema_version,
        "document_type": value.document_type,
        "request_scope": value.request_scope,
        "policy_id": value.policy_id,
        "policy_version": value.policy_version,
        "policy_document_sha256": value.policy_document_sha256,
        "promotion_review_payload_sha256": value.promotion_review_payload_sha256,
        "reference_prompt_artifact_sha256": value.reference_prompt_artifact_sha256,
        "provider_attempt_outcome_id": value.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": value.provider_attempt_outcome_sha256,
        "candidate_id": value.candidate_id,
        "candidate_sha256": value.candidate_sha256,
        "output_ordinal": value.output_ordinal,
        "media_type": value.media_type,
        "media_content_sha256": value.media_content_sha256,
        "media_size_bytes": value.media_size_bytes,
        "media_technical_record_sha256": value.media_technical_record_sha256,
        "qualification_request_id": value.qualification_request_id,
        "qualification_request_sha256": value.qualification_request_sha256,
        "qualification_decision_id": value.qualification_decision_id,
        "qualification_decision_sha256": value.qualification_decision_sha256,
        "qualification_decision_at": value.qualification_decision_at,
        "qualification_valid_until": value.qualification_valid_until,
        "manifest_id": value.manifest_id,
        "manifest_sha256": value.manifest_sha256,
        "manifest_at": value.manifest_at,
        "manifest_valid_until": value.manifest_valid_until,
        "reviewed_rights_scope": _rights_scope_projection(value.reviewed_rights_scope),
        "status_subject_closure_id": value.status_subject_closure_id,
        "status_subject_closure_sha256": value.status_subject_closure_sha256,
        "requested_status_record_id": value.requested_status_record_id,
        "requested_status_record_sha256": value.requested_status_record_sha256,
        "requested_status_receipt_id": value.requested_status_receipt_id,
        "requested_status_receipt_sha256": value.requested_status_receipt_sha256,
        "requested_explicit_chain_set_sha256": value.requested_explicit_chain_set_sha256,
        "requested_coverage_set_sha256": value.requested_coverage_set_sha256,
        "requested_joint_replay_sha256": value.requested_joint_replay_sha256,
        "requested_as_of_assessment_sha256": value.requested_as_of_assessment_sha256,
        "requested_as_of": value.requested_as_of,
        "requested_as_of_status": value.requested_as_of_status,
        "requested_status_valid_until": value.requested_status_valid_until,
        "requested_primary_asset_binding": _primary_binding_projection_with_digest(
            value.requested_primary_asset_binding
        ),
        "maker_identity_ref_sha256": value.maker_identity_ref_sha256,
        "maker_action_sha256": value.maker_action_sha256,
        "maker_prepared_at": value.maker_prepared_at,
        "requested_at": value.requested_at,
        "request_valid_until": value.request_valid_until,
        "request_basis": value.request_basis,
        "requested_representation": value.requested_representation,
        "composite_media_unsplit": value.composite_media_unsplit,
        "role_assignment_embedded": value.role_assignment_embedded,
        "bible_mutation_requested": value.bible_mutation_requested,
        "provider_input_requested": value.provider_input_requested,
        "promotion_performed": value.promotion_performed,
        "sidecar_materialized": value.sidecar_materialized,
        "eligible_for_separate_role_binding_review": (
            value.eligible_for_separate_role_binding_review
        ),
        "status": value.status,
        "evidence_scope": value.evidence_scope,
    }
    projection.update(_zero_authority_projection(value))
    return projection


def _decision_projection_unchecked(
    value: CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
) -> dict[str, object]:
    projection: dict[str, object] = {
        "schema_version": value.schema_version,
        "document_type": value.document_type,
        "decision_scope": value.decision_scope,
        "policy_id": value.policy_id,
        "policy_version": value.policy_version,
        "policy_document_sha256": value.policy_document_sha256,
        "promotion_review_payload_sha256": value.promotion_review_payload_sha256,
        "request_id": value.request_id,
        "request_sha256": value.request_sha256,
        "reference_prompt_artifact_sha256": value.reference_prompt_artifact_sha256,
        "provider_attempt_outcome_id": value.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": value.provider_attempt_outcome_sha256,
        "candidate_id": value.candidate_id,
        "candidate_sha256": value.candidate_sha256,
        "media_content_sha256": value.media_content_sha256,
        "qualification_request_id": value.qualification_request_id,
        "qualification_request_sha256": value.qualification_request_sha256,
        "qualification_decision_id": value.qualification_decision_id,
        "qualification_decision_sha256": value.qualification_decision_sha256,
        "qualification_valid_until": value.qualification_valid_until,
        "manifest_id": value.manifest_id,
        "manifest_sha256": value.manifest_sha256,
        "manifest_valid_until": value.manifest_valid_until,
        "reviewed_rights_scope": _rights_scope_projection(value.reviewed_rights_scope),
        "requested_primary_asset_binding": _primary_binding_projection_with_digest(
            value.requested_primary_asset_binding
        ),
        "promotion_primary_asset_binding": _primary_binding_projection_with_digest(
            value.promotion_primary_asset_binding
        ),
        "status_subject_closure_id": value.status_subject_closure_id,
        "status_subject_closure_sha256": value.status_subject_closure_sha256,
        "promotion_status_record_id": value.promotion_status_record_id,
        "promotion_status_record_sha256": value.promotion_status_record_sha256,
        "promotion_status_receipt_id": value.promotion_status_receipt_id,
        "promotion_status_receipt_sha256": value.promotion_status_receipt_sha256,
        "promotion_explicit_chain_set_sha256": value.promotion_explicit_chain_set_sha256,
        "promotion_coverage_set_sha256": value.promotion_coverage_set_sha256,
        "promotion_joint_replay_sha256": value.promotion_joint_replay_sha256,
        "promotion_as_of_assessment_sha256": value.promotion_as_of_assessment_sha256,
        "promotion_as_of_status": value.promotion_as_of_status,
        "promotion_status_valid_until": value.promotion_status_valid_until,
        "checker_identity_ref_sha256": value.checker_identity_ref_sha256,
        "checker_action_sha256": value.checker_action_sha256,
        "checker_reviewed_at": value.checker_reviewed_at,
        "decision_at": value.decision_at,
        "promotion_at": value.promotion_at,
        "gate_results": [_gate_projection(item) for item in value.gate_results],
        "promotion_issue_codes": list(value.promotion_issue_codes),
        "promotion_basis": value.promotion_basis,
        "decision": value.decision,
        "sidecar_materialization_allowed": value.sidecar_materialization_allowed,
        "promotion_review_performed": value.promotion_review_performed,
        "sidecar_id_embedded": value.sidecar_id_embedded,
        "role_assignment_embedded": value.role_assignment_embedded,
        "provider_input_eligible": value.provider_input_eligible,
        "status": value.status,
        "evidence_scope": value.evidence_scope,
    }
    projection.update(_zero_authority_projection(value))
    return projection


def _sidecar_projection_unchecked(
    value: CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
) -> dict[str, object]:
    projection: dict[str, object] = {
        "schema_version": value.schema_version,
        "document_type": value.document_type,
        "sidecar_scope": value.sidecar_scope,
        "policy_id": value.policy_id,
        "policy_version": value.policy_version,
        "policy_document_sha256": value.policy_document_sha256,
        "request_id": value.request_id,
        "request_sha256": value.request_sha256,
        "decision_id": value.decision_id,
        "decision_sha256": value.decision_sha256,
        "reference_prompt_artifact_sha256": value.reference_prompt_artifact_sha256,
        "provider_attempt_outcome_id": value.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": value.provider_attempt_outcome_sha256,
        "candidate_id": value.candidate_id,
        "candidate_sha256": value.candidate_sha256,
        "output_ordinal": value.output_ordinal,
        "media_type": value.media_type,
        "media_content_sha256": value.media_content_sha256,
        "media_size_bytes": value.media_size_bytes,
        "media_technical_record_sha256": value.media_technical_record_sha256,
        "qualification_request_id": value.qualification_request_id,
        "qualification_request_sha256": value.qualification_request_sha256,
        "qualification_decision_id": value.qualification_decision_id,
        "qualification_decision_sha256": value.qualification_decision_sha256,
        "qualification_valid_until": value.qualification_valid_until,
        "manifest_id": value.manifest_id,
        "manifest_sha256": value.manifest_sha256,
        "manifest_valid_until": value.manifest_valid_until,
        "reviewed_rights_scope": _rights_scope_projection(value.reviewed_rights_scope),
        "primary_asset_binding": _primary_binding_projection_with_digest(
            value.primary_asset_binding
        ),
        "status_subject_closure_id": value.status_subject_closure_id,
        "status_subject_closure_sha256": value.status_subject_closure_sha256,
        "promotion_status_record_id": value.promotion_status_record_id,
        "promotion_status_record_sha256": value.promotion_status_record_sha256,
        "promotion_status_receipt_id": value.promotion_status_receipt_id,
        "promotion_status_receipt_sha256": value.promotion_status_receipt_sha256,
        "promotion_explicit_chain_set_sha256": value.promotion_explicit_chain_set_sha256,
        "promotion_coverage_set_sha256": value.promotion_coverage_set_sha256,
        "promotion_joint_replay_sha256": value.promotion_joint_replay_sha256,
        "promotion_as_of_assessment_sha256": value.promotion_as_of_assessment_sha256,
        "promotion_as_of_status": value.promotion_as_of_status,
        "promotion_at": value.promotion_at,
        "promotion_status_valid_until": value.promotion_status_valid_until,
        "promotion_evidence_valid_until": value.promotion_evidence_valid_until,
        "origin_claim": value.origin_claim,
        "origin_assurance": value.origin_assurance,
        "sidecar_state": value.sidecar_state,
        "promotion_performed": value.promotion_performed,
        "eligible_for_separate_role_binding_review": (
            value.eligible_for_separate_role_binding_review
        ),
        "primary_asset_binding_replaced": value.primary_asset_binding_replaced,
        "bible_active_binding_changed": value.bible_active_binding_changed,
        "asset_version_v1_created": value.asset_version_v1_created,
        "composite_media_unsplit": value.composite_media_unsplit,
        "role_assignment_embedded": value.role_assignment_embedded,
        "provider_input_eligible": value.provider_input_eligible,
        "present_currentness_asserted": value.present_currentness_asserted,
        "perpetual_eligibility_asserted": value.perpetual_eligibility_asserted,
        "supersedes_sidecar": value.supersedes_sidecar,
        "status": value.status,
        "evidence_scope": value.evidence_scope,
    }
    projection.update(_zero_authority_projection(value))
    return projection


def _primary_binding_projection_with_digest(
    value: GeneratedReferencePromotionPrimaryAssetBindingV1,
) -> dict[str, object]:
    return {
        "binding_profile": value.binding_profile,
        "primary_asset_binding_sha256": value.primary_asset_binding_sha256,
        **_primary_binding_projection_unchecked(value),
    }


def _public_projection(value: BaseModel, expected: type[BaseModel]) -> dict[str, object]:
    validated = _exact_model(value, expected, field=expected.__name__)
    if expected is CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        return _request_projection_unchecked(
            cast(CreativeSampleGeneratedReferenceAssetPromotionRequestV1, validated)
        )
    if expected is CreativeSampleGeneratedReferenceAssetPromotionDecisionV1:
        return _decision_projection_unchecked(
            cast(CreativeSampleGeneratedReferenceAssetPromotionDecisionV1, validated)
        )
    if expected is CreativeSampleGeneratedReferenceEligibleAssetSidecarV1:
        return _sidecar_projection_unchecked(
            cast(CreativeSampleGeneratedReferenceEligibleAssetSidecarV1, validated)
        )
    _invalid("unknown Promotion Contract type")


def creative_sample_generated_reference_asset_promotion_request_projection(
    value: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
) -> dict[str, object]:
    return _public_projection(value, CreativeSampleGeneratedReferenceAssetPromotionRequestV1)


def creative_sample_generated_reference_asset_promotion_request_sha256(
    value: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST_SHA256_DOMAIN,
        creative_sample_generated_reference_asset_promotion_request_projection(value),
    )


def creative_sample_generated_reference_asset_promotion_decision_projection(
    value: CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
) -> dict[str, object]:
    return _public_projection(value, CreativeSampleGeneratedReferenceAssetPromotionDecisionV1)


def creative_sample_generated_reference_asset_promotion_decision_sha256(
    value: CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_SHA256_DOMAIN,
        creative_sample_generated_reference_asset_promotion_decision_projection(value),
    )


def creative_sample_generated_reference_eligible_asset_sidecar_projection(
    value: CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
) -> dict[str, object]:
    return _public_projection(value, CreativeSampleGeneratedReferenceEligibleAssetSidecarV1)


def creative_sample_generated_reference_eligible_asset_sidecar_sha256(
    value: CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_SHA256_DOMAIN,
        creative_sample_generated_reference_eligible_asset_sidecar_projection(value),
    )


def generated_reference_asset_promotion_contract_document_bytes(value: BaseModel) -> bytes:
    if type(value) not in _SELF_FIELDS:
        _fail(
            "EXACT_INPUT_TYPE_REQUIRED",
            "only an exact ADR-045 top-level Contract is admitted",
        )
    validated = _exact_model(value, type(value), field="Contract")
    encoded = _persistent_json(_explicit_value(validated))
    if not 1 <= len(encoded) <= _MAX_FORMAL_DOCUMENT_BYTES:
        _fail("DOCUMENT_RESOURCE_LIMIT_EXCEEDED", "formal document exceeds byte limits")
    return encoded


def _exact_model(value: object, expected: type[BaseModel], *, field: str) -> BaseModel:
    if type(value) is not expected:
        _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} must have exact type {expected.__name__}")
    if expected in _SELF_FIELDS:
        return _preflight_formal_contract(value, expected, field=field)
    try:
        explicit = _explicit_value(value)
        return expected.model_validate(_arrays_to_tuples(explicit))
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", f"{field} fails exact revalidation"
        ) from exc


def _revalidate_external_model(
    value: object, expected: type[BaseModel], *, field: str
) -> BaseModel:
    if type(value) is not expected:
        _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} must have exact type {expected.__name__}")
    try:
        source = value
        rebuilt = expected.model_validate(source.model_dump(mode="python"))
    except (AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", f"{field} fails released Contract revalidation"
        ) from exc
    if rebuilt != value:
        _fail("CONTRACT_FIELD_INVALID", f"{field} changes under released Contract revalidation")
    return rebuilt


def _validate_identity(value: BaseModel, expected: type[BaseModel]) -> None:
    id_field, sha_field, stem, domain = _IDENTITY_SPECS[expected]
    if expected is CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        projection = _request_projection_unchecked(
            cast(CreativeSampleGeneratedReferenceAssetPromotionRequestV1, value)
        )
    elif expected is CreativeSampleGeneratedReferenceAssetPromotionDecisionV1:
        projection = _decision_projection_unchecked(
            cast(CreativeSampleGeneratedReferenceAssetPromotionDecisionV1, value)
        )
    else:
        projection = _sidecar_projection_unchecked(
            cast(CreativeSampleGeneratedReferenceEligibleAssetSidecarV1, value)
        )
    digest = _semantic_sha256(domain, projection)
    if getattr(value, sha_field) != digest or getattr(value, id_field) != f"{stem}{digest[:20]}":
        _invalid("semantic ID or digest mismatch")


def _validate_request_contract(
    value: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
) -> None:
    if not (
        value.requested_as_of == value.requested_at == value.maker_prepared_at
    ):
        _invalid("Request times must close at exact requested_at")
    requested_at = _parse_utc(value.requested_at, field="requested_at")
    qualification_until = _parse_utc(
        value.qualification_valid_until, field="qualification_valid_until"
    )
    manifest_until = _parse_utc(value.manifest_valid_until, field="manifest_valid_until")
    status_until = _parse_utc(
        value.requested_status_valid_until, field="requested_status_valid_until"
    )
    expected_until = min(
        requested_at + timedelta(seconds=86_400),
        qualification_until,
        manifest_until,
        status_until,
    )
    if expected_until <= requested_at or value.request_valid_until != _format_utc(expected_until):
        _invalid("Request deadline is not the exact frozen minimum")
    if value.promotion_review_payload_sha256 != _semantic_sha256(
        GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
        _review_payload_projection_from_request(value),
    ):
        _invalid("Promotion review payload digest mismatch")
    _validate_identity(value, CreativeSampleGeneratedReferenceAssetPromotionRequestV1)
    if len(_persistent_json(_explicit_value(value))) > _MAX_FORMAL_DOCUMENT_BYTES:
        _invalid("Request exceeds formal document byte limit")


def _expected_issues(
    gates: tuple[GeneratedReferencePromotionGateResultV1, ...],
) -> tuple[str, ...]:
    mapping = {
        4: "STATUS_NOT_CURRENT_AT_PROMOTION",
        5: "PRIMARY_BINDING_NO_LONGER_ACTIVE",
        7: "PRIMARY_SIDECAR_ASSOCIATION_NOT_APPROVED",
        8: "COMPOSITE_UNSPLIT_ROLE_DEFERRAL_NOT_ACKNOWLEDGED",
    }
    return tuple(mapping[index] for index in (4, 5, 7, 8) if gates[index].result != "PASS")


def _decision_from_gates(
    gates: tuple[GeneratedReferencePromotionGateResultV1, ...],
) -> str:
    if any(item.result == "FAIL" for item in gates):
        return "REJECT_ELIGIBLE_ASSET_SIDECAR"
    if any(item.result == "INDETERMINATE" for item in gates):
        return "INDETERMINATE_ELIGIBLE_ASSET_SIDECAR"
    return "APPROVE_ELIGIBLE_ASSET_SIDECAR"


def _validate_decision_contract(
    value: CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
) -> None:
    if not value.checker_reviewed_at == value.decision_at == value.promotion_at:
        _invalid("Decision times must equal exact promotion_at")
    if tuple(item.gate for item in value.gate_results) != PROMOTION_GATE_ORDER:
        _invalid("Decision gate tuple is not canonical")
    for index in (0, 1, 2, 3, 6, 9):
        if value.gate_results[index].result != "PASS":
            _invalid("compiler pass-only Promotion gate is not PASS")
    for index, basis in enumerate(_COMPILER_GATE_BASES):
        if basis is not None and value.gate_results[index].basis != basis:
            _invalid("compiler-derived Promotion gate basis mismatch")
    expected_status_result = {
        "CURRENT": "PASS",
        "EXPIRED": "FAIL",
        "REVOKED": "FAIL",
        "HELD": "FAIL",
        "INDETERMINATE": "INDETERMINATE",
    }[value.promotion_as_of_status]
    if value.gate_results[4].result != expected_status_result:
        _invalid("promotion status gate mapping mismatch")
    same_binding = value.requested_primary_asset_binding == value.promotion_primary_asset_binding
    if value.gate_results[5].result != ("PASS" if same_binding else "FAIL"):
        _invalid("primary binding gate mapping mismatch")
    if (
        value.requested_primary_asset_binding.subject_id
        != value.promotion_primary_asset_binding.subject_id
        or value.requested_primary_asset_binding.asset_purpose
        != value.promotion_primary_asset_binding.asset_purpose
    ):
        _invalid("Decision primary bindings cross subject or purpose")
    if value.promotion_issue_codes != _expected_issues(value.gate_results):
        _invalid("Promotion issue tuple is not the exact policy subsequence")
    expected_decision = _decision_from_gates(value.gate_results)
    if value.decision != expected_decision:
        _invalid("Promotion Decision does not match its gate tuple")
    if value.sidecar_materialization_allowed is not (
        expected_decision == "APPROVE_ELIGIBLE_ASSET_SIDECAR"
    ):
        _invalid("sidecar materialization Boolean does not match Decision")
    _validate_identity(value, CreativeSampleGeneratedReferenceAssetPromotionDecisionV1)
    if len(_persistent_json(_explicit_value(value))) > _MAX_FORMAL_DOCUMENT_BYTES:
        _invalid("Decision exceeds formal document byte limit")


def _validate_sidecar_contract(
    value: CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
) -> None:
    expected_until = min(
        _parse_utc(value.qualification_valid_until, field="qualification_valid_until"),
        _parse_utc(value.manifest_valid_until, field="manifest_valid_until"),
        _parse_utc(value.promotion_status_valid_until, field="promotion_status_valid_until"),
    )
    promotion_at = _parse_utc(value.promotion_at, field="promotion_at")
    if expected_until <= promotion_at or value.promotion_evidence_valid_until != _format_utc(
        expected_until
    ):
        _invalid("Sidecar historical evidence horizon mismatch")
    _validate_identity(value, CreativeSampleGeneratedReferenceEligibleAssetSidecarV1)
    if len(_persistent_json(_explicit_value(value))) > _MAX_FORMAL_DOCUMENT_BYTES:
        _invalid("Sidecar exceeds formal document byte limit")


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_identity(
    model_type: type[BaseModel], values: Mapping[str, object]
) -> BaseModel:
    id_field, sha_field, stem, domain = _IDENTITY_SPECS[model_type]
    payload = dict(values)
    try:
        if model_type is CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
            projection = _request_projection_from_values(payload)
        elif model_type is CreativeSampleGeneratedReferenceAssetPromotionDecisionV1:
            projection = _decision_projection_from_values(payload)
        elif model_type is CreativeSampleGeneratedReferenceEligibleAssetSidecarV1:
            projection = _sidecar_projection_from_values(payload)
        else:
            _fail("EXACT_INPUT_TYPE_REQUIRED", "unknown formal Contract type")
    except KeyError as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", "closed Contract inputs are missing a frozen field"
        ) from exc
    if set(values) != set(projection):
        _fail("CONTRACT_FIELD_INVALID", "closed Contract inputs have extra frozen fields")
    digest = _semantic_sha256(domain, projection)
    payload[id_field] = f"{stem}{digest[:20]}"
    payload[sha_field] = digest
    try:
        return model_type.model_validate(payload)
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", f"{model_type.__name__} construction failed"
        ) from exc


def _request_projection_from_values(values: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": _explicit_value(values["schema_version"]),
        "document_type": _explicit_value(values["document_type"]),
        "request_scope": _explicit_value(values["request_scope"]),
        "policy_id": _explicit_value(values["policy_id"]),
        "policy_version": _explicit_value(values["policy_version"]),
        "policy_document_sha256": _explicit_value(values["policy_document_sha256"]),
        "promotion_review_payload_sha256": _explicit_value(
            values["promotion_review_payload_sha256"]
        ),
        "reference_prompt_artifact_sha256": _explicit_value(
            values["reference_prompt_artifact_sha256"]
        ),
        "provider_attempt_outcome_id": _explicit_value(
            values["provider_attempt_outcome_id"]
        ),
        "provider_attempt_outcome_sha256": _explicit_value(
            values["provider_attempt_outcome_sha256"]
        ),
        "candidate_id": _explicit_value(values["candidate_id"]),
        "candidate_sha256": _explicit_value(values["candidate_sha256"]),
        "output_ordinal": _explicit_value(values["output_ordinal"]),
        "media_type": _explicit_value(values["media_type"]),
        "media_content_sha256": _explicit_value(values["media_content_sha256"]),
        "media_size_bytes": _explicit_value(values["media_size_bytes"]),
        "media_technical_record_sha256": _explicit_value(
            values["media_technical_record_sha256"]
        ),
        "qualification_request_id": _explicit_value(values["qualification_request_id"]),
        "qualification_request_sha256": _explicit_value(
            values["qualification_request_sha256"]
        ),
        "qualification_decision_id": _explicit_value(
            values["qualification_decision_id"]
        ),
        "qualification_decision_sha256": _explicit_value(
            values["qualification_decision_sha256"]
        ),
        "qualification_decision_at": _explicit_value(
            values["qualification_decision_at"]
        ),
        "qualification_valid_until": _explicit_value(
            values["qualification_valid_until"]
        ),
        "manifest_id": _explicit_value(values["manifest_id"]),
        "manifest_sha256": _explicit_value(values["manifest_sha256"]),
        "manifest_at": _explicit_value(values["manifest_at"]),
        "manifest_valid_until": _explicit_value(values["manifest_valid_until"]),
        "reviewed_rights_scope": _explicit_value(values["reviewed_rights_scope"]),
        "status_subject_closure_id": _explicit_value(values["status_subject_closure_id"]),
        "status_subject_closure_sha256": _explicit_value(
            values["status_subject_closure_sha256"]
        ),
        "requested_status_record_id": _explicit_value(values["requested_status_record_id"]),
        "requested_status_record_sha256": _explicit_value(
            values["requested_status_record_sha256"]
        ),
        "requested_status_receipt_id": _explicit_value(
            values["requested_status_receipt_id"]
        ),
        "requested_status_receipt_sha256": _explicit_value(
            values["requested_status_receipt_sha256"]
        ),
        "requested_explicit_chain_set_sha256": _explicit_value(
            values["requested_explicit_chain_set_sha256"]
        ),
        "requested_coverage_set_sha256": _explicit_value(
            values["requested_coverage_set_sha256"]
        ),
        "requested_joint_replay_sha256": _explicit_value(
            values["requested_joint_replay_sha256"]
        ),
        "requested_as_of_assessment_sha256": _explicit_value(
            values["requested_as_of_assessment_sha256"]
        ),
        "requested_as_of": _explicit_value(values["requested_as_of"]),
        "requested_as_of_status": _explicit_value(values["requested_as_of_status"]),
        "requested_status_valid_until": _explicit_value(
            values["requested_status_valid_until"]
        ),
        "requested_primary_asset_binding": _explicit_value(
            values["requested_primary_asset_binding"]
        ),
        "maker_identity_ref_sha256": _explicit_value(values["maker_identity_ref_sha256"]),
        "maker_action_sha256": _explicit_value(values["maker_action_sha256"]),
        "maker_prepared_at": _explicit_value(values["maker_prepared_at"]),
        "requested_at": _explicit_value(values["requested_at"]),
        "request_valid_until": _explicit_value(values["request_valid_until"]),
        "request_basis": _explicit_value(values["request_basis"]),
        "requested_representation": _explicit_value(values["requested_representation"]),
        "composite_media_unsplit": _explicit_value(values["composite_media_unsplit"]),
        "role_assignment_embedded": _explicit_value(values["role_assignment_embedded"]),
        "bible_mutation_requested": _explicit_value(values["bible_mutation_requested"]),
        "provider_input_requested": _explicit_value(values["provider_input_requested"]),
        "promotion_performed": _explicit_value(values["promotion_performed"]),
        "sidecar_materialized": _explicit_value(values["sidecar_materialized"]),
        "eligible_for_separate_role_binding_review": _explicit_value(
            values["eligible_for_separate_role_binding_review"]
        ),
        "status": _explicit_value(values["status"]),
        "evidence_scope": _explicit_value(values["evidence_scope"]),
        "authority_scope": _explicit_value(values["authority_scope"]),
        "current_gate": _explicit_value(values["current_gate"]),
        "provider_state": _explicit_value(values["provider_state"]),
        "generation_authorized": _explicit_value(values["generation_authorized"]),
        "execution_authorized": _explicit_value(values["execution_authorized"]),
        "publication_authorized": _explicit_value(values["publication_authorized"]),
        "remote_processing_allowed": _explicit_value(values["remote_processing_allowed"]),
        "retention_allowed": _explicit_value(values["retention_allowed"]),
        "training_allowed": _explicit_value(values["training_allowed"]),
        "publication_allowed": _explicit_value(values["publication_allowed"]),
        "automated_execution_allowed": _explicit_value(
            values["automated_execution_allowed"]
        ),
        "authorized_attempts": _explicit_value(values["authorized_attempts"]),
        "authorized_cost_cny": _explicit_value(values["authorized_cost_cny"]),
        "posts_allowed": _explicit_value(values["posts_allowed"]),
        "provider_requests": _explicit_value(values["provider_requests"]),
        "grants_rights": _explicit_value(values["grants_rights"]),
        "grants_qualification": _explicit_value(values["grants_qualification"]),
        "grants_execution_authority": _explicit_value(
            values["grants_execution_authority"]
        ),
        "eligible_for_asset_promotion": _explicit_value(
            values["eligible_for_asset_promotion"]
        ),
        "replaces_rights_manifest": _explicit_value(values["replaces_rights_manifest"]),
        "usage_restriction": _explicit_value(values["usage_restriction"]),
    }


def _decision_projection_from_values(values: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": _explicit_value(values["schema_version"]),
        "document_type": _explicit_value(values["document_type"]),
        "decision_scope": _explicit_value(values["decision_scope"]),
        "policy_id": _explicit_value(values["policy_id"]),
        "policy_version": _explicit_value(values["policy_version"]),
        "policy_document_sha256": _explicit_value(values["policy_document_sha256"]),
        "promotion_review_payload_sha256": _explicit_value(
            values["promotion_review_payload_sha256"]
        ),
        "request_id": _explicit_value(values["request_id"]),
        "request_sha256": _explicit_value(values["request_sha256"]),
        "reference_prompt_artifact_sha256": _explicit_value(
            values["reference_prompt_artifact_sha256"]
        ),
        "provider_attempt_outcome_id": _explicit_value(
            values["provider_attempt_outcome_id"]
        ),
        "provider_attempt_outcome_sha256": _explicit_value(
            values["provider_attempt_outcome_sha256"]
        ),
        "candidate_id": _explicit_value(values["candidate_id"]),
        "candidate_sha256": _explicit_value(values["candidate_sha256"]),
        "media_content_sha256": _explicit_value(values["media_content_sha256"]),
        "qualification_request_id": _explicit_value(values["qualification_request_id"]),
        "qualification_request_sha256": _explicit_value(
            values["qualification_request_sha256"]
        ),
        "qualification_decision_id": _explicit_value(
            values["qualification_decision_id"]
        ),
        "qualification_decision_sha256": _explicit_value(
            values["qualification_decision_sha256"]
        ),
        "qualification_valid_until": _explicit_value(
            values["qualification_valid_until"]
        ),
        "manifest_id": _explicit_value(values["manifest_id"]),
        "manifest_sha256": _explicit_value(values["manifest_sha256"]),
        "manifest_valid_until": _explicit_value(values["manifest_valid_until"]),
        "reviewed_rights_scope": _explicit_value(values["reviewed_rights_scope"]),
        "requested_primary_asset_binding": _explicit_value(
            values["requested_primary_asset_binding"]
        ),
        "promotion_primary_asset_binding": _explicit_value(
            values["promotion_primary_asset_binding"]
        ),
        "status_subject_closure_id": _explicit_value(values["status_subject_closure_id"]),
        "status_subject_closure_sha256": _explicit_value(
            values["status_subject_closure_sha256"]
        ),
        "promotion_status_record_id": _explicit_value(values["promotion_status_record_id"]),
        "promotion_status_record_sha256": _explicit_value(
            values["promotion_status_record_sha256"]
        ),
        "promotion_status_receipt_id": _explicit_value(
            values["promotion_status_receipt_id"]
        ),
        "promotion_status_receipt_sha256": _explicit_value(
            values["promotion_status_receipt_sha256"]
        ),
        "promotion_explicit_chain_set_sha256": _explicit_value(
            values["promotion_explicit_chain_set_sha256"]
        ),
        "promotion_coverage_set_sha256": _explicit_value(
            values["promotion_coverage_set_sha256"]
        ),
        "promotion_joint_replay_sha256": _explicit_value(
            values["promotion_joint_replay_sha256"]
        ),
        "promotion_as_of_assessment_sha256": _explicit_value(
            values["promotion_as_of_assessment_sha256"]
        ),
        "promotion_as_of_status": _explicit_value(values["promotion_as_of_status"]),
        "promotion_status_valid_until": _explicit_value(
            values["promotion_status_valid_until"]
        ),
        "checker_identity_ref_sha256": _explicit_value(
            values["checker_identity_ref_sha256"]
        ),
        "checker_action_sha256": _explicit_value(values["checker_action_sha256"]),
        "checker_reviewed_at": _explicit_value(values["checker_reviewed_at"]),
        "decision_at": _explicit_value(values["decision_at"]),
        "promotion_at": _explicit_value(values["promotion_at"]),
        "gate_results": _explicit_value(values["gate_results"]),
        "promotion_issue_codes": _explicit_value(values["promotion_issue_codes"]),
        "promotion_basis": _explicit_value(values["promotion_basis"]),
        "decision": _explicit_value(values["decision"]),
        "sidecar_materialization_allowed": _explicit_value(
            values["sidecar_materialization_allowed"]
        ),
        "promotion_review_performed": _explicit_value(values["promotion_review_performed"]),
        "sidecar_id_embedded": _explicit_value(values["sidecar_id_embedded"]),
        "role_assignment_embedded": _explicit_value(values["role_assignment_embedded"]),
        "provider_input_eligible": _explicit_value(values["provider_input_eligible"]),
        "status": _explicit_value(values["status"]),
        "evidence_scope": _explicit_value(values["evidence_scope"]),
        "authority_scope": _explicit_value(values["authority_scope"]),
        "current_gate": _explicit_value(values["current_gate"]),
        "provider_state": _explicit_value(values["provider_state"]),
        "generation_authorized": _explicit_value(values["generation_authorized"]),
        "execution_authorized": _explicit_value(values["execution_authorized"]),
        "publication_authorized": _explicit_value(values["publication_authorized"]),
        "remote_processing_allowed": _explicit_value(values["remote_processing_allowed"]),
        "retention_allowed": _explicit_value(values["retention_allowed"]),
        "training_allowed": _explicit_value(values["training_allowed"]),
        "publication_allowed": _explicit_value(values["publication_allowed"]),
        "automated_execution_allowed": _explicit_value(
            values["automated_execution_allowed"]
        ),
        "authorized_attempts": _explicit_value(values["authorized_attempts"]),
        "authorized_cost_cny": _explicit_value(values["authorized_cost_cny"]),
        "posts_allowed": _explicit_value(values["posts_allowed"]),
        "provider_requests": _explicit_value(values["provider_requests"]),
        "grants_rights": _explicit_value(values["grants_rights"]),
        "grants_qualification": _explicit_value(values["grants_qualification"]),
        "grants_execution_authority": _explicit_value(
            values["grants_execution_authority"]
        ),
        "eligible_for_asset_promotion": _explicit_value(
            values["eligible_for_asset_promotion"]
        ),
        "replaces_rights_manifest": _explicit_value(values["replaces_rights_manifest"]),
        "usage_restriction": _explicit_value(values["usage_restriction"]),
    }


def _sidecar_projection_from_values(values: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": _explicit_value(values["schema_version"]),
        "document_type": _explicit_value(values["document_type"]),
        "sidecar_scope": _explicit_value(values["sidecar_scope"]),
        "policy_id": _explicit_value(values["policy_id"]),
        "policy_version": _explicit_value(values["policy_version"]),
        "policy_document_sha256": _explicit_value(values["policy_document_sha256"]),
        "request_id": _explicit_value(values["request_id"]),
        "request_sha256": _explicit_value(values["request_sha256"]),
        "decision_id": _explicit_value(values["decision_id"]),
        "decision_sha256": _explicit_value(values["decision_sha256"]),
        "reference_prompt_artifact_sha256": _explicit_value(
            values["reference_prompt_artifact_sha256"]
        ),
        "provider_attempt_outcome_id": _explicit_value(
            values["provider_attempt_outcome_id"]
        ),
        "provider_attempt_outcome_sha256": _explicit_value(
            values["provider_attempt_outcome_sha256"]
        ),
        "candidate_id": _explicit_value(values["candidate_id"]),
        "candidate_sha256": _explicit_value(values["candidate_sha256"]),
        "output_ordinal": _explicit_value(values["output_ordinal"]),
        "media_type": _explicit_value(values["media_type"]),
        "media_content_sha256": _explicit_value(values["media_content_sha256"]),
        "media_size_bytes": _explicit_value(values["media_size_bytes"]),
        "media_technical_record_sha256": _explicit_value(
            values["media_technical_record_sha256"]
        ),
        "qualification_request_id": _explicit_value(values["qualification_request_id"]),
        "qualification_request_sha256": _explicit_value(
            values["qualification_request_sha256"]
        ),
        "qualification_decision_id": _explicit_value(
            values["qualification_decision_id"]
        ),
        "qualification_decision_sha256": _explicit_value(
            values["qualification_decision_sha256"]
        ),
        "qualification_valid_until": _explicit_value(
            values["qualification_valid_until"]
        ),
        "manifest_id": _explicit_value(values["manifest_id"]),
        "manifest_sha256": _explicit_value(values["manifest_sha256"]),
        "manifest_valid_until": _explicit_value(values["manifest_valid_until"]),
        "reviewed_rights_scope": _explicit_value(values["reviewed_rights_scope"]),
        "primary_asset_binding": _explicit_value(values["primary_asset_binding"]),
        "status_subject_closure_id": _explicit_value(values["status_subject_closure_id"]),
        "status_subject_closure_sha256": _explicit_value(
            values["status_subject_closure_sha256"]
        ),
        "promotion_status_record_id": _explicit_value(values["promotion_status_record_id"]),
        "promotion_status_record_sha256": _explicit_value(
            values["promotion_status_record_sha256"]
        ),
        "promotion_status_receipt_id": _explicit_value(
            values["promotion_status_receipt_id"]
        ),
        "promotion_status_receipt_sha256": _explicit_value(
            values["promotion_status_receipt_sha256"]
        ),
        "promotion_explicit_chain_set_sha256": _explicit_value(
            values["promotion_explicit_chain_set_sha256"]
        ),
        "promotion_coverage_set_sha256": _explicit_value(
            values["promotion_coverage_set_sha256"]
        ),
        "promotion_joint_replay_sha256": _explicit_value(
            values["promotion_joint_replay_sha256"]
        ),
        "promotion_as_of_assessment_sha256": _explicit_value(
            values["promotion_as_of_assessment_sha256"]
        ),
        "promotion_as_of_status": _explicit_value(values["promotion_as_of_status"]),
        "promotion_at": _explicit_value(values["promotion_at"]),
        "promotion_status_valid_until": _explicit_value(
            values["promotion_status_valid_until"]
        ),
        "promotion_evidence_valid_until": _explicit_value(
            values["promotion_evidence_valid_until"]
        ),
        "origin_claim": _explicit_value(values["origin_claim"]),
        "origin_assurance": _explicit_value(values["origin_assurance"]),
        "sidecar_state": _explicit_value(values["sidecar_state"]),
        "promotion_performed": _explicit_value(values["promotion_performed"]),
        "eligible_for_separate_role_binding_review": _explicit_value(
            values["eligible_for_separate_role_binding_review"]
        ),
        "primary_asset_binding_replaced": _explicit_value(
            values["primary_asset_binding_replaced"]
        ),
        "bible_active_binding_changed": _explicit_value(values["bible_active_binding_changed"]),
        "asset_version_v1_created": _explicit_value(values["asset_version_v1_created"]),
        "composite_media_unsplit": _explicit_value(values["composite_media_unsplit"]),
        "role_assignment_embedded": _explicit_value(values["role_assignment_embedded"]),
        "provider_input_eligible": _explicit_value(values["provider_input_eligible"]),
        "present_currentness_asserted": _explicit_value(
            values["present_currentness_asserted"]
        ),
        "perpetual_eligibility_asserted": _explicit_value(
            values["perpetual_eligibility_asserted"]
        ),
        "supersedes_sidecar": _explicit_value(values["supersedes_sidecar"]),
        "status": _explicit_value(values["status"]),
        "evidence_scope": _explicit_value(values["evidence_scope"]),
        "authority_scope": _explicit_value(values["authority_scope"]),
        "current_gate": _explicit_value(values["current_gate"]),
        "provider_state": _explicit_value(values["provider_state"]),
        "generation_authorized": _explicit_value(values["generation_authorized"]),
        "execution_authorized": _explicit_value(values["execution_authorized"]),
        "publication_authorized": _explicit_value(values["publication_authorized"]),
        "remote_processing_allowed": _explicit_value(values["remote_processing_allowed"]),
        "retention_allowed": _explicit_value(values["retention_allowed"]),
        "training_allowed": _explicit_value(values["training_allowed"]),
        "publication_allowed": _explicit_value(values["publication_allowed"]),
        "automated_execution_allowed": _explicit_value(
            values["automated_execution_allowed"]
        ),
        "authorized_attempts": _explicit_value(values["authorized_attempts"]),
        "authorized_cost_cny": _explicit_value(values["authorized_cost_cny"]),
        "posts_allowed": _explicit_value(values["posts_allowed"]),
        "provider_requests": _explicit_value(values["provider_requests"]),
        "grants_rights": _explicit_value(values["grants_rights"]),
        "grants_qualification": _explicit_value(values["grants_qualification"]),
        "grants_execution_authority": _explicit_value(
            values["grants_execution_authority"]
        ),
        "eligible_for_asset_promotion": _explicit_value(
            values["eligible_for_asset_promotion"]
        ),
        "replaces_rights_manifest": _explicit_value(values["replaces_rights_manifest"]),
        "usage_restriction": _explicit_value(values["usage_restriction"]),
    }


def _projection_from_values(
    model_type: type[BaseModel], values: Mapping[str, object]
) -> dict[str, object]:
    if model_type is CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        return _request_projection_from_values(values)
    if model_type is CreativeSampleGeneratedReferenceAssetPromotionDecisionV1:
        return _decision_projection_from_values(values)
    if model_type is CreativeSampleGeneratedReferenceEligibleAssetSidecarV1:
        return _sidecar_projection_from_values(values)
    _fail("EXACT_INPUT_TYPE_REQUIRED", "unknown formal Contract type")


def _preflight_formal_contract(
    value: object, expected: type[BaseModel], *, field: str
) -> BaseModel:
    original = _preflight_formal_contract_structure(value, expected, field=field)
    _verify_formal_contract_policy(original, field=field)
    _verify_formal_contract_semantic(original, expected, field=field)
    rebuilt = _verify_formal_contract_authority_and_rebuild(
        original, expected, field=field
    )
    _verify_no_prohibited_boundary_connection(original, field=field)
    return rebuilt


def _preflight_formal_contract_structure(
    value: object, expected: type[BaseModel], *, field: str
) -> dict[str, object]:
    original = _preflight_formal_contract_resource(value, expected, field=field)
    _verify_formal_value_canonical(original, field=field)
    _verify_formal_contract_structure_values(original, expected, field=field)
    return original


def _preflight_formal_contract_resource(
    value: object, expected: type[BaseModel], *, field: str
) -> dict[str, object]:
    if type(value) is not expected:
        _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} must have exact type {expected.__name__}")
    try:
        explicit = _explicit_value(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", f"{field} cannot expose its frozen fields"
        ) from exc
    if type(explicit) is not dict:
        _fail("CONTRACT_FIELD_INVALID", f"{field} is not one frozen object")
    original = cast(dict[str, object], explicit)
    try:
        encoded = (
            json.dumps(
                original,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                separators=(",", ": "),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8", errors="surrogatepass")
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", f"{field} cannot encode its frozen JSON fields"
        ) from exc
    if not 1 <= len(encoded) <= _MAX_FORMAL_DOCUMENT_BYTES:
        _fail("DOCUMENT_RESOURCE_LIMIT_EXCEEDED", f"{field} exceeds formal byte limits")
    return original


def _verify_formal_contract_structure_values(
    original: Mapping[str, object], expected: type[BaseModel], *, field: str
) -> None:
    id_field, sha_field, stem, domain = _IDENTITY_SPECS[expected]
    sanitized = dict(original)
    sanitized["policy_id"] = _FROZEN_PROMOTION_POLICY_ID
    sanitized["policy_version"] = _FROZEN_PROMOTION_POLICY_VERSION
    sanitized["policy_document_sha256"] = _FROZEN_PROMOTION_POLICY_DOCUMENT_SHA256
    sanitized.update(_zero_authority_values())
    try:
        if expected is CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
            sanitized["promotion_review_payload_sha256"] = _semantic_sha256(
                GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
                _review_payload_projection_from_values(sanitized),
            )
        sanitized_projection = _projection_from_values(expected, sanitized)
        sanitized_digest = _semantic_sha256(domain, sanitized_projection)
        sanitized[id_field] = f"{stem}{sanitized_digest[:20]}"
        sanitized[sha_field] = sanitized_digest
        expected.model_validate(_arrays_to_tuples(sanitized))
    except GeneratedReferenceAssetPromotionError:
        raise
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", f"{field} fails frozen structural validation"
        ) from exc


def _verify_formal_value_canonical(value: object, *, field: str) -> None:
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise GeneratedReferenceAssetPromotionError(
                "CANONICAL_JSON_REQUIRED",
                f"{field} contains a string that cannot use canonical UTF-8",
            ) from exc
        if unicodedata.normalize("NFC", value) != value:
            _fail(
                "CANONICAL_JSON_REQUIRED",
                f"{field} contains a string that is not canonical Unicode NFC",
            )
        return
    if type(value) is dict:
        for key, item in cast(dict[object, object], value).items():
            _verify_formal_value_canonical(key, field=field)
            _verify_formal_value_canonical(item, field=field)
        return
    if type(value) in {tuple, list}:
        for item in cast(tuple[object, ...] | list[object], value):
            _verify_formal_value_canonical(item, field=field)


def _verify_formal_contract_policy(
    original: Mapping[str, object], *, field: str
) -> None:
    _verify_policy_identity()
    if (
        original.get("policy_id") != _FROZEN_PROMOTION_POLICY_ID
        or original.get("policy_version") != _FROZEN_PROMOTION_POLICY_VERSION
        or original.get("policy_document_sha256")
        != _FROZEN_PROMOTION_POLICY_DOCUMENT_SHA256
    ):
        _fail("POLICY_IDENTITY_MISMATCH", f"{field} policy identity drifted")


def _verify_formal_contract_semantic(
    original: Mapping[str, object], expected: type[BaseModel], *, field: str
) -> None:
    id_field, sha_field, stem, domain = _IDENTITY_SPECS[expected]
    try:
        if expected is CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
            expected_review_sha = _semantic_sha256(
                GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
                _review_payload_projection_from_values(original),
            )
            if original.get("promotion_review_payload_sha256") != expected_review_sha:
                _fail(
                    "SEMANTIC_ID_OR_DIGEST_MISMATCH",
                    f"{field} Promotion review-payload digest drifted",
                )
        projection = _projection_from_values(expected, original)
        digest = _semantic_sha256(domain, projection)
    except GeneratedReferenceAssetPromotionError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", f"{field} identity projection is incomplete"
        ) from exc
    if original.get(sha_field) != digest or original.get(id_field) != f"{stem}{digest[:20]}":
        _fail(
            "SEMANTIC_ID_OR_DIGEST_MISMATCH", f"{field} semantic ID or digest drifted"
        )


def _verify_formal_contract_authority_and_rebuild(
    original: Mapping[str, object], expected: type[BaseModel], *, field: str
) -> BaseModel:
    _verify_formal_contract_authority(original, field=field)
    return _rebuild_formal_contract(original, expected, field=field)


def _verify_formal_contract_authority(
    original: Mapping[str, object], *, field: str
) -> None:
    if any(original.get(name) != expected_value for name, expected_value in _ZERO_AUTHORITY_VALUES.items()):
        _fail("AUTHORITY_SURFACE_NONZERO", f"{field} authority surface is not exact zero")


def _rebuild_formal_contract(
    original: Mapping[str, object], expected: type[BaseModel], *, field: str
) -> BaseModel:
    try:
        return expected.model_validate(_arrays_to_tuples(original))
    except (TypeError, ValueError, ValidationError) as exc:  # pragma: no cover - defensive
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", f"{field} fails final exact revalidation"
        ) from exc


_HUMAN_BASIS_LEAF_FIELDS = frozenset(
    {
        "basis",
        "request_basis",
        "promotion_basis",
        "output_copyright_and_commercial_scope_basis",
        "likeness_privacy_and_sensitive_data_basis",
        "brand_and_protected_content_basis",
        "retention_and_deletion_basis",
        "training_use_prohibition_basis",
        "review_basis",
    }
)
_PROHIBITED_BOUNDARY_MAPPING_KEYS = frozenset(
    {
        "path",
        "file_path",
        "filesystem_path",
        "local_path",
        "url",
        "uri",
        "provider_endpoint",
        "credential",
        "credentials",
        "api_key",
        "token",
        "access_token",
        "refresh_token",
        "bearer_token",
        "provider_task_id",
        "account_id",
        "response_body",
        "raw_legal_document",
        "private_key",
        "secret",
        "client_secret",
    }
)
_SENSITIVE_BOUNDARY_NOUN_PATTERN = re.compile(
    r"\b(?:credentials?|api[_ -]?keys?|tokens?|bearer|provider[_ -]?task[_ -]?ids?|"
    r"account[_ -]?ids?|response[_ -]?bod(?:y|ies)|raw[_ -]?legal[_ -]?documents?|"
    r"private[_ -]?keys?|client[_ -]?secrets?)\b",
    flags=re.IGNORECASE,
)
_SENSITIVE_BOUNDARY_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:credentials?|api[_ -]?keys?|tokens?|access[_ -]?tokens?|"
    r"refresh[_ -]?tokens?|bearer[_ -]?tokens?|provider[_ -]?task[_ -]?ids?|"
    r"account[_ -]?ids?|response[_ -]?bod(?:y|ies)|raw[_ -]?legal[_ -]?documents?|"
    r"private[_ -]?keys?|client[_ -]?secrets?|secrets?)\b[ \t]*[:=][ \t]*[^\s,;]+",
    flags=re.IGNORECASE,
)
_PROHIBITED_URI_PATTERN = re.compile(
    r"[A-Za-z][A-Za-z0-9+.-]*://[^\s]+", flags=re.IGNORECASE
)
_WINDOWS_DRIVE_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s<>\"|?*]+"
)
_WINDOWS_UNC_PATH_PATTERN = re.compile(r"\\\\[^\\/\s]+[\\/][^\\/\s]+")
_POSIX_ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9:/])/(?!/)[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*"
)
_DOT_RELATIVE_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9.])\.\.?[\\/][^\s<>\"|?*]+"
)
_ROOT_PATH_PATTERN = re.compile(
    r"^[ \t]*(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+|/|\.\.?[\\/])[ \t]*$"
)
_BEARER_SECRET_PATTERN = re.compile(r"\bbearer[ \t]+[^\s,;]+", flags=re.IGNORECASE)
_PORTABLE_SECRET_SHAPE_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\b(?:sk|pk|rk)-(?:[A-Za-z0-9_-]{8,})\b"
    r"|\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"
)


def _normalized_boundary_key(value: str) -> str:
    return re.sub(r"[ -]+", "_", value.casefold())


def _verify_no_prohibited_boundary_connection(
    value: object, *, field: str, path: tuple[str, ...] = ()
) -> None:
    if type(value) is str:
        actual_material = any(
            pattern.search(value) is not None
            for pattern in (
                _PROHIBITED_URI_PATTERN,
                _WINDOWS_DRIVE_PATH_PATTERN,
                _WINDOWS_UNC_PATH_PATTERN,
                _POSIX_ABSOLUTE_PATH_PATTERN,
                _DOT_RELATIVE_PATH_PATTERN,
                _ROOT_PATH_PATTERN,
                _SENSITIVE_BOUNDARY_ASSIGNMENT_PATTERN,
                _BEARER_SECRET_PATTERN,
                _PORTABLE_SECRET_SHAPE_PATTERN,
            )
        )
        human_basis_leaf = bool(path) and path[-1] in _HUMAN_BASIS_LEAF_FIELDS
        if actual_material or (
            not human_basis_leaf
            and _SENSITIVE_BOUNDARY_NOUN_PATTERN.search(value) is not None
        ):
            _fail(
                "PROHIBITED_BOUNDARY_CONNECTION",
                f"{field} contains a prohibited path, URL, credential, or Provider connection",
            )
        return
    if type(value) in {tuple, list}:
        for index, item in enumerate(cast(Sequence[object], value)):
            _verify_no_prohibited_boundary_connection(
                item, field=field, path=(*path, f"[{index}]")
            )
        return
    if type(value) is dict:
        for key, item in cast(dict[str, object], value).items():
            if type(key) is not str or (
                _normalized_boundary_key(key) in _PROHIBITED_BOUNDARY_MAPPING_KEYS
            ):
                _fail(
                    "PROHIBITED_BOUNDARY_CONNECTION",
                    f"{field} contains a prohibited structured boundary key",
                )
            _verify_no_prohibited_boundary_connection(
                item, field=field, path=(*path, key)
            )


def _review_payload_projection_from_request(
    value: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
) -> dict[str, object]:
    return {
        "policy_id": value.policy_id,
        "policy_version": value.policy_version,
        "policy_document_sha256": value.policy_document_sha256,
        "request_scope": value.request_scope,
        "reference_prompt_artifact_sha256": value.reference_prompt_artifact_sha256,
        "provider_attempt_outcome_id": value.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": value.provider_attempt_outcome_sha256,
        "candidate_id": value.candidate_id,
        "candidate_sha256": value.candidate_sha256,
        "output_ordinal": value.output_ordinal,
        "media_type": value.media_type,
        "media_content_sha256": value.media_content_sha256,
        "media_size_bytes": value.media_size_bytes,
        "media_technical_record_sha256": value.media_technical_record_sha256,
        "qualification_request_id": value.qualification_request_id,
        "qualification_request_sha256": value.qualification_request_sha256,
        "qualification_decision_id": value.qualification_decision_id,
        "qualification_decision_sha256": value.qualification_decision_sha256,
        "qualification_decision_at": value.qualification_decision_at,
        "qualification_valid_until": value.qualification_valid_until,
        "manifest_id": value.manifest_id,
        "manifest_sha256": value.manifest_sha256,
        "manifest_at": value.manifest_at,
        "manifest_valid_until": value.manifest_valid_until,
        "reviewed_rights_scope": _rights_scope_projection(value.reviewed_rights_scope),
        "status_subject_closure_id": value.status_subject_closure_id,
        "status_subject_closure_sha256": value.status_subject_closure_sha256,
        "requested_status_record_id": value.requested_status_record_id,
        "requested_status_record_sha256": value.requested_status_record_sha256,
        "requested_status_receipt_id": value.requested_status_receipt_id,
        "requested_status_receipt_sha256": value.requested_status_receipt_sha256,
        "requested_explicit_chain_set_sha256": value.requested_explicit_chain_set_sha256,
        "requested_coverage_set_sha256": value.requested_coverage_set_sha256,
        "requested_joint_replay_sha256": value.requested_joint_replay_sha256,
        "requested_as_of_assessment_sha256": value.requested_as_of_assessment_sha256,
        "requested_as_of": value.requested_as_of,
        "requested_as_of_status": value.requested_as_of_status,
        "requested_status_valid_until": value.requested_status_valid_until,
        "requested_primary_asset_binding": _primary_binding_projection_with_digest(
            value.requested_primary_asset_binding
        ),
        "requested_at": value.requested_at,
        "request_valid_until": value.request_valid_until,
        "request_basis": value.request_basis,
        "requested_representation": value.requested_representation,
        "composite_media_unsplit": value.composite_media_unsplit,
        "role_assignment_embedded": value.role_assignment_embedded,
        "bible_mutation_requested": value.bible_mutation_requested,
        "provider_input_requested": value.provider_input_requested,
    }


def generated_reference_asset_promotion_review_payload_projection(
    value: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
) -> dict[str, object]:
    validated = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _exact_model(
            value,
            CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
            field="request",
        ),
    )
    return _review_payload_projection_from_request(validated)


def generated_reference_asset_promotion_review_payload_sha256(
    value: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
        generated_reference_asset_promotion_review_payload_projection(value),
    )


_policy_bytes = _compact_json(_PROMOTION_POLICY)
if len(_policy_bytes) != 5_394 or _raw_sha256(_policy_bytes) != (
    _FROZEN_PROMOTION_POLICY_DOCUMENT_SHA256
):
    raise RuntimeError("ADR-045 frozen Promotion policy projection drifted")


def _verify_policy_identity() -> None:
    try:
        encoded = _compact_json(_PROMOTION_POLICY)
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "POLICY_IDENTITY_MISMATCH", "Promotion policy projection is not canonical"
        ) from exc
    if (
        GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_ID != _FROZEN_PROMOTION_POLICY_ID
        or GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_VERSION
        != _FROZEN_PROMOTION_POLICY_VERSION
        or GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256
        != _FROZEN_PROMOTION_POLICY_DOCUMENT_SHA256
        or _PROMOTION_POLICY.get("policy_id") != _FROZEN_PROMOTION_POLICY_ID
        or _PROMOTION_POLICY.get("policy_version") != _FROZEN_PROMOTION_POLICY_VERSION
        or len(encoded) != 5_394
        or _raw_sha256(encoded) != _FROZEN_PROMOTION_POLICY_DOCUMENT_SHA256
    ):
        _fail("POLICY_IDENTITY_MISMATCH", "Promotion policy identity drifted")


@dataclass(frozen=True, slots=True)
class GeneratedReferenceAssetPromotionUpstreamClosureInput:
    artifact: CreativeSampleReferenceVisualPromptArtifactV1
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1
    candidate: CreativeSampleGeneratedReferenceCandidateV1
    qualification_request: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1
    qualification_decision: CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1
    png_bytes: bytes
    qualification_evidence_documents: tuple[GeneratedReferenceQualificationEvidenceInput, ...]
    qualification_preparer_identity_bytes: bytes
    qualification_preparer_action_bytes: bytes
    qualifier_identity_bytes: bytes
    qualifier_action_bytes: bytes
    manifest: CreativeSampleGeneratedReferenceRightsManifestV1
    manifest_review_evidence_documents: tuple[GeneratedReferenceRightsManifestEvidenceInput, ...]
    manifest_proposed_rights_scope: GeneratedReferenceRightsScopeProposalV1
    manifest_maker_identity_bytes: bytes
    manifest_maker_action_bytes: bytes
    manifest_checker_identity_bytes: bytes
    manifest_checker_action_bytes: bytes
    manifest_at: str


@dataclass(frozen=True, slots=True)
class GeneratedReferenceAssetPromotionStatusClosureInput:
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1
    instruction: CreativeSampleGeneratedReferenceCurrentStatusInstructionV1
    decision: CreativeSampleGeneratedReferenceCurrentStatusDecisionV1
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...]
    receipt: CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1
    status_preparer_identity_bytes: bytes
    status_preparer_action_bytes: bytes
    status_checker_identity_bytes: bytes
    status_checker_action_bytes: bytes


@dataclass(frozen=True, slots=True)
class GeneratedReferenceAssetPromotionFinalizationResult:
    decision: CreativeSampleGeneratedReferenceAssetPromotionDecisionV1
    sidecar: CreativeSampleGeneratedReferenceEligibleAssetSidecarV1 | None

    def __post_init__(self) -> None:
        _validate_finalization_result_invariant(self)


def _verify_positive_finalization_pair_linkage(
    decision: CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
    sidecar: CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
) -> None:
    shared_fields = (
        "decision_id",
        "decision_sha256",
        "request_id",
        "request_sha256",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "reference_prompt_artifact_sha256",
        "provider_attempt_outcome_id",
        "provider_attempt_outcome_sha256",
        "candidate_id",
        "candidate_sha256",
        "media_content_sha256",
        "qualification_request_id",
        "qualification_request_sha256",
        "qualification_decision_id",
        "qualification_decision_sha256",
        "qualification_valid_until",
        "manifest_id",
        "manifest_sha256",
        "manifest_valid_until",
        "reviewed_rights_scope",
        "status_subject_closure_id",
        "status_subject_closure_sha256",
        "promotion_status_record_id",
        "promotion_status_record_sha256",
        "promotion_status_receipt_id",
        "promotion_status_receipt_sha256",
        "promotion_explicit_chain_set_sha256",
        "promotion_coverage_set_sha256",
        "promotion_joint_replay_sha256",
        "promotion_as_of_assessment_sha256",
        "promotion_as_of_status",
        "promotion_at",
        "promotion_status_valid_until",
    )
    if any(getattr(sidecar, name) != getattr(decision, name) for name in shared_fields) or (
        sidecar.primary_asset_binding != decision.promotion_primary_asset_binding
    ):
        _fail(
            "CONTRACT_FIELD_INVALID",
            "positive finalization Decision and Sidecar do not form one atomic pair",
        )


def _validate_finalization_result_invariant(
    value: GeneratedReferenceAssetPromotionFinalizationResult,
) -> None:
    if type(value.decision) is not CreativeSampleGeneratedReferenceAssetPromotionDecisionV1:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "finalization Decision has the wrong exact type")
    if value.sidecar is not None and (
        type(value.sidecar) is not CreativeSampleGeneratedReferenceEligibleAssetSidecarV1
    ):
        _fail("EXACT_INPUT_TYPE_REQUIRED", "finalization Sidecar has the wrong exact type")

    decision_values = _preflight_formal_contract_resource(
        value.decision,
        CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
        field="finalization Decision",
    )
    sidecar_values = (
        _preflight_formal_contract_resource(
            value.sidecar,
            CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
            field="finalization Sidecar",
        )
        if value.sidecar is not None
        else None
    )
    _verify_formal_value_canonical(decision_values, field="finalization Decision")
    if sidecar_values is not None:
        _verify_formal_value_canonical(sidecar_values, field="finalization Sidecar")
    _verify_formal_contract_structure_values(
        decision_values,
        CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
        field="finalization Decision",
    )
    if sidecar_values is not None:
        _verify_formal_contract_structure_values(
            sidecar_values,
            CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
            field="finalization Sidecar",
        )

    positive = (
        decision_values["decision"] == "APPROVE_ELIGIBLE_ASSET_SIDECAR"
    )
    if sidecar_values is None and positive:
        _fail(
            "CONTRACT_FIELD_INVALID",
            "a positive finalization result cannot omit its atomic Sidecar",
        )
    if positive and value.sidecar is not None:
        _verify_positive_finalization_pair_linkage(value.decision, value.sidecar)

    _verify_formal_contract_policy(decision_values, field="finalization Decision")
    if sidecar_values is not None:
        _verify_formal_contract_policy(sidecar_values, field="finalization Sidecar")
    _verify_formal_contract_semantic(
        decision_values,
        CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
        field="finalization Decision",
    )
    if sidecar_values is not None:
        _verify_formal_contract_semantic(
            sidecar_values,
            CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
            field="finalization Sidecar",
        )
    if sidecar_values is not None and not positive:
        _fail(
            "PROMOTION_GATE_NOT_PASS",
            "a non-positive Promotion Decision cannot carry a Sidecar",
        )

    _verify_formal_contract_authority(decision_values, field="finalization Decision")
    if sidecar_values is not None:
        _verify_formal_contract_authority(sidecar_values, field="finalization Sidecar")
    _verify_no_prohibited_boundary_connection(
        decision_values, field="finalization Decision"
    )
    if sidecar_values is not None:
        _verify_no_prohibited_boundary_connection(
            sidecar_values, field="finalization Sidecar"
        )
    _rebuild_formal_contract(
        decision_values,
        CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
        field="finalization Decision",
    )
    if sidecar_values is None:
        return
    _rebuild_formal_contract(
        sidecar_values,
        CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
        field="finalization Sidecar",
    )
def build_generated_reference_promotion_primary_asset_binding(
    bible: CharacterBible | SceneBible,
    active_asset_version: CharacterAssetVersion | SceneAssetVersion,
) -> GeneratedReferencePromotionPrimaryAssetBindingV1:
    """Rebuild one exact active imported V1 primary binding without mutating the Bible."""

    if type(bible) is not CharacterBible and type(bible) is not SceneBible:
        _fail(
            "EXACT_INPUT_TYPE_REQUIRED",
            "bible must be one exact released CharacterBible or SceneBible",
        )
    if (
        type(active_asset_version) is not CharacterAssetVersion
        and type(active_asset_version) is not SceneAssetVersion
    ):
        _fail(
            "EXACT_INPUT_TYPE_REQUIRED",
            "active_asset_version must be one exact released CharacterAssetVersion or "
            "SceneAssetVersion",
        )
    try:
        validated_bible: CharacterBible | SceneBible
        validated_asset: CharacterAssetVersion | SceneAssetVersion
        if type(bible) is CharacterBible:
            if type(active_asset_version) is not CharacterAssetVersion:
                _fail(
                    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                    "CharacterBible requires one exact CharacterAssetVersion",
                )
            validated_bible = cast(
                CharacterBible,
                _revalidate_external_model(bible, CharacterBible, field="CharacterBible"),
            )
            validated_asset = cast(
                CharacterAssetVersion,
                _revalidate_external_model(
                    active_asset_version,
                    CharacterAssetVersion,
                    field="CharacterAssetVersion",
                ),
            )
            if not 1 <= len(validated_bible.asset_versions) <= 64:
                _fail(
                    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                    "CharacterBible AssetVersion count is outside 1..64",
                )
            character_active_values = tuple(
                item
                for item in validated_bible.asset_versions
                if item.id == validated_bible.active_asset_version_id
            )
            if (
                len(character_active_values) != 1
                or type(character_active_values[0]) is not CharacterAssetVersion
            ):
                _fail(
                    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                    "CharacterBible active binding is not exact and unique",
                )
            if character_active_values[0] != validated_asset:
                _fail(
                    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                    "supplied CharacterAssetVersion is not the exact Bible-active value",
                )
            subject_id = validated_bible.character_id
            if validated_asset.character_id != subject_id:
                _fail(
                    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                    "CharacterAssetVersion crosses subject",
                )
            asset_purpose: AssetPurpose = "CHARACTER_REFERENCE_ASSET"
        elif type(bible) is SceneBible:
            if type(active_asset_version) is not SceneAssetVersion:
                _fail(
                    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                    "SceneBible requires one exact SceneAssetVersion",
                )
            validated_bible = cast(
                SceneBible,
                _revalidate_external_model(bible, SceneBible, field="SceneBible"),
            )
            validated_asset = cast(
                SceneAssetVersion,
                _revalidate_external_model(
                    active_asset_version, SceneAssetVersion, field="SceneAssetVersion"
                ),
            )
            if not 1 <= len(validated_bible.asset_versions) <= 64:
                _fail(
                    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                    "SceneBible AssetVersion count is outside 1..64",
                )
            scene_active_values = tuple(
                item
                for item in validated_bible.asset_versions
                if item.id == validated_bible.active_asset_version_id
            )
            if (
                len(scene_active_values) != 1
                or type(scene_active_values[0]) is not SceneAssetVersion
            ):
                _fail(
                    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                    "SceneBible active binding is not exact and unique",
                )
            if scene_active_values[0] != validated_asset:
                _fail(
                    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                    "supplied SceneAssetVersion is not the exact Bible-active value",
                )
            subject_id = validated_bible.scene_id
            if validated_asset.scene_id != subject_id:
                _fail(
                    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID", "SceneAssetVersion crosses subject"
                )
            asset_purpose = "SCENE_REFERENCE_ASSET"
        else:  # pragma: no cover - exact Bible type was admitted above
            raise AssertionError("unreachable primary Bible variant")

        projection_sha = generated_reference_primary_asset_version_projection_sha256(
            validated_asset
        )
        values: dict[str, object] = {
            "binding_profile": "sdc.generated-reference-promotion-primary-asset-binding.v1",
            "asset_purpose": asset_purpose,
            "subject_id": subject_id,
            "asset_version_id": validated_asset.id,
            "legacy_asset_version_projection_sha256": projection_sha,
            "version": validated_asset.version,
            "content_sha256": validated_asset.content_sha256,
            "media_type": validated_asset.media_type,
            "approval_ref": validated_asset.approval_ref,
            "provenance": validated_asset.provenance,
            "bible_active_asset_version_id": validated_bible.active_asset_version_id,
        }
        digest = _semantic_sha256(
            GENERATED_REFERENCE_PRIMARY_ASSET_BINDING_SHA256_DOMAIN, values
        )
        return GeneratedReferencePromotionPrimaryAssetBindingV1.model_validate(
            {"primary_asset_binding_sha256": digest, **values}
        )
    except GeneratedReferenceAssetPromotionError as exc:
        if exc.code in {
            "EXACT_INPUT_TYPE_REQUIRED",
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
        }:
            raise
        raise GeneratedReferenceAssetPromotionError(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "primary AssetVersion binding could not be reconstructed",
        ) from exc
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "primary AssetVersion binding could not be reconstructed",
        ) from exc


def _admit_retained_json(raw: bytes, *, maximum: int, field: str) -> dict[str, object]:
    if type(raw) is not bytes:
        _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} must be exact bytes")
    if not 1 <= len(raw) <= maximum:
        _fail("DOCUMENT_RESOURCE_LIMIT_EXCEEDED", f"{field} exceeds byte limits")
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
        _fail("CANONICAL_JSON_REQUIRED", f"{field} is not canonical persistent JSON")
    try:
        parsed = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_json_no_duplicates,
            parse_constant=lambda item: _invalid(f"non-finite number: {item}"),
        )
        _validate_json_tree(parsed)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CANONICAL_JSON_REQUIRED", f"{field} is invalid canonical JSON"
        ) from exc
    if type(parsed) is not dict or _persistent_json(parsed) != raw:
        _fail("CANONICAL_JSON_REQUIRED", f"{field} is not exact canonical object bytes")
    return cast(dict[str, object], parsed)


def _human_identity(raw: bytes, *, field: str) -> tuple[tuple[str, str], str]:
    value = _admit_retained_json(raw, maximum=16_384, field=field)
    if set(value) != {"document_profile", "identity_namespace", "identity_ref"}:
        _fail("CONTRACT_FIELD_INVALID", f"{field} has an unknown or missing field")
    if value["document_profile"] != "sdc.privacy-minimized-human-reference.v1":
        _fail("CONTRACT_FIELD_INVALID", f"{field} profile mismatch")
    namespace = value["identity_namespace"]
    identity_ref = value["identity_ref"]
    if (
        type(namespace) is not str
        or re.fullmatch(_PORTABLE_ID_PATTERN, namespace) is None
        or type(identity_ref) is not str
        or re.fullmatch(_PORTABLE_ID_PATTERN, identity_ref) is None
    ):
        _fail("CONTRACT_FIELD_INVALID", f"{field} identity tuple is invalid")
    return (namespace, identity_ref), _raw_sha256(raw)


def _exact_action(raw: bytes, expected: Mapping[str, object], *, field: str) -> str:
    actual = _admit_retained_json(raw, maximum=262_144, field=field)
    if actual != expected or _compact_json(actual) != _compact_json(dict(expected)):
        _fail("UPSTREAM_CLOSURE_MISMATCH", f"{field} does not close the exact action")
    return _raw_sha256(raw)


def _collect_sha256_strings(value: object, *, seen: set[int] | None = None) -> set[str]:
    if seen is None:
        seen = set()
    if type(value) is str:
        return {value} if re.fullmatch(_LOWER_SHA256_PATTERN, value) else set()
    if type(value) is bytes:
        return {_raw_sha256(value)}
    if value is None or type(value) in {bool, int, float}:
        return set()
    identity = id(value)
    if identity in seen:
        return set()
    seen.add(identity)
    result: set[str] = set()
    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            result.update(_collect_sha256_strings(getattr(value, name), seen=seen))
    elif is_dataclass(value):
        for field_info in fields(value):
            result.update(
                _collect_sha256_strings(getattr(value, field_info.name), seen=seen)
            )
    elif type(value) in {tuple, list}:
        for sequence_item in cast(Sequence[object], value):
            result.update(_collect_sha256_strings(sequence_item, seen=seen))
    elif type(value) is dict:
        for mapping_item in cast(dict[object, object], value).values():
            result.update(_collect_sha256_strings(mapping_item, seen=seen))
    return result


def _preflight_upstream_input_types(
    closure: GeneratedReferenceAssetPromotionUpstreamClosureInput,
) -> None:
    if type(closure) is not GeneratedReferenceAssetPromotionUpstreamClosureInput:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "upstream closure has the wrong process type")
    for value, expected, field in (
        (closure.artifact, CreativeSampleReferenceVisualPromptArtifactV1, "Artifact"),
        (closure.outcome, CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1, "Outcome"),
        (closure.candidate, CreativeSampleGeneratedReferenceCandidateV1, "Candidate"),
        (
            closure.qualification_request,
            CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
            "Qualification Request",
        ),
        (
            closure.qualification_decision,
            CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
            "Qualification Decision",
        ),
        (closure.manifest, CreativeSampleGeneratedReferenceRightsManifestV1, "Manifest"),
        (
            closure.manifest_proposed_rights_scope,
            GeneratedReferenceRightsScopeProposalV1,
            "Manifest Rights proposal",
        ),
    ):
        if type(value) is not expected:
            _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} has the wrong exact type")
    if type(closure.qualification_evidence_documents) is not tuple:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "Qualification evidence collection must be a tuple")
    if type(closure.manifest_review_evidence_documents) is not tuple:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "Manifest evidence collection must be a tuple")
    for qualification_item in closure.qualification_evidence_documents:
        if type(qualification_item) is not GeneratedReferenceQualificationEvidenceInput:
            _fail("EXACT_INPUT_TYPE_REQUIRED", "Qualification evidence input type mismatch")
    for manifest_item in closure.manifest_review_evidence_documents:
        if type(manifest_item) is not GeneratedReferenceRightsManifestEvidenceInput:
            _fail("EXACT_INPUT_TYPE_REQUIRED", "Manifest evidence input type mismatch")
    for raw, field in (
        (closure.png_bytes, "png_bytes"),
        (closure.qualification_preparer_identity_bytes, "Qualification Preparer identity"),
        (closure.qualification_preparer_action_bytes, "Qualification Preparer action"),
        (closure.qualifier_identity_bytes, "Qualification Qualifier identity"),
        (closure.qualifier_action_bytes, "Qualification Qualifier action"),
        (closure.manifest_maker_identity_bytes, "Manifest Maker identity"),
        (closure.manifest_maker_action_bytes, "Manifest Maker action"),
        (closure.manifest_checker_identity_bytes, "Manifest Checker identity"),
        (closure.manifest_checker_action_bytes, "Manifest Checker action"),
    ):
        if type(raw) is not bytes:
            _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} must be exact bytes")
    if type(closure.manifest_at) is not str:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "manifest_at must be an exact string")


def _preflight_status_input_types(
    closure: GeneratedReferenceAssetPromotionStatusClosureInput, *, field: str
) -> None:
    if type(closure) is not GeneratedReferenceAssetPromotionStatusClosureInput:
        _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} closure has the wrong process type")
    for value, expected, name in (
        (closure.subject_closure, GeneratedReferenceCurrentStatusSubjectClosureV1, "Subject"),
        (closure.request, CreativeSampleGeneratedReferenceCurrentStatusRequestV1, "Request"),
        (
            closure.instruction,
            CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
            "Instruction",
        ),
        (closure.decision, CreativeSampleGeneratedReferenceCurrentStatusDecisionV1, "Decision"),
        (closure.record, CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1, "Record"),
        (
            closure.receipt,
            CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
            "Receipt",
        ),
    ):
        if type(value) is not expected:
            _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} Status {name} type mismatch")
    if type(closure.chain_inputs) is not tuple:
        _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} chain_inputs must be a tuple")
    for item in closure.chain_inputs:
        if type(item) is not GeneratedReferenceCurrentStatusExplicitChainInput:
            _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} chain input type mismatch")
    for raw, name in (
        (closure.status_preparer_identity_bytes, "Status Preparer identity"),
        (closure.status_preparer_action_bytes, "Status Preparer action"),
        (closure.status_checker_identity_bytes, "Status Checker identity"),
        (closure.status_checker_action_bytes, "Status Checker action"),
    ):
        if type(raw) is not bytes:
            _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} {name} must be exact bytes")


def _preflight_primary_input_types(
    bible: CharacterBible | SceneBible,
    asset: CharacterAssetVersion | SceneAssetVersion,
    *,
    field: str,
) -> None:
    if type(bible) is not CharacterBible and type(bible) is not SceneBible:
        _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} Bible has the wrong exact type")
    if type(asset) is not CharacterAssetVersion and type(asset) is not SceneAssetVersion:
        _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} AssetVersion has the wrong exact type")


_MAKER_ACTION_FIELDS = frozenset(
    {
        "document_profile",
        "action",
        "actor_ref_sha256",
        "promotion_review_payload_sha256",
        "candidate_sha256",
        "manifest_sha256",
        "requested_status_receipt_sha256",
        "requested_primary_asset_binding_sha256",
        "policy_document_sha256",
        "requested_at",
    }
)
_CHECKER_ACTION_FIELDS = frozenset(
    {
        "document_profile",
        "action",
        "actor_ref_sha256",
        "request_sha256",
        "policy_document_sha256",
        "promotion_status_receipt_sha256",
        "promotion_primary_asset_binding_sha256",
        "promotion_at",
        "gate_results",
        "promotion_issue_codes",
        "promotion_basis",
        "decision",
        "sidecar_materialization_allowed",
    }
)


def _preflight_action_sha_fields(
    value: Mapping[str, object], names: tuple[str, ...], *, field: str
) -> None:
    for name in names:
        member = value.get(name)
        if type(member) is not str or re.fullmatch(_LOWER_SHA256_PATTERN, member) is None:
            _fail("CONTRACT_FIELD_INVALID", f"{field} {name} is not one lower SHA-256")


def _preflight_maker_action_structure(value: Mapping[str, object]) -> None:
    if set(value) != _MAKER_ACTION_FIELDS:
        _fail("CONTRACT_FIELD_INVALID", "Promotion Maker action field set drifted")
    if (
        value.get("document_profile")
        != "sdc.generated-reference-asset-promotion-request-preparation-action.v1"
        or value.get("action")
        != "PREPARED_GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST"
    ):
        _fail("CONTRACT_FIELD_INVALID", "Promotion Maker action profile drifted")
    _preflight_action_sha_fields(
        value,
        (
            "actor_ref_sha256",
            "promotion_review_payload_sha256",
            "candidate_sha256",
            "manifest_sha256",
            "requested_status_receipt_sha256",
            "requested_primary_asset_binding_sha256",
        ),
        field="Promotion Maker action",
    )
    try:
        _parse_utc(cast(str, value.get("requested_at")), field="requested_at")
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID",
            "Promotion Maker action requested_at is not canonical UTC seconds",
        ) from exc


def _preflight_checker_action_structure(value: Mapping[str, object]) -> None:
    if set(value) != _CHECKER_ACTION_FIELDS:
        _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action field set drifted")
    if (
        value.get("document_profile")
        != "sdc.generated-reference-asset-promotion-decision-action.v1"
        or value.get("action")
        != "RECORDED_GENERATED_REFERENCE_ASSET_PROMOTION_DECISION"
    ):
        _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action profile drifted")
    _preflight_action_sha_fields(
        value,
        (
            "actor_ref_sha256",
            "request_sha256",
            "promotion_status_receipt_sha256",
            "promotion_primary_asset_binding_sha256",
        ),
        field="Promotion Checker action",
    )
    try:
        _parse_utc(cast(str, value.get("promotion_at")), field="promotion_at")
        _human_text(cast(str, value.get("promotion_basis")), field="promotion_basis")
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID",
            "Promotion Checker action time or basis is structurally invalid",
        ) from exc
    gate_results = value.get("gate_results")
    if type(gate_results) is not list or len(gate_results) != len(PROMOTION_GATE_ORDER):
        _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action gate_results shape drifted")
    for ordinal, raw_gate in enumerate(cast(list[object], gate_results)):
        if type(raw_gate) is not dict:
            _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action gate member is not an object")
        gate = cast(dict[str, object], raw_gate)
        if set(gate) != {"ordinal", "gate", "result", "basis"}:
            _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action gate field set drifted")
        if type(gate.get("ordinal")) is not int or gate.get("ordinal") != ordinal:
            _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action gate ordinal drifted")
        if type(gate.get("gate")) is not str or type(gate.get("result")) is not str:
            _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action gate literal type drifted")
        if gate.get("result") not in {"PASS", "FAIL", "INDETERMINATE"}:
            _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action gate result is invalid")
        try:
            _human_text(cast(str, gate.get("basis")), field="gate basis")
        except (TypeError, ValueError) as exc:
            raise GeneratedReferenceAssetPromotionError(
                "CONTRACT_FIELD_INVALID",
                "Promotion Checker action gate basis is structurally invalid",
            ) from exc
    issues = value.get("promotion_issue_codes")
    if type(issues) is not list or len(issues) > len(PROMOTION_ISSUE_CODE_ORDER):
        _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action issue tuple shape drifted")
    if any(type(item) is not str for item in cast(list[object], issues)):
        _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action issue member type drifted")
    if value.get("decision") not in {
        "APPROVE_ELIGIBLE_ASSET_SIDECAR",
        "REJECT_ELIGIBLE_ASSET_SIDECAR",
        "INDETERMINATE_ELIGIBLE_ASSET_SIDECAR",
    }:
        _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action Decision literal drifted")
    if type(value.get("sidecar_materialization_allowed")) is not bool:
        _fail("CONTRACT_FIELD_INVALID", "Promotion Checker action materialization flag is invalid")


def _preflight_promotion_retained_documents(
    *,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    checker_identity_bytes: bytes | None = None,
    checker_action_bytes: bytes | None = None,
    verify_policy: bool = True,
) -> tuple[dict[str, object], dict[str, object] | None]:
    raw_inputs: list[tuple[bytes, int, str]] = [
        (maker_identity_bytes, 16_384, "Promotion Maker identity"),
        (maker_action_bytes, 262_144, "Promotion Maker action"),
    ]
    if checker_identity_bytes is not None and checker_action_bytes is not None:
        raw_inputs.extend(
            (
                (checker_identity_bytes, 16_384, "Promotion Checker identity"),
                (checker_action_bytes, 262_144, "Promotion Checker action"),
            )
        )
    for raw, maximum, field in raw_inputs:
        if not 1 <= len(raw) <= maximum:
            _fail("DOCUMENT_RESOURCE_LIMIT_EXCEEDED", f"{field} exceeds byte limits")
    parsed = {
        field: _admit_retained_json(raw, maximum=maximum, field=field)
        for raw, maximum, field in raw_inputs
    }
    _human_identity(maker_identity_bytes, field="Promotion Maker identity")
    maker_action = parsed["Promotion Maker action"]
    _preflight_maker_action_structure(maker_action)
    if checker_identity_bytes is None or checker_action_bytes is None:
        if verify_policy:
            _verify_promotion_retained_policy(maker_action, None)
        return maker_action, None
    _human_identity(checker_identity_bytes, field="Promotion Checker identity")
    checker_action = parsed["Promotion Checker action"]
    _preflight_checker_action_structure(checker_action)
    if verify_policy:
        _verify_promotion_retained_policy(maker_action, checker_action)
    return maker_action, checker_action


def _verify_promotion_retained_policy(
    maker_action: Mapping[str, object],
    checker_action: Mapping[str, object] | None,
) -> None:
    if maker_action.get("policy_document_sha256") != _FROZEN_PROMOTION_POLICY_DOCUMENT_SHA256:
        _fail("POLICY_IDENTITY_MISMATCH", "Promotion Maker action policy identity drifted")
    if checker_action is not None and checker_action.get("policy_document_sha256") != (
        _FROZEN_PROMOTION_POLICY_DOCUMENT_SHA256
    ):
        _fail("POLICY_IDENTITY_MISMATCH", "Promotion Checker action policy identity drifted")


def _preflight_prepare_inputs(
    upstream: GeneratedReferenceAssetPromotionUpstreamClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    primary_bible: CharacterBible | SceneBible,
    primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    *,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    requested_at: str,
    request_basis: str,
) -> None:
    _preflight_upstream_input_types(upstream)
    _preflight_status_input_types(request_status, field="request-time")
    _preflight_primary_input_types(
        primary_bible, primary_asset_version, field="request-time primary"
    )
    for value, field in (
        (maker_identity_bytes, "Promotion Maker identity"),
        (maker_action_bytes, "Promotion Maker action"),
    ):
        if type(value) is not bytes:
            _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} must be exact bytes")
    if type(requested_at) is not str or type(request_basis) is not str:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "Request time and basis must be exact strings")
    maker_action, _checker_action = _preflight_promotion_retained_documents(
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        verify_policy=False,
    )
    try:
        _human_text(request_basis, field="request_basis")
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", "request_basis is not bounded canonical text"
        ) from exc
    _verify_policy_identity()
    _verify_promotion_retained_policy(maker_action, None)
    try:
        _parse_utc(requested_at, field="requested_at")
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "TIME_WINDOW_INVALID_OR_EXPIRED", "requested_at is not canonical UTC seconds"
        ) from exc


def _preflight_finalize_inputs(
    request: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
    upstream: GeneratedReferenceAssetPromotionUpstreamClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_bible: CharacterBible | SceneBible,
    requested_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    final_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    promotion_primary_bible: CharacterBible | SceneBible,
    promotion_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    *,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    checker_identity_bytes: bytes,
    checker_action_bytes: bytes,
    promotion_at: str,
    primary_sidecar_association_result: GateResult,
    primary_sidecar_association_basis: str,
    composite_unsplit_role_deferral_result: GateResult,
    composite_unsplit_role_deferral_basis: str,
    promotion_basis: str,
) -> None:
    if type(request) is not CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "Promotion Request has the wrong exact type")
    _preflight_upstream_input_types(upstream)
    _preflight_status_input_types(request_status, field="request-time")
    _preflight_status_input_types(final_status, field="final")
    _preflight_primary_input_types(
        requested_primary_bible,
        requested_primary_asset_version,
        field="request-time primary",
    )
    _preflight_primary_input_types(
        promotion_primary_bible,
        promotion_primary_asset_version,
        field="final primary",
    )
    for raw_value, field in (
        (maker_identity_bytes, "Promotion Maker identity"),
        (maker_action_bytes, "Promotion Maker action"),
        (checker_identity_bytes, "Promotion Checker identity"),
        (checker_action_bytes, "Promotion Checker action"),
    ):
        if type(raw_value) is not bytes:
            _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} must be exact bytes")
    for text_value, field in (
        (promotion_at, "promotion_at"),
        (primary_sidecar_association_result, "primary association result"),
        (primary_sidecar_association_basis, "primary association basis"),
        (composite_unsplit_role_deferral_result, "role deferral result"),
        (composite_unsplit_role_deferral_basis, "role deferral basis"),
        (promotion_basis, "promotion_basis"),
    ):
        if type(text_value) is not str:
            _fail("EXACT_INPUT_TYPE_REQUIRED", f"{field} must be an exact string")
    maker_action, checker_action = _preflight_promotion_retained_documents(
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        checker_identity_bytes=checker_identity_bytes,
        checker_action_bytes=checker_action_bytes,
        verify_policy=False,
    )
    request_values = _preflight_formal_contract_structure(
        request,
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        field="Promotion Request",
    )
    if primary_sidecar_association_result not in {"PASS", "FAIL", "INDETERMINATE"} or (
        composite_unsplit_role_deferral_result not in {"PASS", "FAIL", "INDETERMINATE"}
    ):
        _fail("CONTRACT_FIELD_INVALID", "Promotion human gate result is invalid")
    for basis_value, field in (
        (primary_sidecar_association_basis, "primary_sidecar_association_basis"),
        (composite_unsplit_role_deferral_basis, "composite_unsplit_role_deferral_basis"),
        (promotion_basis, "promotion_basis"),
    ):
        try:
            _human_text(basis_value, field=field)
        except (TypeError, ValueError) as exc:
            raise GeneratedReferenceAssetPromotionError(
                "CONTRACT_FIELD_INVALID", f"{field} is not bounded canonical text"
            ) from exc
    _verify_policy_identity()
    _verify_promotion_retained_policy(maker_action, checker_action)
    _verify_formal_contract_policy(request_values, field="Promotion Request")
    _verify_formal_contract_semantic(
        request_values,
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        field="Promotion Request",
    )
    try:
        _parse_utc(promotion_at, field="promotion_at")
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "TIME_WINDOW_INVALID_OR_EXPIRED", "promotion_at is not canonical UTC seconds"
        ) from exc
    _verify_formal_contract_authority_and_rebuild(
        request_values,
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        field="Promotion Request",
    )


def _verify_upstream_closure(
    closure: GeneratedReferenceAssetPromotionUpstreamClosureInput,
) -> GeneratedReferenceAssetPromotionUpstreamClosureInput:
    if type(closure) is not GeneratedReferenceAssetPromotionUpstreamClosureInput:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "upstream closure has the wrong process type")
    try:
        rebuilt = verify_generated_reference_rights_manifest(
            closure.manifest,
            closure.artifact,
            closure.outcome,
            closure.candidate,
            closure.qualification_request,
            closure.qualification_decision,
            png_bytes=closure.png_bytes,
            qualification_evidence_documents=closure.qualification_evidence_documents,
            qualification_preparer_identity_bytes=closure.qualification_preparer_identity_bytes,
            qualification_preparer_action_bytes=closure.qualification_preparer_action_bytes,
            qualifier_identity_bytes=closure.qualifier_identity_bytes,
            qualifier_action_bytes=closure.qualifier_action_bytes,
            review_evidence_documents=closure.manifest_review_evidence_documents,
            proposed_rights_scope=closure.manifest_proposed_rights_scope,
            maker_identity_bytes=closure.manifest_maker_identity_bytes,
            maker_action_bytes=closure.manifest_maker_action_bytes,
            checker_identity_bytes=closure.manifest_checker_identity_bytes,
            checker_action_bytes=closure.manifest_checker_action_bytes,
            manifest_at=closure.manifest_at,
        )
    except GeneratedReferenceRightsCurrentStatusError:
        raise
    except Exception as exc:
        raise GeneratedReferenceAssetPromotionError(
            "UPSTREAM_CLOSURE_MISMATCH", "complete ADR-042/043/044 Manifest closure failed"
        ) from exc
    if rebuilt != closure.manifest:
        _fail("UPSTREAM_CLOSURE_MISMATCH", "Manifest rebuild differs from supplied Manifest")
    return closure


def _verify_status_closure(
    closure: GeneratedReferenceAssetPromotionStatusClosureInput,
    manifest: CreativeSampleGeneratedReferenceRightsManifestV1,
    *,
    as_of: str,
) -> CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1:
    if type(closure) is not GeneratedReferenceAssetPromotionStatusClosureInput:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "status closure has the wrong process type")
    try:
        expected_subject = build_generated_reference_current_status_subject_closure(manifest)
        if type(closure.subject_closure) is not GeneratedReferenceCurrentStatusSubjectClosureV1:
            _fail("EXACT_INPUT_TYPE_REQUIRED", "status subject closure type mismatch")
        if closure.subject_closure != expected_subject:
            _fail("UPSTREAM_CLOSURE_MISMATCH", "status subject does not bind exact Manifest")
        for supplied, embedded, expected_type, field in (
            (
                closure.request,
                closure.record.request,
                CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
                "status request",
            ),
            (
                closure.instruction,
                closure.record.instruction,
                CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
                "status instruction",
            ),
            (
                closure.decision,
                closure.record.decision,
                CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
                "status decision",
            ),
        ):
            if type(supplied) is not expected_type or supplied != embedded:
                _fail("UPSTREAM_CLOSURE_MISMATCH", f"{field} differs from Evidence Record")
        if closure.record.subject_closure != expected_subject:
            _fail("UPSTREAM_CLOSURE_MISMATCH", "status Record subject closure drifted")
        verified_record = verify_generated_reference_current_status_evidence_record(
            closure.record,
            chain_inputs=closure.chain_inputs,
            status_preparer_identity_bytes=closure.status_preparer_identity_bytes,
            status_preparer_action_bytes=closure.status_preparer_action_bytes,
            status_checker_identity_bytes=closure.status_checker_identity_bytes,
            status_checker_action_bytes=closure.status_checker_action_bytes,
        )
        if verified_record != closure.record:
            _fail("STATUS_REPLAY_FAILED", "status Record rebuild differs")
        process = process_generated_reference_current_status_record_as_of_assessment(
            closure.record,
            manifest,
            closure.chain_inputs,
            as_of=as_of,
        )
        fresh_receipt = process.receipt
        verify_generated_reference_current_status_record_as_of_assessment_receipt(
            fresh_receipt,
            record=closure.record,
            manifest=manifest,
            chain_inputs=closure.chain_inputs,
        )
        if (
            type(closure.receipt)
            is not CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1
            or closure.receipt != fresh_receipt
            or generated_reference_contract_document_bytes(closure.receipt)
            != generated_reference_contract_document_bytes(fresh_receipt)
        ):
            _fail(
                "STATUS_REPLAY_FAILED",
                "supplied historical Receipt differs from same-call complete replay",
            )
        return fresh_receipt
    except GeneratedReferenceAssetPromotionError:
        raise
    except _ADR044_REPLAY_ERRORS:
        raise
    except Exception as exc:
        raise GeneratedReferenceAssetPromotionError(
            "STATUS_REPLAY_FAILED", "complete generated current-status replay failed"
        ) from exc


def _require_common_upstream_primary_binding(
    closure: GeneratedReferenceAssetPromotionUpstreamClosureInput,
    binding: GeneratedReferencePromotionPrimaryAssetBindingV1,
) -> None:
    artifact = closure.artifact
    outcome = closure.outcome
    candidate = closure.candidate
    manifest = closure.manifest
    expected = (
        binding.asset_purpose,
        binding.subject_id,
        binding.asset_version_id,
        binding.content_sha256,
    )
    for name, actual in (
        (
            "Artifact",
            (
                artifact.asset_purpose,
                artifact.subject_id,
                artifact.expected_active_asset_version_id,
                artifact.expected_active_asset_content_sha256,
            ),
        ),
        (
            "Outcome",
            (
                outcome.asset_purpose,
                outcome.subject_id,
                outcome.expected_active_asset_version_id,
                outcome.expected_active_asset_content_sha256,
            ),
        ),
        (
            "Candidate",
            (
                candidate.asset_purpose,
                candidate.subject_id,
                candidate.expected_active_asset_version_id,
                candidate.expected_active_asset_content_sha256,
            ),
        ),
    ):
        if actual != expected:
            _fail(
                "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                f"{name} expected active primary binding differs",
            )
    if (manifest.asset_purpose, manifest.subject_id) != expected[:2]:
        _fail(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "Manifest subject/purpose differs from primary binding",
        )


def _review_payload_projection_from_values(values: Mapping[str, object]) -> dict[str, object]:
    keys = (
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "request_scope",
        "reference_prompt_artifact_sha256",
        "provider_attempt_outcome_id",
        "provider_attempt_outcome_sha256",
        "candidate_id",
        "candidate_sha256",
        "output_ordinal",
        "media_type",
        "media_content_sha256",
        "media_size_bytes",
        "media_technical_record_sha256",
        "qualification_request_id",
        "qualification_request_sha256",
        "qualification_decision_id",
        "qualification_decision_sha256",
        "qualification_decision_at",
        "qualification_valid_until",
        "manifest_id",
        "manifest_sha256",
        "manifest_at",
        "manifest_valid_until",
        "reviewed_rights_scope",
        "status_subject_closure_id",
        "status_subject_closure_sha256",
        "requested_status_record_id",
        "requested_status_record_sha256",
        "requested_status_receipt_id",
        "requested_status_receipt_sha256",
        "requested_explicit_chain_set_sha256",
        "requested_coverage_set_sha256",
        "requested_joint_replay_sha256",
        "requested_as_of_assessment_sha256",
        "requested_as_of",
        "requested_as_of_status",
        "requested_status_valid_until",
        "requested_primary_asset_binding",
        "requested_at",
        "request_valid_until",
        "request_basis",
        "requested_representation",
        "composite_media_unsplit",
        "role_assignment_embedded",
        "bible_mutation_requested",
        "provider_input_requested",
    )
    if any(key not in values for key in keys):
        _fail("CONTRACT_FIELD_INVALID", "review payload construction is incomplete")
    return {key: _explicit_value(values[key]) for key in keys}


def _base_values() -> dict[str, object]:
    return {
        "policy_id": GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_ID,
        "policy_version": GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_VERSION,
        "policy_document_sha256": GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256,
    }


def _request_action_expected(
    *,
    actor_sha: str,
    review_payload_sha: str,
    candidate_sha: str,
    manifest_sha: str,
    receipt_sha: str,
    binding_sha: str,
    requested_at: str,
) -> dict[str, object]:
    return {
        "document_profile": (
            "sdc.generated-reference-asset-promotion-request-preparation-action.v1"
        ),
        "action": "PREPARED_GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST",
        "actor_ref_sha256": actor_sha,
        "promotion_review_payload_sha256": review_payload_sha,
        "candidate_sha256": candidate_sha,
        "manifest_sha256": manifest_sha,
        "requested_status_receipt_sha256": receipt_sha,
        "requested_primary_asset_binding_sha256": binding_sha,
        "policy_document_sha256": GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256,
        "requested_at": requested_at,
    }


def prepare_generated_reference_asset_promotion_request(
    upstream: GeneratedReferenceAssetPromotionUpstreamClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    primary_bible: CharacterBible | SceneBible,
    primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    *,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    requested_at: str,
    request_basis: str,
) -> CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
    """Prepare one immutable Request only after complete request-time replay to CURRENT."""

    _preflight_prepare_inputs(
        upstream,
        request_status,
        primary_bible,
        primary_asset_version,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        requested_at=requested_at,
        request_basis=request_basis,
    )
    try:
        requested_dt = _parse_utc(requested_at, field="requested_at")
        request_basis = _human_text(request_basis, field="request_basis")
        upstream = _verify_upstream_closure(upstream)
        receipt = _verify_status_closure(
            request_status, upstream.manifest, as_of=requested_at
        )
        binding = build_generated_reference_promotion_primary_asset_binding(
            primary_bible, primary_asset_version
        )
        _require_common_upstream_primary_binding(upstream, binding)

        if (
            receipt.as_of != requested_at
            or receipt.as_of_status != "CURRENT"
            or receipt.same_call_assessment_verified is not True
            or receipt.present_currentness_asserted is not False
        ):
            _fail(
                "STATUS_REPLAY_FAILED",
                "request-time same-call Receipt must be CURRENT at exact requested_at",
            )
        if request_status.subject_closure != request_status.record.subject_closure:
            _fail("UPSTREAM_CLOSURE_MISMATCH", "request-time subject closure drifted")
        decision = upstream.qualification_decision
        manifest = upstream.manifest
        if (
            decision.decision != "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW"
            or decision.eligible_for_separate_generated_rights_manifest_review is not True
            or decision.qualification_performed is not True
        ):
            _fail(
                "UPSTREAM_CLOSURE_MISMATCH",
                "Qualification Decision is not the exact positive scoped result",
            )
        qualification_until = _parse_utc(
            decision.qualification_valid_until, field="qualification_valid_until"
        )
        manifest_until = _parse_utc(
            manifest.manifest_valid_until, field="manifest_valid_until"
        )
        status_until = _parse_utc(
            receipt.status_valid_until, field="requested_status_valid_until"
        )
        if not (
            _parse_utc(decision.decision_at, field="qualification_decision_at")
            <= _parse_utc(manifest.manifest_at, field="manifest_at")
            <= requested_dt
            < qualification_until
            and requested_dt < manifest_until
            and requested_dt < status_until
        ):
            _fail(
                "TIME_WINDOW_INVALID_OR_EXPIRED",
                "Request is outside a frozen upstream half-open window",
            )
        request_valid_until = min(
            requested_dt + timedelta(seconds=86_400),
            qualification_until,
            manifest_until,
            status_until,
        )
        if request_valid_until <= requested_dt:
            _fail("TIME_WINDOW_INVALID_OR_EXPIRED", "Request interval is empty")

        _maker_identity, maker_identity_sha = _human_identity(
            maker_identity_bytes, field="Promotion Maker identity"
        )
        base: dict[str, object] = {
            "schema_version": "1.0.0",
            "document_type": (
                "sdc.creative-sample-generated-reference-asset-promotion-request-v1"
            ),
            "request_scope": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_ONLY",
            **_base_values(),
            "reference_prompt_artifact_sha256": upstream.artifact.artifact_sha256,
            "provider_attempt_outcome_id": upstream.outcome.outcome_id,
            "provider_attempt_outcome_sha256": upstream.outcome.outcome_sha256,
            "candidate_id": upstream.candidate.candidate_id,
            "candidate_sha256": upstream.candidate.candidate_sha256,
            "output_ordinal": 0,
            "media_type": "image/png",
            "media_content_sha256": upstream.candidate.media_content_sha256,
            "media_size_bytes": upstream.candidate.media_size_bytes,
            "media_technical_record_sha256": (
                upstream.candidate.media_technical_record_sha256
            ),
            "qualification_request_id": upstream.qualification_request.request_id,
            "qualification_request_sha256": upstream.qualification_request.request_sha256,
            "qualification_decision_id": decision.decision_id,
            "qualification_decision_sha256": decision.decision_sha256,
            "qualification_decision_at": decision.decision_at,
            "qualification_valid_until": decision.qualification_valid_until,
            "manifest_id": manifest.manifest_id,
            "manifest_sha256": manifest.manifest_sha256,
            "manifest_at": manifest.manifest_at,
            "manifest_valid_until": manifest.manifest_valid_until,
            "reviewed_rights_scope": manifest.reviewed_rights_scope,
            "status_subject_closure_id": request_status.subject_closure.closure_id,
            "status_subject_closure_sha256": request_status.subject_closure.closure_sha256,
            "requested_status_record_id": request_status.record.record_id,
            "requested_status_record_sha256": request_status.record.record_sha256,
            "requested_status_receipt_id": receipt.receipt_id,
            "requested_status_receipt_sha256": receipt.receipt_sha256,
            "requested_explicit_chain_set_sha256": receipt.explicit_chain_set_sha256,
            "requested_coverage_set_sha256": receipt.coverage_set_sha256,
            "requested_joint_replay_sha256": receipt.joint_replay_sha256,
            "requested_as_of_assessment_sha256": receipt.as_of_assessment_sha256,
            "requested_as_of": requested_at,
            "requested_as_of_status": "CURRENT",
            "requested_status_valid_until": receipt.status_valid_until,
            "requested_primary_asset_binding": binding,
            "maker_identity_ref_sha256": maker_identity_sha,
            "maker_prepared_at": requested_at,
            "requested_at": requested_at,
            "request_valid_until": _format_utc(request_valid_until),
            "request_basis": request_basis,
            "requested_representation": "TYPED_ELIGIBLE_ASSET_SIDECAR",
            "composite_media_unsplit": True,
            "role_assignment_embedded": False,
            "bible_mutation_requested": False,
            "provider_input_requested": False,
            "promotion_performed": False,
            "sidecar_materialized": False,
            "eligible_for_separate_role_binding_review": False,
            "status": "GENERATED_REFERENCE_ASSET_PROMOTION_REQUESTED",
            "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
            **_zero_authority_values(),
        }
        review_payload = _review_payload_projection_from_values(base)
        review_payload_sha = _semantic_sha256(
            GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
            review_payload,
        )
        action_sha = _exact_action(
            maker_action_bytes,
            _request_action_expected(
                actor_sha=maker_identity_sha,
                review_payload_sha=review_payload_sha,
                candidate_sha=upstream.candidate.candidate_sha256,
                manifest_sha=manifest.manifest_sha256,
                receipt_sha=receipt.receipt_sha256,
                binding_sha=binding.primary_asset_binding_sha256,
                requested_at=requested_at,
            ),
            field="Promotion Maker action",
        )
        existing_digests = _collect_sha256_strings(upstream) | _collect_sha256_strings(
            request_status
        )
        existing_digests.add(maker_identity_sha)
        if action_sha in existing_digests:
            _fail(
                "UPSTREAM_CLOSURE_MISMATCH",
                "Promotion Maker action aliases an upstream or identity digest",
            )
        base["promotion_review_payload_sha256"] = review_payload_sha
        base["maker_action_sha256"] = action_sha
        built = cast(
            CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
            _build_identity(CreativeSampleGeneratedReferenceAssetPromotionRequestV1, base),
        )
        if (
            generated_reference_asset_promotion_review_payload_sha256(built)
            != review_payload_sha
        ):
            _fail("SEMANTIC_ID_OR_DIGEST_MISMATCH", "review payload rebuild mismatch")
        generated_reference_asset_promotion_contract_document_bytes(built)
        return built
    except GeneratedReferenceAssetPromotionError:
        raise
    except _ADR044_REPLAY_ERRORS:
        raise
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", "Promotion Request preparation failed closed"
        ) from exc


def verify_generated_reference_asset_promotion_request(
    request: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
    upstream: GeneratedReferenceAssetPromotionUpstreamClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    primary_bible: CharacterBible | SceneBible,
    primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    *,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    requested_at: str,
    request_basis: str,
) -> CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
    if type(request) is not CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "Promotion Request has the wrong exact type")
    _preflight_prepare_inputs(
        upstream,
        request_status,
        primary_bible,
        primary_asset_version,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        requested_at=requested_at,
        request_basis=request_basis,
    )
    validated = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _exact_model(
            request,
            CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
            field="Promotion Request",
        ),
    )
    rebuilt = prepare_generated_reference_asset_promotion_request(
        upstream,
        request_status,
        primary_bible,
        primary_asset_version,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        requested_at=requested_at,
        request_basis=request_basis,
    )
    if (
        validated != rebuilt
        or generated_reference_asset_promotion_contract_document_bytes(validated)
        != generated_reference_asset_promotion_contract_document_bytes(rebuilt)
    ):
        _fail(
            "UPSTREAM_CLOSURE_MISMATCH",
            "Promotion Request differs from complete retained-byte/replay rebuild",
        )
    return validated


def _observation_occurrence_map(
    closure: GeneratedReferenceAssetPromotionStatusClosureInput,
) -> dict[tuple[str, str, str], bytes]:
    result: dict[tuple[str, str, str], bytes] = {}
    for chain_index, chain_input in enumerate(closure.chain_inputs):
        if type(chain_input) is not GeneratedReferenceCurrentStatusExplicitChainInput:
            _fail(
                "STATUS_REPLAY_FAILED",
                f"chain_inputs[{chain_index}] has the wrong exact process type",
            )
        for item_index, item in enumerate(chain_input.observation_inputs):
            if type(item) is not GeneratedReferenceCurrentStatusObservationInput:
                _fail(
                    "STATUS_REPLAY_FAILED",
                    f"chain_inputs[{chain_index}].observation_inputs[{item_index}] type mismatch",
                )
            canonical = generated_reference_contract_document_bytes(item.observation)
            if type(item.document_bytes) is not bytes or item.document_bytes != canonical:
                _fail("STATUS_REPLAY_FAILED", "Observation bytes differ from exact Contract")
            anchor = (
                item.observation.observation_id,
                item.observation.observation_sha256,
                generated_reference_current_status_chain_sha256(item.observation),
            )
            prior = result.get(anchor)
            if prior is not None and prior != item.document_bytes:
                _fail("STATUS_REPLAY_FAILED", "Observation occurrence anchor aliases bytes")
            result[anchor] = item.document_bytes
    return result


def _target_anchors(
    closure: GeneratedReferenceAssetPromotionStatusClosureInput,
) -> set[tuple[str, str, str]]:
    return {
        (item.observation_id, item.observation_sha256, item.chain_sha256)
        for item in closure.request.observation_refs
    }


def _verify_final_record_monotonicity(
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    final_status: GeneratedReferenceAssetPromotionStatusClosureInput,
) -> None:
    if request_status.subject_closure != final_status.subject_closure:
        _fail(
            "UPSTREAM_CLOSURE_MISMATCH",
            "request-time and final status subjects are not exact-equal",
        )
    prior_occurrences = _observation_occurrence_map(request_status)
    final_occurrences = _observation_occurrence_map(final_status)
    for anchor, prior_bytes in prior_occurrences.items():
        if final_occurrences.get(anchor) != prior_bytes:
            _fail(
                "STATUS_REPLAY_FAILED",
                "final Record omits, substitutes, or rewrites a request-time Observation occurrence",
            )
    final_targets = _target_anchors(final_status)
    predecessor_anchors: dict[
        tuple[str, str, str], set[tuple[str, str, str]]
    ] = {}
    for chain_input in final_status.chain_inputs:
        for observation_input in chain_input.observation_inputs:
            observation = observation_input.observation
            anchor = (
                observation.observation_id,
                observation.observation_sha256,
                generated_reference_current_status_chain_sha256(observation),
            )
            predecessor_anchors[anchor] = {
                (head.observation_id, head.observation_sha256, head.chain_sha256)
                for head in observation.chain_link.predecessor_heads
            }

    complete_final_ancestry = set(final_targets)
    frontier = list(final_targets)
    while frontier:
        current = frontier.pop()
        for predecessor in predecessor_anchors.get(current, set()):
            if predecessor not in complete_final_ancestry:
                complete_final_ancestry.add(predecessor)
                frontier.append(predecessor)
    for prior_target in _target_anchors(request_status):
        if prior_target not in complete_final_ancestry:
            _fail(
                "STATUS_REPLAY_FAILED",
                "request-time target is neither final nor an exact retained ancestor occurrence",
            )
    # The traversal derives only from explicitly supplied frozen predecessor-head anchors.  ADR-044
    # complete replay has already validated every link and target, so no private replay-result
    # member is needed to prove that every prior branch remains final or becomes exact ancestry.


def _decision_action_expected(
    *,
    actor_sha: str,
    request_sha: str,
    receipt_sha: str,
    binding_sha: str,
    promotion_at: str,
    gates: tuple[GeneratedReferencePromotionGateResultV1, ...],
    issues: tuple[str, ...],
    promotion_basis: str,
    decision: str,
    materialization_allowed: bool,
) -> dict[str, object]:
    return {
        "document_profile": "sdc.generated-reference-asset-promotion-decision-action.v1",
        "action": "RECORDED_GENERATED_REFERENCE_ASSET_PROMOTION_DECISION",
        "actor_ref_sha256": actor_sha,
        "request_sha256": request_sha,
        "policy_document_sha256": GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256,
        "promotion_status_receipt_sha256": receipt_sha,
        "promotion_primary_asset_binding_sha256": binding_sha,
        "promotion_at": promotion_at,
        "gate_results": [_gate_projection(item) for item in gates],
        "promotion_issue_codes": list(issues),
        "promotion_basis": promotion_basis,
        "decision": decision,
        "sidecar_materialization_allowed": materialization_allowed,
    }


def _promotion_gates(
    *,
    promotion_status: str,
    binding_matches: bool,
    association_result: GateResult,
    association_basis: str,
    role_deferral_result: GateResult,
    role_deferral_basis: str,
) -> tuple[GeneratedReferencePromotionGateResultV1, ...]:
    status_result: GateResult = cast(
        GateResult,
        {
            "CURRENT": "PASS",
            "EXPIRED": "FAIL",
            "REVOKED": "FAIL",
            "HELD": "FAIL",
            "INDETERMINATE": "INDETERMINATE",
        }[promotion_status],
    )
    results: tuple[GateResult, ...] = (
        "PASS",
        "PASS",
        "PASS",
        "PASS",
        status_result,
        "PASS" if binding_matches else "FAIL",
        "PASS",
        association_result,
        role_deferral_result,
        "PASS",
    )
    bases = (
        _COMPILER_GATE_BASES[0],
        _COMPILER_GATE_BASES[1],
        _COMPILER_GATE_BASES[2],
        _COMPILER_GATE_BASES[3],
        _COMPILER_GATE_BASES[4],
        _COMPILER_GATE_BASES[5],
        _COMPILER_GATE_BASES[6],
        association_basis,
        role_deferral_basis,
        _COMPILER_GATE_BASES[9],
    )
    return tuple(
        GeneratedReferencePromotionGateResultV1.model_validate(
            {
                "ordinal": ordinal,
                "gate": gate,
                "result": results[ordinal],
                "basis": bases[ordinal],
            }
        )
        for ordinal, gate in enumerate(PROMOTION_GATE_ORDER)
    )


def finalize_generated_reference_asset_promotion(
    request: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
    upstream: GeneratedReferenceAssetPromotionUpstreamClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_bible: CharacterBible | SceneBible,
    requested_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    final_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    promotion_primary_bible: CharacterBible | SceneBible,
    promotion_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    *,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    checker_identity_bytes: bytes,
    checker_action_bytes: bytes,
    promotion_at: str,
    primary_sidecar_association_result: GateResult,
    primary_sidecar_association_basis: str,
    composite_unsplit_role_deferral_result: GateResult,
    composite_unsplit_role_deferral_basis: str,
    promotion_basis: str,
) -> GeneratedReferenceAssetPromotionFinalizationResult:
    """Record one Decision and atomically materialize its optional positive Sidecar."""

    _preflight_finalize_inputs(
        request,
        upstream,
        request_status,
        requested_primary_bible,
        requested_primary_asset_version,
        final_status,
        promotion_primary_bible,
        promotion_primary_asset_version,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        checker_identity_bytes=checker_identity_bytes,
        checker_action_bytes=checker_action_bytes,
        promotion_at=promotion_at,
        primary_sidecar_association_result=primary_sidecar_association_result,
        primary_sidecar_association_basis=primary_sidecar_association_basis,
        composite_unsplit_role_deferral_result=composite_unsplit_role_deferral_result,
        composite_unsplit_role_deferral_basis=composite_unsplit_role_deferral_basis,
        promotion_basis=promotion_basis,
    )
    try:
        validated_request = verify_generated_reference_asset_promotion_request(
            request,
            upstream,
            request_status,
            requested_primary_bible,
            requested_primary_asset_version,
            maker_identity_bytes=maker_identity_bytes,
            maker_action_bytes=maker_action_bytes,
            requested_at=request.requested_at,
            request_basis=request.request_basis,
        )
        upstream = _verify_upstream_closure(upstream)
        if type(promotion_at) is not str:
            _fail("EXACT_INPUT_TYPE_REQUIRED", "promotion_at must be an exact string")
        promotion_dt = _parse_utc(promotion_at, field="promotion_at")
        if not (
            _parse_utc(validated_request.requested_at, field="requested_at")
            <= promotion_dt
            < _parse_utc(validated_request.request_valid_until, field="request_valid_until")
        ):
            _fail(
                "TIME_WINDOW_INVALID_OR_EXPIRED",
                "promotion_at is outside the exact half-open Request window",
            )
        final_receipt = _verify_status_closure(
            final_status, upstream.manifest, as_of=promotion_at
        )
        if final_receipt.as_of != promotion_at:
            _fail("STATUS_REPLAY_FAILED", "final Receipt is not at exact promotion_at")
        _verify_final_record_monotonicity(request_status, final_status)
        if (
            final_status.subject_closure.closure_id
            != validated_request.status_subject_closure_id
            or final_status.subject_closure.closure_sha256
            != validated_request.status_subject_closure_sha256
        ):
            _fail("UPSTREAM_CLOSURE_MISMATCH", "final status subject differs from Request")

        promotion_binding = build_generated_reference_promotion_primary_asset_binding(
            promotion_primary_bible, promotion_primary_asset_version
        )
        if (
            promotion_binding.subject_id
            != validated_request.requested_primary_asset_binding.subject_id
            or promotion_binding.asset_purpose
            != validated_request.requested_primary_asset_binding.asset_purpose
        ):
            _fail(
                "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
                "final supplied binding changes Request subject or purpose",
            )
        binding_matches = (
            promotion_binding == validated_request.requested_primary_asset_binding
        )
        if upstream.manifest.reviewed_rights_scope != validated_request.reviewed_rights_scope:
            _fail(
                "UPSTREAM_CLOSURE_MISMATCH",
                "Request reviewed Rights scope differs from exact Manifest",
            )

        allowed_results = {"PASS", "FAIL", "INDETERMINATE"}
        if (
            type(primary_sidecar_association_result) is not str
            or primary_sidecar_association_result not in allowed_results
            or type(composite_unsplit_role_deferral_result) is not str
            or composite_unsplit_role_deferral_result not in allowed_results
        ):
            _fail("CONTRACT_FIELD_INVALID", "human Promotion gate result is invalid")
        association_basis = _human_text(
            primary_sidecar_association_basis,
            field="primary_sidecar_association_basis",
        )
        role_basis = _human_text(
            composite_unsplit_role_deferral_basis,
            field="composite_unsplit_role_deferral_basis",
        )
        promotion_basis = _human_text(promotion_basis, field="promotion_basis")

        maker_identity, maker_identity_sha = _human_identity(
            maker_identity_bytes, field="Promotion Maker identity"
        )
        checker_identity, checker_identity_sha = _human_identity(
            checker_identity_bytes, field="Promotion Checker identity"
        )
        qualifier_identity, _ = _human_identity(
            upstream.qualifier_identity_bytes, field="Qualification Qualifier identity"
        )
        manifest_checker_identity, _ = _human_identity(
            upstream.manifest_checker_identity_bytes, field="Manifest Checker identity"
        )
        request_status_checker_identity, _ = _human_identity(
            request_status.status_checker_identity_bytes,
            field="request-time Status Checker identity",
        )
        final_status_checker_identity, _ = _human_identity(
            final_status.status_checker_identity_bytes,
            field="final Status Checker identity",
        )
        forbidden_checker_identities = {
            maker_identity,
            qualifier_identity,
            manifest_checker_identity,
            request_status_checker_identity,
            final_status_checker_identity,
        }
        if checker_identity in forbidden_checker_identities:
            _fail(
                "ROLE_SEPARATION_VIOLATION",
                "Promotion Checker aliases a frozen independent role",
            )
        if maker_identity_sha != validated_request.maker_identity_ref_sha256:
            _fail("UPSTREAM_CLOSURE_MISMATCH", "Promotion Maker identity bytes drifted")
        if _raw_sha256(maker_action_bytes) != validated_request.maker_action_sha256:
            _fail("UPSTREAM_CLOSURE_MISMATCH", "Promotion Maker action bytes drifted")

        gates = _promotion_gates(
            promotion_status=final_receipt.as_of_status,
            binding_matches=binding_matches,
            association_result=cast(GateResult, primary_sidecar_association_result),
            association_basis=association_basis,
            role_deferral_result=cast(GateResult, composite_unsplit_role_deferral_result),
            role_deferral_basis=role_basis,
        )
        issues = _expected_issues(gates)
        disposition = _decision_from_gates(gates)
        materialization_allowed = disposition == "APPROVE_ELIGIBLE_ASSET_SIDECAR"
        checker_action_sha = _exact_action(
            checker_action_bytes,
            _decision_action_expected(
                actor_sha=checker_identity_sha,
                request_sha=validated_request.request_sha256,
                receipt_sha=final_receipt.receipt_sha256,
                binding_sha=promotion_binding.primary_asset_binding_sha256,
                promotion_at=promotion_at,
                gates=gates,
                issues=issues,
                promotion_basis=promotion_basis,
                decision=disposition,
                materialization_allowed=materialization_allowed,
            ),
            field="Promotion Checker action",
        )
        existing_digests = (
            _collect_sha256_strings(upstream)
            | _collect_sha256_strings(request_status)
            | _collect_sha256_strings(final_status)
            | _collect_sha256_strings(validated_request)
            | {_raw_sha256(maker_identity_bytes), _raw_sha256(maker_action_bytes), checker_identity_sha}
        )
        if checker_action_sha in existing_digests:
            _fail(
                "UPSTREAM_CLOSURE_MISMATCH",
                "Promotion Checker action aliases an upstream, Request, or identity digest",
            )

        decision_values: dict[str, object] = {
            "schema_version": "1.0.0",
            "document_type": (
                "sdc.creative-sample-generated-reference-asset-promotion-decision-v1"
            ),
            "decision_scope": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_ONLY",
            **_base_values(),
            "promotion_review_payload_sha256": (
                validated_request.promotion_review_payload_sha256
            ),
            "request_id": validated_request.request_id,
            "request_sha256": validated_request.request_sha256,
            "reference_prompt_artifact_sha256": (
                validated_request.reference_prompt_artifact_sha256
            ),
            "provider_attempt_outcome_id": validated_request.provider_attempt_outcome_id,
            "provider_attempt_outcome_sha256": (
                validated_request.provider_attempt_outcome_sha256
            ),
            "candidate_id": validated_request.candidate_id,
            "candidate_sha256": validated_request.candidate_sha256,
            "media_content_sha256": validated_request.media_content_sha256,
            "qualification_request_id": validated_request.qualification_request_id,
            "qualification_request_sha256": validated_request.qualification_request_sha256,
            "qualification_decision_id": validated_request.qualification_decision_id,
            "qualification_decision_sha256": validated_request.qualification_decision_sha256,
            "qualification_valid_until": validated_request.qualification_valid_until,
            "manifest_id": validated_request.manifest_id,
            "manifest_sha256": validated_request.manifest_sha256,
            "manifest_valid_until": validated_request.manifest_valid_until,
            "reviewed_rights_scope": validated_request.reviewed_rights_scope,
            "requested_primary_asset_binding": validated_request.requested_primary_asset_binding,
            "promotion_primary_asset_binding": promotion_binding,
            "status_subject_closure_id": validated_request.status_subject_closure_id,
            "status_subject_closure_sha256": validated_request.status_subject_closure_sha256,
            "promotion_status_record_id": final_status.record.record_id,
            "promotion_status_record_sha256": final_status.record.record_sha256,
            "promotion_status_receipt_id": final_receipt.receipt_id,
            "promotion_status_receipt_sha256": final_receipt.receipt_sha256,
            "promotion_explicit_chain_set_sha256": final_receipt.explicit_chain_set_sha256,
            "promotion_coverage_set_sha256": final_receipt.coverage_set_sha256,
            "promotion_joint_replay_sha256": final_receipt.joint_replay_sha256,
            "promotion_as_of_assessment_sha256": final_receipt.as_of_assessment_sha256,
            "promotion_as_of_status": final_receipt.as_of_status,
            "promotion_status_valid_until": final_receipt.status_valid_until,
            "checker_identity_ref_sha256": checker_identity_sha,
            "checker_action_sha256": checker_action_sha,
            "checker_reviewed_at": promotion_at,
            "decision_at": promotion_at,
            "promotion_at": promotion_at,
            "gate_results": gates,
            "promotion_issue_codes": issues,
            "promotion_basis": promotion_basis,
            "decision": disposition,
            "sidecar_materialization_allowed": materialization_allowed,
            "promotion_review_performed": True,
            "sidecar_id_embedded": False,
            "role_assignment_embedded": False,
            "provider_input_eligible": False,
            "status": "GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_RECORDED",
            "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
            **_zero_authority_values(),
        }
        decision_value = cast(
            CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
            _build_identity(
                CreativeSampleGeneratedReferenceAssetPromotionDecisionV1, decision_values
            ),
        )
        generated_reference_asset_promotion_contract_document_bytes(decision_value)

        if not materialization_allowed:
            return GeneratedReferenceAssetPromotionFinalizationResult(
                decision=decision_value, sidecar=None
            )
        if final_receipt.as_of_status != "CURRENT":
            _fail(
                "PROMOTION_GATE_NOT_PASS",
                "a positive Sidecar requires CURRENT at exact promotion_at",
            )
        evidence_until = min(
            _parse_utc(
                validated_request.qualification_valid_until,
                field="qualification_valid_until",
            ),
            _parse_utc(
                validated_request.manifest_valid_until, field="manifest_valid_until"
            ),
            _parse_utc(final_receipt.status_valid_until, field="promotion_status_valid_until"),
        )
        if evidence_until <= promotion_dt:
            _fail(
                "PROMOTION_GATE_NOT_PASS",
                "positive Sidecar evidence horizon is not open at promotion_at",
            )
        sidecar_values: dict[str, object] = {
            "schema_version": "1.0.0",
            "document_type": (
                "sdc.creative-sample-generated-reference-eligible-asset-sidecar-v1"
            ),
            "sidecar_scope": "GENERATED_REFERENCE_POST_PROMOTION_HISTORICAL_EVIDENCE_ONLY",
            **_base_values(),
            "request_id": validated_request.request_id,
            "request_sha256": validated_request.request_sha256,
            "decision_id": decision_value.decision_id,
            "decision_sha256": decision_value.decision_sha256,
            "reference_prompt_artifact_sha256": (
                validated_request.reference_prompt_artifact_sha256
            ),
            "provider_attempt_outcome_id": validated_request.provider_attempt_outcome_id,
            "provider_attempt_outcome_sha256": (
                validated_request.provider_attempt_outcome_sha256
            ),
            "candidate_id": validated_request.candidate_id,
            "candidate_sha256": validated_request.candidate_sha256,
            "output_ordinal": 0,
            "media_type": "image/png",
            "media_content_sha256": validated_request.media_content_sha256,
            "media_size_bytes": validated_request.media_size_bytes,
            "media_technical_record_sha256": (
                validated_request.media_technical_record_sha256
            ),
            "qualification_request_id": validated_request.qualification_request_id,
            "qualification_request_sha256": validated_request.qualification_request_sha256,
            "qualification_decision_id": validated_request.qualification_decision_id,
            "qualification_decision_sha256": validated_request.qualification_decision_sha256,
            "qualification_valid_until": validated_request.qualification_valid_until,
            "manifest_id": validated_request.manifest_id,
            "manifest_sha256": validated_request.manifest_sha256,
            "manifest_valid_until": validated_request.manifest_valid_until,
            "reviewed_rights_scope": validated_request.reviewed_rights_scope,
            "primary_asset_binding": promotion_binding,
            "status_subject_closure_id": validated_request.status_subject_closure_id,
            "status_subject_closure_sha256": validated_request.status_subject_closure_sha256,
            "promotion_status_record_id": final_status.record.record_id,
            "promotion_status_record_sha256": final_status.record.record_sha256,
            "promotion_status_receipt_id": final_receipt.receipt_id,
            "promotion_status_receipt_sha256": final_receipt.receipt_sha256,
            "promotion_explicit_chain_set_sha256": final_receipt.explicit_chain_set_sha256,
            "promotion_coverage_set_sha256": final_receipt.coverage_set_sha256,
            "promotion_joint_replay_sha256": final_receipt.joint_replay_sha256,
            "promotion_as_of_assessment_sha256": final_receipt.as_of_assessment_sha256,
            "promotion_as_of_status": "CURRENT",
            "promotion_at": promotion_at,
            "promotion_status_valid_until": final_receipt.status_valid_until,
            "promotion_evidence_valid_until": _format_utc(evidence_until),
            "origin_claim": "CALLER_ASSERTED_PROVIDER_GENERATED_REFERENCE_MEDIA",
            "origin_assurance": (
                "QUALIFIED_RIGHTS_REVIEWED_AND_CURRENT_ONLY_AT_EXACT_PROMOTION_AT_NOT_PROVIDER_AUTHENTICATED"
            ),
            "sidecar_state": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_RECORDED",
            "promotion_performed": True,
            "eligible_for_separate_role_binding_review": True,
            "primary_asset_binding_replaced": False,
            "bible_active_binding_changed": False,
            "asset_version_v1_created": False,
            "composite_media_unsplit": True,
            "role_assignment_embedded": False,
            "provider_input_eligible": False,
            "present_currentness_asserted": False,
            "perpetual_eligibility_asserted": False,
            "supersedes_sidecar": False,
            "status": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_RECORDED",
            "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
            **_zero_authority_values(),
        }
        sidecar_value = cast(
            CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
            _build_identity(
                CreativeSampleGeneratedReferenceEligibleAssetSidecarV1, sidecar_values
            ),
        )
        generated_reference_asset_promotion_contract_document_bytes(sidecar_value)
        # Both values have now been completely built and revalidated.  Returning happens only here,
        # so no caller can observe a positive Decision without its paired Sidecar from this call.
        return GeneratedReferenceAssetPromotionFinalizationResult(
            decision=decision_value, sidecar=sidecar_value
        )
    except GeneratedReferenceAssetPromotionError:
        raise
    except _ADR044_REPLAY_ERRORS:
        raise
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceAssetPromotionError(
            "CONTRACT_FIELD_INVALID", "Promotion finalization failed closed"
        ) from exc


def verify_generated_reference_asset_promotion_finalization(
    expected: GeneratedReferenceAssetPromotionFinalizationResult,
    request: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
    upstream: GeneratedReferenceAssetPromotionUpstreamClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_bible: CharacterBible | SceneBible,
    requested_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    final_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    promotion_primary_bible: CharacterBible | SceneBible,
    promotion_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    *,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    checker_identity_bytes: bytes,
    checker_action_bytes: bytes,
    promotion_at: str,
    primary_sidecar_association_result: GateResult,
    primary_sidecar_association_basis: str,
    composite_unsplit_role_deferral_result: GateResult,
    composite_unsplit_role_deferral_basis: str,
    promotion_basis: str,
) -> GeneratedReferenceAssetPromotionFinalizationResult:
    """Freshly replay and require exact Decision/optional-Sidecar equality."""

    if type(expected) is not GeneratedReferenceAssetPromotionFinalizationResult:
        _fail("EXACT_INPUT_TYPE_REQUIRED", "expected finalization result type mismatch")
    _validate_finalization_result_invariant(expected)
    _preflight_finalize_inputs(
        request,
        upstream,
        request_status,
        requested_primary_bible,
        requested_primary_asset_version,
        final_status,
        promotion_primary_bible,
        promotion_primary_asset_version,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        checker_identity_bytes=checker_identity_bytes,
        checker_action_bytes=checker_action_bytes,
        promotion_at=promotion_at,
        primary_sidecar_association_result=primary_sidecar_association_result,
        primary_sidecar_association_basis=primary_sidecar_association_basis,
        composite_unsplit_role_deferral_result=composite_unsplit_role_deferral_result,
        composite_unsplit_role_deferral_basis=composite_unsplit_role_deferral_basis,
        promotion_basis=promotion_basis,
    )
    _exact_model(
        expected.decision,
        CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
        field="expected Promotion Decision",
    )
    if expected.sidecar is not None:
        _exact_model(
            expected.sidecar,
            CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
            field="expected Promotion Sidecar",
        )
    rebuilt = finalize_generated_reference_asset_promotion(
        request,
        upstream,
        request_status,
        requested_primary_bible,
        requested_primary_asset_version,
        final_status,
        promotion_primary_bible,
        promotion_primary_asset_version,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        checker_identity_bytes=checker_identity_bytes,
        checker_action_bytes=checker_action_bytes,
        promotion_at=promotion_at,
        primary_sidecar_association_result=primary_sidecar_association_result,
        primary_sidecar_association_basis=primary_sidecar_association_basis,
        composite_unsplit_role_deferral_result=composite_unsplit_role_deferral_result,
        composite_unsplit_role_deferral_basis=composite_unsplit_role_deferral_basis,
        promotion_basis=promotion_basis,
    )
    if expected.decision != rebuilt.decision or (
        generated_reference_asset_promotion_contract_document_bytes(expected.decision)
        != generated_reference_asset_promotion_contract_document_bytes(rebuilt.decision)
    ):
        _fail("UPSTREAM_CLOSURE_MISMATCH", "Promotion Decision differs from fresh rebuild")
    if (expected.sidecar is None) != (rebuilt.sidecar is None):
        _fail(
            "UPSTREAM_CLOSURE_MISMATCH",
            "atomic optional Sidecar presence differs from the fresh finalization",
        )
    if expected.sidecar is not None and rebuilt.sidecar is not None:
        if expected.sidecar != rebuilt.sidecar or (
            generated_reference_asset_promotion_contract_document_bytes(expected.sidecar)
            != generated_reference_asset_promotion_contract_document_bytes(rebuilt.sidecar)
        ):
            _fail("UPSTREAM_CLOSURE_MISMATCH", "Sidecar differs from fresh atomic rebuild")
    return expected


__all__ = [
    "CreativeSampleGeneratedReferenceAssetPromotionDecisionV1",
    "CreativeSampleGeneratedReferenceAssetPromotionRequestV1",
    "CreativeSampleGeneratedReferenceEligibleAssetSidecarV1",
    "GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_SHA256_DOMAIN",
    "GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256",
    "GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_ID",
    "GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_VERSION",
    "GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST_SHA256_DOMAIN",
    "GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN",
    "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_SHA256_DOMAIN",
    "GENERATED_REFERENCE_PRIMARY_ASSET_BINDING_SHA256_DOMAIN",
    "GENERATED_REFERENCE_PRIMARY_ASSET_VERSION_PROJECTION_SHA256_DOMAIN",
    "GeneratedReferenceAssetPromotionError",
    "GeneratedReferenceAssetPromotionErrorCodeV1",
    "GeneratedReferenceAssetPromotionFinalizationResult",
    "GeneratedReferenceAssetPromotionStatusClosureInput",
    "GeneratedReferenceAssetPromotionUpstreamClosureInput",
    "GeneratedReferencePromotionGateResultV1",
    "GeneratedReferencePromotionPrimaryAssetBindingV1",
    "PROMOTION_GATE_ORDER",
    "PROMOTION_ISSUE_CODE_ORDER",
    "build_generated_reference_promotion_primary_asset_binding",
    "creative_sample_generated_reference_asset_promotion_decision_projection",
    "creative_sample_generated_reference_asset_promotion_decision_sha256",
    "creative_sample_generated_reference_asset_promotion_request_projection",
    "creative_sample_generated_reference_asset_promotion_request_sha256",
    "creative_sample_generated_reference_eligible_asset_sidecar_projection",
    "creative_sample_generated_reference_eligible_asset_sidecar_sha256",
    "finalize_generated_reference_asset_promotion",
    "generated_reference_asset_promotion_contract_document_bytes",
    "generated_reference_asset_promotion_policy_projection",
    "generated_reference_asset_promotion_review_payload_projection",
    "generated_reference_asset_promotion_review_payload_sha256",
    "generated_reference_primary_asset_version_projection",
    "generated_reference_primary_asset_version_projection_sha256",
    "generated_reference_promotion_primary_asset_binding_projection",
    "generated_reference_promotion_primary_asset_binding_sha256",
    "prepare_generated_reference_asset_promotion_request",
    "verify_generated_reference_asset_promotion_finalization",
    "verify_generated_reference_asset_promotion_request",
]
