"""Offline FRESH evidence freezing and trusted Canary profile resolution.

This module never acquires evidence from the network. It only freezes caller-supplied,
pre-sanitized official evidence and snapshot JSON, then resolves a Git-reviewed bundle ID.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, cast
from urllib.parse import urlparse

from pydantic import ValidationError

from sdc.contracts import (
    CANARY_MODEL,
    CANARY_PROVIDER,
    EvidenceAcquisition,
    EvidenceBundle,
    EvidenceCapture,
    EvidenceMember,
    EvidenceObject,
    ProviderCapabilitySnapshot,
    ProviderPricingSnapshot,
    SnapshotStatus,
)
from sdc.evidence import EvidenceBundleError, EvidenceBundleReader, build_evidence_bundle
from sdc.fresh_evidence_registry import (
    FRESH_CANARY_PROFILE,
    REVIEWED_FRESH_EVIDENCE,
    ReviewedFreshEvidence,
)

CAPABILITY_EVIDENCE_PATH: Final = "evidence/capability.pdf"
CAPABILITY_SNAPSHOT_PATH: Final = "snapshots/capability.json"
PRICING_EVIDENCE_PATH: Final = "evidence/pricing.pdf"
PRICING_SNAPSHOT_PATH: Final = "snapshots/pricing.json"
_MAX_SNAPSHOT_BYTES: Final = 256 * 1024
_BUNDLE_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_OFFICIAL_DOC_HOSTS = frozenset({"docs.volcengine.com", "www.volcengine.com"})
_PROTECTED_OUTPUT_COMPONENTS = frozenset(
    {
        "canary",
        "evidence-cas",
        "v02-r2",
        "v02-r3",
        "v02-r4",
        "v02-r5",
        "v02-r6",
        "v02-r6-live",
    }
)
LEGACY_EVIDENCE_BUNDLE_IDS: Final = frozenset(
    {
        "2d33b747367d396f245ddf15187628cbc96936a39ad8cb948282ec87c4c65a8e",
        "07791b67f57c94bc5e5860b74f770317a1b59bd4ea21bfbac9f01613ac11e906",
        "5d3b087154adfe423f7b14190d67a54b35ce3e84eae87dd99ffd6bb8312937ec",
        "8ca336193cd5cd7a5cf0f766f6ae7b482de8def97e63df0b6cca0f95fc278f5b",
        "f91f9aadf10ce0fbfe7a58df9c7c3fbd2f07d1b751b4346d44e19e2026be39d7",
    }
)


def _portable_path_component(part: str) -> str:
    """Normalize the Win32 aliases that can bypass lexical archive guards."""
    trimmed = part.rstrip(" .")
    if trimmed != part:
        raise FreshEvidenceError("evidence paths must not contain trailing dots or spaces")
    return trimmed.casefold()


def _contains_protected_component(path: Path) -> bool:
    return any(
        _portable_path_component(part) in _PROTECTED_OUTPUT_COMPONENTS
        for part in path.parts
    )


def _reject_unc_or_device_path(path: Path) -> None:
    rendered = str(path)
    if rendered.startswith(("\\\\", "//")):
        raise FreshEvidenceError("evidence paths must use a local filesystem path")


class FreshEvidenceError(EvidenceBundleError):
    """Raised when the fixed FRESH Canary evidence profile fails closed."""


@dataclass(frozen=True, slots=True)
class FrozenFreshEvidence:
    bundle: EvidenceBundle
    object_root: Path
    manifest_path: Path
    capability_snapshot_sha256: str
    pricing_snapshot_sha256: str


@dataclass(frozen=True, slots=True)
class FreshCanaryEvidence:
    bundle_id: str
    logical_tree_sha256: str
    valid_until: datetime
    capability: ProviderCapabilitySnapshot
    pricing: ProviderPricingSnapshot
    reviewed_anchor: ReviewedFreshEvidence


def require_trusted_fresh_evidence_anchor(
    bundle_id: str, *, at: datetime | None = None
) -> ReviewedFreshEvidence:
    """Resolve a positive trust anchor without reading a manifest or CAS path."""
    if _BUNDLE_ID_PATTERN.fullmatch(bundle_id) is None:
        raise FreshEvidenceError("trusted evidence bundle ID must be lowercase SHA-256")
    if bundle_id in LEGACY_EVIDENCE_BUNDLE_IDS:
        raise FreshEvidenceError("legacy R2-R6 evidence is permanently ineligible for planning")
    registry_ids = tuple(anchor.bundle_id for anchor in REVIEWED_FRESH_EVIDENCE)
    if len(registry_ids) != len(set(registry_ids)):
        raise FreshEvidenceError("FRESH registry contains a duplicate bundle ID")
    for candidate in REVIEWED_FRESH_EVIDENCE:
        for field, digest in (
            ("bundle_id", candidate.bundle_id),
            ("logical_tree_sha256", candidate.logical_tree_sha256),
            ("capability_snapshot_sha256", candidate.capability_snapshot_sha256),
            ("pricing_snapshot_sha256", candidate.pricing_snapshot_sha256),
        ):
            if _BUNDLE_ID_PATTERN.fullmatch(digest) is None:
                raise FreshEvidenceError(f"FRESH registry {field} is not lowercase SHA-256")
        if candidate.bundle_id in LEGACY_EVIDENCE_BUNDLE_IDS:
            raise FreshEvidenceError("FRESH registry must not contain a legacy bundle ID")
        if candidate.profile != FRESH_CANARY_PROFILE:
            raise FreshEvidenceError("FRESH registry profile is not the approved Canary profile")
        for field, value in (
            ("reviewed_at", candidate.reviewed_at),
            ("valid_until", candidate.valid_until),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise FreshEvidenceError(f"FRESH registry {field} must include a timezone")
        if candidate.reviewed_at > candidate.valid_until:
            raise FreshEvidenceError("FRESH registry review is later than its validity window")
    matching = tuple(anchor for anchor in REVIEWED_FRESH_EVIDENCE if anchor.bundle_id == bundle_id)
    if len(matching) > 1:
        raise FreshEvidenceError("FRESH registry contains a duplicate bundle ID")
    if matching:
        anchor = matching[0]
        if at is not None:
            if at.tzinfo is None or at.utcoffset() is None:
                raise FreshEvidenceError("planning time must include a timezone")
            current = at.astimezone(UTC)
            if current < anchor.reviewed_at.astimezone(UTC):
                raise FreshEvidenceError("FRESH bundle was not reviewed at the planning time")
            if current > anchor.valid_until.astimezone(UTC):
                raise FreshEvidenceError("FRESH registry anchor has expired")
        return anchor
    raise FreshEvidenceError("evidence bundle ID is not in the Git-reviewed FRESH registry")


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FreshEvidenceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise FreshEvidenceError(f"non-finite JSON number is forbidden: {value}")


def _parse_snapshot_bytes[SnapshotT: ProviderCapabilitySnapshot | ProviderPricingSnapshot](
    raw: bytes, model: type[SnapshotT]
) -> SnapshotT:
    if len(raw) > _MAX_SNAPSHOT_BYTES:
        raise FreshEvidenceError("snapshot JSON exceeds the byte limit")
    try:
        text = raw.decode("utf-8")
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_json_constant,
        )
        if not isinstance(payload, dict):
            raise FreshEvidenceError("snapshot JSON must contain one object")
        return cast(SnapshotT, model.model_validate(payload))
    except FreshEvidenceError:
        raise
    except (UnicodeError, ValueError, ValidationError) as exc:
        raise FreshEvidenceError("invalid snapshot JSON") from exc


def _is_link_like(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    try:
        value = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISLNK(value.st_mode)
        or bool(is_junction is not None and is_junction())
        or bool(getattr(value, "st_file_attributes", 0) & reparse_flag)
    )


def _reject_link_components(path: Path) -> None:
    absolute = path.absolute()
    cursor = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        cursor /= part
        if not os.path.lexists(cursor):
            break
        if _is_link_like(cursor):
            raise FreshEvidenceError("evidence paths must not use links or junctions")


def _read_regular_bytes(path: Path, *, limit: int) -> bytes:
    _reject_link_components(path)
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise FreshEvidenceError("evidence input must be a regular file")
            raw = handle.read(limit + 1)
            if len(raw) > limit:
                raise FreshEvidenceError("evidence input exceeds the byte limit")
            after = path.stat()
            if (opened.st_dev, opened.st_ino, opened.st_size) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
            ):
                raise FreshEvidenceError("evidence input changed while it was read")
            return raw
    except FreshEvidenceError:
        raise
    except OSError as exc:
        raise FreshEvidenceError("evidence input could not be read") from exc


def _require_official_snapshot(
    snapshot: ProviderCapabilitySnapshot | ProviderPricingSnapshot,
) -> None:
    if snapshot.status is not SnapshotStatus.CURRENT:
        raise FreshEvidenceError("a FRESH snapshot must be CURRENT when frozen")
    if snapshot.provider != CANARY_PROVIDER or snapshot.model != CANARY_MODEL:
        raise FreshEvidenceError("snapshot does not match the pinned Ark Canary profile")
    parsed = urlparse(snapshot.source_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise FreshEvidenceError("snapshot source URL is invalid") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname not in _OFFICIAL_DOC_HOSTS
        or parsed.netloc != parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
    ):
        raise FreshEvidenceError("snapshot must cite an official Volcengine HTTPS document")
    for field, value in (
        ("source_updated_at", snapshot.source_updated_at),
        ("captured_at", snapshot.captured_at),
        ("valid_until", snapshot.valid_until),
    ):
        if value.tzinfo is None or value.utcoffset() is None:
            raise FreshEvidenceError(f"snapshot {field} must include a timezone")
    if not snapshot.source_updated_at <= snapshot.captured_at <= snapshot.valid_until:
        raise FreshEvidenceError("snapshot evidence timestamps are out of order")


def _evidence_object(data: bytes, media_type: str) -> EvidenceObject:
    return EvidenceObject(
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        media_type=media_type,
    )


def _contract_sha256(
    snapshot: ProviderCapabilitySnapshot | ProviderPricingSnapshot,
) -> str:
    payload = snapshot.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _canonical_snapshot_bytes(
    snapshot: ProviderCapabilitySnapshot | ProviderPricingSnapshot,
) -> bytes:
    canonical = snapshot.model_copy(
        update={
            "source_updated_at": snapshot.source_updated_at.astimezone(UTC),
            "captured_at": snapshot.captured_at.astimezone(UTC),
            "valid_until": snapshot.valid_until.astimezone(UTC),
        }
    )
    return (
        json.dumps(
            canonical.model_dump(mode="json"),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def build_fresh_canary_evidence_bundle(
    *,
    capability_snapshot_bytes: bytes,
    capability_evidence_bytes: bytes,
    pricing_snapshot_bytes: bytes,
    pricing_evidence_bytes: bytes,
) -> tuple[EvidenceBundle, MappingProxyType[str, bytes]]:
    """Build the fixed four-member profile without filesystem or network access."""
    capability = _parse_snapshot_bytes(capability_snapshot_bytes, ProviderCapabilitySnapshot)
    pricing = _parse_snapshot_bytes(pricing_snapshot_bytes, ProviderPricingSnapshot)
    _require_official_snapshot(capability)
    _require_official_snapshot(pricing)
    if capability_evidence_bytes[:5] != b"%PDF-" or pricing_evidence_bytes[:5] != b"%PDF-":
        raise FreshEvidenceError("official capability and pricing evidence must be PDF files")

    capability_snapshot_bytes = _canonical_snapshot_bytes(capability)
    pricing_snapshot_bytes = _canonical_snapshot_bytes(pricing)
    capability = _parse_snapshot_bytes(capability_snapshot_bytes, ProviderCapabilitySnapshot)
    pricing = _parse_snapshot_bytes(pricing_snapshot_bytes, ProviderPricingSnapshot)
    data_by_path = {
        CAPABILITY_EVIDENCE_PATH: capability_evidence_bytes,
        CAPABILITY_SNAPSHOT_PATH: capability_snapshot_bytes,
        PRICING_EVIDENCE_PATH: pricing_evidence_bytes,
        PRICING_SNAPSHOT_PATH: pricing_snapshot_bytes,
    }
    media_by_path = {
        CAPABILITY_EVIDENCE_PATH: "application/pdf",
        CAPABILITY_SNAPSHOT_PATH: "application/json",
        PRICING_EVIDENCE_PATH: "application/pdf",
        PRICING_SNAPSHOT_PATH: "application/json",
    }
    object_by_path = {
        path: _evidence_object(data, media_by_path[path]) for path, data in data_by_path.items()
    }
    if len({item.sha256 for item in object_by_path.values()}) != 4:
        raise FreshEvidenceError("the FRESH profile requires four distinct evidence objects")
    if capability.evidence_sha256 != object_by_path[CAPABILITY_EVIDENCE_PATH].sha256:
        raise FreshEvidenceError("capability snapshot does not bind its evidence PDF")
    if pricing.evidence_sha256 != object_by_path[PRICING_EVIDENCE_PATH].sha256:
        raise FreshEvidenceError("pricing snapshot does not bind its evidence PDF")

    members = (
        EvidenceMember(
            logical_path=CAPABILITY_EVIDENCE_PATH,
            role="capability.evidence",
            object_sha256=object_by_path[CAPABILITY_EVIDENCE_PATH].sha256,
        ),
        EvidenceMember(
            logical_path=CAPABILITY_SNAPSHOT_PATH,
            role="capability.snapshot",
            object_sha256=object_by_path[CAPABILITY_SNAPSHOT_PATH].sha256,
            content_schema_version="1.0.0",
        ),
        EvidenceMember(
            logical_path=PRICING_EVIDENCE_PATH,
            role="pricing.evidence",
            object_sha256=object_by_path[PRICING_EVIDENCE_PATH].sha256,
        ),
        EvidenceMember(
            logical_path=PRICING_SNAPSHOT_PATH,
            role="pricing.snapshot",
            object_sha256=object_by_path[PRICING_SNAPSHOT_PATH].sha256,
            content_schema_version="1.0.0",
        ),
    )
    captures = (
        EvidenceCapture(
            capture_id="capability",
            kind="official-capability",
            source_url=capability.source_url,
            source_updated_at=capability.source_updated_at,
            captured_at=capability.captured_at,
            valid_until=capability.valid_until,
            acquisition=EvidenceAcquisition.FRESH,
            member_paths=(CAPABILITY_EVIDENCE_PATH, CAPABILITY_SNAPSHOT_PATH),
        ),
        EvidenceCapture(
            capture_id="pricing",
            kind="official-pricing",
            source_url=pricing.source_url,
            source_updated_at=pricing.source_updated_at,
            captured_at=pricing.captured_at,
            valid_until=pricing.valid_until,
            acquisition=EvidenceAcquisition.FRESH,
            member_paths=(PRICING_EVIDENCE_PATH, PRICING_SNAPSHOT_PATH),
        ),
    )
    bundle = build_evidence_bundle(
        created_at=max(capability.captured_at, pricing.captured_at),
        objects=object_by_path.values(),
        members=members,
        captures=captures,
        predecessor_bundle_id=None,
    )
    return bundle, MappingProxyType(data_by_path)


def _reject_protected_output(output_root: Path) -> None:
    absolute = output_root.absolute()
    _reject_unc_or_device_path(absolute)
    if _contains_protected_component(absolute):
        raise FreshEvidenceError("FRESH evidence output must be separate from Canary archives")
    _reject_link_components(absolute)
    cursor = absolute
    missing: list[str] = []
    while not os.path.lexists(cursor):
        missing.append(cursor.name)
        parent = cursor.parent
        if parent == cursor:
            raise FreshEvidenceError("FRESH evidence output has no reachable local parent")
        cursor = parent
    try:
        resolved_candidate = cursor.resolve(strict=True).joinpath(*reversed(missing))
    except OSError as exc:
        raise FreshEvidenceError("FRESH evidence output parent could not be resolved") from exc
    if _contains_protected_component(resolved_candidate):
        raise FreshEvidenceError("FRESH evidence output resolves into a protected archive")


def _reject_protected_source(path: Path) -> None:
    absolute = path.absolute()
    _reject_unc_or_device_path(absolute)
    if _contains_protected_component(absolute):
        raise FreshEvidenceError("legacy or live Canary paths cannot be relabeled as FRESH")
    _reject_link_components(absolute)
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise FreshEvidenceError("FRESH evidence source could not be resolved") from exc
    if _contains_protected_component(resolved):
        raise FreshEvidenceError("legacy or live Canary paths cannot be relabeled as FRESH")


def _ensure_directory(path: Path) -> None:
    _reject_link_components(path)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FreshEvidenceError("evidence output directory could not be created") from exc
    _reject_link_components(path)
    if not path.is_dir():
        raise FreshEvidenceError("evidence output path is not a directory")


def _verify_existing_blob(path: Path, expected: bytes) -> None:
    actual = _read_regular_bytes(path, limit=len(expected))
    if actual != expected:
        raise FreshEvidenceError("an existing CAS path does not match its expected bytes")


def _publish_blob_no_replace(path: Path, data: bytes) -> None:
    if os.path.lexists(path):
        _verify_existing_blob(path, data)
        return
    _ensure_directory(path.parent)
    handle_id, temporary_name = tempfile.mkstemp(prefix=".fresh-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle_id, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        staged_digest = hashlib.sha256(_read_regular_bytes(temporary, limit=len(data))).digest()
        if staged_digest != hashlib.sha256(data).digest():
            raise FreshEvidenceError("staged evidence bytes failed verification")
        try:
            os.link(temporary, path)
        except FileExistsError:
            _verify_existing_blob(path, data)
    except FreshEvidenceError:
        raise
    except OSError as exc:
        raise FreshEvidenceError("evidence CAS publication failed") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def freeze_fresh_canary_evidence(
    *,
    capability_snapshot_path: Path,
    capability_evidence_path: Path,
    pricing_snapshot_path: Path,
    pricing_evidence_path: Path,
    output_root: Path,
) -> FrozenFreshEvidence:
    """Freeze a candidate bundle. This does not add it to the trusted planner registry."""
    for path in (
        capability_snapshot_path,
        capability_evidence_path,
        pricing_snapshot_path,
        pricing_evidence_path,
    ):
        _reject_protected_source(path)
    capability_snapshot_bytes = _read_regular_bytes(
        capability_snapshot_path, limit=_MAX_SNAPSHOT_BYTES
    )
    pricing_snapshot_bytes = _read_regular_bytes(pricing_snapshot_path, limit=_MAX_SNAPSHOT_BYTES)
    capability_evidence_bytes = _read_regular_bytes(
        capability_evidence_path, limit=64 * 1024 * 1024
    )
    pricing_evidence_bytes = _read_regular_bytes(pricing_evidence_path, limit=64 * 1024 * 1024)
    bundle, data_by_path = build_fresh_canary_evidence_bundle(
        capability_snapshot_bytes=capability_snapshot_bytes,
        capability_evidence_bytes=capability_evidence_bytes,
        pricing_snapshot_bytes=pricing_snapshot_bytes,
        pricing_evidence_bytes=pricing_evidence_bytes,
    )
    frozen_at = datetime.now(UTC)
    if not bundle.content.created_at <= frozen_at <= bundle.content.valid_until:
        raise FreshEvidenceError("FRESH evidence is not current at freeze time")
    _reject_protected_output(output_root)
    object_root = output_root / "objects"
    manifest_root = output_root / "bundles"
    _ensure_directory(object_root)
    _ensure_directory(manifest_root)

    member_by_path = {member.logical_path: member for member in bundle.content.members}
    for logical_path, data in data_by_path.items():
        digest = member_by_path[logical_path].object_sha256
        _publish_blob_no_replace(object_root / digest[:2] / digest, data)
    EvidenceBundleReader(bundle, object_root, expected_bundle_id=bundle.bundle_id).verify()

    manifest_path = manifest_root / f"{bundle.bundle_id}.json"
    manifest_bytes = (
        json.dumps(
            bundle.model_dump(mode="json"),
            sort_keys=True,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        + b"\n"
    )
    _publish_blob_no_replace(manifest_path, manifest_bytes)
    capability = _parse_snapshot_bytes(
        data_by_path[CAPABILITY_SNAPSHOT_PATH], ProviderCapabilitySnapshot
    )
    pricing = _parse_snapshot_bytes(data_by_path[PRICING_SNAPSHOT_PATH], ProviderPricingSnapshot)
    return FrozenFreshEvidence(
        bundle=bundle,
        object_root=object_root,
        manifest_path=manifest_path,
        capability_snapshot_sha256=_contract_sha256(capability),
        pricing_snapshot_sha256=_contract_sha256(pricing),
    )


def load_trusted_fresh_canary_evidence(
    *,
    manifest_path: Path,
    object_root: Path,
    expected_bundle_id: str,
    at: datetime,
) -> FreshCanaryEvidence:
    """Resolve exactly one approved FRESH profile using bytes returned by one CAS verification."""
    anchor = require_trusted_fresh_evidence_anchor(expected_bundle_id, at=at)
    store_root = object_root.parent.absolute()
    _reject_unc_or_device_path(store_root)
    expected_manifest = store_root / "bundles" / f"{expected_bundle_id}.json"
    if (
        object_root.absolute() != store_root / "objects"
        or manifest_path.absolute() != expected_manifest
    ):
        raise FreshEvidenceError("FRESH store must use the fixed objects/bundles layout")
    if _contains_protected_component(store_root):
        raise FreshEvidenceError("reviewed FRESH evidence must not resolve from a legacy path")
    _reject_link_components(manifest_path)
    _reject_link_components(object_root)
    try:
        resolved_store_root = store_root.resolve(strict=True)
    except OSError as exc:
        raise FreshEvidenceError("reviewed FRESH evidence store does not exist") from exc
    if _contains_protected_component(resolved_store_root):
        raise FreshEvidenceError("reviewed FRESH evidence resolves from a legacy path")
    reader = EvidenceBundleReader.from_manifest(
        manifest_path, object_root, expected_bundle_id=expected_bundle_id
    )
    resolved = reader.verify()
    reader.assert_current(at=at)
    bundle = reader.bundle
    if bundle.content.predecessor_bundle_id is not None:
        raise FreshEvidenceError("the FRESH Canary profile must not inherit a predecessor")
    if anchor.reviewed_at.astimezone(UTC) < bundle.content.created_at:
        raise FreshEvidenceError("FRESH registry review predates the evidence bundle")

    expected_members = (
        (CAPABILITY_EVIDENCE_PATH, "capability.evidence", None, "application/pdf"),
        (PRICING_EVIDENCE_PATH, "pricing.evidence", None, "application/pdf"),
        (CAPABILITY_SNAPSHOT_PATH, "capability.snapshot", "1.0.0", "application/json"),
        (PRICING_SNAPSHOT_PATH, "pricing.snapshot", "1.0.0", "application/json"),
    )
    object_by_hash = {item.sha256: item for item in bundle.content.objects}
    actual_members = tuple(
        (
            member.logical_path,
            member.role,
            member.content_schema_version,
            object_by_hash[member.object_sha256].media_type,
        )
        for member in bundle.content.members
    )
    if actual_members != expected_members or len(bundle.content.objects) != 4:
        raise FreshEvidenceError("evidence bundle does not match the exact Canary profile")
    expected_captures = (
        (
            "capability",
            "official-capability",
            (CAPABILITY_EVIDENCE_PATH, CAPABILITY_SNAPSHOT_PATH),
        ),
        (
            "pricing",
            "official-pricing",
            (PRICING_EVIDENCE_PATH, PRICING_SNAPSHOT_PATH),
        ),
    )
    actual_captures = tuple(
        (capture.capture_id, capture.kind, capture.member_paths)
        for capture in bundle.content.captures
    )
    if actual_captures != expected_captures or any(
        capture.acquisition is not EvidenceAcquisition.FRESH for capture in bundle.content.captures
    ):
        raise FreshEvidenceError("evidence bundle capture profile is not exact and all-FRESH")

    resolved_by_path = {member.logical_path: member for member in resolved}
    if (
        resolved_by_path[CAPABILITY_EVIDENCE_PATH].data[:5] != b"%PDF-"
        or resolved_by_path[PRICING_EVIDENCE_PATH].data[:5] != b"%PDF-"
    ):
        raise FreshEvidenceError("verified official evidence is not PDF content")
    capability = _parse_snapshot_bytes(
        resolved_by_path[CAPABILITY_SNAPSHOT_PATH].data,
        ProviderCapabilitySnapshot,
    )
    pricing = _parse_snapshot_bytes(
        resolved_by_path[PRICING_SNAPSHOT_PATH].data,
        ProviderPricingSnapshot,
    )
    _require_official_snapshot(capability)
    _require_official_snapshot(pricing)
    capability_capture, pricing_capture = bundle.content.captures
    for snapshot, capture, evidence_path in (
        (capability, capability_capture, CAPABILITY_EVIDENCE_PATH),
        (pricing, pricing_capture, PRICING_EVIDENCE_PATH),
    ):
        if snapshot.evidence_sha256 != resolved_by_path[evidence_path].object_sha256:
            raise FreshEvidenceError("snapshot evidence digest is not in the verified closure")
        if (
            capture.source_url != snapshot.source_url
            or capture.source_updated_at != snapshot.source_updated_at.astimezone(UTC)
            or capture.captured_at != snapshot.captured_at.astimezone(UTC)
            or capture.valid_until != snapshot.valid_until.astimezone(UTC)
        ):
            raise FreshEvidenceError("snapshot provenance does not match its bundle capture")
    if capability.provider != pricing.provider or capability.model != pricing.model:
        raise FreshEvidenceError("capability and pricing snapshots do not share one profile")
    if (
        bundle.content.resolved_logical_tree_sha256 != anchor.logical_tree_sha256
        or _contract_sha256(capability) != anchor.capability_snapshot_sha256
        or _contract_sha256(pricing) != anchor.pricing_snapshot_sha256
        or bundle.content.valid_until != anchor.valid_until.astimezone(UTC)
    ):
        raise FreshEvidenceError("FRESH bundle does not match its Git-reviewed anchor")
    return FreshCanaryEvidence(
        bundle_id=bundle.bundle_id,
        logical_tree_sha256=bundle.content.resolved_logical_tree_sha256,
        valid_until=bundle.content.valid_until,
        capability=capability,
        pricing=pricing,
        reviewed_anchor=anchor,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Freeze pre-sanitized execution-day evidence without network access"
    )
    parser.add_argument("--capability-snapshot", type=Path, required=True)
    parser.add_argument("--capability-evidence", type=Path, required=True)
    parser.add_argument("--pricing-snapshot", type=Path, required=True)
    parser.add_argument("--pricing-evidence", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(".artifacts/evidence-current/v1"),
    )
    args = parser.parse_args(argv)
    frozen = freeze_fresh_canary_evidence(
        capability_snapshot_path=args.capability_snapshot,
        capability_evidence_path=args.capability_evidence,
        pricing_snapshot_path=args.pricing_snapshot,
        pricing_evidence_path=args.pricing_evidence,
        output_root=args.output_root,
    )
    print(
        json.dumps(
            {
                "mode": "candidate-only-not-trusted",
                "bundle_id": frozen.bundle.bundle_id,
                "logical_tree_sha256": frozen.bundle.content.resolved_logical_tree_sha256,
                "capability_snapshot_sha256": frozen.capability_snapshot_sha256,
                "pricing_snapshot_sha256": frozen.pricing_snapshot_sha256,
                "manifest": str(frozen.manifest_path),
                "object_root": str(frozen.object_root),
                "valid_until": frozen.bundle.content.valid_until.isoformat(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
