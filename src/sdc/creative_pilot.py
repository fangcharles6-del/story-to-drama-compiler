"""Machine-verifiable, non-operational Creative Sample Pilot Pack v1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import zlib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, cast
from unicodedata import normalize

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sdc.compiler import compile_creative_sample, stable_id
from sdc.contracts import (
    CharacterAssetVersion,
    CharacterBible,
    CreativeCameraAngle,
    CreativeCameraMovement,
    CreativeSampleCompilation,
    CreativeSampleShotSpec,
    CreativeSampleSpec,
    CreativeShotSize,
    DialogueLine,
    SceneAssetVersion,
    SceneBible,
)
from sdc.creative_media import (
    CreativeMediaError,
    read_regular_media,
    validate_local_path,
    validate_regular_media_path,
)

PILOT_PROFILE = "creative-sample-pilot-pack-v1"
PILOT_SPEC_NAME = "creative-sample-spec.json"
PILOT_PACK_NAME = "pilot-pack.json"
PILOT_FILES = frozenset({PILOT_SPEC_NAME, PILOT_PACK_NAME})
PILOT_JSON_LIMIT = 1024 * 1024

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_PORTABLE_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_WINDOWS_RESERVED_STEMS = frozenset(
    {
        "aux",
        "con",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    }
)


class CreativePilotError(RuntimeError):
    """A Pilot Pack failed a local, deterministic gate."""


class _PilotModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


def _canonical_json_bytes(value: BaseModel) -> bytes:
    return (
        json.dumps(
            value.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_contract_sha256(value: BaseModel) -> str:
    raw = json.dumps(
        value.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _portable_text(value: str, *, field: str, maximum: int = 4000) -> str:
    if not value or len(value) > maximum:
        raise ValueError(f"{field} must contain 1..{maximum} characters")
    if value != value.strip() or value != normalize("NFC", value):
        raise ValueError(f"{field} must be trimmed NFC text")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field} must not contain control characters")
    return value


def _logical_path(value: str) -> str:
    if not value or len(value) > 256 or "\\" in value:
        raise ValueError("pilot logical paths must be bounded portable relative paths")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ValueError("pilot logical paths must be canonical and relative")
    for part in path.parts:
        if (
            part in {"", ".", ".."}
            or part.rstrip(" .") != part
            or normalize("NFC", part) != part
            or any(character in '<>:"|?*' for character in part)
            or any(ord(character) < 32 or ord(character) == 127 for character in part)
            or part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_STEMS
        ):
            raise ValueError("pilot logical path contains an unsafe component")
    return value


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def synthetic_placeholder_png_bytes(label: str) -> bytes:
    """Return deterministic metadata-free fixture bytes; never real creative evidence."""
    _portable_text(label, field="placeholder label", maximum=128)
    color = hashlib.sha256(label.encode("utf-8")).digest()[:3]
    scanlines = (b"\x00" + color * 2) * 2
    ihdr = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(scanlines, level=9))
        + _png_chunk(b"IEND", b"")
    )


class PilotAssetRequirement(_PilotModel):
    requirement_id: str = Field(pattern=_PORTABLE_ID)
    subject_kind: Literal["CHARACTER", "SCENE"]
    subject_id: str = Field(pattern=_PORTABLE_ID)
    asset_version_id: str = Field(pattern=_PORTABLE_ID)
    intended_logical_path: str
    placeholder_label: str = Field(min_length=1, max_length=128)
    placeholder_sha256: str = Field(pattern=_LOWER_SHA256)
    media_type: Literal["image/png"] = "image/png"
    source_mode: Literal["SYNTHETIC_PLACEHOLDER_ONLY"] = "SYNTHETIC_PLACEHOLDER_ONLY"
    submission_status: Literal["NOT_SUBMITTED"] = "NOT_SUBMITTED"
    rights_status: Literal["PENDING_REVIEW"] = "PENDING_REVIEW"
    privacy_status: Literal["PENDING_REVIEW"] = "PENDING_REVIEW"
    eligible_for_real_generation: Literal[False] = False
    visual_requirements: tuple[str, ...] = Field(min_length=1)

    @field_validator("intended_logical_path")
    @classmethod
    def validate_logical_path(cls, value: str) -> str:
        return _logical_path(value)

    @field_validator("placeholder_label", "visual_requirements")
    @classmethod
    def validate_text(cls, value: str | tuple[str, ...]) -> str | tuple[str, ...]:
        if isinstance(value, str):
            return _portable_text(value, field="asset requirement", maximum=1000)
        if len(value) != len(set(value)):
            raise ValueError("asset visual requirements must be unique")
        return tuple(
            _portable_text(item, field="asset visual requirement", maximum=1000) for item in value
        )

    @model_validator(mode="after")
    def validate_identity(self) -> PilotAssetRequirement:
        expected = stable_id(
            "pilot_asset_requirement",
            {
                "asset_version_id": self.asset_version_id,
                "intended_logical_path": self.intended_logical_path,
                "placeholder_sha256": self.placeholder_sha256,
                "subject_id": self.subject_id,
                "subject_kind": self.subject_kind,
            },
        )
        if self.requirement_id != expected:
            raise ValueError("pilot asset requirement ID must bind its canonical identity")
        expected_sha = hashlib.sha256(
            synthetic_placeholder_png_bytes(self.placeholder_label)
        ).hexdigest()
        if self.placeholder_sha256 != expected_sha:
            raise ValueError("placeholder digest must bind deterministic synthetic bytes")
        return self


class PilotAudioRequirement(_PilotModel):
    requirement_id: str = Field(pattern=_PORTABLE_ID)
    kind: Literal["VOICE", "BGM"]
    line_id: str | None = Field(default=None, pattern=_PORTABLE_ID)
    start_ms: Annotated[int, Field(ge=0)]
    end_ms: Annotated[int, Field(gt=0)]
    exact_text: str | None = Field(default=None, max_length=2000)
    direction: str = Field(min_length=1, max_length=2000)
    intended_logical_path: str
    media_type: Literal["audio/wav"] = "audio/wav"
    sample_rate_hz: Literal[48000] = 48000
    expected_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    expected_size_bytes: Annotated[int, Field(gt=0)] | None = None
    provenance_record_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    submission_status: Literal["NOT_SUBMITTED", "SUBMITTED"] = "NOT_SUBMITTED"
    rights_status: Literal["PENDING_REVIEW", "APPROVED", "REJECTED"] = "PENDING_REVIEW"
    eligible_for_real_generation: bool = False

    @field_validator("intended_logical_path")
    @classmethod
    def validate_logical_path(cls, value: str) -> str:
        return _logical_path(value)

    @field_validator("exact_text", "direction")
    @classmethod
    def validate_text(cls, value: str | None) -> str | None:
        return (
            None
            if value is None
            else _portable_text(value, field="audio requirement", maximum=2000)
        )

    @model_validator(mode="after")
    def validate_audio_requirement(self) -> PilotAudioRequirement:
        if self.end_ms <= self.start_ms:
            raise ValueError("audio requirement must have a positive interval")
        if self.kind == "VOICE" and (self.line_id is None or self.exact_text is None):
            raise ValueError("voice requirements must bind one dialogue line and exact text")
        if self.kind == "BGM" and (self.line_id is not None or self.exact_text is not None):
            raise ValueError("BGM requirement must not bind dialogue")
        expected = stable_id(
            "pilot_audio_requirement",
            {
                "end_ms": self.end_ms,
                "exact_text": self.exact_text,
                "intended_logical_path": self.intended_logical_path,
                "kind": self.kind,
                "line_id": self.line_id,
                "start_ms": self.start_ms,
            },
        )
        if self.requirement_id != expected:
            raise ValueError("pilot audio requirement ID must bind its canonical identity")
        evidence = (
            self.expected_sha256,
            self.expected_size_bytes,
            self.provenance_record_sha256,
        )
        if self.submission_status == "NOT_SUBMITTED":
            if any(item is not None for item in evidence):
                raise ValueError("unsubmitted audio must not claim byte or provenance evidence")
            if self.rights_status != "PENDING_REVIEW" or self.eligible_for_real_generation:
                raise ValueError("unsubmitted audio must remain pending and ineligible")
        else:
            if any(item is None for item in evidence):
                raise ValueError("submitted audio must bind bytes and provenance")
            expected_eligible = self.rights_status == "APPROVED"
            if self.eligible_for_real_generation != expected_eligible:
                raise ValueError("audio eligibility must exactly follow reviewed rights")
        return self


class PilotShotPlan(_PilotModel):
    shot_id: str = Field(pattern=_PORTABLE_ID)
    ordinal: Annotated[int, Field(ge=0, le=9)]
    start_ms: Annotated[int, Field(ge=0)]
    duration_ms: Annotated[int, Field(gt=0)]
    scene_id: str = Field(pattern=_PORTABLE_ID)
    character_ids: tuple[str, ...] = Field(min_length=1, max_length=2)
    dialogue_line_ids: tuple[str, ...]
    visual_goal: str = Field(min_length=1, max_length=4000)
    unacceptable_defects: tuple[str, ...] = Field(min_length=1)
    required_asset_version_ids: tuple[str, ...] = Field(min_length=2)
    voice_line_ids: tuple[str, ...]
    subtitle_text: tuple[str, ...]
    bgm_direction: str = Field(min_length=1, max_length=2000)
    post_requirements: tuple[str, ...] = Field(min_length=1)
    first_pass_criteria: tuple[str, ...] = Field(min_length=1)
    scene_continuity_required: bool

    @field_validator(
        "character_ids",
        "dialogue_line_ids",
        "required_asset_version_ids",
        "voice_line_ids",
        "unacceptable_defects",
        "post_requirements",
        "first_pass_criteria",
    )
    @classmethod
    def validate_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("pilot shot tuple values must be unique")
        return value

    @field_validator(
        "visual_goal",
        "unacceptable_defects",
        "subtitle_text",
        "bgm_direction",
        "post_requirements",
        "first_pass_criteria",
    )
    @classmethod
    def validate_text(cls, value: str | tuple[str, ...]) -> str | tuple[str, ...]:
        if isinstance(value, str):
            return _portable_text(value, field="shot plan", maximum=4000)
        return tuple(_portable_text(item, field="shot plan", maximum=2000) for item in value)

    @model_validator(mode="after")
    def validate_shot_plan(self) -> PilotShotPlan:
        if self.voice_line_ids != self.dialogue_line_ids:
            raise ValueError("voice requirements must exactly match shot dialogue")
        if len(self.subtitle_text) != len(self.dialogue_line_ids):
            raise ValueError("subtitle text must exactly cover shot dialogue")
        if self.character_ids != tuple(sorted(self.character_ids)):
            raise ValueError("shot character IDs must use canonical sorted order")
        if self.required_asset_version_ids != tuple(sorted(self.required_asset_version_ids)):
            raise ValueError("required asset versions must use canonical sorted order")
        return self


class PilotRightsReviewRow(_PilotModel):
    subject_kind: Literal["IMAGE_ASSET", "VOICE", "BGM"]
    subject_id: str = Field(pattern=_PORTABLE_ID)
    intended_logical_path: str
    submission_status: Literal["NOT_SUBMITTED", "SUBMITTED"] = "NOT_SUBMITTED"
    expected_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    expected_size_bytes: Annotated[int, Field(gt=0)] | None = None
    provenance_record_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    source_category: str | None = Field(default=None, max_length=128)
    rights_basis: str | None = Field(default=None, max_length=1000)
    territory: str | None = Field(default=None, max_length=128)
    use_scope: str | None = Field(default=None, max_length=1000)
    expiry: str | None = Field(default=None, max_length=64)
    likeness_privacy_basis: str | None = Field(default=None, max_length=1000)
    reviewer_a_ref: str | None = Field(default=None, pattern=_PORTABLE_ID)
    reviewer_b_ref: str | None = Field(default=None, pattern=_PORTABLE_ID)
    review_record_a_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    review_record_b_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    decision: Literal["PENDING_REVIEW", "APPROVED", "REJECTED"] = "PENDING_REVIEW"
    eligible_for_real_generation: bool = False

    @field_validator("intended_logical_path")
    @classmethod
    def validate_logical_path(cls, value: str) -> str:
        return _logical_path(value)

    @field_validator(
        "source_category",
        "rights_basis",
        "territory",
        "use_scope",
        "likeness_privacy_basis",
    )
    @classmethod
    def validate_optional_evidence_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _portable_text(value, field="rights evidence", maximum=1000)

    @field_validator("expiry")
    @classmethod
    def validate_expiry(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            if len(value) == 10:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            elif len(value) == 20 and value.endswith("Z"):
                parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
                if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
                    raise ValueError
            else:
                raise ValueError
        except ValueError as exc:
            raise ValueError("rights expiry must be a canonical date or UTC second") from exc
        return value

    @model_validator(mode="after")
    def validate_rights_state(self) -> PilotRightsReviewRow:
        required_evidence = (
            self.expected_sha256,
            self.expected_size_bytes,
            self.provenance_record_sha256,
            self.source_category,
            self.rights_basis,
            self.territory,
            self.use_scope,
            self.likeness_privacy_basis,
            self.reviewer_a_ref,
            self.reviewer_b_ref,
            self.review_record_a_sha256,
            self.review_record_b_sha256,
        )
        if self.submission_status == "NOT_SUBMITTED":
            if any(item is not None for item in (*required_evidence, self.expiry)):
                raise ValueError("unsubmitted rights rows must remain completely unfilled")
            if self.decision != "PENDING_REVIEW" or self.eligible_for_real_generation:
                raise ValueError("unsubmitted rights rows must remain pending and ineligible")
        else:
            if any(item is None for item in required_evidence):
                raise ValueError("submitted rights rows require complete evidence and two reviews")
            if self.reviewer_a_ref == self.reviewer_b_ref:
                raise ValueError("rights reviewers must be distinct")
            if self.review_record_a_sha256 == self.review_record_b_sha256:
                raise ValueError("rights review records must be independently hashed")
            if self.eligible_for_real_generation != (self.decision == "APPROVED"):
                raise ValueError("rights eligibility must exactly follow the final decision")
        return self


class PilotCharacterContinuityReview(_PilotModel):
    character_id: str = Field(pattern=_PORTABLE_ID)
    passed: bool | None = None


class PilotShotReviewTemplate(_PilotModel):
    shot_id: str = Field(pattern=_PORTABLE_ID)
    role: Literal["EDITOR", "INDEPENDENT"]
    scene_continuity_required: bool
    status: Literal["UNFILLED", "COMPLETED"] = "UNFILLED"
    reviewer_ref: str | None = Field(default=None, pattern=_PORTABLE_ID)
    media_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    review_record_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    first_pass_usable: bool | None = None
    shot_intent_pass: bool | None = None
    artifact_free: bool | None = None
    character_continuity: tuple[PilotCharacterContinuityReview, ...] = Field(min_length=1)
    scene_continuity_pass: bool | None = None
    critical_identity_break: bool | None = None
    failure_codes: tuple[str, ...] = ()
    notes: str | None = Field(default=None, max_length=2000)
    human_review_ms: Annotated[int, Field(ge=0)] | None = None
    human_edit_ms: Annotated[int, Field(ge=0)] | None = None

    @field_validator("failure_codes")
    @classmethod
    def validate_failure_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))):
            raise ValueError("review failure codes must be unique and sorted")
        if any(
            not item
            or len(item) > 64
            or item[0] not in "abcdefghijklmnopqrstuvwxyz"
            or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in item)
            for item in value
        ):
            raise ValueError("review failure codes must use canonical lowercase identifiers")
        return value

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        return None if value is None else _portable_text(value, field="review notes", maximum=2000)

    @model_validator(mode="after")
    def validate_review_state(self) -> PilotShotReviewTemplate:
        character_ids = tuple(item.character_id for item in self.character_continuity)
        if character_ids != tuple(sorted(set(character_ids))):
            raise ValueError("review character rows must be unique and sorted")
        scalar_values = (
            self.reviewer_ref,
            self.media_sha256,
            self.review_record_sha256,
            self.first_pass_usable,
            self.shot_intent_pass,
            self.artifact_free,
            self.critical_identity_break,
            self.notes,
            self.human_review_ms,
            self.human_edit_ms,
        )
        if self.status == "UNFILLED":
            if any(item is not None for item in scalar_values):
                raise ValueError("unfilled shot review must not contain review values")
            if self.failure_codes or any(
                item.passed is not None for item in self.character_continuity
            ):
                raise ValueError("unfilled shot review must not contain scored values")
            if self.scene_continuity_pass is not None:
                raise ValueError("unfilled shot review must not contain a scene score")
        else:
            if any(item is None for item in scalar_values):
                raise ValueError("completed shot review requires identity, scores, notes and time")
            if any(item.passed is None for item in self.character_continuity):
                raise ValueError("completed shot review requires every character score")
            if self.scene_continuity_required != (self.scene_continuity_pass is not None):
                raise ValueError("scene continuity score must follow the shot boundary rule")
            if self.first_pass_usable and (
                not self.shot_intent_pass
                or not self.artifact_free
                or self.critical_identity_break
                or any(not item.passed for item in self.character_continuity)
                or (self.scene_continuity_required and not self.scene_continuity_pass)
            ):
                raise ValueError("first-pass usable requires every applicable review gate")
        return self


class PilotFailureCount(_PilotModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    count: Annotated[int, Field(ge=0)]


class PilotShotWorkRecord(_PilotModel):
    shot_id: str = Field(pattern=_PORTABLE_ID)
    status: Literal["UNFILLED", "COMPLETED"] = "UNFILLED"
    source_mode: Literal["IMPORTED_MEDIA", "PROVIDER_GENERATED"] | None = None
    attempts: Annotated[int, Field(ge=1, le=2)] | None = None
    first_attempt_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    final_media_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    provider_request_count: Annotated[int, Field(ge=0, le=2)] | None = None
    provider_cost_cny_microunits: Annotated[int, Field(ge=0)] | None = None
    human_edit_ms: Annotated[int, Field(ge=0)] | None = None
    failure_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_work_state(self) -> PilotShotWorkRecord:
        values = (
            self.source_mode,
            self.attempts,
            self.first_attempt_sha256,
            self.final_media_sha256,
            self.provider_request_count,
            self.provider_cost_cny_microunits,
            self.human_edit_ms,
        )
        if self.failure_codes != tuple(sorted(set(self.failure_codes))) or any(
            not item
            or len(item) > 64
            or item[0] not in "abcdefghijklmnopqrstuvwxyz"
            or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in item)
            for item in self.failure_codes
        ):
            raise ValueError("shot work failure codes must be unique and sorted")
        if self.status == "UNFILLED":
            if any(item is not None for item in values) or self.failure_codes:
                raise ValueError("unfilled shot work rows must not contain observed values")
        elif any(item is None for item in values):
            raise ValueError("completed shot work rows require all time, cost and attempt values")
        elif self.source_mode == "IMPORTED_MEDIA" and (
            self.provider_request_count != 0 or self.provider_cost_cny_microunits != 0
        ):
            raise ValueError(
                "imported media must record zero Provider requests and zero Provider cost"
            )
        elif (
            self.source_mode == "PROVIDER_GENERATED"
            and self.provider_request_count != self.attempts
        ):
            raise ValueError(
                "Provider-generated work request count must exactly equal its Attempts"
            )
        elif (self.attempts == 1) != (self.first_attempt_sha256 == self.final_media_sha256):
            raise ValueError("Attempt 1 reuses its digest and Attempt 2 retains a distinct digest")
        return self


class PilotMetricsTemplate(_PilotModel):
    status: Literal["UNFILLED", "COMPLETED"] = "UNFILLED"
    shot_count: Literal[10] = 10
    character_appearance_count: Literal[17] = 17
    scene_boundary_count: Literal[8] = 8
    first_pass_usable_count: Annotated[int, Field(ge=0, le=10)] | None = None
    character_continuity_pass_count: Annotated[int, Field(ge=0, le=17)] | None = None
    scene_continuity_pass_count: Annotated[int, Field(ge=0, le=8)] | None = None
    shot_intent_pass_count: Annotated[int, Field(ge=0, le=10)] | None = None
    artifact_free_count: Annotated[int, Field(ge=0, le=10)] | None = None
    critical_identity_breaks: Annotated[int, Field(ge=0)] | None = None
    duplicate_media_count: Annotated[int, Field(ge=0)] | None = None
    total_attempts: Annotated[int, Field(ge=10, le=20)] | None = None
    total_elapsed_ms: Annotated[int, Field(ge=0)] | None = None
    human_review_ms: Annotated[int, Field(ge=0)] | None = None
    human_edit_ms: Annotated[int, Field(ge=0)] | None = None
    cost_cny_microunits: Annotated[int, Field(ge=0)] | None = None
    failure_counts: tuple[PilotFailureCount, ...] | None = None

    @model_validator(mode="after")
    def validate_metrics_state(self) -> PilotMetricsTemplate:
        values = tuple(
            getattr(self, name)
            for name in self.__class__.model_fields
            if name
            not in {"status", "shot_count", "character_appearance_count", "scene_boundary_count"}
        )
        if self.status == "UNFILLED" and any(item is not None for item in values):
            raise ValueError("unfilled metrics must not contain observed values")
        if self.status == "COMPLETED" and any(item is None for item in values):
            raise ValueError("completed metrics require every observed value")
        if self.failure_counts is not None:
            codes = tuple(item.code for item in self.failure_counts)
            if codes != tuple(sorted(set(codes))):
                raise ValueError("metric failure counts must be unique and sorted")
        return self


class PilotFailureClass(_PilotModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    meaning: str = Field(min_length=1, max_length=1000)
    disposition: str = Field(min_length=1, max_length=1000)

    @field_validator("meaning", "disposition")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _portable_text(value, field="failure taxonomy", maximum=1000)


class PilotSyntheticRehearsal(_PilotModel):
    source_mode: Literal["SYNTHETIC_FIXTURE"] = "SYNTHETIC_FIXTURE"
    expected_decision: Literal["STOP"] = "STOP"
    human_status: Literal["NOT_SCORED"] = "NOT_SCORED"
    metric_status: Literal["NOT_SCORED_FIXTURE"] = "NOT_SCORED_FIXTURE"
    provider_requests: Literal[0] = 0
    posts_allowed: Literal[0] = 0
    proves_content_quality: Literal[False] = False
    proves_provider_readiness: Literal[False] = False


class PilotDeliveryProfile(_PilotModel):
    width: Literal[1080] = 1080
    height: Literal[1920] = 1920
    display_aspect_ratio: Literal["9:16"] = "9:16"
    fps: Literal[25] = 25
    video_codec: Literal["h264"] = "h264"
    pixel_format: Literal["yuv420p"] = "yuv420p"
    audio_codec: Literal["aac"] = "aac"
    audio_sample_rate_hz: Literal[48000] = 48000
    audio_channels: Literal[2] = 2
    subtitle_codec: Literal["mov_text"] = "mov_text"
    container: Literal["mp4"] = "mp4"


class PilotProviderBatchPlan(_PilotModel):
    provider: Literal["volcengine_ark"] = "volcengine_ark"
    model: Literal["doubao-seedance-2-0-260128"] = "doubao-seedance-2-0-260128"
    region: Literal["cn-beijing"] = "cn-beijing"
    operation: Literal["contents.generations.tasks.create"] = "contents.generations.tasks.create"
    state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    exact_shot_ids: tuple[str, ...] = Field(min_length=10, max_length=10)
    max_attempts_per_shot: Literal[2] = 2
    planned_max_video_requests: Literal[20] = 20
    planned_voice_requests: Literal[0] = 0
    planned_image_requests: Literal[0] = 0
    proposed_cost_ceiling_cny: Literal[450] = 450
    posts_allowed: Literal[0] = 0
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    stop_conditions: tuple[str, ...] = Field(min_length=8)

    @field_validator("stop_conditions")
    @classmethod
    def validate_stop_conditions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("batch stop conditions must be unique")
        return tuple(
            _portable_text(item, field="batch stop condition", maximum=1000) for item in value
        )


class CreativeSamplePilotSpecDocument(_PilotModel):
    """Fixture-only envelope that prevents the embedded spec being mistaken for real media."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-pilot-spec"] = "sdc.creative-sample-pilot-spec"
    profile: Literal["creative-sample-pilot-pack-v1"] = "creative-sample-pilot-pack-v1"
    source_mode: Literal["SYNTHETIC_PLACEHOLDER_ONLY"] = "SYNTHETIC_PLACEHOLDER_ONLY"
    fixture_admission_scope: Literal["TECHNICAL_COMPILATION_ONLY"] = "TECHNICAL_COMPILATION_ONLY"
    eligible_for_real_generation: Literal[False] = False
    spec: CreativeSampleSpec

    @model_validator(mode="after")
    def validate_fixture_only_assets(self) -> CreativeSamplePilotSpecDocument:
        versions: tuple[CharacterAssetVersion | SceneAssetVersion, ...] = (
            *(version for bible in self.spec.character_bibles for version in bible.asset_versions),
            *(version for bible in self.spec.scene_bibles for version in bible.asset_versions),
        )
        if not versions or any(
            not item.approval_ref.startswith("pilot-fixture-only-") for item in versions
        ):
            raise ValueError("Pilot spec envelope accepts only explicit fixture-only asset refs")
        return self


