# SDC Creative Sample Real-Asset Fresh Status Record As-Of Assessment v3.0

## Purpose

This runbook governs v3.0 Slice 5: one pure in-memory assessment of a freshly replayed Fresh Status
Evidence Record at one explicit caller-supplied UTC second.

The operation first validates the standalone `as_of` contract, then runs the public Slice 4 joint
replay over the complete supplied closure and explicit chains. Only after replay succeeds does it
compare `as_of` with the exact recorded half-open Decision window. It does not read a clock,
recompile category results, discover later evidence or persist an assessment.

This is a synthetic developer-validation runbook. It is not a real-evidence operating procedure,
current-rights certification, trusted-local file procedure, Provider gate or execution approval.

## Applicability gate

Use this API only when all of the following are true:

- the subject is at the complete Use Scope Review stage supported by Slice 4;
- all eleven required upstream business objects are already immutable in-memory models;
- the exact Fresh Status Evidence Record and exact explicit finite chain tuple are available in
  memory;
- the caller has deliberately selected one explicit assessment second; and
- the task is limited to deterministic synthetic local validation.

Do not use this profile for an asset-admission-only flow, a partial closure, a missing Use Plan or
Use Scope Review Record, a detached Decision, a serialized Result, real private evidence or a
Provider decision.

## Required in-memory inputs

The complete required boundary is:

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
record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1
chains: tuple[FreshStatusRecordChainInputV1, ...]
as_of: str
```

Every parameter is mandatory and keyword-only. Supply the same exact object set that is intended
for the fresh Slice 4 replay. Do not supply dicts, bytes, JSON documents, paths, streams, a detached
Slice 4 Result, a clock callback, Provider handle, Runtime handle or credential.

## Public surface

The module is:

```text
sdc.real_asset_fresh_status_record_as_of_assessment_v30
```

Its exact public exports are:

```text
FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE
FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1
FreshStatusAsOfWindowStateV1
FreshStatusRecordAsOfAssessmentErrorCodeV1
FreshStatusEvidenceRecordAsOfAssessmentResultV1
RealAssetFreshStatusRecordAsOfAssessmentV30Error
assess_fresh_status_evidence_record_as_of_v1
```

The profile and semantics constants are:

```text
FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE
= creative-sample-real-asset-fresh-status-record-as-of-assessment-v1

FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1
= EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE
```

The only operation is:

```python
assess_fresh_status_evidence_record_as_of_v1(
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
    as_of="2026-08-24T00:00:00Z",
)
```

Use only synthetic values in examples and tests. A successful call remains
`HUMAN_GATE / NOT_AUTHORIZED`.

## Explicit `as_of` admission

`as_of` must be an exact built-in string in this form:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Admission is fail-closed:

1. require `type(as_of) is str`;
2. require the exact digit and literal-separator grammar;
3. parse it as a valid UTC Gregorian calendar second; and
4. format that parsed instant back to UTC seconds and require exact equality.

Accepted values are never normalized. Reject:

- `2026-08-24T08:00:00+08:00`;
- `2026-08-24T00:00:00.000Z`;
- `2026-08-24t00:00:00z`;
- leading or trailing whitespace;
- incomplete or non-zero-padded components;
- impossible dates, `24:00:00`, leap seconds and `PERPETUAL`;
- integer or floating epochs, Boolean, bytes, `datetime`, `None`; and
- a subclass of `str`.

The caller must supply the value. There is no default and no fallback to wall, environment,
filesystem, process or network time.

## Procedure

### 1. Admit only the standalone `as_of` contract

Validate `as_of` before calling any lower layer. Do not inspect Record fields in this phase. A
failure returns:

```text
AS_OF_CONTRACT_INVALID
```

No Slice 4 work occurs after that failure.

### 2. Freshly replay Slice 4

Call `verify_fresh_status_evidence_record_joint_replay_v1` exactly once with the exact supplied:

```text
pack
evidence
reviewer_a
reviewer_b
pair_check
qualification_request
qualification_instruction
qualification_decision
rights_manifest
use_plan
use_scope_review_record
record
chains
```

Do not accept a caller-provided Result and do not invoke Slice 1 or Slice 3 independently as a
substitute. Slice 4 preserves its own order: Slice 3 coverage, exact target derivation, Slice 1
complete closure, cross-layer anchors and process Result provenance.

### 3. Preserve nested replay failures

If the public Slice 4 API raises its domain error, convert it once to:

```text
RECORD_JOINT_REPLAY_FAILED
```

Preserve without reinterpretation:

```text
joint_replay_code  # Slice 4
coverage_code      # Slice 3, when reachable
replay_code        # Slice 2, when reachable
```

Do not parse exception text. Do not catch an unrelated `RuntimeError`, `MemoryError` or process
interruption as a replay-domain failure.

### 4. Bind the freshly replayed anchors

From the exact supplied Record, deterministically calculate:

- the full canonical Evidence Record SHA-256; and
- the full canonical Decision SHA-256.

Require the Record and Request IDs/SHA values, subject closure, coverage digest and joint replay
digest to remain bound to the fresh Slice 4 Result. Require the calculated Decision digest to
equal `record.decision_sha256`.

Only after these checks may the assessor read:

```text
record.decision.evaluated_at
record.decision.status_valid_until
record.decision.disposition
record.decision.blocking_categories
record.decision.indeterminate_categories
```

An impossible mismatch is `INTERNAL_RESULT_INCONSISTENCY`; it is not an invitation to select
another Record, Decision, chain or time.

### 5. Apply the pre-evaluation guard

Compare the parsed explicit instants. If:

```text
as_of < evaluated_at
```

stop with:

```text
AS_OF_PRECEDES_RECORD_EVALUATION
```

Do not return a `NOT_YET_CURRENT` state and do not recompile the historical Record at the earlier
instant.

### 6. Classify the half-open window

Apply exactly:

```text
evaluated_at <= as_of < status_valid_until
    -> WITHIN_EXPLICIT_BOUND_WINDOW

