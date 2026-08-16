from __future__ import annotations

import hashlib
import json
import os
import socket
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    RectangleObject,
)

import sdc.ark_entitlement as ark_entitlement
from sdc.ark_entitlement import (
    ENTITLEMENT_EVIDENCE_PATH,
    ENTITLEMENT_SNAPSHOT_PATH,
    MAX_ENTITLEMENT_PDF_BYTES,
    MAX_ENTITLEMENT_SNAPSHOT_BYTES,
    ArkEntitlementError,
    account_scope_sha256,
    ark_entitlement_snapshot_contract_sha256,
    build_ark_canary_entitlement_bundle,
    credential_binding_sha256,
    freeze_ark_canary_entitlement_candidate,
    load_trusted_ark_entitlement,
)
from sdc.ark_entitlement_registry import (
    ARK_CANARY_ENTITLEMENT_PROFILE,
    REVIEWED_ARK_ENTITLEMENT_EVIDENCE,
    ReviewedArkEntitlementEvidence,
    reviewed_ark_entitlement_anchor_sha256,
)
from sdc.contracts import (
    ArkCanaryEntitlementSnapshot,
    EvidenceCapture,
    EvidenceMember,
    EvidenceObject,
)
from sdc.evidence import EvidenceBundleError, build_evidence_bundle

CAPTURED_AT = datetime(2026, 8, 15, 6, 0, tzinfo=UTC)
REVIEWED_AT = CAPTURED_AT + timedelta(minutes=15)
LOAD_AT = CAPTURED_AT + timedelta(minutes=30)
VALID_UNTIL = CAPTURED_AT + timedelta(hours=3)
SOURCE_VALID_UNTIL = CAPTURED_AT + timedelta(hours=5)
SOURCE_URL = "https://console.volcengine.com/ark/region:cn-beijing/openManagement"
ACCOUNT_SCOPE_SHA256 = "a" * 64
CREDENTIAL_BINDING_SHA256 = "b" * 64


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz: object = None) -> datetime:
        if tz is None:
            return LOAD_AT.replace(tzinfo=None)
        return LOAD_AT


class ExpiringDateTime(datetime):
    calls = 0

    @classmethod
    def now(cls, tz: object = None) -> datetime:
        cls.calls += 1
        value = LOAD_AT if cls.calls < 3 else VALID_UNTIL
        if tz is None:
            return value.replace(tzinfo=None)
        return value


@dataclass(frozen=True)
class Prepared:
    root: Path
    bundle: Any
    data_by_path: dict[str, bytes]
    snapshot: ArkCanaryEntitlementSnapshot
    registry_entry: ReviewedArkEntitlementEvidence
    manifest_path: Path
    object_root: Path


def _render_pdf(*, feature: str | None = None, padding: int = 0) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=72, height=72)
    if padding:
        stream = DecodedStreamObject()
        stream.set_data(b" " * padding)
        page[NameObject("/Contents")] = writer._add_object(stream)

    if feature == "attachment":
        writer.add_attachment("review.txt", b"not allowed")
    elif feature == "form":
        form = DictionaryObject({NameObject("/Fields"): ArrayObject()})
        writer._root_object[NameObject("/AcroForm")] = writer._add_object(form)
    elif feature == "javascript":
        writer.add_js("app.alert('not allowed')")
    elif feature == "open-action":
        page_reference = writer.pages[0].indirect_reference
        assert page_reference is not None
        writer._root_object[NameObject("/OpenAction")] = ArrayObject(
            [page_reference, NameObject("/Fit")]
        )
    elif feature == "uri":
        writer.add_uri(
            0,
            "https://example.invalid/not-allowed",
            RectangleObject((0, 0, 20, 20)),
        )
    elif feature in {"movie", "sound", "3d"}:
        subtype = {"movie": "/Movie", "sound": "/Sound", "3d": "/3D"}[feature]
        payload_key = {"movie": "/Movie", "sound": "/Sound", "3d": "/3DD"}[feature]
        annotation = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject(subtype),
                NameObject("/Rect"): RectangleObject((0, 0, 20, 20)),
                NameObject(payload_key): DictionaryObject(),
            }
        )
        page[NameObject("/Annots")] = ArrayObject([writer._add_object(annotation)])
    elif feature == "transition":
        page[NameObject("/Trans")] = DictionaryObject({NameObject("/S"): NameObject("/Dissolve")})
    elif feature == "encrypted":
        writer.encrypt("test-password")
    elif feature is not None:
        raise AssertionError(f"unknown PDF feature: {feature}")

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _pdf_trailer_variant(kind: str) -> bytes:
    pdf = _render_pdf()
    if kind == "payload":
        return pdf + b"NONEMPTY-TRAILING-PAYLOAD"
    if kind == "second-revision":
        return pdf + _render_pdf()
    if kind == "multiple-eof":
        return pdf + b"%%EOF"
    if kind == "pdf-whitespace":
        return pdf + b"\x00\t\n\f\r "
    raise AssertionError(f"unknown PDF trailer variant: {kind}")


def _sized_pdf(size: int) -> bytes:
    padding = max(0, size - 1_000)
    for _ in range(12):
        rendered = _render_pdf(padding=padding)
        difference = size - len(rendered)
        if difference == 0:
            return rendered
        padding += difference
        if padding < 0:
            break
    raise AssertionError(f"could not construct an exact {size}-byte PDF")


def _snapshot_payload(pdf: bytes, **updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.ark-canary-entitlement-snapshot",
        "evidence_profile": "ark-canary-entitlement-v1",
        "snapshot_revision": "2026-08-15.canary-01",
        "status": "CURRENT",
        "provider": "volcengine_ark",
        "service": "ark-video-generation",
        "model": "doubao-seedance-2-0-260128",
        "region": "cn-beijing",
        "operation": "contents.generations.tasks.create",
        "provider_state": "ENABLED",
        "conclusion": "PASS_ENTITLEMENT_ONLY",
        "account_scope_sha256": ACCOUNT_SCOPE_SHA256,
        "credential_binding_sha256": CREDENTIAL_BINDING_SHA256,
        "source_url": SOURCE_URL,
        "source_valid_until": SOURCE_VALID_UNTIL.isoformat(),
        "captured_at": CAPTURED_AT.isoformat(),
        "valid_until": VALID_UNTIL.isoformat(),
        "evidence_sha256": hashlib.sha256(pdf).hexdigest(),
    }
    payload.update(updates)
    return payload


