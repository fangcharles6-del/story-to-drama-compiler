"""Deterministic generated-reference eligible-asset role binding.

This module implements only the offline, zero-authority boundary accepted by
SDC-ADR-046.  It performs no Provider, Runtime, Compiler, network, credential,
database, publication, retention, training, or asset-mutation operation.
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
from os import fstat
from pathlib import Path
from stat import FILE_ATTRIBUTE_REPARSE_POINT, S_ISREG
from typing import (
    Annotated,
    ClassVar,
    Literal,
    NoReturn,
    cast,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from sdc.contracts import (
    CharacterAssetVersion,
    CharacterBible,
    SceneAssetVersion,
    SceneBible,
)
from sdc.generated_reference_asset_promotion import (
    CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
    CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
    GeneratedReferenceAssetPromotionError,
    GeneratedReferenceAssetPromotionFinalizationResult,
    GeneratedReferenceAssetPromotionStatusClosureInput,
    GeneratedReferenceAssetPromotionUpstreamClosureInput,
    GeneratedReferencePromotionPrimaryAssetBindingV1,
    build_generated_reference_promotion_primary_asset_binding,
    generated_reference_promotion_primary_asset_binding_sha256,
    verify_generated_reference_asset_promotion_finalization,
)
from sdc.generated_reference_candidate import (
    GeneratedReferenceCandidateError,
    admit_generated_reference_png,
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
    build_generated_reference_current_status_subject_closure,
    generated_reference_contract_document_bytes,
    generated_reference_current_status_chain_sha256,
    process_generated_reference_current_status_record_as_of_assessment,
    verify_generated_reference_current_status_evidence_record,
    verify_generated_reference_current_status_record_as_of_assessment_receipt,
)

GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID = (
    "sdc.generated-reference-eligible-asset-role-binding-policy"
)
GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION = "1.0.0"
GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256 = (
    "fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233"
)

GENERATED_REFERENCE_ROLE_BINDING_TARGET_SHA256_DOMAIN = (
    b"sdc:generated-reference-eligible-asset-role-binding-target:v1\0"
)
GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN = (
    b"sdc:generated-reference-eligible-asset-role-binding-review-payload:v1\0"
)
GENERATED_REFERENCE_ROLE_BINDING_REQUEST_SHA256_DOMAIN = (
    b"sdc:generated-reference-eligible-asset-role-binding-request:v1\0"
)
GENERATED_REFERENCE_ROLE_BINDING_DECISION_SHA256_DOMAIN = (
    b"sdc:generated-reference-eligible-asset-role-binding-decision:v1\0"
)
GENERATED_REFERENCE_ROLE_BINDING_SHA256_DOMAIN = (
    b"sdc:generated-reference-eligible-asset-role-binding:v1\0"
)

_REQUEST_ID_STEM = "generated_reference_eligible_asset_role_binding_request_v1_"
_DECISION_ID_STEM = "generated_reference_eligible_asset_role_binding_decision_v1_"
_BINDING_ID_STEM = "generated_reference_eligible_asset_role_binding_v1_"

_LOWER_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_PORTABLE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_SEMANTIC_VERSION_PATTERN = (
    r"^(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})$"
)
_UTC_SECONDS_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_MAX_FORMAL_DOCUMENT_BYTES = 262_144
_MAX_RETAINED_RECORD_BYTES = 262_144
_MAX_HUMAN_IDENTITY_BYTES = 16_384
_MAX_PNG_BYTES = 67_108_864
_MAX_JSON_DEPTH = 16
_MAX_CONTAINER_ITEMS = 64

LowerSha256 = Annotated[str, Field(pattern=_LOWER_SHA256_PATTERN)]
PortableId = Annotated[str, Field(pattern=_PORTABLE_ID_PATTERN)]
SemanticVersion = Annotated[str, Field(pattern=_SEMANTIC_VERSION_PATTERN)]
HumanBasis = Annotated[str, Field(min_length=1, max_length=1000)]
AssetPurpose = Literal["CHARACTER_REFERENCE_ASSET", "SCENE_REFERENCE_ASSET"]
GateResult = Literal["PASS", "FAIL", "INDETERMINATE"]
BindingStatus = Literal["CURRENT", "EXPIRED", "REVOKED", "HELD", "INDETERMINATE"]
ReferenceRole = Literal[
    "CHARACTER_IDENTITY_SHEET",
    "CHARACTER_POSE_REFERENCE",
    "CHARACTER_EXPRESSION_REFERENCE",
    "SCENE_ESTABLISHING_REFERENCE",
    "SCENE_LIGHTING_REFERENCE",
    "SCENE_MATERIAL_REFERENCE",
    "SCENE_PROP_PLACEMENT_REFERENCE",
]
CharacterReferenceRoles = tuple[
    Literal["CHARACTER_IDENTITY_SHEET"],
    Literal["CHARACTER_POSE_REFERENCE"],
    Literal["CHARACTER_EXPRESSION_REFERENCE"],
]
SceneReferenceRoles = tuple[
    Literal["SCENE_ESTABLISHING_REFERENCE"],
    Literal["SCENE_LIGHTING_REFERENCE"],
    Literal["SCENE_MATERIAL_REFERENCE"],
    Literal["SCENE_PROP_PLACEMENT_REFERENCE"],
]
ReferenceRoles = CharacterReferenceRoles | SceneReferenceRoles

CHARACTER_REFERENCE_ROLE_ORDER: CharacterReferenceRoles = (
    "CHARACTER_IDENTITY_SHEET",
    "CHARACTER_POSE_REFERENCE",
    "CHARACTER_EXPRESSION_REFERENCE",
)
SCENE_REFERENCE_ROLE_ORDER: SceneReferenceRoles = (
    "SCENE_ESTABLISHING_REFERENCE",
    "SCENE_LIGHTING_REFERENCE",
    "SCENE_MATERIAL_REFERENCE",
    "SCENE_PROP_PLACEMENT_REFERENCE",
)

ROLE_BINDING_GATE_ORDER = (
    "EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR",
    "EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
    "POSITIVE_UNEXPIRED_QUALIFICATION",
    "VALID_GENERATED_RIGHTS_MANIFEST",
    "CURRENT_STATUS_AT_ROLE_BINDING",
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT",
    "ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP_EXACT",
    "REVIEWED_RIGHTS_SCOPE_UNCHANGED",
    "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED",
    "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED",
    "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED",
    "ROLE_BINDING_REVIEWER_SEPARATION",
)
ROLE_BINDING_ISSUE_CODE_ORDER = (
    "STATUS_NOT_CURRENT_AT_ROLE_BINDING",
    "PRIMARY_BINDING_NO_LONGER_ACTIVE",
    "EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTATION_NOT_ACKNOWLEDGED",
    "WHOLE_COMPOSITE_ROLE_SUITABILITY_NOT_APPROVED",
    "NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_NOT_ACKNOWLEDGED",
)

GeneratedReferenceRoleBindingErrorCodeV1 = Literal[
    "INPUT_RESOURCE_LIMIT_EXCEEDED",
    "INPUT_DOCUMENT_INVALID",
    "CONTRACT_FIELD_INVALID",
    "POLICY_IDENTITY_MISMATCH",
    "FORMAL_IDENTITY_MISMATCH",
    "UPSTREAM_CLOSURE_MISMATCH",
    "PROMOTION_CLOSURE_INVALID",
    "PNG_ADMISSION_INVALID",
    "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
    "CURRENT_STATUS_REPLAY_INVALID",
    "RIGHTS_SCOPE_MISMATCH",
    "ROLE_SEPARATION_VIOLATION",
    "ACTION_RECORD_INVALID",
    "TIME_OR_VALIDITY_INVALID",
    "AUTHORITY_SURFACE_NONZERO",
    "PROHIBITED_BOUNDARY_CONNECTION",
    "BINDING_GATE_NOT_PASS",
    "ATOMIC_OUTPUT_INVARIANT_VIOLATION",
]

_GENERATED_REFERENCE_ROLE_BINDING_ERROR_PRIORITY: tuple[
    GeneratedReferenceRoleBindingErrorCodeV1, ...
] = (
    "INPUT_RESOURCE_LIMIT_EXCEEDED",
    "INPUT_DOCUMENT_INVALID",
    "CONTRACT_FIELD_INVALID",
    "POLICY_IDENTITY_MISMATCH",
    "FORMAL_IDENTITY_MISMATCH",
    "UPSTREAM_CLOSURE_MISMATCH",
    "PROMOTION_CLOSURE_INVALID",
    "PNG_ADMISSION_INVALID",
    "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
    "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
    "CURRENT_STATUS_REPLAY_INVALID",
    "RIGHTS_SCOPE_MISMATCH",
    "ROLE_SEPARATION_VIOLATION",
    "ACTION_RECORD_INVALID",
    "TIME_OR_VALIDITY_INVALID",
    "AUTHORITY_SURFACE_NONZERO",
    "PROHIBITED_BOUNDARY_CONNECTION",
    "BINDING_GATE_NOT_PASS",
    "ATOMIC_OUTPUT_INVARIANT_VIOLATION",
)


class GeneratedReferenceRoleBindingError(ValueError):
    """Stable ADR-046 umbrella failure."""

    def __init__(
        self, code: GeneratedReferenceRoleBindingErrorCodeV1, message: str
    ) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _fail(code: GeneratedReferenceRoleBindingErrorCodeV1, message: str) -> NoReturn:
    raise GeneratedReferenceRoleBindingError(code, message)


def _invalid(message: str) -> NoReturn:
    raise ValueError(message)


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
        _invalid(f"{field} must be a canonical UTC second")
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


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _invalid(f"duplicate JSON key: {key}")
        result[key] = value
    return result


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
        limit = 128 if depth == 1 else _MAX_CONTAINER_ITEMS
        if len(mapping) > limit:
            _invalid(f"{field} has too many members")
        for key, item in mapping.items():
            _canonical_string(key, field=f"{field} key")
            _validate_json_tree(item, field=f"{field}.{key}", depth=depth + 1)
        return
    _invalid(f"{field} is outside the canonical JSON type set")


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


def _compact_json(value: object) -> bytes:
    _validate_json_tree(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
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


def _semantic_sha256(domain: bytes, projection: object) -> str:
    return hashlib.sha256(domain + _compact_json(projection)).hexdigest()


def _raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
    def model_validate_json(
        cls, json_data: str | bytes | bytearray, **kwargs: object
    ) -> _StrictFrozenModel:
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
        if (
            raw.startswith(b"\xef\xbb\xbf")
            or b"\r" in raw
            or not raw.endswith(b"\n")
            or raw.endswith(b"\n\n")
        ):
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
    authority_scope: Literal[
        "THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY"
    ]
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


class GeneratedReferenceEligibleAssetRoleBindingTargetV1(_StrictFrozenModel):
    target_profile: Literal[
        "sdc.generated-reference-eligible-asset-role-binding-target.v1"
    ]
    target_sha256: LowerSha256
    eligible_asset_sidecar_id: PortableId
    eligible_asset_sidecar_sha256: LowerSha256
    promotion_decision_id: PortableId
    promotion_decision_sha256: LowerSha256
    reference_prompt_artifact_sha256: LowerSha256
    provider_attempt_outcome_id: PortableId
    provider_attempt_outcome_sha256: LowerSha256
    candidate_id: PortableId
    candidate_sha256: LowerSha256
    output_ordinal: Literal[0]
    media_type: Literal["image/png"]
    media_content_sha256: LowerSha256
    media_size_bytes: Annotated[int, Field(ge=1, le=_MAX_PNG_BYTES)]
    media_technical_record_sha256: LowerSha256
    asset_purpose: AssetPurpose
    subject_id: PortableId
    profile_id: PortableId
    profile_version: SemanticVersion
    profile_sha256: LowerSha256
    catalog_version: SemanticVersion
    catalog_sha256: LowerSha256
    reference_asset_types: ReferenceRoles
    selected_reference_role: ReferenceRole
    media_binding_scope: Literal[
        "WHOLE_UNSPLIT_UNTRANSFORMED_COMPOSITE_PNG_OCCURRENCE"
    ]
    binding_exclusivity_asserted: Literal[False]
    complete_role_set_asserted: Literal[False]
    global_role_uniqueness_asserted: Literal[False]
    crop_applied: Literal[False]
    split_applied: Literal[False]
    transform_applied: Literal[False]
    derived_media_created: Literal[False]
    provider_slot_embedded: Literal[False]

    @model_validator(mode="after")
    def _closure(self) -> GeneratedReferenceEligibleAssetRoleBindingTargetV1:
        expected_roles: tuple[str, ...] = (
            CHARACTER_REFERENCE_ROLE_ORDER
            if self.asset_purpose == "CHARACTER_REFERENCE_ASSET"
            else SCENE_REFERENCE_ROLE_ORDER
        )
        if self.reference_asset_types != expected_roles:
            _invalid("reference_asset_types is not the exact purpose-derived role tuple")
        if self.selected_reference_role not in expected_roles:
            _invalid("selected_reference_role crosses purpose or is not a Profile member")
        expected_sha = _semantic_sha256(
            GENERATED_REFERENCE_ROLE_BINDING_TARGET_SHA256_DOMAIN,
            _target_projection_unchecked(self),
        )
        if self.target_sha256 != expected_sha:
            _invalid("Role-Binding target digest mismatch")
        return self


class GeneratedReferenceRoleBindingGateResultV1(_StrictFrozenModel):
    ordinal: Annotated[int, Field(ge=0, le=11)]
    gate: Literal[
        "EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR",
        "EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
        "POSITIVE_UNEXPIRED_QUALIFICATION",
        "VALID_GENERATED_RIGHTS_MANIFEST",
        "CURRENT_STATUS_AT_ROLE_BINDING",
        "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT",
        "ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP_EXACT",
        "REVIEWED_RIGHTS_SCOPE_UNCHANGED",
        "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED",
        "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED",
        "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED",
        "ROLE_BINDING_REVIEWER_SEPARATION",
    ]
    result: GateResult
    basis: HumanBasis

    @field_validator("basis")
    @classmethod
    def _basis(cls, value: str) -> str:
        return _human_text(value, field="basis")

    @model_validator(mode="after")
    def _canonical_gate(self) -> GeneratedReferenceRoleBindingGateResultV1:
        if self.gate != ROLE_BINDING_GATE_ORDER[self.ordinal]:
            _invalid("Role-Binding gate ordinal/order mismatch")
        return self


class CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1(
    _ZeroAuthorityModel
):
    schema_version: Literal["1.0.0"]
    document_type: Literal[
        "sdc.creative-sample-generated-reference-eligible-asset-role-binding-request-v1"
    ]
    request_scope: Literal[
        "GENERATED_REFERENCE_ELIGIBLE_ASSET_SINGLE_ROLE_BINDING_ONLY"
    ]
    request_id: PortableId
    request_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-eligible-asset-role-binding-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233"
    ]
    role_binding_review_payload_sha256: LowerSha256
    requested_role_binding_target: GeneratedReferenceEligibleAssetRoleBindingTargetV1
    promotion_request_id: PortableId
    promotion_request_sha256: LowerSha256
    promotion_decision_id: PortableId
    promotion_decision_sha256: LowerSha256
    eligible_asset_sidecar_id: PortableId
    eligible_asset_sidecar_sha256: LowerSha256
    promotion_at: str
    promotion_evidence_valid_until: str
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
    maker_identity_ref_sha256: LowerSha256
    maker_action_sha256: LowerSha256
    maker_prepared_at: str
    requested_at: str
    request_valid_until: str
    request_basis: HumanBasis
    media_binding_scope: Literal[
        "WHOLE_UNSPLIT_UNTRANSFORMED_COMPOSITE_PNG_OCCURRENCE"
    ]
    explicit_human_role_selection: Literal[True]
    profile_role_membership_verified: Literal[True]
    role_binding_exclusivity_asserted: Literal[False]
    complete_role_set_asserted: Literal[False]
    global_role_uniqueness_asserted: Literal[False]
    crop_requested: Literal[False]
    split_requested: Literal[False]
    transform_requested: Literal[False]
    derived_media_requested: Literal[False]
    provider_input_requested: Literal[False]
    role_binding_performed: Literal[False]
    binding_materialized: Literal[False]
    provider_input_eligible: Literal[False]
    status: Literal[
        "GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_REQUESTED"
    ]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    _times = field_validator(
        "promotion_at",
        "promotion_evidence_valid_until",
        "qualification_valid_until",
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
    def _closure(self) -> CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1:
        _validate_request_contract(self)
        return self


BindingIssueCode = Literal[
    "STATUS_NOT_CURRENT_AT_ROLE_BINDING",
    "PRIMARY_BINDING_NO_LONGER_ACTIVE",
    "EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTATION_NOT_ACKNOWLEDGED",
    "WHOLE_COMPOSITE_ROLE_SUITABILITY_NOT_APPROVED",
    "NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_NOT_ACKNOWLEDGED",
]
BindingDecision = Literal[
    "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
    "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
    "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING",
]


class CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1(
    _ZeroAuthorityModel
):
    schema_version: Literal["1.0.0"]
    document_type: Literal[
        "sdc.creative-sample-generated-reference-eligible-asset-role-binding-decision-v1"
    ]
    decision_scope: Literal[
        "GENERATED_REFERENCE_ELIGIBLE_ASSET_SINGLE_ROLE_BINDING_ONLY"
    ]
    decision_id: PortableId
    decision_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-eligible-asset-role-binding-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233"
    ]
    role_binding_review_payload_sha256: LowerSha256
    request_id: PortableId
    request_sha256: LowerSha256
    requested_role_binding_target: GeneratedReferenceEligibleAssetRoleBindingTargetV1
    promotion_request_id: PortableId
    promotion_request_sha256: LowerSha256
    promotion_decision_id: PortableId
    promotion_decision_sha256: LowerSha256
    eligible_asset_sidecar_id: PortableId
    eligible_asset_sidecar_sha256: LowerSha256
    promotion_at: str
    promotion_evidence_valid_until: str
    qualification_decision_id: PortableId
    qualification_decision_sha256: LowerSha256
    qualification_valid_until: str
    manifest_id: PortableId
    manifest_sha256: LowerSha256
    manifest_valid_until: str
    reviewed_rights_scope: GeneratedReferenceReviewedRightsScopeV1
    requested_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
    binding_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
    status_subject_closure_id: PortableId
    status_subject_closure_sha256: LowerSha256
    binding_status_record_id: PortableId
    binding_status_record_sha256: LowerSha256
    binding_status_receipt_id: PortableId
    binding_status_receipt_sha256: LowerSha256
    binding_explicit_chain_set_sha256: LowerSha256
    binding_coverage_set_sha256: LowerSha256
    binding_joint_replay_sha256: LowerSha256
    binding_as_of_assessment_sha256: LowerSha256
    binding_as_of_status: BindingStatus
    binding_status_valid_until: str
    checker_identity_ref_sha256: LowerSha256
    checker_action_sha256: LowerSha256
    checker_reviewed_at: str
    decision_at: str
    binding_at: str
    gate_results: Annotated[
        tuple[GeneratedReferenceRoleBindingGateResultV1, ...],
        Field(min_length=12, max_length=12),
    ]
    binding_issue_codes: Annotated[tuple[BindingIssueCode, ...], Field(max_length=5)]
    decision_basis: HumanBasis
    decision: BindingDecision
    binding_materialization_allowed: bool
    role_binding_review_performed: Literal[True]
    binding_id_embedded: Literal[False]
    role_binding_exclusivity_asserted: Literal[False]
    complete_role_set_asserted: Literal[False]
    global_role_uniqueness_asserted: Literal[False]
    crop_applied: Literal[False]
    split_applied: Literal[False]
    transform_applied: Literal[False]
    derived_media_created: Literal[False]
    provider_input_eligible: Literal[False]
    status: Literal[
        "GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_DECISION_RECORDED"
    ]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    _times = field_validator(
        "promotion_at",
        "promotion_evidence_valid_until",
        "qualification_valid_until",
        "manifest_valid_until",
        "binding_status_valid_until",
        "checker_reviewed_at",
        "decision_at",
        "binding_at",
    )(_utc_seconds)

    @field_validator("decision_basis")
    @classmethod
    def _basis(cls, value: str) -> str:
        return _human_text(value, field="decision_basis")

    @model_validator(mode="after")
    def _closure(self) -> CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1:
        _validate_decision_contract(self)
        return self


class CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1(_ZeroAuthorityModel):
    schema_version: Literal["1.0.0"]
    document_type: Literal[
        "sdc.creative-sample-generated-reference-eligible-asset-role-binding-v1"
    ]
    binding_scope: Literal[
        "POST_PROMOTION_SINGLE_ROLE_BINDING_HISTORICAL_EVIDENCE_ONLY"
    ]
    binding_id: PortableId
    binding_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-eligible-asset-role-binding-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233"
    ]
    request_id: PortableId
    request_sha256: LowerSha256
    decision_id: PortableId
    decision_sha256: LowerSha256
    role_binding_target: GeneratedReferenceEligibleAssetRoleBindingTargetV1
    promotion_request_id: PortableId
    promotion_request_sha256: LowerSha256
    promotion_decision_id: PortableId
    promotion_decision_sha256: LowerSha256
    eligible_asset_sidecar_id: PortableId
    eligible_asset_sidecar_sha256: LowerSha256
    promotion_at: str
    promotion_evidence_valid_until: str
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
    binding_status_record_id: PortableId
    binding_status_record_sha256: LowerSha256
    binding_status_receipt_id: PortableId
    binding_status_receipt_sha256: LowerSha256
    binding_explicit_chain_set_sha256: LowerSha256
    binding_coverage_set_sha256: LowerSha256
    binding_joint_replay_sha256: LowerSha256
    binding_as_of_assessment_sha256: LowerSha256
    binding_as_of_status: Literal["CURRENT"]
    binding_at: str
    binding_status_valid_until: str
    binding_evidence_valid_until: str
    binding_state: Literal[
        "GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_RECORDED"
    ]
    role_binding_performed: Literal[True]
    provider_input_eligible: Literal[False]
    present_currentness_asserted: Literal[False]
    perpetual_role_suitability_asserted: Literal[False]
    role_binding_exclusivity_asserted: Literal[False]
    complete_role_set_asserted: Literal[False]
    global_role_uniqueness_asserted: Literal[False]
    current_role_binding_asserted: Literal[False]
    supersedes_role_binding: Literal[False]
    primary_asset_binding_replaced: Literal[False]
    bible_active_binding_changed: Literal[False]
    asset_version_v1_created: Literal[False]
    whole_composite_media_bound: Literal[True]
    crop_applied: Literal[False]
    split_applied: Literal[False]
    transform_applied: Literal[False]
    derived_media_created: Literal[False]
    provider_slot_embedded: Literal[False]
    status: Literal[
        "GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_RECORDED"
    ]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    _times = field_validator(
        "promotion_at",
        "promotion_evidence_valid_until",
        "qualification_valid_until",
        "manifest_valid_until",
        "binding_at",
        "binding_status_valid_until",
        "binding_evidence_valid_until",
    )(_utc_seconds)

    @model_validator(mode="after")
    def _closure(self) -> CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1:
        _validate_binding_contract(self)
        return self


_POLICY_JSON = r'''{
  "binding_cardinality_rule": "ONE_EXACT_SIDECAR_OCCURRENCE_TO_ONE_ROLE_PER_DOCUMENT_NON_EXCLUSIVE",
  "binding_request_max_age_seconds": 86400,
  "binding_scope": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SINGLE_ROLE_BINDING_ONLY",
  "canonical_codec": "ADR_040_PERSISTENT_AND_COMPACT_CANONICAL_JSON",
  "catalog_rule": "COPY_EXACT_ARTIFACT_SNAPSHOT_IDENTITY_NO_HISTORICAL_CATALOG_READMISSION_CLAIM",
  "checker_action_rule": "FULL_GATE_ISSUE_DECISION_AND_MATERIALIZATION_VALUES_EXACTLY_COPIED_TO_FORMAL_DECISION",
  "cross_document_linkage_rule": "ALL_SHARED_REQUEST_DECISION_AND_POSITIVE_BINDING_FIELDS_EXACTLY_EQUAL_UNDER_CLOSED_MATRIX",
  "decision_mapping": {
    "all_pass": "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
    "any_fail": "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
    "otherwise": "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING"
  },
  "file_admission_layer_rule": "SAFE_BOUNDED_PATH_IO_ADAPTER_THEN_NO_IO_PURE_CONSTRUCTION_CORE",
  "final_record_prior_target_anchor": "OBSERVATION_ID_PLUS_OBSERVATION_SHA256_PLUS_CHAIN_SHA256_ORDINAL_EXCLUDED",
  "final_record_prior_target_coverage_rule": "EACH_PRIOR_TARGET_REMAINS_FINAL_TARGET_OR_IS_COMPLETE_ANCESTOR_OF_FINAL_SUCCESSOR_OR_RECONCILIATION_TARGET_WITH_EVERY_PRIOR_BRANCH_COVERED",
  "final_record_rule": "SAME_OR_NEW_COMPLETE_RECORD_SAME_STATUS_SUBJECT_MONOTONIC_OCCURRENCE_AND_BRANCH_CLOSURE_NO_DISCOVERY",
  "gate_order": [
    "EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR",
    "EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
    "POSITIVE_UNEXPIRED_QUALIFICATION",
    "VALID_GENERATED_RIGHTS_MANIFEST",
    "CURRENT_STATUS_AT_ROLE_BINDING",
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT",
    "ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP_EXACT",
    "REVIEWED_RIGHTS_SCOPE_UNCHANGED",
    "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED",
    "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED",
    "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED",
    "ROLE_BINDING_REVIEWER_SEPARATION"
  ],
  "gate_source_result_mapping": {
    "CURRENT_STATUS_AT_ROLE_BINDING": {
      "basis": "COMPILER_REPLAYED_GENERATED_CURRENT_STATUS_AT_ROLE_BINDING",
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
    "EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR": {
      "basis": "COMPILER_REVALIDATED_EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED": {
      "allowed_results": ["PASS", "FAIL", "INDETERMINATE"],
      "basis": "BOUNDED_CHECKER_TEXT",
      "source": "CHECKER_ACTION"
    },
    "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED": {
      "allowed_results": ["PASS", "FAIL", "INDETERMINATE"],
      "basis": "BOUNDED_CHECKER_TEXT",
      "source": "CHECKER_ACTION"
    },
    "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED": {
      "allowed_results": ["PASS", "FAIL", "INDETERMINATE"],
      "basis": "BOUNDED_CHECKER_TEXT",
      "source": "CHECKER_ACTION"
    },
    "POSITIVE_UNEXPIRED_QUALIFICATION": {
      "basis": "COMPILER_REVALIDATED_POSITIVE_UNEXPIRED_QUALIFICATION",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "REVIEWED_RIGHTS_SCOPE_UNCHANGED": {
      "basis": "COMPILER_REVALIDATED_EXACT_MANIFEST_REVIEWED_RIGHTS_SCOPE",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "ROLE_BINDING_REVIEWER_SEPARATION": {
      "basis": "COMPILER_REVALIDATED_ROLE_BINDING_REVIEWER_SEPARATION",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP_EXACT": {
      "basis": "COMPILER_REVALIDATED_ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT": {
      "basis": "COMPILER_REVALIDATED_FINAL_SUPPLIED_PRIMARY_ASSET_BINDING",
      "result_mapping": {
        "DIFFERENT_ACTIVE_BINDING": "FAIL",
        "EXACT_MATCH": "PASS"
      },
      "source": "COMPILER_DERIVED"
    },
    "VALID_GENERATED_RIGHTS_MANIFEST": {
      "basis": "COMPILER_REVALIDATED_VALID_GENERATED_RIGHTS_MANIFEST",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    }
  },
  "human_gate_order": [
    "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED",
    "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED",
    "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED"
  ],
  "issue_code_order": [
    "STATUS_NOT_CURRENT_AT_ROLE_BINDING",
    "PRIMARY_BINDING_NO_LONGER_ACTIVE",
    "EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTATION_NOT_ACKNOWLEDGED",
    "WHOLE_COMPOSITE_ROLE_SUITABILITY_NOT_APPROVED",
    "NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_NOT_ACKNOWLEDGED"
  ],
  "idempotency_rule": "IDENTICAL_EXPLICIT_INPUTS_ACTION_BYTES_AND_TIMES_PRODUCE_IDENTICAL_VALUES_NO_EXTERNAL_KEY",
  "issue_mapping": {
    "CURRENT_STATUS_AT_ROLE_BINDING": "STATUS_NOT_CURRENT_AT_ROLE_BINDING",
    "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED": "EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTATION_NOT_ACKNOWLEDGED",
    "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED": "NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_NOT_ACKNOWLEDGED",
    "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED": "WHOLE_COMPOSITE_ROLE_SUITABILITY_NOT_APPROVED",
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT": "PRIMARY_BINDING_NO_LONGER_ACTIVE"
  },
  "maker_action_linkage_rule": "REQUEST_MAKER_IDENTITY_ACTION_PAYLOAD_TARGET_ROLE_PRIMARY_STATUS_TIME_AND_BASIS_FIELDS_ALL_EXACTLY_EQUAL",
  "media_rule": "EXACT_WHOLE_UNSPLIT_UNTRANSFORMED_CANDIDATE_PNG_OCCURRENCE_ONLY",
  "multi_binding_rule": "ATOMIC_BINDING_IS_NON_EXCLUSIVE_AND_MAKES_NO_GLOBAL_UNIQUENESS_OR_COMPLETE_SET_CLAIM",
  "policy_id": "sdc.generated-reference-eligible-asset-role-binding-policy",
  "policy_version": "1.0.0",
  "positive_binding_atomicity_rule": "POSITIVE_DECISION_AND_BINDING_SAME_PURE_CALL_NO_PARTIAL_OUTPUT",
  "primary_binding_rule": "REQUEST_BINDING_MUST_EQUAL_SIDECAR_FINAL_BINDING_REBUILT_AND_COMPARED_DIFFERENCE_IS_FAIL_NO_MUTATION",
  "provider_input_rule": "NO_INPUT_MATERIAL_PROVIDER_SLOT_EXECUTABLE_ROUTE_REQUEST_ELIGIBILITY_OR_ROUTING_CLAIM",
  "request_deadline_rule": "MIN_REQUESTED_AT_PLUS_86400_QUALIFICATION_MANIFEST_AND_REQUEST_STATUS_EXCLUSIVE",
  "request_record_prior_promotion_target_anchor": "OBSERVATION_ID_PLUS_OBSERVATION_SHA256_PLUS_CHAIN_SHA256_ORDINAL_EXCLUDED",
  "request_record_prior_promotion_target_coverage_rule": "EACH_PROMOTION_FINAL_TARGET_REMAINS_REQUEST_TARGET_OR_IS_COMPLETE_ANCESTOR_OF_REQUEST_SUCCESSOR_OR_RECONCILIATION_TARGET_WITH_EVERY_PROMOTION_BRANCH_COVERED",
  "request_record_rule": "SAME_AS_PROMOTION_FINAL_OR_NEW_COMPLETE_RECORD_SAME_STATUS_SUBJECT_MONOTONIC_OCCURRENCE_AND_BRANCH_CLOSURE_NO_DISCOVERY",
  "request_status_rule": "FRESH_JOINT_REPLAY_CURRENT_AT_REQUESTED_AS_OF_EQUALS_REQUESTED_AT",
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
    "retained_record_min_bytes": 1,
    "roles_per_binding": 1
  },
  "reviewer_rule": {
    "role_binding_checker_must_differ_from": [
      "ROLE_BINDING_MAKER",
      "QUALIFICATION_QUALIFIER",
      "MANIFEST_CHECKER",
      "PROMOTION_REQUEST_STATUS_CHECKER",
      "PROMOTION_FINAL_STATUS_CHECKER",
      "PROMOTION_CHECKER",
      "ROLE_BINDING_REQUEST_STATUS_CHECKER",
      "ROLE_BINDING_FINAL_STATUS_CHECKER"
    ],
    "role_binding_maker_future_role_auto_expansion": false,
    "role_binding_maker_no_required_separation_from": [
      "QUALIFICATION_REQUEST_PREPARER",
      "QUALIFICATION_QUALIFIER",
      "MANIFEST_MAKER",
      "MANIFEST_CHECKER",
      "PROMOTION_REQUEST_STATUS_PREPARER",
      "PROMOTION_REQUEST_STATUS_CHECKER",
      "PROMOTION_FINAL_STATUS_PREPARER",
      "PROMOTION_FINAL_STATUS_CHECKER",
      "PROMOTION_MAKER",
      "PROMOTION_CHECKER",
      "ROLE_BINDING_REQUEST_STATUS_PREPARER",
      "ROLE_BINDING_REQUEST_STATUS_CHECKER",
      "ROLE_BINDING_FINAL_STATUS_PREPARER",
      "ROLE_BINDING_FINAL_STATUS_CHECKER"
    ],
    "retained_identity_claim": "RECORD_SEPARATION_ONLY_NOT_IDENTITY_AUTHENTICATION"
  },
  "rights_scope_rule": "EXACT_SCOPE_NO_CHANGE_HUMAN_ACKNOWLEDGES_JOINT_PRESENTATION_WITHOUT_EXPANSION_NOT_ROLE_WITHIN_SCOPE_OR_RIGHTS_GRANT",
  "role_order": {
    "CHARACTER_REFERENCE_ASSET": [
      "CHARACTER_IDENTITY_SHEET",
      "CHARACTER_POSE_REFERENCE",
      "CHARACTER_EXPRESSION_REFERENCE"
    ],
    "SCENE_REFERENCE_ASSET": [
      "SCENE_ESTABLISHING_REFERENCE",
      "SCENE_LIGHTING_REFERENCE",
      "SCENE_MATERIAL_REFERENCE",
      "SCENE_PROP_PLACEMENT_REFERENCE"
    ]
  },
  "role_source_rule": "EXPLICIT_HUMAN_MAKER_SELECTION_COMPILER_VALIDATES_PURPOSE_AND_PROFILE_MEMBERSHIP_NO_PIXEL_INFERENCE",
  "sidecar_horizon_rule": "PROMOTION_EVIDENCE_VALID_UNTIL_IS_HISTORICAL_TRACEABILITY_ONLY_NOT_A_ROLE_BINDING_DEADLINE",
  "status_subject_chain_rule": "PROMOTION_FINAL_REQUEST_AND_BINDING_FINAL_RECORDS_SHARE_EXACT_CANDIDATE_QUALIFICATION_MANIFEST_SUBJECT_PURPOSE_AND_POLICY",
  "status_rule": "FRESH_JOINT_REPLAY_AT_EXACT_BINDING_AT_CURRENT_REQUIRED_ONLY_FOR_POSITIVE",
  "supersession_rule": "NO_SUPERSESSION_CURRENT_LATEST_BEST_OR_GLOBAL_UNIQUENESS_SELECTION_IN_V1",
  "time_rule": "REQUEST_RECEIPT_AS_OF_EQUALS_REQUESTED_AS_OF_EQUALS_REQUESTED_AT_EQUALS_MAKER_PREPARED_AT_AND_DECISION_AT_EQUALS_CHECKER_REVIEWED_AT_EQUALS_BINDING_AT_EQUALS_FINAL_RECEIPT_AS_OF",
  "zero_authority_rule": "ALL_PROVIDER_RUNTIME_ASSET_USE_PUBLICATION_RETENTION_TRAINING_AUTHORITY_FALSE_OR_ZERO"
}'''

_ROLE_BINDING_POLICY = cast(dict[str, object], json.loads(_POLICY_JSON))


def _verify_policy_identity() -> None:
    try:
        encoded = _compact_json(_ROLE_BINDING_POLICY)
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "POLICY_IDENTITY_MISMATCH", "Role-Binding policy is not canonical"
        ) from exc
    if (
        _ROLE_BINDING_POLICY.get("policy_id")
        != GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID
        or _ROLE_BINDING_POLICY.get("policy_version")
        != GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION
        or len(encoded) != 9_046
        or _raw_sha256(encoded)
        != GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256
    ):
        _fail("POLICY_IDENTITY_MISMATCH", "Role-Binding policy identity drifted")


def generated_reference_role_binding_policy_projection() -> dict[str, object]:
    """Return an isolated copy of the accepted 9,046-byte policy projection."""

    _verify_policy_identity()
    return cast(dict[str, object], json.loads(_compact_json(_ROLE_BINDING_POLICY)))


_TARGET_PROJECTION_FIELDS = (
    "target_profile",
    "eligible_asset_sidecar_id",
    "eligible_asset_sidecar_sha256",
    "promotion_decision_id",
    "promotion_decision_sha256",
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
    "asset_purpose",
    "subject_id",
    "profile_id",
    "profile_version",
    "profile_sha256",
    "catalog_version",
    "catalog_sha256",
    "reference_asset_types",
    "selected_reference_role",
    "media_binding_scope",
    "binding_exclusivity_asserted",
    "complete_role_set_asserted",
    "global_role_uniqueness_asserted",
    "crop_applied",
    "split_applied",
    "transform_applied",
    "derived_media_created",
    "provider_slot_embedded",
)

_REVIEW_PAYLOAD_FIELDS = (
    "policy_id",
    "policy_version",
    "policy_document_sha256",
    "requested_role_binding_target",
    "promotion_request_id",
    "promotion_request_sha256",
    "promotion_decision_id",
    "promotion_decision_sha256",
    "eligible_asset_sidecar_id",
    "eligible_asset_sidecar_sha256",
    "promotion_at",
    "promotion_evidence_valid_until",
    "qualification_request_id",
    "qualification_request_sha256",
    "qualification_decision_id",
    "qualification_decision_sha256",
    "qualification_valid_until",
    "manifest_id",
    "manifest_sha256",
    "manifest_valid_until",
    "reviewed_rights_scope",
    "requested_primary_asset_binding",
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
    "requested_at",
    "request_valid_until",
    "media_binding_scope",
    "explicit_human_role_selection",
    "profile_role_membership_verified",
    "role_binding_exclusivity_asserted",
    "complete_role_set_asserted",
    "global_role_uniqueness_asserted",
    "crop_requested",
    "split_requested",
    "transform_requested",
    "derived_media_requested",
    "provider_input_requested",
    *_ZERO_AUTHORITY_VALUES,
)

_REQUEST_PROJECTION_FIELDS = (
    "schema_version",
    "document_type",
    "request_scope",
    "policy_id",
    "policy_version",
    "policy_document_sha256",
    "role_binding_review_payload_sha256",
    "requested_role_binding_target",
    "promotion_request_id",
    "promotion_request_sha256",
    "promotion_decision_id",
    "promotion_decision_sha256",
    "eligible_asset_sidecar_id",
    "eligible_asset_sidecar_sha256",
    "promotion_at",
    "promotion_evidence_valid_until",
    "qualification_request_id",
    "qualification_request_sha256",
    "qualification_decision_id",
    "qualification_decision_sha256",
    "qualification_valid_until",
    "manifest_id",
    "manifest_sha256",
    "manifest_valid_until",
    "reviewed_rights_scope",
    "requested_primary_asset_binding",
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
    "maker_identity_ref_sha256",
    "maker_action_sha256",
    "maker_prepared_at",
    "requested_at",
    "request_valid_until",
    "request_basis",
    "media_binding_scope",
    "explicit_human_role_selection",
    "profile_role_membership_verified",
    "role_binding_exclusivity_asserted",
    "complete_role_set_asserted",
    "global_role_uniqueness_asserted",
    "crop_requested",
    "split_requested",
    "transform_requested",
    "derived_media_requested",
    "provider_input_requested",
    "role_binding_performed",
    "binding_materialized",
    "provider_input_eligible",
    "status",
    "evidence_scope",
    *_ZERO_AUTHORITY_VALUES,
)

_DECISION_PROJECTION_FIELDS = (
    "schema_version",
    "document_type",
    "decision_scope",
    "policy_id",
    "policy_version",
    "policy_document_sha256",
    "role_binding_review_payload_sha256",
    "request_id",
    "request_sha256",
    "requested_role_binding_target",
    "promotion_request_id",
    "promotion_request_sha256",
    "promotion_decision_id",
    "promotion_decision_sha256",
    "eligible_asset_sidecar_id",
    "eligible_asset_sidecar_sha256",
    "promotion_at",
    "promotion_evidence_valid_until",
    "qualification_decision_id",
    "qualification_decision_sha256",
    "qualification_valid_until",
    "manifest_id",
    "manifest_sha256",
    "manifest_valid_until",
    "reviewed_rights_scope",
    "requested_primary_asset_binding",
    "binding_primary_asset_binding",
    "status_subject_closure_id",
    "status_subject_closure_sha256",
    "binding_status_record_id",
    "binding_status_record_sha256",
    "binding_status_receipt_id",
    "binding_status_receipt_sha256",
    "binding_explicit_chain_set_sha256",
    "binding_coverage_set_sha256",
    "binding_joint_replay_sha256",
    "binding_as_of_assessment_sha256",
    "binding_as_of_status",
    "binding_status_valid_until",
    "checker_identity_ref_sha256",
    "checker_action_sha256",
    "checker_reviewed_at",
    "decision_at",
    "binding_at",
    "gate_results",
    "binding_issue_codes",
    "decision_basis",
    "decision",
    "binding_materialization_allowed",
    "role_binding_review_performed",
    "binding_id_embedded",
    "role_binding_exclusivity_asserted",
    "complete_role_set_asserted",
    "global_role_uniqueness_asserted",
    "crop_applied",
    "split_applied",
    "transform_applied",
    "derived_media_created",
    "provider_input_eligible",
    "status",
    "evidence_scope",
    *_ZERO_AUTHORITY_VALUES,
)

_BINDING_PROJECTION_FIELDS = (
    "schema_version",
    "document_type",
    "binding_scope",
    "policy_id",
    "policy_version",
    "policy_document_sha256",
    "request_id",
    "request_sha256",
    "decision_id",
    "decision_sha256",
    "role_binding_target",
    "promotion_request_id",
    "promotion_request_sha256",
    "promotion_decision_id",
    "promotion_decision_sha256",
    "eligible_asset_sidecar_id",
    "eligible_asset_sidecar_sha256",
    "promotion_at",
    "promotion_evidence_valid_until",
    "qualification_decision_id",
    "qualification_decision_sha256",
    "qualification_valid_until",
    "manifest_id",
    "manifest_sha256",
    "manifest_valid_until",
    "reviewed_rights_scope",
    "primary_asset_binding",
    "status_subject_closure_id",
    "status_subject_closure_sha256",
    "binding_status_record_id",
    "binding_status_record_sha256",
    "binding_status_receipt_id",
    "binding_status_receipt_sha256",
    "binding_explicit_chain_set_sha256",
    "binding_coverage_set_sha256",
    "binding_joint_replay_sha256",
    "binding_as_of_assessment_sha256",
    "binding_as_of_status",
    "binding_at",
    "binding_status_valid_until",
    "binding_evidence_valid_until",
    "binding_state",
    "role_binding_performed",
    "provider_input_eligible",
    "present_currentness_asserted",
    "perpetual_role_suitability_asserted",
    "role_binding_exclusivity_asserted",
    "complete_role_set_asserted",
    "global_role_uniqueness_asserted",
    "current_role_binding_asserted",
    "supersedes_role_binding",
    "primary_asset_binding_replaced",
    "bible_active_binding_changed",
    "asset_version_v1_created",
    "whole_composite_media_bound",
    "crop_applied",
    "split_applied",
    "transform_applied",
    "derived_media_created",
    "provider_slot_embedded",
    "status",
    "evidence_scope",
    *_ZERO_AUTHORITY_VALUES,
)


def _projection(value: object, names: tuple[str, ...]) -> dict[str, object]:
    if isinstance(value, BaseModel):
        return {name: _explicit_value(getattr(value, name)) for name in names}
    if type(value) is dict:
        source = cast(dict[str, object], value)
        return {name: _explicit_value(source[name]) for name in names}
    _invalid("projection source must be one exact model or mapping")


def _target_projection_unchecked(
    value: GeneratedReferenceEligibleAssetRoleBindingTargetV1,
) -> dict[str, object]:
    return _projection(value, _TARGET_PROJECTION_FIELDS)


def _review_payload_from_request(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
) -> dict[str, object]:
    return _projection(value, _REVIEW_PAYLOAD_FIELDS)


def _request_projection_unchecked(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
) -> dict[str, object]:
    return _projection(value, _REQUEST_PROJECTION_FIELDS)


def _decision_projection_unchecked(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
) -> dict[str, object]:
    return _projection(value, _DECISION_PROJECTION_FIELDS)


def _binding_projection_unchecked(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
) -> dict[str, object]:
    return _projection(value, _BINDING_PROJECTION_FIELDS)


_SELF_FIELDS: dict[type[BaseModel], tuple[str, str, str, bytes, tuple[str, ...]]] = {
    CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1: (
        "request_id",
        "request_sha256",
        _REQUEST_ID_STEM,
        GENERATED_REFERENCE_ROLE_BINDING_REQUEST_SHA256_DOMAIN,
        _REQUEST_PROJECTION_FIELDS,
    ),
    CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1: (
        "decision_id",
        "decision_sha256",
        _DECISION_ID_STEM,
        GENERATED_REFERENCE_ROLE_BINDING_DECISION_SHA256_DOMAIN,
        _DECISION_PROJECTION_FIELDS,
    ),
    CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1: (
        "binding_id",
        "binding_sha256",
        _BINDING_ID_STEM,
        GENERATED_REFERENCE_ROLE_BINDING_SHA256_DOMAIN,
        _BINDING_PROJECTION_FIELDS,
    ),
}


def _validate_identity(value: BaseModel, expected: type[BaseModel]) -> None:
    id_field, sha_field, stem, domain, names = _SELF_FIELDS[expected]
    digest = _semantic_sha256(domain, _projection(value, names))
    if (
        getattr(value, sha_field) != digest
        or getattr(value, id_field) != f"{stem}{digest[:20]}"
    ):
        _invalid("semantic ID or digest mismatch")


def _validate_request_contract(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
) -> None:
    if not (
        value.requested_as_of == value.requested_at == value.maker_prepared_at
    ):
        _invalid("Request times must close at exact requested_at")
    if _parse_utc(value.promotion_at, field="promotion_at") > _parse_utc(
        value.requested_at, field="requested_at"
    ):
        _invalid("requested_at precedes Sidecar promotion_at")
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
    if expected_until <= requested_at or value.request_valid_until != _format_utc(
        expected_until
    ):
        _invalid("Request deadline is not the exact frozen minimum")
    if value.media_binding_scope != value.requested_role_binding_target.media_binding_scope:
        _invalid("Request media-binding scope differs from target")
    review_sha = _semantic_sha256(
        GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
        _review_payload_from_request(value),
    )
    if value.role_binding_review_payload_sha256 != review_sha:
        _invalid("Role-Binding review payload digest mismatch")
    _validate_identity(
        value, CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1
    )
    if len(_persistent_json(_explicit_value(value))) > _MAX_FORMAL_DOCUMENT_BYTES:
        _invalid("Request exceeds formal document byte limit")


def _expected_issues(
    gates: tuple[GeneratedReferenceRoleBindingGateResultV1, ...],
) -> tuple[BindingIssueCode, ...]:
    mapping: dict[int, BindingIssueCode] = {
        4: "STATUS_NOT_CURRENT_AT_ROLE_BINDING",
        5: "PRIMARY_BINDING_NO_LONGER_ACTIVE",
        8: "EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTATION_NOT_ACKNOWLEDGED",
        9: "WHOLE_COMPOSITE_ROLE_SUITABILITY_NOT_APPROVED",
        10: "NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_NOT_ACKNOWLEDGED",
    }
    return tuple(
        mapping[index]
        for index in (4, 5, 8, 9, 10)
        if gates[index].result == "FAIL"
    )


def _decision_from_gates(
    gates: tuple[GeneratedReferenceRoleBindingGateResultV1, ...],
) -> BindingDecision:
    if any(item.result == "FAIL" for item in gates):
        return "REJECT_ELIGIBLE_ASSET_ROLE_BINDING"
    if any(item.result == "INDETERMINATE" for item in gates):
        return "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING"
    return "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"


_COMPILER_GATE_BASES: tuple[str | None, ...] = (
    "COMPILER_REVALIDATED_EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR",
    "COMPILER_REVALIDATED_EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
    "COMPILER_REVALIDATED_POSITIVE_UNEXPIRED_QUALIFICATION",
    "COMPILER_REVALIDATED_VALID_GENERATED_RIGHTS_MANIFEST",
    "COMPILER_REPLAYED_GENERATED_CURRENT_STATUS_AT_ROLE_BINDING",
    "COMPILER_REVALIDATED_FINAL_SUPPLIED_PRIMARY_ASSET_BINDING",
    "COMPILER_REVALIDATED_ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP",
    "COMPILER_REVALIDATED_EXACT_MANIFEST_REVIEWED_RIGHTS_SCOPE",
    None,
    None,
    None,
    "COMPILER_REVALIDATED_ROLE_BINDING_REVIEWER_SEPARATION",
)


def _validate_decision_contract(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
) -> None:
    if not value.checker_reviewed_at == value.decision_at == value.binding_at:
        _invalid("Decision times must equal exact binding_at")
    binding_at = _parse_utc(value.binding_at, field="binding_at")
    for name in (
        "qualification_valid_until",
        "manifest_valid_until",
        "binding_status_valid_until",
    ):
        if binding_at >= _parse_utc(cast(str, getattr(value, name)), field=name):
            _invalid(f"binding_at is outside {name}")
    if tuple(item.gate for item in value.gate_results) != ROLE_BINDING_GATE_ORDER:
        _invalid("Decision gate tuple is not canonical")
    for index in (0, 1, 2, 3, 6, 7, 11):
        if value.gate_results[index].result != "PASS":
            _invalid("compiler pass-only Role-Binding gate is not PASS")
    for index, basis in enumerate(_COMPILER_GATE_BASES):
        if basis is not None and value.gate_results[index].basis != basis:
            _invalid("compiler-derived Role-Binding gate basis mismatch")
    status_result: GateResult = cast(
        GateResult,
        {
            "CURRENT": "PASS",
            "EXPIRED": "FAIL",
            "REVOKED": "FAIL",
            "HELD": "FAIL",
            "INDETERMINATE": "INDETERMINATE",
        }[value.binding_as_of_status],
    )
    if value.gate_results[4].result != status_result:
        _invalid("binding status gate mapping mismatch")
    same_binding = (
        value.requested_primary_asset_binding == value.binding_primary_asset_binding
    )
    if value.gate_results[5].result != ("PASS" if same_binding else "FAIL"):
        _invalid("primary binding gate mapping mismatch")
    if (
        value.requested_primary_asset_binding.subject_id
        != value.binding_primary_asset_binding.subject_id
        or value.requested_primary_asset_binding.asset_purpose
        != value.binding_primary_asset_binding.asset_purpose
    ):
        _invalid("Decision primary bindings cross subject or purpose")
    if value.binding_issue_codes != _expected_issues(value.gate_results):
        _invalid("Role-Binding issue tuple is not the exact policy subsequence")
    expected_decision = _decision_from_gates(value.gate_results)
    if value.decision != expected_decision:
        _invalid("Role-Binding Decision does not match its gate tuple")
    if value.binding_materialization_allowed is not (
        expected_decision == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
    ):
        _invalid("Binding materialization Boolean does not match Decision")
    _validate_identity(
        value, CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1
    )
    if len(_persistent_json(_explicit_value(value))) > _MAX_FORMAL_DOCUMENT_BYTES:
        _invalid("Decision exceeds formal document byte limit")


def _validate_binding_contract(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
) -> None:
    expected_until = min(
        _parse_utc(value.qualification_valid_until, field="qualification_valid_until"),
        _parse_utc(value.manifest_valid_until, field="manifest_valid_until"),
        _parse_utc(value.binding_status_valid_until, field="binding_status_valid_until"),
    )
    binding_at = _parse_utc(value.binding_at, field="binding_at")
    if expected_until <= binding_at or value.binding_evidence_valid_until != _format_utc(
        expected_until
    ):
        _invalid("Binding historical evidence horizon mismatch")
    _validate_identity(value, CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1)
    if len(_persistent_json(_explicit_value(value))) > _MAX_FORMAL_DOCUMENT_BYTES:
        _invalid("Binding exceeds formal document byte limit")


def generated_reference_role_binding_target_projection(
    value: GeneratedReferenceEligibleAssetRoleBindingTargetV1,
) -> dict[str, object]:
    validated = cast(
        GeneratedReferenceEligibleAssetRoleBindingTargetV1,
        _exact_nested_model(
            value,
            GeneratedReferenceEligibleAssetRoleBindingTargetV1,
            field="Role-Binding target",
        ),
    )
    return _target_projection_unchecked(validated)


def generated_reference_role_binding_target_sha256(
    value: GeneratedReferenceEligibleAssetRoleBindingTargetV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_ROLE_BINDING_TARGET_SHA256_DOMAIN,
        generated_reference_role_binding_target_projection(value),
    )


def generated_reference_role_binding_review_payload_projection(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
) -> dict[str, object]:
    validated = cast(
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
        _exact_formal_model(
            value,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
            field="Role-Binding Request",
        ),
    )
    return _review_payload_from_request(validated)


def generated_reference_role_binding_review_payload_sha256(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
        generated_reference_role_binding_review_payload_projection(value),
    )


def creative_sample_generated_reference_eligible_asset_role_binding_request_projection(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
) -> dict[str, object]:
    validated = cast(
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
        _exact_formal_model(
            value,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
            field="Role-Binding Request",
        ),
    )
    return _request_projection_unchecked(validated)


def creative_sample_generated_reference_eligible_asset_role_binding_request_sha256(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_ROLE_BINDING_REQUEST_SHA256_DOMAIN,
        creative_sample_generated_reference_eligible_asset_role_binding_request_projection(value),
    )


def creative_sample_generated_reference_eligible_asset_role_binding_decision_projection(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
) -> dict[str, object]:
    validated = cast(
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
        _exact_formal_model(
            value,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
            field="Role-Binding Decision",
        ),
    )
    return _decision_projection_unchecked(validated)


def creative_sample_generated_reference_eligible_asset_role_binding_decision_sha256(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_ROLE_BINDING_DECISION_SHA256_DOMAIN,
        creative_sample_generated_reference_eligible_asset_role_binding_decision_projection(value),
    )


def creative_sample_generated_reference_eligible_asset_role_binding_projection(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
) -> dict[str, object]:
    validated = cast(
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        _exact_formal_model(
            value,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
            field="Eligible-Asset Role Binding",
        ),
    )
    return _binding_projection_unchecked(validated)


def creative_sample_generated_reference_eligible_asset_role_binding_sha256(
    value: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_ROLE_BINDING_SHA256_DOMAIN,
        creative_sample_generated_reference_eligible_asset_role_binding_projection(value),
    )


def generated_reference_role_binding_contract_document_bytes(value: BaseModel) -> bytes:
    if type(value) not in _SELF_FIELDS:
        _fail(
            "CONTRACT_FIELD_INVALID",
            "only an exact ADR-046 top-level Contract is admitted",
        )
    validated = _exact_formal_model(value, type(value), field="Role-Binding Contract")
    encoded = _persistent_json(_explicit_value(validated))
    if not 1 <= len(encoded) <= _MAX_FORMAL_DOCUMENT_BYTES:
        _fail("INPUT_RESOURCE_LIMIT_EXCEEDED", "formal document exceeds byte limits")
    return encoded


def _exact_nested_model(
    value: object, expected: type[BaseModel], *, field: str
) -> BaseModel:
    if type(value) is not expected:
        _fail("CONTRACT_FIELD_INVALID", f"{field} must have exact type {expected.__name__}")
    try:
        explicit = _explicit_value(value)
        rebuilt = expected.model_validate(_arrays_to_tuples(explicit))
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", f"{field} fails exact revalidation"
        ) from exc
    if rebuilt != value:
        _fail("CONTRACT_FIELD_INVALID", f"{field} changes under exact revalidation")
    return rebuilt


def _verify_formal_resource(value: object, expected: type[BaseModel], *, field: str) -> dict[str, object]:
    if type(value) is not expected:
        _fail("CONTRACT_FIELD_INVALID", f"{field} must have exact type {expected.__name__}")
    try:
        explicit = _explicit_value(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "INPUT_DOCUMENT_INVALID", f"{field} cannot expose its frozen JSON fields"
        ) from exc
    if type(explicit) is not dict:
        _fail("INPUT_DOCUMENT_INVALID", f"{field} is not one frozen JSON object")
    original = cast(dict[str, object], explicit)
    try:
        encoded = _persistent_json(original)
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "INPUT_DOCUMENT_INVALID", f"{field} is outside canonical JSON"
        ) from exc
    if not 1 <= len(encoded) <= _MAX_FORMAL_DOCUMENT_BYTES:
        _fail("INPUT_RESOURCE_LIMIT_EXCEEDED", f"{field} exceeds byte limits")
    return original


def _preflight_formal_resource_limit(
    value: object, expected: type[BaseModel], *, field: str
) -> None:
    """Check one exact formal input's byte limit without claiming document validity.

    A value outside canonical JSON belongs to the following document stage.  This
    resource-only pass therefore skips values that cannot yet be serialized, so
    another exact formal input's independently provable size violation cannot be
    hidden by an earlier document error.
    """

    if type(value) is not expected:
        return
    try:
        explicit = _explicit_value(value)
        if type(explicit) is not dict:
            return
        encoded = _persistent_json(explicit)
    except (AttributeError, TypeError, ValueError):
        return
    if not 1 <= len(encoded) <= _MAX_FORMAL_DOCUMENT_BYTES:
        _fail("INPUT_RESOURCE_LIMIT_EXCEEDED", f"{field} exceeds byte limits")


def _expected_model_fields(expected: type[BaseModel]) -> set[str]:
    return set(expected.model_fields)


def _sanitize_target(value: object) -> GeneratedReferenceEligibleAssetRoleBindingTargetV1:
    if isinstance(value, BaseModel):
        payload = cast(dict[str, object], _explicit_value(value))
    elif type(value) is dict:
        payload = dict(cast(dict[str, object], value))
    else:
        _invalid("target is not one object")
    projection = _projection(payload, _TARGET_PROJECTION_FIELDS)
    payload["target_sha256"] = _semantic_sha256(
        GENERATED_REFERENCE_ROLE_BINDING_TARGET_SHA256_DOMAIN, projection
    )
    return GeneratedReferenceEligibleAssetRoleBindingTargetV1.model_validate(
        _arrays_to_tuples(payload)
    )


def _sanitize_formal_structure(
    original: Mapping[str, object], expected: type[BaseModel]
) -> BaseModel:
    if set(original) != _expected_model_fields(expected):
        _invalid("formal Contract field set drifted")
    payload = dict(original)
    payload["policy_id"] = GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID
    payload["policy_version"] = GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION
    payload["policy_document_sha256"] = (
        GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256
    )
    payload.update(_zero_authority_values())
    target_name = (
        "role_binding_target"
        if expected is CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1
        else "requested_role_binding_target"
    )
    payload[target_name] = _sanitize_target(payload[target_name])
    id_field, sha_field, stem, domain, names = _SELF_FIELDS[expected]
    if expected is CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1:
        payload["role_binding_review_payload_sha256"] = _semantic_sha256(
            GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
            _projection(payload, _REVIEW_PAYLOAD_FIELDS),
        )
    digest = _semantic_sha256(domain, _projection(payload, names))
    payload[id_field] = f"{stem}{digest[:20]}"
    payload[sha_field] = digest
    return expected.model_validate(_arrays_to_tuples(payload))


def _verify_policy_fields(original: Mapping[str, object], *, field: str) -> None:
    _verify_policy_identity()
    if (
        original.get("policy_id") != GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID
        or original.get("policy_version") != GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION
        or original.get("policy_document_sha256")
        != GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256
    ):
        _fail("POLICY_IDENTITY_MISMATCH", f"{field} policy identity drifted")


def _verify_target_identity(value: object, *, field: str) -> None:
    if isinstance(value, BaseModel):
        payload = cast(dict[str, object], _explicit_value(value))
    elif type(value) is dict:
        payload = cast(dict[str, object], value)
    else:
        _fail("FORMAL_IDENTITY_MISMATCH", f"{field} target is not an object")
    try:
        digest = _semantic_sha256(
            GENERATED_REFERENCE_ROLE_BINDING_TARGET_SHA256_DOMAIN,
            _projection(payload, _TARGET_PROJECTION_FIELDS),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", f"{field} target projection is incomplete"
        ) from exc
    if payload.get("target_sha256") != digest:
        _fail("FORMAL_IDENTITY_MISMATCH", f"{field} target digest drifted")


def _verify_formal_identity(
    original: Mapping[str, object], expected: type[BaseModel], *, field: str
) -> None:
    target_name = (
        "role_binding_target"
        if expected is CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1
        else "requested_role_binding_target"
    )
    _verify_target_identity(original.get(target_name), field=field)
    if expected is CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1:
        review_digest = _semantic_sha256(
            GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
            _projection(dict(original), _REVIEW_PAYLOAD_FIELDS),
        )
        if original.get("role_binding_review_payload_sha256") != review_digest:
            _fail("FORMAL_IDENTITY_MISMATCH", f"{field} review payload digest drifted")
    id_field, sha_field, stem, domain, names = _SELF_FIELDS[expected]
    digest = _semantic_sha256(domain, _projection(dict(original), names))
    if (
        original.get(sha_field) != digest
        or original.get(id_field) != f"{stem}{digest[:20]}"
    ):
        _fail("FORMAL_IDENTITY_MISMATCH", f"{field} semantic identity drifted")


def _verify_zero_authority(original: Mapping[str, object], *, field: str) -> None:
    if any(
        original.get(name) != expected
        for name, expected in _ZERO_AUTHORITY_VALUES.items()
    ):
        _fail("AUTHORITY_SURFACE_NONZERO", f"{field} authority surface is not exact zero")


_PROHIBITED_URI = re.compile(r"(?i)(?:https?|ftp)://|(?:data|file)://")
_PROHIBITED_PATH = re.compile(r"(?:^[A-Za-z]:[\\/]|^\\\\|^/|(?:^|[\\/])\.\.?[\\/])")
_PROHIBITED_SECRET = re.compile(
    r"(?i)(?:bearer\s+[A-Za-z0-9._~+/=-]{8,}|(?:api[_-]?key|secret|password|credential)\s*[:=])"
)
_PROHIBITED_KEYS = frozenset(
    {
        "local_path",
        "provider_endpoint",
        "provider_route",
        "provider_slot",
        "provider_request",
        "input_material",
        "credential",
        "api_key",
        "secret",
    }
)


def _verify_no_prohibited_connection(value: object, *, field: str) -> None:
    if type(value) is str:
        text = value
        if (
            _PROHIBITED_URI.search(text)
            or _PROHIBITED_PATH.search(text)
            or _PROHIBITED_SECRET.search(text)
        ):
            _fail(
                "PROHIBITED_BOUNDARY_CONNECTION",
                f"{field} contains a prohibited path, URL, or credential",
            )
        return
    if type(value) in {tuple, list}:
        for item in cast(Sequence[object], value):
            _verify_no_prohibited_connection(item, field=field)
        return
    if type(value) is dict:
        for key, item in cast(dict[str, object], value).items():
            if key.lower() in _PROHIBITED_KEYS:
                _fail(
                    "PROHIBITED_BOUNDARY_CONNECTION",
                    f"{field} contains a prohibited structured boundary field",
                )
            _verify_no_prohibited_connection(item, field=field)


def _exact_formal_model(
    value: object, expected: type[BaseModel], *, field: str
) -> BaseModel:
    original = _verify_formal_resource(value, expected, field=field)
    try:
        _sanitize_formal_structure(original, expected)
    except GeneratedReferenceRoleBindingError:
        raise
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", f"{field} fails frozen structural validation"
        ) from exc
    _verify_policy_fields(original, field=field)
    _verify_formal_identity(original, expected, field=field)
    _verify_zero_authority(original, field=field)
    _verify_no_prohibited_connection(original, field=field)
    try:
        rebuilt = expected.model_validate(_arrays_to_tuples(original))
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", f"{field} fails final exact revalidation"
        ) from exc
    if rebuilt != value:
        _fail("CONTRACT_FIELD_INVALID", f"{field} changes under exact revalidation")
    return rebuilt


def _preflight_formal_workflow_prefix(
    value: object, expected: type[BaseModel], *, field: str
) -> dict[str, object]:
    """Run only resource through semantic-identity stages for a workflow input.

    Authority and prohibited-connection checks are deliberately deferred to their
    frozen workflow stages.  The structural sanitizer validates every other frozen
    field while replacing only fields owned by later priority stages.
    """

    original = _verify_formal_resource(value, expected, field=field)
    try:
        _sanitize_formal_structure(original, expected)
    except GeneratedReferenceRoleBindingError:
        raise
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", f"{field} fails frozen structural validation"
        ) from exc
    _verify_policy_fields(original, field=field)
    _verify_formal_identity(original, expected, field=field)
    return original


def _complete_formal_workflow_boundary(
    value: object,
    original: Mapping[str, object],
    expected: type[BaseModel],
    *,
    field: str,
) -> BaseModel:
    """Apply authority then prohibited-connection stages and rebuild exactly."""

    _verify_zero_authority(original, field=field)
    _verify_no_prohibited_connection(original, field=field)
    try:
        rebuilt = expected.model_validate(_arrays_to_tuples(original))
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", f"{field} fails final exact revalidation"
        ) from exc
    if rebuilt != value:
        _fail("CONTRACT_FIELD_INVALID", f"{field} changes under exact revalidation")
    return rebuilt


def _build_identity(
    model_type: type[BaseModel], values: Mapping[str, object]
) -> BaseModel:
    id_field, sha_field, stem, domain, names = _SELF_FIELDS[model_type]
    if set(values) != set(names):
        _fail("CONTRACT_FIELD_INVALID", "closed Contract values drifted from field inventory")
    payload = dict(values)
    digest = _semantic_sha256(domain, _projection(payload, names))
    payload[id_field] = f"{stem}{digest[:20]}"
    payload[sha_field] = digest
    try:
        value = model_type.model_validate(_arrays_to_tuples(payload))
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", f"{model_type.__name__} construction failed"
        ) from exc
    return _exact_formal_model(value, model_type, field=model_type.__name__)


def _build_identity_with_deferred_boundary(
    model_type: type[BaseModel], values: Mapping[str, object]
) -> BaseModel:
    """Build an internal replay value through formal identity, deferring 16-17."""

    id_field, sha_field, stem, domain, names = _SELF_FIELDS[model_type]
    if set(values) != set(names):
        _fail("CONTRACT_FIELD_INVALID", "closed Contract values drifted from field inventory")
    payload = dict(values)
    digest = _semantic_sha256(domain, _projection(payload, names))
    payload[id_field] = f"{stem}{digest[:20]}"
    payload[sha_field] = digest
    try:
        value = model_type.model_validate(_arrays_to_tuples(payload))
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", f"{model_type.__name__} construction failed"
        ) from exc
    _preflight_formal_workflow_prefix(
        value, model_type, field=f"internal replay {model_type.__name__}"
    )
    return value


@dataclass(frozen=True, slots=True)
class GeneratedReferenceRoleBindingAdmittedPng:
    """Immutable output of one safe bounded local-PNG admission."""

    png_bytes: bytes
    media_content_sha256: str
    media_size_bytes: int
    media_technical_record_sha256: str

    def __post_init__(self) -> None:
        if type(self.png_bytes) is not bytes:
            _fail("PNG_ADMISSION_INVALID", "admitted PNG bytes must be exact bytes")
        if not 1 <= len(self.png_bytes) <= _MAX_PNG_BYTES:
            _fail("INPUT_RESOURCE_LIMIT_EXCEEDED", "admitted PNG is outside byte limits")
        if type(self.media_size_bytes) is not int or self.media_size_bytes != len(
            self.png_bytes
        ):
            _fail("PNG_ADMISSION_INVALID", "admitted PNG size does not close its bytes")
        if (
            type(self.media_content_sha256) is not str
            or re.fullmatch(_LOWER_SHA256_PATTERN, self.media_content_sha256) is None
            or self.media_content_sha256 != _raw_sha256(self.png_bytes)
        ):
            _fail("PNG_ADMISSION_INVALID", "admitted PNG raw digest mismatch")
        if (
            type(self.media_technical_record_sha256) is not str
            or re.fullmatch(
                _LOWER_SHA256_PATTERN, self.media_technical_record_sha256
            )
            is None
        ):
            _fail("PNG_ADMISSION_INVALID", "admitted PNG technical digest is invalid")


@dataclass(frozen=True, slots=True)
class GeneratedReferenceRoleBindingPromotionClosureInput:
    """Complete retained ADR-045 closure required to rebuild one positive Sidecar."""

    request: CreativeSampleGeneratedReferenceAssetPromotionRequestV1
    result: GeneratedReferenceAssetPromotionFinalizationResult
    upstream: GeneratedReferenceAssetPromotionUpstreamClosureInput
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput
    requested_primary_bible: CharacterBible | SceneBible
    requested_primary_asset_version: CharacterAssetVersion | SceneAssetVersion
    final_status: GeneratedReferenceAssetPromotionStatusClosureInput
    promotion_primary_bible: CharacterBible | SceneBible
    promotion_primary_asset_version: CharacterAssetVersion | SceneAssetVersion
    maker_identity_bytes: bytes
    maker_action_bytes: bytes
    checker_identity_bytes: bytes
    checker_action_bytes: bytes
    promotion_at: str
    primary_sidecar_association_result: GateResult
    primary_sidecar_association_basis: str
    composite_unsplit_role_deferral_result: GateResult
    composite_unsplit_role_deferral_basis: str
    promotion_basis: str


@dataclass(frozen=True, slots=True)
class GeneratedReferenceRoleBindingFinalizationResult:
    """Decision-only negative result or atomic positive Decision/Binding pair."""

    decision: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1
    binding: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1 | None

    def __post_init__(self) -> None:
        _validate_finalization_result(self)


def _is_reparse_point(file_stat: object) -> bool:
    attributes = getattr(file_stat, "st_file_attributes", 0)
    return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)


def _file_identity(file_stat: object) -> tuple[object, ...]:
    return (
        getattr(file_stat, "st_dev", None),
        getattr(file_stat, "st_ino", None),
        getattr(file_stat, "st_nlink", None),
        getattr(file_stat, "st_size", None),
        getattr(file_stat, "st_mtime_ns", None),
    )


def _read_safe_single_file(path: Path) -> bytes:
    if type(path) is not type(Path()):
        _fail("PNG_ADMISSION_INVALID", "png_path must be an exact pathlib.Path")
    try:
        before = path.lstat()
        if (
            path.is_symlink()
            or _is_reparse_point(before)
            or not S_ISREG(before.st_mode)
            or getattr(before, "st_nlink", None) != 1
        ):
            _fail(
                "PNG_ADMISSION_INVALID",
                "PNG path must name one regular single-link non-reparse file",
            )
        if not 1 <= before.st_size <= _MAX_PNG_BYTES:
            _fail("INPUT_RESOURCE_LIMIT_EXCEEDED", "PNG size is outside admitted bounds")
        with path.open("rb") as handle:
            opened = fstat(handle.fileno())
            if (
                _is_reparse_point(opened)
                or not S_ISREG(opened.st_mode)
                or getattr(opened, "st_nlink", None) != 1
            ):
                _fail(
                    "PNG_ADMISSION_INVALID",
                    "opened PNG handle is not a regular single-link non-reparse file",
                )
            if _file_identity(before) != _file_identity(opened):
                _fail("PNG_ADMISSION_INVALID", "PNG path identity changed while opening")
            raw = handle.read(_MAX_PNG_BYTES + 1)
            if len(raw) > _MAX_PNG_BYTES:
                _fail("INPUT_RESOURCE_LIMIT_EXCEEDED", "PNG crossed its byte limit")
            after_handle = fstat(handle.fileno())
            if (
                _file_identity(opened) != _file_identity(after_handle)
                or len(raw) != opened.st_size
            ):
                _fail("PNG_ADMISSION_INVALID", "PNG changed while it was read")
        after_path = path.lstat()
        if (
            path.is_symlink()
            or _is_reparse_point(after_path)
            or getattr(after_path, "st_nlink", None) != 1
            or _file_identity(before) != _file_identity(after_path)
        ):
            _fail("PNG_ADMISSION_INVALID", "PNG path identity changed after admission")
        return raw
    except GeneratedReferenceRoleBindingError:
        raise
    except OSError as exc:
        raise GeneratedReferenceRoleBindingError(
            "PNG_ADMISSION_INVALID", "PNG safe-file admission failed"
        ) from exc


def admit_generated_reference_role_binding_png(
    png_path: Path,
) -> GeneratedReferenceRoleBindingAdmittedPng:
    """Safely read and technically validate one explicitly named local PNG."""

    raw = _read_safe_single_file(png_path)
    try:
        descriptor = admit_generated_reference_png(png_path)
    except GeneratedReferenceCandidateError as exc:
        raise GeneratedReferenceRoleBindingError(
            "PNG_ADMISSION_INVALID", "PNG technical admission failed"
        ) from exc
    raw_sha = _raw_sha256(raw)
    if descriptor.content_sha256 != raw_sha or descriptor.size_bytes != len(raw):
        _fail(
            "PNG_ADMISSION_INVALID",
            "technical admission and stable-handle bytes are not exact-equal",
        )
    return GeneratedReferenceRoleBindingAdmittedPng(
        png_bytes=raw,
        media_content_sha256=raw_sha,
        media_size_bytes=len(raw),
        media_technical_record_sha256=descriptor.technical_record_sha256,
    )


def _verify_promotion_closure(
    closure: GeneratedReferenceRoleBindingPromotionClosureInput,
) -> tuple[
    CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
    CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
]:
    if type(closure) is not GeneratedReferenceRoleBindingPromotionClosureInput:
        _fail("CONTRACT_FIELD_INVALID", "Promotion closure has the wrong process type")
    try:
        verified = verify_generated_reference_asset_promotion_finalization(
            closure.result,
            closure.request,
            closure.upstream,
            closure.request_status,
            closure.requested_primary_bible,
            closure.requested_primary_asset_version,
            closure.final_status,
            closure.promotion_primary_bible,
            closure.promotion_primary_asset_version,
            maker_identity_bytes=closure.maker_identity_bytes,
            maker_action_bytes=closure.maker_action_bytes,
            checker_identity_bytes=closure.checker_identity_bytes,
            checker_action_bytes=closure.checker_action_bytes,
            promotion_at=closure.promotion_at,
            primary_sidecar_association_result=closure.primary_sidecar_association_result,
            primary_sidecar_association_basis=closure.primary_sidecar_association_basis,
            composite_unsplit_role_deferral_result=(
                closure.composite_unsplit_role_deferral_result
            ),
            composite_unsplit_role_deferral_basis=(
                closure.composite_unsplit_role_deferral_basis
            ),
            promotion_basis=closure.promotion_basis,
        )
    except GeneratedReferenceAssetPromotionError:
        raise
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "PROMOTION_CLOSURE_INVALID", "ADR-045 Promotion closure failed"
        ) from exc
    sidecar = verified.sidecar
    if (
        verified.decision.decision != "APPROVE_ELIGIBLE_ASSET_SIDECAR"
        or sidecar is None
        or type(sidecar) is not CreativeSampleGeneratedReferenceEligibleAssetSidecarV1
    ):
        _fail(
            "PROMOTION_CLOSURE_INVALID",
            "Role Binding requires one exact positive Promotion/Sidecar pair",
        )
    if verified != closure.result:
        _fail("PROMOTION_CLOSURE_INVALID", "Promotion finalization rebuild drifted")
    return closure.request, sidecar


_ADR044_REPLAY_ERRORS = (
    GeneratedReferenceRightsCurrentStatusError,
    GeneratedReferenceChainReplayError,
    GeneratedReferenceChainCoverageError,
    GeneratedReferenceJointReplayError,
    GeneratedReferenceAsOfAssessmentError,
    GeneratedReferenceReceiptError,
)


def _verify_status_closure(
    closure: GeneratedReferenceAssetPromotionStatusClosureInput,
    manifest: CreativeSampleGeneratedReferenceRightsManifestV1,
    *,
    as_of: str,
) -> CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1:
    if type(closure) is not GeneratedReferenceAssetPromotionStatusClosureInput:
        _fail("CONTRACT_FIELD_INVALID", "status closure has the wrong process type")
    try:
        expected_subject = build_generated_reference_current_status_subject_closure(manifest)
        if type(closure.subject_closure) is not GeneratedReferenceCurrentStatusSubjectClosureV1:
            _fail("UPSTREAM_CLOSURE_MISMATCH", "status subject closure type mismatch")
        if closure.subject_closure != expected_subject:
            _fail(
                "UPSTREAM_CLOSURE_MISMATCH",
                "status subject closure does not bind the exact Manifest",
            )
        for supplied, embedded, expected_type, field in (
            (
                closure.request,
                closure.record.request,
                CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
                "status Request",
            ),
            (
                closure.instruction,
                closure.record.instruction,
                CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
                "status Instruction",
            ),
            (
                closure.decision,
                closure.record.decision,
                CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
                "status Decision",
            ),
        ):
            if type(supplied) is not expected_type or supplied != embedded:
                _fail("UPSTREAM_CLOSURE_MISMATCH", f"{field} differs from Evidence Record")
        if (
            type(closure.record)
            is not CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1
            or closure.record.subject_closure != expected_subject
        ):
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
            _fail("CURRENT_STATUS_REPLAY_INVALID", "status Record rebuild differs")
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
                "CURRENT_STATUS_REPLAY_INVALID",
                "supplied Receipt differs from same-call complete replay",
            )
        return fresh_receipt
    except GeneratedReferenceRoleBindingError:
        raise
    except _ADR044_REPLAY_ERRORS:
        raise
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CURRENT_STATUS_REPLAY_INVALID",
            "complete generated current-status replay failed",
        ) from exc


def _observation_occurrence_map(
    closure: GeneratedReferenceAssetPromotionStatusClosureInput,
) -> dict[tuple[str, str, str], bytes]:
    result: dict[tuple[str, str, str], bytes] = {}
    for chain_index, chain_input in enumerate(closure.chain_inputs):
        if type(chain_input) is not GeneratedReferenceCurrentStatusExplicitChainInput:
            _fail(
                "CURRENT_STATUS_REPLAY_INVALID",
                f"chain_inputs[{chain_index}] has the wrong exact process type",
            )
        for item_index, item in enumerate(chain_input.observation_inputs):
            if type(item) is not GeneratedReferenceCurrentStatusObservationInput:
                _fail(
                    "CURRENT_STATUS_REPLAY_INVALID",
                    f"chain_inputs[{chain_index}].observation_inputs[{item_index}] type mismatch",
                )
            canonical = generated_reference_contract_document_bytes(item.observation)
            if type(item.document_bytes) is not bytes or item.document_bytes != canonical:
                _fail(
                    "CURRENT_STATUS_REPLAY_INVALID",
                    "Observation bytes differ from exact Contract",
                )
            anchor = (
                item.observation.observation_id,
                item.observation.observation_sha256,
                generated_reference_current_status_chain_sha256(item.observation),
            )
            prior = result.get(anchor)
            if prior is not None and prior != item.document_bytes:
                _fail(
                    "CURRENT_STATUS_REPLAY_INVALID",
                    "Observation occurrence anchor aliases bytes",
                )
            result[anchor] = item.document_bytes
    return result


def _target_anchors(
    closure: GeneratedReferenceAssetPromotionStatusClosureInput,
) -> set[tuple[str, str, str]]:
    return {
        (item.observation_id, item.observation_sha256, item.chain_sha256)
        for item in closure.request.observation_refs
    }


def _verify_status_monotonicity(
    prior: GeneratedReferenceAssetPromotionStatusClosureInput,
    later: GeneratedReferenceAssetPromotionStatusClosureInput,
) -> None:
    if prior.subject_closure != later.subject_closure:
        _fail(
            "UPSTREAM_CLOSURE_MISMATCH",
            "adjacent status Records do not share one exact Status Subject Closure",
        )
    prior_occurrences = _observation_occurrence_map(prior)
    later_occurrences = _observation_occurrence_map(later)
    for anchor, prior_bytes in prior_occurrences.items():
        if later_occurrences.get(anchor) != prior_bytes:
            _fail(
                "CURRENT_STATUS_REPLAY_INVALID",
                "later Record omits, substitutes, or rewrites a prior Observation occurrence",
            )
    later_targets = _target_anchors(later)
    predecessor_anchors: dict[
        tuple[str, str, str], set[tuple[str, str, str]]
    ] = {}
    for chain_input in later.chain_inputs:
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
    complete_ancestry = set(later_targets)
    frontier = list(later_targets)
    while frontier:
        current = frontier.pop()
        for predecessor in predecessor_anchors.get(current, set()):
            if predecessor not in complete_ancestry:
                complete_ancestry.add(predecessor)
                frontier.append(predecessor)
    for prior_target in _target_anchors(prior):
        if prior_target not in complete_ancestry:
            _fail(
                "CURRENT_STATUS_REPLAY_INVALID",
                "prior target is neither retained nor an exact complete ancestor",
            )


def _verify_admitted_png(
    admitted_png: GeneratedReferenceRoleBindingAdmittedPng,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    sidecar: CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
) -> GeneratedReferenceRoleBindingAdmittedPng:
    if type(admitted_png) is not GeneratedReferenceRoleBindingAdmittedPng:
        _fail("PNG_ADMISSION_INVALID", "admitted_png has the wrong exact process type")
    admitted_png.__post_init__()
    if (
        type(promotion.upstream.png_bytes) is not bytes
        or admitted_png.png_bytes != promotion.upstream.png_bytes
        or admitted_png.media_content_sha256 != sidecar.media_content_sha256
        or admitted_png.media_size_bytes != sidecar.media_size_bytes
        or admitted_png.media_technical_record_sha256
        != sidecar.media_technical_record_sha256
    ):
        _fail(
            "PNG_ADMISSION_INVALID",
            "admitted PNG does not equal the Candidate/Sidecar occurrence",
        )
    return admitted_png


def _target_values(
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    admitted_png: GeneratedReferenceRoleBindingAdmittedPng,
    *,
    selected_reference_role: str,
) -> dict[str, object]:
    _promotion_request, sidecar = _verify_promotion_closure(promotion)
    admitted = _verify_admitted_png(admitted_png, promotion, sidecar)
    if type(selected_reference_role) is not str:
        _fail(
            "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
            "selected_reference_role must be one exact string literal",
        )
    artifact = promotion.upstream.artifact
    profile = artifact.profile_snapshot
    purpose = cast(str, getattr(artifact.asset_purpose, "value", artifact.asset_purpose))
    roles = tuple(
        cast(str, getattr(item, "value", item)) for item in profile.reference_asset_types
    )
    expected_roles: tuple[str, ...] = (
        CHARACTER_REFERENCE_ROLE_ORDER
        if purpose == "CHARACTER_REFERENCE_ASSET"
        else SCENE_REFERENCE_ROLE_ORDER
    )
    if roles != expected_roles or selected_reference_role not in roles:
        _fail(
            "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
            "selected role is not in the exact purpose-compatible Artifact tuple",
        )
    if (
        purpose != sidecar.primary_asset_binding.asset_purpose
        or artifact.subject_id != sidecar.primary_asset_binding.subject_id
    ):
        _fail(
            "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
            "Artifact purpose/subject differs from Sidecar primary binding",
        )
    return {
        "target_profile": (
            "sdc.generated-reference-eligible-asset-role-binding-target.v1"
        ),
        "eligible_asset_sidecar_id": sidecar.sidecar_id,
        "eligible_asset_sidecar_sha256": sidecar.sidecar_sha256,
        "promotion_decision_id": sidecar.decision_id,
        "promotion_decision_sha256": sidecar.decision_sha256,
        "reference_prompt_artifact_sha256": artifact.artifact_sha256,
        "provider_attempt_outcome_id": sidecar.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": sidecar.provider_attempt_outcome_sha256,
        "candidate_id": sidecar.candidate_id,
        "candidate_sha256": sidecar.candidate_sha256,
        "output_ordinal": 0,
        "media_type": "image/png",
        "media_content_sha256": admitted.media_content_sha256,
        "media_size_bytes": admitted.media_size_bytes,
        "media_technical_record_sha256": admitted.media_technical_record_sha256,
        "asset_purpose": purpose,
        "subject_id": artifact.subject_id,
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
        "profile_sha256": profile.profile_sha256,
        "catalog_version": profile.catalog_version,
        "catalog_sha256": profile.catalog_sha256,
        "reference_asset_types": roles,
        "selected_reference_role": selected_reference_role,
        "media_binding_scope": (
            "WHOLE_UNSPLIT_UNTRANSFORMED_COMPOSITE_PNG_OCCURRENCE"
        ),
        "binding_exclusivity_asserted": False,
        "complete_role_set_asserted": False,
        "global_role_uniqueness_asserted": False,
        "crop_applied": False,
        "split_applied": False,
        "transform_applied": False,
        "derived_media_created": False,
        "provider_slot_embedded": False,
    }


def build_generated_reference_eligible_asset_role_binding_target(
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    admitted_png: GeneratedReferenceRoleBindingAdmittedPng,
    *,
    selected_reference_role: str,
) -> GeneratedReferenceEligibleAssetRoleBindingTargetV1:
    """Build one occurrence-specific target from an exact positive Sidecar and PNG."""

    values = _target_values(
        promotion,
        admitted_png,
        selected_reference_role=selected_reference_role,
    )
    digest = _semantic_sha256(
        GENERATED_REFERENCE_ROLE_BINDING_TARGET_SHA256_DOMAIN, values
    )
    try:
        target = GeneratedReferenceEligibleAssetRoleBindingTargetV1.model_validate(
            _arrays_to_tuples({"target_sha256": digest, **values})
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
            "Role-Binding target construction failed",
        ) from exc
    return cast(
        GeneratedReferenceEligibleAssetRoleBindingTargetV1,
        _exact_nested_model(
            target,
            GeneratedReferenceEligibleAssetRoleBindingTargetV1,
            field="Role-Binding target",
        ),
    )


def _verify_target_linkage(
    target: GeneratedReferenceEligibleAssetRoleBindingTargetV1,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
) -> None:
    _promotion_request, sidecar = _verify_promotion_closure(promotion)
    artifact = promotion.upstream.artifact
    expected = {
        "eligible_asset_sidecar_id": sidecar.sidecar_id,
        "eligible_asset_sidecar_sha256": sidecar.sidecar_sha256,
        "promotion_decision_id": sidecar.decision_id,
        "promotion_decision_sha256": sidecar.decision_sha256,
        "reference_prompt_artifact_sha256": artifact.artifact_sha256,
        "provider_attempt_outcome_id": sidecar.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": sidecar.provider_attempt_outcome_sha256,
        "candidate_id": sidecar.candidate_id,
        "candidate_sha256": sidecar.candidate_sha256,
        "media_content_sha256": sidecar.media_content_sha256,
        "media_size_bytes": sidecar.media_size_bytes,
        "media_technical_record_sha256": sidecar.media_technical_record_sha256,
        "asset_purpose": sidecar.primary_asset_binding.asset_purpose,
        "subject_id": sidecar.primary_asset_binding.subject_id,
    }
    if any(getattr(target, name) != value for name, value in expected.items()):
        _fail(
            "UPSTREAM_CLOSURE_MISMATCH",
            "Role-Binding target differs from exact Promotion/Sidecar occurrence",
        )


def _request_valid_until(
    *,
    requested_at: str,
    qualification_valid_until: str,
    manifest_valid_until: str,
    status_valid_until: str,
) -> str:
    try:
        requested = _parse_utc(requested_at, field="requested_at")
        upper = min(
            requested + timedelta(seconds=86_400),
            _parse_utc(
                qualification_valid_until, field="qualification_valid_until"
            ),
            _parse_utc(manifest_valid_until, field="manifest_valid_until"),
            _parse_utc(status_valid_until, field="requested_status_valid_until"),
        )
    except ValueError as exc:
        raise GeneratedReferenceRoleBindingError(
            "TIME_OR_VALIDITY_INVALID",
            "Request time or evidence deadline is not canonical UTC seconds",
        ) from exc
    if upper <= requested:
        _fail(
            "TIME_OR_VALIDITY_INVALID",
            "requested_at is at or beyond one exclusive evidence deadline",
        )
    return _format_utc(upper)


def _assemble_review_payload(
    *,
    target: GeneratedReferenceEligibleAssetRoleBindingTargetV1,
    promotion_request: CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
    sidecar: CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
    requested_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1,
    receipt: CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
    requested_at: str,
    request_valid_until: str,
) -> dict[str, object]:
    """Assemble the frozen payload from already verified stage outputs."""

    values: dict[str, object] = {
        "policy_id": GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID,
        "policy_version": GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION,
        "policy_document_sha256": GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256,
        "requested_role_binding_target": target,
        "promotion_request_id": promotion_request.request_id,
        "promotion_request_sha256": promotion_request.request_sha256,
        "promotion_decision_id": sidecar.decision_id,
        "promotion_decision_sha256": sidecar.decision_sha256,
        "eligible_asset_sidecar_id": sidecar.sidecar_id,
        "eligible_asset_sidecar_sha256": sidecar.sidecar_sha256,
        "promotion_at": sidecar.promotion_at,
        "promotion_evidence_valid_until": sidecar.promotion_evidence_valid_until,
        "qualification_request_id": sidecar.qualification_request_id,
        "qualification_request_sha256": sidecar.qualification_request_sha256,
        "qualification_decision_id": sidecar.qualification_decision_id,
        "qualification_decision_sha256": sidecar.qualification_decision_sha256,
        "qualification_valid_until": sidecar.qualification_valid_until,
        "manifest_id": sidecar.manifest_id,
        "manifest_sha256": sidecar.manifest_sha256,
        "manifest_valid_until": sidecar.manifest_valid_until,
        "reviewed_rights_scope": sidecar.reviewed_rights_scope,
        "requested_primary_asset_binding": requested_primary_asset_binding,
        "status_subject_closure_id": receipt.subject_closure.closure_id,
        "status_subject_closure_sha256": receipt.subject_closure.closure_sha256,
        "requested_status_record_id": receipt.record_id,
        "requested_status_record_sha256": receipt.record_sha256,
        "requested_status_receipt_id": receipt.receipt_id,
        "requested_status_receipt_sha256": receipt.receipt_sha256,
        "requested_explicit_chain_set_sha256": receipt.explicit_chain_set_sha256,
        "requested_coverage_set_sha256": receipt.coverage_set_sha256,
        "requested_joint_replay_sha256": receipt.joint_replay_sha256,
        "requested_as_of_assessment_sha256": receipt.as_of_assessment_sha256,
        "requested_as_of": receipt.as_of,
        "requested_as_of_status": receipt.as_of_status,
        "requested_status_valid_until": receipt.status_valid_until,
        "requested_at": requested_at,
        "request_valid_until": request_valid_until,
        "media_binding_scope": target.media_binding_scope,
        "explicit_human_role_selection": True,
        "profile_role_membership_verified": True,
        "role_binding_exclusivity_asserted": False,
        "complete_role_set_asserted": False,
        "global_role_uniqueness_asserted": False,
        "crop_requested": False,
        "split_requested": False,
        "transform_requested": False,
        "derived_media_requested": False,
        "provider_input_requested": False,
        **_zero_authority_values(),
    }
    if set(values) != set(_REVIEW_PAYLOAD_FIELDS):
        _fail("CONTRACT_FIELD_INVALID", "review payload field inventory drifted")
    return _projection(values, _REVIEW_PAYLOAD_FIELDS)


def _request_time_derivation(
    *,
    requested_at: str,
    promotion_at: str,
    qualification_valid_until: str,
    manifest_valid_until: str,
    status_valid_until: str,
) -> tuple[str | None, str | None]:
    """Derive the Request deadline without raising before the frozen time stage."""

    try:
        requested = _parse_utc(requested_at, field="requested_at")
        promotion = _parse_utc(promotion_at, field="promotion_at")
        upper = min(
            requested + timedelta(seconds=86_400),
            _parse_utc(
                qualification_valid_until, field="qualification_valid_until"
            ),
            _parse_utc(manifest_valid_until, field="manifest_valid_until"),
            _parse_utc(status_valid_until, field="requested_status_valid_until"),
        )
    except ValueError:
        return None, "Request time or one evidence deadline is not canonical UTC seconds"
    error: str | None = None
    if promotion > requested:
        error = "requested_at precedes promotion_at"
    elif upper <= requested:
        error = "requested_at is at or beyond one exclusive evidence deadline"
    return _format_utc(upper), error


def _verify_binding_time_window(
    request: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
    request_receipt: (
        CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1
    ),
    final_receipt: (
        CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1
    ),
    *,
    binding_at: str,
) -> None:
    """Enforce the exact caller-time equality and every half-open upper bound."""

    request_until, request_time_problem = _request_time_derivation(
        requested_at=request.requested_at,
        promotion_at=request.promotion_at,
        qualification_valid_until=request.qualification_valid_until,
        manifest_valid_until=request.manifest_valid_until,
        status_valid_until=request_receipt.status_valid_until,
    )
    try:
        binding_at_dt = _parse_utc(binding_at, field="binding_at")
        requested_at_dt = _parse_utc(request.requested_at, field="requested_at")
        request_until_dt = _parse_utc(
            request.request_valid_until, field="request_valid_until"
        )
    except ValueError as exc:
        raise GeneratedReferenceRoleBindingError(
            "TIME_OR_VALIDITY_INVALID", "Role-Binding time is not canonical UTC seconds"
        ) from exc
    if (
        request_time_problem is not None
        or request_until != request.request_valid_until
        or request_receipt.as_of != request.requested_at
        or final_receipt.as_of != binding_at
        or not requested_at_dt <= binding_at_dt < request_until_dt
    ):
        _fail("TIME_OR_VALIDITY_INVALID", "Role-Binding time/window closure failed")
    for name, value in (
        ("qualification_valid_until", request.qualification_valid_until),
        ("manifest_valid_until", request.manifest_valid_until),
        ("binding_status_valid_until", final_receipt.status_valid_until),
    ):
        try:
            upper = _parse_utc(value, field=name)
        except ValueError as exc:
            raise GeneratedReferenceRoleBindingError(
                "TIME_OR_VALIDITY_INVALID", f"{name} is not canonical UTC seconds"
            ) from exc
        if binding_at_dt >= upper:
            _fail("TIME_OR_VALIDITY_INVALID", f"binding_at reached exclusive {name}")


def build_generated_reference_role_binding_review_payload_projection(
    target: GeneratedReferenceEligibleAssetRoleBindingTargetV1,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1,
    *,
    requested_at: str,
) -> dict[str, object]:
    """Revalidate the Request evidence and return its digest-only review payload."""

    target = cast(
        GeneratedReferenceEligibleAssetRoleBindingTargetV1,
        _exact_nested_model(
            target,
            GeneratedReferenceEligibleAssetRoleBindingTargetV1,
            field="Role-Binding target",
        ),
    )
    promotion_request, sidecar = _verify_promotion_closure(promotion)
    _verify_target_linkage(target, promotion)
    if (
        type(requested_primary_asset_binding)
        is not GeneratedReferencePromotionPrimaryAssetBindingV1
        or generated_reference_promotion_primary_asset_binding_sha256(
            requested_primary_asset_binding
        )
        != requested_primary_asset_binding.primary_asset_binding_sha256
        or requested_primary_asset_binding != sidecar.primary_asset_binding
    ):
        _fail(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "Request primary binding does not equal the exact Sidecar binding",
        )
    receipt = _verify_status_closure(
        request_status, promotion.upstream.manifest, as_of=requested_at
    )
    _verify_status_monotonicity(promotion.final_status, request_status)
    if receipt.as_of != requested_at or receipt.as_of_status != "CURRENT":
        _fail(
            "CURRENT_STATUS_REPLAY_INVALID",
            "Request-time Receipt must be CURRENT at exact requested_at",
        )
    try:
        precedes_promotion = _parse_utc(
            sidecar.promotion_at, field="promotion_at"
        ) > _parse_utc(requested_at, field="requested_at")
    except ValueError as exc:
        raise GeneratedReferenceRoleBindingError(
            "TIME_OR_VALIDITY_INVALID",
            "review-payload time is not canonical UTC seconds",
        ) from exc
    if precedes_promotion:
        _fail("TIME_OR_VALIDITY_INVALID", "requested_at precedes promotion_at")
    request_valid_until = _request_valid_until(
        requested_at=requested_at,
        qualification_valid_until=sidecar.qualification_valid_until,
        manifest_valid_until=sidecar.manifest_valid_until,
        status_valid_until=receipt.status_valid_until,
    )
    values: dict[str, object] = {
        "policy_id": GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID,
        "policy_version": GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION,
        "policy_document_sha256": GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256,
        "requested_role_binding_target": target,
        "promotion_request_id": promotion_request.request_id,
        "promotion_request_sha256": promotion_request.request_sha256,
        "promotion_decision_id": sidecar.decision_id,
        "promotion_decision_sha256": sidecar.decision_sha256,
        "eligible_asset_sidecar_id": sidecar.sidecar_id,
        "eligible_asset_sidecar_sha256": sidecar.sidecar_sha256,
        "promotion_at": sidecar.promotion_at,
        "promotion_evidence_valid_until": sidecar.promotion_evidence_valid_until,
        "qualification_request_id": sidecar.qualification_request_id,
        "qualification_request_sha256": sidecar.qualification_request_sha256,
        "qualification_decision_id": sidecar.qualification_decision_id,
        "qualification_decision_sha256": sidecar.qualification_decision_sha256,
        "qualification_valid_until": sidecar.qualification_valid_until,
        "manifest_id": sidecar.manifest_id,
        "manifest_sha256": sidecar.manifest_sha256,
        "manifest_valid_until": sidecar.manifest_valid_until,
        "reviewed_rights_scope": sidecar.reviewed_rights_scope,
        "requested_primary_asset_binding": requested_primary_asset_binding,
        "status_subject_closure_id": receipt.subject_closure.closure_id,
        "status_subject_closure_sha256": receipt.subject_closure.closure_sha256,
        "requested_status_record_id": receipt.record_id,
        "requested_status_record_sha256": receipt.record_sha256,
        "requested_status_receipt_id": receipt.receipt_id,
        "requested_status_receipt_sha256": receipt.receipt_sha256,
        "requested_explicit_chain_set_sha256": receipt.explicit_chain_set_sha256,
        "requested_coverage_set_sha256": receipt.coverage_set_sha256,
        "requested_joint_replay_sha256": receipt.joint_replay_sha256,
        "requested_as_of_assessment_sha256": receipt.as_of_assessment_sha256,
        "requested_as_of": receipt.as_of,
        "requested_as_of_status": receipt.as_of_status,
        "requested_status_valid_until": receipt.status_valid_until,
        "requested_at": requested_at,
        "request_valid_until": request_valid_until,
        "media_binding_scope": target.media_binding_scope,
        "explicit_human_role_selection": True,
        "profile_role_membership_verified": True,
        "role_binding_exclusivity_asserted": False,
        "complete_role_set_asserted": False,
        "global_role_uniqueness_asserted": False,
        "crop_requested": False,
        "split_requested": False,
        "transform_requested": False,
        "derived_media_requested": False,
        "provider_input_requested": False,
        **_zero_authority_values(),
    }
    if set(values) != set(_REVIEW_PAYLOAD_FIELDS):
        _fail("CONTRACT_FIELD_INVALID", "review payload field inventory drifted")
    return _projection(values, _REVIEW_PAYLOAD_FIELDS)


def build_generated_reference_role_binding_review_payload_sha256(
    target: GeneratedReferenceEligibleAssetRoleBindingTargetV1,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1,
    *,
    requested_at: str,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
        build_generated_reference_role_binding_review_payload_projection(
            target,
            promotion,
            request_status,
            requested_primary_asset_binding,
            requested_at=requested_at,
        ),
    )


def _admit_retained_json(raw: bytes, *, maximum: int, field: str) -> dict[str, object]:
    if type(raw) is not bytes:
        _fail("CONTRACT_FIELD_INVALID", f"{field} must be exact bytes")
    if not 1 <= len(raw) <= maximum:
        _fail("INPUT_RESOURCE_LIMIT_EXCEEDED", f"{field} exceeds byte limits")
    if (
        raw.startswith(b"\xef\xbb\xbf")
        or b"\r" in raw
        or not raw.endswith(b"\n")
        or raw.endswith(b"\n\n")
    ):
        _fail("INPUT_DOCUMENT_INVALID", f"{field} is not canonical persistent JSON")
    try:
        parsed = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_json_no_duplicates,
            parse_constant=lambda item: _invalid(f"non-finite number: {item}"),
        )
        _validate_json_tree(parsed)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "INPUT_DOCUMENT_INVALID", f"{field} is invalid canonical JSON"
        ) from exc
    if type(parsed) is not dict or _persistent_json(parsed) != raw:
        _fail("INPUT_DOCUMENT_INVALID", f"{field} is not exact canonical object bytes")
    return cast(dict[str, object], parsed)


def _human_identity(raw: bytes, *, field: str) -> tuple[tuple[str, str], str]:
    value = _admit_retained_json(raw, maximum=_MAX_HUMAN_IDENTITY_BYTES, field=field)
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


_MAKER_ACTION_FIELDS = frozenset(
    {
        "document_profile",
        "action",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "role_binding_review_payload_sha256",
        "target_sha256",
        "selected_reference_role",
        "requested_primary_asset_binding_sha256",
        "requested_status_receipt_sha256",
        "actor_ref_sha256",
        "prepared_at",
        "request_basis",
    }
)
_CHECKER_ACTION_FIELDS = frozenset(
    {
        "document_profile",
        "action",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "request_id",
        "request_sha256",
        "target_sha256",
        "selected_reference_role",
        "final_status_receipt_sha256",
        "final_primary_asset_binding_sha256",
        "actor_ref_sha256",
        "reviewed_at",
        "exact_role_and_reviewed_rights_scope_presented_without_expansion_result",
        "exact_role_and_reviewed_rights_scope_presented_without_expansion_basis",
        "whole_composite_role_suitability_result",
        "whole_composite_role_suitability_basis",
        "non_exclusive_no_transform_boundary_result",
        "non_exclusive_no_transform_boundary_basis",
        "gate_results",
        "binding_issue_codes",
        "decision_basis",
        "decision",
        "binding_materialization_allowed",
    }
)


def _preflight_retained_resource_limits(
    records: Sequence[tuple[object, int, str]],
) -> None:
    """Evaluate every applicable retained-byte resource limit before type errors."""

    for raw, maximum, field in records:
        if type(raw) is bytes and not 1 <= len(raw) <= maximum:
            _fail("INPUT_RESOURCE_LIMIT_EXCEEDED", f"{field} exceeds byte limits")


def _preflight_retained_documents(
    records: Sequence[tuple[object, int, str]],
) -> dict[str, dict[str, object]]:
    """Evaluate document syntax before later exact-type/field checks."""

    parsed: dict[str, dict[str, object]] = {}
    for raw, maximum, field in records:
        if type(raw) is bytes:
            parsed[field] = _admit_retained_json(raw, maximum=maximum, field=field)
    return parsed


def _require_exact_bytes(value: object, *, field: str) -> bytes:
    if type(value) is not bytes:
        _fail("CONTRACT_FIELD_INVALID", f"{field} must be exact bytes")
    return value


def _preflight_sha_field(value: object, *, field: str) -> None:
    if type(value) is not str or re.fullmatch(_LOWER_SHA256_PATTERN, value) is None:
        _fail("CONTRACT_FIELD_INVALID", f"{field} must be one lower SHA-256")


def _preflight_portable_field(value: object, *, field: str) -> None:
    if type(value) is not str or re.fullmatch(_PORTABLE_ID_PATTERN, value) is None:
        _fail("CONTRACT_FIELD_INVALID", f"{field} must be one portable identifier")


def _preflight_bounded_text(value: object, *, field: str) -> str:
    if type(value) is not str:
        _fail("CONTRACT_FIELD_INVALID", f"{field} must be an exact string")
    try:
        return _human_text(value, field=field)
    except ValueError as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", f"{field} is not bounded canonical text"
        ) from exc


def _preflight_action_common(
    value: Mapping[str, object], *, expected_fields: frozenset[str], field: str
) -> None:
    if set(value) != expected_fields:
        _fail("CONTRACT_FIELD_INVALID", f"{field} field inventory drifted")
    for name in (
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "selected_reference_role",
    ):
        if type(value.get(name)) is not str:
            _fail("CONTRACT_FIELD_INVALID", f"{field} {name} must be an exact string")


def _preflight_maker_action_structure(value: Mapping[str, object]) -> None:
    field = "Role-Binding Maker action"
    _preflight_action_common(value, expected_fields=_MAKER_ACTION_FIELDS, field=field)
    if (
        value.get("document_profile")
        != "sdc.generated-reference-eligible-asset-role-binding-request-preparation-action.v1"
        or value.get("action")
        != "PREPARED_GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_REQUEST"
    ):
        _fail("CONTRACT_FIELD_INVALID", f"{field} profile/action literal drifted")
    for name in (
        "role_binding_review_payload_sha256",
        "target_sha256",
        "requested_primary_asset_binding_sha256",
        "requested_status_receipt_sha256",
        "actor_ref_sha256",
    ):
        _preflight_sha_field(value.get(name), field=f"{field} {name}")
    if type(value.get("prepared_at")) is not str:
        _fail("CONTRACT_FIELD_INVALID", f"{field} prepared_at must be an exact string")
    _preflight_bounded_text(value.get("request_basis"), field=f"{field} request_basis")


def _preflight_checker_action_structure(value: Mapping[str, object]) -> None:
    field = "Role-Binding Checker action"
    _preflight_action_common(value, expected_fields=_CHECKER_ACTION_FIELDS, field=field)
    if (
        value.get("document_profile")
        != "sdc.generated-reference-eligible-asset-role-binding-decision-action.v1"
        or value.get("action")
        != "RECORDED_GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_DECISION"
    ):
        _fail("CONTRACT_FIELD_INVALID", f"{field} profile/action literal drifted")
    _preflight_portable_field(value.get("request_id"), field=f"{field} request_id")
    for name in (
        "request_sha256",
        "target_sha256",
        "final_status_receipt_sha256",
        "final_primary_asset_binding_sha256",
        "actor_ref_sha256",
    ):
        _preflight_sha_field(value.get(name), field=f"{field} {name}")
    if type(value.get("reviewed_at")) is not str:
        _fail("CONTRACT_FIELD_INVALID", f"{field} reviewed_at must be an exact string")
    for name in (
        "exact_role_and_reviewed_rights_scope_presented_without_expansion_result",
        "whole_composite_role_suitability_result",
        "non_exclusive_no_transform_boundary_result",
    ):
        if value.get(name) not in {"PASS", "FAIL", "INDETERMINATE"}:
            _fail("CONTRACT_FIELD_INVALID", f"{field} {name} literal is invalid")
    for name in (
        "exact_role_and_reviewed_rights_scope_presented_without_expansion_basis",
        "whole_composite_role_suitability_basis",
        "non_exclusive_no_transform_boundary_basis",
        "decision_basis",
    ):
        _preflight_bounded_text(value.get(name), field=f"{field} {name}")
    raw_gates = value.get("gate_results")
    if type(raw_gates) is not list or len(raw_gates) != 12:
        _fail("CONTRACT_FIELD_INVALID", f"{field} gate_results shape drifted")
    try:
        gates = tuple(
            GeneratedReferenceRoleBindingGateResultV1.model_validate(
                _arrays_to_tuples(item)
            )
            for item in cast(list[object], raw_gates)
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", f"{field} gate_results are structurally invalid"
        ) from exc
    if tuple(item.ordinal for item in gates) != tuple(range(12)):
        _fail("CONTRACT_FIELD_INVALID", f"{field} gate order drifted")
    raw_issues = value.get("binding_issue_codes")
    if type(raw_issues) is not list or len(raw_issues) > 5 or any(
        type(item) is not str or item not in ROLE_BINDING_ISSUE_CODE_ORDER
        for item in cast(list[object], raw_issues)
    ):
        _fail("CONTRACT_FIELD_INVALID", f"{field} issue tuple is structurally invalid")
    if value.get("decision") not in {
        "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
        "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
        "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING",
    } or type(value.get("binding_materialization_allowed")) is not bool:
        _fail("CONTRACT_FIELD_INVALID", f"{field} decision fields are structurally invalid")


def _verify_retained_action_policy(
    maker_action: Mapping[str, object],
    checker_action: Mapping[str, object] | None = None,
) -> None:
    _verify_policy_identity()
    actions: list[tuple[Mapping[str, object], str]] = [
        (maker_action, "Role-Binding Maker action")
    ]
    if checker_action is not None:
        actions.append((checker_action, "Role-Binding Checker action"))
    for value, field in actions:
        if (
            value.get("policy_id") != GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID
            or value.get("policy_version")
            != GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION
            or value.get("policy_document_sha256")
            != GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256
        ):
            _fail("POLICY_IDENTITY_MISMATCH", f"{field} policy identity drifted")


def _exact_action(raw: bytes, expected: Mapping[str, object], *, field: str) -> str:
    actual = _admit_retained_json(
        raw, maximum=_MAX_RETAINED_RECORD_BYTES, field=field
    )
    if actual != expected or _compact_json(actual) != _compact_json(dict(expected)):
        _fail("ACTION_RECORD_INVALID", f"{field} does not close the exact action")
    return _raw_sha256(raw)


def _collect_sha256_strings(value: object, *, seen: set[int] | None = None) -> set[str]:
    if seen is None:
        seen = set()
    if type(value) is str:
        text = value
        return {text} if re.fullmatch(_LOWER_SHA256_PATTERN, text) else set()
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
        for item in cast(Sequence[object], value):
            result.update(_collect_sha256_strings(item, seen=seen))
    elif type(value) is dict:
        for item in cast(dict[object, object], value).values():
            result.update(_collect_sha256_strings(item, seen=seen))
    return result


def _without_role_binding_action_digest_anchors(
    value: Mapping[str, object] | None,
) -> dict[str, object] | None:
    """Remove only self-referential Role-Binding action anchors from one surface."""

    if value is None:
        return None
    return {
        name: item
        for name, item in value.items()
        if name not in {"maker_action_sha256", "checker_action_sha256"}
    }


def _action_time(value: str, *, field: str) -> str:
    try:
        _parse_utc(value, field=field)
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "ACTION_RECORD_INVALID", f"{field} is not canonical UTC seconds"
        ) from exc
    return value


def _action_basis(value: str, *, field: str) -> str:
    try:
        return _human_text(value, field=field)
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "ACTION_RECORD_INVALID", f"{field} is not bounded canonical text"
        ) from exc


def generated_reference_role_binding_maker_action_projection(
    *,
    actor_ref_sha256: str,
    role_binding_review_payload_sha256: str,
    target_sha256: str,
    selected_reference_role: str,
    requested_primary_asset_binding_sha256: str,
    requested_status_receipt_sha256: str,
    prepared_at: str,
    request_basis: str,
) -> dict[str, object]:
    for name, value in (
        ("actor_ref_sha256", actor_ref_sha256),
        ("role_binding_review_payload_sha256", role_binding_review_payload_sha256),
        ("target_sha256", target_sha256),
        (
            "requested_primary_asset_binding_sha256",
            requested_primary_asset_binding_sha256,
        ),
        ("requested_status_receipt_sha256", requested_status_receipt_sha256),
    ):
        if type(value) is not str or re.fullmatch(_LOWER_SHA256_PATTERN, value) is None:
            _fail("ACTION_RECORD_INVALID", f"Maker action {name} is not one lower SHA")
    if type(selected_reference_role) is not str or selected_reference_role not in (
        *CHARACTER_REFERENCE_ROLE_ORDER,
        *SCENE_REFERENCE_ROLE_ORDER,
    ):
        _fail("ACTION_RECORD_INVALID", "Maker action selected role is invalid")
    _action_time(prepared_at, field="prepared_at")
    basis = _action_basis(request_basis, field="request_basis")
    return {
        "document_profile": (
            "sdc.generated-reference-eligible-asset-role-binding-request-preparation-action.v1"
        ),
        "action": (
            "PREPARED_GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_REQUEST"
        ),
        "policy_id": GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID,
        "policy_version": GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION,
        "policy_document_sha256": GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256,
        "role_binding_review_payload_sha256": role_binding_review_payload_sha256,
        "target_sha256": target_sha256,
        "selected_reference_role": selected_reference_role,
        "requested_primary_asset_binding_sha256": (
            requested_primary_asset_binding_sha256
        ),
        "requested_status_receipt_sha256": requested_status_receipt_sha256,
        "actor_ref_sha256": actor_ref_sha256,
        "prepared_at": prepared_at,
        "request_basis": basis,
    }


def _preflight_status_closure_structure(
    closure: GeneratedReferenceAssetPromotionStatusClosureInput, *, field: str
) -> None:
    for value, expected, name in (
        (
            closure.subject_closure,
            GeneratedReferenceCurrentStatusSubjectClosureV1,
            "Subject Closure",
        ),
        (closure.request, CreativeSampleGeneratedReferenceCurrentStatusRequestV1, "Request"),
        (
            closure.instruction,
            CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
            "Instruction",
        ),
        (closure.decision, CreativeSampleGeneratedReferenceCurrentStatusDecisionV1, "Decision"),
        (
            closure.record,
            CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
            "Record",
        ),
        (
            closure.receipt,
            CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
            "Receipt",
        ),
    ):
        if type(value) is not expected:
            _fail("CONTRACT_FIELD_INVALID", f"{field} Status {name} type mismatch")
    if type(closure.chain_inputs) is not tuple or any(
        type(item) is not GeneratedReferenceCurrentStatusExplicitChainInput
        for item in closure.chain_inputs
    ):
        _fail("CONTRACT_FIELD_INVALID", f"{field} Status chain_inputs type mismatch")
    for raw, name in (
        (closure.status_preparer_identity_bytes, "Status Preparer identity"),
        (closure.status_preparer_action_bytes, "Status Preparer action"),
        (closure.status_checker_identity_bytes, "Status Checker identity"),
        (closure.status_checker_action_bytes, "Status Checker action"),
    ):
        if type(raw) is not bytes:
            _fail("CONTRACT_FIELD_INVALID", f"{field} {name} must be exact bytes")


def _preflight_prepare_stage_inputs(
    promotion: object,
    request_status: object,
    requested_primary_bible: object,
    requested_primary_asset_version: object,
    admitted_png: object,
    *,
    selected_reference_role: object,
    maker_identity_bytes: object,
    maker_action_bytes: object,
    requested_at: object,
    request_basis: object,
    expected_request: object | None = None,
) -> tuple[
    dict[str, object],
    tuple[str, str],
    str,
    dict[str, object] | None,
]:
    """Run Request resource/document/contract/policy stages in exact order."""

    records = (
        (maker_identity_bytes, _MAX_HUMAN_IDENTITY_BYTES, "Role-Binding Maker identity"),
        (maker_action_bytes, _MAX_RETAINED_RECORD_BYTES, "Role-Binding Maker action"),
    )
    _preflight_retained_resource_limits(records)
    if type(admitted_png) is GeneratedReferenceRoleBindingAdmittedPng:
        raw = admitted_png.png_bytes
        if type(raw) is bytes and not 1 <= len(raw) <= _MAX_PNG_BYTES:
            _fail("INPUT_RESOURCE_LIMIT_EXCEEDED", "admitted PNG exceeds byte limits")
    _preflight_formal_resource_limit(
        expected_request,
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
        field="expected Role-Binding Request",
    )
    expected_values: dict[str, object] | None = None
    if type(expected_request) is (
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1
    ):
        expected_values = _verify_formal_resource(
            expected_request,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
            field="expected Role-Binding Request",
        )
    parsed = _preflight_retained_documents(records)

    if expected_request is not None and expected_values is None:
        _fail(
            "CONTRACT_FIELD_INVALID",
            "expected Role-Binding Request has the wrong exact type",
        )
    if type(promotion) is not GeneratedReferenceRoleBindingPromotionClosureInput:
        _fail("CONTRACT_FIELD_INVALID", "Promotion closure has the wrong process type")
    if type(request_status) is not GeneratedReferenceAssetPromotionStatusClosureInput:
        _fail("CONTRACT_FIELD_INVALID", "request-time status closure type mismatch")
    _preflight_status_closure_structure(request_status, field="request-time")
    if (
        type(requested_primary_bible) is not CharacterBible
        and type(requested_primary_bible) is not SceneBible
    ):
        _fail("CONTRACT_FIELD_INVALID", "request-time Bible has the wrong exact type")
    if (
        type(requested_primary_asset_version) is not CharacterAssetVersion
        and type(requested_primary_asset_version) is not SceneAssetVersion
    ):
        _fail(
            "CONTRACT_FIELD_INVALID",
            "request-time AssetVersion has the wrong exact type",
        )
    if type(admitted_png) is not GeneratedReferenceRoleBindingAdmittedPng:
        _fail("CONTRACT_FIELD_INVALID", "admitted_png has the wrong process type")
    if type(selected_reference_role) is not str:
        _fail("CONTRACT_FIELD_INVALID", "selected_reference_role must be exact str")
    maker_identity_raw = _require_exact_bytes(
        maker_identity_bytes, field="Role-Binding Maker identity"
    )
    _require_exact_bytes(maker_action_bytes, field="Role-Binding Maker action")
    if type(requested_at) is not str:
        _fail("CONTRACT_FIELD_INVALID", "requested_at must be an exact string")
    _preflight_bounded_text(request_basis, field="request_basis")
    maker_tuple, maker_sha = _human_identity(
        maker_identity_raw, field="Role-Binding Maker identity"
    )
    maker_action = parsed["Role-Binding Maker action"]
    _preflight_maker_action_structure(maker_action)
    if expected_values is not None:
        try:
            _sanitize_formal_structure(
                expected_values,
                CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
            )
        except GeneratedReferenceRoleBindingError:
            raise
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise GeneratedReferenceRoleBindingError(
                "CONTRACT_FIELD_INVALID",
                "expected Role-Binding Request structure is invalid",
            ) from exc
    _verify_retained_action_policy(maker_action)
    if expected_values is not None:
        _verify_policy_fields(expected_values, field="expected Role-Binding Request")
        _verify_formal_identity(
            expected_values,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
            field="expected Role-Binding Request",
        )
    return maker_action, maker_tuple, maker_sha, expected_values


_REQUEST_PREDECESSOR_LINK_FIELDS = (
    "promotion_request_id",
    "promotion_request_sha256",
    "promotion_decision_id",
    "promotion_decision_sha256",
    "eligible_asset_sidecar_id",
    "eligible_asset_sidecar_sha256",
    "promotion_at",
    "promotion_evidence_valid_until",
    "qualification_request_id",
    "qualification_request_sha256",
    "qualification_decision_id",
    "qualification_decision_sha256",
    "qualification_valid_until",
    "manifest_id",
    "manifest_sha256",
    "manifest_valid_until",
)

_REQUEST_STATUS_LINK_FIELDS = (
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
)

_TARGET_PREDECESSOR_LINK_FIELDS = (
    "eligible_asset_sidecar_id",
    "eligible_asset_sidecar_sha256",
    "promotion_decision_id",
    "promotion_decision_sha256",
    "reference_prompt_artifact_sha256",
    "provider_attempt_outcome_id",
    "provider_attempt_outcome_sha256",
    "candidate_id",
    "candidate_sha256",
    "media_content_sha256",
    "media_size_bytes",
    "media_technical_record_sha256",
    "asset_purpose",
    "subject_id",
)


def _verify_expected_request_predecessor_linkage(
    expected: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
) -> None:
    """Close cheap copied predecessor fields before full released replay."""

    comparisons: dict[str, object] = {}
    if type(promotion.request) is CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        comparisons.update(
            {
                "promotion_request_id": promotion.request.request_id,
                "promotion_request_sha256": promotion.request.request_sha256,
            }
        )
    raw_sidecar = (
        promotion.result.sidecar
        if type(promotion.result) is GeneratedReferenceAssetPromotionFinalizationResult
        else None
    )
    if type(raw_sidecar) is CreativeSampleGeneratedReferenceEligibleAssetSidecarV1:
        comparisons.update(
            {
                "promotion_decision_id": raw_sidecar.decision_id,
                "promotion_decision_sha256": raw_sidecar.decision_sha256,
                "eligible_asset_sidecar_id": raw_sidecar.sidecar_id,
                "eligible_asset_sidecar_sha256": raw_sidecar.sidecar_sha256,
                "promotion_at": raw_sidecar.promotion_at,
                "promotion_evidence_valid_until": (
                    raw_sidecar.promotion_evidence_valid_until
                ),
                "qualification_request_id": raw_sidecar.qualification_request_id,
                "qualification_request_sha256": raw_sidecar.qualification_request_sha256,
                "qualification_decision_id": raw_sidecar.qualification_decision_id,
                "qualification_decision_sha256": (
                    raw_sidecar.qualification_decision_sha256
                ),
                "qualification_valid_until": raw_sidecar.qualification_valid_until,
                "manifest_id": raw_sidecar.manifest_id,
                "manifest_sha256": raw_sidecar.manifest_sha256,
                "manifest_valid_until": raw_sidecar.manifest_valid_until,
            }
        )
    if any(getattr(expected, name) != value for name, value in comparisons.items()):
        _fail(
            "UPSTREAM_CLOSURE_MISMATCH",
            "expected Role-Binding Request differs from supplied predecessor fields",
        )


def _prepare_generated_reference_eligible_asset_role_binding_request_workflow(
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_bible: CharacterBible | SceneBible,
    requested_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    admitted_png: GeneratedReferenceRoleBindingAdmittedPng,
    *,
    selected_reference_role: str,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    requested_at: str,
    request_basis: str,
    defer_prohibited: bool,
    expected_request_linkage: (
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1 | None
    ) = None,
) -> CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1:
    """Purely construct one Request after complete Promotion and fresh-status replay."""

    maker_action, _maker_tuple, maker_identity_sha, _expected_values = (
        _preflight_prepare_stage_inputs(
            promotion,
            request_status,
            requested_primary_bible,
            requested_primary_asset_version,
            admitted_png,
            selected_reference_role=selected_reference_role,
            maker_identity_bytes=maker_identity_bytes,
            maker_action_bytes=maker_action_bytes,
            requested_at=requested_at,
            request_basis=request_basis,
        )
    )
    # Stages 6-7: close verifier-owned copied fields before retaining nested
    # released errors from the exact positive Promotion/Sidecar replay.
    if expected_request_linkage is not None:
        _verify_expected_request_predecessor_linkage(
            expected_request_linkage, promotion
        )
    promotion_request, sidecar = _verify_promotion_closure(promotion)

    # Stage 8: exact admitted whole PNG occurrence.
    admitted = _verify_admitted_png(admitted_png, promotion, sidecar)

    # Stage 9: exact purpose-compatible Profile membership and target.
    target = build_generated_reference_eligible_asset_role_binding_target(
        promotion,
        admitted,
        selected_reference_role=selected_reference_role,
    )
    if (
        expected_request_linkage is not None
        and expected_request_linkage.requested_role_binding_target != target
    ):
        _fail(
            "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
            "expected Request target differs from the exact rebuilt target",
        )

    # Stage 10: reconstruct and close the exact Sidecar primary binding.
    try:
        primary = build_generated_reference_promotion_primary_asset_binding(
            requested_primary_bible, requested_primary_asset_version
        )
    except GeneratedReferenceAssetPromotionError as exc:
        raise GeneratedReferenceRoleBindingError(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "Request primary binding reconstruction failed",
        ) from exc
    if primary != sidecar.primary_asset_binding:
        _fail(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "Request primary binding differs from exact Sidecar binding",
        )
    if (
        expected_request_linkage is not None
        and expected_request_linkage.requested_primary_asset_binding != primary
    ):
        _fail(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "expected Request primary binding differs from reconstruction",
        )

    # Stage 11: replay at the Receipt's own explicit as_of, then prove the first
    # Promotion-final -> Request-time monotonic transition.  Caller-time equality
    # remains deliberately deferred to stage 15.
    receipt = _verify_status_closure(
        request_status,
        promotion.upstream.manifest,
        as_of=request_status.receipt.as_of,
    )
    _verify_status_monotonicity(promotion.final_status, request_status)
    if receipt.as_of_status != "CURRENT":
        _fail(
            "CURRENT_STATUS_REPLAY_INVALID",
            "Request-time same-call replay must produce CURRENT",
        )
    if expected_request_linkage is not None:
        expected_status = {
            "status_subject_closure_id": receipt.subject_closure.closure_id,
            "status_subject_closure_sha256": receipt.subject_closure.closure_sha256,
            "requested_status_record_id": receipt.record_id,
            "requested_status_record_sha256": receipt.record_sha256,
            "requested_status_receipt_id": receipt.receipt_id,
            "requested_status_receipt_sha256": receipt.receipt_sha256,
            "requested_explicit_chain_set_sha256": receipt.explicit_chain_set_sha256,
            "requested_coverage_set_sha256": receipt.coverage_set_sha256,
            "requested_joint_replay_sha256": receipt.joint_replay_sha256,
            "requested_as_of_assessment_sha256": receipt.as_of_assessment_sha256,
            "requested_as_of": receipt.as_of,
            "requested_as_of_status": receipt.as_of_status,
            "requested_status_valid_until": receipt.status_valid_until,
        }
        if any(
            getattr(expected_request_linkage, name) != value
            for name, value in expected_status.items()
        ):
            _fail(
                "CURRENT_STATUS_REPLAY_INVALID",
                "expected Request status evidence differs from replay",
            )

    # Stage 12: reviewed Rights scope is copied exactly without reinterpretation.
    if sidecar.reviewed_rights_scope != promotion.upstream.manifest.reviewed_rights_scope:
        _fail("RIGHTS_SCOPE_MISMATCH", "Promotion/Manifest Rights scope drifted")
    if (
        expected_request_linkage is not None
        and expected_request_linkage.reviewed_rights_scope
        != sidecar.reviewed_rights_scope
    ):
        _fail("RIGHTS_SCOPE_MISMATCH", "expected Request Rights scope drifted")

    # Stage 13: any repeated identity-record raw digest must preserve exact bytes.
    _verify_identity_raw_digest_collisions(
        _preparation_identity_records(
            promotion=promotion,
            request_status=request_status,
            maker_identity_bytes=maker_identity_bytes,
        )
    )

    request_valid_until, time_problem = _request_time_derivation(
        requested_at=requested_at,
        promotion_at=sidecar.promotion_at,
        qualification_valid_until=sidecar.qualification_valid_until,
        manifest_valid_until=sidecar.manifest_valid_until,
        status_valid_until=receipt.status_valid_until,
    )

    # Stage 14: exact Maker action.  A syntactically invalid caller time cannot
    # produce a review payload; its already structurally admitted action is then
    # followed by the deterministic stage-15 time failure.
    review_payload: dict[str, object] | None = None
    review_sha: str | None = None
    maker_action_sha = _raw_sha256(maker_action_bytes)
    if request_valid_until is not None:
        review_payload = _assemble_review_payload(
            target=target,
            promotion_request=promotion_request,
            sidecar=sidecar,
            requested_primary_asset_binding=primary,
            receipt=receipt,
            requested_at=requested_at,
            request_valid_until=request_valid_until,
        )
        review_sha = _semantic_sha256(
            GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
            review_payload,
        )
        expected_action = generated_reference_role_binding_maker_action_projection(
            actor_ref_sha256=maker_identity_sha,
            role_binding_review_payload_sha256=review_sha,
            target_sha256=target.target_sha256,
            selected_reference_role=target.selected_reference_role,
            requested_primary_asset_binding_sha256=(
                primary.primary_asset_binding_sha256
            ),
            requested_status_receipt_sha256=receipt.receipt_sha256,
            prepared_at=requested_at,
            request_basis=request_basis,
        )
        maker_action_sha = _exact_action(
            maker_action_bytes,
            expected_action,
            field="Role-Binding Maker action",
        )
    else:
        partial_expected = {
            "document_profile": (
                "sdc.generated-reference-eligible-asset-role-binding-request-preparation-action.v1"
            ),
            "action": (
                "PREPARED_GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_REQUEST"
            ),
            "policy_id": GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID,
            "policy_version": GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION,
            "policy_document_sha256": (
                GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256
            ),
            "target_sha256": target.target_sha256,
            "selected_reference_role": target.selected_reference_role,
            "requested_primary_asset_binding_sha256": (
                primary.primary_asset_binding_sha256
            ),
            "requested_status_receipt_sha256": receipt.receipt_sha256,
            "actor_ref_sha256": maker_identity_sha,
            "prepared_at": requested_at,
            "request_basis": request_basis,
        }
        if any(maker_action.get(name) != value for name, value in partial_expected.items()):
            _fail(
                "ACTION_RECORD_INVALID",
                "Role-Binding Maker action fields drift before caller-time validation",
            )
    if expected_request_linkage is not None and (
        expected_request_linkage.maker_identity_ref_sha256 != maker_identity_sha
        or expected_request_linkage.maker_action_sha256 != maker_action_sha
    ):
        _fail(
            "ACTION_RECORD_INVALID",
            "expected Request Maker identity or action anchor drifted",
        )
    occupied = _collect_sha256_strings(
        (
            promotion,
            request_status,
            requested_primary_bible,
            requested_primary_asset_version,
            admitted,
            target,
            review_sha,
            maker_identity_bytes,
            maker_action,
        )
    )
    if maker_action_sha in occupied:
        _fail(
            "ACTION_RECORD_INVALID",
            "Role-Binding Maker action digest aliases evidence or formal identity",
        )

    request_values_candidate: dict[str, object] | None = None
    if review_payload is not None and review_sha is not None:
        request_values_candidate = {
            "schema_version": "1.0.0",
            "document_type": (
                "sdc.creative-sample-generated-reference-eligible-asset-role-binding-request-v1"
            ),
            "request_scope": (
                "GENERATED_REFERENCE_ELIGIBLE_ASSET_SINGLE_ROLE_BINDING_ONLY"
            ),
            "role_binding_review_payload_sha256": review_sha,
            **review_payload,
            "maker_identity_ref_sha256": maker_identity_sha,
            "maker_action_sha256": maker_action_sha,
            "maker_prepared_at": requested_at,
            "request_basis": request_basis,
            "role_binding_performed": False,
            "binding_materialized": False,
            "provider_input_eligible": False,
            "status": "GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_REQUESTED",
            "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
        }
        try:
            request_candidate = cast(
                CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
                _build_identity_with_deferred_boundary(
                    CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
                    request_values_candidate,
                ),
            )
        except GeneratedReferenceRoleBindingError:
            request_candidate = None
        if (
            request_candidate is not None
            and maker_action_sha == request_candidate.request_sha256
        ):
            _fail(
                "ACTION_RECORD_INVALID",
                "Role-Binding Maker action digest aliases the Request semantic identity",
            )

    # Stage 15: caller time, Receipt equality and the exact half-open deadline.
    if receipt.as_of != requested_at:
        time_problem = "Request-time Receipt as_of differs from requested_at"
    if time_problem is not None or request_valid_until is None:
        _fail(
            "TIME_OR_VALIDITY_INVALID",
            time_problem or "Request time derivation failed",
        )
    if review_payload is None or review_sha is None:  # pragma: no cover - closed above
        _fail("TIME_OR_VALIDITY_INVALID", "Request review payload time closure failed")

    # Stages 16-17: a constructor has no supplied formal authority surface, but
    # every retained portable value must still remain disconnected from paths,
    # URLs, credentials and Provider/Runtime fields.
    if not defer_prohibited:
        _verify_no_prohibited_connection(
            {
                "maker_identity": _admit_retained_json(
                    maker_identity_bytes,
                    maximum=_MAX_HUMAN_IDENTITY_BYTES,
                    field="Role-Binding Maker identity",
                ),
                "maker_action": maker_action,
                "request_basis": request_basis,
            },
            field="Role-Binding Request inputs",
        )

    if request_values_candidate is None:  # pragma: no cover - closed at stage 15
        _fail("TIME_OR_VALIDITY_INVALID", "Request semantic candidate is unavailable")
    values = request_values_candidate
    identity_builder = (
        _build_identity_with_deferred_boundary if defer_prohibited else _build_identity
    )
    built = cast(
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
        identity_builder(
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
            values,
        ),
    )
    if maker_action_sha == built.request_sha256:
        _fail(
            "ACTION_RECORD_INVALID",
            "Role-Binding Maker action digest aliases the Request semantic identity",
        )
    return built


def prepare_generated_reference_eligible_asset_role_binding_request(
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_bible: CharacterBible | SceneBible,
    requested_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    admitted_png: GeneratedReferenceRoleBindingAdmittedPng,
    *,
    selected_reference_role: str,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    requested_at: str,
    request_basis: str,
) -> CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1:
    """Purely construct one Request after complete staged closure validation."""

    return _prepare_generated_reference_eligible_asset_role_binding_request_workflow(
        promotion,
        request_status,
        requested_primary_bible,
        requested_primary_asset_version,
        admitted_png,
        selected_reference_role=selected_reference_role,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        requested_at=requested_at,
        request_basis=request_basis,
        defer_prohibited=False,
    )


def verify_generated_reference_eligible_asset_role_binding_request(
    expected: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_bible: CharacterBible | SceneBible,
    requested_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    admitted_png: GeneratedReferenceRoleBindingAdmittedPng,
    *,
    selected_reference_role: str,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
) -> CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1:
    """Freshly rebuild the complete Request and require value and byte equality."""

    _maker_action, _maker_tuple, _maker_sha, original = (
        _preflight_prepare_stage_inputs(
            promotion,
            request_status,
            requested_primary_bible,
            requested_primary_asset_version,
            admitted_png,
            selected_reference_role=selected_reference_role,
            maker_identity_bytes=maker_identity_bytes,
            maker_action_bytes=maker_action_bytes,
            requested_at=getattr(expected, "requested_at", None),
            request_basis=getattr(expected, "request_basis", None),
            expected_request=expected,
        )
    )
    if original is None:  # pragma: no cover - closed by the combined preflight
        _fail("CONTRACT_FIELD_INVALID", "expected Role-Binding Request is unavailable")
    validated_expected = expected
    rebuilt = _prepare_generated_reference_eligible_asset_role_binding_request_workflow(
        promotion,
        request_status,
        requested_primary_bible,
        requested_primary_asset_version,
        admitted_png,
        selected_reference_role=selected_reference_role,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        requested_at=validated_expected.requested_at,
        request_basis=validated_expected.request_basis,
        defer_prohibited=True,
        expected_request_linkage=validated_expected,
    )

    # Copied-field closure is evaluated before the deferred boundary stages.  A
    # rehashed authority-only mutation also changes the review/Request identities;
    # those derivative differences are deferred with their owning authority fields.
    actual_values = cast(dict[str, object], _explicit_value(validated_expected))
    rebuilt_values = cast(dict[str, object], _explicit_value(rebuilt))
    differences = {
        name
        for name in actual_values
        if actual_values.get(name) != rebuilt_values.get(name)
    }
    deferred_authority_differences = {
        *_ZERO_AUTHORITY_VALUES,
        "role_binding_review_payload_sha256",
        "request_id",
        "request_sha256",
    }
    if differences - deferred_authority_differences:
        _fail(
            "UPSTREAM_CLOSURE_MISMATCH",
            "Role-Binding Request differs from its exact supplied closure",
        )

    _verify_zero_authority(original, field="expected Role-Binding Request")
    _verify_no_prohibited_connection(
        {
            "request": original,
            "maker_identity": _admit_retained_json(
                maker_identity_bytes,
                maximum=_MAX_HUMAN_IDENTITY_BYTES,
                field="Role-Binding Maker identity",
            ),
            "maker_action": _admit_retained_json(
                maker_action_bytes,
                maximum=_MAX_RETAINED_RECORD_BYTES,
                field="Role-Binding Maker action",
            ),
        },
        field="Role-Binding Request verification inputs",
    )
    validated = cast(
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
        _complete_formal_workflow_boundary(
            validated_expected,
            original,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
            field="expected Role-Binding Request",
        ),
    )
    if (
        validated != rebuilt
        or generated_reference_role_binding_contract_document_bytes(validated)
        != generated_reference_role_binding_contract_document_bytes(rebuilt)
    ):
        _fail(
            "UPSTREAM_CLOSURE_MISMATCH",
            "Role-Binding Request differs from fresh retained-byte/replay rebuild",
        )
    return validated


def _gate_projection(
    value: GeneratedReferenceRoleBindingGateResultV1,
) -> dict[str, object]:
    return {
        "ordinal": value.ordinal,
        "gate": value.gate,
        "result": value.result,
        "basis": value.basis,
    }


def _role_binding_gates(
    *,
    binding_status: str,
    primary_binding_matches: bool,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_result: GateResult,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_basis: str,
    whole_composite_role_suitability_result: GateResult,
    whole_composite_role_suitability_basis: str,
    non_exclusive_no_transform_boundary_result: GateResult,
    non_exclusive_no_transform_boundary_basis: str,
) -> tuple[GeneratedReferenceRoleBindingGateResultV1, ...]:
    status_result: GateResult = cast(
        GateResult,
        {
            "CURRENT": "PASS",
            "EXPIRED": "FAIL",
            "REVOKED": "FAIL",
            "HELD": "FAIL",
            "INDETERMINATE": "INDETERMINATE",
        }[binding_status],
    )
    results: tuple[GateResult, ...] = (
        "PASS",
        "PASS",
        "PASS",
        "PASS",
        status_result,
        "PASS" if primary_binding_matches else "FAIL",
        "PASS",
        "PASS",
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result,
        whole_composite_role_suitability_result,
        non_exclusive_no_transform_boundary_result,
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
        _COMPILER_GATE_BASES[7],
        _human_text(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis,
            field=(
                "exact_role_and_reviewed_rights_scope_presented_without_expansion_basis"
            ),
        ),
        _human_text(
            whole_composite_role_suitability_basis,
            field="whole_composite_role_suitability_basis",
        ),
        _human_text(
            non_exclusive_no_transform_boundary_basis,
            field="non_exclusive_no_transform_boundary_basis",
        ),
        _COMPILER_GATE_BASES[11],
    )
    if any(basis is None for basis in bases):
        _fail("CONTRACT_FIELD_INVALID", "Role-Binding gate basis derivation is incomplete")
    return tuple(
        GeneratedReferenceRoleBindingGateResultV1.model_validate(
            {
                "ordinal": ordinal,
                "gate": gate,
                "result": results[ordinal],
                "basis": cast(str, bases[ordinal]),
            }
        )
        for ordinal, gate in enumerate(ROLE_BINDING_GATE_ORDER)
    )


def generated_reference_role_binding_checker_action_projection(
    *,
    request_id: str,
    request_sha256: str,
    target_sha256: str,
    selected_reference_role: str,
    final_status_receipt_sha256: str,
    final_primary_asset_binding_sha256: str,
    actor_ref_sha256: str,
    reviewed_at: str,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_result: GateResult,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_basis: str,
    whole_composite_role_suitability_result: GateResult,
    whole_composite_role_suitability_basis: str,
    non_exclusive_no_transform_boundary_result: GateResult,
    non_exclusive_no_transform_boundary_basis: str,
    gate_results: tuple[GeneratedReferenceRoleBindingGateResultV1, ...],
    binding_issue_codes: tuple[BindingIssueCode, ...],
    decision_basis: str,
    decision: BindingDecision,
    binding_materialization_allowed: bool,
) -> dict[str, object]:
    if type(request_id) is not str or re.fullmatch(_PORTABLE_ID_PATTERN, request_id) is None:
        _fail("ACTION_RECORD_INVALID", "Checker action request_id is invalid")
    for name, value in (
        ("request_sha256", request_sha256),
        ("target_sha256", target_sha256),
        ("final_status_receipt_sha256", final_status_receipt_sha256),
        ("final_primary_asset_binding_sha256", final_primary_asset_binding_sha256),
        ("actor_ref_sha256", actor_ref_sha256),
    ):
        if type(value) is not str or re.fullmatch(_LOWER_SHA256_PATTERN, value) is None:
            _fail("ACTION_RECORD_INVALID", f"Checker action {name} is invalid")
    if type(selected_reference_role) is not str or selected_reference_role not in (
        *CHARACTER_REFERENCE_ROLE_ORDER,
        *SCENE_REFERENCE_ROLE_ORDER,
    ):
        _fail("ACTION_RECORD_INVALID", "Checker action selected role is invalid")
    _action_time(reviewed_at, field="reviewed_at")
    if type(gate_results) is not tuple or len(gate_results) != 12:
        _fail("ACTION_RECORD_INVALID", "Checker action gate tuple must contain 12 items")
    for item in gate_results:
        _exact_nested_model(
            item, GeneratedReferenceRoleBindingGateResultV1, field="Checker action gate"
        )
    if binding_issue_codes != _expected_issues(gate_results):
        _fail("ACTION_RECORD_INVALID", "Checker action issue tuple drifted")
    if decision != _decision_from_gates(gate_results):
        _fail("ACTION_RECORD_INVALID", "Checker action decision mapping drifted")
    if binding_materialization_allowed is not (
        decision == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
    ):
        _fail("ACTION_RECORD_INVALID", "Checker action materialization flag drifted")
    return {
        "document_profile": (
            "sdc.generated-reference-eligible-asset-role-binding-decision-action.v1"
        ),
        "action": (
            "RECORDED_GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_DECISION"
        ),
        "policy_id": GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID,
        "policy_version": GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION,
        "policy_document_sha256": GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256,
        "request_id": request_id,
        "request_sha256": request_sha256,
        "target_sha256": target_sha256,
        "selected_reference_role": selected_reference_role,
        "final_status_receipt_sha256": final_status_receipt_sha256,
        "final_primary_asset_binding_sha256": final_primary_asset_binding_sha256,
        "actor_ref_sha256": actor_ref_sha256,
        "reviewed_at": reviewed_at,
        "exact_role_and_reviewed_rights_scope_presented_without_expansion_result": (
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result
        ),
        "exact_role_and_reviewed_rights_scope_presented_without_expansion_basis": (
            _action_basis(
                exact_role_and_reviewed_rights_scope_presented_without_expansion_basis,
                field=(
                    "exact_role_and_reviewed_rights_scope_presented_without_expansion_basis"
                ),
            )
        ),
        "whole_composite_role_suitability_result": (
            whole_composite_role_suitability_result
        ),
        "whole_composite_role_suitability_basis": _action_basis(
            whole_composite_role_suitability_basis,
            field="whole_composite_role_suitability_basis",
        ),
        "non_exclusive_no_transform_boundary_result": (
            non_exclusive_no_transform_boundary_result
        ),
        "non_exclusive_no_transform_boundary_basis": _action_basis(
            non_exclusive_no_transform_boundary_basis,
            field="non_exclusive_no_transform_boundary_basis",
        ),
        "gate_results": [_gate_projection(item) for item in gate_results],
        "binding_issue_codes": list(binding_issue_codes),
        "decision_basis": _action_basis(decision_basis, field="decision_basis"),
        "decision": decision,
        "binding_materialization_allowed": binding_materialization_allowed,
    }


def _preflight_finalize_stage_inputs(
    request: object,
    promotion: object,
    request_status: object,
    requested_primary_bible: object,
    requested_primary_asset_version: object,
    final_status: object,
    binding_primary_bible: object,
    binding_primary_asset_version: object,
    admitted_png: object,
    *,
    selected_reference_role: object,
    maker_identity_bytes: object,
    maker_action_bytes: object,
    checker_identity_bytes: object,
    checker_action_bytes: object,
    binding_at: object,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_result: object,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_basis: object,
    whole_composite_role_suitability_result: object,
    whole_composite_role_suitability_basis: object,
    non_exclusive_no_transform_boundary_result: object,
    non_exclusive_no_transform_boundary_basis: object,
    decision_basis: object,
    expected_finalization: object | None = None,
) -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object] | None,
    dict[str, object] | None,
]:
    """Run finalization stages 1-5 without authority/prohibited checks."""

    records = (
        (maker_identity_bytes, _MAX_HUMAN_IDENTITY_BYTES, "Role-Binding Maker identity"),
        (maker_action_bytes, _MAX_RETAINED_RECORD_BYTES, "Role-Binding Maker action"),
        (
            checker_identity_bytes,
            _MAX_HUMAN_IDENTITY_BYTES,
            "Role-Binding Checker identity",
        ),
        (
            checker_action_bytes,
            _MAX_RETAINED_RECORD_BYTES,
            "Role-Binding Checker action",
        ),
    )
    _preflight_retained_resource_limits(records)
    if type(admitted_png) is GeneratedReferenceRoleBindingAdmittedPng:
        raw = admitted_png.png_bytes
        if type(raw) is bytes and not 1 <= len(raw) <= _MAX_PNG_BYTES:
            _fail("INPUT_RESOURCE_LIMIT_EXCEEDED", "admitted PNG exceeds byte limits")

    expected_decision_values: dict[str, object] | None = None
    expected_binding_values: dict[str, object] | None = None
    expected_decision_object: object | None = None
    expected_binding_object: object | None = None
    if type(expected_finalization) is GeneratedReferenceRoleBindingFinalizationResult:
        expected_decision_object = getattr(expected_finalization, "decision", None)
        expected_binding_object = getattr(expected_finalization, "binding", None)
        _preflight_formal_resource_limit(
            expected_decision_object,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
            field="expected Role-Binding Decision",
        )
        _preflight_formal_resource_limit(
            expected_binding_object,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
            field="expected Eligible-Asset Role Binding",
        )

    _preflight_formal_resource_limit(
        request,
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
        field="Role-Binding Request",
    )

    if type(expected_finalization) is GeneratedReferenceRoleBindingFinalizationResult:
        if type(expected_decision_object) is (
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1
        ):
            expected_decision_values = _verify_formal_resource(
                expected_decision_object,
                CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
                field="expected Role-Binding Decision",
            )
        if type(expected_binding_object) is (
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1
        ):
            expected_binding_values = _verify_formal_resource(
                expected_binding_object,
                CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
                field="expected Eligible-Asset Role Binding",
            )

    # If the formal input has the exact process type, admit its resource/document
    # now.  A wrong formal type is held until after every retained document has had
    # its higher-priority syntax check.
    request_values: dict[str, object] | None = None
    if type(request) is CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1:
        request_values = _verify_formal_resource(
            request,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
            field="Role-Binding Request",
        )
    parsed = _preflight_retained_documents(records)

    if expected_finalization is not None:
        if type(expected_finalization) is not GeneratedReferenceRoleBindingFinalizationResult:
            _fail("CONTRACT_FIELD_INVALID", "expected finalization result type mismatch")
        if expected_decision_values is None:
            _fail("CONTRACT_FIELD_INVALID", "expected Decision has the wrong exact type")
        if expected_binding_object is not None and expected_binding_values is None:
            _fail("CONTRACT_FIELD_INVALID", "expected Binding has the wrong exact type")
    if request_values is None:
        _fail(
            "CONTRACT_FIELD_INVALID",
            "Role-Binding Request has the wrong exact process type",
        )

    if type(promotion) is not GeneratedReferenceRoleBindingPromotionClosureInput:
        _fail("CONTRACT_FIELD_INVALID", "Promotion closure has the wrong process type")
    if type(request_status) is not GeneratedReferenceAssetPromotionStatusClosureInput:
        _fail("CONTRACT_FIELD_INVALID", "request-time status closure type mismatch")
    if type(final_status) is not GeneratedReferenceAssetPromotionStatusClosureInput:
        _fail("CONTRACT_FIELD_INVALID", "final status closure type mismatch")
    _preflight_status_closure_structure(request_status, field="request-time")
    _preflight_status_closure_structure(final_status, field="final")
    for bible, field in (
        (requested_primary_bible, "request-time Bible"),
        (binding_primary_bible, "final Bible"),
    ):
        if type(bible) is not CharacterBible and type(bible) is not SceneBible:
            _fail("CONTRACT_FIELD_INVALID", f"{field} has the wrong exact type")
    for asset, field in (
        (requested_primary_asset_version, "request-time AssetVersion"),
        (binding_primary_asset_version, "final AssetVersion"),
    ):
        if (
            type(asset) is not CharacterAssetVersion
            and type(asset) is not SceneAssetVersion
        ):
            _fail("CONTRACT_FIELD_INVALID", f"{field} has the wrong exact type")
    if type(admitted_png) is not GeneratedReferenceRoleBindingAdmittedPng:
        _fail("CONTRACT_FIELD_INVALID", "admitted_png has the wrong process type")
    if type(selected_reference_role) is not str:
        _fail("CONTRACT_FIELD_INVALID", "selected_reference_role must be exact str")
    maker_identity_raw = _require_exact_bytes(
        maker_identity_bytes, field="Role-Binding Maker identity"
    )
    _require_exact_bytes(maker_action_bytes, field="Role-Binding Maker action")
    checker_identity_raw = _require_exact_bytes(
        checker_identity_bytes, field="Role-Binding Checker identity"
    )
    _require_exact_bytes(checker_action_bytes, field="Role-Binding Checker action")
    if type(binding_at) is not str:
        _fail("CONTRACT_FIELD_INVALID", "binding_at must be an exact string")
    for result, field in (
        (
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result,
            "exact role/Rights presentation result",
        ),
        (whole_composite_role_suitability_result, "whole-composite suitability result"),
        (non_exclusive_no_transform_boundary_result, "non-exclusive boundary result"),
    ):
        if result not in {"PASS", "FAIL", "INDETERMINATE"}:
            _fail("CONTRACT_FIELD_INVALID", f"{field} literal is invalid")
    for basis, field in (
        (
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis,
            "exact role/Rights presentation basis",
        ),
        (whole_composite_role_suitability_basis, "whole-composite suitability basis"),
        (non_exclusive_no_transform_boundary_basis, "non-exclusive boundary basis"),
        (decision_basis, "decision_basis"),
    ):
        _preflight_bounded_text(basis, field=field)
    _human_identity(maker_identity_raw, field="Role-Binding Maker identity")
    _human_identity(checker_identity_raw, field="Role-Binding Checker identity")
    maker_action = parsed["Role-Binding Maker action"]
    checker_action = parsed["Role-Binding Checker action"]
    _preflight_maker_action_structure(maker_action)
    _preflight_checker_action_structure(checker_action)
    expected_structural_values: list[
        tuple[Mapping[str, object], type[BaseModel], str]
    ] = []
    if expected_decision_values is not None:
        expected_structural_values.append(
            (
                expected_decision_values,
                CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
                "expected Role-Binding Decision",
            )
        )
    if expected_binding_values is not None:
        expected_structural_values.append(
            (
                expected_binding_values,
                CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
                "expected Eligible-Asset Role Binding",
            )
        )
    try:
        _sanitize_formal_structure(
            request_values,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
        )
    except GeneratedReferenceRoleBindingError:
        raise
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "CONTRACT_FIELD_INVALID", "Role-Binding Request structure is invalid"
        ) from exc
    for values, model, field in expected_structural_values:
        try:
            _sanitize_formal_structure(values, model)
        except GeneratedReferenceRoleBindingError:
            raise
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise GeneratedReferenceRoleBindingError(
                "CONTRACT_FIELD_INVALID", f"{field} structure is invalid"
            ) from exc

    _verify_policy_fields(request_values, field="Role-Binding Request")
    _verify_retained_action_policy(maker_action, checker_action)
    for values, _model, field in expected_structural_values:
        _verify_policy_fields(values, field=field)
    _verify_formal_identity(
        request_values,
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
        field="Role-Binding Request",
    )
    for values, model, field in expected_structural_values:
        _verify_formal_identity(values, model, field=field)
    return (
        request_values,
        maker_action,
        checker_action,
        expected_decision_values,
        expected_binding_values,
    )


def _preparation_identity_records(
    *,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    maker_identity_bytes: bytes,
) -> tuple[tuple[bytes, str], ...]:
    return (
        (maker_identity_bytes, "Role-Binding Maker identity"),
        (
            promotion.upstream.qualification_preparer_identity_bytes,
            "Qualification Request Preparer identity",
        ),
        (
            promotion.upstream.qualifier_identity_bytes,
            "Qualification Qualifier identity",
        ),
        (
            promotion.upstream.manifest_maker_identity_bytes,
            "Manifest Maker identity",
        ),
        (
            promotion.upstream.manifest_checker_identity_bytes,
            "Manifest Checker identity",
        ),
        (
            promotion.request_status.status_preparer_identity_bytes,
            "Promotion Request-time Status Preparer identity",
        ),
        (
            promotion.request_status.status_checker_identity_bytes,
            "Promotion Request-time Status Checker identity",
        ),
        (
            promotion.final_status.status_preparer_identity_bytes,
            "Promotion final Status Preparer identity",
        ),
        (
            promotion.final_status.status_checker_identity_bytes,
            "Promotion final Status Checker identity",
        ),
        (promotion.maker_identity_bytes, "Promotion Maker identity"),
        (promotion.checker_identity_bytes, "Promotion Checker identity"),
        (
            request_status.status_preparer_identity_bytes,
            "Role-Binding Request-time Status Preparer identity",
        ),
        (
            request_status.status_checker_identity_bytes,
            "Role-Binding Request-time Status Checker identity",
        ),
    )


def _verify_identity_raw_digest_collisions(
    records: tuple[tuple[bytes, str], ...],
) -> tuple[tuple[bytes, tuple[str, str], str], ...]:
    admitted = tuple(
        (raw, *_human_identity(raw, field=field)) for raw, field in records
    )
    for index, (raw, _semantic_tuple, raw_sha) in enumerate(admitted):
        for prior_raw, _prior_tuple, prior_sha in admitted[:index]:
            if raw_sha == prior_sha and raw != prior_raw:
                _fail(
                    "ROLE_SEPARATION_VIOLATION",
                    "identity raw digest collision does not preserve exact bytes",
                )
    return admitted


def _verify_role_separation(
    *,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    final_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    maker_identity_bytes: bytes,
    checker_identity_bytes: bytes,
) -> tuple[str, str]:
    records = (
        *_preparation_identity_records(
            promotion=promotion,
            request_status=request_status,
            maker_identity_bytes=maker_identity_bytes,
        ),
        (
            final_status.status_preparer_identity_bytes,
            "Role-Binding final Status Preparer identity",
        ),
        (
            final_status.status_checker_identity_bytes,
            "Role-Binding final Status Checker identity",
        ),
        (checker_identity_bytes, "Role-Binding Checker identity"),
    )
    admitted = _verify_identity_raw_digest_collisions(records)
    maker_sha = admitted[0][2]
    checker_tuple = admitted[-1][1]
    checker_sha = admitted[-1][2]
    forbidden = tuple(
        admitted[index][1]
        for index in (0, 2, 4, 6, 8, 10, 12, 14)
    )
    if checker_tuple in forbidden:
        _fail(
            "ROLE_SEPARATION_VIOLATION",
            "Role-Binding Checker aliases one forbidden retained role tuple",
        )
    return maker_sha, checker_sha


def _decision_values(
    *,
    request: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
    final_receipt: CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
    final_primary: GeneratedReferencePromotionPrimaryAssetBindingV1,
    checker_identity_sha: str,
    checker_action_sha: str,
    binding_at: str,
    gates: tuple[GeneratedReferenceRoleBindingGateResultV1, ...],
    issues: tuple[BindingIssueCode, ...],
    decision_basis: str,
    decision: BindingDecision,
    materialization_allowed: bool,
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "document_type": (
            "sdc.creative-sample-generated-reference-eligible-asset-role-binding-decision-v1"
        ),
        "decision_scope": (
            "GENERATED_REFERENCE_ELIGIBLE_ASSET_SINGLE_ROLE_BINDING_ONLY"
        ),
        "policy_id": request.policy_id,
        "policy_version": request.policy_version,
        "policy_document_sha256": request.policy_document_sha256,
        "role_binding_review_payload_sha256": (
            request.role_binding_review_payload_sha256
        ),
        "request_id": request.request_id,
        "request_sha256": request.request_sha256,
        "requested_role_binding_target": request.requested_role_binding_target,
        "promotion_request_id": request.promotion_request_id,
        "promotion_request_sha256": request.promotion_request_sha256,
        "promotion_decision_id": request.promotion_decision_id,
        "promotion_decision_sha256": request.promotion_decision_sha256,
        "eligible_asset_sidecar_id": request.eligible_asset_sidecar_id,
        "eligible_asset_sidecar_sha256": request.eligible_asset_sidecar_sha256,
        "promotion_at": request.promotion_at,
        "promotion_evidence_valid_until": request.promotion_evidence_valid_until,
        "qualification_decision_id": request.qualification_decision_id,
        "qualification_decision_sha256": request.qualification_decision_sha256,
        "qualification_valid_until": request.qualification_valid_until,
        "manifest_id": request.manifest_id,
        "manifest_sha256": request.manifest_sha256,
        "manifest_valid_until": request.manifest_valid_until,
        "reviewed_rights_scope": request.reviewed_rights_scope,
        "requested_primary_asset_binding": request.requested_primary_asset_binding,
        "binding_primary_asset_binding": final_primary,
        "status_subject_closure_id": final_receipt.subject_closure.closure_id,
        "status_subject_closure_sha256": final_receipt.subject_closure.closure_sha256,
        "binding_status_record_id": final_receipt.record_id,
        "binding_status_record_sha256": final_receipt.record_sha256,
        "binding_status_receipt_id": final_receipt.receipt_id,
        "binding_status_receipt_sha256": final_receipt.receipt_sha256,
        "binding_explicit_chain_set_sha256": final_receipt.explicit_chain_set_sha256,
        "binding_coverage_set_sha256": final_receipt.coverage_set_sha256,
        "binding_joint_replay_sha256": final_receipt.joint_replay_sha256,
        "binding_as_of_assessment_sha256": final_receipt.as_of_assessment_sha256,
        "binding_as_of_status": final_receipt.as_of_status,
        "binding_status_valid_until": final_receipt.status_valid_until,
        "checker_identity_ref_sha256": checker_identity_sha,
        "checker_action_sha256": checker_action_sha,
        "checker_reviewed_at": binding_at,
        "decision_at": binding_at,
        "binding_at": binding_at,
        "gate_results": gates,
        "binding_issue_codes": issues,
        "decision_basis": decision_basis,
        "decision": decision,
        "binding_materialization_allowed": materialization_allowed,
        "role_binding_review_performed": True,
        "binding_id_embedded": False,
        "role_binding_exclusivity_asserted": False,
        "complete_role_set_asserted": False,
        "global_role_uniqueness_asserted": False,
        "crop_applied": False,
        "split_applied": False,
        "transform_applied": False,
        "derived_media_created": False,
        "provider_input_eligible": False,
        "status": (
            "GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_DECISION_RECORDED"
        ),
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
        **_zero_authority_values(),
    }


def _binding_values(
    *,
    request: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
    decision: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
) -> dict[str, object]:
    evidence_until = min(
        _parse_utc(decision.qualification_valid_until, field="qualification_valid_until"),
        _parse_utc(decision.manifest_valid_until, field="manifest_valid_until"),
        _parse_utc(decision.binding_status_valid_until, field="binding_status_valid_until"),
    )
    return {
        "schema_version": "1.0.0",
        "document_type": (
            "sdc.creative-sample-generated-reference-eligible-asset-role-binding-v1"
        ),
        "binding_scope": (
            "POST_PROMOTION_SINGLE_ROLE_BINDING_HISTORICAL_EVIDENCE_ONLY"
        ),
        "policy_id": decision.policy_id,
        "policy_version": decision.policy_version,
        "policy_document_sha256": decision.policy_document_sha256,
        "request_id": request.request_id,
        "request_sha256": request.request_sha256,
        "decision_id": decision.decision_id,
        "decision_sha256": decision.decision_sha256,
        "role_binding_target": decision.requested_role_binding_target,
        "promotion_request_id": decision.promotion_request_id,
        "promotion_request_sha256": decision.promotion_request_sha256,
        "promotion_decision_id": decision.promotion_decision_id,
        "promotion_decision_sha256": decision.promotion_decision_sha256,
        "eligible_asset_sidecar_id": decision.eligible_asset_sidecar_id,
        "eligible_asset_sidecar_sha256": decision.eligible_asset_sidecar_sha256,
        "promotion_at": decision.promotion_at,
        "promotion_evidence_valid_until": decision.promotion_evidence_valid_until,
        "qualification_decision_id": decision.qualification_decision_id,
        "qualification_decision_sha256": decision.qualification_decision_sha256,
        "qualification_valid_until": decision.qualification_valid_until,
        "manifest_id": decision.manifest_id,
        "manifest_sha256": decision.manifest_sha256,
        "manifest_valid_until": decision.manifest_valid_until,
        "reviewed_rights_scope": decision.reviewed_rights_scope,
        "primary_asset_binding": decision.binding_primary_asset_binding,
        "status_subject_closure_id": decision.status_subject_closure_id,
        "status_subject_closure_sha256": decision.status_subject_closure_sha256,
        "binding_status_record_id": decision.binding_status_record_id,
        "binding_status_record_sha256": decision.binding_status_record_sha256,
        "binding_status_receipt_id": decision.binding_status_receipt_id,
        "binding_status_receipt_sha256": decision.binding_status_receipt_sha256,
        "binding_explicit_chain_set_sha256": decision.binding_explicit_chain_set_sha256,
        "binding_coverage_set_sha256": decision.binding_coverage_set_sha256,
        "binding_joint_replay_sha256": decision.binding_joint_replay_sha256,
        "binding_as_of_assessment_sha256": decision.binding_as_of_assessment_sha256,
        "binding_as_of_status": "CURRENT",
        "binding_at": decision.binding_at,
        "binding_status_valid_until": decision.binding_status_valid_until,
        "binding_evidence_valid_until": _format_utc(evidence_until),
        "binding_state": (
            "GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_RECORDED"
        ),
        "role_binding_performed": True,
        "provider_input_eligible": False,
        "present_currentness_asserted": False,
        "perpetual_role_suitability_asserted": False,
        "role_binding_exclusivity_asserted": False,
        "complete_role_set_asserted": False,
        "global_role_uniqueness_asserted": False,
        "current_role_binding_asserted": False,
        "supersedes_role_binding": False,
        "primary_asset_binding_replaced": False,
        "bible_active_binding_changed": False,
        "asset_version_v1_created": False,
        "whole_composite_media_bound": True,
        "crop_applied": False,
        "split_applied": False,
        "transform_applied": False,
        "derived_media_created": False,
        "provider_slot_embedded": False,
        "status": "GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_RECORDED",
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
        **_zero_authority_values(),
    }


def _verify_expected_finalization_gate_stage(
    expected: GeneratedReferenceRoleBindingFinalizationResult,
) -> None:
    """Validate only the expected output's frozen stage-18 gate conditions."""

    expected_decision = expected.decision
    positive = (
        expected_decision.decision == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
    )
    if expected.binding is not None and not positive:
        _fail(
            "BINDING_GATE_NOT_PASS",
            "an expected non-positive Decision cannot carry a Binding",
        )
    if positive and (
        any(item.result != "PASS" for item in expected_decision.gate_results)
        or expected_decision.binding_issue_codes
        or not expected_decision.binding_materialization_allowed
        or expected_decision.binding_as_of_status != "CURRENT"
    ):
        _fail("BINDING_GATE_NOT_PASS", "expected positive Binding gates are not all PASS")


