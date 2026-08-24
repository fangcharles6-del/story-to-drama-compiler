# SDC-ADR-034: Fresh Status Evidence Record Joint Replay v3.0

- Status: Accepted; synthetic implementation only
- Date: 2026-08-24
- Depends on: SDC-ADR-031 / Fresh Status Evidence v3.0 Slice 1
- Depends on: SDC-ADR-032 / Explicit Finite Fresh Status Source-Chain Replay v3.0 Slice 2
- Depends on: SDC-ADR-033 / Fresh Status Evidence Record Chain Coverage v3.0 Slice 3
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: explicit synthetic in-memory model objects only

## Context

Slice 1 can replay one Fresh Status Evidence Record against the complete, explicitly supplied
Frozen Pack through Use Scope Review object closure and the exact Source Observation documents
referenced by its Request. Slice 2 can replay one explicitly supplied finite logical source chain.
Slice 3 can prove that every Request Observation is targeted exactly once by an explicitly supplied
collection of such chains, that each chain contains only its targets and their supplied ancestors,
and that the target documents rebuild the same Record.

Those APIs intentionally remain separate. A caller can invoke Slice 1 with one object collection
and invoke Slice 3 with another collection, at another point in the process, then accidentally
present the two detached successes as though they were one atomic replay. A serialized or directly
constructed Slice 3 Result is also not a valid substitute for fresh replay, but the application
boundary still needs one narrow call that makes the intended composition unambiguous.

Slice 4 closes only that composition gap. It does not add a new persistent contract, discover an
upstream object, infer a source chain, assess reality currentness or authorize a later action.

## Decision

Add one pure in-memory v3.0 module that jointly performs, in a fixed order, the public Slice 3
Record chain-coverage replay and the public Slice 1 complete object-closure replay for the same
immutable Evidence Record.

The verifier accepts all eleven upstream objects required by the existing complete Use Scope
Review closure, the exact Evidence Record, and the explicit Slice 3 chain inputs. It freshly calls
the public lower-layer verifiers. It never accepts detached Slice 1, Slice 2, Slice 3 or Slice 4
Results.

The exact Request target Observation tuple supplied to Slice 1 is derived only from the same chain
inputs that just passed Slice 3. The API has no independent `observations` argument. This prevents
the caller from proving chain coverage with one target-document set and proving upstream closure
with another.

On success the verifier returns one strict, frozen, non-persistent
`FreshStatusEvidenceRecordJointReplayResultV1`. Success permits only these narrow statements:

```text
provided_upstream_object_closure_consistent=true
provided_evidence_record_request_explicit_chain_coverage_consistent=true
provided_evidence_record_rebuild_consistent=true
```

No success statement contains `global`, `complete`, `current`, `authentic`, `valid for use` or an
equivalent expansion beyond the explicitly supplied finite objects.

## Applicability and complete required object set

Slice 4 applies only to a Fresh Status Evidence Record whose subject has already reached the full
Use Scope Review stage. These eleven keyword-only upstream objects are all required:

| Parameter | Required immutable object |
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

They are followed by the required `record` and `chains` arguments. None has a default, accepts
`None`, represents an optional stage or permits a placeholder. Omission fails at Python keyword
binding before any verifier operation. A present but wrong, incomplete or drifted object fails
closed at its fixed replay stage.

This profile is not applicable to asset-admission-only flows, subjects without a Use Plan, subjects
without a completed Use Scope Review Record or any other partial closure. A future partial-flow
need requires a separately named profile and API; Slice 4 must not be widened with optional
parameters.

The complete supported business chain is:

```text
Frozen Pack
-> Rights Evidence
-> Reviewer A / Reviewer B
-> Pair Check
-> Qualification Request / Instruction / Decision
-> Rights Manifest
-> Use Plan
-> Use Scope Review Record
-> Fresh Status Evidence Record
-> explicit finite logical source-chain inputs
```

## Frozen compatibility boundary

Slice 4 must not change:

- any persistent model from Slice 1 or its five committed Schema files;
- the 67-entry Schema registry;
- the Slice 1 evidence profile, policy version, policy SHA-256, canonical-document rules,
  stable-ID projections, source-chain rules or Record projections;
- the Slice 2 replay profile, resource bounds, graph invariants, error order, digest projection or
  process-local provenance;
- the Slice 3 coverage profile, resource bounds, 22-code error order, coverage-set digest,
  Result projection or process-local provenance;
