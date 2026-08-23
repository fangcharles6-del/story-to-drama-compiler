from __future__ import annotations

import ast
import hashlib
import inspect
import json
from dataclasses import dataclass
from typing import Any, cast

import pytest
from pydantic import ValidationError
from real_asset_v2_test_support import (
    CompleteClosure,
    digest,
    make_complete_closure,
)

import sdc.real_asset_fresh_status_evidence_v30 as fresh_status_module
from sdc.compiler import stable_id
from sdc.real_asset_fresh_status_evidence_v30 import (
    FRESH_STATUS_AUTHORING_INPUT_MAX_BYTES,
    FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256,
    FRESH_STATUS_JSON_MAX_DEPTH,
    FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS,
    FRESH_STATUS_MAX_OBSERVATIONS,
    FRESH_STATUS_MAX_RECONCILIATION_HEADS,
    FRESH_STATUS_MAX_WINDOW_SECONDS,
    FRESH_STATUS_RECORD_MAX_BYTES,
    FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES,
    FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE_DOCUMENT_SHA256,
    CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    CreativeSampleRealAssetFreshStatusInstructionV1,
    CreativeSampleRealAssetFreshStatusRequestV1,
    CreativeSampleRealAssetFreshStatusSourceObservationV1,
    FreshStatusBasisCodeV1,
    FreshStatusCategoryResultV1,
    FreshStatusChainHeadRefV1,
    FreshStatusChainLinkV1,
    FreshStatusClaimValueV1,
    FreshStatusObservationRefV1,
    FreshStatusSourceKindV1,
    FreshStatusSubjectClosureV1,
    RealAssetFreshStatusEvidenceV30Error,
    build_fresh_status_evidence_record_v1,
    build_fresh_status_instruction_v1,
    build_fresh_status_request_v1,
    build_fresh_status_source_observation_v1,
    build_fresh_status_subject_closure_v1,
    compile_fresh_status_decision_v1,
    derive_fresh_status_observation_chain_sha256_v1,
    extract_fresh_status_decision_v1,
    extract_fresh_status_instruction_v1,
    extract_fresh_status_request_v1,
    parse_fresh_status_decision_v1_json,
    parse_fresh_status_evidence_record_v1_json,
    parse_fresh_status_instruction_v1_json,
    parse_fresh_status_request_v1_json,
    parse_fresh_status_source_observation_v1_json,
    verify_fresh_status_evidence_record_closure_v1,
    verify_fresh_status_evidence_record_internal_v1,
    verify_fresh_status_source_observation_internal_v1,
    verify_fresh_status_source_observation_link_v1,
)
from sdc.real_asset_use_plan_v26 import (
    CreativeSampleRealAssetUsePlanV1,
    build_real_asset_use_plan_v1,
)
from sdc.real_asset_use_scope_review_v26 import (
    CreativeSampleRealAssetUseScopeReviewRecordV1,
    UseScopeGateResultV1,
    build_use_scope_review_instruction_v1,
    build_use_scope_review_record_v1,
    build_use_scope_review_request_v1,
)

USE_SCOPE_REQUESTED_AT = "2026-08-19T12:01:00Z"
USE_SCOPE_EVALUATED_AT = "2026-08-19T12:02:00Z"
SOURCE_EVENT_AT = "2026-08-20T00:00:00Z"
OBSERVED_AT = "2026-08-20T00:01:00Z"
VALID_FROM = "2026-08-20T00:00:00Z"
VALID_UNTIL = "2026-08-21T00:00:00Z"
FRESH_REQUESTED_AT = "2026-08-20T00:02:00Z"
FRESH_EVALUATED_AT = "2026-08-20T00:03:00Z"

CATEGORIES = (
    "HOLD_ACTIVE",
    "REVOCATION_EFFECTIVE",
    "COMPLAINT_OPEN",
    "DISPUTE_OPEN",
    "RIGHTS_BASIS_CURRENT",
    "IDENTITY_BINDING_CURRENT",
    "POLICY_COMPATIBILITY_CURRENT",
)
ADVERSE_CATEGORIES = frozenset(CATEGORIES[:4])
SOURCE_KINDS: tuple[FreshStatusSourceKindV1, ...] = (
    "RIGHTS_HOLDER_DECLARATION",
    "LICENSOR_DECLARATION",
    "INTERNAL_HOLD_RECORD",
    "REVOCATION_NOTICE",
    "COMPLAINT_RECORD",
    "DISPUTE_RECORD",
    "IDENTITY_BINDING_RECORD",
    "POLICY_EVALUATION_RECORD",
)
MANDATORY_LIMITATIONS = (
    "SOURCE_AUTHENTICITY_NOT_PROVEN",
    "SOURCE_COMPLETENESS_NOT_PROVEN",
    "CHAIN_COMPLETENESS_NOT_PROVEN",
    "REALITY_CURRENTNESS_NOT_PROVEN",
)
ALL_LIMITATIONS = (
    *MANDATORY_LIMITATIONS,
    "SCOPE_LIMITED_TO_DECLARED_SUBJECT",
    "TIME_WINDOW_LIMITED",
    "LEGAL_EFFECT_NOT_DETERMINED",
)


@dataclass(frozen=True)
class Upstream:
    closure: CompleteClosure
    use_plan: CreativeSampleRealAssetUsePlanV1
    use_scope_record: CreativeSampleRealAssetUseScopeReviewRecordV1
    subject_closure: FreshStatusSubjectClosureV1


