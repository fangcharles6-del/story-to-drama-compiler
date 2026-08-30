from __future__ import annotations

import ast
import builtins
import hashlib
import importlib
import inspect
import json
import os
import random
import secrets
import socket
import time
import unicodedata
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sdc import visual_reference_prompt_compiler as compiler_module
from sdc.contracts import (
    CANARY_MODEL,
    CANARY_PROVIDER,
    CanaryExecution,
    CharacterAssetVersion,
    CharacterBible,
    GenerationJob,
    JobGraph,
    ProviderRequest,
    SceneAssetVersion,
    SceneBible,
    provider_request_fingerprint,
)
from sdc.visual_prompt_catalog import VISUAL_PROMPT_CATALOG
from sdc.visual_prompt_profiles import (
    PROFILE_SHA256_DOMAIN,
    PROMPT_RENDER_RECEIPT_SHA256_DOMAIN,
    RENDER_INPUT_SHA256_DOMAIN,
    prompt_profile_catalog_sha256,
)
from sdc.visual_reference_prompt_compiler import (
    VISUAL_REFERENCE_PROMPT_COMPILER_ARTIFACT_SHA256_DOMAIN,
    CreativeSampleReferenceVisualPromptArtifactV1,
    CreativeSampleReferenceVisualPromptCompileRequestV1,
    VisualReferencePromptCompilerError,
    compile_creative_sample_reference_visual_prompt,
    creative_sample_reference_visual_prompt_artifact_projection,
    creative_sample_reference_visual_prompt_artifact_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PACKET_PATH = (
    ROOT / "tests/fixtures/visual_prompt_profiles/reference-compiler/"
    "reviewed-known-answer-source-v1.json"
)
ADR041_PACKET_PATH = (
    ROOT / "tests/fixtures/visual_prompt_profiles/compiler-integration/"
    "reviewed-known-answer-v1.json"
)
SOURCE_PACKET_SHA256 = "be072fe5be5ef4b35c2e482db3e60c14641bce8cf80eb95398d9a4468750170c"
SOURCE_PACKET_SIZE_BYTES = 14_587
ADR041_PACKET_SHA256 = "40b42f406f76fef0a07f1a810d7ff4853f7f765edd48e8e998d1504fdfc0336e"
ADR041_PACKET_SIZE_BYTES = 26_163
ARTIFACT_DOMAIN = b"sdc:visual-prompt-reference-compiler-artifact:v1\0"
RECEIPT_DOMAIN = b"sdc:visual-prompt-render-receipt:v1\0"

CASE_IDS = (
    "character-reference-basic",
    "character-reference-unicode-nfc",
    "scene-reference-basic-empty-props",
    "scene-reference-unicode-nfc-multi-props",
)
REQUEST_FIELDS = {
    "schema_version",
    "request_purpose",
    "source_contract",
    "selection_scope",
    "asset_purpose",
    "subject_id",
    "expected_active_asset_version_id",
    "expected_active_asset_content_sha256",
    "reference_source",
    "catalog_version",
    "catalog_sha256",
    "profile_id",
    "profile_version",
    "profile_sha256",
    "selection_decision_kind",
    "selection_decision_ref",
    "authoring_decision_kind",
    "authoring_decision_ref",
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
ARTIFACT_FIELDS = {
    "schema_version",
    "artifact_purpose",
    "source_contract",
    "selection_scope",
    "asset_purpose",
    "subject_id",
    "expected_active_asset_version_id",
    "expected_active_asset_content_sha256",
    "reference_source",
    "selection_decision_kind",
    "selection_decision_ref",
    "authoring_decision_kind",
    "authoring_decision_ref",
    "profile_snapshot",
    "render_input",
    "render_input_sha256",
    "prompt",
    "prompt_sha256",
    "prompt_size_bytes",
    "prompt_render_receipt",
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
    "artifact_sha256",
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


def _canonical_document(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_compact(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _semantic_sha256(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_compact(value)).hexdigest()


def _source_packet() -> dict[str, Any]:
    value = json.loads(SOURCE_PACKET_PATH.read_bytes())
    assert type(value) is dict
    return value


def _source_cases() -> list[dict[str, Any]]:
    cases = _source_packet()["cases"]
    assert type(cases) is list
    return cases


def _subject(case: dict[str, Any]) -> CharacterBible | SceneBible:
    if case["request"]["asset_purpose"] == "CHARACTER_REFERENCE_ASSET":
        return CharacterBible.model_validate(case["subject"])
    return SceneBible.model_validate(case["subject"])


def _request(
    case: dict[str, Any],
    **updates: object,
) -> CreativeSampleReferenceVisualPromptCompileRequestV1:
    payload = deepcopy(case["request"])
    payload.update(updates)
    return CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
        _canonical_compact(payload)
    )


@pytest.fixture(scope="module")
def compiled_cases() -> list[
    tuple[
        dict[str, Any],
        CharacterBible | SceneBible,
        CreativeSampleReferenceVisualPromptCompileRequestV1,
        CreativeSampleReferenceVisualPromptArtifactV1,
    ]
]:
    result = []
    for case in _source_cases():
        subject = _subject(case)
        request = _request(case)
        artifact = compile_creative_sample_reference_visual_prompt(subject, request)
        result.append((case, subject, request, artifact))
    return result


def _assert_zero_authority(payload: dict[str, Any]) -> None:
    assert payload["current_gate"] == "HUMAN_GATE"
    assert payload["provider_state"] == "NOT_AUTHORIZED"
    assert payload["usage_restriction"] == "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
    for field in FALSE_AUTHORITY_FIELDS:
        assert payload[field] is False
    for field in ZERO_AUTHORITY_FIELDS:
        assert type(payload[field]) is int and payload[field] == 0


def _mutate(value: object) -> object:
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        if len(value) == 64 and set(value) <= set("0123456789abcdef"):
            return ("1" if value[0] != "1" else "0") + value[1:]
        return value + "-mutated"
    if type(value) is list:
        items = deepcopy(value)
        if items:
            items[0] = _mutate(items[0])
        else:
            items.append("mutated")
        return items
    if type(value) is dict:
        result = deepcopy(value)
        key = sorted(result)[0]
        result[key] = _mutate(result[key])
        return result
    raise AssertionError(f"unsupported mutation type: {type(value)!r}")


def _semantic_leaf_paths(
    value: object,
    path: tuple[str | int, ...] = (),
) -> Iterator[tuple[str | int, ...]]:
    if type(value) is dict:
        mapping = value
        if not mapping:
            yield path
        for key in sorted(mapping):
            yield from _semantic_leaf_paths(mapping[key], (*path, key))
        return
    if type(value) is list:
        items = value
        if not items:
            yield path
        for index, item in enumerate(items):
            yield from _semantic_leaf_paths(item, (*path, index))
        return
    yield path


def _mutate_at_path(value: dict[str, Any], path: tuple[str | int, ...]) -> dict[str, Any]:
    result = deepcopy(value)
    current: Any = result
    for part in path[:-1]:
        current = current[part]
    final = path[-1]
    current[final] = _mutate(current[final])
    return result


def _leaf_strings(value: object) -> Iterator[str]:
    if type(value) is str:
        yield value
    elif type(value) is list:
        for item in value:
            yield from _leaf_strings(item)
    elif type(value) is dict:
        for item in value.values():
            yield from _leaf_strings(item)


def test_source_packet_is_exact_canonical_synthetic_input() -> None:
    raw = SOURCE_PACKET_PATH.read_bytes()
    value = _source_packet()

    assert len(raw) == SOURCE_PACKET_SIZE_BYTES
    assert hashlib.sha256(raw).hexdigest() == SOURCE_PACKET_SHA256
    assert raw == _canonical_document(value)
    assert raw.endswith(b"\n") and b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf")
    assert unicodedata.normalize("NFC", raw.decode("utf-8")) == raw.decode("utf-8")
    assert set(value) == {"cases", "known_answer_version"}
    assert value["known_answer_version"] == "1.0.0"
    assert tuple(case["case_id"] for case in value["cases"]) == CASE_IDS
    for case in value["cases"]:
        assert set(case) == {"case_id", "request", "subject"}
        assert set(case["request"]) == REQUEST_FIELDS
        _subject(case)


def test_public_surface_and_contract_fields_are_exact() -> None:
    assert compiler_module.__all__ == [
        "CreativeSampleReferenceVisualPromptCompileRequestV1",
        "CreativeSampleReferenceVisualPromptArtifactV1",
        "VisualReferencePromptCompilerError",
        "VISUAL_REFERENCE_PROMPT_COMPILER_ARTIFACT_SHA256_DOMAIN",
        "compile_creative_sample_reference_visual_prompt",
        "creative_sample_reference_visual_prompt_artifact_projection",
        "creative_sample_reference_visual_prompt_artifact_sha256",
    ]
    assert VISUAL_REFERENCE_PROMPT_COMPILER_ARTIFACT_SHA256_DOMAIN == ARTIFACT_DOMAIN
    assert set(CreativeSampleReferenceVisualPromptCompileRequestV1.model_fields) == REQUEST_FIELDS
    assert set(CreativeSampleReferenceVisualPromptArtifactV1.model_fields) == ARTIFACT_FIELDS
    assert len(REQUEST_FIELDS) == 38
    assert len(ARTIFACT_FIELDS) == 41
    assert tuple(inspect.signature(compile_creative_sample_reference_visual_prompt).parameters) == (
        "subject",
        "request",
    )
    assert tuple(
        inspect.signature(creative_sample_reference_visual_prompt_artifact_projection).parameters
    ) == ("value",)
    assert tuple(
        inspect.signature(creative_sample_reference_visual_prompt_artifact_sha256).parameters
    ) == ("value",)
    for model in (
        CreativeSampleReferenceVisualPromptCompileRequestV1,
        CreativeSampleReferenceVisualPromptArtifactV1,
    ):
        assert model.model_config["frozen"] is True
        assert model.model_config["extra"] == "forbid"
        assert model.model_config["strict"] is True
        assert all(field.is_required() for field in model.model_fields.values())


def test_every_top_level_field_is_required_and_nested_values_are_frozen(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    case, _subject_value, request, artifact = compiled_cases[0]
    for field_name in REQUEST_FIELDS:
        payload = deepcopy(case["request"])
        del payload[field_name]
        with pytest.raises(ValidationError):
            CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
                _canonical_compact(payload)
            )

    artifact_payload = artifact.model_dump(mode="json")
    for field_name in ARTIFACT_FIELDS:
        payload = deepcopy(artifact_payload)
        del payload[field_name]
        with pytest.raises(ValidationError):
            CreativeSampleReferenceVisualPromptArtifactV1.model_validate_json(
                _canonical_compact(payload)
            )

    frozen_values = (
        request,
        request.reference_source,
        artifact,
        artifact.profile_snapshot,
        artifact.render_input,
        artifact.prompt_render_receipt,
    )
    for value in frozen_values:
        field_name = next(iter(type(value).model_fields))
        with pytest.raises(ValidationError, match="frozen"):
            setattr(value, field_name, getattr(value, field_name))


def test_four_cases_compile_deterministically_with_exact_source_mapping(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    assert tuple(case[0]["case_id"] for case in compiled_cases) == CASE_IDS
    for _case, subject, request, artifact in compiled_cases:
        assert artifact == compile_creative_sample_reference_visual_prompt(subject, request)
        payload = artifact.model_dump(mode="json")
        request_payload = request.model_dump(mode="json")
        assert set(payload) == ARTIFACT_FIELDS
        _assert_zero_authority(request_payload)
        _assert_zero_authority(payload)
        _assert_zero_authority(payload["prompt_render_receipt"])
        assert payload["reference_source"] == request_payload["reference_source"]
        assert payload["subject_id"] == request_payload["subject_id"]
        assert (
            payload["expected_active_asset_version_id"]
            == (request_payload["expected_active_asset_version_id"])
        )
        assert (
            payload["expected_active_asset_content_sha256"]
            == (request_payload["expected_active_asset_content_sha256"])
        )
        prompt_bytes = payload["prompt"].encode("utf-8")
        assert payload["prompt"].endswith("\n")
        assert "\r" not in payload["prompt"]
        assert payload["prompt_size_bytes"] == len(prompt_bytes)
        assert payload["prompt_sha256"] == hashlib.sha256(prompt_bytes).hexdigest()
        assert (
            CreativeSampleReferenceVisualPromptArtifactV1.model_validate_json(
                artifact.model_dump_json()
            )
            == artifact
        )

        source = request_payload["reference_source"]
        render_input = payload["render_input"]
        active_asset = next(
            item for item in subject.asset_versions if item.id == subject.active_asset_version_id
        )
        assert render_input["narrative"] == source["narrative"]
        assert render_input["visual_direction"] == source["visual_direction"]
        assert render_input["action"] == source["action"]
        assert render_input["continuity_notes"] == source["continuity_notes"]
        if request.asset_purpose == "CHARACTER_REFERENCE_ASSET":
            assert render_input["emotion_by_character"] == {
                request.subject_id: source["emotion_direction"]
            }
            assert render_input["wardrobe_by_character"] == {
                request.subject_id: source["wardrobe_direction"]
            }
            assert payload["profile_snapshot"]["reference_asset_types"] == [
                "CHARACTER_IDENTITY_SHEET",
                "CHARACTER_POSE_REFERENCE",
                "CHARACTER_EXPRESSION_REFERENCE",
            ]
            assert len(render_input["character_asset_bindings"]) == 1
            binding = render_input["character_asset_bindings"][0]
            assert binding == {
                "asset_content_sha256": active_asset.content_sha256,
                "asset_version_id": active_asset.id,
                "character_id": subject.character_id,
            }
        else:
            assert render_input["props"] == source["props"]
            assert payload["profile_snapshot"]["reference_asset_types"] == [
                "SCENE_ESTABLISHING_REFERENCE",
                "SCENE_LIGHTING_REFERENCE",
                "SCENE_MATERIAL_REFERENCE",
                "SCENE_PROP_PLACEMENT_REFERENCE",
            ]
            assert set(render_input["scene_asset_binding"]) == {
                "asset_content_sha256",
                "asset_version_id",
                "scene_id",
            }
            assert render_input["scene_asset_binding"] == {
                "asset_content_sha256": active_asset.content_sha256,
                "asset_version_id": active_asset.id,
                "scene_id": subject.scene_id,
            }
        assert active_asset.id == request.expected_active_asset_version_id
        assert active_asset.content_sha256 == request.expected_active_asset_content_sha256

        constraints = payload["profile_snapshot"]["constraint_set"]
        assert all(item in payload["prompt"] for item in constraints["positive_prompt_constraints"])
        assert all(item in payload["prompt"] for item in constraints["negative_prompt_constraints"])
        assert all(item not in payload["prompt"] for item in constraints["qc_expectations"])
        assert "provider_syntax_compatibility" not in json.dumps(payload, ensure_ascii=False)


@pytest.mark.parametrize(
    "case_index",
    (0, 2),
    ids=("character", "scene"),
)
def test_active_binding_profile_admission_and_rendering_follow_accepted_order(
    monkeypatch: pytest.MonkeyPatch,
    case_index: int,
) -> None:
    case = _source_cases()[case_index]
    subject = _subject(case)
    request = _request(case)
    events: list[str] = []

    original_subject_validation = compiler_module._revalidate_subject
    original_request_validation = compiler_module._revalidate_request
    original_active_binding = compiler_module._derive_active_binding
    original_resolver = compiler_module.resolve_visual_prompt_profile
    original_snapshot_contract = compiler_module._snapshot_contract
    original_render_input = compiler_module._derive_render_input
    original_renderer = compiler_module.render_visual_prompt

    def record_subject_validation(*args: Any, **kwargs: Any) -> Any:
        result = original_subject_validation(*args, **kwargs)
        events.append("subject-bible-revalidation")
        return result

    def record_request_validation(*args: Any, **kwargs: Any) -> Any:
        result = original_request_validation(*args, **kwargs)
        events.append("request-zero-authority-revalidation")
        return result

    def record_active_binding(*args: Any, **kwargs: Any) -> Any:
        result = original_active_binding(*args, **kwargs)
        events.append("active-binding-closure")
        return result

    def record_resolver(*args: Any, **kwargs: Any) -> Any:
        result = original_resolver(*args, **kwargs)
        events.append("five-value-profile-resolution")
        return result

    def record_snapshot_contract(*args: Any, **kwargs: Any) -> Any:
        result = original_snapshot_contract(*args, **kwargs)
        events.append("profile-purpose-recipe-role-closure")
        return result

    def record_render_input(*args: Any, **kwargs: Any) -> Any:
        result = original_render_input(*args, **kwargs)
        events.append("render-input-construction")
        return result

    def record_renderer(*args: Any, **kwargs: Any) -> Any:
        result = original_renderer(*args, **kwargs)
        events.append("prompt-receipt-rendering")
        return result

    monkeypatch.setattr(compiler_module, "_revalidate_subject", record_subject_validation)
    monkeypatch.setattr(compiler_module, "_revalidate_request", record_request_validation)
    monkeypatch.setattr(compiler_module, "_derive_active_binding", record_active_binding)
    monkeypatch.setattr(compiler_module, "resolve_visual_prompt_profile", record_resolver)
    monkeypatch.setattr(compiler_module, "_snapshot_contract", record_snapshot_contract)
    monkeypatch.setattr(compiler_module, "_derive_render_input", record_render_input)
    monkeypatch.setattr(compiler_module, "render_visual_prompt", record_renderer)

    artifact = compile_creative_sample_reference_visual_prompt(subject, request)

    assert artifact.subject_id == request.subject_id
    assert events == [
        "subject-bible-revalidation",
        "request-zero-authority-revalidation",
        "active-binding-closure",
        "five-value-profile-resolution",
        "profile-purpose-recipe-role-closure",
        "render-input-construction",
        "prompt-receipt-rendering",
    ]


def test_artifact_projection_and_domain_are_explicit_and_complete(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    for _case, _subject_value, _request_value, artifact in compiled_cases:
        payload = artifact.model_dump(mode="json")
        expected = {key: payload[key] for key in payload if key != "artifact_sha256"}
        projection = creative_sample_reference_visual_prompt_artifact_projection(artifact)
        assert projection == expected
        assert set(projection) == ARTIFACT_FIELDS - {"artifact_sha256"}
        digest = _semantic_sha256(ARTIFACT_DOMAIN, expected)
        assert digest == artifact.artifact_sha256
        assert creative_sample_reference_visual_prompt_artifact_sha256(artifact) == digest

        paths = tuple(_semantic_leaf_paths(expected))
        assert len(paths) >= 100
        for path in paths:
            mutated_projection = _mutate_at_path(expected, path)
            assert (
                _semantic_sha256(
                    ARTIFACT_DOMAIN,
                    mutated_projection,
                )
                != artifact.artifact_sha256
            )
            mutated = {**mutated_projection, "artifact_sha256": artifact.artifact_sha256}
            with pytest.raises(ValidationError):
                CreativeSampleReferenceVisualPromptArtifactV1.model_validate_json(
                    _canonical_compact(mutated)
                )


def test_existing_profile_input_receipt_and_catalog_domains_are_reused_exactly(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    assert PROFILE_SHA256_DOMAIN == b"sdc:visual-prompt-profile:v1\0"
    assert RENDER_INPUT_SHA256_DOMAIN == b"sdc:visual-prompt-render-input:v1\0"
    assert PROMPT_RENDER_RECEIPT_SHA256_DOMAIN == (b"sdc:visual-prompt-render-receipt:v1\0")
    assert ARTIFACT_DOMAIN != b"sdc:visual-prompt-compiler-sidecar:v1\0"
    assert "stable_id" not in inspect.getsource(compiler_module)

    catalog_digest = prompt_profile_catalog_sha256(VISUAL_PROMPT_CATALOG)
    for _case, _subject_value, _request_value, artifact in compiled_cases:
        payload = artifact.model_dump(mode="json")
        snapshot = payload["profile_snapshot"]
        profile_projection = {
            key: value
            for key, value in snapshot.items()
            if key not in {"catalog_sha256", "catalog_version", "profile_sha256"}
        }
        assert snapshot["profile_sha256"] == _semantic_sha256(
            PROFILE_SHA256_DOMAIN,
            profile_projection,
        )
        assert payload["render_input_sha256"] == _semantic_sha256(
            RENDER_INPUT_SHA256_DOMAIN,
            payload["render_input"],
        )
        receipt = payload["prompt_render_receipt"]
        assert receipt["prompt_render_receipt_sha256"] == _semantic_sha256(
            PROMPT_RENDER_RECEIPT_SHA256_DOMAIN,
            {key: value for key, value in receipt.items() if key != "prompt_render_receipt_sha256"},
        )
        assert snapshot["catalog_sha256"] == catalog_digest
        assert receipt["catalog_sha256"] == catalog_digest


def test_local_rerender_rejects_self_consistent_forged_prompt(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    artifact = compiled_cases[0][3]
    payload = artifact.model_dump(mode="json")
    forged_prompt = "Forged but internally rehashed Prompt.\n"
    forged_bytes = forged_prompt.encode("utf-8")
    payload["prompt"] = forged_prompt
    payload["prompt_sha256"] = hashlib.sha256(forged_bytes).hexdigest()
    payload["prompt_size_bytes"] = len(forged_bytes)
    receipt = payload["prompt_render_receipt"]
    receipt["prompt_sha256"] = payload["prompt_sha256"]
    receipt["prompt_size_bytes"] = payload["prompt_size_bytes"]
    receipt["prompt_render_receipt_sha256"] = _semantic_sha256(
        RECEIPT_DOMAIN,
        {key: value for key, value in receipt.items() if key != "prompt_render_receipt_sha256"},
    )
    payload["artifact_sha256"] = _semantic_sha256(
        ARTIFACT_DOMAIN,
        {key: value for key, value in payload.items() if key != "artifact_sha256"},
    )

    with pytest.raises(ValidationError):
        CreativeSampleReferenceVisualPromptArtifactV1.model_validate_json(
            _canonical_compact(payload)
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("catalog_version", "9.9.9"),
        ("catalog_sha256", "0" * 64),
        ("profile_id", "sdc.unknown-reference-profile.v1"),
        ("profile_version", "9.9.9"),
        ("profile_sha256", "1" * 64),
    ),
)
def test_exact_five_value_selection_fails_without_fallback(
    field: str,
    replacement: str,
) -> None:
    case = _source_cases()[0]
    subject = _subject(case)
    request = _request(case, **{field: replacement})
    with pytest.raises(VisualReferencePromptCompilerError) as caught:
        compile_creative_sample_reference_visual_prompt(subject, request)
    assert caught.value.__cause__ is not None


def test_entrypoint_and_public_helpers_revalidate_forged_values(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    _case, subject, request, artifact = compiled_cases[0]
    forged_request = request.model_copy(update={"profile_sha256": "0" * 64})
    with pytest.raises(VisualReferencePromptCompilerError) as request_error:
        compile_creative_sample_reference_visual_prompt(subject, forged_request)
    assert request_error.value.__cause__ is not None

    forged_artifact = artifact.model_copy(update={"artifact_sha256": "0" * 64})
    for helper in (
        creative_sample_reference_visual_prompt_artifact_projection,
        creative_sample_reference_visual_prompt_artifact_sha256,
    ):
        with pytest.raises(VisualReferencePromptCompilerError) as artifact_error:
            helper(forged_artifact)
        assert artifact_error.value.__cause__ is not None
        with pytest.raises(VisualReferencePromptCompilerError) as wrong_type_error:
            helper(object())  # type: ignore[arg-type]
        assert wrong_type_error.value.__cause__ is not None


def test_nested_model_copy_container_drift_and_subclasses_fail_closed(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    _case, subject, request, artifact = compiled_cases[2]
    forged_source = request.reference_source.model_copy(
        update={"props": list(request.reference_source.props)}
    )
    forged_request = request.model_copy(update={"reference_source": forged_source})
    with pytest.raises(VisualReferencePromptCompilerError) as request_error:
        compile_creative_sample_reference_visual_prompt(subject, forged_request)
    assert request_error.value.__cause__ is not None

    forged_input = artifact.render_input.model_copy(
        update={"props": list(artifact.render_input.props)}
    )
    forged_artifact = artifact.model_copy(update={"render_input": forged_input})
    for helper in (
        creative_sample_reference_visual_prompt_artifact_projection,
        creative_sample_reference_visual_prompt_artifact_sha256,
    ):
        with pytest.raises(VisualReferencePromptCompilerError) as artifact_error:
            helper(forged_artifact)
        assert artifact_error.value.__cause__ is not None

    class RequestSubclass(CreativeSampleReferenceVisualPromptCompileRequestV1):
        pass

    class ArtifactSubclass(CreativeSampleReferenceVisualPromptArtifactV1):
        pass

    subclass_request = RequestSubclass.model_validate_json(request.model_dump_json())
    with pytest.raises(VisualReferencePromptCompilerError) as subclass_request_error:
        compile_creative_sample_reference_visual_prompt(subject, subclass_request)
    assert subclass_request_error.value.__cause__ is not None

    subclass_artifact = ArtifactSubclass.model_validate_json(artifact.model_dump_json())
    for helper in (
        creative_sample_reference_visual_prompt_artifact_projection,
        creative_sample_reference_visual_prompt_artifact_sha256,
    ):
        with pytest.raises(VisualReferencePromptCompilerError) as subclass_artifact_error:
            helper(subclass_artifact)
        assert subclass_artifact_error.value.__cause__ is not None


@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings")
def test_python_scalar_subclasses_and_enum_storage_drift_fail_closed(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    class TextSubclass(str):
        pass

    class IntSubclass(int):
        pass

    _case, subject, request, artifact = compiled_cases[2]
    request_payload = request.model_dump(mode="python")
    assert (
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate(request_payload)
        == request
    )
    request_payload["subject_id"] = TextSubclass(request_payload["subject_id"])
    with pytest.raises(ValidationError):
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate(request_payload)

    forged_request = request.model_copy(update={"asset_purpose": "SCENE_REFERENCE_ASSET"})
    with pytest.raises(VisualReferencePromptCompilerError) as request_error:
        compile_creative_sample_reference_visual_prompt(subject, forged_request)
    assert request_error.value.__cause__ is not None

    forged_snapshot = artifact.profile_snapshot.model_copy(
        update={"asset_purpose": "SCENE_REFERENCE_ASSET"}
    )
    section = artifact.profile_snapshot.sections[0]
    enum_drift_snapshots = (
        forged_snapshot,
        artifact.profile_snapshot.model_copy(
            update={"shot_type": artifact.profile_snapshot.shot_type.value}
        ),
        artifact.profile_snapshot.model_copy(
            update={"visual_style_id": artifact.profile_snapshot.visual_style_id.value}
        ),
        artifact.profile_snapshot.model_copy(
            update={
                "narrative_contexts": tuple(
                    item.value for item in artifact.profile_snapshot.narrative_contexts
                )
            }
        ),
        artifact.profile_snapshot.model_copy(
            update={
                "reference_asset_types": tuple(
                    item.value for item in artifact.profile_snapshot.reference_asset_types
                )
            }
        ),
        artifact.profile_snapshot.model_copy(
            update={
                "sections": (
                    section.model_copy(update={"placeholder": section.placeholder.value}),
                    *artifact.profile_snapshot.sections[1:],
                )
            }
        ),
        artifact.profile_snapshot.model_copy(
            update={
                "reference_asset_recipe": (
                    artifact.profile_snapshot.reference_asset_recipe.model_copy(
                        update={
                            "recipe_kind": (
                                artifact.profile_snapshot.reference_asset_recipe.recipe_kind.value
                            )
                        }
                    )
                )
            }
        ),
    )
    enum_drift_input = artifact.render_input.model_copy(
        update={"input_kind": artifact.render_input.input_kind.value}
    )
    forged_artifacts = [
        artifact.model_copy(update={"profile_snapshot": snapshot})
        for snapshot in enum_drift_snapshots
    ]
    forged_artifacts.append(artifact.model_copy(update={"render_input": enum_drift_input}))
    for forged_artifact in forged_artifacts:
        for helper in (
            creative_sample_reference_visual_prompt_artifact_projection,
            creative_sample_reference_visual_prompt_artifact_sha256,
        ):
            with pytest.raises(VisualReferencePromptCompilerError) as snapshot_error:
                helper(forged_artifact)
            assert snapshot_error.value.__cause__ is not None

    artifact_payload = artifact.model_dump(mode="python")
    artifact_payload["prompt_size_bytes"] = IntSubclass(artifact.prompt_size_bytes)
    with pytest.raises(ValidationError):
        CreativeSampleReferenceVisualPromptArtifactV1.model_validate(artifact_payload)

    render_input = artifact.render_input
    dynamic_map_input = render_input.model_copy(
        update={"emotion_by_character": {artifact.subject_id: "Neutral expression."}}
    )
    dynamic_map_artifact = artifact.model_copy(update={"render_input": dynamic_map_input})
    with pytest.raises(VisualReferencePromptCompilerError) as dynamic_map_error:
        creative_sample_reference_visual_prompt_artifact_projection(dynamic_map_artifact)
    assert dynamic_map_error.value.__cause__ is not None

    cyclic_payload = compiled_cases[0][2].model_dump(mode="python")
    cycle: list[object] = []
    cycle.append(cycle)
    cyclic_payload["reference_source"]["visual_direction"] = cycle
    with pytest.raises(ValidationError):
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate(cyclic_payload)


@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings")
def test_snapshot_recipe_and_full_role_tuples_fail_closed_when_forged(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    character_artifact = compiled_cases[0][3]
    scene_artifact = compiled_cases[2][3]

    for artifact, cross_recipe in (
        (character_artifact, scene_artifact.profile_snapshot.reference_asset_recipe),
        (scene_artifact, character_artifact.profile_snapshot.reference_asset_recipe),
    ):
        snapshot = artifact.profile_snapshot
        roles = snapshot.reference_asset_types
        forged_snapshots = (
            snapshot.model_copy(update={"reference_asset_types": roles[:-1]}),
            snapshot.model_copy(update={"reference_asset_types": tuple(reversed(roles))}),
            snapshot.model_copy(update={"reference_asset_recipe": cross_recipe}),
            snapshot.model_copy(
                update={
                    "reference_asset_recipe": snapshot.reference_asset_recipe.model_copy(
                        update={"reference_asset_types": roles[:-1]}
                    )
                }
            ),
            snapshot.model_copy(
                update={
                    "reference_asset_recipe": snapshot.reference_asset_recipe.model_copy(
                        update={"reference_asset_types": tuple(reversed(roles))}
                    )
                }
            ),
        )
        for forged_snapshot in forged_snapshots:
            forged_artifact = artifact.model_copy(update={"profile_snapshot": forged_snapshot})
            for helper in (
                creative_sample_reference_visual_prompt_artifact_projection,
                creative_sample_reference_visual_prompt_artifact_sha256,
            ):
                with pytest.raises(VisualReferencePromptCompilerError) as caught:
                    helper(forged_artifact)
                assert caught.value.__cause__ is not None


def test_expected_binding_is_only_a_fail_closed_cross_check() -> None:
    case = _source_cases()[0]
    subject = _subject(case)
    for field, replacement in (
        ("expected_active_asset_version_id", "character_asset_00000000000000000000"),
        ("expected_active_asset_content_sha256", "0" * 64),
    ):
        with pytest.raises(VisualReferencePromptCompilerError):
            compile_creative_sample_reference_visual_prompt(
                subject,
                _request(case, **{field: replacement}),
            )


@pytest.mark.parametrize(
    ("case_index", "field", "maximum"),
    [
        (0, "narrative", 4000),
        (0, "visual_direction", 4000),
        (0, "action", 2000),
        (0, "emotion_direction", 512),
        (0, "wardrobe_direction", 512),
        (0, "continuity_notes", 2000),
        (2, "narrative", 4000),
        (2, "visual_direction", 4000),
        (2, "action", 2000),
        (2, "continuity_notes", 2000),
    ],
)
def test_reference_source_text_bounds_are_exact(
    case_index: int,
    field: str,
    maximum: int,
) -> None:
    payload = deepcopy(_source_cases()[case_index]["request"])
    source = payload["reference_source"]
    source[field] = "x" * maximum
    CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
        _canonical_compact(payload)
    )
    for invalid in ("", "x" * (maximum + 1), " leading", "trailing "):
        source[field] = invalid
        with pytest.raises(ValidationError):
            CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
                _canonical_compact(payload)
            )


@pytest.mark.parametrize(
    "props",
    [
        ["duplicate", "duplicate"],
        ["zeta", "alpha"],
        [f"prop-{index:02d}" for index in range(17)],
        [""],
        ["x" * 129],
    ],
)
def test_scene_props_fail_closed_for_noncanonical_values(props: list[str]) -> None:
    payload = deepcopy(_source_cases()[2]["request"])
    payload["reference_source"]["props"] = props
    with pytest.raises(ValidationError):
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
            _canonical_compact(payload)
        )


def test_source_tag_purpose_subject_and_bible_variants_cannot_cross() -> None:
    character_case = _source_cases()[0]
    scene_case = _source_cases()[2]

    payload = deepcopy(character_case["request"])
    payload["reference_source"]["source_kind"] = "UNKNOWN_REFERENCE_SOURCE"
    with pytest.raises(ValidationError):
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
            _canonical_compact(payload)
        )

    payload = deepcopy(character_case["request"])
    payload["reference_source"] = deepcopy(scene_case["request"]["reference_source"])
    with pytest.raises(ValidationError):
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
            _canonical_compact(payload)
        )

    with pytest.raises(VisualReferencePromptCompilerError):
        compile_creative_sample_reference_visual_prompt(
            _subject(scene_case),
            _request(character_case),
        )
    with pytest.raises(VisualReferencePromptCompilerError):
        compile_creative_sample_reference_visual_prompt(
            _subject(character_case),
            _request(scene_case),
        )
    with pytest.raises(VisualReferencePromptCompilerError):
        compile_creative_sample_reference_visual_prompt(
            _subject(character_case),
            _request(character_case, subject_id="character-mismatch"),
        )


def _character_bible_with_version_count(subject: CharacterBible, count: int) -> CharacterBible:
    versions = [subject.asset_versions[0]]
    for version in range(2, count + 1):
        content_sha256 = hashlib.sha256(f"inactive-{version}".encode()).hexdigest()
        approval_ref = f"fixture-inactive-{version}"
        description = f"Synthetic inactive reference version {version}."
        asset_id = CharacterAssetVersion.derive_id(
            character_id=subject.character_id,
            version=version,
            content_sha256=content_sha256,
            media_type="image/png",
            approval_ref=approval_ref,
            visual_description=description,
        )
        versions.append(
            CharacterAssetVersion(
                schema_version="1.0.0",
                id=asset_id,
                character_id=subject.character_id,
                version=version,
                content_sha256=content_sha256,
                media_type="image/png",
                approval_ref=approval_ref,
                visual_description=description,
                provenance="IMPORTED_APPROVED_MEDIA",
            )
        )
    return CharacterBible(
        schema_version="1.0.0",
        character_id=subject.character_id,
        name=subject.name,
        visual_description=subject.visual_description,
        asset_versions=tuple(versions),
        active_asset_version_id=subject.active_asset_version_id,
    )


def _scene_bible_with_version_count(subject: SceneBible, count: int) -> SceneBible:
    versions = [subject.asset_versions[0]]
    for version in range(2, count + 1):
        content_sha256 = hashlib.sha256(f"scene-inactive-{version}".encode()).hexdigest()
        approval_ref = f"fixture-scene-inactive-{version}"
        description = f"Synthetic inactive scene reference version {version}."
        asset_id = SceneAssetVersion.derive_id(
            scene_id=subject.scene_id,
            version=version,
            content_sha256=content_sha256,
            media_type="image/png",
            approval_ref=approval_ref,
            visual_description=description,
        )
        versions.append(
            SceneAssetVersion(
                schema_version="1.0.0",
                id=asset_id,
                scene_id=subject.scene_id,
                version=version,
                content_sha256=content_sha256,
                media_type="image/png",
                approval_ref=approval_ref,
                visual_description=description,
                provenance="IMPORTED_APPROVED_MEDIA",
            )
        )
    return SceneBible(
        schema_version="1.0.0",
        scene_id=subject.scene_id,
        ordinal=subject.ordinal,
        name=subject.name,
        visual_description=subject.visual_description,
        asset_versions=tuple(versions),
        active_asset_version_id=subject.active_asset_version_id,
    )


def test_bible_resource_count_and_inactive_history_equivalence(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    case, subject, request, baseline = compiled_cases[0]
    assert type(subject) is CharacterBible
    sixty_four = _character_bible_with_version_count(subject, 64)
    assert compile_creative_sample_reference_visual_prompt(sixty_four, request) == baseline
    sixty_five = _character_bible_with_version_count(subject, 65)
    with pytest.raises(VisualReferencePromptCompilerError):
        compile_creative_sample_reference_visual_prompt(sixty_five, _request(case))

    scene_case, scene_subject, scene_request, scene_baseline = compiled_cases[2]
    assert type(scene_subject) is SceneBible
    scene_sixty_four = _scene_bible_with_version_count(scene_subject, 64)
    assert (
        compile_creative_sample_reference_visual_prompt(scene_sixty_four, scene_request)
        == scene_baseline
    )
    scene_sixty_five = _scene_bible_with_version_count(scene_subject, 65)
    with pytest.raises(VisualReferencePromptCompilerError):
        compile_creative_sample_reference_visual_prompt(
            scene_sixty_five,
            _request(scene_case),
        )


def test_active_asset_closure_rejects_forged_character_and_scene_bibles(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    for case, subject, request, _artifact in (compiled_cases[0], compiled_cases[2]):
        active = subject.asset_versions[0]
        forged_subjects = [
            subject.model_copy(update={"active_asset_version_id": "missing-active-version"}),
            subject.model_copy(update={"asset_versions": (active, active)}),
        ]
        binding_field = "character_id" if type(subject) is CharacterBible else "scene_id"
        for update in (
            {"id": "forged-active-version-id"},
            {binding_field: "cross-bible-subject"},
            {"media_type": "image/jpeg"},
            {"provenance": "GENERATED_MEDIA"},
            {"content_sha256": "G" * 64},
        ):
            forged_asset = active.model_copy(update=update)
            forged_subjects.append(subject.model_copy(update={"asset_versions": (forged_asset,)}))

        for forged_subject in forged_subjects:
            with pytest.raises(VisualReferencePromptCompilerError) as caught:
                compile_creative_sample_reference_visual_prompt(forged_subject, request)
            assert caught.value.__cause__ is not None

        if type(subject) is CharacterBible:
            two_versions: CharacterBible | SceneBible = _character_bible_with_version_count(
                subject,
                2,
            )
        else:
            two_versions = _scene_bible_with_version_count(subject, 2)
        changed_active = two_versions.model_copy(
            update={"active_asset_version_id": two_versions.asset_versions[1].id}
        )
        with pytest.raises(VisualReferencePromptCompilerError):
            compile_creative_sample_reference_visual_prompt(
                changed_active,
                _request(case),
            )


def test_bible_text_and_approval_ref_never_flow_into_prompt() -> None:
    case = _source_cases()[0]
    original = _subject(case)
    assert type(original) is CharacterBible
    marker = "SENTINEL_DO_NOT_COPY_TO_PROMPT"
    name = f"{marker} Name"
    bible_description = f"{marker} Bible description."
    character_id = CharacterBible.derive_id(name=name, visual_description=bible_description)
    asset_description = f"{marker} Asset description."
    approval_ref = "SENTINEL_APPROVAL_DO_NOT_COPY"
    content_sha256 = original.asset_versions[0].content_sha256
    asset_id = CharacterAssetVersion.derive_id(
        character_id=character_id,
        version=1,
        content_sha256=content_sha256,
        media_type="image/png",
        approval_ref=approval_ref,
        visual_description=asset_description,
    )
    asset = CharacterAssetVersion(
        schema_version="1.0.0",
        id=asset_id,
        character_id=character_id,
        version=1,
        content_sha256=content_sha256,
        media_type="image/png",
        approval_ref=approval_ref,
        visual_description=asset_description,
        provenance="IMPORTED_APPROVED_MEDIA",
    )
    subject = CharacterBible(
        schema_version="1.0.0",
        character_id=character_id,
        name=name,
        visual_description=bible_description,
        asset_versions=(asset,),
        active_asset_version_id=asset.id,
    )
    request = _request(
        case,
        subject_id=character_id,
        expected_active_asset_version_id=asset.id,
        expected_active_asset_content_sha256=asset.content_sha256,
    )
    artifact = compile_creative_sample_reference_visual_prompt(subject, request)
    assert marker not in artifact.prompt
    assert approval_ref not in artifact.prompt


def test_scene_bible_text_and_approval_ref_never_flow_into_prompt() -> None:
    case = _source_cases()[2]
    original = _subject(case)
    assert type(original) is SceneBible
    marker = "SCENE_SENTINEL_DO_NOT_COPY_TO_PROMPT"
    name = f"{marker} Name"
    bible_description = f"{marker} Bible description."
    scene_id = SceneBible.derive_id(
        ordinal=original.ordinal,
        name=name,
        visual_description=bible_description,
    )
    asset_description = f"{marker} Asset description."
    approval_ref = "SCENE_SENTINEL_APPROVAL_DO_NOT_COPY"
    content_sha256 = original.asset_versions[0].content_sha256
    asset_id = SceneAssetVersion.derive_id(
        scene_id=scene_id,
        version=1,
        content_sha256=content_sha256,
        media_type="image/png",
        approval_ref=approval_ref,
        visual_description=asset_description,
    )
    asset = SceneAssetVersion(
        schema_version="1.0.0",
        id=asset_id,
        scene_id=scene_id,
        version=1,
        content_sha256=content_sha256,
        media_type="image/png",
        approval_ref=approval_ref,
        visual_description=asset_description,
        provenance="IMPORTED_APPROVED_MEDIA",
    )
    subject = SceneBible(
        schema_version="1.0.0",
        scene_id=scene_id,
        ordinal=original.ordinal,
        name=name,
        visual_description=bible_description,
        asset_versions=(asset,),
        active_asset_version_id=asset.id,
    )
    request = _request(
        case,
        subject_id=scene_id,
        expected_active_asset_version_id=asset.id,
        expected_active_asset_content_sha256=asset.content_sha256,
    )
    artifact = compile_creative_sample_reference_visual_prompt(subject, request)
    assert marker not in artifact.prompt
    assert approval_ref not in artifact.prompt


def test_unknown_fields_and_scalar_coercion_are_rejected_at_formal_boundaries(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    case, _subject, _request_value, artifact = compiled_cases[0]
    request_payload = deepcopy(case["request"])
    invalid_request_payloads = []
    extra_request = deepcopy(request_payload)
    extra_request["unexpected"] = "forbidden"
    invalid_request_payloads.append(extra_request)
    coerced_version = deepcopy(request_payload)
    coerced_version["profile_version"] = 1
    invalid_request_payloads.append(coerced_version)
    coerced_zero = deepcopy(request_payload)
    coerced_zero["authorized_attempts"] = False
    invalid_request_payloads.append(coerced_zero)
    extra_source = deepcopy(request_payload)
    extra_source["reference_source"]["unexpected"] = "forbidden"
    invalid_request_payloads.append(extra_source)
    for payload in invalid_request_payloads:
        with pytest.raises(ValidationError):
            CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
                _canonical_compact(payload)
            )

    artifact_payload = artifact.model_dump(mode="json")
    invalid_artifact_payloads = []
    extra_artifact = deepcopy(artifact_payload)
    extra_artifact["unexpected"] = "forbidden"
    invalid_artifact_payloads.append(extra_artifact)
    coerced_size = deepcopy(artifact_payload)
    coerced_size["prompt_size_bytes"] = str(artifact.prompt_size_bytes)
    invalid_artifact_payloads.append(coerced_size)
    extra_receipt = deepcopy(artifact_payload)
    extra_receipt["prompt_render_receipt"]["unexpected"] = "forbidden"
    invalid_artifact_payloads.append(extra_receipt)
    coerced_receipt_size = deepcopy(artifact_payload)
    coerced_receipt_size["prompt_render_receipt"]["prompt_size_bytes"] = True
    invalid_artifact_payloads.append(coerced_receipt_size)
    for payload in invalid_artifact_payloads:
        with pytest.raises(ValidationError):
            CreativeSampleReferenceVisualPromptArtifactV1.model_validate_json(
                _canonical_compact(payload)
            )


def test_raw_json_admission_counts_bytes_and_rejects_ambiguous_documents(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    request = compiled_cases[0][2]
    request_value = request.model_dump(mode="json")
    request_raw = _canonical_document(request_value)
    assert (
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
            request_raw.decode("utf-8")
        )
        == request
    )
    assert (
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(request_raw)
        == request
    )
    assert (
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
            bytearray(request_raw)
        )
        == request
    )

    padded = request_raw + b" " * (262_144 - len(request_raw))
    assert len(padded) == 262_144
    assert (
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(padded) == request
    )
    with pytest.raises(ValidationError):
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(padded + b" ")

    duplicate = b'{"schema_version":"1.0.0",' + request_raw.lstrip()[1:]
    invalid_documents = (
        duplicate,
        b"\xef\xbb\xbf" + request_raw,
        request_raw[:-2] + b"\r\n",
        request_raw.replace(b'"authorized_cost_cny": 0', b'"authorized_cost_cny": NaN'),
        b"\xff" + request_raw,
    )
    for raw in invalid_documents:
        with pytest.raises(ValidationError):
            CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(raw)

    nfd = deepcopy(request_value)
    nfd["reference_source"]["narrative"] = "Cafe\u0301"
    with pytest.raises(ValidationError):
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
            _canonical_document(nfd)
        )

    artifact = compiled_cases[0][3]
    artifact_raw = _canonical_document(artifact.model_dump(mode="json"))
    padded_artifact = artifact_raw + b" " * (524_288 - len(artifact_raw))
    assert (
        CreativeSampleReferenceVisualPromptArtifactV1.model_validate_json(padded_artifact)
        == artifact
    )
    with pytest.raises(ValidationError):
        CreativeSampleReferenceVisualPromptArtifactV1.model_validate_json(padded_artifact + b" ")

    mutable_request = bytearray(request_raw)
    immutable_snapshot = compiler_module._raw_json_precheck(
        mutable_request,
        maximum=262_144,
    )
    mutable_request[0] = ord(" ")
    assert type(immutable_snapshot) is bytes
    assert immutable_snapshot == request_raw


def test_raw_and_in_memory_depth_breadth_and_persistent_size_boundaries(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    request = compiled_cases[0][2]
    artifact = compiled_cases[0][3]

    def nested_lists(count: int) -> object:
        value: object = 0
        for _index in range(count):
            value = [value]
        return value

    for model, original in (
        (
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            request.model_dump(mode="json"),
        ),
        (
            CreativeSampleReferenceVisualPromptArtifactV1,
            artifact.model_dump(mode="json"),
        ),
    ):
        depth_16 = deepcopy(original)
        depth_16["unexpected_depth_probe"] = nested_lists(15)
        with pytest.raises(ValidationError) as admitted_to_model_validation:
            model.model_validate_json(_canonical_compact(depth_16))
        assert any(
            item["type"] == "extra_forbidden"
            for item in admitted_to_model_validation.value.errors()
        )

        depth_17 = deepcopy(original)
        depth_17["unexpected_depth_probe"] = nested_lists(16)
        with pytest.raises(ValidationError) as rejected_by_depth_gate:
            model.model_validate_json(_canonical_compact(depth_17))
        assert rejected_by_depth_gate.value.__cause__ is not None
        assert "depth exceeds 16" in str(rejected_by_depth_gate.value.__cause__)

        breadth_65 = deepcopy(original)
        breadth_65["unexpected_breadth_probe"] = [None] * 65
        with pytest.raises(ValidationError) as rejected_by_breadth_gate:
            model.model_validate_json(_canonical_compact(breadth_65))
        assert rejected_by_breadth_gate.value.__cause__ is not None
        assert "exceeds 64 items" in str(rejected_by_breadth_gate.value.__cause__)

    nested_tuple: object = "leaf"
    for _index in range(15):
        nested_tuple = (nested_tuple,)
    depth_16_request = request.model_copy(update={"reference_source": nested_tuple})
    compiler_module._require_exact_model_storage(depth_16_request, field="request")

    nested_tuple = (nested_tuple,)
    depth_17_request = request.model_copy(update={"reference_source": nested_tuple})
    with pytest.raises(VisualReferencePromptCompilerError, match="exceeds 16"):
        compiler_module._require_exact_model_storage(depth_17_request, field="request")

    breadth_65_request = request.model_copy(update={"reference_source": tuple(range(65))})
    with pytest.raises(VisualReferencePromptCompilerError, match="exceeding 64"):
        compiler_module._require_exact_model_storage(breadth_65_request, field="request")

    hidden_storage_request = request.model_copy()
    hidden_storage_request.__dict__.update({f"unexpected_{index}": None for index in range(65)})
    with pytest.raises(VisualReferencePromptCompilerError, match="declared fields"):
        compiler_module._require_exact_model_storage(
            hidden_storage_request,
            field="request",
        )

    for maximum, field in (
        (262_144, "request"),
        (524_288, "Artifact"),
        (524_288, "subject Bible"),
    ):
        overhead = len(compiler_module._persistent_document_bytes({"padding": ""}))
        exact = {"padding": "x" * (maximum - overhead)}
        assert len(compiler_module._persistent_document_bytes(exact)) == maximum
        compiler_module._require_persistent_size(exact, maximum=maximum, field=field)
        oversized = {"padding": exact["padding"] + "x"}
        with pytest.raises(VisualReferencePromptCompilerError, match="byte limit"):
            compiler_module._require_persistent_size(
                oversized,
                maximum=maximum,
                field=field,
            )


def test_bible_and_prompt_resource_limits_fail_before_returning_an_artifact(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    _case, subject, request, artifact = compiled_cases[0]
    assert type(subject) is CharacterBible

    empty_subject = subject.model_copy(update={"asset_versions": ()})
    with pytest.raises(VisualReferencePromptCompilerError) as empty_error:
        compile_creative_sample_reference_visual_prompt(empty_subject, request)
    assert empty_error.value.__cause__ is not None

    long_description = "砖" * 4000
    versions = [subject.asset_versions[0]]
    for version in range(2, 65):
        content_sha256 = hashlib.sha256(f"large-{version}".encode()).hexdigest()
        approval_ref = f"large-{version}"
        asset_id = CharacterAssetVersion.derive_id(
            character_id=subject.character_id,
            version=version,
            content_sha256=content_sha256,
            media_type="image/png",
            approval_ref=approval_ref,
            visual_description=long_description,
        )
        versions.append(
            CharacterAssetVersion(
                id=asset_id,
                character_id=subject.character_id,
                version=version,
                content_sha256=content_sha256,
                media_type="image/png",
                approval_ref=approval_ref,
                visual_description=long_description,
                provenance="IMPORTED_APPROVED_MEDIA",
            )
        )
    oversized_bible = CharacterBible(
        character_id=subject.character_id,
        name=subject.name,
        visual_description=subject.visual_description,
        asset_versions=tuple(versions),
        active_asset_version_id=subject.active_asset_version_id,
    )
    assert (
        len(compiler_module._persistent_document_bytes(oversized_bible.model_dump(mode="json")))
        > 524_288
    )
    with pytest.raises(VisualReferencePromptCompilerError) as bible_error:
        compile_creative_sample_reference_visual_prompt(oversized_bible, request)
    assert bible_error.value.__cause__ is not None

    snapshot = artifact.profile_snapshot
    base_positive = tuple(f"P{index:02d}-" + "x" * 996 for index in range(30))
    base_negative = tuple(f"N{index:02d}-" + "x" * 996 for index in range(30))
    base_constraints = snapshot.constraint_set.model_copy(
        update={
            "positive_prompt_constraints": base_positive,
            "negative_prompt_constraints": base_negative,
        }
    )
    sized_snapshot = snapshot.model_copy(update={"constraint_set": base_constraints})
    base_prompt = compiler_module._render_formal_prompt_bytes(
        sized_snapshot,
        artifact.render_input,
    )
    remaining = 65_536 - len(base_prompt)
    extra_count = next(count for count in range(1, 5) if 7 * count <= remaining <= 1003 * count)
    content_bytes = remaining - 3 * extra_count
    extra_lengths: list[int] = []
    for index in range(extra_count):
        slots_left = extra_count - index - 1
        length = min(1000, content_bytes - 4 * slots_left)
        extra_lengths.append(length)
        content_bytes -= length
    assert content_bytes == 0
    extras = tuple(
        f"E{index:02d}-" + "z" * (length - 4) for index, length in enumerate(extra_lengths)
    )
    positive_slots = min(2, len(extras))
    exact_constraints = base_constraints.model_copy(
        update={
            "positive_prompt_constraints": base_positive + extras[:positive_slots],
            "negative_prompt_constraints": base_negative + extras[positive_slots:],
        }
    )
    exact_snapshot = snapshot.model_copy(update={"constraint_set": exact_constraints})
    exact_prompt = compiler_module._render_formal_prompt_bytes(
        exact_snapshot,
        artifact.render_input,
    )
    assert len(exact_prompt) == 65_536

    oversized_input = artifact.render_input.model_copy(
        update={"action": artifact.render_input.action + "x"}
    )
    with pytest.raises(VisualReferencePromptCompilerError, match="Prompt exceeds"):
        compiler_module._render_formal_prompt_bytes(exact_snapshot, oversized_input)

    invalid_minimum = artifact.model_dump(mode="json")
    invalid_minimum["prompt_size_bytes"] = 0
    with pytest.raises(ValidationError) as minimum_error:
        CreativeSampleReferenceVisualPromptArtifactV1.model_validate_json(
            _canonical_compact(invalid_minimum)
        )
    assert any(
        item["loc"] == ("prompt_size_bytes",) and item["type"] == "greater_than_equal"
        for item in minimum_error.value.errors()
    )


def test_artifact_validation_and_helpers_do_not_use_catalog_or_bible(
    monkeypatch: pytest.MonkeyPatch,
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    case, subject, request, artifact = compiled_cases[0]
    monkeypatch.setattr(compiler_module, "VISUAL_PROMPT_CATALOG", None)
    assert (
        CreativeSampleReferenceVisualPromptArtifactV1.model_validate_json(
            artifact.model_dump_json()
        )
        == artifact
    )
    assert (
        creative_sample_reference_visual_prompt_artifact_sha256(artifact)
        == artifact.artifact_sha256
    )
    with pytest.raises(VisualReferencePromptCompilerError):
        compile_creative_sample_reference_visual_prompt(subject, _request(case))
    assert request == _request(case)


def test_new_values_are_structurally_rejected_by_execution_contracts(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    _case, _subject_value, request, artifact = compiled_cases[0]
    job = GenerationJob(
        id="adr042-structural-job",
        shot_id="adr042-structural-shot",
        prompt="synthetic execution-contract control",
        duration_ms=4000,
        idempotency_key="adr042-structural-key",
    )
    graph = JobGraph(id="adr042-structural-graph", jobs=(job,))
    provider_draft = ProviderRequest(
        run_id="adr042-structural-run",
        job_id=job.id,
        attempt=1,
        provider=CANARY_PROVIDER,
        model=CANARY_MODEL,
        prompt=job.prompt,
        duration_ms=job.duration_ms,
        aspect_ratio="9:16",
        resolution="1080p",
        generate_audio=False,
        request_fingerprint="0" * 64,
    )
    provider_request = provider_draft.model_copy(
        update={"request_fingerprint": provider_request_fingerprint(provider_draft)}
    )
    execution = CanaryExecution(
        run_id=provider_request.run_id,
        graph=graph,
        request=provider_request,
    )
    for new_value in (request, artifact):
        invalid_payloads = (
            (
                GenerationJob,
                {**job.model_dump(mode="python"), "prompt": new_value},
            ),
            (
                JobGraph,
                {**graph.model_dump(mode="python"), "jobs": (new_value,)},
            ),
            (
                ProviderRequest,
                {
                    **provider_request.model_dump(mode="python"),
                    "input_materials": (new_value,),
                },
            ),
            (
                CanaryExecution,
                {**execution.model_dump(mode="python"), "request": new_value},
            ),
        )
        for model, payload in invalid_payloads:
            with pytest.raises(ValidationError):
                model.model_validate(payload)
    forbidden_fields = {
        "candidate",
        "media",
        "output_url",
        "local_media_path",
        "provider_id",
        "model_id",
        "task_id",
        "attempt",
        "retry_count",
        "qualification",
        "rights_manifest",
        "qc_result",
        "publication_state",
        "promotion_state",
    }
    assert not (ARTIFACT_FIELDS & forbidden_fields)


def test_all_public_validation_paths_deny_runtime_capability_inputs(
    monkeypatch: pytest.MonkeyPatch,
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    _case, subject, request, artifact = compiled_cases[0]
    request_payload = request.model_dump(mode="python")
    artifact_json = artifact.model_dump_json()

    def denied(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("ADR-042 runtime capability access is forbidden")

    for owner, name in (
        (builtins, "open"),
        (Path, "mkdir"),
        (Path, "open"),
        (Path, "write_bytes"),
        (Path, "write_text"),
        (os, "getenv"),
        (time, "time"),
        (time, "monotonic"),
        (random, "random"),
        (secrets, "token_bytes"),
        (socket, "socket"),
        (socket, "create_connection"),
        (importlib, "import_module"),
    ):
        monkeypatch.setattr(owner, name, denied)

    assert (
        CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate(request_payload)
        == request
    )
    assert (
        CreativeSampleReferenceVisualPromptArtifactV1.model_validate_json(artifact_json) == artifact
    )
    assert creative_sample_reference_visual_prompt_artifact_projection(artifact) == {
        key: value
        for key, value in artifact.model_dump(mode="json").items()
        if key != "artifact_sha256"
    }
    assert (
        creative_sample_reference_visual_prompt_artifact_sha256(artifact)
        == artifact.artifact_sha256
    )
    assert compile_creative_sample_reference_visual_prompt(subject, request) == artifact


def test_compiler_source_has_no_io_dynamic_execution_or_reverse_imports() -> None:
    source_path = Path(compiler_module.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    forbidden_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"open", "exec", "eval", "compile", "__import__"}:
                forbidden_calls.append(node.func.id)
    assert not imported_roots & {
        "asyncio",
        "httpx",
        "importlib",
        "os",
        "pathlib",
        "random",
        "requests",
        "secrets",
        "socket",
        "subprocess",
        "time",
        "urllib",
    }
    assert forbidden_calls == []
    assert "sdc.schemas" not in source
    assert not any(
        (isinstance(node, ast.Name) and node.id == "compile_creative_sample")
        or (isinstance(node, ast.Attribute) and node.attr == "compile_creative_sample")
        for node in ast.walk(tree)
    )

    allowed_reverse_imports = {
        ROOT / "src/sdc/generated_reference_candidate.py",
        ROOT / "src/sdc/generated_reference_asset_promotion.py",
        ROOT / "src/sdc/generated_reference_asset_promotion_codegen.py",
        ROOT / "src/sdc/generated_reference_rights_current_status.py",
        ROOT / "src/sdc/generated_reference_rights_current_status_codegen.py",
        ROOT / "src/sdc/schemas.py",
        ROOT / "src/sdc/visual_reference_prompt_compiler.py",
        ROOT / "src/sdc/visual_reference_prompt_compiler_codegen.py",
    }
    for path in (ROOT / "src/sdc").glob("*.py"):
        if path not in allowed_reverse_imports:
            assert "visual_reference_prompt_compiler" not in path.read_text(encoding="utf-8")


def test_existing_catalog_and_adr041_review_packet_are_unchanged() -> None:
    resolver_source = inspect.getsource(compiler_module.resolve_visual_prompt_profile)
    assert "compatibility" not in resolver_source
    assert "provider" not in resolver_source
    assert VISUAL_PROMPT_CATALOG.catalog_version == "1.0.0"
    assert (
        prompt_profile_catalog_sha256(VISUAL_PROMPT_CATALOG)
        == "cbf0e0baa8ca1bc63f8643b6e9f0982134a9bf2386e8d8c1db8adc31e7cf2fc2"
    )
    profile_hashes = {
        entry.profile.profile_id: entry.profile_sha256 for entry in VISUAL_PROMPT_CATALOG.profiles
    }
    assert profile_hashes == {
        "sdc.character-reference.cinematic.v1": (
            "54901f50bc718eb6f51d866c842c70791c7d341e7f9c20c37281ee0bc840434d"
        ),
        "sdc.narrative-shot.cinematic.v1": (
            "3da25632ad7798921a88200c591cd8774b65e533b6dd54a35be4c96802365181"
        ),
        "sdc.scene-reference.cinematic.v1": (
            "ea62abd6c0f35da2fa2ccc0d79ecc5e629aed84f14378dce0e14d88f49f11b0d"
        ),
    }
    raw = ADR041_PACKET_PATH.read_bytes()
    assert len(raw) == ADR041_PACKET_SIZE_BYTES
    assert hashlib.sha256(raw).hexdigest() == ADR041_PACKET_SHA256


def test_receipt_projection_is_process_evidence_only(
    compiled_cases: list[
        tuple[
            dict[str, Any],
            CharacterBible | SceneBible,
            CreativeSampleReferenceVisualPromptCompileRequestV1,
            CreativeSampleReferenceVisualPromptArtifactV1,
        ]
    ],
) -> None:
    for _case, _subject_value, _request_value, artifact in compiled_cases:
        receipt = artifact.prompt_render_receipt.model_dump(mode="json")
        _assert_zero_authority(receipt)
        assert receipt["receipt_purpose"] == ("DETERMINISTIC_PROMPT_RENDER_PROCESS_EVIDENCE_ONLY")
        assert receipt["replaces_rights_manifest"] is False
        assert receipt["grants_rights"] is False
        projection = compiler_module._prompt_render_receipt_projection(
            artifact.prompt_render_receipt
        )
        assert set(projection) == set(receipt) - {"prompt_render_receipt_sha256"}
