"""Pure explicit finite Fresh Status source-chain replay for v3.0.

This module validates only the exact in-memory SourceObservation set supplied by the caller.
It performs no filesystem, network, Provider, environment-time, or wall-clock I/O.  Success
proves ancestor closure and graph consistency only inside that finite set; it does not prove
source authenticity, global completeness, reality currentness, legal effect, or authority.
"""

from __future__ import annotations

import hashlib
import heapq
import json
from typing import Literal, Never

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationError,
    ValidationInfo,
    model_validator,
)

from sdc.real_asset_fresh_status_evidence_v30 import (
    FRESH_STATUS_EVIDENCE_SCOPE,
    FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256,
    FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
    FRESH_STATUS_EVIDENCE_V1_PROFILE,
    FRESH_STATUS_MAX_CHAIN_RECORDS,
    FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES,
    CreativeSampleRealAssetFreshStatusSourceObservationV1,
    FreshStatusCategoryV1,
    FreshStatusLimitationCodeV1,
    FreshStatusObservationRefV1,
    FreshStatusSourceKindV1,
    FreshStatusSubjectClosureV1,
    RealAssetFreshStatusEvidenceV30Error,
    derive_fresh_status_observation_chain_sha256_v1,
    verify_fresh_status_source_observation_internal_v1,
    verify_fresh_status_source_observation_link_v1,
)

FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE: Literal[
    "creative-sample-real-asset-fresh-status-explicit-chain-replay-v1"
] = "creative-sample-real-asset-fresh-status-explicit-chain-replay-v1"

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_OBSERVATION_SET_DOMAIN = b"sdc:creative-sample-real-asset-fresh-status-explicit-chain-set:v1\0"
_RESULT_PROVENANCE_DOMAIN = (
    b"sdc:creative-sample-real-asset-fresh-status-chain-replay-provenance:v1\0"
)
_RESULT_PROVENANCE_CONTEXT_KEY = "fresh_status_chain_replay_verifier_provenance"
_RESULT_PROVENANCE_SENTINEL = object()

FreshStatusProvidedSetTerminalShapeV1 = Literal[
    "SINGLE_TERMINAL_HEAD",
    "MULTIPLE_TERMINAL_HEADS",
]
FreshStatusChainReplayErrorCodeV1 = Literal[
    "COUNT_OUT_OF_RANGE",
    "OBSERVATION_CONTRACT_INVALID",
    "DUPLICATE_OBSERVATION_ID",
    "DUPLICATE_OBSERVATION_DOCUMENT_SHA256",
    "DUPLICATE_OBSERVATION_CHAIN_SHA256",
    "CHAIN_SCOPE_MISMATCH",
    "ORPHAN_REFERENCE",
    "REFERENCE_ANCHOR_MISMATCH",
    "IMMEDIATE_LINK_INVALID",
    "CYCLE_DETECTED",
    "GENESIS_COUNT_INVALID",
    "DISCONNECTED_GRAPH",
    "RECONCILIATION_HEAD_ANCESTRY_CONFLICT",
    "INTERNAL_RESULT_INCONSISTENCY",
]

_ALL_LIMITATION_CODES: tuple[FreshStatusLimitationCodeV1, ...] = (
    "SOURCE_AUTHENTICITY_NOT_PROVEN",
    "SOURCE_COMPLETENESS_NOT_PROVEN",
    "CHAIN_COMPLETENESS_NOT_PROVEN",
    "REALITY_CURRENTNESS_NOT_PROVEN",
    "SCOPE_LIMITED_TO_DECLARED_SUBJECT",
    "TIME_WINDOW_LIMITED",
    "LEGAL_EFFECT_NOT_DETERMINED",
)


class RealAssetFreshStatusChainReplayV30Error(RuntimeError):
    """The pure explicit finite chain replay failed closed."""

    code: FreshStatusChainReplayErrorCodeV1

    def __init__(self, code: FreshStatusChainReplayErrorCodeV1, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


class _ReplayModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class _ReplayScopeV1(_ReplayModel):
    subject_closure: FreshStatusSubjectClosureV1
    status_category: FreshStatusCategoryV1
    source_kind: FreshStatusSourceKindV1
    source_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)


