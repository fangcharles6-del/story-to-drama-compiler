"""Offline Visual Prompt Profile sidecar compilation for Creative Sample v2.

This module is the isolated Compiler boundary accepted by SDC-ADR-041.  It calls the released
Creative Sample v2 compiler without changing any base artifact, derives deterministic narrative
render inputs from the same source specification, and returns a separate zero-authority Prompt
sidecar.  It performs no filesystem, environment, clock, randomness, network, Provider, Runtime,
QC, Candidate, persistence, publication, or asset-promotion operation.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Literal, NoReturn

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)

from sdc.compiler import compile_creative_sample
from sdc.contracts import (
    CharacterAssetBinding,
    CharacterAssetVersion,
    CreativeSampleCompilation,
    CreativeSampleShotSpec,
    CreativeSampleSpec,
    SceneAssetVersion,
    StoryboardShotV2,
)
from sdc.visual_prompt_catalog import VISUAL_PROMPT_CATALOG
from sdc.visual_prompt_profiles import (
    PROFILE_SHA256_DOMAIN,
    PROMPT_RENDER_RECEIPT_SHA256_DOMAIN,
    RENDER_INPUT_SHA256_DOMAIN,
    AssetPurpose,
    CameraAngleV1,
    CameraMovementV1,
    CharacterAssetPromptBinding,
    DialoguePromptLine,
    NarrativeContext,
    NarrativeShotPromptRenderInput,
    PlaceholderId,
    PromptRenderReceipt,
    SceneAssetPromptBinding,
    ShotSizeV1,
    ShotType,
    VisualPromptProfileError,
    VisualPromptProfileSnapshot,
    VisualStyleId,
    prompt_render_input_sha256,
    prompt_render_receipt_document_projection,
    render_visual_prompt,
    resolve_visual_prompt_profile,
    visual_prompt_profile_snapshot_projection,
)

VISUAL_PROMPT_COMPILER_SIDECAR_SHA256_DOMAIN = (
    b"sdc:visual-prompt-compiler-sidecar:v1\0"
)

_SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"
_REQUEST_PURPOSE: Literal["COMPILE_OFFLINE_NARRATIVE_VISUAL_PROMPTS"] = (
    "COMPILE_OFFLINE_NARRATIVE_VISUAL_PROMPTS"
)
_ARTIFACT_PURPOSE: Literal["OFFLINE_VISUAL_PROMPT_COMPILATION_SIDECAR"] = (
    "OFFLINE_VISUAL_PROMPT_COMPILATION_SIDECAR"
)
_BASE_COMPILER_CONTRACT: Literal["CREATIVE_SAMPLE_V2"] = "CREATIVE_SAMPLE_V2"
_SELECTION_SCOPE: Literal["ALL_NARRATIVE_SHOTS"] = "ALL_NARRATIVE_SHOTS"
_SELECTION_DECISION_KIND: Literal["HUMAN_DECISION"] = "HUMAN_DECISION"
_CURRENT_GATE: Literal["HUMAN_GATE"] = "HUMAN_GATE"
_PROVIDER_STATE: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
_USAGE_RESTRICTION: Literal["MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"] = (
    "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
)
_RENDERER_VERSION: Literal["1.0.0"] = "1.0.0"

_PORTABLE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_LOWER_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_SEMANTIC_VERSION_PATTERN = (
    r"^(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})$"
)
_BASE_COMPILATION_ID_PATTERN = r"^creative_sample_[0-9a-f]{20}$"
_SOURCE_SHOT_ID_PATTERN = r"^storyboard_shot_v2_[0-9a-f]{20}$"
_SEMANTIC_VERSION_COMPONENT_MAX = 2_147_483_647
_PORTABLE_ID = re.compile(_PORTABLE_ID_PATTERN)
_LOWER_SHA256 = re.compile(_LOWER_SHA256_PATTERN)
_SEMANTIC_VERSION = re.compile(_SEMANTIC_VERSION_PATTERN)
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
_NARRATIVE_PLACEHOLDERS = frozenset(PlaceholderId)

PortableId = Annotated[str, Field(pattern=_PORTABLE_ID_PATTERN)]
LowerSha256 = Annotated[str, Field(pattern=_LOWER_SHA256_PATTERN)]
SemanticVersion = Annotated[str, Field(pattern=_SEMANTIC_VERSION_PATTERN)]
BaseCompilationId = Annotated[str, Field(pattern=_BASE_COMPILATION_ID_PATTERN)]
SourceShotId = Annotated[str, Field(pattern=_SOURCE_SHOT_ID_PATTERN)]


class VisualPromptCompilerError(ValueError):
    """One value violates the accepted ADR-041 offline Compiler boundary."""


def _invalid(message: str) -> NoReturn:
    raise VisualPromptCompilerError(message)


def _require_exact_model_storage(value: BaseModel, *, field: str) -> None:
    active: set[int] = set()
    completed: set[int] = set()

    def visit(item: object) -> None:
        if not isinstance(item, (BaseModel, Mapping, list, tuple, set, frozenset)):
            return
        identity = id(item)
        if identity in active:
            _invalid(f"{field} instance graph must not contain a recursive cycle")
        if identity in completed:
            return
        active.add(identity)
        try:
            if isinstance(item, BaseModel):
                declared_fields = frozenset(type(item).model_fields)
                stored_fields = frozenset(item.__dict__)
                if stored_fields != declared_fields or item.__pydantic_extra__:
                    _invalid(
                        f"{field} instance storage must contain exactly its declared fields"
                    )
                for field_name in declared_fields:
                    visit(item.__dict__[field_name])
            elif isinstance(item, Mapping):
                for key, nested_value in item.items():
                    visit(key)
                    visit(nested_value)
            else:
                for nested_value in item:
                    visit(nested_value)
        finally:
            active.remove(identity)
        completed.add(identity)

    try:
        visit(value)
    except RecursionError as exc:
        raise VisualPromptCompilerError(
            f"{field} instance graph exceeded the supported recursion depth"
        ) from exc


def _validate_canonical_text(value: str, field: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        _invalid(f"{field} must contain only Unicode scalar values")
    if unicodedata.normalize("NFC", value) != value:
        _invalid(f"{field} must already use Unicode NFC")
    if any(unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"} for character in value):
        _invalid(f"{field} contains a forbidden control, surrogate, or separator")
    return value


def _validate_trimmed_text(value: str, *, field: str, maximum: int) -> str:
    text = _validate_canonical_text(value, field)
    if not text or len(text) > maximum:
        _invalid(f"{field} must contain 1..{maximum} Unicode scalar values")
    if ord(text[0]) in _TRIM_CODEPOINTS or ord(text[-1]) in _TRIM_CODEPOINTS:
        _invalid(f"{field} must use the frozen TrimmedText boundary")
    return text


def _validate_semantic_version(value: str, field: str) -> str:
    if _SEMANTIC_VERSION.fullmatch(value) is None:
        _invalid(f"{field} must be a SemanticVersion")
    if any(int(component) > _SEMANTIC_VERSION_COMPONENT_MAX for component in value.split(".")):
        _invalid(f"{field} component exceeds 2147483647")
    return value


def _validate_portable_id(value: str, field: str) -> str:
    if _PORTABLE_ID.fullmatch(value) is None:
        _invalid(f"{field} must be a PortableId")
    return value


def _validate_lower_sha256(value: str, field: str) -> str:
    if _LOWER_SHA256.fullmatch(value) is None:
        _invalid(f"{field} must be a LowerSha256")
    return value


def _validate_text_tuple(
    value: tuple[str, ...],
    *,
    field: str,
    minimum: int,
    maximum: int,
    item_maximum: int,
    sorted_values: bool = False,
) -> tuple[str, ...]:
    if not minimum <= len(value) <= maximum:
        _invalid(f"{field} must contain {minimum}..{maximum} items")
    result = tuple(
        _validate_trimmed_text(item, field=f"{field}[{index}]", maximum=item_maximum)
        for index, item in enumerate(value)
    )
    if len(set(result)) != len(result):
        _invalid(f"{field} items must be unique")
    if sorted_values and result != tuple(sorted(result)):
        _invalid(f"{field} must already use ascending Unicode code-point order")
    return result


def _json_array_to_tuple(value: object, info: ValidationInfo) -> object:
    """Admit JSON's only array representation without weakening Python strictness."""

    if info.mode == "json":
        if type(value) is not list:
            raise ValueError(f"{info.field_name} must be an exact JSON array")
        return tuple(value)
    return value


