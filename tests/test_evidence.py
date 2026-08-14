import hashlib
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from sdc.canary import contract_sha256
from sdc.contracts import (
    EvidenceAcquisition,
    EvidenceBundle,
    EvidenceBundleContent,
    EvidenceCapture,
    EvidenceMember,
    EvidenceObject,
    ProviderCapabilitySnapshot,
    ProviderPricingSnapshot,
    ProviderRequest,
    evidence_bundle_content_sha256,
    provider_request_fingerprint,
)
from sdc.evidence import (
    EvidenceBundleError,
    EvidenceBundleExpiredError,
    EvidenceBundleNotYetValidError,
    EvidenceBundleReader,
    EvidenceBundleUnverifiedOriginError,
    build_evidence_bundle,
    load_evidence_bundle,
)

CAPTURED = datetime(2026, 8, 14, 8, tzinfo=UTC)
CREATED = CAPTURED + timedelta(minutes=5)
VALID_UNTIL = CAPTURED + timedelta(hours=12)


def descriptor(data: bytes, media_type: str) -> EvidenceObject:
    return EvidenceObject(
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        media_type=media_type,
    )


def capture(
    capture_id: str,
    kind: str,
    member_paths: tuple[str, ...],
    *,
    acquisition: EvidenceAcquisition = EvidenceAcquisition.FRESH,
    origin_anchor_sha256: str | None = None,
    origin_valid_until: datetime | None = None,
    source_url: str = "https://docs.volcengine.com/docs/82379/1330310",
    captured_at: datetime = CAPTURED,
    valid_until: datetime = VALID_UNTIL,
) -> EvidenceCapture:
    return EvidenceCapture(
        capture_id=capture_id,
        kind=kind,
        source_url=source_url,
        source_updated_at=captured_at - timedelta(days=1),
        captured_at=captured_at,
        valid_until=valid_until,
        acquisition=acquisition,
        origin_anchor_sha256=origin_anchor_sha256,
        origin_valid_until=origin_valid_until,
        member_paths=member_paths,
    )


def sample_bundle() -> tuple[EvidenceBundle, dict[str, bytes]]:
    capability_pdf = b"capability evidence"
    pricing_pdf = b"pricing evidence"
    objects = (
        descriptor(capability_pdf, "application/pdf"),
        descriptor(pricing_pdf, "application/pdf"),
    )
    members = (
        EvidenceMember(
            logical_path="evidence/capability.pdf",
            role="capability",
            object_sha256=objects[0].sha256,
        ),
        EvidenceMember(
            logical_path="evidence/capability-copy.pdf",
            role="capability",
            object_sha256=objects[0].sha256,
        ),
        EvidenceMember(
            logical_path="evidence/pricing.pdf",
            role="pricing",
            object_sha256=objects[1].sha256,
        ),
    )
    captures = (
        capture(
            "capability",
            "official-doc",
            ("evidence/capability-copy.pdf", "evidence/capability.pdf"),
        ),
        capture(
            "pricing",
            "official-doc",
            ("evidence/pricing.pdf",),
            source_url="https://docs.volcengine.com/docs/82379/1544106",
        ),
    )
    bundle = build_evidence_bundle(
        created_at=CREATED,
        objects=reversed(objects),
        members=reversed(members),
        captures=reversed(captures),
    )
    return bundle, {
        objects[0].sha256: capability_pdf,
        objects[1].sha256: pricing_pdf,
    }