@dataclass(frozen=True)
class FreshBundle:
    upstream: Upstream
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...]
    request: CreativeSampleRealAssetFreshStatusRequestV1
    instruction: CreativeSampleRealAssetFreshStatusInstructionV1
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _render(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _all_pass_gates() -> tuple[UseScopeGateResultV1, ...]:
    return tuple(
        UseScopeGateResultV1(gate=gate, approved=True)
        for gate in (
            "COPYRIGHT_USE_SCOPE",
            "LIKENESS_USE_SCOPE",
            "PRIVACY_USE_SCOPE",
            "TERRITORY_USE_SCOPE",
            "CONTENT_ROLE_USE_SCOPE",
            "OFFLINE_ONLY_RESTRICTIONS",
        )
    )


def _build_upstream() -> Upstream:
    closure = make_complete_closure()
    use_plan = build_real_asset_use_plan_v1(
        pack=closure.pack,
        evidence=closure.evidence,
        reviewer_a=closure.reviewer_a,
        reviewer_b=closure.reviewer_b,
        pair_check=closure.pair_check,
        qualification_request=closure.request,
        qualification_instruction=closure.instruction,
        qualification_decision=closure.decision,
        rights_manifest=closure.manifest,
    )
    review_request = build_use_scope_review_request_v1(
        use_plan=use_plan,
        maker_identity_ref_sha256=digest("fresh-v30-upstream-maker"),
        requested_at=USE_SCOPE_REQUESTED_AT,
        request_basis="合成用途计划进入独立用途范围评审。",
    )
    review_instruction = build_use_scope_review_instruction_v1(
        request=review_request,
        checker_identity_ref_sha256=digest("fresh-v30-upstream-checker"),
        evaluated_at=USE_SCOPE_EVALUATED_AT,
        gate_results=_all_pass_gates(),
        disposition="PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY",
        checker_basis="七类新鲜状态证据仍须另行形成，本次只闭合用途范围。",
    )
    use_scope_record = build_use_scope_review_record_v1(
        request=review_request,
        instruction=review_instruction,
    )
    subject_closure = build_fresh_status_subject_closure_v1(
        pack=closure.pack,
        rights_manifest=closure.manifest,
        use_plan=use_plan,
        use_scope_review_record=use_scope_record,
    )
    return Upstream(closure, use_plan, use_scope_record, subject_closure)


def _non_blocking_claim(category: str) -> FreshStatusClaimValueV1:
    return "ABSENT_WITH_EVIDENCE" if category in ADVERSE_CATEGORIES else "PRESENT"


def _observation(
    subject_closure: FreshStatusSubjectClosureV1,
    *,
    category: str,
    claim: FreshStatusClaimValueV1,
    label: str,
    source_kind: FreshStatusSourceKindV1 | None = None,
    source_identity_label: str | None = None,
    source_event_at: str = SOURCE_EVENT_AT,
    observed_at: str = OBSERVED_AT,
    valid_from: str = VALID_FROM,
    valid_until: str = VALID_UNTIL,
    basis_code: FreshStatusBasisCodeV1 | None = None,
    basis_note: str | None = None,
    limitation_codes: tuple[str, ...] = ALL_LIMITATIONS,
    chain_kind: str = "GENESIS",
    predecessor: CreativeSampleRealAssetFreshStatusSourceObservationV1 | None = None,
    reconciliation_heads: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...] = (),
) -> CreativeSampleRealAssetFreshStatusSourceObservationV1:
    category_index = CATEGORIES.index(category)
    determined_basis: dict[str, tuple[FreshStatusBasisCodeV1, FreshStatusBasisCodeV1]] = {
        "HOLD_ACTIVE": ("HOLD_IMPOSED", "HOLD_RELEASED"),
        "REVOCATION_EFFECTIVE": ("REVOCATION_ISSUED", "RIGHTS_REINSTATED"),
        "COMPLAINT_OPEN": ("COMPLAINT_RECEIVED", "COMPLAINT_RESOLVED"),
        "DISPUTE_OPEN": ("DISPUTE_OPENED", "DISPUTE_RESOLVED"),
        "RIGHTS_BASIS_CURRENT": (
            "RIGHTS_GRANTED_OR_RENEWED",
            "RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED",
        ),
        "IDENTITY_BINDING_CURRENT": (
            "IDENTITY_VERIFIED_OR_REBOUND",
            "IDENTITY_EXPIRED_REVOKED_OR_SUPERSEDED",
        ),
        "POLICY_COMPATIBILITY_CURRENT": (
            "POLICY_REVIEWED_COMPATIBLE",
            "POLICY_CHANGED_OR_INCOMPATIBLE",
        ),
    }
    if basis_code is None:
        if chain_kind == "GENESIS":
            basis_code = (
                determined_basis[category][0]
                if claim == "PRESENT"
                else determined_basis[category][1]
                if claim == "ABSENT_WITH_EVIDENCE"
                else "INITIAL_STATUS_UNKNOWN"
                if claim == "UNKNOWN"
                else "INITIAL_STATUS_NOT_ASSESSED"
                if claim == "NOT_ASSESSED"
                else "CONFLICT_IDENTIFIED"
            )
        elif chain_kind == "RECONCILIATION":
            basis_code = "CONFLICT_IDENTIFIED" if claim == "CONFLICT" else "CONFLICT_RECONCILED"
        elif predecessor is not None:
            if claim == "CONFLICT":
                basis_code = "CONFLICT_IDENTIFIED"
            elif claim == "PRESENT":
                basis_code = (
                    "STATUS_RECONFIRMED"
                    if predecessor.claim_value == "PRESENT"
                    else determined_basis[category][0]
                )
            elif claim == "ABSENT_WITH_EVIDENCE":
                basis_code = (
                    "STATUS_RECONFIRMED"
                    if predecessor.claim_value == "ABSENT_WITH_EVIDENCE"
                    else determined_basis[category][1]
                )
            else:
                basis_code = (
                    "INITIAL_STATUS_UNKNOWN"
                    if predecessor.claim_value == "NOT_ASSESSED"
                    else "STATUS_BECAME_UNKNOWN"
                )
        else:
            raise AssertionError("SUCCESSOR test helper requires a predecessor")
    return build_fresh_status_source_observation_v1(
        subject_closure=subject_closure,
        status_category=cast(Any, category),
        claim_value=claim,
        source_kind=source_kind or SOURCE_KINDS[category_index],
        source_identity_ref_sha256=digest(
            f"fresh-v30-source-identity:{source_identity_label or label}"
        ),
        source_object_sha256=digest(f"fresh-v30-source-object:{label}"),
        source_object_size_bytes=10_000 + len(label),
        source_media_type="application/json",
        source_event_at=source_event_at,
        observed_at=observed_at,
        valid_from=valid_from,
        valid_until=valid_until,
        basis_code=basis_code,
        basis_note=basis_note or f"合成状态依据：{label}。",
        limitation_codes=cast(Any, limitation_codes),
        chain_kind=cast(Any, chain_kind),
        predecessor=predecessor,
        reconciliation_heads=reconciliation_heads,
    )


