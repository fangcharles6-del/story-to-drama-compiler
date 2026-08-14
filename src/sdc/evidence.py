"""Read-only content-addressed evidence bundle construction and verification."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from sdc.contracts import (
    EvidenceAcquisition,
    EvidenceBundle,
    EvidenceBundleContent,
    EvidenceCapture,
    EvidenceMember,
    EvidenceObject,
    evidence_bundle_content_sha256,
    evidence_logical_tree_sha256,
)

_MAX_MANIFEST_BYTES = 4 * 1024 * 1024


class EvidenceBundleError(ValueError):
    """Raised when a bundle or a content-addressed object fails closed."""


class EvidenceBundleExpiredError(EvidenceBundleError):
    """Raised when a caller requires current evidence but the bundle has expired."""


class EvidenceBundleNotYetValidError(EvidenceBundleError):
    """Raised when a caller evaluates a bundle before it was assembled."""


class EvidenceBundleUnverifiedOriginError(EvidenceBundleError):
    """Raised when inherited evidence lacks a verified origin resolver."""


@dataclass(frozen=True, slots=True)
class ResolvedEvidenceMember:
    logical_path: str
    role: str
    object_sha256: str
    data: bytes


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise EvidenceBundleError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_evidence_bundle(path: Path, *, expected_bundle_id: str) -> EvidenceBundle:
    """Load a UTF-8 bundle manifest bound to a caller-supplied trusted digest."""
    try:
        if _is_link_like(path):
            raise EvidenceBundleError("evidence bundle manifest must not be a link or junction")
        manifest_stat = path.stat()
        if not stat.S_ISREG(manifest_stat.st_mode):
            raise EvidenceBundleError("evidence bundle manifest must be a regular file")
        if manifest_stat.st_size > _MAX_MANIFEST_BYTES:
            raise EvidenceBundleError("evidence bundle manifest exceeds the byte limit")
        with path.open("rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise EvidenceBundleError("evidence bundle manifest must be a regular file")
            raw_bytes = handle.read(_MAX_MANIFEST_BYTES + 1)
        if len(raw_bytes) > _MAX_MANIFEST_BYTES:
            raise EvidenceBundleError("evidence bundle manifest exceeds the byte limit")
        raw = raw_bytes.decode("utf-8")
        payload = json.loads(raw, object_pairs_hook=_reject_duplicate_json_keys)
        bundle = EvidenceBundle.model_validate(payload)
        if bundle.bundle_id != expected_bundle_id:
            raise EvidenceBundleError("evidence bundle does not match the trusted bundle ID")
        return bundle
    except EvidenceBundleError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise EvidenceBundleError("invalid evidence bundle manifest") from exc


def build_evidence_bundle(
    *,
    created_at: datetime,
    objects: Iterable[EvidenceObject],
    members: Iterable[EvidenceMember],
    captures: Iterable[EvidenceCapture],
    predecessor_bundle_id: str | None = None,
) -> EvidenceBundle:
    """Build a canonical in-memory bundle without reading or writing evidence files."""
    try:
        ordered_objects = tuple(
            sorted(
                (
                    EvidenceObject.model_validate(item.model_dump(mode="python"))
                    for item in objects
                ),
                key=lambda item: item.sha256,
            )
        )
        ordered_members = tuple(
            sorted(
                (
                    EvidenceMember.model_validate(item.model_dump(mode="python"))
                    for item in members
                ),
                key=lambda item: item.logical_path,
            )
        )
        ordered_captures = tuple(
            sorted(
                (
                    EvidenceCapture.model_validate(item.model_dump(mode="python"))
                    for item in captures
                ),
                key=lambda item: item.capture_id,
            )
        )
        if not ordered_captures:
            raise EvidenceBundleError("an evidence bundle requires at least one capture")
        if any(item.acquisition is not EvidenceAcquisition.FRESH for item in ordered_captures):
            raise EvidenceBundleError(
                "inherited evidence requires the deferred verified-origin importer"
            )
        content = EvidenceBundleContent(
            created_at=created_at,
            valid_until=min(item.valid_until for item in ordered_captures),
            predecessor_bundle_id=predecessor_bundle_id,
            objects=ordered_objects,
            members=ordered_members,
            captures=ordered_captures,
            resolved_logical_tree_sha256=evidence_logical_tree_sha256(
                ordered_objects, ordered_members
            ),
        )
        return EvidenceBundle(
            bundle_id=evidence_bundle_content_sha256(content),
            content=content,
        )
    except EvidenceBundleError:
        raise
    except (ValueError, ValidationError) as exc:
        raise EvidenceBundleError("invalid evidence bundle content") from exc


def _is_link_like(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    try:
        file_attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        file_attributes = 0
    return (
        path.is_symlink()
        or bool(is_junction is not None and is_junction())
        or bool(file_attributes & reparse_flag)
    )


class EvidenceBundleReader:
    """Resolve and verify immutable blobs from a caller-supplied SHA-256 CAS root."""

    def __init__(
        self, bundle: EvidenceBundle, object_root: Path, *, expected_bundle_id: str
    ) -> None:
        try:
            validated_bundle = EvidenceBundle.model_validate(
                bundle.model_dump(mode="python")
            )
        except ValidationError as exc:
            raise EvidenceBundleError("invalid evidence bundle content") from exc
        if validated_bundle.bundle_id != expected_bundle_id:
            raise EvidenceBundleError("evidence bundle does not match the trusted bundle ID")
        self.bundle = validated_bundle
        self.object_root = object_root
        self._members = {
            member.logical_path: member for member in validated_bundle.content.members
        }
        self._objects = {item.sha256: item for item in validated_bundle.content.objects}

    @classmethod
    def from_manifest(
        cls, manifest: Path, object_root: Path, *, expected_bundle_id: str
    ) -> EvidenceBundleReader:
        return cls(
            load_evidence_bundle(manifest, expected_bundle_id=expected_bundle_id),
            object_root,
            expected_bundle_id=expected_bundle_id,
        )

    def assert_current(self, *, at: datetime) -> None:
        if at.tzinfo is None or at.utcoffset() is None:
            raise EvidenceBundleError("current time must include a timezone")
        if at < self.bundle.content.created_at:
            raise EvidenceBundleNotYetValidError("evidence bundle has not been assembled yet")
        if at > self.bundle.content.valid_until:
            raise EvidenceBundleExpiredError("evidence bundle has expired")
        if any(
            capture.acquisition is not EvidenceAcquisition.FRESH
            for capture in self.bundle.content.captures
        ):
            raise EvidenceBundleUnverifiedOriginError(
                "inherited evidence origin has not been independently verified"
            )

    def _object_path(self, sha256: str) -> Path:
        root = self.object_root
        if _is_link_like(root):
            raise EvidenceBundleError("evidence object root must not be a link or junction")
        try:
            resolved_root = root.resolve(strict=True)
        except OSError as exc:
            raise EvidenceBundleError("evidence object root does not exist") from exc
        if not resolved_root.is_dir():
            raise EvidenceBundleError("evidence object root is not a directory")

        bucket = root / sha256[:2]
        candidate = bucket / sha256
        if _is_link_like(bucket) or _is_link_like(candidate):
            raise EvidenceBundleError("evidence object path must not use a link or junction")
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(resolved_root)
        except (OSError, ValueError) as exc:
            raise EvidenceBundleError(
                "evidence object path escapes or is missing from the CAS"
            ) from exc
        if not resolved.is_file():
            raise EvidenceBundleError("evidence object is not a regular file")
        return resolved

    def _verify_object(self, item: EvidenceObject) -> bytes:
        path = self._object_path(item.sha256)
        digest = hashlib.sha256()
        size = 0
        data = bytearray()
        try:
            with path.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                    if size > item.size_bytes:
                        raise EvidenceBundleError(
                            "evidence object size does not match its descriptor"
                        )
                    data.extend(chunk)
        except OSError as exc:
            raise EvidenceBundleError("evidence object could not be read") from exc
        if size != item.size_bytes:
            raise EvidenceBundleError("evidence object size does not match its descriptor")
        if digest.hexdigest() != item.sha256:
            raise EvidenceBundleError("evidence object digest does not match its descriptor")
        return bytes(data)

    def resolve(self, logical_path: str) -> ResolvedEvidenceMember:
        member = self._members.get(logical_path)
        if member is None:
            raise EvidenceBundleError("logical evidence member is not declared by the bundle")
        item = self._objects[member.object_sha256]
        return ResolvedEvidenceMember(
            logical_path=member.logical_path,
            role=member.role,
            object_sha256=member.object_sha256,
            data=self._verify_object(item),
        )

    def verify(self) -> tuple[ResolvedEvidenceMember, ...]:
        verified_objects: dict[str, bytes] = {
            item.sha256: self._verify_object(item) for item in self.bundle.content.objects
        }
        return tuple(
            ResolvedEvidenceMember(
                logical_path=member.logical_path,
                role=member.role,
                object_sha256=member.object_sha256,
                data=verified_objects[member.object_sha256],
            )
            for member in self.bundle.content.members
        )
