import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Self, cast

import pytest

import sdc.fresh_evidence as fresh_evidence
from sdc.canary import contract_sha256
from sdc.contracts import (
    EvidenceAcquisition,
    EvidenceBundle,
    EvidenceBundleContent,
    EvidenceCapture,
    EvidenceMember,
    EvidenceObject,
    PricingInputMode,
    ProviderCapabilitySnapshot,
    ProviderPricingSnapshot,
    SnapshotStatus,
    evidence_bundle_content_sha256,
    evidence_logical_tree_sha256,
)
from sdc.evidence import EvidenceBundleError, EvidenceBundleReader, build_evidence_bundle
from sdc.fresh_evidence import (
    CAPABILITY_EVIDENCE_PATH,
    CAPABILITY_SNAPSHOT_PATH,
    LEGACY_EVIDENCE_BUNDLE_IDS,
    PRICING_EVIDENCE_PATH,
    PRICING_SNAPSHOT_PATH,
    FreshEvidenceError,
    build_fresh_canary_evidence_bundle,
    freeze_fresh_canary_evidence,
    load_trusted_fresh_canary_evidence,
)
from sdc.fresh_evidence_registry import (
    FRESH_CANARY_PROFILE,
    ReviewedFreshEvidence,
)
from sdc.legacy_evidence_materialize import REVIEWED_ARCHIVE_CATALOG

CAPTURED_AT = datetime(2026, 8, 15, 1, tzinfo=UTC)
PRICING_CAPTURED_AT = CAPTURED_AT + timedelta(minutes=5)
PLANNED_AT = CAPTURED_AT + timedelta(hours=1)
VALID_UNTIL = CAPTURED_AT + timedelta(hours=12)
CAPABILITY_PDF = b"%PDF-1.7\nexecution-day capability evidence\n%%EOF\n"
PRICING_PDF = b"%PDF-1.7\nexecution-day pricing evidence\n%%EOF\n"


@dataclass(frozen=True)
class Candidate:
    bundle: EvidenceBundle
    data_by_path: Mapping[str, bytes]
    capability: ProviderCapabilitySnapshot
    pricing: ProviderPricingSnapshot


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz: object = None) -> Self:
        if tz is None:
            return cast(Self, PLANNED_AT.replace(tzinfo=None))
        return cast(Self, PLANNED_AT)


def _capability(**updates: object) -> ProviderCapabilitySnapshot:
    value = ProviderCapabilitySnapshot(
        snapshot_revision="2026-08-15.fresh-1",
        status=SnapshotStatus.CURRENT,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        aspect_ratios=("9:16",),
        resolutions=("1080p",),
        fps=24,
        min_duration_ms=4000,
        max_duration_ms=15000,
        source_url="https://docs.volcengine.com/docs/82379/1330310?lang=zh",
        source_updated_at=CAPTURED_AT - timedelta(days=1),
        captured_at=CAPTURED_AT,
        valid_until=VALID_UNTIL,
        evidence_sha256=hashlib.sha256(CAPABILITY_PDF).hexdigest(),
    )
    return value.model_copy(update=updates)


def _pricing(**updates: object) -> ProviderPricingSnapshot:
    value = ProviderPricingSnapshot(
        snapshot_revision="2026-08-15.fresh-1",
        status=SnapshotStatus.CURRENT,
        provider="volcengine_ark",
        model="doubao-seedance-2-0-260128",
        resolution="1080p",
        input_mode=PricingInputMode.WITHOUT_VIDEO,
        billing_unit="provider-token",
        unit_price_cny=Decimal("0.000001"),
        worst_case_units=Decimal("196425"),
        worst_case_cost_cny=Decimal("0.196425"),
        source_url="https://docs.volcengine.com/docs/82379/1544106?lang=zh",
        source_updated_at=CAPTURED_AT - timedelta(days=1),
        captured_at=PRICING_CAPTURED_AT,
        valid_until=VALID_UNTIL,
        evidence_sha256=hashlib.sha256(PRICING_PDF).hexdigest(),
    )
    return value.model_copy(update=updates)


