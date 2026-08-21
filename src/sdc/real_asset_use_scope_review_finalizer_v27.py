"""Trusted-local formation and verification of one inert Use Scope Review Record.

The boundary always reconstructs the immutable Maker Request, Checker Instruction and compiler
Decision from one complete physical Use Plan closure.  It never persists an intermediate module,
reads a clock, grants execution authority or contacts a remote service.
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
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Never, cast

from pydantic import BaseModel, ValidationError

import sdc.real_asset_use_plan_finalizer_v27 as _plan_boundary
from sdc.real_asset_media import SafeLocalFile
from sdc.real_asset_use_plan_finalizer_v27 import TrustedLocalUsePlanPaths
from sdc.real_asset_use_plan_v26 import USE_PLAN_V1_POLICY_DOCUMENT_SHA256
from sdc.real_asset_use_scope_review_v26 import (
    USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetUseScopeReviewInstructionV1,
    CreativeSampleRealAssetUseScopeReviewRecordV1,
    CreativeSampleRealAssetUseScopeReviewRequestV1,
    RealAssetUseScopeReviewV26Error,
    UseScopeGateResultV1,
    build_use_scope_review_instruction_v1,
    build_use_scope_review_record_v1,
    build_use_scope_review_request_v1,
    extract_use_scope_decision_v1,
    extract_use_scope_instruction_v1,
    extract_use_scope_request_v1,
    parse_use_scope_review_record_v1_json,
    verify_use_scope_review_record_closure_v1,
)

_AUTHORING_MAX_BYTES = 65_536
_RECORD_MAX_BYTES = 2_097_152
_IDENTITY_MAX_BYTES = 1_048_576
_EXPECTED_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_REQUEST_ID = re.compile(r"^real_asset_use_scope_request_v1_[0-9a-f]{20}$")
_EXPECTED_INSTRUCTION_ID = re.compile(r"^real_asset_use_scope_instruction_v1_[0-9a-f]{20}$")
_EXPECTED_DECISION_ID = re.compile(r"^real_asset_use_scope_decision_v1_[0-9a-f]{20}$")
_EXPECTED_RECORD_ID = re.compile(r"^real_asset_use_scope_review_record_v1_[0-9a-f]{20}$")
_UTC_SECONDS = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_GATE_ORDER = (
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
_OUTCOME_FILENAME_TOKENS = frozenset(
    {"approved", "authorized", "needs", "pass", "rejected", "revision"}
)


class TrustedLocalUseScopeReviewFinalizationError(RuntimeError):
    """The trusted-local v2.7 Use Scope Review boundary failed closed."""


class TrustedLocalUseScopeReviewQuarantineRequired(TrustedLocalUseScopeReviewFinalizationError):
    """Rollback could not prove invalidation or deletion of the exact created Record."""


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
class TrustedLocalUsePlanArtifactPaths:
    sources: TrustedLocalUsePlanPaths
    use_plan: Path


@dataclass(frozen=True, slots=True)
class TrustedLocalUseScopeReviewRequestPaths:
    plan: TrustedLocalUsePlanArtifactPaths
    maker_identity_ref: Path
    maker_input: Path


@dataclass(frozen=True, slots=True)
class TrustedLocalUseScopeReviewInstructionPaths:
    request: TrustedLocalUseScopeReviewRequestPaths
    checker_identity_ref: Path
    checker_input: Path


@dataclass(frozen=True, slots=True)
class TrustedLocalUseScopeReviewVerificationPaths:
    plan: TrustedLocalUsePlanArtifactPaths
    maker_identity_ref: Path
    checker_identity_ref: Path


@dataclass(frozen=True, slots=True)
class UseScopeReviewRequestPreflightV27:
    status: Literal["REVIEW_REQUEST_READY_FOR_CHECKER_PREFLIGHT"]
    request_id: str
    request_sha256: str


@dataclass(frozen=True, slots=True)
class UseScopeReviewInstructionPreflightV27:
    status: Literal["REVIEW_INSTRUCTION_READY_FOR_RECORD_FINALIZATION"]
    instruction_id: str
    instruction_sha256: str
    decision_id: str
    decision_sha256: str
    record_id: str
    record_sha256: str


@dataclass(frozen=True, slots=True)
class _MakerAuthoring:
    request_basis: str


@dataclass(frozen=True, slots=True)
class _CheckerAuthoring:
    gate_results: tuple[UseScopeGateResultV1, ...]
    disposition: Literal["PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY", "NEEDS_REVISION", "REJECTED"]
    checker_basis: str


@dataclass(frozen=True, slots=True)
class _RequestSnapshot:
    plan: _plan_boundary._UsePlanSnapshot
    maker_identity: _plan_boundary._FileSeal
    maker_input_seal: _plan_boundary._FileSeal
    maker_input: _MakerAuthoring
    link_counts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _InstructionSnapshot:
    plan: _plan_boundary._UsePlanSnapshot
    maker_identity: _plan_boundary._FileSeal
    maker_input_seal: _plan_boundary._FileSeal
    maker_input: _MakerAuthoring
    checker_identity: _plan_boundary._FileSeal
    checker_input_seal: _plan_boundary._FileSeal
    checker_input: _CheckerAuthoring
    link_counts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _VerificationSnapshot:
    plan: _plan_boundary._UsePlanSnapshot
    maker_identity: _plan_boundary._FileSeal
    checker_identity: _plan_boundary._FileSeal
    record: CreativeSampleRealAssetUseScopeReviewRecordV1
    record_seal: _plan_boundary._FileSeal
    link_counts: tuple[int, ...]


def _canonical_document(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_utc_seconds(value: str, *, field: str) -> str:
    if type(value) is not str or _UTC_SECONDS.fullmatch(value) is None:
        raise TrustedLocalUseScopeReviewFinalizationError(f"{field} must be canonical UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"{field} must be canonical UTC seconds"
        ) from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise TrustedLocalUseScopeReviewFinalizationError(f"{field} must be canonical UTC seconds")
    return value


def _expected(value: str, pattern: re.Pattern[str], *, field: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise TrustedLocalUseScopeReviewFinalizationError(f"{field} is malformed")
    return value


def _expected_request_pair(request_id: str, request_sha256: str) -> tuple[str, str]:
    return (
        _expected(request_id, _EXPECTED_REQUEST_ID, field="expected Request ID"),
        _expected(request_sha256, _EXPECTED_SHA256, field="expected Request SHA-256"),
    )


def _require_anchor(
    *,
    calculated_id: str,
    calculated_sha256: str,
    expected_id: str,
    expected_sha256: str,
    field: str,
) -> None:
    if calculated_id != expected_id or calculated_sha256 != expected_sha256:
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"calculated {field} approval anchor does not match"
        )


def _portable_human_text(value: object, *, field: str, maximum: int) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > maximum
        or value != value.strip()
        or unicodedata.normalize("NFC", value) != value
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"{field} violates the exact human-text boundary"
        )
    return value


def _reject_json_constant(value: str) -> Never:
    del value
    raise TrustedLocalUseScopeReviewFinalizationError(
        "authoring input contains a non-finite JSON value"
    )


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TrustedLocalUseScopeReviewFinalizationError(
                "authoring input contains a duplicate key"
            )
        result[key] = value
    return result


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _assert_authoring_owner_only_descriptor(descriptor: int) -> None:
    _plan_boundary._assert_owner_only_descriptor(descriptor)


def _required_os_flag(name: str, *, field: str) -> int:
    value = vars(os).get(name)
    if type(value) is not int:
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"{field} authoring safety flag is unavailable"
        )
    return value


def _is_ordinary_single_link(info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    return (
        stat.S_ISREG(info.st_mode)
        and not stat.S_ISLNK(info.st_mode)
        and not bool(attributes & 0x400)
        and info.st_nlink == 1
    )


def _read_stable_review_file(path: Path, *, max_bytes: int, field: str) -> SafeLocalFile:
    """Bind bytes to before/opened/opened-after/after identity and single-link facts."""

    if max_bytes <= 0:
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"{field} has an invalid fixed byte bound"
        )
    flags = os.O_RDONLY
    if os.name == "nt":
        flags |= _required_os_flag("O_BINARY", field="Windows")
        flags |= _required_os_flag("O_NOINHERIT", field="Windows")
    else:
        flags |= _required_os_flag("O_CLOEXEC", field="POSIX")
        flags |= _required_os_flag("O_NOFOLLOW", field="POSIX")
    descriptor: int | None = None
    try:
        before = path.lstat()
        if (
            not _is_ordinary_single_link(before)
            or before.st_size <= 0
            or before.st_size > max_bytes
        ):
            raise TrustedLocalUseScopeReviewFinalizationError(
                f"{field} must be one bounded ordinary single-link file"
            )
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if not _is_ordinary_single_link(opened) or _identity(opened) != _identity(before):
            raise TrustedLocalUseScopeReviewFinalizationError(
                f"{field} changed identity or link count before its read"
            )
        observed = bytearray()
        while len(observed) <= max_bytes:
            chunk = os.read(descriptor, min(65_536, max_bytes + 1 - len(observed)))
            if not chunk:
                break
            observed.extend(chunk)
        opened_after = os.fstat(descriptor)
        after = path.lstat()
    except TrustedLocalUseScopeReviewFinalizationError:
        raise
    except BaseException as exc:
        if isinstance(exc, Exception):
            raise TrustedLocalUseScopeReviewFinalizationError(
                f"{field} could not be read as one stable file"
            ) from exc
        raise
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                raise TrustedLocalUseScopeReviewFinalizationError(
                    f"{field} descriptor could not be closed"
                ) from exc
    data = bytes(observed)
    if (
        not _is_ordinary_single_link(opened_after)
        or not _is_ordinary_single_link(after)
        or _identity(opened_after) != _identity(before)
        or _identity(after) != _identity(before)
        or len(data) != before.st_size
        or len(data) > max_bytes
    ):
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"{field} changed identity, bytes or link count during its read"
        )
    return SafeLocalFile(
        path=path,
        data=data,
        sha256=_sha256(data),
        size_bytes=len(data),
        identity=_identity(before),
    )


def _read_owner_only_authoring(path: Path, *, field: str) -> SafeLocalFile:
    """Check the opened descriptor's owner-only policy before reading any human text."""

    before = path.lstat()
    attributes = int(getattr(before, "st_file_attributes", 0))
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or bool(attributes & 0x400)
        or before.st_nlink != 1
        or before.st_size <= 0
        or before.st_size > _AUTHORING_MAX_BYTES
    ):
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"{field} must be one bounded, ordinary, single-link file"
        )
    flags = os.O_RDONLY
    if os.name == "nt":
        flags |= _required_os_flag("O_BINARY", field="Windows")
        flags |= _required_os_flag("O_NOINHERIT", field="Windows")
    else:
        flags |= _required_os_flag("O_CLOEXEC", field="POSIX")
        flags |= _required_os_flag("O_NOFOLLOW", field="POSIX")
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        opened_attributes = int(getattr(opened, "st_file_attributes", 0))
        if (
            _identity(opened) != _identity(before)
            or not stat.S_ISREG(opened.st_mode)
            or stat.S_ISLNK(opened.st_mode)
            or bool(opened_attributes & 0x400)
            or opened.st_nlink != 1
        ):
            raise TrustedLocalUseScopeReviewFinalizationError(
                f"{field} identity changed before permission inspection"
            )
        _assert_authoring_owner_only_descriptor(descriptor)
        observed = bytearray()
        while len(observed) <= _AUTHORING_MAX_BYTES:
            chunk = os.read(
                descriptor,
                min(65_536, _AUTHORING_MAX_BYTES + 1 - len(observed)),
            )
            if not chunk:
                break
            observed.extend(chunk)
        after = path.lstat()
    except TrustedLocalUseScopeReviewFinalizationError:
        raise
    except BaseException as exc:
        if isinstance(exc, Exception):
            raise TrustedLocalUseScopeReviewFinalizationError(
                f"{field} could not be safely read"
            ) from exc
        raise
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                raise TrustedLocalUseScopeReviewFinalizationError(
                    f"{field} descriptor could not be closed"
                ) from exc
    data = bytes(observed)
    after_attributes = int(getattr(after, "st_file_attributes", 0))
    if (
        len(data) != before.st_size
        or len(data) > _AUTHORING_MAX_BYTES
        or _identity(after) != _identity(before)
        or not stat.S_ISREG(after.st_mode)
        or stat.S_ISLNK(after.st_mode)
        or bool(after_attributes & 0x400)
        or after.st_nlink != 1
    ):
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"{field} changed during bounded inspection"
        )
    return SafeLocalFile(
        path=path,
        data=data,
        sha256=_sha256(data),
        size_bytes=len(data),
        identity=_identity(before),
    )


