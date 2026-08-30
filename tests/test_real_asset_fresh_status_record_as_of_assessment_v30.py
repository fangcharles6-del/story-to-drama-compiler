from __future__ import annotations

import ast
import hashlib
import inspect
import json
from datetime import UTC, datetime, timedelta
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
    _observations_for_claims,
    _sha,
)
from test_real_asset_fresh_status_record_chain_coverage_v30 import (
    FRESH_STATUS_V30_SCHEMA_SHA256,
    CoverageGraph,
    _build_graph,
    _chain,
)
from test_real_asset_fresh_status_record_joint_replay_v30 import (
    _build_alternate_upstream,
)
from test_schemas import PRE_FRESH_STATUS_V30_SCHEMA_SHA256

import sdc.real_asset_fresh_status_record_as_of_assessment_v30 as assessment_module
from sdc.real_asset_fresh_status_chain_replay_v30 import (
    FreshStatusChainReplayErrorCodeV1,
    FreshStatusExplicitFiniteChainReplayResultV1,
)
from sdc.real_asset_fresh_status_record_as_of_assessment_v30 import (
    FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1,
    FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE,
    FreshStatusAsOfWindowStateV1,
    FreshStatusEvidenceRecordAsOfAssessmentResultV1,
    FreshStatusRecordAsOfAssessmentErrorCodeV1,
    RealAssetFreshStatusRecordAsOfAssessmentV30Error,
    assess_fresh_status_evidence_record_as_of_v1,
)
from sdc.real_asset_fresh_status_record_chain_coverage_v30 import (
    FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES,
    FreshStatusEvidenceRecordChainCoverageResultV1,
    FreshStatusRecordChainCoverageErrorCodeV1,
    FreshStatusRecordChainCoverageSummaryV1,
    FreshStatusRecordChainInputV1,
)
from sdc.real_asset_fresh_status_record_joint_replay_v30 import (
    FreshStatusEvidenceRecordJointReplayResultV1,
    FreshStatusRecordJointReplayErrorCodeV1,
    RealAssetFreshStatusRecordJointReplayV30Error,
    verify_fresh_status_evidence_record_joint_replay_v1,
)

ASSESSMENT_DOMAIN = b"sdc:creative-sample-real-asset-fresh-status-record-as-of-assessment:v1\0"
_DEFAULT_AS_OF = object()


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


def _assessment_kwargs(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    *,
    as_of: object = _DEFAULT_AS_OF,
) -> dict[str, Any]:
    closure = upstream.closure
    return {
        "pack": closure.pack,
        "evidence": closure.evidence,
        "reviewer_a": closure.reviewer_a,
        "reviewer_b": closure.reviewer_b,
        "pair_check": closure.pair_check,
        "qualification_request": closure.request,
        "qualification_instruction": closure.instruction,
        "qualification_decision": closure.decision,
        "rights_manifest": closure.manifest,
        "use_plan": upstream.use_plan,
        "use_scope_review_record": upstream.use_scope_record,
        "record": bundle.record,
        "chains": chains,
        "as_of": FRESH_EVALUATED_AT if as_of is _DEFAULT_AS_OF else as_of,
    }


def _assess(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    *,
    as_of: object = _DEFAULT_AS_OF,
) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1:
    return assess_fresh_status_evidence_record_as_of_v1(
        **_assessment_kwargs(upstream, bundle, chains, as_of=as_of)
    )


def _assert_error(
    expected_code: str,
    callback: Any,
    *,
    joint_replay_code: str | None = None,
    coverage_code: str | None = None,
    replay_code: str | None = None,
) -> RealAssetFreshStatusRecordAsOfAssessmentV30Error:
    with pytest.raises(RealAssetFreshStatusRecordAsOfAssessmentV30Error) as captured:
        callback()
    error = captured.value
    assert error.code == expected_code
    assert error.joint_replay_code == joint_replay_code
    assert error.coverage_code == coverage_code
    assert error.replay_code == replay_code
    assert str(error).startswith(f"{expected_code}:")
    return error


