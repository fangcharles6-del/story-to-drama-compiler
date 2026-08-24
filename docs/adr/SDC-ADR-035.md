# SDC-ADR-035: Fresh Status Evidence Record As-Of Assessment v3.0

- Status: Accepted
- Date: 2026-08-24
- Depends on: SDC-ADR-031 / Fresh Status Evidence v3.0 Slice 1
- Depends on: SDC-ADR-032 / Explicit Finite Fresh Status Source-Chain Replay v3.0 Slice 2
- Depends on: SDC-ADR-033 / Fresh Status Evidence Record Chain Coverage v3.0 Slice 3
- Depends on: SDC-ADR-034 / Fresh Status Evidence Record Joint Replay v3.0 Slice 4
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: explicit synthetic in-memory model objects and one explicit UTC second only

## Context

Slice 1 freezes the Fresh Status Evidence Record, its Checker `evaluated_at`, its Decision
`status_valid_until`, and the rule that the Decision horizon is a half-open interval. Slice 2
replays one explicitly supplied finite logical source chain. Slice 3 proves exact Request target
coverage across an explicitly supplied finite chain collection. Slice 4 freshly composes that
chain-coverage replay with the complete Frozen Pack through Use Scope Review object-closure
replay.

Slice 4 deliberately accepts no assessment instant and makes no currentness statement. Its
successful process Result proves only consistency of the exact finite objects supplied to that
invocation. A caller still needs one narrow deterministic operation that asks whether the already
recorded Decision window contains one explicit caller-supplied UTC second without trusting a
detached Slice 4 Result or introducing a clock.

Slice 5 closes only that temporal assessment gap. It does not recompile the Record at another
instant, rediscover evidence, choose a newer chain head, infer a real-world state, repair an
expired Record, persist a receipt or authorize a later action.

## Decision

Add one pure in-memory v3.0 module:

```text
src/sdc/real_asset_fresh_status_record_as_of_assessment_v30.py
```

The module exposes one assessment operation. It receives the same complete immutable upstream
object set, Evidence Record and explicit chain tuple required by Slice 4, plus one mandatory
keyword-only `as_of` string. It validates only the standalone `as_of` contract first, freshly
invokes the public Slice 4 verifier, then compares the verified Record's frozen time anchors using
the fixed half-open policy.

The assessment has exactly two normal window states:

```text
WITHIN_EXPLICIT_BOUND_WINDOW
EXPIRED_NOT_CURRENT
```

An instant earlier than the Record's evaluation is not a third state. It is a stable domain
failure because Slice 5 is not a historical backdating or counterfactual recomputation API.

Every successful Result remains strict, frozen, process-local, non-persistent and
zero-authority. Even `WITHIN_EXPLICIT_BOUND_WINDOW` means only that the verified recorded window
contains the explicit `as_of` second. The mandatory `REALITY_CURRENTNESS_NOT_PROVEN` limitation
remains present.

## Applicability and complete required inputs

Slice 5 applies only to the complete Use Scope Review profile already admitted by Slice 4. Every
one of these inputs is required and keyword-only:

| Parameter | Required immutable value |
| --- | --- |
| `pack` | `CreativeSampleFrozenRealAssetPackManifest` |
| `evidence` | `CreativeSampleRealAssetRightsEvidenceBundleV2` |
| `reviewer_a` | `CreativeSampleRealAssetHumanPackReviewV2` |
| `reviewer_b` | `CreativeSampleRealAssetHumanPackReviewV2` |
| `pair_check` | `CreativeSampleRealAssetReviewPairCheckV2` |
| `qualification_request` | `CreativeSampleRealAssetQualificationRequestV2` |
| `qualification_instruction` | `CreativeSampleRealAssetQualificationDecisionInstructionV22` |
| `qualification_decision` | `CreativeSampleRealAssetQualificationDecisionV2` |
| `rights_manifest` | `CreativeSampleRealAssetRightsManifestV2` |
| `use_plan` | `CreativeSampleRealAssetUsePlanV1` |
| `use_scope_review_record` | `CreativeSampleRealAssetUseScopeReviewRecordV1` |
| `record` | `CreativeSampleRealAssetFreshStatusEvidenceRecordV1` |
| `chains` | `tuple[FreshStatusRecordChainInputV1, ...]` |
| `as_of` | exact built-in `str` in canonical UTC-second form |

