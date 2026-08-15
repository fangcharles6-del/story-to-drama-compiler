"""Offline, fail-closed materialization of the reviewed R2-R6 evidence store."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from sdc.contracts import EvidenceAcquisition
from sdc.evidence import EvidenceBundleError, EvidenceBundleReader
from sdc.legacy_evidence import (
    LegacyEvidenceError,
    LegacySuccessorAnchor,
    LegacyVerificationLevel,
    LegacyVerificationReport,
    _build_import_plan,
    import_legacy_round,
    verify_legacy_round,
)


@dataclass(frozen=True, slots=True)
class ReviewedLegacyRound:
    """Git-reviewed anchors and deterministic output expectations for one legacy round."""

    round: str
    directory: str
    index: str
    expected_index_sha256: str
    expected_manifest_sha256: str
    expected_report_sha256: str
    expected_tree_sha256: str
    expected_file_count: int
    expected_level: LegacyVerificationLevel
    expected_bundle_id: str
    expected_member_count: int
    expected_new_objects: int


REVIEWED_ARCHIVE_CATALOG: tuple[ReviewedLegacyRound, ...] = (
    ReviewedLegacyRound(
        round="V02-R2",
        directory="v02-r2",
        index="v02-r2-index.json",
        expected_index_sha256=("ef63adc9c040dc543ce593b70b9729c6b29cd9ff4af947856365756f281c743f"),
        expected_manifest_sha256=(
            "9c4489c40d78a105bc49ec106f9ea13d7551a9694d2ee33f1642bbfe68761d90"
        ),
        expected_report_sha256=("f3fb761f6091201aa726a7c81333cf74a2f3ef83c88cf78745df2cddf041fbde"),
        expected_tree_sha256=("e878442d46ade842dd766c14e91af63f15e0ee973a105441030b5bfb7e9b4692"),
        expected_file_count=29,
        expected_level=LegacyVerificationLevel.CHAIN_COMPAT,
        expected_bundle_id=("2d33b747367d396f245ddf15187628cbc96936a39ad8cb948282ec87c4c65a8e"),
        expected_member_count=22,
        expected_new_objects=22,
    ),
    ReviewedLegacyRound(
        round="V02-R3",
        directory="v02-r3",
        index="v02-r3-index.json",
        expected_index_sha256=("9fee187499617e880fbb0d07191ee315efa6ec3a095b06c5aadb7293b0538591"),
        expected_manifest_sha256=(
            "104cc4c56d7f6c539232f0e253fe6b4bcd0ddb3354e0a77f16aa3add8ceba6cb"
        ),
        expected_report_sha256=("72afb1ccb1f06ab9abf39c1e2550d17373cf75762f6536ac570ef57d5b51a3b3"),
        expected_tree_sha256=("f6b9172f6d4e9f80c0eb485d42b75602ba856dc15edb4dc2233d41ce3fc5bd68"),
        expected_file_count=28,
        expected_level=LegacyVerificationLevel.CHAIN_COMPAT,
        expected_bundle_id=("07791b67f57c94bc5e5860b74f770317a1b59bd4ea21bfbac9f01613ac11e906"),
        expected_member_count=22,
        expected_new_objects=3,
    ),
    ReviewedLegacyRound(
        round="V02-R4",
        directory="v02-r4",
        index="v02-r4-index.json",
        expected_index_sha256=("51beb34e5111bc864018a0a5ac37fadf50d86aea7c9944c85b3902c6541bf550"),
        expected_manifest_sha256=(
            "44a97e5d58be29a28ff3db60ee9d0606e1cd73889c65440fcbb8a8195bfe7ef6"
        ),
        expected_report_sha256=("753ff192e24cbd6001015f7a80c23b78e7672f0e323877a8b9fdde5a0b715d8b"),
        expected_tree_sha256=("5f00168d4de2377d1cc12012e7a5a1f30be52369633f43f92c22671a28bf3e8d"),
        expected_file_count=37,
        expected_level=LegacyVerificationLevel.FULL_DESCRIPTOR_TREE,
        expected_bundle_id=("5d3b087154adfe423f7b14190d67a54b35ce3e84eae87dd99ffd6bb8312937ec"),
        expected_member_count=29,
        expected_new_objects=10,
    ),
    ReviewedLegacyRound(
        round="V02-R5",
        directory="v02-r5",
        index="v02-r5-index.json",
        expected_index_sha256=("dfa9ef2af0049e505e25e44da0d090e80ed49be7df478fe95ef40a41f726624e"),
        expected_manifest_sha256=(
            "061e7ced7cf5fc2798d1c1281a2659bfed5c0eb62c1f018018fcec68a2c818eb"
        ),
        expected_report_sha256=("eb9cc499cc6db71759bfe8a20a075eb02c276b3e2275ff84e46364376b0230ab"),
        expected_tree_sha256=("d5d4797fd668f8391fbf8a35dff6ec858334358ea47898194e52d17d4d898aa9"),
        expected_file_count=39,
        expected_level=LegacyVerificationLevel.FULL_DESCRIPTOR_TREE,
        expected_bundle_id=("8ca336193cd5cd7a5cf0f766f6ae7b482de8def97e63df0b6cca0f95fc278f5b"),
        expected_member_count=29,
        expected_new_objects=5,
    ),
    ReviewedLegacyRound(
        round="V02-R6",
        directory="v02-r6",
        index="v02-r6-index.json",
        expected_index_sha256=("cf03a19ba671d89e1504b4c88b5bae1dd33a559eea48965d6ce6af0f47b850c5"),
        expected_manifest_sha256=(
            "c7c9dae6d2799eaf472f10821f33869af68e3903eb0e94c4812ecc4bdec8af5b"
        ),
        expected_report_sha256=("df81e7ff5db0e6ca2662bffcc4bec79bbe1b584c0564121603ea5485cd3a653c"),
        expected_tree_sha256=("2415399d0fb1458d7d9105ce47b96ac5d6162f37af97270653e99599fcc0cb3f"),
        expected_file_count=37,
        expected_level=LegacyVerificationLevel.FULL_DESCRIPTOR_TREE,
        expected_bundle_id=("f91f9aadf10ce0fbfe7a58df9c7c3fbd2f07d1b751b4346d44e19e2026be39d7"),
        expected_member_count=27,
        expected_new_objects=27,
    ),
)


@dataclass(frozen=True, slots=True)
class CanonicalStoreReport:
    """Verified identity and publication state of the canonical local evidence store."""

    output_root: Path
    catalog_sha256: str
    object_count: int
    round_bundle_ids: tuple[tuple[str, str], ...]
    created: bool


class CanonicalMaterializationError(EvidenceBundleError):
    """Raised when reviewed-store verification or materialization fails closed."""


_CATALOG_DOCUMENT_TYPE = "sdc.reviewed-legacy-evidence-catalog"
_CATALOG_SCHEMA_VERSION = "1.0.0"
_TREE_ALGORITHM = "compact-json-array-v1"
_EXPECTED_OBJECT_COUNT = 67
_EXPECTED_STORE_FILE_COUNT = 73
_MAX_STORE_DIRECTORY_COUNT = 70
_PROTECTED_OUTPUT_COMPONENTS = frozenset(
    {
        "canary",
        "v02",
        "v02-r1",
        "v02-r2",
        "v02-r3",
        "v02-r4",
        "v02-r5",
        "v02-r6",
        "v02-r6-live",
    }
)


def _reviewed_round(round_name: str) -> ReviewedLegacyRound:
    matches = [item for item in REVIEWED_ARCHIVE_CATALOG if item.round == round_name]
    if len(matches) != 1:
        raise CanonicalMaterializationError(
            f"reviewed archive catalog must contain exactly one {round_name} entry"
        )
    return matches[0]


def _validate_reviewed_catalog() -> None:
    expected_rounds = ("V02-R2", "V02-R3", "V02-R4", "V02-R5", "V02-R6")
    if tuple(item.round for item in REVIEWED_ARCHIVE_CATALOG) != expected_rounds:
        raise CanonicalMaterializationError("reviewed archive catalog order or closure is invalid")
    if len({item.directory.casefold() for item in REVIEWED_ARCHIVE_CATALOG}) != len(
        REVIEWED_ARCHIVE_CATALOG
    ):
        raise CanonicalMaterializationError("reviewed archive directories collide")
    if len({item.index.casefold() for item in REVIEWED_ARCHIVE_CATALOG}) != len(
        REVIEWED_ARCHIVE_CATALOG
    ):
        raise CanonicalMaterializationError("reviewed outer-index paths collide")
    for item in REVIEWED_ARCHIVE_CATALOG:
        if item.directory != item.round.casefold() or item.index != f"{item.directory}-index.json":
            raise CanonicalMaterializationError("reviewed archive path mapping is invalid")
        digests = (
            item.expected_index_sha256,
            item.expected_manifest_sha256,
            item.expected_report_sha256,
            item.expected_tree_sha256,
            item.expected_bundle_id,
        )
        if any(len(value) != 64 or value != value.lower() for value in digests):
            raise CanonicalMaterializationError("reviewed catalog contains an invalid SHA-256")
        if any(character not in "0123456789abcdef" for value in digests for character in value):
            raise CanonicalMaterializationError("reviewed catalog contains an invalid SHA-256")
        if item.expected_file_count < 1 or item.expected_member_count < 1:
            raise CanonicalMaterializationError("reviewed catalog contains an invalid count")
        if item.expected_new_objects < 1:
            raise CanonicalMaterializationError("reviewed catalog contains an invalid object count")
    if (
        sum(item.expected_new_objects for item in REVIEWED_ARCHIVE_CATALOG)
        != _EXPECTED_OBJECT_COUNT
    ):
        raise CanonicalMaterializationError(
            "reviewed catalog object closure must contain 67 objects"
        )


def _successor_anchor(canary_root: Path) -> LegacySuccessorAnchor:
    r3 = _reviewed_round("V02-R3")
    return LegacySuccessorAnchor(
        source_root=canary_root / r3.directory,
        index_path=canary_root / r3.index,
        expected_index_sha256=r3.expected_index_sha256,
    )


def _verify_report(report: LegacyVerificationReport, reviewed: ReviewedLegacyRound) -> None:
    actual = (
        report.round,
        report.outer_index_sha256,
        report.manifest_sha256,
        report.freeze_report_sha256,
        report.tree_sha256,
        report.file_count,
        report.level,
    )
    expected = (
        reviewed.round,
        reviewed.expected_index_sha256,
        reviewed.expected_manifest_sha256,
        reviewed.expected_report_sha256,
        reviewed.expected_tree_sha256,
        reviewed.expected_file_count,
        reviewed.expected_level,
    )
    if actual != expected:
        raise CanonicalMaterializationError(
            f"reviewed legacy archive verification drifted: {reviewed.round}"
        )
    if report.tree_algorithm != _TREE_ALGORITHM:
        raise CanonicalMaterializationError(
            f"reviewed legacy archive tree algorithm drifted: {reviewed.round}"
        )


def verify_reviewed_archives(canary_root: Path) -> tuple[LegacyVerificationReport, ...]:
    """Verify all reviewed R2-R6 archives without writing any materialized evidence."""
    _validate_reviewed_catalog()
    root = canary_root.absolute()
    successor = _successor_anchor(root)
    reports: list[LegacyVerificationReport] = []
    for reviewed in REVIEWED_ARCHIVE_CATALOG:
        try:
            report = verify_legacy_round(
                root / reviewed.directory,
                root / reviewed.index,
                expected_index_sha256=reviewed.expected_index_sha256,
                successor_anchor=successor if reviewed.round == "V02-R2" else None,
            )
        except CanonicalMaterializationError:
            raise
        except EvidenceBundleError as exc:
            raise CanonicalMaterializationError(
                f"reviewed legacy archive failed verification: {reviewed.round}"
            ) from exc
        _verify_report(report, reviewed)
        reports.append(report)
    seen_objects: set[str] = set()
    try:
        for report, reviewed in zip(reports, REVIEWED_ARCHIVE_CATALOG, strict=True):
            bundle = _build_import_plan(report).bundle
            if bundle.bundle_id != reviewed.expected_bundle_id:
                raise CanonicalMaterializationError(
                    f"reviewed legacy bundle identity drifted: {reviewed.round}"
                )
            if len(bundle.content.members) != reviewed.expected_member_count:
                raise CanonicalMaterializationError(
                    f"reviewed legacy bundle member count drifted: {reviewed.round}"
                )
            if any(
                capture.acquisition is not EvidenceAcquisition.LEGACY_IMPORT
                for capture in bundle.content.captures
            ):
                raise CanonicalMaterializationError(
                    f"reviewed legacy bundle acquisition drifted: {reviewed.round}"
                )
            current_objects = {item.sha256 for item in bundle.content.objects}
            if len(current_objects - seen_objects) != reviewed.expected_new_objects:
                raise CanonicalMaterializationError(
                    f"reviewed legacy object closure drifted: {reviewed.round}"
                )
            seen_objects.update(current_objects)
    except CanonicalMaterializationError:
        raise
    except (EvidenceBundleError, ValueError) as exc:
        raise CanonicalMaterializationError(
            "reviewed legacy bundles could not be planned without writing"
        ) from exc
    if len(seen_objects) != _EXPECTED_OBJECT_COUNT:
        raise CanonicalMaterializationError("reviewed legacy object closure count drifted")
    return tuple(reports)


def _catalog_payload() -> dict[str, Any]:
    return {
        "document_type": _CATALOG_DOCUMENT_TYPE,
        "schema_version": _CATALOG_SCHEMA_VERSION,
        "layout": {
            "bundle_directory": "bundles",
            "object_directory": "objects",
            "object_path": "objects/{sha256[0:2]}/{sha256}",
        },
        "object_count": sum(item.expected_new_objects for item in REVIEWED_ARCHIVE_CATALOG),
        "rounds": [
            {
                "round": item.round,
                "archive_directory": item.directory,
                "outer_index": item.index,
                "outer_index_sha256": item.expected_index_sha256,
                "manifest_sha256": item.expected_manifest_sha256,
                "freeze_report_sha256": item.expected_report_sha256,
                "tree_algorithm": _TREE_ALGORITHM,
                "tree_sha256": item.expected_tree_sha256,
                "file_count": item.expected_file_count,
                "verification_level": item.expected_level.value,
                "bundle_manifest": f"bundles/{item.directory}.json",
                "bundle_id": item.expected_bundle_id,
                "member_count": item.expected_member_count,
            }
            for item in REVIEWED_ARCHIVE_CATALOG
        ],
    }


def _catalog_bytes() -> bytes:
    return (
        json.dumps(
            _catalog_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _path_lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _reject_protected_output_path(path: Path) -> None:
    if any(part.casefold() in _PROTECTED_OUTPUT_COMPONENTS for part in path.absolute().parts):
        raise CanonicalMaterializationError(
            "canonical output root uses a protected Canary archive path"
        )


def _is_link_like(path: Path, value: os.stat_result | None = None) -> bool:
    try:
        inspected = value if value is not None else path.lstat()
    except OSError:
        return False
    is_junction = getattr(path, "is_junction", None)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    attributes = getattr(inspected, "st_file_attributes", 0)
    return (
        stat.S_ISLNK(inspected.st_mode)
        or bool(is_junction is not None and is_junction())
        or bool(attributes & reparse_flag)
    )


def _lstat_no_link(path: Path, label: str) -> os.stat_result | None:
    try:
        value = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CanonicalMaterializationError(f"{label} could not be inspected") from exc
    if _is_link_like(path, value):
        raise CanonicalMaterializationError(f"{label} contains a link or junction")
    return value


def _require_real_directory(path: Path, label: str) -> None:
    value = _lstat_no_link(path, label)
    if value is None or not stat.S_ISDIR(value.st_mode):
        raise CanonicalMaterializationError(f"{label} must be a real directory")
    for parent in path.parents:
        parent_value = _lstat_no_link(parent, label)
        if parent_value is None or not stat.S_ISDIR(parent_value.st_mode):
            raise CanonicalMaterializationError(f"{label} has an unsafe ancestor")


def _ensure_real_directory(path: Path, label: str) -> None:
    missing: list[Path] = []
    cursor = path
    value = _lstat_no_link(cursor, label)
    while value is None:
        missing.append(cursor)
        if cursor.parent == cursor:
            raise CanonicalMaterializationError(f"{label} has no existing ancestor")
        cursor = cursor.parent
        value = _lstat_no_link(cursor, label)
    if not stat.S_ISDIR(value.st_mode):
        raise CanonicalMaterializationError(f"{label} parent must be a real directory")
    for parent in cursor.parents:
        parent_value = _lstat_no_link(parent, label)
        if parent_value is None or not stat.S_ISDIR(parent_value.st_mode):
            raise CanonicalMaterializationError(f"{label} has an unsafe ancestor")
    try:
        for component in reversed(missing):
            component.mkdir(mode=0o700)
            created = _lstat_no_link(component, label)
            if created is None or not stat.S_ISDIR(created.st_mode):
                raise CanonicalMaterializationError(f"{label} must be a real directory")
    except CanonicalMaterializationError:
        raise
    except OSError as exc:
        raise CanonicalMaterializationError(f"{label} could not be created") from exc


def _require_safe_existing_ancestor(path: Path, label: str) -> None:
    cursor = path
    value = _lstat_no_link(cursor, label)
    while value is None:
        if cursor.parent == cursor:
            raise CanonicalMaterializationError(f"{label} has no existing ancestor")
        cursor = cursor.parent
        value = _lstat_no_link(cursor, label)
    if not stat.S_ISDIR(value.st_mode):
        raise CanonicalMaterializationError(f"{label} ancestor must be a real directory")
    for parent in cursor.parents:
        parent_value = _lstat_no_link(parent, label)
        if parent_value is None or not stat.S_ISDIR(parent_value.st_mode):
            raise CanonicalMaterializationError(f"{label} has an unsafe ancestor")


def _read_exact_file(path: Path, *, trusted_root: Path, expected: bytes, label: str) -> bytes:
    try:
        relative = path.absolute().relative_to(trusted_root.absolute())
    except ValueError as exc:
        raise CanonicalMaterializationError(f"{label} escapes the canonical store") from exc
    if not relative.parts:
        raise CanonicalMaterializationError(f"{label} must be below the canonical store")
    _require_real_directory(trusted_root, "canonical store root")
    parent = trusted_root
    for name in relative.parts[:-1]:
        parent /= name
        _require_real_directory(parent, f"{label} parent")
    before = _lstat_no_link(path, label)
    if before is None or not stat.S_ISREG(before.st_mode):
        raise CanonicalMaterializationError(f"{label} must be a regular file")
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise CanonicalMaterializationError(f"{label} must be a regular file")
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                raise CanonicalMaterializationError(f"{label} changed before it was read")
            data = handle.read(len(expected) + 1)
            after = os.fstat(handle.fileno())
        final = _lstat_no_link(path, label)
    except CanonicalMaterializationError:
        raise
    except OSError as exc:
        raise CanonicalMaterializationError(f"{label} could not be read") from exc
    if final is None or (final.st_dev, final.st_ino) != (after.st_dev, after.st_ino):
        raise CanonicalMaterializationError(f"{label} changed while it was read")
    if (
        opened.st_size != after.st_size
        or opened.st_mtime_ns != after.st_mtime_ns
        or final.st_size != after.st_size
        or final.st_mtime_ns != after.st_mtime_ns
        or data != expected
    ):
        raise CanonicalMaterializationError(f"{label} does not match the reviewed bytes")
    return data


def _walk_store(root: Path) -> tuple[frozenset[str], frozenset[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    pending = [root]
    try:
        while pending:
            current = pending.pop()
            with os.scandir(current) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    value = _lstat_no_link(path, "canonical store entry")
                    if value is None:
                        raise CanonicalMaterializationError(
                            "canonical store entry disappeared during enumeration"
                        )
                    relative = path.relative_to(root).as_posix()
                    if stat.S_ISDIR(value.st_mode):
                        directories.add(relative)
                        if len(directories) > _MAX_STORE_DIRECTORY_COUNT:
                            raise CanonicalMaterializationError(
                                "canonical store contains too many directories"
                            )
                        pending.append(path)
                    elif stat.S_ISREG(value.st_mode):
                        files.add(relative)
                        if len(files) > _EXPECTED_STORE_FILE_COUNT:
                            raise CanonicalMaterializationError(
                                "canonical store contains too many files"
                            )
                    else:
                        raise CanonicalMaterializationError(
                            "canonical store contains an unsafe entry"
                        )
    except CanonicalMaterializationError:
        raise
    except OSError as exc:
        raise CanonicalMaterializationError("canonical store could not be enumerated") from exc
    return frozenset(files), frozenset(directories)


def _load_verified_bundles(
    output_root: Path,
) -> tuple[tuple[tuple[str, str], ...], set[str]]:
    object_root = output_root / "objects"
    bundle_root = output_root / "bundles"
    _require_real_directory(object_root, "canonical object root")
    _require_real_directory(bundle_root, "canonical bundle root")
    bundle_ids: list[tuple[str, str]] = []
    object_descriptors: dict[str, tuple[int, str]] = {}
    for reviewed in REVIEWED_ARCHIVE_CATALOG:
        manifest = bundle_root / f"{reviewed.directory}.json"
        reader = EvidenceBundleReader.from_manifest(
            manifest,
            object_root,
            expected_bundle_id=reviewed.expected_bundle_id,
        )
        resolved = reader.verify()
        bundle = reader.bundle
        if len(bundle.content.members) != reviewed.expected_member_count:
            raise CanonicalMaterializationError(
                f"canonical bundle member count drifted: {reviewed.round}"
            )
        if len(resolved) != reviewed.expected_member_count:
            raise CanonicalMaterializationError(
                f"canonical bundle resolution is incomplete: {reviewed.round}"
            )
        if any(
            capture.acquisition is not EvidenceAcquisition.LEGACY_IMPORT
            for capture in bundle.content.captures
        ):
            raise CanonicalMaterializationError(
                f"canonical bundle contains non-legacy acquisition: {reviewed.round}"
            )
        try:
            reader.assert_current(at=max(bundle.content.created_at, bundle.content.valid_until))
        except EvidenceBundleError:
            pass
        else:
            raise CanonicalMaterializationError(
                f"canonical legacy bundle unexpectedly became current: {reviewed.round}"
            )
        for item in bundle.content.objects:
            descriptor = (item.size_bytes, item.media_type)
            existing = object_descriptors.get(item.sha256)
            if existing is not None and existing != descriptor:
                raise CanonicalMaterializationError(
                    "canonical bundles disagree about an object descriptor"
                )
            object_descriptors[item.sha256] = descriptor
        bundle_ids.append((reviewed.round, bundle.bundle_id))
    if len(object_descriptors) != _EXPECTED_OBJECT_COUNT:
        raise CanonicalMaterializationError("canonical object closure count drifted")
    return tuple(bundle_ids), set(object_descriptors)


def _verify_canonical_store(output_root: Path) -> CanonicalStoreReport:
    _validate_reviewed_catalog()
    root = output_root.absolute()
    _require_real_directory(root, "canonical store root")
    expected_catalog = _catalog_bytes()
    _read_exact_file(
        root / "catalog.json",
        trusted_root=root,
        expected=expected_catalog,
        label="canonical store catalog",
    )
    bundle_ids, object_hashes = _load_verified_bundles(root)
    expected_files = {
        "catalog.json",
        *(f"bundles/{item.directory}.json" for item in REVIEWED_ARCHIVE_CATALOG),
        *(f"objects/{digest[:2]}/{digest}" for digest in object_hashes),
    }
    expected_directories = {
        "bundles",
        "objects",
        *(f"objects/{digest[:2]}" for digest in object_hashes),
    }
    actual_files, actual_directories = _walk_store(root)
    if actual_files != expected_files or actual_directories != expected_directories:
        raise CanonicalMaterializationError("canonical store layout is not an exact closure")
    second_bundle_ids, second_object_hashes = _load_verified_bundles(root)
    if second_bundle_ids != bundle_ids or second_object_hashes != object_hashes:
        raise CanonicalMaterializationError("canonical store changed during verification")
    _read_exact_file(
        root / "catalog.json",
        trusted_root=root,
        expected=expected_catalog,
        label="canonical store catalog",
    )
    return CanonicalStoreReport(
        output_root=root,
        catalog_sha256=hashlib.sha256(expected_catalog).hexdigest(),
        object_count=len(object_hashes),
        round_bundle_ids=bundle_ids,
        created=False,
    )


def verify_canonical_store(output_root: Path) -> CanonicalStoreReport:
    """Verify an existing canonical R2-R6 store against the Git-reviewed catalog."""
    try:
        _reject_protected_output_path(output_root)
        return _verify_canonical_store(output_root)
    except CanonicalMaterializationError:
        raise
    except (EvidenceBundleError, OSError, ValueError) as exc:
        raise CanonicalMaterializationError("canonical store failed reviewed verification") from exc


def _validate_output_location(canary_root: Path, output_root: Path) -> None:
    if output_root.parent == output_root:
        raise CanonicalMaterializationError("canonical output root must not be a filesystem root")
    source_absolute = canary_root.absolute()
    output_absolute = output_root.absolute()
    _reject_protected_output_path(output_absolute)
    if (
        output_absolute == source_absolute
        or source_absolute in output_absolute.parents
        or output_absolute in source_absolute.parents
    ):
        raise CanonicalMaterializationError(
            "canonical output root must not overlap the Canary archive container"
        )
    _require_real_directory(source_absolute, "canonical Canary source root")
    _require_safe_existing_ancestor(
        output_absolute.parent,
        "canonical output parent",
    )
    try:
        source = source_absolute.resolve(strict=True)
        candidate = output_absolute.resolve(strict=False)
    except OSError as exc:
        raise CanonicalMaterializationError(
            "canonical source or output location could not be resolved"
        ) from exc
    _reject_protected_output_path(candidate)
    if candidate == source or source in candidate.parents or candidate in source.parents:
        raise CanonicalMaterializationError(
            "canonical output root must not overlap the Canary archive container"
        )


def _write_catalog(stage: Path) -> None:
    path = stage / "catalog.json"
    data = _catalog_bytes()
    try:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CanonicalMaterializationError("canonical catalog could not be staged") from exc
    _read_exact_file(
        path,
        trusted_root=stage,
        expected=data,
        label="staged canonical catalog",
    )


def _publish_directory_no_replace(stage: Path, output_root: Path) -> None:
    if _path_lexists(output_root):
        raise CanonicalMaterializationError("canonical output root appeared before publication")
    _require_real_directory(stage, "canonical staging root")
    _require_real_directory(output_root.parent, "canonical output parent")
    try:
        output_root.mkdir(mode=0o700)
    except OSError as exc:
        raise CanonicalMaterializationError(
            "canonical output root could not be claimed without replacement"
        ) from exc
    _require_real_directory(output_root, "canonical output root")
    files, directories = _walk_store(stage)
    catalog_path = "catalog.json"
    if catalog_path not in files:
        raise CanonicalMaterializationError("staged canonical catalog is missing")
    try:
        for relative in sorted(directories, key=lambda value: (value.count("/"), value)):
            _require_real_directory(output_root, "canonical output root")
            (output_root / relative).mkdir()
        for relative in sorted(files - {catalog_path}):
            _require_real_directory(output_root, "canonical output root")
            os.link(stage / relative, output_root / relative, follow_symlinks=False)
        _require_real_directory(output_root, "canonical output root")
        os.link(
            stage / catalog_path,
            output_root / catalog_path,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise CanonicalMaterializationError(
            "canonical store could not be published without replacement"
        ) from exc
    if not _path_lexists(output_root / catalog_path):
        raise CanonicalMaterializationError("canonical catalog publication result is unknown")


def _remove_published_stage(stage: Path, *, output_parent: Path, output_name: str) -> None:
    expected_prefix = f".{output_name}.stage-"
    if stage.parent != output_parent or not stage.name.startswith(expected_prefix):
        raise CanonicalMaterializationError("canonical staging cleanup target is unsafe")
    files, directories = _walk_store(stage)
    try:
        for relative in sorted(files):
            path = stage / relative
            value = _lstat_no_link(path, "canonical staging file")
            if value is None or not stat.S_ISREG(value.st_mode):
                raise CanonicalMaterializationError("canonical staging file is unsafe")
            path.unlink()
        for relative in sorted(
            directories,
            key=lambda value: (value.count("/"), value),
            reverse=True,
        ):
            (stage / relative).rmdir()
        stage.rmdir()
    except CanonicalMaterializationError:
        raise
    except OSError as exc:
        raise CanonicalMaterializationError(
            "published staging directory could not be removed"
        ) from exc


def materialize_canonical_store(canary_root: Path, output_root: Path) -> CanonicalStoreReport:
    """Materialize all reviewed rounds and publish them as one canonical directory."""
    _validate_reviewed_catalog()
    source = canary_root.absolute()
    target = output_root.absolute()
    _validate_output_location(source, target)
    lock_path = target.parent / f".{target.name}.materialize.lock"
    if _path_lexists(lock_path):
        raise CanonicalMaterializationError(
            f"HUMAN_GATE: canonical materialization lock is present: {lock_path}"
        )
    if _path_lexists(target):
        try:
            return verify_canonical_store(target)
        except Exception as exc:
            raise CanonicalMaterializationError(
                "HUMAN_GATE: existing canonical store failed verification; it was not modified"
            ) from exc

    try:
        initial_reports = verify_reviewed_archives(source)
        _ensure_real_directory(target.parent, "canonical output parent")
    except CanonicalMaterializationError as exc:
        raise CanonicalMaterializationError(
            "HUMAN_GATE: reviewed archive preflight failed; no canonical store was created"
        ) from exc
    try:
        lock = lock_path.open("xb")
    except OSError as exc:
        raise CanonicalMaterializationError(
            f"HUMAN_GATE: canonical materialization lock is unavailable: {lock_path}"
        ) from exc

    stage: Path | None = None
    try:
        stage = Path(
            tempfile.mkdtemp(prefix=f".{target.name}.stage-", dir=target.parent)
        ).absolute()
        _require_real_directory(stage, "canonical staging root")
        successor = _successor_anchor(source)
        written_counts: list[int] = []
        for reviewed in REVIEWED_ARCHIVE_CATALOG:
            result = import_legacy_round(
                source / reviewed.directory,
                source / reviewed.index,
                expected_index_sha256=reviewed.expected_index_sha256,
                output_root=stage,
                successor_anchor=successor if reviewed.round == "V02-R2" else None,
            )
            if result.bundle.bundle_id != reviewed.expected_bundle_id:
                raise CanonicalMaterializationError(
                    f"materialized bundle identity drifted: {reviewed.round}"
                )
            if result.verification_level is not reviewed.expected_level:
                raise CanonicalMaterializationError(
                    f"materialized verification level drifted: {reviewed.round}"
                )
            if len(result.bundle.content.members) != reviewed.expected_member_count:
                raise CanonicalMaterializationError(
                    f"materialized bundle member count drifted: {reviewed.round}"
                )
            if result.objects_written != reviewed.expected_new_objects:
                raise CanonicalMaterializationError(
                    f"materialized new-object count drifted: {reviewed.round}"
                )
            if not result.manifest_created:
                raise CanonicalMaterializationError(
                    f"materialized bundle manifest was not newly created: {reviewed.round}"
                )
            written_counts.append(result.objects_written)
        if tuple(written_counts) != tuple(
            item.expected_new_objects for item in REVIEWED_ARCHIVE_CATALOG
        ):
            raise CanonicalMaterializationError("materialized per-round object counts drifted")

        final_reports = verify_reviewed_archives(source)
        if final_reports != initial_reports:
            raise CanonicalMaterializationError("reviewed archives changed during materialization")
        _write_catalog(stage)
        staged_report = verify_canonical_store(stage)
        if staged_report.object_count != _EXPECTED_OBJECT_COUNT:
            raise CanonicalMaterializationError("staged canonical object count drifted")
        _publish_directory_no_replace(stage, target)
        published_report = verify_canonical_store(target)
        _remove_published_stage(
            stage,
            output_parent=target.parent,
            output_name=target.name,
        )
        try:
            lock.close()
            lock_path.unlink()
        except OSError as exc:
            raise CanonicalMaterializationError(
                f"HUMAN_GATE: canonical store is published but its lock remains: {lock_path}"
            ) from exc
        return replace(published_report, created=True)
    except Exception as exc:
        try:
            lock.close()
        except OSError:
            pass
        if stage is not None and _path_lexists(stage):
            artifact_message = f"staging is preserved at {stage}"
        elif _path_lexists(target):
            artifact_message = f"published candidate is preserved at {target}"
        else:
            artifact_message = "no published canonical directory is visible"
        raise CanonicalMaterializationError(
            "HUMAN_GATE: canonical materialization did not complete; "
            f"{artifact_message}; lock is preserved at {lock_path}"
        ) from exc


def _report_payload(report: CanonicalStoreReport) -> dict[str, Any]:
    return {
        "output_root": str(report.output_root),
        "catalog_sha256": report.catalog_sha256,
        "object_count": report.object_count,
        "round_bundle_ids": [
            {"round": round_name, "bundle_id": bundle_id}
            for round_name, bundle_id in report.round_bundle_ids
        ],
        "created": report.created,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify or materialize the fixed reviewed R2-R6 legacy evidence store"
    )
    parser.add_argument(
        "--canary-root",
        type=Path,
        default=Path(".artifacts/canary"),
        help="canonical local Canary archive container",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(".artifacts/evidence-cas/v1"),
        help="canonical evidence store root",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="materialize and publish; without this flag verification is read-only",
    )
    args = parser.parse_args(argv)
    try:
        if args.apply:
            payload: dict[str, Any] = {
                "mode": "apply",
                "store": _report_payload(
                    materialize_canonical_store(args.canary_root, args.output_root)
                ),
            }
        else:
            reports = verify_reviewed_archives(args.canary_root)
            _validate_output_location(
                args.canary_root.absolute(),
                args.output_root.absolute(),
            )
            lock_path = (
                args.output_root.absolute().parent
                / f".{args.output_root.absolute().name}.materialize.lock"
            )
            if _path_lexists(lock_path):
                raise CanonicalMaterializationError(
                    f"HUMAN_GATE: canonical materialization lock is present: {lock_path}"
                )
            payload = {
                "mode": "verify-only",
                "archives": [
                    {
                        "round": report.round,
                        "verification_level": report.level.value,
                        "outer_index_sha256": report.outer_index_sha256,
                        "file_count": report.file_count,
                    }
                    for report in reports
                ],
                "store": (
                    _report_payload(verify_canonical_store(args.output_root))
                    if _path_lexists(args.output_root.absolute())
                    else None
                ),
            }
    except (LegacyEvidenceError, EvidenceBundleError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2), end="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
