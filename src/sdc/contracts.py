"""Versioned, immutable public contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Final, Literal
from unicodedata import normalize
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION: Final[Literal["1.0.0"]] = "1.0.0"
CREATIVE_SCHEMA_VERSION: Final[Literal["2.0.0"]] = "2.0.0"
CANARY_PROVIDER: Final[Literal["volcengine_ark"]] = "volcengine_ark"
CANARY_MODEL: Final[Literal["doubao-seedance-2-0-260128"]] = "doubao-seedance-2-0-260128"
ARK_CANARY_ENTITLEMENT_PROFILE: Final[Literal["ark-canary-entitlement-v1"]] = (
    "ark-canary-entitlement-v1"
)
ARK_CANARY_SERVICE: Final[Literal["ark-video-generation"]] = "ark-video-generation"
ARK_CANARY_REGION: Final[Literal["cn-beijing"]] = "cn-beijing"
ARK_CANARY_OPERATION: Final[Literal["contents.generations.tasks.create"]] = (
    "contents.generations.tasks.create"
)
ARK_CANARY_ENTITLEMENT_SOURCE_URL: Final[
    Literal["https://console.volcengine.com/ark/region:cn-beijing/openManagement"]
] = "https://console.volcengine.com/ark/region:cn-beijing/openManagement"
EVIDENCE_MAX_OBJECT_BYTES: Final = 64 * 1024 * 1024
EVIDENCE_MAX_BUNDLE_BYTES: Final = 512 * 1024 * 1024
Ms = Annotated[int, Field(ge=0)]

_SHANGHAI_TIMEZONE = timezone(timedelta(hours=8))
_ENTITLEMENT_MAX_VALIDITY = timedelta(hours=4)


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION


class ContractV2(BaseModel):
    """Independent v2 contract family; released v1 contracts remain byte-stable."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["2.0.0"] = CREATIVE_SCHEMA_VERSION


class StoryBeat(Contract):
    text: str = Field(min_length=1)
    duration_ms: Annotated[int, Field(gt=0)] = 2000


class StoryInput(Contract):
    title: str = Field(min_length=1)
    beats: tuple[StoryBeat, ...] = Field(min_length=1)
    seed: int = 1


class NIRScene(Contract):
    id: str
    ordinal: int
    narrative: str
    duration_ms: Annotated[int, Field(gt=0)]


class NIR(Contract):
    id: str
    title: str
    scenes: tuple[NIRScene, ...]


class PIRShot(Contract):
    id: str
    scene_id: str
    ordinal: int
    prompt: str
    start_ms: Ms
    duration_ms: Annotated[int, Field(gt=0)]


class PIR(Contract):
    id: str
    shots: tuple[PIRShot, ...]


class AudioCue(Contract):
    id: str
    shot_id: str
    start_ms: Ms
    end_ms: Ms


class AudioMasterClock(Contract):
    id: str
    duration_ms: Ms
    sample_rate_hz: Literal[48000] = 48000
    cues: tuple[AudioCue, ...]


class GenerationJob(Contract):
    id: str
    shot_id: str
    prompt: str
    duration_ms: Annotated[int, Field(gt=0)]
    depends_on: tuple[str, ...] = ()
    idempotency_key: str
    max_attempts: Literal[2] = 2


class JobGraph(Contract):
    id: str
    jobs: tuple[GenerationJob, ...]


class AssemblyItem(Contract):
    job_id: str
    start_ms: Ms
    duration_ms: Annotated[int, Field(gt=0)]


class AssemblyPlan(Contract):
    id: str
    clock_id: str
    items: tuple[AssemblyItem, ...]


_PORTABLE_CREATIVE_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_LOWER_SHA256 = r"^[0-9a-f]{64}$"


def _creative_stable_id(kind: str, value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"{kind}_{hashlib.sha256(canonical.encode()).hexdigest()[:20]}"


class CharacterAssetVersion(Contract):
    """Portable, immutable reference to one approved character asset version."""

    id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    character_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    version: Annotated[int, Field(ge=1)]
    content_sha256: str = Field(pattern=_LOWER_SHA256)
    media_type: Literal["image/png"] = "image/png"
    approval_ref: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    visual_description: str = Field(min_length=1, max_length=4000)
    provenance: Literal["IMPORTED_APPROVED_MEDIA"] = "IMPORTED_APPROVED_MEDIA"

    @classmethod
    def derive_id(
        cls,
        *,
        character_id: str,
        version: int,
        content_sha256: str,
        media_type: Literal["image/png"],
        approval_ref: str,
        visual_description: str,
    ) -> str:
        return _creative_stable_id(
            "character_asset",
            {
                "approval_ref": approval_ref,
                "character_id": character_id,
                "content_sha256": content_sha256,
                "media_type": media_type,
                "provenance": "IMPORTED_APPROVED_MEDIA",
                "version": version,
                "visual_description": visual_description,
            },
        )

    @model_validator(mode="after")
    def validate_character_asset_id(self) -> CharacterAssetVersion:
        expected = self.derive_id(
            character_id=self.character_id,
            version=self.version,
            content_sha256=self.content_sha256,
            media_type=self.media_type,
            approval_ref=self.approval_ref,
            visual_description=self.visual_description,
        )
        if self.id != expected:
            raise ValueError(
                "character asset ID must derive from canonical content and bind its "
                "containing character"
            )
        return self


class CharacterBible(Contract):
    character_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    name: str = Field(min_length=1, max_length=128)
    visual_description: str = Field(min_length=1, max_length=4000)
    asset_versions: tuple[CharacterAssetVersion, ...] = Field(min_length=1)
    active_asset_version_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)

    @classmethod
    def derive_id(cls, *, name: str, visual_description: str) -> str:
        return _creative_stable_id(
            "character",
            {"name": name, "visual_description": visual_description},
        )

    @model_validator(mode="after")
    def validate_character_assets(self) -> CharacterBible:
        if self.character_id != self.derive_id(
            name=self.name,
            visual_description=self.visual_description,
        ):
            raise ValueError("character ID must derive from its canonical content")
        version_ids = tuple(item.id for item in self.asset_versions)
        versions = tuple(item.version for item in self.asset_versions)
        if len(version_ids) != len(set(version_ids)) or len(versions) != len(set(versions)):
            raise ValueError("character asset IDs and versions must be unique")
        if versions != tuple(sorted(versions)):
            raise ValueError("character asset versions must use ascending version order")
        if any(item.character_id != self.character_id for item in self.asset_versions):
            raise ValueError("character asset version must bind its containing character")
        if self.active_asset_version_id not in version_ids:
            raise ValueError("active character asset version must exist in the bible")
        return self