as_of >= status_valid_until
    -> EXPIRED_NOT_CURRENT
```

The lower bound is inclusive. The upper bound is exclusive. There is no tolerance or grace
period.

If `evaluated_at == status_valid_until`, the interval is empty. The exact evaluation second is
therefore `EXPIRED_NOT_CURRENT`.

### 7. Preserve the recorded Decision

Copy the exact recorded disposition and category tuples into the Result. Do not rerun category
reduction at `as_of`, change a claim, add or remove a relied-on Observation, choose a later chain
head or reinterpret expiry as an adverse or favorable fact.

### 8. Derive and verify the process Result

Derive the assessment digest, construct the Result only under the private process sentinel and
immediately verify its provenance. No Result is returned from a partial or failed phase.

## Fixed outer failure order

The stable order is:

```text
AS_OF_CONTRACT_INVALID
RECORD_JOINT_REPLAY_FAILED
AS_OF_PRECEDES_RECORD_EVALUATION
INTERNAL_RESULT_INCONSISTENCY
```

Use the following precedence rules:

| Simultaneous defect | Required first result |
| --- | --- |
| malformed `as_of` and invalid replay input | `AS_OF_CONTRACT_INVALID` |
| canonical pre-evaluation `as_of` and invalid replay input | `RECORD_JOINT_REPLAY_FAILED` |
| canonical pre-evaluation `as_of` and valid replay | `AS_OF_PRECEDES_RECORD_EVALUATION` |
| valid replay and impossible derived anchors/Result | `INTERNAL_RESULT_INCONSISTENCY` |

`EXPIRED_NOT_CURRENT` is a successful assessment state and never an error code.

## Half-open boundary table

For `evaluated_at < status_valid_until`:

| Explicit instant | Expected behavior |
| --- | --- |
| `evaluated_at - 1 second` | `AS_OF_PRECEDES_RECORD_EVALUATION` |
| `evaluated_at` | `WITHIN_EXPLICIT_BOUND_WINDOW` |
| `evaluated_at + 1 second` | `WITHIN_EXPLICIT_BOUND_WINDOW` |
| `status_valid_until - 1 second` | `WITHIN_EXPLICIT_BOUND_WINDOW` |
| `status_valid_until` | `EXPIRED_NOT_CURRENT` |
| `status_valid_until + 1 second` | `EXPIRED_NOT_CURRENT` |

For `evaluated_at == status_valid_until`:

| Explicit instant | Expected behavior |
| --- | --- |
| before `evaluated_at` | `AS_OF_PRECEDES_RECORD_EVALUATION` |
| exactly `evaluated_at` | `EXPIRED_NOT_CURRENT` |
| after `evaluated_at` | `EXPIRED_NOT_CURRENT` |

## Success Result

`FreshStatusEvidenceRecordAsOfAssessmentResultV1` contains this exact public projection:

```text
result_type=FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_RESULT_V1
assessment_profile=creative-sample-real-asset-fresh-status-record-as-of-assessment-v1
source_joint_replay_profile
source_record_chain_coverage_profile
source_chain_replay_profile
source_evidence_profile
source_evidence_policy_version
source_evidence_policy_document_sha256
evidence_record_id
evidence_record_sha256
request_id
request_sha256
decision_id
decision_sha256
subject_closure
coverage_set_sha256
joint_replay_sha256
as_of
evaluated_at
status_valid_until
window_semantics=EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE
recorded_disposition
recorded_blocking_categories
recorded_indeterminate_categories
as_of_window_state
as_of_assessment_sha256
provided_record_joint_replay_consistent=true
explicit_as_of_window_assessment_consistent=true
limitation_codes
status=FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_COMPLETED
the complete zero-authority field set
```

The Result is strict, frozen and process-local. It is not registered in the Schema registry and
has no supported parser, canonical document writer or persistence boundary.

Require these exact profile and policy bindings:

```text
assessment_profile=creative-sample-real-asset-fresh-status-record-as-of-assessment-v1
source_joint_replay_profile=creative-sample-real-asset-fresh-status-record-joint-replay-v1
source_record_chain_coverage_profile=creative-sample-real-asset-fresh-status-record-chain-coverage-v1
source_chain_replay_profile=creative-sample-real-asset-fresh-status-explicit-chain-replay-v1
source_evidence_profile=creative-sample-real-asset-fresh-status-evidence-v3.0
source_evidence_policy_version=3.0.0
source_evidence_policy_document_sha256=ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58
```

## Reproducible assessment digest

Use this exact domain, including the final NUL byte:

```text
sdc:creative-sample-real-asset-fresh-status-record-as-of-assessment:v1\0
```

The digest projection contains exactly:

```text
assessment_profile
source_joint_replay_profile
source_record_chain_coverage_profile
source_chain_replay_profile
source_evidence_profile
source_evidence_policy_version
source_evidence_policy_document_sha256
evidence_record_id
evidence_record_sha256
request_id
request_sha256
decision_id
decision_sha256
subject_closure
coverage_set_sha256
joint_replay_sha256
as_of
evaluated_at
status_valid_until
window_semantics
recorded_disposition
recorded_blocking_categories
recorded_indeterminate_categories
as_of_window_state
```

Construct one projection object, convert Pydantic values to their JSON-mode forms and serialize
with:

```text
UTF-8
sort_keys=true
separators=(",", ":")
ensure_ascii=false
allow_nan=false
```

Then calculate:

```text
SHA256(domain_bytes || canonical_compact_json(projection))
```

Do not manually concatenate projected fields. Do not include `as_of_assessment_sha256`, completion
status, consistency flags, limitations, zero-authority fields or private provenance in this digest.

## Process-local provenance handling

Result construction requires the private context key:

```text
fresh_status_record_as_of_assessment_verifier_provenance
```

and an unexported process sentinel. The private provenance digest domain is:

```text
sdc:creative-sample-real-asset-fresh-status-record-as-of-assessment-provenance:v1\0
```

It binds the complete public Result `model_dump(mode="json", exclude_none=false)` under the same
compact canonical JSON rules. Verify the sentinel and digest immediately before returning.

Never treat model construction, `model_validate`, `model_dump`, copy, pickle or a serialized value
as evidence that the public assessor ran successfully. Provenance is process-local and is not a
receipt or authority token.

## Recorded disposition matrix

The assessor preserves, rather than recomputes, these exact Decision dispositions:

| Recorded disposition | Window state | Permitted interpretation |
| --- | --- | --- |
| `BLOCKING_STATUS_RECORDED` | either | same recorded blocking Decision plus temporal window state |
| `INSUFFICIENT_OR_CONFLICTING_EVIDENCE` | either | same recorded indeterminate Decision plus temporal window state |
| `NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET` | either | same finite-set Decision plus temporal window state |

No combination authorizes use. In particular, within-window plus no-blocking does not mean rights
clear, complete, safe, Provider-ready or current in reality.

## Synthetic test recipes

### Canonical time admission

Test one valid whole-second UTC value. Parameterize offset, fractional, lowercase, whitespace,
invalid date/time, leap second, `PERPETUAL`, bytes, numeric, Boolean, `datetime`, `None` and `str`
subclass values. Assert one stable `AS_OF_CONTRACT_INVALID` and zero Slice 4 calls.

### Window boundaries

Use a synthetic Record with a non-empty Decision horizon and test the six rows in the boundary
table. Build an all-unrelied synthetic Record whose `status_valid_until == evaluated_at` and prove
that the equality instant is expired.

### All recorded dispositions

Build synthetic blocking, indeterminate and no-blocking Records. Assess each within its window and
at its exclusive endpoint. Require exact preservation of disposition, blocking tuple and
indeterminate tuple.

### No dynamic reduction

Include a synthetic Observation that was unrelied at Checker evaluation but whose own onset is
before a later `as_of`. Require the original category result and Decision projections to remain
unchanged. Do not admit or discover another Observation.

### Layer ordering

Instrument the public Slice 4 call. Prove standalone time validation runs first, Slice 4 runs once
for canonical time, and no Record time comparison occurs after a replay failure.

### Nested errors

Exercise every Slice 4 outer code. Require exact `joint_replay_code`; for reachable coverage and
chain failures require exact `coverage_code` and `replay_code`. Confirm no exception-text parsing
and no wrapping of unrelated Runtime failures.

### Result and digest

Independently calculate the Decision canonical SHA-256 and the assessment digest. Mutate each
digest-projection field separately and prove sensitivity. Verify identical inputs across repeated
processes produce identical public Result values and digests.

### Provenance and strictness

Reject direct construction without private context, strict-type substitutions, unknown fields,
altered literals and changed zero-authority values. Exercise reconstruction, model copy,
`deepcopy`, pickle and private-provenance tampering without creating a valid public success.

### Static pure-memory boundary

Parse the production module AST. Permit deterministic `datetime.strptime` and `UTC` use for the
explicit value. Reject filesystem/path modules, subprocess, time/environment lookup, `now`,
`utcnow`, `today`, sockets, HTTP, Provider/Runtime, persistence, credential, execution and CLI
surfaces.

### Compatibility locks

Run Slice 1 through Slice 4 focused suites. Require exactly 67 registered models, exactly the five
existing persistent Fresh Status models and no Slice 5 Result registration. Compare every
committed Schema byte with its prior reviewed value.

Finally, run the complete offline `make check` once in a fresh LF-preserving isolated worktree.
Use synthetic temporary data only.

## Permitted success statements

For `WITHIN_EXPLICIT_BOUND_WINDOW`, the strongest permitted statement is:

> The exact supplied Fresh Status Evidence Record and explicit finite chain collection passed fresh
> Slice 4 replay, and the explicit caller-supplied `as_of` second lies inside the Record's frozen
> inclusive/exclusive Decision window.

For `EXPIRED_NOT_CURRENT`, the strongest permitted statement is:

> The exact supplied inputs passed fresh Slice 4 replay, and the explicit caller-supplied `as_of`
> second is at or beyond the Record's frozen exclusive Decision horizon.

Do not say:

- the instant is an authentic present time;
- the real-world evidence set or chain history is complete;
- the recorded claims remain true outside the supplied finite closure;
- expiry proves an adverse state or restores a favorable one;
- the asset is currently clear, safe or valid for use; or
- a Provider or execution action may proceed.

## Seven mandatory limitations

Every successful Result contains this exact ordered tuple:

```text
SOURCE_AUTHENTICITY_NOT_PROVEN
SOURCE_COMPLETENESS_NOT_PROVEN
CHAIN_COMPLETENESS_NOT_PROVEN
REALITY_CURRENTNESS_NOT_PROVEN
SCOPE_LIMITED_TO_DECLARED_SUBJECT
TIME_WINDOW_LIMITED
LEGAL_EFFECT_NOT_DETERMINED
```

Do not remove, reorder or reinterpret a limitation for either window state.

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

Also require:

```text
provided_record_joint_replay_consistent=true
explicit_as_of_window_assessment_consistent=true
```

Those consistency facts do not modify the authority boundary.

## Prohibited actions

This runbook provides no approval for:

- reading or writing a path, directory, private intake or repository `output/`/`tmp/` material;
- obtaining time from a wall clock, environment, file metadata, process, network or Provider;
- accepting a detached replay or assessment Result as a fresh invocation;
- discovering, scanning, globbing, selecting `latest` or automatically choosing evidence;
- updating, repairing, reconciling, extending or replacing a Record;
- persisting a Result, creating a receipt, finalizing, rolling back or quarantining;
- network, Provider, Runtime, Key, credential, entitlement, database, queue or worker access;
- generation, execution, publication, purchase, contact, upload, retention or training; or
- commit, push, PR, merge, tag, release or deployment without separate explicit approval.

## Deferred later boundaries

Trusted-local input admission, authoring preparation, filesystem/path handling, CLI, create-new
persistence, historical verification receipts, Schema, rollback, quarantine, network, Provider,
credentials, entitlements and execution remain separate future designs. A successful process
assessment is not advance approval for any of them.

## Verification handoff

Record only synthetic validation facts:

```text
assessment profile
exact public API and export set
explicit as_of value used by the synthetic case
fresh Slice 4 invocation count
window semantics and expected boundary state
nested error preservation results
independent assessment digest result
process-local provenance checks
zero-authority and limitation checks
static forbidden-import/call checks
Slice 1-4 regression results
Schema registry and byte-preservation results
full offline make check result
```

Do not record a real evidence path, real identity, real asset status, Provider credential,
authorization or operational currentness claim.
