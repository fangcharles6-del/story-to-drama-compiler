# SDC-ADR-033: Fresh Status Evidence Record Chain Coverage v3.0

- Status: Accepted; synthetic implementation only
- Date: 2026-08-23
- Depends on: SDC-ADR-031 / Fresh Status Evidence v3.0 Slice 1
- Depends on: SDC-ADR-032 / Explicit Finite Fresh Status Source-Chain Replay v3.0 Slice 2
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: explicit synthetic in-memory model objects only

## Context

SDC-ADR-031 defines the immutable Fresh Status Source Observation, Request, Instruction, Decision
and Evidence Record contracts. A Request binds between one and 32 exact Source Observation
references, but the Record does not embed the Observation documents or their ancestors.

SDC-ADR-032 adds a pure in-memory replay for one explicitly scoped logical source chain. Given one
exact 1..64 Observation set, it proves only that the provided finite set is internally
ancestor-closed, exact-anchor consistent, single-Genesis reachable, acyclic and compliant with the
Reconciliation antichain rule.

Neither slice answers the Record-level question: whether every Observation referenced by one exact
Evidence Record Request has been explicitly assigned to exactly one logical chain, whether each
chain input contains exactly the ancestors and targets needed for those Request observations, and
whether the exact target Observation documents deterministically rebuild the existing Request,
Instruction, Decision and outer Record.

Slice 3 answers only that narrow question. It does not discover chains, infer targets, fetch
ancestors, assess currentness or create a persistent coverage receipt.

## Decision

Add one separate pure in-memory v3.0 module that verifies explicit chain coverage for one existing
Fresh Status Evidence Record.

The caller supplies:

- one exact immutable `CreativeSampleRealAssetFreshStatusEvidenceRecordV1`; and
- an exact tuple of 1..32 `FreshStatusRecordChainInputV1` values.

Each chain input explicitly declares one logical chain scope, one or more full Request target
references and the exact Source Observation documents supplied for that chain. The verifier never
partitions an Observation collection, infers a target from a terminal head, discovers an ancestor
or selects a favorable branch.

On success it returns one strict, frozen, non-persistent
`FreshStatusEvidenceRecordChainCoverageResultV1`. Success permits exactly these two narrow
statements:

```text
provided_evidence_record_request_explicit_chain_coverage_consistent=true
provided_evidence_record_rebuild_consistent=true
```

The implementation adds no CLI, parser, path profile, filesystem reader or writer, persistent
receipt, committed Schema, implicit clock, network, Provider, Runtime, entitlement or execution
capability.

## Frozen compatibility boundary

Slice 3 must not change:

- any of the five Slice 1 top-level models or their Schema bytes;
- the 67-entry Schema registry;
- the Slice 1 evidence profile
  `creative-sample-real-asset-fresh-status-evidence-v3.0`;
- Slice 1 policy version `3.0.0` or policy SHA-256
  `ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58`;
- Slice 1 canonical JSON, stable-ID, source-chain or Record projections;
- the Request limit of 1..32 Observation references;
- the Slice 2 replay profile
  `creative-sample-real-asset-fresh-status-explicit-chain-replay-v1`;
- the Slice 2 1..64 chain bound, graph invariants, error semantics, set-digest projection or
  process-local provenance rules; or
- any upstream Frozen Pack, Rights Manifest, Use Plan or Use Scope Review contract.

A Slice 3 failure does not make a previously valid Slice 1 document Schema-invalid and does not
rewrite a Slice 2 replay result. It means only that the supplied Record and explicit chain inputs
did not satisfy this additional coverage boundary.

## Frozen profile and resource constant

The coverage profile is:

```text
FRESH_STATUS_RECORD_CHAIN_COVERAGE_V1_PROFILE
= creative-sample-real-asset-fresh-status-record-chain-coverage-v1
```

The aggregate supplied-source byte budget is:

```text
FRESH_STATUS_RECORD_CHAIN_COVERAGE_MAX_SOURCE_BYTES
= 16_777_216
```

The budget is exactly 16 MiB. It is the sum of the Slice 1 canonical-document byte length of every
supplied Source Observation occurrence across all chain inputs. The same Observation supplied in
two inputs is charged twice even though later semantic validation rejects the cross-chain
duplicate. The Record bytes, target-reference bytes, input-model overhead and derived result bytes
are not included.