_DECISION_REQUEST_LINK_FIELDS = (
    "policy_id",
    "policy_version",
    "policy_document_sha256",
    "role_binding_review_payload_sha256",
    "request_id",
    "request_sha256",
    "requested_role_binding_target",
    "promotion_request_id",
    "promotion_request_sha256",
    "promotion_decision_id",
    "promotion_decision_sha256",
    "eligible_asset_sidecar_id",
    "eligible_asset_sidecar_sha256",
    "promotion_at",
    "promotion_evidence_valid_until",
    "qualification_decision_id",
    "qualification_decision_sha256",
    "qualification_valid_until",
    "manifest_id",
    "manifest_sha256",
    "manifest_valid_until",
    "reviewed_rights_scope",
    "requested_primary_asset_binding",
)


def _verify_expected_decision_request_linkage(
    expected: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
    request: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
) -> None:
    """Close every frozen Decision-from-Request field at workflow stage 6."""

    if any(
        getattr(expected, name) != getattr(request, name)
        for name in _DECISION_REQUEST_LINK_FIELDS
    ):
        _fail(
            "UPSTREAM_CLOSURE_MISMATCH",
            "expected Role-Binding Decision differs from its supplied Request",
        )


def _finalize_generated_reference_eligible_asset_role_binding_workflow(
    request: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_bible: CharacterBible | SceneBible,
    requested_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    final_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    binding_primary_bible: CharacterBible | SceneBible,
    binding_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    admitted_png: GeneratedReferenceRoleBindingAdmittedPng,
    *,
    selected_reference_role: str,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    checker_identity_bytes: bytes,
    checker_action_bytes: bytes,
    binding_at: str,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_result: GateResult,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_basis: str,
    whole_composite_role_suitability_result: GateResult,
    whole_composite_role_suitability_basis: str,
    non_exclusive_no_transform_boundary_result: GateResult,
    non_exclusive_no_transform_boundary_basis: str,
    decision_basis: str,
    additional_authority_surfaces: Sequence[
        tuple[Mapping[str, object], str]
    ] = (),
    additional_prohibited_surfaces: Sequence[
        tuple[Mapping[str, object], str]
    ] = (),
    expected_decision_request_linkage: (
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1 | None
    ) = None,
    expected_gate_result: GeneratedReferenceRoleBindingFinalizationResult | None = None,
) -> GeneratedReferenceRoleBindingFinalizationResult:
    """Run finalization with optional verifier-owned stage surfaces."""

    (
        request_values,
        maker_action,
        checker_action,
        expected_decision_values,
        expected_binding_values,
    ) = _preflight_finalize_stage_inputs(
        request,
        promotion,
        request_status,
        requested_primary_bible,
        requested_primary_asset_version,
        final_status,
        binding_primary_bible,
        binding_primary_asset_version,
        admitted_png,
        selected_reference_role=selected_reference_role,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        checker_identity_bytes=checker_identity_bytes,
        checker_action_bytes=checker_action_bytes,
        binding_at=binding_at,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result
        ),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis
        ),
        whole_composite_role_suitability_result=whole_composite_role_suitability_result,
        whole_composite_role_suitability_basis=whole_composite_role_suitability_basis,
        non_exclusive_no_transform_boundary_result=(
            non_exclusive_no_transform_boundary_result
        ),
        non_exclusive_no_transform_boundary_basis=(
            non_exclusive_no_transform_boundary_basis
        ),
        decision_basis=decision_basis,
    )

    # Stage 6: verifier-owned Decision linkage and cheap predecessor anchors are
    # compared before full Promotion replay, without accepting digest substitutes.
    _verify_expected_request_predecessor_linkage(request, promotion)
    if expected_decision_request_linkage is not None:
        _verify_expected_decision_request_linkage(
            expected_decision_request_linkage, request
        )
    if type(promotion.request) is CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        if (
            request.promotion_request_id != promotion.request.request_id
            or request.promotion_request_sha256 != promotion.request.request_sha256
        ):
            _fail("UPSTREAM_CLOSURE_MISMATCH", "Request Promotion anchor drifted")
    raw_sidecar = (
        promotion.result.sidecar
        if type(promotion.result) is GeneratedReferenceAssetPromotionFinalizationResult
        else None
    )
    if type(raw_sidecar) is CreativeSampleGeneratedReferenceEligibleAssetSidecarV1:
        if (
            request.promotion_decision_id != raw_sidecar.decision_id
            or request.promotion_decision_sha256 != raw_sidecar.decision_sha256
            or request.eligible_asset_sidecar_id != raw_sidecar.sidecar_id
            or request.eligible_asset_sidecar_sha256 != raw_sidecar.sidecar_sha256
        ):
            _fail("UPSTREAM_CLOSURE_MISMATCH", "Request Sidecar anchor drifted")

    # Stage 7: complete ADR-045 verification, retaining its released nested errors.
    promotion_request, sidecar = _verify_promotion_closure(promotion)

    # Stage 8: exact whole admitted PNG occurrence.
    admitted = _verify_admitted_png(admitted_png, promotion, sidecar)

    # Stage 9: selected role, purpose and Profile membership close one exact target.
    expected_target = build_generated_reference_eligible_asset_role_binding_target(
        promotion,
        admitted,
        selected_reference_role=selected_reference_role,
    )
    if request.requested_role_binding_target != expected_target:
        _fail(
            "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
            "Request target differs from the exact role/purpose/Profile closure",
        )

    # Stage 10: both primary snapshots are reconstructed.  One valid same-subject
    # final active-binding difference remains a gate FAIL, not a structural error.
    try:
        requested_primary = build_generated_reference_promotion_primary_asset_binding(
            requested_primary_bible, requested_primary_asset_version
        )
        final_primary = build_generated_reference_promotion_primary_asset_binding(
            binding_primary_bible, binding_primary_asset_version
        )
    except GeneratedReferenceAssetPromotionError as exc:
        raise GeneratedReferenceRoleBindingError(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "Role-Binding primary binding reconstruction failed",
        ) from exc
    if (
        requested_primary != sidecar.primary_asset_binding
        or request.requested_primary_asset_binding != requested_primary
    ):
        _fail(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "Request primary binding differs from the Sidecar",
        )
    if (
        final_primary.subject_id != requested_primary.subject_id
        or final_primary.asset_purpose != requested_primary.asset_purpose
    ):
        _fail(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "final primary binding crosses the requested subject or purpose",
        )
    if (
        expected_gate_result is not None
        and expected_gate_result.decision.binding_primary_asset_binding
        != final_primary
    ):
        _fail(
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
            "expected Decision final primary binding differs from reconstruction",
        )

    # Stage 11: replay both exact Records at their own Receipt as_of values and
    # enforce Promotion-final -> Request-time -> final monotonic closure.
    request_receipt = _verify_status_closure(
        request_status,
        promotion.upstream.manifest,
        as_of=request_status.receipt.as_of,
    )
    _verify_status_monotonicity(promotion.final_status, request_status)
    final_receipt = _verify_status_closure(
        final_status,
        promotion.upstream.manifest,
        as_of=final_status.receipt.as_of,
    )
    _verify_status_monotonicity(request_status, final_status)
    if request_receipt.as_of_status != "CURRENT":
        _fail("CURRENT_STATUS_REPLAY_INVALID", "Request-time status is not CURRENT")
    request_status_fields = {
        "status_subject_closure_id": request_receipt.subject_closure.closure_id,
        "status_subject_closure_sha256": request_receipt.subject_closure.closure_sha256,
        "requested_status_record_id": request_receipt.record_id,
        "requested_status_record_sha256": request_receipt.record_sha256,
        "requested_status_receipt_id": request_receipt.receipt_id,
        "requested_status_receipt_sha256": request_receipt.receipt_sha256,
        "requested_explicit_chain_set_sha256": request_receipt.explicit_chain_set_sha256,
        "requested_coverage_set_sha256": request_receipt.coverage_set_sha256,
        "requested_joint_replay_sha256": request_receipt.joint_replay_sha256,
        "requested_as_of_assessment_sha256": request_receipt.as_of_assessment_sha256,
        "requested_as_of": request_receipt.as_of,
        "requested_as_of_status": request_receipt.as_of_status,
        "requested_status_valid_until": request_receipt.status_valid_until,
    }
    if any(getattr(request, name) != value for name, value in request_status_fields.items()):
        _fail("CURRENT_STATUS_REPLAY_INVALID", "Request status anchors drifted")
    if (
        final_receipt.subject_closure.closure_id != request.status_subject_closure_id
        or final_receipt.subject_closure.closure_sha256
        != request.status_subject_closure_sha256
    ):
        _fail("CURRENT_STATUS_REPLAY_INVALID", "final Status Subject drifted")
    if expected_gate_result is not None:
        expected_status = {
            "status_subject_closure_id": final_receipt.subject_closure.closure_id,
            "status_subject_closure_sha256": (
                final_receipt.subject_closure.closure_sha256
            ),
            "binding_status_record_id": final_receipt.record_id,
            "binding_status_record_sha256": final_receipt.record_sha256,
            "binding_status_receipt_id": final_receipt.receipt_id,
            "binding_status_receipt_sha256": final_receipt.receipt_sha256,
            "binding_explicit_chain_set_sha256": (
                final_receipt.explicit_chain_set_sha256
            ),
            "binding_coverage_set_sha256": final_receipt.coverage_set_sha256,
            "binding_joint_replay_sha256": final_receipt.joint_replay_sha256,
            "binding_as_of_assessment_sha256": (
                final_receipt.as_of_assessment_sha256
            ),
            "binding_as_of_status": final_receipt.as_of_status,
            "binding_status_valid_until": final_receipt.status_valid_until,
        }
        if any(
            getattr(expected_gate_result.decision, name) != value
            for name, value in expected_status.items()
        ):
            _fail(
                "CURRENT_STATUS_REPLAY_INVALID",
                "expected Decision final Status evidence differs from replay",
            )

    # Stage 12: exact Rights scope preservation.
    if not (
        request.reviewed_rights_scope
        == sidecar.reviewed_rights_scope
        == promotion.upstream.manifest.reviewed_rights_scope
    ):
        _fail("RIGHTS_SCOPE_MISMATCH", "reviewed Rights scope changed")

    # Stage 13: the Checker must differ semantically from all eight frozen roles.
    maker_identity_sha, checker_identity_sha = _verify_role_separation(
        promotion=promotion,
        request_status=request_status,
        final_status=final_status,
        maker_identity_bytes=maker_identity_bytes,
        checker_identity_bytes=checker_identity_bytes,
    )

    # Stage 14: exact Maker and Checker actions.  Gate derivation here only closes
    # the action bytes; Decision/materialization remains the later gate stage.
    expected_review = _assemble_review_payload(
        target=expected_target,
        promotion_request=promotion_request,
        sidecar=sidecar,
        requested_primary_asset_binding=requested_primary,
        receipt=request_receipt,
        requested_at=request.requested_at,
        request_valid_until=request.request_valid_until,
    )
    request_review = _review_payload_from_request(request)
    review_differences = {
        name
        for name in _REVIEW_PAYLOAD_FIELDS
        if request_review.get(name) != expected_review.get(name)
    }
    if review_differences - set(_ZERO_AUTHORITY_VALUES):
        _fail("UPSTREAM_CLOSURE_MISMATCH", "Request review payload fields drifted")
    expected_review_sha = _semantic_sha256(
        GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
        expected_review,
    )
    expected_maker_action = generated_reference_role_binding_maker_action_projection(
        actor_ref_sha256=maker_identity_sha,
        role_binding_review_payload_sha256=expected_review_sha,
        target_sha256=expected_target.target_sha256,
        selected_reference_role=selected_reference_role,
        requested_primary_asset_binding_sha256=(
            requested_primary.primary_asset_binding_sha256
        ),
        requested_status_receipt_sha256=request_receipt.receipt_sha256,
        prepared_at=request.requested_at,
        request_basis=request.request_basis,
    )
    maker_action_sha = _exact_action(
        maker_action_bytes,
        expected_maker_action,
        field="Role-Binding Maker action",
    )
    if (
        request.maker_identity_ref_sha256 != maker_identity_sha
        or request.maker_action_sha256 != maker_action_sha
        or request.maker_prepared_at != request.requested_at
    ):
        _fail("ACTION_RECORD_INVALID", "Request Maker closure drifted")

    gates = _role_binding_gates(
        binding_status=final_receipt.as_of_status,
        primary_binding_matches=(final_primary == requested_primary),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result
        ),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis
        ),
        whole_composite_role_suitability_result=whole_composite_role_suitability_result,
        whole_composite_role_suitability_basis=whole_composite_role_suitability_basis,
        non_exclusive_no_transform_boundary_result=(
            non_exclusive_no_transform_boundary_result
        ),
        non_exclusive_no_transform_boundary_basis=(
            non_exclusive_no_transform_boundary_basis
        ),
    )
    issues = _expected_issues(gates)
    decision = _decision_from_gates(gates)
    materialization_allowed = decision == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
    # Build with the already replayed canonical Receipt time, then replace only the
    # reviewed_at leaf with the caller's raw string.  This keeps full action exactness
    # applicable before stage 15 even when the caller time itself is malformed.
    expected_checker_action = generated_reference_role_binding_checker_action_projection(
        request_id=request.request_id,
        request_sha256=request.request_sha256,
        target_sha256=expected_target.target_sha256,
        selected_reference_role=selected_reference_role,
        final_status_receipt_sha256=final_receipt.receipt_sha256,
        final_primary_asset_binding_sha256=final_primary.primary_asset_binding_sha256,
        actor_ref_sha256=checker_identity_sha,
        reviewed_at=final_receipt.as_of,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result
        ),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis
        ),
        whole_composite_role_suitability_result=(
            whole_composite_role_suitability_result
        ),
        whole_composite_role_suitability_basis=whole_composite_role_suitability_basis,
        non_exclusive_no_transform_boundary_result=(
            non_exclusive_no_transform_boundary_result
        ),
        non_exclusive_no_transform_boundary_basis=(
            non_exclusive_no_transform_boundary_basis
        ),
        gate_results=gates,
        binding_issue_codes=issues,
        decision_basis=decision_basis,
        decision=decision,
        binding_materialization_allowed=materialization_allowed,
    )
    expected_checker_action["reviewed_at"] = binding_at
    checker_action_sha = _exact_action(
        checker_action_bytes,
        expected_checker_action,
        field="Role-Binding Checker action",
    )
    if expected_gate_result is not None and (
        expected_gate_result.decision.checker_identity_ref_sha256
        != checker_identity_sha
        or expected_gate_result.decision.checker_action_sha256
        != checker_action_sha
        or expected_gate_result.decision.gate_results != gates
        or expected_gate_result.decision.binding_issue_codes != issues
        or expected_gate_result.decision.decision_basis != decision_basis
        or expected_gate_result.decision.decision != decision
        or expected_gate_result.decision.binding_materialization_allowed
        is not materialization_allowed
    ):
        _fail(
            "ACTION_RECORD_INVALID",
            "expected Decision differs from the exact Checker action tuple",
        )
    request_action_free = _without_role_binding_action_digest_anchors(request_values)
    expected_decision_action_free = _without_role_binding_action_digest_anchors(
        expected_decision_values
    )
    expected_binding_action_free = _without_role_binding_action_digest_anchors(
        expected_binding_values
    )
    occupied = _collect_sha256_strings(
        (
            promotion,
            request_status,
            final_status,
            requested_primary_bible,
            requested_primary_asset_version,
            binding_primary_bible,
            binding_primary_asset_version,
            admitted,
            request_action_free,
            maker_identity_bytes,
            checker_identity_bytes,
            maker_action,
            checker_action,
            expected_decision_action_free,
            expected_binding_action_free,
        )
    )
    if (
        maker_action_sha == checker_action_sha
        or maker_action_sha in occupied
        or checker_action_sha in occupied
    ):
        _fail(
            "ACTION_RECORD_INVALID",
            "Role-Binding action digest aliases another action, evidence, or formal identity",
        )

    decision_candidate_values = _decision_values(
        request=request,
        final_receipt=final_receipt,
        final_primary=final_primary,
        checker_identity_sha=checker_identity_sha,
        checker_action_sha=checker_action_sha,
        binding_at=binding_at,
        gates=gates,
        issues=issues,
        decision_basis=decision_basis,
        decision=decision,
        materialization_allowed=materialization_allowed,
    )
    try:
        decision_candidate = cast(
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
            _build_identity_with_deferred_boundary(
                CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
                decision_candidate_values,
            ),
        )
    except GeneratedReferenceRoleBindingError:
        decision_candidate = None
    if decision_candidate is not None:
        if decision_candidate.decision_sha256 in {
            maker_action_sha,
            checker_action_sha,
        }:
            _fail(
                "ACTION_RECORD_INVALID",
                "Role-Binding action digest aliases the Decision semantic identity",
            )
        if materialization_allowed:
            try:
                binding_candidate = cast(
                    CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
                    _build_identity_with_deferred_boundary(
                        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
                        _binding_values(request=request, decision=decision_candidate),
                    ),
                )
            except GeneratedReferenceRoleBindingError:
                binding_candidate = None
            if binding_candidate is not None and binding_candidate.binding_sha256 in {
                maker_action_sha,
                checker_action_sha,
            }:
                _fail(
                    "ACTION_RECORD_INVALID",
                    "Role-Binding action digest aliases the Binding semantic identity",
                )

    # Stage 15: only now evaluate caller time, as_of equality and half-open bounds.
    _verify_binding_time_window(
        request,
        request_receipt,
        final_receipt,
        binding_at=binding_at,
    )
    if expected_gate_result is not None and any(
        getattr(expected_gate_result.decision, name) != binding_at
        for name in ("checker_reviewed_at", "decision_at", "binding_at")
    ):
        _fail(
            "TIME_OR_VALIDITY_INVALID",
            "expected Decision times differ from the reviewed binding_at",
        )

    # Stages 16-17: every supplied and verifier-owned formal authority surface is
    # checked before any supplied or verifier-owned prohibited connection surface.
    _verify_zero_authority(request_values, field="Role-Binding Request")
    for surface, field in additional_authority_surfaces:
        _verify_zero_authority(surface, field=field)
    _verify_no_prohibited_connection(
        {
            "request": request_values,
            "maker_identity": _admit_retained_json(
                maker_identity_bytes,
                maximum=_MAX_HUMAN_IDENTITY_BYTES,
                field="Role-Binding Maker identity",
            ),
            "maker_action": maker_action,
            "checker_identity": _admit_retained_json(
                checker_identity_bytes,
                maximum=_MAX_HUMAN_IDENTITY_BYTES,
                field="Role-Binding Checker identity",
            ),
            "checker_action": checker_action,
        },
        field="Role-Binding finalization inputs",
    )
    for surface, field in additional_prohibited_surfaces:
        _verify_no_prohibited_connection(surface, field=field)
    validated_request = cast(
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
        _complete_formal_workflow_boundary(
            request,
            request_values,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
            field="Role-Binding Request",
        ),
    )

    # Stage 18 derives the valid Decision (including normal Decision-only FAIL or
    # INDETERMINATE outcomes).  It does not treat a normal negative gate as error.
    decision_value = cast(
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
        _build_identity(
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
            _decision_values(
                request=validated_request,
                final_receipt=final_receipt,
                final_primary=final_primary,
                checker_identity_sha=checker_identity_sha,
                checker_action_sha=checker_action_sha,
                binding_at=binding_at,
                gates=gates,
                issues=issues,
                decision_basis=decision_basis,
                decision=decision,
                materialization_allowed=materialization_allowed,
            ),
        ),
    )
    if maker_action_sha == decision_value.decision_sha256 or (
        checker_action_sha == decision_value.decision_sha256
    ):
        _fail("ACTION_RECORD_INVALID", "action digest aliases Decision identity")
    if expected_gate_result is not None:
        _verify_expected_finalization_gate_stage(expected_gate_result)
    if not materialization_allowed:
        return GeneratedReferenceRoleBindingFinalizationResult(
            decision=decision_value, binding=None
        )

    # Stage 19: one in-memory positive Decision/Binding pair or no positive output.
    try:
        binding_value = cast(
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
            _build_identity(
                CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
                _binding_values(request=validated_request, decision=decision_value),
            ),
        )
        if maker_action_sha == binding_value.binding_sha256 or (
            checker_action_sha == binding_value.binding_sha256
        ):
            _fail("ACTION_RECORD_INVALID", "action digest aliases Binding identity")
        result = GeneratedReferenceRoleBindingFinalizationResult(
            decision=decision_value, binding=binding_value
        )
        generated_reference_role_binding_contract_document_bytes(result.decision)
        generated_reference_role_binding_contract_document_bytes(binding_value)
        return result
    except GeneratedReferenceRoleBindingError as exc:
        if exc.code in {"ATOMIC_OUTPUT_INVARIANT_VIOLATION", "ACTION_RECORD_INVALID"}:
            raise
        raise GeneratedReferenceRoleBindingError(
            "ATOMIC_OUTPUT_INVARIANT_VIOLATION",
            "positive Decision and Binding could not be completed atomically",
        ) from exc
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRoleBindingError(
            "ATOMIC_OUTPUT_INVARIANT_VIOLATION",
            "positive Decision and Binding could not be completed atomically",
        ) from exc


