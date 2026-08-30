"""Fixed repository-only known-answer closure for the ADR-044 boundary.

The CLI has exactly two explicit modes.  It safely reads one frozen human-reviewed source
packet, the exact ADR-043 Candidate source/derived fixtures and one first-party synthetic PNG,
then either checks or directly rewrites one derived JSON fixture.  It performs no Provider,
network, credential, clock, Runtime, publication, asset-promotion or recursive discovery work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tomllib
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Never, cast

from pydantic import ValidationError

from sdc import generated_reference_rights_current_status as rights_module
from sdc.generated_reference_candidate import (
    EVIDENCE_CATEGORY_ORDER,
    QUALIFICATION_GATE_ORDER,
    CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
    CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
    CreativeSampleGeneratedReferenceCandidateV1,
    CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    GeneratedReferenceQualificationEvidenceInput,
    GeneratedReferenceQualificationEvidenceReferenceV1,
    GeneratedReferenceQualificationGateResultV1,
    prepare_generated_reference_candidate_qualification_request,
    record_generated_reference_candidate_qualification_decision,
)
from sdc.visual_reference_prompt_compiler import (
    CreativeSampleReferenceVisualPromptArtifactV1,
)

_KNOWN_ANSWER_VERSION = "1.0.0"
_FIXTURE_DIRECTORY = (
    "tests/fixtures/visual_prompt_profiles/generated-reference-rights-current-status"
)
_REVIEWED_SOURCE_PATH = f"{_FIXTURE_DIRECTORY}/reviewed-known-answer-source-v1.json"
_DERIVED_FIXTURE_PATH = f"{_FIXTURE_DIRECTORY}/generated-known-answer-v1.json"
_CANDIDATE_DIRECTORY = "tests/fixtures/visual_prompt_profiles/generated-reference-candidate"
_CANDIDATE_SOURCE_PATH = f"{_CANDIDATE_DIRECTORY}/reviewed-known-answer-source-v1.json"
_CANDIDATE_GENERATED_PATH = f"{_CANDIDATE_DIRECTORY}/generated-known-answer-v1.json"
_CHARACTER_PNG_PATH = f"{_CANDIDATE_DIRECTORY}/character-reference-synthetic-v1.png"

_PROTECTED_FINGERPRINTS = {
    _REVIEWED_SOURCE_PATH: (
        46_739,
        "d6c74ecb90c4c14abe47dbbd3d4ecd8fff8d5a4e0e90dbb2edae166773160315",
    ),
    _CANDIDATE_SOURCE_PATH: (
        101_487,
        "b385164d9dabd467308250da41166e1a0d47b8cf8504eb15b5644590aa9edb55",
    ),
    _CANDIDATE_GENERATED_PATH: (
        84_090,
        "aaaf5fed96b2e867a99debf9ddfcc2759febd6e87ccb7defef3e4ae5f0b120a3",
    ),
    _CHARACTER_PNG_PATH: (
        5_841,
        "3c20c94c18fbd72b68a58748bae9aba2daefc6baa38e9fc1c6ab30b40e6f39fc",
    ),
}

_MAX_SOURCE_BYTES = 2_097_152
_MAX_DERIVED_BYTES = 4_194_304
_MAX_CANDIDATE_FIXTURE_BYTES = 4_194_304
_MAX_PNG_BYTES = 67_108_864
_MAX_REPOSITORY_METADATA_BYTES = 262_144
_MAX_JSON_CONTAINER_DEPTH = 24
_MAX_JSON_CONTAINER_ITEMS = 256
_WINDOWS_REPARSE_POINT_ATTRIBUTE = 0x400
_UTF8_BOM = b"\xef\xbb\xbf"

_ROOT_KEYS = (
    "historical_qualification_expiry_cases",
    "known_answer_version",
    "positive_cases",
    "source_packet_scope",
)
_POSITIVE_CASE_ID = "character-reference-current-v1"
_SOURCE_CASE_ID = "character-reference-pass"
_HISTORICAL_CASE_IDS = (
    "character-reference-pass",
    "scene-reference-pass",
)

_QUALIFICATION_GATE_EVIDENCE_CATEGORIES = {
    "PROVENANCE_CLOSURE": tuple(EVIDENCE_CATEGORY_ORDER),
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
    "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION": (
        "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
    ),
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


class GeneratedReferenceRightsCurrentStatusCodegenError(ValueError):
    """The fixed ADR-044 closure is missing, stale, unsafe or invalid."""


def _fail(message: str) -> Never:
    raise GeneratedReferenceRightsCurrentStatusCodegenError(message)


def _raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_regular_non_symlink(info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    return (
        stat.S_ISREG(info.st_mode)
        and not stat.S_ISLNK(info.st_mode)
        and not bool(attributes & _WINDOWS_REPARSE_POINT_ATTRIBUTE)
    )


def _is_directory_non_symlink(info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    return (
        stat.S_ISDIR(info.st_mode)
        and not stat.S_ISLNK(info.st_mode)
        and not bool(attributes & _WINDOWS_REPARSE_POINT_ATTRIBUTE)
    )


def _same_file(left: os.stat_result, right: os.stat_result) -> bool:
    left_identity = (getattr(left, "st_dev", None), getattr(left, "st_ino", None))
    right_identity = (getattr(right, "st_dev", None), getattr(right, "st_ino", None))
    return left_identity == right_identity and left_identity != (None, None)


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _read_stable_regular_file(path: Path, *, max_bytes: int, label: str) -> bytes:
    if type(max_bytes) is not int or max_bytes <= 0:
        _fail(f"{label} has an invalid byte boundary")
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            f"{label} is missing or inaccessible"
        ) from exc
    if not _is_regular_non_symlink(before) or before.st_nlink != 1:
        _fail(f"{label} must be one regular non-symlink file with one link")
    if not 1 <= before.st_size <= max_bytes:
        _fail(f"{label} exceeds its frozen byte boundary")
    flags = os.O_RDONLY
    if os.name == "nt":
        flags |= int(getattr(os, "O_BINARY", 0))
        flags |= int(getattr(os, "O_NOINHERIT", 0))
    else:
        flags |= int(getattr(os, "O_CLOEXEC", 0))
        no_follow = getattr(os, "O_NOFOLLOW", None)
        if type(no_follow) is not int:
            _fail("this host cannot enforce non-symlink fixture reads")
        flags |= no_follow
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if not _is_regular_non_symlink(opened) or opened.st_nlink != 1:
            _fail(f"opened {label} is not one regular file")
        if not _same_file(before, opened):
            _fail(f"{label} changed before it was opened")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                _fail(f"{label} exceeds its frozen byte boundary")
        after_handle = os.fstat(descriptor)
    except GeneratedReferenceRightsCurrentStatusCodegenError:
        raise
    except OSError as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            f"{label} could not be read safely"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        after_path = os.lstat(path)
    except OSError as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            f"{label} could not be re-inspected"
        ) from exc
    raw = b"".join(chunks)
    if (
        not _is_regular_non_symlink(after_path)
        or after_path.st_nlink != 1
        or _file_identity(before) != _file_identity(after_handle)
        or _file_identity(before) != _file_identity(after_path)
    ):
        _fail(f"{label} changed while it was read")
    if len(raw) != before.st_size:
        _fail(f"{label} byte count changed while it was read")
    return raw


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("persistent JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> Never:
    _fail(f"persistent JSON contains the non-finite number {value}")


def _validate_json_value(value: object, *, depth: int = 1) -> None:
    if depth > _MAX_JSON_CONTAINER_DEPTH:
        _fail("persistent JSON exceeds the frozen container-depth boundary")
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is str:
        text = value
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            _fail("persistent JSON contains a non-Unicode-scalar string")
        if unicodedata.normalize("NFC", text) != text:
            _fail("persistent JSON strings must already use Unicode NFC")
        return
    if type(value) is list:
        list_items = cast(list[object], value)
        if len(list_items) > _MAX_JSON_CONTAINER_ITEMS:
            _fail("persistent JSON array exceeds the frozen item boundary")
        for item in list_items:
            _validate_json_value(
                item,
                depth=depth + 1 if type(item) in {dict, list} else depth,
            )
        return
    if type(value) is dict:
        dict_items = cast(dict[object, object], value)
        if len(dict_items) > _MAX_JSON_CONTAINER_ITEMS:
            _fail("persistent JSON object exceeds the frozen field boundary")
        for key, item in dict_items.items():
            if type(key) is not str:
                _fail("persistent JSON object keys must be exact strings")
            _validate_json_value(key, depth=depth)
            _validate_json_value(
                item,
                depth=depth + 1 if type(item) in {dict, list} else depth,
            )
        return
    _fail("persistent JSON contains a value outside the canonical type set")


def _canonical_document_bytes(value: object) -> bytes:
    _validate_json_value(value)
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            "persistent JSON serialization failed"
        ) from exc


def _compact_json(value: object) -> bytes:
    _validate_json_value(value)
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            "compact canonical JSON serialization failed"
        ) from exc


def _parse_canonical_document(raw: bytes, *, label: str) -> dict[str, object]:
    if not raw or raw.startswith(_UTF8_BOM) or b"\r" in raw:
        _fail(f"{label} must use nonempty UTF-8, LF-only, no-BOM bytes")
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail(f"{label} must end with exactly one LF")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            f"{label} is not strict UTF-8 JSON"
        ) from exc
    if type(value) is not dict:
        _fail(f"{label} must have an object root")
    _validate_json_value(value)
    if _canonical_document_bytes(value) != raw:
        _fail(f"{label} is not the frozen persistent canonical JSON document")
    return cast(dict[str, object], value)


def _explicit(value: object) -> object:
    if hasattr(value, "model_dump"):
        return cast(object, value.model_dump(mode="json"))
    if isinstance(value, tuple):
        return [_explicit(item) for item in value]
    if isinstance(value, list):
        return [_explicit(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _explicit(item) for key, item in value.items()}
    return value


def _assert_source_shape(value: dict[str, object]) -> dict[str, object]:
    if tuple(value) != _ROOT_KEYS or value.get("known_answer_version") != _KNOWN_ANSWER_VERSION:
        _fail("reviewed source root keys or known_answer_version are not frozen")
    positive_cases = value.get("positive_cases")
    if type(positive_cases) is not list or len(positive_cases) != 1:
        _fail("reviewed source must contain exactly one positive case")
    positive = positive_cases[0]
    if type(positive) is not dict or positive.get("case_id") != _POSITIVE_CASE_ID:
        _fail("reviewed source positive case identity is not frozen")
    positive = cast(dict[str, object], positive)
    reused = positive.get("reused_upstream")
    qualification = positive.get("qualification")
    png = positive.get("png")
    if type(reused) is not dict or type(qualification) is not dict or type(png) is not dict:
        _fail("reviewed source upstream, Qualification or PNG closure is incomplete")
    reused = cast(dict[str, object], reused)
    qualification = cast(dict[str, object], qualification)
    png = cast(dict[str, object], png)
    if (
        reused.get("source_case_id") != _SOURCE_CASE_ID
        or reused.get("source_generated_fixture_path") != _CANDIDATE_GENERATED_PATH
        or qualification.get("evidence_source_case_id") != _SOURCE_CASE_ID
        or qualification.get("evidence_source_fixture_path") != _CANDIDATE_SOURCE_PATH
        or png.get("path") != _CHARACTER_PNG_PATH
        or png.get("size_bytes") != _PROTECTED_FINGERPRINTS[_CHARACTER_PNG_PATH][0]
        or png.get("sha256") != _PROTECTED_FINGERPRINTS[_CHARACTER_PNG_PATH][1]
    ):
        _fail("reviewed source references an unfrozen upstream fixture or PNG")
    historical = value.get("historical_qualification_expiry_cases")
    if type(historical) is not list or tuple(
        item.get("case_id") if type(item) is dict else None for item in historical
    ) != _HISTORICAL_CASE_IDS:
        _fail("reviewed source historical expiry case order is not frozen")
    scope = value.get("source_packet_scope")
    expected_scope = {
        "automated_execution_allowed": False,
        "commercial_use_rights_proven": False,
        "content_origin": "FIRST_PARTY_SYNTHETIC_TEST_CONTENT",
        "generation_authorized": False,
        "identity_authentication_claimed": False,
        "network_allowed": False,
        "provider_requests": 0,
        "purpose": "Offline deterministic SDC-ADR-044 known-answer review only",
        "real_world_currentness_asserted": False,
        "retention_allowed": False,
        "training_allowed": False,
    }
    if (
        type(scope) is not dict
        or set(cast(dict[str, object], scope)) != set(expected_scope)
        or any(
            type(cast(dict[str, object], scope).get(name)) is not type(expected)
            or cast(dict[str, object], scope).get(name) != expected
            for name, expected in expected_scope.items()
        )
    ):
        _fail("reviewed source packet scope is not the frozen zero-authority declaration")
    return positive


def _assert_fixed_paths() -> None:
    paths = (*_PROTECTED_FINGERPRINTS, _DERIVED_FIXTURE_PATH)
    if len(paths) != len(set(paths)):
        _fail("source, upstream, PNG and derived fixture paths must be distinct")
    for value in paths:
        path = Path(value)
        if (
            path.is_absolute()
            or "\\" in value
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
            or ":" in path.parts[0]
        ):
            _fail("a fixed fixture path is not canonical repository-relative POSIX text")
    if Path(_REVIEWED_SOURCE_PATH).parent != Path(_FIXTURE_DIRECTORY) or Path(
        _DERIVED_FIXTURE_PATH
    ).parent != Path(_FIXTURE_DIRECTORY):
        _fail("ADR-044 source and derived fixtures must share their fixed directory")
    if any(
        Path(value).parent != Path(_CANDIDATE_DIRECTORY)
        for value in (_CANDIDATE_SOURCE_PATH, _CANDIDATE_GENERATED_PATH, _CHARACTER_PNG_PATH)
    ):
        _fail("ADR-043 upstream fixtures must remain in their fixed directory")


def _safe_path(root: Path, relative_path: str, *, label: str) -> Path:
    if not root.is_absolute():
        _fail(f"{label} repository root must be absolute")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        _fail(f"{label} path is not one fixed repository-relative path")
    try:
        root_info = os.lstat(root)
    except OSError as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            "repository root is missing or inaccessible"
        ) from exc
    if not _is_directory_non_symlink(root_info):
        _fail("repository root must be one regular non-symlink directory")
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise GeneratedReferenceRightsCurrentStatusCodegenError(
                f"{label} ancestor is missing or inaccessible"
            ) from exc
        if not _is_directory_non_symlink(info):
            _fail(f"{label} ancestors must be regular non-symlink directories")
    candidate = root / relative
    try:
        if os.path.commonpath((str(root.resolve()), str(candidate.resolve(strict=False)))) != str(
            root.resolve()
        ):
            _fail(f"{label} escapes the fixed repository root")
    except (OSError, ValueError) as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            f"{label} could not be anchored inside the repository"
        ) from exc
    return candidate


def _read_frozen(
    root: Path,
    relative_path: str,
    *,
    max_bytes: int,
    label: str,
) -> bytes:
    path = _safe_path(root, relative_path, label=label)
    raw = _read_stable_regular_file(path, max_bytes=max_bytes, label=label)
    expected_size, expected_sha = _PROTECTED_FINGERPRINTS[relative_path]
    if len(raw) != expected_size or _raw_sha256(raw) != expected_sha:
        _fail(f"{label} does not have its frozen exact bytes")
    return raw


@dataclass(frozen=True, slots=True)
class _ProtectedInputs:
    reviewed_source_raw: bytes
    reviewed_source: dict[str, object]
    candidate_source_raw: bytes
    candidate_source: dict[str, object]
    candidate_generated_raw: bytes
    candidate_generated: dict[str, object]
    character_png_raw: bytes


@dataclass(frozen=True, slots=True)
class _ExpectedClosure:
    protected: _ProtectedInputs
    derived_value: dict[str, object]
    derived_raw: bytes


def _load_protected_inputs(root: Path) -> _ProtectedInputs:
    _assert_fixed_paths()
    reviewed_raw = _read_frozen(
        root,
        _REVIEWED_SOURCE_PATH,
        max_bytes=_MAX_SOURCE_BYTES,
        label="reviewed source fixture",
    )
    candidate_source_raw = _read_frozen(
        root,
        _CANDIDATE_SOURCE_PATH,
        max_bytes=_MAX_CANDIDATE_FIXTURE_BYTES,
        label="ADR-043 reviewed source fixture",
    )
    candidate_generated_raw = _read_frozen(
        root,
        _CANDIDATE_GENERATED_PATH,
        max_bytes=_MAX_CANDIDATE_FIXTURE_BYTES,
        label="ADR-043 generated fixture",
    )
    png_raw = _read_frozen(
        root,
        _CHARACTER_PNG_PATH,
        max_bytes=_MAX_PNG_BYTES,
        label="first-party synthetic character PNG",
    )
    reviewed = _parse_canonical_document(reviewed_raw, label="reviewed source fixture")
    _assert_source_shape(reviewed)
    return _ProtectedInputs(
        reviewed_source_raw=reviewed_raw,
        reviewed_source=reviewed,
        candidate_source_raw=candidate_source_raw,
        candidate_source=_parse_canonical_document(
            candidate_source_raw,
            label="ADR-043 reviewed source fixture",
        ),
        candidate_generated_raw=candidate_generated_raw,
        candidate_generated=_parse_canonical_document(
            candidate_generated_raw,
            label="ADR-043 generated fixture",
        ),
        character_png_raw=png_raw,
    )


def _case(value: dict[str, object], *, case_id: str, label: str) -> dict[str, object]:
    raw_cases = value.get("cases")
    if type(raw_cases) is not list:
        _fail(f"{label} cases are missing")
    matches = [
        item
        for item in cast(list[object], raw_cases)
        if type(item) is dict and cast(dict[str, object], item).get("case_id") == case_id
    ]
    if len(matches) != 1:
        _fail(f"{label} does not contain exactly one {case_id} case")
    return cast(dict[str, object], matches[0])


def _role(case: dict[str, object], role: str) -> dict[str, object]:
    raw_roles = case.get("synthetic_role_records")
    if type(raw_roles) is not list:
        _fail("positive case synthetic_role_records are missing")
    matches = [
        item
        for item in cast(list[object], raw_roles)
        if type(item) is dict and cast(dict[str, object], item).get("role") == role
    ]
    if len(matches) != 1:
        _fail(f"positive case does not contain exactly one {role} role record")
    result = cast(dict[str, object], matches[0])
    if (
        type(result.get("identity_record")) is not dict
        or type(result.get("action_semantics")) is not dict
    ):
        _fail(f"{role} identity or action semantics are incomplete")
    return result


def _identity_bytes(role: dict[str, object]) -> bytes:
    return _canonical_document_bytes(role["identity_record"])


def _parse_utc(value: object, *, field: str) -> datetime:
    if type(value) is not str:
        _fail(f"{field} must be one canonical UTC second")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            f"{field} must be one canonical UTC second"
        ) from exc
    return parsed


def _model(value: object, model_type: type[object], *, label: str) -> object:
    if type(value) is not dict:
        _fail(f"{label} must be one complete object")
    try:
        return model_type.model_validate_json(  # type: ignore[attr-defined]
            _canonical_document_bytes(value),
            strict=True,
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            f"{label} does not validate as its exact Contract"
        ) from exc


@dataclass(frozen=True, slots=True)
class _UpstreamClosure:
    artifact: CreativeSampleReferenceVisualPromptArtifactV1
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1
    candidate: CreativeSampleGeneratedReferenceCandidateV1
    qualification_request: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1
    qualification_decision: CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1
    evidence_inputs: tuple[GeneratedReferenceQualificationEvidenceInput, ...]
    preparer_identity_bytes: bytes
    preparer_action_bytes: bytes
    qualifier_identity_bytes: bytes
    qualifier_action_bytes: bytes
    png_bytes: bytes


def _qualification_gate_results(
    case: dict[str, object],
    evidence_inputs: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
) -> tuple[GeneratedReferenceQualificationGateResultV1, ...]:
    qualification = cast(dict[str, object], case["qualification"])
    raw_gates = qualification.get("expected_gate_results")
    if type(raw_gates) is not list or len(raw_gates) != 15:
        _fail("positive case must contain exactly fifteen Qualification Gate Results")
    record_by_category = {
        item.reference.category: item.reference.record_id for item in evidence_inputs
    }
    results: list[GeneratedReferenceQualificationGateResultV1] = []
    for expected_gate, raw_gate in zip(QUALIFICATION_GATE_ORDER, raw_gates, strict=True):
        if type(raw_gate) is not dict:
            _fail("Qualification Gate Result source must be one object")
        gate = cast(dict[str, object], raw_gate)
        if (
            gate.get("gate") != expected_gate
            or gate.get("result") != "PASS"
            or type(gate.get("basis")) is not str
        ):
            _fail("Qualification Gate Result order or positive result drifted")
        evidence_record_ids = tuple(
            record_by_category[category]
            for category in _QUALIFICATION_GATE_EVIDENCE_CATEGORIES[expected_gate]
        )
        results.append(
            GeneratedReferenceQualificationGateResultV1(
                gate=expected_gate,
                result="PASS",
                evidence_record_ids=evidence_record_ids,
                basis=cast(str, gate["basis"]),
            )
        )
    return tuple(results)


def _build_upstream(protected: _ProtectedInputs, case: dict[str, object]) -> _UpstreamClosure:
    source_case = _case(
        protected.candidate_source,
        case_id=_SOURCE_CASE_ID,
        label="ADR-043 reviewed source fixture",
    )
    generated_case = _case(
        protected.candidate_generated,
        case_id=_SOURCE_CASE_ID,
        label="ADR-043 generated fixture",
    )
    artifact = cast(
        CreativeSampleReferenceVisualPromptArtifactV1,
        _model(
            generated_case.get("artifact"),
            CreativeSampleReferenceVisualPromptArtifactV1,
            label="ADR-042 Artifact",
        ),
    )
    outcome = cast(
        CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
        _model(
            generated_case.get("provider_attempt_outcome"),
            CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
            label="ADR-043 Provider Attempt Outcome",
        ),
    )
    candidate = cast(
        CreativeSampleGeneratedReferenceCandidateV1,
        _model(
            generated_case.get("candidate"),
            CreativeSampleGeneratedReferenceCandidateV1,
            label="ADR-043 Candidate",
        ),
    )
    reused = cast(dict[str, object], case["reused_upstream"])
    expected_reused = {
        "artifact_sha256": artifact.artifact_sha256,
        "candidate_id": candidate.candidate_id,
        "candidate_sha256": candidate.candidate_sha256,
        "provider_attempt_outcome_id": outcome.outcome_id,
        "provider_attempt_outcome_sha256": outcome.outcome_sha256,
        "source_case_id": _SOURCE_CASE_ID,
        "source_generated_fixture_path": _CANDIDATE_GENERATED_PATH,
        "subject_id": candidate.subject_id,
    }
    if reused != expected_reused:
        _fail("reviewed source copied upstream anchors do not match exact ADR-043 objects")

    raw_evidence = source_case.get("evidence_documents")
    if type(raw_evidence) is not list or len(raw_evidence) != 10:
        _fail("ADR-043 source case must contain exactly ten evidence documents")
    reviews = cast(dict[str, object], case["qualification"]).get("refreshed_evidence_reviews")
    if type(reviews) is not list or len(reviews) != 10:
        _fail("positive case must contain exactly ten refreshed evidence reviews")
    evidence_inputs: list[GeneratedReferenceQualificationEvidenceInput] = []
    for expected_category, raw_item, raw_review in zip(
        EVIDENCE_CATEGORY_ORDER,
        raw_evidence,
        reviews,
        strict=True,
    ):
        if type(raw_item) is not dict or type(raw_review) is not dict:
            _fail("Qualification evidence or review entry is not one object")
        item = cast(dict[str, object], raw_item)
        review = cast(dict[str, object], raw_review)
        document_bytes = _canonical_document_bytes(item.get("document"))
        reference = cast(
            GeneratedReferenceQualificationEvidenceReferenceV1,
            _model(
                item.get("reference"),
                GeneratedReferenceQualificationEvidenceReferenceV1,
                label=f"Qualification evidence reference {expected_category}",
            ),
        )
        if (
            reference.category != expected_category
            or review.get("category") != expected_category
            or review.get("record_id") != reference.record_id
            or review.get("document_size_bytes") != len(document_bytes)
            or review.get("document_sha256") != _raw_sha256(document_bytes)
            or review.get("source_evidence_valid_until") != reference.evidence_valid_until
        ):
            _fail("refreshed Qualification review does not bind the exact retained evidence")
        _parse_utc(review.get("reviewed_at"), field="Qualification review reviewed_at")
        if type(review.get("review_basis")) is not str:
            _fail("Qualification review basis must be one exact string")
        evidence_inputs.append(
            GeneratedReferenceQualificationEvidenceInput(
                reference=reference,
                document_bytes=document_bytes,
            )
        )
    evidence_tuple = tuple(evidence_inputs)

    preparer = _role(case, "QUALIFICATION_PREPARER")
    qualifier = _role(case, "QUALIFICATION_QUALIFIER")
    preparer_identity = _identity_bytes(preparer)
    qualifier_identity = _identity_bytes(qualifier)
    if cast(dict[str, object], preparer["identity_record"])["identity_ref"] == cast(
        dict[str, object], qualifier["identity_record"]
    )["identity_ref"]:
        _fail("Qualification Preparer and Qualifier identities must differ")
    qualification = cast(dict[str, object], case["qualification"])
    requested_at = qualification.get("requested_at")
    decision_at = qualification.get("decision_at")
    preparer_semantics = cast(dict[str, object], preparer["action_semantics"])
    qualifier_semantics = cast(dict[str, object], qualifier["action_semantics"])
    if (
        preparer_semantics.get("action") != "PREPARED_GENERATED_REFERENCE_QUALIFICATION_EVIDENCE"
        or preparer_semantics.get("prepared_at") != requested_at
        or qualifier_semantics.get("action")
        != "RECORDED_GENERATED_REFERENCE_QUALIFICATION_DECISION"
        or qualifier_semantics.get("decision_at") != decision_at
    ):
        _fail("Qualification retained action semantics or times drifted")
    evidence_digests = tuple(_raw_sha256(item.document_bytes) for item in evidence_tuple)
    preparer_action = _canonical_document_bytes(
        {
            "document_profile": (
                "sdc.generated-reference-qualification-request-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_QUALIFICATION_EVIDENCE",
            "actor_ref_sha256": _raw_sha256(preparer_identity),
            "candidate_sha256": candidate.candidate_sha256,
            "provider_attempt_outcome_sha256": outcome.outcome_sha256,
            "policy_document_sha256": (
                "9991a23c2d12c842691585ef11fe4edc5697bccb8086ec661c23a240375d359f"
            ),
            "requested_at": requested_at,
            "evidence_document_sha256s": list(evidence_digests),
        }
    )
    png_path = _safe_path(
        Path(rights_module.__file__).resolve().parents[2],
        _CHARACTER_PNG_PATH,
        label="first-party synthetic character PNG",
    )
    request = prepare_generated_reference_candidate_qualification_request(
        artifact,
        outcome,
        candidate,
        png_path=png_path,
        evidence_documents=evidence_tuple,
        preparer_reference_bytes=preparer_identity,
        preparer_action_bytes=preparer_action,
        requested_at=cast(str, requested_at),
    )
    gate_results = _qualification_gate_results(case, evidence_tuple)
    qualification_basis = qualification.get("request_basis")
    qualifier_action = _canonical_document_bytes(
        {
            "document_profile": "sdc.generated-reference-qualification-decision-action.v1",
            "action": "RECORDED_GENERATED_REFERENCE_QUALIFICATION_DECISION",
            "actor_ref_sha256": _raw_sha256(qualifier_identity),
            "request_sha256": request.request_sha256,
            "decision_at": decision_at,
            "gate_results": [_explicit(item) for item in gate_results],
            "qualification_issue_codes": [],
            "qualification_basis": qualification_basis,
            "decision": "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
            "eligible_for_separate_generated_rights_manifest_review": True,
        }
    )
    decision = record_generated_reference_candidate_qualification_decision(
        artifact,
        outcome,
        candidate,
        request,
        png_path=png_path,
        evidence_documents=evidence_tuple,
        preparer_reference_bytes=preparer_identity,
        preparer_action_bytes=preparer_action,
        qualifier_reference_bytes=qualifier_identity,
        qualifier_action_bytes=qualifier_action,
        decision_at=cast(str, decision_at),
        gate_results=gate_results,
        qualification_issue_codes=(),
        qualification_basis=cast(str, qualification_basis),
        decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
    )
    if (
        decision.decision != qualification.get("expected_decision")
        or decision.eligible_for_separate_generated_rights_manifest_review
        is not qualification.get("expected_eligible_for_separate_generated_rights_manifest_review")
        or decision.qualification_valid_until
        != qualification.get("expected_qualification_valid_until")
    ):
        _fail("rebuilt Qualification closure does not match the reviewed known answer")
    return _UpstreamClosure(
        artifact=artifact,
        outcome=outcome,
        candidate=candidate,
        qualification_request=request,
        qualification_decision=decision,
        evidence_inputs=evidence_tuple,
        preparer_identity_bytes=preparer_identity,
        preparer_action_bytes=preparer_action,
        qualifier_identity_bytes=qualifier_identity,
        qualifier_action_bytes=qualifier_action,
        png_bytes=protected.character_png_raw,
    )


@dataclass(frozen=True, slots=True)
class _ManifestClosure:
    manifest: rights_module.CreativeSampleGeneratedReferenceRightsManifestV1
    review_evidence_documents: tuple[bytes, ...]
    maker_identity_bytes: bytes
    maker_action_bytes: bytes
    checker_identity_bytes: bytes
    checker_action_bytes: bytes


def _build_manifest(case: dict[str, object], upstream: _UpstreamClosure) -> _ManifestClosure:
    manifest_source = case.get("manifest")
    if type(manifest_source) is not dict:
        _fail("positive case Manifest source is missing")
    manifest_source = cast(dict[str, object], manifest_source)
    raw_documents = manifest_source.get("review_evidence_documents")
    raw_reviews = manifest_source.get("human_gate_reviews")
    if type(raw_documents) is not list or len(raw_documents) != 9:
        _fail("Manifest must contain exactly nine review evidence documents")
    if type(raw_reviews) is not list or len(raw_reviews) != 9:
        _fail("Manifest must contain exactly nine human Gate Results")
    evidence_inputs: list[rights_module.GeneratedReferenceRightsManifestEvidenceInput] = []
    for ordinal, (expected_category, raw_document, raw_review) in enumerate(
        zip(
            rights_module.MANIFEST_REVIEW_EVIDENCE_CATEGORY_ORDER,
            raw_documents,
            raw_reviews,
            strict=True,
        )
    ):
        if type(raw_document) is not dict or type(raw_review) is not dict:
            _fail("Manifest evidence or human Gate Result is not one object")
        document = cast(dict[str, object], raw_document)
        review = cast(dict[str, object], raw_review)
        raw = _canonical_document_bytes(document)
        if (
            document.get("category") != expected_category
            or review.get("gate") != expected_category
            or review.get("result") != "PASS"
            or review.get("evidence_record_id") != document.get("record_id")
            or any(
                type(document.get(name)) is not str
                for name in (
                    "record_id",
                    "document_profile",
                    "media_type",
                    "observed_at",
                    "effective_from",
                    "effective_until",
                    "evidence_valid_until",
                )
            )
        ):
            _fail("Manifest evidence or Gate Result order/binding drifted")
        reference = rights_module.GeneratedReferenceRightsManifestEvidenceReferenceV1(
            ordinal=ordinal,
            category=expected_category,
            record_id=cast(str, document["record_id"]),
            document_profile=cast(str, document["document_profile"]),
            document_sha256=_raw_sha256(raw),
            document_size_bytes=len(raw),
            media_type=cast(str, document["media_type"]),
            observed_at=cast(str, document["observed_at"]),
            effective_from=cast(str, document["effective_from"]),
            effective_until=cast(str, document["effective_until"]),
            evidence_valid_until=cast(str, document["evidence_valid_until"]),
        )
        evidence_inputs.append(
            rights_module.GeneratedReferenceRightsManifestEvidenceInput(
                reference=reference,
                document_bytes=raw,
            )
        )
    evidence_input_tuple = tuple(evidence_inputs)
    evidence_tuple = tuple(item.reference for item in evidence_input_tuple)
    proposed_source = manifest_source.get("proposed_rights_scope")
    reviewed_source = manifest_source.get("reviewed_rights_scope")
    if type(proposed_source) is not dict or type(reviewed_source) is not dict:
        _fail("Manifest proposed or reviewed Rights scope is incomplete")
    proposed_values = dict(cast(dict[str, object], proposed_source))
    reviewed_values = dict(cast(dict[str, object], reviewed_source))
    proposed_values["territory_scope"] = tuple(
        cast(list[object], proposed_values.get("territory_scope"))
    )
    proposed_values["allowed_use_scope"] = tuple(
        cast(list[object], proposed_values.get("allowed_use_scope"))
    )
    reviewed_values["territory_scope"] = tuple(
        cast(list[object], reviewed_values.get("territory_scope"))
    )
    reviewed_values["allowed_use_scope"] = tuple(
        cast(list[object], reviewed_values.get("allowed_use_scope"))
    )
    proposed = rights_module.GeneratedReferenceRightsScopeProposalV1.model_validate(
        proposed_values
    )
    reviewed = rights_module.GeneratedReferenceReviewedRightsScopeV1.model_validate(
        reviewed_values
    )
    qualification = upstream.qualification_decision
    artifact = upstream.artifact
    outcome = upstream.outcome
    candidate = upstream.candidate
    request = upstream.qualification_request
    manifest_at = cast(str, manifest_source.get("manifest_at"))
    snapshot = artifact.profile_snapshot
    payload = {
        "manifest_review_payload_profile": (
            "sdc.generated-reference-rights-manifest-review-payload.v1"
        ),
        "manifest_policy_id": rights_module.GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_ID,
        "manifest_policy_version": (
            rights_module.GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_VERSION
        ),
        "manifest_policy_document_sha256": (
            rights_module.GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_DOCUMENT_SHA256
        ),
        "reference_prompt_artifact_sha256": artifact.artifact_sha256,
        "provider_attempt_outcome_id": outcome.outcome_id,
        "provider_attempt_outcome_sha256": outcome.outcome_sha256,
        "candidate_id": candidate.candidate_id,
        "candidate_sha256": candidate.candidate_sha256,
        "qualification_request_id": request.request_id,
        "qualification_request_sha256": request.request_sha256,
        "qualification_decision_id": qualification.decision_id,
        "qualification_decision_sha256": qualification.decision_sha256,
        "subject_id": candidate.subject_id,
        "asset_purpose": candidate.asset_purpose,
        "profile_id": snapshot.profile_id,
        "profile_version": snapshot.profile_version,
        "profile_sha256": snapshot.profile_sha256,
        "catalog_version": snapshot.catalog_version,
        "catalog_sha256": snapshot.catalog_sha256,
        "render_input_sha256": artifact.render_input_sha256,
        "prompt_sha256": artifact.prompt_sha256,
        "prompt_size_bytes": len(artifact.prompt.encode("utf-8")),
        "prompt_render_receipt_sha256": (
            artifact.prompt_render_receipt.prompt_render_receipt_sha256
        ),
        "media_content_sha256": _raw_sha256(upstream.png_bytes),
        "media_size_bytes": len(upstream.png_bytes),
        "media_technical_record_sha256": candidate.media_technical_record_sha256,
        "provider": candidate.provider,
        "model": candidate.model,
        "provider_region": candidate.provider_region,
        "provider_terms_snapshot_id": candidate.provider_terms_snapshot_id,
        "provider_terms_snapshot_sha256": candidate.provider_terms_snapshot_sha256,
        "submitted_at": outcome.submitted_at,
        "qualification_decision_at": qualification.decision_at,
        "qualification_valid_until": qualification.qualification_valid_until,
        "manifest_at": manifest_at,
        "review_evidence_refs": [_explicit(item) for item in evidence_tuple],
        "proposed_rights_scope": _explicit(proposed),
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
    }
    payload_raw = _compact_json(payload)
    if len(payload_raw) > 262_144:
        _fail("Manifest review payload exceeds its frozen byte boundary")
    payload_sha = hashlib.sha256(
        rights_module.GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW_PAYLOAD_SHA256_DOMAIN
        + payload_raw
    ).hexdigest()

    maker = _role(case, "MANIFEST_MAKER")
    checker = _role(case, "MANIFEST_CHECKER")
    maker_identity = _identity_bytes(maker)
    checker_identity = _identity_bytes(checker)
    maker_record = cast(dict[str, object], maker["identity_record"])
    checker_record = cast(dict[str, object], checker["identity_record"])
    qualifier_record = cast(
        dict[str, object], _role(case, "QUALIFICATION_QUALIFIER")["identity_record"]
    )
    maker_semantics = cast(dict[str, object], maker["action_semantics"])
    checker_semantics = cast(dict[str, object], checker["action_semantics"])
    if (
        (maker_record["identity_namespace"], maker_record["identity_ref"])
        == (checker_record["identity_namespace"], checker_record["identity_ref"])
        or (checker_record["identity_namespace"], checker_record["identity_ref"])
        == (qualifier_record["identity_namespace"], qualifier_record["identity_ref"])
    ):
        _fail("Manifest Maker/Checker/Qualifier semantic identity separation failed")
    maker_prepared_at = maker_semantics.get("prepared_at")
    if (
        maker_semantics.get("action")
        != "PREPARED_GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW"
        or checker_semantics.get("action")
        != "RECORDED_GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW"
        or checker_semantics.get("reviewed_at") != manifest_at
    ):
        _fail("Manifest retained action semantics or times drifted")
    maker_action = _canonical_document_bytes(
        {
            "document_profile": (
                "sdc.generated-reference-rights-manifest-review-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW",
            "actor_identity_ref_sha256": _raw_sha256(maker_identity),
            "manifest_review_payload_sha256": payload_sha,
            "prepared_at": maker_prepared_at,
        }
    )

    gates: list[rights_module.GeneratedReferenceRightsManifestGateResultV1] = [
        rights_module.GeneratedReferenceRightsManifestGateResultV1(
            ordinal=0,
            gate=rights_module.MANIFEST_REVIEW_GATE_ORDER[0],
            result="PASS",
            evidence_record_ids=(),
            basis="COMPILER_REVALIDATED_EXACT_ADR042_ADR043_CLOSURE",
        )
    ]
    for ordinal, (expected_gate, evidence, raw_review) in enumerate(
        zip(
            rights_module.MANIFEST_REVIEW_GATE_ORDER[1:10],
            evidence_tuple,
            raw_reviews,
            strict=True,
        ),
        start=1,
    ):
        review = cast(dict[str, object], raw_review)
        if review.get("gate") != expected_gate or type(review.get("basis")) is not str:
            _fail("Manifest human Gate order drifted")
        gates.append(
            rights_module.GeneratedReferenceRightsManifestGateResultV1(
                ordinal=ordinal,
                gate=expected_gate,
                result="PASS",
                evidence_record_ids=(evidence.record_id,),
                basis=cast(str, review["basis"]),
            )
        )
    gates.append(
        rights_module.GeneratedReferenceRightsManifestGateResultV1(
            ordinal=10,
            gate=rights_module.MANIFEST_REVIEW_GATE_ORDER[10],
            result="PASS",
            evidence_record_ids=(),
            basis="COMPILER_REVALIDATED_DISTINCT_ROLE_AND_ACTION_CLOSURE",
        )
    )
    gate_tuple = tuple(gates)
    checker_action = _canonical_document_bytes(
        {
            "document_profile": (
                "sdc.generated-reference-rights-manifest-review-checker-action.v1"
            ),
            "action": "RECORDED_GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW",
            "actor_identity_ref_sha256": _raw_sha256(checker_identity),
            "manifest_review_payload_sha256": payload_sha,
            "maker_action_sha256": _raw_sha256(maker_action),
            "reviewed_at": manifest_at,
            "gate_results": [_explicit(item) for item in gate_tuple],
            "reviewed_rights_scope": _explicit(reviewed),
            "disposition": "PASS_FOR_SEPARATE_GENERATED_CURRENT_STATUS_ASSESSMENT",
        }
    )

    manifest = rights_module.build_generated_reference_rights_manifest(
        upstream.artifact,
        upstream.outcome,
        upstream.candidate,
        upstream.qualification_request,
        upstream.qualification_decision,
        png_bytes=upstream.png_bytes,
        qualification_evidence_documents=upstream.evidence_inputs,
        qualification_preparer_identity_bytes=upstream.preparer_identity_bytes,
        qualification_preparer_action_bytes=upstream.preparer_action_bytes,
        qualifier_identity_bytes=upstream.qualifier_identity_bytes,
        qualifier_action_bytes=upstream.qualifier_action_bytes,
        review_evidence_documents=evidence_input_tuple,
        proposed_rights_scope=proposed,
        maker_identity_bytes=maker_identity,
        maker_action_bytes=maker_action,
        checker_identity_bytes=checker_identity,
        checker_action_bytes=checker_action,
        manifest_at=manifest_at,
    )
    rights_module.verify_generated_reference_rights_manifest(
        manifest,
        upstream.artifact,
        upstream.outcome,
        upstream.candidate,
        upstream.qualification_request,
        upstream.qualification_decision,
        png_bytes=upstream.png_bytes,
        qualification_evidence_documents=upstream.evidence_inputs,
        qualification_preparer_identity_bytes=upstream.preparer_identity_bytes,
        qualification_preparer_action_bytes=upstream.preparer_action_bytes,
        qualifier_identity_bytes=upstream.qualifier_identity_bytes,
        qualifier_action_bytes=upstream.qualifier_action_bytes,
        review_evidence_documents=evidence_input_tuple,
        proposed_rights_scope=proposed,
        maker_identity_bytes=maker_identity,
        maker_action_bytes=maker_action,
        checker_identity_bytes=checker_identity,
        checker_action_bytes=checker_action,
        manifest_at=manifest_at,
    )
    if (
        manifest.manifest_review_payload_sha256 != payload_sha
        or rights_module.generated_reference_rights_manifest_review_payload_sha256(manifest)
        != payload_sha
        or manifest.gate_results != gate_tuple
        or manifest.proposed_rights_scope != proposed
        or manifest.reviewed_rights_scope != reviewed
        or manifest.manifest_valid_until
        != manifest_source.get("expected_manifest_valid_until")
    ):
        _fail("rebuilt Manifest does not match the reviewed known answer")
    return _ManifestClosure(
        manifest=manifest,
        review_evidence_documents=tuple(item.document_bytes for item in evidence_input_tuple),
        maker_identity_bytes=maker_identity,
        maker_action_bytes=maker_action,
        checker_identity_bytes=checker_identity,
        checker_action_bytes=checker_action,
    )


@dataclass(frozen=True, slots=True)
class _CurrentStatusClosure:
    subject_closure: rights_module.GeneratedReferenceCurrentStatusSubjectClosureV1
    observation_inputs: tuple[rights_module.GeneratedReferenceCurrentStatusObservationInput, ...]
    request: rights_module.CreativeSampleGeneratedReferenceCurrentStatusRequestV1
    instruction: rights_module.CreativeSampleGeneratedReferenceCurrentStatusInstructionV1
    decision: rights_module.CreativeSampleGeneratedReferenceCurrentStatusDecisionV1
    evidence_record: rights_module.CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1
    chain_inputs: tuple[rights_module.GeneratedReferenceCurrentStatusExplicitChainInput, ...]
    process_result: rights_module.GeneratedReferenceCurrentStatusReceiptProcessResult
    preparer_identity_bytes: bytes
    preparer_action_bytes: bytes
    checker_identity_bytes: bytes
    checker_action_bytes: bytes


def _canonical_request_refs(
    observations: tuple[
        rights_module.CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1, ...
    ],
) -> tuple[rights_module.GeneratedReferenceCurrentStatusObservationRefV1, ...]:
    category_index = {
        category: index
        for index, category in enumerate(rights_module.CURRENT_STATUS_CATEGORY_ORDER)
    }
    unordered = tuple(
        rights_module.generated_reference_current_status_observation_ref(
            observation,
            ordinal=0,
        )
        for observation in observations
    )
    ordered = tuple(
        sorted(
            unordered,
            key=lambda item: (
                category_index[item.category],
                item.valid_from,
                item.observation_id,
            ),
        )
    )
    return tuple(
        rights_module.GeneratedReferenceCurrentStatusObservationRefV1.model_validate(
            {**cast(dict[str, object], _explicit(item)), "ordinal": ordinal}
        )
        for ordinal, item in enumerate(ordered)
    )


def _current_status_category_results(
    request: rights_module.CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    observations: tuple[
        rights_module.CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1, ...
    ],
) -> tuple[rights_module.GeneratedReferenceCurrentStatusCategoryResultV1, ...]:
    observation_by_category = {item.category: item for item in observations}
    reference_by_category = {item.category: item for item in request.observation_refs}
    results: list[rights_module.GeneratedReferenceCurrentStatusCategoryResultV1] = []
    for ordinal, category in enumerate(rights_module.CURRENT_STATUS_CATEGORY_ORDER):
        observation = observation_by_category[category]
        reference = reference_by_category[category]
        effect: rights_module.CurrentStatusDeterministicEffect
        if ordinal < 4:
            if observation.claim_value != "ABSENT_WITH_EVIDENCE":
                _fail("positive known answer lacks explicit adverse-absence evidence")
            effect = "ADVERSE_ABSENT"
        else:
            if observation.claim_value != "PRESENT":
                _fail("positive known answer lacks one required positive predicate")
            effect = "POSITIVE_PRESENT"
        results.append(
            rights_module.GeneratedReferenceCurrentStatusCategoryResultV1(
                ordinal=ordinal,
                category=category,
                claim_value=observation.claim_value,
                deterministic_effect=effect,
                category_observation_refs=(reference,),
                relied_on_observation_refs=(reference,),
                result_valid_until=min(
                    request.request_valid_until,
                    request.subject_closure.manifest_valid_until,
                    reference.valid_until,
                ),
            )
        )
    return tuple(results)


def _build_current_status(
    case: dict[str, object],
    manifest_closure: _ManifestClosure,
) -> _CurrentStatusClosure:
    current_source = case.get("current_status")
    raw_observations = (
        cast(dict[str, object], current_source).get("observations")
        if type(current_source) is dict
        else None
    )
    if type(current_source) is not dict or type(raw_observations) is not list:
        _fail("positive case current-status source is incomplete")
    current_source = cast(dict[str, object], current_source)
    if len(raw_observations) != 9:
        _fail("positive case must contain exactly nine current-status observations")
    if current_source.get("limitation_codes") != list(
        rights_module.CURRENT_STATUS_LIMITATION_CODE_ORDER
    ):
        _fail("current-status limitation-code order drifted")

    subject_closure = rights_module.build_generated_reference_current_status_subject_closure(
        manifest_closure.manifest
    )
    observation_inputs: list[rights_module.GeneratedReferenceCurrentStatusObservationInput] = []
    observation_keys: list[str] = []
    expected_observation_keys = {
        "basis_code",
        "basis_note",
        "category",
        "claim_value",
        "link_kind",
        "observation_key",
        "observed_at",
        "source_event_at",
        "source_kind",
        "source_object",
        "source_object_media_type",
        "source_object_ref",
        "source_reference",
        "valid_from",
        "valid_until",
    }
    for expected_category, raw_observation in zip(
        rights_module.CURRENT_STATUS_CATEGORY_ORDER,
        raw_observations,
        strict=True,
    ):
        if type(raw_observation) is not dict:
            _fail("current-status Observation source must be one object")
        source = cast(dict[str, object], raw_observation)
        if set(source) != expected_observation_keys:
            _fail("current-status Observation source fields drifted")
        if source.get("category") != expected_category or source.get("link_kind") != "GENESIS":
            _fail("current-status Observation category order or link kind drifted")
        observation_key = source.get("observation_key")
        if type(observation_key) is not str:
            _fail("current-status observation_key must be one string")
        observation_keys.append(observation_key)
        source_identity_bytes = _canonical_document_bytes(source.get("source_reference"))
        source_object_bytes = _canonical_document_bytes(source.get("source_object"))
        observation = rights_module.build_generated_reference_current_status_source_observation(
            subject_closure=subject_closure,
            category=cast(rights_module.CurrentStatusCategory, source["category"]),
            claim_value=cast(rights_module.CurrentStatusClaimValue, source["claim_value"]),
            source_kind=cast(rights_module.CurrentStatusSourceKind, source["source_kind"]),
            basis_code=cast(rights_module.CurrentStatusBasisCode, source["basis_code"]),
            basis_note=cast(str, source["basis_note"]),
            source_identity_bytes=source_identity_bytes,
            source_object_ref=cast(str, source["source_object_ref"]),
            source_object_bytes=source_object_bytes,
            source_object_media_type=cast(str, source["source_object_media_type"]),
            source_event_at=cast(str, source["source_event_at"]),
            observed_at=cast(str, source["observed_at"]),
            valid_from=cast(str, source["valid_from"]),
            valid_until=cast(str, source["valid_until"]),
            link_kind="GENESIS",
        )
        document_bytes = _canonical_document_bytes(_explicit(observation))
        observation_inputs.append(
            rights_module.GeneratedReferenceCurrentStatusObservationInput(
                observation=observation,
                document_bytes=document_bytes,
            )
        )
    if len(observation_keys) != len(set(observation_keys)):
        _fail("current-status observation_key values must be unique")
    observation_input_tuple = tuple(observation_inputs)
    observations = tuple(item.observation for item in observation_input_tuple)
    expected_refs = _canonical_request_refs(observations)

    requested_at = cast(str, case.get("requested_at"))
    requested = _parse_utc(requested_at, field="requested_at")
    request_valid_until = min(
        requested + timedelta(seconds=86_400),
        _parse_utc(subject_closure.manifest_valid_until, field="manifest_valid_until"),
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    if request_valid_until != current_source.get("expected_request_valid_until"):
        _fail("derived Request deadline does not match the reviewed known answer")
    preparer = _role(case, "STATUS_PREPARER")
    preparer_identity = _identity_bytes(preparer)
    preparer_semantics = cast(dict[str, object], preparer["action_semantics"])
    if (
        preparer_semantics.get("action")
        != "PREPARED_GENERATED_REFERENCE_CURRENT_STATUS_REQUEST"
        or preparer_semantics.get("requested_at") != requested_at
    ):
        _fail("Status Preparer action semantics or time drifted")
    request_basis = cast(str, current_source.get("request_basis"))
    preparer_action = _canonical_document_bytes(
        {
            "document_profile": (
                "sdc.generated-reference-current-status-request-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_CURRENT_STATUS_REQUEST",
            "actor_identity_ref_sha256": _raw_sha256(preparer_identity),
            "subject_closure_sha256": subject_closure.closure_sha256,
            "policy_document_sha256": (
                rights_module.GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256
            ),
            "requested_at": requested_at,
            "request_valid_until": request_valid_until,
            "observation_target_refs": [_explicit(item) for item in expected_refs],
            "request_basis": request_basis,
        }
    )
    request = rights_module.build_generated_reference_current_status_request(
        subject_closure=subject_closure,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        requested_at=requested_at,
        target_observations=observation_input_tuple,
        request_basis=request_basis,
    )
    if (
        request.observation_refs != expected_refs
        or request.request_valid_until != request_valid_until
    ):
        _fail("rebuilt Request does not match the reviewed known answer")

    reference_by_id = {item.observation_id: item for item in request.observation_refs}
    chain_inputs = tuple(
        sorted(
            (
                rights_module.GeneratedReferenceCurrentStatusExplicitChainInput(
                    target_observation_refs=(reference_by_id[item.observation.observation_id],),
                    observation_inputs=(item,),
                )
                for item in observation_input_tuple
            ),
            key=lambda item: (
                item.target_observation_refs[0].chain_scope_sha256,
                item.target_observation_refs[0].observation_id,
            ),
        )
    )
    category_results = _current_status_category_results(request, observations)
    status_valid_until = min(item.result_valid_until for item in category_results)
    if status_valid_until != current_source.get("expected_status_valid_until"):
        _fail("derived current-status deadline does not match the reviewed known answer")

    checker = _role(case, "STATUS_CHECKER")
    checker_identity = _identity_bytes(checker)
    checker_semantics = cast(dict[str, object], checker["action_semantics"])
    evaluated_at = cast(str, case.get("evaluated_at"))
    if (
        checker_semantics.get("action")
        != "RECORDED_GENERATED_REFERENCE_CURRENT_STATUS_DECISION"
        or checker_semantics.get("evaluated_at") != evaluated_at
    ):
        _fail("Status Checker action semantics or time drifted")
    checker_basis = cast(str, current_source.get("status_checker_basis"))
    checker_action = _canonical_document_bytes(
        {
            "document_profile": (
                "sdc.generated-reference-current-status-decision-checker-action.v1"
            ),
            "action": "RECORDED_GENERATED_REFERENCE_CURRENT_STATUS_DECISION",
            "actor_identity_ref_sha256": _raw_sha256(checker_identity),
            "request_sha256": request.request_sha256,
            "evaluated_at": evaluated_at,
            "category_results": [_explicit(item) for item in category_results],
            "checker_basis": checker_basis,
            "status_valid_until": status_valid_until,
            "recorded_status": "CURRENT",
        }
    )
    instruction = rights_module.build_generated_reference_current_status_instruction(
        request=request,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
        evaluated_at=evaluated_at,
        checker_basis=checker_basis,
    )
    if instruction.category_results != category_results:
        _fail("compiler-derived category results differ from reviewed known answer")
    decision = rights_module.build_generated_reference_current_status_decision(
        request=request,
        instruction=instruction,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
    )
    evidence_record = rights_module.build_generated_reference_current_status_evidence_record(
        request=request,
        instruction=instruction,
        decision=decision,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
    )
    process_result = (
        rights_module.process_generated_reference_current_status_record_as_of_assessment(
            evidence_record,
            manifest_closure.manifest,
            chain_inputs,
            as_of=cast(str, case.get("as_of")),
        )
    )
    rights_module.verify_generated_reference_current_status_record_as_of_assessment_receipt(
        process_result.receipt,
        record=evidence_record,
        manifest=manifest_closure.manifest,
        chain_inputs=chain_inputs,
    )
    if (
        decision.recorded_status != "CURRENT"
        or process_result.assessment.as_of_status != "CURRENT"
        or decision.recorded_status != cast(dict[str, object], case["expected"]).get(
            "recorded_status"
        )
        or process_result.assessment.as_of_status
        != cast(dict[str, object], case["expected"]).get("as_of_status")
    ):
        _fail("rebuilt current-status closure differs from reviewed known answer")
    return _CurrentStatusClosure(
        subject_closure=subject_closure,
        observation_inputs=observation_input_tuple,
        request=request,
        instruction=instruction,
        decision=decision,
        evidence_record=evidence_record,
        chain_inputs=chain_inputs,
        process_result=process_result,
        preparer_identity_bytes=preparer_identity,
        preparer_action_bytes=preparer_action,
        checker_identity_bytes=checker_identity,
        checker_action_bytes=checker_action,
    )


def _historical_expiry_results(
    protected: _ProtectedInputs,
) -> list[dict[str, object]]:
    raw_cases = protected.reviewed_source.get("historical_qualification_expiry_cases")
    if type(raw_cases) is not list:
        _fail("historical Qualification expiry cases are missing")
    results: list[dict[str, object]] = []
    for raw_case in raw_cases:
        if type(raw_case) is not dict:
            _fail("historical Qualification expiry case must be one object")
        source = cast(dict[str, object], raw_case)
        case_id = cast(str, source.get("case_id"))
        generated = _case(
            protected.candidate_generated,
            case_id=case_id,
            label="ADR-043 generated fixture",
        )
        decision = cast(
            CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
            _model(
                generated.get("qualification_decision"),
                CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
                label=f"historical Qualification Decision {case_id}",
            ),
        )
        attempt_at = _parse_utc(source.get("manifest_attempt_at"), field="manifest_attempt_at")
        valid_until = _parse_utc(
            decision.qualification_valid_until,
            field="historical qualification_valid_until",
        )
        expected = {
            "case_id": case_id,
            "expected_failure_code": "TIME_WINDOW_INVALID_OR_EXPIRED",
            "expected_manifest_created": False,
            "historical_decision_at": decision.decision_at,
            "historical_decision_id": decision.decision_id,
            "historical_decision_sha256": decision.decision_sha256,
            "historical_qualification_valid_until": decision.qualification_valid_until,
            "manifest_attempt_at": cast(str, source.get("manifest_attempt_at")),
            "source_generated_fixture_path": _CANDIDATE_GENERATED_PATH,
        }
        if source != expected or attempt_at < valid_until:
            _fail("historical Qualification expiry known answer drifted")
        results.append(
            {
                **source,
                "observed_failure_code": "TIME_WINDOW_INVALID_OR_EXPIRED",
                "manifest_created": False,
            }
        )
    return results


def _assert_zero_authority(
    values: tuple[object, ...],
    expected: dict[str, object],
) -> None:
    for value in values:
        if not hasattr(value, "model_dump"):
            _fail("zero-authority validation received a non-Contract value")
        dumped = cast(dict[str, object], value.model_dump(mode="json"))
        for name, wanted in expected.items():
            actual = dumped.get(name)
            if type(actual) is not type(wanted) or actual != wanted:
                _fail(f"formal Contract zero-authority field {name} drifted")


def _build_expected_closure(root: Path) -> _ExpectedClosure:
    try:
        _assert_fixed_paths()
        protected = _load_protected_inputs(root)
        case = _assert_source_shape(protected.reviewed_source)
        upstream = _build_upstream(protected, case)
        manifest = _build_manifest(case, upstream)
        current = _build_current_status(case, manifest)
        expected = case.get("expected")
        if type(expected) is not dict or type(expected.get("zero_authority_surface")) is not dict:
            _fail("positive case zero-authority expectation is incomplete")
        zero_authority = cast(dict[str, object], expected["zero_authority_surface"])
        formal_values: tuple[object, ...] = (
            manifest.manifest,
            *(item.observation for item in current.observation_inputs),
            current.request,
            current.instruction,
            current.decision,
            current.evidence_record,
            current.process_result.receipt,
        )
        _assert_zero_authority(formal_values, zero_authority)
        explicit_chain_inputs = [
            {
                "target_observation_refs": [
                    _explicit(item) for item in chain.target_observation_refs
                ],
                "observations": [
                    _explicit(item.observation) for item in chain.observation_inputs
                ],
            }
            for chain in current.chain_inputs
        ]
        positive_case = {
            "case_id": case["case_id"],
            "artifact": _explicit(upstream.artifact),
            "provider_attempt_outcome": _explicit(upstream.outcome),
            "candidate": _explicit(upstream.candidate),
            "qualification_request": _explicit(upstream.qualification_request),
            "qualification_decision": _explicit(upstream.qualification_decision),
            "rights_manifest": _explicit(manifest.manifest),
            "subject_closure": _explicit(current.subject_closure),
            "source_observations": [
                _explicit(item.observation) for item in current.observation_inputs
            ],
            "current_status_request": _explicit(current.request),
            "current_status_instruction": _explicit(current.instruction),
            "current_status_decision": _explicit(current.decision),
            "current_status_evidence_record": _explicit(current.evidence_record),
            "explicit_chain_inputs": explicit_chain_inputs,
            "record_as_of_assessment": {
                "as_of": current.process_result.assessment.as_of,
                "as_of_assessment_sha256": (
                    current.process_result.assessment.as_of_assessment_sha256
                ),
                "as_of_status": current.process_result.assessment.as_of_status,
                "coverage_set_sha256": (
                    current.process_result.assessment.coverage_set_sha256
                ),
                "explicit_chain_set_sha256": (
                    current.process_result.assessment.explicit_chain_set_sha256
                ),
                "joint_replay_sha256": (
                    current.process_result.assessment.joint_replay_sha256
                ),
                "recorded_status": current.process_result.assessment.recorded_status,
                "status_valid_until": (
                    current.process_result.assessment.status_valid_until
                ),
            },
            "record_as_of_assessment_receipt": _explicit(current.process_result.receipt),
        }
        derived_value: dict[str, object] = {
            "current_status_policy_document_sha256": (
                rights_module.GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256
            ),
            "historical_qualification_expiry_cases": _historical_expiry_results(protected),
            "known_answer_version": _KNOWN_ANSWER_VERSION,
            "manifest_policy_document_sha256": (
                rights_module.GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_DOCUMENT_SHA256
            ),
            "positive_cases": [positive_case],
            "reviewed_source": {
                "path": _REVIEWED_SOURCE_PATH,
                "raw_sha256": _raw_sha256(protected.reviewed_source_raw),
                "size_bytes": len(protected.reviewed_source_raw),
            },
            "upstream_inputs": {
                "candidate_generated_fixture_path": _CANDIDATE_GENERATED_PATH,
                "candidate_generated_raw_sha256": _raw_sha256(
                    protected.candidate_generated_raw
                ),
                "candidate_generated_size_bytes": len(protected.candidate_generated_raw),
                "candidate_source_fixture_path": _CANDIDATE_SOURCE_PATH,
                "candidate_source_raw_sha256": _raw_sha256(protected.candidate_source_raw),
                "candidate_source_size_bytes": len(protected.candidate_source_raw),
                "character_png_path": _CHARACTER_PNG_PATH,
                "character_png_raw_sha256": _raw_sha256(protected.character_png_raw),
                "character_png_size_bytes": len(protected.character_png_raw),
            },
        }
        derived_raw = _canonical_document_bytes(derived_value)
        if not 1 <= len(derived_raw) <= _MAX_DERIVED_BYTES:
            _fail("derived known-answer fixture exceeds its frozen byte boundary")
        return _ExpectedClosure(
            protected=protected,
            derived_value=derived_value,
            derived_raw=derived_raw,
        )
    except GeneratedReferenceRightsCurrentStatusCodegenError:
        raise
    except Exception as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            "fixed ADR-044 known-answer closure could not be rebuilt"
        ) from exc


def _protected_file_infos(root: Path) -> tuple[os.stat_result, ...]:
    infos: list[os.stat_result] = []
    for relative_path in _PROTECTED_FINGERPRINTS:
        path = _safe_path(root, relative_path, label="protected input")
        try:
            info = os.lstat(path)
        except OSError as exc:
            raise GeneratedReferenceRightsCurrentStatusCodegenError(
                "protected input could not be inspected before update"
            ) from exc
        if not _is_regular_non_symlink(info) or info.st_nlink != 1:
            _fail("protected input must remain one regular non-symlink file with one link")
        infos.append(info)
    return tuple(infos)


def _write_exact_derived(root: Path, relative_path: str, raw: bytes) -> None:
    if relative_path != _DERIVED_FIXTURE_PATH:
        _fail("update attempted to write outside the single fixed derived-fixture allowlist")
    if type(raw) is not bytes or not 1 <= len(raw) <= _MAX_DERIVED_BYTES:
        _fail("derived fixture write bytes are outside the fixed boundary")
    _parse_canonical_document(raw, label="derived known-answer fixture write bytes")
    destination = _safe_path(root, relative_path, label="derived known-answer fixture")
    protected_infos = _protected_file_infos(root)
    try:
        before = os.lstat(destination)
    except FileNotFoundError:
        before = None
    except OSError as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            "derived fixture destination could not be inspected"
        ) from exc
    if before is not None:
        if not _is_regular_non_symlink(before) or before.st_nlink != 1:
            _fail("derived fixture destination must be one regular non-symlink file")
        if any(_same_file(info, before) for info in protected_infos):
            _fail("derived fixture destination must not alias a protected input")
    flags = os.O_WRONLY
    if before is None:
        flags |= os.O_CREAT | os.O_EXCL
    if os.name == "nt":
        flags |= int(getattr(os, "O_BINARY", 0))
        flags |= int(getattr(os, "O_NOINHERIT", 0))
    else:
        flags |= int(getattr(os, "O_CLOEXEC", 0))
        no_follow = getattr(os, "O_NOFOLLOW", None)
        if type(no_follow) is not int:
            _fail("this host cannot enforce non-symlink fixture writes")
        flags |= no_follow
    descriptor: int | None = None
    try:
        descriptor = os.open(destination, flags, 0o644)
        opened = os.fstat(descriptor)
        if not _is_regular_non_symlink(opened) or opened.st_nlink != 1:
            _fail("opened derived fixture is not one regular file")
        if before is not None and not _same_file(before, opened):
            _fail("derived fixture destination changed before it was opened")
        if any(_same_file(info, opened) for info in protected_infos):
            _fail("opened derived fixture aliases a protected input")
        os.ftruncate(descriptor, 0)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                _fail("derived fixture write made no progress")
            offset += written
        os.fsync(descriptor)
        after_handle = os.fstat(descriptor)
    except GeneratedReferenceRightsCurrentStatusCodegenError:
        raise
    except OSError as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            "derived fixture could not be written directly"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        after_path = os.lstat(destination)
    except OSError as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            "derived fixture could not be re-inspected"
        ) from exc
    if (
        not _is_regular_non_symlink(after_path)
        or after_path.st_nlink != 1
        or not _same_file(after_handle, after_path)
        or after_path.st_size != len(raw)
    ):
        _fail("derived fixture changed while it was written")
    actual = _read_stable_regular_file(
        destination,
        max_bytes=_MAX_DERIVED_BYTES,
        label="derived known-answer fixture",
    )
    if actual != raw:
        _fail("derived fixture final bytes differ from the requested bytes")
    for protected_path in _PROTECTED_FINGERPRINTS:
        _safe_path(root, protected_path, label="protected input")


def _same_protected_inputs(left: _ProtectedInputs, right: _ProtectedInputs) -> bool:
    return (
        left.reviewed_source_raw == right.reviewed_source_raw
        and left.reviewed_source == right.reviewed_source
        and left.candidate_source_raw == right.candidate_source_raw
        and left.candidate_source == right.candidate_source
        and left.candidate_generated_raw == right.candidate_generated_raw
        and left.candidate_generated == right.candidate_generated
        and left.character_png_raw == right.character_png_raw
    )


def _check_closure(root: Path, closure: _ExpectedClosure) -> None:
    path = _safe_path(root, _DERIVED_FIXTURE_PATH, label="derived known-answer fixture")
    actual = _read_stable_regular_file(
        path,
        max_bytes=_MAX_DERIVED_BYTES,
        label="derived known-answer fixture",
    )
    _parse_canonical_document(actual, label="derived known-answer fixture")
    if actual != closure.derived_raw:
        _fail("derived known-answer fixture is byte-stale")


def _update_closure(root: Path, closure: _ExpectedClosure) -> None:
    before = _load_protected_inputs(root)
    if not _same_protected_inputs(before, closure.protected):
        _fail("a protected input changed before derived-fixture update")
    _write_exact_derived(root, _DERIVED_FIXTURE_PATH, closure.derived_raw)
    after = _load_protected_inputs(root)
    if not _same_protected_inputs(after, closure.protected):
        _fail("a protected input changed during derived-fixture update")
    _check_closure(root, closure)


def _repository_root() -> Path:
    module_path = Path(__file__).resolve()
    root = module_path.parents[2]
    expected_parent = root / "src" / "sdc"
    if module_path.parent != expected_parent.resolve():
        _fail("codegen module is outside the frozen src/sdc repository layout")
    expected_core = expected_parent / "generated_reference_rights_current_status.py"
    if Path(rights_module.__file__).resolve() != expected_core.resolve():
        _fail("Rights/current-status core does not belong to the same fixed repository layout")
    pyproject = _safe_path(root, "pyproject.toml", label="repository pyproject.toml")
    raw = _read_stable_regular_file(
        pyproject,
        max_bytes=_MAX_REPOSITORY_METADATA_BYTES,
        label="repository pyproject.toml",
    )
    try:
        value = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise GeneratedReferenceRightsCurrentStatusCodegenError(
            "repository pyproject.toml is not strict UTF-8 TOML"
        ) from exc
    project = value.get("project")
    if type(project) is not dict or project.get("name") != "story-to-drama-compiler":
        _fail("repository pyproject.toml has the wrong project identity")
    return root


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -B -m sdc.generated_reference_rights_current_status_codegen",
        description="Check or explicitly update the fixed ADR-044 known-answer fixture.",
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--update", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    root = _repository_root()
    closure = _build_expected_closure(root)
    if args.check:
        _check_closure(root, closure)
    elif args.update:
        _update_closure(root, closure)
    else:  # pragma: no cover
        _fail("one explicit codegen mode is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
