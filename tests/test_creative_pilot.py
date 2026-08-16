from __future__ import annotations

import ast
import asyncio
import copy
import hashlib
import inspect
import json
import os
import shutil
import socket
import subprocess
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Literal, cast

import pytest
from pydantic import ValidationError

from sdc import creative_pilot as creative_pilot_module
from sdc.ark_entitlement_registry import REVIEWED_ARK_ENTITLEMENT_EVIDENCE
from sdc.compiler import compile_creative_sample
from sdc.contracts import (
    CharacterAssetVersion,
    CharacterBible,
    CreativeSampleDecision,
    CreativeSampleSpec,
    SceneAssetVersion,
    SceneBible,
)
from sdc.creative_pilot import (
    CreativePilotError,
    CreativeSamplePilotPack,
    CreativeSamplePilotSpecDocument,
    build_creative_sample_pilot_documents,
    load_creative_sample_pilot_pack,
    synthetic_placeholder_png_bytes,
    write_creative_sample_pilot_documents,
)
from sdc.creative_sample import (
    AssetImport,
    BGMImport,
    CreativeSampleImportManifest,
    CreativeSampleRunResult,
    ReviewerAssessment,
    ShotImportReview,
    VoiceImport,
    run_creative_sample,
    verify_creative_sample_output,
)
from sdc.evidence_authorization_registry import REVIEWED_EVIDENCE_AUTHORIZATIONS

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_PACK_ROOT = REPOSITORY_ROOT / "examples" / "creative-sample-pilot-v1"
EXPECTED_CLOCK = (
    (0, 6000),
    (6000, 7000),
    (13000, 7000),
    (20000, 8000),
    (28000, 8000),
    (36000, 7000),
    (43000, 7000),
    (50000, 8000),
    (58000, 7000),
    (65000, 7000),
)
EXPECTED_DIALOGUE_CLOCK = (
    (6800, 11600),
    (14000, 15600),
    (20900, 24800),
    (28900, 32600),
    (36900, 41800),
    (44100, 46100),
    (50900, 55600),
    (58900, 62200),
    (65700, 70400),
)
EXPECTED_FAILURE_CODES = {
    "artifact.duplicate_media",
    "artifact.extra_person",
    "artifact.face",
    "artifact.hand",
    "artifact.static_or_placeholder",
    "artifact.text_or_watermark",
    "audio.bgm_rights",
    "audio.subtitle_timing",
    "audio.voice_quality",
    "content.character_drift",
    "content.dialogue_lipsync",
    "content.identity_break",
    "content.prop_drift",
    "content.scene_drift",
    "content.shot_intent",
    "content.wardrobe_drift",
    "provenance.unverified",
    "review.disagreement",
    "rights.unverified",
    "technical.duration",
    "technical.frame",
}
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _canonical_json_bytes(value: object) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _canonical_contract_bytes(value: CreativeSampleSpec | CreativeSampleImportManifest) -> bytes:
    return json.dumps(
        value.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _write_canonical(path: Path, value: object) -> None:
    path.write_bytes(_canonical_json_bytes(value))


def _resign_pack(payload: dict[str, object]) -> dict[str, object]:
    unsigned = {key: value for key, value in payload.items() if key != "pack_id"}
    payload["pack_id"] = CreativeSamplePilotPack.derive_id(unsigned)
    return payload


def _copy_pack(tmp_path: Path) -> Path:
    destination = tmp_path / "pilot-pack"
    shutil.copytree(COMMITTED_PACK_ROOT, destination)
    return destination


def _ffmpeg(*args: str) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-y", *args],
        check=True,
        capture_output=True,
    )


