from __future__ import annotations

import ast
import hashlib
import inspect
import json

import pytest
from pydantic import ValidationError
from real_asset_v2_test_support import (
    MANIFEST_AT,
    CompleteClosure,
    canonical_document,
    digest,
    make_complete_closure,
)

from sdc.compiler import stable_id
from sdc.real_asset_use_plan_v26 import (
    CreativeSampleRealAssetUsePlanV1,
    RealAssetUsePlanV26Error,
    build_real_asset_use_plan_v1,
    parse_real_asset_use_plan_v1_json,
    verify_real_asset_use_plan_closure_v1,
)
from sdc.real_asset_use_scope_review_v26 import (
    REVIEW_VALIDITY_SECONDS,
    CreativeSampleRealAssetUseScopeReviewDecisionV1,
    CreativeSampleRealAssetUseScopeReviewInstructionV1,
    CreativeSampleRealAssetUseScopeReviewRecordV1,
    CreativeSampleRealAssetUseScopeReviewRequestV1,
    RealAssetUseScopeReviewV26Error,
    UseScopeGateResultV1,
    build_use_scope_review_instruction_v1,
    build_use_scope_review_record_v1,
    build_use_scope_review_request_v1,
    extract_use_scope_decision_v1,
    extract_use_scope_instruction_v1,
    extract_use_scope_request_v1,
    parse_use_scope_review_decision_v1_json,
    parse_use_scope_review_instruction_v1_json,
    parse_use_scope_review_record_v1_json,
    parse_use_scope_review_request_v1_json,
    verify_use_scope_review_current_v1,
    verify_use_scope_review_record_closure_v1,
    verify_use_scope_review_record_internal_v1,
)

REQUESTED_AT = "2026-08-19T12:01:00Z"
CHECKED_AT = "2026-08-19T12:02:00Z"