def _observations_for_claims(
    upstream: Upstream,
    claims: dict[str, FreshStatusClaimValueV1] | None = None,
) -> tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...]:
    claims = claims or {}
    return tuple(
        _observation(
            upstream.subject_closure,
            category=category,
            claim=claims.get(category, _non_blocking_claim(category)),
            label=f"category-{index}-{claims.get(category, 'default')}",
        )
        for index, category in enumerate(CATEGORIES)
    )


def _build_bundle(
    upstream: Upstream,
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
    *,
    evaluated_at: str = FRESH_EVALUATED_AT,
    preparer_identity: str | None = None,
    checker_identity: str | None = None,
) -> FreshBundle:
    request = build_fresh_status_request_v1(
        subject_closure=upstream.subject_closure,
        preparer_identity_ref_sha256=preparer_identity or digest("fresh-v30-preparer"),
        requested_at=FRESH_REQUESTED_AT,
        request_basis="请求评审显式有限集合中的合成新鲜状态证据。",
        observations=observations,
    )
    instruction = build_fresh_status_instruction_v1(
        request=request,
        observations=observations,
        checker_identity_ref_sha256=checker_identity or digest("fresh-v30-checker"),
        evaluated_at=evaluated_at,
        checker_basis="仅评审所提供合成集合及明确半开时间窗。",
    )
    record = build_fresh_status_evidence_record_v1(
        request=request,
        instruction=instruction,
    )
    return FreshBundle(upstream, observations, request, instruction, record)


@pytest.fixture(scope="module")
def upstream() -> Upstream:
    return _build_upstream()


@pytest.fixture(scope="module")
def bundle(upstream: Upstream) -> FreshBundle:
    return _build_bundle(upstream, _observations_for_claims(upstream))


def test_complete_seven_category_non_blocking_record_is_deterministic(
    bundle: FreshBundle,
) -> None:
    second = _build_bundle(bundle.upstream, bundle.observations)
    assert second == bundle
    assert bundle.record.decision.disposition == (
        "NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET"
    )
    assert tuple(item.status_category for item in bundle.instruction.category_results) == CATEGORIES
    assert all(
        item.assessment_effect == "NON_BLOCKING_WITHIN_BOUND_WINDOW"
        for item in bundle.instruction.category_results
    )
    assert bundle.record.decision.blocking_categories == ()
    assert bundle.record.decision.indeterminate_categories == ()
    assert bundle.record.decision.status_valid_until == VALID_UNTIL


def test_modules_have_independent_sha_extractors_and_exact_parsers(bundle: FreshBundle) -> None:
    record = bundle.record
    assert record.request_sha256 == _sha(record.request)
    assert record.instruction_sha256 == _sha(record.instruction)
    assert record.decision_sha256 == _sha(record.decision)
    assert record.instruction.request_sha256 == record.request_sha256
    assert record.decision.instruction_sha256 == record.instruction_sha256

    request, request_raw = extract_fresh_status_request_v1(record)
    instruction, instruction_raw = extract_fresh_status_instruction_v1(record)
    decision, decision_raw = extract_fresh_status_decision_v1(record)
    assert request == record.request
    assert instruction == record.instruction
    assert decision == record.decision
    assert parse_fresh_status_request_v1_json(request_raw) == request
    assert parse_fresh_status_instruction_v1_json(instruction_raw) == instruction
    assert parse_fresh_status_decision_v1_json(decision_raw) == decision
    assert parse_fresh_status_evidence_record_v1_json(_canonical(record)) == record
    assert (
        parse_fresh_status_source_observation_v1_json(_canonical(bundle.observations[0]))
        == bundle.observations[0]
    )


def test_all_artifacts_are_immutable_and_zero_authority(bundle: FreshBundle) -> None:
    artifacts = (
        *bundle.observations,
        bundle.request,
        bundle.instruction,
        bundle.record.decision,
        bundle.record,
    )
    false_fields = (
        "generation_authorized",
        "execution_authorized",
        "publication_authorized",
        "remote_processing_allowed",
        "retention_allowed",
        "training_allowed",
        "publication_allowed",
        "automated_execution_allowed",
    )
    zero_fields = (
        "authorized_attempts",
        "authorized_cost_cny",
        "posts_allowed",
        "provider_requests",
    )
    for artifact in artifacts:
        assert artifact.current_gate == "HUMAN_GATE"
        assert artifact.provider_state == "NOT_AUTHORIZED"
        assert artifact.evidence_scope == "EXPLICIT_FINITE_BOUND_SET_ONLY"
        assert artifact.usage_restriction == "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
        assert all(getattr(artifact, field) is False for field in false_fields)
        assert all(getattr(artifact, field) == 0 for field in zero_fields)
        with pytest.raises(ValidationError):
            artifact.execution_authorized = True  # type: ignore[misc]


@pytest.mark.parametrize(
    ("claim_overrides", "expected"),
    (
        ({}, "NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET"),
        ({"HOLD_ACTIVE": "PRESENT"}, "BLOCKING_STATUS_RECORDED"),
        (
            {"POLICY_COMPATIBILITY_CURRENT": "UNKNOWN"},
            "INSUFFICIENT_OR_CONFLICTING_EVIDENCE",
        ),
    ),
)
def test_three_dispositions_are_compiler_derived(
    upstream: Upstream,
    claim_overrides: dict[str, FreshStatusClaimValueV1],
    expected: str,
) -> None:
    observations = _observations_for_claims(upstream, claim_overrides)
    built = _build_bundle(upstream, observations)
    assert built.record.decision.disposition == expected
    assert (
        compile_fresh_status_decision_v1(
            request=built.request,
            instruction=built.instruction,
        )
        == built.record.decision
    )


