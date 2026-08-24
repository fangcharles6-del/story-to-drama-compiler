from __future__ import annotations

import ast
import hashlib
import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast, get_args

import pytest
from pydantic import ValidationError
from real_asset_v2_test_support import digest
from test_real_asset_fresh_status_chain_replay_v30 import (
    _build_linear,
    _rebuild_with_link_updates,
)
from test_real_asset_fresh_status_evidence_v30 import (
    ALL_LIMITATIONS,
    FreshBundle,
    Upstream,
    _build_bundle,
    _build_upstream,
    _observation,
    _sha,
)
from test_schemas import PRE_FRESH_STATUS_V30_SCHEMA_SHA256

import sdc.real_asset_fresh_status_record_chain_coverage_v30 as coverage_module
from sdc.compiler import stable_id
from sdc.real_asset_fresh_status_chain_replay_v30 import (
    FreshStatusChainReplayErrorCodeV1,
    RealAssetFreshStatusChainReplayV30Error,
    verify_fresh_status_explicit_finite_source_chain_v1,
)
from sdc.real_asset_fresh_status_evidence_v30 import (
    CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    CreativeSampleRealAssetFreshStatusInstructionV1,
    CreativeSampleRealAssetFreshStatusSourceObservationV1,
    FreshStatusCategoryResultV1,
    FreshStatusObservationRefV1,
    build_fresh_status_evidence_record_v1,
    derive_fresh_status_observation_chain_sha256_v1,
)
from sdc.real_asset_fresh_status_record_chain_coverage_v30 import (
    FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES,
    FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE,
    FreshStatusEvidenceRecordChainCoverageResultV1,
    FreshStatusRecordChainCoverageErrorCodeV1,
    FreshStatusRecordChainCoverageSummaryV1,
    FreshStatusRecordChainInputV1,
    RealAssetFreshStatusRecordChainCoverageV30Error,
    verify_fresh_status_evidence_record_explicit_chain_coverage_v1,
)

CATEGORY_A = "HOLD_ACTIVE"
SOURCE_KIND_A = "INTERNAL_HOLD_RECORD"
SOURCE_IDENTITY_LABEL_A = "record-chain-coverage-source-a"
SOURCE_IDENTITY_SHA256_A = digest(f"fresh-v30-source-identity:{SOURCE_IDENTITY_LABEL_A}")

CATEGORY_B = "DISPUTE_OPEN"
SOURCE_KIND_B = "DISPUTE_RECORD"
SOURCE_IDENTITY_LABEL_B = "record-chain-coverage-source-b"
SOURCE_IDENTITY_SHA256_B = digest(f"fresh-v30-source-identity:{SOURCE_IDENTITY_LABEL_B}")

FRESH_STATUS_V30_SCHEMA_SHA256 = {
    "CreativeSampleRealAssetFreshStatusSourceObservationV1.schema.json": (
        "42e4c98388e61f4601d48694de3321b1df7d1363c8e81373d182bf7c21c85edf"
    ),
    "CreativeSampleRealAssetFreshStatusRequestV1.schema.json": (
        "1ed275c92bf6d85fe2cec086bb9f28c3a9e54b2da4efacb7f5e7290ad7ff4e56"
    ),
    "CreativeSampleRealAssetFreshStatusInstructionV1.schema.json": (
        "0a3834758f907c975f8ae3cb83609b19549d4178b4d957848864f9b1b6ad2163"
    ),
    "CreativeSampleRealAssetFreshStatusDecisionV1.schema.json": (
        "5ac58dbb91dc521528f32257a1e361ca30b2f4810a43aff25996314e42127507"
    ),
    "CreativeSampleRealAssetFreshStatusEvidenceRecordV1.schema.json": (
        "6d9d5c210ffa2ba6bbaa9ab5d24dc3251827026b214df0d1eb9ef55a90a20b78"
    ),
}


@dataclass(frozen=True)
class CoverageGraph:
    genesis_a: CreativeSampleRealAssetFreshStatusSourceObservationV1
    target_a: CreativeSampleRealAssetFreshStatusSourceObservationV1
    sibling_a: CreativeSampleRealAssetFreshStatusSourceObservationV1
    descendant_a: CreativeSampleRealAssetFreshStatusSourceObservationV1
    target_b: CreativeSampleRealAssetFreshStatusSourceObservationV1


def _ref(
    observation: CreativeSampleRealAssetFreshStatusSourceObservationV1,
) -> FreshStatusObservationRefV1:
    return FreshStatusObservationRefV1(
        observation_id=observation.observation_id,
        observation_sha256=_sha(observation),
        status_category=observation.status_category,
        source_identity_ref_sha256=observation.source_identity_ref_sha256,
        chain_sha256=derive_fresh_status_observation_chain_sha256_v1(observation),
    )


def _chain(
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
    targets: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> FreshStatusRecordChainInputV1:
    first = observations[0]
    return FreshStatusRecordChainInputV1(
        status_category=first.status_category,
        source_kind=first.source_kind,
        source_identity_ref_sha256=first.source_identity_ref_sha256,
        request_target_refs=tuple(_ref(item) for item in targets),
        observations=observations,
    )


def _verify(
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> FreshStatusEvidenceRecordChainCoverageResultV1:
    return verify_fresh_status_evidence_record_explicit_chain_coverage_v1(
        record=record,
        chains=chains,
    )


def _assert_error(
    expected_code: str,
    callback: Any,
    *,
    replay_code: str | None = None,
) -> RealAssetFreshStatusRecordChainCoverageV30Error:
    with pytest.raises(RealAssetFreshStatusRecordChainCoverageV30Error) as captured:
        callback()
    assert captured.value.code == expected_code
    assert captured.value.replay_code == replay_code
    assert str(captured.value).startswith(f"{expected_code}:")
    return captured.value


def _build_graph(upstream: Upstream) -> CoverageGraph:
    genesis_a = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="UNKNOWN",
        label="record-chain-coverage-genesis-a",
        source_kind=SOURCE_KIND_A,
        source_identity_label=SOURCE_IDENTITY_LABEL_A,
    )
    target_a = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="PRESENT",
        label="record-chain-coverage-target-a",
        source_kind=SOURCE_KIND_A,
        source_identity_label=SOURCE_IDENTITY_LABEL_A,
        chain_kind="SUCCESSOR",
        predecessor=genesis_a,
    )
    sibling_a = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="ABSENT_WITH_EVIDENCE",
        label="record-chain-coverage-sibling-a",
        source_kind=SOURCE_KIND_A,
        source_identity_label=SOURCE_IDENTITY_LABEL_A,
        chain_kind="SUCCESSOR",
        predecessor=genesis_a,
    )
    descendant_a = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="PRESENT",
        label="record-chain-coverage-descendant-a",
        source_kind=SOURCE_KIND_A,
        source_identity_label=SOURCE_IDENTITY_LABEL_A,
        chain_kind="SUCCESSOR",
        predecessor=target_a,
    )
    target_b = _observation(
        upstream.subject_closure,
        category=CATEGORY_B,
        claim="ABSENT_WITH_EVIDENCE",
        label="record-chain-coverage-target-b",
        source_kind=SOURCE_KIND_B,
        source_identity_label=SOURCE_IDENTITY_LABEL_B,
    )
    return CoverageGraph(genesis_a, target_a, sibling_a, descendant_a, target_b)


