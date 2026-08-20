# Creative Sample Real Asset Use Plan Consumer v2.6

## Purpose and stage boundary

This runbook specifies the pure in-memory v2.6 boundary defined by SDC-ADR-027. It covers:

1. deterministic construction and historical verification of one provider-neutral offline Use
   Plan from one complete verified Rights Manifest closure; and
2. deterministic construction and verification of one Maker/Checker Use Scope Review Record.

This is ADR release 1.0. The five top-level versioned artifact contracts use
`schema_version=1.0.0`; the consumers and
their two fixed policies use version `2.6.0`.

PR1 is synthetic-only and pure. It does not explain how to locate private files, authenticate a
person, create a real artifact, operate a UI or invoke a CLI. It has no trusted-local command,
output path, directory scan, network, clock, Provider or Runtime integration. Do not substitute
the current real private Pack, media, Evidence, Reviews, PairCheck, qualification records,
identity references or Manifest into development tests or manual experiments. Do not read or
write repository `output/` or `tmp/`.

A successful Use Plan or Review Record remains inert:

```text
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
eligible_for_separate_provider_approval=false
eligible_for_real_generation=false
execution_authorized=false
publication_authorized=false
posts_allowed=0
provider_requests=0
```

The strongest positive v2.6 result is eligibility to design a separate Provider proposal. It is
not permission to choose, contact or pay a Provider.

## Public contract and Schema surface

The v2.6 artifact surface contains exactly these five top-level versioned models and five
committed Schemas:

| Public model | Committed Schema | Artifact role |
|---|---|---|
| `CreativeSampleRealAssetUsePlanV1` | `CreativeSampleRealAssetUsePlanV1.schema.json` | One deterministic offline plan candidate. |
| `CreativeSampleRealAssetUseScopeReviewRequestV1` | `CreativeSampleRealAssetUseScopeReviewRequestV1.schema.json` | Maker-owned Request module. |
| `CreativeSampleRealAssetUseScopeReviewInstructionV1` | `CreativeSampleRealAssetUseScopeReviewInstructionV1.schema.json` | Checker-owned Instruction module. |
| `CreativeSampleRealAssetUseScopeReviewDecisionV1` | `CreativeSampleRealAssetUseScopeReviewDecisionV1.schema.json` | Compiler-derived Decision module. |
| `CreativeSampleRealAssetUseScopeReviewRecordV1` | `CreativeSampleRealAssetUseScopeReviewRecordV1.schema.json` | Single final Review artifact containing all three modules. |

Use bindings, closure bindings and gate-result models are helper definitions under `$defs`.
`ManifestClosureBindingV26`, `ProviderNeutralBaselineProjectionV26`, `MediaMappingV26` and
`UseScopeGateResultV1` are also public Python helper types, but they do not add top-level
committed Schemas. The Request, Instruction and Decision Schemas define
auditable module shapes; they do not authorize three separately persisted real files. A real use
scope review, if a future trusted-local design permits one, is represented by exactly one outer
Review Record artifact.

All 57 earlier committed Schemas remain normalized-LF byte-identical. PR1 adds exactly five and
brings the total to 62.

## Pure module boundary

The implementation is divided into:

```text
sdc.real_asset_use_plan_v26
sdc.real_asset_use_scope_review_v26
```

The Use Plan module exposes an immutable Plan model, its fixed policy constants, one fail-closed
error type and pure build, strict parse and historical closure-verification operations.

The Use Scope Review module exposes the Request, Instruction, Decision and Record models, its
fixed policy and time constants, one fail-closed error type and separate pure operations to:

- construct a Maker Request;
- construct a Checker Instruction bound to that immutable Request;
- deterministically finalize the Decision and complete Record;
- strictly parse the public models;
- historically verify the complete Record closure;
- extract each physical module and its standard canonical bytes; and
- assess temporal currency under the recorded contracts with an explicit `observed_at`.

The exact exported names in the implementation and `__all__` are normative. There is no
filesystem loader, path parameter, output parameter, CLI parser, `main`, `__main__` block,
environment-selected policy, clock default or automatic continuation.

The Use Plan module exports exactly:

```text
PROVIDER_NEUTRAL_BASELINE_SHA256
USE_PLAN_V1_POLICY_DOCUMENT_SHA256
USE_PLAN_V1_POLICY_ID
USE_PLAN_V1_POLICY_VERSION
USE_PLAN_V1_PROFILE
CreativeSampleRealAssetUsePlanV1
ManifestClosureBindingV26
MediaMappingV26
ProviderNeutralBaselineProjectionV26
RealAssetUsePlanV26Error
build_real_asset_use_plan_v1
parse_real_asset_use_plan_v1_json
verify_real_asset_use_plan_closure_v1
```