def _validate_canonical_json(value: object, field: str = "projection") -> None:
    if value is None or type(value) in {bool, int, str}:
        if type(value) is str:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                _invalid(f"{field} must contain only Unicode scalar values")
            if unicodedata.normalize("NFC", value) != value:
                _invalid(f"{field} must already use Unicode NFC")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _validate_canonical_json(item, f"{field}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _invalid(f"{field} object keys must be exact strings")
            _validate_canonical_json(key, f"{field} object key")
            _validate_canonical_json(item, f"{field}.{key}")
        return
    _invalid(f"{field} contains a value outside the canonical JSON type set")


def _canonical_compact_json(value: object) -> bytes:
    _validate_canonical_json(value)
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise VisualPromptCompilerError("semantic projection is not canonical JSON") from exc


def _semantic_sha256(domain: bytes, projection: object) -> str:
    return hashlib.sha256(domain + _canonical_compact_json(projection)).hexdigest()


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class _ZeroAuthorityModel(_StrictFrozenModel):
    current_gate: Literal["HUMAN_GATE"]
    provider_state: Literal["NOT_AUTHORIZED"]
    generation_authorized: Literal[False]
    execution_authorized: Literal[False]
    publication_authorized: Literal[False]
    remote_processing_allowed: Literal[False]
    retention_allowed: Literal[False]
    training_allowed: Literal[False]
    publication_allowed: Literal[False]
    automated_execution_allowed: Literal[False]
    authorized_attempts: Literal[0]
    authorized_cost_cny: Literal[0]
    posts_allowed: Literal[0]
    provider_requests: Literal[0]
    grants_rights: Literal[False]
    grants_qualification: Literal[False]
    grants_execution_authority: Literal[False]
    eligible_for_asset_promotion: Literal[False]
    replaces_rights_manifest: Literal[False]
    usage_restriction: Literal["MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"]

    @model_validator(mode="before")
    @classmethod
    def validate_zero_authority_scalar_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
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
            if field_name in value and type(value[field_name]) is not bool:
                raise ValueError(f"{field_name} must be an exact JSON boolean")
        for field_name in (
            "authorized_attempts",
            "authorized_cost_cny",
            "posts_allowed",
            "provider_requests",
        ):
            if field_name in value and (
                type(value[field_name]) is not int or value[field_name] != 0
            ):
                raise ValueError(f"{field_name} must be the exact JSON integer zero")
        return value


class CreativeSampleVisualPromptCompileRequestV1(_ZeroAuthorityModel):
    """Exact human-selected, zero-authority request for one offline sidecar compilation."""

    schema_version: Literal["1.0.0"]
    request_purpose: Literal["COMPILE_OFFLINE_NARRATIVE_VISUAL_PROMPTS"]
    base_compiler_contract: Literal["CREATIVE_SAMPLE_V2"]
    selection_scope: Literal["ALL_NARRATIVE_SHOTS"]
    spec_sha256: LowerSha256
    catalog_version: SemanticVersion
    catalog_sha256: LowerSha256
    profile_id: PortableId
    profile_version: SemanticVersion
    profile_sha256: LowerSha256
    selection_decision_kind: Literal["HUMAN_DECISION"]
    selection_decision_ref: PortableId

    @field_validator("catalog_version", "profile_version")
    @classmethod
    def validate_versions(cls, value: str) -> str:
        return _validate_semantic_version(value, "semantic version")


class _PromptConstraintSetV1(_StrictFrozenModel):
    negative_prompt_constraints: tuple[str, ...]
    positive_prompt_constraints: tuple[str, ...]
    qc_expectations: tuple[str, ...]

    @field_validator(
        "negative_prompt_constraints",
        "positive_prompt_constraints",
        "qc_expectations",
        mode="before",
    )
    @classmethod
    def admit_json_arrays(cls, value: object, info: ValidationInfo) -> object:
        return _json_array_to_tuple(value, info)

    @field_validator(
        "negative_prompt_constraints",
        "positive_prompt_constraints",
        "qc_expectations",
    )
    @classmethod
    def validate_constraints(cls, value: tuple[str, ...], info: object) -> tuple[str, ...]:
        field_name = getattr(info, "field_name", "constraint")
        return _validate_text_tuple(
            value,
            field=field_name,
            minimum=1,
            maximum=32,
            item_maximum=1000,
        )


class _PromptSectionV1(_StrictFrozenModel):
    heading: str
    placeholder: PlaceholderId
    section_id: PortableId

    @field_validator("heading")
    @classmethod
    def validate_heading(cls, value: str) -> str:
        heading = _validate_trimmed_text(value, field="heading", maximum=80)
        if any(character in heading for character in "{}:"):
            _invalid("heading must not contain braces or a colon")
        return heading


class _VisualPromptProfileSnapshotV1(_StrictFrozenModel):
    asset_purpose: Literal[AssetPurpose.NARRATIVE_SHOT]
    constraint_set: _PromptConstraintSetV1
    narrative_contexts: tuple[NarrativeContext, ...]
    profile_id: PortableId
    profile_version: SemanticVersion
    reference_asset_recipe: None
    reference_asset_types: tuple[()]
    renderer_version: Literal["1.0.0"]
    sections: tuple[_PromptSectionV1, ...]
    shot_type: Literal[ShotType.NARRATIVE_FRAME]
    visual_style_id: Literal[VisualStyleId.CINEMATIC_STORYBOARD_V1]
    profile_sha256: LowerSha256
    catalog_version: SemanticVersion
    catalog_sha256: LowerSha256

    @field_validator(
        "narrative_contexts",
        "reference_asset_types",
        "sections",
        mode="before",
    )
    @classmethod
    def admit_json_arrays(cls, value: object, info: ValidationInfo) -> object:
        return _json_array_to_tuple(value, info)

    @field_validator("profile_version", "catalog_version")
    @classmethod
    def validate_versions(cls, value: str) -> str:
        return _validate_semantic_version(value, "snapshot semantic version")

    @model_validator(mode="after")
    def validate_snapshot(self) -> _VisualPromptProfileSnapshotV1:
        if not 1 <= len(self.narrative_contexts) <= len(NarrativeContext):
            _invalid("narrative_contexts must contain 1..5 values")
        context_order = {item: index for index, item in enumerate(NarrativeContext)}
        ranks = tuple(context_order[item] for item in self.narrative_contexts)
        if len(set(self.narrative_contexts)) != len(self.narrative_contexts) or ranks != tuple(
            sorted(ranks)
        ):
            _invalid("narrative_contexts must use unique frozen canonical order")
        if NarrativeContext.REFERENCE_DEVELOPMENT in self.narrative_contexts:
            _invalid("narrative Profile cannot use REFERENCE_DEVELOPMENT")
        if not 1 <= len(self.sections) <= 16:
            _invalid("sections must contain 1..16 items")
        if len({item.section_id for item in self.sections}) != len(self.sections):
            _invalid("section_id values must be unique")
        if len({item.heading for item in self.sections}) != len(self.sections):
            _invalid("section headings must be unique")
        placeholders = tuple(item.placeholder for item in self.sections)
        if (
            len(set(placeholders)) != len(placeholders)
            or frozenset(placeholders) != _NARRATIVE_PLACEHOLDERS
        ):
            _invalid("sections must contain the exact narrative placeholder set")
        expected_profile_sha256 = _semantic_sha256(
            PROFILE_SHA256_DOMAIN,
            _snapshot_profile_projection(self),
        )
        if self.profile_sha256 != expected_profile_sha256:
            _invalid("profile_sha256 does not bind the exact flattened Profile semantics")
        return self


class _CharacterAssetPromptBindingV1(_StrictFrozenModel):
    asset_content_sha256: LowerSha256
    asset_version_id: PortableId
    character_id: PortableId


class _SceneAssetPromptBindingV1(_StrictFrozenModel):
    asset_content_sha256: LowerSha256
    asset_version_id: PortableId
    scene_id: PortableId


class _DialoguePromptLineV1(_StrictFrozenModel):
    character_id: PortableId
    line_id: PortableId
    ordinal: Annotated[int, Field(ge=0, le=9_223_372_036_854_775_807)]
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_trimmed_text(value, field="dialogue text", maximum=2000)


class _NarrativeShotPromptRenderInputV1(_StrictFrozenModel):
    action: str
    camera_angle: CameraAngleV1
    camera_movement: CameraMovementV1
    character_asset_bindings: tuple[_CharacterAssetPromptBindingV1, ...]
    continuity_notes: str
    dialogue: tuple[_DialoguePromptLineV1, ...]
    emotion_by_character: Mapping[str, str]
    input_kind: Literal[AssetPurpose.NARRATIVE_SHOT]
    narrative: str
    props: tuple[str, ...]
    scene_asset_binding: _SceneAssetPromptBindingV1
    shot_size: ShotSizeV1
    visual_direction: str
    wardrobe_by_character: Mapping[str, str]

    @field_validator("character_asset_bindings", "dialogue", "props", mode="before")
    @classmethod
    def admit_json_arrays(cls, value: object, info: ValidationInfo) -> object:
        return _json_array_to_tuple(value, info)

    @field_validator("action", "continuity_notes")
    @classmethod
    def validate_direction_text(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "direction")
        return _validate_trimmed_text(value, field=field_name, maximum=2000)

    @field_validator("narrative", "visual_direction")
    @classmethod
    def validate_narrative_text(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "narrative")
        return _validate_trimmed_text(value, field=field_name, maximum=4000)

    @field_validator("props")
    @classmethod
    def validate_props(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_text_tuple(
            value,
            field="props",
            minimum=0,
            maximum=16,
            item_maximum=128,
            sorted_values=True,
        )

    @field_validator("emotion_by_character", "wardrobe_by_character")
    @classmethod
    def validate_character_text_map(
        cls,
        value: Mapping[str, str],
        info: object,
    ) -> Mapping[str, str]:
        field_name = getattr(info, "field_name", "character text map")
        keys = tuple(value)
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            _invalid(f"{field_name} keys must be unique and use ascending order")
        result: dict[str, str] = {}
        for key, text in value.items():
            result[_validate_portable_id(key, f"{field_name} key")] = _validate_trimmed_text(
                text,
                field=f"{field_name}[{key}]",
                maximum=512,
            )
        return MappingProxyType(result)

    @field_serializer("emotion_by_character", "wardrobe_by_character")
    def serialize_character_text_map(self, value: Mapping[str, str]) -> dict[str, str]:
        return dict(value)

    @model_validator(mode="after")
    def validate_input_closure(self) -> _NarrativeShotPromptRenderInputV1:
        if len(self.character_asset_bindings) > 2:
            _invalid("character_asset_bindings must contain 0..2 items")
        character_ids = tuple(item.character_id for item in self.character_asset_bindings)
        asset_version_ids = tuple(item.asset_version_id for item in self.character_asset_bindings)
        if character_ids != tuple(sorted(character_ids)) or len(set(character_ids)) != len(
            character_ids
        ):
            _invalid("character_asset_bindings must be unique and sorted by character_id")
        if len(set(asset_version_ids)) != len(asset_version_ids):
            _invalid("character asset version IDs must be unique")
        if tuple(self.emotion_by_character) != character_ids:
            _invalid("emotion_by_character keys must equal character bindings")
        if tuple(self.wardrobe_by_character) != character_ids:
            _invalid("wardrobe_by_character keys must equal character bindings")
        if len(self.dialogue) > 64:
            _invalid("dialogue must contain 0..64 lines")
        ordinals = tuple(item.ordinal for item in self.dialogue)
        line_ids = tuple(item.line_id for item in self.dialogue)
        if any(first >= second for first, second in zip(ordinals, ordinals[1:], strict=False)):
            _invalid("dialogue must use strictly ascending source ordinal order")
        if len(set(line_ids)) != len(line_ids):
            _invalid("dialogue line IDs must be unique")
        if any(item.character_id not in character_ids for item in self.dialogue):
            _invalid("every dialogue character must have a character binding")
        if not character_ids and self.dialogue:
            _invalid("a no-character input must have no dialogue")
        return self


class _PromptRenderReceiptV1(_ZeroAuthorityModel):
    receipt_purpose: Literal["DETERMINISTIC_PROMPT_RENDER_PROCESS_EVIDENCE_ONLY"]
    profile_id: PortableId
    profile_version: SemanticVersion
    profile_sha256: LowerSha256
    catalog_version: SemanticVersion
    catalog_sha256: LowerSha256
    render_input_sha256: LowerSha256
    renderer_id: Literal["sdc.visual-prompt-renderer"]
    renderer_version: Literal["1.0.0"]
    prompt_sha256: LowerSha256
    prompt_size_bytes: Annotated[int, Field(ge=1, le=65_536)]
    prompt_render_receipt_sha256: LowerSha256

    @field_validator("profile_version", "catalog_version")
    @classmethod
    def validate_versions(cls, value: str) -> str:
        return _validate_semantic_version(value, "receipt semantic version")

    @model_validator(mode="after")
    def validate_receipt_digest(self) -> _PromptRenderReceiptV1:
        expected = _semantic_sha256(
            PROMPT_RENDER_RECEIPT_SHA256_DOMAIN,
            _prompt_render_receipt_projection(self),
        )
        if self.prompt_render_receipt_sha256 != expected:
            _invalid("prompt_render_receipt_sha256 does not bind the exact Receipt projection")
        return self


class _CreativeSampleVisualPromptShotV1(_StrictFrozenModel):
    source_shot_id: SourceShotId
    source_shot_ordinal: Annotated[int, Field(ge=0, le=11)]
    render_input: _NarrativeShotPromptRenderInputV1
    render_input_sha256: LowerSha256
    prompt: str
    prompt_sha256: LowerSha256
    prompt_size_bytes: Annotated[int, Field(ge=1, le=65_536)]
    prompt_render_receipt: _PromptRenderReceiptV1

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            _invalid("prompt must contain only Unicode scalar values")
        if unicodedata.normalize("NFC", value) != value:
            _invalid("prompt must already use Unicode NFC")
        if value.startswith("\ufeff") or "\r" in value:
            _invalid("prompt must use LF only and contain no BOM")
        if not value.endswith("\n") or value.endswith("\n\n"):
            _invalid("prompt must end with exactly one LF")
        if any(line.endswith((" ", "\t")) for line in value[:-1].split("\n")):
            _invalid("prompt must contain no trailing horizontal whitespace")
        return value

    @model_validator(mode="after")
    def validate_shot_integrity(self) -> _CreativeSampleVisualPromptShotV1:
        input_projection = _narrative_render_input_projection(self.render_input)
        expected_input_sha256 = _semantic_sha256(
            RENDER_INPUT_SHA256_DOMAIN,
            input_projection,
        )
        if self.render_input_sha256 != expected_input_sha256:
            _invalid("render_input_sha256 does not bind the exact render input")
        prompt_bytes = self.prompt.encode("utf-8")
        expected_prompt_sha256 = hashlib.sha256(prompt_bytes).hexdigest()
        if self.prompt_sha256 != expected_prompt_sha256:
            _invalid("prompt_sha256 does not bind the exact Prompt bytes")
        if self.prompt_size_bytes != len(prompt_bytes):
            _invalid("prompt_size_bytes does not equal the exact UTF-8 byte length")
        receipt = self.prompt_render_receipt
        if (
            receipt.render_input_sha256 != self.render_input_sha256
            or receipt.prompt_sha256 != self.prompt_sha256
            or receipt.prompt_size_bytes != self.prompt_size_bytes
        ):
            _invalid("Prompt Receipt does not bind the enclosing input and Prompt")
        return self


class CreativeSampleVisualPromptSidecarV1(_ZeroAuthorityModel):
    """Immutable offline Prompt sidecar bound to one unchanged Creative Sample v2 compilation."""

    schema_version: Literal["1.0.0"]
    artifact_purpose: Literal["OFFLINE_VISUAL_PROMPT_COMPILATION_SIDECAR"]
    base_compiler_contract: Literal["CREATIVE_SAMPLE_V2"]
    selection_scope: Literal["ALL_NARRATIVE_SHOTS"]
    base_compilation_id: BaseCompilationId
    spec_sha256: LowerSha256
    selection_decision_kind: Literal["HUMAN_DECISION"]
    selection_decision_ref: PortableId
    profile_snapshot: _VisualPromptProfileSnapshotV1
    shot_prompts: tuple[_CreativeSampleVisualPromptShotV1, ...] = Field(min_length=8, max_length=12)
    sidecar_sha256: LowerSha256

    @field_validator("shot_prompts", mode="before")
    @classmethod
    def admit_json_arrays(cls, value: object, info: ValidationInfo) -> object:
        return _json_array_to_tuple(value, info)

    @model_validator(mode="after")
    def validate_sidecar(self) -> CreativeSampleVisualPromptSidecarV1:
        expected_ordinals = tuple(range(len(self.shot_prompts)))
        if tuple(item.source_shot_ordinal for item in self.shot_prompts) != expected_ordinals:
            _invalid("shot_prompts must use contiguous source ordinals beginning at zero")
        shot_ids = tuple(item.source_shot_id for item in self.shot_prompts)
        if len(set(shot_ids)) != len(shot_ids):
            _invalid("shot_prompts source_shot_id values must be unique")
        snapshot = self.profile_snapshot
        for item in self.shot_prompts:
            receipt = item.prompt_render_receipt
            expected_prompt = _render_formal_prompt_bytes(snapshot, item.render_input)
            if item.prompt.encode("utf-8") != expected_prompt:
                _invalid("shot Prompt does not match the exact Snapshot and render input")
            if (
                receipt.profile_id != snapshot.profile_id
                or receipt.profile_version != snapshot.profile_version
                or receipt.profile_sha256 != snapshot.profile_sha256
                or receipt.catalog_version != snapshot.catalog_version
                or receipt.catalog_sha256 != snapshot.catalog_sha256
            ):
                _invalid("every Prompt Receipt must bind the exact sidecar Snapshot")
        expected = _semantic_sha256(
            VISUAL_PROMPT_COMPILER_SIDECAR_SHA256_DOMAIN,
            _creative_sample_visual_prompt_sidecar_projection_unchecked(self),
        )
        if self.sidecar_sha256 != expected:
            _invalid("sidecar_sha256 does not bind the exact sidecar projection")
        return self


def _constraint_set_projection(value: _PromptConstraintSetV1) -> dict[str, object]:
    return {
        "negative_prompt_constraints": list(value.negative_prompt_constraints),
        "positive_prompt_constraints": list(value.positive_prompt_constraints),
        "qc_expectations": list(value.qc_expectations),
    }


def _prompt_section_projection(value: _PromptSectionV1) -> dict[str, object]:
    return {
        "heading": value.heading,
        "placeholder": value.placeholder.value,
        "section_id": value.section_id,
    }


def _snapshot_profile_projection(value: _VisualPromptProfileSnapshotV1) -> dict[str, object]:
    return {
        "asset_purpose": value.asset_purpose.value,
        "constraint_set": _constraint_set_projection(value.constraint_set),
        "narrative_contexts": [item.value for item in value.narrative_contexts],
        "profile_id": value.profile_id,
        "profile_version": value.profile_version,
        "reference_asset_recipe": None,
        "reference_asset_types": [],
        "renderer_version": value.renderer_version,
        "sections": [_prompt_section_projection(item) for item in value.sections],
        "shot_type": value.shot_type.value,
        "visual_style_id": value.visual_style_id.value,
    }


def _snapshot_projection(value: _VisualPromptProfileSnapshotV1) -> dict[str, object]:
    profile = _snapshot_profile_projection(value)
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


def _character_binding_projection(value: _CharacterAssetPromptBindingV1) -> dict[str, object]:
    return {
        "asset_content_sha256": value.asset_content_sha256,
        "asset_version_id": value.asset_version_id,
        "character_id": value.character_id,
    }


def _scene_binding_projection(value: _SceneAssetPromptBindingV1) -> dict[str, object]:
    return {
        "asset_content_sha256": value.asset_content_sha256,
        "asset_version_id": value.asset_version_id,
        "scene_id": value.scene_id,
    }


def _dialogue_line_projection(value: _DialoguePromptLineV1) -> dict[str, object]:
    return {
        "character_id": value.character_id,
        "line_id": value.line_id,
        "ordinal": value.ordinal,
        "text": value.text,
    }


def _narrative_render_input_projection(
    value: _NarrativeShotPromptRenderInputV1,
) -> dict[str, object]:
    return {
        "action": value.action,
        "camera_angle": value.camera_angle.value,
        "camera_movement": value.camera_movement.value,
        "character_asset_bindings": [
            _character_binding_projection(item) for item in value.character_asset_bindings
        ],
        "continuity_notes": value.continuity_notes,
        "dialogue": [_dialogue_line_projection(item) for item in value.dialogue],
        "emotion_by_character": dict(value.emotion_by_character),
        "input_kind": value.input_kind.value,
        "narrative": value.narrative,
        "props": list(value.props),
        "scene_asset_binding": _scene_binding_projection(value.scene_asset_binding),
        "shot_size": value.shot_size.value,
        "visual_direction": value.visual_direction,
        "wardrobe_by_character": dict(value.wardrobe_by_character),
    }


def _render_formal_prompt_bytes(
    snapshot: _VisualPromptProfileSnapshotV1,
    render_input: _NarrativeShotPromptRenderInputV1,
) -> bytes:
    input_projection = _narrative_render_input_projection(render_input)
    lines: list[str] = []
    for section in snapshot.sections:
        rendered_value = input_projection[section.placeholder.value]
        if type(rendered_value) is str:
            text = rendered_value
        else:
            text = _canonical_compact_json(rendered_value).decode("utf-8")
        lines.append(f"{section.heading}: {text}")
    lines.append("Positive Prompt Constraints:")
    lines.extend(f"- {item}" for item in snapshot.constraint_set.positive_prompt_constraints)
    lines.append("Negative Prompt Constraints:")
    lines.extend(f"- {item}" for item in snapshot.constraint_set.negative_prompt_constraints)
    prompt = "\n".join(lines) + "\n"
    return prompt.encode("utf-8")


def _prompt_render_receipt_projection(value: _PromptRenderReceiptV1) -> dict[str, object]:
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


def _prompt_render_receipt_document_projection(
    value: _PromptRenderReceiptV1,
) -> dict[str, object]:
    return {
        **_prompt_render_receipt_projection(value),
        "prompt_render_receipt_sha256": value.prompt_render_receipt_sha256,
    }


def _shot_prompt_projection(value: _CreativeSampleVisualPromptShotV1) -> dict[str, object]:
    return {
        "source_shot_id": value.source_shot_id,
        "source_shot_ordinal": value.source_shot_ordinal,
        "render_input": _narrative_render_input_projection(value.render_input),
        "render_input_sha256": value.render_input_sha256,
        "prompt": value.prompt,
        "prompt_sha256": value.prompt_sha256,
        "prompt_size_bytes": value.prompt_size_bytes,
        "prompt_render_receipt": _prompt_render_receipt_document_projection(
            value.prompt_render_receipt
        ),
    }


def _sidecar_projection_from_parts(
    *,
    base_compilation_id: str,
    spec_sha256: str,
    selection_decision_ref: str,
    profile_snapshot: _VisualPromptProfileSnapshotV1,
    shot_prompts: tuple[_CreativeSampleVisualPromptShotV1, ...],
) -> dict[str, object]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "artifact_purpose": _ARTIFACT_PURPOSE,
        "base_compiler_contract": _BASE_COMPILER_CONTRACT,
        "selection_scope": _SELECTION_SCOPE,
        "base_compilation_id": base_compilation_id,
        "spec_sha256": spec_sha256,
        "selection_decision_kind": _SELECTION_DECISION_KIND,
        "selection_decision_ref": selection_decision_ref,
        "profile_snapshot": _snapshot_projection(profile_snapshot),
        "shot_prompts": [_shot_prompt_projection(item) for item in shot_prompts],
        "current_gate": _CURRENT_GATE,
        "provider_state": _PROVIDER_STATE,
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
        "grants_rights": False,
        "grants_qualification": False,
        "grants_execution_authority": False,
        "eligible_for_asset_promotion": False,
        "replaces_rights_manifest": False,
        "usage_restriction": _USAGE_RESTRICTION,
    }


def _creative_sample_visual_prompt_sidecar_projection_unchecked(
    value: CreativeSampleVisualPromptSidecarV1,
) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "artifact_purpose": value.artifact_purpose,
        "base_compiler_contract": value.base_compiler_contract,
        "selection_scope": value.selection_scope,
        "base_compilation_id": value.base_compilation_id,
        "spec_sha256": value.spec_sha256,
        "selection_decision_kind": value.selection_decision_kind,
        "selection_decision_ref": value.selection_decision_ref,
        "profile_snapshot": _snapshot_projection(value.profile_snapshot),
        "shot_prompts": [_shot_prompt_projection(item) for item in value.shot_prompts],
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
        "grants_rights": value.grants_rights,
        "grants_qualification": value.grants_qualification,
        "grants_execution_authority": value.grants_execution_authority,
        "eligible_for_asset_promotion": value.eligible_for_asset_promotion,
        "replaces_rights_manifest": value.replaces_rights_manifest,
        "usage_restriction": value.usage_restriction,
    }


