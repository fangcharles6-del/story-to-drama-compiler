from __future__ import annotations

import hashlib
import json
import struct
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

import sdc.legacy_evidence as legacy_evidence
from sdc.contracts import EvidenceAcquisition
from sdc.evidence import EvidenceBundleExpiredError, EvidenceBundleReader
from sdc.legacy_evidence import (
    LegacyEvidenceError,
    LegacyImportResult,
    LegacySuccessorAnchor,
    LegacyVerificationLevel,
    import_legacy_round,
    verify_legacy_round,
)

_CAPTURED_AT = "2026-08-13T17:14:11+08:00"
_VALID_UNTIL = "2026-08-13T23:59:59+08:00"
_IMPORTED_AT = datetime(2026, 8, 14, tzinfo=UTC)
_TREE_ALGORITHM = "compact-json-array-v1"

_COMMON_PDF_PATHS = (
    "evidence/01-capability-evidence.pdf",
    "evidence/02-pricing-evidence.pdf",
    "evidence/03-create-task-api-evidence.pdf",
    "evidence/04-api-content-contract-evidence.pdf",
)
_PRE_R6_RAW_PATHS = (
    "evidence/raw/01-capability-row.jpg",
    "evidence/raw/01-capability-update-time.jpg",
    "evidence/raw/02-pricing-formula.jpg",
    "evidence/raw/02-pricing-token-row.jpg",
    "evidence/raw/02-pricing-update-time.jpg",
    "evidence/raw/03-api-async.jpg",
    "evidence/raw/03-api-audio.jpg",
    "evidence/raw/03-api-content-definition.jpg",
    "evidence/raw/03-api-duration.jpg",
    "evidence/raw/03-api-endpoint.jpg",
    "evidence/raw/03-api-ratio.jpg",
    "evidence/raw/03-api-resolution.jpg",
    "evidence/raw/03-api-text-to-video-example.png",
    "evidence/raw/03-api-text-type-fields.jpg",
    "evidence/raw/03-api-update-time.jpg",
)
_R4_R5_EXTRA_MEDIA_PATHS = (
    "evidence/05-entitlement-and-usage-evidence.pdf",
    "evidence/raw/05-exact-model-id.png",
    "evidence/raw/05-service-enabled-status.png",
    "evidence/raw/06-usage-range-summary.png",
    "evidence/raw/06-usage-zero.png",
)
_RUN_CORE_PATHS = (
    "story.json",
    "request-frozen.json",
    "execution.json",
    "plan.json",
    "validation/test_ark_provider.py",
)
_REVIEW_PATHS = (
    "historical-activation-provenance.json",
    "local-evidence-review.json",
    "offline-boundary-observation.json",
    "validation-results.json",
)

_R6_ARTIFACT_PATHS = (
    "evidence/01-capability-evidence.pdf",
    "evidence/02-pricing-evidence.pdf",
    "evidence/03-create-task-api-evidence.pdf",
    "evidence/04-api-content-contract-evidence.pdf",
    "evidence/05-entitlement-evidence.pdf",
    "capability.json",
    "pricing.json",
    "story.json",
    "request-frozen.json",
    "execution.json",
    "plan.json",
    "entitlement-continuity.json",
    "telemetry-continuity.json",
    "historical-activation-provenance.json",
    "local-evidence-review.json",
    "offline-boundary-observation.json",
    "validation-results.json",
    "validation/test_ark_provider.py",
)
_R6_RAW_PATHS = (
    "evidence/raw/01-capability-row.png",
    "evidence/raw/01-capability-update-time.png",
    "evidence/raw/02-pricing-formula.png",
    "evidence/raw/02-pricing-token-row.png",
    "evidence/raw/02-pricing-update-time.png",
    "evidence/raw/03-api-async.png",
    "evidence/raw/03-api-audio.png",
    "evidence/raw/03-api-content-definition.png",
    "evidence/raw/03-api-duration.png",
    "evidence/raw/03-api-endpoint.png",
    "evidence/raw/03-api-ratio.png",
    "evidence/raw/03-api-resolution.png",
    "evidence/raw/03-api-text-field.png",
    "evidence/raw/03-api-type-field.png",
    "evidence/raw/03-api-update-time.png",
    "evidence/raw/05-exact-model-id.png",
    "evidence/raw/05-service-enabled-status.png",
)
_R6_ADMITTED_PATHS = frozenset(
    {
        *[path for path in _R6_ARTIFACT_PATHS if path.startswith("evidence/")],
        *_R6_RAW_PATHS,
        "capability.json",
        "pricing.json",
        "entitlement-continuity.json",
        "telemetry-continuity.json",
    }
)
_R6_EXCLUDED_PATHS = frozenset(_R6_ARTIFACT_PATHS) - _R6_ADMITTED_PATHS


@dataclass(frozen=True, slots=True)
class SyntheticLegacyArchive:
    round_name: str
    root: Path
    index: Path
    index_sha256: str
    tree_sha256: str
    manifest_sha256: str
    report_sha256: str
    file_count: int


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _pdf_bytes(label: str) -> bytes:
    body = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    body.extend(f"% {label}\n".encode())
    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Resources << >> >>",
    )
    offsets: list[int] = []
    for number, value in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{number} 0 obj\n".encode())
        body.extend(value)
        body.extend(b"\nendobj\n")
    xref_offset = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        body.extend(f"{offset:010d} 00000 n \n".encode())
    body.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(body)


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def _png_bytes(label: str) -> bytes:
    color = hashlib.sha256(label.encode()).digest()[:3] + b"\xff"
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)),
            _png_chunk(b"tEXt", b"Comment\x00" + label.encode()),
            _png_chunk(b"IDAT", zlib.compress(b"\x00" + color)),
            _png_chunk(b"IEND", b""),
        )
    )


def _jpeg_bytes(label: str) -> bytes:
    return b"\xff\xd8\xff\xe0" + label.encode() + b"\xff\xd9"