@pytest.fixture(scope="module")
def upstream() -> Upstream:
    return _build_upstream()


@pytest.fixture(scope="module")
def graph(upstream: Upstream) -> CoverageGraph:
    return _build_graph(upstream)


@pytest.fixture(scope="module")
def bundle(upstream: Upstream, graph: CoverageGraph) -> FreshBundle:
    return _build_bundle(upstream, (graph.target_a, graph.target_b))


def test_two_explicit_chains_cover_the_exact_record_request(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    result = _verify(
        bundle.record,
        (
            _chain((graph.genesis_a, graph.target_a), (graph.target_a,)),
            _chain((graph.target_b,), (graph.target_b,)),
        ),
    )

    assert result.coverage_profile == FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE
    assert result.result_type == "FRESH_STATUS_EVIDENCE_RECORD_CHAIN_COVERAGE_RESULT_V1"
    assert result.status == "FRESH_STATUS_EVIDENCE_RECORD_CHAIN_COVERAGE_CONSISTENT"
    assert result.source_chain_replay_profile == (
        "creative-sample-real-asset-fresh-status-explicit-chain-replay-v1"
    )
    assert result.source_evidence_profile == "creative-sample-real-asset-fresh-status-evidence-v3.0"
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
    assert result.subject_closure == bundle.upstream.subject_closure
    assert result.request_observation_count == 2
    assert result.chain_count == 2
    assert result.covered_request_observation_count == 2
    assert result.provided_observation_count == 3
    assert result.supporting_ancestor_observation_count == 1
    assert result.provided_evidence_record_rebuild_consistent is True
    assert result.provided_evidence_record_request_explicit_chain_coverage_consistent is True
    assert result.coverage_set_sha256 == (
        "6876ac5395362afc3fea7833b37bf8a9bd9064bb67731bfe9bbb1f9be8ec1afb"
    )

    by_category = {item.status_category: item for item in result.chain_coverages}
    assert by_category[CATEGORY_A].request_target_refs == (_ref(graph.target_a),)
    assert by_category[CATEGORY_A].supporting_ancestor_refs == (_ref(graph.genesis_a),)
    assert by_category[CATEGORY_A].provided_explicit_finite_chain_closure_consistent is True
    assert by_category[CATEGORY_B].request_target_refs == (_ref(graph.target_b),)
    assert by_category[CATEGORY_B].supporting_ancestor_refs == ()


def test_targets_are_explicit_and_one_chain_may_cover_multiple_request_refs(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    local = _build_bundle(upstream, (graph.genesis_a, graph.target_a))
    result = _verify(
        local.record,
        (
            _chain(
                (graph.target_a, graph.genesis_a),
                (graph.target_a, graph.genesis_a),
            ),
        ),
    )
    assert result.chain_count == 1
    assert result.request_observation_refs == local.request.observation_refs
    assert result.chain_coverages[0].request_target_refs == local.request.observation_refs
    assert result.chain_coverages[0].supporting_ancestor_refs == ()
    reordered = _verify(
        local.record,
        (_chain((graph.genesis_a, graph.target_a), (graph.genesis_a, graph.target_a)),),
    )
    assert reordered == result


def test_target_ancestor_or_self_closure_is_exact(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    local = _build_bundle(upstream, (graph.target_a,))
    result = _verify(
        local.record,
        (_chain((graph.target_a, graph.genesis_a), (graph.target_a,)),),
    )
    coverage = result.chain_coverages[0]
    assert coverage.request_target_refs == (_ref(graph.target_a),)
    assert coverage.supporting_ancestor_refs == (_ref(graph.genesis_a),)
    assert coverage.observation_refs == tuple(
        sorted((_ref(graph.genesis_a), _ref(graph.target_a)), key=lambda item: item.observation_id)
    )


def test_reconciliation_target_accepts_its_complete_ancestor_closure(
    upstream: Upstream,
) -> None:
    genesis = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="UNKNOWN",
        label="record-chain-coverage-reconciliation-genesis",
        source_kind=SOURCE_KIND_A,
        source_identity_label="record-chain-coverage-reconciliation",
    )
    branch_a = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="PRESENT",
        label="record-chain-coverage-reconciliation-branch-a",
        source_kind=SOURCE_KIND_A,
        source_identity_label="record-chain-coverage-reconciliation",
        chain_kind="SUCCESSOR",
        predecessor=genesis,
    )
    branch_b = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="ABSENT_WITH_EVIDENCE",
        label="record-chain-coverage-reconciliation-branch-b",
        source_kind=SOURCE_KIND_A,
        source_identity_label="record-chain-coverage-reconciliation",
        chain_kind="SUCCESSOR",
        predecessor=genesis,
    )
    reconciliation = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="CONFLICT",
        label="record-chain-coverage-reconciliation-target",
        source_kind=SOURCE_KIND_A,
        source_identity_label="record-chain-coverage-reconciliation",
        chain_kind="RECONCILIATION",
        reconciliation_heads=(branch_a, branch_b),
    )
    local = _build_bundle(upstream, (reconciliation,))
    result = _verify(
        local.record,
        (
            _chain(
                (reconciliation, branch_b, genesis, branch_a),
                (reconciliation,),
            ),
        ),
    )
    coverage = result.chain_coverages[0]
    assert coverage.request_target_refs == (_ref(reconciliation),)
    assert set(coverage.supporting_ancestor_refs) == {
        _ref(genesis),
        _ref(branch_a),
        _ref(branch_b),
    }
    assert coverage.provided_set_terminal_head_refs == (_ref(reconciliation),)


