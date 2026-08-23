# Creative Sample Real-Asset Fresh Status Chain Replay v3.0 Runbook

## Purpose

This runbook covers the pure in-memory verifier defined by SDC-ADR-032. It determines whether one
explicitly supplied finite set of synthetic Fresh Status Source Observations is ancestor-closed and
graph-consistent under the frozen v3.0 rules.

This is a developer verification runbook, not an operational real-data procedure. There is no CLI,
path input, file output, persistent receipt or next-action command.

## Mandatory operator warning

A successful replay means only:

```text
provided_explicit_finite_chain_closure_consistent=true
```

for the exact in-memory set supplied to the function. It does not prove source authenticity,
truth, external completeness, currentness or legal effect. It grants no Provider, generation,
execution or publication authority.

Do not use real identity, rights, hold, revocation, complaint, dispute or policy material under this
runbook. Do not read repository `output/` or `tmp/` data to create a test fixture.

## Supported surface

The single supported operation is:

```python
verify_fresh_status_explicit_finite_source_chain_v1(...)
```

It accepts only:

```text
one explicit FreshStatusSubjectClosureV1
one explicit status_category
one explicit source_kind
one explicit source_identity_ref_sha256
one exact tuple containing 1..64 SourceObservation models
```

It returns `FreshStatusExplicitFiniteChainReplayResultV1` or raises
`RealAssetFreshStatusChainReplayV30Error`. It never returns a partial result.

## Preconditions

Before calling the verifier, confirm all of the following:

1. Every object was generated from synthetic values in memory.
2. Every Source Observation is a frozen v3.0 model.
3. The caller knows the exact intended subject, category, source kind and source identity digest.
4. The tuple contains every predecessor and Reconciliation head referenced by every included node.
5. The tuple contains no more than 64 records.
6. No success result will be treated as current-state assessment or authorization.

Do not infer the scope from an Observation filename, tuple position, timestamp or favorable claim.

## Chain key

Every supplied Observation must match this exact key:

```text
closure_id, enforced through complete subject_closure object equality
status_category
source_identity_ref_sha256
source_kind
profile
policy_version
```

ADR-031 names `closure_id` in the semantic key. Slice 1 actually compares the complete immutable
closure object, whose valid ID already binds every field. Slice 2 preserves that stronger
implementation equality; it does not define a different key.

Multiple source identities are multiple chains even when they concern the same subject and
category. The verifier rejects a mixed tuple; it does not partition it.

## Input limits

| Resource | Inclusive limit |
| --- | ---: |
| Source Observations in one replay | 1..64 |
| Canonical bytes per Source Observation | 262,144 |
| Reconciliation heads per Observation | 2..8 |
| JSON depth inside each existing Observation | 32 |

The count check happens before content traversal. Zero or 65 records fail; the implementation does
not truncate, sample or partially replay the tuple.

## What the verifier checks

For every supplied Observation it:

1. runs strict Slice 1 internal revalidation;
2. renders the exact canonical document;
3. checks its canonical byte bound;
4. recomputes its document SHA-256;
5. recomputes its domain-separated chain SHA-256;
6. verifies independent ID and digest uniqueness; and
7. compares the complete explicit chain scope.

It then resolves every link:

- `GENESIS` receives no predecessor;
- `SUCCESSOR` resolves one exact ID/document-SHA/chain-SHA/claim tuple;
- `RECONCILIATION` resolves every exact ID/document-SHA/chain-SHA head.

The existing Slice 1 link verifier is called for every node. The replay then checks acyclicity,
exactly one Genesis, reachability and Reconciliation-head ancestry antichains.

## Determinism

The input tuple may arrive in any order. The verifier normalizes it by:

```text
(observation_id, observation_sha256, chain_sha256)
```

Graph traversal uses the same canonical key whenever more than one node is ready. Fork references,
terminal references and the set SHA-256 are therefore invariant under input permutation.

Do not interpret the internal topological traversal as chronological order. No traversal order is
returned as a historical or temporal claim.

## Fork and terminal interpretation

A node with more than one supplied child is a supplied-set fork point. A node with no supplied
child is a supplied-set terminal head.

An unreconciled fork is allowed:

```text
G -> A
  -> B
```

The result has terminal heads `A` and `B` and shape `MULTIPLE_TERMINAL_HEADS`.

A complete supplied-set reconciliation is allowed:

```text
G -> A
  -> B
R(A, B)
```

The result has terminal head `R` and shape `SINGLE_TERMINAL_HEAD`.

Partial reconciliation is also allowed:

```text
G -> A
  -> B
  -> C
R(A, B)
```

The result has terminal heads `R` and `C`. It must not be reported as globally resolved or
complete.

## Reconciliation antichain rule

Every pair of heads named by one Reconciliation must represent topology branches: neither may be
an ancestor of the other.

This graph fails:

```text
G -> A -> B
R(G, B)
```

`G` and `B` are two unique records, but they are one lineage rather than two branches. The failure
code is `RECONCILIATION_HEAD_ANCESTRY_CONFLICT`.

The verifier does not require named heads to remain global terminals in the final graph. A later or
parallel explicit child can keep another branch open.

## Time handling

The verifier reads no clock and performs no currentness assessment. Existing Source Observations
still enforce their own timestamp format and validity-window invariants, but chain edges do not
require parent-to-child timestamp monotonicity.

Never describe a terminal head as latest or current. A terminal is only a node with no child inside
the exact supplied tuple.

## Success result checklist

On success, confirm:

- `observation_count` equals the complete canonical reference count;
- `genesis_ref` is present in `observation_refs`;
- fork and terminal references are sorted exact subsets;
- `provided_set_terminal_shape` matches the terminal count;
- `observation_set_sha256` binds the explicit scope and complete reference set;
- `provided_explicit_finite_chain_closure_consistent=true`;
- all seven limitation codes remain present; and
- every zero-authority field retains its fixed value.

The result intentionally has no stable artifact ID, supported canonical parser, committed Schema,
selected head or current-state field. Do not serialize it as a repository contract or present it
as a receipt.

Only the value returned by the verifier carries process-local provenance. The verifier binds all
public result fields to a private in-memory provenance digest and checks it before returning.
Ordinary construction, JSON reload, `model_construct` or a mutated `model_copy` does not establish
or preserve verifier provenance. Any dump is diagnostic public data only; it loses provenance and
must not be reloaded as a result.

The private provenance mechanism prevents ordinary accidental misuse. It is not a signature,
security token or protection against deliberate Python reflection or memory manipulation.

## Fixed zero-authority result

Every successful result must contain:

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

These are immutable facts, not defaults that a caller may replace.

## Failure handling

Catch only `RealAssetFreshStatusChainReplayV30Error` at the domain boundary and use its stable
`code`. Do not parse human-readable error sentences as an API.

| Code | Meaning inside the supplied set |
| --- | --- |
| `COUNT_OUT_OF_RANGE` | The tuple does not contain 1..64 records. |
| `OBSERVATION_CONTRACT_INVALID` | A record or tuple violates the strict immutable boundary. |
| `DUPLICATE_OBSERVATION_ID` | At least two records share an Observation ID. |
| `DUPLICATE_OBSERVATION_DOCUMENT_SHA256` | At least two records share a canonical document digest. |
| `DUPLICATE_OBSERVATION_CHAIN_SHA256` | At least two records share a chain digest. |
| `CHAIN_SCOPE_MISMATCH` | A record does not match the explicit chain key. |
| `ORPHAN_REFERENCE` | A named predecessor or head is absent from the tuple. |
| `REFERENCE_ANCHOR_MISMATCH` | A present record does not match all named anchors. |
| `IMMEDIATE_LINK_INVALID` | Slice 1 same-chain, transition or basis replay failed. |
| `CYCLE_DETECTED` | The resolved supplied graph is cyclic. |
| `GENESIS_COUNT_INVALID` | The supplied graph does not contain exactly one Genesis. |
| `DISCONNECTED_GRAPH` | Defensive invariant: a supplied node is unreachable from the one Genesis. |
| `RECONCILIATION_HEAD_ANCESTRY_CONFLICT` | Named heads do not form an ancestry antichain. |
| `INTERNAL_RESULT_INCONSISTENCY` | A derived result violated its own strict invariants. |

