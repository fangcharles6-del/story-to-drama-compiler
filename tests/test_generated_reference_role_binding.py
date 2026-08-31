from __future__ import annotations

import ast
import hashlib
import inspect
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from typing import Any, cast, get_args

import pytest
from pydantic import BaseModel, ValidationError

from sdc import generated_reference_asset_promotion as promotion_module
from sdc import generated_reference_role_binding as role_module
from sdc import generated_reference_role_binding_codegen as codegen
from sdc.contracts import CharacterAssetVersion, CharacterBible
from sdc.generated_reference_rights_current_status import (
    process_generated_reference_current_status_record_as_of_assessment,
)

ROOT = Path(__file__).resolve().parents[1]


def _raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _semantic(domain: bytes, projection: object) -> str:
    encoded = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(domain + encoded).hexdigest()


def _document(value: object) -> bytes:
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


def _explicit(value: object) -> object:
    return role_module._explicit_value(value)


@dataclass(frozen=True, slots=True)
class _Operation:
    case: dict[str, object]
    review: dict[str, object]
    materials: codegen._RoleKnownAnswerMaterials
    target: role_module.GeneratedReferenceEligibleAssetRoleBindingTargetV1
    maker_action_bytes: bytes
    request: role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1
    gates: tuple[role_module.GeneratedReferenceRoleBindingGateResultV1, ...]
    checker_action_bytes: bytes
    result: role_module.GeneratedReferenceRoleBindingFinalizationResult


@dataclass(frozen=True, slots=True)
class _KnownAnswers:
    protected: codegen._ProtectedInputs
    character_case: dict[str, object]
    scene_case: dict[str, object]
    character_materials: codegen._RoleKnownAnswerMaterials
    scene_materials: codegen._RoleKnownAnswerMaterials
    positive: _Operation
    rejected: _Operation
    indeterminate: _Operation


def _human_values(review: dict[str, object]) -> tuple[dict[str, object], ...]:
    return tuple(cast(list[dict[str, object]], review["human_gate_results"]))


def _checker_action(
    *,
    operation_request: (
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1
    ),
    materials: codegen._RoleKnownAnswerMaterials,
    review: dict[str, object],
    gates: tuple[role_module.GeneratedReferenceRoleBindingGateResultV1, ...],
    final_primary: promotion_module.GeneratedReferencePromotionPrimaryAssetBindingV1,
    checker_identity_bytes: bytes | None = None,
    final_status: promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput | None = None,
    reviewed_at: str | None = None,
) -> bytes:
    human = _human_values(review)
    issues = codegen._role_issues(gates)
    decision = codegen._role_decision(gates)
    checker_identity = checker_identity_bytes or materials.checker_identity_bytes
    status = final_status or materials.promotion.final_status
    return _document(
        role_module.generated_reference_role_binding_checker_action_projection(
            request_id=operation_request.request_id,
            request_sha256=operation_request.request_sha256,
            target_sha256=operation_request.requested_role_binding_target.target_sha256,
            selected_reference_role=(
                operation_request.requested_role_binding_target.selected_reference_role
            ),
            final_status_receipt_sha256=status.receipt.receipt_sha256,
            final_primary_asset_binding_sha256=(
                final_primary.primary_asset_binding_sha256
            ),
            actor_ref_sha256=_raw_sha256(checker_identity),
            reviewed_at=reviewed_at or materials.promotion.promotion_at,
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result=cast(
                promotion_module.GateResult, human[0]["result"]
            ),
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
                str, human[0]["basis"]
            ),
            whole_composite_role_suitability_result=cast(
                promotion_module.GateResult, human[1]["result"]
            ),
            whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
            non_exclusive_no_transform_boundary_result=cast(
                promotion_module.GateResult, human[2]["result"]
            ),
            non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
            gate_results=gates,
            binding_issue_codes=issues,
            decision_basis=cast(str, review["decision_basis"]),
            decision=decision,
            binding_materialization_allowed=(
                decision == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
            ),
        )
    )


def _build_operation(
    case: dict[str, object],
    review: dict[str, object],
    materials: codegen._RoleKnownAnswerMaterials,
) -> _Operation:
    promotion = materials.promotion
    selected_role = cast(str, review["selected_reference_role"])
    target = role_module.build_generated_reference_eligible_asset_role_binding_target(
        promotion,
        materials.admitted_png,
        selected_reference_role=selected_role,
    )
    review_projection = (
        role_module.build_generated_reference_role_binding_review_payload_projection(
            target,
            promotion,
            promotion.final_status,
            materials.primary,
            requested_at=promotion.promotion_at,
        )
    )
    maker_action = _document(
        role_module.generated_reference_role_binding_maker_action_projection(
            actor_ref_sha256=_raw_sha256(materials.maker_identity_bytes),
            role_binding_review_payload_sha256=_semantic(
                role_module.GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
                review_projection,
            ),
            target_sha256=target.target_sha256,
            selected_reference_role=selected_role,
            requested_primary_asset_binding_sha256=(
                materials.primary.primary_asset_binding_sha256
            ),
            requested_status_receipt_sha256=(
                promotion.final_status.receipt.receipt_sha256
            ),
            prepared_at=promotion.promotion_at,
            request_basis=cast(str, review["request_basis"]),
        )
    )
    request = role_module.prepare_generated_reference_eligible_asset_role_binding_request(
        promotion,
        promotion.final_status,
        promotion.promotion_primary_bible,
        promotion.promotion_primary_asset_version,
        materials.admitted_png,
        selected_reference_role=selected_role,
        maker_identity_bytes=materials.maker_identity_bytes,
        maker_action_bytes=maker_action,
        requested_at=promotion.promotion_at,
        request_basis=cast(str, review["request_basis"]),
    )
    gates = codegen._role_gate_results(review)
    checker_action = _checker_action(
        operation_request=request,
        materials=materials,
        review=review,
        gates=gates,
        final_primary=materials.primary,
    )
    human = _human_values(review)
    result = role_module.finalize_generated_reference_eligible_asset_role_binding(
        request,
        promotion,
        promotion.final_status,
        promotion.promotion_primary_bible,
        promotion.promotion_primary_asset_version,
        promotion.final_status,
        promotion.promotion_primary_bible,
        promotion.promotion_primary_asset_version,
        materials.admitted_png,
        selected_reference_role=selected_role,
        maker_identity_bytes=materials.maker_identity_bytes,
        maker_action_bytes=maker_action,
        checker_identity_bytes=materials.checker_identity_bytes,
        checker_action_bytes=checker_action,
        binding_at=promotion.promotion_at,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result=cast(
            promotion_module.GateResult, human[0]["result"]
        ),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
            str, human[0]["basis"]
        ),
        whole_composite_role_suitability_result=cast(
            promotion_module.GateResult, human[1]["result"]
        ),
        whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
        non_exclusive_no_transform_boundary_result=cast(
            promotion_module.GateResult, human[2]["result"]
        ),
        non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
        decision_basis=cast(str, review["decision_basis"]),
    )
    return _Operation(
        case=case,
        review=review,
        materials=materials,
        target=target,
        maker_action_bytes=maker_action,
        request=request,
        gates=gates,
        checker_action_bytes=checker_action,
        result=result,
    )


@pytest.fixture(scope="module")
def known_answers() -> _KnownAnswers:
    protected = codegen._load_protected_inputs(ROOT)
    cases = codegen._assert_source_shape(protected.reviewed_source)
    character_case, scene_case = cases
    character_materials = codegen._role_materials(ROOT, protected, character_case)
    scene_materials = codegen._role_materials(ROOT, protected, scene_case)
    reviews = cast(list[dict[str, object]], character_case["role_reviews"])
    return _KnownAnswers(
        protected=protected,
        character_case=character_case,
        scene_case=scene_case,
        character_materials=character_materials,
        scene_materials=scene_materials,
        positive=_build_operation(character_case, reviews[0], character_materials),
        rejected=_build_operation(character_case, reviews[1], character_materials),
        indeterminate=_build_operation(character_case, reviews[2], character_materials),
    )


def _different(value: object) -> object:
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        return value + "-mutated"
    if type(value) is tuple:
        return (*value, "MUTATED")
    if type(value) is list:
        return [*cast(list[object], value), "MUTATED"]
    if type(value) is dict:
        return {**cast(dict[str, object], value), "mutated": True}
    raise AssertionError(f"unhandled projection value {type(value)!r}")


def _rehash_request(
    request: role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
    updates: dict[str, object],
) -> role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1:
    changed = request.model_copy(update=updates)
    review_sha = _semantic(
        role_module.GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
        role_module._review_payload_from_request(changed),
    )
    changed = changed.model_copy(
        update={"role_binding_review_payload_sha256": review_sha}
    )
    digest = _semantic(
        role_module.GENERATED_REFERENCE_ROLE_BINDING_REQUEST_SHA256_DOMAIN,
        role_module._request_projection_unchecked(changed),
    )
    return changed.model_copy(
        update={
            "request_id": (
                "generated_reference_eligible_asset_role_binding_request_v1_"
                + digest[:20]
            ),
            "request_sha256": digest,
        }
    )


def _rehash_decision(
    decision: role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
    updates: dict[str, object],
) -> role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1:
    changed = decision.model_copy(update=updates)
    digest = _semantic(
        role_module.GENERATED_REFERENCE_ROLE_BINDING_DECISION_SHA256_DOMAIN,
        role_module._decision_projection_unchecked(changed),
    )
    return changed.model_copy(
        update={
            "decision_id": (
                "generated_reference_eligible_asset_role_binding_decision_v1_"
                + digest[:20]
            ),
            "decision_sha256": digest,
        }
    )


def _mutated_primary_binding(
    primary: promotion_module.GeneratedReferencePromotionPrimaryAssetBindingV1,
) -> promotion_module.GeneratedReferencePromotionPrimaryAssetBindingV1:
    changed = primary.model_copy(
        update={"approval_ref": primary.approval_ref + "-mutated"}
    )
    digest = _semantic(
        promotion_module.GENERATED_REFERENCE_PRIMARY_ASSET_BINDING_SHA256_DOMAIN,
        promotion_module._primary_binding_projection_unchecked(changed),
    )
    return changed.model_copy(update={"primary_asset_binding_sha256": digest})


def _target_payload(
    target: role_module.GeneratedReferenceEligibleAssetRoleBindingTargetV1,
    updates: dict[str, object],
) -> dict[str, object]:
    values = cast(dict[str, object], target.model_dump(mode="python"))
    values.update(updates)
    projection = {
        name: _explicit(values[name])
        for name in role_module._TARGET_PROJECTION_FIELDS
    }
    values["target_sha256"] = _semantic(
        role_module.GENERATED_REFERENCE_ROLE_BINDING_TARGET_SHA256_DOMAIN,
        projection,
    )
    return values


def _identity_bytes(ordinal: int) -> bytes:
    return _document(
        {
            "document_profile": "sdc.privacy-minimized-human-reference.v1",
            "identity_namespace": "synthetic-role-binding-matrix-v1",
            "identity_ref": f"synthetic-role-binding-role-{ordinal:02d}",
        }
    )


def _finalize_positive(
    operation: _Operation,
    *,
    request: (
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1
        | None
    ) = None,
    final_status: (
        promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput | None
    ) = None,
    binding_primary_bible: CharacterBible | None = None,
    binding_primary_asset_version: CharacterAssetVersion | None = None,
    checker_identity_bytes: bytes | None = None,
    checker_action_bytes: bytes | None = None,
    binding_at: str | None = None,
) -> role_module.GeneratedReferenceRoleBindingFinalizationResult:
    human = _human_values(operation.review)
    return role_module.finalize_generated_reference_eligible_asset_role_binding(
        request or operation.request,
        operation.materials.promotion,
        operation.materials.promotion.final_status,
        operation.materials.promotion.promotion_primary_bible,
        operation.materials.promotion.promotion_primary_asset_version,
        final_status or operation.materials.promotion.final_status,
        binding_primary_bible or operation.materials.promotion.promotion_primary_bible,
        binding_primary_asset_version
        or operation.materials.promotion.promotion_primary_asset_version,
        operation.materials.admitted_png,
        selected_reference_role=operation.target.selected_reference_role,
        maker_identity_bytes=operation.materials.maker_identity_bytes,
        maker_action_bytes=operation.maker_action_bytes,
        checker_identity_bytes=(
            checker_identity_bytes or operation.materials.checker_identity_bytes
        ),
        checker_action_bytes=checker_action_bytes or operation.checker_action_bytes,
        binding_at=binding_at or operation.materials.promotion.promotion_at,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result=cast(
            role_module.GateResult, human[0]["result"]
        ),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
            str, human[0]["basis"]
        ),
        whole_composite_role_suitability_result=cast(
            role_module.GateResult, human[1]["result"]
        ),
        whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
        non_exclusive_no_transform_boundary_result=cast(
            role_module.GateResult, human[2]["result"]
        ),
        non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
        decision_basis=cast(str, operation.review["decision_basis"]),
    )