def _parse_authoring_json(source: SafeLocalFile, *, field: str) -> dict[str, object]:
    raw = source.data
    if raw.startswith(b"\xef\xbb\xbf"):
        raise TrustedLocalUseScopeReviewFinalizationError(f"{field} must not contain a BOM")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except TrustedLocalUseScopeReviewFinalizationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"{field} must be strict UTF-8 JSON"
        ) from exc
    if type(value) is not dict or raw != _canonical_document(value):
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"{field} must be the exact canonical JSON document"
        )
    return cast(dict[str, object], value)


def _read_maker_authoring(
    path: Path,
) -> tuple[_MakerAuthoring, _plan_boundary._FileSeal]:
    source = _read_owner_only_authoring(path, field="Maker authoring input")
    value = _parse_authoring_json(source, field="Maker authoring input")
    if set(value) != {"request_basis"}:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Maker authoring input has missing or unknown members"
        )
    parsed = _MakerAuthoring(
        request_basis=_portable_human_text(
            value["request_basis"], field="Maker request basis", maximum=2000
        )
    )
    return parsed, _plan_boundary._file_seal(source)


def _read_checker_authoring(
    path: Path,
) -> tuple[_CheckerAuthoring, _plan_boundary._FileSeal]:
    source = _read_owner_only_authoring(path, field="Checker authoring input")
    value = _parse_authoring_json(source, field="Checker authoring input")
    if set(value) != {"checker_basis", "disposition", "gate_results"}:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Checker authoring input has missing or unknown members"
        )
    disposition = value["disposition"]
    if type(disposition) is not str or disposition not in _DISPOSITIONS:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Checker disposition is not one exact policy value"
        )
    raw_gates = value["gate_results"]
    if type(raw_gates) is not list or len(raw_gates) != len(_GATE_ORDER):
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Checker authoring input requires the six ordered gates"
        )
    gates: list[UseScopeGateResultV1] = []
    for expected_gate, item in zip(_GATE_ORDER, raw_gates, strict=True):
        if type(item) is not dict or set(item) != {"approved", "gate", "note"}:
            raise TrustedLocalUseScopeReviewFinalizationError(
                "Checker gate has missing or unknown members"
            )
        gate = cast(dict[str, object], item)
        if gate["gate"] != expected_gate or type(gate["approved"]) is not bool:
            raise TrustedLocalUseScopeReviewFinalizationError(
                "Checker gates must use the fixed order and exact boolean type"
            )
        note = gate["note"]
        if gate["approved"] is True:
            if note is not None:
                raise TrustedLocalUseScopeReviewFinalizationError(
                    "an approved Checker gate must have a null note"
                )
        else:
            note = _portable_human_text(note, field="Checker gate note", maximum=1000)
        try:
            gates.append(
                UseScopeGateResultV1.model_validate(
                    {"gate": expected_gate, "approved": gate["approved"], "note": note},
                    strict=True,
                )
            )
        except ValidationError as exc:
            raise TrustedLocalUseScopeReviewFinalizationError(
                "Checker gate violates the exact review policy"
            ) from exc
    parsed_disposition = cast(
        Literal["PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY", "NEEDS_REVISION", "REJECTED"],
        disposition,
    )
    parsed = _CheckerAuthoring(
        gate_results=tuple(gates),
        disposition=parsed_disposition,
        checker_basis=_portable_human_text(
            value["checker_basis"], field="Checker basis", maximum=2000
        ),
    )
    return parsed, _plan_boundary._file_seal(source)