The bound is inclusive. A total of 16,777,216 bytes is admitted; 16,777,217 bytes is rejected. No
input is truncated, sampled, deduplicated or partially replayed to fit the budget.

## Public API

The Slice 3 public surface is limited to:

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

The only operation is:

```python
verify_fresh_status_evidence_record_explicit_chain_coverage_v1(
    *,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> FreshStatusEvidenceRecordChainCoverageResultV1
```

The function accepts existing in-memory models only. It accepts no bytes, stream, path, directory,
clock, `as_of`, Provider handle or discovery callback.

## Explicit chain input

`FreshStatusRecordChainInputV1` is strict, frozen, `extra=forbid` and contains exactly:

```text
status_category
source_kind
source_identity_ref_sha256
request_target_refs
observations
```

`request_target_refs` is an exact tuple of full `FreshStatusObservationRefV1` values. A target is
not merely an Observation ID. It binds:

```text
observation_id
observation_sha256
status_category
source_identity_ref_sha256
chain_sha256
```

`observations` is an exact tuple of existing immutable Source Observation models. Input order has
no semantic effect. The verifier normalizes targets, Observation references, coverage summaries
and all derived subsets before comparing or hashing them.

Before either nested count is examined, Slice 3 directly strict-revalidates the complete existing
`FreshStatusRecordChainInputV1` instance tree. This is instance revalidation, not validation of a
`model_dump` projection: it revisits every target reference and Source Observation and rejects
undeclared instance state injected through `model_copy` or equivalent trusted-object mutation. A
hidden extra at the outer input or anywhere in an embedded model fails closed as
`CHAIN_INPUT_CONTRACT_INVALID`.

Each chain input has these inclusive bounds:

| Resource | Allowed |
| --- | ---: |
| Request targets in one chain input | 1..32 |
| Source Observations in one chain input | 1..64 |

The outer `chains` tuple contains 1..32 inputs. The maximum follows from the Slice 1 Request limit
and the requirement that every chain input declare at least one Request target.

## Fixed admission and failure order

The verifier applies the following error categories in this exact order:

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

This order is part of the Slice 3 contract. In particular:

1. a non-tuple chain collection fails before its count is examined;
2. the 1..32 chain count fails before chain content is traversed;
3. every chain input is strictly revalidated before target and Observation count checks;
4. all target-count failures precede all Observation-count failures;
5. the aggregate occurrence-byte budget is enforced before the Evidence Record is examined;
6. the Record is strictly verified before target coverage is interpreted;
7. complete Request target coverage is established before any chain replay;
8. every Slice 2 replay completes before cross-chain and target-closure checks; and
9. the three chain postconditions run as three collection-wide passes, in order: every unresolved
   target across every chain, then every target-set mismatch across every chain, then every
   unrelated support Observation across every chain; and
10. Record rebuild happens only after every chain and ancestor/self invariant succeeds.

The three postcondition categories are never interleaved per chain. Each pass examines the complete
canonically ordered replay collection and either selects the canonical first failure in that one
category or completes before the next category begins. A target-set mismatch or unrelated-support
fault in an earlier-sorted chain therefore cannot mask an unresolved target in a later-sorted
chain.

After strict admission, processing and error selection use canonical keys rather than caller tuple
position. Permuting otherwise identical valid inputs cannot change the result, summaries or
coverage digest.

## Evidence Record admission

`EVIDENCE_RECORD_INVALID` means the supplied outer Record failed direct strict instance
revalidation or the public Slice 1 internal verifier. After the aggregate occurrence-byte check,
Slice 3 directly strict-revalidates the complete existing Record tree, including Request,
Instruction and Decision, before invoking the internal verifier. It does not revalidate only a
`model_dump` projection. Hidden outer or nested extras injected through `model_copy` or equivalent
trusted-object mutation fail closed. Slice 3 then strictly replays the complete three-module digest
chain and exact immutable Record before trusting its Request fields.

Slice 3 does not replay the Frozen Pack, Rights Manifest, Use Plan or Use Scope Review filesystem or
object closure. Those upstream objects are not arguments to this API.

## Exact Request target coverage

Let `R` be the complete canonical set of `record.request.observation_refs`, and let `T` be every
declared `request_target_refs` occurrence across all chain inputs.