def _media_type(path: str) -> str:
    if path.endswith(".pdf"):
        return "application/pdf"
    if path.endswith(".png"):
        return "image/png"
    if path.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if path.endswith(".json"):
        return "application/json"
    if path.endswith(".py"):
        return "text/x-python"
    if path.endswith(".patch"):
        return "text/x-diff"
    raise AssertionError(f"unhandled synthetic fixture path: {path}")


def _declaration(
    path: str,
    data: bytes,
    *,
    directory_name: str = "v02-r6",
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "path": f".artifacts/canary/{directory_name}/{path}",
        "bytes": len(data),
        "sha256": _sha256(data),
        "mime_type": _media_type(path),
    }
    if path.endswith(".json"):
        value["schema_version"] = "1.0.0"
    return value


def _source(
    kind: str,
    path: str,
    contents: dict[str, bytes],
    *,
    url: str,
    updated_at: str | None,
    directory_name: str = "v02-r6",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "canonical_url": url,
        "page_updated_at": updated_at,
        "captured_at": _CAPTURED_AT,
        "valid_until": _VALID_UNTIL,
        "evidence": _declaration(path, contents[path], directory_name=directory_name),
    }


def _archive_tree(root: Path) -> str:
    rows = []
    for candidate in sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    ):
        data = candidate.read_bytes()
        rows.append((candidate.relative_to(root).as_posix(), len(data), _sha256(data)))
    return _sha256(json.dumps(rows, separators=(",", ":")).encode())


def _build_r6_archive(base: Path) -> SyntheticLegacyArchive:
    root = base / "v02-r6"
    index_path = base / "v02-r6-index.json"
    contents: dict[str, bytes] = {}
    for path in _R6_ARTIFACT_PATHS:
        if path.endswith(".pdf"):
            contents[path] = _pdf_bytes(path)
        elif path.endswith(".py"):
            contents[path] = b"# synthetic immutable validation source\n"
        elif path not in {
            "capability.json",
            "pricing.json",
            "entitlement-continuity.json",
            "telemetry-continuity.json",
        }:
            contents[path] = _json_bytes({"fixture_path": path})
    for path in _R6_RAW_PATHS:
        contents[path] = _png_bytes(path)

    capability_pdf = "evidence/01-capability-evidence.pdf"
    pricing_pdf = "evidence/02-pricing-evidence.pdf"
    contents["capability.json"] = _json_bytes(
        {
            "schema_version": "1.0.0",
            "snapshot_revision": "2026-08-13.synthetic-v02-r6",
            "status": "CURRENT",
            "provider": "volcengine_ark",
            "model": "doubao-seedance-2-0-260128",
            "aspect_ratios": ["9:16"],
            "resolutions": ["1080p"],
            "fps": 24,
            "min_duration_ms": 4000,
            "max_duration_ms": 15000,
            "source_url": "https://docs.volcengine.com/docs/82379/1330310?lang=zh",
            "source_updated_at": "2026-08-12T21:53:29+08:00",
            "captured_at": _CAPTURED_AT,
            "valid_until": _VALID_UNTIL,
            "evidence_sha256": _sha256(contents[capability_pdf]),
        }
    )
    contents["pricing.json"] = _json_bytes(
        {
            "schema_version": "1.0.0",
            "snapshot_revision": "2026-08-13.synthetic-v02-r6",
            "status": "CURRENT",
            "provider": "volcengine_ark",
            "model": "doubao-seedance-2-0-260128",
            "resolution": "1080p",
            "input_mode": "WITHOUT_VIDEO",
            "currency": "CNY",
            "billing_unit": "provider-token",
            "unit_price_cny": "0.000051",
            "worst_case_units": "194400",
            "worst_case_cost_cny": "9.9144",
            "source_url": "https://docs.volcengine.com/docs/82379/1544106?lang=zh",
            "source_updated_at": "2026-08-12T22:01:30+08:00",
            "captured_at": _CAPTURED_AT,
            "valid_until": _VALID_UNTIL,
            "evidence_sha256": _sha256(contents[pricing_pdf]),
        }
    )
    contents["entitlement-continuity.json"] = _json_bytes(
        {"schema_version": "1.0.0", "observed_at": _CAPTURED_AT}
    )
    contents["telemetry-continuity.json"] = _json_bytes(
        {"schema_version": "1.0.0", "historical_observed_at": _CAPTURED_AT}
    )

    for path, data in contents.items():
        destination = root / Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    sources = (
        _source(
            "capability",
            capability_pdf,
            contents,
            url="https://docs.volcengine.com/docs/82379/1330310?lang=zh",
            updated_at="2026-08-12T21:53:29+08:00",
        ),
        _source(
            "pricing",
            pricing_pdf,
            contents,
            url="https://docs.volcengine.com/docs/82379/1544106?lang=zh",
            updated_at="2026-08-12T22:01:30+08:00",
        ),
        _source(
            "create_task_api",
            "evidence/03-create-task-api-evidence.pdf",
            contents,
            url="https://docs.volcengine.com/docs/82379/1520757?lang=zh",
            updated_at="2026-08-12T21:50:40+08:00",
        ),
        _source(
            "create_task_content_contract",
            "evidence/04-api-content-contract-evidence.pdf",
            contents,
            url="https://docs.volcengine.com/docs/82379/1520757?lang=zh",
            updated_at="2026-08-12T21:50:40+08:00",
        ),
        _source(
            "entitlement",
            "evidence/05-entitlement-evidence.pdf",
            contents,
            url="https://console.volcengine.com/ark/region:cn-beijing/openManagement",
            updated_at=None,
        ),
    )
    manifest = {
        "schema_version": "1.0.0",
        "freeze_id": "SDC-CANARY-001-V02-R6-SYNTHETIC",
        "round": "V02-R6",
        "assembled_at": "2026-08-13T17:29:18+08:00",
        "valid_until": _VALID_UNTIL,
        "archive_integrity_algorithm": _TREE_ALGORITHM,
        "sources": sources,
        "entitlement": {"observed_at": _CAPTURED_AT},
        "telemetry": {"historical_observed_at": _CAPTURED_AT},
        "artifacts": [_declaration(path, contents[path]) for path in _R6_ARTIFACT_PATHS],
        "raw_capture_files": [_declaration(path, contents[path]) for path in _R6_RAW_PATHS],
    }
    manifest_bytes = _json_bytes(manifest)
    manifest_path = root / "evidence" / "manifest.json"
    manifest_path.write_bytes(manifest_bytes)
    report_bytes = _json_bytes(
        {"schema_version": "1.0.0", "round": "V02-R6", "result": "PASS_SYNTHETIC"}
    )
    (root / "freeze-report.json").write_bytes(report_bytes)

    tree_sha256 = _archive_tree(root)
    index = {
        "schema_version": "1.0.0",
        "freeze_id": "SDC-CANARY-001-V02-R6-SYNTHETIC",
        "round": "V02-R6",
        "disposition": "FROZEN_NOT_AUTHORIZED_TEST_ARCHIVE_ONLY",
        "canonical_live_execution_eligible": False,
        "manifest_sha256": _sha256(manifest_bytes),
        "freeze_report_sha256": _sha256(report_bytes),
        "tree_sha256": tree_sha256,
        "tree_algorithm": _TREE_ALGORITHM,
        "file_count": len(_R6_ARTIFACT_PATHS) + len(_R6_RAW_PATHS) + 2,
        "authorization_artifact_present": False,
        "posts_allowed": 0,
    }
    index_bytes = _json_bytes(index)
    index_path.write_bytes(index_bytes)
    return SyntheticLegacyArchive(
        round_name="V02-R6",
        root=root,
        index=index_path,
        index_sha256=_sha256(index_bytes),
        tree_sha256=tree_sha256,
        manifest_sha256=_sha256(manifest_bytes),
        report_sha256=_sha256(report_bytes),
        file_count=len(_R6_ARTIFACT_PATHS) + len(_R6_RAW_PATHS) + 2,
    )