def _candidate(
    *,
    capability: ProviderCapabilitySnapshot | None = None,
    pricing: ProviderPricingSnapshot | None = None,
) -> Candidate:
    capability = capability or _capability()
    pricing = pricing or _pricing()
    capability_json = capability.model_dump_json(indent=2).encode("utf-8")
    pricing_json = pricing.model_dump_json(indent=2).encode("utf-8")
    bundle, data_by_path = build_fresh_canary_evidence_bundle(
        capability_snapshot_bytes=capability_json,
        capability_evidence_bytes=CAPABILITY_PDF,
        pricing_snapshot_bytes=pricing_json,
        pricing_evidence_bytes=PRICING_PDF,
    )
    return Candidate(bundle, data_by_path, capability, pricing)


def _anchor(candidate: Candidate, *, bundle: EvidenceBundle | None = None) -> ReviewedFreshEvidence:
    selected = bundle or candidate.bundle
    return ReviewedFreshEvidence(
        bundle_id=selected.bundle_id,
        logical_tree_sha256=selected.content.resolved_logical_tree_sha256,
        capability_snapshot_sha256=contract_sha256(candidate.capability),
        pricing_snapshot_sha256=contract_sha256(candidate.pricing),
        reviewed_at=selected.content.created_at,
        valid_until=selected.content.valid_until,
        profile=FRESH_CANARY_PROFILE,
    )


def _write_candidate(
    root: Path,
    candidate: Candidate,
    *,
    bundle: EvidenceBundle | None = None,
) -> tuple[Path, Path]:
    selected = bundle or candidate.bundle
    object_root = root / "objects"
    for member in selected.content.members:
        data = candidate.data_by_path[member.logical_path]
        target = object_root / member.object_sha256[:2] / member.object_sha256
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest = root / "bundles" / f"{selected.bundle_id}.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(selected.model_dump_json(indent=2), encoding="utf-8")
    return manifest, object_root


def _write_freeze_inputs(root: Path, candidate: Candidate) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "capability_snapshot_path": root / "capability-snapshot.json",
        "capability_evidence_path": root / "capability.pdf",
        "pricing_snapshot_path": root / "pricing-snapshot.json",
        "pricing_evidence_path": root / "pricing.pdf",
    }
    paths["capability_snapshot_path"].write_bytes(candidate.data_by_path[CAPABILITY_SNAPSHOT_PATH])
    paths["capability_evidence_path"].write_bytes(CAPABILITY_PDF)
    paths["pricing_snapshot_path"].write_bytes(candidate.data_by_path[PRICING_SNAPSHOT_PATH])
    paths["pricing_evidence_path"].write_bytes(PRICING_PDF)
    return paths


def _assemble_bundle(
    candidate: Candidate,
    *,
    objects: tuple[EvidenceObject, ...] | None = None,
    members: tuple[EvidenceMember, ...] | None = None,
    captures: tuple[EvidenceCapture, ...] | None = None,
    predecessor_bundle_id: str | None = None,
) -> EvidenceBundle:
    selected_objects = tuple(
        sorted(objects or candidate.bundle.content.objects, key=lambda x: x.sha256)
    )
    selected_members = tuple(
        sorted(members or candidate.bundle.content.members, key=lambda x: x.logical_path)
    )
    selected_captures = tuple(
        sorted(captures or candidate.bundle.content.captures, key=lambda x: x.capture_id)
    )
    content = EvidenceBundleContent(
        created_at=candidate.bundle.content.created_at,
        valid_until=min(capture.valid_until for capture in selected_captures),
        predecessor_bundle_id=predecessor_bundle_id,
        objects=selected_objects,
        members=selected_members,
        captures=selected_captures,
        resolved_logical_tree_sha256=evidence_logical_tree_sha256(
            selected_objects, selected_members
        ),
    )
    return EvidenceBundle(
        bundle_id=evidence_bundle_content_sha256(content),
        content=content,
    )