def _verify_finalization(
    operation: _Operation,
    expected: role_module.GeneratedReferenceRoleBindingFinalizationResult,
    *,
    request: (
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1
        | None
    ) = None,
    final_status: (
        promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput | None
    ) = None,
    binding_primary_bible: CharacterBible | None = None,
    binding_primary_asset_version: CharacterAssetVersion | None = None,
    checker_identity_bytes: bytes | None = None,
    maker_action_bytes: bytes | None = None,
    checker_action_bytes: bytes | None = None,
    binding_at: str | None = None,
) -> role_module.GeneratedReferenceRoleBindingFinalizationResult:
    human = _human_values(operation.review)
    return role_module.verify_generated_reference_eligible_asset_role_binding_finalization(
        expected,
        request or operation.request,
        operation.materials.promotion,
        operation.materials.promotion.final_status,
        operation.materials.promotion.promotion_primary_bible,
        operation.materials.promotion.promotion_primary_asset_version,
        final_status or operation.materials.promotion.final_status,
        binding_primary_bible or operation.materials.promotion.promotion_primary_bible,
        binding_primary_asset_version
        or operation.materials.promotion.promotion_primary_asset_version,
        operation.materials.admitted_png,
        selected_reference_role=operation.target.selected_reference_role,
        maker_identity_bytes=operation.materials.maker_identity_bytes,
        maker_action_bytes=(
            operation.maker_action_bytes
            if maker_action_bytes is None
            else maker_action_bytes
        ),
        checker_identity_bytes=(
            operation.materials.checker_identity_bytes
            if checker_identity_bytes is None
            else checker_identity_bytes
        ),
        checker_action_bytes=(
            operation.checker_action_bytes
            if checker_action_bytes is None
            else checker_action_bytes
        ),
        binding_at=binding_at or operation.materials.promotion.promotion_at,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result=cast(
            role_module.GateResult, human[0]["result"]
        ),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
            str, human[0]["basis"]
        ),
        whole_composite_role_suitability_result=cast(
            role_module.GateResult, human[1]["result"]
        ),
        whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
        non_exclusive_no_transform_boundary_result=cast(
            role_module.GateResult, human[2]["result"]
        ),
        non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
        decision_basis=cast(str, operation.review["decision_basis"]),
    )


def _unchecked_finalization(
    decision: role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
    binding: (
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1 | None
    ),
) -> role_module.GeneratedReferenceRoleBindingFinalizationResult:
    value = object.__new__(role_module.GeneratedReferenceRoleBindingFinalizationResult)
    object.__setattr__(value, "decision", decision)
    object.__setattr__(value, "binding", binding)
    return value