Omission fails at the Python call boundary. Slice 5 has no partial-closure profile and no optional
upstream object. It is not applicable to asset-admission-only flows, a subject without a Use Plan,
a subject without a completed Use Scope Review Record, a detached Decision or a detached Slice 4
Result. A future partial-flow use case requires a separately named profile and API.

All business-object fixtures for this slice use synthetic in-memory data only. Static compatibility
tests may inspect tracked source and Schema bytes but never private business material.

## Frozen compatibility boundary

Slice 5 must not change:

- any persistent Slice 1 model or any of its five committed Schema files;
- the 67-entry Schema registry;
- the Slice 1 evidence profile, policy version, policy digest, stable-ID projections, canonical
  document rules, transition rules, time formulas, dispositions or Record compiler;
- the Slice 2 replay profile, graph rules, resource limits, errors, digest or provenance;
- the Slice 3 coverage profile, admission order, errors, coverage digest or provenance;
- the Slice 4 required input set, replay order, errors, joint digest or provenance;
- any Frozen Pack, Rights Evidence, Review, Qualification, Rights Manifest, Use Plan or Use Scope
  Review contract; or
- any trusted-local finalizer, filesystem verifier or authority state.

The Slice 5 Result is a process value. It is absent from `sdc.schemas.MODELS` and has no JSON
parser, document builder, supported serialization round trip or committed Schema.

## Frozen profile and public API

The assessment profile is:

```text
creative-sample-real-asset-fresh-status-record-as-of-assessment-v1
```

The exact public surface is:

```text
FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_V1_PROFILE
FRESH_STATUS_AS_OF_WINDOW_SEMANTICS_V1
FreshStatusAsOfWindowStateV1
FreshStatusRecordAsOfAssessmentErrorCodeV1
FreshStatusEvidenceRecordAsOfAssessmentResultV1
RealAssetFreshStatusRecordAsOfAssessmentV30Error
assess_fresh_status_evidence_record_as_of_v1
```

The only public operation is:

```python
assess_fresh_status_evidence_record_as_of_v1(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    qualification_request: CreativeSampleRealAssetQualificationRequestV2,
    qualification_instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
    qualification_decision: CreativeSampleRealAssetQualificationDecisionV2,
    rights_manifest: CreativeSampleRealAssetRightsManifestV2,
    use_plan: CreativeSampleRealAssetUsePlanV1,
    use_scope_review_record: CreativeSampleRealAssetUseScopeReviewRecordV1,
    record: CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    as_of: str,
) -> FreshStatusEvidenceRecordAsOfAssessmentResultV1
```

The operation accepts already constructed immutable in-memory models and one exact string. It
accepts no dict, bytes, JSON document, stream, path, directory, CLI namespace, optional clock,
environment lookup, filesystem timestamp, callback, detached Result, Provider handle, Runtime
handle, entitlement or credential.

Every Result freezes these exact profile and policy bindings:

| Field | Exact value |
| --- | --- |
| `assessment_profile` | `creative-sample-real-asset-fresh-status-record-as-of-assessment-v1` |
| `source_joint_replay_profile` | `creative-sample-real-asset-fresh-status-record-joint-replay-v1` |
| `source_record_chain_coverage_profile` | `creative-sample-real-asset-fresh-status-record-chain-coverage-v1` |
| `source_chain_replay_profile` | `creative-sample-real-asset-fresh-status-explicit-chain-replay-v1` |
| `source_evidence_profile` | `creative-sample-real-asset-fresh-status-evidence-v3.0` |
| `source_evidence_policy_version` | `3.0.0` |
| `source_evidence_policy_document_sha256` | `ce1a486ba2ce4021ab6a5bf47a859216a90ac600bc4054b1742d64f68c242b58` |

