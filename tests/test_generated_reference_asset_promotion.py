from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, cast, get_args

import pytest
from pydantic import BaseModel, ValidationError

import sdc.generated_reference_asset_promotion as promotion_module
import sdc.generated_reference_rights_current_status as rights_module
from sdc.contracts import CharacterAssetVersion, CharacterBible, SceneAssetVersion, SceneBible
from sdc.generated_reference_asset_promotion import (
    GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_SHA256_DOMAIN,
    GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256,
    GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST_SHA256_DOMAIN,
    GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
    GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_SHA256_DOMAIN,
    GENERATED_REFERENCE_PRIMARY_ASSET_BINDING_SHA256_DOMAIN,
    GENERATED_REFERENCE_PRIMARY_ASSET_VERSION_PROJECTION_SHA256_DOMAIN,
    PROMOTION_GATE_ORDER,
    CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
    CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
    CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
    GeneratedReferenceAssetPromotionError,
    GeneratedReferenceAssetPromotionErrorCodeV1,
    GeneratedReferenceAssetPromotionFinalizationResult,
    GeneratedReferenceAssetPromotionStatusClosureInput,
    GeneratedReferenceAssetPromotionUpstreamClosureInput,
    GeneratedReferencePromotionGateResultV1,
    GeneratedReferencePromotionPrimaryAssetBindingV1,
    build_generated_reference_promotion_primary_asset_binding,
    creative_sample_generated_reference_asset_promotion_decision_projection,
    creative_sample_generated_reference_asset_promotion_decision_sha256,
    creative_sample_generated_reference_asset_promotion_request_projection,
    creative_sample_generated_reference_asset_promotion_request_sha256,
    creative_sample_generated_reference_eligible_asset_sidecar_projection,
    creative_sample_generated_reference_eligible_asset_sidecar_sha256,
    finalize_generated_reference_asset_promotion,
    generated_reference_asset_promotion_contract_document_bytes,
    generated_reference_asset_promotion_policy_projection,
    generated_reference_asset_promotion_review_payload_projection,
    generated_reference_asset_promotion_review_payload_sha256,
    generated_reference_primary_asset_version_projection,
    generated_reference_primary_asset_version_projection_sha256,
    generated_reference_promotion_primary_asset_binding_projection,
    generated_reference_promotion_primary_asset_binding_sha256,
    prepare_generated_reference_asset_promotion_request,
    verify_generated_reference_asset_promotion_finalization,
    verify_generated_reference_asset_promotion_request,
)
from sdc.generated_reference_candidate import (
    GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256,
    build_generated_reference_provider_attempt_outcome,
    capture_generated_reference_candidate,
    creative_sample_generated_reference_provider_attempt_outcome_projection,
    prepare_generated_reference_candidate_qualification_request,
    record_generated_reference_candidate_qualification_decision,
)
from sdc.generated_reference_rights_current_status import (
    GeneratedReferenceJointReplayError,
    GeneratedReferenceReviewedRightsScopeV1,
    GeneratedReferenceRightsCurrentStatusError,
    GeneratedReferenceRightsManifestEvidenceInput,
    GeneratedReferenceRightsScopeProposalV1,
    process_generated_reference_current_status_record_as_of_assessment,
)

ROOT = Path(__file__).resolve().parents[1]
status_fixtures: Any = importlib.import_module(
    "test_generated_reference_rights_current_status"
)

_ZERO_AUTHORITY = {
    "authority_scope": "THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY",
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

_COMPILER_BASES = (
    "COMPILER_REVALIDATED_EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
    "COMPILER_REVALIDATED_EXACT_SUCCESSFUL_OUTCOME_AND_ARTIFACT",
    "COMPILER_REVALIDATED_POSITIVE_UNEXPIRED_QUALIFICATION",
    "COMPILER_REVALIDATED_VALID_GENERATED_RIGHTS_MANIFEST",
    "COMPILER_REPLAYED_GENERATED_CURRENT_STATUS_AT_PROMOTION",
    "COMPILER_REVALIDATED_FINAL_SUPPLIED_PRIMARY_ASSET_BINDING",
    "COMPILER_REVALIDATED_EXACT_MANIFEST_REVIEWED_RIGHTS_SCOPE",
    "Human association approved.",
    "Human composite role deferral acknowledged.",
    "COMPILER_REVALIDATED_PROMOTION_ROLE_SEPARATION",
)


def _compact(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


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


def _semantic(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _compact(value)).hexdigest()


def _explicit(value: object) -> object:
    if isinstance(value, BaseModel):
        return {
            name: _explicit(getattr(value, name))
            for name in type(value).model_fields
        }
    if type(value) is tuple:
        return [_explicit(item) for item in cast(tuple[object, ...], value)]
    if type(value) is dict:
        return {
            cast(str, key): _explicit(item)
            for key, item in cast(dict[object, object], value).items()
        }
    return value


def _character_binding() -> tuple[
    CharacterBible, CharacterAssetVersion, GeneratedReferencePromotionPrimaryAssetBindingV1
]:
    character_id = CharacterBible.derive_id(
        name="Synthetic Keeper", visual_description="A first-party synthetic design."
    )
    asset_id = CharacterAssetVersion.derive_id(
        character_id=character_id,
        version=1,
        content_sha256="11" * 32,
        media_type="image/png",
        approval_ref="synthetic_primary_review",
        visual_description="Synthetic imported primary sheet.",
    )
    asset = CharacterAssetVersion(
        id=asset_id,
        character_id=character_id,
        version=1,
        content_sha256="11" * 32,
        media_type="image/png",
        approval_ref="synthetic_primary_review",
        visual_description="Synthetic imported primary sheet.",
        provenance="IMPORTED_APPROVED_MEDIA",
    )
    bible = CharacterBible(
        character_id=character_id,
        name="Synthetic Keeper",
        visual_description="A first-party synthetic design.",
        asset_versions=(asset,),
        active_asset_version_id=asset.id,
    )
    return bible, asset, build_generated_reference_promotion_primary_asset_binding(bible, asset)


def _scene_binding() -> tuple[
    SceneBible, SceneAssetVersion, GeneratedReferencePromotionPrimaryAssetBindingV1
]:
    scene_id = SceneBible.derive_id(
        ordinal=0,
        name="Synthetic Atrium",
        visual_description="A first-party synthetic scene.",
    )
    asset_id = SceneAssetVersion.derive_id(
        scene_id=scene_id,
        version=1,
        content_sha256="22" * 32,
        media_type="image/png",
        approval_ref="synthetic_scene_review",
        visual_description="Synthetic imported scene sheet.",
    )
    asset = SceneAssetVersion(
        id=asset_id,
        scene_id=scene_id,
        version=1,
        content_sha256="22" * 32,
        media_type="image/png",
        approval_ref="synthetic_scene_review",
        visual_description="Synthetic imported scene sheet.",
        provenance="IMPORTED_APPROVED_MEDIA",
    )
    bible = SceneBible(
        scene_id=scene_id,
        ordinal=0,
        name="Synthetic Atrium",
        visual_description="A first-party synthetic scene.",
        asset_versions=(asset,),
        active_asset_version_id=asset.id,
    )
    return bible, asset, build_generated_reference_promotion_primary_asset_binding(bible, asset)


def _rights_scope() -> GeneratedReferenceReviewedRightsScopeV1:
    return GeneratedReferenceReviewedRightsScopeV1(
        territory_scope=("SYNTHETIC_TEST_TERRITORY",),
        allowed_use_scope=("SYNTHETIC_REFERENCE_REVIEW",),
        reviewed_scope_valid_until="2026-01-02T00:00:00Z",
        output_copyright_and_commercial_scope_basis="Synthetic scope basis.",
        likeness_privacy_and_sensitive_data_basis="Synthetic privacy basis.",
        brand_and_protected_content_basis="Synthetic brand basis.",
        retention_and_deletion_basis="Synthetic retention basis.",
        training_use_prohibition_basis="Synthetic training basis.",
        review_basis="Synthetic overall review basis.",
    )


def _review_payload(request_values: dict[str, object]) -> dict[str, object]:
    fields = (
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "request_scope",
        "reference_prompt_artifact_sha256",
        "provider_attempt_outcome_id",
        "provider_attempt_outcome_sha256",
        "candidate_id",
        "candidate_sha256",
        "output_ordinal",
        "media_type",
        "media_content_sha256",
        "media_size_bytes",
        "media_technical_record_sha256",
        "qualification_request_id",
        "qualification_request_sha256",
        "qualification_decision_id",
        "qualification_decision_sha256",
        "qualification_decision_at",
        "qualification_valid_until",
        "manifest_id",
        "manifest_sha256",
        "manifest_at",
        "manifest_valid_until",
        "reviewed_rights_scope",
        "status_subject_closure_id",
        "status_subject_closure_sha256",
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
        "requested_primary_asset_binding",
        "requested_at",
        "request_valid_until",
        "request_basis",
        "requested_representation",
        "composite_media_unsplit",
        "role_assignment_embedded",
        "bible_mutation_requested",
        "provider_input_requested",
    )
    return {name: _explicit(request_values[name]) for name in fields}


def _rehash_formal(
    value: BaseModel, updates: dict[str, object], *, refresh_review_payload: bool = False
) -> BaseModel:
    values = cast(dict[str, object], _explicit(value))
    values.update({name: _explicit(item) for name, item in updates.items()})
    if type(value) is CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        id_field = "request_id"
        sha_field = "request_sha256"
        stem = "generated_reference_asset_promotion_request_v1_"
        domain = GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST_SHA256_DOMAIN
        if refresh_review_payload:
            values["promotion_review_payload_sha256"] = _semantic(
                GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
                _review_payload(values),
            )
    elif type(value) is CreativeSampleGeneratedReferenceAssetPromotionDecisionV1:
        id_field = "decision_id"
        sha_field = "decision_sha256"
        stem = "generated_reference_asset_promotion_decision_v1_"
        domain = GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_SHA256_DOMAIN
    elif type(value) is CreativeSampleGeneratedReferenceEligibleAssetSidecarV1:
        id_field = "sidecar_id"
        sha_field = "sidecar_sha256"
        stem = "generated_reference_eligible_asset_sidecar_v1_"
        domain = GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_SHA256_DOMAIN
    else:  # pragma: no cover - test helper guard
        raise AssertionError("unknown formal Contract")
    projection = dict(values)
    projection.pop(id_field)
    projection.pop(sha_field)
    digest = _semantic(domain, projection)
    identity_updates = {**updates, id_field: f"{stem}{digest[:20]}", sha_field: digest}
    if type(value) is CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        identity_updates["promotion_review_payload_sha256"] = values[
            "promotion_review_payload_sha256"
        ]
    return value.model_copy(update=identity_updates)


def _mutated_formal_field(field_name: str, value: object) -> object:
    if isinstance(value, GeneratedReferenceReviewedRightsScopeV1):
        return value.model_copy(update={"review_basis": f"{value.review_basis} Mutated."})
    if isinstance(value, GeneratedReferencePromotionPrimaryAssetBindingV1):
        return value.model_copy(update={"primary_asset_binding_sha256": "00" * 32})
    if type(value) is tuple:
        items = cast(tuple[object, ...], value)
        if items:
            return tuple(reversed(items)) if len(items) > 1 else ()
        if field_name == "promotion_issue_codes":
            return ("PRIMARY_SIDECAR_ASSOCIATION_NOT_APPROVED",)
        return ("mutated",)
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        if len(value) == 64 and all(character in "0123456789abcdef" for character in value):
            return ("0" if value[0] != "0" else "1") + value[1:]
        return f"{value}_mutated"
    raise AssertionError(f"no field mutator for {field_name}: {type(value)!r}")


def _mutated_rights_scope_field(
    scope: GeneratedReferenceReviewedRightsScopeV1, field_name: str
) -> object:
    if field_name == "territory_scope":
        return ("ZZ_SYNTHETIC_MUTATED_TERRITORY",)
    if field_name == "allowed_use_scope":
        return ("ZZ_SYNTHETIC_MUTATED_USE",)
    if field_name == "reviewed_scope_valid_until":
        return "2026-08-30T01:59:59Z"
    value = getattr(scope, field_name)
    assert type(value) is str
    return f"{value} Independently mutated."


def _known_answer_contracts() -> tuple[
    CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
    CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
    CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
]:
    _bible, _asset, binding = _character_binding()
    rights_scope = _rights_scope()
    request_values: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": (
            "sdc.creative-sample-generated-reference-asset-promotion-request-v1"
        ),
        "request_scope": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_ONLY",
        "policy_id": "sdc.generated-reference-asset-promotion-policy",
        "policy_version": "1.0.0",
        "policy_document_sha256": GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256,
        "reference_prompt_artifact_sha256": "31" * 32,
        "provider_attempt_outcome_id": "synthetic_outcome",
        "provider_attempt_outcome_sha256": "32" * 32,
        "candidate_id": "synthetic_candidate",
        "candidate_sha256": "33" * 32,
        "output_ordinal": 0,
        "media_type": "image/png",
        "media_content_sha256": "34" * 32,
        "media_size_bytes": 1024,
        "media_technical_record_sha256": "35" * 32,
        "qualification_request_id": "synthetic_qualification_request",
        "qualification_request_sha256": "36" * 32,
        "qualification_decision_id": "synthetic_qualification_decision",
        "qualification_decision_sha256": "37" * 32,
        "qualification_decision_at": "2025-12-31T23:00:00Z",
        "qualification_valid_until": "2026-01-03T00:00:00Z",
        "manifest_id": "synthetic_manifest",
        "manifest_sha256": "38" * 32,
        "manifest_at": "2025-12-31T23:30:00Z",
        "manifest_valid_until": "2026-01-02T00:00:00Z",
        "reviewed_rights_scope": rights_scope,
        "status_subject_closure_id": "synthetic_status_subject",
        "status_subject_closure_sha256": "39" * 32,
        "requested_status_record_id": "synthetic_requested_record",
        "requested_status_record_sha256": "3a" * 32,
        "requested_status_receipt_id": "synthetic_requested_receipt",
        "requested_status_receipt_sha256": "3b" * 32,
        "requested_explicit_chain_set_sha256": "3c" * 32,
        "requested_coverage_set_sha256": "3d" * 32,
        "requested_joint_replay_sha256": "3e" * 32,
        "requested_as_of_assessment_sha256": "3f" * 32,
        "requested_as_of": "2026-01-01T00:00:00Z",
        "requested_as_of_status": "CURRENT",
        "requested_status_valid_until": "2026-01-01T12:00:00Z",
        "requested_primary_asset_binding": binding,
        "maker_identity_ref_sha256": "40" * 32,
        "maker_action_sha256": "41" * 32,
        "maker_prepared_at": "2026-01-01T00:00:00Z",
        "requested_at": "2026-01-01T00:00:00Z",
        "request_valid_until": "2026-01-01T12:00:00Z",
        "request_basis": "Synthetic promotion request basis.",
        "requested_representation": "TYPED_ELIGIBLE_ASSET_SIDECAR",
        "composite_media_unsplit": True,
        "role_assignment_embedded": False,
        "bible_mutation_requested": False,
        "provider_input_requested": False,
        "promotion_performed": False,
        "sidecar_materialized": False,
        "eligible_for_separate_role_binding_review": False,
        "status": "GENERATED_REFERENCE_ASSET_PROMOTION_REQUESTED",
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
        **_ZERO_AUTHORITY,
    }
    request_values["promotion_review_payload_sha256"] = _semantic(
        GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
        _review_payload(request_values),
    )
    request_sha = _semantic(
        GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST_SHA256_DOMAIN,
        {name: _explicit(value) for name, value in request_values.items()},
    )
    request = CreativeSampleGeneratedReferenceAssetPromotionRequestV1.model_validate(
        {
            "request_id": f"generated_reference_asset_promotion_request_v1_{request_sha[:20]}",
            "request_sha256": request_sha,
            **request_values,
        }
    )

    gates = tuple(
        GeneratedReferencePromotionGateResultV1.model_validate(
            {
                "ordinal": index,
                "gate": gate,
                "result": "PASS",
                "basis": _COMPILER_BASES[index],
            }
        )
        for index, gate in enumerate(PROMOTION_GATE_ORDER)
    )
    decision_values: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": (
            "sdc.creative-sample-generated-reference-asset-promotion-decision-v1"
        ),
        "decision_scope": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_ONLY",
        "policy_id": "sdc.generated-reference-asset-promotion-policy",
        "policy_version": "1.0.0",
        "policy_document_sha256": GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256,
        "promotion_review_payload_sha256": request.promotion_review_payload_sha256,
        "request_id": request.request_id,
        "request_sha256": request.request_sha256,
        "reference_prompt_artifact_sha256": request.reference_prompt_artifact_sha256,
        "provider_attempt_outcome_id": request.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": request.provider_attempt_outcome_sha256,
        "candidate_id": request.candidate_id,
        "candidate_sha256": request.candidate_sha256,
        "media_content_sha256": request.media_content_sha256,
        "qualification_request_id": request.qualification_request_id,
        "qualification_request_sha256": request.qualification_request_sha256,
        "qualification_decision_id": request.qualification_decision_id,
        "qualification_decision_sha256": request.qualification_decision_sha256,
        "qualification_valid_until": request.qualification_valid_until,
        "manifest_id": request.manifest_id,
        "manifest_sha256": request.manifest_sha256,
        "manifest_valid_until": request.manifest_valid_until,
        "reviewed_rights_scope": rights_scope,
        "requested_primary_asset_binding": binding,
        "promotion_primary_asset_binding": binding,
        "status_subject_closure_id": request.status_subject_closure_id,
        "status_subject_closure_sha256": request.status_subject_closure_sha256,
        "promotion_status_record_id": "synthetic_promotion_record",
        "promotion_status_record_sha256": "42" * 32,
        "promotion_status_receipt_id": "synthetic_promotion_receipt",
        "promotion_status_receipt_sha256": "43" * 32,
        "promotion_explicit_chain_set_sha256": "44" * 32,
        "promotion_coverage_set_sha256": "45" * 32,
        "promotion_joint_replay_sha256": "46" * 32,
        "promotion_as_of_assessment_sha256": "47" * 32,
        "promotion_as_of_status": "CURRENT",
        "promotion_status_valid_until": "2026-01-01T12:00:00Z",
        "checker_identity_ref_sha256": "48" * 32,
        "checker_action_sha256": "49" * 32,
        "checker_reviewed_at": "2026-01-01T01:00:00Z",
        "decision_at": "2026-01-01T01:00:00Z",
        "promotion_at": "2026-01-01T01:00:00Z",
        "gate_results": gates,
        "promotion_issue_codes": (),
        "promotion_basis": "Synthetic positive promotion basis.",
        "decision": "APPROVE_ELIGIBLE_ASSET_SIDECAR",
        "sidecar_materialization_allowed": True,
        "promotion_review_performed": True,
        "sidecar_id_embedded": False,
        "role_assignment_embedded": False,
        "provider_input_eligible": False,
        "status": "GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_RECORDED",
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
        **_ZERO_AUTHORITY,
    }
    decision_sha = _semantic(
        GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_SHA256_DOMAIN,
        {name: _explicit(value) for name, value in decision_values.items()},
    )
    decision = CreativeSampleGeneratedReferenceAssetPromotionDecisionV1.model_validate(
        {
            "decision_id": (
                f"generated_reference_asset_promotion_decision_v1_{decision_sha[:20]}"
            ),
            "decision_sha256": decision_sha,
            **decision_values,
        }
    )

    sidecar_values: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": (
            "sdc.creative-sample-generated-reference-eligible-asset-sidecar-v1"
        ),
        "sidecar_scope": "GENERATED_REFERENCE_POST_PROMOTION_HISTORICAL_EVIDENCE_ONLY",
        "policy_id": "sdc.generated-reference-asset-promotion-policy",
        "policy_version": "1.0.0",
        "policy_document_sha256": GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256,
        "request_id": request.request_id,
        "request_sha256": request.request_sha256,
        "decision_id": decision.decision_id,
        "decision_sha256": decision.decision_sha256,
        "reference_prompt_artifact_sha256": request.reference_prompt_artifact_sha256,
        "provider_attempt_outcome_id": request.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": request.provider_attempt_outcome_sha256,
        "candidate_id": request.candidate_id,
        "candidate_sha256": request.candidate_sha256,
        "output_ordinal": 0,
        "media_type": "image/png",
        "media_content_sha256": request.media_content_sha256,
        "media_size_bytes": request.media_size_bytes,
        "media_technical_record_sha256": request.media_technical_record_sha256,
        "qualification_request_id": request.qualification_request_id,
        "qualification_request_sha256": request.qualification_request_sha256,
        "qualification_decision_id": request.qualification_decision_id,
        "qualification_decision_sha256": request.qualification_decision_sha256,
        "qualification_valid_until": request.qualification_valid_until,
        "manifest_id": request.manifest_id,
        "manifest_sha256": request.manifest_sha256,
        "manifest_valid_until": request.manifest_valid_until,
        "reviewed_rights_scope": rights_scope,
        "primary_asset_binding": binding,
        "status_subject_closure_id": request.status_subject_closure_id,
        "status_subject_closure_sha256": request.status_subject_closure_sha256,
        "promotion_status_record_id": decision.promotion_status_record_id,
        "promotion_status_record_sha256": decision.promotion_status_record_sha256,
        "promotion_status_receipt_id": decision.promotion_status_receipt_id,
        "promotion_status_receipt_sha256": decision.promotion_status_receipt_sha256,
        "promotion_explicit_chain_set_sha256": decision.promotion_explicit_chain_set_sha256,
        "promotion_coverage_set_sha256": decision.promotion_coverage_set_sha256,
        "promotion_joint_replay_sha256": decision.promotion_joint_replay_sha256,
        "promotion_as_of_assessment_sha256": decision.promotion_as_of_assessment_sha256,
        "promotion_as_of_status": "CURRENT",
        "promotion_at": decision.promotion_at,
        "promotion_status_valid_until": decision.promotion_status_valid_until,
        "promotion_evidence_valid_until": "2026-01-01T12:00:00Z",
        "origin_claim": "CALLER_ASSERTED_PROVIDER_GENERATED_REFERENCE_MEDIA",
        "origin_assurance": (
            "QUALIFIED_RIGHTS_REVIEWED_AND_CURRENT_ONLY_AT_EXACT_PROMOTION_AT_NOT_PROVIDER_AUTHENTICATED"
        ),
        "sidecar_state": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_RECORDED",
        "promotion_performed": True,
        "eligible_for_separate_role_binding_review": True,
        "primary_asset_binding_replaced": False,
        "bible_active_binding_changed": False,
        "asset_version_v1_created": False,
        "composite_media_unsplit": True,
        "role_assignment_embedded": False,
        "provider_input_eligible": False,
        "present_currentness_asserted": False,
        "perpetual_eligibility_asserted": False,
        "supersedes_sidecar": False,
        "status": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_RECORDED",
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
        **_ZERO_AUTHORITY,
    }
    sidecar_sha = _semantic(
        GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_SHA256_DOMAIN,
        {name: _explicit(value) for name, value in sidecar_values.items()},
    )
    sidecar = CreativeSampleGeneratedReferenceEligibleAssetSidecarV1.model_validate(
        {
            "sidecar_id": f"generated_reference_eligible_asset_sidecar_v1_{sidecar_sha[:20]}",
            "sidecar_sha256": sidecar_sha,
            **sidecar_values,
        }
    )
    return request, decision, sidecar


