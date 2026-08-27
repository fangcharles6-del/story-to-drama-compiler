from __future__ import annotations

import ast
import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import cast

import pytest

from sdc import visual_prompt_profiles as profiles_module
from sdc.visual_prompt_profile_source import load_visual_prompt_profile_source
from sdc.visual_prompt_profiles import (
    AssetPurpose,
    CameraAngleV1,
    CameraMovementV1,
    CharacterAssetPromptBinding,
    CharacterReferenceAssetRecipe,
    CharacterReferencePromptRenderInput,
    DialoguePromptLine,
    NarrativeShotPromptRenderInput,
    OfflineRenderAdmissionStatus,
    ProfileTextProvenanceStatus,
    PromptConstraintSet,
    PromptProfileCatalog,
    PromptProfileCatalogEntry,
    PromptRenderInput,
    PromptRenderReceipt,
    PromptSection,
    ProviderSyntaxCompatibilityObservation,
    SceneAssetPromptBinding,
    SceneReferenceAssetRecipe,
    SceneReferencePromptRenderInput,
    ShotSizeV1,
    VisualPromptProfile,
    VisualPromptProfileError,
    VisualPromptProfileSnapshot,
    _build_catalog_from_generated_value,
    _build_catalog_from_validated_source,
    _build_prompt_render_input_from_validated_value,
    prompt_profile_catalog_projection,
    prompt_profile_catalog_sha256,
    prompt_render_input_projection,
    prompt_render_input_sha256,
    prompt_render_receipt_projection,
    render_visual_prompt,
    resolve_visual_prompt_profile,
    visual_prompt_profile_projection,
    visual_prompt_profile_sha256,
)


def _canonical_compact(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _independent_semantic_sha256(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_compact(value)).hexdigest()


def _literal_constraint_set_projection(value: PromptConstraintSet) -> dict[str, object]:
    return {
        "negative_prompt_constraints": list(value.negative_prompt_constraints),
        "positive_prompt_constraints": list(value.positive_prompt_constraints),
        "qc_expectations": list(value.qc_expectations),
    }


def _literal_character_recipe_projection(
    value: CharacterReferenceAssetRecipe,
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


def _literal_scene_recipe_projection(value: SceneReferenceAssetRecipe) -> dict[str, object]:
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


def _literal_recipe_projection(
    value: CharacterReferenceAssetRecipe | SceneReferenceAssetRecipe | None,
) -> dict[str, object] | None:
    if value is None:
        return None
    if type(value) is CharacterReferenceAssetRecipe:
        return _literal_character_recipe_projection(value)
    assert type(value) is SceneReferenceAssetRecipe
    return _literal_scene_recipe_projection(value)


def _literal_section_projection(value: PromptSection) -> dict[str, object]:
    return {
        "heading": value.heading,
        "placeholder": value.placeholder.value,
        "section_id": value.section_id,
    }


def _literal_profile_projection(value: VisualPromptProfile) -> dict[str, object]:
    return {
        "asset_purpose": value.asset_purpose.value,
        "constraint_set": _literal_constraint_set_projection(value.constraint_set),
        "narrative_contexts": [item.value for item in value.narrative_contexts],
        "profile_id": value.profile_id,
        "profile_version": value.profile_version,
        "reference_asset_recipe": _literal_recipe_projection(value.reference_asset_recipe),
        "reference_asset_types": [item.value for item in value.reference_asset_types],
        "renderer_version": value.renderer_version,
        "sections": [_literal_section_projection(item) for item in value.sections],
        "shot_type": value.shot_type.value,
        "visual_style_id": value.visual_style_id.value,
    }


def _literal_observation_projection(
    value: ProviderSyntaxCompatibilityObservation,
) -> dict[str, object]:
    return {
        "compatibility_status": value.compatibility_status.value,
        "provider_id": value.provider_id,
        "provider_profile_id": value.provider_profile_id,
        "provider_profile_version": value.provider_profile_version,
    }


def _literal_catalog_entry_projection(value: PromptProfileCatalogEntry) -> dict[str, object]:
    profile_projection = _literal_profile_projection(value.profile)
    profile_sha256 = _independent_semantic_sha256(
        b"sdc:visual-prompt-profile:v1\0",
        profile_projection,
    )
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
            "profile_sha256": profile_sha256,
            "profile_version": value.profile.profile_version,
        },
        "profile_text_provenance_status": value.profile_text_provenance_status.value,
        "provider_syntax_compatibility_observations": [
            _literal_observation_projection(item)
            for item in value.provider_syntax_compatibility_observations
        ],
    }


def _literal_catalog_projection(value: PromptProfileCatalog) -> dict[str, object]:
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
        "profile_entries": [_literal_catalog_entry_projection(item) for item in value.profiles],
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