The verifier requires:

1. no exact Request Observation reference is declared as a target more than once, within one input
   or across inputs;
2. when a target ID exists in `R`, the target must equal that Request reference in all five fields;
3. every target ID must exist in `R`; and
4. every reference in `R` must be targeted exactly once.

The corresponding error order is:

```text
REQUEST_TARGET_COVERED_MULTIPLE_TIMES
REQUEST_TARGET_ANCHOR_MISMATCH
REQUEST_TARGET_NOT_IN_RECORD
REQUEST_OBSERVATION_NOT_COVERED
```

No filename, timestamp, tuple position, terminal shape or favorable claim can create or replace a
target.

## Per-chain replay

For each admitted chain input, Slice 3 calls the public Slice 2 verifier with:

```text
record.subject_closure
chain_input.status_category
chain_input.source_kind
chain_input.source_identity_ref_sha256
chain_input.observations
```

Slice 3 accepts only a verifier-originated Slice 2 result with intact process-local provenance. A
Slice 2 failure is wrapped as `CHAIN_REPLAY_FAILED`; the Slice 3 exception retains the nested Slice
2 error code in optional `replay_code`. It does not flatten, reinterpret, retry or repair the chain.

## Logical-chain identity

Within one Record, a logical-chain key is:

```text
status_category
source_kind
source_identity_ref_sha256
genesis_ref.observation_id
genesis_ref.observation_sha256
genesis_ref.chain_sha256
```

The complete Record subject closure and fixed Slice 1 profile and policy version are common to all
accepted inputs and remain part of the semantic replay scope.

Two inputs with the same logical-chain key are rejected as `DUPLICATE_LOGICAL_CHAIN`. This prevents
one logical chain from being split into multiple inputs. Two inputs with the same category, source
kind and source identity but different exact Genesis references are allowed as separate logical
chains. Slice 3 does not infer a relationship between those roots.

## Cross-chain uniqueness

After every chain replays successfully and logical-chain keys are unique, Slice 3 requires global
independent uniqueness of:

```text
observation_id
observation_sha256
chain_sha256
observation_set_sha256
```

The checks run in the displayed order. An Observation cannot be shared across two chain inputs,
even when it is used as a support ancestor in one input and a Request target in another. A repeated
set digest is also rejected; it is never treated as an alias for a second logical chain.

## Chain target set

For each freshly replayed chain, every declared Request target must resolve to an exact full
reference in that replay result. Absence or anchor drift is
`REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN`.

The verifier then computes the canonical full-field intersection:

```text
freshly_replayed_observation_refs ∩ record.request.observation_refs
```

The chain input's canonically sorted `request_target_refs` must equal that intersection exactly.
Any difference is `CHAIN_TARGET_SET_MISMATCH`. A Request Observation present in one supplied chain
cannot be hidden as an unreported support record or assigned to another logical chain.

This comparison is retained as a defensive consistency guard. Under the current earlier public
invariants it is expected to be unreachable in an ordinary supported call: every Record reference
is declared exactly once; all declared targets have already resolved in their declared chains; and
cross-chain Observation identity, document, chain and set collisions have already failed closed.
An extra Record reference in one replay would therefore already imply either an unresolved target
in another chain or an earlier cross-chain duplicate. The fixed error code remains to detect an
implementation regression or violated internal invariant, and its comparison logic is exercised
through a private pure symbolic helper rather than by weakening an earlier public invariant.

## Exact ancestor-and-self closure

For each declared target, Slice 3 walks only resolved immutable parent edges backward inside the
freshly replayed DAG. It includes:

- the target itself;
- the complete predecessor path of every Successor ancestor; and
- every branch head and every ancestor of every branch head for a Reconciliation ancestor.

The union of all target ancestor-and-self sets must equal the complete supplied Observation set for
that chain:

```text
supplied_observations
== union(ancestors(target) ∪ {target} for every explicit target)
```

Any supplied node outside that union is `UNRELATED_SUPPORT_OBSERVATION`. Examples include an
untargeted sibling, an untargeted descendant of a target or a branch that reaches no explicit
target.

A target may be an ancestor of another target. In that case it remains a Request target rather than
a supporting ancestor. `supporting_ancestor_refs` contains exactly the replayed Observation
references that are not Request targets; every such reference is proven, within the supplied set,
to be an ancestor of at least one target.