def test_policy_contract_inventory_domains_and_every_projection_field(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    binding = operation.result.binding
    assert binding is not None
    policy = json.dumps(
        role_module.generated_reference_role_binding_policy_projection(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert len(policy) == 9_046
    assert _raw_sha256(policy) == (
        "fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233"
    )
    assert len(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1.model_fields
    ) == 84
    assert len(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1.model_fields
    ) == 84
    assert len(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1.model_fields
    ) == 85

    projections: tuple[
        tuple[bytes, dict[str, object], str, set[str]], ...
    ] = (
        (
            role_module.GENERATED_REFERENCE_ROLE_BINDING_TARGET_SHA256_DOMAIN,
            role_module.generated_reference_role_binding_target_projection(operation.target),
            operation.target.target_sha256,
            {"target_sha256"},
        ),
        (
            role_module.GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
            role_module.generated_reference_role_binding_review_payload_projection(
                operation.request
            ),
            operation.request.role_binding_review_payload_sha256,
            set(),
        ),
        (
            role_module.GENERATED_REFERENCE_ROLE_BINDING_REQUEST_SHA256_DOMAIN,
            role_module.creative_sample_generated_reference_eligible_asset_role_binding_request_projection(
                operation.request
            ),
            operation.request.request_sha256,
            {"request_id", "request_sha256"},
        ),
        (
            role_module.GENERATED_REFERENCE_ROLE_BINDING_DECISION_SHA256_DOMAIN,
            role_module.creative_sample_generated_reference_eligible_asset_role_binding_decision_projection(
                operation.result.decision
            ),
            operation.result.decision.decision_sha256,
            {"decision_id", "decision_sha256"},
        ),
        (
            role_module.GENERATED_REFERENCE_ROLE_BINDING_SHA256_DOMAIN,
            role_module.creative_sample_generated_reference_eligible_asset_role_binding_projection(
                binding
            ),
            binding.binding_sha256,
            {"binding_id", "binding_sha256"},
        ),
    )
    assert len({domain for domain, _projection, _digest, _excluded in projections}) == 5
    for domain, projection, digest, excluded in projections:
        assert _semantic(domain, projection) == digest
        assert not excluded.intersection(projection)
        for name, value in projection.items():
            mutated = {**projection, name: _different(value)}
            assert _semantic(domain, mutated) != digest
    probe = {"probe": "same-projection", "ordinal": 0}
    assert len({_semantic(domain, probe) for domain, *_rest in projections}) == 5

    identities = (
        (
            operation.request.request_id,
            operation.request.request_sha256,
            "generated_reference_eligible_asset_role_binding_request_v1_",
        ),
        (
            operation.result.decision.decision_id,
            operation.result.decision.decision_sha256,
            "generated_reference_eligible_asset_role_binding_decision_v1_",
        ),
        (
            binding.binding_id,
            binding.binding_sha256,
            "generated_reference_eligible_asset_role_binding_v1_",
        ),
    )
    for portable_id, full_sha256, stem in identities:
        assert portable_id == stem + full_sha256[:20]
        assert len(full_sha256) == 64


def test_all_seven_roles_are_purpose_closed_and_nonexclusive(
    known_answers: _KnownAnswers,
) -> None:
    targets = []
    for materials, roles in (
        (
            known_answers.character_materials,
            role_module.CHARACTER_REFERENCE_ROLE_ORDER,
        ),
        (known_answers.scene_materials, role_module.SCENE_REFERENCE_ROLE_ORDER),
    ):
        for selected_role in roles:
            targets.append(
                role_module.build_generated_reference_eligible_asset_role_binding_target(
                    materials.promotion,
                    materials.admitted_png,
                    selected_reference_role=selected_role,
                )
            )
    assert tuple(item.selected_reference_role for item in targets) == (
        *role_module.CHARACTER_REFERENCE_ROLE_ORDER,
        *role_module.SCENE_REFERENCE_ROLE_ORDER,
    )
    assert len({item.target_sha256 for item in targets}) == 7
    assert all(
        item.binding_exclusivity_asserted is False
        and item.complete_role_set_asserted is False
        and item.global_role_uniqueness_asserted is False
        and item.crop_applied is False
        and item.split_applied is False
        and item.transform_applied is False
        and item.provider_slot_embedded is False
        for item in targets
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        role_module.build_generated_reference_eligible_asset_role_binding_target(
            known_answers.character_materials.promotion,
            known_answers.character_materials.admitted_png,
            selected_reference_role="SCENE_LIGHTING_REFERENCE",
        )
    assert error.value.code == "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID"


@pytest.mark.parametrize(
    ("field", "mutated"),
    (
        ("reference_asset_types", ("CHARACTER_IDENTITY_SHEET",)),
        (
            "reference_asset_types",
            (
                "CHARACTER_EXPRESSION_REFERENCE",
                "CHARACTER_POSE_REFERENCE",
                "CHARACTER_IDENTITY_SHEET",
            ),
        ),
        ("selected_reference_role", "UNKNOWN_REFERENCE_ROLE"),
        ("selected_reference_role", "SCENE_LIGHTING_REFERENCE"),
    ),
)
def test_role_tuple_subset_reorder_unknown_and_cross_purpose_are_rejected(
    known_answers: _KnownAnswers,
    field: str,
    mutated: object,
) -> None:
    with pytest.raises(ValidationError):
        role_module.GeneratedReferenceEligibleAssetRoleBindingTargetV1.model_validate(
            _target_payload(known_answers.positive.target, {field: mutated})
        )


@pytest.mark.parametrize(
    "untrusted_field",
    ("profile_inferred_role", "prompt_role", "qc_role", "file_name_role", "layout_role"),
)
def test_profile_prompt_qc_filename_and_layout_cannot_create_roles(
    known_answers: _KnownAnswers,
    untrusted_field: str,
) -> None:
    values = cast(
        dict[str, object], known_answers.positive.target.model_dump(mode="python")
    )
    values[untrusted_field] = "SCENE_LIGHTING_REFERENCE"
    with pytest.raises(ValidationError):
        role_module.GeneratedReferenceEligibleAssetRoleBindingTargetV1.model_validate(values)


@pytest.mark.parametrize(
    "mutation",
    (
        {"crop_applied": True},
        {"split_applied": True},
        {"transform_applied": True},
        {"derived_media_created": True},
        {"provider_slot_embedded": True},
        {"resize_applied": True},
        {"transcode_applied": True},
    ),
)
def test_crop_split_transform_resize_transcode_and_derived_flags_are_rejected(
    known_answers: _KnownAnswers,
    mutation: dict[str, object],
) -> None:
    values = _target_payload(known_answers.positive.target, mutation)
    with pytest.raises(ValidationError):
        role_module.GeneratedReferenceEligibleAssetRoleBindingTargetV1.model_validate(values)


def test_png_and_candidate_occurrence_are_both_in_target_identity(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    admitted = known_answers.character_materials.admitted_png
    assert admitted.png_bytes == known_answers.character_materials.promotion.upstream.png_bytes
    assert admitted.media_content_sha256 == _raw_sha256(admitted.png_bytes)
    assert admitted.media_size_bytes == len(admitted.png_bytes)
    projection = role_module.generated_reference_role_binding_target_projection(
        operation.target
    )
    changed = {**projection, "candidate_id": "candidate_same_bytes_other_occurrence"}
    assert _semantic(
        role_module.GENERATED_REFERENCE_ROLE_BINDING_TARGET_SHA256_DOMAIN, changed
    ) != operation.target.target_sha256
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        role_module.GeneratedReferenceRoleBindingAdmittedPng(
            png_bytes=admitted.png_bytes + b"x",
            media_content_sha256=admitted.media_content_sha256,
            media_size_bytes=admitted.media_size_bytes,
            media_technical_record_sha256=admitted.media_technical_record_sha256,
        )
    assert error.value.code == "PNG_ADMISSION_INVALID"

    distinct_occurrence = (
        role_module.GeneratedReferenceEligibleAssetRoleBindingTargetV1.model_validate(
            _target_payload(
                operation.target,
                {
                    "provider_attempt_outcome_id": (
                        "attempt_equal_bytes_distinct_occurrence"
                    ),
                    "provider_attempt_outcome_sha256": "cd" * 32,
                    "candidate_id": "candidate_equal_bytes_distinct_occurrence",
                    "candidate_sha256": "ab" * 32,
                },
            )
        )
    )
    assert distinct_occurrence.media_content_sha256 == operation.target.media_content_sha256
    assert distinct_occurrence.media_size_bytes == operation.target.media_size_bytes
    assert (
        distinct_occurrence.provider_attempt_outcome_id
        != operation.target.provider_attempt_outcome_id
    )
    assert distinct_occurrence.candidate_id != operation.target.candidate_id
    assert distinct_occurrence.target_sha256 != operation.target.target_sha256
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as closure_error:
        role_module._verify_target_linkage(
            distinct_occurrence, known_answers.character_materials.promotion
        )
    assert closure_error.value.code == "UPSTREAM_CLOSURE_MISMATCH"

    derived_bytes = admitted.png_bytes[:-1] + bytes([admitted.png_bytes[-1] ^ 1])
    derived = role_module.GeneratedReferenceRoleBindingAdmittedPng(
        png_bytes=derived_bytes,
        media_content_sha256=_raw_sha256(derived_bytes),
        media_size_bytes=len(derived_bytes),
        media_technical_record_sha256=admitted.media_technical_record_sha256,
    )
    sidecar = known_answers.character_materials.promotion.result.sidecar
    assert sidecar is not None
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as derived_error:
        role_module._verify_admitted_png(
            derived,
            known_answers.character_materials.promotion,
            sidecar,
        )
    assert derived_error.value.code == "PNG_ADMISSION_INVALID"


def test_target_build_replays_complete_adr_042_through_045_closure(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"manifest": 0, "status": 0, "promotion": 0}
    original_manifest = cast(
        Any,
        promotion_module.verify_generated_reference_rights_manifest,  # type: ignore[attr-defined]
    )
    original_status = promotion_module._verify_status_closure
    original_promotion = cast(
        Any,
        role_module.verify_generated_reference_asset_promotion_finalization,  # type: ignore[attr-defined]
    )

    def manifest_spy(*args: object, **kwargs: object) -> object:
        calls["manifest"] += 1
        return original_manifest(*cast(Any, args), **cast(Any, kwargs))

    def status_spy(*args: object, **kwargs: object) -> object:
        calls["status"] += 1
        return original_status(*cast(Any, args), **cast(Any, kwargs))

    def promotion_spy(*args: object, **kwargs: object) -> object:
        calls["promotion"] += 1
        return original_promotion(*cast(Any, args), **cast(Any, kwargs))

    monkeypatch.setattr(
        promotion_module, "verify_generated_reference_rights_manifest", manifest_spy
    )
    monkeypatch.setattr(promotion_module, "_verify_status_closure", status_spy)
    monkeypatch.setattr(
        role_module,
        "verify_generated_reference_asset_promotion_finalization",
        promotion_spy,
    )
    target = role_module.build_generated_reference_eligible_asset_role_binding_target(
        known_answers.character_materials.promotion,
        known_answers.character_materials.admitted_png,
        selected_reference_role="CHARACTER_IDENTITY_SHEET",
    )
    assert target == known_answers.positive.target
    assert calls["promotion"] >= 1
    assert calls["manifest"] >= 1
    assert calls["status"] >= 2
    sidecar = known_answers.character_materials.promotion.result.sidecar
    assert sidecar is not None
    assert (
        known_answers.positive.request.promotion_evidence_valid_until
        == sidecar.promotion_evidence_valid_until
    )
    assert (
        known_answers.positive.request.requested_as_of
        == known_answers.character_materials.promotion.final_status.receipt.as_of
    )


def test_two_status_transitions_reject_regression_and_occurrence_omission(
    known_answers: _KnownAnswers,
) -> None:
    promotion = known_answers.scene_materials.promotion
    role_module._verify_status_monotonicity(
        promotion.request_status, promotion.final_status
    )
    role_module._verify_status_monotonicity(
        promotion.final_status, promotion.final_status
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as regression:
        role_module._verify_status_monotonicity(
            promotion.final_status, promotion.request_status
        )
    assert regression.value.code == "CURRENT_STATUS_REPLAY_INVALID"
    omitted = replace(promotion.final_status, chain_inputs=())
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as omission:
        role_module._verify_status_monotonicity(promotion.final_status, omitted)
    assert omission.value.code == "CURRENT_STATUS_REPLAY_INVALID"

    target_omitted_request = promotion.final_status.request.model_copy(
        update={
            "observation_refs": promotion.final_status.request.observation_refs[:-1]
        }
    )
    target_omitted = replace(
        promotion.final_status, request=target_omitted_request
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as target_error:
        role_module._verify_status_monotonicity(
            promotion.final_status, target_omitted
        )
    assert target_error.value.code == "CURRENT_STATUS_REPLAY_INVALID"

    replaced_input = promotion.final_status.chain_inputs[0].observation_inputs[0]
    rewritten = replace(replaced_input, document_bytes=b"{}\n")
    rewritten_chain = replace(
        promotion.final_status.chain_inputs[0], observation_inputs=(rewritten,)
    )
    replaced_branch = replace(
        promotion.final_status,
        chain_inputs=(rewritten_chain, *promotion.final_status.chain_inputs[1:]),
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as replaced_error:
        role_module._verify_status_monotonicity(
            promotion.final_status, replaced_branch
        )
    assert replaced_error.value.code == "CURRENT_STATUS_REPLAY_INVALID"

    changed_subject = promotion.final_status.subject_closure.model_copy(
        update={"closure_id": "different_status_subject_closure"}
    )
    wrong_subject = replace(
        promotion.final_status, subject_closure=changed_subject
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as subject_error:
        role_module._verify_status_monotonicity(
            promotion.final_status, wrong_subject
        )
    assert subject_error.value.code == "UPSTREAM_CLOSURE_MISMATCH"


@pytest.mark.parametrize(
    "requested_at",
    (
        "2026-08-29T11:59:59Z",
        "2026-08-29T12:00:00Z",
        "2026-08-29T12:00:01Z",
    ),
)
def test_sidecar_horizon_is_historical_before_equal_and_after(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
    requested_at: str,
) -> None:
    operation = known_answers.positive
    historical_sidecar_horizon = "2026-08-29T12:00:00Z"
    assert "promotion_evidence_valid_until" not in inspect.signature(
        role_module._request_time_derivation
    ).parameters
    sidecar = operation.materials.promotion.result.sidecar
    assert sidecar is not None
    copied_sidecar = sidecar.model_copy(
        update={"promotion_evidence_valid_until": historical_sidecar_horizon}
    )
    fresh_receipt = (
            process_generated_reference_current_status_record_as_of_assessment(
            operation.materials.promotion.final_status.record,
            operation.materials.promotion.upstream.manifest,
            operation.materials.promotion.final_status.chain_inputs,
            as_of=requested_at,
        ).receipt
    )
    request_status = replace(
        operation.materials.promotion.final_status, receipt=fresh_receipt
    )
    assert fresh_receipt.as_of == requested_at
    assert fresh_receipt.as_of_status == "CURRENT"

    def promotion_replay(
        closure: role_module.GeneratedReferenceRoleBindingPromotionClosureInput,
    ) -> tuple[object, object]:
        return closure.request, copied_sidecar

    monkeypatch.setattr(role_module, "_verify_promotion_closure", promotion_replay)
    review_projection = (
        role_module.build_generated_reference_role_binding_review_payload_projection(
            operation.target,
            operation.materials.promotion,
            request_status,
            operation.materials.primary,
            requested_at=requested_at,
        )
    )
    basis = cast(str, operation.review["request_basis"])
    maker_action = _document(
        role_module.generated_reference_role_binding_maker_action_projection(
            actor_ref_sha256=_raw_sha256(operation.materials.maker_identity_bytes),
            role_binding_review_payload_sha256=_semantic(
                role_module.GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
                review_projection,
            ),
            target_sha256=operation.target.target_sha256,
            selected_reference_role=operation.target.selected_reference_role,
            requested_primary_asset_binding_sha256=(
                operation.materials.primary.primary_asset_binding_sha256
            ),
            requested_status_receipt_sha256=fresh_receipt.receipt_sha256,
            prepared_at=requested_at,
            request_basis=basis,
        )
    )
    request = role_module.prepare_generated_reference_eligible_asset_role_binding_request(
        operation.materials.promotion,
        request_status,
        operation.materials.promotion.promotion_primary_bible,
        operation.materials.promotion.promotion_primary_asset_version,
        operation.materials.admitted_png,
        selected_reference_role=operation.target.selected_reference_role,
        maker_identity_bytes=operation.materials.maker_identity_bytes,
        maker_action_bytes=maker_action,
        requested_at=requested_at,
        request_basis=basis,
    )
    assert request.promotion_evidence_valid_until == historical_sidecar_horizon
    assert request.requested_at == requested_at
    assert request.request_valid_until > requested_at


@pytest.mark.parametrize(
    "exclusive_field",
    ("qualification_valid_until", "manifest_valid_until", "status_valid_until"),
)
def test_request_time_equal_to_each_exclusive_deadline_fails_closed(
    exclusive_field: str,
) -> None:
    values = {
        "qualification_valid_until": "2026-09-02T00:00:00Z",
        "manifest_valid_until": "2026-09-03T00:00:00Z",
        "status_valid_until": "2026-09-04T00:00:00Z",
    }
    values[exclusive_field] = "2026-09-01T00:00:00Z"
    request_valid_until, error = role_module._request_time_derivation(
        requested_at="2026-09-01T00:00:00Z",
        promotion_at="2026-08-31T00:00:00Z",
        **values,
    )
    assert request_valid_until == "2026-09-01T00:00:00Z"
    assert error == "requested_at is at or beyond one exclusive evidence deadline"


@pytest.mark.parametrize(
    "governing_bound",
    (
        "requested_at_plus_86400",
        "qualification_valid_until",
        "manifest_valid_until",
        "requested_status_valid_until",
        "binding_status_valid_until",
    ),
)
def test_each_binding_half_open_bound_is_independently_governing(
    known_answers: _KnownAnswers,
    governing_bound: str,
) -> None:
    operation = known_answers.positive
    requested_at = "2026-09-01T00:00:00Z"
    later = "2026-09-03T00:00:00Z"
    selected_upper = "2026-09-01T12:00:00Z"
    qualification = later
    manifest = later
    requested_status = later
    final_status = later
    if governing_bound == "qualification_valid_until":
        qualification = selected_upper
    elif governing_bound == "manifest_valid_until":
        manifest = selected_upper
    elif governing_bound == "requested_status_valid_until":
        requested_status = selected_upper
    elif governing_bound == "binding_status_valid_until":
        final_status = selected_upper
    request_until, derivation_error = role_module._request_time_derivation(
        requested_at=requested_at,
        promotion_at="2026-08-31T00:00:00Z",
        qualification_valid_until=qualification,
        manifest_valid_until=manifest,
        status_valid_until=requested_status,
    )
    assert derivation_error is None
    assert request_until is not None
    binding_at = (
        selected_upper
        if governing_bound == "binding_status_valid_until"
        else request_until
    )
    request = operation.request.model_copy(
        update={
            "requested_at": requested_at,
            "maker_prepared_at": requested_at,
            "requested_as_of": requested_at,
            "promotion_at": "2026-08-31T00:00:00Z",
            "qualification_valid_until": qualification,
            "manifest_valid_until": manifest,
            "requested_status_valid_until": requested_status,
            "request_valid_until": request_until,
        }
    )
    request_receipt = operation.materials.promotion.final_status.receipt.model_copy(
        update={"as_of": requested_at, "status_valid_until": requested_status}
    )
    final_receipt = operation.materials.promotion.final_status.receipt.model_copy(
        update={"as_of": binding_at, "status_valid_until": final_status}
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        role_module._verify_binding_time_window(
            request,
            request_receipt,
            final_receipt,
            binding_at=binding_at,
        )
    assert error.value.code == "TIME_OR_VALIDITY_INVALID"


@pytest.mark.parametrize(
    "deadline_source",
    (
        "request_valid_until",
        "qualification_valid_until",
        "manifest_valid_until",
        "binding_status_valid_until",
    ),
)
def test_binding_at_equal_to_every_half_open_upper_bound_fails_closed(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
    deadline_source: str,
) -> None:
    operation = known_answers.positive
    deadline = {
        "request_valid_until": operation.request.request_valid_until,
        "qualification_valid_until": operation.request.qualification_valid_until,
        "manifest_valid_until": operation.request.manifest_valid_until,
        "binding_status_valid_until": (
            operation.materials.promotion.final_status.receipt.status_valid_until
        ),
    }[deadline_source]
    fake_receipt = operation.materials.promotion.final_status.receipt.model_copy(
        update={"as_of": deadline}
    )
    fake_final_status = replace(
        operation.materials.promotion.final_status, receipt=fake_receipt
    )
    checker_action = _checker_action(
        operation_request=operation.request,
        materials=operation.materials,
        review=operation.review,
        gates=operation.gates,
        final_primary=operation.materials.primary,
        final_status=fake_final_status,
        reviewed_at=deadline,
    )

    def replay_supplied_receipt(
        closure: promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput,
        *args: object,
        **kwargs: object,
    ) -> object:
        return closure.receipt

    monkeypatch.setattr(role_module, "_verify_status_closure", replay_supplied_receipt)
    monkeypatch.setattr(
        role_module, "_verify_status_monotonicity", lambda *args, **kwargs: None
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _finalize_positive(
            operation,
            final_status=fake_final_status,
            checker_action_bytes=checker_action,
            binding_at=deadline,
        )
    assert error.value.code == "TIME_OR_VALIDITY_INVALID"


def test_positive_negative_indeterminate_and_atomic_pair(
    known_answers: _KnownAnswers,
) -> None:
    positive = known_answers.positive.result
    rejected = known_answers.rejected.result
    indeterminate = known_answers.indeterminate.result
    assert positive.decision.decision == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
    assert positive.binding is not None
    assert positive.decision.binding_materialization_allowed is True
    assert rejected.decision.decision == "REJECT_ELIGIBLE_ASSET_ROLE_BINDING"
    assert rejected.binding is None
    assert indeterminate.decision.decision == (
        "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING"
    )
    assert indeterminate.binding is None
    assert positive.binding.decision_id == positive.decision.decision_id
    assert positive.binding.decision_sha256 == positive.decision.decision_sha256
    role_module.verify_generated_reference_eligible_asset_role_binding_finalization(
        positive,
        known_answers.positive.request,
        known_answers.character_materials.promotion,
        known_answers.character_materials.promotion.final_status,
        known_answers.character_materials.promotion.promotion_primary_bible,
        known_answers.character_materials.promotion.promotion_primary_asset_version,
        known_answers.character_materials.promotion.final_status,
        known_answers.character_materials.promotion.promotion_primary_bible,
        known_answers.character_materials.promotion.promotion_primary_asset_version,
        known_answers.character_materials.admitted_png,
        selected_reference_role=known_answers.positive.target.selected_reference_role,
        maker_identity_bytes=known_answers.character_materials.maker_identity_bytes,
        maker_action_bytes=known_answers.positive.maker_action_bytes,
        checker_identity_bytes=known_answers.character_materials.checker_identity_bytes,
        checker_action_bytes=known_answers.positive.checker_action_bytes,
        binding_at=known_answers.character_materials.promotion.promotion_at,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result="PASS",
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
            str, _human_values(known_answers.positive.review)[0]["basis"]
        ),
        whole_composite_role_suitability_result="PASS",
        whole_composite_role_suitability_basis=cast(
            str, _human_values(known_answers.positive.review)[1]["basis"]
        ),
        non_exclusive_no_transform_boundary_result="PASS",
        non_exclusive_no_transform_boundary_basis=cast(
            str, _human_values(known_answers.positive.review)[2]["basis"]
        ),
        decision_basis=cast(str, known_answers.positive.review["decision_basis"]),
    )


def test_repeated_same_sidecar_and_role_review_remains_nonexclusive(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    repeated_target = (
        role_module.build_generated_reference_eligible_asset_role_binding_target(
            operation.materials.promotion,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
        )
    )
    assert repeated_target == operation.target
    alternate_basis = cast(str, operation.review["request_basis"]) + (
        " This independent repeated review grants no exclusivity."
    )
    review_projection = (
        role_module.build_generated_reference_role_binding_review_payload_projection(
            repeated_target,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.primary,
            requested_at=operation.materials.promotion.promotion_at,
        )
    )
    alternate_action = _document(
        role_module.generated_reference_role_binding_maker_action_projection(
            actor_ref_sha256=_raw_sha256(operation.materials.maker_identity_bytes),
            role_binding_review_payload_sha256=_semantic(
                role_module.GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
                review_projection,
            ),
            target_sha256=repeated_target.target_sha256,
            selected_reference_role=repeated_target.selected_reference_role,
            requested_primary_asset_binding_sha256=(
                operation.materials.primary.primary_asset_binding_sha256
            ),
            requested_status_receipt_sha256=(
                operation.materials.promotion.final_status.receipt.receipt_sha256
            ),
            prepared_at=operation.materials.promotion.promotion_at,
            request_basis=alternate_basis,
        )
    )
    repeated_request = (
        role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=repeated_target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=alternate_action,
            requested_at=operation.materials.promotion.promotion_at,
            request_basis=alternate_basis,
        )
    )
    assert repeated_request.request_sha256 != operation.request.request_sha256
    assert repeated_request.requested_role_binding_target == operation.target
    assert repeated_request.role_binding_exclusivity_asserted is False
    assert repeated_request.complete_role_set_asserted is False
    assert repeated_request.global_role_uniqueness_asserted is False

    decision = operation.result.decision
    binding = operation.result.binding
    assert binding is not None
    false_inventory = (
        (
            operation.target,
            (
                "binding_exclusivity_asserted",
                "complete_role_set_asserted",
                "global_role_uniqueness_asserted",
            ),
        ),
        (
            repeated_request,
            (
                "role_binding_exclusivity_asserted",
                "complete_role_set_asserted",
                "global_role_uniqueness_asserted",
                "role_binding_performed",
                "binding_materialized",
            ),
        ),
        (
            decision,
            (
                "binding_id_embedded",
                "role_binding_exclusivity_asserted",
                "complete_role_set_asserted",
                "global_role_uniqueness_asserted",
            ),
        ),
        (
            binding,
            (
                "present_currentness_asserted",
                "perpetual_role_suitability_asserted",
                "role_binding_exclusivity_asserted",
                "complete_role_set_asserted",
                "global_role_uniqueness_asserted",
                "current_role_binding_asserted",
                "supersedes_role_binding",
                "primary_asset_binding_replaced",
                "bible_active_binding_changed",
                "asset_version_v1_created",
            ),
        ),
    )
    for formal, fields_to_check in false_inventory:
        assert all(getattr(formal, name) is False for name in fields_to_check)


@pytest.mark.parametrize(
    "tampered_component",
    ("gate_results", "binding_issue_codes", "decision", "materialization"),
)
def test_checker_action_closes_gate_issue_decision_and_materialization_tuple(
    known_answers: _KnownAnswers,
    tampered_component: str,
) -> None:
    expected = cast(
        dict[str, object], json.loads(known_answers.positive.checker_action_bytes)
    )
    tampered = cast(dict[str, object], json.loads(json.dumps(expected)))
    if tampered_component == "gate_results":
        gates = cast(list[dict[str, object]], tampered["gate_results"])
        gates[0]["basis"] = cast(str, gates[0]["basis"]) + " tampered"
    elif tampered_component == "binding_issue_codes":
        tampered["binding_issue_codes"] = ["PRIMARY_BINDING_NO_LONGER_ACTIVE"]
    elif tampered_component == "decision":
        tampered["decision"] = "REJECT_ELIGIBLE_ASSET_ROLE_BINDING"
    else:
        tampered["binding_materialization_allowed"] = False
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        role_module._exact_action(
            _document(tampered), expected, field="synthetic Checker action"
        )
    assert error.value.code == "ACTION_RECORD_INVALID"


def test_positive_binding_construction_failure_is_atomic(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = role_module._build_identity

    def fail_only_binding(model_type: object, values: object) -> object:
        if (
            model_type
            is role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1
        ):
            raise ValueError("synthetic injected Binding construction failure")
        return original(cast(Any, model_type), cast(Any, values))

    monkeypatch.setattr(role_module, "_build_identity", fail_only_binding)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _finalize_positive(known_answers.positive)
    assert error.value.code == "ATOMIC_OUTPUT_INVARIANT_VIOLATION"


def test_every_request_to_decision_linkage_row_is_exact(
    known_answers: _KnownAnswers,
) -> None:
    request = known_answers.positive.request
    decision = known_answers.positive.result.decision
    exact_linkage_fields = (
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "role_binding_review_payload_sha256",
        "request_id",
        "request_sha256",
        "requested_role_binding_target",
        "promotion_request_id",
        "promotion_request_sha256",
        "promotion_decision_id",
        "promotion_decision_sha256",
        "eligible_asset_sidecar_id",
        "eligible_asset_sidecar_sha256",
        "promotion_at",
        "promotion_evidence_valid_until",
        "qualification_decision_id",
        "qualification_decision_sha256",
        "qualification_valid_until",
        "manifest_id",
        "manifest_sha256",
        "manifest_valid_until",
        "reviewed_rights_scope",
        "requested_primary_asset_binding",
    )
    assert role_module._DECISION_REQUEST_LINK_FIELDS == exact_linkage_fields
    for name in exact_linkage_fields:
        assert getattr(decision, name) == getattr(request, name), name

    request_time_status_and_maker_fields = (
        "requested_status_record_id",
        "requested_status_record_sha256",
        "requested_status_receipt_id",
        "requested_status_receipt_sha256",
        "requested_explicit_chain_set_sha256",
        "requested_coverage_set_sha256",
        "requested_joint_replay_sha256",
        "requested_as_of_assessment_sha256",
        "requested_as_of",
        "requested_as_of_status",
        "requested_status_valid_until",
        "maker_identity_ref_sha256",
        "maker_action_sha256",
        "maker_prepared_at",
        "requested_at",
        "request_valid_until",
        "request_basis",
    )
    request_fields = type(request).model_fields
    decision_fields = type(decision).model_fields
    assert set(request_time_status_and_maker_fields).issubset(request_fields)
    assert set(request_time_status_and_maker_fields).isdisjoint(decision_fields)


@pytest.mark.parametrize(
    ("field", "expected_code"),
    tuple(
        (
            field,
            (
                "POLICY_IDENTITY_MISMATCH"
                if field in role_module._DECISION_REQUEST_LINK_FIELDS[:3]
                else "UPSTREAM_CLOSURE_MISMATCH"
            ),
        )
        for field in role_module._DECISION_REQUEST_LINK_FIELDS
    ),
)
def test_expected_decision_every_request_linkage_mutation_precedes_atomicity(
    known_answers: _KnownAnswers,
    field: str,
    expected_code: str,
) -> None:
    operation = known_answers.positive
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    current = getattr(operation.result.decision, field)
    updates: dict[str, object]
    if field == "requested_role_binding_target":
        updates = {field: known_answers.rejected.target}
    elif field == "reviewed_rights_scope":
        updates = {
            field: current.model_copy(
                update={
                    "review_basis": current.review_basis + " Synthetic mutation."
                }
            )
        }
    elif field == "requested_primary_asset_binding":
        primary = _mutated_primary_binding(current)
        updates = {
            "requested_primary_asset_binding": primary,
            "binding_primary_asset_binding": primary,
        }
    elif field == "promotion_at":
        updates = {field: "2000-01-01T00:00:00Z"}
    elif field in {
        "promotion_evidence_valid_until",
        "qualification_valid_until",
        "manifest_valid_until",
    }:
        updates = {field: "2099-01-01T00:00:00Z"}
    elif field.endswith("_sha256"):
        updates = {field: "ab" * 32 if current != "ab" * 32 else "cd" * 32}
    else:
        updates = {field: cast(str, current) + "_mutated"}

    mutated_decision = _rehash_decision(operation.result.decision, updates)
    expected = _unchecked_finalization(mutated_decision, binding)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(operation, expected)
    assert error.value.code == expected_code


def test_expected_request_copied_linkage_precedes_promotion_replay_failure(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = known_answers.positive
    mutated = _rehash_request(
        operation.request,
        {
            "promotion_request_id": (
                operation.request.promotion_request_id + "_mutated"
            )
        },
    )

    def fail_promotion(*args: object, **kwargs: object) -> Any:
        raise role_module.GeneratedReferenceRoleBindingError(
            "PROMOTION_CLOSURE_INVALID", "synthetic later Promotion failure"
        )

    monkeypatch.setattr(role_module, "_verify_promotion_closure", fail_promotion)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            mutated,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
        )
    assert error.value.code == "UPSTREAM_CLOSURE_MISMATCH"


@pytest.mark.parametrize(
    "maker_field", ("maker_identity_ref_sha256", "maker_action_sha256")
)
@pytest.mark.parametrize("later_fault", ("time", "authority"))
def test_expected_request_maker_anchor_drift_is_action_invalid(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
    maker_field: str,
    later_fault: str,
) -> None:
    operation = known_answers.positive
    updates: dict[str, object] = {maker_field: "ab" * 32}
    if later_fault == "authority":
        updates["provider_requests"] = 1
    else:
        monkeypatch.setattr(
            role_module,
            "_request_time_derivation",
            lambda **kwargs: (None, "synthetic later time failure"),
        )
    mutated = _rehash_request(operation.request, updates)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            mutated,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
        )
    assert error.value.code == "ACTION_RECORD_INVALID"


@pytest.mark.parametrize("field", role_module._REQUEST_PREDECESSOR_LINK_FIELDS)
def test_finalization_request_every_predecessor_drift_precedes_promotion_replay(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    operation = known_answers.positive
    current = getattr(operation.request, field)
    updates: dict[str, object]
    if field == "promotion_at":
        updates = {field: "2000-01-01T00:00:00Z"}
    elif field in {
        "promotion_evidence_valid_until",
        "qualification_valid_until",
        "manifest_valid_until",
    }:
        updates = {field: "2099-01-01T00:00:00Z"}
    elif field.endswith("_sha256"):
        updates = {field: "ab" * 32 if current != "ab" * 32 else "cd" * 32}
    else:
        updates = {field: cast(str, current) + "_mutated"}

    preview = operation.request.model_copy(update=updates)
    updates["request_valid_until"] = role_module._request_valid_until(
        requested_at=preview.requested_at,
        qualification_valid_until=preview.qualification_valid_until,
        manifest_valid_until=preview.manifest_valid_until,
        status_valid_until=preview.requested_status_valid_until,
    )
    mutated_request = _rehash_request(operation.request, updates)
    decision_updates = {
        name: getattr(mutated_request, name)
        for name in role_module._DECISION_REQUEST_LINK_FIELDS
    }
    mutated_decision = _rehash_decision(operation.result.decision, decision_updates)
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    expected = _unchecked_finalization(mutated_decision, binding)

    def fail_promotion(*args: object, **kwargs: object) -> Any:
        raise role_module.GeneratedReferenceRoleBindingError(
            "PROMOTION_CLOSURE_INVALID", "synthetic later Promotion failure"
        )

    monkeypatch.setattr(role_module, "_verify_promotion_closure", fail_promotion)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(operation, expected, request=mutated_request)
    assert error.value.code == "UPSTREAM_CLOSURE_MISMATCH"


@pytest.mark.parametrize("field", role_module._TARGET_PREDECESSOR_LINK_FIELDS)
def test_finalization_target_every_drift_is_owned_by_role_stage(
    known_answers: _KnownAnswers,
    field: str,
) -> None:
    operation = known_answers.positive
    current = getattr(operation.target, field)
    if field == "asset_purpose":
        updates: dict[str, object] = {
            "asset_purpose": "SCENE_REFERENCE_ASSET",
            "reference_asset_types": role_module.SCENE_REFERENCE_ROLE_ORDER,
            "selected_reference_role": role_module.SCENE_REFERENCE_ROLE_ORDER[0],
        }
    elif field == "media_size_bytes":
        updates = {field: cast(int, current) + 1}
    elif field.endswith("_sha256"):
        updates = {field: "ab" * 32 if current != "ab" * 32 else "cd" * 32}
    else:
        updates = {field: cast(str, current) + "_mutated"}
    mutated_target = (
        role_module.GeneratedReferenceEligibleAssetRoleBindingTargetV1.model_validate(
            role_module._arrays_to_tuples(_target_payload(operation.target, updates))
        )
    )
    mutated_request = _rehash_request(
        operation.request, {"requested_role_binding_target": mutated_target}
    )
    decision_updates = {
        name: getattr(mutated_request, name)
        for name in role_module._DECISION_REQUEST_LINK_FIELDS
    }
    mutated_decision = _rehash_decision(operation.result.decision, decision_updates)
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )

    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation,
            _unchecked_finalization(mutated_decision, binding),
            request=mutated_request,
        )
    assert error.value.code == "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID"


def test_expected_request_target_drift_is_owned_by_role_stage(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    mutated_request = _rehash_request(
        operation.request,
        {"requested_role_binding_target": known_answers.rejected.target},
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as request_error:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            mutated_request,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
        )
    assert request_error.value.code == "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID"
    decision_updates = {
        name: getattr(mutated_request, name)
        for name in role_module._DECISION_REQUEST_LINK_FIELDS
    }
    mutated_decision = _rehash_decision(operation.result.decision, decision_updates)
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation,
            _unchecked_finalization(mutated_decision, binding),
            request=mutated_request,
        )
    assert error.value.code == "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID"


def test_synchronized_request_primary_drift_is_owned_by_primary_stage(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    primary = _mutated_primary_binding(operation.request.requested_primary_asset_binding)
    mutated_request = _rehash_request(
        operation.request, {"requested_primary_asset_binding": primary}
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as request_error:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            mutated_request,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
        )
    assert request_error.value.code == "PRIMARY_ASSET_BINDING_CLOSURE_INVALID"

    decision_updates = {
        name: getattr(mutated_request, name)
        for name in role_module._DECISION_REQUEST_LINK_FIELDS
    }
    decision_updates["binding_primary_asset_binding"] = primary
    mutated_decision = _rehash_decision(operation.result.decision, decision_updates)
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as final_error:
        _verify_finalization(
            operation,
            _unchecked_finalization(mutated_decision, binding),
            request=mutated_request,
        )
    assert final_error.value.code == "PRIMARY_ASSET_BINDING_CLOSURE_INVALID"


@pytest.mark.parametrize("field", role_module._REQUEST_STATUS_LINK_FIELDS)
def test_synchronized_request_status_drift_is_owned_by_status_stage(
    known_answers: _KnownAnswers,
    field: str,
) -> None:
    operation = known_answers.positive
    current = getattr(operation.request, field)
    if field == "requested_as_of":
        updates: dict[str, object] = {
            "requested_as_of": "2026-08-29T06:00:01Z",
            "requested_at": "2026-08-29T06:00:01Z",
            "maker_prepared_at": "2026-08-29T06:00:01Z",
        }
    elif field == "requested_as_of_status":
        updates = {field: "EXPIRED"}
    elif field == "requested_status_valid_until":
        updates = {field: "2099-01-01T00:00:00Z"}
    elif field.endswith("_sha256"):
        updates = {field: "ab" * 32 if current != "ab" * 32 else "cd" * 32}
    else:
        updates = {field: cast(str, current) + "_mutated"}
    preview = operation.request.model_copy(update=updates)
    updates["request_valid_until"] = role_module._request_valid_until(
        requested_at=preview.requested_at,
        qualification_valid_until=preview.qualification_valid_until,
        manifest_valid_until=preview.manifest_valid_until,
        status_valid_until=preview.requested_status_valid_until,
    )
    mutated_request = _rehash_request(operation.request, updates)
    decision_updates = {
        name: getattr(mutated_request, name)
        for name in role_module._DECISION_REQUEST_LINK_FIELDS
    }
    mutated_decision = _rehash_decision(operation.result.decision, decision_updates)
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation,
            _unchecked_finalization(mutated_decision, binding),
            request=mutated_request,
        )
    expected_code = (
        "CONTRACT_FIELD_INVALID"
        if field == "requested_as_of_status"
        else "CURRENT_STATUS_REPLAY_INVALID"
    )
    assert error.value.code == expected_code


def test_expected_request_status_drift_is_owned_by_status_stage(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    mutated = _rehash_request(
        operation.request,
        {"requested_status_record_id": operation.request.requested_status_record_id + "_mutated"},
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            mutated,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
        )
    assert error.value.code == "CURRENT_STATUS_REPLAY_INVALID"


def test_synchronized_request_rights_drift_is_owned_by_rights_stage(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    scope = operation.request.reviewed_rights_scope.model_copy(
        update={
            "review_basis": (
                operation.request.reviewed_rights_scope.review_basis
                + " Synthetic mutation."
            )
        }
    )
    mutated_request = _rehash_request(
        operation.request, {"reviewed_rights_scope": scope}
    )
    decision_updates = {
        name: getattr(mutated_request, name)
        for name in role_module._DECISION_REQUEST_LINK_FIELDS
    }
    mutated_decision = _rehash_decision(operation.result.decision, decision_updates)
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation,
            _unchecked_finalization(mutated_decision, binding),
            request=mutated_request,
        )
    assert error.value.code == "RIGHTS_SCOPE_MISMATCH"


@pytest.mark.parametrize("native_stage", ("target", "primary", "status", "rights"))
def test_synchronized_request_native_drift_does_not_precede_promotion_replay(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
    native_stage: str,
) -> None:
    operation = known_answers.positive
    if native_stage == "target":
        updates: dict[str, object] = {
            "requested_role_binding_target": known_answers.rejected.target
        }
    elif native_stage == "primary":
        updates = {
            "requested_primary_asset_binding": _mutated_primary_binding(
                operation.request.requested_primary_asset_binding
            )
        }
    elif native_stage == "status":
        updates = {
            "requested_status_record_id": (
                operation.request.requested_status_record_id + "_mutated"
            )
        }
    else:
        updates = {
            "reviewed_rights_scope": operation.request.reviewed_rights_scope.model_copy(
                update={
                    "review_basis": (
                        operation.request.reviewed_rights_scope.review_basis
                        + " Synthetic mutation."
                    )
                }
            )
        }
    mutated_request = _rehash_request(operation.request, updates)
    decision_updates = {
        name: getattr(mutated_request, name)
        for name in role_module._DECISION_REQUEST_LINK_FIELDS
    }
    if native_stage == "primary":
        decision_updates["binding_primary_asset_binding"] = (
            mutated_request.requested_primary_asset_binding
        )
    mutated_decision = _rehash_decision(operation.result.decision, decision_updates)
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )

    def fail_promotion(*args: object, **kwargs: object) -> Any:
        raise role_module.GeneratedReferenceRoleBindingError(
            "PROMOTION_CLOSURE_INVALID", "synthetic stage-7 Promotion failure"
        )

    monkeypatch.setattr(role_module, "_verify_promotion_closure", fail_promotion)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation,
            _unchecked_finalization(mutated_decision, binding),
            request=mutated_request,
        )
    assert error.value.code == "PROMOTION_CLOSURE_INVALID"


@pytest.mark.parametrize("actor", ("maker", "checker"))
@pytest.mark.parametrize(
    "occupied_surface", ("final_status", "final_primary", "checker_identity")
)
def test_finalization_actions_cannot_alias_final_only_evidence_or_identity(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
    actor: str,
    occupied_surface: str,
) -> None:
    operation = known_answers.positive
    final_status = operation.materials.promotion.final_status
    final_primary = operation.materials.primary
    binding_primary_bible: CharacterBible | None = None
    binding_primary_asset_version: CharacterAssetVersion | None = None
    gates = operation.gates
    binding_at = operation.materials.promotion.promotion_at
    if occupied_surface == "final_status":
        binding_at = role_module._format_utc(
            role_module._parse_utc(binding_at, field="binding_at")
            + timedelta(seconds=1)
        )
        fresh_receipt = (
            process_generated_reference_current_status_record_as_of_assessment(
                final_status.record,
                operation.materials.promotion.upstream.manifest,
                final_status.chain_inputs,
                as_of=binding_at,
            ).receipt
        )
        final_status = replace(final_status, receipt=fresh_receipt)
        alias = fresh_receipt.receipt_sha256
    elif occupied_surface == "final_primary":
        bible = cast(
            CharacterBible,
            operation.materials.promotion.promotion_primary_bible,
        )
        asset = cast(
            CharacterAssetVersion,
            operation.materials.promotion.promotion_primary_asset_version,
        )
        description = f"{asset.visual_description} Alias-isolation drift."
        drift_asset = CharacterAssetVersion(
            id=CharacterAssetVersion.derive_id(
                character_id=asset.character_id,
                version=asset.version + 1,
                content_sha256="ab" * 32,
                media_type="image/png",
                approval_ref="synthetic_alias_isolation_review",
                visual_description=description,
            ),
            character_id=asset.character_id,
            version=asset.version + 1,
            content_sha256="ab" * 32,
            media_type="image/png",
            approval_ref="synthetic_alias_isolation_review",
            visual_description=description,
            provenance="IMPORTED_APPROVED_MEDIA",
        )
        drift_bible = CharacterBible(
            character_id=bible.character_id,
            name=bible.name,
            visual_description=bible.visual_description,
            asset_versions=(*bible.asset_versions, drift_asset),
            active_asset_version_id=drift_asset.id,
        )
        final_primary = (
            promotion_module.build_generated_reference_promotion_primary_asset_binding(
                drift_bible, drift_asset
            )
        )
        binding_primary_bible = drift_bible
        binding_primary_asset_version = drift_asset
        human = _human_values(operation.review)
        gates = role_module._role_binding_gates(
            binding_status="CURRENT",
            primary_binding_matches=False,
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result=cast(
                role_module.GateResult, human[0]["result"]
            ),
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
                str, human[0]["basis"]
            ),
            whole_composite_role_suitability_result=cast(
                role_module.GateResult, human[1]["result"]
            ),
            whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
            non_exclusive_no_transform_boundary_result=cast(
                role_module.GateResult, human[2]["result"]
            ),
            non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
        )
        alias = final_primary.primary_asset_binding_sha256
    else:
        alias = _raw_sha256(operation.materials.checker_identity_bytes)

    checker_action_bytes = _checker_action(
        operation_request=operation.request,
        materials=operation.materials,
        review=operation.review,
        gates=gates,
        final_primary=final_primary,
        final_status=final_status,
        reviewed_at=binding_at,
    )
    base_result = _finalize_positive(
        operation,
        final_status=final_status,
        binding_primary_bible=binding_primary_bible,
        binding_primary_asset_version=binding_primary_asset_version,
        checker_action_bytes=checker_action_bytes,
        binding_at=binding_at,
    )
    request_values = cast(
        dict[str, object], operation.request.model_dump(mode="python")
    )
    request_values.pop("maker_action_sha256")
    preparation_occupied = role_module._collect_sha256_strings(
        (
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            operation.target,
            request_values,
            operation.materials.maker_identity_bytes,
        )
    )
    assert alias not in preparation_occupied

    request = operation.request
    maker_action_bytes = operation.maker_action_bytes
    decision_updates: dict[str, object]
    if actor == "maker":
        request = _rehash_request(request, {"maker_action_sha256": alias})
        checker_action_bytes = _checker_action(
            operation_request=request,
            materials=operation.materials,
            review=operation.review,
            gates=gates,
            final_primary=final_primary,
            final_status=final_status,
            reviewed_at=binding_at,
        )
        decision_updates = {
            **{
                name: getattr(request, name)
                for name in role_module._DECISION_REQUEST_LINK_FIELDS
            },
            "checker_action_sha256": _raw_sha256(checker_action_bytes),
        }
        aliased_action_bytes = maker_action_bytes
    else:
        decision_updates = {"checker_action_sha256": alias}
        aliased_action_bytes = checker_action_bytes
    decision = _rehash_decision(base_result.decision, decision_updates)
    expected = _unchecked_finalization(decision, base_result.binding)
    original_raw_sha256 = role_module._raw_sha256

    def alias_one_action(value: bytes) -> str:
        if value == aliased_action_bytes:
            return alias
        return original_raw_sha256(value)

    monkeypatch.setattr(role_module, "_raw_sha256", alias_one_action)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation,
            expected,
            request=request,
            final_status=final_status,
            binding_primary_bible=binding_primary_bible,
            binding_primary_asset_version=binding_primary_asset_version,
            maker_action_bytes=maker_action_bytes,
            checker_action_bytes=checker_action_bytes,
            binding_at=binding_at,
        )
    assert error.value.code == "ACTION_RECORD_INVALID"


def test_finalization_maker_and_checker_action_digests_must_differ(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = known_answers.positive
    alias = "ab" * 32
    request = _rehash_request(operation.request, {"maker_action_sha256": alias})
    checker_action_bytes = _checker_action(
        operation_request=request,
        materials=operation.materials,
        review=operation.review,
        gates=operation.gates,
        final_primary=operation.materials.primary,
        final_status=operation.materials.promotion.final_status,
        reviewed_at=operation.materials.promotion.promotion_at,
    )
    decision = _rehash_decision(
        operation.result.decision,
        {
            **{
                name: getattr(request, name)
                for name in role_module._DECISION_REQUEST_LINK_FIELDS
            },
            "checker_action_sha256": alias,
        },
    )
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    expected = _unchecked_finalization(decision, binding)
    original_raw_sha256 = role_module._raw_sha256
    aliased_actions = {operation.maker_action_bytes, checker_action_bytes}

    def alias_both_actions(value: bytes) -> str:
        if value in aliased_actions:
            return alias
        return original_raw_sha256(value)

    monkeypatch.setattr(role_module, "_raw_sha256", alias_both_actions)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation,
            expected,
            request=request,
            checker_action_bytes=checker_action_bytes,
        )
    assert error.value.code == "ACTION_RECORD_INVALID"


def test_derived_request_action_alias_precedes_prohibited_boundary(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = known_answers.positive
    request_basis = "/synthetic/prohibited/role-binding-path"
    maker_action = cast(dict[str, object], json.loads(operation.maker_action_bytes))
    maker_action["request_basis"] = request_basis
    maker_action_bytes = _document(maker_action)
    alias = _raw_sha256(maker_action_bytes)
    original_semantic_sha256 = role_module._semantic_sha256

    def collide_with_request(
        domain: bytes, projection: dict[str, object]
    ) -> str:
        if domain == role_module.GENERATED_REFERENCE_ROLE_BINDING_REQUEST_SHA256_DOMAIN:
            return alias
        return original_semantic_sha256(domain, projection)

    monkeypatch.setattr(role_module, "_semantic_sha256", collide_with_request)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as alias_error:
        role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=maker_action_bytes,
            requested_at=operation.materials.promotion.promotion_at,
            request_basis=request_basis,
        )
    assert alias_error.value.code == "ACTION_RECORD_INVALID"

    monkeypatch.setattr(role_module, "_semantic_sha256", original_semantic_sha256)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as later_error:
        role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=maker_action_bytes,
            requested_at=operation.materials.promotion.promotion_at,
            request_basis=request_basis,
        )
    assert later_error.value.code == "PROHIBITED_BOUNDARY_CONNECTION"


def test_maker_action_policy_digest_alias_precedes_prohibited_boundary(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = known_answers.positive
    request_basis = "/synthetic/prohibited/policy-alias-path"
    maker_action = cast(dict[str, object], json.loads(operation.maker_action_bytes))
    maker_action["request_basis"] = request_basis
    maker_action_bytes = _document(maker_action)
    original_raw_sha256 = role_module._raw_sha256

    def collide_with_policy(value: bytes) -> str:
        if value == maker_action_bytes:
            return role_module.GENERATED_REFERENCE_ROLE_BINDING_POLICY_DOCUMENT_SHA256
        return original_raw_sha256(value)

    monkeypatch.setattr(role_module, "_raw_sha256", collide_with_policy)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as alias_error:
        role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=maker_action_bytes,
            requested_at=operation.materials.promotion.promotion_at,
            request_basis=request_basis,
        )
    assert alias_error.value.code == "ACTION_RECORD_INVALID"

    monkeypatch.setattr(role_module, "_raw_sha256", original_raw_sha256)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as later_error:
        role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=maker_action_bytes,
            requested_at=operation.materials.promotion.promotion_at,
            request_basis=request_basis,
        )
    assert later_error.value.code == "PROHIBITED_BOUNDARY_CONNECTION"


@pytest.mark.parametrize("candidate_kind", ("decision", "binding"))
@pytest.mark.parametrize("later_fault", ("time", "authority", "prohibited", "gate"))
def test_derived_final_action_alias_precedes_later_stages(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
    candidate_kind: str,
    later_fault: str,
) -> None:
    operation = known_answers.positive
    alias = _raw_sha256(operation.checker_action_bytes)
    original_semantic_sha256 = role_module._semantic_sha256
    domain_to_alias = (
        role_module.GENERATED_REFERENCE_ROLE_BINDING_DECISION_SHA256_DOMAIN
        if candidate_kind == "decision"
        else role_module.GENERATED_REFERENCE_ROLE_BINDING_SHA256_DOMAIN
    )

    def collide_with_derived_formal(
        domain: bytes, projection: dict[str, object]
    ) -> str:
        if domain == domain_to_alias:
            return alias
        return original_semantic_sha256(domain, projection)

    later_code: role_module.GeneratedReferenceRoleBindingErrorCodeV1
    if later_fault == "time":
        later_code = "TIME_OR_VALIDITY_INVALID"

        def fail_time(*args: object, **kwargs: object) -> None:
            raise role_module.GeneratedReferenceRoleBindingError(
                later_code, "synthetic later time failure"
            )

        monkeypatch.setattr(role_module, "_verify_binding_time_window", fail_time)
    elif later_fault == "authority":
        later_code = "AUTHORITY_SURFACE_NONZERO"

        def fail_authority(*args: object, **kwargs: object) -> None:
            raise role_module.GeneratedReferenceRoleBindingError(
                later_code, "synthetic later authority failure"
            )

        monkeypatch.setattr(role_module, "_verify_zero_authority", fail_authority)
    elif later_fault == "prohibited":
        later_code = "PROHIBITED_BOUNDARY_CONNECTION"

        def fail_prohibited(*args: object, **kwargs: object) -> None:
            raise role_module.GeneratedReferenceRoleBindingError(
                later_code, "synthetic later prohibited failure"
            )

        monkeypatch.setattr(
            role_module, "_verify_no_prohibited_connection", fail_prohibited
        )
    else:
        later_code = "BINDING_GATE_NOT_PASS"
        original_build_identity = role_module._build_identity

        def fail_gate(
            model_type: type[BaseModel],
            values: Mapping[str, object],
        ) -> BaseModel:
            if (
                model_type
                is role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1
            ):
                raise role_module.GeneratedReferenceRoleBindingError(
                    later_code, "synthetic later gate failure"
                )
            return original_build_identity(model_type, values)

        monkeypatch.setattr(role_module, "_build_identity", fail_gate)

    monkeypatch.setattr(
        role_module, "_semantic_sha256", collide_with_derived_formal
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as alias_error:
        _finalize_positive(operation)
    assert alias_error.value.code == "ACTION_RECORD_INVALID"

    monkeypatch.setattr(role_module, "_semantic_sha256", original_semantic_sha256)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as later_error:
        _finalize_positive(operation)
    assert later_error.value.code == later_code


def test_expected_decision_primary_drift_precedes_atomic_pair(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    primary = _mutated_primary_binding(operation.materials.primary)
    gates = list(operation.gates)
    gates[5] = gates[5].model_copy(update={"result": "FAIL"})
    mutated_decision = _rehash_decision(
        operation.result.decision,
        {
            "binding_primary_asset_binding": primary,
            "gate_results": tuple(gates),
            "binding_issue_codes": ("PRIMARY_BINDING_NO_LONGER_ACTIVE",),
            "decision": "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
            "binding_materialization_allowed": False,
        },
    )
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation, _unchecked_finalization(mutated_decision, binding)
        )
    assert error.value.code == "PRIMARY_ASSET_BINDING_CLOSURE_INVALID"


@pytest.mark.parametrize(
    "field",
    (
        "status_subject_closure_id",
        "status_subject_closure_sha256",
        "binding_status_record_id",
        "binding_status_record_sha256",
        "binding_status_receipt_id",
        "binding_status_receipt_sha256",
        "binding_explicit_chain_set_sha256",
        "binding_coverage_set_sha256",
        "binding_joint_replay_sha256",
        "binding_as_of_assessment_sha256",
        "binding_as_of_status",
        "binding_status_valid_until",
    ),
)
def test_expected_decision_every_final_status_drift_precedes_atomic_pair(
    known_answers: _KnownAnswers,
    field: str,
) -> None:
    operation = known_answers.positive
    current = getattr(operation.result.decision, field)
    updates: dict[str, object]
    if field == "binding_as_of_status":
        gates = list(operation.gates)
        gates[4] = gates[4].model_copy(update={"result": "FAIL"})
        updates = {
            field: "EXPIRED",
            "gate_results": tuple(gates),
            "binding_issue_codes": ("STATUS_NOT_CURRENT_AT_ROLE_BINDING",),
            "decision": "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
            "binding_materialization_allowed": False,
        }
    elif field == "binding_status_valid_until":
        updates = {field: "2099-01-01T00:00:00Z"}
    elif field.endswith("_sha256"):
        updates = {field: "ab" * 32 if current != "ab" * 32 else "cd" * 32}
    else:
        updates = {field: cast(str, current) + "_mutated"}
    mutated_decision = _rehash_decision(operation.result.decision, updates)
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation, _unchecked_finalization(mutated_decision, binding)
        )
    assert error.value.code == "CURRENT_STATUS_REPLAY_INVALID"


@pytest.mark.parametrize(
    "field", ("checker_identity_ref_sha256", "checker_action_sha256")
)
def test_expected_decision_checker_anchor_drift_precedes_atomic_pair(
    known_answers: _KnownAnswers,
    field: str,
) -> None:
    operation = known_answers.positive
    mutated_decision = _rehash_decision(
        operation.result.decision, {field: "ab" * 32}
    )
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation, _unchecked_finalization(mutated_decision, binding)
        )
    assert error.value.code == "ACTION_RECORD_INVALID"


@pytest.mark.parametrize("component", ("decision_basis", "decision_tuple"))
def test_expected_decision_checker_tuple_drift_is_action_invalid(
    known_answers: _KnownAnswers,
    component: str,
) -> None:
    operation = known_answers.positive
    if component == "decision_basis":
        updates: dict[str, object] = {
            "decision_basis": operation.result.decision.decision_basis
            + " Synthetic mutation."
        }
        binding = cast(
            role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
            operation.result.binding,
        )
    else:
        gates = list(operation.gates)
        gates[8] = gates[8].model_copy(update={"result": "FAIL"})
        updates = {
            "gate_results": tuple(gates),
            "binding_issue_codes": (
                "EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTATION_NOT_ACKNOWLEDGED",
            ),
            "decision": "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
            "binding_materialization_allowed": False,
        }
        binding = None
    mutated_decision = _rehash_decision(operation.result.decision, updates)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation, _unchecked_finalization(mutated_decision, binding)
        )
    assert error.value.code == "ACTION_RECORD_INVALID"


def test_expected_decision_time_drift_precedes_atomic_pair(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    mutated_decision = _rehash_decision(
        operation.result.decision,
        {
            "checker_reviewed_at": "2000-01-01T00:00:00Z",
            "decision_at": "2000-01-01T00:00:00Z",
            "binding_at": "2000-01-01T00:00:00Z",
        },
    )
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation, _unchecked_finalization(mutated_decision, binding)
        )
    assert error.value.code == "TIME_OR_VALIDITY_INVALID"


def test_every_positive_decision_to_binding_linkage_row_is_atomic(
    known_answers: _KnownAnswers,
) -> None:
    decision = known_answers.positive.result.decision
    binding = known_answers.positive.result.binding
    assert binding is not None
    shared_fields = (
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "request_id",
        "request_sha256",
        "decision_id",
        "decision_sha256",
        "promotion_request_id",
        "promotion_request_sha256",
        "promotion_decision_id",
        "promotion_decision_sha256",
        "eligible_asset_sidecar_id",
        "eligible_asset_sidecar_sha256",
        "promotion_at",
        "promotion_evidence_valid_until",
        "qualification_decision_id",
        "qualification_decision_sha256",
        "qualification_valid_until",
        "manifest_id",
        "manifest_sha256",
        "manifest_valid_until",
        "reviewed_rights_scope",
        "status_subject_closure_id",
        "status_subject_closure_sha256",
        "binding_status_record_id",
        "binding_status_record_sha256",
        "binding_status_receipt_id",
        "binding_status_receipt_sha256",
        "binding_explicit_chain_set_sha256",
        "binding_coverage_set_sha256",
        "binding_joint_replay_sha256",
        "binding_as_of_assessment_sha256",
        "binding_as_of_status",
        "binding_at",
        "binding_status_valid_until",
        "role_binding_exclusivity_asserted",
        "complete_role_set_asserted",
        "global_role_uniqueness_asserted",
        "crop_applied",
        "split_applied",
        "transform_applied",
        "derived_media_created",
        "provider_input_eligible",
        "evidence_scope",
        *role_module._ZERO_AUTHORITY_VALUES,
    )
    for name in shared_fields:
        drifted = binding.model_copy(update={name: None})
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
            role_module._verify_positive_pair_linkage(decision, drifted)
        assert error.value.code == "ATOMIC_OUTPUT_INVARIANT_VIOLATION"
    for name in ("role_binding_target", "primary_asset_binding"):
        drifted = binding.model_copy(update={name: None})
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
            role_module._verify_positive_pair_linkage(decision, drifted)
        assert error.value.code == "ATOMIC_OUTPUT_INVARIANT_VIOLATION"


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    (
        ("EXPANSION", "RIGHTS_SCOPE_MISMATCH"),
        ("NARROWING", "CONTRACT_FIELD_INVALID"),
        ("RENEWAL_OR_EXTENSION", "RIGHTS_SCOPE_MISMATCH"),
    ),
)
def test_rights_scope_expansion_narrowing_reorder_and_renewal_are_rejected(
    known_answers: _KnownAnswers,
    mutation: str,
    expected_code: str,
) -> None:
    operation = known_answers.positive
    scope = operation.request.reviewed_rights_scope
    if mutation == "EXPANSION":
        updates: dict[str, object] = {
            "allowed_use_scope": (
                *scope.allowed_use_scope,
                "SYNTHETIC_SCOPE_EXPANSION",
            )
        }
    elif mutation == "NARROWING":
        updates = {"allowed_use_scope": ()}
    else:
        updates = {"reviewed_scope_valid_until": "2026-08-31T02:00:00Z"}
    changed_scope = scope.model_copy(update=updates)
    forged = _rehash_request(operation.request, {"reviewed_rights_scope": changed_scope})
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _finalize_positive(operation, request=forged)
    assert error.value.code == expected_code


def test_rights_scope_same_members_reorder_is_rejected(
    known_answers: _KnownAnswers,
) -> None:
    scope = known_answers.positive.request.reviewed_rights_scope
    values = cast(dict[str, object], scope.model_dump(mode="python"))
    ordered = (
        "ADDITIONAL_SYNTHETIC_TEST_SCOPE",
        *scope.allowed_use_scope,
    )
    values["allowed_use_scope"] = ordered
    valid_two_member_scope = type(scope).model_validate(values)
    reordered_values = cast(
        dict[str, object], valid_two_member_scope.model_dump(mode="python")
    )
    reordered_values["allowed_use_scope"] = tuple(reversed(ordered))
    with pytest.raises(ValidationError):
        type(scope).model_validate(reordered_values)


def test_valid_same_subject_primary_drift_is_decision_only(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    bible = cast(CharacterBible, operation.materials.promotion.promotion_primary_bible)
    asset = cast(
        CharacterAssetVersion,
        operation.materials.promotion.promotion_primary_asset_version,
    )
    description = f"{asset.visual_description} Synthetic Role-Binding drift."
    drift_asset = CharacterAssetVersion(
        id=CharacterAssetVersion.derive_id(
            character_id=asset.character_id,
            version=asset.version + 1,
            content_sha256="ab" * 32,
            media_type="image/png",
            approval_ref="synthetic_role_binding_drift_review",
            visual_description=description,
        ),
        character_id=asset.character_id,
        version=asset.version + 1,
        content_sha256="ab" * 32,
        media_type="image/png",
        approval_ref="synthetic_role_binding_drift_review",
        visual_description=description,
        provenance="IMPORTED_APPROVED_MEDIA",
    )
    drift_bible = CharacterBible(
        character_id=bible.character_id,
        name=bible.name,
        visual_description=bible.visual_description,
        asset_versions=(*bible.asset_versions, drift_asset),
        active_asset_version_id=drift_asset.id,
    )
    final_primary = promotion_module.build_generated_reference_promotion_primary_asset_binding(
        drift_bible, drift_asset
    )
    human = _human_values(operation.review)
    gates = role_module._role_binding_gates(
        binding_status="CURRENT",
        primary_binding_matches=False,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result="PASS",
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
            str, human[0]["basis"]
        ),
        whole_composite_role_suitability_result="PASS",
        whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
        non_exclusive_no_transform_boundary_result="PASS",
        non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
    )
    checker_action = _checker_action(
        operation_request=operation.request,
        materials=operation.materials,
        review=operation.review,
        gates=gates,
        final_primary=final_primary,
    )
    result = role_module.finalize_generated_reference_eligible_asset_role_binding(
        operation.request,
        operation.materials.promotion,
        operation.materials.promotion.final_status,
        bible,
        asset,
        operation.materials.promotion.final_status,
        drift_bible,
        drift_asset,
        operation.materials.admitted_png,
        selected_reference_role=operation.target.selected_reference_role,
        maker_identity_bytes=operation.materials.maker_identity_bytes,
        maker_action_bytes=operation.maker_action_bytes,
        checker_identity_bytes=operation.materials.checker_identity_bytes,
        checker_action_bytes=checker_action,
        binding_at=operation.materials.promotion.promotion_at,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result="PASS",
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
            str, human[0]["basis"]
        ),
        whole_composite_role_suitability_result="PASS",
        whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
        non_exclusive_no_transform_boundary_result="PASS",
        non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
        decision_basis=cast(str, operation.review["decision_basis"]),
    )
    assert result.binding is None
    assert result.decision.decision == "REJECT_ELIGIBLE_ASSET_ROLE_BINDING"
    assert result.decision.binding_issue_codes == (
        "PRIMARY_BINDING_NO_LONGER_ACTIVE",
    )