def _literal_character_binding_projection(
    value: CharacterAssetPromptBinding,
) -> dict[str, object]:
    return {
        "asset_content_sha256": value.asset_content_sha256,
        "asset_version_id": value.asset_version_id,
        "character_id": value.character_id,
    }


def _literal_scene_binding_projection(value: SceneAssetPromptBinding) -> dict[str, object]:
    return {
        "asset_content_sha256": value.asset_content_sha256,
        "asset_version_id": value.asset_version_id,
        "scene_id": value.scene_id,
    }


def _literal_dialogue_projection(value: DialoguePromptLine) -> dict[str, object]:
    return {
        "character_id": value.character_id,
        "line_id": value.line_id,
        "ordinal": value.ordinal,
        "text": value.text,
    }


def _literal_character_text_map(value: tuple[tuple[str, str], ...]) -> dict[str, object]:
    return {key: text for key, text in value}


def _literal_render_input_projection(value: PromptRenderInput) -> dict[str, object]:
    if type(value) is NarrativeShotPromptRenderInput:
        return {
            "action": value.action,
            "camera_angle": value.camera_angle.value,
            "camera_movement": value.camera_movement.value,
            "character_asset_bindings": [
                _literal_character_binding_projection(item)
                for item in value.character_asset_bindings
            ],
            "continuity_notes": value.continuity_notes,
            "dialogue": [_literal_dialogue_projection(item) for item in value.dialogue],
            "emotion_by_character": _literal_character_text_map(value.emotion_by_character),
            "input_kind": value.input_kind.value,
            "narrative": value.narrative,
            "props": list(value.props),
            "scene_asset_binding": _literal_scene_binding_projection(value.scene_asset_binding),
            "shot_size": value.shot_size.value,
            "visual_direction": value.visual_direction,
            "wardrobe_by_character": _literal_character_text_map(value.wardrobe_by_character),
        }
    if type(value) is CharacterReferencePromptRenderInput:
        return {
            "action": value.action,
            "character_asset_bindings": [
                _literal_character_binding_projection(item)
                for item in value.character_asset_bindings
            ],
            "continuity_notes": value.continuity_notes,
            "emotion_by_character": _literal_character_text_map(value.emotion_by_character),
            "input_kind": value.input_kind.value,
            "narrative": value.narrative,
            "visual_direction": value.visual_direction,
            "wardrobe_by_character": _literal_character_text_map(value.wardrobe_by_character),
        }
    assert type(value) is SceneReferencePromptRenderInput
    return {
        "action": value.action,
        "continuity_notes": value.continuity_notes,
        "input_kind": value.input_kind.value,
        "narrative": value.narrative,
        "props": list(value.props),
        "scene_asset_binding": _literal_scene_binding_projection(value.scene_asset_binding),
        "visual_direction": value.visual_direction,
    }


def _literal_receipt_projection(value: PromptRenderReceipt) -> dict[str, object]:
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


def _literal_recipe_lines(
    value: CharacterReferenceAssetRecipe | SceneReferenceAssetRecipe,
) -> tuple[str, ...]:
    if type(value) is CharacterReferenceAssetRecipe:
        items: tuple[tuple[str, object], ...] = (
            ("Recipe kind", value.recipe_kind.value),
            ("Reference asset types", [item.value for item in value.reference_asset_types]),
            ("Face identity anchors", list(value.face_identity_anchors)),
            ("Hairstyle anchors", list(value.hairstyle_anchors)),
            ("Wardrobe anchors", list(value.wardrobe_anchors)),
            ("Body proportion anchors", list(value.body_proportion_anchors)),
            ("Expression range", list(value.expression_range)),
            ("Forbidden identity drift", list(value.forbidden_identity_drift)),
            ("Forbidden hairstyle drift", list(value.forbidden_hairstyle_drift)),
            ("Forbidden wardrobe drift", list(value.forbidden_wardrobe_drift)),
            (
                "Forbidden body proportion drift",
                list(value.forbidden_body_proportion_drift),
            ),
            ("Sheet layout requirements", list(value.sheet_layout_requirements)),
            ("Background requirements", list(value.background_requirements)),
            (
                "Required primary binding fields",
                list(value.required_primary_binding_fields),
            ),
        )
    else:
        assert type(value) is SceneReferenceAssetRecipe
        items = (
            ("Recipe kind", value.recipe_kind.value),
            ("Reference asset types", [item.value for item in value.reference_asset_types]),
            ("Layout requirements", list(value.layout_requirements)),
            ("Geography anchors", list(value.geography_anchors)),
            ("Lighting anchors", list(value.lighting_anchors)),
            ("Palette anchors", list(value.palette_anchors)),
            ("Material anchors", list(value.material_anchors)),
            ("Prop placement anchors", list(value.prop_placement_anchors)),
            ("Continuity requirements", list(value.continuity_requirements)),
            ("Forbidden drift", list(value.forbidden_drift)),
            (
                "Required primary binding fields",
                list(value.required_primary_binding_fields),
            ),
        )
    return tuple(
        f"{label}: {raw if type(raw) is str else _canonical_compact(raw).decode('utf-8')}"
        for label, raw in items
    )