def finalize_generated_reference_eligible_asset_role_binding(
    request: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_bible: CharacterBible | SceneBible,
    requested_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    final_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    binding_primary_bible: CharacterBible | SceneBible,
    binding_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    admitted_png: GeneratedReferenceRoleBindingAdmittedPng,
    *,
    selected_reference_role: str,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    checker_identity_bytes: bytes,
    checker_action_bytes: bytes,
    binding_at: str,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_result: GateResult,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_basis: str,
    whole_composite_role_suitability_result: GateResult,
    whole_composite_role_suitability_basis: str,
    non_exclusive_no_transform_boundary_result: GateResult,
    non_exclusive_no_transform_boundary_basis: str,
    decision_basis: str,
) -> GeneratedReferenceRoleBindingFinalizationResult:
    """Purely record a Decision and atomically materialize its optional Binding."""

    return _finalize_generated_reference_eligible_asset_role_binding_workflow(
        request,
        promotion,
        request_status,
        requested_primary_bible,
        requested_primary_asset_version,
        final_status,
        binding_primary_bible,
        binding_primary_asset_version,
        admitted_png,
        selected_reference_role=selected_reference_role,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        checker_identity_bytes=checker_identity_bytes,
        checker_action_bytes=checker_action_bytes,
        binding_at=binding_at,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result
        ),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis
        ),
        whole_composite_role_suitability_result=whole_composite_role_suitability_result,
        whole_composite_role_suitability_basis=whole_composite_role_suitability_basis,
        non_exclusive_no_transform_boundary_result=(
            non_exclusive_no_transform_boundary_result
        ),
        non_exclusive_no_transform_boundary_basis=(
            non_exclusive_no_transform_boundary_basis
        ),
        decision_basis=decision_basis,
    )