def _byte_identity(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def _review(
    *,
    role: Literal["editor", "independent"],
    shot_id: str,
    character_ids: tuple[str, ...],
    scene_continuity_pass: bool | None,
) -> ReviewerAssessment:
    return ReviewerAssessment(
        reviewer_ref=f"fixture-{role}",
        review_record_sha256=hashlib.sha256(
            f"synthetic-fixture:{role}:{shot_id}".encode()
        ).hexdigest(),
        first_pass_usable=True,
        shot_intent_pass=True,
        artifact_free=True,
        character_continuity={character_id: True for character_id in character_ids},
        scene_continuity_pass=scene_continuity_pass,
        critical_identity_break=False,
    )


def _active_versions(
    spec: CreativeSampleSpec,
) -> dict[str, CharacterAssetVersion | SceneAssetVersion]:
    bibles: tuple[CharacterBible | SceneBible, ...] = (
        *spec.character_bibles,
        *spec.scene_bibles,
    )
    return {
        bible.active_asset_version_id: next(
            item for item in bible.asset_versions if item.id == bible.active_asset_version_id
        )
        for bible in bibles
    }


def _synthetic_manifest(
    *,
    spec: CreativeSampleSpec,
    pack: CreativeSamplePilotPack,
    input_root: Path,
) -> CreativeSampleImportManifest:
    compilation = compile_creative_sample(spec)
    active_versions = _active_versions(spec)
    asset_imports: list[AssetImport] = []
    for requirement in pack.asset_requirements:
        path = input_root.joinpath(*requirement.intended_logical_path.split("/"))
        digest, size_bytes = _byte_identity(path)
        assert digest == active_versions[requirement.asset_version_id].content_sha256
        asset_imports.append(
            AssetImport(
                asset_version_id=requirement.asset_version_id,
                logical_path=requirement.intended_logical_path,
                expected_sha256=digest,
                expected_size_bytes=size_bytes,
                source_kind="SYNTHETIC_FIXTURE",
            )
        )

    shot_imports: list[ShotImportReview] = []
    seen_scenes: set[str] = set()
    for shot in compilation.pir.shots:
        logical_path = f"shots/{shot.ordinal:02d}.mp4"
        digest, size_bytes = _byte_identity(input_root.joinpath(*logical_path.split("/")))
        first_in_scene = shot.scene_bible_id not in seen_scenes
        seen_scenes.add(shot.scene_bible_id)
        character_ids = tuple(sorted(item.character_id for item in shot.character_assets))
        shot_imports.append(
            ShotImportReview(
                shot_id=shot.id,
                logical_path=logical_path,
                expected_sha256=digest,
                expected_size_bytes=size_bytes,
                first_attempt_sha256=digest,
                approval_ref=f"synthetic-shot-{shot.ordinal:02d}",
                provenance_record_sha256=hashlib.sha256(
                    f"synthetic:{logical_path}".encode()
                ).hexdigest(),
                source_kind="SYNTHETIC_FIXTURE",
                attempts=1,
                editor_review=_review(
                    role="editor",
                    shot_id=shot.id,
                    character_ids=character_ids,
                    scene_continuity_pass=None if first_in_scene else True,
                ),
                independent_review=_review(
                    role="independent",
                    shot_id=shot.id,
                    character_ids=character_ids,
                    scene_continuity_pass=None if first_in_scene else True,
                ),
                cost_cny=Decimal("0"),
                failure_codes=(),
            )
        )

    voice_imports: list[VoiceImport] = []
    for ordinal, line in enumerate(spec.dialogue):
        logical_path = f"voices/{ordinal:02d}.wav"
        digest, size_bytes = _byte_identity(input_root.joinpath(*logical_path.split("/")))
        voice_imports.append(
            VoiceImport(
                line_id=line.line_id,
                logical_path=logical_path,
                expected_sha256=digest,
                expected_size_bytes=size_bytes,
                approval_ref=f"synthetic-voice-{ordinal:02d}",
                provenance_record_sha256=hashlib.sha256(
                    f"synthetic:{logical_path}".encode()
                ).hexdigest(),
                source_kind="SYNTHETIC_FIXTURE",
            )
        )

    bgm_logical_path = "bgm/background.wav"
    bgm_sha256, bgm_size = _byte_identity(input_root.joinpath(*bgm_logical_path.split("/")))
    return CreativeSampleImportManifest(
        sample_spec_sha256=hashlib.sha256(_canonical_contract_bytes(spec)).hexdigest(),
        assets=tuple(sorted(asset_imports, key=lambda item: item.asset_version_id)),
        shots=tuple(shot_imports),
        voices=tuple(voice_imports),
        bgm=BGMImport(
            logical_path=bgm_logical_path,
            expected_sha256=bgm_sha256,
            expected_size_bytes=bgm_size,
            approval_ref="synthetic-bgm",
            provenance_record_sha256=hashlib.sha256(
                f"synthetic:{bgm_logical_path}".encode()
            ).hexdigest(),
            source_kind="SYNTHETIC_FIXTURE",
        ),
        total_elapsed_ms=0,
        human_edit_minutes=Decimal("0"),
    )


@contextmanager
def _network_forbidden() -> Iterator[None]:
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo
    original_connect = socket.socket.connect

    def fail(*_: object, **__: object) -> None:
        raise AssertionError("Creative Pilot validation must not access the network")

    socket.create_connection = fail  # type: ignore[assignment]
    socket.getaddrinfo = fail  # type: ignore[assignment]
    socket.socket.connect = fail  # type: ignore[method-assign]
    try:
        yield
    finally:
        socket.create_connection = original_create_connection
        socket.getaddrinfo = original_getaddrinfo
        socket.socket.connect = original_connect  # type: ignore[method-assign]


def test_committed_pilot_pack_is_canonical_and_exactly_rebuilds() -> None:
    assert {item.name for item in COMMITTED_PACK_ROOT.iterdir()} == {
        "creative-sample-spec.json",
        "pilot-pack.json",
    }
    loaded = load_creative_sample_pilot_pack(COMMITTED_PACK_ROOT)
    expected_spec, expected_pack = build_creative_sample_pilot_documents()

    assert loaded.spec == expected_spec
    assert loaded.pack == expected_pack
    assert loaded.compilation == compile_creative_sample(expected_spec)
    assert loaded.pack.pack_id == "creative_pilot_pack_b1041dbe27fc145c73c8"
    assert loaded.compilation.id == "creative_sample_c43253e73fe962f1623d"
    expected_envelope = CreativeSamplePilotSpecDocument(spec=expected_spec)
    assert (COMMITTED_PACK_ROOT / "creative-sample-spec.json").read_bytes() == (
        _canonical_json_bytes(expected_envelope)
    )
    assert (COMMITTED_PACK_ROOT / "pilot-pack.json").read_bytes() == _canonical_json_bytes(
        expected_pack
    )


def test_frozen_story_has_exact_72_second_content_and_reference_closure() -> None:
    spec, pack = build_creative_sample_pilot_documents()
    compilation = compile_creative_sample(spec)

    assert spec.title == "辞职信照旧"
    assert spec.seed == 20260816
    assert spec.duration_ms == 72_000
    assert len(spec.character_bibles) == len(spec.scene_bibles) == 2
    assert len(spec.shots) == len(pack.shot_plans) == 10
    assert len(spec.dialogue) == 9
    assert tuple((item.start_ms, item.duration_ms) for item in spec.shots) == EXPECTED_CLOCK
    assert tuple((item.start_ms, item.end_ms) for item in spec.dialogue) == EXPECTED_DIALOGUE_CLOCK
    assert tuple(item.scene_id for item in spec.shots[:5]) == (spec.scene_bibles[0].scene_id,) * 5
    assert tuple(item.scene_id for item in spec.shots[5:]) == (spec.scene_bibles[1].scene_id,) * 5
    assert pack.ordered_shot_ids == tuple(item.id for item in compilation.pir.shots)
    assert pack.active_asset_version_ids == tuple(sorted(_active_versions(spec)))

    appearances = {
        character.character_id: sum(
            character.character_id in shot.character_ids for shot in spec.shots
        )
        for character in spec.character_bibles
    }
    assert sorted(appearances.values()) == [7, 10]
    assert all("成年" in character.visual_description for character in spec.character_bibles)
    assert all(
        {shot.scene_id for shot in spec.shots if character.character_id in shot.character_ids}
        == {item.scene_id for item in spec.scene_bibles}
        for character in spec.character_bibles
    )


def test_every_shot_freezes_complete_assets_audio_post_and_acceptance() -> None:
    spec, pack = build_creative_sample_pilot_documents()
    line_by_id = {item.line_id: item for item in spec.dialogue}
    scene_by_id = {item.scene_id: item for item in spec.scene_bibles}
    character_by_id = {item.character_id: item for item in spec.character_bibles}

    for source, plan in zip(spec.shots, pack.shot_plans, strict=True):
        expected_assets = {
            scene_by_id[source.scene_id].active_asset_version_id,
            *(character_by_id[item].active_asset_version_id for item in source.character_ids),
        }
        assert plan.ordinal == source.ordinal
        assert (plan.start_ms, plan.duration_ms) == (source.start_ms, source.duration_ms)
        assert plan.scene_id == source.scene_id
        assert plan.character_ids == source.character_ids
        assert plan.dialogue_line_ids == source.dialogue_line_ids
        assert plan.voice_line_ids == source.dialogue_line_ids
        assert plan.subtitle_text == tuple(
            line_by_id[item].text for item in source.dialogue_line_ids
        )
        assert set(plan.required_asset_version_ids) == expected_assets
        assert plan.visual_goal and plan.unacceptable_defects
        assert plan.bgm_direction and plan.post_requirements and plan.first_pass_criteria
        assert any("静态" in item or "纯色" in item for item in plan.unacceptable_defects) == (
            source.ordinal == 0
        )
        assert plan.scene_continuity_required is (source.ordinal not in {0, 5})


def test_asset_rights_reviews_metrics_and_failure_taxonomy_are_inert_templates() -> None:
    spec, pack = build_creative_sample_pilot_documents()
    assert len(pack.asset_requirements) == 4
    assert len(pack.audio_requirements) == 10
    assert len(pack.rights_review_rows) == 14
    assert tuple(item.asset_version_id for item in pack.asset_requirements) == (
        pack.active_asset_version_ids
    )
    expected_rights_keys = (
        *(("IMAGE_ASSET", item) for item in pack.active_asset_version_ids),
        *(
            (
                item.kind,
                item.line_id if item.kind == "VOICE" else item.requirement_id,
            )
            for item in pack.audio_requirements
        ),
    )
    assert (
        tuple((item.subject_kind, item.subject_id) for item in pack.rights_review_rows)
        == expected_rights_keys
    )
    assert all(
        item.source_mode == "SYNTHETIC_PLACEHOLDER_ONLY"
        and item.submission_status == "NOT_SUBMITTED"
        and item.rights_status == "PENDING_REVIEW"
        and item.privacy_status == "PENDING_REVIEW"
        and item.eligible_for_real_generation is False
        for item in pack.asset_requirements
    )
    assert all(
        row.submission_status == "NOT_SUBMITTED"
        and row.decision == "PENDING_REVIEW"
        and row.source_category is None
        and row.rights_basis is None
        and row.reviewer_a_ref is row.reviewer_b_ref is None
        and row.review_record_a_sha256 is row.review_record_b_sha256 is None
        and row.eligible_for_real_generation is False
        for row in pack.rights_review_rows
    )
    assert all(
        item.submission_status == "NOT_SUBMITTED"
        and item.rights_status == "PENDING_REVIEW"
        and item.expected_sha256 is None
        and item.expected_size_bytes is None
        and item.provenance_record_sha256 is None
        and item.eligible_for_real_generation is False
        for item in pack.audio_requirements
    )
    assert pack.metrics_template.status == "UNFILLED"
    assert pack.metrics_template.shot_count == 10
    assert pack.metrics_template.character_appearance_count == 17
    assert pack.metrics_template.scene_boundary_count == 8
    metrics = pack.metrics_template.model_dump()
    assert metrics["status"] == "UNFILLED"
    assert all(
        value is None
        for key, value in metrics.items()
        if key not in {"status", "shot_count", "character_appearance_count", "scene_boundary_count"}
    )
    assert {item.code for item in pack.failure_taxonomy} == EXPECTED_FAILURE_CODES
    assert tuple(item.code for item in pack.failure_taxonomy) == tuple(
        sorted(EXPECTED_FAILURE_CODES)
    )
    assert len(pack.shot_work_records) == 10
    assert tuple(item.shot_id for item in pack.shot_work_records) == pack.ordered_shot_ids
    assert all(
        item.status == "UNFILLED" and item.source_mode is None for item in pack.shot_work_records
    )
    assert len(spec.character_bibles) == 2


def test_two_reviewer_template_is_exact_ordered_and_unfilled() -> None:
    _, pack = build_creative_sample_pilot_documents()
    assert len(pack.shot_review_templates) == 20
    expected = tuple(
        (shot_id, role) for shot_id in pack.ordered_shot_ids for role in ("EDITOR", "INDEPENDENT")
    )
    assert tuple((item.shot_id, item.role) for item in pack.shot_review_templates) == expected
    for row in pack.shot_review_templates:
        assert row.status == "UNFILLED"
        assert row.reviewer_ref is row.media_sha256 is row.review_record_sha256 is None
        assert row.first_pass_usable is row.shot_intent_pass is row.artifact_free is None
        assert row.scene_continuity_pass is row.critical_identity_break is None
        assert row.failure_codes == () and row.notes is None
        assert {item.passed for item in row.character_continuity} == {None}
        assert tuple(item.character_id for item in row.character_continuity) == tuple(
            sorted(item.character_id for item in row.character_continuity)
        )
        assert row.scene_continuity_required is (
            row.shot_id
            not in {
                pack.ordered_shot_ids[0],
                pack.ordered_shot_ids[5],
            }
        )


def test_delivery_profile_is_exact_and_locally_assemblable() -> None:
    _, pack = build_creative_sample_pilot_documents()
    assert pack.delivery_profile.model_dump(mode="json") == {
        "width": 1080,
        "height": 1920,
        "display_aspect_ratio": "9:16",
        "fps": 25,
        "video_codec": "h264",
        "pixel_format": "yuv420p",
        "audio_codec": "aac",
        "audio_sample_rate_hz": 48000,
        "audio_channels": 2,
        "subtitle_codec": "mov_text",
        "container": "mp4",
    }


def test_pending_templates_can_validate_complete_future_local_records() -> None:
    _, pack = build_creative_sample_pilot_documents()
    digest_a = "a" * 64
    digest_b = "b" * 64
    digest_c = "c" * 64

    audio_model = type(pack.audio_requirements[0])
    audio_payload = pack.audio_requirements[0].model_dump(mode="python")
    audio_payload.update(
        submission_status="SUBMITTED",
        expected_sha256=digest_a,
        expected_size_bytes=123,
        provenance_record_sha256=digest_b,
        rights_status="APPROVED",
        eligible_for_real_generation=True,
    )
    completed_audio = audio_model.model_validate(audio_payload, strict=True)
    assert completed_audio.submission_status == "SUBMITTED"
    assert completed_audio.eligible_for_real_generation is True

    rights_model = type(pack.rights_review_rows[0])
    rights_payload = pack.rights_review_rows[0].model_dump(mode="python")
    rights_payload.update(
        submission_status="SUBMITTED",
        expected_sha256=digest_a,
        expected_size_bytes=456,
        provenance_record_sha256=digest_b,
        source_category="locally-retained-license",
        rights_basis="written production license",
        territory="worldwide",
        use_scope="short-drama sample evaluation",
        likeness_privacy_basis="fictional adult; no private likeness",
        reviewer_a_ref="rights-reviewer-a",
        reviewer_b_ref="rights-reviewer-b",
        review_record_a_sha256=digest_b,
        review_record_b_sha256=digest_c,
        decision="APPROVED",
        eligible_for_real_generation=True,
    )
    completed_rights = rights_model.model_validate(rights_payload, strict=True)
    assert completed_rights.decision == "APPROVED"
    assert completed_rights.eligible_for_real_generation is True

    review_model = type(pack.shot_review_templates[0])
    review_payload = pack.shot_review_templates[0].model_dump(mode="python")
    review_payload.update(
        status="COMPLETED",
        reviewer_ref="editor-a",
        media_sha256=digest_a,
        review_record_sha256=digest_b,
        first_pass_usable=True,
        shot_intent_pass=True,
        artifact_free=True,
        character_continuity=tuple(
            {**item, "passed": True} for item in review_payload["character_continuity"]
        ),
        scene_continuity_pass=(True if review_payload["scene_continuity_required"] else None),
        critical_identity_break=False,
        notes="Exact local review record retained separately.",
        human_review_ms=12_000,
        human_edit_ms=0,
    )
    completed_review = review_model.model_validate(review_payload, strict=True)
    assert completed_review.status == "COMPLETED"
    assert all(item.passed is True for item in completed_review.character_continuity)

    work_model = type(pack.shot_work_records[0])
    work_payload = pack.shot_work_records[0].model_dump(mode="python")
    work_payload.update(
        status="COMPLETED",
        source_mode="IMPORTED_MEDIA",
        attempts=1,
        first_attempt_sha256=digest_a,
        final_media_sha256=digest_a,
        provider_request_count=0,
        provider_cost_cny_microunits=0,
        human_edit_ms=0,
    )
    completed_work = work_model.model_validate(work_payload, strict=True)
    assert completed_work.status == "COMPLETED"
    assert completed_work.source_mode == "IMPORTED_MEDIA"
    assert completed_work.provider_request_count == 0

    metrics_model = type(pack.metrics_template)
    metrics_payload = pack.metrics_template.model_dump(mode="python")
    metrics_payload.update(
        status="COMPLETED",
        first_pass_usable_count=8,
        character_continuity_pass_count=16,
        scene_continuity_pass_count=8,
        shot_intent_pass_count=8,
        artifact_free_count=9,
        critical_identity_breaks=0,
        duplicate_media_count=0,
        total_attempts=10,
        total_elapsed_ms=300_000,
        human_review_ms=120_000,
        human_edit_ms=30_000,
        cost_cny_microunits=0,
        failure_counts=({"code": "content.scene_drift", "count": 0},),
    )
    completed_metrics = metrics_model.model_validate(metrics_payload, strict=True)
    assert completed_metrics.status == "COMPLETED"
    assert completed_metrics.first_pass_usable_count == 8

    partial_rights = dict(rights_payload, review_record_b_sha256=None)
    with pytest.raises(ValidationError, match="complete evidence"):
        rights_model.model_validate(partial_rights, strict=True)
    unfilled_with_score = pack.shot_review_templates[0].model_dump(mode="python")
    unfilled_with_score["first_pass_usable"] = True
    with pytest.raises(ValidationError, match="unfilled shot review"):
        review_model.model_validate(unfilled_with_score, strict=True)


def _completed_rights_payload(pack: CreativeSamplePilotPack) -> dict[str, object]:
    payload = pack.rights_review_rows[0].model_dump(mode="python")
    payload.update(
        submission_status="SUBMITTED",
        expected_sha256="a" * 64,
        expected_size_bytes=456,
        provenance_record_sha256="b" * 64,
        source_category="locally-retained-license",
        rights_basis="written production license",
        territory="worldwide",
        use_scope="short-drama sample evaluation",
        likeness_privacy_basis="fictional adult; no private likeness",
        reviewer_a_ref="rights-reviewer-a",
        reviewer_b_ref="rights-reviewer-b",
        review_record_a_sha256="b" * 64,
        review_record_b_sha256="c" * 64,
        decision="APPROVED",
        eligible_for_real_generation=True,
    )
    return payload


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("source_category", ""),
        ("rights_basis", " "),
        ("territory", " worldwide"),
        ("use_scope", "sample evaluation "),
        ("likeness_privacy_basis", "fictional\n adult"),
        ("source_category", "e\u0301vidence"),
    ],
)
def test_submitted_rights_reject_empty_noncanonical_or_control_text(
    field: str,
    invalid_value: str,
) -> None:
    _, pack = build_creative_sample_pilot_documents()
    model = type(pack.rights_review_rows[0])
    payload = _completed_rights_payload(pack)
    payload[field] = invalid_value
    with pytest.raises(ValidationError, match="rights evidence"):
        model.model_validate(payload, strict=True)