def _literal_prompt_bytes(
    render_input: PromptRenderInput,
    profile: VisualPromptProfile,
) -> bytes:
    input_projection = _literal_render_input_projection(render_input)
    lines: list[str] = []
    for section in profile.sections:
        raw = input_projection[section.placeholder.value]
        rendered = raw if type(raw) is str else _canonical_compact(raw).decode("utf-8")
        lines.append(f"{section.heading}: {rendered}")
    lines.append("Positive Prompt Constraints:")
    lines.extend(f"- {item}" for item in profile.constraint_set.positive_prompt_constraints)
    lines.append("Negative Prompt Constraints:")
    lines.extend(f"- {item}" for item in profile.constraint_set.negative_prompt_constraints)
    if profile.reference_asset_recipe is not None:
        lines.append("Reference Asset Recipe:")
        lines.extend(_literal_recipe_lines(profile.reference_asset_recipe))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _semantic_leaf_paths(
    value: object,
    path: tuple[str | int, ...] = (),
) -> list[tuple[str | int, ...]]:
    if type(value) is dict:
        mapping = cast(dict[str, object], value)
        if not mapping:
            return [path]
        return [
            child
            for key in sorted(mapping)
            for child in _semantic_leaf_paths(mapping[key], (*path, key))
        ]
    if type(value) is list:
        items = cast(list[object], value)
        if not items:
            return [path]
        return [
            child
            for index, item in enumerate(items)
            for child in _semantic_leaf_paths(item, (*path, index))
        ]
    return [path]


def _mutated_json_leaf(value: object) -> object:
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        return value + "-changed"
    if value is None:
        return "changed"
    if type(value) is list:
        assert not value
        return ["changed"]
    assert type(value) is dict and not value
    return {"changed": True}


def _mutate_projection_at_path(value: object, path: tuple[str | int, ...]) -> object:
    if not path:
        return _mutated_json_leaf(value)
    changed = copy.deepcopy(value)
    head, *tail = path
    if type(changed) is dict:
        assert type(head) is str
        mapping = cast(dict[str, object], changed)
        mapping[head] = _mutate_projection_at_path(mapping[head], tuple(tail))
        return mapping
    assert type(changed) is list and type(head) is int
    items = cast(list[object], changed)
    items[head] = _mutate_projection_at_path(items[head], tuple(tail))
    return items


def _synthetic_admitted_catalog() -> PromptProfileCatalog:
    """Return the reviewed catalog used by the existing pure-renderer tests."""

    return load_visual_prompt_profile_source()


def _narrative_input() -> NarrativeShotPromptRenderInput:
    return NarrativeShotPromptRenderInput(
        action="They compare the two letters.",
        camera_angle=CameraAngleV1.EYE_LEVEL,
        camera_movement=CameraMovementV1.STATIC,
        character_asset_bindings=(
            CharacterAssetPromptBinding(
                asset_content_sha256="a" * 64,
                asset_version_id="asset-alex-v1",
                character_id="alex",
            ),
            CharacterAssetPromptBinding(
                asset_content_sha256="b" * 64,
                asset_version_id="asset-bo-v1",
                character_id="bo",
            ),
        ),
        continuity_notes="Keep the blue envelope on the table.",
        dialogue=(
            DialoguePromptLine(
                character_id="alex",
                line_id="line-10",
                ordinal=10,
                text="The marks are identical.",
            ),
            DialoguePromptLine(
                character_id="bo",
                line_id="line-20",
                ordinal=20,
                text="Then the sender knew us both.",
            ),
        ),
        emotion_by_character=(("alex", "Focused"), ("bo", "Uneasy")),
        input_kind=AssetPurpose.NARRATIVE_SHOT,
        narrative="Alex and Bo examine matching letters in the archive.",
        props=("blue envelope", "letters"),
        scene_asset_binding=SceneAssetPromptBinding(
            asset_content_sha256="c" * 64,
            asset_version_id="asset-archive-v1",
            scene_id="archive",
        ),
        shot_size=ShotSizeV1.MEDIUM,
        visual_direction="Muted amber light with a restrained cinematic composition.",
        wardrobe_by_character=(("alex", "Charcoal coat"), ("bo", "Navy jacket")),
    )