def _pre_r6_media_paths(round_name: str) -> frozenset[str]:
    paths = {*_COMMON_PDF_PATHS, *_PRE_R6_RAW_PATHS}
    if round_name in {"V02-R4", "V02-R5"}:
        paths.update(_R4_R5_EXTRA_MEDIA_PATHS)
    return frozenset(paths)


def _pre_r6_json_paths(round_name: str) -> frozenset[str]:
    paths = {"capability.json", "pricing.json"}
    if round_name == "V02-R4":
        paths.update({"entitlement-observation.json", "telemetry-observation.json"})
    elif round_name == "V02-R5":
        paths.update({"entitlement-continuity.json", "telemetry-continuity.json"})
    return frozenset(paths)


def _pre_r6_declared_paths(round_name: str) -> frozenset[str]:
    if round_name not in {"V02-R2", "V02-R3", "V02-R4", "V02-R5"}:
        raise AssertionError(f"unsupported synthetic pre-R6 round: {round_name}")
    paths = {
        *_pre_r6_media_paths(round_name),
        *_pre_r6_json_paths(round_name),
        *_RUN_CORE_PATHS,
    }
    if round_name == "V02-R2":
        paths.add("validation/ark-wire-golden-test.patch")
    elif round_name == "V02-R4":
        paths.update({"activation-operation-trace.json", "activation-review.json"})
    elif round_name == "V02-R5":
        paths.update(_REVIEW_PATHS)
    return frozenset(paths)