The Use Scope Review module exports exactly:

```text
REQUEST_VALIDITY_SECONDS
REVIEW_VALIDITY_SECONDS
USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256
USE_SCOPE_REVIEW_V1_POLICY_ID
USE_SCOPE_REVIEW_V1_POLICY_VERSION
USE_SCOPE_REVIEW_V1_PROFILE
CreativeSampleRealAssetUseScopeReviewDecisionV1
CreativeSampleRealAssetUseScopeReviewInstructionV1
CreativeSampleRealAssetUseScopeReviewRecordV1
CreativeSampleRealAssetUseScopeReviewRequestV1
RealAssetUseScopeReviewV26Error
UseScopeGateResultV1
build_use_scope_review_instruction_v1
build_use_scope_review_record_v1
build_use_scope_review_request_v1
compile_use_scope_review_decision_v1
extract_use_scope_decision_v1
extract_use_scope_instruction_v1
extract_use_scope_request_v1
parse_use_scope_review_decision_v1_json
parse_use_scope_review_instruction_v1_json
parse_use_scope_review_record_v1_json
parse_use_scope_review_request_v1_json
verify_use_scope_review_current_v1
verify_use_scope_review_record_closure_v1
verify_use_scope_review_record_internal_v1
```

The three human/compiler stages are separate calls. Their caller-supplied fields are exactly:

```text
build_use_scope_review_request_v1(
  use_plan, maker_identity_ref_sha256, requested_at, request_basis
)
build_use_scope_review_instruction_v1(
  request, checker_identity_ref_sha256, evaluated_at,
  gate_results, disposition, checker_basis
)
build_use_scope_review_record_v1(request, instruction)
```

Both full historical Review verification and temporal-current verification require the complete
nine-model closure, the exact Use Plan and the Review Record. The latter additionally requires
an explicit `observed_at`; it accepts no caller assertion for hold/revocation status.

## Complete nine-model input closure

Every accepted Use Plan is rooted in these nine exact models:

| Ordinal | Model | Required reconstruction |
|---:|---|---|
| 1 | `CreativeSampleFrozenRealAssetPackManifest` | Exact fourteen-object Pack, ordinals `0..13`, stable ID and canonical digest. |
| 2 | `CreativeSampleRealAssetRightsEvidenceBundleV2` | Exact Evidence bound to the Pack and its declared validity. |
| 3 | Reviewer A `CreativeSampleRealAssetHumanPackReviewV2` | Finalized Pack review with role A. |
| 4 | Reviewer B `CreativeSampleRealAssetHumanPackReviewV2` | Finalized Pack review with role B. |
| 5 | `CreativeSampleRealAssetReviewPairCheckV2` | Exact issue-free pair closure. |
| 6 | `CreativeSampleRealAssetQualificationRequestV2` | Exact deterministic qualification request. |
| 7 | `CreativeSampleRealAssetQualificationDecisionInstructionV22` | Exact retained Qualifier instruction. |
| 8 | `CreativeSampleRealAssetQualificationDecisionV2` | Exact positive scoped qualification Decision. |
| 9 | `CreativeSampleRealAssetRightsManifestV2` | Exact historical Manifest reconstructed from the first eight models. |

The builder and verifier receive all nine models explicitly. They do not accept a wrapper that
allows a missing member, a copied digest in place of a model or a Manifest as a bearer token.

The existing pure `verify_real_asset_rights_manifest_closure_v2` operation reconstructs the
historical closure at the Manifest's recorded `manifest_at`. The v2.6 consumer then recomputes the
standard canonical-document digest of each boundary and binds the exact results in the Plan.

The Manifest must contain:

```text
qualification_decision=PASS_ASSET_INTAKE_ONLY
qualification_scope=ASSET_INTAKE_ONLY
status=RIGHTS_MANIFEST_CREATED
rights_qualification_performed=true
rights_manifest_created=true
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

Any negative decision, unresolved issue, role alias, digest collision, stale identity, policy
drift, type coercion or non-zero authority value fails closed.

## Standard canonical document

Unless a policy-digest section explicitly says compact canonical JSON, “canonical document” means:

```text
UTF-8 without BOM
object keys sorted at every depth
two-space indentation
unescaped Unicode where JSON permits it
one final LF
```

Every upstream contract digest, the Plan digest bound by a Request and the Request, Instruction
and Decision module digests use SHA-256 over these complete canonical-document bytes.

The repository `stable_id(kind, payload)` convention is separate. It uses compact canonical JSON
with sorted keys and returns the first twenty hexadecimal SHA-256 digits under a kind prefix.
Each v2.6 stable ID covers every field in its model or module except that stable ID itself.

Do not hash a model before strict revalidation. Do not call a value-equivalent, differently
serialized input file canonical merely because its parsed model is valid.

## Fixed provider-neutral known vector

The consumer rebuilds, in memory, the released Creative Sample Pilot specification and Pack,
their deterministic compilation and the real-asset intake template. Callers cannot provide an
alternate story, Pilot Pack, shot order, role list or template.

The admitted known vector fixes:

```text
duration_ms=72000
ordered_shot_count=10
image_requirement_count=4
voice_requirement_count=9
bgm_requirement_count=1
total_real_media_count=14
```

The Plan contains a provider-neutral lineage binding over these fixed predecessor values:

- Pilot specification digest;
- predecessor compilation identity and digest;
- ten predecessor shot identities;
- intake template identity and digest;
- intake-template digest, which transitively pins the exact image, audio and shot-role
  requirements used for deterministic mapping.

The projection excludes the Pilot Pack's `provider_batch_plan`. It excludes Provider, model,
region, operation, account, price, credential, request fingerprint, Task Queue, Runtime release
and ledger identity. A historical Pilot Pack ID may be recorded as lineage metadata but cannot be
used to infer any Provider selection or authorization.

The provider-neutral projection is deterministic and fixes:

```text
domain=sdc:creative-sample-real-asset-provider-neutral-baseline:v1\0
projection_sha256=b888bdb0dfd76444905b0287d6b424525463e2618e3f17d5fc49b3538f1aff11
```

Here `\0` is one NUL byte. The compact canonical payload contains exactly:

```text
intake_template_id=real_asset_intake_template_58cfac98339ce9e36dce
intake_template_document_sha256=0c969aba4e885b8dc1fadd36d934c19dbc37cc5c0241651605ebdc6c7cdfccc8
pilot_pack_id=creative_pilot_pack_b1041dbe27fc145c73c8
pilot_spec_payload_sha256=221ccd64abeaa786f9271e89e70c2c8ab37e8f03790daa766f9b763aa25e0af4
pilot_spec_document_sha256=43f7cb9949796a2d212e8b85aa23dc4e46eef22f1a2fcf10ad978d994ace261b
pilot_compilation_id=creative_sample_c43253e73fe962f1623d
pilot_compilation_document_sha256=cd5a441fc1610435663ae3add96a14af9c2afe3c089202711ae9189181b3c8d5
pilot_ordered_shot_ids=<the ten exact IDs frozen in SDC-ADR-027 and the contract constant>
```

The opaque released `pilot_pack_id` covers its old Pack's complete content, including the old
illustrative batch plan. It is retained only as predecessor lineage. The v2.6 consumer never
copies or interprets the old Provider/model/region/operation fields, and it does not promise that
editing those old fields would preserve the opaque predecessor ID or projection digest.

## Use Plan policy

The Plan must bind exactly:

```text
policy_id=creative-sample-real-asset-use-plan-policy
policy_version=2.6.0
policy_document_sha256=68ce2b32bfac11e88a19b3155d3935f47dc7334d79e97496245f046836b28775
```

The digest input is the literal domain bytes
`sdc:creative-sample-real-asset-use-plan-policy:v2.6\0`, where `\0` is one NUL byte, followed by
compact canonical JSON for this payload:

```json
{
  "consumer_scope": "OFFLINE_DESIGN_REVIEW_ONLY",
  "policy_id": "creative-sample-real-asset-use-plan-policy",
  "policy_version": "2.6.0",
  "positive_manifest_status": "RIGHTS_MANIFEST_CREATED",
  "rules": [
    "EXACT_VERIFIED_RIGHTS_MANIFEST_CLOSURE",
    "EXACT_PROVIDER_NEUTRAL_PILOT_BASELINE",
    "EXACT_FOURTEEN_MEDIA_MAPPINGS",
    "DETERMINISTIC_NEW_SPEC_AND_COMPILATION",
    "PROPOSAL_CEILINGS_ARE_NOT_AUTHORITY",
    "NO_V1_RIGHTS_OR_REVISION_CONVERSION",
    "NO_GENERATION_NO_EXECUTION_NO_PROVIDER_AUTHORIZATION_NO_PUBLICATION"
  ]
}
```

Policy identity, version, digest, rule order and payload are built in. There is no caller,
environment or configuration override.

## Structured use bindings

`CreativeSampleRealAssetUsePlanV1` contains exactly fourteen use bindings in Pack ordinal order.
Each binding must expose enough data to audit the Pack-to-design relationship without opening a
media file:

```text
ordinal
mapping_id
requirement_id
logical_path
object_path
kind
subject_kind
subject_id
media_type
media_sha256
media_size_bytes
duration_ms
source_authority
provenance_record_sha256
technical_profile
technical_record_sha256
use_role
target_id
timeline_start_ms
timeline_end_ms
exact_text
```

Fields that do not apply to a media kind are explicit nulls only where the strict helper contract
permits them. Shape rules are:

- `IMAGE`: target is one exact character or scene role; duration and audio interval are absent;
- `VOICE`: target is one exact dialogue line; exact text, start and end match the fixed Pilot
  dialogue; and
- `BGM`: target is the master score and covers exactly `[0, 72000)`.

The binding tuple must contain exactly four `IMAGE`, nine `VOICE` and one `BGM` member. Pack
ordinal, requirement ID, subject, logical path, kind and technical profile must replay the fixed
intake template. Media digest, size, duration, provenance and technical record must replay the
exact Pack descriptor. Media digests and retained-record digests remain distinct and non-aliasing
under the inherited Pack and Manifest rules.

Filenames, tuple position alone or matching media types cannot substitute for requirement IDs and
subjects. No binding is inferred from a sibling file or directory scan.

## Derived real specification and compilation

The consumer creates new imported-media asset versions for the exact four image bindings. Their
identities bind the media digest, requirement, technical record and Rights Manifest reference.
It then creates one deterministic `CreativeSampleSpec` that preserves the fixed narrative,
dialogue, shot timing and creative direction while replacing fixture-only image identities.

`CharacterAssetVersion` and `SceneAssetVersion` retain the older field name `approval_ref`.
Within this consumer its value is a deterministic v2.6 planning-binding ID over the exact
Manifest and media facts. It does not mean Provider approval or operational authorization.

The public pure `compile_creative_sample` operation compiles the new specification. The Plan
binds the complete real specification and compilation, their canonical digests, the compilation
ID and exactly ten ordered derived shot IDs.

The verifier requires:

- real specification digest differs from the Pilot specification digest;
- real compilation ID differs from the predecessor compilation ID;
- every derived shot ID differs from its predecessor at the same ordinal;
- all four active asset versions are imported-media versions bound to the exact Pack;
- the compilation is an exact pure rebuild of the embedded specification;
- ten shots and the audio clock cover exactly 72,000 contiguous milliseconds; and
- the nine voice bindings and BGM binding close over the exact dialogue and master clock.

The module must not import or call `CreativeSampleRealAssetRevision`, private v1 derivation
helpers, `qualify_real_asset_candidate_pack`, the v1 rights-manifest builder or a v1 28-row review
conversion. It may reuse the immutable Pack model, public intake template builder, public Pilot
known-vector builder, public creative contracts and pure compiler.

## Use Plan fixed state and planning envelope

Every valid Plan fixes:

```text
schema_version=1.0.0
document_type=sdc.creative-sample-real-asset-use-plan-v1
profile=creative-sample-real-asset-use-plan-consumer-v2.6
source_mode=IMPORTED_MEDIA
consumer_scope=OFFLINE_DESIGN_REVIEW_ONLY
status=USE_PLAN_CANDIDATE_CREATED

