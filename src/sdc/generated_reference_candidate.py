"""Offline generated-reference Candidate provenance and Qualification boundary.

This module implements the isolated, zero-authority core accepted by SDC-ADR-043.  It admits
caller-supplied immutable evidence and one explicitly named PNG, but it performs no Provider,
network, credential, Runtime, persistence, QC, publication, or asset-promotion operation.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import zlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from os import fstat
from pathlib import Path
from stat import FILE_ATTRIBUTE_REPARSE_POINT, S_ISREG
from typing import Annotated, ClassVar, Literal, NoReturn, Self, cast, get_args, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic.config import ExtraValues

from sdc.visual_reference_prompt_compiler import (
    CreativeSampleReferenceVisualPromptArtifactV1,
    VisualReferencePromptCompilerError,
    creative_sample_reference_visual_prompt_artifact_projection,
    creative_sample_reference_visual_prompt_artifact_sha256,
)

GENERATED_REFERENCE_PNG_TECHNICAL_RECORD_SHA256_DOMAIN = (
    b"sdc:generated-reference-png-technical-record:v1\0"
)
GENERATED_REFERENCE_PROVIDER_OUTPUT_SET_SHA256_DOMAIN = (
    b"sdc:generated-reference-provider-output-set:v1\0"
)
GENERATED_REFERENCE_PROVIDER_ATTEMPT_OUTCOME_SHA256_DOMAIN = (
    b"sdc:generated-reference-provider-attempt-outcome:v1\0"
)
GENERATED_REFERENCE_CANDIDATE_SHA256_DOMAIN = b"sdc:generated-reference-candidate:v1\0"
GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_REQUEST_SHA256_DOMAIN = (
    b"sdc:generated-reference-candidate-qualification-request:v1\0"
)
GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_DECISION_SHA256_DOMAIN = (
    b"sdc:generated-reference-candidate-qualification-decision:v1\0"
)

GENERATED_REFERENCE_QUALIFICATION_POLICY_ID = (
    "sdc.generated-reference-candidate-qualification-policy"
)
GENERATED_REFERENCE_QUALIFICATION_POLICY_VERSION = "1.0.0"
GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256 = (
    "9991a23c2d12c842691585ef11fe4edc5697bccb8086ec661c23a240375d359f"
)

_SCHEMA_VERSION = "1.0.0"
_MAX_DOCUMENT_BYTES = 262_144
_MAX_ARTIFACT_BYTES = 524_288
_MAX_PROMPT_BYTES = 65_536
_MAX_PNG_BYTES = 67_108_864
_MAX_JSON_DEPTH = 16
_MAX_CONTAINER_ITEMS = 64
_MAX_FORMAL_ROOT_ITEMS = 128
_MAX_HUMAN_REFERENCE_BYTES = 16_384
_MAX_RETAINED_RECORD_BYTES = 262_144

_PORTABLE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_LOWER_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_SEMANTIC_VERSION_PATTERN = r"^(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})$"
_UTC_SECONDS_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_OUTCOME_ID_PATTERN = r"^generated_reference_attempt_outcome_v1_[0-9a-f]{20}$"
_CANDIDATE_ID_PATTERN = r"^generated_reference_candidate_v1_[0-9a-f]{20}$"
_REQUEST_ID_PATTERN = r"^generated_reference_candidate_qualification_request_v1_[0-9a-f]{20}$"
_DECISION_ID_PATTERN = r"^generated_reference_candidate_qualification_decision_v1_[0-9a-f]{20}$"

PortableId = Annotated[str, Field(pattern=_PORTABLE_ID_PATTERN)]
LowerSha256 = Annotated[str, Field(pattern=_LOWER_SHA256_PATTERN)]
SemanticVersion = Annotated[str, Field(pattern=_SEMANTIC_VERSION_PATTERN)]

AssetPurpose = Literal["CHARACTER_REFERENCE_ASSET", "SCENE_REFERENCE_ASSET"]
TerminalDisposition = Literal[
    "VERIFIED_SUCCESS",
    "SUBMISSION_REJECTED",
    "PROVIDER_TASK_FAILED",
    "CANCELLED",
    "EXPIRED",
    "SUBMISSION_UNKNOWN",
    "PARTIAL_OUTPUT",
    "OUTPUT_INTEGRITY_FAILURE",
    "UNSUPPORTED_OUTPUT_CARDINALITY",
]
TerminalReasonCode = Literal[
    "SUBMISSION_REJECTED_BY_PROVIDER",
    "PROVIDER_TASK_REPORTED_FAILURE",
    "PROVIDER_TASK_CANCELLED",
    "PROVIDER_TASK_EXPIRED_OR_TIMED_OUT",
    "SUBMISSION_RESULT_UNKNOWN",
    "EXPECTED_OUTPUT_NOT_FULLY_AVAILABLE",
    "OUTPUT_BYTES_OR_TECHNICAL_RECORD_MISMATCH",
    "PROVIDER_REPORTED_UNSUPPORTED_OUTPUT_COUNT",
]
EvidenceCategory = Literal[
    "PROVIDER_ATTEMPT_PROVENANCE",
    "PROVIDER_TERMINAL_OBSERVATION",
    "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
    "PROVIDER_TERMS_AT_SUBMISSION",
    "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    "BRAND_AND_PROTECTED_CONTENT",
    "REMOTE_PROCESSING_AUTHORIZATION_AT_SUBMISSION",
    "RETENTION_POLICY_AT_SUBMISSION",
    "TRAINING_USE_POLICY_AT_SUBMISSION",
]
QualificationGate = Literal[
    "PROVENANCE_CLOSURE",
    "PROMPT_AND_RECEIPT_CLOSURE",
    "OUTPUT_SET_COMPLETENESS",
    "TECHNICAL_MEDIA_FIT",
    "SUBJECT_AND_ASSET_PURPOSE_MATCH",
    "IDENTITY_CONTINUITY",
    "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
    "PROVIDER_GENERATION_PROVENANCE",
    "PROVIDER_OUTPUT_TERMS",
    "COPYRIGHT_AND_COMMERCIAL_SCOPE",
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    "BRAND_AND_PROTECTED_CONTENT",
    "REMOTE_PROCESSING_AUTHORIZED_AT_SUBMISSION",
    "RETENTION_POLICY_ALIGNMENT",
    "TRAINING_USE_POLICY_ALIGNMENT",
]
QualificationIssueCode = Literal[
    "PROVENANCE_CLOSURE_UNRESOLVED",
    "PROMPT_AND_RECEIPT_CLOSURE_UNRESOLVED",
    "OUTPUT_SET_COMPLETENESS_UNRESOLVED",
    "TECHNICAL_MEDIA_FIT_UNRESOLVED",
    "SUBJECT_AND_ASSET_PURPOSE_UNRESOLVED_OR_MISMATCH",
    "IDENTITY_CONTINUITY_UNRESOLVED",
    "INPUT_RIGHTS_UNRESOLVED",
    "PROVIDER_GENERATION_PROVENANCE_UNRESOLVED",
    "PROVIDER_OUTPUT_TERMS_UNRESOLVED",
    "COPYRIGHT_OR_COMMERCIAL_SCOPE_UNRESOLVED",
    "LIKENESS_PRIVACY_OR_SENSITIVE_DATA_UNRESOLVED",
    "BRAND_OR_PROTECTED_CONTENT_UNRESOLVED",
    "REMOTE_PROCESSING_AUTHORIZATION_UNRESOLVED_OR_ABSENT",
    "RETENTION_STATUS_UNRESOLVED_OR_NONCOMPLIANT",
    "TRAINING_USE_POLICY_UNRESOLVED_OR_NOT_PROHIBITED",
    "QUALIFIER_REJECTED",
]
QualificationDecision = Literal[
    "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
    "NEEDS_HUMAN_REVIEW",
    "REJECTED",
]

EVIDENCE_CATEGORY_ORDER: tuple[EvidenceCategory, ...] = (
    "PROVIDER_ATTEMPT_PROVENANCE",
    "PROVIDER_TERMINAL_OBSERVATION",
    "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
    "PROVIDER_TERMS_AT_SUBMISSION",
    "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    "BRAND_AND_PROTECTED_CONTENT",
    "REMOTE_PROCESSING_AUTHORIZATION_AT_SUBMISSION",
    "RETENTION_POLICY_AT_SUBMISSION",
    "TRAINING_USE_POLICY_AT_SUBMISSION",
)
QUALIFICATION_GATE_ORDER: tuple[QualificationGate, ...] = (
    "PROVENANCE_CLOSURE",
    "PROMPT_AND_RECEIPT_CLOSURE",
    "OUTPUT_SET_COMPLETENESS",
    "TECHNICAL_MEDIA_FIT",
    "SUBJECT_AND_ASSET_PURPOSE_MATCH",
    "IDENTITY_CONTINUITY",
    "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
    "PROVIDER_GENERATION_PROVENANCE",
    "PROVIDER_OUTPUT_TERMS",
    "COPYRIGHT_AND_COMMERCIAL_SCOPE",
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    "BRAND_AND_PROTECTED_CONTENT",
    "REMOTE_PROCESSING_AUTHORIZED_AT_SUBMISSION",
    "RETENTION_POLICY_ALIGNMENT",
    "TRAINING_USE_POLICY_ALIGNMENT",
)
QUALIFICATION_ISSUE_CODE_ORDER: tuple[QualificationIssueCode, ...] = (
    "PROVENANCE_CLOSURE_UNRESOLVED",
    "PROMPT_AND_RECEIPT_CLOSURE_UNRESOLVED",
    "OUTPUT_SET_COMPLETENESS_UNRESOLVED",
    "TECHNICAL_MEDIA_FIT_UNRESOLVED",
    "SUBJECT_AND_ASSET_PURPOSE_UNRESOLVED_OR_MISMATCH",
    "IDENTITY_CONTINUITY_UNRESOLVED",
    "INPUT_RIGHTS_UNRESOLVED",
    "PROVIDER_GENERATION_PROVENANCE_UNRESOLVED",
    "PROVIDER_OUTPUT_TERMS_UNRESOLVED",
    "COPYRIGHT_OR_COMMERCIAL_SCOPE_UNRESOLVED",
    "LIKENESS_PRIVACY_OR_SENSITIVE_DATA_UNRESOLVED",
    "BRAND_OR_PROTECTED_CONTENT_UNRESOLVED",
    "REMOTE_PROCESSING_AUTHORIZATION_UNRESOLVED_OR_ABSENT",
    "RETENTION_STATUS_UNRESOLVED_OR_NONCOMPLIANT",
    "TRAINING_USE_POLICY_UNRESOLVED_OR_NOT_PROHIBITED",
    "QUALIFIER_REJECTED",
)

_GATE_EVIDENCE_CATEGORIES: dict[QualificationGate, tuple[EvidenceCategory, ...]] = {
    "PROVENANCE_CLOSURE": EVIDENCE_CATEGORY_ORDER,
    "PROMPT_AND_RECEIPT_CLOSURE": (),
    "OUTPUT_SET_COMPLETENESS": (
        "PROVIDER_ATTEMPT_PROVENANCE",
        "PROVIDER_TERMINAL_OBSERVATION",
    ),
    "TECHNICAL_MEDIA_FIT": (),
    "SUBJECT_AND_ASSET_PURPOSE_MATCH": ("INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",),
    "IDENTITY_CONTINUITY": (
        "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
        "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    ),
    "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION": ("INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",),
    "PROVIDER_GENERATION_PROVENANCE": (
        "PROVIDER_ATTEMPT_PROVENANCE",
        "PROVIDER_TERMINAL_OBSERVATION",
    ),
    "PROVIDER_OUTPUT_TERMS": ("PROVIDER_TERMS_AT_SUBMISSION",),
    "COPYRIGHT_AND_COMMERCIAL_SCOPE": ("OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",),
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA": ("LIKENESS_PRIVACY_AND_SENSITIVE_DATA",),
    "BRAND_AND_PROTECTED_CONTENT": ("BRAND_AND_PROTECTED_CONTENT",),
    "REMOTE_PROCESSING_AUTHORIZED_AT_SUBMISSION": (
        "PROVIDER_ATTEMPT_PROVENANCE",
        "REMOTE_PROCESSING_AUTHORIZATION_AT_SUBMISSION",
    ),
    "RETENTION_POLICY_ALIGNMENT": (
        "PROVIDER_TERMS_AT_SUBMISSION",
        "RETENTION_POLICY_AT_SUBMISSION",
    ),
    "TRAINING_USE_POLICY_ALIGNMENT": (
        "PROVIDER_TERMS_AT_SUBMISSION",
        "TRAINING_USE_POLICY_AT_SUBMISSION",
    ),
}

_SUBMISSION_TIME_CATEGORIES = frozenset(
    {
        "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
        "PROVIDER_TERMS_AT_SUBMISSION",
        "REMOTE_PROCESSING_AUTHORIZATION_AT_SUBMISSION",
        "RETENTION_POLICY_AT_SUBMISSION",
        "TRAINING_USE_POLICY_AT_SUBMISSION",
    }
)

_POLICY_PROJECTION: dict[str, object] = {
    "decision_mapping": {
        "all_pass": "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
        "any_fail": "REJECTED",
        "otherwise": "NEEDS_HUMAN_REVIEW",
    },
    "evidence_category_order": list(EVIDENCE_CATEGORY_ORDER),
    "gate_evidence_category_map": {
        gate: list(categories) for gate, categories in _GATE_EVIDENCE_CATEGORIES.items()
    },
    "gate_order": list(QUALIFICATION_GATE_ORDER),
    "issue_code_order": list(QUALIFICATION_ISSUE_CODE_ORDER),
    "policy_id": GENERATED_REFERENCE_QUALIFICATION_POLICY_ID,
    "policy_version": GENERATED_REFERENCE_QUALIFICATION_POLICY_VERSION,
    "qualification_decision_max_age_seconds": 86_400,
    "qualification_scope": "GENERATED_REFERENCE_CANDIDATE_INTAKE_ONLY",
    "request_max_age_seconds": 86_400,
    "retention_rule": (
        "NO_RETENTION_OR_PREAUTHORIZED_BOUNDED_RETENTION_WITH_DELETION_EVIDENCE_REQUIRED"
    ),
    "training_rule": "PROVIDER_TRAINING_USE_MUST_BE_PROHIBITED_AT_SUBMISSION",
}


class GeneratedReferenceCandidateError(ValueError):
    """The ADR-043 offline evidence boundary failed closed."""


def _invalid(message: str) -> NoReturn:
    raise ValueError(message)


def _validate_canonical_string(value: str, *, field: str) -> str:
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
    return value


def _validate_human_text(value: str, *, field: str, maximum: int) -> str:
    value = _validate_canonical_string(value, field=field)
    if not 1 <= len(value) <= maximum or value != value.strip():
        _invalid(f"{field} must contain 1..{maximum} trimmed code points")
    for character in value:
        codepoint = ord(character)
        if unicodedata.category(character) in {"Cc", "Cs"} or codepoint in {
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
        }:
            _invalid(f"{field} contains a prohibited control character")
    return value


def _validate_json_tree(
    value: object,
    *,
    field: str = "value",
    depth: int = 1,
    root_maximum: int = _MAX_CONTAINER_ITEMS,
) -> None:
    if depth > _MAX_JSON_DEPTH:
        _invalid(f"{field} exceeds the maximum nesting depth")
    if value is None or type(value) in {bool, int, str}:
        if type(value) is str:
            _validate_canonical_string(value, field=field)
        return
    if type(value) is float:
        _invalid(f"{field} contains a floating-point value")
    if isinstance(value, (list, tuple)):
        if len(value) > _MAX_CONTAINER_ITEMS:
            _invalid(f"{field} contains too many items")
        for index, item in enumerate(value):
            _validate_json_tree(
                item,
                field=f"{field}[{index}]",
                depth=depth + 1,
                root_maximum=root_maximum,
            )
        return
    if isinstance(value, dict):
        maximum = root_maximum if depth == 1 else _MAX_CONTAINER_ITEMS
        if len(value) > maximum:
            _invalid(f"{field} contains too many keys")
        for key, item in value.items():
            if type(key) is not str:
                _invalid(f"{field} contains a non-string key")
            _validate_canonical_string(key, field=f"{field} key")
            _validate_json_tree(
                item,
                field=f"{field}.{key}",
                depth=depth + 1,
                root_maximum=root_maximum,
            )
        return
    _invalid(f"{field} is outside the canonical JSON type set")


def _canonical_compact_json(
    value: object,
    *,
    root_maximum: int = _MAX_CONTAINER_ITEMS,
) -> bytes:
    _validate_json_tree(value, root_maximum=root_maximum)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _persistent_document_bytes(
    value: object,
    *,
    root_maximum: int = _MAX_CONTAINER_ITEMS,
) -> bytes:
    _validate_json_tree(value, root_maximum=root_maximum)
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


def _json_tree_exactly_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is list:
        left_items = cast(list[object], left)
        right_items = cast(list[object], right)
        return len(left_items) == len(right_items) and all(
            _json_tree_exactly_equal(left_item, right_item)
            for left_item, right_item in zip(left_items, right_items, strict=True)
        )
    if type(left) is dict:
        left_mapping = cast(dict[str, object], left)
        right_mapping = cast(dict[str, object], right)
        return left_mapping.keys() == right_mapping.keys() and all(
            _json_tree_exactly_equal(left_mapping[key], right_mapping[key]) for key in left_mapping
        )
    return left == right


def _semantic_sha256(domain: bytes, projection: object) -> str:
    root_maximum = (
        _MAX_FORMAL_ROOT_ITEMS
        if domain
        in {
            GENERATED_REFERENCE_PROVIDER_ATTEMPT_OUTCOME_SHA256_DOMAIN,
            GENERATED_REFERENCE_CANDIDATE_SHA256_DOMAIN,
            GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_REQUEST_SHA256_DOMAIN,
            GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_DECISION_SHA256_DOMAIN,
        }
        else _MAX_CONTAINER_ITEMS
    )
    return hashlib.sha256(
        domain + _canonical_compact_json(projection, root_maximum=root_maximum)
    ).hexdigest()


def _raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class _DuplicateKeyError(ValueError):
    pass


def _object_from_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON number is prohibited: {value}")


def _admit_persistent_json(
    raw: bytes,
    *,
    maximum: int,
    field: str,
    root_maximum: int = _MAX_CONTAINER_ITEMS,
) -> dict[str, object]:
    if type(raw) is not bytes or not 1 <= len(raw) <= maximum:
        _invalid(f"{field} must be exact bytes in 1..{maximum}")
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        _invalid(f"{field} must be UTF-8 without BOM and LF-only")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_object_from_pairs,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError, _DuplicateKeyError, ValueError) as exc:
        raise ValueError(f"{field} is not strict JSON") from exc
    if type(value) is not dict:
        _invalid(f"{field} must contain one JSON object")
    _validate_json_tree(value, field=field, root_maximum=root_maximum)
    if _persistent_document_bytes(value, root_maximum=root_maximum) != raw:
        _invalid(f"{field} is not the exact persistent canonical JSON encoding")
    return cast(dict[str, object], value)


def _utc_seconds(value: str, *, field: str) -> str:
    if type(value) is not str or re.fullmatch(_UTC_SECONDS_PATTERN, value) is None:
        _invalid(f"{field} must be canonical UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        _invalid(f"{field} must be canonical UTC seconds")
    return value


def _parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _finite_or_perpetual(value: str, *, field: str) -> str:
    if value == "PERPETUAL":
        return value
    return _utc_seconds(value, field=field)


def _before(value: str, upper: str) -> bool:
    return upper == "PERPETUAL" or _parse_utc(value) < _parse_utc(upper)


def _minimum_finite(values: tuple[str, ...]) -> str:
    finite = tuple(value for value in values if value != "PERPETUAL")
    return min(finite) if finite else "PERPETUAL"


def _bounded_valid_until(start: str, evidence_valid_until: str) -> str:
    try:
        cap = _format_utc(_parse_utc(start) + timedelta(seconds=86_400))
    except OverflowError:
        if evidence_valid_until != "PERPETUAL":
            return evidence_valid_until
        _invalid("validity interval cannot derive a representable 24-hour UTC cap")
    if evidence_valid_until == "PERPETUAL":
        return cap
    return min(cap, evidence_valid_until)


_policy_bytes = _canonical_compact_json(_POLICY_PROJECTION)
if len(_policy_bytes) != 3_604 or _raw_sha256(_policy_bytes) != (
    GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256
):
    raise RuntimeError("ADR-043 frozen Qualification policy projection drifted")


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )
    _raw_json_max_bytes: ClassVar[int] = _MAX_DOCUMENT_BYTES
    _root_json_max_items: ClassVar[int] = _MAX_CONTAINER_ITEMS

    @model_validator(mode="before")
    @classmethod
    def reject_subclass_instances(cls, value: object) -> object:
        if isinstance(value, BaseModel) and type(value) is not cls:
            raise ValueError(f"{cls.__name__} rejects subclass model values")
        return value

    @model_validator(mode="before")
    @classmethod
    def reject_numeric_boolean_coercion(cls, value: object) -> object:
        if isinstance(value, dict):
            supplied = value
        elif type(value) is cls:
            supplied = {field_name: getattr(value, field_name) for field_name in cls.model_fields}
        else:
            return value
        for field_name, field_info in cls.model_fields.items():
            if field_name not in supplied:
                continue
            annotation = field_info.annotation
            expected_type: type[int] | type[bool] | None = None
            if annotation is int:
                expected_type = int
            elif annotation is bool:
                expected_type = bool
            elif get_origin(annotation) is Literal:
                literal_types = {type(item) for item in get_args(annotation)}
                if literal_types == {int}:
                    expected_type = int
                elif literal_types == {bool}:
                    expected_type = bool
            if expected_type is not None and type(supplied[field_name]) is not expected_type:
                _invalid(
                    f"{field_name} must be an exact JSON "
                    f"{'integer' if expected_type is int else 'boolean'}"
                )
        return value

    @classmethod
    def model_validate(
        cls,
        obj: object,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        from_attributes: bool | None = None,
        context: object | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        del strict, extra, from_attributes
        return super().model_validate(
            obj,
            strict=True,
            extra="forbid",
            from_attributes=False,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: object | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        del strict, extra
        if type(json_data) is str:
            try:
                raw = json_data.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError(f"{cls.__name__} JSON is not UTF-8") from exc
        elif isinstance(json_data, (bytes, bytearray)):
            raw = bytes(json_data)
        else:
            raise TypeError("json_data must be str, bytes, or bytearray")
        admitted = _admit_persistent_json(
            raw,
            maximum=cls._raw_json_max_bytes,
            field=cls.__name__,
            root_maximum=cls._root_json_max_items,
        )
        validated = super().model_validate_json(
            raw,
            strict=False,
            extra="forbid",
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )
        if not _json_tree_exactly_equal(validated.model_dump(mode="json"), admitted):
            _invalid(f"{cls.__name__} JSON required prohibited type coercion")
        return validated


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

    @model_validator(mode="before")
    @classmethod
    def validate_zero_authority_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        boolean_fields = (
            "generation_authorized",
            "execution_authorized",
            "publication_authorized",
            "remote_processing_allowed",
            "retention_allowed",
            "training_allowed",
            "publication_allowed",
            "automated_execution_allowed",
            "grants_rights",
            "grants_qualification",
            "grants_execution_authority",
            "eligible_for_asset_promotion",
            "replaces_rights_manifest",
        )
        integer_fields = (
            "authorized_attempts",
            "authorized_cost_cny",
            "posts_allowed",
            "provider_requests",
        )
        for field_name in boolean_fields:
            if field_name in value and type(value[field_name]) is not bool:
                _invalid(f"{field_name} must be an exact JSON boolean")
        for field_name in integer_fields:
            if field_name in value and (
                type(value[field_name]) is not int or value[field_name] != 0
            ):
                _invalid(f"{field_name} must be the exact JSON integer zero")
        return value


def _zero_authority_values() -> dict[str, object]:
    return {
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


class GeneratedReferencePngTechnicalRecordV1(_StrictFrozenModel):
    media_type: Literal["image/png"]
    width: Annotated[int, Field(ge=512, le=4096)]
    height: Annotated[int, Field(ge=512, le=4096)]
    bit_depth: Literal[8]
    color_space: Literal["RGB", "RGBA"]
    alpha_status: Literal["ABSENT", "OPAQUE", "NON_OPAQUE"]
    interlaced: Literal[False]
    animation_frame_count: Literal[1]
    metadata_status: Literal["ABSENT", "PRESENT"]
    metadata_chunk_types: Annotated[tuple[str, ...], Field(max_length=32)]
    png_signature_valid: Literal[True]
    ihdr_count: Literal[1]
    idat_present: Literal[True]
    iend_count: Literal[1]
    chunk_crc_valid: Literal[True]
    unknown_critical_chunk_absent: Literal[True]
    apng_chunks_absent: Literal[True]
    trailing_bytes_count: Literal[0]
    decompressed_pixel_bytes: Annotated[int, Field(ge=786_432, le=_MAX_PNG_BYTES)]

    @field_validator("metadata_chunk_types")
    @classmethod
    def validate_metadata_types(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            _invalid("metadata_chunk_types must be unique in first-occurrence order")
        if any(re.fullmatch(r"[A-Za-z]{4}", item) is None for item in value):
            _invalid("metadata_chunk_types contains an invalid PNG chunk type")
        return value

    @model_validator(mode="after")
    def validate_record(self) -> GeneratedReferencePngTechnicalRecordV1:
        channels = 3 if self.color_space == "RGB" else 4
        if self.decompressed_pixel_bytes != self.width * self.height * channels:
            _invalid("decompressed_pixel_bytes does not match dimensions and color space")
        if self.color_space == "RGB" and self.alpha_status != "ABSENT":
            _invalid("RGB requires alpha_status=ABSENT")
        if self.color_space == "RGBA" and self.alpha_status == "ABSENT":
            _invalid("RGBA requires an explicit alpha status")
        expected_status = "ABSENT" if not self.metadata_chunk_types else "PRESENT"
        if self.metadata_status != expected_status:
            _invalid("metadata_status does not match metadata_chunk_types")
        return self


class GeneratedReferenceOutputDescriptorV1(_StrictFrozenModel):
    ordinal: Literal[0]
    media_type: Literal["image/png"]
    content_sha256: LowerSha256
    size_bytes: Annotated[int, Field(ge=1, le=_MAX_PNG_BYTES)]
    technical_record: GeneratedReferencePngTechnicalRecordV1
    technical_record_sha256: LowerSha256
    regular_file_verified: Literal[True]
    symlink_absent: Literal[True]
    reparse_point_absent: Literal[True]
    admission_transform_performed: Literal[False]

    @model_validator(mode="after")
    def validate_technical_digest(self) -> GeneratedReferenceOutputDescriptorV1:
        expected = _semantic_sha256(
            GENERATED_REFERENCE_PNG_TECHNICAL_RECORD_SHA256_DOMAIN,
            _png_technical_record_projection_unchecked(self.technical_record),
        )
        if self.technical_record_sha256 != expected:
            _invalid("technical_record_sha256 does not bind the exact PNG record")
        return self


class GeneratedReferenceQualificationEvidenceReferenceV1(_StrictFrozenModel):
    category: EvidenceCategory
    record_id: PortableId
    document_profile: PortableId
    media_type: Literal["application/json"]
    document_size_bytes: Annotated[int, Field(ge=1, le=_MAX_RETAINED_RECORD_BYTES)]
    document_sha256: LowerSha256
    observed_at: str
    effective_from: str
    effective_until: str
    evidence_valid_until: str

    @field_validator("observed_at", "effective_from")
    @classmethod
    def validate_finite_times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @field_validator("effective_until", "evidence_valid_until")
    @classmethod
    def validate_upper_times(cls, value: str, info: ValidationInfo) -> str:
        return _finite_or_perpetual(value, field=str(info.field_name))

    @model_validator(mode="after")
    def validate_intervals(self) -> GeneratedReferenceQualificationEvidenceReferenceV1:
        if not _before(self.effective_from, self.effective_until):
            _invalid("evidence effective interval must be non-empty and half-open")
        if not _before(self.observed_at, self.evidence_valid_until):
            _invalid("observed_at must precede evidence_valid_until")
        return self


@dataclass(frozen=True, slots=True)
class GeneratedReferenceQualificationEvidenceInput:
    reference: GeneratedReferenceQualificationEvidenceReferenceV1
    document_bytes: bytes


class GeneratedReferenceQualificationGateResultV1(_StrictFrozenModel):
    gate: QualificationGate
    result: Literal["PASS", "FAIL", "INDETERMINATE"]
    evidence_record_ids: Annotated[tuple[PortableId, ...], Field(max_length=10)]
    basis: Annotated[str, Field(min_length=1, max_length=1000)]

    @field_validator("evidence_record_ids")
    @classmethod
    def validate_record_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            _invalid("evidence_record_ids must be unique")
        return value

    @field_validator("basis")
    @classmethod
    def validate_basis(cls, value: str) -> str:
        return _validate_human_text(value, field="basis", maximum=1000)


class CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1(_ZeroAuthorityModel):
    _root_json_max_items: ClassVar[int] = _MAX_FORMAL_ROOT_ITEMS

    schema_version: Literal["1.0.0"]
    document_type: Literal["sdc.creative-sample-generated-reference-provider-attempt-outcome-v1"]
    outcome_purpose: Literal["CALLER_ASSERTED_IMMUTABLE_PROVIDER_ATTEMPT_OUTCOME_EVIDENCE_ONLY"]
    outcome_id: Annotated[str, Field(pattern=_OUTCOME_ID_PATTERN)]
    outcome_sha256: LowerSha256
    reference_prompt_artifact_sha256: LowerSha256
    asset_purpose: AssetPurpose
    subject_id: PortableId
    expected_active_asset_version_id: PortableId
    expected_active_asset_content_sha256: LowerSha256
    profile_id: PortableId
    profile_version: SemanticVersion
    profile_sha256: LowerSha256
    catalog_version: SemanticVersion
    catalog_sha256: LowerSha256
    render_input_sha256: LowerSha256
    submitted_prompt_sha256: LowerSha256
    submitted_prompt_size_bytes: Annotated[int, Field(ge=1, le=_MAX_PROMPT_BYTES)]
    prompt_render_receipt_sha256: LowerSha256
    provider: PortableId
    model: PortableId
    provider_region: PortableId
    provider_terms_snapshot_id: PortableId
    provider_terms_snapshot_sha256: LowerSha256
    provider_terms_observed_at: str
    provider_terms_valid_from: str
    provider_terms_valid_until: str
    attempt_provenance_record_sha256: LowerSha256
    terminal_observation_record_sha256: LowerSha256
    historical_execution_authorization_status: Literal[
        "CLAIMED_PRESENT", "CLAIMED_ABSENT", "UNKNOWN"
    ]
    attempt_ordinal: Literal[1]
    submitted_input_material_count: Literal[0]
    submitted_at: str
    terminal_observed_at: str
    terminal_disposition: TerminalDisposition
    terminal_reason_code: TerminalReasonCode | None
    provider_task_reference_status: Literal["PRESENT_IN_RETAINED_RECORD", "ABSENT"]
    expected_output_count: Literal[1]
    reported_output_count_bounded: Annotated[int, Field(ge=0, le=64)]
    reported_output_count_overflow: bool
    verified_output_count: Annotated[int, Field(ge=0, le=1)]
    output_descriptors: Annotated[
        tuple[GeneratedReferenceOutputDescriptorV1, ...], Field(max_length=1)
    ]
    output_set_sha256: LowerSha256
    observed_provider_request_count: Literal[1]

    @field_validator(
        "provider_terms_observed_at",
        "provider_terms_valid_from",
        "submitted_at",
        "terminal_observed_at",
    )
    @classmethod
    def validate_finite_times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @field_validator("provider_terms_valid_until")
    @classmethod
    def validate_terms_until(cls, value: str) -> str:
        return _finite_or_perpetual(value, field="provider_terms_valid_until")

    @model_validator(mode="before")
    @classmethod
    def validate_exact_count_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        for field_name in (
            "submitted_prompt_size_bytes",
            "attempt_ordinal",
            "submitted_input_material_count",
            "expected_output_count",
            "reported_output_count_bounded",
            "verified_output_count",
            "observed_provider_request_count",
        ):
            if field_name in value and type(value[field_name]) is not int:
                _invalid(f"{field_name} must be an exact JSON integer")
        if "reported_output_count_overflow" in value and (
            type(value["reported_output_count_overflow"]) is not bool
        ):
            _invalid("reported_output_count_overflow must be an exact JSON boolean")
        return value

    @model_validator(mode="after")
    def validate_outcome(self) -> CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1:
        _validate_outcome_matrix(self)
        if _parse_utc(self.submitted_at) > _parse_utc(self.terminal_observed_at):
            _invalid("submitted_at must not follow terminal_observed_at")
        if _parse_utc(self.provider_terms_observed_at) > _parse_utc(self.submitted_at):
            _invalid("Provider terms must be observed no later than submission")
        if _parse_utc(self.provider_terms_valid_from) > _parse_utc(
            self.submitted_at
        ) or not _before(self.submitted_at, self.provider_terms_valid_until):
            _invalid("Provider terms were not effective at submission")
        expected_output_set = _semantic_sha256(
            GENERATED_REFERENCE_PROVIDER_OUTPUT_SET_SHA256_DOMAIN,
            _provider_output_set_projection_unchecked(self),
        )
        if self.output_set_sha256 != expected_output_set:
            _invalid("output_set_sha256 does not bind the exact Output Set")
        expected_sha = _semantic_sha256(
            GENERATED_REFERENCE_PROVIDER_ATTEMPT_OUTCOME_SHA256_DOMAIN,
            _outcome_projection_unchecked(self),
        )
        if self.outcome_sha256 != expected_sha:
            _invalid("outcome_sha256 does not bind the exact Outcome projection")
        if self.outcome_id != f"generated_reference_attempt_outcome_v1_{expected_sha[:20]}":
            _invalid("outcome_id does not agree with outcome_sha256")
        _require_model_size(self, field="Outcome")
        return self


class CreativeSampleGeneratedReferenceCandidateV1(_ZeroAuthorityModel):
    _root_json_max_items: ClassVar[int] = _MAX_FORMAL_ROOT_ITEMS

    schema_version: Literal["1.0.0"]
    document_type: Literal["sdc.creative-sample-generated-reference-candidate-v1"]
    candidate_purpose: Literal["GENERATED_REFERENCE_MEDIA_PROVENANCE_EVIDENCE_ONLY"]
    candidate_state: Literal["CAPTURED_UNQUALIFIED"]
    candidate_id: Annotated[str, Field(pattern=_CANDIDATE_ID_PATTERN)]
    candidate_sha256: LowerSha256
    origin_claim: Literal["CALLER_ASSERTED_PROVIDER_GENERATED_REFERENCE_MEDIA"]
    origin_assurance: Literal["UNAUTHENTICATED_CALLER_EVIDENCE_NOT_YET_HUMAN_QUALIFIED"]
    reference_prompt_artifact_sha256: LowerSha256
    provider_attempt_outcome_id: Annotated[str, Field(pattern=_OUTCOME_ID_PATTERN)]
    provider_attempt_outcome_sha256: LowerSha256
    output_set_sha256: LowerSha256
    output_ordinal: Literal[0]
    asset_purpose: AssetPurpose
    subject_id: PortableId
    expected_active_asset_version_id: PortableId
    expected_active_asset_content_sha256: LowerSha256
    profile_id: PortableId
    profile_version: SemanticVersion
    profile_sha256: LowerSha256
    catalog_version: SemanticVersion
    catalog_sha256: LowerSha256
    render_input_sha256: LowerSha256
    prompt_sha256: LowerSha256
    prompt_size_bytes: Annotated[int, Field(ge=1, le=_MAX_PROMPT_BYTES)]
    prompt_render_receipt_sha256: LowerSha256
    provider: PortableId
    model: PortableId
    provider_region: PortableId
    provider_terms_snapshot_id: PortableId
    provider_terms_snapshot_sha256: LowerSha256
    provider_terms_valid_from: str
    provider_terms_valid_until: str
    attempt_provenance_record_sha256: LowerSha256
    terminal_observation_record_sha256: LowerSha256
    historical_execution_authorization_status: Literal[
        "CLAIMED_PRESENT", "CLAIMED_ABSENT", "UNKNOWN"
    ]
    attempt_ordinal: Literal[1]
    submitted_input_material_count: Literal[0]
    media_type: Literal["image/png"]
    media_content_sha256: LowerSha256
    media_size_bytes: Annotated[int, Field(ge=1, le=_MAX_PNG_BYTES)]
    media_width: Annotated[int, Field(ge=512, le=4096)]
    media_height: Annotated[int, Field(ge=512, le=4096)]
    media_technical_record_sha256: LowerSha256
    qualification_decision_embedded: Literal[False]
    rights_manifest_embedded: Literal[False]
    current_status_assessment_embedded: Literal[False]

    @field_validator("provider_terms_valid_from")
    @classmethod
    def validate_terms_from(cls, value: str) -> str:
        return _utc_seconds(value, field="provider_terms_valid_from")

    @field_validator("provider_terms_valid_until")
    @classmethod
    def validate_terms_until(cls, value: str) -> str:
        return _finite_or_perpetual(value, field="provider_terms_valid_until")

    @model_validator(mode="after")
    def validate_candidate(self) -> CreativeSampleGeneratedReferenceCandidateV1:
        expected_sha = _semantic_sha256(
            GENERATED_REFERENCE_CANDIDATE_SHA256_DOMAIN,
            _candidate_projection_unchecked(self),
        )
        if self.candidate_sha256 != expected_sha:
            _invalid("candidate_sha256 does not bind the exact Candidate projection")
        if self.candidate_id != f"generated_reference_candidate_v1_{expected_sha[:20]}":
            _invalid("candidate_id does not agree with candidate_sha256")
        _require_model_size(self, field="Candidate")
        return self


class CreativeSampleGeneratedReferenceCandidateQualificationRequestV1(_ZeroAuthorityModel):
    _root_json_max_items: ClassVar[int] = _MAX_FORMAL_ROOT_ITEMS

    schema_version: Literal["1.0.0"]
    document_type: Literal[
        "sdc.creative-sample-generated-reference-candidate-qualification-request-v1"
    ]
    request_id: Annotated[str, Field(pattern=_REQUEST_ID_PATTERN)]
    request_sha256: LowerSha256
    qualification_scope: Literal["GENERATED_REFERENCE_CANDIDATE_INTAKE_ONLY"]
    policy_id: Literal["sdc.generated-reference-candidate-qualification-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "9991a23c2d12c842691585ef11fe4edc5697bccb8086ec661c23a240375d359f"
    ]
    candidate_id: Annotated[str, Field(pattern=_CANDIDATE_ID_PATTERN)]
    candidate_sha256: LowerSha256
    provider_attempt_outcome_id: Annotated[str, Field(pattern=_OUTCOME_ID_PATTERN)]
    provider_attempt_outcome_sha256: LowerSha256
    reference_prompt_artifact_sha256: LowerSha256
    media_content_sha256: LowerSha256
    media_technical_record_sha256: LowerSha256
    submitted_at: str
    requested_at: str
    request_valid_until: str
    evidence_valid_until: str
    evidence_preparer_ref_sha256: LowerSha256
    evidence_preparer_record_sha256: LowerSha256
    evidence_refs: Annotated[
        tuple[GeneratedReferenceQualificationEvidenceReferenceV1, ...],
        Field(min_length=10, max_length=10),
    ]
    status: Literal["QUALIFICATION_REQUESTED"]
    rights_manifest_embedded: Literal[False]
    current_status_assessment_embedded: Literal[False]

    @field_validator("submitted_at", "requested_at", "request_valid_until")
    @classmethod
    def validate_finite_times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @field_validator("evidence_valid_until")
    @classmethod
    def validate_evidence_until(cls, value: str) -> str:
        return _finite_or_perpetual(value, field="evidence_valid_until")

    @model_validator(mode="after")
    def validate_request(
        self,
    ) -> CreativeSampleGeneratedReferenceCandidateQualificationRequestV1:
        if tuple(item.category for item in self.evidence_refs) != EVIDENCE_CATEGORY_ORDER:
            _invalid("evidence_refs must use the exact canonical category order")
        if len({item.record_id for item in self.evidence_refs}) != 10:
            _invalid("evidence_refs record IDs must be unique")
        if _parse_utc(self.submitted_at) > _parse_utc(self.requested_at):
            _invalid("requested_at cannot precede submitted_at")
        _validate_evidence_times(
            self.evidence_refs,
            submitted_at=self.submitted_at,
            observed_at=self.requested_at,
        )
        expected_evidence_until = _minimum_finite(
            tuple(item.evidence_valid_until for item in self.evidence_refs)
        )
        if self.evidence_valid_until != expected_evidence_until:
            _invalid("evidence_valid_until is not the exact earliest evidence expiry")
        if self.request_valid_until != _bounded_valid_until(
            self.requested_at, self.evidence_valid_until
        ):
            _invalid("request_valid_until is not uniquely derived")
        expected_sha = _semantic_sha256(
            GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_REQUEST_SHA256_DOMAIN,
            _request_projection_unchecked(self),
        )
        if self.request_sha256 != expected_sha:
            _invalid("request_sha256 does not bind the exact Request projection")
        expected_id = f"generated_reference_candidate_qualification_request_v1_{expected_sha[:20]}"
        if self.request_id != expected_id:
            _invalid("request_id does not agree with request_sha256")
        _require_model_size(self, field="Qualification Request")
        return self


class CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1(_ZeroAuthorityModel):
    _root_json_max_items: ClassVar[int] = _MAX_FORMAL_ROOT_ITEMS

    schema_version: Literal["1.0.0"]
    document_type: Literal[
        "sdc.creative-sample-generated-reference-candidate-qualification-decision-v1"
    ]
    decision_id: Annotated[str, Field(pattern=_DECISION_ID_PATTERN)]
    decision_sha256: LowerSha256
    qualification_scope: Literal["GENERATED_REFERENCE_CANDIDATE_INTAKE_ONLY"]
    request_id: Annotated[str, Field(pattern=_REQUEST_ID_PATTERN)]
    request_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-candidate-qualification-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "9991a23c2d12c842691585ef11fe4edc5697bccb8086ec661c23a240375d359f"
    ]
    candidate_id: Annotated[str, Field(pattern=_CANDIDATE_ID_PATTERN)]
    candidate_sha256: LowerSha256
    provider_attempt_outcome_id: Annotated[str, Field(pattern=_OUTCOME_ID_PATTERN)]
    provider_attempt_outcome_sha256: LowerSha256
    reference_prompt_artifact_sha256: LowerSha256
    media_content_sha256: LowerSha256
    requested_at: str
    request_valid_until: str
    evidence_valid_until: str
    qualifier_ref_sha256: LowerSha256
    qualifier_record_sha256: LowerSha256
    decision_at: str
    qualification_valid_until: str
    gate_results: Annotated[
        tuple[GeneratedReferenceQualificationGateResultV1, ...],
        Field(min_length=15, max_length=15),
    ]
    qualification_issue_codes: Annotated[tuple[QualificationIssueCode, ...], Field(max_length=16)]
    qualification_basis: Annotated[str, Field(min_length=1, max_length=1000)]
    decision: QualificationDecision
    eligible_for_separate_generated_rights_manifest_review: bool
    status: Literal["QUALIFICATION_COMPLETE"]
    qualification_performed: Literal[True]
    rights_manifest_embedded: Literal[False]
    current_status_assessment_embedded: Literal[False]

    @field_validator(
        "requested_at",
        "request_valid_until",
        "decision_at",
        "qualification_valid_until",
    )
    @classmethod
    def validate_finite_times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @field_validator("evidence_valid_until")
    @classmethod
    def validate_evidence_until(cls, value: str) -> str:
        return _finite_or_perpetual(value, field="evidence_valid_until")

    @field_validator("qualification_basis")
    @classmethod
    def validate_basis(cls, value: str) -> str:
        return _validate_human_text(value, field="qualification_basis", maximum=1000)

    @model_validator(mode="before")
    @classmethod
    def validate_eligibility_type(cls, value: object) -> object:
        if (
            isinstance(value, dict)
            and "eligible_for_separate_generated_rights_manifest_review" in value
        ):
            if type(value["eligible_for_separate_generated_rights_manifest_review"]) is not bool:
                _invalid(
                    "eligible_for_separate_generated_rights_manifest_review must be an exact "
                    "boolean"
                )
        return value

    @model_validator(mode="after")
    def validate_decision(
        self,
    ) -> CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1:
        if tuple(item.gate for item in self.gate_results) != QUALIFICATION_GATE_ORDER:
            _invalid("gate_results must use the exact frozen gate order")
        expected_codes, expected_decision, expected_eligible = _derive_decision(self.gate_results)
        if self.qualification_issue_codes != expected_codes:
            _invalid("qualification_issue_codes do not match Gate Results")
        if self.decision != expected_decision or (
            self.eligible_for_separate_generated_rights_manifest_review != expected_eligible
        ):
            _invalid("Decision literal or eligibility does not match Gate Results")
        if not (
            _parse_utc(self.requested_at)
            <= _parse_utc(self.decision_at)
            < _parse_utc(self.request_valid_until)
        ):
            _invalid("decision_at is outside the Request interval")
        if self.qualification_valid_until != _bounded_valid_until(
            self.decision_at, self.evidence_valid_until
        ):
            _invalid("qualification_valid_until is not uniquely derived")
        expected_sha = _semantic_sha256(
            GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_DECISION_SHA256_DOMAIN,
            _decision_projection_unchecked(self),
        )
        if self.decision_sha256 != expected_sha:
            _invalid("decision_sha256 does not bind the exact Decision projection")
        expected_id = f"generated_reference_candidate_qualification_decision_v1_{expected_sha[:20]}"
        if self.decision_id != expected_id:
            _invalid("decision_id does not agree with decision_sha256")
        _require_model_size(self, field="Qualification Decision")
        return self


def _revalidate[ModelT: _StrictFrozenModel](
    value: ModelT,
    model_type: type[ModelT],
    *,
    field: str,
) -> ModelT:
    if type(value) is not model_type:
        raise TypeError(f"{field} must be an exact {model_type.__name__}")
    return model_type.model_validate(value.model_dump(mode="python"))


def _require_model_size(value: _StrictFrozenModel, *, field: str) -> None:
    raw = _persistent_document_bytes(
        value.model_dump(mode="json"),
        root_maximum=value._root_json_max_items,
    )
    if not 1 <= len(raw) <= value._raw_json_max_bytes:
        _invalid(f"{field} exceeds its persistent document byte bound")


def _validate_outcome_matrix(
    value: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
) -> None:
    expected_reason: dict[TerminalDisposition, TerminalReasonCode | None] = {
        "VERIFIED_SUCCESS": None,
        "SUBMISSION_REJECTED": "SUBMISSION_REJECTED_BY_PROVIDER",
        "PROVIDER_TASK_FAILED": "PROVIDER_TASK_REPORTED_FAILURE",
        "CANCELLED": "PROVIDER_TASK_CANCELLED",
        "EXPIRED": "PROVIDER_TASK_EXPIRED_OR_TIMED_OUT",
        "SUBMISSION_UNKNOWN": "SUBMISSION_RESULT_UNKNOWN",
        "PARTIAL_OUTPUT": "EXPECTED_OUTPUT_NOT_FULLY_AVAILABLE",
        "OUTPUT_INTEGRITY_FAILURE": "OUTPUT_BYTES_OR_TECHNICAL_RECORD_MISMATCH",
        "UNSUPPORTED_OUTPUT_CARDINALITY": "PROVIDER_REPORTED_UNSUPPORTED_OUTPUT_COUNT",
    }
    if value.terminal_reason_code != expected_reason[value.terminal_disposition]:
        _invalid("terminal_reason_code is not uniquely derived from disposition")
    if value.verified_output_count != len(value.output_descriptors):
        _invalid("verified_output_count does not equal descriptor count")
    disposition = value.terminal_disposition
    task_status = value.provider_task_reference_status
    count = value.reported_output_count_bounded
    overflow = value.reported_output_count_overflow
    verified = value.verified_output_count
    if disposition == "VERIFIED_SUCCESS":
        valid = task_status == "PRESENT_IN_RETAINED_RECORD" and (count, overflow, verified) == (
            1,
            False,
            1,
        )
    elif disposition == "SUBMISSION_REJECTED":
        valid = task_status == "ABSENT" and (count, overflow, verified) == (0, False, 0)
    elif disposition in {"PROVIDER_TASK_FAILED", "CANCELLED", "EXPIRED"}:
        valid = task_status == "PRESENT_IN_RETAINED_RECORD" and (
            count,
            overflow,
            verified,
        ) == (0, False, 0)
    elif disposition == "SUBMISSION_UNKNOWN":
        valid = (count, overflow, verified) == (0, False, 0)
    elif disposition == "PARTIAL_OUTPUT":
        valid = task_status == "PRESENT_IN_RETAINED_RECORD" and (
            count in {0, 1} and not overflow and verified == 0
        )
    elif disposition == "OUTPUT_INTEGRITY_FAILURE":
        valid = task_status == "PRESENT_IN_RETAINED_RECORD" and (
            count,
            overflow,
            verified,
        ) == (1, False, 0)
    else:
        valid = (
            task_status == "PRESENT_IN_RETAINED_RECORD"
            and verified == 0
            and ((not overflow and 2 <= count <= 64) or (overflow and count == 64))
        )
    if not valid:
        _invalid("terminal fields do not match the frozen disposition matrix")
    if disposition != "VERIFIED_SUCCESS" and value.output_descriptors:
        _invalid("non-success Outcomes cannot contain an output descriptor")


def _validate_evidence_times(
    values: tuple[GeneratedReferenceQualificationEvidenceReferenceV1, ...],
    *,
    submitted_at: str,
    observed_at: str,
) -> None:
    observed_dt = _parse_utc(observed_at)
    submitted_dt = _parse_utc(submitted_at)
    for item in values:
        if _parse_utc(item.observed_at) > observed_dt or not _before(
            observed_at, item.evidence_valid_until
        ):
            _invalid(f"{item.category} was not fresh at the operation time")
        point = submitted_dt if item.category in _SUBMISSION_TIME_CATEGORIES else observed_dt
        if point < _parse_utc(item.effective_from) or (
            item.effective_until != "PERPETUAL" and point >= _parse_utc(item.effective_until)
        ):
            _invalid(f"{item.category} was not effective at the required time")
        if item.category not in _SUBMISSION_TIME_CATEGORIES and (
            item.effective_until != "PERPETUAL"
            and (
                item.evidence_valid_until == "PERPETUAL"
                or _parse_utc(item.evidence_valid_until) > _parse_utc(item.effective_until)
            )
        ):
            _invalid(f"{item.category} freshness exceeds its effective interval")


def _derive_decision(
    values: tuple[GeneratedReferenceQualificationGateResultV1, ...],
) -> tuple[tuple[QualificationIssueCode, ...], QualificationDecision, bool]:
    non_pass_codes = tuple(
        QUALIFICATION_ISSUE_CODE_ORDER[index]
        for index, item in enumerate(values)
        if item.result != "PASS"
    )
    if any(item.result == "FAIL" for item in values):
        return (*non_pass_codes, "QUALIFIER_REJECTED"), "REJECTED", False
    if non_pass_codes:
        return non_pass_codes, "NEEDS_HUMAN_REVIEW", False
    return (), "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW", True


def _zero_authority_projection(value: _ZeroAuthorityModel) -> dict[str, object]:
    return {
        "authority_scope": value.authority_scope,
        "current_gate": value.current_gate,
        "provider_state": value.provider_state,
        "generation_authorized": value.generation_authorized,
        "execution_authorized": value.execution_authorized,
        "publication_authorized": value.publication_authorized,
        "remote_processing_allowed": value.remote_processing_allowed,
        "retention_allowed": value.retention_allowed,
        "training_allowed": value.training_allowed,
        "publication_allowed": value.publication_allowed,
        "automated_execution_allowed": value.automated_execution_allowed,
        "authorized_attempts": value.authorized_attempts,
        "authorized_cost_cny": value.authorized_cost_cny,
        "posts_allowed": value.posts_allowed,
        "provider_requests": value.provider_requests,
        "grants_rights": value.grants_rights,
        "grants_qualification": value.grants_qualification,
        "grants_execution_authority": value.grants_execution_authority,
        "eligible_for_asset_promotion": value.eligible_for_asset_promotion,
        "replaces_rights_manifest": value.replaces_rights_manifest,
        "usage_restriction": value.usage_restriction,
    }


def _png_technical_record_projection_unchecked(
    value: GeneratedReferencePngTechnicalRecordV1,
) -> dict[str, object]:
    return {
        "media_type": value.media_type,
        "width": value.width,
        "height": value.height,
        "bit_depth": value.bit_depth,
        "color_space": value.color_space,
        "alpha_status": value.alpha_status,
        "interlaced": value.interlaced,
        "animation_frame_count": value.animation_frame_count,
        "metadata_status": value.metadata_status,
        "metadata_chunk_types": list(value.metadata_chunk_types),
        "png_signature_valid": value.png_signature_valid,
        "ihdr_count": value.ihdr_count,
        "idat_present": value.idat_present,
        "iend_count": value.iend_count,
        "chunk_crc_valid": value.chunk_crc_valid,
        "unknown_critical_chunk_absent": value.unknown_critical_chunk_absent,
        "apng_chunks_absent": value.apng_chunks_absent,
        "trailing_bytes_count": value.trailing_bytes_count,
        "decompressed_pixel_bytes": value.decompressed_pixel_bytes,
    }


def _output_descriptor_projection(
    value: GeneratedReferenceOutputDescriptorV1,
) -> dict[str, object]:
    return {
        "ordinal": value.ordinal,
        "media_type": value.media_type,
        "content_sha256": value.content_sha256,
        "size_bytes": value.size_bytes,
        "technical_record": _png_technical_record_projection_unchecked(value.technical_record),
        "technical_record_sha256": value.technical_record_sha256,
        "regular_file_verified": value.regular_file_verified,
        "symlink_absent": value.symlink_absent,
        "reparse_point_absent": value.reparse_point_absent,
        "admission_transform_performed": value.admission_transform_performed,
    }


def _provider_output_set_projection_unchecked(
    value: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
) -> dict[str, object]:
    return {
        "expected_output_count": value.expected_output_count,
        "reported_output_count_bounded": value.reported_output_count_bounded,
        "reported_output_count_overflow": value.reported_output_count_overflow,
        "verified_output_count": value.verified_output_count,
        "output_descriptors": [
            _output_descriptor_projection(item) for item in value.output_descriptors
        ],
    }


def _outcome_projection_unchecked(
    value: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "document_type": value.document_type,
        "outcome_purpose": value.outcome_purpose,
        "reference_prompt_artifact_sha256": value.reference_prompt_artifact_sha256,
        "asset_purpose": value.asset_purpose,
        "subject_id": value.subject_id,
        "expected_active_asset_version_id": value.expected_active_asset_version_id,
        "expected_active_asset_content_sha256": value.expected_active_asset_content_sha256,
        "profile_id": value.profile_id,
        "profile_version": value.profile_version,
        "profile_sha256": value.profile_sha256,
        "catalog_version": value.catalog_version,
        "catalog_sha256": value.catalog_sha256,
        "render_input_sha256": value.render_input_sha256,
        "submitted_prompt_sha256": value.submitted_prompt_sha256,
        "submitted_prompt_size_bytes": value.submitted_prompt_size_bytes,
        "prompt_render_receipt_sha256": value.prompt_render_receipt_sha256,
        "provider": value.provider,
        "model": value.model,
        "provider_region": value.provider_region,
        "provider_terms_snapshot_id": value.provider_terms_snapshot_id,
        "provider_terms_snapshot_sha256": value.provider_terms_snapshot_sha256,
        "provider_terms_observed_at": value.provider_terms_observed_at,
        "provider_terms_valid_from": value.provider_terms_valid_from,
        "provider_terms_valid_until": value.provider_terms_valid_until,
        "attempt_provenance_record_sha256": value.attempt_provenance_record_sha256,
        "terminal_observation_record_sha256": value.terminal_observation_record_sha256,
        "historical_execution_authorization_status": (
            value.historical_execution_authorization_status
        ),
        "attempt_ordinal": value.attempt_ordinal,
        "submitted_input_material_count": value.submitted_input_material_count,
        "submitted_at": value.submitted_at,
        "terminal_observed_at": value.terminal_observed_at,
        "terminal_disposition": value.terminal_disposition,
        "terminal_reason_code": value.terminal_reason_code,
        "provider_task_reference_status": value.provider_task_reference_status,
        **_provider_output_set_projection_unchecked(value),
        "output_set_sha256": value.output_set_sha256,
        "observed_provider_request_count": value.observed_provider_request_count,
        **_zero_authority_projection(value),
    }


def _candidate_projection_unchecked(
    value: CreativeSampleGeneratedReferenceCandidateV1,
) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "document_type": value.document_type,
        "candidate_purpose": value.candidate_purpose,
        "candidate_state": value.candidate_state,
        "origin_claim": value.origin_claim,
        "origin_assurance": value.origin_assurance,
        "reference_prompt_artifact_sha256": value.reference_prompt_artifact_sha256,
        "provider_attempt_outcome_id": value.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": value.provider_attempt_outcome_sha256,
        "output_set_sha256": value.output_set_sha256,
        "output_ordinal": value.output_ordinal,
        "asset_purpose": value.asset_purpose,
        "subject_id": value.subject_id,
        "expected_active_asset_version_id": value.expected_active_asset_version_id,
        "expected_active_asset_content_sha256": value.expected_active_asset_content_sha256,
        "profile_id": value.profile_id,
        "profile_version": value.profile_version,
        "profile_sha256": value.profile_sha256,
        "catalog_version": value.catalog_version,
        "catalog_sha256": value.catalog_sha256,
        "render_input_sha256": value.render_input_sha256,
        "prompt_sha256": value.prompt_sha256,
        "prompt_size_bytes": value.prompt_size_bytes,
        "prompt_render_receipt_sha256": value.prompt_render_receipt_sha256,
        "provider": value.provider,
        "model": value.model,
        "provider_region": value.provider_region,
        "provider_terms_snapshot_id": value.provider_terms_snapshot_id,
        "provider_terms_snapshot_sha256": value.provider_terms_snapshot_sha256,
        "provider_terms_valid_from": value.provider_terms_valid_from,
        "provider_terms_valid_until": value.provider_terms_valid_until,
        "attempt_provenance_record_sha256": value.attempt_provenance_record_sha256,
        "terminal_observation_record_sha256": value.terminal_observation_record_sha256,
        "historical_execution_authorization_status": (
            value.historical_execution_authorization_status
        ),
        "attempt_ordinal": value.attempt_ordinal,
        "submitted_input_material_count": value.submitted_input_material_count,
        "media_type": value.media_type,
        "media_content_sha256": value.media_content_sha256,
        "media_size_bytes": value.media_size_bytes,
        "media_width": value.media_width,
        "media_height": value.media_height,
        "media_technical_record_sha256": value.media_technical_record_sha256,
        "qualification_decision_embedded": value.qualification_decision_embedded,
        "rights_manifest_embedded": value.rights_manifest_embedded,
        "current_status_assessment_embedded": value.current_status_assessment_embedded,
        **_zero_authority_projection(value),
    }


def _evidence_reference_projection(
    value: GeneratedReferenceQualificationEvidenceReferenceV1,
) -> dict[str, object]:
    return {
        "category": value.category,
        "record_id": value.record_id,
        "document_profile": value.document_profile,
        "media_type": value.media_type,
        "document_size_bytes": value.document_size_bytes,
        "document_sha256": value.document_sha256,
        "observed_at": value.observed_at,
        "effective_from": value.effective_from,
        "effective_until": value.effective_until,
        "evidence_valid_until": value.evidence_valid_until,
    }


def _request_projection_unchecked(
    value: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "document_type": value.document_type,
        "qualification_scope": value.qualification_scope,
        "policy_id": value.policy_id,
        "policy_version": value.policy_version,
        "policy_document_sha256": value.policy_document_sha256,
        "candidate_id": value.candidate_id,
        "candidate_sha256": value.candidate_sha256,
        "provider_attempt_outcome_id": value.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": value.provider_attempt_outcome_sha256,
        "reference_prompt_artifact_sha256": value.reference_prompt_artifact_sha256,
        "media_content_sha256": value.media_content_sha256,
        "media_technical_record_sha256": value.media_technical_record_sha256,
        "submitted_at": value.submitted_at,
        "requested_at": value.requested_at,
        "request_valid_until": value.request_valid_until,
        "evidence_valid_until": value.evidence_valid_until,
        "evidence_preparer_ref_sha256": value.evidence_preparer_ref_sha256,
        "evidence_preparer_record_sha256": value.evidence_preparer_record_sha256,
        "evidence_refs": [_evidence_reference_projection(item) for item in value.evidence_refs],
        "status": value.status,
        "rights_manifest_embedded": value.rights_manifest_embedded,
        "current_status_assessment_embedded": value.current_status_assessment_embedded,
        **_zero_authority_projection(value),
    }


def _gate_result_projection(
    value: GeneratedReferenceQualificationGateResultV1,
) -> dict[str, object]:
    return {
        "gate": value.gate,
        "result": value.result,
        "evidence_record_ids": list(value.evidence_record_ids),
        "basis": value.basis,
    }


def _decision_projection_unchecked(
    value: CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "document_type": value.document_type,
        "qualification_scope": value.qualification_scope,
        "request_id": value.request_id,
        "request_sha256": value.request_sha256,
        "policy_id": value.policy_id,
        "policy_version": value.policy_version,
        "policy_document_sha256": value.policy_document_sha256,
        "candidate_id": value.candidate_id,
        "candidate_sha256": value.candidate_sha256,
        "provider_attempt_outcome_id": value.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": value.provider_attempt_outcome_sha256,
        "reference_prompt_artifact_sha256": value.reference_prompt_artifact_sha256,
        "media_content_sha256": value.media_content_sha256,
        "requested_at": value.requested_at,
        "request_valid_until": value.request_valid_until,
        "evidence_valid_until": value.evidence_valid_until,
        "qualifier_ref_sha256": value.qualifier_ref_sha256,
        "qualifier_record_sha256": value.qualifier_record_sha256,
        "decision_at": value.decision_at,
        "qualification_valid_until": value.qualification_valid_until,
        "gate_results": [_gate_result_projection(item) for item in value.gate_results],
        "qualification_issue_codes": list(value.qualification_issue_codes),
        "qualification_basis": value.qualification_basis,
        "decision": value.decision,
        "eligible_for_separate_generated_rights_manifest_review": (
            value.eligible_for_separate_generated_rights_manifest_review
        ),
        "status": value.status,
        "qualification_performed": value.qualification_performed,
        "rights_manifest_embedded": value.rights_manifest_embedded,
        "current_status_assessment_embedded": value.current_status_assessment_embedded,
        **_zero_authority_projection(value),
    }


def generated_reference_png_technical_record_projection(
    value: GeneratedReferencePngTechnicalRecordV1,
) -> dict[str, object]:
    """Return the explicit ADR-043 PNG technical-record projection."""

    try:
        validated = _revalidate(value, GeneratedReferencePngTechnicalRecordV1, field="PNG record")
        return _png_technical_record_projection_unchecked(validated)
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceCandidateError("PNG technical-record projection failed") from exc


def generated_reference_png_technical_record_sha256(
    value: GeneratedReferencePngTechnicalRecordV1,
) -> str:
    """Return the domain-separated PNG technical-record digest."""

    projection = generated_reference_png_technical_record_projection(value)
    return _semantic_sha256(GENERATED_REFERENCE_PNG_TECHNICAL_RECORD_SHA256_DOMAIN, projection)


def generated_reference_provider_output_set_projection(
    value: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
) -> dict[str, object]:
    """Return the exact Output Set embedded by one valid Outcome."""

    try:
        validated = _revalidate(
            value,
            CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
            field="Outcome",
        )
        return _provider_output_set_projection_unchecked(validated)
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceCandidateError("Output Set projection failed") from exc


def generated_reference_provider_output_set_sha256(
    value: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
) -> str:
    """Return the domain-separated Output Set digest."""

    return _semantic_sha256(
        GENERATED_REFERENCE_PROVIDER_OUTPUT_SET_SHA256_DOMAIN,
        generated_reference_provider_output_set_projection(value),
    )


def creative_sample_generated_reference_provider_attempt_outcome_projection(
    value: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
) -> dict[str, object]:
    """Strictly revalidate and project an Outcome without its self identity fields."""

    try:
        validated = _revalidate(
            value,
            CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
            field="Outcome",
        )
        return _outcome_projection_unchecked(validated)
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceCandidateError("Outcome projection failed") from exc


def creative_sample_generated_reference_provider_attempt_outcome_sha256(
    value: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
) -> str:
    """Return the authoritative domain-separated Outcome identity."""

    return _semantic_sha256(
        GENERATED_REFERENCE_PROVIDER_ATTEMPT_OUTCOME_SHA256_DOMAIN,
        creative_sample_generated_reference_provider_attempt_outcome_projection(value),
    )


def creative_sample_generated_reference_candidate_projection(
    value: CreativeSampleGeneratedReferenceCandidateV1,
) -> dict[str, object]:
    """Strictly revalidate and project a Candidate without its self identity fields."""

    try:
        validated = _revalidate(
            value,
            CreativeSampleGeneratedReferenceCandidateV1,
            field="Candidate",
        )
        return _candidate_projection_unchecked(validated)
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceCandidateError("Candidate projection failed") from exc


def creative_sample_generated_reference_candidate_sha256(
    value: CreativeSampleGeneratedReferenceCandidateV1,
) -> str:
    """Return the authoritative domain-separated Candidate identity."""

    return _semantic_sha256(
        GENERATED_REFERENCE_CANDIDATE_SHA256_DOMAIN,
        creative_sample_generated_reference_candidate_projection(value),
    )


def creative_sample_generated_reference_candidate_qualification_request_projection(
    value: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
) -> dict[str, object]:
    """Strictly revalidate and project a Request without its self identity fields."""

    try:
        validated = _revalidate(
            value,
            CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
            field="Qualification Request",
        )
        return _request_projection_unchecked(validated)
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceCandidateError("Qualification Request projection failed") from exc


def creative_sample_generated_reference_candidate_qualification_request_sha256(
    value: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
) -> str:
    """Return the authoritative domain-separated Request identity."""

    return _semantic_sha256(
        GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_REQUEST_SHA256_DOMAIN,
        creative_sample_generated_reference_candidate_qualification_request_projection(value),
    )


def creative_sample_generated_reference_candidate_qualification_decision_projection(
    value: CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
) -> dict[str, object]:
    """Strictly revalidate and project a Decision without its self identity fields."""

    try:
        validated = _revalidate(
            value,
            CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
            field="Qualification Decision",
        )
        return _decision_projection_unchecked(validated)
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceCandidateError("Qualification Decision projection failed") from exc


def creative_sample_generated_reference_candidate_qualification_decision_sha256(
    value: CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
) -> str:
    """Return the authoritative domain-separated Decision identity."""

    return _semantic_sha256(
        GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_DECISION_SHA256_DOMAIN,
        creative_sample_generated_reference_candidate_qualification_decision_projection(value),
    )


def _normalize_output_descriptor_input(
    value: object,
) -> GeneratedReferenceOutputDescriptorV1:
    if type(value) is GeneratedReferenceOutputDescriptorV1:
        return _revalidate(
            value,
            GeneratedReferenceOutputDescriptorV1,
            field="Outcome output descriptor",
        )
    if type(value) is not dict:
        raise TypeError("Outcome output descriptor must be an exact model or JSON object")
    descriptor = dict(cast(dict[str, object], value))
    technical_value = descriptor.get("technical_record")
    if type(technical_value) is GeneratedReferencePngTechnicalRecordV1:
        technical_record = _revalidate(
            technical_value,
            GeneratedReferencePngTechnicalRecordV1,
            field="Outcome PNG technical record",
        )
    elif type(technical_value) is dict:
        technical_payload = dict(cast(dict[str, object], technical_value))
        metadata_types = technical_payload.get("metadata_chunk_types")
        if type(metadata_types) is list:
            technical_payload["metadata_chunk_types"] = tuple(cast(list[object], metadata_types))
        technical_record = GeneratedReferencePngTechnicalRecordV1.model_validate(technical_payload)
    else:
        raise TypeError("Outcome PNG technical record must be an exact model or JSON object")
    descriptor["technical_record"] = technical_record
    return GeneratedReferenceOutputDescriptorV1.model_validate(descriptor)


def build_generated_reference_provider_attempt_outcome(
    projection: Mapping[str, object],
) -> CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1:
    """Close a reviewed complete non-self Outcome projection into its immutable identity."""

    try:
        if not isinstance(projection, Mapping):
            raise TypeError("projection must be a mapping")
        payload = dict(projection)
        expected_fields = set(
            CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1.model_fields
        ) - {"outcome_id", "outcome_sha256"}
        if frozenset(payload) != frozenset(expected_fields):
            _invalid("Outcome projection does not contain the exact non-self field set")
        descriptors = payload.get("output_descriptors")
        if type(descriptors) not in {list, tuple}:
            raise TypeError("output_descriptors must be an exact list or tuple")
        normalized_descriptors = tuple(
            _normalize_output_descriptor_input(item)
            for item in cast(list[object] | tuple[object, ...], descriptors)
        )
        payload["output_descriptors"] = normalized_descriptors
        descriptor_projections = [
            _output_descriptor_projection(item) for item in normalized_descriptors
        ]
        normalized_projection = {
            key: (descriptor_projections if key == "output_descriptors" else value)
            for key, value in payload.items()
        }
        digest = _semantic_sha256(
            GENERATED_REFERENCE_PROVIDER_ATTEMPT_OUTCOME_SHA256_DOMAIN,
            normalized_projection,
        )
        closed_payload = {
            **payload,
            "outcome_id": f"generated_reference_attempt_outcome_v1_{digest[:20]}",
            "outcome_sha256": digest,
        }
        return CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1.model_validate(
            closed_payload
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceCandidateError(
            "reviewed Outcome projection failed closure"
        ) from exc


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
    if not isinstance(path, Path) or type(path) is not type(Path()):
        raise TypeError("png_path must be an exact pathlib.Path")
    before = path.lstat()
    if (
        path.is_symlink()
        or _is_reparse_point(before)
        or not S_ISREG(before.st_mode)
        or getattr(before, "st_nlink", None) != 1
    ):
        _invalid("PNG path must name one regular single-link file")
    if not 1 <= before.st_size <= _MAX_PNG_BYTES:
        _invalid("PNG file size is outside the admitted bound")
    with path.open("rb") as handle:
        opened = fstat(handle.fileno())
        if (
            _is_reparse_point(opened)
            or not S_ISREG(opened.st_mode)
            or getattr(opened, "st_nlink", None) != 1
        ):
            _invalid("opened PNG handle is not a regular single-link non-reparse file")
        if _file_identity(before) != _file_identity(opened):
            _invalid("PNG path identity changed while opening")
        raw = handle.read(_MAX_PNG_BYTES + 1)
        if len(raw) > _MAX_PNG_BYTES:
            _invalid("PNG file crossed its byte bound while reading")
        after_handle = fstat(handle.fileno())
        if _file_identity(opened) != _file_identity(after_handle) or len(raw) != opened.st_size:
            _invalid("PNG file changed while it was being read")
    after_path = path.lstat()
    if (
        path.is_symlink()
        or _is_reparse_point(after_path)
        or getattr(after_path, "st_nlink", None) != 1
        or (_file_identity(before) != _file_identity(after_path))
    ):
        _invalid("PNG path identity changed after admission")
    return raw


def _paeth(left: int, above: int, upper_left: int) -> int:
    prediction = left + above - upper_left
    left_distance = abs(prediction - left)
    above_distance = abs(prediction - above)
    upper_left_distance = abs(prediction - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def _decode_png_rows(
    compressed: bytes,
    *,
    width: int,
    height: int,
    channels: int,
) -> tuple[int, bool]:
    row_bytes = width * channels
    expected_encoded = (row_bytes + 1) * height
    decompressor = zlib.decompressobj()
    try:
        decoded = decompressor.decompress(compressed, expected_encoded + 1)
        if len(decoded) > expected_encoded or decompressor.unconsumed_tail:
            _invalid("PNG decompression crossed its exact output bound")
        remaining = expected_encoded - len(decoded)
        if remaining:
            decoded += decompressor.flush(remaining + 1)
        else:
            decoded += decompressor.flush()
    except zlib.error as exc:
        raise ValueError("PNG IDAT stream is not valid zlib data") from exc
    if (
        len(decoded) != expected_encoded
        or not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
    ):
        _invalid("PNG decompression did not produce the exact bounded image")

    previous = bytearray(row_bytes)
    offset = 0
    all_alpha_opaque = True
    bytes_per_pixel = channels
    for _row_index in range(height):
        filter_type = decoded[offset]
        offset += 1
        filtered = decoded[offset : offset + row_bytes]
        offset += row_bytes
        if filter_type > 4:
            _invalid("PNG scanline uses an unknown filter")
        current = bytearray(row_bytes)
        for index, byte in enumerate(filtered):
            left = current[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            above = previous[index]
            upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            if filter_type == 0:
                value = byte
            elif filter_type == 1:
                value = (byte + left) & 0xFF
            elif filter_type == 2:
                value = (byte + above) & 0xFF
            elif filter_type == 3:
                value = (byte + ((left + above) // 2)) & 0xFF
            else:
                value = (byte + _paeth(left, above, upper_left)) & 0xFF
            current[index] = value
        if channels == 4 and all_alpha_opaque:
            all_alpha_opaque = all(current[index] == 255 for index in range(3, row_bytes, 4))
        previous = current
    return width * height * channels, all_alpha_opaque


def _parse_png(raw: bytes) -> GeneratedReferencePngTechnicalRecordV1:
    if not 1 <= len(raw) <= _MAX_PNG_BYTES or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        _invalid("PNG signature or size is invalid")
    offset = 8
    chunk_count = 0
    idat_count = 0
    ancillary_count = 0
    ancillary_payload = 0
    metadata_types: list[str] = []
    ihdr_count = 0
    iend_count = 0
    plte_count = 0
    idat_started = False
    idat_closed = False
    compressed_parts: list[bytes] = []
    width = height = bit_depth = color_type = interlace = -1
    known_critical = {"IHDR", "PLTE", "IDAT", "IEND"}
    before_plte_and_idat = {"cHRM", "gAMA", "iCCP", "sBIT", "sRGB"}
    before_idat = {"bKGD", "hIST", "pHYs", "sPLT", "eXIf"}

    while offset < len(raw):
        if len(raw) - offset < 12:
            _invalid("PNG contains a truncated chunk framing")
        length = int.from_bytes(raw[offset : offset + 4], "big")
        chunk_type_bytes = raw[offset + 4 : offset + 8]
        if any(not (65 <= item <= 90 or 97 <= item <= 122) for item in chunk_type_bytes):
            _invalid("PNG chunk type is malformed")
        if chunk_type_bytes[2] & 0x20:
            _invalid("PNG chunk type has a lowercase reserved bit")
        chunk_type = chunk_type_bytes.decode("ascii")
        end = offset + 12 + length
        if end > len(raw):
            _invalid("PNG chunk length exceeds the admitted bytes")
        chunk_data = raw[offset + 8 : offset + 8 + length]
        stored_crc = int.from_bytes(raw[offset + 8 + length : end], "big")
        if zlib.crc32(chunk_type_bytes + chunk_data) & 0xFFFFFFFF != stored_crc:
            _invalid("PNG chunk CRC is invalid")
        chunk_count += 1
        if chunk_count > 1_024:
            _invalid("PNG exceeds the total chunk-count bound")
        if chunk_count == 1 and chunk_type != "IHDR":
            _invalid("PNG IHDR must be the first chunk")
        if chunk_type in {"acTL", "fcTL", "fdAT"}:
            _invalid("APNG chunks are prohibited")
        if chunk_type == "tRNS":
            _invalid("PNG tRNS is prohibited")
        is_ancillary = bool(chunk_type_bytes[0] & 0x20)
        if not is_ancillary and chunk_type not in known_critical:
            _invalid("PNG contains an unknown critical chunk")
        if chunk_type in before_plte_and_idat and (plte_count or idat_started):
            _invalid(f"PNG {chunk_type} must precede PLTE and IDAT")
        if chunk_type in before_idat and idat_started:
            _invalid(f"PNG {chunk_type} must precede IDAT")
        if chunk_type == "hIST" and plte_count != 1:
            _invalid("PNG hIST requires a preceding PLTE")
        if is_ancillary:
            ancillary_count += 1
            ancillary_payload += length
            if ancillary_count > 64 or ancillary_payload > 1_048_576:
                _invalid("PNG ancillary metadata crosses its frozen bound")
            if chunk_type not in metadata_types:
                metadata_types.append(chunk_type)
                if len(metadata_types) > 32:
                    _invalid("PNG has too many distinct metadata chunk types")
        if chunk_type == "IHDR":
            ihdr_count += 1
            if ihdr_count != 1 or length != 13:
                _invalid("PNG requires one exact IHDR")
            width = int.from_bytes(chunk_data[0:4], "big")
            height = int.from_bytes(chunk_data[4:8], "big")
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
            compression_method = chunk_data[10]
            filter_method = chunk_data[11]
            interlace = chunk_data[12]
            if (
                not 512 <= width <= 4096
                or not 512 <= height <= 4096
                or bit_depth != 8
                or color_type not in {2, 6}
                or compression_method != 0
                or filter_method != 0
                or interlace != 0
            ):
                _invalid("PNG IHDR is outside the frozen technical profile")
        elif chunk_type == "PLTE":
            plte_count += 1
            if (
                plte_count > 1
                or idat_started
                or "bKGD" in metadata_types
                or length == 0
                or length > 768
                or length % 3
            ):
                _invalid("PNG PLTE placement or size is invalid")
        elif chunk_type == "IDAT":
            if idat_closed:
                _invalid("PNG IDAT chunks must be consecutive")
            idat_started = True
            idat_count += 1
            if idat_count > 512:
                _invalid("PNG exceeds the IDAT chunk-count bound")
            compressed_parts.append(chunk_data)
        elif idat_started and chunk_type != "IEND":
            idat_closed = True
        if chunk_type == "IEND":
            iend_count += 1
            if iend_count != 1 or length != 0 or end != len(raw):
                _invalid("PNG requires one terminal IEND and no trailing bytes")
        offset = end

    if ihdr_count != 1 or iend_count != 1 or not idat_count:
        _invalid("PNG is missing IHDR, IDAT, or IEND")
    channels = 3 if color_type == 2 else 4
    decompressed_bytes, opaque = _decode_png_rows(
        b"".join(compressed_parts),
        width=width,
        height=height,
        channels=channels,
    )
    alpha_status: Literal["ABSENT", "OPAQUE", "NON_OPAQUE"]
    if channels == 3:
        alpha_status = "ABSENT"
    else:
        alpha_status = "OPAQUE" if opaque else "NON_OPAQUE"
    return GeneratedReferencePngTechnicalRecordV1.model_validate(
        {
            "media_type": "image/png",
            "width": width,
            "height": height,
            "bit_depth": 8,
            "color_space": "RGB" if channels == 3 else "RGBA",
            "alpha_status": alpha_status,
            "interlaced": False,
            "animation_frame_count": 1,
            "metadata_status": "ABSENT" if not metadata_types else "PRESENT",
            "metadata_chunk_types": tuple(metadata_types),
            "png_signature_valid": True,
            "ihdr_count": 1,
            "idat_present": True,
            "iend_count": 1,
            "chunk_crc_valid": True,
            "unknown_critical_chunk_absent": True,
            "apng_chunks_absent": True,
            "trailing_bytes_count": 0,
            "decompressed_pixel_bytes": decompressed_bytes,
        }
    )


def _admit_png(path: Path) -> tuple[bytes, GeneratedReferenceOutputDescriptorV1]:
    raw = _read_safe_single_file(path)
    record = _parse_png(raw)
    record_sha256 = _semantic_sha256(
        GENERATED_REFERENCE_PNG_TECHNICAL_RECORD_SHA256_DOMAIN,
        _png_technical_record_projection_unchecked(record),
    )
    descriptor = GeneratedReferenceOutputDescriptorV1.model_validate(
        {
            "ordinal": 0,
            "media_type": "image/png",
            "content_sha256": _raw_sha256(raw),
            "size_bytes": len(raw),
            "technical_record": record,
            "technical_record_sha256": record_sha256,
            "regular_file_verified": True,
            "symlink_absent": True,
            "reparse_point_absent": True,
            "admission_transform_performed": False,
        }
    )
    return raw, descriptor


def admit_generated_reference_png(png_path: Path) -> GeneratedReferenceOutputDescriptorV1:
    """Safely admit one explicitly named PNG and return its immutable descriptor."""

    try:
        _raw, descriptor = _admit_png(png_path)
        return descriptor
    except (OSError, TypeError, ValueError, ValidationError, zlib.error) as exc:
        raise GeneratedReferenceCandidateError("PNG admission failed closed") from exc


def _artifact_projection(
    artifact: CreativeSampleReferenceVisualPromptArtifactV1,
) -> dict[str, object]:
    if type(artifact) is not CreativeSampleReferenceVisualPromptArtifactV1:
        raise TypeError("artifact must be an exact ADR-042 Artifact")
    projection = creative_sample_reference_visual_prompt_artifact_projection(artifact)
    if (
        creative_sample_reference_visual_prompt_artifact_sha256(artifact)
        != artifact.artifact_sha256
    ):
        _invalid("Artifact self identity failed public ADR-042 validation")
    return projection


def _artifact_cross_fields(projection: dict[str, object]) -> dict[str, object]:
    snapshot = projection.get("profile_snapshot")
    receipt = projection.get("prompt_render_receipt")
    if type(snapshot) is not dict or type(receipt) is not dict:
        _invalid("Artifact public projection is missing Snapshot or Receipt closure")
    return {
        "asset_purpose": projection["asset_purpose"],
        "subject_id": projection["subject_id"],
        "expected_active_asset_version_id": projection["expected_active_asset_version_id"],
        "expected_active_asset_content_sha256": projection["expected_active_asset_content_sha256"],
        "profile_id": snapshot["profile_id"],
        "profile_version": snapshot["profile_version"],
        "profile_sha256": snapshot["profile_sha256"],
        "catalog_version": snapshot["catalog_version"],
        "catalog_sha256": snapshot["catalog_sha256"],
        "render_input_sha256": projection["render_input_sha256"],
        "prompt_sha256": projection["prompt_sha256"],
        "prompt_size_bytes": projection["prompt_size_bytes"],
        "prompt_render_receipt_sha256": receipt["prompt_render_receipt_sha256"],
    }


def _validated_candidate_closure(
    artifact: CreativeSampleReferenceVisualPromptArtifactV1,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    *,
    png_path: Path,
) -> tuple[
    CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    dict[str, object],
    bytes,
    GeneratedReferenceOutputDescriptorV1,
]:
    artifact_projection = _artifact_projection(artifact)
    cross = _artifact_cross_fields(artifact_projection)
    validated_outcome = _revalidate(
        outcome,
        CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
        field="Outcome",
    )
    if validated_outcome.terminal_disposition != "VERIFIED_SUCCESS":
        _invalid("Candidate capture requires VERIFIED_SUCCESS")
    expected = {
        "reference_prompt_artifact_sha256": artifact.artifact_sha256,
        "asset_purpose": cross["asset_purpose"],
        "subject_id": cross["subject_id"],
        "expected_active_asset_version_id": cross["expected_active_asset_version_id"],
        "expected_active_asset_content_sha256": cross["expected_active_asset_content_sha256"],
        "profile_id": cross["profile_id"],
        "profile_version": cross["profile_version"],
        "profile_sha256": cross["profile_sha256"],
        "catalog_version": cross["catalog_version"],
        "catalog_sha256": cross["catalog_sha256"],
        "render_input_sha256": cross["render_input_sha256"],
        "submitted_prompt_sha256": cross["prompt_sha256"],
        "submitted_prompt_size_bytes": cross["prompt_size_bytes"],
        "prompt_render_receipt_sha256": cross["prompt_render_receipt_sha256"],
    }
    for field_name, expected_value in expected.items():
        if getattr(validated_outcome, field_name) != expected_value:
            _invalid(f"Outcome {field_name} differs from the exact Artifact closure")
    raw, descriptor = _admit_png(png_path)
    if len(validated_outcome.output_descriptors) != 1 or (
        _output_descriptor_projection(validated_outcome.output_descriptors[0])
        != _output_descriptor_projection(descriptor)
    ):
        _invalid("local PNG does not match the exact successful Outcome descriptor")
    return validated_outcome, cross, raw, descriptor


def capture_generated_reference_candidate(
    artifact: CreativeSampleReferenceVisualPromptArtifactV1,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    *,
    png_path: Path,
) -> CreativeSampleGeneratedReferenceCandidateV1:
    """Capture one exact successful output occurrence as an immutable unqualified Candidate."""

    try:
        validated_outcome, cross, raw, descriptor = _validated_candidate_closure(
            artifact, outcome, png_path=png_path
        )
        projection: dict[str, object] = {
            "schema_version": _SCHEMA_VERSION,
            "document_type": "sdc.creative-sample-generated-reference-candidate-v1",
            "candidate_purpose": "GENERATED_REFERENCE_MEDIA_PROVENANCE_EVIDENCE_ONLY",
            "candidate_state": "CAPTURED_UNQUALIFIED",
            "origin_claim": "CALLER_ASSERTED_PROVIDER_GENERATED_REFERENCE_MEDIA",
            "origin_assurance": "UNAUTHENTICATED_CALLER_EVIDENCE_NOT_YET_HUMAN_QUALIFIED",
            "reference_prompt_artifact_sha256": artifact.artifact_sha256,
            "provider_attempt_outcome_id": validated_outcome.outcome_id,
            "provider_attempt_outcome_sha256": validated_outcome.outcome_sha256,
            "output_set_sha256": validated_outcome.output_set_sha256,
            "output_ordinal": 0,
            "asset_purpose": cross["asset_purpose"],
            "subject_id": cross["subject_id"],
            "expected_active_asset_version_id": cross["expected_active_asset_version_id"],
            "expected_active_asset_content_sha256": cross["expected_active_asset_content_sha256"],
            "profile_id": cross["profile_id"],
            "profile_version": cross["profile_version"],
            "profile_sha256": cross["profile_sha256"],
            "catalog_version": cross["catalog_version"],
            "catalog_sha256": cross["catalog_sha256"],
            "render_input_sha256": cross["render_input_sha256"],
            "prompt_sha256": cross["prompt_sha256"],
            "prompt_size_bytes": cross["prompt_size_bytes"],
            "prompt_render_receipt_sha256": cross["prompt_render_receipt_sha256"],
            "provider": validated_outcome.provider,
            "model": validated_outcome.model,
            "provider_region": validated_outcome.provider_region,
            "provider_terms_snapshot_id": validated_outcome.provider_terms_snapshot_id,
            "provider_terms_snapshot_sha256": validated_outcome.provider_terms_snapshot_sha256,
            "provider_terms_valid_from": validated_outcome.provider_terms_valid_from,
            "provider_terms_valid_until": validated_outcome.provider_terms_valid_until,
            "attempt_provenance_record_sha256": (
                validated_outcome.attempt_provenance_record_sha256
            ),
            "terminal_observation_record_sha256": (
                validated_outcome.terminal_observation_record_sha256
            ),
            "historical_execution_authorization_status": (
                validated_outcome.historical_execution_authorization_status
            ),
            "attempt_ordinal": 1,
            "submitted_input_material_count": 0,
            "media_type": "image/png",
            "media_content_sha256": _raw_sha256(raw),
            "media_size_bytes": len(raw),
            "media_width": descriptor.technical_record.width,
            "media_height": descriptor.technical_record.height,
            "media_technical_record_sha256": descriptor.technical_record_sha256,
            "qualification_decision_embedded": False,
            "rights_manifest_embedded": False,
            "current_status_assessment_embedded": False,
            **_zero_authority_values(),
        }
        digest = _semantic_sha256(GENERATED_REFERENCE_CANDIDATE_SHA256_DOMAIN, projection)
        return CreativeSampleGeneratedReferenceCandidateV1.model_validate(
            {
                **projection,
                "candidate_id": f"generated_reference_candidate_v1_{digest[:20]}",
                "candidate_sha256": digest,
            }
        )
    except (
        OSError,
        TypeError,
        ValueError,
        ValidationError,
        VisualReferencePromptCompilerError,
        zlib.error,
    ) as exc:
        raise GeneratedReferenceCandidateError("Candidate capture failed closed") from exc


def _validate_exact_record(
    raw: bytes,
    *,
    expected: dict[str, object],
    maximum: int,
    field: str,
) -> tuple[dict[str, object], str]:
    value = _admit_persistent_json(raw, maximum=maximum, field=field)
    if not _json_tree_exactly_equal(value, expected):
        _invalid(f"{field} does not contain the exact frozen record")
    return value, _raw_sha256(raw)


def _human_reference(raw: bytes, *, field: str) -> tuple[dict[str, object], str]:
    value = _admit_persistent_json(raw, maximum=_MAX_HUMAN_REFERENCE_BYTES, field=field)
    if (
        set(value) != {"document_profile", "identity_namespace", "identity_ref"}
        or value.get("document_profile") != "sdc.privacy-minimized-human-reference.v1"
    ):
        _invalid(f"{field} does not use the frozen human-reference profile")
    for key in ("identity_namespace", "identity_ref"):
        item = value.get(key)
        if type(item) is not str or re.fullmatch(_PORTABLE_ID_PATTERN, item) is None:
            _invalid(f"{field}.{key} is not a PortableId")
    return value, _raw_sha256(raw)


def _admit_evidence_documents(
    evidence_documents: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
) -> tuple[
    tuple[GeneratedReferenceQualificationEvidenceReferenceV1, ...],
    tuple[str, ...],
]:
    if type(evidence_documents) is not tuple or len(evidence_documents) != 10:
        _invalid("evidence_documents must be an exact ten-item tuple")
    references: list[GeneratedReferenceQualificationEvidenceReferenceV1] = []
    digests: list[str] = []
    metadata_fields = (
        "record_id",
        "document_profile",
        "observed_at",
        "effective_from",
        "effective_until",
        "evidence_valid_until",
    )
    for index, item in enumerate(evidence_documents):
        if type(item) is not GeneratedReferenceQualificationEvidenceInput:
            _invalid(f"evidence_documents[{index}] has the wrong exact input type")
        reference = _revalidate(
            item.reference,
            GeneratedReferenceQualificationEvidenceReferenceV1,
            field=f"evidence reference {index}",
        )
        document = _admit_persistent_json(
            item.document_bytes,
            maximum=_MAX_RETAINED_RECORD_BYTES,
            field=f"evidence document {index}",
        )
        digest = _raw_sha256(item.document_bytes)
        if reference.document_size_bytes != len(item.document_bytes) or (
            reference.document_sha256 != digest
        ):
            _invalid(f"evidence document {index} size or digest does not match its reference")
        if document.get("category") != reference.category:
            _invalid(f"evidence document {index} category differs from its reference")
        for field_name in metadata_fields:
            if document.get(field_name) != getattr(reference, field_name):
                _invalid(f"evidence document {index} {field_name} differs from its reference")
        references.append(reference)
        digests.append(digest)
    result = tuple(references)
    if tuple(item.category for item in result) != EVIDENCE_CATEGORY_ORDER:
        _invalid("evidence documents are not in the frozen category order")
    if len({item.record_id for item in result}) != 10 or len(set(digests)) != 10:
        _invalid("evidence record IDs and exact document bytes must be unique")
    return result, tuple(digests)


def _validate_evidence_outcome_bindings(
    references: tuple[GeneratedReferenceQualificationEvidenceReferenceV1, ...],
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
) -> None:
    by_category = {item.category: item for item in references}
    provenance = by_category["PROVIDER_ATTEMPT_PROVENANCE"]
    terminal = by_category["PROVIDER_TERMINAL_OBSERVATION"]
    terms = by_category["PROVIDER_TERMS_AT_SUBMISSION"]
    if provenance.document_sha256 != outcome.attempt_provenance_record_sha256:
        _invalid("Provider-attempt provenance evidence does not match Outcome")
    if terminal.document_sha256 != outcome.terminal_observation_record_sha256:
        _invalid("terminal-observation evidence does not match Outcome")
    if (
        terms.record_id != outcome.provider_terms_snapshot_id
        or terms.document_sha256 != outcome.provider_terms_snapshot_sha256
        or terms.observed_at != outcome.provider_terms_observed_at
        or terms.effective_from != outcome.provider_terms_valid_from
        or terms.effective_until != outcome.provider_terms_valid_until
    ):
        _invalid("Provider-terms evidence does not match the exact Outcome terms closure")


def _request_preparer_action_expected(
    *,
    actor_ref_sha256: str,
    candidate: CreativeSampleGeneratedReferenceCandidateV1,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    requested_at: str,
    evidence_digests: tuple[str, ...],
) -> dict[str, object]:
    return {
        "document_profile": ("sdc.generated-reference-qualification-request-preparation-action.v1"),
        "action": "PREPARED_GENERATED_REFERENCE_QUALIFICATION_EVIDENCE",
        "actor_ref_sha256": actor_ref_sha256,
        "candidate_sha256": candidate.candidate_sha256,
        "provider_attempt_outcome_sha256": outcome.outcome_sha256,
        "policy_document_sha256": GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256,
        "requested_at": requested_at,
        "evidence_document_sha256s": list(evidence_digests),
    }


def _collect_formal_sha256_bindings(value: BaseModel) -> set[str]:
    result: set[str] = set()
    ignored_retained_bindings = {
        "evidence_preparer_ref_sha256",
        "evidence_preparer_record_sha256",
        "qualifier_ref_sha256",
        "qualifier_record_sha256",
    }

    def visit(item: object) -> None:
        if type(item) is dict:
            for key, nested in cast(dict[str, object], item).items():
                if key in ignored_retained_bindings:
                    continue
                if (
                    key.endswith("_sha256")
                    and type(nested) is str
                    and re.fullmatch(_LOWER_SHA256_PATTERN, nested) is not None
                ):
                    result.add(nested)
                visit(nested)
        elif type(item) in {list, tuple}:
            for nested in cast(list[object] | tuple[object, ...], item):
                visit(nested)

    visit(value.model_dump(mode="json"))
    return result


def _ensure_no_digest_aliases(
    retained_digests: tuple[str, ...],
    *,
    evidence_digests: tuple[str, ...],
    artifact: CreativeSampleReferenceVisualPromptArtifactV1,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    candidate: CreativeSampleGeneratedReferenceCandidateV1,
    request: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1 | None = None,
) -> None:
    if len(retained_digests) != len(set(retained_digests)):
        _invalid("retained human-reference/action records must have distinct raw digests")
    forbidden = {
        *evidence_digests,
        GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256,
    }
    for formal_value in (artifact, outcome, candidate):
        forbidden.update(_collect_formal_sha256_bindings(formal_value))
    if request is not None:
        forbidden.update(_collect_formal_sha256_bindings(request))
    if set(retained_digests) & forbidden:
        _invalid("retained human records alias evidence or a bound formal SHA-256 value")


def prepare_generated_reference_candidate_qualification_request(
    artifact: CreativeSampleReferenceVisualPromptArtifactV1,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    candidate: CreativeSampleGeneratedReferenceCandidateV1,
    *,
    png_path: Path,
    evidence_documents: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
    preparer_reference_bytes: bytes,
    preparer_action_bytes: bytes,
    requested_at: str,
) -> CreativeSampleGeneratedReferenceCandidateQualificationRequestV1:
    """Prepare one finite independent-human Qualification Request over an exact closure."""

    try:
        requested_at = _utc_seconds(requested_at, field="requested_at")
        validated_candidate = _revalidate(
            candidate,
            CreativeSampleGeneratedReferenceCandidateV1,
            field="Candidate",
        )
        recaptured = capture_generated_reference_candidate(
            artifact,
            outcome,
            png_path=png_path,
        )
        if recaptured != validated_candidate:
            _invalid("Candidate is not the exact recaptured Artifact/Outcome/PNG closure")
        validated_outcome = _revalidate(
            outcome,
            CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
            field="Outcome",
        )
        if not (
            _parse_utc(validated_outcome.submitted_at)
            <= _parse_utc(validated_outcome.terminal_observed_at)
            <= _parse_utc(requested_at)
        ):
            _invalid("Outcome lifecycle does not close at requested_at")
        references, evidence_digests = _admit_evidence_documents(evidence_documents)
        _validate_evidence_times(
            references,
            submitted_at=validated_outcome.submitted_at,
            observed_at=requested_at,
        )
        _validate_evidence_outcome_bindings(references, validated_outcome)
        _preparer_reference, preparer_ref_sha = _human_reference(
            preparer_reference_bytes,
            field="preparer human-reference record",
        )
        expected_action = _request_preparer_action_expected(
            actor_ref_sha256=preparer_ref_sha,
            candidate=validated_candidate,
            outcome=validated_outcome,
            requested_at=requested_at,
            evidence_digests=evidence_digests,
        )
        _action, preparer_action_sha = _validate_exact_record(
            preparer_action_bytes,
            expected=expected_action,
            maximum=_MAX_RETAINED_RECORD_BYTES,
            field="preparer action record",
        )
        _ensure_no_digest_aliases(
            (preparer_ref_sha, preparer_action_sha),
            evidence_digests=evidence_digests,
            artifact=artifact,
            outcome=validated_outcome,
            candidate=validated_candidate,
        )
        evidence_valid_until = _minimum_finite(
            tuple(item.evidence_valid_until for item in references)
        )
        projection: dict[str, object] = {
            "schema_version": _SCHEMA_VERSION,
            "document_type": (
                "sdc.creative-sample-generated-reference-candidate-qualification-request-v1"
            ),
            "qualification_scope": "GENERATED_REFERENCE_CANDIDATE_INTAKE_ONLY",
            "policy_id": GENERATED_REFERENCE_QUALIFICATION_POLICY_ID,
            "policy_version": GENERATED_REFERENCE_QUALIFICATION_POLICY_VERSION,
            "policy_document_sha256": (GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256),
            "candidate_id": validated_candidate.candidate_id,
            "candidate_sha256": validated_candidate.candidate_sha256,
            "provider_attempt_outcome_id": validated_outcome.outcome_id,
            "provider_attempt_outcome_sha256": validated_outcome.outcome_sha256,
            "reference_prompt_artifact_sha256": artifact.artifact_sha256,
            "media_content_sha256": validated_candidate.media_content_sha256,
            "media_technical_record_sha256": (validated_candidate.media_technical_record_sha256),
            "submitted_at": validated_outcome.submitted_at,
            "requested_at": requested_at,
            "request_valid_until": _bounded_valid_until(requested_at, evidence_valid_until),
            "evidence_valid_until": evidence_valid_until,
            "evidence_preparer_ref_sha256": preparer_ref_sha,
            "evidence_preparer_record_sha256": preparer_action_sha,
            "evidence_refs": [_evidence_reference_projection(item) for item in references],
            "status": "QUALIFICATION_REQUESTED",
            "rights_manifest_embedded": False,
            "current_status_assessment_embedded": False,
            **_zero_authority_values(),
        }
        digest = _semantic_sha256(
            GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_REQUEST_SHA256_DOMAIN,
            projection,
        )
        return CreativeSampleGeneratedReferenceCandidateQualificationRequestV1.model_validate(
            {
                **projection,
                "request_id": (
                    f"generated_reference_candidate_qualification_request_v1_{digest[:20]}"
                ),
                "request_sha256": digest,
                "evidence_refs": references,
            }
        )
    except (
        OSError,
        TypeError,
        ValueError,
        ValidationError,
        VisualReferencePromptCompilerError,
        zlib.error,
    ) as exc:
        raise GeneratedReferenceCandidateError(
            "Qualification Request preparation failed closed"
        ) from exc


def _validate_gate_evidence_mapping(
    gate_results: tuple[GeneratedReferenceQualificationGateResultV1, ...],
    references: tuple[GeneratedReferenceQualificationEvidenceReferenceV1, ...],
) -> None:
    record_by_category = {item.category: item.record_id for item in references}
    for item in gate_results:
        expected = tuple(
            record_by_category[category] for category in _GATE_EVIDENCE_CATEGORIES[item.gate]
        )
        if item.evidence_record_ids != expected:
            _invalid(f"{item.gate} evidence_record_ids do not match the frozen policy map")


def _qualifier_action_expected(
    *,
    actor_ref_sha256: str,
    request: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
    decision_at: str,
    gate_results: tuple[GeneratedReferenceQualificationGateResultV1, ...],
    issue_codes: tuple[QualificationIssueCode, ...],
    qualification_basis: str,
    decision: QualificationDecision,
    eligible: bool,
) -> dict[str, object]:
    return {
        "document_profile": "sdc.generated-reference-qualification-decision-action.v1",
        "action": "RECORDED_GENERATED_REFERENCE_QUALIFICATION_DECISION",
        "actor_ref_sha256": actor_ref_sha256,
        "request_sha256": request.request_sha256,
        "decision_at": decision_at,
        "gate_results": [_gate_result_projection(item) for item in gate_results],
        "qualification_issue_codes": list(issue_codes),
        "qualification_basis": qualification_basis,
        "decision": decision,
        "eligible_for_separate_generated_rights_manifest_review": eligible,
    }


def record_generated_reference_candidate_qualification_decision(
    artifact: CreativeSampleReferenceVisualPromptArtifactV1,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    candidate: CreativeSampleGeneratedReferenceCandidateV1,
    request: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
    *,
    png_path: Path,
    evidence_documents: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
    preparer_reference_bytes: bytes,
    preparer_action_bytes: bytes,
    qualifier_reference_bytes: bytes,
    qualifier_action_bytes: bytes,
    decision_at: str,
    gate_results: tuple[GeneratedReferenceQualificationGateResultV1, ...],
    qualification_issue_codes: tuple[QualificationIssueCode, ...],
    qualification_basis: str,
    decision: QualificationDecision,
) -> CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1:
    """Record one scoped independent-human Decision without granting reusable authority."""

    try:
        decision_at = _utc_seconds(decision_at, field="decision_at")
        qualification_basis = _validate_human_text(
            qualification_basis,
            field="qualification_basis",
            maximum=1000,
        )
        validated_request = _revalidate(
            request,
            CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
            field="Qualification Request",
        )
        rebuilt_request = prepare_generated_reference_candidate_qualification_request(
            artifact,
            outcome,
            candidate,
            png_path=png_path,
            evidence_documents=evidence_documents,
            preparer_reference_bytes=preparer_reference_bytes,
            preparer_action_bytes=preparer_action_bytes,
            requested_at=validated_request.requested_at,
        )
        if rebuilt_request != validated_request:
            _invalid("Request is not the exact rebuilt Qualification closure")
        validated_outcome = _revalidate(
            outcome,
            CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
            field="Outcome",
        )
        validated_candidate = _revalidate(
            candidate,
            CreativeSampleGeneratedReferenceCandidateV1,
            field="Candidate",
        )
        if not (
            _parse_utc(validated_request.requested_at)
            <= _parse_utc(decision_at)
            < _parse_utc(validated_request.request_valid_until)
        ):
            _invalid("decision_at is outside the half-open Request interval")
        references, evidence_digests = _admit_evidence_documents(evidence_documents)
        for item in references:
            if item.category not in _SUBMISSION_TIME_CATEGORIES and (
                _parse_utc(decision_at) < _parse_utc(item.effective_from)
                or (
                    item.effective_until != "PERPETUAL"
                    and _parse_utc(decision_at) >= _parse_utc(item.effective_until)
                )
            ):
                _invalid(f"{item.category} was not effective at decision_at")
        if type(gate_results) is not tuple or len(gate_results) != 15:
            _invalid("gate_results must be an exact 15-item tuple")
        validated_gate_results = tuple(
            _revalidate(item, GeneratedReferenceQualificationGateResultV1, field=f"Gate {index}")
            for index, item in enumerate(gate_results)
        )
        if tuple(item.gate for item in validated_gate_results) != QUALIFICATION_GATE_ORDER:
            _invalid("gate_results are not in the frozen policy order")
        _validate_gate_evidence_mapping(validated_gate_results, references)
        remote_processing_result = validated_gate_results[
            QUALIFICATION_GATE_ORDER.index("REMOTE_PROCESSING_AUTHORIZED_AT_SUBMISSION")
        ]
        if (
            validated_outcome.historical_execution_authorization_status
            in {"CLAIMED_ABSENT", "UNKNOWN"}
            and remote_processing_result.result == "PASS"
        ):
            _invalid(
                "REMOTE_PROCESSING_AUTHORIZED_AT_SUBMISSION cannot PASS when historical "
                "execution authorization is absent or unknown"
            )
        expected_codes, expected_decision, eligible = _derive_decision(validated_gate_results)
        if (
            type(qualification_issue_codes) is not tuple
            or qualification_issue_codes != expected_codes
            or decision != expected_decision
        ):
            _invalid("supplied issues or Decision do not match the exact Gate Result mapping")
        preparer_reference, preparer_ref_sha = _human_reference(
            preparer_reference_bytes,
            field="preparer human-reference record",
        )
        _preparer_action, preparer_action_sha = _validate_exact_record(
            preparer_action_bytes,
            expected=_request_preparer_action_expected(
                actor_ref_sha256=preparer_ref_sha,
                candidate=validated_candidate,
                outcome=validated_outcome,
                requested_at=validated_request.requested_at,
                evidence_digests=evidence_digests,
            ),
            maximum=_MAX_RETAINED_RECORD_BYTES,
            field="preparer action record",
        )
        qualifier_reference, qualifier_ref_sha = _human_reference(
            qualifier_reference_bytes,
            field="qualifier human-reference record",
        )
        if (
            preparer_reference["identity_namespace"],
            preparer_reference["identity_ref"],
        ) == (
            qualifier_reference["identity_namespace"],
            qualifier_reference["identity_ref"],
        ):
            _invalid("evidence preparer and qualifier identities must be distinct")
        expected_action = _qualifier_action_expected(
            actor_ref_sha256=qualifier_ref_sha,
            request=validated_request,
            decision_at=decision_at,
            gate_results=validated_gate_results,
            issue_codes=expected_codes,
            qualification_basis=qualification_basis,
            decision=expected_decision,
            eligible=eligible,
        )
        _qualifier_action, qualifier_action_sha = _validate_exact_record(
            qualifier_action_bytes,
            expected=expected_action,
            maximum=_MAX_RETAINED_RECORD_BYTES,
            field="qualifier action record",
        )
        _ensure_no_digest_aliases(
            (
                preparer_ref_sha,
                preparer_action_sha,
                qualifier_ref_sha,
                qualifier_action_sha,
            ),
            evidence_digests=evidence_digests,
            artifact=artifact,
            outcome=validated_outcome,
            candidate=validated_candidate,
            request=validated_request,
        )
        projection: dict[str, object] = {
            "schema_version": _SCHEMA_VERSION,
            "document_type": (
                "sdc.creative-sample-generated-reference-candidate-qualification-decision-v1"
            ),
            "qualification_scope": "GENERATED_REFERENCE_CANDIDATE_INTAKE_ONLY",
            "request_id": validated_request.request_id,
            "request_sha256": validated_request.request_sha256,
            "policy_id": GENERATED_REFERENCE_QUALIFICATION_POLICY_ID,
            "policy_version": GENERATED_REFERENCE_QUALIFICATION_POLICY_VERSION,
            "policy_document_sha256": (GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256),
            "candidate_id": validated_candidate.candidate_id,
            "candidate_sha256": validated_candidate.candidate_sha256,
            "provider_attempt_outcome_id": validated_outcome.outcome_id,
            "provider_attempt_outcome_sha256": validated_outcome.outcome_sha256,
            "reference_prompt_artifact_sha256": artifact.artifact_sha256,
            "media_content_sha256": validated_candidate.media_content_sha256,
            "requested_at": validated_request.requested_at,
            "request_valid_until": validated_request.request_valid_until,
            "evidence_valid_until": validated_request.evidence_valid_until,
            "qualifier_ref_sha256": qualifier_ref_sha,
            "qualifier_record_sha256": qualifier_action_sha,
            "decision_at": decision_at,
            "qualification_valid_until": _bounded_valid_until(
                decision_at, validated_request.evidence_valid_until
            ),
            "gate_results": [_gate_result_projection(item) for item in validated_gate_results],
            "qualification_issue_codes": list(expected_codes),
            "qualification_basis": qualification_basis,
            "decision": expected_decision,
            "eligible_for_separate_generated_rights_manifest_review": eligible,
            "status": "QUALIFICATION_COMPLETE",
            "qualification_performed": True,
            "rights_manifest_embedded": False,
            "current_status_assessment_embedded": False,
            **_zero_authority_values(),
        }
        digest = _semantic_sha256(
            GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_DECISION_SHA256_DOMAIN,
            projection,
        )
        return CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1.model_validate(
            {
                **projection,
                "decision_id": (
                    f"generated_reference_candidate_qualification_decision_v1_{digest[:20]}"
                ),
                "decision_sha256": digest,
                "gate_results": validated_gate_results,
                "qualification_issue_codes": expected_codes,
            }
        )
    except (
        OSError,
        TypeError,
        ValueError,
        ValidationError,
        VisualReferencePromptCompilerError,
        zlib.error,
    ) as exc:
        raise GeneratedReferenceCandidateError(
            "Qualification Decision recording failed closed"
        ) from exc


__all__ = [
    "CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1",
    "CreativeSampleGeneratedReferenceCandidateQualificationRequestV1",
    "CreativeSampleGeneratedReferenceCandidateV1",
    "CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1",
    "GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_DECISION_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_REQUEST_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CANDIDATE_SHA256_DOMAIN",
    "GENERATED_REFERENCE_PNG_TECHNICAL_RECORD_SHA256_DOMAIN",
    "GENERATED_REFERENCE_PROVIDER_ATTEMPT_OUTCOME_SHA256_DOMAIN",
    "GENERATED_REFERENCE_PROVIDER_OUTPUT_SET_SHA256_DOMAIN",
    "GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256",
    "GENERATED_REFERENCE_QUALIFICATION_POLICY_ID",
    "GENERATED_REFERENCE_QUALIFICATION_POLICY_VERSION",
    "EVIDENCE_CATEGORY_ORDER",
    "QUALIFICATION_GATE_ORDER",
    "QUALIFICATION_ISSUE_CODE_ORDER",
    "GeneratedReferenceCandidateError",
    "GeneratedReferenceOutputDescriptorV1",
    "GeneratedReferencePngTechnicalRecordV1",
    "GeneratedReferenceQualificationEvidenceInput",
    "GeneratedReferenceQualificationEvidenceReferenceV1",
    "GeneratedReferenceQualificationGateResultV1",
    "admit_generated_reference_png",
    "build_generated_reference_provider_attempt_outcome",
    "capture_generated_reference_candidate",
    "creative_sample_generated_reference_candidate_projection",
    "creative_sample_generated_reference_candidate_qualification_decision_projection",
    "creative_sample_generated_reference_candidate_qualification_decision_sha256",
    "creative_sample_generated_reference_candidate_qualification_request_projection",
    "creative_sample_generated_reference_candidate_qualification_request_sha256",
    "creative_sample_generated_reference_candidate_sha256",
    "creative_sample_generated_reference_provider_attempt_outcome_projection",
    "creative_sample_generated_reference_provider_attempt_outcome_sha256",
    "generated_reference_png_technical_record_projection",
    "generated_reference_png_technical_record_sha256",
    "generated_reference_provider_output_set_projection",
    "generated_reference_provider_output_set_sha256",
    "prepare_generated_reference_candidate_qualification_request",
    "record_generated_reference_candidate_qualification_decision",
]