def test_frozen_policy_projection_and_six_domains() -> None:
    projection = generated_reference_asset_promotion_policy_projection()
    encoded = _compact(projection)
    assert len(encoded) == 5_394
    assert hashlib.sha256(encoded).hexdigest() == (
        GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256
    )
    assert projection["gate_order"] == list(PROMOTION_GATE_ORDER)
    assert len(
        {
            GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
            GENERATED_REFERENCE_PRIMARY_ASSET_VERSION_PROJECTION_SHA256_DOMAIN,
            GENERATED_REFERENCE_PRIMARY_ASSET_BINDING_SHA256_DOMAIN,
            GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST_SHA256_DOMAIN,
            GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_SHA256_DOMAIN,
            GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_SHA256_DOMAIN,
        }
    ) == 6
    probe = {"probe": "identical-projection", "ordinal": 0}
    domains = (
        GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
        GENERATED_REFERENCE_PRIMARY_ASSET_VERSION_PROJECTION_SHA256_DOMAIN,
        GENERATED_REFERENCE_PRIMARY_ASSET_BINDING_SHA256_DOMAIN,
        GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST_SHA256_DOMAIN,
        GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_SHA256_DOMAIN,
        GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_SHA256_DOMAIN,
    )
    assert len({_semantic(domain, probe) for domain in domains}) == 6


def test_frozen_error_priority_explicit_identity_code_and_reverse_import_isolation() -> None:
    expected_priority = (
        "EXACT_INPUT_TYPE_REQUIRED",
        "DOCUMENT_RESOURCE_LIMIT_EXCEEDED",
        "CANONICAL_JSON_REQUIRED",
        "CONTRACT_FIELD_INVALID",
        "POLICY_IDENTITY_MISMATCH",
        "SEMANTIC_ID_OR_DIGEST_MISMATCH",
        "UPSTREAM_CLOSURE_MISMATCH",
        "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
        "TIME_WINDOW_INVALID_OR_EXPIRED",
        "ROLE_SEPARATION_VIOLATION",
        "STATUS_REPLAY_FAILED",
        "PROMOTION_GATE_NOT_PASS",
        "AUTHORITY_SURFACE_NONZERO",
        "PROHIBITED_BOUNDARY_CONNECTION",
    )
    assert get_args(GeneratedReferenceAssetPromotionErrorCodeV1) == expected_priority
    assert promotion_module._GENERATED_REFERENCE_ASSET_PROMOTION_ERROR_PRIORITY == (
        expected_priority
    )
    # Each frozen umbrella is a stable live exception value.  Public-path tests below exercise the
    # individual branches; this loop prevents any declared code from becoming unraisable or aliased.
    for code in expected_priority:
        with pytest.raises(GeneratedReferenceAssetPromotionError) as reachable:
            promotion_module._fail(
                cast(GeneratedReferenceAssetPromotionErrorCodeV1, code),
                "synthetic reachability probe",
            )
        assert reachable.value.code == code

    for projection_builder in (
        promotion_module._request_projection_from_values,
        promotion_module._decision_projection_from_values,
        promotion_module._sidecar_projection_from_values,
    ):
        source = inspect.getsource(projection_builder)
        assert "model_fields" not in source
        assert "model_dump" not in source
        assert "for name" not in source

    module_path = ROOT / "src/sdc/generated_reference_asset_promotion.py"
    syntax = ast.parse(module_path.read_text(encoding="utf-8"))
    prohibited_imports = {
        "os",
        "pathlib",
        "subprocess",
        "requests",
        "httpx",
        "sdc.compiler",
        "sdc.persistence",
        "sdc.provider",
        "sdc.runtime",
        "sdc.worker",
    }
    imported = {
        alias.name
        for node in ast.walk(syntax)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(syntax)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert prohibited_imports.isdisjoint(imported)
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"now", "utcnow", "today"}
        for node in ast.walk(syntax)
    )

    reverse_import_files = (
        "contracts.py",
        "compiler.py",
        "runtime.py",
        "provider.py",
        "creative_providers.py",
        "persistence.py",
        "qc.py",
        "semantic_qc.py",
        "worker.py",
        "visual_reference_prompt_compiler.py",
        "generated_reference_candidate.py",
        "generated_reference_rights_current_status.py",
    )
    for filename in reverse_import_files:
        text = (ROOT / "src/sdc" / filename).read_text(encoding="utf-8")
        assert "generated_reference_asset_promotion" not in text


@pytest.mark.parametrize("contract_name", ("request", "decision", "sidecar"))
def test_every_formal_field_mutation_is_rejected(contract_name: str) -> None:
    request, decision, sidecar = _known_answer_contracts()
    values: dict[str, BaseModel] = {
        "request": request,
        "decision": decision,
        "sidecar": sidecar,
    }
    projections: dict[str, Callable[[Any], dict[str, object]]] = {
        "request": creative_sample_generated_reference_asset_promotion_request_projection,
        "decision": creative_sample_generated_reference_asset_promotion_decision_projection,
        "sidecar": creative_sample_generated_reference_eligible_asset_sidecar_projection,
    }
    self_fields = {
        "request": {"request_id", "request_sha256"},
        "decision": {"decision_id", "decision_sha256"},
        "sidecar": {"sidecar_id", "sidecar_sha256"},
    }
    value = values[contract_name]
    projection = projections[contract_name](value)
    assert set(type(value).model_fields) == set(projection) | self_fields[contract_name]
    assert type(type(value).model_validate_json(
        generated_reference_asset_promotion_contract_document_bytes(value)
    )) is type(value)
    for field_name in type(value).model_fields:
        forged = value.model_copy(
            update={
                field_name: _mutated_formal_field(field_name, getattr(value, field_name))
            }
        )
        with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
            projections[contract_name](forged)
        assert error.value.code in {
            "CANONICAL_JSON_REQUIRED",
            "CONTRACT_FIELD_INVALID",
            "POLICY_IDENTITY_MISMATCH",
            "SEMANTIC_ID_OR_DIGEST_MISMATCH",
        }