class SceneAssetVersion(Contract):
    """Portable, immutable reference to one approved scene asset version."""

    id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    scene_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    version: Annotated[int, Field(ge=1)]
    content_sha256: str = Field(pattern=_LOWER_SHA256)
    media_type: Literal["image/png"] = "image/png"
    approval_ref: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    visual_description: str = Field(min_length=1, max_length=4000)
    provenance: Literal["IMPORTED_APPROVED_MEDIA"] = "IMPORTED_APPROVED_MEDIA"

    @classmethod
    def derive_id(
        cls,
        *,
        scene_id: str,
        version: int,
        content_sha256: str,
        media_type: Literal["image/png"],
        approval_ref: str,
        visual_description: str,
    ) -> str:
        return _creative_stable_id(
            "scene_asset",
            {
                "approval_ref": approval_ref,
                "content_sha256": content_sha256,
                "media_type": media_type,
                "provenance": "IMPORTED_APPROVED_MEDIA",
                "scene_id": scene_id,
                "version": version,
                "visual_description": visual_description,
            },
        )

    @model_validator(mode="after")
    def validate_scene_asset_id(self) -> SceneAssetVersion:
        expected = self.derive_id(
            scene_id=self.scene_id,
            version=self.version,
            content_sha256=self.content_sha256,
            media_type=self.media_type,
            approval_ref=self.approval_ref,
            visual_description=self.visual_description,
        )
        if self.id != expected:
            raise ValueError(
                "scene asset ID must derive from canonical content and bind its containing scene"
            )
        return self


class SceneBible(Contract):
    scene_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    ordinal: Annotated[int, Field(ge=0)]
    name: str = Field(min_length=1, max_length=128)
    visual_description: str = Field(min_length=1, max_length=4000)
    asset_versions: tuple[SceneAssetVersion, ...] = Field(min_length=1)
    active_asset_version_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)

    @classmethod
    def derive_id(cls, *, ordinal: int, name: str, visual_description: str) -> str:
        return _creative_stable_id(
            "scene",
            {
                "name": name,
                "ordinal": ordinal,
                "visual_description": visual_description,
            },
        )

    @model_validator(mode="after")
    def validate_scene_assets(self) -> SceneBible:
        if self.scene_id != self.derive_id(
            ordinal=self.ordinal,
            name=self.name,
            visual_description=self.visual_description,
        ):
            raise ValueError("scene ID must derive from its canonical content")
        version_ids = tuple(item.id for item in self.asset_versions)
        versions = tuple(item.version for item in self.asset_versions)
        if len(version_ids) != len(set(version_ids)) or len(versions) != len(set(versions)):
            raise ValueError("scene asset IDs and versions must be unique")
        if versions != tuple(sorted(versions)):
            raise ValueError("scene asset versions must use ascending version order")
        if any(item.scene_id != self.scene_id for item in self.asset_versions):
            raise ValueError("scene asset version must bind its containing scene")
        if self.active_asset_version_id not in version_ids:
            raise ValueError("active scene asset version must exist in the bible")
        return self


class DialogueLine(Contract):
    line_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    ordinal: Annotated[int, Field(ge=0)]
    scene_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    character_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    text: str = Field(min_length=1, max_length=2000)
    start_ms: Ms
    end_ms: Ms

    @classmethod
    def derive_id(
        cls,
        *,
        ordinal: int,
        scene_id: str,
        character_id: str,
        text: str,
        start_ms: int,
        end_ms: int,
    ) -> str:
        return _creative_stable_id(
            "dialogue",
            {
                "character_id": character_id,
                "end_ms": end_ms,
                "ordinal": ordinal,
                "scene_id": scene_id,
                "start_ms": start_ms,
                "text": text,
            },
        )

    @model_validator(mode="after")
    def validate_dialogue_interval(self) -> DialogueLine:
        if self.end_ms <= self.start_ms:
            raise ValueError("dialogue end_ms must be strictly later than start_ms")
        if self.line_id != self.derive_id(
            ordinal=self.ordinal,
            scene_id=self.scene_id,
            character_id=self.character_id,
            text=self.text,
            start_ms=self.start_ms,
            end_ms=self.end_ms,
        ):
            raise ValueError("dialogue line ID must derive from its canonical content")
        return self


class CreativeShotSize(StrEnum):
    EXTREME_CLOSE_UP = "EXTREME_CLOSE_UP"
    CLOSE_UP = "CLOSE_UP"
    MEDIUM_CLOSE_UP = "MEDIUM_CLOSE_UP"
    MEDIUM = "MEDIUM"
    MEDIUM_WIDE = "MEDIUM_WIDE"
    WIDE = "WIDE"
    EXTREME_WIDE = "EXTREME_WIDE"


class CreativeCameraAngle(StrEnum):
    EYE_LEVEL = "EYE_LEVEL"
    LOW_ANGLE = "LOW_ANGLE"
    HIGH_ANGLE = "HIGH_ANGLE"
    DUTCH_ANGLE = "DUTCH_ANGLE"
    OVERHEAD = "OVERHEAD"
    POV = "POV"


class CreativeCameraMovement(StrEnum):
    STATIC = "STATIC"
    PAN = "PAN"
    TILT = "TILT"
    DOLLY = "DOLLY"
    TRUCK = "TRUCK"
    PEDESTAL = "PEDESTAL"
    HANDHELD = "HANDHELD"
    CRANE = "CRANE"
    ZOOM = "ZOOM"
    ORBIT = "ORBIT"


def _canonical_creative_text(value: str, *, field: str) -> str:
    if value != value.strip() or normalize("NFC", value) != value:
        raise ValueError(f"{field} must be trimmed and use NFC normalization")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field} must not contain control characters")
    return value


class CreativeSampleShotSpec(Contract):
    """ID-free source shot; compilation derives the immutable StoryboardShotV2 ID."""

    ordinal: Annotated[int, Field(ge=0)]
    scene_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    narrative: str = Field(min_length=1, max_length=4000)
    visual_direction: str = Field(min_length=1, max_length=4000)
    emotion_by_character: dict[str, str] = Field(max_length=2)
    action: str = Field(min_length=1, max_length=2000)
    shot_size: CreativeShotSize
    camera_angle: CreativeCameraAngle
    camera_movement: CreativeCameraMovement
    wardrobe_by_character: dict[str, str] = Field(max_length=2)
    props: tuple[str, ...] = Field(max_length=16)
    continuity_notes: str = Field(min_length=1, max_length=2000)
    start_ms: Ms
    duration_ms: Annotated[int, Field(gt=0)]
    character_ids: tuple[str, ...] = Field(max_length=2)
    dialogue_line_ids: tuple[str, ...]

    @field_validator("character_ids", "dialogue_line_ids")
    @classmethod
    def validate_shot_references(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("shot references must be unique")
        if any(not item for item in value):
            raise ValueError("shot references must not be empty")
        return value

    @field_validator("character_ids")
    @classmethod
    def validate_canonical_character_order(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(value)):
            raise ValueError("shot character_ids must use canonical sorted order")
        return value

    @field_validator("emotion_by_character", "wardrobe_by_character")
    @classmethod
    def validate_character_direction_map(cls, value: dict[str, str]) -> dict[str, str]:
        for item in value.values():
            if not item or len(item) > 512:
                raise ValueError("character direction values must contain 1..512 characters")
            _canonical_creative_text(item, field="character direction")
        return value

    @field_validator("action", "continuity_notes")
    @classmethod
    def validate_direction_text(cls, value: str) -> str:
        return _canonical_creative_text(value, field="shot direction")

    @field_validator("props")
    @classmethod
    def validate_props(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))):
            raise ValueError("props must be unique and use canonical sorted order")
        for item in value:
            if not item or len(item) > 128:
                raise ValueError("props must contain 1..128 characters")
            _canonical_creative_text(item, field="prop")
        return value

    @model_validator(mode="after")
    def validate_character_direction_closure(self) -> CreativeSampleShotSpec:
        expected = set(self.character_ids)
        if set(self.emotion_by_character) != expected:
            raise ValueError("emotion_by_character keys must exactly match character_ids")
        if set(self.wardrobe_by_character) != expected:
            raise ValueError("wardrobe_by_character keys must exactly match character_ids")
        return self