def _character_input() -> CharacterReferencePromptRenderInput:
    return CharacterReferencePromptRenderInput(
        action="Hold a neutral front-facing pose.",
        character_asset_bindings=(
            CharacterAssetPromptBinding(
                asset_content_sha256="a" * 64,
                asset_version_id="asset-alex-v1",
                character_id="alex",
            ),
        ),
        continuity_notes="Preserve Alex's identity across every panel.",
        emotion_by_character=(("alex", "Neutral and attentive"),),
        input_kind=AssetPurpose.CHARACTER_REFERENCE_ASSET,
        narrative="Alex identity reference for the archive sequence.",
        visual_direction="Clean orthographic reference treatment with neutral lighting.",
        wardrobe_by_character=(("alex", "Charcoal coat"),),
    )


def _scene_input() -> SceneReferencePromptRenderInput:
    return SceneReferencePromptRenderInput(
        action="Keep all architecture and furniture static.",
        continuity_notes="Preserve the north-window and central-table relationship.",
        input_kind=AssetPurpose.SCENE_REFERENCE_ASSET,
        narrative="The archive room before Alex and Bo arrive.",
        props=(),
        scene_asset_binding=SceneAssetPromptBinding(
            asset_content_sha256="c" * 64,
            asset_version_id="asset-archive-v1",
            scene_id="archive",
        ),
        visual_direction="Neutral establishing reference with readable spatial depth.",
    )


def _render_cases() -> tuple[tuple[int, PromptRenderInput], ...]:
    return (
        (0, _character_input()),
        (1, _narrative_input()),
        (2, _scene_input()),
    )


def _resolve_entry(
    catalog: PromptProfileCatalog,
    index: int,
) -> VisualPromptProfileSnapshot:
    entry = catalog.profiles[index]
    return resolve_visual_prompt_profile(
        catalog,
        catalog_version=catalog.catalog_version,
        catalog_sha256=catalog.catalog_sha256,
        profile_id=entry.profile.profile_id,
        profile_version=entry.profile.profile_version,
        profile_sha256=entry.profile_sha256,
    )


def test_profile_and_catalog_hashes_use_exact_independent_projections() -> None:
    catalog = _synthetic_admitted_catalog()

    for entry in catalog.profiles:
        literal_profile = _literal_profile_projection(entry.profile)
        expected_profile_sha256 = _independent_semantic_sha256(
            b"sdc:visual-prompt-profile:v1\0",
            literal_profile,
        )
        assert visual_prompt_profile_projection(entry.profile) == literal_profile
        assert visual_prompt_profile_sha256(entry.profile) == expected_profile_sha256
        assert entry.profile_sha256 == expected_profile_sha256

    literal_catalog = _literal_catalog_projection(catalog)
    expected_catalog_sha256 = _independent_semantic_sha256(
        b"sdc:visual-prompt-catalog:v1\0",
        literal_catalog,
    )
    assert prompt_profile_catalog_projection(catalog) == literal_catalog
    assert prompt_profile_catalog_sha256(catalog) == expected_catalog_sha256
    assert catalog.catalog_sha256 == expected_catalog_sha256


def test_semantic_hash_domains_are_exact_and_separate_from_raw_hashes() -> None:
    domains = (
        profiles_module.PROFILE_SHA256_DOMAIN,
        profiles_module.CATALOG_SHA256_DOMAIN,
        profiles_module.RENDER_INPUT_SHA256_DOMAIN,
        profiles_module.PROMPT_RENDER_RECEIPT_SHA256_DOMAIN,
        profiles_module.CATALOG_DIGEST_RECEIPT_SHA256_DOMAIN,
    )
    assert domains == (
        b"sdc:visual-prompt-profile:v1\0",
        b"sdc:visual-prompt-catalog:v1\0",
        b"sdc:visual-prompt-render-input:v1\0",
        b"sdc:visual-prompt-render-receipt:v1\0",
        b"sdc:visual-prompt-catalog-digest-receipt:v1\0",
    )

    projection = {"same": "projection"}
    semantic_digests = {_independent_semantic_sha256(domain, projection) for domain in domains}
    raw_digest = hashlib.sha256(_canonical_compact(projection)).hexdigest()

    assert len(semantic_digests) == len(domains)
    assert raw_digest not in semantic_digests


def test_display_and_status_metadata_change_only_the_catalog_hash() -> None:
    catalog = _synthetic_admitted_catalog()
    original_entry = catalog.profiles[1]
    changed_entry = replace(
        original_entry,
        display_name="Changed display-only name",
        offline_render_admission_status=OfflineRenderAdmissionStatus.RETIRED,
    )
    changed = replace(
        catalog,
        profiles=(catalog.profiles[0], changed_entry, catalog.profiles[2]),
    )

    assert changed_entry.profile_sha256 == original_entry.profile_sha256
    assert changed.catalog_sha256 != catalog.catalog_sha256


