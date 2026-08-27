from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any, cast, get_args

import pytest
from pydantic import ValidationError
from test_real_asset_fresh_status_evidence_v30 import (
    ALL_LIMITATIONS,
    CATEGORIES,
    FRESH_EVALUATED_AT,
    VALID_FROM,
    FreshBundle,
    FreshStatusClaimValueV1,
    Upstream,
    _build_bundle,
    _build_upstream,
    _observation,
)
from test_real_asset_fresh_status_record_as_of_assessment_v30 import (
    _assessment_kwargs,
    _complete_category_bundle,
    _shift_seconds,
)
from test_real_asset_fresh_status_record_chain_coverage_v30 import (
    CoverageGraph,
    _build_graph,
    _chain,
)
from test_real_asset_fresh_status_record_joint_replay_v30 import (
    _build_alternate_upstream,
)

import sdc.real_asset_fresh_status_record_as_of_assessment_receipt_v30 as receipt_module
from sdc.real_asset_fresh_status_chain_replay_v30 import (
    FreshStatusChainReplayErrorCodeV1,
)
from sdc.real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
    FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES,
    FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_V1_PROFILE,
    CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
    FreshStatusRecordAsOfAssessmentReceiptErrorCodeV1,
    RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error,
    build_fresh_status_record_as_of_assessment_receipt_v1,
    verify_fresh_status_record_as_of_assessment_receipt_closure_v1,
)
from sdc.real_asset_fresh_status_record_as_of_assessment_v30 import (
    FreshStatusEvidenceRecordAsOfAssessmentResultV1,
    FreshStatusRecordAsOfAssessmentErrorCodeV1,
    RealAssetFreshStatusRecordAsOfAssessmentV30Error,
    assess_fresh_status_evidence_record_as_of_v1,
)
from sdc.real_asset_fresh_status_record_chain_coverage_v30 import (
    FreshStatusRecordChainCoverageErrorCodeV1,
    FreshStatusRecordChainInputV1,
)
from sdc.real_asset_fresh_status_record_joint_replay_v30 import (
    FreshStatusRecordJointReplayErrorCodeV1,
)
from sdc.schemas import MODELS

_DEFAULT_AS_OF = object()
_RECEIPT_ID_KIND = "real_asset_fresh_status_record_as_of_assessment_receipt_v1"
_ASSESSMENT_DOMAIN = b"sdc:creative-sample-real-asset-fresh-status-record-as-of-assessment:v1\0"


@pytest.fixture(scope="module")
def upstream() -> Upstream:
    return _build_upstream()


@pytest.fixture(scope="module")
def graph(upstream: Upstream) -> CoverageGraph:
    return _build_graph(upstream)


@pytest.fixture(scope="module")
def bundle(upstream: Upstream, graph: CoverageGraph) -> FreshBundle:
    return _build_bundle(upstream, (graph.target_a, graph.target_b))


@pytest.fixture(scope="module")
def chains(graph: CoverageGraph) -> tuple[FreshStatusRecordChainInputV1, ...]:
    return (
        _chain((graph.genesis_a, graph.target_a), (graph.target_a,)),
        _chain((graph.target_b,), (graph.target_b,)),
    )


def _receipt_kwargs(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    *,
    as_of: object = _DEFAULT_AS_OF,
) -> dict[str, Any]:
    if as_of is _DEFAULT_AS_OF:
        return _assessment_kwargs(upstream, bundle, chains)
    return _assessment_kwargs(upstream, bundle, chains, as_of=as_of)


