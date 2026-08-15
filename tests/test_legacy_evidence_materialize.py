from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
import test_legacy_evidence as legacy_fixtures

import sdc.legacy_evidence as legacy_evidence
import sdc.legacy_evidence_materialize as materialize
from sdc.contracts import EvidenceAcquisition
from sdc.evidence import (
    EvidenceBundleExpiredError,
    EvidenceBundleReader,
    EvidenceBundleUnverifiedOriginError,
)
from sdc.legacy_evidence import (
    LegacySuccessorAnchor,
    LegacyVerificationLevel,
    verify_legacy_round,
)
from sdc.legacy_evidence_materialize import (
    REVIEWED_ARCHIVE_CATALOG,
    CanonicalMaterializationError,
    ReviewedLegacyRound,
    main,
    materialize_canonical_store,
    verify_canonical_store,
    verify_reviewed_archives,
)

_EXPECTED_REVIEWED_CATALOG = (
    (
        "V02-R2",
        "v02-r2",
        "v02-r2-index.json",
        "ef63adc9c040dc543ce593b70b9729c6b29cd9ff4af947856365756f281c743f",
        "9c4489c40d78a105bc49ec106f9ea13d7551a9694d2ee33f1642bbfe68761d90",
        "f3fb761f6091201aa726a7c81333cf74a2f3ef83c88cf78745df2cddf041fbde",
        "e878442d46ade842dd766c14e91af63f15e0ee973a105441030b5bfb7e9b4692",
        29,
        "CHAIN_COMPAT",
        "2d33b747367d396f245ddf15187628cbc96936a39ad8cb948282ec87c4c65a8e",
        22,
        22,
    ),
    (
        "V02-R3",
        "v02-r3",
        "v02-r3-index.json",
        "9fee187499617e880fbb0d07191ee315efa6ec3a095b06c5aadb7293b0538591",
        "104cc4c56d7f6c539232f0e253fe6b4bcd0ddb3354e0a77f16aa3add8ceba6cb",
        "72afb1ccb1f06ab9abf39c1e2550d17373cf75762f6536ac570ef57d5b51a3b3",
        "f6b9172f6d4e9f80c0eb485d42b75602ba856dc15edb4dc2233d41ce3fc5bd68",
        28,
        "CHAIN_COMPAT",
        "07791b67f57c94bc5e5860b74f770317a1b59bd4ea21bfbac9f01613ac11e906",
        22,
        3,
    ),
    (
        "V02-R4",
        "v02-r4",
        "v02-r4-index.json",
        "51beb34e5111bc864018a0a5ac37fadf50d86aea7c9944c85b3902c6541bf550",
        "44a97e5d58be29a28ff3db60ee9d0606e1cd73889c65440fcbb8a8195bfe7ef6",
        "753ff192e24cbd6001015f7a80c23b78e7672f0e323877a8b9fdde5a0b715d8b",
        "5f00168d4de2377d1cc12012e7a5a1f30be52369633f43f92c22671a28bf3e8d",
        37,
        "FULL_DESCRIPTOR_TREE",
        "5d3b087154adfe423f7b14190d67a54b35ce3e84eae87dd99ffd6bb8312937ec",
        29,
        10,
    ),
    (
        "V02-R5",
        "v02-r5",
        "v02-r5-index.json",
        "dfa9ef2af0049e505e25e44da0d090e80ed49be7df478fe95ef40a41f726624e",
        "061e7ced7cf5fc2798d1c1281a2659bfed5c0eb62c1f018018fcec68a2c818eb",
        "eb9cc499cc6db71759bfe8a20a075eb02c276b3e2275ff84e46364376b0230ab",
        "d5d4797fd668f8391fbf8a35dff6ec858334358ea47898194e52d17d4d898aa9",
        39,
        "FULL_DESCRIPTOR_TREE",
        "8ca336193cd5cd7a5cf0f766f6ae7b482de8def97e63df0b6cca0f95fc278f5b",
        29,
        5,
    ),
    (
        "V02-R6",
        "v02-r6",
        "v02-r6-index.json",
        "cf03a19ba671d89e1504b4c88b5bae1dd33a559eea48965d6ce6af0f47b850c5",
        "c7c9dae6d2799eaf472f10821f33869af68e3903eb0e94c4812ecc4bdec8af5b",
        "df81e7ff5db0e6ca2662bffcc4bec79bbe1b584c0564121603ea5485cd3a653c",
        "2415399d0fb1458d7d9105ce47b96ac5d6162f37af97270653e99599fcc0cb3f",
        37,
        "FULL_DESCRIPTOR_TREE",
        "f91f9aadf10ce0fbfe7a58df9c7c3fbd2f07d1b751b4346d44e19e2026be39d7",
        27,
        27,
    ),
)


