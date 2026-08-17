"""Prepare a static, offline human-review console for one frozen real-asset pack.

The console is deliberately draft-only.  It verifies an explicitly selected frozen pack,
publishes no media, starts no server, and has no path to a rights manifest, qualification,
Provider, runtime, database, or authorization boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from sdc.creative_media import CreativeMediaError, validate_local_path
from sdc.real_asset_intake import FrozenRealAssetPack, verify_real_asset_candidate_pack
from sdc.real_asset_media import RealAssetMediaError, read_safe_local_file
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetRightsEvidenceBundleV2,
    RealAssetReviewV2Error,
    build_real_asset_rights_evidence_bundle_v2,
    load_real_asset_rights_evidence_bundle_v2,
)

CONSOLE_PROFILE = "creative-sample-real-asset-human-review-v2"
CONSOLE_DIRECTORY_PREFIX = "human-review-console-v2-"
CONTEXT_JSON_NAME = "review-context.json"
CONTEXT_SCRIPT_NAME = "review-context.js"
STATIC_ASSET_NAMES = ("index.html", "app.js", "style.css")
CONSOLE_MAX_STATIC_BYTES = 1024 * 1024
CONSOLE_MAX_EVIDENCE_BYTES = 1024 * 1024
WorkspaceKind = Literal["EVIDENCE", "REVIEWER_A", "REVIEWER_B"]
_WORKSPACE_SUFFIX: dict[WorkspaceKind, str] = {
    "EVIDENCE": "evidence",
    "REVIEWER_A": "reviewer-a",
    "REVIEWER_B": "reviewer-b",
}


class HumanReviewConsoleError(RuntimeError):
    """The offline draft console could not be prepared safely."""


@dataclass(frozen=True, slots=True)
class HumanReviewConsoleWorkspace:
    root: Path
    context_path: Path
    index_path: Path
    pack_id: str
    workspace_kind: WorkspaceKind
    review_context_sha256: str
    evidence_bundle_id: str | None
    evidence_bundle_sha256: str | None


@dataclass(frozen=True, slots=True)
class _VerifiedEvidence:
    path: Path
    bundle: CreativeSampleRealAssetRightsEvidenceBundleV2
    sha256: str


def _canonical_document(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _is_link_like(path: Path, info: os.stat_result) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return (
        stat.S_ISLNK(info.st_mode)
        or bool(int(getattr(info, "st_file_attributes", 0)) & 0x400)
        or bool(is_junction is not None and is_junction())
    )


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _read_static_asset(name: str) -> bytes:
    if name not in STATIC_ASSET_NAMES:
        raise HumanReviewConsoleError("unknown human-review console asset")
    path = Path(__file__).with_name("human_review_console_assets") / name
    try:
        before = path.lstat()
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or _is_link_like(path, before)
            or before.st_size > CONSOLE_MAX_STATIC_BYTES
        ):
            raise HumanReviewConsoleError("human-review console asset is not a safe regular file")
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            raw = handle.read(CONSOLE_MAX_STATIC_BYTES + 1)
        after = path.lstat()
    except OSError as exc:
        raise HumanReviewConsoleError("human-review console asset could not be read") from exc
    if (
        len(raw) > CONSOLE_MAX_STATIC_BYTES
        or len(raw) != opened.st_size
        or _identity(before) != _identity(opened)
        or _identity(opened) != _identity(after)
        or not stat.S_ISREG(opened.st_mode)
        or opened.st_nlink != 1
        or _is_link_like(path, after)
        or after.st_nlink != 1
    ):
        raise HumanReviewConsoleError("human-review console asset changed while it was read")
    return raw


def _read_workspace_file(path: Path) -> bytes:
    try:
        before = path.lstat()
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or _is_link_like(path, before)
            or before.st_size > CONSOLE_MAX_STATIC_BYTES
        ):
            raise HumanReviewConsoleError(
                "human-review console workspace contains an unsafe file"
            )
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            raw = handle.read(CONSOLE_MAX_STATIC_BYTES + 1)
        after = path.lstat()
    except OSError as exc:
        raise HumanReviewConsoleError(
            "human-review console workspace file could not be read"
        ) from exc
    if (
        len(raw) > CONSOLE_MAX_STATIC_BYTES
        or len(raw) != opened.st_size
        or _identity(before) != _identity(opened)
        or _identity(opened) != _identity(after)
        or not stat.S_ISREG(opened.st_mode)
        or opened.st_nlink != 1
        or _is_link_like(path, after)
        or after.st_nlink != 1
    ):
        raise HumanReviewConsoleError(
            "human-review console workspace file changed while it was read"
        )
    return raw


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _nearest_git_root(path: Path) -> Path | None:
    cursor = path if os.path.lexists(path) and path.is_dir() else path.parent
    while True:
        if os.path.lexists(cursor / ".git"):
            return cursor
        parent = cursor.parent
        if parent == cursor:
            return None
        cursor = parent


def _known_repository_root() -> Path | None:
    return _nearest_git_root(Path(__file__).absolute())


def _require_outside_git(path: Path, *, field: str) -> None:
    containing_git_root = _nearest_git_root(path)
    known_repository_root = _known_repository_root()
    if containing_git_root is not None or (
        known_repository_root is not None and _paths_overlap(path, known_repository_root)
    ):
        raise HumanReviewConsoleError(f"{field} must remain outside Git repositories")


def _load_verified_evidence(
    path: Path,
    *,
    frozen: FrozenRealAssetPack,
) -> _VerifiedEvidence:
    try:
        absolute = validate_local_path(path, must_exist=True)
    except CreativeMediaError as exc:
        raise HumanReviewConsoleError("rights evidence path is not safe and local") from exc
    if _paths_overlap(absolute, frozen.root):
        raise HumanReviewConsoleError(
            "rights evidence bundle and frozen pack must not overlap"
        )
    _require_outside_git(absolute, field="rights evidence bundle")
    try:
        before = read_safe_local_file(absolute, max_bytes=CONSOLE_MAX_EVIDENCE_BYTES)
        evidence = load_real_asset_rights_evidence_bundle_v2(absolute)
        after = read_safe_local_file(absolute, max_bytes=CONSOLE_MAX_EVIDENCE_BYTES)
    except (RealAssetMediaError, RealAssetReviewV2Error) as exc:
        raise HumanReviewConsoleError(
            "rights evidence bundle is not a safe canonical v2 document"
        ) from exc
    if before.identity != after.identity or before.sha256 != after.sha256:
        raise HumanReviewConsoleError("rights evidence bundle changed while it was read")
    canonical = _canonical_document(evidence.model_dump(mode="json"))
    if after.data != canonical:
        raise HumanReviewConsoleError(
            "rights evidence bundle must use exact canonical v2 JSON bytes"
        )
    try:
        rebuilt = build_real_asset_rights_evidence_bundle_v2(
            pack=frozen.manifest,
            evidence_record_sha256=evidence.evidence_record_sha256,
            copyright_basis=evidence.copyright_basis,
            likeness_basis=evidence.likeness_basis,
            privacy_basis=evidence.privacy_basis,
            territory=evidence.territory,
            use_scope=evidence.use_scope,
            valid_until=evidence.valid_until,
        )
    except (RealAssetReviewV2Error, ValueError) as exc:
        raise HumanReviewConsoleError(
            "rights evidence bundle could not be rebuilt against the frozen pack"
        ) from exc
    if rebuilt != evidence:
        raise HumanReviewConsoleError(
            "rights evidence bundle drifted from the exact frozen pack"
        )
    return _VerifiedEvidence(path=absolute, bundle=evidence, sha256=after.sha256)


def _verified_evidence_for_kind(
    *,
    workspace_kind: WorkspaceKind,
    evidence_path: Path | None,
    frozen: FrozenRealAssetPack,
) -> _VerifiedEvidence | None:
    if workspace_kind == "EVIDENCE":
        if evidence_path is not None:
            raise HumanReviewConsoleError(
                "EVIDENCE workspace must not bind an already-finalized evidence bundle"
            )
        return None
    if evidence_path is None:
        raise HumanReviewConsoleError(
            "REVIEWER_A and REVIEWER_B workspaces require an explicit evidence bundle"
        )
    return _load_verified_evidence(evidence_path, frozen=frozen)


def _relative_media_path(*, console_root: Path, media_path: Path) -> str:
    try:
        rendered = os.path.relpath(media_path, start=console_root)
    except ValueError as exc:
        raise HumanReviewConsoleError(
            "console and frozen pack must share a local drive for relative media paths"
        ) from exc
    portable = rendered.replace(os.sep, "/")
    candidate = PurePosixPath(portable)
    if candidate.is_absolute() or not candidate.parts:
        raise HumanReviewConsoleError("console media path could not be made relative")
    return candidate.as_posix()


def _build_context(
    *,
    frozen: FrozenRealAssetPack,
    console_root: Path,
    workspace_kind: WorkspaceKind,
    evidence: _VerifiedEvidence | None,
) -> dict[str, object]:
    manifest = frozen.manifest
    manifest_payload = manifest.model_dump(mode="json")
    manifest_sha256 = hashlib.sha256(_canonical_document(manifest_payload)).hexdigest()
    assets: list[dict[str, object]] = []
    for descriptor in manifest.objects:
        media_path = frozen.root.joinpath(*PurePosixPath(descriptor.object_path).parts)
        technical_evidence = descriptor.image if descriptor.image is not None else descriptor.audio
        assets.append(
            {
                "ordinal": descriptor.ordinal,
                "requirement_id": descriptor.requirement_id,
                "kind": descriptor.kind,
                "subject_id": descriptor.subject_id,
                "logical_path": descriptor.logical_path,
                "object_path": descriptor.object_path,
                "media_relative_path": _relative_media_path(
                    console_root=console_root,
                    media_path=media_path,
                ),
                "media_type": descriptor.media_type,
                "media_sha256": descriptor.sha256,
                "media_size_bytes": descriptor.size_bytes,
                "duration_ms": descriptor.duration_ms,
                "source_authority": descriptor.source_authority,
                "provenance_record_sha256": descriptor.provenance_record_sha256,
                "technical_profile": descriptor.technical_profile,
                "technical_record_sha256": descriptor.technical_record_sha256,
                "technical_summary": (
                    technical_evidence.model_dump(mode="json")
                    if technical_evidence is not None
                    else None
                ),
                "read_only": True,
            }
        )
    evidence_projection: dict[str, object] | None = None
    if evidence is not None:
        bundle = evidence.bundle
        evidence_projection = {
            "bundle_id": bundle.bundle_id,
            "bundle_sha256": evidence.sha256,
            "evidence_record_sha256": bundle.evidence_record_sha256,
            "copyright_basis": bundle.copyright_basis,
            "likeness_basis": bundle.likeness_basis,
            "privacy_basis": bundle.privacy_basis,
            "territory": bundle.territory,
            "use_scope": bundle.use_scope,
            "valid_until": bundle.valid_until,
            "read_only": True,
        }
    return {
        "schema_version": "2.0.0",
        "document_type": "sdc.creative-sample-human-review-console-context",
        "profile": CONSOLE_PROFILE,
        "console_state": "DRAFT_ONLY",
        "workspace_kind": workspace_kind,
        "reviewer_role": workspace_kind if workspace_kind != "EVIDENCE" else None,
        "pack_id": manifest.pack_id,
        "pack_manifest_sha256": manifest_sha256,
        "evidence_bundle": evidence_projection,
        "assets": assets,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
        "rights_manifest_created": False,
        "rights_qualification_performed": False,
    }


def _context_script(context: dict[str, object], context_sha256: str) -> bytes:
    compact = json.dumps(
        context,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    quoted = json.dumps(compact, ensure_ascii=True)
    return (
        "\"use strict\";\n"
        f"window.SDC_HUMAN_REVIEW_CONTEXT_SHA256 = \"{context_sha256}\";\n"
        f"window.SDC_HUMAN_REVIEW_CONTEXT = JSON.parse({quoted});\n"
    ).encode()


def _workspace_payloads(context: dict[str, object]) -> tuple[dict[str, bytes], str]:
    context_document = _canonical_document(context)
    context_sha256 = hashlib.sha256(context_document).hexdigest()
    return (
        {
            **{name: _read_static_asset(name) for name in STATIC_ASSET_NAMES},
            CONTEXT_JSON_NAME: context_document,
            CONTEXT_SCRIPT_NAME: _context_script(context, context_sha256),
        },
        context_sha256,
    )


def _write_new_file(path: Path, data: bytes) -> None:
    try:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise HumanReviewConsoleError("human-review console file could not be published") from exc


def _cleanup_new_workspace(root: Path, names: tuple[str, ...]) -> None:
    for name in names:
        try:
            (root / name).unlink(missing_ok=True)
        except OSError:
            pass
    try:
        root.rmdir()
    except OSError:
        pass


def verify_human_review_console_workspace(
    pack_root: Path,
    workspace_root: Path,
    workspace_kind: WorkspaceKind,
    *,
    evidence_path: Path | None = None,
) -> HumanReviewConsoleWorkspace:
    """Rebuild and verify one exact five-file console workspace without trusting its JSON."""

    if workspace_kind not in _WORKSPACE_SUFFIX:
        raise HumanReviewConsoleError("unsupported human-review console workspace kind")
    frozen = verify_real_asset_candidate_pack(pack_root)
    try:
        root = validate_local_path(workspace_root, must_exist=True)
        root_info = root.lstat()
    except (CreativeMediaError, OSError) as exc:
        raise HumanReviewConsoleError(
            "human-review console workspace path is not safe and local"
        ) from exc
    if not stat.S_ISDIR(root_info.st_mode) or _is_link_like(root, root_info):
        raise HumanReviewConsoleError(
            "human-review console workspace must be a non-linked directory"
        )
    if _paths_overlap(root, frozen.root):
        raise HumanReviewConsoleError(
            "human-review console and frozen pack must not overlap"
        )
    _require_outside_git(root, field="human-review console")
    evidence = _verified_evidence_for_kind(
        workspace_kind=workspace_kind,
        evidence_path=evidence_path,
        frozen=frozen,
    )
    context = _build_context(
        frozen=frozen,
        console_root=root,
        workspace_kind=workspace_kind,
        evidence=evidence,
    )
    expected_payloads, context_sha256 = _workspace_payloads(context)
    expected_names = frozenset(expected_payloads)
    try:
        entries = tuple(root.iterdir())
    except OSError as exc:
        raise HumanReviewConsoleError(
            "human-review console workspace could not be enumerated"
        ) from exc
    if len(entries) != len(expected_names) or {entry.name for entry in entries} != expected_names:
        raise HumanReviewConsoleError(
            "human-review console workspace must contain the exact five committed files"
        )
    for name, expected in expected_payloads.items():
        if _read_workspace_file(root / name) != expected:
            raise HumanReviewConsoleError(
                f"human-review console workspace file drifted: {name}"
            )
    try:
        root_after = root.lstat()
        names_after = frozenset(entry.name for entry in root.iterdir())
    except OSError as exc:
        raise HumanReviewConsoleError(
            "human-review console workspace changed while it was verified"
        ) from exc
    if (
        _identity(root_info) != _identity(root_after)
        or _is_link_like(root, root_after)
        or names_after != expected_names
    ):
        raise HumanReviewConsoleError(
            "human-review console workspace changed while it was verified"
        )
    verified_after = verify_real_asset_candidate_pack(frozen.root)
    if verified_after.manifest != frozen.manifest:
        raise HumanReviewConsoleError(
            "frozen pack changed while the console workspace was verified"
        )
    return HumanReviewConsoleWorkspace(
        root=root,
        context_path=root / CONTEXT_JSON_NAME,
        index_path=root / "index.html",
        pack_id=frozen.manifest.pack_id,
        workspace_kind=workspace_kind,
        review_context_sha256=context_sha256,
        evidence_bundle_id=(evidence.bundle.bundle_id if evidence is not None else None),
        evidence_bundle_sha256=(evidence.sha256 if evidence is not None else None),
    )


def write_human_review_console(
    pack_root: Path,
    output_parent: Path,
    workspace_kind: WorkspaceKind,
    *,
    evidence_path: Path | None = None,
) -> HumanReviewConsoleWorkspace:
    """Create one new static draft console after exact read-only pack verification."""

    if workspace_kind not in _WORKSPACE_SUFFIX:
        raise HumanReviewConsoleError("unsupported human-review console workspace kind")
    frozen = verify_real_asset_candidate_pack(pack_root)
    evidence = _verified_evidence_for_kind(
        workspace_kind=workspace_kind,
        evidence_path=evidence_path,
        frozen=frozen,
    )
    try:
        destination_parent = validate_local_path(output_parent, must_exist=True)
    except CreativeMediaError as exc:
        raise HumanReviewConsoleError(str(exc)) from exc
    if not destination_parent.is_dir():
        raise HumanReviewConsoleError("human-review console output parent must be a directory")

    final = destination_parent / (
        f"{CONSOLE_DIRECTORY_PREFIX}{frozen.manifest.pack_id}-"
        f"{_WORKSPACE_SUFFIX[workspace_kind]}"
    )
    try:
        final = validate_local_path(final, must_exist=False)
    except CreativeMediaError as exc:
        raise HumanReviewConsoleError(str(exc)) from exc
    if os.path.lexists(final):
        raise HumanReviewConsoleError("human-review console output must be a new directory")
    if _paths_overlap(final, frozen.root):
        raise HumanReviewConsoleError("human-review console and frozen pack must not overlap")
    _require_outside_git(final, field="human-review console")

    context = _build_context(
        frozen=frozen,
        console_root=final,
        workspace_kind=workspace_kind,
        evidence=evidence,
    )
    names = (*STATIC_ASSET_NAMES, CONTEXT_JSON_NAME, CONTEXT_SCRIPT_NAME)
    payloads, _context_sha256 = _workspace_payloads(context)
    try:
        final.mkdir()
    except OSError as exc:
        raise HumanReviewConsoleError(
            "human-review console directory could not be created"
        ) from exc
    created: list[str] = []
    try:
        for name in names:
            _write_new_file(final / name, payloads[name])
            created.append(name)
    except Exception:
        _cleanup_new_workspace(final, tuple(created))
        raise

    try:
        return verify_human_review_console_workspace(
            frozen.root,
            final,
            workspace_kind,
            evidence_path=evidence_path,
        )
    except Exception:
        _cleanup_new_workspace(final, names)
        raise


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare an offline draft-only review console")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="verify one frozen pack and create a console")
    prepare.add_argument("--pack-root", type=Path, required=True)
    prepare.add_argument("--output-parent", type=Path, required=True)
    prepare.add_argument(
        "--evidence",
        type=Path,
        help="canonical v2 evidence bundle; required only for REVIEWER_A/REVIEWER_B",
    )
    prepare.add_argument(
        "--workspace-kind",
        choices=tuple(_WORKSPACE_SUFFIX),
        required=True,
    )
    args = parser.parse_args(argv)
    if args.command != "prepare":  # pragma: no cover - argparse enforces the finite command set.
        parser.error("unsupported command")
    workspace = write_human_review_console(
        args.pack_root,
        args.output_parent,
        args.workspace_kind,
        evidence_path=args.evidence,
    )
    print(
        json.dumps(
            {
                "console": str(workspace.index_path),
                "current_gate": "HUMAN_GATE",
                "execution_authorized": False,
                "evidence_bundle_id": workspace.evidence_bundle_id,
                "evidence_bundle_sha256": workspace.evidence_bundle_sha256,
                "pack_id": workspace.pack_id,
                "posts_allowed": 0,
                "provider_requests": 0,
                "provider_state": "NOT_AUTHORIZED",
                "review_context_sha256": workspace.review_context_sha256,
                "workspace_kind": workspace.workspace_kind,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


__all__ = [
    "HumanReviewConsoleError",
    "HumanReviewConsoleWorkspace",
    "verify_human_review_console_workspace",
    "write_human_review_console",
]


if __name__ == "__main__":
    raise SystemExit(_main())