def test_chain_collection_and_count_boundaries_fail_before_content(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    valid = _chain((graph.target_b,), (graph.target_b,))
    _assert_error(
        "CHAIN_COLLECTION_CONTRACT_INVALID",
        lambda: verify_fresh_status_evidence_record_explicit_chain_coverage_v1(
            record=bundle.record,
            chains=cast(Any, [valid]),
        ),
    )
    _assert_error("CHAIN_COUNT_OUT_OF_RANGE", lambda: _verify(bundle.record, ()))
    _assert_error(
        "CHAIN_COUNT_OUT_OF_RANGE",
        lambda: _verify(bundle.record, (valid,) * 33),
    )


def test_inner_count_boundaries_are_explicit(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    valid = _chain((graph.target_b,), (graph.target_b,))
    empty_targets = valid.model_copy(update={"request_target_refs": ()})
    empty_observations = valid.model_copy(update={"observations": ()})
    sixty_five = valid.model_copy(update={"observations": (graph.target_b,) * 65})
    _assert_error(
        "TARGET_COUNT_OUT_OF_RANGE",
        lambda: _verify(bundle.record, (empty_targets,)),
    )
    _assert_error(
        "OBSERVATION_COUNT_OUT_OF_RANGE",
        lambda: _verify(bundle.record, (empty_observations,)),
    )
    _assert_error(
        "OBSERVATION_COUNT_OUT_OF_RANGE",
        lambda: _verify(bundle.record, (sixty_five,)),
    )


def test_chain_input_must_be_one_exact_immutable_grouping(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    valid = _chain((graph.target_b,), (graph.target_b,))
    _assert_error(
        "CHAIN_INPUT_CONTRACT_INVALID",
        lambda: _verify(bundle.record, (cast(Any, valid.model_dump(mode="python")),)),
    )
    forged = valid.model_copy(update={"request_target_refs": [_ref(graph.target_b)]})
    _assert_error(
        "CHAIN_INPUT_CONTRACT_INVALID",
        lambda: _verify(bundle.record, (forged,)),
    )
    forged_observations = valid.model_copy(update={"observations": [graph.target_b]})
    _assert_error(
        "CHAIN_INPUT_CONTRACT_INVALID",
        lambda: _verify(bundle.record, (forged_observations,)),
    )


@pytest.mark.parametrize("level", ("outer", "target", "observation"))
def test_chain_outer_or_nested_hidden_extra_fails_at_the_chain_boundary(
    bundle: FreshBundle,
    graph: CoverageGraph,
    level: str,
) -> None:
    valid = _chain((graph.target_b,), (graph.target_b,))
    if level == "outer":
        forged = valid.model_copy(update={"hidden_extra": "synthetic"})
    elif level == "target":
        forged_target = _ref(graph.target_b).model_copy(update={"hidden_extra": "synthetic"})
        forged = valid.model_copy(update={"request_target_refs": (forged_target,)})
    else:
        forged_observation = graph.target_b.model_copy(update={"hidden_extra": "synthetic"})
        forged = valid.model_copy(update={"observations": (forged_observation,)})
    _assert_error(
        "CHAIN_INPUT_CONTRACT_INVALID",
        lambda: _verify(bundle.record, (forged,)),
    )


def test_invalid_nested_observation_precedes_its_sixty_five_count(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    invalid = graph.target_b.model_copy(
        update={"observation_id": "real_asset_fresh_status_observation_v1_00000000000000000000"}
    )
    forged = _chain((graph.target_b,), (graph.target_b,)).model_copy(
        update={"observations": (invalid,) * 65}
    )
    _assert_error(
        "CHAIN_INPUT_CONTRACT_INVALID",
        lambda: _verify(bundle.record, (forged,)),
    )


def test_thirty_two_explicit_genesis_chains_cover_thirty_two_request_refs(
    upstream: Upstream,
) -> None:
    observations = tuple(
        _observation(
            upstream.subject_closure,
            category=CATEGORY_A,
            claim="PRESENT",
            label=f"record-chain-coverage-32-chains-{index:02d}",
            source_kind=SOURCE_KIND_A,
            source_identity_label=f"record-chain-coverage-32-chains-{index:02d}",
        )
        for index in range(32)
    )
    local = _build_bundle(upstream, observations)
    result = _verify(
        local.record,
        tuple(_chain((item,), (item,)) for item in reversed(observations)),
    )
    assert result.chain_count == 32
    assert result.covered_request_observation_count == 32
    assert result.provided_observation_count == 32
    assert result.supporting_ancestor_observation_count == 0


def test_sixty_four_node_chain_covers_one_terminal_request_target(
    upstream: Upstream,
) -> None:
    items: list[CreativeSampleRealAssetFreshStatusSourceObservationV1] = []
    for index in range(64):
        previous = items[-1] if items else None
        items.append(
            _observation(
                upstream.subject_closure,
                category=CATEGORY_A,
                claim="UNKNOWN" if previous is None else "PRESENT",
                label=f"record-chain-coverage-64-nodes-{index:02d}",
                source_kind=SOURCE_KIND_A,
                source_identity_label="record-chain-coverage-64-nodes",
                chain_kind="GENESIS" if previous is None else "SUCCESSOR",
                predecessor=previous,
            )
        )
    observations = tuple(items)
    local = _build_bundle(upstream, (observations[-1],))
    result = _verify(
        local.record,
        (_chain(tuple(reversed(observations)), (observations[-1],)),),
    )
    assert result.chain_count == 1
    assert result.provided_observation_count == 64
    assert result.supporting_ancestor_observation_count == 63
    assert len(result.chain_coverages[0].observation_refs) == 64


def test_one_chain_accepts_thirty_two_explicit_request_targets(
    upstream: Upstream,
) -> None:
    observations = _build_linear(upstream, 32)
    local = _build_bundle(upstream, observations)
    result = _verify(
        local.record,
        (_chain(tuple(reversed(observations)), tuple(reversed(observations))),),
    )
    assert result.chain_count == 1
    assert result.request_observation_count == 32
    assert result.covered_request_observation_count == 32
    assert result.supporting_ancestor_observation_count == 0


def test_thirty_three_targets_fail_before_duplicate_target_analysis(
    upstream: Upstream,
) -> None:
    observations = _build_linear(upstream, 32)
    local = _build_bundle(upstream, observations)
    valid = _chain(observations, observations)
    too_many = valid.model_copy(
        update={"request_target_refs": (*valid.request_target_refs, valid.request_target_refs[0])}
    )
    _assert_error(
        "TARGET_COUNT_OUT_OF_RANGE",
        lambda: _verify(local.record, (too_many,)),
    )


def test_one_chain_input_cannot_repeat_its_request_target(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    local = _build_bundle(upstream, (graph.target_b,))
    repeated = _chain((graph.target_b,), (graph.target_b,)).model_copy(
        update={"request_target_refs": (_ref(graph.target_b), _ref(graph.target_b))}
    )
    _assert_error(
        "REQUEST_TARGET_COVERED_MULTIPLE_TIMES",
        lambda: _verify(local.record, (repeated,)),
    )


def test_thirty_two_by_sixty_four_occurrence_kernel_is_explicitly_bounded(
    graph: CoverageGraph,
) -> None:
    one = _chain((graph.target_b,), (graph.target_b,))
    sixty_four = one.model_copy(update={"observations": (graph.target_b,) * 64})
    expected_one = len(coverage_module._canonical_document(graph.target_b))
    assert coverage_module._aggregate_source_bytes((sixty_four,) * 32) == (expected_one * 32 * 64)


def test_evidence_record_is_strictly_revalidated(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    forged = bundle.record.model_copy(
        update={"record_id": "real_asset_fresh_status_evidence_record_v1_00000000000000000000"}
    )
    _assert_error(
        "EVIDENCE_RECORD_INVALID",
        lambda: _verify(forged, (_chain((graph.target_b,), (graph.target_b,)),)),
    )


@pytest.mark.parametrize("level", ("record", "request", "instruction", "decision"))
def test_record_outer_or_module_hidden_extra_is_evidence_record_invalid(
    bundle: FreshBundle,
    graph: CoverageGraph,
    level: str,
) -> None:
    if level == "record":
        forged = bundle.record.model_copy(update={"hidden_extra": "synthetic"})
    else:
        nested = getattr(bundle.record, level).model_copy(update={"hidden_extra": "synthetic"})
        forged = bundle.record.model_copy(update={level: nested})
    _assert_error(
        "EVIDENCE_RECORD_INVALID",
        lambda: _verify(
            forged,
            (
                _chain((graph.genesis_a, graph.target_a), (graph.target_a,)),
                _chain((graph.target_b,), (graph.target_b,)),
            ),
        ),
    )


def test_same_scope_two_genesis_records_fail_inside_slice2(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    other_genesis = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="PRESENT",
        label="record-chain-coverage-other-genesis",
        source_kind=SOURCE_KIND_A,
        source_identity_label=SOURCE_IDENTITY_LABEL_A,
    )
    local = _build_bundle(upstream, (graph.genesis_a, other_genesis))
    _assert_error(
        "CHAIN_REPLAY_FAILED",
        lambda: _verify(
            local.record,
            (_chain((graph.genesis_a, other_genesis), (graph.genesis_a, other_genesis)),),
        ),
        replay_code="GENESIS_COUNT_INVALID",
    )


def test_reachable_slice2_orphan_code_is_nested_exactly(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    local = _build_bundle(upstream, (graph.target_a,))
    _assert_error(
        "CHAIN_REPLAY_FAILED",
        lambda: _verify(
            local.record,
            (_chain((graph.target_a,), (graph.target_a,)),),
        ),
        replay_code="ORPHAN_REFERENCE",
    )


def test_reachable_slice2_anchor_mismatch_code_is_nested_exactly(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    drifted = _rebuild_with_link_updates(
        graph.target_a,
        previous_observation_sha256="0" * 64,
    )
    local = _build_bundle(upstream, (drifted,))
    _assert_error(
        "CHAIN_REPLAY_FAILED",
        lambda: _verify(
            local.record,
            (_chain((graph.genesis_a, drifted), (drifted,)),),
        ),
        replay_code="REFERENCE_ANCHOR_MISMATCH",
    )


def test_reachable_slice2_reconciliation_antichain_code_is_nested_exactly(
    upstream: Upstream,
) -> None:
    genesis = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="UNKNOWN",
        label="record-chain-coverage-antichain-genesis",
        source_kind=SOURCE_KIND_A,
        source_identity_label="record-chain-coverage-antichain",
    )
    first = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="PRESENT",
        label="record-chain-coverage-antichain-first",
        source_kind=SOURCE_KIND_A,
        source_identity_label="record-chain-coverage-antichain",
        chain_kind="SUCCESSOR",
        predecessor=genesis,
    )
    second = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="PRESENT",
        label="record-chain-coverage-antichain-second",
        source_kind=SOURCE_KIND_A,
        source_identity_label="record-chain-coverage-antichain",
        chain_kind="SUCCESSOR",
        predecessor=first,
    )
    reconciliation = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="CONFLICT",
        label="record-chain-coverage-antichain-reconciliation",
        source_kind=SOURCE_KIND_A,
        source_identity_label="record-chain-coverage-antichain",
        chain_kind="RECONCILIATION",
        reconciliation_heads=(genesis, second),
    )
    local = _build_bundle(upstream, (reconciliation,))
    _assert_error(
        "CHAIN_REPLAY_FAILED",
        lambda: _verify(
            local.record,
            (_chain((genesis, first, second, reconciliation), (reconciliation,)),),
        ),
        replay_code="RECONCILIATION_HEAD_ANCESTRY_CONFLICT",
    )


@pytest.mark.parametrize("replay_code", get_args(FreshStatusChainReplayErrorCodeV1))
def test_every_slice2_error_code_is_preserved_by_the_slice3_wrapper(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    graph: CoverageGraph,
    replay_code: str,
) -> None:
    """Cycle and disconnected graph construction remain covered by Slice 2 symbolic tests."""

    local = _build_bundle(upstream, (graph.target_b,))

    def fail_slice2(**_kwargs: object) -> None:
        raise RealAssetFreshStatusChainReplayV30Error(
            cast(Any, replay_code),
            "synthetic nested Slice 2 failure",
        )

    monkeypatch.setattr(
        coverage_module,
        "verify_fresh_status_explicit_finite_source_chain_v1",
        fail_slice2,
    )
    _assert_error(
        "CHAIN_REPLAY_FAILED",
        lambda: _verify(local.record, (_chain((graph.target_b,), (graph.target_b,)),)),
        replay_code=replay_code,
    )


def test_same_scope_different_genesis_are_distinct_logical_chains(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    other_genesis = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="PRESENT",
        label="record-chain-coverage-independent-genesis",
        source_kind=SOURCE_KIND_A,
        source_identity_label=SOURCE_IDENTITY_LABEL_A,
    )
    local = _build_bundle(upstream, (graph.genesis_a, other_genesis))
    result = _verify(
        local.record,
        (
            _chain((graph.genesis_a,), (graph.genesis_a,)),
            _chain((other_genesis,), (other_genesis,)),
        ),
    )
    assert result.chain_count == 2
    assert {item.genesis_ref for item in result.chain_coverages} == {
        _ref(graph.genesis_a),
        _ref(other_genesis),
    }


def test_same_logical_chain_cannot_be_split_across_inputs(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    local = _build_bundle(upstream, (graph.genesis_a, graph.target_a))
    _assert_error(
        "DUPLICATE_LOGICAL_CHAIN",
        lambda: _verify(
            local.record,
            (
                _chain((graph.genesis_a,), (graph.genesis_a,)),
                _chain((graph.genesis_a, graph.target_a), (graph.target_a,)),
            ),
        ),
    )


def test_request_target_duplicate_missing_and_anchor_drift_fail_closed(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    first = _chain((graph.genesis_a, graph.target_a), (graph.target_a,))
    second = _chain((graph.target_b,), (graph.target_b,))
    duplicate = second.model_copy(update={"request_target_refs": (_ref(graph.target_a),)})
    _assert_error(
        "REQUEST_TARGET_COVERED_MULTIPLE_TIMES",
        lambda: _verify(bundle.record, (first, duplicate)),
    )
    _assert_error(
        "REQUEST_OBSERVATION_NOT_COVERED",
        lambda: _verify(bundle.record, (first,)),
    )

    drifted_ref = _ref(graph.target_a).model_copy(update={"chain_sha256": "0" * 64})
    drifted = first.model_copy(update={"request_target_refs": (drifted_ref,)})
    _assert_error(
        "REQUEST_TARGET_ANCHOR_MISMATCH",
        lambda: _verify(bundle.record, (drifted, second)),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("observation_sha256", "0" * 64),
        ("status_category", "COMPLAINT_OPEN"),
        ("source_identity_ref_sha256", "1" * 64),
        ("chain_sha256", "2" * 64),
    ),
)
def test_every_known_id_full_ref_anchor_field_is_exact(
    upstream: Upstream,
    graph: CoverageGraph,
    field: str,
    value: str,
) -> None:
    local = _build_bundle(upstream, (graph.target_a,))
    drifted_ref = _ref(graph.target_a).model_copy(update={field: value})
    chain = _chain((graph.genesis_a, graph.target_a), (graph.target_a,)).model_copy(
        update={"request_target_refs": (drifted_ref,)}
    )
    _assert_error(
        "REQUEST_TARGET_ANCHOR_MISMATCH",
        lambda: _verify(local.record, (chain,)),
    )


def test_unknown_request_target_id_is_not_in_the_record(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    local = _build_bundle(upstream, (graph.target_a,))
    unknown = _ref(graph.target_a).model_copy(
        update={"observation_id": "real_asset_fresh_status_observation_v1_ffffffffffffffffffff"}
    )
    chain = _chain((graph.genesis_a, graph.target_a), (graph.target_a,)).model_copy(
        update={"request_target_refs": (unknown,)}
    )
    _assert_error(
        "REQUEST_TARGET_NOT_IN_RECORD",
        lambda: _verify(local.record, (chain,)),
    )


def test_target_not_in_record_and_target_not_resolved_are_distinct(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    local = _build_bundle(upstream, (graph.target_a,))
    _assert_error(
        "REQUEST_TARGET_NOT_IN_RECORD",
        lambda: _verify(
            local.record,
            (_chain((graph.genesis_a, graph.target_a), (graph.genesis_a,)),),
        ),
    )
    unresolved = FreshStatusRecordChainInputV1(
        status_category=graph.target_b.status_category,
        source_kind=graph.target_b.source_kind,
        source_identity_ref_sha256=graph.target_b.source_identity_ref_sha256,
        request_target_refs=(_ref(graph.target_a),),
        observations=(graph.target_b,),
    )
    _assert_error(
        "REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN",
        lambda: _verify(local.record, (unresolved,)),
    )


def test_unresolved_target_globally_precedes_an_earlier_chain_target_mismatch(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    local = _build_bundle(upstream, (graph.genesis_a, graph.target_a))
    later_sorted_dummy = _observation(
        upstream.subject_closure,
        category="POLICY_COMPATIBILITY_CURRENT",
        claim="PRESENT",
        label="record-chain-coverage-target-mismatch-dummy",
        source_kind="POLICY_EVALUATION_RECORD",
        source_identity_label="record-chain-coverage-target-mismatch-dummy",
    )
    mismatched = (
        _chain((graph.genesis_a, graph.target_a), (graph.target_a,)),
        FreshStatusRecordChainInputV1(
            status_category=later_sorted_dummy.status_category,
            source_kind=later_sorted_dummy.source_kind,
            source_identity_ref_sha256=later_sorted_dummy.source_identity_ref_sha256,
            request_target_refs=(_ref(graph.genesis_a),),
            observations=(later_sorted_dummy,),
        ),
    )
    errors = tuple(
        _assert_error(
            "REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN",
            lambda order=order: _verify(local.record, order),
        )
        for order in (mismatched, tuple(reversed(mismatched)))
    )
    assert (
        tuple((item.code, item.replay_code, str(item)) for item in errors)[0]
        == tuple((item.code, item.replay_code, str(item)) for item in errors)[1]
    )


def test_chain_target_set_mismatch_is_a_defensive_publicly_unreachable_guard(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    """Normal exact-cover, uniqueness and global-resolution passes make this branch unreachable."""

    chain = _chain((graph.genesis_a, graph.target_a), (graph.target_a,))
    replay = verify_fresh_status_explicit_finite_source_chain_v1(
        subject_closure=upstream.subject_closure,
        status_category=chain.status_category,
        source_kind=chain.source_kind,
        source_identity_ref_sha256=chain.source_identity_ref_sha256,
        observations=chain.observations,
    )
    record_keys = frozenset(
        coverage_module._full_ref_key(item)
        for item in (_ref(graph.genesis_a), _ref(graph.target_a))
    )
    _assert_error(
        "CHAIN_TARGET_SET_MISMATCH",
        lambda: coverage_module._require_chain_target_sets_match(
            replayed=((chain, replay),),
            record_keys=record_keys,
        ),
    )


def test_unresolved_target_globally_precedes_unrelated_support(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    declared_elsewhere = _observation(
        upstream.subject_closure,
        category="POLICY_COMPATIBILITY_CURRENT",
        claim="PRESENT",
        label="record-chain-coverage-unresolved-declared-target",
        source_kind="POLICY_EVALUATION_RECORD",
        source_identity_label="record-chain-coverage-unresolved-declared-target",
    )
    unrelated_dummy = _observation(
        upstream.subject_closure,
        category="RIGHTS_BASIS_CURRENT",
        claim="PRESENT",
        label="record-chain-coverage-unresolved-unrelated-dummy",
        source_kind="RIGHTS_HOLDER_DECLARATION",
        source_identity_label="record-chain-coverage-unresolved-unrelated-dummy",
    )
    local = _build_bundle(upstream, (graph.target_a, declared_elsewhere))
    chains = (
        _chain(
            (graph.genesis_a, graph.target_a, graph.sibling_a),
            (graph.target_a,),
        ),
        FreshStatusRecordChainInputV1(
            status_category=unrelated_dummy.status_category,
            source_kind=unrelated_dummy.source_kind,
            source_identity_ref_sha256=unrelated_dummy.source_identity_ref_sha256,
            request_target_refs=(_ref(declared_elsewhere),),
            observations=(unrelated_dummy,),
        ),
    )
    errors = tuple(
        _assert_error(
            "REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN",
            lambda order=order: _verify(local.record, order),
        )
        for order in (chains, tuple(reversed(chains)))
    )
    assert (
        tuple((item.code, item.replay_code, str(item)) for item in errors)[0]
        == tuple((item.code, item.replay_code, str(item)) for item in errors)[1]
    )


@pytest.mark.parametrize("extra_name", ("sibling_a", "descendant_a"))
def test_sibling_or_graph_descendant_is_unrelated_support(
    upstream: Upstream,
    graph: CoverageGraph,
    extra_name: str,
) -> None:
    local = _build_bundle(upstream, (graph.target_a,))
    extra = cast(
        CreativeSampleRealAssetFreshStatusSourceObservationV1,
        getattr(graph, extra_name),
    )
    _assert_error(
        "UNRELATED_SUPPORT_OBSERVATION",
        lambda: _verify(
            local.record,
            (_chain((graph.genesis_a, graph.target_a, extra), (graph.target_a,)),),
        ),
    )


def test_outer_inner_and_target_permutations_have_one_result(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    first_observations = (graph.genesis_a, graph.target_a)
    expected = _verify(
        bundle.record,
        (
            _chain(first_observations, (graph.target_a,)),
            _chain((graph.target_b,), (graph.target_b,)),
        ),
    )
    candidates = tuple(
        (
            _chain(observation_order, (graph.target_a,)),
            _chain((graph.target_b,), (graph.target_b,)),
        )
        for observation_order in itertools.permutations(first_observations)
    )
    assert all(
        _verify(bundle.record, chain_order) == expected
        for candidate in candidates
        for chain_order in (candidate, tuple(reversed(candidate)))
    )


def test_coverage_digest_binds_record_request_closure_sets_and_all_five_counts(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    result = _verify(
        bundle.record,
        (
            _chain((graph.genesis_a, graph.target_a), (graph.target_a,)),
            _chain((graph.target_b,), (graph.target_b,)),
        ),
    )
    arguments: dict[str, Any] = {
        "evidence_record_id": result.evidence_record_id,
        "evidence_record_sha256": result.evidence_record_sha256,
        "request_id": result.request_id,
        "request_sha256": result.request_sha256,
        "subject_closure": result.subject_closure,
        "request_observation_count": result.request_observation_count,
        "request_observation_refs": result.request_observation_refs,
        "chain_count": result.chain_count,
        "chain_coverages": result.chain_coverages,
        "covered_request_observation_count": result.covered_request_observation_count,
        "provided_observation_count": result.provided_observation_count,
        "supporting_ancestor_observation_count": (result.supporting_ancestor_observation_count),
    }
    assert coverage_module._coverage_set_sha256(**arguments) == result.coverage_set_sha256

    variations: dict[str, dict[str, Any]] = {}

    def add_variation(label: str, **updates: object) -> None:
        changed = dict(arguments)
        changed.update(updates)
        variations[label] = changed

    for field in ("evidence_record_id", "request_id"):
        add_variation(field, **{field: f"changed-{field}"})
    for field in ("evidence_record_sha256", "request_sha256"):
        add_variation(field, **{field: "f" * 64})
    add_variation(
        "subject_closure",
        subject_closure=result.subject_closure.model_copy(update={"closure_id": "changed-closure"}),
    )

    request_ref = result.request_observation_refs[0]
    request_ref_updates: tuple[tuple[str, object], ...] = (
        ("observation_id", "real_asset_fresh_status_observation_v1_ffffffffffffffffffff"),
        ("observation_sha256", "e" * 64),
        (
            "status_category",
            CATEGORY_B if request_ref.status_category != CATEGORY_B else CATEGORY_A,
        ),
        ("source_identity_ref_sha256", "d" * 64),
        ("chain_sha256", "c" * 64),
    )
    for field, value in request_ref_updates:
        changed_refs = list(result.request_observation_refs)
        changed_refs[0] = request_ref.model_copy(update={field: value})
        add_variation(
            f"request_observation_refs.{field}",
            request_observation_refs=tuple(changed_refs),
        )

    summary_index = next(
        index
        for index, summary in enumerate(result.chain_coverages)
        if summary.supporting_ancestor_refs
    )
    summary = result.chain_coverages[summary_index]

    def add_summary_variation(label: str, **updates: object) -> None:
        changed_summaries = list(result.chain_coverages)
        changed_summaries[summary_index] = summary.model_copy(update=updates)
        add_variation(
            f"chain_coverages.{label}",
            chain_coverages=tuple(changed_summaries),
        )

    add_summary_variation(
        "status_category",
        status_category=(CATEGORY_B if summary.status_category != CATEGORY_B else CATEGORY_A),
    )
    add_summary_variation(
        "source_kind",
        source_kind=(SOURCE_KIND_B if summary.source_kind != SOURCE_KIND_B else SOURCE_KIND_A),
    )
    add_summary_variation(
        "source_identity_ref_sha256",
        source_identity_ref_sha256="b" * 64,
    )
    add_summary_variation("observation_count", observation_count=summary.observation_count + 1)
    add_summary_variation("observation_set_sha256", observation_set_sha256="a" * 64)

    first_observation_ref = summary.observation_refs[0]
    changed_observation_refs = list(summary.observation_refs)
    changed_observation_refs[0] = first_observation_ref.model_copy(
        update={"observation_sha256": "9" * 64}
    )
    add_summary_variation(
        "observation_refs.content",
        observation_refs=tuple(changed_observation_refs),
    )
    add_summary_variation(
        "genesis_ref.content",
        genesis_ref=summary.genesis_ref.model_copy(update={"chain_sha256": "8" * 64}),
    )
    add_summary_variation(
        "provided_set_fork_point_refs",
        provided_set_fork_point_refs=(summary.genesis_ref,),
    )
    add_summary_variation(
        "provided_set_terminal_head_refs",
        provided_set_terminal_head_refs=(),
    )
    add_summary_variation(
        "provided_set_terminal_shape",
        provided_set_terminal_shape="MULTIPLE_TERMINAL_HEADS",
    )
    add_summary_variation(
        "request_target_refs",
        request_target_refs=summary.supporting_ancestor_refs,
    )
    add_summary_variation("supporting_ancestor_refs", supporting_ancestor_refs=())
    add_summary_variation(
        "provided_explicit_finite_chain_closure_consistent",
        provided_explicit_finite_chain_closure_consistent=False,
    )

    add_variation(
        "request_observation_refs.order",
        request_observation_refs=tuple(reversed(result.request_observation_refs)),
    )
    add_variation(
        "chain_coverages.order",
        chain_coverages=tuple(reversed(result.chain_coverages)),
    )
    for field in (
        "request_observation_count",
        "chain_count",
        "covered_request_observation_count",
        "provided_observation_count",
        "supporting_ancestor_observation_count",
    ):
        add_variation(field, **{field: cast(int, arguments[field]) + 1})

    changed_digests = {
        label: coverage_module._coverage_set_sha256(**item) for label, item in variations.items()
    }
    assert all(item != result.coverage_set_sha256 for item in changed_digests.values())
    assert len(changed_digests) == len(set(changed_digests.values()))


def test_multiple_deep_chain_failures_are_deterministic_under_outer_permutation(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    other_genesis = _observation(
        upstream.subject_closure,
        category=CATEGORY_A,
        claim="PRESENT",
        label="record-chain-coverage-deterministic-other-genesis",
        source_kind=SOURCE_KIND_A,
        source_identity_label=SOURCE_IDENTITY_LABEL_A,
    )
    policy_genesis = _observation(
        upstream.subject_closure,
        category="POLICY_COMPATIBILITY_CURRENT",
        claim="UNKNOWN",
        label="record-chain-coverage-deterministic-policy-genesis",
        source_kind="POLICY_EVALUATION_RECORD",
        source_identity_label="record-chain-coverage-deterministic-policy",
    )
    policy_orphan = _observation(
        upstream.subject_closure,
        category="POLICY_COMPATIBILITY_CURRENT",
        claim="PRESENT",
        label="record-chain-coverage-deterministic-policy-orphan",
        source_kind="POLICY_EVALUATION_RECORD",
        source_identity_label="record-chain-coverage-deterministic-policy",
        chain_kind="SUCCESSOR",
        predecessor=policy_genesis,
    )
    local = _build_bundle(upstream, (graph.genesis_a, policy_orphan))
    invalid_groups = (
        _chain((graph.genesis_a, other_genesis), (graph.genesis_a,)),
        _chain((policy_orphan,), (policy_orphan,)),
    )
    errors = tuple(
        _assert_error(
            "CHAIN_REPLAY_FAILED",
            lambda order=order: _verify(local.record, order),
            replay_code="GENESIS_COUNT_INVALID",
        )
        for order in (invalid_groups, tuple(reversed(invalid_groups)))
    )
    assert (
        tuple((item.code, item.replay_code, str(item)) for item in errors)[0]
        == tuple((item.code, item.replay_code, str(item)) for item in errors)[1]
    )


def _synthetic_ref(
    index: int,
    *,
    observation_id: str | None = None,
    observation_sha256: str | None = None,
    chain_sha256: str | None = None,
) -> FreshStatusObservationRefV1:
    hexadecimal = f"{index:064x}"
    return FreshStatusObservationRefV1(
        observation_id=observation_id or f"real_asset_fresh_status_observation_v1_{index:020x}",
        observation_sha256=observation_sha256 or hexadecimal,
        status_category=CATEGORY_A,
        source_identity_ref_sha256=SOURCE_IDENTITY_SHA256_A,
        chain_sha256=chain_sha256 or f"{index + 100:064x}",
    )


@pytest.mark.parametrize(
    ("left", "right", "set_digests", "expected_code"),
    (
        (
            _synthetic_ref(1),
            _synthetic_ref(
                2,
                observation_id="real_asset_fresh_status_observation_v1_00000000000000000001",
            ),
            ("a" * 64, "b" * 64),
            "CROSS_CHAIN_DUPLICATE_OBSERVATION_ID",
        ),
        (
            _synthetic_ref(3),
            _synthetic_ref(4, observation_sha256=f"{3:064x}"),
            ("c" * 64, "d" * 64),
            "CROSS_CHAIN_DUPLICATE_OBSERVATION_DOCUMENT_SHA256",
        ),
        (
            _synthetic_ref(5),
            _synthetic_ref(6, chain_sha256=f"{105:064x}"),
            ("e" * 64, "f" * 64),
            "CROSS_CHAIN_DUPLICATE_OBSERVATION_CHAIN_SHA256",
        ),
        (
            _synthetic_ref(7),
            _synthetic_ref(8),
            ("9" * 64, "9" * 64),
            "CROSS_CHAIN_DUPLICATE_OBSERVATION_SET_SHA256",
        ),
    ),
)
def test_cross_chain_collision_guards_are_independent_and_ordered(
    left: FreshStatusObservationRefV1,
    right: FreshStatusObservationRefV1,
    set_digests: tuple[str, str],
    expected_code: str,
) -> None:
    _assert_error(
        expected_code,
        lambda: coverage_module._require_cross_chain_uniqueness(
            observation_ref_groups=((left,), (right,)),
            observation_set_sha256s=set_digests,
        ),
    )


def test_exact_duplicate_uses_cross_chain_id_precedence() -> None:
    repeated = _synthetic_ref(9)
    _assert_error(
        "CROSS_CHAIN_DUPLICATE_OBSERVATION_ID",
        lambda: coverage_module._require_cross_chain_uniqueness(
            observation_ref_groups=((repeated,), (repeated,)),
            observation_set_sha256s=("a" * 64, "a" * 64),
        ),
    )


@pytest.mark.parametrize(
    "canonical_size",
    (
        FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES - 1,
        FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES,
    ),
)
def test_aggregate_source_byte_budget_accepts_limit_and_limit_minus_one(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    graph: CoverageGraph,
    canonical_size: int,
) -> None:
    local = _build_bundle(upstream, (graph.target_b,))
    chain = _chain((graph.target_b,), (graph.target_b,))
    real_canonical = coverage_module._canonical_document

    def sized_canonical(value: Any) -> bytes:
        if type(value) is CreativeSampleRealAssetFreshStatusSourceObservationV1:
            return b"x" * canonical_size
        return real_canonical(value)

    monkeypatch.setattr(coverage_module, "_canonical_document", sized_canonical)
    result = _verify(local.record, (chain,))
    assert result.chain_count == 1


def test_aggregate_source_byte_budget_rejects_limit_plus_one_before_record(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    chain = _chain((graph.target_b,), (graph.target_b,))
    real_canonical = coverage_module._canonical_document

    def sized_canonical(value: Any) -> bytes:
        if type(value) is CreativeSampleRealAssetFreshStatusSourceObservationV1:
            return b"x" * (FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES + 1)
        return real_canonical(value)

    monkeypatch.setattr(coverage_module, "_canonical_document", sized_canonical)
    forged_record = cast(
        CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
        {"not": "a record"},
    )
    _assert_error(
        "AGGREGATE_CANONICAL_BYTES_OUT_OF_RANGE",
        lambda: _verify(forged_record, (chain,)),
    )


def test_source_byte_budget_counts_every_supplied_occurrence(
    graph: CoverageGraph,
) -> None:
    chain = _chain((graph.target_b,), (graph.target_b,))
    one = coverage_module._aggregate_source_bytes((chain,))
    assert coverage_module._aggregate_source_bytes((chain, chain)) == one * 2


def test_record_rebuild_mismatch_fails_closed(
    upstream: Upstream,
    graph: CoverageGraph,
) -> None:
    local = _build_bundle(upstream, (graph.target_a,))
    original_result = next(
        item for item in local.instruction.category_results if item.status_category == CATEGORY_A
    )
    forged_result = FreshStatusCategoryResultV1.model_validate(
        {
            **original_result.model_dump(mode="python"),
            "claim_value": "ABSENT_WITH_EVIDENCE",
            "assessment_effect": "NON_BLOCKING_WITHIN_BOUND_WINDOW",
        },
        strict=True,
    )
    instruction_payload = local.instruction.model_dump(mode="python")
    instruction_payload["category_results"] = tuple(
        forged_result.model_dump(mode="python")
        if item.status_category == CATEGORY_A
        else item.model_dump(mode="python")
        for item in local.instruction.category_results
    )
    instruction_payload["instruction_id"] = stable_id(
        "real_asset_fresh_status_instruction_v1",
        {key: value for key, value in instruction_payload.items() if key != "instruction_id"},
    )
    forged_instruction = CreativeSampleRealAssetFreshStatusInstructionV1.model_validate(
        instruction_payload,
        strict=True,
    )
    forged_record = build_fresh_status_evidence_record_v1(
        request=local.request,
        instruction=forged_instruction,
    )
    assert (
        coverage_module.verify_fresh_status_evidence_record_internal_v1(forged_record)
        == forged_record
    )
    _assert_error(
        "RECORD_REBUILD_MISMATCH",
        lambda: _verify(
            forged_record,
            (_chain((graph.genesis_a, graph.target_a), (graph.target_a,)),),
        ),
    )


def test_result_is_frozen_and_zero_authority(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    result = _verify(
        bundle.record,
        (
            _chain((graph.genesis_a, graph.target_a), (graph.target_a,)),
            _chain((graph.target_b,), (graph.target_b,)),
        ),
    )
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


def test_result_requires_private_verifier_provenance(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    result = _verify(
        bundle.record,
        (
            _chain((graph.genesis_a, graph.target_a), (graph.target_a,)),
            _chain((graph.target_b,), (graph.target_b,)),
        ),
    )
    with pytest.raises(ValidationError, match="complete verifier"):
        FreshStatusEvidenceRecordChainCoverageResultV1.model_validate(
            result.model_dump(mode="python"),
            strict=True,
        )


def test_provenance_rejects_constructed_and_mutated_copied_results(
    bundle: FreshBundle,
    graph: CoverageGraph,
) -> None:
    result = _verify(
        bundle.record,
        (
            _chain((graph.genesis_a, graph.target_a), (graph.target_a,)),
            _chain((graph.target_b,), (graph.target_b,)),
        ),
    )
    constructed = FreshStatusEvidenceRecordChainCoverageResultV1.model_construct(
        **{
            field: getattr(result, field)
            for field in FreshStatusEvidenceRecordChainCoverageResultV1.model_fields
        }
    )
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: coverage_module._require_result_provenance(constructed),
    )
    copied = result.model_copy(update={"coverage_set_sha256": "0" * 64})
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: coverage_module._require_result_provenance(copied),
    )
    with pytest.raises(ValidationError):
        FreshStatusEvidenceRecordChainCoverageResultV1.model_validate_json(
            result.model_dump_json(),
            strict=True,
        )


def test_production_module_has_no_io_clock_provider_or_execution_surface() -> None:
    source = coverage_module.__file__
    assert source is not None
    with open(source, encoding="utf-8", newline="") as handle:
        tree = ast.parse(handle.read())
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

    forbidden_components = {
        "database",
        "datetime",
        "db",
        "httpx",
        "importlib",
        "os",
        "pathlib",
        "persistence",
        "provider",
        "queue",
        "requests",
        "runtime",
        "socket",
        "subprocess",
        "time",
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
        "builtins.open",
        "compile",
        "eval",
        "exec",
        "open",
    }.isdisjoint(called_names)


def test_coverage_models_are_not_registered_as_persistent_schemas() -> None:
    from sdc.schemas import MODELS

    assert len(MODELS) == 67
    assert FreshStatusRecordChainInputV1 not in MODELS
    assert FreshStatusRecordChainCoverageSummaryV1 not in MODELS
    assert FreshStatusEvidenceRecordChainCoverageResultV1 not in MODELS
    assert sum("FreshStatus" in model.__name__ for model in MODELS) == 5


def test_all_sixty_seven_existing_schema_bytes_are_locked() -> None:
    from sdc.schemas import MODELS

    expected = {
        **PRE_FRESH_STATUS_V30_SCHEMA_SHA256,
        **FRESH_STATUS_V30_SCHEMA_SHA256,
    }
    assert len(expected) == 67
    assert set(expected) == {f"{model.__name__}.schema.json" for model in MODELS}
    for name, expected_sha256 in expected.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == expected_sha256, name


def test_public_surface_is_exact() -> None:
    assert coverage_module.__all__ == [
        "FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE",
        "FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES",
        "FreshStatusRecordChainCoverageErrorCodeV1",
        "FreshStatusRecordChainInputV1",
        "FreshStatusRecordChainCoverageSummaryV1",
        "FreshStatusEvidenceRecordChainCoverageResultV1",
        "RealAssetFreshStatusRecordChainCoverageV30Error",
        "verify_fresh_status_evidence_record_explicit_chain_coverage_v1",
    ]


def test_error_literal_preserves_the_frozen_failure_order() -> None:
    assert get_args(FreshStatusRecordChainCoverageErrorCodeV1) == (
        "CHAIN_COLLECTION_CONTRACT_INVALID",
        "CHAIN_COUNT_OUT_OF_RANGE",
        "CHAIN_INPUT_CONTRACT_INVALID",
        "TARGET_COUNT_OUT_OF_RANGE",
        "OBSERVATION_COUNT_OUT_OF_RANGE",
        "AGGREGATE_CANONICAL_BYTES_OUT_OF_RANGE",
        "EVIDENCE_RECORD_INVALID",
        "REQUEST_TARGET_COVERED_MULTIPLE_TIMES",
        "REQUEST_TARGET_ANCHOR_MISMATCH",
        "REQUEST_TARGET_NOT_IN_RECORD",
        "REQUEST_OBSERVATION_NOT_COVERED",
        "CHAIN_REPLAY_FAILED",
        "DUPLICATE_LOGICAL_CHAIN",
        "CROSS_CHAIN_DUPLICATE_OBSERVATION_ID",
        "CROSS_CHAIN_DUPLICATE_OBSERVATION_DOCUMENT_SHA256",
        "CROSS_CHAIN_DUPLICATE_OBSERVATION_CHAIN_SHA256",
        "CROSS_CHAIN_DUPLICATE_OBSERVATION_SET_SHA256",
        "REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN",
        "CHAIN_TARGET_SET_MISMATCH",
        "UNRELATED_SUPPORT_OBSERVATION",
        "RECORD_REBUILD_MISMATCH",
        "INTERNAL_RESULT_INCONSISTENCY",
    )


def test_source_byte_budget_constant_is_exact() -> None:
    assert FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES == 16 * 1024 * 1024