def _shift_seconds(value: str, seconds: int) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return (parsed + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _complete_category_bundle(
    upstream: Upstream,
    overrides: dict[str, FreshStatusClaimValueV1],
) -> tuple[FreshBundle, tuple[FreshStatusRecordChainInputV1, ...]]:
    observations = _observations_for_claims(upstream, overrides)
    local_bundle = _build_bundle(upstream, observations)
    local_chains = tuple(_chain((item,), (item,)) for item in observations)
    return local_bundle, local_chains


def test_assessment_is_exact_deterministic_and_bound_to_the_fresh_joint_replay(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    result = _assess(upstream, bundle, chains)
    reordered = _assess(
        upstream,
        bundle,
        tuple(
            chain.model_copy(update={"observations": tuple(reversed(chain.observations))})
            for chain in reversed(chains)
        ),
    )
    joint = verify_fresh_status_evidence_record_joint_replay_v1(
        **{
            key: value
            for key, value in _assessment_kwargs(upstream, bundle, chains).items()
            if key != "as_of"
        }
    )

    assert reordered == result
    assert result.assessment_profile == FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE
    assert result.assessment_profile == (
        "creative-sample-real-asset-fresh-status-record-as-of-assessment-v1"
    )
    assert result.source_joint_replay_profile == joint.joint_replay_profile
    assert result.source_record_chain_coverage_profile == joint.source_record_chain_coverage_profile
    assert result.source_chain_replay_profile == joint.source_chain_replay_profile
    assert result.source_evidence_profile == joint.source_evidence_profile
    assert result.source_evidence_policy_version == joint.source_evidence_policy_version
    assert (
        result.source_evidence_policy_document_sha256
        == joint.source_evidence_policy_document_sha256
    )
    assert result.evidence_record_id == bundle.record.record_id == joint.evidence_record_id
    assert result.evidence_record_sha256 == _sha(bundle.record) == joint.evidence_record_sha256
    assert result.request_id == bundle.record.request.request_id == joint.request_id
    assert result.request_sha256 == bundle.record.request_sha256 == joint.request_sha256
    assert result.decision_id == bundle.record.decision.decision_id
    assert result.decision_sha256 == _sha(bundle.record.decision)
    assert result.subject_closure == bundle.record.subject_closure == joint.subject_closure
    assert result.coverage_set_sha256 == joint.coverage_set_sha256
    assert result.joint_replay_sha256 == joint.joint_replay_sha256
    assert result.as_of == FRESH_EVALUATED_AT
    assert result.evaluated_at == bundle.record.decision.evaluated_at
    assert result.status_valid_until == bundle.record.decision.status_valid_until
    assert result.window_semantics == FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1
    assert result.window_semantics == ("EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE")
    assert result.recorded_disposition == bundle.record.decision.disposition
    assert result.recorded_blocking_categories == bundle.record.decision.blocking_categories
    assert (
        result.recorded_indeterminate_categories == bundle.record.decision.indeterminate_categories
    )
    assert result.as_of_window_state == "WITHIN_EXPLICIT_BOUND_WINDOW"
    assert result.provided_record_joint_replay_consistent is True
    assert result.explicit_as_of_window_assessment_consistent is True


@pytest.mark.parametrize(
    ("position", "expected_state"),
    (
        ("evaluated", "WITHIN_EXPLICIT_BOUND_WINDOW"),
        ("last_second", "WITHIN_EXPLICIT_BOUND_WINDOW"),
        ("exclusive_end", "EXPIRED_NOT_CURRENT"),
        ("after_end", "EXPIRED_NOT_CURRENT"),
    ),
)
def test_half_open_as_of_boundaries_are_exact(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    position: str,
    expected_state: FreshStatusAsOfWindowStateV1,
) -> None:
    evaluated_at = bundle.record.decision.evaluated_at
    status_valid_until = bundle.record.decision.status_valid_until
    values = {
        "evaluated": evaluated_at,
        "last_second": _shift_seconds(status_valid_until, -1),
        "exclusive_end": status_valid_until,
        "after_end": _shift_seconds(status_valid_until, 1),
    }
    result = _assess(upstream, bundle, chains, as_of=values[position])
    assert result.as_of_window_state == expected_state
    assert result.recorded_disposition == bundle.record.decision.disposition
    assert result.recorded_blocking_categories == bundle.record.decision.blocking_categories
    assert (
        result.recorded_indeterminate_categories == bundle.record.decision.indeterminate_categories
    )


def test_as_of_before_evaluation_fails_instead_of_replaying_history(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    _assert_error(
        "AS_OF_PRECEDES_RECORD_EVALUATION",
        lambda: _assess(
            upstream,
            bundle,
            chains,
            as_of=_shift_seconds(bundle.record.decision.evaluated_at, -1),
        ),
    )


def test_zero_length_record_horizon_is_expired_at_evaluation(
    upstream: Upstream,
) -> None:
    expired_observation = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="ABSENT_WITH_EVIDENCE",
        label="as-of-zero-length-horizon",
        valid_from=VALID_FROM,
        valid_until=FRESH_EVALUATED_AT,
    )
    local_bundle = _build_bundle(upstream, (expired_observation,))
    local_chains = (_chain((expired_observation,), (expired_observation,)),)
    assert local_bundle.record.decision.status_valid_until == FRESH_EVALUATED_AT

    result = _assess(upstream, local_bundle, local_chains, as_of=FRESH_EVALUATED_AT)
    assert result.as_of_window_state == "EXPIRED_NOT_CURRENT"
    _assert_error(
        "AS_OF_PRECEDES_RECORD_EVALUATION",
        lambda: _assess(
            upstream,
            local_bundle,
            local_chains,
            as_of=_shift_seconds(FRESH_EVALUATED_AT, -1),
        ),
    )


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
def test_window_state_never_reclassifies_the_recorded_disposition(
    upstream: Upstream,
    overrides: dict[str, FreshStatusClaimValueV1],
    expected_disposition: str,
    as_of_selector: str,
    expected_state: FreshStatusAsOfWindowStateV1,
) -> None:
    local_bundle, local_chains = _complete_category_bundle(upstream, overrides)
    decision = local_bundle.record.decision
    as_of = decision.evaluated_at if as_of_selector == "evaluated" else decision.status_valid_until
    result = _assess(upstream, local_bundle, local_chains, as_of=as_of)
    assert decision.disposition == expected_disposition
    assert result.recorded_disposition == expected_disposition
    assert result.recorded_blocking_categories == decision.blocking_categories
    assert result.recorded_indeterminate_categories == decision.indeterminate_categories
    assert result.as_of_window_state == expected_state
    assert "REALITY_CURRENTNESS_NOT_PROVEN" in result.limitation_codes


@pytest.mark.parametrize(
    "valid",
    (
        "2028-02-29T00:00:00Z",
        "9999-12-31T23:59:59Z",
    ),
)
def test_canonical_calendar_valid_as_of_values_are_accepted(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    valid: str,
) -> None:
    result = _assess(upstream, bundle, chains, as_of=valid)
    assert result.as_of == valid
    assert result.as_of_window_state == "EXPIRED_NOT_CURRENT"


@pytest.mark.parametrize(
    "invalid",
    (
        "",
        "2026-08-20T00:03:00",
        "2026-08-20 00:03:00Z",
        "2026-08-20T00:03:00z",
        "2026-08-20T00:03:00.0Z",
        "2026-08-20T00:03:00+00:00",
        " 2026-08-20T00:03:00Z",
        "2026-08-20T00:03:00Z ",
        "2026-08-20T00:03:00Z\n",
        "2026-08-20T00:03:00Z\0",
        "２０２６-08-20T00:03:00Z",
        "0000-01-01T00:00:00Z",
        "2027-02-29T00:00:00Z",
        "2026-00-20T00:03:00Z",
        "2026-13-20T00:03:00Z",
        "2026-08-00T00:03:00Z",
        "2026-08-32T00:03:00Z",
        "2026-08-20T24:03:00Z",
        "2026-08-20T00:60:00Z",
        "2026-08-20T00:03:60Z",
        "2" * 19,
        "2" * 21,
    ),
)
def test_noncanonical_or_impossible_as_of_fails_closed_before_replay(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    invalid: str,
) -> None:
    calls = 0

    def unexpected_replay(**_: Any) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("Slice 4 must not run for an invalid as_of")

    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        unexpected_replay,
    )
    _assert_error(
        "AS_OF_CONTRACT_INVALID",
        lambda: _assess(upstream, bundle, chains, as_of=invalid),
    )
    assert calls == 0


@pytest.mark.parametrize("invalid", (None, b"2026-08-20T00:03:00Z", 0, False))
def test_as_of_requires_an_exact_string_without_coercion(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    invalid: object,
) -> None:
    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        lambda **_: pytest.fail("Slice 4 must not run for a non-string as_of"),
    )
    _assert_error(
        "AS_OF_CONTRACT_INVALID",
        lambda: _assess(upstream, bundle, chains, as_of=invalid),
    )