def _verify_positive_pair_linkage(
    decision: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
    binding: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
) -> None:
    shared_fields = (
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "request_id",
        "request_sha256",
        "decision_id",
        "decision_sha256",
        "promotion_request_id",
        "promotion_request_sha256",
        "promotion_decision_id",
        "promotion_decision_sha256",
        "eligible_asset_sidecar_id",
        "eligible_asset_sidecar_sha256",
        "promotion_at",
        "promotion_evidence_valid_until",
        "qualification_decision_id",
        "qualification_decision_sha256",
        "qualification_valid_until",
        "manifest_id",
        "manifest_sha256",
        "manifest_valid_until",
        "reviewed_rights_scope",
        "status_subject_closure_id",
        "status_subject_closure_sha256",
        "binding_status_record_id",
        "binding_status_record_sha256",
        "binding_status_receipt_id",
        "binding_status_receipt_sha256",
        "binding_explicit_chain_set_sha256",
        "binding_coverage_set_sha256",
        "binding_joint_replay_sha256",
        "binding_as_of_assessment_sha256",
        "binding_as_of_status",
        "binding_at",
        "binding_status_valid_until",
        "role_binding_exclusivity_asserted",
        "complete_role_set_asserted",
        "global_role_uniqueness_asserted",
        "crop_applied",
        "split_applied",
        "transform_applied",
        "derived_media_created",
        "provider_input_eligible",
        "evidence_scope",
        *_ZERO_AUTHORITY_VALUES,
    )
    if any(getattr(binding, name) != getattr(decision, name) for name in shared_fields):
        _fail(
            "ATOMIC_OUTPUT_INVARIANT_VIOLATION",
            "positive Decision and Binding shared fields drifted",
        )
    if (
        binding.role_binding_target != decision.requested_role_binding_target
        or binding.primary_asset_binding != decision.binding_primary_asset_binding
    ):
        _fail(
            "ATOMIC_OUTPUT_INVARIANT_VIOLATION",
            "positive Decision and Binding nested values drifted",
        )