@dataclass(frozen=True, slots=True)
class SyntheticReviewedArchives:
    canary_root: Path
    archives: tuple[legacy_fixtures.SyntheticLegacyArchive, ...]
    catalog: tuple[ReviewedLegacyRound, ...]
    excluded_paths: frozenset[Path]
    live_root: Path


def _reviewed_catalog_values(
    catalog: tuple[ReviewedLegacyRound, ...],
) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            item.round,
            item.directory,
            item.index,
            item.expected_index_sha256,
            item.expected_manifest_sha256,
            item.expected_report_sha256,
            item.expected_tree_sha256,
            item.expected_file_count,
            item.expected_level.value,
            item.expected_bundle_id,
            item.expected_member_count,
            item.expected_new_objects,
        )
        for item in catalog
    )


def _normalized_media_label(label: str) -> str:
    """Share reviewed R2-R5 bytes while keeping the recaptured R6 media distinct."""
    if ":" in label:
        return label.split(":", 1)[1]
    return f"V02-R6:{label}"


@pytest.fixture(scope="module")
def synthetic_reviewed_archives(
    tmp_path_factory: pytest.TempPathFactory,
) -> SyntheticReviewedArchives:
    canary_root = tmp_path_factory.mktemp("canonical-materialization") / "canary"
    builder_patch = pytest.MonkeyPatch()
    original_pdf = legacy_fixtures._pdf_bytes
    original_png = legacy_fixtures._png_bytes
    original_jpeg = legacy_fixtures._jpeg_bytes
    builder_patch.setattr(
        legacy_fixtures,
        "_pdf_bytes",
        lambda label: original_pdf(_normalized_media_label(label)),
    )
    builder_patch.setattr(
        legacy_fixtures,
        "_png_bytes",
        lambda label: original_png(_normalized_media_label(label)),
    )
    builder_patch.setattr(
        legacy_fixtures,
        "_jpeg_bytes",
        lambda label: original_jpeg(_normalized_media_label(label)),
    )
    try:
        r2 = legacy_fixtures._build_pre_r6_archive(canary_root, "V02-R2")
        r3 = legacy_fixtures._build_pre_r6_archive(
            canary_root,
            "V02-R3",
            predecessor=r2,
        )
        r4 = legacy_fixtures._build_pre_r6_archive(canary_root, "V02-R4")
        r5 = legacy_fixtures._build_pre_r6_archive(canary_root, "V02-R5")
        r6 = legacy_fixtures._build_r6_archive(canary_root)
    finally:
        builder_patch.undo()

    live_root = canary_root / "v02-r6-live"
    live_root.mkdir()
    (live_root / "must-not-be-touched.bin").write_bytes(b"synthetic live boundary sentinel")

    archives = (r2, r3, r4, r5, r6)
    successor = LegacySuccessorAnchor(
        source_root=r3.root,
        index_path=r3.index,
        expected_index_sha256=r3.index_sha256,
    )
    compatibility_patch = pytest.MonkeyPatch()
    compatibility_patch.setattr(
        legacy_evidence,
        "_R3_CANONICAL_INDEX_SHA256",
        r3.index_sha256,
    )
    try:
        reports = tuple(
            verify_legacy_round(
                archive.root,
                archive.index,
                expected_index_sha256=archive.index_sha256,
                successor_anchor=successor if archive is r2 else None,
            )
            for archive in archives
        )
        plans = tuple(legacy_evidence._build_import_plan(report) for report in reports)
    finally:
        compatibility_patch.undo()

    seen_objects: set[str] = set()
    new_object_counts: list[int] = []
    for plan in plans:
        current = {item.sha256 for item in plan.bundle.content.objects}
        new_object_counts.append(len(current - seen_objects))
        seen_objects.update(current)
    assert tuple(new_object_counts) == (22, 3, 10, 5, 27)
    assert len(seen_objects) == 67

    catalog = tuple(
        ReviewedLegacyRound(
            round=archive.round_name,
            directory=archive.root.name,
            index=archive.index.name,
            expected_index_sha256=archive.index_sha256,
            expected_manifest_sha256=archive.manifest_sha256,
            expected_report_sha256=archive.report_sha256,
            expected_tree_sha256=archive.tree_sha256,
            expected_file_count=archive.file_count,
            expected_level=report.level,
            expected_bundle_id=plan.bundle.bundle_id,
            expected_member_count=len(plan.bundle.content.members),
            expected_new_objects=new_objects,
        )
        for archive, report, plan, new_objects in zip(
            archives,
            reports,
            plans,
            new_object_counts,
            strict=True,
        )
    )

    excluded_paths: set[Path] = set()
    for archive in archives[:-1]:
        declared = legacy_fixtures._pre_r6_declared_paths(archive.round_name)
        admitted = legacy_fixtures._pre_r6_media_paths(
            archive.round_name
        ) | legacy_fixtures._pre_r6_json_paths(archive.round_name)
        excluded_paths.update(archive.root / Path(path) for path in declared - admitted)
    excluded_paths.update(r6.root / Path(path) for path in legacy_fixtures._R6_EXCLUDED_PATHS)
    return SyntheticReviewedArchives(
        canary_root=canary_root,
        archives=archives,
        catalog=catalog,
        excluded_paths=frozenset(path.absolute() for path in excluded_paths),
        live_root=live_root,
    )


