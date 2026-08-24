# SDC Creative Sample Real-Asset Fresh Status Record Joint Replay v3.0

## Purpose

This runbook describes the synthetic-only, pure in-memory Slice 4 verifier that jointly replays:

1. the exact Fresh Status Evidence Record Request against explicitly supplied finite logical source
   chains through Slice 3; and
2. the same exact Evidence Record against the complete Frozen Pack through Use Scope Review object
   closure through Slice 1.

The operation exists to prevent detached lower-layer successes from being treated as one joint
proof. It produces only a non-persistent process Result and remains
`HUMAN_GATE / NOT_AUTHORIZED`.

## Applicability gate

Use this profile only when the subject has the complete supported chain:

```text
Frozen Pack
-> Rights Evidence
-> two Human Reviews
-> Pair Check
-> Qualification Request / Instruction / Decision
-> Rights Manifest
-> Use Plan
-> Use Scope Review Record
-> Fresh Status Evidence Record
-> explicit finite logical source-chain inputs
```

Do not use Slice 4 for an asset-admission-only flow, a subject without a Use Plan, a subject without
a completed Use Scope Review Record or any partial closure. Do not substitute `None`, a placeholder
or a previous-stage object. A partial-flow requirement needs a separate profile and approval.

## Required in-memory inputs

The verifier requires exactly these eleven keyword-only upstream objects:

```text
pack: CreativeSampleFrozenRealAssetPackManifest
evidence: CreativeSampleRealAssetRightsEvidenceBundleV2
reviewer_a: CreativeSampleRealAssetHumanPackReviewV2
reviewer_b: CreativeSampleRealAssetHumanPackReviewV2
pair_check: CreativeSampleRealAssetReviewPairCheckV2
qualification_request: CreativeSampleRealAssetQualificationRequestV2
qualification_instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22
qualification_decision: CreativeSampleRealAssetQualificationDecisionV2
rights_manifest: CreativeSampleRealAssetRightsManifestV2
use_plan: CreativeSampleRealAssetUsePlanV1
use_scope_review_record: CreativeSampleRealAssetUseScopeReviewRecordV1
```

It additionally requires:

```text
record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1
chains: tuple[FreshStatusRecordChainInputV1, ...]
```

Every upstream object is mandatory. Omission fails before the function runs. `record` and `chains`
must be the exact immutable in-memory values to replay. Do not supply dicts, bytes, documents,
paths, streams, a detached Result, `as_of`, a clock, Provider handle, callback or credential.

All examples and tests under this runbook use synthetic objects only.

## Public operation

```python
verify_fresh_status_evidence_record_joint_replay_v1(
    *,
    pack=pack,
    evidence=evidence,
    reviewer_a=reviewer_a,
    reviewer_b=reviewer_b,
    pair_check=pair_check,
    qualification_request=qualification_request,
    qualification_instruction=qualification_instruction,
    qualification_decision=qualification_decision,
    rights_manifest=rights_manifest,
    use_plan=use_plan,
    use_scope_review_record=use_scope_review_record,
    record=record,
    chains=chains,
)
```

The fixed profile is:

```text
creative-sample-real-asset-fresh-status-record-joint-replay-v1
```

## Procedure

### 1. Preserve the exact caller boundary

Keep the eleven upstream objects, Evidence Record and chain inputs in memory. Do not serialize and
reload an intermediate verification Result. Do not read a path, scan a directory, resolve a
filename, contact a service or obtain a system timestamp.

Do not preselect target Observations separately from `chains`. Slice 4 deliberately has no
`observations` parameter.

### 2. Freshly replay Slice 3 first

Invoke the public Slice 3 operation with the same `record` and exact `chains`:

```text
verify_fresh_status_evidence_record_explicit_chain_coverage_v1
```

This call retains Slice 3's complete fixed admission order, resource bounds, public Slice 2 replay,
target coverage, exact ancestor/self closure and deterministic Record rebuild. Accept only the
freshly returned Result with intact process-local provenance.

If Slice 3 fails, stop. Do not inspect or replay the upstream closure, infer a replacement chain,
trim an Observation or retry automatically.

### 3. Derive only the Request targets from the same chains

For every Source Observation in the admitted chains, derive its exact full reference:

```text
observation_id
observation_sha256
status_category
source_identity_ref_sha256
chain_sha256
```