This rule does not require one terminal head. A chain may cover multiple Request targets on
different unresolved branches if every supplied branch is necessary for at least one explicit
target.

## Deterministic Record rebuild

After coverage succeeds, Slice 3 resolves the exact Source Observation object for every canonical
Request target reference and orders those target objects through the frozen Slice 1 canonical
Observation order. Supporting ancestors are not passed to the Record builders unless they are also
explicit Request targets.

The verifier then rebuilds:

1. the Request with the original subject closure, preparer identity-reference SHA-256,
   `requested_at`, `request_basis` and exact target Observation objects;
2. the Instruction with the rebuilt Request, the same exact target objects, original checker
   identity-reference SHA-256, `evaluated_at` and `checker_basis`; and
3. the Decision and outer Record through the public Slice 1 Record builder.

The rebuilt Request, Instruction, Decision, their canonical SHA-256 values and the complete outer
Record must equal the strictly verified supplied Record. Any difference is
`RECORD_REBUILD_MISMATCH`.

This rebuild proves deterministic contract consistency with the exact target Observation bytes. It
does not prove that an Observation statement is true, authentic, complete or current.

## Per-chain coverage summary

Each `FreshStatusRecordChainCoverageSummaryV1` contains exactly:

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

The replay-derived fields are copied only from a freshly returned, provenance-checked Slice 2
result. Target and support references are exact, disjoint, canonically sorted subsets of
`observation_refs`, and together they exhaust that set.

Coverage summaries are sorted by this exact key:

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

Every reference tuple inside every summary is canonically sorted by:

```text
(observation_id, observation_sha256, chain_sha256)
```

## Outer process result

`FreshStatusEvidenceRecordChainCoverageResultV1` contains:

```text
result_type
coverage_profile
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
provided_evidence_record_request_explicit_chain_coverage_consistent
provided_evidence_record_rebuild_consistent
limitation_codes
status
all fixed zero-authority fields
```

The fixed literals are:

```text
result_type=FRESH_STATUS_EVIDENCE_RECORD_CHAIN_COVERAGE_RESULT_V1
coverage_profile=creative-sample-real-asset-fresh-status-record-chain-coverage-v1
status=FRESH_STATUS_EVIDENCE_RECORD_CHAIN_COVERAGE_CONSISTENT
provided_evidence_record_request_explicit_chain_coverage_consistent=true
provided_evidence_record_rebuild_consistent=true
```

Slice 2 consistency is not duplicated as a second outer aggregate boolean. It is established by
calling the public Slice 2 verifier for every chain and retained in each summary as
`provided_explicit_finite_chain_closure_consistent=true`.

On success:

```text
request_observation_count
== covered_request_observation_count
== len(request_observation_refs)

chain_count == len(chain_coverages)

provided_observation_count
== sum(summary.observation_count for summary in chain_coverages)

supporting_ancestor_observation_count
== sum(len(summary.supporting_ancestor_refs) for summary in chain_coverages)

provided_observation_count
== covered_request_observation_count
   + supporting_ancestor_observation_count
```

The last equality follows from exact target coverage, cross-chain uniqueness and each chain's exact
target/support partition.

## Coverage-set digest

The exact coverage-set handle is:

```text
coverage_set_sha256 = SHA256(
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
evidence_record_sha256
request_id
request_sha256
complete subject_closure
request_observation_count
complete canonically sorted request_observation_refs
chain_count
covered_request_observation_count
provided_observation_count
supporting_ancestor_observation_count
complete canonically sorted chain_coverages
```

Canonical compact JSON uses UTF-8, `ensure_ascii=false`, sorted object keys and no insignificant
whitespace. The projection excludes `coverage_set_sha256` itself, status, limitation codes and all
zero-authority fields. Those excluded fixed fields are independently bound by the process-local
result provenance described below.

The digest is deterministic and domain-separated. It is not a signature, authorization token or
proof that the named external sources exist or are authentic.

## Process-local provenance

The outer Result is strict, frozen and `extra=forbid`, but it is not a persistent document
contract. The module uses a private context sentinel while constructing it and stores a private
provenance value:

```text
SHA256(
  "sdc:creative-sample-real-asset-fresh-status-record-chain-coverage-provenance:v1\0"
  || canonical_compact_json(every public Result field)
)
```

