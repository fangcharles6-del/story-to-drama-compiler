# SDC-ADR-036: Fresh Status Record As-Of Assessment Receipt v3.0

- Status: Accepted
- Date: 2026-08-25
- Depends on: SDC-ADR-031 / Fresh Status Evidence v3.0 Slice 1
- Depends on: SDC-ADR-032 / Explicit Finite Fresh Status Source-Chain Replay v3.0 Slice 2
- Depends on: SDC-ADR-033 / Fresh Status Evidence Record Chain Coverage v3.0 Slice 3
- Depends on: SDC-ADR-034 / Fresh Status Evidence Record Joint Replay v3.0 Slice 4
- Depends on: SDC-ADR-035 / Fresh Status Evidence Record As-Of Assessment v3.0 Slice 5
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: explicit synthetic in-memory immutable models and one explicit UTC second only

## Context

Slice 1 defines the immutable Fresh Status Evidence Record and its Request, Instruction and
Decision. Slices 2 through 4 freshly replay one explicitly supplied finite chain collection and
the complete Frozen Pack through Use Scope Review closure. Slice 5 freshly invokes Slice 4 and
deterministically assesses the verified Record at one exact caller-supplied `as_of` second.

The Slice 5 Result is deliberately process-local. Reconstructing it from a dump, accepting a
detached Result or serializing it as though it were a durable audit fact would discard the
private same-call provenance that distinguishes a successful assessment invocation from an
arbitrary model value. A durable historical record therefore cannot be produced by merely
copying a detached Slice 5 Result.

Slice 6 closes only that persistence-contract gap. It defines one immutable Receipt whose builder
freshly runs the complete Slice 5 assessment in the same call and whose verifier freshly rebuilds
the same Receipt from the complete upstream closure. It does not add a file reader, path, writer,
finalizer, implicit clock, currentness oracle, Provider integration or execution authority.

## Decision

Add one pure in-memory v3.0 module:

```text
src/sdc/real_asset_fresh_status_record_as_of_assessment_receipt_v30.py
```

The module defines one persistent immutable contract:

```text
CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
```

and exactly two public operations:

```text
build_fresh_status_record_as_of_assessment_receipt_v1
verify_fresh_status_record_as_of_assessment_receipt_closure_v1
```

Both operations invoke the public Slice 5 assessor exactly once per call. Neither operation
accepts a detached Slice 2, Slice 3, Slice 4 or Slice 5 Result. The verifier obtains its only
assessment instant from the strictly admitted `receipt.as_of`; it accepts no second `as_of`.

The Receipt is a deterministic historical statement about exact supplied bytes and one explicit
instant. It is not evidence that the instant is the real present, that the finite closure is
globally complete, that no hidden branch exists, that a source is authentic, that a statement is
true, that rights remain current, that a Provider is available or that an action is authorized.

## Applicability and complete required inputs

Slice 6 applies only to the complete Use Scope Review profile admitted by Slices 4 and 5. The
builder requires every one of these keyword-only inputs:

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

The verifier requires the same first thirteen object/chain inputs plus one exact
`CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1`. It does not accept a separate
`as_of`; after strict Receipt admission it uses only `receipt.as_of` for the fresh Slice 5 call.

Every input is mandatory. Slice 6 has no partial-closure mode and is not applicable to an
asset-admission-only flow, a flow without a Use Plan, a flow without a completed Use Scope Review
Record, a detached Decision or a subset of the Request targets. A future partial-flow profile
requires a separately named contract, API, design and approval.

Business tests and examples use synthetic in-memory objects only. Static compatibility checks may
read tracked source and Schema bytes but do not read private business material.

## Frozen compatibility boundary

Slice 6 must not change:

- any Slice 1 through Slice 5 public contract, API, error order, digest, provenance or policy;
- the Slice 1 evidence policy version or policy-document SHA-256;
- the Slice 5 assessment digest domain or projection;
- any Frozen Pack, Rights Evidence, Review, Qualification, Rights Manifest, Use Plan or Use Scope
  Review contract;
