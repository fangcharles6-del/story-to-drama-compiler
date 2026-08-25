# SDC Creative Sample Real-Asset Fresh Status Record As-Of Assessment Receipt v3.0

## Purpose

Use this runbook to build or historically verify one immutable
`CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1` from a complete synthetic
in-memory Fresh Status closure.

The builder freshly runs the public Slice 5 assessment in the same call. The verifier strictly
admits the supplied Receipt, obtains its exact historical `as_of`, freshly runs the public Slice 5
assessment and requires the rebuilt Receipt to have exactly identical canonical content.

This runbook does not authorize a filesystem read or write, private-data operation, currentness
claim, Provider call, generation, execution, publication or other operational action. Every
success remains `HUMAN_GATE / NOT_AUTHORIZED`.

## Applicability gate

Use this profile only when all of the following are true:

- the complete Frozen Pack through Use Scope Review closure is available as immutable in-memory
  model objects;
- one complete Fresh Status Evidence Record and the exact explicit finite chain tuple are
  available in memory;
- for a build, the caller has deliberately supplied one exact canonical UTC-second `as_of`;
- for verification, the exact Receipt is available as the registered immutable model and its own
  `as_of` is the only assessment instant; and
- all business inputs and examples are synthetic.

Do not use this profile for an asset-admission-only flow, a partial closure, a missing Use Plan or
Use Scope Review Record, a detached Decision, a subset of Request targets, a detached process
Result, real private evidence, an operational currentness decision or a Provider decision.

## Required in-memory inputs

The Receipt builder requires:

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

The historical verifier requires the same first thirteen object/chain values and:

```text
receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
```

Every parameter is mandatory and keyword-only. The verifier does not accept a second `as_of`.
Do not supply dicts, bytes, JSON documents, paths, streams, clock callbacks, Provider handles,
Runtime handles, credentials or any detached Slice 2 through Slice 5 Result.

## Public surface

The module is:

```text
sdc.real_asset_fresh_status_record_as_of_assessment_receipt_v30
```

Its exact public exports are:

```text
FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_V1_PROFILE
FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
FreshStatusRecordAsOfAssessmentReceiptErrorCodeV1
CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error
build_fresh_status_record_as_of_assessment_receipt_v1
verify_fresh_status_record_as_of_assessment_receipt_closure_v1
```

The profile and maximum are:

```text
FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_V1_PROFILE
= creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1

FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
= 65536
```

The only runtime operations are the builder and historical verifier. The module exposes no JSON
reader, bytes parser, extractor, path helper, writer, finalizer, CLI or Provider interface.

## Receipt contract checklist

Require this exact envelope and anti-misuse declaration:

```text
schema_version=1.0.0
document_type=sdc.creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1
profile=creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1
receipt_id=real_asset_fresh_status_record_as_of_assessment_receipt_v1_<20 lowercase hex>
receipt_purpose=HISTORICAL_EXPLICIT_AS_OF_ASSESSMENT_ONLY
reliance_requirement=FULL_CLOSURE_AND_EXPLICIT_AS_OF_REPLAY_REQUIRED
present_currentness_asserted=false
```

Require these exact Slice 5 source literals:

```text
source_assessment_result_type=FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_RESULT_V1
source_assessment_status=FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_COMPLETED
assessment_profile=creative-sample-real-asset-fresh-status-record-as-of-assessment-v1
source_joint_replay_profile=creative-sample-real-asset-fresh-status-record-joint-replay-v1
source_record_chain_coverage_profile=creative-sample-real-asset-fresh-status-record-chain-coverage-v1
source_chain_replay_profile=creative-sample-real-asset-fresh-status-explicit-chain-replay-v1
source_evidence_profile=creative-sample-real-asset-fresh-status-evidence-v3.0
source_evidence_policy_version=3.0.0
source_evidence_policy_document_sha256=ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58
```

Require these exact anchor, assessment and status fields:

```text
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
status=FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_RECORDED
```

The model is strict, frozen, extra-forbid and revalidates instances. It contains no
Receipt-specific policy ID/version/hash, full upstream document, chain object, detached Result,
private provenance, Receipt-document SHA, path, URL, secret, credential or execution handle.

## Stable ID and canonical bytes

The stable ID uses:

```python
stable_id(
    "real_asset_fresh_status_record_as_of_assessment_receipt_v1",
    receipt.model_dump(mode="json", exclude={"receipt_id"}),
)
```

Recalculate the expected ID from every non-ID Receipt field. Do not accept an ID copied from a
different Receipt, and do not exclude limitations, zero-authority values or status from the
projection.

Canonical Receipt bytes are the complete JSON-mode model projection rendered as:

```text
UTF-8 without BOM
sort_keys=true
indent=2
ensure_ascii=false
allow_nan=false
one and only one trailing LF
```