class CreativeSampleSpec(Contract):
    """Portable, deterministic source for one 60-90 second creative sample."""

    title: str = Field(min_length=1, max_length=256)
    seed: int
    duration_ms: Annotated[int, Field(ge=60_000, le=90_000)]
    character_bibles: tuple[CharacterBible, ...] = Field(min_length=1, max_length=2)
    scene_bibles: tuple[SceneBible, ...] = Field(min_length=2, max_length=2)
    dialogue: tuple[DialogueLine, ...] = Field(min_length=1)
    shots: tuple[CreativeSampleShotSpec, ...] = Field(min_length=8, max_length=12)

    @model_validator(mode="after")
    def validate_creative_sample(self) -> CreativeSampleSpec:
        character_ids = tuple(item.character_id for item in self.character_bibles)
        if character_ids != tuple(sorted(set(character_ids))):
            raise ValueError("character bibles must be unique and sorted by character_id")

        scene_ids = tuple(item.scene_id for item in self.scene_bibles)
        scene_ordinals = tuple(item.ordinal for item in self.scene_bibles)
        if len(scene_ids) != len(set(scene_ids)) or scene_ordinals != (0, 1):
            raise ValueError("creative sample must contain two unique scenes in ordinal order")

        all_asset_ids = tuple(
            version.id for bible in self.character_bibles for version in bible.asset_versions
        ) + tuple(version.id for bible in self.scene_bibles for version in bible.asset_versions)
        if len(all_asset_ids) != len(set(all_asset_ids)):
            raise ValueError("asset version IDs must be globally unique")

        line_ids = tuple(item.line_id for item in self.dialogue)
        line_ordinals = tuple(item.ordinal for item in self.dialogue)
        if len(line_ids) != len(set(line_ids)) or line_ordinals != tuple(range(len(line_ids))):
            raise ValueError("dialogue lines must have unique IDs and contiguous ordinals")
        known_characters = set(character_ids)
        known_scenes = set(scene_ids)
        for line in self.dialogue:
            if line.character_id not in known_characters or line.scene_id not in known_scenes:
                raise ValueError("dialogue line references an unknown character or scene")
            if line.end_ms > self.duration_ms:
                raise ValueError("dialogue line exceeds the sample master timeline")
        for previous, current in zip(self.dialogue, self.dialogue[1:], strict=False):
            if current.start_ms < previous.end_ms:
                raise ValueError("dialogue lines must use non-overlapping master-clock intervals")

        shot_ordinals = tuple(item.ordinal for item in self.shots)
        if shot_ordinals != tuple(range(len(self.shots))):
            raise ValueError("shot ordinals must be contiguous and match tuple order")
        cursor = 0
        referenced_scenes: set[str] = set()
        referenced_characters: set[str] = set()
        referenced_lines: list[str] = []
        scene_shot_counts = {scene_id: 0 for scene_id in scene_ids}
        character_shot_counts = {character_id: 0 for character_id in character_ids}
        character_scenes = {character_id: set[str]() for character_id in character_ids}
        line_by_id = {item.line_id: item for item in self.dialogue}
        line_order = {item.line_id: item.ordinal for item in self.dialogue}
        scene_order = {item.scene_id: item.ordinal for item in self.scene_bibles}
        prior_scene_ordinal = 0
        for shot in self.shots:
            if shot.start_ms != cursor:
                raise ValueError("shot timeline must be contiguous and start at zero")
            cursor += shot.duration_ms
            if shot.scene_id not in known_scenes:
                raise ValueError("shot references an unknown scene")
            current_scene_ordinal = scene_order[shot.scene_id]
            if current_scene_ordinal < prior_scene_ordinal:
                raise ValueError("shots for each scene must form one contiguous scene block")
            prior_scene_ordinal = current_scene_ordinal
            referenced_scenes.add(shot.scene_id)
            scene_shot_counts[shot.scene_id] += 1
            if not set(shot.character_ids) <= known_characters:
                raise ValueError("shot references an unknown character")
            referenced_characters.update(shot.character_ids)
            for character_id in shot.character_ids:
                character_shot_counts[character_id] += 1
                character_scenes[character_id].add(shot.scene_id)
            if any(line_id not in line_by_id for line_id in shot.dialogue_line_ids):
                raise ValueError("shot references an unknown dialogue line")
            expected_line_order = tuple(sorted(shot.dialogue_line_ids, key=line_order.__getitem__))
            if shot.dialogue_line_ids != expected_line_order:
                raise ValueError("shot dialogue references must follow dialogue ordinal order")
            for line_id in shot.dialogue_line_ids:
                line = line_by_id[line_id]
                if line.scene_id != shot.scene_id or line.character_id not in shot.character_ids:
                    raise ValueError("shot dialogue binding does not match its scene and character")
                if line.start_ms < shot.start_ms or line.end_ms > shot.start_ms + shot.duration_ms:
                    raise ValueError("dialogue line must lie completely within its bound shot")
            referenced_lines.extend(shot.dialogue_line_ids)

        if cursor != self.duration_ms:
            raise ValueError("shot durations must equal the exact sample duration")
        if referenced_scenes != known_scenes or referenced_characters != known_characters:
            raise ValueError("every declared scene and character must be used by the sample")
        if any(count < 3 for count in scene_shot_counts.values()):
            raise ValueError("each scene must contain at least three shots")
        if any(
            character_shot_counts[character_id] < 3
            or character_scenes[character_id] != known_scenes
            for character_id in character_ids
        ):
            raise ValueError(
                "each recurring character must appear in three shots across both scenes"
            )
        if len(referenced_lines) != len(set(referenced_lines)) or set(referenced_lines) != set(
            line_ids
        ):
            raise ValueError("every dialogue line must be referenced by exactly one shot")
        return self


class NIRSceneV2(ContractV2):
    id: str
    scene_bible_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    scene_asset_version_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    ordinal: Annotated[int, Field(ge=0)]
    narrative: str = Field(min_length=1)
    start_ms: Ms
    duration_ms: Annotated[int, Field(gt=0)]
    character_ids: tuple[str, ...]
    dialogue_line_ids: tuple[str, ...]