class CreativeSamplePilotPack(_PilotModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-pilot-pack"] = "sdc.creative-sample-pilot-pack"
    profile: Literal["creative-sample-pilot-pack-v1"] = "creative-sample-pilot-pack-v1"
    pack_id: str = Field(pattern=r"^creative_pilot_pack_[0-9a-f]{20}$")
    title: Literal["辞职信照旧"] = "辞职信照旧"
    sample_spec_sha256: str = Field(pattern=_LOWER_SHA256)
    compilation_id: str = Field(pattern=r"^creative_sample_[0-9a-f]{20}$")
    ordered_shot_ids: tuple[str, ...] = Field(min_length=10, max_length=10)
    active_asset_version_ids: tuple[str, ...] = Field(min_length=4, max_length=4)
    asset_requirements: tuple[PilotAssetRequirement, ...] = Field(min_length=4, max_length=4)
    audio_requirements: tuple[PilotAudioRequirement, ...] = Field(min_length=10, max_length=10)
    shot_plans: tuple[PilotShotPlan, ...] = Field(min_length=10, max_length=10)
    delivery_profile: PilotDeliveryProfile
    rights_review_rows: tuple[PilotRightsReviewRow, ...] = Field(min_length=14, max_length=14)
    shot_review_templates: tuple[PilotShotReviewTemplate, ...] = Field(min_length=20, max_length=20)
    shot_work_records: tuple[PilotShotWorkRecord, ...] = Field(min_length=10, max_length=10)
    metrics_template: PilotMetricsTemplate
    failure_taxonomy: tuple[PilotFailureClass, ...] = Field(min_length=21, max_length=21)
    synthetic_rehearsal: PilotSyntheticRehearsal
    provider_batch_plan: PilotProviderBatchPlan

    @staticmethod
    def derive_id(value: dict[str, object]) -> str:
        return stable_id("creative_pilot_pack", value)

    @model_validator(mode="after")
    def validate_pack_closure(self) -> CreativeSamplePilotPack:
        if self.pack_id != self.derive_id(self.model_dump(mode="json", exclude={"pack_id"})):
            raise ValueError("Pilot Pack ID must derive from its complete canonical content")
        if self.ordered_shot_ids != tuple(dict.fromkeys(self.ordered_shot_ids)):
            raise ValueError("Pilot Pack shot IDs must be unique and ordered")
        if self.active_asset_version_ids != tuple(sorted(set(self.active_asset_version_ids))):
            raise ValueError("Pilot Pack active assets must be unique and canonically sorted")
        if tuple(item.asset_version_id for item in self.asset_requirements) != (
            self.active_asset_version_ids
        ):
            raise ValueError("asset requirements must exactly cover active asset versions")
        expected_rights_keys = (
            *(("IMAGE_ASSET", item) for item in self.active_asset_version_ids),
            *(
                (
                    item.kind,
                    item.line_id if item.kind == "VOICE" else item.requirement_id,
                )
                for item in self.audio_requirements
            ),
        )
        actual_rights_keys = tuple(
            (item.subject_kind, item.subject_id) for item in self.rights_review_rows
        )
        if actual_rights_keys != expected_rights_keys:
            raise ValueError("rights rows must exactly cover every image, voice and BGM input")
        if tuple(item.shot_id for item in self.shot_plans) != self.ordered_shot_ids:
            raise ValueError("shot plans must exactly cover ordered shots")
        expected_review_keys = tuple(
            (shot_id, role)
            for shot_id in self.ordered_shot_ids
            for role in ("EDITOR", "INDEPENDENT")
        )
        actual_review_keys = tuple((item.shot_id, item.role) for item in self.shot_review_templates)
        if actual_review_keys != expected_review_keys:
            raise ValueError("review templates must contain two ordered unfilled rows per shot")
        for offset in range(0, len(self.shot_review_templates), 2):
            editor, independent = self.shot_review_templates[offset : offset + 2]
            if editor.status != independent.status:
                raise ValueError("the two shot reviewers must be filled as one complete pair")
            if editor.status == "COMPLETED" and (
                editor.reviewer_ref == independent.reviewer_ref
                or editor.media_sha256 != independent.media_sha256
            ):
                raise ValueError(
                    "completed shot reviews need distinct reviewers on identical bytes"
                )
        if tuple(item.shot_id for item in self.shot_work_records) != self.ordered_shot_ids:
            raise ValueError("shot work records must exactly cover ordered shots")
        if self.provider_batch_plan.exact_shot_ids != self.ordered_shot_ids:
            raise ValueError("future batch plan must bind the exact Pilot Pack shots")
        codes = tuple(item.code for item in self.failure_taxonomy)
        if codes != tuple(sorted(set(codes))):
            raise ValueError("failure taxonomy must be unique and canonically sorted")
        return self


@dataclass(frozen=True, slots=True)
class ValidatedCreativeSamplePilotPack:
    root: Path
    spec: CreativeSampleSpec
    compilation: CreativeSampleCompilation
    pack: CreativeSamplePilotPack


def _character_bible(
    *, name: str, visual_description: str, label: str, asset_description: str
) -> CharacterBible:
    character_id = CharacterBible.derive_id(name=name, visual_description=visual_description)
    placeholder_sha = hashlib.sha256(synthetic_placeholder_png_bytes(label)).hexdigest()
    approval_ref = f"pilot-fixture-only-{label}-v1"
    version_id = CharacterAssetVersion.derive_id(
        character_id=character_id,
        version=1,
        content_sha256=placeholder_sha,
        media_type="image/png",
        approval_ref=approval_ref,
        visual_description=asset_description,
    )
    version = CharacterAssetVersion(
        id=version_id,
        character_id=character_id,
        version=1,
        content_sha256=placeholder_sha,
        media_type="image/png",
        approval_ref=approval_ref,
        visual_description=asset_description,
    )
    return CharacterBible(
        character_id=character_id,
        name=name,
        visual_description=visual_description,
        asset_versions=(version,),
        active_asset_version_id=version.id,
    )


def _scene_bible(
    *, ordinal: int, name: str, visual_description: str, label: str, asset_description: str
) -> SceneBible:
    scene_id = SceneBible.derive_id(
        ordinal=ordinal,
        name=name,
        visual_description=visual_description,
    )
    placeholder_sha = hashlib.sha256(synthetic_placeholder_png_bytes(label)).hexdigest()
    approval_ref = f"pilot-fixture-only-{label}-v1"
    version_id = SceneAssetVersion.derive_id(
        scene_id=scene_id,
        version=1,
        content_sha256=placeholder_sha,
        media_type="image/png",
        approval_ref=approval_ref,
        visual_description=asset_description,
    )
    version = SceneAssetVersion(
        id=version_id,
        scene_id=scene_id,
        version=1,
        content_sha256=placeholder_sha,
        media_type="image/png",
        approval_ref=approval_ref,
        visual_description=asset_description,
    )
    return SceneBible(
        scene_id=scene_id,
        ordinal=ordinal,
        name=name,
        visual_description=visual_description,
        asset_versions=(version,),
        active_asset_version_id=version.id,
    )


def _dialogue(
    *,
    ordinal: int,
    scene_id: str,
    character_id: str,
    text: str,
    start_ms: int,
    end_ms: int,
) -> DialogueLine:
    return DialogueLine(
        line_id=DialogueLine.derive_id(
            ordinal=ordinal,
            scene_id=scene_id,
            character_id=character_id,
            text=text,
            start_ms=start_ms,
            end_ms=end_ms,
        ),
        ordinal=ordinal,
        scene_id=scene_id,
        character_id=character_id,
        text=text,
        start_ms=start_ms,
        end_ms=end_ms,
    )


def _build_spec() -> CreativeSampleSpec:
    su = _character_bible(
        name="苏晴",
        visual_description=(
            "28岁成年中国女性，椭圆脸，深棕色眼睛，黑色低马尾，身形匀称，神态克制；"
            "全片固定穿象牙白无标识衬衫、炭灰色直筒裤和黑色平底鞋，不佩戴首饰；"
            "自然妆容，无纹身、品牌标志或可读文字。"
        ),
        label="su-qing",
        asset_description="苏晴合成占位参考板：正面、四分之三侧面、半身和全身比例，纯技术夹具。",
    )
    gu = _character_bible(
        name="顾言",
        visual_description=(
            "32岁成年中国男性，短黑发，深棕色眼睛，轮廓清晰，身形修长，表达冷静；"
            "全片固定穿海军蓝无标识工作夹克、浅灰色衬衫和炭灰色长裤，不打领带；"
            "无胡须、首饰、品牌标志或可读文字。"
        ),
        label="gu-yan",
        asset_description="顾言合成占位参考板：正面、四分之三侧面、半身和全身比例，纯技术夹具。",
    )
    characters = tuple(sorted((su, gu), key=lambda item: item.character_id))
    by_name = {item.name: item for item in characters}

    office = _scene_bible(
        ordinal=0,
        name="建筑工作室深夜",
        visual_description=(
            "当代小型建筑工作室深夜，深灰水泥地面、浅木工作桌、玻璃门和落地窗，"
            "窗外为雨后虚化城市灯光；4300K冷白顶灯为主光，画面右后方有一盏2700K"
            "暖色台灯；空间整洁，无品牌、标识、屏幕内容或可读文字。"
        ),
        label="office-night",
        asset_description="建筑工作室深夜合成占位场景板，固定机位轴线与冷暖光方向。",
    )
    rooftop = _scene_bible(
        ordinal=1,
        name="同楼屋顶清晨",
        visual_description=(
            "同一建筑屋顶的清晨蓝调时刻，浅灰混凝土地面、腰高深灰女儿墙、远处"
            "无品牌城市天际线，暖色地平线位于画面右后方；无广告牌、车辆、其他人物"
            "或可读文字。"
        ),
        label="rooftop-dawn",
        asset_description="同楼屋顶清晨合成占位场景板，固定女儿墙安全线、天际线与光向。",
    )
    scenes = (office, rooftop)

    dialogue_rows = (
        (
            0,
            office.scene_id,
            by_name["苏晴"].character_id,
            "辞职信在桌上。天亮前，我就走。",
            6800,
            11600,
        ),
        (1, office.scene_id, by_name["顾言"].character_id, "我不同意。", 14000, 15600),
        (
            2,
            office.scene_id,
            by_name["苏晴"].character_id,
            "项目都停了，你拿什么留我？",
            20900,
            24800,
        ),
        (3, office.scene_id, by_name["顾言"].character_id, "不是留你。跟我上天台。", 28900, 32600),
        (
            4,
            rooftop.scene_id,
            by_name["顾言"].character_id,
            "三个月前，我把你的方案投进了城南改造终审。",
            36900,
            41800,
        ),
        (5, rooftop.scene_id, by_name["苏晴"].character_id, "你没问过我。", 44100, 46100),
        (
            6,
            rooftop.scene_id,
            by_name["顾言"].character_id,
            "所以今天不是替你决定，是请你自己选。",
            50900,
            55600,
        ),
        (
            7,
            rooftop.scene_id,
            by_name["顾言"].character_id,
            "合伙人，或者自由建筑师。",
            58900,
            62200,
        ),
        (
            8,
            rooftop.scene_id,
            by_name["苏晴"].character_id,
            "辞职信照旧。明天，我会以合伙人的身份回来。",
            65700,
            70400,
        ),
    )
    dialogue = tuple(
        _dialogue(
            ordinal=ordinal,
            scene_id=scene_id,
            character_id=character_id,
            text=text,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        for ordinal, scene_id, character_id, text, start_ms, end_ms in dialogue_rows
    )
    line_ids = tuple(item.line_id for item in dialogue)
    su_id = by_name["苏晴"].character_id
    gu_id = by_name["顾言"].character_id
    wardrobe = {
        su_id: "象牙白无标识衬衫、炭灰色直筒裤、黑色平底鞋、黑色低马尾",
        gu_id: "海军蓝无标识工作夹克、浅灰色衬衫、炭灰色长裤",
    }

    shot_rows: tuple[dict[str, object], ...] = (
        dict(
            scene_id=office.scene_id,
            narrative="辞职信落在桌上，在解释原因之前形成钩子。",
            visual_direction="高机位静态近景；苏晴右手将奶油色信封放在浅木桌左前方，脸在浅景深背景中仍可辨认。",
            emotions={su_id: "克制、疲惫，但决定已经做出，不哭泣"},
            action="右手放下信封，停顿半秒后收回",
            size=CreativeShotSize.CLOSE_UP,
            angle=CreativeCameraAngle.HIGH_ANGLE,
            movement=CreativeCameraMovement.STATIC,
            props=("cream-envelope",),
            continuity="苏晴位于画面左侧；信封长边平行桌沿，最终停在桌面左前部。",
            start=0,
            duration=6000,
            chars=(su_id,),
            lines=(),
        ),
        dict(
            scene_id=office.scene_id,
            narrative="苏晴平静宣布离开，建立核心冲突。",
            visual_direction="眼平静态中近景；苏晴在画面左侧，信封作前景，从信封抬眼望向右侧门口并说完对白。",
            emotions={su_id: "平静外表下的失望，尾句坚定"},
            action="看信封后抬眼望向右侧门口并说完对白",
            size=CreativeShotSize.MEDIUM_CLOSE_UP,
            angle=CreativeCameraAngle.EYE_LEVEL,
            movement=CreativeCameraMovement.STATIC,
            props=("cream-envelope",),
            continuity="延续镜头0的脸、发型、服装、屏幕方向和桌上信封位置。",
            start=6000,
            duration=7000,
            chars=(su_id,),
            lines=(line_ids[0],),
        ),
        dict(
            scene_id=office.scene_id,
            narrative="顾言进门，以一句拒绝打断苏晴的决定。",
            visual_direction="眼平中景缓慢推进；顾言从右后玻璃门迈入一步后停下，左手垂持蓝色文件夹，苏晴背肩作左前景锚点。",
            emotions={gu_id: "错愕后压住焦急", su_id: "戒备，不回头"},
            action="顾言入门、停步并说话，苏晴保持静止",
            size=CreativeShotSize.MEDIUM,
            angle=CreativeCameraAngle.EYE_LEVEL,
            movement=CreativeCameraMovement.DOLLY,
            props=("blue-partner-folder", "cream-envelope"),
            continuity="苏晴保持画面左侧；顾言从右侧进入，蓝色文件夹始终在左手。",
            start=13000,
            duration=7000,
            chars=tuple(sorted((su_id, gu_id))),
            lines=(line_ids[1],),
        ),
        dict(
            scene_id=office.scene_id,
            narrative="苏晴转身质问，迫使顾言面对停摆的项目。",
            visual_direction="顾言肩后眼平静态中近景；苏晴转身约45度质问并保持目光，顾言闭口倾听。",
            emotions={su_id: "压抑的愤怒与失望", gu_id: "克制倾听，不辩解"},
            action="苏晴转身、质问并停住，顾言闭口",
            size=CreativeShotSize.MEDIUM_CLOSE_UP,
            angle=CreativeCameraAngle.EYE_LEVEL,
            movement=CreativeCameraMovement.STATIC,
            props=("blue-partner-folder", "cream-envelope"),
            continuity="不越180度轴线；信封仍在桌上，文件夹仍在顾言左手。",
            start=20000,
            duration=8000,
            chars=tuple(sorted((su_id, gu_id))),
            lines=(line_ids[2],),
        ),
        dict(
            scene_id=office.scene_id,
            narrative="顾言不解释，只邀请苏晴到天台看答案。",
            visual_direction="眼平双人中景轻微推进；顾言在右侧说完转向门口，苏晴随后用右手拿起信封。",
            emotions={gu_id: "坦诚、急切但不施压", su_id: "不信任中出现轻微动摇"},
            action="顾言说话后转身，苏晴右手取信封",
            size=CreativeShotSize.MEDIUM,
            angle=CreativeCameraAngle.EYE_LEVEL,
            movement=CreativeCameraMovement.DOLLY,
            props=("blue-partner-folder", "cream-envelope"),
            continuity="对白、转身、取信封依次发生；顾言左手持文件夹，苏晴右手持信封进入下一场。",
            start=28000,
            duration=8000,
            chars=tuple(sorted((su_id, gu_id))),
            lines=(line_ids[3],),
        ),
        dict(
            scene_id=rooftop.scene_id,
            narrative="屋顶清晨，顾言揭示自己已把苏晴的方案送入终审。",
            visual_direction="眼平广角建立镜头缓慢推进；顾言右、苏晴左，两人距女儿墙至少1.5米，分别持文件夹与信封。",
            emotions={gu_id: "谨慎揭示事实并准备承担后果", su_id: "警惕观察"},
            action="两人停下，顾言面对苏晴说话",
            size=CreativeShotSize.WIDE,
            angle=CreativeCameraAngle.EYE_LEVEL,
            movement=CreativeCameraMovement.DOLLY,
            props=("blue-partner-folder", "cream-envelope"),
            continuity="场景切换后角色身份、服装、左右位置与双道具手别完全延续；人物保持安全距离。",
            start=36000,
            duration=7000,
            chars=tuple(sorted((su_id, gu_id))),
            lines=(line_ids[4],),
        ),
        dict(
            scene_id=rooftop.scene_id,
            narrative="苏晴对未经同意的决定提出短促异议。",
            visual_direction="眼平静态近景；苏晴先看向画外右侧文件夹，再看顾言，克制说出短句。",
            emotions={su_id: "意外、被冒犯，同时产生好奇"},
            action="轻吸气、说短句，右手信封保持不动",
            size=CreativeShotSize.CLOSE_UP,
            angle=CreativeCameraAngle.EYE_LEVEL,
            movement=CreativeCameraMovement.STATIC,
            props=("blue-partner-folder", "cream-envelope"),
            continuity="屋顶光向与背景连续；信封仍在苏晴右手，画外文件夹不得出现在她手中。",
            start=43000,
            duration=7000,
            chars=(su_id,),
            lines=(line_ids[5],),
        ),
        dict(
            scene_id=rooftop.scene_id,
            narrative="顾言将选择权归还给苏晴，而不是替她决定。",
            visual_direction="苏晴肩后眼平静态中近景；顾言把文件夹放上内侧平台，左手扶边、右手打开，页面无字。",
            emotions={gu_id: "坦诚、带歉意、愿意承担后果", su_id: "逐渐理解但仍克制"},
            action="顾言放下并打开文件夹后说话，苏晴不触碰",
            size=CreativeShotSize.MEDIUM_CLOSE_UP,
            angle=CreativeCameraAngle.EYE_LEVEL,
            movement=CreativeCameraMovement.STATIC,
            props=("blue-partner-folder", "cream-envelope"),
            continuity="顾言完成文件夹由左手到平台的状态变化；苏晴不触碰，信封仍在右手。",
            start=50000,
            duration=8000,
            chars=tuple(sorted((su_id, gu_id))),
            lines=(line_ids[6],),
        ),
        dict(
            scene_id=rooftop.scene_id,
            narrative="顾言给出合伙人或自由建筑师两个选项，并彻底撤回手。",
            visual_direction="眼平静态中广角双人镜头；顾言合上文件夹，推至中点并完全撤手，苏晴只看不碰。",
            emotions={gu_id: "释然，把选择权交出", su_id: "犹豫开始转为坚定"},
            action="顾言说完选项、推文件夹并撤手，苏晴只看文件夹",
            size=CreativeShotSize.MEDIUM_WIDE,
            angle=CreativeCameraAngle.EYE_LEVEL,
            movement=CreativeCameraMovement.STATIC,
            props=("blue-partner-folder", "cream-envelope"),
            continuity="文件夹最终静止在两人中点且无人触碰；不换位、不越轴、不靠近女儿墙。",
            start=58000,
            duration=7000,
            chars=tuple(sorted((su_id, gu_id))),
            lines=(line_ids[7],),
        ),
        dict(
            scene_id=rooftop.scene_id,
            narrative="苏晴保留辞职决定，却以合伙人身份选择回来。",
            visual_direction="眼平中近景缓慢推进；苏晴左手拿起文件夹、右手保留信封，说完望向晨光，顾言右肩作锚。",
            emotions={su_id: "坚定、释然，笑意极轻", gu_id: "松一口气但不抢戏"},
            action="苏晴左手拿文件夹后说话，顾言闭口静听",
            size=CreativeShotSize.MEDIUM_CLOSE_UP,
            angle=CreativeCameraAngle.EYE_LEVEL,
            movement=CreativeCameraMovement.DOLLY,
            props=("blue-partner-folder", "cream-envelope"),
            continuity="苏晴左手文件夹、右手信封；顾言保持右侧、闭口，70400ms后稳定保持至72000ms。",
            start=65000,
            duration=7000,
            chars=tuple(sorted((su_id, gu_id))),
            lines=(line_ids[8],),
        ),
    )
    shots = tuple(
        CreativeSampleShotSpec(
            ordinal=ordinal,
            scene_id=cast(str, row["scene_id"]),
            narrative=cast(str, row["narrative"]),
            visual_direction=cast(str, row["visual_direction"]),
            emotion_by_character=cast(dict[str, str], row["emotions"]),
            action=cast(str, row["action"]),
            shot_size=cast(CreativeShotSize, row["size"]),
            camera_angle=cast(CreativeCameraAngle, row["angle"]),
            camera_movement=cast(CreativeCameraMovement, row["movement"]),
            wardrobe_by_character={
                character_id: wardrobe[character_id]
                for character_id in cast(tuple[str, ...], row["chars"])
            },
            props=cast(tuple[str, ...], row["props"]),
            continuity_notes=cast(str, row["continuity"]),
            start_ms=cast(int, row["start"]),
            duration_ms=cast(int, row["duration"]),
            character_ids=cast(tuple[str, ...], row["chars"]),
            dialogue_line_ids=cast(tuple[str, ...], row["lines"]),
        )
        for ordinal, row in enumerate(shot_rows)
    )
    return CreativeSampleSpec(
        title="辞职信照旧",
        seed=20260816,
        duration_ms=72000,
        character_bibles=characters,
        scene_bibles=scenes,
        dialogue=dialogue,
        shots=shots,
    )


def _active_asset_requirements(spec: CreativeSampleSpec) -> tuple[PilotAssetRequirement, ...]:
    path_by_name = {
        "苏晴": "assets/characters/su-qing/v1.png",
        "顾言": "assets/characters/gu-yan/v1.png",
        "建筑工作室深夜": "assets/scenes/office-night/v1.png",
        "同楼屋顶清晨": "assets/scenes/rooftop-dawn/v1.png",
    }
    label_by_name = {
        "苏晴": "su-qing",
        "顾言": "gu-yan",
        "建筑工作室深夜": "office-night",
        "同楼屋顶清晨": "rooftop-dawn",
    }
    rows: list[PilotAssetRequirement] = []
    bibles: tuple[tuple[Literal["CHARACTER", "SCENE"], CharacterBible | SceneBible], ...] = (
        *(("CHARACTER", item) for item in spec.character_bibles),
        *(("SCENE", item) for item in spec.scene_bibles),
    )
    for subject_kind, bible in bibles:
        version = next(
            item for item in bible.asset_versions if item.id == bible.active_asset_version_id
        )
        subject_id = bible.character_id if isinstance(bible, CharacterBible) else bible.scene_id
        label = label_by_name[bible.name]
        path = path_by_name[bible.name]
        rows.append(
            PilotAssetRequirement(
                requirement_id=stable_id(
                    "pilot_asset_requirement",
                    {
                        "asset_version_id": version.id,
                        "intended_logical_path": path,
                        "placeholder_sha256": version.content_sha256,
                        "subject_id": subject_id,
                        "subject_kind": subject_kind,
                    },
                ),
                subject_kind=subject_kind,
                subject_id=subject_id,
                asset_version_id=version.id,
                intended_logical_path=path,
                placeholder_label=label,
                placeholder_sha256=version.content_sha256,
                visual_requirements=(
                    "未来真实文件必须来自单独审查的精确本地字节并冻结新内容摘要。",
                    "不得包含真实私密身份、品牌、可读个人信息或未授权第三方作品。",
                    "当前摘要仅绑定2x2合成占位PNG，不具备真实生成资格。",
                ),
            )
        )
    return tuple(sorted(rows, key=lambda item: item.asset_version_id))


def _audio_requirements(spec: CreativeSampleSpec) -> tuple[PilotAudioRequirement, ...]:
    by_character = {item.character_id: item.name for item in spec.character_bibles}
    rows: list[PilotAudioRequirement] = []
    for ordinal, line in enumerate(spec.dialogue):
        intended_path = f"audio/voices/{ordinal:02d}.wav"
        rows.append(
            PilotAudioRequirement(
                requirement_id=stable_id(
                    "pilot_audio_requirement",
                    {
                        "end_ms": line.end_ms,
                        "exact_text": line.text,
                        "intended_logical_path": intended_path,
                        "kind": "VOICE",
                        "line_id": line.line_id,
                        "start_ms": line.start_ms,
                    },
                ),
                kind="VOICE",
                line_id=line.line_id,
                start_ms=line.start_ms,
                end_ms=line.end_ms,
                exact_text=line.text,
                direction=(
                    f"{by_character[line.character_id]}成年自然中低声区，克制清晰；严格匹配原文，"
                    "不得添加说话人标签或改写。"
                ),
                intended_logical_path=intended_path,
            )
        )
    bgm_path = "audio/bgm/background.wav"
    rows.append(
        PilotAudioRequirement(
            requirement_id=stable_id(
                "pilot_audio_requirement",
                {
                    "end_ms": 72000,
                    "exact_text": None,
                    "intended_logical_path": bgm_path,
                    "kind": "BGM",
                    "line_id": None,
                    "start_ms": 0,
                },
            ),
            kind="BGM",
            start_ms=0,
            end_ms=72000,
            direction=(
                "无歌词稀疏钢琴起始，36秒前低脉冲，36秒后暖色铺底，58秒后克制解决；"
                "必须单独保留版权审查记录。"
            ),
            intended_logical_path=bgm_path,
        )
    )
    return tuple(rows)


def _shot_plans(
    spec: CreativeSampleSpec, compilation: CreativeSampleCompilation
) -> tuple[PilotShotPlan, ...]:
    line_by_id = {item.line_id: item for item in spec.dialogue}
    scene_by_id = {item.scene_id: item for item in spec.scene_bibles}
    character_by_id = {item.character_id: item for item in spec.character_bibles}
    reject_rows = (
        ("静态或纯色卡片", "钩子晚于2秒", "手或信封畸形", "可读文字、额外人物、标志或水印"),
        ("脸、头发、服装或眼睛闪烁", "口型不匹配", "信封移动", "画外说话人被错误渲染"),
        ("额外人物", "门或文件夹瞬移", "文件夹换手", "苏晴口型运动或越轴"),
        ("两人同时说话", "视线错误或越轴", "身份漂移", "前景肩部变成第三人"),
        ("手部相交", "提前拿取道具", "道具换手", "角色换位或错误口型"),
        ("靠近或跨越屋顶边缘", "人物或道具丢失", "错误天气或场景替换", "天际线可读标识"),
        ("夸张哭泣", "身份漂移", "背景光向反转", "信封换手或文件夹误入苏晴手中"),
        ("生成文档文字", "页面或手畸形", "文件夹变色", "苏晴提前抓取或威胁姿态"),
        ("同时交接或手融合", "文件夹瞬移", "顾言未撤手", "越轴或不安全边缘位置"),
        ("道具缺失或换手", "两人同时说话", "夸张笑容或身份发型漂移", "手融合或生成标题"),
    )
    first_pass_rows = (
        ("动作在前2秒完成", "苏晴身份和手部解剖稳定", "信封最终位置正确"),
        ("苏晴身份稳定", "整句清晰完整", "道具与屏幕方向延续镜头0"),
        ("两人身份稳定", "顾言为唯一说话人", "蓝色文件夹始终在顾言左手"),
        ("对抗关系清晰", "仅苏晴说话", "脸、空间和道具连续"),
        ("对白、取信封和转身为三个独立节拍", "跨场道具状态精确成立"),
        ("屋顶场景立即可辨", "角色、服装与道具跨场保持", "人物始终在安全线内"),
        ("反应自然且身份可辨", "声音清楚", "屋顶边界连续"),
        ("文件夹完整转移至平台", "顾言为唯一说话人", "道歉与归还选择权清晰"),
        ("两个选项清楚", "文件夹最终静止在中点", "双方均不触碰文件夹"),
        ("取文件夹与对白顺序正确", "双道具手别正确", "身份稳定且结尾保持干净"),
    )
    bgm_rows = (
        "克制室内环境音与单个钢琴音；6000ms硬切。",
        "稀疏钢琴维持最低音量，语音优先。",
        "引入安静低脉冲，不遮挡短对白。",
        "低脉冲轻微抬升，仍保持对白清晰。",
        "对白后留动作空间，36000ms硬切屋顶。",
        "暖色铺底展开，但不得压对白。",
        "对白下压低音乐，保持短句清晰。",
        "只保留柔和铺底，语气非胁迫。",
        "开始和声解决，选项间保留自然停顿。",
        "70400ms后解决和弦，稳定画面保持到72000ms。",
    )
    plans: list[PilotShotPlan] = []
    for source, compiled in zip(spec.shots, compilation.pir.shots, strict=True):
        scene = scene_by_id[source.scene_id]
        required = [scene.active_asset_version_id]
        required.extend(
            character_by_id[item].active_asset_version_id for item in source.character_ids
        )
        subtitle = tuple(line_by_id[item].text for item in source.dialogue_line_ids)
        plans.append(
            PilotShotPlan(
                shot_id=compiled.id,
                ordinal=source.ordinal,
                start_ms=source.start_ms,
                duration_ms=source.duration_ms,
                scene_id=source.scene_id,
                character_ids=source.character_ids,
                dialogue_line_ids=source.dialogue_line_ids,
                visual_goal=f"{source.narrative} {source.visual_direction}",
                unacceptable_defects=reject_rows[source.ordinal],
                required_asset_version_ids=tuple(sorted(required)),
                voice_line_ids=source.dialogue_line_ids,
                subtitle_text=subtitle,
                bgm_direction=bgm_rows[source.ordinal],
                post_requirements=(
                    "只使用硬切和固定25fps/1080x1920画幅，不做生成式插帧或远程特效。",
                    "对白字幕必须逐字来自冻结DialogueLine并位于精确主时钟区间。",
                    "输出不得保留输入元数据、章节、本地路径、标志或水印。",
                ),
                first_pass_criteria=first_pass_rows[source.ordinal],
                scene_continuity_required=source.ordinal not in {0, 5},
            )
        )
    return tuple(plans)


def _failure_taxonomy() -> tuple[PilotFailureClass, ...]:
    rows = {
        "artifact.duplicate_media": ("两个镜头使用未声明的相同最终字节", "STOP"),
        "artifact.extra_person": ("出现未声明人物或人物状前景", "拒收媒体"),
        "artifact.face": ("面部变形、闪烁或时序不稳定", "判定artifact-free失败"),
        "artifact.hand": ("手部变形、融合或道具交互不可能", "判定artifact-free失败"),
        "artifact.static_or_placeholder": ("静态、纯色或夹具冒充内容", "STOP"),
        "artifact.text_or_watermark": ("出现非预期可读文字、标志或水印", "拒收媒体"),
        "audio.bgm_rights": ("音乐版权缺失、不明或过期", "STOP并进入HUMAN_GATE"),
        "audio.subtitle_timing": ("字幕文字或时间偏离冻结对白", "技术QC失败"),
        "audio.voice_quality": ("对白不可懂、成年角色不符或显著生硬", "首遍可用失败"),
        "content.character_drift": ("脸、头发、年龄、体型或角色发生漂移", "角色连续性失败"),
        "content.dialogue_lipsync": ("说话人错误、额外口型或阻塞同步失败", "镜头意图失败"),
        "content.identity_break": ("声明角色不再可辨认为同一人", "STOP并进入HUMAN_GATE"),
        "content.prop_drift": ("信封或文件夹状态、颜色、位置或手别错误", "意图或连续性失败"),
        "content.scene_drift": ("地点、光向或空间轴线错误变化", "场景连续性失败"),
        "content.shot_intent": ("冻结叙事、动作或机位意图未表达", "镜头意图失败"),
        "content.wardrobe_drift": ("固定服装变化、变色或出现标志", "角色连续性失败"),
        "provenance.unverified": ("来源无法绑定保留的本地记录", "STOP"),
        "review.disagreement": ("两个复核人对任一评分声明不一致", "记录并进入HUMAN_GATE"),
        "rights.unverified": ("内容、肖像或隐私权利不完整", "STOP并进入HUMAN_GATE"),
        "technical.duration": ("媒体或成片时长偏离精确主时钟", "技术QC失败"),
        "technical.frame": ("画幅、尺寸、帧率、像素格式或可解码性错误", "技术QC失败"),
    }
    return tuple(
        PilotFailureClass(code=code, meaning=meaning, disposition=disposition)
        for code, (meaning, disposition) in sorted(rows.items())
    )


def _build_pack(
    spec: CreativeSampleSpec, compilation: CreativeSampleCompilation
) -> CreativeSamplePilotPack:
    asset_requirements = _active_asset_requirements(spec)
    active_assets = tuple(item.asset_version_id for item in asset_requirements)
    audio_requirements = _audio_requirements(spec)
    rights_rows = (
        *(
            PilotRightsReviewRow(
                subject_kind="IMAGE_ASSET",
                subject_id=item.asset_version_id,
                intended_logical_path=item.intended_logical_path,
            )
            for item in asset_requirements
        ),
        *(
            PilotRightsReviewRow(
                subject_kind=item.kind,
                subject_id=(
                    item.line_id if item.kind == "VOICE" and item.line_id else item.requirement_id
                ),
                intended_logical_path=item.intended_logical_path,
            )
            for item in audio_requirements
        ),
    )
    shot_ids = tuple(item.id for item in compilation.pir.shots)
    shot_plans = _shot_plans(spec, compilation)
    plan_by_shot = {item.shot_id: item for item in shot_plans}
    character_ids_by_shot = {
        shot.id: tuple(sorted(item.character_id for item in shot.character_assets))
        for shot in compilation.pir.shots
    }
    reviews = tuple(
        PilotShotReviewTemplate(
            shot_id=shot_id,
            role=role,
            scene_continuity_required=plan_by_shot[shot_id].scene_continuity_required,
            character_continuity=tuple(
                PilotCharacterContinuityReview(character_id=item)
                for item in character_ids_by_shot[shot_id]
            ),
        )
        for shot_id in shot_ids
        for role in cast(tuple[Literal["EDITOR", "INDEPENDENT"], ...], ("EDITOR", "INDEPENDENT"))
    )
    shot_work_records = tuple(PilotShotWorkRecord(shot_id=item) for item in shot_ids)
    stop_conditions = (
        "缺少独立复核、版权、来源或隐私审查时停止。",
        "规格、素材、内容摘要、运行发布、队列、账本或部署绑定漂移时停止。",
        "任何关键身份断裂、安全或合规问题出现时停止。",
        "未解决的双人复核分歧出现时停止。",
        "请求数达到20、成本达到CNY450或任一镜头达到Attempt 2时停止。",
        "Provider明确拒绝、远端失败或返回结构不合格时停止且不得自动换供应商。",
        "提交、事务提交结果或task ID持久化结果不明时进入SUBMISSION_UNKNOWN与HUMAN_GATE。",
        "任何部分账本行、所有权冲突、过期证据或技术闭包验证失败时停止。",
    )
    delivery_profile = PilotDeliveryProfile()
    metrics_template = PilotMetricsTemplate()
    failure_taxonomy = _failure_taxonomy()
    synthetic_rehearsal = PilotSyntheticRehearsal()
    provider_batch_plan = PilotProviderBatchPlan(
        exact_shot_ids=shot_ids,
        stop_conditions=stop_conditions,
    )
    canonical: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-pilot-pack",
        "profile": PILOT_PROFILE,
        "title": "辞职信照旧",
        "sample_spec_sha256": _canonical_contract_sha256(spec),
        "compilation_id": compilation.id,
        "ordered_shot_ids": shot_ids,
        "active_asset_version_ids": active_assets,
        "asset_requirements": tuple(item.model_dump(mode="json") for item in asset_requirements),
        "audio_requirements": tuple(item.model_dump(mode="json") for item in audio_requirements),
        "shot_plans": tuple(item.model_dump(mode="json") for item in shot_plans),
        "delivery_profile": delivery_profile.model_dump(mode="json"),
        "rights_review_rows": tuple(item.model_dump(mode="json") for item in rights_rows),
        "shot_review_templates": tuple(item.model_dump(mode="json") for item in reviews),
        "shot_work_records": tuple(item.model_dump(mode="json") for item in shot_work_records),
        "metrics_template": metrics_template.model_dump(mode="json"),
        "failure_taxonomy": tuple(item.model_dump(mode="json") for item in failure_taxonomy),
        "synthetic_rehearsal": synthetic_rehearsal.model_dump(mode="json"),
        "provider_batch_plan": provider_batch_plan.model_dump(mode="json"),
    }
    pack_id = CreativeSamplePilotPack.derive_id(canonical)
    return CreativeSamplePilotPack(
        pack_id=pack_id,
        sample_spec_sha256=_canonical_contract_sha256(spec),
        compilation_id=compilation.id,
        ordered_shot_ids=shot_ids,
        active_asset_version_ids=active_assets,
        asset_requirements=asset_requirements,
        audio_requirements=audio_requirements,
        shot_plans=shot_plans,
        delivery_profile=delivery_profile,
        rights_review_rows=rights_rows,
        shot_review_templates=reviews,
        shot_work_records=shot_work_records,
        metrics_template=metrics_template,
        failure_taxonomy=failure_taxonomy,
        synthetic_rehearsal=synthetic_rehearsal,
        provider_batch_plan=provider_batch_plan,
    )


def build_creative_sample_pilot_documents() -> tuple[CreativeSampleSpec, CreativeSamplePilotPack]:
    """Build the exact deterministic, design-only Pilot specification and pack."""
    spec = _build_spec()
    compilation = compile_creative_sample(spec)
    pack = _build_pack(spec, compilation)
    _validate_cross_bindings(spec, compilation, pack)
    return spec, pack


def _validate_cross_bindings(
    spec: CreativeSampleSpec,
    compilation: CreativeSampleCompilation,
    pack: CreativeSamplePilotPack,
) -> None:
    if spec != _build_spec():
        raise CreativePilotError("Pilot specification differs from the frozen v1 content design")
    if spec.title != "辞职信照旧" or spec.seed != 20260816 or spec.duration_ms != 72000:
        raise CreativePilotError("Pilot specification identity or duration drifted")
    if len(spec.character_bibles) != 2 or len(spec.scene_bibles) != 2 or len(spec.shots) != 10:
        raise CreativePilotError("Pilot specification shape drifted")
    if tuple((item.start_ms, item.duration_ms) for item in spec.shots) != (
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
    ):
        raise CreativePilotError("Pilot shot clock drifted")
    rebuilt = compile_creative_sample(spec)
    if compilation != rebuilt:
        raise CreativePilotError("Pilot compilation is not the exact deterministic rebuild")
    if pack.sample_spec_sha256 != _canonical_contract_sha256(spec):
        raise CreativePilotError("Pilot Pack does not bind the exact sample specification")
    if pack.compilation_id != compilation.id:
        raise CreativePilotError("Pilot Pack compilation identity drifted")
    if pack.ordered_shot_ids != tuple(item.id for item in compilation.pir.shots):
        raise CreativePilotError("Pilot Pack shot closure drifted")
    active_versions = tuple(
        sorted(
            (
                *(item.active_asset_version_id for item in spec.character_bibles),
                *(item.active_asset_version_id for item in spec.scene_bibles),
            )
        )
    )
    if pack.active_asset_version_ids != active_versions:
        raise CreativePilotError("Pilot Pack active asset closure drifted")
    expected_pack = _build_pack(spec, compilation)
    if pack != expected_pack:
        raise CreativePilotError("Pilot Pack content differs from the frozen v1 design")


def _reject_constant(value: str) -> None:
    raise CreativePilotError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CreativePilotError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _load_document(path: Path, model: type[BaseModel]) -> BaseModel:
    try:
        declared = validate_regular_media_path(path).lstat()
        if declared.st_size > PILOT_JSON_LIMIT:
            raise CreativePilotError("Pilot JSON exceeds the 1 MiB limit")
        data, _ = read_regular_media(path)
    except CreativeMediaError as exc:
        raise CreativePilotError(str(exc)) from exc
    if len(data) > PILOT_JSON_LIMIT:
        raise CreativePilotError("Pilot JSON exceeds the 1 MiB limit")
    if data.startswith(b"\xef\xbb\xbf"):
        raise CreativePilotError("Pilot JSON must not contain a UTF-8 BOM")
    try:
        text = data.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativePilotError("Pilot JSON is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise CreativePilotError("Pilot JSON must contain one object")
    try:
        parsed = model.model_validate_json(data, strict=True)
    except ValueError as exc:
        raise CreativePilotError("Pilot JSON does not match its strict contract") from exc
    if data != _canonical_json_bytes(parsed):
        raise CreativePilotError("Pilot JSON bytes are not canonical sorted UTF-8")
    return parsed


def load_creative_sample_pilot_pack(root: Path) -> ValidatedCreativeSamplePilotPack:
    """Load the exact committed Pilot Pack without network, Provider or authority access."""
    try:
        absolute = validate_local_path(root, must_exist=True)
    except CreativeMediaError as exc:
        raise CreativePilotError(str(exc)) from exc
    if not absolute.is_dir():
        raise CreativePilotError("Pilot Pack root must be a local directory")
    actual = {item.name for item in absolute.iterdir()}
    if actual != PILOT_FILES:
        raise CreativePilotError("Pilot Pack directory does not have the exact two-file closure")
    spec_document = cast(
        CreativeSamplePilotSpecDocument,
        _load_document(absolute / PILOT_SPEC_NAME, CreativeSamplePilotSpecDocument),
    )
    spec = spec_document.spec
    pack = cast(
        CreativeSamplePilotPack,
        _load_document(absolute / PILOT_PACK_NAME, CreativeSamplePilotPack),
    )
    compilation = compile_creative_sample(spec)
    _validate_cross_bindings(spec, compilation, pack)
    return ValidatedCreativeSamplePilotPack(
        root=absolute,
        spec=spec,
        compilation=compilation,
        pack=pack,
    )


def write_creative_sample_pilot_documents(root: Path) -> ValidatedCreativeSamplePilotPack:
    """Publish the deterministic two-file Pilot Pack to a new local directory."""
    spec, pack = build_creative_sample_pilot_documents()
    try:
        absolute = validate_local_path(root, must_exist=False)
        parent = validate_local_path(absolute.parent, must_exist=True)
    except CreativeMediaError as exc:
        raise CreativePilotError(str(exc)) from exc
    if absolute.exists() or os.path.lexists(absolute):
        raise CreativePilotError("Pilot Pack output must be a new directory")
    stage = parent / f".{absolute.name}.stage"
    if stage.exists() or os.path.lexists(stage):
        raise CreativePilotError("Pilot Pack staging directory already exists")
    created: list[Path] = []
    try:
        stage.mkdir()
        spec_document = CreativeSamplePilotSpecDocument(spec=spec)
        for name, value in ((PILOT_SPEC_NAME, spec_document), (PILOT_PACK_NAME, pack)):
            target = stage / name
            with target.open("xb") as handle:
                handle.write(_canonical_json_bytes(value))
                handle.flush()
                os.fsync(handle.fileno())
            created.append(target)
        load_creative_sample_pilot_pack(stage)
        stage.rename(absolute)
    except BaseException:
        for target in reversed(created):
            if target.exists():
                target.unlink()
        if stage.exists():
            stage.rmdir()
        raise
    return load_creative_sample_pilot_pack(absolute)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a non-operational Pilot Pack")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    loaded = load_creative_sample_pilot_pack(args.root)
    print(
        json.dumps(
            {
                "pack_id": loaded.pack.pack_id,
                "sample_id": loaded.compilation.id,
                "state": loaded.pack.provider_batch_plan.state,
                "posts_allowed": loaded.pack.provider_batch_plan.posts_allowed,
                "synthetic_decision": loaded.pack.synthetic_rehearsal.expected_decision,
                "provider_requests": loaded.pack.synthetic_rehearsal.provider_requests,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


__all__ = [
    "CreativePilotError",
    "CreativeSamplePilotPack",
    "CreativeSamplePilotSpecDocument",
    "ValidatedCreativeSamplePilotPack",
    "build_creative_sample_pilot_documents",
    "load_creative_sample_pilot_pack",
    "synthetic_placeholder_png_bytes",
    "write_creative_sample_pilot_documents",
]


if __name__ == "__main__":
    raise SystemExit(main())