class _ZeroAuthorityReplayModel(_ReplayModel):
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"] = FRESH_STATUS_EVIDENCE_SCOPE
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    generation_authorized: Literal[False] = False
    execution_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    remote_processing_allowed: Literal[False] = False
    retention_allowed: Literal[False] = False
    training_allowed: Literal[False] = False
    publication_allowed: Literal[False] = False
    automated_execution_allowed: Literal[False] = False
    authorized_attempts: Literal[0] = 0
    authorized_cost_cny: Literal[0] = 0
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0
    usage_restriction: Literal["MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"] = (
        "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_zero_authority_scalar_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        for field in (
            "generation_authorized",
            "execution_authorized",
            "publication_authorized",
            "remote_processing_allowed",
            "retention_allowed",
            "training_allowed",
            "publication_allowed",
            "automated_execution_allowed",
        ):
            if field in value and type(value[field]) is not bool:
                raise ValueError(f"{field} must be an exact JSON boolean")
        for field in (
            "authorized_attempts",
            "authorized_cost_cny",
            "posts_allowed",
            "provider_requests",
        ):
            if field in value and (type(value[field]) is not int or value[field] != 0):
                raise ValueError(f"{field} must be the exact JSON integer zero")
        return value


def _json_projection(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_projection(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return tuple(_json_projection(item) for item in value)
    return value


def _canonical_payload(value: object) -> bytes:
    return json.dumps(
        _json_projection(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_document(value: BaseModel) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _ref_key(item: FreshStatusObservationRefV1) -> tuple[str, str, str]:
    return item.observation_id, item.observation_sha256, item.chain_sha256


def _observation_set_sha256(
    *,
    scope: _ReplayScopeV1,
    observation_refs: tuple[FreshStatusObservationRefV1, ...],
) -> str:
    payload = {
        "profile": FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE,
        "source_evidence_policy_document_sha256": (FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256),
        "subject_closure": scope.subject_closure,
        "status_category": scope.status_category,
        "source_kind": scope.source_kind,
        "source_identity_ref_sha256": scope.source_identity_ref_sha256,
        "observation_refs": observation_refs,
    }
    return _sha256(_OBSERVATION_SET_DOMAIN + _canonical_payload(payload))


def _result_provenance_sha256(value: BaseModel) -> str:
    return _sha256(
        _RESULT_PROVENANCE_DOMAIN
        + _canonical_payload(value.model_dump(mode="json", exclude_none=False))
    )


def _validate_ref_subset(
    *,
    label: str,
    subset: tuple[FreshStatusObservationRefV1, ...],
    all_refs: tuple[FreshStatusObservationRefV1, ...],
) -> None:
    keys = tuple(_ref_key(item) for item in subset)
    if len(keys) != len(set(keys)) or keys != tuple(sorted(keys)):
        raise ValueError(f"{label} must be unique and canonically sorted")
    by_key = {_ref_key(item): item for item in all_refs}
    if any(by_key.get(_ref_key(item)) != item for item in subset):
        raise ValueError(f"{label} must be an exact subset of observation_refs")


class FreshStatusExplicitFiniteChainReplayResultV1(_ZeroAuthorityReplayModel):
    """Non-persistent process result for one exact provided source-chain set.

    Only the value returned by the public verifier carries replay meaning.  Direct model
    construction does not replay a graph and must never be treated as a receipt or proof.
    """

    _verification_provenance: tuple[object, str] | None = PrivateAttr(default=None)

    result_type: Literal["FRESH_STATUS_EXPLICIT_FINITE_CHAIN_REPLAY_RESULT_V1"] = (
        "FRESH_STATUS_EXPLICIT_FINITE_CHAIN_REPLAY_RESULT_V1"
    )
    replay_profile: Literal["creative-sample-real-asset-fresh-status-explicit-chain-replay-v1"] = (
        FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE
    )
    source_evidence_profile: Literal["creative-sample-real-asset-fresh-status-evidence-v3.0"] = (
        FRESH_STATUS_EVIDENCE_V1_PROFILE
    )
    source_evidence_policy_version: Literal["3.0.0"] = FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION
    source_evidence_policy_document_sha256: Literal[
        "ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58"
    ] = FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256
    subject_closure: FreshStatusSubjectClosureV1
    status_category: FreshStatusCategoryV1
    source_kind: FreshStatusSourceKindV1
    source_identity_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    observation_count: int = Field(ge=1, le=FRESH_STATUS_MAX_CHAIN_RECORDS)
    observation_set_sha256: str = Field(pattern=_LOWER_SHA256)
    observation_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        min_length=1,
        max_length=FRESH_STATUS_MAX_CHAIN_RECORDS,
    )
    genesis_ref: FreshStatusObservationRefV1
    provided_set_fork_point_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        max_length=FRESH_STATUS_MAX_CHAIN_RECORDS,
    )
    provided_set_terminal_head_refs: tuple[FreshStatusObservationRefV1, ...] = Field(
        min_length=1,
        max_length=FRESH_STATUS_MAX_CHAIN_RECORDS,
    )
    provided_set_terminal_shape: FreshStatusProvidedSetTerminalShapeV1
    provided_explicit_finite_chain_closure_consistent: Literal[True] = True
    limitation_codes: tuple[FreshStatusLimitationCodeV1, ...] = _ALL_LIMITATION_CODES
    status: Literal["FRESH_STATUS_EXPLICIT_FINITE_CHAIN_REPLAY_CONSISTENT"] = (
        "FRESH_STATUS_EXPLICIT_FINITE_CHAIN_REPLAY_CONSISTENT"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_exact_integer(cls, value: object) -> object:
        if isinstance(value, dict) and "observation_count" in value:
            count = value["observation_count"]
            if type(count) is not int:
                raise ValueError("observation_count must be an exact JSON integer")
        return value

    @model_validator(mode="after")
    def validate_result(
        self,
        info: ValidationInfo,
    ) -> FreshStatusExplicitFiniteChainReplayResultV1:
        keys = tuple(_ref_key(item) for item in self.observation_refs)
        ids = tuple(item.observation_id for item in self.observation_refs)
        document_digests = tuple(item.observation_sha256 for item in self.observation_refs)
        chain_digests = tuple(item.chain_sha256 for item in self.observation_refs)
        if (
            len(keys) != len(set(keys))
            or len(ids) != len(set(ids))
            or len(document_digests) != len(set(document_digests))
            or len(chain_digests) != len(set(chain_digests))
            or keys != tuple(sorted(keys))
        ):
            raise ValueError("observation_refs must be independently unique and sorted")
        if self.observation_count != len(self.observation_refs):
            raise ValueError("observation_count drifted from observation_refs")
        if any(
            item.status_category != self.status_category
            or item.source_identity_ref_sha256 != self.source_identity_ref_sha256
            for item in self.observation_refs
        ):
            raise ValueError("observation_refs drifted from the explicit replay scope")
        _validate_ref_subset(
            label="genesis_ref",
            subset=(self.genesis_ref,),
            all_refs=self.observation_refs,
        )
        _validate_ref_subset(
            label="provided_set_fork_point_refs",
            subset=self.provided_set_fork_point_refs,
            all_refs=self.observation_refs,
        )
        _validate_ref_subset(
            label="provided_set_terminal_head_refs",
            subset=self.provided_set_terminal_head_refs,
            all_refs=self.observation_refs,
        )
        if set(map(_ref_key, self.provided_set_fork_point_refs)) & set(
            map(_ref_key, self.provided_set_terminal_head_refs)
        ):
            raise ValueError("fork points and terminal heads must be disjoint")
        expected_shape: FreshStatusProvidedSetTerminalShapeV1 = (
            "SINGLE_TERMINAL_HEAD"
            if len(self.provided_set_terminal_head_refs) == 1
            else "MULTIPLE_TERMINAL_HEADS"
        )
        if self.provided_set_terminal_shape != expected_shape:
            raise ValueError("provided-set terminal shape drifted from terminal heads")
        if self.limitation_codes != _ALL_LIMITATION_CODES:
            raise ValueError("chain replay must retain all seven limitation codes")
        scope = _ReplayScopeV1(
            subject_closure=self.subject_closure,
            status_category=self.status_category,
            source_kind=self.source_kind,
            source_identity_ref_sha256=self.source_identity_ref_sha256,
        )
        if self.observation_set_sha256 != _observation_set_sha256(
            scope=scope,
            observation_refs=self.observation_refs,
        ):
            raise ValueError("observation_set_sha256 drifted from the explicit replay set")
        if (
            not isinstance(info.context, dict)
            or info.context.get(_RESULT_PROVENANCE_CONTEXT_KEY) is not _RESULT_PROVENANCE_SENTINEL
        ):
            raise ValueError(
                "replay results may be constructed only by the complete in-memory verifier"
            )
        self._verification_provenance = (
            _RESULT_PROVENANCE_SENTINEL,
            _result_provenance_sha256(self),
        )
        return self


def _require_replay_result_provenance(
    value: FreshStatusExplicitFiniteChainReplayResultV1,
) -> FreshStatusExplicitFiniteChainReplayResultV1:
    provenance = value._verification_provenance
    if provenance is None or provenance[0] is not _RESULT_PROVENANCE_SENTINEL:
        _raise(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the replay result lacks verifier-bound in-memory provenance",
        )
    expected = (_RESULT_PROVENANCE_SENTINEL, _result_provenance_sha256(value))
    if provenance != expected:
        _raise(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the replay result lacks verifier-bound in-memory provenance",
        )
    return value


def _raise(code: FreshStatusChainReplayErrorCodeV1, message: str) -> Never:
    raise RealAssetFreshStatusChainReplayV30Error(code, message)


def _replay_scope(
    *,
    subject_closure: FreshStatusSubjectClosureV1,
    status_category: FreshStatusCategoryV1,
    source_kind: FreshStatusSourceKindV1,
    source_identity_ref_sha256: str,
) -> _ReplayScopeV1:
    if type(subject_closure) is not FreshStatusSubjectClosureV1:
        _raise(
            "CHAIN_SCOPE_MISMATCH",
            "subject_closure must be one exact immutable FreshStatusSubjectClosureV1 model",
        )
    try:
        return _ReplayScopeV1.model_validate(
            {
                "subject_closure": subject_closure,
                "status_category": status_category,
                "source_kind": source_kind,
                "source_identity_ref_sha256": source_identity_ref_sha256,
            },
            strict=True,
        )
    except ValidationError as exc:
        raise RealAssetFreshStatusChainReplayV30Error(
            "CHAIN_SCOPE_MISMATCH",
            "the explicit source-chain scope violates its strict contract",
        ) from exc


def _observation_ref(
    observation: CreativeSampleRealAssetFreshStatusSourceObservationV1,
) -> FreshStatusObservationRefV1:
    return FreshStatusObservationRefV1(
        observation_id=observation.observation_id,
        observation_sha256=_sha256(_canonical_document(observation)),
        status_category=observation.status_category,
        source_identity_ref_sha256=observation.source_identity_ref_sha256,
        chain_sha256=derive_fresh_status_observation_chain_sha256_v1(observation),
    )


def _require_unique_observation_refs(
    observation_refs: tuple[FreshStatusObservationRefV1, ...],
) -> None:
    ids = tuple(item.observation_id for item in observation_refs)
    document_digests = tuple(item.observation_sha256 for item in observation_refs)
    chain_digests = tuple(item.chain_sha256 for item in observation_refs)
    if len(ids) != len(set(ids)):
        _raise("DUPLICATE_OBSERVATION_ID", "observation IDs must be unique")
    if len(document_digests) != len(set(document_digests)):
        _raise(
            "DUPLICATE_OBSERVATION_DOCUMENT_SHA256",
            "observation canonical-document digests must be unique",
        )
    if len(chain_digests) != len(set(chain_digests)):
        _raise(
            "DUPLICATE_OBSERVATION_CHAIN_SHA256",
            "observation chain digests must be unique",
        )


def _strict_observations(
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> tuple[
    tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, FreshStatusObservationRefV1],
    ...,
]:
    if type(observations) is not tuple:
        _raise("OBSERVATION_CONTRACT_INVALID", "observations must be an exact tuple")
    if not 1 <= len(observations) <= FRESH_STATUS_MAX_CHAIN_RECORDS:
        _raise("COUNT_OUT_OF_RANGE", "the provided chain must contain 1..64 observations")
    rebuilt: list[
        tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, FreshStatusObservationRefV1]
    ] = []
    for observation in observations:
        try:
            verified = verify_fresh_status_source_observation_internal_v1(observation)
            raw = _canonical_document(verified)
            if len(raw) > FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES:
                _raise(
                    "OBSERVATION_CONTRACT_INVALID",
                    "a SourceObservation exceeds its canonical byte limit",
                )
            rebuilt.append((verified, _observation_ref(verified)))
        except RealAssetFreshStatusChainReplayV30Error:
            raise
        except (RealAssetFreshStatusEvidenceV30Error, TypeError, ValueError) as exc:
            raise RealAssetFreshStatusChainReplayV30Error(
                "OBSERVATION_CONTRACT_INVALID",
                "a SourceObservation violates its strict immutable contract",
            ) from exc
    ordered = tuple(sorted(rebuilt, key=lambda item: _ref_key(item[1])))
    _require_unique_observation_refs(tuple(item[1] for item in ordered))
    return ordered


def _topological_order(
    *,
    node_keys: dict[str, tuple[str, str, str]],
    parents: dict[str, tuple[str, ...]],
    children: dict[str, set[str]],
) -> tuple[str, ...]:
    indegree = {node_id: len(parents[node_id]) for node_id in node_keys}
    ready = [(node_keys[node_id], node_id) for node_id, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    ordered: list[str] = []
    while ready:
        _, node_id = heapq.heappop(ready)
        ordered.append(node_id)
        for child_id in sorted(children[node_id], key=node_keys.__getitem__):
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                heapq.heappush(ready, (node_keys[child_id], child_id))
    if len(ordered) != len(node_keys):
        _raise("CYCLE_DETECTED", "the provided finite source-chain graph contains a cycle")
    return tuple(ordered)


def _require_reachable(
    *,
    genesis_id: str,
    node_keys: dict[str, tuple[str, str, str]],
    children: dict[str, set[str]],
) -> None:
    pending = [genesis_id]
    reached: set[str] = set()
    while pending:
        node_id = pending.pop()
        if node_id in reached:
            continue
        reached.add(node_id)
        pending.extend(sorted(children[node_id], key=node_keys.__getitem__, reverse=True))
    if len(reached) != len(node_keys):
        _raise(
            "DISCONNECTED_GRAPH",
            "not every provided observation is reachable from the one Genesis",
        )


def _require_reconciliation_antichains(
    *,
    ordered_ids: tuple[str, ...],
    observations_by_id: dict[str, CreativeSampleRealAssetFreshStatusSourceObservationV1],
    parents: dict[str, tuple[str, ...]],
) -> None:
    position = {node_id: index for index, node_id in enumerate(ordered_ids)}
    ancestors: dict[str, int] = {}
    for node_id in ordered_ids:
        bits = 0
        for parent_id in parents[node_id]:
            bits |= ancestors[parent_id] | (1 << position[parent_id])
        ancestors[node_id] = bits
    for node_id in ordered_ids:
        observation = observations_by_id[node_id]
        if observation.chain_link.kind != "RECONCILIATION":
            continue
        head_ids = parents[node_id]
        for index, left_id in enumerate(head_ids):
            for right_id in head_ids[index + 1 :]:
                left_is_ancestor = bool(ancestors[right_id] & (1 << position[left_id]))
                right_is_ancestor = bool(ancestors[left_id] & (1 << position[right_id]))
                if left_is_ancestor or right_is_ancestor:
                    _raise(
                        "RECONCILIATION_HEAD_ANCESTRY_CONFLICT",
                        "Reconciliation heads must form an ancestry antichain",
                    )


def verify_fresh_status_explicit_finite_source_chain_v1(
    *,
    subject_closure: FreshStatusSubjectClosureV1,
    status_category: FreshStatusCategoryV1,
    source_kind: FreshStatusSourceKindV1,
    source_identity_ref_sha256: str,
    observations: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...],
) -> FreshStatusExplicitFiniteChainReplayResultV1:
    """Replay one exact, explicit, finite, ancestor-closed in-memory source chain."""

    if type(observations) is not tuple:
        _raise("OBSERVATION_CONTRACT_INVALID", "observations must be an exact tuple")
    if not 1 <= len(observations) <= FRESH_STATUS_MAX_CHAIN_RECORDS:
        _raise("COUNT_OUT_OF_RANGE", "the provided chain must contain 1..64 observations")
    ordered = _strict_observations(observations)
    scope = _replay_scope(
        subject_closure=subject_closure,
        status_category=status_category,
        source_kind=source_kind,
        source_identity_ref_sha256=source_identity_ref_sha256,
    )
    expected_key = (
        scope.subject_closure,
        scope.status_category,
        scope.source_identity_ref_sha256,
        scope.source_kind,
        FRESH_STATUS_EVIDENCE_V1_PROFILE,
        FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION,
    )
    if any(
        (
            observation.subject_closure,
            observation.status_category,
            observation.source_identity_ref_sha256,
            observation.source_kind,
            observation.profile,
            observation.policy_version,
        )
        != expected_key
        for observation, _ in ordered
    ):
        _raise(
            "CHAIN_SCOPE_MISMATCH",
            "every observation must match the complete explicit source-chain key",
        )

    observations_by_id = {item.observation_id: item for item, _ in ordered}
    refs_by_id = {item.observation_id: ref for item, ref in ordered}
    node_keys = {node_id: _ref_key(ref) for node_id, ref in refs_by_id.items()}
    parents: dict[str, tuple[str, ...]] = {}
    children: dict[str, set[str]] = {node_id: set() for node_id in observations_by_id}
    genesis_ids: list[str] = []

    for observation, _ in ordered:
        link = observation.chain_link
        parent_ids: tuple[str, ...]
        predecessors: tuple[CreativeSampleRealAssetFreshStatusSourceObservationV1, ...]
        if link.kind == "GENESIS":
            genesis_ids.append(observation.observation_id)
            parent_ids = ()
            predecessors = ()
        elif link.kind == "SUCCESSOR":
            previous_id = link.previous_observation_id
            if previous_id is None or previous_id not in observations_by_id:
                _raise(
                    "ORPHAN_REFERENCE",
                    "the provided set omits a referenced predecessor observation",
                )
            previous = observations_by_id[previous_id]
            previous_ref = refs_by_id[previous_id]
            expected = (
                previous_ref.observation_id,
                previous_ref.observation_sha256,
                previous_ref.chain_sha256,
                previous.claim_value,
            )
            actual = (
                link.previous_observation_id,
                link.previous_observation_sha256,
                link.previous_chain_sha256,
                link.previous_claim_value,
            )
            if actual != expected:
                _raise(
                    "REFERENCE_ANCHOR_MISMATCH",
                    "a Successor predecessor anchor drifted from the exact supplied observation",
                )
            parent_ids = (previous_id,)
            predecessors = (previous,)
        else:
            resolved: list[CreativeSampleRealAssetFreshStatusSourceObservationV1] = []
            resolved_ids: list[str] = []
            for head in link.branch_heads:
                if head.observation_id not in observations_by_id:
                    _raise(
                        "ORPHAN_REFERENCE",
                        "the provided set omits a referenced Reconciliation head",
                    )
                expected_head = refs_by_id[head.observation_id]
                if (
                    head.observation_id,
                    head.observation_sha256,
                    head.chain_sha256,
                ) != _ref_key(expected_head):
                    _raise(
                        "REFERENCE_ANCHOR_MISMATCH",
                        "a Reconciliation head anchor drifted from the exact supplied observation",
                    )
                resolved_ids.append(head.observation_id)
                resolved.append(observations_by_id[head.observation_id])
            parent_ids = tuple(resolved_ids)
            predecessors = tuple(resolved)
        try:
            verify_fresh_status_source_observation_link_v1(
                observation=observation,
                predecessors=predecessors,
            )
        except RealAssetFreshStatusEvidenceV30Error as exc:
            raise RealAssetFreshStatusChainReplayV30Error(
                "IMMEDIATE_LINK_INVALID",
                "an immediate source-chain link violates the frozen Slice 1 rules",
            ) from exc
        parents[observation.observation_id] = parent_ids
        for parent_id in parent_ids:
            children[parent_id].add(observation.observation_id)

    ordered_ids = _topological_order(
        node_keys=node_keys,
        parents=parents,
        children=children,
    )
    if len(genesis_ids) != 1:
        _raise(
            "GENESIS_COUNT_INVALID",
            "the provided finite source chain must contain exactly one Genesis",
        )
    genesis_id = genesis_ids[0]
    _require_reachable(genesis_id=genesis_id, node_keys=node_keys, children=children)
    _require_reconciliation_antichains(
        ordered_ids=ordered_ids,
        observations_by_id=observations_by_id,
        parents=parents,
    )

    observation_refs = tuple(ref for _, ref in ordered)
    fork_refs = tuple(
        sorted(
            (refs_by_id[node_id] for node_id, child_ids in children.items() if len(child_ids) > 1),
            key=_ref_key,
        )
    )
    terminal_refs = tuple(
        sorted(
            (refs_by_id[node_id] for node_id, child_ids in children.items() if not child_ids),
            key=_ref_key,
        )
    )
    terminal_shape: FreshStatusProvidedSetTerminalShapeV1 = (
        "SINGLE_TERMINAL_HEAD" if len(terminal_refs) == 1 else "MULTIPLE_TERMINAL_HEADS"
    )
    observation_set_sha256 = _observation_set_sha256(
        scope=scope,
        observation_refs=observation_refs,
    )
    try:
        result = FreshStatusExplicitFiniteChainReplayResultV1.model_validate(
            {
                "subject_closure": scope.subject_closure,
                "status_category": scope.status_category,
                "source_kind": scope.source_kind,
                "source_identity_ref_sha256": scope.source_identity_ref_sha256,
                "observation_count": len(observation_refs),
                "observation_set_sha256": observation_set_sha256,
                "observation_refs": observation_refs,
                "genesis_ref": refs_by_id[genesis_id],
                "provided_set_fork_point_refs": fork_refs,
                "provided_set_terminal_head_refs": terminal_refs,
                "provided_set_terminal_shape": terminal_shape,
                "provided_explicit_finite_chain_closure_consistent": True,
                "limitation_codes": _ALL_LIMITATION_CODES,
            },
            strict=True,
            context={
                _RESULT_PROVENANCE_CONTEXT_KEY: _RESULT_PROVENANCE_SENTINEL,
            },
        )
    except ValidationError as exc:
        raise RealAssetFreshStatusChainReplayV30Error(
            "INTERNAL_RESULT_INCONSISTENCY",
            "the derived non-persistent replay result is internally inconsistent",
        ) from exc
    return _require_replay_result_provenance(result)


__all__ = [
    "FRESH_STATUS_CHAIN_REPLAY_V1_PROFILE",
    "FreshStatusProvidedSetTerminalShapeV1",
    "FreshStatusChainReplayErrorCodeV1",
    "FreshStatusExplicitFiniteChainReplayResultV1",
    "RealAssetFreshStatusChainReplayV30Error",
    "verify_fresh_status_explicit_finite_source_chain_v1",
]
