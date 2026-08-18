"""Trusted local preparation of a v2.2 qualification decision instruction.

This module has exactly three operations.  It binds one already-canonical qualification
Request to one opaque qualifier reference, creates a static local workspace, finalizes the
workspace's untrusted draft into a zero-authority retained Instruction, or historically
rebuilds that Instruction.  It never reads a clock, infers a human field, performs a
qualification, creates a rights manifest, or contacts a runtime or Provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Never
from unicodedata import normalize

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from sdc.compiler import stable_id
from sdc.creative_media import CreativeMediaError, validate_local_path
from sdc.real_asset_media import RealAssetMediaError, SafeLocalFile, read_safe_local_file
from sdc.real_asset_qualification_decision_instruction_v22 import (
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
)
from sdc.real_asset_qualification_v2 import (
    CreativeSampleRealAssetQualificationRequestV2,
    RealAssetQualificationDecisionV2,
    RealAssetQualificationIssueCodeV2,
    RealAssetQualificationV2Error,
    parse_real_asset_qualification_request_v2_json,
)

_JSON_MAX_BYTES = 1_048_576
_PRIVATE_RECORD_MAX_BYTES = 64 * 1024 * 1024
_STATIC_ASSET_MAX_BYTES = 1_048_576
_STATIC_ASSET_NAMES = ("index.html", "app.js", "style.css")
_CONTEXT_JSON_NAME = "instruction-context.json"
_CONTEXT_SCRIPT_NAME = "instruction-context.js"
_WORKSPACE_NAMES = (*_STATIC_ASSET_NAMES, _CONTEXT_JSON_NAME, _CONTEXT_SCRIPT_NAME)
_ASSET_DIRECTORY_NAME = "real_asset_qualification_instruction_preparer_v23_assets"
_DRAFT_DOCUMENT_TYPE: Literal[
    "sdc.creative-sample-real-asset-qualification-decision-instruction-draft-v2.3"
] = (
    "sdc.creative-sample-real-asset-qualification-decision-instruction-draft-v2.3"
)
_PROFILE: Literal[
    "creative-sample-real-asset-qualification-instruction-preparation-v2.3"
] = "creative-sample-real-asset-qualification-instruction-preparation-v2.3"
_MUTABLE_ALIAS_TOKENS = frozenset({"current", "latest", "newest"})
_OUTCOME_FILENAME_TOKENS = frozenset({"needs", "pass", "rejected"})
_UTC_SECONDS = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_ISSUE_ORDER: tuple[RealAssetQualificationIssueCodeV2, ...] = (
    "EVIDENCE_SCOPE_UNCLEAR",
    "POLICY_REQUIREMENT_NOT_MET",
    "QUALIFIER_REJECTED_ASSET_INTAKE",
    "OTHER_BLOCKING_ISSUE",
)


class TrustedLocalInstructionPreparationError(RuntimeError):
    """The local prepare-only instruction boundary failed closed."""


class TrustedLocalInstructionQuarantineRequired(TrustedLocalInstructionPreparationError):
    """A created workspace or Instruction could not be proven safe or deleted."""


class _CliArgumentError(RuntimeError):
    pass


class _FailClosedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        del message
        raise _CliArgumentError


def _parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _canonical_utc_model(value: str, *, field: str) -> str:
    if _UTC_SECONDS.fullmatch(value) is None:
        raise ValueError(f"{field} must be canonical UTC seconds")
    try:
        parsed = _parse_utc(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError(f"{field} must be canonical UTC seconds")
    return value


def _canonical_utc(value: str, *, field: str) -> str:
    try:
        return _canonical_utc_model(value, field=field)
    except ValueError as exc:
        raise TrustedLocalInstructionPreparationError(str(exc)) from exc


class _InstructionWorkspaceContextV23(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal["2.3.0"] = "2.3.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-qualification-instruction-workspace-context-v2.3"
    ] = "sdc.creative-sample-real-asset-qualification-instruction-workspace-context-v2.3"
    profile: Literal[
        "creative-sample-real-asset-qualification-instruction-preparation-v2.3"
    ] = _PROFILE
    context_id: str = Field(
        pattern=r"^real_asset_qualification_instruction_context_v23_[0-9a-f]{20}$"
    )
    request_id: str = Field(pattern=r"^real_asset_qualification_request_v2_[0-9a-f]{20}$")
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    requested_at: str
    request_valid_until: str
    prepared_at: str
    policy_id: Literal["creative-sample-real-asset-qualification-policy"]
    policy_version: Literal["2.0.0"]
    policy_document_sha256: str = Field(pattern=_LOWER_SHA256)
    qualification_scope: Literal["ASSET_INTAKE_ONLY"] = "ASSET_INTAKE_ONLY"
    qualifier_role: Literal["INDEPENDENT_QUALIFIER"] = "INDEPENDENT_QUALIFIER"
    qualifier_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    draft_document_type: Literal[
        "sdc.creative-sample-real-asset-qualification-decision-instruction-draft-v2.3"
    ] = _DRAFT_DOCUMENT_TYPE
    status: Literal["AWAITING_EXPLICIT_QUALIFIER_INPUT"] = (
        "AWAITING_EXPLICIT_QUALIFIER_INPUT"
    )
    rights_manifest_created: Literal[False] = False
    rights_qualification_performed: Literal[False] = False
    eligible_for_separate_manifest_design_review: Literal[False] = False
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    eligible_for_real_generation: Literal[False] = False
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @field_validator("requested_at", "request_valid_until", "prepared_at")
    @classmethod
    def validate_times(cls, value: str) -> str:
        return _canonical_utc_model(value, field="workspace timestamp")

    @model_validator(mode="after")
    def validate_context(self) -> _InstructionWorkspaceContextV23:
        if not (_parse_utc(self.requested_at) <= _parse_utc(self.prepared_at)):
            raise ValueError("workspace cannot precede its Request")
        if not (_parse_utc(self.prepared_at) < _parse_utc(self.request_valid_until)):
            raise ValueError("workspace requires one currently valid Request")
        expected = stable_id(
            "real_asset_qualification_instruction_context_v23",
            self.model_dump(mode="json", exclude={"context_id"}),
        )
        if self.context_id != expected:
            raise ValueError("context ID must bind the complete mechanical context")
        return self


class _QualificationInstructionDraftV23(BaseModel):
    """Strict untrusted export; exactly four fields carry a human conclusion."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal["2.3.0"]
    document_type: Literal[
        "sdc.creative-sample-real-asset-qualification-decision-instruction-draft-v2.3"
    ]
    profile: Literal[
        "creative-sample-real-asset-qualification-instruction-preparation-v2.3"
    ]
    status: Literal["UNTRUSTED_DRAFT"]
    context_id: str = Field(
        pattern=r"^real_asset_qualification_instruction_context_v23_[0-9a-f]{20}$"
    )
    context_sha256: str = Field(pattern=_LOWER_SHA256)
    request_id: str = Field(pattern=r"^real_asset_qualification_request_v2_[0-9a-f]{20}$")
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    qualifier_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    decision_at: str
    decision: RealAssetQualificationDecisionV2
    qualification_issue_codes: tuple[RealAssetQualificationIssueCodeV2, ...] = Field(
        max_length=4
    )
    qualification_basis: str = Field(min_length=1, max_length=1000)

    @field_validator("decision_at")
    @classmethod
    def validate_decision_at(cls, value: str) -> str:
        return _canonical_utc_model(value, field="decision_at")

    @field_validator("qualification_basis")
    @classmethod
    def validate_basis(cls, value: str) -> str:
        if value != value.strip() or value != normalize("NFC", value):
            raise ValueError("qualification basis must be trimmed NFC text")
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("qualification basis must not contain control characters")
        return value

    @field_validator("qualification_issue_codes")
    @classmethod
    def validate_issues(
        cls, value: tuple[RealAssetQualificationIssueCodeV2, ...]
    ) -> tuple[RealAssetQualificationIssueCodeV2, ...]:
        if len(value) != len(set(value)):
            raise ValueError("qualification issue codes must be unique")
        if value != tuple(code for code in _ISSUE_ORDER if code in value):
            raise ValueError("qualification issue codes must use canonical order")
        return value

    @model_validator(mode="after")
    def validate_outcome(self) -> _QualificationInstructionDraftV23:
        positive = self.decision == "PASS_ASSET_INTAKE_ONLY"
        if positive == bool(self.qualification_issue_codes):
            raise ValueError(
                "positive decisions require no issue; negative decisions require an issue"
            )
        rejection = "QUALIFIER_REJECTED_ASSET_INTAKE"
        if self.decision == "REJECTED" and rejection not in self.qualification_issue_codes:
            raise ValueError("rejected decisions require the qualifier rejection issue code")
        if self.decision == "NEEDS_HUMAN_REVIEW" and rejection in self.qualification_issue_codes:
            raise ValueError("human-review decisions cannot contain the rejection issue code")
        return self