@pytest.mark.parametrize("expiry", ["2027-12-31", "2027-12-31T23:59:59Z"])
def test_submitted_rights_accept_only_canonical_optional_expiry(expiry: str) -> None:
    _, pack = build_creative_sample_pilot_documents()
    model = type(pack.rights_review_rows[0])
    payload = _completed_rights_payload(pack)
    payload["expiry"] = expiry
    assert model.model_validate(payload, strict=True).expiry == expiry


@pytest.mark.parametrize(
    "expiry",
    [
        "",
        "2027-1-1",
        "2020-W01-1",
        "2027-02-30",
        "2027-12-31T23:59:59+00:00",
        "2027-12-31T23:59:59.000Z",
    ],
)
def test_submitted_rights_reject_noncanonical_or_invalid_expiry(expiry: str) -> None:
    _, pack = build_creative_sample_pilot_documents()
    model = type(pack.rights_review_rows[0])
    payload = _completed_rights_payload(pack)
    payload["expiry"] = expiry
    with pytest.raises(ValidationError, match="canonical date or UTC second"):
        model.model_validate(payload, strict=True)


def test_submitted_rights_require_independently_hashed_review_records() -> None:
    _, pack = build_creative_sample_pilot_documents()
    model = type(pack.rights_review_rows[0])
    payload = _completed_rights_payload(pack)
    payload["review_record_b_sha256"] = payload["review_record_a_sha256"]
    with pytest.raises(ValidationError, match="independently hashed"):
        model.model_validate(payload, strict=True)