def _reject_review_artifact_filename(path: Path, *, field: str) -> None:
    if path.suffix.casefold() != ".json":
        raise TrustedLocalUseScopeReviewFinalizationError(f"{field} must use an exact JSON suffix")
    tokens = frozenset(filter(None, re.split(r"[^a-z0-9]+", path.stem.casefold())))
    if tokens & _OUTCOME_FILENAME_TOKENS:
        raise TrustedLocalUseScopeReviewFinalizationError(
            f"{field} filename contains a forbidden outcome or authority token"
        )


def _normalize_plan_artifact_paths(
    paths: TrustedLocalUsePlanArtifactPaths,
) -> TrustedLocalUsePlanArtifactPaths:
    if type(paths) is not TrustedLocalUsePlanArtifactPaths:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Use Plan artifact paths use the wrong operational type"
        )
    sources = _plan_boundary._normalize_use_plan_paths(paths.sources)
    use_plan = _plan_boundary._validate_existing_use_plan(paths.use_plan, paths=sources)
    return TrustedLocalUsePlanArtifactPaths(sources=sources, use_plan=use_plan)


def _safe_source(path: Path, *, field: str) -> Path:
    return _plan_boundary._safe_absolute(path, must_exist=True, field=field)


def _assert_json_authoring_name(path: Path, *, field: str) -> None:
    if path.suffix.casefold() != ".json":
        raise TrustedLocalUseScopeReviewFinalizationError(f"{field} must use an exact JSON suffix")


def _plan_file_paths(plan: TrustedLocalUsePlanArtifactPaths) -> tuple[Path, ...]:
    return (*_plan_boundary._all_use_plan_source_paths(plan.sources), plan.use_plan)


def _assert_distinct_named_files(paths: tuple[Path, ...], *, expected: int) -> None:
    if (
        len(paths) != expected
        or len(set(paths)) != expected
        or len({path.as_posix().casefold() for path in paths}) != expected
    ):
        raise TrustedLocalUseScopeReviewFinalizationError(
            "review operation does not contain its exact distinct source set"
        )


def _assert_separate_added_areas(
    plan: TrustedLocalUsePlanArtifactPaths,
    additions: tuple[tuple[Path, str], ...],
) -> tuple[Path, ...]:
    areas = [*_plan_boundary._use_plan_trust_areas(plan.sources), plan.use_plan.parent]
    for path, field in additions:
        _plan_boundary._assert_separate_trust_parent(
            path.parent,
            tuple(areas),
            field=f"{field} parent",
        )
        areas.append(path.parent)
    return tuple(areas)


def _normalize_request_paths(
    paths: TrustedLocalUseScopeReviewRequestPaths,
) -> TrustedLocalUseScopeReviewRequestPaths:
    if type(paths) is not TrustedLocalUseScopeReviewRequestPaths:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Request paths use the wrong operational type"
        )
    plan = _normalize_plan_artifact_paths(paths.plan)
    maker_identity = _safe_source(paths.maker_identity_ref, field="Maker identity reference")
    maker_input = _safe_source(paths.maker_input, field="Maker authoring input")
    _assert_json_authoring_name(maker_input, field="Maker authoring input")
    _assert_separate_added_areas(
        plan,
        (
            (maker_identity, "Maker identity reference"),
            (maker_input, "Maker authoring input"),
        ),
    )
    _assert_distinct_named_files(
        (*_plan_file_paths(plan), maker_identity, maker_input), expected=32
    )
    return TrustedLocalUseScopeReviewRequestPaths(
        plan=plan,
        maker_identity_ref=maker_identity,
        maker_input=maker_input,
    )


