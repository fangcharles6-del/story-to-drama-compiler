# SDC-ADR-027: Manifest-bound offline real-asset use planning and review v2.6

- **Status:** Accepted
- **Date:** 2026-08-19
- **ADR release:** 1.0
- **Contract schema version:** 1.0.0
- **Consumer and policy version:** 2.6.0

## Context

SDC-ADR-025 introduced the immutable
`CreativeSampleRealAssetRightsManifestV2` and its pure v2.4 consumer. SDC-ADR-026 then specified
a separately controlled trusted-local v2.5 boundary for creating and historically verifying one
exact Manifest artifact. A valid Manifest records that one exact fourteen-member Pack passed the
earlier, narrowly scoped asset-intake rights process. It remains deliberately inert:

```text
rights_manifest_created=true
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

The Manifest is not a bearer token. Its existence or successful verification does not authorize
use by a Provider, remote processing, retention, model training, generation, Runtime execution,
publication or distribution. It also does not establish that a historical rights statement is
still free of a later hold, revocation, complaint or dispute.

The next useful production-design boundary is therefore not entitlement or execution. The team
first needs a deterministic, provider-neutral statement of how the fourteen exact admitted media
objects would map into the fixed 72-second, ten-shot Creative Sample design. A second human must
then be able to assess that exact offline plan against the rights scope without approving their
own request and without turning a planning ceiling into authority.

The team has two people. Requiring six different natural persons would make the process
inoperable without improving the cryptographic or contractual facts. Conversely, merging request,
review and decision into undifferentiated fields would erase the responsibility chain. The design
must preserve zero authority, deterministic closure verification, plan/review separation and
Maker/Checker procedural separation while using one final review artifact.

## Decision

Add two pure in-memory v2.6 consumers:

```text
sdc.real_asset_use_plan_v26
sdc.real_asset_use_scope_review_v26
```

They define these five top-level versioned artifact contracts and committed Schemas:

1. `CreativeSampleRealAssetUsePlanV1`;
2. `CreativeSampleRealAssetUseScopeReviewRequestV1`;
3. `CreativeSampleRealAssetUseScopeReviewInstructionV1`;
4. `CreativeSampleRealAssetUseScopeReviewDecisionV1`; and
5. `CreativeSampleRealAssetUseScopeReviewRecordV1`.

Every public contract uses `schema_version=1.0.0`. The consumer profiles and both fixed policy
documents use version `2.6.0`. “ADR release 1.0”, “contract schema 1.0.0” and “consumer/policy
2.6.0” name different versioned surfaces and must not be substituted for one another.

This first implementation PR is a **pure contract PR**. It accepts only already constructed
in-memory models, writes no file, accepts no path, has no CLI or `__main__`, reads no wall clock,
uses no network and touches no Provider, Runtime, Worker, entitlement, authorization, ledger,
database or registry. Tests use synthetic fixtures only. No real private artifact is read or
created by this PR.

A trusted-local authoring or finalization boundary, any real-data operation, Provider proposal,
fresh entitlement evidence, execution authorization, Runtime integration and publication review
are separate future designs, PRs and explicit approvals. This ADR does not pre-approve their
commands, paths, identities or behavior.

## Complete nine-model Manifest closure

The Use Plan builder accepts the complete, exact closure rather than accepting a Manifest alone:

1. `CreativeSampleFrozenRealAssetPackManifest`;
2. `CreativeSampleRealAssetRightsEvidenceBundleV2`;
3. Reviewer A's finalized `CreativeSampleRealAssetHumanPackReviewV2`;
4. Reviewer B's finalized `CreativeSampleRealAssetHumanPackReviewV2`;
5. their issue-free `CreativeSampleRealAssetReviewPairCheckV2`;
6. `CreativeSampleRealAssetQualificationRequestV2`;
7. `CreativeSampleRealAssetQualificationDecisionInstructionV22`;
8. the positive `CreativeSampleRealAssetQualificationDecisionV2`; and
9. `CreativeSampleRealAssetRightsManifestV2`.

The consumer strictly revalidates all nine models and invokes the existing pure historical
Manifest closure verifier. It requires the Manifest to reconstruct exactly from the other eight
models at the Manifest's recorded `manifest_at`. Supplying a copied Manifest ID, digest, positive
terminal line or `rights_manifest_created=true` is insufficient.

The Manifest must retain the exact zero-authority positive state defined by SDC-ADR-025. Any
drifted model, digest, ID, role, ordinal, policy, retained-record binding, non-canonical value,
negative qualification outcome or non-zero authority field fails closed.

## Fixed provider-neutral Pilot known vector

The builder deterministically reconstructs the released Creative Sample Pilot specification,
Pilot Pack, compilation and real-asset intake template. These are known vectors, not caller
choices. It verifies the exact predecessor story, 72,000 ms master clock, ten ordered shots,
four image roles, nine dialogue voice roles and one BGM role.

The Use Plan records a provider-neutral lineage projection. The projection binds only the
creative and intake facts needed to rebuild the plan, including the fixed Pilot specification,
predecessor compilation and ordered shots, intake template and the exact asset/audio role
requirements. It excludes the Pilot Pack's `provider_batch_plan` and excludes Provider name,
model, region, operation, account, pricing, credentials, request fingerprints and Runtime
configuration.

The historical Pilot Pack ID may be retained as lineage metadata, but it is not interpreted as a
Provider selection. No field or digest copied from the Pilot's illustrative batch-planning
section becomes a v2.6 Provider binding. The provider-neutral projection has its own deterministic
digest, and the Use Plan policy validates that projection rather than inheriting an executable
batch plan.

The projection digest is fixed as:

```text
domain=sdc:creative-sample-real-asset-provider-neutral-baseline:v1\0
projection_sha256=b888bdb0dfd76444905b0287d6b424525463e2618e3f17d5fc49b3538f1aff11
```

Here `\0` is one NUL byte. The domain is followed by compact canonical JSON for this exact
payload:

```json
{
  "intake_template_document_sha256": "0c969aba4e885b8dc1fadd36d934c19dbc37cc5c0241651605ebdc6c7cdfccc8",
  "intake_template_id": "real_asset_intake_template_58cfac98339ce9e36dce",
  "pilot_compilation_document_sha256": "cd5a441fc1610435663ae3add96a14af9c2afe3c089202711ae9189181b3c8d5",
  "pilot_compilation_id": "creative_sample_c43253e73fe962f1623d",
  "pilot_ordered_shot_ids": [
    "storyboard_shot_v2_6efad69a2a84e32dbc5b",
    "storyboard_shot_v2_13822570b72c80607da5",
    "storyboard_shot_v2_c506a9c24a958ea1645b",
    "storyboard_shot_v2_70097fbd380d13f419f7",
    "storyboard_shot_v2_c13ef471e7c016ef416f",
    "storyboard_shot_v2_c2f12fbc85044ad16dfb",
    "storyboard_shot_v2_99634ba94f4c01b7de21",
    "storyboard_shot_v2_8fe54fb039ee2c31e475",
    "storyboard_shot_v2_433f35b18c478ab1428c",
    "storyboard_shot_v2_64efc36a850a3781c7bb"
  ],
  "pilot_pack_id": "creative_pilot_pack_b1041dbe27fc145c73c8",
  "pilot_spec_document_sha256": "43f7cb9949796a2d212e8b85aa23dc4e46eef22f1a2fcf10ad978d994ace261b",
  "pilot_spec_payload_sha256": "221ccd64abeaa786f9271e89e70c2c8ab37e8f03790daa766f9b763aa25e0af4"
}
```

The opaque historical `pilot_pack_id` is included to pin the released predecessor and is also
covered by the complete Plan identity. Because that predecessor ID covers the old Pack's entire
content, this ADR does not claim that editing an illustrative Provider field in the old Pack
would preserve the predecessor ID or projection digest. Provider-neutral means that v2.6 neither
copies nor interprets those fields as a Provider choice or executable plan.

## Exact fourteen-member use mapping

The Use Plan contains exactly fourteen ordered, structured use bindings corresponding one-to-one
with Pack ordinals `0..13`:

- four PNG media objects map to exact character or scene asset roles;
- nine WAV voice objects map to exact dialogue line IDs, canonical text and master-clock
  intervals; and
- one WAV BGM object maps to the complete 72,000 ms master clock.

Every binding carries, at minimum, the Pack ordinal, requirement ID, logical path, media kind,
subject ID, media SHA-256, size, duration, provenance-record SHA-256, technical-record SHA-256,
target role and target subject. Voice and BGM bindings also carry their exact time boundary;
voice bindings carry the exact dialogue text. The tuple preserves canonical Pack order.

The builder reconstructs the fixed intake template and proves that every descriptor satisfies its
exact requirement. It rejects an omission, duplicate, reorder, renamed role, changed subject,
changed byte digest, changed retained record, changed technical evidence, filename inference or
one object silently satisfying two roles.

## New deterministic specification and compilation

Using only the verified Pack mappings, provider-neutral Pilot known vector and exact Manifest
binding, the Use Plan derives a new `CreativeSampleSpec` and compiles it with the existing pure
`compile_creative_sample` function. The result must contain exactly ten ordered shots and a
72,000 ms audio clock.

The four imported images receive new active asset-version identities bound to the exact media,
requirement, technical evidence and Manifest. The real specification digest, compilation ID,
compilation digest and every derived shot ID must differ from the synthetic predecessor. The
Plan embeds enough structured specification, compilation and mapping content for deterministic
rebuild and audit.

The inherited creative-contract field named `approval_ref` stores a v2.6 planning-binding ID
derived from the exact Manifest and media facts. In this context it means only “source binding
accepted for offline plan construction”; it is not Provider approval, execution approval or a
bearer authorization.

This is a new v2.6 derivation. It must not call, wrap or convert the Real Asset Intake v1 rights
builder, `CreativeSampleRealAssetRevision`, its private derivation helpers,
`qualify_real_asset_candidate_pack`, or any path that invents 28 v1 review acts. Reusing the
immutable frozen Pack model, fixed intake template, Pilot known-vector builder, public creative
contracts and pure compiler is not a v1 rights conversion.

## No clock in the Use Plan

`CreativeSampleRealAssetUsePlanV1` is a deterministic compiled artifact. It introduces no
`created_at`, `planned_at`, `evaluated_at` or wall-clock-derived value. The Plan carries the
Manifest's existing historical `manifest_at` and inherited `evidence_valid_until` only as bound
upstream facts.

Two identical nine-model closures always produce the same Plan. Historical verification reuses
the recorded upstream times and reads no current time. A later recorded-window assessment
must use an explicit caller-supplied `observed_at`; it must never mutate or reissue the Plan.

## Fixed Use Plan policy

The Plan binds this non-selectable policy triple:

```text
use_plan_policy_id=creative-sample-real-asset-use-plan-policy
use_plan_policy_version=2.6.0
use_plan_policy_document_sha256=68ce2b32bfac11e88a19b3155d3935f47dc7334d79e97496245f046836b28775
```

The digest is SHA-256 over the literal domain
`sdc:creative-sample-real-asset-use-plan-policy:v2.6\0`, where `\0` is one NUL byte, followed by
compact canonical JSON for:

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

The displayed indentation is non-normative; digest input uses UTF-8, sorted object keys,
unescaped Unicode where JSON permits it and no insignificant whitespace.

## Planning envelope is not authority

The Use Plan fixes this proposal envelope for later human and engineering discussion:

```text
shot_count=10
proposed_attempts_per_shot=2
proposed_provider_requests_max=20
proposed_image_generation_requests=0
proposed_audio_generation_requests=0
proposed_cost_ceiling_cny=450
```

The cost is an exact non-floating JSON number. These values are planning ceilings, not granted
budgets or request permits. The same Plan fixes:

```text
authorized_attempts=0
authorized_cost_cny=0
posts_allowed=0
provider_requests=0
```

It also fixes:

```text
source_mode=IMPORTED_MEDIA
consumer_scope=OFFLINE_DESIGN_REVIEW_ONLY
status=USE_PLAN_CANDIDATE_CREATED
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
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
```

No caller may override these constants. A successful Plan means only that an exact offline design
candidate exists for separate review.

## One Review Record, three physical modules

The real review outcome is one
`CreativeSampleRealAssetUseScopeReviewRecordV1` artifact. Inside that single JSON object,
`request`, `instruction` and `decision` are three nested physical modules. They are never flattened
into shared fields and no free-text field carries both an application and an approval meaning.

The three module classes have public Schemas so their boundaries are auditable and reusable by
pure code. Those Schemas do not authorize writing three operational files. In the v2.6 design,
the only eventual persisted review artifact is the outer Record.

Each module independently has:

- a stable ID derived from every module field except its own ID; and
- a standard canonical-document SHA-256 computed over the complete validated module including
  its stable ID.

Standard canonical-document bytes are UTF-8 without BOM, sorted keys, two-space indentation,
unescaped Unicode where JSON permits it and one final LF. The module SHA-256 values do not use a
domain prefix. The Instruction binds the exact Request ID and canonical-document SHA-256. The
Decision binds both preceding module IDs and SHA-256 values. The outer Record carries all three
modules and their three digests.

The outer `record_id` is a finalization fingerprint: the repository `stable_id` over the complete
Record payload excluding only `record_id`. It binds all modules, module digests, policy facts and
zero-authority facts. It is not a self-contained complete-file SHA-256 and must not be described
as one.

## Three-stage generation without incremental file mutation

The responsibility chain is generated in three pure stages:

```text
MAKER constructs immutable Request
  -> CHECKER constructs immutable Instruction bound to that Request
  -> deterministic compiler derives Decision and final Review Record
