# SDC-ADR-031: Immutable fresh status evidence contracts v3.0

- **Status:** Accepted
- **Date:** 2026-08-23
- **ADR release:** 1.0
- **Contract boundary version:** 3.0.0
- **Contract Schema version:** 1.0.0
- **Implementation slice:** Slice 1 — pure contracts, builders, parsers and synthetic tests only
- **Upstream closure:** Frozen Pack, Rights Manifest v2, Use Plan v1 and Use Scope Review Record v1

## Context

The Frozen Pack, Rights Manifest, Use Plan and Use Scope Review Record form a deterministic
historical closure. That closure proves that the exact submitted bytes agree with the contracts
and policy versions under which they were created. It deliberately does not prove that a right,
identity, policy position, complaint, dispute, hold or revocation remains unchanged at a later
time.

The next boundary therefore needs an immutable way to record fresh, explicitly bounded status
evidence without turning historical verification into an authorization mechanism. A successful
Use Scope Review, including `PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY`, is not sufficient evidence
of current status and cannot be promoted into Provider, generation, publication or execution
authority.

This ADR defines the v3.0 contract vocabulary and the first implementation slice. Slice 1 is a
pure Python/Pydantic layer. It has no filesystem, path, CLI, network, Provider, database, queue,
worker, implicit-clock or real-data boundary. Later trusted-local finalization and current-status
assessment remain separately designed and separately approved work.

This ADR records the reviewed Slice 1 contract boundary. It is not an operational approval, a
real-evidence instruction, a commit approval or authority for any later action.

## Decision

Add one pure module:

```text
sdc.real_asset_fresh_status_evidence_v30
```

The module defines five top-level immutable contract artifacts:

```text
CreativeSampleRealAssetFreshStatusSourceObservationV1
CreativeSampleRealAssetFreshStatusRequestV1
CreativeSampleRealAssetFreshStatusInstructionV1
CreativeSampleRealAssetFreshStatusDecisionV1
CreativeSampleRealAssetFreshStatusEvidenceRecordV1
```

The first four are independently addressable documents. The outer Evidence Record physically
contains Request, Instruction and Decision as three separate modules and binds the exact canonical
document SHA-256 of each. Source Observations remain separately addressable documents; the Request
binds an explicit, finite, ordered set of their IDs and full canonical-document SHA-256 values.

Nested claim, observation-reference, assessment and chain-link models may appear in generated
`$defs`, but they are not standalone persisted artifacts and are not registered as additional
top-level committed Schemas.

## Zero-authority invariant

Every top-level v3.0 artifact contains the following immutable scope constant and fourteen
zero-authority fields:

```text
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
execution_authorized=false
generation_authorized=false
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
```

Every top-level artifact also carries the fixed manual-use restriction:

```text
usage_restriction=MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION
```

These are contract literals, not caller defaults. A caller cannot replace them with truthy,
non-zero or alternate string values. No positive status result changes them.

The following names and claims are forbidden in v3.0 outputs:

```text
AUTHORIZED
APPROVED_FOR_EXECUTION
READY_TO_RUN
PROVIDER_READY
CURRENT_GLOBAL_TRUTH
COMPLETE_STATUS_HISTORY
NO_UNDISCLOSED_EVIDENCE
```

No record, digest, stable ID, chain handle, status window or disposition is an entitlement,
permit, token, receipt, capability or executable parameter set.

## Version and policy binding

All five top-level documents bind these constants:

```text
schema_version=1.0.0
profile=creative-sample-real-asset-fresh-status-evidence-v3.0
policy_id=creative-sample-real-asset-fresh-status-evidence-policy
policy_version=3.0.0
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
```

The policy document SHA-256 is compiled into the module and checked against one domain-separated,
canonical policy payload at import time. Changing a predicate, state, disposition, order, source
kind, limitation code, transition rule, time formula, size limit, quantity limit, canonical-byte
rule or zero-authority constant requires a new policy version. A later implementation must not
silently accept or adapt a different version.