def _validate_finalization_result(
    value: GeneratedReferenceRoleBindingFinalizationResult,
) -> None:
    if type(value.decision) is not (
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1
    ):
        _fail("CONTRACT_FIELD_INVALID", "finalization Decision has the wrong exact type")
    decision = cast(
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
        _exact_formal_model(
            value.decision,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
            field="finalization Decision",
        ),
    )
    positive = decision.decision == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
    if value.binding is None:
        if positive:
            _fail(
                "ATOMIC_OUTPUT_INVARIANT_VIOLATION",
                "positive Decision cannot omit its atomic Binding",
            )
        return
    if type(value.binding) is not CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1:
        _fail("CONTRACT_FIELD_INVALID", "finalization Binding has the wrong exact type")
    if not positive:
        _fail(
            "BINDING_GATE_NOT_PASS",
            "a non-positive Decision cannot carry a Binding",
        )
    binding = cast(
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        _exact_formal_model(
            value.binding,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
            field="finalization Binding",
        ),
    )
    if (
        any(item.result != "PASS" for item in decision.gate_results)
        or decision.binding_issue_codes
        or not decision.binding_materialization_allowed
        or decision.binding_as_of_status != "CURRENT"
    ):
        _fail("BINDING_GATE_NOT_PASS", "positive Binding gates are not all PASS")
    _verify_positive_pair_linkage(decision, binding)


