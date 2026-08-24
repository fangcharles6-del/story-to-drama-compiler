# Creative Sample Real-Asset Fresh Status Record Chain Coverage v3.0 Runbook

## Purpose

This runbook covers the pure in-memory Slice 3 verifier defined by SDC-ADR-033. It determines
whether every exact Source Observation referenced by one Fresh Status Evidence Record Request is
explicitly targeted exactly once, covered by a freshly replayed logical chain, backed by exactly
the supplied ancestor-and-self closure, and able to rebuild the same immutable Record.

This is a developer verification runbook for synthetic model objects only. It is not an operational
real-data procedure and provides no next-action authority.

## Mandatory warning

A successful call permits only:

```text
provided_evidence_record_request_explicit_chain_coverage_consistent=true
provided_evidence_record_rebuild_consistent=true
```

for the exact Record, targets and Source Observation occurrences supplied in that call.

It does not prove source authenticity, truth, external completeness, currentness, legal effect or
identity authority. It does not authorize Provider access, proposal design, upload, purchase,
generation, execution, publication, retention or training.

Do not use real identity, rights, hold, revocation, complaint, dispute, policy or Provider material.
Do not read repository `output/` or `tmp/` data to construct a fixture.

## Supported surface

The public operation is:

```python
verify_fresh_status_evidence_record_explicit_chain_coverage_v1(
    *,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> FreshStatusEvidenceRecordChainCoverageResultV1
```

The public Slice 3 names are:

```text
FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE
FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES
FreshStatusRecordChainInputV1
FreshStatusRecordChainCoverageSummaryV1
FreshStatusEvidenceRecordChainCoverageResultV1
FreshStatusRecordChainCoverageErrorCodeV1
RealAssetFreshStatusRecordChainCoverageV30Error
verify_fresh_status_evidence_record_explicit_chain_coverage_v1
```

No supported API accepts bytes, a file, path, directory, stream, URL, environment value, clock,
`as_of`, Provider handle or discovery callback.

## Profiles and fixed limits

```text
coverage profile:
creative-sample-real-asset-fresh-status-record-chain-coverage-v1

Slice 2 replay profile:
creative-sample-real-asset-fresh-status-explicit-chain-replay-v1

Slice 1 evidence profile:
creative-sample-real-asset-fresh-status-evidence-v3.0

Slice 1 policy version:
3.0.0

Slice 1 policy SHA-256:
ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58
```

| Resource | Inclusive limit |
| --- | ---: |
| Chain inputs | 1..32 |
| Request targets per chain input | 1..32 |
| Source Observation occurrences per chain input | 1..64 |
| Aggregate supplied Source Observation canonical bytes | 1..16,777,216 |

The byte total counts every occurrence in every chain input. It does not deduplicate repeated
objects before charging the budget. Individual Slice 1 and Slice 2 limits remain in force.

## Input model

Construct each `FreshStatusRecordChainInputV1` with:

```text
status_category
source_kind
source_identity_ref_sha256
request_target_refs
observations
```

`request_target_refs` must use full `FreshStatusObservationRefV1` values. Copy the exact five-field
reference from the Record Request; do not reconstruct it from a filename or type only.

`observations` must contain exactly the union of:

- every explicit target in that logical chain; and
- every ancestor required to reach those targets from the one exact Genesis.

Do not add an untargeted sibling, target descendant or other convenient support record.

## Logical-chain grouping

One chain input represents one exact logical chain identified within the Record by:

```text
status_category
source_kind
source_identity_ref_sha256
full Genesis reference
```

The full Genesis reference means:

```text
genesis observation_id
genesis observation_sha256
genesis chain_sha256
```

All accepted chains also bind the Record's complete subject closure and the fixed Slice 1 profile
and policy version.

Do not split one scope-and-Genesis chain across inputs. The verifier rejects that as
`DUPLICATE_LOGICAL_CHAIN`. The same category, kind and identity with two different exact Genesis
records is allowed as two logical chains; this does not prove those roots are related or unrelated
in reality.

## Preconditions

Before a synthetic call, confirm:

1. `record` is an existing immutable v3.0 Fresh Status Evidence Record model.
2. `chains` is an exact tuple and contains 1..32 inputs.
3. Every chain input is a strict `FreshStatusRecordChainInputV1`.
4. Every chain input declares 1..32 full Request target references.
5. Every chain input supplies 1..64 immutable Source Observation models.
6. Every target was copied exactly from `record.request.observation_refs`.
7. Every Request reference is targeted in one and only one chain input.
8. Every supplied chain includes all named predecessors and Reconciliation heads.
9. Each logical chain appears in only one input.
10. Every non-target Observation is an ancestor of at least one target.
11. Aggregate canonical bytes of all supplied occurrences do not exceed 16 MiB.
12. The call uses synthetic in-memory values only.
13. No Result dump will be stored or treated as a receipt.
14. No successful outcome will be treated as authorization or current-state proof.

## Canonical reference order

References are normalized by:

```text
(observation_id, observation_sha256, chain_sha256)
```

Coverage summaries are normalized by:

```text
(
  status_category,
  source_kind,
  source_identity_ref_sha256,
  genesis_ref.observation_id,
  genesis_ref.observation_sha256,
  genesis_ref.chain_sha256,
  observation_set_sha256,
)
```

Caller order does not select a chain, target, ancestor, fork or terminal. Permuting otherwise
identical valid tuples must produce the same Result and `coverage_set_sha256`.

## Verification sequence

The verifier performs these phases in order.

### 1. Admit the chain collection

- require `chains` to be an exact tuple;
- enforce 1..32 inputs before traversing content;
- directly strict-revalidate every complete chain-input instance tree, including all target refs
  and Source Observations;
- enforce every target tuple at 1..32 occurrences;
- enforce every Observation tuple at 1..64 occurrences; and
- sum the Slice 1 canonical-document byte length of every supplied Observation occurrence.

Do not validate only a `model_dump` projection. An undeclared field injected into an outer chain
input or embedded model through `model_copy` or equivalent trusted-object mutation must fail as
`CHAIN_INPUT_CONTRACT_INVALID` before either nested count is considered.

The aggregate byte check occurs before the Record is inspected and before replay or duplicate
analysis. A repeated occurrence is still charged.

### 2. Verify the Record

First directly strict-revalidate the complete existing Record instance tree, including Request,
Instruction and Decision. Do not validate only a `model_dump` projection. Hidden outer or nested
extras injected through `model_copy` or equivalent trusted-object mutation fail as
`EVIDENCE_RECORD_INVALID`. Then run the public Slice 1 internal Record verifier. The Record must
preserve its three physical modules, independent canonical digests, stable IDs, deterministic
Decision and zero-authority fields.

This phase does not replay Frozen Pack, Rights Manifest, Use Plan or Use Scope Review objects.

### 3. Establish exact global Request targets

Across all chain inputs:

- reject an exact Request Observation reference targeted more than once;
- compare all five target-reference fields to the matching Request reference;
- reject target IDs absent from the Record Request; and
- reject every Record Request reference that is not targeted.

Do not proceed to chain replay until the complete Request target set is exact.

### 4. Freshly replay every chain

For each chain input, call the Slice 2 verifier with the Record subject closure and the input's
explicit category, source kind, source identity digest and Observation tuple.

Accept only the provenance-bearing value returned by that call. Do not reload a Slice 2 Result
dump. If replay fails, stop with `CHAIN_REPLAY_FAILED` and inspect the nested `replay_code`.

### 5. Reject logical and cross-chain aliases

Require one input per exact logical-chain key. Then independently reject any cross-chain duplicate:

```text
observation_id
observation_sha256
chain_sha256
observation_set_sha256
```

Do not merge or deduplicate overlapping inputs.

### 6. Apply the three global chain postcondition passes

The following are collection-wide passes over all canonically ordered replay results. Never
interleave these checks per chain.

Pass 1: resolve every declared target to the same full reference in its freshly replayed chain. If
any target is unresolved, return the canonical first `REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN` before
examining any target-set mismatch or unrelated support fault.

Pass 2: for every chain compute:

```text
replayed observation_refs ∩ Record Request observation_refs
```

using full five-field equality. The canonically sorted intersection must exactly equal that input's
canonically sorted `request_target_refs`. `CHAIN_TARGET_SET_MISMATCH` is a defensive consistency
guard. With the current earlier public invariants it is normally unreachable: global targets
already cover the Record exactly once, every target has resolved, and cross-chain collisions have
already failed closed. Exercise this guard through a private pure symbolic comparison helper; do
not weaken an earlier public invariant merely to reach it.