def _snapshot_bytes(pdf: bytes, **updates: object) -> bytes:
    return json.dumps(
        _snapshot_payload(pdf, **updates),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _registry_entry(
    bundle: Any,
    snapshot: ArkCanaryEntitlementSnapshot,
    *,
    raw_evidence_sha256: str,
) -> ReviewedArkEntitlementEvidence:
    return ReviewedArkEntitlementEvidence(
        bundle_id=bundle.bundle_id,
        logical_tree_sha256=bundle.content.resolved_logical_tree_sha256,
        snapshot_contract_sha256=ark_entitlement_snapshot_contract_sha256(snapshot),
        raw_evidence_sha256=raw_evidence_sha256,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        region="cn-beijing",
        operation="contents.generations.tasks.create",
        account_scope_sha256=snapshot.account_scope_sha256,
        credential_binding_sha256=snapshot.credential_binding_sha256,
        captured_at=snapshot.captured_at,
        reviewed_at=REVIEWED_AT,
        valid_until=snapshot.valid_until,
        profile=ARK_CANARY_ENTITLEMENT_PROFILE,
    )


def _materialize(
    root: Path,
    *,
    pdf: bytes | None = None,
    snapshot_bytes: bytes | None = None,
) -> Prepared:
    selected_pdf = _render_pdf() if pdf is None else pdf
    selected_snapshot = _snapshot_bytes(selected_pdf) if snapshot_bytes is None else snapshot_bytes
    bundle, immutable_data = build_ark_canary_entitlement_bundle(
        snapshot_bytes=selected_snapshot,
        evidence_pdf_bytes=selected_pdf,
    )
    data_by_path = dict(immutable_data)
    return _materialize_bundle(root, bundle=bundle, data_by_path=data_by_path)


def _materialize_bundle(
    root: Path,
    *,
    bundle: Any,
    data_by_path: dict[str, bytes],
) -> Prepared:
    object_root = root / "objects"
    manifest_path = root / "bundles" / f"{bundle.bundle_id}.json"
    member_by_path = {member.logical_path: member for member in bundle.content.members}
    for logical_path, data in data_by_path.items():
        digest = member_by_path[logical_path].object_sha256
        target = object_root / digest[:2] / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(bundle.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    snapshot = ArkCanaryEntitlementSnapshot.model_validate_json(
        data_by_path[ENTITLEMENT_SNAPSHOT_PATH]
    )
    raw_digest = hashlib.sha256(data_by_path[ENTITLEMENT_EVIDENCE_PATH]).hexdigest()
    return Prepared(
        root=root,
        bundle=bundle,
        data_by_path=data_by_path,
        snapshot=snapshot,
        registry_entry=_registry_entry(
            bundle,
            snapshot,
            raw_evidence_sha256=raw_digest,
        ),
        manifest_path=manifest_path,
        object_root=object_root,
    )


def _unchecked_pdf_profile(pdf: bytes) -> tuple[Any, dict[str, bytes]]:
    snapshot = ArkCanaryEntitlementSnapshot.model_validate(_snapshot_payload(pdf))
    canonical_snapshot = json.dumps(
        snapshot.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    pdf_object = EvidenceObject(
        sha256=hashlib.sha256(pdf).hexdigest(),
        size_bytes=len(pdf),
        media_type="application/pdf",
    )
    snapshot_object = EvidenceObject(
        sha256=hashlib.sha256(canonical_snapshot).hexdigest(),
        size_bytes=len(canonical_snapshot),
        media_type="application/json",
    )
    members = (
        EvidenceMember(
            logical_path=ENTITLEMENT_EVIDENCE_PATH,
            role="entitlement.evidence",
            object_sha256=pdf_object.sha256,
        ),
        EvidenceMember(
            logical_path=ENTITLEMENT_SNAPSHOT_PATH,
            role="entitlement.snapshot",
            object_sha256=snapshot_object.sha256,
            content_schema_version="1.0.0",
        ),
    )
    capture = EvidenceCapture(
        capture_id="entitlement",
        kind="official-console-entitlement",
        source_url=SOURCE_URL,
        source_updated_at=None,
        captured_at=CAPTURED_AT,
        valid_until=VALID_UNTIL,
        acquisition="FRESH",
        member_paths=(ENTITLEMENT_EVIDENCE_PATH, ENTITLEMENT_SNAPSHOT_PATH),
    )
    bundle = build_evidence_bundle(
        created_at=CAPTURED_AT,
        objects=(pdf_object, snapshot_object),
        members=members,
        captures=(capture,),
    )
    return bundle, {
        ENTITLEMENT_EVIDENCE_PATH: pdf,
        ENTITLEMENT_SNAPSHOT_PATH: canonical_snapshot,
    }


def _trust(prepared: Prepared, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ark_entitlement,
        "REVIEWED_ARK_ENTITLEMENT_EVIDENCE",
        (prepared.registry_entry,),
    )


def test_committed_registry_is_empty_and_candidate_profile_is_exact() -> None:
    assert REVIEWED_ARK_ENTITLEMENT_EVIDENCE == ()
    pdf = _render_pdf()
    bundle, data_by_path = build_ark_canary_entitlement_bundle(
        snapshot_bytes=_snapshot_bytes(pdf),
        evidence_pdf_bytes=pdf,
    )

    assert len(bundle.content.objects) == 2
    assert len({item.sha256 for item in bundle.content.objects}) == 2
    assert tuple(
        (member.logical_path, member.role, member.content_schema_version)
        for member in bundle.content.members
    ) == (
        (ENTITLEMENT_EVIDENCE_PATH, "entitlement.evidence", None),
        (ENTITLEMENT_SNAPSHOT_PATH, "entitlement.snapshot", "1.0.0"),
    )
    assert len(bundle.content.captures) == 1
    capture = bundle.content.captures[0]
    assert capture.capture_id == "entitlement"
    assert capture.kind == "official-console-entitlement"
    assert capture.source_updated_at is None
    assert capture.origin_anchor_sha256 is None
    assert capture.origin_valid_until is None
    assert capture.member_paths == (
        ENTITLEMENT_EVIDENCE_PATH,
        ENTITLEMENT_SNAPSHOT_PATH,
    )
    assert bundle.content.predecessor_bundle_id is None
    assert bundle.content.created_at == capture.captured_at == CAPTURED_AT
    assert bundle.content.valid_until == capture.valid_until == VALID_UNTIL
    assert data_by_path[ENTITLEMENT_EVIDENCE_PATH] == pdf
    stored_snapshot = data_by_path[ENTITLEMENT_SNAPSHOT_PATH]
    assert stored_snapshot == stored_snapshot.rstrip(b" \t\r\n")
    assert stored_snapshot == (
        json.dumps(
            json.loads(stored_snapshot),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def test_private_scope_digests_match_the_exact_domain_separated_adr_formula() -> None:
    salt = b"SALT-MARKER-" + b"x" * 20
    assert len(salt) == 32
    account_payload = {
        "account_id": "account-001",
        "project_id": None,
        "subaccount_id": "subaccount-002",
    }
    credential_payload = {
        "immutable_version": "version-7",
        "resource_locator": "vault://ark/canary/key",
        "secret_store": "vault",
    }
    canonical_account = json.dumps(
        account_payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    canonical_credential = json.dumps(
        credential_payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    expected_account = hashlib.sha256(
        b"sdc:volcengine-account-scope:v1\0" + canonical_account + b"\0" + salt
    ).hexdigest()
    expected_credential = hashlib.sha256(
        b"sdc:ark-credential-binding:v1\0" + canonical_credential + b"\0" + salt
    ).hexdigest()

    assert (
        account_scope_sha256(
            account_id="account-001",
            subaccount_id="subaccount-002",
            project_id=None,
            private_salt=salt,
        )
        == expected_account
    )
    assert (
        credential_binding_sha256(
            secret_store="vault",
            resource_locator="vault://ark/canary/key",
            immutable_version="version-7",
            private_salt=salt,
        )
        == expected_credential
    )
    assert expected_account != expected_credential


@pytest.mark.parametrize(
    ("account_id", "salt"),
    [
        ("e\u0301", b"x" * 32),
        ("account\nidentifier", b"x" * 32),
        ("account", b"x" * 31),
        ("account", b"x" * 33),
        ("account", b"\0" * 32),
    ],
    ids=["non-nfc", "control", "short-salt", "long-salt", "zero-salt"],
)
def test_private_scope_digest_rejects_noncanonical_identifiers_and_salts(
    account_id: str,
    salt: bytes,
) -> None:
    with pytest.raises(ArkEntitlementError, match="canonical|32-byte salt"):
        account_scope_sha256(
            account_id=account_id,
            subaccount_id=None,
            project_id=None,
            private_salt=salt,
        )


def test_credential_digest_rejects_control_characters_and_never_accepts_key_material() -> None:
    salt = b"x" * 32
    with pytest.raises(ArkEntitlementError, match="canonical"):
        credential_binding_sha256(
            secret_store="vault",
            resource_locator="vault://ark/key\nsecret-value-must-not-leak",
            immutable_version="version-7",
            private_salt=salt,
        )
    with pytest.raises(TypeError):
        credential_binding_sha256(  # type: ignore[call-arg]
            secret_store="vault",
            resource_locator="vault://ark/key",
            immutable_version="version-7",
            private_salt=salt,
            api_key="secret-value-must-not-leak",
        )


@pytest.mark.parametrize(
    "field",
    [
        "document_type",
        "evidence_profile",
        "snapshot_revision",
        "status",
        "provider",
        "service",
        "model",
        "region",
        "operation",
        "provider_state",
        "conclusion",
        "account_scope_sha256",
        "credential_binding_sha256",
        "source_url",
        "source_valid_until",
        "captured_at",
        "valid_until",
        "evidence_sha256",
    ],
)
def test_snapshot_requires_every_bound_field(field: str) -> None:
    pdf = _render_pdf()
    payload = _snapshot_payload(pdf)
    del payload[field]

    with pytest.raises(ArkEntitlementError, match="invalid entitlement snapshot JSON"):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=json.dumps(payload).encode(),
            evidence_pdf_bytes=pdf,
        )


@pytest.mark.parametrize(
    "raw",
    [
        b"\xff",
        b"[]",
        b'{"provider":"volcengine_ark","provider":"volcengine_ark"}',
        b'{"unexpected":NaN}',
    ],
    ids=["invalid-utf8", "not-an-object", "duplicate-key", "non-finite"],
)
def test_strict_snapshot_json_rejects_invalid_inputs(raw: bytes) -> None:
    pdf = _render_pdf()
    with pytest.raises(ArkEntitlementError):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=raw,
            evidence_pdf_bytes=pdf,
        )


def test_snapshot_rejects_extra_fields_and_noncanonical_console_urls() -> None:
    pdf = _render_pdf()
    with pytest.raises(ArkEntitlementError, match="invalid entitlement snapshot JSON"):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=_snapshot_bytes(pdf, unexpected="field"),
            evidence_pdf_bytes=pdf,
        )

    for source_url in (
        SOURCE_URL + "/",
        SOURCE_URL + "?lang=zh",
        SOURCE_URL + "#fragment",
        SOURCE_URL.replace("https://", "http://"),
        SOURCE_URL.replace("console.volcengine.com", "console.volcengine.com.example"),
        SOURCE_URL.replace("openManagement", "model/detail"),
    ):
        with pytest.raises(ArkEntitlementError, match="invalid entitlement snapshot JSON"):
            build_ark_canary_entitlement_bundle(
                snapshot_bytes=_snapshot_bytes(pdf, source_url=source_url),
                evidence_pdf_bytes=pdf,
            )


def test_snapshot_json_size_boundary_is_exact() -> None:
    pdf = _render_pdf()
    raw = _snapshot_bytes(pdf)
    at_limit = raw + b" " * (MAX_ENTITLEMENT_SNAPSHOT_BYTES - len(raw))
    assert len(at_limit) == MAX_ENTITLEMENT_SNAPSHOT_BYTES
    build_ark_canary_entitlement_bundle(
        snapshot_bytes=at_limit,
        evidence_pdf_bytes=pdf,
    )

    with pytest.raises(ArkEntitlementError, match="64 KiB"):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=at_limit + b" ",
            evidence_pdf_bytes=pdf,
        )


@pytest.mark.parametrize(
    "feature",
    [
        "attachment",
        "form",
        "javascript",
        "open-action",
        "uri",
        "movie",
        "sound",
        "3d",
        "transition",
    ],
)
def test_real_pypdf_active_content_is_rejected(feature: str) -> None:
    pdf = _render_pdf(feature=feature)
    assert len(PdfReader(BytesIO(pdf), strict=True).pages) == 1

    with pytest.raises(ArkEntitlementError, match="active or interactive"):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=_snapshot_bytes(pdf),
            evidence_pdf_bytes=pdf,
        )


def test_real_pypdf_encrypted_content_is_rejected() -> None:
    pdf = _render_pdf(feature="encrypted")
    assert PdfReader(BytesIO(pdf), strict=True).is_encrypted

    with pytest.raises(ArkEntitlementError, match="encrypted"):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=_snapshot_bytes(pdf),
            evidence_pdf_bytes=pdf,
        )


@pytest.mark.parametrize("kind", ["payload", "second-revision", "multiple-eof"])
def test_pdf_rejects_every_non_whitespace_or_multiple_revision_trailer(kind: str) -> None:
    pdf = _pdf_trailer_variant(kind)
    with pytest.raises(ArkEntitlementError, match="one complete revision|trailing payload"):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=_snapshot_bytes(pdf),
            evidence_pdf_bytes=pdf,
        )