def _preflight_expected_finalization_prefix(
    expected: object,
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Preflight expected output through stage 5, deferring 16-19."""

    if type(expected) is not GeneratedReferenceRoleBindingFinalizationResult:
        _fail("CONTRACT_FIELD_INVALID", "expected finalization result type mismatch")
    decision_object = expected.decision
    binding_object = expected.binding
    decision_values: dict[str, object] | None = None
    binding_values: dict[str, object] | None = None
    if type(decision_object) is (
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1
    ):
        decision_values = _verify_formal_resource(
            decision_object,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
            field="expected Role-Binding Decision",
        )
    if type(binding_object) is CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1:
        binding_values = _verify_formal_resource(
            binding_object,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
            field="expected Eligible-Asset Role Binding",
        )
    if decision_values is None:
        _fail("CONTRACT_FIELD_INVALID", "expected Decision has the wrong exact type")
    if binding_object is not None and binding_values is None:
        _fail("CONTRACT_FIELD_INVALID", "expected Binding has the wrong exact type")
    structural_values: list[tuple[Mapping[str, object], type[BaseModel], str]] = [
        (
            decision_values,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
            "expected Role-Binding Decision",
        )
    ]
    if binding_values is not None:
        structural_values.append(
            (
                binding_values,
                CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
                "expected Eligible-Asset Role Binding",
            )
        )
    for values, model, field in structural_values:
        try:
            _sanitize_formal_structure(values, model)
        except GeneratedReferenceRoleBindingError:
            raise
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise GeneratedReferenceRoleBindingError(
                "CONTRACT_FIELD_INVALID", f"{field} structure is invalid"
            ) from exc
    _verify_policy_fields(decision_values, field="expected Role-Binding Decision")
    if binding_values is not None:
        _verify_policy_fields(
            binding_values, field="expected Eligible-Asset Role Binding"
        )
    _verify_formal_identity(
        decision_values,
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
        field="expected Role-Binding Decision",
    )
    if binding_values is not None:
        _verify_formal_identity(
            binding_values,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
            field="expected Eligible-Asset Role Binding",
        )
    return decision_values, binding_values


def verify_generated_reference_eligible_asset_role_binding_finalization(
    expected: GeneratedReferenceRoleBindingFinalizationResult,
    request: CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
    promotion: GeneratedReferenceRoleBindingPromotionClosureInput,
    request_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    requested_primary_bible: CharacterBible | SceneBible,
    requested_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    final_status: GeneratedReferenceAssetPromotionStatusClosureInput,
    binding_primary_bible: CharacterBible | SceneBible,
    binding_primary_asset_version: CharacterAssetVersion | SceneAssetVersion,
    admitted_png: GeneratedReferenceRoleBindingAdmittedPng,
    *,
    selected_reference_role: str,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    checker_identity_bytes: bytes,
    checker_action_bytes: bytes,
    binding_at: str,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_result: GateResult,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_basis: str,
    whole_composite_role_suitability_result: GateResult,
    whole_composite_role_suitability_basis: str,
    non_exclusive_no_transform_boundary_result: GateResult,
    non_exclusive_no_transform_boundary_basis: str,
    decision_basis: str,
) -> GeneratedReferenceRoleBindingFinalizationResult:
    """Freshly replay finalization and require exact Decision/optional-Binding bytes."""

    (
        _request_values,
        _maker_action,
        _checker_action,
        decision_values,
        binding_values,
    ) = _preflight_finalize_stage_inputs(
        request,
        promotion,
        request_status,
        requested_primary_bible,
        requested_primary_asset_version,
        final_status,
        binding_primary_bible,
        binding_primary_asset_version,
        admitted_png,
        selected_reference_role=selected_reference_role,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        checker_identity_bytes=checker_identity_bytes,
        checker_action_bytes=checker_action_bytes,
        binding_at=binding_at,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result
        ),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis
        ),
        whole_composite_role_suitability_result=whole_composite_role_suitability_result,
        whole_composite_role_suitability_basis=whole_composite_role_suitability_basis,
        non_exclusive_no_transform_boundary_result=(
            non_exclusive_no_transform_boundary_result
        ),
        non_exclusive_no_transform_boundary_basis=(
            non_exclusive_no_transform_boundary_basis
        ),
        decision_basis=decision_basis,
        expected_finalization=expected,
    )
    if decision_values is None:  # pragma: no cover - closed by combined preflight
        _fail("CONTRACT_FIELD_INVALID", "expected Decision is unavailable")
    expected_formal_surfaces: tuple[tuple[Mapping[str, object], str], ...] = (
        (decision_values, "expected Role-Binding Decision"),
    )
    if binding_values is not None:
        expected_formal_surfaces += (
            (binding_values, "expected Eligible-Asset Role Binding"),
        )
    rebuilt = _finalize_generated_reference_eligible_asset_role_binding_workflow(
        request,
        promotion,
        request_status,
        requested_primary_bible,
        requested_primary_asset_version,
        final_status,
        binding_primary_bible,
        binding_primary_asset_version,
        admitted_png,
        selected_reference_role=selected_reference_role,
        maker_identity_bytes=maker_identity_bytes,
        maker_action_bytes=maker_action_bytes,
        checker_identity_bytes=checker_identity_bytes,
        checker_action_bytes=checker_action_bytes,
        binding_at=binding_at,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result
        ),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=(
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis
        ),
        whole_composite_role_suitability_result=whole_composite_role_suitability_result,
        whole_composite_role_suitability_basis=whole_composite_role_suitability_basis,
        non_exclusive_no_transform_boundary_result=(
            non_exclusive_no_transform_boundary_result
        ),
        non_exclusive_no_transform_boundary_basis=(
            non_exclusive_no_transform_boundary_basis
        ),
        decision_basis=decision_basis,
        additional_authority_surfaces=expected_formal_surfaces,
        additional_prohibited_surfaces=expected_formal_surfaces,
        expected_decision_request_linkage=expected.decision,
        expected_gate_result=expected,
    )

    # Resource through prohibited stages have now run globally across supplied and
    # expected formal surfaces.  Exact reconstruction and pair atomicity remain.
    _complete_formal_workflow_boundary(
        expected.decision,
        decision_values,
        CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
        field="expected Role-Binding Decision",
    )
    if expected.binding is not None and binding_values is not None:
        _complete_formal_workflow_boundary(
            expected.binding,
            binding_values,
            CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
            field="expected Eligible-Asset Role Binding",
        )
    _validate_finalization_result(expected)
    if (
        expected.decision != rebuilt.decision
        or generated_reference_role_binding_contract_document_bytes(expected.decision)
        != generated_reference_role_binding_contract_document_bytes(rebuilt.decision)
    ):
        _fail("UPSTREAM_CLOSURE_MISMATCH", "Decision differs from fresh rebuild")
    if (expected.binding is None) != (rebuilt.binding is None):
        _fail("UPSTREAM_CLOSURE_MISMATCH", "Binding presence differs from fresh rebuild")
    if expected.binding is not None and rebuilt.binding is not None:
        if (
            expected.binding != rebuilt.binding
            or generated_reference_role_binding_contract_document_bytes(expected.binding)
            != generated_reference_role_binding_contract_document_bytes(rebuilt.binding)
        ):
            _fail("UPSTREAM_CLOSURE_MISMATCH", "Binding differs from fresh rebuild")
    return expected


_verify_policy_identity()


__all__ = [
    "CHARACTER_REFERENCE_ROLE_ORDER",
    "CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1",
    "CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1",
    "CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1",
    "GENERATED_REFERENCE_ROLE_BINDING_DECISION_SHA256_DOMAIN",
    "GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256",
    "GENERATED_REFERENCE_ROLE_BINDING_POLICY_ID",
    "GENERATED_REFERENCE_ROLE_BINDING_POLICY_VERSION",
    "GENERATED_REFERENCE_ROLE_BINDING_REQUEST_SHA256_DOMAIN",
    "GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN",
    "GENERATED_REFERENCE_ROLE_BINDING_SHA256_DOMAIN",
    "GENERATED_REFERENCE_ROLE_BINDING_TARGET_SHA256_DOMAIN",
    "GeneratedReferenceEligibleAssetRoleBindingTargetV1",
    "GeneratedReferenceRoleBindingAdmittedPng",
    "GeneratedReferenceRoleBindingError",
    "GeneratedReferenceRoleBindingErrorCodeV1",
    "GeneratedReferenceRoleBindingFinalizationResult",
    "GeneratedReferenceRoleBindingGateResultV1",
    "GeneratedReferenceRoleBindingPromotionClosureInput",
    "ROLE_BINDING_GATE_ORDER",
    "ROLE_BINDING_ISSUE_CODE_ORDER",
    "SCENE_REFERENCE_ROLE_ORDER",
    "admit_generated_reference_role_binding_png",
    "build_generated_reference_eligible_asset_role_binding_target",
    "build_generated_reference_role_binding_review_payload_projection",
    "build_generated_reference_role_binding_review_payload_sha256",
    "creative_sample_generated_reference_eligible_asset_role_binding_decision_projection",
    "creative_sample_generated_reference_eligible_asset_role_binding_decision_sha256",
    "creative_sample_generated_reference_eligible_asset_role_binding_projection",
    "creative_sample_generated_reference_eligible_asset_role_binding_request_projection",
    "creative_sample_generated_reference_eligible_asset_role_binding_request_sha256",
    "creative_sample_generated_reference_eligible_asset_role_binding_sha256",
    "finalize_generated_reference_eligible_asset_role_binding",
    "generated_reference_role_binding_checker_action_projection",
    "generated_reference_role_binding_contract_document_bytes",
    "generated_reference_role_binding_maker_action_projection",
    "generated_reference_role_binding_policy_projection",
    "generated_reference_role_binding_review_payload_projection",
    "generated_reference_role_binding_review_payload_sha256",
    "generated_reference_role_binding_target_projection",
    "generated_reference_role_binding_target_sha256",
    "prepare_generated_reference_eligible_asset_role_binding_request",
    "verify_generated_reference_eligible_asset_role_binding_finalization",
    "verify_generated_reference_eligible_asset_role_binding_request",
]
