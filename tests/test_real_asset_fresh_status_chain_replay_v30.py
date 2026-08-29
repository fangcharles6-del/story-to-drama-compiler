from __future__ import annotations

import ast
import itertools
from dataclasses import dataclass
from typing import Any, cast

import pytest
from pydantic import ValidationError
from real_asset_v2_test_support import digest
from test_real_asset_fresh_status_evidence_v30 import (
    ALL_LIMITATIONS,
    Upstream,
    _build_upstream,
    _observation,
    _sha,
)

import sdc.real_asset_fresh_status_chain_replay_v30 as replay_module
from sdc.compiler import stable_id
from sdc.real_asset_fresh_status_chain_replay_v30 import (
    FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE,
    FreshStatusExplicitFiniteChainReplayResultV1,
    RealAssetFreshStatusChainReplayV30Error,
    verify_fresh_status_explicit_finite_source_chain_v1,
)
from sdc.real_asset_fresh_status_evidence_v30 import (
    CreativeSampleRealAssetFreshStatusSourceObservationV1,
    FreshStatusChainHeadRefV1,
    FreshStatusObservationRefV1,
    FreshStatusSubjectClosureV1,
    derive_fresh_status_observation_chain_sha256_v1,
)

CATEGORY = "HOLD_ACTIVE"
SOURCE_KIND = "INTERNAL_HOLD_RECORD"
SOURCE_IDENTITY_LABEL = "chain-replay-v30-one-source"
SOURCE_IDENTITY_SHA256 = digest(f"fresh-v30-source-identity:{SOURCE_IDENTITY_LABEL}")


@dataclass(frozen=True)
class Topology:
    genesis: CreativeSampleRealAssetFreshStatusSourceObservationV1
    branch_a: CreativeSampleRealAssetFreshStatusSourceObservationV1
    branch_b: CreativeSampleRealAssetFreshStatusSourceObservationV1
    branch_c: CreativeSampleRealAssetFreshStatusSourceObservationV1
    reconciliation: CreativeSampleRealAssetFreshStatusSourceObservationV1


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


def _verify(
    upstream: Upstream,
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> FreshStatusExplicitFiniteChainReplayResultV1:
    return verify_fresh_status_explicit_finite_source_chain_v1(
        subject_closure=upstream.subject_closure,
        status_category=CATEGORY,
        source_kind=SOURCE_KIND,
        source_identity_ref_sha256=SOURCE_IDENTITY_SHA256,
        observations=observations,
    )


def _build_linear(
    upstream: Upstream,
    count: int,
) -> tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...]:
    observations: list[CreativeSampleRealAssetFreshStatusSourceObservationV1] = []
    for index in range(count):
        previous = observations[-1] if observations else None
        observations.append(
            _observation(
                upstream.subject_closure,
                category=CATEGORY,
                claim="PRESENT",
                label=f"chain-replay-linear-{index:02d}",
                source_kind=SOURCE_KIND,
                source_identity_label=SOURCE_IDENTITY_LABEL,
                chain_kind="GENESIS" if previous is None else "SUCCESSOR",
                predecessor=previous,
            )
        )
    return tuple(observations)


def _build_topology(upstream: Upstream) -> Topology:
    genesis = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="UNKNOWN",
        label="chain-replay-topology-genesis",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
    )
    branches = tuple(
        _observation(
            upstream.subject_closure,
            category=CATEGORY,
            claim=claim,
            label=f"chain-replay-topology-branch-{name}",
            source_kind=SOURCE_KIND,
            source_identity_label=SOURCE_IDENTITY_LABEL,
            chain_kind="SUCCESSOR",
            predecessor=genesis,
        )
        for name, claim in (
            ("a", "PRESENT"),
            ("b", "ABSENT_WITH_EVIDENCE"),
            ("c", "PRESENT"),
        )
    )
    reconciliation = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="CONFLICT",
        label="chain-replay-topology-reconciliation",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
        chain_kind="RECONCILIATION",
        reconciliation_heads=branches[:2],
    )
    return Topology(genesis, *branches, reconciliation)