def _build_plan(
    *, valid_until: str | None = None
) -> tuple[CompleteClosure, CreativeSampleRealAssetUsePlanV1]:
    closure = (
        make_complete_closure()
        if valid_until is None
        else make_complete_closure(valid_until=valid_until)
    )
    plan = build_real_asset_use_plan_v1(
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
    return closure, plan


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


def _build_record(*, valid_until: str | None = None) -> tuple[
    CompleteClosure,
    CreativeSampleRealAssetUsePlanV1,
    CreativeSampleRealAssetUseScopeReviewRequestV1,
    CreativeSampleRealAssetUseScopeReviewInstructionV1,
    CreativeSampleRealAssetUseScopeReviewRecordV1,
]:
    closure, plan = _build_plan(valid_until=valid_until)
    request = build_use_scope_review_request_v1(
        use_plan=plan,
        maker_identity_ref_sha256=digest("maker"),
        requested_at=REQUESTED_AT,
        request_basis="请求审查精确离线用途计划与既有权利范围的一致性。",
    )
    instruction = build_use_scope_review_instruction_v1(
        request=request,
        checker_identity_ref_sha256=digest("checker"),
        evaluated_at=CHECKED_AT,
        gate_results=_all_pass_gates(),
        disposition="PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY",
        checker_basis="六项离线用途范围均与精确计划及权利证据一致。",
    )
    record = build_use_scope_review_record_v1(
        request=request,
        instruction=instruction,
    )
    return closure, plan, request, instruction, record


def test_use_plan_is_deterministic_exact_and_zero_authority() -> None:
    closure, plan = _build_plan()
    second = build_real_asset_use_plan_v1(
        pack=closure.pack,  # type: ignore[union-attr]
        evidence=closure.evidence,  # type: ignore[union-attr]
        reviewer_a=closure.reviewer_a,  # type: ignore[union-attr]
        reviewer_b=closure.reviewer_b,  # type: ignore[union-attr]
        pair_check=closure.pair_check,  # type: ignore[union-attr]
        qualification_request=closure.request,  # type: ignore[union-attr]
        qualification_instruction=closure.instruction,  # type: ignore[union-attr]
        qualification_decision=closure.decision,  # type: ignore[union-attr]
        rights_manifest=closure.manifest,  # type: ignore[union-attr]
    )
    assert plan == second
    assert len(plan.media_mappings) == 14
    assert tuple(item.kind for item in plan.media_mappings) == (
        "IMAGE",
        "IMAGE",
        "IMAGE",
        "IMAGE",
        *("VOICE" for _ in range(9)),
        "BGM",
    )
    assert len(plan.planned_shot_ids) == 10
    assert all(
        current != predecessor
        for current, predecessor in zip(
            plan.planned_shot_ids,
            plan.baseline.pilot_ordered_shot_ids,
            strict=True,
        )
    )
    assert plan.proposed_provider_requests_max == (
        plan.shot_count * plan.proposed_attempts_per_shot
    )
    assert plan.source_mode == "IMPORTED_MEDIA"
    assert plan.authorized_attempts == plan.authorized_cost_cny == 0
    assert plan.rights_manifest_created is True
    assert plan.eligible_for_separate_use_scope_review is True
    assert plan.eligible_for_separate_provider_proposal is False
    assert plan.eligible_for_separate_provider_approval is False
    assert plan.provider_approval_granted is False
    assert plan.eligible_for_real_generation is False
    assert plan.generation_authorized is False
    assert plan.execution_authorized is False
    assert plan.publication_authorized is False
    assert plan.remote_processing_allowed is False
    assert plan.retention_allowed is False
    assert plan.training_allowed is False
    assert plan.publication_allowed is False
    assert plan.posts_allowed == plan.provider_requests == 0
    assert "plan_at" not in CreativeSampleRealAssetUsePlanV1.model_fields
    assert parse_real_asset_use_plan_v1_json(canonical_document(plan)) == plan


def test_use_plan_full_closure_and_internal_drift_fail_closed() -> None:
    closure, plan = _build_plan()
    assert (
        verify_real_asset_use_plan_closure_v1(
            pack=closure.pack,  # type: ignore[union-attr]
            evidence=closure.evidence,  # type: ignore[union-attr]
            reviewer_a=closure.reviewer_a,  # type: ignore[union-attr]
            reviewer_b=closure.reviewer_b,  # type: ignore[union-attr]
            pair_check=closure.pair_check,  # type: ignore[union-attr]
            qualification_request=closure.request,  # type: ignore[union-attr]
            qualification_instruction=closure.instruction,  # type: ignore[union-attr]
            qualification_decision=closure.decision,  # type: ignore[union-attr]
            rights_manifest=closure.manifest,  # type: ignore[union-attr]
            use_plan=plan,
        )
        == plan
    )
    forged = plan.model_copy(update={"provider_requests": 1})
    with pytest.raises(RealAssetUsePlanV26Error, match="strict contract"):
        verify_real_asset_use_plan_closure_v1(
            pack=closure.pack,  # type: ignore[union-attr]
            evidence=closure.evidence,  # type: ignore[union-attr]
            reviewer_a=closure.reviewer_a,  # type: ignore[union-attr]
            reviewer_b=closure.reviewer_b,  # type: ignore[union-attr]
            pair_check=closure.pair_check,  # type: ignore[union-attr]
            qualification_request=closure.request,  # type: ignore[union-attr]
            qualification_instruction=closure.instruction,  # type: ignore[union-attr]
            qualification_decision=closure.decision,  # type: ignore[union-attr]
            rights_manifest=closure.manifest,  # type: ignore[union-attr]
            use_plan=forged,
        )
    wrong_mapping = plan.media_mappings[0].model_copy(
        update={"target_id": plan.media_mappings[1].target_id}
    )
    with pytest.raises(ValidationError, match="mapping ID|active planned asset"):
        CreativeSampleRealAssetUsePlanV1.model_validate(
            {
                **plan.model_dump(mode="python"),
                "media_mappings": (wrong_mapping, *plan.media_mappings[1:]),
            },
            strict=True,
        )


def test_use_plan_parser_rejects_ambiguous_or_noncanonical_json() -> None:
    _, plan = _build_plan()
    raw = canonical_document(plan)
    with pytest.raises(RealAssetUsePlanV26Error, match="canonical"):
        parse_real_asset_use_plan_v1_json(raw.rstrip())
    with pytest.raises(RealAssetUsePlanV26Error, match="BOM"):
        parse_real_asset_use_plan_v1_json(b"\xef\xbb\xbf" + raw)
    duplicate = (
        "{"
        + json.dumps("plan_id")
        + ":"
        + json.dumps(plan.plan_id)
        + ","
        + raw.decode()[1:]
    ).encode()
    with pytest.raises(RealAssetUsePlanV26Error, match="duplicate"):
        parse_real_asset_use_plan_v1_json(duplicate)
    unknown = plan.model_dump(mode="json")
    unknown["unknown"] = True
    with pytest.raises(RealAssetUsePlanV26Error, match="strict contract"):
        parse_real_asset_use_plan_v1_json(
            (json.dumps(unknown, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        )


def test_single_record_preserves_three_modules_and_standard_hash_chain() -> None:
    closure, plan, request, instruction, record = _build_record()
    assert isinstance(record, CreativeSampleRealAssetUseScopeReviewRecordV1)
    assert record.request_sha256 == hashlib.sha256(canonical_document(request)).hexdigest()
    assert record.instruction_sha256 == hashlib.sha256(
        canonical_document(instruction)
    ).hexdigest()
    assert record.decision_sha256 == hashlib.sha256(
        canonical_document(record.decision)
    ).hexdigest()
    assert record.instruction.request_sha256 == record.request_sha256
    assert record.decision.instruction_sha256 == record.instruction_sha256
    assert record.decision.decision == "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY"
    assert record.decision.eligible_for_separate_provider_proposal is True
    assert record.decision.provider_approval_granted is False
    assert record.decision.eligible_for_real_generation is False
    assert record.decision.execution_authorized is False
    assert record.decision.publication_authorized is False
    assert record.decision.posts_allowed == record.decision.provider_requests == 0
    assert verify_use_scope_review_record_internal_v1(record) == record
    assert (
        verify_use_scope_review_record_closure_v1(
            pack=closure.pack,  # type: ignore[union-attr]
            evidence=closure.evidence,  # type: ignore[union-attr]
            reviewer_a=closure.reviewer_a,  # type: ignore[union-attr]
            reviewer_b=closure.reviewer_b,  # type: ignore[union-attr]
            pair_check=closure.pair_check,  # type: ignore[union-attr]
            qualification_request=closure.request,  # type: ignore[union-attr]
            qualification_instruction=closure.instruction,  # type: ignore[union-attr]
            qualification_decision=closure.decision,  # type: ignore[union-attr]
            rights_manifest=closure.manifest,  # type: ignore[union-attr]
            use_plan=plan,
            record=record,
        )
        == record
    )

    extracted_request, request_bytes = extract_use_scope_request_v1(record)
    extracted_instruction, instruction_bytes = extract_use_scope_instruction_v1(record)
    extracted_decision, decision_bytes = extract_use_scope_decision_v1(record)
    assert extracted_request == request
    assert extracted_instruction == instruction
    assert extracted_decision == record.decision
    assert parse_use_scope_review_request_v1_json(request_bytes) == request
    assert parse_use_scope_review_instruction_v1_json(instruction_bytes) == instruction
    assert parse_use_scope_review_decision_v1_json(decision_bytes) == record.decision
    assert parse_use_scope_review_record_v1_json(canonical_document(record)) == record


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("rights_manifest_id", "real_asset_rights_manifest_v2_" + "f" * 20),
        ("rights_manifest_sha256", digest("forged-manifest")),
        ("rights_manifest_at", "2026-08-19T11:59:59Z"),
        ("evidence_valid_until", "PERPETUAL"),
    ),
)
def test_full_review_closure_rebuilds_request_from_verified_plan(
    field: str,
    replacement: str,
) -> None:
    closure, plan, request, instruction, _ = _build_record()
    request_payload = request.model_dump(mode="json", exclude={"request_id"})
    request_payload[field] = replacement
    forged_request = CreativeSampleRealAssetUseScopeReviewRequestV1.model_validate(
        {
            "request_id": stable_id("real_asset_use_scope_request_v1", request_payload),
            **request_payload,
        },
        strict=True,
    )
    forged_instruction = build_use_scope_review_instruction_v1(
        request=forged_request,
        checker_identity_ref_sha256=instruction.checker_identity_ref_sha256,
        evaluated_at=instruction.evaluated_at,
        gate_results=instruction.gate_results,
        disposition=instruction.disposition,
        checker_basis=instruction.checker_basis,
    )
    forged_record = build_use_scope_review_record_v1(
        request=forged_request,
        instruction=forged_instruction,
    )
    assert verify_use_scope_review_record_internal_v1(forged_record) == forged_record
    with pytest.raises(RealAssetUseScopeReviewV26Error, match="Request drifted"):
        verify_use_scope_review_record_closure_v1(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            qualification_request=closure.request,
            qualification_instruction=closure.instruction,
            qualification_decision=closure.decision,
            rights_manifest=closure.manifest,
            use_plan=plan,
            record=forged_record,
        )


def test_extracted_instruction_and_decision_enforce_time_formulas_independently() -> None:
    _, _, _, instruction, record = _build_record()
    instruction_payload = instruction.model_dump(mode="python", exclude={"instruction_id"})
    instruction_payload["request_valid_until"] = "2026-08-21T12:01:00Z"
    with pytest.raises(ValidationError, match="fixed request window"):
        CreativeSampleRealAssetUseScopeReviewInstructionV1.model_validate(
            {
                "instruction_id": stable_id(
                    "real_asset_use_scope_instruction_v1", instruction_payload
                ),
                **instruction_payload,
            },
            strict=True,
        )

    decision_payload = record.decision.model_dump(mode="python", exclude={"decision_id"})
    decision_payload["review_valid_until"] = "2026-10-01T00:00:00Z"
    with pytest.raises(ValidationError, match="horizon drifted"):
        CreativeSampleRealAssetUseScopeReviewDecisionV1.model_validate(
            {
                "decision_id": stable_id(
                    "real_asset_use_scope_decision_v1", decision_payload
                ),
                **decision_payload,
            },
            strict=True,
        )


@pytest.mark.parametrize("disposition", ["NEEDS_REVISION", "REJECTED"])
def test_negative_gate_deterministically_blocks_proposal(disposition: str) -> None:
    _, plan = _build_plan()
    request = build_use_scope_review_request_v1(
        use_plan=plan,
        maker_identity_ref_sha256=digest("maker-negative"),
        requested_at=REQUESTED_AT,
        request_basis="请求检查一份存在待确认项的离线用途计划。",
    )
    gates = list(_all_pass_gates())
    gates[2] = UseScopeGateResultV1(
        gate="PRIVACY_USE_SCOPE",
        approved=False,
        note="隐私用途范围仍需补充明确依据。",
    )
    instruction = build_use_scope_review_instruction_v1(
        request=request,
        checker_identity_ref_sha256=digest(f"checker:{disposition}"),
        evaluated_at=CHECKED_AT,
        gate_results=tuple(gates),
        disposition=disposition,  # type: ignore[arg-type]
        checker_basis="隐私用途范围未能在本次评审中确认。",
    )
    record = build_use_scope_review_record_v1(
        request=request,
        instruction=instruction,
    )
    assert record.decision.eligible_for_separate_provider_proposal is False
    assert "PRIVACY_USE_SCOPE_NOT_CONFIRMED" in record.decision.issue_codes
    assert ("CHECKER_REJECTED_USE_SCOPE" in record.decision.issue_codes) is (
        disposition == "REJECTED"
    )


def test_time_identity_and_currentness_boundaries_fail_closed() -> None:
    _, plan = _build_plan()
    with pytest.raises(RealAssetUseScopeReviewV26Error, match="could not be built"):
        build_use_scope_review_request_v1(
            use_plan=plan,
            maker_identity_ref_sha256=digest("maker-before-manifest"),
            requested_at="2026-08-19T11:59:59Z",
            request_basis="此请求故意早于Manifest。",
        )
    request = build_use_scope_review_request_v1(
        use_plan=plan,
        maker_identity_ref_sha256=digest("same-person"),
        requested_at=REQUESTED_AT,
        request_basis="请求执行离线用途范围评审。",
    )
    with pytest.raises(RealAssetUseScopeReviewV26Error, match="could not be built"):
        build_use_scope_review_instruction_v1(
            request=request,
            checker_identity_ref_sha256=request.maker_identity_ref_sha256,
            evaluated_at=CHECKED_AT,
            gate_results=_all_pass_gates(),
            disposition="PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY",
            checker_basis="故意使用同一程序性身份引用。",
        )
    with pytest.raises(RealAssetUseScopeReviewV26Error, match="could not be built"):
        build_use_scope_review_instruction_v1(
            request=request,
            checker_identity_ref_sha256=digest("late-checker"),
            evaluated_at=request.request_valid_until,
            gate_results=_all_pass_gates(),
            disposition="PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY",
            checker_basis="故意落在排他的申请截止边界。",
        )

    closure, plan, _, _, record = _build_record()
    assert REVIEW_VALIDITY_SECONDS == 2_592_000
    assert (
        verify_use_scope_review_current_v1(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            qualification_request=closure.request,
            qualification_instruction=closure.instruction,
            qualification_decision=closure.decision,
            rights_manifest=closure.manifest,
            use_plan=plan,
            record=record,
            observed_at="2026-08-20T00:00:00Z",
        )
        == record
    )
    with pytest.raises(RealAssetUseScopeReviewV26Error, match="not currently"):
        verify_use_scope_review_current_v1(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            qualification_request=closure.request,
            qualification_instruction=closure.instruction,
            qualification_decision=closure.decision,
            rights_manifest=closure.manifest,
            use_plan=plan,
            record=record,
            observed_at="2026-08-19T12:01:59Z",
        )
    with pytest.raises(RealAssetUseScopeReviewV26Error, match="not currently"):
        verify_use_scope_review_current_v1(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            qualification_request=closure.request,
            qualification_instruction=closure.instruction,
            qualification_decision=closure.decision,
            rights_manifest=closure.manifest,
            use_plan=plan,
            record=record,
            observed_at=record.decision.review_valid_until,
        )


def test_finite_evidence_exclusively_caps_review_horizon() -> None:
    evidence_end = "2026-08-20T12:02:30Z"
    closure, plan, _, _, record = _build_record(valid_until=evidence_end)
    assert record.decision.review_valid_until == evidence_end
    assert (
        verify_use_scope_review_current_v1(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            qualification_request=closure.request,
            qualification_instruction=closure.instruction,
            qualification_decision=closure.decision,
            rights_manifest=closure.manifest,
            use_plan=plan,
            record=record,
            observed_at="2026-08-20T12:02:29Z",
        )
        == record
    )
    with pytest.raises(RealAssetUseScopeReviewV26Error, match="not currently"):
        verify_use_scope_review_current_v1(
            pack=closure.pack,
            evidence=closure.evidence,
            reviewer_a=closure.reviewer_a,
            reviewer_b=closure.reviewer_b,
            pair_check=closure.pair_check,
            qualification_request=closure.request,
            qualification_instruction=closure.instruction,
            qualification_decision=closure.decision,
            rights_manifest=closure.manifest,
            use_plan=plan,
            record=record,
            observed_at=evidence_end,
        )


def test_all_authority_fields_are_literal_false_or_zero() -> None:
    _, plan, request, instruction, record = _build_record()
    plan_false_fields = (
        "use_scope_review_performed",
        "eligible_for_separate_provider_proposal",
        "eligible_for_separate_provider_approval",
        "provider_approval_granted",
        "eligible_for_real_generation",
        "generation_authorized",
        "execution_authorized",
        "publication_authorized",
        "remote_processing_allowed",
        "retention_allowed",
        "training_allowed",
        "publication_allowed",
    )
    for field in plan_false_fields:
        with pytest.raises(ValidationError):
            CreativeSampleRealAssetUsePlanV1.model_validate(
                {**plan.model_dump(mode="python"), field: True},
                strict=True,
            )
    for field in (
        "authorized_attempts",
        "authorized_cost_cny",
        "posts_allowed",
        "provider_requests",
    ):
        with pytest.raises(ValidationError):
            CreativeSampleRealAssetUsePlanV1.model_validate(
                {**plan.model_dump(mode="python"), field: 1},
                strict=True,
            )

    review_false_fields = (
        "eligible_for_separate_provider_approval",
        "provider_approval_granted",
        "eligible_for_real_generation",
        "generation_authorized",
        "execution_authorized",
        "publication_authorized",
        "remote_processing_allowed",
        "retention_allowed",
        "training_allowed",
        "publication_allowed",
    )
    for module in (request, instruction, record.decision):
        model = type(module)
        for field in review_false_fields:
            with pytest.raises(ValidationError):
                model.model_validate(
                    {**module.model_dump(mode="python"), field: True},
                    strict=True,
                )
        for field in (
            "authorized_attempts",
            "authorized_cost_cny",
            "posts_allowed",
            "provider_requests",
        ):
            with pytest.raises(ValidationError):
                model.model_validate(
                    {**module.model_dump(mode="python"), field: 1},
                    strict=True,
                )


def test_pure_modules_import_no_runtime_provider_clock_or_v1_revision_path() -> None:
    import sdc.real_asset_use_plan_v26 as plan_module
    import sdc.real_asset_use_scope_review_v26 as review_module

    module_sources = (inspect.getsource(plan_module), inspect.getsource(review_module))
    source = "\n".join(module_sources)
    for forbidden in (
        "datetime.now",
        "datetime.utcnow",
        "from sdc.runtime",
        "from sdc.provider",
        "from sdc.worker",
        "from sdc.ark_entitlement",
        "CreativeSampleRealAssetRevision",
        "_derive_real_spec",
        "qualify_real_asset_candidate_pack",
        "build_real_asset_rights_manifest(",
    ):
        assert forbidden not in source
    forbidden_import_roots = {
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
        "sdc.provider",
        "sdc.runtime",
        "sdc.worker",
    )
    for module_source in module_sources:
        tree = ast.parse(module_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(
                    alias.name.split(".", maxsplit=1)[0] not in forbidden_import_roots
                    for alias in node.names
                )
            if isinstance(node, ast.ImportFrom):
                imported = node.module or ""
                assert imported.split(".", maxsplit=1)[0] not in forbidden_import_roots
                assert not imported.startswith(forbidden_sdc_prefixes)
            if isinstance(node, ast.Call):
                assert not (isinstance(node.func, ast.Name) and node.func.id == "open")
                assert not (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"now", "utcnow"}
                )
    assert MANIFEST_AT < REQUESTED_AT