def _exact_profile_mutation(kind: str) -> Candidate:
    candidate = _candidate()
    objects = candidate.bundle.content.objects
    members = candidate.bundle.content.members
    captures = candidate.bundle.content.captures
    data_by_path = dict(candidate.data_by_path)

    if kind == "extra":
        extra_path = "evidence/supplement.pdf"
        extra_data = b"%PDF-1.7\nunreviewed supplement\n%%EOF\n"
        extra_object = EvidenceObject(
            sha256=hashlib.sha256(extra_data).hexdigest(),
            size_bytes=len(extra_data),
            media_type="application/pdf",
        )
        extra_member = EvidenceMember(
            logical_path=extra_path,
            role="capability.supplement",
            object_sha256=extra_object.sha256,
        )
        capability_capture = EvidenceCapture.model_validate(
            {
                **captures[0].model_dump(mode="python"),
                "member_paths": tuple(sorted((*captures[0].member_paths, extra_path))),
            }
        )
        bundle = _assemble_bundle(
            candidate,
            objects=(*objects, extra_object),
            members=(*members, extra_member),
            captures=(capability_capture, captures[1]),
        )
        data_by_path[extra_path] = extra_data
    elif kind == "non-fresh":
        inherited_capture = EvidenceCapture.model_validate(
            {
                **captures[0].model_dump(mode="python"),
                "acquisition": EvidenceAcquisition.INHERITED,
                "origin_anchor_sha256": "a" * 64,
                "origin_valid_until": captures[0].valid_until,
            }
        )
        bundle = _assemble_bundle(
            candidate,
            captures=(inherited_capture, captures[1]),
        )
    elif kind == "wrong-mime":
        evidence_digest = next(
            member.object_sha256
            for member in members
            if member.logical_path == CAPABILITY_EVIDENCE_PATH
        )
        changed_objects = tuple(
            EvidenceObject.model_validate(
                {**item.model_dump(mode="python"), "media_type": "image/png"}
            )
            if item.sha256 == evidence_digest
            else item
            for item in objects
        )
        bundle = _assemble_bundle(candidate, objects=changed_objects)
    elif kind == "schema":
        changed_members = tuple(
            EvidenceMember.model_validate(
                {
                    **member.model_dump(mode="python"),
                    "content_schema_version": "2.0.0",
                }
            )
            if member.logical_path == CAPABILITY_SNAPSHOT_PATH
            else member
            for member in members
        )
        bundle = _assemble_bundle(candidate, members=changed_members)
    elif kind == "predecessor":
        bundle = _assemble_bundle(candidate, predecessor_bundle_id="b" * 64)
    else:  # pragma: no cover - test helper guard
        raise AssertionError(f"unknown mutation: {kind}")
    return Candidate(
        bundle=bundle,
        data_by_path=data_by_path,
        capability=candidate.capability,
        pricing=candidate.pricing,
    )


def test_fixed_profile_build_is_deterministic_and_exactly_four_member_fresh() -> None:
    first = _candidate()
    second = _candidate()

    assert first.bundle == second.bundle
    assert first.data_by_path == second.data_by_path
    assert first.bundle.content.predecessor_bundle_id is None
    assert len(first.bundle.content.objects) == 4
    assert len({item.sha256 for item in first.bundle.content.objects}) == 4
    assert [member.logical_path for member in first.bundle.content.members] == [
        CAPABILITY_EVIDENCE_PATH,
        PRICING_EVIDENCE_PATH,
        CAPABILITY_SNAPSHOT_PATH,
        PRICING_SNAPSHOT_PATH,
    ]
    assert {member.role for member in first.bundle.content.members} == {
        "capability.evidence",
        "capability.snapshot",
        "pricing.evidence",
        "pricing.snapshot",
    }
    assert {capture.acquisition for capture in first.bundle.content.captures} == {
        EvidenceAcquisition.FRESH
    }
    assert first.bundle.content.valid_until == VALID_UNTIL


def test_equivalent_timezone_spelling_produces_the_same_canonical_bundle() -> None:
    offset = timezone(timedelta(hours=8))
    capability = _capability().model_copy(
        update={
            "source_updated_at": _capability().source_updated_at.astimezone(offset),
            "captured_at": _capability().captured_at.astimezone(offset),
            "valid_until": _capability().valid_until.astimezone(offset),
        }
    )
    pricing = _pricing().model_copy(
        update={
            "source_updated_at": _pricing().source_updated_at.astimezone(offset),
            "captured_at": _pricing().captured_at.astimezone(offset),
            "valid_until": _pricing().valid_until.astimezone(offset),
        }
    )

    assert (
        _candidate(capability=capability, pricing=pricing).bundle.bundle_id
        == _candidate().bundle.bundle_id
    )