The provenance binds the coverage digest, summaries, derived counts, limitation codes, status and
every zero-authority field. The public verifier checks it immediately before returning.

Ordinary construction, ordinary `model_validate`, JSON round-trip, `model_construct` and mutated
`model_copy` do not establish or preserve valid verifier provenance. The provenance mechanism is
module-private and is not a public API.

This is an engineering misuse guard only. It is not a signature, security token, cross-process
attestation or protection against deliberate Python reflection or memory manipulation. Dumped
public fields lose provenance and must not be reloaded or treated as a Result, receipt or permit.

The Result has:

- no stable persistent artifact ID;
- no supported canonical bytes parser or extractor;
- no committed or supported JSON Schema;
- no registration in `sdc.schemas.MODELS`; and
- no filesystem finalizer, writer, rollback, quarantine or receipt semantics.

## Error object

Failures raise `RealAssetFreshStatusRecordChainCoverageV30Error`. The exception exposes:

```text
code: FreshStatusRecordChainCoverageErrorCodeV1
replay_code: FreshStatusChainReplayErrorCodeV1 | None
```

`replay_code` is populated only for `CHAIN_REPLAY_FAILED`. No failure returns a partial summary or
partial Result. No failure triggers discovery, repair, retry, mutation, rollback or quarantine.

| Error code | Meaning inside the exact supplied values |
| --- | --- |
| `CHAIN_COLLECTION_CONTRACT_INVALID` | `chains` is not the exact supported tuple shape. |
| `CHAIN_COUNT_OUT_OF_RANGE` | The collection does not contain 1..32 chain inputs. |
| `CHAIN_INPUT_CONTRACT_INVALID` | A chain input or embedded value violates its strict contract. |
| `TARGET_COUNT_OUT_OF_RANGE` | A chain input does not contain 1..32 target occurrences. |
| `OBSERVATION_COUNT_OUT_OF_RANGE` | A chain input does not contain 1..64 Observation occurrences. |
| `AGGREGATE_CANONICAL_BYTES_OUT_OF_RANGE` | Supplied Observation occurrences exceed 16 MiB. |
| `EVIDENCE_RECORD_INVALID` | The complete Record instance tree failed direct strict revalidation or Slice 1 internal replay. |
| `REQUEST_TARGET_COVERED_MULTIPLE_TIMES` | An exact Request Observation reference is targeted more than once. |
| `REQUEST_TARGET_ANCHOR_MISMATCH` | A known Request target differs in one or more full reference fields. |
| `REQUEST_TARGET_NOT_IN_RECORD` | A declared target ID is absent from the Record Request. |
| `REQUEST_OBSERVATION_NOT_COVERED` | A Record Request reference has no explicit target occurrence. |
| `CHAIN_REPLAY_FAILED` | One explicit chain failed Slice 2; inspect optional `replay_code`. |
| `DUPLICATE_LOGICAL_CHAIN` | Two inputs have the same explicit scope and exact Genesis. |
| `CROSS_CHAIN_DUPLICATE_OBSERVATION_ID` | Two chain results share an Observation ID. |
| `CROSS_CHAIN_DUPLICATE_OBSERVATION_DOCUMENT_SHA256` | Two chain results share a document digest. |
| `CROSS_CHAIN_DUPLICATE_OBSERVATION_CHAIN_SHA256` | Two chain results share a chain digest. |
| `CROSS_CHAIN_DUPLICATE_OBSERVATION_SET_SHA256` | Two chain results share a complete set digest. |
| `REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN` | A declared target does not resolve to its exact chain Observation. |
| `CHAIN_TARGET_SET_MISMATCH` | Defensive consistency guard: declared targets differ from the replay/Request full-field intersection; expected unreachable after the current earlier public invariants. |
| `UNRELATED_SUPPORT_OBSERVATION` | A supplied non-target is not an ancestor of any declared target. |
| `RECORD_REBUILD_MISMATCH` | Exact target Observations do not rebuild the supplied Record. |
| `INTERNAL_RESULT_INCONSISTENCY` | A derived summary, digest, count or provenance invariant failed. |

## Exact proof boundary

Success proves only that, for the exact in-memory values supplied in this call:

- the Record passed Slice 1 internal three-module replay;
- every Record Request Observation reference was declared as a target exactly once;
- each target matched all five Request reference fields;
- every explicit chain passed the Slice 2 finite DAG replay;
- no logical chain was split and no Observation or set digest was reused across chain inputs;
- each chain's target declarations equaled its exact replay/Request intersection;
- each chain input contained exactly the union of its targets and their supplied ancestors;
- the exact target Observation objects deterministically rebuilt the Request, Instruction,
  Decision and outer Record; and
- the returned summaries, counts and digest were derived deterministically under this profile.

Success does not prove:

- that every relevant source, event, ancestor, descendant, sibling, fork or logical chain was
  supplied outside the Record's explicit Request targets;
- that the Record's Request selected every real-world fact that ought to have been considered;
- that a source, source identity, locator, statement or Observation is authentic, authorized or
  true;
- that no evidence was hidden, deleted, superseded, backfilled or observed later;
- that a terminal head is latest, current, valid, favorable or legally effective;
- that two same-scope chains with different Genesis records are related or unrelated in reality;
- that SHA-256 is collision-proof as an external factual guarantee;
- that any rights, identity, privacy, policy or legal conclusion is valid outside the declared
  subject closure and explicit finite sets;
- that the Evidence Record remains current after any explicit half-open validity window;
- that the process-local provenance is an unforgeable attestation; or
- that any Provider, generation, execution, publication, purchase, contact, upload, retention or
  training action is allowed.

Record rebuild is deterministic consistency replay, not a new assessment and not an approval.

## Zero-authority invariant

Every successful Result fixes:

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

It also retains all seven Slice 1 limitation codes in canonical policy order:

```text
SOURCE_AUTHENTICITY_NOT_PROVEN
SOURCE_COMPLETENESS_NOT_PROVEN
CHAIN_COMPLETENESS_NOT_PROVEN
REALITY_CURRENTNESS_NOT_PROVEN
SCOPE_LIMITED_TO_DECLARED_SUBJECT
TIME_WINDOW_LIMITED
LEGAL_EFFECT_NOT_DETERMINED
```

The two positive scoped-consistency booleans do not override any limitation or zero-authority
field.

## Synthetic verification matrix

Tests must use only programmatically generated synthetic in-memory models and cover:

- exact tuple enforcement for `chains`, nested targets and Observation collections;
- direct strict instance revalidation of every chain input and embedded value, including hidden
  outer-input and nested-Observation extras injected with `model_copy`;
- chain-input counts 0, 1, 32 and 33;
- per-chain target counts 0, 1, 32 and 33;
- per-chain Observation counts 0, 1, 64 and 65;
- aggregate canonical occurrence-byte totals at limit minus one, exactly 16,777,216 and limit plus
  one, with budget failure preceding Record or semantic failures;
- strict invalid Evidence Record rejection after input and budget admission, including hidden
  extras independently injected into the outer Record, Request, Instruction and Decision;
- target duplication within one input and across inputs;
- each of the five target-reference fields drifting independently;
- target ID absent from the Record and one Record Request target omitted;
- nested Slice 2 orphan, anchor, cycle, Genesis, reachability, disconnected-graph and antichain
  failures with exact `replay_code` preservation;
- one logical chain split across two inputs;
- same scope with different exact Genesis references accepted as distinct logical chains;
- independent cross-chain duplicate ID, document SHA, chain SHA and Observation-set SHA guards;
- target absent from its declared replay chain;
- the private pure target-set comparison helper returning `CHAIN_TARGET_SET_MISMATCH` for a
  symbolic inconsistent intersection, while the supported public path documents that guard as
  normally unreachable after earlier invariants;
- Genesis, Successor and Reconciliation targets with complete ancestor-and-self unions;
- multiple targets where one target is an ancestor of another;
- untargeted sibling, descendant and unrelated support Observation rejection;
- exact supporting-ancestor summaries and target/support exhaustion;
- a strictly valid internal Record whose Instruction does not deterministically rebuild from the
  exact target Observation documents, without monkeypatching a production builder;
- permutations of chain inputs, targets and Observation tuples producing one identical Result and
  coverage digest;
- digest sensitivity to Record, Request target, support ancestor, chain scope and chain-summary
  changes;
- direct construction, ordinary validation, JSON reload, `model_construct` and mutated
  `model_copy` failing the provenance boundary;