def populate_cas(root: Path, objects: dict[str, bytes]) -> None:
    for digest, data in objects.items():
        target = root / digest[:2] / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def test_bundle_is_canonical_round_trips_and_has_no_live_authority() -> None:
    bundle, _ = sample_bundle()

    parsed = EvidenceBundle.model_validate_json(bundle.model_dump_json())

    assert parsed == bundle
    assert bundle.document_type == "sdc.evidence-bundle"
    assert bundle.bundle_id == "23c60083b366534caf113103c8a5ee1c2b1b4de4be4135b1962d2fb17b6bca86"
    assert (
        bundle.content.resolved_logical_tree_sha256
        == "49a5c29930b41048e366d38323b0bebfa293db1264c9d306da25ac62f9c5ab38"
    )
    assert bundle.content.valid_until == VALID_UNTIL
    assert [item.logical_path for item in bundle.content.members] == sorted(
        item.logical_path for item in bundle.content.members
    )
    assert set(EvidenceBundle.model_fields) == {
        "schema_version",
        "document_type",
        "bundle_id",
        "content",
    }
    with pytest.raises(ValidationError):
        EvidenceBundle.model_validate({**bundle.model_dump(mode="json"), "authorization": {}})


def test_bundle_identity_normalizes_equivalent_timezone_offsets() -> None:
    bundle, _ = sample_bundle()
    plus_eight = timezone(timedelta(hours=8))
    shifted_captures = tuple(
        EvidenceCapture.model_validate(
            {
                **item.model_dump(mode="python"),
                "source_updated_at": item.source_updated_at.astimezone(plus_eight)
                if item.source_updated_at is not None
                else None,
                "captured_at": item.captured_at.astimezone(plus_eight),
                "valid_until": item.valid_until.astimezone(plus_eight),
            }
        )
        for item in bundle.content.captures
    )

    rebuilt = build_evidence_bundle(
        created_at=bundle.content.created_at.astimezone(plus_eight),
        objects=bundle.content.objects,
        members=bundle.content.members,
        captures=shifted_captures,
    )

    assert rebuilt == bundle


def test_reader_verifies_deduplicated_objects_and_resolves_members(tmp_path: Path) -> None:
    bundle, objects = sample_bundle()
    cas = tmp_path / "objects"
    populate_cas(cas, objects)

    resolved = EvidenceBundleReader(
        bundle, cas, expected_bundle_id=bundle.bundle_id
    ).verify()

    assert len(resolved) == 3
    assert resolved[0].data is resolved[1].data
    assert resolved[0].data == b"capability evidence"
    assert EvidenceBundleReader(
        bundle, cas, expected_bundle_id=bundle.bundle_id
    ).resolve("evidence/pricing.pdf").data == b"pricing evidence"


def test_reader_rejects_missing_tampered_and_wrong_size_objects(tmp_path: Path) -> None:
    bundle, objects = sample_bundle()
    cas = tmp_path / "objects"
    populate_cas(cas, objects)
    first = bundle.content.objects[0]
    first_path = cas / first.sha256[:2] / first.sha256
    first_path.unlink()
    with pytest.raises(EvidenceBundleError, match="missing"):
        EvidenceBundleReader(bundle, cas, expected_bundle_id=bundle.bundle_id).verify()

    first_path.write_bytes(b"tampered evidence")
    with pytest.raises(EvidenceBundleError, match="size|digest"):
        EvidenceBundleReader(bundle, cas, expected_bundle_id=bundle.bundle_id).verify()

    first_path.write_bytes(b"x" * first.size_bytes)
    with pytest.raises(EvidenceBundleError, match="digest"):
        EvidenceBundleReader(bundle, cas, expected_bundle_id=bundle.bundle_id).verify()


def test_reader_rejects_symlink_escape_when_supported(tmp_path: Path) -> None:
    bundle, objects = sample_bundle()
    cas = tmp_path / "objects"
    populate_cas(cas, objects)
    first = bundle.content.objects[0]
    candidate = cas / first.sha256[:2] / first.sha256
    outside = tmp_path / "outside"
    outside.write_bytes(objects[first.sha256])
    candidate.unlink()
    try:
        os.symlink(outside, candidate)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")

    with pytest.raises(EvidenceBundleError, match="link|junction"):
        EvidenceBundleReader(bundle, cas, expected_bundle_id=bundle.bundle_id).verify()