def test_freeze_is_append_only_reuses_identical_files_and_refuses_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate()
    inputs = _write_freeze_inputs(tmp_path, candidate)
    output = tmp_path / "fresh-store"
    monkeypatch.setattr(fresh_evidence, "datetime", FrozenDateTime)

    first = freeze_fresh_canary_evidence(output_root=output, **inputs)
    before = {
        path.relative_to(output): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in output.rglob("*")
        if path.is_file()
    }
    second = freeze_fresh_canary_evidence(output_root=output, **inputs)
    after = {
        path.relative_to(output): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in output.rglob("*")
        if path.is_file()
    }

    assert first.bundle.bundle_id == candidate.bundle.bundle_id == second.bundle.bundle_id
    assert before == after
    assert len(before) == 5

    capability_member = next(
        member
        for member in first.bundle.content.members
        if member.logical_path == CAPABILITY_EVIDENCE_PATH
    )
    object_path = (
        first.object_root / capability_member.object_sha256[:2] / capability_member.object_sha256
    )
    object_path.write_bytes(b"X" * len(CAPABILITY_PDF))
    with pytest.raises(FreshEvidenceError, match="existing CAS path"):
        freeze_fresh_canary_evidence(output_root=output, **inputs)


def test_reviewed_registry_anchor_allows_verified_current_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate()
    manifest, object_root = _write_candidate(tmp_path, candidate)
    anchor = _anchor(candidate)
    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", (anchor,))

    loaded = load_trusted_fresh_canary_evidence(
        manifest_path=manifest,
        object_root=object_root,
        expected_bundle_id=candidate.bundle.bundle_id,
        at=PLANNED_AT,
    )

    assert loaded.bundle_id == candidate.bundle.bundle_id
    assert loaded.logical_tree_sha256 == anchor.logical_tree_sha256
    assert loaded.capability == candidate.capability
    assert loaded.pricing == candidate.pricing
    assert loaded.reviewed_anchor == anchor


def test_legacy_denylist_matches_the_materializer_catalog() -> None:
    assert LEGACY_EVIDENCE_BUNDLE_IDS == frozenset(
        item.expected_bundle_id for item in REVIEWED_ARCHIVE_CATALOG
    )
    assert tuple(item.round for item in REVIEWED_ARCHIVE_CATALOG) == (
        "V02-R2",
        "V02-R3",
        "V02-R4",
        "V02-R5",
        "V02-R6",
    )


@pytest.mark.parametrize("bundle_id", sorted(LEGACY_EVIDENCE_BUNDLE_IDS))
def test_every_legacy_id_is_rejected_before_manifest_read(
    bundle_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_manifest_read(*_: object, **__: object) -> None:
        raise AssertionError("manifest must not be read for an untrusted ID")

    monkeypatch.setattr(
        EvidenceBundleReader,
        "from_manifest",
        classmethod(forbidden_manifest_read),
    )
    with pytest.raises(FreshEvidenceError, match="legacy R2-R6"):
        load_trusted_fresh_canary_evidence(
            manifest_path=tmp_path / "must-not-be-read.json",
            object_root=tmp_path / "must-not-be-read",
            expected_bundle_id=bundle_id,
            at=PLANNED_AT,
        )


def test_unknown_id_is_rejected_before_manifest_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_manifest_read(*_: object, **__: object) -> None:
        raise AssertionError("manifest must not be read for an untrusted ID")

    monkeypatch.setattr(
        EvidenceBundleReader,
        "from_manifest",
        classmethod(forbidden_manifest_read),
    )
    with pytest.raises(FreshEvidenceError, match="not in the Git-reviewed"):
        load_trusted_fresh_canary_evidence(
            manifest_path=tmp_path / "must-not-be-read.json",
            object_root=tmp_path / "must-not-be-read",
            expected_bundle_id="f" * 64,
            at=PLANNED_AT,
        )


def test_verified_loader_rejects_cas_and_manifest_digest_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate()
    manifest, object_root = _write_candidate(tmp_path, candidate)
    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", (_anchor(candidate),))

    first = candidate.bundle.content.objects[0]
    object_path = object_root / first.sha256[:2] / first.sha256
    original = object_path.read_bytes()
    object_path.write_bytes(b"X" * len(original))
    with pytest.raises(EvidenceBundleError, match="digest"):
        load_trusted_fresh_canary_evidence(
            manifest_path=manifest,
            object_root=object_root,
            expected_bundle_id=candidate.bundle.bundle_id,
            at=PLANNED_AT,
        )

    object_path.write_bytes(original)
    payload = candidate.bundle.model_dump(mode="json")
    payload["bundle_id"] = "0" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceBundleError, match="manifest|bundle_id"):
        load_trusted_fresh_canary_evidence(
            manifest_path=manifest,
            object_root=object_root,
            expected_bundle_id=candidate.bundle.bundle_id,
            at=PLANNED_AT,
        )