def _build_pre_r6_archive(
    base: Path,
    round_name: str,
    *,
    predecessor: SyntheticLegacyArchive | None = None,
    predecessor_tree_sha256: str | None = None,
) -> SyntheticLegacyArchive:
    directory_name = round_name.lower()
    root = base / directory_name
    index_path = base / f"{directory_name}-index.json"
    declared_paths = _pre_r6_declared_paths(round_name)
    raw_paths = tuple(sorted(path for path in declared_paths if path.startswith("evidence/raw/")))
    artifact_paths = tuple(sorted(declared_paths - frozenset(raw_paths)))
    contents: dict[str, bytes] = {}
    for path in declared_paths:
        if path.endswith(".pdf"):
            contents[path] = _pdf_bytes(f"{round_name}:{path}")
        elif path.endswith(".png"):
            contents[path] = _png_bytes(f"{round_name}:{path}")
        elif path.endswith((".jpg", ".jpeg")):
            contents[path] = _jpeg_bytes(f"{round_name}:{path}")
        elif path.endswith(".py"):
            contents[path] = b"# synthetic immutable validation source\n"
        elif path.endswith(".patch"):
            contents[path] = b"--- a/test\n+++ b/test\n@@ -0,0 +1 @@\n+synthetic\n"
        elif path not in {"capability.json", "pricing.json"}:
            value: dict[str, str] = {"schema_version": "1.0.0", "fixture_path": path}
            if path.startswith("entitlement-"):
                value["observed_at"] = _CAPTURED_AT
            elif path.startswith("telemetry-"):
                value["historical_observed_at"] = _CAPTURED_AT
            contents[path] = _json_bytes(value)

    capability_pdf = "evidence/01-capability-evidence.pdf"
    pricing_pdf = "evidence/02-pricing-evidence.pdf"
    contents["capability.json"] = _json_bytes(
        {
            "schema_version": "1.0.0",
            "snapshot_revision": f"2026-08-13.synthetic-{directory_name}",
            "status": "CURRENT",
            "provider": "volcengine_ark",
            "model": "doubao-seedance-2-0-260128",
            "aspect_ratios": ["9:16"],
            "resolutions": ["1080p"],
            "fps": 24,
            "min_duration_ms": 4000,
            "max_duration_ms": 15000,
            "source_url": "https://docs.volcengine.com/docs/82379/1330310?lang=zh",
            "source_updated_at": "2026-08-12T21:53:29+08:00",
            "captured_at": _CAPTURED_AT,
            "valid_until": _VALID_UNTIL,
            "evidence_sha256": _sha256(contents[capability_pdf]),
        }
    )
    contents["pricing.json"] = _json_bytes(
        {
            "schema_version": "1.0.0",
            "snapshot_revision": f"2026-08-13.synthetic-{directory_name}",
            "status": "CURRENT",
            "provider": "volcengine_ark",
            "model": "doubao-seedance-2-0-260128",
            "resolution": "1080p",
            "input_mode": "WITHOUT_VIDEO",
            "currency": "CNY",
            "billing_unit": "provider-token",
            "unit_price_cny": "0.000051",
            "worst_case_units": "194400",
            "worst_case_cost_cny": "9.9144",
            "source_url": "https://docs.volcengine.com/docs/82379/1544106?lang=zh",
            "source_updated_at": "2026-08-12T22:01:30+08:00",
            "captured_at": _CAPTURED_AT,
            "valid_until": _VALID_UNTIL,
            "evidence_sha256": _sha256(contents[pricing_pdf]),
        }
    )

    for path, data in contents.items():
        destination = root / Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    sources = (
        _source(
            "capability",
            capability_pdf,
            contents,
            url="https://docs.volcengine.com/docs/82379/1330310?lang=zh",
            updated_at="2026-08-12T21:53:29+08:00",
            directory_name=directory_name,
        ),
        _source(
            "pricing",
            pricing_pdf,
            contents,
            url="https://docs.volcengine.com/docs/82379/1544106?lang=zh",
            updated_at="2026-08-12T22:01:30+08:00",
            directory_name=directory_name,
        ),
        _source(
            "create_task_api",
            "evidence/03-create-task-api-evidence.pdf",
            contents,
            url="https://docs.volcengine.com/docs/82379/1520757?lang=zh",
            updated_at="2026-08-12T21:50:40+08:00",
            directory_name=directory_name,
        ),
        _source(
            "create_task_content_contract",
            "evidence/04-api-content-contract-evidence.pdf",
            contents,
            url="https://docs.volcengine.com/docs/82379/1520757?lang=zh",
            updated_at="2026-08-12T21:50:40+08:00",
            directory_name=directory_name,
        ),
    )
    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "freeze_id": f"SDC-CANARY-001-{round_name}-SYNTHETIC",
        "round": round_name,
        "assembled_at": "2026-08-13T17:29:18+08:00",
        "valid_until": _VALID_UNTIL,
        "sources": sources,
        "artifacts": [
            _declaration(path, contents[path], directory_name=directory_name)
            for path in artifact_paths
        ],
        "raw_capture_files": [
            _declaration(path, contents[path], directory_name=directory_name) for path in raw_paths
        ],
    }
    if round_name in {"V02-R4", "V02-R5"}:
        manifest["archive_integrity_algorithm"] = _TREE_ALGORITHM
        manifest["entitlement"] = {"observed_at": _CAPTURED_AT}
        manifest["telemetry"] = {"historical_observed_at": _CAPTURED_AT}
    if round_name == "V02-R3":
        if predecessor is None or predecessor.round_name != "V02-R2":
            raise AssertionError("synthetic R3 requires its synthetic R2 predecessor")
        manifest["prior_rounds"] = [
            {
                "path": ".artifacts/canary/v02-r2",
                "integrity": {
                    "file_count": predecessor.file_count,
                    "tree_sha256": predecessor_tree_sha256 or predecessor.tree_sha256,
                },
                "manifest_sha256": predecessor.manifest_sha256,
                "freeze_report_sha256": predecessor.report_sha256,
                "outer_index_sha256": predecessor.index_sha256,
            }
        ]

    manifest_bytes = _json_bytes(manifest)
    manifest_path = root / "evidence" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_bytes)
    report_bytes = _json_bytes(
        {"schema_version": "1.0.0", "round": round_name, "result": "PASS_SYNTHETIC"}
    )
    (root / "freeze-report.json").write_bytes(report_bytes)
    tree_sha256 = _archive_tree(root)
    file_count = len(declared_paths) + 2
    index: dict[str, Any] = {
        "schema_version": "1.0.0",
        "freeze_id": f"SDC-CANARY-001-{round_name}-SYNTHETIC",
        "round": round_name,
        "disposition": "FROZEN_NOT_AUTHORIZED_TEST_ARCHIVE_ONLY",
        "canonical_live_execution_eligible": False,
        "manifest_sha256": _sha256(manifest_bytes),
        "freeze_report_sha256": _sha256(report_bytes),
        "file_count": file_count,
        "authorization_artifact_present": False,
        "posts_allowed": 0,
    }
    if round_name != "V02-R2":
        index["tree_sha256"] = tree_sha256
    if round_name in {"V02-R4", "V02-R5"}:
        index["tree_algorithm"] = _TREE_ALGORITHM
    index_bytes = _json_bytes(index)
    index_path.write_bytes(index_bytes)
    return SyntheticLegacyArchive(
        round_name=round_name,
        root=root,
        index=index_path,
        index_sha256=_sha256(index_bytes),
        tree_sha256=tree_sha256,
        manifest_sha256=_sha256(manifest_bytes),
        report_sha256=_sha256(report_bytes),
        file_count=file_count,
    )


@pytest.fixture
def r6_archive(tmp_path: Path) -> SyntheticLegacyArchive:
    return _build_r6_archive(tmp_path / "canary")


def _import(
    archive: SyntheticLegacyArchive,
    tmp_path: Path,
    *,
    expected_index_sha256: str,
) -> LegacyImportResult:
    return import_legacy_round(
        archive.root,
        archive.index,
        expected_index_sha256=expected_index_sha256,
        output_root=tmp_path / "output",
    )