def test_as_of_rejects_string_subclasses_and_never_calls_str(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    class StringSubclass(str):
        pass

    class NoStringCoercion:
        def __str__(self) -> str:
            raise AssertionError("as_of must not be coerced")

    for invalid in (
        StringSubclass(FRESH_EVALUATED_AT),
        NoStringCoercion(),
    ):
        _assert_error(
            "AS_OF_CONTRACT_INVALID",
            lambda invalid=invalid: _assess(upstream, bundle, chains, as_of=invalid),
        )


def test_public_api_requires_the_complete_slice_four_input_plus_as_of() -> None:
    signature = inspect.signature(assess_fresh_status_evidence_record_as_of_v1)
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
        "joint_replay_result",
        "coverage_result",
        "observations",
        "subject_closure",
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


def test_success_calls_slice_four_once_with_the_exact_input_objects(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    real_replay = assessment_module.verify_fresh_status_evidence_record_joint_replay_v1
    captured: list[dict[str, Any]] = []

    def wrapped_replay(**kwargs: Any) -> FreshStatusEvidenceRecordJointReplayResultV1:
        captured.append(kwargs)
        return real_replay(**kwargs)

    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        wrapped_replay,
    )
    kwargs = _assessment_kwargs(upstream, bundle, chains)
    result = assess_fresh_status_evidence_record_as_of_v1(**kwargs)
    assert result.provided_record_joint_replay_consistent is True
    assert len(captured) == 1
    assert set(captured[0]) == set(kwargs) - {"as_of"}
    for name, value in captured[0].items():
        assert value is kwargs[name], name


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
def test_each_required_upstream_object_is_freshly_replayed(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    parameter: str,
    id_field: str,
) -> None:
    kwargs = _assessment_kwargs(upstream, bundle, chains)
    original = kwargs[parameter]
    old_id = cast(str, getattr(original, id_field))
    replacement = "0" if old_id[-1] != "0" else "1"
    kwargs[parameter] = original.model_copy(update={id_field: old_id[:-1] + replacement})
    _assert_error(
        "RECORD_JOINT_REPLAY_FAILED",
        lambda: assess_fresh_status_evidence_record_as_of_v1(**kwargs),
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
        "RECORD_JOINT_REPLAY_FAILED",
        lambda: _assess(upstream, bundle, alternate_chains),
        joint_replay_code="RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        coverage_code="REQUEST_TARGET_NOT_IN_RECORD",
    )


def test_a_real_but_unrelated_slice_four_result_is_rejected_by_joint_anchors(
    monkeypatch: pytest.MonkeyPatch,
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
    alternate_joint = verify_fresh_status_evidence_record_joint_replay_v1(
        **{
            key: value
            for key, value in _assessment_kwargs(
                alternate,
                alternate_bundle,
                alternate_chains,
            ).items()
            if key != "as_of"
        }
    )
    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        lambda **_: alternate_joint,
    )
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: _assess(
            upstream,
            bundle,
            chains,
            as_of=_shift_seconds(bundle.record.decision.evaluated_at, -1),
        ),
    )