def test_duplicate_json_is_rejected_in_snapshot_and_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate()
    duplicated_snapshot = candidate.data_by_path[CAPABILITY_SNAPSHOT_PATH].replace(
        b'"status":"CURRENT"',
        b'"status":"CURRENT","status":"CURRENT"',
        1,
    )
    with pytest.raises(FreshEvidenceError, match="duplicate JSON key"):
        build_fresh_canary_evidence_bundle(
            capability_snapshot_bytes=duplicated_snapshot,
            capability_evidence_bytes=CAPABILITY_PDF,
            pricing_snapshot_bytes=candidate.data_by_path[PRICING_SNAPSHOT_PATH],
            pricing_evidence_bytes=PRICING_PDF,
        )

    manifest, object_root = _write_candidate(tmp_path, candidate)
    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", (_anchor(candidate),))
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            '"schema_version": "1.0.0",',
            '"schema_version": "1.0.0",\n  "schema_version": "1.0.0",',
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(EvidenceBundleError, match="duplicate JSON key"):
        load_trusted_fresh_canary_evidence(
            manifest_path=manifest,
            object_root=object_root,
            expected_bundle_id=candidate.bundle.bundle_id,
            at=PLANNED_AT,
        )


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        ("invalid-utf8", "invalid snapshot JSON"),
        ("nan", "non-finite JSON number"),
        ("oversize", "byte limit"),
    ],
)
def test_snapshot_parser_rejects_invalid_utf8_nan_and_oversize(
    kind: str, message: str
) -> None:
    candidate = _candidate()
    invalid = {
        "invalid-utf8": b"\xff",
        "nan": b'{"fps":NaN}',
        "oversize": b" " * (256 * 1024 + 1),
    }[kind]

    with pytest.raises(FreshEvidenceError, match=message):
        build_fresh_canary_evidence_bundle(
            capability_snapshot_bytes=invalid,
            capability_evidence_bytes=CAPABILITY_PDF,
            pricing_snapshot_bytes=candidate.data_by_path[PRICING_SNAPSHOT_PATH],
            pricing_evidence_bytes=PRICING_PDF,
        )


def test_snapshot_evidence_digest_and_profile_drift_fail_at_admission() -> None:
    bad_digest = _capability(evidence_sha256="0" * 64)
    with pytest.raises(FreshEvidenceError, match="does not bind"):
        _candidate(capability=bad_digest)

    bad_profile = _capability(model="unreviewed-model")
    with pytest.raises(FreshEvidenceError, match="pinned Ark Canary profile"):
        _candidate(capability=bad_profile)