def _creative_sample_visual_prompt_sidecar_sha256_unchecked(
    value: CreativeSampleVisualPromptSidecarV1,
) -> str:
    return _semantic_sha256(
        VISUAL_PROMPT_COMPILER_SIDECAR_SHA256_DOMAIN,
        _creative_sample_visual_prompt_sidecar_projection_unchecked(value),
    )


def _revalidate_sidecar(
    value: CreativeSampleVisualPromptSidecarV1,
) -> CreativeSampleVisualPromptSidecarV1:
    if type(value) is not CreativeSampleVisualPromptSidecarV1:
        _invalid("sidecar must be an exact CreativeSampleVisualPromptSidecarV1")
    _require_exact_model_storage(value, field="sidecar")
    try:
        return CreativeSampleVisualPromptSidecarV1.model_validate_json(
            value.model_dump_json(),
            strict=True,
        )
    except (ValidationError, TypeError, ValueError, RecursionError) as exc:
        raise VisualPromptCompilerError(
            "sidecar failed complete strict revalidation"
        ) from exc


def creative_sample_visual_prompt_sidecar_projection(
    value: CreativeSampleVisualPromptSidecarV1,
) -> dict[str, object]:
    """Revalidate one exact sidecar, then project every semantic field except self digest."""

    validated = _revalidate_sidecar(value)
    return _creative_sample_visual_prompt_sidecar_projection_unchecked(validated)


