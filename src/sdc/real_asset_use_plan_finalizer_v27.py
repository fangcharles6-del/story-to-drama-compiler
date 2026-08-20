"""Trusted-local finalization of one inert real-asset Use Plan v1.

The boundary consumes the complete repository-external v2.5 Rights Manifest closure and the
existing v2.6 pure Use Plan compiler.  It never discovers inputs, reads a clock, contacts a remote
service, or grants Provider, generation, execution, or publication authority.  Only
``finalize-use-plan`` writes, and that operation creates one canonical file exactly once.
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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, Never, cast

from pydantic import BaseModel, ValidationError

import sdc.real_asset_rights_manifest_finalizer_v25 as _manifest_boundary
from sdc.real_asset_rights_manifest_finalizer_v25 import (
    TrustedLocalRightsManifestFinalizationError,
    TrustedLocalRightsManifestPaths,
)
from sdc.real_asset_use_plan_v26 import (
    USE_PLAN_V1_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetUsePlanV1,
    RealAssetUsePlanV26Error,
    build_real_asset_use_plan_v1,
    parse_real_asset_use_plan_v1_json,
    verify_real_asset_use_plan_closure_v1,
)

_PLAN_MAX_BYTES = 4_194_304
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PLAN_ID = re.compile(r"^real_asset_use_plan_v1_[0-9a-f]{20}$")
_OUTCOME_FILENAME_TOKENS = frozenset(
    {"approved", "authorized", "needs", "pass", "rejected", "revision"}
)
_READY_FOR_USE_PLAN_FINALIZATION: Literal["READY_FOR_USE_PLAN_FINALIZATION"] = (
    "READY_FOR_USE_PLAN_FINALIZATION"
)

# Intentional private compatibility surface for the companion Review boundary.  Keeping these
# aliases here gives v2.7 one implementation of the inherited v2.5 path and byte primitives.
_FileSeal = _manifest_boundary._FileSeal
_ManifestSnapshot = _manifest_boundary._ManifestSnapshot
_assert_non_aliasing = _manifest_boundary._assert_non_aliasing
_assert_separate_trust_parent = _manifest_boundary._assert_separate_trust_parent
_directory_identity = _manifest_boundary._directory_identity
_file_seal = _manifest_boundary._file_seal
_manifest_trust_areas = _manifest_boundary._manifest_trust_areas
_paths_overlap = _manifest_boundary._paths_overlap
_read_safe = _manifest_boundary._read_safe
_safe_absolute = _manifest_boundary._safe_absolute


class TrustedLocalUsePlanFinalizationError(RuntimeError):
    """The trusted-local Use Plan v2.7 boundary failed closed."""


class TrustedLocalUsePlanQuarantineRequired(TrustedLocalUsePlanFinalizationError):
    """Rollback could not prove invalidation or deletion of the exact created file."""


class _NativeArtifactCreateNeverSucceeded(OSError):
    """The native create operation returned an explicit failure without a new handle."""


class _IndependentArtifactCreateWinner(FileExistsError):
    """CREATE_NEW/O_EXCL reported an independently created winner."""


class _CliArgumentError(RuntimeError):
    pass


class _FailClosedArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("allow_abbrev", False)
        kwargs.setdefault("add_help", False)
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> Never:
        del message
        raise _CliArgumentError


class _StoreOnce(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        del parser, option_string
        if getattr(namespace, self.dest, None) is not None:
            raise _CliArgumentError
        setattr(namespace, self.dest, values)


@dataclass(frozen=True, slots=True)
class TrustedLocalUsePlanPaths:
    """All twenty-nine explicit entries needed to reconstruct one Use Plan."""

    manifest_sources: TrustedLocalRightsManifestPaths
    rights_manifest: Path


@dataclass(frozen=True, slots=True)
class UsePlanReadinessV27:
    """Bounded, non-authoritative approval anchor for one rebuilt candidate Plan."""

    status: Literal["READY_FOR_USE_PLAN_FINALIZATION"]
    plan_id: str
    plan_sha256: str


@dataclass(frozen=True, slots=True)
class _UsePlanSnapshot:
    manifest_snapshot: _ManifestSnapshot
    use_plan: CreativeSampleRealAssetUsePlanV1 | None = None
    use_plan_seal: _FileSeal | None = None
    link_counts: tuple[int, ...] = ()

    @property
    def files(self) -> tuple[_FileSeal, ...]:
        if self.use_plan_seal is None:
            return self.manifest_snapshot.files
        return (*self.manifest_snapshot.files, self.use_plan_seal)


@dataclass(frozen=True, slots=True)
class _OutputTarget:
    path: Path
    parent: Path
    parent_physical_identity: tuple[int, int]


@dataclass(slots=True)
class _CreatedArtifact:
    target: _OutputTarget
    descriptor: int
    parent_guard: int
    windows_parent_guard: bool
    seal: _FileSeal | None = None
    parent_guard_closed: bool = False
    parent_guard_close_uncertain: bool = False
    descriptor_close_uncertain: bool = False
    closed: bool = False


@dataclass(slots=True)
class _CreateAttemptState:
    native_call_entered: bool = False
    native_never_succeeded: bool = False
    rollback_confirmed: bool = False


_CreatedArtifactHolder = _CreatedArtifact


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


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _reject_outcome_filename(path: Path, *, field: str) -> None:
    tokens = frozenset(filter(None, re.split(r"[^a-z0-9]+", path.stem.casefold())))
    if tokens & _OUTCOME_FILENAME_TOKENS:
        raise TrustedLocalUsePlanFinalizationError(
            f"{field} filename must not disclose a review outcome or authority claim"
        )


def _translate_manifest_error(exc: BaseException, *, message: str) -> Never:
    raise TrustedLocalUsePlanFinalizationError(message) from exc


def _all_use_plan_source_paths(paths: TrustedLocalUsePlanPaths) -> tuple[Path, ...]:
    request = paths.manifest_sources.decision_inputs.request_inputs
    return (
        request.pack_root,
        *_manifest_boundary._all_source_paths(paths.manifest_sources),
        paths.rights_manifest,
    )


def _use_plan_trust_areas(paths: TrustedLocalUsePlanPaths) -> tuple[Path, ...]:
    return (*_manifest_trust_areas(paths.manifest_sources), paths.rights_manifest.parent)


def _normalize_use_plan_paths(paths: TrustedLocalUsePlanPaths) -> TrustedLocalUsePlanPaths:
    if type(paths) is not TrustedLocalUsePlanPaths:
        raise TrustedLocalUsePlanFinalizationError(
            "Use Plan paths must use the exact trusted-local path envelope"
        )
    if type(paths.manifest_sources) is not TrustedLocalRightsManifestPaths or not isinstance(
        paths.rights_manifest, Path
    ):
        raise TrustedLocalUsePlanFinalizationError(
            "Use Plan paths contain an invalid nested source or Manifest path"
        )
    try:
        manifest_sources = _manifest_boundary._normalize_paths(paths.manifest_sources)
        rights_manifest = _manifest_boundary._validate_existing_manifest(
            paths.rights_manifest,
            paths=manifest_sources,
        )
    except (
        TrustedLocalRightsManifestFinalizationError,
        AttributeError,
        TypeError,
        ValueError,
    ) as exc:
        _translate_manifest_error(exc, message="Use Plan physical closure failed path admission")
    normalized = TrustedLocalUsePlanPaths(
        manifest_sources=manifest_sources,
        rights_manifest=rights_manifest,
    )
    if len(_all_use_plan_source_paths(normalized)) != 29:
        raise TrustedLocalUsePlanFinalizationError(
            "Use Plan requires exactly twenty-nine explicit source entries"
        )
    return normalized


def _validate_plan_filename(path: Path, *, field: str) -> None:
    if path.suffix.casefold() != ".json":
        raise TrustedLocalUsePlanFinalizationError(f"{field} must use a JSON filename")
    _reject_outcome_filename(path, field=field)


def _assert_plan_area_isolated(parent: Path, paths: TrustedLocalUsePlanPaths) -> None:
    try:
        _assert_separate_trust_parent(
            parent,
            _use_plan_trust_areas(paths),
            field="Use Plan parent",
        )
    except TrustedLocalRightsManifestFinalizationError as exc:
        _translate_manifest_error(exc, message="Use Plan parent is not an isolated trust area")


def _validate_existing_use_plan(
    use_plan_path: Path,
    *,
    paths: TrustedLocalUsePlanPaths,
) -> Path:
    if not isinstance(use_plan_path, Path):
        raise TrustedLocalUsePlanFinalizationError("existing Use Plan must be one explicit Path")
    try:
        plan = _safe_absolute(use_plan_path, must_exist=True, field="existing Use Plan")
    except TrustedLocalRightsManifestFinalizationError as exc:
        _translate_manifest_error(exc, message="existing Use Plan failed path admission")
    _validate_plan_filename(plan, field="existing Use Plan")
    if any(_paths_overlap(plan, source) for source in _all_use_plan_source_paths(paths)):
        raise TrustedLocalUsePlanFinalizationError("existing Use Plan overlaps an immutable source")
    _assert_plan_area_isolated(plan.parent, paths)
    return plan


def _validate_use_plan_output(
    output_path: Path,
    *,
    paths: TrustedLocalUsePlanPaths,
) -> _OutputTarget:
    if not isinstance(output_path, Path):
        raise TrustedLocalUsePlanFinalizationError("Use Plan output must be one explicit Path")
    try:
        target = _safe_absolute(output_path, must_exist=False, field="Use Plan output")
    except TrustedLocalRightsManifestFinalizationError as exc:
        _translate_manifest_error(exc, message="Use Plan output failed path admission")
    if os.path.lexists(target):
        raise TrustedLocalUsePlanFinalizationError("Use Plan output must be one new file")
    _validate_plan_filename(target, field="Use Plan output")
    if any(_paths_overlap(target, source) for source in _all_use_plan_source_paths(paths)):
        raise TrustedLocalUsePlanFinalizationError("Use Plan output overlaps an immutable source")
    _assert_plan_area_isolated(target.parent, paths)
    try:
        identity = _directory_identity(target.parent, field="Use Plan output parent")
    except TrustedLocalRightsManifestFinalizationError as exc:
        _translate_manifest_error(exc, message="Use Plan output parent could not be guarded")
    return _OutputTarget(
        path=target,
        parent=target.parent,
        parent_physical_identity=(identity[0], identity[1]),
    )


def _revalidate_output_target(target: _OutputTarget, *, must_be_absent: bool) -> None:
    try:
        parent = _safe_absolute(target.parent, must_exist=True, field="artifact output parent")
        identity = _directory_identity(parent, field="artifact output parent")
    except TrustedLocalRightsManifestFinalizationError as exc:
        _translate_manifest_error(
            exc,
            message="artifact output parent identity could not be checked",
        )
    if parent != target.parent or (identity[0], identity[1]) != target.parent_physical_identity:
        raise TrustedLocalUsePlanFinalizationError("artifact output parent identity drifted")
    try:
        path = _safe_absolute(
            target.path,
            must_exist=not must_be_absent,
            field="artifact output",
        )
    except TrustedLocalRightsManifestFinalizationError as exc:
        _translate_manifest_error(exc, message="artifact output identity could not be checked")
    if path != target.path or (must_be_absent and os.path.lexists(path)):
        raise TrustedLocalUsePlanFinalizationError("artifact output identity drifted")


def _parse_use_plan_source(source: object) -> tuple[CreativeSampleRealAssetUsePlanV1, _FileSeal]:
    safe_source = cast(Any, source)
    try:
        use_plan = parse_real_asset_use_plan_v1_json(safe_source.data)
    except (RealAssetUsePlanV26Error, ValidationError, ValueError) as exc:
        raise TrustedLocalUsePlanFinalizationError(
            "existing Use Plan violates its strict contract"
        ) from exc
    if safe_source.data != _canonical_document(use_plan):
        raise TrustedLocalUsePlanFinalizationError("existing Use Plan bytes are not canonical")
    return use_plan, _file_seal(safe_source)


def _safe_metadata_open(path: Path) -> int:
    flags = os.O_RDONLY
    if sys.platform == "win32":
        flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    else:
        required = ("O_NOFOLLOW", "O_CLOEXEC")
        if any(not hasattr(os, name) for name in required):
            raise TrustedLocalUsePlanFinalizationError(
                "POSIX no-follow metadata primitives are unavailable"
            )
        flags |= os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        return os.open(path, flags)
    except OSError as exc:
        raise TrustedLocalUsePlanFinalizationError(
            "captured file could not be reopened for link-count verification"
        ) from exc


def _revalidate_file_link_counts(files: tuple[_FileSeal, ...]) -> tuple[int, ...]:
    link_counts: list[int] = []
    for seal in files:
        descriptor: int | None = None
        try:
            before = seal.path.lstat()
            descriptor = _safe_metadata_open(seal.path)
            opened = os.fstat(descriptor)
            after = seal.path.lstat()
        except (OSError, TrustedLocalUsePlanFinalizationError) as exc:
            raise TrustedLocalUsePlanFinalizationError(
                "captured file link-count identity could not be established"
            ) from exc
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError as exc:
                    raise TrustedLocalUsePlanFinalizationError(
                        "captured file metadata handle could not be closed"
                    ) from exc
        attributes = int(getattr(after, "st_file_attributes", 0))
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(after.st_mode)
            or stat.S_ISLNK(before.st_mode)
            or stat.S_ISLNK(after.st_mode)
            or bool(attributes & 0x400)
            or before.st_nlink != 1
            or opened.st_nlink != 1
            or after.st_nlink != 1
            or _stat_identity(before) != seal.identity
            or _stat_identity(opened) != seal.identity
            or _stat_identity(after) != seal.identity
        ):
            raise TrustedLocalUsePlanFinalizationError(
                "captured file changed identity or link count"
            )
        link_counts.append(opened.st_nlink)
    return tuple(link_counts)


def _capture_use_plan_snapshot(
    paths: TrustedLocalUsePlanPaths,
    *,
    use_plan_path: Path | None = None,
) -> _UsePlanSnapshot:
    try:
        manifest_snapshot = _manifest_boundary._capture_snapshot(
            paths.manifest_sources,
            manifest_at=None,
            manifest_path=paths.rights_manifest,
        )
    except TrustedLocalRightsManifestFinalizationError as exc:
        _translate_manifest_error(exc, message="Use Plan Manifest closure failed exact capture")
    if manifest_snapshot.manifest is None:
        raise TrustedLocalUsePlanFinalizationError(
            "Use Plan capture requires one parsed Rights Manifest"
        )
    if use_plan_path is None:
        return _UsePlanSnapshot(
            manifest_snapshot=manifest_snapshot,
            link_counts=_revalidate_file_link_counts(manifest_snapshot.files),
        )
    try:
        source = _read_safe(
            use_plan_path,
            max_bytes=_PLAN_MAX_BYTES,
            field="existing Use Plan",
        )
    except TrustedLocalRightsManifestFinalizationError as exc:
        _translate_manifest_error(exc, message="existing Use Plan failed bounded capture")
    use_plan, plan_seal = _parse_use_plan_source(source)
    try:
        _assert_non_aliasing((*manifest_snapshot.files, plan_seal))
    except TrustedLocalRightsManifestFinalizationError as exc:
        _translate_manifest_error(exc, message="existing Use Plan aliases its physical closure")
    upstream_snapshot = _UsePlanSnapshot(
        manifest_snapshot=manifest_snapshot,
        use_plan=use_plan,
    )
    if plan_seal.sha256 in _reserved_use_plan_snapshot_digests(upstream_snapshot):
        raise TrustedLocalUsePlanFinalizationError(
            "existing Use Plan aliases an immutable closure digest"
        )
    files = (*manifest_snapshot.files, plan_seal)
    return _UsePlanSnapshot(
        manifest_snapshot=manifest_snapshot,
        use_plan=use_plan,
        use_plan_seal=plan_seal,
        link_counts=_revalidate_file_link_counts(files),
    )


def _assert_use_plan_snapshot_unchanged(
    before: _UsePlanSnapshot,
    after: _UsePlanSnapshot,
) -> None:
    if before != after:
        raise TrustedLocalUsePlanFinalizationError(
            "trusted-local Use Plan inputs drifted during complete verification"
        )


def _reserved_use_plan_snapshot_digests(
    snapshot: _UsePlanSnapshot,
    *,
    exclude_use_plan: bool = False,
) -> set[str]:
    reserved = _manifest_boundary._reserved_snapshot_digests(snapshot.manifest_snapshot)
    reserved.add(USE_PLAN_V1_POLICY_DOCUMENT_SHA256)
    if snapshot.use_plan is not None:
        reserved.update(_normative_use_plan_sha256_values(snapshot.use_plan))
    if snapshot.use_plan_seal is not None and not exclude_use_plan:
        reserved.add(snapshot.use_plan_seal.sha256)
    return reserved


def _normative_use_plan_sha256_values(
    plan: CreativeSampleRealAssetUsePlanV1,
) -> set[str]:
    values: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, member in value.items():
                if (
                    isinstance(key, str)
                    and key.casefold().endswith("sha256")
                    and isinstance(member, str)
                    and _LOWER_SHA256.fullmatch(member) is not None
                ):
                    values.add(member)
                visit(member)
        elif isinstance(value, (list, tuple)):
            for member in value:
                visit(member)

    visit(plan.model_dump(mode="json"))
    values.add(USE_PLAN_V1_POLICY_DOCUMENT_SHA256)
    return values


def _build_use_plan(snapshot: _UsePlanSnapshot) -> CreativeSampleRealAssetUsePlanV1:
    manifest = snapshot.manifest_snapshot.manifest
    if manifest is None:
        raise TrustedLocalUsePlanFinalizationError("Rights Manifest is missing from the snapshot")
    try:
        plan = build_real_asset_use_plan_v1(
            pack=snapshot.manifest_snapshot.pack.manifest,
            evidence=snapshot.manifest_snapshot.evidence,
            reviewer_a=snapshot.manifest_snapshot.reviewer_a,
            reviewer_b=snapshot.manifest_snapshot.reviewer_b,
            pair_check=snapshot.manifest_snapshot.pair_check,
            qualification_request=snapshot.manifest_snapshot.request,
            qualification_instruction=snapshot.manifest_snapshot.instruction,
            qualification_decision=snapshot.manifest_snapshot.decision,
            rights_manifest=manifest,
        )
    except (RealAssetUsePlanV26Error, ValidationError, ValueError) as exc:
        raise TrustedLocalUsePlanFinalizationError(
            "Use Plan could not be built from the exact stable closure"
        ) from exc
    _assert_use_plan_candidate(plan, snapshot=snapshot)
    return plan


def _assert_use_plan_candidate(
    plan: CreativeSampleRealAssetUsePlanV1,
    *,
    snapshot: _UsePlanSnapshot,
) -> None:
    raw = _canonical_document(plan)
    if not raw or len(raw) > _PLAN_MAX_BYTES:
        raise TrustedLocalUsePlanFinalizationError("candidate Use Plan exceeds its fixed bound")
    try:
        reparsed = parse_real_asset_use_plan_v1_json(raw)
    except (RealAssetUsePlanV26Error, ValidationError, ValueError) as exc:
        raise TrustedLocalUsePlanFinalizationError(
            "candidate Use Plan violates its strict contract"
        ) from exc
    if reparsed != plan:
        raise TrustedLocalUsePlanFinalizationError(
            "candidate Use Plan changes during canonical revalidation"
        )
    if (
        plan.status != "USE_PLAN_CANDIDATE_CREATED"
        or plan.rights_qualification_performed is not True
        or plan.rights_manifest_created is not True
        or plan.use_scope_review_performed is not False
        or plan.eligible_for_separate_use_scope_review is not True
        or plan.eligible_for_separate_provider_proposal is not False
        or plan.current_gate != "HUMAN_GATE"
        or plan.provider_state != "NOT_AUTHORIZED"
        or plan.eligible_for_separate_provider_approval is not False
        or plan.provider_approval_granted is not False
        or plan.eligible_for_real_generation is not False
        or plan.generation_authorized is not False
        or plan.execution_authorized is not False
        or plan.publication_authorized is not False
        or plan.remote_processing_allowed is not False
        or plan.retention_allowed is not False
        or plan.training_allowed is not False
        or plan.publication_allowed is not False
        or plan.authorized_attempts != 0
        or plan.authorized_cost_cny != 0
        or plan.posts_allowed != 0
        or plan.provider_requests != 0
        or len(plan.media_mappings) != 14
        or plan.shot_count != 10
        or plan.proposed_provider_requests_max != 20
        or plan.proposed_cost_ceiling_cny != 450
    ):
        raise TrustedLocalUsePlanFinalizationError(
            "candidate Use Plan violates fixed zero-authority policy"
        )
    if _sha256(raw) in _reserved_use_plan_snapshot_digests(
        snapshot,
        exclude_use_plan=True,
    ) | _normative_use_plan_sha256_values(plan):
        raise TrustedLocalUsePlanFinalizationError(
            "candidate Use Plan aliases an immutable source digest"
        )


def _verify_use_plan_snapshot(snapshot: _UsePlanSnapshot) -> CreativeSampleRealAssetUsePlanV1:
    manifest = snapshot.manifest_snapshot.manifest
    use_plan = snapshot.use_plan
    if manifest is None or use_plan is None:
        raise TrustedLocalUsePlanFinalizationError(
            "historical verification requires one complete Plan snapshot"
        )
    try:
        verified = verify_real_asset_use_plan_closure_v1(
            pack=snapshot.manifest_snapshot.pack.manifest,
            evidence=snapshot.manifest_snapshot.evidence,
            reviewer_a=snapshot.manifest_snapshot.reviewer_a,
            reviewer_b=snapshot.manifest_snapshot.reviewer_b,
            pair_check=snapshot.manifest_snapshot.pair_check,
            qualification_request=snapshot.manifest_snapshot.request,
            qualification_instruction=snapshot.manifest_snapshot.instruction,
            qualification_decision=snapshot.manifest_snapshot.decision,
            rights_manifest=manifest,
            use_plan=use_plan,
        )
    except (RealAssetUsePlanV26Error, ValidationError, ValueError) as exc:
        raise TrustedLocalUsePlanFinalizationError(
            "Use Plan failed exact historical reconstruction"
        ) from exc
    if verified != use_plan or _canonical_document(verified) != _canonical_document(use_plan):
        raise TrustedLocalUsePlanFinalizationError(
            "Use Plan verifier returned a different document"
        )
    _assert_use_plan_candidate(verified, snapshot=snapshot)
    return verified


def _strict_path_is_absent(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    except BaseException:
        return False
    return False


if sys.platform == "win32":
    import ctypes as _windows_ctypes
    import msvcrt as _windows_msvcrt
    from ctypes import wintypes as _windows_wintypes

    _INVALID_HANDLE_VALUE = _windows_ctypes.c_void_p(-1).value
    _FILE_ALL_ACCESS = 0x001F01FF
    _HANDLE_FLAG_INHERIT = 0x00000001
    _OWNER_SECURITY_INFORMATION = 0x00000001
    _DACL_SECURITY_INFORMATION = 0x00000004
    _SE_DACL_PRESENT = 0x0004
    _SE_DACL_PROTECTED = 0x1000
    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _GENERIC_EXECUTE = 0x20000000
    _GENERIC_ALL = 0x10000000
    _FILE_GENERIC_READ = 0x00120089
    _FILE_GENERIC_WRITE = 0x00120116
    _FILE_GENERIC_EXECUTE = 0x001200A0

    class _SecurityAttributes(_windows_ctypes.Structure):
        _fields_ = (
            ("nLength", _windows_wintypes.DWORD),
            ("lpSecurityDescriptor", _windows_wintypes.LPVOID),
            ("bInheritHandle", _windows_wintypes.BOOL),
        )

    class _AclSizeInformation(_windows_ctypes.Structure):
        _fields_ = (
            ("AceCount", _windows_wintypes.DWORD),
            ("AclBytesInUse", _windows_wintypes.DWORD),
            ("AclBytesFree", _windows_wintypes.DWORD),
        )

    class _AceHeader(_windows_ctypes.Structure):
        _fields_ = (
            ("AceType", _windows_ctypes.c_ubyte),
            ("AceFlags", _windows_ctypes.c_ubyte),
            ("AceSize", _windows_wintypes.WORD),
        )

    class _AccessAllowedAce(_windows_ctypes.Structure):
        _fields_ = (
            ("Header", _AceHeader),
            ("Mask", _windows_wintypes.DWORD),
            ("SidStart", _windows_wintypes.DWORD),
        )

    class _GenericMapping(_windows_ctypes.Structure):
        _fields_ = (
            ("GenericRead", _windows_wintypes.DWORD),
            ("GenericWrite", _windows_wintypes.DWORD),
            ("GenericExecute", _windows_wintypes.DWORD),
            ("GenericAll", _windows_wintypes.DWORD),
        )

    class _FileId128(_windows_ctypes.Structure):
        _fields_ = (("Identifier", _windows_ctypes.c_ubyte * 16),)

    class _FileIdInfo(_windows_ctypes.Structure):
        _fields_ = (
            ("VolumeSerialNumber", _windows_ctypes.c_ulonglong),
            ("FileId", _FileId128),
        )

    def _normalized_file_access_mask(mask: int) -> int:
        advapi32 = _windows_ctypes.WinDLL("advapi32", use_last_error=True)
        map_generic = advapi32.MapGenericMask
        map_generic.argtypes = (
            _windows_ctypes.POINTER(_windows_wintypes.DWORD),
            _windows_ctypes.POINTER(_GenericMapping),
        )
        map_generic.restype = None
        normalized = _windows_wintypes.DWORD(mask)
        mapping = _GenericMapping(
            GenericRead=_FILE_GENERIC_READ,
            GenericWrite=_FILE_GENERIC_WRITE,
            GenericExecute=_FILE_GENERIC_EXECUTE,
            GenericAll=_FILE_ALL_ACCESS,
        )
        map_generic(_windows_ctypes.byref(normalized), _windows_ctypes.byref(mapping))
        return int(normalized.value)

    def _windows_handle_identity(handle: int) -> tuple[int, int]:
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        get_information = kernel32.GetFileInformationByHandleEx
        get_information.argtypes = (
            _windows_wintypes.HANDLE,
            _windows_ctypes.c_int,
            _windows_wintypes.LPVOID,
            _windows_wintypes.DWORD,
        )
        get_information.restype = _windows_wintypes.BOOL
        information = _FileIdInfo()
        if not get_information(
            handle,
            18,
            _windows_ctypes.byref(information),
            _windows_ctypes.sizeof(information),
        ):
            raise OSError(
                _windows_ctypes.get_last_error(),
                "GetFileInformationByHandleEx(FileIdInfo) failed",
            )
        return (
            int(information.VolumeSerialNumber),
            int.from_bytes(bytes(information.FileId.Identifier), "little"),
        )

    def _invalidate_windows_handle(handle: int) -> bool:
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        set_pointer = kernel32.SetFilePointerEx
        set_pointer.argtypes = (
            _windows_wintypes.HANDLE,
            _windows_ctypes.c_longlong,
            _windows_ctypes.POINTER(_windows_ctypes.c_longlong),
            _windows_wintypes.DWORD,
        )
        set_pointer.restype = _windows_wintypes.BOOL
        set_end = kernel32.SetEndOfFile
        set_end.argtypes = (_windows_wintypes.HANDLE,)
        set_end.restype = _windows_wintypes.BOOL
        flush = kernel32.FlushFileBuffers
        flush.argtypes = (_windows_wintypes.HANDLE,)
        flush.restype = _windows_wintypes.BOOL
        get_size = kernel32.GetFileSizeEx
        get_size.argtypes = (
            _windows_wintypes.HANDLE,
            _windows_ctypes.POINTER(_windows_ctypes.c_longlong),
        )
        get_size.restype = _windows_wintypes.BOOL
        new_position = _windows_ctypes.c_longlong()
        size = _windows_ctypes.c_longlong()
        return bool(
            set_pointer(handle, 0, _windows_ctypes.byref(new_position), 0)
            and set_end(handle)
            and flush(handle)
            and get_size(handle, _windows_ctypes.byref(size))
            and size.value == 0
        )

    def _open_windows_effective_token(advapi32: Any, kernel32: Any) -> object:
        token = _windows_wintypes.HANDLE()
        open_thread_token = advapi32.OpenThreadToken
        open_thread_token.argtypes = (
            _windows_wintypes.HANDLE,
            _windows_wintypes.DWORD,
            _windows_wintypes.BOOL,
            _windows_ctypes.POINTER(_windows_wintypes.HANDLE),
        )
        open_thread_token.restype = _windows_wintypes.BOOL
        get_current_thread = kernel32.GetCurrentThread
        get_current_thread.argtypes = ()
        get_current_thread.restype = _windows_wintypes.HANDLE
        if open_thread_token(
            get_current_thread(),
            0x0008,
            True,
            _windows_ctypes.byref(token),
        ):
            return token
        thread_error = _windows_ctypes.get_last_error()
        if thread_error != 1008:
            raise OSError(thread_error, "OpenThreadToken failed")
        open_process_token = advapi32.OpenProcessToken
        open_process_token.argtypes = (
            _windows_wintypes.HANDLE,
            _windows_wintypes.DWORD,
            _windows_ctypes.POINTER(_windows_wintypes.HANDLE),
        )
        open_process_token.restype = _windows_wintypes.BOOL
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.argtypes = ()
        get_current_process.restype = _windows_wintypes.HANDLE
        if not open_process_token(
            get_current_process(),
            0x0008,
            _windows_ctypes.byref(token),
        ):
            raise OSError(_windows_ctypes.get_last_error(), "OpenProcessToken failed")
        return token

    def _close_windows_checked_handle(kernel32: Any, handle: object) -> None:
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (_windows_wintypes.HANDLE,)
        close_handle.restype = _windows_wintypes.BOOL
        if not close_handle(handle):
            raise OSError(_windows_ctypes.get_last_error(), "CloseHandle failed")

    def _windows_local_free(kernel32: Any, pointer: object) -> None:
        local_free = kernel32.LocalFree
        local_free.argtypes = (_windows_wintypes.LPVOID,)
        local_free.restype = _windows_wintypes.LPVOID
        if local_free(pointer):
            raise OSError(_windows_ctypes.get_last_error(), "LocalFree failed")

    def _windows_local_free_all(kernel32: Any, *pointers: object) -> None:
        cleanup_error: BaseException | None = None
        for pointer in pointers:
            try:
                _windows_local_free(kernel32, pointer)
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
        if cleanup_error is not None:
            raise cleanup_error

    def _windows_effective_user_sid_string() -> str:
        advapi32 = _windows_ctypes.WinDLL("advapi32", use_last_error=True)
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        token = _open_windows_effective_token(advapi32, kernel32)
        try:
            required = _windows_wintypes.DWORD()
            get_token = advapi32.GetTokenInformation
            get_token.argtypes = (
                _windows_wintypes.HANDLE,
                _windows_ctypes.c_int,
                _windows_wintypes.LPVOID,
                _windows_wintypes.DWORD,
                _windows_ctypes.POINTER(_windows_wintypes.DWORD),
            )
            get_token.restype = _windows_wintypes.BOOL
            get_token(token, 1, None, 0, _windows_ctypes.byref(required))
            if required.value == 0:
                raise OSError(_windows_ctypes.get_last_error(), "GetTokenInformation failed")
            buffer = _windows_ctypes.create_string_buffer(required.value)
            if not get_token(
                token,
                1,
                buffer,
                required,
                _windows_ctypes.byref(required),
            ):
                raise OSError(_windows_ctypes.get_last_error(), "GetTokenInformation failed")
            sid = _windows_ctypes.cast(buffer, _windows_ctypes.POINTER(_windows_wintypes.LPVOID))[0]
            string_sid = _windows_wintypes.LPWSTR()
            convert_sid = advapi32.ConvertSidToStringSidW
            convert_sid.argtypes = (
                _windows_wintypes.LPVOID,
                _windows_ctypes.POINTER(_windows_wintypes.LPWSTR),
            )
            convert_sid.restype = _windows_wintypes.BOOL
            if not convert_sid(sid, _windows_ctypes.byref(string_sid)):
                raise OSError(_windows_ctypes.get_last_error(), "ConvertSidToStringSidW failed")
            try:
                return str(string_sid.value)
            finally:
                _windows_local_free(kernel32, string_sid)
        finally:
            _close_windows_checked_handle(kernel32, token)

    def _windows_sid_from_string(value: str) -> tuple[_windows_wintypes.LPVOID, object]:
        advapi32 = _windows_ctypes.WinDLL("advapi32", use_last_error=True)
        sid = _windows_wintypes.LPVOID()
        convert = advapi32.ConvertStringSidToSidW
        convert.argtypes = (
            _windows_wintypes.LPCWSTR,
            _windows_ctypes.POINTER(_windows_wintypes.LPVOID),
        )
        convert.restype = _windows_wintypes.BOOL
        if not convert(value, _windows_ctypes.byref(sid)):
            raise OSError(_windows_ctypes.get_last_error(), "ConvertStringSidToSidW failed")
        return sid, sid

    def _assert_windows_owner_only_handle(handle: int) -> None:
        advapi32 = _windows_ctypes.WinDLL("advapi32", use_last_error=True)
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        owner = _windows_wintypes.LPVOID()
        dacl = _windows_wintypes.LPVOID()
        descriptor = _windows_wintypes.LPVOID()
        get_security = advapi32.GetSecurityInfo
        get_security.argtypes = (
            _windows_wintypes.HANDLE,
            _windows_ctypes.c_int,
            _windows_wintypes.DWORD,
            _windows_ctypes.POINTER(_windows_wintypes.LPVOID),
            _windows_wintypes.LPVOID,
            _windows_ctypes.POINTER(_windows_wintypes.LPVOID),
            _windows_wintypes.LPVOID,
            _windows_ctypes.POINTER(_windows_wintypes.LPVOID),
        )
        get_security.restype = _windows_wintypes.DWORD
        result = get_security(
            handle,
            1,
            _OWNER_SECURITY_INFORMATION | _DACL_SECURITY_INFORMATION,
            _windows_ctypes.byref(owner),
            None,
            _windows_ctypes.byref(dacl),
            None,
            _windows_ctypes.byref(descriptor),
        )
        if result != 0:
            raise OSError(result, "GetSecurityInfo failed")
        try:
            sid_pointer, allocated_sid = _windows_sid_from_string(
                _windows_effective_user_sid_string()
            )
        except BaseException:
            _windows_local_free(kernel32, descriptor)
            raise
        try:
            equal_sid = advapi32.EqualSid
            equal_sid.argtypes = (_windows_wintypes.LPVOID, _windows_wintypes.LPVOID)
            equal_sid.restype = _windows_wintypes.BOOL
            control = _windows_wintypes.WORD()
            revision = _windows_wintypes.DWORD()
            get_control = advapi32.GetSecurityDescriptorControl
            get_control.argtypes = (
                _windows_wintypes.LPVOID,
                _windows_ctypes.POINTER(_windows_wintypes.WORD),
                _windows_ctypes.POINTER(_windows_wintypes.DWORD),
            )
            get_control.restype = _windows_wintypes.BOOL
            acl_info = _AclSizeInformation()
            get_acl_info = advapi32.GetAclInformation
            get_acl_info.argtypes = (
                _windows_wintypes.LPVOID,
                _windows_wintypes.LPVOID,
                _windows_wintypes.DWORD,
                _windows_ctypes.c_int,
            )
            get_acl_info.restype = _windows_wintypes.BOOL
            ace_pointer = _windows_wintypes.LPVOID()
            get_ace = advapi32.GetAce
            get_ace.argtypes = (
                _windows_wintypes.LPVOID,
                _windows_wintypes.DWORD,
                _windows_ctypes.POINTER(_windows_wintypes.LPVOID),
            )
            get_ace.restype = _windows_wintypes.BOOL
            if (
                not owner
                or not dacl
                or not equal_sid(owner, sid_pointer)
                or not get_control(
                    descriptor,
                    _windows_ctypes.byref(control),
                    _windows_ctypes.byref(revision),
                )
                or not bool(control.value & _SE_DACL_PRESENT)
                or not bool(control.value & _SE_DACL_PROTECTED)
                or not get_acl_info(
                    dacl,
                    _windows_ctypes.byref(acl_info),
                    _windows_ctypes.sizeof(acl_info),
                    2,
                )
                or acl_info.AceCount != 1
                or not get_ace(dacl, 0, _windows_ctypes.byref(ace_pointer))
            ):
                raise OSError("file does not have the protected owner-only DACL")
            ace = _windows_ctypes.cast(
                ace_pointer,
                _windows_ctypes.POINTER(_AccessAllowedAce),
            ).contents
            ace_sid = _windows_ctypes.byref(ace, _AccessAllowedAce.SidStart.offset)
            if (
                ace.Header.AceType != 0
                or ace.Header.AceFlags != 0
                or _normalized_file_access_mask(int(ace.Mask)) != _FILE_ALL_ACCESS
                or not equal_sid(ace_sid, sid_pointer)
            ):
                raise OSError("file DACL is not one exact owner FILE_ALL_ACCESS ACE")
            flags = _windows_wintypes.DWORD()
            get_handle_information = kernel32.GetHandleInformation
            get_handle_information.argtypes = (
                _windows_wintypes.HANDLE,
                _windows_ctypes.POINTER(_windows_wintypes.DWORD),
            )
            get_handle_information.restype = _windows_wintypes.BOOL
            if not get_handle_information(handle, _windows_ctypes.byref(flags)) or bool(
                flags.value & _HANDLE_FLAG_INHERIT
            ):
                raise OSError("file handle is inheritable or cannot be inspected")
        finally:
            _windows_local_free_all(kernel32, allocated_sid, descriptor)

    def _rollback_raw_windows_handle(target: _OutputTarget, raw_handle: int) -> None:
        invalidated = False
        try:
            invalidated = _invalidate_windows_handle(raw_handle)
        except BaseException:
            invalidated = False
        delete_marked = False
        try:
            delete_marked = _manifest_boundary._mark_windows_handle_delete(raw_handle)
        except BaseException:
            delete_marked = False
        close_succeeded = False
        try:
            _manifest_boundary._close_windows_handle(raw_handle)
            close_succeeded = True
        except BaseException:
            close_succeeded = False
        absent = _strict_path_is_absent(target.path)
        if not (invalidated and delete_marked and close_succeeded and absent):
            raise TrustedLocalUsePlanQuarantineRequired(
                "raw created artifact rollback could not be confirmed"
            )

    def _call_windows_create_file(
        create_file: Any,
        target: _OutputTarget,
        attributes: _SecurityAttributes,
    ) -> int:
        return int(
            create_file(
                str(target.path),
                _GENERIC_READ | _GENERIC_WRITE | 0x00010000,
                0,
                _windows_ctypes.byref(attributes),
                1,
                0x00000080 | 0x00200000,
                None,
            )
        )

    def _open_windows_exclusive_artifact(
        target: _OutputTarget,
        parent_guard: int,
        attempt_state: _CreateAttemptState | None = None,
    ) -> int:
        state = attempt_state if attempt_state is not None else _CreateAttemptState()
        advapi32 = _windows_ctypes.WinDLL("advapi32", use_last_error=True)
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        sid = _windows_effective_user_sid_string()
        sddl = f"O:{sid}D:P(A;;FA;;;{sid})"
        descriptor = _windows_wintypes.LPVOID()
        convert = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
        convert.argtypes = (
            _windows_wintypes.LPCWSTR,
            _windows_wintypes.DWORD,
            _windows_wintypes.LPVOID,
            _windows_wintypes.LPVOID,
        )
        convert.restype = _windows_wintypes.BOOL
        if not convert(sddl, 1, _windows_ctypes.byref(descriptor), None):
            raise OSError(
                _windows_ctypes.get_last_error(),
                "owner-only security descriptor creation failed",
            )
        attributes = _SecurityAttributes(
            nLength=_windows_ctypes.sizeof(_SecurityAttributes),
            lpSecurityDescriptor=descriptor,
            bInheritHandle=False,
        )
        create_file = kernel32.CreateFileW
        create_file.argtypes = (
            _windows_wintypes.LPCWSTR,
            _windows_wintypes.DWORD,
            _windows_wintypes.DWORD,
            _windows_ctypes.POINTER(_SecurityAttributes),
            _windows_wintypes.DWORD,
            _windows_wintypes.DWORD,
            _windows_wintypes.HANDLE,
        )
        create_file.restype = _windows_wintypes.HANDLE
        native_handle: int | None = None
        raw_handle: int | None = None
        descriptor_fd: int | None = None
        try:
            state.native_call_entered = True
            native_handle = _call_windows_create_file(create_file, target, attributes)
            if native_handle == _INVALID_HANDLE_VALUE:
                state.native_never_succeeded = True
                error = _windows_ctypes.get_last_error()
                if error in {80, 183}:
                    raise _IndependentArtifactCreateWinner(str(target.path))
                raise _NativeArtifactCreateNeverSucceeded(error, "CreateFileW failed")
            raw_handle = native_handle
            descriptor_to_free = descriptor
            descriptor = _windows_wintypes.LPVOID()
            _windows_local_free(kernel32, descriptor_to_free)
            set_handle_information = kernel32.SetHandleInformation
            set_handle_information.argtypes = (
                _windows_wintypes.HANDLE,
                _windows_wintypes.DWORD,
                _windows_wintypes.DWORD,
            )
            set_handle_information.restype = _windows_wintypes.BOOL
            if not set_handle_information(raw_handle, _HANDLE_FLAG_INHERIT, 0):
                raise OSError(_windows_ctypes.get_last_error(), "SetHandleInformation failed")
            _assert_windows_owner_only_handle(raw_handle)
            descriptor_fd = _windows_msvcrt.open_osfhandle(
                raw_handle,
                os.O_RDWR | getattr(os, "O_BINARY", 0),
            )
            raw_handle = None
            return descriptor_fd
        except (_IndependentArtifactCreateWinner, _NativeArtifactCreateNeverSucceeded):
            raise
        except BaseException as creation_error:
            if descriptor_fd is not None:
                emergency_holder = _CreatedArtifactHolder(
                    target=target,
                    descriptor=descriptor_fd,
                    parent_guard=parent_guard,
                    windows_parent_guard=True,
                )
                _rollback_created_artifact(emergency_holder, close_parent=False)
                state.rollback_confirmed = True
            elif raw_handle is not None:
                _rollback_raw_windows_handle(target, raw_handle)
                state.rollback_confirmed = True
            elif native_handle is not None and native_handle != _INVALID_HANDLE_VALUE:
                _rollback_raw_windows_handle(target, native_handle)
                state.rollback_confirmed = True
            elif state.native_call_entered and not state.native_never_succeeded:
                raise TrustedLocalUsePlanQuarantineRequired(
                    "Windows native create returned without a retained handle"
                ) from creation_error
            if isinstance(creation_error, TrustedLocalUsePlanFinalizationError):
                raise
            if isinstance(creation_error, Exception):
                raise OSError(
                    "Windows artifact creation failed after safe rollback"
                ) from creation_error
            raise
        finally:
            if descriptor:
                _windows_local_free(kernel32, descriptor)

else:

    def _normalized_file_access_mask(mask: int) -> int:
        del mask
        raise OSError("Windows generic access-mask normalization is unavailable")

    def _windows_handle_identity(handle: int) -> tuple[int, int]:
        del handle
        raise OSError("Windows handle identity inspection is unavailable")

    def _invalidate_windows_handle(handle: int) -> bool:
        del handle
        raise OSError("Windows raw-handle invalidation is unavailable")

    def _assert_windows_owner_only_handle(handle: int) -> None:
        del handle
        raise OSError("Windows owner-only DACL inspection is unavailable")

    def _rollback_raw_windows_handle(target: _OutputTarget, raw_handle: int) -> None:
        del target, raw_handle
        raise OSError("Windows raw-handle rollback is unavailable")

    def _open_windows_exclusive_artifact(
        target: _OutputTarget,
        parent_guard: int,
        attempt_state: _CreateAttemptState | None = None,
    ) -> int:
        del target, parent_guard, attempt_state
        raise OSError("Windows owner-only creation is unavailable")


def _assert_owner_only_descriptor(descriptor: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        try:
            _assert_windows_owner_only_handle(msvcrt.get_osfhandle(descriptor))
        except OSError as exc:
            raise TrustedLocalUsePlanFinalizationError(
                "file permissions are not exact protected owner-only access"
            ) from exc
        return
    try:
        opened = os.fstat(descriptor)
        effective_user = os.geteuid()
    except (AttributeError, OSError) as exc:
        raise TrustedLocalUsePlanFinalizationError(
            "file owner and mode could not be established"
        ) from exc
    if opened.st_uid != effective_user or stat.S_IMODE(opened.st_mode) != 0o600:
        raise TrustedLocalUsePlanFinalizationError(
            "file must be owned by the effective user with exact mode 0600"
        )


def _acquire_parent_guard(target: _OutputTarget) -> tuple[int, bool]:
    if sys.platform != "win32":
        required = ("O_DIRECTORY", "O_CLOEXEC")
        if any(not hasattr(os, name) for name in required) or os.open not in os.supports_dir_fd:
            raise TrustedLocalUsePlanFinalizationError(
                "POSIX parent-relative safety primitives are unavailable"
            )
        descriptor: int | None = None
        try:
            descriptor = os.open(
                target.parent,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
            )
            opened = os.fstat(descriptor)
        except OSError as exc:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            raise TrustedLocalUsePlanFinalizationError(
                "artifact output parent could not be guarded"
            ) from exc
        if (opened.st_dev, opened.st_ino) != target.parent_physical_identity:
            os.close(descriptor)
            raise TrustedLocalUsePlanFinalizationError(
                "artifact output parent changed before guard acquisition"
            )
        return descriptor, False
    try:
        parent_guard = _manifest_boundary._acquire_parent_guard(cast(Any, target))
    except (TrustedLocalRightsManifestFinalizationError, OSError) as exc:
        raise TrustedLocalUsePlanFinalizationError(
            "artifact output parent could not be guarded"
        ) from exc
    try:
        observed_identity = _windows_handle_identity(parent_guard[0])
    except BaseException as exc:
        try:
            _manifest_boundary._close_windows_handle(parent_guard[0])
        except BaseException as close_exc:
            raise TrustedLocalUsePlanFinalizationError(
                "Windows parent guard identity and close could not be established"
            ) from close_exc
        raise TrustedLocalUsePlanFinalizationError(
            "Windows parent guard identity could not be established"
        ) from exc
    if observed_identity != target.parent_physical_identity:
        try:
            _manifest_boundary._close_windows_handle(parent_guard[0])
        except BaseException as exc:
            raise TrustedLocalUsePlanFinalizationError(
                "mismatched Windows parent guard could not be closed"
            ) from exc
        raise TrustedLocalUsePlanFinalizationError(
            "Windows parent guard opened a different physical directory"
        )
    return parent_guard


def _close_parent_guard(created: _CreatedArtifact) -> None:
    if created.parent_guard_closed or created.parent_guard_close_uncertain:
        raise TrustedLocalUsePlanFinalizationError(
            "artifact parent guard is already closed or uncertain"
        )
    try:
        if created.windows_parent_guard:
            _manifest_boundary._close_windows_handle(created.parent_guard)
        else:
            os.close(created.parent_guard)
    except BaseException:
        created.parent_guard_close_uncertain = True
        raise
    created.parent_guard_closed = True


def _call_posix_exclusive_create(target: _OutputTarget, parent_guard: int, flags: int) -> int:
    try:
        return os.open(target.path.name, flags, 0o600, dir_fd=parent_guard)
    except FileExistsError as exc:
        raise _IndependentArtifactCreateWinner(str(target.path)) from exc


def _open_exclusive_artifact(
    target: _OutputTarget,
    parent_guard: int,
    attempt_state: _CreateAttemptState | None = None,
) -> int:
    state = attempt_state if attempt_state is not None else _CreateAttemptState()
    descriptor: int | None = None
    try:
        if sys.platform == "win32":
            descriptor = _open_windows_exclusive_artifact(target, parent_guard, state)
        else:
            required = ("O_NOFOLLOW", "O_CLOEXEC")
            if any(not hasattr(os, name) for name in required) or os.open not in os.supports_dir_fd:
                state.native_never_succeeded = True
                raise _NativeArtifactCreateNeverSucceeded(
                    "POSIX exclusive parent-relative creation primitives are unavailable"
                )
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
            state.native_call_entered = True
            descriptor = _call_posix_exclusive_create(target, parent_guard, flags)
        return descriptor
    except _IndependentArtifactCreateWinner:
        state.native_never_succeeded = True
        raise
    except _NativeArtifactCreateNeverSucceeded:
        state.native_never_succeeded = True
        raise
    except BaseException as creation_error:
        if descriptor is not None:
            emergency_holder = _CreatedArtifactHolder(
                target=target,
                descriptor=descriptor,
                parent_guard=parent_guard,
                windows_parent_guard=sys.platform == "win32",
            )
            _rollback_created_artifact(emergency_holder, close_parent=False)
            state.rollback_confirmed = True
        elif state.native_call_entered and not state.rollback_confirmed:
            raise TrustedLocalUsePlanQuarantineRequired(
                "artifact create returned without a retained descriptor"
            ) from creation_error
        raise


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _assert_created_artifact_binding(
    created: _CreatedArtifact,
    *,
    require_empty: bool = False,
) -> None:
    if (
        created.closed
        or created.descriptor_close_uncertain
        or created.parent_guard_closed
        or created.parent_guard_close_uncertain
    ):
        raise TrustedLocalUsePlanFinalizationError("created artifact binding guard is not live")
    try:
        if created.windows_parent_guard:
            parent_identity = _windows_handle_identity(created.parent_guard)
        else:
            parent = os.fstat(created.parent_guard)
            parent_identity = (parent.st_dev, parent.st_ino)
        _revalidate_output_target(created.target, must_be_absent=False)
        opened = os.fstat(created.descriptor)
        named = created.target.path.lstat()
    except (OSError, TrustedLocalUsePlanFinalizationError) as exc:
        raise TrustedLocalUsePlanFinalizationError(
            "created artifact binding could not be established"
        ) from exc
    opened_physical = (opened.st_dev, opened.st_ino)
    named_physical = (named.st_dev, named.st_ino)
    named_attributes = int(getattr(named, "st_file_attributes", 0))
    if (
        parent_identity != created.target.parent_physical_identity
        or created.target.path.parent != created.target.parent
        or opened_physical != named_physical
        or not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(named.st_mode)
        or stat.S_ISLNK(named.st_mode)
        or bool(named_attributes & 0x400)
        or opened.st_nlink != 1
        or named.st_nlink != 1
        or (require_empty and (opened.st_size != 0 or named.st_size != 0))
    ):
        raise TrustedLocalUsePlanFinalizationError(
            "created artifact is not bound to its exact guarded target"
        )


def _read_open_created_artifact[ArtifactT: BaseModel](
    created: _CreatedArtifact,
    artifact: ArtifactT,
    *,
    parser: Callable[[bytes], ArtifactT],
    maximum_bytes: int,
    field: str,
) -> _FileSeal:
    raw = _canonical_document(artifact)
    try:
        _assert_created_artifact_binding(created)
        _assert_owner_only_descriptor(created.descriptor)
        opened = os.fstat(created.descriptor)
        os.lseek(created.descriptor, 0, os.SEEK_SET)
        observed = bytearray()
        while len(observed) <= maximum_bytes:
            chunk = os.read(
                created.descriptor,
                min(65_536, maximum_bytes + 1 - len(observed)),
            )
            if not chunk:
                break
            observed.extend(chunk)
        opened_after = os.fstat(created.descriptor)
        _assert_owner_only_descriptor(created.descriptor)
        named = created.target.path.lstat()
    except (OSError, TrustedLocalUsePlanFinalizationError) as exc:
        raise TrustedLocalUsePlanFinalizationError(
            f"created {field} could not be inspected"
        ) from exc
    opened_identity = _stat_identity(opened)
    named_identity = _stat_identity(named)
    attributes = int(getattr(named, "st_file_attributes", 0))
    if (
        opened_identity != named_identity
        or _stat_identity(opened_after) != opened_identity
        or not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(opened_after.st_mode)
        or not stat.S_ISREG(named.st_mode)
        or stat.S_ISLNK(named.st_mode)
        or bool(attributes & 0x400)
        or opened.st_nlink != 1
        or opened_after.st_nlink != 1
        or named.st_nlink != 1
    ):
        raise TrustedLocalUsePlanFinalizationError(f"created {field} identity drifted")
    _assert_created_artifact_binding(created)
    data = bytes(observed)
    if len(data) > maximum_bytes:
        raise TrustedLocalUsePlanFinalizationError(f"created {field} exceeded its fixed bound")
    try:
        loaded = parser(data)
    except (ValidationError, ValueError, RuntimeError) as exc:
        raise TrustedLocalUsePlanFinalizationError(
            f"created {field} violates its strict contract"
        ) from exc
    if loaded != artifact or data != raw:
        raise TrustedLocalUsePlanFinalizationError(
            f"written {field} failed exact canonical verification"
        )
    return _FileSeal(
        path=created.target.path,
        sha256=_sha256(data),
        size_bytes=len(data),
        identity=opened_identity,
    )


def _inspect_created_artifact_name(
    created: _CreatedArtifact,
    opened_physical: tuple[int, int],
) -> tuple[bool, bool]:
    try:
        if sys.platform == "win32":
            named = created.target.path.lstat()
        else:
            named = os.stat(
                created.target.path.name,
                dir_fd=created.parent_guard,
                follow_symlinks=False,
            )
    except FileNotFoundError:
        return True, True
    except OSError:
        return False, False
    return (named.st_dev, named.st_ino) == opened_physical, False


def _record_descriptor_closed(created: _CreatedArtifact) -> None:
    created.closed = True
    created.descriptor_close_uncertain = False


def _rollback_created_artifact(
    created: _CreatedArtifact,
    *,
    close_parent: bool = True,
) -> None:
    if created.descriptor_close_uncertain:
        raise TrustedLocalUsePlanQuarantineRequired(
            "created artifact descriptor close is uncertain"
        )
    if created.closed:
        return
    invalidated = False
    delete_pending = False
    name_safe = False
    name_absent = False
    descriptor_closed = False
    descriptor_state_error: BaseException | None = None
    parent_closed = created.parent_guard_closed or not close_parent
    opened_physical: tuple[int, int] | None = None
    try:
        try:
            opened = os.fstat(created.descriptor)
            opened_physical = (opened.st_dev, opened.st_ino)
        except BaseException:
            opened_physical = None
        try:
            invalidated = _manifest_boundary._invalidate_open_manifest(created.descriptor)
        except BaseException:
            invalidated = False
        if not invalidated:
            try:
                invalidated = _manifest_boundary._emergency_poison_open_manifest(created.descriptor)
            except BaseException:
                invalidated = False
        if sys.platform == "win32":
            try:
                delete_pending = _manifest_boundary._delete_open_windows_manifest(
                    created.descriptor
                )
            except BaseException:
                delete_pending = False
    finally:
        created.descriptor_close_uncertain = True
        try:
            os.close(created.descriptor)
        except BaseException:
            descriptor_closed = False
        else:
            descriptor_closed = True
            try:
                _record_descriptor_closed(created)
            except BaseException as exc:
                descriptor_state_error = exc
        try:
            if (
                opened_physical is not None
                and not created.parent_guard_closed
                and not created.parent_guard_close_uncertain
            ):
                name_safe, name_absent = _inspect_created_artifact_name(
                    created,
                    opened_physical,
                )
        except BaseException:
            name_safe = False
            name_absent = False
        if close_parent and not created.parent_guard_closed:
            if created.parent_guard_close_uncertain:
                parent_closed = False
            else:
                try:
                    _close_parent_guard(created)
                    parent_closed = True
                except BaseException:
                    parent_closed = False
        elif created.parent_guard_closed:
            parent_closed = True
    if descriptor_state_error is not None:
        raise TrustedLocalUsePlanQuarantineRequired(
            "created artifact descriptor close state is uncertain"
        ) from descriptor_state_error
    if sys.platform == "win32":
        deletion_confirmed = delete_pending and descriptor_closed and name_absent
        rollback_confirmed = (
            descriptor_closed
            and parent_closed
            and name_safe
            and (invalidated or deletion_confirmed)
        )
    else:
        rollback_confirmed = invalidated and descriptor_closed and name_safe and parent_closed
    if not rollback_confirmed:
        raise TrustedLocalUsePlanQuarantineRequired(
            "created artifact rollback failed closed; output requires quarantine"
        )


def _fsync_parent_directory(created: _CreatedArtifact) -> None:
    if not created.windows_parent_guard:
        os.fsync(created.parent_guard)


def _create_new_artifact[ArtifactT: BaseModel](
    target: _OutputTarget,
    artifact: ArtifactT,
    *,
    parser: Callable[[bytes], ArtifactT],
    maximum_bytes: int,
    field: str,
) -> _CreatedArtifact:
    raw = _canonical_document(artifact)
    if not raw or len(raw) > maximum_bytes:
        raise TrustedLocalUsePlanFinalizationError(f"candidate {field} exceeds its fixed bound")
    _revalidate_output_target(target, must_be_absent=True)
    parent_guard = _acquire_parent_guard(target)
    descriptor: int | None = None
    created: _CreatedArtifact | None = None
    attempt_state = _CreateAttemptState()
    try:
        _revalidate_output_target(target, must_be_absent=True)
        descriptor = _open_exclusive_artifact(
            target,
            parent_guard[0],
            attempt_state,
        )
        created = _CreatedArtifact(
            target=target,
            descriptor=descriptor,
            parent_guard=parent_guard[0],
            windows_parent_guard=parent_guard[1],
        )
        _assert_created_artifact_binding(created, require_empty=True)
        _assert_owner_only_descriptor(descriptor)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise OSError("short write")
            offset += written
        os.fsync(descriptor)
        created.seal = _read_open_created_artifact(
            created,
            artifact,
            parser=parser,
            maximum_bytes=maximum_bytes,
            field=field,
        )
        _revalidate_output_target(target, must_be_absent=False)
        return created
    except _IndependentArtifactCreateWinner as exc:
        try:
            if parent_guard[1]:
                _manifest_boundary._close_windows_handle(parent_guard[0])
            else:
                os.close(parent_guard[0])
        except BaseException:
            pass
        raise TrustedLocalUsePlanFinalizationError(f"{field} output must be one new file") from exc
    except BaseException as exc:
        if created is not None:
            _rollback_created_artifact(created)
            attempt_state.rollback_confirmed = True
        elif descriptor is not None:
            emergency_holder = _CreatedArtifactHolder(
                target=target,
                descriptor=descriptor,
                parent_guard=parent_guard[0],
                windows_parent_guard=parent_guard[1],
            )
            _rollback_created_artifact(emergency_holder)
            attempt_state.rollback_confirmed = True
        else:
            parent_closed = False
            try:
                if parent_guard[1]:
                    _manifest_boundary._close_windows_handle(parent_guard[0])
                else:
                    os.close(parent_guard[0])
                parent_closed = True
            except BaseException:
                parent_closed = False
            if attempt_state.native_call_entered and not attempt_state.native_never_succeeded:
                if not attempt_state.rollback_confirmed:
                    raise TrustedLocalUsePlanQuarantineRequired(
                        "native artifact create returned without a retained rollback handle"
                    ) from exc
                if not parent_closed:
                    raise TrustedLocalUsePlanQuarantineRequired(
                        "artifact parent guard close could not be confirmed after rollback"
                    ) from exc
            if not parent_closed:
                raise TrustedLocalUsePlanFinalizationError(
                    "artifact parent guard close could not be confirmed"
                ) from exc
        if isinstance(exc, TrustedLocalUsePlanFinalizationError):
            raise
        if isinstance(exc, Exception):
            raise TrustedLocalUsePlanFinalizationError(
                f"{field} output could not be created"
            ) from exc
        raise


def _commit_created_artifact[ArtifactT: BaseModel](
    created: _CreatedArtifact,
    artifact: ArtifactT,
    *,
    parser: Callable[[bytes], ArtifactT],
    maximum_bytes: int,
    field: str,
) -> None:
    if created.descriptor_close_uncertain:
        raise TrustedLocalUsePlanQuarantineRequired(
            f"created {field} descriptor close is uncertain"
        )
    if created.closed or created.seal is None:
        raise TrustedLocalUsePlanFinalizationError(f"created {field} is not publishable")
    _assert_created_artifact_binding(created)
    _revalidate_output_target(created.target, must_be_absent=False)
    final_seal = _read_open_created_artifact(
        created,
        artifact,
        parser=parser,
        maximum_bytes=maximum_bytes,
        field=field,
    )
    if final_seal != created.seal:
        raise TrustedLocalUsePlanFinalizationError(f"created {field} drifted before commit")
    _fsync_parent_directory(created)
    try:
        _close_parent_guard(created)
    except BaseException as parent_close_error:
        created.parent_guard_close_uncertain = True
        _rollback_created_artifact(created, close_parent=False)
        raise TrustedLocalUsePlanQuarantineRequired(
            f"created {field} parent guard close is uncertain"
        ) from parent_close_error
    created.descriptor_close_uncertain = True
    try:
        os.close(created.descriptor)
    except BaseException as descriptor_close_error:
        raise TrustedLocalUsePlanQuarantineRequired(
            f"created {field} descriptor close is uncertain"
        ) from descriptor_close_error
    else:
        try:
            _record_descriptor_closed(created)
        except BaseException as descriptor_state_error:
            raise TrustedLocalUsePlanQuarantineRequired(
                f"created {field} descriptor close state is uncertain"
            ) from descriptor_state_error


def _validated_expected_anchor(plan_id: str, plan_sha256: str) -> tuple[str, str]:
    if (
        type(plan_id) is not str
        or type(plan_sha256) is not str
        or _PLAN_ID.fullmatch(plan_id) is None
        or _LOWER_SHA256.fullmatch(plan_sha256) is None
    ):
        raise TrustedLocalUsePlanFinalizationError(
            "expected Plan anchor must use one exact stable ID and lowercase SHA-256"
        )
    return plan_id, plan_sha256


def inspect_use_plan_ready(paths: TrustedLocalUsePlanPaths) -> UsePlanReadinessV27:
    """Rebuild one exact candidate twice and expose only its comparison anchor."""

    normalized = _normalize_use_plan_paths(paths)
    before = _capture_use_plan_snapshot(normalized)
    candidate = _build_use_plan(before)
    after = _capture_use_plan_snapshot(normalized)
    _assert_use_plan_snapshot_unchanged(before, after)
    return UsePlanReadinessV27(
        status=_READY_FOR_USE_PLAN_FINALIZATION,
        plan_id=candidate.plan_id,
        plan_sha256=_sha256(_canonical_document(candidate)),
    )


def finalize_use_plan(
    paths: TrustedLocalUsePlanPaths,
    output_path: Path,
    *,
    expected_plan_id: str,
    expected_plan_sha256: str,
) -> CreativeSampleRealAssetUsePlanV1:
    """Create one canonical Use Plan after fresh closure and exact anchor comparison."""

    expected_plan_id, expected_plan_sha256 = _validated_expected_anchor(
        expected_plan_id,
        expected_plan_sha256,
    )
    normalized = _normalize_use_plan_paths(paths)
    target = _validate_use_plan_output(output_path, paths=normalized)
    before = _capture_use_plan_snapshot(normalized)
    candidate = _build_use_plan(before)
    candidate_sha256 = _sha256(_canonical_document(candidate))
    if candidate.plan_id != expected_plan_id or candidate_sha256 != expected_plan_sha256:
        raise TrustedLocalUsePlanFinalizationError(
            "rebuilt Use Plan does not match the separately approved anchor"
        )
    immediately_before_write = _capture_use_plan_snapshot(normalized)
    _assert_use_plan_snapshot_unchanged(before, immediately_before_write)
    created: _CreatedArtifact | None = None
    try:
        created = _create_new_artifact(
            target,
            candidate,
            parser=parse_real_asset_use_plan_v1_json,
            maximum_bytes=_PLAN_MAX_BYTES,
            field="Use Plan",
        )
        if created.seal is None or created.seal.sha256 in (
            _reserved_use_plan_snapshot_digests(before)
        ):
            raise TrustedLocalUsePlanFinalizationError(
                "written Use Plan aliases an immutable source digest"
            )
        after = _capture_use_plan_snapshot(normalized)
        _assert_use_plan_snapshot_unchanged(before, after)
        _commit_created_artifact(
            created,
            candidate,
            parser=parse_real_asset_use_plan_v1_json,
            maximum_bytes=_PLAN_MAX_BYTES,
            field="Use Plan",
        )
    except BaseException as exc:
        if created is not None and not created.closed:
            _rollback_created_artifact(created)
        if isinstance(exc, TrustedLocalUsePlanFinalizationError):
            raise
        if isinstance(exc, Exception):
            raise TrustedLocalUsePlanFinalizationError(
                "Use Plan publication failed closed"
            ) from exc
        raise
    return candidate


def verify_use_plan(
    paths: TrustedLocalUsePlanPaths,
    use_plan_path: Path,
) -> CreativeSampleRealAssetUsePlanV1:
    """Historically reconstruct one complete Plan without a clock or filesystem write."""

    normalized = _normalize_use_plan_paths(paths)
    use_plan_path = _validate_existing_use_plan(use_plan_path, paths=normalized)
    before = _capture_use_plan_snapshot(normalized, use_plan_path=use_plan_path)
    verified = _verify_use_plan_snapshot(before)
    after = _capture_use_plan_snapshot(normalized, use_plan_path=use_plan_path)
    _assert_use_plan_snapshot_unchanged(before, after)
    return verified


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pack-root", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--pack-manifest", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--media-path", required=True, action="append", type=Path)
    parser.add_argument("--evidence", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--reviewer-a", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--reviewer-b", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--pair-check", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--evidence-retained-record", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--evidence-preparer-ref", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--reviewer-a-retained-record", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--reviewer-b-retained-record", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--qualification-request", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--qualifier-ref", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--qualification-instruction", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--qualification-decision", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--rights-manifest-file", required=True, type=Path, action=_StoreOnce)


def _paths_from_namespace(args: argparse.Namespace) -> TrustedLocalUsePlanPaths:
    from sdc.real_asset_qualification_decision_finalizer_v22 import TrustedLocalDecisionPaths
    from sdc.real_asset_qualification_preparer_v21 import TrustedLocalRequestPaths

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
    decision_inputs = TrustedLocalDecisionPaths(
        request_inputs=request_inputs,
        request=cast(Path, args.qualification_request),
        qualifier_ref=cast(Path, args.qualifier_ref),
        qualifier_decision_record=cast(Path, args.qualification_instruction),
    )
    manifest_sources = TrustedLocalRightsManifestPaths(
        decision_inputs=decision_inputs,
        decision=cast(Path, args.qualification_decision),
    )
    return TrustedLocalUsePlanPaths(
        manifest_sources=manifest_sources,
        rights_manifest=cast(Path, args.rights_manifest_file),
    )


def _expected_plan_id(value: str) -> str:
    if _PLAN_ID.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("invalid expected Plan ID")
    return value


def _expected_sha256(value: str) -> str:
    if _LOWER_SHA256.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("invalid expected SHA-256")
    return value


def _success_summary(
    operation: str,
    value: UsePlanReadinessV27 | CreativeSampleRealAssetUsePlanV1,
) -> str:
    payload: dict[str, object] = {
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "operation": operation,
        "posts_allowed": 0,
        "provider_requests": 0,
        "provider_state": "NOT_AUTHORIZED",
    }
    if operation == "inspect-use-plan-ready":
        readiness = cast(UsePlanReadinessV27, value)
        payload.update(asdict(readiness))
    elif operation == "finalize-use-plan":
        payload["status"] = "USE_PLAN_FINALIZED"
    else:
        payload["status"] = "USE_PLAN_HISTORICALLY_VERIFIED"
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _failure_summary(status: str) -> str:
    return json.dumps(
        {"error": status},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _write_json_line(stream: object, payload: str) -> None:
    encoded = (payload + "\n").encode("utf-8")
    binary = getattr(stream, "buffer", None)
    if binary is not None:
        binary.write(encoded)
        binary.flush()
        return
    text_stream = cast(Any, stream)
    text_stream.write(encoded.decode("utf-8"))
    text_stream.flush()


def main(argv: list[str] | None = None) -> int:
    parser = _FailClosedArgumentParser(
        description="Finalize or historically verify one trusted-local inert Use Plan"
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=_FailClosedArgumentParser,
    )
    inspect_parser = commands.add_parser("inspect-use-plan-ready")
    _add_common_arguments(inspect_parser)
    finalize_parser = commands.add_parser("finalize-use-plan")
    _add_common_arguments(finalize_parser)
    finalize_parser.add_argument(
        "--expected-plan-id",
        required=True,
        type=_expected_plan_id,
        action=_StoreOnce,
    )
    finalize_parser.add_argument(
        "--expected-plan-sha256",
        required=True,
        type=_expected_sha256,
        action=_StoreOnce,
    )
    finalize_parser.add_argument("--output", required=True, type=Path, action=_StoreOnce)
    verify_parser = commands.add_parser("verify-use-plan")
    _add_common_arguments(verify_parser)
    verify_parser.add_argument(
        "--use-plan-file",
        required=True,
        type=Path,
        action=_StoreOnce,
    )
    try:
        args = parser.parse_args(argv)
    except BaseException:
        _write_json_line(sys.stderr, _failure_summary("FAILED_CLOSED"))
        return 2
    try:
        paths = _paths_from_namespace(args)
        if args.command == "inspect-use-plan-ready":
            result: UsePlanReadinessV27 | CreativeSampleRealAssetUsePlanV1 = inspect_use_plan_ready(
                paths
            )
        elif args.command == "finalize-use-plan":
            result = finalize_use_plan(
                paths,
                cast(Path, args.output),
                expected_plan_id=cast(str, args.expected_plan_id),
                expected_plan_sha256=cast(str, args.expected_plan_sha256),
            )
        else:
            result = verify_use_plan(paths, cast(Path, args.use_plan_file))
    except TrustedLocalUsePlanQuarantineRequired:
        _write_json_line(
            sys.stderr,
            _failure_summary("ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"),
        )
        return 3
    except BaseException:
        _write_json_line(sys.stderr, _failure_summary("FAILED_CLOSED"))
        return 2
    _write_json_line(sys.stdout, _success_summary(cast(str, args.command), result))
    return 0


__all__ = [
    "TrustedLocalUsePlanPaths",
    "UsePlanReadinessV27",
    "TrustedLocalUsePlanFinalizationError",
    "TrustedLocalUsePlanQuarantineRequired",
    "inspect_use_plan_ready",
    "finalize_use_plan",
    "verify_use_plan",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
