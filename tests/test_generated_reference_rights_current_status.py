from __future__ import annotations

import ast
import copy
import hashlib
import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ValidationError

import sdc.generated_reference_rights_current_status as rights
import sdc.generated_reference_rights_current_status_codegen as codegen
from sdc.contracts import (
    CharacterAssetVersion,
    CharacterBible,
    GenerationJob,
    InputMaterial,
    JobGraph,
    ProviderRequest,
    SceneAssetVersion,
    SceneBible,
)

ROOT = Path(__file__).parents[1]

MANIFEST_POLICY_SIZE = 4_686
MANIFEST_POLICY_SHA256 = "7d9f72f134b5be5f68bb55f25ee898736bd84d39b2ff6917e0e2ecab447f8f16"
CURRENT_STATUS_POLICY_SIZE = 14_138
CURRENT_STATUS_POLICY_SHA256 = "cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0"

ZERO_AUTHORITY_FIELDS: Mapping[str, object] = {
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

DOMAINS = (
    rights.GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW_PAYLOAD_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_RIGHTS_MANIFEST_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_SUBJECT_CLOSURE_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_OBSERVATION_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_CHAIN_SCOPE_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_CHAIN_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_OBSERVATION_SET_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_REQUEST_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_INSTRUCTION_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_DECISION_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_RECORD_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_EXPLICIT_CHAIN_SET_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_COVERAGE_SET_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_JOINT_REPLAY_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_PROVENANCE_SHA256_DOMAIN,
    rights.GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_SHA256_DOMAIN,
)

FORMAL_ZERO_AUTHORITY_TYPES: tuple[type[BaseModel], ...] = (
    rights.CreativeSampleGeneratedReferenceRightsManifestV1,
    rights.CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
    rights.CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    rights.CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
    rights.CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
    rights.CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    rights.CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
)


def _compact_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _semantic_sha256(domain: bytes, projection: object) -> str:
    """Independent known-answer calculator; it does not call a production hash helper."""

    return hashlib.sha256(domain + _compact_json(projection)).hexdigest()


def _raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def _semantic_leaf_paths(
    value: object, prefix: tuple[object, ...] = ()
) -> Iterator[tuple[object, ...]]:
    if type(value) is dict:
        for key, item in cast(dict[str, object], value).items():
            yield from _semantic_leaf_paths(item, (*prefix, key))
        return
    if type(value) is list:
        for index, item in enumerate(cast(list[object], value)):
            yield from _semantic_leaf_paths(item, (*prefix, index))
        return
    yield prefix


def _mutated_leaf(value: object) -> object:
    if value is None:
        return "mutated"
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        return value + "-mutated"
    raise AssertionError(f"unexpected semantic leaf type: {type(value)!r}")


def _mutate_semantic_leaf(value: dict[str, object], path: tuple[object, ...]) -> dict[str, object]:
    result = copy.deepcopy(value)
    cursor: object = result
    for segment in path[:-1]:
        if type(cursor) is dict:
            cursor = cast(dict[str, object], cursor)[cast(str, segment)]
        else:
            cursor = cast(list[object], cursor)[cast(int, segment)]
    final = path[-1]
    if type(cursor) is dict:
        mapping = cast(dict[str, object], cursor)
        mapping[cast(str, final)] = _mutated_leaf(mapping[cast(str, final)])
    else:
        items = cast(list[object], cursor)
        items[cast(int, final)] = _mutated_leaf(items[cast(int, final)])
    return result


def _assert_zero_authority(value: BaseModel) -> None:
    for field_name, expected in ZERO_AUTHORITY_FIELDS.items():
        assert getattr(value, field_name) == expected


@dataclass(frozen=True, slots=True)
class _ManifestMaterials:
    source_case: dict[str, object]
    upstream: Any
    manifest_closure: Any

    @property
    def manifest(self) -> rights.CreativeSampleGeneratedReferenceRightsManifestV1:
        return cast(
            rights.CreativeSampleGeneratedReferenceRightsManifestV1,
            self.manifest_closure.manifest,
        )


@dataclass(frozen=True, slots=True)
class _ObservationOverride:
    claim_value: str
    basis_code: str
    source_kind: str | None = None
    valid_until: str | None = None


@dataclass(frozen=True, slots=True)
class _StatusClosure:
    manifest: rights.CreativeSampleGeneratedReferenceRightsManifestV1
    subject_closure: rights.GeneratedReferenceCurrentStatusSubjectClosureV1
    observation_inputs: tuple[rights.GeneratedReferenceCurrentStatusObservationInput, ...]
    request: rights.CreativeSampleGeneratedReferenceCurrentStatusRequestV1
    chain_inputs: tuple[rights.GeneratedReferenceCurrentStatusExplicitChainInput, ...]
    status_preparer_identity_bytes: bytes
    status_preparer_action_bytes: bytes
    status_checker_identity_bytes: bytes
    status_checker_action_bytes: bytes
    instruction: rights.CreativeSampleGeneratedReferenceCurrentStatusInstructionV1
    decision: rights.CreativeSampleGeneratedReferenceCurrentStatusDecisionV1
    record: rights.CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1


@cache
def _manifest_materials() -> _ManifestMaterials:
    protected = codegen._load_protected_inputs(ROOT)
    source_case = codegen._assert_source_shape(protected.reviewed_source)
    upstream = codegen._build_upstream(protected, source_case)
    manifest_closure = codegen._build_manifest(source_case, upstream)
    return _ManifestMaterials(
        source_case=source_case,
        upstream=upstream,
        manifest_closure=manifest_closure,
    )


def _role_identity_bytes(source_case: dict[str, object], role_name: str) -> bytes:
    role = codegen._role(source_case, role_name)
    return _canonical_document(role["identity_record"])


def _status_source(source_case: dict[str, object]) -> dict[str, object]:
    value = source_case["current_status"]
    assert type(value) is dict
    return cast(dict[str, object], value)


def _build_observation_input(
    *,
    subject_closure: rights.GeneratedReferenceCurrentStatusSubjectClosureV1,
    source: dict[str, object],
    override: _ObservationOverride | None = None,
    suffix: str = "",
    link_kind: str | None = None,
    predecessor_heads: tuple[rights.GeneratedReferenceCurrentStatusChainHeadRefV1, ...] = (),
) -> rights.GeneratedReferenceCurrentStatusObservationInput:
    claim_value = override.claim_value if override is not None else source["claim_value"]
    basis_code = override.basis_code if override is not None else source["basis_code"]
    source_kind = (
        override.source_kind
        if override is not None and override.source_kind is not None
        else source["source_kind"]
    )
    valid_until = (
        override.valid_until
        if override is not None and override.valid_until is not None
        else source["valid_until"]
    )
    source_reference = copy.deepcopy(cast(dict[str, object], source["source_reference"]))
    source_object = copy.deepcopy(cast(dict[str, object], source["source_object"]))
    source_object_ref = cast(str, source["source_object_ref"])
    basis_note = cast(str, source["basis_note"])
    observed_at = cast(str, source["observed_at"])
    source_event_at = cast(str, source["source_event_at"])
    valid_from = cast(str, source["valid_from"])
    if suffix:
        source_object_ref = f"{source_object_ref}-{suffix}"
        source_object["record_id"] = f"{source_object['record_id']}-{suffix}"
        source_object["synthetic_finding"] = (
            f"First-party synthetic {suffix} branch for deterministic fork replay."
        )
        basis_note = f"First-party synthetic {suffix} branch for deterministic fork replay."
        observed_at = "2026-08-29T02:40:00Z" if suffix == "left" else "2026-08-29T02:41:00Z"
        source_event_at = (
            "2026-08-29T02:30:00Z" if suffix == "left" else "2026-08-29T02:31:00Z"
        )
        valid_from = "2026-08-29T02:30:00Z"
    observation = rights.build_generated_reference_current_status_source_observation(
        subject_closure=subject_closure,
        category=cast(Any, source["category"]),
        claim_value=cast(Any, claim_value),
        source_kind=cast(Any, source_kind),
        basis_code=cast(Any, basis_code),
        basis_note=basis_note,
        source_identity_bytes=_canonical_document(source_reference),
        source_object_ref=source_object_ref,
        source_object_bytes=_canonical_document(source_object),
        source_object_media_type=cast(str, source["source_object_media_type"]),
        source_event_at=source_event_at,
        observed_at=observed_at,
        valid_from=valid_from,
        valid_until=cast(str, valid_until),
        link_kind=cast(Any, link_kind or source["link_kind"]),
        predecessor_heads=predecessor_heads,
    )
    return rights.GeneratedReferenceCurrentStatusObservationInput(
        observation=observation,
        document_bytes=rights.generated_reference_contract_document_bytes(observation),
    )


def _canonical_request_refs(
    inputs: Sequence[rights.GeneratedReferenceCurrentStatusObservationInput],
) -> tuple[rights.GeneratedReferenceCurrentStatusObservationRefV1, ...]:
    category_index = {
        category: index for index, category in enumerate(rights.CURRENT_STATUS_CATEGORY_ORDER)
    }
    refs = [
        rights.generated_reference_current_status_observation_ref(item.observation, ordinal=0)
        for item in inputs
    ]
    refs.sort(
        key=lambda item: (
            category_index[item.category],
            item.valid_from,
            item.observation_id,
        )
    )
    return tuple(
        rights.GeneratedReferenceCurrentStatusObservationRefV1.model_validate(
            {**item.model_dump(mode="python"), "ordinal": ordinal}
        )
        for ordinal, item in enumerate(refs)
    )


def _manual_category_results(
    *,
    request: rights.CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    chain_inputs: tuple[rights.GeneratedReferenceCurrentStatusExplicitChainInput, ...],
    evaluated_at: str,
    unresolved_fork_category: str | None,
) -> tuple[rights.GeneratedReferenceCurrentStatusCategoryResultV1, ...]:
    observations = {
        item.observation.observation_id: item.observation
        for chain in chain_inputs
        for item in chain.observation_inputs
    }
    results: list[rights.GeneratedReferenceCurrentStatusCategoryResultV1] = []
    adverse = set(rights.CURRENT_STATUS_CATEGORY_ORDER[:4])
    for ordinal, category in enumerate(rights.CURRENT_STATUS_CATEGORY_ORDER):
        category_refs = tuple(
            item for item in request.observation_refs if item.category == category
        )
        relied = tuple(
            item
            for item in category_refs
            if observations[item.observation_id].claim_value != "NOT_ASSESSED"
            and max(observations[item.observation_id].observed_at, item.valid_from)
            <= evaluated_at
            < item.valid_until
        )
        claims = {observations[item.observation_id].claim_value for item in relied}
        if not relied:
            claim = "NOT_ASSESSED"
        elif len(claims) > 1 or category == unresolved_fork_category:
            claim = "CONFLICT"
        else:
            claim = next(iter(claims))
        if claim in {"UNKNOWN", "NOT_ASSESSED", "CONFLICT"}:
            effect = "INDETERMINATE"
        elif category in adverse:
            effect = "ADVERSE_PRESENT" if claim == "PRESENT" else "ADVERSE_ABSENT"
        else:
            effect = "POSITIVE_PRESENT" if claim == "PRESENT" else "POSITIVE_ABSENT"
        deadlines = [request.request_valid_until, request.subject_closure.manifest_valid_until]
        deadlines.extend(item.valid_until for item in relied)
        results.append(
            rights.GeneratedReferenceCurrentStatusCategoryResultV1(
                ordinal=ordinal,
                category=category,
                claim_value=cast(Any, claim),
                deterministic_effect=cast(Any, effect),
                category_observation_refs=category_refs,
                relied_on_observation_refs=relied,
                result_valid_until=min(deadlines),
            )
        )
    return tuple(results)


def _manual_recorded_status(
    results: tuple[rights.GeneratedReferenceCurrentStatusCategoryResultV1, ...],
) -> str:
    by_category: dict[str, str] = {
        item.category: item.deterministic_effect for item in results
    }
    if by_category["REVOCATION_EFFECTIVE"] == "ADVERSE_PRESENT":
        return "REVOKED"
    held = any(
        by_category[category] == "ADVERSE_PRESENT"
        for category in ("HOLD_ACTIVE", "COMPLAINT_OPEN", "DISPUTE_OPEN")
    ) or any(
        by_category[category] == "POSITIVE_ABSENT"
        for category in rights.CURRENT_STATUS_CATEGORY_ORDER[4:]
    )
    if held:
        return "HELD"
    if any(item.deterministic_effect == "INDETERMINATE" for item in results):
        return "INDETERMINATE"
    return "CURRENT"


def _build_status_closure(
    overrides: Mapping[str, _ObservationOverride] | None = None,
    *,
    unresolved_fork_category: str | None = None,
) -> _StatusClosure:
    materials = _manifest_materials()
    manifest = materials.manifest
    subject_closure = rights.build_generated_reference_current_status_subject_closure(manifest)
    current_source = _status_source(materials.source_case)
    raw_observations = cast(list[object], current_source["observations"])
    source_by_category = {
        cast(str, cast(dict[str, object], item)["category"]): cast(dict[str, object], item)
        for item in raw_observations
    }
    overrides = overrides or {}
    target_inputs: list[rights.GeneratedReferenceCurrentStatusObservationInput] = []
    chain_members: dict[
        str, tuple[rights.GeneratedReferenceCurrentStatusObservationInput, ...]
    ] = {}
    for category in rights.CURRENT_STATUS_CATEGORY_ORDER:
        source = source_by_category[category]
        genesis = _build_observation_input(
            subject_closure=subject_closure,
            source=source,
            override=overrides.get(category),
        )
        if category == unresolved_fork_category:
            branch_override = _ObservationOverride(
                claim_value="PRESENT",
                basis_code="HOLD_IMPOSED",
                source_kind="INTERNAL_HOLD_RECORD",
            )
            predecessor = (
                rights.generated_reference_current_status_chain_head(genesis.observation),
            )
            left = _build_observation_input(
                subject_closure=subject_closure,
                source=source,
                override=branch_override,
                suffix="left",
                link_kind="SUCCESSOR",
                predecessor_heads=predecessor,
            )
            right = _build_observation_input(
                subject_closure=subject_closure,
                source=source,
                override=branch_override,
                suffix="right",
                link_kind="SUCCESSOR",
                predecessor_heads=predecessor,
            )
            target_inputs.extend((left, right))
            chain_members[category] = (genesis, left, right)
        else:
            target_inputs.append(genesis)
            chain_members[category] = (genesis,)

    preparer_identity = _role_identity_bytes(materials.source_case, "STATUS_PREPARER")
    checker_identity = _role_identity_bytes(materials.source_case, "STATUS_CHECKER")
    requested_at = "2026-08-29T03:00:00Z"
    request_basis = cast(str, current_source["request_basis"])
    request_refs = _canonical_request_refs(target_inputs)
    request_valid_until = min("2026-08-30T03:00:00Z", manifest.manifest_valid_until)
    preparer_action = _canonical_document(
        {
            "document_profile": (
                "sdc.generated-reference-current-status-request-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_CURRENT_STATUS_REQUEST",
            "actor_identity_ref_sha256": _raw_sha256(preparer_identity),
            "subject_closure_sha256": subject_closure.closure_sha256,
            "policy_document_sha256": (
                rights.GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256
            ),
            "requested_at": requested_at,
            "request_valid_until": request_valid_until,
            "observation_target_refs": [item.model_dump(mode="json") for item in request_refs],
            "request_basis": request_basis,
        }
    )
    request = rights.build_generated_reference_current_status_request(
        subject_closure=subject_closure,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        requested_at=requested_at,
        target_observations=tuple(target_inputs),
        request_basis=request_basis,
    )
    assert request.observation_refs == request_refs

    ref_by_id = {item.observation_id: item for item in request.observation_refs}
    unsorted_chains: list[rights.GeneratedReferenceCurrentStatusExplicitChainInput] = []
    for category in rights.CURRENT_STATUS_CATEGORY_ORDER:
        members = chain_members[category]
        target_members = (
            members[1:] if category == unresolved_fork_category else members
        )
        unsorted_chains.append(
            rights.GeneratedReferenceCurrentStatusExplicitChainInput(
                target_observation_refs=tuple(
                    ref_by_id[item.observation.observation_id] for item in target_members
                ),
                observation_inputs=members,
            )
        )
    chain_inputs = tuple(
        sorted(
            unsorted_chains,
            key=lambda item: (
                item.observation_inputs[0].observation.chain_link.chain_scope_sha256,
                item.observation_inputs[0].observation.observation_id,
            ),
        )
    )
    evaluated_at = "2026-08-29T04:00:00Z"
    category_results = _manual_category_results(
        request=request,
        chain_inputs=chain_inputs,
        evaluated_at=evaluated_at,
        unresolved_fork_category=unresolved_fork_category,
    )
    checker_basis = cast(str, current_source["status_checker_basis"])
    checker_action = _canonical_document(
        {
            "document_profile": (
                "sdc.generated-reference-current-status-decision-checker-action.v1"
            ),
            "action": "RECORDED_GENERATED_REFERENCE_CURRENT_STATUS_DECISION",
            "actor_identity_ref_sha256": _raw_sha256(checker_identity),
            "request_sha256": request.request_sha256,
            "evaluated_at": evaluated_at,
            "category_results": [item.model_dump(mode="json") for item in category_results],
            "checker_basis": checker_basis,
            "status_valid_until": min(item.result_valid_until for item in category_results),
            "recorded_status": _manual_recorded_status(category_results),
        }
    )
    instruction = rights.build_generated_reference_current_status_instruction(
        request=request,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
        evaluated_at=evaluated_at,
        checker_basis=checker_basis,
    )
    assert instruction.category_results == category_results
    decision = rights.build_generated_reference_current_status_decision(
        request=request,
        instruction=instruction,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
    )
    record = rights.build_generated_reference_current_status_evidence_record(
        request=request,
        instruction=instruction,
        decision=decision,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
    )
    return _StatusClosure(
        manifest=manifest,
        subject_closure=subject_closure,
        observation_inputs=tuple(target_inputs),
        request=request,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
        instruction=instruction,
        decision=decision,
        record=record,
    )


@cache
def _current_closure() -> _StatusClosure:
    return _build_status_closure()


def _rehash_manifest_values(
    manifest: rights.CreativeSampleGeneratedReferenceRightsManifestV1,
    mutate: Any,
) -> dict[str, object]:
    values = cast(dict[str, object], manifest.model_dump(mode="python"))
    mutate(values)
    payload = rights.generated_reference_rights_manifest_review_payload_projection(manifest)
    for key in tuple(payload):
        if key in values:
            payload[key] = values[key]
    values["manifest_review_payload_sha256"] = _semantic_sha256(
        rights.GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW_PAYLOAD_SHA256_DOMAIN,
        payload,
    )
    projection = {
        key: value
        for key, value in values.items()
        if key not in {"manifest_id", "manifest_sha256"}
    }
    digest = _semantic_sha256(rights.GENERATED_REFERENCE_RIGHTS_MANIFEST_SHA256_DOMAIN, projection)
    values["manifest_id"] = f"generated_reference_rights_manifest_v1_{digest[:20]}"
    values["manifest_sha256"] = digest
    return values


def _rehash_contract_values(
    value: BaseModel,
    mutate: Any,
    *,
    domain: bytes,
    id_field: str,
    sha_field: str,
    stem: str,
) -> dict[str, object]:
    values = cast(dict[str, object], value.model_dump(mode="python"))
    mutate(values)
    projection = {
        key: item for key, item in values.items() if key not in {id_field, sha_field}
    }
    digest = _semantic_sha256(domain, projection)
    values[id_field] = f"{stem}{digest[:20]}"
    values[sha_field] = digest
    return values


def _manifest_builder_kwargs(materials: _ManifestMaterials) -> dict[str, object]:
    upstream = materials.upstream
    closure = materials.manifest_closure
    return {
        "artifact": upstream.artifact,
        "outcome": upstream.outcome,
        "candidate": upstream.candidate,
        "qualification_request": upstream.qualification_request,
        "qualification_decision": upstream.qualification_decision,
        "png_bytes": upstream.png_bytes,
        "qualification_evidence_documents": upstream.evidence_inputs,
        "qualification_preparer_identity_bytes": upstream.preparer_identity_bytes,
        "qualification_preparer_action_bytes": upstream.preparer_action_bytes,
        "qualifier_identity_bytes": upstream.qualifier_identity_bytes,
        "qualifier_action_bytes": upstream.qualifier_action_bytes,
        "review_evidence_documents": tuple(
            rights.GeneratedReferenceRightsManifestEvidenceInput(
                reference=reference, document_bytes=document
            )
            for reference, document in zip(
                closure.manifest.review_evidence_refs,
                closure.review_evidence_documents,
                strict=True,
            )
        ),
        "proposed_rights_scope": closure.manifest.proposed_rights_scope,
        "maker_identity_bytes": closure.maker_identity_bytes,
        "maker_action_bytes": closure.maker_action_bytes,
        "checker_identity_bytes": closure.checker_identity_bytes,
        "checker_action_bytes": closure.checker_action_bytes,
        "manifest_at": closure.manifest.manifest_at,
    }


def test_manifest_exact_gates_roles_times_scope_and_historical_submission_are_fail_closed() -> None:
    materials = _manifest_materials()
    manifest = materials.manifest
    assert len(materials.upstream.qualification_decision.gate_results) == 15
    assert all(
        item.result == "PASS"
        for item in materials.upstream.qualification_decision.gate_results
    )
    assert tuple(item.gate for item in manifest.gate_results) == rights.MANIFEST_REVIEW_GATE_ORDER
    assert tuple(item.ordinal for item in manifest.gate_results) == tuple(range(11))
    assert tuple(item.category for item in manifest.review_evidence_refs) == (
        rights.MANIFEST_REVIEW_EVIDENCE_CATEGORY_ORDER
    )
    assert tuple(item.ordinal for item in manifest.review_evidence_refs) == tuple(range(9))
    assert all(item.result == "PASS" for item in manifest.gate_results)
    assert manifest.maker_identity_ref_sha256 != manifest.checker_identity_ref_sha256
    assert manifest.maker_action_sha256 != manifest.checker_action_sha256
    assert manifest.qualification_decision_at <= manifest.maker_prepared_at
    assert manifest.maker_prepared_at <= manifest.manifest_at == manifest.checker_reviewed_at
    assert manifest.manifest_at < manifest.qualification_valid_until

    def gate_failure(values: dict[str, object]) -> None:
        gates = cast(list[dict[str, object]], values["gate_results"])
        gates[4]["result"] = "FAIL"

    def gate_evidence_drift(values: dict[str, object]) -> None:
        gates = cast(list[dict[str, object]], values["gate_results"])
        gates[4]["evidence_record_ids"] = []

    def role_alias(values: dict[str, object]) -> None:
        values["checker_identity_ref_sha256"] = values["maker_identity_ref_sha256"]

    def action_alias(values: dict[str, object]) -> None:
        values["checker_action_sha256"] = values["maker_action_sha256"]

    def checker_time_drift(values: dict[str, object]) -> None:
        values["checker_reviewed_at"] = "2026-08-29T02:00:01Z"

    def qualification_upper_bound(values: dict[str, object]) -> None:
        boundary = cast(str, values["qualification_valid_until"])
        values["manifest_at"] = boundary
        values["checker_reviewed_at"] = boundary

    def reviewed_scope_broadens(values: dict[str, object]) -> None:
        reviewed = cast(dict[str, object], values["reviewed_rights_scope"])
        reviewed["allowed_use_scope"] = ["OFFLINE_DETERMINISTIC_TESTING_ONLY", "PUBLICATION"]

    def later_review_cannot_cure_submission(values: dict[str, object]) -> None:
        evidence = cast(list[dict[str, object]], values["review_evidence_refs"])
        evidence[0]["effective_from"] = "2026-08-02T00:00:00Z"
        assert cast(str, values["submitted_at"]) < cast(str, evidence[0]["effective_from"])
        assert cast(str, evidence[0]["effective_from"]) < cast(str, evidence[0]["observed_at"])
        assert cast(str, evidence[0]["observed_at"]) < cast(str, values["manifest_at"])

    for mutator in (
        gate_failure,
        gate_evidence_drift,
        role_alias,
        action_alias,
        checker_time_drift,
        qualification_upper_bound,
        reviewed_scope_broadens,
        later_review_cannot_cure_submission,
    ):
        with pytest.raises(ValidationError):
            rights.CreativeSampleGeneratedReferenceRightsManifestV1.model_validate(
                _rehash_manifest_values(manifest, mutator)
            )


def test_manifest_checker_cannot_alias_qualification_qualifier() -> None:
    materials = _manifest_materials()
    kwargs = _manifest_builder_kwargs(materials)
    kwargs["checker_identity_bytes"] = materials.upstream.qualifier_identity_bytes
    with pytest.raises(
        rights.GeneratedReferenceRightsCurrentStatusError,
        match="MANIFEST_CLOSURE_REVALIDATION_FAILED",
    ):
        rights.build_generated_reference_rights_manifest(**cast(Any, kwargs))


def test_current_known_answer_has_nine_categories_current_and_exact_expiry() -> None:
    closure = _current_closure()
    assert tuple(item.category for item in closure.instruction.category_results) == (
        rights.CURRENT_STATUS_CATEGORY_ORDER
    )
    assert tuple(item.deterministic_effect for item in closure.instruction.category_results) == (
        "ADVERSE_ABSENT",
        "ADVERSE_ABSENT",
        "ADVERSE_ABSENT",
        "ADVERSE_ABSENT",
        "POSITIVE_PRESENT",
        "POSITIVE_PRESENT",
        "POSITIVE_PRESENT",
        "POSITIVE_PRESENT",
        "POSITIVE_PRESENT",
    )
    assert closure.decision.recorded_status == "CURRENT"
    assert closure.decision.status_valid_until == "2026-08-30T01:30:00Z"
    assert closure.request.request_valid_until == "2026-08-30T02:00:00Z"

    assessment = rights.assess_generated_reference_current_status_record_as_of(
        closure.record,
        closure.manifest,
        closure.chain_inputs,
        as_of="2026-08-29T05:00:00Z",
    )
    assert assessment.recorded_status == assessment.as_of_status == "CURRENT"
    at_upper_bound = rights.assess_generated_reference_current_status_record_as_of(
        closure.record,
        closure.manifest,
        closure.chain_inputs,
        as_of=closure.decision.status_valid_until,
    )
    assert at_upper_bound.recorded_status == "CURRENT"
    assert at_upper_bound.as_of_status == "EXPIRED"
    with pytest.raises(
        rights.GeneratedReferenceAsOfAssessmentError,
        match="AS_OF_PRECEDES_RECORD_EVALUATION",
    ):
        rights.assess_generated_reference_current_status_record_as_of(
            closure.record,
            closure.manifest,
            closure.chain_inputs,
            as_of="2026-08-29T03:59:59Z",
        )


def test_request_evaluation_upper_bound_is_exclusive() -> None:
    closure = _current_closure()
    evaluated_at = closure.request.request_valid_until
    results = _manual_category_results(
        request=closure.request,
        chain_inputs=closure.chain_inputs,
        evaluated_at=evaluated_at,
        unresolved_fork_category=None,
    )
    checker_basis = closure.instruction.checker_basis
    checker_action = _canonical_document(
        {
            "document_profile": (
                "sdc.generated-reference-current-status-decision-checker-action.v1"
            ),
            "action": "RECORDED_GENERATED_REFERENCE_CURRENT_STATUS_DECISION",
            "actor_identity_ref_sha256": _raw_sha256(
                closure.status_checker_identity_bytes
            ),
            "request_sha256": closure.request.request_sha256,
            "evaluated_at": evaluated_at,
            "category_results": [item.model_dump(mode="json") for item in results],
            "checker_basis": checker_basis,
            "status_valid_until": min(item.result_valid_until for item in results),
            "recorded_status": _manual_recorded_status(results),
        }
    )
    with pytest.raises(
        rights.GeneratedReferenceRightsCurrentStatusError,
        match="INSTRUCTION_CONTRACT_INVALID",
    ):
        rights.build_generated_reference_current_status_instruction(
            request=closure.request,
            chain_inputs=closure.chain_inputs,
            status_preparer_identity_bytes=closure.status_preparer_identity_bytes,
            status_preparer_action_bytes=closure.status_preparer_action_bytes,
            status_checker_identity_bytes=closure.status_checker_identity_bytes,
            status_checker_action_bytes=checker_action,
            evaluated_at=evaluated_at,
            checker_basis=checker_basis,
        )


@pytest.mark.parametrize(
    ("requested_at", "request_valid_until"),
    (
        ("2026-08-29T01:59:59Z", "2026-08-30T01:59:59Z"),
        ("2026-08-30T02:00:00Z", "2026-08-30T02:00:00Z"),
    ),
)
def test_request_time_must_be_inside_the_manifest_half_open_window(
    requested_at: str,
    request_valid_until: str,
) -> None:
    closure = _current_closure()
    assert closure.manifest.manifest_at == "2026-08-29T02:00:00Z"
    assert closure.manifest.manifest_valid_until == "2026-08-30T02:00:00Z"

    def outside_manifest(values: dict[str, object]) -> None:
        values["requested_at"] = requested_at
        values["request_valid_until"] = request_valid_until

    with pytest.raises(ValidationError, match="outside the Rights Manifest window"):
        rights.CreativeSampleGeneratedReferenceCurrentStatusRequestV1.model_validate(
            _rehash_contract_values(
                closure.request,
                outside_manifest,
                domain=rights.GENERATED_REFERENCE_CURRENT_STATUS_REQUEST_SHA256_DOMAIN,
                id_field="request_id",
                sha_field="request_sha256",
                stem="generated_reference_current_status_request_v1_",
            )
        )


def test_request_builder_preserves_manifest_window_failure_code() -> None:
    closure = _current_closure()
    with pytest.raises(rights.GeneratedReferenceRightsCurrentStatusError) as error:
        rights.build_generated_reference_current_status_request(
            subject_closure=closure.subject_closure,
            status_preparer_identity_bytes=closure.status_preparer_identity_bytes,
            status_preparer_action_bytes=closure.status_preparer_action_bytes,
            requested_at=closure.manifest.manifest_valid_until,
            target_observations=closure.observation_inputs,
            request_basis=closure.request.request_basis,
        )
    assert error.value.code == "REQUEST_CONTRACT_INVALID"


def test_observation_validity_window_is_at_most_86400_seconds() -> None:
    observation = _current_closure().observation_inputs[0].observation

    def valid_exact_upper_bound(values: dict[str, object]) -> None:
        values["valid_from"] = "2026-08-29T01:30:00Z"

    exact_values = _rehash_contract_values(
        observation,
        valid_exact_upper_bound,
        domain=rights.GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_OBSERVATION_SHA256_DOMAIN,
        id_field="observation_id",
        sha_field="observation_sha256",
        stem="generated_reference_current_status_source_observation_v1_",
    )
    exact = rights.CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1.model_validate(
        exact_values
    )
    assert exact.valid_until == "2026-08-30T01:30:00Z"

    def exceeds_upper_bound(values: dict[str, object]) -> None:
        values["valid_from"] = "2026-08-29T01:29:59Z"

    with pytest.raises(ValidationError, match="exceeds 86400 seconds"):
        rights.CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1.model_validate(
            _rehash_contract_values(
                observation,
                exceeds_upper_bound,
                domain=(
                    rights.GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_OBSERVATION_SHA256_DOMAIN
                ),
                id_field="observation_id",
                sha_field="observation_sha256",
                stem="generated_reference_current_status_source_observation_v1_",
            )
        )


def test_observation_builder_preserves_validity_window_failure_code() -> None:
    materials = _manifest_materials()
    subject_closure = rights.build_generated_reference_current_status_subject_closure(
        materials.manifest
    )
    source = cast(
        dict[str, object],
        cast(list[object], _status_source(materials.source_case)["observations"])[0],
    )
    with pytest.raises(rights.GeneratedReferenceRightsCurrentStatusError) as error:
        rights.build_generated_reference_current_status_source_observation(
            subject_closure=subject_closure,
            category=cast(Any, source["category"]),
            claim_value=cast(Any, source["claim_value"]),
            source_kind=cast(Any, source["source_kind"]),
            basis_code=cast(Any, source["basis_code"]),
            basis_note=cast(str, source["basis_note"]),
            source_identity_bytes=_canonical_document(source["source_reference"]),
            source_object_ref=cast(str, source["source_object_ref"]),
            source_object_bytes=_canonical_document(source["source_object"]),
            source_object_media_type=cast(str, source["source_object_media_type"]),
            source_event_at=cast(str, source["source_event_at"]),
            observed_at=cast(str, source["observed_at"]),
            valid_from="2026-08-29T01:29:59Z",
            valid_until=cast(str, source["valid_until"]),
            link_kind=cast(Any, source["link_kind"]),
        )
    assert error.value.code == "OBSERVATION_CONTRACT_INVALID"


@pytest.mark.parametrize(
    ("category", "claim_value", "expected_effect"),
    (
        ("HOLD_ACTIVE", "PRESENT", "ADVERSE_PRESENT"),
        ("HOLD_ACTIVE", "ABSENT_WITH_EVIDENCE", "ADVERSE_ABSENT"),
        ("RIGHTS_BASIS_CURRENT", "PRESENT", "POSITIVE_PRESENT"),
        ("RIGHTS_BASIS_CURRENT", "ABSENT_WITH_EVIDENCE", "POSITIVE_ABSENT"),
        ("HOLD_ACTIVE", "UNKNOWN", "INDETERMINATE"),
        ("HOLD_ACTIVE", "NOT_ASSESSED", "INDETERMINATE"),
        ("HOLD_ACTIVE", "CONFLICT", "INDETERMINATE"),
    ),
)
def test_category_result_claim_effect_matrix_is_complete_and_fail_closed(
    category: str,
    claim_value: str,
    expected_effect: str,
) -> None:
    result = next(
        item
        for item in _current_closure().instruction.category_results
        if item.category == category
    )
    valid_values = cast(dict[str, object], result.model_dump(mode="python"))
    valid_values["claim_value"] = claim_value
    valid_values["deterministic_effect"] = expected_effect
    admitted = rights.GeneratedReferenceCurrentStatusCategoryResultV1.model_validate(
        valid_values
    )
    assert admitted.deterministic_effect == expected_effect

    invalid_values = dict(valid_values)
    invalid_values["deterministic_effect"] = (
        "ADVERSE_PRESENT" if expected_effect != "ADVERSE_PRESENT" else "INDETERMINATE"
    )
    with pytest.raises(ValidationError, match="does not match category and claim_value"):
        rights.GeneratedReferenceCurrentStatusCategoryResultV1.model_validate(invalid_values)


def test_status_preparer_and_checker_aliases_fail_at_contract_and_builder_boundaries() -> None:
    closure = _current_closure()

    def alias_raw_role(values: dict[str, object]) -> None:
        values["status_checker_identity_ref_sha256"] = values[
            "status_preparer_identity_ref_sha256"
        ]

    def alias_raw_action(values: dict[str, object]) -> None:
        values["status_checker_action_sha256"] = values["status_preparer_action_sha256"]

    for alias in (alias_raw_role, alias_raw_action):
        with pytest.raises(ValidationError, match="identities/actions must be distinct"):
            rights.CreativeSampleGeneratedReferenceCurrentStatusInstructionV1.model_validate(
                _rehash_contract_values(
                    closure.instruction,
                    alias,
                    domain=rights.GENERATED_REFERENCE_CURRENT_STATUS_INSTRUCTION_SHA256_DOMAIN,
                    id_field="instruction_id",
                    sha_field="instruction_sha256",
                    stem="generated_reference_current_status_instruction_v1_",
                )
            )

    builder_aliases = (
        (
            closure.status_preparer_identity_bytes,
            closure.status_checker_action_bytes,
        ),
        (
            closure.status_checker_identity_bytes,
            closure.status_preparer_action_bytes,
        ),
    )
    for checker_identity_bytes, checker_action_bytes in builder_aliases:
        with pytest.raises(
            rights.GeneratedReferenceRightsCurrentStatusError,
            match="INSTRUCTION_CONTRACT_INVALID",
        ):
            rights.build_generated_reference_current_status_instruction(
                request=closure.request,
                chain_inputs=closure.chain_inputs,
                status_preparer_identity_bytes=closure.status_preparer_identity_bytes,
                status_preparer_action_bytes=closure.status_preparer_action_bytes,
                status_checker_identity_bytes=checker_identity_bytes,
                status_checker_action_bytes=checker_action_bytes,
                evaluated_at=closure.instruction.evaluated_at,
                checker_basis=closure.instruction.checker_basis,
            )


def test_all_five_claim_values_are_admitted_as_explicit_genesis_evidence() -> None:
    closure = _current_closure()
    source = next(
        cast(dict[str, object], item)
        for item in cast(
            list[object],
            _status_source(_manifest_materials().source_case)["observations"],
        )
        if cast(dict[str, object], item)["category"] == "HOLD_ACTIVE"
    )
    cases = (
        _ObservationOverride("PRESENT", "HOLD_IMPOSED"),
        _ObservationOverride("ABSENT_WITH_EVIDENCE", "HOLD_RELEASED"),
        _ObservationOverride("UNKNOWN", "INITIAL_STATUS_UNKNOWN"),
        _ObservationOverride("NOT_ASSESSED", "INITIAL_STATUS_NOT_ASSESSED"),
        _ObservationOverride("CONFLICT", "CONFLICT_IDENTIFIED"),
    )
    claims: list[str] = []
    for index, override in enumerate(cases):
        item = _build_observation_input(
            subject_closure=closure.subject_closure,
            source=source,
            override=override,
            suffix=f"claim-{index}",
        )
        target = rights.generated_reference_current_status_observation_ref(
            item.observation, ordinal=0
        )
        replay = rights.replay_generated_reference_current_status_chain(
            rights.GeneratedReferenceCurrentStatusExplicitChainInput(
                target_observation_refs=(target,), observation_inputs=(item,)
            )
        )
        claims.append(replay.observations[0].claim_value)
    assert tuple(claims) == (
        "PRESENT",
        "ABSENT_WITH_EVIDENCE",
        "UNKNOWN",
        "NOT_ASSESSED",
        "CONFLICT",
    )


@pytest.mark.parametrize(
    ("category", "override", "expected_status"),
    (
        (
            "REVOCATION_EFFECTIVE",
            _ObservationOverride("PRESENT", "SUPERSEDED"),
            "REVOKED",
        ),
        (
            "COMPLAINT_OPEN",
            _ObservationOverride("PRESENT", "COMPLAINT_RECEIVED"),
            "HELD",
        ),
        (
            "DISPUTE_OPEN",
            _ObservationOverride("PRESENT", "DISPUTE_OPENED"),
            "HELD",
        ),
        (
            "PROVIDER_TERMS_COMPATIBILITY_CURRENT",
            _ObservationOverride("ABSENT_WITH_EVIDENCE", "TERMS_CHANGED_OR_INCOMPATIBLE"),
            "HELD",
        ),
        (
            "RETENTION_DELETION_COMPLIANCE_CURRENT",
            _ObservationOverride(
                "ABSENT_WITH_EVIDENCE",
                "RETENTION_DELETION_UNRESOLVED_OR_NONCOMPLIANT",
            ),
            "HELD",
        ),
        (
            "TRAINING_USE_PROHIBITION_CURRENT",
            _ObservationOverride(
                "ABSENT_WITH_EVIDENCE",
                "TRAINING_UNRESOLVED_OR_VIOLATED",
            ),
            "HELD",
        ),
        (
            "REVOCATION_EFFECTIVE",
            _ObservationOverride(
                "PRESENT",
                "RETENTION_DELETION_VIOLATION_CONFIRMED",
                "RETENTION_DELETION_RECORD",
            ),
            "REVOKED",
        ),
        (
            "REVOCATION_EFFECTIVE",
            _ObservationOverride(
                "PRESENT",
                "TRAINING_VIOLATION_CONFIRMED",
                "TRAINING_USE_RECORD",
            ),
            "REVOKED",
        ),
    ),
)
def test_supersession_privacy_dispute_provider_retention_and_training_rules(
    category: str,
    override: _ObservationOverride,
    expected_status: str,
) -> None:
    closure = _build_status_closure({category: override})
    assert closure.decision.recorded_status == expected_status


def test_exactly_stale_evidence_is_not_assessed_and_does_not_become_structure_failure() -> None:
    category = "RIGHTS_BASIS_CURRENT"
    closure = _build_status_closure(
        {
            category: _ObservationOverride(
                "PRESENT",
                "RIGHTS_CONFIRMED",
                valid_until="2026-08-29T04:00:00Z",
            )
        }
    )
    result = next(
        item for item in closure.instruction.category_results if item.category == category
    )
    assert result.claim_value == "NOT_ASSESSED"
    assert result.deterministic_effect == "INDETERMINATE"
    assert result.relied_on_observation_refs == ()
    assert closure.decision.recorded_status == "INDETERMINATE"


def test_complete_unreconciled_fork_is_conflict_not_structural_failure() -> None:
    closure = _build_status_closure(unresolved_fork_category="HOLD_ACTIVE")
    result = closure.instruction.category_results[0]
    assert result.category == "HOLD_ACTIVE"
    assert result.claim_value == "CONFLICT"
    assert result.deterministic_effect == "INDETERMINATE"
    assert len(result.category_observation_refs) == 2
    assert len(result.relied_on_observation_refs) == 2
    assert closure.decision.recorded_status == "INDETERMINATE"


def test_missing_cycle_shaped_nonancestor_and_omitted_target_structures_fail() -> None:
    fork = _build_status_closure(unresolved_fork_category="HOLD_ACTIVE")
    fork_chain = next(item for item in fork.chain_inputs if len(item.observation_inputs) == 3)

    missing_ancestor = rights.GeneratedReferenceCurrentStatusExplicitChainInput(
        target_observation_refs=fork_chain.target_observation_refs,
        observation_inputs=fork_chain.observation_inputs[1:],
    )
    with pytest.raises(rights.GeneratedReferenceChainReplayError) as missing_error:
        rights.replay_generated_reference_current_status_chain(missing_ancestor)
    assert missing_error.value.code == "ORPHAN_REFERENCE"

    nonancestor_closed = rights.GeneratedReferenceCurrentStatusExplicitChainInput(
        target_observation_refs=fork_chain.target_observation_refs[:1],
        observation_inputs=fork_chain.observation_inputs,
    )
    with pytest.raises(rights.GeneratedReferenceChainReplayError) as nonancestor_error:
        rights.replay_generated_reference_current_status_chain(nonancestor_closed)
    assert nonancestor_error.value.code == "DISCONNECTED_GRAPH"

    missing_ref = fork_chain.target_observation_refs[0].model_copy(
        update={
            "observation_id": (
                "generated_reference_current_status_source_observation_v1_00000000000000000000"
            )
        }
    )
    with pytest.raises(rights.GeneratedReferenceChainReplayError) as target_error:
        rights.replay_generated_reference_current_status_chain(
            rights.GeneratedReferenceCurrentStatusExplicitChainInput(
                target_observation_refs=(missing_ref,),
                observation_inputs=fork_chain.observation_inputs,
            )
        )
    assert target_error.value.code == "REFERENCE_ANCHOR_MISMATCH"

    genesis = fork_chain.observation_inputs[0]
    self_head = rights.GeneratedReferenceCurrentStatusChainHeadRefV1(
        observation_id=genesis.observation.observation_id,
        observation_sha256=genesis.observation.observation_sha256,
        chain_sha256=rights.generated_reference_current_status_chain_sha256(genesis.observation),
    )
    tampered_link = rights.GeneratedReferenceCurrentStatusChainLinkV1(
        link_kind="SUCCESSOR",
        chain_scope_sha256=genesis.observation.chain_link.chain_scope_sha256,
        predecessor_heads=(self_head,),
    )
    cycle_shaped = rights.GeneratedReferenceCurrentStatusObservationInput(
        observation=genesis.observation.model_copy(update={"chain_link": tampered_link}),
        document_bytes=genesis.document_bytes,
    )
    with pytest.raises(rights.GeneratedReferenceChainReplayError) as cycle_error:
        rights.replay_generated_reference_current_status_chain(
            rights.GeneratedReferenceCurrentStatusExplicitChainInput(
                target_observation_refs=fork_chain.target_observation_refs[:1],
                observation_inputs=(cycle_shaped,),
            )
        )
    assert cycle_error.value.code == "OBSERVATION_CONTRACT_INVALID"

    with pytest.raises(rights.GeneratedReferenceChainCoverageError) as omitted_error:
        rights.cover_generated_reference_current_status_chains(
            fork.record,
            tuple(item for item in fork.chain_inputs if item is not fork_chain),
        )
    assert omitted_error.value.code == "REQUEST_OBSERVATION_NOT_COVERED"


def test_coverage_input_shape_codes_are_reachable_in_frozen_priority_order() -> None:
    closure = _current_closure()
    first = closure.chain_inputs[0]
    cases: tuple[tuple[Any, str], ...] = (
        ([], "CHAIN_COLLECTION_CONTRACT_INVALID"),
        ((), "CHAIN_COUNT_OUT_OF_RANGE"),
        ((object(),), "CHAIN_INPUT_CONTRACT_INVALID"),
        ((replace(first, target_observation_refs=()),), "TARGET_COUNT_OUT_OF_RANGE"),
        ((replace(first, observation_inputs=()),), "OBSERVATION_COUNT_OUT_OF_RANGE"),
    )
    for chain_inputs, expected_code in cases:
        with pytest.raises(rights.GeneratedReferenceChainCoverageError) as error:
            rights.cover_generated_reference_current_status_chains(
                closure.record, cast(Any, chain_inputs)
            )
        assert error.value.code == expected_code


def test_coverage_request_target_error_precedence_is_stable() -> None:
    closure = _current_closure()
    first, second, *tail = closure.chain_inputs
    first_target = first.target_observation_refs[0]
    second_target = second.target_observation_refs[0]
    anchored_wrong = second_target.model_copy(update={"observation_sha256": "0" * 64})
    unknown = second_target.model_copy(
        update={
            "observation_id": (
                "generated_reference_current_status_source_observation_v1_00000000000000000000"
            )
        }
    )
    cases = (
        (
            (
                replace(first, target_observation_refs=(first_target, first_target)),
                replace(second, target_observation_refs=(anchored_wrong,)),
                *tail,
            ),
            "REQUEST_TARGET_COVERED_MULTIPLE_TIMES",
        ),
        (
            (
                first,
                replace(second, target_observation_refs=(anchored_wrong, unknown)),
                *tail,
            ),
            "REQUEST_TARGET_ANCHOR_MISMATCH",
        ),
        (
            (
                first,
                replace(second, target_observation_refs=(unknown,)),
                *tail,
            ),
            "REQUEST_TARGET_NOT_IN_RECORD",
        ),
    )
    for chain_inputs, expected_code in cases:
        with pytest.raises(rights.GeneratedReferenceChainCoverageError) as error:
            rights.cover_generated_reference_current_status_chains(
                closure.record, chain_inputs
            )
        assert error.value.code == expected_code


def test_each_chain_target_set_must_preserve_exact_request_anchor_order() -> None:
    closure = _build_status_closure(unresolved_fork_category="HOLD_ACTIVE")
    fork_chain = next(
        item for item in closure.chain_inputs if len(item.target_observation_refs) == 2
    )
    reversed_chain = replace(
        fork_chain,
        target_observation_refs=tuple(reversed(fork_chain.target_observation_refs)),
    )
    chain_inputs = tuple(
        reversed_chain if item is fork_chain else item for item in closure.chain_inputs
    )
    with pytest.raises(rights.GeneratedReferenceChainCoverageError) as error:
        rights.cover_generated_reference_current_status_chains(closure.record, chain_inputs)
    assert error.value.code == "CHAIN_TARGET_SET_MISMATCH"


def test_request_target_anchor_compares_the_complete_typed_reference() -> None:
    closure = _current_closure()
    selected = closure.chain_inputs[0]
    target = selected.target_observation_refs[0]
    ordinal_only_drift = target.model_copy(update={"ordinal": target.ordinal + 1})
    changed = replace(selected, target_observation_refs=(ordinal_only_drift,))
    chain_inputs = tuple(
        changed if item is selected else item for item in closure.chain_inputs
    )
    with pytest.raises(rights.GeneratedReferenceChainCoverageError) as error:
        rights.cover_generated_reference_current_status_chains(closure.record, chain_inputs)
    assert error.value.code == "REQUEST_TARGET_ANCHOR_MISMATCH"


def test_coverage_defensively_rejects_internal_replay_result_with_unresolved_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closure = _current_closure()
    selected = closure.chain_inputs[0]
    original_replay = rights.replay_generated_reference_current_status_chain

    def omit_resolved_target(
        chain_input: rights.GeneratedReferenceCurrentStatusExplicitChainInput,
    ) -> rights.GeneratedReferenceCurrentStatusChainReplayResult:
        result = original_replay(chain_input)
        if chain_input is selected:
            return replace(result, observations=())
        return result

    monkeypatch.setattr(
        rights,
        "replay_generated_reference_current_status_chain",
        omit_resolved_target,
    )
    with pytest.raises(rights.GeneratedReferenceChainCoverageError) as error:
        rights.cover_generated_reference_current_status_chains(
            closure.record, closure.chain_inputs
        )
    assert error.value.code == "REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN"


def test_coverage_defensively_rejects_internal_replay_result_with_unrelated_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closure = _current_closure()
    selected = next(
        item
        for item in closure.chain_inputs
        if item.target_observation_refs[0].category == "HOLD_ACTIVE"
    )
    fork = _build_status_closure(unresolved_fork_category="HOLD_ACTIVE")
    extra = next(
        observation_input.observation
        for chain in fork.chain_inputs
        if len(chain.observation_inputs) == 3
        for observation_input in chain.observation_inputs[1:2]
    )
    original_replay = rights.replay_generated_reference_current_status_chain

    def inject_unrelated_support(
        chain_input: rights.GeneratedReferenceCurrentStatusExplicitChainInput,
    ) -> rights.GeneratedReferenceCurrentStatusChainReplayResult:
        result = original_replay(chain_input)
        if chain_input is selected:
            return replace(result, observations=(*result.observations, extra))
        return result

    monkeypatch.setattr(
        rights,
        "replay_generated_reference_current_status_chain",
        inject_unrelated_support,
    )
    with pytest.raises(rights.GeneratedReferenceChainCoverageError) as error:
        rights.cover_generated_reference_current_status_chains(
            closure.record, closure.chain_inputs
        )
    assert error.value.code == "UNRELATED_SUPPORT_OBSERVATION"


def test_public_chain_failure_preserves_nested_replay_code() -> None:
    closure = _current_closure()
    selected = next(
        item
        for item in closure.chain_inputs
        if item.target_observation_refs[0].category == "HOLD_ACTIVE"
    )
    fork = _build_status_closure(unresolved_fork_category="HOLD_ACTIVE")
    unrelated_input = next(
        observation_input
        for chain in fork.chain_inputs
        if len(chain.observation_inputs) == 3
        for observation_input in chain.observation_inputs[1:2]
    )
    changed = replace(
        selected,
        observation_inputs=(*selected.observation_inputs, unrelated_input),
    )
    chain_inputs = tuple(
        changed if item is selected else item for item in closure.chain_inputs
    )
    with pytest.raises(rights.GeneratedReferenceChainCoverageError) as error:
        rights.cover_generated_reference_current_status_chains(closure.record, chain_inputs)
    assert error.value.code == "CHAIN_REPLAY_FAILED"
    assert error.value.replay_code == "DISCONNECTED_GRAPH"


@pytest.mark.parametrize(
    ("field_name", "replacement_value"),
    (
        ("status_preparer_identity_ref_sha256", "1" * 64),
        ("status_preparer_action_sha256", "2" * 64),
        ("requested_at", "2026-08-29T03:00:01Z"),
        ("request_valid_until", "2026-08-30T01:59:59Z"),
    ),
)
def test_record_repeats_the_exact_request_preparer_and_time_closure(
    field_name: str,
    replacement_value: str,
) -> None:
    closure = _current_closure()

    def mutate_instruction(values: dict[str, object]) -> None:
        values[field_name] = replacement_value

    instruction = (
        rights.CreativeSampleGeneratedReferenceCurrentStatusInstructionV1.model_validate(
            _rehash_contract_values(
                closure.instruction,
                mutate_instruction,
                domain=rights.GENERATED_REFERENCE_CURRENT_STATUS_INSTRUCTION_SHA256_DOMAIN,
                id_field="instruction_id",
                sha_field="instruction_sha256",
                stem="generated_reference_current_status_instruction_v1_",
            )
        )
    )

    def replace_instruction(values: dict[str, object]) -> None:
        values["instruction"] = instruction.model_dump(mode="python")

    with pytest.raises(
        ValidationError,
        match="does not repeat the exact Request Preparer/time closure",
    ):
        rights.CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1.model_validate(
            _rehash_contract_values(
                closure.record,
                replace_instruction,
                domain=rights.GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_RECORD_SHA256_DOMAIN,
                id_field="record_id",
                sha_field="record_sha256",
                stem="generated_reference_current_status_evidence_record_v1_",
            )
        )


def test_record_closes_instruction_evaluation_window_and_decision_evaluation_time() -> None:
    closure = _current_closure()

    def instruction_after_request(values: dict[str, object]) -> None:
        values["evaluated_at"] = closure.request.request_valid_until

    instruction = (
        rights.CreativeSampleGeneratedReferenceCurrentStatusInstructionV1.model_validate(
            _rehash_contract_values(
                closure.instruction,
                instruction_after_request,
                domain=rights.GENERATED_REFERENCE_CURRENT_STATUS_INSTRUCTION_SHA256_DOMAIN,
                id_field="instruction_id",
                sha_field="instruction_sha256",
                stem="generated_reference_current_status_instruction_v1_",
            )
        )
    )

    def replace_instruction(values: dict[str, object]) -> None:
        values["instruction"] = instruction.model_dump(mode="python")

    with pytest.raises(ValidationError, match="outside the embedded Request window"):
        rights.CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1.model_validate(
            _rehash_contract_values(
                closure.record,
                replace_instruction,
                domain=rights.GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_RECORD_SHA256_DOMAIN,
                id_field="record_id",
                sha_field="record_sha256",
                stem="generated_reference_current_status_evidence_record_v1_",
            )
        )

    def decision_time_drift(values: dict[str, object]) -> None:
        values["evaluated_at"] = "2026-08-29T04:00:01Z"
        values["decision_at"] = "2026-08-29T04:00:01Z"

    decision = rights.CreativeSampleGeneratedReferenceCurrentStatusDecisionV1.model_validate(
        _rehash_contract_values(
            closure.decision,
            decision_time_drift,
            domain=rights.GENERATED_REFERENCE_CURRENT_STATUS_DECISION_SHA256_DOMAIN,
            id_field="decision_id",
            sha_field="decision_sha256",
            stem="generated_reference_current_status_decision_v1_",
        )
    )

    def replace_decision(values: dict[str, object]) -> None:
        values["decision"] = decision.model_dump(mode="python")

    with pytest.raises(
        ValidationError,
        match="Decision evaluated_at does not equal embedded Instruction evaluated_at",
    ):
        rights.CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1.model_validate(
            _rehash_contract_values(
                closure.record,
                replace_decision,
                domain=rights.GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_RECORD_SHA256_DOMAIN,
                id_field="record_id",
                sha_field="record_sha256",
                stem="generated_reference_current_status_evidence_record_v1_",
            )
        )


def test_receipt_parsing_is_not_replay_and_full_replay_is_mandatory_for_verification() -> None:
    closure = _current_closure()
    process = rights.process_generated_reference_current_status_record_as_of_assessment(
        closure.record,
        closure.manifest,
        closure.chain_inputs,
        as_of="2026-08-29T05:00:00Z",
    )
    raw = rights.generated_reference_contract_document_bytes(process.receipt)
    receipt_type = (
        rights.CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1
    )
    parsed = receipt_type.model_validate_json(raw)
    assert parsed == process.receipt
    incomplete_replay_inputs: tuple[dict[str, object], ...] = (
        {},
        {"record": closure.record},
        {"manifest": closure.manifest},
        {"chain_inputs": closure.chain_inputs},
        {"record": closure.record, "manifest": closure.manifest},
        {"record": closure.record, "chain_inputs": closure.chain_inputs},
        {"manifest": closure.manifest, "chain_inputs": closure.chain_inputs},
    )
    for replay_inputs in incomplete_replay_inputs:
        with pytest.raises(rights.GeneratedReferenceReceiptError) as replay_input_error:
            rights.verify_generated_reference_current_status_record_as_of_assessment_receipt(
                parsed, **cast(Any, replay_inputs)
            )
        assert replay_input_error.value.code == "RECEIPT_REPLAY_MISMATCH"
    assert rights.verify_generated_reference_current_status_record_as_of_assessment_receipt(
        parsed,
        record=closure.record,
        manifest=closure.manifest,
        chain_inputs=closure.chain_inputs,
    ) == parsed
    assert parsed.historical_assessment_only is True
    assert parsed.present_currentness_asserted is False


def test_receipt_requires_untampered_same_call_assessment_and_accepts_expiry_bounds() -> None:
    closure = _current_closure()
    process = rights.process_generated_reference_current_status_record_as_of_assessment(
        closure.record,
        closure.manifest,
        closure.chain_inputs,
        as_of="2026-08-29T05:00:00Z",
    )
    copied_and_tampered = replace(process.assessment, as_of_status="REVOKED")
    with pytest.raises(rights.GeneratedReferenceReceiptError) as assessment_error:
        rights.build_generated_reference_current_status_record_as_of_assessment_receipt(
            cast(Any, copied_and_tampered)
        )
    assert assessment_error.value.code == "ASSESSMENT_RESULT_INCONSISTENT"

    for identical_copy in (
        replace(process.assessment),
        copy.copy(process.assessment),
        copy.deepcopy(process.assessment),
    ):
        with pytest.raises(rights.GeneratedReferenceReceiptError) as copy_error:
            rights.build_generated_reference_current_status_record_as_of_assessment_receipt(
                identical_copy
            )
        assert copy_error.value.code == "ASSESSMENT_RESULT_INCONSISTENT"

    for exact_upper_bound in (
        closure.decision.status_valid_until,
        closure.manifest.manifest_valid_until,
    ):
        expired = rights.process_generated_reference_current_status_record_as_of_assessment(
            closure.record,
            closure.manifest,
            closure.chain_inputs,
            as_of=exact_upper_bound,
        )
        assert expired.receipt.as_of == exact_upper_bound
        assert expired.receipt.as_of_status == "EXPIRED"
        assert rights.verify_generated_reference_current_status_record_as_of_assessment_receipt(
            expired.receipt,
            record=closure.record,
            manifest=closure.manifest,
            chain_inputs=closure.chain_inputs,
        ) == expired.receipt


def test_every_formal_projection_hashes_independently_mutates_and_excludes_own_identity() -> None:
    closure = _current_closure()
    process = rights.process_generated_reference_current_status_record_as_of_assessment(
        closure.record,
        closure.manifest,
        closure.chain_inputs,
        as_of="2026-08-29T05:00:00Z",
    )
    observation = closure.observation_inputs[0].observation
    cases: tuple[tuple[BaseModel, Any, Any, bytes, tuple[str, ...]], ...] = (
        (
            closure.manifest,
            rights.creative_sample_generated_reference_rights_manifest_projection,
            rights.creative_sample_generated_reference_rights_manifest_sha256,
            rights.GENERATED_REFERENCE_RIGHTS_MANIFEST_SHA256_DOMAIN,
            ("manifest_id", "manifest_sha256"),
        ),
        (
            closure.subject_closure,
            rights.generated_reference_current_status_subject_closure_projection,
            rights.generated_reference_current_status_subject_closure_sha256,
            rights.GENERATED_REFERENCE_CURRENT_STATUS_SUBJECT_CLOSURE_SHA256_DOMAIN,
            ("closure_id", "closure_sha256"),
        ),
        (
            observation,
            rights.creative_sample_generated_reference_current_status_source_observation_projection,
            rights.creative_sample_generated_reference_current_status_source_observation_sha256,
            rights.GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_OBSERVATION_SHA256_DOMAIN,
            ("observation_id", "observation_sha256"),
        ),
        (
            closure.request,
            rights.creative_sample_generated_reference_current_status_request_projection,
            rights.creative_sample_generated_reference_current_status_request_sha256,
            rights.GENERATED_REFERENCE_CURRENT_STATUS_REQUEST_SHA256_DOMAIN,
            ("request_id", "request_sha256"),
        ),
        (
            closure.instruction,
            rights.creative_sample_generated_reference_current_status_instruction_projection,
            rights.creative_sample_generated_reference_current_status_instruction_sha256,
            rights.GENERATED_REFERENCE_CURRENT_STATUS_INSTRUCTION_SHA256_DOMAIN,
            ("instruction_id", "instruction_sha256"),
        ),
        (
            closure.decision,
            rights.creative_sample_generated_reference_current_status_decision_projection,
            rights.creative_sample_generated_reference_current_status_decision_sha256,
            rights.GENERATED_REFERENCE_CURRENT_STATUS_DECISION_SHA256_DOMAIN,
            ("decision_id", "decision_sha256"),
        ),
        (
            closure.record,
            rights.creative_sample_generated_reference_current_status_evidence_record_projection,
            rights.creative_sample_generated_reference_current_status_evidence_record_sha256,
            rights.GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_RECORD_SHA256_DOMAIN,
            ("record_id", "record_sha256"),
        ),
        (
            process.receipt,
            rights.creative_sample_generated_reference_current_status_record_as_of_assessment_receipt_projection,
            rights.creative_sample_generated_reference_current_status_record_as_of_assessment_receipt_sha256,
            rights.GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_SHA256_DOMAIN,
            ("receipt_id", "receipt_sha256"),
        ),
    )
    for value, projection_function, hash_function, domain, self_fields in cases:
        projection = cast(dict[str, object], projection_function(value))
        expected = cast(str, hash_function(value))
        assert _semantic_sha256(domain, projection) == expected
        assert not set(self_fields) & set(projection)
        assert len({_semantic_sha256(candidate, projection) for candidate in DOMAINS}) == 17
        for path in _semantic_leaf_paths(projection):
            assert _semantic_sha256(domain, _mutate_semantic_leaf(projection, path)) != expected


def test_all_portable_documents_retain_zero_authority_even_when_status_is_current() -> None:
    closure = _current_closure()
    receipt = rights.process_generated_reference_current_status_record_as_of_assessment(
        closure.record,
        closure.manifest,
        closure.chain_inputs,
        as_of="2026-08-29T05:00:00Z",
    ).receipt
    documents: tuple[BaseModel, ...] = (
        closure.manifest,
        *(item.observation for item in closure.observation_inputs),
        closure.request,
        closure.instruction,
        closure.decision,
        closure.record,
        receipt,
    )
    for document in documents:
        _assert_zero_authority(document)


def test_candidate_is_immutable_and_outputs_do_not_cross_formal_boundaries() -> None:
    materials = _manifest_materials()
    candidate = materials.upstream.candidate
    candidate_before = candidate.model_dump(mode="python")
    candidate_bytes_before = _canonical_document(candidate.model_dump(mode="json"))
    closure = _current_closure()
    receipt = rights.process_generated_reference_current_status_record_as_of_assessment(
        closure.record,
        closure.manifest,
        closure.chain_inputs,
        as_of="2026-08-29T05:00:00Z",
    ).receipt

    assert candidate.candidate_state == "CAPTURED_UNQUALIFIED"
    with pytest.raises(ValidationError, match="frozen"):
        cast(Any, candidate).candidate_state = "QUALIFIED"
    assert candidate.model_dump(mode="python") == candidate_before
    assert _canonical_document(candidate.model_dump(mode="json")) == candidate_bytes_before

    prohibited_consumers: tuple[type[BaseModel], ...] = (
        CharacterAssetVersion,
        CharacterBible,
        SceneAssetVersion,
        SceneBible,
        InputMaterial,
        ProviderRequest,
        GenerationJob,
        JobGraph,
    )
    status_outputs: tuple[BaseModel, ...] = (
        closure.manifest,
        *(item.observation for item in closure.observation_inputs),
        closure.request,
        closure.instruction,
        closure.decision,
        closure.record,
        receipt,
    )
    for value in (candidate, *status_outputs):
        for consumer in prohibited_consumers:
            assert not isinstance(value, consumer)
            with pytest.raises(ValidationError):
                consumer.model_validate(value.model_dump(mode="python"))


def test_frozen_policy_sizes_hashes_orders_and_five_value_algebra() -> None:
    manifest_projection = rights.generated_reference_rights_manifest_policy_projection()
    current_projection = rights.generated_reference_current_status_policy_projection()
    manifest_raw = _compact_json(manifest_projection)
    current_raw = _compact_json(current_projection)

    assert len(manifest_raw) == MANIFEST_POLICY_SIZE
    assert _raw_sha256(manifest_raw) == MANIFEST_POLICY_SHA256
    assert rights.GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_DOCUMENT_SHA256 == (
        MANIFEST_POLICY_SHA256
    )
    assert len(current_raw) == CURRENT_STATUS_POLICY_SIZE
    assert _raw_sha256(current_raw) == CURRENT_STATUS_POLICY_SHA256
    assert rights.GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256 == (
        CURRENT_STATUS_POLICY_SHA256
    )
    assert tuple(cast(list[object], current_projection["claim_values"])) == (
        "PRESENT",
        "ABSENT_WITH_EVIDENCE",
        "UNKNOWN",
        "NOT_ASSESSED",
        "CONFLICT",
    )
    assert (
        *cast(list[object], current_projection["adverse_category_order"]),
        *cast(list[object], current_projection["positive_category_order"]),
    ) == rights.CURRENT_STATUS_CATEGORY_ORDER
    assert len(rights.CURRENT_STATUS_CATEGORY_ORDER) == 9
    assert len(rights.MANIFEST_REVIEW_GATE_ORDER) == 11
    assert len(rights.MANIFEST_REVIEW_EVIDENCE_CATEGORY_ORDER) == 9
    assert len(rights.CURRENT_STATUS_LIMITATION_CODE_ORDER) == 7


def test_all_seventeen_domains_are_nul_terminated_distinct_and_non_aliasing() -> None:
    assert DOMAINS == (
        b"sdc:generated-reference-rights-manifest-review-payload:v1\0",
        b"sdc:generated-reference-rights-manifest:v1\0",
        b"sdc:generated-reference-current-status-subject-closure:v1\0",
        b"sdc:generated-reference-current-status-source-observation:v1\0",
        b"sdc:generated-reference-current-status-chain-scope:v1\0",
        b"sdc:generated-reference-current-status-chain:v1\0",
        b"sdc:generated-reference-current-status-observation-set:v1\0",
        b"sdc:generated-reference-current-status-request:v1\0",
        b"sdc:generated-reference-current-status-instruction:v1\0",
        b"sdc:generated-reference-current-status-decision:v1\0",
        b"sdc:generated-reference-current-status-evidence-record:v1\0",
        b"sdc:generated-reference-current-status-explicit-chain-set:v1\0",
        b"sdc:generated-reference-current-status-coverage-set:v1\0",
        b"sdc:generated-reference-current-status-joint-replay:v1\0",
        b"sdc:generated-reference-current-status-record-as-of-assessment:v1\0",
        b"sdc:generated-reference-current-status-record-as-of-assessment-provenance:v1\0",
        b"sdc:generated-reference-current-status-"
        b"record-as-of-assessment-receipt:v1\0",
    )
    assert len(DOMAINS) == 17
    assert len(set(DOMAINS)) == 17
    assert all(type(domain) is bytes and domain.endswith(b"\0") for domain in DOMAINS)

    projection = {"same": "projection", "ordinal": 1}
    digests = {_semantic_sha256(domain, projection) for domain in DOMAINS}
    assert len(digests) == 17


def test_all_seven_portable_types_freeze_the_same_twenty_one_zero_authority_fields() -> None:
    assert len(ZERO_AUTHORITY_FIELDS) == 21
    for model_type in FORMAL_ZERO_AUTHORITY_TYPES:
        assert set(ZERO_AUTHORITY_FIELDS) <= set(model_type.model_fields)
        schema = model_type.model_json_schema()
        properties = cast(dict[str, dict[str, object]], schema["properties"])
        for field_name, expected in ZERO_AUTHORITY_FIELDS.items():
            assert properties[field_name].get("const") == expected


def test_core_has_no_runtime_provider_network_persistence_or_dynamic_import_boundary() -> None:
    source = Path(rights.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    prohibited_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec", "compile", "__import__"}:
                prohibited_calls.append(node.func.id)

    assert prohibited_calls == []
    assert imports <= {
        "__future__",
        "collections.abc",
        "dataclasses",
        "datetime",
        "hashlib",
        "json",
        "pydantic",
        "re",
        "sdc.generated_reference_candidate",
        "sdc.visual_reference_prompt_compiler",
        "typing",
        "unicodedata",
    }
    assert not imports & {
        "asyncio",
        "asyncpg",
        "fastapi",
        "httpx",
        "os",
        "requests",
        "socket",
        "sqlalchemy",
        "subprocess",
        "temporalio",
        "urllib",
    }
    folded = source.casefold()
    for marker in (
        "os.environ",
        "getenv(",
        "datetime.now(",
        "datetime.utcnow(",
        "time.time(",
        "random.",
        "uuid4(",
        "assetversion",
        "inputmaterial",
        "providerrequest(",
        "from sdc.runtime",
    ):
        assert marker not in folded