def test_pdf_allows_only_pdf_whitespace_after_the_single_eof() -> None:
    pdf = _pdf_trailer_variant("pdf-whitespace")
    bundle, data_by_path = build_ark_canary_entitlement_bundle(
        snapshot_bytes=_snapshot_bytes(pdf),
        evidence_pdf_bytes=pdf,
    )
    assert len(bundle.content.objects) == 2
    assert data_by_path[ENTITLEMENT_EVIDENCE_PATH] == pdf


def test_freezer_rejects_nonempty_pdf_trailer_and_accepts_pdf_whitespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ark_entitlement, "datetime", FrozenDateTime)
    snapshot_path = tmp_path / "snapshot.json"
    pdf_path = tmp_path / "entitlement.pdf"
    invalid_pdf = _pdf_trailer_variant("payload")
    snapshot_path.write_bytes(_snapshot_bytes(invalid_pdf))
    pdf_path.write_bytes(invalid_pdf)

    with pytest.raises(ArkEntitlementError, match="one complete revision|trailing payload"):
        freeze_ark_canary_entitlement_candidate(
            snapshot_path=snapshot_path,
            evidence_pdf_path=pdf_path,
            output_root=tmp_path / "invalid-store",
        )
    assert not (tmp_path / "invalid-store").exists()

    valid_pdf = _pdf_trailer_variant("pdf-whitespace")
    snapshot_path.write_bytes(_snapshot_bytes(valid_pdf))
    pdf_path.write_bytes(valid_pdf)
    frozen = freeze_ark_canary_entitlement_candidate(
        snapshot_path=snapshot_path,
        evidence_pdf_path=pdf_path,
        output_root=tmp_path / "valid-store",
    )
    assert frozen.raw_evidence_sha256 == hashlib.sha256(valid_pdf).hexdigest()