Pass 3: check ancestor-and-self exhaustion for every chain. Walk resolved edges backward from each
explicit target. Build the union of every target and all of its supplied ancestors. Require that
union to equal the complete replayed Observation set. Only after passes 1 and 2 complete may an
`UNRELATED_SUPPORT_OBSERVATION` be selected.

The following are allowed:

- one Genesis that is itself the only target;
- one Successor target with its complete predecessor path;
- one Reconciliation target with every head and every head ancestor;
- multiple targets on different unresolved branches; and
- one target that is an ancestor of another target.

The following fail as `UNRELATED_SUPPORT_OBSERVATION`:

- an untargeted sibling branch;
- an untargeted child or later descendant of a target;
- an otherwise valid node that is not an ancestor of any target; or
- padding the chain input with a convenient but irrelevant Observation.

### 7. Rebuild the exact Record

Resolve the Source Observation object for each Request target and exclude non-target supporting
ancestors from the builder input. Rebuild through public Slice 1 functions:

```text
build_fresh_status_request_v1
  using original closure, preparer identity, requested_at and request_basis

build_fresh_status_instruction_v1
  using rebuilt Request, exact target Observations,
  original checker identity, evaluated_at and checker_basis

build_fresh_status_evidence_record_v1
  using rebuilt Request and Instruction
```

The final builder deterministically compiles the Decision. Require exact equality with the supplied
strictly verified Request, Instruction, Decision, module digests and outer Record.

### 8. Derive summaries, digest and Result

For each chain, copy only freshly replayed fields into a
`FreshStatusRecordChainCoverageSummaryV1`, add exact target and supporting-ancestor subsets, then
sort every summary canonically.

Derive all counts and the coverage-set digest. Construct the outer Result only under the module's
private provenance context and verify that provenance before returning.

## Success summary fields

Each chain summary contains:

```text
status_category
source_kind
source_identity_ref_sha256
observation_count
observation_set_sha256
observation_refs
genesis_ref
provided_set_fork_point_refs
provided_set_terminal_head_refs
provided_set_terminal_shape
request_target_refs
supporting_ancestor_refs
provided_explicit_finite_chain_closure_consistent=true
```

`request_target_refs` and `supporting_ancestor_refs` are disjoint, sorted and exhaustive subsets of
the summary's `observation_refs`.

## Success Result fields

The outer `FreshStatusEvidenceRecordChainCoverageResultV1` includes:

```text
result_type=FRESH_STATUS_EVIDENCE_RECORD_CHAIN_COVERAGE_RESULT_V1
coverage_profile=creative-sample-real-asset-fresh-status-record-chain-coverage-v1
source_chain_replay_profile
source_evidence_profile
source_evidence_policy_version
source_evidence_policy_document_sha256
evidence_record_id
evidence_record_sha256
request_id
request_sha256
subject_closure
request_observation_count
request_observation_refs
chain_count
chain_coverages
covered_request_observation_count
provided_observation_count
supporting_ancestor_observation_count
coverage_set_sha256
provided_evidence_record_request_explicit_chain_coverage_consistent=true
provided_evidence_record_rebuild_consistent=true
limitation_codes
status=FRESH_STATUS_EVIDENCE_RECORD_CHAIN_COVERAGE_CONSISTENT
all fixed zero-authority fields
```

Per-chain Slice 2 consistency is expressed by the freshly invoked public Slice 2 verifier and each
summary's `provided_explicit_finite_chain_closure_consistent=true`; it is not duplicated as an
outer aggregate boolean.

Confirm these count equations:

```text
request_observation_count
== covered_request_observation_count
== len(request_observation_refs)

chain_count == len(chain_coverages)

provided_observation_count
== sum(chain.observation_count for chain in chain_coverages)

supporting_ancestor_observation_count
== sum(len(chain.supporting_ancestor_refs) for chain in chain_coverages)

provided_observation_count
== covered_request_observation_count
   + supporting_ancestor_observation_count
```

## Coverage-set digest

The Result derives:

```text
SHA256(
  "sdc:creative-sample-real-asset-fresh-status-record-chain-coverage-set:v1\0"
  || canonical_compact_json(projection)
)
```

The projection binds:

```text
coverage_profile
source_chain_replay_profile
source_evidence_profile
source_evidence_policy_version
source_evidence_policy_document_sha256
evidence_record_id
full canonical Evidence Record SHA-256
request_id
request_sha256
complete subject_closure
request_observation_count
complete sorted request_observation_refs
chain_count
covered_request_observation_count
provided_observation_count
supporting_ancestor_observation_count
complete sorted chain_coverages
```