@pytest.mark.parametrize(
    "logical_path",
    [
        "../secret",
        ".",
        "/absolute",
        "//server/share",
        "C:/windows",
        "folder\\file",
        "file:stream",
        "folder/file?.pdf",
        "CON.txt",
        "COM¹.txt",
        "folder//double",
        f"folder/{'x' * 256}",
        "folder/trailing. ",
        "folder/\x01control",
    ],
)
def test_member_rejects_nonportable_or_escaping_logical_paths(logical_path: str) -> None:
    with pytest.raises(ValidationError):
        EvidenceMember(
            logical_path=logical_path,
            role="capability",
            object_sha256="a" * 64,
        )


def test_bundle_rejects_casefold_collision_and_inexact_object_closure() -> None:
    item = descriptor(b"same", "application/pdf")
    with pytest.raises(EvidenceBundleError):
        build_evidence_bundle(
            created_at=CREATED,
            objects=(item,),
            members=(
                EvidenceMember(
                    logical_path="Evidence/item.pdf",
                    role="capability",
                    object_sha256=item.sha256,
                ),
                EvidenceMember(
                    logical_path="evidence/item.pdf",
                    role="capability",
                    object_sha256=item.sha256,
                ),
            ),
            captures=(
                capture(
                    "capability",
                    "official-doc",
                    ("Evidence/item.pdf", "evidence/item.pdf"),
                ),
            ),
        )

    unreferenced = descriptor(b"unreferenced", "application/pdf")
    with pytest.raises(EvidenceBundleError):
        build_evidence_bundle(
            created_at=CREATED,
            objects=(item, unreferenced),
            members=(
                EvidenceMember(
                    logical_path="evidence/item.pdf",
                    role="capability",
                    object_sha256=item.sha256,
                ),
            ),
            captures=(capture("capability", "official-doc", ("evidence/item.pdf",)),),
        )


def test_bundle_requires_one_capture_per_member_and_uses_earliest_expiry() -> None:
    item = descriptor(b"same", "application/pdf")
    member = EvidenceMember(
        logical_path="evidence/item.pdf",
        role="capability",
        object_sha256=item.sha256,
    )
    with pytest.raises(EvidenceBundleError):
        build_evidence_bundle(
            created_at=CREATED,
            objects=(item,),
            members=(member,),
            captures=(
                capture("a", "official-doc", (member.logical_path,)),
                capture("b", "official-doc", (member.logical_path,)),
            ),
        )

    second = descriptor(b"second", "application/pdf")
    early_expiry = VALID_UNTIL - timedelta(hours=1)
    bundle = build_evidence_bundle(
        created_at=CREATED,
        objects=(item, second),
        members=(
            member,
            EvidenceMember(
                logical_path="evidence/second.pdf",
                role="pricing",
                object_sha256=second.sha256,
            ),
        ),
        captures=(
            capture("a", "official-doc", (member.logical_path,)),
            capture(
                "b",
                "official-doc",
                ("evidence/second.pdf",),
                valid_until=early_expiry,
            ),
        ),
    )
    assert bundle.content.valid_until == early_expiry


def test_object_media_type_requires_canonical_lowercase() -> None:
    with pytest.raises(ValidationError):
        descriptor(b"content", "Application/PDF")


def test_object_and_bundle_resource_limits_fail_closed() -> None:
    with pytest.raises(ValidationError):
        EvidenceObject(
            sha256="a" * 64,
            size_bytes=64 * 1024 * 1024 + 1,
            media_type="application/pdf",
        )

    objects = tuple(
        EvidenceObject(
            sha256=f"{index:064x}",
            size_bytes=64 * 1024 * 1024,
            media_type="application/pdf",
        )
        for index in range(1, 10)
    )
    members = tuple(
        EvidenceMember(
            logical_path=f"evidence/{index}.pdf",
            role="capability",
            object_sha256=item.sha256,
        )
        for index, item in enumerate(objects, start=1)
    )
    captures = tuple(
        capture(
            f"capture-{index}",
            "official-doc",
            (member.logical_path,),
        )
        for index, member in enumerate(members, start=1)
    )
    with pytest.raises(EvidenceBundleError):
        build_evidence_bundle(
            created_at=CREATED,
            objects=objects,
            members=members,
            captures=captures,
        )