def test_first_pass_usable_rejects_any_failed_applicable_review_gate() -> None:
    _, pack = build_creative_sample_pilot_documents()
    template = next(item for item in pack.shot_review_templates if item.scene_continuity_required)
    model = type(template)
    payload = template.model_dump(mode="python")
    payload.update(
        status="COMPLETED",
        reviewer_ref="independent-a",
        media_sha256="a" * 64,
        review_record_sha256="b" * 64,
        first_pass_usable=True,
        shot_intent_pass=True,
        artifact_free=True,
        character_continuity=tuple(
            {**item, "passed": True} for item in payload["character_continuity"]
        ),
        scene_continuity_pass=True,
        critical_identity_break=False,
        notes="All applicable review gates passed.",
        human_review_ms=10_000,
        human_edit_ms=0,
    )
    assert model.model_validate(payload, strict=True).first_pass_usable is True

    for field, failed_value in (
        ("shot_intent_pass", False),
        ("artifact_free", False),
        ("scene_continuity_pass", False),
        ("critical_identity_break", True),
    ):
        failed = copy.deepcopy(payload)
        failed[field] = failed_value
        with pytest.raises(ValidationError, match="every applicable review gate"):
            model.model_validate(failed, strict=True)

    failed_character = copy.deepcopy(payload)
    character_rows = cast(tuple[dict[str, object], ...], failed_character["character_continuity"])
    character_rows[0]["passed"] = False
    with pytest.raises(ValidationError, match="every applicable review gate"):
        model.model_validate(failed_character, strict=True)