## Roles and separation

V3.0 has three fixed roles:

```text
STATUS_PREPARER
STATUS_CHECKER
COMPILER
```

The `STATUS_PREPARER` creates Source Observations and a Request from explicitly supplied values.
The `STATUS_CHECKER` supplies only its identity-reference digest, explicit `evaluated_at` and
bounded `checker_basis`, then reviews the deterministically derived seven-category result. The
Instruction builder must consume the Request's exact Observation set; neither role may select a
favorable subset, state, effect or evidence reference. The compiler deterministically derives the
Decision and outer Record; it does not add an external fact or human judgment.

`STATUS_PREPARER` and `STATUS_CHECKER` identity references are lowercase full SHA-256 values and
must differ. They
bind exact identity-reference bytes only. They do not authenticate a natural person, prove role
authority or prove that two references correspond to two different people. Human governance
remains responsible for actual role separation.

Role fields are contract literals. A `STATUS_PREPARER` document cannot carry `STATUS_CHECKER`
fields; an Instruction cannot claim compiler authorship; a caller cannot directly submit a
Decision.

## Subject closure

Every Source Observation and each Request, Instruction and Decision independently repeats one
exact subject closure:

```text
pack_id + pack_manifest_sha256
rights_manifest_id + rights_manifest_sha256
use_plan_id + use_plan_sha256
use_scope_review_record_id + use_scope_review_record_sha256
closure_profile + closure_profile_document_sha256
closure_id
```

Every ID is paired with a lowercase 64-hex SHA-256. `closure_id` is derived from the
ordered identity projection of all preceding pairs and the closure profile. It is a stable handle,
not a substitute for any full digest.

`build_fresh_status_subject_closure_v1` receives the already constructed Frozen Pack, Rights
Manifest, Use Plan and Use Scope Review Record candidates. It strictly revalidates those four
objects, checks their direct ID/SHA relationships and calculates their exact canonical-document
digests. This is candidate-closure construction, not a claim that every earlier upstream object
was replayed.

`verify_fresh_status_evidence_record_closure_v1` is the separate full in-memory closure verifier.
It receives the complete explicit upstream model set, invokes the existing pure Use Scope Review
closure verifier, rebuilds the v3.0 candidate closure and then rebuilds the exact Request,
Instruction, Decision and Record. Neither function opens a file. Trusted-local filesystem closure
replay remains deferred.

## Document topology and independent summaries

The Evidence Record has exactly this logical shape:

```text
FreshStatusEvidenceRecord
├── request
├── request_sha256
├── instruction
├── instruction_sha256
├── decision
└── decision_sha256
```

Request, Instruction and Decision are physically separate object members. They have separate
stable IDs, separate canonical-document bytes and separate SHA-256 values. Fields may be repeated
where independent extraction requires them, but fields from different roles must never be mixed
into one module.

The Record validates all of the following:

- the three stored digests match the exact embedded module bytes;
- Instruction binds the exact Request ID and digest;
- Decision binds the exact Request and Instruction IDs and digests;
- all three modules bind the same subject closure and observation set;
- `STATUS_PREPARER` and `STATUS_CHECKER` references remain distinct; and
- the Record ID binds every embedded module and digest, excluding only its own ID field.

The Record does not store its own SHA-256. External consumers calculate the full canonical
document SHA-256 after serialization. This avoids self-reference.

## Fixed predicates

Every Instruction and Decision contains exactly seven predicate assessments in this order:

```text
HOLD_ACTIVE
REVOCATION_EFFECTIVE
COMPLAINT_OPEN
DISPUTE_OPEN
RIGHTS_BASIS_CURRENT
IDENTITY_BINDING_CURRENT
POLICY_COMPATIBILITY_CURRENT
```