@pytest.mark.parametrize(
    "field_name",
    (
        "binding_profile",
        "primary_asset_binding_sha256",
        "asset_purpose",
        "subject_id",
        "asset_version_id",
        "legacy_asset_version_projection_sha256",
        "version",
        "content_sha256",
        "media_type",
        "approval_ref",
        "provenance",
        "bible_active_asset_version_id",
    ),
)
def test_every_primary_binding_field_participates_in_request_identity(
    field_name: str,
) -> None:
    request, _decision, _sidecar = _known_answer_contracts()
    binding = request.requested_primary_asset_binding
    assert set(type(binding).model_fields) == {
        "binding_profile",
        "primary_asset_binding_sha256",
        "asset_purpose",
        "subject_id",
        "asset_version_id",
        "legacy_asset_version_projection_sha256",
        "version",
        "content_sha256",
        "media_type",
        "approval_ref",
        "provenance",
        "bible_active_asset_version_id",
    }
    mutated_binding = binding.model_copy(
        update={
            field_name: _mutated_formal_field(
                field_name, getattr(binding, field_name)
            )
        }
    )
    forged_request = request.model_copy(
        update={"requested_primary_asset_binding": mutated_binding}
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            forged_request
        )
    assert error.value.code in {
        "CONTRACT_FIELD_INVALID",
        "SEMANTIC_ID_OR_DIGEST_MISMATCH",
    }


@pytest.mark.parametrize("field_name", ("ordinal", "gate", "result", "basis"))
def test_every_gate_result_field_participates_in_decision_identity(
    field_name: str,
) -> None:
    _request, decision, _sidecar = _known_answer_contracts()
    gate = decision.gate_results[7]
    assert set(type(gate).model_fields) == {"ordinal", "gate", "result", "basis"}
    mutated_gate = gate.model_copy(
        update={field_name: _mutated_formal_field(field_name, getattr(gate, field_name))}
    )
    gates = (*decision.gate_results[:7], mutated_gate, *decision.gate_results[8:])
    forged_decision = decision.model_copy(update={"gate_results": gates})
    with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
        creative_sample_generated_reference_asset_promotion_decision_projection(
            forged_decision
        )
    assert error.value.code in {
        "CONTRACT_FIELD_INVALID",
        "SEMANTIC_ID_OR_DIGEST_MISMATCH",
    }


def test_primary_binding_closes_full_character_and_scene_asset_versions() -> None:
    with pytest.raises(GeneratedReferenceAssetPromotionError) as exact_type_error:
        build_generated_reference_promotion_primary_asset_binding(
            cast(Any, object()), cast(Any, object())
        )
    assert exact_type_error.value.code == "EXACT_INPUT_TYPE_REQUIRED"

    for bible, asset, binding in (_character_binding(), _scene_binding()):
        projection = generated_reference_primary_asset_version_projection(asset)
        expected_legacy_sha = hashlib.sha256(
            GENERATED_REFERENCE_PRIMARY_ASSET_VERSION_PROJECTION_SHA256_DOMAIN
            + _compact(projection)
        ).hexdigest()
        assert binding.legacy_asset_version_projection_sha256 == expected_legacy_sha
        assert binding.asset_version_id == bible.active_asset_version_id
        assert generated_reference_promotion_primary_asset_binding_sha256(binding) == (
            binding.primary_asset_binding_sha256
        )
        assert "primary_asset_binding_sha256" not in (
            generated_reference_promotion_primary_asset_binding_projection(binding)
        )
        assert generated_reference_primary_asset_version_projection_sha256(asset) == (
            expected_legacy_sha
        )

    character_bible, character_asset, character_binding = _character_binding()
    scene_bible, scene_asset, _scene_primary_binding = _scene_binding()
    for valid_bible in (character_bible, scene_bible):
        for invalid_asset in (object(), {}):
            with pytest.raises(
                GeneratedReferenceAssetPromotionError
            ) as exact_asset_error:
                build_generated_reference_promotion_primary_asset_binding(
                    valid_bible, cast(Any, invalid_asset)
                )
            assert exact_asset_error.value.code == "EXACT_INPUT_TYPE_REQUIRED"

    binding_projection = generated_reference_promotion_primary_asset_binding_projection(
        character_binding
    )
    assert set(binding_projection) == {
        "binding_profile",
        "asset_purpose",
        "subject_id",
        "asset_version_id",
        "legacy_asset_version_projection_sha256",
        "version",
        "content_sha256",
        "media_type",
        "approval_ref",
        "provenance",
        "bible_active_asset_version_id",
    }
    for bible, asset in (
        (character_bible, scene_asset),
        (scene_bible, character_asset),
        (
            character_bible.model_copy(update={"active_asset_version_id": "missing-version"}),
            character_asset,
        ),
        (
            character_bible,
            character_asset.model_copy(update={"character_id": "cross-subject"}),
        ),
        (
            scene_bible,
            scene_asset.model_copy(update={"scene_id": "cross-subject"}),
        ),
    ):
        with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
            build_generated_reference_promotion_primary_asset_binding(
                cast(Any, bible), cast(Any, asset)
            )
        assert error.value.code == "PRIMARY_ASSET_BINDING_CLOSURE_INVALID"

    forged = character_binding.model_copy(
        update={"primary_asset_binding_sha256": "00" * 32}
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as binding_error:
        generated_reference_promotion_primary_asset_binding_projection(forged)
    assert binding_error.value.code == "CONTRACT_FIELD_INVALID"


def test_formal_known_answers_round_trip_and_exclude_only_self_identity() -> None:
    request, decision, sidecar = _known_answer_contracts()
    request_projection = creative_sample_generated_reference_asset_promotion_request_projection(
        request
    )
    assert {"request_id", "request_sha256"}.isdisjoint(request_projection)
    assert (
        creative_sample_generated_reference_asset_promotion_request_sha256(request)
        == request.request_sha256
    )
    request_raw = generated_reference_asset_promotion_contract_document_bytes(request)
    assert CreativeSampleGeneratedReferenceAssetPromotionRequestV1.model_validate_json(
        request_raw
    ) == request

    decision_projection = creative_sample_generated_reference_asset_promotion_decision_projection(
        decision
    )
    assert {"decision_id", "decision_sha256"}.isdisjoint(decision_projection)
    assert (
        creative_sample_generated_reference_asset_promotion_decision_sha256(decision)
        == decision.decision_sha256
    )
    decision_raw = generated_reference_asset_promotion_contract_document_bytes(decision)
    assert CreativeSampleGeneratedReferenceAssetPromotionDecisionV1.model_validate_json(
        decision_raw
    ) == decision

    sidecar_projection = creative_sample_generated_reference_eligible_asset_sidecar_projection(
        sidecar
    )
    assert {"sidecar_id", "sidecar_sha256"}.isdisjoint(sidecar_projection)
    assert (
        creative_sample_generated_reference_eligible_asset_sidecar_sha256(sidecar)
        == sidecar.sidecar_sha256
    )
    sidecar_raw = generated_reference_asset_promotion_contract_document_bytes(sidecar)
    assert CreativeSampleGeneratedReferenceEligibleAssetSidecarV1.model_validate_json(
        sidecar_raw
    ) == sidecar
    for raw in (request_raw, decision_raw, sidecar_raw):
        assert raw.endswith(b"\n") and b"\r" not in raw

    assert generated_reference_asset_promotion_review_payload_sha256(request) == (
        request.promotion_review_payload_sha256
    )
    assert generated_reference_asset_promotion_review_payload_projection(request) == (
        _review_payload(cast(dict[str, object], _explicit(request)))
    )


def test_formal_field_inventory_and_zero_authority_tamper_rejection() -> None:
    request, decision, sidecar = _known_answer_contracts()
    assert len(CreativeSampleGeneratedReferenceAssetPromotionRequestV1.model_fields) == 81
    assert len(CreativeSampleGeneratedReferenceAssetPromotionDecisionV1.model_fields) == 77
    assert len(CreativeSampleGeneratedReferenceEligibleAssetSidecarV1.model_fields) == 83
    assert len(GeneratedReferencePromotionPrimaryAssetBindingV1.model_fields) == 12
    assert len(GeneratedReferencePromotionGateResultV1.model_fields) == 4

    forged = request.model_copy(update={"provider_requests": 1})
    with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
        creative_sample_generated_reference_asset_promotion_request_projection(forged)
    assert error.value.code == "SEMANTIC_ID_OR_DIGEST_MISMATCH"

    rehashed_authority = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(request, {"provider_requests": 1}),
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            rehashed_authority
        )
    assert error.value.code == "AUTHORITY_SURFACE_NONZERO"

    policy_tamper = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(
            request,
            {"policy_id": "sdc.generated-reference-asset-promotion-policy-tampered"},
            refresh_review_payload=True,
        ),
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
        creative_sample_generated_reference_asset_promotion_request_projection(policy_tamper)
    assert error.value.code == "POLICY_IDENTITY_MISMATCH"

    self_tamper = request.model_copy(update={"request_sha256": "00" * 32})
    with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
        creative_sample_generated_reference_asset_promotion_request_projection(self_tamper)
    assert error.value.code == "SEMANTIC_ID_OR_DIGEST_MISMATCH"

    with pytest.raises(ValidationError):
        CreativeSampleGeneratedReferenceAssetPromotionDecisionV1.model_validate(
            {
                **cast(dict[str, object], _explicit(decision)),
                "sidecar_materialization_allowed": False,
            }
        )
    with pytest.raises(ValidationError):
        CreativeSampleGeneratedReferenceEligibleAssetSidecarV1.model_validate(
            {
                **cast(dict[str, object], _explicit(sidecar)),
                "present_currentness_asserted": True,
            }
        )
    for bad_basis in ("line one\nline two", "visible\u202ereordered"):
        with pytest.raises(ValidationError):
            GeneratedReferencePromotionGateResultV1.model_validate(
                {
                    "ordinal": 7,
                    "gate": "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED",
                    "result": "PASS",
                    "basis": bad_basis,
                }
            )
        with pytest.raises(ValidationError):
            CreativeSampleGeneratedReferenceAssetPromotionRequestV1.model_validate(
                {
                    **cast(dict[str, object], _explicit(request)),
                    "request_basis": bad_basis,
                }
            )


def test_formal_multi_faults_follow_frozen_error_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _decision, _sidecar = _known_answer_contracts()

    structural_policy_semantic_authority = request.model_copy(
        update={
            "media_size_bytes": 0,
            "policy_id": "tampered-policy",
            "request_sha256": "00" * 32,
            "provider_requests": 1,
        }
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as structural_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            structural_policy_semantic_authority
        )
    assert structural_error.value.code == "CONTRACT_FIELD_INVALID"

    policy_semantic_authority = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(
            request,
            {
                "policy_id": "sdc.generated-reference-asset-promotion-policy-tampered",
                "provider_requests": 1,
            },
            refresh_review_payload=True,
        ),
    ).model_copy(update={"request_sha256": "00" * 32})
    with pytest.raises(GeneratedReferenceAssetPromotionError) as policy_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            policy_semantic_authority
        )
    assert policy_error.value.code == "POLICY_IDENTITY_MISMATCH"

    semantic_authority = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(request, {"provider_requests": 1}),
    ).model_copy(update={"request_sha256": "00" * 32})
    with pytest.raises(GeneratedReferenceAssetPromotionError) as semantic_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            semantic_authority
        )
    assert semantic_error.value.code == "SEMANTIC_ID_OR_DIGEST_MISMATCH"

    authority_only = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(request, {"provider_requests": 1}),
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as authority_error:
        creative_sample_generated_reference_asset_promotion_request_projection(authority_only)
    assert authority_error.value.code == "AUTHORITY_SURFACE_NONZERO"

    with pytest.raises(GeneratedReferenceAssetPromotionError) as exact_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            cast(Any, cast(dict[str, object], _explicit(request)))
        )
    assert exact_error.value.code == "EXACT_INPUT_TYPE_REQUIRED"

    oversized_noncanonical = request.model_copy(
        update={"request_basis": "x" * 262_145 + "e\u0301"}
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as resource_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            oversized_noncanonical
        )
    assert resource_error.value.code == "DOCUMENT_RESOURCE_LIMIT_EXCEEDED"

    noncanonical = request.model_copy(update={"request_basis": "decomposed-e\u0301"})
    with pytest.raises(GeneratedReferenceAssetPromotionError) as canonical_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            noncanonical
        )
    assert canonical_error.value.code == "CANONICAL_JSON_REQUIRED"

    surrogate = request.model_copy(update={"request_basis": "invalid-\ud800"})
    with pytest.raises(GeneratedReferenceAssetPromotionError) as surrogate_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            surrogate
        )
    assert surrogate_error.value.code == "CANONICAL_JSON_REQUIRED"

    oversized_surrogate = request.model_copy(
        update={"request_basis": "x" * 262_145 + "\ud800"}
    )
    with pytest.raises(
        GeneratedReferenceAssetPromotionError
    ) as oversized_surrogate_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            oversized_surrogate
        )
    assert oversized_surrogate_error.value.code == (
        "DOCUMENT_RESOURCE_LIMIT_EXCEEDED"
    )

    with monkeypatch.context() as patch:
        patch.setitem(promotion_module._PROMOTION_POLICY, "policy_id", "tampered-policy")
        with pytest.raises(GeneratedReferenceAssetPromotionError) as runtime_policy_error:
            generated_reference_asset_promotion_policy_projection()
        assert runtime_policy_error.value.code == "POLICY_IDENTITY_MISMATCH"