def test_forged_primary_binding_and_character_scene_crossing_fail_closed(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    forged_primary = operation.materials.primary.model_copy(
        update={"primary_asset_binding_sha256": "00" * 32}
    )
    with pytest.raises(promotion_module.GeneratedReferenceAssetPromotionError) as forged_error:
        role_module.build_generated_reference_role_binding_review_payload_projection(
            operation.target,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            forged_primary,
            requested_at=operation.materials.promotion.promotion_at,
        )
    assert forged_error.value.code == "CONTRACT_FIELD_INVALID"

    scene = known_answers.scene_materials.promotion
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as crossing_error:
        role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            scene.promotion_primary_bible,
            scene.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
            requested_at=operation.materials.promotion.promotion_at,
            request_basis=cast(str, operation.review["request_basis"]),
        )
    assert crossing_error.value.code == "PRIMARY_ASSET_BINDING_CLOSURE_INVALID"


def test_checker_semantically_differs_from_all_eight_frozen_roles(
    known_answers: _KnownAnswers,
) -> None:
    identities = tuple(_identity_bytes(ordinal) for ordinal in range(9))
    semantic_tuples = tuple(
        role_module._human_identity(identity, field="synthetic matrix identity")[0]
        for identity in identities
    )
    assert len(set(semantic_tuples)) == 9
    original = known_answers.character_materials.promotion
    matrix_promotion = replace(
        original,
        upstream=replace(
            original.upstream,
            qualifier_identity_bytes=identities[1],
            manifest_checker_identity_bytes=identities[2],
        ),
        request_status=replace(
            original.request_status,
            status_checker_identity_bytes=identities[3],
        ),
        final_status=replace(
            original.final_status,
            status_checker_identity_bytes=identities[4],
        ),
        checker_identity_bytes=identities[5],
    )
    role_request_status = replace(
        original.final_status,
        status_checker_identity_bytes=identities[6],
    )
    role_final_status = replace(
        original.final_status,
        status_checker_identity_bytes=identities[7],
    )
    for identity in identities[:8]:
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
            role_module._verify_role_separation(
                promotion=matrix_promotion,
                request_status=role_request_status,
                final_status=role_final_status,
                maker_identity_bytes=identities[0],
                checker_identity_bytes=identity,
            )
        assert error.value.code == "ROLE_SEPARATION_VIOLATION"
    maker_sha, checker_sha = role_module._verify_role_separation(
        promotion=matrix_promotion,
        request_status=role_request_status,
        final_status=role_final_status,
        maker_identity_bytes=identities[0],
        checker_identity_bytes=identities[8],
    )
    assert maker_sha == _raw_sha256(identities[0])
    assert checker_sha == _raw_sha256(identities[8])