def _normalize_instruction_paths(
    paths: TrustedLocalUseScopeReviewInstructionPaths,
) -> TrustedLocalUseScopeReviewInstructionPaths:
    if type(paths) is not TrustedLocalUseScopeReviewInstructionPaths:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Instruction paths use the wrong operational type"
        )
    request = _normalize_request_paths(paths.request)
    checker_identity = _safe_source(paths.checker_identity_ref, field="Checker identity reference")
    checker_input = _safe_source(paths.checker_input, field="Checker authoring input")
    _assert_json_authoring_name(checker_input, field="Checker authoring input")
    _assert_separate_added_areas(
        request.plan,
        (
            (request.maker_identity_ref, "Maker identity reference"),
            (request.maker_input, "Maker authoring input"),
            (checker_identity, "Checker identity reference"),
            (checker_input, "Checker authoring input"),
        ),
    )
    _assert_distinct_named_files(
        (
            *_plan_file_paths(request.plan),
            request.maker_identity_ref,
            request.maker_input,
            checker_identity,
            checker_input,
        ),
        expected=34,
    )
    return TrustedLocalUseScopeReviewInstructionPaths(
        request=request,
        checker_identity_ref=checker_identity,
        checker_input=checker_input,
    )


def _normalize_verification_paths(
    paths: TrustedLocalUseScopeReviewVerificationPaths,
) -> TrustedLocalUseScopeReviewVerificationPaths:
    if type(paths) is not TrustedLocalUseScopeReviewVerificationPaths:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "verification paths use the wrong operational type"
        )
    plan = _normalize_plan_artifact_paths(paths.plan)
    maker_identity = _safe_source(paths.maker_identity_ref, field="Maker identity reference")
    checker_identity = _safe_source(paths.checker_identity_ref, field="Checker identity reference")
    _assert_separate_added_areas(
        plan,
        (
            (maker_identity, "Maker identity reference"),
            (checker_identity, "Checker identity reference"),
        ),
    )
    _assert_distinct_named_files(
        (*_plan_file_paths(plan), maker_identity, checker_identity), expected=32
    )
    return TrustedLocalUseScopeReviewVerificationPaths(
        plan=plan,
        maker_identity_ref=maker_identity,
        checker_identity_ref=checker_identity,
    )


def _read_identity(path: Path, *, field: str) -> _plan_boundary._FileSeal:
    source = _read_stable_review_file(path, max_bytes=_IDENTITY_MAX_BYTES, field=field)
    return _plan_boundary._file_seal(source)


def _review_link_counts(files: tuple[_plan_boundary._FileSeal, ...]) -> tuple[int, ...]:
    try:
        return _plan_boundary._revalidate_file_link_counts(files)
    except _plan_boundary.TrustedLocalUsePlanFinalizationError as exc:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Review source link-count revalidation failed closed"
        ) from exc


def _assert_non_aliasing_review_files(
    plan: _plan_boundary._UsePlanSnapshot,
    extras: tuple[_plan_boundary._FileSeal, ...],
) -> None:
    if plan.use_plan_seal is None:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "review operations require one existing Use Plan"
        )
    _plan_boundary._assert_non_aliasing(
        (*plan.manifest_snapshot.files, plan.use_plan_seal, *extras)
    )
    reserved = {
        *_plan_boundary._reserved_use_plan_snapshot_digests(plan),
        USE_PLAN_V1_POLICY_DOCUMENT_SHA256,
        USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256,
    }
    extra_digests = [item.sha256 for item in extras]
    if len(set(extra_digests)) != len(extra_digests) or any(
        digest in reserved for digest in extra_digests
    ):
        raise TrustedLocalUseScopeReviewFinalizationError(
            "identity, authoring or Record bytes alias another closure digest"
        )


def _verify_plan_snapshot(snapshot: _plan_boundary._UsePlanSnapshot) -> None:
    verified = _plan_boundary._verify_use_plan_snapshot(snapshot)
    if snapshot.use_plan is None or verified != snapshot.use_plan:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Use Plan failed exact full-closure verification"
        )


def _reserved_instruction_snapshot_digests(
    snapshot: _InstructionSnapshot,
) -> set[str]:
    return {
        *_plan_boundary._reserved_use_plan_snapshot_digests(snapshot.plan),
        snapshot.maker_identity.sha256,
        snapshot.maker_input_seal.sha256,
        snapshot.checker_identity.sha256,
        snapshot.checker_input_seal.sha256,
        USE_PLAN_V1_POLICY_DOCUMENT_SHA256,
        USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256,
    }


def _capture_request_snapshot(
    paths: TrustedLocalUseScopeReviewRequestPaths,
) -> _RequestSnapshot:
    plan = _plan_boundary._capture_use_plan_snapshot(
        paths.plan.sources, use_plan_path=paths.plan.use_plan
    )
    maker_identity = _read_identity(paths.maker_identity_ref, field="Maker identity reference")
    maker_input, maker_input_seal = _read_maker_authoring(paths.maker_input)
    _assert_non_aliasing_review_files(plan, (maker_identity, maker_input_seal))
    return _RequestSnapshot(
        plan=plan,
        maker_identity=maker_identity,
        maker_input_seal=maker_input_seal,
        maker_input=maker_input,
        link_counts=_review_link_counts((maker_identity, maker_input_seal)),
    )


def _capture_instruction_snapshot(
    paths: TrustedLocalUseScopeReviewInstructionPaths,
) -> _InstructionSnapshot:
    plan = _plan_boundary._capture_use_plan_snapshot(
        paths.request.plan.sources, use_plan_path=paths.request.plan.use_plan
    )
    maker_identity = _read_identity(
        paths.request.maker_identity_ref, field="Maker identity reference"
    )
    maker_input, maker_input_seal = _read_maker_authoring(paths.request.maker_input)
    checker_identity = _read_identity(
        paths.checker_identity_ref, field="Checker identity reference"
    )
    checker_input, checker_input_seal = _read_checker_authoring(paths.checker_input)
    _assert_non_aliasing_review_files(
        plan,
        (maker_identity, maker_input_seal, checker_identity, checker_input_seal),
    )
    return _InstructionSnapshot(
        plan=plan,
        maker_identity=maker_identity,
        maker_input_seal=maker_input_seal,
        maker_input=maker_input,
        checker_identity=checker_identity,
        checker_input_seal=checker_input_seal,
        checker_input=checker_input,
        link_counts=_review_link_counts(
            (maker_identity, maker_input_seal, checker_identity, checker_input_seal)
        ),
    )