- any Frozen Pack, Rights Evidence, Review, Qualification, Rights Manifest, Use Plan or Use Scope
  Review contract; or
- any existing filesystem finalizer, trusted-local boundary or authority state.

Slice 4 adds no persistent model and is absent from `sdc.schemas.MODELS`. Its process Result has no
JSON parser, document builder, Schema registration or supported serialization round trip.

## Frozen profile and public API

The joint-replay profile is:

```text
FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE
= creative-sample-real-asset-fresh-status-record-joint-replay-v1
```

The public surface is limited to:

```text
FRESH_STATUS_RECORD_JOINT_REPLAY_V1_PROFILE
FreshStatusRecordJointReplayErrorCodeV1
RealAssetFreshStatusRecordJointReplayV30Error
FreshStatusEvidenceRecordJointReplayResultV1
verify_fresh_status_evidence_record_joint_replay_v1
```

The only operation is:

```python
verify_fresh_status_evidence_record_joint_replay_v1(
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
) -> FreshStatusEvidenceRecordJointReplayResultV1
```

The operation accepts only already constructed in-memory models. It accepts no dict, bytes,
string document, stream, path, directory, CLI namespace, `as_of`, implicit clock, callback,
detached verification Result, Provider handle, Runtime handle, entitlement or credential.

## Fixed joint replay order

The verifier performs the following phases in this exact order:

1. invoke `verify_fresh_status_evidence_record_explicit_chain_coverage_v1` with the exact supplied
   `record` and `chains`;
2. accept only the freshly returned, provenance-bearing Slice 3 Result;
3. derive the exact Request target Source Observation tuple from the same admitted `chains`;
4. invoke `verify_fresh_status_evidence_record_closure_v1` with all eleven upstream objects, the
   derived target tuple and the same exact `record`;
5. compare the successful Slice 1 replay with the successful Slice 3 anchors; and
6. derive and construct the minimal Slice 4 Result under private process-local provenance.

Slice 4 must not pre-validate or reorder lower-layer failures in a way that changes Slice 3's
frozen admission sequence. No upstream closure work is performed if Slice 3 fails. No Result is
constructed if any phase fails.

## Exact target Observation derivation

For target selection, a Source Observation is identified by the full five-field reference:

```text
observation_id
observation_sha256
status_category
source_identity_ref_sha256
chain_sha256
```

After Slice 3 succeeds, the implementation derives the canonical reference for every supplied
Observation from its exact immutable document and source-chain fields. It then resolves each
canonically ordered `coverage.request_observation_refs` entry from that freshly returned Slice 3
Result to exactly one supplied Source Observation with equal values in all five fields. It does not
reselect the target set from the caller's Record after coverage replay.

The derivation requires:

- every Request reference resolves exactly once;
- no independently selected or inferred Observation is admitted;
- no tuple position, filename, timestamp, terminal status or favorable claim selects a target;
- non-target supporting ancestors are excluded from the Slice 1 `observations` tuple; and
- the derived tuple uses the fresh Slice 3 canonical Request-reference order, after which Slice 1
  independently revalidates and canonicalizes the exact target documents.

The earlier successful Slice 3 replay already proves exact target coverage, cross-chain uniqueness
and target resolution. Slice 4 repeats only the small pure derivation needed to avoid trusting a
detached Result or a second observations argument. Failure here is a defensive internal
inconsistency, not a recoverable invitation to infer another target.

## Fixed outer error model

The outer error codes run in this exact order:

```text
RECORD_CHAIN_COVERAGE_REPLAY_FAILED
TARGET_OBSERVATION_DERIVATION_INCONSISTENT
PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED
INTERNAL_RESULT_INCONSISTENCY
```

`RealAssetFreshStatusRecordJointReplayV30Error` exposes:

```text
code: FreshStatusRecordJointReplayErrorCodeV1
coverage_code: FreshStatusRecordChainCoverageErrorCodeV1 | None
replay_code: FreshStatusChainReplayErrorCodeV1 | None
```

Rules:

- a Slice 3 domain failure becomes `RECORD_CHAIN_COVERAGE_REPLAY_FAILED` and preserves the exact
  nested `coverage_code`;
- when that Slice 3 code is `CHAIN_REPLAY_FAILED`, the optional Slice 2 `replay_code` is also
  preserved unchanged;
- target derivation failure becomes `TARGET_OBSERVATION_DERIVATION_INCONSISTENT`;
- any supported Slice 1/upstream contract or closure failure becomes
  `PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED` and retains the original exception as `__cause__`;
