from __future__ import annotations

import ast
import hashlib
import inspect
import json
import math
import os
import shutil
import socket
import struct
import sys
import zlib
from array import array
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from pydantic import ValidationError

from sdc import real_asset_intake as intake_module
from sdc import real_asset_media as media_module
from sdc.ark_entitlement_registry import REVIEWED_ARK_ENTITLEMENT_EVIDENCE
from sdc.compiler import stable_id
from sdc.creative_pilot import (
    build_creative_sample_pilot_documents,
    load_creative_sample_pilot_pack,
)
from sdc.evidence_authorization_registry import REVIEWED_EVIDENCE_AUTHORIZATIONS
from sdc.real_asset_intake import (
    CreativeSampleRealAssetIntakeTemplate,
    CreativeSampleRealAssetRightsManifest,
    CreativeSampleRealAssetSubmission,
    FrozenRealAssetPack,
    QualifiedRealAssetRevision,
    RealAssetIntakeError,
    RealAssetRightsReview,
    RealAssetSubmissionItem,
    assess_real_asset_submission,
    build_missing_real_asset_submission,
    build_real_asset_gap_report,
    build_real_asset_intake_template,
    build_real_asset_rights_manifest,
    build_real_asset_submission,
    freeze_real_asset_candidate_pack,
    load_real_asset_intake_template,
    load_real_asset_rights_manifest,
    load_real_asset_submission,
    qualify_real_asset_candidate_pack,
    verify_qualified_real_asset_revision,
    verify_real_asset_candidate_pack,
    write_real_asset_intake_templates,
)
from sdc.real_asset_media import (
    RealAssetMediaError,
    inspect_bgm_wav,
    inspect_png,
    inspect_voice_wav,
    read_safe_local_file,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_PILOT_ROOT = REPOSITORY_ROOT / "examples" / "creative-sample-pilot-v1"
EXPECTED_PATHS = (
    "assets/characters/gu-yan/v1.png",
    "assets/characters/su-qing/v1.png",
    "assets/scenes/office-night/v1.png",
    "assets/scenes/rooftop-dawn/v1.png",
    *(f"audio/voices/{ordinal:02d}.wav" for ordinal in range(9)),
    "audio/bgm/background.wav",
)
EVALUATED_AT = "2026-08-16T12:00:00Z"


def _digest(label: str) -> str:
    return hashlib.sha256(f"sdc-real-intake-test:{label}".encode()).hexdigest()


def _canonical_document(value: object) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")  # type: ignore[union-attr]
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _png_bytes(
    seed: int,
    *,
    width: int = 512,
    height: int = 512,
    color_type: int = 2,
    alpha: int = 255,
    interlace: int = 0,
    static: bool = False,
    metadata: bool = False,
) -> bytes:
    channels = 4 if color_type == 6 else 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            if static:
                pixel = (seed, seed, seed)
            else:
                pixel = (
                    (x + seed * 17) & 0xFF,
                    (y * 3 + seed * 29) & 0xFF,
                    (x + y * 5 + seed * 11) & 0xFF,
                )
            raw.extend(pixel)
            if channels == 4:
                raw.append(alpha)
    chunks = [
        _png_chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, interlace),
        )
    ]
    if metadata:
        chunks.append(_png_chunk(b"tEXt", b"Comment\0private metadata"))
    chunks.extend((_png_chunk(b"IDAT", zlib.compress(bytes(raw), 9)), _png_chunk(b"IEND", b"")))
    return b"\x89PNG\r\n\x1a\n" + b"".join(chunks)