The first four are adverse predicates. The last three are positive predicates. No caller may
insert, remove, duplicate, rename or reorder a predicate.

## Fixed epistemic states

Each predicate uses exactly one of these five states:

```text
PRESENT
ABSENT_WITH_EVIDENCE
UNKNOWN
NOT_ASSESSED
CONFLICT
```

Absence of a Source Observation never means absence of the real-world condition. It maps only to
`UNKNOWN` or `NOT_ASSESSED`. `ABSENT_WITH_EVIDENCE` requires one or more explicit, relied-on Source
Observations that are usable at the explicit evaluation boundary.

For adverse predicates:

| State | Deterministic effect |
| --- | --- |
| `PRESENT` | `BLOCKING` |
| `ABSENT_WITH_EVIDENCE` | `NON_BLOCKING_WITHIN_BOUND_WINDOW` |
| `UNKNOWN`, `NOT_ASSESSED`, `CONFLICT` | `INDETERMINATE` |

For positive predicates:

| State | Deterministic effect |
| --- | --- |
| `PRESENT` | `NON_BLOCKING_WITHIN_BOUND_WINDOW` |
| `ABSENT_WITH_EVIDENCE` | `BLOCKING` |
| `UNKNOWN`, `NOT_ASSESSED`, `CONFLICT` | `INDETERMINATE` |

The effect is compiler-derived. A `STATUS_PREPARER` or `STATUS_CHECKER` cannot submit it.

### Deterministic Observation-set reduction

The Request binds one exact, sorted set of 1..32 Source Observations. The Instruction builder must
receive that same set byte-for-byte and must account for every Request reference exactly once
across the seven fixed categories. It does not accept a caller-supplied category state, effect,
disposition or selected reference list.

For each `status_category`, the builder considers every Request Observation in that category. An
Observation is relied on only when its claim is not `NOT_ASSESSED` and its explicit half-open
window contains `evaluated_at`. Reduction is fixed:

- no usable Observation produces `NOT_ASSESSED`;
- one distinct usable claim with no explicit fork produces that claim;
- more than one distinct usable claim produces `CONFLICT`; and
- two or more usable `SUCCESSOR` Observations that bind the same predecessor observation ID form
  an explicit fork and produce `CONFLICT`, even when their claim strings match.

Every category result retains all category Observation references separately from the relied-on
subset. The `STATUS_CHECKER` reviews these deterministic results and contributes only its exact
identity-reference digest, `evaluated_at` and bounded `checker_basis`.

## Fixed dispositions

The Decision uses exactly one of these three dispositions:

```text
BLOCKING_STATUS_RECORDED
INSUFFICIENT_OR_CONFLICTING_EVIDENCE
NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET
```

Derivation order is fixed:

1. If any predicate effect is `BLOCKING`, use `BLOCKING_STATUS_RECORDED`.
2. Otherwise, if any effect is `INDETERMINATE`, use
   `INSUFFICIENT_OR_CONFLICTING_EVIDENCE`.
3. Otherwise use `NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET`.

The third disposition is deliberately scoped to the explicitly supplied, finite source set and
explicit time windows. It does not mean clear, approved, safe, complete, current outside that
window or authorized for a later operation.

## Fixed source kinds

Every Source Observation selects `source_kind` from exactly this closed set:

```text
RIGHTS_HOLDER_DECLARATION
LICENSOR_DECLARATION
INTERNAL_HOLD_RECORD
REVOCATION_NOTICE
COMPLAINT_RECORD
DISPUTE_RECORD
IDENTITY_BINDING_RECORD
POLICY_EVALUATION_RECORD
```

There is no predicate-to-source-kind one-to-one mapping. A source object may support one or more
predicates only through separate, explicit Source Observation documents that bind the same source
object digest and size. The tool never infers a predicate from `source_kind`. Membership in this
closed set does not prove source authenticity, author identity, statement truth, completeness,
currentness, legal effect or authority.