rights_qualification_performed=true
rights_manifest_created=true
use_scope_review_performed=false
eligible_for_separate_use_scope_review=true
eligible_for_separate_provider_proposal=false
eligible_for_separate_provider_approval=false
provider_approval_granted=false
eligible_for_real_generation=false
generation_authorized=false
execution_authorized=false
publication_authorized=false

remote_processing_allowed=false
retention_allowed=false
training_allowed=false
publication_allowed=false

current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
authorized_attempts=0
authorized_cost_cny=0
posts_allowed=0
provider_requests=0
```

The non-authoritative proposal envelope is exactly:

```text
shot_count=10
proposed_attempts_per_shot=2
proposed_provider_requests_max=20
proposed_image_generation_requests=0
proposed_audio_generation_requests=0
proposed_cost_ceiling_cny=450
```

Ten times two explains the planning request ceiling of twenty. It does not allocate twenty
permits. The CNY 450 value is an exact contract number, not a floating estimate and not a charge
authorization. No derived or convenience property may map these proposal fields into any
`authorized_*`, `posts_allowed` or `provider_requests` field.

## Plan identity and no new Plan time

The Plan stable ID binds every Plan field except `plan_id`. A Request later binds both that ID and
the SHA-256 of the complete canonical Plan document.

The Plan introduces no wall-clock field. It records only the inherited historical `manifest_at`
and `evidence_valid_until` from the exact closure. Plan build and historical verification must be
byte-deterministic for the same inputs regardless of the day they run.

Do not add `created_at`, call `datetime.now`, inspect a file timestamp, read a timezone or use an
environment timestamp. Current temporal assessment belongs to the Review boundary and always
uses an explicit `observed_at`.

## Plan build procedure

The pure Plan builder performs, in order:

1. strict canonical revalidation of all nine closure models;
2. complete historical Manifest closure reconstruction;
3. exact positive Manifest and zero-authority admission checks;
4. fixed Pilot, compilation and intake-template known-vector reconstruction;
5. provider-neutral lineage projection and digest construction;
6. one-to-one validation of all fourteen Pack descriptors against exact intake roles;
7. deterministic imported-media asset-version and real-specification derivation;
8. pure compilation and ten-shot/72-second closure verification;
9. construction of all fourteen structured use bindings;
10. insertion of the fixed planning envelope and zero-authority constants;
11. content-derived Plan ID construction; and
12. final strict validation of the immutable Plan.

An exception returns no Plan model and has no external side effect.

## Plan historical verification

Historical Plan verification accepts the same nine upstream models and one in-memory Plan. It
strictly revalidates the Plan, reruns the complete build procedure with no current clock, and
requires exact model equality. It does not trust the Plan ID, Manifest SHA, provider-neutral
digest, embedded specification or compilation in isolation.

Historical verification remains possible after an inherited Evidence deadline. It proves what
the Plan bound historically; it does not assert that the Plan is presently rights-clear or that
rights have not since changed.

## Review policy

Every Request, Instruction, Decision and Record binds the fixed Review policy as applicable:

```text
policy_id=creative-sample-real-asset-use-scope-review-policy
policy_version=2.6.0
policy_document_sha256=0a2745b52d92335e8894b79ee7ff5588dea79d5bbfd021489c45c3bec5f7a969
```

The digest input is the literal domain bytes
`sdc:creative-sample-real-asset-use-scope-review-policy:v2.6\0`, where `\0` is one NUL byte,
followed by compact canonical JSON for:

```json
{
  "gate_order": [
    "COPYRIGHT_USE_SCOPE",
    "LIKENESS_USE_SCOPE",
    "PRIVACY_USE_SCOPE",
    "TERRITORY_USE_SCOPE",
    "CONTENT_ROLE_USE_SCOPE",
    "OFFLINE_ONLY_RESTRICTIONS"
  ],
  "policy_id": "creative-sample-real-asset-use-scope-review-policy",
  "policy_version": "2.6.0",
  "request_validity_seconds": 86400,
  "requested_outcome_scope": "PROVIDER_PROPOSAL_DESIGN_ONLY",
  "review_scope": "OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY",
  "review_validity_seconds": 2592000,
  "rules": [
    "EXACT_USE_PLAN_AND_MANIFEST_CLOSURE",
    "MAKER_CHECKER_PROCEDURAL_SEPARATION",
    "REQUEST_WINDOW_EXCLUSIVE",
    "EVIDENCE_VALID_AT_REQUEST_AND_CHECK",
    "FIXED_GATE_ORDER",
    "PASS_REQUIRES_ALL_GATES_APPROVED",
    "NEGATIVE_REQUIRES_FAILED_GATE",
    "REJECTION_REQUIRES_EXPLICIT_DISPOSITION",
    "PROVIDER_PROPOSAL_ELIGIBILITY_ONLY",
    "NO_REMOTE_PROCESSING_RETENTION_TRAINING_PUBLICATION",
    "NO_PROVIDER_APPROVAL_GENERATION_EXECUTION_AUTHORIZATION"
  ]
}
```

## Single Review Record layout

The final Record has three physically nested modules and three independent module digests. The
conceptual structure is:

```json
{
  "request": {},
  "request_sha256": "...",
  "instruction": {},
  "instruction_sha256": "...",
  "decision": {},
  "decision_sha256": "...",
  "record_id": "..."
}
```

The complete strict contract also carries its schema, document, profile and fixed zero-authority
facts. Actual canonical member order is sorted-key order, not the illustrative order above.

For each module:

1. derive the module stable ID over every module field except its own ID;
2. strictly validate the complete module including that ID;
3. serialize the complete module as a standard canonical document; and
4. SHA-256 those exact bytes with no domain prefix.

The Instruction binds `request_id` and `request_sha256`. The Decision binds Request and
Instruction IDs and digests. The outer Record embeds all three exact models and digests.
`record_id` is the repository stable ID over every outer field except `record_id`. It is the
finalization fingerprint for the complete Record payload, not a complete-file SHA-256.

Any one-byte module change invalidates that module's stable ID or digest and every downstream
binding. The verifier does not repair or recalculate a submitted stale value.

## Request module

The Maker creates the immutable Request first. It binds:

```text
request_id
use_plan_id
use_plan_sha256
maker_identity_ref_sha256
requested_at
request_valid_until
request_basis
review_scope=OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY
requested_outcome_scope=PROVIDER_PROPOSAL_DESIGN_ONLY
remote_processing_allowed=false
retention_allowed=false
training_allowed=false
publication_allowed=false
```

It also binds the exact Plan/Manifest closure and fixed Review policy fields required by the
implementation contract. The Maker supplies only the explicit time and retained identity
reference allowed by the pure API; IDs, digests, deadlines, scopes and zero-authority values are
recomputed or fixed.

The request deadline is exactly:

```text
request_valid_until = requested_at + 86400 seconds
```

The deadline is exclusive. The Request contains no Checker conclusion and no final Decision.

## Instruction module

The Checker creates a new immutable Instruction from the exact Plan and Request. It binds:

```text
instruction_id
use_plan_id
use_plan_sha256
request_id
request_sha256
maker_identity_ref_sha256
checker_identity_ref_sha256
evaluated_at
review_scope=OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY
requested_outcome_scope=PROVIDER_PROPOSAL_DESIGN_ONLY
gate_results
disposition
checker_basis
```

The Checker cannot amend the Request through the Instruction. If the Request or Plan needs a
change, the Checker returns it and the Maker creates a new Plan or Request with a new identity and
digest.

The two identity-reference SHA-256 values must differ. That inequality is a procedural contract
check only. It does not authenticate either person, verify signatures or prove custody of an
identity file. PR1 accepts already computed synthetic reference digests. A later trusted-local
ADR must specify exact separate identity paths, safe reads and file-identity checks.

## Six fixed gate results

`gate_results` contains exactly six entries in this order:

```text
COPYRIGHT_USE_SCOPE
LIKENESS_USE_SCOPE
PRIVACY_USE_SCOPE
TERRITORY_USE_SCOPE
CONTENT_ROLE_USE_SCOPE
OFFLINE_ONLY_RESTRICTIONS
```

Each entry contains an exact Boolean `approved`. The tuple cannot be reordered, shortened,
extended or duplicated. Failed-gate issue codes are deterministically derived in the same order;
the Checker does not provide a separate arbitrary issue-code tuple.

Machine-verifiable closure integrity, fourteen-member mapping, provider-neutral lineage and
compilation equality are not human gate choices. The consumer verifies them before admitting the
Instruction.

The Checker selects exactly one disposition:

```text
PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY
NEEDS_REVISION
REJECTED
```

Admission rules are:

| Gate state | Admitted disposition | Derived overall Decision |
|---|---|---|
| All six true | `PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY` only | `PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY` |
| At least one false, no explicit rejection | `NEEDS_REVISION` | `NEEDS_REVISION` |
| At least one false, explicit rejection | `REJECTED` | `REJECTED` plus fixed rejection issue code |

PASS with any false gate, NEEDS_REVISION with all gates true, REJECTED with all gates true or an
unknown disposition fails closed.

Failed-gate issue codes are unique and use this exact order and mapping:

```text
COPYRIGHT_USE_SCOPE             -> COPYRIGHT_USE_SCOPE_NOT_CONFIRMED
LIKENESS_USE_SCOPE              -> LIKENESS_USE_SCOPE_NOT_CONFIRMED
PRIVACY_USE_SCOPE               -> PRIVACY_USE_SCOPE_NOT_CONFIRMED
TERRITORY_USE_SCOPE             -> TERRITORY_USE_SCOPE_NOT_CONFIRMED
CONTENT_ROLE_USE_SCOPE          -> CONTENT_ROLE_USE_SCOPE_NOT_CONFIRMED
OFFLINE_ONLY_RESTRICTIONS       -> OFFLINE_ONLY_RESTRICTIONS_NOT_CONFIRMED
explicit REJECTED disposition   -> CHECKER_REJECTED_USE_SCOPE
```

## Decision module

The deterministic compiler, not the Maker or Checker, constructs the Decision. It binds the exact
Plan, Request and Instruction identities and standard canonical-document digests, Review policy,
recorded time boundaries, derived issue codes and derived final outcome.

The compiler accepts no new free text, gate value, issue code or outcome override. Its output
must be fully reproducible from the immutable Plan, Request, Instruction and fixed policy.

For PASS it fixes:

```text
eligible_for_separate_provider_proposal=true
eligible_for_separate_provider_approval=false
provider_approval_granted=false
eligible_for_real_generation=false
generation_authorized=false
execution_authorized=false
publication_authorized=false
remote_processing_allowed=false
retention_allowed=false
training_allowed=false
publication_allowed=false
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
authorized_attempts=0
authorized_cost_cny=0
posts_allowed=0
provider_requests=0
```

For NEEDS_REVISION or REJECTED,
`eligible_for_separate_provider_proposal=false`; every other zero-authority value remains the
same.

## Three-stage construction rule

The pure construction order is normative:

1. build and freeze the Request;
2. build and freeze the Instruction against the exact Request canonical digest;
3. compile the Decision and complete outer Record against both frozen modules.

Do not expose a one-call API that accepts all Maker and Checker free fields and fabricates all
three modules without an immutable intermediate boundary. Do not permit the Checker constructor
to edit Request fields. Do not permit the finalizer to alter either human-owned module.

PR1 performs these stages in memory only. It does not create or mutate files. A future
trusted-local boundary may eventually materialize one complete Record through create-new
semantics, but must not progressively write or rewrite the same output path as Request,
Instruction and Decision arrive.

## Time rules

All supplied times use canonical whole-second UTC:

```text
YYYY-MM-DDTHH:MM:SSZ
```

The consumers never read a wall clock. They enforce:

```text
manifest_at <= requested_at <= evaluated_at < request_valid_until
request_valid_until = requested_at + 86400 seconds
```

For finite Evidence:

```text
requested_at < evidence_valid_until
evaluated_at < evidence_valid_until
```

All upper bounds are exclusive. Equality with `request_valid_until` or a finite
`evidence_valid_until` is invalid.

The Review deadline is computed, never selected:

```text
candidate_review_end = evaluated_at + 2592000 seconds