def test_completed_shot_work_rejects_attempt_digest_and_request_count_drift() -> None:
    _, pack = build_creative_sample_pilot_documents()
    model = type(pack.shot_work_records[0])
    valid = pack.shot_work_records[0].model_dump(mode="python")
    valid.update(
        status="COMPLETED",
        source_mode="PROVIDER_GENERATED",
        attempts=1,
        first_attempt_sha256="a" * 64,
        final_media_sha256="a" * 64,
        provider_request_count=1,
        provider_cost_cny_microunits=0,
        human_edit_ms=0,
    )
    assert model.model_validate(valid, strict=True).attempts == 1

    imported = dict(
        valid,
        source_mode="IMPORTED_MEDIA",
        provider_request_count=0,
        provider_cost_cny_microunits=0,
    )
    admitted_import = model.model_validate(imported, strict=True)
    assert admitted_import.source_mode == "IMPORTED_MEDIA"
    assert admitted_import.provider_request_count == 0

    missing_source = dict(valid, source_mode=None)
    with pytest.raises(ValidationError, match="require all time, cost and attempt values"):
        model.model_validate(missing_source, strict=True)

    for field in ("provider_request_count", "provider_cost_cny_microunits"):
        imported_drift = dict(imported)
        imported_drift[field] = 1
        with pytest.raises(ValidationError, match="imported media must record zero"):
            model.model_validate(imported_drift, strict=True)

    attempt_one_drift = dict(valid, final_media_sha256="b" * 64)
    with pytest.raises(ValidationError, match="Attempt 1 reuses"):
        model.model_validate(attempt_one_drift, strict=True)

    attempt_two_same_digest = dict(valid, attempts=2, provider_request_count=2)
    with pytest.raises(ValidationError, match="Attempt 1 reuses"):
        model.model_validate(attempt_two_same_digest, strict=True)

    request_count_drift = dict(valid, provider_request_count=0)
    with pytest.raises(ValidationError, match="request count"):
        model.model_validate(request_count_drift, strict=True)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../asset.png",
        "C:/asset.png",
        "assets\\asset.png",
        "assets/a?.png",
        "assets/con.png",
        "assets/trailing. ",
        "assets/control\x01.png",
    ],
)
def test_pilot_logical_paths_are_strictly_portable(unsafe_path: str) -> None:
    _, pack = build_creative_sample_pilot_documents()
    model = type(pack.asset_requirements[0])
    payload = pack.asset_requirements[0].model_dump(mode="python")
    payload["intended_logical_path"] = unsafe_path
    with pytest.raises(ValidationError, match="logical path"):
        model.model_validate(payload, strict=True)