def test_loader_rejects_capture_provenance_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate()
    changed_capture = candidate.bundle.content.captures[0].model_copy(
        update={"source_url": "https://docs.volcengine.com/docs/82379/999999"}
    )
    changed_bundle = build_evidence_bundle(
        created_at=candidate.bundle.content.created_at,
        objects=candidate.bundle.content.objects,
        members=candidate.bundle.content.members,
        captures=(changed_capture, candidate.bundle.content.captures[1]),
    )
    manifest, object_root = _write_candidate(tmp_path, candidate, bundle=changed_bundle)
    monkeypatch.setattr(
        fresh_evidence,
        "REVIEWED_FRESH_EVIDENCE",
        (_anchor(candidate, bundle=changed_bundle),),
    )

    with pytest.raises(FreshEvidenceError, match="provenance"):
        load_trusted_fresh_canary_evidence(
            manifest_path=manifest,
            object_root=object_root,
            expected_bundle_id=changed_bundle.bundle_id,
            at=PLANNED_AT,
        )


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        ("extra", "exact Canary profile"),
        ("non-fresh", "inherited evidence origin"),
        ("wrong-mime", "exact Canary profile"),
        ("schema", "exact Canary profile"),
        ("predecessor", "must not inherit a predecessor"),
    ],
)
def test_loader_rejects_every_exact_profile_mutation(
    kind: str,
    message: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _exact_profile_mutation(kind)
    manifest, object_root = _write_candidate(tmp_path, candidate)
    monkeypatch.setattr(
        fresh_evidence,
        "REVIEWED_FRESH_EVIDENCE",
        (_anchor(candidate),),
    )

    with pytest.raises(EvidenceBundleError, match=message):
        load_trusted_fresh_canary_evidence(
            manifest_path=manifest,
            object_root=object_root,
            expected_bundle_id=candidate.bundle.bundle_id,
            at=PLANNED_AT,
        )


def test_expired_reviewed_bundle_is_rejected_before_disk_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate()
    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", (_anchor(candidate),))

    with pytest.raises(FreshEvidenceError, match="anchor has expired"):
        load_trusted_fresh_canary_evidence(
            manifest_path=tmp_path / "does-not-need-to-exist.json",
            object_root=tmp_path / "does-not-need-to-exist",
            expected_bundle_id=candidate.bundle.bundle_id,
            at=VALID_UNTIL + timedelta(microseconds=1),
        )


def test_registry_rejects_wrong_profile_and_duplicate_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate()
    wrong_profile = replace(_anchor(candidate), profile="unreviewed-profile")
    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", (wrong_profile,))
    with pytest.raises(FreshEvidenceError, match="approved Canary profile"):
        fresh_evidence.require_trusted_fresh_evidence_anchor(
            candidate.bundle.bundle_id, at=PLANNED_AT
        )


def test_loader_rejects_registry_tree_or_contract_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate()
    manifest, object_root = _write_candidate(tmp_path, candidate)
    anchor = _anchor(candidate)

    for bad_anchor in (
        replace(anchor, logical_tree_sha256="0" * 64),
        replace(anchor, capability_snapshot_sha256="0" * 64),
        replace(anchor, pricing_snapshot_sha256="0" * 64),
    ):
        monkeypatch.setattr(
            fresh_evidence,
            "REVIEWED_FRESH_EVIDENCE",
            (bad_anchor,),
        )
        with pytest.raises(FreshEvidenceError, match="Git-reviewed anchor"):
            load_trusted_fresh_canary_evidence(
                manifest_path=manifest,
                object_root=object_root,
                expected_bundle_id=candidate.bundle.bundle_id,
                at=PLANNED_AT,
            )


def test_freezer_rejects_legacy_sources_and_protected_outputs_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate()
    monkeypatch.setattr(fresh_evidence, "datetime", FrozenDateTime)
    legacy_inputs = _write_freeze_inputs(tmp_path / "canary", candidate)
    output = tmp_path / "fresh-output"
    with pytest.raises(FreshEvidenceError, match="cannot be relabeled"):
        freeze_fresh_canary_evidence(output_root=output, **legacy_inputs)
    assert not output.exists()

    clean_inputs = _write_freeze_inputs(tmp_path / "clean", candidate)
    protected_output = tmp_path / "evidence-cas" / "fresh"
    with pytest.raises(FreshEvidenceError, match="separate from Canary archives"):
        freeze_fresh_canary_evidence(
            output_root=protected_output,
            **clean_inputs,
        )
    assert not protected_output.exists()

    anchor = _anchor(candidate)
    monkeypatch.setattr(fresh_evidence, "REVIEWED_FRESH_EVIDENCE", (anchor, anchor))
    with pytest.raises(FreshEvidenceError, match="duplicate bundle ID"):
        fresh_evidence.require_trusted_fresh_evidence_anchor(
            candidate.bundle.bundle_id, at=PLANNED_AT
        )


@pytest.mark.parametrize("windows_alias", ["canary.", "canary "])
def test_freezer_rejects_win32_trailing_dot_or_space_archive_alias(
    windows_alias: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate()
    clean_inputs = _write_freeze_inputs(tmp_path / "clean-inputs", candidate)
    output = tmp_path / windows_alias / "fresh"
    monkeypatch.setattr(fresh_evidence, "datetime", FrozenDateTime)

    with pytest.raises(FreshEvidenceError, match="trailing dots or spaces"):
        freeze_fresh_canary_evidence(output_root=output, **clean_inputs)
    assert not output.exists()
