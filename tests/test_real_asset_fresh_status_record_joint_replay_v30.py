from __future__ import annotations

import ast
import hashlib
import inspect
from pathlib import Path
from typing import Any, cast, get_args

import pytest
from pydantic import ValidationError
from real_asset_v2_test_support import digest, make_complete_closure
from test_real_asset_fresh_status_evidence_v30 import (
    ALL_LIMITATIONS,
    USE_SCOPE_EVALUATED_AT,
    USE_SCOPE_REQUESTED_AT,
    FreshBundle,
    Upstream,
    _build_bundle,
    _build_upstream,
    _sha,
)
from test_real_asset_fresh_status_record_chain_coverage_v30 import (
    FRESH_STATUS_V30_SCHEMA_SHA256,
    CoverageGraph,
    _build_graph,
    _chain,
)
from test_schemas import PRE_FRESH_STATUS_V30_SCHEMA_SHA256

import sdc.real_asset_fresh_status_record_joint_replay_v30 as joint_module
from sdc.real_asset_fresh_status_chain_replay_v30 import (
    FreshStatusChainReplayErrorCodeV1,
)
from sdc.real_asset_fresh_status_evidence_v30 import (
    FreshStatusSubjectClosureV1,
    build_fresh_status_subject_closure_v1,
)
from sdc.real_asset_fresh_status_record_chain_coverage_v30 import (
    FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE,
    FreshStatusRecordChainCoverageErrorCodeV1,
    FreshStatusRecordChainInputV1,
    RealAssetFreshStatusRecordChainCoverageV30Error,
)
from sdc.real_asset_fresh_status_record_joint_replay_v30 import (
    FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE,
    FreshStatusEvidenceRecordJointReplayResultV1,
    FreshStatusRecordJointReplayErrorCodeV1,
    RealAssetFreshStatusRecordJointReplayV30Error,
    verify_fresh_status_evidence_record_joint_replay_v1,
)
from sdc.real_asset_use_plan_v26 import build_real_asset_use_plan_v1
from sdc.real_asset_use_scope_review_v26 import (
    UseScopeGateResultV1,
    build_use_scope_review_instruction_v1,
    build_use_scope_review_record_v1,
    build_use_scope_review_request_v1,
)


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