The projection excludes the digest itself, status, limitation codes and zero-authority fields.
Private Result provenance binds every public field, including those fixed excluded fields.

## Process-local provenance handling

Only the value returned directly by the verifier has process-local provenance. The private digest
uses:

```text
sdc:creative-sample-real-asset-fresh-status-record-chain-coverage-provenance:v1\0
```

and binds every public Result field.

Do not:

- construct the Result directly;
- use ordinary `model_validate` to recreate one;
- reload a JSON or Python dump;
- use `model_construct`;
- trust a mutated `model_copy`; or
- serialize the Result as a repository or external receipt.

The private provenance guard prevents ordinary accidental misuse. It is not a signature,
attestation, security token or defense against deliberate Python reflection or memory mutation.

## Fixed failure order

Catch only `RealAssetFreshStatusRecordChainCoverageV30Error` at the domain boundary and use its
stable `code`. Inspect optional `replay_code` only when `code == CHAIN_REPLAY_FAILED`.

```text
CHAIN_COLLECTION_CONTRACT_INVALID
CHAIN_COUNT_OUT_OF_RANGE
CHAIN_INPUT_CONTRACT_INVALID
TARGET_COUNT_OUT_OF_RANGE
OBSERVATION_COUNT_OUT_OF_RANGE
AGGREGATE_CANONICAL_BYTES_OUT_OF_RANGE
EVIDENCE_RECORD_INVALID
REQUEST_TARGET_COVERED_MULTIPLE_TIMES
REQUEST_TARGET_ANCHOR_MISMATCH
REQUEST_TARGET_NOT_IN_RECORD
REQUEST_OBSERVATION_NOT_COVERED
CHAIN_REPLAY_FAILED
DUPLICATE_LOGICAL_CHAIN
CROSS_CHAIN_DUPLICATE_OBSERVATION_ID
CROSS_CHAIN_DUPLICATE_OBSERVATION_DOCUMENT_SHA256
CROSS_CHAIN_DUPLICATE_OBSERVATION_CHAIN_SHA256
CROSS_CHAIN_DUPLICATE_OBSERVATION_SET_SHA256
REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN
CHAIN_TARGET_SET_MISMATCH
UNRELATED_SUPPORT_OBSERVATION
RECORD_REBUILD_MISMATCH
INTERNAL_RESULT_INCONSISTENCY
```

The final three chain-postcondition categories are three complete global passes in the displayed
order: unresolved targets, target-set mismatches, then unrelated support Observations. They are not
interleaved per chain. `CHAIN_TARGET_SET_MISMATCH` is retained as a defensive consistency guard and
is normally unreachable after the current earlier public invariants; test its pure comparison
through the private symbolic helper.

| Code | Required response |
| --- | --- |
| `CHAIN_COLLECTION_CONTRACT_INVALID` | Stop; supply the exact tuple type. |
| `CHAIN_COUNT_OUT_OF_RANGE` | Stop; do not truncate or sample chain inputs. |
| `CHAIN_INPUT_CONTRACT_INVALID` | Stop; correct the synthetic immutable input explicitly. |
| `TARGET_COUNT_OUT_OF_RANGE` | Stop; do not drop or infer targets. |
| `OBSERVATION_COUNT_OUT_OF_RANGE` | Stop; do not trim a chain. |
| `AGGREGATE_CANONICAL_BYTES_OUT_OF_RANGE` | Stop; do not deduplicate or partially replay to bypass the budget. |
| `EVIDENCE_RECORD_INVALID` | Stop; do not repair or rewrite the Record. |
| `REQUEST_TARGET_COVERED_MULTIPLE_TIMES` | Stop; assign each Request ID exactly once. |
| `REQUEST_TARGET_ANCHOR_MISMATCH` | Stop; use the exact five-field Request reference. |
| `REQUEST_TARGET_NOT_IN_RECORD` | Stop; do not add an inferred target. |
| `REQUEST_OBSERVATION_NOT_COVERED` | Stop; explicitly cover the omitted Request reference. |
| `CHAIN_REPLAY_FAILED` | Stop; report the nested Slice 2 `replay_code`; do not retry automatically. |
| `DUPLICATE_LOGICAL_CHAIN` | Stop; provide one complete input for the logical chain. |
| `CROSS_CHAIN_DUPLICATE_OBSERVATION_ID` | Stop; do not alias or merge the inputs. |
| `CROSS_CHAIN_DUPLICATE_OBSERVATION_DOCUMENT_SHA256` | Stop; report the exact collision guard. |
| `CROSS_CHAIN_DUPLICATE_OBSERVATION_CHAIN_SHA256` | Stop; report the exact collision guard. |
| `CROSS_CHAIN_DUPLICATE_OBSERVATION_SET_SHA256` | Stop; do not treat the set as a second chain. |
| `REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN` | Stop; supply the exact target document in its declared chain. |
| `CHAIN_TARGET_SET_MISMATCH` | Stop; this defensive guard indicates an internal invariant regression after the earlier public checks. |
| `UNRELATED_SUPPORT_OBSERVATION` | Stop; remove only after explicit human correction of the declared synthetic input. |
| `RECORD_REBUILD_MISMATCH` | Stop; do not rewrite the existing Record or its modules. |
| `INTERNAL_RESULT_INCONSISTENCY` | Stop; emit no Result and do not retry automatically. |