@dataclass(frozen=True, slots=True)
class TrustedLocalInstructionWorkspace:
    """A verified exact five-file local workspace."""

    root: Path
    index_path: Path
    context_path: Path
    context_id: str
    context_sha256: str


@dataclass(frozen=True, slots=True)
class _FileSeal:
    path: Path
    sha256: str
    size_bytes: int
    identity: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class _InputPaths:
    request: Path
    qualifier_ref: Path


@dataclass(frozen=True, slots=True)
class _InputSnapshot:
    request: CreativeSampleRealAssetQualificationRequestV2
    request_seal: _FileSeal
    qualifier_ref: _FileSeal


@dataclass(frozen=True, slots=True)
class _WorkspaceSnapshot:
    inputs: _InputSnapshot
    context: _InstructionWorkspaceContextV23
    context_sha256: str
    root_identity: tuple[int, int, int, int]
    files: tuple[_FileSeal, ...]


@dataclass(frozen=True, slots=True)
class _FinalizeSnapshot:
    workspace: _WorkspaceSnapshot
    draft: _QualificationInstructionDraftV23
    draft_seal: _FileSeal
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22 | None = None
    instruction_seal: _FileSeal | None = None


@dataclass(frozen=True, slots=True)
class _OutputTarget:
    path: Path
    parent: Path
    parent_physical_identity: tuple[int, int]


@dataclass(frozen=True, slots=True)
class _WorkspaceTarget:
    root: Path
    parent: Path
    parent_physical_identity: tuple[int, int]


@dataclass(slots=True)
class _CreatedInstruction:
    target: _OutputTarget
    descriptor: int
    parent_guard: int
    windows_parent_guard: bool
    seal: _FileSeal | None = None
    closed: bool = False


@dataclass(slots=True)
class _CreatedWorkspace:
    target: _WorkspaceTarget
    parent_guard: int
    windows_parent_guard: bool
    root_guard: int
    windows_root_guard: bool
    root_physical_identity: tuple[int, int]
    descriptors: dict[str, int]
    file_physical_identities: dict[str, tuple[int, int]]
    closed: bool = False


if sys.platform == "win32":
    import ctypes as _windows_ctypes
    import msvcrt as _windows_msvcrt
    from ctypes import wintypes as _windows_wintypes

    def _acquire_windows_directory_guard(path: Path, *, field: str) -> int:
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
            str(path),
            0x0080 | 0x00010000,
            0x00000001 | 0x00000002,
            None,
            3,
            0x02000000,
            None,
        )
        invalid = _windows_ctypes.c_void_p(-1).value
        if handle == invalid:
            raise TrustedLocalInstructionPreparationError(
                f"{field} could not be guarded"
            )
        return int(handle)

    def _acquire_windows_parent_guard(target: _OutputTarget) -> int:
        return _acquire_windows_directory_guard(
            target.parent,
            field="instruction output parent",
        )

    def _close_windows_handle(handle: int) -> None:
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (_windows_wintypes.HANDLE,)
        close_handle.restype = _windows_wintypes.BOOL
        if not close_handle(handle):
            error = _windows_ctypes.get_last_error()
            raise OSError(error, "CloseHandle failed")

    def _open_windows_exclusive_path(path: Path) -> int:
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
            str(path),
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
                raise FileExistsError(str(path))
            raise OSError(error, "CreateFileW failed")
        try:
            return _windows_msvcrt.open_osfhandle(
                int(handle), os.O_RDWR | getattr(os, "O_BINARY", 0)
            )
        except OSError:
            _close_windows_handle(int(handle))
            raise

    def _open_windows_exclusive(target: _OutputTarget) -> int:
        return _open_windows_exclusive_path(target.path)

    def _delete_open_windows(descriptor: int) -> bool:
        handle = _windows_msvcrt.get_osfhandle(descriptor)
        return _delete_windows_handle(int(handle))

    def _delete_windows_handle(handle: int) -> bool:
        class FileDispositionInfo(_windows_ctypes.Structure):
            _fields_ = (("DeleteFile", _windows_wintypes.BOOL),)

        disposition = FileDispositionInfo(True)
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        setter = kernel32.SetFileInformationByHandle
        setter.argtypes = (
            _windows_wintypes.HANDLE,
            _windows_ctypes.c_int,
            _windows_wintypes.LPVOID,
            _windows_wintypes.DWORD,
        )
        setter.restype = _windows_wintypes.BOOL
        return bool(
            setter(
                handle,
                4,
                _windows_ctypes.byref(disposition),
                _windows_ctypes.sizeof(disposition),
            )
        )

else:

    def _windows_unavailable() -> Never:
        raise OSError("Windows-only instruction output helper is unavailable")

    def _acquire_windows_directory_guard(path: Path, *, field: str) -> int:
        del path, field
        return _windows_unavailable()

    def _acquire_windows_parent_guard(target: _OutputTarget) -> int:
        del target
        return _windows_unavailable()

    def _close_windows_handle(handle: int) -> None:
        del handle
        _windows_unavailable()

    def _open_windows_exclusive(target: _OutputTarget) -> int:
        del target
        return _windows_unavailable()

    def _open_windows_exclusive_path(path: Path) -> int:
        del path
        return _windows_unavailable()

    def _delete_open_windows(descriptor: int) -> bool:
        del descriptor
        return _windows_unavailable()

    def _delete_windows_handle(handle: int) -> bool:
        del handle
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


def _reject_json_constant(value: str) -> None:
    del value
    raise TrustedLocalInstructionPreparationError("non-finite JSON numbers are forbidden")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TrustedLocalInstructionPreparationError("duplicate JSON key is forbidden")
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
        raise TrustedLocalInstructionPreparationError(
            f"{field} is not bounded canonical JSON"
        )
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise TrustedLocalInstructionPreparationError(
            f"{field} is not strict UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        raise TrustedLocalInstructionPreparationError(f"{field} must contain one JSON object")
    try:
        parsed = model.model_validate_json(raw, strict=True)
    except ValidationError as exc:
        raise TrustedLocalInstructionPreparationError(
            f"{field} violates its strict contract"
        ) from exc
    try:
        canonical = _canonical_document(parsed)
    except UnicodeError as exc:
        raise TrustedLocalInstructionPreparationError(
            f"{field} contains text outside canonical UTF-8"
        ) from exc
    if raw != canonical:
        raise TrustedLocalInstructionPreparationError(f"{field} bytes are not canonical")
    return parsed


def _file_seal(source: SafeLocalFile) -> _FileSeal:
    return _FileSeal(
        path=source.path,
        sha256=source.sha256,
        size_bytes=source.size_bytes,
        identity=source.identity,
    )


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _nearest_git_root(path: Path) -> Path | None:
    cursor = path if os.path.lexists(path) and path.is_dir() else path.parent
    while True:
        try:
            (cursor / ".git").lstat()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise TrustedLocalInstructionPreparationError(
                "local path Git isolation could not be checked"
            ) from exc
        else:
            return cursor
        parent = cursor.parent
        if parent == cursor:
            return None
        cursor = parent


def _reject_mutable_alias(path: Path, *, field: str) -> None:
    components = path.parts[1:] if path.anchor else path.parts
    for component in components:
        tokens = frozenset(filter(None, re.split(r"[^a-z0-9]+", component.casefold())))
        if tokens & _MUTABLE_ALIAS_TOKENS:
            raise TrustedLocalInstructionPreparationError(
                f"{field} cannot use a mutable alias path"
            )


def _reject_outcome_filename(path: Path, *, field: str) -> None:
    tokens = frozenset(filter(None, re.split(r"[^a-z0-9]+", path.stem.casefold())))
    if tokens & _OUTCOME_FILENAME_TOKENS:
        raise TrustedLocalInstructionPreparationError(
            f"{field} filename must not disclose a qualification outcome"
        )


def _safe_absolute(path: Path, *, must_exist: bool, field: str) -> Path:
    if not path.is_absolute():
        raise TrustedLocalInstructionPreparationError(f"{field} must be an absolute local path")
    _reject_mutable_alias(path, field=field)
    try:
        absolute = validate_local_path(path, must_exist=must_exist)
        if not must_exist:
            validate_local_path(absolute.parent, must_exist=True)
    except (CreativeMediaError, OSError) as exc:
        raise TrustedLocalInstructionPreparationError(
            f"{field} is not a safe local path"
        ) from exc
    _reject_mutable_alias(absolute, field=field)
    if _nearest_git_root(absolute) is not None:
        raise TrustedLocalInstructionPreparationError(
            f"{field} must remain outside every Git tree"
        )
    return absolute


def _read_safe(path: Path, *, max_bytes: int, field: str) -> SafeLocalFile:
    absolute = _safe_absolute(path, must_exist=True, field=field)
    try:
        return read_safe_local_file(absolute, max_bytes=max_bytes)
    except RealAssetMediaError as exc:
        raise TrustedLocalInstructionPreparationError(
            f"{field} must be one stable non-linked local file"
        ) from exc


def _read_request(
    path: Path,
) -> tuple[CreativeSampleRealAssetQualificationRequestV2, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field="qualification Request")
    try:
        request = parse_real_asset_qualification_request_v2_json(source.data)
    except RealAssetQualificationV2Error as exc:
        raise TrustedLocalInstructionPreparationError(
            "qualification Request violates its strict contract"
        ) from exc
    if source.data != _canonical_document(request):
        raise TrustedLocalInstructionPreparationError(
            "qualification Request bytes are not canonical"
        )
    return request, _file_seal(source)


def _read_draft(path: Path) -> tuple[_QualificationInstructionDraftV23, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field="untrusted instruction draft")
    return (
        _parse_canonical_json(source, _QualificationInstructionDraftV23, field="untrusted draft"),
        _file_seal(source),
    )


def _read_instruction(
    path: Path,
) -> tuple[CreativeSampleRealAssetQualificationDecisionInstructionV22, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field="retained Instruction")
    return (
        _parse_canonical_json(
            source,
            CreativeSampleRealAssetQualificationDecisionInstructionV22,
            field="retained Instruction",
        ),
        _file_seal(source),
    )


def _directory_identity(path: Path, *, field: str) -> tuple[int, int, int, int]:
    try:
        info = path.lstat()
    except OSError as exc:
        raise TrustedLocalInstructionPreparationError(f"{field} could not be inspected") from exc
    attributes = int(getattr(info, "st_file_attributes", 0))
    is_junction = getattr(path, "is_junction", None)
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_ISLNK(info.st_mode)
        or bool(attributes & 0x400)
        or bool(is_junction is not None and is_junction())
    ):
        raise TrustedLocalInstructionPreparationError(
            f"{field} must be one non-linked directory"
        )
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _normalize_inputs(request_path: Path, qualifier_ref_path: Path) -> _InputPaths:
    request = _safe_absolute(request_path, must_exist=True, field="qualification Request")
    qualifier = _safe_absolute(
        qualifier_ref_path, must_exist=True, field="qualifier reference"
    )
    if request == qualifier:
        raise TrustedLocalInstructionPreparationError(
            "Request and qualifier reference must be distinct"
        )
    return _InputPaths(request=request, qualifier_ref=qualifier)