def test_conflicting_usable_claims_are_indeterminate(upstream: Upstream) -> None:
    observations = list(_observations_for_claims(upstream))
    observations.append(
        _observation(
            upstream.subject_closure,
            category="HOLD_ACTIVE",
            claim="PRESENT",
            label="conflicting-hold",
        )
    )
    built = _build_bundle(upstream, tuple(observations))
    result = built.instruction.category_results[0]
    assert result.claim_value == "CONFLICT"
    assert result.assessment_effect == "INDETERMINATE"
    assert built.record.decision.disposition == "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"


@pytest.mark.parametrize(
    "parser,artifact",
    (
        (parse_fresh_status_source_observation_v1_json, "observation"),
        (parse_fresh_status_request_v1_json, "request"),
        (parse_fresh_status_instruction_v1_json, "instruction"),
        (parse_fresh_status_decision_v1_json, "decision"),
        (parse_fresh_status_evidence_record_v1_json, "record"),
    ),
)
def test_all_parsers_require_exact_canonical_bytes(
    bundle: FreshBundle,
    parser: Any,
    artifact: str,
) -> None:
    value = {
        "observation": bundle.observations[0],
        "request": bundle.request,
        "instruction": bundle.instruction,
        "decision": bundle.record.decision,
        "record": bundle.record,
    }[artifact]
    raw = _canonical(value)
    assert parser(raw) == value
    for changed in (raw.rstrip(b"\n"), raw.replace(b"\n", b"\r\n"), b"\xef\xbb\xbf" + raw):
        with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
            parser(changed)


def test_parser_rejects_duplicate_nonfinite_extra_and_non_nfc(bundle: FreshBundle) -> None:
    raw = _canonical(bundle.request)
    duplicate = (
        "{"
        + json.dumps("request_id")
        + ":"
        + json.dumps(bundle.request.request_id)
        + ","
        + raw.decode("utf-8")[1:]
    ).encode("utf-8")
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        parse_fresh_status_request_v1_json(duplicate)

    for constant in (b"NaN", b"Infinity"):
        changed = raw.replace(b'"authorized_cost_cny": 0', b'"authorized_cost_cny": ' + constant)
        assert changed != raw
        with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
            parse_fresh_status_request_v1_json(changed)

    extra = bundle.request.model_dump(mode="json")
    extra["unexpected"] = True
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        parse_fresh_status_request_v1_json(_render(extra))

    non_nfc = bundle.request.model_dump(mode="json")
    non_nfc["request_basis"] = "Cafe\u0301"
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        parse_fresh_status_request_v1_json(_render(non_nfc))


def _nested_array(levels: int) -> object:
    value: object = 0
    for _ in range(levels):
        value = [value]
    return value


def test_json_depth_32_is_admitted_before_contract_check_and_33_fails_depth(
    bundle: FreshBundle,
) -> None:
    depth_32 = bundle.request.model_dump(mode="json")
    depth_32["unexpected"] = _nested_array(31)
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error) as at_limit:
        parse_fresh_status_request_v1_json(_render(depth_32))
    assert "depth 32" not in str(at_limit.value)

    depth_33 = bundle.request.model_dump(mode="json")
    depth_33["unexpected"] = _nested_array(32)
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="depth 32"):
        parse_fresh_status_request_v1_json(_render(depth_33))


def test_parser_byte_precheck_fails_before_json_decode() -> None:
    assert FRESH_STATUS_AUTHORING_INPUT_MAX_BYTES == 65_536
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="bounded BOM-free"):
        parse_fresh_status_request_v1_json(b" " * (FRESH_STATUS_RECORD_MAX_BYTES + 1))
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="bounded BOM-free"):
        parse_fresh_status_source_observation_v1_json(b"")


def test_models_are_strict_about_exact_scalar_types(bundle: FreshBundle) -> None:
    observation = bundle.observations[0]
    for replacement in (True, 1.0, "1"):
        payload = observation.model_dump(mode="python")
        payload["source_object_size_bytes"] = replacement
        with pytest.raises(ValidationError):
            CreativeSampleRealAssetFreshStatusSourceObservationV1.model_validate(
                payload, strict=True
            )

    for field, replacement in (
        ("execution_authorized", 0),
        ("posts_allowed", False),
        ("provider_requests", 0.0),
    ):
        payload = bundle.request.model_dump(mode="python")
        payload[field] = replacement
        with pytest.raises(ValidationError):
            CreativeSampleRealAssetFreshStatusRequestV1.model_validate(payload, strict=True)

    payload = bundle.request.model_dump(mode="python")
    payload["observation_refs"] = list(payload["observation_refs"])
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetFreshStatusRequestV1.model_validate(payload, strict=True)


def test_time_windows_are_half_open_and_capped_at_86400(upstream: Upstream) -> None:
    exact = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="ABSENT_WITH_EVIDENCE",
        label="exact-86400",
        valid_from="2026-08-20T00:00:00Z",
        valid_until="2026-08-21T00:00:00Z",
    )
    assert verify_fresh_status_source_observation_internal_v1(exact) == exact

    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="could not be built"):
        _observation(
            upstream.subject_closure,
            category="HOLD_ACTIVE",
            claim="ABSENT_WITH_EVIDENCE",
            label="over-86400",
            valid_from="2026-08-20T00:00:00Z",
            valid_until="2026-08-21T00:00:01Z",
        )

    request = build_fresh_status_request_v1(
        subject_closure=upstream.subject_closure,
        preparer_identity_ref_sha256=digest("time-preparer"),
        requested_at=FRESH_REQUESTED_AT,
        request_basis="合成时间边界检查。",
        observations=(exact,),
    )
    assert FRESH_STATUS_MAX_WINDOW_SECONDS == 86_400
    assert request.request_valid_until == "2026-08-21T00:02:00Z"
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        build_fresh_status_instruction_v1(
            request=request,
            observations=(exact,),
            checker_identity_ref_sha256=digest("time-checker-expired"),
            evaluated_at=request.request_valid_until,
            checker_basis="故意落在排他截止点。",
        )

    expired_at_boundary = build_fresh_status_instruction_v1(
        request=request,
        observations=(exact,),
        checker_identity_ref_sha256=digest("time-checker-observation-expired"),
        evaluated_at=exact.valid_until,
        checker_basis="Observation 在其排他截止点不再可依赖。",
    )
    assert expired_at_boundary.category_results[0].claim_value == "NOT_ASSESSED"
    assert expired_at_boundary.category_results[0].relied_on_observation_refs == ()