def _validate_existing_record(
    record_path: Path,
    *,
    paths: TrustedLocalUseScopeReviewVerificationPaths,
) -> Path:
    record = _safe_source(record_path, field="existing Use Scope Review Record")
    _reject_review_artifact_filename(record, field="existing Use Scope Review Record")
    additions = (
        (paths.maker_identity_ref, "Maker identity reference"),
        (paths.checker_identity_ref, "Checker identity reference"),
        (record, "existing Use Scope Review Record"),
    )
    _assert_separate_added_areas(paths.plan, additions)
    _assert_distinct_named_files(
        (*_plan_file_paths(paths.plan), *(item[0] for item in additions)), expected=33
    )
    return record


def _read_record(
    path: Path,
) -> tuple[CreativeSampleRealAssetUseScopeReviewRecordV1, _plan_boundary._FileSeal]:
    source = _read_stable_review_file(
        path,
        max_bytes=_RECORD_MAX_BYTES,
        field="Use Scope Review Record",
    )
    try:
        record = parse_use_scope_review_record_v1_json(source.data)
    except RealAssetUseScopeReviewV26Error as exc:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Use Scope Review Record violates its strict contract"
        ) from exc
    if source.data != _canonical_document(record):
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Use Scope Review Record bytes are not canonical"
        )
    return record, _plan_boundary._file_seal(source)


def _capture_verification_snapshot(
    paths: TrustedLocalUseScopeReviewVerificationPaths,
    *,
    record_path: Path,
) -> _VerificationSnapshot:
    plan = _plan_boundary._capture_use_plan_snapshot(
        paths.plan.sources, use_plan_path=paths.plan.use_plan
    )
    maker_identity = _read_identity(paths.maker_identity_ref, field="Maker identity reference")
    checker_identity = _read_identity(
        paths.checker_identity_ref, field="Checker identity reference"
    )
    record, record_seal = _read_record(record_path)
    _assert_non_aliasing_review_files(plan, (maker_identity, checker_identity, record_seal))
    return _VerificationSnapshot(
        plan=plan,
        maker_identity=maker_identity,
        checker_identity=checker_identity,
        record=record,
        record_seal=record_seal,
        link_counts=_review_link_counts((maker_identity, checker_identity, record_seal)),
    )


def _assert_request_snapshot_unchanged(before: _RequestSnapshot, after: _RequestSnapshot) -> None:
    _plan_boundary._assert_use_plan_snapshot_unchanged(before.plan, after.plan)
    if before != after:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Request inputs drifted during complete verification"
        )


def _assert_instruction_snapshot_unchanged(
    before: _InstructionSnapshot, after: _InstructionSnapshot
) -> None:
    _plan_boundary._assert_use_plan_snapshot_unchanged(before.plan, after.plan)
    if before != after:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Instruction inputs drifted during complete verification"
        )


def _assert_verification_snapshot_unchanged(
    before: _VerificationSnapshot, after: _VerificationSnapshot
) -> None:
    _plan_boundary._assert_use_plan_snapshot_unchanged(before.plan, after.plan)
    if before != after:
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Review verification inputs drifted during complete verification"
        )


def _build_request(
    snapshot: _RequestSnapshot | _InstructionSnapshot,
    *,
    requested_at: str,
) -> CreativeSampleRealAssetUseScopeReviewRequestV1:
    if snapshot.plan.use_plan is None:
        raise TrustedLocalUseScopeReviewFinalizationError("Use Plan is missing")
    return build_use_scope_review_request_v1(
        use_plan=snapshot.plan.use_plan,
        maker_identity_ref_sha256=snapshot.maker_identity.sha256,
        requested_at=requested_at,
        request_basis=snapshot.maker_input.request_basis,
    )


def _build_instruction(
    snapshot: _InstructionSnapshot,
    *,
    request: CreativeSampleRealAssetUseScopeReviewRequestV1,
    evaluated_at: str,
) -> CreativeSampleRealAssetUseScopeReviewInstructionV1:
    return build_use_scope_review_instruction_v1(
        request=request,
        checker_identity_ref_sha256=snapshot.checker_identity.sha256,
        evaluated_at=evaluated_at,
        gate_results=snapshot.checker_input.gate_results,
        disposition=snapshot.checker_input.disposition,
        checker_basis=snapshot.checker_input.checker_basis,
    )


def _translate_boundary_error(exc: BaseException, *, message: str) -> Never:
    if isinstance(exc, TrustedLocalUseScopeReviewFinalizationError):
        raise exc
    if isinstance(exc, _plan_boundary.TrustedLocalUsePlanQuarantineRequired):
        raise TrustedLocalUseScopeReviewQuarantineRequired(message) from exc
    if isinstance(exc, Exception):
        raise TrustedLocalUseScopeReviewFinalizationError(message) from exc
    raise exc


def preflight_review_request(
    paths: TrustedLocalUseScopeReviewRequestPaths,
    *,
    requested_at: str,
) -> UseScopeReviewRequestPreflightV27:
    """Rebuild only the Maker Request and expose its comparison anchor."""

    requested_at = _canonical_utc_seconds(requested_at, field="requested_at")
    try:
        normalized = _normalize_request_paths(paths)
        before = _capture_request_snapshot(normalized)
        _verify_plan_snapshot(before.plan)
        request = _build_request(before, requested_at=requested_at)
        after = _capture_request_snapshot(normalized)
        _assert_request_snapshot_unchanged(before, after)
        return UseScopeReviewRequestPreflightV27(
            status="REVIEW_REQUEST_READY_FOR_CHECKER_PREFLIGHT",
            request_id=request.request_id,
            request_sha256=_sha256(_canonical_document(request)),
        )
    except BaseException as exc:
        _translate_boundary_error(exc, message="Request preflight failed closed")