class NIRV2(ContractV2):
    id: str
    title: str = Field(min_length=1)
    seed: int
    duration_ms: Annotated[int, Field(ge=60_000, le=90_000)]
    character_bibles: tuple[CharacterBible, ...] = Field(min_length=1, max_length=2)
    scene_bibles: tuple[SceneBible, ...] = Field(min_length=2, max_length=2)
    dialogue: tuple[DialogueLine, ...] = Field(min_length=1)
    scenes: tuple[NIRSceneV2, ...] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def validate_nir_v2_timeline(self) -> NIRV2:
        if tuple(item.ordinal for item in self.scenes) != (0, 1):
            raise ValueError("NIRV2 scenes must use exact ordinals 0 and 1")
        cursor = 0
        for scene in self.scenes:
            if scene.start_ms != cursor:
                raise ValueError("NIRV2 scene timeline must be contiguous")
            cursor += scene.duration_ms
        if cursor != self.duration_ms:
            raise ValueError("NIRV2 scenes must cover the exact duration")
        if {item.scene_bible_id for item in self.scenes} != {
            item.scene_id for item in self.scene_bibles
        }:
            raise ValueError("NIRV2 scene bibles must form an exact reference closure")
        scene_bible_by_id = {item.scene_id: item for item in self.scene_bibles}
        dialogue_by_id = {item.line_id: item for item in self.dialogue}
        for scene in self.scenes:
            bible = scene_bible_by_id[scene.scene_bible_id]
            if scene.scene_asset_version_id != bible.active_asset_version_id:
                raise ValueError("NIRV2 scene must bind the active approved scene asset")
            for line_id in scene.dialogue_line_ids:
                line = dialogue_by_id.get(line_id)
                if line is None or line.scene_id != scene.scene_bible_id:
                    raise ValueError("NIRV2 dialogue must bind its declared scene")
                if line.character_id not in scene.character_ids:
                    raise ValueError("NIRV2 dialogue character must appear in its scene")
        if {item.character_id for item in self.character_bibles} != {
            character_id for scene in self.scenes for character_id in scene.character_ids
        }:
            raise ValueError("NIRV2 character bibles must form an exact reference closure")
        if {item.line_id for item in self.dialogue} != {
            line_id for scene in self.scenes for line_id in scene.dialogue_line_ids
        }:
            raise ValueError("NIRV2 dialogue must form an exact reference closure")
        return self


class CharacterAssetBinding(ContractV2):
    character_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    asset_version_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)


class StoryboardShotV2(ContractV2):
    id: str
    nir_scene_id: str
    scene_bible_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    scene_asset_version_id: str = Field(pattern=_PORTABLE_CREATIVE_ID)
    ordinal: Annotated[int, Field(ge=0)]
    narrative: str = Field(min_length=1)
    visual_direction: str = Field(min_length=1)
    emotion_by_character: dict[str, str] = Field(max_length=2)
    action: str = Field(min_length=1, max_length=2000)
    shot_size: CreativeShotSize
    camera_angle: CreativeCameraAngle
    camera_movement: CreativeCameraMovement
    wardrobe_by_character: dict[str, str] = Field(max_length=2)
    props: tuple[str, ...] = Field(max_length=16)
    continuity_notes: str = Field(min_length=1, max_length=2000)
    prompt: str = Field(min_length=1)
    start_ms: Ms
    duration_ms: Annotated[int, Field(gt=0)]
    character_assets: tuple[CharacterAssetBinding, ...] = Field(max_length=2)
    dialogue_line_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_storyboard_bindings(self) -> StoryboardShotV2:
        character_ids = tuple(item.character_id for item in self.character_assets)
        asset_ids = tuple(item.asset_version_id for item in self.character_assets)
        if character_ids != tuple(sorted(set(character_ids))):
            raise ValueError("storyboard character bindings must be unique and sorted")
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("storyboard character asset versions must be unique")
        if len(self.dialogue_line_ids) != len(set(self.dialogue_line_ids)):
            raise ValueError("storyboard dialogue references must be unique")
        if set(self.emotion_by_character) != set(character_ids):
            raise ValueError("storyboard emotion keys must exactly match character bindings")
        if set(self.wardrobe_by_character) != set(character_ids):
            raise ValueError("storyboard wardrobe keys must exactly match character bindings")
        for value in (*self.emotion_by_character.values(), *self.wardrobe_by_character.values()):
            if not value or len(value) > 512:
                raise ValueError("storyboard character directions must contain 1..512 characters")
            _canonical_creative_text(value, field="storyboard character direction")
        _canonical_creative_text(self.action, field="storyboard action")
        _canonical_creative_text(self.continuity_notes, field="storyboard continuity notes")
        if self.props != tuple(sorted(set(self.props))):
            raise ValueError("storyboard props must be unique and use canonical sorted order")
        for prop in self.props:
            if not prop or len(prop) > 128:
                raise ValueError("storyboard props must contain 1..128 characters")
            _canonical_creative_text(prop, field="storyboard prop")
        expected_id = _creative_stable_id(
            "storyboard_shot_v2",
            {
                "character_assets": tuple(
                    item.model_dump(mode="json") for item in self.character_assets
                ),
                "dialogue_line_ids": self.dialogue_line_ids,
                "duration_ms": self.duration_ms,
                "emotion_by_character": self.emotion_by_character,
                "narrative": self.narrative,
                "nir_scene_id": self.nir_scene_id,
                "ordinal": self.ordinal,
                "action": self.action,
                "camera_angle": self.camera_angle.value,
                "camera_movement": self.camera_movement.value,
                "continuity_notes": self.continuity_notes,
                "prompt": self.prompt,
                "props": self.props,
                "scene_asset_version_id": self.scene_asset_version_id,
                "scene_bible_id": self.scene_bible_id,
                "shot_size": self.shot_size.value,
                "start_ms": self.start_ms,
                "visual_direction": self.visual_direction,
                "wardrobe_by_character": self.wardrobe_by_character,
            },
        )
        if self.id != expected_id:
            raise ValueError("storyboard shot ID must derive from its canonical content")
        return self


class PIRV2(ContractV2):
    id: str
    nir_id: str
    duration_ms: Annotated[int, Field(ge=60_000, le=90_000)]
    shots: tuple[StoryboardShotV2, ...] = Field(min_length=8, max_length=12)

    @model_validator(mode="after")
    def validate_pir_v2_timeline(self) -> PIRV2:
        if tuple(item.ordinal for item in self.shots) != tuple(range(len(self.shots))):
            raise ValueError("PIRV2 shots must use contiguous ordinals")
        cursor = 0
        for shot in self.shots:
            if shot.start_ms != cursor:
                raise ValueError("PIRV2 shot timeline must be contiguous")
            cursor += shot.duration_ms
        if cursor != self.duration_ms:
            raise ValueError("PIRV2 shots must cover the exact duration")
        expected_id = _creative_stable_id(
            "pirv2",
            {
                "duration_ms": self.duration_ms,
                "nir_id": self.nir_id,
                "shots": tuple(item.model_dump(mode="json") for item in self.shots),
            },
        )
        if self.id != expected_id:
            raise ValueError("PIRV2 ID must derive from its canonical content")
        return self


NonNegativeFailureCount = Annotated[int, Field(ge=0)]


class CreativeSampleDecision(StrEnum):
    PASS_SAMPLE = "PASS_SAMPLE"
    REVISE_OFFLINE = "REVISE_OFFLINE"
    STOP = "STOP"