- any existing committed Schema byte; or
- any trusted-local reader, writer, finalizer, rollback, quarantine or authority state.

Slice 6 adds one registry entry and one committed Schema for the Receipt. The Schema registry
moves from exactly 67 models to exactly 68. The process-local Results from Slices 2 through 5
remain absent from `sdc.schemas.MODELS` and continue to have no committed Schema.

## Frozen profile, contract and public surface

The exact Receipt profile is:

```text
creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1
```

The exact document type is:

```text
sdc.creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1
```

The exact public surface is:

```text
FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_V1_PROFILE
FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
FreshStatusRecordAsOfAssessmentReceiptErrorCodeV1
CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error
build_fresh_status_record_as_of_assessment_receipt_v1
verify_fresh_status_record_as_of_assessment_receipt_closure_v1
```

The maximum canonical Receipt size is exactly:

```text
65536 bytes
```

The Receipt model is strict, frozen, extra-forbid and revalidates instances. Its envelope is:

```text
schema_version=1.0.0
document_type=sdc.creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1
profile=creative-sample-real-asset-fresh-status-record-as-of-assessment-receipt-v1
receipt_id=real_asset_fresh_status_record_as_of_assessment_receipt_v1_<20 lowercase hex>
receipt_purpose=HISTORICAL_EXPLICIT_AS_OF_ASSESSMENT_ONLY
reliance_requirement=FULL_CLOSURE_AND_EXPLICIT_AS_OF_REPLAY_REQUIRED
present_currentness_asserted=false
```

The Receipt has no Receipt-specific policy ID, version or policy-document digest. It retains the
exact source evidence policy bindings copied from the freshly produced Slice 5 Result.

## Exact Receipt projection

The complete public field projection is:

```text
schema_version
document_type
profile
receipt_id
receipt_purpose
reliance_requirement
present_currentness_asserted
source_assessment_result_type
source_assessment_status
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
as_of_assessment_sha256
provided_record_joint_replay_consistent=true
explicit_as_of_window_assessment_consistent=true
limitation_codes
status=FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_RECORDED
the complete forced zero-authority field set
```

The two source fields freeze these exact Slice 5 literals:

```text
source_assessment_result_type=FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_RESULT_V1
source_assessment_status=FRESH_STATUS_EVIDENCE_RECORD_AS_OF_ASSESSMENT_COMPLETED
```

The Receipt does not embed the full Record, Request, Decision, Observation documents, chain
inputs, Slice 4 Result, Slice 5 Result or any private process provenance. It contains no
Receipt-document SHA-256, self-digest, file path, filename, URL, credential, identity secret,
authorization token, execution handle or Provider data.

## Stable ID and canonical document

`receipt_id` is derived exactly as:

```python
stable_id(
    "real_asset_fresh_status_record_as_of_assessment_receipt_v1",
    receipt.model_dump(mode="json", exclude={"receipt_id"}),
)
```

The ID therefore binds every other Receipt field, including the source anchors, explicit
`as_of`, Slice 5 assessment digest, limitations, status and zero-authority declarations. There is
no circular self-hash. Any change outside `receipt_id` requires a different valid ID.

The canonical Receipt document is the complete JSON-mode model projection serialized with:

```text
UTF-8 without BOM
sort_keys=true
indent=2
ensure_ascii=false
allow_nan=false
exactly one trailing LF
```

Keys are sorted recursively by the JSON serializer. Arrays preserve their frozen tuple order.
Duplicate keys, unknown fields, non-JSON scalar substitutions and NaN/Infinity are not admitted.
The builder and verifier require strict model revalidation, stable canonical bytes and a canonical
size not greater than 65,536 bytes.

The Receipt intentionally reuses the existing `as_of_assessment_sha256` exactly as produced by
Slice 5. Slice 6 independently recomputes that frozen Slice 5 digest from the Receipt projection;
it does not call a private Slice 5 helper and does not introduce a second assessment digest.

## Builder API and fixed order