Require recursive key sorting, frozen tuple order, no unknown keys and no non-JSON scalar
substitutions. Canonical bytes must remain unchanged through strict revalidation and must be no
larger than exactly 65,536 bytes.

There is no Receipt self-SHA. `as_of_assessment_sha256` remains the frozen Slice 5 digest and must
be independently recomputed from the Receipt's exact Slice 5 assessment projection. Do not call a
private Slice 5 digest helper and do not create a second assessment digest.

## Build procedure

### 1. Supply the complete closure and explicit instant

Call only:

```python
build_fresh_status_record_as_of_assessment_receipt_v1(
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
    as_of="2026-08-25T00:00:00Z",
)
```

The time shown is synthetic. The caller must supply an exact built-in string in Slice 5's
canonical `YYYY-MM-DDTHH:MM:SSZ` grammar. There is no default, normalization or implicit clock.

### 2. Freshly invoke Slice 5 exactly once

The builder forwards every argument unchanged to the public:

```text
assess_fresh_status_evidence_record_as_of_v1
```

It must not call Slice 4 directly or accept a caller-provided Slice 5 Result. Slice 5 retains its
own order: standalone `as_of` admission, fresh Slice 4 replay, exact anchor binding, pre-evaluation
guard, half-open classification, digest and process provenance.

### 3. Preserve lower-layer failures

If Slice 5 raises its domain error, the builder raises:

```text
AS_OF_ASSESSMENT_REPLAY_FAILED
```

and preserves without reinterpretation:

```text
assessment_code  # Slice 5
joint_replay_code  # Slice 4, when reachable
coverage_code  # Slice 3, when reachable
replay_code  # Slice 2, when reachable
```

Do not parse exception text and do not wrap unrelated runtime or process failures.

### 4. Admit only the live assessment Result

Require the exact `FreshStatusEvidenceRecordAsOfAssessmentResultV1` type returned by the one live
call and require its private Slice 5 provenance to remain valid through the public Slice 5 return
boundary. Bind all profile/policy, Record/Request/Decision, closure, replay, time, disposition,
digest, consistency, limitation and authority values.

An impossible live-Result mismatch is:

```text
ASSESSMENT_RESULT_INCONSISTENT
```

It must not trigger a retry, direct Slice 4 call or use of a detached substitute.

### 5. Compile and close the Receipt

Project every Receipt field only from the live Result and frozen Receipt constants. Derive the
stable ID, strictly validate the model, independently recompute the Slice 5 assessment digest,
require canonical-byte stability and enforce the 65,536-byte maximum.

A derivation, strict validation, digest, ID, canonical or bound failure at this phase is:

```text
INTERNAL_RECEIPT_INCONSISTENCY
```

Return only the exact immutable model. Do not serialize or write it as part of this API.

## Historical verification procedure

### 1. Strictly admit the supplied Receipt

Call only:

```python
verify_fresh_status_record_as_of_assessment_receipt_closure_v1(
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
    receipt=receipt,
)
```

First require the exact model type, strict full-model reconstruction, unchanged canonical bytes,
valid stable ID, independent assessment digest, exact literals, all limitations, zero authority
and the size bound.

Any failure is:

```text
RECEIPT_CONTRACT_INVALID
```

and must occur before Slice 5 is invoked.

### 2. Use only the Receipt's historical instant

After strict admission, read exactly:

```text
receipt.as_of
```

Do not accept, derive or look up another `as_of`. Do not use wall, environment, filesystem,
process, network or Provider time. Verification replays a historical assessment; it does not ask
whether the Record is current now.

### 3. Freshly invoke Slice 5 exactly once

Call the public Slice 5 assessor with the exact supplied thirteen closure values and the admitted
`receipt.as_of`. Preserve a typed Slice 5 failure as `AS_OF_ASSESSMENT_REPLAY_FAILED` with the full
nested error-code chain.

Do not call the public Receipt builder from the verifier because that would invoke Slice 5 a
second time. Compile the expected Receipt through a private pure projection step from the one live
Result.

### 4. Compare the complete historical Receipt

Require both:

```text
supplied_receipt == expected_receipt
canonical_document(supplied_receipt) == canonical_document(expected_receipt)
```

No field may be ignored, normalized, merged or repaired. A difference after successful fresh
assessment is:

```text
RECEIPT_REPLAY_MISMATCH
```

On success, return the strictly revalidated supplied Receipt unchanged. Do not add a verification
timestamp, update status, choose a newer Receipt or produce a new output document.

## Fixed outer failure order

The exact order is:

```text
RECEIPT_CONTRACT_INVALID
AS_OF_ASSESSMENT_REPLAY_FAILED
ASSESSMENT_RESULT_INCONSISTENT
INTERNAL_RECEIPT_INCONSISTENCY
RECEIPT_REPLAY_MISMATCH
```