class CreativeSampleMetrics(Contract):
    """Caller observations; continuity scores are human inputs, not technical QC."""

    sample_id: str = Field(pattern=r"^creative_sample_[0-9a-f]{20}$")
    revision_id: str = Field(pattern=r"^creative_revision_[0-9a-f]{20}$")
    first_pass_usable_rate: Annotated[Decimal, Field(ge=0, le=1)]
    character_continuity_rate: Annotated[Decimal, Field(ge=0, le=1)]
    scene_continuity_rate: Annotated[Decimal, Field(ge=0, le=1)]
    shot_intent_pass_rate: Annotated[Decimal, Field(ge=0, le=1)]
    artifact_free_rate: Annotated[Decimal, Field(ge=0, le=1)]
    critical_identity_breaks: Annotated[int, Field(ge=0)]
    duplicate_media_count: Annotated[int, Field(ge=0)]
    average_attempts: Annotated[Decimal, Field(ge=1, le=2)]
    total_elapsed_ms: Annotated[int, Field(ge=0)]
    human_edit_minutes: Annotated[Decimal, Field(ge=0)]
    cost_cny: Annotated[Decimal, Field(ge=0)]
    failure_counts: dict[str, NonNegativeFailureCount]

    @field_validator("failure_counts")
    @classmethod
    def validate_failure_counts(
        cls, value: dict[str, NonNegativeFailureCount]
    ) -> dict[str, NonNegativeFailureCount]:
        if any(
            not key
            or len(key) > 64
            or key[0].lower() not in "abcdefghijklmnopqrstuvwxyz"
            or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in key)
            for key in value
        ):
            raise ValueError("failure count keys must use canonical lowercase identifiers")
        return value

    @property
    def decision(self) -> CreativeSampleDecision:
        """Stop on an identity break, then apply the ADR-019 creative thresholds."""
        if self.critical_identity_breaks > 0:
            return CreativeSampleDecision.STOP
        if (
            self.character_continuity_rate >= Decimal("0.90")
            and self.scene_continuity_rate >= Decimal("0.90")
            and self.shot_intent_pass_rate >= Decimal("0.80")
            and self.artifact_free_rate >= Decimal("0.90")
            and self.first_pass_usable_rate >= Decimal("0.75")
            and self.critical_identity_breaks == 0
            and self.duplicate_media_count == 0
        ):
            return CreativeSampleDecision.PASS_SAMPLE
        return CreativeSampleDecision.REVISE_OFFLINE


class CreativeSampleCompilation(ContractV2):
    id: str
    spec_sha256: str = Field(pattern=_LOWER_SHA256)
    nir: NIRV2
    pir: PIRV2
    audio_clock: AudioMasterClock
    job_graph: JobGraph
    assembly_plan: AssemblyPlan

    @model_validator(mode="after")
    def validate_compilation_closure(self) -> CreativeSampleCompilation:
        if self.nir.id != f"nirv2_{self.spec_sha256[:20]}":
            raise ValueError("NIRV2 ID must derive from the canonical sample specification")
        if self.pir.nir_id != self.nir.id:
            raise ValueError("PIRV2 must reference the compiled NIRV2")
        if self.pir.duration_ms != self.nir.duration_ms:
            raise ValueError("compiled NIRV2 and PIRV2 durations must match")
        if self.audio_clock.duration_ms != self.pir.duration_ms:
            raise ValueError("audio clock must match the compiled sample duration")
        shots = self.pir.shots
        nir_scene_by_id = {item.id: item for item in self.nir.scenes}
        character_by_id = {item.character_id: item for item in self.nir.character_bibles}
        scene_by_id = {item.scene_id: item for item in self.nir.scene_bibles}
        dialogue_by_id = {item.line_id: item for item in self.nir.dialogue}
        for scene in self.nir.scenes:
            expected_scene_id = _creative_stable_id(
                "nir_scene_v2",
                {
                    "character_ids": scene.character_ids,
                    "dialogue_line_ids": scene.dialogue_line_ids,
                    "duration_ms": scene.duration_ms,
                    "narrative": scene.narrative,
                    "nir_id": self.nir.id,
                    "ordinal": scene.ordinal,
                    "scene_asset_version_id": scene.scene_asset_version_id,
                    "scene_bible_id": scene.scene_bible_id,
                    "start_ms": scene.start_ms,
                },
            )
            if scene.id != expected_scene_id:
                raise ValueError("NIRSceneV2 ID must derive from its canonical content")
        for shot in shots:
            nir_scene = nir_scene_by_id.get(shot.nir_scene_id)
            scene_bible = scene_by_id.get(shot.scene_bible_id)
            if nir_scene is None or nir_scene.scene_bible_id != shot.scene_bible_id:
                raise ValueError("storyboard shot must reference its compiled NIRV2 scene")
            if (
                scene_bible is None
                or shot.scene_asset_version_id != scene_bible.active_asset_version_id
            ):
                raise ValueError("storyboard shot must bind the active approved scene asset")
            bound_characters: set[str] = set()
            for binding in shot.character_assets:
                bible = character_by_id.get(binding.character_id)
                if bible is None or binding.asset_version_id != bible.active_asset_version_id:
                    raise ValueError(
                        "storyboard shot must bind each active approved character asset"
                    )
                bound_characters.add(binding.character_id)
            for line_id in shot.dialogue_line_ids:
                line = dialogue_by_id.get(line_id)
                if (
                    line is None
                    or line.scene_id != shot.scene_bible_id
                    or line.character_id not in bound_characters
                    or line.start_ms < shot.start_ms
                    or line.end_ms > shot.start_ms + shot.duration_ms
                ):
                    raise ValueError("storyboard dialogue must close over its shot bindings")
        if tuple(cue.shot_id for cue in self.audio_clock.cues) != tuple(shot.id for shot in shots):
            raise ValueError("audio cues must form an exact storyboard-shot closure")
        for cue, shot in zip(self.audio_clock.cues, shots, strict=True):
            if cue.start_ms != shot.start_ms or cue.end_ms != shot.start_ms + shot.duration_ms:
                raise ValueError("audio cue timing must match its storyboard shot")
        if tuple(job.shot_id for job in self.job_graph.jobs) != tuple(shot.id for shot in shots):
            raise ValueError("generation jobs must form an exact storyboard-shot closure")
        for job, shot in zip(self.job_graph.jobs, shots, strict=True):
            if job.prompt != shot.prompt or job.duration_ms != shot.duration_ms or job.depends_on:
                raise ValueError("generation job content must match its storyboard shot")
        if self.assembly_plan.clock_id != self.audio_clock.id:
            raise ValueError("assembly plan must reference the compiled audio clock")
        expected_items = tuple(
            (job.id, shot.start_ms, shot.duration_ms)
            for job, shot in zip(self.job_graph.jobs, shots, strict=True)
        )
        actual_items = tuple(
            (item.job_id, item.start_ms, item.duration_ms) for item in self.assembly_plan.items
        )
        if actual_items != expected_items:
            raise ValueError("assembly items must form an exact generation-job closure")
        expected_compilation_id = _creative_stable_id(
            "creative_sample",
            [
                self.spec_sha256,
                self.nir.id,
                self.pir.id,
                self.audio_clock.id,
                self.job_graph.id,
                self.assembly_plan.id,
            ],
        )
        if self.id != expected_compilation_id:
            raise ValueError("creative sample ID must derive from its canonical compilation")
        return self