def _capture_inputs(paths: _InputPaths) -> _InputSnapshot:
    request, request_seal = _read_request(paths.request)
    qualifier = _file_seal(
        _read_safe(
            paths.qualifier_ref,
            max_bytes=_PRIVATE_RECORD_MAX_BYTES,
            field="qualifier reference",
        )
    )
    _assert_non_aliasing((request_seal, qualifier))
    reserved = _request_reserved_digests(request)
    if request_seal.sha256 in reserved or qualifier.sha256 in reserved:
        raise TrustedLocalInstructionPreparationError(
            "Request preparation inputs alias a reserved Request digest"
        )
    return _InputSnapshot(
        request=request,
        request_seal=request_seal,
        qualifier_ref=qualifier,
    )


def _request_reserved_digests(
    request: CreativeSampleRealAssetQualificationRequestV2,
) -> frozenset[str]:
    payload = request.model_dump(mode="json")
    return frozenset(
        value
        for key, value in payload.items()
        if key.endswith("_sha256") and isinstance(value, str)
    )


def _assert_non_aliasing(files: tuple[_FileSeal, ...]) -> None:
    if len({item.path for item in files}) != len(files):
        raise TrustedLocalInstructionPreparationError("local inputs contain a path alias")
    if len({(item.identity[0], item.identity[1]) for item in files}) != len(files):
        raise TrustedLocalInstructionPreparationError(
            "local inputs contain a physical file alias"
        )
    if len({item.sha256 for item in files}) != len(files):
        raise TrustedLocalInstructionPreparationError(
            "local inputs contain a byte digest alias"
        )


def _assert_input_unchanged(before: _InputSnapshot, after: _InputSnapshot) -> None:
    if before != after:
        raise TrustedLocalInstructionPreparationError(
            "Request or qualifier reference drifted during verification"
        )


def _assert_observed_request_time(
    request: CreativeSampleRealAssetQualificationRequestV2,
    observed_at: str,
) -> None:
    observed = _parse_utc(_canonical_utc(observed_at, field="observed_at"))
    if not (_parse_utc(request.requested_at) <= observed < _parse_utc(request.request_valid_until)):
        raise TrustedLocalInstructionPreparationError(
            "observed_at must fall inside the Request validity interval"
        )


def _build_context(
    snapshot: _InputSnapshot,
    *,
    prepared_at: str,
) -> _InstructionWorkspaceContextV23:
    request = snapshot.request
    payload: dict[str, object] = {
        "schema_version": "2.3.0",
        "document_type": (
            "sdc.creative-sample-real-asset-qualification-instruction-workspace-context-v2.3"
        ),
        "profile": _PROFILE,
        "request_id": request.request_id,
        "request_sha256": snapshot.request_seal.sha256,
        "requested_at": request.requested_at,
        "request_valid_until": request.request_valid_until,
        "prepared_at": prepared_at,
        "policy_id": request.policy_id,
        "policy_version": request.policy_version,
        "policy_document_sha256": request.policy_document_sha256,
        "qualification_scope": "ASSET_INTAKE_ONLY",
        "qualifier_role": "INDEPENDENT_QUALIFIER",
        "qualifier_ref_sha256": snapshot.qualifier_ref.sha256,
        "draft_document_type": _DRAFT_DOCUMENT_TYPE,
        "status": "AWAITING_EXPLICIT_QUALIFIER_INPUT",
        "rights_manifest_created": False,
        "rights_qualification_performed": False,
        "eligible_for_separate_manifest_design_review": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return _InstructionWorkspaceContextV23.model_validate(
        {
            **payload,
            "context_id": stable_id(
                "real_asset_qualification_instruction_context_v23", payload
            ),
        },
        strict=True,
    )


def _read_static_asset(name: str) -> bytes:
    if name not in _STATIC_ASSET_NAMES:
        raise TrustedLocalInstructionPreparationError("unknown workspace static asset")
    path = Path(__file__).with_name(_ASSET_DIRECTORY_NAME) / name
    try:
        before = path.lstat()
        attributes = int(getattr(before, "st_file_attributes", 0))
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_ISLNK(before.st_mode)
            or bool(attributes & 0x400)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > _STATIC_ASSET_MAX_BYTES
        ):
            raise OSError("unsafe package asset")
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            raw = handle.read(_STATIC_ASSET_MAX_BYTES + 1)
        after = path.lstat()
    except OSError as exc:
        raise TrustedLocalInstructionPreparationError(
            "workspace static asset could not be read safely"
        ) from exc
    def identity(item: os.stat_result) -> tuple[int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)

    if (
        len(raw) != before.st_size
        or len(raw) > _STATIC_ASSET_MAX_BYTES
        or identity(before) != identity(opened)
        or identity(opened) != identity(after)
        or after.st_nlink != 1
    ):
        raise TrustedLocalInstructionPreparationError(
            "workspace static asset drifted while it was read"
        )
    return raw


def _context_script(context: _InstructionWorkspaceContextV23, digest: str) -> bytes:
    compact = json.dumps(
        context.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    quoted = json.dumps(compact, ensure_ascii=True)
    return (
        '"use strict";\n'
        "const sdcDeepFreeze = (value) => {\n"
        "  if (value && typeof value === \"object\") {\n"
        "    Object.values(value).forEach(sdcDeepFreeze);\n"
        "    Object.freeze(value);\n"
        "  }\n"
        "  return value;\n"
        "};\n"
        f"const sdcInstructionContext = sdcDeepFreeze(JSON.parse({quoted}));\n"
        "Object.defineProperty(globalThis, \"SDC_QUALIFICATION_INSTRUCTION_CONTEXT\", {\n"
        "  configurable: false,\n"
        "  enumerable: true,\n"
        "  value: Object.freeze({\n"
        f'    context_sha256: "{digest}",\n'
        "    context: sdcInstructionContext\n"
        "  }),\n"
        "  writable: false\n"
        "});\n"
    ).encode()


def _workspace_payloads(
    context: _InstructionWorkspaceContextV23,
) -> tuple[dict[str, bytes], str]:
    context_bytes = _canonical_document(context)
    digest = hashlib.sha256(context_bytes).hexdigest()
    return (
        {
            **{name: _read_static_asset(name) for name in _STATIC_ASSET_NAMES},
            _CONTEXT_JSON_NAME: context_bytes,
            _CONTEXT_SCRIPT_NAME: _context_script(context, digest),
        },
        digest,
    )


def _validate_workspace_target(
    root_path: Path,
    *,
    paths: _InputPaths,
) -> _WorkspaceTarget:
    root = _safe_absolute(root_path, must_exist=False, field="instruction workspace")
    if os.path.lexists(root):
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace must be one new directory"
        )
    if any(_paths_overlap(root, item) for item in (paths.request, paths.qualifier_ref)):
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace overlaps an immutable input"
        )
    for area in (paths.request.parent, paths.qualifier_ref.parent):
        if _paths_overlap(root.parent, area):
            raise TrustedLocalInstructionPreparationError(
                "workspace parent must use a separate non-intersecting trust area"
            )
    identity = _directory_identity(root.parent, field="workspace output parent")
    return _WorkspaceTarget(
        root=root,
        parent=root.parent,
        parent_physical_identity=(identity[0], identity[1]),
    )