The builder is:

```python
build_fresh_status_record_as_of_assessment_receipt_v1(
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
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
```

It performs these phases in this exact order:

1. call the public `assess_fresh_status_evidence_record_as_of_v1` exactly once with the exact
   fourteen supplied values;
2. preserve a Slice 5 domain failure and its complete nested error-code chain;
3. accept only the live, exact Slice 5 Result type returned by that call;
4. check the Result profile, status, Record/Request/Decision anchors, joint replay digest,
   assessment digest, time state, limitation tuple and zero-authority values;
5. construct the Receipt projection from that live Result without accepting caller replacements;
6. derive `receipt_id`, strictly validate the Receipt, independently recompute the Slice 5 digest,
   recheck canonical stability and enforce the 65,536-byte limit; and
7. return the immutable Receipt.

The builder never calls Slice 4 directly and never substitutes a private or copied Slice 5
Result. A malformed `as_of` remains governed by Slice 5's existing admission and ordering.

## Verifier API and fixed order

The verifier is:

```python
verify_fresh_status_record_as_of_assessment_receipt_closure_v1(
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
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
```

It performs these phases in this exact order:

1. require the exact Receipt model type and strictly reconstruct it from its complete Python-mode
   projection;
2. require unchanged canonical bytes, valid ID, independent assessment digest, fixed limitations,
   zero authority and the canonical size limit;
3. read the one allowed assessment instant from the strictly admitted `receipt.as_of`;
4. call the public Slice 5 assessor exactly once with the exact thirteen supplied closure values
   and that `receipt.as_of`;
5. preserve any Slice 5 domain failure and its complete nested error-code chain;
6. compile one expected Receipt internally from the live Result without calling the public builder
   and therefore without performing a second Slice 5 call;
7. require exact model equality and exact canonical-byte equality between the supplied and expected
   Receipts; and
8. return the strictly revalidated supplied Receipt without changing it.

Receipt contract failure occurs before Slice 5 is called. After Receipt admission, the complete
fresh assessment replay occurs before any expected-Receipt mismatch conclusion. Verification does
not select another Record, chain collection or `as_of`, and it does not repair the Receipt.

## Historical time semantics

The Receipt freezes the exact caller-supplied UTC second already admitted by Slice 5. There is no
default, normalization or fallback. The assessment interval remains:

```text
[evaluated_at, status_valid_until)
```

The fixed mapping remains:

| Condition | Receipt state |
| --- | --- |
| `as_of < evaluated_at` | Slice 5 failure; no Receipt |
| `evaluated_at <= as_of < status_valid_until` | `WITHIN_EXPLICIT_BOUND_WINDOW` |
| `as_of >= status_valid_until` | `EXPIRED_NOT_CURRENT` |

The lower endpoint is inclusive and the upper endpoint exclusive. If
`evaluated_at == status_valid_until`, the interval is empty and equality is
`EXPIRED_NOT_CURRENT`.

No `created_at`, `issued_at`, `verified_at`, wall time, verification time or second validity
window is added. Re-verification always replays the Receipt's historical `as_of`; it does not
refresh the Receipt against the real present. A later explicit `as_of` requires building a
different Receipt. Multiple Receipts are not automatically ordered and do not form a previous/
next evidence chain in this slice.

## Fixed outer error model

The exact stable outer error order is:

```text
RECEIPT_CONTRACT_INVALID
AS_OF_ASSESSMENT_REPLAY_FAILED
ASSESSMENT_RESULT_INCONSISTENT
INTERNAL_RECEIPT_INCONSISTENCY
RECEIPT_REPLAY_MISMATCH
```

The error object contains its outer `code` and these optional nested fields:

```text
assessment_code
joint_replay_code
coverage_code
replay_code
```

Rules:

- verifier Receipt type, strict-contract, ID, digest, canonical or size failure becomes
  `RECEIPT_CONTRACT_INVALID` before Slice 5 runs;
