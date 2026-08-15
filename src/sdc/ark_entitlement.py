"""Offline candidate freezing and trusted loading for Ark Canary entitlement evidence.

This module never acquires entitlement evidence. It accepts two explicit, sanitized local
files, freezes a candidate in an append-only CAS, and resolves only bundle IDs present in the
source-controlled positive registry. A frozen candidate is not an authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, cast
from unicodedata import normalize

from pydantic import ValidationError
from pypdf import PdfReader
from pypdf.generic import IndirectObject

from sdc.ark_entitlement_registry import (
    ARK_CANARY_ENTITLEMENT_PROFILE,
    REVIEWED_ARK_ENTITLEMENT_EVIDENCE,
    ReviewedArkEntitlementEvidence,
    reviewed_ark_entitlement_anchor_sha256,
)
from sdc.contracts import (
    ARK_CANARY_ENTITLEMENT_SOURCE_URL,
    ARK_CANARY_OPERATION,
    ARK_CANARY_REGION,
    CANARY_MODEL,
    CANARY_PROVIDER,
    ArkCanaryEntitlementSnapshot,
    EvidenceAcquisition,
    EvidenceBundle,
    EvidenceCapture,
    EvidenceMember,
    EvidenceObject,
)
from sdc.evidence import EvidenceBundleError, EvidenceBundleReader, build_evidence_bundle

ENTITLEMENT_EVIDENCE_PATH: Final = "evidence/entitlement.pdf"
ENTITLEMENT_SNAPSHOT_PATH: Final = "snapshots/entitlement.json"
ENTITLEMENT_SOURCE_URL: Final = ARK_CANARY_ENTITLEMENT_SOURCE_URL
ENTITLEMENT_REGION: Final = ARK_CANARY_REGION
ENTITLEMENT_OPERATION: Final = ARK_CANARY_OPERATION
MAX_ENTITLEMENT_PDF_BYTES: Final = 16 * 1024 * 1024
MAX_ENTITLEMENT_SNAPSHOT_BYTES: Final = 64 * 1024

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,255}$")
_ACCOUNT_SCOPE_DOMAIN = b"sdc:volcengine-account-scope:v1\0"
_CREDENTIAL_BINDING_DOMAIN = b"sdc:ark-credential-binding:v1\0"
_PROTECTED_SOURCE_COMPONENTS = frozenset(
    {
        "canary",
        "entitlement-current",
        "evidence-cas",
        "evidence-current",
        "v02-r2",
        "v02-r3",
        "v02-r4",
        "v02-r5",
        "v02-r6",
        "v02-r6-live",
    }
)
_PROTECTED_OUTPUT_COMPONENTS = _PROTECTED_SOURCE_COMPONENTS - {"entitlement-current"}
_WINDOWS_RESERVED_STEMS = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
    | {f"com{index}" for index in "¹²³"}
    | {f"lpt{index}" for index in "¹²³"}
)
_ACTIVE_PDF_KEYS = frozenset(
    {
        "/A",
        "/AA",
        "/AcroForm",
        "/AF",
        "/Annots",
        "/3D",
        "/EmbeddedFiles",
        "/EF",
        "/JavaScript",
        "/JS",
        "/Launch",
        "/Movie",
        "/Names",
        "/OpenAction",
        "/Rendition",
        "/RichMedia",
        "/Sound",
        "/SubmitForm",
        "/Trans",
        "/ImportData",
        "/URI",
        "/GoToR",
        "/GoToE",
        "/XFA",
    }
)
_ACTIVE_PDF_VALUES = frozenset(
    {
        "/Action",
        "/3D",
        "/EmbeddedFile",
        "/FileAttachment",
        "/Filespec",
        "/JavaScript",
        "/Launch",
        "/Movie",
        "/Rendition",
        "/RichMedia",
        "/Screen",
        "/Sound",
        "/SubmitForm",
        "/ImportData",
        "/URI",
        "/Widget",
        "/GoToR",
        "/GoToE",
    }
)
_MAX_PDF_GRAPH_NODES = 50_000
_MAX_PDF_GRAPH_DEPTH = 64
_MAX_ENTITLEMENT_PAGES = 16
_PDF_WHITESPACE = b"\x00\x09\x0a\x0c\x0d\x20"
_FINAL_PDF_TRAILER = re.compile(
    rb"startxref[\x00\x09\x0a\x0c\x0d\x20]+[0-9]+"
    rb"[\x00\x09\x0a\x0c\x0d\x20]+%%EOF$"
)


class ArkEntitlementError(EvidenceBundleError):
    """Raised when entitlement evidence or its trust binding fails closed."""


@dataclass(frozen=True, slots=True)
class FrozenArkEntitlement:
    """A locally frozen candidate. This value conveys no trust or live authority."""

    bundle: EvidenceBundle
    object_root: Path
    manifest_path: Path
    snapshot_contract_sha256: str
    raw_evidence_sha256: str


@dataclass(frozen=True, slots=True, init=False)
class _TrustedArkEntitlement:
    """Opaque result produced only by the supported trusted loader."""

    bundle_id: str
    logical_tree_sha256: str
    snapshot_contract_sha256: str
    raw_evidence_sha256: str
    entitlement_anchor_sha256: str
    valid_until: datetime
    snapshot: ArkCanaryEntitlementSnapshot

    @classmethod
    def _from_verified(
        cls,
        *,
        bundle_id: str,
        logical_tree_sha256: str,
        snapshot_contract_sha256: str,
        raw_evidence_sha256: str,
        entitlement_anchor_sha256: str,
        valid_until: datetime,
        snapshot: ArkCanaryEntitlementSnapshot,
    ) -> _TrustedArkEntitlement:
        value = object.__new__(cls)
        for field, item in (
            ("bundle_id", bundle_id),
            ("logical_tree_sha256", logical_tree_sha256),
            ("snapshot_contract_sha256", snapshot_contract_sha256),
            ("raw_evidence_sha256", raw_evidence_sha256),
            ("entitlement_anchor_sha256", entitlement_anchor_sha256),
            ("valid_until", valid_until),
            ("snapshot", snapshot),
        ):
            object.__setattr__(value, field, item)
        return value


def _canonical_json_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_private_identifier(value: str | None, *, optional: bool) -> str | None:
    if value is None:
        if optional:
            return None
        raise ArkEntitlementError("required private scope metadata is missing")
    if (
        not value
        or normalize("NFC", value) != value
        or _SAFE_IDENTIFIER_PATTERN.fullmatch(value) is None
        or any(ord(character) <= 32 or ord(character) == 127 for character in value)
    ):
        raise ArkEntitlementError("private scope metadata is not canonical")
    return value


def _salted_domain_digest(domain: bytes, payload: Mapping[str, object], salt: bytes) -> str:
    if not isinstance(salt, bytes) or len(salt) != 32 or not any(salt):
        raise ArkEntitlementError("a reviewer-controlled non-zero 32-byte salt is required")
    return hashlib.sha256(domain + _canonical_json_bytes(payload) + b"\0" + salt).hexdigest()


def account_scope_sha256(
    *,
    account_id: str,
    subaccount_id: str | None,
    project_id: str | None,
    private_salt: bytes,
) -> str:
    """Derive a pseudonymous account-scope digest without retaining its input or salt."""
    payload: dict[str, object] = {
        "account_id": _canonical_private_identifier(account_id, optional=False),
        "project_id": _canonical_private_identifier(project_id, optional=True),
        "subaccount_id": _canonical_private_identifier(subaccount_id, optional=True),
    }
    return _salted_domain_digest(_ACCOUNT_SCOPE_DOMAIN, payload, private_salt)


def credential_binding_sha256(
    *,
    secret_store: str,
    resource_locator: str,
    immutable_version: str,
    private_salt: bytes,
) -> str:
    """Derive a pseudonymous credential-metadata digest; the Key value is never accepted."""
    payload: dict[str, object] = {
        "immutable_version": _canonical_private_identifier(immutable_version, optional=False),
        "resource_locator": _canonical_private_identifier(resource_locator, optional=False),
        "secret_store": _canonical_private_identifier(secret_store, optional=False),
    }
    return _salted_domain_digest(_CREDENTIAL_BINDING_DOMAIN, payload, private_salt)


def ark_entitlement_snapshot_contract_sha256(
    snapshot: ArkCanaryEntitlementSnapshot,
) -> str:
    """Hash the normalized public snapshot contract (not its JSON object blob)."""
    validated = ArkCanaryEntitlementSnapshot.model_validate(snapshot.model_dump(mode="python"))
    return hashlib.sha256(_canonical_json_bytes(validated.model_dump(mode="json"))).hexdigest()


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArkEntitlementError("snapshot JSON contains a duplicate key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise ArkEntitlementError("snapshot JSON contains a non-finite number")


def _parse_snapshot_bytes(raw: bytes) -> ArkCanaryEntitlementSnapshot:
    if len(raw) > MAX_ENTITLEMENT_SNAPSHOT_BYTES:
        raise ArkEntitlementError("entitlement snapshot exceeds the 64 KiB limit")
    try:
        text = raw.decode("utf-8")
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_json_constant,
        )
        if not isinstance(payload, dict):
            raise ArkEntitlementError("entitlement snapshot must contain one JSON object")
        return ArkCanaryEntitlementSnapshot.model_validate(payload)
    except ArkEntitlementError:
        raise
    except (UnicodeError, ValueError, ValidationError) as exc:
        raise ArkEntitlementError("invalid entitlement snapshot JSON") from exc


def _canonical_snapshot_bytes(snapshot: ArkCanaryEntitlementSnapshot) -> bytes:
    return _canonical_json_bytes(snapshot.model_dump(mode="json"))


def _walk_pdf_object_graph(root: object) -> None:
    pending: list[tuple[object, int]] = [(root, 0)]
    indirect_seen: set[tuple[int, int]] = set()
    direct_seen: set[int] = set()
    nodes = 0
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > _MAX_PDF_GRAPH_NODES or depth > _MAX_PDF_GRAPH_DEPTH:
            raise ArkEntitlementError("entitlement PDF object graph exceeds safety limits")
        if isinstance(current, IndirectObject):
            indirect_identity = (current.idnum, current.generation)
            if indirect_identity in indirect_seen:
                continue
            indirect_seen.add(indirect_identity)
            try:
                pending.append((current.get_object(), depth + 1))
            except Exception as exc:
                raise ArkEntitlementError("entitlement PDF contains an invalid object") from exc
            continue
        if isinstance(current, Mapping):
            direct_identity = id(current)
            if direct_identity in direct_seen:
                continue
            direct_seen.add(direct_identity)
            for key, value in current.items():
                rendered_key = str(key)
                if rendered_key in _ACTIVE_PDF_KEYS or str(value) in _ACTIVE_PDF_VALUES:
                    raise ArkEntitlementError(
                        "entitlement PDF contains active or interactive content"
                    )
                pending.append((value, depth + 1))
            continue
        if isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            sequence_identity = id(current)
            if sequence_identity in direct_seen:
                continue
            direct_seen.add(sequence_identity)
            pending.extend((item, depth + 1) for item in current)


def _validate_entitlement_pdf(raw: bytes) -> None:
    if len(raw) > MAX_ENTITLEMENT_PDF_BYTES:
        raise ArkEntitlementError("entitlement PDF exceeds the 16 MiB limit")
    if not raw.startswith(b"%PDF-"):
        raise ArkEntitlementError("entitlement evidence must be a PDF")
    stripped = raw.rstrip(_PDF_WHITESPACE)
    if (
        raw.count(b"%%EOF") != 1
        or raw.count(b"startxref") != 1
        or _FINAL_PDF_TRAILER.search(stripped) is None
    ):
        raise ArkEntitlementError(
            "entitlement PDF must be one complete revision with no trailing payload"
        )
    try:
        reader = PdfReader(BytesIO(raw), strict=True, root_object_recovery_limit=0)
        if reader.is_encrypted:
            raise ArkEntitlementError("encrypted entitlement PDFs are forbidden")
        page_count = len(reader.pages)
        if page_count == 0:
            raise ArkEntitlementError("entitlement PDF must contain at least one page")
        if page_count > _MAX_ENTITLEMENT_PAGES:
            raise ArkEntitlementError("entitlement PDF exceeds the page-count limit")
        _walk_pdf_object_graph(reader.trailer)
    except ArkEntitlementError:
        raise
    except Exception as exc:
        raise ArkEntitlementError("entitlement PDF failed structural validation") from exc


def _evidence_object(data: bytes, media_type: str) -> EvidenceObject:
    return EvidenceObject(
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        media_type=media_type,
    )


def build_ark_canary_entitlement_bundle(
    *, snapshot_bytes: bytes, evidence_pdf_bytes: bytes
) -> tuple[EvidenceBundle, MappingProxyType[str, bytes]]:
    """Build the exact two-member candidate entirely in memory and without network access."""
    snapshot = _parse_snapshot_bytes(snapshot_bytes)
    _validate_entitlement_pdf(evidence_pdf_bytes)
    canonical_snapshot = _canonical_snapshot_bytes(snapshot)
    if len(canonical_snapshot) > MAX_ENTITLEMENT_SNAPSHOT_BYTES:
        raise ArkEntitlementError("canonical entitlement snapshot exceeds the 64 KiB limit")
    snapshot = _parse_snapshot_bytes(canonical_snapshot)
    if snapshot.source_url != ENTITLEMENT_SOURCE_URL:
        raise ArkEntitlementError("entitlement snapshot does not cite the exact console route")

    data_by_path = {
        ENTITLEMENT_EVIDENCE_PATH: evidence_pdf_bytes,
        ENTITLEMENT_SNAPSHOT_PATH: canonical_snapshot,
    }
    object_by_path = {
        ENTITLEMENT_EVIDENCE_PATH: _evidence_object(evidence_pdf_bytes, "application/pdf"),
        ENTITLEMENT_SNAPSHOT_PATH: _evidence_object(canonical_snapshot, "application/json"),
    }
    if len({item.sha256 for item in object_by_path.values()}) != 2:
        raise ArkEntitlementError("the entitlement profile requires two distinct objects")
    if snapshot.evidence_sha256 != object_by_path[ENTITLEMENT_EVIDENCE_PATH].sha256:
        raise ArkEntitlementError("entitlement snapshot does not bind its evidence PDF")

    members = (
        EvidenceMember(
            logical_path=ENTITLEMENT_EVIDENCE_PATH,
            role="entitlement.evidence",
            object_sha256=object_by_path[ENTITLEMENT_EVIDENCE_PATH].sha256,
        ),
        EvidenceMember(
            logical_path=ENTITLEMENT_SNAPSHOT_PATH,
            role="entitlement.snapshot",
            object_sha256=object_by_path[ENTITLEMENT_SNAPSHOT_PATH].sha256,
            content_schema_version="1.0.0",
        ),
    )
    capture = EvidenceCapture(
        capture_id="entitlement",
        kind="official-console-entitlement",
        source_url=snapshot.source_url,
        source_updated_at=None,
        captured_at=snapshot.captured_at,
        valid_until=snapshot.valid_until,
        acquisition=EvidenceAcquisition.FRESH,
        member_paths=(ENTITLEMENT_EVIDENCE_PATH, ENTITLEMENT_SNAPSHOT_PATH),
    )
    bundle = build_evidence_bundle(
        created_at=snapshot.captured_at,
        objects=object_by_path.values(),
        members=members,
        captures=(capture,),
        predecessor_bundle_id=None,
    )
    return bundle, MappingProxyType(data_by_path)


def _portable_component(part: str) -> str:
    trimmed = part.rstrip(" .")
    if trimmed != part:
        raise ArkEntitlementError("entitlement paths contain a Win32 alias")
    if any(character in '<>:"|?*' for character in part) or any(
        ord(character) < 32 or ord(character) == 127 for character in part
    ):
        raise ArkEntitlementError("entitlement paths contain a non-portable component")
    if part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_STEMS:
        raise ArkEntitlementError("entitlement paths contain a reserved device name")
    return trimmed.casefold()


def _contains_component(path: Path, protected: frozenset[str]) -> bool:
    parts = path.parts[1:] if path.anchor else path.parts
    return any(_portable_component(part) in protected for part in parts)


def _reject_unc_device_or_relative_drive(path: Path) -> None:
    rendered = str(path)
    if rendered.startswith(("\\\\", "//", "\\\\?\\", "\\\\.\\")):
        raise ArkEntitlementError("entitlement paths must use a local filesystem")
    if path.drive and not path.root:
        raise ArkEntitlementError("drive-relative entitlement paths are forbidden")
    if os.name == "nt" and path.drive and _windows_drive_type(path.anchor) in {0, 1, 4}:
        raise ArkEntitlementError(
            "mapped network drives or unverified drive types are forbidden for entitlement paths"
        )


def _windows_drive_type(anchor: str) -> int:
    """Return Win32 GetDriveTypeW without resolving or reading a path."""
    if os.name != "nt":
        return 3
    try:
        import ctypes

        kernel32 = cast(Any, ctypes).windll.kernel32
        return int(kernel32.GetDriveTypeW(anchor))
    except (AttributeError, OSError) as exc:
        raise ArkEntitlementError("entitlement drive type could not be verified") from exc


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
            raise ArkEntitlementError("entitlement paths must not use links or junctions")


def _resolved_candidate(path: Path) -> Path:
    cursor = path.absolute()
    missing: list[str] = []
    while not os.path.lexists(cursor):
        missing.append(cursor.name)
        parent = cursor.parent
        if parent == cursor:
            raise ArkEntitlementError("entitlement path has no reachable local parent")
        cursor = parent
    try:
        return cursor.resolve(strict=True).joinpath(*reversed(missing))
    except OSError as exc:
        raise ArkEntitlementError("entitlement path could not be resolved") from exc


def _validate_path_policy(path: Path, *, protected: frozenset[str], must_exist: bool) -> None:
    _reject_unc_device_or_relative_drive(path)
    if any(part == ".." for part in path.parts):
        raise ArkEntitlementError("entitlement paths must not contain parent traversal")
    if _contains_component(path, protected):
        raise ArkEntitlementError("entitlement path overlaps a protected archive")
    absolute = path.absolute()
    _reject_unc_device_or_relative_drive(absolute)
    if _contains_component(absolute, protected):
        raise ArkEntitlementError("entitlement path overlaps a protected archive")
    _reject_link_components(absolute)
    resolved = _resolved_candidate(absolute)
    _reject_unc_device_or_relative_drive(resolved)
    if _contains_component(resolved, protected):
        raise ArkEntitlementError("entitlement path resolves into a protected archive")
    if must_exist and not os.path.lexists(absolute):
        raise ArkEntitlementError("entitlement input does not exist")


def _read_regular_bytes(path: Path, *, limit: int, reject_hardlinks: bool = False) -> bytes:
    _reject_link_components(path)
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise ArkEntitlementError("entitlement input must be a regular file")
            if reject_hardlinks and opened.st_nlink != 1:
                raise ArkEntitlementError("entitlement input must not be a hard link")
            raw = handle.read(limit + 1)
            if len(raw) > limit:
                raise ArkEntitlementError("entitlement input exceeds its byte limit")
            after = path.stat()
            if (
                opened.st_dev,
                opened.st_ino,
                opened.st_size,
                opened.st_mtime_ns,
            ) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ):
                raise ArkEntitlementError("entitlement input changed while it was read")
            _reject_link_components(path)
            return raw
    except ArkEntitlementError:
        raise
    except OSError as exc:
        raise ArkEntitlementError("entitlement input could not be read") from exc


def _ensure_directory(path: Path) -> None:
    _reject_link_components(path)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ArkEntitlementError("entitlement output directory could not be created") from exc
    _reject_link_components(path)
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ArkEntitlementError("entitlement output directory is unavailable") from exc
    if not stat.S_ISDIR(mode):
        raise ArkEntitlementError("entitlement output path is not a directory")


def _verify_existing_blob(path: Path, expected: bytes) -> None:
    actual = _read_regular_bytes(path, limit=len(expected))
    if actual != expected:
        raise ArkEntitlementError("an existing entitlement CAS object conflicts")


def _publish_blob_no_replace(path: Path, data: bytes) -> None:
    if os.path.lexists(path):
        _verify_existing_blob(path, data)
        return
    _ensure_directory(path.parent)
    handle_id, temporary_name = tempfile.mkstemp(prefix=".entitlement-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle_id, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _verify_existing_blob(temporary, data)
        try:
            os.link(temporary, path)
        except FileExistsError:
            _verify_existing_blob(path, data)
        _verify_existing_blob(path, data)
    except ArkEntitlementError:
        raise
    except OSError as exc:
        raise ArkEntitlementError("entitlement CAS publication failed") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _exclusive_current(
    *, current: datetime, created_at: datetime, valid_until: datetime, label: str
) -> None:
    if current.tzinfo is None or current.utcoffset() is None:
        raise ArkEntitlementError(f"{label} time must include a timezone")
    normalized = current.astimezone(UTC)
    if normalized < created_at.astimezone(UTC):
        raise ArkEntitlementError(f"{label} precedes the entitlement capture")
    if normalized >= valid_until.astimezone(UTC):
        raise ArkEntitlementError(f"{label} is outside the entitlement validity window")


def freeze_ark_canary_entitlement_candidate(
    *, snapshot_path: Path, evidence_pdf_path: Path, output_root: Path
) -> FrozenArkEntitlement:
    """Freeze a candidate. This never reads or modifies the positive registry."""
    _validate_path_policy(snapshot_path, protected=_PROTECTED_SOURCE_COMPONENTS, must_exist=True)
    _validate_path_policy(
        evidence_pdf_path, protected=_PROTECTED_SOURCE_COMPONENTS, must_exist=True
    )
    snapshot_bytes = _read_regular_bytes(
        snapshot_path,
        limit=MAX_ENTITLEMENT_SNAPSHOT_BYTES,
        reject_hardlinks=True,
    )
    evidence_pdf_bytes = _read_regular_bytes(
        evidence_pdf_path,
        limit=MAX_ENTITLEMENT_PDF_BYTES,
        reject_hardlinks=True,
    )
    bundle, data_by_path = build_ark_canary_entitlement_bundle(
        snapshot_bytes=snapshot_bytes,
        evidence_pdf_bytes=evidence_pdf_bytes,
    )
    _exclusive_current(
        current=datetime.now(UTC),
        created_at=bundle.content.created_at,
        valid_until=bundle.content.valid_until,
        label="freeze",
    )
    _validate_path_policy(output_root, protected=_PROTECTED_OUTPUT_COMPONENTS, must_exist=False)
    object_root = output_root / "objects"
    manifest_root = output_root / "bundles"
    _ensure_directory(object_root)
    _ensure_directory(manifest_root)

    member_by_path = {member.logical_path: member for member in bundle.content.members}
    for logical_path, data in data_by_path.items():
        digest = member_by_path[logical_path].object_sha256
        _publish_blob_no_replace(object_root / digest[:2] / digest, data)
    EvidenceBundleReader(bundle, object_root, expected_bundle_id=bundle.bundle_id).verify()

    # Do not publish a trusted-looking manifest if validation/writes crossed the exclusive end.
    _exclusive_current(
        current=datetime.now(UTC),
        created_at=bundle.content.created_at,
        valid_until=bundle.content.valid_until,
        label="freeze completion",
    )

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
    reader = EvidenceBundleReader.from_manifest(
        manifest_path, object_root, expected_bundle_id=bundle.bundle_id
    )
    reader.verify()
    snapshot = _parse_snapshot_bytes(data_by_path[ENTITLEMENT_SNAPSHOT_PATH])
    return FrozenArkEntitlement(
        bundle=bundle,
        object_root=object_root,
        manifest_path=manifest_path,
        snapshot_contract_sha256=ark_entitlement_snapshot_contract_sha256(snapshot),
        raw_evidence_sha256=hashlib.sha256(evidence_pdf_bytes).hexdigest(),
    )


def _validated_registry() -> tuple[ReviewedArkEntitlementEvidence, ...]:
    anchors = REVIEWED_ARK_ENTITLEMENT_EVIDENCE
    unique_identities: set[str] = set()
    for entry in anchors:
        for field in (
            "bundle_id",
            "logical_tree_sha256",
            "snapshot_contract_sha256",
            "raw_evidence_sha256",
            "account_scope_sha256",
            "credential_binding_sha256",
        ):
            value = cast(str, getattr(entry, field))
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ArkEntitlementError("entitlement registry contains an invalid digest")
        if (
            entry.profile != ARK_CANARY_ENTITLEMENT_PROFILE
            or entry.provider != CANARY_PROVIDER
            or entry.model != CANARY_MODEL
            or entry.region != ENTITLEMENT_REGION
            or entry.operation != ENTITLEMENT_OPERATION
        ):
            raise ArkEntitlementError("entitlement registry contains the wrong fixed profile")
        for timestamp in (entry.captured_at, entry.reviewed_at, entry.valid_until):
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ArkEntitlementError("entitlement registry times must include a timezone")
        if not entry.captured_at <= entry.reviewed_at < entry.valid_until:
            raise ArkEntitlementError("entitlement registry times are out of order")
        if entry.account_scope_sha256 == entry.credential_binding_sha256:
            raise ArkEntitlementError("entitlement registry scope bindings are not independent")
        anchor_digest = reviewed_ark_entitlement_anchor_sha256(entry)
        for digest in (
            entry.bundle_id,
            entry.logical_tree_sha256,
            entry.snapshot_contract_sha256,
            entry.raw_evidence_sha256,
            anchor_digest,
        ):
            if digest in unique_identities:
                raise ArkEntitlementError("entitlement registry contains a duplicate identity")
            unique_identities.add(digest)
    return anchors


def require_reviewed_ark_entitlement(
    bundle_id: str, *, at: datetime | None = None
) -> ReviewedArkEntitlementEvidence:
    """Resolve a positive registry entry before any artifact path may be inspected."""
    if _SHA256_PATTERN.fullmatch(bundle_id) is None:
        raise ArkEntitlementError("reviewed entitlement bundle ID must be lowercase SHA-256")
    anchors = _validated_registry()
    matches = tuple(entry for entry in anchors if entry.bundle_id == bundle_id)
    if len(matches) != 1:
        raise ArkEntitlementError("bundle ID is not uniquely present in the entitlement registry")
    entry = matches[0]
    current = datetime.now(UTC) if at is None else at
    _exclusive_current(
        current=current,
        created_at=entry.reviewed_at,
        valid_until=entry.valid_until,
        label="entitlement review",
    )
    return entry


def _validate_fixed_store_layout(*, manifest_path: Path, object_root: Path, bundle_id: str) -> None:
    store_root = object_root.parent
    for candidate in (store_root, object_root, manifest_path):
        _validate_path_policy(candidate, protected=_PROTECTED_OUTPUT_COMPONENTS, must_exist=True)
    expected_object_root = store_root / "objects"
    expected_manifest = store_root / "bundles" / f"{bundle_id}.json"
    try:
        if object_root.resolve(strict=True) != expected_object_root.resolve(
            strict=True
        ) or manifest_path.resolve(strict=True) != expected_manifest.resolve(strict=True):
            raise ArkEntitlementError(
                "trusted entitlement store must use the fixed objects/bundles layout"
            )
    except OSError as exc:
        raise ArkEntitlementError("trusted entitlement store is incomplete") from exc


def load_trusted_ark_entitlement(
    *,
    reviewed_bundle_id: str,
    manifest_path: Path,
    object_root: Path,
    at: datetime | None = None,
) -> _TrustedArkEntitlement:
    """Load exactly one reviewed two-member entitlement profile from verified CAS bytes."""
    # Trust lookup is deliberately the first operation; unknown IDs never inspect either path.
    anchor = require_reviewed_ark_entitlement(reviewed_bundle_id, at=at)
    _validate_fixed_store_layout(
        manifest_path=manifest_path,
        object_root=object_root,
        bundle_id=reviewed_bundle_id,
    )
    reader = EvidenceBundleReader.from_manifest(
        manifest_path, object_root, expected_bundle_id=reviewed_bundle_id
    )
    bundle = reader.bundle
    if bundle.content.predecessor_bundle_id is not None:
        raise ArkEntitlementError("entitlement bundles must not have predecessors")
    if len(bundle.content.objects) != 2:
        raise ArkEntitlementError("entitlement bundle must contain exactly two objects")
    expected_members = (
        (ENTITLEMENT_EVIDENCE_PATH, "entitlement.evidence", None, "application/pdf"),
        (
            ENTITLEMENT_SNAPSHOT_PATH,
            "entitlement.snapshot",
            "1.0.0",
            "application/json",
        ),
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
    if actual_members != expected_members:
        raise ArkEntitlementError("entitlement bundle member profile is not exact")
    if (
        object_by_hash[bundle.content.members[0].object_sha256].size_bytes
        > MAX_ENTITLEMENT_PDF_BYTES
        or object_by_hash[bundle.content.members[1].object_sha256].size_bytes
        > MAX_ENTITLEMENT_SNAPSHOT_BYTES
    ):
        raise ArkEntitlementError("entitlement bundle descriptor exceeds profile limits")
    if len(bundle.content.captures) != 1:
        raise ArkEntitlementError("entitlement bundle must contain exactly one capture")
    capture = bundle.content.captures[0]
    if (
        capture.capture_id != "entitlement"
        or capture.kind != "official-console-entitlement"
        or capture.source_url != ENTITLEMENT_SOURCE_URL
        or capture.source_updated_at is not None
        or capture.acquisition is not EvidenceAcquisition.FRESH
        or capture.origin_anchor_sha256 is not None
        or capture.origin_valid_until is not None
        or capture.member_paths != (ENTITLEMENT_EVIDENCE_PATH, ENTITLEMENT_SNAPSHOT_PATH)
    ):
        raise ArkEntitlementError("entitlement bundle capture profile is not exact and FRESH")

    resolved = reader.verify()
    current = datetime.now(UTC) if at is None else at
    reader.assert_current(at=current)
    _exclusive_current(
        current=current,
        created_at=bundle.content.created_at,
        valid_until=bundle.content.valid_until,
        label="entitlement load",
    )
    resolved_by_path = {member.logical_path: member for member in resolved}
    pdf_member = resolved_by_path[ENTITLEMENT_EVIDENCE_PATH]
    snapshot_member = resolved_by_path[ENTITLEMENT_SNAPSHOT_PATH]
    _validate_entitlement_pdf(pdf_member.data)
    snapshot = _parse_snapshot_bytes(snapshot_member.data)
    if snapshot_member.data != _canonical_snapshot_bytes(snapshot):
        raise ArkEntitlementError("stored entitlement snapshot is not canonical JSON")
    contract_digest = ark_entitlement_snapshot_contract_sha256(snapshot)
    if (
        bundle.content.created_at != snapshot.captured_at
        or capture.captured_at != snapshot.captured_at
        or bundle.content.valid_until != snapshot.valid_until
        or capture.valid_until != snapshot.valid_until
        or snapshot.evidence_sha256 != pdf_member.object_sha256
        or anchor.bundle_id != bundle.bundle_id
        or anchor.logical_tree_sha256 != bundle.content.resolved_logical_tree_sha256
        or anchor.snapshot_contract_sha256 != contract_digest
        or anchor.raw_evidence_sha256 != pdf_member.object_sha256
        or anchor.account_scope_sha256 != snapshot.account_scope_sha256
        or anchor.credential_binding_sha256 != snapshot.credential_binding_sha256
        or anchor.captured_at.astimezone(UTC) != snapshot.captured_at
        or anchor.valid_until.astimezone(UTC) != snapshot.valid_until
        or anchor.provider != snapshot.provider
        or anchor.model != snapshot.model
        or anchor.region != snapshot.region
        or anchor.operation != snapshot.operation
        or anchor.profile != snapshot.evidence_profile
        or anchor.reviewed_at.astimezone(UTC) < snapshot.captured_at
    ):
        raise ArkEntitlementError(
            "entitlement evidence does not match its reviewed registry binding"
        )
    final_current = datetime.now(UTC) if at is None else at
    _exclusive_current(
        current=final_current,
        created_at=bundle.content.created_at,
        valid_until=bundle.content.valid_until,
        label="entitlement verification completion",
    )
    return _TrustedArkEntitlement._from_verified(
        bundle_id=bundle.bundle_id,
        logical_tree_sha256=bundle.content.resolved_logical_tree_sha256,
        snapshot_contract_sha256=contract_digest,
        raw_evidence_sha256=pdf_member.object_sha256,
        entitlement_anchor_sha256=reviewed_ark_entitlement_anchor_sha256(anchor),
        valid_until=bundle.content.valid_until,
        snapshot=snapshot,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Freeze a sanitized Ark entitlement candidate without network access"
    )
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--evidence-pdf", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(".artifacts/entitlement-current/v1"),
    )
    args = parser.parse_args(argv)
    frozen = freeze_ark_canary_entitlement_candidate(
        snapshot_path=args.snapshot,
        evidence_pdf_path=args.evidence_pdf,
        output_root=args.output_root,
    )
    print(
        json.dumps(
            {
                "mode": "candidate-only-not-trusted",
                "bundle_id": frozen.bundle.bundle_id,
                "logical_tree_sha256": (frozen.bundle.content.resolved_logical_tree_sha256),
                "snapshot_contract_sha256": frozen.snapshot_contract_sha256,
                "raw_evidence_sha256": frozen.raw_evidence_sha256,
                "valid_until": frozen.bundle.content.valid_until.isoformat(),
                "manifest": str(frozen.manifest_path),
                "object_root": str(frozen.object_root),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
