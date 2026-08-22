"""Prepare one inert v2.7 Use Scope Review authoring input safely.

The v2.9 boundary consumes one explicit repository-external draft and creates at most one
canonical, owner-only Maker or Checker authoring input.  It never reads a business closure,
discovers a path, reads a clock, invokes another finalizer, contacts a Provider, or grants any
execution authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, Never, cast

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

import sdc.real_asset_rights_manifest_finalizer_v25 as _manifest_boundary
import sdc.real_asset_use_plan_finalizer_v27 as _plan_boundary
from sdc.real_asset_media import SafeLocalFile
from sdc.real_asset_rights_manifest_finalizer_v25 import (
    TrustedLocalRightsManifestFinalizationError,
)
from sdc.real_asset_use_plan_finalizer_v27 import (
    TrustedLocalUsePlanFinalizationError,
    TrustedLocalUsePlanQuarantineRequired,
)

_DRAFT_MAX_BYTES = 65_536
_AUTHORING_MAX_BYTES = 65_536
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DOCUMENT_TYPE = "sdc.trusted-local-use-scope-review-authoring-draft"
_DRAFT_FORMAT_VERSION = "1.0.0"
_PREPARER_VERSION = "v2.9"
_TARGET_FINALIZER_MODULE = "sdc.real_asset_use_scope_review_finalizer_v27"
_TARGET_FINALIZER_VERSION = "v2.7"
_USAGE_RESTRICTION = "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
_PARENT_SEAL_DOMAIN = b"sdc:v29:output-parent-seal\0"
_INSPECTED_STATUS = "AUTHORING_CANDIDATE_INSPECTED_FOR_SEPARATE_CREATE_APPROVAL_ONLY"
_FINALIZED_STATUS = "AUTHORING_INPUT_CREATED_FOR_SEPARATE_MANUAL_V27_PREFLIGHT_ONLY"

AuthoringRole = Literal["MAKER", "CHECKER"]
GateName = Literal[
    "COPYRIGHT_USE_SCOPE",
    "LIKENESS_USE_SCOPE",
    "PRIVACY_USE_SCOPE",
    "TERRITORY_USE_SCOPE",
    "CONTENT_ROLE_USE_SCOPE",
    "OFFLINE_ONLY_RESTRICTIONS",
]
Disposition = Literal[
    "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY",
    "NEEDS_REVISION",
    "REJECTED",
]

_GATE_ORDER: tuple[GateName, ...] = (
    "COPYRIGHT_USE_SCOPE",
    "LIKENESS_USE_SCOPE",
    "PRIVACY_USE_SCOPE",
    "TERRITORY_USE_SCOPE",
    "CONTENT_ROLE_USE_SCOPE",
    "OFFLINE_ONLY_RESTRICTIONS",
)
_DISPOSITIONS = frozenset(
    {
        "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY",
        "NEEDS_REVISION",
        "REJECTED",
    }
)
_DRAFT_SUFFIXES: dict[AuthoringRole, str] = {
    "MAKER": ".maker-authoring-draft-v29.json",
    "CHECKER": ".checker-authoring-draft-v29.json",
}
_OUTPUT_PREFIXES: dict[AuthoringRole, str] = {
    "MAKER": "maker_use_scope_review_authoring_input_v27_",
    "CHECKER": "checker_use_scope_review_authoring_input_v27_",
}


class TrustedLocalReviewAuthoringPreparationError(RuntimeError):
    """The trusted-local v2.9 authoring preparation boundary failed closed."""


class TrustedLocalReviewAuthoringQuarantineRequired(TrustedLocalReviewAuthoringPreparationError):
    """Rollback could not prove invalidation of the exact newly created input."""


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
class AuthoringInspectionV29:
    """Comparison-only result for one separately approved future create."""

    status: Literal["AUTHORING_CANDIDATE_INSPECTED_FOR_SEPARATE_CREATE_APPROVAL_ONLY"]
    authoring_role: AuthoringRole
    draft_sha256: str
    candidate_authoring_sha256: str
    candidate_authoring_size_bytes: int
    required_output_filename: str
    output_parent_seal_sha256: str


@dataclass(frozen=True, slots=True)
class PreparedAuthoringInputV29:
    """Bounded result for one inert, non-authoritative created authoring input."""

    status: Literal["AUTHORING_INPUT_CREATED_FOR_SEPARATE_MANUAL_V27_PREFLIGHT_ONLY"]
    authoring_role: AuthoringRole
    draft_sha256: str
    authoring_input_sha256: str
    authoring_input_size_bytes: int


class _DraftEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    authoring_role: AuthoringRole
    document_type: Literal["sdc.trusted-local-use-scope-review-authoring-draft"]
    draft_format_version: Literal["1.0.0"]
    payload: dict[str, object]
    target_finalizer_module: Literal["sdc.real_asset_use_scope_review_finalizer_v27"]
    target_finalizer_version: Literal["v2.7"]


def _portable_human_text(value: object, *, maximum: int) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > maximum
        or value != value.strip()
        or unicodedata.normalize("NFC", value) != value
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        raise ValueError("human text violates the exact v2.7 boundary")
    return value


class _MakerAuthoring(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    request_basis: str

    @field_validator("request_basis")
    @classmethod
    def _validate_request_basis(cls, value: str) -> str:
        return _portable_human_text(value, maximum=2_000)


class _GateAuthoring(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    approved: bool
    gate: GateName
    note: str | None

    @model_validator(mode="after")
    def _validate_note(self) -> _GateAuthoring:
        if self.approved:
            if self.note is not None:
                raise ValueError("approved gate requires a null note")
        else:
            _portable_human_text(self.note, maximum=1_000)
        return self


class _CheckerAuthoring(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    checker_basis: str
    disposition: Disposition
    gate_results: tuple[_GateAuthoring, ...]

    @field_validator("checker_basis")
    @classmethod
    def _validate_checker_basis(cls, value: str) -> str:
        return _portable_human_text(value, maximum=2_000)

    @model_validator(mode="after")
    def _validate_policy(self) -> _CheckerAuthoring:
        if tuple(item.gate for item in self.gate_results) != _GATE_ORDER:
            raise ValueError("Checker gates do not use the exact v2.7 order")
        approvals = tuple(item.approved for item in self.gate_results)
        positive = self.disposition == "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY"
        if positive != all(approvals):
            raise ValueError("Checker disposition and gates are inconsistent")
        return self


_AuthoringModel = _MakerAuthoring | _CheckerAuthoring


@dataclass(frozen=True, slots=True)
class _DraftCapture:
    source: SafeLocalFile
    stat_signature: tuple[int, int, int, int, int, int, int, int, int, int]
    owner_identity: str


@dataclass(frozen=True, slots=True)
class _ParentCapture:
    path: Path
    seal_sha256: str
    physical_identity: tuple[int, int]
    stat_signature: tuple[int, int, int, int, int]
    owner_identity: str


@dataclass(frozen=True, slots=True)
class _CandidateSnapshot:
    role: AuthoringRole
    draft: _DraftCapture
    output_parent: _ParentCapture
    authoring: _AuthoringModel
    authoring_bytes: bytes
    authoring_sha256: str
    required_output_filename: str


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _reject_json_constant(value: str) -> Never:
    del value
    raise TrustedLocalReviewAuthoringPreparationError("draft contains a non-finite value")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise TrustedLocalReviewAuthoringPreparationError("draft contains a duplicate key")
        value[key] = item
    return value


def _strict_json_object(raw: bytes, *, field: str) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise TrustedLocalReviewAuthoringPreparationError(f"{field} must not contain a BOM")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except TrustedLocalReviewAuthoringPreparationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise TrustedLocalReviewAuthoringPreparationError(
            f"{field} must be strict UTF-8 JSON"
        ) from exc
    if type(value) is not dict:
        raise TrustedLocalReviewAuthoringPreparationError(f"{field} must be one JSON object")
    return cast(dict[str, object], value)


def _build_authoring(payload: object, *, role: AuthoringRole) -> _AuthoringModel:
    if type(payload) is not dict:
        raise TrustedLocalReviewAuthoringPreparationError("draft payload must be one object")
    admitted = cast(dict[str, object], payload)
    try:
        if role == "MAKER":
            if set(admitted) != {"request_basis"}:
                raise TrustedLocalReviewAuthoringPreparationError(
                    "Maker payload has missing or unknown members"
                )
            return _MakerAuthoring.model_validate(admitted, strict=True)
        if set(admitted) != {"checker_basis", "disposition", "gate_results"}:
            raise TrustedLocalReviewAuthoringPreparationError(
                "Checker payload has missing or unknown members"
            )
        disposition = admitted["disposition"]
        if type(disposition) is not str or disposition not in _DISPOSITIONS:
            raise TrustedLocalReviewAuthoringPreparationError(
                "Checker disposition is not one exact policy value"
            )
        raw_gates = admitted["gate_results"]
        if type(raw_gates) is not list or len(raw_gates) != len(_GATE_ORDER):
            raise TrustedLocalReviewAuthoringPreparationError(
                "Checker payload requires six ordered gates"
            )
        gates: list[_GateAuthoring] = []
        for expected_gate, raw_gate in zip(_GATE_ORDER, raw_gates, strict=True):
            if type(raw_gate) is not dict or set(raw_gate) != {"approved", "gate", "note"}:
                raise TrustedLocalReviewAuthoringPreparationError(
                    "Checker gate has missing or unknown members"
                )
            gate = cast(dict[str, object], raw_gate)
            if gate["gate"] != expected_gate or type(gate["approved"]) is not bool:
                raise TrustedLocalReviewAuthoringPreparationError(
                    "Checker gates use the wrong order or boolean type"
                )
            gates.append(_GateAuthoring.model_validate(gate, strict=True))
        return _CheckerAuthoring.model_validate(
            {
                "checker_basis": admitted["checker_basis"],
                "disposition": disposition,
                "gate_results": tuple(gates),
            },
            strict=True,
        )
    except TrustedLocalReviewAuthoringPreparationError:
        raise
    except (ValidationError, ValueError, TypeError) as exc:
        raise TrustedLocalReviewAuthoringPreparationError(
            f"{role} payload violates the exact v2.7 authoring policy"
        ) from exc


def _canonical_authoring(value: _AuthoringModel) -> bytes:
    try:
        raw = (
            json.dumps(
                value.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (UnicodeEncodeError, ValueError, TypeError) as exc:
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring candidate cannot be serialized canonically"
        ) from exc
    if not raw or len(raw) > _AUTHORING_MAX_BYTES:
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring candidate exceeds its fixed bound"
        )
    return raw


def _parse_draft(raw: bytes, *, role: AuthoringRole) -> _AuthoringModel:
    value = _strict_json_object(raw, field="authoring draft")
    if set(value) != {
        "authoring_role",
        "document_type",
        "draft_format_version",
        "payload",
        "target_finalizer_module",
        "target_finalizer_version",
    }:
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring draft has missing or unknown members"
        )
    try:
        envelope = _DraftEnvelope.model_validate(value, strict=True)
    except ValidationError as exc:
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring draft has the wrong fixed envelope"
        ) from exc
    if envelope.authoring_role != role:
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring command and draft role do not match"
        )
    return _build_authoring(envelope.payload, role=role)


def _parse_canonical_authoring(raw: bytes, *, role: AuthoringRole) -> _AuthoringModel:
    value = _strict_json_object(raw, field="created authoring input")
    authoring = _build_authoring(value, role=role)
    if raw != _canonical_authoring(authoring):
        raise TrustedLocalReviewAuthoringPreparationError(
            "created authoring input is not exact canonical JSON"
        )
    return authoring


def _safe_absolute(path: Path, *, must_exist: bool, field: str) -> Path:
    if not isinstance(path, Path):
        raise TrustedLocalReviewAuthoringPreparationError(f"{field} must be one explicit Path")
    try:
        return _manifest_boundary._safe_absolute(path, must_exist=must_exist, field=field)
    except TrustedLocalRightsManifestFinalizationError as exc:
        raise TrustedLocalReviewAuthoringPreparationError(
            f"{field} failed safe local path admission"
        ) from exc


if sys.platform == "win32":
    import ctypes as _windows_ctypes
    from ctypes import wintypes as _windows_wintypes

    _OWNER_SECURITY_INFORMATION = 0x00000001
    _SE_FILE_OBJECT = 1

    def _windows_named_owner_sid(path: Path) -> str:
        advapi32 = _windows_ctypes.WinDLL("advapi32", use_last_error=True)
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        get_named_security_info = advapi32.GetNamedSecurityInfoW
        get_named_security_info.argtypes = (
            _windows_wintypes.LPWSTR,
            _windows_wintypes.DWORD,
            _windows_wintypes.DWORD,
            _windows_ctypes.POINTER(_windows_wintypes.LPVOID),
            _windows_ctypes.POINTER(_windows_wintypes.LPVOID),
            _windows_ctypes.POINTER(_windows_wintypes.LPVOID),
            _windows_ctypes.POINTER(_windows_wintypes.LPVOID),
            _windows_ctypes.POINTER(_windows_wintypes.LPVOID),
        )
        get_named_security_info.restype = _windows_wintypes.DWORD
        owner = _windows_wintypes.LPVOID()
        descriptor = _windows_wintypes.LPVOID()
        result = int(
            get_named_security_info(
                str(path),
                _SE_FILE_OBJECT,
                _OWNER_SECURITY_INFORMATION,
                _windows_ctypes.byref(owner),
                None,
                None,
                None,
                _windows_ctypes.byref(descriptor),
            )
        )
        if result != 0 or not owner or not descriptor:
            if descriptor:
                kernel32.LocalFree(descriptor)
            raise TrustedLocalReviewAuthoringPreparationError("path owner could not be inspected")
        sid_text = _windows_wintypes.LPWSTR()
        convert_sid = advapi32.ConvertSidToStringSidW
        convert_sid.argtypes = (
            _windows_wintypes.LPVOID,
            _windows_ctypes.POINTER(_windows_wintypes.LPWSTR),
        )
        convert_sid.restype = _windows_wintypes.BOOL
        try:
            if not convert_sid(owner, _windows_ctypes.byref(sid_text)) or not sid_text:
                raise TrustedLocalReviewAuthoringPreparationError(
                    "path owner SID could not be inspected"
                )
            return cast(str, sid_text.value)
        finally:
            if sid_text:
                kernel32.LocalFree(sid_text)
            kernel32.LocalFree(descriptor)

    def _effective_owner_identity(path: Path) -> str:
        observed = _windows_named_owner_sid(path)
        try:
            expected = _plan_boundary._windows_effective_user_sid_string()
        except BaseException as exc:
            raise TrustedLocalReviewAuthoringPreparationError(
                "effective Windows owner could not be established"
            ) from exc
        if observed != expected:
            raise TrustedLocalReviewAuthoringPreparationError(
                "path is not owned by the effective Windows user"
            )
        return observed

else:

    def _effective_owner_identity(path: Path) -> str:
        try:
            info = path.lstat()
            effective_uid = os.geteuid()
        except (AttributeError, OSError) as exc:
            raise TrustedLocalReviewAuthoringPreparationError(
                "effective POSIX owner could not be established"
            ) from exc
        if info.st_uid != effective_uid:
            raise TrustedLocalReviewAuthoringPreparationError(
                "path is not owned by the effective POSIX user"
            )
        return str(effective_uid)


def _draft_stat_signature(path: Path) -> tuple[int, int, int, int, int, int, int, int, int, int]:
    try:
        value = path.lstat()
    except OSError as exc:
        raise TrustedLocalReviewAuthoringPreparationError(
            "draft metadata could not be recaptured"
        ) from exc
    attributes = int(getattr(value, "st_file_attributes", 0))
    signature = (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_size),
        int(value.st_mtime_ns),
        int(getattr(value, "st_ctime_ns", 0)),
        int(value.st_mode),
        int(value.st_nlink),
        int(getattr(value, "st_uid", 0)),
        int(getattr(value, "st_gid", 0)),
        attributes,
    )
    if (
        not stat.S_ISREG(value.st_mode)
        or stat.S_ISLNK(value.st_mode)
        or bool(attributes & 0x400)
        or value.st_nlink != 1
    ):
        raise TrustedLocalReviewAuthoringPreparationError(
            "draft must be one ordinary single-link file"
        )
    return signature


def _capture_draft(path: Path, *, role: AuthoringRole) -> _DraftCapture:
    if not isinstance(path, Path):
        raise TrustedLocalReviewAuthoringPreparationError(
            f"{role} authoring draft must be one explicit Path"
        )
    expected_suffix = _DRAFT_SUFFIXES[role]
    if not path.name.casefold().endswith(expected_suffix):
        raise TrustedLocalReviewAuthoringPreparationError(
            "draft filename does not bind the selected authoring role and version"
        )
    absolute = _safe_absolute(path, must_exist=True, field=f"{role} authoring draft")
    signature_before = _draft_stat_signature(absolute)
    owner_before = _effective_owner_identity(absolute)
    try:
        source = _manifest_boundary._read_safe(
            absolute,
            max_bytes=_DRAFT_MAX_BYTES,
            field=f"{role} authoring draft",
        )
    except TrustedLocalRightsManifestFinalizationError as exc:
        raise TrustedLocalReviewAuthoringPreparationError(
            "draft could not be captured as one stable bounded file"
        ) from exc
    signature_after = _draft_stat_signature(absolute)
    owner_after = _effective_owner_identity(absolute)
    if (
        signature_before != signature_after
        or owner_before != owner_after
        or source.path != absolute
        or source.identity != signature_after[:4]
    ):
        raise TrustedLocalReviewAuthoringPreparationError(
            "draft metadata or owner changed during capture"
        )
    return _DraftCapture(
        source=source,
        stat_signature=signature_after,
        owner_identity=owner_after,
    )


def _normalized_parent_text(path: Path) -> str:
    value = str(path)
    if sys.platform == "win32":
        value = value.replace("/", "\\")
        anchor = str(Path(path.anchor)) if path.anchor else ""
        while value.endswith("\\") and value != anchor:
            value = value[:-1]
    elif value != path.anchor:
        value = value.rstrip("/")
    return value


def _parent_seal_payload(path: Path, value: os.stat_result) -> dict[str, object]:
    return {
        "normalized_absolute_path": _normalized_parent_text(path),
        "physical_identity": [int(value.st_dev), int(value.st_ino)],
        "platform": "WINDOWS" if sys.platform == "win32" else "POSIX",
        "st_file_attributes": int(getattr(value, "st_file_attributes", 0)),
        "st_gid": int(getattr(value, "st_gid", 0)),
        "st_mode": int(value.st_mode),
        "st_uid": int(getattr(value, "st_uid", 0)),
    }


def _capture_parent(path: Path) -> _ParentCapture:
    if not isinstance(path, Path):
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring output parent must be one explicit Path"
        )
    submitted_path = path
    absolute = _safe_absolute(path, must_exist=True, field="authoring output parent")
    try:
        identity = _manifest_boundary._directory_identity(
            absolute,
            field="authoring output parent",
        )
        value_before = absolute.lstat()
    except (OSError, TrustedLocalRightsManifestFinalizationError) as exc:
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring output parent could not be captured"
        ) from exc
    attributes_before = int(getattr(value_before, "st_file_attributes", 0))
    if (
        (int(value_before.st_dev), int(value_before.st_ino)) != (int(identity[0]), int(identity[1]))
        or not stat.S_ISDIR(value_before.st_mode)
        or stat.S_ISLNK(value_before.st_mode)
        or bool(attributes_before & 0x400)
    ):
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring output parent is not one ordinary directory"
        )
    owner = _effective_owner_identity(absolute)
    try:
        value = absolute.lstat()
    except OSError as exc:
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring output parent could not be recaptured"
        ) from exc
    attributes = int(getattr(value, "st_file_attributes", 0))
    before_signature = (
        int(value_before.st_dev),
        int(value_before.st_ino),
        int(value_before.st_mode),
        int(getattr(value_before, "st_uid", 0)),
        int(getattr(value_before, "st_gid", 0)),
        attributes_before,
    )
    after_signature = (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_mode),
        int(getattr(value, "st_uid", 0)),
        int(getattr(value, "st_gid", 0)),
        attributes,
    )
    if before_signature != after_signature or after_signature[:2] != (
        int(identity[0]),
        int(identity[1]),
    ):
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring output parent changed during capture"
        )
    payload = json.dumps(
        _parent_seal_payload(submitted_path, value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    seal = _sha256(_PARENT_SEAL_DOMAIN + payload)
    return _ParentCapture(
        path=absolute,
        seal_sha256=seal,
        physical_identity=(int(identity[0]), int(identity[1])),
        stat_signature=(
            int(value.st_mode),
            int(getattr(value, "st_uid", 0)),
            int(getattr(value, "st_gid", 0)),
            attributes,
            int(value.st_ino),
        ),
        owner_identity=owner,
    )


def _assert_separate_areas(draft: _DraftCapture, parent: _ParentCapture) -> None:
    try:
        _manifest_boundary._assert_separate_trust_parent(
            parent.path,
            (draft.source.path.parent,),
            field="authoring output parent",
        )
    except TrustedLocalRightsManifestFinalizationError as exc:
        raise TrustedLocalReviewAuthoringPreparationError(
            "draft and output must use separate non-intersecting trust areas"
        ) from exc


def _required_output_filename(role: AuthoringRole, authoring_sha256: str) -> str:
    return f"{_OUTPUT_PREFIXES[role]}{authoring_sha256[:20]}.json"


def _capture_candidate(
    role: AuthoringRole,
    draft_path: Path,
    output_parent: Path,
) -> _CandidateSnapshot:
    draft = _capture_draft(draft_path, role=role)
    parent = _capture_parent(output_parent)
    _assert_separate_areas(draft, parent)
    authoring = _parse_draft(draft.source.data, role=role)
    raw = _canonical_authoring(authoring)
    digest = _sha256(raw)
    return _CandidateSnapshot(
        role=role,
        draft=draft,
        output_parent=parent,
        authoring=authoring,
        authoring_bytes=raw,
        authoring_sha256=digest,
        required_output_filename=_required_output_filename(role, digest),
    )


def _assert_candidate_unchanged(
    before: _CandidateSnapshot,
    after: _CandidateSnapshot,
) -> None:
    if before != after:
        raise TrustedLocalReviewAuthoringPreparationError(
            "draft candidate or output parent drifted during the operation"
        )


def _assert_required_output_absent(snapshot: _CandidateSnapshot) -> None:
    target = snapshot.output_parent.path / snapshot.required_output_filename
    if os.path.lexists(target):
        raise TrustedLocalReviewAuthoringPreparationError(
            "the digest-bound authoring output must remain absent"
        )
    absolute = _safe_absolute(target, must_exist=False, field="authoring output candidate")
    if (
        absolute != target
        or absolute.parent != snapshot.output_parent.path
        or os.path.lexists(target)
    ):
        raise TrustedLocalReviewAuthoringPreparationError(
            "the digest-bound authoring output must remain absent"
        )


def _validated_expected_sha256(value: str, *, field: str) -> str:
    if type(value) is not str or _LOWER_SHA256.fullmatch(value) is None:
        raise TrustedLocalReviewAuthoringPreparationError(f"{field} must be one lowercase SHA-256")
    return value


def _inspect_authoring(
    role: AuthoringRole,
    draft_path: Path,
    output_parent: Path,
) -> AuthoringInspectionV29:
    before = _capture_candidate(role, draft_path, output_parent)
    _assert_required_output_absent(before)
    after = _capture_candidate(role, draft_path, output_parent)
    _assert_required_output_absent(after)
    _assert_candidate_unchanged(before, after)
    return AuthoringInspectionV29(
        status=cast(
            Literal["AUTHORING_CANDIDATE_INSPECTED_FOR_SEPARATE_CREATE_APPROVAL_ONLY"],
            _INSPECTED_STATUS,
        ),
        authoring_role=role,
        draft_sha256=before.draft.source.sha256,
        candidate_authoring_sha256=before.authoring_sha256,
        candidate_authoring_size_bytes=len(before.authoring_bytes),
        required_output_filename=before.required_output_filename,
        output_parent_seal_sha256=before.output_parent.seal_sha256,
    )


def inspect_maker_authoring(
    draft_path: Path,
    output_parent: Path,
) -> AuthoringInspectionV29:
    """Inspect one explicit Maker draft without writing a file."""

    return _inspect_authoring("MAKER", draft_path, output_parent)


def inspect_checker_authoring(
    draft_path: Path,
    output_parent: Path,
) -> AuthoringInspectionV29:
    """Inspect one explicit Checker draft without writing a file."""

    return _inspect_authoring("CHECKER", draft_path, output_parent)


def _validate_output_target(
    output_path: Path,
    *,
    snapshot: _CandidateSnapshot,
) -> Any:
    if output_path.name != snapshot.required_output_filename:
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring output filename does not match the approved role, version and digest"
        )
    absolute = _safe_absolute(output_path, must_exist=False, field="authoring output")
    if absolute.parent != snapshot.output_parent.path or os.path.lexists(absolute):
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring output must be one absent file in the approved parent"
        )
    try:
        if _manifest_boundary._paths_overlap(absolute, snapshot.draft.source.path):
            raise TrustedLocalReviewAuthoringPreparationError(
                "authoring output overlaps its draft source"
            )
    except TrustedLocalReviewAuthoringPreparationError:
        raise
    return _plan_boundary._OutputTarget(
        path=absolute,
        parent=absolute.parent,
        parent_physical_identity=snapshot.output_parent.physical_identity,
    )


def _translate_plan_error(exc: BaseException) -> Never:
    if isinstance(exc, TrustedLocalUsePlanQuarantineRequired):
        raise TrustedLocalReviewAuthoringQuarantineRequired(
            "authoring output rollback requires quarantine"
        ) from exc
    if isinstance(exc, TrustedLocalUsePlanFinalizationError):
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring output failed the protected create-new boundary"
        ) from exc
    raise exc


def _finalize_authoring(
    role: AuthoringRole,
    draft_path: Path,
    output_path: Path,
    *,
    expected_draft_sha256: str,
    expected_authoring_sha256: str,
    expected_output_parent_seal_sha256: str,
) -> PreparedAuthoringInputV29:
    if not isinstance(draft_path, Path) or not isinstance(output_path, Path):
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring draft and output must be explicit Path values"
        )
    expected_draft_sha256 = _validated_expected_sha256(
        expected_draft_sha256,
        field="expected draft SHA-256",
    )
    expected_authoring_sha256 = _validated_expected_sha256(
        expected_authoring_sha256,
        field="expected authoring SHA-256",
    )
    expected_output_parent_seal_sha256 = _validated_expected_sha256(
        expected_output_parent_seal_sha256,
        field="expected output parent seal SHA-256",
    )
    before = _capture_candidate(role, draft_path, output_path.parent)
    _assert_required_output_absent(before)
    if (
        before.draft.source.sha256 != expected_draft_sha256
        or before.authoring_sha256 != expected_authoring_sha256
        or before.output_parent.seal_sha256 != expected_output_parent_seal_sha256
    ):
        raise TrustedLocalReviewAuthoringPreparationError(
            "authoring candidate does not match the separately approved comparison guards"
        )
    target = _validate_output_target(output_path, snapshot=before)
    immediately_before = _capture_candidate(role, draft_path, output_path.parent)
    _assert_required_output_absent(immediately_before)
    _assert_candidate_unchanged(before, immediately_before)
    created: Any | None = None

    def parser(raw: bytes) -> _AuthoringModel:
        return _parse_canonical_authoring(raw, role=role)

    try:
        created = _plan_boundary._create_new_artifact(
            target,
            before.authoring,
            parser=parser,
            maximum_bytes=_AUTHORING_MAX_BYTES,
            field=f"{role} authoring input",
        )
        after = _capture_candidate(role, draft_path, output_path.parent)
        _assert_candidate_unchanged(before, after)
        _plan_boundary._commit_created_artifact(
            created,
            before.authoring,
            parser=parser,
            maximum_bytes=_AUTHORING_MAX_BYTES,
            field=f"{role} authoring input",
        )
    except BaseException as exc:
        try:
            if created is not None and not bool(created.closed):
                _plan_boundary._rollback_created_artifact(created)
        except BaseException as rollback_exc:
            raise TrustedLocalReviewAuthoringQuarantineRequired(
                "authoring output rollback could not be confirmed"
            ) from rollback_exc
        _translate_plan_error(exc)
    return PreparedAuthoringInputV29(
        status=cast(
            Literal["AUTHORING_INPUT_CREATED_FOR_SEPARATE_MANUAL_V27_PREFLIGHT_ONLY"],
            _FINALIZED_STATUS,
        ),
        authoring_role=role,
        draft_sha256=before.draft.source.sha256,
        authoring_input_sha256=before.authoring_sha256,
        authoring_input_size_bytes=len(before.authoring_bytes),
    )


def finalize_maker_authoring(
    draft_path: Path,
    output_path: Path,
    *,
    expected_draft_sha256: str,
    expected_authoring_sha256: str,
    expected_output_parent_seal_sha256: str,
) -> PreparedAuthoringInputV29:
    """Create one protected Maker authoring input after exact guard comparison."""

    return _finalize_authoring(
        "MAKER",
        draft_path,
        output_path,
        expected_draft_sha256=expected_draft_sha256,
        expected_authoring_sha256=expected_authoring_sha256,
        expected_output_parent_seal_sha256=expected_output_parent_seal_sha256,
    )


def finalize_checker_authoring(
    draft_path: Path,
    output_path: Path,
    *,
    expected_draft_sha256: str,
    expected_authoring_sha256: str,
    expected_output_parent_seal_sha256: str,
) -> PreparedAuthoringInputV29:
    """Create one protected Checker authoring input after exact guard comparison."""

    return _finalize_authoring(
        "CHECKER",
        draft_path,
        output_path,
        expected_draft_sha256=expected_draft_sha256,
        expected_authoring_sha256=expected_authoring_sha256,
        expected_output_parent_seal_sha256=expected_output_parent_seal_sha256,
    )


def _expected_sha256_argument(value: str) -> str:
    if _LOWER_SHA256.fullmatch(value) is None:
        raise argparse.ArgumentTypeError
    return value


def _add_inspect_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--draft", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--output-parent", required=True, type=Path, action=_StoreOnce)


def _add_finalize_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--draft", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--output", required=True, type=Path, action=_StoreOnce)
    parser.add_argument(
        "--expected-draft-sha256",
        required=True,
        type=_expected_sha256_argument,
        action=_StoreOnce,
    )
    parser.add_argument(
        "--expected-authoring-sha256",
        required=True,
        type=_expected_sha256_argument,
        action=_StoreOnce,
    )
    parser.add_argument(
        "--expected-output-parent-seal-sha256",
        required=True,
        type=_expected_sha256_argument,
        action=_StoreOnce,
    )


def _success_summary(
    operation: str,
    result: AuthoringInspectionV29 | PreparedAuthoringInputV29,
) -> str:
    payload: dict[str, object] = {
        "automated_execution_allowed": False,
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "manual_confirmation_required": True,
        "operation": operation,
        "posts_allowed": 0,
        "preparer_version": _PREPARER_VERSION,
        "provider_requests": 0,
        "provider_state": "NOT_AUTHORIZED",
        "target_finalizer_module": _TARGET_FINALIZER_MODULE,
        "target_finalizer_version": _TARGET_FINALIZER_VERSION,
        "usage_restriction": _USAGE_RESTRICTION,
    }
    payload.update(asdict(result))
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _failure_summary(error: str) -> str:
    return json.dumps({"error": error}, separators=(",", ":"), sort_keys=True)


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
        description="Prepare one inert trusted-local v2.7 review authoring input"
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=_FailClosedArgumentParser,
    )
    inspect_maker = commands.add_parser("inspect-maker-authoring")
    _add_inspect_arguments(inspect_maker)
    inspect_checker = commands.add_parser("inspect-checker-authoring")
    _add_inspect_arguments(inspect_checker)
    finalize_maker = commands.add_parser("finalize-maker-authoring")
    _add_finalize_arguments(finalize_maker)
    finalize_checker = commands.add_parser("finalize-checker-authoring")
    _add_finalize_arguments(finalize_checker)
    try:
        args = parser.parse_args(argv)
        command = cast(str, args.command)
        if command == "inspect-maker-authoring":
            result: AuthoringInspectionV29 | PreparedAuthoringInputV29 = inspect_maker_authoring(
                cast(Path, args.draft),
                cast(Path, args.output_parent),
            )
        elif command == "inspect-checker-authoring":
            result = inspect_checker_authoring(
                cast(Path, args.draft),
                cast(Path, args.output_parent),
            )
        elif command == "finalize-maker-authoring":
            result = finalize_maker_authoring(
                cast(Path, args.draft),
                cast(Path, args.output),
                expected_draft_sha256=cast(str, args.expected_draft_sha256),
                expected_authoring_sha256=cast(str, args.expected_authoring_sha256),
                expected_output_parent_seal_sha256=cast(
                    str,
                    args.expected_output_parent_seal_sha256,
                ),
            )
        else:
            result = finalize_checker_authoring(
                cast(Path, args.draft),
                cast(Path, args.output),
                expected_draft_sha256=cast(str, args.expected_draft_sha256),
                expected_authoring_sha256=cast(str, args.expected_authoring_sha256),
                expected_output_parent_seal_sha256=cast(
                    str,
                    args.expected_output_parent_seal_sha256,
                ),
            )
    except TrustedLocalReviewAuthoringQuarantineRequired:
        _write_json_line(
            sys.stderr,
            _failure_summary("ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"),
        )
        return 3
    except BaseException:
        _write_json_line(sys.stderr, _failure_summary("FAILED_CLOSED"))
        return 2
    _write_json_line(sys.stdout, _success_summary(command, result))
    return 0


__all__ = [
    "AuthoringInspectionV29",
    "PreparedAuthoringInputV29",
    "TrustedLocalReviewAuthoringPreparationError",
    "TrustedLocalReviewAuthoringQuarantineRequired",
    "finalize_checker_authoring",
    "finalize_maker_authoring",
    "inspect_checker_authoring",
    "inspect_maker_authoring",
    "main",
]


if __name__ == "__main__":  # pragma: no cover - exercised through the module CLI
    raise SystemExit(main())