def test_byte_identical_maker_identity_reuse_with_allowed_upstream_role(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    shared = operation.materials.promotion.upstream.qualification_preparer_identity_bytes
    maker_action = cast(dict[str, object], json.loads(operation.maker_action_bytes))
    maker_action["actor_ref_sha256"] = _raw_sha256(shared)
    maker_action_bytes = _document(maker_action)
    request = role_module.prepare_generated_reference_eligible_asset_role_binding_request(
        operation.materials.promotion,
        operation.materials.promotion.final_status,
        operation.materials.promotion.promotion_primary_bible,
        operation.materials.promotion.promotion_primary_asset_version,
        operation.materials.admitted_png,
        selected_reference_role=operation.target.selected_reference_role,
        maker_identity_bytes=shared,
        maker_action_bytes=maker_action_bytes,
        requested_at=operation.materials.promotion.promotion_at,
        request_basis=cast(str, operation.review["request_basis"]),
    )
    assert request.maker_identity_ref_sha256 == _raw_sha256(shared)
    maker_sha, checker_sha = role_module._verify_role_separation(
        promotion=operation.materials.promotion,
        request_status=operation.materials.promotion.final_status,
        final_status=operation.materials.promotion.final_status,
        maker_identity_bytes=shared,
        checker_identity_bytes=operation.materials.checker_identity_bytes,
    )
    assert maker_sha == _raw_sha256(shared)
    assert checker_sha == _raw_sha256(operation.materials.checker_identity_bytes)


@pytest.mark.parametrize("actor", ("maker", "checker"))
def test_identity_raw_digest_collision_with_different_upstream_bytes_is_rejected(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
    actor: str,
) -> None:
    operation = known_answers.positive
    upstream = (
        operation.materials.promotion.upstream.qualification_preparer_identity_bytes
    )
    role_identity = (
        operation.materials.maker_identity_bytes
        if actor == "maker"
        else operation.materials.checker_identity_bytes
    )
    assert role_identity != upstream
    original_raw_sha256 = role_module._raw_sha256
    colliding = {role_identity, upstream}

    def force_collision(value: bytes) -> str:
        if value in colliding:
            return "ab" * 32
        return original_raw_sha256(value)

    monkeypatch.setattr(role_module, "_raw_sha256", force_collision)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        role_module._verify_role_separation(
            promotion=operation.materials.promotion,
            request_status=operation.materials.promotion.final_status,
            final_status=operation.materials.promotion.final_status,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            checker_identity_bytes=operation.materials.checker_identity_bytes,
        )
    assert error.value.code == "ROLE_SEPARATION_VIOLATION"


def test_request_preparation_rejects_identity_raw_digest_collision(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = known_answers.positive
    upstream = (
        operation.materials.promotion.upstream.qualification_preparer_identity_bytes
    )
    maker = operation.materials.maker_identity_bytes
    assert maker != upstream
    original_raw_sha256 = role_module._raw_sha256
    colliding = {maker, upstream}

    def force_collision(value: bytes) -> str:
        if value in colliding:
            return "ab" * 32
        return original_raw_sha256(value)

    monkeypatch.setattr(role_module, "_raw_sha256", force_collision)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=maker,
            maker_action_bytes=operation.maker_action_bytes,
            requested_at=operation.materials.promotion.promotion_at,
            request_basis=cast(str, operation.review["request_basis"]),
        )
    assert error.value.code == "ROLE_SEPARATION_VIOLATION"


def test_zero_authority_prohibited_connection_and_status_priority(
    known_answers: _KnownAnswers, monkeypatch: pytest.MonkeyPatch
) -> None:
    operation = known_answers.positive
    for formal in (
        operation.request,
        operation.result.decision,
        cast(
            role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
            operation.result.binding,
        ),
    ):
        for name, frozen_value in role_module._ZERO_AUTHORITY_VALUES.items():
            assert getattr(formal, name) == frozen_value
        assert formal.provider_input_eligible is False

    authority = _rehash_request(operation.request, {"provider_requests": 1})
    original_status = role_module._verify_status_closure

    def fail_status(*args: object, **kwargs: object) -> Any:
        raise role_module.GeneratedReferenceRoleBindingError(
            "CURRENT_STATUS_REPLAY_INVALID", "synthetic earlier-stage failure"
        )

    monkeypatch.setattr(role_module, "_verify_status_closure", fail_status)
    human = _human_values(operation.review)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as priority:
        role_module.finalize_generated_reference_eligible_asset_role_binding(
            authority,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
            checker_identity_bytes=operation.materials.checker_identity_bytes,
            checker_action_bytes=operation.checker_action_bytes,
            binding_at=operation.materials.promotion.promotion_at,
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result="PASS",
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
                str, human[0]["basis"]
            ),
            whole_composite_role_suitability_result="PASS",
            whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
            non_exclusive_no_transform_boundary_result="PASS",
            non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
            decision_basis=cast(str, operation.review["decision_basis"]),
        )
    assert priority.value.code == "CURRENT_STATUS_REPLAY_INVALID"
    monkeypatch.setattr(role_module, "_verify_status_closure", original_status)

    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as authority_error:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            authority,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
        )
    assert authority_error.value.code == "AUTHORITY_SURFACE_NONZERO"

    action_value = cast(dict[str, object], json.loads(operation.maker_action_bytes))
    action_value["request_basis"] = "/prohibited/local/path"
    prohibited_action = _document(action_value)
    prohibited = _rehash_request(
        operation.request,
        {
            "request_basis": "/prohibited/local/path",
            "maker_action_sha256": _raw_sha256(prohibited_action),
        },
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as path_error:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            prohibited,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=prohibited_action,
        )
    assert path_error.value.code == "PROHIBITED_BOUNDARY_CONNECTION"

    authority_and_prohibited = _rehash_request(
        prohibited, {"provider_requests": 1}
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as ordered:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            authority_and_prohibited,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=prohibited_action,
        )
    assert ordered.value.code == "AUTHORITY_SURFACE_NONZERO"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("provider_input_eligible", True),
        ("provider_slot", "synthetic-slot"),
        ("input_material", {"sha256": "ab" * 32}),
        ("provider_request", {"attempts": 1}),
        ("executable_route", "provider://synthetic"),
        ("runtime", "remote"),
        ("credential", "synthetic-secret"),
        ("cost", 1),
        ("retry", 1),
        ("publication", True),
        ("retention", True),
        ("training", True),
    ),
)
def test_provider_runtime_and_execution_surface_cannot_be_injected(
    known_answers: _KnownAnswers,
    field: str,
    value: object,
) -> None:
    request_values = cast(
        dict[str, object], known_answers.positive.request.model_dump(mode="python")
    )
    request_values[field] = value
    with pytest.raises(ValidationError):
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1.model_validate(
            request_values
        )


