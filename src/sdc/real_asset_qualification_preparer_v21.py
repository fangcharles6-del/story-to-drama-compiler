"""Trusted local preparation of zero-authority Pack Review v2 qualification requests.

The three CLI operations in this module consume only explicitly named local files.  They never
scan for inputs, perform a qualification, create a rights manifest, or contact a runtime or
Provider.  Every successful operation finishes with an exact second verification of the frozen
Pack, its fourteen media objects, the Review v2 closure, and four independent retained records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Never, cast

from pydantic import BaseModel, ValidationError

from sdc.creative_media import CreativeMediaError, validate_local_path
from sdc.real_asset_intake import (
    CreativeSampleFrozenRealAssetPackManifest,
    FrozenRealAssetPack,
    RealAssetIntakeError,
    verify_real_asset_candidate_pack,
)
from sdc.real_asset_media import RealAssetMediaError, SafeLocalFile, read_safe_local_file
from sdc.real_asset_qualification_v2 import (
    CreativeSampleRealAssetQualificationRequestV2,
    RealAssetQualificationV2Error,
    build_real_asset_qualification_request_v2,
    parse_real_asset_qualification_request_v2_json,
)
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
    RealAssetReviewV2Error,
    load_real_asset_human_pack_review_v2,
    load_real_asset_review_pair_check_v2,
    load_real_asset_rights_evidence_bundle_v2,
)

_PACK_MANIFEST_NAME = "asset-pack.json"
_JSON_MAX_BYTES = 1_048_576
_PRIVATE_RECORD_MAX_BYTES = 64 * 1024 * 1024
_MEDIA_MAX_BYTES = 64 * 1024 * 1024
_MUTABLE_ALIAS_TOKENS = frozenset({"current", "latest", "newest"})
_UTC_SECONDS = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)


class TrustedLocalRequestPreparationError(RuntimeError):
    """The prepare-only local consumer failed closed."""


class _CliArgumentError(RuntimeError):
    pass


class _FailClosedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        del message
        raise _CliArgumentError


@dataclass(frozen=True, slots=True)
class TrustedLocalRequestPaths:
    """Every immutable upstream path required to prepare or verify one request."""

    pack_root: Path
    pack_manifest: Path
    media_paths: tuple[Path, ...]
    evidence_bundle: Path
    reviewer_a: Path
    reviewer_b: Path
    pair_check: Path
    evidence_retained_record: Path
    evidence_preparer_ref: Path
    reviewer_a_retained_record: Path
    reviewer_b_retained_record: Path


@dataclass(frozen=True, slots=True)
class _FileSeal:
    path: Path
    sha256: str
    size_bytes: int
    identity: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class _ReadySnapshot:
    pack: FrozenRealAssetPack
    pack_root_identity: tuple[int, int, int, int]
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2
    pair_check: CreativeSampleRealAssetReviewPairCheckV2
    evidence_retained_record: _FileSeal
    evidence_preparer_ref: _FileSeal
    reviewer_a_retained_record: _FileSeal
    reviewer_b_retained_record: _FileSeal
    files: tuple[_FileSeal, ...]
    request: CreativeSampleRealAssetQualificationRequestV2 | None = None


@dataclass(frozen=True, slots=True)
class _OutputTarget:
    path: Path
    parent: Path
    parent_physical_identity: tuple[int, int]


@dataclass(slots=True)
class _CreatedRequest:
    target: _OutputTarget
    descriptor: int
    parent_guard: int
    windows_parent_guard: bool
    seal: _FileSeal | None = None
    closed: bool = False


if sys.platform == "win32":
    import ctypes as _windows_ctypes
    import msvcrt as _windows_msvcrt
    from ctypes import wintypes as _windows_wintypes

    def _acquire_windows_parent_guard(target: _OutputTarget) -> int:
        create_file = _windows_ctypes.windll.kernel32.CreateFileW
        create_file.argtypes = (
            _windows_wintypes.LPCWSTR,
            _windows_wintypes.DWORD,
            _windows_wintypes.DWORD,
            _windows_wintypes.LPVOID,
            _windows_wintypes.DWORD,
            _windows_wintypes.DWORD,
            _windows_wintypes.HANDLE,
        )
        create_file.restype = _windows_wintypes.HANDLE
        handle = create_file(
            str(target.parent),
            0x0080,  # FILE_READ_ATTRIBUTES
            0x00000001 | 0x00000002,  # share read/write, deliberately deny delete/rename
            None,
            3,  # OPEN_EXISTING
            0x02000000,  # FILE_FLAG_BACKUP_SEMANTICS
            None,
        )
        invalid = _windows_ctypes.c_void_p(-1).value
        if handle == invalid:
            raise TrustedLocalRequestPreparationError(
                "request output parent could not be guarded"
            )
        return int(handle)

    def _close_windows_handle(handle: int) -> None:
        _windows_ctypes.windll.kernel32.CloseHandle(handle)

    def _open_windows_exclusive_request(target: _OutputTarget) -> int:
        create_file = _windows_ctypes.windll.kernel32.CreateFileW
        create_file.argtypes = (
            _windows_wintypes.LPCWSTR,
            _windows_wintypes.DWORD,
            _windows_wintypes.DWORD,
            _windows_wintypes.LPVOID,
            _windows_wintypes.DWORD,
            _windows_wintypes.DWORD,
            _windows_wintypes.HANDLE,
        )
        create_file.restype = _windows_wintypes.HANDLE
        handle = create_file(
            str(target.path),
            0x80000000 | 0x40000000 | 0x00010000,  # read, write and delete exact handle
            0x00000001,  # share read only; replacement/delete is denied while open
            None,
            1,  # CREATE_NEW
            0x00000080,  # FILE_ATTRIBUTE_NORMAL
            None,
        )
        invalid = _windows_ctypes.c_void_p(-1).value
        if handle == invalid:
            error = _windows_ctypes.get_last_error()
            if error in {80, 183}:
                raise FileExistsError(str(target.path))
            raise OSError(error, "CreateFileW failed")
        try:
            return _windows_msvcrt.open_osfhandle(
                int(handle), os.O_RDWR | getattr(os, "O_BINARY", 0)
            )
        except OSError:
            _close_windows_handle(int(handle))
            raise

    def _delete_open_windows_request(descriptor: int) -> bool:
        class FileDispositionInfo(_windows_ctypes.Structure):
            _fields_ = (("DeleteFile", _windows_wintypes.BOOL),)

        disposition = FileDispositionInfo(True)
        handle = _windows_msvcrt.get_osfhandle(descriptor)
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        set_information = kernel32.SetFileInformationByHandle
        set_information.argtypes = (
            _windows_wintypes.HANDLE,
            _windows_ctypes.c_int,
            _windows_wintypes.LPVOID,
            _windows_wintypes.DWORD,
        )
        set_information.restype = _windows_wintypes.BOOL
        return bool(
            set_information(
                handle,
                4,
                _windows_ctypes.byref(disposition),
                _windows_ctypes.sizeof(disposition),
            )
        )

else:

    def _windows_unavailable() -> Never:
        raise OSError("Windows-only request output helper is unavailable")

    def _acquire_windows_parent_guard(target: _OutputTarget) -> int:
        del target
        return _windows_unavailable()

    def _close_windows_handle(handle: int) -> None:
        del handle
        _windows_unavailable()

    def _open_windows_exclusive_request(target: _OutputTarget) -> int:
        del target
        return _windows_unavailable()

    def _delete_open_windows_request(descriptor: int) -> bool:
        del descriptor
        return _windows_unavailable()


def _canonical_document(value: BaseModel) -> bytes:
    return (
        json.dumps(
            value.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _canonical_utc_seconds(value: str, *, field: str) -> str:
    if _UTC_SECONDS.fullmatch(value) is None:
        raise TrustedLocalRequestPreparationError(f"{field} must be canonical UTC seconds")
    try:
        parsed = _parse_utc(value)
    except ValueError as exc:
        raise TrustedLocalRequestPreparationError(f"{field} must be a valid UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise TrustedLocalRequestPreparationError(f"{field} must be canonical UTC seconds")
    return value


def _reject_json_constant(value: str) -> None:
    raise TrustedLocalRequestPreparationError(
        f"non-finite JSON number is forbidden: {value}"
    )


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TrustedLocalRequestPreparationError("duplicate JSON key is forbidden")
        result[key] = value
    return result


def _parse_canonical_json[ModelT: BaseModel](
    source: SafeLocalFile,
    model: type[ModelT],
    *,
    field: str,
) -> ModelT:
    raw = source.data
    if not raw or len(raw) > _JSON_MAX_BYTES or raw.startswith(b"\xef\xbb\xbf"):
        raise TrustedLocalRequestPreparationError(f"{field} is not bounded canonical JSON")
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrustedLocalRequestPreparationError(f"{field} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise TrustedLocalRequestPreparationError(f"{field} must contain one JSON object")
    try:
        parsed = model.model_validate_json(raw, strict=True)
    except ValidationError as exc:
        raise TrustedLocalRequestPreparationError(f"{field} violates its strict contract") from exc
    if raw != _canonical_document(parsed):
        raise TrustedLocalRequestPreparationError(f"{field} bytes are not canonical")
    return parsed


def _file_seal(source: SafeLocalFile) -> _FileSeal:
    return _FileSeal(
        path=source.path,
        sha256=source.sha256,
        size_bytes=source.size_bytes,
        identity=source.identity,
    )


def _nearest_git_root(path: Path) -> Path | None:
    cursor = path if os.path.lexists(path) and path.is_dir() else path.parent
    while True:
        try:
            (cursor / ".git").lstat()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise TrustedLocalRequestPreparationError(
                "local path Git isolation could not be checked"
            ) from exc
        else:
            return cursor
        parent = cursor.parent
        if parent == cursor:
            return None
        cursor = parent


def _reject_mutable_alias_path(path: Path, *, field: str) -> None:
    components = path.parts[1:] if path.anchor else path.parts
    for component in components:
        tokens = frozenset(
            filter(None, re.split(r"[^a-z0-9]+", component.casefold()))
        )
        if tokens & _MUTABLE_ALIAS_TOKENS:
            raise TrustedLocalRequestPreparationError(
                f"{field} cannot use a mutable alias path"
            )


def _safe_absolute(path: Path, *, must_exist: bool, field: str) -> Path:
    if not path.is_absolute():
        raise TrustedLocalRequestPreparationError(f"{field} must be an absolute local path")
    _reject_mutable_alias_path(path, field=field)
    try:
        absolute = validate_local_path(path, must_exist=must_exist)
        if not must_exist:
            validate_local_path(absolute.parent, must_exist=True)
    except (CreativeMediaError, OSError) as exc:
        raise TrustedLocalRequestPreparationError(f"{field} is not a safe local path") from exc
    _reject_mutable_alias_path(absolute, field=field)
    if _nearest_git_root(absolute) is not None:
        raise TrustedLocalRequestPreparationError(f"{field} must remain outside every Git tree")
    return absolute


def _read_safe(path: Path, *, max_bytes: int, field: str) -> SafeLocalFile:
    absolute = _safe_absolute(path, must_exist=True, field=field)
    try:
        return read_safe_local_file(absolute, max_bytes=max_bytes)
    except RealAssetMediaError as exc:
        raise TrustedLocalRequestPreparationError(
            f"{field} must be one stable non-linked local file"
        ) from exc


def _assert_same_file(before: _FileSeal, after: _FileSeal, *, field: str) -> None:
    if before != after:
        raise TrustedLocalRequestPreparationError(f"{field} drifted during local verification")


def _read_canonical_with_loader[ModelT: BaseModel](
    path: Path,
    model: type[ModelT],
    loader: Callable[[Path], ModelT],
    *,
    field: str,
) -> tuple[ModelT, _FileSeal]:
    first = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field=field)
    parsed = _parse_canonical_json(first, model, field=field)
    try:
        loaded = loader(first.path)
    except (RealAssetReviewV2Error, RealAssetIntakeError, ValidationError) as exc:
        raise TrustedLocalRequestPreparationError(
            f"{field} failed independent strict loading"
        ) from exc
    second = _read_safe(first.path, max_bytes=_JSON_MAX_BYTES, field=field)
    _assert_same_file(_file_seal(first), _file_seal(second), field=field)
    if loaded != parsed:
        raise TrustedLocalRequestPreparationError(f"{field} loaders disagree")
    return parsed, _file_seal(first)


def _read_request(path: Path) -> tuple[CreativeSampleRealAssetQualificationRequestV2, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field="qualification request")
    try:
        request = parse_real_asset_qualification_request_v2_json(source.data)
    except RealAssetQualificationV2Error as exc:
        raise TrustedLocalRequestPreparationError(
            "qualification request violates its strict contract"
        ) from exc
    if source.data != _canonical_document(request):
        raise TrustedLocalRequestPreparationError("qualification request bytes are not canonical")
    return request, _file_seal(source)


def _directory_identity(path: Path, *, field: str) -> tuple[int, int, int, int]:
    try:
        info = path.lstat()
    except OSError as exc:
        raise TrustedLocalRequestPreparationError(f"{field} could not be inspected") from exc
    attributes = int(getattr(info, "st_file_attributes", 0))
    is_junction = getattr(path, "is_junction", None)
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_ISLNK(info.st_mode)
        or bool(attributes & 0x400)
        or bool(is_junction is not None and is_junction())
    ):
        raise TrustedLocalRequestPreparationError(f"{field} must be one non-linked directory")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _assert_separate_request_parent(
    parent: Path,
    paths: TrustedLocalRequestPaths,
) -> None:
    external_parents = tuple(
        path.parent
        for path in (
            paths.evidence_bundle,
            paths.reviewer_a,
            paths.reviewer_b,
            paths.pair_check,
            paths.evidence_retained_record,
            paths.evidence_preparer_ref,
            paths.reviewer_a_retained_record,
            paths.reviewer_b_retained_record,
        )
    )
    if _paths_overlap(parent, paths.pack_root) or any(
        _paths_overlap(parent, external_parent)
        for external_parent in external_parents
    ):
        raise TrustedLocalRequestPreparationError(
            "request parent must use a separate non-intersecting trust area"
        )


def _normalize_paths(paths: TrustedLocalRequestPaths) -> TrustedLocalRequestPaths:
    pack_root = _safe_absolute(paths.pack_root, must_exist=True, field="frozen Pack root")
    if not pack_root.is_dir():
        raise TrustedLocalRequestPreparationError("frozen Pack root must be a directory")
    pack_manifest = _safe_absolute(
        paths.pack_manifest,
        must_exist=True,
        field="frozen Pack manifest",
    )
    if pack_manifest != pack_root / _PACK_MANIFEST_NAME:
        raise TrustedLocalRequestPreparationError(
            "frozen Pack manifest must be the exact manifest under the supplied Pack root"
        )
    if len(paths.media_paths) != 14:
        raise TrustedLocalRequestPreparationError("exactly fourteen media paths are required")
    media_paths = tuple(
        _safe_absolute(path, must_exist=True, field=f"frozen media {ordinal}")
        for ordinal, path in enumerate(paths.media_paths)
    )
    external = (
        _safe_absolute(paths.evidence_bundle, must_exist=True, field="Evidence Bundle"),
        _safe_absolute(paths.reviewer_a, must_exist=True, field="Reviewer A contract"),
        _safe_absolute(paths.reviewer_b, must_exist=True, field="Reviewer B contract"),
        _safe_absolute(paths.pair_check, must_exist=True, field="PairCheck contract"),
        _safe_absolute(
            paths.evidence_retained_record,
            must_exist=True,
            field="evidence retained record",
        ),
        _safe_absolute(
            paths.evidence_preparer_ref,
            must_exist=True,
            field="evidence preparer reference",
        ),
        _safe_absolute(
            paths.reviewer_a_retained_record,
            must_exist=True,
            field="Reviewer A retained record",
        ),
        _safe_absolute(
            paths.reviewer_b_retained_record,
            must_exist=True,
            field="Reviewer B retained record",
        ),
    )
    if any(path == pack_root or path.is_relative_to(pack_root) for path in external):
        raise TrustedLocalRequestPreparationError(
            "contracts and retained records must remain outside the frozen Pack"
        )
    all_named_files = (pack_manifest, *media_paths, *external)
    if len(set(all_named_files)) != len(all_named_files):
        raise TrustedLocalRequestPreparationError("all explicitly named files must be distinct")
    return TrustedLocalRequestPaths(
        pack_root=pack_root,
        pack_manifest=pack_manifest,
        media_paths=media_paths,
        evidence_bundle=external[0],
        reviewer_a=external[1],
        reviewer_b=external[2],
        pair_check=external[3],
        evidence_retained_record=external[4],
        evidence_preparer_ref=external[5],
        reviewer_a_retained_record=external[6],
        reviewer_b_retained_record=external[7],
    )


def _assert_non_aliasing(files: tuple[_FileSeal, ...]) -> None:
    if len({item.path for item in files}) != len(files):
        raise TrustedLocalRequestPreparationError("local inputs contain a path alias")
    physical = {(item.identity[0], item.identity[1]) for item in files}
    if len(physical) != len(files):
        raise TrustedLocalRequestPreparationError("local inputs contain a physical file alias")
    if len({item.sha256 for item in files}) != len(files):
        raise TrustedLocalRequestPreparationError("local inputs contain a byte digest alias")


def _capture_ready(
    paths: TrustedLocalRequestPaths,
    *,
    request_path: Path | None = None,
) -> _ReadySnapshot:
    root_before = _directory_identity(paths.pack_root, field="frozen Pack root")
    try:
        pack = verify_real_asset_candidate_pack(paths.pack_root)
    except (RealAssetIntakeError, RealAssetMediaError, CreativeMediaError) as exc:
        raise TrustedLocalRequestPreparationError("frozen Pack verification failed") from exc
    if pack.root != paths.pack_root or pack.manifest_path != paths.pack_manifest:
        raise TrustedLocalRequestPreparationError("frozen Pack verifier returned a different root")
    root_after_verify = _directory_identity(paths.pack_root, field="frozen Pack root")
    if root_before != root_after_verify:
        raise TrustedLocalRequestPreparationError("frozen Pack root drifted during verification")

    manifest_source = _read_safe(
        paths.pack_manifest,
        max_bytes=_JSON_MAX_BYTES,
        field="frozen Pack manifest",
    )
    manifest = _parse_canonical_json(
        manifest_source,
        CreativeSampleFrozenRealAssetPackManifest,
        field="frozen Pack manifest",
    )
    if manifest != pack.manifest:
        raise TrustedLocalRequestPreparationError("frozen Pack manifest snapshot disagrees")

    expected_media = tuple(
        paths.pack_root.joinpath(*PurePosixPath(item.object_path).parts)
        for item in pack.manifest.objects
    )
    if paths.media_paths != expected_media:
        raise TrustedLocalRequestPreparationError(
            "fourteen media paths must match manifest order and location exactly"
        )
    media_seals: list[_FileSeal] = []
    for ordinal, (path, descriptor) in enumerate(
        zip(paths.media_paths, pack.manifest.objects, strict=True)
    ):
        source = _read_safe(path, max_bytes=_MEDIA_MAX_BYTES, field=f"frozen media {ordinal}")
        if source.sha256 != descriptor.sha256 or source.size_bytes != descriptor.size_bytes:
            raise TrustedLocalRequestPreparationError(
                f"frozen media {ordinal} does not match its manifest identity"
            )
        media_seals.append(_file_seal(source))

    evidence, evidence_seal = _read_canonical_with_loader(
        paths.evidence_bundle,
        CreativeSampleRealAssetRightsEvidenceBundleV2,
        load_real_asset_rights_evidence_bundle_v2,
        field="Evidence Bundle",
    )
    reviewer_a, reviewer_a_seal = _read_canonical_with_loader(
        paths.reviewer_a,
        CreativeSampleRealAssetHumanPackReviewV2,
        load_real_asset_human_pack_review_v2,
        field="Reviewer A contract",
    )
    reviewer_b, reviewer_b_seal = _read_canonical_with_loader(
        paths.reviewer_b,
        CreativeSampleRealAssetHumanPackReviewV2,
        load_real_asset_human_pack_review_v2,
        field="Reviewer B contract",
    )
    pair_check, pair_check_seal = _read_canonical_with_loader(
        paths.pair_check,
        CreativeSampleRealAssetReviewPairCheckV2,
        load_real_asset_review_pair_check_v2,
        field="PairCheck contract",
    )
    if reviewer_a.reviewer_role != "REVIEWER_A" or reviewer_b.reviewer_role != "REVIEWER_B":
        raise TrustedLocalRequestPreparationError("reviewer roles do not match their exact inputs")
    if (
        pair_check.status != "READY_FOR_SEPARATE_QUALIFICATION_REVIEW"
        or pair_check.issue_codes
    ):
        raise TrustedLocalRequestPreparationError("PairCheck is not issue-free and ready")

    evidence_record = _read_safe(
        paths.evidence_retained_record,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="evidence retained record",
    )
    preparer_ref = _read_safe(
        paths.evidence_preparer_ref,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="evidence preparer reference",
    )
    reviewer_a_record = _read_safe(
        paths.reviewer_a_retained_record,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="Reviewer A retained record",
    )
    reviewer_b_record = _read_safe(
        paths.reviewer_b_retained_record,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="Reviewer B retained record",
    )
    if evidence_record.sha256 != evidence.evidence_record_sha256:
        raise TrustedLocalRequestPreparationError("evidence retained record digest disagrees")
    if reviewer_a_record.sha256 != reviewer_a.reviewer_ref_sha256:
        raise TrustedLocalRequestPreparationError("Reviewer A retained record digest disagrees")
    if reviewer_b_record.sha256 != reviewer_b.reviewer_ref_sha256:
        raise TrustedLocalRequestPreparationError("Reviewer B retained record digest disagrees")

    request: CreativeSampleRealAssetQualificationRequestV2 | None = None
    request_seal: _FileSeal | None = None
    if request_path is not None:
        absolute_request = _safe_absolute(
            request_path,
            must_exist=True,
            field="qualification request",
        )
        if absolute_request == paths.pack_root or absolute_request.is_relative_to(paths.pack_root):
            raise TrustedLocalRequestPreparationError(
                "qualification request must remain outside the frozen Pack"
            )
        named_inputs = (
            paths.pack_manifest,
            *paths.media_paths,
            paths.evidence_bundle,
            paths.reviewer_a,
            paths.reviewer_b,
            paths.pair_check,
            paths.evidence_retained_record,
            paths.evidence_preparer_ref,
            paths.reviewer_a_retained_record,
            paths.reviewer_b_retained_record,
        )
        if any(_paths_overlap(absolute_request, path) for path in named_inputs):
            raise TrustedLocalRequestPreparationError(
                "qualification request must not alias an immutable input"
            )
        _assert_separate_request_parent(absolute_request.parent, paths)
        request, request_seal = _read_request(absolute_request)

    files = (
        _file_seal(manifest_source),
        *media_seals,
        evidence_seal,
        reviewer_a_seal,
        reviewer_b_seal,
        pair_check_seal,
        _file_seal(evidence_record),
        _file_seal(preparer_ref),
        _file_seal(reviewer_a_record),
        _file_seal(reviewer_b_record),
        *((request_seal,) if request_seal is not None else ()),
    )
    _assert_non_aliasing(files)
    root_after = _directory_identity(paths.pack_root, field="frozen Pack root")
    if root_before != root_after:
        raise TrustedLocalRequestPreparationError("frozen Pack root drifted during verification")
    return _ReadySnapshot(
        pack=pack,
        pack_root_identity=root_before,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        evidence_retained_record=_file_seal(evidence_record),
        evidence_preparer_ref=_file_seal(preparer_ref),
        reviewer_a_retained_record=_file_seal(reviewer_a_record),
        reviewer_b_retained_record=_file_seal(reviewer_b_record),
        files=files,
        request=request,
    )


def _assert_ready_unchanged(before: _ReadySnapshot, after: _ReadySnapshot) -> None:
    if before != after:
        raise TrustedLocalRequestPreparationError(
            "trusted local request inputs drifted during complete verification"
        )


def _build_request(
    snapshot: _ReadySnapshot,
    *,
    requested_at: str,
) -> CreativeSampleRealAssetQualificationRequestV2:
    try:
        return build_real_asset_qualification_request_v2(
            pack=snapshot.pack.manifest,
            evidence=snapshot.evidence,
            reviewer_a=snapshot.reviewer_a,
            reviewer_b=snapshot.reviewer_b,
            pair_check=snapshot.pair_check,
            evidence_preparer_ref_sha256=snapshot.evidence_preparer_ref.sha256,
            requested_at=requested_at,
        )
    except (RealAssetQualificationV2Error, ValidationError, ValueError) as exc:
        raise TrustedLocalRequestPreparationError(
            "zero-authority qualification request could not be rebuilt"
        ) from exc


def _validate_output(
    output_path: Path,
    *,
    paths: TrustedLocalRequestPaths,
) -> _OutputTarget:
    target = _safe_absolute(output_path, must_exist=False, field="request output")
    if os.path.lexists(target):
        raise TrustedLocalRequestPreparationError("request output must be one new file")
    if target.suffix.casefold() != ".json":
        raise TrustedLocalRequestPreparationError("request output must use a JSON filename")
    tokens = frozenset(filter(None, re.split(r"[^a-z0-9]+", target.stem.casefold())))
    if tokens & _MUTABLE_ALIAS_TOKENS:
        raise TrustedLocalRequestPreparationError("request output cannot use a mutable alias name")
    if target == paths.pack_root or target.is_relative_to(paths.pack_root):
        raise TrustedLocalRequestPreparationError("request output must remain outside the Pack")
    inputs = (
        paths.pack_manifest,
        *paths.media_paths,
        paths.evidence_bundle,
        paths.reviewer_a,
        paths.reviewer_b,
        paths.pair_check,
        paths.evidence_retained_record,
        paths.evidence_preparer_ref,
        paths.reviewer_a_retained_record,
        paths.reviewer_b_retained_record,
    )
    if any(_paths_overlap(target, path) for path in inputs):
        raise TrustedLocalRequestPreparationError("request output overlaps an immutable input")
    _assert_separate_request_parent(target.parent, paths)
    parent_identity = _directory_identity(target.parent, field="request output parent")
    return _OutputTarget(
        path=target,
        parent=target.parent,
        parent_physical_identity=(parent_identity[0], parent_identity[1]),
    )


def _revalidate_output_target(target: _OutputTarget, *, must_be_absent: bool) -> None:
    absolute_parent = _safe_absolute(
        target.parent,
        must_exist=True,
        field="request output parent",
    )
    parent_identity = _directory_identity(absolute_parent, field="request output parent")
    if absolute_parent != target.parent or (parent_identity[0], parent_identity[1]) != (
        target.parent_physical_identity
    ):
        raise TrustedLocalRequestPreparationError("request output parent identity drifted")
    if must_be_absent:
        absolute_target = _safe_absolute(
            target.path,
            must_exist=False,
            field="request output",
        )
        if absolute_target != target.path or os.path.lexists(absolute_target):
            raise TrustedLocalRequestPreparationError("request output must remain absent")
    else:
        absolute_target = _safe_absolute(
            target.path,
            must_exist=True,
            field="request output",
        )
        if absolute_target != target.path:
            raise TrustedLocalRequestPreparationError("request output identity drifted")


def _acquire_parent_guard(target: _OutputTarget) -> tuple[int, bool]:
    if sys.platform != "win32":
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
        try:
            return os.open(target.parent, flags), False
        except OSError as exc:
            raise TrustedLocalRequestPreparationError(
                "request output parent could not be guarded"
            ) from exc

    return _acquire_windows_parent_guard(target), True


def _close_parent_guard(created: _CreatedRequest) -> None:
    if created.windows_parent_guard:
        _close_windows_handle(created.parent_guard)
    else:
        os.close(created.parent_guard)


def _open_exclusive_request(target: _OutputTarget, parent_guard: int) -> int:
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    if sys.platform != "win32":
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        return os.open(target.path.name, flags, 0o600, dir_fd=parent_guard)
    return _open_windows_exclusive_request(target)


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _read_open_created_request(
    created: _CreatedRequest,
    request: CreativeSampleRealAssetQualificationRequestV2,
) -> _FileSeal:
    raw = _canonical_document(request)
    try:
        opened = os.fstat(created.descriptor)
        os.lseek(created.descriptor, 0, os.SEEK_SET)
        observed = bytearray()
        while len(observed) <= _JSON_MAX_BYTES:
            chunk = os.read(created.descriptor, min(65_536, _JSON_MAX_BYTES + 1 - len(observed)))
            if not chunk:
                break
            observed.extend(chunk)
        path_info = created.target.path.lstat()
    except OSError as exc:
        raise TrustedLocalRequestPreparationError("created request could not be inspected") from exc
    opened_identity = _stat_identity(opened)
    path_identity = _stat_identity(path_info)
    attributes = int(getattr(path_info, "st_file_attributes", 0))
    if (
        opened_identity != path_identity
        or not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(path_info.st_mode)
        or stat.S_ISLNK(path_info.st_mode)
        or bool(attributes & 0x400)
        or opened.st_nlink != 1
        or path_info.st_nlink != 1
    ):
        raise TrustedLocalRequestPreparationError("created request identity drifted")
    data = bytes(observed)
    source = SafeLocalFile(
        path=created.target.path,
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        identity=opened_identity,
    )
    try:
        loaded = parse_real_asset_qualification_request_v2_json(source.data)
    except RealAssetQualificationV2Error as exc:
        raise TrustedLocalRequestPreparationError(
            "created request violates its strict contract"
        ) from exc
    seal = _file_seal(source)
    if (
        loaded != request
        or source.data != raw
        or seal.sha256 != hashlib.sha256(raw).hexdigest()
        or seal.size_bytes != len(raw)
    ):
        raise TrustedLocalRequestPreparationError("written request failed exact verification")
    return seal


def _rollback_created_request(created: _CreatedRequest) -> None:
    if created.closed:
        return
    invalidated = False
    deleted = False
    try:
        opened = os.fstat(created.descriptor)
        opened_physical = (opened.st_dev, opened.st_ino)
        invalidated = _invalidate_open_request(created.descriptor)
        if sys.platform == "win32":
            deleted = _delete_open_windows_request(created.descriptor)
        else:
            deleted = _unlink_open_posix_request(created, opened_physical)
    except OSError:
        deleted = False
    finally:
        try:
            os.close(created.descriptor)
        finally:
            _close_parent_guard(created)
            created.closed = True
    if not invalidated and not deleted:
        raise TrustedLocalRequestPreparationError(
            "created request rollback failed closed"
        )


def _invalidate_open_request(descriptor: int) -> bool:
    try:
        os.ftruncate(descriptor, 0)
        os.fsync(descriptor)
        if os.fstat(descriptor).st_size == 0:
            return True
    except OSError:
        pass
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        if os.write(descriptor, b"\0") != 1:
            return False
        os.fsync(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        return os.read(descriptor, 1) == b"\0"
    except OSError:
        return False


def _unlink_open_posix_request(
    created: _CreatedRequest,
    opened_physical: tuple[int, int],
) -> bool:
    try:
        named = os.stat(
            created.target.path.name,
            dir_fd=created.parent_guard,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return True
    if (named.st_dev, named.st_ino) != opened_physical:
        return False
    try:
        os.unlink(created.target.path.name, dir_fd=created.parent_guard)
    except OSError:
        return False
    return True


def _commit_created_request(
    created: _CreatedRequest,
    request: CreativeSampleRealAssetQualificationRequestV2,
) -> None:
    if created.closed or created.seal is None:
        raise TrustedLocalRequestPreparationError("created request is not publishable")
    _revalidate_output_target(created.target, must_be_absent=False)
    final_seal = _read_open_created_request(created, request)
    if final_seal != created.seal:
        raise TrustedLocalRequestPreparationError("created request drifted before commit")
    _fsync_parent_directory(created)
    os.close(created.descriptor)
    _close_parent_guard(created)
    created.closed = True


def _fsync_parent_directory(created: _CreatedRequest) -> None:
    if not created.windows_parent_guard:
        os.fsync(created.parent_guard)


def _create_new_request(
    target: _OutputTarget,
    request: CreativeSampleRealAssetQualificationRequestV2,
) -> _CreatedRequest:
    _revalidate_output_target(target, must_be_absent=True)
    parent_guard = _acquire_parent_guard(target)
    descriptor: int | None = None
    created: _CreatedRequest | None = None
    try:
        _revalidate_output_target(target, must_be_absent=True)
        descriptor = _open_exclusive_request(target, parent_guard[0])
        created = _CreatedRequest(
            target=target,
            descriptor=descriptor,
            parent_guard=parent_guard[0],
            windows_parent_guard=parent_guard[1],
        )
        raw = _canonical_document(request)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise OSError("short write")
            offset += written
        os.fsync(descriptor)
        created.seal = _read_open_created_request(created, request)
        _revalidate_output_target(target, must_be_absent=False)
        return created
    except FileExistsError as exc:
        if descriptor is None:
            if parent_guard[1]:
                _close_windows_handle(parent_guard[0])
            else:
                os.close(parent_guard[0])
        raise TrustedLocalRequestPreparationError("request output must be one new file") from exc
    except Exception as exc:
        if created is not None:
            _rollback_created_request(created)
        else:
            if parent_guard[1]:
                _close_windows_handle(parent_guard[0])
            else:
                os.close(parent_guard[0])
        if isinstance(exc, TrustedLocalRequestPreparationError):
            raise
        raise TrustedLocalRequestPreparationError("request output could not be created") from exc


def inspect_ready(
    paths: TrustedLocalRequestPaths,
    *,
    requested_at: str,
) -> CreativeSampleRealAssetQualificationRequestV2:
    """Read and rebuild an issue-free request in memory, with no filesystem writes."""

    requested_at = _canonical_utc_seconds(requested_at, field="requested_at")
    normalized = _normalize_paths(paths)
    before = _capture_ready(normalized)
    request = _build_request(before, requested_at=requested_at)
    after = _capture_ready(normalized)
    _assert_ready_unchanged(before, after)
    return request


def prepare_request(
    paths: TrustedLocalRequestPaths,
    output_path: Path,
    *,
    requested_at: str,
) -> CreativeSampleRealAssetQualificationRequestV2:
    """Create one canonical request new-only, then reverify every immutable input."""

    requested_at = _canonical_utc_seconds(requested_at, field="requested_at")
    normalized = _normalize_paths(paths)
    target = _validate_output(output_path, paths=normalized)
    before = _capture_ready(normalized)
    request = _build_request(before, requested_at=requested_at)
    immediately_before_write = _capture_ready(normalized)
    _assert_ready_unchanged(before, immediately_before_write)
    created: _CreatedRequest | None = None
    try:
        created = _create_new_request(target, request)
        assert created.seal is not None
        if created.seal.sha256 in {item.sha256 for item in before.files}:
            raise TrustedLocalRequestPreparationError("written request aliases an immutable input")
        after = _capture_ready(normalized)
        _assert_ready_unchanged(before, after)
        _commit_created_request(created, request)
    except Exception as exc:
        if created is not None:
            _rollback_created_request(created)
        if isinstance(exc, TrustedLocalRequestPreparationError):
            raise
        raise TrustedLocalRequestPreparationError(
            "request publication failed closed"
        ) from exc
    return request


def verify_request(
    paths: TrustedLocalRequestPaths,
    request_path: Path,
    *,
    observed_at: str,
) -> CreativeSampleRealAssetQualificationRequestV2:
    """Rebuild one existing canonical request and verify its current finite validity."""

    observed_at = _canonical_utc_seconds(observed_at, field="observed_at")
    normalized = _normalize_paths(paths)
    before = _capture_ready(normalized, request_path=request_path)
    request = before.request
    if request is None:
        raise TrustedLocalRequestPreparationError("qualification request is missing")
    now = _parse_utc(observed_at)
    if _parse_utc(request.requested_at) > now:
        raise TrustedLocalRequestPreparationError("qualification request is from the future")
    if now >= _parse_utc(request.request_valid_until):
        raise TrustedLocalRequestPreparationError("qualification request is expired")
    rebuilt = _build_request(before, requested_at=request.requested_at)
    if rebuilt != request:
        raise TrustedLocalRequestPreparationError("qualification request does not exactly rebuild")
    after = _capture_ready(normalized, request_path=request_path)
    _assert_ready_unchanged(before, after)
    return request


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pack-root", required=True, type=Path)
    parser.add_argument("--pack-manifest", required=True, type=Path)
    parser.add_argument("--media-path", required=True, action="append", type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--reviewer-a", required=True, type=Path)
    parser.add_argument("--reviewer-b", required=True, type=Path)
    parser.add_argument("--pair-check", required=True, type=Path)
    parser.add_argument("--evidence-retained-record", required=True, type=Path)
    parser.add_argument("--evidence-preparer-ref", required=True, type=Path)
    parser.add_argument("--reviewer-a-retained-record", required=True, type=Path)
    parser.add_argument("--reviewer-b-retained-record", required=True, type=Path)


def _paths_from_namespace(args: argparse.Namespace) -> TrustedLocalRequestPaths:
    return TrustedLocalRequestPaths(
        pack_root=cast(Path, args.pack_root),
        pack_manifest=cast(Path, args.pack_manifest),
        media_paths=tuple(cast(list[Path], args.media_path)),
        evidence_bundle=cast(Path, args.evidence),
        reviewer_a=cast(Path, args.reviewer_a),
        reviewer_b=cast(Path, args.reviewer_b),
        pair_check=cast(Path, args.pair_check),
        evidence_retained_record=cast(Path, args.evidence_retained_record),
        evidence_preparer_ref=cast(Path, args.evidence_preparer_ref),
        reviewer_a_retained_record=cast(Path, args.reviewer_a_retained_record),
        reviewer_b_retained_record=cast(Path, args.reviewer_b_retained_record),
    )


def _safe_summary(
    operation: str,
    request: CreativeSampleRealAssetQualificationRequestV2,
) -> str:
    payload: dict[str, object] = {
        "current_gate": request.current_gate,
        "execution_authorized": request.execution_authorized,
        "operation": operation,
        "posts_allowed": request.posts_allowed,
        "provider_requests": request.provider_requests,
        "provider_state": request.provider_state,
        "rights_manifest_created": request.rights_manifest_created,
        "rights_qualification_performed": request.rights_qualification_performed,
        "status": (
            "READY_FOR_REQUEST_PREPARATION"
            if operation == "inspect-ready"
            else request.status
        ),
    }
    if operation != "inspect-ready":
        payload["request_id"] = request.request_id
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _FailClosedArgumentParser(
        description="Prepare or verify one zero-authority local qualification request"
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=_FailClosedArgumentParser,
    )
    inspect_parser = commands.add_parser("inspect-ready")
    _add_common_arguments(inspect_parser)
    inspect_parser.add_argument("--requested-at", required=True)
    prepare_parser = commands.add_parser("prepare-request")
    _add_common_arguments(prepare_parser)
    prepare_parser.add_argument("--output", required=True, type=Path)
    prepare_parser.add_argument("--requested-at", required=True)
    verify_parser = commands.add_parser("verify-request")
    _add_common_arguments(verify_parser)
    verify_parser.add_argument("--request", required=True, type=Path)
    verify_parser.add_argument("--observed-at", required=True)
    try:
        args = parser.parse_args(argv)
        paths = _paths_from_namespace(args)
        if args.command == "inspect-ready":
            request = inspect_ready(paths, requested_at=cast(str, args.requested_at))
        elif args.command == "prepare-request":
            request = prepare_request(
                paths,
                cast(Path, args.output),
                requested_at=cast(str, args.requested_at),
            )
        else:
            request = verify_request(
                paths,
                cast(Path, args.request),
                observed_at=cast(str, args.observed_at),
            )
    except Exception:
        print(
            '{"current_gate":"HUMAN_GATE","execution_authorized":false,'
            '"posts_allowed":0,"provider_requests":0,"provider_state":"NOT_AUTHORIZED",'
            '"status":"FAILED_CLOSED"}',
            file=sys.stderr,
        )
        return 2
    print(_safe_summary(args.command, request))
    return 0


__all__ = [
    "TrustedLocalRequestPaths",
    "TrustedLocalRequestPreparationError",
    "inspect_ready",
    "main",
    "prepare_request",
    "verify_request",
]


if __name__ == "__main__":
    raise SystemExit(main())