def _assert_error(
    expected_code: str,
    callback: Any,
) -> RealAssetFreshStatusChainReplayV30Error:
    with pytest.raises(RealAssetFreshStatusChainReplayV30Error) as captured:
        callback()
    assert captured.value.code == expected_code
    assert str(captured.value).startswith(f"{expected_code}:")
    return captured.value


def _rebuild_with_link_updates(
    observation: CreativeSampleRealAssetFreshStatusSourceObservationV1,
    **updates: object,
) -> CreativeSampleRealAssetFreshStatusSourceObservationV1:
    payload = observation.model_dump(mode="python")
    chain_link = cast(dict[str, object], payload["chain_link"])
    chain_link.update(updates)
    payload["observation_id"] = stable_id(
        "real_asset_fresh_status_observation_v1",
        {key: value for key, value in payload.items() if key != "observation_id"},
    )
    return CreativeSampleRealAssetFreshStatusSourceObservationV1.model_validate(
        payload,
        strict=True,
    )


def _rebuild_with_branch_head_updates(
    observation: CreativeSampleRealAssetFreshStatusSourceObservationV1,
    *,
    head_index: int,
    **updates: object,
) -> CreativeSampleRealAssetFreshStatusSourceObservationV1:
    payload = observation.model_dump(mode="python")
    chain_link = cast(dict[str, object], payload["chain_link"])
    branch_heads = list(cast(tuple[dict[str, object], ...], chain_link["branch_heads"]))
    branch_heads[head_index].update(updates)
    chain_link["branch_heads"] = tuple(branch_heads)
    payload["observation_id"] = stable_id(
        "real_asset_fresh_status_observation_v1",
        {key: value for key, value in payload.items() if key != "observation_id"},
    )
    return CreativeSampleRealAssetFreshStatusSourceObservationV1.model_validate(
        payload,
        strict=True,
    )


@pytest.fixture(scope="module")
def upstream() -> Upstream:
    return _build_upstream()


@pytest.fixture(scope="module")
def linear_65(
    upstream: Upstream,
) -> tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...]:
    return _build_linear(upstream, 65)


@pytest.fixture(scope="module")
def topology(upstream: Upstream) -> Topology:
    return _build_topology(upstream)


@pytest.mark.parametrize("count", (1, 2, 63, 64))
def test_linear_chain_accepts_supported_boundaries(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
    count: int,
) -> None:
    result = _verify(upstream, linear_65[:count])
    assert result.observation_count == count
    assert result.genesis_ref == _ref(linear_65[0])
    assert result.provided_set_fork_point_refs == ()
    assert result.provided_set_terminal_head_refs == (_ref(linear_65[count - 1]),)
    assert result.provided_set_terminal_shape == "SINGLE_TERMINAL_HEAD"
    assert result.provided_explicit_finite_chain_closure_consistent is True