- Slice 1 free-form exception text is never parsed into a fabricated stable code;
- an unrelated `RuntimeError` or other non-contract implementation failure is not reclassified as
  a closure-domain failure and propagates unchanged;
- an impossible mismatch while deriving the final Result becomes
  `INTERNAL_RESULT_INCONSISTENCY`; and
- `MemoryError`, process interruption and other non-contract failures are not converted into a
  successful or partial domain result.

The verifier does not retry, repair, reconcile, overwrite, roll back or quarantine. Because it has
no write surface, a failure leaves no Slice 4 artifact to clean up.

## Minimal outer process Result

`FreshStatusEvidenceRecordJointReplayResultV1` is strict, frozen,
`extra=forbid`, recursively revalidated and process-local. It contains exactly the joint binding
rather than embedding a detached Slice 3 Result:

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

The Result must retain these equations from the freshly verified Slice 3 Result:

```text
request_observation_count == covered_request_observation_count

provided_observation_count
== covered_request_observation_count
 + supporting_ancestor_observation_count
```

`chain_count` remains within the frozen Slice 3 1..32 bound. The evidence Record, Request and
subject-closure anchors must equal both successful lower-layer results exactly.

The Result intentionally does not duplicate complete Request-reference or per-chain-summary
collections. `evidence_record_sha256` binds the immutable Record, while the freshly recomputed
`coverage_set_sha256` binds the complete Slice 3 coverage projection. This keeps Slice 4 a minimal
composition proof rather than a second coverage receipt.

## Joint replay digest and canonical JSON

The deterministic handle is:

```text
SHA256(
  "sdc:creative-sample-real-asset-fresh-status-record-joint-replay-set:v1\0"
  || canonical_compact_json(frozen_projection)
)
```

The frozen projection contains:

```text
joint_replay_profile
source_record_chain_coverage_profile
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
chain_count
covered_request_observation_count
provided_observation_count
supporting_ancestor_observation_count
coverage_set_sha256
```

`canonical_compact_json` is fixed as follows:

- recursively sort every JSON object key by the serializer's deterministic lexicographic key
  order (`sort_keys=True`);
- encode as UTF-8 with `ensure_ascii=False`;
- use exact separators `(",", ":")`;
- produce no BOM, indentation, insignificant whitespace or trailing newline;
- reject `NaN`, positive/negative infinity and every other non-finite number;
- preserve the exact contract-defined order of arrays and tuples; and
- preserve JSON booleans and integers as their exact scalar types.

No implementation may depend on Pydantic field declaration order, Python dict insertion order or
caller tuple order where the lower-layer contract specifies canonical sorting. Manual field-string
concatenation is forbidden. The projection field set, profile and domain cannot change in place;
a semantic change requires a new version and domain.

The projection excludes `joint_replay_sha256` itself, the three fixed consistency booleans,
limitation codes, status and zero-authority fields. Private Result provenance binds all public
fields, including the fixed excluded fields.

## Process-local provenance

Only the Result returned directly by the complete joint verifier has accepted process-local
provenance. The private provenance digest uses:

```text
sdc:creative-sample-real-asset-fresh-status-record-joint-replay-provenance:v1\0
```

and canonical compact JSON over every public Result field.

The Result validator requires a private construction context and records a private sentinel plus
the provenance digest. Before return, the verifier checks that private state and the complete
public projection still match.

The following are invalid:

- direct Result construction;
- ordinary `model_validate` without the private verifier context;
- JSON or Python dump/reload;
- `model_construct`;
- a modified `model_copy`; and
- treating a cross-process Result value as a persistent proof.

This guard reduces ordinary accidental composition and mutation. It is not a signature,
attestation, credential, authorization token or defense against deliberate Python reflection or
memory modification.

## Pure-memory static boundary

The production module is constrained by both an import allowlist and an AST denylist.

Permitted standard-library dependencies are limited to the pure deterministic facilities needed
for canonical projection and typing, principally:

```text
hashlib
json
typing
```

Permitted non-standard imports are Pydantic, the exact existing immutable upstream object types,
and the approved public Slice 1 and Slice 3 symbols required by the API and joint replay. Dynamic
imports are forbidden.

AST tests must reject direct or aliased import or use of:

```text
os, pathlib, glob, shutil, tempfile
subprocess, sys.argv, argparse, click, typer
datetime, time
socket, urllib, http, requests, httpx
database, queue, worker, runtime and Provider adapters
keyring and credential helpers
open, input, eval, exec, compile, __import__
```