def creative_sample_visual_prompt_sidecar_sha256(
    value: CreativeSampleVisualPromptSidecarV1,
) -> str:
    """Revalidate and return the ADR-041 domain-separated sidecar semantic identity."""

    validated = _revalidate_sidecar(value)
    return _creative_sample_visual_prompt_sidecar_sha256_unchecked(validated)


def _creative_sample_spec_sha256(spec: CreativeSampleSpec) -> str:
    try:
        source = spec.model_dump(mode="json")
        raw = json.dumps(
            source,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(raw.encode()).hexdigest()
    except (TypeError, ValueError, RecursionError) as exc:
        raise VisualPromptCompilerError(
            "source specification identity serialization failed"
        ) from exc


def _active_character_asset(
    versions: tuple[CharacterAssetVersion, ...],
    active_id: str,
) -> CharacterAssetVersion:
    matches = tuple(item for item in versions if item.id == active_id)
    if len(matches) != 1:
        _invalid("character Bible must resolve exactly one active AssetVersion")
    return matches[0]


def _active_scene_asset(
    versions: tuple[SceneAssetVersion, ...],
    active_id: str,
) -> SceneAssetVersion:
    matches = tuple(item for item in versions if item.id == active_id)
    if len(matches) != 1:
        _invalid("scene Bible must resolve exactly one active AssetVersion")
    return matches[0]


def _require_source_base_closure(
    spec: CreativeSampleSpec,
    base: CreativeSampleCompilation,
) -> None:
    if base.spec_sha256 != _creative_sample_spec_sha256(spec):
        _invalid("base compilation does not bind the exact source specification")
    if (
        base.nir.character_bibles != spec.character_bibles
        or base.nir.scene_bibles != spec.scene_bibles
        or base.nir.dialogue != spec.dialogue
    ):
        _invalid("base NIRV2 does not preserve the exact source Bible and dialogue values")
    if len(base.pir.shots) != len(spec.shots):
        _invalid("base compilation must contain exactly one shot for every source shot")
    scene_by_id = {item.scene_id: item for item in spec.scene_bibles}
    character_by_id = {item.character_id: item for item in spec.character_bibles}
    for source, compiled in zip(spec.shots, base.pir.shots, strict=True):
        expected_scene = scene_by_id.get(source.scene_id)
        if expected_scene is None:
            _invalid("source shot references an unknown scene Bible")
        expected_character_assets = tuple(
            CharacterAssetBinding(
                character_id=character_id,
                asset_version_id=character_by_id[character_id].active_asset_version_id,
            )
            for character_id in source.character_ids
        )
        source_values = (
            source.ordinal,
            source.scene_id,
            source.narrative,
            source.visual_direction,
            source.emotion_by_character,
            source.action,
            source.shot_size,
            source.camera_angle,
            source.camera_movement,
            source.wardrobe_by_character,
            source.props,
            source.continuity_notes,
            source.start_ms,
            source.duration_ms,
            source.dialogue_line_ids,
        )
        compiled_values = (
            compiled.ordinal,
            compiled.scene_bible_id,
            compiled.narrative,
            compiled.visual_direction,
            compiled.emotion_by_character,
            compiled.action,
            compiled.shot_size,
            compiled.camera_angle,
            compiled.camera_movement,
            compiled.wardrobe_by_character,
            compiled.props,
            compiled.continuity_notes,
            compiled.start_ms,
            compiled.duration_ms,
            compiled.dialogue_line_ids,
        )
        if source_values != compiled_values:
            _invalid("compiled shot semantics do not match the exact source shot")
        if compiled.scene_asset_version_id != expected_scene.active_asset_version_id:
            _invalid("compiled shot does not bind the active scene AssetVersion")
        if compiled.character_assets != expected_character_assets:
            _invalid("compiled shot does not bind the exact active character AssetVersions")


def _derive_narrative_render_input(
    spec: CreativeSampleSpec,
    source: CreativeSampleShotSpec,
    compiled: StoryboardShotV2,
) -> NarrativeShotPromptRenderInput:
    scene_by_id = {item.scene_id: item for item in spec.scene_bibles}
    character_by_id = {item.character_id: item for item in spec.character_bibles}
    dialogue_by_id = {item.line_id: item for item in spec.dialogue}
    scene = scene_by_id.get(source.scene_id)
    if scene is None:
        _invalid("source shot references an unknown scene Bible")
    scene_asset = _active_scene_asset(scene.asset_versions, scene.active_asset_version_id)
    if compiled.scene_asset_version_id != scene_asset.id:
        _invalid("compiled shot scene binding differs from the active source AssetVersion")

    character_bindings: list[CharacterAssetPromptBinding] = []
    for character_id in source.character_ids:
        bible = character_by_id.get(character_id)
        if bible is None:
            _invalid("source shot references an unknown character Bible")
        asset = _active_character_asset(bible.asset_versions, bible.active_asset_version_id)
        character_bindings.append(
            CharacterAssetPromptBinding(
                asset_content_sha256=asset.content_sha256,
                asset_version_id=asset.id,
                character_id=character_id,
            )
        )
    expected_compiled_bindings = tuple(
        (item.character_id, item.asset_version_id) for item in compiled.character_assets
    )
    actual_bindings = tuple(
        (item.character_id, item.asset_version_id) for item in character_bindings
    )
    if actual_bindings != expected_compiled_bindings:
        _invalid("render input character bindings do not match the base storyboard shot")

    dialogue: list[DialoguePromptLine] = []
    prior_ordinal = -1
    for line_id in source.dialogue_line_ids:
        line = dialogue_by_id.get(line_id)
        if line is None:
            _invalid("source shot references an unknown dialogue line")
        if line.ordinal <= prior_ordinal:
            _invalid("source shot dialogue must use strictly ascending source ordinal order")
        if line.scene_id != source.scene_id or line.character_id not in source.character_ids:
            _invalid("dialogue line does not close over the source shot scene and characters")
        prior_ordinal = line.ordinal
        dialogue.append(
            DialoguePromptLine(
                character_id=line.character_id,
                line_id=line.line_id,
                ordinal=line.ordinal,
                text=line.text,
            )
        )

    return NarrativeShotPromptRenderInput(
        action=source.action,
        camera_angle=CameraAngleV1(source.camera_angle.value),
        camera_movement=CameraMovementV1(source.camera_movement.value),
        character_asset_bindings=tuple(character_bindings),
        continuity_notes=source.continuity_notes,
        dialogue=tuple(dialogue),
        emotion_by_character=tuple(sorted(source.emotion_by_character.items())),
        input_kind=AssetPurpose.NARRATIVE_SHOT,
        narrative=source.narrative,
        props=source.props,
        scene_asset_binding=SceneAssetPromptBinding(
            asset_content_sha256=scene_asset.content_sha256,
            asset_version_id=scene_asset.id,
            scene_id=scene.scene_id,
        ),
        shot_size=ShotSizeV1(source.shot_size.value),
        visual_direction=source.visual_direction,
        wardrobe_by_character=tuple(sorted(source.wardrobe_by_character.items())),
    )


def _snapshot_contract(
    snapshot: VisualPromptProfileSnapshot,
) -> _VisualPromptProfileSnapshotV1:
    profile = snapshot.profile
    if (
        profile.asset_purpose is not AssetPurpose.NARRATIVE_SHOT
        or profile.renderer_version != _RENDERER_VERSION
        or profile.shot_type is not ShotType.NARRATIVE_FRAME
        or profile.visual_style_id is not VisualStyleId.CINEMATIC_STORYBOARD_V1
        or profile.reference_asset_recipe is not None
        or profile.reference_asset_types
    ):
        _invalid("admitted Snapshot is outside the narrative-only Compiler slice")
    contract = _VisualPromptProfileSnapshotV1(
        asset_purpose=AssetPurpose.NARRATIVE_SHOT,
        constraint_set=_PromptConstraintSetV1(
            negative_prompt_constraints=profile.constraint_set.negative_prompt_constraints,
            positive_prompt_constraints=profile.constraint_set.positive_prompt_constraints,
            qc_expectations=profile.constraint_set.qc_expectations,
        ),
        narrative_contexts=profile.narrative_contexts,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        reference_asset_recipe=None,
        reference_asset_types=(),
        renderer_version=_RENDERER_VERSION,
        sections=tuple(
            _PromptSectionV1(
                heading=item.heading,
                placeholder=item.placeholder,
                section_id=item.section_id,
            )
            for item in profile.sections
        ),
        shot_type=ShotType.NARRATIVE_FRAME,
        visual_style_id=VisualStyleId.CINEMATIC_STORYBOARD_V1,
        profile_sha256=snapshot.profile_sha256,
        catalog_version=snapshot.catalog_version,
        catalog_sha256=snapshot.catalog_sha256,
    )
    if _snapshot_projection(contract) != visual_prompt_profile_snapshot_projection(snapshot):
        _invalid("formal Snapshot projection differs from the admitted Phase 1 Snapshot")
    return contract


def _render_input_contract(
    value: NarrativeShotPromptRenderInput,
) -> _NarrativeShotPromptRenderInputV1:
    return _NarrativeShotPromptRenderInputV1(
        action=value.action,
        camera_angle=value.camera_angle,
        camera_movement=value.camera_movement,
        character_asset_bindings=tuple(
            _CharacterAssetPromptBindingV1(
                asset_content_sha256=item.asset_content_sha256,
                asset_version_id=item.asset_version_id,
                character_id=item.character_id,
            )
            for item in value.character_asset_bindings
        ),
        continuity_notes=value.continuity_notes,
        dialogue=tuple(
            _DialoguePromptLineV1(
                character_id=item.character_id,
                line_id=item.line_id,
                ordinal=item.ordinal,
                text=item.text,
            )
            for item in value.dialogue
        ),
        emotion_by_character=dict(value.emotion_by_character),
        input_kind=AssetPurpose.NARRATIVE_SHOT,
        narrative=value.narrative,
        props=value.props,
        scene_asset_binding=_SceneAssetPromptBindingV1(
            asset_content_sha256=value.scene_asset_binding.asset_content_sha256,
            asset_version_id=value.scene_asset_binding.asset_version_id,
            scene_id=value.scene_asset_binding.scene_id,
        ),
        shot_size=value.shot_size,
        visual_direction=value.visual_direction,
        wardrobe_by_character=dict(value.wardrobe_by_character),
    )


def _receipt_contract(value: PromptRenderReceipt) -> _PromptRenderReceiptV1:
    source = prompt_render_receipt_document_projection(value)
    return _PromptRenderReceiptV1.model_validate(source, strict=True)


def _build_sidecar(
    *,
    request: CreativeSampleVisualPromptCompileRequestV1,
    base: CreativeSampleCompilation,
    profile_snapshot: _VisualPromptProfileSnapshotV1,
    shot_prompts: tuple[_CreativeSampleVisualPromptShotV1, ...],
) -> CreativeSampleVisualPromptSidecarV1:
    projection = _sidecar_projection_from_parts(
        base_compilation_id=base.id,
        spec_sha256=base.spec_sha256,
        selection_decision_ref=request.selection_decision_ref,
        profile_snapshot=profile_snapshot,
        shot_prompts=shot_prompts,
    )
    digest = _semantic_sha256(VISUAL_PROMPT_COMPILER_SIDECAR_SHA256_DOMAIN, projection)
    return CreativeSampleVisualPromptSidecarV1(
        schema_version=_SCHEMA_VERSION,
        artifact_purpose=_ARTIFACT_PURPOSE,
        base_compiler_contract=_BASE_COMPILER_CONTRACT,
        selection_scope=_SELECTION_SCOPE,
        base_compilation_id=base.id,
        spec_sha256=base.spec_sha256,
        selection_decision_kind=_SELECTION_DECISION_KIND,
        selection_decision_ref=request.selection_decision_ref,
        profile_snapshot=profile_snapshot,
        shot_prompts=shot_prompts,
        current_gate=_CURRENT_GATE,
        provider_state=_PROVIDER_STATE,
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
        grants_rights=False,
        grants_qualification=False,
        grants_execution_authority=False,
        eligible_for_asset_promotion=False,
        replaces_rights_manifest=False,
        usage_restriction=_USAGE_RESTRICTION,
        sidecar_sha256=digest,
    )


def compile_creative_sample_visual_prompts(
    spec: CreativeSampleSpec,
    request: CreativeSampleVisualPromptCompileRequestV1,
) -> tuple[CreativeSampleCompilation, CreativeSampleVisualPromptSidecarV1]:
    """Compile one unchanged Creative Sample v2 base plus its offline Prompt sidecar."""

    if type(spec) is not CreativeSampleSpec:
        _invalid("spec must be an exact CreativeSampleSpec")
    if type(request) is not CreativeSampleVisualPromptCompileRequestV1:
        _invalid("request must be an exact CreativeSampleVisualPromptCompileRequestV1")
    _require_exact_model_storage(spec, field="spec")
    _require_exact_model_storage(request, field="request")
    try:
        CreativeSampleSpec.model_validate(
            spec.model_dump(mode="python"),
            strict=True,
        )
    except (ValidationError, TypeError, ValueError, RecursionError) as exc:
        raise VisualPromptCompilerError(
            "spec failed complete Creative Sample strict revalidation"
        ) from exc
    try:
        request = CreativeSampleVisualPromptCompileRequestV1.model_validate(
            request,
            strict=True,
        )
    except (ValidationError, TypeError, ValueError, RecursionError) as exc:
        raise VisualPromptCompilerError(
            "request failed complete strict revalidation"
        ) from exc
    spec_sha256 = _creative_sample_spec_sha256(spec)
    if request.spec_sha256 != spec_sha256:
        _invalid("request spec_sha256 does not bind the exact source specification")

    compiled_base = compile_creative_sample(spec)
    if type(compiled_base) is not CreativeSampleCompilation:
        _invalid("released base compiler returned an unexpected contract type")
    _require_exact_model_storage(compiled_base, field="base compilation")
    try:
        base = CreativeSampleCompilation.model_validate(
            compiled_base.model_dump(mode="python"),
            strict=True,
        )
    except (ValidationError, TypeError, ValueError, RecursionError) as exc:
        raise VisualPromptCompilerError(
            "base compilation failed complete identity and closure revalidation"
        ) from exc
    if base.spec_sha256 != spec_sha256:
        _invalid("released base compiler returned an unexpected specification identity")
    _require_source_base_closure(spec, base)

    try:
        snapshot = resolve_visual_prompt_profile(
            VISUAL_PROMPT_CATALOG,
            catalog_version=request.catalog_version,
            catalog_sha256=request.catalog_sha256,
            profile_id=request.profile_id,
            profile_version=request.profile_version,
            profile_sha256=request.profile_sha256,
        )
    except VisualPromptProfileError as exc:
        raise VisualPromptCompilerError(
            "the exact five-value Profile selection was rejected"
        ) from exc
    if snapshot.asset_purpose is not AssetPurpose.NARRATIVE_SHOT:
        _invalid("the selected Profile purpose must be NARRATIVE_SHOT")
    formal_snapshot = _snapshot_contract(snapshot)

    shot_prompts: list[_CreativeSampleVisualPromptShotV1] = []
    for source, compiled in zip(spec.shots, base.pir.shots, strict=True):
        render_input = _derive_narrative_render_input(spec, source, compiled)
        try:
            prompt_bytes, receipt = render_visual_prompt(render_input, snapshot)
        except VisualPromptProfileError as exc:
            raise VisualPromptCompilerError("deterministic visual Prompt rendering failed") from exc
        input_digest = prompt_render_input_sha256(render_input)
        if receipt.render_input_sha256 != input_digest:
            _invalid("renderer Receipt does not bind the exact derived render input")
        prompt_digest = hashlib.sha256(prompt_bytes).hexdigest()
        if receipt.prompt_sha256 != prompt_digest or receipt.prompt_size_bytes != len(prompt_bytes):
            _invalid("renderer Receipt does not bind the exact Prompt bytes")
        try:
            prompt = prompt_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise VisualPromptCompilerError("renderer returned non-UTF-8 Prompt bytes") from exc
        formal_input = _render_input_contract(render_input)
        if _semantic_sha256(
            RENDER_INPUT_SHA256_DOMAIN,
            _narrative_render_input_projection(formal_input),
        ) != input_digest:
            _invalid("formal render-input projection differs from the Phase 1 projection")
        shot_prompts.append(
            _CreativeSampleVisualPromptShotV1(
                source_shot_id=compiled.id,
                source_shot_ordinal=source.ordinal,
                render_input=formal_input,
                render_input_sha256=input_digest,
                prompt=prompt,
                prompt_sha256=prompt_digest,
                prompt_size_bytes=len(prompt_bytes),
                prompt_render_receipt=_receipt_contract(receipt),
            )
        )

    sidecar = _build_sidecar(
        request=request,
        base=base,
        profile_snapshot=formal_snapshot,
        shot_prompts=tuple(shot_prompts),
    )
    if sidecar.sidecar_sha256 != creative_sample_visual_prompt_sidecar_sha256(sidecar):
        _invalid("constructed sidecar failed its independent semantic identity check")
    return base, sidecar


__all__ = [
    "CreativeSampleVisualPromptCompileRequestV1",
    "CreativeSampleVisualPromptSidecarV1",
    "VISUAL_PROMPT_COMPILER_SIDECAR_SHA256_DOMAIN",
    "VisualPromptCompilerError",
    "compile_creative_sample_visual_prompts",
    "creative_sample_visual_prompt_sidecar_projection",
    "creative_sample_visual_prompt_sidecar_sha256",
]