@pytest.mark.parametrize("kind", ["payload", "second-revision", "multiple-eof"])
def test_trusted_loader_revalidates_pdf_trailer_from_reviewed_cas(
    kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle, data_by_path = _unchecked_pdf_profile(_pdf_trailer_variant(kind))
    prepared = _materialize_bundle(
        tmp_path / kind,
        bundle=bundle,
        data_by_path=data_by_path,
    )
    _trust(prepared, monkeypatch)

    with pytest.raises(ArkEntitlementError, match="one complete revision|trailing payload"):
        load_trusted_ark_entitlement(
            reviewed_bundle_id=prepared.bundle.bundle_id,
            manifest_path=prepared.manifest_path,
            object_root=prepared.object_root,
            at=LOAD_AT,
        )


def test_trusted_loader_accepts_pdf_whitespace_after_the_single_eof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _materialize(
        tmp_path / "store",
        pdf=_pdf_trailer_variant("pdf-whitespace"),
    )
    _trust(prepared, monkeypatch)
    trusted = load_trusted_ark_entitlement(
        reviewed_bundle_id=prepared.bundle.bundle_id,
        manifest_path=prepared.manifest_path,
        object_root=prepared.object_root,
        at=LOAD_AT,
    )
    assert trusted.raw_evidence_sha256 == prepared.registry_entry.raw_evidence_sha256


def test_pdf_size_boundary_accepts_16_mib_and_rejects_one_more_byte() -> None:
    at_limit = _sized_pdf(MAX_ENTITLEMENT_PDF_BYTES)
    assert len(at_limit) == MAX_ENTITLEMENT_PDF_BYTES
    build_ark_canary_entitlement_bundle(
        snapshot_bytes=_snapshot_bytes(at_limit),
        evidence_pdf_bytes=at_limit,
    )

    over_limit = _sized_pdf(MAX_ENTITLEMENT_PDF_BYTES + 1)
    assert len(over_limit) == MAX_ENTITLEMENT_PDF_BYTES + 1
    with pytest.raises(ArkEntitlementError, match="16 MiB"):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=_snapshot_bytes(over_limit),
            evidence_pdf_bytes=over_limit,
        )


def test_validity_boundaries_and_exact_expiry_are_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = _render_pdf()
    four_hours = CAPTURED_AT + timedelta(hours=4)
    build_ark_canary_entitlement_bundle(
        snapshot_bytes=_snapshot_bytes(
            pdf,
            source_valid_until=None,
            valid_until=four_hours.isoformat(),
        ),
        evidence_pdf_bytes=pdf,
    )
    with pytest.raises(ArkEntitlementError, match="invalid entitlement snapshot JSON"):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=_snapshot_bytes(
                pdf,
                source_valid_until=None,
                valid_until=(four_hours + timedelta(microseconds=1)).isoformat(),
            ),
            evidence_pdf_bytes=pdf,
        )

    prepared = _materialize(tmp_path / "store")
    _trust(prepared, monkeypatch)
    trusted = load_trusted_ark_entitlement(
        reviewed_bundle_id=prepared.bundle.bundle_id,
        manifest_path=prepared.manifest_path,
        object_root=prepared.object_root,
        at=VALID_UNTIL - timedelta(microseconds=1),
    )
    assert trusted.valid_until == VALID_UNTIL

    with pytest.raises(ArkEntitlementError, match="outside.*validity"):
        load_trusted_ark_entitlement(
            reviewed_bundle_id=prepared.bundle.bundle_id,
            manifest_path=prepared.manifest_path,
            object_root=prepared.object_root,
            at=VALID_UNTIL,
        )