```

The Checker cannot edit the Request. A requested change returns to the Maker and produces a new
Request ID and digest. The compiler cannot add a conclusion, issue or basis absent from the
Instruction. It only verifies the fixed rules and derives the final Decision.

No stage opens or edits an in-progress Review Record file. A future trusted-local implementation
must construct complete immutable stage values, then create one new final Record after a separate
reviewed instruction exists. It must not progressively append Request, Instruction and Decision
into the same path, rewrite an earlier section, or treat an output file as mutable workflow state.

PR1 implements only the in-memory constructors and verifiers. This ADR does not claim that a
trusted-local identity file, UI, CLI, create-new write or finalizer already exists.

## Maker and Checker semantics

The Request carries a `maker_identity_ref_sha256`. The Instruction carries a distinct
`checker_identity_ref_sha256`. The policy requires:

```text
maker_identity_ref_sha256 != checker_identity_ref_sha256
```

This proves only that the contract contains two distinct procedural references. It does not
authenticate a natural person, verify a signature, prove custody of a Key or establish that two
different humans actually acted. Tests must not describe this inequality as cryptographic identity
authentication.

A future trusted-local boundary must receive two explicitly selected, repository-external
identity-reference files, safely reopen and hash them, enforce path and file-identity separation
and bind those exact bytes. That boundary requires a separate ADR and approval.

One person may act as Maker and the other as Checker across use planning, later proposal review
and later publication review. The same approval cannot span those stages, and a person may not
approve their own candidate within one stage.

## Structured offline request scope

The Request cannot carry an open-ended requested-use paragraph as its operative scope. It fixes a
structured scope:

```text
review_scope=OFFLINE_USE_PLAN_AND_RIGHTS_ALIGNMENT_ONLY
requested_outcome_scope=PROVIDER_PROPOSAL_DESIGN_ONLY
remote_processing_allowed=false
retention_allowed=false
training_allowed=false
publication_allowed=false
```

Human basis text may explain a conclusion but cannot widen these fields. Provider upload,
Provider selection, account use, generation, commercial distribution and publication remain
outside the Request.

## Six fixed human gates and deterministic outcome

The Instruction contains exactly six gate results in this fixed order:

1. `COPYRIGHT_USE_SCOPE`;
2. `LIKENESS_USE_SCOPE`;
3. `PRIVACY_USE_SCOPE`;
4. `TERRITORY_USE_SCOPE`;
5. `CONTENT_ROLE_USE_SCOPE`; and
6. `OFFLINE_ONLY_RESTRICTIONS`.

Each gate carries an exact Boolean `approved` value. Mechanical closure integrity, Pack mapping
and compilation reconstruction are not human gates; the pure verifier enforces them before an
Instruction or Record is admitted.

The Instruction disposition is one of:

```text
PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY
NEEDS_REVISION
REJECTED
```

The Decision is not caller-selected. The compiler deterministically enforces:

- `PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY` if and only if all six gates are true;
- `NEEDS_REVISION` only when at least one gate is false and no rejection disposition was selected;
- `REJECTED` only when at least one gate is false and the Instruction explicitly selects rejection;
- issue codes are derived from the failed gate set in fixed gate order; and
- rejection adds the fixed rejection issue code.

The exact derivation is:

```text
COPYRIGHT_USE_SCOPE             -> COPYRIGHT_USE_SCOPE_NOT_CONFIRMED
LIKENESS_USE_SCOPE              -> LIKENESS_USE_SCOPE_NOT_CONFIRMED
PRIVACY_USE_SCOPE               -> PRIVACY_USE_SCOPE_NOT_CONFIRMED
TERRITORY_USE_SCOPE             -> TERRITORY_USE_SCOPE_NOT_CONFIRMED
CONTENT_ROLE_USE_SCOPE          -> CONTENT_ROLE_USE_SCOPE_NOT_CONFIRMED
OFFLINE_ONLY_RESTRICTIONS       -> OFFLINE_ONLY_RESTRICTIONS_NOT_CONFIRMED
explicit REJECTED disposition   -> CHECKER_REJECTED_USE_SCOPE
```

Issue codes are unique and retain this policy order.

A PASS makes only `eligible_for_separate_provider_proposal=true`. It keeps Provider approval,
generation, Runtime execution, publication, posts and requests disabled. NEEDS_REVISION and
REJECTED make provider-proposal eligibility false. No outcome mutates an entitlement or
authorization registry.

## Fixed Review policy

The Review Record binds this non-selectable policy triple:

```text
review_policy_id=creative-sample-real-asset-use-scope-review-policy
review_policy_version=2.6.0
review_policy_document_sha256=0a2745b52d92335e8894b79ee7ff5588dea79d5bbfd021489c45c3bec5f7a969
```

The digest is SHA-256 over the literal domain
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

The displayed form is non-normative; digest calculation uses compact canonical JSON.

## Explicit request and review time boundaries

The Plan contains no new time. The Request and Instruction accept explicit canonical UTC seconds
from their callers and never read a clock:

```text
YYYY-MM-DDTHH:MM:SSZ
```

The Request window is exactly 86,400 seconds:

```text
request_valid_until = requested_at + 86400 seconds
```

The upper bound is exclusive. The Checker must act at:

```text
manifest_at <= requested_at <= evaluated_at < request_valid_until
```

For finite Evidence, both Request and Checker assessment must precede the inherited exclusive
Evidence deadline:

```text
requested_at < evidence_valid_until
evaluated_at < evidence_valid_until
```

The review horizon is 2,592,000 seconds, exactly 30 times 86,400 seconds. It is shortened, never
extended, by finite Evidence:

```text
review_valid_until = evaluated_at + 2592000 seconds                 # PERPETUAL Evidence
review_valid_until = min(evaluated_at + 2592000, evidence_valid_until)  # finite Evidence
```

`review_valid_until` is exclusive. A finite Evidence deadline must still be strictly later than
`evaluated_at`; otherwise no completed current review can be formed. Request expiry governs when
the Checker may issue the Instruction. Once a timely Review Record exists, request expiry does
not shorten the separate review horizon.

## Historical verification and recorded-window currency are separate

Historical verification reconstructs the Plan or Review Record from its recorded inputs and
times. It reads no current clock and remains possible after the Request, Review or finite Evidence
deadline. A successful historical verification says the artifact was internally valid under its
recorded boundaries; it does not make it current again.

The temporal-current check accepts an explicit caller-supplied `observed_at` and requires:

```text
evaluated_at <= observed_at < review_valid_until
```

It also reconstructs the complete Plan and Review Record and requires the PASS outcome. The check
may report only temporal eligibility for separate Provider-proposal design under the recorded time
bounds. It may not report Provider approval, generation readiness or execution authority.

Neither the historical models nor `observed_at` can prove the absence of a later rights hold,
revocation, complaint or dispute. Before any future Provider proposal could progress toward
authorization, a separately designed fresh status source must bind the exact Plan/Record and
confirm current hold/revocation state. This ADR defines no such registry or evidence contract.

## Canonical identity, parsing and audit extraction

All five top-level versioned artifact contracts are immutable strict Pydantic v2 models with
forbidden unknown fields and exact scalar types. Strict in-memory parsers reject malformed UTF-8,
BOM, duplicate keys at
any depth, non-finite numbers, a top-level non-object, missing or unknown fields, coercion,
non-canonical timestamps, invalid constants and stale stable IDs.

The outer Record permits independent extraction of Request, Instruction and Decision as their
respective validated public models and standard canonical bytes. Extraction is read-only. It
does not create three artifacts, bypass whole-Record verification or make a partially valid
Record acceptable. Acceptance always verifies the full Request -> Instruction -> Decision ->
Record digest and identity chain and the complete upstream Plan/Manifest closure. The extractors
perform self-contained Record validation; they do not replace the full closure verifier.

## Schema compatibility

PR1 adds exactly five top-level committed Schemas, one for each versioned artifact model listed in
the Decision.
Helper models such as use bindings, closure bindings and gate results appear only under Schema
`$defs`; they are not additional top-level committed Schema files.

All 57 pre-v2.6 Schemas remain normalized-LF byte-identical. The total committed Schema count
becomes 62. Adding public Request, Instruction and Decision Schemas documents the three module
boundaries; it does not change the one-artifact operational rule for a real Review Record.

## Required tests

Synthetic tests must cover at least:

- exact nine-model Manifest closure reconstruction and mutation of every upstream boundary;
- fixed Pilot and intake known vectors, provider-neutral lineage and exclusion of Provider fields;
- exactly fourteen mappings, four images, nine voices, one BGM and ten derived shots;
- new specification, compilation and shot identities and prohibition of v1 conversion paths;
- all fixed proposal ceilings and every attempted authority escalation;
- deterministic Plan build, parse, stable ID and historical verification without a clock;
- three-stage Request, Instruction and Decision construction;
- Maker/Checker reference inequality without claiming human authentication;
- standard canonical-document SHA-256 for each physical module and every digest-chain mutation;
- fixed six-gate order, deterministic issue codes and all three disposition mappings;
- the 86,400-second Request and 2,592,000-second Review boundaries at exact exclusive instants;
- finite Evidence shortening and `PERPETUAL` behavior;
- historical verification versus explicit-`observed_at` recorded-window behavior;
- strict JSON duplicate, BOM, non-finite, coercion, unknown-field and stale-ID rejection;
- AST proof of no filesystem, wall-clock, network, Provider, Runtime, entitlement,
  authorization, registry, ledger or v1 rights/revision dependency; and
- byte locks for all 57 old Schemas and exactly five new public Schemas.

## Explicit prohibitions

PR1 must not:

- read, copy, hash or embed any current real private Pack, media, Evidence, identity record,
  review, PairCheck, Request, Instruction, Decision or Manifest;
- create a CLI, filesystem loader, trusted-local workspace, draft, finalizer or output artifact;
- mutate one Review file progressively across the three stages;
- select a Provider, model, account, region, operation, price or request fingerprint;
- interpret `20`, `450`, a PASS, a Manifest or a Plan as authorization;
- read a Key, network, environment-selected time or mutable registry;
- touch Provider, Runtime, Worker, PostgreSQL, Temporal, Ark, ledger or migration code;
- call a v1 rights, qualification or real-revision derivation path;
- upload, POST, purchase, recharge, claim a trial, generate or publish; or
- imply that digest-reference inequality authenticates two humans.

## Consequences

The project gains a deterministic bridge from one exact verified Manifest closure to one exact
offline design candidate, followed by one auditable Maker/Checker Review Record. The bridge is
usable by a two-person team without erasing the responsibility chain.

The cost is five new public Schemas, explicit reconstruction of the complete closure at each
accepted boundary and a requirement to design later operational and freshness controls
separately. These costs are intentional. The v2.6 result remains a planning and review fact, not
production permission.

The only positive transition created by this ADR is:

```text
verified Manifest closure
  -> zero-authority offline Use Plan
  -> PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY
  -> eligible_for_separate_provider_proposal=true
```

It creates no transition to Provider approval, generation, execution or publication.