def test_event_time_and_timestamp_grammar_fail_closed(upstream: Upstream) -> None:
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        _observation(
            upstream.subject_closure,
            category="HOLD_ACTIVE",
            claim="PRESENT",
            label="future-event",
            source_event_at="2026-08-20T00:02:00Z",
            observed_at="2026-08-20T00:01:00Z",
        )
    for invalid in (
        "2026-08-20T00:01:00+00:00",
        "2026-08-20T00:01:00.000Z",
        "PERPETUAL",
        "2026-02-30T00:00:00Z",
    ):
        with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
            _observation(
                upstream.subject_closure,
                category="HOLD_ACTIVE",
                claim="PRESENT",
                label=f"invalid-time-{invalid}",
                observed_at=invalid,
            )


def test_preparer_and_checker_identity_references_must_differ(upstream: Upstream) -> None:
    observations = _observations_for_claims(upstream)
    same = digest("same-fresh-role")
    request = build_fresh_status_request_v1(
        subject_closure=upstream.subject_closure,
        preparer_identity_ref_sha256=same,
        requested_at=FRESH_REQUESTED_AT,
        request_basis="合成身份分离检查。",
        observations=observations,
    )
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="could not be built"):
        build_fresh_status_instruction_v1(
            request=request,
            observations=observations,
            checker_identity_ref_sha256=same,
            evaluated_at=FRESH_EVALUATED_AT,
            checker_basis="故意复用同一身份引用。",
        )


def test_observation_order_is_canonical_duplicates_fail(upstream: Upstream) -> None:
    observations = _observations_for_claims(upstream)
    first = build_fresh_status_request_v1(
        subject_closure=upstream.subject_closure,
        preparer_identity_ref_sha256=digest("order-preparer"),
        requested_at=FRESH_REQUESTED_AT,
        request_basis="合成排序检查。",
        observations=observations,
    )
    second = build_fresh_status_request_v1(
        subject_closure=upstream.subject_closure,
        preparer_identity_ref_sha256=digest("order-preparer"),
        requested_at=FRESH_REQUESTED_AT,
        request_basis="合成排序检查。",
        observations=tuple(reversed(observations)),
    )
    assert first == second
    keys = tuple((item.observation_id, item.observation_sha256) for item in first.observation_refs)
    assert keys == tuple(sorted(keys))
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="unique"):
        build_fresh_status_request_v1(
            subject_closure=upstream.subject_closure,
            preparer_identity_ref_sha256=digest("duplicate-preparer"),
            requested_at=FRESH_REQUESTED_AT,
            request_basis="故意重复 Observation。",
            observations=(*observations, observations[0]),
        )


def test_observation_subject_closure_drift_fails(upstream: Upstream) -> None:
    payload = upstream.subject_closure.model_dump(mode="json", exclude={"closure_id"})
    payload["use_scope_review_record_sha256"] = digest("different-review-record")
    other_closure = FreshStatusSubjectClosureV1.model_validate(
        {
            "closure_id": stable_id("real_asset_fresh_status_subject_closure_v1", payload),
            **payload,
        },
        strict=True,
    )
    foreign = _observation(
        other_closure,
        category="HOLD_ACTIVE",
        claim="PRESENT",
        label="foreign-closure",
    )
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="exact Request subject"):
        build_fresh_status_request_v1(
            subject_closure=upstream.subject_closure,
            preparer_identity_ref_sha256=digest("closure-drift-preparer"),
            requested_at=FRESH_REQUESTED_AT,
            request_basis="故意混入另一闭包。",
            observations=(foreign,),
        )


def test_genesis_successor_and_exact_link_summary(upstream: Upstream) -> None:
    base = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="UNKNOWN",
        label="chain-base",
        source_kind="INTERNAL_HOLD_RECORD",
        source_identity_label="chain-owner",
    )
    successor = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="PRESENT",
        label="chain-successor",
        source_kind="INTERNAL_HOLD_RECORD",
        source_identity_label="chain-owner",
        chain_kind="SUCCESSOR",
        predecessor=base,
    )
    assert verify_fresh_status_source_observation_link_v1(observation=base, predecessors=()) == base
    assert (
        verify_fresh_status_source_observation_link_v1(observation=successor, predecessors=(base,))
        == successor
    )
    assert successor.chain_link.previous_observation_sha256 == _sha(base)
    assert successor.chain_link.previous_chain_sha256 == (
        derive_fresh_status_observation_chain_sha256_v1(base)
    )

    other = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="UNKNOWN",
        label="other-chain-byte-summary",
        source_kind="INTERNAL_HOLD_RECORD",
        source_identity_label="chain-owner",
    )
    assert derive_fresh_status_observation_chain_sha256_v1(other) != (
        derive_fresh_status_observation_chain_sha256_v1(base)
    )
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="exact same-chain"):
        verify_fresh_status_source_observation_link_v1(
            observation=successor,
            predecessors=(other,),
        )


def test_chain_link_shape_validation_is_exclusive() -> None:
    with pytest.raises(ValidationError, match="GENESIS"):
        FreshStatusChainLinkV1(
            kind="GENESIS",
            previous_observation_id="real_asset_fresh_status_observation_v1_" + "a" * 20,
            previous_observation_sha256="a" * 64,
            previous_chain_sha256="b" * 64,
        )
    with pytest.raises(ValidationError, match="SUCCESSOR"):
        FreshStatusChainLinkV1(kind="SUCCESSOR")
    with pytest.raises(ValidationError, match="2..8"):
        FreshStatusChainLinkV1(kind="RECONCILIATION")