def _revalidate_workspace_target(
    target: _WorkspaceTarget,
    *,
    must_exist: bool,
) -> None:
    absolute = _safe_absolute(
        target.root,
        must_exist=must_exist,
        field="instruction workspace",
    )
    if absolute != target.root or os.path.lexists(absolute) != must_exist:
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace target drifted"
        )
    identity = _directory_identity(target.parent, field="workspace output parent")
    if (identity[0], identity[1]) != target.parent_physical_identity:
        raise TrustedLocalInstructionPreparationError(
            "workspace output parent identity drifted"
        )
    if must_exist:
        _directory_identity(target.root, field="instruction workspace")


def _normalize_workspace(root_path: Path, *, paths: _InputPaths) -> Path:
    root = _safe_absolute(root_path, must_exist=True, field="instruction workspace")
    _directory_identity(root, field="instruction workspace")
    if any(_paths_overlap(root, item) for item in (paths.request, paths.qualifier_ref)):
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace overlaps an immutable input"
        )
    if any(
        _paths_overlap(root.parent, area)
        for area in (paths.request.parent, paths.qualifier_ref.parent)
    ):
        raise TrustedLocalInstructionPreparationError(
            "workspace parent must use a separate non-intersecting trust area"
        )
    return root


def _read_workspace_file(path: Path, *, field: str) -> tuple[bytes, _FileSeal]:
    source = _read_safe(path, max_bytes=_STATIC_ASSET_MAX_BYTES, field=field)
    return source.data, _file_seal(source)


def _bounded_workspace_names(root: Path, *, field: str) -> frozenset[str]:
    names: list[str] = []
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                if len(names) >= len(_WORKSPACE_NAMES):
                    raise TrustedLocalInstructionPreparationError(
                        f"{field} contains more than the bounded member set"
                    )
                names.append(entry.name)
    except TrustedLocalInstructionPreparationError:
        raise
    except OSError as exc:
        raise TrustedLocalInstructionPreparationError(
            f"{field} could not be enumerated"
        ) from exc
    if len(names) != len(set(names)):
        raise TrustedLocalInstructionPreparationError(
            f"{field} contains ambiguous member names"
        )
    return frozenset(names)


def _capture_workspace(
    paths: _InputPaths,
    root: Path,
) -> _WorkspaceSnapshot:
    inputs = _capture_inputs(paths)
    root_before = _directory_identity(root, field="instruction workspace")
    names = _bounded_workspace_names(root, field="instruction workspace")
    if names != frozenset(_WORKSPACE_NAMES):
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace must contain the exact five committed files"
        )
    sources: dict[str, tuple[bytes, _FileSeal]] = {}
    for name in _WORKSPACE_NAMES:
        sources[name] = _read_workspace_file(
            root / name, field=f"instruction workspace file {name}"
        )
    context_source = SafeLocalFile(
        path=sources[_CONTEXT_JSON_NAME][1].path,
        data=sources[_CONTEXT_JSON_NAME][0],
        sha256=sources[_CONTEXT_JSON_NAME][1].sha256,
        size_bytes=sources[_CONTEXT_JSON_NAME][1].size_bytes,
        identity=sources[_CONTEXT_JSON_NAME][1].identity,
    )
    context = _parse_canonical_json(
        context_source,
        _InstructionWorkspaceContextV23,
        field="workspace context",
    )
    expected, digest = _workspace_payloads(context)
    if any(sources[name][0] != expected[name] for name in _WORKSPACE_NAMES):
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace bytes do not match their exact rebuilt closure"
        )
    if context.request_id != inputs.request.request_id or (
        context.request_sha256 != inputs.request_seal.sha256
        or context.qualifier_ref_sha256 != inputs.qualifier_ref.sha256
        or context.requested_at != inputs.request.requested_at
        or context.request_valid_until != inputs.request.request_valid_until
        or context.policy_id != inputs.request.policy_id
        or context.policy_version != inputs.request.policy_version
        or context.policy_document_sha256 != inputs.request.policy_document_sha256
    ):
        raise TrustedLocalInstructionPreparationError(
            "workspace context does not bind the supplied Request and qualifier"
        )
    root_after = _directory_identity(root, field="instruction workspace")
    names_after = _bounded_workspace_names(
        root,
        field="instruction workspace",
    )
    if root_before != root_after or names_after != frozenset(_WORKSPACE_NAMES):
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace drifted during verification"
        )
    files = tuple(sources[name][1] for name in _WORKSPACE_NAMES)
    _assert_non_aliasing((inputs.request_seal, inputs.qualifier_ref, *files))
    reserved = _request_reserved_digests(inputs.request)
    if any(file.sha256 in reserved for file in files):
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace aliases a reserved Request digest"
        )
    return _WorkspaceSnapshot(
        inputs=inputs,
        context=context,
        context_sha256=digest,
        root_identity=root_before,
        files=files,
    )


def _assert_workspace_unchanged(
    before: _WorkspaceSnapshot,
    after: _WorkspaceSnapshot,
) -> None:
    if before != after:
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace closure drifted during verification"
        )


def _capture_finalize(
    paths: _InputPaths,
    root: Path,
    draft_path: Path,
    *,
    instruction_path: Path | None = None,
) -> _FinalizeSnapshot:
    workspace = _capture_workspace(paths, root)
    draft, draft_seal = _read_draft(draft_path)
    context = workspace.context
    if (
        draft.context_id != context.context_id
        or draft.context_sha256 != workspace.context_sha256
        or draft.request_id != context.request_id
        or draft.request_sha256 != context.request_sha256
        or draft.qualifier_ref_sha256 != context.qualifier_ref_sha256
    ):
        raise TrustedLocalInstructionPreparationError(
            "untrusted draft does not bind the exact workspace context"
        )
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22 | None = None
    instruction_seal: _FileSeal | None = None
    files = (
        *workspace.files,
        workspace.inputs.request_seal,
        workspace.inputs.qualifier_ref,
        draft_seal,
    )
    if instruction_path is not None:
        instruction, instruction_seal = _read_instruction(instruction_path)
        files = (*files, instruction_seal)
    _assert_non_aliasing(files)
    reserved = _request_reserved_digests(workspace.inputs.request)
    if draft_seal.sha256 in reserved or (
        instruction_seal is not None and instruction_seal.sha256 in reserved
    ):
        raise TrustedLocalInstructionPreparationError(
            "draft or Instruction aliases a reserved Request digest"
        )
    return _FinalizeSnapshot(
        workspace=workspace,
        draft=draft,
        draft_seal=draft_seal,
        instruction=instruction,
        instruction_seal=instruction_seal,
    )


def _assert_finalize_unchanged(before: _FinalizeSnapshot, after: _FinalizeSnapshot) -> None:
    if before != after:
        raise TrustedLocalInstructionPreparationError(
            "instruction preparation closure drifted during verification"
        )


