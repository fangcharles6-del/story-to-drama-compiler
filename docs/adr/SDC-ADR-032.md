# SDC-ADR-032: Explicit Finite Fresh Status Source-Chain Replay v3.0

- Status: Accepted; synthetic implementation only
- Date: 2026-08-23
- Depends on: SDC-ADR-031 / Fresh Status Evidence v3.0 Slice 1
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: explicit synthetic in-memory model objects only

## Context

SDC-ADR-031 freezes five immutable Fresh Status Evidence v3.0 documents and their pure builders,
parsers, compiler and verifiers. A Source Observation may be a `GENESIS`, a one-parent
`SUCCESSOR`, or a two-to-eight-parent `RECONCILIATION`. Slice 1 verifies one immediate link when
the caller explicitly supplies its predecessor or heads, but it does not walk earlier history.

Slice 1 also freezes a future complete-chain replay limit of 64 records and reserves exactly one
narrow proof statement for that later replay:

```text
provided_explicit_finite_chain_closure_consistent=true
```

Without a complete explicit replay, a caller could provide a valid Successor while omitting its
predecessor or describe a Reconciliation whose named heads do not represent distinct branches.
Slice 1 correctly does not reject such an Observation merely because the earlier records were not
supplied. A separate verifier is required to decide whether one caller-provided finite set is
ancestor-closed and graph-consistent. It still cannot detect an unreferenced sibling or any other
branch omitted from that set.

## Decision

Add one separate pure in-memory v3.0 module that replays exactly one explicitly scoped finite
source chain. It accepts an expected chain scope and 1..64 existing immutable Source Observation
models. It resolves every immediate reference inside the supplied set, reuses the frozen Slice 1
link verifier, validates the resulting directed acyclic graph and returns an immutable
non-persistent process result.

The implementation does not add a CLI, path, file reader, file writer, parser, persistent receipt,
Schema, implicit clock, network, Provider, Runtime, entitlement or execution capability.

## Frozen Slice 1 compatibility boundary

Slice 2 must not change any of the following:

- the five Slice 1 top-level models or their Schema bytes;
- the existing 67-entry Schema registry;
- profile `creative-sample-real-asset-fresh-status-evidence-v3.0`;
- policy version `3.0.0` and policy SHA-256
  `ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58`;
- subject-closure profile SHA-256
  `76d151b7a73dcef7aafa6a928e20e024f353ead30fa91a0b7522078eca3f3c7e`;
- canonical JSON, stable-ID projections or the v3.0 chain-digest domain;
- the fixed category, claim, source-kind, basis, limitation and transition sets;
- the existing immediate-link verifier or Evidence Record closure verifier; or
- Request's separate 1..32 Observation limit.

ADR-031 describes the source-chain key as this exact semantic tuple:

```text
closure_id
status_category
source_identity_ref_sha256
source_kind
profile
policy_version
```

The frozen Slice 1 implementation uses complete `subject_closure` object equality in place of a
bare `closure_id` comparison. This is an implementation-level clarification, not a new chain key:
every valid `closure_id` already binds every field of that immutable closure, while full-object
equality also fails closed against a malformed alias. Slice 2 preserves that stronger equality.
The displayed tuple order is descriptive and is not a serialization or sorting order.

The public function requires the first four values as explicit expected scope. Profile and policy
version are frozen Slice 1 constants. The verifier never infers a target chain from the first item
or silently partitions a mixed input set.

A Slice 2 failure means only that the supplied set did not qualify for the narrow complete
explicit-set statement. It does not retroactively make an otherwise valid Slice 1 Observation,
Request, Instruction, Decision or Record Schema-invalid.

## Public API

The only operation is:

```python
verify_fresh_status_explicit_finite_source_chain_v1(
    *,
    subject_closure: FreshStatusSubjectClosureV1,
    status_category: FreshStatusCategoryV1,
    source_kind: FreshStatusSourceKindV1,
    source_identity_ref_sha256: str,
    observations: tuple[
        CreativeSampleRealAssetFreshStatusSourceObservationV1, ...
    ],
) -> FreshStatusExplicitFiniteChainReplayResultV1
```