The contract stores only source metadata, full digest, byte count and an optional locator-reference
digest. It never stores a path, URL, credential, Key, account ID or source bytes.

## Fixed limitation codes

`limitation_codes` is a unique tuple in this exact policy order:

```text
SOURCE_AUTHENTICITY_NOT_PROVEN
SOURCE_COMPLETENESS_NOT_PROVEN
CHAIN_COMPLETENESS_NOT_PROVEN
REALITY_CURRENTNESS_NOT_PROVEN
SCOPE_LIMITED_TO_DECLARED_SUBJECT
TIME_WINDOW_LIMITED
LEGAL_EFFECT_NOT_DETERMINED
```

The first four codes are mandatory on every Source Observation. The remaining codes are added only
when applicable. Codes cannot be duplicated, reordered, omitted when mandatory or replaced with
free text. `basis_note` is a separate bounded human statement and cannot cancel a limitation.

## Source Observation fields

A Source Observation binds at least:

```text
observation_id
subject closure fields
status_category
claim_value
source_kind
source_identity_ref_sha256
source_object_sha256
source_object_size_bytes
source_media_type
source_locator_ref_sha256 (optional)
source_event_at
observed_at
valid_from
valid_until
basis_code
basis_note
limitation_codes
chain_link
```

`status_category` is the field name for one member of the fixed seven-predicate vocabulary. It is
not an extensible taxonomy and does not permit a caller-defined category.

Each `FreshStatusObservationRefV1` contains exactly the binding information needed by the Request
and deterministic category results:

```text
observation_id
observation_sha256
status_category
source_identity_ref_sha256
chain_sha256
```

The document SHA-256 and domain-separated chain SHA-256 are distinct. Reference sets reject a
duplicate ID, duplicate full document digest or non-canonical order.

`observation_id` is a stable ID over all other canonical identity fields. Source object size is an
exact positive integer binding, not proof that Slice 1 opened or measured a file.

The policy fixes predicate-specific onset and reversal basis codes:

| Predicate | Present/current basis | Absent/not-current basis |
| --- | --- | --- |
| Hold | `HOLD_IMPOSED` | `HOLD_RELEASED` |
| Revocation | `REVOCATION_ISSUED` | `RIGHTS_REINSTATED` |
| Complaint | `COMPLAINT_RECEIVED` | `COMPLAINT_RESOLVED` |
| Dispute | `DISPUTE_OPENED` | `DISPUTE_RESOLVED` |
| Rights | `RIGHTS_GRANTED_OR_RENEWED` | `RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED` |
| Identity | `IDENTITY_VERIFIED_OR_REBOUND` | `IDENTITY_EXPIRED_REVOKED_OR_SUPERSEDED` |
| Policy | `POLICY_REVIEWED_COMPATIBLE` | `POLICY_CHANGED_OR_INCOMPATIBLE` |

The closed basis-code set contains the fourteen predicate-specific codes above plus exactly:

```text
INITIAL_STATUS_UNKNOWN
INITIAL_STATUS_NOT_ASSESSED
STATUS_RECONFIRMED
STATUS_BECAME_UNKNOWN
CONFLICT_IDENTIFIED
CONFLICT_RECONCILED
```

These six common or initial codes are allowed only for the matching transition shapes below. Late
evidence remains represented by explicit `source_event_at` and `observed_at` values and never
reorders history. A state cannot flip merely because a later document claims a favorable value.

## State transition rules

All changes create a new immutable Source Observation. No contract is updated in place.

### Genesis matching

| New claim | Required basis |
| --- | --- |
| `PRESENT` | The category's present/current predicate-specific code |
| `ABSENT_WITH_EVIDENCE` | The category's absent/not-current predicate-specific code |
| `UNKNOWN` | `INITIAL_STATUS_UNKNOWN` |
| `NOT_ASSESSED` | `INITIAL_STATUS_NOT_ASSESSED` |
| `CONFLICT` | `CONFLICT_IDENTIFIED` |