Apply this precedence table:

| Simultaneous condition | Required first result |
| --- | --- |
| malformed Receipt and invalid upstream closure | `RECEIPT_CONTRACT_INVALID`; zero Slice 5 calls |
| valid Receipt and Slice 5 domain failure | `AS_OF_ASSESSMENT_REPLAY_FAILED` |
| valid Receipt and impossible live Slice 5 Result | `ASSESSMENT_RESULT_INCONSISTENT` |
| valid live Result and impossible expected Receipt derivation | `INTERNAL_RECEIPT_INCONSISTENCY` |
| valid Receipt and successful replay yielding different Receipt | `RECEIPT_REPLAY_MISMATCH` |

The error object exposes:

```text
code
assessment_code
joint_replay_code
coverage_code
replay_code
```

Nested codes are copied as typed values. Exception text is not an interface. There is no retry,
fallback, auto-repair, rollback or quarantine in this slice.

## Historical time semantics

The Receipt preserves Slice 5's exact half-open interval:

```text
[evaluated_at, status_valid_until)
```

For a non-empty interval:

| Receipt `as_of` | Expected behavior |
| --- | --- |
| before `evaluated_at` | Slice 5 failure; no valid Receipt build |
| equal to `evaluated_at` | `WITHIN_EXPLICIT_BOUND_WINDOW` |
| one second before `status_valid_until` | `WITHIN_EXPLICIT_BOUND_WINDOW` |
| equal to `status_valid_until` | `EXPIRED_NOT_CURRENT` |
| after `status_valid_until` | `EXPIRED_NOT_CURRENT` |

For `evaluated_at == status_valid_until`, equality is `EXPIRED_NOT_CURRENT` because the interval
is empty.

The Receipt records what the exact Slice 5 invocation concluded at its explicit historical
instant. It contains no `created_at`, `issued_at`, `verified_at` or implicit present time. A later
verification repeats the same historical instant and does not renew, extend, revoke or supersede
the Receipt. A later `as_of` requires a separately built Receipt.

## Recorded disposition matrix

The Receipt preserves rather than recomputes the recorded Decision:

| Recorded disposition | Window state | Permitted interpretation |
| --- | --- | --- |
| `BLOCKING_STATUS_RECORDED` | either | same recorded blocking Decision plus historical window state |
| `INSUFFICIENT_OR_CONFLICTING_EVIDENCE` | either | same recorded indeterminate Decision plus historical window state |
| `NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET` | either | same finite-set Decision plus historical window state |

Expiry does not clear or create a category. A within-window no-blocking disposition is not rights
clearance, reality currentness or permission.

## Seven mandatory limitations

Every Receipt must retain this exact ordered tuple:

```text
SOURCE_AUTHENTICITY_NOT_PROVEN
SOURCE_COMPLETENESS_NOT_PROVEN
CHAIN_COMPLETENESS_NOT_PROVEN
REALITY_CURRENTNESS_NOT_PROVEN
SCOPE_LIMITED_TO_DECLARED_SUBJECT
TIME_WINDOW_LIMITED
LEGAL_EFFECT_NOT_DETERMINED
```

Do not remove, reorder or reinterpret a limitation for either window state or after successful
historical verification.

## Zero-authority checklist