def test_count_bounds_fail_before_content_validation(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    _assert_error("COUNT_OUT_OF_RANGE", lambda: _verify(upstream, ()))
    _assert_error("COUNT_OUT_OF_RANGE", lambda: _verify(upstream, linear_65))
    _assert_error("COUNT_OUT_OF_RANGE", lambda: _verify(upstream, (linear_65[0],) * 65))


def test_input_must_be_an_exact_tuple(upstream: Upstream, linear_65: tuple[Any, ...]) -> None:
    _assert_error(
        "OBSERVATION_CONTRACT_INVALID",
        lambda: verify_fresh_status_explicit_finite_source_chain_v1(
            subject_closure=upstream.subject_closure,
            status_category=CATEGORY,
            source_kind=SOURCE_KIND,
            source_identity_ref_sha256=SOURCE_IDENTITY_SHA256,
            observations=cast(Any, list(linear_65[:1])),
        ),
    )


def test_subject_closure_must_be_an_existing_immutable_model(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    _assert_error(
        "CHAIN_SCOPE_MISMATCH",
        lambda: verify_fresh_status_explicit_finite_source_chain_v1(
            subject_closure=cast(Any, upstream.subject_closure.model_dump(mode="python")),
            status_category=CATEGORY,
            source_kind=SOURCE_KIND,
            source_identity_ref_sha256=SOURCE_IDENTITY_SHA256,
            observations=linear_65[:1],
        ),
    )


def test_two_record_observation_set_digest_is_golden(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    result = _verify(upstream, linear_65[:2])
    assert result.observation_set_sha256 == (
        "83505b755b0b8f1b0912b9881b79a7f3ea0aad2e8a1535d11b7c141c667b1c0e"
    )


def test_input_order_does_not_change_linear_result(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    records = linear_65[:64]
    expected = _verify(upstream, records)
    variants = (
        tuple(reversed(records)),
        records[17:] + records[:17],
        records[::2] + records[1::2],
    )
    assert all(_verify(upstream, variant) == expected for variant in variants)


def test_unreconciled_fork_is_consistent_with_multiple_terminals(
    upstream: Upstream,
    topology: Topology,
) -> None:
    observations = (topology.genesis, topology.branch_a, topology.branch_b)
    result = _verify(upstream, observations)
    assert result.provided_set_fork_point_refs == (_ref(topology.genesis),)
    assert result.provided_set_terminal_head_refs == tuple(
        sorted((_ref(topology.branch_a), _ref(topology.branch_b)), key=replay_module._ref_key)
    )
    assert result.provided_set_terminal_shape == "MULTIPLE_TERMINAL_HEADS"


def test_full_reconciliation_has_one_terminal(
    upstream: Upstream,
    topology: Topology,
) -> None:
    observations = (
        topology.genesis,
        topology.branch_a,
        topology.branch_b,
        topology.reconciliation,
    )
    result = _verify(upstream, observations)
    assert result.provided_set_fork_point_refs == (_ref(topology.genesis),)
    assert result.provided_set_terminal_head_refs == (_ref(topology.reconciliation),)
    assert result.provided_set_terminal_shape == "SINGLE_TERMINAL_HEAD"


def test_partial_reconciliation_retains_every_terminal(
    upstream: Upstream,
    topology: Topology,
) -> None:
    observations = (
        topology.genesis,
        topology.branch_a,
        topology.branch_b,
        topology.branch_c,
        topology.reconciliation,
    )
    result = _verify(upstream, observations)
    expected_terminals = tuple(
        sorted(
            (_ref(topology.branch_c), _ref(topology.reconciliation)),
            key=replay_module._ref_key,
        )
    )
    assert result.provided_set_terminal_head_refs == expected_terminals
    assert result.provided_set_terminal_shape == "MULTIPLE_TERMINAL_HEADS"
    assert not hasattr(result, "winner")
    assert not hasattr(result, "latest")
    assert not hasattr(result, "selected_head")


def test_every_small_graph_permutation_has_one_result(
    upstream: Upstream,
    topology: Topology,
) -> None:
    observations = (
        topology.genesis,
        topology.branch_a,
        topology.branch_b,
        topology.branch_c,
        topology.reconciliation,
    )
    expected = _verify(upstream, observations)
    assert all(
        _verify(upstream, items) == expected for items in itertools.permutations(observations)
    )


def test_reconciliation_heads_must_form_an_antichain(upstream: Upstream) -> None:
    genesis, branch_a, branch_b = _build_linear(upstream, 3)
    invalid_reconciliation = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="CONFLICT",
        label="chain-replay-ancestor-head-reconciliation",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
        chain_kind="RECONCILIATION",
        reconciliation_heads=(genesis, branch_b),
    )
    _assert_error(
        "RECONCILIATION_HEAD_ANCESTRY_CONFLICT",
        lambda: _verify(upstream, (genesis, branch_a, branch_b, invalid_reconciliation)),
    )


def test_three_reconciliation_heads_reject_one_ancestor_pair(upstream: Upstream) -> None:
    genesis, branch_a, branch_b = _build_linear(upstream, 3)
    sibling = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="ABSENT_WITH_EVIDENCE",
        label="chain-replay-three-head-sibling",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
        chain_kind="SUCCESSOR",
        predecessor=genesis,
    )
    reconciliation = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="CONFLICT",
        label="chain-replay-three-head-reconciliation",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
        chain_kind="RECONCILIATION",
        reconciliation_heads=(genesis, branch_b, sibling),
    )
    _assert_error(
        "RECONCILIATION_HEAD_ANCESTRY_CONFLICT",
        lambda: _verify(
            upstream,
            (genesis, branch_a, branch_b, sibling, reconciliation),
        ),
    )


def test_successor_and_reconciliation_children_both_create_a_fork(upstream: Upstream) -> None:
    genesis = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="UNKNOWN",
        label="chain-replay-mixed-children-genesis",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
    )
    branch_a = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="PRESENT",
        label="chain-replay-mixed-children-a",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
        chain_kind="SUCCESSOR",
        predecessor=genesis,
    )
    branch_b = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="ABSENT_WITH_EVIDENCE",
        label="chain-replay-mixed-children-b",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
        chain_kind="SUCCESSOR",
        predecessor=genesis,
    )
    successor = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="PRESENT",
        label="chain-replay-mixed-children-successor",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
        chain_kind="SUCCESSOR",
        predecessor=branch_a,
    )
    reconciliation = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="CONFLICT",
        label="chain-replay-mixed-children-reconciliation",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
        chain_kind="RECONCILIATION",
        reconciliation_heads=(branch_a, branch_b),
    )
    result = _verify(
        upstream,
        (genesis, branch_a, branch_b, successor, reconciliation),
    )
    assert result.provided_set_fork_point_refs == tuple(
        sorted((_ref(genesis), _ref(branch_a)), key=replay_module._ref_key)
    )
    assert result.provided_set_terminal_head_refs == tuple(
        sorted((_ref(successor), _ref(reconciliation)), key=replay_module._ref_key)
    )