@pytest.mark.parametrize(
    "joint_replay_code",
    get_args(FreshStatusRecordJointReplayErrorCodeV1),
)
def test_all_slice_four_error_codes_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    joint_replay_code: FreshStatusRecordJointReplayErrorCodeV1,
) -> None:
    def fail_replay(**_: Any) -> None:
        raise RealAssetFreshStatusRecordJointReplayV30Error(
            joint_replay_code,
            "synthetic Slice 4 failure",
        )

    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        fail_replay,
    )
    error = _assert_error(
        "RECORD_JOINT_REPLAY_FAILED",
        lambda: _assess(upstream, bundle, chains),
        joint_replay_code=joint_replay_code,
    )
    assert isinstance(error.__cause__, RealAssetFreshStatusRecordJointReplayV30Error)


@pytest.mark.parametrize(
    "coverage_code",
    get_args(FreshStatusRecordChainCoverageErrorCodeV1),
)
def test_all_slice_three_error_codes_are_preserved_transitively(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    coverage_code: FreshStatusRecordChainCoverageErrorCodeV1,
) -> None:
    def fail_replay(**_: Any) -> None:
        raise RealAssetFreshStatusRecordJointReplayV30Error(
            "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
            "synthetic nested Slice 3 failure",
            coverage_code=coverage_code,
        )

    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        fail_replay,
    )
    _assert_error(
        "RECORD_JOINT_REPLAY_FAILED",
        lambda: _assess(upstream, bundle, chains),
        joint_replay_code="RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        coverage_code=coverage_code,
    )


@pytest.mark.parametrize("replay_code", get_args(FreshStatusChainReplayErrorCodeV1))
def test_all_slice_two_error_codes_are_preserved_transitively(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    replay_code: FreshStatusChainReplayErrorCodeV1,
) -> None:
    def fail_replay(**_: Any) -> None:
        raise RealAssetFreshStatusRecordJointReplayV30Error(
            "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
            "synthetic nested Slice 2 failure",
            coverage_code="CHAIN_REPLAY_FAILED",
            replay_code=replay_code,
        )

    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        fail_replay,
    )
    _assert_error(
        "RECORD_JOINT_REPLAY_FAILED",
        lambda: _assess(upstream, bundle, chains),
        joint_replay_code="RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        coverage_code="CHAIN_REPLAY_FAILED",
        replay_code=replay_code,
    )


def test_invalid_as_of_precedes_every_lower_layer_failure(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    replay_called = False

    def unexpected_replay(**_: Any) -> None:
        nonlocal replay_called
        replay_called = True
        raise RealAssetFreshStatusRecordJointReplayV30Error(
            "INTERNAL_RESULT_INCONSISTENCY",
            "must remain unreachable",
        )

    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        unexpected_replay,
    )
    _assert_error(
        "AS_OF_CONTRACT_INVALID",
        lambda: _assess(upstream, bundle, chains, as_of="not-a-time"),
    )
    assert replay_called is False