def test_fixture_spec_envelope_cannot_be_parsed_as_a_real_base_spec(tmp_path: Path) -> None:
    raw = (COMMITTED_PACK_ROOT / "creative-sample-spec.json").read_bytes()
    envelope = CreativeSamplePilotSpecDocument.model_validate_json(raw, strict=True)
    assert envelope.source_mode == "SYNTHETIC_PLACEHOLDER_ONLY"
    assert envelope.fixture_admission_scope == "TECHNICAL_COMPILATION_ONLY"
    assert envelope.eligible_for_real_generation is False
    bibles: tuple[CharacterBible | SceneBible, ...] = (
        *envelope.spec.character_bibles,
        *envelope.spec.scene_bibles,
    )
    assert all(
        version.approval_ref.startswith("pilot-fixture-only-")
        for bible in bibles
        for version in bible.asset_versions
    )
    with pytest.raises(ValidationError):
        CreativeSampleSpec.model_validate_json(raw, strict=True)

    bare_root = _copy_pack(tmp_path / "bare")
    _write_canonical(bare_root / "creative-sample-spec.json", envelope.spec)
    with pytest.raises(CreativePilotError):
        load_creative_sample_pilot_pack(bare_root)

    relabelled_root = _copy_pack(tmp_path / "relabelled")
    payload = cast(dict[str, object], json.loads(raw))
    payload["source_mode"] = "IMPORTED_MEDIA"
    _write_canonical(relabelled_root / "creative-sample-spec.json", payload)
    with pytest.raises(CreativePilotError):
        load_creative_sample_pilot_pack(relabelled_root)


def test_future_batch_is_finite_but_presently_grants_zero_authority() -> None:
    _, pack = build_creative_sample_pilot_documents()
    batch = pack.provider_batch_plan

    assert batch.state == "NOT_AUTHORIZED"
    assert batch.posts_allowed == 0
    assert batch.current_gate == "HUMAN_GATE"
    assert batch.exact_shot_ids == pack.ordered_shot_ids
    assert batch.max_attempts_per_shot == 2
    assert batch.planned_max_video_requests == 20
    assert batch.planned_voice_requests == batch.planned_image_requests == 0
    assert batch.proposed_cost_ceiling_cny == 450
    rendered_stops = " ".join(batch.stop_conditions)
    for required in (
        "20",
        "CNY450",
        "Attempt 2",
        "SUBMISSION_UNKNOWN",
        "HUMAN_GATE",
        "task ID",
        "复核",
        "版权",
        "技术闭包",
    ):
        assert required in rendered_stops
    forbidden_authority_fields = {
        "authorization_id",
        "entitlement_id",
        "nonce",
        "credential_locator",
        "key_locator",
        "account_id",
        "request_fingerprints",
    }
    assert forbidden_authority_fields.isdisjoint(batch.model_fields_set)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("state", "AUTHORIZED"),
        ("posts_allowed", 1),
        ("max_attempts_per_shot", 3),
        ("planned_max_video_requests", 21),
        ("proposed_cost_ceiling_cny", 451),
        ("current_gate", "RUNNING"),
    ],
)
def test_future_batch_rejects_authority_or_ceiling_drift(field: str, value: object) -> None:
    _, pack = build_creative_sample_pilot_documents()
    payload = pack.provider_batch_plan.model_dump(mode="python")
    payload[field] = value
    model = type(pack.provider_batch_plan)
    with pytest.raises(ValidationError):
        model.model_validate(payload, strict=True)


def test_synthetic_declaration_is_permanently_not_scored_and_zero_request() -> None:
    _, pack = build_creative_sample_pilot_documents()
    rehearsal = pack.synthetic_rehearsal
    assert rehearsal.source_mode == "SYNTHETIC_FIXTURE"
    assert rehearsal.expected_decision == "STOP"
    assert rehearsal.human_status == "NOT_SCORED"
    assert rehearsal.metric_status == "NOT_SCORED_FIXTURE"
    assert rehearsal.provider_requests == rehearsal.posts_allowed == 0
    assert rehearsal.proves_content_quality is rehearsal.proves_provider_readiness is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update(pack_id="creative_pilot_pack_" + "0" * 20),
        lambda payload: payload.update(sample_spec_sha256="0" * 64),
        lambda payload: cast(list[object], payload["ordered_shot_ids"]).reverse(),
        lambda payload: cast(list[object], payload["rights_review_rows"]).pop(),
        lambda payload: cast(list[object], payload["shot_review_templates"]).pop(),
        lambda payload: cast(list[object], payload["failure_taxonomy"]).pop(),
    ],
)
def test_canonical_pack_id_and_exact_cross_file_closure_fail_closed(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], object],
) -> None:
    root = _copy_pack(tmp_path)
    pack_path = root / "pilot-pack.json"
    payload = cast(dict[str, object], json.loads(pack_path.read_text(encoding="utf-8")))
    mutation(payload)
    if payload.get("sample_spec_sha256") == "0" * 64:
        _resign_pack(payload)
    _write_canonical(pack_path, payload)

    with pytest.raises(CreativePilotError):
        load_creative_sample_pilot_pack(root)