- a Slice 5 domain failure becomes `AS_OF_ASSESSMENT_REPLAY_FAILED`, preserving the exact Slice 5,
  Slice 4, Slice 3 and Slice 2 codes without parsing message text;
- a live Slice 5 return with an impossible type, provenance, profile, anchor, digest, state,
  limitation or authority projection becomes `ASSESSMENT_RESULT_INCONSISTENT`;
- a Receipt that cannot be consistently derived, strictly validated, independently checked or
  canonically bounded from a valid live Result becomes `INTERNAL_RECEIPT_INCONSISTENCY`;
- only after a valid supplied Receipt and successful fresh Slice 5 replay may an exact supplied/
  expected Receipt difference become `RECEIPT_REPLAY_MISMATCH`;
- builder construction defects cannot be misreported as caller Receipt admission failures;
- unrelated `RuntimeError`, `MemoryError`, process interruption and other non-domain failures are
  not reclassified; and
- no failure is retried, repaired, persisted, rolled back or quarantined.

This order makes a malformed supplied Receipt win over a simultaneous damaged upstream closure.
Once the Receipt is admitted, a Slice 5 replay failure wins over an expected-Receipt mismatch.

## Seven mandatory limitations

Every Receipt contains this exact ordered tuple:

```text
SOURCE_AUTHENTICITY_NOT_PROVEN
SOURCE_COMPLETENESS_NOT_PROVEN
CHAIN_COMPLETENESS_NOT_PROVEN
REALITY_CURRENTNESS_NOT_PROVEN
SCOPE_LIMITED_TO_DECLARED_SUBJECT
TIME_WINDOW_LIMITED
LEGAL_EFFECT_NOT_DETERMINED
```

Neither successful construction nor successful historical verification removes or reorders a
limitation. `WITHIN_EXPLICIT_BOUND_WINDOW` does not remove
`REALITY_CURRENTNESS_NOT_PROVEN`. `EXPIRED_NOT_CURRENT` proves no adverse real-world fact.

## Zero-authority boundary

Every Receipt contains exactly:

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

These are immutable contract fields and stable-ID inputs, not comments. No profile, ID, digest,
window state, recorded disposition, builder success, verifier success or Schema admission changes
the authority boundary.

## Pure-memory static boundary

The production module is limited to deterministic hashing, canonical JSON, strict Pydantic
validation, deterministic parsing/comparison of explicit UTC strings and one call to the public
Slice 5 API. It must not import or call:

- `os`, `pathlib`, `subprocess`, `shutil`, `tempfile`, `glob` or filesystem APIs;
- `time`, `datetime.now`, `datetime.utcnow`, `date.today` or any implicit clock;
- environment access, sockets, HTTP clients, URLs, browsers or network discovery;
- Provider/Runtime adapters, credentials, Keys, tokens, entitlements or authorization stores;
- database, queue, worker, ledger, cache or persistent result APIs;
- reader, parser, extractor, writer, finalizer, rollback or quarantine APIs; or
- generation, execution, publication, purchase, contact, upload, retention or training APIs.

Deterministic `datetime.strptime` and `UTC` use is allowed only for validating or comparing the
explicit strings already present in the supplied models. The module has no import-time side
effect, `__main__` branch or CLI surface.

## Synthetic verification matrix

The Slice 6 suite must cover at least:

### Applicability and API

- exact keyword-only signatures and complete required input sets;
- omission of each required input at the Python call boundary;
- no detached Result parameter and no second verifier `as_of`;
- one and only one public Slice 5 call from each operation; and
- proof that verifier contract rejection causes zero Slice 5 calls.

### Contract, ID and canonical form

- strict scalar types, extra-field rejection and frozen behavior;
- the exact envelope, purpose, reliance and currentness literals;
- stable-ID golden value and sensitivity to every non-ID field;
- independent Slice 5 assessment-digest golden and field sensitivity;
- recursive sorted-key canonical JSON, non-ASCII handling and exactly one trailing LF;
- repeatable bytes and ID across independent reconstructions from the same explicit inputs; and
- the exact 65,536-byte limit constant plus the bounded rejection path. Because every Receipt
  field is already structurally bounded, tests must not add an artificial production field merely
  to manufacture an otherwise unreachable exact-boundary document.