The input must be an exact tuple. No argument accepts bytes, a stream, a path, a directory, a
clock, an `as_of` value or a Provider handle.

## Admission and canonical set binding

Validation follows a fixed failure order:

1. reject a non-tuple input;
2. reject counts outside 1..64 before examining content;
3. strictly revalidate every Source Observation through the public Slice 1 verifier;
4. render the exact frozen canonical document and enforce the 262,144-byte Observation limit;
5. recompute the full canonical-document SHA-256;
6. recompute the domain-separated chain SHA-256 through the public Slice 1 deriver;
7. sort by `(observation_id, observation_sha256, chain_sha256)`;
8. require IDs, document digests and chain digests to be independently unique; and
9. require every record to match the complete explicit chain scope.

Input tuple order therefore has no semantic effect.

The result binds the exact set through:

```text
SHA256(
  "sdc:creative-sample-real-asset-fresh-status-explicit-chain-set:v1\0"
  || canonical_compact_json(
       replay profile,
       Slice 1 policy SHA-256,
       complete subject closure,
       category,
       source kind,
       source identity reference SHA-256,
       canonically sorted complete Observation references
     )
)
```

This set digest is a deterministic handle, not a signature, authenticity proof or authorization.

## Graph construction

Each Observation is one node. Edges point from named predecessor or branch head to the child:

```text
GENESIS:         no parent
SUCCESSOR:       one exact parent
RECONCILIATION:  two to eight exact parents
```

For a Successor, the verifier requires the named parent ID to exist and independently compares:

```text
previous_observation_id
previous_observation_sha256
previous_chain_sha256
previous_claim_value
```

For each Reconciliation head it independently compares:

```text
observation_id
observation_sha256
chain_sha256
```

A missing ID is an orphan. An existing ID with any mismatched anchor is anchor drift. After exact
resolution, the frozen Slice 1 immediate-link verifier replays same-chain, transition and basis
rules. Slice 2 does not duplicate or weaken those rules.

## DAG invariants

After all edges are resolved, the verifier:

1. performs deterministic Kahn topological traversal;
2. rejects any unconsumed node as a cycle;
3. requires exactly one explicit `GENESIS`;
4. iteratively confirms that every supplied node is reachable from that Genesis;
5. computes ancestor bitsets in topological order; and
6. requires the heads of every Reconciliation to form an ancestry antichain.

An antichain means that no named Reconciliation head is an ancestor or descendant of another
named head. Without this rule, two records from one lineage could be presented as two independent
branches. This is a Slice 2 graph-closure condition; it does not modify the immediate-link shape
accepted by the Slice 1 Observation contract.

Reconciliation heads are not required to have zero out-degree in the final supplied graph.
Topology alone cannot determine whether a different child was recorded before or after a
Reconciliation, and partial reconciliation remains representable.

## Forks, terminals and partial reconciliation

Within the supplied graph:

- out-degree greater than one identifies a fork point;
- out-degree zero identifies a terminal head; and
- all fork and terminal references are returned in canonical reference order.

Multiple terminal heads are a successful structural outcome, not an exception. For example:

```text
G -> A
  -> B
  -> C
R(A, B)
```

has terminal heads `R` and `C`. The supplied graph may be ancestor-closed and internally
consistent while still containing multiple unresolved terminal branches. The result never picks
a winner, latest, favorable or current head and never creates a Reconciliation automatically.

## Time semantics

Each Source Observation retains its own Slice 1 timestamp and half-open-window validation. Slice 2
adds no cross-node chronology rule. In particular, it does not:

- require child `observed_at` to be later than parent `observed_at`;
- sort nodes by any timestamp;
- infer currentness from `valid_until`;
- inspect filesystem timestamps; or
- read a wall clock, environment clock or network time.

Late-observed or backfilled records therefore do not rewrite graph history. Only explicit immutable
links define the graph.

## Non-persistent process result

`FreshStatusExplicitFiniteChainReplayResultV1` is strict, frozen and `extra=forbid`, but it is not a
top-level document contract. It has:

- no stable artifact ID;
- no supported bounded canonical bytes parser or extractor;
- no committed or supported JSON Schema;
- no registration in `sdc.schemas.MODELS`; and
- no filesystem finalizer or receipt semantics.

It includes the explicit scope, complete sorted Observation reference set, set SHA-256, unique
Genesis reference, supplied-set fork references, supplied-set terminal references and terminal
shape. The terminal shape is exactly one of:

```text
SINGLE_TERMINAL_HEAD
MULTIPLE_TERMINAL_HEADS
```

It contains no selected-head or current-status field. A future persistent replay artifact would
require a separate design because a detached summary cannot independently replay the source
documents that its digests name.

The verifier supplies a module-private, process-local provenance context while constructing the
result. A private digest then binds every public result field. Ordinary construction,
`model_validate` and JSON round-trip do not carry that provenance; `model_construct` and a mutated
`model_copy` do not pass the internal provenance check. Every present or future consumer must run
that check before trusting a result as verifier-originated.

This provenance is only an engineering misuse guard. Python reflection and deliberate in-process
memory manipulation are outside the trust boundary, so it is not a signature, security token or
unforgeable proof. Dumped public fields lose verifier provenance and must never be reloaded or
treated as a replay result, receipt or authorization.

## Error taxonomy

Failure raises `RealAssetFreshStatusChainReplayV30Error`. The exception exposes one stable `code`
and emits no partial result:

```text
COUNT_OUT_OF_RANGE
OBSERVATION_CONTRACT_INVALID
DUPLICATE_OBSERVATION_ID
DUPLICATE_OBSERVATION_DOCUMENT_SHA256
DUPLICATE_OBSERVATION_CHAIN_SHA256
CHAIN_SCOPE_MISMATCH
ORPHAN_REFERENCE
REFERENCE_ANCHOR_MISMATCH
IMMEDIATE_LINK_INVALID
CYCLE_DETECTED
GENESIS_COUNT_INVALID
DISCONNECTED_GRAPH
RECONCILIATION_HEAD_ANCESTRY_CONFLICT
INTERNAL_RESULT_INCONSISTENCY
```

Error messages describe the supplied set, never a claim that an omitted real-world source or event
does not exist. No failure triggers repair, discovery, retry, mutation, rollback or quarantine;
the pure function has performed no I/O.

`DISCONNECTED_GRAPH` is a defensive graph-kernel invariant. With strict exact links, an acyclic
graph and exactly one Genesis, it is not expected to be independently reachable through the valid
public model path; it remains explicit to protect future refactors and direct kernel tests.

## Proof boundary

Success permits exactly this narrow statement:

```text
provided_explicit_finite_chain_closure_consistent=true
```

It means that the exact supplied finite set was strictly valid, ancestor-closed, exact-anchor
consistent, single-Genesis reachable, acyclic and compliant with the Reconciliation antichain
rule.

Success does not prove:

- that the source bytes or identity are authentic;
- that any source statement is true;
- that every relevant source, event, ancestor, descendant or fork was supplied;
- that no evidence was hidden, deleted, superseded, backfilled or observed later;
- that SHA-256 is collision-proof as an external factual guarantee;
- that an Observation remains current in reality;
- that rights, identity, policy or legal effect are valid outside the declared closure; or
- that any Provider, generation, execution, publication, retention or training action is allowed.

For that reason the result retains all seven limitation codes, including both:

```text
provided_explicit_finite_chain_closure_consistent=true
CHAIN_COMPLETENESS_NOT_PROVEN
```

These are not contradictory. The first is scoped to ancestor closure inside the exact supplied
set. The second preserves the unproven completeness of the external or undisclosed chain.

## Zero-authority invariant

Every successful result fixes these values; callers cannot override them:

```text
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
generation_authorized=false
execution_authorized=false
publication_authorized=false
remote_processing_allowed=false
retention_allowed=false
training_allowed=false
publication_allowed=false
automated_execution_allowed=false
authorized_attempts=0
authorized_cost_cny=0
posts_allowed=0
provider_requests=0
usage_restriction=MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION
```