The verifier performs no write, so failure has no rollback, quarantine or automatic repair phase.

## Synthetic test recipes

### Count and collection boundaries

Use synthetic fixtures for:

```text
chains: 0, 1, 32, 33
targets per chain: 0, 1, 32, 33
observations per chain: 0, 1, 64, 65
```

Use a non-tuple collection and non-tuple nested fields to confirm exact-type failure. Combine count
and malformed-content faults to confirm the frozen priority.

Also inject hidden extras with `model_copy` into an outer chain input and an embedded Source
Observation. Direct strict instance revalidation must reject each as
`CHAIN_INPUT_CONTRACT_INVALID` before target or Observation count errors.

### Aggregate budget

Generate valid unique synthetic Source Observations with controlled canonical padding. Verify total
occurrence sizes at:

```text
16,777,215
16,777,216
16,777,217
```

Count repeated occurrences separately. For the over-limit case, include a later invalid Record or
duplicate to prove the budget failure occurs first.

### Target coverage

Test:

- one exact target;
- duplicate exact target reference inside one input;
- duplicate exact target reference across two inputs;
- independent drift of document SHA, category, source identity SHA and chain SHA for a known ID;
- one unknown target ID; and
- one omitted Request reference.

Assert the exact stable error code, not a human sentence.

Strictly revalidate the complete Record tree after the budget phase. Independently inject one
hidden extra into the outer Record, Request, Instruction and Decision and require
`EVIDENCE_RECORD_INVALID` in every case.

### Nested replay

Use valid synthetic Source Observation models to trigger Slice 2 failures including:

- orphan predecessor;
- predecessor anchor drift;
- mixed chain scope;
- duplicate Observation anchor;
- cycle at the symbolic graph-kernel boundary;
- disconnected graph at the symbolic graph-kernel boundary;
- invalid Genesis count; and
- Reconciliation ancestry conflict.

Assert outer `CHAIN_REPLAY_FAILED` and the exact nested `replay_code` for faults reachable through
strict public models. Cycle and disconnected-graph states that cannot be honestly represented after
Slice 1 validation belong in the Slice 2 private pure graph kernel or symbolic helper tests. Do not
relax a public model merely to claim those symbolic states are reachable through Slice 3.

### Logical and cross-chain boundaries

Test one logical chain split into two inputs and require `DUPLICATE_LOGICAL_CHAIN`. Test two
same-scope inputs with distinct exact Genesis records and require success.

Exercise the independent cross-chain guards for ID, document SHA, chain SHA and set SHA. Use a
small pure internal symbolic helper for cryptographic collision dimensions that cannot be produced
honestly without a SHA-256 collision; do not monkeypatch the production hash functions.

Exercise the defensive target-set comparison with a private pure symbolic helper and require
`CHAIN_TARGET_SET_MISMATCH`. In the supported public verifier, construct a combined fault with an
earlier-sorted chain mismatch and a later-sorted unresolved target and require the global first-pass
error `REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN`. Reverse the caller tuple and require the same error.

### Ancestor-and-self closure

Cover at least:

```text
G                       target G
G -> A                  target A
G -> A -> B             targets A and B
G -> A / B              targets A and B
G -> A / B; R(A, B)     target R
G -> A / B / C; R(A,B)  targets R and C
```