def _build_instruction(
    snapshot: _FinalizeSnapshot,
) -> CreativeSampleRealAssetQualificationDecisionInstructionV22:
    request = snapshot.workspace.inputs.request
    draft = snapshot.draft
    payload: dict[str, object] = {
        "schema_version": "2.2.0",
        "document_type": (
            "sdc.creative-sample-real-asset-qualification-decision-instruction-v2.2"
        ),
        "profile": (
            "creative-sample-real-asset-qualification-decision-finalization-v2.2"
        ),
        "request_id": request.request_id,
        "request_sha256": snapshot.workspace.inputs.request_seal.sha256,
        "policy_id": request.policy_id,
        "policy_version": request.policy_version,
        "policy_document_sha256": request.policy_document_sha256,
        "qualification_scope": "ASSET_INTAKE_ONLY",
        "qualifier_role": "INDEPENDENT_QUALIFIER",
        "qualifier_ref_sha256": snapshot.workspace.inputs.qualifier_ref.sha256,
        "decision_at": draft.decision_at,
        "decision": draft.decision,
        "qualification_issue_codes": draft.qualification_issue_codes,
        "qualification_basis": draft.qualification_basis,
        "status": "DECISION_INSTRUCTION_RECORDED",
        "rights_manifest_created": False,
        "rights_qualification_performed": False,
        "eligible_for_separate_manifest_design_review": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetQualificationDecisionInstructionV22.model_validate(
        {
            **payload,
            "instruction_id": stable_id(
                "real_asset_qualification_decision_instruction_v22", payload
            ),
        },
        strict=True,
    )


def _assert_draft_time(
    snapshot: _FinalizeSnapshot,
    *,
    observed_at: str | None,
) -> None:
    context = snapshot.workspace.context
    decision = _parse_utc(snapshot.draft.decision_at)
    prepared = _parse_utc(context.prepared_at)
    valid_until = _parse_utc(context.request_valid_until)
    if not (prepared <= decision < valid_until):
        raise TrustedLocalInstructionPreparationError(
            "decision_at must follow workspace preparation inside Request validity"
        )
    if observed_at is not None:
        observed = _parse_utc(_canonical_utc(observed_at, field="observed_at"))
        if not (decision <= observed < valid_until):
            raise TrustedLocalInstructionPreparationError(
                "observed_at must follow decision_at inside Request validity"
            )


def _validate_draft_path(path: Path, *, paths: _InputPaths, root: Path) -> Path:
    draft = _safe_absolute(path, must_exist=True, field="untrusted instruction draft")
    _reject_outcome_filename(draft, field="untrusted instruction draft")
    if draft.suffix.casefold() != ".json":
        raise TrustedLocalInstructionPreparationError(
            "untrusted instruction draft must use a JSON filename"
        )
    if any(_paths_overlap(draft, item) for item in (paths.request, paths.qualifier_ref, root)):
        raise TrustedLocalInstructionPreparationError(
            "untrusted instruction draft must remain outside immutable inputs and workspace"
        )
    return draft


def _assert_separate_output_parent(
    parent: Path,
    *,
    paths: _InputPaths,
    root: Path,
    draft: Path,
) -> None:
    areas = (paths.request.parent, paths.qualifier_ref.parent, root, draft.parent)
    if any(_paths_overlap(parent, area) for area in areas):
        raise TrustedLocalInstructionPreparationError(
            "Instruction parent must use a separate non-intersecting trust area"
        )


def _validate_output(
    output_path: Path,
    *,
    paths: _InputPaths,
    root: Path,
    draft: Path,
    must_exist: bool,
) -> _OutputTarget:
    output = _safe_absolute(
        output_path,
        must_exist=must_exist,
        field="retained Instruction" if must_exist else "Instruction output",
    )
    _reject_outcome_filename(output, field="retained Instruction")
    if output.suffix.casefold() != ".json":
        raise TrustedLocalInstructionPreparationError(
            "retained Instruction must use a JSON filename"
        )
    if must_exist != os.path.lexists(output):
        raise TrustedLocalInstructionPreparationError(
            "Instruction output existence does not match the operation"
        )
    named = (paths.request, paths.qualifier_ref, root, draft)
    if any(_paths_overlap(output, item) for item in named):
        raise TrustedLocalInstructionPreparationError(
            "retained Instruction overlaps an immutable input"
        )
    _assert_separate_output_parent(
        output.parent, paths=paths, root=root, draft=draft
    )
    identity = _directory_identity(output.parent, field="Instruction output parent")
    return _OutputTarget(
        path=output,
        parent=output.parent,
        parent_physical_identity=(identity[0], identity[1]),
    )


def _revalidate_output(target: _OutputTarget, *, must_exist: bool) -> None:
    absolute = _safe_absolute(
        target.path,
        must_exist=must_exist,
        field="retained Instruction" if must_exist else "Instruction output",
    )
    if absolute != target.path or os.path.lexists(absolute) != must_exist:
        raise TrustedLocalInstructionPreparationError(
            "Instruction output target drifted"
        )
    identity = _directory_identity(target.parent, field="Instruction output parent")
    if (identity[0], identity[1]) != target.parent_physical_identity:
        raise TrustedLocalInstructionPreparationError(
            "Instruction output parent identity drifted"
        )


def _acquire_parent_guard(target: _OutputTarget) -> tuple[int, bool]:
    if sys.platform == "win32":
        return _acquire_windows_parent_guard(target), True
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    return os.open(target.parent, flags), False


def _close_parent_guard(created: _CreatedInstruction) -> None:
    if created.windows_parent_guard:
        _close_windows_handle(created.parent_guard)
    else:
        os.close(created.parent_guard)


def _open_exclusive(target: _OutputTarget, parent_guard: int) -> int:
    if sys.platform == "win32":
        return _open_windows_exclusive(target)
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    return os.open(target.path.name, flags, 0o600, dir_fd=parent_guard)


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _read_open_instruction(
    created: _CreatedInstruction,
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
) -> _FileSeal:
    raw = _canonical_document(instruction)
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
        named = created.target.path.lstat()
    except OSError as exc:
        raise TrustedLocalInstructionPreparationError(
            "created Instruction could not be inspected"
        ) from exc
    opened_identity = _stat_identity(opened)
    attributes = int(getattr(named, "st_file_attributes", 0))
    if (
        opened_identity != _stat_identity(named)
        or not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(named.st_mode)
        or stat.S_ISLNK(named.st_mode)
        or bool(attributes & 0x400)
        or opened.st_nlink != 1
        or named.st_nlink != 1
    ):
        raise TrustedLocalInstructionPreparationError(
            "created Instruction identity drifted"
        )
    data = bytes(observed)
    source = SafeLocalFile(
        path=created.target.path,
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        identity=opened_identity,
    )
    parsed = _parse_canonical_json(
        source,
        CreativeSampleRealAssetQualificationDecisionInstructionV22,
        field="created Instruction",
    )
    if parsed != instruction or data != raw:
        raise TrustedLocalInstructionPreparationError(
            "written Instruction failed exact verification"
        )
    return _file_seal(source)


def _invalidate_open(descriptor: int) -> bool:
    try:
        os.ftruncate(descriptor, 0)
        os.fsync(descriptor)
        if os.fstat(descriptor).st_size == 0:
            return True
    except OSError:
        pass
    return _emergency_poison(descriptor)


def _emergency_poison(descriptor: int) -> bool:
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        if os.write(descriptor, b"\0") != 1:
            return False
        os.fsync(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        return os.read(descriptor, 1) == b"\0"
    except OSError:
        return False


def _unlink_open_posix(
    created: _CreatedInstruction,
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


def _rollback_created(created: _CreatedInstruction) -> None:
    if created.closed:
        return
    invalidated = False
    deleted = False
    opened_physical: tuple[int, int] | None = None
    try:
        try:
            info = os.fstat(created.descriptor)
            opened_physical = (info.st_dev, info.st_ino)
        except BaseException:
            pass
        try:
            invalidated = _invalidate_open(created.descriptor)
        except BaseException:
            invalidated = False
        if not invalidated:
            try:
                invalidated = _emergency_poison(created.descriptor)
            except BaseException:
                invalidated = False
        try:
            if sys.platform == "win32":
                deleted = _delete_open_windows(created.descriptor)
            elif opened_physical is not None:
                deleted = _unlink_open_posix(created, opened_physical)
        except BaseException:
            deleted = False
    finally:
        try:
            os.close(created.descriptor)
        except BaseException:
            pass
        try:
            _close_parent_guard(created)
        except BaseException:
            pass
        created.closed = True
    if not invalidated and not deleted:
        raise TrustedLocalInstructionQuarantineRequired(
            "created Instruction rollback failed closed; output requires quarantine"
        )


def _commit_created(
    created: _CreatedInstruction,
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
) -> None:
    if created.closed or created.seal is None:
        raise TrustedLocalInstructionPreparationError(
            "created Instruction is not publishable"
        )
    try:
        _revalidate_output(created.target, must_exist=True)
        if _read_open_instruction(created, instruction) != created.seal:
            raise TrustedLocalInstructionPreparationError(
                "created Instruction drifted before commit"
            )
        if not created.windows_parent_guard:
            os.fsync(created.parent_guard)
        os.close(created.descriptor)
        _close_parent_guard(created)
        created.closed = True
    except BaseException as exc:
        try:
            _rollback_created(created)
        except TrustedLocalInstructionPreparationError:
            raise
        if isinstance(exc, TrustedLocalInstructionPreparationError):
            raise
        raise TrustedLocalInstructionPreparationError(
            "created Instruction commit failed closed"
        ) from exc


def _create_new_instruction(
    target: _OutputTarget,
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
) -> _CreatedInstruction:
    _revalidate_output(target, must_exist=False)
    guard = _acquire_parent_guard(target)
    descriptor: int | None = None
    created: _CreatedInstruction | None = None
    try:
        _revalidate_output(target, must_exist=False)
        descriptor = _open_exclusive(target, guard[0])
        created = _CreatedInstruction(
            target=target,
            descriptor=descriptor,
            parent_guard=guard[0],
            windows_parent_guard=guard[1],
        )
        raw = _canonical_document(instruction)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise OSError("short write")
            offset += written
        os.fsync(descriptor)
        created.seal = _read_open_instruction(created, instruction)
        _revalidate_output(target, must_exist=True)
        return created
    except FileExistsError as exc:
        if descriptor is None:
            if guard[1]:
                _close_windows_handle(guard[0])
            else:
                os.close(guard[0])
        raise TrustedLocalInstructionPreparationError(
            "Instruction output must be one new file"
        ) from exc
    except BaseException as exc:
        if created is not None:
            try:
                _rollback_created(created)
            except TrustedLocalInstructionPreparationError:
                raise
        else:
            try:
                if guard[1]:
                    _close_windows_handle(guard[0])
                else:
                    os.close(guard[0])
            except BaseException:
                pass
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        if isinstance(exc, TrustedLocalInstructionPreparationError):
            raise
        raise TrustedLocalInstructionPreparationError(
            "Instruction output could not be created safely"
        ) from exc


def _acquire_workspace_parent_guard(target: _WorkspaceTarget) -> tuple[int, bool]:
    if sys.platform == "win32":
        result = (
            _acquire_windows_directory_guard(
                target.parent,
                field="workspace output parent",
            ),
            True,
        )
    else:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        result = (os.open(target.parent, flags), False)
    try:
        observed = _guarded_directory_physical_identity(
            result[0],
            windows=result[1],
            path=target.parent,
        )
    except BaseException:
        _close_guard(result[0], windows=result[1])
        raise
    if observed != target.parent_physical_identity:
        _close_guard(result[0], windows=result[1])
        raise TrustedLocalInstructionPreparationError(
            "workspace output parent guard identity drifted"
        )
    return result


def _close_guard(descriptor: int, *, windows: bool) -> None:
    if windows:
        _close_windows_handle(descriptor)
    else:
        os.close(descriptor)


def _guarded_directory_physical_identity(
    descriptor: int,
    *,
    windows: bool,
    path: Path,
) -> tuple[int, int]:
    if windows:
        # The Windows guard denies delete/rename sharing.  Once it is acquired, the exact
        # named directory cannot be swapped before this physical path seal is sampled.
        identity = _directory_identity(path, field="guarded directory")
        return (identity[0], identity[1])
    try:
        info = os.fstat(descriptor)
    except OSError as exc:
        raise TrustedLocalInstructionPreparationError(
            "guarded directory identity could not be inspected"
        ) from exc
    if not stat.S_ISDIR(info.st_mode):
        raise TrustedLocalInstructionPreparationError(
            "guarded directory is not a directory"
        )
    return (info.st_dev, info.st_ino)


def _acquire_workspace_root_guard(
    target: _WorkspaceTarget,
    *,
    parent_guard: int,
) -> tuple[int, bool]:
    if sys.platform == "win32":
        return (
            _acquire_windows_directory_guard(
                target.root,
                field="created instruction workspace",
            ),
            True,
        )
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return os.open(target.root.name, flags, dir_fd=parent_guard), False


def _open_workspace_file(
    created: _CreatedWorkspace,
    name: str,
) -> int:
    if sys.platform == "win32":
        return _open_windows_exclusive_path(created.target.root / name)
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    return os.open(name, flags, 0o600, dir_fd=created.root_guard)


def _read_open_workspace_file(
    created: _CreatedWorkspace,
    name: str,
    expected: bytes,
) -> tuple[int, int]:
    descriptor = created.descriptors[name]
    try:
        opened = os.fstat(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        observed = bytearray()
        while len(observed) <= _STATIC_ASSET_MAX_BYTES:
            chunk = os.read(
                descriptor,
                min(65_536, _STATIC_ASSET_MAX_BYTES + 1 - len(observed)),
            )
            if not chunk:
                break
            observed.extend(chunk)
        named = (created.target.root / name).lstat()
    except OSError as exc:
        raise TrustedLocalInstructionPreparationError(
            "created workspace file could not be inspected"
        ) from exc
    attributes = int(getattr(named, "st_file_attributes", 0))
    if (
        _stat_identity(opened) != _stat_identity(named)
        or not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(named.st_mode)
        or stat.S_ISLNK(named.st_mode)
        or bool(attributes & 0x400)
        or opened.st_nlink != 1
        or named.st_nlink != 1
        or bytes(observed) != expected
    ):
        raise TrustedLocalInstructionPreparationError(
            "created workspace file failed exact opened-byte verification"
        )
    return (opened.st_dev, opened.st_ino)


def _unlink_open_posix_workspace_file(
    created: _CreatedWorkspace,
    name: str,
    opened_physical: tuple[int, int],
) -> bool:
    try:
        named = os.stat(name, dir_fd=created.root_guard, follow_symlinks=False)
    except FileNotFoundError:
        return True
    if (named.st_dev, named.st_ino) != opened_physical:
        return False
    try:
        os.unlink(name, dir_fd=created.root_guard)
    except OSError:
        return False
    return True


def _delete_exact_workspace_root(created: _CreatedWorkspace) -> bool:
    if created.windows_root_guard:
        return _delete_windows_handle(created.root_guard)
    try:
        named = os.stat(
            created.target.root.name,
            dir_fd=created.parent_guard,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return True
    if (named.st_dev, named.st_ino) != created.root_physical_identity:
        return False
    try:
        os.rmdir(created.target.root.name, dir_fd=created.parent_guard)
    except OSError:
        return False
    return True


def _rollback_workspace(created: _CreatedWorkspace) -> None:
    if created.closed:
        return
    all_files_deleted = True
    all_files_safe = True
    root_deleted = False
    try:
        for name in reversed(_WORKSPACE_NAMES):
            descriptor = created.descriptors.get(name)
            if descriptor is None:
                continue
            opened_physical: tuple[int, int] | None = None
            try:
                opened = os.fstat(descriptor)
                opened_physical = (opened.st_dev, opened.st_ino)
            except BaseException:
                pass
            try:
                invalidated = _invalidate_open(descriptor)
            except BaseException:
                invalidated = False
            if not invalidated:
                try:
                    invalidated = _emergency_poison(descriptor)
                except BaseException:
                    invalidated = False
            deleted = False
            try:
                if sys.platform == "win32":
                    deleted = _delete_open_windows(descriptor)
                elif opened_physical is not None:
                    deleted = _unlink_open_posix_workspace_file(
                        created,
                        name,
                        opened_physical,
                    )
            except BaseException:
                deleted = False
            all_files_deleted = all_files_deleted and deleted
            all_files_safe = all_files_safe and (invalidated or deleted)
            try:
                os.close(descriptor)
            except BaseException:
                all_files_deleted = False
        if all_files_deleted:
            try:
                root_deleted = _delete_exact_workspace_root(created)
            except BaseException:
                root_deleted = False
    finally:
        try:
            _close_guard(created.root_guard, windows=created.windows_root_guard)
        except BaseException:
            root_deleted = False
        try:
            _close_guard(created.parent_guard, windows=created.windows_parent_guard)
        except BaseException:
            root_deleted = False
        created.closed = True
    if not root_deleted or not all_files_deleted or not all_files_safe:
        raise TrustedLocalInstructionQuarantineRequired(
            "created workspace rollback failed closed; output requires quarantine"
        )


def _assert_created_workspace_matches(
    created: _CreatedWorkspace,
    snapshot: _WorkspaceSnapshot,
) -> None:
    if (snapshot.root_identity[0], snapshot.root_identity[1]) != created.root_physical_identity:
        raise TrustedLocalInstructionPreparationError(
            "created workspace root identity drifted"
        )
    observed = {
        item.path.name: (item.identity[0], item.identity[1]) for item in snapshot.files
    }
    if observed != created.file_physical_identities:
        raise TrustedLocalInstructionPreparationError(
            "created workspace file identities drifted"
        )


def _capture_created_workspace(
    paths: _InputPaths,
    created: _CreatedWorkspace,
    *,
    expected_context: _InstructionWorkspaceContextV23,
    expected_payloads: dict[str, bytes],
    expected_context_sha256: str,
) -> _WorkspaceSnapshot:
    """Verify all just-created bytes through the retained exact descriptors."""

    inputs = _capture_inputs(paths)
    root_before = _directory_identity(
        created.target.root,
        field="created instruction workspace",
    )
    names = _bounded_workspace_names(
        created.target.root,
        field="created instruction workspace",
    )
    if names != frozenset(_WORKSPACE_NAMES):
        raise TrustedLocalInstructionPreparationError(
            "created instruction workspace does not have the exact five files"
        )
    rebuilt_payloads, rebuilt_digest = _workspace_payloads(expected_context)
    if rebuilt_payloads != expected_payloads or rebuilt_digest != expected_context_sha256:
        raise TrustedLocalInstructionPreparationError(
            "workspace payload source drifted after creation"
        )
    files: list[_FileSeal] = []
    for name in _WORKSPACE_NAMES:
        physical = _read_open_workspace_file(
            created,
            name,
            expected_payloads[name],
        )
        descriptor = created.descriptors[name]
        info = os.fstat(descriptor)
        source = SafeLocalFile(
            path=created.target.root / name,
            data=expected_payloads[name],
            sha256=hashlib.sha256(expected_payloads[name]).hexdigest(),
            size_bytes=len(expected_payloads[name]),
            identity=_stat_identity(info),
        )
        if physical != (source.identity[0], source.identity[1]):
            raise TrustedLocalInstructionPreparationError(
                "created workspace exact descriptor identity drifted"
            )
        files.append(_file_seal(source))
    context_source = SafeLocalFile(
        path=created.target.root / _CONTEXT_JSON_NAME,
        data=expected_payloads[_CONTEXT_JSON_NAME],
        sha256=hashlib.sha256(expected_payloads[_CONTEXT_JSON_NAME]).hexdigest(),
        size_bytes=len(expected_payloads[_CONTEXT_JSON_NAME]),
        identity=next(
            item.identity for item in files if item.path.name == _CONTEXT_JSON_NAME
        ),
    )
    parsed_context = _parse_canonical_json(
        context_source,
        _InstructionWorkspaceContextV23,
        field="created workspace context",
    )
    if parsed_context != expected_context:
        raise TrustedLocalInstructionPreparationError(
            "created workspace context differs from the exact mechanical context"
        )
    if (
        parsed_context.request_id != inputs.request.request_id
        or parsed_context.request_sha256 != inputs.request_seal.sha256
        or parsed_context.qualifier_ref_sha256 != inputs.qualifier_ref.sha256
        or parsed_context.policy_id != inputs.request.policy_id
        or parsed_context.policy_version != inputs.request.policy_version
        or parsed_context.policy_document_sha256 != inputs.request.policy_document_sha256
    ):
        raise TrustedLocalInstructionPreparationError(
            "created workspace context does not bind the postwrite source capture"
        )
    root_after = _directory_identity(
        created.target.root,
        field="created instruction workspace",
    )
    if root_before != root_after:
        raise TrustedLocalInstructionPreparationError(
            "created instruction workspace root drifted"
        )
    all_files = (inputs.request_seal, inputs.qualifier_ref, *files)
    _assert_non_aliasing(all_files)
    reserved = _request_reserved_digests(inputs.request)
    if any(item.sha256 in reserved for item in files):
        raise TrustedLocalInstructionPreparationError(
            "created workspace aliases a reserved Request digest"
        )
    return _WorkspaceSnapshot(
        inputs=inputs,
        context=parsed_context,
        context_sha256=expected_context_sha256,
        root_identity=root_before,
        files=tuple(files),
    )


def _commit_workspace(
    created: _CreatedWorkspace,
    expected_payloads: dict[str, bytes],
) -> None:
    if created.closed or set(created.descriptors) != set(_WORKSPACE_NAMES):
        raise TrustedLocalInstructionPreparationError(
            "created workspace is not publishable"
        )
    close_started = False
    try:
        _revalidate_workspace_target(created.target, must_exist=True)
        root_identity = _directory_identity(
            created.target.root,
            field="created instruction workspace",
        )
        if (root_identity[0], root_identity[1]) != created.root_physical_identity:
            raise TrustedLocalInstructionPreparationError(
                "created workspace root drifted before commit"
            )
        names = _bounded_workspace_names(
            created.target.root,
            field="created workspace before commit",
        )
        if names != frozenset(_WORKSPACE_NAMES):
            raise TrustedLocalInstructionPreparationError(
                "created workspace member set drifted before commit"
            )
        for name in _WORKSPACE_NAMES:
            physical = _read_open_workspace_file(
                created,
                name,
                expected_payloads[name],
            )
            if physical != created.file_physical_identities[name]:
                raise TrustedLocalInstructionPreparationError(
                    "created workspace file identity drifted before commit"
                )
        final_root_identity = _directory_identity(
            created.target.root,
            field="created instruction workspace",
        )
        final_names = _bounded_workspace_names(
            created.target.root,
            field="created workspace final member set",
        )
        if (
            (final_root_identity[0], final_root_identity[1])
            != created.root_physical_identity
            or final_names != frozenset(_WORKSPACE_NAMES)
        ):
            raise TrustedLocalInstructionPreparationError(
                "created workspace final member set drifted before commit"
            )
        if not created.windows_root_guard:
            os.fsync(created.root_guard)
        close_started = True
        for descriptor in created.descriptors.values():
            os.close(descriptor)
        created.descriptors.clear()
        _close_guard(created.root_guard, windows=created.windows_root_guard)
        if not created.windows_parent_guard:
            os.fsync(created.parent_guard)
        _close_guard(created.parent_guard, windows=created.windows_parent_guard)
        created.closed = True
    except BaseException as exc:
        if not close_started:
            try:
                _rollback_workspace(created)
            except TrustedLocalInstructionPreparationError:
                raise
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            if isinstance(exc, TrustedLocalInstructionPreparationError):
                raise
            raise TrustedLocalInstructionPreparationError(
                "created workspace failed final exact verification"
            ) from exc
        # Closing any retained publication handle at an unknown boundary makes the exact
        # cleanup state unknowable; the caller must quarantine the explicit workspace path.
        for descriptor in created.descriptors.values():
            try:
                os.close(descriptor)
            except BaseException:
                pass
        try:
            _close_guard(created.root_guard, windows=created.windows_root_guard)
        except BaseException:
            pass
        try:
            _close_guard(created.parent_guard, windows=created.windows_parent_guard)
        except BaseException:
            pass
        created.closed = True
        raise TrustedLocalInstructionQuarantineRequired(
            "created workspace commit state requires quarantine"
        ) from exc


def _create_workspace(
    target: _WorkspaceTarget,
    payloads: dict[str, bytes],
) -> _CreatedWorkspace:
    _revalidate_workspace_target(target, must_exist=False)
    parent_guard, parent_is_windows = _acquire_workspace_parent_guard(target)
    root_guard: int | None = None
    created: _CreatedWorkspace | None = None
    root_physical: tuple[int, int] | None = None
    root_created = False
    try:
        _revalidate_workspace_target(target, must_exist=False)
        if sys.platform == "win32":
            os.mkdir(target.root, mode=0o700)
        else:
            os.mkdir(target.root.name, mode=0o700, dir_fd=parent_guard)
        root_created = True
        root_info = _directory_identity(target.root, field="created instruction workspace")
        root_physical = (root_info[0], root_info[1])
        root_guard, root_is_windows = _acquire_workspace_root_guard(
            target,
            parent_guard=parent_guard,
        )
        guarded_root_physical = _guarded_directory_physical_identity(
            root_guard,
            windows=root_is_windows,
            path=target.root,
        )
        if guarded_root_physical != root_physical:
            raise TrustedLocalInstructionQuarantineRequired(
                "created workspace root guard identity drifted"
            )
        created = _CreatedWorkspace(
            target=target,
            parent_guard=parent_guard,
            windows_parent_guard=parent_is_windows,
            root_guard=root_guard,
            windows_root_guard=root_is_windows,
            root_physical_identity=root_physical,
            descriptors={},
            file_physical_identities={},
        )
        _revalidate_workspace_target(target, must_exist=True)
        for name in _WORKSPACE_NAMES:
            descriptor = _open_workspace_file(created, name)
            created.descriptors[name] = descriptor
            raw = payloads[name]
            offset = 0
            while offset < len(raw):
                written = os.write(descriptor, raw[offset:])
                if written <= 0:
                    raise OSError("short workspace write")
                offset += written
            os.fsync(descriptor)
            created.file_physical_identities[name] = _read_open_workspace_file(
                created,
                name,
                raw,
            )
        _revalidate_workspace_target(target, must_exist=True)
        return created
    except FileExistsError as exc:
        if created is not None:
            _rollback_workspace(created)
        else:
            if root_guard is not None:
                try:
                    _close_guard(root_guard, windows=(sys.platform == "win32"))
                except BaseException:
                    pass
            try:
                _close_guard(parent_guard, windows=parent_is_windows)
            except BaseException:
                pass
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace must be one new directory"
        ) from exc
    except BaseException as exc:
        if created is not None:
            try:
                _rollback_workspace(created)
            except TrustedLocalInstructionPreparationError:
                raise
        else:
            # If the directory was created but its exact root handle could not be acquired,
            # never attempt pathname cleanup that could remove a replacement.
            if root_guard is not None:
                try:
                    _close_guard(root_guard, windows=(sys.platform == "win32"))
                except BaseException:
                    pass
            try:
                _close_guard(parent_guard, windows=parent_is_windows)
            except BaseException:
                pass
            if root_created:
                raise TrustedLocalInstructionQuarantineRequired(
                    "created workspace could not be retained for exact rollback"
                ) from exc
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        if isinstance(exc, TrustedLocalInstructionPreparationError):
            raise
        raise TrustedLocalInstructionPreparationError(
            "instruction workspace could not be created safely"
        ) from exc


def prepare_workspace(
    request_path: Path,
    qualifier_ref_path: Path,
    workspace_root: Path,
    *,
    observed_at: str,
) -> TrustedLocalInstructionWorkspace:
    """Create one exact static workspace after two complete source captures."""

    paths = _normalize_inputs(request_path, qualifier_ref_path)
    target = _validate_workspace_target(workspace_root, paths=paths)
    root = target.root
    before = _capture_inputs(paths)
    _assert_observed_request_time(before.request, observed_at)
    context = _build_context(before, prepared_at=observed_at)
    payloads, digest = _workspace_payloads(context)
    after = _capture_inputs(paths)
    _assert_input_unchanged(before, after)
    _assert_observed_request_time(after.request, observed_at)
    revalidated = _validate_workspace_target(root, paths=paths)
    if revalidated != target:
        raise TrustedLocalInstructionPreparationError(
            "workspace target drifted before publication"
        )
    created = _create_workspace(target, payloads)
    try:
        verified = _capture_created_workspace(
            paths,
            created,
            expected_context=context,
            expected_payloads=payloads,
            expected_context_sha256=digest,
        )
        _assert_created_workspace_matches(created, verified)
        _assert_input_unchanged(before, verified.inputs)
        if verified.context != context or verified.context_sha256 != digest:
            raise TrustedLocalInstructionPreparationError(
                "created instruction workspace failed exact verification"
            )
        final_inputs = _capture_inputs(paths)
        _assert_input_unchanged(before, final_inputs)
        _commit_workspace(created, payloads)
    except BaseException:
        if not created.closed:
            _rollback_workspace(created)
        raise
    return TrustedLocalInstructionWorkspace(
        root=root,
        index_path=root / "index.html",
        context_path=root / _CONTEXT_JSON_NAME,
        context_id=context.context_id,
        context_sha256=digest,
    )


def finalize_instruction(
    request_path: Path,
    qualifier_ref_path: Path,
    workspace_root: Path,
    draft_path: Path,
    output_path: Path,
    *,
    observed_at: str,
) -> CreativeSampleRealAssetQualificationDecisionInstructionV22:
    """Create one canonical retained Instruction from four explicit human fields."""

    paths = _normalize_inputs(request_path, qualifier_ref_path)
    root = _normalize_workspace(workspace_root, paths=paths)
    draft = _validate_draft_path(draft_path, paths=paths, root=root)
    target = _validate_output(
        output_path,
        paths=paths,
        root=root,
        draft=draft,
        must_exist=False,
    )
    before = _capture_finalize(paths, root, draft)
    _assert_observed_request_time(before.workspace.inputs.request, observed_at)
    _assert_draft_time(before, observed_at=observed_at)
    candidate = _build_instruction(before)
    after = _capture_finalize(paths, root, draft)
    _assert_finalize_unchanged(before, after)
    if _build_instruction(after) != candidate:
        raise TrustedLocalInstructionPreparationError(
            "Instruction rebuild drifted before publication"
        )
    _revalidate_output(target, must_exist=False)
    created = _create_new_instruction(target, candidate)
    try:
        final = _capture_finalize(paths, root, draft)
        _assert_finalize_unchanged(before, final)
        if _build_instruction(final) != candidate:
            raise TrustedLocalInstructionPreparationError(
                "Instruction rebuild drifted after publication"
            )
        if created.seal is None:
            raise TrustedLocalInstructionPreparationError(
                "created Instruction has no exact byte seal"
            )
        source_files = (
            final.workspace.inputs.request_seal,
            final.workspace.inputs.qualifier_ref,
            *final.workspace.files,
            final.draft_seal,
        )
        if created.seal.sha256 in {
            *{item.sha256 for item in source_files},
            *_request_reserved_digests(final.workspace.inputs.request),
        }:
            raise TrustedLocalInstructionPreparationError(
                "created Instruction aliases an immutable source digest"
            )
        _commit_created(created, candidate)
    except BaseException:
        if not created.closed:
            _rollback_created(created)
        raise
    return candidate


def verify_instruction(
    request_path: Path,
    qualifier_ref_path: Path,
    workspace_root: Path,
    draft_path: Path,
    instruction_path: Path,
) -> CreativeSampleRealAssetQualificationDecisionInstructionV22:
    """Historically rebuild one Instruction without a wall clock or any write."""

    paths = _normalize_inputs(request_path, qualifier_ref_path)
    root = _normalize_workspace(workspace_root, paths=paths)
    draft = _validate_draft_path(draft_path, paths=paths, root=root)
    instruction_target = _validate_output(
        instruction_path,
        paths=paths,
        root=root,
        draft=draft,
        must_exist=True,
    )
    _revalidate_output(instruction_target, must_exist=True)
    before = _capture_finalize(
        paths,
        root,
        draft,
        instruction_path=instruction_target.path,
    )
    _assert_draft_time(before, observed_at=None)
    rebuilt = _build_instruction(before)
    if before.instruction != rebuilt:
        raise TrustedLocalInstructionPreparationError(
            "retained Instruction does not equal the historical rebuild"
        )
    _revalidate_output(instruction_target, must_exist=True)
    after = _capture_finalize(
        paths,
        root,
        draft,
        instruction_path=instruction_target.path,
    )
    _assert_finalize_unchanged(before, after)
    _revalidate_output(instruction_target, must_exist=True)
    if after.instruction != rebuilt:
        raise TrustedLocalInstructionPreparationError(
            "retained Instruction drifted during historical verification"
        )
    return rebuilt


def _safe_summary(status: str) -> str:
    payload: dict[str, object] = {
        "status": status,
        "rights_manifest_created": False,
        "rights_qualification_performed": False,
        "eligible_for_separate_manifest_design_review": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = _FailClosedArgumentParser(
        description="Prepare one trusted local zero-authority qualification Instruction"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-workspace")
    prepare.add_argument("--request", required=True, type=Path)
    prepare.add_argument("--qualifier-ref", required=True, type=Path)
    prepare.add_argument("--workspace", required=True, type=Path)
    prepare.add_argument("--observed-at", required=True)
    finalize = commands.add_parser("finalize-instruction")
    finalize.add_argument("--request", required=True, type=Path)
    finalize.add_argument("--qualifier-ref", required=True, type=Path)
    finalize.add_argument("--workspace", required=True, type=Path)
    finalize.add_argument("--draft", required=True, type=Path)
    finalize.add_argument("--output", required=True, type=Path)
    finalize.add_argument("--observed-at", required=True)
    verify = commands.add_parser("verify-instruction")
    verify.add_argument("--request", required=True, type=Path)
    verify.add_argument("--qualifier-ref", required=True, type=Path)
    verify.add_argument("--workspace", required=True, type=Path)
    verify.add_argument("--draft", required=True, type=Path)
    verify.add_argument("--instruction", required=True, type=Path)
    try:
        args = parser.parse_args(argv)
    except _CliArgumentError:
        print(_safe_summary("FAILED_CLOSED"), file=sys.stderr)
        return 2
    try:
        if args.command == "prepare-workspace":
            result = prepare_workspace(
                args.request,
                args.qualifier_ref,
                args.workspace,
                observed_at=args.observed_at,
            )
            del result
            print(_safe_summary("AWAITING_EXPLICIT_QUALIFIER_INPUT"))
        elif args.command == "finalize-instruction":
            instruction = finalize_instruction(
                args.request,
                args.qualifier_ref,
                args.workspace,
                args.draft,
                args.output,
                observed_at=args.observed_at,
            )
            del instruction
            print(_safe_summary("DECISION_INSTRUCTION_RECORDED"))
        elif args.command == "verify-instruction":
            instruction = verify_instruction(
                args.request,
                args.qualifier_ref,
                args.workspace,
                args.draft,
                args.instruction,
            )
            del instruction
            print(_safe_summary("DECISION_INSTRUCTION_RECORDED"))
        else:  # pragma: no cover - argparse owns the finite command set.
            raise TrustedLocalInstructionPreparationError("unsupported operation")
    except TrustedLocalInstructionQuarantineRequired:
        print(
            _safe_summary("ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"),
            file=sys.stderr,
        )
        return 3
    except BaseException:
        print(_safe_summary("FAILED_CLOSED"), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "TrustedLocalInstructionPreparationError",
    "TrustedLocalInstructionQuarantineRequired",
    "TrustedLocalInstructionWorkspace",
    "finalize_instruction",
    "main",
    "prepare_workspace",
    "verify_instruction",
]