if evidence_valid_until == PERPETUAL:
    review_valid_until = candidate_review_end
else:
    review_valid_until = min(candidate_review_end, evidence_valid_until)
```

`2592000` is exactly thirty 86,400-second days; it is not calendar-month arithmetic. A finite
Evidence deadline must be strictly later than `evaluated_at`. The Request's 24-hour window governs
timely Checker action but does not truncate the completed Review's separate 30-day horizon.

## Historical verification

Historical Review verification accepts the complete nine-model closure, exact Use Plan and one
Review Record. It:

1. historically verifies the Manifest and Use Plan without a clock;
2. strictly revalidates the three embedded modules and outer Record;
3. recomputes all three stable IDs and standard canonical-document digests;
4. verifies the Plan -> Request -> Instruction -> Decision digest chain;
5. recomputes the request and review deadlines from recorded times;
6. derives failed-gate issue codes and overall Decision from the fixed policy;
7. rebuilds the complete outer Record; and
8. requires exact model equality.

Historical verification remains valid after deadlines expire because it answers whether the
record was correctly formed at its recorded times. It does not answer whether the record may be
consumed now.

## Explicit-observation recorded-window currency

Current-consumability assessment is a separate pure operation. The caller supplies
`observed_at`; there is no default and no current clock read. The operation first performs full
historical verification, requires the PASS outcome, and then enforces:

```text
evaluated_at <= observed_at < review_valid_until
```

At `review_valid_until`, the Record is not current. A NEEDS_REVISION or REJECTED Record is never
inside a current proposal-design window.

On success the function returns the same fully verified immutable Review Record; it does not
mint a new status token or artifact. The strongest supported finding is only that the recorded
PASS remains inside its exclusive temporal window for separate Provider-proposal design. It is
not Provider approval, entitlement, generation eligibility, execution authorization or
publication approval.

The operation cannot detect a later hold, revocation, complaint, dispute or rights-policy change
from historical contracts. Before any future proposal progresses toward actual authorization, a
future ADR must define and bind fresh status evidence for those conditions. Do not add a mutable
registry lookup or network check to this pure v2.6 module.

## Strict parse and extraction

Every public parser accepts bounded non-empty in-memory bytes and rejects:

- malformed UTF-8 and BOM;
- a top-level value other than one object;
- duplicate keys at any depth;
- `NaN`, positive or negative infinity;
- missing, unknown or coerced fields;
- invalid SHA-256 or stable-ID shape;
- invalid fixed policy, scope, gate order or zero-authority value;
- non-canonical or invalid timestamps; and
- any model-level cross-binding failure.

The public byte parsers require the supplied bytes to equal the exact standard canonical document.
An in-memory model or extracted module alone does not prove that some external file contains those
bytes or came from an authenticated path; those are future trusted-local responsibilities.

The Review module provides read-only extraction after strict self-contained Record validation.
Each extractor returns the exact public module model and its standard canonical bytes. Extraction
does not accept a partially valid Record, rewrite a section or create an operational file. Before
treating any extracted content as accepted, the caller must run the full closure verifier over
the nine upstream models, exact Plan and Record; extraction alone is not closure acceptance.

## Synthetic test procedure

Tests construct a complete fourteen-object synthetic Pack and full positive Manifest closure in
memory. No test may contain a current real identifier, path, digest, media byte or private text.

Minimum positive Plan coverage:

1. build a complete synthetic nine-model closure;
2. rebuild the fixed Pilot and intake known vectors;
3. build the Plan twice and require exact equality;
4. require four image, nine voice and one BGM binding in exact order;
5. require a new real specification, compilation and ten shot IDs;
6. require the exact `10 x 2 = 20`, CNY 450 proposal envelope and zero authorization;
7. strict-parse canonical Plan bytes; and
8. historically verify the complete Plan closure.

Minimum positive Review coverage:

1. create a Maker Request with a fixed explicit `requested_at`;
2. create a distinct Checker Instruction before the exclusive 24-hour deadline;
3. mark all six gates approved and select PASS;
4. finalize one complete Record;
5. verify each module ID, standard canonical digest and downstream binding;
6. rebuild the deterministic PASS Decision;
7. extract each physical module and compare canonical bytes; and
8. assess recorded-window currency immediately before, but not at, the exclusive Review deadline.

Negative Plan tests cover at least:

- mutation of every one of the nine upstream models;
- a Manifest treated as a standalone authority token;
- missing, duplicate or reordered Pack objects and use bindings;
- wrong image, dialogue, BGM, time, text, provenance or technical mapping;
- Provider/model/region data leaking into the provider-neutral lineage or Plan;
- equality with predecessor specification, compilation or shot identities;
- any v1 rights/revision builder dependency;
- proposal ceilings copied into authorization fields;
- every non-zero authority, remote, retention, training or publication attempt;
- malformed strict JSON and stale Plan identity; and
- any wall-clock, filesystem, network, Provider or Runtime dependency.

Negative Review tests cover at least:

- Maker and Checker identity-reference digests equal;
- Request at or after finite Evidence expiry;
- Checker at exactly or after the Request deadline;
- Checker at exactly or after finite Evidence expiry;
- incorrect 86,400 or 2,592,000 second arithmetic;
- finite Evidence failing to shorten the Review deadline;
- gate omission, duplicate or reorder;
- PASS with a false gate;
- NEEDS_REVISION or REJECTED with all gates true;
- REJECTED without its fixed rejection issue code;
- any caller-supplied issue-code or Decision override;
- drift in any module byte, stable ID, digest or downstream reference;
- flattening or cross-writing fields between modules;
- Record ID not covering the complete final payload;
- current observation before evaluation, at expiry or after expiry;
- historical verification incorrectly consulting current time; and
- any attempted authority escalation for all three outcomes.

Schema tests retain fixed normalized-LF SHA-256 locks for all 57 earlier Schemas, require exactly
62 unique registered model names/files, compare each committed Schema to
`model_json_schema()`, and assert the v2.6 fixed zero-authority constants.

## Explicit prohibitions

This v2.6 PR must not:

- expose a filesystem path, finalizer, authoring UI, workspace or CLI;
- claim an `inspect`, `finalize` or `verify` trusted-local command exists;
- read or write real private artifacts;
- persist Request and Instruction as separately authorized real artifacts;
- incrementally edit a Review Record output;
- authenticate a person from digest inequality alone;
- select or call a Provider, model, account, region or operation;
- create an entitlement, authorization, permit, task, ledger row or registry entry;
- upload, POST, generate, purchase, recharge, claim a trial or publish;
- read a Key, clock, filesystem timestamp, environment-selected time or network;
- import Runtime, Worker, Provider, Ark, database, Temporal, ledger or migration code;
- invoke a v1 rights/qualification/revision conversion; or
- infer authority from Manifest verification, PASS, proposal count or cost ceiling.

## Future stages

Merging PR1 authorizes no real-data operation. Each later stage requires a separate design,
implementation review and explicit approval:

1. trusted-local Plan and single-Record preparation/finalization with exact absolute paths,
   separate identity-reference files, safe bounded reads, path/file identity checks, TOCTOU
   defense, create-new output and rollback/quarantine semantics;
2. a fresh hold/revocation/status evidence design;
3. an exact Provider proposal containing Provider, model, region, account, operation, pricing and
   request fingerprints;
4. current entitlement and capability evidence;
5. finite, independently reviewed batch authorization and atomic per-request permits;
6. replaceable Runtime/Provider adapters, dedicated ledger and no-repost handling for unknown
   submission state; and
7. separate output QC and publication authorization.

No step inherits approval from the previous step. A v2.6 PASS only permits preparing the design
for step 3; it does not approve step 3 or any later operation.