class RunState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    STOP_2 = "STOP-2"
    HUMAN_GATE = "HUMAN_GATE"


class ProviderFailureClass(StrEnum):
    SUBMISSION_UNKNOWN = "SUBMISSION_UNKNOWN"
    REMOTE_FAILED = "REMOTE_FAILED"
    EXPIRED = "EXPIRED"
    AUTHENTICATION = "AUTHENTICATION"
    QUOTA = "QUOTA"
    CONFIGURATION = "CONFIGURATION"
    INVALID_INPUT = "INVALID_INPUT"
    SENSITIVE_CONTENT = "SENSITIVE_CONTENT"
    TRANSIENT = "TRANSIENT"
    LIVE_NOT_AUTHORIZED = "LIVE_NOT_AUTHORIZED"
    CAPABILITY_DRIFT = "CAPABILITY_DRIFT"
    COST_LIMIT = "COST_LIMIT"


class ProviderTaskState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ProviderAttemptState(StrEnum):
    RESERVED = "RESERVED"
    SUBMITTED = "SUBMITTED"
    WATCHING = "WATCHING"
    DOWNLOADING = "DOWNLOADING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    SUBMISSION_UNKNOWN = "SUBMISSION_UNKNOWN"
    HUMAN_GATE = "HUMAN_GATE"


class ProviderProfile(Contract):
    provider: str
    model: str
    aspect_ratio: str = "9:16"
    resolution: str = "1080p"
    min_duration_ms: int = 4000
    max_duration_ms: int = 15000
    max_in_flight: int = 2
    generate_audio: bool = False


class SnapshotStatus(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    REVOKED = "REVOKED"


class ArkCanaryEntitlementSnapshot(Contract):
    """Execution-day proof of the exact Ark Canary entitlement scope."""

    document_type: Literal["sdc.ark-canary-entitlement-snapshot"]
    evidence_profile: Literal["ark-canary-entitlement-v1"]
    snapshot_revision: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    status: Literal["CURRENT"]
    provider: Literal["volcengine_ark"]
    service: Literal["ark-video-generation"]
    model: Literal["doubao-seedance-2-0-260128"]
    region: Literal["cn-beijing"]
    operation: Literal["contents.generations.tasks.create"]
    provider_state: Literal["ENABLED"]
    conclusion: Literal["PASS_ENTITLEMENT_ONLY"]
    account_scope_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    credential_binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_url: Literal["https://console.volcengine.com/ark/region:cn-beijing/openManagement"]
    source_valid_until: datetime | None
    captured_at: datetime
    valid_until: datetime
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("source_valid_until", "captured_at", "valid_until")
    @classmethod
    def canonicalize_entitlement_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        _require_timezone(value, "entitlement datetime")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_entitlement_window(self) -> ArkCanaryEntitlementSnapshot:
        if self.account_scope_sha256 == self.credential_binding_sha256:
            raise ValueError("account scope and credential binding must be independent digests")
        if self.captured_at >= self.valid_until:
            raise ValueError("entitlement validity must end strictly after capture")
        if self.source_valid_until is not None and self.source_valid_until <= self.captured_at:
            raise ValueError("entitlement source boundary must end strictly after capture")

        local_capture = self.captured_at.astimezone(_SHANGHAI_TIMEZONE)
        capture_day_boundary = datetime(
            local_capture.year,
            local_capture.month,
            local_capture.day,
            23,
            59,
            59,
            tzinfo=_SHANGHAI_TIMEZONE,
        ).astimezone(UTC)
        deadlines = [
            self.captured_at + _ENTITLEMENT_MAX_VALIDITY,
            capture_day_boundary,
        ]
        if self.source_valid_until is not None:
            deadlines.append(self.source_valid_until)
        if self.valid_until > min(deadlines):
            raise ValueError(
                "entitlement validity exceeds its source, four-hour, or capture-day boundary"
            )
        return self


class PricingInputMode(StrEnum):
    WITHOUT_VIDEO = "WITHOUT_VIDEO"
    WITH_VIDEO = "WITH_VIDEO"


class ProviderCapabilitySnapshot(Contract):
    snapshot_revision: str
    status: SnapshotStatus
    provider: str
    model: str
    aspect_ratios: tuple[str, ...] = Field(min_length=1)
    resolutions: tuple[str, ...] = Field(min_length=1)
    fps: Annotated[int, Field(gt=0)]
    min_duration_ms: Annotated[int, Field(gt=0)]
    max_duration_ms: Annotated[int, Field(gt=0)]
    source_url: str
    source_updated_at: datetime
    captured_at: datetime
    valid_until: datetime
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProviderPricingSnapshot(Contract):
    snapshot_revision: str
    status: SnapshotStatus
    provider: str
    model: str
    resolution: str
    input_mode: PricingInputMode
    currency: Literal["CNY"] = "CNY"
    billing_unit: str
    unit_price_cny: Annotated[Decimal, Field(gt=0)]
    worst_case_units: Annotated[Decimal, Field(gt=0)]
    worst_case_cost_cny: Annotated[Decimal, Field(gt=0)]
    source_url: str
    source_updated_at: datetime
    captured_at: datetime
    valid_until: datetime
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class LiveAuthorization(Contract):
    authorization_id: str
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pricing_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_cost_cny: Annotated[Decimal, Field(gt=0)]
    expires_at: datetime
    nonce: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_posts: Literal[1] = 1


class CanaryPlan(Contract):
    state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    run_id: str
    job_id: str
    attempt: Literal[1] = 1
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pricing_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    worst_case_cost_cny: Annotated[Decimal, Field(gt=0)]
    approved_cost_ceiling_cny: Annotated[Decimal, Field(gt=0)]
    planned_at: datetime
    posts_allowed: Literal[0] = 0


class EvidenceBoundCanaryPlan(Contract):
    """Zero-authority plan whose snapshots came from one trusted FRESH bundle."""

    document_type: Literal["sdc.evidence-bound-canary-plan"] = "sdc.evidence-bound-canary-plan"
    evidence_profile: Literal["ark-canary-capability-pricing-v1"] = (
        "ark-canary-capability-pricing-v1"
    )
    evidence_bundle_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_logical_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_valid_until: datetime
    state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    run_id: str
    job_id: str
    attempt: Literal[1] = 1
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pricing_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    worst_case_cost_cny: Annotated[Decimal, Field(gt=0)]
    approved_cost_ceiling_cny: Annotated[Decimal, Field(gt=0)]
    planned_at: datetime
    posts_allowed: Literal[0] = 0

    @model_validator(mode="after")
    def validate_evidence_window(self) -> EvidenceBoundCanaryPlan:
        for field, value in (
            ("planned_at", self.planned_at),
            ("evidence_valid_until", self.evidence_valid_until),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field} must include a timezone")
        if self.planned_at > self.evidence_valid_until:
            raise ValueError("planned_at must not exceed the evidence validity window")
        if self.worst_case_cost_cny > self.approved_cost_ceiling_cny:
            raise ValueError("worst-case cost must not exceed the approved ceiling")
        return self


class EvidenceBoundLiveAuthorization(Contract):
    """Inert one-POST authorization candidate bound to reviewed evidence and runtime policy."""

    document_type: Literal["sdc.evidence-bound-live-authorization"] = (
        "sdc.evidence-bound-live-authorization"
    )
    evidence_profile: Literal["ark-canary-capability-pricing-v1"] = (
        "ark-canary-capability-pricing-v1"
    )
    authorization_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    submission_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_release_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_bundle_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_logical_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_valid_until: datetime
    entitlement_anchor_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entitlement_valid_until: datetime
    provider_region: Literal["cn-beijing"] = "cn-beijing"
    task_queue: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    ledger_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    run_id: str = Field(min_length=1, max_length=256)
    job_id: str = Field(min_length=1, max_length=128)
    attempt: Literal[1] = 1
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pricing_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    worst_case_cost_cny: Annotated[Decimal, Field(gt=0)]
    max_cost_cny: Annotated[Decimal, Field(gt=0, le=15)]
    authorized_at: datetime
    expires_at: datetime
    nonce: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_posts: Literal[1] = 1

    @field_validator(
        "evidence_valid_until",
        "entitlement_valid_until",
        "authorized_at",
        "expires_at",
    )
    @classmethod
    def canonicalize_authorization_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evidence-bound authorization datetimes must include a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_authorization_window(self) -> EvidenceBoundLiveAuthorization:
        if self.authorized_at >= self.expires_at:
            raise ValueError("authorization expiry must be later than authorized_at")
        if self.expires_at > min(self.evidence_valid_until, self.entitlement_valid_until):
            raise ValueError("authorization must expire within evidence and entitlement validity")
        if self.worst_case_cost_cny > self.max_cost_cny:
            raise ValueError("authorization max cost must cover the reviewed worst-case cost")
        if self.entitlement_anchor_sha256 in {
            self.evidence_bundle_id,
            self.evidence_logical_tree_sha256,
            self.capability_snapshot_sha256,
            self.pricing_snapshot_sha256,
        }:
            raise ValueError("entitlement must use an independent reviewed anchor")
        return self


class EvidenceAcquisition(StrEnum):
    FRESH = "FRESH"
    INHERITED = "INHERITED"
    LEGACY_IMPORT = "LEGACY_IMPORT"


_WINDOWS_RESERVED_PATH_STEMS = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
    | {f"com{index}" for index in "¹²³"}
    | {f"lpt{index}" for index in "¹²³"}
)
_EVIDENCE_SOURCE_HOSTS = frozenset(
    {"console.volcengine.com", "docs.volcengine.com", "www.volcengine.com"}
)