@pytest.fixture
def reviewed_synthetic_catalog(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_reviewed_archives: SyntheticReviewedArchives,
) -> SyntheticReviewedArchives:
    monkeypatch.setattr(
        materialize,
        "REVIEWED_ARCHIVE_CATALOG",
        synthetic_reviewed_archives.catalog,
    )
    monkeypatch.setattr(
        legacy_evidence,
        "_R3_CANONICAL_INDEX_SHA256",
        synthetic_reviewed_archives.catalog[1].expected_index_sha256,
    )
    return synthetic_reviewed_archives


def _store_snapshot(root: Path) -> tuple[tuple[str, int, int, str], ...]:
    rows: list[tuple[str, int, int, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        value = path.lstat()
        if stat.S_ISREG(value.st_mode):
            rows.append(
                (
                    path.relative_to(root).as_posix(),
                    value.st_size,
                    value.st_mtime_ns,
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            )
    return tuple(rows)


def _reviewed_source_metadata(
    fixtures: SyntheticReviewedArchives,
) -> tuple[tuple[str, int, int, int], ...]:
    rows: list[tuple[str, int, int, int]] = []
    for archive in fixtures.archives:
        paths = (archive.index, *archive.root.rglob("*"))
        for path in paths:
            value = path.lstat()
            rows.append(
                (
                    path.relative_to(fixtures.canary_root).as_posix(),
                    value.st_mode,
                    value.st_size,
                    value.st_mtime_ns,
                )
            )
    return tuple(sorted(rows))


def _is_below(path: Path, root: Path) -> bool:
    absolute = path.absolute()
    absolute_root = root.absolute()
    return absolute == absolute_root or absolute_root in absolute.parents


def _replace_reviewed_field(
    item: ReviewedLegacyRound,
    field: str,
    value: object,
) -> ReviewedLegacyRound:
    """Keep parametrized drift cases dynamic without weakening production types."""
    dynamic_replace = cast(Any, replace)
    return cast(ReviewedLegacyRound, dynamic_replace(item, **{field: value}))


def test_reviewed_archive_catalog_is_the_exact_fixed_canonical_catalog() -> None:
    assert _reviewed_catalog_values(REVIEWED_ARCHIVE_CATALOG) == _EXPECTED_REVIEWED_CATALOG


def test_default_verification_and_cli_are_read_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    source_before = _reviewed_source_metadata(reviewed_synthetic_catalog)
    output_root = tmp_path / "canonical-store"

    reports = verify_reviewed_archives(reviewed_synthetic_catalog.canary_root)
    assert tuple(report.round for report in reports) == (
        "V02-R2",
        "V02-R3",
        "V02-R4",
        "V02-R5",
        "V02-R6",
    )
    assert not output_root.exists()

    assert (
        main(
            [
                "--canary-root",
                str(reviewed_synthetic_catalog.canary_root),
                "--output-root",
                str(output_root),
            ]
        )
        == 0
    )
    assert not output_root.exists()
    assert _reviewed_source_metadata(reviewed_synthetic_catalog) == source_before
    assert capsys.readouterr().out


def test_apply_publishes_exact_closure_and_repeat_only_verifies(
    tmp_path: Path,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    output_root = tmp_path / "canonical-store"
    expected_bundle_ids = tuple(
        (item.round, item.expected_bundle_id) for item in reviewed_synthetic_catalog.catalog
    )

    first = materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)

    assert first.output_root == output_root
    assert first.created is True
    assert first.object_count == 67
    assert first.round_bundle_ids == expected_bundle_ids
    assert {path.name for path in (output_root / "bundles").iterdir()} == {
        "v02-r2.json",
        "v02-r3.json",
        "v02-r4.json",
        "v02-r5.json",
        "v02-r6.json",
    }
    object_paths = tuple((output_root / "objects").glob("*/*"))
    assert len(object_paths) == 67
    assert all(
        path.is_file()
        and len(path.name) == 64
        and path.name == path.name.lower()
        and path.parent.name == path.name[:2]
        for path in object_paths
    )
    assert len([path for path in output_root.rglob("*") if path.is_file()]) == 73
    catalog_bytes = (output_root / "catalog.json").read_bytes()
    assert hashlib.sha256(catalog_bytes).hexdigest() == first.catalog_sha256
    assert isinstance(json.loads(catalog_bytes), dict)

    verified = verify_canonical_store(output_root)
    assert verified.created is False
    assert verified.catalog_sha256 == first.catalog_sha256
    assert verified.object_count == first.object_count
    assert verified.round_bundle_ids == first.round_bundle_ids

    before_repeat = _store_snapshot(output_root)
    repeated = materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)
    assert repeated.created is False
    assert repeated.catalog_sha256 == first.catalog_sha256
    assert repeated.object_count == 67
    assert repeated.round_bundle_ids == first.round_bundle_ids
    assert _store_snapshot(output_root) == before_repeat


@pytest.mark.parametrize("catalog_position", range(5))
@pytest.mark.parametrize(
    ("field", "bad_value"),
    (
        ("expected_index_sha256", "0" * 64),
        ("expected_bundle_id", "f" * 64),
    ),
)
def test_any_round_anchor_or_bundle_drift_never_publishes_final_catalog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
    catalog_position: int,
    field: str,
    bad_value: object,
) -> None:
    changed = list(reviewed_synthetic_catalog.catalog)
    changed[catalog_position] = _replace_reviewed_field(changed[catalog_position], field, bad_value)
    monkeypatch.setattr(materialize, "REVIEWED_ARCHIVE_CATALOG", tuple(changed))
    output_root = tmp_path / f"drift-{catalog_position}-{field}"

    with pytest.raises(CanonicalMaterializationError):
        materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)

    assert not output_root.exists()