def test_reconciliation_binds_sorted_unique_heads(upstream: Upstream) -> None:
    base = _observation(
        upstream.subject_closure,
        category="REVOCATION_EFFECTIVE",
        claim="UNKNOWN",
        label="reconcile-base",
        source_kind="REVOCATION_NOTICE",
        source_identity_label="reconcile-owner",
    )
    branch_a = _observation(
        upstream.subject_closure,
        category="REVOCATION_EFFECTIVE",
        claim="PRESENT",
        label="reconcile-branch-a",
        source_kind="REVOCATION_NOTICE",
        source_identity_label="reconcile-owner",
        chain_kind="SUCCESSOR",
        predecessor=base,
    )
    branch_b = _observation(
        upstream.subject_closure,
        category="REVOCATION_EFFECTIVE",
        claim="ABSENT_WITH_EVIDENCE",
        label="reconcile-branch-b",
        source_kind="REVOCATION_NOTICE",
        source_identity_label="reconcile-owner",
        chain_kind="SUCCESSOR",
        predecessor=base,
    )
    reconciled = _observation(
        upstream.subject_closure,
        category="REVOCATION_EFFECTIVE",
        claim="CONFLICT",
        label="reconciled",
        source_kind="REVOCATION_NOTICE",
        source_identity_label="reconcile-owner",
        chain_kind="RECONCILIATION",
        reconciliation_heads=(branch_b, branch_a),
    )
    assert (
        verify_fresh_status_source_observation_link_v1(
            observation=reconciled,
            predecessors=(branch_a, branch_b),
        )
        == reconciled
    )
    head_keys = tuple(
        (head.observation_id, head.observation_sha256, head.chain_sha256)
        for head in reconciled.chain_link.branch_heads
    )
    assert head_keys == tuple(sorted(head_keys))
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="distinct"):
        _observation(
            upstream.subject_closure,
            category="REVOCATION_EFFECTIVE",
            claim="CONFLICT",
            label="duplicate-reconciliation",
            source_kind="REVOCATION_NOTICE",
            source_identity_label="reconcile-owner",
            chain_kind="RECONCILIATION",
            reconciliation_heads=(branch_a, branch_a),
        )


def test_ninth_reconciliation_head_fails_before_artifact_creation(upstream: Upstream) -> None:
    heads = tuple(
        _observation(
            upstream.subject_closure,
            category="COMPLAINT_OPEN",
            claim="UNKNOWN",
            label=f"head-{index}",
            source_kind="COMPLAINT_RECORD",
            source_identity_label="nine-head-owner",
        )
        for index in range(FRESH_STATUS_MAX_RECONCILIATION_HEADS + 1)
    )
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="2..8"):
        _observation(
            upstream.subject_closure,
            category="COMPLAINT_OPEN",
            claim="CONFLICT",
            label="ninth-head-reconciliation",
            source_kind="COMPLAINT_RECORD",
            source_identity_label="nine-head-owner",
            chain_kind="RECONCILIATION",
            reconciliation_heads=heads,
        )


def _many_observations(
    upstream: Upstream,
    count: int,
) -> tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...]:
    return tuple(
        _observation(
            upstream.subject_closure,
            category=CATEGORIES[index % len(CATEGORIES)],
            claim=_non_blocking_claim(CATEGORIES[index % len(CATEGORIES)]),
            label=f"many-{index:02d}",
            source_kind=SOURCE_KINDS[index % len(SOURCE_KINDS)],
        )
        for index in range(count)
    )


def test_observation_count_32_passes_and_33_fails(upstream: Upstream) -> None:
    observations_32 = _many_observations(upstream, FRESH_STATUS_MAX_OBSERVATIONS)
    request = build_fresh_status_request_v1(
        subject_closure=upstream.subject_closure,
        preparer_identity_ref_sha256=digest("count-32-preparer"),
        requested_at=FRESH_REQUESTED_AT,
        request_basis="精确三十二项合成 Observation。",
        observations=observations_32,
    )
    assert len(request.observation_refs) == 32
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="1..32"):
        build_fresh_status_request_v1(
            subject_closure=upstream.subject_closure,
            preparer_identity_ref_sha256=digest("count-33-preparer"),
            requested_at=FRESH_REQUESTED_AT,
            request_basis="故意提交三十三项。",
            observations=_many_observations(upstream, 33),
        )


def test_basis_note_1000_passes_and_1001_fails(upstream: Upstream) -> None:
    assert FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS == 1_000
    exact = _observation(
        upstream.subject_closure,
        category="DISPUTE_OPEN",
        claim="ABSENT_WITH_EVIDENCE",
        label="basis-1000",
        basis_note="界" * 1_000,
    )
    assert len(exact.basis_note) == 1_000
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        _observation(
            upstream.subject_closure,
            category="DISPUTE_OPEN",
            claim="ABSENT_WITH_EVIDENCE",
            label="basis-1001",
            basis_note="界" * 1_001,
        )


@pytest.mark.parametrize("source_kind", SOURCE_KINDS)
def test_all_eight_source_kinds_are_closed_but_not_predicate_mapped(
    upstream: Upstream,
    source_kind: FreshStatusSourceKindV1,
) -> None:
    observation = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="ABSENT_WITH_EVIDENCE",
        label=f"source-kind-{source_kind}",
        source_kind=source_kind,
    )
    assert observation.source_kind == source_kind


def test_unknown_source_kind_and_limitation_shapes_fail(upstream: Upstream) -> None:
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        _observation(
            upstream.subject_closure,
            category="HOLD_ACTIVE",
            claim="ABSENT_WITH_EVIDENCE",
            label="unknown-source-kind",
            source_kind=cast(Any, "HOLD_STATUS_RECORD"),
        )

    for limitations in (
        MANDATORY_LIMITATIONS[:3],
        tuple(reversed(MANDATORY_LIMITATIONS)),
        (*MANDATORY_LIMITATIONS, "UNAPPROVED_LIMITATION"),
    ):
        with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
            _observation(
                upstream.subject_closure,
                category="HOLD_ACTIVE",
                claim="ABSENT_WITH_EVIDENCE",
                label=f"bad-limitation-{len(limitations)}-{limitations[-1]}",
                limitation_codes=limitations,
            )

    exact_mandatory = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="ABSENT_WITH_EVIDENCE",
        label="mandatory-limitations-only",
        limitation_codes=MANDATORY_LIMITATIONS,
    )
    assert exact_mandatory.limitation_codes == MANDATORY_LIMITATIONS