Every Receipt must retain:

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
present_currentness_asserted=false
provided_record_joint_replay_consistent=true
explicit_as_of_window_assessment_consistent=true
status=FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_RECORDED
```

The consistency flags and recorded status are historical contract facts. They do not modify the
authority boundary.

## Permitted success statements

After build success, the strongest permitted statement is:

> For the exact supplied complete upstream closure, explicit finite chain tuple and explicit
> `as_of`, a same-call public Slice 5 assessment succeeded and this immutable Receipt
> deterministically records that historical assessment projection.

After verification success, the strongest permitted statement is:

> For the exact supplied complete upstream closure and this Receipt's exact historical `as_of`, a
> fresh public Slice 5 assessment rebuilt a Receipt with exactly identical canonical content.

Do not say:

- the Receipt was assessed against the real present;
- the `as_of` source is authentic;
- the source, identity, evidence or statement is authentic or true;
- the finite chain collection is globally complete or excludes every hidden/newer branch;
- current rights, revocation, policy, terms, pricing, capability or availability were proved;
- legal effect, clearance, safety, acceptance or fitness was established;
- a favorable recorded disposition grants permission; or
- a Provider, generation, execution, publication or other action may proceed.

## Synthetic test recipes

### Public API and same-call enforcement

Inspect both signatures and the exact export list. Prove all parameters are keyword-only, no
detached Result can be supplied, verifier has no second `as_of`, and each successful operation
calls the public Slice 5 function exactly once. Reject a malformed Receipt before any Slice 5
call.

### Strict Receipt contract

Exercise exact scalar types, unknown fields, mutated literals, frozen assignment, model-copy and
construct bypass attempts. Strictly reconstruct the whole model and require unchanged canonical
bytes. Attempt cross-Receipt field splicing even when the attacker recomputes `receipt_id`.

### Stable ID and canonical document

Calculate one independent stable-ID golden. Change every non-ID field separately and require ID
sensitivity. Render independently with the frozen JSON rules, including non-ASCII content and
one trailing LF. Prove repeatability across independent reconstructions from the same explicit
inputs. Lock the exact 65,536-byte constant and the bounded rejection path; do not add an
artificial production field solely to manufacture an otherwise unreachable exact-boundary
document when the fixed Receipt topology is already structurally smaller.

### Same-call Slice 5 binding

Instrument the public assessor. Require exact object identity/value forwarding for all thirteen
closure inputs and exact builder `as_of` or admitted `receipt.as_of`. Prove a caller cannot inject
a detached reconstructed Slice 5 Result and that the verifier does not call the public builder.

### Assessment digest and anchors

Independently calculate `as_of_assessment_sha256` using the frozen Slice 5 domain and projection.
Mutate each digest input separately. Exercise Record, Request and Decision ID/SHA, subject closure,
coverage digest and joint replay digest mismatch attempts.

### Time and recorded state

Exercise the lower bound, exclusive upper bound, empty interval and a distant expired instant.
Build synthetic blocking, indeterminate and no-blocking Records at both normal window states.
Require exact preservation of disposition and category tuples without dynamic category reduction.

### Error order and nested codes

Exercise all five outer codes and all reachable Slice 5 through Slice 2 nested codes. Require
typed values and `__cause__` preservation without text parsing. Prove unrelated `RuntimeError`,
`MemoryError` and process interruptions are not converted to Receipt domain codes.

### Limitations and zero authority

For every window/disposition combination, require the exact seven-code tuple, every false/zero
authority field, historical-purpose literals and `present_currentness_asserted=false`. Attempt to
change each field while recomputing the stable ID and require strict contract or replay failure.

### Static pure-memory boundary

Parse the production module AST. Reject filesystem/path, subprocess, environment, implicit-clock,
network, Provider/Runtime, persistence, credential, authorization, execution and CLI surfaces.
Permit deterministic `datetime.strptime`/`UTC` only for explicit supplied timestamp validation or
comparison. Reject a `__main__` branch and import-time side effects.

### Schema and compatibility locks

Require:

```text
registered model count=68
new Schema count=1
new Schema=CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.schema.json
prior 67 Schema paths unchanged
prior 67 Schema bytes unchanged
Slice 2-5 process Results absent from the registry
```

Run focused Slice 1 through Slice 5 suites. Then run the complete offline `make check` once after
the exact diff and Schema checks, using synthetic data only.

## Prohibited actions

This runbook provides no approval for:

- reading or writing a path, directory, private intake or repository `output/`/`tmp/` material;
- parsing JSON/bytes or extracting a Receipt from an external document;
- obtaining time from a wall clock, environment, file metadata, process, network or Provider;
- accepting a detached replay/assessment Result as a same-call invocation;
- discovering, scanning, globbing, selecting `latest` or automatically choosing evidence or a
  Receipt;
- updating, repairing, renewing, revoking, reconciling, extending or replacing a Receipt;
- persisting a model, create-new writing, finalizing, rolling back or quarantining;
- network, Provider, Runtime, Key, credential, entitlement, database, queue or worker access;
- generation, execution, publication, purchase, contact, upload, retention or training; or
- commit, push, PR, merge, tag, release or deployment without separate explicit approval.

## Deferred later boundaries

Trusted-local readers, JSON/bytes parsers, extractors, filesystem/path handling, CLI, create-new
writers and finalizers, external whole-document hashing, rollback, quarantine, Receipt history
chains, automatic latest selection, currentness renewal, network, Provider adapters, credentials,
entitlements and execution remain separate future designs.

The committed Receipt Schema registers only structure. It is not a reader, writer, finalizer,
currentness certificate, authorization or advance approval for any later boundary.

## Verification handoff

Record only synthetic validation facts:

```text
Receipt profile, document type and model name
exact public API and export set
builder and verifier Slice 5 invocation counts
explicit synthetic as_of and expected historical window state
stable ID and independent assessment digest results
strict/canonical/65536-byte boundary results
complete anchor and replay-mismatch results
nested error preservation and fixed-order results
seven limitations and zero-authority results
static forbidden-import/call results
Schema 67-to-68 and prior-byte-preservation results
Slice 1-5 regression results
full offline make check result
```

Do not record a real evidence path, real identity, real asset status, Provider credential,
authorization, present-currentness claim or operational instruction.
