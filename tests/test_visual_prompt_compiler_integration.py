from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
import random
import socket
import time
import unicodedata
import uuid
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sdc import visual_prompt_compiler as integration_module
from sdc.compiler import compile_creative_sample, compile_story
from sdc.contracts import (
    CreativeSampleCompilation,
    CreativeSampleShotSpec,
    CreativeSampleSpec,
    DialogueLine,
    GenerationJob,
    JobGraph,
    ProviderRequest,
    StoryInput,
)
from sdc.creative_pilot import CreativeSamplePilotSpecDocument
from sdc.visual_prompt_catalog import VISUAL_PROMPT_CATALOG
from sdc.visual_prompt_compiler import (
    VISUAL_PROMPT_COMPILER_SIDECAR_SHA256_DOMAIN,
    CreativeSampleVisualPromptCompileRequestV1,
    CreativeSampleVisualPromptSidecarV1,
    VisualPromptCompilerError,
    compile_creative_sample_visual_prompts,
    creative_sample_visual_prompt_sidecar_projection,
    creative_sample_visual_prompt_sidecar_sha256,
)
from sdc.visual_prompt_profiles import (
    VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS,
    AssetPurpose,
    OfflineRenderAdmissionStatus,
    ProfileTextProvenanceStatus,
    prompt_profile_catalog_sha256,
    visual_prompt_profile_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
PILOT_SPEC_PATH = ROOT / "examples/creative-sample-pilot-v1/creative-sample-spec.json"
INTEGRATION_SOURCE = ROOT / "src/sdc/visual_prompt_compiler.py"
HUMAN_REVIEW_PACKET_PATH = (
    ROOT
    / "tests/fixtures/visual_prompt_profiles/compiler-integration/reviewed-known-answer-v1.json"
)
HUMAN_REVIEW_PACKET_RAW_SHA256 = (
    "40b42f406f76fef0a07f1a810d7ff4853f7f765edd48e8e998d1504fdfc0336e"
)
HUMAN_REVIEW_PACKET_SIZE_BYTES = 26_163

CATALOG_VERSION = "1.0.0"
CATALOG_SHA256 = "cbf0e0baa8ca1bc63f8643b6e9f0982134a9bf2386e8d8c1db8adc31e7cf2fc2"
PROFILE_ID = "sdc.narrative-shot.cinematic.v1"
PROFILE_VERSION = "1.0.0"
PROFILE_SHA256 = "3da25632ad7798921a88200c591cd8774b65e533b6dd54a35be4c96802365181"
PILOT_SPEC_SHA256 = "221ccd64abeaa786f9271e89e70c2c8ab37e8f03790daa766f9b763aa25e0af4"
PILOT_COMPILATION_ID = "creative_sample_c43253e73fe962f1623d"
V1_COMPILATION_SHA256 = "054319f521a69afde2dd91180f48f9af69b3223e34468b47273b04a0773c62c7"

REQUEST_FIELDS = {
    "schema_version",
    "request_purpose",
    "base_compiler_contract",
    "selection_scope",
    "spec_sha256",
    "catalog_version",
    "catalog_sha256",
    "profile_id",
    "profile_version",
    "profile_sha256",
    "selection_decision_kind",
    "selection_decision_ref",
    "current_gate",
    "provider_state",
    "generation_authorized",
    "execution_authorized",
    "publication_authorized",
    "remote_processing_allowed",
    "retention_allowed",
    "training_allowed",
    "publication_allowed",
    "automated_execution_allowed",
    "authorized_attempts",
    "authorized_cost_cny",
    "posts_allowed",
    "provider_requests",
    "grants_rights",
    "grants_qualification",
    "grants_execution_authority",
    "eligible_for_asset_promotion",
    "replaces_rights_manifest",
    "usage_restriction",
}
SIDECAR_FIELDS = {
    "schema_version",
    "artifact_purpose",
    "base_compiler_contract",
    "selection_scope",
    "base_compilation_id",
    "spec_sha256",
    "selection_decision_kind",
    "selection_decision_ref",
    "profile_snapshot",
    "shot_prompts",
    "current_gate",
    "provider_state",
    "generation_authorized",
    "execution_authorized",
    "publication_authorized",
    "remote_processing_allowed",
    "retention_allowed",
    "training_allowed",
    "publication_allowed",
    "automated_execution_allowed",
    "authorized_attempts",
    "authorized_cost_cny",
    "posts_allowed",
    "provider_requests",
    "grants_rights",
    "grants_qualification",
    "grants_execution_authority",
    "eligible_for_asset_promotion",
    "replaces_rights_manifest",
    "usage_restriction",
    "sidecar_sha256",
}
SNAPSHOT_FIELDS = {
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
    "profile_sha256",
    "catalog_version",
    "catalog_sha256",
}
SHOT_PROMPT_FIELDS = {
    "source_shot_id",
    "source_shot_ordinal",
    "render_input",
    "render_input_sha256",
    "prompt",
    "prompt_sha256",
    "prompt_size_bytes",
    "prompt_render_receipt",
}
NARRATIVE_INPUT_FIELDS = {
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
RECEIPT_FIELDS = {
    "receipt_purpose",
    "profile_id",
    "profile_version",
    "profile_sha256",
    "catalog_version",
    "catalog_sha256",
    "render_input_sha256",
    "renderer_id",
    "renderer_version",
    "prompt_sha256",
    "prompt_size_bytes",
    "current_gate",
    "provider_state",
    "generation_authorized",
    "execution_authorized",
    "publication_authorized",
    "remote_processing_allowed",
    "retention_allowed",
    "training_allowed",
    "publication_allowed",
    "automated_execution_allowed",
    "authorized_attempts",
    "authorized_cost_cny",
    "posts_allowed",
    "provider_requests",
    "usage_restriction",
    "grants_rights",
    "grants_qualification",
    "grants_execution_authority",
    "eligible_for_asset_promotion",
    "replaces_rights_manifest",
    "prompt_render_receipt_sha256",
}
FALSE_AUTHORITY_FIELDS = (
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
ZERO_AUTHORITY_FIELDS = (
    "authorized_attempts",
    "authorized_cost_cny",
    "posts_allowed",
    "provider_requests",
)
FORGED_ENTRYPOINT_REQUEST_VALUES = (
    ("selection_decision_kind", "AUTOMATED_POLICY"),
    ("unexpected_field", "forbidden"),
    *((field, True) for field in FALSE_AUTHORITY_FIELDS),
    *((field, False) for field in ZERO_AUTHORITY_FIELDS),
    *((field, 1) for field in ZERO_AUTHORITY_FIELDS),
)


@pytest.fixture(scope="module")
def synthetic_spec() -> CreativeSampleSpec:
    document = CreativeSamplePilotSpecDocument.model_validate_json(
        PILOT_SPEC_PATH.read_bytes(), strict=True
    )
    assert document.source_mode == "SYNTHETIC_PLACEHOLDER_ONLY"
    assert document.fixture_admission_scope == "TECHNICAL_COMPILATION_ONLY"
    return document.spec


@pytest.fixture(scope="module")
def compiled_sidecar(
    synthetic_spec: CreativeSampleSpec,
) -> CreativeSampleVisualPromptSidecarV1:
    _base, sidecar = compile_creative_sample_visual_prompts(
        synthetic_spec, _request(synthetic_spec)
    )
    return sidecar


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_json_document_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _spec_sha256(spec: CreativeSampleSpec) -> str:
    return hashlib.sha256(_canonical_json_bytes(spec.model_dump(mode="json"))).hexdigest()


def _request_payload(spec: CreativeSampleSpec, **updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "request_purpose": "COMPILE_OFFLINE_NARRATIVE_VISUAL_PROMPTS",
        "base_compiler_contract": "CREATIVE_SAMPLE_V2",
        "selection_scope": "ALL_NARRATIVE_SHOTS",
        "spec_sha256": _spec_sha256(spec),
        "catalog_version": CATALOG_VERSION,
        "catalog_sha256": CATALOG_SHA256,
        "profile_id": PROFILE_ID,
        "profile_version": PROFILE_VERSION,
        "profile_sha256": PROFILE_SHA256,
        "selection_decision_kind": "HUMAN_DECISION",
        "selection_decision_ref": "github.fangcharles6-del.adr041-build-test",
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
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
        "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION",
    }
    payload.update(updates)
    return payload


def _request(
    spec: CreativeSampleSpec, **updates: object
) -> CreativeSampleVisualPromptCompileRequestV1:
    return CreativeSampleVisualPromptCompileRequestV1.model_validate(
        _request_payload(spec, **updates), strict=True
    )


def _assert_zero_authority(payload: dict[str, Any]) -> None:
    assert payload["current_gate"] == "HUMAN_GATE"
    assert payload["provider_state"] == "NOT_AUTHORIZED"
    assert payload["usage_restriction"] == "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
    for field in FALSE_AUTHORITY_FIELDS:
        assert payload[field] is False
    for field in ZERO_AUTHORITY_FIELDS:
        assert type(payload[field]) is int
        assert payload[field] == 0


def _active_asset_by_id(spec: CreativeSampleSpec) -> dict[str, Any]:
    bibles = (*spec.character_bibles, *spec.scene_bibles)
    return {
        bible.active_asset_version_id: next(
            version
            for version in bible.asset_versions
            if version.id == bible.active_asset_version_id
        )
        for bible in bibles
    }


def _independent_sidecar_sha256(payload: dict[str, Any]) -> str:
    semantic = {key: value for key, value in payload.items() if key != "sidecar_sha256"}
    return hashlib.sha256(
        VISUAL_PROMPT_COMPILER_SIDECAR_SHA256_DOMAIN + _canonical_json_bytes(semantic)
    ).hexdigest()


def _leaf_paths(value: object, path: tuple[str | int, ...] = ()) -> Iterator[tuple[str | int, ...]]:
    if type(value) is dict:
        for key, item in value.items():
            yield from _leaf_paths(item, (*path, key))
    elif type(value) is list:
        for index, item in enumerate(value):
            yield from _leaf_paths(item, (*path, index))
    else:
        yield path


def _mutate_leaf(value: object) -> object:
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        return value + "x"
    if value is None:
        return "x"
    raise AssertionError(f"unsupported semantic leaf type: {type(value)!r}")


def _copy_with_leaf_mutation(value: object, path: tuple[str | int, ...]) -> object:
    if not path:
        return _mutate_leaf(value)
    head, *tail = path
    if type(value) is dict and type(head) is str:
        result = dict(value)
        result[head] = _copy_with_leaf_mutation(result[head], tuple(tail))
        return result
    if type(value) is list and type(head) is int:
        result = list(value)
        result[head] = _copy_with_leaf_mutation(result[head], tuple(tail))
        return result
    raise AssertionError(f"invalid semantic path {path!r}")


def _sidecar_dump(
    spec: CreativeSampleSpec,
) -> tuple[CreativeSampleCompilation, CreativeSampleVisualPromptSidecarV1, dict[str, Any]]:
    base, sidecar = compile_creative_sample_visual_prompts(spec, _request(spec))
    return base, sidecar, sidecar.model_dump(mode="json")


def _cyclic_list() -> list[object]:
    value: list[object] = []
    value.append(value)
    return value


def _cyclic_mapping() -> dict[str, object]:
    value: dict[str, object] = {}
    value["self"] = value
    return value


def test_request_contract_is_exact_strict_frozen_and_zero_authority(
    synthetic_spec: CreativeSampleSpec,
) -> None:
    request = _request(synthetic_spec)
    payload = request.model_dump(mode="json")

    assert set(payload) == REQUEST_FIELDS
    assert payload["request_purpose"] == "COMPILE_OFFLINE_NARRATIVE_VISUAL_PROMPTS"
    assert payload["base_compiler_contract"] == "CREATIVE_SAMPLE_V2"
    assert payload["selection_scope"] == "ALL_NARRATIVE_SHOTS"
    assert payload["selection_decision_kind"] == "HUMAN_DECISION"
    _assert_zero_authority(payload)

    with pytest.raises(ValidationError, match="frozen"):
        request.selection_decision_ref = "changed-human-decision"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        CreativeSampleVisualPromptCompileRequestV1.model_validate(
            {**payload, "unexpected": "forbidden"}, strict=True
        )


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("schema_version", "1.0.1"),
        ("request_purpose", "EXECUTE_VISUAL_PROMPTS"),
        ("base_compiler_contract", "CREATIVE_SAMPLE_V1"),
        ("selection_scope", "ONE_SHOT"),
        ("spec_sha256", "A" * 64),
        ("catalog_version", "01.0.0"),
        ("profile_id", "not/portable"),
        ("selection_decision_kind", "AUTOMATED_POLICY"),
        ("selection_decision_ref", "not/portable"),
        ("generation_authorized", 0),
        ("authorized_attempts", False),
        ("authorized_cost_cny", 0.0),
        ("usage_restriction", "AUTOMATED_EXECUTION_ALLOWED"),
    ],
)
def test_request_rejects_coercion_and_nonfrozen_literals(
    synthetic_spec: CreativeSampleSpec,
    field: str,
    invalid: object,
) -> None:
    with pytest.raises(ValidationError):
        CreativeSampleVisualPromptCompileRequestV1.model_validate(
            _request_payload(synthetic_spec, **{field: invalid}), strict=True
        )


@pytest.mark.parametrize(("field", "forged_value"), FORGED_ENTRYPOINT_REQUEST_VALUES)
def test_entrypoint_revalidates_model_copy_forged_request_before_compilation(
    synthetic_spec: CreativeSampleSpec,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    forged_value: object,
) -> None:
    request = _request(synthetic_spec).model_copy(update={field: forged_value})

    def unexpected_base_compile(_spec: CreativeSampleSpec) -> CreativeSampleCompilation:
        raise AssertionError("forged request reached base compilation")

    monkeypatch.setattr(integration_module, "compile_creative_sample", unexpected_base_compile)
    with pytest.raises(VisualPromptCompilerError):
        compile_creative_sample_visual_prompts(synthetic_spec, request)


@pytest.mark.parametrize("cycle_kind", ["list", "mapping"])
def test_entrypoint_wraps_cyclic_request_as_compiler_error_before_compilation(
    synthetic_spec: CreativeSampleSpec,
    monkeypatch: pytest.MonkeyPatch,
    cycle_kind: str,
) -> None:
    cycle: object = _cyclic_list() if cycle_kind == "list" else _cyclic_mapping()
    request = _request(synthetic_spec).model_copy(update={"profile_id": cycle})

    def unexpected_base_compile(_spec: CreativeSampleSpec) -> CreativeSampleCompilation:
        raise AssertionError("cyclic request reached base compilation")

    monkeypatch.setattr(integration_module, "compile_creative_sample", unexpected_base_compile)
    with pytest.raises(VisualPromptCompilerError):
        compile_creative_sample_visual_prompts(synthetic_spec, request)


def _forged_source_spec_model_copy(
    spec: CreativeSampleSpec,
    mutation: str,
) -> CreativeSampleSpec:
    if mutation == "shot_order":
        shots = list(spec.shots)
        shots[0], shots[1] = shots[1], shots[0]
        return spec.model_copy(update={"shots": tuple(shots)})
    if mutation == "shot_closure":
        shot = spec.shots[0].model_copy(update={"character_ids": ()})
        return spec.model_copy(update={"shots": (shot, *spec.shots[1:])})
    if mutation == "asset_closure":
        bible = spec.character_bibles[0].model_copy(
            update={"active_asset_version_id": "character_asset_00000000000000000000"}
        )
        return spec.model_copy(
            update={"character_bibles": (bible, *spec.character_bibles[1:])}
        )
    if mutation == "extra":
        return spec.model_copy(update={"unexpected_field": "forbidden"})
    raise AssertionError(mutation)


@pytest.mark.parametrize(
    "mutation", ["shot_order", "shot_closure", "asset_closure", "extra"]
)
def test_entrypoint_rejects_model_copy_forged_source_before_base_compilation(
    synthetic_spec: CreativeSampleSpec,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    forged = _forged_source_spec_model_copy(synthetic_spec, mutation)
    request = _request(forged)

    def unexpected_base_compile(_spec: CreativeSampleSpec) -> CreativeSampleCompilation:
        raise AssertionError("forged source reached base compilation")

    monkeypatch.setattr(integration_module, "compile_creative_sample", unexpected_base_compile)
    with pytest.raises(VisualPromptCompilerError):
        compile_creative_sample_visual_prompts(forged, request)


def _cyclic_source_spec_model_copy(
    spec: CreativeSampleSpec,
    mutation: str,
) -> CreativeSampleSpec:
    if mutation == "top_list":
        return spec.model_copy(update={"shots": _cyclic_list()})
    if mutation == "top_mapping":
        return spec.model_copy(update={"character_bibles": _cyclic_mapping()})
    if mutation == "nested_list":
        shot = spec.shots[0].model_copy(update={"dialogue_line_ids": _cyclic_list()})
    elif mutation == "nested_mapping":
        shot = spec.shots[0].model_copy(update={"emotion_by_character": _cyclic_mapping()})
    else:
        raise AssertionError(mutation)
    return spec.model_copy(update={"shots": (shot, *spec.shots[1:])})


@pytest.mark.parametrize(
    "mutation", ["top_list", "top_mapping", "nested_list", "nested_mapping"]
)
def test_entrypoint_wraps_cyclic_source_as_compiler_error_before_base_compilation(
    synthetic_spec: CreativeSampleSpec,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    forged = _cyclic_source_spec_model_copy(synthetic_spec, mutation)

    def unexpected_base_compile(_spec: CreativeSampleSpec) -> CreativeSampleCompilation:
        raise AssertionError("cyclic source reached base compilation")

    monkeypatch.setattr(integration_module, "compile_creative_sample", unexpected_base_compile)
    with pytest.raises(VisualPromptCompilerError):
        compile_creative_sample_visual_prompts(forged, _request(synthetic_spec))


@pytest.mark.parametrize("missing_field", sorted(REQUEST_FIELDS))
def test_request_rejects_every_missing_semantic_field(
    synthetic_spec: CreativeSampleSpec,
    missing_field: str,
) -> None:
    payload = _request(synthetic_spec).model_dump(mode="json")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        CreativeSampleVisualPromptCompileRequestV1.model_validate_json(
            _canonical_json_bytes(payload), strict=True
        )


def test_compile_closes_over_every_source_shot_and_preserves_base(
    synthetic_spec: CreativeSampleSpec,
) -> None:
    request = _request(synthetic_spec)
    expected_base = compile_creative_sample(synthetic_spec)
    base, sidecar = compile_creative_sample_visual_prompts(synthetic_spec, request)
    payload = sidecar.model_dump(mode="json")

    assert _spec_sha256(synthetic_spec) == PILOT_SPEC_SHA256
    assert base == expected_base
    assert base.id == PILOT_COMPILATION_ID
    assert base.spec_sha256 == PILOT_SPEC_SHA256
    assert set(payload) == SIDECAR_FIELDS
    assert payload["artifact_purpose"] == "OFFLINE_VISUAL_PROMPT_COMPILATION_SIDECAR"
    assert payload["base_compiler_contract"] == "CREATIVE_SAMPLE_V2"
    assert payload["selection_scope"] == "ALL_NARRATIVE_SHOTS"
    assert payload["base_compilation_id"] == base.id
    assert payload["spec_sha256"] == PILOT_SPEC_SHA256
    assert payload["selection_decision_kind"] == "HUMAN_DECISION"
    assert payload["selection_decision_ref"] == request.selection_decision_ref
    _assert_zero_authority(payload)

    snapshot = payload["profile_snapshot"]
    assert set(snapshot) == SNAPSHOT_FIELDS
    assert snapshot["asset_purpose"] == "NARRATIVE_SHOT"
    assert snapshot["shot_type"] == "NARRATIVE_FRAME"
    assert snapshot["reference_asset_recipe"] is None
    assert snapshot["reference_asset_types"] == []
    assert snapshot["profile_id"] == PROFILE_ID
    assert snapshot["profile_version"] == PROFILE_VERSION
    assert snapshot["profile_sha256"] == PROFILE_SHA256
    assert snapshot["catalog_version"] == CATALOG_VERSION
    assert snapshot["catalog_sha256"] == CATALOG_SHA256
    assert "profile" not in snapshot
    assert "catalog_reviewer_ref" not in snapshot
    assert "provider_syntax_compatibility_observations" not in snapshot

    shot_prompts = payload["shot_prompts"]
    assert len(shot_prompts) == len(synthetic_spec.shots) == len(base.pir.shots) == 10
    assert [item["source_shot_ordinal"] for item in shot_prompts] == list(range(10))
    assert [item["source_shot_id"] for item in shot_prompts] == [
        shot.id for shot in base.pir.shots
    ]

    character_by_id = {item.character_id: item for item in synthetic_spec.character_bibles}
    scene_by_id = {item.scene_id: item for item in synthetic_spec.scene_bibles}
    dialogue_by_id = {item.line_id: item for item in synthetic_spec.dialogue}
    active_assets = _active_asset_by_id(synthetic_spec)
    for source_shot, base_shot, entry in zip(
        synthetic_spec.shots, base.pir.shots, shot_prompts, strict=True
    ):
        assert set(entry) == SHOT_PROMPT_FIELDS
        render_input = entry["render_input"]
        assert set(render_input) == NARRATIVE_INPUT_FIELDS
        assert render_input["input_kind"] == "NARRATIVE_SHOT"
        for field in (
            "action",
            "continuity_notes",
            "narrative",
            "props",
            "visual_direction",
        ):
            expected = getattr(source_shot, field)
            assert render_input[field] == (list(expected) if type(expected) is tuple else expected)
        assert render_input["shot_size"] == source_shot.shot_size.value
        assert render_input["camera_angle"] == source_shot.camera_angle.value
        assert render_input["camera_movement"] == source_shot.camera_movement.value
        assert render_input["emotion_by_character"] == dict(
            sorted(source_shot.emotion_by_character.items())
        )
        assert render_input["wardrobe_by_character"] == dict(
            sorted(source_shot.wardrobe_by_character.items())
        )

        expected_character_bindings = []
        for character_id in source_shot.character_ids:
            asset_id = character_by_id[character_id].active_asset_version_id
            expected_character_bindings.append(
                {
                    "asset_content_sha256": active_assets[asset_id].content_sha256,
                    "asset_version_id": asset_id,
                    "character_id": character_id,
                }
            )
        assert render_input["character_asset_bindings"] == expected_character_bindings

        scene = scene_by_id[source_shot.scene_id]
        scene_asset = active_assets[scene.active_asset_version_id]
        assert render_input["scene_asset_binding"] == {
            "asset_content_sha256": scene_asset.content_sha256,
            "asset_version_id": scene.active_asset_version_id,
            "scene_id": scene.scene_id,
        }
        assert render_input["dialogue"] == [
            {
                "character_id": dialogue_by_id[line_id].character_id,
                "line_id": line_id,
                "ordinal": dialogue_by_id[line_id].ordinal,
                "text": dialogue_by_id[line_id].text,
            }
            for line_id in source_shot.dialogue_line_ids
        ]

        prompt_bytes = entry["prompt"].encode("utf-8")
        assert entry["prompt"].endswith("\n")
        assert not entry["prompt"].endswith("\n\n")
        assert "\r" not in entry["prompt"]
        assert not prompt_bytes.startswith(b"\xef\xbb\xbf")
        assert hashlib.sha256(prompt_bytes).hexdigest() == entry["prompt_sha256"]
        assert len(prompt_bytes) == entry["prompt_size_bytes"]
        receipt = entry["prompt_render_receipt"]
        assert set(receipt) == RECEIPT_FIELDS
        assert receipt["render_input_sha256"] == entry["render_input_sha256"]
        assert receipt["prompt_sha256"] == entry["prompt_sha256"]
        assert receipt["prompt_size_bytes"] == entry["prompt_size_bytes"]
        assert receipt["profile_sha256"] == PROFILE_SHA256
        assert receipt["catalog_sha256"] == CATALOG_SHA256
        _assert_zero_authority(receipt)

        constraints = snapshot["constraint_set"]
        for constraint in constraints["positive_prompt_constraints"]:
            assert f"- {constraint}\n" in entry["prompt"]
        for constraint in constraints["negative_prompt_constraints"]:
            assert f"- {constraint}\n" in entry["prompt"]
        for expectation in constraints["qc_expectations"]:
            assert expectation not in entry["prompt"]

        assert base_shot.prompt == base.job_graph.jobs[source_shot.ordinal].prompt
        assert base_shot.prompt != entry["prompt"]


def test_sidecar_projection_and_literal_domain_are_independent_and_complete(
    synthetic_spec: CreativeSampleSpec,
) -> None:
    _base, sidecar, payload = _sidecar_dump(synthetic_spec)
    semantic = creative_sample_visual_prompt_sidecar_projection(sidecar)

    assert VISUAL_PROMPT_COMPILER_SIDECAR_SHA256_DOMAIN == (
        b"sdc:visual-prompt-compiler-sidecar:v1\0"
    )
    assert semantic == {key: value for key, value in payload.items() if key != "sidecar_sha256"}
    assert payload["sidecar_sha256"] == _independent_sidecar_sha256(payload)
    assert payload["sidecar_sha256"] == creative_sample_visual_prompt_sidecar_sha256(sidecar)

    baseline_digest = payload["sidecar_sha256"]
    for path in _leaf_paths(semantic):
        mutated_semantic = _copy_with_leaf_mutation(semantic, path)
        assert type(mutated_semantic) is dict
        mutated_digest = hashlib.sha256(
            VISUAL_PROMPT_COMPILER_SIDECAR_SHA256_DOMAIN
            + _canonical_json_bytes(mutated_semantic)
        ).hexdigest()
        assert mutated_digest != baseline_digest, path


def _forged_sidecar_model_copy(
    sidecar: CreativeSampleVisualPromptSidecarV1,
    mutation: str,
) -> CreativeSampleVisualPromptSidecarV1:
    first = sidecar.shot_prompts[0]
    if mutation == "top_authority":
        return sidecar.model_copy(update={"generation_authorized": True})
    if mutation == "top_digest":
        return sidecar.model_copy(update={"sidecar_sha256": "0" * 64})
    if mutation == "top_extra":
        return sidecar.model_copy(update={"unexpected_field": "forbidden"})
    if mutation == "snapshot":
        snapshot = sidecar.profile_snapshot.model_copy(update={"profile_sha256": "0" * 64})
        return sidecar.model_copy(update={"profile_snapshot": snapshot})
    if mutation == "shot":
        shot = first.model_copy(update={"source_shot_ordinal": 1})
    elif mutation == "render_input":
        render_input = first.render_input.model_copy(
            update={"narrative": "Forged canonical narrative"}
        )
        shot = first.model_copy(update={"render_input": render_input})
    elif mutation == "receipt":
        receipt = first.prompt_render_receipt.model_copy(update={"provider_requests": 1})
        shot = first.model_copy(update={"prompt_render_receipt": receipt})
    else:
        raise AssertionError(mutation)
    return sidecar.model_copy(update={"shot_prompts": (shot, *sidecar.shot_prompts[1:])})


@pytest.mark.parametrize(
    "mutation",
    [
        "top_authority",
        "top_digest",
        "top_extra",
        "snapshot",
        "shot",
        "render_input",
        "receipt",
    ],
)
def test_public_projection_and_hash_reject_model_copy_forged_sidecar(
    compiled_sidecar: CreativeSampleVisualPromptSidecarV1,
    mutation: str,
) -> None:
    forged = _forged_sidecar_model_copy(compiled_sidecar, mutation)
    for operation in (
        creative_sample_visual_prompt_sidecar_projection,
        creative_sample_visual_prompt_sidecar_sha256,
    ):
        with pytest.raises(VisualPromptCompilerError):
            operation(forged)


def _cyclic_sidecar_model_copy(
    sidecar: CreativeSampleVisualPromptSidecarV1,
    mutation: str,
) -> CreativeSampleVisualPromptSidecarV1:
    if mutation == "top_list":
        return sidecar.model_copy(update={"shot_prompts": _cyclic_list()})
    if mutation == "top_mapping":
        return sidecar.model_copy(update={"profile_snapshot": _cyclic_mapping()})

    first = sidecar.shot_prompts[0]
    if mutation == "nested_list":
        render_input = first.render_input.model_copy(update={"dialogue": _cyclic_list()})
    elif mutation == "nested_mapping":
        render_input = first.render_input.model_copy(
            update={"emotion_by_character": _cyclic_mapping()}
        )
    else:
        raise AssertionError(mutation)
    shot = first.model_copy(update={"render_input": render_input})
    return sidecar.model_copy(update={"shot_prompts": (shot, *sidecar.shot_prompts[1:])})


@pytest.mark.parametrize(
    "mutation", ["top_list", "top_mapping", "nested_list", "nested_mapping"]
)
def test_public_projection_and_hash_wrap_cyclic_sidecar_as_compiler_error(
    compiled_sidecar: CreativeSampleVisualPromptSidecarV1,
    mutation: str,
) -> None:
    forged = _cyclic_sidecar_model_copy(compiled_sidecar, mutation)
    for operation in (
        creative_sample_visual_prompt_sidecar_projection,
        creative_sample_visual_prompt_sidecar_sha256,
    ):
        with pytest.raises(VisualPromptCompilerError):
            operation(forged)


def test_compilation_is_byte_deterministic_and_preserves_v1_identity(
    synthetic_spec: CreativeSampleSpec,
) -> None:
    first = compile_creative_sample_visual_prompts(synthetic_spec, _request(synthetic_spec))
    second = compile_creative_sample_visual_prompts(synthetic_spec, _request(synthetic_spec))
    assert first == second
    assert first[1].model_dump_json() == second[1].model_dump_json()

    story = StoryInput.model_validate_json((ROOT / "examples/minimal_story.json").read_bytes())
    v1_values = [item.model_dump(mode="json") for item in compile_story(story)]
    assert hashlib.sha256(_canonical_json_bytes(v1_values)).hexdigest() == V1_COMPILATION_SHA256


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [
        ("spec_sha256", "0" * 64),
        ("catalog_version", "1.0.1"),
        ("catalog_sha256", "0" * 64),
        ("profile_id", "sdc.unknown-profile.v1"),
        ("profile_version", "1.0.1"),
        ("profile_sha256", "0" * 64),
    ],
)
def test_compile_rejects_every_exact_selection_mismatch_without_fallback(
    synthetic_spec: CreativeSampleSpec,
    field: str,
    wrong_value: str,
) -> None:
    request = _request(synthetic_spec).model_copy(update={field: wrong_value})
    with pytest.raises(VisualPromptCompilerError):
        compile_creative_sample_visual_prompts(synthetic_spec, request)


@pytest.mark.parametrize(
    "purpose",
    [AssetPurpose.CHARACTER_REFERENCE_ASSET, AssetPurpose.SCENE_REFERENCE_ASSET],
)
def test_compile_rejects_reference_profile_purposes(
    synthetic_spec: CreativeSampleSpec,
    purpose: AssetPurpose,
) -> None:
    entry = next(
        item for item in VISUAL_PROMPT_CATALOG.profiles if item.profile.asset_purpose is purpose
    )
    request = _request(
        synthetic_spec,
        profile_id=entry.profile.profile_id,
        profile_version=entry.profile.profile_version,
        profile_sha256=visual_prompt_profile_sha256(entry.profile),
    )
    with pytest.raises(VisualPromptCompilerError):
        compile_creative_sample_visual_prompts(synthetic_spec, request)


@pytest.mark.parametrize(
    ("admission", "provenance"),
    [
        (OfflineRenderAdmissionStatus.DRAFT, ProfileTextProvenanceStatus.FIRST_PARTY_TEXT_REVIEWED),
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
    ],
)
def test_compile_rejects_each_nonadmitted_catalog_status(
    synthetic_spec: CreativeSampleSpec,
    monkeypatch: pytest.MonkeyPatch,
    admission: OfflineRenderAdmissionStatus,
    provenance: ProfileTextProvenanceStatus,
) -> None:
    entries = list(VISUAL_PROMPT_CATALOG.profiles)
    index = next(
        index for index, item in enumerate(entries) if item.profile.profile_id == PROFILE_ID
    )
    entries[index] = replace(
        entries[index],
        offline_render_admission_status=admission,
        profile_text_provenance_status=provenance,
    )
    catalog = replace(VISUAL_PROMPT_CATALOG, profiles=tuple(entries))
    monkeypatch.setattr(integration_module, "VISUAL_PROMPT_CATALOG", catalog)
    request = _request(synthetic_spec, catalog_sha256=prompt_profile_catalog_sha256(catalog))

    with pytest.raises(VisualPromptCompilerError):
        compile_creative_sample_visual_prompts(synthetic_spec, request)


def _tampered_compilation(
    compilation: CreativeSampleCompilation,
    mutation: str,
) -> CreativeSampleCompilation:
    if mutation == "extra":
        return compilation.model_copy(update={"unexpected_field": "forbidden"})
    shots = list(compilation.pir.shots)
    if mutation == "semantic":
        shots[0] = shots[0].model_copy(update={"narrative": "Tampered compiled narrative"})
    elif mutation == "character_binding":
        binding = shots[0].character_assets[0].model_copy(
            update={"asset_version_id": "character_asset_00000000000000000000"}
        )
        shots[0] = shots[0].model_copy(update={"character_assets": (binding,)})
    elif mutation == "scene_binding":
        shots[0] = shots[0].model_copy(
            update={"scene_asset_version_id": "scene_asset_00000000000000000000"}
        )
    elif mutation == "shot_id":
        shots[0] = shots[0].model_copy(
            update={"id": "storyboard_shot_v2_00000000000000000000"}
        )
    elif mutation == "prompt":
        shots[0] = shots[0].model_copy(update={"prompt": "Forged base Prompt"})
    elif mutation == "jobgraph_binding":
        jobs = list(compilation.job_graph.jobs)
        jobs[0] = jobs[0].model_copy(update={"shot_id": shots[1].id})
        graph = compilation.job_graph.model_copy(update={"jobs": tuple(jobs)})
        return compilation.model_copy(update={"job_graph": graph})
    elif mutation == "missing":
        shots.pop()
    elif mutation == "reordered":
        shots[0], shots[1] = shots[1], shots[0]
    else:
        raise AssertionError(mutation)
    pir = compilation.pir.model_copy(update={"shots": tuple(shots)})
    return compilation.model_copy(update={"pir": pir})


def _cyclic_compilation_model_copy(
    compilation: CreativeSampleCompilation,
    mutation: str,
) -> CreativeSampleCompilation:
    if mutation == "top_list":
        return compilation.model_copy(update={"pir": _cyclic_list()})
    if mutation == "top_mapping":
        return compilation.model_copy(update={"job_graph": _cyclic_mapping()})
    if mutation == "nested_list":
        pir = compilation.pir.model_copy(update={"shots": _cyclic_list()})
        return compilation.model_copy(update={"pir": pir})
    if mutation == "nested_mapping":
        shots = list(compilation.pir.shots)
        shots[0] = shots[0].model_copy(
            update={"emotion_by_character": _cyclic_mapping()}
        )
        pir = compilation.pir.model_copy(update={"shots": tuple(shots)})
        return compilation.model_copy(update={"pir": pir})
    raise AssertionError(mutation)


@pytest.mark.parametrize(
    "mutation",
    [
        "semantic",
        "character_binding",
        "scene_binding",
        "shot_id",
        "prompt",
        "jobgraph_binding",
        "extra",
        "missing",
        "reordered",
    ],
)
def test_source_to_base_closure_rejects_tampered_compilation(
    synthetic_spec: CreativeSampleSpec,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    tampered = _tampered_compilation(compile_creative_sample(synthetic_spec), mutation)
    monkeypatch.setattr(integration_module, "compile_creative_sample", lambda _spec: tampered)

    def unexpected_sidecar_build(**_kwargs: object) -> CreativeSampleVisualPromptSidecarV1:
        raise AssertionError("forged base reached sidecar construction")

    monkeypatch.setattr(integration_module, "_build_sidecar", unexpected_sidecar_build)
    with pytest.raises(VisualPromptCompilerError):
        compile_creative_sample_visual_prompts(synthetic_spec, _request(synthetic_spec))


@pytest.mark.parametrize(
    "mutation", ["top_list", "top_mapping", "nested_list", "nested_mapping"]
)
def test_entrypoint_wraps_cyclic_compiled_base_before_sidecar_construction(
    synthetic_spec: CreativeSampleSpec,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    forged = _cyclic_compilation_model_copy(
        compile_creative_sample(synthetic_spec), mutation
    )
    monkeypatch.setattr(integration_module, "compile_creative_sample", lambda _spec: forged)

    def unexpected_sidecar_build(**_kwargs: object) -> CreativeSampleVisualPromptSidecarV1:
        raise AssertionError("cyclic base reached sidecar construction")

    monkeypatch.setattr(integration_module, "_build_sidecar", unexpected_sidecar_build)
    with pytest.raises(VisualPromptCompilerError):
        compile_creative_sample_visual_prompts(synthetic_spec, _request(synthetic_spec))


def _rehashed_sidecar_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload["sidecar_sha256"] = _independent_sidecar_sha256(payload)
    return payload


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["profile_snapshot"].__setitem__("unexpected", "forbidden"),
        lambda value: value["shot_prompts"][0]["render_input"].__setitem__(
            "narrative", "Different canonical narrative"
        ),
        lambda value: value["shot_prompts"][0].__setitem__(
            "prompt", value["shot_prompts"][0]["prompt"] + "extra\n"
        ),
        lambda value: value["shot_prompts"][0]["prompt_render_receipt"].__setitem__(
            "prompt_sha256", "0" * 64
        ),
        lambda value: value["shot_prompts"].pop(1),
        lambda value: value["shot_prompts"].__setitem__(
            slice(0, 2), list(reversed(value["shot_prompts"][:2]))
        ),
        lambda value: value.__setitem__("generation_authorized", True),
    ],
)
def test_sidecar_rejects_nested_mismatch_even_with_recomputed_outer_digest(
    synthetic_spec: CreativeSampleSpec,
    mutate: Callable[[dict[str, Any]], object],
) -> None:
    _base, _sidecar, payload = _sidecar_dump(synthetic_spec)
    mutate(payload)
    with pytest.raises(ValidationError):
        CreativeSampleVisualPromptSidecarV1.model_validate_json(
            _canonical_json_bytes(_rehashed_sidecar_payload(payload)), strict=True
        )


def test_sidecar_and_nested_values_are_frozen(synthetic_spec: CreativeSampleSpec) -> None:
    _base, sidecar, _payload = _sidecar_dump(synthetic_spec)
    assert (
        CreativeSampleVisualPromptSidecarV1.model_validate_json(
            sidecar.model_dump_json(), strict=True
        )
        == sidecar
    )
    with pytest.raises(ValidationError, match="frozen"):
        sidecar.selection_decision_ref = "changed-selection"  # type: ignore[misc]
    with pytest.raises(ValidationError, match="frozen"):
        sidecar.profile_snapshot.profile_id = "changed-profile"  # type: ignore[misc]
    with pytest.raises(ValidationError, match="frozen"):
        sidecar.shot_prompts[0].prompt = "changed prompt\n"  # type: ignore[misc]


@pytest.mark.parametrize("missing_field", sorted(SIDECAR_FIELDS))
def test_sidecar_rejects_every_missing_semantic_field(
    compiled_sidecar: CreativeSampleVisualPromptSidecarV1,
    missing_field: str,
) -> None:
    payload = compiled_sidecar.model_dump(mode="json")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        CreativeSampleVisualPromptSidecarV1.model_validate_json(
            _canonical_json_bytes(payload), strict=True
        )


@pytest.mark.parametrize("missing_field", sorted(RECEIPT_FIELDS))
def test_nested_receipt_rejects_every_missing_semantic_field(
    compiled_sidecar: CreativeSampleVisualPromptSidecarV1,
    missing_field: str,
) -> None:
    receipt = compiled_sidecar.shot_prompts[0].prompt_render_receipt
    payload = receipt.model_dump(mode="json")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        type(receipt).model_validate_json(_canonical_json_bytes(payload), strict=True)


def _spec_with_no_character_no_dialogue_shot(spec: CreativeSampleSpec) -> CreativeSampleSpec:
    first = spec.shots[0]
    assert not first.dialogue_line_ids
    empty = first.model_copy(
        update={
            "action": "信封保持静止，晨光中的窗帘投影轻微移动",
            "character_ids": (),
            "continuity_notes": "保持空桌、信封位置与晨光方向在前后镜头中一致。",
            "dialogue_line_ids": (),
            "emotion_by_character": {},
            "narrative": "奶油色信封静置在空无一人的浅木桌上。",
            "visual_direction": "高机位静态近景；空置办公室内，信封位于桌面左前方。",
            "wardrobe_by_character": {},
        }
    )
    return CreativeSampleSpec(
        title=spec.title,
        seed=spec.seed,
        duration_ms=spec.duration_ms,
        character_bibles=spec.character_bibles,
        scene_bibles=spec.scene_bibles,
        dialogue=spec.dialogue,
        shots=(empty, *spec.shots[1:]),
    )


def test_no_character_no_dialogue_shot_has_exact_empty_projection(
    synthetic_spec: CreativeSampleSpec,
) -> None:
    spec = _spec_with_no_character_no_dialogue_shot(synthetic_spec)
    _base, sidecar = compile_creative_sample_visual_prompts(spec, _request(spec))
    first = sidecar.model_dump(mode="json")["shot_prompts"][0]
    render_input = first["render_input"]

    assert render_input["character_asset_bindings"] == []
    assert render_input["emotion_by_character"] == {}
    assert render_input["wardrobe_by_character"] == {}
    assert render_input["dialogue"] == []
    assert "Character Asset Bindings: []\n" in first["prompt"]
    assert "Dialogue: []\n" in first["prompt"]


def _spec_with_ordered_multi_character_dialogue(
    spec: CreativeSampleSpec,
) -> tuple[CreativeSampleSpec, int]:
    target = next(
        shot for shot in spec.shots if len(shot.character_ids) == 2 and shot.dialogue_line_ids
    )
    original_by_id = {line.line_id: line for line in spec.dialogue}
    target_line = original_by_id[target.dialogue_line_ids[0]]
    target_index = spec.dialogue.index(target_line)
    next_line = spec.dialogue[target_index + 1]
    new_start = target_line.end_ms + 100
    new_end = new_start + 500
    assert new_end <= target.start_ms + target.duration_ms
    assert new_end <= next_line.start_ms

    descriptors: list[tuple[DialogueLine | None, str, int, int, str, str]] = []
    for line in spec.dialogue:
        descriptors.append(
            (line, line.text, line.start_ms, line.end_ms, line.scene_id, line.character_id)
        )
        if line is target_line:
            descriptors.append(
                (
                    None,
                    "第二句第一方合成对白，保持 NFC。",
                    new_start,
                    new_end,
                    target.scene_id,
                    target.character_ids[1],
                )
            )

    dialogue: list[DialogueLine] = []
    old_to_new: dict[str, str] = {}
    inserted_id = ""
    for ordinal, (old, text, start_ms, end_ms, scene_id, character_id) in enumerate(descriptors):
        line_id = DialogueLine.derive_id(
            ordinal=ordinal,
            scene_id=scene_id,
            character_id=character_id,
            text=text,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        line = DialogueLine(
            line_id=line_id,
            ordinal=ordinal,
            scene_id=scene_id,
            character_id=character_id,
            text=text,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        dialogue.append(line)
        if old is None:
            inserted_id = line.line_id
        else:
            old_to_new[old.line_id] = line.line_id

    shots: list[CreativeSampleShotSpec] = []
    for shot in spec.shots:
        ids = tuple(old_to_new[line_id] for line_id in shot.dialogue_line_ids)
        if shot.ordinal == target.ordinal:
            ids = (*ids, inserted_id)
        shots.append(shot.model_copy(update={"dialogue_line_ids": ids}))
    updated = CreativeSampleSpec(
        title=spec.title,
        seed=spec.seed,
        duration_ms=spec.duration_ms,
        character_bibles=spec.character_bibles,
        scene_bibles=spec.scene_bibles,
        dialogue=tuple(dialogue),
        shots=tuple(shots),
    )
    return updated, target.ordinal


def test_multi_character_dialogue_and_active_content_hashes_are_ordered(
    synthetic_spec: CreativeSampleSpec,
) -> None:
    spec, ordinal = _spec_with_ordered_multi_character_dialogue(synthetic_spec)
    _base, sidecar = compile_creative_sample_visual_prompts(spec, _request(spec))
    render_input = sidecar.model_dump(mode="json")["shot_prompts"][ordinal]["render_input"]

    assert len(render_input["character_asset_bindings"]) == 2
    assert len(render_input["dialogue"]) == 2
    assert [line["ordinal"] for line in render_input["dialogue"]] == sorted(
        line["ordinal"] for line in render_input["dialogue"]
    )
    active_assets = _active_asset_by_id(spec)
    for binding in render_input["character_asset_bindings"]:
        assert binding["asset_content_sha256"] == active_assets[
            binding["asset_version_id"]
        ].content_sha256


def _human_review_case(
    spec: CreativeSampleSpec,
    ordinal: int,
    *,
    case_id: str,
    semantics: str,
    source_variant: str,
) -> dict[str, Any]:
    base, sidecar = compile_creative_sample_visual_prompts(spec, _request(spec))
    sidecar_value = sidecar.model_dump(mode="json")
    shot = sidecar_value["shot_prompts"][ordinal]
    snapshot = sidecar_value["profile_snapshot"]
    receipt = shot["prompt_render_receipt"]
    return {
        "base_compilation_id": base.id,
        "case_id": case_id,
        "case_semantics": semantics,
        "catalog_sha256": snapshot["catalog_sha256"],
        "catalog_version": snapshot["catalog_version"],
        "profile_id": snapshot["profile_id"],
        "profile_sha256": snapshot["profile_sha256"],
        "profile_version": snapshot["profile_version"],
        "prompt": shot["prompt"],
        "prompt_render_receipt": receipt,
        "prompt_render_receipt_sha256": receipt["prompt_render_receipt_sha256"],
        "prompt_sha256": shot["prompt_sha256"],
        "prompt_size_bytes": shot["prompt_size_bytes"],
        "render_input": shot["render_input"],
        "render_input_sha256": shot["render_input_sha256"],
        "review_status": "HUMAN_REVIEW_REQUIRED",
        "sidecar_sha256": sidecar.sidecar_sha256,
        "sidecar_shot_count": len(sidecar.shot_prompts),
        "source_shot_id": shot["source_shot_id"],
        "source_shot_ordinal": shot["source_shot_ordinal"],
        "source_spec_variant": source_variant,
        "spec_sha256": base.spec_sha256,
    }


def _nested_mapping_keys(value: object) -> Iterator[str]:
    if type(value) is dict:
        for key, item in value.items():
            assert type(key) is str
            yield key
            yield from _nested_mapping_keys(item)
    elif type(value) is list:
        for item in value:
            yield from _nested_mapping_keys(item)


def test_human_review_packet_has_exact_frozen_bytes_and_no_review_claim(
    synthetic_spec: CreativeSampleSpec,
) -> None:
    relative_path = HUMAN_REVIEW_PACKET_PATH.relative_to(ROOT).as_posix()
    assert len(VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS) == 9
    assert relative_path not in VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS

    raw = HUMAN_REVIEW_PACKET_PATH.read_bytes()
    assert len(raw) == HUMAN_REVIEW_PACKET_SIZE_BYTES
    assert hashlib.sha256(raw).hexdigest() == HUMAN_REVIEW_PACKET_RAW_SHA256
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw

    packet = json.loads(raw)
    assert type(packet) is dict
    assert raw == _canonical_json_document_bytes(packet)
    assert set(packet) == {
        "authority_scope",
        "cases",
        "packet_purpose",
        "packet_version",
        "review_status",
        "source_scope",
    }
    assert packet["packet_version"] == "1.0.0"
    assert packet["review_status"] == "HUMAN_REVIEW_REQUIRED"
    assert packet["authority_scope"] == (
        "NO_RIGHTS_PROVIDER_EXECUTION_QUALIFICATION_OR_PUBLICATION_AUTHORITY"
    )
    assert packet["source_scope"] == (
        "EXISTING_SYNTHETIC_PILOT_SPEC_AND_DETERMINISTIC_LOCAL_VARIANTS_ONLY"
    )
    assert tuple(case["case_id"] for case in packet["cases"]) == (
        "basic-narrative",
        "unicode-nfc",
        "no-character-no-dialogue",
        "multi-character-ordered-dialogue-active-assets",
    )
    assert all(case["review_status"] == "HUMAN_REVIEW_REQUIRED" for case in packet["cases"])

    forbidden_keys = {
        "approval_ref",
        "approved_at",
        "review_decision",
        "reviewed_at",
        "reviewer_ref",
    }
    keys = tuple(_nested_mapping_keys(packet))
    assert not forbidden_keys.intersection(keys)
    assert not any(key.endswith(("_reviewer", "_reviewer_ref")) for key in keys)
    assert not any(key.endswith("_ref") for key in keys)
    assert not any(key.endswith(("_at", "_time", "_timestamp")) for key in keys)
    assert b'"APPROVED"' not in raw
    assert b'"HUMAN_REVIEWED_FOR_OFFLINE_RENDER"' not in raw
    assert b'"FIRST_PARTY_TEXT_REVIEWED"' not in raw

    no_character = _spec_with_no_character_no_dialogue_shot(synthetic_spec)
    multi_character, multi_ordinal = _spec_with_ordered_multi_character_dialogue(synthetic_spec)
    expected_cases = [
        _human_review_case(
            synthetic_spec,
            0,
            case_id="basic-narrative",
            semantics="ONE_CHARACTER_BASIC_NARRATIVE_WITH_NO_DIALOGUE",
            source_variant="EXISTING_SYNTHETIC_PILOT_SPEC",
        ),
        _human_review_case(
            synthetic_spec,
            1,
            case_id="unicode-nfc",
            semantics="UNICODE_NFC_NARRATIVE_PROMPT_AND_RECEIPT",
            source_variant="EXISTING_SYNTHETIC_PILOT_SPEC",
        ),
        _human_review_case(
            no_character,
            0,
            case_id="no-character-no-dialogue",
            semantics="EMPTY_CHARACTER_BINDINGS_MAPS_AND_DIALOGUE",
            source_variant="DETERMINISTIC_LOCAL_NO_CHARACTER_NO_DIALOGUE_VARIANT",
        ),
        _human_review_case(
            multi_character,
            multi_ordinal,
            case_id="multi-character-ordered-dialogue-active-assets",
            semantics="TWO_CHARACTERS_ORDERED_DIALOGUE_AND_ACTIVE_ASSET_CONTENT_HASHES",
            source_variant="DETERMINISTIC_LOCAL_MULTI_CHARACTER_ORDERED_DIALOGUE_VARIANT",
        ),
    ]
    assert packet["cases"] == expected_cases


def test_human_review_packet_cases_bind_all_required_hashes_and_semantics(
    synthetic_spec: CreativeSampleSpec,
) -> None:
    packet = json.loads(HUMAN_REVIEW_PACKET_PATH.read_bytes())
    case_by_id = {case["case_id"]: case for case in packet["cases"]}
    assert len(case_by_id) == 4

    for case in case_by_id.values():
        prompt_raw = case["prompt"].encode("utf-8")
        assert case["prompt_sha256"] == hashlib.sha256(prompt_raw).hexdigest()
        assert case["prompt_size_bytes"] == len(prompt_raw)
        assert case["render_input_sha256"] == hashlib.sha256(
            b"sdc:visual-prompt-render-input:v1\0"
            + _canonical_json_bytes(case["render_input"])
        ).hexdigest()

        receipt = case["prompt_render_receipt"]
        assert set(receipt) == RECEIPT_FIELDS
        receipt_projection = {
            key: value
            for key, value in receipt.items()
            if key != "prompt_render_receipt_sha256"
        }
        expected_receipt_sha256 = hashlib.sha256(
            b"sdc:visual-prompt-render-receipt:v1\0"
            + _canonical_json_bytes(receipt_projection)
        ).hexdigest()
        assert receipt["prompt_render_receipt_sha256"] == expected_receipt_sha256
        assert case["prompt_render_receipt_sha256"] == expected_receipt_sha256
        assert receipt["render_input_sha256"] == case["render_input_sha256"]
        assert receipt["prompt_sha256"] == case["prompt_sha256"]
        assert receipt["prompt_size_bytes"] == case["prompt_size_bytes"]
        assert case["catalog_version"] == receipt["catalog_version"] == CATALOG_VERSION
        assert case["catalog_sha256"] == receipt["catalog_sha256"] == CATALOG_SHA256
        assert case["profile_id"] == receipt["profile_id"] == PROFILE_ID
        assert case["profile_version"] == receipt["profile_version"] == PROFILE_VERSION
        assert case["profile_sha256"] == receipt["profile_sha256"] == PROFILE_SHA256
        assert case["sidecar_shot_count"] == len(synthetic_spec.shots)
        assert case["source_shot_ordinal"] in range(case["sidecar_shot_count"])
        _assert_zero_authority(receipt)

    basic = case_by_id["basic-narrative"]["render_input"]
    assert len(basic["character_asset_bindings"]) == 1
    assert basic["dialogue"] == []

    unicode_case = case_by_id["unicode-nfc"]
    unicode_text = json.dumps(unicode_case["render_input"], ensure_ascii=False)
    assert any(ord(character) > 127 for character in unicode_text)
    assert unicodedata.normalize("NFC", unicode_text) == unicode_text
    assert unicodedata.normalize("NFC", unicode_case["prompt"]) == unicode_case["prompt"]

    empty = case_by_id["no-character-no-dialogue"]["render_input"]
    assert empty["character_asset_bindings"] == []
    assert empty["emotion_by_character"] == {}
    assert empty["wardrobe_by_character"] == {}
    assert empty["dialogue"] == []
    empty_text = json.dumps(empty, ensure_ascii=False)
    assert all(bible.name not in empty_text for bible in synthetic_spec.character_bibles)

    multi_spec, _ordinal = _spec_with_ordered_multi_character_dialogue(synthetic_spec)
    multi = case_by_id["multi-character-ordered-dialogue-active-assets"]["render_input"]
    assert len(multi["character_asset_bindings"]) == 2
    assert len(multi["dialogue"]) == 2
    assert [line["ordinal"] for line in multi["dialogue"]] == sorted(
        line["ordinal"] for line in multi["dialogue"]
    )
    active_assets = _active_asset_by_id(multi_spec)
    for binding in multi["character_asset_bindings"]:
        assert binding["asset_content_sha256"] == active_assets[
            binding["asset_version_id"]
        ].content_sha256


def test_compilation_reads_no_network_environment_clock_randomness_or_source_catalog(
    synthetic_spec: CreativeSampleSpec,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("forbidden nondeterministic or external input")

    from sdc import visual_prompt_profile_source

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(os, "getenv", denied)
    monkeypatch.setattr(random, "random", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(time, "time", denied)
    monkeypatch.setattr(uuid, "uuid4", denied)
    monkeypatch.setattr(visual_prompt_profile_source, "load_visual_prompt_profile_source", denied)

    base, sidecar = compile_creative_sample_visual_prompts(synthetic_spec, _request(synthetic_spec))
    assert base.id == PILOT_COMPILATION_ID
    assert sidecar.provider_requests == 0


def test_integration_source_has_no_execution_or_dynamic_input_imports() -> None:
    tree = ast.parse(INTEGRATION_SOURCE.read_text(encoding="utf-8"))
    forbidden_roots = {
        "datetime",
        "httpx",
        "importlib",
        "os",
        "pathlib",
        "random",
        "requests",
        "socket",
        "subprocess",
        "time",
        "urllib",
        "uuid",
    }
    forbidden_sdc_modules = {
        "sdc.ark_provider",
        "sdc.client",
        "sdc.creative_providers",
        "sdc.provider",
        "sdc.qc",
        "sdc.runtime",
        "sdc.semantic_qc",
        "sdc.worker",
        "sdc.workflow",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not {alias.name.split(".")[0] for alias in node.names} & forbidden_roots
            assert not {alias.name for alias in node.names} & forbidden_sdc_modules
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            assert node.module.split(".")[0] not in forbidden_roots
            assert node.module not in forbidden_sdc_modules
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"__import__", "eval", "exec", "open"}


def test_runtime_provider_worker_and_qc_do_not_import_integration() -> None:
    isolated_modules = (
        "client.py",
        "runtime.py",
        "worker.py",
        "workflow.py",
        "provider.py",
        "creative_providers.py",
        "qc.py",
        "semantic_qc.py",
    )
    for name in isolated_modules:
        source = (ROOT / "src/sdc" / name).read_text(encoding="utf-8")
        assert "visual_prompt_compiler" not in source
        assert "CreativeSampleVisualPromptSidecarV1" not in source


def test_sidecar_is_structurally_rejected_by_execution_contracts(
    synthetic_spec: CreativeSampleSpec,
) -> None:
    base, _sidecar, payload = _sidecar_dump(synthetic_spec)
    for model in (GenerationJob, JobGraph, ProviderRequest):
        with pytest.raises(ValidationError):
            model.model_validate(payload, strict=True)

    assert len(base.job_graph.jobs) == len(base.pir.shots)
    assert [job.shot_id for job in base.job_graph.jobs] == [shot.id for shot in base.pir.shots]
    assert all(job.max_attempts == 2 for job in base.job_graph.jobs)
    assert payload["authorized_attempts"] == 0


def test_integrity_verification_does_not_claim_historical_catalog_readmission(
    synthetic_spec: CreativeSampleSpec,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base, sidecar, payload = _sidecar_dump(synthetic_spec)
    monkeypatch.setattr(integration_module, "VISUAL_PROMPT_CATALOG", None)

    assert creative_sample_visual_prompt_sidecar_sha256(sidecar) == payload["sidecar_sha256"]
    with pytest.raises(VisualPromptCompilerError):
        compile_creative_sample_visual_prompts(synthetic_spec, _request(synthetic_spec))


def test_schema_registry_appends_only_the_two_formal_top_level_contracts() -> None:
    from sdc.schemas import MODELS

    assert len(MODELS) == 70
    assert [model.__name__ for model in MODELS[-2:]] == [
        "CreativeSampleVisualPromptCompileRequestV1",
        "CreativeSampleVisualPromptSidecarV1",
    ]
    request_path = ROOT / "schemas/CreativeSampleVisualPromptCompileRequestV1.schema.json"
    sidecar_path = ROOT / "schemas/CreativeSampleVisualPromptSidecarV1.schema.json"
    assert request_path.is_file()
    assert sidecar_path.is_file()

    request_schema = json.loads(request_path.read_bytes())
    sidecar_schema = json.loads(sidecar_path.read_bytes())
    assert len(request_schema["required"]) == 32
    assert set(request_schema["required"]) == REQUEST_FIELDS
    assert len(sidecar_schema["required"]) == 31
    assert set(sidecar_schema["required"]) == SIDECAR_FIELDS

    receipt_definitions = [
        definition
        for definition in sidecar_schema["$defs"].values()
        if set(definition.get("properties", {})) == RECEIPT_FIELDS
    ]
    assert len(receipt_definitions) == 1
    receipt_schema = receipt_definitions[0]
    assert len(receipt_schema["required"]) == 32
    assert set(receipt_schema["required"]) == RECEIPT_FIELDS