- frozen zero-authority and limitation fields;
- no production path, filesystem, process, network, Provider, clock or execution surface; and
- the unchanged 67-entry Schema registry with exactly five existing Fresh Status top-level
  Schemas and byte-identical pre-Slice-3 Schema files.

Use honest strictly validated public fixtures whenever the contract can represent the fault.
Cycle and disconnected-graph states that cannot be honestly constructed after Slice 1 model
invariants are exercised at the Slice 2 private pure graph kernel or symbolic helper boundary;
Slice 3 separately verifies exact preservation of reachable nested `replay_code` values. Likewise,
cryptographic ID/document/chain/set collision dimensions that cannot be honestly produced without
a SHA-256 collision use private pure symbolic collision helpers. These helper tests do not
monkeypatch production hash functions, relax a public model, or claim that the corresponding
symbolic state is reachable through the normal public API.

Focused tests, Ruff, strict Mypy and the complete offline `make check` must pass. Any full check must
run in a fresh LF-preserving isolated worktree that excludes the repository's current `output/` and
`tmp/` directories.

## Implementation boundary

The separately approved synthetic implementation is limited to:

```text
docs/adr/SDC-ADR-033.md
docs/runbooks/SDC-CREATIVE-SAMPLE-REAL-ASSET-FRESH-STATUS-RECORD-CHAIN-COVERAGE-V30.md
src/sdc/real_asset_fresh_status_record_chain_coverage_v30.py
tests/test_real_asset_fresh_status_record_chain_coverage_v30.py
```

This document-creation action creates only the first two files. It does not itself authorize source
or test implementation, Schema generation, a commit, push, PR, merge or any real-data operation.

## Alternatives rejected

### Infer targets from terminal heads

Rejected because terminal means only no child in the supplied tuple. It is not equivalent to a
Record Request target, latest state or current evidence.

### Automatically partition one Observation pool

Rejected because it would turn explicit validation into discovery and could hide a caller's chain
scope or Genesis mistake.

### Allow one logical chain in multiple inputs

Rejected because split inputs could hide siblings or distort target/support accounting. All targets
and supplied ancestors for one exact scope and Genesis belong in one input.

### Require one terminal per covered chain

Rejected because one Record may explicitly target multiple unresolved branches. Ancestor/self
coverage, not favorable convergence, is the Slice 3 invariant.

### Deduplicate before the 16 MiB budget

Rejected because repeated occurrences consume validation resources and must not bypass the bound.

### Reuse Slice 2 detached result dumps

Rejected because dumps lose process-local provenance. Slice 3 performs fresh replay calls from the
exact Source Observation models.

### Add a persistent receipt or Schema

Rejected for Slice 3. A detached summary cannot independently replay the Record and exact Source
Observation documents that its hashes name and could be mistaken for authorization.

## Versioning rule

Any semantic change to the profile, public field names, count or byte bounds, occurrence accounting,
fixed error order, target-intersection rule, logical-chain key, ancestor/self rule, Record rebuild,
summary sort key, coverage digest projection/domain or provenance semantics requires a new coverage
profile and Result version. A changed digest projection also requires a new domain separator.

No future implementation may silently reinterpret an earlier process Result or golden digest.

## Consequences and deferred work

The positive consequence is a bounded, deterministic answer to whether one exact Evidence Record's
Request targets are fully assigned to freshly replayed explicit chains and backed by exact supplied
ancestor/self closures.

The cost is deliberate verbosity: callers must declare every target, logical scope and supporting
ancestor explicitly, and overlapping logical-chain inputs fail rather than being merged.

The following remain separately deferred:

- trusted-local filesystem loading or a path profile;
- a CLI, finalizer, create-new writer, rollback, quarantine or receipt;
- a persistent coverage artifact or JSON Schema;
- external chain, source or hidden-branch discovery;
- source authenticity, identity authority or current-status assessment;
- automated Reconciliation or target selection;
- real evidence, identity, rights, complaint, dispute, hold, revocation or policy material; and
- Provider proposal, selection, contact, Key use, upload, purchase, generation, execution,
  publication, retention or training.

Acceptance, implementation, test success, commit, review or merge of this ADR authorizes none of
those deferred actions. Each requires a separate explicit design and approval.