@pytest.mark.parametrize(
    ("field", "bad_value"),
    (
        ("expected_manifest_sha256", "0" * 64),
        ("expected_report_sha256", "0" * 64),
        ("expected_tree_sha256", "0" * 64),
        ("expected_file_count", 999),
        ("expected_level", LegacyVerificationLevel.DEGRADED),
        ("expected_member_count", 999),
        ("expected_new_objects", 999),
    ),
)
def test_secondary_catalog_drift_never_publishes_final_catalog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
    field: str,
    bad_value: object,
) -> None:
    changed = list(reviewed_synthetic_catalog.catalog)
    changed[2] = _replace_reviewed_field(changed[2], field, bad_value)
    monkeypatch.setattr(materialize, "REVIEWED_ARCHIVE_CATALOG", tuple(changed))
    output_root = tmp_path / f"secondary-drift-{field}"

    with pytest.raises(CanonicalMaterializationError):
        materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)

    assert not output_root.exists()


def test_r2_is_importable_only_through_the_reviewed_r3_successor(
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    r2 = reviewed_synthetic_catalog.archives[0]
    standalone = verify_legacy_round(
        r2.root,
        r2.index,
        expected_index_sha256=r2.index_sha256,
    )
    reports = verify_reviewed_archives(reviewed_synthetic_catalog.canary_root)

    assert standalone.level is LegacyVerificationLevel.DEGRADED
    assert reports[0].level is LegacyVerificationLevel.CHAIN_COMPAT
    assert reports[0].successor_anchor == LegacySuccessorAnchor(
        source_root=reviewed_synthetic_catalog.archives[1].root,
        index_path=reviewed_synthetic_catalog.archives[1].index,
        expected_index_sha256=reviewed_synthetic_catalog.catalog[1].expected_index_sha256,
    )


@pytest.mark.parametrize("overlap", ("same", "inside", "ancestor"))
def test_overlapping_destination_is_rejected_without_source_mutation(
    monkeypatch: pytest.MonkeyPatch,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
    overlap: str,
) -> None:
    source_before = _reviewed_source_metadata(reviewed_synthetic_catalog)
    destinations = {
        "same": reviewed_synthetic_catalog.canary_root,
        "inside": reviewed_synthetic_catalog.canary_root / "canonical-store",
        "ancestor": reviewed_synthetic_catalog.canary_root.parent,
    }

    with pytest.raises(CanonicalMaterializationError):
        materialize_canonical_store(
            reviewed_synthetic_catalog.canary_root,
            destinations[overlap],
        )

    assert _reviewed_source_metadata(reviewed_synthetic_catalog) == source_before
    assert not (reviewed_synthetic_catalog.canary_root / "canonical-store").exists()


def test_existing_invalid_store_is_never_repaired(
    tmp_path: Path,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    output_root = tmp_path / "existing-invalid"
    output_root.mkdir()
    marker = output_root / "operator-owned.txt"
    marker.write_bytes(b"do not repair or replace")
    before = _store_snapshot(output_root)

    with pytest.raises(CanonicalMaterializationError):
        materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)

    assert _store_snapshot(output_root) == before


def test_existing_corrupt_store_is_rejected_without_repair(
    tmp_path: Path,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    output_root = tmp_path / "existing-corrupt"
    materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)
    object_path = next((output_root / "objects").glob("*/*"))
    object_path.write_bytes(b"corrupt-existing-object")
    before = _store_snapshot(output_root)

    with pytest.raises(CanonicalMaterializationError):
        materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)

    assert _store_snapshot(output_root) == before