## Explicit `as_of` contract

`as_of` is an exact built-in `str` with this complete grammar:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Validation requires all of the following before Slice 4 is called:

1. `type(as_of) is str`;
2. the value matches exactly four year digits, two digits for every other component, literal
   separators, literal `T` and uppercase `Z`;
3. the value is a valid UTC Gregorian calendar second; and
4. deterministic parse followed by UTC whole-second formatting reproduces the exact original
   string.

The assessor rejects rather than normalizes offsets, fractional seconds, local time, whitespace,
lowercase `z`, epoch numbers, `datetime` values, bytes, invalid calendar dates, leap seconds,
`PERPETUAL` and string subclasses. It performs no trimming, timezone conversion, rounding,
truncation or fallback.

The module may use deterministic `datetime.strptime` plus `UTC` only to validate and compare the
explicit strings. It must never call `datetime.now`, `datetime.utcnow`, `date.today`, `time.time`
or obtain time from a file, environment, process, network or Provider.

## Fixed assessment order

The assessor performs these phases in this exact order:

1. validate only the standalone `as_of` contract;
2. invoke `verify_fresh_status_evidence_record_joint_replay_v1` with the exact supplied thirteen
   object/chain inputs;
3. accept only the freshly returned provenance-bearing Slice 4 Result;
4. bind that Result back to the exact verified Record, Request and Decision anchors, including the
   full canonical Decision SHA-256;
5. read `evaluated_at` and `status_valid_until` only from that freshly replayed exact Record;
6. reject `as_of < evaluated_at`;
7. classify the explicit instant with the frozen half-open policy;
8. derive the assessment digest and construct the minimal Slice 5 Result under private
   process-local provenance; and
9. immediately recheck Result provenance before returning.

The first phase does not inspect or pre-validate a lower-layer object. After `as_of` passes its own
contract, Slice 5 must not pre-read Record times or otherwise reorder Slice 4 failures. If Slice 4
fails, no temporal state or Result is produced.

## Frozen half-open window semantics

The exact semantics token is:

```text
EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE
```

The assessed interval is:

```text
[record.decision.evaluated_at, record.decision.status_valid_until)
```

The deterministic mapping is:

| Condition | Outcome |
| --- | --- |
| `as_of < evaluated_at` | fail with `AS_OF_PRECEDES_RECORD_EVALUATION` |
| `evaluated_at <= as_of < status_valid_until` | `WITHIN_EXPLICIT_BOUND_WINDOW` |
| `as_of >= status_valid_until` | `EXPIRED_NOT_CURRENT` |

The lower endpoint is inclusive and the upper endpoint is exclusive. One second before the upper
endpoint remains within the explicit bound window; the exact upper endpoint is expired.

Slice 1 intentionally permits `status_valid_until == evaluated_at` when no Observation is relied
on anywhere in the Record. That creates an empty interval. At that boundary,
`as_of == evaluated_at == status_valid_until` yields `EXPIRED_NOT_CURRENT`, not a transient
within-window state.

There is no tolerance, grace period, automatic extension, nearest-second selection or implicit
present instant. A canonical instant arbitrarily later than the upper endpoint remains a normal
`EXPIRED_NOT_CURRENT` assessment rather than an error.

## Recorded Decision preservation

Slice 5 assesses the already compiled Decision window. It does not run Slice 1's category
reduction again at `as_of`. The Result therefore binds and preserves exactly:

- `record.decision.disposition`;
- `record.decision.blocking_categories`; and
- `record.decision.indeterminate_categories`.

The window state and recorded disposition are independent axes. Every recorded disposition can
coexist with either window state:

```text
BLOCKING_STATUS_RECORDED
INSUFFICIENT_OR_CONFLICTING_EVIDENCE
NO_BLOCKING_STATUS_OBSERVED_WITHIN_EXPLICIT_BOUND_SET
```

Expiry never flips `PRESENT` to `ABSENT_WITH_EVIDENCE`, converts an indeterminate state to a
determined one, removes a blocking category or restores a favorable historical state. Likewise,
an Observation that was not relied on at `evaluated_at` cannot become relied on merely because its
own `valid_from` or `observed_at` is earlier than a later `as_of` value. A new assessment after new
evidence requires a new upstream Record under separately approved work.

## Fixed outer error model

The outer stable error codes run in this exact order:

```text
AS_OF_CONTRACT_INVALID
RECORD_JOINT_REPLAY_FAILED
AS_OF_PRECEDES_RECORD_EVALUATION
INTERNAL_RESULT_INCONSISTENCY
```

The Slice 5 error object exposes its own code and these optional nested lower-layer fields:

```text
joint_replay_code
coverage_code
replay_code
```

Rules:

- an invalid standalone `as_of` becomes `AS_OF_CONTRACT_INVALID` before Slice 4 runs;
- a Slice 4 domain failure becomes `RECORD_JOINT_REPLAY_FAILED` and preserves its exact
  `joint_replay_code`, `coverage_code` and `replay_code` values without text parsing;
- after successful replay, an earlier assessment instant becomes
  `AS_OF_PRECEDES_RECORD_EVALUATION`;
- an impossible cross-layer anchor, digest, state or derived Result mismatch becomes
  `INTERNAL_RESULT_INCONSISTENCY`;
- an expired instant is a successful `EXPIRED_NOT_CURRENT` result, not an error;
- unrelated `RuntimeError`, `MemoryError`, process interruption and other non-domain failures are
  not reclassified as a temporal or replay-domain failure; and
- no failure is retried, repaired, normalized, reconciled, persisted, rolled back or quarantined.

This ordering intentionally means a malformed `as_of` wins over a simultaneous damaged replay
input. Once `as_of` is canonical, a replay failure wins over a simultaneous pre-evaluation time:
the assessor cannot trust the Record's time anchors until fresh replay succeeds.

## Minimal process Result

`FreshStatusEvidenceRecordAsOfAssessmentResultV1` is strict and frozen. Its public fields are
limited to:

```text
result_type=FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_RESULT_V1
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
the complete forced zero-authority field set
```

`decision_sha256` is the ordinary SHA-256 of the exact canonical Decision document and must equal
the outer Record's stored `decision_sha256`. Record ID/SHA, Request ID/SHA and subject closure must
match both the freshly returned Slice 4 Result and exact supplied Record. The coverage-set and joint
replay digests come only from that fresh Slice 4 Result and are bound into the Slice 5 digest.

The Result does not embed the full Record, chains, observations or any source bytes. It does not
contain a clock reading, path, URL, filename, identity secret, credential, Provider data,
authorization, receipt or execution handle.

## Reproducible assessment digest

The digest domain is the exact byte string:

```text
sdc:creative-sample-real-asset-fresh-status-record-as-of-assessment:v1\0
```

`as_of_assessment_sha256` is:

```text
SHA256(
  domain_bytes
  || canonical_compact_json(
       assessment_profile,
       source_joint_replay_profile,
       source_record_chain_coverage_profile,
       source_chain_replay_profile,
       source_evidence_profile,
       source_evidence_policy_version,
       source_evidence_policy_document_sha256,
       evidence_record_id,
       evidence_record_sha256,
       request_id,
       request_sha256,
       decision_id,
       decision_sha256,
       subject_closure,
       coverage_set_sha256,
       joint_replay_sha256,
       as_of,
       evaluated_at,
       status_valid_until,
       window_semantics,
       recorded_disposition,
       recorded_blocking_categories,
       recorded_indeterminate_categories,
       as_of_window_state
     )
)
```