def test_exact_resolver_admits_reviewed_profiles_and_rejects_every_identity_mismatch() -> None:
    catalog = load_visual_prompt_profile_source()
    assert tuple(
        (
            entry.profile.profile_id,
            entry.profile.profile_version,
            entry.profile.asset_purpose,
        )
        for entry in catalog.profiles
    ) == (
        (
            "sdc.character-reference.cinematic.v1",
            "1.0.0",
            AssetPurpose.CHARACTER_REFERENCE_ASSET,
        ),
        (
            "sdc.narrative-shot.cinematic.v1",
            "1.0.0",
            AssetPurpose.NARRATIVE_SHOT,
        ),
        (
            "sdc.scene-reference.cinematic.v1",
            "1.0.0",
            AssetPurpose.SCENE_REFERENCE_ASSET,
        ),
    )
    assert tuple(item.value for item in catalog.profiles[0].profile.reference_asset_types) == (
        "CHARACTER_IDENTITY_SHEET",
        "CHARACTER_POSE_REFERENCE",
        "CHARACTER_EXPRESSION_REFERENCE",
    )
    assert catalog.profiles[1].profile.reference_asset_types == ()
    assert tuple(item.value for item in catalog.profiles[2].profile.reference_asset_types) == (
        "SCENE_ESTABLISHING_REFERENCE",
        "SCENE_LIGHTING_REFERENCE",
        "SCENE_MATERIAL_REFERENCE",
        "SCENE_PROP_PLACEMENT_REFERENCE",
    )
    assert catalog.catalog_reviewer_ref == "github.fangcharles6-del"
    assert catalog.catalog_reviewed_at == "2026-08-27T03:06:32Z"
    assert catalog.source_revision == "sdc.visual-prompt-profiles.phase1-reviewed.1"
    assert (
        catalog.catalog_sha256 == "cbf0e0baa8ca1bc63f8643b6e9f0982134a9bf2386e8d8c1db8adc31e7cf2fc2"
    )
    assert (
        catalog.catalog_sha256 != "aaf1e0caf4781da4d0c334b228284d984ed0cdd5590f072ec4ae3c6222e3e9f6"
    )
    assert tuple(entry.profile_sha256 for entry in catalog.profiles) == (
        "54901f50bc718eb6f51d866c842c70791c7d341e7f9c20c37281ee0bc840434d",
        "3da25632ad7798921a88200c591cd8774b65e533b6dd54a35be4c96802365181",
        "ea62abd6c0f35da2fa2ccc0d79ecc5e629aed84f14378dce0e14d88f49f11b0d",
    )
    for entry in catalog.profiles:
        assert entry.provider_syntax_compatibility_observations == ()
        assert (
            entry.offline_render_admission_status
            is OfflineRenderAdmissionStatus.HUMAN_REVIEWED_FOR_OFFLINE_RENDER
        )
        assert (
            entry.profile_text_provenance_status
            is ProfileTextProvenanceStatus.FIRST_PARTY_TEXT_REVIEWED
        )
        resolved = resolve_visual_prompt_profile(
            catalog,
            catalog_version=catalog.catalog_version,
            catalog_sha256=catalog.catalog_sha256,
            profile_id=entry.profile.profile_id,
            profile_version=entry.profile.profile_version,
            profile_sha256=entry.profile_sha256,
        )
        assert resolved.profile == entry.profile

        with pytest.raises(VisualPromptProfileError, match="resolver-only"):
            VisualPromptProfileSnapshot(
                profile=entry.profile,
                profile_sha256=entry.profile_sha256,
                catalog_version=catalog.catalog_version,
                catalog_sha256=catalog.catalog_sha256,
            )

    entry = catalog.profiles[1]
    exact_identity = {
        "catalog_version": catalog.catalog_version,
        "catalog_sha256": catalog.catalog_sha256,
        "profile_id": entry.profile.profile_id,
        "profile_version": entry.profile.profile_version,
        "profile_sha256": entry.profile_sha256,
    }
    mismatches = (
        ("catalog_version", "2.0.0", "catalog_version"),
        ("catalog_sha256", "0" * 64, "catalog_sha256"),
        ("profile_id", "sdc.missing-profile", "exact profile identity"),
        ("profile_version", "2.0.0", "exact profile identity"),
        ("profile_sha256", "0" * 64, "profile_sha256"),
    )
    for field, wrong_value, message in mismatches:
        supplied = {**exact_identity, field: wrong_value}
        with pytest.raises(VisualPromptProfileError, match=message):
            resolve_visual_prompt_profile(catalog, **supplied)  # type: ignore[arg-type]

    missing_value = dict(exact_identity)
    del missing_value["profile_sha256"]
    with pytest.raises(TypeError, match="profile_sha256"):
        resolve_visual_prompt_profile(catalog, **missing_value)  # type: ignore[arg-type]

    resolved = _resolve_entry(catalog, 1)
    with pytest.raises(VisualPromptProfileError, match="resolver-only"):
        replace(resolved, catalog_sha256=resolved.catalog_sha256)