def test_representative_promotion_png_role_primary_status_stage_priority(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = known_answers.positive
    sidecar = operation.materials.promotion.result.sidecar
    assert sidecar is not None
    original_png = operation.materials.admitted_png
    changed_png_bytes = original_png.png_bytes[:-1] + bytes(
        [original_png.png_bytes[-1] ^ 1]
    )
    changed_png = role_module.GeneratedReferenceRoleBindingAdmittedPng(
        png_bytes=changed_png_bytes,
        media_content_sha256=_raw_sha256(changed_png_bytes),
        media_size_bytes=len(changed_png_bytes),
        media_technical_record_sha256=original_png.media_technical_record_sha256,
    )
    scene = known_answers.scene_materials.promotion

    def prepare(
        *,
        admitted_png: role_module.GeneratedReferenceRoleBindingAdmittedPng,
        selected_role: str,
        bible: object | None = None,
        asset: object | None = None,
    ) -> object:
        return role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            cast(
                Any,
                bible
                if bible is not None
                else operation.materials.promotion.promotion_primary_bible,
            ),
            cast(
                Any,
                asset
                if asset is not None
                else operation.materials.promotion.promotion_primary_asset_version,
            ),
            admitted_png,
            selected_reference_role=selected_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
            requested_at=operation.materials.promotion.promotion_at,
            request_basis=cast(str, operation.review["request_basis"]),
        )

    def pass_promotion(
        closure: role_module.GeneratedReferenceRoleBindingPromotionClosureInput,
    ) -> tuple[object, object]:
        return closure.request, sidecar

    def fail_promotion(*args: object, **kwargs: object) -> Any:
        raise role_module.GeneratedReferenceRoleBindingError(
            "PROMOTION_CLOSURE_INVALID", "synthetic Promotion failure"
        )

    def fail_status(*args: object, **kwargs: object) -> Any:
        raise role_module.GeneratedReferenceRoleBindingError(
            "CURRENT_STATUS_REPLAY_INVALID", "synthetic status failure"
        )

    with monkeypatch.context() as patcher:
        patcher.setattr(role_module, "_verify_promotion_closure", fail_promotion)
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
            prepare(
                admitted_png=changed_png,
                selected_role="SCENE_LIGHTING_REFERENCE",
            )
        assert error.value.code == "PROMOTION_CLOSURE_INVALID"

    with monkeypatch.context() as patcher:
        patcher.setattr(role_module, "_verify_promotion_closure", pass_promotion)
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
            prepare(
                admitted_png=changed_png,
                selected_role="SCENE_LIGHTING_REFERENCE",
            )
        assert error.value.code == "PNG_ADMISSION_INVALID"

    with monkeypatch.context() as patcher:
        patcher.setattr(role_module, "_verify_promotion_closure", pass_promotion)
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
            prepare(
                admitted_png=original_png,
                selected_role="SCENE_LIGHTING_REFERENCE",
                bible=scene.promotion_primary_bible,
                asset=scene.promotion_primary_asset_version,
            )
        assert error.value.code == "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID"

    with monkeypatch.context() as patcher:
        patcher.setattr(role_module, "_verify_promotion_closure", pass_promotion)
        patcher.setattr(role_module, "_verify_status_closure", fail_status)
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
            prepare(
                admitted_png=original_png,
                selected_role=operation.target.selected_reference_role,
                bible=scene.promotion_primary_bible,
                asset=scene.promotion_primary_asset_version,
            )
        assert error.value.code == "PRIMARY_ASSET_BINDING_CLOSURE_INVALID"

    changed_scope = sidecar.reviewed_rights_scope.model_copy(
        update={"reviewed_scope_valid_until": "2026-08-31T02:00:00Z"}
    )
    changed_sidecar = sidecar.model_copy(
        update={"reviewed_rights_scope": changed_scope}
    )

    def pass_changed_promotion(
        closure: role_module.GeneratedReferenceRoleBindingPromotionClosureInput,
    ) -> tuple[object, object]:
        return closure.request, changed_sidecar

    with monkeypatch.context() as patcher:
        patcher.setattr(
            role_module, "_verify_promotion_closure", pass_changed_promotion
        )
        patcher.setattr(role_module, "_verify_status_closure", fail_status)
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
            prepare(
                admitted_png=original_png,
                selected_role=operation.target.selected_reference_role,
            )
        assert error.value.code == "CURRENT_STATUS_REPLAY_INVALID"