def test_capture_rejects_untrusted_source_and_invalid_provenance() -> None:
    with pytest.raises(ValidationError, match="approved Volcengine"):
        capture(
            "capability",
            "official-doc",
            ("evidence/capability.pdf",),
            source_url="https://docs.volcengine.com.evil.invalid/evidence",
        )
    for unsafe_url in (
        "http://docs.volcengine.com/docs/82379/1330310",
        "https://user@docs.volcengine.com/docs/82379/1330310",
        "https://docs.volcengine.com:444/docs/82379/1330310",
        "https://docs.volcengine.com/docs/82379/1330310?token=secret",
        "https://console.volcengine.com/ark?lang=zh",
        "https://docs.volcengine.com/docs/82379/1330310\\unsafe",
        "https://docs.volcengine.com/docs/82379/1330310\n",
    ):
        with pytest.raises(ValidationError, match="approved Volcengine"):
            capture(
                "capability",
                "official-doc",
                ("evidence/capability.pdf",),
                source_url=unsafe_url,
            )
    assert (
        capture(
            "capability",
            "official-doc",
            ("evidence/capability.pdf",),
            source_url="https://docs.volcengine.com/docs/82379/1330310?lang=zh",
        ).source_url
        == "https://docs.volcengine.com/docs/82379/1330310?lang=zh"
    )
    with pytest.raises(ValidationError, match="origin"):
        capture(
            "capability",
            "official-doc",
            ("evidence/capability.pdf",),
            acquisition=EvidenceAcquisition.INHERITED,
        )
    inherited = capture(
        "capability",
        "official-doc",
        ("evidence/capability.pdf",),
        acquisition=EvidenceAcquisition.INHERITED,
        origin_anchor_sha256="a" * 64,
        origin_valid_until=VALID_UNTIL,
    )
    assert inherited.valid_until == VALID_UNTIL
    item = descriptor(b"inherited", "application/pdf")
    with pytest.raises(EvidenceBundleError, match="verified-origin importer"):
        build_evidence_bundle(
            created_at=CREATED,
            objects=(item,),
            members=(
                EvidenceMember(
                    logical_path="evidence/inherited.pdf",
                    role="capability",
                    object_sha256=item.sha256,
                ),
            ),
            captures=(
                inherited.model_copy(
                    update={"member_paths": ("evidence/inherited.pdf",)}
                ),
            ),
        )
    with pytest.raises(ValidationError, match="extend"):
        capture(
            "capability",
            "official-doc",
            ("evidence/capability.pdf",),
            acquisition=EvidenceAcquisition.INHERITED,
            origin_anchor_sha256="a" * 64,
            origin_valid_until=VALID_UNTIL - timedelta(seconds=1),
        )
    with pytest.raises(ValidationError, match="timezone"):
        capture(
            "capability",
            "official-doc",
            ("evidence/capability.pdf",),
            captured_at=datetime(2026, 8, 14),
        )
    with pytest.raises(ValidationError, match="source_updated_at"):
        EvidenceCapture(
            capture_id="capability",
            kind="official-doc",
            source_url="https://docs.volcengine.com/docs/82379/1330310",
            source_updated_at=CAPTURED + timedelta(seconds=1),
            captured_at=CAPTURED,
            valid_until=VALID_UNTIL,
            acquisition=EvidenceAcquisition.FRESH,
            member_paths=("evidence/capability.pdf",),
        )