def test_resolver_blocks_status_and_provenance_independently() -> None:
    admitted = _synthetic_admitted_catalog()
    original = admitted.profiles[1]
    blocked_pairs = (
        (
            OfflineRenderAdmissionStatus.DRAFT,
            ProfileTextProvenanceStatus.FIRST_PARTY_TEXT_REVIEWED,
        ),
        (
            OfflineRenderAdmissionStatus.RETIRED,
            ProfileTextProvenanceStatus.FIRST_PARTY_TEXT_REVIEWED,
        ),
        (
            OfflineRenderAdmissionStatus.HUMAN_REVIEWED_FOR_OFFLINE_RENDER,
            ProfileTextProvenanceStatus.RIGHTS_REVIEW_REQUIRED,
        ),
        (
            OfflineRenderAdmissionStatus.HUMAN_REVIEWED_FOR_OFFLINE_RENDER,
            ProfileTextProvenanceStatus.PROHIBITED_EXTERNAL_CONTENT,
        ),
    )
    for admission_status, provenance_status in blocked_pairs:
        blocked_entry = replace(
            original,
            offline_render_admission_status=admission_status,
            profile_text_provenance_status=provenance_status,
        )
        blocked_catalog = replace(
            admitted,
            profiles=(admitted.profiles[0], blocked_entry, admitted.profiles[2]),
        )
        with pytest.raises(VisualPromptProfileError, match="does not admit"):
            _resolve_entry(blocked_catalog, 1)


def test_exact_scalar_types_reject_coercion_and_bool_as_int() -> None:
    catalog = _synthetic_admitted_catalog()
    narrative = _narrative_input()
    snapshot = _resolve_entry(catalog, 1)
    _prompt, receipt = render_visual_prompt(narrative, snapshot)

    with pytest.raises(VisualPromptProfileError, match="exact boolean false"):
        replace(catalog, generation_authorized=0)  # type: ignore[arg-type]
    with pytest.raises(VisualPromptProfileError, match="StrictNonNegativeInt"):
        replace(narrative.dialogue[0], ordinal=True)  # type: ignore[arg-type]
    with pytest.raises(VisualPromptProfileError, match="exact CameraAngleV1"):
        replace(narrative, camera_angle="EYE_LEVEL")  # type: ignore[arg-type]
    with pytest.raises(VisualPromptProfileError, match="exact integer"):
        replace(receipt, prompt_size_bytes=True)  # type: ignore[arg-type]


def test_render_input_hash_is_explicit_and_independent_of_snapshot() -> None:
    for _entry_index, render_input in _render_cases():
        literal_projection = _literal_render_input_projection(render_input)
        expected_sha256 = _independent_semantic_sha256(
            b"sdc:visual-prompt-render-input:v1\0",
            literal_projection,
        )
        assert prompt_render_input_projection(render_input) == literal_projection
        assert prompt_render_input_sha256(render_input) == expected_sha256


def test_renderer_uses_exact_grammar_and_builds_a_zero_authority_receipt() -> None:
    catalog = _synthetic_admitted_catalog()
    for entry_index, render_input in _render_cases():
        entry = catalog.profiles[entry_index]
        snapshot = _resolve_entry(catalog, entry_index)

        prompt, receipt = render_visual_prompt(render_input, snapshot)

        assert prompt == _literal_prompt_bytes(render_input, entry.profile)
        assert b"QC Expectations" not in prompt
        assert prompt.endswith(b"\n") and not prompt.endswith(b"\n\n")
        assert b"\r" not in prompt
        assert all(not line.endswith((b" ", b"\t")) for line in prompt[:-1].split(b"\n"))
        assert receipt.prompt_sha256 == hashlib.sha256(prompt).hexdigest()
        assert receipt.prompt_size_bytes == len(prompt)
        assert receipt.render_input_sha256 == _independent_semantic_sha256(
            b"sdc:visual-prompt-render-input:v1\0",
            _literal_render_input_projection(render_input),
        )
        assert receipt.generation_authorized is False
        assert receipt.grants_rights is False
        assert receipt.replaces_rights_manifest is False

        literal_receipt = _literal_receipt_projection(receipt)
        expected_receipt_sha256 = _independent_semantic_sha256(
            b"sdc:visual-prompt-render-receipt:v1\0",
            literal_receipt,
        )
        assert prompt_render_receipt_projection(receipt) == literal_receipt
        assert receipt.prompt_render_receipt_sha256 == expected_receipt_sha256