Resolve every canonically ordered `coverage.request_observation_refs` item from the freshly
returned Slice 3 Result against those full references. Each Request item must resolve to exactly
one immutable Source Observation. Do not reselect the target set from the caller's Record after
coverage replay; Slice 1 independently revalidates the derived documents against that same Record.

The following are forbidden target selectors:

- Observation ID alone;
- caller tuple position;
- filename or path;
- newest-looking timestamp;
- terminal-head shape;
- favorable claim value; or
- a second caller-supplied Observation collection.

Exclude every non-target supporting ancestor from the tuple passed to Slice 1. An Observation that
is both an ancestor and an explicit Request target remains a target.

A missing, duplicate or five-field-drifted resolution after successful Slice 3 indicates a
defensive internal inconsistency. Stop rather than infer or repair a target.

### 4. Replay the complete upstream closure through Slice 1

Invoke the public Slice 1 closure verifier with:

- all eleven upstream objects;
- the target Observation tuple derived in step 3; and
- the same exact `record` supplied to Slice 3.

Slice 1 replays the existing Use Scope Review closure, rebuilds the Fresh Status subject closure,
verifies the internal Request/Instruction/Decision chain and rebuilds the Record with the exact
target Observation documents.

If any supplied upstream object, closure anchor or Record binding drifts, stop with
`PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED`. Do not rewrite an object or parse Slice 1's free-form error
text into a new stable code.

### 5. Compare cross-layer anchors

Require exact agreement across the fresh Slice 1 replay, fresh Slice 3 Result and supplied Record:

```text
Evidence Record ID
full canonical Evidence Record SHA-256
Request ID
Request SHA-256
complete Fresh Status subject_closure
Request Observation count
```

Also retain Slice 3's exact:

```text
chain_count
covered_request_observation_count
provided_observation_count
supporting_ancestor_observation_count
coverage_set_sha256
```

Any impossible post-replay mismatch is `INTERNAL_RESULT_INCONSISTENCY`. Emit no partial Result.

### 6. Build and immediately verify the process Result

Construct `FreshStatusEvidenceRecordJointReplayResultV1` only inside the module's private verifier
context. Derive its joint digest, validate all equations, limitation codes and authority scalar
types, attach private provenance and check that provenance before return.

Do not persist, serialize for later trust, register a Schema for or treat the Result as a receipt.

## Fixed outer failure order

```text
RECORD_CHAIN_COVERAGE_REPLAY_FAILED
TARGET_OBSERVATION_DERIVATION_INCONSISTENT
PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED
INTERNAL_RESULT_INCONSISTENCY
```

The exception provides:

```text
code
coverage_code: optional exact Slice 3 code
replay_code: optional exact Slice 2 code
```

| Outer code | Required response |
| --- | --- |
| `RECORD_CHAIN_COVERAGE_REPLAY_FAILED` | Stop. Report the preserved `coverage_code`; when present, also report `replay_code`. Do not retry or flatten it. |
| `TARGET_OBSERVATION_DERIVATION_INCONSISTENT` | Stop. Treat as an internal invariant violation after Slice 3; do not infer a target. |
| `PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED` | Stop. Identify only the supplied synthetic object boundary; do not parse text, repair or rewrite. |
| `INTERNAL_RESULT_INCONSISTENCY` | Stop. Emit no Result and do not retry automatically. |

Wrap only the known Slice 1, Use Scope Review and Use Plan contract failures. An unrelated
`RuntimeError` or other non-contract implementation failure must propagate unchanged rather than
being mislabeled as `PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED`.

No error writes a file, so there is no rollback, quarantine, rename, permission change or cleanup
phase.

## Success Result

The returned process-only Result contains:

```text
result_type=FRESH_STATUS_EVIDENCE_RECORD_JOINT_REPLAY_RESULT_V1
joint_replay_profile=creative-sample-real-asset-fresh-status-record-joint-replay-v1
source_record_chain_coverage_profile
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
chain_count
covered_request_observation_count
provided_observation_count
supporting_ancestor_observation_count
coverage_set_sha256
joint_replay_sha256
provided_upstream_object_closure_consistent=true
provided_evidence_record_request_explicit_chain_coverage_consistent=true
provided_evidence_record_rebuild_consistent=true
limitation_codes
status=FRESH_STATUS_EVIDENCE_RECORD_JOINT_REPLAY_CONSISTENT
all fixed zero-authority fields
```

Confirm:

```text
request_observation_count == covered_request_observation_count

provided_observation_count
== covered_request_observation_count
 + supporting_ancestor_observation_count
```

The Result does not embed complete Request-reference or chain-summary collections. The exact Record
digest and Slice 3 coverage-set digest bind those already verified projections without creating a
second coverage receipt.

## Reproducible joint digest

Calculate:

```text
SHA256(
  "sdc:creative-sample-real-asset-fresh-status-record-joint-replay-set:v1\0"
  || canonical_compact_json(frozen_projection)
)
```

The projection binds every profile/policy anchor, Evidence Record and Request ID/SHA pair, complete
subject closure, all five counts and `coverage_set_sha256`.

Canonical compact JSON requires:

```text
recursive JSON-object key sorting
UTF-8 and ensure_ascii=false
separators=(",", ":")
no BOM, indentation, whitespace or trailing newline
no NaN or infinity
exact contract-defined array/tuple order
exact JSON boolean and integer types
```

Never hand-concatenate field strings or depend on model field order, dict insertion order or
non-canonical caller order. A projection or domain change requires a version increment.

## Process-local provenance handling

Only the value returned directly from the complete joint verifier has accepted provenance. The
private digest uses:

```text
sdc:creative-sample-real-asset-fresh-status-record-joint-replay-provenance:v1\0
```

and binds every public Result field.

Do not:

- construct the Result directly;
- ordinary-validate a dump;
- reload JSON or Python output;
- use `model_construct`;
- trust a changed `model_copy`; or
- use a cross-process Result as a persistent proof.

The guard prevents routine accidental misuse. It is not cryptographic attestation, hostile-memory
protection, a credential or an authorization token.

## Synthetic test recipes

### Happy paths

Cover at least:

```text
one Genesis target in one chain
one Successor target with all ancestors
multiple targets in one chain
multiple independent chains
one target that is an ancestor of another target
targets on multiple unresolved branches
one Reconciliation target with every branch ancestor
```

For each case, first construct a complete synthetic Frozen Pack through Use Scope Review closure,
then build the exact Fresh Status Record and explicit chains. Assert all three success booleans,
counts, lower-layer profile anchors and identical Result values on repeated calls.

### Complete eleven-object closure

Independently replace or drift each of the eleven upstream objects while retaining a valid Record
and chains. Every case must pass Slice 3 and then stop as
`PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED`. No Result may escape.

Also omit each required keyword in a call-signature test. Omission must be a Python argument
binding failure rather than a partial Slice 4 mode.

### Layer-order separation

Test both directions:

- a mismatched `record` and `chains` fails as `RECORD_CHAIN_COVERAGE_REPLAY_FAILED` without invoking
  Slice 1; and
- valid matching `record` and `chains` with a different upstream closure reaches Slice 1 and fails
  as `PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED`.

Use call sentinels only around the public lower-layer functions. Do not replace their internal
verification semantics in successful tests.

### Exact target derivation

Exercise the private pure derivation helper with:

- one exact five-field match;
- one missing Request target;
- duplicate supplied matches;
- independent drift in document SHA, category, source identity SHA and chain SHA; and
- a supporting ancestor that must not enter the target tuple.

The inconsistent cases use `TARGET_OBSERVATION_DERIVATION_INCONSISTENT`. Do not weaken Slice 3
public invariants merely to make defensive states reachable through the full public API.

### Nested error preservation

For every Slice 3 stable error that can be represented with honest synthetic models, assert:

```text
outer code == RECORD_CHAIN_COVERAGE_REPLAY_FAILED
coverage_code == exact Slice 3 code
```

For every reachable Slice 2 error wrapped by Slice 3, additionally assert the exact
`replay_code`. Do not flatten a nested code into a sentence or convert one nested failure into an
upstream closure failure.

### Determinism and digest

Permute, where Slice 3 permits semantic order independence:

- outer chain inputs;
- targets within each chain; and
- observations within each chain.

Require complete Slice 4 Result equality and one identical `joint_replay_sha256`.

Then change one bound field at a time in private pure digest-projection tests and require digest
sensitivity for every profile/policy anchor, Record/Request anchor, subject-closure anchor, count
and coverage-set digest. Verify recursive nested-key ordering and exact compact UTF-8 encoding.
Reject non-finite numbers. Do not monkeypatch SHA-256 to simulate a collision.

### Provenance and exact scalar types

Confirm:

- direct Result construction fails;
- ordinary validation without the private context fails;
- dump/reload and `model_construct` lack provenance;
- a modified `model_copy` fails the provenance check;
- the fresh returned value retains valid private provenance;
- the seven limitation codes retain exact content and order;
- every false authority field is the exact JSON boolean `false`; and
- every zero authority field is the exact JSON integer `0`.

### Static pure-memory boundary

Parse the production module AST. Allow only deterministic imports needed for hashing, canonical
JSON, typing, Pydantic, exact immutable upstream model types and public Slice 1/Slice 3 operations.

Fail on direct, aliased or attribute-chain access to:

```text
os, pathlib, glob, shutil, tempfile
subprocess, sys.argv, argparse, click, typer
datetime, time
socket, urllib, http, requests, httpx
database, queue, worker, Runtime or Provider adapters
keyring or credential helpers
open, input, eval, exec, compile, __import__
```

Include exact tests for `datetime.now`, `datetime.utcnow`, `datetime.today`, `time.time`, `os.getenv`,
`Path`, `open` and `subprocess.*`. Ruff alone is not the architecture guard.

### Compatibility locks

Verify:

```text
len(sdc.schemas.MODELS) == 67
exactly five Fresh Status persistent top-level models remain registered
Slice 2, Slice 3 and Slice 4 process models are absent from MODELS
all committed Schema bytes are unchanged
all Slice 1, Slice 2 and Slice 3 focused tests remain green
```

Then run Ruff, strict Mypy and one complete offline `make check` in a fresh LF-preserving isolated
worktree containing only the approved Slice 4 files. Do not copy or read repository `output/` or
`tmp/` into that worktree.

## Permitted success statement

After success, it is permissible to say:

> For the exact supplied in-memory objects, the same Fresh Status Evidence Record passed the
> complete provided upstream object-closure replay and the explicit finite Request-target chain
> coverage replay, and its exact Request target Observation documents rebuilt the same immutable
> Record.

Do not say:

- the real-world chain or evidence set is complete;
- every branch, event or newer status was found;
- a source, identity or statement is authentic;
- a statement is true or legally effective;
- the Record is current at this or any other instant;
- the asset is cleared for use; or
- a Provider or execution action may proceed.

## Seven mandatory limitations

```text
SOURCE_AUTHENTICITY_NOT_PROVEN
SOURCE_COMPLETENESS_NOT_PROVEN
CHAIN_COMPLETENESS_NOT_PROVEN
REALITY_CURRENTNESS_NOT_PROVEN
SCOPE_LIMITED_TO_DECLARED_SUBJECT
TIME_WINDOW_LIMITED
LEGAL_EFFECT_NOT_DETERMINED
```

No caller or wrapper may remove, reorder or reinterpret them.

## Zero-authority checklist

Every success must retain:

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

Success does not authorize access, upload, submission, retention, training, processing, generation,
execution, publication, purchase or Provider contact.

## Prohibited actions

This runbook does not authorize:

- any real intake, identity, evidence, Record, output or Provider data;
- reading or writing repository `output/` or `tmp/`;
- a path, filesystem reader/writer, directory scan, CLI or environment lookup;
- implicit or wall-clock time;
- network, Provider, Runtime, credential, database, queue or worker access;
- a persistent result, receipt, Schema, finalizer, rollback or quarantine mechanism;
- automatic discovery, target selection, reconciliation or repair;
- generation, execution, publication, purchase, contact, upload, retention or training; or
- commit, push, PR, merge, tag, release or deployment without separate explicit approval.

## Deferred Slice 5 and later boundaries

An explicit-`as_of` current-status assessor belongs to Slice 5. It must receive the assessment
instant as explicit immutable input and may not obtain an environment or wall clock.

Trusted-local authoring, paths, CLI, create-new persistence, verification receipts, Schema,
rollback, quarantine, network, Provider and execution remain separate later designs. A successful
Slice 4 process Result is not advance approval for any of them.

## Verification handoff

Record only synthetic verification evidence:

- focused Slice 4 results;
- unchanged Slice 1, Slice 2 and Slice 3 focused results;
- Ruff and strict Mypy results;
- exact Schema registry and byte-lock results; and
- one complete offline isolated `make check` result.

Verification success remains `HUMAN_GATE / NOT_AUTHORIZED`. It does not authorize commit, push, PR,
merge, persistent finalization, real-data use or Provider action.