def test_validity_is_capped_by_source_and_shanghai_capture_day() -> None:
    pdf = _render_pdf()
    source_boundary = CAPTURED_AT + timedelta(hours=1)
    build_ark_canary_entitlement_bundle(
        snapshot_bytes=_snapshot_bytes(
            pdf,
            source_valid_until=source_boundary.isoformat(),
            valid_until=source_boundary.isoformat(),
        ),
        evidence_pdf_bytes=pdf,
    )
    with pytest.raises(ArkEntitlementError, match="invalid entitlement snapshot JSON"):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=_snapshot_bytes(
                pdf,
                source_valid_until=source_boundary.isoformat(),
                valid_until=(source_boundary + timedelta(microseconds=1)).isoformat(),
            ),
            evidence_pdf_bytes=pdf,
        )

    late_capture = datetime(2026, 8, 15, 15, 0, tzinfo=UTC)  # 23:00 in Shanghai.
    shanghai_day_end = datetime(2026, 8, 15, 15, 59, 59, tzinfo=UTC)
    build_ark_canary_entitlement_bundle(
        snapshot_bytes=_snapshot_bytes(
            pdf,
            captured_at=late_capture.isoformat(),
            source_valid_until=None,
            valid_until=shanghai_day_end.isoformat(),
        ),
        evidence_pdf_bytes=pdf,
    )
    with pytest.raises(ArkEntitlementError, match="invalid entitlement snapshot JSON"):
        build_ark_canary_entitlement_bundle(
            snapshot_bytes=_snapshot_bytes(
                pdf,
                captured_at=late_capture.isoformat(),
                source_valid_until=None,
                valid_until=(shanghai_day_end + timedelta(microseconds=1)).isoformat(),
            ),
            evidence_pdf_bytes=pdf,
        )


def test_loader_rechecks_expiry_after_artifact_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _materialize(tmp_path / "store")
    _trust(prepared, monkeypatch)
    ExpiringDateTime.calls = 0
    monkeypatch.setattr(ark_entitlement, "datetime", ExpiringDateTime)

    with pytest.raises(ArkEntitlementError, match="outside.*validity"):
        load_trusted_ark_entitlement(
            reviewed_bundle_id=prepared.bundle.bundle_id,
            manifest_path=prepared.manifest_path,
            object_root=prepared.object_root,
        )
    assert ExpiringDateTime.calls == 3


def test_loader_verifies_each_cas_object_once_and_uses_those_opened_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _materialize(tmp_path / "store")
    _trust(prepared, monkeypatch)
    calls: list[str] = []
    original = ark_entitlement.EvidenceBundleReader._verify_object

    def counted_verify(reader: Any, item: EvidenceObject) -> bytes:
        calls.append(item.sha256)
        return original(reader, item)

    monkeypatch.setattr(
        ark_entitlement.EvidenceBundleReader,
        "_verify_object",
        counted_verify,
    )
    load_trusted_ark_entitlement(
        reviewed_bundle_id=prepared.bundle.bundle_id,
        manifest_path=prepared.manifest_path,
        object_root=prepared.object_root,
        at=LOAD_AT,
    )

    assert sorted(calls) == sorted(item.sha256 for item in prepared.bundle.content.objects)