def _canonical_evidence_path(value: str) -> str:
    if not value or len(value) > 512:
        raise ValueError("evidence logical path must contain 1..512 characters")
    if normalize("NFC", value) != value:
        raise ValueError("evidence logical path must use NFC Unicode normalization")
    if (
        "\\" in value
        or any(character in '<>:"|?*' for character in value)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError("evidence logical path contains a non-portable character")
    path = PurePosixPath(value)
    if not path.parts or value == "." or path.is_absolute() or path.as_posix() != value:
        raise ValueError("evidence logical path must be canonical and relative")
    for part in path.parts:
        if part in {"", ".", ".."} or len(part) > 255 or part.rstrip(" .") != part:
            raise ValueError("evidence logical path contains an unsafe segment")
        if part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_PATH_STEMS:
            raise ValueError("evidence logical path contains a reserved device name")
    return value


def _require_timezone(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")


class EvidenceObject(Contract):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: Annotated[int, Field(gt=0, le=EVIDENCE_MAX_OBJECT_BYTES)]
    media_type: str = Field(
        min_length=3,
        max_length=127,
        pattern=r"^[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*$",
    )

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, value: str) -> str:
        if value != value.lower():
            raise ValueError("evidence media type must use canonical lowercase spelling")
        return value


class EvidenceMember(Contract):
    logical_path: str
    role: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9._-]*$")
    object_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_schema_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=32,
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$",
    )

    @field_validator("logical_path")
    @classmethod
    def validate_logical_path(cls, value: str) -> str:
        return _canonical_evidence_path(value)


class EvidenceCapture(Contract):
    capture_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    kind: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9._-]*$")
    source_url: str | None = Field(default=None, max_length=2048)
    source_updated_at: datetime | None = None
    captured_at: datetime
    valid_until: datetime
    acquisition: EvidenceAcquisition
    origin_anchor_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    origin_valid_until: datetime | None = None
    member_paths: tuple[str, ...] = Field(min_length=1)

    @field_validator("source_updated_at", "captured_at", "valid_until", "origin_valid_until")
    @classmethod
    def canonicalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        _require_timezone(value, "evidence datetime")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_capture(self) -> EvidenceCapture:
        if self.source_updated_at is not None:
            if self.source_updated_at > self.captured_at:
                raise ValueError("source_updated_at must not be later than captured_at")
        if self.captured_at > self.valid_until:
            raise ValueError("captured_at must not be later than valid_until")
        if self.source_url is not None:
            parsed = urlparse(self.source_url)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError("source_url must be an approved Volcengine HTTPS URL") from exc
            safe_doc_query = parsed.hostname in {
                "docs.volcengine.com",
                "www.volcengine.com",
            } and parsed.query in {"lang=zh", "lang=en"}
            has_noncanonical_character = "\\" in self.source_url or any(
                ord(character) <= 32 or ord(character) == 127 for character in self.source_url
            )
            if (
                has_noncanonical_character
                or parsed.scheme != "https"
                or parsed.hostname not in _EVIDENCE_SOURCE_HOSTS
                or parsed.netloc != parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or port is not None
                or (parsed.query and not safe_doc_query)
                or parsed.fragment
            ):
                raise ValueError("source_url must be an approved Volcengine HTTPS URL")
        canonical_paths = tuple(_canonical_evidence_path(path) for path in self.member_paths)
        if canonical_paths != tuple(sorted(set(canonical_paths))):
            raise ValueError("capture member_paths must be unique and sorted")
        if self.acquisition is EvidenceAcquisition.FRESH:
            if self.origin_anchor_sha256 is not None or self.origin_valid_until is not None:
                raise ValueError("fresh evidence must not name an origin")
        elif self.origin_anchor_sha256 is None or self.origin_valid_until is None:
            raise ValueError("inherited or legacy evidence must name its origin and expiry")
        elif self.valid_until > self.origin_valid_until:
            raise ValueError("inherited evidence must not extend its origin validity")
        return self