### Successor matching

| Previous claim → new claim | Required basis |
| --- | --- |
| `NOT_ASSESSED → UNKNOWN` | `INITIAL_STATUS_UNKNOWN` |
| `NOT_ASSESSED/UNKNOWN → PRESENT` | The category's present/current code |
| `NOT_ASSESSED/UNKNOWN → ABSENT_WITH_EVIDENCE` | The category's absent/not-current code |
| `PRESENT → PRESENT` | `STATUS_RECONFIRMED` |
| `ABSENT_WITH_EVIDENCE → ABSENT_WITH_EVIDENCE` | `STATUS_RECONFIRMED` |
| `PRESENT → ABSENT_WITH_EVIDENCE` | The category's absent/not-current code |
| `ABSENT_WITH_EVIDENCE → PRESENT` | The category's present/current code |
| `PRESENT/ABSENT_WITH_EVIDENCE → UNKNOWN` | `STATUS_BECAME_UNKNOWN` |
| `NOT_ASSESSED/UNKNOWN/PRESENT/ABSENT_WITH_EVIDENCE → CONFLICT` | `CONFLICT_IDENTIFIED` |

`UNKNOWN → UNKNOWN`, every Successor to `NOT_ASSESSED`, and every single-predecessor Successor from
`CONFLICT` are rejected.

### Reconciliation matching

A Reconciliation binds 2..8 explicit, sorted, unique same-chain heads. A result of `PRESENT`,
`ABSENT_WITH_EVIDENCE` or `UNKNOWN` requires `CONFLICT_RECONCILED`. A result that remains
`CONFLICT` requires `CONFLICT_IDENTIFIED`. A Reconciliation to `NOT_ASSESSED` is rejected. This
multi-head shape records only the supplied heads; it cannot prove that every historical branch was
provided.

The builder validates matching basis and immediate link structure using the explicitly supplied
predecessor or heads. The dedicated link verifier replays only that immediate link. Neither API
walks an earlier chain, detects every hidden fork or emits a complete-chain claim. Complete
historical chain replay remains deferred.

## Evidence chain and proof boundary

Each chain is scoped by this exact tuple:

```text
closure_id
status_category
source_identity_ref_sha256
source_kind
profile
policy_version
```

Here `status_category` is exactly the fixed predicate member used by the contract.

`chain_link.kind` is one of:

```text
GENESIS
SUCCESSOR
RECONCILIATION
```

A Successor binds one predecessor observation ID, its full canonical-document SHA-256 and its
derived chain SHA-256. A Reconciliation binds between two and eight unique branch heads, sorted by
ID and full digest. A Genesis contains no predecessor or branch head.

Two observations referencing the same predecessor form a fork. Neither timestamp, sequence,
filename nor favorable state selects a winner. Reconciliation requires a new immutable record and
cannot rewrite either branch.

The chain may only support this claim:

```text
provided_explicit_finite_chain_closure_consistent=true
```

Even that claim is reserved for the deferred complete chain verifier. Slice 1 does not emit it.

A chain, ID or digest does not prove:

- that a source is authentic or its author is authorized;
- that a source statement is true;
- that the provided set contains every relevant source or branch;
- that no evidence was hidden, deleted, backfilled or observed late;
- that the external state remains current after `valid_until`;
- that policy, identity or rights are valid outside the explicit closure; or
- that any Provider, generation, execution or publication action is permitted.

Multiple source identities remain separate chains. V3.0 has no global truth chain, implicit
`latest`, automatic branch winner or automated reconciliation.

## Explicit time model

Every time is caller-supplied canonical UTC seconds:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Offsets, fractional seconds, local time, filesystem timestamps, environment time, network time,
`datetime.now`, `datetime.utcnow`, `time.time` and `PERPETUAL` are forbidden.