def test_r6_external_index_anchor_verifies_full_exact_path_closure(
    r6_archive: SyntheticLegacyArchive,
) -> None:
    report = verify_legacy_round(
        r6_archive.root,
        r6_archive.index,
        expected_index_sha256=r6_archive.index_sha256,
    )

    assert report.level is LegacyVerificationLevel.FULL_DESCRIPTOR_TREE
    assert report.outer_index_sha256 == r6_archive.index_sha256
    assert report.tree_algorithm == _TREE_ALGORITHM
    assert report.tree_sha256 == r6_archive.tree_sha256
    assert report.file_count == 37
    assert {item.relative_path for item in report.files} == {
        *_R6_ARTIFACT_PATHS,
        *_R6_RAW_PATHS,
        "evidence/manifest.json",
        "freeze-report.json",
    }


def test_source_root_is_rejected_before_any_archive_file_is_opened(
    r6_archive: SyntheticLegacyArchive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_lstat_no_link = legacy_evidence._lstat_no_link

    def linked_lstat(path: Path, label: str) -> Any:
        if path == r6_archive.root:
            raise LegacyEvidenceError(f"{label} contains a link or junction")
        return original_lstat_no_link(path, label)

    def forbidden_read(*args: Any, **kwargs: Any) -> tuple[bytes, str]:
        raise AssertionError("archive bytes were opened before source-root validation")

    monkeypatch.setattr(legacy_evidence, "_lstat_no_link", linked_lstat)
    monkeypatch.setattr(legacy_evidence, "_read_regular_file", forbidden_read)

    with pytest.raises(LegacyEvidenceError, match="archive root contains a link or junction"):
        verify_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=r6_archive.index_sha256,
        )


def test_import_validates_source_before_inspecting_output_location(
    r6_archive: SyntheticLegacyArchive,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_lstat_no_link = legacy_evidence._lstat_no_link

    def linked_lstat(path: Path, label: str) -> Any:
        if path == r6_archive.root.parent:
            raise LegacyEvidenceError(f"{label} contains a link or junction")
        return original_lstat_no_link(path, label)

    def forbidden_output_validation(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("output location inspected before source validation")

    monkeypatch.setattr(legacy_evidence, "_lstat_no_link", linked_lstat)
    monkeypatch.setattr(
        legacy_evidence, "_validate_output_root_location", forbidden_output_validation
    )

    with pytest.raises(LegacyEvidenceError, match="archive root contains a link or junction"):
        import_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=r6_archive.index_sha256,
            output_root=tmp_path / "output",
        )


def test_linked_evidence_parent_is_rejected_before_manifest_open(
    r6_archive: SyntheticLegacyArchive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence_root = r6_archive.root / "evidence"
    manifest_path = evidence_root / "manifest.json"
    original_lstat_no_link = legacy_evidence._lstat_no_link
    original_open = Path.open

    def linked_lstat(path: Path, label: str) -> Any:
        if path == evidence_root:
            raise LegacyEvidenceError(f"{label} contains a link or junction")
        return original_lstat_no_link(path, label)

    def guarded_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path == manifest_path:
            raise AssertionError("manifest opened through linked evidence directory")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(legacy_evidence, "_lstat_no_link", linked_lstat)
    monkeypatch.setattr(Path, "open", guarded_open)

    with pytest.raises(LegacyEvidenceError, match="contains a link or junction"):
        verify_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=r6_archive.index_sha256,
        )


def test_archive_walk_errors_fail_closed(
    r6_archive: SyntheticLegacyArchive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_walk(
        *args: Any,
        onerror: Any,
        **kwargs: Any,
    ) -> Iterator[tuple[str, list[str], list[str]]]:
        onerror(PermissionError("synthetic unreadable directory"))
        yield from ()

    monkeypatch.setattr("sdc.legacy_evidence.os.walk", failed_walk)

    with pytest.raises(LegacyEvidenceError, match="could not be enumerated"):
        verify_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=r6_archive.index_sha256,
        )


def test_non_r2_round_rejects_successor_without_touching_its_path(
    r6_archive: SyntheticLegacyArchive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_root = r6_archive.root.parent / "v02-r6-live"
    original_require = legacy_evidence._require_real_directory
    inspected: list[Path] = []

    def record_require(path: Path, label: str) -> None:
        inspected.append(path)
        original_require(path, label)

    monkeypatch.setattr(legacy_evidence, "_require_real_directory", record_require)

    with pytest.raises(LegacyEvidenceError, match="only R2"):
        verify_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=r6_archive.index_sha256,
            successor_anchor=LegacySuccessorAnchor(
                source_root=live_root,
                index_path=r6_archive.root.parent / "v02-r6-live-index.json",
                expected_index_sha256="0" * 64,
            ),
        )

    assert live_root not in inspected


def test_import_never_opens_excluded_archive_payloads(
    r6_archive: SyntheticLegacyArchive,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read = legacy_evidence._read_regular_file
    opened_archive_paths: list[str] = []

    def guarded_read(
        path: Path,
        *,
        trusted_root: Path,
        max_bytes: int,
        expected_size: int | None = None,
    ) -> tuple[bytes, str]:
        try:
            relative = path.relative_to(r6_archive.root).as_posix()
        except ValueError:
            relative = None
        if relative is not None:
            assert relative not in _R6_EXCLUDED_PATHS
            opened_archive_paths.append(relative)
        return original_read(
            path,
            trusted_root=trusted_root,
            max_bytes=max_bytes,
            expected_size=expected_size,
        )

    monkeypatch.setattr(legacy_evidence, "_read_regular_file", guarded_read)
    report = verify_legacy_round(
        r6_archive.root,
        r6_archive.index,
        expected_index_sha256=r6_archive.index_sha256,
    )
    result = _import(
        r6_archive,
        tmp_path,
        expected_index_sha256=r6_archive.index_sha256,
    )

    assert report.tree_sha256 == r6_archive.tree_sha256
    assert result.verification_level is LegacyVerificationLevel.FULL_DESCRIPTOR_TREE
    assert _R6_ADMITTED_PATHS <= set(opened_archive_paths)
    assert result.bundle.content.resolved_logical_tree_sha256


def test_unanchored_archive_verifies_but_cannot_be_imported(
    r6_archive: SyntheticLegacyArchive, tmp_path: Path
) -> None:
    report = verify_legacy_round(
        r6_archive.root,
        r6_archive.index,
        expected_index_sha256=None,
    )
    assert report.level is LegacyVerificationLevel.SELF_CONSISTENT_UNANCHORED

    with pytest.raises(LegacyEvidenceError, match="not independently verified"):
        _import(
            r6_archive,
            tmp_path,
            expected_index_sha256=cast(str, None),
        )
    assert not tuple((tmp_path / "output").rglob("*"))


def test_import_is_atomic_content_addressed_and_idempotent(
    r6_archive: SyntheticLegacyArchive, tmp_path: Path
) -> None:
    first = _import(
        r6_archive,
        tmp_path,
        expected_index_sha256=r6_archive.index_sha256,
    )
    manifest_path = tmp_path / "output" / "bundles" / "v02-r6.json"
    object_root = tmp_path / "output" / "objects"
    reader = EvidenceBundleReader.from_manifest(
        manifest_path,
        object_root,
        expected_bundle_id=first.bundle.bundle_id,
    )

    assert first.verification_level is LegacyVerificationLevel.FULL_DESCRIPTOR_TREE
    assert first.objects_written == len(first.bundle.content.objects)
    assert first.objects_reused == 0
    assert first.manifest_created is True
    assert first.object_root == object_root
    assert first.manifest_path == manifest_path
    assert len(reader.verify()) == len(_R6_ADMITTED_PATHS) + 1
    assert not tuple(tmp_path.rglob("*.tmp"))

    second = _import(
        r6_archive,
        tmp_path,
        expected_index_sha256=r6_archive.index_sha256,
    )
    assert second.bundle == first.bundle
    assert second.objects_written == 0
    assert second.objects_reused == len(first.bundle.content.objects)
    assert second.manifest_created is False
    assert not tuple(tmp_path.rglob("*.tmp"))


def test_import_preserves_expiry_and_marks_every_capture_legacy(
    r6_archive: SyntheticLegacyArchive, tmp_path: Path
) -> None:
    result = _import(
        r6_archive,
        tmp_path,
        expected_index_sha256=r6_archive.index_sha256,
    )
    expected_expiry = datetime(2026, 8, 13, 15, 59, 59, tzinfo=UTC)

    assert result.bundle.content.valid_until == expected_expiry
    assert all(
        capture.acquisition is EvidenceAcquisition.LEGACY_IMPORT
        and capture.valid_until == expected_expiry
        and capture.origin_valid_until == expected_expiry
        and capture.origin_anchor_sha256 == r6_archive.index_sha256
        for capture in result.bundle.content.captures
    )
    reader = EvidenceBundleReader(
        result.bundle,
        tmp_path / "output" / "objects",
        expected_bundle_id=result.bundle.bundle_id,
    )
    with pytest.raises(EvidenceBundleExpiredError):
        reader.assert_current(at=_IMPORTED_AT)


def test_verifier_rejects_declared_file_digest_drift(
    r6_archive: SyntheticLegacyArchive,
) -> None:
    capability = r6_archive.root / "evidence" / "01-capability-evidence.pdf"
    tampered = bytearray(capability.read_bytes())
    tampered[-2] ^= 0x01
    capability.write_bytes(tampered)

    with pytest.raises(LegacyEvidenceError, match="declaration digest mismatch"):
        verify_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=r6_archive.index_sha256,
        )


@pytest.mark.parametrize(
    ("relative_path", "expected_error"),
    (
        ("undeclared.txt", "missing or undeclared files"),
        ("authorization.json", "forbidden artifact"),
    ),
)
def test_verifier_rejects_extra_and_forbidden_files(
    r6_archive: SyntheticLegacyArchive,
    relative_path: str,
    expected_error: str,
) -> None:
    (r6_archive.root / relative_path).write_bytes(b"not admitted")

    with pytest.raises(LegacyEvidenceError, match=expected_error):
        verify_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=r6_archive.index_sha256,
        )