def evidence_logical_tree_sha256(
    objects: tuple[EvidenceObject, ...], members: tuple[EvidenceMember, ...]
) -> str:
    object_by_hash = {item.sha256: item for item in objects}
    resolved: list[dict[str, object]] = []
    for member in sorted(members, key=lambda item: item.logical_path):
        item = object_by_hash.get(member.object_sha256)
        if item is None:
            raise ValueError(f"member references undeclared object: {member.logical_path}")
        resolved.append(
            {
                "logical_path": member.logical_path,
                "role": member.role,
                "content_schema_version": member.content_schema_version,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "media_type": item.media_type,
            }
        )
    descriptor = json.dumps(
        resolved, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    return hashlib.sha256(b"sdc:evidence-logical-tree:1.0.0\0" + descriptor).hexdigest()


class EvidenceBundleContent(Contract):
    created_at: datetime
    valid_until: datetime
    predecessor_bundle_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    objects: tuple[EvidenceObject, ...] = Field(min_length=1)
    members: tuple[EvidenceMember, ...] = Field(min_length=1)
    captures: tuple[EvidenceCapture, ...] = Field(min_length=1)
    resolved_logical_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("created_at", "valid_until")
    @classmethod
    def canonicalize_datetime(cls, value: datetime) -> datetime:
        _require_timezone(value, "bundle datetime")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_bundle_content(self) -> EvidenceBundleContent:
        object_hashes = tuple(item.sha256 for item in self.objects)
        if object_hashes != tuple(sorted(set(object_hashes))):
            raise ValueError("evidence objects must be unique and sorted by sha256")

        member_paths = tuple(item.logical_path for item in self.members)
        if member_paths != tuple(sorted(set(member_paths))):
            raise ValueError("evidence members must be unique and sorted by logical_path")
        if len({path.casefold() for path in member_paths}) != len(member_paths):
            raise ValueError("evidence logical paths must remain unique when case-folded")

        declared_objects = set(object_hashes)
        referenced_objects = {item.object_sha256 for item in self.members}
        if referenced_objects != declared_objects:
            raise ValueError("evidence objects and member references must form an exact closure")
        if sum(item.size_bytes for item in self.objects) > EVIDENCE_MAX_BUNDLE_BYTES:
            raise ValueError("evidence bundle exceeds the total object byte limit")

        capture_ids = tuple(item.capture_id for item in self.captures)
        if capture_ids != tuple(sorted(set(capture_ids))):
            raise ValueError("evidence captures must be unique and sorted by capture_id")
        captured_paths = [path for capture in self.captures for path in capture.member_paths]
        if len(captured_paths) != len(set(captured_paths)) or set(captured_paths) != set(
            member_paths
        ):
            raise ValueError("captures must reference every evidence member exactly once")
        if self.created_at < max(capture.captured_at for capture in self.captures):
            raise ValueError("created_at must not precede an evidence capture")

        expected_valid_until = min(capture.valid_until for capture in self.captures)
        if self.valid_until != expected_valid_until:
            raise ValueError("bundle valid_until must equal the earliest capture expiry")
        expected_tree = evidence_logical_tree_sha256(self.objects, self.members)
        if self.resolved_logical_tree_sha256 != expected_tree:
            raise ValueError("resolved evidence tree digest does not match bundle members")
        return self


def evidence_bundle_content_sha256(content: EvidenceBundleContent) -> str:
    descriptor = json.dumps(
        content.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(b"sdc:evidence-bundle-content:1.0.0\0" + descriptor).hexdigest()


class EvidenceBundle(Contract):
    document_type: Literal["sdc.evidence-bundle"] = "sdc.evidence-bundle"
    bundle_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    content: EvidenceBundleContent

    @model_validator(mode="after")
    def validate_bundle_id(self) -> EvidenceBundle:
        if self.bundle_id != evidence_bundle_content_sha256(self.content):
            raise ValueError("bundle_id does not match canonical bundle content")
        if self.bundle_id == self.content.predecessor_bundle_id:
            raise ValueError("bundle predecessor must differ from the current bundle")
        return self


class InputMaterial(Contract):
    reference: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProviderRequest(Contract):
    run_id: str
    job_id: str
    attempt: Annotated[int, Field(ge=1, le=2)]
    provider: str
    model: str
    prompt: str
    duration_ms: Annotated[int, Field(gt=0)]
    aspect_ratio: str
    resolution: str
    generate_audio: bool
    input_materials: tuple[InputMaterial, ...] = ()
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def provider_request_fingerprint(request: ProviderRequest) -> str:
    """Hash every explicit Provider input while excluding the self-referential digest."""
    body = request.model_dump(exclude={"request_fingerprint"}, mode="json")
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class CanaryExecution(Contract):
    """Exact workflow payload for the separately authorized one-task canary route."""

    run_id: str = Field(min_length=1)
    graph: JobGraph
    request: ProviderRequest

    @model_validator(mode="after")
    def validate_exact_canary(self) -> CanaryExecution:
        if len(self.graph.jobs) != 1:
            raise ValueError("canary workflow must contain exactly one Job")
        job = self.graph.jobs[0]
        if job.depends_on:
            raise ValueError("canary Job must not depend on another Job")
        if self.request.run_id != self.run_id or self.request.job_id != job.id:
            raise ValueError("canary run_id/job_id must match the Workflow payload")
        if self.request.attempt != 1:
            raise ValueError("canary permits Attempt 1 only")
        if self.request.provider != CANARY_PROVIDER or self.request.model != CANARY_MODEL:
            raise ValueError("canary Provider and Seedance 2.0 model are fixed")
        if (
            self.request.duration_ms != 4000
            or self.request.aspect_ratio != "9:16"
            or self.request.resolution != "1080p"
        ):
            raise ValueError("canary output is fixed to 9:16, 1080p, and 4000 ms")
        if self.request.generate_audio:
            raise ValueError("canary generate_audio must be false")
        if self.request.input_materials:
            raise ValueError("canary is text-only and accepts no input materials")
        if not self.request.prompt.strip():
            raise ValueError("canary text prompt must not be empty")
        if self.request.prompt != job.prompt or self.request.duration_ms != job.duration_ms:
            raise ValueError("canary request must match the single compiled Job")
        if provider_request_fingerprint(self.request) != self.request.request_fingerprint:
            raise ValueError("canary request fingerprint does not match the Workflow request")
        return self


class ProviderSubmission(Contract):
    provider_task_id: str
    state: ProviderTaskState


class ProviderFailure(Contract):
    failure_class: ProviderFailureClass
    code: str | None = None
    message: str
    retryable: bool = False


class ProviderTaskSnapshot(Contract):
    provider_task_id: str
    state: ProviderTaskState
    usage_tokens: int | None = None
    failure: ProviderFailure | None = None
    # Ephemeral signed URLs are adapter-only data and deliberately excluded.
    result_available: bool = False


class DownloadedArtifact(Contract):
    provider_task_id: str
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: Annotated[int, Field(gt=0)]
    ffprobe: dict[str, object]


class CancelResult(Contract):
    provider_task_id: str
    cancelled: bool


class RunEvent(Contract):
    id: str
    run_id: str
    event_type: str
    state: RunState
    occurred_at: str
    idempotency_key: str
    payload: dict[str, str | int | bool] = {}


class QCEvidence(Contract):
    check: str
    passed: bool
    details: dict[str, str | int | bool]


class QCReport(Contract):
    id: str
    passed: bool
    evidence: tuple[QCEvidence, ...]
    ffprobe: dict[str, object]


class ReleaseManifest(Contract):
    id: str
    media_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: Annotated[int, Field(gt=0)]
    duration_ms: Ms
