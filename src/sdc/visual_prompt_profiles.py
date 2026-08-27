"""Pure, immutable runtime core for deterministic visual Prompt profiles.

This module implements only the offline semantic boundary accepted by SDC-ADR-039 and
SDC-ADR-040.  It performs no filesystem, environment, clock, randomness, network, Provider,
Compiler, Candidate, asset-promotion, or persistence operation.  A successful render and its
receipt prove only a deterministic process binding; they grant no rights, qualification, or
execution authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import NoReturn, cast

PROFILE_SHA256_DOMAIN = b"sdc:visual-prompt-profile:v1\0"
CATALOG_SHA256_DOMAIN = b"sdc:visual-prompt-catalog:v1\0"
RENDER_INPUT_SHA256_DOMAIN = b"sdc:visual-prompt-render-input:v1\0"
PROMPT_RENDER_RECEIPT_SHA256_DOMAIN = b"sdc:visual-prompt-render-receipt:v1\0"

VISUAL_PROMPT_RENDERER_ID = "sdc.visual-prompt-renderer"
VISUAL_PROMPT_RENDERER_VERSION = "1.0.0"

PROMPT_RENDER_RECEIPT_PURPOSE = "DETERMINISTIC_PROMPT_RENDER_PROCESS_EVIDENCE_ONLY"
CURRENT_GATE = "HUMAN_GATE"
PROVIDER_STATE = "NOT_AUTHORIZED"
USAGE_RESTRICTION = "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"

MAX_PROMPT_BYTES = 65_536
MAX_STRICT_NON_NEGATIVE_INT = 9_223_372_036_854_775_807

_PORTABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PROVIDER_ID = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_SEMANTIC_VERSION = re.compile(r"^(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})$")
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC_SECOND = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_SEMANTIC_VERSION_COMPONENT_MAX = 2_147_483_647
_TRIM_CODEPOINTS = frozenset(
    {
        *range(0x0009, 0x000E),
        0x0020,
        0x0085,
        0x00A0,
        0x1680,
        *range(0x2000, 0x200B),
        0x2028,
        0x2029,
        0x202F,
        0x205F,
        0x3000,
    }
)


class VisualPromptProfileError(ValueError):
    """One value violates the frozen ADR-039/040 runtime contract."""


class AssetPurpose(StrEnum):
    NARRATIVE_SHOT = "NARRATIVE_SHOT"
    CHARACTER_REFERENCE_ASSET = "CHARACTER_REFERENCE_ASSET"
    SCENE_REFERENCE_ASSET = "SCENE_REFERENCE_ASSET"


class VisualStyleId(StrEnum):
    CINEMATIC_STORYBOARD_V1 = "sdc.cinematic-storyboard.v1"


class NarrativeContext(StrEnum):
    DIALOGUE = "DIALOGUE"
    ACTION = "ACTION"
    ESTABLISHING = "ESTABLISHING"
    TRANSITION = "TRANSITION"
    REFERENCE_DEVELOPMENT = "REFERENCE_DEVELOPMENT"


class ShotType(StrEnum):
    NARRATIVE_FRAME = "NARRATIVE_FRAME"
    REFERENCE_SHEET = "REFERENCE_SHEET"


class ShotSizeV1(StrEnum):
    EXTREME_CLOSE_UP = "EXTREME_CLOSE_UP"
    CLOSE_UP = "CLOSE_UP"
    MEDIUM_CLOSE_UP = "MEDIUM_CLOSE_UP"
    MEDIUM = "MEDIUM"
    MEDIUM_WIDE = "MEDIUM_WIDE"
    WIDE = "WIDE"
    EXTREME_WIDE = "EXTREME_WIDE"


class CameraAngleV1(StrEnum):
    EYE_LEVEL = "EYE_LEVEL"
    LOW_ANGLE = "LOW_ANGLE"
    HIGH_ANGLE = "HIGH_ANGLE"
    DUTCH_ANGLE = "DUTCH_ANGLE"
    OVERHEAD = "OVERHEAD"
    POV = "POV"


class CameraMovementV1(StrEnum):
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


class ReferenceAssetType(StrEnum):
    CHARACTER_IDENTITY_SHEET = "CHARACTER_IDENTITY_SHEET"
    CHARACTER_POSE_REFERENCE = "CHARACTER_POSE_REFERENCE"
    CHARACTER_EXPRESSION_REFERENCE = "CHARACTER_EXPRESSION_REFERENCE"
    SCENE_ESTABLISHING_REFERENCE = "SCENE_ESTABLISHING_REFERENCE"
    SCENE_LIGHTING_REFERENCE = "SCENE_LIGHTING_REFERENCE"
    SCENE_MATERIAL_REFERENCE = "SCENE_MATERIAL_REFERENCE"
    SCENE_PROP_PLACEMENT_REFERENCE = "SCENE_PROP_PLACEMENT_REFERENCE"


class ReferenceAssetRecipeKind(StrEnum):
    CHARACTER_REFERENCE = "CHARACTER_REFERENCE"
    SCENE_REFERENCE = "SCENE_REFERENCE"


class OfflineRenderAdmissionStatus(StrEnum):
    DRAFT = "DRAFT"
    HUMAN_REVIEWED_FOR_OFFLINE_RENDER = "HUMAN_REVIEWED_FOR_OFFLINE_RENDER"
    RETIRED = "RETIRED"


class ProfileTextProvenanceStatus(StrEnum):
    FIRST_PARTY_TEXT_REVIEWED = "FIRST_PARTY_TEXT_REVIEWED"
    RIGHTS_REVIEW_REQUIRED = "RIGHTS_REVIEW_REQUIRED"
    PROHIBITED_EXTERNAL_CONTENT = "PROHIBITED_EXTERNAL_CONTENT"


class ProviderSyntaxCompatibilityStatus(StrEnum):
    UNASSESSED = "UNASSESSED"
    SYNTAX_COMPATIBLE = "SYNTAX_COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"


class PlaceholderId(StrEnum):
    NARRATIVE = "narrative"
    VISUAL_DIRECTION = "visual_direction"
    ACTION = "action"
    SHOT_SIZE = "shot_size"
    CAMERA_ANGLE = "camera_angle"
    CAMERA_MOVEMENT = "camera_movement"
    CHARACTER_ASSET_BINDINGS = "character_asset_bindings"
    SCENE_ASSET_BINDING = "scene_asset_binding"
    EMOTION_BY_CHARACTER = "emotion_by_character"
    WARDROBE_BY_CHARACTER = "wardrobe_by_character"
    PROPS = "props"
    CONTINUITY_NOTES = "continuity_notes"
    DIALOGUE = "dialogue"


_NARRATIVE_CONTEXT_ORDER = tuple(NarrativeContext)
_REFERENCE_ASSET_TYPE_ORDER = tuple(ReferenceAssetType)
_CHARACTER_REFERENCE_ASSET_TYPES = _REFERENCE_ASSET_TYPE_ORDER[:3]
_SCENE_REFERENCE_ASSET_TYPES = _REFERENCE_ASSET_TYPE_ORDER[3:]
_NARRATIVE_PLACEHOLDERS = frozenset(PlaceholderId)
_CHARACTER_REFERENCE_PLACEHOLDERS = frozenset(
    {
        PlaceholderId.NARRATIVE,
        PlaceholderId.VISUAL_DIRECTION,
        PlaceholderId.ACTION,
        PlaceholderId.CHARACTER_ASSET_BINDINGS,
        PlaceholderId.EMOTION_BY_CHARACTER,
        PlaceholderId.WARDROBE_BY_CHARACTER,
        PlaceholderId.CONTINUITY_NOTES,
    }
)
_SCENE_REFERENCE_PLACEHOLDERS = frozenset(
    {
        PlaceholderId.NARRATIVE,
        PlaceholderId.VISUAL_DIRECTION,
        PlaceholderId.ACTION,
        PlaceholderId.SCENE_ASSET_BINDING,
        PlaceholderId.PROPS,
        PlaceholderId.CONTINUITY_NOTES,
    }
)
_CHARACTER_PRIMARY_BINDING_FIELDS = (
    "character_id",
    "asset_version_id",
    "asset_content_sha256",
)
_SCENE_PRIMARY_BINDING_FIELDS = (
    "scene_id",
    "asset_version_id",
    "asset_content_sha256",
)


def _invalid(message: str) -> NoReturn:
    raise VisualPromptProfileError(message)


def _require_exact_type(value: object, expected: type[object], field: str) -> None:
    if type(value) is not expected:
        _invalid(f"{field} must be an exact {expected.__name__}")


def _validate_portable_id(value: object, field: str) -> str:
    if type(value) is not str or _PORTABLE_ID.fullmatch(value) is None:
        _invalid(f"{field} must be a PortableId")
    return value


def _validate_provider_id(value: object, field: str) -> str:
    if type(value) is not str or _PROVIDER_ID.fullmatch(value) is None:
        _invalid(f"{field} must be a ProviderId")
    return value


def _validate_semantic_version(value: object, field: str) -> str:
    if type(value) is not str:
        _invalid(f"{field} must be a SemanticVersion")
    text = value
    if _SEMANTIC_VERSION.fullmatch(text) is None:
        _invalid(f"{field} must be a SemanticVersion")
    if any(int(component) > _SEMANTIC_VERSION_COMPONENT_MAX for component in text.split(".")):
        _invalid(f"{field} component exceeds 2147483647")
    return text


def _semantic_version_key(value: str) -> tuple[int, int, int]:
    _validate_semantic_version(value, "semantic version")
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def _validate_lower_sha256(value: object, field: str) -> str:
    if type(value) is not str or _LOWER_SHA256.fullmatch(value) is None:
        _invalid(f"{field} must be a LowerSha256")
    return value


def _validate_utc_second(value: object, field: str) -> str:
    if type(value) is not str:
        _invalid(f"{field} must be a UtcSecond")
    text = value
    if _UTC_SECOND.fullmatch(text) is None:
        _invalid(f"{field} must be a UtcSecond")
    year = int(text[0:4])
    month = int(text[5:7])
    day = int(text[8:10])
    hour = int(text[11:13])
    minute = int(text[14:16])
    second = int(text[17:19])
    try:
        parsed = datetime(year, month, day, hour, minute, second)
    except ValueError:
        _invalid(f"{field} must be a real UTC-second instant")
    roundtrip = (
        f"{parsed.year:04d}-{parsed.month:02d}-{parsed.day:02d}T"
        f"{parsed.hour:02d}:{parsed.minute:02d}:{parsed.second:02d}Z"
    )
    if roundtrip != text:
        _invalid(f"{field} must be a canonical UTC-second instant")
    return text


def _validate_canonical_text(value: object, field: str) -> str:
    if type(value) is not str:
        _invalid(f"{field} must be an exact string")
    text = value
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        _invalid(f"{field} must contain only Unicode scalar values")
    if unicodedata.normalize("NFC", text) != text:
        _invalid(f"{field} must already use Unicode NFC")
    if any(unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"} for character in text):
        _invalid(f"{field} contains a forbidden control, surrogate, or separator")
    return text


def _validate_trimmed_text(value: object, field: str, maximum: int) -> str:
    text = _validate_canonical_text(value, field)
    if not text or len(text) > maximum:
        _invalid(f"{field} must contain 1..{maximum} Unicode scalar values")
    if ord(text[0]) in _TRIM_CODEPOINTS or ord(text[-1]) in _TRIM_CODEPOINTS:
        _invalid(f"{field} must use the frozen TrimmedText boundary")
    return text


def _validate_fixed_bool(value: object, expected: bool, field: str) -> None:
    if type(value) is not bool or value is not expected:
        _invalid(f"{field} must be the exact boolean {str(expected).lower()}")


def _validate_fixed_zero(value: object, field: str) -> None:
    if type(value) is not int or value != 0:
        _invalid(f"{field} must be the exact integer 0")


def _validate_non_negative_int(value: object, field: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_STRICT_NON_NEGATIVE_INT:
        _invalid(f"{field} must be a StrictNonNegativeInt")
    return value


def _validate_enum[EnumT: StrEnum](
    value: object,
    expected: type[EnumT],
    field: str,
) -> EnumT:
    if type(value) is not expected:
        _invalid(f"{field} must be an exact {expected.__name__}")
    return value


def _enum_from_json[EnumT: StrEnum](
    value: object,
    expected: type[EnumT],
    field: str,
) -> EnumT:
    if type(value) is not str:
        _invalid(f"{field} must be an exact string")
    try:
        return expected(value)
    except ValueError:
        _invalid(f"{field} contains an unknown {expected.__name__} value")


def _require_tuple(value: object, field: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        _invalid(f"{field} must be an exact tuple")
    return cast(tuple[object, ...], value)


def _validate_text_tuple(
    value: object,
    *,
    field: str,
    minimum: int,
    maximum: int,
    item_maximum: int,
    sorted_values: bool = False,
) -> tuple[str, ...]:
    items = _require_tuple(value, field)
    if not minimum <= len(items) <= maximum:
        _invalid(f"{field} must contain {minimum}..{maximum} items")
    validated = tuple(
        _validate_trimmed_text(item, f"{field}[{index}]", item_maximum)
        for index, item in enumerate(items)
    )
    if len(set(validated)) != len(validated):
        _invalid(f"{field} items must be unique")
    if sorted_values and validated != tuple(sorted(validated)):
        _invalid(f"{field} must already use ascending Unicode code-point order")
    return validated


def _validate_enum_subset[EnumT: StrEnum](
    value: object,
    *,
    field: str,
    expected_type: type[EnumT],
    canonical_order: tuple[EnumT, ...],
    minimum: int,
    maximum: int,
) -> tuple[EnumT, ...]:
    items = _require_tuple(value, field)
    if not minimum <= len(items) <= maximum:
        _invalid(f"{field} must contain {minimum}..{maximum} items")
    validated = tuple(
        _validate_enum(item, expected_type, f"{field}[{index}]") for index, item in enumerate(items)
    )
    if len(set(validated)) != len(validated):
        _invalid(f"{field} items must be unique")
    rank = {item: index for index, item in enumerate(canonical_order)}
    if any(item not in rank for item in validated):
        _invalid(f"{field} contains a value outside its allowed subset")
    if tuple(rank[item] for item in validated) != tuple(sorted(rank[item] for item in validated)):
        _invalid(f"{field} must already use its frozen canonical order")
    return validated


@dataclass(frozen=True, slots=True)
class PromptConstraintSet:
    negative_prompt_constraints: tuple[str, ...]
    positive_prompt_constraints: tuple[str, ...]
    qc_expectations: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_text_tuple(
            self.negative_prompt_constraints,
            field="negative_prompt_constraints",
            minimum=1,
            maximum=32,
            item_maximum=1000,
        )
        _validate_text_tuple(
            self.positive_prompt_constraints,
            field="positive_prompt_constraints",
            minimum=1,
            maximum=32,
            item_maximum=1000,
        )
        _validate_text_tuple(
            self.qc_expectations,
            field="qc_expectations",
            minimum=1,
            maximum=32,
            item_maximum=1000,
        )


@dataclass(frozen=True, slots=True)
class CharacterReferenceAssetRecipe:
    background_requirements: tuple[str, ...]
    body_proportion_anchors: tuple[str, ...]
    expression_range: tuple[str, ...]
    face_identity_anchors: tuple[str, ...]
    forbidden_body_proportion_drift: tuple[str, ...]
    forbidden_hairstyle_drift: tuple[str, ...]
    forbidden_identity_drift: tuple[str, ...]
    forbidden_wardrobe_drift: tuple[str, ...]
    hairstyle_anchors: tuple[str, ...]
    recipe_kind: ReferenceAssetRecipeKind
    reference_asset_types: tuple[ReferenceAssetType, ...]
    required_primary_binding_fields: tuple[str, ...]
    sheet_layout_requirements: tuple[str, ...]
    wardrobe_anchors: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_enum(
            self.recipe_kind,
            ReferenceAssetRecipeKind,
            "character recipe_kind",
        )
        if self.recipe_kind is not ReferenceAssetRecipeKind.CHARACTER_REFERENCE:
            _invalid("character recipe_kind must be CHARACTER_REFERENCE")
        roles = _validate_enum_subset(
            self.reference_asset_types,
            field="character reference_asset_types",
            expected_type=ReferenceAssetType,
            canonical_order=_CHARACTER_REFERENCE_ASSET_TYPES,
            minimum=1,
            maximum=3,
        )
        if any(role not in _CHARACTER_REFERENCE_ASSET_TYPES for role in roles):
            _invalid("character recipe cannot contain a scene reference role")
        if (
            type(self.required_primary_binding_fields) is not tuple
            or any(type(item) is not str for item in self.required_primary_binding_fields)
            or self.required_primary_binding_fields != _CHARACTER_PRIMARY_BINDING_FIELDS
        ):
            _invalid("character required_primary_binding_fields must equal the frozen tuple")
        for field_name in (
            "background_requirements",
            "body_proportion_anchors",
            "expression_range",
            "face_identity_anchors",
            "forbidden_body_proportion_drift",
            "forbidden_hairstyle_drift",
            "forbidden_identity_drift",
            "forbidden_wardrobe_drift",
            "hairstyle_anchors",
            "sheet_layout_requirements",
            "wardrobe_anchors",
        ):
            _validate_text_tuple(
                getattr(self, field_name),
                field=field_name,
                minimum=1,
                maximum=16,
                item_maximum=1000,
            )


@dataclass(frozen=True, slots=True)
class SceneReferenceAssetRecipe:
    continuity_requirements: tuple[str, ...]
    forbidden_drift: tuple[str, ...]
    geography_anchors: tuple[str, ...]
    layout_requirements: tuple[str, ...]
    lighting_anchors: tuple[str, ...]
    material_anchors: tuple[str, ...]
    palette_anchors: tuple[str, ...]
    prop_placement_anchors: tuple[str, ...]
    recipe_kind: ReferenceAssetRecipeKind
    reference_asset_types: tuple[ReferenceAssetType, ...]
    required_primary_binding_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_enum(self.recipe_kind, ReferenceAssetRecipeKind, "scene recipe_kind")
        if self.recipe_kind is not ReferenceAssetRecipeKind.SCENE_REFERENCE:
            _invalid("scene recipe_kind must be SCENE_REFERENCE")
        roles = _validate_enum_subset(
            self.reference_asset_types,
            field="scene reference_asset_types",
            expected_type=ReferenceAssetType,
            canonical_order=_SCENE_REFERENCE_ASSET_TYPES,
            minimum=1,
            maximum=4,
        )
        if any(role not in _SCENE_REFERENCE_ASSET_TYPES for role in roles):
            _invalid("scene recipe cannot contain a character reference role")
        if (
            type(self.required_primary_binding_fields) is not tuple
            or any(type(item) is not str for item in self.required_primary_binding_fields)
            or self.required_primary_binding_fields != _SCENE_PRIMARY_BINDING_FIELDS
        ):
            _invalid("scene required_primary_binding_fields must equal the frozen tuple")
        for field_name in (
            "continuity_requirements",
            "forbidden_drift",
            "geography_anchors",
            "layout_requirements",
            "lighting_anchors",
            "material_anchors",
            "palette_anchors",
            "prop_placement_anchors",
        ):
            _validate_text_tuple(
                getattr(self, field_name),
                field=field_name,
                minimum=1,
                maximum=16,
                item_maximum=1000,
            )


ReferenceAssetRecipe = CharacterReferenceAssetRecipe | SceneReferenceAssetRecipe


@dataclass(frozen=True, slots=True)
class PromptSection:
    heading: str
    placeholder: PlaceholderId
    section_id: str

    def __post_init__(self) -> None:
        heading = _validate_trimmed_text(self.heading, "heading", 80)
        if any(character in heading for character in "{}:"):
            _invalid("heading must not contain braces or a colon")
        _validate_enum(self.placeholder, PlaceholderId, "placeholder")
        _validate_portable_id(self.section_id, "section_id")


@dataclass(frozen=True, slots=True)
class VisualPromptProfile:
    asset_purpose: AssetPurpose
    constraint_set: PromptConstraintSet
    narrative_contexts: tuple[NarrativeContext, ...]
    profile_id: str
    profile_version: str
    reference_asset_recipe: ReferenceAssetRecipe | None
    reference_asset_types: tuple[ReferenceAssetType, ...]
    renderer_version: str
    sections: tuple[PromptSection, ...]
    shot_type: ShotType
    visual_style_id: VisualStyleId

    def __post_init__(self) -> None:
        _validate_enum(self.asset_purpose, AssetPurpose, "asset_purpose")
        _require_exact_type(self.constraint_set, PromptConstraintSet, "constraint_set")
        contexts = _validate_enum_subset(
            self.narrative_contexts,
            field="narrative_contexts",
            expected_type=NarrativeContext,
            canonical_order=_NARRATIVE_CONTEXT_ORDER,
            minimum=1,
            maximum=5,
        )
        _validate_portable_id(self.profile_id, "profile_id")
        _validate_semantic_version(self.profile_version, "profile_version")
        roles = _validate_enum_subset(
            self.reference_asset_types,
            field="reference_asset_types",
            expected_type=ReferenceAssetType,
            canonical_order=_REFERENCE_ASSET_TYPE_ORDER,
            minimum=0,
            maximum=7,
        )
        _validate_semantic_version(self.renderer_version, "renderer_version")
        sections = _require_tuple(self.sections, "sections")
        if not 1 <= len(sections) <= 16:
            _invalid("sections must contain 1..16 items")
        if any(type(section) is not PromptSection for section in sections):
            _invalid("sections must contain exact PromptSection values")
        typed_sections = cast(tuple[PromptSection, ...], sections)
        if len({section.section_id for section in typed_sections}) != len(typed_sections):
            _invalid("section_id values must be unique within a profile")
        if len({section.heading for section in typed_sections}) != len(typed_sections):
            _invalid("section headings must be unique within a profile")
        placeholders = tuple(section.placeholder for section in typed_sections)
        if len(set(placeholders)) != len(placeholders):
            _invalid("section placeholders must be unique within a profile")
        _validate_enum(self.shot_type, ShotType, "shot_type")
        _validate_enum(self.visual_style_id, VisualStyleId, "visual_style_id")

        if self.asset_purpose is AssetPurpose.NARRATIVE_SHOT:
            if self.shot_type is not ShotType.NARRATIVE_FRAME:
                _invalid("narrative profiles must use NARRATIVE_FRAME")
            if roles:
                _invalid("narrative profiles must have no reference_asset_types")
            if self.reference_asset_recipe is not None:
                _invalid("narrative profiles must have a null reference recipe")
            if NarrativeContext.REFERENCE_DEVELOPMENT in contexts:
                _invalid("narrative profiles cannot use REFERENCE_DEVELOPMENT")
            expected_placeholders = _NARRATIVE_PLACEHOLDERS
        elif self.asset_purpose is AssetPurpose.CHARACTER_REFERENCE_ASSET:
            if self.shot_type is not ShotType.REFERENCE_SHEET:
                _invalid("character reference profiles must use REFERENCE_SHEET")
            if any(role not in _CHARACTER_REFERENCE_ASSET_TYPES for role in roles):
                _invalid("character profiles cannot contain scene reference roles")
            if type(self.reference_asset_recipe) is not CharacterReferenceAssetRecipe:
                _invalid("character profiles require a character reference recipe")
            character_recipe = self.reference_asset_recipe
            if character_recipe.reference_asset_types != roles:
                _invalid("character profile and recipe role arrays must match exactly")
            if NarrativeContext.REFERENCE_DEVELOPMENT not in contexts:
                _invalid("reference profiles must include REFERENCE_DEVELOPMENT")
            expected_placeholders = _CHARACTER_REFERENCE_PLACEHOLDERS
        else:
            if self.shot_type is not ShotType.REFERENCE_SHEET:
                _invalid("scene reference profiles must use REFERENCE_SHEET")
            if any(role not in _SCENE_REFERENCE_ASSET_TYPES for role in roles):
                _invalid("scene profiles cannot contain character reference roles")
            if type(self.reference_asset_recipe) is not SceneReferenceAssetRecipe:
                _invalid("scene profiles require a scene reference recipe")
            scene_recipe = self.reference_asset_recipe
            if scene_recipe.reference_asset_types != roles:
                _invalid("scene profile and recipe role arrays must match exactly")
            if NarrativeContext.REFERENCE_DEVELOPMENT not in contexts:
                _invalid("reference profiles must include REFERENCE_DEVELOPMENT")
            expected_placeholders = _SCENE_REFERENCE_PLACEHOLDERS
        if frozenset(placeholders) != expected_placeholders:
            _invalid("sections must contain the exact purpose-specific placeholder set")

    @property
    def profile_sha256(self) -> str:
        """Return the exact domain-separated semantic identity."""

        return visual_prompt_profile_sha256(self)


@dataclass(frozen=True, slots=True)
class ProviderSyntaxCompatibilityObservation:
    compatibility_status: ProviderSyntaxCompatibilityStatus
    provider_id: str
    provider_profile_id: str
    provider_profile_version: str

    def __post_init__(self) -> None:
        _validate_enum(
            self.compatibility_status,
            ProviderSyntaxCompatibilityStatus,
            "compatibility_status",
        )
        _validate_provider_id(self.provider_id, "provider_id")
        _validate_portable_id(self.provider_profile_id, "provider_profile_id")
        _validate_portable_id(self.provider_profile_version, "provider_profile_version")

    @property
    def identity_key(self) -> tuple[str, str, str]:
        return self.provider_id, self.provider_profile_id, self.provider_profile_version


@dataclass(frozen=True, slots=True)
class PromptProfileCatalogEntry:
    description: str
    display_name: str
    eligible_for_asset_promotion: bool
    grants_execution_authority: bool
    grants_qualification: bool
    grants_rights: bool
    offline_render_admission_status: OfflineRenderAdmissionStatus
    profile: VisualPromptProfile
    profile_text_provenance_status: ProfileTextProvenanceStatus
    provider_syntax_compatibility_observations: tuple[ProviderSyntaxCompatibilityObservation, ...]

    def __post_init__(self) -> None:
        _validate_trimmed_text(self.description, "description", 1000)
        _validate_trimmed_text(self.display_name, "display_name", 128)
        _validate_fixed_bool(
            self.eligible_for_asset_promotion,
            False,
            "eligible_for_asset_promotion",
        )
        _validate_fixed_bool(
            self.grants_execution_authority,
            False,
            "grants_execution_authority",
        )
        _validate_fixed_bool(self.grants_qualification, False, "grants_qualification")
        _validate_fixed_bool(self.grants_rights, False, "grants_rights")
        _validate_enum(
            self.offline_render_admission_status,
            OfflineRenderAdmissionStatus,
            "offline_render_admission_status",
        )
        _require_exact_type(self.profile, VisualPromptProfile, "profile")
        _validate_enum(
            self.profile_text_provenance_status,
            ProfileTextProvenanceStatus,
            "profile_text_provenance_status",
        )
        observations = _require_tuple(
            self.provider_syntax_compatibility_observations,
            "provider_syntax_compatibility_observations",
        )
        if len(observations) > 32:
            _invalid("provider_syntax_compatibility_observations must contain 0..32 items")
        if any(type(item) is not ProviderSyntaxCompatibilityObservation for item in observations):
            _invalid("provider observations must use exact immutable observation values")
        typed = cast(tuple[ProviderSyntaxCompatibilityObservation, ...], observations)
        keys = tuple(item.identity_key for item in typed)
        if len(set(keys)) != len(keys):
            _invalid("provider observation identities must be unique")
        if keys != tuple(sorted(keys)):
            _invalid("provider observations must already use canonical identity order")

    @property
    def profile_sha256(self) -> str:
        return visual_prompt_profile_sha256(self.profile)


@dataclass(frozen=True, slots=True)
class PromptProfileCatalog:
    automated_execution_allowed: bool
    authorized_attempts: int
    authorized_cost_cny: int
    catalog_reviewer_ref: str
    catalog_reviewed_at: str
    catalog_version: str
    current_gate: str
    execution_authorized: bool
    generation_authorized: bool
    posts_allowed: int
    profiles: tuple[PromptProfileCatalogEntry, ...]
    provider_requests: int
    provider_state: str
    publication_allowed: bool
    publication_authorized: bool
    remote_processing_allowed: bool
    renderer_id: str
    renderer_version: str
    retention_allowed: bool
    source_revision: str
    training_allowed: bool
    usage_restriction: str

    def __post_init__(self) -> None:
        _validate_fixed_bool(
            self.automated_execution_allowed,
            False,
            "automated_execution_allowed",
        )
        _validate_fixed_zero(self.authorized_attempts, "authorized_attempts")
        _validate_fixed_zero(self.authorized_cost_cny, "authorized_cost_cny")
        _validate_portable_id(self.catalog_reviewer_ref, "catalog_reviewer_ref")
        _validate_utc_second(self.catalog_reviewed_at, "catalog_reviewed_at")
        _validate_semantic_version(self.catalog_version, "catalog_version")
        if type(self.current_gate) is not str or self.current_gate != CURRENT_GATE:
            _invalid("current_gate must be HUMAN_GATE")
        _validate_fixed_bool(self.execution_authorized, False, "execution_authorized")
        _validate_fixed_bool(self.generation_authorized, False, "generation_authorized")
        _validate_fixed_zero(self.posts_allowed, "posts_allowed")
        entries = _require_tuple(self.profiles, "profiles")
        if not 1 <= len(entries) <= 64:
            _invalid("profiles must contain 1..64 entries")
        if any(type(entry) is not PromptProfileCatalogEntry for entry in entries):
            _invalid("profiles must contain exact PromptProfileCatalogEntry values")
        typed_entries = cast(tuple[PromptProfileCatalogEntry, ...], entries)
        identity_keys = tuple(
            (
                entry.profile.profile_id,
                _semantic_version_key(entry.profile.profile_version),
            )
            for entry in typed_entries
        )
        if identity_keys != tuple(sorted(identity_keys)):
            _invalid("profiles must already use canonical profile identity order")
        if len(set(identity_keys)) != len(identity_keys):
            _invalid("profile identity pairs must be unique")
        _validate_fixed_zero(self.provider_requests, "provider_requests")
        if type(self.provider_state) is not str or self.provider_state != PROVIDER_STATE:
            _invalid("provider_state must be NOT_AUTHORIZED")
        _validate_fixed_bool(self.publication_allowed, False, "publication_allowed")
        _validate_fixed_bool(self.publication_authorized, False, "publication_authorized")
        _validate_fixed_bool(
            self.remote_processing_allowed,
            False,
            "remote_processing_allowed",
        )
        if type(self.renderer_id) is not str or self.renderer_id != VISUAL_PROMPT_RENDERER_ID:
            _invalid("renderer_id must equal the frozen renderer identity")
        _validate_semantic_version(self.renderer_version, "renderer_version")
        if self.renderer_version != VISUAL_PROMPT_RENDERER_VERSION:
            _invalid("renderer_version must equal 1.0.0")
        if any(entry.profile.renderer_version != self.renderer_version for entry in typed_entries):
            _invalid("every profile renderer_version must equal the catalog renderer_version")
        _validate_fixed_bool(self.retention_allowed, False, "retention_allowed")
        _validate_portable_id(self.source_revision, "source_revision")
        _validate_fixed_bool(self.training_allowed, False, "training_allowed")
        if type(self.usage_restriction) is not str or self.usage_restriction != USAGE_RESTRICTION:
            _invalid("usage_restriction must equal the frozen manual-review restriction")

    @property
    def catalog_sha256(self) -> str:
        """Return the exact domain-separated catalog identity."""

        return prompt_profile_catalog_sha256(self)


@dataclass(frozen=True, slots=True, init=False)
class VisualPromptProfileSnapshot:
    profile: VisualPromptProfile
    profile_sha256: str
    catalog_version: str
    catalog_sha256: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        """Reject construction outside the exact resolver admission path."""

        _invalid("VisualPromptProfileSnapshot is resolver-only")

    def _validate_resolved_value(self) -> None:
        _require_exact_type(self.profile, VisualPromptProfile, "profile")
        _validate_lower_sha256(self.profile_sha256, "profile_sha256")
        if self.profile_sha256 != visual_prompt_profile_sha256(self.profile):
            _invalid("profile_sha256 does not bind the exact profile projection")
        _validate_semantic_version(self.catalog_version, "catalog_version")
        _validate_lower_sha256(self.catalog_sha256, "catalog_sha256")

    @property
    def profile_id(self) -> str:
        return self.profile.profile_id

    @property
    def profile_version(self) -> str:
        return self.profile.profile_version

    @property
    def asset_purpose(self) -> AssetPurpose:
        return self.profile.asset_purpose


def _make_resolved_visual_prompt_profile_snapshot(
    *,
    profile: VisualPromptProfile,
    profile_sha256: str,
    catalog_version: str,
    catalog_sha256: str,
) -> VisualPromptProfileSnapshot:
    """Construct a Snapshot only after the resolver has closed catalog admission."""

    snapshot = object.__new__(VisualPromptProfileSnapshot)
    object.__setattr__(snapshot, "profile", profile)
    object.__setattr__(snapshot, "profile_sha256", profile_sha256)
    object.__setattr__(snapshot, "catalog_version", catalog_version)
    object.__setattr__(snapshot, "catalog_sha256", catalog_sha256)
    snapshot._validate_resolved_value()
    return snapshot


@dataclass(frozen=True, slots=True)
class CharacterAssetPromptBinding:
    asset_content_sha256: str
    asset_version_id: str
    character_id: str

    def __post_init__(self) -> None:
        _validate_lower_sha256(self.asset_content_sha256, "asset_content_sha256")
        _validate_portable_id(self.asset_version_id, "asset_version_id")
        _validate_portable_id(self.character_id, "character_id")


@dataclass(frozen=True, slots=True)
class SceneAssetPromptBinding:
    asset_content_sha256: str
    asset_version_id: str
    scene_id: str

    def __post_init__(self) -> None:
        _validate_lower_sha256(self.asset_content_sha256, "asset_content_sha256")
        _validate_portable_id(self.asset_version_id, "asset_version_id")
        _validate_portable_id(self.scene_id, "scene_id")


@dataclass(frozen=True, slots=True)
class DialoguePromptLine:
    character_id: str
    line_id: str
    ordinal: int
    text: str

    def __post_init__(self) -> None:
        _validate_portable_id(self.character_id, "dialogue character_id")
        _validate_portable_id(self.line_id, "dialogue line_id")
        _validate_non_negative_int(self.ordinal, "dialogue ordinal")
        _validate_trimmed_text(self.text, "dialogue text", 2000)


CharacterTextMap = tuple[tuple[str, str], ...]


def _validate_character_bindings(
    value: object,
    *,
    minimum: int,
    maximum: int,
) -> tuple[CharacterAssetPromptBinding, ...]:
    items = _require_tuple(value, "character_asset_bindings")
    if not minimum <= len(items) <= maximum:
        _invalid(f"character_asset_bindings must contain {minimum}..{maximum} items")
    if any(type(item) is not CharacterAssetPromptBinding for item in items):
        _invalid("character_asset_bindings must contain exact binding values")
    typed = cast(tuple[CharacterAssetPromptBinding, ...], items)
    character_ids = tuple(item.character_id for item in typed)
    asset_version_ids = tuple(item.asset_version_id for item in typed)
    if character_ids != tuple(sorted(character_ids)):
        _invalid("character_asset_bindings must already be sorted by character_id")
    if len(set(character_ids)) != len(character_ids):
        _invalid("character IDs must be unique")
    if len(set(asset_version_ids)) != len(asset_version_ids):
        _invalid("character asset version IDs must be unique")
    return typed


def _validate_character_text_map(
    value: object,
    *,
    field: str,
    expected_character_ids: tuple[str, ...],
) -> CharacterTextMap:
    items = _require_tuple(value, field)
    result: list[tuple[str, str]] = []
    for index, item in enumerate(items):
        if type(item) is not tuple or len(item) != 2:
            _invalid(f"{field}[{index}] must be an exact two-item tuple")
        pair = cast(tuple[object, object], item)
        key = _validate_portable_id(pair[0], f"{field}[{index}] key")
        text = _validate_trimmed_text(pair[1], f"{field}[{index}] value", 512)
        result.append((key, text))
    keys = tuple(key for key, _value in result)
    if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
        _invalid(f"{field} must contain unique keys in ascending order")
    if keys != expected_character_ids:
        _invalid(f"{field} key set must equal the character binding key set")
    return tuple(result)


def _validate_dialogue(
    value: object,
    *,
    character_ids: tuple[str, ...],
) -> tuple[DialoguePromptLine, ...]:
    items = _require_tuple(value, "dialogue")
    if len(items) > 64:
        _invalid("dialogue must contain 0..64 lines")
    if any(type(item) is not DialoguePromptLine for item in items):
        _invalid("dialogue must contain exact DialoguePromptLine values")
    typed = cast(tuple[DialoguePromptLine, ...], items)
    ordinals = tuple(item.ordinal for item in typed)
    line_ids = tuple(item.line_id for item in typed)
    if any(first >= second for first, second in zip(ordinals, ordinals[1:], strict=False)):
        _invalid("dialogue must already be in strictly ascending ordinal order")
    if len(set(line_ids)) != len(line_ids):
        _invalid("dialogue line_id values must be unique")
    if any(item.character_id not in character_ids for item in typed):
        _invalid("every dialogue character_id must have a character binding")
    return typed


@dataclass(frozen=True, slots=True)
class NarrativeShotPromptRenderInput:
    action: str
    camera_angle: CameraAngleV1
    camera_movement: CameraMovementV1
    character_asset_bindings: tuple[CharacterAssetPromptBinding, ...]
    continuity_notes: str
    dialogue: tuple[DialoguePromptLine, ...]
    emotion_by_character: CharacterTextMap
    input_kind: AssetPurpose
    narrative: str
    props: tuple[str, ...]
    scene_asset_binding: SceneAssetPromptBinding
    shot_size: ShotSizeV1
    visual_direction: str
    wardrobe_by_character: CharacterTextMap

    def __post_init__(self) -> None:
        _validate_trimmed_text(self.action, "action", 2000)
        _validate_enum(self.camera_angle, CameraAngleV1, "camera_angle")
        _validate_enum(self.camera_movement, CameraMovementV1, "camera_movement")
        bindings = _validate_character_bindings(
            self.character_asset_bindings,
            minimum=0,
            maximum=2,
        )
        character_ids = tuple(item.character_id for item in bindings)
        _validate_trimmed_text(self.continuity_notes, "continuity_notes", 2000)
        dialogue = _validate_dialogue(self.dialogue, character_ids=character_ids)
        _validate_character_text_map(
            self.emotion_by_character,
            field="emotion_by_character",
            expected_character_ids=character_ids,
        )
        _validate_enum(self.input_kind, AssetPurpose, "input_kind")
        if self.input_kind is not AssetPurpose.NARRATIVE_SHOT:
            _invalid("narrative input_kind must be NARRATIVE_SHOT")
        _validate_trimmed_text(self.narrative, "narrative", 4000)
        _validate_text_tuple(
            self.props,
            field="props",
            minimum=0,
            maximum=16,
            item_maximum=128,
            sorted_values=True,
        )
        _require_exact_type(
            self.scene_asset_binding,
            SceneAssetPromptBinding,
            "scene_asset_binding",
        )
        _validate_enum(self.shot_size, ShotSizeV1, "shot_size")
        _validate_trimmed_text(self.visual_direction, "visual_direction", 4000)
        _validate_character_text_map(
            self.wardrobe_by_character,
            field="wardrobe_by_character",
            expected_character_ids=character_ids,
        )
        if not bindings and dialogue:
            _invalid("a narrative input with no characters must have empty dialogue")


@dataclass(frozen=True, slots=True)
class CharacterReferencePromptRenderInput:
    action: str
    character_asset_bindings: tuple[CharacterAssetPromptBinding, ...]
    continuity_notes: str
    emotion_by_character: CharacterTextMap
    input_kind: AssetPurpose
    narrative: str
    visual_direction: str
    wardrobe_by_character: CharacterTextMap

    def __post_init__(self) -> None:
        _validate_trimmed_text(self.action, "action", 2000)
        bindings = _validate_character_bindings(
            self.character_asset_bindings,
            minimum=1,
            maximum=1,
        )
        character_ids = tuple(item.character_id for item in bindings)
        _validate_trimmed_text(self.continuity_notes, "continuity_notes", 2000)
        _validate_character_text_map(
            self.emotion_by_character,
            field="emotion_by_character",
            expected_character_ids=character_ids,
        )
        _validate_enum(self.input_kind, AssetPurpose, "input_kind")
        if self.input_kind is not AssetPurpose.CHARACTER_REFERENCE_ASSET:
            _invalid("character reference input_kind must be CHARACTER_REFERENCE_ASSET")
        _validate_trimmed_text(self.narrative, "narrative", 4000)
        _validate_trimmed_text(self.visual_direction, "visual_direction", 4000)
        _validate_character_text_map(
            self.wardrobe_by_character,
            field="wardrobe_by_character",
            expected_character_ids=character_ids,
        )


@dataclass(frozen=True, slots=True)
class SceneReferencePromptRenderInput:
    action: str
    continuity_notes: str
    input_kind: AssetPurpose
    narrative: str
    props: tuple[str, ...]
    scene_asset_binding: SceneAssetPromptBinding
    visual_direction: str

    def __post_init__(self) -> None:
        _validate_trimmed_text(self.action, "action", 2000)
        _validate_trimmed_text(self.continuity_notes, "continuity_notes", 2000)
        _validate_enum(self.input_kind, AssetPurpose, "input_kind")
        if self.input_kind is not AssetPurpose.SCENE_REFERENCE_ASSET:
            _invalid("scene reference input_kind must be SCENE_REFERENCE_ASSET")
        _validate_trimmed_text(self.narrative, "narrative", 4000)
        _validate_text_tuple(
            self.props,
            field="props",
            minimum=0,
            maximum=16,
            item_maximum=128,
            sorted_values=True,
        )
        _require_exact_type(
            self.scene_asset_binding,
            SceneAssetPromptBinding,
            "scene_asset_binding",
        )
        _validate_trimmed_text(self.visual_direction, "visual_direction", 4000)


PromptRenderInput = (
    NarrativeShotPromptRenderInput
    | CharacterReferencePromptRenderInput
    | SceneReferencePromptRenderInput
)


@dataclass(frozen=True, slots=True)
class PromptRenderReceipt:
    receipt_purpose: str
    profile_id: str
    profile_version: str
    profile_sha256: str
    catalog_version: str
    catalog_sha256: str
    render_input_sha256: str
    renderer_id: str
    renderer_version: str
    prompt_sha256: str
    prompt_size_bytes: int
    current_gate: str
    provider_state: str
    generation_authorized: bool
    execution_authorized: bool
    publication_authorized: bool
    remote_processing_allowed: bool
    retention_allowed: bool
    training_allowed: bool
    publication_allowed: bool
    automated_execution_allowed: bool
    authorized_attempts: int
    authorized_cost_cny: int
    posts_allowed: int
    provider_requests: int
    usage_restriction: str
    grants_rights: bool
    grants_qualification: bool
    grants_execution_authority: bool
    eligible_for_asset_promotion: bool
    replaces_rights_manifest: bool
    prompt_render_receipt_sha256: str

    def __post_init__(self) -> None:
        if (
            type(self.receipt_purpose) is not str
            or self.receipt_purpose != PROMPT_RENDER_RECEIPT_PURPOSE
        ):
            _invalid("receipt_purpose must equal the frozen process-evidence literal")
        _validate_portable_id(self.profile_id, "receipt profile_id")
        _validate_semantic_version(self.profile_version, "receipt profile_version")
        _validate_lower_sha256(self.profile_sha256, "receipt profile_sha256")
        _validate_semantic_version(self.catalog_version, "receipt catalog_version")
        _validate_lower_sha256(self.catalog_sha256, "receipt catalog_sha256")
        _validate_lower_sha256(self.render_input_sha256, "receipt render_input_sha256")
        if type(self.renderer_id) is not str or self.renderer_id != VISUAL_PROMPT_RENDERER_ID:
            _invalid("receipt renderer_id must equal the frozen renderer identity")
        if (
            type(self.renderer_version) is not str
            or self.renderer_version != VISUAL_PROMPT_RENDERER_VERSION
        ):
            _invalid("receipt renderer_version must equal 1.0.0")
        _validate_lower_sha256(self.prompt_sha256, "receipt prompt_sha256")
        if type(self.prompt_size_bytes) is not int or not 1 <= self.prompt_size_bytes <= 65_536:
            _invalid("prompt_size_bytes must be an exact integer in 1..65536")
        if type(self.current_gate) is not str or self.current_gate != CURRENT_GATE:
            _invalid("receipt current_gate must be HUMAN_GATE")
        if type(self.provider_state) is not str or self.provider_state != PROVIDER_STATE:
            _invalid("receipt provider_state must be NOT_AUTHORIZED")
        for field_name in (
            "generation_authorized",
            "execution_authorized",
            "publication_authorized",
            "remote_processing_allowed",
            "retention_allowed",
            "training_allowed",
            "publication_allowed",
            "automated_execution_allowed",
            "grants_rights",
            "grants_qualification",
            "grants_execution_authority",
            "eligible_for_asset_promotion",
            "replaces_rights_manifest",
        ):
            _validate_fixed_bool(getattr(self, field_name), False, f"receipt {field_name}")
        for field_name in (
            "authorized_attempts",
            "authorized_cost_cny",
            "posts_allowed",
            "provider_requests",
        ):
            _validate_fixed_zero(getattr(self, field_name), f"receipt {field_name}")
        if type(self.usage_restriction) is not str or self.usage_restriction != USAGE_RESTRICTION:
            _invalid("receipt usage_restriction must equal the frozen manual-review restriction")
        _validate_lower_sha256(
            self.prompt_render_receipt_sha256,
            "prompt_render_receipt_sha256",
        )
        expected = _semantic_sha256(
            PROMPT_RENDER_RECEIPT_SHA256_DOMAIN,
            prompt_render_receipt_projection(self),
        )
        if self.prompt_render_receipt_sha256 != expected:
            _invalid("prompt_render_receipt_sha256 does not bind the exact receipt projection")


def prompt_constraint_set_projection(value: PromptConstraintSet) -> dict[str, object]:
    _require_exact_type(value, PromptConstraintSet, "constraint_set")
    return {
        "negative_prompt_constraints": list(value.negative_prompt_constraints),
        "positive_prompt_constraints": list(value.positive_prompt_constraints),
        "qc_expectations": list(value.qc_expectations),
    }


def character_reference_asset_recipe_projection(
    value: CharacterReferenceAssetRecipe,
) -> dict[str, object]:
    _require_exact_type(value, CharacterReferenceAssetRecipe, "character recipe")
    return {
        "background_requirements": list(value.background_requirements),
        "body_proportion_anchors": list(value.body_proportion_anchors),
        "expression_range": list(value.expression_range),
        "face_identity_anchors": list(value.face_identity_anchors),
        "forbidden_body_proportion_drift": list(value.forbidden_body_proportion_drift),
        "forbidden_hairstyle_drift": list(value.forbidden_hairstyle_drift),
        "forbidden_identity_drift": list(value.forbidden_identity_drift),
        "forbidden_wardrobe_drift": list(value.forbidden_wardrobe_drift),
        "hairstyle_anchors": list(value.hairstyle_anchors),
        "recipe_kind": value.recipe_kind.value,
        "reference_asset_types": [item.value for item in value.reference_asset_types],
        "required_primary_binding_fields": list(value.required_primary_binding_fields),
        "sheet_layout_requirements": list(value.sheet_layout_requirements),
        "wardrobe_anchors": list(value.wardrobe_anchors),
    }


def scene_reference_asset_recipe_projection(
    value: SceneReferenceAssetRecipe,
) -> dict[str, object]:
    _require_exact_type(value, SceneReferenceAssetRecipe, "scene recipe")
    return {
        "continuity_requirements": list(value.continuity_requirements),
        "forbidden_drift": list(value.forbidden_drift),
        "geography_anchors": list(value.geography_anchors),
        "layout_requirements": list(value.layout_requirements),
        "lighting_anchors": list(value.lighting_anchors),
        "material_anchors": list(value.material_anchors),
        "palette_anchors": list(value.palette_anchors),
        "prop_placement_anchors": list(value.prop_placement_anchors),
        "recipe_kind": value.recipe_kind.value,
        "reference_asset_types": [item.value for item in value.reference_asset_types],
        "required_primary_binding_fields": list(value.required_primary_binding_fields),
    }


def _reference_asset_recipe_projection(
    value: ReferenceAssetRecipe | None,
) -> dict[str, object] | None:
    if value is None:
        return None
    if type(value) is CharacterReferenceAssetRecipe:
        return character_reference_asset_recipe_projection(value)
    if type(value) is SceneReferenceAssetRecipe:
        return scene_reference_asset_recipe_projection(value)
    _invalid("reference_asset_recipe must use one exact tagged-union member")


def prompt_section_projection(value: PromptSection) -> dict[str, object]:
    _require_exact_type(value, PromptSection, "section")
    return {
        "heading": value.heading,
        "placeholder": value.placeholder.value,
        "section_id": value.section_id,
    }


def visual_prompt_profile_projection(value: VisualPromptProfile) -> dict[str, object]:
    """Project exactly the profile fields frozen by ADR-040."""

    _require_exact_type(value, VisualPromptProfile, "profile")
    return {
        "asset_purpose": value.asset_purpose.value,
        "constraint_set": prompt_constraint_set_projection(value.constraint_set),
        "narrative_contexts": [item.value for item in value.narrative_contexts],
        "profile_id": value.profile_id,
        "profile_version": value.profile_version,
        "reference_asset_recipe": _reference_asset_recipe_projection(value.reference_asset_recipe),
        "reference_asset_types": [item.value for item in value.reference_asset_types],
        "renderer_version": value.renderer_version,
        "sections": [prompt_section_projection(section) for section in value.sections],
        "shot_type": value.shot_type.value,
        "visual_style_id": value.visual_style_id.value,
    }


def provider_syntax_compatibility_observation_projection(
    value: ProviderSyntaxCompatibilityObservation,
) -> dict[str, object]:
    _require_exact_type(
        value,
        ProviderSyntaxCompatibilityObservation,
        "provider compatibility observation",
    )
    return {
        "compatibility_status": value.compatibility_status.value,
        "provider_id": value.provider_id,
        "provider_profile_id": value.provider_profile_id,
        "provider_profile_version": value.provider_profile_version,
    }


def prompt_profile_catalog_entry_projection(
    value: PromptProfileCatalogEntry,
) -> dict[str, object]:
    _require_exact_type(value, PromptProfileCatalogEntry, "catalog entry")
    return {
        "description": value.description,
        "display_name": value.display_name,
        "eligible_for_asset_promotion": value.eligible_for_asset_promotion,
        "grants_execution_authority": value.grants_execution_authority,
        "grants_qualification": value.grants_qualification,
        "grants_rights": value.grants_rights,
        "offline_render_admission_status": value.offline_render_admission_status.value,
        "profile_ref": {
            "profile_id": value.profile.profile_id,
            "profile_sha256": value.profile_sha256,
            "profile_version": value.profile.profile_version,
        },
        "profile_text_provenance_status": value.profile_text_provenance_status.value,
        "provider_syntax_compatibility_observations": [
            provider_syntax_compatibility_observation_projection(item)
            for item in value.provider_syntax_compatibility_observations
        ],
    }


def prompt_profile_catalog_projection(value: PromptProfileCatalog) -> dict[str, object]:
    """Project exactly the catalog fields frozen by ADR-040."""

    _require_exact_type(value, PromptProfileCatalog, "catalog")
    return {
        "automated_execution_allowed": value.automated_execution_allowed,
        "authorized_attempts": value.authorized_attempts,
        "authorized_cost_cny": value.authorized_cost_cny,
        "catalog_reviewer_ref": value.catalog_reviewer_ref,
        "catalog_reviewed_at": value.catalog_reviewed_at,
        "catalog_version": value.catalog_version,
        "current_gate": value.current_gate,
        "execution_authorized": value.execution_authorized,
        "generation_authorized": value.generation_authorized,
        "posts_allowed": value.posts_allowed,
        "profile_entries": [
            prompt_profile_catalog_entry_projection(entry) for entry in value.profiles
        ],
        "provider_requests": value.provider_requests,
        "provider_state": value.provider_state,
        "publication_allowed": value.publication_allowed,
        "publication_authorized": value.publication_authorized,
        "remote_processing_allowed": value.remote_processing_allowed,
        "renderer_id": value.renderer_id,
        "renderer_version": value.renderer_version,
        "retention_allowed": value.retention_allowed,
        "source_revision": value.source_revision,
        "training_allowed": value.training_allowed,
        "usage_restriction": value.usage_restriction,
    }


def visual_prompt_profile_snapshot_projection(
    value: VisualPromptProfileSnapshot,
) -> dict[str, object]:
    """Return the explicitly flattened, non-hashed Snapshot representation."""

    _require_exact_type(value, VisualPromptProfileSnapshot, "snapshot")
    profile = visual_prompt_profile_projection(value.profile)
    return {
        "asset_purpose": profile["asset_purpose"],
        "catalog_sha256": value.catalog_sha256,
        "catalog_version": value.catalog_version,
        "constraint_set": profile["constraint_set"],
        "narrative_contexts": profile["narrative_contexts"],
        "profile_id": profile["profile_id"],
        "profile_sha256": value.profile_sha256,
        "profile_version": profile["profile_version"],
        "reference_asset_recipe": profile["reference_asset_recipe"],
        "reference_asset_types": profile["reference_asset_types"],
        "renderer_version": profile["renderer_version"],
        "sections": profile["sections"],
        "shot_type": profile["shot_type"],
        "visual_style_id": profile["visual_style_id"],
    }


def character_asset_prompt_binding_projection(
    value: CharacterAssetPromptBinding,
) -> dict[str, object]:
    _require_exact_type(value, CharacterAssetPromptBinding, "character binding")
    return {
        "asset_content_sha256": value.asset_content_sha256,
        "asset_version_id": value.asset_version_id,
        "character_id": value.character_id,
    }


def scene_asset_prompt_binding_projection(value: SceneAssetPromptBinding) -> dict[str, object]:
    _require_exact_type(value, SceneAssetPromptBinding, "scene binding")
    return {
        "asset_content_sha256": value.asset_content_sha256,
        "asset_version_id": value.asset_version_id,
        "scene_id": value.scene_id,
    }


def dialogue_prompt_line_projection(value: DialoguePromptLine) -> dict[str, object]:
    _require_exact_type(value, DialoguePromptLine, "dialogue line")
    return {
        "character_id": value.character_id,
        "line_id": value.line_id,
        "ordinal": value.ordinal,
        "text": value.text,
    }


def _character_text_map_projection(value: CharacterTextMap) -> dict[str, object]:
    return {key: text for key, text in value}


def prompt_render_input_projection(value: PromptRenderInput) -> dict[str, object]:
    """Project one exact tagged input without a Snapshot or derived digest."""

    if type(value) is NarrativeShotPromptRenderInput:
        narrative = value
        return {
            "action": narrative.action,
            "camera_angle": narrative.camera_angle.value,
            "camera_movement": narrative.camera_movement.value,
            "character_asset_bindings": [
                character_asset_prompt_binding_projection(item)
                for item in narrative.character_asset_bindings
            ],
            "continuity_notes": narrative.continuity_notes,
            "dialogue": [dialogue_prompt_line_projection(item) for item in narrative.dialogue],
            "emotion_by_character": _character_text_map_projection(narrative.emotion_by_character),
            "input_kind": narrative.input_kind.value,
            "narrative": narrative.narrative,
            "props": list(narrative.props),
            "scene_asset_binding": scene_asset_prompt_binding_projection(
                narrative.scene_asset_binding
            ),
            "shot_size": narrative.shot_size.value,
            "visual_direction": narrative.visual_direction,
            "wardrobe_by_character": _character_text_map_projection(
                narrative.wardrobe_by_character
            ),
        }
    if type(value) is CharacterReferencePromptRenderInput:
        character = value
        return {
            "action": character.action,
            "character_asset_bindings": [
                character_asset_prompt_binding_projection(item)
                for item in character.character_asset_bindings
            ],
            "continuity_notes": character.continuity_notes,
            "emotion_by_character": _character_text_map_projection(character.emotion_by_character),
            "input_kind": character.input_kind.value,
            "narrative": character.narrative,
            "visual_direction": character.visual_direction,
            "wardrobe_by_character": _character_text_map_projection(
                character.wardrobe_by_character
            ),
        }
    if type(value) is SceneReferencePromptRenderInput:
        scene = value
        return {
            "action": scene.action,
            "continuity_notes": scene.continuity_notes,
            "input_kind": scene.input_kind.value,
            "narrative": scene.narrative,
            "props": list(scene.props),
            "scene_asset_binding": scene_asset_prompt_binding_projection(scene.scene_asset_binding),
            "visual_direction": scene.visual_direction,
        }
    _invalid("render input must use one exact tagged-union member")


def prompt_render_receipt_projection(value: PromptRenderReceipt) -> dict[str, object]:
    """Project every Receipt semantic field while excluding only its self digest."""

    _require_exact_type(value, PromptRenderReceipt, "Prompt Render Receipt")
    return {
        "receipt_purpose": value.receipt_purpose,
        "profile_id": value.profile_id,
        "profile_version": value.profile_version,
        "profile_sha256": value.profile_sha256,
        "catalog_version": value.catalog_version,
        "catalog_sha256": value.catalog_sha256,
        "render_input_sha256": value.render_input_sha256,
        "renderer_id": value.renderer_id,
        "renderer_version": value.renderer_version,
        "prompt_sha256": value.prompt_sha256,
        "prompt_size_bytes": value.prompt_size_bytes,
        "current_gate": value.current_gate,
        "provider_state": value.provider_state,
        "generation_authorized": value.generation_authorized,
        "execution_authorized": value.execution_authorized,
        "publication_authorized": value.publication_authorized,
        "remote_processing_allowed": value.remote_processing_allowed,
        "retention_allowed": value.retention_allowed,
        "training_allowed": value.training_allowed,
        "publication_allowed": value.publication_allowed,
        "automated_execution_allowed": value.automated_execution_allowed,
        "authorized_attempts": value.authorized_attempts,
        "authorized_cost_cny": value.authorized_cost_cny,
        "posts_allowed": value.posts_allowed,
        "provider_requests": value.provider_requests,
        "usage_restriction": value.usage_restriction,
        "grants_rights": value.grants_rights,
        "grants_qualification": value.grants_qualification,
        "grants_execution_authority": value.grants_execution_authority,
        "eligible_for_asset_promotion": value.eligible_for_asset_promotion,
        "replaces_rights_manifest": value.replaces_rights_manifest,
    }


def prompt_render_receipt_document_projection(value: PromptRenderReceipt) -> dict[str, object]:
    projection = prompt_render_receipt_projection(value)
    return {**projection, "prompt_render_receipt_sha256": value.prompt_render_receipt_sha256}


def _canonical_compact_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise VisualPromptProfileError("semantic projection is not canonical JSON") from exc


def _semantic_sha256(domain: bytes, projection: object) -> str:
    return hashlib.sha256(domain + _canonical_compact_json(projection)).hexdigest()


def visual_prompt_profile_sha256(value: VisualPromptProfile) -> str:
    return _semantic_sha256(PROFILE_SHA256_DOMAIN, visual_prompt_profile_projection(value))


def prompt_profile_catalog_sha256(value: PromptProfileCatalog) -> str:
    return _semantic_sha256(CATALOG_SHA256_DOMAIN, prompt_profile_catalog_projection(value))


def prompt_render_input_sha256(value: PromptRenderInput) -> str:
    return _semantic_sha256(RENDER_INPUT_SHA256_DOMAIN, prompt_render_input_projection(value))


def prompt_render_receipt_sha256(value: PromptRenderReceipt) -> str:
    return _semantic_sha256(
        PROMPT_RENDER_RECEIPT_SHA256_DOMAIN,
        prompt_render_receipt_projection(value),
    )


def _json_object(
    value: object,
    *,
    field: str,
    keys: frozenset[str],
) -> dict[str, object]:
    if type(value) is not dict:
        _invalid(f"{field} must be an exact JSON object")
    result = cast(dict[object, object], value)
    if any(type(key) is not str for key in result):
        _invalid(f"{field} object keys must be exact strings")
    typed = cast(dict[str, object], result)
    actual = frozenset(typed)
    if actual != keys:
        missing = sorted(keys - actual)
        unknown = sorted(actual - keys)
        _invalid(f"{field} has an invalid field set; missing={missing}, unknown={unknown}")
    return typed


def _json_array(value: object, *, field: str) -> list[object]:
    if type(value) is not list:
        _invalid(f"{field} must be an exact JSON array")
    return cast(list[object], value)


def _text_tuple_from_json(
    value: object,
    *,
    field: str,
    minimum: int,
    maximum: int,
    item_maximum: int,
    sorted_values: bool = False,
) -> tuple[str, ...]:
    items = _json_array(value, field=field)
    result = tuple(
        _validate_trimmed_text(item, f"{field}[{index}]", item_maximum)
        for index, item in enumerate(items)
    )
    _validate_text_tuple(
        result,
        field=field,
        minimum=minimum,
        maximum=maximum,
        item_maximum=item_maximum,
        sorted_values=sorted_values,
    )
    return result


def _enum_tuple_from_json[EnumT: StrEnum](
    value: object,
    *,
    field: str,
    expected_type: type[EnumT],
    canonical_order: tuple[EnumT, ...],
    minimum: int,
    maximum: int,
) -> tuple[EnumT, ...]:
    items = _json_array(value, field=field)
    result = tuple(
        _enum_from_json(item, expected_type, f"{field}[{index}]")
        for index, item in enumerate(items)
    )
    _validate_enum_subset(
        result,
        field=field,
        expected_type=expected_type,
        canonical_order=canonical_order,
        minimum=minimum,
        maximum=maximum,
    )
    return result


def _prompt_constraint_set_from_json(value: object) -> PromptConstraintSet:
    source = _json_object(
        value,
        field="constraint_set",
        keys=frozenset(
            {
                "negative_prompt_constraints",
                "positive_prompt_constraints",
                "qc_expectations",
            }
        ),
    )
    return PromptConstraintSet(
        negative_prompt_constraints=_text_tuple_from_json(
            source["negative_prompt_constraints"],
            field="negative_prompt_constraints",
            minimum=1,
            maximum=32,
            item_maximum=1000,
        ),
        positive_prompt_constraints=_text_tuple_from_json(
            source["positive_prompt_constraints"],
            field="positive_prompt_constraints",
            minimum=1,
            maximum=32,
            item_maximum=1000,
        ),
        qc_expectations=_text_tuple_from_json(
            source["qc_expectations"],
            field="qc_expectations",
            minimum=1,
            maximum=32,
            item_maximum=1000,
        ),
    )


def _character_recipe_from_json(value: object) -> CharacterReferenceAssetRecipe:
    keys = frozenset(
        {
            "background_requirements",
            "body_proportion_anchors",
            "expression_range",
            "face_identity_anchors",
            "forbidden_body_proportion_drift",
            "forbidden_hairstyle_drift",
            "forbidden_identity_drift",
            "forbidden_wardrobe_drift",
            "hairstyle_anchors",
            "recipe_kind",
            "reference_asset_types",
            "required_primary_binding_fields",
            "sheet_layout_requirements",
            "wardrobe_anchors",
        }
    )
    source = _json_object(value, field="character reference recipe", keys=keys)

    def guidance(name: str) -> tuple[str, ...]:
        return _text_tuple_from_json(
            source[name],
            field=name,
            minimum=1,
            maximum=16,
            item_maximum=1000,
        )

    required_fields = _json_array(
        source["required_primary_binding_fields"],
        field="required_primary_binding_fields",
    )
    return CharacterReferenceAssetRecipe(
        background_requirements=guidance("background_requirements"),
        body_proportion_anchors=guidance("body_proportion_anchors"),
        expression_range=guidance("expression_range"),
        face_identity_anchors=guidance("face_identity_anchors"),
        forbidden_body_proportion_drift=guidance("forbidden_body_proportion_drift"),
        forbidden_hairstyle_drift=guidance("forbidden_hairstyle_drift"),
        forbidden_identity_drift=guidance("forbidden_identity_drift"),
        forbidden_wardrobe_drift=guidance("forbidden_wardrobe_drift"),
        hairstyle_anchors=guidance("hairstyle_anchors"),
        recipe_kind=_enum_from_json(
            source["recipe_kind"],
            ReferenceAssetRecipeKind,
            "recipe_kind",
        ),
        reference_asset_types=_enum_tuple_from_json(
            source["reference_asset_types"],
            field="character recipe reference_asset_types",
            expected_type=ReferenceAssetType,
            canonical_order=_CHARACTER_REFERENCE_ASSET_TYPES,
            minimum=1,
            maximum=3,
        ),
        required_primary_binding_fields=tuple(
            _validate_canonical_text(item, f"required_primary_binding_fields[{index}]")
            for index, item in enumerate(required_fields)
        ),
        sheet_layout_requirements=guidance("sheet_layout_requirements"),
        wardrobe_anchors=guidance("wardrobe_anchors"),
    )


def _scene_recipe_from_json(value: object) -> SceneReferenceAssetRecipe:
    keys = frozenset(
        {
            "continuity_requirements",
            "forbidden_drift",
            "geography_anchors",
            "layout_requirements",
            "lighting_anchors",
            "material_anchors",
            "palette_anchors",
            "prop_placement_anchors",
            "recipe_kind",
            "reference_asset_types",
            "required_primary_binding_fields",
        }
    )
    source = _json_object(value, field="scene reference recipe", keys=keys)

    def guidance(name: str) -> tuple[str, ...]:
        return _text_tuple_from_json(
            source[name],
            field=name,
            minimum=1,
            maximum=16,
            item_maximum=1000,
        )

    required_fields = _json_array(
        source["required_primary_binding_fields"],
        field="required_primary_binding_fields",
    )
    return SceneReferenceAssetRecipe(
        continuity_requirements=guidance("continuity_requirements"),
        forbidden_drift=guidance("forbidden_drift"),
        geography_anchors=guidance("geography_anchors"),
        layout_requirements=guidance("layout_requirements"),
        lighting_anchors=guidance("lighting_anchors"),
        material_anchors=guidance("material_anchors"),
        palette_anchors=guidance("palette_anchors"),
        prop_placement_anchors=guidance("prop_placement_anchors"),
        recipe_kind=_enum_from_json(
            source["recipe_kind"],
            ReferenceAssetRecipeKind,
            "recipe_kind",
        ),
        reference_asset_types=_enum_tuple_from_json(
            source["reference_asset_types"],
            field="scene recipe reference_asset_types",
            expected_type=ReferenceAssetType,
            canonical_order=_SCENE_REFERENCE_ASSET_TYPES,
            minimum=1,
            maximum=4,
        ),
        required_primary_binding_fields=tuple(
            _validate_canonical_text(item, f"required_primary_binding_fields[{index}]")
            for index, item in enumerate(required_fields)
        ),
    )


def _reference_recipe_from_json(value: object) -> ReferenceAssetRecipe | None:
    if value is None:
        return None
    if type(value) is not dict:
        _invalid("reference_asset_recipe must be null or an exact JSON object")
    candidate = cast(dict[object, object], value)
    recipe_kind = candidate.get("recipe_kind")
    if recipe_kind == ReferenceAssetRecipeKind.CHARACTER_REFERENCE.value:
        return _character_recipe_from_json(value)
    if recipe_kind == ReferenceAssetRecipeKind.SCENE_REFERENCE.value:
        return _scene_recipe_from_json(value)
    _invalid("reference_asset_recipe has an unknown recipe_kind")


def _prompt_section_from_json(value: object) -> PromptSection:
    source = _json_object(
        value,
        field="section",
        keys=frozenset({"heading", "placeholder", "section_id"}),
    )
    return PromptSection(
        heading=_validate_trimmed_text(source["heading"], "heading", 80),
        placeholder=_enum_from_json(source["placeholder"], PlaceholderId, "placeholder"),
        section_id=_validate_portable_id(source["section_id"], "section_id"),
    )


def _visual_prompt_profile_from_json(value: object) -> VisualPromptProfile:
    source = _json_object(
        value,
        field="profile",
        keys=frozenset(
            {
                "asset_purpose",
                "constraint_set",
                "narrative_contexts",
                "profile_id",
                "profile_version",
                "reference_asset_recipe",
                "reference_asset_types",
                "renderer_version",
                "sections",
                "shot_type",
                "visual_style_id",
            }
        ),
    )
    sections = _json_array(source["sections"], field="sections")
    return VisualPromptProfile(
        asset_purpose=_enum_from_json(source["asset_purpose"], AssetPurpose, "asset_purpose"),
        constraint_set=_prompt_constraint_set_from_json(source["constraint_set"]),
        narrative_contexts=_enum_tuple_from_json(
            source["narrative_contexts"],
            field="narrative_contexts",
            expected_type=NarrativeContext,
            canonical_order=_NARRATIVE_CONTEXT_ORDER,
            minimum=1,
            maximum=5,
        ),
        profile_id=_validate_portable_id(source["profile_id"], "profile_id"),
        profile_version=_validate_semantic_version(
            source["profile_version"],
            "profile_version",
        ),
        reference_asset_recipe=_reference_recipe_from_json(source["reference_asset_recipe"]),
        reference_asset_types=_enum_tuple_from_json(
            source["reference_asset_types"],
            field="reference_asset_types",
            expected_type=ReferenceAssetType,
            canonical_order=_REFERENCE_ASSET_TYPE_ORDER,
            minimum=0,
            maximum=7,
        ),
        renderer_version=_validate_semantic_version(
            source["renderer_version"],
            "renderer_version",
        ),
        sections=tuple(_prompt_section_from_json(item) for item in sections),
        shot_type=_enum_from_json(source["shot_type"], ShotType, "shot_type"),
        visual_style_id=_enum_from_json(
            source["visual_style_id"],
            VisualStyleId,
            "visual_style_id",
        ),
    )


def _provider_observation_from_json(
    value: object,
) -> ProviderSyntaxCompatibilityObservation:
    source = _json_object(
        value,
        field="provider compatibility observation",
        keys=frozenset(
            {
                "compatibility_status",
                "provider_id",
                "provider_profile_id",
                "provider_profile_version",
            }
        ),
    )
    return ProviderSyntaxCompatibilityObservation(
        compatibility_status=_enum_from_json(
            source["compatibility_status"],
            ProviderSyntaxCompatibilityStatus,
            "compatibility_status",
        ),
        provider_id=_validate_provider_id(source["provider_id"], "provider_id"),
        provider_profile_id=_validate_portable_id(
            source["provider_profile_id"],
            "provider_profile_id",
        ),
        provider_profile_version=_validate_portable_id(
            source["provider_profile_version"],
            "provider_profile_version",
        ),
    )


def _catalog_entry_from_json(value: object) -> PromptProfileCatalogEntry:
    source = _json_object(
        value,
        field="catalog source entry",
        keys=frozenset(
            {
                "description",
                "display_name",
                "eligible_for_asset_promotion",
                "grants_execution_authority",
                "grants_qualification",
                "grants_rights",
                "offline_render_admission_status",
                "profile",
                "profile_text_provenance_status",
                "provider_syntax_compatibility_observations",
            }
        ),
    )
    observations = _json_array(
        source["provider_syntax_compatibility_observations"],
        field="provider_syntax_compatibility_observations",
    )
    return PromptProfileCatalogEntry(
        description=_validate_trimmed_text(source["description"], "description", 1000),
        display_name=_validate_trimmed_text(source["display_name"], "display_name", 128),
        eligible_for_asset_promotion=cast(bool, source["eligible_for_asset_promotion"]),
        grants_execution_authority=cast(bool, source["grants_execution_authority"]),
        grants_qualification=cast(bool, source["grants_qualification"]),
        grants_rights=cast(bool, source["grants_rights"]),
        offline_render_admission_status=_enum_from_json(
            source["offline_render_admission_status"],
            OfflineRenderAdmissionStatus,
            "offline_render_admission_status",
        ),
        profile=_visual_prompt_profile_from_json(source["profile"]),
        profile_text_provenance_status=_enum_from_json(
            source["profile_text_provenance_status"],
            ProfileTextProvenanceStatus,
            "profile_text_provenance_status",
        ),
        provider_syntax_compatibility_observations=tuple(
            _provider_observation_from_json(item) for item in observations
        ),
    )


def _build_catalog_from_validated_source(value: object) -> PromptProfileCatalog:
    """Build the deep-frozen catalog from one already decoded strict source JSON value.

    Raw-byte, duplicate-key, nesting-depth, and persistent-canonical-document admission belongs to
    :mod:`sdc.visual_prompt_profile_source`.  This boundary independently rechecks the complete
    primitive shape and every semantic and cross-field constraint.
    """

    source = _json_object(
        value,
        field="visual Prompt profile source",
        keys=frozenset(
            {
                "automated_execution_allowed",
                "authorized_attempts",
                "authorized_cost_cny",
                "catalog_reviewer_ref",
                "catalog_reviewed_at",
                "catalog_version",
                "current_gate",
                "execution_authorized",
                "generation_authorized",
                "posts_allowed",
                "profiles",
                "provider_requests",
                "provider_state",
                "publication_allowed",
                "publication_authorized",
                "remote_processing_allowed",
                "renderer_id",
                "renderer_version",
                "retention_allowed",
                "source_revision",
                "training_allowed",
                "usage_restriction",
            }
        ),
    )
    profiles = _json_array(source["profiles"], field="profiles")
    return PromptProfileCatalog(
        automated_execution_allowed=cast(bool, source["automated_execution_allowed"]),
        authorized_attempts=cast(int, source["authorized_attempts"]),
        authorized_cost_cny=cast(int, source["authorized_cost_cny"]),
        catalog_reviewer_ref=_validate_portable_id(
            source["catalog_reviewer_ref"],
            "catalog_reviewer_ref",
        ),
        catalog_reviewed_at=_validate_utc_second(
            source["catalog_reviewed_at"],
            "catalog_reviewed_at",
        ),
        catalog_version=_validate_semantic_version(
            source["catalog_version"],
            "catalog_version",
        ),
        current_gate=cast(str, source["current_gate"]),
        execution_authorized=cast(bool, source["execution_authorized"]),
        generation_authorized=cast(bool, source["generation_authorized"]),
        posts_allowed=cast(int, source["posts_allowed"]),
        profiles=tuple(_catalog_entry_from_json(item) for item in profiles),
        provider_requests=cast(int, source["provider_requests"]),
        provider_state=cast(str, source["provider_state"]),
        publication_allowed=cast(bool, source["publication_allowed"]),
        publication_authorized=cast(bool, source["publication_authorized"]),
        remote_processing_allowed=cast(bool, source["remote_processing_allowed"]),
        renderer_id=cast(str, source["renderer_id"]),
        renderer_version=_validate_semantic_version(
            source["renderer_version"],
            "renderer_version",
        ),
        retention_allowed=cast(bool, source["retention_allowed"]),
        source_revision=_validate_portable_id(source["source_revision"], "source_revision"),
        training_allowed=cast(bool, source["training_allowed"]),
        usage_restriction=cast(str, source["usage_restriction"]),
    )


def _build_catalog_from_generated_value(value: object) -> PromptProfileCatalog:
    """Admit one static generated catalog with independently verified authored digests.

    The generated module calls this function with a literal complete source root plus one sibling
    ``profile_sha256`` per entry and one root ``catalog_sha256``.  This function never reads the
    authoritative source file and never trusts or repairs an authored digest.
    """

    generated = _json_object(
        value,
        field="generated visual Prompt catalog",
        keys=frozenset(
            {
                "automated_execution_allowed",
                "authorized_attempts",
                "authorized_cost_cny",
                "catalog_reviewer_ref",
                "catalog_reviewed_at",
                "catalog_sha256",
                "catalog_version",
                "current_gate",
                "execution_authorized",
                "generation_authorized",
                "posts_allowed",
                "profiles",
                "provider_requests",
                "provider_state",
                "publication_allowed",
                "publication_authorized",
                "remote_processing_allowed",
                "renderer_id",
                "renderer_version",
                "retention_allowed",
                "source_revision",
                "training_allowed",
                "usage_restriction",
            }
        ),
    )
    expected_catalog_sha256 = _validate_lower_sha256(
        generated["catalog_sha256"],
        "generated catalog_sha256",
    )
    generated_entries = _json_array(generated["profiles"], field="generated profiles")
    source_entries: list[object] = []
    expected_profile_sha256_values: list[str] = []
    generated_entry_keys = frozenset(
        {
            "description",
            "display_name",
            "eligible_for_asset_promotion",
            "grants_execution_authority",
            "grants_qualification",
            "grants_rights",
            "offline_render_admission_status",
            "profile",
            "profile_sha256",
            "profile_text_provenance_status",
            "provider_syntax_compatibility_observations",
        }
    )
    for index, raw_entry in enumerate(generated_entries):
        entry = _json_object(
            raw_entry,
            field=f"generated profiles[{index}]",
            keys=generated_entry_keys,
        )
        expected_profile_sha256_values.append(
            _validate_lower_sha256(
                entry["profile_sha256"],
                f"generated profiles[{index}].profile_sha256",
            )
        )
        source_entries.append(
            {
                "description": entry["description"],
                "display_name": entry["display_name"],
                "eligible_for_asset_promotion": entry["eligible_for_asset_promotion"],
                "grants_execution_authority": entry["grants_execution_authority"],
                "grants_qualification": entry["grants_qualification"],
                "grants_rights": entry["grants_rights"],
                "offline_render_admission_status": entry["offline_render_admission_status"],
                "profile": entry["profile"],
                "profile_text_provenance_status": entry["profile_text_provenance_status"],
                "provider_syntax_compatibility_observations": entry[
                    "provider_syntax_compatibility_observations"
                ],
            }
        )
    source_value: dict[str, object] = {
        "automated_execution_allowed": generated["automated_execution_allowed"],
        "authorized_attempts": generated["authorized_attempts"],
        "authorized_cost_cny": generated["authorized_cost_cny"],
        "catalog_reviewer_ref": generated["catalog_reviewer_ref"],
        "catalog_reviewed_at": generated["catalog_reviewed_at"],
        "catalog_version": generated["catalog_version"],
        "current_gate": generated["current_gate"],
        "execution_authorized": generated["execution_authorized"],
        "generation_authorized": generated["generation_authorized"],
        "posts_allowed": generated["posts_allowed"],
        "profiles": source_entries,
        "provider_requests": generated["provider_requests"],
        "provider_state": generated["provider_state"],
        "publication_allowed": generated["publication_allowed"],
        "publication_authorized": generated["publication_authorized"],
        "remote_processing_allowed": generated["remote_processing_allowed"],
        "renderer_id": generated["renderer_id"],
        "renderer_version": generated["renderer_version"],
        "retention_allowed": generated["retention_allowed"],
        "source_revision": generated["source_revision"],
        "training_allowed": generated["training_allowed"],
        "usage_restriction": generated["usage_restriction"],
    }
    catalog = _build_catalog_from_validated_source(source_value)
    for index, (catalog_entry, expected_profile_sha256) in enumerate(
        zip(catalog.profiles, expected_profile_sha256_values, strict=True)
    ):
        if catalog_entry.profile_sha256 != expected_profile_sha256:
            _invalid(f"generated profiles[{index}].profile_sha256 does not bind its profile")
    if catalog.catalog_sha256 != expected_catalog_sha256:
        _invalid("generated catalog_sha256 does not bind the exact catalog projection")
    return catalog


def _character_binding_from_json(value: object) -> CharacterAssetPromptBinding:
    source = _json_object(
        value,
        field="character asset binding",
        keys=frozenset({"asset_content_sha256", "asset_version_id", "character_id"}),
    )
    return CharacterAssetPromptBinding(
        asset_content_sha256=_validate_lower_sha256(
            source["asset_content_sha256"],
            "asset_content_sha256",
        ),
        asset_version_id=_validate_portable_id(
            source["asset_version_id"],
            "asset_version_id",
        ),
        character_id=_validate_portable_id(source["character_id"], "character_id"),
    )


def _scene_binding_from_json(value: object) -> SceneAssetPromptBinding:
    source = _json_object(
        value,
        field="scene asset binding",
        keys=frozenset({"asset_content_sha256", "asset_version_id", "scene_id"}),
    )
    return SceneAssetPromptBinding(
        asset_content_sha256=_validate_lower_sha256(
            source["asset_content_sha256"],
            "asset_content_sha256",
        ),
        asset_version_id=_validate_portable_id(
            source["asset_version_id"],
            "asset_version_id",
        ),
        scene_id=_validate_portable_id(source["scene_id"], "scene_id"),
    )


def _dialogue_line_from_json(value: object) -> DialoguePromptLine:
    source = _json_object(
        value,
        field="dialogue line",
        keys=frozenset({"character_id", "line_id", "ordinal", "text"}),
    )
    return DialoguePromptLine(
        character_id=_validate_portable_id(source["character_id"], "character_id"),
        line_id=_validate_portable_id(source["line_id"], "line_id"),
        ordinal=_validate_non_negative_int(source["ordinal"], "ordinal"),
        text=_validate_trimmed_text(source["text"], "dialogue text", 2000),
    )


def _character_text_map_from_json(value: object, *, field: str) -> CharacterTextMap:
    if type(value) is not dict:
        _invalid(f"{field} must be an exact JSON object")
    source = cast(dict[object, object], value)
    result: list[tuple[str, str]] = []
    for index, (raw_key, raw_value) in enumerate(source.items()):
        key = _validate_portable_id(raw_key, f"{field} key {index}")
        text = _validate_trimmed_text(raw_value, f"{field}[{key}]", 512)
        result.append((key, text))
    return tuple(sorted(result, key=lambda item: item[0]))


def _character_bindings_from_json(value: object) -> tuple[CharacterAssetPromptBinding, ...]:
    return tuple(
        _character_binding_from_json(item)
        for item in _json_array(value, field="character_asset_bindings")
    )


def _build_prompt_render_input_from_validated_value(value: object) -> PromptRenderInput:
    """Build one deep-frozen tagged render input from a strict decoded JSON object."""

    if type(value) is not dict:
        _invalid("render_input must be an exact JSON object")
    candidate = cast(dict[object, object], value)
    raw_kind = candidate.get("input_kind")
    kind = _enum_from_json(raw_kind, AssetPurpose, "input_kind")
    if kind is AssetPurpose.NARRATIVE_SHOT:
        source = _json_object(
            value,
            field="narrative render_input",
            keys=frozenset(
                {
                    "action",
                    "camera_angle",
                    "camera_movement",
                    "character_asset_bindings",
                    "continuity_notes",
                    "dialogue",
                    "emotion_by_character",
                    "input_kind",
                    "narrative",
                    "props",
                    "scene_asset_binding",
                    "shot_size",
                    "visual_direction",
                    "wardrobe_by_character",
                }
            ),
        )
        return NarrativeShotPromptRenderInput(
            action=_validate_trimmed_text(source["action"], "action", 2000),
            camera_angle=_enum_from_json(
                source["camera_angle"],
                CameraAngleV1,
                "camera_angle",
            ),
            camera_movement=_enum_from_json(
                source["camera_movement"],
                CameraMovementV1,
                "camera_movement",
            ),
            character_asset_bindings=_character_bindings_from_json(
                source["character_asset_bindings"]
            ),
            continuity_notes=_validate_trimmed_text(
                source["continuity_notes"],
                "continuity_notes",
                2000,
            ),
            dialogue=tuple(
                _dialogue_line_from_json(item)
                for item in _json_array(source["dialogue"], field="dialogue")
            ),
            emotion_by_character=_character_text_map_from_json(
                source["emotion_by_character"],
                field="emotion_by_character",
            ),
            input_kind=kind,
            narrative=_validate_trimmed_text(source["narrative"], "narrative", 4000),
            props=_text_tuple_from_json(
                source["props"],
                field="props",
                minimum=0,
                maximum=16,
                item_maximum=128,
                sorted_values=True,
            ),
            scene_asset_binding=_scene_binding_from_json(source["scene_asset_binding"]),
            shot_size=_enum_from_json(source["shot_size"], ShotSizeV1, "shot_size"),
            visual_direction=_validate_trimmed_text(
                source["visual_direction"],
                "visual_direction",
                4000,
            ),
            wardrobe_by_character=_character_text_map_from_json(
                source["wardrobe_by_character"],
                field="wardrobe_by_character",
            ),
        )
    if kind is AssetPurpose.CHARACTER_REFERENCE_ASSET:
        source = _json_object(
            value,
            field="character reference render_input",
            keys=frozenset(
                {
                    "action",
                    "character_asset_bindings",
                    "continuity_notes",
                    "emotion_by_character",
                    "input_kind",
                    "narrative",
                    "visual_direction",
                    "wardrobe_by_character",
                }
            ),
        )
        return CharacterReferencePromptRenderInput(
            action=_validate_trimmed_text(source["action"], "action", 2000),
            character_asset_bindings=_character_bindings_from_json(
                source["character_asset_bindings"]
            ),
            continuity_notes=_validate_trimmed_text(
                source["continuity_notes"],
                "continuity_notes",
                2000,
            ),
            emotion_by_character=_character_text_map_from_json(
                source["emotion_by_character"],
                field="emotion_by_character",
            ),
            input_kind=kind,
            narrative=_validate_trimmed_text(source["narrative"], "narrative", 4000),
            visual_direction=_validate_trimmed_text(
                source["visual_direction"],
                "visual_direction",
                4000,
            ),
            wardrobe_by_character=_character_text_map_from_json(
                source["wardrobe_by_character"],
                field="wardrobe_by_character",
            ),
        )
    source = _json_object(
        value,
        field="scene reference render_input",
        keys=frozenset(
            {
                "action",
                "continuity_notes",
                "input_kind",
                "narrative",
                "props",
                "scene_asset_binding",
                "visual_direction",
            }
        ),
    )
    return SceneReferencePromptRenderInput(
        action=_validate_trimmed_text(source["action"], "action", 2000),
        continuity_notes=_validate_trimmed_text(
            source["continuity_notes"],
            "continuity_notes",
            2000,
        ),
        input_kind=kind,
        narrative=_validate_trimmed_text(source["narrative"], "narrative", 4000),
        props=_text_tuple_from_json(
            source["props"],
            field="props",
            minimum=0,
            maximum=16,
            item_maximum=128,
            sorted_values=True,
        ),
        scene_asset_binding=_scene_binding_from_json(source["scene_asset_binding"]),
        visual_direction=_validate_trimmed_text(
            source["visual_direction"],
            "visual_direction",
            4000,
        ),
    )


def resolve_visual_prompt_profile(
    catalog: PromptProfileCatalog,
    *,
    catalog_version: str,
    catalog_sha256: str,
    profile_id: str,
    profile_version: str,
    profile_sha256: str,
) -> VisualPromptProfileSnapshot:
    """Resolve one admitted profile by the exact five-value identity only."""

    _require_exact_type(catalog, PromptProfileCatalog, "catalog")
    _validate_semantic_version(catalog_version, "catalog_version")
    _validate_lower_sha256(catalog_sha256, "catalog_sha256")
    _validate_portable_id(profile_id, "profile_id")
    _validate_semantic_version(profile_version, "profile_version")
    _validate_lower_sha256(profile_sha256, "profile_sha256")
    if catalog.catalog_version != catalog_version:
        _invalid("catalog_version does not match the supplied catalog")
    actual_catalog_sha256 = prompt_profile_catalog_sha256(catalog)
    if actual_catalog_sha256 != catalog_sha256:
        _invalid("catalog_sha256 does not match the supplied catalog")
    matches = tuple(
        entry
        for entry in catalog.profiles
        if entry.profile.profile_id == profile_id
        and entry.profile.profile_version == profile_version
    )
    if len(matches) != 1:
        _invalid("the exact profile identity must resolve to exactly one catalog entry")
    entry = matches[0]
    actual_profile_sha256 = visual_prompt_profile_sha256(entry.profile)
    if actual_profile_sha256 != profile_sha256:
        _invalid("profile_sha256 does not match the resolved profile")
    if (
        entry.offline_render_admission_status
        is not OfflineRenderAdmissionStatus.HUMAN_REVIEWED_FOR_OFFLINE_RENDER
        or entry.profile_text_provenance_status
        is not ProfileTextProvenanceStatus.FIRST_PARTY_TEXT_REVIEWED
    ):
        _invalid("the exact status/provenance pair does not admit offline rendering")
    return _make_resolved_visual_prompt_profile_snapshot(
        profile=entry.profile,
        profile_sha256=actual_profile_sha256,
        catalog_version=catalog.catalog_version,
        catalog_sha256=actual_catalog_sha256,
    )


def _render_recipe_lines(recipe: ReferenceAssetRecipe) -> tuple[str, ...]:
    if type(recipe) is CharacterReferenceAssetRecipe:
        character = recipe
        values: tuple[tuple[str, object], ...] = (
            ("Recipe kind", character.recipe_kind.value),
            (
                "Reference asset types",
                [item.value for item in character.reference_asset_types],
            ),
            ("Face identity anchors", list(character.face_identity_anchors)),
            ("Hairstyle anchors", list(character.hairstyle_anchors)),
            ("Wardrobe anchors", list(character.wardrobe_anchors)),
            ("Body proportion anchors", list(character.body_proportion_anchors)),
            ("Expression range", list(character.expression_range)),
            ("Forbidden identity drift", list(character.forbidden_identity_drift)),
            ("Forbidden hairstyle drift", list(character.forbidden_hairstyle_drift)),
            ("Forbidden wardrobe drift", list(character.forbidden_wardrobe_drift)),
            (
                "Forbidden body proportion drift",
                list(character.forbidden_body_proportion_drift),
            ),
            ("Sheet layout requirements", list(character.sheet_layout_requirements)),
            ("Background requirements", list(character.background_requirements)),
            (
                "Required primary binding fields",
                list(character.required_primary_binding_fields),
            ),
        )
    elif type(recipe) is SceneReferenceAssetRecipe:
        scene = recipe
        values = (
            ("Recipe kind", scene.recipe_kind.value),
            ("Reference asset types", [item.value for item in scene.reference_asset_types]),
            ("Layout requirements", list(scene.layout_requirements)),
            ("Geography anchors", list(scene.geography_anchors)),
            ("Lighting anchors", list(scene.lighting_anchors)),
            ("Palette anchors", list(scene.palette_anchors)),
            ("Material anchors", list(scene.material_anchors)),
            ("Prop placement anchors", list(scene.prop_placement_anchors)),
            ("Continuity requirements", list(scene.continuity_requirements)),
            ("Forbidden drift", list(scene.forbidden_drift)),
            (
                "Required primary binding fields",
                list(scene.required_primary_binding_fields),
            ),
        )
    else:
        _invalid("reference recipe must use one exact tagged-union member")
    return tuple(
        f"{label}: {raw if type(raw) is str else _canonical_compact_json(raw).decode('utf-8')}"
        for label, raw in values
    )


def _prompt_render_receipt_payload(
    *,
    snapshot: VisualPromptProfileSnapshot,
    render_input_sha256: str,
    prompt_sha256: str,
    prompt_size_bytes: int,
) -> dict[str, object]:
    return {
        "receipt_purpose": PROMPT_RENDER_RECEIPT_PURPOSE,
        "profile_id": snapshot.profile.profile_id,
        "profile_version": snapshot.profile.profile_version,
        "profile_sha256": snapshot.profile_sha256,
        "catalog_version": snapshot.catalog_version,
        "catalog_sha256": snapshot.catalog_sha256,
        "render_input_sha256": render_input_sha256,
        "renderer_id": VISUAL_PROMPT_RENDERER_ID,
        "renderer_version": VISUAL_PROMPT_RENDERER_VERSION,
        "prompt_sha256": prompt_sha256,
        "prompt_size_bytes": prompt_size_bytes,
        "current_gate": CURRENT_GATE,
        "provider_state": PROVIDER_STATE,
        "generation_authorized": False,
        "execution_authorized": False,
        "publication_authorized": False,
        "remote_processing_allowed": False,
        "retention_allowed": False,
        "training_allowed": False,
        "publication_allowed": False,
        "automated_execution_allowed": False,
        "authorized_attempts": 0,
        "authorized_cost_cny": 0,
        "posts_allowed": 0,
        "provider_requests": 0,
        "usage_restriction": USAGE_RESTRICTION,
        "grants_rights": False,
        "grants_qualification": False,
        "grants_execution_authority": False,
        "eligible_for_asset_promotion": False,
        "replaces_rights_manifest": False,
    }


def _make_prompt_render_receipt(
    *,
    snapshot: VisualPromptProfileSnapshot,
    render_input_sha256: str,
    prompt_sha256: str,
    prompt_size_bytes: int,
) -> PromptRenderReceipt:
    payload = _prompt_render_receipt_payload(
        snapshot=snapshot,
        render_input_sha256=render_input_sha256,
        prompt_sha256=prompt_sha256,
        prompt_size_bytes=prompt_size_bytes,
    )
    digest = _semantic_sha256(PROMPT_RENDER_RECEIPT_SHA256_DOMAIN, payload)
    return PromptRenderReceipt(
        receipt_purpose=PROMPT_RENDER_RECEIPT_PURPOSE,
        profile_id=snapshot.profile.profile_id,
        profile_version=snapshot.profile.profile_version,
        profile_sha256=snapshot.profile_sha256,
        catalog_version=snapshot.catalog_version,
        catalog_sha256=snapshot.catalog_sha256,
        render_input_sha256=render_input_sha256,
        renderer_id=VISUAL_PROMPT_RENDERER_ID,
        renderer_version=VISUAL_PROMPT_RENDERER_VERSION,
        prompt_sha256=prompt_sha256,
        prompt_size_bytes=prompt_size_bytes,
        current_gate=CURRENT_GATE,
        provider_state=PROVIDER_STATE,
        generation_authorized=False,
        execution_authorized=False,
        publication_authorized=False,
        remote_processing_allowed=False,
        retention_allowed=False,
        training_allowed=False,
        publication_allowed=False,
        automated_execution_allowed=False,
        authorized_attempts=0,
        authorized_cost_cny=0,
        posts_allowed=0,
        provider_requests=0,
        usage_restriction=USAGE_RESTRICTION,
        grants_rights=False,
        grants_qualification=False,
        grants_execution_authority=False,
        eligible_for_asset_promotion=False,
        replaces_rights_manifest=False,
        prompt_render_receipt_sha256=digest,
    )


def render_visual_prompt(
    render_input: PromptRenderInput,
    snapshot: VisualPromptProfileSnapshot,
) -> tuple[bytes, PromptRenderReceipt]:
    """Purely render exact Prompt bytes and their zero-authority process Receipt."""

    if type(render_input) not in {
        NarrativeShotPromptRenderInput,
        CharacterReferencePromptRenderInput,
        SceneReferencePromptRenderInput,
    }:
        _invalid("render_input must use one exact tagged-union member")
    _require_exact_type(snapshot, VisualPromptProfileSnapshot, "snapshot")
    if render_input.input_kind is not snapshot.profile.asset_purpose:
        _invalid("render_input input_kind must equal the Snapshot asset_purpose")
    if snapshot.profile.renderer_version != VISUAL_PROMPT_RENDERER_VERSION:
        _invalid("Snapshot renderer_version is not supported by this renderer")

    input_projection = prompt_render_input_projection(render_input)
    lines: list[str] = []
    for section in snapshot.profile.sections:
        rendered_value = input_projection[section.placeholder.value]
        if type(rendered_value) is str:
            text = rendered_value
        else:
            text = _canonical_compact_json(rendered_value).decode("utf-8")
        lines.append(f"{section.heading}: {text}")
    lines.append("Positive Prompt Constraints:")
    lines.extend(
        f"- {item}" for item in snapshot.profile.constraint_set.positive_prompt_constraints
    )
    lines.append("Negative Prompt Constraints:")
    lines.extend(
        f"- {item}" for item in snapshot.profile.constraint_set.negative_prompt_constraints
    )
    if snapshot.profile.reference_asset_recipe is not None:
        lines.append("Reference Asset Recipe:")
        lines.extend(_render_recipe_lines(snapshot.profile.reference_asset_recipe))
    prompt_text = "\n".join(lines) + "\n"
    if unicodedata.normalize("NFC", prompt_text) != prompt_text:
        _invalid("rendered Prompt is not NFC")
    if "\r" in prompt_text or prompt_text.startswith("\ufeff"):
        _invalid("rendered Prompt violates the LF/no-BOM grammar")
    if any(line.endswith((" ", "\t")) for line in prompt_text[:-1].split("\n")):
        _invalid("rendered Prompt contains trailing horizontal whitespace")
    prompt_bytes = prompt_text.encode("utf-8")
    if not 1 <= len(prompt_bytes) <= MAX_PROMPT_BYTES:
        _invalid("rendered Prompt exceeds the frozen 1..65536 byte limit")
    input_digest = prompt_render_input_sha256(render_input)
    prompt_digest = hashlib.sha256(prompt_bytes).hexdigest()
    receipt = _make_prompt_render_receipt(
        snapshot=snapshot,
        render_input_sha256=input_digest,
        prompt_sha256=prompt_digest,
        prompt_size_bytes=len(prompt_bytes),
    )
    return prompt_bytes, receipt


__all__ = [
    "AssetPurpose",
    "CameraAngleV1",
    "CameraMovementV1",
    "CharacterAssetPromptBinding",
    "CharacterReferenceAssetRecipe",
    "CharacterReferencePromptRenderInput",
    "DialoguePromptLine",
    "NarrativeContext",
    "NarrativeShotPromptRenderInput",
    "OfflineRenderAdmissionStatus",
    "PlaceholderId",
    "ProfileTextProvenanceStatus",
    "PromptConstraintSet",
    "PromptProfileCatalog",
    "PromptProfileCatalogEntry",
    "PromptRenderInput",
    "PromptRenderReceipt",
    "PromptSection",
    "ProviderSyntaxCompatibilityObservation",
    "ProviderSyntaxCompatibilityStatus",
    "ReferenceAssetRecipe",
    "ReferenceAssetRecipeKind",
    "ReferenceAssetType",
    "SceneAssetPromptBinding",
    "SceneReferenceAssetRecipe",
    "SceneReferencePromptRenderInput",
    "ShotSizeV1",
    "ShotType",
    "VisualPromptProfile",
    "VisualPromptProfileError",
    "VisualPromptProfileSnapshot",
    "VisualStyleId",
    "character_asset_prompt_binding_projection",
    "character_reference_asset_recipe_projection",
    "dialogue_prompt_line_projection",
    "prompt_constraint_set_projection",
    "prompt_profile_catalog_entry_projection",
    "prompt_profile_catalog_projection",
    "prompt_profile_catalog_sha256",
    "prompt_render_input_projection",
    "prompt_render_input_sha256",
    "prompt_render_receipt_document_projection",
    "prompt_render_receipt_projection",
    "prompt_render_receipt_sha256",
    "prompt_section_projection",
    "provider_syntax_compatibility_observation_projection",
    "render_visual_prompt",
    "resolve_visual_prompt_profile",
    "scene_asset_prompt_binding_projection",
    "scene_reference_asset_recipe_projection",
    "visual_prompt_profile_projection",
    "visual_prompt_profile_sha256",
    "visual_prompt_profile_snapshot_projection",
]