def test_verifier_rejects_duplicate_json_keys(
    r6_archive: SyntheticLegacyArchive,
) -> None:
    index_bytes = b'{"round":"V02-R6","round":"V02-R6","disposition":"FROZEN_NOT_AUTHORIZED_TEST"}'
    r6_archive.index.write_bytes(index_bytes)

    with pytest.raises(LegacyEvidenceError, match="duplicate JSON key: round"):
        verify_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=_sha256(index_bytes),
        )


def test_verifier_rejects_unknown_tree_algorithm(
    r6_archive: SyntheticLegacyArchive,
) -> None:
    index = json.loads(r6_archive.index.read_text(encoding="utf-8"))
    index["tree_algorithm"] = "attacker-defined-v1"
    index_bytes = _json_bytes(index)
    r6_archive.index.write_bytes(index_bytes)

    with pytest.raises(LegacyEvidenceError, match="unknown legacy archive tree algorithm"):
        verify_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=_sha256(index_bytes),
        )


def test_import_rejects_conflicting_existing_cas_object_without_partial_publish(
    r6_archive: SyntheticLegacyArchive, tmp_path: Path
) -> None:
    admitted = {
        _sha256((r6_archive.root / path).read_bytes()): (r6_archive.root / path).read_bytes()
        for path in _R6_ADMITTED_PATHS
    }
    first_digest = min(admitted)
    expected = admitted[first_digest]
    conflicting = bytes([expected[0] ^ 0xFF]) + expected[1:]
    target = tmp_path / "output" / "objects" / first_digest[:2] / first_digest
    target.parent.mkdir(parents=True)
    target.write_bytes(conflicting)

    with pytest.raises(LegacyEvidenceError, match="existing evidence CAS object"):
        _import(
            r6_archive,
            tmp_path,
            expected_index_sha256=r6_archive.index_sha256,
        )

    object_root = tmp_path / "output" / "objects"
    assert [path for path in object_root.rglob("*") if path.is_file()] == [target]
    assert target.read_bytes() == conflicting
    assert not (tmp_path / "output" / "bundles" / "v02-r6.json").exists()
    assert not tuple(tmp_path.rglob("*.tmp"))