def test_expired_bundle_remains_parseable_but_freshness_fails_closed() -> None:
    bundle, _ = sample_bundle()
    reader = EvidenceBundleReader(
        bundle, Path("unused"), expected_bundle_id=bundle.bundle_id
    )

    assert EvidenceBundle.model_validate_json(bundle.model_dump_json()) == bundle
    reader.assert_current(at=VALID_UNTIL)
    with pytest.raises(EvidenceBundleNotYetValidError):
        reader.assert_current(at=CREATED - timedelta(microseconds=1))
    with pytest.raises(EvidenceBundleExpiredError):
        reader.assert_current(at=VALID_UNTIL + timedelta(microseconds=1))
    with pytest.raises(EvidenceBundleError, match="timezone"):
        reader.assert_current(at=datetime(2026, 8, 14))


def test_inherited_bundle_cannot_be_declared_current_without_origin_verification() -> None:
    bundle, _ = sample_bundle()
    payload = bundle.content.model_dump(mode="python")
    first_capture = {
        **payload["captures"][0],
        "acquisition": EvidenceAcquisition.INHERITED,
        "origin_anchor_sha256": "a" * 64,
        "origin_valid_until": VALID_UNTIL,
    }
    payload["captures"] = (first_capture, *payload["captures"][1:])
    content = EvidenceBundleContent.model_validate(payload)
    inherited = EvidenceBundle(
        bundle_id=evidence_bundle_content_sha256(content),
        content=content,
    )
    reader = EvidenceBundleReader(
        inherited,
        Path("unused"),
        expected_bundle_id=inherited.bundle_id,
    )

    with pytest.raises(EvidenceBundleUnverifiedOriginError):
        reader.assert_current(at=CREATED)


def test_manifest_loader_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    manifest = tmp_path / "bundle.json"
    manifest.write_text('{"schema_version":"1.0.0","schema_version":"1.0.0"}')

    with pytest.raises(EvidenceBundleError, match="duplicate JSON key"):
        load_evidence_bundle(manifest, expected_bundle_id="0" * 64)


def test_manifest_loader_rejects_oversized_input(tmp_path: Path) -> None:
    manifest = tmp_path / "bundle.json"
    manifest.write_bytes(b" " * (4 * 1024 * 1024 + 1))

    with pytest.raises(EvidenceBundleError, match="byte limit"):
        load_evidence_bundle(manifest, expected_bundle_id="0" * 64)


def test_manifest_loader_rejects_non_regular_input(tmp_path: Path) -> None:
    with pytest.raises(EvidenceBundleError, match="regular file"):
        load_evidence_bundle(tmp_path, expected_bundle_id="0" * 64)


def test_manifest_loader_normalizes_non_json_value_errors(tmp_path: Path) -> None:
    manifest = tmp_path / "bundle.json"
    manifest.write_text("9" * 5000, encoding="utf-8")

    with pytest.raises(EvidenceBundleError, match="invalid evidence bundle manifest"):
        load_evidence_bundle(manifest, expected_bundle_id="0" * 64)


def test_manifest_loader_can_bind_to_a_trusted_bundle_id(tmp_path: Path) -> None:
    bundle, _ = sample_bundle()
    manifest = tmp_path / "bundle.json"
    manifest.write_text(bundle.model_dump_json(), encoding="utf-8")

    assert load_evidence_bundle(manifest, expected_bundle_id=bundle.bundle_id) == bundle
    with pytest.raises(EvidenceBundleError, match="trusted bundle ID"):
        load_evidence_bundle(manifest, expected_bundle_id="0" * 64)
    with pytest.raises(EvidenceBundleError, match="trusted bundle ID"):
        EvidenceBundleReader(bundle, tmp_path, expected_bundle_id="0" * 64)