def test_successor_and_reconciliation_orphans_fail_closed(
    upstream: Upstream,
    topology: Topology,
) -> None:
    _assert_error("ORPHAN_REFERENCE", lambda: _verify(upstream, (topology.branch_a,)))
    _assert_error(
        "ORPHAN_REFERENCE",
        lambda: _verify(
            upstream,
            (topology.genesis, topology.branch_a, topology.reconciliation),
        ),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("previous_observation_sha256", "0" * 64),
        ("previous_chain_sha256", "1" * 64),
    ),
)
def test_successor_anchor_drift_is_distinct_from_an_orphan(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
    field: str,
    value: object,
) -> None:
    genesis, successor = linear_65[:2]
    drifted = _rebuild_with_link_updates(successor, **{field: value})
    _assert_error(
        "REFERENCE_ANCHOR_MISMATCH",
        lambda: _verify(upstream, (genesis, drifted)),
    )


def test_previous_claim_anchor_drift_is_detected(
    upstream: Upstream,
    topology: Topology,
) -> None:
    drifted = _rebuild_with_link_updates(
        topology.branch_a,
        previous_claim_value="NOT_ASSESSED",
    )
    _assert_error(
        "REFERENCE_ANCHOR_MISMATCH",
        lambda: _verify(upstream, (topology.genesis, drifted)),
    )


def test_unknown_predecessor_id_is_an_orphan(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    successor = _rebuild_with_link_updates(
        linear_65[1],
        previous_observation_id="real_asset_fresh_status_observation_v1_00000000000000000000",
    )
    _assert_error("ORPHAN_REFERENCE", lambda: _verify(upstream, (linear_65[0], successor)))


def test_reconciliation_head_anchor_drift_is_detected(
    upstream: Upstream,
    topology: Topology,
) -> None:
    drifted = _rebuild_with_branch_head_updates(
        topology.reconciliation,
        head_index=0,
        observation_sha256="0" * 64,
    )
    _assert_error(
        "REFERENCE_ANCHOR_MISMATCH",
        lambda: _verify(
            upstream,
            (topology.genesis, topology.branch_a, topology.branch_b, drifted),
        ),
    )


def test_two_same_scope_genesis_records_are_not_one_chain(upstream: Upstream) -> None:
    first = _build_linear(upstream, 1)[0]
    second = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="PRESENT",
        label="chain-replay-second-genesis",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
    )
    _assert_error("GENESIS_COUNT_INVALID", lambda: _verify(upstream, (first, second)))