def _wav_bytes(
    *,
    duration_ms: int,
    channels: int,
    seed: int,
    sample_rate: int = 48_000,
    amplitude: int = 4_000,
    clipped: bool = False,
    extra_chunk: bool = False,
) -> bytes:
    frames = sample_rate * duration_ms // 1000
    pattern_frames = min(frames, 480)
    pattern = array("h")
    cycles = seed + 3
    for frame in range(pattern_frames):
        value = int(round(amplitude * math.sin(2 * math.pi * cycles * frame / 480)))
        for channel in range(channels):
            pattern.append(value if channel == 0 else -value)
    repetitions, remainder = divmod(frames, pattern_frames)
    samples = pattern * repetitions + pattern[: remainder * channels]
    if clipped and samples:
        samples[0] = 32767
    if sys.byteorder != "little":
        samples.byteswap()
    payload = samples.tobytes()
    block_align = channels * 2
    fmt = struct.pack(
        "<HHIIHH", 1, channels, sample_rate, sample_rate * block_align, block_align, 16
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        return kind + struct.pack("<I", len(data)) + data + (b"\0" if len(data) & 1 else b"")

    chunks = [chunk(b"fmt ", fmt)]
    if extra_chunk:
        chunks.append(chunk(b"LIST", b"INFO"))
    chunks.append(chunk(b"data", payload))
    body = b"WAVE" + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def _write_exact_media_tree(root: Path, template: CreativeSampleRealAssetIntakeTemplate) -> None:
    root.mkdir()
    for requirement in template.requirements:
        target = root.joinpath(*requirement.logical_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        if requirement.kind == "IMAGE":
            data = _png_bytes(requirement.ordinal + 1)
        elif requirement.kind == "VOICE":
            data = _wav_bytes(
                duration_ms=250,
                channels=1,
                seed=requirement.ordinal + 1,
            )
        else:
            data = _wav_bytes(duration_ms=72_000, channels=2, seed=31)
        target.write_bytes(data)


def _write_shape_only_tree(root: Path, template: CreativeSampleRealAssetIntakeTemplate) -> None:
    root.mkdir()
    for requirement in template.requirements:
        target = root.joinpath(*requirement.logical_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x")


def _submission_with_items(
    template: CreativeSampleRealAssetIntakeTemplate,
    items: tuple[RealAssetSubmissionItem, ...],
) -> CreativeSampleRealAssetSubmission:
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-submission",
        "profile": "creative-sample-real-asset-intake-v1",
        "template_id": template.template_id,
        "items": tuple(item.model_dump(mode="json") for item in items),
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetSubmission(
        submission_id=stable_id("real_asset_submission", payload),
        template_id=template.template_id,
        items=items,
    )


def _complete_submission(
    template: CreativeSampleRealAssetIntakeTemplate, source_root: Path
) -> CreativeSampleRealAssetSubmission:
    items: list[RealAssetSubmissionItem] = []
    for requirement in template.requirements:
        data = source_root.joinpath(*requirement.logical_path.split("/")).read_bytes()
        items.append(
            RealAssetSubmissionItem(
                requirement_id=requirement.requirement_id,
                logical_path=requirement.logical_path,
                status="SUBMITTED",
                source_authority="USER_PROVIDED_LOCAL",
                expected_sha256=hashlib.sha256(data).hexdigest(),
                expected_size_bytes=len(data),
                provenance_record_sha256=_digest(
                    f"private-provenance:{requirement.requirement_id}"
                ),
            )
        )
    return build_real_asset_submission(tuple(items), template=template)


def _review(*, pack_id: str, ordinal: int, descriptor: object, role: str) -> RealAssetRightsReview:
    requirement_id = str(descriptor.requirement_id)  # type: ignore[attr-defined]
    return RealAssetRightsReview(
        ordinal=ordinal,
        pack_id=pack_id,
        requirement_id=requirement_id,
        logical_path=str(descriptor.logical_path),  # type: ignore[attr-defined]
        reviewer_role=role,
        reviewer_ref_sha256=_digest(f"reviewer:{role}"),
        review_record_sha256=_digest(f"review:{requirement_id}:{role}"),
        media_sha256=str(descriptor.sha256),  # type: ignore[attr-defined]
        media_size_bytes=int(descriptor.size_bytes),  # type: ignore[attr-defined]
        provenance_record_sha256=str(  # type: ignore[attr-defined]
            descriptor.provenance_record_sha256
        ),
        technical_record_sha256=str(  # type: ignore[attr-defined]
            descriptor.technical_record_sha256
        ),
        source_authority=str(descriptor.source_authority),  # type: ignore[attr-defined]
        copyright_basis="私有证据库中的精确字节许可记录覆盖本次内部短剧评估。",
        likeness_basis="私有证据库记录确认虚构形象或已获表演者与声音使用同意。",
        privacy_basis="双人检查未发现未披露个人信息，原始证据不进入Git。",
        territory="CN",
        use_scope="短剧内部评估、剪辑、合成及后续另行审批的生成参考。",
        reviewed_at="2026-08-16T10:00:00Z",
        valid_until="2027-08-16T10:00:00Z",
        provenance_approved=True,
        copyright_approved=True,
        likeness_approved=True,
        privacy_approved=True,
        territory_approved=True,
        use_scope_approved=True,
        content_role_approved=True,
        decision="APPROVED",
    )


def _rights_manifest(
    frozen: FrozenRealAssetPack,
) -> CreativeSampleRealAssetRightsManifest:
    reviews = tuple(
        _review(
            pack_id=frozen.manifest.pack_id,
            ordinal=index * 2 + role_index,
            descriptor=descriptor,
            role=role,
        )
        for index, descriptor in enumerate(frozen.manifest.objects)
        for role_index, role in enumerate(("REVIEWER_A", "REVIEWER_B"))
    )
    return build_real_asset_rights_manifest(pack=frozen.manifest, reviews=reviews)


def _replace_rights_review(
    manifest: CreativeSampleRealAssetRightsManifest,
    index: int,
    **changes: object,
) -> CreativeSampleRealAssetRightsManifest:
    reviews = list(manifest.reviews)
    review_payload = reviews[index].model_dump(mode="python")
    review_payload.update(changes)
    reviews[index] = RealAssetRightsReview.model_validate(review_payload, strict=True)
    reviews_tuple = tuple(reviews)
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-rights-manifest",
        "profile": "creative-sample-real-asset-intake-v1",
        "pack_id": manifest.pack_id,
        "reviews": tuple(item.model_dump(mode="json") for item in reviews_tuple),
        "status": "REVIEW_CANDIDATE",
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetRightsManifest(
        manifest_id=stable_id("real_asset_rights", payload),
        pack_id=manifest.pack_id,
        reviews=reviews_tuple,
    )


@contextmanager
def _network_forbidden() -> Iterator[None]:
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo
    original_connect = socket.socket.connect

    def fail(*_: object, **__: object) -> None:
        raise AssertionError("real asset intake must not access the network")

    socket.create_connection = fail  # type: ignore[assignment]
    socket.getaddrinfo = fail  # type: ignore[assignment]
    socket.socket.connect = fail  # type: ignore[method-assign]
    try:
        yield
    finally:
        socket.create_connection = original_create_connection
        socket.getaddrinfo = original_getaddrinfo
        socket.socket.connect = original_connect  # type: ignore[method-assign]


@dataclass(frozen=True, slots=True)
class _QualifiedFixture:
    template: CreativeSampleRealAssetIntakeTemplate
    source_root: Path
    submission: CreativeSampleRealAssetSubmission
    frozen: FrozenRealAssetPack
    rights: CreativeSampleRealAssetRightsManifest
    revisions_parent: Path
    qualified: QualifiedRealAssetRevision


@pytest.fixture(scope="module")
def qualified_fixture(tmp_path_factory: pytest.TempPathFactory) -> _QualifiedFixture:
    root = tmp_path_factory.mktemp("real-asset-intake")
    template = build_real_asset_intake_template()
    source_root = root / "explicit-local-candidates"
    _write_exact_media_tree(source_root, template)
    submission = _complete_submission(template, source_root)
    packs_parent = root / "packs"
    revisions_parent = root / "revisions"
    packs_parent.mkdir()
    revisions_parent.mkdir()
    with _network_forbidden():
        frozen = freeze_real_asset_candidate_pack(
            submission=submission,
            source_root=source_root,
            output_parent=packs_parent,
        )
        rights = _rights_manifest(frozen)
        qualified = qualify_real_asset_candidate_pack(
            pack_root=frozen.root,
            rights=rights,
            output_parent=revisions_parent,
            evaluated_at=EVALUATED_AT,
        )
    return _QualifiedFixture(
        template=template,
        source_root=source_root,
        submission=submission,
        frozen=frozen,
        rights=rights,
        revisions_parent=revisions_parent,
        qualified=qualified,
    )


def test_template_is_exact_deterministic_fourteen_member_zero_authority() -> None:
    template = build_real_asset_intake_template()
    pilot_spec, pilot = build_creative_sample_pilot_documents()

    assert template == build_real_asset_intake_template()
    assert tuple(item.ordinal for item in template.requirements) == tuple(range(14))
    assert tuple(item.logical_path for item in template.requirements) == EXPECTED_PATHS
    assert tuple(item.kind for item in template.requirements) == (
        "IMAGE",
        "IMAGE",
        "IMAGE",
        "IMAGE",
        *("VOICE" for _ in range(9)),
        "BGM",
    )
    assert len({item.requirement_id for item in template.requirements}) == 14
    assert template.pilot_pack_id == pilot.pack_id
    assert template.pilot_compilation_id == pilot.compilation_id
    assert template.pilot_ordered_shot_ids == pilot.ordered_shot_ids
    assert template.forbidden_fixture_asset_ids == tuple(sorted(pilot.active_asset_version_ids))
    assert template.forbidden_fixture_sha256 == tuple(
        sorted(item.placeholder_sha256 for item in pilot.asset_requirements)
    )
    assert (
        template.pilot_sample_spec_sha256
        == hashlib.sha256(
            json.dumps(
                pilot_spec.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        ).hexdigest()
    )
    assert template.status == "HUMAN_GATE"
    assert template.execution_authorized is False
    assert template.posts_allowed == template.provider_requests == 0

    for requirement in template.requirements[:4]:
        assert requirement.media_type == "image/png"
        assert requirement.forbidden_fixture_asset_id is not None
        assert requirement.forbidden_fixture_sha256 is not None
        assert requirement.technical_profile == "strict-png-real-reference-v1"
    for requirement in template.requirements[4:13]:
        assert requirement.media_type == "audio/wav"
        assert requirement.start_ms is not None
        assert requirement.end_ms is not None
        assert requirement.start_ms < requirement.end_ms
        assert requirement.exact_text
        assert requirement.technical_profile == "pcm16-48khz-mono-dialogue-v1"
    bgm = template.requirements[-1]
    assert (bgm.start_ms, bgm.end_ms) == (0, 72_000)
    assert bgm.technical_profile == "pcm16-48khz-stereo-score-72s-v1"


def test_missing_and_partial_submissions_preserve_every_gap_and_human_gate() -> None:
    template = build_real_asset_intake_template()
    missing = build_missing_real_asset_submission(template)
    report = build_real_asset_gap_report(missing, template)
    assert len(missing.items) == len(report.rows) == 14
    assert {item.status for item in missing.items} == {"MISSING"}
    assert {item.disposition for item in report.rows} == {"MISSING"}
    assert (report.missing_count, report.pending_count, report.approved_count) == (14, 0, 0)
    assert report.current_gate == "HUMAN_GATE"
    assert report.ready_for_rights_review is False
    assert report.execution_authorized is False
    assert report.posts_allowed == report.provider_requests == 0
    assert all(row.failures and row.replacement_guidance for row in report.rows)

    first = template.requirements[0]
    partial_items = list(missing.items)
    partial_items[0] = RealAssetSubmissionItem(
        requirement_id=first.requirement_id,
        logical_path=first.logical_path,
        status="SUBMITTED",
        source_authority="USER_PROVIDED_LOCAL",
        expected_sha256=_digest("candidate-one"),
        expected_size_bytes=123,
        provenance_record_sha256=_digest("candidate-one-provenance"),
    )
    partial = _submission_with_items(template, tuple(partial_items))
    partial_report = build_real_asset_gap_report(partial, template)
    assert partial_report.rows[0].disposition == "REVIEW_PENDING"
    assert (partial_report.missing_count, partial_report.pending_count) == (13, 1)
    assert partial_report.approved_count == 0


def test_local_assessment_reports_pending_rejected_missing_and_identity_mismatch(
    tmp_path: Path,
) -> None:
    template = build_real_asset_intake_template()
    source = tmp_path / "explicit-subset"
    source.mkdir()
    items = list(build_missing_real_asset_submission(template).items)

    for index, data in ((0, _png_bytes(41)), (1, b"not-a-png")):
        requirement = template.requirements[index]
        target = source.joinpath(*requirement.logical_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        items[index] = RealAssetSubmissionItem(
            requirement_id=requirement.requirement_id,
            logical_path=requirement.logical_path,
            status="SUBMITTED",
            source_authority="USER_PROVIDED_LOCAL",
            expected_sha256=hashlib.sha256(data).hexdigest(),
            expected_size_bytes=len(data),
            provenance_record_sha256=_digest(f"assessment:{index}"),
        )

    absent = template.requirements[2]
    items[2] = RealAssetSubmissionItem(
        requirement_id=absent.requirement_id,
        logical_path=absent.logical_path,
        status="SUBMITTED",
        source_authority="USER_PROVIDED_LOCAL",
        expected_sha256=_digest("declared-but-absent"),
        expected_size_bytes=1,
        provenance_record_sha256=_digest("assessment:2"),
    )
    submission = build_real_asset_submission(tuple(items), template=template)
    report = assess_real_asset_submission(submission=submission, source_root=source)

    assert tuple(row.disposition for row in report.rows[:3]) == (
        "REVIEW_PENDING",
        "TECHNICAL_REJECTED",
        "IDENTITY_MISMATCH",
    )
    assert {row.disposition for row in report.rows[3:]} == {"MISSING"}
    assert (report.missing_count, report.rejected_count, report.pending_count) == (11, 2, 1)
    assert report.approved_count == 0
    assert report.current_gate == "HUMAN_GATE"
    assert report.ready_for_rights_review is False
    assert report.execution_authorized is False
    assert report.posts_allowed == report.provider_requests == 0


@pytest.mark.parametrize("mutation", ["reorder", "duplicate"])
def test_submission_requires_exact_ordered_fourteen_slot_closure(mutation: str) -> None:
    template = build_real_asset_intake_template()
    items = list(build_missing_real_asset_submission(template).items)
    if mutation == "reorder":
        items[0], items[1] = items[1], items[0]
    else:
        items[1] = items[0]
    submission = _submission_with_items(template, tuple(items))
    with pytest.raises(RealAssetIntakeError, match="fourteen-slot closure"):
        build_real_asset_gap_report(submission, template)


def test_template_writer_and_loaders_use_canonical_new_only_documents(tmp_path: Path) -> None:
    root = tmp_path / "published"
    template_path, gap_path = write_real_asset_intake_templates(root)
    template = build_real_asset_intake_template()
    assert {item.name for item in root.iterdir()} == {"intake-template.json", "gap-report.json"}
    assert template_path.read_bytes() == _canonical_document(template)
    assert gap_path.read_bytes() == _canonical_document(
        build_real_asset_gap_report(template=template)
    )
    assert load_real_asset_intake_template(template_path) == template

    submission = build_missing_real_asset_submission(template)
    submission_path = tmp_path / "submission.json"
    submission_path.write_bytes(_canonical_document(submission))
    assert load_real_asset_submission(submission_path) == submission
    with pytest.raises(RealAssetIntakeError, match="new directory"):
        write_real_asset_intake_templates(root)


@pytest.mark.parametrize(
    "name,raw",
    [
        ("duplicate", b'{"schema_version":"1.0.0","schema_version":"1.0.0"}\n'),
        ("nan", b'{"value":NaN}\n'),
        ("infinity", b'{"value":Infinity}\n'),
        ("invalid-utf8", b"\xff\xfe"),
        ("bom", b"\xef\xbb\xbf{}\n"),
        ("array", b"[]\n"),
        ("scalar", b"null\n"),
    ],
)
def test_strict_json_rejects_ambiguous_or_non_object_bytes(
    tmp_path: Path, name: str, raw: bytes
) -> None:
    path = tmp_path / f"{name}.json"
    path.write_bytes(raw)
    with pytest.raises(RealAssetIntakeError):
        load_real_asset_intake_template(path)


def test_strict_json_rejects_noncanonical_extra_coerced_and_oversize(tmp_path: Path) -> None:
    template = build_real_asset_intake_template()
    compact = json.dumps(
        template.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    extra = template.model_dump(mode="json")
    extra["unexpected"] = "forbidden"
    coerced = template.model_dump(mode="json")
    coerced["posts_allowed"] = False
    cases = {
        "compact": compact,
        "extra": _canonical_document(extra),
        "coerced": _canonical_document(coerced),
        "oversize": b"{" + b" " * (1024 * 1024) + b"}",
    }
    for name, raw in cases.items():
        path = tmp_path / f"{name}.json"
        path.write_bytes(raw)
        with pytest.raises(RealAssetIntakeError):
            load_real_asset_intake_template(path)


def test_strict_json_rejects_hardlinked_document(tmp_path: Path) -> None:
    root = tmp_path / "published"
    template_path, _ = write_real_asset_intake_templates(root)
    outside = tmp_path / "outside.json"
    try:
        os.link(template_path, outside)
    except OSError:
        pytest.skip("hard links are unavailable on this host")
    with pytest.raises(RealAssetIntakeError, match="non-linked"):
        load_real_asset_intake_template(template_path)


def test_strict_json_rejects_inode_replacement_between_lstat_and_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "published"
    template_path, _ = write_real_asset_intake_templates(root)
    replacement = tmp_path / "replacement.json"
    replacement.write_bytes(template_path.read_bytes())
    original_open = Path.open
    replaced = False

    def replace_before_open(self: Path, *args: object, **kwargs: object) -> object:
        nonlocal replaced
        if self == template_path and not replaced:
            replaced = True
            os.replace(replacement, self)
        return original_open(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "open", replace_before_open)
    with pytest.raises(RealAssetIntakeError, match="changed while it was read"):
        load_real_asset_intake_template(template_path)
    assert replaced is True


@pytest.mark.parametrize(
    "unsafe",
    [
        "../candidate.png",
        "/candidate.png",
        "C:/candidate.png",
        "\\\\server\\share\\candidate.png",
        "assets//candidate.png",
        "assets/./candidate.png",
        "assets/CON.png",
        "assets/candidate. ",
        "assets/candidate?.png",
        "assets/cafe\u0301.png",
        "assets/control\x01.png",
    ],
)
def test_logical_paths_are_strictly_portable(unsafe: str) -> None:
    requirement = build_real_asset_intake_template().requirements[0]
    with pytest.raises(ValidationError):
        RealAssetSubmissionItem(
            requirement_id=requirement.requirement_id,
            logical_path=unsafe,
        )


@pytest.mark.parametrize("drift", ["missing", "extra", "hardlink", "symlink-reparse"])
def test_freezer_rejects_nonexact_or_linked_source_tree(tmp_path: Path, drift: str) -> None:
    template = build_real_asset_intake_template()
    source = tmp_path / "source"
    _write_shape_only_tree(source, template)
    submission = _complete_submission(template, source)
    if drift == "missing":
        source.joinpath(*template.requirements[0].logical_path.split("/")).unlink()
    elif drift == "extra":
        (source / "unexpected.bin").write_bytes(b"unexpected")
    elif drift == "hardlink":
        first = source.joinpath(*template.requirements[0].logical_path.split("/"))
        outside = tmp_path / "outside.bin"
        try:
            os.link(first, outside)
        except OSError:
            pytest.skip("hard links are unavailable on this host")
    else:
        first = source.joinpath(*template.requirements[0].logical_path.split("/"))
        outside = tmp_path / "symlink-target.bin"
        outside.write_bytes(first.read_bytes())
        first.unlink()
        try:
            first.symlink_to(outside)
        except OSError:
            pytest.skip("symbolic links/reparse points are unavailable on this host")
    output_parent = tmp_path / "packs"
    output_parent.mkdir()
    with pytest.raises(RealAssetIntakeError, match="closure|hard-linked|links"):
        freeze_real_asset_candidate_pack(
            submission=submission,
            source_root=source,
            output_parent=output_parent,
        )


def test_freezer_rejects_partial_submission_before_any_publication(tmp_path: Path) -> None:
    template = build_real_asset_intake_template()
    source = tmp_path / "source"
    _write_shape_only_tree(source, template)
    output_parent = tmp_path / "packs"
    output_parent.mkdir()
    with pytest.raises(RealAssetIntakeError, match="partial intake"):
        freeze_real_asset_candidate_pack(
            submission=build_missing_real_asset_submission(template),
            source_root=source,
            output_parent=output_parent,
        )
    assert not tuple(output_parent.iterdir())


def test_png_profile_accepts_active_rgb_and_rejects_fixture_digest(tmp_path: Path) -> None:
    path = tmp_path / "active.png"
    path.write_bytes(_png_bytes(7))
    source, evidence = inspect_png(path)
    assert source.size_bytes == path.stat().st_size
    assert source.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert (evidence.width, evidence.height, evidence.color_space) == (512, 512, "RGB")
    assert evidence.distinct_color_count >= 16
    assert evidence.metadata_free is True
    assert evidence.semantic_privacy_reviewed is False
    with pytest.raises(RealAssetMediaError, match="placeholder"):
        inspect_png(path, forbidden_sha256=(source.sha256,))


@pytest.mark.parametrize(
    "name,builder",
    [
        ("too-small", lambda: _png_bytes(1, width=511)),
        ("static", lambda: _png_bytes(1, static=True)),
        ("metadata", lambda: _png_bytes(1, metadata=True)),
        ("transparent", lambda: _png_bytes(1, color_type=6, alpha=254)),
        ("interlaced", lambda: _png_bytes(1, interlace=1)),
        ("trailing", lambda: _png_bytes(1) + b"polyglot"),
        ("bad-crc", lambda: _png_bytes(1)[:-1] + bytes([_png_bytes(1)[-1] ^ 1])),
    ],
)
def test_png_profile_fails_closed_on_decode_content_or_privacy_container_boundary(
    tmp_path: Path, name: str, builder: Callable[[], bytes]
) -> None:
    path = tmp_path / f"{name}.png"
    path.write_bytes(builder())
    with pytest.raises(RealAssetMediaError):
        inspect_png(path)


def test_safe_media_reader_rejects_oversize_and_hardlinks(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.bin"
    with oversized.open("wb") as handle:
        handle.truncate(1025)
    with pytest.raises(RealAssetMediaError, match="byte boundary"):
        read_safe_local_file(oversized, max_bytes=1024)

    regular = tmp_path / "regular.bin"
    regular.write_bytes(b"content")
    outside = tmp_path / "hardlink.bin"
    try:
        os.link(regular, outside)
    except OSError:
        pytest.skip("hard links are unavailable on this host")
    with pytest.raises(RealAssetMediaError, match="non-linked"):
        read_safe_local_file(regular, max_bytes=1024)


def test_wav_profiles_accept_exact_pcm16_and_bind_measured_evidence(tmp_path: Path) -> None:
    voice = tmp_path / "voice.wav"
    voice.write_bytes(_wav_bytes(duration_ms=250, channels=1, seed=5))
    source, evidence = inspect_voice_wav(voice, maximum_duration_ms=250)
    assert source.sha256 == hashlib.sha256(voice.read_bytes()).hexdigest()
    assert (evidence.codec, evidence.sample_rate_hz, evidence.channels) == (
        "pcm_s16le",
        48_000,
        1,
    )
    assert evidence.duration_ms == 250
    assert evidence.clipped_sample_count == 0
    assert evidence.silence_ppm <= 800_000
    assert evidence.semantic_content_reviewed is False


@pytest.mark.parametrize(
    "name,data,maximum_ms",
    [
        ("too-short", _wav_bytes(duration_ms=249, channels=1, seed=1), 1000),
        ("too-long", _wav_bytes(duration_ms=251, channels=1, seed=1), 250),
        ("wrong-rate", _wav_bytes(duration_ms=250, channels=1, seed=1, sample_rate=44_100), 250),
        ("wrong-channels", _wav_bytes(duration_ms=250, channels=2, seed=1), 250),
        ("clipped", _wav_bytes(duration_ms=250, channels=1, seed=1, clipped=True), 250),
        ("silent", _wav_bytes(duration_ms=250, channels=1, seed=1, amplitude=0), 250),
        ("metadata", _wav_bytes(duration_ms=250, channels=1, seed=1, extra_chunk=True), 250),
    ],
    ids=[
        "too-short",
        "too-long",
        "wrong-rate",
        "wrong-channels",
        "clipped",
        "silent",
        "metadata",
    ],
)
def test_voice_wav_rejects_rate_channel_duration_clipping_silence_and_extra_chunks(
    tmp_path: Path, name: str, data: bytes, maximum_ms: int
) -> None:
    path = tmp_path / f"{name}.wav"
    path.write_bytes(data)
    with pytest.raises(RealAssetMediaError):
        inspect_voice_wav(path, maximum_duration_ms=maximum_ms)


def test_bgm_requires_exact_stereo_72_second_master_clock(tmp_path: Path) -> None:
    short = tmp_path / "short-bgm.wav"
    short.write_bytes(_wav_bytes(duration_ms=1000, channels=2, seed=9))
    with pytest.raises(RealAssetMediaError, match="duration|72-second"):
        inspect_bgm_wav(short)


def test_full_freeze_double_review_and_revision_are_new_and_still_zero_authority(
    qualified_fixture: _QualifiedFixture,
) -> None:
    template = qualified_fixture.template
    frozen = qualified_fixture.frozen
    rights = qualified_fixture.rights
    qualified = qualified_fixture.qualified
    pilot_spec, pilot = build_creative_sample_pilot_documents()

    assert frozen.created is True
    assert len(frozen.manifest.objects) == 14
    assert tuple(item.logical_path for item in frozen.manifest.objects) == EXPECTED_PATHS
    assert len({item.sha256 for item in frozen.manifest.objects}) == 14
    assert frozen.manifest.pilot_pack_id == template.pilot_pack_id
    assert frozen.manifest.state == "FROZEN_UNREVIEWED"
    assert frozen.manifest.current_gate == "HUMAN_GATE"
    assert frozen.manifest.eligible_for_real_generation is False
    assert frozen.manifest.execution_authorized is False
    assert frozen.manifest.posts_allowed == frozen.manifest.provider_requests == 0
    assert len(rights.reviews) == 28
    assert tuple(item.reviewer_role for item in rights.reviews) == tuple(
        role for _ in range(14) for role in ("REVIEWER_A", "REVIEWER_B")
    )
    assert rights.current_gate == "HUMAN_GATE"
    assert rights.execution_authorized is False
    assert rights.posts_allowed == rights.provider_requests == 0

    revision = qualified.revision
    assert qualified.created is True
    assert revision.revision_number == 2
    assert revision.predecessor_pilot_pack_id == pilot.pack_id
    assert revision.predecessor_compilation_id == pilot.compilation_id
    assert revision.predecessor_shot_ids == pilot.ordered_shot_ids
    assert revision.real_spec != pilot_spec
    assert revision.compilation.id != pilot.compilation_id
    assert len(revision.ordered_shot_ids) == 10
    assert all(
        current != fixture
        for current, fixture in zip(revision.ordered_shot_ids, pilot.ordered_shot_ids, strict=True)
    )
    old_ids = set(pilot.active_asset_version_ids)
    old_digests = {item.placeholder_sha256 for item in pilot.asset_requirements}
    new_versions = tuple(
        version
        for bible in (*revision.real_spec.character_bibles, *revision.real_spec.scene_bibles)
        for version in bible.asset_versions
    )
    assert {item.version for item in new_versions} == {2}
    assert not old_ids & {item.id for item in new_versions}
    assert not old_digests & {item.content_sha256 for item in new_versions}
    assert all(not item.approval_ref.startswith("pilot-fixture-only-") for item in new_versions)
    assert tuple(item.kind for item in revision.audio_bindings) == (
        *("VOICE" for _ in range(9)),
        "BGM",
    )
    assert revision.decision == "PASS_ASSET_INTAKE_ONLY"
    assert revision.current_gate == "HUMAN_GATE"
    assert revision.provider_state == "NOT_AUTHORIZED"
    assert revision.eligible_for_separate_provider_approval is True
    assert revision.execution_authorized is False
    assert revision.posts_allowed == revision.provider_requests == 0

    assert qualified.root.name == revision.revision_id
    assert qualified.revision_path.name == "real-asset-revision.json"


def test_rights_loader_is_strict_and_canonical(
    tmp_path: Path, qualified_fixture: _QualifiedFixture
) -> None:
    path = tmp_path / "rights.json"
    path.write_bytes(_canonical_document(qualified_fixture.rights))
    assert load_real_asset_rights_manifest(path) == qualified_fixture.rights
    path.write_bytes(
        json.dumps(
            qualified_fixture.rights.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    )
    with pytest.raises(RealAssetIntakeError, match="canonical"):
        load_real_asset_rights_manifest(path)


@pytest.mark.parametrize(
    "drift,changes,match",
    [
        (
            "same-reviewer",
            {"reviewer_ref_sha256": _digest("reviewer:REVIEWER_A")},
            "one person",
        ),
        ("disagreement", {"territory": "CN-HK"}, "disagree"),
        (
            "rejected",
            {"privacy_approved": False, "decision": "REJECTED"},
            "rejected",
        ),
        ("expired", {"valid_until": EVALUATED_AT}, "expired"),
        (
            "future-review",
            {"reviewed_at": "2026-08-17T10:00:00Z", "valid_until": "2027-08-17T10:00:00Z"},
            "future",
        ),
        ("object-drift", {"media_size_bytes": 1}, "drifted"),
    ],
)
def test_missing_disputed_rejected_expired_or_drifted_rights_remain_human_gate(
    tmp_path: Path,
    qualified_fixture: _QualifiedFixture,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
    changes: dict[str, object],
    match: str,
) -> None:
    monkeypatch.setattr(
        intake_module,
        "verify_real_asset_candidate_pack",
        lambda _: qualified_fixture.frozen,
    )
    rights = _replace_rights_review(qualified_fixture.rights, 1, **changes)
    parent = tmp_path / drift
    parent.mkdir()
    with pytest.raises(RealAssetIntakeError, match=match):
        qualify_real_asset_candidate_pack(
            pack_root=qualified_fixture.frozen.root,
            rights=rights,
            output_parent=parent,
            evaluated_at=EVALUATED_AT,
        )
    assert not tuple(parent.iterdir())


def test_rights_contract_requires_exact_twenty_eight_ordered_reviews(
    qualified_fixture: _QualifiedFixture,
) -> None:
    payload = qualified_fixture.rights.model_dump(mode="python")
    payload["reviews"] = qualified_fixture.rights.reviews[:-1]
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetRightsManifest.model_validate(payload, strict=True)

    reviews = list(qualified_fixture.rights.reviews)
    reviews[0], reviews[1] = reviews[1], reviews[0]
    payload["reviews"] = tuple(reviews)
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetRightsManifest.model_validate(payload, strict=True)


def test_rights_reject_cross_object_reuse_of_both_private_review_digests(
    qualified_fixture: _QualifiedFixture,
) -> None:
    reviews = list(qualified_fixture.rights.reviews)
    for target_index, source_index in ((2, 0), (3, 1)):
        payload = reviews[target_index].model_dump(mode="python")
        payload["review_record_sha256"] = reviews[source_index].review_record_sha256
        reviews[target_index] = RealAssetRightsReview.model_validate(payload, strict=True)

    with pytest.raises(ValidationError, match="twenty-eight private review records"):
        build_real_asset_rights_manifest(
            pack=qualified_fixture.frozen.manifest,
            reviews=tuple(reviews),
        )


@pytest.mark.parametrize("drift", ["object", "extra"])
def test_frozen_pack_verification_rejects_cas_or_filesystem_drift(
    tmp_path: Path, qualified_fixture: _QualifiedFixture, drift: str
) -> None:
    copied = tmp_path / qualified_fixture.frozen.manifest.pack_id
    shutil.copytree(qualified_fixture.frozen.root, copied)
    if drift == "extra":
        (copied / "unexpected.bin").write_bytes(b"unexpected")
    else:
        descriptor = qualified_fixture.frozen.manifest.objects[0]
        object_path = copied.joinpath(*descriptor.object_path.split("/"))
        object_path.write_bytes(object_path.read_bytes() + b"drift")
    with pytest.raises(RealAssetIntakeError, match="closure|identity|verified"):
        verify_real_asset_candidate_pack(copied)


def test_clean_pack_and_qualified_revision_cannot_be_verified_under_renamed_roots(
    tmp_path: Path, qualified_fixture: _QualifiedFixture
) -> None:
    renamed_pack = tmp_path / "renamed-pack"
    shutil.copytree(qualified_fixture.frozen.root, renamed_pack)
    with pytest.raises(RealAssetIntakeError, match="root name.*pack ID"):
        verify_real_asset_candidate_pack(renamed_pack)

    renamed_revision = tmp_path / "renamed-revision"
    shutil.copytree(qualified_fixture.qualified.root, renamed_revision)
    with pytest.raises(RealAssetIntakeError, match="root name.*revision ID"):
        verify_qualified_real_asset_revision(
            renamed_revision,
            pack_root=qualified_fixture.frozen.root,
        )


def test_build_freeze_and_qualification_have_no_network_or_secret_boundary(
    tmp_path: Path, qualified_fixture: _QualifiedFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel = "must-never-appear-in-real-intake-output"
    monkeypatch.setenv("SDC_REAL_INTAKE_SENTINEL", sentinel)
    destination = tmp_path / "templates"
    with _network_forbidden():
        write_real_asset_intake_templates(destination)
        load_real_asset_intake_template(destination / "intake-template.json")
        verify_qualified_real_asset_revision(
            qualified_fixture.qualified.root,
            pack_root=qualified_fixture.frozen.root,
        )
    for root in (destination, qualified_fixture.frozen.root, qualified_fixture.qualified.root):
        for path in root.rglob("*"):
            if path.is_file():
                assert sentinel.encode() not in path.read_bytes()


def test_intake_modules_have_no_network_runtime_provider_key_or_authority_dependency() -> None:
    imported_roots: set[str] = set()
    imported_modules: set[str] = set()
    for module in (intake_module, media_module):
        source = inspect.getsource(module)
        assert "os.environ" not in source
        assert "os.getenv" not in source
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.partition(".")[0] for alias in node.names)
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_roots.add(node.module.partition(".")[0])
                imported_modules.add(node.module)
    assert imported_roots.isdisjoint(
        {
            "aiohttp",
            "asyncpg",
            "boto3",
            "httpx",
            "requests",
            "socket",
            "sqlalchemy",
            "temporalio",
            "urllib",
        }
    )
    assert imported_modules.isdisjoint(
        {
            "sdc.ark_provider",
            "sdc.canary",
            "sdc.evidence_authorization",
            "sdc.evidence_ledger",
            "sdc.persistence",
            "sdc.temporal_workflows",
            "sdc.worker",
        }
    )
    assert REVIEWED_ARK_ENTITLEMENT_EVIDENCE == ()
    assert REVIEWED_EVIDENCE_AUTHORIZATIONS == ()


def test_no_real_or_private_media_is_committed_as_an_intake_example() -> None:
    root = REPOSITORY_ROOT / "examples" / "creative-sample-real-asset-intake-v1"
    if not root.exists():
        return
    files = tuple(path for path in root.rglob("*") if path.is_file())
    forbidden_suffixes = {
        ".aac",
        ".flac",
        ".jpeg",
        ".jpg",
        ".m4a",
        ".mov",
        ".mp3",
        ".mp4",
        ".pdf",
        ".png",
        ".wav",
    }
    assert files
    assert all(path.suffix.casefold() not in forbidden_suffixes for path in files)


def test_original_pilot_contract_and_committed_fixture_remain_exactly_compatible() -> None:
    spec, pack = build_creative_sample_pilot_documents()
    loaded = load_creative_sample_pilot_pack(COMMITTED_PILOT_ROOT)
    assert loaded.spec == spec
    assert loaded.pack == pack
    assert loaded.compilation.id == pack.compilation_id
    assert pack.synthetic_rehearsal.expected_decision == "STOP"
    assert pack.synthetic_rehearsal.human_status == "NOT_SCORED"
    assert pack.synthetic_rehearsal.provider_requests == 0
    assert pack.provider_batch_plan.state == "NOT_AUTHORIZED"
    assert pack.provider_batch_plan.posts_allowed == 0
