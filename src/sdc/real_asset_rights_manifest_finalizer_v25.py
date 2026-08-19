"""Trusted local finalization of one inert Pack-level Rights Manifest v2.

Every source is an explicitly named absolute local path.  The module never scans for inputs,
reads a clock, infers a qualification outcome, grants authority, or contacts a remote service.
Only ``finalize-manifest`` writes, and it creates one canonical repository-external file once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Never, cast

from pydantic import BaseModel, ValidationError

from sdc.creative_media import CreativeMediaError, validate_local_path
from sdc.real_asset_intake import (
    CreativeSampleFrozenRealAssetPackManifest,
    FrozenRealAssetPack,
    RealAudioTechnicalRecord,
    RealImageTechnicalRecord,
    build_real_asset_intake_template,
)
from sdc.real_asset_media import (
    RealAssetMediaError,
    SafeLocalFile,
    inspect_bgm_wav,
    inspect_png,
    inspect_voice_wav,
    read_safe_local_file,
)
from sdc.real_asset_qualification_decision_finalizer_v22 import TrustedLocalDecisionPaths
from sdc.real_asset_qualification_decision_instruction_v22 import (
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
)
from sdc.real_asset_qualification_preparer_v21 import TrustedLocalRequestPaths
from sdc.real_asset_qualification_v2 import (
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationRequestV2,
    RealAssetQualificationV2Error,
    parse_real_asset_qualification_decision_v2_json,
    parse_real_asset_qualification_request_v2_json,
    verify_real_asset_qualification_closure_v2,
)
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
)
from sdc.real_asset_rights_manifest_v24 import (
    RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetRightsManifestV2,
    RealAssetRightsManifestV24Error,
    build_real_asset_rights_manifest_v2,
    parse_real_asset_rights_manifest_v2_json,
    verify_real_asset_rights_manifest_closure_v2,
)

_PACK_MANIFEST_NAME = "asset-pack.json"
_JSON_MAX_BYTES = 1_048_576
_PRIVATE_RECORD_MAX_BYTES = 1_048_576
_MEDIA_MAX_BYTES = 64 * 1024 * 1024
_MOUNTINFO_MAX_BYTES = 1_048_576
_MUTABLE_ALIAS_TOKENS = frozenset({"current", "latest", "newest"})
_OUTCOME_FILENAME_TOKENS = frozenset({"needs", "pass", "rejected"})
_UTC_SECONDS = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
_READY_FOR_MANIFEST_FINALIZATION: Literal["READY_FOR_MANIFEST_FINALIZATION"] = (
    "READY_FOR_MANIFEST_FINALIZATION"
)


class TrustedLocalRightsManifestFinalizationError(RuntimeError):
    """The trusted local Rights Manifest v2.5 boundary failed closed."""


class TrustedLocalRightsManifestQuarantineRequired(
    TrustedLocalRightsManifestFinalizationError
):
    """Rollback could not prove invalidation or deletion of the exact created file."""


class _CliArgumentError(RuntimeError):
    pass


class _FailClosedArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> Never:
        del message
        raise _CliArgumentError


class _StoreOnce(argparse.Action):
    """Store one singleton option and reject every repeated occurrence."""

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
class TrustedLocalRightsManifestPaths:
    """All twenty-eight explicit path entries needed for one Manifest operation."""

    decision_inputs: TrustedLocalDecisionPaths
    decision: Path


@dataclass(frozen=True, slots=True)
class _FileSeal:
    path: Path
    sha256: str
    size_bytes: int
    identity: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class _ManifestSnapshot:
    pack: FrozenRealAssetPack
    pack_root_identity: tuple[int, int, int, int]
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2
    pair_check: CreativeSampleRealAssetReviewPairCheckV2
    request: CreativeSampleRealAssetQualificationRequestV2
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22
    decision: CreativeSampleRealAssetQualificationDecisionV2
    files: tuple[_FileSeal, ...]
    manifest: CreativeSampleRealAssetRightsManifestV2 | None = None


@dataclass(frozen=True, slots=True)
class _OutputTarget:
    path: Path
    parent: Path
    parent_physical_identity: tuple[int, int]


@dataclass(slots=True)
class _CreatedManifest:
    target: _OutputTarget
    descriptor: int
    parent_guard: int
    windows_parent_guard: bool
    seal: _FileSeal | None = None
    closed: bool = False


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


def _parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _canonical_utc_seconds(value: str, *, field: str) -> str:
    if _UTC_SECONDS.fullmatch(value) is None:
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} must be canonical UTC seconds"
        )
    try:
        parsed = _parse_utc(value)
    except ValueError as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} must be a valid UTC timestamp"
        ) from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} must be canonical UTC seconds"
        )
    return value


def _reject_json_constant(value: str) -> None:
    del value
    raise TrustedLocalRightsManifestFinalizationError(
        "non-finite JSON numbers are forbidden"
    )


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TrustedLocalRightsManifestFinalizationError(
                "duplicate JSON key is forbidden"
            )
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
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} is not bounded canonical JSON"
        )
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} is not strict UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} must contain one JSON object"
        )
    try:
        parsed = model.model_validate_json(raw, strict=True)
    except ValidationError as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} violates its strict contract"
        ) from exc
    if raw != _canonical_document(parsed):
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} bytes are not canonical"
        )
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
            raise TrustedLocalRightsManifestFinalizationError(
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
            raise TrustedLocalRightsManifestFinalizationError(
                f"{field} cannot use a mutable alias path"
            )


def _reject_outcome_filename(path: Path, *, field: str) -> None:
    tokens = frozenset(filter(None, re.split(r"[^a-z0-9]+", path.stem.casefold())))
    if tokens & _OUTCOME_FILENAME_TOKENS:
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} filename must not disclose a qualification outcome"
        )


def _is_mount_component(path: Path) -> bool:
    """Return whether one existing path component is a filesystem mount point."""

    return os.path.ismount(path)


def _linux_mount_points() -> frozenset[str]:
    """Read Linux mount points once, bounded, so bind mounts are not missed."""

    if not sys.platform.startswith("linux"):
        return frozenset()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open("/proc/self/mountinfo", flags)
        observed = bytearray()
        while len(observed) <= _MOUNTINFO_MAX_BYTES:
            chunk = os.read(
                descriptor,
                min(65_536, _MOUNTINFO_MAX_BYTES + 1 - len(observed)),
            )
            if not chunk:
                break
            observed.extend(chunk)
    except OSError as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            "Linux mount isolation could not be inspected"
        ) from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                raise TrustedLocalRightsManifestFinalizationError(
                    "Linux mount isolation handle could not be closed"
                ) from exc
    if len(observed) > _MOUNTINFO_MAX_BYTES:
        raise TrustedLocalRightsManifestFinalizationError(
            "Linux mount isolation metadata exceeded its fixed bound"
        )
    try:
        decoded = observed.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            "Linux mount isolation metadata is not UTF-8"
        ) from exc

    def unescape(value: str) -> str:
        return re.sub(
            r"\\([0-7]{3})",
            lambda match: chr(int(match.group(1), 8)),
            value,
        )

    points: set[str] = set()
    for line in decoded.splitlines():
        fields = line.split(" ")
        if len(fields) < 6 or "-" not in fields[6:]:
            raise TrustedLocalRightsManifestFinalizationError(
                "Linux mount isolation metadata is malformed"
            )
        points.add(os.path.normpath(unescape(fields[4])))
    return frozenset(points)


def _reject_non_anchor_mount_components(path: Path, *, field: str) -> None:
    """Reject mounted components without treating the filesystem/drive anchor as input."""

    linux_mount_points = _linux_mount_points()
    cursor = Path(path.anchor)
    components = path.parts[1:] if path.anchor else path.parts
    for component in components:
        cursor /= component
        try:
            cursor.lstat()
            mounted = _is_mount_component(cursor) or (
                os.path.normpath(str(cursor)) in linux_mount_points
            )
        except FileNotFoundError:
            break
        except OSError as exc:
            raise TrustedLocalRightsManifestFinalizationError(
                f"{field} mount isolation could not be checked"
            ) from exc
        if mounted:
            raise TrustedLocalRightsManifestFinalizationError(
                f"{field} must not traverse a mounted path component"
            )


def _safe_absolute(path: Path, *, must_exist: bool, field: str) -> Path:
    if not path.is_absolute():
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} must be an absolute local path"
        )
    _reject_mutable_alias_path(path, field=field)
    try:
        absolute = validate_local_path(path, must_exist=must_exist)
        if not must_exist:
            validate_local_path(absolute.parent, must_exist=True)
    except (CreativeMediaError, OSError) as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} is not a safe local path"
        ) from exc
    _reject_non_anchor_mount_components(absolute, field=field)
    _reject_mutable_alias_path(absolute, field=field)
    if _nearest_git_root(absolute) is not None:
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} must remain outside every Git tree, including output and tmp"
        )
    return absolute


def _read_safe(path: Path, *, max_bytes: int, field: str) -> SafeLocalFile:
    absolute = _safe_absolute(path, must_exist=True, field=field)
    try:
        return read_safe_local_file(absolute, max_bytes=max_bytes)
    except RealAssetMediaError as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} must be one stable non-linked local file"
        ) from exc


def _directory_identity(path: Path, *, field: str) -> tuple[int, int, int, int]:
    _reject_non_anchor_mount_components(path, field=field)
    try:
        info = path.lstat()
    except OSError as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} could not be inspected"
        ) from exc
    attributes = int(getattr(info, "st_file_attributes", 0))
    is_junction = getattr(path, "is_junction", None)
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_ISLNK(info.st_mode)
        or bool(attributes & 0x400)
        or bool(is_junction is not None and is_junction())
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} must be one non-linked directory"
        )
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _paths_overlap(left: Path, right: Path) -> bool:
    left_parts = tuple(part.casefold() for part in left.parts)
    right_parts = tuple(part.casefold() for part in right.parts)
    shorter = min(len(left_parts), len(right_parts))
    return left_parts[:shorter] == right_parts[:shorter]


def _all_source_paths(paths: TrustedLocalRightsManifestPaths) -> tuple[Path, ...]:
    request = paths.decision_inputs.request_inputs
    return (
        request.pack_manifest,
        *request.media_paths,
        request.evidence_bundle,
        request.reviewer_a,
        request.reviewer_b,
        request.pair_check,
        request.evidence_retained_record,
        request.evidence_preparer_ref,
        request.reviewer_a_retained_record,
        request.reviewer_b_retained_record,
        paths.decision_inputs.request,
        paths.decision_inputs.qualifier_ref,
        paths.decision_inputs.qualifier_decision_record,
        paths.decision,
    )


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


def _assert_separate_trust_parent(
    parent: Path,
    trust_areas: tuple[Path, ...],
    *,
    field: str,
) -> None:
    if any(_paths_overlap(parent, area) for area in trust_areas):
        raise TrustedLocalRightsManifestFinalizationError(
            f"{field} must use a separate non-intersecting trust area"
        )
    parent_identity = _directory_identity(parent, field=field)[:2]
    for area in trust_areas:
        if _directory_identity(area, field="source trust area")[:2] == parent_identity:
            raise TrustedLocalRightsManifestFinalizationError(
                f"{field} physically aliases a source trust area"
            )


def _normalize_paths(
    paths: TrustedLocalRightsManifestPaths,
) -> TrustedLocalRightsManifestPaths:
    supplied_request = paths.decision_inputs.request_inputs
    pack_root = _safe_absolute(
        supplied_request.pack_root,
        must_exist=True,
        field="frozen Pack root",
    )
    if not pack_root.is_dir():
        raise TrustedLocalRightsManifestFinalizationError(
            "frozen Pack root must be a directory"
        )
    pack_manifest = _safe_absolute(
        supplied_request.pack_manifest,
        must_exist=True,
        field="frozen Pack manifest",
    )
    if pack_manifest != pack_root / _PACK_MANIFEST_NAME:
        raise TrustedLocalRightsManifestFinalizationError(
            "frozen Pack manifest must be exact under the supplied Pack root"
        )
    if len(supplied_request.media_paths) != 14:
        raise TrustedLocalRightsManifestFinalizationError(
            "exactly fourteen explicit media paths are required"
        )
    media_paths = tuple(
        _safe_absolute(path, must_exist=True, field=f"frozen media {ordinal}")
        for ordinal, path in enumerate(supplied_request.media_paths)
    )
    external = tuple(
        _safe_absolute(path, must_exist=True, field=field)
        for path, field in (
            (supplied_request.evidence_bundle, "Evidence Bundle"),
            (supplied_request.reviewer_a, "Reviewer A contract"),
            (supplied_request.reviewer_b, "Reviewer B contract"),
            (supplied_request.pair_check, "PairCheck contract"),
            (supplied_request.evidence_retained_record, "evidence retained record"),
            (supplied_request.evidence_preparer_ref, "evidence preparer reference"),
            (supplied_request.reviewer_a_retained_record, "Reviewer A retained record"),
            (supplied_request.reviewer_b_retained_record, "Reviewer B retained record"),
        )
    )
    request_inputs = TrustedLocalRequestPaths(
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
    decision_inputs = TrustedLocalDecisionPaths(
        request_inputs=request_inputs,
        request=_safe_absolute(
            paths.decision_inputs.request,
            must_exist=True,
            field="qualification request",
        ),
        qualifier_ref=_safe_absolute(
            paths.decision_inputs.qualifier_ref,
            must_exist=True,
            field="Qualifier reference",
        ),
        qualifier_decision_record=_safe_absolute(
            paths.decision_inputs.qualifier_decision_record,
            must_exist=True,
            field="qualification instruction",
        ),
    )
    _reject_outcome_filename(
        decision_inputs.qualifier_decision_record,
        field="qualification instruction",
    )
    normalized = TrustedLocalRightsManifestPaths(
        decision_inputs=decision_inputs,
        decision=_safe_absolute(
            paths.decision,
            must_exist=True,
            field="qualification decision",
        ),
    )
    _reject_outcome_filename(normalized.decision, field="qualification decision")
    for path in (
        *external,
        decision_inputs.request,
        decision_inputs.qualifier_ref,
        decision_inputs.qualifier_decision_record,
        normalized.decision,
    ):
        if _paths_overlap(path, pack_root):
            raise TrustedLocalRightsManifestFinalizationError(
                "external contracts and records must remain outside the frozen Pack"
            )
    named = _all_source_paths(normalized)
    if (
        len(named) != 27
        or len(set(named)) != 27
        or len({path.as_posix().casefold() for path in named}) != 27
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "all twenty-seven explicitly named files must be distinct"
        )
    request_trust_areas = (pack_root, *_request_external_parents(request_inputs))
    _assert_separate_trust_parent(
        decision_inputs.request.parent,
        request_trust_areas,
        field="Request parent",
    )
    decision_trust_areas = (
        *request_trust_areas,
        decision_inputs.request.parent,
        decision_inputs.qualifier_ref.parent,
        decision_inputs.qualifier_decision_record.parent,
    )
    _assert_separate_trust_parent(
        normalized.decision.parent,
        decision_trust_areas,
        field="Decision parent",
    )
    return normalized


def _read_contract[ModelT: BaseModel](
    path: Path,
    model: type[ModelT],
    *,
    field: str,
) -> tuple[ModelT, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field=field)
    return _parse_canonical_json(source, model, field=field), _file_seal(source)


def _read_request(
    path: Path,
) -> tuple[CreativeSampleRealAssetQualificationRequestV2, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field="qualification request")
    try:
        parsed = parse_real_asset_qualification_request_v2_json(source.data)
    except RealAssetQualificationV2Error as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification request violates its strict contract"
        ) from exc
    if source.data != _canonical_document(parsed):
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification request bytes are not canonical"
        )
    return parsed, _file_seal(source)


def _read_decision(
    path: Path,
) -> tuple[CreativeSampleRealAssetQualificationDecisionV2, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field="qualification decision")
    try:
        parsed = parse_real_asset_qualification_decision_v2_json(source.data)
    except RealAssetQualificationV2Error as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification decision violates its strict contract"
        ) from exc
    if source.data != _canonical_document(parsed):
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification decision bytes are not canonical"
        )
    return parsed, _file_seal(source)


def _read_manifest(
    path: Path,
) -> tuple[CreativeSampleRealAssetRightsManifestV2, _FileSeal]:
    source = _read_safe(path, max_bytes=_JSON_MAX_BYTES, field="Rights Manifest")
    try:
        parsed = parse_real_asset_rights_manifest_v2_json(source.data)
    except RealAssetRightsManifestV24Error as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            "Rights Manifest violates its strict contract"
        ) from exc
    if source.data != _canonical_document(parsed):
        raise TrustedLocalRightsManifestFinalizationError(
            "Rights Manifest bytes are not canonical"
        )
    return parsed, _file_seal(source)


def _verify_explicit_pack(
    paths: TrustedLocalRequestPaths,
) -> tuple[FrozenRealAssetPack, tuple[_FileSeal, ...], _FileSeal, tuple[int, int, int, int]]:
    root_before = _directory_identity(paths.pack_root, field="frozen Pack root")
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
    if paths.pack_root.name != manifest.pack_id:
        raise TrustedLocalRightsManifestFinalizationError(
            "frozen Pack root name must equal the immutable Pack ID"
        )
    template = build_real_asset_intake_template()
    if (
        manifest.template_id != template.template_id
        or manifest.pilot_pack_id != template.pilot_pack_id
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "frozen Pack does not bind the exact intake template"
        )
    expected_bindings = tuple(
        (item.requirement_id, item.logical_path, item.kind, item.subject_id)
        for item in template.requirements
    )
    actual_bindings = tuple(
        (item.requirement_id, item.logical_path, item.kind, item.subject_id)
        for item in manifest.objects
    )
    if actual_bindings != expected_bindings:
        raise TrustedLocalRightsManifestFinalizationError(
            "frozen Pack descriptor closure drifted from the template"
        )
    expected_media = tuple(
        paths.pack_root.joinpath(*PurePosixPath(item.object_path).parts)
        for item in manifest.objects
    )
    if paths.media_paths != expected_media:
        raise TrustedLocalRightsManifestFinalizationError(
            "fourteen media paths must match manifest order and location exactly"
        )

    media_seals: list[_FileSeal] = []
    for ordinal, (requirement, descriptor, path) in enumerate(
        zip(template.requirements, manifest.objects, paths.media_paths, strict=True)
    ):
        try:
            if descriptor.kind == "IMAGE":
                source, observed = inspect_png(
                    path,
                    forbidden_sha256=template.forbidden_fixture_sha256,
                )
                observed_image = RealImageTechnicalRecord(**asdict(observed))
                observed_audio = None
            elif descriptor.kind == "VOICE":
                assert requirement.start_ms is not None and requirement.end_ms is not None
                source, observed_audio_raw = inspect_voice_wav(
                    path,
                    maximum_duration_ms=requirement.end_ms - requirement.start_ms,
                )
                observed_image = None
                observed_audio = RealAudioTechnicalRecord(**asdict(observed_audio_raw))
            else:
                source, observed_audio_raw = inspect_bgm_wav(path)
                observed_image = None
                observed_audio = RealAudioTechnicalRecord(**asdict(observed_audio_raw))
        except (RealAssetMediaError, OSError, ValueError) as exc:
            raise TrustedLocalRightsManifestFinalizationError(
                f"frozen media {ordinal} failed explicit technical verification"
            ) from exc
        if source.path != path:
            raise TrustedLocalRightsManifestFinalizationError(
                f"frozen media {ordinal} resolved to a different path"
            )
        if source.sha256 != descriptor.sha256 or source.size_bytes != descriptor.size_bytes:
            raise TrustedLocalRightsManifestFinalizationError(
                f"frozen media {ordinal} does not match its manifest identity"
            )
        if descriptor.image != observed_image or descriptor.audio != observed_audio:
            raise TrustedLocalRightsManifestFinalizationError(
                f"frozen media {ordinal} technical evidence did not reproduce"
            )
        media_seals.append(_file_seal(source))
    root_after = _directory_identity(paths.pack_root, field="frozen Pack root")
    if root_before != root_after:
        raise TrustedLocalRightsManifestFinalizationError(
            "frozen Pack root drifted during explicit verification"
        )
    return (
        FrozenRealAssetPack(
            root=paths.pack_root,
            manifest_path=paths.pack_manifest,
            manifest=manifest,
            created=False,
        ),
        tuple(media_seals),
        _file_seal(manifest_source),
        root_before,
    )


def _assert_non_aliasing(files: tuple[_FileSeal, ...]) -> None:
    if len({item.path for item in files}) != len(files) or len(
        {item.path.as_posix().casefold() for item in files}
    ) != len(files):
        raise TrustedLocalRightsManifestFinalizationError(
            "local inputs contain a path alias"
        )
    if len({(item.identity[0], item.identity[1]) for item in files}) != len(files):
        raise TrustedLocalRightsManifestFinalizationError(
            "local inputs contain a physical file alias"
        )
    if len({item.sha256 for item in files}) != len(files):
        raise TrustedLocalRightsManifestFinalizationError(
            "local inputs contain a byte digest alias"
        )


def _verify_instruction_binding(snapshot: _ManifestSnapshot) -> None:
    request = snapshot.request
    instruction = snapshot.instruction
    decision = snapshot.decision
    instruction_sha256 = _sha256(_canonical_document(instruction))
    if instruction_sha256 != decision.qualifier_record_sha256:
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification decision does not bind the canonical instruction"
        )
    if (
        instruction.request_id != request.request_id
        or instruction.request_sha256 != _sha256(_canonical_document(request))
        or instruction.policy_id != request.policy_id
        or instruction.policy_version != request.policy_version
        or instruction.policy_document_sha256 != request.policy_document_sha256
        or instruction.qualification_scope != decision.qualification_scope
        or instruction.qualifier_ref_sha256 != decision.qualifier_ref_sha256
        or instruction.decision_at != decision.decision_at
        or instruction.decision != decision.decision
        or instruction.qualification_issue_codes != decision.qualification_issue_codes
        or instruction.qualification_basis != decision.qualification_basis
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification instruction does not bind the exact Request and Decision"
        )


def _verify_qualification_closure(snapshot: _ManifestSnapshot) -> None:
    _verify_instruction_binding(snapshot)
    try:
        verified = verify_real_asset_qualification_closure_v2(
            pack=snapshot.pack.manifest,
            evidence=snapshot.evidence,
            reviewer_a=snapshot.reviewer_a,
            reviewer_b=snapshot.reviewer_b,
            pair_check=snapshot.pair_check,
            request=snapshot.request,
            decision=snapshot.decision,
        )
    except (RealAssetQualificationV2Error, ValidationError, ValueError) as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification closure failed exact historical reconstruction"
        ) from exc
    if verified != snapshot.decision:
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification verifier returned a different Decision"
        )


def _assert_manifest_policy_ready(snapshot: _ManifestSnapshot, *, manifest_at: str) -> None:
    manifest_at = _canonical_utc_seconds(manifest_at, field="manifest_at")
    decision = snapshot.decision
    if (
        decision.decision != "PASS_ASSET_INTAKE_ONLY"
        or decision.qualification_scope != "ASSET_INTAKE_ONLY"
        or decision.status != "QUALIFICATION_COMPLETE"
        or decision.rights_qualification_performed is not True
        or decision.eligible_for_separate_manifest_design_review is not True
        or decision.rights_manifest_created is not False
        or decision.current_gate != "HUMAN_GATE"
        or decision.provider_state != "NOT_AUTHORIZED"
        or decision.eligible_for_real_generation is not False
        or decision.execution_authorized is not False
        or decision.posts_allowed != 0
        or decision.provider_requests != 0
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification Decision is not eligible for Manifest finalization"
        )
    if _parse_utc(manifest_at) < _parse_utc(decision.decision_at):
        raise TrustedLocalRightsManifestFinalizationError(
            "manifest_at cannot predate the qualification Decision"
        )
    if (
        snapshot.evidence.valid_until != "PERPETUAL"
        and _parse_utc(manifest_at) >= _parse_utc(snapshot.evidence.valid_until)
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "Rights Evidence is not valid at manifest_at"
        )

    pack = snapshot.pack.manifest
    contract_digests = {
        _sha256(_canonical_document(pack)),
        _sha256(_canonical_document(snapshot.evidence)),
        _sha256(_canonical_document(snapshot.reviewer_a)),
        _sha256(_canonical_document(snapshot.reviewer_b)),
        _sha256(_canonical_document(snapshot.pair_check)),
        _sha256(_canonical_document(snapshot.request)),
        _sha256(_canonical_document(snapshot.instruction)),
        _sha256(_canonical_document(decision)),
        decision.policy_document_sha256,
        RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256,
        snapshot.request.review_a_record_sha256,
        snapshot.request.review_b_record_sha256,
    }
    if len(contract_digests) != 12:
        raise TrustedLocalRightsManifestFinalizationError(
            "Manifest contract and review-record digests must be distinct"
        )
    retained_digests = {
        decision.evidence_retained_record_sha256,
        decision.evidence_preparer_ref_sha256,
        decision.reviewer_a_retained_record_sha256,
        decision.reviewer_b_retained_record_sha256,
        decision.qualifier_ref_sha256,
    }
    if len(retained_digests) != 5 or retained_digests & contract_digests:
        raise TrustedLocalRightsManifestFinalizationError(
            "Manifest retained records must be distinct and non-aliasing"
        )
    pack_record_sequence = tuple(
        digest
        for descriptor in pack.objects
        for digest in (
            descriptor.sha256,
            descriptor.provenance_record_sha256,
            descriptor.technical_record_sha256,
        )
    )
    pack_record_digests = set(pack_record_sequence)
    if len(pack_record_sequence) != 42 or len(pack_record_digests) != 42:
        raise TrustedLocalRightsManifestFinalizationError(
            "Pack media, provenance, and technical digests must be fully distinct"
        )
    if pack_record_digests & (contract_digests | retained_digests):
        raise TrustedLocalRightsManifestFinalizationError(
            "Pack object records alias the Manifest closure"
        )


def _capture_snapshot(
    paths: TrustedLocalRightsManifestPaths,
    *,
    manifest_at: str | None,
    manifest_path: Path | None = None,
) -> _ManifestSnapshot:
    if (manifest_at is None) == (manifest_path is None):
        raise TrustedLocalRightsManifestFinalizationError(
            "exactly one Manifest time source is required"
        )
    request_paths = paths.decision_inputs.request_inputs
    pack, media_seals, pack_manifest_seal, root_identity = _verify_explicit_pack(
        request_paths
    )
    evidence, evidence_seal = _read_contract(
        request_paths.evidence_bundle,
        CreativeSampleRealAssetRightsEvidenceBundleV2,
        field="Evidence Bundle",
    )
    reviewer_a, reviewer_a_seal = _read_contract(
        request_paths.reviewer_a,
        CreativeSampleRealAssetHumanPackReviewV2,
        field="Reviewer A contract",
    )
    reviewer_b, reviewer_b_seal = _read_contract(
        request_paths.reviewer_b,
        CreativeSampleRealAssetHumanPackReviewV2,
        field="Reviewer B contract",
    )
    pair_check, pair_check_seal = _read_contract(
        request_paths.pair_check,
        CreativeSampleRealAssetReviewPairCheckV2,
        field="PairCheck contract",
    )
    if reviewer_a.reviewer_role != "REVIEWER_A" or reviewer_b.reviewer_role != "REVIEWER_B":
        raise TrustedLocalRightsManifestFinalizationError(
            "Reviewer roles do not match their explicit inputs"
        )
    if (
        pair_check.status != "READY_FOR_SEPARATE_QUALIFICATION_REVIEW"
        or pair_check.issue_codes
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "PairCheck is not issue-free and ready"
        )

    evidence_record = _read_safe(
        request_paths.evidence_retained_record,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="evidence retained record",
    )
    preparer_ref = _read_safe(
        request_paths.evidence_preparer_ref,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="evidence preparer reference",
    )
    reviewer_a_ref = _read_safe(
        request_paths.reviewer_a_retained_record,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="Reviewer A retained record",
    )
    reviewer_b_ref = _read_safe(
        request_paths.reviewer_b_retained_record,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="Reviewer B retained record",
    )
    request, request_seal = _read_request(paths.decision_inputs.request)
    instruction, instruction_seal = _read_contract(
        paths.decision_inputs.qualifier_decision_record,
        CreativeSampleRealAssetQualificationDecisionInstructionV22,
        field="qualification instruction",
    )
    qualifier_ref = _read_safe(
        paths.decision_inputs.qualifier_ref,
        max_bytes=_PRIVATE_RECORD_MAX_BYTES,
        field="Qualifier reference",
    )
    decision, decision_seal = _read_decision(paths.decision)

    if evidence_record.sha256 != evidence.evidence_record_sha256:
        raise TrustedLocalRightsManifestFinalizationError(
            "evidence retained record digest disagrees"
        )
    if preparer_ref.sha256 != request.evidence_preparer_ref_sha256:
        raise TrustedLocalRightsManifestFinalizationError(
            "evidence preparer reference digest disagrees"
        )
    if (
        reviewer_a_ref.sha256 != reviewer_a.reviewer_ref_sha256
        or reviewer_a_ref.sha256 != request.reviewer_a_retained_record_sha256
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "Reviewer A retained record digest disagrees"
        )
    if (
        reviewer_b_ref.sha256 != reviewer_b.reviewer_ref_sha256
        or reviewer_b_ref.sha256 != request.reviewer_b_retained_record_sha256
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "Reviewer B retained record digest disagrees"
        )
    if qualifier_ref.sha256 != instruction.qualifier_ref_sha256 or (
        qualifier_ref.sha256 != decision.qualifier_ref_sha256
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "Qualifier reference digest disagrees"
        )
    if instruction_seal.sha256 != decision.qualifier_record_sha256:
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification instruction digest disagrees with the Decision"
        )
    if request_seal.sha256 != instruction.request_sha256 or (
        request_seal.sha256 != decision.request_sha256
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "qualification Request digest disagrees"
        )
    expected_contract_digests = (
        (pack_manifest_seal.sha256, request.pack_manifest_sha256, "Pack manifest"),
        (
            evidence_seal.sha256,
            request.rights_evidence_bundle_sha256,
            "Evidence Bundle",
        ),
        (reviewer_a_seal.sha256, request.review_a_contract_sha256, "Reviewer A"),
        (reviewer_b_seal.sha256, request.review_b_contract_sha256, "Reviewer B"),
        (pair_check_seal.sha256, request.pair_check_sha256, "PairCheck"),
    )
    for observed, expected, field in expected_contract_digests:
        if observed != expected:
            raise TrustedLocalRightsManifestFinalizationError(
                f"{field} canonical digest disagrees with the Request"
            )

    manifest: CreativeSampleRealAssetRightsManifestV2 | None = None
    manifest_seal: _FileSeal | None = None
    effective_manifest_at = manifest_at
    if manifest_path is not None:
        manifest, manifest_seal = _read_manifest(manifest_path)
        effective_manifest_at = manifest.manifest_at
    assert effective_manifest_at is not None
    files = (
        pack_manifest_seal,
        *media_seals,
        evidence_seal,
        reviewer_a_seal,
        reviewer_b_seal,
        pair_check_seal,
        _file_seal(evidence_record),
        _file_seal(preparer_ref),
        _file_seal(reviewer_a_ref),
        _file_seal(reviewer_b_ref),
        request_seal,
        _file_seal(qualifier_ref),
        instruction_seal,
        decision_seal,
        *((manifest_seal,) if manifest_seal is not None else ()),
    )
    _assert_non_aliasing(files)
    if _directory_identity(request_paths.pack_root, field="frozen Pack root") != root_identity:
        raise TrustedLocalRightsManifestFinalizationError(
            "frozen Pack root drifted during complete verification"
        )
    snapshot = _ManifestSnapshot(
        pack=pack,
        pack_root_identity=root_identity,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
        instruction=instruction,
        decision=decision,
        files=files,
        manifest=manifest,
    )
    if manifest_seal is not None and manifest_seal.sha256 in _reserved_snapshot_digests(
        snapshot,
        exclude_file=manifest_seal,
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "existing Rights Manifest aliases an immutable closure digest"
        )
    _verify_qualification_closure(snapshot)
    _assert_manifest_policy_ready(snapshot, manifest_at=effective_manifest_at)
    return snapshot


def _assert_snapshot_unchanged(
    before: _ManifestSnapshot,
    after: _ManifestSnapshot,
) -> None:
    if before != after:
        raise TrustedLocalRightsManifestFinalizationError(
            "trusted local Manifest inputs drifted during complete verification"
        )


def _manifest_trust_areas(paths: TrustedLocalRightsManifestPaths) -> tuple[Path, ...]:
    request = paths.decision_inputs.request_inputs
    return (
        request.pack_root,
        *_request_external_parents(request),
        paths.decision_inputs.request.parent,
        paths.decision_inputs.qualifier_ref.parent,
        paths.decision_inputs.qualifier_decision_record.parent,
        paths.decision.parent,
    )


def _assert_separate_manifest_parent(
    parent: Path,
    paths: TrustedLocalRightsManifestPaths,
) -> None:
    _assert_separate_trust_parent(
        parent,
        _manifest_trust_areas(paths),
        field="Manifest parent",
    )


def _validate_output(
    output_path: Path,
    *,
    paths: TrustedLocalRightsManifestPaths,
) -> _OutputTarget:
    target = _safe_absolute(output_path, must_exist=False, field="Manifest output")
    if os.path.lexists(target):
        raise TrustedLocalRightsManifestFinalizationError(
            "Manifest output must be one new file"
        )
    if target.suffix.casefold() != ".json":
        raise TrustedLocalRightsManifestFinalizationError(
            "Manifest output must use a JSON filename"
        )
    _reject_outcome_filename(target, field="Manifest output")
    if any(_paths_overlap(target, source) for source in _all_source_paths(paths)):
        raise TrustedLocalRightsManifestFinalizationError(
            "Manifest output overlaps an immutable input"
        )
    _assert_separate_manifest_parent(target.parent, paths)
    identity = _directory_identity(target.parent, field="Manifest output parent")
    return _OutputTarget(
        path=target,
        parent=target.parent,
        parent_physical_identity=(identity[0], identity[1]),
    )


def _validate_existing_manifest(
    manifest_path: Path,
    *,
    paths: TrustedLocalRightsManifestPaths,
) -> Path:
    manifest = _safe_absolute(
        manifest_path,
        must_exist=True,
        field="existing Rights Manifest",
    )
    if manifest.suffix.casefold() != ".json":
        raise TrustedLocalRightsManifestFinalizationError(
            "existing Rights Manifest must use a JSON filename"
        )
    _reject_outcome_filename(manifest, field="existing Rights Manifest")
    if any(_paths_overlap(manifest, source) for source in _all_source_paths(paths)):
        raise TrustedLocalRightsManifestFinalizationError(
            "existing Rights Manifest overlaps an immutable input"
        )
    _assert_separate_manifest_parent(manifest.parent, paths)
    return manifest


def _revalidate_output_target(target: _OutputTarget, *, must_be_absent: bool) -> None:
    parent = _safe_absolute(
        target.parent,
        must_exist=True,
        field="Manifest output parent",
    )
    identity = _directory_identity(parent, field="Manifest output parent")
    if parent != target.parent or (identity[0], identity[1]) != target.parent_physical_identity:
        raise TrustedLocalRightsManifestFinalizationError(
            "Manifest output parent identity drifted"
        )
    if must_be_absent:
        path = _safe_absolute(target.path, must_exist=False, field="Manifest output")
        if path != target.path or os.path.lexists(path):
            raise TrustedLocalRightsManifestFinalizationError(
                "Manifest output must remain absent"
            )
    else:
        path = _safe_absolute(target.path, must_exist=True, field="Manifest output")
        if path != target.path:
            raise TrustedLocalRightsManifestFinalizationError(
                "Manifest output identity drifted"
            )


if sys.platform == "win32":
    import ctypes as _windows_ctypes
    import msvcrt as _windows_msvcrt
    from ctypes import wintypes as _windows_wintypes

    def _acquire_windows_parent_guard(target: _OutputTarget) -> int:
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
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
        if handle == _windows_ctypes.c_void_p(-1).value:
            raise TrustedLocalRightsManifestFinalizationError(
                "Manifest output parent could not be guarded"
            )
        return int(handle)

    def _close_windows_handle(handle: int) -> None:
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (_windows_wintypes.HANDLE,)
        close_handle.restype = _windows_wintypes.BOOL
        if not close_handle(handle):
            error = _windows_ctypes.get_last_error()
            raise OSError(error, "CloseHandle failed")

    def _mark_windows_handle_delete(handle: int) -> bool:
        class FileDispositionInfo(_windows_ctypes.Structure):
            _fields_ = (("DeleteFile", _windows_wintypes.BOOL),)

        disposition = FileDispositionInfo(True)
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

    def _open_windows_exclusive_manifest(target: _OutputTarget) -> int:
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
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
        if handle == _windows_ctypes.c_void_p(-1).value:
            error = _windows_ctypes.get_last_error()
            if error in {80, 183}:
                raise FileExistsError(str(target.path))
            raise OSError(error, "CreateFileW failed")
        try:
            return _windows_msvcrt.open_osfhandle(
                int(handle),
                os.O_RDWR | getattr(os, "O_BINARY", 0),
            )
        except BaseException as conversion_error:
            delete_marked = False
            try:
                delete_marked = _mark_windows_handle_delete(int(handle))
            except BaseException:
                delete_marked = False
            try:
                _close_windows_handle(int(handle))
            except BaseException as close_error:
                raise TrustedLocalRightsManifestQuarantineRequired(
                    "raw created Manifest handle could not be closed"
                ) from close_error
            try:
                target.path.lstat()
            except FileNotFoundError:
                if not delete_marked:
                    raise TrustedLocalRightsManifestQuarantineRequired(
                        "raw created Manifest deletion was not confirmed"
                    ) from conversion_error
                if isinstance(conversion_error, Exception):
                    raise OSError(
                        "open_osfhandle failed after safe rollback"
                    ) from conversion_error
                raise conversion_error from None
            except OSError as inspect_error:
                raise TrustedLocalRightsManifestQuarantineRequired(
                    "raw created Manifest target could not be inspected"
                ) from inspect_error
            raise TrustedLocalRightsManifestQuarantineRequired(
                "raw created Manifest target remains after conversion failure"
            ) from conversion_error

    def _delete_open_windows_manifest(descriptor: int) -> bool:
        handle = _windows_msvcrt.get_osfhandle(descriptor)
        return _mark_windows_handle_delete(handle)

else:

    def _windows_unavailable() -> Never:
        raise OSError("Windows-only Manifest output helper is unavailable")

    def _acquire_windows_parent_guard(target: _OutputTarget) -> int:
        del target
        return _windows_unavailable()

    def _close_windows_handle(handle: int) -> None:
        del handle
        _windows_unavailable()

    def _mark_windows_handle_delete(handle: int) -> bool:
        del handle
        return _windows_unavailable()

    def _open_windows_exclusive_manifest(target: _OutputTarget) -> int:
        del target
        return _windows_unavailable()

    def _delete_open_windows_manifest(descriptor: int) -> bool:
        del descriptor
        return _windows_unavailable()


def _acquire_parent_guard(target: _OutputTarget) -> tuple[int, bool]:
    if sys.platform == "win32":
        return _acquire_windows_parent_guard(target), True
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(target.parent, flags)
        opened = os.fstat(descriptor)
    except OSError as exc:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise TrustedLocalRightsManifestFinalizationError(
            "Manifest output parent could not be guarded"
        ) from exc
    if (opened.st_dev, opened.st_ino) != target.parent_physical_identity:
        os.close(descriptor)
        raise TrustedLocalRightsManifestFinalizationError(
            "Manifest output parent changed before guard acquisition"
        )
    return descriptor, False


def _close_parent_guard(created: _CreatedManifest) -> None:
    if created.windows_parent_guard:
        _close_windows_handle(created.parent_guard)
    else:
        os.close(created.parent_guard)


def _open_exclusive_manifest(target: _OutputTarget, parent_guard: int) -> int:
    if sys.platform == "win32":
        return _open_windows_exclusive_manifest(target)
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    return os.open(target.path.name, flags, 0o600, dir_fd=parent_guard)


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _read_open_created_manifest(
    created: _CreatedManifest,
    manifest: CreativeSampleRealAssetRightsManifestV2,
) -> _FileSeal:
    raw = _canonical_document(manifest)
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
        raise TrustedLocalRightsManifestFinalizationError(
            "created Manifest could not be inspected"
        ) from exc
    opened_identity = _stat_identity(opened)
    named_identity = _stat_identity(named)
    attributes = int(getattr(named, "st_file_attributes", 0))
    if (
        opened_identity != named_identity
        or not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(named.st_mode)
        or stat.S_ISLNK(named.st_mode)
        or bool(attributes & 0x400)
        or opened.st_nlink != 1
        or named.st_nlink != 1
    ):
        raise TrustedLocalRightsManifestFinalizationError(
            "created Manifest identity drifted"
        )
    data = bytes(observed)
    try:
        loaded = parse_real_asset_rights_manifest_v2_json(data)
    except RealAssetRightsManifestV24Error as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            "created Manifest violates its strict contract"
        ) from exc
    if loaded != manifest or data != raw:
        raise TrustedLocalRightsManifestFinalizationError(
            "written Manifest failed exact verification"
        )
    return _FileSeal(
        path=created.target.path,
        sha256=_sha256(data),
        size_bytes=len(data),
        identity=opened_identity,
    )


def _invalidate_open_manifest(descriptor: int) -> bool:
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


def _emergency_poison_open_manifest(descriptor: int) -> bool:
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        if os.write(descriptor, b"\0") != 1:
            return False
        os.fsync(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        return os.read(descriptor, 1) == b"\0"
    except OSError:
        return False


def _inspect_created_manifest_name(
    created: _CreatedManifest,
    opened_physical: tuple[int, int],
) -> tuple[bool, bool]:
    """Return ``(safe_identity, absent)`` after the exact descriptor close attempt.

    POSIX has no portable unlink-by-file-descriptor operation.  A pathname unlink after an
    identity check would retain a stat-to-unlink replacement race, so rollback deliberately
    leaves an exact zero/NUL remnant instead of deleting by name.
    """

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


def _rollback_created_manifest(created: _CreatedManifest) -> None:
    if created.closed:
        return
    invalidated = False
    delete_pending = False
    name_safe = False
    name_absent = False
    descriptor_closed = False
    opened_physical: tuple[int, int] | None = None
    try:
        try:
            opened = os.fstat(created.descriptor)
            opened_physical = (opened.st_dev, opened.st_ino)
        except BaseException:
            opened_physical = None
        try:
            invalidated = _invalidate_open_manifest(created.descriptor)
        except BaseException:
            invalidated = False
        if not invalidated:
            try:
                invalidated = _emergency_poison_open_manifest(created.descriptor)
            except BaseException:
                invalidated = False
        try:
            if sys.platform == "win32":
                delete_pending = _delete_open_windows_manifest(created.descriptor)
        except BaseException:
            delete_pending = False
    finally:
        try:
            os.close(created.descriptor)
            descriptor_closed = True
        except BaseException:
            pass
        try:
            if opened_physical is not None:
                name_safe, name_absent = _inspect_created_manifest_name(
                    created,
                    opened_physical,
                )
        except BaseException:
            name_safe = False
            name_absent = False
        finally:
            try:
                _close_parent_guard(created)
            except BaseException:
                pass
            created.closed = True
    deletion_confirmed = False
    if sys.platform == "win32" and delete_pending and descriptor_closed and name_absent:
        deletion_confirmed = True
    rollback_confirmed = (
        name_safe and (invalidated or deletion_confirmed)
        if sys.platform == "win32"
        else invalidated and name_safe
    )
    if not rollback_confirmed:
        raise TrustedLocalRightsManifestQuarantineRequired(
            "created Manifest rollback failed closed; output requires quarantine"
        )


def _fsync_parent_directory(created: _CreatedManifest) -> None:
    if not created.windows_parent_guard:
        os.fsync(created.parent_guard)


def _commit_created_manifest(
    created: _CreatedManifest,
    manifest: CreativeSampleRealAssetRightsManifestV2,
) -> None:
    if created.closed or created.seal is None:
        raise TrustedLocalRightsManifestFinalizationError(
            "created Manifest is not publishable"
        )
    _revalidate_output_target(created.target, must_be_absent=False)
    final_seal = _read_open_created_manifest(created, manifest)
    if final_seal != created.seal:
        raise TrustedLocalRightsManifestFinalizationError(
            "created Manifest drifted before commit"
        )
    _fsync_parent_directory(created)
    os.close(created.descriptor)
    _close_parent_guard(created)
    created.closed = True


def _create_new_manifest(
    target: _OutputTarget,
    manifest: CreativeSampleRealAssetRightsManifestV2,
) -> _CreatedManifest:
    _revalidate_output_target(target, must_be_absent=True)
    parent_guard = _acquire_parent_guard(target)
    descriptor: int | None = None
    created: _CreatedManifest | None = None
    try:
        _revalidate_output_target(target, must_be_absent=True)
        descriptor = _open_exclusive_manifest(target, parent_guard[0])
        created = _CreatedManifest(
            target=target,
            descriptor=descriptor,
            parent_guard=parent_guard[0],
            windows_parent_guard=parent_guard[1],
        )
        raw = _canonical_document(manifest)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise OSError("short write")
            offset += written
        os.fsync(descriptor)
        created.seal = _read_open_created_manifest(created, manifest)
        _revalidate_output_target(target, must_be_absent=False)
        return created
    except FileExistsError as exc:
        if descriptor is None:
            if parent_guard[1]:
                _close_windows_handle(parent_guard[0])
            else:
                os.close(parent_guard[0])
        raise TrustedLocalRightsManifestFinalizationError(
            "Manifest output must be one new file"
        ) from exc
    except BaseException as exc:
        if created is not None:
            try:
                _rollback_created_manifest(created)
            except TrustedLocalRightsManifestFinalizationError:
                raise
        else:
            try:
                if parent_guard[1]:
                    _close_windows_handle(parent_guard[0])
                else:
                    os.close(parent_guard[0])
            except BaseException:
                pass
        if isinstance(exc, TrustedLocalRightsManifestFinalizationError):
            raise
        if isinstance(exc, Exception):
            raise TrustedLocalRightsManifestFinalizationError(
                "Manifest output could not be created"
            ) from exc
        raise


def _reserved_snapshot_digests(
    snapshot: _ManifestSnapshot,
    *,
    exclude_file: _FileSeal | None = None,
) -> set[str]:
    pack = snapshot.pack.manifest
    return {
        *(
            item.sha256
            for item in snapshot.files
            if exclude_file is None or item.path != exclude_file.path
        ),
        snapshot.request.policy_document_sha256,
        RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256,
        snapshot.request.review_a_record_sha256,
        snapshot.request.review_b_record_sha256,
        *(descriptor.sha256 for descriptor in pack.objects),
        *(descriptor.provenance_record_sha256 for descriptor in pack.objects),
        *(descriptor.technical_record_sha256 for descriptor in pack.objects),
    }


def inspect_manifest_ready(
    paths: TrustedLocalRightsManifestPaths,
    *,
    manifest_at: str,
) -> Literal["READY_FOR_MANIFEST_FINALIZATION"]:
    """Verify Manifest readiness twice, without calling the v2.4 builder or writing."""

    manifest_at = _canonical_utc_seconds(manifest_at, field="manifest_at")
    normalized = _normalize_paths(paths)
    before = _capture_snapshot(normalized, manifest_at=manifest_at)
    after = _capture_snapshot(normalized, manifest_at=manifest_at)
    _assert_snapshot_unchanged(before, after)
    return _READY_FOR_MANIFEST_FINALIZATION


def finalize_manifest(
    paths: TrustedLocalRightsManifestPaths,
    output_path: Path,
    *,
    manifest_at: str,
) -> CreativeSampleRealAssetRightsManifestV2:
    """Create one canonical Manifest new-only after two stable complete snapshots."""

    manifest_at = _canonical_utc_seconds(manifest_at, field="manifest_at")
    normalized = _normalize_paths(paths)
    target = _validate_output(output_path, paths=normalized)
    before = _capture_snapshot(normalized, manifest_at=manifest_at)
    immediately_before_write = _capture_snapshot(normalized, manifest_at=manifest_at)
    _assert_snapshot_unchanged(before, immediately_before_write)
    try:
        manifest = build_real_asset_rights_manifest_v2(
            pack=immediately_before_write.pack.manifest,
            evidence=immediately_before_write.evidence,
            reviewer_a=immediately_before_write.reviewer_a,
            reviewer_b=immediately_before_write.reviewer_b,
            pair_check=immediately_before_write.pair_check,
            request=immediately_before_write.request,
            instruction=immediately_before_write.instruction,
            decision=immediately_before_write.decision,
            manifest_at=manifest_at,
        )
    except (RealAssetRightsManifestV24Error, ValidationError, ValueError) as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            "Rights Manifest could not be built from the exact stable closure"
        ) from exc

    created: _CreatedManifest | None = None
    try:
        created = _create_new_manifest(target, manifest)
        assert created.seal is not None
        if created.seal.sha256 in _reserved_snapshot_digests(before):
            raise TrustedLocalRightsManifestFinalizationError(
                "written Manifest aliases an immutable source digest"
            )
        after = _capture_snapshot(normalized, manifest_at=manifest_at)
        _assert_snapshot_unchanged(before, after)
        _commit_created_manifest(created, manifest)
    except BaseException as exc:
        if created is not None:
            try:
                _rollback_created_manifest(created)
            except TrustedLocalRightsManifestFinalizationError:
                raise
        if isinstance(exc, TrustedLocalRightsManifestFinalizationError):
            raise
        if isinstance(exc, Exception):
            raise TrustedLocalRightsManifestFinalizationError(
                "Manifest publication failed closed"
            ) from exc
        raise
    return manifest


def verify_manifest(
    paths: TrustedLocalRightsManifestPaths,
    manifest_path: Path,
) -> CreativeSampleRealAssetRightsManifestV2:
    """Historically rebuild one existing Manifest without a clock or filesystem write."""

    normalized = _normalize_paths(paths)
    manifest_path = _validate_existing_manifest(manifest_path, paths=normalized)
    before = _capture_snapshot(
        normalized,
        manifest_at=None,
        manifest_path=manifest_path,
    )
    assert before.manifest is not None
    try:
        verified = verify_real_asset_rights_manifest_closure_v2(
            pack=before.pack.manifest,
            evidence=before.evidence,
            reviewer_a=before.reviewer_a,
            reviewer_b=before.reviewer_b,
            pair_check=before.pair_check,
            request=before.request,
            instruction=before.instruction,
            decision=before.decision,
            manifest=before.manifest,
        )
    except (RealAssetRightsManifestV24Error, ValidationError, ValueError) as exc:
        raise TrustedLocalRightsManifestFinalizationError(
            "Rights Manifest failed exact historical reconstruction"
        ) from exc
    if verified != before.manifest:
        raise TrustedLocalRightsManifestFinalizationError(
            "Rights Manifest verifier returned a different document"
        )
    after = _capture_snapshot(
        normalized,
        manifest_at=None,
        manifest_path=manifest_path,
    )
    _assert_snapshot_unchanged(before, after)
    return verified


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pack-root", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--pack-manifest", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--media-path", required=True, action="append", type=Path)
    parser.add_argument("--evidence", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--reviewer-a", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--reviewer-b", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--pair-check", required=True, type=Path, action=_StoreOnce)
    parser.add_argument(
        "--evidence-retained-record", required=True, type=Path, action=_StoreOnce
    )
    parser.add_argument(
        "--evidence-preparer-ref", required=True, type=Path, action=_StoreOnce
    )
    parser.add_argument(
        "--reviewer-a-retained-record", required=True, type=Path, action=_StoreOnce
    )
    parser.add_argument(
        "--reviewer-b-retained-record", required=True, type=Path, action=_StoreOnce
    )
    parser.add_argument("--request", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--qualifier-ref", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--instruction", required=True, type=Path, action=_StoreOnce)
    parser.add_argument("--decision", required=True, type=Path, action=_StoreOnce)


def _paths_from_namespace(args: argparse.Namespace) -> TrustedLocalRightsManifestPaths:
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
        request=cast(Path, args.request),
        qualifier_ref=cast(Path, args.qualifier_ref),
        qualifier_decision_record=cast(Path, args.instruction),
    )
    return TrustedLocalRightsManifestPaths(
        decision_inputs=decision_inputs,
        decision=cast(Path, args.decision),
    )


def _safe_summary(
    operation: str,
    value: str | CreativeSampleRealAssetRightsManifestV2,
) -> str:
    inspected = operation == "inspect-manifest-ready"
    status: str
    if inspected:
        rights_manifest_created = False
        rights_qualification_performed = True
        status = _READY_FOR_MANIFEST_FINALIZATION
    else:
        assert isinstance(value, CreativeSampleRealAssetRightsManifestV2)
        rights_manifest_created = value.rights_manifest_created
        rights_qualification_performed = value.rights_qualification_performed
        status = value.status
    payload: dict[str, object] = {
        "current_gate": "HUMAN_GATE",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "operation": operation,
        "posts_allowed": 0,
        "provider_requests": 0,
        "provider_state": "NOT_AUTHORIZED",
        "rights_manifest_created": rights_manifest_created,
        "rights_qualification_performed": rights_qualification_performed,
        "status": status,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _failure_summary(status: str) -> str:
    return json.dumps(
        {
            "current_gate": "HUMAN_GATE",
            "eligible_for_real_generation": False,
            "execution_authorized": False,
            "posts_allowed": 0,
            "provider_requests": 0,
            "provider_state": "NOT_AUTHORIZED",
            "rights_manifest_created": False,
            "status": status,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _FailClosedArgumentParser(
        description="Finalize or verify one trusted local inert Rights Manifest"
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=_FailClosedArgumentParser,
    )
    inspect_parser = commands.add_parser("inspect-manifest-ready")
    _add_common_arguments(inspect_parser)
    inspect_parser.add_argument("--manifest-at", required=True, action=_StoreOnce)
    finalize_parser = commands.add_parser("finalize-manifest")
    _add_common_arguments(finalize_parser)
    finalize_parser.add_argument("--manifest-at", required=True, action=_StoreOnce)
    finalize_parser.add_argument("--output", required=True, type=Path, action=_StoreOnce)
    verify_parser = commands.add_parser("verify-manifest")
    _add_common_arguments(verify_parser)
    verify_parser.add_argument(
        "--manifest-file", required=True, type=Path, action=_StoreOnce
    )
    try:
        args = parser.parse_args(argv)
    except Exception:
        print(_failure_summary("FAILED_CLOSED"), file=sys.stderr)
        return 2
    try:
        paths = _paths_from_namespace(args)
        if args.command == "inspect-manifest-ready":
            result: str | CreativeSampleRealAssetRightsManifestV2 = inspect_manifest_ready(
                paths,
                manifest_at=cast(str, args.manifest_at),
            )
        elif args.command == "finalize-manifest":
            result = finalize_manifest(
                paths,
                cast(Path, args.output),
                manifest_at=cast(str, args.manifest_at),
            )
        else:
            result = verify_manifest(paths, cast(Path, args.manifest_file))
    except TrustedLocalRightsManifestQuarantineRequired:
        print(
            _failure_summary("ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"),
            file=sys.stderr,
        )
        return 3
    except BaseException:
        print(_failure_summary("FAILED_CLOSED"), file=sys.stderr)
        return 2
    print(_safe_summary(cast(str, args.command), result))
    return 0


__all__ = [
    "TrustedLocalRightsManifestFinalizationError",
    "TrustedLocalRightsManifestPaths",
    "TrustedLocalRightsManifestQuarantineRequired",
    "finalize_manifest",
    "inspect_manifest_ready",
    "main",
    "verify_manifest",
]


if __name__ == "__main__":
    raise SystemExit(main())