def test_mixed_chain_scope_fails_before_root_analysis(upstream: Upstream) -> None:
    first = _build_linear(upstream, 1)[0]
    foreign = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="PRESENT",
        label="chain-replay-foreign-source",
        source_kind=SOURCE_KIND,
        source_identity_label="chain-replay-v30-foreign-source",
    )
    _assert_error("CHAIN_SCOPE_MISMATCH", lambda: _verify(upstream, (first, foreign)))


@pytest.mark.parametrize(
    ("scope_field", "scope_value"),
    (
        ("status_category", "COMPLAINT_OPEN"),
        ("source_kind", "COMPLAINT_RECORD"),
        ("source_identity_ref_sha256", "0" * 64),
    ),
)
def test_explicit_expected_scope_cannot_select_another_chain(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
    scope_field: str,
    scope_value: object,
) -> None:
    arguments: dict[str, object] = {
        "subject_closure": upstream.subject_closure,
        "status_category": CATEGORY,
        "source_kind": SOURCE_KIND,
        "source_identity_ref_sha256": SOURCE_IDENTITY_SHA256,
        "observations": linear_65[:1],
    }
    arguments[scope_field] = scope_value
    _assert_error(
        "CHAIN_SCOPE_MISMATCH",
        lambda: verify_fresh_status_explicit_finite_source_chain_v1(**cast(Any, arguments)),
    )