The displayed list identifies the exact closed projection, not a manual concatenation order. The
implementation constructs one object and serializes it as UTF-8 compact canonical JSON with
lexicographically sorted keys, no insignificant whitespace, `ensure_ascii=false` and
`allow_nan=false`. `subject_closure` uses its full JSON-mode projection. Tuple values retain their
frozen policy order.

The projection deliberately excludes the assessment digest itself, Result completion status,
consistency booleans, limitations, zero-authority fields and private provenance. Adding, removing,
renaming or reinterpreting a projected field or changing the domain requires a version increment.

## Process-local provenance

The Result may be constructed only inside the assessment operation with a private context sentinel.
After construction it carries a private provenance tuple containing the process sentinel and a
digest over:

```text
sdc:creative-sample-real-asset-fresh-status-record-as-of-assessment-provenance:v1\0
|| canonical_compact_json(full public Result projection)
```

The function checks that provenance immediately before return. Direct model construction,
ordinary `model_validate`, reconstruction from `model_dump`, serialization round trips and copied
or altered values are not supported evidence of a successful Slice 5 invocation. The private
sentinel and provenance digest are not public authority fields and must never be serialized as a
receipt.

## Pure-memory static boundary

The production module is limited to deterministic hashing, canonical JSON, exact UTC parsing,
Pydantic validation and calls to the existing pure Slice 4 API. It must not import or call:

- `os`, `pathlib`, `subprocess`, `shutil`, `tempfile`, `glob` or filesystem APIs;
- `time`, `datetime.now`, `datetime.utcnow`, `date.today` or an environment clock;
- sockets, HTTP clients, URLs, browser APIs, network discovery or Provider/Runtime adapters;
- database, queue, worker, ledger, cache, persistence, finalizer, receipt, rollback or quarantine
  APIs;
- credential, Key, token, entitlement or authorization stores; or
- generation, execution, publication, purchase, contact, upload, retention or training APIs.

No import-time side effect is permitted. The implementation receives no path and performs no I/O.
Static AST tests lock the module against prohibited imports, calls, names and a `__main__`/CLI
surface while allowing only deterministic UTC parsing of the explicit input.

## Synthetic verification matrix

The Slice 5 tests must cover at least:

### Time grammar and exact scalar types

- one valid canonical UTC second;
- offsets, fractional seconds, lowercase `z`, leading/trailing whitespace and `PERPETUAL`;
- invalid month, day, hour, minute, second, invalid leap-day combinations and leap seconds;
- empty string, bytes, integer, float, Boolean, `datetime`, `None` and a `str` subclass; and
- proof that rejected representations are not normalized.

### Half-open boundaries

- `as_of == evaluated_at` with a non-empty horizon;
- one second after `evaluated_at`;
- one second before `status_valid_until`;
- `as_of == status_valid_until`;
- one second and a distant canonical instant after `status_valid_until`;
- one second before `evaluated_at`; and
- `evaluated_at == status_valid_until`, proving the empty interval is immediately expired.

### Recorded-state preservation

- within-window and expired outcomes for all three recorded dispositions;
- blocking and indeterminate category tuples remain byte-for-byte unchanged;
- expiry does not rewrite category claims or effects;
- a future-usable but historically unrelied Observation is never dynamically selected; and
- no automatic newer head, branch winner or successor discovery occurs.

### Replay and error precedence

- the exact complete thirteen-input Slice 4 invocation occurs once after `as_of` validation;
- malformed `as_of` prevents Slice 4 from running;
- canonical `as_of` plus a lower-layer failure returns `RECORD_JOINT_REPLAY_FAILED` before any
  pre-evaluation comparison;
- every Slice 4 outer code is preserved, with reachable Slice 3 and Slice 2 nested codes;
- unrelated lower-layer Runtime failures propagate unchanged; and
- impossible anchor/result mismatches fail as `INTERNAL_RESULT_INCONSISTENCY`.