Every Source Observation uses a half-open interval:

```text
[valid_from, valid_until)
valid_from < valid_until
valid_until <= valid_from + 86,400 seconds
source_event_at <= observed_at
usable_from = max(observed_at, valid_from)
```

The Request window is also half-open and fixed to 86,400 seconds:

```text
request_valid_until = requested_at + 86,400 seconds
requested_at <= evaluated_at < request_valid_until
```

Every observation relied on by an Instruction must satisfy:

```text
usable_from <= evaluated_at < valid_until
```

The compiler fixes:

```text
decision_at = evaluated_at
status_valid_until = min(request_valid_until, every relied-on valid_until)
```

When there is no relied-on Observation in any category,
`status_valid_until=evaluated_at`. Otherwise the minimum includes `request_valid_until` and every
relied-on category result's `valid_until`.

At `valid_until`, evidence is expired. Expiry yields `EXPIRED_NOT_CURRENT` only in the deferred
explicit-time assessor. It never flips `PRESENT` to `ABSENT_WITH_EVIDENCE` and never restores a
favorable historical state.

## Canonical bytes and stable identities

All v3.0 artifacts use:

```text
UTF-8
no BOM
Unicode NFC
sorted object keys
two-space indentation
ensure_ascii=false
one LF after the final closing brace
no CRLF
```

Parsers reject malformed UTF-8, duplicate keys at any depth, non-finite JSON numbers, unknown or
missing fields, type coercion, a top-level non-object, excess nesting and any raw bytes that differ
from the canonical document. Arrays with set semantics use the fixed policy order and reject
duplicates.

JSON depth counts the top-level object as depth 1. Entering any nested object or array increments
depth by one; scalar members do not add depth. A computed depth greater than 32 fails closed.

Stable IDs use domain-separated identity projections and exclude only the ID being calculated.
Module SHA-256 values use the full canonical document including the stable ID. A 20-hex stable-ID
suffix is only a human-scale handle; every binding and comparison also carries the full 64-hex
SHA-256.

## Fixed resource limits

The v3.0 policy fixes these inclusive limits:

| Resource | Limit |
| --- | ---: |
| Future role authoring input | 65,536 bytes |
| One Source Observation document | 262,144 bytes |
| One Request, Instruction or Decision document | 2,097,152 bytes |
| One outer Evidence Record document | 2,097,152 bytes |
| Source Observations in one Request | 32 |
| Predicate assessments | exactly 7 |
| Records in one future explicit chain replay | 64 (constant frozen; replay deferred) |
| Reconciliation branch heads | 8 |
| `basis_note` | 1,000 Unicode code points |
| JSON nesting depth | 32 |

An empty document, zero observations, oversize document, thirty-third observation, ninth branch
head, 1,001st code point or thirty-third JSON nesting level fails closed. The implementation never
truncates, drops, samples or partially validates an input.

The 65,536-byte value is frozen only for a future role-authoring input contract; Slice 1 defines no
such parser. Slice 1 Request, Instruction, Decision and outer Record builders/parsers use the
2,097,152-byte document limit. Source Observation uses its separate 262,144-byte limit.

## Slice 1 public API and `__all__`

The module's ordered `__all__` is the public boundary. It exports, in order:

```text
FRESH_STATUS_EVIDENCE_V1_PROFILE
FRESH_STATUS_EVIDENCE_V1_POLICY_ID
FRESH_STATUS_EVIDENCE_V1_POLICY_VERSION
FRESH_STATUS_EVIDENCE_V1_POLICY_DOCUMENT_SHA256
FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE
FRESH_STATUS_SUBJECT_CLOSURE_V1_PROFILE_DOCUMENT_SHA256
FRESH_STATUS_MAX_WINDOW_SECONDS
FRESH_STATUS_MAX_OBSERVATIONS
FRESH_STATUS_MAX_CHAIN_RECORDS
FRESH_STATUS_MAX_RECONCILIATION_HEADS
FRESH_STATUS_MAX_BASIS_NOTE_CODEPOINTS
FRESH_STATUS_AUTHORING_INPUT_MAX_BYTES
FRESH_STATUS_SOURCE_OBSERVATION_MAX_BYTES
FRESH_STATUS_RECORD_MAX_BYTES
FRESH_STATUS_JSON_MAX_DEPTH
FRESH_STATUS_EVIDENCE_SCOPE
FreshStatusCategoryV1
FreshStatusClaimValueV1
FreshStatusAssessmentEffectV1
FreshStatusDispositionV1
FreshStatusChainLinkKindV1
FreshStatusBasisCodeV1
FreshStatusSourceKindV1
FreshStatusLimitationCodeV1
FreshStatusSubjectClosureV1
FreshStatusObservationRefV1
FreshStatusChainHeadRefV1
FreshStatusChainLinkV1
FreshStatusCategoryResultV1
CreativeSampleRealAssetFreshStatusSourceObservationV1
CreativeSampleRealAssetFreshStatusRequestV1
CreativeSampleRealAssetFreshStatusInstructionV1
CreativeSampleRealAssetFreshStatusDecisionV1
CreativeSampleRealAssetFreshStatusEvidenceRecordV1
RealAssetFreshStatusEvidenceV30Error
build_fresh_status_subject_closure_v1
derive_fresh_status_observation_chain_sha256_v1
build_fresh_status_source_observation_v1
verify_fresh_status_source_observation_internal_v1
verify_fresh_status_source_observation_link_v1
build_fresh_status_request_v1
build_fresh_status_instruction_v1
compile_fresh_status_decision_v1
build_fresh_status_evidence_record_v1
verify_fresh_status_evidence_record_internal_v1
verify_fresh_status_evidence_record_closure_v1
extract_fresh_status_request_v1
extract_fresh_status_instruction_v1
extract_fresh_status_decision_v1
parse_fresh_status_source_observation_v1_json
parse_fresh_status_request_v1_json
parse_fresh_status_instruction_v1_json
parse_fresh_status_decision_v1_json
parse_fresh_status_evidence_record_v1_json
```

Builders accept only explicit in-memory values and existing immutable upstream model instances.
Parsers accept bounded `bytes`, never a path or stream. Extractors return one separately verified
embedded module and its canonical bytes. The internal verifier revalidates only the embedded
module chain and exact digests. The full closure verifier consumes an explicit in-memory upstream
set. The immediate link verifier validates only its explicitly supplied predecessor or heads.
None verifies a current external status or a complete historical chain.

Only the five top-level artifact models are registered in `sdc.schemas.MODELS`; nested value
types remain `$defs`. There is no package-root re-export requirement.

## Slice 1 committed Schemas

Slice 1 appends exactly five committed JSON Schemas:

```text
CreativeSampleRealAssetFreshStatusSourceObservationV1.schema.json
CreativeSampleRealAssetFreshStatusRequestV1.schema.json
CreativeSampleRealAssetFreshStatusInstructionV1.schema.json
CreativeSampleRealAssetFreshStatusDecisionV1.schema.json
CreativeSampleRealAssetFreshStatusEvidenceRecordV1.schema.json
```

The `MODELS` list grows from 62 to 67. Existing entries remain in their exact order, and all 62
existing committed Schema blobs remain normalized-LF byte-identical. Running schema generation
before all five new models are registered is prohibited because the generator removes unregistered
Schema files.

## Slice 1 failure semantics

Slice 1 has no persistent side effect. Any validation, canonicalization, closure, transition,
time, role, resource or digest failure raises the dedicated v3.0 error and returns no artifact.
There is nothing to roll back or quarantine.

Domain conflict is not a filesystem failure. A valid `CONFLICT` observation or
`INSUFFICIENT_OR_CONFLICTING_EVIDENCE` Decision is a successful zero-authority historical result.
It must not be silently repaired, upgraded or converted into a positive disposition.