For each success, assert the exact `request_target_refs`, `supporting_ancestor_refs`, fork refs and
terminal refs.

For failures, add an untargeted sibling, an untargeted target descendant and another connected but
non-ancestor node. Each must fail as `UNRELATED_SUPPORT_OBSERVATION` rather than being silently
discarded.

### Record rebuild

Build a normal synthetic Record and require exact success. Then construct a strictly internally
valid synthetic Record whose Instruction/Decision are self-consistent but differ from the
deterministic assessment of the exact target Observation documents. Require
`RECORD_REBUILD_MISMATCH`; do not mutate the target anchors or make the Record internally invalid,
because those belong to earlier error categories. Do not monkeypatch a production builder for this
test; construct the synthetic internally valid mismatch explicitly.

### Determinism

Permute:

- the outer chain-input tuple;
- each input's target tuple; and
- each input's Observation tuple.

Assert complete Result equality, identical sorted summaries and one identical
`coverage_set_sha256`. Include a small graph with exhaustive permutations and a larger bounded
fixture with reversal, rotation and interleaving.

Then change one bound dimension at a time and require digest sensitivity for the exact Record,
Request target, supporting ancestor, chain scope and complete chain summary. Use honest derived
fixtures or private pure digest-projection helpers where a deliberately inconsistent public Result
would be rejected by provenance before it could be constructed.

### Provenance and authority

Confirm:

- direct Result construction fails;
- ordinary strict validation without private context fails;
- JSON and Python dumps cannot be reloaded as Results;
- `model_construct` lacks provenance;
- a mutated `model_copy` fails the provenance check;
- the value returned by the verifier has intact private provenance;
- all seven limitation codes remain fixed; and
- every zero-authority scalar has its exact false or zero JSON type.

### Static safety and compatibility

Inspect the production module AST and fail if it imports or calls filesystem, path, process,
network, Provider, database, queue, environment-clock or wall-clock surfaces.

Confirm:

```text
len(sdc.schemas.MODELS) == 67
exactly five Fresh Status top-level models remain registered
the Slice 3 process models are absent from MODELS
all existing committed Schema files are byte-identical
```

## Proof checklist

After success, it is permissible to say:

> The exact supplied Fresh Status Evidence Record Request targets were covered exactly once by the
> exact freshly replayed finite logical chains, each supplied chain contained exactly the targets
> and their supplied ancestors, and the exact target Observation documents rebuilt the same
> immutable Record.

Do not say:

- the real-world chain is complete;
- every relevant branch or event was found;
- the source or identity is authentic;
- the statements are true;
- the terminals are latest or current;
- the Record is legally effective now;
- the result clears the subject for any use; or
- any Provider or execution action may proceed.

## Zero-authority checklist

Every successful Result must retain:

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

It must also retain:

```text
SOURCE_AUTHENTICITY_NOT_PROVEN
SOURCE_COMPLETENESS_NOT_PROVEN
CHAIN_COMPLETENESS_NOT_PROVEN
REALITY_CURRENTNESS_NOT_PROVEN
SCOPE_LIMITED_TO_DECLARED_SUBJECT
TIME_WINDOW_LIMITED
LEGAL_EFFECT_NOT_DETERMINED
```

## Prohibited actions

This runbook does not authorize:

- reading or writing real project intake, identity, evidence or output material;
- reading repository `output/` or `tmp/` as fixture input;
- filesystem discovery or automatic chain partitioning;
- writing a coverage receipt, Schema or final output;
- creating directories, changing permissions, rollback or quarantine;
- using an implicit or wall clock;
- network or Provider access;
- generation, execution, publication, purchase, contact, upload, retention or training;
- changing Slice 1 or Slice 2 contracts, policies, schemas or digest domains; or
- commit, push, PR, merge, tag, release or deployment without separate approval.

## Verification handoff

Before any later implementation handoff, record only synthetic evidence:

- focused Slice 3 test result;
- unchanged Slice 1 and Slice 2 focused tests;
- Ruff result;
- strict Mypy result;
- exact Schema registry and byte-lock result; and
- complete offline `make check` result from a fresh LF-preserving isolated worktree that excludes
  the current repository `output/` and `tmp/` directories.

Test success remains `HUMAN_GATE / NOT_AUTHORIZED`. It does not authorize a commit, push, PR,
merge, persistent finalizer, real-data operation or Provider action.