def test_materialized_legacy_captures_can_never_be_current(
    tmp_path: Path,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    output_root = tmp_path / "historical-only"
    report = materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)

    for round_name, bundle_id in report.round_bundle_ids:
        reader = EvidenceBundleReader.from_manifest(
            output_root / "bundles" / f"{round_name.lower()}.json",
            output_root / "objects",
            expected_bundle_id=bundle_id,
        )
        assert all(
            capture.acquisition is EvidenceAcquisition.LEGACY_IMPORT
            for capture in reader.bundle.content.captures
        )
        with pytest.raises(EvidenceBundleUnverifiedOriginError):
            reader.assert_current(at=datetime.fromisoformat("2026-08-13T18:00:00+08:00"))
        with pytest.raises(EvidenceBundleExpiredError):
            reader.assert_current(at=datetime.fromisoformat("2026-08-14T00:00:00+08:00"))


def test_materialization_never_touches_r6_live_or_opens_excluded_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    original_open = Path.open
    original_lstat_no_link = legacy_evidence._lstat_no_link
    original_scandir = os.scandir
    live_metadata = (reviewed_synthetic_catalog.live_root / "must-not-be-touched.bin").lstat()

    def guarded_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        absolute = path.absolute()
        if absolute in reviewed_synthetic_catalog.excluded_paths or _is_below(
            absolute, reviewed_synthetic_catalog.live_root
        ):
            raise AssertionError(f"forbidden legacy bytes were opened: {path}")
        return original_open(path, *args, **kwargs)

    def guarded_lstat_no_link(path: Path, label: str) -> os.stat_result | None:
        if _is_below(path, reviewed_synthetic_catalog.live_root):
            raise AssertionError(f"R6-live was inspected: {path}")
        return original_lstat_no_link(path, label)

    def guarded_scandir(
        path: int | str | bytes | os.PathLike[str] | os.PathLike[bytes],
    ) -> Any:
        if (
            not isinstance(path, int)
            and Path(os.fsdecode(path)).absolute() == reviewed_synthetic_catalog.canary_root
        ):
            raise AssertionError("the Canary container was broadly enumerated")
        return original_scandir(path)

    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(legacy_evidence, "_lstat_no_link", guarded_lstat_no_link)
    monkeypatch.setattr(os, "scandir", guarded_scandir)

    result = materialize_canonical_store(
        reviewed_synthetic_catalog.canary_root,
        tmp_path / "boundary-store",
    )

    assert result.object_count == 67
    assert (
        reviewed_synthetic_catalog.live_root / "must-not-be-touched.bin"
    ).lstat() == live_metadata