def test_record_internal_and_complete_closure_replay(bundle: FreshBundle) -> None:
    assert verify_fresh_status_evidence_record_internal_v1(bundle.record) == bundle.record
    closure = bundle.upstream.closure
    assert (
        verify_fresh_status_evidence_record_closure_v1(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            qualification_request=closure.request,
            qualification_instruction=closure.instruction,
            qualification_decision=closure.decision,
            rights_manifest=closure.manifest,
            use_plan=bundle.upstream.use_plan,
            use_scope_review_record=bundle.upstream.use_scope_record,
            observations=bundle.observations,
            record=bundle.record,
        )
        == bundle.record
    )

    forged = bundle.record.model_copy(update={"request_sha256": digest("forged-request")})
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        verify_fresh_status_evidence_record_internal_v1(forged)
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        verify_fresh_status_evidence_record_closure_v1(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            qualification_request=closure.request,
            qualification_instruction=closure.instruction,
            qualification_decision=closure.decision,
            rights_manifest=closure.manifest,
            use_plan=bundle.upstream.use_plan,
            use_scope_review_record=bundle.upstream.use_scope_record,
            observations=bundle.observations[:-1],
            record=bundle.record,
        )


def test_basis_code_must_match_predicate_state_and_transition(upstream: Upstream) -> None:
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        _observation(
            upstream.subject_closure,
            category="HOLD_ACTIVE",
            claim="ABSENT_WITH_EVIDENCE",
            label="wrong-genesis-basis",
            basis_code="HOLD_IMPOSED",
        )

    predecessor = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="PRESENT",
        label="basis-predecessor",
        source_kind="INTERNAL_HOLD_RECORD",
        source_identity_label="basis-chain",
    )
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error):
        _observation(
            upstream.subject_closure,
            category="HOLD_ACTIVE",
            claim="ABSENT_WITH_EVIDENCE",
            label="wrong-successor-basis",
            source_kind="INTERNAL_HOLD_RECORD",
            source_identity_label="basis-chain",
            basis_code="STATUS_RECONFIRMED",
            chain_kind="SUCCESSOR",
            predecessor=predecessor,
        )


def test_same_claim_explicit_fork_is_indeterminate(upstream: Upstream) -> None:
    base = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="UNKNOWN",
        label="same-claim-fork-base",
        source_kind="INTERNAL_HOLD_RECORD",
        source_identity_label="same-claim-fork-chain",
    )
    branches = tuple(
        _observation(
            upstream.subject_closure,
            category="HOLD_ACTIVE",
            claim="PRESENT",
            label=f"same-claim-fork-{suffix}",
            source_kind="INTERNAL_HOLD_RECORD",
            source_identity_label="same-claim-fork-chain",
            chain_kind="SUCCESSOR",
            predecessor=base,
        )
        for suffix in ("a", "b")
    )
    other_categories = _observations_for_claims(upstream)[1:]
    built = _build_bundle(upstream, (*branches, *other_categories))
    result = built.instruction.category_results[0]
    assert result.claim_value == "CONFLICT"
    assert result.assessment_effect == "INDETERMINATE"


def test_not_assessed_observation_is_never_relied_on(upstream: Upstream) -> None:
    observations = (
        _observation(
            upstream.subject_closure,
            category="HOLD_ACTIVE",
            claim="NOT_ASSESSED",
            label="explicit-not-assessed",
        ),
        *_observations_for_claims(upstream)[1:],
    )
    built = _build_bundle(upstream, observations)
    result = built.instruction.category_results[0]
    assert result.claim_value == "NOT_ASSESSED"
    assert result.observation_refs
    assert result.relied_on_observation_refs == ()
    assert built.record.decision.disposition == "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"


def test_decision_horizon_is_capped_by_request_and_explicit_evidence(
    bundle: FreshBundle,
) -> None:
    assert bundle.record.decision.status_valid_until == min(
        bundle.request.request_valid_until,
        *(item.valid_until for item in bundle.observations),
    )
    assert bundle.record.decision.status_valid_until <= bundle.request.request_valid_until


def test_observation_refs_bind_source_identity_and_chain(bundle: FreshBundle) -> None:
    observations_by_id = {item.observation_id: item for item in bundle.observations}
    for reference in bundle.request.observation_refs:
        observation = observations_by_id[reference.observation_id]
        assert reference.source_identity_ref_sha256 == observation.source_identity_ref_sha256
        assert reference.chain_sha256 == derive_fresh_status_observation_chain_sha256_v1(
            observation
        )


def test_reference_and_head_ids_and_digests_are_independently_unique() -> None:
    duplicate_id = "real_asset_fresh_status_observation_v1_" + "a" * 20
    refs = tuple(
        FreshStatusObservationRefV1(
            observation_id=duplicate_id,
            observation_sha256=character * 64,
            status_category="HOLD_ACTIVE",
            source_identity_ref_sha256=("c" if character == "a" else "d") * 64,
            chain_sha256=("e" if character == "a" else "f") * 64,
        )
        for character in ("a", "b")
    )
    with pytest.raises(ValidationError, match="unique"):
        FreshStatusCategoryResultV1(
            status_category="HOLD_ACTIVE",
            claim_value="NOT_ASSESSED",
            assessment_effect="INDETERMINATE",
            observation_refs=refs,
            relied_on_observation_refs=(),
            result_valid_until=FRESH_EVALUATED_AT,
        )

    heads = tuple(
        FreshStatusChainHeadRefV1(
            observation_id=duplicate_id,
            observation_sha256=character * 64,
            chain_sha256=("1" if character == "a" else "2") * 64,
        )
        for character in ("a", "b")
    )
    with pytest.raises(ValidationError, match="unique"):
        FreshStatusChainLinkV1(kind="RECONCILIATION", branch_heads=heads)