def preflight_review_instruction(
    paths: TrustedLocalUseScopeReviewInstructionPaths,
    *,
    requested_at: str,
    evaluated_at: str,
    expected_request_id: str,
    expected_request_sha256: str,
) -> UseScopeReviewInstructionPreflightV27:
    """Guard the rebuilt Request, then transiently derive Instruction/Decision/Record anchors."""

    expected_request_id, expected_request_sha256 = _expected_request_pair(
        expected_request_id, expected_request_sha256
    )
    requested_at = _canonical_utc_seconds(requested_at, field="requested_at")
    evaluated_at = _canonical_utc_seconds(evaluated_at, field="evaluated_at")
    try:
        normalized = _normalize_instruction_paths(paths)
        before = _capture_instruction_snapshot(normalized)
        _verify_plan_snapshot(before.plan)
        request = _build_request(before, requested_at=requested_at)
        _require_anchor(
            calculated_id=request.request_id,
            calculated_sha256=_sha256(_canonical_document(request)),
            expected_id=expected_request_id,
            expected_sha256=expected_request_sha256,
            field="Request",
        )
        instruction = _build_instruction(
            before,
            request=request,
            evaluated_at=evaluated_at,
        )
        record = build_use_scope_review_record_v1(
            request=request,
            instruction=instruction,
        )
        record_sha256 = _sha256(_canonical_document(record))
        if record_sha256 in _reserved_instruction_snapshot_digests(before):
            raise TrustedLocalUseScopeReviewFinalizationError(
                "candidate Review Record aliases a source or policy digest"
            )
        after = _capture_instruction_snapshot(normalized)
        _assert_instruction_snapshot_unchanged(before, after)
        return UseScopeReviewInstructionPreflightV27(
            status="REVIEW_INSTRUCTION_READY_FOR_RECORD_FINALIZATION",
            instruction_id=instruction.instruction_id,
            instruction_sha256=_sha256(_canonical_document(instruction)),
            decision_id=record.decision.decision_id,
            decision_sha256=_sha256(_canonical_document(record.decision)),
            record_id=record.record_id,
            record_sha256=record_sha256,
        )
    except BaseException as exc:
        _translate_boundary_error(exc, message="Instruction preflight failed closed")


def _review_output_target(
    output_path: Path,
    *,
    paths: TrustedLocalUseScopeReviewInstructionPaths,
) -> _plan_boundary._OutputTarget:
    output = _plan_boundary._safe_absolute(
        output_path,
        must_exist=False,
        field="Use Scope Review Record output",
    )
    if os.path.lexists(output):
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Use Scope Review Record output must be absent"
        )
    _reject_review_artifact_filename(output, field="Use Scope Review Record output")
    source_paths = (
        *_plan_file_paths(paths.request.plan),
        paths.request.maker_identity_ref,
        paths.request.maker_input,
        paths.checker_identity_ref,
        paths.checker_input,
    )
    if any(_plan_boundary._paths_overlap(output, source) for source in source_paths):
        raise TrustedLocalUseScopeReviewFinalizationError(
            "Use Scope Review Record output overlaps a source"
        )
    areas = _assert_separate_added_areas(
        paths.request.plan,
        (
            (paths.request.maker_identity_ref, "Maker identity reference"),
            (paths.request.maker_input, "Maker authoring input"),
            (paths.checker_identity_ref, "Checker identity reference"),
            (paths.checker_input, "Checker authoring input"),
        ),
    )
    _plan_boundary._assert_separate_trust_parent(
        output.parent,
        areas,
        field="Use Scope Review Record output parent",
    )
    identity = _plan_boundary._directory_identity(
        output.parent, field="Use Scope Review Record output parent"
    )
    return _plan_boundary._OutputTarget(
        path=output,
        parent=output.parent,
        parent_physical_identity=(identity[0], identity[1]),
    )


def finalize_review_record(
    paths: TrustedLocalUseScopeReviewInstructionPaths,
    output_path: Path,
    *,
    requested_at: str,
    evaluated_at: str,
    expected_request_id: str,
    expected_request_sha256: str,
    expected_instruction_id: str,
    expected_instruction_sha256: str,
    expected_decision_id: str,
    expected_decision_sha256: str,
    expected_record_id: str,
    expected_record_sha256: str,
) -> CreativeSampleRealAssetUseScopeReviewRecordV1:
    """Create-new one complete Record after every independently approved anchor matches."""

    expected_request_id, expected_request_sha256 = _expected_request_pair(
        expected_request_id, expected_request_sha256
    )
    expected_instruction_id = _expected(
        expected_instruction_id,
        _EXPECTED_INSTRUCTION_ID,
        field="expected Instruction ID",
    )
    expected_instruction_sha256 = _expected(
        expected_instruction_sha256,
        _EXPECTED_SHA256,
        field="expected Instruction SHA-256",
    )
    expected_decision_id = _expected(
        expected_decision_id, _EXPECTED_DECISION_ID, field="expected Decision ID"
    )
    expected_decision_sha256 = _expected(
        expected_decision_sha256,
        _EXPECTED_SHA256,
        field="expected Decision SHA-256",
    )
    expected_record_id = _expected(
        expected_record_id, _EXPECTED_RECORD_ID, field="expected Record ID"
    )
    expected_record_sha256 = _expected(
        expected_record_sha256,
        _EXPECTED_SHA256,
        field="expected Record SHA-256",
    )
    requested_at = _canonical_utc_seconds(requested_at, field="requested_at")
    evaluated_at = _canonical_utc_seconds(evaluated_at, field="evaluated_at")

    created: _plan_boundary._CreatedArtifact | None = None
    try:
        normalized = _normalize_instruction_paths(paths)
        target = _review_output_target(output_path, paths=normalized)
        before = _capture_instruction_snapshot(normalized)
        _verify_plan_snapshot(before.plan)
        request = _build_request(before, requested_at=requested_at)
        request_sha256 = _sha256(_canonical_document(request))
        _require_anchor(
            calculated_id=request.request_id,
            calculated_sha256=request_sha256,
            expected_id=expected_request_id,
            expected_sha256=expected_request_sha256,
            field="Request",
        )
        instruction = _build_instruction(
            before,
            request=request,
            evaluated_at=evaluated_at,
        )
        instruction_sha256 = _sha256(_canonical_document(instruction))
        _require_anchor(
            calculated_id=instruction.instruction_id,
            calculated_sha256=instruction_sha256,
            expected_id=expected_instruction_id,
            expected_sha256=expected_instruction_sha256,
            field="Instruction",
        )
        record = build_use_scope_review_record_v1(
            request=request,
            instruction=instruction,
        )
        decision_sha256 = _sha256(_canonical_document(record.decision))
        record_sha256 = _sha256(_canonical_document(record))
        _require_anchor(
            calculated_id=record.decision.decision_id,
            calculated_sha256=decision_sha256,
            expected_id=expected_decision_id,
            expected_sha256=expected_decision_sha256,
            field="Decision",
        )
        _require_anchor(
            calculated_id=record.record_id,
            calculated_sha256=record_sha256,
            expected_id=expected_record_id,
            expected_sha256=expected_record_sha256,
            field="Record",
        )
        if len(_canonical_document(record)) > _RECORD_MAX_BYTES:
            raise TrustedLocalUseScopeReviewFinalizationError(
                "candidate Review Record exceeds its fixed byte bound"
            )
        if record_sha256 in _reserved_instruction_snapshot_digests(before):
            raise TrustedLocalUseScopeReviewFinalizationError(
                "candidate Review Record aliases a source or policy digest"
            )
        immediately_before_write = _capture_instruction_snapshot(normalized)
        _assert_instruction_snapshot_unchanged(before, immediately_before_write)
        created = _plan_boundary._create_new_artifact(
            target,
            record,
            parser=parse_use_scope_review_record_v1_json,
            maximum_bytes=_RECORD_MAX_BYTES,
            field="Use Scope Review Record",
        )
        if created.seal is None:
            raise TrustedLocalUseScopeReviewFinalizationError(
                "created Review Record has no retained seal"
            )
        if created.seal.sha256 in _reserved_instruction_snapshot_digests(before):
            raise TrustedLocalUseScopeReviewFinalizationError(
                "written Review Record aliases a source or policy digest"
            )
        after = _capture_instruction_snapshot(normalized)
        _assert_instruction_snapshot_unchanged(before, after)
        _plan_boundary._commit_created_artifact(
            created,
            record,
            parser=parse_use_scope_review_record_v1_json,
            maximum_bytes=_RECORD_MAX_BYTES,
            field="Use Scope Review Record",
        )
        return record
    except BaseException as exc:
        if created is not None and not created.closed:
            try:
                _plan_boundary._rollback_created_artifact(created)
            except BaseException as rollback_exc:
                if isinstance(rollback_exc, _plan_boundary.TrustedLocalUsePlanQuarantineRequired):
                    raise TrustedLocalUseScopeReviewQuarantineRequired(
                        "Review Record rollback requires quarantine"
                    ) from rollback_exc
                raise
        _translate_boundary_error(exc, message="Review Record finalization failed closed")