def _build_alternate_upstream() -> Upstream:
    closure = make_complete_closure(valid_until="2027-12-31T00:00:00Z")
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
        maker_identity_ref_sha256=digest("fresh-v30-alternate-upstream-maker"),
        requested_at=USE_SCOPE_REQUESTED_AT,
        request_basis="合成替代用途计划进入独立用途范围评审。",
    )
    review_instruction = build_use_scope_review_instruction_v1(
        request=review_request,
        checker_identity_ref_sha256=digest("fresh-v30-alternate-upstream-checker"),
        evaluated_at=USE_SCOPE_EVALUATED_AT,
        gate_results=_all_pass_gates(),
        disposition="PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY",
        checker_basis="合成替代闭包只用于联合重放反拼接测试。",
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


def _joint_kwargs(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
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
    }


def _verify(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> FreshStatusEvidenceRecordJointReplayResultV1:
    return verify_fresh_status_evidence_record_joint_replay_v1(
        **_joint_kwargs(upstream, bundle, chains)
    )


def _assert_error(
    expected_code: str,
    callback: Any,
    *,
    coverage_code: str | None = None,
    replay_code: str | None = None,
) -> RealAssetFreshStatusRecordJointReplayV30Error:
    with pytest.raises(RealAssetFreshStatusRecordJointReplayV30Error) as captured:
        callback()
    assert captured.value.code == expected_code
    assert captured.value.coverage_code == coverage_code
    assert captured.value.replay_code == replay_code
    assert str(captured.value).startswith(f"{expected_code}:")
    return captured.value


def test_complete_joint_replay_is_deterministic_and_exact(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    result = _verify(upstream, bundle, chains)
    reordered = _verify(
        upstream,
        bundle,
        tuple(
            chain.model_copy(update={"observations": tuple(reversed(chain.observations))})
            for chain in reversed(chains)
        ),
    )

    assert reordered == result
    assert result.result_type == "FRESH_STATUS_EVIDENCE_RECORD_JOINT_REPLAY_RESULT_V1"
    assert result.joint_replay_profile == FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE
    assert result.source_record_chain_coverage_profile == (
        FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE
    )
    assert result.source_chain_replay_profile == (
        "creative-sample-real-asset-fresh-status-explicit-chain-replay-v1"
    )
    assert result.source_evidence_profile == (
        "creative-sample-real-asset-fresh-status-evidence-v3.0"
    )
    assert result.source_evidence_policy_version == "3.0.0"
    assert result.source_evidence_policy_document_sha256 == (
        "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"
    )
    assert result.evidence_record_id == bundle.record.record_id
    assert result.evidence_record_sha256 == _sha(bundle.record)
    assert result.evidence_record_sha256 == (
        "40ce557997fd0fd778722d68426b513f7d5e41b3521532fc11e0e90684b0a2b0"
    )
    assert result.request_id == bundle.request.request_id
    assert result.request_sha256 == bundle.record.request_sha256
    assert result.subject_closure == upstream.subject_closure
    assert (
        result.request_observation_count,
        result.chain_count,
        result.covered_request_observation_count,
        result.provided_observation_count,
        result.supporting_ancestor_observation_count,
    ) == (2, 2, 2, 3, 1)
    assert result.coverage_set_sha256 == (
        "6876ac5395362afc3fea7833b37bf8a9bd9064bb67731bfe9bbb1f9be8ec1afb"
    )
    assert result.joint_replay_sha256 == (
        "bb30139b6bf64151ccd5253fc30b18fd37658a96b52cbedb702b48543737c317"
    )
    assert result.provided_upstream_object_closure_consistent is True
    assert result.provided_evidence_record_request_explicit_chain_coverage_consistent is True
    assert result.provided_evidence_record_rebuild_consistent is True
    assert result.status == "FRESH_STATUS_EVIDENCE_RECORD_JOINT_REPLAY_CONSISTENT"


def test_supporting_ancestors_never_enter_slice_one_observations(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    graph: CoverageGraph,
) -> None:
    real_closure_verifier = joint_module.verify_fresh_status_evidence_record_closure_v1
    captured: list[tuple[object, ...]] = []

    def wrapped_closure_verifier(**kwargs: Any) -> object:
        captured.append(kwargs["observations"])
        return real_closure_verifier(**kwargs)

    monkeypatch.setattr(
        joint_module,
        "verify_fresh_status_evidence_record_closure_v1",
        wrapped_closure_verifier,
    )
    _verify(upstream, bundle, chains)
    targets_by_id = {item.observation_id: item for item in (graph.target_a, graph.target_b)}
    expected = tuple(targets_by_id[item.observation_id] for item in bundle.request.observation_refs)
    assert captured == [expected]
    assert graph.genesis_a not in captured[0]


def test_main_flow_derives_targets_from_the_fresh_slice_three_result(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    real_coverage_verifier = (
        joint_module.verify_fresh_status_evidence_record_explicit_chain_coverage_v1
    )
    real_target_deriver = joint_module._derive_request_target_observations
    fresh_refs: list[tuple[object, ...]] = []
    derived_from: list[tuple[object, ...]] = []

    def wrapped_coverage(**kwargs: Any) -> object:
        result = real_coverage_verifier(**kwargs)
        fresh_refs.append(result.request_observation_refs)
        return result

    def wrapped_deriver(**kwargs: Any) -> tuple[object, ...]:
        derived_from.append(kwargs["request_observation_refs"])
        return real_target_deriver(**kwargs)

    monkeypatch.setattr(
        joint_module,
        "verify_fresh_status_evidence_record_explicit_chain_coverage_v1",
        wrapped_coverage,
    )
    monkeypatch.setattr(
        joint_module,
        "_derive_request_target_observations",
        wrapped_deriver,
    )
    _verify(upstream, bundle, chains)
    assert derived_from == fresh_refs


def test_complete_upstream_a_cannot_be_spliced_to_record_b(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    alternate = _build_alternate_upstream()
    assert alternate.subject_closure != upstream.subject_closure
    _assert_error(
        "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
        lambda: verify_fresh_status_evidence_record_joint_replay_v1(
            **_joint_kwargs(alternate, bundle, chains)
        ),
    )


def test_record_a_cannot_be_spliced_to_chains_b(
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
        "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        lambda: _verify(upstream, bundle, alternate_chains),
        coverage_code="REQUEST_TARGET_NOT_IN_RECORD",
    )


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
def test_each_of_eleven_required_upstream_objects_is_freshly_replayed(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    parameter: str,
    id_field: str,
) -> None:
    kwargs = _joint_kwargs(upstream, bundle, chains)
    original = kwargs[parameter]
    old_id = cast(str, getattr(original, id_field))
    replacement = "0" if old_id[-1] != "0" else "1"
    kwargs[parameter] = original.model_copy(update={id_field: old_id[:-1] + replacement})
    _assert_error(
        "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
        lambda: verify_fresh_status_evidence_record_joint_replay_v1(**kwargs),
    )


def test_partial_upstream_profile_is_not_accepted(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    kwargs = _joint_kwargs(upstream, bundle, chains)
    kwargs["use_plan"] = None
    _assert_error(
        "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
        lambda: verify_fresh_status_evidence_record_joint_replay_v1(**kwargs),
    )


def test_all_eleven_upstream_objects_are_required_keyword_only_inputs() -> None:
    signature = inspect.signature(verify_fresh_status_evidence_record_joint_replay_v1)
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
    )
    assert tuple(signature.parameters) == expected
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert {
        "observations",
        "subject_closure",
        "coverage_result",
        "as_of",
        "path",
        "callback",
    }.isdisjoint(signature.parameters)


@pytest.mark.parametrize(
    "coverage_code",
    get_args(FreshStatusRecordChainCoverageErrorCodeV1),
)
def test_all_twenty_two_slice_three_codes_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    coverage_code: FreshStatusRecordChainCoverageErrorCodeV1,
) -> None:
    def fail_coverage(**_: Any) -> None:
        raise RealAssetFreshStatusRecordChainCoverageV30Error(
            coverage_code,
            "synthetic Slice 3 failure",
        )

    monkeypatch.setattr(
        joint_module,
        "verify_fresh_status_evidence_record_explicit_chain_coverage_v1",
        fail_coverage,
    )
    error = _assert_error(
        "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        lambda: _verify(upstream, bundle, chains),
        coverage_code=coverage_code,
    )
    assert isinstance(error.__cause__, RealAssetFreshStatusRecordChainCoverageV30Error)


@pytest.mark.parametrize("replay_code", get_args(FreshStatusChainReplayErrorCodeV1))
def test_all_fourteen_slice_two_codes_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    replay_code: FreshStatusChainReplayErrorCodeV1,
) -> None:
    def fail_coverage(**_: Any) -> None:
        raise RealAssetFreshStatusRecordChainCoverageV30Error(
            "CHAIN_REPLAY_FAILED",
            "synthetic nested Slice 2 failure",
            replay_code=replay_code,
        )

    monkeypatch.setattr(
        joint_module,
        "verify_fresh_status_evidence_record_explicit_chain_coverage_v1",
        fail_coverage,
    )
    error = _assert_error(
        "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        lambda: _verify(upstream, bundle, chains),
        coverage_code="CHAIN_REPLAY_FAILED",
        replay_code=replay_code,
    )
    assert isinstance(error.__cause__, RealAssetFreshStatusRecordChainCoverageV30Error)


def test_slice_three_failure_precedes_target_and_closure_replay(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    later_calls: list[str] = []

    def fail_coverage(**_: Any) -> None:
        raise RealAssetFreshStatusRecordChainCoverageV30Error(
            "CHAIN_COUNT_OUT_OF_RANGE",
            "synthetic first-stage failure",
        )

    def unexpected_target(**_: Any) -> tuple[()]:
        later_calls.append("target")
        return ()

    def unexpected_closure(**_: Any) -> object:
        later_calls.append("closure")
        return bundle.record

    monkeypatch.setattr(
        joint_module,
        "verify_fresh_status_evidence_record_explicit_chain_coverage_v1",
        fail_coverage,
    )
    monkeypatch.setattr(joint_module, "_derive_request_target_observations", unexpected_target)
    monkeypatch.setattr(
        joint_module,
        "verify_fresh_status_evidence_record_closure_v1",
        unexpected_closure,
    )
    _assert_error(
        "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        lambda: _verify(upstream, bundle, chains),
        coverage_code="CHAIN_COUNT_OUT_OF_RANGE",
    )
    assert later_calls == []


def test_target_derivation_failure_precedes_closure_replay(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    closure_called = False

    def fail_target(**_: Any) -> tuple[()]:
        raise RealAssetFreshStatusRecordJointReplayV30Error(
            "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
            "synthetic target derivation failure",
        )

    def unexpected_closure(**_: Any) -> object:
        nonlocal closure_called
        closure_called = True
        return bundle.record

    monkeypatch.setattr(joint_module, "_derive_request_target_observations", fail_target)
    monkeypatch.setattr(
        joint_module,
        "verify_fresh_status_evidence_record_closure_v1",
        unexpected_closure,
    )
    _assert_error(
        "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
        lambda: _verify(upstream, bundle, chains),
    )
    assert closure_called is False


def test_closure_failure_precedes_internal_result_processing(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    kwargs = _joint_kwargs(upstream, bundle, chains)
    plan = kwargs["use_plan"]
    kwargs["use_plan"] = plan.model_copy(
        update={"plan_id": plan.plan_id[:-1] + ("0" if plan.plan_id[-1] != "0" else "1")}
    )
    internal_called = False

    def unexpected_internal(**_: Any) -> None:
        nonlocal internal_called
        internal_called = True

    monkeypatch.setattr(joint_module, "_require_joint_anchors", unexpected_internal)
    _assert_error(
        "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
        lambda: verify_fresh_status_evidence_record_joint_replay_v1(**kwargs),
    )
    assert internal_called is False


def test_unrelated_runtime_error_is_not_reclassified_as_a_closure_failure(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    def fail_with_unrelated_runtime(**_: Any) -> object:
        raise RuntimeError("synthetic unrelated runtime failure")

    monkeypatch.setattr(
        joint_module,
        "verify_fresh_status_evidence_record_closure_v1",
        fail_with_unrelated_runtime,
    )
    with pytest.raises(RuntimeError, match="synthetic unrelated runtime failure") as captured:
        _verify(upstream, bundle, chains)
    assert type(captured.value) is RuntimeError


def test_internal_anchor_failure_occurs_only_after_successful_closure_replay(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    real_closure_verifier = joint_module.verify_fresh_status_evidence_record_closure_v1
    closure_calls = 0

    def drift_after_success(**kwargs: Any) -> object:
        nonlocal closure_calls
        closure_calls += 1
        verified = real_closure_verifier(**kwargs)
        replacement = "0" if verified.record_id[-1] != "0" else "1"
        return verified.model_copy(update={"record_id": verified.record_id[:-1] + replacement})

    monkeypatch.setattr(
        joint_module,
        "verify_fresh_status_evidence_record_closure_v1",
        drift_after_success,
    )
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: _verify(upstream, bundle, chains),
    )
    assert closure_calls == 1


def test_target_derivation_helper_accepts_only_exact_request_targets(
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    graph: CoverageGraph,
) -> None:
    derived = joint_module._derive_request_target_observations(
        request_observation_refs=bundle.request.observation_refs,
        chains=chains,
    )
    targets_by_id = {item.observation_id: item for item in (graph.target_a, graph.target_b)}
    assert derived == tuple(
        targets_by_id[item.observation_id] for item in bundle.request.observation_refs
    )

    missing = chains[0].model_copy(update={"observations": (graph.genesis_a,)})
    _assert_error(
        "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
        lambda: joint_module._derive_request_target_observations(
            request_observation_refs=bundle.request.observation_refs,
            chains=(missing, chains[1]),
        ),
    )

    drifted = graph.target_a.model_copy(update={"source_identity_ref_sha256": "f" * 64})
    drift = chains[0].model_copy(update={"observations": (graph.genesis_a, drifted)})
    _assert_error(
        "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
        lambda: joint_module._derive_request_target_observations(
            request_observation_refs=bundle.request.observation_refs,
            chains=(drift, chains[1]),
        ),
    )

    duplicate = chains[0].model_copy(
        update={"observations": (graph.genesis_a, graph.target_a, graph.target_a)}
    )
    _assert_error(
        "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
        lambda: joint_module._derive_request_target_observations(
            request_observation_refs=bundle.request.observation_refs,
            chains=(duplicate, chains[1]),
        ),
    )

    missing_target_declaration = chains[0].model_copy(update={"request_target_refs": ()})
    _assert_error(
        "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
        lambda: joint_module._derive_request_target_observations(
            request_observation_refs=bundle.request.observation_refs,
            chains=(missing_target_declaration, chains[1]),
        ),
    )


def test_outer_error_literal_preserves_the_four_stage_failure_order() -> None:
    assert get_args(FreshStatusRecordJointReplayErrorCodeV1) == (
        "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
        "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
        "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
        "INTERNAL_RESULT_INCONSISTENCY",
    )


def test_joint_digest_uses_recursive_compact_canonical_json() -> None:
    assert (
        joint_module._canonical_payload({"z": {"b": 2, "a": "界"}, "a": (3, 1)})
        == '{"a":[3,1],"z":{"a":"界","b":2}}'.encode()
    )
    with pytest.raises(ValueError):
        joint_module._canonical_payload({"not_finite": float("nan")})


def test_every_joint_digest_projection_field_is_bound(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    result = _verify(upstream, bundle, chains)
    signature = inspect.signature(joint_module._joint_replay_sha256)
    baseline = {name: getattr(result, name) for name in signature.parameters}
    assert joint_module._joint_replay_sha256(**baseline) == result.joint_replay_sha256

    closure = cast(FreshStatusSubjectClosureV1, baseline["subject_closure"])
    variations: dict[str, object] = {
        "evidence_record_id": cast(str, baseline["evidence_record_id"])[:-1] + "0",
        "evidence_record_sha256": "1" * 64,
        "request_id": cast(str, baseline["request_id"])[:-1] + "0",
        "request_sha256": "2" * 64,
        "subject_closure": closure.model_copy(update={"use_scope_review_record_sha256": "3" * 64}),
        "request_observation_count": cast(int, baseline["request_observation_count"]) + 1,
        "chain_count": cast(int, baseline["chain_count"]) + 1,
        "covered_request_observation_count": (
            cast(int, baseline["covered_request_observation_count"]) + 1
        ),
        "provided_observation_count": cast(int, baseline["provided_observation_count"]) + 1,
        "supporting_ancestor_observation_count": (
            cast(int, baseline["supporting_ancestor_observation_count"]) + 1
        ),
        "coverage_set_sha256": "4" * 64,
    }
    changed: list[str] = []
    for field, value in variations.items():
        arguments = {**baseline, field: value}
        digest_value = joint_module._joint_replay_sha256(**arguments)
        assert digest_value != result.joint_replay_sha256, field
        changed.append(digest_value)
    assert len(changed) == len(set(changed))


def test_result_is_frozen_process_local_and_zero_authority(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    result = _verify(upstream, bundle, chains)
    assert result.limitation_codes == ALL_LIMITATIONS
    assert result.evidence_scope == "EXPLICIT_FINITE_BOUND_SET_ONLY"
    assert result.current_gate == "HUMAN_GATE"
    assert result.provider_state == "NOT_AUTHORIZED"
    assert result.usage_restriction == "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
    assert all(
        getattr(result, field) is False
        for field in (
            "generation_authorized",
            "execution_authorized",
            "publication_authorized",
            "remote_processing_allowed",
            "retention_allowed",
            "training_allowed",
            "publication_allowed",
            "automated_execution_allowed",
        )
    )
    assert all(
        getattr(result, field) == 0
        for field in (
            "authorized_attempts",
            "authorized_cost_cny",
            "posts_allowed",
            "provider_requests",
        )
    )
    with pytest.raises(ValidationError):
        result.execution_authorized = True  # type: ignore[misc]
    with pytest.raises(ValidationError, match="only by the verifier"):
        FreshStatusEvidenceRecordJointReplayResultV1.model_validate(
            result.model_dump(mode="python"),
            strict=True,
        )
    with pytest.raises(ValidationError):
        FreshStatusEvidenceRecordJointReplayResultV1.model_validate_json(
            result.model_dump_json(),
            strict=True,
        )


def test_provenance_rejects_constructed_and_mutated_copied_results(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    result = _verify(upstream, bundle, chains)
    constructed = FreshStatusEvidenceRecordJointReplayResultV1.model_construct(
        **{
            field: getattr(result, field)
            for field in FreshStatusEvidenceRecordJointReplayResultV1.model_fields
        }
    )
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: joint_module._require_result_provenance(constructed),
    )
    copied = result.model_copy(update={"joint_replay_sha256": "0" * 64})
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: joint_module._require_result_provenance(copied),
    )


def test_production_module_is_ast_locked_to_pure_memory() -> None:
    source = joint_module.__file__
    assert source is not None
    tree = ast.parse(Path(source).read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    called_names: set[str] = set()

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

    assert {module.split(".", maxsplit=1)[0] for module in imported_modules} <= {
        "__future__",
        "hashlib",
        "json",
        "pydantic",
        "sdc",
        "typing",
    }
    forbidden_components = {
        "argparse",
        "asyncio",
        "click",
        "database",
        "datetime",
        "db",
        "glob",
        "http",
        "httpx",
        "importlib",
        "keyring",
        "os",
        "pathlib",
        "persistence",
        "provider",
        "queue",
        "requests",
        "runtime",
        "shutil",
        "socket",
        "subprocess",
        "tempfile",
        "time",
        "typer",
        "urllib",
        "worker",
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
    assert not any(name.endswith((".now", ".utcnow", ".today", ".time")) for name in called_names)


def test_joint_result_and_all_prior_process_results_are_not_persistent_schemas() -> None:
    from sdc.real_asset_fresh_status_chain_replay_v30 import (
        FreshStatusExplicitFiniteChainReplayResultV1,
    )
    from sdc.real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
        CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
    )
    from sdc.real_asset_fresh_status_record_chain_coverage_v30 import (
        FreshStatusEvidenceRecordChainCoverageResultV1,
    )
    from sdc.schemas import MODELS

    assert len(MODELS) == 68
    assert sum("FreshStatus" in model.__name__ for model in MODELS) == 6
    assert MODELS[-1] is CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
    assert FreshStatusExplicitFiniteChainReplayResultV1 not in MODELS
    assert FreshStatusEvidenceRecordChainCoverageResultV1 not in MODELS
    assert FreshStatusEvidenceRecordJointReplayResultV1 not in MODELS
    assert not Path("schemas/FreshStatusEvidenceRecordJointReplayResultV1.schema.json").exists()
    assert Path(
        "schemas/CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.schema.json"
    ).is_file()


def test_all_sixty_seven_existing_schema_bytes_are_unchanged() -> None:
    from sdc.schemas import MODELS

    receipt_schema = "CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.schema.json"
    expected = {
        **PRE_FRESH_STATUS_V30_SCHEMA_SHA256,
        **FRESH_STATUS_V30_SCHEMA_SHA256,
    }
    assert len(expected) == 67
    registered = {f"{model.__name__}.schema.json" for model in MODELS}
    assert len(MODELS) == 68
    assert registered == {*expected, receipt_schema}
    assert {path.name for path in Path("schemas").glob("*.schema.json")} == registered
    for name, expected_sha256 in expected.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == expected_sha256, name


def test_public_surface_is_exact_and_has_no_io_or_execution_entry() -> None:
    assert joint_module.__all__ == [
        "FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE",
        "FreshStatusRecordJointReplayErrorCodeV1",
        "FreshStatusEvidenceRecordJointReplayResultV1",
        "RealAssetFreshStatusRecordJointReplayV30Error",
        "verify_fresh_status_evidence_record_joint_replay_v1",
    ]
    assert not any(
        name.lower().startswith(("authorize", "cli_", "file_", "path_", "provider_", "write_"))
        for name in joint_module.__all__
    )