### Same-call assessment and historical replay

- live Slice 5 Result consumption without a detached reconstruction path;
- exact forwarding of every upstream object, chain tuple and builder `as_of`;
- verifier use of only `receipt.as_of`;
- half-open lower, upper and empty-window boundaries;
- both window states with all three recorded Decision dispositions; and
- preservation of Record/Request/Decision, coverage, joint replay and assessment anchors.

### Error ordering and tamper resistance

- every outer Receipt error code in its fixed order;
- every reachable Slice 5, Slice 4, Slice 3 and Slice 2 nested code;
- exact `__cause__` preservation without exception-text parsing;
- malformed Receipt plus invalid closure, valid Receipt plus invalid closure, and successful replay
  plus Receipt mismatch precedence;
- mutation of every Receipt field, including recomputed-ID attempts;
- cross-Receipt splicing of Record, Request, Decision, closure, digest, time and status fields; and
- no catch/reclassification of unrelated runtime or process failures.

### Compatibility, Schema and static safety

- exactly 68 registered models after adding only the Receipt;
- exactly one new Receipt Schema and byte-for-byte preservation of all prior 67 Schemas;
- no registration of Slice 2 through Slice 5 process Results;
- Slice 1 through Slice 5 focused regression suites;
- AST rejection of filesystem, path, CLI, environment, implicit-time, network, Provider,
  persistence, credential and execution surfaces; and
- complete offline `make check` after exact diff and Schema checks, using synthetic data only.

## Permitted claims and explicit non-proofs

After builder success, the strongest permitted statement is:

> For the exact supplied complete upstream closure, explicit finite chain tuple and explicit
> `as_of`, a same-call public Slice 5 assessment succeeded and this immutable Receipt
> deterministically records that historical assessment projection.

After verifier success, the strongest permitted statement is:

> For the exact supplied complete upstream closure and this Receipt's exact historical `as_of`, a
> fresh public Slice 5 assessment rebuilt a Receipt with exactly identical canonical content.

Neither statement proves:

- that `as_of` is the real present or came from an authentic clock;
- that the supplied sources, identities, statements or evidence are authentic or true;
- that the supplied finite set is globally complete or that no hidden/newer branch exists;
- present-day rights, revocation status, policy, terms, pricing, capability or availability;
- legal effect, clearance, safety, acceptance or fitness for a purpose;
- Provider readiness, credential validity or operational capability; or
- permission to access, generate, execute, publish, purchase, contact, upload, retain, train or
  perform remote processing.

## Deferred work

Trusted-local readers, JSON/bytes parsers, extractors, path handling, directory handling, CLI,
create-new writers and finalizers, external full-document hashing, rollback, quarantine, Receipt
history chaining, automatic latest selection, currentness renewal, network, Provider adapters,
credentials, entitlements and execution remain separate future designs. Each needs its own
detailed design, synthetic validation and explicit approval.

The presence of a committed Schema means only that the Receipt's structure is registered. It does
not authorize reading, writing or verifying a filesystem document and is not advance approval for
any deferred boundary.

## Consequences

Positive consequences:

- a durable immutable contract can record one exact same-call Slice 5 historical assessment;
- detached process Results cannot substitute for fresh complete replay;
- the Receipt binds all Record/Request/Decision, closure, replay, time, limitation and authority
  projections under one deterministic stable ID;
- historical verification has an exact whole-document equality rule; and
- Schema and static locks make the persistence contract reviewable without adding I/O.

Costs and limits:

- every build and verification call must resupply the complete closure and chain tuple;
- every call performs a fresh full Slice 5 replay;
- verifier success is historical closure consistency, not present currentness;
- there is no file operation or operational finalization workflow in this slice; and
- new evidence or a later explicit instant requires a new upstream assessment and Receipt rather
  than mutation of an existing Receipt.