@pytest.mark.parametrize(
    "field,value",
    (
        ("source_identity_ref_sha256", "9" * 64),
        ("chain_sha256", "8" * 64),
        ("status_category", "COMPLAINT_OPEN"),
    ),
)
def test_relied_reference_must_match_the_complete_category_reference(
    bundle: FreshBundle,
    field: str,
    value: str,
) -> None:
    reference = bundle.instruction.category_results[0].observation_refs[0]
    forged = reference.model_copy(update={field: value})
    with pytest.raises(ValidationError, match="exactly match"):
        FreshStatusCategoryResultV1(
            status_category="HOLD_ACTIVE",
            claim_value="ABSENT_WITH_EVIDENCE",
            assessment_effect="NON_BLOCKING_WITHIN_BOUND_WINDOW",
            observation_refs=(reference,),
            relied_on_observation_refs=(forged,),
            result_valid_until=VALID_UNTIL,
        )


def test_parser_rejects_rehashed_cross_module_identity_drift(bundle: FreshBundle) -> None:
    instruction_data = bundle.instruction.model_dump(mode="json")
    instruction_data["preparer_identity_ref_sha256"] = digest("forged-preparer")
    instruction_data["instruction_id"] = stable_id(
        "real_asset_fresh_status_instruction_v1",
        {key: value for key, value in instruction_data.items() if key != "instruction_id"},
    )
    forged_instruction = type(bundle.instruction).model_validate(
        instruction_data,
        strict=False,
    )

    decision_data = bundle.record.decision.model_dump(mode="json")
    decision_data["instruction_id"] = forged_instruction.instruction_id
    decision_data["instruction_sha256"] = _sha(forged_instruction)
    decision_data["decision_id"] = stable_id(
        "real_asset_fresh_status_decision_v1",
        {key: value for key, value in decision_data.items() if key != "decision_id"},
    )
    forged_decision = type(bundle.record.decision).model_validate(decision_data, strict=False)

    record_data = bundle.record.model_dump(mode="json")
    record_data["instruction"] = forged_instruction.model_dump(mode="json")
    record_data["instruction_sha256"] = _sha(forged_instruction)
    record_data["decision"] = forged_decision.model_dump(mode="json")
    record_data["decision_sha256"] = _sha(forged_decision)
    record_data["record_id"] = stable_id(
        "real_asset_fresh_status_evidence_record_v1",
        {key: value for key, value in record_data.items() if key != "record_id"},
    )
    with pytest.raises(RealAssetFreshStatusEvidenceV30Error, match="strict contract"):
        parse_fresh_status_evidence_record_v1_json(_render(record_data))


def test_policy_digest_and_limits_are_reviewed_goldens() -> None:
    assert FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256 == (
        "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"
    )
    assert FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE_DOCUMENT_SHA256 == (
        "76d151b7a73dcef7aafa6a928e20e024f353ead30fa91a0b7522078eca3f3c7e"
    )
    policy_raw = json.dumps(
        fresh_status_module._FRESH_STATUS_POLICY_PAYLOAD,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    assert (
        hashlib.sha256(
            b"sdc:creative-sample-real-asset-fresh-status-evidence-policy:v3.0\0" + policy_raw
        ).hexdigest()
        == FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256
    )
    assert FRESH_STATUS_MAX_WINDOW_SECONDS == 86_400
    assert FRESH_STATUS_MAX_OBSERVATIONS == 32
    assert FRESH_STATUS_JSON_MAX_DEPTH == 32
    assert FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES == 262_144
    assert FRESH_STATUS_RECORD_MAX_BYTES == 2_097_152


def test_source_is_pure_and_has_no_path_network_provider_or_wall_clock() -> None:
    source = inspect.getsource(fresh_status_module)
    tree = ast.parse(source)
    forbidden_import_roots = {
        "asyncio",
        "httpx",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    forbidden_sdc_prefixes = (
        "sdc.ark_entitlement",
        "sdc.client",
        "sdc.persistence",
        "sdc.provider",
        "sdc.runtime",
        "sdc.worker",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(
                alias.name.split(".", maxsplit=1)[0] not in forbidden_import_roots
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            imported = node.module or ""
            assert imported.split(".", maxsplit=1)[0] not in forbidden_import_roots
            assert not imported.startswith(forbidden_sdc_prefixes)
            assert all(alias.name != "Path" for alias in node.names)
        elif isinstance(node, ast.Call):
            assert not (isinstance(node.func, ast.Name) and node.func.id == "open")
            assert not (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in {"now", "utcnow", "time", "open", "read", "write"}
            )
    assert "Path" not in fresh_status_module.__all__


def test_documented_public_api_has_no_cli_or_io_surface() -> None:
    public = set(fresh_status_module.__all__)
    required = {
        "build_fresh_status_source_observation_v1",
        "build_fresh_status_request_v1",
        "build_fresh_status_instruction_v1",
        "compile_fresh_status_decision_v1",
        "build_fresh_status_evidence_record_v1",
        "verify_fresh_status_evidence_record_internal_v1",
        "verify_fresh_status_evidence_record_closure_v1",
        "extract_fresh_status_request_v1",
        "extract_fresh_status_instruction_v1",
        "extract_fresh_status_decision_v1",
    }
    assert required <= public
    forbidden_names = {
        "main",
        "open",
        "Path",
        "authorize",
        "current_assessor",
    }
    assert not (public & forbidden_names)
    assert not any(
        name.lower().startswith(("cli_", "path_", "file_", "provider_")) for name in public
    )


def test_constants_match_approved_resource_boundary() -> None:
    assert FRESH_STATUS_MAX_RECONCILIATION_HEADS == 8
    assert FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS == 1_000
    assert FRESH_STATUS_AUTHORING_INPUT_MAX_BYTES == 65_536
    assert FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES == 262_144
    assert FRESH_STATUS_RECORD_MAX_BYTES == 2_097_152
    assert FRESH_STATUS_JSON_MAX_DEPTH == 32
