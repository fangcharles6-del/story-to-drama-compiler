"""Deterministic offline Character/Scene reference Prompt compilation.

This isolated module implements the single-subject, zero-authority boundary accepted by
SDC-ADR-042.  It performs no filesystem, environment, clock, randomness, network, Provider,
Runtime, QC, Candidate, persistence, publication, or asset-promotion operation.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterator, Mapping, Sized
from dataclasses import dataclass
from typing import Annotated, ClassVar, Literal, NoReturn, Self, cast

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
from pydantic.config import ExtraValues

from sdc.contracts import (
    CharacterAssetVersion,
    CharacterBible,
    SceneAssetVersion,
    SceneBible,
)
from sdc.visual_prompt_catalog import VISUAL_PROMPT_CATALOG
from sdc.visual_prompt_profiles import (
    PROFILE_SHA256_DOMAIN,
    PROMPT_RENDER_RECEIPT_SHA256_DOMAIN,
    RENDER_INPUT_SHA256_DOMAIN,
    AssetPurpose,
    CharacterAssetPromptBinding,
    CharacterReferenceAssetRecipe,
    CharacterReferencePromptRenderInput,
    NarrativeContext,
    PlaceholderId,
    PromptRenderReceipt,
    ReferenceAssetRecipeKind,
    ReferenceAssetType,
    SceneAssetPromptBinding,
    SceneReferenceAssetRecipe,
    SceneReferencePromptRenderInput,
    ShotType,
    VisualPromptProfileError,
    VisualPromptProfileSnapshot,
    VisualStyleId,
    prompt_render_input_projection,
    prompt_render_input_sha256,
    prompt_render_receipt_document_projection,
    render_visual_prompt,
    resolve_visual_prompt_profile,
    visual_prompt_profile_snapshot_projection,
)

VISUAL_REFERENCE_PROMPT_COMPILER_ARTIFACT_SHA256_DOMAIN = (
    b"sdc:visual-prompt-reference-compiler-artifact:v1\0"
)

_SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"
_REQUEST_PURPOSE: Literal["COMPILE_OFFLINE_REFERENCE_VISUAL_PROMPT"] = (
    "COMPILE_OFFLINE_REFERENCE_VISUAL_PROMPT"
)
_ARTIFACT_PURPOSE: Literal["OFFLINE_REFERENCE_VISUAL_PROMPT_ARTIFACT"] = (
    "OFFLINE_REFERENCE_VISUAL_PROMPT_ARTIFACT"
)
_SOURCE_CONTRACT: Literal["CHARACTER_OR_SCENE_BIBLE_V1"] = "CHARACTER_OR_SCENE_BIBLE_V1"
_SELECTION_SCOPE: Literal["ONE_REFERENCE_SUBJECT"] = "ONE_REFERENCE_SUBJECT"
_HUMAN_DECISION: Literal["HUMAN_DECISION"] = "HUMAN_DECISION"
_CURRENT_GATE: Literal["HUMAN_GATE"] = "HUMAN_GATE"
_PROVIDER_STATE: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
_USAGE_RESTRICTION: Literal["MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"] = (
    "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
)
_RENDERER_VERSION: Literal["1.0.0"] = "1.0.0"

_REQUEST_MAX_BYTES = 262_144
_ARTIFACT_MAX_BYTES = 524_288
_BIBLE_MAX_BYTES = 524_288
_PROMPT_MAX_BYTES = 65_536
_MAX_JSON_DEPTH = 16
_MAX_CONTAINER_ITEMS = 64

_PORTABLE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_LOWER_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_SEMANTIC_VERSION_PATTERN = r"^(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})$"
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

_CHARACTER_REFERENCE_ASSET_TYPES = (
    ReferenceAssetType.CHARACTER_IDENTITY_SHEET,
    ReferenceAssetType.CHARACTER_POSE_REFERENCE,
    ReferenceAssetType.CHARACTER_EXPRESSION_REFERENCE,
)
_SCENE_REFERENCE_ASSET_TYPES = (
    ReferenceAssetType.SCENE_ESTABLISHING_REFERENCE,
    ReferenceAssetType.SCENE_LIGHTING_REFERENCE,
    ReferenceAssetType.SCENE_MATERIAL_REFERENCE,
    ReferenceAssetType.SCENE_PROP_PLACEMENT_REFERENCE,
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
_EXACT_STORAGE_SCALAR_TYPES = frozenset(
    {
        str,
        int,
        bool,
        type(None),
        AssetPurpose,
        NarrativeContext,
        PlaceholderId,
        ReferenceAssetRecipeKind,
        ReferenceAssetType,
        ShotType,
        VisualStyleId,
    }
)

PortableId = Annotated[str, Field(pattern=_PORTABLE_ID_PATTERN)]
LowerSha256 = Annotated[str, Field(pattern=_LOWER_SHA256_PATTERN)]
SemanticVersion = Annotated[str, Field(pattern=_SEMANTIC_VERSION_PATTERN)]
_Text128 = Annotated[str, Field(min_length=1, max_length=128)]
_Text512 = Annotated[str, Field(min_length=1, max_length=512)]
_Text1000 = Annotated[str, Field(min_length=1, max_length=1000)]
_Text2000 = Annotated[str, Field(min_length=1, max_length=2000)]
_Text4000 = Annotated[str, Field(min_length=1, max_length=4000)]
_PromptText = Annotated[str, Field(min_length=1, max_length=_PROMPT_MAX_BYTES)]
_PropsV1 = Annotated[
    tuple[_Text128, ...],
    Field(min_length=0, max_length=16, json_schema_extra={"uniqueItems": True}),
]
_ConstraintTextTupleV1 = Annotated[
    tuple[_Text1000, ...],
    Field(min_length=1, max_length=32, json_schema_extra={"uniqueItems": True}),
]
_RecipeTextTupleV1 = Annotated[
    tuple[_Text1000, ...],
    Field(min_length=1, max_length=16, json_schema_extra={"uniqueItems": True}),
]
_NarrativeContextsV1 = Annotated[
    tuple[NarrativeContext, ...],
    Field(
        min_length=1,
        max_length=len(NarrativeContext),
        json_schema_extra={"uniqueItems": True},
    ),
]
_CharacterReferenceAssetTypesV1 = tuple[
    Literal[ReferenceAssetType.CHARACTER_IDENTITY_SHEET],
    Literal[ReferenceAssetType.CHARACTER_POSE_REFERENCE],
    Literal[ReferenceAssetType.CHARACTER_EXPRESSION_REFERENCE],
]
_SceneReferenceAssetTypesV1 = tuple[
    Literal[ReferenceAssetType.SCENE_ESTABLISHING_REFERENCE],
    Literal[ReferenceAssetType.SCENE_LIGHTING_REFERENCE],
    Literal[ReferenceAssetType.SCENE_MATERIAL_REFERENCE],
    Literal[ReferenceAssetType.SCENE_PROP_PLACEMENT_REFERENCE],
]
_CharacterPrimaryBindingFieldsV1 = tuple[
    Literal["character_id"],
    Literal["asset_version_id"],
    Literal["asset_content_sha256"],
]
_ScenePrimaryBindingFieldsV1 = tuple[
    Literal["scene_id"],
    Literal["asset_version_id"],
    Literal["asset_content_sha256"],
]


class VisualReferencePromptCompilerError(ValueError):
    """One value violates the accepted ADR-042 offline Compiler boundary."""


@dataclass(frozen=True, slots=True)
class _FrozenStringMap(Mapping[str, str]):
    _items: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if type(self._items) is not tuple:
            raise ValueError("frozen string map storage must be an exact tuple")
        if len(self._items) > _MAX_CONTAINER_ITEMS:
            raise ValueError("frozen string map exceeds 64 entries")
        keys: list[str] = []
        for pair in self._items:
            if (
                type(pair) is not tuple
                or len(pair) != 2
                or type(pair[0]) is not str
                or type(pair[1]) is not str
            ):
                raise ValueError("frozen string map entries must be exact string pairs")
            keys.append(pair[0])
        if keys != sorted(keys) or len(set(keys)) != len(keys):
            raise ValueError("frozen string map keys must be unique and ascending")

    def __getitem__(self, key: str) -> str:
        for stored_key, value in self._items:
            if stored_key == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _value in self._items)

    def __len__(self) -> int:
        return len(self._items)


def _invalid(message: str) -> NoReturn:
    raise VisualReferencePromptCompilerError(message)


def _require_exact_model_storage(value: BaseModel, *, field: str) -> None:
    active: set[int] = set()

    def visit(item: object, *, depth: int) -> None:
        if type(item) in _EXACT_STORAGE_SCALAR_TYPES:
            return
        if depth > _MAX_JSON_DEPTH:
            _invalid(f"{field} instance graph exceeds 16 nested containers")
        if isinstance(item, BaseModel) and type(item) not in _exact_storage_model_types():
            _invalid(f"{field} contains a model with a non-exact dynamic type")
        if not isinstance(item, BaseModel) and type(item) not in {tuple, _FrozenStringMap}:
            if isinstance(item, (Mapping, list, tuple, set, frozenset)):
                _invalid(f"{field} contains a container with a non-exact dynamic type")
            _invalid(f"{field} contains a value with a non-exact dynamic type")
        identity = id(item)
        if identity in active:
            _invalid(f"{field} instance graph must not contain a recursive cycle")
        active.add(identity)
        try:
            if isinstance(item, BaseModel):
                model_fields = type(item).model_fields
                if len(item.__dict__) != len(model_fields):
                    _invalid(f"{field} instance storage must contain exactly its declared fields")
                declared = frozenset(model_fields)
                stored = frozenset(item.__dict__)
                if stored != declared or item.__pydantic_extra__:
                    _invalid(f"{field} instance storage must contain exactly its declared fields")
                for field_name in declared:
                    visit(item.__dict__[field_name], depth=depth + 1)
            elif type(item) is _FrozenStringMap:
                if type(item._items) is not tuple:
                    _invalid(f"{field} contains a malformed frozen string map")
                if len(item._items) > _MAX_CONTAINER_ITEMS:
                    _invalid(f"{field} contains a frozen string map exceeding 64 entries")
                keys: list[str] = []
                for pair in item._items:
                    if (
                        type(pair) is not tuple
                        or len(pair) != 2
                        or type(pair[0]) is not str
                        or type(pair[1]) is not str
                    ):
                        _invalid(f"{field} contains a malformed frozen string map entry")
                    key, nested = pair
                    keys.append(key)
                    visit(key, depth=depth + 1)
                    visit(nested, depth=depth + 1)
                if keys != sorted(keys) or len(set(keys)) != len(keys):
                    _invalid(f"{field} frozen string map keys must be unique and ascending")
            else:
                tuple_value_storage = cast(tuple[object, ...], item)
                if len(tuple_value_storage) > _MAX_CONTAINER_ITEMS:
                    _invalid(f"{field} contains a tuple exceeding 64 items")
                for tuple_value in tuple_value_storage:
                    visit(tuple_value, depth=depth + 1)
        finally:
            active.remove(identity)

    try:
        visit(value, depth=1)
    except RecursionError as exc:
        raise VisualReferencePromptCompilerError(
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


def _validate_json_string(value: str, field: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        _invalid(f"{field} must contain only Unicode scalar values")
    if unicodedata.normalize("NFC", value) != value:
        _invalid(f"{field} must already use Unicode NFC")
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
    if any(int(item) > _SEMANTIC_VERSION_COMPONENT_MAX for item in value.split(".")):
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
    if info.mode == "json":
        if type(value) is not list:
            raise ValueError(f"{info.field_name} must be an exact JSON array")
        return tuple(value)
    return value


def _exact_enum_input(
    value: object,
    info: ValidationInfo,
    *,
    enum_type: type[object],
) -> object:
    if info.mode != "json" and type(value) is not enum_type:
        raise ValueError(f"{info.field_name} must use its exact enum type")
    return value


def _exact_enum_tuple_input(
    value: object,
    info: ValidationInfo,
    *,
    enum_type: type[object],
) -> object:
    if info.mode == "json":
        if type(value) is not list:
            raise ValueError(f"{info.field_name} must be an exact JSON array")
        return tuple(value)
    if type(value) is not tuple or any(type(item) is not enum_type for item in value):
        raise ValueError(f"{info.field_name} must use an exact tuple of exact enum values")
    return value


def _exact_discriminator_input(
    value: object,
    info: ValidationInfo,
    *,
    field_name: str,
    enum_type: type[object],
) -> object:
    if info.mode != "json" and type(value) is dict and field_name in value:
        if type(value[field_name]) is not enum_type:
            raise ValueError(f"{field_name} must use its exact enum type")
    return value


def _validate_canonical_json(value: object, field: str = "projection") -> None:
    if value is None or type(value) in {bool, int, str}:
        if type(value) is str:
            _validate_json_string(value, field)
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _validate_canonical_json(item, f"{field}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _invalid(f"{field} object keys must be exact strings")
            _validate_json_string(key, f"{field} object key")
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
        raise VisualReferencePromptCompilerError(
            "semantic projection is not canonical JSON"
        ) from exc


def _semantic_sha256(domain: bytes, projection: object) -> str:
    return hashlib.sha256(domain + _canonical_compact_json(projection)).hexdigest()


def _persistent_document_bytes(value: object) -> bytes:
    _validate_canonical_json(value, "persistent document")
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        return (text + "\n").encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError, RecursionError) as exc:
        raise VisualReferencePromptCompilerError(
            "persistent document cannot be encoded canonically"
        ) from exc


def _require_persistent_size(value: object, *, maximum: int, field: str) -> None:
    if len(_persistent_document_bytes(value)) > maximum:
        _invalid(f"{field} exceeds its persistent document byte limit")


class _DuplicateJsonKeyError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _validate_raw_tree(value: object, *, depth: int = 1) -> None:
    if value is None or type(value) in {bool, int, float, str}:
        if type(value) is float and not (-float("inf") < value < float("inf")):
            raise ValueError("non-finite JSON number is forbidden")
        if type(value) is str:
            _validate_json_string(value, "JSON string")
        return
    if type(value) is list:
        if depth > _MAX_JSON_DEPTH:
            raise ValueError("JSON container depth exceeds 16")
        if len(value) > _MAX_CONTAINER_ITEMS:
            raise ValueError("JSON array exceeds 64 items")
        for item in value:
            nested_depth = depth + 1 if type(item) in {list, dict} else depth
            _validate_raw_tree(item, depth=nested_depth)
        return
    if type(value) is dict:
        if depth > _MAX_JSON_DEPTH:
            raise ValueError("JSON container depth exceeds 16")
        if len(value) > _MAX_CONTAINER_ITEMS:
            raise ValueError("JSON object exceeds 64 fields")
        for key, item in value.items():
            _validate_json_string(key, "JSON object key")
            nested_depth = depth + 1 if type(item) in {list, dict} else depth
            _validate_raw_tree(item, depth=nested_depth)
        return
    raise ValueError("JSON contains an unsupported value")


def _raw_json_precheck(value: str | bytes | bytearray, *, maximum: int) -> bytes:
    if type(value) is str:
        try:
            raw = value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("raw JSON must be UTF-8 encodable") from exc
    elif type(value) is bytes:
        raw = value
    elif type(value) is bytearray:
        raw = bytes(value)
    else:
        raise TypeError("JSON input must be str, bytes, or bytearray")
    if len(raw) > maximum:
        raise ValueError("raw JSON exceeds its byte limit")
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError("raw JSON must contain no BOM or CR")
    try:
        text = raw.decode("utf-8", errors="strict")
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
        _validate_raw_tree(parsed)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("raw JSON failed canonical admission") from exc
    return raw


def _raw_admission_error(
    model_name: str,
    value: str | bytes | bytearray,
    error: Exception,
) -> ValidationError:
    return ValidationError.from_exception_data(
        model_name,
        [
            {
                "type": "value_error",
                "loc": (),
                "input": value,
                "ctx": {"error": error},
            }
        ],
        hide_input=True,
    )


def _validate_exact_python_input_tree(value: object) -> None:
    active: set[int] = set()

    def visit(item: object, *, depth: int) -> None:
        if type(item) in _EXACT_STORAGE_SCALAR_TYPES or type(item) is float:
            return
        if isinstance(item, (str, int, float)):
            raise ValueError("Python input scalar subclasses are forbidden")
        if isinstance(item, BaseModel):
            return
        if type(item) not in {dict, list, tuple, _FrozenStringMap}:
            if isinstance(item, (Mapping, list, tuple, set, frozenset)):
                raise ValueError("Python input container subclasses are forbidden")
            return
        if depth > _MAX_JSON_DEPTH:
            raise ValueError("Python input container depth exceeds 16")
        if len(cast(Sized, item)) > _MAX_CONTAINER_ITEMS:
            raise ValueError("Python input container exceeds 64 items")
        identity = id(item)
        if identity in active:
            raise ValueError("Python input containers must not be cyclic")
        active.add(identity)
        try:
            if type(item) is dict:
                for key, nested in cast(Mapping[object, object], item).items():
                    if type(key) is not str:
                        raise ValueError("Python input object keys must be exact strings")
                    visit(key, depth=depth + 1)
                    visit(nested, depth=depth + 1)
            elif type(item) is _FrozenStringMap:
                if type(item._items) is not tuple:
                    raise ValueError("Python input contains a malformed frozen string map")
                keys: list[str] = []
                for pair in item._items:
                    if (
                        type(pair) is not tuple
                        or len(pair) != 2
                        or type(pair[0]) is not str
                        or type(pair[1]) is not str
                    ):
                        raise ValueError(
                            "Python input contains a malformed frozen string map entry"
                        )
                    key, nested = pair
                    keys.append(key)
                    visit(key, depth=depth + 1)
                    visit(nested, depth=depth + 1)
                if keys != sorted(keys) or len(set(keys)) != len(keys):
                    raise ValueError(
                        "Python input frozen string map keys must be unique and ascending"
                    )
            else:
                for nested in cast(list[object] | tuple[object, ...], item):
                    visit(nested, depth=depth + 1)
        finally:
            active.remove(identity)

    visit(value, depth=1)


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )
    _raw_json_max_bytes: ClassVar[int | None] = None

    @model_validator(mode="before")
    @classmethod
    def validate_exact_python_inputs(cls, value: object, info: ValidationInfo) -> object:
        if info.mode != "json":
            _validate_exact_python_input_tree(value)
        return value

    @model_validator(mode="before")
    @classmethod
    def reject_forged_model_instance(cls, value: object) -> object:
        if isinstance(value, BaseModel):
            if type(value) is not cls:
                raise ValueError(f"{cls.__name__} rejects subclass model values")
            _require_exact_model_storage(value, field=cls.__name__)
        return value

    @classmethod
    def model_validate(
        cls,
        obj: object,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        from_attributes: bool | None = None,
        context: object | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        del strict, extra, from_attributes
        return super().model_validate(
            obj,
            strict=True,
            extra="forbid",
            from_attributes=False,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: object | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        del strict, extra
        if cls._raw_json_max_bytes is not None:
            try:
                json_data = _raw_json_precheck(
                    json_data,
                    maximum=cls._raw_json_max_bytes,
                )
            except (TypeError, ValueError, VisualReferencePromptCompilerError) as exc:
                raise _raw_admission_error(cls.__name__, json_data, exc) from exc
        return super().model_validate_json(
            json_data,
            strict=True,
            extra="forbid",
            context=context,
            by_alias=by_alias,
            by_name=by_name,
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


class _CharacterReferenceSourceV1(_StrictFrozenModel):
    source_kind: Literal["CHARACTER_REFERENCE_SOURCE"]
    narrative: _Text4000
    visual_direction: _Text4000
    action: _Text2000
    emotion_direction: _Text512
    wardrobe_direction: _Text512
    continuity_notes: _Text2000

    @field_validator("narrative", "visual_direction")
    @classmethod
    def validate_long_text(cls, value: str, info: ValidationInfo) -> str:
        return _validate_trimmed_text(value, field=str(info.field_name), maximum=4000)

    @field_validator("action", "continuity_notes")
    @classmethod
    def validate_direction_text(cls, value: str, info: ValidationInfo) -> str:
        return _validate_trimmed_text(value, field=str(info.field_name), maximum=2000)

    @field_validator("emotion_direction", "wardrobe_direction")
    @classmethod
    def validate_character_text(cls, value: str, info: ValidationInfo) -> str:
        return _validate_trimmed_text(value, field=str(info.field_name), maximum=512)


class _SceneReferenceSourceV1(_StrictFrozenModel):
    source_kind: Literal["SCENE_REFERENCE_SOURCE"]
    narrative: _Text4000
    visual_direction: _Text4000
    action: _Text2000
    props: _PropsV1
    continuity_notes: _Text2000

    @field_validator("props", mode="before")
    @classmethod
    def admit_json_arrays(cls, value: object, info: ValidationInfo) -> object:
        return _json_array_to_tuple(value, info)

    @field_validator("narrative", "visual_direction")
    @classmethod
    def validate_long_text(cls, value: str, info: ValidationInfo) -> str:
        return _validate_trimmed_text(value, field=str(info.field_name), maximum=4000)

    @field_validator("action", "continuity_notes")
    @classmethod
    def validate_direction_text(cls, value: str, info: ValidationInfo) -> str:
        return _validate_trimmed_text(value, field=str(info.field_name), maximum=2000)

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


_ReferenceSourceV1 = Annotated[
    _CharacterReferenceSourceV1 | _SceneReferenceSourceV1,
    Field(discriminator="source_kind"),
]


class CreativeSampleReferenceVisualPromptCompileRequestV1(_ZeroAuthorityModel):
    """One exact human-selected, human-authored, zero-authority reference request."""

    _raw_json_max_bytes = _REQUEST_MAX_BYTES

    schema_version: Literal["1.0.0"]
    request_purpose: Literal["COMPILE_OFFLINE_REFERENCE_VISUAL_PROMPT"]
    source_contract: Literal["CHARACTER_OR_SCENE_BIBLE_V1"]
    selection_scope: Literal["ONE_REFERENCE_SUBJECT"]
    asset_purpose: Literal[
        AssetPurpose.CHARACTER_REFERENCE_ASSET,
        AssetPurpose.SCENE_REFERENCE_ASSET,
    ]
    subject_id: PortableId
    expected_active_asset_version_id: PortableId
    expected_active_asset_content_sha256: LowerSha256
    reference_source: _ReferenceSourceV1
    catalog_version: SemanticVersion
    catalog_sha256: LowerSha256
    profile_id: PortableId
    profile_version: SemanticVersion
    profile_sha256: LowerSha256
    selection_decision_kind: Literal["HUMAN_DECISION"]
    selection_decision_ref: PortableId
    authoring_decision_kind: Literal["HUMAN_DECISION"]
    authoring_decision_ref: PortableId

    @field_validator("asset_purpose", mode="before")
    @classmethod
    def validate_asset_purpose_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_enum_input(value, info, enum_type=AssetPurpose)

    @field_validator("catalog_version", "profile_version")
    @classmethod
    def validate_versions(cls, value: str, info: ValidationInfo) -> str:
        return _validate_semantic_version(value, str(info.field_name))

    @model_validator(mode="after")
    def validate_request(self) -> CreativeSampleReferenceVisualPromptCompileRequestV1:
        if self.asset_purpose is AssetPurpose.CHARACTER_REFERENCE_ASSET:
            if type(self.reference_source) is not _CharacterReferenceSourceV1:
                _invalid("character request requires CHARACTER_REFERENCE_SOURCE")
        elif type(self.reference_source) is not _SceneReferenceSourceV1:
            _invalid("scene request requires SCENE_REFERENCE_SOURCE")
        _require_persistent_size(
            _request_projection(self),
            maximum=_REQUEST_MAX_BYTES,
            field="request",
        )
        return self


class _PromptConstraintSetV1(_StrictFrozenModel):
    negative_prompt_constraints: _ConstraintTextTupleV1
    positive_prompt_constraints: _ConstraintTextTupleV1
    qc_expectations: _ConstraintTextTupleV1

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
    def validate_constraints(
        cls,
        value: tuple[str, ...],
        info: ValidationInfo,
    ) -> tuple[str, ...]:
        return _validate_text_tuple(
            value,
            field=str(info.field_name),
            minimum=1,
            maximum=32,
            item_maximum=1000,
        )


class _PromptSectionV1(_StrictFrozenModel):
    heading: Annotated[str, Field(min_length=1, max_length=80)]
    placeholder: PlaceholderId
    section_id: PortableId

    @field_validator("placeholder", mode="before")
    @classmethod
    def validate_placeholder_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_enum_input(value, info, enum_type=PlaceholderId)

    @field_validator("heading")
    @classmethod
    def validate_heading(cls, value: str) -> str:
        heading = _validate_trimmed_text(value, field="heading", maximum=80)
        if any(character in heading for character in "{}:"):
            _invalid("heading must not contain braces or a colon")
        return heading


class _CharacterReferenceAssetRecipeV1(_StrictFrozenModel):
    background_requirements: _RecipeTextTupleV1
    body_proportion_anchors: _RecipeTextTupleV1
    expression_range: _RecipeTextTupleV1
    face_identity_anchors: _RecipeTextTupleV1
    forbidden_body_proportion_drift: _RecipeTextTupleV1
    forbidden_hairstyle_drift: _RecipeTextTupleV1
    forbidden_identity_drift: _RecipeTextTupleV1
    forbidden_wardrobe_drift: _RecipeTextTupleV1
    hairstyle_anchors: _RecipeTextTupleV1
    recipe_kind: Literal[ReferenceAssetRecipeKind.CHARACTER_REFERENCE]
    reference_asset_types: _CharacterReferenceAssetTypesV1
    required_primary_binding_fields: _CharacterPrimaryBindingFieldsV1
    sheet_layout_requirements: _RecipeTextTupleV1
    wardrobe_anchors: _RecipeTextTupleV1

    @field_validator(
        "background_requirements",
        "body_proportion_anchors",
        "expression_range",
        "face_identity_anchors",
        "forbidden_body_proportion_drift",
        "forbidden_hairstyle_drift",
        "forbidden_identity_drift",
        "forbidden_wardrobe_drift",
        "hairstyle_anchors",
        "required_primary_binding_fields",
        "sheet_layout_requirements",
        "wardrobe_anchors",
        mode="before",
    )
    @classmethod
    def admit_json_arrays(cls, value: object, info: ValidationInfo) -> object:
        return _json_array_to_tuple(value, info)

    @field_validator("reference_asset_types", mode="before")
    @classmethod
    def validate_reference_asset_types(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _exact_enum_tuple_input(value, info, enum_type=ReferenceAssetType)

    @field_validator("recipe_kind", mode="before")
    @classmethod
    def validate_recipe_kind_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_enum_input(value, info, enum_type=ReferenceAssetRecipeKind)

    @field_validator(
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
    )
    @classmethod
    def validate_recipe_text(
        cls,
        value: tuple[str, ...],
        info: ValidationInfo,
    ) -> tuple[str, ...]:
        return _validate_text_tuple(
            value,
            field=str(info.field_name),
            minimum=1,
            maximum=16,
            item_maximum=1000,
        )

    @model_validator(mode="after")
    def validate_recipe(self) -> _CharacterReferenceAssetRecipeV1:
        if self.reference_asset_types != _CHARACTER_REFERENCE_ASSET_TYPES:
            _invalid("character recipe requires the exact complete three-role tuple")
        if self.required_primary_binding_fields != _CHARACTER_PRIMARY_BINDING_FIELDS:
            _invalid("character recipe requires the frozen primary binding fields")
        return self


class _SceneReferenceAssetRecipeV1(_StrictFrozenModel):
    continuity_requirements: _RecipeTextTupleV1
    forbidden_drift: _RecipeTextTupleV1
    geography_anchors: _RecipeTextTupleV1
    layout_requirements: _RecipeTextTupleV1
    lighting_anchors: _RecipeTextTupleV1
    material_anchors: _RecipeTextTupleV1
    palette_anchors: _RecipeTextTupleV1
    prop_placement_anchors: _RecipeTextTupleV1
    recipe_kind: Literal[ReferenceAssetRecipeKind.SCENE_REFERENCE]
    reference_asset_types: _SceneReferenceAssetTypesV1
    required_primary_binding_fields: _ScenePrimaryBindingFieldsV1

    @field_validator(
        "continuity_requirements",
        "forbidden_drift",
        "geography_anchors",
        "layout_requirements",
        "lighting_anchors",
        "material_anchors",
        "palette_anchors",
        "prop_placement_anchors",
        "required_primary_binding_fields",
        mode="before",
    )
    @classmethod
    def admit_json_arrays(cls, value: object, info: ValidationInfo) -> object:
        return _json_array_to_tuple(value, info)

    @field_validator("reference_asset_types", mode="before")
    @classmethod
    def validate_reference_asset_types(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _exact_enum_tuple_input(value, info, enum_type=ReferenceAssetType)

    @field_validator("recipe_kind", mode="before")
    @classmethod
    def validate_recipe_kind_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_enum_input(value, info, enum_type=ReferenceAssetRecipeKind)

    @field_validator(
        "continuity_requirements",
        "forbidden_drift",
        "geography_anchors",
        "layout_requirements",
        "lighting_anchors",
        "material_anchors",
        "palette_anchors",
        "prop_placement_anchors",
    )
    @classmethod
    def validate_recipe_text(
        cls,
        value: tuple[str, ...],
        info: ValidationInfo,
    ) -> tuple[str, ...]:
        return _validate_text_tuple(
            value,
            field=str(info.field_name),
            minimum=1,
            maximum=16,
            item_maximum=1000,
        )

    @model_validator(mode="after")
    def validate_recipe(self) -> _SceneReferenceAssetRecipeV1:
        if self.reference_asset_types != _SCENE_REFERENCE_ASSET_TYPES:
            _invalid("scene recipe requires the exact complete four-role tuple")
        if self.required_primary_binding_fields != _SCENE_PRIMARY_BINDING_FIELDS:
            _invalid("scene recipe requires the frozen primary binding fields")
        return self


class _ReferenceVisualPromptProfileSnapshotBaseV1(_StrictFrozenModel):
    constraint_set: _PromptConstraintSetV1
    narrative_contexts: _NarrativeContextsV1
    profile_id: PortableId
    profile_version: SemanticVersion
    renderer_version: Literal["1.0.0"]
    sections: Annotated[
        tuple[_PromptSectionV1, ...],
        Field(min_length=1, max_length=16, json_schema_extra={"uniqueItems": True}),
    ]
    shot_type: Literal[ShotType.REFERENCE_SHEET]
    visual_style_id: Literal[VisualStyleId.CINEMATIC_STORYBOARD_V1]
    profile_sha256: LowerSha256
    catalog_version: SemanticVersion
    catalog_sha256: LowerSha256

    @field_validator("sections", mode="before")
    @classmethod
    def admit_json_arrays(cls, value: object, info: ValidationInfo) -> object:
        return _json_array_to_tuple(value, info)

    @field_validator("narrative_contexts", mode="before")
    @classmethod
    def validate_narrative_contexts(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        return _exact_enum_tuple_input(value, info, enum_type=NarrativeContext)

    @field_validator("shot_type", mode="before")
    @classmethod
    def validate_shot_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_enum_input(value, info, enum_type=ShotType)

    @field_validator("visual_style_id", mode="before")
    @classmethod
    def validate_visual_style_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_enum_input(value, info, enum_type=VisualStyleId)

    @field_validator("profile_version", "catalog_version")
    @classmethod
    def validate_versions(cls, value: str, info: ValidationInfo) -> str:
        return _validate_semantic_version(value, str(info.field_name))

    def _validate_common_snapshot(
        self,
        *,
        placeholders: frozenset[PlaceholderId],
    ) -> None:
        contexts = self.narrative_contexts
        order = {item: index for index, item in enumerate(NarrativeContext)}
        ranks = tuple(order[item] for item in contexts)
        if (
            not 1 <= len(contexts) <= len(NarrativeContext)
            or len(set(contexts)) != len(contexts)
            or ranks != tuple(sorted(ranks))
            or NarrativeContext.REFERENCE_DEVELOPMENT not in contexts
        ):
            _invalid(
                "reference narrative_contexts must be unique, canonical, and include "
                "REFERENCE_DEVELOPMENT"
            )
        if not 1 <= len(self.sections) <= 16:
            _invalid("sections must contain 1..16 items")
        if len({item.section_id for item in self.sections}) != len(self.sections):
            _invalid("section_id values must be unique")
        if len({item.heading for item in self.sections}) != len(self.sections):
            _invalid("section headings must be unique")
        actual_placeholders = tuple(item.placeholder for item in self.sections)
        if (
            len(set(actual_placeholders)) != len(actual_placeholders)
            or frozenset(actual_placeholders) != placeholders
        ):
            _invalid("sections must contain the exact reference placeholder set")


class _CharacterVisualPromptProfileSnapshotV1(_ReferenceVisualPromptProfileSnapshotBaseV1):
    asset_purpose: Literal[AssetPurpose.CHARACTER_REFERENCE_ASSET]
    reference_asset_recipe: _CharacterReferenceAssetRecipeV1
    reference_asset_types: _CharacterReferenceAssetTypesV1

    @field_validator("reference_asset_types", mode="before")
    @classmethod
    def admit_reference_types(cls, value: object, info: ValidationInfo) -> object:
        return _exact_enum_tuple_input(value, info, enum_type=ReferenceAssetType)

    @model_validator(mode="before")
    @classmethod
    def validate_asset_purpose_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_discriminator_input(
            value,
            info,
            field_name="asset_purpose",
            enum_type=AssetPurpose,
        )

    @model_validator(mode="after")
    def validate_snapshot(self) -> _CharacterVisualPromptProfileSnapshotV1:
        self._validate_common_snapshot(placeholders=_CHARACTER_REFERENCE_PLACEHOLDERS)
        if (
            self.reference_asset_types != _CHARACTER_REFERENCE_ASSET_TYPES
            or self.reference_asset_recipe.reference_asset_types != self.reference_asset_types
        ):
            _invalid("character Snapshot requires the exact complete three-role tuple")
        if self.profile_sha256 != _semantic_sha256(
            PROFILE_SHA256_DOMAIN,
            _snapshot_profile_projection(self),
        ):
            _invalid("profile_sha256 does not bind the exact character Profile semantics")
        return self


class _SceneVisualPromptProfileSnapshotV1(_ReferenceVisualPromptProfileSnapshotBaseV1):
    asset_purpose: Literal[AssetPurpose.SCENE_REFERENCE_ASSET]
    reference_asset_recipe: _SceneReferenceAssetRecipeV1
    reference_asset_types: _SceneReferenceAssetTypesV1

    @field_validator("reference_asset_types", mode="before")
    @classmethod
    def admit_reference_types(cls, value: object, info: ValidationInfo) -> object:
        return _exact_enum_tuple_input(value, info, enum_type=ReferenceAssetType)

    @model_validator(mode="before")
    @classmethod
    def validate_asset_purpose_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_discriminator_input(
            value,
            info,
            field_name="asset_purpose",
            enum_type=AssetPurpose,
        )

    @model_validator(mode="after")
    def validate_snapshot(self) -> _SceneVisualPromptProfileSnapshotV1:
        self._validate_common_snapshot(placeholders=_SCENE_REFERENCE_PLACEHOLDERS)
        if (
            self.reference_asset_types != _SCENE_REFERENCE_ASSET_TYPES
            or self.reference_asset_recipe.reference_asset_types != self.reference_asset_types
        ):
            _invalid("scene Snapshot requires the exact complete four-role tuple")
        if self.profile_sha256 != _semantic_sha256(
            PROFILE_SHA256_DOMAIN,
            _snapshot_profile_projection(self),
        ):
            _invalid("profile_sha256 does not bind the exact scene Profile semantics")
        return self


_ReferenceVisualPromptProfileSnapshotV1 = Annotated[
    _CharacterVisualPromptProfileSnapshotV1 | _SceneVisualPromptProfileSnapshotV1,
    Field(discriminator="asset_purpose"),
]


class _CharacterAssetPromptBindingV1(_StrictFrozenModel):
    asset_content_sha256: LowerSha256
    asset_version_id: PortableId
    character_id: PortableId


class _SceneAssetPromptBindingV1(_StrictFrozenModel):
    asset_content_sha256: LowerSha256
    asset_version_id: PortableId
    scene_id: PortableId


class _CharacterReferencePromptRenderInputV1(_StrictFrozenModel):
    action: _Text2000
    character_asset_bindings: tuple[_CharacterAssetPromptBindingV1]
    continuity_notes: _Text2000
    emotion_by_character: Annotated[
        Mapping[PortableId, _Text512],
        Field(
            min_length=1,
            max_length=1,
            json_schema_extra={"additionalProperties": False},
        ),
    ]
    input_kind: Literal[AssetPurpose.CHARACTER_REFERENCE_ASSET]
    narrative: _Text4000
    visual_direction: _Text4000
    wardrobe_by_character: Annotated[
        Mapping[PortableId, _Text512],
        Field(
            min_length=1,
            max_length=1,
            json_schema_extra={"additionalProperties": False},
        ),
    ]

    @model_validator(mode="before")
    @classmethod
    def validate_input_kind_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_discriminator_input(
            value,
            info,
            field_name="input_kind",
            enum_type=AssetPurpose,
        )

    @field_validator("character_asset_bindings", mode="before")
    @classmethod
    def admit_json_arrays(cls, value: object, info: ValidationInfo) -> object:
        return _json_array_to_tuple(value, info)

    @field_validator("narrative", "visual_direction")
    @classmethod
    def validate_long_text(cls, value: str, info: ValidationInfo) -> str:
        return _validate_trimmed_text(value, field=str(info.field_name), maximum=4000)

    @field_validator("action", "continuity_notes")
    @classmethod
    def validate_direction_text(cls, value: str, info: ValidationInfo) -> str:
        return _validate_trimmed_text(value, field=str(info.field_name), maximum=2000)

    @field_validator("emotion_by_character", "wardrobe_by_character")
    @classmethod
    def validate_character_text_map(
        cls,
        value: Mapping[str, str],
        info: ValidationInfo,
    ) -> Mapping[str, str]:
        field_name = str(info.field_name)
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
        return _FrozenStringMap(tuple(result.items()))

    @field_serializer("emotion_by_character", "wardrobe_by_character")
    def serialize_character_text_map(self, value: Mapping[str, str]) -> dict[str, str]:
        return dict(value)

    @model_validator(mode="after")
    def validate_input(self) -> _CharacterReferencePromptRenderInputV1:
        if len(self.character_asset_bindings) != 1:
            _invalid("character reference input requires exactly one asset binding")
        character_id = self.character_asset_bindings[0].character_id
        if tuple(self.emotion_by_character) != (character_id,):
            _invalid("emotion_by_character must contain exactly the bound character")
        if tuple(self.wardrobe_by_character) != (character_id,):
            _invalid("wardrobe_by_character must contain exactly the bound character")
        return self


class _SceneReferencePromptRenderInputV1(_StrictFrozenModel):
    action: _Text2000
    continuity_notes: _Text2000
    input_kind: Literal[AssetPurpose.SCENE_REFERENCE_ASSET]
    narrative: _Text4000
    props: _PropsV1
    scene_asset_binding: _SceneAssetPromptBindingV1
    visual_direction: _Text4000

    @model_validator(mode="before")
    @classmethod
    def validate_input_kind_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_discriminator_input(
            value,
            info,
            field_name="input_kind",
            enum_type=AssetPurpose,
        )

    @field_validator("props", mode="before")
    @classmethod
    def admit_json_arrays(cls, value: object, info: ValidationInfo) -> object:
        return _json_array_to_tuple(value, info)

    @field_validator("narrative", "visual_direction")
    @classmethod
    def validate_long_text(cls, value: str, info: ValidationInfo) -> str:
        return _validate_trimmed_text(value, field=str(info.field_name), maximum=4000)

    @field_validator("action", "continuity_notes")
    @classmethod
    def validate_direction_text(cls, value: str, info: ValidationInfo) -> str:
        return _validate_trimmed_text(value, field=str(info.field_name), maximum=2000)

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


_ReferencePromptRenderInputV1 = Annotated[
    _CharacterReferencePromptRenderInputV1 | _SceneReferencePromptRenderInputV1,
    Field(discriminator="input_kind"),
]


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
    prompt_size_bytes: Annotated[int, Field(ge=1, le=_PROMPT_MAX_BYTES)]
    prompt_render_receipt_sha256: LowerSha256

    @field_validator("profile_version", "catalog_version")
    @classmethod
    def validate_versions(cls, value: str, info: ValidationInfo) -> str:
        return _validate_semantic_version(value, str(info.field_name))

    @model_validator(mode="after")
    def validate_receipt_digest(self) -> _PromptRenderReceiptV1:
        expected = _semantic_sha256(
            PROMPT_RENDER_RECEIPT_SHA256_DOMAIN,
            _prompt_render_receipt_projection(self),
        )
        if self.prompt_render_receipt_sha256 != expected:
            _invalid("prompt_render_receipt_sha256 does not bind the exact Receipt")
        return self


class CreativeSampleReferenceVisualPromptArtifactV1(_ZeroAuthorityModel):
    """Immutable offline reference Prompt and zero-authority process evidence."""

    _raw_json_max_bytes = _ARTIFACT_MAX_BYTES

    schema_version: Literal["1.0.0"]
    artifact_purpose: Literal["OFFLINE_REFERENCE_VISUAL_PROMPT_ARTIFACT"]
    source_contract: Literal["CHARACTER_OR_SCENE_BIBLE_V1"]
    selection_scope: Literal["ONE_REFERENCE_SUBJECT"]
    asset_purpose: Literal[
        AssetPurpose.CHARACTER_REFERENCE_ASSET,
        AssetPurpose.SCENE_REFERENCE_ASSET,
    ]
    subject_id: PortableId
    expected_active_asset_version_id: PortableId
    expected_active_asset_content_sha256: LowerSha256
    reference_source: _ReferenceSourceV1
    selection_decision_kind: Literal["HUMAN_DECISION"]
    selection_decision_ref: PortableId
    authoring_decision_kind: Literal["HUMAN_DECISION"]
    authoring_decision_ref: PortableId
    profile_snapshot: _ReferenceVisualPromptProfileSnapshotV1
    render_input: _ReferencePromptRenderInputV1
    render_input_sha256: LowerSha256
    prompt: _PromptText
    prompt_sha256: LowerSha256
    prompt_size_bytes: Annotated[int, Field(ge=1, le=_PROMPT_MAX_BYTES)]
    prompt_render_receipt: _PromptRenderReceiptV1
    artifact_sha256: LowerSha256

    @field_validator("asset_purpose", mode="before")
    @classmethod
    def validate_asset_purpose_type(cls, value: object, info: ValidationInfo) -> object:
        return _exact_enum_input(value, info, enum_type=AssetPurpose)

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
    def validate_artifact(self) -> CreativeSampleReferenceVisualPromptArtifactV1:
        _validate_artifact_closure(self)
        expected = _semantic_sha256(
            VISUAL_REFERENCE_PROMPT_COMPILER_ARTIFACT_SHA256_DOMAIN,
            _artifact_projection_unchecked(self),
        )
        if self.artifact_sha256 != expected:
            _invalid("artifact_sha256 does not bind the exact Artifact projection")
        _require_persistent_size(
            _artifact_document_projection(self),
            maximum=_ARTIFACT_MAX_BYTES,
            field="Artifact",
        )
        return self


def _exact_storage_model_types() -> frozenset[type[BaseModel]]:
    return frozenset(
        {
            CharacterAssetVersion,
            CharacterBible,
            SceneAssetVersion,
            SceneBible,
            _CharacterReferenceSourceV1,
            _SceneReferenceSourceV1,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            _PromptConstraintSetV1,
            _PromptSectionV1,
            _CharacterReferenceAssetRecipeV1,
            _SceneReferenceAssetRecipeV1,
            _CharacterVisualPromptProfileSnapshotV1,
            _SceneVisualPromptProfileSnapshotV1,
            _CharacterAssetPromptBindingV1,
            _SceneAssetPromptBindingV1,
            _CharacterReferencePromptRenderInputV1,
            _SceneReferencePromptRenderInputV1,
            _PromptRenderReceiptV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        }
    )


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


def _character_recipe_projection(
    value: _CharacterReferenceAssetRecipeV1,
) -> dict[str, object]:
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


def _scene_recipe_projection(
    value: _SceneReferenceAssetRecipeV1,
) -> dict[str, object]:
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


def _snapshot_profile_projection(
    value: _CharacterVisualPromptProfileSnapshotV1 | _SceneVisualPromptProfileSnapshotV1,
) -> dict[str, object]:
    if type(value) is _CharacterVisualPromptProfileSnapshotV1:
        recipe = _character_recipe_projection(value.reference_asset_recipe)
    elif type(value) is _SceneVisualPromptProfileSnapshotV1:
        recipe = _scene_recipe_projection(value.reference_asset_recipe)
    else:
        _invalid("Snapshot must use one exact reference variant")
    return {
        "asset_purpose": value.asset_purpose.value,
        "constraint_set": _constraint_set_projection(value.constraint_set),
        "narrative_contexts": [item.value for item in value.narrative_contexts],
        "profile_id": value.profile_id,
        "profile_version": value.profile_version,
        "reference_asset_recipe": recipe,
        "reference_asset_types": [item.value for item in value.reference_asset_types],
        "renderer_version": value.renderer_version,
        "sections": [_prompt_section_projection(item) for item in value.sections],
        "shot_type": value.shot_type.value,
        "visual_style_id": value.visual_style_id.value,
    }


def _snapshot_projection(
    value: _CharacterVisualPromptProfileSnapshotV1 | _SceneVisualPromptProfileSnapshotV1,
) -> dict[str, object]:
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


def _character_binding_projection(
    value: _CharacterAssetPromptBindingV1,
) -> dict[str, object]:
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


def _render_input_projection(
    value: _CharacterReferencePromptRenderInputV1 | _SceneReferencePromptRenderInputV1,
) -> dict[str, object]:
    if type(value) is _CharacterReferencePromptRenderInputV1:
        return {
            "action": value.action,
            "character_asset_bindings": [
                _character_binding_projection(item) for item in value.character_asset_bindings
            ],
            "continuity_notes": value.continuity_notes,
            "emotion_by_character": dict(value.emotion_by_character),
            "input_kind": value.input_kind.value,
            "narrative": value.narrative,
            "visual_direction": value.visual_direction,
            "wardrobe_by_character": dict(value.wardrobe_by_character),
        }
    if type(value) is _SceneReferencePromptRenderInputV1:
        return {
            "action": value.action,
            "continuity_notes": value.continuity_notes,
            "input_kind": value.input_kind.value,
            "narrative": value.narrative,
            "props": list(value.props),
            "scene_asset_binding": _scene_binding_projection(value.scene_asset_binding),
            "visual_direction": value.visual_direction,
        }
    _invalid("render input must use one exact reference variant")


def _reference_source_projection(
    value: _CharacterReferenceSourceV1 | _SceneReferenceSourceV1,
) -> dict[str, object]:
    if type(value) is _CharacterReferenceSourceV1:
        return {
            "source_kind": value.source_kind,
            "narrative": value.narrative,
            "visual_direction": value.visual_direction,
            "action": value.action,
            "emotion_direction": value.emotion_direction,
            "wardrobe_direction": value.wardrobe_direction,
            "continuity_notes": value.continuity_notes,
        }
    if type(value) is _SceneReferenceSourceV1:
        return {
            "source_kind": value.source_kind,
            "narrative": value.narrative,
            "visual_direction": value.visual_direction,
            "action": value.action,
            "props": list(value.props),
            "continuity_notes": value.continuity_notes,
        }
    _invalid("reference_source must use one exact tagged-union member")


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


def _zero_authority_projection(value: _ZeroAuthorityModel) -> dict[str, object]:
    return {
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


def _request_projection(
    value: CreativeSampleReferenceVisualPromptCompileRequestV1,
) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "request_purpose": value.request_purpose,
        "source_contract": value.source_contract,
        "selection_scope": value.selection_scope,
        "asset_purpose": value.asset_purpose.value,
        "subject_id": value.subject_id,
        "expected_active_asset_version_id": value.expected_active_asset_version_id,
        "expected_active_asset_content_sha256": (value.expected_active_asset_content_sha256),
        "reference_source": _reference_source_projection(value.reference_source),
        "catalog_version": value.catalog_version,
        "catalog_sha256": value.catalog_sha256,
        "profile_id": value.profile_id,
        "profile_version": value.profile_version,
        "profile_sha256": value.profile_sha256,
        "selection_decision_kind": value.selection_decision_kind,
        "selection_decision_ref": value.selection_decision_ref,
        "authoring_decision_kind": value.authoring_decision_kind,
        "authoring_decision_ref": value.authoring_decision_ref,
        **_zero_authority_projection(value),
    }


def _artifact_projection_unchecked(
    value: CreativeSampleReferenceVisualPromptArtifactV1,
) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "artifact_purpose": value.artifact_purpose,
        "source_contract": value.source_contract,
        "selection_scope": value.selection_scope,
        "asset_purpose": value.asset_purpose.value,
        "subject_id": value.subject_id,
        "expected_active_asset_version_id": value.expected_active_asset_version_id,
        "expected_active_asset_content_sha256": (value.expected_active_asset_content_sha256),
        "reference_source": _reference_source_projection(value.reference_source),
        "selection_decision_kind": value.selection_decision_kind,
        "selection_decision_ref": value.selection_decision_ref,
        "authoring_decision_kind": value.authoring_decision_kind,
        "authoring_decision_ref": value.authoring_decision_ref,
        "profile_snapshot": _snapshot_projection(value.profile_snapshot),
        "render_input": _render_input_projection(value.render_input),
        "render_input_sha256": value.render_input_sha256,
        "prompt": value.prompt,
        "prompt_sha256": value.prompt_sha256,
        "prompt_size_bytes": value.prompt_size_bytes,
        "prompt_render_receipt": _prompt_render_receipt_document_projection(
            value.prompt_render_receipt
        ),
        **_zero_authority_projection(value),
    }


def _artifact_document_projection(
    value: CreativeSampleReferenceVisualPromptArtifactV1,
) -> dict[str, object]:
    return {**_artifact_projection_unchecked(value), "artifact_sha256": value.artifact_sha256}


def _recipe_lines(
    recipe: _CharacterReferenceAssetRecipeV1 | _SceneReferenceAssetRecipeV1,
) -> tuple[str, ...]:
    if type(recipe) is _CharacterReferenceAssetRecipeV1:
        values: tuple[tuple[str, object], ...] = (
            ("Recipe kind", recipe.recipe_kind.value),
            (
                "Reference asset types",
                [item.value for item in recipe.reference_asset_types],
            ),
            ("Face identity anchors", list(recipe.face_identity_anchors)),
            ("Hairstyle anchors", list(recipe.hairstyle_anchors)),
            ("Wardrobe anchors", list(recipe.wardrobe_anchors)),
            ("Body proportion anchors", list(recipe.body_proportion_anchors)),
            ("Expression range", list(recipe.expression_range)),
            ("Forbidden identity drift", list(recipe.forbidden_identity_drift)),
            ("Forbidden hairstyle drift", list(recipe.forbidden_hairstyle_drift)),
            ("Forbidden wardrobe drift", list(recipe.forbidden_wardrobe_drift)),
            (
                "Forbidden body proportion drift",
                list(recipe.forbidden_body_proportion_drift),
            ),
            ("Sheet layout requirements", list(recipe.sheet_layout_requirements)),
            ("Background requirements", list(recipe.background_requirements)),
            (
                "Required primary binding fields",
                list(recipe.required_primary_binding_fields),
            ),
        )
    elif type(recipe) is _SceneReferenceAssetRecipeV1:
        values = (
            ("Recipe kind", recipe.recipe_kind.value),
            (
                "Reference asset types",
                [item.value for item in recipe.reference_asset_types],
            ),
            ("Layout requirements", list(recipe.layout_requirements)),
            ("Geography anchors", list(recipe.geography_anchors)),
            ("Lighting anchors", list(recipe.lighting_anchors)),
            ("Palette anchors", list(recipe.palette_anchors)),
            ("Material anchors", list(recipe.material_anchors)),
            ("Prop placement anchors", list(recipe.prop_placement_anchors)),
            ("Continuity requirements", list(recipe.continuity_requirements)),
            ("Forbidden drift", list(recipe.forbidden_drift)),
            (
                "Required primary binding fields",
                list(recipe.required_primary_binding_fields),
            ),
        )
    else:
        _invalid("reference recipe must use one exact tagged-union member")
    return tuple(
        f"{label}: {raw if type(raw) is str else _canonical_compact_json(raw).decode('utf-8')}"
        for label, raw in values
    )


def _render_formal_prompt_bytes(
    snapshot: _CharacterVisualPromptProfileSnapshotV1 | _SceneVisualPromptProfileSnapshotV1,
    render_input: _CharacterReferencePromptRenderInputV1 | _SceneReferencePromptRenderInputV1,
) -> bytes:
    if snapshot.asset_purpose is not render_input.input_kind:
        _invalid("formal Snapshot purpose must equal formal render-input kind")
    input_projection = _render_input_projection(render_input)
    lines: list[str] = []
    for section in snapshot.sections:
        if section.placeholder.value not in input_projection:
            _invalid("Snapshot section has no exact render-input source")
        rendered = input_projection[section.placeholder.value]
        text = (
            rendered if type(rendered) is str else _canonical_compact_json(rendered).decode("utf-8")
        )
        lines.append(f"{section.heading}: {text}")
    lines.append("Positive Prompt Constraints:")
    lines.extend(f"- {item}" for item in snapshot.constraint_set.positive_prompt_constraints)
    lines.append("Negative Prompt Constraints:")
    lines.extend(f"- {item}" for item in snapshot.constraint_set.negative_prompt_constraints)
    lines.append("Reference Asset Recipe:")
    lines.extend(_recipe_lines(snapshot.reference_asset_recipe))
    prompt = "\n".join(lines) + "\n"
    raw = prompt.encode("utf-8")
    if not 1 <= len(raw) <= _PROMPT_MAX_BYTES:
        _invalid("locally re-rendered Prompt exceeds the frozen byte limit")
    return raw


def _expected_receipt_projection(
    *,
    snapshot: _CharacterVisualPromptProfileSnapshotV1 | _SceneVisualPromptProfileSnapshotV1,
    render_input_sha256: str,
    prompt_sha256: str,
    prompt_size_bytes: int,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "receipt_purpose": "DETERMINISTIC_PROMPT_RENDER_PROCESS_EVIDENCE_ONLY",
        "profile_id": snapshot.profile_id,
        "profile_version": snapshot.profile_version,
        "profile_sha256": snapshot.profile_sha256,
        "catalog_version": snapshot.catalog_version,
        "catalog_sha256": snapshot.catalog_sha256,
        "render_input_sha256": render_input_sha256,
        "renderer_id": "sdc.visual-prompt-renderer",
        "renderer_version": _RENDERER_VERSION,
        "prompt_sha256": prompt_sha256,
        "prompt_size_bytes": prompt_size_bytes,
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
        "usage_restriction": _USAGE_RESTRICTION,
        "grants_rights": False,
        "grants_qualification": False,
        "grants_execution_authority": False,
        "eligible_for_asset_promotion": False,
        "replaces_rights_manifest": False,
    }
    return {
        **payload,
        "prompt_render_receipt_sha256": _semantic_sha256(
            PROMPT_RENDER_RECEIPT_SHA256_DOMAIN,
            payload,
        ),
    }


def _validate_artifact_closure(
    value: CreativeSampleReferenceVisualPromptArtifactV1,
) -> None:
    snapshot = value.profile_snapshot
    render_input = value.render_input
    source = value.reference_source

    if value.asset_purpose is AssetPurpose.CHARACTER_REFERENCE_ASSET:
        if (
            type(source) is not _CharacterReferenceSourceV1
            or type(snapshot) is not _CharacterVisualPromptProfileSnapshotV1
            or type(render_input) is not _CharacterReferencePromptRenderInputV1
        ):
            _invalid("character Artifact requires exact parallel character variants")
        character_binding = render_input.character_asset_bindings[0]
        if (
            character_binding.character_id != value.subject_id
            or character_binding.asset_version_id != value.expected_active_asset_version_id
            or character_binding.asset_content_sha256 != value.expected_active_asset_content_sha256
        ):
            _invalid("character Artifact binding does not match the expected subject binding")
        if (
            source.narrative != render_input.narrative
            or source.visual_direction != render_input.visual_direction
            or source.action != render_input.action
            or source.continuity_notes != render_input.continuity_notes
            or dict(render_input.emotion_by_character)
            != {value.subject_id: source.emotion_direction}
            or dict(render_input.wardrobe_by_character)
            != {value.subject_id: source.wardrobe_direction}
        ):
            _invalid("character source does not map exactly to the embedded render input")
    elif value.asset_purpose is AssetPurpose.SCENE_REFERENCE_ASSET:
        if (
            type(source) is not _SceneReferenceSourceV1
            or type(snapshot) is not _SceneVisualPromptProfileSnapshotV1
            or type(render_input) is not _SceneReferencePromptRenderInputV1
        ):
            _invalid("scene Artifact requires exact parallel scene variants")
        scene_binding = render_input.scene_asset_binding
        if (
            scene_binding.scene_id != value.subject_id
            or scene_binding.asset_version_id != value.expected_active_asset_version_id
            or scene_binding.asset_content_sha256 != value.expected_active_asset_content_sha256
        ):
            _invalid("scene Artifact binding does not match the expected subject binding")
        if (
            source.narrative != render_input.narrative
            or source.visual_direction != render_input.visual_direction
            or source.action != render_input.action
            or source.props != render_input.props
            or source.continuity_notes != render_input.continuity_notes
        ):
            _invalid("scene source does not map exactly to the embedded render input")
    else:
        _invalid("Artifact asset_purpose is outside the reference boundary")

    if snapshot.asset_purpose is not value.asset_purpose:
        _invalid("Artifact Snapshot purpose differs from asset_purpose")
    input_digest = _semantic_sha256(
        RENDER_INPUT_SHA256_DOMAIN,
        _render_input_projection(render_input),
    )
    if value.render_input_sha256 != input_digest:
        _invalid("render_input_sha256 does not bind the exact render input")

    expected_prompt = _render_formal_prompt_bytes(snapshot, render_input)
    if value.prompt.encode("utf-8") != expected_prompt:
        _invalid("Prompt is not the exact local renderer result")
    prompt_sha256 = hashlib.sha256(expected_prompt).hexdigest()
    if value.prompt_sha256 != prompt_sha256:
        _invalid("prompt_sha256 does not bind the exact Prompt bytes")
    if value.prompt_size_bytes != len(expected_prompt):
        _invalid("prompt_size_bytes does not equal the exact Prompt byte length")
    expected_receipt = _expected_receipt_projection(
        snapshot=snapshot,
        render_input_sha256=input_digest,
        prompt_sha256=prompt_sha256,
        prompt_size_bytes=len(expected_prompt),
    )
    if _prompt_render_receipt_document_projection(value.prompt_render_receipt) != (
        expected_receipt
    ):
        _invalid("Prompt Receipt is not the exact local renderer process evidence")


def _revalidate_artifact(
    value: CreativeSampleReferenceVisualPromptArtifactV1,
) -> CreativeSampleReferenceVisualPromptArtifactV1:
    try:
        if type(value) is not CreativeSampleReferenceVisualPromptArtifactV1:
            raise TypeError("value must be an exact CreativeSampleReferenceVisualPromptArtifactV1")
        _require_exact_model_storage(value, field="Artifact")
        return CreativeSampleReferenceVisualPromptArtifactV1.model_validate(
            value.model_dump(mode="python"),
        )
    except (
        ValidationError,
        TypeError,
        ValueError,
        RecursionError,
        UnicodeError,
    ) as exc:
        raise VisualReferencePromptCompilerError(
            "Artifact failed complete strict integrity revalidation"
        ) from exc


def creative_sample_reference_visual_prompt_artifact_projection(
    value: CreativeSampleReferenceVisualPromptArtifactV1,
) -> dict[str, object]:
    """Strictly revalidate and project every Artifact field except its self digest."""

    try:
        validated = _revalidate_artifact(value)
        return _artifact_projection_unchecked(validated)
    except VisualReferencePromptCompilerError as exc:
        raise VisualReferencePromptCompilerError(
            "Artifact projection rejected the supplied value"
        ) from exc


def creative_sample_reference_visual_prompt_artifact_sha256(
    value: CreativeSampleReferenceVisualPromptArtifactV1,
) -> str:
    """Strictly revalidate and return the ADR-042 domain-separated Artifact identity."""

    try:
        validated = _revalidate_artifact(value)
        return _semantic_sha256(
            VISUAL_REFERENCE_PROMPT_COMPILER_ARTIFACT_SHA256_DOMAIN,
            _artifact_projection_unchecked(validated),
        )
    except VisualReferencePromptCompilerError as exc:
        raise VisualReferencePromptCompilerError(
            "Artifact identity rejected the supplied value"
        ) from exc


def _character_recipe_contract(
    value: CharacterReferenceAssetRecipe,
) -> _CharacterReferenceAssetRecipeV1:
    return _CharacterReferenceAssetRecipeV1(
        background_requirements=value.background_requirements,
        body_proportion_anchors=value.body_proportion_anchors,
        expression_range=value.expression_range,
        face_identity_anchors=value.face_identity_anchors,
        forbidden_body_proportion_drift=value.forbidden_body_proportion_drift,
        forbidden_hairstyle_drift=value.forbidden_hairstyle_drift,
        forbidden_identity_drift=value.forbidden_identity_drift,
        forbidden_wardrobe_drift=value.forbidden_wardrobe_drift,
        hairstyle_anchors=value.hairstyle_anchors,
        recipe_kind=ReferenceAssetRecipeKind.CHARACTER_REFERENCE,
        reference_asset_types=cast(
            _CharacterReferenceAssetTypesV1,
            value.reference_asset_types,
        ),
        required_primary_binding_fields=cast(
            _CharacterPrimaryBindingFieldsV1,
            value.required_primary_binding_fields,
        ),
        sheet_layout_requirements=value.sheet_layout_requirements,
        wardrobe_anchors=value.wardrobe_anchors,
    )


def _scene_recipe_contract(
    value: SceneReferenceAssetRecipe,
) -> _SceneReferenceAssetRecipeV1:
    return _SceneReferenceAssetRecipeV1(
        continuity_requirements=value.continuity_requirements,
        forbidden_drift=value.forbidden_drift,
        geography_anchors=value.geography_anchors,
        layout_requirements=value.layout_requirements,
        lighting_anchors=value.lighting_anchors,
        material_anchors=value.material_anchors,
        palette_anchors=value.palette_anchors,
        prop_placement_anchors=value.prop_placement_anchors,
        recipe_kind=ReferenceAssetRecipeKind.SCENE_REFERENCE,
        reference_asset_types=cast(
            _SceneReferenceAssetTypesV1,
            value.reference_asset_types,
        ),
        required_primary_binding_fields=cast(
            _ScenePrimaryBindingFieldsV1,
            value.required_primary_binding_fields,
        ),
    )


def _snapshot_contract(
    snapshot: VisualPromptProfileSnapshot,
) -> _CharacterVisualPromptProfileSnapshotV1 | _SceneVisualPromptProfileSnapshotV1:
    profile = snapshot.profile
    if (
        profile.renderer_version != _RENDERER_VERSION
        or profile.shot_type is not ShotType.REFERENCE_SHEET
        or profile.visual_style_id is not VisualStyleId.CINEMATIC_STORYBOARD_V1
    ):
        _invalid("admitted reference Profile violates the frozen renderer boundary")
    constraint_set = _PromptConstraintSetV1(
        negative_prompt_constraints=profile.constraint_set.negative_prompt_constraints,
        positive_prompt_constraints=profile.constraint_set.positive_prompt_constraints,
        qc_expectations=profile.constraint_set.qc_expectations,
    )
    sections = tuple(
        _PromptSectionV1(
            heading=item.heading,
            placeholder=item.placeholder,
            section_id=item.section_id,
        )
        for item in profile.sections
    )
    if profile.asset_purpose is AssetPurpose.CHARACTER_REFERENCE_ASSET:
        if (
            type(profile.reference_asset_recipe) is not CharacterReferenceAssetRecipe
            or profile.reference_asset_types != _CHARACTER_REFERENCE_ASSET_TYPES
        ):
            _invalid("admitted character Profile must use the exact complete character recipe")
        contract: _CharacterVisualPromptProfileSnapshotV1 | _SceneVisualPromptProfileSnapshotV1 = (
            _CharacterVisualPromptProfileSnapshotV1(
                asset_purpose=AssetPurpose.CHARACTER_REFERENCE_ASSET,
                reference_asset_recipe=_character_recipe_contract(profile.reference_asset_recipe),
                reference_asset_types=cast(
                    _CharacterReferenceAssetTypesV1,
                    profile.reference_asset_types,
                ),
                constraint_set=constraint_set,
                narrative_contexts=profile.narrative_contexts,
                profile_id=profile.profile_id,
                profile_version=profile.profile_version,
                renderer_version=_RENDERER_VERSION,
                sections=sections,
                shot_type=ShotType.REFERENCE_SHEET,
                visual_style_id=VisualStyleId.CINEMATIC_STORYBOARD_V1,
                profile_sha256=snapshot.profile_sha256,
                catalog_version=snapshot.catalog_version,
                catalog_sha256=snapshot.catalog_sha256,
            )
        )
    elif profile.asset_purpose is AssetPurpose.SCENE_REFERENCE_ASSET:
        if (
            type(profile.reference_asset_recipe) is not SceneReferenceAssetRecipe
            or profile.reference_asset_types != _SCENE_REFERENCE_ASSET_TYPES
        ):
            _invalid("admitted scene Profile must use the exact complete scene recipe")
        contract = _SceneVisualPromptProfileSnapshotV1(
            asset_purpose=AssetPurpose.SCENE_REFERENCE_ASSET,
            reference_asset_recipe=_scene_recipe_contract(profile.reference_asset_recipe),
            reference_asset_types=cast(
                _SceneReferenceAssetTypesV1,
                profile.reference_asset_types,
            ),
            constraint_set=constraint_set,
            narrative_contexts=profile.narrative_contexts,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            renderer_version=_RENDERER_VERSION,
            sections=sections,
            shot_type=ShotType.REFERENCE_SHEET,
            visual_style_id=VisualStyleId.CINEMATIC_STORYBOARD_V1,
            profile_sha256=snapshot.profile_sha256,
            catalog_version=snapshot.catalog_version,
            catalog_sha256=snapshot.catalog_sha256,
        )
    else:
        _invalid("admitted Profile purpose is outside the reference boundary")
    if _snapshot_projection(contract) != visual_prompt_profile_snapshot_projection(snapshot):
        _invalid("formal Snapshot differs from the exact resolved Profile Snapshot")
    return contract


def _render_input_contract(
    value: CharacterReferencePromptRenderInput | SceneReferencePromptRenderInput,
) -> _CharacterReferencePromptRenderInputV1 | _SceneReferencePromptRenderInputV1:
    if type(value) is CharacterReferencePromptRenderInput:
        contract: _CharacterReferencePromptRenderInputV1 | _SceneReferencePromptRenderInputV1 = (
            _CharacterReferencePromptRenderInputV1(
                action=value.action,
                character_asset_bindings=cast(
                    tuple[_CharacterAssetPromptBindingV1],
                    tuple(
                        _CharacterAssetPromptBindingV1(
                            asset_content_sha256=item.asset_content_sha256,
                            asset_version_id=item.asset_version_id,
                            character_id=item.character_id,
                        )
                        for item in value.character_asset_bindings
                    ),
                ),
                continuity_notes=value.continuity_notes,
                emotion_by_character=dict(value.emotion_by_character),
                input_kind=AssetPurpose.CHARACTER_REFERENCE_ASSET,
                narrative=value.narrative,
                visual_direction=value.visual_direction,
                wardrobe_by_character=dict(value.wardrobe_by_character),
            )
        )
    elif type(value) is SceneReferencePromptRenderInput:
        contract = _SceneReferencePromptRenderInputV1(
            action=value.action,
            continuity_notes=value.continuity_notes,
            input_kind=AssetPurpose.SCENE_REFERENCE_ASSET,
            narrative=value.narrative,
            props=value.props,
            scene_asset_binding=_SceneAssetPromptBindingV1(
                asset_content_sha256=value.scene_asset_binding.asset_content_sha256,
                asset_version_id=value.scene_asset_binding.asset_version_id,
                scene_id=value.scene_asset_binding.scene_id,
            ),
            visual_direction=value.visual_direction,
        )
    else:
        _invalid("renderer input must use one exact reference variant")
    if _render_input_projection(contract) != prompt_render_input_projection(value):
        _invalid("formal render input differs from the Phase 1 projection")
    return contract


def _receipt_contract(value: PromptRenderReceipt) -> _PromptRenderReceiptV1:
    return _PromptRenderReceiptV1.model_validate(prompt_render_receipt_document_projection(value))


def _active_character_asset(subject: CharacterBible) -> CharacterAssetVersion:
    matches = tuple(
        item for item in subject.asset_versions if item.id == subject.active_asset_version_id
    )
    if len(matches) != 1:
        _invalid("CharacterBible must resolve exactly one active AssetVersion")
    asset = matches[0]
    if (
        asset.character_id != subject.character_id
        or asset.media_type != "image/png"
        or asset.provenance != "IMPORTED_APPROVED_MEDIA"
    ):
        _invalid("active CharacterAssetVersion violates the released binding closure")
    _validate_lower_sha256(asset.content_sha256, "active character content_sha256")
    return asset


def _active_scene_asset(subject: SceneBible) -> SceneAssetVersion:
    matches = tuple(
        item for item in subject.asset_versions if item.id == subject.active_asset_version_id
    )
    if len(matches) != 1:
        _invalid("SceneBible must resolve exactly one active AssetVersion")
    asset = matches[0]
    if (
        asset.scene_id != subject.scene_id
        or asset.media_type != "image/png"
        or asset.provenance != "IMPORTED_APPROVED_MEDIA"
    ):
        _invalid("active SceneAssetVersion violates the released binding closure")
    _validate_lower_sha256(asset.content_sha256, "active scene content_sha256")
    return asset


def _revalidate_subject(subject: CharacterBible | SceneBible) -> CharacterBible | SceneBible:
    try:
        if type(subject) not in {CharacterBible, SceneBible}:
            raise TypeError("subject must be an exact CharacterBible or SceneBible")
        if type(subject.asset_versions) is not tuple:
            raise TypeError("subject Bible asset_versions must use exact tuple storage")
        if not 1 <= len(subject.asset_versions) <= 64:
            raise ValueError("subject Bible must contain 1..64 AssetVersions")
        _require_exact_model_storage(subject, field="subject Bible")
        if type(subject) is CharacterBible:
            validated: CharacterBible | SceneBible = CharacterBible.model_validate(
                subject.model_dump(mode="python"),
                strict=True,
            )
        else:
            validated = SceneBible.model_validate(
                subject.model_dump(mode="python"),
                strict=True,
            )
    except (ValidationError, TypeError, ValueError, RecursionError) as exc:
        raise VisualReferencePromptCompilerError(
            "subject Bible failed complete released-contract revalidation"
        ) from exc
    if not 1 <= len(validated.asset_versions) <= 64:
        _invalid("subject Bible must contain 1..64 AssetVersions")
    try:
        bible_document = validated.model_dump(mode="json")
    except (TypeError, ValueError, RecursionError) as exc:
        raise VisualReferencePromptCompilerError(
            "subject Bible resource representation failed"
        ) from exc
    _require_persistent_size(
        bible_document,
        maximum=_BIBLE_MAX_BYTES,
        field="subject Bible",
    )
    return validated


def _revalidate_request(
    request: CreativeSampleReferenceVisualPromptCompileRequestV1,
) -> CreativeSampleReferenceVisualPromptCompileRequestV1:
    try:
        if type(request) is not CreativeSampleReferenceVisualPromptCompileRequestV1:
            raise TypeError(
                "request must be an exact CreativeSampleReferenceVisualPromptCompileRequestV1"
            )
        _require_exact_model_storage(request, field="request")
        return CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate(
            request.model_dump(mode="python")
        )
    except (
        ValidationError,
        TypeError,
        ValueError,
        RecursionError,
        UnicodeError,
    ) as exc:
        raise VisualReferencePromptCompilerError(
            "request failed complete strict revalidation"
        ) from exc


def _derive_active_binding(
    subject: CharacterBible | SceneBible,
    request: CreativeSampleReferenceVisualPromptCompileRequestV1,
) -> CharacterAssetPromptBinding | SceneAssetPromptBinding:
    source = request.reference_source
    if type(subject) is CharacterBible:
        if (
            request.asset_purpose is not AssetPurpose.CHARACTER_REFERENCE_ASSET
            or request.subject_id != subject.character_id
            or type(source) is not _CharacterReferenceSourceV1
        ):
            _invalid("request does not close over the exact CharacterBible variant")
        character_asset = _active_character_asset(subject)
        if (
            request.expected_active_asset_version_id != character_asset.id
            or request.expected_active_asset_content_sha256 != character_asset.content_sha256
        ):
            _invalid("request expectations differ from the Bible-declared active asset")
        return CharacterAssetPromptBinding(
            asset_content_sha256=character_asset.content_sha256,
            asset_version_id=character_asset.id,
            character_id=subject.character_id,
        )
    if type(subject) is SceneBible:
        if (
            request.asset_purpose is not AssetPurpose.SCENE_REFERENCE_ASSET
            or request.subject_id != subject.scene_id
            or type(source) is not _SceneReferenceSourceV1
        ):
            _invalid("request does not close over the exact SceneBible variant")
        scene_asset = _active_scene_asset(subject)
        if (
            request.expected_active_asset_version_id != scene_asset.id
            or request.expected_active_asset_content_sha256 != scene_asset.content_sha256
        ):
            _invalid("request expectations differ from the Bible-declared active asset")
        return SceneAssetPromptBinding(
            asset_content_sha256=scene_asset.content_sha256,
            asset_version_id=scene_asset.id,
            scene_id=subject.scene_id,
        )
    _invalid("subject must use one exact released Bible variant")


def _derive_render_input(
    request: CreativeSampleReferenceVisualPromptCompileRequestV1,
    active_binding: CharacterAssetPromptBinding | SceneAssetPromptBinding,
    formal_snapshot: _CharacterVisualPromptProfileSnapshotV1
    | _SceneVisualPromptProfileSnapshotV1,
) -> CharacterReferencePromptRenderInput | SceneReferencePromptRenderInput:
    source = request.reference_source
    if type(active_binding) is CharacterAssetPromptBinding:
        if (
            request.asset_purpose is not AssetPurpose.CHARACTER_REFERENCE_ASSET
            or request.subject_id != active_binding.character_id
            or type(source) is not _CharacterReferenceSourceV1
            or type(formal_snapshot) is not _CharacterVisualPromptProfileSnapshotV1
        ):
            _invalid(
                "active binding does not close over the exact character Profile/source variant"
            )
        return CharacterReferencePromptRenderInput(
            action=source.action,
            character_asset_bindings=(active_binding,),
            continuity_notes=source.continuity_notes,
            emotion_by_character=((active_binding.character_id, source.emotion_direction),),
            input_kind=AssetPurpose.CHARACTER_REFERENCE_ASSET,
            narrative=source.narrative,
            visual_direction=source.visual_direction,
            wardrobe_by_character=((active_binding.character_id, source.wardrobe_direction),),
        )
    if type(active_binding) is SceneAssetPromptBinding:
        if (
            request.asset_purpose is not AssetPurpose.SCENE_REFERENCE_ASSET
            or request.subject_id != active_binding.scene_id
            or type(source) is not _SceneReferenceSourceV1
            or type(formal_snapshot) is not _SceneVisualPromptProfileSnapshotV1
        ):
            _invalid("active binding does not close over the exact scene Profile/source variant")
        return SceneReferencePromptRenderInput(
            action=source.action,
            continuity_notes=source.continuity_notes,
            input_kind=AssetPurpose.SCENE_REFERENCE_ASSET,
            narrative=source.narrative,
            props=source.props,
            scene_asset_binding=active_binding,
            visual_direction=source.visual_direction,
        )
    _invalid("active binding must use one exact reference variant")


def _artifact_projection_from_parts(
    *,
    request: CreativeSampleReferenceVisualPromptCompileRequestV1,
    snapshot: _CharacterVisualPromptProfileSnapshotV1 | _SceneVisualPromptProfileSnapshotV1,
    render_input: _CharacterReferencePromptRenderInputV1 | _SceneReferencePromptRenderInputV1,
    render_input_sha256: str,
    prompt: str,
    prompt_sha256: str,
    prompt_size_bytes: int,
    receipt: _PromptRenderReceiptV1,
) -> dict[str, object]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "artifact_purpose": _ARTIFACT_PURPOSE,
        "source_contract": _SOURCE_CONTRACT,
        "selection_scope": _SELECTION_SCOPE,
        "asset_purpose": request.asset_purpose.value,
        "subject_id": request.subject_id,
        "expected_active_asset_version_id": request.expected_active_asset_version_id,
        "expected_active_asset_content_sha256": (request.expected_active_asset_content_sha256),
        "reference_source": _reference_source_projection(request.reference_source),
        "selection_decision_kind": _HUMAN_DECISION,
        "selection_decision_ref": request.selection_decision_ref,
        "authoring_decision_kind": _HUMAN_DECISION,
        "authoring_decision_ref": request.authoring_decision_ref,
        "profile_snapshot": _snapshot_projection(snapshot),
        "render_input": _render_input_projection(render_input),
        "render_input_sha256": render_input_sha256,
        "prompt": prompt,
        "prompt_sha256": prompt_sha256,
        "prompt_size_bytes": prompt_size_bytes,
        "prompt_render_receipt": _prompt_render_receipt_document_projection(receipt),
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


def _compile_creative_sample_reference_visual_prompt(
    subject: CharacterBible | SceneBible,
    request: CreativeSampleReferenceVisualPromptCompileRequestV1,
) -> CreativeSampleReferenceVisualPromptArtifactV1:
    validated_subject = _revalidate_subject(subject)
    validated_request = _revalidate_request(request)
    active_binding = _derive_active_binding(validated_subject, validated_request)

    try:
        snapshot = resolve_visual_prompt_profile(
            VISUAL_PROMPT_CATALOG,
            catalog_version=validated_request.catalog_version,
            catalog_sha256=validated_request.catalog_sha256,
            profile_id=validated_request.profile_id,
            profile_version=validated_request.profile_version,
            profile_sha256=validated_request.profile_sha256,
        )
    except VisualPromptProfileError as exc:
        raise VisualReferencePromptCompilerError(
            "the exact five-value reference Profile selection was rejected"
        ) from exc
    if snapshot.asset_purpose is not validated_request.asset_purpose:
        _invalid("resolved Profile purpose differs from the request purpose")
    try:
        formal_snapshot = _snapshot_contract(snapshot)
        render_input = _derive_render_input(
            validated_request,
            active_binding,
            formal_snapshot,
        )
        prompt_bytes, receipt = render_visual_prompt(render_input, snapshot)
        formal_input = _render_input_contract(render_input)
        formal_receipt = _receipt_contract(receipt)
    except (
        ValidationError,
        VisualPromptProfileError,
        TypeError,
        ValueError,
        RecursionError,
        UnicodeError,
    ) as exc:
        raise VisualReferencePromptCompilerError(
            "reference Profile rendering or formal projection failed"
        ) from exc

    input_digest = prompt_render_input_sha256(render_input)
    if input_digest != _semantic_sha256(
        RENDER_INPUT_SHA256_DOMAIN,
        _render_input_projection(formal_input),
    ):
        _invalid("formal render-input digest differs from the Phase 1 identity")
    if formal_receipt.render_input_sha256 != input_digest:
        _invalid("renderer Receipt does not bind the exact derived render input")
    try:
        prompt = prompt_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise VisualReferencePromptCompilerError(
            "renderer returned non-UTF-8 Prompt bytes"
        ) from exc
    prompt_digest = hashlib.sha256(prompt_bytes).hexdigest()
    if formal_receipt.prompt_sha256 != prompt_digest or formal_receipt.prompt_size_bytes != len(
        prompt_bytes
    ):
        _invalid("renderer Receipt does not bind the exact Prompt bytes")

    projection = _artifact_projection_from_parts(
        request=validated_request,
        snapshot=formal_snapshot,
        render_input=formal_input,
        render_input_sha256=input_digest,
        prompt=prompt,
        prompt_sha256=prompt_digest,
        prompt_size_bytes=len(prompt_bytes),
        receipt=formal_receipt,
    )
    digest = _semantic_sha256(
        VISUAL_REFERENCE_PROMPT_COMPILER_ARTIFACT_SHA256_DOMAIN,
        projection,
    )
    try:
        artifact = CreativeSampleReferenceVisualPromptArtifactV1(
            schema_version=_SCHEMA_VERSION,
            artifact_purpose=_ARTIFACT_PURPOSE,
            source_contract=_SOURCE_CONTRACT,
            selection_scope=_SELECTION_SCOPE,
            asset_purpose=validated_request.asset_purpose,
            subject_id=validated_request.subject_id,
            expected_active_asset_version_id=(validated_request.expected_active_asset_version_id),
            expected_active_asset_content_sha256=(
                validated_request.expected_active_asset_content_sha256
            ),
            reference_source=validated_request.reference_source,
            selection_decision_kind=_HUMAN_DECISION,
            selection_decision_ref=validated_request.selection_decision_ref,
            authoring_decision_kind=_HUMAN_DECISION,
            authoring_decision_ref=validated_request.authoring_decision_ref,
            profile_snapshot=formal_snapshot,
            render_input=formal_input,
            render_input_sha256=input_digest,
            prompt=prompt,
            prompt_sha256=prompt_digest,
            prompt_size_bytes=len(prompt_bytes),
            prompt_render_receipt=formal_receipt,
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
            artifact_sha256=digest,
        )
        validated_artifact = _revalidate_artifact(artifact)
    except (
        ValidationError,
        TypeError,
        ValueError,
        RecursionError,
        UnicodeError,
    ) as exc:
        raise VisualReferencePromptCompilerError(
            "constructed reference Prompt Artifact failed strict validation"
        ) from exc
    if validated_artifact.artifact_sha256 != (
        creative_sample_reference_visual_prompt_artifact_sha256(validated_artifact)
    ):
        _invalid("constructed Artifact failed independent semantic identity validation")
    return validated_artifact


def compile_creative_sample_reference_visual_prompt(
    subject: CharacterBible | SceneBible,
    request: CreativeSampleReferenceVisualPromptCompileRequestV1,
) -> CreativeSampleReferenceVisualPromptArtifactV1:
    """Compile exactly one deterministic offline reference-sheet Prompt Artifact."""

    try:
        return _compile_creative_sample_reference_visual_prompt(subject, request)
    except (
        ValidationError,
        VisualPromptProfileError,
        VisualReferencePromptCompilerError,
        TypeError,
        ValueError,
        RecursionError,
        UnicodeError,
    ) as exc:
        raise VisualReferencePromptCompilerError(
            "reference Prompt compilation rejected the supplied values"
        ) from exc


__all__ = [
    "CreativeSampleReferenceVisualPromptCompileRequestV1",
    "CreativeSampleReferenceVisualPromptArtifactV1",
    "VisualReferencePromptCompilerError",
    "VISUAL_REFERENCE_PROMPT_COMPILER_ARTIFACT_SHA256_DOMAIN",
    "compile_creative_sample_reference_visual_prompt",
    "creative_sample_reference_visual_prompt_artifact_projection",
    "creative_sample_reference_visual_prompt_artifact_sha256",
]
