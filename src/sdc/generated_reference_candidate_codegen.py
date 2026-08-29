"""Fixed repository-only known-answer closure for the ADR-043 Candidate boundary.

The generator has exactly two explicit modes.  It reads one frozen human-reviewed source
packet and two frozen first-party offline synthetic PNGs, then either checks or directly
rewrites one derived JSON fixture.  It never writes the source packet or either PNG, creates
a directory, performs Provider work, or uses network, credential, clock, entropy, Runtime,
persistence, publication, or asset-promotion facilities.
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
from pathlib import Path
from typing import Never, cast

from pydantic import ValidationError

from sdc import generated_reference_candidate as candidate_module
from sdc.generated_reference_candidate import (
    EVIDENCE_CATEGORY_ORDER,
    QUALIFICATION_GATE_ORDER,
    GeneratedReferenceQualificationEvidenceInput,
    GeneratedReferenceQualificationEvidenceReferenceV1,
    GeneratedReferenceQualificationGateResultV1,
    build_generated_reference_provider_attempt_outcome,
    capture_generated_reference_candidate,
    creative_sample_generated_reference_candidate_projection,
    creative_sample_generated_reference_candidate_qualification_decision_projection,
    creative_sample_generated_reference_candidate_qualification_decision_sha256,
    creative_sample_generated_reference_candidate_qualification_request_projection,
    creative_sample_generated_reference_candidate_qualification_request_sha256,
    creative_sample_generated_reference_candidate_sha256,
    creative_sample_generated_reference_provider_attempt_outcome_projection,
    creative_sample_generated_reference_provider_attempt_outcome_sha256,
    prepare_generated_reference_candidate_qualification_request,
    record_generated_reference_candidate_qualification_decision,
)

_KNOWN_ANSWER_VERSION = "1.0.0"
_FIXTURE_DIRECTORY = "tests/fixtures/visual_prompt_profiles/generated-reference-candidate"
_REVIEWED_SOURCE_PATH = f"{_FIXTURE_DIRECTORY}/reviewed-known-answer-source-v1.json"
_DERIVED_FIXTURE_PATH = f"{_FIXTURE_DIRECTORY}/generated-known-answer-v1.json"
_CHARACTER_PNG_PATH = f"{_FIXTURE_DIRECTORY}/character-reference-synthetic-v1.png"
_SCENE_PNG_PATH = f"{_FIXTURE_DIRECTORY}/scene-reference-synthetic-v1.png"

# These constants freeze human-reviewed inputs.  Ordinary --update cannot change those bytes.
_REVIEWED_SOURCE_RAW_SHA256 = "b385164d9dabd467308250da41166e1a0d47b8cf8504eb15b5644590aa9edb55"
_REVIEWED_SOURCE_SIZE_BYTES = 101_487
_PNG_FINGERPRINTS = {
    _CHARACTER_PNG_PATH: (
        5_841,
        "3c20c94c18fbd72b68a58748bae9aba2daefc6baa38e9fc1c6ab30b40e6f39fc",
    ),
    _SCENE_PNG_PATH: (
        5_754,
        "97019f80b032242f33963836ce661e8761add311cdc7f8bd7b63ac247c0e5574",
    ),
}

_MAX_SOURCE_BYTES = 2_097_152
_MAX_DERIVED_BYTES = 4_194_304
_MAX_PNG_BYTES = 67_108_864
_MAX_REPOSITORY_METADATA_BYTES = 262_144
_MAX_JSON_CONTAINER_DEPTH = 24
_MAX_JSON_CONTAINER_ITEMS = 256
_WINDOWS_REPARSE_POINT_ATTRIBUTE = 0x400
_UTF8_BOM = b"\xef\xbb\xbf"

_CASE_IDS = (
    "character-reference-pass",
    "scene-reference-pass",
)
_CASE_PNG_PATHS = {
    "character-reference-pass": _CHARACTER_PNG_PATH,
    "scene-reference-pass": _SCENE_PNG_PATH,
}
_SOURCE_ROOT_KEYS = ("cases", "known_answer_version")
_SOURCE_CASE_KEYS = (
    "artifact",
    "case_id",
    "decision",
    "decision_at",
    "evidence_documents",
    "gate_results",
    "outcome_projection",
    "png_path",
    "png_sha256",
    "png_size_bytes",
    "preparer_action",
    "preparer_reference",
    "qualification_basis",
    "qualification_issue_codes",
    "qualifier_action",
    "qualifier_reference",
    "requested_at",
    "synthetic_review",
)
_SOURCE_EVIDENCE_KEYS = ("document", "reference")
_SYNTHETIC_REVIEW_KEYS = (
    "construction",
    "description",
    "external_material_used",
    "provider_used",
)
_SYNTHETIC_REVIEW_VALUES = {
    "character-reference-pass": {
        "construction": "FIRST_PARTY_OFFLINE_PROGRAMMATIC_GEOMETRIC_RASTER",
        "description": (
            "Three-panel composite sheet of one fictional geometric character with fixed head, "
            "clothing and scarf colors; only pose and framing vary."
        ),
        "external_material_used": False,
        "provider_used": False,
    },
    "scene-reference-pass": {
        "construction": "FIRST_PARTY_OFFLINE_PROGRAMMATIC_GEOMETRIC_RASTER",
        "description": (
            "Composite sheet of one fictional geometric scene with a consistent skyline, "
            "perspective grid, palette and lighting treatment."
        ),
        "external_material_used": False,
        "provider_used": False,
    },
}
_DERIVED_CASE_KEYS = (
    "artifact",
    "candidate",
    "case_id",
    "provider_attempt_outcome",
    "qualification_decision",
    "qualification_request",
)


class GeneratedReferenceCandidateCodegenError(ValueError):
    """The fixed ADR-043 known-answer closure is missing, stale, unsafe or invalid."""


def _fail(message: str) -> Never:
    raise GeneratedReferenceCandidateCodegenError(message)


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


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _same_file(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _open_read_flags() -> int:
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
    return flags


def _read_stable_regular_file(path: Path, *, max_bytes: int, label: str) -> bytes:
    if type(max_bytes) is not int or max_bytes <= 0:
        _fail(f"{label} has an invalid byte boundary")
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise GeneratedReferenceCandidateCodegenError(f"{label} could not be inspected") from exc
    if not _is_regular_non_symlink(before) or before.st_nlink != 1:
        _fail(f"{label} must be one regular non-symlink file with one link")
    if not 0 <= before.st_size <= max_bytes:
        _fail(f"{label} exceeds its byte boundary")
    descriptor: int | None = None
    try:
        descriptor = os.open(path, _open_read_flags())
        opened = os.fstat(descriptor)
        if (
            not _is_regular_non_symlink(opened)
            or opened.st_nlink != 1
            or not _same_file(before, opened)
        ):
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
                _fail(f"{label} exceeds its byte boundary")
        after_handle = os.fstat(descriptor)
    except GeneratedReferenceCandidateCodegenError:
        raise
    except OSError as exc:
        raise GeneratedReferenceCandidateCodegenError(f"{label} could not be read") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        after_path = os.lstat(path)
    except OSError as exc:
        raise GeneratedReferenceCandidateCodegenError(f"{label} could not be re-inspected") from exc
    if (
        not _is_regular_non_symlink(after_path)
        or after_path.st_nlink != 1
        or _file_identity(before) != _file_identity(after_handle)
        or _file_identity(before) != _file_identity(after_path)
    ):
        _fail(f"{label} changed while it was read")
    raw = b"".join(chunks)
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
        array_items = cast(list[object], value)
        if len(array_items) > _MAX_JSON_CONTAINER_ITEMS:
            _fail("persistent JSON array exceeds the frozen item boundary")
        for item in array_items:
            _validate_json_value(
                item,
                depth=depth + 1 if type(item) in {dict, list} else depth,
            )
        return
    if type(value) is dict:
        object_items = cast(dict[object, object], value)
        if len(object_items) > _MAX_JSON_CONTAINER_ITEMS:
            _fail("persistent JSON object exceeds the frozen field boundary")
        for key, item in object_items.items():
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
        raise GeneratedReferenceCandidateCodegenError(
            "persistent JSON serialization failed"
        ) from exc


def _parse_canonical_document(raw: bytes, *, label: str) -> dict[str, object]:
    if not raw or raw.startswith(_UTF8_BOM) or b"\r" in raw:
        _fail(f"{label} must use nonempty UTF-8, LF-only, no-BOM bytes")
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail(f"{label} must end with exactly one LF")
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GeneratedReferenceCandidateCodegenError(f"{label} is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        _fail(f"{label} must have an object root")
    _validate_json_value(value)
    if _canonical_document_bytes(value) != raw:
        _fail(f"{label} is not the frozen persistent canonical JSON document")
    return cast(dict[str, object], value)


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
        raise GeneratedReferenceCandidateCodegenError(
            "compact canonical JSON serialization failed"
        ) from exc


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


def _validate_source_document(value: dict[str, object]) -> tuple[dict[str, object], ...]:
    if tuple(value) != _SOURCE_ROOT_KEYS:
        _fail("reviewed source root keys are not the frozen exact set")
    if value["known_answer_version"] != _KNOWN_ANSWER_VERSION:
        _fail("reviewed source known_answer_version is not frozen")
    raw_cases = value["cases"]
    if type(raw_cases) is not list:
        _fail("reviewed source cases must be one JSON array")
    cases = tuple(cast(list[object], raw_cases))
    if len(cases) != len(_CASE_IDS):
        _fail("reviewed source must contain exactly two cases")
    validated: list[dict[str, object]] = []
    for expected_id, raw_case in zip(_CASE_IDS, cases, strict=True):
        if type(raw_case) is not dict:
            _fail("each reviewed source case must be one object")
        case = cast(dict[str, object], raw_case)
        if tuple(case) != _SOURCE_CASE_KEYS or case.get("case_id") != expected_id:
            _fail("reviewed source case keys or order are not frozen")
        expected_png_path = _CASE_PNG_PATHS[expected_id]
        expected_size, expected_sha = _PNG_FINGERPRINTS[expected_png_path]
        if (
            case["png_path"] != expected_png_path
            or case["png_size_bytes"] != expected_size
            or case["png_sha256"] != expected_sha
        ):
            _fail("reviewed source PNG identity is not the frozen exact value")
        review = case["synthetic_review"]
        if type(review) is not dict or tuple(review) != _SYNTHETIC_REVIEW_KEYS:
            _fail("reviewed synthetic-media declaration keys are not frozen")
        if not _json_tree_exactly_equal(review, _SYNTHETIC_REVIEW_VALUES[expected_id]):
            _fail("reviewed synthetic-media declaration values are not frozen")
        for key in (
            "artifact",
            "outcome_projection",
            "preparer_action",
            "preparer_reference",
            "qualifier_action",
            "qualifier_reference",
        ):
            if type(case[key]) is not dict:
                _fail(f"reviewed source {key} must be one complete object")
        evidence_values = case["evidence_documents"]
        if type(evidence_values) is not list or len(evidence_values) != 10:
            _fail("reviewed source must contain exactly ten evidence documents")
        categories: list[object] = []
        for evidence_value in evidence_values:
            if type(evidence_value) is not dict:
                _fail("each reviewed evidence input must be one object")
            evidence = cast(dict[str, object], evidence_value)
            if tuple(evidence) != _SOURCE_EVIDENCE_KEYS:
                _fail("reviewed evidence input keys are not frozen")
            if type(evidence["document"]) is not dict or type(evidence["reference"]) is not dict:
                _fail(
                    "reviewed evidence input must contain complete document and reference objects"
                )
            categories.append(cast(dict[str, object], evidence["reference"]).get("category"))
        if tuple(categories) != tuple(EVIDENCE_CATEGORY_ORDER):
            _fail("reviewed evidence inputs are not in frozen category order")
        gate_values = case["gate_results"]
        if type(gate_values) is not list or len(gate_values) != 15:
            _fail("reviewed source must contain exactly fifteen Gate Results")
        if tuple(
            cast(dict[str, object], item).get("gate") for item in gate_values if type(item) is dict
        ) != tuple(QUALIFICATION_GATE_ORDER):
            _fail("reviewed Gate Results are not in frozen policy order")
        if type(case["qualification_issue_codes"]) is not list:
            _fail("reviewed qualification_issue_codes must be one JSON array")
        if case["qualification_issue_codes"] != [] or case["decision"] != (
            "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW"
        ):
            _fail("reviewed pass cases must use the exact positive Decision mapping")
        validated.append(case)
    return tuple(validated)


@dataclass(frozen=True, slots=True)
class _ProtectedInputs:
    source_raw: bytes
    source_value: dict[str, object]
    png_raw_by_path: dict[str, bytes]


@dataclass(frozen=True, slots=True)
class _ExpectedClosure:
    protected: _ProtectedInputs
    derived_value: dict[str, object]
    derived_raw: bytes


def _load_reviewed_source(root: Path) -> tuple[bytes, dict[str, object]]:
    source_path = _assert_safe_fixture_path(
        root,
        _REVIEWED_SOURCE_PATH,
        label="reviewed known-answer source",
    )
    raw = _read_stable_regular_file(
        source_path,
        max_bytes=_MAX_SOURCE_BYTES,
        label="reviewed known-answer source",
    )
    _assert_safe_fixture_path(
        root,
        _REVIEWED_SOURCE_PATH,
        label="reviewed known-answer source",
    )
    if len(raw) != _REVIEWED_SOURCE_SIZE_BYTES:
        _fail("reviewed known-answer source byte size does not match its frozen constant")
    if hashlib.sha256(raw).hexdigest() != _REVIEWED_SOURCE_RAW_SHA256:
        _fail("reviewed known-answer source SHA-256 does not match its frozen constant")
    value = _parse_canonical_document(raw, label="reviewed known-answer source")
    _validate_source_document(value)
    return raw, value


def _load_png(root: Path, relative_path: str) -> bytes:
    expected_size, expected_sha = _PNG_FINGERPRINTS[relative_path]
    png_path = _assert_safe_fixture_path(root, relative_path, label="synthetic PNG")
    raw = _read_stable_regular_file(
        png_path,
        max_bytes=_MAX_PNG_BYTES,
        label="synthetic PNG",
    )
    _assert_safe_fixture_path(root, relative_path, label="synthetic PNG")
    if len(raw) != expected_size:
        _fail("synthetic PNG byte size does not match its frozen constant")
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        _fail("synthetic PNG SHA-256 does not match its frozen constant")
    return raw


def _load_protected_inputs(root: Path) -> _ProtectedInputs:
    source_raw, source_value = _load_reviewed_source(root)
    png_raw_by_path = {path: _load_png(root, path) for path in _PNG_FINGERPRINTS}
    return _ProtectedInputs(
        source_raw=source_raw,
        source_value=source_value,
        png_raw_by_path=png_raw_by_path,
    )


def _build_evidence_inputs(
    values: object,
) -> tuple[GeneratedReferenceQualificationEvidenceInput, ...]:
    if type(values) is not list:
        _fail("reviewed evidence inputs must be one JSON array")
    inputs: list[GeneratedReferenceQualificationEvidenceInput] = []
    for value in cast(list[object], values):
        evidence = cast(dict[str, object], value)
        reference_value = cast(dict[str, object], evidence["reference"])
        document_bytes = _canonical_document_bytes(evidence["document"])
        if (
            reference_value.get("document_size_bytes") != len(document_bytes)
            or reference_value.get("document_sha256") != hashlib.sha256(document_bytes).hexdigest()
        ):
            _fail("reviewed evidence reference does not bind its exact retained document bytes")
        reference = GeneratedReferenceQualificationEvidenceReferenceV1.model_validate_json(
            _canonical_document_bytes(reference_value),
            strict=True,
        )
        inputs.append(
            GeneratedReferenceQualificationEvidenceInput(
                reference=reference,
                document_bytes=document_bytes,
            )
        )
    return tuple(inputs)


def _build_expected_derived_value(root: Path, source_value: dict[str, object]) -> dict[str, object]:
    cases = _validate_source_document(source_value)
    derived_cases: list[dict[str, object]] = []
    for case in cases:
        case_id = cast(str, case["case_id"])
        png_path = root / cast(str, case["png_path"])
        try:
            artifact_model = candidate_module.__dict__[
                "CreativeSampleReferenceVisualPromptArtifactV1"
            ]
            artifact_projection = candidate_module.__dict__[
                "creative_sample_reference_visual_prompt_artifact_projection"
            ]
            artifact_sha256 = candidate_module.__dict__[
                "creative_sample_reference_visual_prompt_artifact_sha256"
            ]
            artifact = artifact_model.model_validate_json(
                _compact_json(case["artifact"]), strict=True
            )
            if (
                artifact_projection(artifact)
                != {
                    key: value
                    for key, value in cast(dict[str, object], case["artifact"]).items()
                    if key not in {"artifact_id", "artifact_sha256"}
                }
                or artifact_sha256(artifact) != artifact.artifact_sha256
            ):
                _fail("reviewed Artifact identity is not self-consistent")
            outcome = build_generated_reference_provider_attempt_outcome(
                cast(dict[str, object], case["outcome_projection"])
            )
            if (
                creative_sample_generated_reference_provider_attempt_outcome_projection(outcome)
                != case["outcome_projection"]
                or creative_sample_generated_reference_provider_attempt_outcome_sha256(outcome)
                != outcome.outcome_sha256
            ):
                _fail("reviewed Outcome projection is not self-consistent")
            candidate = capture_generated_reference_candidate(
                artifact,
                outcome,
                png_path=png_path,
            )
            if (
                creative_sample_generated_reference_candidate_projection(candidate)
                != {
                    key: value
                    for key, value in candidate.model_dump(mode="json").items()
                    if key not in {"candidate_id", "candidate_sha256"}
                }
                or creative_sample_generated_reference_candidate_sha256(candidate)
                != candidate.candidate_sha256
            ):
                _fail("derived Candidate identity is not self-consistent")
            evidence_inputs = _build_evidence_inputs(case["evidence_documents"])
            request = prepare_generated_reference_candidate_qualification_request(
                artifact,
                outcome,
                candidate,
                png_path=png_path,
                evidence_documents=evidence_inputs,
                preparer_reference_bytes=_canonical_document_bytes(case["preparer_reference"]),
                preparer_action_bytes=_canonical_document_bytes(case["preparer_action"]),
                requested_at=cast(str, case["requested_at"]),
            )
            if (
                creative_sample_generated_reference_candidate_qualification_request_projection(
                    request
                )
                != {
                    key: value
                    for key, value in request.model_dump(mode="json").items()
                    if key not in {"request_id", "request_sha256"}
                }
                or creative_sample_generated_reference_candidate_qualification_request_sha256(
                    request
                )
                != request.request_sha256
            ):
                _fail("derived Qualification Request identity is not self-consistent")
            gate_results = tuple(
                GeneratedReferenceQualificationGateResultV1.model_validate_json(
                    _canonical_document_bytes(value),
                    strict=True,
                )
                for value in cast(list[object], case["gate_results"])
            )
            decision = record_generated_reference_candidate_qualification_decision(
                artifact,
                outcome,
                candidate,
                request,
                png_path=png_path,
                evidence_documents=evidence_inputs,
                preparer_reference_bytes=_canonical_document_bytes(case["preparer_reference"]),
                preparer_action_bytes=_canonical_document_bytes(case["preparer_action"]),
                qualifier_reference_bytes=_canonical_document_bytes(case["qualifier_reference"]),
                qualifier_action_bytes=_canonical_document_bytes(case["qualifier_action"]),
                decision_at=cast(str, case["decision_at"]),
                gate_results=gate_results,
                qualification_issue_codes=(),
                qualification_basis=cast(str, case["qualification_basis"]),
                decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
            )
            if (
                creative_sample_generated_reference_candidate_qualification_decision_projection(
                    decision
                )
                != {
                    key: value
                    for key, value in decision.model_dump(mode="json").items()
                    if key not in {"decision_id", "decision_sha256"}
                }
                or creative_sample_generated_reference_candidate_qualification_decision_sha256(
                    decision
                )
                != decision.decision_sha256
            ):
                _fail("derived Qualification Decision identity is not self-consistent")
        except GeneratedReferenceCandidateCodegenError:
            raise
        except (ValidationError, OSError, TypeError, ValueError, RecursionError) as exc:
            raise GeneratedReferenceCandidateCodegenError(
                f"reviewed source case failed deterministic closure: {case_id}"
            ) from exc
        derived_case: dict[str, object] = {
            "artifact": artifact.model_dump(mode="json"),
            "candidate": candidate.model_dump(mode="json"),
            "case_id": case_id,
            "provider_attempt_outcome": outcome.model_dump(mode="json"),
            "qualification_decision": decision.model_dump(mode="json"),
            "qualification_request": request.model_dump(mode="json"),
        }
        if tuple(derived_case) != _DERIVED_CASE_KEYS:
            _fail("internal derived case keys drifted")
        derived_cases.append(derived_case)
    return {"cases": derived_cases, "known_answer_version": _KNOWN_ANSWER_VERSION}


def _build_expected_closure(root: Path) -> _ExpectedClosure:
    _assert_fixed_paths()
    protected = _load_protected_inputs(root)
    derived_value = _build_expected_derived_value(root, protected.source_value)
    derived_raw = _canonical_document_bytes(derived_value)
    if len(derived_raw) > _MAX_DERIVED_BYTES:
        _fail("derived known-answer fixture exceeds its byte boundary")
    return _ExpectedClosure(
        protected=protected,
        derived_value=derived_value,
        derived_raw=derived_raw,
    )


def _assert_fixed_paths() -> None:
    paths = (
        _REVIEWED_SOURCE_PATH,
        _DERIVED_FIXTURE_PATH,
        _CHARACTER_PNG_PATH,
        _SCENE_PNG_PATH,
    )
    if len(set(paths)) != 4:
        _fail("source, derived and PNG fixture paths must be distinct")
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
        if path.parent != Path(_FIXTURE_DIRECTORY):
            _fail("all generated-reference fixtures must share the frozen directory")


def _assert_parent_directory(path: Path) -> None:
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise GeneratedReferenceCandidateCodegenError(
            "derived fixture parent directory is missing or inaccessible"
        ) from exc
    if not _is_directory_non_symlink(info):
        _fail("derived fixture parent must be one regular non-symlink directory")


def _assert_safe_fixture_path(root: Path, relative_path: str, *, label: str) -> Path:
    if not root.is_absolute():
        _fail(f"{label} repository root must be absolute")
    current = root
    for part in ("", *Path(relative_path).parts[:-1]):
        if part:
            current /= part
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise GeneratedReferenceCandidateCodegenError(
                f"{label} ancestor is missing or inaccessible"
            ) from exc
        if not _is_directory_non_symlink(info):
            _fail(f"{label} ancestors must be regular non-symlink directories")
    return root / relative_path


def _protected_file_infos(root: Path) -> tuple[os.stat_result, ...]:
    infos: list[os.stat_result] = []
    for relative_path in (_REVIEWED_SOURCE_PATH, *_PNG_FINGERPRINTS):
        path = _assert_safe_fixture_path(root, relative_path, label="protected input")
        try:
            info = os.lstat(path)
        except OSError as exc:
            raise GeneratedReferenceCandidateCodegenError(
                "protected input could not be inspected before update"
            ) from exc
        if not _is_regular_non_symlink(info) or info.st_nlink != 1:
            _fail("protected input must remain one regular non-symlink file with one link")
        infos.append(info)
    return tuple(infos)


def _write_exact_derived(root: Path, relative_path: str, raw: bytes) -> None:
    if relative_path != _DERIVED_FIXTURE_PATH:
        _fail("update attempted to write outside the single fixed derived-fixture allowlist")
    destination = _assert_safe_fixture_path(
        root,
        relative_path,
        label="derived known-answer fixture",
    )
    _assert_parent_directory(destination.parent)
    protected_infos = _protected_file_infos(root)
    try:
        destination_before = os.lstat(destination)
    except FileNotFoundError:
        destination_before = None
    except OSError as exc:
        raise GeneratedReferenceCandidateCodegenError(
            "derived fixture destination could not be inspected"
        ) from exc
    if destination_before is not None:
        if not _is_regular_non_symlink(destination_before) or destination_before.st_nlink != 1:
            _fail("derived fixture destination must be one regular non-symlink file")
        if any(_same_file(info, destination_before) for info in protected_infos):
            _fail("derived fixture destination must not alias a protected input")
    flags = os.O_WRONLY
    if destination_before is None:
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
        if destination_before is not None and not _same_file(destination_before, opened):
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
    except GeneratedReferenceCandidateCodegenError:
        raise
    except OSError as exc:
        raise GeneratedReferenceCandidateCodegenError(
            "derived fixture could not be written directly"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        after_path = os.lstat(destination)
    except OSError as exc:
        raise GeneratedReferenceCandidateCodegenError(
            "derived fixture could not be re-inspected"
        ) from exc
    if (
        not _is_regular_non_symlink(after_path)
        or after_path.st_nlink != 1
        or not _same_file(after_handle, after_path)
        or after_path.st_size != len(raw)
    ):
        _fail("derived fixture changed while it was written")
    _assert_safe_fixture_path(root, relative_path, label="derived known-answer fixture")
    for protected_path in (_REVIEWED_SOURCE_PATH, *_PNG_FINGERPRINTS):
        _assert_safe_fixture_path(root, protected_path, label="protected input")


def _same_protected_inputs(left: _ProtectedInputs, right: _ProtectedInputs) -> bool:
    return (
        left.source_raw == right.source_raw
        and left.source_value == right.source_value
        and left.png_raw_by_path == right.png_raw_by_path
    )


def _check_closure(root: Path, closure: _ExpectedClosure) -> None:
    derived_path = _assert_safe_fixture_path(
        root,
        _DERIVED_FIXTURE_PATH,
        label="derived known-answer fixture",
    )
    actual = _read_stable_regular_file(
        derived_path,
        max_bytes=_MAX_DERIVED_BYTES,
        label="derived known-answer fixture",
    )
    _assert_safe_fixture_path(
        root,
        _DERIVED_FIXTURE_PATH,
        label="derived known-answer fixture",
    )
    _parse_canonical_document(actual, label="derived known-answer fixture")
    if actual != closure.derived_raw:
        _fail("derived known-answer fixture is byte-stale")


def _update_closure(root: Path, closure: _ExpectedClosure) -> None:
    before = _load_protected_inputs(root)
    if not _same_protected_inputs(before, closure.protected):
        _fail("a protected source or PNG changed before derived-fixture update")
    _write_exact_derived(root, _DERIVED_FIXTURE_PATH, closure.derived_raw)
    after = _load_protected_inputs(root)
    if not _same_protected_inputs(after, closure.protected):
        _fail("a protected source or PNG changed during derived-fixture update")
    _check_closure(root, closure)


def _repository_root() -> Path:
    module_path = Path(__file__).resolve()
    root = module_path.parents[2]
    expected_module_parent = root / "src" / "sdc"
    if module_path.parent != expected_module_parent.resolve():
        _fail("codegen module is outside the frozen src/sdc repository layout")
    expected_candidate_module = expected_module_parent / "generated_reference_candidate.py"
    if Path(candidate_module.__file__).resolve() != expected_candidate_module.resolve():
        _fail("Candidate module does not belong to the same fixed repository layout")
    pyproject_path = _assert_safe_fixture_path(
        root,
        "pyproject.toml",
        label="repository pyproject.toml",
    )
    raw = _read_stable_regular_file(
        pyproject_path,
        max_bytes=_MAX_REPOSITORY_METADATA_BYTES,
        label="repository pyproject.toml",
    )
    try:
        value = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise GeneratedReferenceCandidateCodegenError(
            "repository pyproject.toml is not strict UTF-8 TOML"
        ) from exc
    project = value.get("project")
    if type(project) is not dict or project.get("name") != "story-to-drama-compiler":
        _fail("repository pyproject.toml has the wrong project identity")
    return root


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m sdc.generated_reference_candidate_codegen",
        description="Check or explicitly update the fixed ADR-043 known-answer fixture.",
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
    else:  # pragma: no cover - argparse makes the modes exhaustive
        _fail("one explicit codegen mode is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