def _build(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    *,
    as_of: object = _DEFAULT_AS_OF,
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
    return build_fresh_status_record_as_of_assessment_receipt_v1(
        **_receipt_kwargs(upstream, bundle, chains, as_of=as_of)
    )


def _verify_kwargs(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> dict[str, Any]:
    kwargs = _receipt_kwargs(upstream, bundle, chains)
    kwargs.pop("as_of")
    kwargs["receipt"] = receipt
    return kwargs


def _verify(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
    return verify_fresh_status_record_as_of_assessment_receipt_closure_v1(
        **_verify_kwargs(upstream, bundle, chains, receipt)
    )


def _assert_error(
    expected_code: str,
    callback: Any,
    *,
    assessment_code: str | None = None,
    joint_replay_code: str | None = None,
    coverage_code: str | None = None,
    replay_code: str | None = None,
) -> RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error:
    with pytest.raises(RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error) as captured:
        callback()
    error = captured.value
    assert error.code == expected_code
    assert error.assessment_code == assessment_code
    assert error.joint_replay_code == joint_replay_code
    assert error.coverage_code == coverage_code
    assert error.replay_code == replay_code
    assert str(error).startswith(f"{expected_code}:")
    return error


def _independent_canonical_document(
    value: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> bytes:
    return (
        json.dumps(
            value.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _independent_json_projection(value: object) -> object:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")  # type: ignore[union-attr]
    if isinstance(value, dict):
        return {key: _independent_json_projection(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return tuple(_independent_json_projection(item) for item in value)
    return value


def _independent_receipt_id(payload: dict[str, object]) -> str:
    raw = json.dumps(
        _independent_json_projection(payload),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"{_RECEIPT_ID_KIND}_{hashlib.sha256(raw).hexdigest()[:20]}"


def _independent_assessment_projection(
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> dict[str, object]:
    return {
        "assessment_profile": receipt.assessment_profile,
        "source_joint_replay_profile": receipt.source_joint_replay_profile,
        "source_record_chain_coverage_profile": (receipt.source_record_chain_coverage_profile),
        "source_chain_replay_profile": receipt.source_chain_replay_profile,
        "source_evidence_profile": receipt.source_evidence_profile,
        "source_evidence_policy_version": receipt.source_evidence_policy_version,
        "source_evidence_policy_document_sha256": (receipt.source_evidence_policy_document_sha256),
        "evidence_record_id": receipt.evidence_record_id,
        "evidence_record_sha256": receipt.evidence_record_sha256,
        "request_id": receipt.request_id,
        "request_sha256": receipt.request_sha256,
        "decision_id": receipt.decision_id,
        "decision_sha256": receipt.decision_sha256,
        "subject_closure": receipt.subject_closure.model_dump(mode="json"),
        "coverage_set_sha256": receipt.coverage_set_sha256,
        "joint_replay_sha256": receipt.joint_replay_sha256,
        "as_of": receipt.as_of,
        "evaluated_at": receipt.evaluated_at,
        "status_valid_until": receipt.status_valid_until,
        "window_semantics": receipt.window_semantics,
        "recorded_disposition": receipt.recorded_disposition,
        "recorded_blocking_categories": receipt.recorded_blocking_categories,
        "recorded_indeterminate_categories": receipt.recorded_indeterminate_categories,
        "as_of_window_state": receipt.as_of_window_state,
    }


def _independent_assessment_sha256(projection: dict[str, object]) -> str:
    canonical = json.dumps(
        projection,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(_ASSESSMENT_DOMAIN + canonical).hexdigest()


def _different_string(value: str) -> str:
    return value[:-1] + ("0" if value[-1:] != "0" else "1")


def _mutated_receipt_field_value(
    field: str,
    value: object,
) -> object:
    if field == "subject_closure":
        closure = cast(Any, value)
        return closure.model_copy(
            update={
                "use_scope_review_record_sha256": _different_string(
                    closure.use_scope_review_record_sha256
                )
            }
        )
    if field == "as_of":
        return _shift_seconds(cast(str, value), 1)
    if field == "evaluated_at":
        return _shift_seconds(cast(str, value), -1)
    if field == "status_valid_until":
        return _shift_seconds(cast(str, value), 1)
    if field in {"recorded_blocking_categories", "recorded_indeterminate_categories"}:
        categories = cast(tuple[str, ...], value)
        missing = next((item for item in CATEGORIES if item not in categories), None)
        return (*categories, missing) if missing is not None else categories[:-1]
    if field == "limitation_codes":
        return tuple(reversed(cast(tuple[str, ...], value)))
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if isinstance(value, str):
        return _different_string(value)
    raise AssertionError(f"no independent mutation defined for Receipt field {field}")


def test_builder_is_exact_deterministic_and_binds_the_live_slice_five_result(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    repeated = _build(upstream, bundle, tuple(reversed(chains)))
    assessment = assess_fresh_status_evidence_record_as_of_v1(
        **_receipt_kwargs(upstream, bundle, chains)
    )

    assert repeated == receipt
    assert receipt.profile == FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_V1_PROFILE
    assert receipt.profile == (
        "creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1"
    )
    assert receipt.schema_version == "1.0.0"
    assert receipt.document_type == (
        "sdc.creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1"
    )
    assert receipt.receipt_purpose == "HISTORICAL_EXPLICIT_AS_OF_ASSESSMENT_ONLY"
    assert receipt.reliance_requirement == ("FULL_CLOSURE_AND_EXPLICIT_AS_OF_REPLAY_REQUIRED")
    assert receipt.present_currentness_asserted is False
    assert receipt.source_assessment_result_type == assessment.result_type
    assert receipt.source_assessment_status == assessment.status
    for field in (
        "assessment_profile",
        "source_joint_replay_profile",
        "source_record_chain_coverage_profile",
        "source_chain_replay_profile",
        "source_evidence_profile",
        "source_evidence_policy_version",
        "source_evidence_policy_document_sha256",
        "evidence_record_id",
        "evidence_record_sha256",
        "request_id",
        "request_sha256",
        "decision_id",
        "decision_sha256",
        "subject_closure",
        "coverage_set_sha256",
        "joint_replay_sha256",
        "as_of",
        "evaluated_at",
        "status_valid_until",
        "window_semantics",
        "recorded_disposition",
        "recorded_blocking_categories",
        "recorded_indeterminate_categories",
        "as_of_window_state",
        "as_of_assessment_sha256",
        "provided_record_joint_replay_consistent",
        "explicit_as_of_window_assessment_consistent",
        "limitation_codes",
    ):
        assert getattr(receipt, field) == getattr(assessment, field), field
    assert receipt.status == "FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_RECORDED"


def test_receipt_id_binds_every_other_field_with_the_frozen_kind(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    expected = _independent_receipt_id(receipt.model_dump(mode="python", exclude={"receipt_id"}))
    assert receipt.receipt_id == expected
    assert receipt.receipt_id == (
        "real_asset_fresh_status_record_as_of_assessment_receipt_v1_48b7f828aad6defef254"
    )
    assert receipt.receipt_id.startswith(f"{_RECEIPT_ID_KIND}_")
    assert len(receipt.receipt_id.removeprefix(f"{_RECEIPT_ID_KIND}_")) == 20

    payload = receipt.model_dump(mode="python")
    payload["receipt_id"] = receipt.receipt_id[:-1] + (
        "0" if receipt.receipt_id[-1] != "0" else "1"
    )
    with pytest.raises(ValidationError, match="Receipt ID"):
        CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_validate(
            payload,
            strict=True,
        )


def test_assessment_digest_has_an_independent_literal_golden_and_binds_every_key(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    projection = _independent_assessment_projection(receipt)
    independent = _independent_assessment_sha256(projection)
    assert independent == receipt.as_of_assessment_sha256
    assert independent == "e841f69b7ee679bd10099bac512e6a80d0e55cca0a845cb732788c895610ba5b"

    changed_digests: list[str] = []
    for key, value in projection.items():
        if key == "subject_closure":
            changed_value = {**cast(dict[str, object], value), "closure_id": "drift"}
        elif isinstance(value, tuple):
            changed_value = (*value, "DRIFT")
        elif isinstance(value, str):
            changed_value = f"{value}_DRIFT"
        else:
            raise AssertionError(f"no assessment projection mutation for {key}")
        changed = _independent_assessment_sha256({**projection, key: changed_value})
        assert changed != independent, key
        changed_digests.append(changed)
    assert len(changed_digests) == len(projection)
    assert len(changed_digests) == len(set(changed_digests))


def test_every_non_id_receipt_field_changes_the_independent_stable_id_and_fails_replay(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    fields = tuple(
        field
        for field in CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_fields
        if field != "receipt_id"
    )
    assert fields

    for field in fields:
        current = getattr(receipt, field)
        changed = _mutated_receipt_field_value(field, current)
        payload = receipt.model_dump(mode="python", exclude={"receipt_id"})
        payload[field] = changed
        changed_id = _independent_receipt_id(payload)
        assert changed_id != receipt.receipt_id, field
        tampered = receipt.model_copy(update={field: changed, "receipt_id": changed_id})
        with pytest.raises(RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error) as captured:
            _verify(upstream, bundle, chains, tampered)
        assert captured.value.code in {
            "RECEIPT_CONTRACT_INVALID",
            "RECEIPT_REPLAY_MISMATCH",
        }, field


def test_canonical_document_is_independent_deterministic_utf8_lf_and_bounded(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    canonical = receipt_module._canonical_document(receipt)
    assert canonical == _independent_canonical_document(receipt)
    assert canonical.endswith(b"\n")
    assert not canonical.endswith(b"\n\n")
    assert not canonical.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in canonical
    assert json.loads(canonical) == receipt.model_dump(mode="json")
    assert len(canonical) <= FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
    assert FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES == 65_536


def test_receipt_is_strict_frozen_and_round_trip_stable(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    rebuilt = CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_validate(
        receipt.model_dump(mode="python"),
        strict=True,
    )
    assert rebuilt == receipt
    assert receipt_module._canonical_document(rebuilt) == receipt_module._canonical_document(
        receipt
    )
    with pytest.raises(ValidationError):
        receipt.execution_authorized = True  # type: ignore[misc]
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_validate(
            {**receipt.model_dump(mode="python"), "extra": "forbidden"},
            strict=True,
        )


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("present_currentness_asserted", 0),
        ("execution_authorized", 0),
        ("publication_authorized", 0),
        ("authorized_attempts", False),
        ("provider_requests", False),
    ),
)
def test_boolean_and_zero_authority_scalar_types_cannot_be_exchanged(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    field: str,
    invalid: object,
) -> None:
    payload = _build(upstream, bundle, chains).model_dump(mode="python")
    payload[field] = invalid
    with pytest.raises(ValidationError):
        CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_validate(
            payload,
            strict=True,
        )


def test_receipt_has_the_exact_minimal_field_set_and_no_embedded_sources(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    expected = {
        "schema_version",
        "document_type",
        "profile",
        "receipt_id",
        "receipt_purpose",
        "reliance_requirement",
        "present_currentness_asserted",
        "source_assessment_result_type",
        "source_assessment_status",
        "assessment_profile",
        "source_joint_replay_profile",
        "source_record_chain_coverage_profile",
        "source_chain_replay_profile",
        "source_evidence_profile",
        "source_evidence_policy_version",
        "source_evidence_policy_document_sha256",
        "evidence_record_id",
        "evidence_record_sha256",
        "request_id",
        "request_sha256",
        "decision_id",
        "decision_sha256",
        "subject_closure",
        "coverage_set_sha256",
        "joint_replay_sha256",
        "as_of",
        "evaluated_at",
        "status_valid_until",
        "window_semantics",
        "recorded_disposition",
        "recorded_blocking_categories",
        "recorded_indeterminate_categories",
        "as_of_window_state",
        "as_of_assessment_sha256",
        "provided_record_joint_replay_consistent",
        "explicit_as_of_window_assessment_consistent",
        "limitation_codes",
        "status",
        "evidence_scope",
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
    }
    assert set(CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_fields) == (
        expected
    )
    assert set(receipt.model_dump()) == expected
    assert {
        "record",
        "request",
        "instruction",
        "decision",
        "observations",
        "chains",
        "joint_replay_result",
        "assessment_result",
        "created_at",
        "issued_at",
        "verified_at",
        "previous_receipt_id",
        "previous_receipt_sha256",
        "receipt_sha256",
        "is_current",
        "rights_valid",
        "authorized",
    }.isdisjoint(expected)


def test_receipt_is_permanently_zero_authority_and_retains_all_limitations(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    assert receipt.limitation_codes == ALL_LIMITATIONS
    assert receipt.evidence_scope == "EXPLICIT_FINITE_BOUND_SET_ONLY"
    assert receipt.current_gate == "HUMAN_GATE"
    assert receipt.provider_state == "NOT_AUTHORIZED"
    assert receipt.usage_restriction == "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
    false_fields = (
        "present_currentness_asserted",
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
    assert all(getattr(receipt, field) is False for field in false_fields)
    assert all(type(getattr(receipt, field)) is bool for field in false_fields)
    assert all(getattr(receipt, field) == 0 for field in zero_fields)
    assert all(type(getattr(receipt, field)) is int for field in zero_fields)


@pytest.mark.parametrize(
    ("overrides", "expected_disposition"),
    (
        ({}, "NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET"),
        ({"HOLD_ACTIVE": "PRESENT"}, "BLOCKING_STATUS_RECORDED"),
        (
            {"POLICY_COMPATIBILITY_CURRENT": "UNKNOWN"},
            "INSUFFICIENT_OR_CONFLICTING_EVIDENCE",
        ),
    ),
)
@pytest.mark.parametrize(
    ("as_of_selector", "expected_state"),
    (
        ("evaluated", "WITHIN_EXPLICIT_BOUND_WINDOW"),
        ("expired", "EXPIRED_NOT_CURRENT"),
    ),
)
def test_all_dispositions_and_window_states_remain_historical_and_zero_authority(
    upstream: Upstream,
    overrides: dict[str, FreshStatusClaimValueV1],
    expected_disposition: str,
    as_of_selector: str,
    expected_state: str,
) -> None:
    local_bundle, local_chains = _complete_category_bundle(upstream, overrides)
    decision = local_bundle.record.decision
    as_of = decision.evaluated_at if as_of_selector == "evaluated" else decision.status_valid_until
    receipt = _build(upstream, local_bundle, local_chains, as_of=as_of)
    assert receipt.recorded_disposition == expected_disposition
    assert receipt.recorded_blocking_categories == decision.blocking_categories
    assert receipt.recorded_indeterminate_categories == decision.indeterminate_categories
    assert receipt.as_of_window_state == expected_state
    assert receipt.present_currentness_asserted is False
    assert receipt.provider_state == "NOT_AUTHORIZED"
    assert receipt.execution_authorized is False
    assert _verify(upstream, local_bundle, local_chains, receipt) == receipt


@pytest.mark.parametrize(
    ("position", "expected_state"),
    (
        ("evaluated", "WITHIN_EXPLICIT_BOUND_WINDOW"),
        ("last_second", "WITHIN_EXPLICIT_BOUND_WINDOW"),
        ("exclusive_end", "EXPIRED_NOT_CURRENT"),
        ("after_end", "EXPIRED_NOT_CURRENT"),
    ),
)
def test_receipt_preserves_the_exact_half_open_time_boundary(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    position: str,
    expected_state: str,
) -> None:
    decision = bundle.record.decision
    as_of_by_position = {
        "evaluated": decision.evaluated_at,
        "last_second": _shift_seconds(decision.status_valid_until, -1),
        "exclusive_end": decision.status_valid_until,
        "after_end": _shift_seconds(decision.status_valid_until, 1),
    }
    receipt = _build(upstream, bundle, chains, as_of=as_of_by_position[position])
    assert receipt.as_of_window_state == expected_state
    assert receipt.window_semantics == ("EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE")
    assert receipt.recorded_disposition == bundle.record.decision.disposition


def test_zero_length_record_horizon_is_an_expired_historical_receipt(
    upstream: Upstream,
) -> None:
    observation = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="ABSENT_WITH_EVIDENCE",
        label="receipt-zero-length-horizon",
        valid_from=VALID_FROM,
        valid_until=FRESH_EVALUATED_AT,
    )
    local_bundle = _build_bundle(upstream, (observation,))
    local_chains = (_chain((observation,), (observation,)),)
    receipt = _build(
        upstream,
        local_bundle,
        local_chains,
        as_of=FRESH_EVALUATED_AT,
    )
    assert receipt.evaluated_at == FRESH_EVALUATED_AT
    assert receipt.status_valid_until == receipt.evaluated_at
    assert receipt.as_of == receipt.evaluated_at
    assert receipt.as_of_window_state == "EXPIRED_NOT_CURRENT"
    assert receipt.present_currentness_asserted is False
    assert _verify(upstream, local_bundle, local_chains, receipt) == receipt


def test_each_distinct_explicit_as_of_produces_a_distinct_historical_receipt(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    first = _build(upstream, bundle, chains, as_of=bundle.record.decision.evaluated_at)
    second = _build(
        upstream,
        bundle,
        chains,
        as_of=_shift_seconds(bundle.record.decision.evaluated_at, 1),
    )
    assert first.as_of_window_state == second.as_of_window_state
    assert first.joint_replay_sha256 == second.joint_replay_sha256
    assert first.as_of_assessment_sha256 != second.as_of_assessment_sha256
    assert first.receipt_id != second.receipt_id


def test_builder_public_api_is_exact_complete_and_keyword_only() -> None:
    signature = inspect.signature(build_fresh_status_record_as_of_assessment_receipt_v1)
    expected = (
        "pack",
        "evidence",
        "reviewer_a",
        "reviewer_b",
        "pair_check",
        "qualification_request",
        "qualification_instruction",
        "qualification_decision",
        "rights_manifest",
        "use_plan",
        "use_scope_review_record",
        "record",
        "chains",
        "as_of",
    )
    assert tuple(signature.parameters) == expected
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert {
        "assessment_result",
        "joint_replay_result",
        "coverage_result",
        "replay_result",
        "now",
        "clock",
        "time_provider",
        "path",
        "reader",
        "writer",
        "callback",
        "provider",
        "credential",
        "runtime",
    }.isdisjoint(signature.parameters)


def test_verifier_public_api_is_exact_complete_and_has_no_second_as_of() -> None:
    signature = inspect.signature(verify_fresh_status_record_as_of_assessment_receipt_closure_v1)
    expected = (
        "pack",
        "evidence",
        "reviewer_a",
        "reviewer_b",
        "pair_check",
        "qualification_request",
        "qualification_instruction",
        "qualification_decision",
        "rights_manifest",
        "use_plan",
        "use_scope_review_record",
        "record",
        "chains",
        "receipt",
    )
    assert tuple(signature.parameters) == expected
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert {
        "as_of",
        "assessment_result",
        "joint_replay_result",
        "coverage_result",
        "replay_result",
        "now",
        "clock",
        "time_provider",
        "path",
        "reader",
        "writer",
        "callback",
        "provider",
        "credential",
        "runtime",
    }.isdisjoint(signature.parameters)


def test_builder_calls_public_slice_five_exactly_once_with_exact_input_objects(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    real_assess = receipt_module.assess_fresh_status_evidence_record_as_of_v1
    captured: list[dict[str, Any]] = []

    def wrapped_assess(**kwargs: Any) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
        captured.append(kwargs)
        return real_assess(**kwargs)

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        wrapped_assess,
    )
    kwargs = _receipt_kwargs(upstream, bundle, chains)
    receipt = build_fresh_status_record_as_of_assessment_receipt_v1(**kwargs)
    assert receipt.source_assessment_status.endswith("COMPLETED")
    assert len(captured) == 1
    assert set(captured[0]) == set(kwargs)
    for name, value in captured[0].items():
        assert value is kwargs[name], name


def test_verifier_calls_public_slice_five_exactly_once_using_only_receipt_as_of(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(
        upstream,
        bundle,
        chains,
        as_of=_shift_seconds(bundle.record.decision.evaluated_at, 1),
    )
    real_assess = receipt_module.assess_fresh_status_evidence_record_as_of_v1
    captured: list[dict[str, Any]] = []

    def wrapped_assess(**kwargs: Any) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
        captured.append(kwargs)
        return real_assess(**kwargs)

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        wrapped_assess,
    )
    kwargs = _verify_kwargs(upstream, bundle, chains, receipt)
    verified = verify_fresh_status_record_as_of_assessment_receipt_closure_v1(**kwargs)
    assert verified is receipt
    assert len(captured) == 1
    expected = _receipt_kwargs(upstream, bundle, chains, as_of=receipt.as_of)
    assert set(captured[0]) == set(expected)
    for name, value in captured[0].items():
        assert value is expected[name], name
    assert captured[0]["as_of"] is receipt.as_of


def test_verifier_never_calls_the_public_receipt_builder(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    calls = 0

    def unexpected_public_builder(**_: Any) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("verifier must compile internally after exactly one Slice 5 call")

    monkeypatch.setattr(
        receipt_module,
        "build_fresh_status_record_as_of_assessment_receipt_v1",
        unexpected_public_builder,
    )
    assert _verify(upstream, bundle, chains, receipt) is receipt
    assert calls == 0


def test_verifier_rejects_an_invalid_receipt_before_calling_slice_five(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    invalid = receipt.model_copy(update={"receipt_id": "invalid"})
    calls = 0

    def unexpected_assess(**_: Any) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("Slice 5 must not run before strict Receipt admission")

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        unexpected_assess,
    )
    _assert_error(
        "RECEIPT_CONTRACT_INVALID",
        lambda: _verify(upstream, bundle, chains, invalid),
    )
    assert calls == 0


def test_verifier_rejects_hidden_noncanonical_model_state_before_slice_five(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    canonical_before = _independent_canonical_document(receipt)
    object.__setattr__(
        receipt,
        "__pydantic_private__",
        {"synthetic_hidden_state": "not part of canonical JSON"},
    )
    assert _independent_canonical_document(receipt) == canonical_before
    calls = 0

    def unexpected_assess(**_: Any) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("Slice 5 must not run for hidden Receipt state")

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        unexpected_assess,
    )
    _assert_error(
        "RECEIPT_CONTRACT_INVALID",
        lambda: _verify(upstream, bundle, chains, receipt),
    )
    assert calls == 0


def test_verifier_rejects_non_receipt_objects_before_calling_slice_five(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    calls = 0

    def unexpected_assess(**_: Any) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("Slice 5 must not run for a non-Receipt")

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        unexpected_assess,
    )
    for invalid in ({}, None, b"{}", "{}", object()):
        _assert_error(
            "RECEIPT_CONTRACT_INVALID",
            lambda invalid=invalid: verify_fresh_status_record_as_of_assessment_receipt_closure_v1(
                **{
                    **{
                        key: value
                        for key, value in _receipt_kwargs(upstream, bundle, chains).items()
                        if key != "as_of"
                    },
                    "receipt": invalid,
                }
            ),
        )
    assert calls == 0


def test_fixed_category_order_is_contract_checked_before_replay(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
) -> None:
    local_bundle, local_chains = _complete_category_bundle(
        upstream,
        {"HOLD_ACTIVE": "PRESENT", "REVOCATION_EFFECTIVE": "PRESENT"},
    )
    receipt = _build(upstream, local_bundle, local_chains)
    assert receipt.recorded_blocking_categories == CATEGORIES[:2]
    reordered = receipt.model_copy(
        update={"recorded_blocking_categories": tuple(reversed(CATEGORIES[:2]))}
    )
    calls = 0

    def unexpected_assess(**_: Any) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("Slice 5 must not run for category-order drift")

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        unexpected_assess,
    )
    error = _assert_error(
        "RECEIPT_CONTRACT_INVALID",
        lambda: _verify(upstream, local_bundle, local_chains, reordered),
    )
    assert isinstance(error.__cause__, (ValidationError, ValueError))
    assert calls == 0


UPSTREAM_ID_FIELDS = (
    ("pack", "pack_id"),
    ("evidence", "bundle_id"),
    ("reviewer_a", "review_id"),
    ("reviewer_b", "review_id"),
    ("pair_check", "pair_check_id"),
    ("qualification_request", "request_id"),
    ("qualification_instruction", "instruction_id"),
    ("qualification_decision", "decision_id"),
    ("rights_manifest", "manifest_id"),
    ("use_plan", "plan_id"),
    ("use_scope_review_record", "record_id"),
)


@pytest.mark.parametrize(("parameter", "id_field"), UPSTREAM_ID_FIELDS)
def test_builder_freshly_replays_each_required_upstream_object(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    parameter: str,
    id_field: str,
) -> None:
    kwargs = _receipt_kwargs(upstream, bundle, chains)
    original = kwargs[parameter]
    old_id = cast(str, getattr(original, id_field))
    replacement = "0" if old_id[-1] != "0" else "1"
    kwargs[parameter] = original.model_copy(update={id_field: old_id[:-1] + replacement})
    _assert_error(
        "AS_OF_ASSESSMENT_REPLAY_FAILED",
        lambda: build_fresh_status_record_as_of_assessment_receipt_v1(**kwargs),
        assessment_code="RECORD_JOINT_REPLAY_FAILED",
        joint_replay_code="PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
    )


def test_record_cannot_be_spliced_to_another_chain_set(
    upstream: Upstream,
    bundle: FreshBundle,
) -> None:
    alternate = _build_alternate_upstream()
    alternate_graph = _build_graph(alternate)
    alternate_chains = (
        _chain(
            (alternate_graph.genesis_a, alternate_graph.target_a),
            (alternate_graph.target_a,),
        ),
        _chain((alternate_graph.target_b,), (alternate_graph.target_b,)),
    )
    _assert_error(
        "AS_OF_ASSESSMENT_REPLAY_FAILED",
        lambda: _build(upstream, bundle, alternate_chains),
        assessment_code="RECORD_JOINT_REPLAY_FAILED",
        joint_replay_code="RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        coverage_code="REQUEST_TARGET_NOT_IN_RECORD",
    )


def test_a_valid_receipt_cannot_be_spliced_to_another_complete_closure(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    alternate = _build_alternate_upstream()
    alternate_graph = _build_graph(alternate)
    alternate_bundle = _build_bundle(
        alternate,
        (alternate_graph.target_a, alternate_graph.target_b),
    )
    alternate_chains = (
        _chain(
            (alternate_graph.genesis_a, alternate_graph.target_a),
            (alternate_graph.target_a,),
        ),
        _chain((alternate_graph.target_b,), (alternate_graph.target_b,)),
    )
    alternate_receipt = _build(
        alternate,
        alternate_bundle,
        alternate_chains,
        as_of=FRESH_EVALUATED_AT,
    )
    assert alternate_receipt.receipt_id != _build(upstream, bundle, chains).receipt_id
    _assert_error(
        "RECEIPT_REPLAY_MISMATCH",
        lambda: _verify(upstream, bundle, chains, alternate_receipt),
    )


def test_receipt_tampering_is_not_repaired_or_rewritten(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    for field, value in (
        ("as_of_assessment_sha256", "0" * 64),
        ("joint_replay_sha256", "1" * 64),
        ("present_currentness_asserted", True),
        ("provider_state", "AUTHORIZED"),
        ("status", "DRIFTED"),
    ):
        tampered = receipt.model_copy(update={field: value})
        _assert_error(
            "RECEIPT_CONTRACT_INVALID",
            lambda tampered=tampered: _verify(upstream, bundle, chains, tampered),
        )
        assert getattr(tampered, field) == value


@pytest.mark.parametrize(
    "assessment_code",
    get_args(FreshStatusRecordAsOfAssessmentErrorCodeV1),
)
def test_all_slice_five_error_codes_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    assessment_code: FreshStatusRecordAsOfAssessmentErrorCodeV1,
) -> None:
    def fail_assessment(**_: Any) -> None:
        raise RealAssetFreshStatusRecordAsOfAssessmentV30Error(
            assessment_code,
            "synthetic Slice 5 failure",
        )

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        fail_assessment,
    )
    error = _assert_error(
        "AS_OF_ASSESSMENT_REPLAY_FAILED",
        lambda: _build(upstream, bundle, chains),
        assessment_code=assessment_code,
    )
    assert isinstance(error.__cause__, RealAssetFreshStatusRecordAsOfAssessmentV30Error)


@pytest.mark.parametrize(
    "joint_replay_code",
    get_args(FreshStatusRecordJointReplayErrorCodeV1),
)
def test_all_slice_four_codes_are_preserved_transitively(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    joint_replay_code: FreshStatusRecordJointReplayErrorCodeV1,
) -> None:
    def fail_assessment(**_: Any) -> None:
        raise RealAssetFreshStatusRecordAsOfAssessmentV30Error(
            "RECORD_JOINT_REPLAY_FAILED",
            "synthetic nested Slice 4 failure",
            joint_replay_code=joint_replay_code,
        )

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        fail_assessment,
    )
    _assert_error(
        "AS_OF_ASSESSMENT_REPLAY_FAILED",
        lambda: _build(upstream, bundle, chains),
        assessment_code="RECORD_JOINT_REPLAY_FAILED",
        joint_replay_code=joint_replay_code,
    )


@pytest.mark.parametrize(
    "coverage_code",
    get_args(FreshStatusRecordChainCoverageErrorCodeV1),
)
def test_all_slice_three_codes_are_preserved_transitively(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    coverage_code: FreshStatusRecordChainCoverageErrorCodeV1,
) -> None:
    def fail_assessment(**_: Any) -> None:
        raise RealAssetFreshStatusRecordAsOfAssessmentV30Error(
            "RECORD_JOINT_REPLAY_FAILED",
            "synthetic nested Slice 3 failure",
            joint_replay_code="RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
            coverage_code=coverage_code,
        )

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        fail_assessment,
    )
    _assert_error(
        "AS_OF_ASSESSMENT_REPLAY_FAILED",
        lambda: _build(upstream, bundle, chains),
        assessment_code="RECORD_JOINT_REPLAY_FAILED",
        joint_replay_code="RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        coverage_code=coverage_code,
    )


@pytest.mark.parametrize("replay_code", get_args(FreshStatusChainReplayErrorCodeV1))
def test_all_slice_two_codes_are_preserved_transitively(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    replay_code: FreshStatusChainReplayErrorCodeV1,
) -> None:
    def fail_assessment(**_: Any) -> None:
        raise RealAssetFreshStatusRecordAsOfAssessmentV30Error(
            "RECORD_JOINT_REPLAY_FAILED",
            "synthetic nested Slice 2 failure",
            joint_replay_code="RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
            coverage_code="CHAIN_REPLAY_FAILED",
            replay_code=replay_code,
        )

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        fail_assessment,
    )
    _assert_error(
        "AS_OF_ASSESSMENT_REPLAY_FAILED",
        lambda: _build(upstream, bundle, chains),
        assessment_code="RECORD_JOINT_REPLAY_FAILED",
        joint_replay_code="RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        coverage_code="CHAIN_REPLAY_FAILED",
        replay_code=replay_code,
    )


def test_receipt_contract_failure_precedes_every_slice_five_failure(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _build(upstream, bundle, chains)
    invalid = receipt.model_copy(update={"receipt_id": "invalid"})
    calls = 0

    def lower_failure(**_: Any) -> None:
        nonlocal calls
        calls += 1
        raise RealAssetFreshStatusRecordAsOfAssessmentV30Error(
            "RECORD_JOINT_REPLAY_FAILED",
            "must remain unreachable",
        )

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        lower_failure,
    )
    _assert_error(
        "RECEIPT_CONTRACT_INVALID",
        lambda: _verify(upstream, bundle, chains, invalid),
    )
    assert calls == 0


def test_unrelated_slice_five_runtime_error_is_not_reclassified(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    def fail_with_runtime(**_: Any) -> None:
        raise RuntimeError("synthetic unrelated Slice 5 runtime failure")

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        fail_with_runtime,
    )
    with pytest.raises(RuntimeError, match="synthetic unrelated Slice 5 runtime failure") as error:
        _build(upstream, bundle, chains)
    assert type(error.value) is RuntimeError


@pytest.mark.parametrize("operation", ("build", "verify"))
@pytest.mark.parametrize("failure_type", (MemoryError, KeyboardInterrupt))
def test_process_control_and_memory_failures_propagate_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    operation: str,
    failure_type: type[BaseException],
) -> None:
    receipt = _build(upstream, bundle, chains) if operation == "verify" else None
    failure = failure_type("synthetic non-domain failure")

    def fail_assessment(**_: Any) -> None:
        raise failure

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        fail_assessment,
    )
    with pytest.raises(failure_type) as captured:
        if operation == "build":
            _build(upstream, bundle, chains)
        else:
            assert receipt is not None
            _verify(upstream, bundle, chains, receipt)
    assert captured.value is failure


def test_wrong_slice_five_result_type_fails_after_one_live_call(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    calls = 0

    def wrong_result(**_: Any) -> object:
        nonlocal calls
        calls += 1
        return object()

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        wrong_result,
    )
    _assert_error(
        "ASSESSMENT_RESULT_INCONSISTENT",
        lambda: _build(upstream, bundle, chains),
    )
    assert calls == 1


def test_constructed_detached_slice_five_result_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    real_result = assess_fresh_status_evidence_record_as_of_v1(
        **_receipt_kwargs(upstream, bundle, chains)
    )
    detached = FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_construct(
        **{
            field: getattr(real_result, field)
            for field in FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_fields
        }
    )
    calls = 0

    def detached_result(**_: Any) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
        nonlocal calls
        calls += 1
        return detached

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        detached_result,
    )
    _assert_error(
        "ASSESSMENT_RESULT_INCONSISTENT",
        lambda: _build(upstream, bundle, chains),
    )
    assert calls == 1


def test_detached_slice_five_result_with_forged_token_and_digest_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    real_result = assess_fresh_status_evidence_record_as_of_v1(
        **_receipt_kwargs(upstream, bundle, chains)
    )
    detached = FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_construct(
        **{
            field: getattr(real_result, field)
            for field in FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_fields
        }
    )
    detached._verification_provenance = (
        object(),
        receipt_module._assessment_result_provenance_sha256(detached),
    )
    calls = 0

    def detached_result(**_: Any) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
        nonlocal calls
        calls += 1
        return detached

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        detached_result,
    )
    _assert_error(
        "ASSESSMENT_RESULT_INCONSISTENT",
        lambda: _build(upstream, bundle, chains),
    )
    assert calls == 1


def test_internal_receipt_id_failure_is_not_misreported_as_replay_failure(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    calls = 0
    real_assess = receipt_module.assess_fresh_status_evidence_record_as_of_v1

    def counted_assess(**kwargs: Any) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
        nonlocal calls
        calls += 1
        return real_assess(**kwargs)

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        counted_assess,
    )
    monkeypatch.setattr(receipt_module, "stable_id", lambda *_args, **_kwargs: "invalid")
    _assert_error(
        "INTERNAL_RECEIPT_INCONSISTENCY",
        lambda: _build(upstream, bundle, chains),
    )
    assert calls == 1


def test_canonical_size_overflow_fails_closed_after_one_slice_five_call(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    calls = 0
    real_assess = receipt_module.assess_fresh_status_evidence_record_as_of_v1

    def counted_assess(**kwargs: Any) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
        nonlocal calls
        calls += 1
        return real_assess(**kwargs)

    monkeypatch.setattr(
        receipt_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        counted_assess,
    )
    monkeypatch.setattr(
        receipt_module,
        "_canonical_document",
        lambda _value: b"x" * (FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES + 1),
    )
    _assert_error(
        "INTERNAL_RECEIPT_INCONSISTENCY",
        lambda: _build(upstream, bundle, chains),
    )
    assert calls == 1


def test_error_literal_preserves_the_frozen_five_stage_order() -> None:
    assert get_args(FreshStatusRecordAsOfAssessmentReceiptErrorCodeV1) == (
        "RECEIPT_CONTRACT_INVALID",
        "AS_OF_ASSESSMENT_REPLAY_FAILED",
        "ASSESSMENT_RESULT_INCONSISTENT",
        "INTERNAL_RECEIPT_INCONSISTENCY",
        "RECEIPT_REPLAY_MISMATCH",
    )


def test_public_surface_is_exact_and_has_no_parser_extractor_or_execution_entry() -> None:
    assert tuple(receipt_module.__all__) == (
        "FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_V1_PROFILE",
        "FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES",
        "FreshStatusRecordAsOfAssessmentReceiptErrorCodeV1",
        "CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1",
        "RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error",
        "build_fresh_status_record_as_of_assessment_receipt_v1",
        "verify_fresh_status_record_as_of_assessment_receipt_closure_v1",
    )
    assert not any(
        name.lower().startswith(
            (
                "authorize",
                "cli_",
                "extract_",
                "file_",
                "finalize_",
                "parse_",
                "path_",
                "provider_",
                "read_",
                "write_",
            )
        )
        for name in receipt_module.__all__
    )


def test_receipt_remains_the_frozen_index_67_registered_schema_contract() -> None:
    assert len(MODELS) == 70
    assert len({model.__name__ for model in MODELS}) == 70
    assert MODELS[67] is CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
    assert FreshStatusEvidenceRecordAsOfAssessmentResultV1 not in MODELS

    schema_path = Path(
        "schemas/CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.schema.json"
    )
    assert schema_path.is_file()
    expected = (
        json.dumps(
            CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_json_schema(),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    assert schema_path.read_text(encoding="utf-8") == expected
    assert not Path("schemas/FreshStatusEvidenceRecordAsOfAssessmentResultV1.schema.json").exists()


def test_production_module_is_ast_locked_to_pure_memory_and_explicit_time() -> None:
    source = receipt_module.__file__
    assert source is not None
    tree = ast.parse(Path(source).read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    called_names: set[str] = set()
    loaded_names: set[str] = set()

    def dotted_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = dotted_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
            imported_modules.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name:
                called_names.add(name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            loaded_names.add(node.id)

    assert {module.split(".", maxsplit=1)[0] for module in imported_modules} <= {
        "__future__",
        "datetime",
        "hashlib",
        "json",
        "pydantic",
        "re",
        "sdc",
        "typing",
    }
    forbidden_components = {
        "argparse",
        "asyncio",
        "click",
        "credential",
        "database",
        "db",
        "glob",
        "http",
        "httpx",
        "importlib",
        "io",
        "keyring",
        "locale",
        "logging",
        "mmap",
        "multiprocessing",
        "os",
        "pathlib",
        "persistence",
        "pickle",
        "platform",
        "provider",
        "queue",
        "random",
        "requests",
        "runtime",
        "secrets",
        "shelve",
        "shutil",
        "socket",
        "sqlite3",
        "subprocess",
        "sys",
        "tempfile",
        "threading",
        "time",
        "typer",
        "urllib",
        "uuid",
        "worker",
        "zoneinfo",
    }

    def has_forbidden_component(value: str) -> bool:
        return any(
            component == forbidden or component.startswith(f"{forbidden}_")
            for component in value.lower().split(".")
            for forbidden in forbidden_components
        )

    assert not any(has_forbidden_component(module) for module in imported_modules)
    assert not any(has_forbidden_component(name) for name in called_names)
    assert {
        "__import__",
        "builtins.compile",
        "builtins.eval",
        "builtins.exec",
        "builtins.input",
        "builtins.open",
        "compile",
        "eval",
        "exec",
        "input",
        "open",
    }.isdisjoint(called_names)
    assert not any(
        name.endswith(
            (
                ".now",
                ".utcnow",
                ".today",
                ".time",
                ".monotonic",
                ".perf_counter",
                ".process_time",
                ".sleep",
                ".fromisoformat",
                ".fromtimestamp",
                ".utcfromtimestamp",
            )
        )
        for name in called_names
    )
    assert "__file__" not in loaded_names
    assert not any(
        isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith))
        for node in ast.walk(tree)
    )