def test_explicit_subject_closure_must_match_the_observation_chain(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    payload = upstream.subject_closure.model_dump(mode="python")
    payload["use_plan_sha256"] = digest("chain-replay-different-use-plan")
    payload["closure_id"] = stable_id(
        "real_asset_fresh_status_subject_closure_v1",
        {key: value for key, value in payload.items() if key != "closure_id"},
    )
    different_closure = FreshStatusSubjectClosureV1.model_validate(payload, strict=True)
    _assert_error(
        "CHAIN_SCOPE_MISMATCH",
        lambda: verify_fresh_status_explicit_finite_source_chain_v1(
            subject_closure=different_closure,
            status_category=CATEGORY,
            source_kind=SOURCE_KIND,
            source_identity_ref_sha256=SOURCE_IDENTITY_SHA256,
            observations=linear_65[:1],
        ),
    )


def test_exact_duplicate_uses_duplicate_id_precedence(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    _assert_error(
        "DUPLICATE_OBSERVATION_ID",
        lambda: _verify(upstream, (linear_65[0], linear_65[0])),
    )


@pytest.mark.parametrize(
    ("refs", "expected_code"),
    (
        (
            (
                FreshStatusObservationRefV1(
                    observation_id="real_asset_fresh_status_observation_v1_00000000000000000001",
                    observation_sha256="a" * 64,
                    status_category=CATEGORY,
                    source_identity_ref_sha256=SOURCE_IDENTITY_SHA256,
                    chain_sha256="b" * 64,
                ),
                FreshStatusObservationRefV1(
                    observation_id="real_asset_fresh_status_observation_v1_00000000000000000002",
                    observation_sha256="a" * 64,
                    status_category=CATEGORY,
                    source_identity_ref_sha256=SOURCE_IDENTITY_SHA256,
                    chain_sha256="c" * 64,
                ),
            ),
            "DUPLICATE_OBSERVATION_DOCUMENT_SHA256",
        ),
        (
            (
                FreshStatusObservationRefV1(
                    observation_id="real_asset_fresh_status_observation_v1_00000000000000000003",
                    observation_sha256="d" * 64,
                    status_category=CATEGORY,
                    source_identity_ref_sha256=SOURCE_IDENTITY_SHA256,
                    chain_sha256="e" * 64,
                ),
                FreshStatusObservationRefV1(
                    observation_id="real_asset_fresh_status_observation_v1_00000000000000000004",
                    observation_sha256="f" * 64,
                    status_category=CATEGORY,
                    source_identity_ref_sha256=SOURCE_IDENTITY_SHA256,
                    chain_sha256="e" * 64,
                ),
            ),
            "DUPLICATE_OBSERVATION_CHAIN_SHA256",
        ),
    ),
)
def test_independent_digest_collision_guards(
    refs: tuple[FreshStatusObservationRefV1, ...],
    expected_code: str,
) -> None:
    _assert_error(
        expected_code,
        lambda: replay_module._require_unique_observation_refs(refs),
    )


def test_symbolic_graph_kernel_detects_cycles() -> None:
    keys = {
        "a": ("a", "a", "a"),
        "b": ("b", "b", "b"),
    }
    _assert_error(
        "CYCLE_DETECTED",
        lambda: replay_module._topological_order(
            node_keys=keys,
            parents={"a": ("b",), "b": ("a",)},
            children={"a": {"b"}, "b": {"a"}},
        ),
    )


def test_cycle_precedes_genesis_and_disconnected_diagnostics() -> None:
    keys = {
        "g": ("g", "g", "g"),
        "a": ("a", "a", "a"),
        "b": ("b", "b", "b"),
    }
    _assert_error(
        "CYCLE_DETECTED",
        lambda: replay_module._topological_order(
            node_keys=keys,
            parents={"g": (), "a": ("b",), "b": ("a",)},
            children={"g": set(), "a": {"b"}, "b": {"a"}},
        ),
    )


def test_symbolic_reachability_kernel_detects_a_disconnected_component() -> None:
    keys = {
        "g": ("g", "g", "g"),
        "a": ("a", "a", "a"),
        "b": ("b", "b", "b"),
    }
    _assert_error(
        "DISCONNECTED_GRAPH",
        lambda: replay_module._require_reachable(
            genesis_id="g",
            node_keys=keys,
            children={"g": {"a"}, "a": set(), "b": set()},
        ),
    )


def test_result_is_frozen_complete_and_zero_authority(
    upstream: Upstream,
    topology: Topology,
) -> None:
    result = _verify(
        upstream,
        (
            topology.genesis,
            topology.branch_a,
            topology.branch_b,
            topology.reconciliation,
        ),
    )
    assert result.replay_profile == FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE
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


def test_result_rejects_derived_field_and_authority_drift(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    result = _verify(upstream, linear_65[:2])
    payload = result.model_dump(mode="python")
    payload["observation_set_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="observation_set_sha256"):
        FreshStatusExplicitFiniteChainReplayResultV1.model_validate(payload, strict=True)
    payload = result.model_dump(mode="python")
    payload["execution_authorized"] = True
    with pytest.raises(ValidationError):
        FreshStatusExplicitFiniteChainReplayResultV1.model_validate(payload, strict=True)


def test_result_requires_private_verifier_provenance(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    result = _verify(upstream, linear_65[:3])
    payload = result.model_dump(mode="python")
    with pytest.raises(ValidationError, match="complete in-memory verifier"):
        FreshStatusExplicitFiniteChainReplayResultV1.model_validate(payload, strict=True)
    with pytest.raises(ValidationError):
        FreshStatusExplicitFiniteChainReplayResultV1.model_validate_json(
            result.model_dump_json(),
            strict=True,
        )


def test_provenance_check_rejects_constructed_or_copied_results(
    upstream: Upstream,
    topology: Topology,
) -> None:
    result = _verify(
        upstream,
        (
            topology.genesis,
            topology.branch_a,
            topology.branch_b,
            topology.reconciliation,
        ),
    )
    constructed = FreshStatusExplicitFiniteChainReplayResultV1.model_construct(
        **result.model_dump(mode="python")
    )
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: replay_module._require_replay_result_provenance(constructed),
    )
    copied = result.model_copy(update={"genesis_ref": result.provided_set_terminal_head_refs[0]})
    _assert_error(
        "INTERNAL_RESULT_INCONSISTENCY",
        lambda: replay_module._require_replay_result_provenance(copied),
    )


def test_child_timestamps_do_not_define_graph_order(upstream: Upstream) -> None:
    genesis = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="PRESENT",
        label="chain-replay-late-genesis",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
        source_event_at="2026-08-20T10:00:00Z",
        observed_at="2026-08-20T10:01:00Z",
        valid_from="2026-08-20T10:00:00Z",
        valid_until="2026-08-21T10:00:00Z",
    )
    backfilled_successor = _observation(
        upstream.subject_closure,
        category=CATEGORY,
        claim="PRESENT",
        label="chain-replay-backfilled-successor",
        source_kind=SOURCE_KIND,
        source_identity_label=SOURCE_IDENTITY_LABEL,
        source_event_at="2026-08-20T01:00:00Z",
        observed_at="2026-08-20T01:01:00Z",
        valid_from="2026-08-20T01:00:00Z",
        valid_until="2026-08-21T01:00:00Z",
        chain_kind="SUCCESSOR",
        predecessor=genesis,
    )
    result = _verify(upstream, (backfilled_successor, genesis))
    assert result.provided_set_terminal_head_refs == (_ref(backfilled_successor),)


def test_public_entry_rejects_a_forged_model_before_graph_analysis(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    forged = linear_65[1].model_copy(update={"observation_id": linear_65[0].observation_id})
    _assert_error(
        "OBSERVATION_CONTRACT_INVALID",
        lambda: _verify(upstream, (linear_65[0], forged)),
    )


def test_observation_contract_failure_precedes_scope_failure(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> None:
    forged = linear_65[0].model_copy(
        update={"observation_id": "real_asset_fresh_status_observation_v1_00000000000000000000"}
    )
    _assert_error(
        "OBSERVATION_CONTRACT_INVALID",
        lambda: verify_fresh_status_explicit_finite_source_chain_v1(
            subject_closure=upstream.subject_closure,
            status_category=CATEGORY,
            source_kind=SOURCE_KIND,
            source_identity_ref_sha256="bad",
            observations=(forged,),
        ),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("profile", "forged-profile"),
        ("policy_version", "9.9.9"),
    ),
)
def test_forged_profile_or_policy_fails_at_the_observation_boundary(
    upstream: Upstream,
    linear_65: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
    field: str,
    value: str,
) -> None:
    forged = linear_65[0].model_copy(update={field: value})
    _assert_error(
        "OBSERVATION_CONTRACT_INVALID",
        lambda: _verify(upstream, (forged,)),
    )


def test_production_module_has_no_io_clock_provider_or_execution_surface() -> None:
    source = replay_module.__file__
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


def test_replay_result_is_not_registered_as_a_persistent_schema() -> None:
    from pathlib import Path

    from sdc.real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
        CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
    )
    from sdc.schemas import MODELS

    assert len(MODELS) == 76
    assert sum("FreshStatus" in model.__name__ for model in MODELS) == 6
    assert MODELS[67] is CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
    assert FreshStatusExplicitFiniteChainReplayResultV1 not in MODELS
    assert not Path("schemas/FreshStatusExplicitFiniteChainReplayResultV1.schema.json").exists()
    assert Path(
        "schemas/CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.schema.json"
    ).is_file()


def test_public_surface_is_exact() -> None:
    assert replay_module.__all__ == [
        "FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE",
        "FreshStatusProvidedSetTerminalShapeV1",
        "FreshStatusChainReplayErrorCodeV1",
        "FreshStatusExplicitFiniteChainReplayResultV1",
        "RealAssetFreshStatusChainReplayV30Error",
        "verify_fresh_status_explicit_finite_source_chain_v1",
    ]
    assert FreshStatusChainHeadRefV1 not in replay_module.__dict__.values()
