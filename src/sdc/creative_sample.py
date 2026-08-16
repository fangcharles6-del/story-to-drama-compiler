"""Repeatable, offline ImportedMedia creative-sample loop."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import stat
from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sdc.asset_pack import LocalAssetSource, freeze_asset_pack, verify_asset_pack
from sdc.compiler import compile_creative_sample, stable_id
from sdc.contracts import (
    CharacterAssetVersion,
    CreativeSampleCompilation,
    CreativeSampleDecision,
    CreativeSampleMetrics,
    CreativeSampleSpec,
    ReleaseManifest,
    SceneAssetVersion,
    StoryboardShotV2,
)
from sdc.creative_media import (
    CreativeMediaError,
    MediaToolchain,
    TimedVoiceTrack,
    assemble_sample,
    inspect_imported_audio,
    inspect_imported_video,
    read_regular_media,
    render_audio_master,
    render_srt,
    resolve_media_toolchain,
    validate_local_path,
    validate_regular_media_path,
    verify_assembled_sample,
    verify_media_toolchain,
)
from sdc.media import manifest as release_manifest

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_PORTABLE_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_JSON_LIMIT = 1024 * 1024


class CreativeSampleError(CreativeMediaError):
    pass


class _ImportModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _logical_path(value: str) -> str:
    if not value or len(value) > 512 or "\\" in value:
        raise ValueError("import path must be a bounded portable relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ValueError("import path must be canonical and relative")
    if any(part in {"", ".", ".."} or part.rstrip(" .") != part for part in path.parts):
        raise ValueError("import path contains an unsafe component")
    return value


class AssetImport(_ImportModel):
    asset_version_id: str = Field(pattern=_PORTABLE_ID)
    logical_path: str
    expected_sha256: str = Field(pattern=_LOWER_SHA256)
    expected_size_bytes: Annotated[int, Field(gt=0)]
    source_kind: Literal["IMPORTED_MEDIA", "SYNTHETIC_FIXTURE"] = "IMPORTED_MEDIA"

    @field_validator("logical_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _logical_path(value)


class VoiceImport(_ImportModel):
    line_id: str = Field(pattern=_PORTABLE_ID)
    logical_path: str
    expected_sha256: str = Field(pattern=_LOWER_SHA256)
    expected_size_bytes: Annotated[int, Field(gt=0)]
    media_type: Literal["audio/wav"] = "audio/wav"
    approval_ref: str = Field(pattern=_PORTABLE_ID)
    provenance_record_sha256: str = Field(pattern=_LOWER_SHA256)
    source_kind: Literal["IMPORTED_MEDIA", "SYNTHETIC_FIXTURE"] = "IMPORTED_MEDIA"

    @field_validator("logical_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _logical_path(value)


class BGMImport(_ImportModel):
    logical_path: str
    expected_sha256: str = Field(pattern=_LOWER_SHA256)
    expected_size_bytes: Annotated[int, Field(gt=0)]
    media_type: Literal["audio/wav"] = "audio/wav"
    approval_ref: str = Field(pattern=_PORTABLE_ID)
    provenance_record_sha256: str = Field(pattern=_LOWER_SHA256)
    source_kind: Literal["IMPORTED_MEDIA", "SYNTHETIC_FIXTURE"] = "IMPORTED_MEDIA"

    @field_validator("logical_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _logical_path(value)


class ReviewerAssessment(_ImportModel):
    reviewer_ref: str = Field(pattern=_PORTABLE_ID)
    review_record_sha256: str = Field(pattern=_LOWER_SHA256)
    first_pass_usable: bool
    shot_intent_pass: bool
    artifact_free: bool
    character_continuity: dict[str, bool]
    scene_continuity_pass: bool | None
    critical_identity_break: bool = False


class ShotImportReview(_ImportModel):
    shot_id: str = Field(min_length=1, max_length=128)
    logical_path: str
    expected_sha256: str = Field(pattern=_LOWER_SHA256)
    expected_size_bytes: Annotated[int, Field(gt=0)]
    media_type: Literal["video/mp4"] = "video/mp4"
    first_attempt_sha256: str = Field(pattern=_LOWER_SHA256)
    approval_ref: str = Field(pattern=_PORTABLE_ID)
    provenance_record_sha256: str = Field(pattern=_LOWER_SHA256)
    source_kind: Literal["IMPORTED_MEDIA", "SYNTHETIC_FIXTURE"] = "IMPORTED_MEDIA"
    attempts: Annotated[int, Field(ge=1, le=2)]
    editor_review: ReviewerAssessment
    independent_review: ReviewerAssessment
    cost_cny: Annotated[Decimal, Field(ge=0)]
    failure_codes: tuple[str, ...] = ()

    @field_validator("logical_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _logical_path(value)

    @field_validator("failure_codes")
    @classmethod
    def validate_failure_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))):
            raise ValueError("failure codes must be unique and sorted")
        if any(
            not item
            or len(item) > 64
            or item[0] not in "abcdefghijklmnopqrstuvwxyz"
            or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in item)
            for item in value
        ):
            raise ValueError("failure codes must use canonical lowercase identifiers")
        return value

    @model_validator(mode="after")
    def validate_first_pass_and_reviews(self) -> ShotImportReview:
        if self.editor_review.reviewer_ref == self.independent_review.reviewer_ref:
            raise ValueError("editor and independent reviewer references must be distinct")
        if self.attempts == 1 and self.first_attempt_sha256 != self.expected_sha256:
            raise ValueError("Attempt 1 must bind the admitted first-pass digest")
        if self.attempts == 2:
            if self.first_attempt_sha256 == self.expected_sha256:
                raise ValueError("Attempt 2 must retain a distinct first-attempt digest")
            if self.editor_review.first_pass_usable or self.independent_review.first_pass_usable:
                raise ValueError("a replacement shot cannot be reported as first-pass usable")
        return self


class CreativeSampleImportManifest(_ImportModel):
    document_type: Literal["sdc.creative-sample-import-manifest"] = (
        "sdc.creative-sample-import-manifest"
    )
    sample_spec_sha256: str = Field(pattern=_LOWER_SHA256)
    revision_number: Annotated[int, Field(ge=1)] = 1
    predecessor_manifest_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    assets: tuple[AssetImport, ...]
    shots: tuple[ShotImportReview, ...] = Field(min_length=8, max_length=12)
    voices: tuple[VoiceImport, ...] = Field(min_length=1)
    bgm: BGMImport | None = None
    total_elapsed_ms: Annotated[int, Field(ge=0)]
    human_edit_minutes: Annotated[Decimal, Field(ge=0)]

    @model_validator(mode="after")
    def validate_revision_and_source_mode(self) -> CreativeSampleImportManifest:
        if (self.revision_number == 1) != (self.predecessor_manifest_sha256 is None):
            raise ValueError("only revision 1 may omit its predecessor manifest digest")
        source_kinds = {
            *(item.source_kind for item in self.assets),
            *(item.source_kind for item in self.shots),
            *(item.source_kind for item in self.voices),
            *(() if self.bgm is None else (self.bgm.source_kind,)),
        }
        if len(source_kinds) != 1:
            raise ValueError("a sample revision cannot mix ImportedMedia with synthetic fixtures")
        return self


@dataclass(frozen=True, slots=True)
class CreativeSampleRunResult:
    sample_id: str
    revision_id: str
    decision: CreativeSampleDecision
    output_root: Path
    final_media: Path
    report_path: Path


def _reject_constant(value: str) -> None:
    raise CreativeSampleError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CreativeSampleError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _load_json(path: Path, model: type[BaseModel]) -> BaseModel:
    data, _ = read_regular_media(path)
    if len(data) > _JSON_LIMIT:
        raise CreativeSampleError("creative sample JSON exceeds the 1 MiB limit")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CreativeSampleError("creative sample JSON must be strict UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise CreativeSampleError("creative sample JSON is malformed") from exc
    return model.model_validate(value)


def _load_json_object(path: Path) -> dict[str, object]:
    data, _ = read_regular_media(path)
    if len(data) > _JSON_LIMIT:
        raise CreativeSampleError("creative sample JSON exceeds the 1 MiB limit")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeSampleError("creative sample JSON is malformed") from exc
    if not isinstance(value, dict):
        raise CreativeSampleError("creative sample JSON must contain an object")
    return value


def _write_bytes_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise CreativeSampleError(f"creative sample output already exists: {path}") from exc


def _write_json_new(path: Path, value: object) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    _write_bytes_new(
        path,
        (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"),
    )


def _canonical_model_bytes(value: BaseModel) -> bytes:
    return json.dumps(
        value.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _freeze_declared_file(
    source: Path,
    target: Path,
    *,
    expected_sha256: str,
    expected_size_bytes: int,
) -> Path:
    data, _ = read_regular_media(source)
    if len(data) != expected_size_bytes or hashlib.sha256(data).hexdigest() != expected_sha256:
        raise CreativeSampleError("imported media does not match its declared byte identity")
    _write_bytes_new(target, data)
    confirmed, _ = read_regular_media(target)
    if confirmed != data:
        raise CreativeSampleError("frozen media object failed byte-for-byte verification")
    return target


def _safe_media_profile(ffprobe: dict[str, object]) -> dict[str, object]:
    format_value = ffprobe.get("format")
    streams_value = ffprobe.get("streams")
    format_info = format_value if isinstance(format_value, dict) else {}
    streams = streams_value if isinstance(streams_value, list) else []
    allowed_stream_fields = (
        "index",
        "codec_type",
        "codec_name",
        "pix_fmt",
        "avg_frame_rate",
        "width",
        "height",
        "sample_rate",
        "channels",
    )
    try:
        measured_duration_ms = round(float(format_info.get("duration", 0)) * 1000)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CreativeSampleError("media duration could not be measured safely") from exc
    if measured_duration_ms <= 0:
        raise CreativeSampleError("media duration must be positive")
    return {
        "format_name": str(format_info.get("format_name", "")),
        "measured_duration_ms": measured_duration_ms,
        "streams": [
            {key: item[key] for key in allowed_stream_fields if key in item}
            for item in streams
            if isinstance(item, dict)
        ],
    }


def _effective_review(
    review: ShotImportReview,
) -> tuple[bool, bool, bool, dict[str, bool], bool | None, bool, bool]:
    editor = review.editor_review
    independent = review.independent_review
    character_ids = set(editor.character_continuity) | set(independent.character_continuity)
    characters = {
        character_id: bool(editor.character_continuity.get(character_id, False))
        and bool(independent.character_continuity.get(character_id, False))
        for character_id in sorted(character_ids)
    }
    if editor.scene_continuity_pass is None or independent.scene_continuity_pass is None:
        scene = None
    else:
        scene = editor.scene_continuity_pass and independent.scene_continuity_pass
    disagreement = (
        editor.first_pass_usable != independent.first_pass_usable
        or editor.shot_intent_pass != independent.shot_intent_pass
        or editor.artifact_free != independent.artifact_free
        or editor.character_continuity != independent.character_continuity
        or editor.scene_continuity_pass != independent.scene_continuity_pass
        or editor.critical_identity_break != independent.critical_identity_break
    )
    return (
        editor.first_pass_usable and independent.first_pass_usable,
        editor.shot_intent_pass and independent.shot_intent_pass,
        editor.artifact_free and independent.artifact_free,
        characters,
        scene,
        editor.critical_identity_break or independent.critical_identity_break,
        disagreement,
    )


def _source_path(root: Path, logical_path: str) -> Path:
    return root.joinpath(*PurePosixPath(logical_path).parts)


def _rate(passed: int, total: int) -> Decimal:
    if total <= 0:
        raise CreativeSampleError("creative metric denominator must be positive")
    return (Decimal(passed) / Decimal(total)).quantize(Decimal("0.0001"))


_EffectiveReview = tuple[bool, bool, bool, dict[str, bool], bool | None, bool, bool]


def _derive_review_metrics(
    compilation_id: str,
    revision_id: str,
    pir_shots: tuple[StoryboardShotV2, ...],
    imports: CreativeSampleImportManifest,
) -> tuple[
    CreativeSampleMetrics | None,
    dict[str, int | str],
    dict[str, _EffectiveReview],
]:
    if tuple(item.shot_id for item in imports.shots) != tuple(item.id for item in pir_shots):
        raise CreativeSampleError("imported shots must form the exact compiled storyboard order")
    shot_by_id = {item.id: item for item in pir_shots}
    first_scene_shot: set[str] = set()
    seen_scenes: set[str] = set()
    for shot in pir_shots:
        if shot.scene_bible_id not in seen_scenes:
            first_scene_shot.add(shot.id)
            seen_scenes.add(shot.scene_bible_id)

    character_passes = 0
    character_total = 0
    scene_passes = 0
    scene_total = 0
    effective_first_pass: list[bool] = []
    effective_intent: list[bool] = []
    effective_artifact: list[bool] = []
    effective_critical: list[bool] = []
    disagreement_count = 0
    effective_by_shot: dict[str, _EffectiveReview] = {}
    for review in imports.shots:
        shot = shot_by_id[review.shot_id]
        expected_characters = {item.character_id for item in shot.character_assets}
        for assessment in (review.editor_review, review.independent_review):
            if set(assessment.character_continuity) != expected_characters:
                raise CreativeSampleError(
                    "each character-continuity review must match the shot bindings"
                )
        effective = _effective_review(review)
        effective_by_shot[review.shot_id] = effective
        (
            first_pass_usable,
            shot_intent_pass,
            artifact_free,
            character_continuity,
            scene_continuity_pass,
            critical_identity_break,
            disagreement,
        ) = effective
        character_total += len(expected_characters)
        character_passes += sum(character_continuity.values())
        if review.shot_id in first_scene_shot:
            if any(
                assessment.scene_continuity_pass is not None
                for assessment in (review.editor_review, review.independent_review)
            ):
                raise CreativeSampleError("the first shot of a scene has no prior scene boundary")
        else:
            if any(
                assessment.scene_continuity_pass is None
                for assessment in (review.editor_review, review.independent_review)
            ):
                raise CreativeSampleError("each in-scene boundary requires a continuity review")
            assert scene_continuity_pass is not None
            scene_total += 1
            scene_passes += int(scene_continuity_pass)
        effective_first_pass.append(first_pass_usable)
        effective_intent.append(shot_intent_pass)
        effective_artifact.append(artifact_free)
        effective_critical.append(critical_identity_break)
        disagreement_count += int(disagreement)

    reviews = imports.shots
    source_mode = reviews[0].source_kind
    digests = [item.expected_sha256 for item in reviews]
    duplicate_media_count = len(digests) - len(set(digests))
    failures = Counter(code for item in reviews for code in item.failure_codes)
    if disagreement_count:
        failures["review.disagreement"] += disagreement_count
    metric_counts: dict[str, int | str] = {
        "status": "SCORED" if source_mode == "IMPORTED_MEDIA" else "NOT_SCORED_FIXTURE",
        "shot_total": len(reviews) if source_mode == "IMPORTED_MEDIA" else 0,
        "first_pass_usable_passed": (
            sum(effective_first_pass) if source_mode == "IMPORTED_MEDIA" else 0
        ),
        "character_appearance_total": character_total if source_mode == "IMPORTED_MEDIA" else 0,
        "character_appearance_passed": (character_passes if source_mode == "IMPORTED_MEDIA" else 0),
        "scene_boundary_total": scene_total if source_mode == "IMPORTED_MEDIA" else 0,
        "scene_boundary_passed": scene_passes if source_mode == "IMPORTED_MEDIA" else 0,
        "shot_intent_passed": sum(effective_intent) if source_mode == "IMPORTED_MEDIA" else 0,
        "artifact_free_passed": (sum(effective_artifact) if source_mode == "IMPORTED_MEDIA" else 0),
        "review_disagreement_count": disagreement_count,
    }
    metrics = None
    if source_mode == "IMPORTED_MEDIA":
        metrics = CreativeSampleMetrics(
            sample_id=compilation_id,
            revision_id=revision_id,
            first_pass_usable_rate=_rate(sum(effective_first_pass), len(reviews)),
            character_continuity_rate=_rate(character_passes, character_total),
            scene_continuity_rate=_rate(scene_passes, scene_total),
            shot_intent_pass_rate=_rate(sum(effective_intent), len(reviews)),
            artifact_free_rate=_rate(sum(effective_artifact), len(reviews)),
            critical_identity_breaks=sum(effective_critical),
            duplicate_media_count=duplicate_media_count,
            average_attempts=_rate(sum(item.attempts for item in reviews), len(reviews)),
            total_elapsed_ms=imports.total_elapsed_ms,
            human_edit_minutes=imports.human_edit_minutes,
            cost_cny=sum((item.cost_cny for item in reviews), start=Decimal("0")),
            failure_counts=dict(sorted(failures.items())),
        )
    return metrics, metric_counts, effective_by_shot


async def _preflight(
    spec: CreativeSampleSpec,
    compilation_id: str,
    revision_id: str,
    pir_shots: tuple[StoryboardShotV2, ...],
    imports: CreativeSampleImportManifest,
    input_root: Path,
    frozen_root: Path,
    toolchain: MediaToolchain,
) -> tuple[
    tuple[tuple[Path, int], ...],
    tuple[TimedVoiceTrack, ...],
    Path | None,
    tuple[LocalAssetSource, ...],
    CreativeSampleMetrics | None,
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object] | None,
    str,
    dict[str, int | str],
]:
    if (
        imports.sample_spec_sha256
        != hashlib.sha256(
            json.dumps(
                spec.model_dump(mode="json"),
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
    ):
        raise CreativeSampleError("import manifest does not bind the exact sample specification")

    compiled_shots = tuple(pir_shots)
    compiled_ids = tuple(item.id for item in compiled_shots)
    if tuple(item.shot_id for item in imports.shots) != compiled_ids:
        raise CreativeSampleError("imported shots must form the exact compiled storyboard order")
    shot_by_id = {item.id: item for item in compiled_shots}
    metrics, metric_counts, effective_by_shot = _derive_review_metrics(
        compilation_id,
        revision_id,
        compiled_shots,
        imports,
    )

    video_inputs: list[tuple[Path, int]] = []
    video_records: list[dict[str, object]] = []
    for review in imports.shots:
        shot = shot_by_id[review.shot_id]
        expected_characters = {item.character_id for item in shot.character_assets}
        (
            first_pass_usable,
            shot_intent_pass,
            artifact_free,
            character_continuity,
            scene_continuity_pass,
            critical_identity_break,
            disagreement,
        ) = effective_by_shot[review.shot_id]

        source = _source_path(input_root, review.logical_path)
        path = _freeze_declared_file(
            source,
            frozen_root / "shots" / f"{shot.ordinal:02d}-{review.expected_sha256}.mp4",
            expected_sha256=review.expected_sha256,
            expected_size_bytes=review.expected_size_bytes,
        )
        evidence, distinct_frames = await inspect_imported_video(
            path,
            expected_duration_ms=shot.duration_ms,
            toolchain=toolchain,
        )
        if evidence.sha256 != review.expected_sha256:
            raise CreativeSampleError("imported shot digest does not match its manifest")
        video_inputs.append((path, shot.duration_ms))
        video_records.append(
            {
                "shot_id": review.shot_id,
                "ordinal": shot.ordinal,
                "scene_id": shot.scene_bible_id,
                "character_ids": sorted(expected_characters),
                "sha256": evidence.sha256,
                "size_bytes": evidence.size_bytes,
                "media_type": review.media_type,
                "measured_media": _safe_media_profile(evidence.ffprobe),
                "first_attempt_sha256": review.first_attempt_sha256,
                "attempts": review.attempts,
                "approval_ref": review.approval_ref,
                "provenance_record_sha256": review.provenance_record_sha256,
                "source_kind": review.source_kind,
                "sampled_distinct_frames": distinct_frames,
                "review": {
                    "editor_ref": review.editor_review.reviewer_ref,
                    "editor_record_sha256": review.editor_review.review_record_sha256,
                    "independent_ref": review.independent_review.reviewer_ref,
                    "independent_record_sha256": (review.independent_review.review_record_sha256),
                    "disagreement": disagreement,
                    "effective_first_pass_usable": first_pass_usable,
                    "effective_shot_intent_pass": shot_intent_pass,
                    "effective_artifact_free": artifact_free,
                    "effective_character_continuity": character_continuity,
                    "effective_scene_continuity_pass": scene_continuity_pass,
                    "effective_critical_identity_break": critical_identity_break,
                },
                "origin_authenticated_by_sdc": False,
            }
        )

    line_by_id = {item.line_id: item for item in spec.dialogue}
    expected_line_ids = tuple(item.line_id for item in spec.dialogue)
    if tuple(item.line_id for item in imports.voices) != expected_line_ids:
        raise CreativeSampleError("voice imports must form the exact dialogue-line order")
    voice_tracks: list[TimedVoiceTrack] = []
    voice_records: list[dict[str, object]] = []
    for ordinal, voice in enumerate(imports.voices):
        source = _source_path(input_root, voice.logical_path)
        path = _freeze_declared_file(
            source,
            frozen_root / "voices" / f"{ordinal:02d}-{voice.expected_sha256}.wav",
            expected_sha256=voice.expected_sha256,
            expected_size_bytes=voice.expected_size_bytes,
        )
        evidence = await inspect_imported_audio(path, toolchain=toolchain)
        if evidence.sha256 != voice.expected_sha256:
            raise CreativeSampleError("voice digest does not match its manifest")
        line = line_by_id[voice.line_id]
        voice_profile = _safe_media_profile(evidence.ffprobe)
        measured_value = voice_profile["measured_duration_ms"]
        if not isinstance(measured_value, int):
            raise CreativeSampleError("voice duration could not be measured safely")
        measured_duration_ms = measured_value
        if measured_duration_ms <= 0 or measured_duration_ms > line.end_ms - line.start_ms + 120:
            raise CreativeSampleError("voice duration exceeds its dialogue master-clock interval")
        voice_tracks.append(
            TimedVoiceTrack(
                line_id=voice.line_id,
                path=path,
                start_ms=line.start_ms,
                end_ms=line.end_ms,
            )
        )
        voice_records.append(
            {
                "line_id": voice.line_id,
                "sha256": evidence.sha256,
                "size_bytes": evidence.size_bytes,
                "media_type": voice.media_type,
                "measured_media": voice_profile,
                "approval_ref": voice.approval_ref,
                "provenance_record_sha256": voice.provenance_record_sha256,
                "source_kind": voice.source_kind,
            }
        )

    bgm_path: Path | None = None
    bgm_record: dict[str, object] | None = None
    if imports.bgm is not None:
        source = _source_path(input_root, imports.bgm.logical_path)
        bgm_path = _freeze_declared_file(
            source,
            frozen_root / "bgm" / f"{imports.bgm.expected_sha256}.wav",
            expected_sha256=imports.bgm.expected_sha256,
            expected_size_bytes=imports.bgm.expected_size_bytes,
        )
        evidence = await inspect_imported_audio(bgm_path, toolchain=toolchain)
        if evidence.sha256 != imports.bgm.expected_sha256:
            raise CreativeSampleError("BGM digest does not match its manifest")
        bgm_record = {
            "sha256": evidence.sha256,
            "size_bytes": evidence.size_bytes,
            "media_type": imports.bgm.media_type,
            "measured_media": _safe_media_profile(evidence.ffprobe),
            "approval_ref": imports.bgm.approval_ref,
            "provenance_record_sha256": imports.bgm.provenance_record_sha256,
            "source_kind": imports.bgm.source_kind,
        }

    character_versions: list[CharacterAssetVersion] = [
        next(item for item in bible.asset_versions if item.id == bible.active_asset_version_id)
        for bible in spec.character_bibles
    ]
    scene_versions: list[SceneAssetVersion] = [
        next(item for item in bible.asset_versions if item.id == bible.active_asset_version_id)
        for bible in spec.scene_bibles
    ]
    active_versions: list[CharacterAssetVersion | SceneAssetVersion] = sorted(
        [*character_versions, *scene_versions], key=lambda item: item.id
    )
    if tuple(item.asset_version_id for item in imports.assets) != tuple(
        item.id for item in active_versions
    ):
        raise CreativeSampleError("asset imports must form the sorted exact active-version closure")
    asset_sources: list[LocalAssetSource] = []
    for ordinal, (imported, version) in enumerate(
        zip(imports.assets, active_versions, strict=True)
    ):
        if imported.expected_sha256 != version.content_sha256:
            raise CreativeSampleError("asset import does not bind the approved version digest")
        source = _source_path(input_root, imported.logical_path)
        path = _freeze_declared_file(
            source,
            frozen_root / "assets" / f"{ordinal:02d}-{version.content_sha256}.png",
            expected_sha256=version.content_sha256,
            expected_size_bytes=imported.expected_size_bytes,
        )
        asset_sources.append(LocalAssetSource(version.id, path))

    source_mode = imports.shots[0].source_kind
    return (
        tuple(video_inputs),
        tuple(voice_tracks),
        bgm_path,
        tuple(asset_sources),
        metrics,
        video_records,
        voice_records,
        bgm_record,
        source_mode,
        metric_counts,
    )


def _walk_regular_tree(root: Path) -> tuple[set[str], set[str]]:
    validate_local_path(root, must_exist=True)
    directories: set[str] = set()
    files: set[str] = set()
    entry_count = 0
    for item in root.rglob("*"):
        entry_count += 1
        if entry_count > 256:
            raise CreativeSampleError("creative sample output exceeds its bounded file closure")
        info = item.lstat()
        attributes = int(getattr(info, "st_file_attributes", 0))
        relative = item.relative_to(root).as_posix()
        if stat.S_ISLNK(info.st_mode) or attributes & 0x400:
            raise CreativeSampleError("creative sample output contains a link or reparse point")
        if stat.S_ISDIR(info.st_mode):
            directories.add(relative)
        elif stat.S_ISREG(info.st_mode):
            files.add(relative)
        else:
            raise CreativeSampleError("creative sample output contains a non-regular entry")
    return directories, files


def _closure(root: Path, files: set[str]) -> list[dict[str, str | int]]:
    result: list[dict[str, str | int]] = []
    for relative in sorted(files):
        data, _ = read_regular_media(root.joinpath(*PurePosixPath(relative).parts))
        result.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            }
        )
    return result


def verify_creative_sample_output(root: Path) -> dict[str, object]:
    """Verify the report-last immutable output closure without running FFmpeg."""
    absolute = validate_local_path(root, must_exist=True)
    directories, files = _walk_regular_tree(absolute)
    if "INCOMPLETE.json" in files or "sample-report.json" not in files:
        raise CreativeSampleError("creative sample output has no completion catalog")
    report = _load_json_object(absolute / "sample-report.json")
    if not isinstance(report, dict) or report.get("completion_marker") is not True:
        raise CreativeSampleError("creative sample completion catalog is not authoritative")
    raw_closure = report.get("output_closure")
    if not isinstance(raw_closure, list) or len(raw_closure) > 255:
        raise CreativeSampleError("creative sample completion closure is invalid")
    expected_paths: set[str] = set()
    for entry in raw_closure:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size_bytes"}:
            raise CreativeSampleError("creative sample closure entry is invalid")
        if (
            not isinstance(entry["path"], str)
            or not isinstance(entry["sha256"], str)
            or len(entry["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in entry["sha256"])
            or not isinstance(entry["size_bytes"], int)
            or isinstance(entry["size_bytes"], bool)
            or entry["size_bytes"] <= 0
        ):
            raise CreativeSampleError("creative sample closure identity is invalid")
        relative = _logical_path(entry["path"])
        if relative == "sample-report.json" or relative in expected_paths:
            raise CreativeSampleError("creative sample closure path is duplicated or recursive")
        expected_paths.add(relative)
        data, _ = read_regular_media(absolute.joinpath(*PurePosixPath(relative).parts))
        if hashlib.sha256(data).hexdigest() != entry["sha256"] or len(data) != entry["size_bytes"]:
            raise CreativeSampleError("creative sample output object drifted from its catalog")
    if files != expected_paths | {"sample-report.json"}:
        raise CreativeSampleError("creative sample output has an unexpected file closure")
    expected_directories: set[str] = set()
    for relative in expected_paths:
        parent = PurePosixPath(relative).parent
        while parent.as_posix() != ".":
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    if directories != expected_directories:
        raise CreativeSampleError("creative sample output has an unexpected directory closure")

    required_fixed_paths = {
        "assembly-receipt.json",
        "audio-master.wav",
        "compilation.json",
        "creative-technical-qc.json",
        "final.mp4",
        "import-evidence.json",
        "import-manifest.json",
        "metrics.json",
        "release-manifest.json",
        "sample-spec.json",
        "subtitles.srt",
    }
    if not required_fixed_paths <= expected_paths:
        raise CreativeSampleError("creative sample output omits a required result")

    spec_model = _load_json(absolute / "sample-spec.json", CreativeSampleSpec)
    compilation_model = _load_json(
        absolute / "compilation.json",
        CreativeSampleCompilation,
    )
    imports_model = _load_json(
        absolute / "import-manifest.json",
        CreativeSampleImportManifest,
    )
    release_model = _load_json(absolute / "release-manifest.json", ReleaseManifest)
    assert isinstance(spec_model, CreativeSampleSpec)
    assert isinstance(compilation_model, CreativeSampleCompilation)
    assert isinstance(imports_model, CreativeSampleImportManifest)
    assert isinstance(release_model, ReleaseManifest)
    if compilation_model != compile_creative_sample(spec_model):
        raise CreativeSampleError("published compilation is not the exact pure compiler output")

    canonical_spec_sha256 = hashlib.sha256(_canonical_model_bytes(spec_model)).hexdigest()
    canonical_import_sha256 = hashlib.sha256(_canonical_model_bytes(imports_model)).hexdigest()
    revision_id = stable_id(
        "creative_revision",
        [compilation_model.id, canonical_import_sha256],
    )
    if (
        compilation_model.spec_sha256 != canonical_spec_sha256
        or imports_model.sample_spec_sha256 != canonical_spec_sha256
        or report.get("sample_id") != compilation_model.id
        or report.get("revision_id") != revision_id
        or report.get("sample_spec_sha256") != canonical_spec_sha256
        or report.get("import_manifest_sha256") != canonical_import_sha256
        or report.get("revision_number") != imports_model.revision_number
        or report.get("predecessor_manifest_sha256") != imports_model.predecessor_manifest_sha256
    ):
        raise CreativeSampleError("creative sample completion identities are inconsistent")

    expected_import_paths: set[str] = set()
    compiled_shots = compilation_model.pir.shots
    if tuple(item.shot_id for item in imports_model.shots) != tuple(
        item.id for item in compiled_shots
    ):
        raise CreativeSampleError("published shot imports do not close over the compilation")
    for shot, shot_import in zip(compiled_shots, imports_model.shots, strict=True):
        expected_import_paths.add(
            f"imported-media/shots/{shot.ordinal:02d}-{shot_import.expected_sha256}.mp4"
        )
    if tuple(item.line_id for item in imports_model.voices) != tuple(
        item.line_id for item in spec_model.dialogue
    ):
        raise CreativeSampleError("published voice imports do not close over the dialogue")
    for ordinal, voice_import in enumerate(imports_model.voices):
        expected_import_paths.add(
            f"imported-media/voices/{ordinal:02d}-{voice_import.expected_sha256}.wav"
        )
    if imports_model.bgm is not None:
        expected_import_paths.add(f"imported-media/bgm/{imports_model.bgm.expected_sha256}.wav")
    active_versions: list[CharacterAssetVersion | SceneAssetVersion] = [
        *(
            next(
                version
                for version in bible.asset_versions
                if version.id == bible.active_asset_version_id
            )
            for bible in spec_model.character_bibles
        ),
        *(
            next(
                version
                for version in bible.asset_versions
                if version.id == bible.active_asset_version_id
            )
            for bible in spec_model.scene_bibles
        ),
    ]
    active_versions.sort(key=lambda item: item.id)
    if tuple(item.asset_version_id for item in imports_model.assets) != tuple(
        item.id for item in active_versions
    ):
        raise CreativeSampleError("published asset imports do not form the active-version closure")
    for ordinal, version in enumerate(active_versions):
        expected_import_paths.add(
            f"imported-media/assets/{ordinal:02d}-{version.content_sha256}.png"
        )

    asset_pack_id = report.get("asset_pack_id")
    if not isinstance(asset_pack_id, str) or len(asset_pack_id) != 64:
        raise CreativeSampleError("creative sample asset-pack identity is invalid")
    pack_root = absolute / "asset-packs" / asset_pack_id
    verify_asset_pack(spec_model, pack_root, expected_pack_id=asset_pack_id)
    _, pack_files = _walk_regular_tree(pack_root)
    expected_pack_paths = {f"asset-packs/{asset_pack_id}/{item}" for item in pack_files}
    if expected_paths != required_fixed_paths | expected_import_paths | expected_pack_paths:
        raise CreativeSampleError("creative sample output is not the exact required result closure")

    release = report.get("release")
    if release != release_model.model_dump(mode="json") or release_model.media_path != "final.mp4":
        raise CreativeSampleError("creative sample release binding is invalid")
    final_data, _ = read_regular_media(absolute / "final.mp4")
    if (
        hashlib.sha256(final_data).hexdigest() != release_model.sha256
        or len(final_data) != release_model.size_bytes
        or release_model.duration_ms != spec_model.duration_ms
    ):
        raise CreativeSampleError("creative sample final media drifted from its release binding")

    receipt = _load_json_object(absolute / "assembly-receipt.json")
    if (
        set(receipt)
        != {
            "receipt_id",
            "document_type",
            "schema_version",
            "sample_id",
            "revision_id",
            "ordered_shots",
            "audio_master_sha256",
            "subtitles_sha256",
            "final_sha256",
            "ffmpeg_policy",
        }
        or receipt.get("document_type") != "sdc.creative-sample-assembly-receipt"
        or receipt.get("schema_version") != "1.0.0"
    ):
        raise CreativeSampleError("creative sample assembly receipt schema is invalid")
    receipt_id = receipt.get("receipt_id")
    receipt_descriptor = {key: value for key, value in receipt.items() if key != "receipt_id"}
    computed_receipt_id = hashlib.sha256(
        b"sdc:creative-sample-assembly-receipt:1.0.0\0"
        + json.dumps(
            receipt_descriptor,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    policy = receipt.get("ffmpeg_policy")
    expected_policy_values = {
        "network_protocols": [],
        "video_input_format": "mov/mp4",
        "audio_input_format": "wav",
        "subtitle_input_format": "srt",
        "metadata": "stripped",
        "chapters": "stripped",
        "width": 1080,
        "height": 1920,
        "fps": 25,
        "audio_rate": 48000,
        "tool_trust_boundary": "operator-controlled-local-installation",
    }
    if not isinstance(policy, dict) or any(
        policy.get(key) != value for key, value in expected_policy_values.items()
    ):
        raise CreativeSampleError("creative sample FFmpeg policy binding is invalid")
    for key in ("ffmpeg_sha256", "ffprobe_sha256"):
        digest = policy.get(key)
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise CreativeSampleError("creative sample media-tool identity is invalid")
    if set(policy) != set(expected_policy_values) | {"ffmpeg_sha256", "ffprobe_sha256"}:
        raise CreativeSampleError("creative sample FFmpeg policy has an unexpected field")
    ordered_shots = receipt.get("ordered_shots")
    expected_ordered_shots = [
        {
            "ordinal": shot.ordinal,
            "shot_id": shot.id,
            "sha256": imported.expected_sha256,
            "duration_ms": shot.duration_ms,
        }
        for shot, imported in zip(compiled_shots, imports_model.shots, strict=True)
    ]
    audio_master, _ = read_regular_media(absolute / "audio-master.wav")
    subtitles, _ = read_regular_media(absolute / "subtitles.srt")
    if (
        receipt_id != computed_receipt_id
        or report.get("assembly_receipt_id") != receipt_id
        or receipt.get("sample_id") != compilation_model.id
        or receipt.get("revision_id") != revision_id
        or ordered_shots != expected_ordered_shots
        or receipt.get("audio_master_sha256") != hashlib.sha256(audio_master).hexdigest()
        or receipt.get("subtitles_sha256") != hashlib.sha256(subtitles).hexdigest()
        or receipt.get("final_sha256") != release_model.sha256
    ):
        raise CreativeSampleError("creative sample assembly receipt is inconsistent")

    technical = _load_json_object(absolute / "creative-technical-qc.json")
    media = technical.get("media")
    technical_checks = technical.get("checks")
    expected_technical_checks = {
        "stream_closure",
        "dimensions",
        "video_profile",
        "audio_profile",
        "subtitle_profile",
        "duration",
        "ordered_import_closure",
        "assembly_timeline_closure",
    }
    if (
        set(technical) != {"passed", "checks", "media", "assembly_receipt_id"}
        or not isinstance(technical.get("passed"), bool)
        or technical.get("assembly_receipt_id") != receipt_id
        or not isinstance(media, dict)
        or set(media) != {"sha256", "size_bytes", "measured_media"}
        or media.get("sha256") != release_model.sha256
        or media.get("size_bytes") != release_model.size_bytes
        or not isinstance(media.get("measured_media"), dict)
        or set(media["measured_media"]) != {"format_name", "measured_duration_ms", "streams"}
        or not isinstance(technical_checks, list)
        or len(technical_checks) != len(expected_technical_checks)
        or any(
            not isinstance(check, dict)
            or set(check) != {"check", "passed", "details"}
            or not isinstance(check.get("check"), str)
            or not isinstance(check.get("passed"), bool)
            or not isinstance(check.get("details"), dict)
            for check in technical_checks
        )
        or {str(check["check"]) for check in technical_checks} != expected_technical_checks
    ):
        raise CreativeSampleError("creative sample technical QC binding is inconsistent")

    source_kind = imports_model.shots[0].source_kind
    import_evidence = _load_json_object(absolute / "import-evidence.json")
    expected_import_evidence_keys = {
        "document_type",
        "schema_version",
        "sample_id",
        "revision_id",
        "source_mode",
        "imported_shots",
        "imported_voices",
        "imported_bgm",
        "metric_counts",
        "origin_authenticated_by_sdc",
    }
    imported_shots_value = import_evidence.get("imported_shots")
    imported_voices_value = import_evidence.get("imported_voices")
    metric_counts_value = import_evidence.get("metric_counts")
    if (
        set(import_evidence) != expected_import_evidence_keys
        or import_evidence.get("document_type") != "sdc.creative-sample-import-evidence"
        or import_evidence.get("schema_version") != "1.0.0"
        or import_evidence.get("sample_id") != compilation_model.id
        or import_evidence.get("revision_id") != revision_id
        or import_evidence.get("source_mode") != source_kind
        or import_evidence.get("origin_authenticated_by_sdc") is not False
        or not isinstance(imported_shots_value, list)
        or len(imported_shots_value) != len(compiled_shots)
        or not isinstance(imported_voices_value, list)
        or len(imported_voices_value) != len(imports_model.voices)
        or not isinstance(metric_counts_value, dict)
    ):
        raise CreativeSampleError("creative sample import evidence is inconsistent")
    derived_metrics, derived_metric_counts, effective_by_shot = _derive_review_metrics(
        compilation_model.id,
        revision_id,
        compiled_shots,
        imports_model,
    )
    if metric_counts_value != derived_metric_counts:
        raise CreativeSampleError("creative sample metric counts are not reproducible")
    for shot, imported, record in zip(
        compiled_shots,
        imports_model.shots,
        imported_shots_value,
        strict=True,
    ):
        if not isinstance(record, dict):
            raise CreativeSampleError("creative sample shot evidence is invalid")
        effective = effective_by_shot[shot.id]
        expected_review = {
            "editor_ref": imported.editor_review.reviewer_ref,
            "editor_record_sha256": imported.editor_review.review_record_sha256,
            "independent_ref": imported.independent_review.reviewer_ref,
            "independent_record_sha256": imported.independent_review.review_record_sha256,
            "disagreement": effective[6],
            "effective_first_pass_usable": effective[0],
            "effective_shot_intent_pass": effective[1],
            "effective_artifact_free": effective[2],
            "effective_character_continuity": effective[3],
            "effective_scene_continuity_pass": effective[4],
            "effective_critical_identity_break": effective[5],
        }
        measured = record.get("measured_media")
        expected_record_keys = {
            "shot_id",
            "ordinal",
            "scene_id",
            "character_ids",
            "sha256",
            "size_bytes",
            "media_type",
            "measured_media",
            "first_attempt_sha256",
            "attempts",
            "approval_ref",
            "provenance_record_sha256",
            "source_kind",
            "sampled_distinct_frames",
            "review",
            "origin_authenticated_by_sdc",
        }
        if (
            set(record) != expected_record_keys
            or record.get("shot_id") != shot.id
            or record.get("ordinal") != shot.ordinal
            or record.get("scene_id") != shot.scene_bible_id
            or record.get("character_ids")
            != sorted(item.character_id for item in shot.character_assets)
            or record.get("sha256") != imported.expected_sha256
            or record.get("size_bytes") != imported.expected_size_bytes
            or record.get("media_type") != imported.media_type
            or record.get("first_attempt_sha256") != imported.first_attempt_sha256
            or record.get("attempts") != imported.attempts
            or record.get("approval_ref") != imported.approval_ref
            or record.get("provenance_record_sha256") != imported.provenance_record_sha256
            or record.get("source_kind") != imported.source_kind
            or not isinstance(record.get("sampled_distinct_frames"), int)
            or isinstance(record.get("sampled_distinct_frames"), bool)
            or int(record["sampled_distinct_frames"]) < 2
            or record.get("review") != expected_review
            or record.get("origin_authenticated_by_sdc") is not False
            or not isinstance(measured, dict)
            or set(measured) != {"format_name", "measured_duration_ms", "streams"}
            or measured.get("format_name") != "mov,mp4,m4a,3gp,3g2,mj2"
            or not isinstance(measured.get("measured_duration_ms"), int)
            or isinstance(measured.get("measured_duration_ms"), bool)
            or abs(int(measured["measured_duration_ms"]) - shot.duration_ms) > 120
            or not isinstance(measured.get("streams"), list)
        ):
            raise CreativeSampleError("creative sample shot evidence is not reproducible")

    line_by_id = {line.line_id: line for line in spec_model.dialogue}
    for voice_import, record in zip(imports_model.voices, imported_voices_value, strict=True):
        if not isinstance(record, dict):
            raise CreativeSampleError("creative sample voice evidence is invalid")
        measured = record.get("measured_media")
        line = line_by_id[voice_import.line_id]
        if (
            set(record)
            != {
                "line_id",
                "sha256",
                "size_bytes",
                "media_type",
                "measured_media",
                "approval_ref",
                "provenance_record_sha256",
                "source_kind",
            }
            or record.get("line_id") != voice_import.line_id
            or record.get("sha256") != voice_import.expected_sha256
            or record.get("size_bytes") != voice_import.expected_size_bytes
            or record.get("media_type") != voice_import.media_type
            or record.get("approval_ref") != voice_import.approval_ref
            or record.get("provenance_record_sha256") != voice_import.provenance_record_sha256
            or record.get("source_kind") != voice_import.source_kind
            or not isinstance(measured, dict)
            or set(measured) != {"format_name", "measured_duration_ms", "streams"}
            or measured.get("format_name") != "wav"
            or not isinstance(measured.get("measured_duration_ms"), int)
            or isinstance(measured.get("measured_duration_ms"), bool)
            or int(measured["measured_duration_ms"]) <= 0
            or int(measured["measured_duration_ms"]) > line.end_ms - line.start_ms + 120
            or not isinstance(measured.get("streams"), list)
        ):
            raise CreativeSampleError("creative sample voice evidence is not reproducible")

    bgm_evidence = import_evidence.get("imported_bgm")
    if imports_model.bgm is None:
        if bgm_evidence is not None:
            raise CreativeSampleError("creative sample has an undeclared BGM evidence record")
    else:
        bgm_measured = (
            bgm_evidence.get("measured_media") if isinstance(bgm_evidence, dict) else None
        )
        if (
            not isinstance(bgm_evidence, dict)
            or set(bgm_evidence)
            != {
                "sha256",
                "size_bytes",
                "media_type",
                "measured_media",
                "approval_ref",
                "provenance_record_sha256",
                "source_kind",
            }
            or bgm_evidence.get("sha256") != imports_model.bgm.expected_sha256
            or bgm_evidence.get("size_bytes") != imports_model.bgm.expected_size_bytes
            or bgm_evidence.get("media_type") != imports_model.bgm.media_type
            or bgm_evidence.get("approval_ref") != imports_model.bgm.approval_ref
            or bgm_evidence.get("provenance_record_sha256")
            != imports_model.bgm.provenance_record_sha256
            or bgm_evidence.get("source_kind") != imports_model.bgm.source_kind
            or not isinstance(bgm_measured, dict)
            or set(bgm_measured) != {"format_name", "measured_duration_ms", "streams"}
            or bgm_measured.get("format_name") != "wav"
            or not isinstance(bgm_measured.get("measured_duration_ms"), int)
            or isinstance(bgm_measured.get("measured_duration_ms"), bool)
            or int(bgm_measured["measured_duration_ms"]) <= 0
            or not isinstance(bgm_measured.get("streams"), list)
        ):
            raise CreativeSampleError("creative sample BGM evidence is not reproducible")
    metrics_value = _load_json_object(absolute / "metrics.json")
    if source_kind == "IMPORTED_MEDIA":
        metrics = CreativeSampleMetrics.model_validate(metrics_value)
        if metrics != derived_metrics:
            raise CreativeSampleError("creative sample metrics are not reproducible")
        expected_decision = metrics.decision if technical["passed"] else CreativeSampleDecision.STOP
        if report.get("metrics") != metrics.model_dump(mode="json"):
            raise CreativeSampleError("creative sample metrics drifted from their report binding")
    else:
        expected_not_scored = {
            "document_type": "sdc.creative-sample-metrics-not-scored",
            "sample_id": compilation_model.id,
            "revision_id": revision_id,
            "status": "SYNTHETIC_FIXTURE_NOT_SCORED",
        }
        if metrics_value != expected_not_scored or report.get("metrics") != {
            "status": "SYNTHETIC_FIXTURE_NOT_SCORED"
        }:
            raise CreativeSampleError("synthetic fixture metrics must remain explicitly unscored")
        expected_decision = CreativeSampleDecision.STOP
    expected_metrics_source = (
        "TWO_REVIEWER_DECLARATIONS_NOT_AUTHENTICATED"
        if source_kind == "IMPORTED_MEDIA"
        else "SYNTHETIC_FIXTURE_NOT_SCORED"
    )
    expected_report_keys = {
        "document_type",
        "schema_version",
        "sample_id",
        "revision_id",
        "revision_number",
        "predecessor_manifest_sha256",
        "sample_spec_sha256",
        "import_manifest_sha256",
        "asset_pack_id",
        "asset_pack_created",
        "imported_shots",
        "imported_voices",
        "imported_bgm",
        "release",
        "metrics",
        "metric_counts",
        "metrics_source",
        "decision",
        "assembly_receipt_id",
        "output_closure",
        "completion_marker",
        "origin_authenticated_by_sdc",
        "live_authority",
        "provider_requests",
    }
    if (
        set(report) != expected_report_keys
        or report.get("document_type") != "sdc.creative-sample-report"
        or report.get("schema_version") != "1.0.0"
        or report.get("decision") != expected_decision.value
        or report.get("metrics_source") != expected_metrics_source
        or report.get("completion_marker") is not True
        or report.get("origin_authenticated_by_sdc") is not False
        or report.get("live_authority") is not False
        or report.get("provider_requests") != 0
        or report.get("asset_pack_created") is not True
        or report.get("imported_shots") != import_evidence["imported_shots"]
        or report.get("imported_voices") != import_evidence["imported_voices"]
        or report.get("imported_bgm") != import_evidence["imported_bgm"]
        or report.get("metric_counts") != import_evidence["metric_counts"]
    ):
        raise CreativeSampleError("creative sample report safety disposition is invalid")
    return report


def _publish_completed_stage(stage: Path, target: Path) -> None:
    directories, files = _walk_regular_tree(stage)
    completion = "sample-report.json"
    if completion not in files or "INCOMPLETE.json" in files:
        raise CreativeSampleError("creative sample stage does not have a completed catalog")
    if os.path.lexists(target):
        raise CreativeSampleError("creative sample target appeared before publication")
    try:
        target.mkdir()
    except OSError as exc:
        raise CreativeSampleError("creative sample target could not be claimed") from exc
    try:
        for relative in sorted(directories, key=lambda value: (value.count("/"), value)):
            target.joinpath(*PurePosixPath(relative).parts).mkdir()
        for relative in sorted(files - {completion}):
            data, _ = read_regular_media(stage.joinpath(*PurePosixPath(relative).parts))
            _write_bytes_new(target.joinpath(*PurePosixPath(relative).parts), data)
        report_data, _ = read_regular_media(stage / completion)
        _write_bytes_new(target / completion, report_data)
        actual_directories, actual_files = _walk_regular_tree(target)
        if actual_directories != directories or actual_files != files:
            raise CreativeSampleError("published creative sample closure is incomplete")
        for relative in sorted(files):
            staged, _ = read_regular_media(stage.joinpath(*PurePosixPath(relative).parts))
            published, _ = read_regular_media(target.joinpath(*PurePosixPath(relative).parts))
            if staged != published:
                raise CreativeSampleError("published creative sample bytes do not match staging")
        verify_creative_sample_output(target)
    except Exception as exc:
        raise CreativeSampleError(
            f"creative sample publication is incomplete; preserve for human review: {target}"
        ) from exc


def _remove_completed_stage(stage: Path, *, target_name: str) -> None:
    if stage.parent == stage or stage.name != f".{target_name}.creative-stage":
        raise CreativeSampleError("creative sample staging cleanup target is unsafe")
    directories, files = _walk_regular_tree(stage)
    try:
        for relative in sorted(files):
            stage.joinpath(*PurePosixPath(relative).parts).unlink()
        for relative in sorted(
            directories,
            key=lambda value: (value.count("/"), value),
            reverse=True,
        ):
            stage.joinpath(*PurePosixPath(relative).parts).rmdir()
        stage.rmdir()
    except OSError as exc:
        raise CreativeSampleError(
            "creative sample published successfully but its staging copy needs human cleanup"
        ) from exc


async def run_creative_sample(
    *,
    spec_path: Path,
    import_manifest_path: Path,
    output_root: Path,
) -> CreativeSampleRunResult:
    spec_model = _load_json(spec_path, CreativeSampleSpec)
    imports_model = _load_json(import_manifest_path, CreativeSampleImportManifest)
    assert isinstance(spec_model, CreativeSampleSpec)
    assert isinstance(imports_model, CreativeSampleImportManifest)
    compilation = compile_creative_sample(spec_model)
    import_manifest_bytes = _canonical_model_bytes(imports_model)
    import_manifest_sha256 = hashlib.sha256(import_manifest_bytes).hexdigest()
    revision_id = stable_id(
        "creative_revision",
        [compilation.id, import_manifest_sha256],
    )
    input_root = validate_local_path(import_manifest_path, must_exist=True).parent
    spec_root = validate_local_path(spec_path, must_exist=True).parent
    output_absolute = validate_local_path(output_root, must_exist=False)
    for source_root in {input_root, spec_root}:
        if (
            output_absolute == source_root
            or output_absolute in source_root.parents
            or source_root in output_absolute.parents
        ):
            raise CreativeSampleError(
                "creative sample output must not overlap a declared input container"
            )
    if os.path.lexists(output_absolute):
        raise CreativeSampleError("creative sample output root must not already exist")
    if not output_absolute.name:
        raise CreativeSampleError("creative sample output root must have a bounded name")
    output_absolute.parent.mkdir(parents=True, exist_ok=True)
    stage = output_absolute.parent / f".{output_absolute.name}.creative-stage"
    if os.path.lexists(stage):
        raise CreativeSampleError("a preserved creative sample staging directory requires review")
    declared_paths = [
        *(item.logical_path for item in imports_model.assets),
        *(item.logical_path for item in imports_model.shots),
        *(item.logical_path for item in imports_model.voices),
        *(() if imports_model.bgm is None else (imports_model.bgm.logical_path,)),
    ]
    for logical_path in declared_paths:
        validate_regular_media_path(_source_path(input_root, logical_path))
    toolchain = resolve_media_toolchain()
    try:
        stage.mkdir()
    except OSError as exc:
        raise CreativeSampleError("creative sample staging directory could not be claimed") from exc
    try:
        _write_json_new(
            stage / "INCOMPLETE.json",
            {
                "document_type": "sdc.creative-sample-incomplete",
                "sample_id": compilation.id,
                "revision_id": revision_id,
            },
        )
        (
            videos,
            voices,
            bgm,
            asset_sources,
            metrics,
            video_records,
            voice_records,
            bgm_record,
            source_mode,
            metric_counts,
        ) = await _preflight(
            spec_model,
            compilation.id,
            revision_id,
            compilation.pir.shots,
            imports_model,
            input_root,
            stage / "imported-media",
            toolchain,
        )

        _write_json_new(stage / "sample-spec.json", spec_model)
        _write_json_new(stage / "compilation.json", compilation)
        _write_json_new(stage / "import-manifest.json", imports_model)
        pack = freeze_asset_pack(spec_model, asset_sources, stage / "asset-packs")

        subtitle_bytes = render_srt(
            [(line.start_ms, line.end_ms, line.text) for line in spec_model.dialogue]
        )
        subtitles = stage / "subtitles.srt"
        _write_bytes_new(subtitles, subtitle_bytes)
        audio_master = stage / "audio-master.wav"
        await render_audio_master(
            voices=voices,
            bgm=bgm,
            duration_ms=spec_model.duration_ms,
            output=audio_master,
            toolchain=toolchain,
        )
        final_media = stage / "final.mp4"
        await assemble_sample(
            videos=videos,
            voices=(
                TimedVoiceTrack(
                    line_id="audio-master",
                    path=audio_master,
                    start_ms=0,
                    end_ms=spec_model.duration_ms,
                ),
            ),
            bgm=None,
            subtitles=subtitles,
            duration_ms=spec_model.duration_ms,
            output=final_media,
            toolchain=toolchain,
        )

        release = release_manifest(final_media, spec_model.duration_ms)
        technical = await verify_assembled_sample(
            final_media,
            expected_duration_ms=spec_model.duration_ms,
            toolchain=toolchain,
        )
        audio_master_data, _ = read_regular_media(audio_master)
        assembly_descriptor = {
            "document_type": "sdc.creative-sample-assembly-receipt",
            "schema_version": "1.0.0",
            "sample_id": compilation.id,
            "revision_id": revision_id,
            "ordered_shots": [
                {
                    "ordinal": record["ordinal"],
                    "shot_id": record["shot_id"],
                    "sha256": record["sha256"],
                    "duration_ms": compilation.pir.shots[index].duration_ms,
                }
                for index, record in enumerate(video_records)
            ],
            "audio_master_sha256": hashlib.sha256(audio_master_data).hexdigest(),
            "subtitles_sha256": hashlib.sha256(subtitle_bytes).hexdigest(),
            "final_sha256": technical.media.sha256,
            "ffmpeg_policy": {
                "network_protocols": [],
                "video_input_format": "mov/mp4",
                "audio_input_format": "wav",
                "subtitle_input_format": "srt",
                "metadata": "stripped",
                "chapters": "stripped",
                "width": 1080,
                "height": 1920,
                "fps": 25,
                "audio_rate": 48000,
                "ffmpeg_sha256": toolchain.ffmpeg_sha256,
                "ffprobe_sha256": toolchain.ffprobe_sha256,
                "tool_trust_boundary": "operator-controlled-local-installation",
            },
        }
        assembly_receipt_id = hashlib.sha256(
            b"sdc:creative-sample-assembly-receipt:1.0.0\0"
            + json.dumps(
                assembly_descriptor,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        assembly_receipt = {
            "receipt_id": assembly_receipt_id,
            **assembly_descriptor,
        }
        _write_json_new(stage / "assembly-receipt.json", assembly_receipt)

        decision = CreativeSampleDecision.STOP
        if technical.passed and source_mode == "IMPORTED_MEDIA" and metrics is not None:
            decision = metrics.decision
        technical_checks = [asdict(item) for item in technical.checks]
        technical_checks.extend(
            [
                {
                    "check": "ordered_import_closure",
                    "passed": len(video_records) == len(compilation.pir.shots),
                    "details": {
                        "imported_shots": len(video_records),
                        "expected_shots": len(compilation.pir.shots),
                    },
                },
                {
                    "check": "assembly_timeline_closure",
                    "passed": sum(item.duration_ms for item in compilation.pir.shots)
                    == spec_model.duration_ms,
                    "details": {
                        "timeline_ms": sum(item.duration_ms for item in compilation.pir.shots),
                        "expected_ms": spec_model.duration_ms,
                    },
                },
            ]
        )
        _write_json_new(stage / "release-manifest.json", release)
        _write_json_new(
            stage / "creative-technical-qc.json",
            {
                "passed": technical.passed
                and all(bool(item["passed"]) for item in technical_checks),
                "checks": technical_checks,
                "media": {
                    "sha256": technical.media.sha256,
                    "size_bytes": technical.media.size_bytes,
                    "measured_media": _safe_media_profile(technical.media.ffprobe),
                },
                "assembly_receipt_id": assembly_receipt_id,
            },
        )
        metrics_payload: object = (
            metrics
            if metrics is not None
            else {
                "document_type": "sdc.creative-sample-metrics-not-scored",
                "sample_id": compilation.id,
                "revision_id": revision_id,
                "status": "SYNTHETIC_FIXTURE_NOT_SCORED",
            }
        )
        _write_json_new(stage / "metrics.json", metrics_payload)
        import_evidence = {
            "document_type": "sdc.creative-sample-import-evidence",
            "schema_version": "1.0.0",
            "sample_id": compilation.id,
            "revision_id": revision_id,
            "source_mode": source_mode,
            "imported_shots": video_records,
            "imported_voices": voice_records,
            "imported_bgm": bgm_record,
            "metric_counts": metric_counts,
            "origin_authenticated_by_sdc": False,
        }
        _write_json_new(stage / "import-evidence.json", import_evidence)
        verify_media_toolchain(toolchain)
        (stage / "INCOMPLETE.json").unlink()
        _, staged_files = _walk_regular_tree(stage)
        output_closure = _closure(stage, staged_files)
        report_path = stage / "sample-report.json"
        _write_json_new(
            report_path,
            {
                "document_type": "sdc.creative-sample-report",
                "schema_version": "1.0.0",
                "sample_id": compilation.id,
                "revision_id": revision_id,
                "revision_number": imports_model.revision_number,
                "predecessor_manifest_sha256": (imports_model.predecessor_manifest_sha256),
                "sample_spec_sha256": compilation.spec_sha256,
                "import_manifest_sha256": import_manifest_sha256,
                "asset_pack_id": pack.pack_id,
                "asset_pack_created": pack.created,
                "imported_shots": video_records,
                "imported_voices": voice_records,
                "imported_bgm": bgm_record,
                "release": release.model_dump(mode="json"),
                "metrics": (
                    metrics.model_dump(mode="json")
                    if metrics is not None
                    else {"status": "SYNTHETIC_FIXTURE_NOT_SCORED"}
                ),
                "metric_counts": metric_counts,
                "metrics_source": (
                    "TWO_REVIEWER_DECLARATIONS_NOT_AUTHENTICATED"
                    if metrics is not None
                    else "SYNTHETIC_FIXTURE_NOT_SCORED"
                ),
                "decision": decision.value,
                "assembly_receipt_id": assembly_receipt_id,
                "output_closure": output_closure,
                "completion_marker": True,
                "origin_authenticated_by_sdc": False,
                "live_authority": False,
                "provider_requests": 0,
            },
        )
        _publish_completed_stage(stage, output_absolute)
        _remove_completed_stage(stage, target_name=output_absolute.name)
    except Exception as exc:
        raise CreativeSampleError(
            f"creative sample output is incomplete; preserve for human review: {stage}"
        ) from exc
    return CreativeSampleRunResult(
        sample_id=compilation.id,
        revision_id=revision_id,
        decision=decision,
        output_root=output_absolute,
        final_media=output_absolute / "final.mp4",
        report_path=output_absolute / "sample-report.json",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assemble one offline ImportedMedia sample")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--imports", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = asyncio.run(
        run_creative_sample(
            spec_path=args.spec,
            import_manifest_path=args.imports,
            output_root=args.output_root,
        )
    )
    print(
        json.dumps(
            {
                "mode": "offline-imported-media",
                "sample_id": result.sample_id,
                "revision_id": result.revision_id,
                "decision": result.decision.value,
                "output_root": str(result.output_root),
                "provider_requests": 0,
                "live_authority": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AssetImport",
    "BGMImport",
    "CreativeSampleError",
    "CreativeSampleImportManifest",
    "CreativeSampleRunResult",
    "ReviewerAssessment",
    "ShotImportReview",
    "VoiceImport",
    "main",
    "run_creative_sample",
    "verify_creative_sample_output",
]
