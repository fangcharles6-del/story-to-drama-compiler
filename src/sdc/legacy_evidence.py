"""Fail-closed import of reviewed legacy Canary evidence into the v1 evidence CAS."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from sdc.contracts import (
    EVIDENCE_MAX_OBJECT_BYTES,
    EvidenceAcquisition,
    EvidenceBundle,
    EvidenceBundleContent,
    EvidenceCapture,
    EvidenceMember,
    EvidenceObject,
    ProviderCapabilitySnapshot,
    ProviderPricingSnapshot,
    evidence_bundle_content_sha256,
    evidence_logical_tree_sha256,
)
from sdc.evidence import EvidenceBundleError, EvidenceBundleReader

_MAX_JSON_BYTES = 4 * 1024 * 1024
_MAX_ARCHIVE_FILES = 4096
_MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
_TREE_ALGORITHM = "compact-json-array-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_R3_CANONICAL_INDEX_SHA256 = "9fee187499617e880fbb0d07191ee315efa6ec3a095b06c5aadb7293b0538591"

_COMMON_PDFS = frozenset(
    {
        "evidence/01-capability-evidence.pdf",
        "evidence/02-pricing-evidence.pdf",
        "evidence/03-create-task-api-evidence.pdf",
        "evidence/04-api-content-contract-evidence.pdf",
    }
)
_R2_R5_RAW = frozenset(
    {
        "evidence/raw/01-capability-row.jpg",
        "evidence/raw/01-capability-update-time.jpg",
        "evidence/raw/02-pricing-formula.jpg",
        "evidence/raw/02-pricing-token-row.jpg",
        "evidence/raw/02-pricing-update-time.jpg",
        "evidence/raw/03-api-async.jpg",
        "evidence/raw/03-api-audio.jpg",
        "evidence/raw/03-api-content-definition.jpg",
        "evidence/raw/03-api-duration.jpg",
        "evidence/raw/03-api-endpoint.jpg",
        "evidence/raw/03-api-ratio.jpg",
        "evidence/raw/03-api-resolution.jpg",
        "evidence/raw/03-api-text-to-video-example.png",
        "evidence/raw/03-api-text-type-fields.jpg",
        "evidence/raw/03-api-update-time.jpg",
    }
)
_R4_R5_EXTRA_MEDIA = frozenset(
    {
        "evidence/05-entitlement-and-usage-evidence.pdf",
        "evidence/raw/05-exact-model-id.png",
        "evidence/raw/05-service-enabled-status.png",
        "evidence/raw/06-usage-range-summary.png",
        "evidence/raw/06-usage-zero.png",
    }
)
_R6_MEDIA = frozenset(
    {
        *_COMMON_PDFS,
        "evidence/05-entitlement-evidence.pdf",
        "evidence/raw/01-capability-row.png",
        "evidence/raw/01-capability-update-time.png",
        "evidence/raw/02-pricing-formula.png",
        "evidence/raw/02-pricing-token-row.png",
        "evidence/raw/02-pricing-update-time.png",
        "evidence/raw/03-api-async.png",
        "evidence/raw/03-api-audio.png",
        "evidence/raw/03-api-content-definition.png",
        "evidence/raw/03-api-duration.png",
        "evidence/raw/03-api-endpoint.png",
        "evidence/raw/03-api-ratio.png",
        "evidence/raw/03-api-resolution.png",
        "evidence/raw/03-api-text-field.png",
        "evidence/raw/03-api-type-field.png",
        "evidence/raw/03-api-update-time.png",
        "evidence/raw/05-exact-model-id.png",
        "evidence/raw/05-service-enabled-status.png",
    }
)
_BASE_JSON = frozenset({"capability.json", "pricing.json"})
_CONTINUITY_JSON = frozenset({"entitlement-continuity.json", "telemetry-continuity.json"})
_R4_OBSERVATION_JSON = frozenset({"entitlement-observation.json", "telemetry-observation.json"})
_RUN_CORE_PATHS = frozenset(
    {
        "story.json",
        "request-frozen.json",
        "execution.json",
        "plan.json",
        "validation/test_ark_provider.py",
    }
)
_R5_R6_REVIEW_PATHS = frozenset(
    {
        "historical-activation-provenance.json",
        "local-evidence-review.json",
        "offline-boundary-observation.json",
        "validation-results.json",
    }
)
_FORBIDDEN_PATH_PARTS = (
    "authorization",
    "api-key",
    "apikey",
    "credential",
    "cookie",
    "session-token",
    "provider-response",
    "provider-result",
    "task-id",
)
_FORBIDDEN_SUFFIXES = {
    ".env",
    ".har",
    ".key",
    ".log",
    ".m4a",
    ".mov",
    ".mp3",
    ".mp4",
    ".p12",
    ".pem",
    ".pfx",
    ".sqlite",
    ".sqlite3",
    ".wav",
    ".webm",
}


class LegacyEvidenceError(EvidenceBundleError):
    """Raised when a legacy archive or import fails closed."""


class LegacyVerificationLevel(StrEnum):
    FULL_DESCRIPTOR_TREE = "FULL_DESCRIPTOR_TREE"
    CHAIN_COMPAT = "CHAIN_COMPAT"
    SELF_CONSISTENT_UNANCHORED = "SELF_CONSISTENT_UNANCHORED"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True, slots=True)
class LegacySuccessorAnchor:
    source_root: Path
    index_path: Path
    expected_index_sha256: str


@dataclass(frozen=True, slots=True)
class LegacyFileDescriptor:
    relative_path: str
    size_bytes: int
    sha256: str
    byte_verified: bool


@dataclass(frozen=True, slots=True)
class LegacyVerificationReport:
    source_root: Path
    index_path: Path
    expected_index_sha256: str | None
    outer_index_sha256: str
    round: str
    level: LegacyVerificationLevel
    file_count: int
    tree_algorithm: str | None
    tree_sha256: str
    manifest_sha256: str
    freeze_report_sha256: str
    files: tuple[LegacyFileDescriptor, ...]
    successor_anchor: LegacySuccessorAnchor | None = None


@dataclass(frozen=True, slots=True)
class LegacyImportResult:
    bundle: EvidenceBundle
    verification_level: LegacyVerificationLevel
    objects_written: int
    objects_reused: int
    manifest_created: bool
    object_root: Path
    manifest_path: Path


@dataclass(frozen=True, slots=True)
class _LegacyProfile:
    round: str
    directory_name: str
    media_paths: frozenset[str]
    json_paths: frozenset[str]
    declared_paths: frozenset[str]
    source_kinds: frozenset[str]
    source_evidence_paths: tuple[tuple[str, str], ...]

    @property
    def admitted_paths(self) -> frozenset[str]:
        return self.media_paths | self.json_paths

    @property
    def source_path_by_kind(self) -> dict[str, str]:
        return dict(self.source_evidence_paths)


@dataclass(frozen=True, slots=True)
class _LegacyDeclaration:
    relative_path: str
    size_bytes: int
    sha256: str
    media_type: str
    content_schema_version: str | None


@dataclass(frozen=True, slots=True)
class _ImportPlan:
    bundle: EvidenceBundle
    declarations: tuple[_LegacyDeclaration, ...]
    generated_objects: tuple[tuple[str, bytes], ...]


_PROFILES = {
    "V02-R2": _LegacyProfile(
        round="V02-R2",
        directory_name="v02-r2",
        media_paths=_COMMON_PDFS | _R2_R5_RAW,
        json_paths=_BASE_JSON,
        declared_paths=(
            _COMMON_PDFS
            | _R2_R5_RAW
            | _BASE_JSON
            | _RUN_CORE_PATHS
            | {"validation/ark-wire-golden-test.patch"}
        ),
        source_kinds=frozenset(
            {"capability", "pricing", "create_task_api", "create_task_content_contract"}
        ),
        source_evidence_paths=(
            ("capability", "evidence/01-capability-evidence.pdf"),
            ("pricing", "evidence/02-pricing-evidence.pdf"),
            ("create_task_api", "evidence/03-create-task-api-evidence.pdf"),
            (
                "create_task_content_contract",
                "evidence/04-api-content-contract-evidence.pdf",
            ),
        ),
    ),
    "V02-R3": _LegacyProfile(
        round="V02-R3",
        directory_name="v02-r3",
        media_paths=_COMMON_PDFS | _R2_R5_RAW,
        json_paths=_BASE_JSON,
        declared_paths=_COMMON_PDFS | _R2_R5_RAW | _BASE_JSON | _RUN_CORE_PATHS,
        source_kinds=frozenset(
            {"capability", "pricing", "create_task_api", "create_task_content_contract"}
        ),
        source_evidence_paths=(
            ("capability", "evidence/01-capability-evidence.pdf"),
            ("pricing", "evidence/02-pricing-evidence.pdf"),
            ("create_task_api", "evidence/03-create-task-api-evidence.pdf"),
            (
                "create_task_content_contract",
                "evidence/04-api-content-contract-evidence.pdf",
            ),
        ),
    ),
    "V02-R4": _LegacyProfile(
        round="V02-R4",
        directory_name="v02-r4",
        media_paths=_COMMON_PDFS | _R2_R5_RAW | _R4_R5_EXTRA_MEDIA,
        json_paths=_BASE_JSON | _R4_OBSERVATION_JSON,
        declared_paths=(
            _COMMON_PDFS
            | _R2_R5_RAW
            | _R4_R5_EXTRA_MEDIA
            | _BASE_JSON
            | _R4_OBSERVATION_JSON
            | _RUN_CORE_PATHS
            | {"activation-operation-trace.json", "activation-review.json"}
        ),
        source_kinds=frozenset(
            {"capability", "pricing", "create_task_api", "create_task_content_contract"}
        ),
        source_evidence_paths=(
            ("capability", "evidence/01-capability-evidence.pdf"),
            ("pricing", "evidence/02-pricing-evidence.pdf"),
            ("create_task_api", "evidence/03-create-task-api-evidence.pdf"),
            (
                "create_task_content_contract",
                "evidence/04-api-content-contract-evidence.pdf",
            ),
        ),
    ),
    "V02-R5": _LegacyProfile(
        round="V02-R5",
        directory_name="v02-r5",
        media_paths=_COMMON_PDFS | _R2_R5_RAW | _R4_R5_EXTRA_MEDIA,
        json_paths=_BASE_JSON | _CONTINUITY_JSON,
        declared_paths=(
            _COMMON_PDFS
            | _R2_R5_RAW
            | _R4_R5_EXTRA_MEDIA
            | _BASE_JSON
            | _CONTINUITY_JSON
            | _RUN_CORE_PATHS
            | _R5_R6_REVIEW_PATHS
        ),
        source_kinds=frozenset(
            {"capability", "pricing", "create_task_api", "create_task_content_contract"}
        ),
        source_evidence_paths=(
            ("capability", "evidence/01-capability-evidence.pdf"),
            ("pricing", "evidence/02-pricing-evidence.pdf"),
            ("create_task_api", "evidence/03-create-task-api-evidence.pdf"),
            (
                "create_task_content_contract",
                "evidence/04-api-content-contract-evidence.pdf",
            ),
        ),
    ),
    "V02-R6": _LegacyProfile(
        round="V02-R6",
        directory_name="v02-r6",
        media_paths=_R6_MEDIA,
        json_paths=_BASE_JSON | _CONTINUITY_JSON,
        declared_paths=(
            _R6_MEDIA | _BASE_JSON | _CONTINUITY_JSON | _RUN_CORE_PATHS | _R5_R6_REVIEW_PATHS
        ),
        source_kinds=frozenset(
            {
                "capability",
                "pricing",
                "create_task_api",
                "create_task_content_contract",
                "entitlement",
            }
        ),
        source_evidence_paths=(
            ("capability", "evidence/01-capability-evidence.pdf"),
            ("pricing", "evidence/02-pricing-evidence.pdf"),
            ("create_task_api", "evidence/03-create-task-api-evidence.pdf"),
            (
                "create_task_content_contract",
                "evidence/04-api-content-contract-evidence.pdf",
            ),
            ("entitlement", "evidence/05-entitlement-evidence.pdf"),
        ),
    ),
}
_PROFILE_BY_DIRECTORY = {
    profile.directory_name.casefold(): profile for profile in _PROFILES.values()
}
_PROTECTED_ARCHIVE_DIRECTORY_NAMES = frozenset(
    {"canary", *(profile.directory_name.casefold() for profile in _PROFILES.values())}
)


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LegacyEvidenceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _is_link_like(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        attributes = 0
    return (
        path.is_symlink()
        or bool(is_junction is not None and is_junction())
        or bool(attributes & reparse_flag)
    )


def _lstat_no_link(path: Path, label: str) -> os.stat_result | None:
    """Inspect one lexical path component without following a reparse target."""
    try:
        value = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LegacyEvidenceError(f"{label} could not be inspected") from exc
    is_junction = getattr(path, "is_junction", None)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    attributes = getattr(value, "st_file_attributes", 0)
    if (
        stat.S_ISLNK(value.st_mode)
        or bool(is_junction is not None and is_junction())
        or bool(attributes & reparse_flag)
    ):
        raise LegacyEvidenceError(f"{label} contains a link or junction")
    return value


def _require_real_directory(path: Path, label: str) -> None:
    """Reject a missing, non-directory, or link-like source path and its ancestors."""
    for position, component in enumerate((path, *path.parents)):
        value = _lstat_no_link(component, label)
        if value is None:
            raise LegacyEvidenceError(f"{label} must be an existing directory")
        if position == 0 and not stat.S_ISDIR(value.st_mode):
            raise LegacyEvidenceError(f"{label} must be an existing directory")


def _regular_file_under_root(path: Path, trusted_root: Path, label: str) -> os.stat_result:
    try:
        lexical_root = trusted_root.absolute()
        lexical_path = path.absolute()
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise LegacyEvidenceError(f"{label} escapes its trusted root") from exc
    if not relative.parts:
        raise LegacyEvidenceError(f"{label} must name a file below its trusted root")
    _require_real_directory(trusted_root, f"{label} trusted root")
    parent = trusted_root
    for component_name in relative.parts[:-1]:
        parent /= component_name
        value = _lstat_no_link(parent, f"{label} parent")
        if value is None or not stat.S_ISDIR(value.st_mode):
            raise LegacyEvidenceError(f"{label} parent must be a real directory")
    value = _lstat_no_link(path, label)
    if value is None or not stat.S_ISREG(value.st_mode):
        raise LegacyEvidenceError(f"{label} must be a regular file")
    try:
        resolved_root = trusted_root.resolve(strict=True)
        path.resolve(strict=True).relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise LegacyEvidenceError(f"{label} escapes its trusted root") from exc
    return value


def _read_regular_file(
    path: Path,
    *,
    trusted_root: Path,
    max_bytes: int,
    expected_size: int | None = None,
) -> tuple[bytes, str]:
    try:
        label = f"legacy path {path.name}"
        path_before = _regular_file_under_root(path, trusted_root, label)
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise LegacyEvidenceError(f"legacy path must be a regular file: {path.name}")
            if (path_before.st_dev, path_before.st_ino) != (before.st_dev, before.st_ino):
                raise LegacyEvidenceError(f"legacy file changed before being read: {path.name}")
            data = bytearray()
            digest = hashlib.sha256()
            while chunk := handle.read(min(1024 * 1024, max_bytes + 1)):
                data.extend(chunk)
                digest.update(chunk)
                if len(data) > max_bytes or (
                    expected_size is not None and len(data) > expected_size
                ):
                    raise LegacyEvidenceError(f"legacy file exceeds its byte limit: {path.name}")
            after = os.fstat(handle.fileno())
        path_after = _regular_file_under_root(path, trusted_root, label)
        if (
            (path_after.st_dev, path_after.st_ino) != (after.st_dev, after.st_ino)
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_size != len(data)
        ):
            raise LegacyEvidenceError(f"legacy file changed while being read: {path.name}")
        if expected_size is not None and len(data) != expected_size:
            raise LegacyEvidenceError(f"legacy file size mismatch: {path.name}")
        return bytes(data), digest.hexdigest()
    except LegacyEvidenceError:
        raise
    except OSError as exc:
        raise LegacyEvidenceError(f"legacy file could not be read: {path.name}") from exc


def _load_json(
    path: Path, *, trusted_root: Path, expected_sha256: str | None = None
) -> dict[str, Any]:
    raw, digest = _read_regular_file(path, trusted_root=trusted_root, max_bytes=_MAX_JSON_BYTES)
    if expected_sha256 is not None and digest != expected_sha256:
        raise LegacyEvidenceError(f"legacy JSON digest mismatch: {path.name}")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys)
    except LegacyEvidenceError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise LegacyEvidenceError(f"invalid legacy JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise LegacyEvidenceError(f"legacy JSON must contain an object: {path.name}")
    return value


def _required_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise LegacyEvidenceError(f"legacy field must be a non-empty string: {field}")
    return value


def _required_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LegacyEvidenceError(f"legacy field must be a non-negative integer: {field}")
    return int(value)


def _required_sha256(value: Any, field: str) -> str:
    digest = _required_str(value, field)
    if _SHA256_RE.fullmatch(digest) is None:
        raise LegacyEvidenceError(f"legacy field must be a lowercase SHA-256: {field}")
    return digest


def _required_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise LegacyEvidenceError(f"legacy field must be a list: {field}")
    return value


def _required_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LegacyEvidenceError(f"legacy field must be an object: {field}")
    return value


def _parse_datetime(value: Any, field: str) -> datetime:
    raw = _required_str(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LegacyEvidenceError(f"legacy datetime is invalid: {field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LegacyEvidenceError(f"legacy datetime must include a timezone: {field}")
    return parsed.astimezone(UTC)


def _profile_for_round(round_name: str) -> _LegacyProfile:
    try:
        return _PROFILES[round_name]
    except KeyError as exc:
        raise LegacyEvidenceError(f"unsupported legacy round: {round_name}") from exc


def _normalize_declared_path(value: Any, profile: _LegacyProfile) -> str:
    raw = _required_str(value, "declared path")
    prefix = f".artifacts/canary/{profile.directory_name}/"
    if not raw.startswith(prefix):
        raise LegacyEvidenceError("legacy declaration escapes its canonical round prefix")
    relative = raw[len(prefix) :]
    try:
        EvidenceMember(
            logical_path=relative,
            role="legacy",
            object_sha256="0" * 64,
        )
    except ValidationError as exc:
        raise LegacyEvidenceError(f"unsafe legacy path: {raw}") from exc
    return relative


def _declarations(
    manifest: dict[str, Any], profile: _LegacyProfile
) -> dict[str, _LegacyDeclaration]:
    entries = [
        *_required_list(manifest.get("artifacts"), "artifacts"),
        *_required_list(manifest.get("raw_capture_files"), "raw_capture_files"),
    ]
    declarations: dict[str, _LegacyDeclaration] = {}
    casefolded: set[str] = set()
    for position, raw_entry in enumerate(entries):
        entry = _required_mapping(raw_entry, f"declaration[{position}]")
        relative = _normalize_declared_path(entry.get("path"), profile)
        folded = relative.casefold()
        if relative in declarations or folded in casefolded:
            raise LegacyEvidenceError(f"duplicate legacy declaration: {relative}")
        declaration = _LegacyDeclaration(
            relative_path=relative,
            size_bytes=_required_int(entry.get("bytes"), f"{relative}.bytes"),
            sha256=_required_sha256(entry.get("sha256"), f"{relative}.sha256"),
            media_type=_required_str(entry.get("mime_type"), f"{relative}.mime_type"),
            content_schema_version=entry.get("schema_version")
            if isinstance(entry.get("schema_version"), str)
            else None,
        )
        declarations[relative] = declaration
        casefolded.add(folded)

    declared_evidence = frozenset(path for path in declarations if path.startswith("evidence/"))
    if declared_evidence != profile.media_paths:
        raise LegacyEvidenceError("legacy evidence paths do not match the reviewed round profile")
    if frozenset(declarations) != profile.declared_paths:
        raise LegacyEvidenceError("legacy declarations do not match the reviewed round profile")
    missing_json = profile.json_paths - declarations.keys()
    if missing_json:
        raise LegacyEvidenceError("legacy evidence contract paths are missing from the archive")
    return declarations


def _walk_archive(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        root_value = _lstat_no_link(root, "legacy archive root")
        if root_value is None or not stat.S_ISDIR(root_value.st_mode):
            raise LegacyEvidenceError("legacy archive root must be a directory")
        paths: list[str] = []
        directory_paths: list[str] = []
        entry_count = 0

        def fail_walk(error: OSError) -> None:
            raise LegacyEvidenceError("legacy archive could not be enumerated") from error

        for current, directories, filenames in os.walk(root, followlinks=False, onerror=fail_walk):
            current_path = Path(current)
            for name in directories:
                directory = current_path / name
                directory_value = _lstat_no_link(directory, "legacy archive directory")
                if directory_value is None or not stat.S_ISDIR(directory_value.st_mode):
                    raise LegacyEvidenceError("legacy archive contains a linked directory")
                relative_directory = directory.relative_to(root).as_posix()
                try:
                    EvidenceMember(
                        logical_path=relative_directory,
                        role="legacy",
                        object_sha256="0" * 64,
                    )
                except ValidationError as exc:
                    raise LegacyEvidenceError(
                        f"unsafe archive directory: {relative_directory}"
                    ) from exc
                directory_paths.append(relative_directory)
                entry_count += 1
                if entry_count > _MAX_ARCHIVE_FILES:
                    raise LegacyEvidenceError("legacy archive exceeds the entry-count limit")
            for name in filenames:
                candidate = current_path / name
                candidate_value = _lstat_no_link(candidate, "legacy archive file")
                if candidate_value is None:
                    raise LegacyEvidenceError("legacy archive file disappeared during enumeration")
                relative = candidate.relative_to(root).as_posix()
                try:
                    EvidenceMember(
                        logical_path=relative,
                        role="legacy",
                        object_sha256="0" * 64,
                    )
                except ValidationError as exc:
                    raise LegacyEvidenceError(f"unsafe archive path: {relative}") from exc
                paths.append(relative)
                entry_count += 1
                if entry_count > _MAX_ARCHIVE_FILES:
                    raise LegacyEvidenceError("legacy archive exceeds the entry-count limit")
        if len(paths) != len(set(paths)) or len(paths) != len({path.casefold() for path in paths}):
            raise LegacyEvidenceError("legacy archive paths collide")
        if len(directory_paths) != len({path.casefold() for path in directory_paths}):
            raise LegacyEvidenceError("legacy archive directories collide")
        return tuple(sorted(paths)), tuple(sorted(directory_paths))
    except LegacyEvidenceError:
        raise
    except OSError as exc:
        raise LegacyEvidenceError("legacy archive could not be enumerated") from exc


def _reject_forbidden_paths(paths: tuple[str, ...]) -> None:
    for path in paths:
        folded = path.casefold()
        suffix = Path(path).suffix.casefold()
        if any(part in folded for part in _FORBIDDEN_PATH_PARTS) or suffix in _FORBIDDEN_SUFFIXES:
            raise LegacyEvidenceError(f"legacy archive contains a forbidden artifact: {path}")


def _stat_regular_file(path: Path) -> int:
    value = _lstat_no_link(path, f"legacy path {path.name}")
    if value is None or not stat.S_ISREG(value.st_mode):
        raise LegacyEvidenceError(f"legacy path must be a regular file: {path.name}")
    return value.st_size


def _hash_archive(
    root: Path,
    paths: tuple[str, ...],
    declarations: dict[str, _LegacyDeclaration],
    profile: _LegacyProfile,
) -> tuple[tuple[LegacyFileDescriptor, ...], str]:
    descriptors: list[LegacyFileDescriptor] = []
    total = 0
    for relative in paths:
        path = root / Path(relative)
        declaration = declarations.get(relative)
        if relative in {"evidence/manifest.json", "freeze-report.json"}:
            data, digest = _read_regular_file(path, trusted_root=root, max_bytes=_MAX_JSON_BYTES)
            size = len(data)
            byte_verified = True
        elif declaration is None:
            raise LegacyEvidenceError(f"legacy tree contains an undeclared file: {relative}")
        elif relative in profile.admitted_paths:
            data, digest = _read_regular_file(
                path,
                trusted_root=root,
                max_bytes=EVIDENCE_MAX_OBJECT_BYTES,
                expected_size=declaration.size_bytes,
            )
            size = len(data)
            if digest != declaration.sha256:
                raise LegacyEvidenceError(f"legacy declaration digest mismatch: {relative}")
            byte_verified = True
        else:
            size = _stat_regular_file(path)
            if size != declaration.size_bytes:
                raise LegacyEvidenceError(f"legacy declaration size mismatch: {relative}")
            digest = declaration.sha256
            byte_verified = False
        total += size
        if total > _MAX_ARCHIVE_BYTES:
            raise LegacyEvidenceError("legacy archive exceeds the total byte limit")
        descriptors.append(
            LegacyFileDescriptor(
                relative_path=relative,
                size_bytes=size,
                sha256=digest,
                byte_verified=byte_verified,
            )
        )
    rows = [(item.relative_path, item.size_bytes, item.sha256) for item in descriptors]
    tree = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
    return tuple(descriptors), tree


def _validate_source_cross_references(
    manifest: dict[str, Any], profile: _LegacyProfile, declarations: dict[str, _LegacyDeclaration]
) -> None:
    sources = _required_list(manifest.get("sources"), "sources")
    kinds: set[str] = set()
    for position, raw_source in enumerate(sources):
        source = _required_mapping(raw_source, f"sources[{position}]")
        kind = _required_str(source.get("kind"), f"sources[{position}].kind")
        if kind in kinds:
            raise LegacyEvidenceError(f"duplicate legacy source kind: {kind}")
        kinds.add(kind)
        evidence = _required_mapping(source.get("evidence"), f"sources[{position}].evidence")
        relative = _normalize_declared_path(evidence.get("path"), profile)
        if relative != profile.source_path_by_kind.get(kind):
            raise LegacyEvidenceError(
                f"legacy source kind points to the wrong reviewed evidence path: {kind}"
            )
        declaration = declarations.get(relative)
        if declaration is None:
            raise LegacyEvidenceError("legacy source references an undeclared evidence file")
        if (
            declaration.size_bytes != _required_int(evidence.get("bytes"), "source bytes")
            or declaration.sha256 != _required_sha256(evidence.get("sha256"), "source sha256")
            or declaration.media_type != _required_str(evidence.get("mime_type"), "source mime")
        ):
            raise LegacyEvidenceError("legacy source descriptor disagrees with its declaration")
    if kinds != profile.source_kinds:
        raise LegacyEvidenceError("legacy source kinds do not match the reviewed round profile")


def _verify_successor_chain(
    report: LegacyVerificationReport,
    successor: LegacySuccessorAnchor,
) -> None:
    successor_report = verify_legacy_round(
        successor.source_root,
        successor.index_path,
        expected_index_sha256=successor.expected_index_sha256,
    )
    if (
        successor_report.round != "V02-R3"
        or successor_report.level is not LegacyVerificationLevel.CHAIN_COMPAT
    ):
        raise LegacyEvidenceError("R2 requires the canonical verified R3 successor")
    manifest = _load_json(
        successor.source_root / "evidence" / "manifest.json",
        trusted_root=successor.source_root,
        expected_sha256=successor_report.manifest_sha256,
    )
    entries = _required_list(manifest.get("prior_rounds"), "prior_rounds")
    expected_path = ".artifacts/canary/v02-r2"
    matches = [
        _required_mapping(item, "prior_round")
        for item in entries
        if isinstance(item, dict) and item.get("path") == expected_path
    ]
    if len(matches) != 1:
        raise LegacyEvidenceError("R3 does not uniquely anchor the R2 predecessor")
    entry = matches[0]
    integrity = _required_mapping(entry.get("integrity"), "R2 successor integrity")
    if (
        _required_int(integrity.get("file_count"), "R2 successor file_count") != report.file_count
        or _required_sha256(integrity.get("tree_sha256"), "R2 successor tree") != report.tree_sha256
        or _required_sha256(entry.get("manifest_sha256"), "R2 successor manifest")
        != report.manifest_sha256
        or _required_sha256(entry.get("freeze_report_sha256"), "R2 successor report")
        != report.freeze_report_sha256
        or _required_sha256(entry.get("outer_index_sha256"), "R2 successor index")
        != report.outer_index_sha256
    ):
        raise LegacyEvidenceError("R3 predecessor anchor does not match the R2 archive")


def verify_legacy_round(
    source_root: Path,
    index_path: Path,
    *,
    expected_index_sha256: str | None,
    successor_anchor: LegacySuccessorAnchor | None = None,
) -> LegacyVerificationReport:
    """Verify a canonical R2-R6 archive without modifying or materializing it."""
    if expected_index_sha256 is not None and _SHA256_RE.fullmatch(expected_index_sha256) is None:
        raise LegacyEvidenceError("trusted outer-index digest must be lowercase SHA-256")
    if successor_anchor is not None and expected_index_sha256 is None:
        raise LegacyEvidenceError("an unanchored archive cannot use a successor trust chain")

    profile_from_directory = _PROFILE_BY_DIRECTORY.get(source_root.name.casefold())
    if profile_from_directory is None:
        raise LegacyEvidenceError("legacy archive directory is not an admitted R2-R6 round")
    _require_real_directory(source_root, "legacy archive root")
    _require_real_directory(source_root.parent, "legacy archive container")
    expected_index_name = f"{profile_from_directory.directory_name}-index.json"
    if index_path.parent.absolute() != source_root.parent.absolute():
        raise LegacyEvidenceError("legacy outer index must be the round's adjacent index")
    try:
        same_parent = index_path.parent.resolve(strict=True) == source_root.parent.resolve(
            strict=True
        )
    except OSError as exc:
        raise LegacyEvidenceError("legacy archive container could not be resolved") from exc
    if index_path.name.casefold() != expected_index_name.casefold() or not same_parent:
        raise LegacyEvidenceError("legacy outer index must be the round's adjacent index")
    raw_index, actual_index_sha256 = _read_regular_file(
        index_path,
        trusted_root=source_root.parent,
        max_bytes=_MAX_JSON_BYTES,
    )
    if expected_index_sha256 is not None and actual_index_sha256 != expected_index_sha256:
        raise LegacyEvidenceError("legacy outer index does not match its trusted digest")
    try:
        index_value = json.loads(
            raw_index.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys
        )
    except LegacyEvidenceError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise LegacyEvidenceError("invalid legacy outer index") from exc
    index = _required_mapping(index_value, "outer index")
    round_name = _required_str(index.get("round"), "round")
    profile = _profile_for_round(round_name)
    if profile != profile_from_directory:
        raise LegacyEvidenceError("legacy outer index round does not match its directory")
    if source_root.name.casefold() != profile.directory_name.casefold():
        raise LegacyEvidenceError("legacy archive directory does not match its round")
    if successor_anchor is not None:
        if round_name != "V02-R2":
            raise LegacyEvidenceError("only R2 may use the reviewed R3 successor chain")
        if (
            successor_anchor.source_root.name.casefold() != "v02-r3"
            or successor_anchor.index_path.name.casefold() != "v02-r3-index.json"
            or successor_anchor.source_root.parent.absolute() != source_root.parent.absolute()
            or successor_anchor.index_path.parent.absolute() != source_root.parent.absolute()
            or _SHA256_RE.fullmatch(successor_anchor.expected_index_sha256) is None
        ):
            raise LegacyEvidenceError("R2 successor must be the adjacent canonical V02-R3 archive")
        _require_real_directory(successor_anchor.source_root, "legacy successor archive root")
        try:
            same_successor_container = successor_anchor.source_root.parent.resolve(
                strict=True
            ) == source_root.parent.resolve(strict=True)
        except OSError as exc:
            raise LegacyEvidenceError(
                "legacy successor archive container could not be resolved"
            ) from exc
        if not same_successor_container:
            raise LegacyEvidenceError(
                "legacy successor archive must share the canonical Canary container"
            )
    if _required_int(index.get("posts_allowed"), "posts_allowed") != 0:
        raise LegacyEvidenceError("legacy archive carries spend authority")
    if index.get("canonical_live_execution_eligible") is not False:
        raise LegacyEvidenceError("legacy archive is marked live eligible")
    if index.get("authorization_artifact_present") is not False:
        raise LegacyEvidenceError("legacy archive contains an authorization artifact")
    disposition = _required_str(index.get("disposition"), "disposition")
    if not disposition.startswith("FROZEN_NOT_AUTHORIZED"):
        raise LegacyEvidenceError("legacy archive disposition is not archive-only")

    manifest_sha256 = _required_sha256(index.get("manifest_sha256"), "manifest_sha256")
    report_sha256 = _required_sha256(index.get("freeze_report_sha256"), "freeze_report_sha256")
    manifest_path = source_root / "evidence" / "manifest.json"
    report_path = source_root / "freeze-report.json"
    manifest = _load_json(
        manifest_path,
        trusted_root=source_root,
        expected_sha256=manifest_sha256,
    )
    _, actual_report_sha = _read_regular_file(
        report_path,
        trusted_root=source_root,
        max_bytes=_MAX_JSON_BYTES,
    )
    if actual_report_sha != report_sha256:
        raise LegacyEvidenceError("legacy freeze report digest mismatch")
    if _required_str(manifest.get("round"), "manifest.round") != round_name:
        raise LegacyEvidenceError("legacy manifest and index rounds differ")
    declarations = _declarations(manifest, profile)
    _validate_source_cross_references(manifest, profile, declarations)

    paths, directories = _walk_archive(source_root)
    _reject_forbidden_paths(paths)
    expected_paths = set(declarations) | {"evidence/manifest.json", "freeze-report.json"}
    if set(paths) != expected_paths:
        raise LegacyEvidenceError("legacy archive has missing or undeclared files")
    expected_directories = {
        parent.as_posix()
        for path in expected_paths
        for parent in Path(path).parents
        if parent.as_posix() != "."
    }
    if set(directories) != expected_directories:
        raise LegacyEvidenceError("legacy archive has undeclared or missing directories")
    if len(paths) != _required_int(index.get("file_count"), "file_count"):
        raise LegacyEvidenceError("legacy archive file count does not match its index")

    files, tree_sha256 = _hash_archive(
        source_root,
        paths,
        declarations,
        profile,
    )
    descriptor_by_path = {item.relative_path: item for item in files}
    for relative, declaration in declarations.items():
        actual = descriptor_by_path[relative]
        if actual.size_bytes != declaration.size_bytes or actual.sha256 != declaration.sha256:
            raise LegacyEvidenceError(f"legacy declaration digest mismatch: {relative}")

    declared_tree = index.get("tree_sha256")
    declared_algorithm = index.get("tree_algorithm")
    if round_name == "V02-R2":
        if declared_tree is not None or declared_algorithm is not None:
            raise LegacyEvidenceError("R2 unexpectedly claims a standalone tree anchor")
        level = LegacyVerificationLevel.DEGRADED
        tree_algorithm: str | None = None
    else:
        expected_tree = _required_sha256(declared_tree, "tree_sha256")
        if expected_tree != tree_sha256:
            raise LegacyEvidenceError("legacy archive tree digest mismatch")
        if round_name == "V02-R3":
            if declared_algorithm is not None:
                raise LegacyEvidenceError(
                    "R3 compatibility profile unexpectedly declares an algorithm"
                )
            if expected_index_sha256 != _R3_CANONICAL_INDEX_SHA256:
                level = LegacyVerificationLevel.SELF_CONSISTENT_UNANCHORED
            else:
                level = LegacyVerificationLevel.CHAIN_COMPAT
            tree_algorithm = _TREE_ALGORITHM
        else:
            if declared_algorithm != _TREE_ALGORITHM:
                raise LegacyEvidenceError("unknown legacy archive tree algorithm")
            level = (
                LegacyVerificationLevel.FULL_DESCRIPTOR_TREE
                if expected_index_sha256 is not None
                else LegacyVerificationLevel.SELF_CONSISTENT_UNANCHORED
            )
            tree_algorithm = _TREE_ALGORITHM

    report = LegacyVerificationReport(
        source_root=source_root,
        index_path=index_path,
        expected_index_sha256=expected_index_sha256,
        outer_index_sha256=actual_index_sha256,
        round=round_name,
        level=level,
        file_count=len(files),
        tree_algorithm=tree_algorithm,
        tree_sha256=tree_sha256,
        manifest_sha256=manifest_sha256,
        freeze_report_sha256=report_sha256,
        files=files,
        successor_anchor=successor_anchor,
    )
    if round_name == "V02-R2" and successor_anchor is not None:
        _verify_successor_chain(report, successor_anchor)
        report = replace(
            report,
            level=LegacyVerificationLevel.CHAIN_COMPAT,
            tree_algorithm=_TREE_ALGORITHM,
        )
    return report


_CONTENT_CONTRACT_RAW = frozenset(
    {
        "evidence/raw/03-api-content-definition.jpg",
        "evidence/raw/03-api-content-definition.png",
        "evidence/raw/03-api-text-field.png",
        "evidence/raw/03-api-text-to-video-example.png",
        "evidence/raw/03-api-text-type-fields.jpg",
        "evidence/raw/03-api-type-field.png",
    }
)


def _role_for_path(path: str) -> str:
    if path == "capability.json":
        return "capability-snapshot"
    if path == "pricing.json":
        return "pricing-snapshot"
    if path in {"entitlement-continuity.json", "entitlement-observation.json"}:
        return "entitlement-record"
    if path in {"telemetry-continuity.json", "telemetry-observation.json"}:
        return "telemetry-record"
    if path == "evidence/04-api-content-contract-evidence.pdf" or path in _CONTENT_CONTRACT_RAW:
        return "content-contract"
    if path.startswith("evidence/01-") or path.startswith("evidence/raw/01-"):
        return "capability"
    if path.startswith("evidence/02-") or path.startswith("evidence/raw/02-"):
        return "pricing"
    if path.startswith("evidence/03-") or path.startswith("evidence/raw/03-"):
        return "create-task-api"
    if path.startswith("evidence/05-") or path.startswith("evidence/raw/05-"):
        return "entitlement"
    if path.startswith("evidence/raw/06-"):
        return "telemetry"
    raise LegacyEvidenceError(f"legacy path has no reviewed evidence role: {path}")


def _capture_key_for_path(path: str) -> str:
    role = _role_for_path(path)
    return {
        "capability": "capability",
        "capability-snapshot": "capability",
        "pricing": "pricing",
        "pricing-snapshot": "pricing",
        "create-task-api": "create_task_api",
        "content-contract": "create_task_content_contract",
        "entitlement": "entitlement",
        "entitlement-record": "entitlement",
        "telemetry": "telemetry",
        "telemetry-record": "telemetry",
    }[role]


def _validate_json_evidence(path: str, data: bytes) -> None:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys)
    except LegacyEvidenceError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise LegacyEvidenceError(f"invalid admitted JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise LegacyEvidenceError(f"admitted JSON evidence must be an object: {path}")
    try:
        if path == "capability.json":
            ProviderCapabilitySnapshot.model_validate(value)
        elif path == "pricing.json":
            ProviderPricingSnapshot.model_validate(value)
    except ValidationError as exc:
        raise LegacyEvidenceError(f"legacy snapshot contract is invalid: {path}") from exc


def _validate_admitted_payload(declaration: _LegacyDeclaration, data: bytes) -> None:
    path = declaration.relative_path
    expected_media_type: str
    if path.endswith(".pdf"):
        expected_media_type = "application/pdf"
        valid_magic = data.startswith(b"%PDF-")
    elif path.endswith(".png"):
        expected_media_type = "image/png"
        valid_magic = data.startswith(b"\x89PNG\r\n\x1a\n")
    elif path.endswith((".jpg", ".jpeg")):
        expected_media_type = "image/jpeg"
        valid_magic = data.startswith(b"\xff\xd8\xff")
    elif path.endswith(".json"):
        expected_media_type = "application/json"
        valid_magic = True
        _validate_json_evidence(path, data)
    else:
        raise LegacyEvidenceError(f"legacy evidence extension is not admitted: {path}")
    if declaration.media_type != expected_media_type or not valid_magic:
        raise LegacyEvidenceError(f"legacy evidence MIME or magic bytes are invalid: {path}")


def _source_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for position, raw in enumerate(_required_list(manifest.get("sources"), "sources")):
        source = _required_mapping(raw, f"sources[{position}]")
        kind = _required_str(source.get("kind"), f"sources[{position}].kind")
        result[kind] = source
    return result


def _observation_time(section: dict[str, Any], name: str) -> datetime:
    for key in ("observed_at", "historical_observed_at"):
        value = section.get(key)
        if value is not None:
            return _parse_datetime(value, f"{name}.{key}")
    raise LegacyEvidenceError(f"legacy {name} observation has no capture time")


def _build_captures(
    *,
    manifest: dict[str, Any],
    profile: _LegacyProfile,
    report: LegacyVerificationReport,
    members: tuple[EvidenceMember, ...],
) -> tuple[EvidenceCapture, ...]:
    member_groups: dict[str, list[str]] = {}
    for member in members:
        member_groups.setdefault(_capture_key_for_path(member.logical_path), []).append(
            member.logical_path
        )

    sources = _source_map(manifest)
    captures: list[EvidenceCapture] = []
    for kind in sorted(sources):
        source = sources[kind]
        paths = tuple(sorted(member_groups.pop(kind, [])))
        if not paths:
            raise LegacyEvidenceError(f"legacy source has no admitted members: {kind}")
        captured_at = _parse_datetime(source.get("captured_at"), f"sources.{kind}.captured_at")
        valid_until = _parse_datetime(source.get("valid_until"), f"sources.{kind}.valid_until")
        updated_raw = source.get("page_updated_at")
        captures.append(
            EvidenceCapture(
                capture_id=f"{profile.directory_name}.{kind.replace('_', '-')}",
                kind=kind.replace("_", "-"),
                source_url=source.get("canonical_url")
                if isinstance(source.get("canonical_url"), str)
                else None,
                source_updated_at=_parse_datetime(updated_raw, f"sources.{kind}.page_updated_at")
                if updated_raw is not None
                else None,
                captured_at=captured_at,
                valid_until=valid_until,
                acquisition=EvidenceAcquisition.LEGACY_IMPORT,
                origin_anchor_sha256=report.outer_index_sha256,
                origin_valid_until=valid_until,
                member_paths=paths,
            )
        )

    manifest_valid_until = _parse_datetime(manifest.get("valid_until"), "valid_until")
    for kind in ("entitlement", "telemetry"):
        paths = tuple(sorted(member_groups.pop(kind, [])))
        if not paths:
            continue
        section = _required_mapping(manifest.get(kind), kind)
        captured_at = _observation_time(section, kind)
        captures.append(
            EvidenceCapture(
                capture_id=f"{profile.directory_name}.{kind}",
                kind=kind,
                source_url=None,
                source_updated_at=None,
                captured_at=captured_at,
                valid_until=manifest_valid_until,
                acquisition=EvidenceAcquisition.LEGACY_IMPORT,
                origin_anchor_sha256=report.outer_index_sha256,
                origin_valid_until=manifest_valid_until,
                member_paths=paths,
            )
        )
    if member_groups:
        raise LegacyEvidenceError("legacy evidence members were not assigned to a capture")
    return tuple(sorted(captures, key=lambda item: item.capture_id))


def _origin_record(report: LegacyVerificationReport) -> tuple[str, bytes]:
    profile = _profile_for_round(report.round)
    successor: dict[str, str] | None = None
    if report.successor_anchor is not None:
        successor = {
            "round": "V02-R3",
            "outer_index_sha256": report.successor_anchor.expected_index_sha256,
        }
    payload = {
        "document_type": "sdc.legacy-evidence-origin",
        "schema_version": "1.0.0",
        "round": report.round,
        "verification_level": report.level.value,
        "verification_semantics": "descriptor-tree-and-admitted-bytes",
        "outer_index_sha256": report.outer_index_sha256,
        "manifest_sha256": report.manifest_sha256,
        "freeze_report_sha256": report.freeze_report_sha256,
        "file_count": report.file_count,
        "tree_algorithm": report.tree_algorithm,
        "tree_sha256": report.tree_sha256,
        "byte_verified_paths": [item.relative_path for item in report.files if item.byte_verified],
        "descriptor_only_paths": [
            item.relative_path for item in report.files if not item.byte_verified
        ],
        "successor_anchor": successor,
    }
    data = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    return f"provenance/{profile.directory_name}-origin.json", data


def _build_import_plan(report: LegacyVerificationReport) -> _ImportPlan:
    if report.level not in {
        LegacyVerificationLevel.FULL_DESCRIPTOR_TREE,
        LegacyVerificationLevel.CHAIN_COMPAT,
    }:
        raise LegacyEvidenceError("legacy archive is not independently verified for import")
    profile = _profile_for_round(report.round)
    manifest = _load_json(
        report.source_root / "evidence" / "manifest.json",
        trusted_root=report.source_root,
        expected_sha256=report.manifest_sha256,
    )
    declarations_by_path = _declarations(manifest, profile)
    declarations = tuple(declarations_by_path[path] for path in sorted(profile.admitted_paths))
    objects_by_digest: dict[str, EvidenceObject] = {}
    members: list[EvidenceMember] = []
    for declaration in declarations:
        data, digest = _read_regular_file(
            report.source_root / Path(declaration.relative_path),
            trusted_root=report.source_root,
            max_bytes=EVIDENCE_MAX_OBJECT_BYTES,
            expected_size=declaration.size_bytes,
        )
        if digest != declaration.sha256:
            raise LegacyEvidenceError(f"legacy evidence digest drift: {declaration.relative_path}")
        _validate_admitted_payload(declaration, data)
        item = EvidenceObject(
            sha256=declaration.sha256,
            size_bytes=declaration.size_bytes,
            media_type=declaration.media_type,
        )
        existing = objects_by_digest.get(item.sha256)
        if existing is not None and existing != item:
            raise LegacyEvidenceError("legacy object descriptors conflict")
        objects_by_digest[item.sha256] = item
        members.append(
            EvidenceMember(
                logical_path=declaration.relative_path,
                role=_role_for_path(declaration.relative_path),
                object_sha256=declaration.sha256,
                content_schema_version=declaration.content_schema_version,
            )
        )
    ordered_members = tuple(sorted(members, key=lambda item: item.logical_path))
    captures = _build_captures(
        manifest=manifest,
        profile=profile,
        report=report,
        members=ordered_members,
    )
    origin_path, origin_data = _origin_record(report)
    origin_sha256 = hashlib.sha256(origin_data).hexdigest()
    origin_object = EvidenceObject(
        sha256=origin_sha256,
        size_bytes=len(origin_data),
        media_type="application/json",
    )
    existing_origin = objects_by_digest.get(origin_sha256)
    if existing_origin is not None and existing_origin != origin_object:
        raise LegacyEvidenceError("legacy origin record conflicts with an evidence object")
    objects_by_digest[origin_sha256] = origin_object
    members.append(
        EvidenceMember(
            logical_path=origin_path,
            role="legacy-origin-record",
            object_sha256=origin_sha256,
            content_schema_version="1.0.0",
        )
    )
    origin_valid_until = min(item.valid_until for item in captures)
    captures = (
        *captures,
        EvidenceCapture(
            capture_id=f"{profile.directory_name}.legacy-origin",
            kind="legacy-origin",
            source_url=None,
            source_updated_at=None,
            captured_at=max(item.captured_at for item in captures),
            valid_until=origin_valid_until,
            acquisition=EvidenceAcquisition.LEGACY_IMPORT,
            origin_anchor_sha256=report.outer_index_sha256,
            origin_valid_until=origin_valid_until,
            member_paths=(origin_path,),
        ),
    )
    objects = tuple(sorted(objects_by_digest.values(), key=lambda item: item.sha256))
    ordered_members = tuple(sorted(members, key=lambda item: item.logical_path))
    captures = tuple(sorted(captures, key=lambda item: item.capture_id))
    try:
        content = EvidenceBundleContent(
            created_at=max(item.captured_at for item in captures),
            valid_until=min(item.valid_until for item in captures),
            predecessor_bundle_id=None,
            objects=objects,
            members=ordered_members,
            captures=captures,
            resolved_logical_tree_sha256=evidence_logical_tree_sha256(objects, ordered_members),
        )
        bundle = EvidenceBundle(
            bundle_id=evidence_bundle_content_sha256(content),
            content=content,
        )
    except ValidationError as exc:
        raise LegacyEvidenceError("legacy evidence could not form a canonical bundle") from exc
    return _ImportPlan(
        bundle=bundle,
        declarations=declarations,
        generated_objects=((origin_sha256, origin_data),),
    )


def _ensure_real_directory(path: Path, label: str) -> None:
    try:
        missing: list[Path] = []
        cursor = path
        value = _lstat_no_link(cursor, label)
        while value is None:
            missing.append(cursor)
            if cursor.parent == cursor:
                raise LegacyEvidenceError(f"{label} has no existing directory ancestor")
            cursor = cursor.parent
            value = _lstat_no_link(cursor, label)
        for ancestor in cursor.parents:
            if _lstat_no_link(ancestor, label) is None:
                raise LegacyEvidenceError(f"{label} has a missing directory ancestor")
        if not stat.S_ISDIR(value.st_mode):
            raise LegacyEvidenceError(f"{label} parent must be a real directory")
        for component in reversed(missing):
            component.mkdir()
            created = _lstat_no_link(component, label)
            if created is None or not stat.S_ISDIR(created.st_mode):
                raise LegacyEvidenceError(f"{label} must be a real directory")
    except LegacyEvidenceError:
        raise
    except OSError as exc:
        raise LegacyEvidenceError(f"{label} could not be created") from exc


def _validate_output_root_location(source_root: Path, output_root: Path) -> None:
    cursor = output_root
    value = _lstat_no_link(cursor, "legacy import output root")
    while value is None:
        if cursor.parent == cursor:
            raise LegacyEvidenceError(
                "legacy import output root has no existing directory ancestor"
            )
        cursor = cursor.parent
        value = _lstat_no_link(cursor, "legacy import output root")
    for ancestor in cursor.parents:
        if _lstat_no_link(ancestor, "legacy import output root") is None:
            raise LegacyEvidenceError("legacy import output root has a missing directory ancestor")
    if not stat.S_ISDIR(value.st_mode):
        raise LegacyEvidenceError("legacy import output root parent must be a real directory")

    try:
        source_container = source_root.parent.resolve(strict=True)
        candidate = output_root.resolve(strict=False)
    except OSError as exc:
        raise LegacyEvidenceError("legacy source or output root could not be resolved") from exc
    if (
        candidate == source_container
        or source_container in candidate.parents
        or candidate in source_container.parents
    ):
        raise LegacyEvidenceError("output root must not overlap the Canary archive container")
    if any(
        component.casefold() in _PROTECTED_ARCHIVE_DIRECTORY_NAMES
        for component in output_root.absolute().parts
    ):
        raise LegacyEvidenceError("output root must not be inside a canonical Canary archive path")


def _ensure_output_root(source_root: Path, output_root: Path) -> None:
    _validate_output_root_location(source_root, output_root)
    _ensure_real_directory(output_root, "legacy import output root")


def _ensure_child_directory(root: Path, path: Path, label: str) -> None:
    try:
        lexical_root = root.absolute()
        lexical_path = path.absolute()
        lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise LegacyEvidenceError(f"{label} escapes the import output root") from exc
    _ensure_real_directory(path, label)
    try:
        resolved_root = root.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
        resolved_path.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise LegacyEvidenceError(f"{label} escapes the import output root") from exc
    for component in (path, *path.parents):
        if component == root.parent:
            break
        if _lstat_no_link(component, label) is None:
            raise LegacyEvidenceError(f"{label} contains a missing directory component")


def _verify_existing_bytes(path: Path, data: bytes, label: str, *, root: Path) -> None:
    actual, digest = _read_regular_file(
        path,
        trusted_root=root,
        max_bytes=len(data),
        expected_size=len(data),
    )
    if digest != hashlib.sha256(data).hexdigest() or actual != data:
        raise LegacyEvidenceError(f"existing {label} does not match the imported bytes")


def _publish_no_replace(root: Path, path: Path, data: bytes, label: str) -> bool:
    _ensure_child_directory(root, path.parent, f"{label} parent")
    existing = _lstat_no_link(path, label)
    if existing is not None:
        if not stat.S_ISREG(existing.st_mode):
            raise LegacyEvidenceError(f"existing {label} must be a regular file")
        _verify_existing_bytes(path, data, label, root=root)
        return False
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _verify_existing_bytes(temporary, data, f"staged {label}", root=root)
        _ensure_child_directory(root, path.parent, f"{label} parent")
        try:
            os.link(temporary, path)
            created = True
        except FileExistsError:
            _verify_existing_bytes(path, data, label, root=root)
            created = False
        _ensure_child_directory(root, path.parent, f"{label} parent")
        return created
    except LegacyEvidenceError:
        raise
    except OSError as exc:
        raise LegacyEvidenceError(f"{label} could not be published atomically") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _materialize_objects(
    plan: _ImportPlan, *, source_root: Path, output_root: Path, object_root: Path
) -> tuple[int, int]:
    _ensure_child_directory(output_root, object_root, "evidence CAS root")
    declarations_by_digest: dict[str, _LegacyDeclaration] = {}
    for declaration in plan.declarations:
        declarations_by_digest.setdefault(declaration.sha256, declaration)
    generated_by_digest = dict(plan.generated_objects)
    payloads: dict[str, bytes] = {}
    for item in plan.bundle.content.objects:
        data = generated_by_digest.get(item.sha256)
        if data is None:
            source_declaration = declarations_by_digest.get(item.sha256)
            if source_declaration is None:
                raise LegacyEvidenceError("evidence object has no admitted source or origin record")
            data, digest = _read_regular_file(
                source_root / Path(source_declaration.relative_path),
                trusted_root=source_root,
                max_bytes=item.size_bytes,
                expected_size=item.size_bytes,
            )
        else:
            digest = hashlib.sha256(data).hexdigest()
        if digest != item.sha256:
            raise LegacyEvidenceError("legacy evidence changed before CAS publication")
        if len(data) != item.size_bytes:
            raise LegacyEvidenceError("legacy evidence size changed before CAS publication")
        payloads[item.sha256] = data

    for item in plan.bundle.content.objects:
        bucket = object_root / item.sha256[:2]
        _ensure_child_directory(output_root, bucket, "evidence CAS bucket")
        target = bucket / item.sha256
        existing = _lstat_no_link(target, "evidence CAS object")
        if existing is not None:
            if not stat.S_ISREG(existing.st_mode):
                raise LegacyEvidenceError("existing evidence CAS object must be a regular file")
            _verify_existing_bytes(
                target,
                payloads[item.sha256],
                "evidence CAS object",
                root=output_root,
            )

    written = 0
    reused = 0
    for item in plan.bundle.content.objects:
        bucket = object_root / item.sha256[:2]
        target = bucket / item.sha256
        if _publish_no_replace(output_root, target, payloads[item.sha256], "evidence CAS object"):
            written += 1
        else:
            reused += 1
    return written, reused


def _bundle_bytes(bundle: EvidenceBundle) -> bytes:
    return (
        json.dumps(
            bundle.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def import_legacy_round(
    source_root: Path,
    index_path: Path,
    *,
    expected_index_sha256: str,
    output_root: Path,
    successor_anchor: LegacySuccessorAnchor | None = None,
) -> LegacyImportResult:
    """Verify, admit, and atomically materialize one reviewed legacy evidence round."""
    verification = verify_legacy_round(
        source_root,
        index_path,
        expected_index_sha256=expected_index_sha256,
        successor_anchor=successor_anchor,
    )
    _validate_output_root_location(source_root, output_root)
    plan = _build_import_plan(verification)
    _ensure_output_root(source_root, output_root)
    profile = _profile_for_round(verification.round)
    object_root = output_root / "objects"
    manifest_path = output_root / "bundles" / f"{profile.directory_name}.json"
    written, reused = _materialize_objects(
        plan,
        source_root=source_root,
        output_root=output_root,
        object_root=object_root,
    )

    final_verification = verify_legacy_round(
        source_root,
        index_path,
        expected_index_sha256=expected_index_sha256,
        successor_anchor=successor_anchor,
    )
    if final_verification != verification:
        raise LegacyEvidenceError("legacy archive changed during import")

    EvidenceBundleReader(
        plan.bundle,
        object_root,
        expected_bundle_id=plan.bundle.bundle_id,
    ).verify()
    manifest_created = _publish_no_replace(
        output_root,
        manifest_path,
        _bundle_bytes(plan.bundle),
        "evidence bundle manifest",
    )
    reader = EvidenceBundleReader.from_manifest(
        manifest_path,
        object_root,
        expected_bundle_id=plan.bundle.bundle_id,
    )
    if reader.bundle != plan.bundle:
        raise LegacyEvidenceError("published evidence bundle manifest changed unexpectedly")
    reader.verify()
    return LegacyImportResult(
        bundle=plan.bundle,
        verification_level=verification.level,
        objects_written=written,
        objects_reused=reused,
        manifest_created=manifest_created,
        object_root=object_root,
        manifest_path=manifest_path,
    )
