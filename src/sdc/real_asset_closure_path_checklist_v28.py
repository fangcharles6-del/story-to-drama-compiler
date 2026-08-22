"""Render one inert, human-only checklist for a fixed trusted-local v2.7 path closure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Final, Literal, Never, cast

from pydantic import ValidationError

from sdc import real_asset_rights_manifest_finalizer_v25 as _path_boundary
from sdc.real_asset_intake import (
    INTAKE_PACK_NAME,
    CreativeSampleFrozenRealAssetPackManifest,
)
from sdc.real_asset_media import SafeLocalFile, read_safe_local_file

_SEED_MAX_BYTES: Final = 64 * 1024
_MANIFEST_MAX_BYTES: Final = 1024 * 1024
_SEED_SCHEMA_VERSION: Final = "1.0.0"
_SEED_DOCUMENT_TYPE: Final = "sdc.trusted-local-closure-path-checklist-seed"
_OUTPUT_SCHEMA_VERSION: Final = "1.0.0"
_OUTPUT_DOCUMENT_TYPE: Final = "sdc.trusted-local-closure-path-checklist"
_GENERATOR_VERSION: Final = "v2.8"
_TARGET_FINALIZER_VERSION: Final = "v2.7"
_STATUS: Final = "PATH_CHECKLIST_READY_FOR_HUMAN_REVIEW_ONLY"
_USAGE_RESTRICTION: Final = "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"

ChecklistProfile = Literal[
    "USE_PLAN_29",
    "REVIEW_REQUEST_32",
    "REVIEW_INSTRUCTION_34",
    "REVIEW_RECORD_VERIFICATION_33",
]
PathSource = Literal["EXPLICIT", "MANIFEST_DERIVED"]
PathKind = Literal["DIRECTORY", "FILE"]


class TrustedLocalClosurePathChecklistError(RuntimeError):
    """One checklist seed or its explicitly named local path set failed closed."""


class _CliArgumentError(RuntimeError):
    pass


class _FailClosedArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("add_help", False)
        kwargs.setdefault("allow_abbrev", False)
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
class ClosurePathChecklistEntryV28:
    """One display-only mapping from a v2.7 CLI path argument to an admitted path."""

    ordinal: int
    argument_name: str
    occurrence: int
    path: str
    source: PathSource

    def payload(self) -> dict[str, object]:
        return {
            "argument_name": self.argument_name,
            "occurrence": self.occurrence,
            "ordinal": self.ordinal,
            "path": self.path,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class TrustedLocalClosurePathChecklistV28:
    """A deterministic, inert checklist that no finalizer accepts as execution input."""

    profile: ChecklistProfile
    target_finalizer_module: str
    target_finalizer_version: Literal["v2.7"]
    target_command: str
    entries: tuple[ClosurePathChecklistEntryV28, ...]
    path_list_sha256: str
    path_format: Literal["WINDOWS_BACKSLASH", "POSIX_SLASH"]

    def payload(self) -> dict[str, object]:
        return {
            "automated_execution_allowed": False,
            "current_gate": "HUMAN_GATE",
            "document_type": _OUTPUT_DOCUMENT_TYPE,
            "entries": [entry.payload() for entry in self.entries],
            "entry_count": len(self.entries),
            "execution_authorized": False,
            "generator_version": _GENERATOR_VERSION,
            "manual_confirmation_required": True,
            "path_format": self.path_format,
            "path_list_sha256": self.path_list_sha256,
            "posts_allowed": 0,
            "profile": self.profile,
            "provider_requests": 0,
            "provider_state": "NOT_AUTHORIZED",
            "schema_version": _OUTPUT_SCHEMA_VERSION,
            "status": _STATUS,
            "target_command": self.target_command,
            "target_finalizer_module": self.target_finalizer_module,
            "target_finalizer_version": self.target_finalizer_version,
            "usage_restriction": _USAGE_RESTRICTION,
        }


@dataclass(frozen=True, slots=True)
class _ProfileSpec:
    profile: ChecklistProfile
    target_module: str
    commands: tuple[str, ...]
    explicit_arguments: tuple[str, ...]
    expected_count: int


@dataclass(frozen=True, slots=True)
class _Seed:
    profile: ChecklistProfile
    target_finalizer_module: str
    target_finalizer_version: str
    target_command: str
    explicit_paths: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class _AdmittedEntry:
    argument_name: str
    occurrence: int
    path: Path
    source: PathSource


@dataclass(frozen=True, slots=True)
class _PathSeal:
    path: Path
    kind: PathKind
    identity: tuple[int, int, int, int]
    link_count: int


_COMMON_EXPLICIT_ARGUMENTS: Final = (
    "--pack-root",
    "--evidence",
    "--reviewer-a",
    "--reviewer-b",
    "--pair-check",
    "--evidence-retained-record",
    "--evidence-preparer-ref",
    "--reviewer-a-retained-record",
    "--reviewer-b-retained-record",
    "--qualification-request",
    "--qualifier-ref",
    "--qualification-instruction",
    "--qualification-decision",
    "--rights-manifest-file",
)
_REQUEST_ADDITIONS: Final = (
    "--use-plan-file",
    "--maker-identity-ref",
    "--maker-input",
)
_INSTRUCTION_ADDITIONS: Final = (
    *_REQUEST_ADDITIONS,
    "--checker-identity-ref",
    "--checker-input",
)
_VERIFICATION_ADDITIONS: Final = (
    "--use-plan-file",
    "--maker-identity-ref",
    "--checker-identity-ref",
    "--review-record-file",
)

_PROFILE_SPECS: Final[Mapping[str, _ProfileSpec]] = MappingProxyType(
    {
        "USE_PLAN_29": _ProfileSpec(
            profile="USE_PLAN_29",
            target_module="sdc.real_asset_use_plan_finalizer_v27",
            commands=("inspect-use-plan-ready", "finalize-use-plan"),
            explicit_arguments=_COMMON_EXPLICIT_ARGUMENTS,
            expected_count=29,
        ),
        "REVIEW_REQUEST_32": _ProfileSpec(
            profile="REVIEW_REQUEST_32",
            target_module="sdc.real_asset_use_scope_review_finalizer_v27",
            commands=("preflight-review-request",),
            explicit_arguments=(*_COMMON_EXPLICIT_ARGUMENTS, *_REQUEST_ADDITIONS),
            expected_count=32,
        ),
        "REVIEW_INSTRUCTION_34": _ProfileSpec(
            profile="REVIEW_INSTRUCTION_34",
            target_module="sdc.real_asset_use_scope_review_finalizer_v27",
            commands=("preflight-review-instruction", "finalize-review-record"),
            explicit_arguments=(*_COMMON_EXPLICIT_ARGUMENTS, *_INSTRUCTION_ADDITIONS),
            expected_count=34,
        ),
        "REVIEW_RECORD_VERIFICATION_33": _ProfileSpec(
            profile="REVIEW_RECORD_VERIFICATION_33",
            target_module="sdc.real_asset_use_scope_review_finalizer_v27",
            commands=("verify-review-record",),
            explicit_arguments=(*_COMMON_EXPLICIT_ARGUMENTS, *_VERIFICATION_ADDITIONS),
            expected_count=33,
        ),
    }
)


def _canonical_json(value: object, *, compact: bool) -> bytes:
    if compact:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    else:
        rendered = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    return (rendered + "\n").encode("utf-8")


def _reject_json_constant(value: str) -> Never:
    del value
    raise ValueError("non-finite JSON constants are forbidden")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, member in pairs:
        if key in value:
            raise ValueError("duplicate JSON member")
        value[key] = member
    return value


def _strict_json_object(raw: bytes, *, field: str) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise TrustedLocalClosurePathChecklistError(f"{field} must not contain a UTF-8 BOM")
    try:
        decoded = raw.decode("utf-8")
        parsed = cast(
            object,
            json.loads(
                decoded,
                object_pairs_hook=_unique_json_object,
                parse_constant=_reject_json_constant,
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise TrustedLocalClosurePathChecklistError(
            f"{field} must contain strict UTF-8 JSON"
        ) from exc
    if type(parsed) is not dict:
        raise TrustedLocalClosurePathChecklistError(f"{field} must contain one JSON object")
    return cast(dict[str, object], parsed)


def _read_bounded_file(path: Path, *, maximum_bytes: int, field: str) -> SafeLocalFile:
    try:
        admitted = _path_boundary._safe_absolute(path, must_exist=True, field=field)
        return read_safe_local_file(admitted, max_bytes=maximum_bytes)
    except Exception as exc:
        raise TrustedLocalClosurePathChecklistError(
            f"{field} is not one stable bounded local file"
        ) from exc


def _parse_seed(source: SafeLocalFile) -> _Seed:
    value = _strict_json_object(source.data, field="checklist seed")
    expected_members = {
        "document_type",
        "explicit_paths",
        "profile",
        "schema_version",
        "target_command",
        "target_finalizer_module",
        "target_finalizer_version",
    }
    if set(value) != expected_members:
        raise TrustedLocalClosurePathChecklistError(
            "checklist seed must contain its exact fixed member set"
        )
    if value["schema_version"] != _SEED_SCHEMA_VERSION:
        raise TrustedLocalClosurePathChecklistError("checklist seed version is unsupported")
    if value["document_type"] != _SEED_DOCUMENT_TYPE:
        raise TrustedLocalClosurePathChecklistError("checklist seed document type is unsupported")
    profile_value = value["profile"]
    if type(profile_value) is not str or profile_value not in _PROFILE_SPECS:
        raise TrustedLocalClosurePathChecklistError("checklist profile is unsupported")
    spec = _PROFILE_SPECS[profile_value]
    module_value = value["target_finalizer_module"]
    version_value = value["target_finalizer_version"]
    command_value = value["target_command"]
    if module_value != spec.target_module:
        raise TrustedLocalClosurePathChecklistError(
            "checklist target finalizer module does not match its fixed profile"
        )
    if version_value != _TARGET_FINALIZER_VERSION:
        raise TrustedLocalClosurePathChecklistError(
            "checklist target finalizer version is unsupported"
        )
    if type(command_value) is not str or command_value not in spec.commands:
        raise TrustedLocalClosurePathChecklistError(
            "checklist target command does not match its fixed profile"
        )
    explicit_value = value["explicit_paths"]
    if type(explicit_value) is not dict:
        raise TrustedLocalClosurePathChecklistError(
            "checklist explicit_paths must contain one JSON object"
        )
    explicit_object = cast(dict[object, object], explicit_value)
    if set(explicit_object) != set(spec.explicit_arguments):
        raise TrustedLocalClosurePathChecklistError(
            "checklist explicit_paths does not match its fixed profile"
        )
    explicit_paths: dict[str, str] = {}
    for argument in spec.explicit_arguments:
        member = explicit_object[argument]
        if type(member) is not str or not member:
            raise TrustedLocalClosurePathChecklistError(
                "every checklist explicit path must be one non-empty string"
            )
        explicit_paths[argument] = member
    return _Seed(
        profile=spec.profile,
        target_finalizer_module=module_value,
        target_finalizer_version=version_value,
        target_command=command_value,
        explicit_paths=MappingProxyType(explicit_paths),
    )


def _stat_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _safe_metadata_open(path: Path) -> int:
    flags = os.O_RDONLY
    if sys.platform == "win32":
        flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    else:
        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_CLOEXEC"):
            raise TrustedLocalClosurePathChecklistError(
                "POSIX no-follow metadata primitives are unavailable"
            )
        flags |= os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        return os.open(path, flags)
    except OSError as exc:
        raise TrustedLocalClosurePathChecklistError(
            "checklist source could not be opened for metadata verification"
        ) from exc


def _regular_file_seal(path: Path, *, field: str) -> _PathSeal:
    descriptor: int | None = None
    try:
        admitted = _path_boundary._safe_absolute(path, must_exist=True, field=field)
        before = admitted.lstat()
        descriptor = _safe_metadata_open(admitted)
        opened = os.fstat(descriptor)
        after = admitted.lstat()
    except Exception as exc:
        raise TrustedLocalClosurePathChecklistError(
            f"{field} is not an admitted local file"
        ) from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                raise TrustedLocalClosurePathChecklistError(
                    f"{field} metadata handle could not be closed"
                ) from exc
    before_attributes = int(getattr(before, "st_file_attributes", 0))
    after_attributes = int(getattr(after, "st_file_attributes", 0))
    if (
        not stat.S_ISREG(before.st_mode)
        or not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or stat.S_ISLNK(after.st_mode)
        or bool(before_attributes & 0x400)
        or bool(after_attributes & 0x400)
        or before.st_nlink != 1
        or opened.st_nlink != 1
        or after.st_nlink != 1
        or before.st_size <= 0
        or _stat_identity(before) != _stat_identity(opened)
        or _stat_identity(opened) != _stat_identity(after)
    ):
        raise TrustedLocalClosurePathChecklistError(
            f"{field} must be one non-empty, single-link ordinary file"
        )
    return _PathSeal(
        path=admitted,
        kind="FILE",
        identity=_stat_identity(opened),
        link_count=opened.st_nlink,
    )


def _directory_seal(path: Path, *, field: str) -> _PathSeal:
    try:
        admitted = _path_boundary._safe_absolute(path, must_exist=True, field=field)
        identity = _path_boundary._directory_identity(admitted, field=field)
    except Exception as exc:
        raise TrustedLocalClosurePathChecklistError(
            f"{field} is not one admitted local directory"
        ) from exc
    return _PathSeal(path=admitted, kind="DIRECTORY", identity=identity, link_count=1)


def _parse_manifest(source: SafeLocalFile) -> CreativeSampleFrozenRealAssetPackManifest:
    _strict_json_object(source.data, field="frozen Pack manifest")
    try:
        manifest = CreativeSampleFrozenRealAssetPackManifest.model_validate_json(
            source.data,
            strict=True,
        )
    except ValidationError as exc:
        raise TrustedLocalClosurePathChecklistError(
            "frozen Pack manifest violates its strict contract"
        ) from exc
    canonical = _canonical_json(manifest.model_dump(mode="json"), compact=False)
    if source.data != canonical:
        raise TrustedLocalClosurePathChecklistError("frozen Pack manifest bytes are not canonical")
    return manifest


def _same_or_nested(left: Path, right: Path) -> bool:
    left_parts = tuple(part.casefold() for part in left.parts)
    right_parts = tuple(part.casefold() for part in right.parts)
    shorter = min(len(left_parts), len(right_parts))
    return left_parts[:shorter] == right_parts[:shorter]


def _normalize_rendered_path(rendered: str, *, anchor: str, windows: bool) -> str:
    if not rendered:
        raise TrustedLocalClosurePathChecklistError("an admitted path rendered empty")
    if windows:
        rendered = rendered.replace("/", "\\")
        anchor = anchor.replace("/", "\\")
        if rendered != anchor:
            rendered = rendered.rstrip("\\")
    elif rendered != anchor:
        rendered = rendered.rstrip("/")
    return rendered


def _render_admitted_path(path: Path, *, windows: bool) -> str:
    return _normalize_rendered_path(str(path), anchor=path.anchor, windows=windows)


def _assert_separate_parent(
    parent: Path,
    trust_areas: tuple[Path, ...],
    *,
    field: str,
) -> None:
    if any(_same_or_nested(parent, area) for area in trust_areas):
        raise TrustedLocalClosurePathChecklistError(
            f"{field} must use a separate non-intersecting trust area"
        )
    parent_identity = _directory_seal(parent, field=field).identity[:2]
    for area in trust_areas:
        if _directory_seal(area, field="source trust area").identity[:2] == parent_identity:
            raise TrustedLocalClosurePathChecklistError(
                f"{field} physically aliases a source trust area"
            )


def _assert_v27_trust_area_separation(
    seed: _Seed,
    admitted_by_argument: Mapping[str, Path],
) -> None:
    pack_root = admitted_by_argument["--pack-root"]
    request_external_parents = tuple(
        admitted_by_argument[argument].parent for argument in _COMMON_EXPLICIT_ARGUMENTS[1:9]
    )
    request_parent = admitted_by_argument["--qualification-request"].parent
    qualifier_parent = admitted_by_argument["--qualifier-ref"].parent
    instruction_parent = admitted_by_argument["--qualification-instruction"].parent
    decision_parent = admitted_by_argument["--qualification-decision"].parent
    rights_manifest_parent = admitted_by_argument["--rights-manifest-file"].parent

    request_areas = (pack_root, *request_external_parents)
    _assert_separate_parent(request_parent, request_areas, field="Request parent")
    decision_areas = (
        *request_areas,
        request_parent,
        qualifier_parent,
        instruction_parent,
    )
    _assert_separate_parent(decision_parent, decision_areas, field="Decision parent")
    manifest_areas = (*decision_areas, decision_parent)
    _assert_separate_parent(
        rights_manifest_parent,
        manifest_areas,
        field="Rights Manifest parent",
    )

    if "--use-plan-file" not in admitted_by_argument:
        return
    use_plan_parent = admitted_by_argument["--use-plan-file"].parent
    use_plan_areas = (*manifest_areas, rights_manifest_parent)
    _assert_separate_parent(use_plan_parent, use_plan_areas, field="Use Plan parent")

    review_areas = [*use_plan_areas, use_plan_parent]
    if seed.profile in {"REVIEW_REQUEST_32", "REVIEW_INSTRUCTION_34"}:
        additions = ["--maker-identity-ref", "--maker-input"]
        if seed.profile == "REVIEW_INSTRUCTION_34":
            additions.extend(("--checker-identity-ref", "--checker-input"))
    else:
        additions = [
            "--maker-identity-ref",
            "--checker-identity-ref",
            "--review-record-file",
        ]
    for argument in additions:
        parent = admitted_by_argument[argument].parent
        _assert_separate_parent(parent, tuple(review_areas), field=f"{argument} parent")
        review_areas.append(parent)


def _materialize_entries(
    seed: _Seed,
) -> tuple[
    tuple[_AdmittedEntry, ...],
    tuple[_PathSeal, ...],
    SafeLocalFile,
    CreativeSampleFrozenRealAssetPackManifest,
]:
    spec = _PROFILE_SPECS[seed.profile]
    pack_root_seal = _directory_seal(
        Path(seed.explicit_paths["--pack-root"]),
        field="frozen Pack root",
    )
    pack_root = pack_root_seal.path
    manifest_path = pack_root / INTAKE_PACK_NAME
    manifest_source = _read_bounded_file(
        manifest_path,
        maximum_bytes=_MANIFEST_MAX_BYTES,
        field="frozen Pack manifest",
    )
    manifest = _parse_manifest(manifest_source)
    if pack_root.name != manifest.pack_id:
        raise TrustedLocalClosurePathChecklistError(
            "frozen Pack root name does not match its manifest ID"
        )

    admitted: list[_AdmittedEntry] = [
        _AdmittedEntry("--pack-root", 0, pack_root, "EXPLICIT"),
        _AdmittedEntry("--pack-manifest", 0, manifest_source.path, "MANIFEST_DERIVED"),
    ]
    seals: list[_PathSeal] = [
        pack_root_seal,
        _regular_file_seal(manifest_source.path, field="frozen Pack manifest"),
    ]
    for occurrence, descriptor in enumerate(manifest.objects):
        relative = PurePosixPath(descriptor.object_path)
        media_path = pack_root.joinpath(*relative.parts)
        media_seal = _regular_file_seal(media_path, field=f"frozen media {occurrence}")
        if not media_seal.path.is_relative_to(pack_root):
            raise TrustedLocalClosurePathChecklistError(
                "derived frozen media path escaped the explicit Pack root"
            )
        if media_seal.identity[2] != descriptor.size_bytes:
            raise TrustedLocalClosurePathChecklistError(
                "derived frozen media size disagrees with the Pack manifest"
            )
        admitted.append(
            _AdmittedEntry("--media-path", occurrence, media_seal.path, "MANIFEST_DERIVED")
        )
        seals.append(media_seal)

    for argument in spec.explicit_arguments:
        if argument == "--pack-root":
            continue
        file_seal = _regular_file_seal(Path(seed.explicit_paths[argument]), field=argument)
        if _same_or_nested(pack_root, file_seal.path):
            raise TrustedLocalClosurePathChecklistError(
                "an explicit external checklist path overlaps the frozen Pack"
            )
        admitted.append(_AdmittedEntry(argument, 0, file_seal.path, "EXPLICIT"))
        seals.append(file_seal)

    if len(admitted) != spec.expected_count or len(seals) != spec.expected_count:
        raise TrustedLocalClosurePathChecklistError(
            "materialized checklist count does not match its fixed profile"
        )
    rendered_keys = tuple(entry.path.as_posix().casefold() for entry in admitted)
    if len(set(rendered_keys)) != len(rendered_keys):
        raise TrustedLocalClosurePathChecklistError("materialized checklist contains a path alias")
    file_identities = tuple(seal.identity[:2] for seal in seals if seal.kind == "FILE")
    if len(set(file_identities)) != len(file_identities):
        raise TrustedLocalClosurePathChecklistError(
            "materialized checklist contains a physical file alias"
        )
    admitted_by_argument = {
        entry.argument_name: entry.path
        for entry in admitted
        if entry.argument_name != "--media-path"
    }
    _assert_v27_trust_area_separation(seed, admitted_by_argument)
    return tuple(admitted), tuple(seals), manifest_source, manifest


def _path_list_payload(
    *,
    seed: _Seed,
    entries: tuple[ClosurePathChecklistEntryV28, ...],
) -> dict[str, object]:
    return {
        "entries": [entry.payload() for entry in entries],
        "entry_count": len(entries),
        "profile": seed.profile,
        "target_command": seed.target_command,
        "target_finalizer_module": seed.target_finalizer_module,
        "target_finalizer_version": seed.target_finalizer_version,
    }


def build_closure_path_checklist_v28(seed_path: Path) -> TrustedLocalClosurePathChecklistV28:
    """Build one deterministic human checklist without scanning or writing any directory."""

    try:
        seed_before = _read_bounded_file(
            seed_path,
            maximum_bytes=_SEED_MAX_BYTES,
            field="checklist seed",
        )
        seed = _parse_seed(seed_before)
        admitted, seals_before, manifest_before, parsed_manifest = _materialize_entries(seed)
        windows = os.name == "nt"
        entries = tuple(
            ClosurePathChecklistEntryV28(
                ordinal=ordinal,
                argument_name=entry.argument_name,
                occurrence=entry.occurrence,
                path=_render_admitted_path(entry.path, windows=windows),
                source=entry.source,
            )
            for ordinal, entry in enumerate(admitted)
        )
        digest = hashlib.sha256(
            _canonical_json(_path_list_payload(seed=seed, entries=entries), compact=False)
        ).hexdigest()

        seed_after = _read_bounded_file(
            seed_before.path,
            maximum_bytes=_SEED_MAX_BYTES,
            field="checklist seed",
        )
        manifest_after = _read_bounded_file(
            manifest_before.path,
            maximum_bytes=_MANIFEST_MAX_BYTES,
            field="frozen Pack manifest",
        )
        if seed_after != seed_before or manifest_after != manifest_before:
            raise TrustedLocalClosurePathChecklistError(
                "checklist seed or Pack manifest drifted during rendering"
            )
        if _parse_manifest(manifest_after) != parsed_manifest:
            raise TrustedLocalClosurePathChecklistError(
                "Pack manifest contract drifted during rendering"
            )
        seals_after = tuple(
            _directory_seal(seal.path, field="frozen Pack root")
            if seal.kind == "DIRECTORY"
            else _regular_file_seal(seal.path, field="checklist source")
            for seal in seals_before
        )
        if seals_after != seals_before:
            raise TrustedLocalClosurePathChecklistError(
                "one checklist path identity drifted during rendering"
            )
        admitted_by_argument = {
            entry.argument_name: entry.path
            for entry in admitted
            if entry.argument_name != "--media-path"
        }
        _assert_v27_trust_area_separation(seed, admitted_by_argument)
        if seed_before.identity[:2] in {
            seal.identity[:2] for seal in seals_before if seal.kind == "FILE"
        }:
            raise TrustedLocalClosurePathChecklistError("checklist seed aliases one listed source")
        return TrustedLocalClosurePathChecklistV28(
            profile=seed.profile,
            target_finalizer_module=seed.target_finalizer_module,
            target_finalizer_version="v2.7",
            target_command=seed.target_command,
            entries=entries,
            path_list_sha256=digest,
            path_format="WINDOWS_BACKSLASH" if windows else "POSIX_SLASH",
        )
    except TrustedLocalClosurePathChecklistError:
        raise
    except Exception as exc:
        raise TrustedLocalClosurePathChecklistError(
            "trusted-local closure path checklist failed closed"
        ) from exc


def _write_json_line(stream: object, payload: dict[str, object]) -> None:
    encoded = _canonical_json(payload, compact=True)
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
        description="Render one inert, human-only trusted-local path checklist"
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=_FailClosedArgumentParser,
    )
    render = commands.add_parser("render-checklist")
    render.add_argument("--seed", required=True, type=Path, action=_StoreOnce)
    try:
        args = parser.parse_args(argv)
        if cast(str, args.command) != "render-checklist":
            raise _CliArgumentError
        result = build_closure_path_checklist_v28(cast(Path, args.seed))
    except BaseException:
        _write_json_line(sys.stderr, {"error": "FAILED_CLOSED"})
        return 2
    _write_json_line(sys.stdout, result.payload())
    return 0


__all__ = [
    "ClosurePathChecklistEntryV28",
    "TrustedLocalClosurePathChecklistError",
    "TrustedLocalClosurePathChecklistV28",
    "build_closure_path_checklist_v28",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