@pytest.mark.parametrize("output_location", ("inside", "same", "ancestor"))
def test_import_rejects_output_that_overlaps_the_canary_container(
    r6_archive: SyntheticLegacyArchive,
    output_location: str,
) -> None:
    canary = r6_archive.root.parent
    output_root = {
        "inside": canary / "legacy-import",
        "same": canary,
        "ancestor": canary.parent,
    }[output_location]

    with pytest.raises(LegacyEvidenceError, match="must not overlap.*archive container"):
        import_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=r6_archive.index_sha256,
            output_root=output_root,
        )
    assert not (canary / "legacy-import").exists()


def test_import_rejects_a_different_canonical_canary_archive_as_output(
    r6_archive: SyntheticLegacyArchive,
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "other-history" / "canary" / "v02-r3"

    with pytest.raises(LegacyEvidenceError, match="canonical Canary archive path"):
        import_legacy_round(
            r6_archive.root,
            r6_archive.index,
            expected_index_sha256=r6_archive.index_sha256,
            output_root=output_root,
        )
    assert not output_root.exists()


def _synthetic_pre_r6_catalog(tmp_path: Path) -> dict[str, SyntheticLegacyArchive]:
    canary = tmp_path / "canary"
    r2 = _build_pre_r6_archive(canary, "V02-R2")
    return {
        "V02-R2": r2,
        "V02-R3": _build_pre_r6_archive(canary, "V02-R3", predecessor=r2),
        "V02-R4": _build_pre_r6_archive(canary, "V02-R4"),
        "V02-R5": _build_pre_r6_archive(canary, "V02-R5"),
    }


def test_synthetic_r2_r5_profiles_verify_without_local_archives(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = _synthetic_pre_r6_catalog(tmp_path)
    # A synthetic index cannot have the historical R3 digest. Bind the compatibility
    # allowlist to this fixture's independently supplied digest to exercise the same branch.
    monkeypatch.setattr(
        legacy_evidence,
        "_R3_CANONICAL_INDEX_SHA256",
        catalog["V02-R3"].index_sha256,
    )
    expected = {
        "V02-R2": (29, LegacyVerificationLevel.DEGRADED),
        "V02-R3": (28, LegacyVerificationLevel.CHAIN_COMPAT),
        "V02-R4": (37, LegacyVerificationLevel.FULL_DESCRIPTOR_TREE),
        "V02-R5": (39, LegacyVerificationLevel.FULL_DESCRIPTOR_TREE),
    }

    for round_name, archive in catalog.items():
        report = verify_legacy_round(
            archive.root,
            archive.index,
            expected_index_sha256=archive.index_sha256,
        )
        declared = _pre_r6_declared_paths(round_name)
        admitted = _pre_r6_media_paths(round_name) | _pre_r6_json_paths(round_name)

        assert (report.file_count, report.level) == expected[round_name]
        assert report.tree_sha256 == archive.tree_sha256
        assert {item.relative_path for item in report.files} == {
            *declared,
            "evidence/manifest.json",
            "freeze-report.json",
        }
        assert {item.relative_path for item in report.files if not item.byte_verified} == (
            declared - admitted
        )
        assert report.tree_algorithm == (None if round_name == "V02-R2" else _TREE_ALGORITHM)


def test_synthetic_r2_successor_chain_unlocks_legacy_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = _synthetic_pre_r6_catalog(tmp_path)
    r2 = catalog["V02-R2"]
    r3 = catalog["V02-R3"]
    monkeypatch.setattr(legacy_evidence, "_R3_CANONICAL_INDEX_SHA256", r3.index_sha256)
    successor = LegacySuccessorAnchor(
        source_root=r3.root,
        index_path=r3.index,
        expected_index_sha256=r3.index_sha256,
    )

    standalone = verify_legacy_round(
        r2.root,
        r2.index,
        expected_index_sha256=r2.index_sha256,
    )
    chained = verify_legacy_round(
        r2.root,
        r2.index,
        expected_index_sha256=r2.index_sha256,
        successor_anchor=successor,
    )
    result = import_legacy_round(
        r2.root,
        r2.index,
        expected_index_sha256=r2.index_sha256,
        output_root=tmp_path / "r2-import",
        successor_anchor=successor,
    )

    assert standalone.level is LegacyVerificationLevel.DEGRADED
    assert chained.level is LegacyVerificationLevel.CHAIN_COMPAT
    assert chained.tree_algorithm == _TREE_ALGORITHM
    assert result.verification_level is LegacyVerificationLevel.CHAIN_COMPAT
    assert result.manifest_path == tmp_path / "r2-import" / "bundles" / "v02-r2.json"
    assert len(result.bundle.content.members) == 22
    assert [
        member.logical_path
        for member in result.bundle.content.members
        if member.role == "legacy-origin-record"
    ] == ["provenance/v02-r2-origin.json"]
    resolved = {
        member.logical_path: member.data
        for member in EvidenceBundleReader.from_manifest(
            result.manifest_path,
            result.object_root,
            expected_bundle_id=result.bundle.bundle_id,
        ).verify()
    }
    origin = json.loads(resolved["provenance/v02-r2-origin.json"])
    assert origin["outer_index_sha256"] == r2.index_sha256
    assert origin["successor_anchor"] == {
        "round": "V02-R3",
        "outer_index_sha256": r3.index_sha256,
    }
    assert all(
        capture.acquisition is EvidenceAcquisition.LEGACY_IMPORT
        and capture.origin_anchor_sha256 == r2.index_sha256
        for capture in result.bundle.content.captures
    )


def test_synthetic_r2_chain_rejects_mismatched_r3_predecessor_anchor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canary = tmp_path / "canary"
    r2 = _build_pre_r6_archive(canary, "V02-R2")
    r3 = _build_pre_r6_archive(
        canary,
        "V02-R3",
        predecessor=r2,
        predecessor_tree_sha256="0" * 64,
    )
    monkeypatch.setattr(legacy_evidence, "_R3_CANONICAL_INDEX_SHA256", r3.index_sha256)

    with pytest.raises(LegacyEvidenceError, match="predecessor anchor does not match"):
        verify_legacy_round(
            r2.root,
            r2.index,
            expected_index_sha256=r2.index_sha256,
            successor_anchor=LegacySuccessorAnchor(
                source_root=r3.root,
                index_path=r3.index,
                expected_index_sha256=r3.index_sha256,
            ),
        )


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_CANARY_ROOT = _REPOSITORY_ROOT / ".artifacts" / "canary"
_CANONICAL_GOLDENS = {
    "V02-R2": {
        "directory": "v02-r2",
        "index": "v02-r2-index.json",
        "index_sha256": "ef63adc9c040dc543ce593b70b9729c6b29cd9ff4af947856365756f281c743f",
        "manifest_sha256": "9c4489c40d78a105bc49ec106f9ea13d7551a9694d2ee33f1642bbfe68761d90",
        "report_sha256": "f3fb761f6091201aa726a7c81333cf74a2f3ef83c88cf78745df2cddf041fbde",
        "tree_sha256": "e878442d46ade842dd766c14e91af63f15e0ee973a105441030b5bfb7e9b4692",
        "file_count": 29,
        "level": LegacyVerificationLevel.CHAIN_COMPAT,
    },
    "V02-R3": {
        "directory": "v02-r3",
        "index": "v02-r3-index.json",
        "index_sha256": "9fee187499617e880fbb0d07191ee315efa6ec3a095b06c5aadb7293b0538591",
        "manifest_sha256": "104cc4c56d7f6c539232f0e253fe6b4bcd0ddb3354e0a77f16aa3add8ceba6cb",
        "report_sha256": "72afb1ccb1f06ab9abf39c1e2550d17373cf75762f6536ac570ef57d5b51a3b3",
        "tree_sha256": "f6b9172f6d4e9f80c0eb485d42b75602ba856dc15edb4dc2233d41ce3fc5bd68",
        "file_count": 28,
        "level": LegacyVerificationLevel.CHAIN_COMPAT,
    },
    "V02-R4": {
        "directory": "v02-r4",
        "index": "v02-r4-index.json",
        "index_sha256": "51beb34e5111bc864018a0a5ac37fadf50d86aea7c9944c85b3902c6541bf550",
        "manifest_sha256": "44a97e5d58be29a28ff3db60ee9d0606e1cd73889c65440fcbb8a8195bfe7ef6",
        "report_sha256": "753ff192e24cbd6001015f7a80c23b78e7672f0e323877a8b9fdde5a0b715d8b",
        "tree_sha256": "5f00168d4de2377d1cc12012e7a5a1f30be52369633f43f92c22671a28bf3e8d",
        "file_count": 37,
        "level": LegacyVerificationLevel.FULL_DESCRIPTOR_TREE,
    },
    "V02-R5": {
        "directory": "v02-r5",
        "index": "v02-r5-index.json",
        "index_sha256": "dfa9ef2af0049e505e25e44da0d090e80ed49be7df478fe95ef40a41f726624e",
        "manifest_sha256": "061e7ced7cf5fc2798d1c1281a2659bfed5c0eb62c1f018018fcec68a2c818eb",
        "report_sha256": "eb9cc499cc6db71759bfe8a20a075eb02c276b3e2275ff84e46364376b0230ab",
        "tree_sha256": "d5d4797fd668f8391fbf8a35dff6ec858334358ea47898194e52d17d4d898aa9",
        "file_count": 39,
        "level": LegacyVerificationLevel.FULL_DESCRIPTOR_TREE,
    },
    "V02-R6": {
        "directory": "v02-r6",
        "index": "v02-r6-index.json",
        "index_sha256": "cf03a19ba671d89e1504b4c88b5bae1dd33a559eea48965d6ce6af0f47b850c5",
        "manifest_sha256": "c7c9dae6d2799eaf472f10821f33869af68e3903eb0e94c4812ecc4bdec8af5b",
        "report_sha256": "df81e7ff5db0e6ca2662bffcc4bec79bbe1b584c0564121603ea5485cd3a653c",
        "tree_sha256": "2415399d0fb1458d7d9105ce47b96ac5d6162f37af97270653e99599fcc0cb3f",
        "file_count": 37,
        "level": LegacyVerificationLevel.FULL_DESCRIPTOR_TREE,
    },
}
_LOCAL_ARCHIVES_PRESENT = all(
    (_CANARY_ROOT / cast(str, golden["directory"])).is_dir()
    and (_CANARY_ROOT / cast(str, golden["index"])).is_file()
    for golden in _CANONICAL_GOLDENS.values()
)


@pytest.mark.skipif(
    not _LOCAL_ARCHIVES_PRESENT,
    reason="canonical local R2-R6 archives are not present",
)
def test_local_r2_r6_archives_match_reviewed_golden_catalog() -> None:
    r3 = _CANONICAL_GOLDENS["V02-R3"]
    successor = LegacySuccessorAnchor(
        source_root=_CANARY_ROOT / cast(str, r3["directory"]),
        index_path=_CANARY_ROOT / cast(str, r3["index"]),
        expected_index_sha256=cast(str, r3["index_sha256"]),
    )

    for round_name, golden in _CANONICAL_GOLDENS.items():
        report = verify_legacy_round(
            _CANARY_ROOT / cast(str, golden["directory"]),
            _CANARY_ROOT / cast(str, golden["index"]),
            expected_index_sha256=cast(str, golden["index_sha256"]),
            successor_anchor=successor if round_name == "V02-R2" else None,
        )
        assert report.round == round_name
        assert report.level is golden["level"]
        assert report.outer_index_sha256 == golden["index_sha256"]
        assert report.manifest_sha256 == golden["manifest_sha256"]
        assert report.freeze_report_sha256 == golden["report_sha256"]
        assert report.tree_sha256 == golden["tree_sha256"]
        assert report.file_count == golden["file_count"]