def verify_review_record(
    paths: TrustedLocalUseScopeReviewVerificationPaths,
    record_path: Path,
) -> CreativeSampleRealAssetUseScopeReviewRecordV1:
    """Historically verify one Record without reopening authoring input or reading a clock."""

    try:
        normalized = _normalize_verification_paths(paths)
        record_path = _validate_existing_record(record_path, paths=normalized)
        before = _capture_verification_snapshot(normalized, record_path=record_path)
        manifest = before.plan.manifest_snapshot
        use_plan = before.plan.use_plan
        rights_manifest = manifest.manifest
        if use_plan is None or rights_manifest is None:
            raise TrustedLocalUseScopeReviewFinalizationError(
                "Use Plan or Rights Manifest is missing"
            )
        verified = verify_use_scope_review_record_closure_v1(
            pack=manifest.pack.manifest,
            evidence=manifest.evidence,
            reviewer_a=manifest.reviewer_a,
            reviewer_b=manifest.reviewer_b,
            pair_check=manifest.pair_check,
            qualification_request=manifest.request,
            qualification_instruction=manifest.instruction,
            qualification_decision=manifest.decision,
            rights_manifest=rights_manifest,
            use_plan=use_plan,
            record=before.record,
        )
        if verified != before.record:
            raise TrustedLocalUseScopeReviewFinalizationError(
                "Review Record verifier returned a different closure"
            )
        if (
            verified.request.maker_identity_ref_sha256 != before.maker_identity.sha256
            or verified.instruction.checker_identity_ref_sha256 != before.checker_identity.sha256
        ):
            raise TrustedLocalUseScopeReviewFinalizationError(
                "Review Record identity references do not match current exact bytes"
            )
        request, request_raw = extract_use_scope_request_v1(verified)
        instruction, instruction_raw = extract_use_scope_instruction_v1(verified)
        decision, decision_raw = extract_use_scope_decision_v1(verified)
        if (
            request != verified.request
            or instruction != verified.instruction
            or decision != verified.decision
            or request_raw != _canonical_document(verified.request)
            or instruction_raw != _canonical_document(verified.instruction)
            or decision_raw != _canonical_document(verified.decision)
            or _sha256(request_raw) != verified.request_sha256
            or _sha256(instruction_raw) != verified.instruction_sha256
            or _sha256(decision_raw) != verified.decision_sha256
        ):
            raise TrustedLocalUseScopeReviewFinalizationError(
                "Review Record module extraction drifted"
            )
        after = _capture_verification_snapshot(normalized, record_path=record_path)
        _assert_verification_snapshot_unchanged(before, after)
        return verified
    except BaseException as exc:
        _translate_boundary_error(
            exc,
            message="Review Record historical verification failed closed",
        )


def _arg_expected(pattern: re.Pattern[str]) -> Callable[[str], str]:
    def parse(value: str) -> str:
        if pattern.fullmatch(value) is None:
            raise argparse.ArgumentTypeError("malformed approval anchor")
        return value

    return parse


def _arg_utc(value: str) -> str:
    try:
        return _canonical_utc_seconds(value, field="review timestamp")
    except TrustedLocalUseScopeReviewFinalizationError as exc:
        raise argparse.ArgumentTypeError("malformed review timestamp") from exc


def _add_plan_artifact_argument(parser: argparse.ArgumentParser) -> None:
    _plan_boundary._add_common_arguments(parser)
    parser.add_argument("--use-plan-file", required=True, type=Path, action=_StoreOnce)


def _add_request_arguments(parser: argparse.ArgumentParser) -> None:
    _add_plan_artifact_argument(parser)
    parser.add_argument("--maker-identity-ref", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--maker-input", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--requested-at", required=True, type=_arg_utc, action=_StoreOnce)


def _add_instruction_arguments(parser: argparse.ArgumentParser) -> None:
    _add_request_arguments(parser)
    parser.add_argument(
        "--expected-request-id",
        required=True,
        type=_arg_expected(_EXPECTED_REQUEST_ID),
        action=_StoreOnce,
    )
    parser.add_argument(
        "--expected-request-sha256",
        required=True,
        type=_arg_expected(_EXPECTED_SHA256),
        action=_StoreOnce,
    )
    parser.add_argument("--checker-identity-ref", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--checker-input", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--evaluated-at", required=True, type=_arg_utc, action=_StoreOnce)