def test_semantically_self_consistent_shot_reorder_still_fails_golden_binding(
    tmp_path: Path,
) -> None:
    root = _copy_pack(tmp_path)
    pack_path = root / "pilot-pack.json"
    payload = cast(dict[str, object], json.loads(pack_path.read_text(encoding="utf-8")))
    ordered = cast(list[str], payload["ordered_shot_ids"])
    ordered[0], ordered[1] = ordered[1], ordered[0]
    plans = cast(list[dict[str, object]], payload["shot_plans"])
    plans[0], plans[1] = plans[1], plans[0]
    reviews = cast(list[dict[str, object]], payload["shot_review_templates"])
    reviews[0:4] = reviews[2:4] + reviews[0:2]
    cast(dict[str, object], payload["provider_batch_plan"])["exact_shot_ids"] = list(ordered)
    _resign_pack(payload)
    _write_canonical(pack_path, payload)

    with pytest.raises(CreativePilotError):
        load_creative_sample_pilot_pack(root)


@pytest.mark.parametrize(
    ("name", "raw"),
    [
        ("duplicate", b'{"schema_version":"1.0.0","schema_version":"1.0.0"}\n'),
        ("nan", b'{"value":NaN}\n'),
        ("infinity", b'{"value":Infinity}\n'),
        ("invalid-utf8", b"\xff\xfe"),
        ("bom", b"\xef\xbb\xbf{}\n"),
        ("array", b"[]\n"),
    ],
)
def test_strict_loader_rejects_ambiguous_or_non_object_json(
    tmp_path: Path,
    name: str,
    raw: bytes,
) -> None:
    root = _copy_pack(tmp_path)
    (root / "pilot-pack.json").write_bytes(raw)
    with pytest.raises(CreativePilotError, match="JSON|duplicate|finite|BOM|object"):
        load_creative_sample_pilot_pack(root)


def test_strict_loader_rejects_extra_coerced_noncanonical_and_oversize_json(
    tmp_path: Path,
) -> None:
    mutators: Mapping[str, Callable[[Path], object]] = {
        "extra": lambda path: _mutate_json(path, lambda value: value.update(extra="forbidden")),
        "coerced": lambda path: _mutate_json(
            path,
            lambda value: cast(dict[str, object], value["provider_batch_plan"]).update(
                proposed_cost_ceiling_cny="450"
            ),
        ),
        "noncanonical": lambda path: path.write_text(
            json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False),
            encoding="utf-8",
        ),
        "oversize": lambda path: path.write_bytes(b"{" + b" " * (1024 * 1024) + b"}"),
    }
    for name, mutate in mutators.items():
        root = _copy_pack(tmp_path / name)
        target = root / "pilot-pack.json"
        mutate(target)
        with pytest.raises(CreativePilotError):
            load_creative_sample_pilot_pack(root)


def _mutate_json(path: Path, mutation: Callable[[dict[str, object]], object]) -> None:
    payload = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    mutation(payload)
    _write_canonical(path, payload)


def test_loader_rejects_missing_extra_linked_and_hardlinked_members(tmp_path: Path) -> None:
    missing = _copy_pack(tmp_path / "missing")
    (missing / "pilot-pack.json").unlink()
    with pytest.raises(CreativePilotError, match="exact two-file closure"):
        load_creative_sample_pilot_pack(missing)

    extra = _copy_pack(tmp_path / "extra")
    (extra / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(CreativePilotError, match="exact two-file closure"):
        load_creative_sample_pilot_pack(extra)

    linked = _copy_pack(tmp_path / "linked")
    original = linked / "pilot-pack.json"
    target = linked / "real-pack.json"
    original.rename(target)
    try:
        original.symlink_to(target.name)
    except OSError:
        pytest.skip("symbolic links are unavailable on this host")
    (linked / "real-pack.json").unlink()
    with pytest.raises(CreativePilotError):
        load_creative_sample_pilot_pack(linked)

    hardlinked = _copy_pack(tmp_path / "hardlinked")
    source = hardlinked / "pilot-pack.json"
    outside = tmp_path / "outside-pack.json"
    try:
        os.link(source, outside)
    except OSError:
        pytest.skip("hard links are unavailable on this host")
    with pytest.raises(CreativePilotError, match="hard link"):
        load_creative_sample_pilot_pack(hardlinked)


def test_writer_is_no_overwrite_and_cleans_failed_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "published"
    written = write_creative_sample_pilot_documents(destination)
    assert written.root == destination.absolute()
    with pytest.raises(CreativePilotError, match="new directory"):
        write_creative_sample_pilot_documents(destination)

    failed = tmp_path / "failed"
    original_load = creative_pilot_module.load_creative_sample_pilot_pack

    def fail_stage(root: Path) -> object:
        if root.name == ".failed.stage":
            raise CreativePilotError("forced verification failure")
        return original_load(root)

    monkeypatch.setattr(creative_pilot_module, "load_creative_sample_pilot_pack", fail_stage)
    with pytest.raises(CreativePilotError, match="forced verification failure"):
        write_creative_sample_pilot_documents(failed)
    assert not failed.exists()
    assert not (tmp_path / ".failed.stage").exists()


def test_pilot_build_and_load_have_no_network_or_secret_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel = "must-never-leave-process-pilot-secret"
    monkeypatch.setenv("SDC_PILOT_SENTINEL", sentinel)
    destination = tmp_path / "offline-pack"
    with _network_forbidden():
        build_creative_sample_pilot_documents()
        loaded = write_creative_sample_pilot_documents(destination)
        assert load_creative_sample_pilot_pack(destination) == loaded
    assert all(sentinel.encode() not in path.read_bytes() for path in destination.iterdir())


def test_pilot_module_has_no_network_runtime_key_or_authority_dependency() -> None:
    source = inspect.getsource(creative_pilot_module)
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.partition(".")[0] for alias in node.names)
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.partition(".")[0])
            imported_modules.add(node.module)
    assert imported_roots.isdisjoint(
        {"aiohttp", "boto3", "httpx", "requests", "socket", "temporalio", "urllib"}
    )
    assert imported_modules.isdisjoint(
        {
            "sdc.ark_provider",
            "sdc.ark_entitlement",
            "sdc.canary",
            "sdc.evidence_authorization",
            "sdc.evidence_ledger",
            "sdc.persistence",
            "sdc.provider",
            "sdc.runtime",
            "sdc.worker",
            "sdc.workflow",
        }
    )
    assert "os.environ[" not in source
    assert "os.environ.get" not in source
    assert "getenv(" not in source
    assert REVIEWED_ARK_ENTITLEMENT_EVIDENCE == ()
    assert REVIEWED_EVIDENCE_AUTHORIZATIONS == ()