### Result, digest and provenance

- exact Result fields, literals, strict scalar types and frozen behavior;
- independent golden calculation of `decision_sha256` and `as_of_assessment_sha256`;
- field sensitivity for every assessment-digest projection member;
- stable output across repeated processes and identical explicit inputs;
- a one-second endpoint crossing changes the explicit `as_of`, expected window state and digest,
  while every upstream and recorded Decision projection remains unchanged;
- direct construction, reconstruction, replacement, copy and pickle paths cannot acquire valid
  process provenance; and
- limitations, zero-authority fields and the two consistency booleans cannot drift.

### Compatibility and static safety

- all Slice 1 through Slice 4 focused tests remain passing;
- `sdc.schemas.MODELS` remains exactly 67 and contains only the existing five Fresh Status
  persistent models;
- every committed Schema byte remains unchanged;
- AST checks reject filesystem, path, CLI, implicit-clock, environment, network, Provider,
  persistence, credential and execution surfaces; and
- complete offline `make check` passes in a fresh LF-preserving isolated worktree using synthetic
  data only.

## Seven mandatory limitations

Every successful Result retains this exact ordered tuple:

```text
SOURCE_AUTHENTICITY_NOT_PROVEN
SOURCE_COMPLETENESS_NOT_PROVEN
CHAIN_COMPLETENESS_NOT_PROVEN
REALITY_CURRENTNESS_NOT_PROVEN
SCOPE_LIMITED_TO_DECLARED_SUBJECT
TIME_WINDOW_LIMITED
LEGAL_EFFECT_NOT_DETERMINED
```

`WITHIN_EXPLICIT_BOUND_WINDOW` does not remove
`REALITY_CURRENTNESS_NOT_PROVEN`: it assesses only a recorded interval against an explicit caller
instant. `EXPIRED_NOT_CURRENT` likewise proves no adverse real-world fact; it says only that the
instant is at or beyond the recorded exclusive horizon.

## Zero-authority boundary

Every successful Result retains:

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

Neither window state, any recorded disposition, either consistency flag, the assessment digest nor
process provenance changes this boundary.

## Non-proofs and deferred work

Slice 5 does not prove:

- that `as_of` is the real present time or came from an authentic clock;
- that the supplied finite evidence and chain set is globally complete;
- that no hidden branch, newer event, replacement, revocation or late observation exists;
- source, identity or statement authenticity, statement truth or legal validity;
- present-day rights, policy, pricing, terms, availability, acceptance or capability;
- that a no-blocking recorded disposition is clearance, safety or permission; or
- that any Provider, generation, execution, publication or other action may proceed.

Also deferred are trusted-local readers, authoring preparers, paths, CLI surfaces, create-new
finalizers, persistent assessment receipts, Schema, rollback, quarantine, network, Provider
adapters, credentials, entitlements and execution. Each later layer needs separate detailed
design, synthetic validation and explicit approval. A successful Slice 5 process Result is not
advance approval for any of them.

## Consequences

Positive consequences:

- one fresh call now binds complete closure replay, explicit source-chain coverage and an exact
  caller-supplied assessment second;
- the inclusive/exclusive boundary and immediate-expiry case are deterministic;
- expiry remains separate from the historical Decision disposition;
- malformed time, replay failure, pre-evaluation time and internal inconsistency have stable,
  ordered failure meanings; and
- currentness overclaim, implicit clocks and detached-Result reuse remain structurally blocked.

Costs and limits:

- callers must resupply all complete Slice 4 inputs for every assessment;
- callers remain responsible for selecting and explicitly supplying `as_of`;
- the Result is intentionally non-persistent and cannot serve as an audit receipt; and
- assessing a later instant does not incorporate later evidence. A new source fact requires a new
  reviewed evidence chain and Record under separately approved work.