def test_representative_rights_separation_action_time_authority_priority(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = known_answers.positive
    sidecar = operation.materials.promotion.result.sidecar
    assert sidecar is not None
    changed_scope = sidecar.reviewed_rights_scope.model_copy(
        update={"reviewed_scope_valid_until": "2026-08-31T02:00:00Z"}
    )
    changed_sidecar = sidecar.model_copy(
        update={"reviewed_rights_scope": changed_scope}
    )

    def promotion_replay(
        closure: role_module.GeneratedReferenceRoleBindingPromotionClosureInput,
    ) -> tuple[object, object]:
        return closure.request, sidecar

    def changed_promotion_replay(
        closure: role_module.GeneratedReferenceRoleBindingPromotionClosureInput,
    ) -> tuple[object, object]:
        return closure.request, changed_sidecar

    def status_replay(
        closure: promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput,
        *args: object,
        **kwargs: object,
    ) -> object:
        return closure.receipt

    action_values = cast(
        dict[str, object], json.loads(operation.checker_action_bytes)
    )
    action_values["decision"] = "REJECT_ELIGIBLE_ASSET_ROLE_BINDING"
    wrong_action = _document(action_values)
    with monkeypatch.context() as patcher:
        patcher.setattr(
            role_module, "_verify_promotion_closure", changed_promotion_replay
        )
        patcher.setattr(role_module, "_verify_status_closure", status_replay)
        patcher.setattr(
            role_module, "_verify_status_monotonicity", lambda *args, **kwargs: None
        )
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as rights:
            _finalize_positive(
                operation,
                checker_identity_bytes=operation.materials.maker_identity_bytes,
                checker_action_bytes=wrong_action,
            )
        assert rights.value.code == "RIGHTS_SCOPE_MISMATCH"

    with monkeypatch.context() as patcher:
        patcher.setattr(role_module, "_verify_promotion_closure", promotion_replay)
        patcher.setattr(role_module, "_verify_status_closure", status_replay)
        patcher.setattr(
            role_module, "_verify_status_monotonicity", lambda *args, **kwargs: None
        )
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as separation:
            _finalize_positive(
                operation,
                checker_identity_bytes=operation.materials.maker_identity_bytes,
                checker_action_bytes=wrong_action,
            )
        assert separation.value.code == "ROLE_SEPARATION_VIOLATION"

    authority = _rehash_request(operation.request, {"provider_requests": 1})
    deadline = authority.request_valid_until
    fake_receipt = operation.materials.promotion.final_status.receipt.model_copy(
        update={"as_of": deadline}
    )
    fake_final_status = replace(
        operation.materials.promotion.final_status, receipt=fake_receipt
    )
    checker_action = _checker_action(
        operation_request=authority,
        materials=operation.materials,
        review=operation.review,
        gates=operation.gates,
        final_primary=operation.materials.primary,
        final_status=fake_final_status,
        reviewed_at=deadline,
    )
    with monkeypatch.context() as patcher:
        patcher.setattr(role_module, "_verify_promotion_closure", promotion_replay)
        patcher.setattr(role_module, "_verify_status_closure", status_replay)
        patcher.setattr(
            role_module, "_verify_status_monotonicity", lambda *args, **kwargs: None
        )
        with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as time_error:
            _finalize_positive(
                operation,
                request=authority,
                final_status=fake_final_status,
                checker_action_bytes=checker_action,
                binding_at=deadline,
            )
        assert time_error.value.code == "TIME_OR_VALIDITY_INVALID"


def test_gate_failure_precedes_atomic_pair_validation(
    known_answers: _KnownAnswers,
) -> None:
    invalid = object.__new__(role_module.GeneratedReferenceRoleBindingFinalizationResult)
    object.__setattr__(invalid, "decision", known_answers.rejected.result.decision)
    object.__setattr__(invalid, "binding", known_answers.positive.result.binding)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        role_module._validate_finalization_result(invalid)
    assert error.value.code == "BINDING_GATE_NOT_PASS"


def test_multi_fault_priority_and_no_raw_value_error(
    known_answers: _KnownAnswers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = known_answers.positive
    human = _human_values(operation.review)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as document_first:
        role_module.finalize_generated_reference_eligible_asset_role_binding(
            cast(Any, {}),
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=b"{not-json\n",
            checker_identity_bytes=operation.materials.checker_identity_bytes,
            checker_action_bytes=operation.checker_action_bytes,
            binding_at="not-a-time",
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result="PASS",
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
                str, human[0]["basis"]
            ),
            whole_composite_role_suitability_result="PASS",
            whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
            non_exclusive_no_transform_boundary_result="PASS",
            non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
            decision_basis=cast(str, operation.review["decision_basis"]),
        )
    assert document_first.value.code == "INPUT_DOCUMENT_INVALID"

    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as resource_first:
        role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=b" " * 262_145,
            requested_at="not-a-time",
            request_basis="invalid\x00basis",
        )
    assert resource_first.value.code == "INPUT_RESOURCE_LIMIT_EXCEEDED"

    malformed_action = cast(dict[str, object], json.loads(operation.maker_action_bytes))
    malformed_action["policy_document_sha256"] = "00" * 32
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as contract_first:
        role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=_document(malformed_action),
            requested_at="not-a-time",
            request_basis="invalid\x00basis",
        )
    assert contract_first.value.code == "CONTRACT_FIELD_INVALID"

    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as action_before_time:
        role_module.finalize_generated_reference_eligible_asset_role_binding(
            operation.request,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
            checker_identity_bytes=operation.materials.checker_identity_bytes,
            checker_action_bytes=operation.checker_action_bytes,
            binding_at="not-a-time",
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result="PASS",
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
                str, human[0]["basis"]
            ),
            whole_composite_role_suitability_result="PASS",
            whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
            non_exclusive_no_transform_boundary_result="PASS",
            non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
            decision_basis=cast(str, operation.review["decision_basis"]),
        )
    assert action_before_time.value.code == "ACTION_RECORD_INVALID"

    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as verifier_document:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            cast(Any, {}),
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=b"{not-json\n",
        )
    assert verifier_document.value.code == "INPUT_DOCUMENT_INVALID"

    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as final_document:
        role_module.verify_generated_reference_eligible_asset_role_binding_finalization(
            cast(Any, {}),
            operation.request,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
            checker_identity_bytes=operation.materials.checker_identity_bytes,
            checker_action_bytes=b"{not-json\n",
            binding_at=operation.materials.promotion.promotion_at,
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result=(
                "PASS"
            ),
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
                str, human[0]["basis"]
            ),
            whole_composite_role_suitability_result="PASS",
            whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
            non_exclusive_no_transform_boundary_result="PASS",
            non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
            decision_basis=cast(str, operation.review["decision_basis"]),
        )
    assert final_document.value.code == "INPUT_DOCUMENT_INVALID"

    policy_and_identity = operation.request.model_copy(
        update={
            "policy_document_sha256": "00" * 32,
            "request_sha256": "11" * 32,
        }
    )
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as policy_first:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            policy_and_identity,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
        )
    assert policy_first.value.code == "POLICY_IDENTITY_MISMATCH"

    formal_identity = operation.request.model_copy(
        update={"request_sha256": "11" * 32}
    )

    def fail_later_promotion(*args: object, **kwargs: object) -> Any:
        raise role_module.GeneratedReferenceRoleBindingError(
            "PROMOTION_CLOSURE_INVALID", "synthetic later-stage failure"
        )

    monkeypatch.setattr(role_module, "_verify_promotion_closure", fail_later_promotion)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as formal_first:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            formal_identity,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=operation.maker_action_bytes,
        )
    assert formal_first.value.code == "FORMAL_IDENTITY_MISMATCH"

    expected_priority = (
        "INPUT_RESOURCE_LIMIT_EXCEEDED",
        "INPUT_DOCUMENT_INVALID",
        "CONTRACT_FIELD_INVALID",
        "POLICY_IDENTITY_MISMATCH",
        "FORMAL_IDENTITY_MISMATCH",
        "UPSTREAM_CLOSURE_MISMATCH",
        "PROMOTION_CLOSURE_INVALID",
        "PNG_ADMISSION_INVALID",
        "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
        "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
        "CURRENT_STATUS_REPLAY_INVALID",
        "RIGHTS_SCOPE_MISMATCH",
        "ROLE_SEPARATION_VIOLATION",
        "ACTION_RECORD_INVALID",
        "TIME_OR_VALIDITY_INVALID",
        "AUTHORITY_SURFACE_NONZERO",
        "PROHIBITED_BOUNDARY_CONNECTION",
        "BINDING_GATE_NOT_PASS",
        "ATOMIC_OUTPUT_INVARIANT_VIOLATION",
    )
    assert get_args(role_module.GeneratedReferenceRoleBindingErrorCodeV1) == expected_priority
    assert role_module._GENERATED_REFERENCE_ROLE_BINDING_ERROR_PRIORITY == expected_priority