@pytest.mark.parametrize(
    "boundary_field",
    (
        "request_valid_until",
        "qualification_valid_until",
        "manifest_valid_until",
        "requested_status_valid_until",
    ),
)
def test_request_half_open_upper_bounds_are_independently_rejected(
    boundary_field: str,
) -> None:
    request, _decision, _sidecar = _known_answer_contracts()
    boundary = request.requested_at
    later = "2026-01-01T12:00:00Z"
    updates: dict[str, object] = {
        "qualification_valid_until": later,
        "manifest_valid_until": later,
        "requested_status_valid_until": later,
        "request_valid_until": boundary,
    }
    if boundary_field != "request_valid_until":
        updates[boundary_field] = boundary
    forged = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(request, updates, refresh_review_payload=True),
    )
    assert forged.request_valid_until == boundary
    if boundary_field != "request_valid_until":
        assert getattr(forged, boundary_field) == boundary
        assert all(
            getattr(forged, other) > boundary
            for other in (
                "qualification_valid_until",
                "manifest_valid_until",
                "requested_status_valid_until",
            )
            if other != boundary_field
        )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
        creative_sample_generated_reference_asset_promotion_request_projection(forged)
    assert error.value.code == "CONTRACT_FIELD_INVALID"


@pytest.mark.parametrize(
    "boundary_field",
    (
        "qualification_valid_until",
        "manifest_valid_until",
        "promotion_status_valid_until",
    ),
)
def test_final_evidence_half_open_upper_bounds_are_independently_rejected(
    boundary_field: str,
) -> None:
    _request, _decision, sidecar = _known_answer_contracts()
    boundary = sidecar.promotion_at
    later = "2026-01-01T12:00:00Z"
    updates: dict[str, object] = {
        "qualification_valid_until": later,
        "manifest_valid_until": later,
        "promotion_status_valid_until": later,
        "promotion_evidence_valid_until": boundary,
    }
    updates[boundary_field] = boundary
    forged = cast(
        CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
        _rehash_formal(sidecar, updates),
    )
    assert getattr(forged, boundary_field) == forged.promotion_at
    assert all(
        getattr(forged, other) > boundary
        for other in (
            "qualification_valid_until",
            "manifest_valid_until",
            "promotion_status_valid_until",
        )
        if other != boundary_field
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
        creative_sample_generated_reference_eligible_asset_sidecar_projection(forged)
    assert error.value.code == "CONTRACT_FIELD_INVALID"


def test_rights_scope_reorder_is_rejected_without_expansion_or_narrowing() -> None:
    request, _decision, _sidecar = _known_answer_contracts()
    scope_values = request.reviewed_rights_scope.model_dump(mode="python")
    ordered_codes = (
        "AA_SYNTHETIC_OFFLINE_USE",
        "BB_SYNTHETIC_REVIEW_USE",
    )
    scope_values["allowed_use_scope"] = ordered_codes
    ordered_scope = GeneratedReferenceReviewedRightsScopeV1.model_validate(scope_values)
    ordered_request = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(
            request,
            {"reviewed_rights_scope": ordered_scope},
            refresh_review_payload=True,
        ),
    )
    creative_sample_generated_reference_asset_promotion_request_projection(
        ordered_request
    )

    reordered_codes = tuple(reversed(ordered_codes))
    assert set(reordered_codes) == set(ordered_codes)
    assert len(reordered_codes) == len(ordered_codes)
    reordered_scope = ordered_scope.model_copy(
        update={"allowed_use_scope": reordered_codes}
    )
    reordered_request = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(
            ordered_request,
            {"reviewed_rights_scope": reordered_scope},
            refresh_review_payload=True,
        ),
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            reordered_request
        )
    assert error.value.code == "CONTRACT_FIELD_INVALID"


def test_prohibited_portable_url_reaches_frozen_boundary_code() -> None:
    request, _decision, _sidecar = _known_answer_contracts()
    prohibited = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(
            request,
            {"request_basis": "See https://example.invalid/private-response."},
            refresh_review_payload=True,
        ),
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as error:
        creative_sample_generated_reference_asset_promotion_request_projection(prohibited)
    assert error.value.code == "PROHIBITED_BOUNDARY_CONNECTION"


def test_boundary_scanner_allows_negated_basis_but_rejects_portable_material() -> None:
    request, decision, sidecar = _known_answer_contracts()
    negated_sentence = (
        "The first-party fictional geometric scene contains no real person, likeness, "
        "identity claim, biometric data, contact detail, credential, or other sensitive data."
    )

    def with_sensitive_basis(value: BaseModel, basis: str) -> BaseModel:
        scope = cast(Any, value).reviewed_rights_scope
        updated_scope = scope.model_copy(
            update={"likeness_privacy_and_sensitive_data_basis": basis}
        )
        return _rehash_formal(
            value,
            {"reviewed_rights_scope": updated_scope},
            refresh_review_payload=(
                type(value) is CreativeSampleGeneratedReferenceAssetPromotionRequestV1
            ),
        )

    public_contracts: tuple[
        tuple[BaseModel, Callable[[Any], dict[str, object]]], ...
    ] = (
        (
            request,
            creative_sample_generated_reference_asset_promotion_request_projection,
        ),
        (
            decision,
            creative_sample_generated_reference_asset_promotion_decision_projection,
        ),
        (
            sidecar,
            creative_sample_generated_reference_eligible_asset_sidecar_projection,
        ),
    )
    for contract, projection_builder in public_contracts:
        accepted = with_sensitive_basis(contract, negated_sentence)
        assert projection_builder(accepted)["reviewed_rights_scope"]

    actual_material = (
        "http://example.invalid/material",
        "https://example.invalid/material",
        "file:///tmp/private/material.json",
        "s3://synthetic-bucket/private/material.json",
        "ftp://example.invalid/private/material.json",
        r"C:\Users\Alice\private\material.json",
        r"\\server\share\private\material.json",
        "/etc/private/material.json",
        "/synthetic-secret.json",
        "./private/material.json",
        "../private/material.json",
        "credential: synthetic-secret",
        "api key = synthetic-secret",
        "token: synthetic-token",
        "Bearer synthetic-token",
        "provider task id: task-123",
        "account id = account-123",
        "response body: opaque-payload",
        "raw legal document = embedded-payload",
        "private key: synthetic-private-key",
        "-----BEGIN PRIVATE KEY----- synthetic-material",
        "sk-syntheticsecret123",
    )
    for injected_basis in actual_material:
        for contract, projection_builder in public_contracts:
            injected = with_sensitive_basis(contract, injected_basis)
            with pytest.raises(
                GeneratedReferenceAssetPromotionError
            ) as material_error:
                projection_builder(injected)
            assert material_error.value.code == "PROHIBITED_BOUNDARY_CONNECTION"

    non_basis_sensitive_noun = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(
            request,
            {"candidate_id": "credential"},
            refresh_review_payload=True,
        ),
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as noun_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            non_basis_sensitive_noun
        )
    assert noun_error.value.code == "PROHIBITED_BOUNDARY_CONNECTION"

    for prohibited_key in ("api_key", "local_path", "provider_endpoint"):
        with pytest.raises(GeneratedReferenceAssetPromotionError) as mapping_key_error:
            promotion_module._verify_no_prohibited_boundary_connection(
                {prohibited_key: "synthetic-material"}, field="synthetic mapping"
            )
        assert mapping_key_error.value.code == "PROHIBITED_BOUNDARY_CONNECTION"

    for root_path in (
        "C:\\",
        "C:/",
        r"\\server",
        "/",
        "./",
        "../",
        ".\\",
        "..\\",
    ):
        with pytest.raises(GeneratedReferenceAssetPromotionError) as root_path_error:
            promotion_module._verify_no_prohibited_boundary_connection(
                root_path, field="synthetic root path"
            )
        assert root_path_error.value.code == "PROHIBITED_BOUNDARY_CONNECTION"
    promotion_module._verify_no_prohibited_boundary_connection(
        "A / B", field="synthetic prose"
    )

    scope_with_extra = cast(
        dict[str, object], _explicit(request.reviewed_rights_scope)
    )
    scope_with_extra["api_key"] = "synthetic-secret"
    extra_key_request = request.model_copy(
        update={"reviewed_rights_scope": scope_with_extra}
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as extra_key_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            extra_key_request
        )
    assert extra_key_error.value.code == "CONTRACT_FIELD_INVALID"

    authority_and_url = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(
            request,
            {
                "provider_requests": 1,
                "request_basis": "https://example.invalid/material",
            },
            refresh_review_payload=True,
        ),
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as authority_error:
        creative_sample_generated_reference_asset_promotion_request_projection(
            authority_and_url
        )
    assert authority_error.value.code == "AUTHORITY_SURFACE_NONZERO"