def test_verify_only_recomputes_bundle_identity_before_any_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    changed = list(reviewed_synthetic_catalog.catalog)
    changed[4] = replace(changed[4], expected_bundle_id="f" * 64)
    monkeypatch.setattr(materialize, "REVIEWED_ARCHIVE_CATALOG", tuple(changed))
    output_root = tmp_path / "must-not-exist"

    with pytest.raises(CanonicalMaterializationError, match="bundle identity"):
        verify_reviewed_archives(reviewed_synthetic_catalog.canary_root)

    assert not output_root.exists()


def test_existing_store_under_r6_live_is_rejected_before_target_inspection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    safe_store = tmp_path / "safe-store"
    materialize_canonical_store(reviewed_synthetic_catalog.canary_root, safe_store)
    live_store = reviewed_synthetic_catalog.live_root / "canonical-store"
    safe_store.rename(live_store)
    original_lstat = materialize._lstat_no_link

    def guarded_lstat(path: Path, label: str) -> os.stat_result | None:
        if _is_below(path, reviewed_synthetic_catalog.live_root):
            raise AssertionError(f"R6-live target was inspected: {path}")
        return original_lstat(path, label)

    monkeypatch.setattr(materialize, "_lstat_no_link", guarded_lstat)

    with pytest.raises(CanonicalMaterializationError, match="protected Canary"):
        verify_canonical_store(live_store)
    with pytest.raises(CanonicalMaterializationError, match="protected Canary"):
        materialize_canonical_store(reviewed_synthetic_catalog.canary_root, live_store)
    assert (
        main(
            [
                "--canary-root",
                str(reviewed_synthetic_catalog.canary_root),
                "--output-root",
                str(live_store),
            ]
        )
        == 2
    )


def test_other_canary_archive_path_is_rejected_before_creating_parent(
    tmp_path: Path,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    protected_parent = tmp_path / "other" / "canary" / "v02-r2"
    output_root = protected_parent / "canonical-store"

    with pytest.raises(CanonicalMaterializationError, match="protected Canary"):
        materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)

    assert not protected_parent.exists()


def test_existing_valid_store_with_preserved_lock_remains_human_gate(
    tmp_path: Path,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    output_root = tmp_path / "locked-store"
    materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)
    before = _store_snapshot(output_root)
    lock_path = output_root.parent / f".{output_root.name}.materialize.lock"
    lock_path.write_bytes(b"preserved human gate")

    with pytest.raises(CanonicalMaterializationError, match="lock is present"):
        materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)

    assert _store_snapshot(output_root) == before
    assert lock_path.read_bytes() == b"preserved human gate"


def test_publication_race_never_replaces_an_appearing_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    output_root = tmp_path / "raced-store"
    original_mkdir = Path.mkdir
    marker = b"operator-owned target"

    def raced_mkdir(
        path: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        if path.absolute() == output_root.absolute() and not path.exists():
            original_mkdir(path)
            (path / "marker.bin").write_bytes(marker)
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", raced_mkdir)

    with pytest.raises(CanonicalMaterializationError):
        materialize_canonical_store(reviewed_synthetic_catalog.canary_root, output_root)

    assert (output_root / "marker.bin").read_bytes() == marker


def test_linked_output_parent_is_rejected_without_external_write(
    tmp_path: Path,
    reviewed_synthetic_catalog: SyntheticReviewedArchives,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    linked_parent = tmp_path / "linked-parent"
    try:
        linked_parent.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")

    with pytest.raises(CanonicalMaterializationError, match="link|junction"):
        materialize_canonical_store(
            reviewed_synthetic_catalog.canary_root,
            linked_parent / "v1",
        )

    assert not tuple(outside.iterdir())