def test_verifiers_scan_every_formal_resource_before_any_document(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    malformed_decision = operation.result.decision.model_copy(
        update={"decision_basis": object()}
    )
    malformed_expected = _unchecked_finalization(malformed_decision, binding)
    oversized_request = operation.request.model_copy(
        update={"request_basis": "x" * 300_000}
    )

    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as final_error:
        _verify_finalization(
            operation,
            malformed_expected,
            request=oversized_request,
        )
    assert final_error.value.code == "INPUT_RESOURCE_LIMIT_EXCEEDED"

    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as request_error:
        role_module.verify_generated_reference_eligible_asset_role_binding_request(
            oversized_request,
            operation.materials.promotion,
            operation.materials.promotion.final_status,
            operation.materials.promotion.promotion_primary_bible,
            operation.materials.promotion.promotion_primary_asset_version,
            operation.materials.admitted_png,
            selected_reference_role=operation.target.selected_reference_role,
            maker_identity_bytes=operation.materials.maker_identity_bytes,
            maker_action_bytes=b"{not-json\n",
        )
    assert request_error.value.code == "INPUT_RESOURCE_LIMIT_EXCEEDED"


def test_expected_authority_precedes_supplied_prohibited_surface(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.positive
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        operation.result.binding,
    )
    maker_action_value = cast(
        dict[str, object], json.loads(operation.maker_action_bytes)
    )
    maker_action_value["request_basis"] = "/prohibited/local/path"
    prohibited_maker_action = _document(maker_action_value)
    prohibited_request = _rehash_request(
        operation.request,
        {
            "request_basis": "/prohibited/local/path",
            "maker_action_sha256": _raw_sha256(prohibited_maker_action),
        },
    )
    checker_action = _checker_action(
        operation_request=prohibited_request,
        materials=operation.materials,
        review=operation.review,
        gates=operation.gates,
        final_primary=operation.materials.primary,
        final_status=operation.materials.promotion.final_status,
        reviewed_at=operation.materials.promotion.promotion_at,
    )
    authority_decision = _rehash_decision(
        operation.result.decision,
        {
            **{
                field: getattr(prohibited_request, field)
                for field in role_module._DECISION_REQUEST_LINK_FIELDS
            },
            "checker_action_sha256": _raw_sha256(checker_action),
            "provider_requests": 1,
        },
    )
    expected = _unchecked_finalization(authority_decision, binding)

    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(
            operation,
            expected,
            request=prohibited_request,
            maker_action_bytes=prohibited_maker_action,
            checker_action_bytes=checker_action,
        )
    assert error.value.code == "AUTHORITY_SURFACE_NONZERO"


def test_nonpositive_expected_decision_with_binding_is_gate_invalid(
    known_answers: _KnownAnswers,
) -> None:
    operation = known_answers.rejected
    binding = cast(
        role_module.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
        known_answers.positive.result.binding,
    )
    invalid_expected = _unchecked_finalization(operation.result.decision, binding)
    with pytest.raises(role_module.GeneratedReferenceRoleBindingError) as error:
        _verify_finalization(operation, invalid_expected)
    assert error.value.code == "BINDING_GATE_NOT_PASS"


def test_reverse_import_and_provider_runtime_isolation() -> None:
    module_path = ROOT / "src/sdc/generated_reference_role_binding.py"
    module_source = module_path.read_text(encoding="utf-8")
    syntax = ast.parse(module_source)
    imports = {
        alias.name
        for node in ast.walk(syntax)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(syntax)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(
        token in imported.casefold()
        for imported in imports
        for token in ("provider_input", "runtime", "compiler", "network", "requests")
    )
    reverse_import_allowlist = {
        "generated_reference_role_binding.py",
        "generated_reference_role_binding_codegen.py",
        "schemas.py",
    }
    reverse_importers = {
        path.name
        for path in (ROOT / "src/sdc").rglob("*.py")
        if "generated_reference_role_binding" in path.read_text(encoding="utf-8")
    }
    assert reverse_importers == reverse_import_allowlist

    forbidden_import_roots = {
        "asyncio",
        "http",
        "random",
        "requests",
        "secrets",
        "socket",
        "sqlite3",
        "subprocess",
        "time",
        "urllib",
        "uuid",
    }
    assert not any(
        imported.split(".", maxsplit=1)[0] in forbidden_import_roots
        for imported in imports
    )
    forbidden_call_names = {
        "connect",
        "getenv",
        "glob",
        "iterdir",
        "listdir",
        "now",
        "random",
        "rglob",
        "scandir",
        "time",
        "urandom",
        "utcnow",
        "uuid4",
        "walk",
    }
    observed_calls = {
        node.func.attr
        if isinstance(node.func, ast.Attribute)
        else node.func.id
        for node in ast.walk(syntax)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert observed_calls.isdisjoint(forbidden_call_names)
    observed_attributes = {
        node.attr for node in ast.walk(syntax) if isinstance(node, ast.Attribute)
    }
    assert observed_attributes.isdisjoint({"environ", *forbidden_call_names})

    pure_entrypoints = {
        "build_generated_reference_eligible_asset_role_binding_target",
        "build_generated_reference_role_binding_review_payload_projection",
        "prepare_generated_reference_eligible_asset_role_binding_request",
        "verify_generated_reference_eligible_asset_role_binding_request",
        "finalize_generated_reference_eligible_asset_role_binding",
        "verify_generated_reference_eligible_asset_role_binding_finalization",
    }
    pure_nodes = {
        node.name: node
        for node in syntax.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in pure_entrypoints
    }
    assert set(pure_nodes) == pure_entrypoints
    for node in pure_nodes.values():
        names = {
            child.id for child in ast.walk(node) if isinstance(child, ast.Name)
        }
        attributes = {
            child.attr for child in ast.walk(node) if isinstance(child, ast.Attribute)
        }
        assert names.isdisjoint({"Path", "fstat", "open"})
        assert attributes.isdisjoint({"open", "read_bytes", "resolve", "stat"})