The guard explicitly rejects `datetime.now`, `datetime.utcnow`, `datetime.today`, `time.time`,
`os.getenv`, `Path`, `open` and every `subprocess` call. Equivalent aliases or attribute chains
must also fail. Ruff remains responsible for ordinary formatting and lint; AST tests enforce this
architectural boundary.

## Synthetic verification matrix

The implementation must cover at least:

1. one target/one chain, multiple targets/one chain, multiple chains, ancestor targets, branches
   and Reconciliation targets;
2. all eleven upstream objects correctly bound through one complete Use Scope Review closure;
3. one-at-a-time drift of every upstream object, with closure failure and no Result;
4. a Record/chains mismatch that stops at Slice 3 before any upstream closure call;
5. a chain-valid Record paired with a different upstream closure that stops only at Slice 1;
6. exact five-field target derivation, with defensive missing, duplicate and anchor-drift cases;
7. proof that supporting ancestors never enter Slice 1's target Observation tuple;
8. preservation of every Slice 3 `coverage_code` and every reachable nested Slice 2
   `replay_code`;
9. the fixed four-category outer error order and lower-layer call order;
10. deterministic equality under valid permutations of outer chains, targets and observations;
11. joint digest reproducibility, field sensitivity, canonical recursive key ordering and rejection
    of non-finite numbers;
12. strict/frozen Result validation and all process-local provenance misuse cases;
13. exact retention of all seven limitation codes and every false/zero authority scalar type;
14. AST import/call allowlist and denylist checks;
15. focused Slice 1, Slice 2 and Slice 3 regression tests;
16. `len(sdc.schemas.MODELS) == 67`, exactly five registered Fresh Status persistent models, no
    Slice 2/3/4 process Result in the registry and byte-identical committed Schemas; and
17. Ruff, strict Mypy and one complete offline `make check` in a fresh LF-preserving isolated
    worktree containing only the approved Slice 4 changes and no repository `output/` or `tmp/`.

All fixtures and temporary objects are synthetic. No test may call a paid or remote generation
service or read real intake, identity, evidence, output or temporary business material.

## Seven mandatory limitations

Every success retains exactly, in this order:

```text
SOURCE_AUTHENTICITY_NOT_PROVEN
SOURCE_COMPLETENESS_NOT_PROVEN
CHAIN_COMPLETENESS_NOT_PROVEN
REALITY_CURRENTNESS_NOT_PROVEN
SCOPE_LIMITED_TO_DECLARED_SUBJECT
TIME_WINDOW_LIMITED
LEGAL_EFFECT_NOT_DETERMINED
```

They mean that Slice 4 proves consistency only inside the exact provided finite object set. It does
not prove that a source, identity or statement is authentic; that all relevant objects, chains,
branches or events were supplied; that reality is current; or that any legal effect follows.

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

The false values must remain exact JSON booleans and the zero values exact JSON integers. A Slice 4
success is inert technical evidence. It grants no permission to access, upload, submit, retain,
train, process, generate, execute, publish, purchase or contact a Provider.

## Non-proofs and deferred work

Slice 4 does not prove:

- that the supplied finite set is globally complete;
- that no hidden branch, newer event, replacement document or revocation exists;
- source authenticity, identity authenticity, statement truth or legal validity;
- present-day rights, policy, price, terms, availability, acceptance or capability;
- that any Observation is current at an assessment instant; or
- that any Provider or execution action is permitted.

An explicit-`as_of` current-status assessor remains deferred to v3.0 Slice 5. Slice 5 must receive
an explicit caller-supplied timestamp and establish its own deterministic policy and error order;
it may not add an implicit clock to Slice 4.

Also deferred are authoring preparers, trusted-local paths and readers, CLI surfaces, create-new
finalizers, rollback, quarantine, persistent receipts, Schema, network, Provider adapters,
credentials, entitlements and execution. Each requires separate design and explicit approval.

## Consequences

The added API makes the intended Slice 1 plus Slice 3 composition one explicit, fail-closed
operation and prevents a second independent target Observation set. It also adds another narrow
verification layer and a deterministic process-only handle. The cost is deliberate duplication of
some anchor checks and a larger required call signature, which is appropriate because all eleven
upstream objects are necessary to prove the complete supported closure.

This decision does not authorize a commit, push, PR, merge, deployment, real-data operation or any
Provider action. Each later transition remains separately gated.