def _plan_artifact_paths_from_namespace(
    args: argparse.Namespace,
) -> TrustedLocalUsePlanArtifactPaths:
    return TrustedLocalUsePlanArtifactPaths(
        sources=_plan_boundary._paths_from_namespace(args),
        use_plan=cast(Path, args.use_plan_file),
    )


def _request_paths_from_namespace(
    args: argparse.Namespace,
) -> TrustedLocalUseScopeReviewRequestPaths:
    return TrustedLocalUseScopeReviewRequestPaths(
        plan=_plan_artifact_paths_from_namespace(args),
        maker_identity_ref=cast(Path, args.maker_identity_ref),
        maker_input=cast(Path, args.maker_input),
    )


def _instruction_paths_from_namespace(
    args: argparse.Namespace,
) -> TrustedLocalUseScopeReviewInstructionPaths:
    return TrustedLocalUseScopeReviewInstructionPaths(
        request=_request_paths_from_namespace(args),
        checker_identity_ref=cast(Path, args.checker_identity_ref),
        checker_input=cast(Path, args.checker_input),
    )


def _success_summary(operation: str, result: object) -> str:
    payload: dict[str, object] = {
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "operation": operation,
        "posts_allowed": 0,
        "provider_requests": 0,
        "provider_state": "NOT_AUTHORIZED",
    }
    if isinstance(result, UseScopeReviewRequestPreflightV27):
        payload.update(
            status=result.status,
            request_id=result.request_id,
            request_sha256=result.request_sha256,
        )
    elif isinstance(result, UseScopeReviewInstructionPreflightV27):
        payload.update(
            status=result.status,
            instruction_id=result.instruction_id,
            instruction_sha256=result.instruction_sha256,
            decision_id=result.decision_id,
            decision_sha256=result.decision_sha256,
            record_id=result.record_id,
            record_sha256=result.record_sha256,
        )
    elif operation == "finalize-review-record":
        payload["status"] = "USE_SCOPE_REVIEW_RECORD_FINALIZED"
    else:
        payload["status"] = "USE_SCOPE_REVIEW_RECORD_HISTORICALLY_VERIFIED"
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
        description="Form or verify one trusted-local inert Use Scope Review Record"
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=_FailClosedArgumentParser,
    )
    request_parser = commands.add_parser("preflight-review-request")
    _add_request_arguments(request_parser)
    instruction_parser = commands.add_parser("preflight-review-instruction")
    _add_instruction_arguments(instruction_parser)
    finalize_parser = commands.add_parser("finalize-review-record")
    _add_instruction_arguments(finalize_parser)
    finalize_parser.add_argument(
        "--expected-instruction-id",
        required=True,
        type=_arg_expected(_EXPECTED_INSTRUCTION_ID),
        action=_StoreOnce,
    )
    finalize_parser.add_argument(
        "--expected-instruction-sha256",
        required=True,
        type=_arg_expected(_EXPECTED_SHA256),
        action=_StoreOnce,
    )
    finalize_parser.add_argument(
        "--expected-decision-id",
        required=True,
        type=_arg_expected(_EXPECTED_DECISION_ID),
        action=_StoreOnce,
    )
    finalize_parser.add_argument(
        "--expected-decision-sha256",
        required=True,
        type=_arg_expected(_EXPECTED_SHA256),
        action=_StoreOnce,
    )
    finalize_parser.add_argument(
        "--expected-record-id",
        required=True,
        type=_arg_expected(_EXPECTED_RECORD_ID),
        action=_StoreOnce,
    )
    finalize_parser.add_argument(
        "--expected-record-sha256",
        required=True,
        type=_arg_expected(_EXPECTED_SHA256),
        action=_StoreOnce,
    )
    finalize_parser.add_argument("--output", required=True, type=Path, action=_StoreOnce)
    verify_parser = commands.add_parser("verify-review-record")
    _add_plan_artifact_argument(verify_parser)
    verify_parser.add_argument("--maker-identity-ref", required=True, type=Path, action=_StoreOnce)
    verify_parser.add_argument(
        "--checker-identity-ref", required=True, type=Path, action=_StoreOnce
    )
    verify_parser.add_argument("--review-record-file", required=True, type=Path, action=_StoreOnce)
    try:
        args = parser.parse_args(argv)
        command = cast(str, args.command)
        if command == "preflight-review-request":
            result: object = preflight_review_request(
                _request_paths_from_namespace(args),
                requested_at=cast(str, args.requested_at),
            )
        elif command == "preflight-review-instruction":
            result = preflight_review_instruction(
                _instruction_paths_from_namespace(args),
                requested_at=cast(str, args.requested_at),
                evaluated_at=cast(str, args.evaluated_at),
                expected_request_id=cast(str, args.expected_request_id),
                expected_request_sha256=cast(str, args.expected_request_sha256),
            )
        elif command == "finalize-review-record":
            result = finalize_review_record(
                _instruction_paths_from_namespace(args),
                cast(Path, args.output),
                requested_at=cast(str, args.requested_at),
                evaluated_at=cast(str, args.evaluated_at),
                expected_request_id=cast(str, args.expected_request_id),
                expected_request_sha256=cast(str, args.expected_request_sha256),
                expected_instruction_id=cast(str, args.expected_instruction_id),
                expected_instruction_sha256=cast(str, args.expected_instruction_sha256),
                expected_decision_id=cast(str, args.expected_decision_id),
                expected_decision_sha256=cast(str, args.expected_decision_sha256),
                expected_record_id=cast(str, args.expected_record_id),
                expected_record_sha256=cast(str, args.expected_record_sha256),
            )
        else:
            verification_paths = TrustedLocalUseScopeReviewVerificationPaths(
                plan=_plan_artifact_paths_from_namespace(args),
                maker_identity_ref=cast(Path, args.maker_identity_ref),
                checker_identity_ref=cast(Path, args.checker_identity_ref),
            )
            result = verify_review_record(
                verification_paths,
                cast(Path, args.review_record_file),
            )
    except TrustedLocalUseScopeReviewQuarantineRequired:
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
    "TrustedLocalUsePlanArtifactPaths",
    "TrustedLocalUseScopeReviewRequestPaths",
    "TrustedLocalUseScopeReviewInstructionPaths",
    "TrustedLocalUseScopeReviewVerificationPaths",
    "UseScopeReviewRequestPreflightV27",
    "UseScopeReviewInstructionPreflightV27",
    "TrustedLocalUseScopeReviewFinalizationError",
    "TrustedLocalUseScopeReviewQuarantineRequired",
    "preflight_review_request",
    "preflight_review_instruction",
    "finalize_review_record",
    "verify_review_record",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