def test_complete_adr044_replay_prepares_and_atomically_finalizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    materials = status_fixtures._manifest_materials()
    status = status_fixtures._current_closure()
    manifest_kwargs = status_fixtures._manifest_builder_kwargs(materials)
    upstream = GeneratedReferenceAssetPromotionUpstreamClosureInput(
        artifact=materials.upstream.artifact,
        outcome=materials.upstream.outcome,
        candidate=materials.upstream.candidate,
        qualification_request=materials.upstream.qualification_request,
        qualification_decision=materials.upstream.qualification_decision,
        png_bytes=materials.upstream.png_bytes,
        qualification_evidence_documents=materials.upstream.evidence_inputs,
        qualification_preparer_identity_bytes=materials.upstream.preparer_identity_bytes,
        qualification_preparer_action_bytes=materials.upstream.preparer_action_bytes,
        qualifier_identity_bytes=materials.upstream.qualifier_identity_bytes,
        qualifier_action_bytes=materials.upstream.qualifier_action_bytes,
        manifest=materials.manifest,
        manifest_review_evidence_documents=cast(
            tuple[GeneratedReferenceRightsManifestEvidenceInput, ...],
            manifest_kwargs["review_evidence_documents"],
        ),
        manifest_proposed_rights_scope=cast(
            GeneratedReferenceRightsScopeProposalV1,
            manifest_kwargs["proposed_rights_scope"],
        ),
        manifest_maker_identity_bytes=materials.manifest_closure.maker_identity_bytes,
        manifest_maker_action_bytes=materials.manifest_closure.maker_action_bytes,
        manifest_checker_identity_bytes=materials.manifest_closure.checker_identity_bytes,
        manifest_checker_action_bytes=materials.manifest_closure.checker_action_bytes,
        manifest_at=materials.manifest.manifest_at,
    )

    def status_input_at(
        source_status: Any, as_of: str
    ) -> GeneratedReferenceAssetPromotionStatusClosureInput:
        receipt = process_generated_reference_current_status_record_as_of_assessment(
            source_status.record,
            source_status.manifest,
            source_status.chain_inputs,
            as_of=as_of,
        ).receipt
        return GeneratedReferenceAssetPromotionStatusClosureInput(
            subject_closure=source_status.subject_closure,
            request=source_status.request,
            instruction=source_status.instruction,
            decision=source_status.decision,
            record=source_status.record,
            chain_inputs=source_status.chain_inputs,
            receipt=receipt,
            status_preparer_identity_bytes=source_status.status_preparer_identity_bytes,
            status_preparer_action_bytes=source_status.status_preparer_action_bytes,
            status_checker_identity_bytes=source_status.status_checker_identity_bytes,
            status_checker_action_bytes=source_status.status_checker_action_bytes,
        )

    def status_at(as_of: str) -> GeneratedReferenceAssetPromotionStatusClosureInput:
        return status_input_at(status, as_of)

    def rebuild_status_from_targets(
        target_inputs: tuple[Any, ...],
        chain_members_by_category: dict[str, tuple[Any, ...]],
        *,
        as_of: str,
        checker_identity_value: bytes | None = None,
    ) -> GeneratedReferenceAssetPromotionStatusClosureInput:
        expected_refs = status_fixtures._canonical_request_refs(target_inputs)
        preparer_identity = status.status_preparer_identity_bytes
        checker_identity_bytes = (
            status.status_checker_identity_bytes
            if checker_identity_value is None
            else checker_identity_value
        )
        requested_at_value = status.request.requested_at
        request_basis_value = status.request.request_basis
        preparer_action = _document(
            {
                "document_profile": (
                    "sdc.generated-reference-current-status-request-preparation-action.v1"
                ),
                "action": "PREPARED_GENERATED_REFERENCE_CURRENT_STATUS_REQUEST",
                "actor_identity_ref_sha256": hashlib.sha256(
                    preparer_identity
                ).hexdigest(),
                "subject_closure_sha256": status.subject_closure.closure_sha256,
                "policy_document_sha256": (
                    rights_module.GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256
                ),
                "requested_at": requested_at_value,
                "request_valid_until": status.request.request_valid_until,
                "observation_target_refs": [_explicit(item) for item in expected_refs],
                "request_basis": request_basis_value,
            }
        )
        rebuilt_request = rights_module.build_generated_reference_current_status_request(
            subject_closure=status.subject_closure,
            status_preparer_identity_bytes=preparer_identity,
            status_preparer_action_bytes=preparer_action,
            requested_at=requested_at_value,
            target_observations=target_inputs,
            request_basis=request_basis_value,
        )
        assert rebuilt_request.observation_refs == expected_refs
        ref_by_id = {
            item.observation_id: item for item in rebuilt_request.observation_refs
        }
        chain_inputs = tuple(
            sorted(
                (
                    rights_module.GeneratedReferenceCurrentStatusExplicitChainInput(
                        target_observation_refs=tuple(
                            ref_by_id[item.observation.observation_id]
                            for item in target_inputs
                            if item.observation.category == category
                        ),
                        observation_inputs=members,
                    )
                    for category, members in chain_members_by_category.items()
                ),
                key=lambda item: (
                    item.observation_inputs[0].observation.chain_link.chain_scope_sha256,
                    item.observation_inputs[0].observation.observation_id,
                ),
            )
        )
        category_results = status_fixtures._manual_category_results(
            request=rebuilt_request,
            chain_inputs=chain_inputs,
            evaluated_at=status.instruction.evaluated_at,
            unresolved_fork_category=None,
        )
        recorded_status = status_fixtures._manual_recorded_status(category_results)
        checker_basis = status.instruction.checker_basis
        checker_action = _document(
            {
                "document_profile": (
                    "sdc.generated-reference-current-status-decision-checker-action.v1"
                ),
                "action": "RECORDED_GENERATED_REFERENCE_CURRENT_STATUS_DECISION",
                "actor_identity_ref_sha256": hashlib.sha256(
                    checker_identity_bytes
                ).hexdigest(),
                "request_sha256": rebuilt_request.request_sha256,
                "evaluated_at": status.instruction.evaluated_at,
                "category_results": [_explicit(item) for item in category_results],
                "checker_basis": checker_basis,
                "status_valid_until": min(
                    item.result_valid_until for item in category_results
                ),
                "recorded_status": recorded_status,
            }
        )
        instruction = rights_module.build_generated_reference_current_status_instruction(
            request=rebuilt_request,
            chain_inputs=chain_inputs,
            status_preparer_identity_bytes=preparer_identity,
            status_preparer_action_bytes=preparer_action,
            status_checker_identity_bytes=checker_identity_bytes,
            status_checker_action_bytes=checker_action,
            evaluated_at=status.instruction.evaluated_at,
            checker_basis=checker_basis,
        )
        decision = rights_module.build_generated_reference_current_status_decision(
            request=rebuilt_request,
            instruction=instruction,
            chain_inputs=chain_inputs,
            status_preparer_identity_bytes=preparer_identity,
            status_preparer_action_bytes=preparer_action,
            status_checker_identity_bytes=checker_identity_bytes,
            status_checker_action_bytes=checker_action,
        )
        record = rights_module.build_generated_reference_current_status_evidence_record(
            request=rebuilt_request,
            instruction=instruction,
            decision=decision,
            chain_inputs=chain_inputs,
            status_preparer_identity_bytes=preparer_identity,
            status_preparer_action_bytes=preparer_action,
            status_checker_identity_bytes=checker_identity_bytes,
            status_checker_action_bytes=checker_action,
        )
        receipt = process_generated_reference_current_status_record_as_of_assessment(
            record,
            status.manifest,
            chain_inputs,
            as_of=as_of,
        ).receipt
        return GeneratedReferenceAssetPromotionStatusClosureInput(
            subject_closure=status.subject_closure,
            request=rebuilt_request,
            instruction=instruction,
            decision=decision,
            record=record,
            chain_inputs=chain_inputs,
            receipt=receipt,
            status_preparer_identity_bytes=preparer_identity,
            status_preparer_action_bytes=preparer_action,
            status_checker_identity_bytes=checker_identity_bytes,
            status_checker_action_bytes=checker_action,
        )

    requested_at = "2026-08-29T05:00:00Z"
    promotion_at = "2026-08-29T05:30:00Z"
    request_status = status_at(requested_at)
    final_status = status_at(promotion_at)

    primary_source = json.loads(
        (
            ROOT
            / "tests/fixtures/visual_prompt_profiles/reference-compiler/"
            "reviewed-known-answer-source-v1.json"
        ).read_text(encoding="utf-8")
    )
    source_cases = cast(list[object], primary_source["cases"])
    primary_case = next(
        cast(dict[str, object], item)
        for item in source_cases
        if cast(dict[str, object], item)["case_id"] == "character-reference-basic"
    )
    bible = CharacterBible.model_validate(primary_case["subject"])
    assert len(bible.asset_versions) == 1
    asset = bible.asset_versions[0]
    binding = build_generated_reference_promotion_primary_asset_binding(bible, asset)
    request_basis = "Synthetic end-to-end Promotion request basis."
    request_valid_until = min(
        "2026-08-30T05:00:00Z",
        upstream.qualification_decision.qualification_valid_until,
        upstream.manifest.manifest_valid_until,
        request_status.receipt.status_valid_until,
    )
    review_source: dict[str, object] = {
        "policy_id": "sdc.generated-reference-asset-promotion-policy",
        "policy_version": "1.0.0",
        "policy_document_sha256": (
            GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256
        ),
        "request_scope": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_ONLY",
        "reference_prompt_artifact_sha256": upstream.artifact.artifact_sha256,
        "provider_attempt_outcome_id": upstream.outcome.outcome_id,
        "provider_attempt_outcome_sha256": upstream.outcome.outcome_sha256,
        "candidate_id": upstream.candidate.candidate_id,
        "candidate_sha256": upstream.candidate.candidate_sha256,
        "output_ordinal": 0,
        "media_type": "image/png",
        "media_content_sha256": upstream.candidate.media_content_sha256,
        "media_size_bytes": upstream.candidate.media_size_bytes,
        "media_technical_record_sha256": upstream.candidate.media_technical_record_sha256,
        "qualification_request_id": upstream.qualification_request.request_id,
        "qualification_request_sha256": upstream.qualification_request.request_sha256,
        "qualification_decision_id": upstream.qualification_decision.decision_id,
        "qualification_decision_sha256": upstream.qualification_decision.decision_sha256,
        "qualification_decision_at": upstream.qualification_decision.decision_at,
        "qualification_valid_until": (
            upstream.qualification_decision.qualification_valid_until
        ),
        "manifest_id": upstream.manifest.manifest_id,
        "manifest_sha256": upstream.manifest.manifest_sha256,
        "manifest_at": upstream.manifest.manifest_at,
        "manifest_valid_until": upstream.manifest.manifest_valid_until,
        "reviewed_rights_scope": upstream.manifest.reviewed_rights_scope,
        "status_subject_closure_id": request_status.subject_closure.closure_id,
        "status_subject_closure_sha256": request_status.subject_closure.closure_sha256,
        "requested_status_record_id": request_status.record.record_id,
        "requested_status_record_sha256": request_status.record.record_sha256,
        "requested_status_receipt_id": request_status.receipt.receipt_id,
        "requested_status_receipt_sha256": request_status.receipt.receipt_sha256,
        "requested_explicit_chain_set_sha256": (
            request_status.receipt.explicit_chain_set_sha256
        ),
        "requested_coverage_set_sha256": request_status.receipt.coverage_set_sha256,
        "requested_joint_replay_sha256": request_status.receipt.joint_replay_sha256,
        "requested_as_of_assessment_sha256": (
            request_status.receipt.as_of_assessment_sha256
        ),
        "requested_as_of": requested_at,
        "requested_as_of_status": "CURRENT",
        "requested_status_valid_until": request_status.receipt.status_valid_until,
        "requested_primary_asset_binding": binding,
        "requested_at": requested_at,
        "request_valid_until": request_valid_until,
        "request_basis": request_basis,
        "requested_representation": "TYPED_ELIGIBLE_ASSET_SIDECAR",
        "composite_media_unsplit": True,
        "role_assignment_embedded": False,
        "bible_mutation_requested": False,
        "provider_input_requested": False,
    }
    review_sha = _semantic(
        GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
        _review_payload(review_source),
    )
    maker_identity = _document(
        {
            "document_profile": "sdc.privacy-minimized-human-reference.v1",
            "identity_namespace": "synthetic-promotion",
            "identity_ref": "maker",
        }
    )
    checker_identity = _document(
        {
            "document_profile": "sdc.privacy-minimized-human-reference.v1",
            "identity_namespace": "synthetic-promotion",
            "identity_ref": "checker",
        }
    )
    maker_action = _document(
        {
            "document_profile": (
                "sdc.generated-reference-asset-promotion-request-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST",
            "actor_ref_sha256": hashlib.sha256(maker_identity).hexdigest(),
            "promotion_review_payload_sha256": review_sha,
            "candidate_sha256": upstream.candidate.candidate_sha256,
            "manifest_sha256": upstream.manifest.manifest_sha256,
            "requested_status_receipt_sha256": request_status.receipt.receipt_sha256,
            "requested_primary_asset_binding_sha256": (
                binding.primary_asset_binding_sha256
            ),
            "policy_document_sha256": (
                GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256
            ),
            "requested_at": requested_at,
        }
    )
    request = prepare_generated_reference_asset_promotion_request(
        upstream,
        request_status,
        bible,
        asset,
        maker_identity_bytes=maker_identity,
        maker_action_bytes=maker_action,
        requested_at=requested_at,
        request_basis=request_basis,
    )
    assert request.promotion_review_payload_sha256 == review_sha
    assert (
        verify_generated_reference_asset_promotion_request(
            request,
            upstream,
            request_status,
            bible,
            asset,
            maker_identity_bytes=maker_identity,
            maker_action_bytes=maker_action,
            requested_at=requested_at,
            request_basis=request_basis,
        )
        == request
    )

    association_basis = "Human independently approved the Sidecar association."
    deferral_basis = "Human acknowledged unsplit composite role deferral."

    def finalize_with_association(
        association_result: Literal["PASS", "FAIL", "INDETERMINATE"],
        *,
        deferral_result: Literal["PASS", "FAIL", "INDETERMINATE"] = "PASS",
        request_value: CreativeSampleGeneratedReferenceAssetPromotionRequestV1 = request,
        request_status_value: GeneratedReferenceAssetPromotionStatusClosureInput = request_status,
        final_status_value: GeneratedReferenceAssetPromotionStatusClosureInput = final_status,
        requested_bible_value: CharacterBible | SceneBible = bible,
        requested_asset_value: CharacterAssetVersion | SceneAssetVersion = asset,
        promotion_bible_value: CharacterBible | SceneBible = bible,
        promotion_asset_value: CharacterAssetVersion | SceneAssetVersion = asset,
        maker_identity_value: bytes = maker_identity,
        maker_action_value: bytes = maker_action,
        checker_identity_value: bytes = checker_identity,
        promotion_at_value: str = promotion_at,
    ) -> tuple[GeneratedReferenceAssetPromotionFinalizationResult, bytes, str]:
        promotion_binding = build_generated_reference_promotion_primary_asset_binding(
            promotion_bible_value, promotion_asset_value
        )
        status_result = {
            "CURRENT": "PASS",
            "EXPIRED": "FAIL",
            "REVOKED": "FAIL",
            "HELD": "FAIL",
            "INDETERMINATE": "INDETERMINATE",
        }[final_status_value.receipt.as_of_status]
        gate_results = tuple(
            GeneratedReferencePromotionGateResultV1.model_validate(
                {
                    "ordinal": index,
                    "gate": gate,
                    "result": (
                        association_result
                        if gate == "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED"
                        else status_result
                        if gate == "CURRENT_STATUS_AT_PROMOTION"
                        else (
                            "PASS"
                            if promotion_binding
                            == request_value.requested_primary_asset_binding
                            else "FAIL"
                        )
                        if gate == "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT"
                        else deferral_result
                        if gate
                        == "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED"
                        else "PASS"
                    ),
                    "basis": (
                        association_basis
                        if gate == "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED"
                        else deferral_basis
                        if gate == "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED"
                        else _COMPILER_BASES[index]
                    ),
                }
            )
            for index, gate in enumerate(PROMOTION_GATE_ORDER)
        )
        issue_codes = [
            code
            for index, code in (
                (4, "STATUS_NOT_CURRENT_AT_PROMOTION"),
                (5, "PRIMARY_BINDING_NO_LONGER_ACTIVE"),
                (7, "PRIMARY_SIDECAR_ASSOCIATION_NOT_APPROVED"),
                (8, "COMPOSITE_UNSPLIT_ROLE_DEFERRAL_NOT_ACKNOWLEDGED"),
            )
            if gate_results[index].result != "PASS"
        ]
        if any(item.result == "FAIL" for item in gate_results):
            disposition = "REJECT_ELIGIBLE_ASSET_SIDECAR"
        elif any(item.result == "INDETERMINATE" for item in gate_results):
            disposition = "INDETERMINATE_ELIGIBLE_ASSET_SIDECAR"
        else:
            disposition = "APPROVE_ELIGIBLE_ASSET_SIDECAR"
        approved = disposition == "APPROVE_ELIGIBLE_ASSET_SIDECAR"
        promotion_basis = (
            "Synthetic positive Promotion decision basis."
            if approved
            else "Synthetic non-positive Promotion decision basis."
        )
        checker_action = _document(
            {
                "document_profile": (
                    "sdc.generated-reference-asset-promotion-decision-action.v1"
                ),
                "action": "RECORDED_GENERATED_REFERENCE_ASSET_PROMOTION_DECISION",
                "actor_ref_sha256": hashlib.sha256(checker_identity_value).hexdigest(),
                "request_sha256": request_value.request_sha256,
                "policy_document_sha256": (
                    GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256
                ),
                "promotion_status_receipt_sha256": (
                    final_status_value.receipt.receipt_sha256
                ),
                "promotion_primary_asset_binding_sha256": (
                    promotion_binding.primary_asset_binding_sha256
                ),
                "promotion_at": promotion_at_value,
                "gate_results": [_explicit(item) for item in gate_results],
                "promotion_issue_codes": issue_codes,
                "promotion_basis": promotion_basis,
                "decision": disposition,
                "sidecar_materialization_allowed": approved,
            }
        )
        result = finalize_generated_reference_asset_promotion(
            request_value,
            upstream,
            request_status_value,
            requested_bible_value,
            requested_asset_value,
            final_status_value,
            promotion_bible_value,
            promotion_asset_value,
            maker_identity_bytes=maker_identity_value,
            maker_action_bytes=maker_action_value,
            checker_identity_bytes=checker_identity_value,
            checker_action_bytes=checker_action,
            promotion_at=promotion_at_value,
            primary_sidecar_association_result=association_result,
            primary_sidecar_association_basis=association_basis,
            composite_unsplit_role_deferral_result=deferral_result,
            composite_unsplit_role_deferral_basis=deferral_basis,
            promotion_basis=promotion_basis,
        )
        return result, checker_action, promotion_basis

    positive, positive_checker_action, positive_basis = finalize_with_association("PASS")
    assert positive.decision.decision == "APPROVE_ELIGIBLE_ASSET_SIDECAR"
    assert positive.sidecar is not None
    assert positive.sidecar.decision_sha256 == positive.decision.decision_sha256
    assert positive.sidecar.primary_asset_binding_replaced is False
    assert positive.sidecar.bible_active_binding_changed is False
    assert positive.sidecar.asset_version_v1_created is False
    assert (
        verify_generated_reference_asset_promotion_finalization(
            positive,
            request,
            upstream,
            request_status,
            bible,
            asset,
            final_status,
            bible,
            asset,
            maker_identity_bytes=maker_identity,
            maker_action_bytes=maker_action,
            checker_identity_bytes=checker_identity,
            checker_action_bytes=positive_checker_action,
            promotion_at=promotion_at,
            primary_sidecar_association_result="PASS",
            primary_sidecar_association_basis=association_basis,
            composite_unsplit_role_deferral_result="PASS",
            composite_unsplit_role_deferral_basis=deferral_basis,
            promotion_basis=positive_basis,
        )
        == positive
    )

    rejected, _rejected_action, _rejected_basis = finalize_with_association("FAIL")
    assert rejected.decision.decision == "REJECT_ELIGIBLE_ASSET_SIDECAR"
    assert rejected.decision.promotion_issue_codes == (
        "PRIMARY_SIDECAR_ASSOCIATION_NOT_APPROVED",
    )
    assert rejected.sidecar is None

    indeterminate, _indeterminate_action, _indeterminate_basis = (
        finalize_with_association("INDETERMINATE")
    )
    assert indeterminate.decision.decision == "INDETERMINATE_ELIGIBLE_ASSET_SIDECAR"
    assert indeterminate.decision.promotion_issue_codes == (
        "PRIMARY_SIDECAR_ASSOCIATION_NOT_APPROVED",
    )
    assert indeterminate.sidecar is None

    for deferral_result, expected_decision in (
        ("FAIL", "REJECT_ELIGIBLE_ASSET_SIDECAR"),
        ("INDETERMINATE", "INDETERMINATE_ELIGIBLE_ASSET_SIDECAR"),
    ):
        deferred, _deferred_action, _deferred_basis = finalize_with_association(
            "PASS", deferral_result=cast(Any, deferral_result)
        )
        assert deferred.decision.decision == expected_decision
        assert deferred.decision.promotion_issue_codes == (
            "COMPOSITE_UNSPLIT_ROLE_DEFERRAL_NOT_ACKNOWLEDGED",
        )
        assert deferred.sidecar is None

    with pytest.raises(GeneratedReferenceAssetPromotionError) as missing_sidecar_error:
        GeneratedReferenceAssetPromotionFinalizationResult(
            decision=positive.decision, sidecar=None
        )
    assert missing_sidecar_error.value.code == "CONTRACT_FIELD_INVALID"
    semantic_positive_decision = positive.decision.model_copy(
        update={"decision_sha256": "00" * 32}
    )
    authority_positive_decision = cast(
        CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
        _rehash_formal(positive.decision, {"provider_requests": 1}),
    )
    prohibited_positive_decision = cast(
        CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
        _rehash_formal(
            positive.decision,
            {"promotion_basis": "See https://example.invalid/prohibited."},
        ),
    )
    for malformed_positive_decision in (
        semantic_positive_decision,
        authority_positive_decision,
        prohibited_positive_decision,
    ):
        with pytest.raises(
            GeneratedReferenceAssetPromotionError
        ) as missing_sidecar_priority_error:
            GeneratedReferenceAssetPromotionFinalizationResult(
                decision=malformed_positive_decision,
                sidecar=None,
            )
        assert missing_sidecar_priority_error.value.code == "CONTRACT_FIELD_INVALID"

    with pytest.raises(GeneratedReferenceAssetPromotionError) as negative_sidecar_error:
        GeneratedReferenceAssetPromotionFinalizationResult(
            decision=rejected.decision, sidecar=positive.sidecar
        )
    assert negative_sidecar_error.value.code == "PROMOTION_GATE_NOT_PASS"
    assert positive.sidecar is not None
    authority_sidecar = cast(
        CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
        _rehash_formal(positive.sidecar, {"provider_requests": 1}),
    )
    url_scope = positive.sidecar.reviewed_rights_scope.model_copy(
        update={
            "review_basis": (
                "Synthetic negative-gate priority probe at "
                "https://example.invalid/prohibited."
            )
        }
    )
    prohibited_sidecar = cast(
        CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
        _rehash_formal(positive.sidecar, {"reviewed_rights_scope": url_scope}),
    )
    for late_failure_sidecar in (authority_sidecar, prohibited_sidecar):
        with pytest.raises(
            GeneratedReferenceAssetPromotionError
        ) as negative_priority_error:
            GeneratedReferenceAssetPromotionFinalizationResult(
                decision=rejected.decision,
                sidecar=late_failure_sidecar,
            )
        assert negative_priority_error.value.code == "PROMOTION_GATE_NOT_PASS"
    with pytest.raises(
        GeneratedReferenceAssetPromotionError
    ) as positive_authority_error:
        GeneratedReferenceAssetPromotionFinalizationResult(
            decision=positive.decision,
            sidecar=authority_sidecar,
        )
    assert positive_authority_error.value.code == "AUTHORITY_SURFACE_NONZERO"

    pair_and_authority_sidecar = cast(
        CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
        _rehash_formal(
            positive.sidecar,
            {"request_id": "different-request", "provider_requests": 1},
        ),
    )
    for pair_failure_sidecar in (
        pair_and_authority_sidecar,
        prohibited_sidecar,
    ):
        with pytest.raises(
            GeneratedReferenceAssetPromotionError
        ) as pair_priority_error:
            GeneratedReferenceAssetPromotionFinalizationResult(
                decision=positive.decision,
                sidecar=pair_failure_sidecar,
            )
        assert pair_priority_error.value.code == "CONTRACT_FIELD_INVALID"

    mismatched_sidecar = cast(
        CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
        _rehash_formal(positive.sidecar, {"request_id": "different-request"}),
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as pair_error:
        GeneratedReferenceAssetPromotionFinalizationResult(
            decision=positive.decision, sidecar=mismatched_sidecar
        )
    assert pair_error.value.code == "CONTRACT_FIELD_INVALID"

    original_build_identity = promotion_module._build_identity

    def fail_sidecar_build(
        model_type: type[BaseModel], values: Any
    ) -> BaseModel:
        if model_type is CreativeSampleGeneratedReferenceEligibleAssetSidecarV1:
            raise GeneratedReferenceAssetPromotionError(
                "CONTRACT_FIELD_INVALID", "synthetic Sidecar construction failure"
            )
        return original_build_identity(model_type, values)

    with monkeypatch.context() as patch:
        patch.setattr(promotion_module, "_build_identity", fail_sidecar_build)
        with pytest.raises(GeneratedReferenceAssetPromotionError) as atomic_error:
            finalize_with_association("PASS")
        assert atomic_error.value.code == "CONTRACT_FIELD_INVALID"

    role_aliases = (
        ("Promotion Maker", maker_identity),
        ("Qualification Qualifier", upstream.qualifier_identity_bytes),
        ("Manifest Checker", upstream.manifest_checker_identity_bytes),
        ("request Status Checker", request_status.status_checker_identity_bytes),
        ("final Status Checker", final_status.status_checker_identity_bytes),
    )
    for _role_name, aliased_identity in role_aliases:
        with pytest.raises(GeneratedReferenceAssetPromotionError) as role_error:
            finalize_with_association(
                "PASS", checker_identity_value=aliased_identity
            )
        assert role_error.value.code == "ROLE_SEPARATION_VIOLATION"

    reused_maker_identity = upstream.qualifier_identity_bytes
    reused_maker_action_source = cast(dict[str, object], json.loads(maker_action))
    reused_maker_action_source["actor_ref_sha256"] = hashlib.sha256(
        reused_maker_identity
    ).hexdigest()
    reused_maker_action = _document(reused_maker_action_source)
    reused_maker_request = prepare_generated_reference_asset_promotion_request(
        upstream,
        request_status,
        bible,
        asset,
        maker_identity_bytes=reused_maker_identity,
        maker_action_bytes=reused_maker_action,
        requested_at=requested_at,
        request_basis=request_basis,
    )
    reused_maker_result, _reused_checker_action, _reused_basis = (
        finalize_with_association(
            "PASS",
            request_value=reused_maker_request,
            maker_identity_value=reused_maker_identity,
            maker_action_value=reused_maker_action,
        )
    )
    assert reused_maker_result.sidecar is not None

    replay_calls = 0

    def prohibit_manifest_replay(*_args: object, **_kwargs: object) -> object:
        nonlocal replay_calls
        replay_calls += 1
        raise AssertionError("new-layer preflight must precede upstream replay")

    policy_request = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(
            request,
            {"policy_id": "sdc.generated-reference-asset-promotion-policy-tampered"},
            refresh_review_payload=True,
        ),
    )
    self_request = request.model_copy(update={"request_sha256": "00" * 32})
    authority_request = cast(
        CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
        _rehash_formal(request, {"provider_requests": 1}),
    )
    with monkeypatch.context() as patch:
        patch.setattr(
            promotion_module,
            "verify_generated_reference_rights_manifest",
            prohibit_manifest_replay,
        )
        for forged_request, expected_code in (
            (policy_request, "POLICY_IDENTITY_MISMATCH"),
            (self_request, "SEMANTIC_ID_OR_DIGEST_MISMATCH"),
            (authority_request, "AUTHORITY_SURFACE_NONZERO"),
        ):
            with pytest.raises(GeneratedReferenceAssetPromotionError) as preflight_error:
                finalize_with_association("PASS", request_value=forged_request)
            assert preflight_error.value.code == expected_code
        with pytest.raises(GeneratedReferenceAssetPromotionError) as exact_preflight_error:
            verify_generated_reference_asset_promotion_request(
                cast(Any, {}),
                upstream,
                request_status,
                bible,
                asset,
                maker_identity_bytes=maker_identity,
                maker_action_bytes=maker_action,
                requested_at=requested_at,
                request_basis=request_basis,
            )
        assert exact_preflight_error.value.code == "EXACT_INPUT_TYPE_REQUIRED"
        tampered_maker_action = cast(dict[str, object], json.loads(maker_action))
        tampered_maker_action["policy_document_sha256"] = "00" * 32
        with pytest.raises(GeneratedReferenceAssetPromotionError) as action_policy_error:
            prepare_generated_reference_asset_promotion_request(
                upstream,
                request_status,
                bible,
                asset,
                maker_identity_bytes=maker_identity,
                maker_action_bytes=_document(tampered_maker_action),
                requested_at=requested_at,
                request_basis=request_basis,
            )
        assert action_policy_error.value.code == "POLICY_IDENTITY_MISMATCH"
    assert replay_calls == 0

    with pytest.raises(GeneratedReferenceAssetPromotionError) as resource_priority_error:
        prepare_generated_reference_asset_promotion_request(
            upstream,
            request_status,
            bible,
            asset,
            maker_identity_bytes=maker_identity,
            maker_action_bytes=b" " * 262_145,
            requested_at=requested_at,
            request_basis="decomposed-e\u0301",
        )
    assert resource_priority_error.value.code == "DOCUMENT_RESOURCE_LIMIT_EXCEEDED"

    with pytest.raises(GeneratedReferenceAssetPromotionError) as prepare_contract_priority:
        prepare_generated_reference_asset_promotion_request(
            upstream,
            request_status,
            bible,
            asset,
            maker_identity_bytes=maker_identity,
            maker_action_bytes=maker_action,
            requested_at="not-a-time",
            request_basis="invalid\x00basis",
        )
    assert prepare_contract_priority.value.code == "CONTRACT_FIELD_INVALID"

    policy_mismatch_action = cast(dict[str, object], json.loads(maker_action))
    policy_mismatch_action["policy_document_sha256"] = "00" * 32
    with pytest.raises(GeneratedReferenceAssetPromotionError) as policy_contract_priority:
        prepare_generated_reference_asset_promotion_request(
            upstream,
            request_status,
            bible,
            asset,
            maker_identity_bytes=maker_identity,
            maker_action_bytes=_document(policy_mismatch_action),
            requested_at=requested_at,
            request_basis="invalid\x00basis",
        )
    assert policy_contract_priority.value.code == "CONTRACT_FIELD_INVALID"

    with pytest.raises(GeneratedReferenceAssetPromotionError) as finalize_contract_priority:
        finalize_generated_reference_asset_promotion(
            request,
            upstream,
            request_status,
            bible,
            asset,
            final_status,
            bible,
            asset,
            maker_identity_bytes=maker_identity,
            maker_action_bytes=maker_action,
            checker_identity_bytes=checker_identity,
            checker_action_bytes=positive_checker_action,
            promotion_at="not-a-time",
            primary_sidecar_association_result="PASS",
            primary_sidecar_association_basis="invalid\x00basis",
            composite_unsplit_role_deferral_result="PASS",
            composite_unsplit_role_deferral_basis=deferral_basis,
            promotion_basis=positive_basis,
        )
    assert finalize_contract_priority.value.code == "CONTRACT_FIELD_INVALID"

    checker_policy_mismatch = cast(
        dict[str, object], json.loads(positive_checker_action)
    )
    checker_policy_mismatch["policy_document_sha256"] = "00" * 32
    with pytest.raises(GeneratedReferenceAssetPromotionError) as final_policy_contract_priority:
        finalize_generated_reference_asset_promotion(
            request,
            upstream,
            request_status,
            bible,
            asset,
            final_status,
            bible,
            asset,
            maker_identity_bytes=maker_identity,
            maker_action_bytes=maker_action,
            checker_identity_bytes=checker_identity,
            checker_action_bytes=_document(checker_policy_mismatch),
            promotion_at=promotion_at,
            primary_sidecar_association_result="PASS",
            primary_sidecar_association_basis="invalid\x00basis",
            composite_unsplit_role_deferral_result="PASS",
            composite_unsplit_role_deferral_basis=deferral_basis,
            promotion_basis=positive_basis,
        )
    assert final_policy_contract_priority.value.code == "CONTRACT_FIELD_INVALID"

    for partial_status_substitute in (
        request_status.receipt,
        request_status.receipt.receipt_id,
        request_status.receipt.receipt_sha256,
    ):
        with pytest.raises(
            GeneratedReferenceAssetPromotionError
        ) as partial_receipt_error:
            prepare_generated_reference_asset_promotion_request(
                upstream,
                cast(Any, partial_status_substitute),
                bible,
                asset,
                maker_identity_bytes=maker_identity,
                maker_action_bytes=maker_action,
                requested_at=requested_at,
                request_basis=request_basis,
            )
        assert partial_receipt_error.value.code == "EXACT_INPUT_TYPE_REQUIRED"

    receipt_attacks = (
        (
            replace(
                request_status,
                receipt=request_status.receipt.model_copy(
                    update={"receipt_id": "generated_reference_status_receipt_v1_forged"}
                ),
            ),
            "STATUS_REPLAY_FAILED",
        ),
        (
            replace(
                request_status,
                receipt=request_status.receipt.model_copy(
                    update={"receipt_sha256": "00" * 32}
                ),
            ),
            "STATUS_REPLAY_FAILED",
        ),
        (
            replace(
                request_status,
                receipt=status_at(promotion_at).receipt,
            ),
            "STATUS_REPLAY_FAILED",
        ),
        (
            replace(
                request_status,
                record=request_status.record.model_copy(
                    update={"record_sha256": "00" * 32}
                ),
            ),
            "SEMANTIC_ID_OR_DIGEST_MISMATCH",
        ),
    )
    for attacked_status, expected_receipt_code in receipt_attacks:
        with pytest.raises(ValueError) as replay_attack_error:
            prepare_generated_reference_asset_promotion_request(
                upstream,
                attacked_status,
                bible,
                asset,
                maker_identity_bytes=maker_identity,
                maker_action_bytes=maker_action,
                requested_at=requested_at,
                request_basis=request_basis,
            )
        assert getattr(replay_attack_error.value, "code", None) == expected_receipt_code

    original_status_process = (
        process_generated_reference_current_status_record_as_of_assessment
    )
    replay_as_of_values: list[str] = []

    def count_status_replay(
        record_value: Any,
        manifest_value: Any,
        chain_inputs_value: Any,
        *,
        as_of: str,
    ) -> object:
        replay_as_of_values.append(as_of)
        return original_status_process(
            record_value, manifest_value, chain_inputs_value, as_of=as_of
        )

    with monkeypatch.context() as patch:
        patch.setattr(
            promotion_module,
            "process_generated_reference_current_status_record_as_of_assessment",
            count_status_replay,
        )
        replayed_result, _replayed_action, _replayed_basis = finalize_with_association(
            "PASS"
        )
    assert replayed_result.sidecar is not None
    assert requested_at in replay_as_of_values
    assert promotion_at in replay_as_of_values

    final_replay_failure = GeneratedReferenceJointReplayError(
        "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
        "synthetic promotion-time replay failure",
    )

    def fail_only_final_status_replay(
        record_value: Any,
        manifest_value: Any,
        chain_inputs_value: Any,
        *,
        as_of: str,
    ) -> object:
        if as_of == promotion_at:
            raise final_replay_failure
        return original_status_process(
            record_value, manifest_value, chain_inputs_value, as_of=as_of
        )

    with monkeypatch.context() as patch:
        patch.setattr(
            promotion_module,
            "process_generated_reference_current_status_record_as_of_assessment",
            fail_only_final_status_replay,
        )
        with pytest.raises(GeneratedReferenceJointReplayError) as final_replay_error:
            finalize_with_association("PASS")
        assert final_replay_error.value is final_replay_failure

    status_source = status_fixtures._status_source(materials.source_case)
    source_by_category = {
        cast(str, cast(dict[str, object], item)["category"]): cast(
            dict[str, object], item
        )
        for item in cast(list[object], status_source["observations"])
    }
    base_chain_members = {
        cast(str, chain.target_observation_refs[0].category): chain.observation_inputs
        for chain in status.chain_inputs
    }

    def replacement_genesis_status(
        category: str,
        source: dict[str, object],
        *,
        suffix: str,
    ) -> GeneratedReferenceAssetPromotionStatusClosureInput:
        replacement_genesis = status_fixtures._build_observation_input(
            subject_closure=status.subject_closure,
            source=source,
            suffix=suffix,
            link_kind="GENESIS",
        )
        replacement_targets = tuple(
            replacement_genesis
            if item.observation.category == category
            else item
            for item in status.observation_inputs
        )
        replacement_chains = dict(base_chain_members)
        replacement_chains[category] = (replacement_genesis,)
        replacement_status = rebuild_status_from_targets(
            replacement_targets,
            replacement_chains,
            as_of=promotion_at,
        )
        replayed_receipt = (
            process_generated_reference_current_status_record_as_of_assessment(
                replacement_status.record,
                upstream.manifest,
                replacement_status.chain_inputs,
                as_of=promotion_at,
            ).receipt
        )
        assert replayed_receipt == replacement_status.receipt
        return replacement_status

    omission_category = status.observation_inputs[0].observation.category
    omission_source = cast(
        dict[str, object],
        json.loads(json.dumps(source_by_category[omission_category])),
    )
    omission_source_reference = cast(
        dict[str, object], omission_source["source_reference"]
    )
    omission_source_reference["source_identity_ref"] = (
        f"{omission_source_reference['source_identity_ref']}-independent"
    )
    replay_valid_omission_status = replacement_genesis_status(
        omission_category,
        omission_source,
        suffix="monotonic-omission",
    )

    rewrite_category = status.observation_inputs[1].observation.category
    replay_valid_rewrite_status = replacement_genesis_status(
        rewrite_category,
        source_by_category[rewrite_category],
        suffix="monotonic-rewrite",
    )
    for attack_name, replay_valid_attack_status in (
        ("omission", replay_valid_omission_status),
        ("rewrite", replay_valid_rewrite_status),
    ):
        prior_ids = {
            item.observation.observation_id
            for chain in request_status.chain_inputs
            for item in chain.observation_inputs
        }
        final_ids = {
            item.observation.observation_id
            for chain in replay_valid_attack_status.chain_inputs
            for item in chain.observation_inputs
        }
        assert prior_ids - final_ids, f"{attack_name} must remove a prior occurrence"
        with pytest.raises(
            GeneratedReferenceAssetPromotionError
        ) as replay_valid_monotonic_error:
            finalize_with_association(
                "PASS", final_status_value=replay_valid_attack_status
            )
        assert isinstance(replay_valid_monotonic_error.value, ValueError)
        assert replay_valid_monotonic_error.value.code == "STATUS_REPLAY_FAILED"

    def successor_status(
        category: str,
        override: Any,
        *,
        suffix: str,
    ) -> GeneratedReferenceAssetPromotionStatusClosureInput:
        members = base_chain_members[category]
        assert len(members) == 1
        predecessor = (
            rights_module.generated_reference_current_status_chain_head(
                members[0].observation
            ),
        )
        successor = status_fixtures._build_observation_input(
            subject_closure=status.subject_closure,
            source=source_by_category[category],
            override=override,
            suffix=suffix,
            link_kind="SUCCESSOR",
            predecessor_heads=predecessor,
        )
        targets = tuple(
            successor if item.observation.category == category else item
            for item in status.observation_inputs
        )
        chains = dict(base_chain_members)
        chains[category] = (*members, successor)
        return rebuild_status_from_targets(
            targets,
            chains,
            as_of=promotion_at,
        )

    held_status = successor_status(
        "HOLD_ACTIVE",
        status_fixtures._ObservationOverride(
            claim_value="PRESENT",
            basis_code="HOLD_IMPOSED",
            source_kind="INTERNAL_HOLD_RECORD",
        ),
        suffix="promotion-held",
    )
    revoked_status = successor_status(
        "REVOCATION_EFFECTIVE",
        status_fixtures._ObservationOverride(
            claim_value="PRESENT",
            basis_code="REVOCATION_ISSUED",
        ),
        suffix="promotion-revoked",
    )
    expired_status = successor_status(
        "RIGHTS_BASIS_CURRENT",
        status_fixtures._ObservationOverride(
            claim_value="ABSENT_WITH_EVIDENCE",
            basis_code="RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED",
            valid_until=promotion_at,
        ),
        suffix="promotion-expired",
    )
    for status_name, non_current_status in (
        ("HELD", held_status),
        ("REVOKED", revoked_status),
        ("EXPIRED", expired_status),
    ):
        assert non_current_status.receipt.as_of_status == status_name
        non_current_result, _non_current_action, _non_current_basis = (
            finalize_with_association(
                "PASS", final_status_value=non_current_status
            )
        )
        assert non_current_result.decision.decision == (
            "REJECT_ELIGIBLE_ASSET_SIDECAR"
        )
        assert non_current_result.decision.promotion_issue_codes == (
            "STATUS_NOT_CURRENT_AT_PROMOTION",
        )
        assert non_current_result.sidecar is None

    distinct_final_status_checker = _document(
        {
            "document_profile": "sdc.privacy-minimized-human-reference.v1",
            "identity_namespace": "synthetic-promotion",
            "identity_ref": "distinct-final-status-checker",
        }
    )
    distinct_checker_status = rebuild_status_from_targets(
        tuple(status.observation_inputs),
        dict(base_chain_members),
        as_of=promotion_at,
        checker_identity_value=distinct_final_status_checker,
    )
    assert request_status.status_checker_identity_bytes != (
        distinct_checker_status.status_checker_identity_bytes
    )
    with pytest.raises(GeneratedReferenceAssetPromotionError) as distinct_role_error:
        finalize_with_association(
            "PASS",
            final_status_value=distinct_checker_status,
            checker_identity_value=distinct_final_status_checker,
        )
    assert distinct_role_error.value.code == "ROLE_SEPARATION_VIOLATION"

    fork_fixture = status_fixtures._build_status_closure(
        unresolved_fork_category="HOLD_ACTIVE"
    )
    fork_status = status_input_at(fork_fixture, promotion_at)
    assert fork_status.receipt.as_of_status == "INDETERMINATE"
    successor_result, _successor_action, _successor_basis = finalize_with_association(
        "PASS", final_status_value=fork_status
    )
    assert successor_result.decision.decision == (
        "INDETERMINATE_ELIGIBLE_ASSET_SIDECAR"
    )
    assert successor_result.decision.promotion_as_of_status == "INDETERMINATE"
    assert successor_result.decision.promotion_issue_codes == (
        "STATUS_NOT_CURRENT_AT_PROMOTION",
    )
    assert successor_result.sidecar is None
    assert len(
        {
            item.observation.observation_id
            for chain in fork_status.chain_inputs
            for item in chain.observation_inputs
        }
    ) > len(
        {
            item.observation.observation_id
            for chain in request_status.chain_inputs
            for item in chain.observation_inputs
        }
    )
    prior_ordinals = {
        (item.observation_id, item.observation_sha256, item.chain_sha256): item.ordinal
        for item in request_status.request.observation_refs
    }
    final_ordinals = {
        (item.observation_id, item.observation_sha256, item.chain_sha256): item.ordinal
        for item in fork_status.request.observation_refs
    }
    assert any(
        final_ordinals[anchor] != ordinal
        for anchor, ordinal in prior_ordinals.items()
        if anchor in final_ordinals
    )

    selected_chain = request_status.chain_inputs[0]
    rewritten_observation = replace(
        selected_chain.observation_inputs[0], document_bytes=b"{}\n"
    )
    rewritten_chain = replace(
        selected_chain,
        observation_inputs=(
            rewritten_observation,
            *selected_chain.observation_inputs[1:],
        ),
    )
    monotonic_attacks = (
        replace(request_status, chain_inputs=request_status.chain_inputs[1:]),
        replace(
            request_status,
            chain_inputs=(rewritten_chain, *request_status.chain_inputs[1:]),
        ),
        replace(
            request_status,
            request=request_status.request.model_copy(
                update={"observation_refs": request_status.request.observation_refs[1:]}
            ),
        ),
    )
    for attacked_final_status in monotonic_attacks:
        with pytest.raises(GeneratedReferenceAssetPromotionError) as monotonic_error:
            promotion_module._verify_final_record_monotonicity(
                request_status, attacked_final_status
            )
        assert monotonic_error.value.code == "STATUS_REPLAY_FAILED"

    fork_chain = next(
        item for item in fork_status.chain_inputs if len(item.observation_inputs) == 3
    )
    predecessor_heads = tuple(
        sorted(
            (
                rights_module.generated_reference_current_status_chain_head(
                    item.observation
                )
                for item in fork_chain.observation_inputs[1:]
            ),
            key=lambda item: (
                item.observation_id,
                item.observation_sha256,
                item.chain_sha256,
            ),
        )
    )
    status_source = status_fixtures._status_source(materials.source_case)
    hold_source = next(
        cast(dict[str, object], item)
        for item in cast(list[object], status_source["observations"])
        if cast(dict[str, object], item)["category"] == "HOLD_ACTIVE"
    )
    reconciliation_input = status_fixtures._build_observation_input(
        subject_closure=fork_status.subject_closure,
        source=hold_source,
        override=status_fixtures._ObservationOverride(
            claim_value="CONFLICT",
            basis_code="CONFLICT_IDENTIFIED",
            source_kind="INTERNAL_HOLD_RECORD",
        ),
        suffix="reconciled",
        link_kind="RECONCILIATION",
        predecessor_heads=predecessor_heads,
    )
    fork_hold_ids = {
        item.observation_id for item in fork_chain.target_observation_refs
    }
    reconciliation_targets = (
        reconciliation_input,
        *(
            item
            for item in fork_fixture.observation_inputs
            if item.observation.observation_id not in fork_hold_ids
        ),
    )
    reconciliation_members = {
        cast(str, chain.target_observation_refs[0].category): chain.observation_inputs
        for chain in fork_fixture.chain_inputs
    }
    reconciliation_members["HOLD_ACTIVE"] = (
        *fork_chain.observation_inputs,
        reconciliation_input,
    )
    reconciliation_status = rebuild_status_from_targets(
        reconciliation_targets,
        reconciliation_members,
        as_of=promotion_at,
    )
    promotion_module._verify_final_record_monotonicity(
        request_status, reconciliation_status
    )
    reconciliation_result, _reconciliation_action, _reconciliation_basis = (
        finalize_with_association(
            "PASS", final_status_value=reconciliation_status
        )
    )
    assert reconciliation_result.decision.decision == (
        "INDETERMINATE_ELIGIBLE_ASSET_SIDECAR"
    )
    assert reconciliation_result.sidecar is None

    rebuilt_reconciliation_chain = next(
        chain
        for chain in reconciliation_status.chain_inputs
        if chain.target_observation_refs[0].category == "HOLD_ACTIVE"
    )
    omitted_reconciliation_chain = replace(
        rebuilt_reconciliation_chain,
        observation_inputs=(
            rebuilt_reconciliation_chain.observation_inputs[0],
            *rebuilt_reconciliation_chain.observation_inputs[2:],
        ),
    )
    rewritten_reconciliation_chain = replace(
        rebuilt_reconciliation_chain,
        observation_inputs=(
            replace(
                rebuilt_reconciliation_chain.observation_inputs[0],
                document_bytes=b"{}\n",
            ),
            *rebuilt_reconciliation_chain.observation_inputs[1:],
        ),
    )
    for attacked_chain, expected_replay_code in (
        (omitted_reconciliation_chain, "ORPHAN_REFERENCE"),
        (rewritten_reconciliation_chain, "OBSERVATION_CONTRACT_INVALID"),
    ):
        attacked_reconciliation_status = replace(
            reconciliation_status,
            chain_inputs=tuple(
                attacked_chain
                if chain is rebuilt_reconciliation_chain
                else chain
                for chain in reconciliation_status.chain_inputs
            ),
        )
        with pytest.raises(
            GeneratedReferenceRightsCurrentStatusError
        ) as reconciliation_error:
            finalize_with_association(
                "PASS", final_status_value=attacked_reconciliation_status
            )
        assert reconciliation_error.value.code == "CHAIN_STRUCTURE_INVALID"
        assert reconciliation_error.value.replay_code == expected_replay_code

    drift_description = f"{asset.visual_description} Promotion-time drift."
    drift_asset = CharacterAssetVersion(
        id=CharacterAssetVersion.derive_id(
            character_id=asset.character_id,
            version=asset.version + 1,
            content_sha256="ab" * 32,
            media_type="image/png",
            approval_ref="synthetic_promotion_drift_review",
            visual_description=drift_description,
        ),
        character_id=asset.character_id,
        version=asset.version + 1,
        content_sha256="ab" * 32,
        media_type="image/png",
        approval_ref="synthetic_promotion_drift_review",
        visual_description=drift_description,
        provenance="IMPORTED_APPROVED_MEDIA",
    )
    drift_bible = CharacterBible(
        character_id=bible.character_id,
        name=bible.name,
        visual_description=bible.visual_description,
        asset_versions=(*bible.asset_versions, drift_asset),
        active_asset_version_id=drift_asset.id,
    )
    drift_result, _drift_action, _drift_basis = finalize_with_association(
        "PASS",
        promotion_bible_value=drift_bible,
        promotion_asset_value=drift_asset,
    )
    assert drift_result.decision.decision == "REJECT_ELIGIBLE_ASSET_SIDECAR"
    assert drift_result.decision.promotion_issue_codes == (
        "PRIMARY_BINDING_NO_LONGER_ACTIVE",
    )
    assert drift_result.sidecar is None

    other_character_bible, other_character_asset, _other_character_binding = (
        _character_binding()
    )
    scene_bible, scene_asset, _scene_binding_value = _scene_binding()
    for cross_bible, cross_asset in (
        (other_character_bible, other_character_asset),
        (scene_bible, scene_asset),
    ):
        with pytest.raises(GeneratedReferenceAssetPromotionError) as cross_binding_error:
            finalize_with_association(
                "PASS",
                promotion_bible_value=cross_bible,
                promotion_asset_value=cross_asset,
            )
        assert cross_binding_error.value.code == (
            "PRIMARY_ASSET_BINDING_CLOSURE_INVALID"
        )

    png_path = (
        ROOT
        / "tests/fixtures/visual_prompt_profiles/generated-reference-candidate/"
        "character-reference-synthetic-v1.png"
    )
    distinct_outcome_values = (
        creative_sample_generated_reference_provider_attempt_outcome_projection(
            upstream.outcome
        )
    )
    distinct_outcome_values["provider"] = f"{upstream.outcome.provider}-distinct"
    distinct_outcome = build_generated_reference_provider_attempt_outcome(
        distinct_outcome_values
    )
    distinct_candidate = capture_generated_reference_candidate(
        upstream.artifact,
        distinct_outcome,
        png_path=png_path,
    )
    assert png_path.read_bytes() == upstream.png_bytes
    assert distinct_candidate.media_content_sha256 == (
        upstream.candidate.media_content_sha256
    )
    assert distinct_outcome.outcome_id != upstream.outcome.outcome_id
    assert distinct_candidate.candidate_id != upstream.candidate.candidate_id

    distinct_preparer_action = _document(
        {
            "document_profile": (
                "sdc.generated-reference-qualification-request-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_QUALIFICATION_EVIDENCE",
            "actor_ref_sha256": hashlib.sha256(
                upstream.qualification_preparer_identity_bytes
            ).hexdigest(),
            "candidate_sha256": distinct_candidate.candidate_sha256,
            "provider_attempt_outcome_sha256": distinct_outcome.outcome_sha256,
            "policy_document_sha256": (
                GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256
            ),
            "requested_at": upstream.qualification_request.requested_at,
            "evidence_document_sha256s": [
                item.reference.document_sha256
                for item in upstream.qualification_evidence_documents
            ],
        }
    )
    distinct_qualification_request = (
        prepare_generated_reference_candidate_qualification_request(
            upstream.artifact,
            distinct_outcome,
            distinct_candidate,
            png_path=png_path,
            evidence_documents=upstream.qualification_evidence_documents,
            preparer_reference_bytes=upstream.qualification_preparer_identity_bytes,
            preparer_action_bytes=distinct_preparer_action,
            requested_at=upstream.qualification_request.requested_at,
        )
    )
    distinct_gates = upstream.qualification_decision.gate_results
    distinct_qualifier_action = _document(
        {
            "document_profile": (
                "sdc.generated-reference-qualification-decision-action.v1"
            ),
            "action": "RECORDED_GENERATED_REFERENCE_QUALIFICATION_DECISION",
            "actor_ref_sha256": hashlib.sha256(
                upstream.qualifier_identity_bytes
            ).hexdigest(),
            "request_sha256": distinct_qualification_request.request_sha256,
            "decision_at": upstream.qualification_decision.decision_at,
            "gate_results": [_explicit(item) for item in distinct_gates],
            "qualification_issue_codes": list(
                upstream.qualification_decision.qualification_issue_codes
            ),
            "qualification_basis": (
                upstream.qualification_decision.qualification_basis
            ),
            "decision": upstream.qualification_decision.decision,
            "eligible_for_separate_generated_rights_manifest_review": (
                upstream.qualification_decision
                .eligible_for_separate_generated_rights_manifest_review
            ),
        }
    )
    distinct_qualification_decision = (
        record_generated_reference_candidate_qualification_decision(
            upstream.artifact,
            distinct_outcome,
            distinct_candidate,
            distinct_qualification_request,
            png_path=png_path,
            evidence_documents=upstream.qualification_evidence_documents,
            preparer_reference_bytes=upstream.qualification_preparer_identity_bytes,
            preparer_action_bytes=distinct_preparer_action,
            qualifier_reference_bytes=upstream.qualifier_identity_bytes,
            qualifier_action_bytes=distinct_qualifier_action,
            decision_at=upstream.qualification_decision.decision_at,
            gate_results=distinct_gates,
            qualification_issue_codes=(
                upstream.qualification_decision.qualification_issue_codes
            ),
            qualification_basis=upstream.qualification_decision.qualification_basis,
            decision=upstream.qualification_decision.decision,
        )
    )
    distinct_occurrence_upstream = replace(
        upstream,
        outcome=distinct_outcome,
        candidate=distinct_candidate,
        qualification_request=distinct_qualification_request,
        qualification_decision=distinct_qualification_decision,
        qualification_preparer_action_bytes=distinct_preparer_action,
        qualifier_action_bytes=distinct_qualifier_action,
    )
    with pytest.raises(
        GeneratedReferenceRightsCurrentStatusError
    ) as distinct_occurrence_error:
        prepare_generated_reference_asset_promotion_request(
            distinct_occurrence_upstream,
            request_status,
            bible,
            asset,
            maker_identity_bytes=maker_identity,
            maker_action_bytes=maker_action,
            requested_at=requested_at,
            request_basis=request_basis,
        )
    assert distinct_occurrence_error.value.code == "UPSTREAM_CLOSURE_MISMATCH"

    scope = request.reviewed_rights_scope
    rights_scope_attacks = (
        (
            scope.model_copy(
                update={
                    "allowed_use_scope": (
                        *scope.allowed_use_scope,
                        "ZZ_SYNTHETIC_EXPANDED_USE",
                    )
                }
            ),
            "UPSTREAM_CLOSURE_MISMATCH",
        ),
        (
            scope.model_copy(update={"allowed_use_scope": ()}),
            "CONTRACT_FIELD_INVALID",
        ),
        (
            scope.model_copy(
                update={
                    "allowed_use_scope": (
                        "ZZ_SYNTHETIC_REORDERED_USE",
                        *scope.allowed_use_scope,
                    )
                }
            ),
            "CONTRACT_FIELD_INVALID",
        ),
        (
            scope.model_copy(
                update={"reviewed_scope_valid_until": "2026-08-30T03:00:00Z"}
            ),
            "UPSTREAM_CLOSURE_MISMATCH",
        ),
    )
    for forged_scope, expected_rights_code in rights_scope_attacks:
        forged_rights_request = cast(
            CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
            _rehash_formal(
                request,
                {"reviewed_rights_scope": forged_scope},
                refresh_review_payload=True,
            ),
        )
        with pytest.raises(ValueError) as rights_error:
            verify_generated_reference_asset_promotion_request(
                forged_rights_request,
                upstream,
                request_status,
                bible,
                asset,
                maker_identity_bytes=maker_identity,
                maker_action_bytes=maker_action,
                requested_at=requested_at,
                request_basis=request_basis,
            )
        assert getattr(rights_error.value, "code", None) == expected_rights_code

    expected_rights_fields = {
        "territory_scope",
        "allowed_use_scope",
        "reviewed_scope_valid_until",
        "output_copyright_and_commercial_scope_basis",
        "likeness_privacy_and_sensitive_data_basis",
        "brand_and_protected_content_basis",
        "retention_and_deletion_basis",
        "training_use_prohibition_basis",
        "review_basis",
    }
    assert set(type(scope).model_fields) == expected_rights_fields
    for field_name in expected_rights_fields:
        mutated_scope = scope.model_copy(
            update={
                field_name: _mutated_rights_scope_field(scope, field_name)
            }
        )
        mutated_rights_request = cast(
            CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
            _rehash_formal(
                request,
                {"reviewed_rights_scope": mutated_scope},
                refresh_review_payload=True,
            ),
        )
        with pytest.raises(GeneratedReferenceAssetPromotionError) as field_rights_error:
            verify_generated_reference_asset_promotion_request(
                mutated_rights_request,
                upstream,
                request_status,
                bible,
                asset,
                maker_identity_bytes=maker_identity,
                maker_action_bytes=maker_action,
                requested_at=requested_at,
                request_basis=request_basis,
            )
        assert field_rights_error.value.code == "UPSTREAM_CLOSURE_MISMATCH"

    formal_injections: tuple[
        tuple[
            BaseModel | None,
            dict[str, object],
            Callable[[Any], dict[str, object]],
            bool,
        ],
        ...,
    ] = (
        (
            request,
            {"role_assignment_embedded": True},
            creative_sample_generated_reference_asset_promotion_request_projection,
            True,
        ),
        (
            request,
            {"composite_media_unsplit": False},
            creative_sample_generated_reference_asset_promotion_request_projection,
            True,
        ),
        (
            request,
            {"provider_input_requested": True},
            creative_sample_generated_reference_asset_promotion_request_projection,
            True,
        ),
        (
            positive.decision,
            {"provider_input_eligible": True},
            creative_sample_generated_reference_asset_promotion_decision_projection,
            False,
        ),
        (
            positive.sidecar,
            {"composite_media_unsplit": False},
            creative_sample_generated_reference_eligible_asset_sidecar_projection,
            False,
        ),
    )
    for formal_value, update, projection_builder, refresh_review in formal_injections:
        assert formal_value is not None
        injected = _rehash_formal(
            formal_value,
            update,
            refresh_review_payload=refresh_review,
        )
        with pytest.raises(GeneratedReferenceAssetPromotionError) as injection_error:
            projection_builder(injected)
        assert injection_error.value.code == "CONTRACT_FIELD_INVALID"

    for injected_field in (
        "crop_box",
        "split_media",
        "role_assignment",
        "provider_task_id",
    ):
        injected_action = cast(dict[str, object], json.loads(maker_action))
        injected_action[injected_field] = "PROHIBITED"
        with pytest.raises(GeneratedReferenceAssetPromotionError) as action_injection_error:
            prepare_generated_reference_asset_promotion_request(
                upstream,
                request_status,
                bible,
                asset,
                maker_identity_bytes=maker_identity,
                maker_action_bytes=_document(injected_action),
                requested_at=requested_at,
                request_basis=request_basis,
            )
        assert action_injection_error.value.code == "CONTRACT_FIELD_INVALID"

    for upper_bound in (
        request.request_valid_until,
        request.qualification_valid_until,
        request.manifest_valid_until,
        request.requested_status_valid_until,
    ):
        with pytest.raises(GeneratedReferenceAssetPromotionError) as boundary_error:
            finalize_with_association("PASS", promotion_at_value=upper_bound)
        assert boundary_error.value.code == "TIME_WINDOW_INVALID_OR_EXPIRED"

    upstream_failure = GeneratedReferenceRightsCurrentStatusError(
        "REPLAY_MISMATCH", "synthetic nested Manifest replay failure"
    )

    def fail_manifest_replay(*_args: object, **_kwargs: object) -> object:
        raise upstream_failure

    with monkeypatch.context() as patch:
        patch.setattr(
            promotion_module,
            "verify_generated_reference_rights_manifest",
            fail_manifest_replay,
        )
        with pytest.raises(GeneratedReferenceRightsCurrentStatusError) as caught_upstream:
            prepare_generated_reference_asset_promotion_request(
                upstream,
                request_status,
                bible,
                asset,
                maker_identity_bytes=maker_identity,
                maker_action_bytes=maker_action,
                requested_at=requested_at,
                request_basis=request_basis,
            )
        assert caught_upstream.value is upstream_failure
        assert caught_upstream.value.code == "REPLAY_MISMATCH"

    status_failure = GeneratedReferenceJointReplayError(
        "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
        "synthetic nested status replay failure",
    )

    def fail_status_replay(*_args: object, **_kwargs: object) -> object:
        raise status_failure

    with monkeypatch.context() as patch:
        patch.setattr(
            promotion_module,
            "verify_generated_reference_current_status_evidence_record",
            fail_status_replay,
        )
        with pytest.raises(GeneratedReferenceJointReplayError) as caught_status:
            prepare_generated_reference_asset_promotion_request(
                upstream,
                request_status,
                bible,
                asset,
                maker_identity_bytes=maker_identity,
                maker_action_bytes=maker_action,
                requested_at=requested_at,
                request_basis=request_basis,
            )
        assert caught_status.value is status_failure
        assert caught_status.value.code == "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED"