def test_empty_registry_fails_before_manifest_or_cas_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def forbidden_read(*_: object, **__: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("unreviewed entitlement must stop before artifact reads")

    monkeypatch.setattr(ark_entitlement, "REVIEWED_ARK_ENTITLEMENT_EVIDENCE", ())
    monkeypatch.setattr(
        ark_entitlement.EvidenceBundleReader,
        "from_manifest",
        classmethod(forbidden_read),
    )
    monkeypatch.setattr(ark_entitlement, "_validate_fixed_store_layout", forbidden_read)

    with pytest.raises(ArkEntitlementError, match="not uniquely present"):
        load_trusted_ark_entitlement(
            reviewed_bundle_id="f" * 64,
            manifest_path=tmp_path / "must-not-read" / "bundle.json",
            object_root=tmp_path / "must-not-read" / "objects",
            at=LOAD_AT,
        )
    assert calls == 0


def test_registry_anchor_is_domain_separated_and_not_an_artifact_digest(
    tmp_path: Path,
) -> None:
    prepared = _materialize(tmp_path / "store")
    entry = prepared.registry_entry
    anchor = reviewed_ark_entitlement_anchor_sha256(entry)
    assert anchor not in {
        entry.bundle_id,
        entry.logical_tree_sha256,
        entry.snapshot_contract_sha256,
        entry.raw_evidence_sha256,
    }
    assert (
        reviewed_ark_entitlement_anchor_sha256(
            replace(entry, reviewed_at=entry.reviewed_at.astimezone(UTC))
        )
        == anchor
    )
    assert (
        reviewed_ark_entitlement_anchor_sha256(replace(entry, credential_binding_sha256="c" * 64))
        != anchor
    )


@pytest.mark.parametrize(
    "duplicate_field",
    [
        "bundle_id",
        "logical_tree_sha256",
        "snapshot_contract_sha256",
        "raw_evidence_sha256",
    ],
)
def test_registry_rejects_each_duplicate_artifact_identity_before_disk_read(
    duplicate_field: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _materialize(tmp_path / "store")
    original = prepared.registry_entry
    second = replace(
        original,
        bundle_id="1" * 64,
        logical_tree_sha256="2" * 64,
        snapshot_contract_sha256="3" * 64,
        raw_evidence_sha256="4" * 64,
        reviewed_at=original.reviewed_at + timedelta(microseconds=1),
    )
    second = replace(second, **{duplicate_field: getattr(original, duplicate_field)})
    monkeypatch.setattr(
        ark_entitlement,
        "REVIEWED_ARK_ENTITLEMENT_EVIDENCE",
        (original, second),
    )

    with pytest.raises(ArkEntitlementError, match="duplicate identity"):
        ark_entitlement.require_reviewed_ark_entitlement(
            original.bundle_id,
            at=LOAD_AT,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("logical_tree_sha256", "1" * 64),
        ("snapshot_contract_sha256", "2" * 64),
        ("raw_evidence_sha256", "3" * 64),
        ("account_scope_sha256", "4" * 64),
        ("credential_binding_sha256", "5" * 64),
        ("captured_at", CAPTURED_AT + timedelta(microseconds=1)),
        ("valid_until", VALID_UNTIL - timedelta(microseconds=1)),
        ("provider", "other-provider"),
        ("model", "doubao-seedance-2-0"),
        ("region", "cn-shanghai"),
        ("operation", "contents.generations.tasks.get"),
        ("profile", "ark-canary-entitlement-v2"),
    ],
)
def test_loader_rejects_each_registry_to_bundle_or_snapshot_mapping_drift(
    field: str,
    value: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _materialize(tmp_path / "store")
    drifted = replace(prepared.registry_entry, **{field: value})
    monkeypatch.setattr(
        ark_entitlement,
        "REVIEWED_ARK_ENTITLEMENT_EVIDENCE",
        (drifted,),
    )

    with pytest.raises(ArkEntitlementError, match="profile|binding"):
        load_trusted_ark_entitlement(
            reviewed_bundle_id=prepared.bundle.bundle_id,
            manifest_path=prepared.manifest_path,
            object_root=prepared.object_root,
            at=LOAD_AT,
        )


@pytest.mark.parametrize("mutation", ["extra-object", "two-captures", "wrong-role"])
def test_loader_rejects_nonexact_two_member_one_capture_profiles(
    mutation: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _materialize(tmp_path / "original")
    bundle = prepared.bundle
    data = dict(prepared.data_by_path)
    objects = list(bundle.content.objects)
    members = list(bundle.content.members)
    captures = list(bundle.content.captures)

    if mutation == "extra-object":
        extra_data = b"not part of the fixed entitlement profile"
        extra_object = EvidenceObject(
            sha256=hashlib.sha256(extra_data).hexdigest(),
            size_bytes=len(extra_data),
            media_type="text/plain",
        )
        objects.append(extra_object)
        members.append(
            EvidenceMember(
                logical_path="evidence/extra.txt",
                role="entitlement.extra",
                object_sha256=extra_object.sha256,
            )
        )
        captures[0] = captures[0].model_copy(
            update={
                "member_paths": (
                    ENTITLEMENT_EVIDENCE_PATH,
                    "evidence/extra.txt",
                    ENTITLEMENT_SNAPSHOT_PATH,
                )
            }
        )
        data["evidence/extra.txt"] = extra_data
    elif mutation == "two-captures":
        original = captures[0]
        captures = [
            EvidenceCapture(
                capture_id="entitlement-evidence",
                kind=original.kind,
                source_url=original.source_url,
                source_updated_at=None,
                captured_at=original.captured_at,
                valid_until=original.valid_until,
                acquisition=original.acquisition,
                member_paths=(ENTITLEMENT_EVIDENCE_PATH,),
            ),
            EvidenceCapture(
                capture_id="entitlement-snapshot",
                kind=original.kind,
                source_url=original.source_url,
                source_updated_at=None,
                captured_at=original.captured_at,
                valid_until=original.valid_until,
                acquisition=original.acquisition,
                member_paths=(ENTITLEMENT_SNAPSHOT_PATH,),
            ),
        ]
    else:
        members[0] = members[0].model_copy(update={"role": "entitlement.wrong"})

    mutated = build_evidence_bundle(
        created_at=bundle.content.created_at,
        objects=objects,
        members=members,
        captures=captures,
    )
    candidate = _materialize_bundle(
        tmp_path / mutation,
        bundle=mutated,
        data_by_path=data,
    )
    _trust(candidate, monkeypatch)

    with pytest.raises(ArkEntitlementError, match="exactly|profile"):
        load_trusted_ark_entitlement(
            reviewed_bundle_id=candidate.bundle.bundle_id,
            manifest_path=candidate.manifest_path,
            object_root=candidate.object_root,
            at=LOAD_AT,
        )


def test_loader_rejects_noncanonical_stored_snapshot_even_when_all_digests_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _materialize(tmp_path / "original")
    pretty_snapshot = (
        json.dumps(
            prepared.snapshot.model_dump(mode="json"),
            sort_keys=False,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        + b"\n"
    )
    snapshot_object = EvidenceObject(
        sha256=hashlib.sha256(pretty_snapshot).hexdigest(),
        size_bytes=len(pretty_snapshot),
        media_type="application/json",
    )
    pdf_member, snapshot_member = prepared.bundle.content.members
    pdf_object = next(
        item for item in prepared.bundle.content.objects if item.sha256 == pdf_member.object_sha256
    )
    changed_snapshot_member = snapshot_member.model_copy(
        update={"object_sha256": snapshot_object.sha256}
    )
    changed_bundle = build_evidence_bundle(
        created_at=prepared.bundle.content.created_at,
        objects=(pdf_object, snapshot_object),
        members=(pdf_member, changed_snapshot_member),
        captures=prepared.bundle.content.captures,
    )
    candidate = _materialize_bundle(
        tmp_path / "noncanonical",
        bundle=changed_bundle,
        data_by_path={
            ENTITLEMENT_EVIDENCE_PATH: prepared.data_by_path[ENTITLEMENT_EVIDENCE_PATH],
            ENTITLEMENT_SNAPSHOT_PATH: pretty_snapshot,
        },
    )
    _trust(candidate, monkeypatch)

    with pytest.raises(ArkEntitlementError, match="not canonical JSON"):
        load_trusted_ark_entitlement(
            reviewed_bundle_id=candidate.bundle.bundle_id,
            manifest_path=candidate.manifest_path,
            object_root=candidate.object_root,
            at=LOAD_AT,
        )


@pytest.mark.parametrize("drift", ["missing", "same-size-tamper", "wrong-size"])
def test_loader_rejects_cas_drift(
    drift: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _materialize(tmp_path / "store")
    _trust(prepared, monkeypatch)
    pdf_digest = prepared.registry_entry.raw_evidence_sha256
    object_path = prepared.object_root / pdf_digest[:2] / pdf_digest
    if drift == "missing":
        object_path.unlink()
    elif drift == "same-size-tamper":
        original = object_path.read_bytes()
        object_path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    else:
        object_path.write_bytes(object_path.read_bytes() + b"x")

    with pytest.raises(EvidenceBundleError, match="CAS|digest|size|missing"):
        load_trusted_ark_entitlement(
            reviewed_bundle_id=prepared.bundle.bundle_id,
            manifest_path=prepared.manifest_path,
            object_root=prepared.object_root,
            at=LOAD_AT,
        )


def test_freezer_is_idempotent_and_never_replaces_a_conflicting_cas_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = _render_pdf()
    snapshot = tmp_path / "snapshot.json"
    evidence = tmp_path / "entitlement.pdf"
    output = tmp_path / "store"
    snapshot.write_bytes(_snapshot_bytes(pdf))
    evidence.write_bytes(pdf)
    monkeypatch.setattr(ark_entitlement, "datetime", FrozenDateTime)

    first = freeze_ark_canary_entitlement_candidate(
        snapshot_path=snapshot,
        evidence_pdf_path=evidence,
        output_root=output,
    )
    before = {
        path.relative_to(output).as_posix(): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }
    second = freeze_ark_canary_entitlement_candidate(
        snapshot_path=snapshot,
        evidence_pdf_path=evidence,
        output_root=output,
    )
    after = {
        path.relative_to(output).as_posix(): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }
    assert second == first
    assert after == before

    pdf_digest = first.raw_evidence_sha256
    object_path = first.object_root / pdf_digest[:2] / pdf_digest
    conflict = b"x" * len(object_path.read_bytes())
    object_path.write_bytes(conflict)
    with pytest.raises(ArkEntitlementError, match="existing entitlement CAS object conflicts"):
        freeze_ark_canary_entitlement_candidate(
            snapshot_path=snapshot,
            evidence_pdf_path=evidence,
            output_root=output,
        )
    assert object_path.read_bytes() == conflict


def test_loader_rejects_wrong_store_layout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _materialize(tmp_path / "store")
    _trust(prepared, monkeypatch)
    alias = prepared.root / "renamed.json"
    alias.write_bytes(prepared.manifest_path.read_bytes())

    with pytest.raises(ArkEntitlementError, match="fixed objects/bundles layout"):
        load_trusted_ark_entitlement(
            reviewed_bundle_id=prepared.bundle.bundle_id,
            manifest_path=alias,
            object_root=prepared.object_root,
            at=LOAD_AT,
        )


def test_loader_rejects_a_link_at_the_exact_manifest_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _materialize(tmp_path / "store")
    _trust(prepared, monkeypatch)
    outside = tmp_path / "outside-manifest.json"
    outside.write_bytes(prepared.manifest_path.read_bytes())
    prepared.manifest_path.unlink()
    try:
        os.symlink(outside, prepared.manifest_path)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")

    with pytest.raises(ArkEntitlementError, match="links or junctions"):
        load_trusted_ark_entitlement(
            reviewed_bundle_id=prepared.bundle.bundle_id,
            manifest_path=prepared.manifest_path,
            object_root=prepared.object_root,
            at=LOAD_AT,
        )


@pytest.mark.skipif(os.name != "nt", reason="drive-relative paths are Windows-only")
def test_drive_relative_path_is_rejected_before_absolute_or_any_file_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    absolute_calls = 0
    read_calls = 0

    def forbidden_absolute(_path: Path) -> Path:
        nonlocal absolute_calls
        absolute_calls += 1
        raise AssertionError("drive-relative input must be rejected before absolute()")

    def forbidden_read(*_: object, **__: object) -> bytes:
        nonlocal read_calls
        read_calls += 1
        raise AssertionError("drive-relative input must be rejected before reading")

    monkeypatch.setattr(Path, "absolute", forbidden_absolute)
    monkeypatch.setattr(ark_entitlement, "_read_regular_bytes", forbidden_read)

    with pytest.raises(ArkEntitlementError, match="drive-relative"):
        freeze_ark_canary_entitlement_candidate(
            snapshot_path=Path(r"C:relative\snapshot.json"),
            evidence_pdf_path=tmp_path / "must-not-read.pdf",
            output_root=tmp_path / "must-not-create",
        )
    assert absolute_calls == 0
    assert read_calls == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows drive types are Windows-only")
@pytest.mark.parametrize("remote_check", [2, 3], ids=["absolute", "resolved"])
def test_remote_drive_discovered_after_absolute_or_resolve_is_rejected_before_read(
    remote_check: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_bytes(b"must not be read")
    drive_type_calls = 0
    read_calls = 0

    def sequenced_drive_type(_anchor: str) -> int:
        nonlocal drive_type_calls
        drive_type_calls += 1
        return 4 if drive_type_calls == remote_check else 3

    def forbidden_read(*_: object, **__: object) -> bytes:
        nonlocal read_calls
        read_calls += 1
        raise AssertionError("a remote-drive input must be rejected before reading")

    monkeypatch.setattr(ark_entitlement, "_windows_drive_type", sequenced_drive_type)
    monkeypatch.setattr(ark_entitlement, "_read_regular_bytes", forbidden_read)

    with pytest.raises(ArkEntitlementError, match="mapped network drives"):
        freeze_ark_canary_entitlement_candidate(
            snapshot_path=snapshot_path,
            evidence_pdf_path=tmp_path / "must-not-read.pdf",
            output_root=tmp_path / "must-not-create",
        )
    assert drive_type_calls == remote_check
    assert read_calls == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows drive types are Windows-only")
def test_fixed_local_drive_type_allows_offline_freezing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = _render_pdf()
    snapshot_path = tmp_path / "snapshot.json"
    pdf_path = tmp_path / "entitlement.pdf"
    snapshot_path.write_bytes(_snapshot_bytes(pdf))
    pdf_path.write_bytes(pdf)
    drive_type_calls = 0

    def fixed_drive_type(_anchor: str) -> int:
        nonlocal drive_type_calls
        drive_type_calls += 1
        return 3

    def forbidden_network(*_: object, **__: object) -> None:
        raise AssertionError("local-drive entitlement freezing must remain offline")

    monkeypatch.setattr(ark_entitlement, "_windows_drive_type", fixed_drive_type)
    monkeypatch.setattr(ark_entitlement, "datetime", FrozenDateTime)
    monkeypatch.setattr(socket, "create_connection", forbidden_network)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden_network)
    monkeypatch.setattr(httpx.Client, "send", forbidden_network)
    monkeypatch.setattr(httpx.AsyncClient, "send", forbidden_network)

    frozen = freeze_ark_canary_entitlement_candidate(
        snapshot_path=snapshot_path,
        evidence_pdf_path=pdf_path,
        output_root=tmp_path / "local-store",
    )
    assert drive_type_calls > 0
    assert frozen.manifest_path.is_file()


def test_freezer_rejects_protected_paths_and_source_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = _render_pdf()
    snapshot = tmp_path / "snapshot.json"
    evidence = tmp_path / "entitlement.pdf"
    snapshot.write_bytes(_snapshot_bytes(pdf))
    evidence.write_bytes(pdf)
    monkeypatch.setattr(ark_entitlement, "datetime", FrozenDateTime)

    with pytest.raises(ArkEntitlementError, match="protected archive"):
        freeze_ark_canary_entitlement_candidate(
            snapshot_path=snapshot,
            evidence_pdf_path=evidence,
            output_root=tmp_path / "canary" / "entitlement",
        )

    linked = tmp_path / "linked-entitlement.pdf"
    try:
        os.symlink(evidence, linked)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    with pytest.raises(ArkEntitlementError, match="links or junctions"):
        freeze_ark_canary_entitlement_candidate(
            snapshot_path=snapshot,
            evidence_pdf_path=linked,
            output_root=tmp_path / "safe-output",
        )


def test_freeze_and_trusted_load_are_zero_network_and_registry_stays_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = _render_pdf()
    snapshot_path = tmp_path / "snapshot.json"
    pdf_path = tmp_path / "entitlement.pdf"
    snapshot_path.write_bytes(_snapshot_bytes(pdf))
    pdf_path.write_bytes(pdf)

    def forbidden_network(*_: object, **__: object) -> None:
        raise AssertionError("entitlement trust must remain offline")

    monkeypatch.setattr(socket, "create_connection", forbidden_network)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden_network)
    monkeypatch.setattr(httpx.Client, "send", forbidden_network)
    monkeypatch.setattr(httpx.AsyncClient, "send", forbidden_network)
    monkeypatch.setattr(ark_entitlement, "datetime", FrozenDateTime)
    before = ark_entitlement.REVIEWED_ARK_ENTITLEMENT_EVIDENCE

    frozen = freeze_ark_canary_entitlement_candidate(
        snapshot_path=snapshot_path,
        evidence_pdf_path=pdf_path,
        output_root=tmp_path / "store",
    )
    assert ark_entitlement.REVIEWED_ARK_ENTITLEMENT_EVIDENCE == before == ()

    stored_snapshot = ArkCanaryEntitlementSnapshot.model_validate_json(
        (
            frozen.object_root
            / frozen.bundle.content.members[1].object_sha256[:2]
            / frozen.bundle.content.members[1].object_sha256
        ).read_bytes()
    )
    entry = _registry_entry(
        frozen.bundle,
        stored_snapshot,
        raw_evidence_sha256=frozen.raw_evidence_sha256,
    )
    monkeypatch.setattr(
        ark_entitlement,
        "REVIEWED_ARK_ENTITLEMENT_EVIDENCE",
        (entry,),
    )
    trusted = load_trusted_ark_entitlement(
        reviewed_bundle_id=frozen.bundle.bundle_id,
        manifest_path=frozen.manifest_path,
        object_root=frozen.object_root,
        at=LOAD_AT,
    )
    assert trusted.entitlement_anchor_sha256 == reviewed_ark_entitlement_anchor_sha256(entry)


def test_freezer_files_cli_stdout_and_errors_never_leak_private_digest_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    account_id = "raw-account-scope-marker-001"
    subaccount_id = "raw-subaccount-marker-002"
    project_id = "raw-project-marker-003"
    resource_locator = "vault://private/ark-key/version-7"
    key_marker = "raw-api-key-marker-must-never-appear"
    salt = b"SALT-MARKER-" + b"x" * 20
    account_digest = account_scope_sha256(
        account_id=account_id,
        subaccount_id=subaccount_id,
        project_id=project_id,
        private_salt=salt,
    )
    credential_digest = credential_binding_sha256(
        secret_store="vault",
        resource_locator=resource_locator,
        immutable_version="version-7",
        private_salt=salt,
    )
    pdf = _render_pdf()
    snapshot_path = tmp_path / "snapshot.json"
    pdf_path = tmp_path / "entitlement.pdf"
    output_root = tmp_path / "store"
    snapshot_path.write_bytes(
        _snapshot_bytes(
            pdf,
            account_scope_sha256=account_digest,
            credential_binding_sha256=credential_digest,
        )
    )
    pdf_path.write_bytes(pdf)
    monkeypatch.setattr(ark_entitlement, "datetime", FrozenDateTime)

    assert (
        ark_entitlement.main(
            [
                "--snapshot",
                str(snapshot_path),
                "--evidence-pdf",
                str(pdf_path),
                "--output-root",
                str(output_root),
            ]
        )
        == 0
    )
    stdout = capsys.readouterr().out
    output_bytes = b"".join(path.read_bytes() for path in output_root.rglob("*") if path.is_file())
    forbidden_text = (
        account_id,
        subaccount_id,
        project_id,
        resource_locator,
        key_marker,
        salt.hex(),
    )
    for marker in forbidden_text:
        assert marker not in stdout
        assert marker.encode() not in output_bytes
    assert salt not in output_bytes

    with pytest.raises(ArkEntitlementError) as account_error:
        account_scope_sha256(
            account_id=account_id + "\n",
            subaccount_id=None,
            project_id=None,
            private_salt=salt,
        )
    with pytest.raises(ArkEntitlementError) as credential_error:
        credential_binding_sha256(
            secret_store="vault",
            resource_locator=resource_locator + "\n" + key_marker,
            immutable_version="version-7",
            private_salt=salt,
        )
    rendered_errors = f"{account_error.value}\n{credential_error.value}"
    for marker in forbidden_text:
        assert marker not in rendered_errors