@pytest.fixture(scope="module")
def synthetic_pilot_result(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    if not FFMPEG_AVAILABLE:
        pytest.skip("ffmpeg and ffprobe are required for the 72-second Pilot rehearsal")
    root = tmp_path_factory.mktemp("p")
    input_root = root / "i"
    input_root.mkdir()
    spec, pack = build_creative_sample_pilot_documents()
    spec_path = input_root / "sample-spec.json"
    _write_canonical(spec_path, spec)

    templates: dict[int, Path] = {}
    for duration_ms in {item.duration_ms for item in spec.shots}:
        template = root / f"dynamic-{duration_ms}.mp4"
        _ffmpeg(
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=160x90:rate=8:duration={duration_ms / 1000:g}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(template),
        )
        templates[duration_ms] = template
    for shot in spec.shots:
        target = input_root / "shots" / f"{shot.ordinal:02d}.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(templates[shot.duration_ms], target)

    voice_template = root / "voice.wav"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=48000:duration=1",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(voice_template),
    )
    for ordinal in range(len(spec.dialogue)):
        target = input_root / "voices" / f"{ordinal:02d}.wav"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(voice_template, target)

    bgm = input_root / "bgm" / "background.wav"
    bgm.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=220:sample_rate=48000:duration=1",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(bgm),
    )
    for requirement in pack.asset_requirements:
        target = input_root.joinpath(*requirement.intended_logical_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(synthetic_placeholder_png_bytes(requirement.placeholder_label))

    manifest = _synthetic_manifest(spec=spec, pack=pack, input_root=input_root)
    manifest_path = input_root / "import-manifest.json"
    _write_canonical(manifest_path, manifest)
    output_root = root / "o"
    secret = "pilot-e2e-secret-must-not-propagate"
    prior_secret = os.environ.get("SDC_PILOT_SENTINEL")
    os.environ["SDC_PILOT_SENTINEL"] = secret
    try:
        with asyncio.Runner() as runner:
            with _network_forbidden():
                result = runner.run(
                    run_creative_sample(
                        spec_path=spec_path,
                        import_manifest_path=manifest_path,
                        output_root=output_root,
                    )
                )
                report = verify_creative_sample_output(output_root)
    finally:
        if prior_secret is None:
            os.environ.pop("SDC_PILOT_SENTINEL", None)
        else:
            os.environ["SDC_PILOT_SENTINEL"] = prior_secret
    return {
        "result": result,
        "report": report,
        "root": output_root,
        "spec": spec,
        "pack": pack,
        "secret": secret,
    }


def test_real_ffmpeg_exact_72_second_pilot_fixture_is_technical_only(
    synthetic_pilot_result: dict[str, object],
) -> None:
    result = cast(CreativeSampleRunResult, synthetic_pilot_result["result"])
    report = cast(dict[str, object], synthetic_pilot_result["report"])
    output_root = cast(Path, synthetic_pilot_result["root"])
    spec = cast(CreativeSampleSpec, synthetic_pilot_result["spec"])
    pack = cast(CreativeSamplePilotPack, synthetic_pilot_result["pack"])
    secret = cast(str, synthetic_pilot_result["secret"])

    assert spec.duration_ms == 72_000
    assert len(spec.shots) == 10
    assert result.decision is CreativeSampleDecision.STOP
    assert report["decision"] == pack.synthetic_rehearsal.expected_decision == "STOP"
    assert report["provider_requests"] == pack.synthetic_rehearsal.provider_requests == 0
    assert report["live_authority"] is False
    assert report["metrics"] == {"status": "SYNTHETIC_FIXTURE_NOT_SCORED"}
    counts = cast(dict[str, object], report["metric_counts"])
    assert counts["status"] == "NOT_SCORED_FIXTURE"
    assert len(cast(list[object], report["imported_shots"])) == 10
    assert len(cast(list[object], report["imported_voices"])) == 9
    assert all(
        item["source_kind"] == "SYNTHETIC_FIXTURE"
        for item in cast(list[dict[str, object]], report["imported_shots"])
    )
    assert all(
        item["source_kind"] == "SYNTHETIC_FIXTURE"
        for item in cast(list[dict[str, object]], report["imported_voices"])
    )
    assert cast(dict[str, object], report["imported_bgm"])["source_kind"] == ("SYNTHETIC_FIXTURE")
    technical = json.loads((output_root / "creative-technical-qc.json").read_text("utf-8"))
    receipt = json.loads((output_root / "assembly-receipt.json").read_text("utf-8"))
    assert technical["passed"] is True
    assert len(receipt["ordered_shots"]) == 10
    assert receipt["ffmpeg_policy"]["width"] == 1080
    assert receipt["ffmpeg_policy"]["height"] == 1920
    assert receipt["ffmpeg_policy"]["fps"] == 25
    assert receipt["ffmpeg_policy"]["audio_rate"] == 48000
    assert receipt["ffmpeg_policy"]["network_protocols"] == []
    assert verify_creative_sample_output(output_root) == report
    for name in (
        "sample-report.json",
        "metrics.json",
        "creative-technical-qc.json",
        "assembly-receipt.json",
        "import-evidence.json",
    ):
        assert secret not in (output_root / name).read_text("utf-8")