Failure requires the caller to stop. The function performs no write, so there is no rollback,
quarantine or automatic repair. Do not retry with discovered, scanned or silently dropped records.

## Proof and non-proof checklist

Permitted after success:

> The exact explicitly supplied finite Source Observation set was internally ancestor-closed,
> anchor-consistent, single-Genesis reachable, acyclic and compliant with the Reconciliation
> antichain rule.

Forbidden after success:

- the chain is globally complete;
- every relevant branch was found;
- the source or identity is authentic;
- the source statement is true;
- the terminal head is latest, current, valid or legally effective;
- a favorable claim clears the subject;
- any Provider or execution action may proceed.

The result retains `CHAIN_COMPLETENESS_NOT_PROVEN` because external completeness remains unproven.

## Synthetic focused validation

Run only against generated synthetic in-memory objects:

```text
uv run pytest -q tests/test_real_asset_fresh_status_chain_replay_v30.py
uv run pytest -q tests/test_real_asset_fresh_status_evidence_v30.py
uv run ruff format --check \
  src/sdc/real_asset_fresh_status_chain_replay_v30.py \
  tests/test_real_asset_fresh_status_chain_replay_v30.py
uv run ruff check \
  src/sdc/real_asset_fresh_status_chain_replay_v30.py \
  tests/test_real_asset_fresh_status_chain_replay_v30.py
uv run mypy src/sdc/real_asset_fresh_status_chain_replay_v30.py
```

The focused matrix must cover linear limits, all small-graph permutations, fork shapes,
Reconciliation antichains, missing references, anchor drift, independent duplicate guards, graph
kernel cycles, reachability, backfilled timestamps, result immutability, zero authority, production
purity and unchanged Schema registration.

## Full offline validation

Before any later commit approval:

1. Confirm the diff contains only the four approved Slice 2 paths.
2. Confirm existing Slice 1 source, policy and five Schema files are byte-unchanged.
3. Create a new LF-preserving isolated worktree from the current HEAD.
4. Materialize only the four approved working files into that worktree.
5. Do not copy, enumerate or read the current repository's `output/` or `tmp/` directories.
6. Run `make check` offline in the isolated worktree.
7. Confirm the isolated validation creates no tracked change.
8. Safely remove only the verified temporary worktree after the check completes.

Full validation success does not authorize commit, push, PR, merge or real-data use.

## Static purity checklist

The production module must contain no import or call surface for:

```text
os
pathlib
open
subprocess
socket
httpx / requests / urllib
datetime.now / datetime.utcnow / time.time
Provider / Runtime / Worker / database / queue adapters
```

Hashing, canonical JSON, bounded iterative graph operations, Pydantic and public Slice 1 pure
functions are permitted.

## Version lock

Do not change the admission/error order, 1..64 bound, set-digest projection or domain, DAG or
antichain rules, fork/terminal projection, result fields or provenance behavior under the existing
replay profile. Any semantic change requires a new replay profile and result version; a digest
projection change also requires a new domain separator and new reviewed golden digest.

## Explicit stop conditions

Stop without repair or scope expansion if:

- the tuple is not exact or exceeds 64 records;
- any record fails strict revalidation;
- any independent identity or digest collision guard fires;
- an explicit chain scope differs;
- a predecessor or head is missing;
- an anchor, transition or basis differs;
- the graph has a cycle, wrong Genesis count or unreachable node;
- Reconciliation heads contain an ancestor relationship;
- any test, lint, type or Schema lock fails; or
- any filesystem, clock, Provider or execution surface appears in production code.

## Deferred work

This runbook does not authorize or describe:

- trusted-local or filesystem replay;
- path discovery, path admission or checklist generation;
- create-new writing, rollback or quarantine;
- a persistent replay report or Schema;
- multi-chain Evidence Record aggregation;
- hidden-branch discovery;
- source authenticity or identity authority;
- current-status assessment at an explicit `as_of`;
- automatic Reconciliation;
- real status evidence; or
- Provider proposal, contact, upload, purchase, generation, execution, publication, retention or
  training.

There is no automatic next operation after a successful replay. The correct action is to report
the bounded technical result and stop. Every later capability requires a separate explicit design
and approval.
