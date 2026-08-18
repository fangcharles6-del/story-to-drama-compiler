"""Trusted local finalization of one Pack Review v2 qualification decision.

The three operations in this module consume only explicitly named local files.  They never scan
for inputs, read a clock, create a rights manifest, authorize execution, or contact a runtime or
Provider.  A retained, canonical decision instruction supplies all decision-bearing content;
none of that content is accepted from command-line arguments, environment variables, or stdin.
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
from sdc.real_asset_qualification_decision_instruction_v22 import (
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
)
from sdc.real_asset_qualification_preparer_v21 import (
    TrustedLocalRequestPaths,
    TrustedLocalRequestPreparationError,
    verify_request,
)
from sdc.real_asset_qualification_v2 import (
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationRequestV2,
    RealAssetQualificationV2Error,
    build_real_asset_qualification_decision_v2,
    build_real_asset_qualification_request_v2,
    parse_real_asset_qualification_decision_v2_json,
    parse_real_asset_qualification_request_v2_json,
    verify_real_asset_qualification_closure_v2,
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
_OUTCOME_FILENAME_TOKENS = frozenset({"needs", "pass", "rejected"})
_UTC_SECONDS = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)


class TrustedLocalDecisionFinalizationError(RuntimeError):
    """The local decision finalizer failed closed."""


class TrustedLocalDecisionQuarantineRequired(TrustedLocalDecisionFinalizationError):
    """Rollback could not prove invalidation or deletion of the exact created artifact."""


class _CliArgumentError(RuntimeError):
    pass


class _FailClosedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        del message
        raise _CliArgumentError


@dataclass(frozen=True, slots=True)
class TrustedLocalDecisionPaths:
    """Every explicit immutable path required to finalize or verify one decision."""

    request_inputs: TrustedLocalRequestPaths
    request: Path
    qualifier_ref: Path
    qualifier_decision_record: Path


@dataclass(frozen=True, slots=True)
class _FileSeal:
    path: Path
    sha256: str
    size_bytes: int
    identity: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class _DecisionSnapshot:
    pack: FrozenRealAssetPack
    pack_root_identity: tuple[int, int, int, int]
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2
    pair_check: CreativeSampleRealAssetReviewPairCheckV2
    request: CreativeSampleRealAssetQualificationRequestV2
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22
    qualifier_ref: _FileSeal
    qualifier_record: _FileSeal
    files: tuple[_FileSeal, ...]
    decision: CreativeSampleRealAssetQualificationDecisionV2 | None = None


@dataclass(frozen=True, slots=True)
class _OutputTarget:
    path: Path
    parent: Path
    parent_physical_identity: tuple[int, int]


@dataclass(slots=True)
class _CreatedDecision:
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
            0x0080,
            0x00000001 | 0x00000002,
            None,
            3,
            0x02000000,
            None,
        )
        invalid = _windows_ctypes.c_void_p(-1).value
        if handle == invalid:
            raise TrustedLocalDecisionFinalizationError(
                "decision output parent could not be guarded"
            )
        return int(handle)

    def _close_windows_handle(handle: int) -> None:
        _windows_ctypes.windll.kernel32.CloseHandle(handle)

    def _open_windows_exclusive_decision(target: _OutputTarget) -> int:
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
            0x80000000 | 0x40000000 | 0x00010000,
            0x00000001,
            None,
            1,
            0x00000080,
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

    def _delete_open_windows_decision(descriptor: int) -> bool:
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
        raise OSError("Windows-only decision output helper is unavailable")

    def _acquire_windows_parent_guard(target: _OutputTarget) -> int:
        del target
        return _windows_unavailable()

    def _close_windows_handle(handle: int) -> None:
        del handle
        _windows_unavailable()

    def _open_windows_exclusive_decision(target: _OutputTarget) -> int:
        del target
        return _windows_unavailable()

    def _delete_open_windows_decision(descriptor: int) -> bool:
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


def _canonical_utc_seconds_model(value: str, *, field: str) -> str:
    if _UTC_SECONDS.fullmatch(value) is None:
        raise ValueError(f"{field} must be canonical UTC seconds")
    try:
        parsed = _parse_utc(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError(f"{field} must be canonical UTC seconds")
    return value


def _canonical_utc_seconds(value: str, *, field: str) -> str:
    try:
        return _canonical_utc_seconds_model(value, field=field)
    except ValueError as exc:
        raise TrustedLocalDecisionFinalizationError(str(exc)) from exc


def _reject_json_constant(value: str) -> None:
    del value
    raise TrustedLocalDecisionFinalizationError("non-finite JSON numbers are forbidden")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TrustedLocalDecisionFinalizationError("duplicate JSON key is forbidden")
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
        raise TrustedLocalDecisionFinalizationError(f"{field} is not bounded canonical JSON")
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrustedLocalDecisionFinalizationError(
            f"{field} is not strict UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        raise TrustedLocalDecisionFinalizationError(f"{field} must contain one JSON object")
    try:
        parsed = model.model_validate_json(raw, strict=True)
    except ValidationError as exc:
        raise TrustedLocalDecisionFinalizationError(
            f"{field} violates its strict contract"
        ) from exc
    if raw != _canonical_document(parsed):
        raise TrustedLocalDecisionFinalizationError(f"{field} bytes are not canonical")
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
            raise TrustedLocalDecisionFinalizationError(
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
        tokens = frozenset(filter(None, re.split(r"[^a-z0-9]+", component.casefold())))
        if tokens & _MUTABLE_ALIAS_TOKENS:
            raise TrustedLocalDecisionFinalizationError(
                f"{field} cannot use a mutable alias path"
            )


def _reject_outcome_filename(path: Path, *, field: str) -> None:
    tokens = frozenset(filter(None, re.split(r"[^a-z0-9]+", path.stem.casefold())))
    if tokens & _OUTCOME_FILENAME_TOKENS:
        raise TrustedLocalDecisionFinalizationError(
            f"{field} filename must not disclose a qualification outcome"
        )


def _safe_absolute(path: Path, *, must_exist: bool, field: str) -> Path:
    if not path.is_absolute():
        raise TrustedLocalDecisionFinalizationError(
            f"{field} must be an absolute local path"
        )
    _reject_mutable_alias_path(path, field=field)
    try:
        absolute = validate_local_path(path, must_exist=must_exist)
        if not must_exist:
            validate_local_path(absolute.parent, must_exist=True)
    except (CreativeMediaError, OSError) as exc:
        raise TrustedLocalDecisionFinalizationError(
            f"{field} is not a safe local path"
        ) from exc
    _reject_mutable_alias_path(absolute, field=field)
    if _nearest_git_root(absolute) is not None:
        raise TrustedLocalDecisionFinalizationError(
            f"{field} must remain outside every Git tree"
        )
    return absolute


def _read_safe(path: Path, *, max_bytes: int, field: str) -> SafeLocalFile:
    absolute = _safe_absolute(path, must_exist=True, field=field)
    try:
        return read_safe_local_file(absolute, max_bytes=max_bytes)
    except RealAssetMediaError as exc:
        raise TrustedLocalDecisionFinalizationError(
            f"{field} must be one stable non-linked local file"
        ) from exc


def _assert_same_file(before: _FileSeal, after: _FileSeal, *, field: str) -> None:
    if before != after:
        raise TrustedLocalDecisionFinalizationError(
            f"{field} drifted during local verification"
        )


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
        raise TrustedLocalDecisionFinalizationError(
            f"{field} failed independent strict loading"
        ) from exc
    second = _read_safe(first.path, max_bytes=_JSON_MAX_BYTES, field=field)
    _assert_same_file(_file_seal(first), _file_seal(second), field=field)
    if loaded != parsed:
        raise TrustedLocalDecisionFinalizationError(f"{field} loaders disagree")
    return parsed, _file_seal(first)


def _read_request(
    path: Path,
) -> tuple[CreativeSampleRealAssetQualificationRequestV2, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field="qualification request")
    try:
        request = parse_real_asset_qualification_request_v2_json(source.data)
    except RealAssetQualificationV2Error as exc:
        raise TrustedLocalDecisionFinalizationError(
            "qualification request violates its strict contract"
        ) from exc
    if source.data != _canonical_document(request):
        raise TrustedLocalDecisionFinalizationError(
            "qualification request bytes are not canonical"
        )
    return request, _file_seal(source)


def _read_instruction(
    path: Path,
) -> tuple[CreativeSampleRealAssetQualificationDecisionInstructionV22, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field="qualifier decision record")
    instruction = _parse_canonical_json(
        source,
        CreativeSampleRealAssetQualificationDecisionInstructionV22,
        field="qualifier decision record",
    )
    return instruction, _file_seal(source)


def _read_decision(
    path: Path,
) -> tuple[CreativeSampleRealAssetQualificationDecisionV2, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field="qualification decision")
    try:
        decision = parse_real_asset_qualification_decision_v2_json(source.data)
    except RealAssetQualificationV2Error as exc:
        raise TrustedLocalDecisionFinalizationError(
            "qualification decision violates its strict contract"
        ) from exc
    if source.data != _canonical_document(decision):
        raise TrustedLocalDecisionFinalizationError(
            "qualification decision bytes are not canonical"
        )
    return decision, _file_seal(source)


def _directory_identity(path: Path, *, field: str) -> tuple[int, int, int, int]:
    try:
        info = path.lstat()
    except OSError as exc:
        raise TrustedLocalDecisionFinalizationError(f"{field} could not be inspected") from exc
    attributes = int(getattr(info, "st_file_attributes", 0))
    is_junction = getattr(path, "is_junction", None)
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_ISLNK(info.st_mode)
        or bool(attributes & 0x400)
        or bool(is_junction is not None and is_junction())
    ):
        raise TrustedLocalDecisionFinalizationError(
            f"{field} must be one non-linked directory"
        )
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _request_external_parents(paths: TrustedLocalRequestPaths) -> tuple[Path, ...]:
    return tuple(
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


def _assert_separate_request_parent(parent: Path, paths: TrustedLocalRequestPaths) -> None:
    if _paths_overlap(parent, paths.pack_root) or any(
        _paths_overlap(parent, external_parent)
        for external_parent in _request_external_parents(paths)
    ):
        raise TrustedLocalDecisionFinalizationError(
            "request parent must use a separate non-intersecting trust area"
        )


def _assert_separate_decision_parent(parent: Path, paths: TrustedLocalDecisionPaths) -> None:
    trust_areas = (
        paths.request_inputs.pack_root,
        *_request_external_parents(paths.request_inputs),
        paths.request.parent,
        paths.qualifier_ref.parent,
        paths.qualifier_decision_record.parent,
    )
    if any(_paths_overlap(parent, area) for area in trust_areas):
        raise TrustedLocalDecisionFinalizationError(
            "decision parent must use a separate non-intersecting trust area"
        )


def _normalize_request_paths(paths: TrustedLocalRequestPaths) -> TrustedLocalRequestPaths:
    pack_root = _safe_absolute(paths.pack_root, must_exist=True, field="frozen Pack root")
    if not pack_root.is_dir():
        raise TrustedLocalDecisionFinalizationError("frozen Pack root must be a directory")
    pack_manifest = _safe_absolute(
        paths.pack_manifest,
        must_exist=True,
        field="frozen Pack manifest",
    )
    if pack_manifest != pack_root / _PACK_MANIFEST_NAME:
        raise TrustedLocalDecisionFinalizationError(
            "frozen Pack manifest must be the exact manifest under the supplied Pack root"
        )
    if len(paths.media_paths) != 14:
        raise TrustedLocalDecisionFinalizationError(
            "exactly fourteen media paths are required"
        )
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
        raise TrustedLocalDecisionFinalizationError(
            "contracts and retained records must remain outside the frozen Pack"
        )
    named = (pack_manifest, *media_paths, *external)
    if len(set(named)) != len(named):
        raise TrustedLocalDecisionFinalizationError(
            "all explicitly named request inputs must be distinct"
        )
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


def _normalize_paths(paths: TrustedLocalDecisionPaths) -> TrustedLocalDecisionPaths:
    request_inputs = _normalize_request_paths(paths.request_inputs)
    request = _safe_absolute(paths.request, must_exist=True, field="qualification request")
    qualifier_ref = _safe_absolute(
        paths.qualifier_ref,
        must_exist=True,
        field="qualifier reference",
    )
    qualifier_record = _safe_absolute(
        paths.qualifier_decision_record,
        must_exist=True,
        field="qualifier decision record",
    )
    _reject_outcome_filename(qualifier_record, field="qualifier decision record")
    for field, path in (
        ("qualification request", request),
        ("qualifier reference", qualifier_ref),
        ("qualifier decision record", qualifier_record),
    ):
        if path == request_inputs.pack_root or path.is_relative_to(request_inputs.pack_root):
            raise TrustedLocalDecisionFinalizationError(
                f"{field} must remain outside the frozen Pack"
            )
    request_named = (
        request_inputs.pack_manifest,
        *request_inputs.media_paths,
        request_inputs.evidence_bundle,
        request_inputs.reviewer_a,
        request_inputs.reviewer_b,
        request_inputs.pair_check,
        request_inputs.evidence_retained_record,
        request_inputs.evidence_preparer_ref,
        request_inputs.reviewer_a_retained_record,
        request_inputs.reviewer_b_retained_record,
    )
    all_named = (*request_named, request, qualifier_ref, qualifier_record)
    if len(set(all_named)) != len(all_named):
        raise TrustedLocalDecisionFinalizationError(
            "all explicitly named decision inputs must be distinct"
        )
    if any(_paths_overlap(request, item) for item in request_named):
        raise TrustedLocalDecisionFinalizationError(
            "qualification request must not alias an immutable input"
        )
    _assert_separate_request_parent(request.parent, request_inputs)
    return TrustedLocalDecisionPaths(
        request_inputs=request_inputs,
        request=request,
        qualifier_ref=qualifier_ref,
        qualifier_decision_record=qualifier_record,
    )


def _assert_non_aliasing(files: tuple[_FileSeal, ...]) -> None:
    if len({item.path for item in files}) != len(files):
        raise TrustedLocalDecisionFinalizationError("local inputs contain a path alias")
    physical = {(item.identity[0], item.identity[1]) for item in files}
    if len(physical) != len(files):
        raise TrustedLocalDecisionFinalizationError(
            "local inputs contain a physical file alias"
        )
    if len({item.sha256 for item in files}) != len(files):
        raise TrustedLocalDecisionFinalizationError(
            "local inputs contain a byte digest alias"
        )


def _reserved_digest_closure(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    request: CreativeSampleRealAssetQualificationRequestV2,
) -> set[str]:
    return {
        hashlib.sha256(_canonical_document(pack)).hexdigest(),
        hashlib.sha256(_canonical_document(evidence)).hexdigest(),
        hashlib.sha256(_canonical_document(reviewer_a)).hexdigest(),
        hashlib.sha256(_canonical_document(reviewer_b)).hexdigest(),
        hashlib.sha256(_canonical_document(pair_check)).hexdigest(),
        hashlib.sha256(_canonical_document(request)).hexdigest(),
        evidence.evidence_record_sha256,
        request.evidence_preparer_ref_sha256,
        reviewer_a.reviewer_ref_sha256,
        reviewer_b.reviewer_ref_sha256,
        reviewer_a.review_record_sha256,
        reviewer_b.review_record_sha256,
        request.policy_document_sha256,
        *(descriptor.sha256 for descriptor in pack.objects),
        *(descriptor.provenance_record_sha256 for descriptor in pack.objects),
        *(descriptor.technical_record_sha256 for descriptor in pack.objects),
    }


def _assert_qualifier_digest_closure(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    request: CreativeSampleRealAssetQualificationRequestV2,
    qualifier_ref_sha256: str,
    qualifier_record_sha256: str,
) -> None:
    reserved = _reserved_digest_closure(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
    )
    if (
        qualifier_ref_sha256 == qualifier_record_sha256
        or qualifier_ref_sha256 in reserved
        or qualifier_record_sha256 in reserved
    ):
        raise TrustedLocalDecisionFinalizationError(
            "qualifier identity and retained instruction must not alias reserved closure digests"
        )


def _verify_request_public(
    paths: TrustedLocalDecisionPaths,
    *,
    observed_at: str,
) -> CreativeSampleRealAssetQualificationRequestV2:
    try:
        return verify_request(
            paths.request_inputs,
            paths.request,
            observed_at=observed_at,
        )
    except TrustedLocalRequestPreparationError as exc:
        raise TrustedLocalDecisionFinalizationError(
            "qualification request closure failed public verification"
        ) from exc


def _assert_request_rebuild(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    request: CreativeSampleRealAssetQualificationRequestV2,
    evidence_preparer_ref_sha256: str,
) -> None:
    try:
        rebuilt = build_real_asset_qualification_request_v2(
            pack=pack,
            evidence=evidence,
            reviewer_a=reviewer_a,
            reviewer_b=reviewer_b,
            pair_check=pair_check,
            evidence_preparer_ref_sha256=evidence_preparer_ref_sha256,
            requested_at=request.requested_at,
        )
    except (RealAssetQualificationV2Error, ValidationError, ValueError) as exc:
        raise TrustedLocalDecisionFinalizationError(
            "qualification request failed an independent in-memory rebuild"
        ) from exc
    if rebuilt != request:
        raise TrustedLocalDecisionFinalizationError(
            "qualification request drifted from the captured upstream closure"
        )


def _capture_ready(
    paths: TrustedLocalDecisionPaths,
    *,
    observed_at: str | None,
    decision_path: Path | None = None,
) -> _DecisionSnapshot:
    instruction, instruction_seal = _read_instruction(paths.qualifier_decision_record)
    request_observed_at = instruction.decision_at if observed_at is None else observed_at
    public_request = _verify_request_public(paths, observed_at=request_observed_at)

    decided_at = _parse_utc(instruction.decision_at)
    requested_at = _parse_utc(public_request.requested_at)
    if decided_at < requested_at:
        raise TrustedLocalDecisionFinalizationError(
            "qualification decision instruction predates its request"
        )
    if observed_at is not None:
        observed = _parse_utc(observed_at)
        if decided_at > observed:
            raise TrustedLocalDecisionFinalizationError(
                "qualification decision instruction is later than observed_at"
            )

    root_before = _directory_identity(paths.request_inputs.pack_root, field="frozen Pack root")
    try:
        pack = verify_real_asset_candidate_pack(paths.request_inputs.pack_root)
    except (RealAssetIntakeError, RealAssetMediaError, CreativeMediaError) as exc:
        raise TrustedLocalDecisionFinalizationError("frozen Pack verification failed") from exc
    if (
        pack.root != paths.request_inputs.pack_root
        or pack.manifest_path != paths.request_inputs.pack_manifest
    ):
        raise TrustedLocalDecisionFinalizationError(
            "frozen Pack verifier returned a different root"
        )
    if root_before != _directory_identity(
        paths.request_inputs.pack_root,
        field="frozen Pack root",
    ):
        raise TrustedLocalDecisionFinalizationError(
            "frozen Pack root drifted during verification"
        )

    manifest_source = _read_safe(
        paths.request_inputs.pack_manifest,
        max_bytes=_JSON_MAX_BYTES,
        field="frozen Pack manifest",
    )
    manifest = _parse_canonical_json(
        manifest_source,
        CreativeSampleFrozenRealAssetPackManifest,
        field="frozen Pack manifest",
    )
    if manifest != pack.manifest:
        raise TrustedLocalDecisionFinalizationError(
            "frozen Pack manifest snapshot disagrees"
        )
    expected_media = tuple(
        paths.request_inputs.pack_root.joinpath(*PurePosixPath(item.object_path).parts)
        for item in pack.manifest.objects
    )
    if paths.request_inputs.media_paths != expected_media:
        raise TrustedLocalDecisionFinalizationError(
            "fourteen media paths must match manifest order and location exactly"
        )
    media_seals: list[_FileSeal] = []
    for ordinal, (path, descriptor) in enumerate(
        zip(paths.request_inputs.media_paths, pack.manifest.objects, strict=True)
    ):
        source = _read_safe(path, max_bytes=_MEDIA_MAX_BYTES, field=f"frozen media {ordinal}")
        if source.sha256 != descriptor.sha256 or source.size_bytes != descriptor.size_bytes:
            raise TrustedLocalDecisionFinalizationError(
                f"frozen media {ordinal} does not match its manifest identity"
            )
        media_seals.append(_file_seal(source))

    evidence, evidence_seal = _read_canonical_with_loader(
        paths.request_inputs.evidence_bundle,
        CreativeSampleRealAssetRightsEvidenceBundleV2,
        load_real_asset_rights_evidence_bundle_v2,
        field="Evidence Bundle",
    )
    reviewer_a, reviewer_a_seal = _read_canonical_with_loader(
        paths.request_inputs.reviewer_a,
        CreativeSampleRealAssetHumanPackReviewV2,
        load_real_asset_human_pack_review_v2,
        field="Reviewer A contract",
    )
    reviewer_b, reviewer_b_seal = _read_canonical_with_loader(
        paths.request_inputs.reviewer_b,
        CreativeSampleRealAssetHumanPackReviewV2,
        load_real_asset_human_pack_review_v2,
        field="Reviewer B contract",
    )
    pair_check, pair_check_seal = _read_canonical_with_loader(
        paths.request_inputs.pair_check,
        CreativeSampleRealAssetReviewPairCheckV2,
        load_real_asset_review_pair_check_v2,
        field="PairCheck contract",
    )
    if reviewer_a.reviewer_role != "REVIEWER_A" or reviewer_b.reviewer_role != "REVIEWER_B":
        raise TrustedLocalDecisionFinalizationError(
            "reviewer roles do not match their exact inputs"
        )
    if (
        pair_check.status != "READY_FOR_SEPARATE_QUALIFICATION_REVIEW"
        or pair_check.issue_codes
    ):
        raise TrustedLocalDecisionFinalizationError(
            "PairCheck is not issue-free and ready"
        )

    evidence_record = _read_safe(
        paths.request_inputs.evidence_retained_record,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="evidence retained record",
    )
    preparer_ref = _read_safe(
        paths.request_inputs.evidence_preparer_ref,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="evidence preparer reference",
    )
    reviewer_a_record = _read_safe(
        paths.request_inputs.reviewer_a_retained_record,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="Reviewer A retained record",
    )
    reviewer_b_record = _read_safe(
        paths.request_inputs.reviewer_b_retained_record,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="Reviewer B retained record",
    )
    if evidence_record.sha256 != evidence.evidence_record_sha256:
        raise TrustedLocalDecisionFinalizationError(
            "evidence retained record digest disagrees"
        )
    if preparer_ref.sha256 != public_request.evidence_preparer_ref_sha256:
        raise TrustedLocalDecisionFinalizationError(
            "evidence preparer reference digest disagrees"
        )
    if reviewer_a_record.sha256 != reviewer_a.reviewer_ref_sha256:
        raise TrustedLocalDecisionFinalizationError(
            "Reviewer A retained record digest disagrees"
        )
    if reviewer_b_record.sha256 != reviewer_b.reviewer_ref_sha256:
        raise TrustedLocalDecisionFinalizationError(
            "Reviewer B retained record digest disagrees"
        )

    request, request_seal = _read_request(paths.request)
    if request != public_request:
        raise TrustedLocalDecisionFinalizationError(
            "qualification request public and local snapshots disagree"
        )
    _assert_request_rebuild(
        pack=pack.manifest,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
        evidence_preparer_ref_sha256=preparer_ref.sha256,
    )
    qualifier_ref = _read_safe(
        paths.qualifier_ref,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="qualifier reference",
    )
    if qualifier_ref.sha256 != instruction.qualifier_ref_sha256:
        raise TrustedLocalDecisionFinalizationError(
            "qualifier reference digest disagrees with its instruction"
        )
    if (
        instruction.request_id != request.request_id
        or instruction.request_sha256 != request_seal.sha256
    ):
        raise TrustedLocalDecisionFinalizationError(
            "qualifier decision instruction does not bind the exact request"
        )
    if (
        instruction.policy_id != request.policy_id
        or instruction.policy_version != request.policy_version
        or instruction.policy_document_sha256 != request.policy_document_sha256
    ):
        raise TrustedLocalDecisionFinalizationError(
            "qualifier decision instruction policy binding disagrees"
        )

    decision: CreativeSampleRealAssetQualificationDecisionV2 | None = None
    decision_seal: _FileSeal | None = None
    if decision_path is not None:
        decision, decision_seal = _read_decision(decision_path)

    instruction_again, instruction_seal_again = _read_instruction(
        paths.qualifier_decision_record
    )
    qualifier_ref_again = _read_safe(
        paths.qualifier_ref,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="qualifier reference",
    )
    _assert_same_file(
        instruction_seal,
        instruction_seal_again,
        field="qualifier decision record",
    )
    _assert_same_file(
        _file_seal(qualifier_ref),
        _file_seal(qualifier_ref_again),
        field="qualifier reference",
    )
    if instruction_again != instruction:
        raise TrustedLocalDecisionFinalizationError(
            "qualifier decision record drifted during parsing"
        )

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
        request_seal,
        _file_seal(qualifier_ref),
        instruction_seal,
        *((decision_seal,) if decision_seal is not None else ()),
    )
    _assert_non_aliasing(files)
    _assert_qualifier_digest_closure(
        pack=pack.manifest,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
        qualifier_ref_sha256=qualifier_ref.sha256,
        qualifier_record_sha256=instruction_seal.sha256,
    )
    if decision_seal is not None and decision_seal.sha256 in _reserved_digest_closure(
        pack=pack.manifest,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
    ):
        raise TrustedLocalDecisionFinalizationError(
            "qualification decision aliases a reserved closure digest"
        )
    root_after = _directory_identity(paths.request_inputs.pack_root, field="frozen Pack root")
    if root_before != root_after:
        raise TrustedLocalDecisionFinalizationError(
            "frozen Pack root drifted during complete verification"
        )
    return _DecisionSnapshot(
        pack=pack,
        pack_root_identity=root_before,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
        instruction=instruction,
        qualifier_ref=_file_seal(qualifier_ref),
        qualifier_record=instruction_seal,
        files=files,
        decision=decision,
    )


def _assert_ready_unchanged(before: _DecisionSnapshot, after: _DecisionSnapshot) -> None:
    if before != after:
        raise TrustedLocalDecisionFinalizationError(
            "trusted local decision inputs drifted during complete verification"
        )


def _build_decision(
    snapshot: _DecisionSnapshot,
) -> CreativeSampleRealAssetQualificationDecisionV2:
    instruction = snapshot.instruction
    try:
        return build_real_asset_qualification_decision_v2(
            pack=snapshot.pack.manifest,
            evidence=snapshot.evidence,
            reviewer_a=snapshot.reviewer_a,
            reviewer_b=snapshot.reviewer_b,
            pair_check=snapshot.pair_check,
            request=snapshot.request,
            qualifier_ref_sha256=snapshot.qualifier_ref.sha256,
            qualifier_record_sha256=snapshot.qualifier_record.sha256,
            decision_at=instruction.decision_at,
            qualification_issue_codes=instruction.qualification_issue_codes,
            qualification_basis=instruction.qualification_basis,
            decision=instruction.decision,
        )
    except (RealAssetQualificationV2Error, ValidationError, ValueError) as exc:
        raise TrustedLocalDecisionFinalizationError(
            "qualification decision could not be built from its retained instruction"
        ) from exc


def _assert_decision_binds_instruction(snapshot: _DecisionSnapshot) -> None:
    decision = snapshot.decision
    if decision is None:
        raise TrustedLocalDecisionFinalizationError("qualification decision is missing")
    instruction = snapshot.instruction
    if (
        decision.request_id != instruction.request_id
        or decision.request_sha256 != instruction.request_sha256
        or decision.policy_id != instruction.policy_id
        or decision.policy_version != instruction.policy_version
        or decision.policy_document_sha256 != instruction.policy_document_sha256
        or decision.qualification_scope != instruction.qualification_scope
        or decision.qualifier_ref_sha256 != instruction.qualifier_ref_sha256
        or decision.qualifier_record_sha256 != snapshot.qualifier_record.sha256
        or decision.decision_at != instruction.decision_at
        or decision.decision != instruction.decision
        or decision.qualification_issue_codes != instruction.qualification_issue_codes
        or decision.qualification_basis != instruction.qualification_basis
    ):
        raise TrustedLocalDecisionFinalizationError(
            "qualification decision does not bind its exact retained instruction"
        )


def _verify_decision_closure(
    snapshot: _DecisionSnapshot,
) -> CreativeSampleRealAssetQualificationDecisionV2:
    _assert_decision_binds_instruction(snapshot)
    assert snapshot.decision is not None
    try:
        return verify_real_asset_qualification_closure_v2(
            pack=snapshot.pack.manifest,
            evidence=snapshot.evidence,
            reviewer_a=snapshot.reviewer_a,
            reviewer_b=snapshot.reviewer_b,
            pair_check=snapshot.pair_check,
            request=snapshot.request,
            decision=snapshot.decision,
        )
    except (RealAssetQualificationV2Error, ValidationError, ValueError) as exc:
        raise TrustedLocalDecisionFinalizationError(
            "qualification decision closure failed exact rebuild"
        ) from exc


def _validate_output(
    output_path: Path,
    *,
    paths: TrustedLocalDecisionPaths,
) -> _OutputTarget:
    target = _safe_absolute(output_path, must_exist=False, field="decision output")
    if os.path.lexists(target):
        raise TrustedLocalDecisionFinalizationError(
            "decision output must be one new file"
        )
    if target.suffix.casefold() != ".json":
        raise TrustedLocalDecisionFinalizationError(
            "decision output must use a JSON filename"
        )
    _reject_outcome_filename(target, field="decision output")
    named = (
        paths.request_inputs.pack_manifest,
        *paths.request_inputs.media_paths,
        paths.request_inputs.evidence_bundle,
        paths.request_inputs.reviewer_a,
        paths.request_inputs.reviewer_b,
        paths.request_inputs.pair_check,
        paths.request_inputs.evidence_retained_record,
        paths.request_inputs.evidence_preparer_ref,
        paths.request_inputs.reviewer_a_retained_record,
        paths.request_inputs.reviewer_b_retained_record,
        paths.request,
        paths.qualifier_ref,
        paths.qualifier_decision_record,
    )
    if any(_paths_overlap(target, item) for item in named):
        raise TrustedLocalDecisionFinalizationError(
            "decision output overlaps an immutable input"
        )
    _assert_separate_decision_parent(target.parent, paths)
    parent_identity = _directory_identity(target.parent, field="decision output parent")
    return _OutputTarget(
        path=target,
        parent=target.parent,
        parent_physical_identity=(parent_identity[0], parent_identity[1]),
    )


def _validate_existing_decision(path: Path, *, paths: TrustedLocalDecisionPaths) -> Path:
    decision = _safe_absolute(path, must_exist=True, field="qualification decision")
    if decision.suffix.casefold() != ".json":
        raise TrustedLocalDecisionFinalizationError(
            "qualification decision must use a JSON filename"
        )
    _reject_outcome_filename(decision, field="qualification decision")
    named = (
        paths.request_inputs.pack_manifest,
        *paths.request_inputs.media_paths,
        paths.request_inputs.evidence_bundle,
        paths.request_inputs.reviewer_a,
        paths.request_inputs.reviewer_b,
        paths.request_inputs.pair_check,
        paths.request_inputs.evidence_retained_record,
        paths.request_inputs.evidence_preparer_ref,
        paths.request_inputs.reviewer_a_retained_record,
        paths.request_inputs.reviewer_b_retained_record,
        paths.request,
        paths.qualifier_ref,
        paths.qualifier_decision_record,
    )
    if any(_paths_overlap(decision, item) for item in named):
        raise TrustedLocalDecisionFinalizationError(
            "qualification decision aliases an immutable input"
        )
    _assert_separate_decision_parent(decision.parent, paths)
    return decision


def _revalidate_output_target(target: _OutputTarget, *, must_be_absent: bool) -> None:
    absolute_parent = _safe_absolute(
        target.parent,
        must_exist=True,
        field="decision output parent",
    )
    parent_identity = _directory_identity(absolute_parent, field="decision output parent")
    if absolute_parent != target.parent or (parent_identity[0], parent_identity[1]) != (
        target.parent_physical_identity
    ):
        raise TrustedLocalDecisionFinalizationError(
            "decision output parent identity drifted"
        )
    if must_be_absent:
        absolute_target = _safe_absolute(
            target.path,
            must_exist=False,
            field="decision output",
        )
        if absolute_target != target.path or os.path.lexists(absolute_target):
            raise TrustedLocalDecisionFinalizationError(
                "decision output must remain absent"
            )
    else:
        absolute_target = _safe_absolute(
            target.path,
            must_exist=True,
            field="decision output",
        )
        if absolute_target != target.path:
            raise TrustedLocalDecisionFinalizationError(
                "decision output identity drifted"
            )


def _acquire_parent_guard(target: _OutputTarget) -> tuple[int, bool]:
    if sys.platform != "win32":
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
        try:
            return os.open(target.parent, flags), False
        except OSError as exc:
            raise TrustedLocalDecisionFinalizationError(
                "decision output parent could not be guarded"
            ) from exc
    return _acquire_windows_parent_guard(target), True


def _close_parent_guard(created: _CreatedDecision) -> None:
    if created.windows_parent_guard:
        _close_windows_handle(created.parent_guard)
    else:
        os.close(created.parent_guard)


def _open_exclusive_decision(target: _OutputTarget, parent_guard: int) -> int:
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    if sys.platform != "win32":
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        return os.open(target.path.name, flags, 0o600, dir_fd=parent_guard)
    return _open_windows_exclusive_decision(target)


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _read_open_created_decision(
    created: _CreatedDecision,
    decision: CreativeSampleRealAssetQualificationDecisionV2,
) -> _FileSeal:
    raw = _canonical_document(decision)
    try:
        opened = os.fstat(created.descriptor)
        os.lseek(created.descriptor, 0, os.SEEK_SET)
        observed = bytearray()
        while len(observed) <= _JSON_MAX_BYTES:
            chunk = os.read(
                created.descriptor,
                min(65_536, _JSON_MAX_BYTES + 1 - len(observed)),
            )
            if not chunk:
                break
            observed.extend(chunk)
        path_info = created.target.path.lstat()
    except OSError as exc:
        raise TrustedLocalDecisionFinalizationError(
            "created decision could not be inspected"
        ) from exc
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
        raise TrustedLocalDecisionFinalizationError(
            "created decision identity drifted"
        )
    data = bytes(observed)
    source = SafeLocalFile(
        path=created.target.path,
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        identity=opened_identity,
    )
    try:
        loaded = parse_real_asset_qualification_decision_v2_json(source.data)
    except RealAssetQualificationV2Error as exc:
        raise TrustedLocalDecisionFinalizationError(
            "created decision violates its strict contract"
        ) from exc
    seal = _file_seal(source)
    if (
        loaded != decision
        or source.data != raw
        or seal.sha256 != hashlib.sha256(raw).hexdigest()
        or seal.size_bytes != len(raw)
    ):
        raise TrustedLocalDecisionFinalizationError(
            "written decision failed exact verification"
        )
    return seal


def _invalidate_open_decision(descriptor: int) -> bool:
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


def _emergency_poison_open_decision(descriptor: int) -> bool:
    """Poison only the retained exact descriptor after the primary invalidation failed."""

    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        if os.write(descriptor, b"\0") != 1:
            return False
        os.fsync(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        return os.read(descriptor, 1) == b"\0"
    except OSError:
        return False


def _unlink_open_posix_decision(
    created: _CreatedDecision,
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


def _rollback_created_decision(created: _CreatedDecision) -> None:
    if created.closed:
        return
    invalidated = False
    deleted = False
    opened_physical: tuple[int, int] | None = None
    try:
        try:
            opened = os.fstat(created.descriptor)
            opened_physical = (opened.st_dev, opened.st_ino)
        except BaseException:
            opened_physical = None
        try:
            invalidated = _invalidate_open_decision(created.descriptor)
        except BaseException:
            invalidated = False
        if not invalidated:
            try:
                invalidated = _emergency_poison_open_decision(created.descriptor)
            except BaseException:
                invalidated = False
        try:
            if sys.platform == "win32":
                deleted = _delete_open_windows_decision(created.descriptor)
            elif opened_physical is not None:
                deleted = _unlink_open_posix_decision(created, opened_physical)
        except BaseException:
            deleted = False
    finally:
        try:
            try:
                os.close(created.descriptor)
            except BaseException:
                pass
        finally:
            try:
                _close_parent_guard(created)
            except BaseException:
                pass
            created.closed = True
    if not invalidated and not deleted:
        raise TrustedLocalDecisionQuarantineRequired(
            "created decision rollback failed closed; output requires quarantine"
        )


def _fsync_parent_directory(created: _CreatedDecision) -> None:
    if not created.windows_parent_guard:
        os.fsync(created.parent_guard)


def _commit_created_decision(
    created: _CreatedDecision,
    decision: CreativeSampleRealAssetQualificationDecisionV2,
) -> None:
    if created.closed or created.seal is None:
        raise TrustedLocalDecisionFinalizationError(
            "created decision is not publishable"
        )
    _revalidate_output_target(created.target, must_be_absent=False)
    final_seal = _read_open_created_decision(created, decision)
    if final_seal != created.seal:
        raise TrustedLocalDecisionFinalizationError(
            "created decision drifted before commit"
        )
    _fsync_parent_directory(created)
    os.close(created.descriptor)
    _close_parent_guard(created)
    created.closed = True


def _create_new_decision(
    target: _OutputTarget,
    decision: CreativeSampleRealAssetQualificationDecisionV2,
) -> _CreatedDecision:
    _revalidate_output_target(target, must_be_absent=True)
    parent_guard = _acquire_parent_guard(target)
    descriptor: int | None = None
    created: _CreatedDecision | None = None
    try:
        _revalidate_output_target(target, must_be_absent=True)
        descriptor = _open_exclusive_decision(target, parent_guard[0])
        created = _CreatedDecision(
            target=target,
            descriptor=descriptor,
            parent_guard=parent_guard[0],
            windows_parent_guard=parent_guard[1],
        )
        raw = _canonical_document(decision)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise OSError("short write")
            offset += written
        os.fsync(descriptor)
        created.seal = _read_open_created_decision(created, decision)
        _revalidate_output_target(target, must_be_absent=False)
        return created
    except FileExistsError as exc:
        if descriptor is None:
            if parent_guard[1]:
                _close_windows_handle(parent_guard[0])
            else:
                os.close(parent_guard[0])
        raise TrustedLocalDecisionFinalizationError(
            "decision output must be one new file"
        ) from exc
    except BaseException as exc:
        if created is not None:
            try:
                _rollback_created_decision(created)
            except TrustedLocalDecisionFinalizationError:
                raise
        else:
            try:
                if parent_guard[1]:
                    _close_windows_handle(parent_guard[0])
                else:
                    os.close(parent_guard[0])
            except BaseException:
                pass
        if isinstance(exc, TrustedLocalDecisionFinalizationError):
            raise
        if isinstance(exc, Exception):
            raise TrustedLocalDecisionFinalizationError(
                "decision output could not be created"
            ) from exc
        raise


def inspect_decision_ready(
    paths: TrustedLocalDecisionPaths,
    *,
    observed_at: str,
) -> CreativeSampleRealAssetQualificationDecisionInstructionV22:
    """Verify decision readiness twice without building a decision or writing a file."""

    observed_at = _canonical_utc_seconds(observed_at, field="observed_at")
    normalized = _normalize_paths(paths)
    before = _capture_ready(normalized, observed_at=observed_at)
    after = _capture_ready(normalized, observed_at=observed_at)
    _assert_ready_unchanged(before, after)
    return before.instruction


def finalize_decision(
    paths: TrustedLocalDecisionPaths,
    output_path: Path,
    *,
    observed_at: str,
) -> CreativeSampleRealAssetQualificationDecisionV2:
    """Create one canonical decision new-only after three complete input snapshots."""

    observed_at = _canonical_utc_seconds(observed_at, field="observed_at")
    normalized = _normalize_paths(paths)
    target = _validate_output(output_path, paths=normalized)
    before = _capture_ready(normalized, observed_at=observed_at)
    immediately_before_write = _capture_ready(normalized, observed_at=observed_at)
    _assert_ready_unchanged(before, immediately_before_write)
    decision = _build_decision(immediately_before_write)
    created: _CreatedDecision | None = None
    try:
        created = _create_new_decision(target, decision)
        assert created.seal is not None
        reserved = _reserved_digest_closure(
            pack=before.pack.manifest,
            evidence=before.evidence,
            reviewer_a=before.reviewer_a,
            reviewer_b=before.reviewer_b,
            pair_check=before.pair_check,
            request=before.request,
        ) | {item.sha256 for item in before.files}
        if created.seal.sha256 in reserved:
            raise TrustedLocalDecisionFinalizationError(
                "written decision aliases an immutable input"
            )
        after = _capture_ready(normalized, observed_at=observed_at)
        _assert_ready_unchanged(before, after)
        _commit_created_decision(created, decision)
    except BaseException as exc:
        if created is not None:
            try:
                _rollback_created_decision(created)
            except TrustedLocalDecisionFinalizationError:
                raise
        if isinstance(exc, TrustedLocalDecisionFinalizationError):
            raise
        if isinstance(exc, Exception):
            raise TrustedLocalDecisionFinalizationError(
                "decision publication failed closed"
            ) from exc
        raise
    return decision


def verify_decision(
    paths: TrustedLocalDecisionPaths,
    decision_path: Path,
) -> CreativeSampleRealAssetQualificationDecisionV2:
    """Historically rebuild one existing decision without reading a clock or writing a file."""

    normalized = _normalize_paths(paths)
    decision_path = _validate_existing_decision(decision_path, paths=normalized)
    before = _capture_ready(normalized, observed_at=None, decision_path=decision_path)
    verified = _verify_decision_closure(before)
    after = _capture_ready(normalized, observed_at=None, decision_path=decision_path)
    _assert_ready_unchanged(before, after)
    return verified


def _add_request_arguments(parser: argparse.ArgumentParser) -> None:
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


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    _add_request_arguments(parser)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--qualifier-ref", required=True, type=Path)
    parser.add_argument("--qualifier-decision-record", required=True, type=Path)


def _paths_from_namespace(args: argparse.Namespace) -> TrustedLocalDecisionPaths:
    request_inputs = TrustedLocalRequestPaths(
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
    return TrustedLocalDecisionPaths(
        request_inputs=request_inputs,
        request=cast(Path, args.request),
        qualifier_ref=cast(Path, args.qualifier_ref),
        qualifier_decision_record=cast(Path, args.qualifier_decision_record),
    )


def _safe_summary(
    operation: str,
    value: (
        CreativeSampleRealAssetQualificationDecisionInstructionV22
        | CreativeSampleRealAssetQualificationDecisionV2
    ),
) -> str:
    payload: dict[str, object] = {
        "current_gate": value.current_gate,
        "execution_authorized": value.execution_authorized,
        "operation": operation,
        "posts_allowed": value.posts_allowed,
        "provider_requests": value.provider_requests,
        "provider_state": value.provider_state,
        "rights_manifest_created": value.rights_manifest_created,
        "rights_qualification_performed": value.rights_qualification_performed,
        "status": (
            "READY_FOR_DECISION_FINALIZATION"
            if operation == "inspect-decision-ready"
            else value.status
        ),
    }
    if isinstance(value, CreativeSampleRealAssetQualificationDecisionV2):
        payload["decision_id"] = value.decision_id
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _FailClosedArgumentParser(
        description="Finalize or verify one trusted local scoped qualification decision"
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=_FailClosedArgumentParser,
    )
    inspect_parser = commands.add_parser("inspect-decision-ready")
    _add_common_arguments(inspect_parser)
    inspect_parser.add_argument("--observed-at", required=True)
    finalize_parser = commands.add_parser("finalize-decision")
    _add_common_arguments(finalize_parser)
    finalize_parser.add_argument("--output", required=True, type=Path)
    finalize_parser.add_argument("--observed-at", required=True)
    verify_parser = commands.add_parser("verify-decision")
    _add_common_arguments(verify_parser)
    verify_parser.add_argument("--decision-file", required=True, type=Path)
    try:
        args = parser.parse_args(argv)
    except Exception:
        print(
            '{"current_gate":"HUMAN_GATE","execution_authorized":false,'
            '"posts_allowed":0,"provider_requests":0,"provider_state":"NOT_AUTHORIZED",'
            '"rights_manifest_created":false,"status":"FAILED_CLOSED"}',
            file=sys.stderr,
        )
        return 2
    try:
        paths = _paths_from_namespace(args)
        if args.command == "inspect-decision-ready":
            result: (
                CreativeSampleRealAssetQualificationDecisionInstructionV22
                | CreativeSampleRealAssetQualificationDecisionV2
            ) = inspect_decision_ready(
                paths,
                observed_at=cast(str, args.observed_at),
            )
        elif args.command == "finalize-decision":
            result = finalize_decision(
                paths,
                cast(Path, args.output),
                observed_at=cast(str, args.observed_at),
            )
        else:
            result = verify_decision(paths, cast(Path, args.decision_file))
    except TrustedLocalDecisionQuarantineRequired:
        print(
            '{"current_gate":"HUMAN_GATE","execution_authorized":false,'
            '"posts_allowed":0,"provider_requests":0,"provider_state":"NOT_AUTHORIZED",'
            '"rights_manifest_created":false,'
            '"status":"ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"}',
            file=sys.stderr,
        )
        return 3
    except BaseException:
        print(
            '{"current_gate":"HUMAN_GATE","execution_authorized":false,'
            '"posts_allowed":0,"provider_requests":0,"provider_state":"NOT_AUTHORIZED",'
            '"rights_manifest_created":false,"status":"FAILED_CLOSED"}',
            file=sys.stderr,
        )
        return 2
    print(_safe_summary(args.command, result))
    return 0


__all__ = [
    "CreativeSampleRealAssetQualificationDecisionInstructionV22",
    "TrustedLocalDecisionFinalizationError",
    "TrustedLocalDecisionPaths",
    "TrustedLocalDecisionQuarantineRequired",
    "finalize_decision",
    "inspect_decision_ready",
    "main",
    "verify_decision",
]


if __name__ == "__main__":
    raise SystemExit(main())