def test_negative_constraints_are_not_qc_facts_or_retry_authority() -> None:
    catalog = _synthetic_admitted_catalog()
    entry = catalog.profiles[1]
    prompt, receipt = render_visual_prompt(_narrative_input(), _resolve_entry(catalog, 1))

    for constraint in entry.profile.constraint_set.negative_prompt_constraints:
        assert f"- {constraint}\n".encode() in prompt
    for expectation in entry.profile.constraint_set.qc_expectations:
        assert expectation.encode() not in prompt

    receipt_projection = prompt_render_receipt_projection(receipt)
    assert all(not key.startswith(("qc_", "retry_", "recovery_")) for key in receipt_projection)
    assert all(
        constraint not in json.dumps(receipt_projection, ensure_ascii=False)
        for constraint in entry.profile.constraint_set.negative_prompt_constraints
    )
    assert receipt.authorized_attempts == 0
    assert receipt.automated_execution_allowed is False


def test_prompt_render_receipt_carries_the_complete_zero_authority_state() -> None:
    catalog = _synthetic_admitted_catalog()
    _prompt, receipt = render_visual_prompt(_narrative_input(), _resolve_entry(catalog, 1))

    false_fields = (
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
    )
    zero_fields = (
        "authorized_attempts",
        "authorized_cost_cny",
        "posts_allowed",
        "provider_requests",
    )
    assert all(getattr(receipt, field) is False for field in false_fields)
    assert all(type(getattr(receipt, field)) is int for field in zero_fields)
    assert all(getattr(receipt, field) == 0 for field in zero_fields)
    assert receipt.receipt_purpose == "DETERMINISTIC_PROMPT_RENDER_PROCESS_EVIDENCE_ONLY"
    assert receipt.current_gate == "HUMAN_GATE"
    assert receipt.provider_state == "NOT_AUTHORIZED"
    assert receipt.usage_restriction == "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"


def test_renderer_is_invariant_to_cwd_and_process_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = _synthetic_admitted_catalog()
    snapshot = _resolve_entry(catalog, 1)
    render_input = _narrative_input()
    baseline = render_visual_prompt(render_input, snapshot)

    monkeypatch.chdir(tmp_path)
    for name, value in (
        ("LANG", "hostile-locale"),
        ("LC_ALL", "hostile-locale"),
        ("PYTHONHASHSEED", "987654321"),
        ("SDC_VISUAL_PROMPT_PROFILE_SOURCE", str(tmp_path / "untrusted.json")),
        ("SOURCE_DATE_EPOCH", "1"),
        ("TZ", "Pacific/Kiritimati"),
    ):
        monkeypatch.setenv(name, value)

    assert render_visual_prompt(render_input, snapshot) == baseline


def test_runtime_core_has_no_capability_imports_dynamic_execution_or_clock_reads() -> None:
    source_path = Path(profiles_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots <= {
        "__future__",
        "dataclasses",
        "datetime",
        "enum",
        "hashlib",
        "json",
        "re",
        "typing",
        "unicodedata",
    }

    forbidden_calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in {
            "__import__",
            "eval",
            "exec",
            "open",
        }:
            forbidden_calls.append(node.func.id)
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"date", "datetime"}
            and node.func.attr in {"now", "today", "utcnow"}
        ):
            forbidden_calls.append(f"{node.func.value.id}.{node.func.attr}")
    assert forbidden_calls == []


def test_renderer_rejects_prompt_bytes_above_the_frozen_limit() -> None:
    catalog = _synthetic_admitted_catalog()
    entry = catalog.profiles[1]

    def maximum_text(prefix: str, index: int) -> str:
        label = f"{prefix}{index:02d}"
        return label + "界" * (1000 - len(label))

    oversized_constraints = replace(
        entry.profile.constraint_set,
        negative_prompt_constraints=tuple(maximum_text("negative", index) for index in range(32)),
        positive_prompt_constraints=tuple(maximum_text("positive", index) for index in range(32)),
    )
    oversized_entry = replace(
        entry,
        profile=replace(entry.profile, constraint_set=oversized_constraints),
    )
    oversized_catalog = replace(
        catalog,
        profiles=(catalog.profiles[0], oversized_entry, catalog.profiles[2]),
    )

    with pytest.raises(VisualPromptProfileError, match="exceeds the frozen"):
        render_visual_prompt(
            _narrative_input(),
            _resolve_entry(oversized_catalog, 1),
        )