The result is not a permit, approval, entitlement, continuation token or machine authorization.

## Implementation boundary

The approved implementation is limited to:

```text
docs/adr/SDC-ADR-032.md
docs/runbooks/SDC-CREATIVE-SAMPLE-REAL-ASSET-FRESH-STATUS-CHAIN-REPLAY-V30.md
src/sdc/real_asset_fresh_status_chain_replay_v30.py
tests/test_real_asset_fresh_status_chain_replay_v30.py
```

The production module may import hashing, canonical JSON, bounded graph utilities, Pydantic and the
public Slice 1 contract functions. It must not import or call filesystem, path, process, network,
Provider, database, queue, Runtime, environment-time or wall-clock facilities.

## Synthetic verification matrix

Tests must use only programmatically generated synthetic model objects and cover:

- 1, 2, 63 and 64 valid linear records; zero and 65 rejected before content processing;
- input reversal, rotation, interleaving and every permutation of a small branching graph;
- unreconciled fork, complete reconciliation and partial reconciliation;
- ancestor-and-descendant Reconciliation heads;
- missing predecessor and missing Reconciliation head;
- ID, document SHA, chain SHA and predecessor-claim drift;
- independent duplicate ID, document-digest and chain-digest guards;
- mixed subject, category, source kind, source identity, profile or policy scope;
- cycle detection at the pure graph kernel and forged-model rejection at the public boundary;
- second Genesis and disconnected reachability;
- exact fork and terminal projection;
- backfilled timestamps having no graph-order effect;
- immutable limitation and zero-authority fields;
- absence of production I/O, implicit-clock, Provider and execution surfaces; and
- unchanged 67-entry Schema registry with exactly five existing Fresh Status Schemas.

Focused tests, Ruff, strict Mypy and the complete offline `make check` must pass. The full check must
run in a new LF-preserving isolated worktree that excludes the repository's current `output/` and
`tmp/` directories.

## Alternatives rejected

### Reuse the Request 1..32 sorter

Rejected because complete history has a separately frozen 1..64 bound and a Request need not
contain every ancestor.

### Infer or partition chains automatically

Rejected because that would hide caller scope errors and turn validation into discovery.

### Require one terminal head

Rejected because an explicit finite graph may be internally consistent while retaining an
unreconciled or partially reconciled fork.

### Add a persistent replay artifact and Schema

Rejected for this slice. A detached receipt cannot independently prove the graph without the exact
Observation documents and could be mistaken for an authorization artifact.

### Use timestamps to select a winner

Rejected because late evidence is permitted and time does not create or rewrite immutable links.

## Slice 2 versioning rule

Any semantic change to the admission/error order, 1..64 bound, set-digest projection or domain,
DAG invariants, Reconciliation antichain rule, fork/terminal projection, result fields or private
provenance semantics requires a new replay profile and result version. A changed digest projection
also requires a new domain separator. Such a change must not silently reinterpret an earlier
in-memory result or golden digest.

## Consequences and deferred work

The positive consequence is a bounded, deterministic and auditable answer to one narrow question:
whether the exact supplied source-chain set is internally closed and structurally consistent.

The cost is that callers must explicitly provide every ancestor and exact chain scope. The verifier
intentionally refuses to discover missing material or simplify multiple terminal heads.

The following remain separately deferred:

- filesystem or trusted-local chain replay;
- a CLI, path profile, finalizer, create-new writer, rollback or quarantine;
- a persistent replay receipt or Schema;
- Evidence Record multi-chain aggregation;
- hidden-branch or source discovery;
- source authenticity and identity-authority validation;
- an explicit-`as_of` current-status assessor;
- automated Reconciliation;
- real evidence or identity material; and
- Provider proposal, selection, contact, Key use, upload, purchase, generation, execution,
  publication, retention or training.

Acceptance, implementation, test success, commit, review or merge of this ADR authorizes none of
those deferred actions. Each requires a new explicit design and approval.