def test_slice_four_failure_precedes_as_of_relation_to_the_record(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    def fail_replay(**_: Any) -> None:
        raise RealAssetFreshStatusRecordJointReplayV30Error(
            "INTERNAL_RESULT_INCONSISTENCY",
            "synthetic replay-before-time failure",
        )

    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        fail_replay,
    )
    _assert_error(
        "RECORD_JOINT_REPLAY_FAILED",
        lambda: _assess(
            upstream,
            bundle,
            chains,
            as_of=_shift_seconds(bundle.record.decision.evaluated_at, -1),
        ),
        joint_replay_code="INTERNAL_RESULT_INCONSISTENCY",
    )


def test_as_of_precedes_evaluation_before_digest_or_result_processing(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    digest_called = False

    def unexpected_digest(**_: Any) -> str:
        nonlocal digest_called
        digest_called = True
        return "0" * 64

    monkeypatch.setattr(assessment_module, "_as_of_assessment_sha256", unexpected_digest)
    _assert_error(
        "AS_OF_PRECEDES_RECORD_EVALUATION",
        lambda: _assess(
            upstream,
            bundle,
            chains,
            as_of=_shift_seconds(bundle.record.decision.evaluated_at, -1),
        ),
    )
    assert digest_called is False


def test_unrelated_runtime_error_from_slice_four_is_not_reclassified(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    def fail_with_runtime(**_: Any) -> None:
        raise RuntimeError("synthetic unrelated Slice 4 runtime failure")

    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        fail_with_runtime,
    )
    with pytest.raises(RuntimeError, match="synthetic unrelated Slice 4 runtime failure") as error:
        _assess(upstream, bundle, chains)
    assert type(error.value) is RuntimeError


def test_unrelated_runtime_error_from_digest_is_not_reclassified(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    def fail_with_runtime(**_: Any) -> str:
        raise RuntimeError("synthetic unrelated digest runtime failure")

    monkeypatch.setattr(assessment_module, "_as_of_assessment_sha256", fail_with_runtime)
    with pytest.raises(RuntimeError, match="synthetic unrelated digest runtime failure") as error:
        _assess(upstream, bundle, chains)
    assert type(error.value) is RuntimeError


def test_invalid_derived_result_is_classified_only_after_successful_replay(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    replay_calls = 0
    real_replay = assessment_module.verify_fresh_status_evidence_record_joint_replay_v1

    def counted_replay(**kwargs: Any) -> FreshStatusEvidenceRecordJointReplayResultV1:
        nonlocal replay_calls
        replay_calls += 1
        return real_replay(**kwargs)

    monkeypatch.setattr(
        assessment_module,
        "verify_fresh_status_evidence_record_joint_replay_v1",
        counted_replay,
    )
    monkeypatch.setattr(
        assessment_module,
        "_as_of_assessment_sha256",
        lambda **_: "not-a-sha256",
    )
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: _assess(upstream, bundle, chains),
    )
    assert replay_calls == 1


def test_error_literal_preserves_the_frozen_four_stage_order() -> None:
    assert get_args(FreshStatusRecordAsOfAssessmentErrorCodeV1) == (
        "AS_OF_CONTRACT_INVALID",
        "RECORD_JOINT_REPLAY_FAILED",
        "AS_OF_PRECEDES_RECORD_EVALUATION",
        "INTERNAL_RESULT_INCONSISTENCY",
    )
    assert get_args(FreshStatusAsOfWindowStateV1) == (
        "WITHIN_EXPLICIT_BOUND_WINDOW",
        "EXPIRED_NOT_CURRENT",
    )


def test_a_future_usable_but_recorded_unrelied_observation_is_never_reassessed(
    upstream: Upstream,
) -> None:
    future_observation = _observation(
        upstream.subject_closure,
        category="HOLD_ACTIVE",
        claim="PRESENT",
        label="as-of-future-usable-never-reassessed",
        valid_from=_shift_seconds(FRESH_EVALUATED_AT, 1),
        valid_until=_shift_seconds(FRESH_EVALUATED_AT, 600),
    )
    local_bundle = _build_bundle(upstream, (future_observation,))
    local_chains = (_chain((future_observation,), (future_observation,)),)
    decision = local_bundle.record.decision
    assert decision.status_valid_until == decision.evaluated_at
    assert decision.blocking_categories == ()
    assert decision.disposition == "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"

    result = _assess(
        upstream,
        local_bundle,
        local_chains,
        as_of=_shift_seconds(FRESH_EVALUATED_AT, 60),
    )
    assert result.as_of_window_state == "EXPIRED_NOT_CURRENT"
    assert result.recorded_disposition == "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"
    assert result.recorded_blocking_categories == ()
    assert result.recorded_indeterminate_categories == decision.indeterminate_categories


def test_assessment_digest_has_an_independent_canonical_golden(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    result = _assess(upstream, bundle, chains)
    projection = {
        "assessment_profile": result.assessment_profile,
        "source_joint_replay_profile": result.source_joint_replay_profile,
        "source_record_chain_coverage_profile": result.source_record_chain_coverage_profile,
        "source_chain_replay_profile": result.source_chain_replay_profile,
        "source_evidence_profile": result.source_evidence_profile,
        "source_evidence_policy_version": result.source_evidence_policy_version,
        "source_evidence_policy_document_sha256": (result.source_evidence_policy_document_sha256),
        "evidence_record_id": result.evidence_record_id,
        "evidence_record_sha256": result.evidence_record_sha256,
        "request_id": result.request_id,
        "request_sha256": result.request_sha256,
        "decision_id": result.decision_id,
        "decision_sha256": result.decision_sha256,
        "subject_closure": result.subject_closure.model_dump(mode="json"),
        "coverage_set_sha256": result.coverage_set_sha256,
        "joint_replay_sha256": result.joint_replay_sha256,
        "as_of": result.as_of,
        "evaluated_at": result.evaluated_at,
        "status_valid_until": result.status_valid_until,
        "window_semantics": result.window_semantics,
        "recorded_disposition": result.recorded_disposition,
        "recorded_blocking_categories": result.recorded_blocking_categories,
        "recorded_indeterminate_categories": result.recorded_indeterminate_categories,
        "as_of_window_state": result.as_of_window_state,
    }
    canonical = json.dumps(
        projection,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    independent = hashlib.sha256(ASSESSMENT_DOMAIN + canonical).hexdigest()
    assert independent == result.as_of_assessment_sha256
    assert result.as_of_assessment_sha256 == (
        "e841f69b7ee679bd10099bac512e6a80d0e55cca0a845cb732788c895610ba5b"
    )


def test_assessment_digest_uses_recursive_compact_canonical_json() -> None:
    assert (
        assessment_module._canonical_payload({"z": {"b": 2, "a": "界"}, "a": (3, 1)})
        == '{"a":[3,1],"z":{"a":"界","b":2}}'.encode()
    )
    assert assessment_module._canonical_payload({"b": 1, "a": 2}) == (
        assessment_module._canonical_payload({"a": 2, "b": 1})
    )
    with pytest.raises(ValueError):
        assessment_module._canonical_payload({"not_finite": float("nan")})
    with pytest.raises(ValueError):
        assessment_module._canonical_payload({"not_finite": float("inf")})


def test_every_dynamic_assessment_projection_field_is_digest_bound(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    result = _assess(upstream, bundle, chains)
    signature = inspect.signature(assessment_module._as_of_assessment_sha256)
    expected_parameters = (
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
    )
    assert tuple(signature.parameters) == expected_parameters
    baseline = {name: getattr(result, name) for name in signature.parameters}
    assert assessment_module._as_of_assessment_sha256(**baseline) == (
        result.as_of_assessment_sha256
    )
    variations: dict[str, object] = {
        "evidence_record_id": result.evidence_record_id + "-drift",
        "evidence_record_sha256": "1" * 64,
        "request_id": result.request_id + "-drift",
        "request_sha256": "2" * 64,
        "decision_id": result.decision_id + "-drift",
        "decision_sha256": "3" * 64,
        "subject_closure": result.subject_closure.model_copy(
            update={"use_scope_review_record_sha256": "4" * 64}
        ),
        "coverage_set_sha256": "5" * 64,
        "joint_replay_sha256": "6" * 64,
        "as_of": _shift_seconds(result.as_of, 1),
        "evaluated_at": _shift_seconds(result.evaluated_at, -1),
        "status_valid_until": _shift_seconds(result.status_valid_until, 1),
        "window_semantics": result.window_semantics + "_DRIFT",
        "recorded_disposition": "NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET",
        "recorded_blocking_categories": (),
        "recorded_indeterminate_categories": (),
        "as_of_window_state": "EXPIRED_NOT_CURRENT",
    }
    changed: list[str] = []
    for field, value in variations.items():
        digest = assessment_module._as_of_assessment_sha256(**{**baseline, field: value})
        assert digest != result.as_of_assessment_sha256, field
        changed.append(digest)
    assert len(changed) == len(set(changed))


def test_as_of_changes_the_digest_even_inside_the_same_window(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    first = _assess(upstream, bundle, chains, as_of=bundle.record.decision.evaluated_at)
    second = _assess(
        upstream,
        bundle,
        chains,
        as_of=_shift_seconds(bundle.record.decision.evaluated_at, 1),
    )
    assert first.as_of_window_state == second.as_of_window_state
    assert first.joint_replay_sha256 == second.joint_replay_sha256
    assert first.recorded_disposition == second.recorded_disposition
    assert first.as_of_assessment_sha256 != second.as_of_assessment_sha256


def test_result_is_strict_frozen_process_local_and_zero_authority(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    result = _assess(upstream, bundle, chains)
    assert result.result_type == "FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_RESULT_V1"
    assert result.status == "FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_COMPLETED"
    assert result.limitation_codes == ALL_LIMITATIONS
    assert result.evidence_scope == "EXPLICIT_FINITE_BOUND_SET_ONLY"
    assert result.current_gate == "HUMAN_GATE"
    assert result.provider_state == "NOT_AUTHORIZED"
    assert result.usage_restriction == "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
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
    assert all(getattr(result, field) is False for field in false_fields)
    assert all(type(getattr(result, field)) is bool for field in false_fields)
    assert all(getattr(result, field) == 0 for field in zero_fields)
    assert all(type(getattr(result, field)) is int for field in zero_fields)
    with pytest.raises(ValidationError):
        result.execution_authorized = True  # type: ignore[misc]
    with pytest.raises(ValidationError, match="only by the verifier"):
        FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_validate(
            result.model_dump(mode="python"),
            strict=True,
        )
    with pytest.raises(ValidationError):
        FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_validate_json(
            result.model_dump_json(),
            strict=True,
        )


def test_result_field_set_is_minimal_and_contains_no_source_collections(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    result = _assess(upstream, bundle, chains)
    expected = {
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
        "result_type",
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
    }
    assert set(FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_fields) == expected
    assert set(result.model_dump()) == expected
    assert {
        "record",
        "chains",
        "observations",
        "chain_coverages",
        "joint_replay_result",
        "is_current",
        "rights_valid",
        "authorized",
    }.isdisjoint(expected)
    assert len(result.recorded_blocking_categories) <= len(CATEGORIES)
    assert len(result.recorded_indeterminate_categories) <= len(CATEGORIES)


def test_result_provenance_rejects_constructed_and_mutated_copies(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    result = _assess(upstream, bundle, chains)
    constructed = FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_construct(
        **{
            field: getattr(result, field)
            for field in FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_fields
        }
    )
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: assessment_module._require_result_provenance(constructed),
    )
    copied = result.model_copy(update={"as_of_assessment_sha256": "0" * 64})
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: assessment_module._require_result_provenance(copied),
    )


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("execution_authorized", 0),
        ("publication_authorized", 0),
        ("authorized_attempts", False),
        ("provider_requests", False),
    ),
)
def test_zero_authority_scalar_types_cannot_be_exchanged(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    field: str,
    invalid: object,
) -> None:
    result = _assess(upstream, bundle, chains)
    payload = result.model_dump(mode="python")
    payload[field] = invalid
    with pytest.raises(ValidationError):
        FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_validate(
            payload,
            strict=True,
            context={
                assessment_module._RESULT_PROVENANCE_CONTEXT_KEY: (
                    assessment_module._RESULT_PROVENANCE_SENTINEL
                )
            },
        )


def test_production_module_is_ast_locked_to_explicit_time_and_pure_memory() -> None:
    source = assessment_module.__file__
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


def test_only_deterministic_datetime_parsing_is_imported() -> None:
    source = assessment_module.__file__
    assert source is not None
    tree = ast.parse(Path(source).read_text(encoding="utf-8"))
    datetime_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "datetime"
    ]
    assert len(datetime_imports) == 1
    assert {alias.name for alias in datetime_imports[0].names} <= {"UTC", "datetime"}


def test_as_of_result_and_all_prior_process_results_are_not_persistent_schemas() -> None:
    from sdc.real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
        CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
    )
    from sdc.schemas import MODELS

    assert len(MODELS) == 86
    assert sum("FreshStatus" in model.__name__ for model in MODELS) == 6
    assert MODELS[67] is CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
    assert FreshStatusExplicitFiniteChainReplayResultV1 not in MODELS
    assert FreshStatusRecordChainInputV1 not in MODELS
    assert FreshStatusRecordChainCoverageSummaryV1 not in MODELS
    assert FreshStatusEvidenceRecordChainCoverageResultV1 not in MODELS
    assert FreshStatusEvidenceRecordJointReplayResultV1 not in MODELS
    assert FreshStatusEvidenceRecordAsOfAssessmentResultV1 not in MODELS
    assert not Path("schemas/FreshStatusEvidenceRecordAsOfAssessmentResultV1.schema.json").exists()
    assert Path(
        "schemas/CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.schema.json"
    ).is_file()
    schema_registry_source = Path("src/sdc/schemas.py").read_text(encoding="utf-8")
    assert "real_asset_fresh_status_record_as_of_assessment_v30" not in schema_registry_source
    assert "real_asset_fresh_status_record_as_of_assessment_receipt_v30" in (schema_registry_source)


def test_all_sixty_seven_committed_schema_bytes_remain_unchanged() -> None:
    from sdc.schemas import MODELS

    receipt_schema = "CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.schema.json"
    expected = {
        **PRE_FRESH_STATUS_V30_SCHEMA_SHA256,
        **FRESH_STATUS_V30_SCHEMA_SHA256,
    }
    assert len(expected) == 67
    registered_prefix = {f"{model.__name__}.schema.json" for model in MODELS[:68]}
    registered = {f"{model.__name__}.schema.json" for model in MODELS}
    assert len(MODELS) == 86
    assert registered_prefix == {*expected, receipt_schema}
    assert {path.name for path in Path("schemas").glob("*.schema.json")} == registered
    for name, expected_sha256 in expected.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == expected_sha256, name


def test_public_surface_is_exact_and_has_no_io_or_execution_entry() -> None:
    assert assessment_module.__all__ == [
        "FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE",
        "FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1",
        "FreshStatusAsOfWindowStateV1",
        "FreshStatusRecordAsOfAssessmentErrorCodeV1",
        "FreshStatusEvidenceRecordAsOfAssessmentResultV1",
        "RealAssetFreshStatusRecordAsOfAssessmentV30Error",
        "assess_fresh_status_evidence_record_as_of_v1",
    ]
    assert not any(
        name.lower().startswith(
            (
                "authorize",
                "cli_",
                "file_",
                "path_",
                "provider_",
                "read_",
                "write_",
            )
        )
        for name in assessment_module.__all__
    )


def test_as_of_is_the_only_new_fixed_size_resource(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    assert len(FRESH_EVALUATED_AT) == 20
    assert len(FRESH_EVALUATED_AT.encode("ascii")) == 20
    assert FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES == 16 * 1024 * 1024
    _assess(upstream, bundle, chains)
    fields = FreshStatusEvidenceRecordAsOfAssessmentResultV1.model_fields
    assert "chains" not in fields
    assert "observations" not in fields
    assert "chain_coverages" not in fields


def test_thirty_two_chains_succeed_and_thirty_three_fail_at_the_lower_bound(
    upstream: Upstream,
) -> None:
    observations = tuple(
        _observation(
            upstream.subject_closure,
            category="HOLD_ACTIVE",
            claim="ABSENT_WITH_EVIDENCE",
            label=f"as-of-32-chains-{index:02d}",
            source_identity_label=f"as-of-32-chains-{index:02d}",
        )
        for index in range(32)
    )
    local_bundle = _build_bundle(upstream, observations)
    local_chains = tuple(_chain((item,), (item,)) for item in observations)
    result = _assess(upstream, local_bundle, local_chains)
    assert result.as_of_window_state == "WITHIN_EXPLICIT_BOUND_WINDOW"

    _assert_error(
        "RECORD_JOINT_REPLAY_FAILED",
        lambda: _assess(
            upstream,
            local_bundle,
            (*local_chains, local_chains[0]),
        ),
        joint_replay_code="RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        coverage_code="CHAIN_COUNT_OUT_OF_RANGE",
    )


def test_sixty_four_observations_succeed_and_sixty_five_fail_at_the_lower_bound(
    upstream: Upstream,
) -> None:
    observations = []
    for index in range(65):
        predecessor = observations[-1] if observations else None
        observations.append(
            _observation(
                upstream.subject_closure,
                category="HOLD_ACTIVE",
                claim="UNKNOWN" if predecessor is None else "ABSENT_WITH_EVIDENCE",
                label=f"as-of-65-node-chain-{index:02d}",
                source_identity_label="as-of-65-node-chain",
                chain_kind="GENESIS" if predecessor is None else "SUCCESSOR",
                predecessor=predecessor,
            )
        )

    accepted = tuple(observations[:64])
    accepted_bundle = _build_bundle(upstream, (accepted[-1],))
    accepted_chain = (_chain(tuple(reversed(accepted)), (accepted[-1],)),)
    result = _assess(upstream, accepted_bundle, accepted_chain)
    assert result.as_of_window_state == "WITHIN_EXPLICIT_BOUND_WINDOW"

    rejected = tuple(observations)
    rejected_bundle = _build_bundle(upstream, (rejected[-1],))
    valid_shape = _chain(tuple(reversed(rejected[:64])), (rejected[-1],))
    oversized = valid_shape.model_copy(update={"observations": tuple(reversed(rejected))})
    _assert_error(
        "RECORD_JOINT_REPLAY_FAILED",
        lambda: _assess(upstream, rejected_bundle, (oversized,)),
        joint_replay_code="RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        coverage_code="OBSERVATION_COUNT_OUT_OF_RANGE",
    )