def test_every_semantic_projection_leaf_changes_its_independent_digest() -> None:
    catalog = _synthetic_admitted_catalog()
    projections: list[tuple[str, bytes, dict[str, object]]] = []
    for index, entry in enumerate(catalog.profiles):
        projections.append(
            (
                f"profile[{index}]",
                b"sdc:visual-prompt-profile:v1\0",
                _literal_profile_projection(entry.profile),
            )
        )
    projections.append(
        (
            "catalog",
            b"sdc:visual-prompt-catalog:v1\0",
            _literal_catalog_projection(catalog),
        )
    )
    for entry_index, render_input in _render_cases():
        projections.append(
            (
                f"render_input[{entry_index}]",
                b"sdc:visual-prompt-render-input:v1\0",
                _literal_render_input_projection(render_input),
            )
        )
        snapshot = _resolve_entry(catalog, entry_index)
        _prompt, receipt = render_visual_prompt(render_input, snapshot)
        projections.append(
            (
                f"receipt[{entry_index}]",
                b"sdc:visual-prompt-render-receipt:v1\0",
                _literal_receipt_projection(receipt),
            )
        )

    for label, domain, projection in projections:
        baseline = _independent_semantic_sha256(domain, projection)
        paths = _semantic_leaf_paths(projection)
        assert paths, label
        for path in paths:
            mutated = _mutate_projection_at_path(projection, path)
            assert _independent_semantic_sha256(domain, mutated) != baseline, (label, path)


def test_mapping_member_insertion_order_is_not_render_input_semantics() -> None:
    canonical_value = _literal_render_input_projection(_narrative_input())
    reordered_value = copy.deepcopy(canonical_value)
    for field in ("emotion_by_character", "wardrobe_by_character"):
        mapping = reordered_value[field]
        assert type(mapping) is dict
        items = tuple(cast(dict[str, object], mapping).items())
        reordered_value[field] = dict(reversed(items))
    reordered_value = dict(reversed(tuple(reordered_value.items())))

    canonical = _build_prompt_render_input_from_validated_value(canonical_value)
    reordered = _build_prompt_render_input_from_validated_value(reordered_value)

    assert canonical == reordered == _narrative_input()
    assert prompt_render_input_projection(canonical) == prompt_render_input_projection(reordered)
    assert prompt_render_input_sha256(canonical) == prompt_render_input_sha256(reordered)

    catalog = _synthetic_admitted_catalog()
    snapshot = _resolve_entry(catalog, 1)
    assert render_visual_prompt(canonical, snapshot) == render_visual_prompt(
        reordered,
        snapshot,
    )


def test_collections_are_deeply_immutable_and_noncanonical_order_fails() -> None:
    catalog = _synthetic_admitted_catalog()
    assert not hasattr(catalog, "__dict__")
    assert not hasattr(catalog.profiles[0].profile, "__dict__")
    with pytest.raises(FrozenInstanceError):
        catalog.catalog_version = "2.0.0"  # type: ignore[misc]

    valid = _narrative_input()
    with pytest.raises(VisualPromptProfileError, match="sorted by character_id"):
        replace(valid, character_asset_bindings=tuple(reversed(valid.character_asset_bindings)))
    with pytest.raises(VisualPromptProfileError, match="unique keys in ascending order"):
        replace(valid, emotion_by_character=tuple(reversed(valid.emotion_by_character)))
    with pytest.raises(VisualPromptProfileError, match="ascending ordinal order"):
        replace(valid, dialogue=tuple(reversed(valid.dialogue)))
    with pytest.raises(VisualPromptProfileError, match="ascending Unicode code-point order"):
        replace(valid, props=tuple(reversed(valid.props)))
    with pytest.raises(VisualPromptProfileError, match="exact tuple"):
        replace(valid, props=["letter"])  # type: ignore[arg-type]


def test_receipt_cannot_be_reconstructed_with_a_changed_self_digest() -> None:
    catalog = _synthetic_admitted_catalog()
    snapshot = _resolve_entry(catalog, 1)
    _prompt, receipt = render_visual_prompt(_narrative_input(), snapshot)

    with pytest.raises(VisualPromptProfileError, match="does not bind"):
        replace(receipt, prompt_render_receipt_sha256="0" * 64)
    assert isinstance(receipt, PromptRenderReceipt)


def test_generated_catalog_builder_verifies_every_literal_digest() -> None:
    source_path = Path(__file__).parents[1] / "src" / "sdc" / "visual_prompt_profiles.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    assert type(source) is dict
    catalog = _build_catalog_from_validated_source(source)
    generated = {
        **source,
        "catalog_sha256": catalog.catalog_sha256,
        "profiles": [
            {**raw_entry, "profile_sha256": entry.profile_sha256}
            for raw_entry, entry in zip(source["profiles"], catalog.profiles, strict=True)
        ],
    }

    assert _build_catalog_from_generated_value(generated) == catalog

    wrong_profile = {**generated, "profiles": list(generated["profiles"])}
    wrong_profile["profiles"][0] = {
        **wrong_profile["profiles"][0],
        "profile_sha256": "0" * 64,
    }
    with pytest.raises(VisualPromptProfileError, match=r"profiles\[0\].*does not bind"):
        _build_catalog_from_generated_value(wrong_profile)

    wrong_catalog = {**generated, "catalog_sha256": "0" * 64}
    with pytest.raises(VisualPromptProfileError, match="catalog_sha256 does not bind"):
        _build_catalog_from_generated_value(wrong_catalog)