def test_bundle_id_and_tree_detect_descriptor_tampering() -> None:
    bundle, _ = sample_bundle()
    payload = bundle.model_dump(mode="json")
    payload["content"]["objects"][0]["media_type"] = "image/png"

    with pytest.raises(ValidationError, match="tree digest"):
        EvidenceBundle.model_validate(payload)

    payload = bundle.model_dump(mode="json")
    payload["bundle_id"] = "0" * 64
    with pytest.raises(ValidationError, match="bundle_id"):
        EvidenceBundle.model_validate(payload)


def test_builder_and_reader_revalidate_model_copy_inputs() -> None:
    bundle, _ = sample_bundle()
    bad_object = bundle.content.objects[0].model_copy(
        update={"media_type": "Application/PDF"}
    )
    with pytest.raises(EvidenceBundleError):
        build_evidence_bundle(
            created_at=bundle.content.created_at,
            objects=(bad_object, *bundle.content.objects[1:]),
            members=bundle.content.members,
            captures=bundle.content.captures,
        )

    bad_member = bundle.content.members[0].model_copy(update={"role": "INVALID"})
    bad_content = bundle.content.model_copy(
        update={"members": (bad_member, *bundle.content.members[1:])}
    )
    bad_bundle = bundle.model_copy(update={"content": bad_content})
    with pytest.raises(EvidenceBundleError, match="invalid evidence bundle"):
        EvidenceBundleReader(
            bad_bundle,
            Path("unused"),
            expected_bundle_id=bundle.bundle_id,
        )

    substituted_member = bundle.content.members[0].model_copy(
        update={"object_sha256": bundle.content.members[-1].object_sha256}
    )
    substituted_content = bundle.content.model_copy(
        update={"members": (substituted_member, *bundle.content.members[1:])}
    )
    substituted_bundle = bundle.model_copy(update={"content": substituted_content})
    with pytest.raises(EvidenceBundleError, match="invalid evidence bundle"):
        EvidenceBundleReader(
            substituted_bundle,
            Path("unused"),
            expected_bundle_id=bundle.bundle_id,
        )


def test_evidence_contracts_do_not_change_the_r6_request_fingerprint() -> None:
    request = ProviderRequest(
        run_id="sdc-canary-001-v02-r6-main-71bd325-20260813-01",
        job_id="job_a265074cbb6202d447d4",
        attempt=1,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        prompt="A paper lantern glows softly against a plain midnight background.",
        duration_ms=4000,
        aspect_ratio="9:16",
        resolution="1080p",
        generate_audio=False,
        request_fingerprint="0" * 64,
    )

    assert (
        provider_request_fingerprint(request)
        == "bbf514fb637145d1df616405082dfbb300ec35a34cff5f9181be76d22758de44"
    )


def test_evidence_contracts_do_not_change_the_r6_snapshot_hashes() -> None:
    capability = ProviderCapabilitySnapshot.model_validate(
        {
            "schema_version": "1.0.0",
            "snapshot_revision": "2026-08-13.v02-r6",
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
            "captured_at": "2026-08-13T17:14:11+08:00",
            "valid_until": "2026-08-13T23:59:59+08:00",
            "evidence_sha256": "116eb554e334f45d72e51002638fa0c78006b4196eafa4a43a81b169d6b0eb1f",
        }
    )
    pricing = ProviderPricingSnapshot.model_validate(
        {
            "schema_version": "1.0.0",
            "snapshot_revision": "2026-08-13.v02-r6",
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
            "captured_at": "2026-08-13T17:14:11+08:00",
            "valid_until": "2026-08-13T23:59:59+08:00",
            "evidence_sha256": "10c41d8af4ba5a2db1aff14441e6933a915beeaeb1544d6ef5d71d5c78acbc05",
        }
    )

    assert (
        contract_sha256(capability)
        == "c7f13d6c8f922d7dd233f712c0672a513661477fea3215c713f7415c5bb102cf"
    )
    assert (
        contract_sha256(pricing)
        == "d65f7be81cffbcc383cc355ba1dd78971d31211c1b0ecea9e5d03a1c8f24c3ea"
    )