## Synthetic validation boundary

Slice 1 tests use generated temporary synthetic objects only and cover:

- deterministic construction and exact canonical golden bytes for all five artifacts;
- stable IDs, full SHA-256 bindings and independent module extraction;
- all seven predicates, five states and three disposition outcomes;
- adverse/positive state mapping and disposition precedence;
- all legal and illegal transition shapes;
- closed-set source-kind admission without predicate inference, and limitation-code order;
- observation-set ordering, uniqueness and 1/32/33 boundaries;
- half-open time boundaries and the 86,400-second cap;
- Genesis, Successor, Reconciliation, fork, duplicate, self-link and cycle-shaped inputs;
- `STATUS_PREPARER`/`STATUS_CHECKER`/compiler role separation;
- canonical UTF-8, BOM, duplicate-key, non-finite-number, NFC and depth rejection;
- `limit-1`, `limit`, `limit+1` resource boundaries;
- forced zero-authority constants and prohibited authority claims;
- no filesystem, implicit clock, network, Provider or runtime imports/calls;
- preservation of all 62 prior committed Schema bytes; and
- full offline `make check` in a fresh LF-preserving isolated worktree.

Golden tests bind reviewed synthetic canonical bytes and exact SHA-256 values. Rebuilding an
equivalent Python value is not sufficient if its document bytes differ.

## Explicitly deferred work

Slice 1 does not implement or authorize:

- a CLI or command-line parser;
- path admission, path normalization, directory inspection or checklist generation;
- file, descriptor, HANDLE, ACL, owner-only or create-new behavior;
- trusted-local inspect, preflight, finalization or historical file verification;
- rollback, quarantine, isolation, repair or delivery-uncertainty handling;
- complete source-chain or complete upstream filesystem closure replay;
- an explicit-time current-status assessor;
- source-object capture or authenticity validation;
- `STATUS_PREPARER`/`STATUS_CHECKER` authoring preparers;
- automatic discovery, glob, scan, `latest`, `current` or `newest` selection;
- real identity, rights, hold, revocation, complaint, dispute or policy evidence;
- Provider proposal design, Provider selection, Key access, upload, POST, purchase, generation,
  execution, publication, retention or training; or
- entitlement, permit, authorization, database, queue, Worker, Runtime, ledger or migration state.

Each deferred layer requires a separate detailed design, synthetic implementation approval,
validation, commit and operational approval. Completion of Slice 1 does not imply approval of
Slice 2.

## Consequences

### Positive

- Currentness is no longer inferred from a historically valid Review Record.
- Human Request, `STATUS_CHECKER` Instruction and compiler Decision remain physically and cryptographically
  separable inside one outer artifact.
- The fixed vocabulary makes favorable, unknown, conflicting and blocking states unambiguous.
- Explicit finite source sets and windows bound every claim.
- Pure contracts can be tested deterministically without touching private data or the filesystem.

### Costs

- Five new top-level Schemas and substantial cross-field validation are required.
- A useful operational workflow still needs later trusted-local I/O, chain and assessment slices.
- Human operators must continue to identify missing sources, hidden branches and real-world
  changes that no deterministic contract can discover.

### Residual risk

A perfectly valid v3.0 Record can still contain a false, incomplete, forged, stale or selectively
provided source statement. Canonical bytes and hash chains make the supplied bytes traceable; they
do not make those bytes true. The fixed limitation codes and zero-authority fields preserve that
distinction but cannot replace human or legal review.

## Non-authorization statement

Acceptance, implementation, test success, commit, PR review or eventual merge of this ADR cannot
authorize a real-data read, real status conclusion, Provider proposal, Provider call, generation,
execution, purchase, upload, publication, retention, training or branch deletion. Every such step
requires its own explicit authority and remains outside Slice 1.
