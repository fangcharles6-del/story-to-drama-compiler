# SDC-ADR-044: Generated Reference Rights Manifest and Current-Status Evidence Boundary

- Status: Accepted
- Date: 2026-08-29
- Depends on: SDC-ADR-031 through SDC-ADR-037 / Fresh Status Evidence v3.0 patterns
- Reference-Prompt dependency: SDC-ADR-042 / Character and Scene Reference Prompt Compiler Input
  Boundary
- Candidate/Qualification dependency: SDC-ADR-043 / Generated Reference Candidate Provenance and
  Qualification Boundary
- Baseline: `a3a200bab2f70203d3cdc743054eb20f035f91b2`
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: explicit finite first-party synthetic documents, retained-record digests and local
  bytes only
- Network/spend boundary: zero network calls, zero credential reads, zero Provider requests, zero
  authorized Attempts and zero authorized cost

## Context

SDC-ADR-042 defines one deterministic offline character-or-scene reference Prompt Artifact.
SDC-ADR-043 and its merged R1 implementation then define four immutable generated-reference
documents:

1. one caller-asserted Provider Attempt Outcome;
2. one `CAPTURED_UNQUALIFIED` Candidate bound to one exact PNG occurrence;
3. one finite Qualification Request over ten exact retained evidence documents; and
4. one immutable historical Qualification Decision over fifteen fixed gates.

A positive ADR-043 Decision means only:

```text
PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW
```

It does not create a Rights Manifest, prove current status, promote an asset or authorize Provider
input. The Candidate remains `CAPTURED_UNQUALIFIED` and every authority field remains false or
zero.

At this ADR's baseline, `sdc.schemas.MODELS` contains exactly 76 entries. Entries 72 through 75 are
the ADR-043 Outcome, Candidate, Qualification Request and Qualification Decision. There is no
generated-specific Rights Manifest, current-status Source Observation, current-status Evidence
Record, as-of Receipt or promotion contract.

The two committed ADR-043 positive known-answer Decisions are historical synthetic fixtures. Their
exclusive qualification deadlines are `2026-08-02T11:00:00Z` and
`2026-08-04T11:00:00Z`. They are expired at this ADR's date. They cannot be renewed, reinterpreted
as current eligibility or used as positive inputs to a new Rights Manifest.

The imported-real-asset types cannot close this gap:

- `CreativeSampleRealAssetRightsManifestV2` binds an imported 14-member Pack and the
  `ASSET_INTAKE_ONLY` Qualification scope;
- `FreshStatusSubjectClosureV1` binds an imported Pack, that real-asset Manifest, one Use Plan and
  one Use Scope Review Record; and
- the real-asset Fresh Status family has released subject, policy, digest and Schema meanings that
  cannot be broadened into generated-reference unions.

SDC-ADR-031 through SDC-ADR-037 are therefore implementation-pattern evidence only. Their explicit
finite evidence sets, append-only chains, Maker/Checker separation, replay layers, half-open time
windows, limitation codes and historical Receipt semantics are useful. Their public types, subject
closure, policy values and digest domains are not reusable for generated-reference media.

SDC-ADR-043 requires a future generated Rights Manifest and a future append-only current-status
boundary. It also contains wording that the Manifest must bind the current-status closure used by
a consumer while separately allowing the Manifest to be assessed later. A direct implementation
of both directions would create a digest cycle. This Proposed ADR resolves that ambiguity before
any Contract or BUILD work.

## Decision summary

This Proposed decision recommends a generated-specific, offline, zero-authority Rights and
current-status boundary with this strict order:

1. revalidate the exact ADR-042 Artifact and complete ADR-043 Outcome, Candidate, Request and
   positive unexpired Decision closure;
2. prepare one immutable Manifest review payload;
3. bind one retained Manifest Maker action and one retained Manifest Checker action to that payload;
4. create one immutable generated Rights Manifest only after every fixed Rights gate passes;
5. create a generated current-status subject closure that binds the completed Manifest;
6. admit append-only generated current-status Source Observations over that subject;
7. compile one finite Request, Instruction, Decision and Evidence Record under a fixed nine-category
   policy;
8. freshly replay the complete explicitly supplied observation chains at one exact `as_of`; and
9. create one persistent historical Receipt from that same-call replay.

The Manifest never embeds or hashes a later status subject, Record, Result or Receipt. The status
subject binds the exact Manifest. A later consumer must jointly supply and revalidate the exact
Manifest and exact current-status closure. This is the only permitted interpretation of the
SDC-ADR-043 consumer-binding requirement if this ADR is accepted.

If accepted, this ADR narrowly supersedes only two SDC-ADR-043 statements whose implementation
details were deferred to this boundary:

1. the Rights Manifest interface item requiring the Manifest itself to bind the consumer's
   current-status/freshness closure is replaced by the one-way joint-supply rule above; and
2. the undifferentiated statement that missing, stale, forked or incomplete observation chains all
   produce `INDETERMINATE` is replaced by the exact structural-versus-policy distinction below:
   malformed, broken, missing-predecessor or non-ancestor-closed supplied structure fails without a
   status, while stale but valid evidence, no usable evidence and structurally complete unresolved
   forks may produce `INDETERMINATE` only after successful replay.

Every other SDC-ADR-043 decision remains unchanged.

This Proposed ADR does not approve implementation. It creates no Contract, Schema, Manifest,
Observation, status result, Receipt or promoted asset.

## Proposed acceptance record and implementation gate

Acceptance of this ADR would explicitly accept these six trade-offs:

1. a one-way `Manifest -> status subject -> Record -> Receipt` digest DAG rather than embedding a
   current-status Receipt in the Manifest;
2. a finite Manifest V1 validity window of at most 86,400 seconds rather than perpetual or
   automatically renewable generated rights status;
3. a five-value resolver whose fixed precedence is
   `EXPIRED > REVOKED > HELD > INDETERMINATE > CURRENT` and whose `CURRENT` result is limited to one
   exact finite supplied evidence closure at one exact `as_of`;
4. seven separately registered top-level Contracts, preserving formal status
   Request/Instruction/Decision separation rather than compressing them into inline data;
5. continued prohibition of promotion, Provider input and Runtime integration after this boundary;
   and
6. structural and replay invalidity fails without a status rather than being represented as
   `INDETERMINATE`; that value remains a successful-policy result only.

Acceptance would also approve the role rule that the Manifest Maker and Checker are distinct and
that the Manifest Checker is distinct from the ADR-043 Qualification qualifier. Retained identity
records establish only deterministic record separation; they do not authenticate a real person.

No BUILD may begin merely because this document exists or is later accepted. A separate explicit
BUILD approval, new clean `codex/` branch, synthetic known-answer review and Draft PR are required.

## Frozen compatibility boundary

This Proposed decision and any later conforming implementation must not change the behavior,
serialized value, Schema or deterministic identity of:

- `compile_story` or any v1 product;
- `compile_creative_sample` or any Creative Sample v2 product;
- `CreativeSampleSpec`, `CreativeSampleCompilation`, `NIRV2`, `PIRV2`,
  `StoryboardShotV2`, `GenerationJob`, `JobGraph` or `AssemblyPlan`;
- `CharacterAssetVersion`, `CharacterBible`, `SceneAssetVersion`, `SceneBible` or
  `CharacterAssetBinding`;
- any Visual Prompt Profile, Catalog, Snapshot, render input, Prompt, Prompt Receipt or Catalog
  Receipt projection;
- `CreativeSampleReferenceVisualPromptCompileRequestV1` or
  `CreativeSampleReferenceVisualPromptArtifactV1`;
- any ADR-043 Outcome, Candidate, Qualification Request or Qualification Decision field,
  projection, domain, ID or Schema;
- Candidate state `CAPTURED_UNQUALIFIED`;
- existing `rights_manifest_embedded=false`,
  `current_status_assessment_embedded=false` and `eligible_for_asset_promotion=false` values;
- any v1 or Creative Sample v2 Prompt, ID, idempotency key or frozen regression byte;
- all current 76 committed Schema blobs and the order of `MODELS[:76]`;
- all 14 fixtures committed before an ADR-044 BUILD;
- imported-real-asset Qualification, Rights Manifest, Use Plan or Fresh Status semantics;
- Runtime, Temporal, PostgreSQL, Provider, Retry, QC or publication behavior; or
- `CharacterAssetVersion` and `SceneAssetVersion` provenance
  `IMPORTED_APPROVED_MEDIA`.

No existing class, enum, literal or optional field may be broadened to carry generated Rights or
current-status semantics. The first implementation must be append-only.

## Terminology and lifecycle

The following values remain distinct:

1. **Reference Prompt Artifact**: deterministic offline Prompt compilation evidence.
2. **Provider Attempt Outcome**: caller-asserted immutable evidence about one historical or
   synthetic Attempt.
3. **Generated Reference Candidate**: one exact PNG occurrence with unqualified generated
   provenance.
4. **Qualification Decision**: a finite historical human decision that may route one Candidate to
   a separate Manifest review.
5. **Manifest review payload**: the deterministic pre-action projection over the exact closure,
   complete review evidence set and Maker-proposed rights scope. It contains no Checker gate
   result, Checker basis or final Manifest identity.
6. **Generated Rights Manifest**: one immutable positive historical review closure. It records a
   bounded reviewed scope but grants no rights or execution authority.
7. **Current-status Source Observation**: append-only bounded evidence about one Manifest subject
   at explicit times.
8. **Current-status Evidence Record**: one complete Request/Instruction/Decision closure over a
   finite explicit observation set.
9. **As-of assessment Result**: a non-persistent same-call replay result with private verifier
   provenance.
10. **As-of Receipt**: persistent historical process evidence for that exact replay and exact
    `as_of`. It is not an approval or present-time assertion.
11. **Promotion**: a future atomic decision over a qualified, rights-closed and current-status
    verified Candidate. No promotion type is defined here.

Qualification is not a Rights Manifest. A Rights Manifest is not current-status proof.
`CURRENT` is not promotion. None of these values is Provider input, Runtime authority,
publication permission, retention permission or training permission.

## Acyclic subject and digest DAG

The proposed identity graph is exactly one-way:

```text
ADR-042 Artifact
  -> ADR-043 Provider Attempt Outcome
  -> ADR-043 Candidate
  -> ADR-043 Qualification Request
  -> positive, unexpired ADR-043 Qualification Decision
  -> Manifest review core payload
  -> retained Manifest Maker action
  -> retained Manifest Checker action
  -> Generated Rights Manifest
  -> Generated Current-Status Subject Closure
  -> append-only Source Observations and chains
  -> retained Status Preparer action
  -> Current-Status Request
  -> retained Status Checker action
  -> Current-Status Instruction
  -> Current-Status Decision
  -> Current-Status Evidence Record
  -> non-persistent explicit-as_of Result
  -> persistent historical Receipt
```

The Manifest must not contain a current-status subject ID, Record ID, Receipt ID, status value or
any corresponding digest. The current-status subject closure must contain the Manifest's complete
ID/SHA anchor.

The Manifest Checker action must not bind the final Manifest ID or SHA because the final Manifest
binds the Checker action SHA. Instead:

1. a domain-separated `manifest_review_payload_sha256` binds the complete pre-action review
   projection;
2. the Maker action binds that payload;
3. the Checker action binds the payload and exact Maker action SHA; and
4. the final Manifest binds the payload, Maker action SHA and Checker action SHA.

The final Manifest semantic projection excludes only its own `manifest_id` and
`manifest_sha256`. It includes no later status digest.

No optional empty digest, null self-reference, placeholder status, second-pass mutation or
incidental serialization may be used to evade this DAG.

## Generated Rights Manifest admission boundary

A future pure Manifest builder and verifier must receive exact typed values and exact bytes, not
copied digest strings:

- one exact ADR-042 Artifact;
- one exact ADR-043 Provider Attempt Outcome;
- one exact ADR-043 Candidate;
- one exact ADR-043 Qualification Request;
- one exact positive ADR-043 Qualification Decision;
- the exact raw PNG bytes represented by the Candidate;
- the exact ten retained Qualification evidence documents;
- the exact retained Qualification preparer and qualifier identity/action records;
- the exact fixed-order Manifest review evidence documents;
- one exact Maker-proposed rights scope;
- one retained Manifest Maker identity reference and action record;
- one retained Manifest Checker identity reference and action record; and
- one explicit `manifest_at`.

Every upstream object must be revalidated as its exact public type and fully reconstructed from the
supplied closure. The operation must rehash the PNG, retained documents and action records. A
Candidate ID, Decision eligibility Boolean, filename or copied SHA is never sufficient.

The Decision must retain:

```text
qualification_scope=GENERATED_REFERENCE_CANDIDATE_INTAKE_ONLY
decision=PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW
eligible_for_separate_generated_rights_manifest_review=true
status=QUALIFICATION_COMPLETE
qualification_performed=true
rights_manifest_embedded=false
current_status_assessment_embedded=false
eligible_for_asset_promotion=false
```

Every ADR-043 zero-authority value must still be exact. A rejected, indeterminate or expired
Decision fails closed.

## Manifest time and validity

`manifest_at` is one caller-supplied canonical whole-second UTC value. It has no default and no
wall-clock, filesystem-time, environment, timezone or network fallback.

The builder must enforce:

```text
decision_at <= manifest_at < qualification_valid_until
```

Equality with `qualification_valid_until` is expired and produces no Manifest. A new Manifest after
expiry requires a new exact Qualification Request and Decision. No operation may renew, extend or
edit the historical Decision.

V1 proposes one finite Manifest interval:

```text
[manifest_at, manifest_valid_until)
```

`manifest_valid_until` is uniquely derived as the earliest of:

- `manifest_at + 86400 seconds`;
- every finite `effective_until` and `evidence_valid_until` in these exact current-facing
  review-evidence categories:
  - `INPUT_TEXT_AND_MEDIA_RIGHTS`;
  - `OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE`;
  - `LIKENESS_PRIVACY_AND_SENSITIVE_DATA`;
  - `BRAND_AND_PROTECTED_CONTENT`;
  - `TERRITORY_DURATION_AND_ALLOWED_USE`;
  - `RETENTION_AND_DELETION_OBLIGATIONS`; and
  - `TRAINING_USE_PROHIBITION`; and
- the Checker's finite `reviewed_scope_valid_until`.

Every listed current-facing evidence record must satisfy
`observed_at <= manifest_at`, `effective_from <= manifest_at < effective_until` and
`manifest_at < evidence_valid_until`, with `PERPETUAL` admitted only as an evidence upper bound and
omitted from the minimum. `reviewed_scope_valid_until` is always a finite canonical UTC second and
must be later than `manifest_at`. If every evidence upper bound is `PERPETUAL`, the minimum still
contains `manifest_at + 86400 seconds` and `reviewed_scope_valid_until`. Therefore
`manifest_at < manifest_valid_until` is always required and the result is unique.

The derived value is never caller-overridable and never `PERPETUAL` in V1. Historical
`SUBMISSION_TIME_AUTHORIZATION` and `PROVIDER_TERMS_AT_SUBMISSION` records must have been effective
at submission but do not independently shorten the Manifest unless a separately listed
current-facing record also establishes that ongoing bound.

Qualification expiry after a valid Manifest was created does not mutate or erase the historical
Manifest. It also does not make the Manifest current. Current status is determined only through
the later generated current-status closure within the Manifest's own finite interval.

No later `as_of`, Observation, Receipt or human action may extend `manifest_valid_until`. An expired
Manifest requires a new Qualification and Manifest review; it is never refreshed in place.

## Manifest Maker/Checker separation

The Manifest review uses one retained Maker record and one retained Checker record.

- The Maker prepares the exact review payload and complete evidence set.
- The Checker reviews that exact payload and the Maker action.
- The Checker supplies the human results and bases for gates two through ten plus the final reviewed
  scope. The compiler derives gates one and eleven. The Checker action carries the resulting exact
  full eleven-gate tuple, but cannot override either compiler-derived result. None of those values
  is part of the Maker-authored payload.
- The compiler derives whether the positive Manifest disposition is available.
- The Maker and Checker semantic identities must differ.
- The Manifest Checker semantic identity must differ from the ADR-043 Qualification qualifier.
- The Manifest Maker may equal the ADR-043 qualifier, but can never equal the Manifest Checker.

Identity separation is evaluated over the retained semantic tuple
`(identity_namespace, identity_ref)`, not merely SHA inequality. Retained records are privacy
minimized and remain outside portable Contracts. Their digests prove exact supplied bytes and
record separation only; they do not prove legal identity, employment, professional status or
authority.

If any Manifest gate is `FAIL` or `INDETERMINATE`, no Manifest is created. The negative or
indeterminate retained action remains external evidence and is not converted into a positive
portable Manifest.

The retained action records have closed projections:

```text
Manifest Maker action:
  document_profile=sdc.generated-reference-rights-manifest-review-preparation-action.v1
  action=PREPARED_GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW
  actor_identity_ref_sha256
  manifest_review_payload_sha256
  prepared_at

Manifest Checker action:
  document_profile=sdc.generated-reference-rights-manifest-review-checker-action.v1
  action=RECORDED_GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW
  actor_identity_ref_sha256
  manifest_review_payload_sha256
  maker_action_sha256
  reviewed_at
  gate_results
  reviewed_rights_scope
  disposition
```

`decision_at <= prepared_at <= reviewed_at` and `reviewed_at == manifest_at` are required. The
Checker action contains neither `manifest_id` nor `manifest_sha256`. Maker and Checker action SHAs
are undomained raw SHA-256 values over their exact retained canonical bytes; neither retained
record contains its own raw SHA. The final Manifest copies the Checker gate results and reviewed
scope exactly and binds both action SHAs.

The Checker's `reviewed_rights_scope` territory and allowed-use tuples must be equal to or a strict
canonical subset of the Maker proposal, and its reviewed-scope deadline cannot exceed the proposed deadline. The Checker
cannot broaden scope, add evidence after the Maker action or edit the payload. A narrower positive
scope is copied exactly into the Manifest; a broader or differently anchored scope fails.

The review payload is a closed private projection, not an eighth Contract. In exact projection
order it contains:

```text
manifest_review_payload_profile=sdc.generated-reference-rights-manifest-review-payload.v1
manifest_policy_id
manifest_policy_version
manifest_policy_document_sha256
reference_prompt_artifact_sha256
provider_attempt_outcome_id
provider_attempt_outcome_sha256
candidate_id
candidate_sha256
qualification_request_id
qualification_request_sha256
qualification_decision_id
qualification_decision_sha256
subject_id
asset_purpose
profile_id
profile_version
profile_sha256
catalog_version
catalog_sha256
render_input_sha256
prompt_sha256
prompt_size_bytes
prompt_render_receipt_sha256
media_content_sha256
media_size_bytes
media_technical_record_sha256
provider
model
provider_region
provider_terms_snapshot_id
provider_terms_snapshot_sha256
submitted_at
qualification_decision_at
qualification_valid_until
manifest_at
review_evidence_refs
proposed_rights_scope
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
```

`review_evidence_refs` is exactly nine entries and `proposed_rights_scope` uses the closed inline
definitions below. The payload has no Checker identity, gate result, basis, final reviewed scope,
action SHA, Manifest ID or Manifest SHA. Retained action bytes are not portable Contracts or Schema
Registry models.

The final Manifest retains both `proposed_rights_scope` and `reviewed_rights_scope` plus the same
nine evidence references. A verifier jointly supplies the exact upstream/evidence/action bytes and
reconstructs the private payload from the Manifest's proposed scope and references; it must recover
the exact `manifest_review_payload_sha256`. The reviewed scope must equal or narrow that retained
proposal. A copied payload digest without successful reconstruction is invalid.

All Manifest and status human identity-reference records reuse this exact retained profile:

```text
document_profile=sdc.privacy-minimized-human-reference.v1
identity_namespace
identity_ref
```

The identity record is 1..16,384 canonical bytes. Every portable `*_identity_ref_sha256` is the
undomained raw SHA-256 of one exact supplied record. Every `*_action_sha256` is the undomained raw
SHA-256 of its corresponding exact action bytes. An action's `actor_identity_ref_sha256` must equal
the raw SHA of its exact identity record. No retained record contains its own raw digest.

A Source Observation instead uses this closed 1..16,384-byte source-reference profile:

```text
document_profile=sdc.privacy-minimized-source-reference.v1
source_identity_namespace
source_identity_ref
```

`source_identity_ref_sha256` is the undomained raw SHA-256 of those exact canonical bytes. It does
not authenticate a person, organization, Provider or system.

The status action records are closed as follows:

```text
Status Preparer action:
  document_profile=sdc.generated-reference-current-status-request-preparation-action.v1
  action=PREPARED_GENERATED_REFERENCE_CURRENT_STATUS_REQUEST
  actor_identity_ref_sha256
  subject_closure_sha256
  policy_document_sha256
  requested_at
  request_valid_until
  observation_target_refs
  request_basis

Status Checker action:
  document_profile=sdc.generated-reference-current-status-decision-checker-action.v1
  action=RECORDED_GENERATED_REFERENCE_CURRENT_STATUS_DECISION
  actor_identity_ref_sha256
  request_sha256
  evaluated_at
  category_results
  checker_basis
  status_valid_until
  recorded_status
```

The Request copies the Preparer identity/action SHA anchors. The Instruction copies those anchors
and the Checker identity/action SHA anchors. The status Checker action contains no Instruction or
Decision ID/SHA; the Instruction binds the completed action, and the Decision later binds the
Instruction. The compiler derives `category_results`, `status_valid_until` and `recorded_status`;
the Checker action carries exact non-overridable copies and contributes only its identity plus
`checker_basis`. Exact copied fields must agree. Within each Maker/Checker or Preparer/Checker pair,
the two identity records, two action records and applicable evidence records have pairwise distinct
raw digests and cannot alias a formal semantic digest, Prompt digest or media digest.

## Frozen Manifest review policy

The Proposed V1 Manifest gate order is:

```text
PROVENANCE_AND_CANDIDATE_CLOSURE
SUBMISSION_TIME_AUTHORIZATION
PROVIDER_TERMS_AT_SUBMISSION
INPUT_TEXT_AND_MEDIA_RIGHTS
OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE
LIKENESS_PRIVACY_AND_SENSITIVE_DATA
BRAND_AND_PROTECTED_CONTENT
TERRITORY_DURATION_AND_ALLOWED_USE
RETENTION_AND_DELETION_OBLIGATIONS
TRAINING_USE_PROHIBITION
REVIEWER_ROLE_AND_EVIDENCE_CLOSURE
```

Every gate must be `PASS`. The only positive Manifest disposition is:

```text
PASS_FOR_SEPARATE_GENERATED_CURRENT_STATUS_ASSESSMENT
```

The gate order is part of the semantic projection. Prompt constraints, QC expectations, Catalog
`qualification`/`rights`/`compatibility` metadata and Provider compatibility observations cannot
satisfy a Manifest gate.

The Proposed Manifest policy projection is:

```json
{
  "action_time_rule": "DECISION_AT_LE_MAKER_PREPARED_AT_LE_MANIFEST_AT_EQ_CHECKER_REVIEWED_AT",
  "compiler_gate_basis": [
    {
      "basis": "COMPILER_REVALIDATED_EXACT_ADR042_ADR043_CLOSURE",
      "gate_ordinal": 0
    },
    {
      "basis": "COMPILER_REVALIDATED_DISTINCT_ROLE_AND_ACTION_CLOSURE",
      "gate_ordinal": 10
    }
  ],
  "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
  "manifest_max_age_seconds": 86400,
  "manifest_outcome": "PASS_FOR_SEPARATE_GENERATED_CURRENT_STATUS_ASSESSMENT",
  "manifest_review_gate_order": [
    "PROVENANCE_AND_CANDIDATE_CLOSURE",
    "SUBMISSION_TIME_AUTHORIZATION",
    "PROVIDER_TERMS_AT_SUBMISSION",
    "INPUT_TEXT_AND_MEDIA_RIGHTS",
    "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    "BRAND_AND_PROTECTED_CONTENT",
    "TERRITORY_DURATION_AND_ALLOWED_USE",
    "RETENTION_AND_DELETION_OBLIGATIONS",
    "TRAINING_USE_PROHIBITION",
    "REVIEWER_ROLE_AND_EVIDENCE_CLOSURE"
  ],
  "manifest_review_payload_profile": "sdc.generated-reference-rights-manifest-review-payload.v1",
  "manifest_review_evidence_category_order": [
    "SUBMISSION_TIME_AUTHORIZATION",
    "PROVIDER_TERMS_AT_SUBMISSION",
    "INPUT_TEXT_AND_MEDIA_RIGHTS",
    "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    "BRAND_AND_PROTECTED_CONTENT",
    "TERRITORY_DURATION_AND_ALLOWED_USE",
    "RETENTION_AND_DELETION_OBLIGATIONS",
    "TRAINING_USE_PROHIBITION"
  ],
  "manifest_gate_evidence_mapping": [
    {
      "evidence_category": null,
      "evidence_ordinal": null,
      "gate": "PROVENANCE_AND_CANDIDATE_CLOSURE",
      "gate_ordinal": 0,
      "source": "COMPILER_DERIVED"
    },
    {
      "evidence_category": "SUBMISSION_TIME_AUTHORIZATION",
      "evidence_ordinal": 0,
      "gate": "SUBMISSION_TIME_AUTHORIZATION",
      "gate_ordinal": 1,
      "source": "HUMAN_REVIEW_EVIDENCE"
    },
    {
      "evidence_category": "PROVIDER_TERMS_AT_SUBMISSION",
      "evidence_ordinal": 1,
      "gate": "PROVIDER_TERMS_AT_SUBMISSION",
      "gate_ordinal": 2,
      "source": "HUMAN_REVIEW_EVIDENCE"
    },
    {
      "evidence_category": "INPUT_TEXT_AND_MEDIA_RIGHTS",
      "evidence_ordinal": 2,
      "gate": "INPUT_TEXT_AND_MEDIA_RIGHTS",
      "gate_ordinal": 3,
      "source": "HUMAN_REVIEW_EVIDENCE"
    },
    {
      "evidence_category": "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
      "evidence_ordinal": 3,
      "gate": "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
      "gate_ordinal": 4,
      "source": "HUMAN_REVIEW_EVIDENCE"
    },
    {
      "evidence_category": "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
      "evidence_ordinal": 4,
      "gate": "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
      "gate_ordinal": 5,
      "source": "HUMAN_REVIEW_EVIDENCE"
    },
    {
      "evidence_category": "BRAND_AND_PROTECTED_CONTENT",
      "evidence_ordinal": 5,
      "gate": "BRAND_AND_PROTECTED_CONTENT",
      "gate_ordinal": 6,
      "source": "HUMAN_REVIEW_EVIDENCE"
    },
    {
      "evidence_category": "TERRITORY_DURATION_AND_ALLOWED_USE",
      "evidence_ordinal": 6,
      "gate": "TERRITORY_DURATION_AND_ALLOWED_USE",
      "gate_ordinal": 7,
      "source": "HUMAN_REVIEW_EVIDENCE"
    },
    {
      "evidence_category": "RETENTION_AND_DELETION_OBLIGATIONS",
      "evidence_ordinal": 7,
      "gate": "RETENTION_AND_DELETION_OBLIGATIONS",
      "gate_ordinal": 8,
      "source": "HUMAN_REVIEW_EVIDENCE"
    },
    {
      "evidence_category": "TRAINING_USE_PROHIBITION",
      "evidence_ordinal": 8,
      "gate": "TRAINING_USE_PROHIBITION",
      "gate_ordinal": 9,
      "source": "HUMAN_REVIEW_EVIDENCE"
    },
    {
      "evidence_category": null,
      "evidence_ordinal": null,
      "gate": "REVIEWER_ROLE_AND_EVIDENCE_CLOSURE",
      "gate_ordinal": 10,
      "source": "COMPILER_DERIVED"
    }
  ],
  "manifest_scope": "GENERATED_REFERENCE_RIGHTS_REVIEW_ONLY",
  "manifest_valid_until_rule": "MIN_MANIFEST_AT_PLUS_86400_CURRENT_EVIDENCE_AND_REVIEWED_SCOPE_END",
  "policy_id": "sdc.generated-reference-rights-manifest-policy",
  "policy_version": "1.0.0",
  "qualification_required_decision": "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
  "qualification_scope": "GENERATED_REFERENCE_CANDIDATE_INTAKE_ONLY",
  "required_gate_result": "PASS",
  "resource_limits": {
    "allowed_use_codes_max": 32,
    "basis_code_points_max": 1000,
    "generic_container_items_max": 64,
    "identity_reference_document_bytes_max": 16384,
    "json_depth_max": 32,
    "manifest_document_bytes_max": 262144,
    "manifest_review_payload_bytes_max": 262144,
    "retained_action_document_bytes_max": 262144,
    "review_evidence_document_bytes_max": 262144,
    "territory_codes_max": 64,
    "top_level_object_members_max": 128
  },
  "review_action_projection_rule": "PAYLOAD_THEN_MAKER_THEN_CHECKER_NO_FINAL_MANIFEST_SHA",
  "reviewed_scope_basis_gate_mapping": [
    {
      "field": "output_copyright_and_commercial_scope_basis",
      "gate_ordinal": 4
    },
    {
      "field": "likeness_privacy_and_sensitive_data_basis",
      "gate_ordinal": 5
    },
    {
      "field": "brand_and_protected_content_basis",
      "gate_ordinal": 6
    },
    {
      "field": "retention_and_deletion_basis",
      "gate_ordinal": 8
    },
    {
      "field": "training_use_prohibition_basis",
      "gate_ordinal": 9
    }
  ],
  "reviewer_rule": "MANIFEST_MAKER_DISTINCT_FROM_CHECKER_AND_CHECKER_DISTINCT_FROM_QUALIFIER",
  "scope_code_order": "STRICT_ASCENDING_UTF8_BYTES_UNIQUE",
  "scope_rule": "CHECKER_REVIEWED_SCOPE_SUBSET_OF_MAKER_PROPOSED_SCOPE",
  "time_rule": "DECISION_AT_LE_MANIFEST_AT_LT_QUALIFICATION_VALID_UNTIL",
  "zero_authority": true
}
```

Under the ADR-040 compact canonical JSON codec, the projection is exactly 4,686 UTF-8 bytes and its
raw SHA-256 is:

```text
7d9f72f134b5be5f68bb55f25ee898736bd84d39b2ff6917e0e2ecab447f8f16
```

No latest-policy lookup, environment override or fallback is permitted.

## Generated Rights Manifest projection

The future Manifest uses the exact closed field projection below. Its semantic coverage includes:

- Schema version, document type and Manifest scope;
- Manifest policy ID, version and exact policy digest;
- Manifest review payload SHA;
- Artifact SHA;
- Outcome ID/SHA;
- Candidate ID/SHA;
- Qualification Request ID/SHA;
- Qualification Decision ID/SHA;
- subject ID and asset purpose;
- exact Profile, Catalog, render-input, Prompt and Prompt Receipt SHA anchors;
- PNG raw SHA, size and technical-record SHA;
- Provider, model, region and exact submission-time terms snapshot anchors;
- Decision time and exclusive Qualification deadline;
- `manifest_at` and `manifest_valid_until`;
- fixed-order Rights evidence references and eleven fixed gate results;
- Maker-proposed and Checker-reviewed territory, duration and allowed-use scope;
- reviewed output copyright/commercial, likeness/privacy, brand/protected-content,
  retention/deletion and training-use conclusions;
- Maker and Checker retained identity/action SHA anchors;
- `rights_review_performed=true`;
- `eligible_for_separate_generated_current_status_review=true`;
- `current_status_assessment_embedded=false`;
- `status=GENERATED_RIGHTS_MANIFEST_RECORDED`; and
- the complete zero-authority surface.

This list is a semantic coverage summary, not an extension point. Field names, inline definitions
and cardinalities are exclusively the closed projection later in this ADR.

The two positive Booleans record that one scoped compiler/review boundary completed and may be
routed to a separate status review. They grant no legal right, Provider capability, promotion or
execution authority.

## Current-status subject closure

The generated current-status subject closure is a closed inline definition, not a top-level
Registry model. It must bind:

- closure profile and policy identity;
- closure ID and full semantic SHA;
- Artifact SHA;
- Outcome ID/SHA;
- Candidate ID/SHA;
- Qualification Request ID/SHA;
- Qualification Decision ID/SHA;
- Manifest ID/SHA;
- subject ID and asset purpose;
- exact PNG raw SHA;
- `manifest_at` and `manifest_valid_until`.

Every digest must be distinct except equalities explicitly required by an upstream released
projection. The closure ID is derived from its full domain-separated SHA. The Manifest never binds
this closure in reverse.

## Current-status categories and claim values

The Proposed policy uses these nine categories in exact order:

```text
HOLD_ACTIVE
REVOCATION_EFFECTIVE
COMPLAINT_OPEN
DISPUTE_OPEN
RIGHTS_BASIS_CURRENT
IDENTITY_BINDING_CURRENT
PROVIDER_TERMS_COMPATIBILITY_CURRENT
RETENTION_DELETION_COMPLIANCE_CURRENT
TRAINING_USE_PROHIBITION_CURRENT
```

The first four are adverse categories. The final five are positive currentness predicates.

Each category uses one of:

```text
PRESENT
ABSENT_WITH_EVIDENCE
UNKNOWN
NOT_ASSESSED
CONFLICT
```

For an eventual `CURRENT` result:

- every adverse category must be `ABSENT_WITH_EVIDENCE`;
- every positive category must be `PRESENT`;
- every required Observation and complete ancestor chain must be explicitly supplied;
- all category evidence must be valid at the exact evaluation time;
- every branch must be reconciled without selecting a favorable head; and
- the Record and Manifest windows must remain open.

Absence of an Observation is not `ABSENT_WITH_EVIDENCE`. A generic policy-compatibility record
cannot substitute for the separate Provider terms, retention/deletion or training predicates.

`SUPERSEDED`, a confirmed prohibited-training event or a confirmed retention/deletion violation
must produce explicit `REVOCATION_EFFECTIVE=PRESENT` evidence to resolve as `REVOKED`. An unresolved
training or deletion concern requires explicit hold evidence to resolve as `HELD`; without that
evidence the result is `INDETERMINATE`. A privacy complaint maps to `COMPLAINT_OPEN`. A Provider
terms change affects `PROVIDER_TERMS_COMPATIBILITY_CURRENT` and cannot be treated as Provider
capability evidence.

Brand/protected-content and likeness/privacy conclusions remain part of the Manifest's reviewed
rights basis. Later complaints, disputes or identity changes enter the append-only status chain.

`IDENTITY_BINDING_CURRENT` concerns only the continued binding among this exact Candidate
occurrence, `subject_id`, `asset_purpose`, upstream active-asset anchors and exact PNG digest inside
the reviewed Manifest scope. It is not reviewer identity, real-person authentication, likeness
consent or a Bible promotion fact. Those remain separate evidence or later decisions.

## Source Observations and append-only chains

Each generated Source Observation must bind:

- the exact generated current-status subject closure;
- one category and claim value;
- one bounded source kind and basis/reason code;
- privacy-minimized source identity and object references;
- raw source-object SHA, size and media type;
- `source_event_at`, `observed_at`, `valid_from` and `valid_until`;
- all mandatory limitation codes; and
- one `GENESIS`, `SUCCESSOR` or `RECONCILIATION` chain link.

Observation construction receives the exact source-reference bytes and exact bounded retained
source-object bytes, rehashes both and verifies size/media type before creating the portable value.
`source_object_ref` is one bounded portable opaque ID, never a path, URL, Provider task ID or
credential. A copied source digest or locator is insufficient.

The closed `source_kind` values are:

```text
RIGHTS_HOLDER_DECLARATION
LICENSOR_DECLARATION
PROVIDER_TERMS_RECORD
INTERNAL_HOLD_RECORD
REVOCATION_NOTICE
COMPLAINT_RECORD
DISPUTE_RECORD
IDENTITY_BINDING_RECORD
RETENTION_DELETION_RECORD
TRAINING_USE_RECORD
```

The following category, basis-code and claim-value combinations are exhaustive. A caller cannot
combine a basis code with another category or claim value:

| Category | Basis code | Claim value |
| --- | --- | --- |
| `HOLD_ACTIVE` | `HOLD_IMPOSED` | `PRESENT` |
| `HOLD_ACTIVE` | `HOLD_RELEASED` | `ABSENT_WITH_EVIDENCE` |
| `REVOCATION_EFFECTIVE` | `REVOCATION_ISSUED` | `PRESENT` |
| `REVOCATION_EFFECTIVE` | `RIGHTS_REINSTATED` | `ABSENT_WITH_EVIDENCE` |
| `REVOCATION_EFFECTIVE` | `SUPERSEDED` | `PRESENT` |
| `REVOCATION_EFFECTIVE` | `RETENTION_DELETION_VIOLATION_CONFIRMED` | `PRESENT` |
| `REVOCATION_EFFECTIVE` | `TRAINING_VIOLATION_CONFIRMED` | `PRESENT` |
| `COMPLAINT_OPEN` | `COMPLAINT_RECEIVED` | `PRESENT` |
| `COMPLAINT_OPEN` | `COMPLAINT_RESOLVED` | `ABSENT_WITH_EVIDENCE` |
| `DISPUTE_OPEN` | `DISPUTE_OPENED` | `PRESENT` |
| `DISPUTE_OPEN` | `DISPUTE_RESOLVED` | `ABSENT_WITH_EVIDENCE` |
| `RIGHTS_BASIS_CURRENT` | `RIGHTS_CONFIRMED` | `PRESENT` |
| `RIGHTS_BASIS_CURRENT` | `RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED` | `ABSENT_WITH_EVIDENCE` |
| `IDENTITY_BINDING_CURRENT` | `IDENTITY_CONFIRMED` | `PRESENT` |
| `IDENTITY_BINDING_CURRENT` | `IDENTITY_EXPIRED_REVOKED_OR_SUPERSEDED` | `ABSENT_WITH_EVIDENCE` |
| `PROVIDER_TERMS_COMPATIBILITY_CURRENT` | `TERMS_COMPATIBLE` | `PRESENT` |
| `PROVIDER_TERMS_COMPATIBILITY_CURRENT` | `TERMS_CHANGED_OR_INCOMPATIBLE` | `ABSENT_WITH_EVIDENCE` |
| `RETENTION_DELETION_COMPLIANCE_CURRENT` | `RETENTION_DELETION_COMPLIANT` | `PRESENT` |
| `RETENTION_DELETION_COMPLIANCE_CURRENT` | `RETENTION_DELETION_UNRESOLVED_OR_NONCOMPLIANT` | `ABSENT_WITH_EVIDENCE` |
| `TRAINING_USE_PROHIBITION_CURRENT` | `TRAINING_PROHIBITION_CONFIRMED` | `PRESENT` |
| `TRAINING_USE_PROHIBITION_CURRENT` | `TRAINING_UNRESOLVED_OR_VIOLATED` | `ABSENT_WITH_EVIDENCE` |

Every category also permits `INITIAL_STATUS_UNKNOWN`, `INITIAL_STATUS_NOT_ASSESSED`,
`STATUS_RECONFIRMED`, `STATUS_BECAME_UNKNOWN`, `CONFLICT_IDENTIFIED` and
`CONFLICT_RECONCILED` only under the transition matrix below. The source kind must be semantically
applicable to its frozen basis code; exact applicability is part of the policy and not caller text.

Applicability is closed as follows: hold codes use `INTERNAL_HOLD_RECORD`; complaint and dispute
codes use their corresponding record kinds; identity codes use `IDENTITY_BINDING_RECORD`; Provider
terms codes use `PROVIDER_TERMS_RECORD`; retention codes use `RETENTION_DELETION_RECORD`; training
codes use `TRAINING_USE_RECORD`; rights-basis codes use `RIGHTS_HOLDER_DECLARATION` or
`LICENSOR_DECLARATION`; and revocation codes use `REVOCATION_NOTICE`, except the two confirmed
violation codes may use their corresponding retention or training record kind. The four general
unknown/conflict codes may use only a source kind already applicable to that category. The two
remaining generic codes, `STATUS_RECONFIRMED` and `CONFLICT_RECONCILED`, use the already frozen
chain-scope source kind. No other pair is valid.

The transition matrix is exact:

```text
GENESIS
  PRESENT                  -> category-specific present basis
  ABSENT_WITH_EVIDENCE     -> category-specific absent basis
  UNKNOWN                  -> INITIAL_STATUS_UNKNOWN
  NOT_ASSESSED             -> INITIAL_STATUS_NOT_ASSESSED
  CONFLICT                 -> CONFLICT_IDENTIFIED

SUCCESSOR
  NOT_ASSESSED -> UNKNOWN                         -> INITIAL_STATUS_UNKNOWN
  NOT_ASSESSED/UNKNOWN -> PRESENT                 -> category-specific present basis
  NOT_ASSESSED/UNKNOWN -> ABSENT_WITH_EVIDENCE    -> category-specific absent basis
  PRESENT -> PRESENT                              -> STATUS_RECONFIRMED
  ABSENT_WITH_EVIDENCE -> ABSENT_WITH_EVIDENCE    -> STATUS_RECONFIRMED
  PRESENT -> ABSENT_WITH_EVIDENCE                 -> category-specific absent basis
  ABSENT_WITH_EVIDENCE -> PRESENT                 -> category-specific present basis
  PRESENT/ABSENT_WITH_EVIDENCE -> UNKNOWN         -> STATUS_BECAME_UNKNOWN
  any non-CONFLICT claim -> CONFLICT              -> CONFLICT_IDENTIFIED

SUCCESSOR REJECTION
  UNKNOWN -> UNKNOWN
  every claim -> NOT_ASSESSED
  every one-parent successor from CONFLICT

RECONCILIATION WITH 2..8 HEADS
  final PRESENT/ABSENT_WITH_EVIDENCE/UNKNOWN       -> CONFLICT_RECONCILED
  final CONFLICT                                   -> CONFLICT_IDENTIFIED
  final NOT_ASSESSED                               -> reject
```

The category-specific basis in this matrix is one exact allowed basis/source-kind pair from the
earlier table. Where a category has multiple present bases, the exact supplied evidence meaning
selects one; no default, priority or fallback basis exists.
`STATUS_RECONFIRMED` requires an unchanged determined claim. `CONFLICT_RECONCILED` is valid only on
a multi-head reconciliation; it records resolution procedure, while the final category claim and
all branch heads remain explicit. No single-parent successor can escape a prior conflict.

Observation validity is a non-empty half-open interval of at most 86,400 seconds. Source event time
cannot follow observation time. A malformed value, broken/missing predecessor, non-ancestor-closed
set, aliased identity, cycle or noncanonical value fails closed without a status. A structurally
valid Observation that is outside its validity interval at `evaluated_at` is unusable for that
assessment and contributes `NOT_ASSESSED`, not an operation failure. A structurally complete but
unreconciled multi-head chain contributes `CONFLICT`.

A successor binds one complete predecessor. A reconciliation binds two through eight complete
branch heads in strict ascending `(observation_id, observation_sha256, chain_sha256)` order. No replay operation may scan storage, select `latest`, select
`best`, discard an unfavorable branch or infer a missing predecessor.

New evidence is appended. Candidate, Qualification Decision, Manifest and existing Observations are
never edited. Releasing a hold, reinstating rights or reconciling a conflict requires a new
successor or reconciliation Observation under an exact frozen basis code.

## Current-status Request, Instruction, Decision and Evidence Record

The future Request binds:

- one exact subject closure;
- one `STATUS_PREPARER` retained identity record and exact preparation action;
- one explicit `requested_at`;
- `request_valid_until`;
- a complete canonical ordered tuple of Observation target references; and
- a bounded request basis.

Each supplied Observation must satisfy `observation.observed_at <= requested_at`. The Request
admits each exact retained Observation from its canonical bytes and compares the subject semantic
tuple, not merely a copied closure SHA. Equal digests never substitute for exact type, exact bytes
and semantic anchor revalidation.

The future Instruction binds the exact Request, repeats the subject and preparer identity/action
anchors, adds one distinct `STATUS_CHECKER` identity/action pair and one explicit `evaluated_at`,
and contains nine fixed-order category results.

The Checker cannot choose a favorable subset, supply a final five-value status or omit a category.
The compiler derives all category effects, blocking/indeterminate projections, status horizon and
final status from the exact supplied closure.

The future Decision binds the exact Request and Instruction and carries:

- `evaluated_at == decision_at`;
- `status_valid_until`;
- all nine category results;
- exact adverse and indeterminate category tuples;
- one of the five frozen status values; and
- the complete zero-authority surface.

The Evidence Record embeds the exact typed Request, Instruction and Decision plus their full
semantic SHA values. It verifies one subject closure, complete module-digest chain and exact
category projection. It does not embed or discover Source Observation documents.

The Status Preparer and Checker semantic identities must differ. This proves only distinct retained
records under supplied namespaces; it does not authenticate people or authority.

Every status builder accepts the exact retained preparer/checker identity bytes, rehashes them and
requires agreement with the portable references. Role separation compares the retained semantic
tuple `(identity_namespace, identity_ref)`, not raw-SHA inequality. A copied digest, differently
typed value or alternate byte document is insufficient.

Category aggregation is deterministic after complete chain replay. For each category, the compiler
considers every Request target in that category and its freshly replayed complete chain:

1. the relied-on set contains every and only target whose complete-chain claim is not
   `NOT_ASSESSED` and whose exact half-open interval contains `evaluated_at`; no usable target may
   be omitted as redundant or unnecessary;
2. no usable target produces `NOT_ASSESSED`;
3. one distinct usable claim with no explicit fork produces that claim;
4. more than one distinct usable claim produces `CONFLICT`; and
5. any two usable target Observations in one logical chain that are incomparable by ancestry and are not
   closed by one supplied reconciliation descendant form an unresolved fork and produce
   `CONFLICT`, even when their claim strings match.

Multiple independent chains with the same usable claim therefore reduce to that one claim; an
`UNKNOWN` or `CONFLICT` target remains an explicit usable claim, not absence. Every Category Result
retains all category target references separately from its relied-on subset. The Status Checker
cannot supply, omit, reorder or select these deterministic results.

## Status time windows

The proposed finite windows are:

```text
manifest_at <= requested_at < manifest_valid_until
request_valid_until =
  min(requested_at + 86400 seconds, manifest_valid_until)
requested_at <= evaluated_at < request_valid_until
max(observed_at, valid_from) <= evaluated_at < observation.valid_until
status_valid_until =
  min(every one of the nine category result_valid_until values)
```

Each Category Result derives:

```text
result_valid_until =
  min(request_valid_until, manifest_valid_until, every relied-on target.valid_until)
```

For an empty relied-on set, only the Request and Manifest terms remain. Because every relied-on
target appears in exactly one Category Result, the Decision formula is equivalent to the minimum
over all relied-on target deadlines but is uniquely computed through the fixed nine-result tuple.

If no Observation is relied on, the empty observation term is omitted and `status_valid_until` is
the minimum of the Request and Manifest deadlines. Every category without usable evidence is
`NOT_ASSESSED`, so the recorded value is `INDETERMINATE`; the finite window never converts missing
evidence into `CURRENT`.

All timestamps are explicit canonical UTC seconds. No wall clock, filesystem time, environment
fallback, grace period or automatic renewal exists.

An as-of assessor accepts one explicit `as_of`:

- `as_of < evaluated_at` is a contract-domain failure and produces no Result or Receipt;
- `as_of == status_valid_until` is `EXPIRED`;
- `as_of > status_valid_until` is `EXPIRED`; and
- a later `as_of` never extends a Manifest, Observation, Request or Record.

A new current-status assessment after new evidence requires a new Request, Instruction, Decision,
Record and Receipt. Historical documents are not updated.

## Frozen five-value resolver

Structural validation and replay occur before status reduction. An invalid Contract, broken anchor,
missing referenced Observation or ancestor, non-ancestor-closed chain, cycle, illegal link,
coverage omission or failed joint replay is an operation failure, not a status value, and creates
no Receipt. After that boundary the category tuple is always exactly nine values; a category is
never absent from a structurally successful result.

After complete replay, the proposed precedence is:

```text
EXPIRED
REVOKED
HELD
INDETERMINATE
CURRENT
```

The resolver applies:

1. if `as_of >= status_valid_until` or `as_of >= manifest_valid_until`, return `EXPIRED`;
2. otherwise, if complete current evidence has `REVOCATION_EFFECTIVE=PRESENT`, return `REVOKED`;
3. otherwise, if complete current evidence has `HOLD_ACTIVE=PRESENT`,
   `COMPLAINT_OPEN=PRESENT` or `DISPUTE_OPEN=PRESENT`, or if any of the five positive categories is
   `ABSENT_WITH_EVIDENCE`, return `HELD`;
4. otherwise, if any category is `UNKNOWN`, `NOT_ASSESSED` or `CONFLICT`, including a structurally
   complete unreconciled fork, or if no usable current evidence supports a required category,
   return `INDETERMINATE`; and
5. only if all four adverse categories are `ABSENT_WITH_EVIDENCE` and all five positive categories
   are `PRESENT`, return `CURRENT`.

An adverse category with `ABSENT_WITH_EVIDENCE` is favorable only for that adverse predicate. A
positive category with the same claim value is an evidenced failure of a required positive
predicate and therefore resolves to `HELD` unless the higher-precedence expiry or revocation rule
applies. This closes every category-by-claim path without treating missing evidence as absence.

An expired Record retains its historical adverse facts but cannot continue to claim current
`REVOKED` or `HELD` outside its evidence window. A later assessment needs new evidence. This is why
`EXPIRED` precedes the adverse values.

`CURRENT` means only:

> the exact explicit finite supplied closure satisfies the frozen policy at the exact historical
> `as_of` within the exact half-open window.

It does not mean all real-world sources were discovered, that a source is authentic, that no
unseen revocation exists, that legal effect is determined or that the value remains current when
read later.

## Frozen current-status policy

The Proposed current-status policy projection is:

```json
{
  "adverse_category_order": [
    "HOLD_ACTIVE",
    "REVOCATION_EFFECTIVE",
    "COMPLAINT_OPEN",
    "DISPUTE_OPEN"
  ],
  "basis_claim_matrix": [
    {
      "absent_basis_codes": ["HOLD_RELEASED"],
      "category": "HOLD_ACTIVE",
      "present_basis_codes": ["HOLD_IMPOSED"]
    },
    {
      "absent_basis_codes": ["RIGHTS_REINSTATED"],
      "category": "REVOCATION_EFFECTIVE",
      "present_basis_codes": [
        "REVOCATION_ISSUED",
        "SUPERSEDED",
        "RETENTION_DELETION_VIOLATION_CONFIRMED",
        "TRAINING_VIOLATION_CONFIRMED"
      ]
    },
    {
      "absent_basis_codes": ["COMPLAINT_RESOLVED"],
      "category": "COMPLAINT_OPEN",
      "present_basis_codes": ["COMPLAINT_RECEIVED"]
    },
    {
      "absent_basis_codes": ["DISPUTE_RESOLVED"],
      "category": "DISPUTE_OPEN",
      "present_basis_codes": ["DISPUTE_OPENED"]
    },
    {
      "absent_basis_codes": ["RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED"],
      "category": "RIGHTS_BASIS_CURRENT",
      "present_basis_codes": ["RIGHTS_CONFIRMED"]
    },
    {
      "absent_basis_codes": ["IDENTITY_EXPIRED_REVOKED_OR_SUPERSEDED"],
      "category": "IDENTITY_BINDING_CURRENT",
      "present_basis_codes": ["IDENTITY_CONFIRMED"]
    },
    {
      "absent_basis_codes": ["TERMS_CHANGED_OR_INCOMPATIBLE"],
      "category": "PROVIDER_TERMS_COMPATIBILITY_CURRENT",
      "present_basis_codes": ["TERMS_COMPATIBLE"]
    },
    {
      "absent_basis_codes": ["RETENTION_DELETION_UNRESOLVED_OR_NONCOMPLIANT"],
      "category": "RETENTION_DELETION_COMPLIANCE_CURRENT",
      "present_basis_codes": ["RETENTION_DELETION_COMPLIANT"]
    },
    {
      "absent_basis_codes": ["TRAINING_UNRESOLVED_OR_VIOLATED"],
      "category": "TRAINING_USE_PROHIBITION_CURRENT",
      "present_basis_codes": ["TRAINING_PROHIBITION_CONFIRMED"]
    }
  ],
  "category_reduction_rules": [
    "NO_USABLE_TARGET_YIELDS_NOT_ASSESSED",
    "ONE_DISTINCT_USABLE_CLAIM_WITHOUT_FORK_YIELDS_THAT_CLAIM",
    "MULTIPLE_DISTINCT_USABLE_CLAIMS_YIELD_CONFLICT",
    "INCOMPARABLE_USABLE_HEADS_WITHOUT_SUPPLIED_RECONCILIATION_DESCENDANT_YIELD_CONFLICT_EVEN_IF_CLAIMS_MATCH"
  ],
  "category_effect_rules": {
    "ADVERSE_ABSENT_WITH_EVIDENCE": "ADVERSE_ABSENT",
    "ADVERSE_PRESENT": "ADVERSE_PRESENT",
    "ANY_CONFLICT_NOT_ASSESSED_OR_UNKNOWN": "INDETERMINATE",
    "POSITIVE_ABSENT_WITH_EVIDENCE": "POSITIVE_ABSENT",
    "POSITIVE_PRESENT": "POSITIVE_PRESENT"
  },
  "category_result_valid_until_rule": "MIN_REQUEST_VALID_UNTIL_MANIFEST_VALID_UNTIL_AND_RELIED_TARGET_VALID_UNTIL",
  "category_result_reference_membership": {
    "category_observation_refs": "EVERY_AND_ONLY_REQUEST_TARGET_FOR_CATEGORY",
    "relied_on_observation_refs": "EVERY_AND_ONLY_CATEGORY_TARGET_WITH_COMPLETE_CHAIN_CLAIM_NOT_NOT_ASSESSED_AND_MAX_OBSERVED_AT_VALID_FROM_LE_EVALUATED_AT_LT_VALID_UNTIL"
  },
  "chain_scope_fields": [
    "subject_closure_id",
    "subject_closure_sha256",
    "category",
    "source_identity_ref_sha256",
    "source_kind",
    "observation_profile",
    "policy_version"
  ],
  "claim_values": [
    "PRESENT",
    "ABSENT_WITH_EVIDENCE",
    "UNKNOWN",
    "NOT_ASSESSED",
    "CONFLICT"
  ],
  "coverage_byte_accounting": "COUNT_EVERY_OCCURRENCE_BEFORE_UNIQUENESS",
  "current_requirements": "ALL_ADVERSE_ABSENT_WITH_EVIDENCE_AND_ALL_POSITIVE_PRESENT",
  "decision_category_tuple_membership": {
    "final_status_precedence_rule": "RETAIN_ALL_MATCHING_MEMBERS_NEVER_CLEAR_DIAGNOSTIC_TUPLES",
    "held_categories": [
      {
        "category": "HOLD_ACTIVE",
        "deterministic_effect": "ADVERSE_PRESENT"
      },
      {
        "category": "COMPLAINT_OPEN",
        "deterministic_effect": "ADVERSE_PRESENT"
      },
      {
        "category": "DISPUTE_OPEN",
        "deterministic_effect": "ADVERSE_PRESENT"
      },
      {
        "category": "RIGHTS_BASIS_CURRENT",
        "deterministic_effect": "POSITIVE_ABSENT"
      },
      {
        "category": "IDENTITY_BINDING_CURRENT",
        "deterministic_effect": "POSITIVE_ABSENT"
      },
      {
        "category": "PROVIDER_TERMS_COMPATIBILITY_CURRENT",
        "deterministic_effect": "POSITIVE_ABSENT"
      },
      {
        "category": "RETENTION_DELETION_COMPLIANCE_CURRENT",
        "deterministic_effect": "POSITIVE_ABSENT"
      },
      {
        "category": "TRAINING_USE_PROHIBITION_CURRENT",
        "deterministic_effect": "POSITIVE_ABSENT"
      }
    ],
    "indeterminate_categories": [
      {
        "category": "HOLD_ACTIVE",
        "deterministic_effect": "INDETERMINATE"
      },
      {
        "category": "REVOCATION_EFFECTIVE",
        "deterministic_effect": "INDETERMINATE"
      },
      {
        "category": "COMPLAINT_OPEN",
        "deterministic_effect": "INDETERMINATE"
      },
      {
        "category": "DISPUTE_OPEN",
        "deterministic_effect": "INDETERMINATE"
      },
      {
        "category": "RIGHTS_BASIS_CURRENT",
        "deterministic_effect": "INDETERMINATE"
      },
      {
        "category": "IDENTITY_BINDING_CURRENT",
        "deterministic_effect": "INDETERMINATE"
      },
      {
        "category": "PROVIDER_TERMS_COMPATIBILITY_CURRENT",
        "deterministic_effect": "INDETERMINATE"
      },
      {
        "category": "RETENTION_DELETION_COMPLIANCE_CURRENT",
        "deterministic_effect": "INDETERMINATE"
      },
      {
        "category": "TRAINING_USE_PROHIBITION_CURRENT",
        "deterministic_effect": "INDETERMINATE"
      }
    ],
    "revoked_categories": [
      {
        "category": "REVOCATION_EFFECTIVE",
        "deterministic_effect": "ADVERSE_PRESENT"
      }
    ]
  },
  "error_orders": {
    "as_of": [
      "AS_OF_CONTRACT_INVALID",
      "RECORD_JOINT_REPLAY_FAILED",
      "AS_OF_PRECEDES_RECORD_EVALUATION",
      "INTERNAL_RESULT_INCONSISTENCY"
    ],
    "chain_replay": [
      "COUNT_OUT_OF_RANGE",
      "OBSERVATION_CONTRACT_INVALID",
      "DUPLICATE_OBSERVATION_ID",
      "DUPLICATE_OBSERVATION_DOCUMENT_SHA256",
      "DUPLICATE_OBSERVATION_CHAIN_SHA256",
      "CHAIN_SCOPE_MISMATCH",
      "ORPHAN_REFERENCE",
      "REFERENCE_ANCHOR_MISMATCH",
      "IMMEDIATE_LINK_INVALID",
      "CYCLE_DETECTED",
      "GENESIS_COUNT_INVALID",
      "DISCONNECTED_GRAPH",
      "RECONCILIATION_HEAD_ANCESTRY_CONFLICT",
      "INTERNAL_RESULT_INCONSISTENCY"
    ],
    "coverage": [
      "CHAIN_COLLECTION_CONTRACT_INVALID",
      "CHAIN_COUNT_OUT_OF_RANGE",
      "CHAIN_INPUT_CONTRACT_INVALID",
      "TARGET_COUNT_OUT_OF_RANGE",
      "OBSERVATION_COUNT_OUT_OF_RANGE",
      "AGGREGATE_CANONICAL_BYTES_OUT_OF_RANGE",
      "EVIDENCE_RECORD_INVALID",
      "REQUEST_TARGET_COVERED_MULTIPLE_TIMES",
      "REQUEST_TARGET_ANCHOR_MISMATCH",
      "REQUEST_TARGET_NOT_IN_RECORD",
      "REQUEST_OBSERVATION_NOT_COVERED",
      "CHAIN_REPLAY_FAILED",
      "DUPLICATE_LOGICAL_CHAIN",
      "CROSS_CHAIN_DUPLICATE_OBSERVATION_ID",
      "CROSS_CHAIN_DUPLICATE_OBSERVATION_DOCUMENT_SHA256",
      "CROSS_CHAIN_DUPLICATE_OBSERVATION_CHAIN_SHA256",
      "CROSS_CHAIN_DUPLICATE_OBSERVATION_SET_SHA256",
      "REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN",
      "CHAIN_TARGET_SET_MISMATCH",
      "UNRELATED_SUPPORT_OBSERVATION",
      "RECORD_REBUILD_MISMATCH",
      "INTERNAL_RESULT_INCONSISTENCY"
    ],
    "joint_replay": [
      "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
      "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
      "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
      "INTERNAL_RESULT_INCONSISTENCY"
    ],
    "receipt": [
      "RECEIPT_CONTRACT_INVALID",
      "AS_OF_ASSESSMENT_REPLAY_FAILED",
      "ASSESSMENT_RESULT_INCONSISTENT",
      "INTERNAL_RECEIPT_INCONSISTENCY",
      "RECEIPT_REPLAY_MISMATCH"
    ]
  },
  "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
  "generic_basis_order": [
    "INITIAL_STATUS_UNKNOWN",
    "INITIAL_STATUS_NOT_ASSESSED",
    "STATUS_RECONFIRMED",
    "STATUS_BECAME_UNKNOWN",
    "CONFLICT_IDENTIFIED",
    "CONFLICT_RECONCILED"
  ],
  "generic_basis_source_kind_rule": "INITIAL_UNKNOWN_INITIAL_NOT_ASSESSED_STATUS_BECAME_UNKNOWN_AND_CONFLICT_IDENTIFIED_USE_CATEGORY_APPLICABLE_KIND_STATUS_RECONFIRMED_AND_CONFLICT_RECONCILED_REUSE_CHAIN_SCOPE_KIND",
  "limitation_codes": [
    "SOURCE_AUTHENTICITY_NOT_PROVEN",
    "SOURCE_COMPLETENESS_NOT_PROVEN",
    "CHAIN_COMPLETENESS_NOT_PROVEN",
    "REALITY_CURRENTNESS_NOT_PROVEN",
    "SCOPE_LIMITED_TO_DECLARED_SUBJECT",
    "TIME_WINDOW_LIMITED",
    "LEGAL_EFFECT_NOT_DETERMINED"
  ],
  "limitation_rule": "EXACT_POLICY_ORDER_NO_OMISSION_EXTENSION_OR_REORDERING",
  "max_window_seconds": 86400,
  "observation_profile": "sdc.generated-reference-current-status-observation-profile.v1",
  "ordering_rules": {
    "category_observation_refs": "REQUEST_ORDER_FILTERED_BY_CATEGORY",
    "category_results": "EXACT_FULL_CATEGORY_ORDER",
    "decision_derived_category_tuples": "STABLE_SUBSEQUENCE_OF_FULL_CATEGORY_ORDER_FILTERED_BY_EFFECT",
    "explicit_chain_set_chain_inputs": "STRICT_ASCENDING_CHAIN_SCOPE_SHA256_THEN_GENESIS_OBSERVATION_ID",
    "full_category_order": [
      "HOLD_ACTIVE",
      "REVOCATION_EFFECTIVE",
      "COMPLAINT_OPEN",
      "DISPUTE_OPEN",
      "RIGHTS_BASIS_CURRENT",
      "IDENTITY_BINDING_CURRENT",
      "PROVIDER_TERMS_COMPATIBILITY_CURRENT",
      "RETENTION_DELETION_COMPLIANCE_CURRENT",
      "TRAINING_USE_PROHIBITION_CURRENT"
    ],
    "logical_chain_key_fields": ["chain_scope_sha256", "genesis_observation_id"],
    "logical_chain_uniqueness": "EQUAL_KEYS_FAIL_SAME_SCOPE_DIFFERENT_GENESIS_IS_DISTINCT",
    "observation_set_observation_occurrences": "STRICT_ASCENDING_OBSERVATION_ID",
    "observation_set_target_observation_refs": "STABLE_SUBSEQUENCE_OF_REQUEST_OBSERVATION_REFS_FILTERED_BY_LOGICAL_CHAIN",
    "reconciliation_predecessor_heads": "STRICT_ASCENDING_OBSERVATION_ID_OBSERVATION_SHA256_CHAIN_SHA256",
    "relied_on_observation_refs": "STABLE_SUBSEQUENCE_OF_CATEGORY_OBSERVATION_REFS",
    "request_observation_refs": "STRICT_ASCENDING_FULL_CATEGORY_ORDER_THEN_VALID_FROM_THEN_OBSERVATION_ID",
    "target_coverage": "REQUEST_ORDER"
  },
  "policy_id": "sdc.generated-reference-current-status-policy",
  "policy_version": "1.0.0",
  "positive_category_order": [
    "RIGHTS_BASIS_CURRENT",
    "IDENTITY_BINDING_CURRENT",
    "PROVIDER_TERMS_COMPATIBILITY_CURRENT",
    "RETENTION_DELETION_COMPLIANCE_CURRENT",
    "TRAINING_USE_PROHIBITION_CURRENT"
  ],
  "precedence": [
    "EXPIRED",
    "REVOKED",
    "HELD",
    "INDETERMINATE",
    "CURRENT"
  ],
  "resolution_rules": {
    "CURRENT": "ALL_ADVERSE_ABSENT_WITH_EVIDENCE_AND_ALL_POSITIVE_PRESENT",
    "EXPIRED": "AS_OF_GE_STATUS_VALID_UNTIL_OR_MANIFEST_VALID_UNTIL",
    "HELD": "HOLD_COMPLAINT_OR_DISPUTE_PRESENT_OR_ANY_POSITIVE_ABSENT_WITH_EVIDENCE",
    "INDETERMINATE": "COMPLETE_STRUCTURE_WITH_UNKNOWN_NOT_ASSESSED_CONFLICT_OR_NO_USABLE_EVIDENCE",
    "REVOKED": "REVOCATION_EFFECTIVE_PRESENT"
  },
  "resource_limits": {
    "aggregate_observation_occurrence_bytes_max": 16777216,
    "as_of_receipt_document_bytes_max": 65536,
    "basis_code_points_max": 1000,
    "chain_inputs_max": 32,
    "chain_inputs_min": 1,
    "generic_container_items_max": 64,
    "identity_reference_document_bytes_max": 16384,
    "json_depth_max": 32,
    "observations_per_chain_max": 64,
    "observations_per_chain_min": 1,
    "reconciliation_heads_max": 8,
    "request_instruction_decision_record_bytes_max": 2097152,
    "request_targets_max": 32,
    "request_targets_min": 9,
    "retained_action_document_bytes_max": 262144,
    "retained_source_object_bytes_max": 262144,
    "source_observation_document_bytes_max": 262144,
    "source_reference_document_bytes_max": 16384,
    "targets_per_chain_max": 32,
    "targets_per_chain_min": 1,
    "top_level_object_members_max": 128
  },
  "request_reference_rule": "EXPLICIT_TARGET_OBSERVATIONS_ANCESTOR_TARGETS_ALLOWED_NO_TERMINAL_INFERENCE",
  "reviewer_rule": "STATUS_PREPARER_DISTINCT_FROM_STATUS_CHECKER",
  "result_values": [
    "EXPIRED",
    "REVOKED",
    "HELD",
    "INDETERMINATE",
    "CURRENT"
  ],
  "source_kind_applicability": [
    {
      "basis_codes": ["HOLD_IMPOSED", "HOLD_RELEASED"],
      "category": "HOLD_ACTIVE",
      "source_kinds": ["INTERNAL_HOLD_RECORD"]
    },
    {
      "basis_codes": ["REVOCATION_ISSUED", "RIGHTS_REINSTATED", "SUPERSEDED"],
      "category": "REVOCATION_EFFECTIVE",
      "source_kinds": ["REVOCATION_NOTICE"]
    },
    {
      "basis_codes": ["RETENTION_DELETION_VIOLATION_CONFIRMED"],
      "category": "REVOCATION_EFFECTIVE",
      "source_kinds": ["RETENTION_DELETION_RECORD"]
    },
    {
      "basis_codes": ["TRAINING_VIOLATION_CONFIRMED"],
      "category": "REVOCATION_EFFECTIVE",
      "source_kinds": ["TRAINING_USE_RECORD"]
    },
    {
      "basis_codes": ["COMPLAINT_RECEIVED", "COMPLAINT_RESOLVED"],
      "category": "COMPLAINT_OPEN",
      "source_kinds": ["COMPLAINT_RECORD"]
    },
    {
      "basis_codes": ["DISPUTE_OPENED", "DISPUTE_RESOLVED"],
      "category": "DISPUTE_OPEN",
      "source_kinds": ["DISPUTE_RECORD"]
    },
    {
      "basis_codes": ["RIGHTS_CONFIRMED", "RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED"],
      "category": "RIGHTS_BASIS_CURRENT",
      "source_kinds": ["RIGHTS_HOLDER_DECLARATION", "LICENSOR_DECLARATION"]
    },
    {
      "basis_codes": ["IDENTITY_CONFIRMED", "IDENTITY_EXPIRED_REVOKED_OR_SUPERSEDED"],
      "category": "IDENTITY_BINDING_CURRENT",
      "source_kinds": ["IDENTITY_BINDING_RECORD"]
    },
    {
      "basis_codes": ["TERMS_COMPATIBLE", "TERMS_CHANGED_OR_INCOMPATIBLE"],
      "category": "PROVIDER_TERMS_COMPATIBILITY_CURRENT",
      "source_kinds": ["PROVIDER_TERMS_RECORD"]
    },
    {
      "basis_codes": [
        "RETENTION_DELETION_COMPLIANT",
        "RETENTION_DELETION_UNRESOLVED_OR_NONCOMPLIANT"
      ],
      "category": "RETENTION_DELETION_COMPLIANCE_CURRENT",
      "source_kinds": ["RETENTION_DELETION_RECORD"]
    },
    {
      "basis_codes": ["TRAINING_PROHIBITION_CONFIRMED", "TRAINING_UNRESOLVED_OR_VIOLATED"],
      "category": "TRAINING_USE_PROHIBITION_CURRENT",
      "source_kinds": ["TRAINING_USE_RECORD"]
    }
  ],
  "source_kind_order": [
    "RIGHTS_HOLDER_DECLARATION",
    "LICENSOR_DECLARATION",
    "PROVIDER_TERMS_RECORD",
    "INTERNAL_HOLD_RECORD",
    "REVOCATION_NOTICE",
    "COMPLAINT_RECORD",
    "DISPUTE_RECORD",
    "IDENTITY_BINDING_RECORD",
    "RETENTION_DELETION_RECORD",
    "TRAINING_USE_RECORD"
  ],
  "status_subject": "EXACT_GENERATED_RIGHTS_MANIFEST_CLOSURE",
  "status_action_projection_rule": "PREPARER_ACTION_THEN_REQUEST_THEN_CHECKER_ACTION_THEN_INSTRUCTION_THEN_DECISION",
  "status_valid_until_rule": "MIN_OF_NINE_CATEGORY_RESULT_VALID_UNTIL_VALUES",
  "structural_failure_rule": "MALFORMED_OR_MISSING_REFERENCED_CLOSURE_FAILS_WITHOUT_RESULT",
  "subject_closure_profile": "sdc.generated-reference-current-status-subject-closure.v1",
  "successful_conflict_rule": "COMPLETE_UNRECONCILED_MULTI_HEAD_CHAIN_YIELDS_CONFLICT",
  "transition_matrix": {
    "GENESIS": [
      {
        "basis": "CATEGORY_SPECIFIC_PRESENT",
        "to": "PRESENT"
      },
      {
        "basis": "CATEGORY_SPECIFIC_ABSENT",
        "to": "ABSENT_WITH_EVIDENCE"
      },
      {
        "basis": "INITIAL_STATUS_UNKNOWN",
        "to": "UNKNOWN"
      },
      {
        "basis": "INITIAL_STATUS_NOT_ASSESSED",
        "to": "NOT_ASSESSED"
      },
      {
        "basis": "CONFLICT_IDENTIFIED",
        "to": "CONFLICT"
      }
    ],
    "RECONCILIATION_2_TO_8_HEADS": [
      {
        "basis": "CONFLICT_RECONCILED",
        "final_claims": ["PRESENT", "ABSENT_WITH_EVIDENCE", "UNKNOWN"]
      },
      {
        "basis": "CONFLICT_IDENTIFIED",
        "final_claims": ["CONFLICT"]
      },
      {
        "final_claims": ["NOT_ASSESSED"],
        "result": "REJECT"
      }
    ],
    "SUCCESSOR": [
      {
        "basis": "INITIAL_STATUS_UNKNOWN",
        "from_claims": ["NOT_ASSESSED"],
        "to": "UNKNOWN"
      },
      {
        "basis": "CATEGORY_SPECIFIC_PRESENT",
        "from_claims": ["NOT_ASSESSED", "UNKNOWN"],
        "to": "PRESENT"
      },
      {
        "basis": "CATEGORY_SPECIFIC_ABSENT",
        "from_claims": ["NOT_ASSESSED", "UNKNOWN"],
        "to": "ABSENT_WITH_EVIDENCE"
      },
      {
        "basis": "STATUS_RECONFIRMED",
        "from_claims": ["PRESENT"],
        "to": "PRESENT"
      },
      {
        "basis": "STATUS_RECONFIRMED",
        "from_claims": ["ABSENT_WITH_EVIDENCE"],
        "to": "ABSENT_WITH_EVIDENCE"
      },
      {
        "basis": "CATEGORY_SPECIFIC_ABSENT",
        "from_claims": ["PRESENT"],
        "to": "ABSENT_WITH_EVIDENCE"
      },
      {
        "basis": "CATEGORY_SPECIFIC_PRESENT",
        "from_claims": ["ABSENT_WITH_EVIDENCE"],
        "to": "PRESENT"
      },
      {
        "basis": "STATUS_BECAME_UNKNOWN",
        "from_claims": ["PRESENT", "ABSENT_WITH_EVIDENCE"],
        "to": "UNKNOWN"
      },
      {
        "basis": "CONFLICT_IDENTIFIED",
        "from_claims": ["NOT_ASSESSED", "UNKNOWN", "PRESENT", "ABSENT_WITH_EVIDENCE"],
        "to": "CONFLICT"
      }
    ],
    "SUCCESSOR_REJECTION": [
      {
        "from_claims": ["UNKNOWN"],
        "result": "REJECT",
        "to_claims": ["UNKNOWN"]
      },
      {
        "from_claims": ["NOT_ASSESSED", "UNKNOWN", "PRESENT", "ABSENT_WITH_EVIDENCE", "CONFLICT"],
        "result": "REJECT",
        "to_claims": ["NOT_ASSESSED"]
      },
      {
        "from_claims": ["CONFLICT"],
        "result": "REJECT",
        "to_claims": ["PRESENT", "ABSENT_WITH_EVIDENCE", "UNKNOWN", "NOT_ASSESSED", "CONFLICT"]
      }
    ]
  },
  "window_semantics": "EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE",
  "zero_authority": true
}
```

Under the ADR-040 compact canonical JSON codec, the projection is exactly 14,138 UTF-8 bytes and its
raw SHA-256 is:

```text
cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0
```

No policy lookup, environment override or fallback is permitted.
Every use of `policy order` in the current-status family means the exact nine-value
`ordering_rules.full_category_order` tuple: all four adverse categories in their declared order,
followed by all five positive categories in their declared order.

## Explicit replay, assessment and Receipt boundary

The generated current-status family must preserve separate pure operations equivalent to:

1. replay one explicit Source Observation chain;
2. prove that the explicit chain set covers every Request target and complete ancestor;
3. jointly replay one Evidence Record against the exact Manifest and all explicit chains;
4. assess that freshly replayed Record at one explicit `as_of`;
5. build one persistent Receipt from that same-call Result; and
6. verify one existing Receipt by freshly replaying the Receipt's exact historical `as_of`.

Replay Results, coverage Results, joint Results and as-of Results are non-persistent process values
with private in-memory verifier provenance. They are not top-level Contracts and cannot be trusted
when reconstructed from JSON, copied dictionaries or subclasses.

The Receipt is a persistent historical Contract. Its public projection binds:

- the exact Evidence Record, Request and Decision IDs/SHAs;
- the subject closure;
- explicit chain-set, coverage and joint-replay digests;
- `as_of`, `evaluated_at` and `status_valid_until`;
- half-open window semantics;
- recorded status and freshly resolved `as_of_status`;
- one public `as_of_assessment_sha256` over the complete public as-of assessment projection;
- replay-consistency literals;
- every mandatory limitation code;
- `present_currentness_asserted=false`; and
- the complete zero-authority surface.

The builder verifies private same-call provenance before constructing the Receipt. No private
sentinel, capability, verifier token or provenance digest may enter Receipt bytes, a Schema or a
semantic projection. The dedicated provenance domain is used only in memory and never names a
persistent field.

Receipt parsing proves only strict canonical Contract admission. It does not replay evidence,
authenticate sources or prove currentness. Historical Receipt verification always replays the
Receipt's own `as_of`; it does not substitute the current wall clock.

## Mandatory limitation codes

Every current-status Source Observation, non-persistent Result and Receipt carries exactly the
following seven limitation codes in this exact order. No code may be omitted, added or reordered:

```text
SOURCE_AUTHENTICITY_NOT_PROVEN
SOURCE_COMPLETENESS_NOT_PROVEN
CHAIN_COMPLETENESS_NOT_PROVEN
REALITY_CURRENTNESS_NOT_PROVEN
SCOPE_LIMITED_TO_DECLARED_SUBJECT
TIME_WINDOW_LIMITED
LEGAL_EFFECT_NOT_DETERMINED
```

No successful replay removes a limitation. The Receipt's `CURRENT` value and
`present_currentness_asserted=false` are consistent because the Receipt records one exact
historical finite assessment, not a claim about the time when the Receipt is later read.

## Contract and Schema Registry impact

This Proposed ADR changes no current Contract, Schema or Registry entry.

If accepted and later implemented under separate approvals, the complete boundary will append
exactly seven top-level Contracts and seven committed Schemas:

```text
MODELS[76] = CreativeSampleGeneratedReferenceRightsManifestV1
MODELS[77] = CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1
MODELS[78] = CreativeSampleGeneratedReferenceCurrentStatusRequestV1
MODELS[79] = CreativeSampleGeneratedReferenceCurrentStatusInstructionV1
MODELS[80] = CreativeSampleGeneratedReferenceCurrentStatusDecisionV1
MODELS[81] = CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1
MODELS[82] = CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1
```

The final Registry count will be exactly 83.

The following remain closed inline definitions or non-persistent process values and do not receive
top-level Schema files:

- Manifest review evidence reference and gate result;
- current-status subject closure;
- Observation reference, chain head and chain link;
- category result;
- explicit chain replay Result;
- chain-set coverage Result;
- joint replay Result; and
- as-of assessment Result.

Seven top-level Contracts are sufficient only because the Manifest itself is the final immutable
positive Maker/Checker review closure. If a later review requires a formal Manifest
Request/Instruction/Decision/Record family, it must revise this ADR and append new versioned
Contracts. BUILD may not silently add them.

The Registry wiring remains one-way: a future generated Rights/current-status module must not
import `sdc.schemas`. `sdc.schemas` may import the new top-level models only after separate BUILD
approval.

## Closed Contract and inline projections

The seven top-level projections below are exhaustive. Every listed field is required, extra fields
are forbidden, and no field is implicitly defaulted. The phrase `complete zero-authority surface`
means every field and literal in the later section of that name, in the exact listed order. Each
semantic projection includes every field, including nested values and authority literals, except
only its own `<kind>_id` and `<kind>_sha256` fields.

The exact top-level document literals and ID stems are:

| Contract | `document_type` | ID / SHA fields | ID stem |
| --- | --- | --- | --- |
| Rights Manifest | `sdc.creative-sample-generated-reference-rights-manifest-v1` | `manifest_id`, `manifest_sha256` | `generated_reference_rights_manifest_v1_` |
| Source Observation | `sdc.creative-sample-generated-reference-current-status-source-observation-v1` | `observation_id`, `observation_sha256` | `generated_reference_current_status_source_observation_v1_` |
| Request | `sdc.creative-sample-generated-reference-current-status-request-v1` | `request_id`, `request_sha256` | `generated_reference_current_status_request_v1_` |
| Instruction | `sdc.creative-sample-generated-reference-current-status-instruction-v1` | `instruction_id`, `instruction_sha256` | `generated_reference_current_status_instruction_v1_` |
| Decision | `sdc.creative-sample-generated-reference-current-status-decision-v1` | `decision_id`, `decision_sha256` | `generated_reference_current_status_decision_v1_` |
| Evidence Record | `sdc.creative-sample-generated-reference-current-status-evidence-record-v1` | `record_id`, `record_sha256` | `generated_reference_current_status_evidence_record_v1_` |
| As-of Receipt | `sdc.creative-sample-generated-reference-current-status-record-as-of-assessment-receipt-v1` | `receipt_id`, `receipt_sha256` | `generated_reference_current_status_record_as_of_assessment_receipt_v1_` |

Every document uses `schema_version=1.0.0`. Its ID is its exact stem plus the first twenty lowercase
hex characters of its authoritative full semantic SHA. A formal document never carries its own raw
canonical-document SHA.

### Rights Manifest exact fields

```text
schema_version
document_type
manifest_scope=GENERATED_REFERENCE_RIGHTS_REVIEW_ONLY
manifest_id
manifest_sha256
policy_id
policy_version
policy_document_sha256
manifest_review_payload_sha256
reference_prompt_artifact_sha256
provider_attempt_outcome_id
provider_attempt_outcome_sha256
candidate_id
candidate_sha256
qualification_request_id
qualification_request_sha256
qualification_decision_id
qualification_decision_sha256
subject_id
asset_purpose
profile_id
profile_version
profile_sha256
catalog_version
catalog_sha256
render_input_sha256
prompt_sha256
prompt_size_bytes
prompt_render_receipt_sha256
media_content_sha256
media_size_bytes
media_technical_record_sha256
provider
model
provider_region
provider_terms_snapshot_id
provider_terms_snapshot_sha256
submitted_at
qualification_decision_at
qualification_valid_until
manifest_at
manifest_valid_until
review_evidence_refs
gate_results
proposed_rights_scope
reviewed_rights_scope
maker_identity_ref_sha256
maker_action_sha256
maker_prepared_at
checker_identity_ref_sha256
checker_action_sha256
checker_reviewed_at
rights_review_performed=true
eligible_for_separate_generated_current_status_review=true
current_status_assessment_embedded=false
status=GENERATED_RIGHTS_MANIFEST_RECORDED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

`review_evidence_refs` has exactly nine entries in this order:
`SUBMISSION_TIME_AUTHORIZATION`, `PROVIDER_TERMS_AT_SUBMISSION`, then the seven current-facing
categories used by the Manifest deadline formula. `gate_results` has exactly eleven entries in the
frozen Manifest gate order and every result in a positive Manifest is `PASS`. The first gate has an empty
`evidence_record_ids` tuple and is derived from the exact upstream closure; the second through tenth
gates each name exactly the one corresponding review-evidence `record_id`; the eleventh gate has an empty tuple
and is derived from exact retained Maker/Checker identity/action bytes. No gate may cite another
record or an arbitrary subset.

The first gate (`ordinal=0`) derives only from fresh reconstruction of the exact ADR-042/043
closure. The eleventh gate (`ordinal=10`) derives from the exact Maker identity/action, Checker identity and the Checker action pre-result
projection; that pre-result projection excludes `gate_results` and `disposition`, so the gate cannot
self-certify. The complete Checker action SHA is calculated only after the two derived results and
nine human results have been fixed. The Manifest copies the completed tuple exactly.

Manifest evidence-reference ordinals are zero-based `0..8` in evidence-category order. Gate-result
ordinals are zero-based `0..10` in gate order. Gate zero basis is the exact literal
`COMPILER_REVALIDATED_EXACT_ADR042_ADR043_CLOSURE`; gate ten basis is the exact literal
`COMPILER_REVALIDATED_DISTINCT_ROLE_AND_ACTION_CLOSURE`. Gates one through nine carry the exact
bounded human basis supplied for their corresponding evidence review. No ordinal or compiler basis
text is caller-selectable.

### Source Observation exact fields

```text
schema_version
document_type
observation_scope=GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_EVIDENCE_ONLY
observation_profile=sdc.generated-reference-current-status-observation-profile.v1
observation_id
observation_sha256
policy_id
policy_version
policy_document_sha256
subject_closure
category
claim_value
source_kind
basis_code
basis_note
source_identity_ref_sha256
source_object_ref
source_object_sha256
source_object_size_bytes
source_object_media_type
source_event_at
observed_at
valid_from
valid_until
chain_link
limitation_codes
status=GENERATED_CURRENT_STATUS_SOURCE_OBSERVATION_RECORDED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

`chain_sha256` is deliberately absent. It is derived only after the Observation ID/SHA exists and
appears in Observation references. This prevents an Observation/chain self-cycle.

### Request exact fields

```text
schema_version
document_type
request_scope=GENERATED_REFERENCE_CURRENT_STATUS_ASSESSMENT_ONLY
request_id
request_sha256
policy_id
policy_version
policy_document_sha256
subject_closure
status_preparer_identity_ref_sha256
status_preparer_action_sha256
requested_at
request_valid_until
observation_refs
request_basis
status=GENERATED_CURRENT_STATUS_REQUESTED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

`observation_refs` contains 9..32 unique explicit target-Observation entries and includes at least one target for
every category. Its canonical order is category-policy order, then `valid_from`, then
`observation_id`. The Request does not embed ancestors. Coverage receives 1..32 explicit logical
chain inputs; each input may cover 1..32 Request targets from that one chain and contains 1..64
Observations. Every Request target is covered exactly once by one input. Coverage replay proves
every predecessor and ancestor, and each target's `chain_sha256` binds its complete chain input. A
Request target may be an ancestor of another Request target. Targets are never inferred from graph
terminal shape, out-degree or storage state; `CHAIN_TARGET_SET_MISMATCH` compares only the exact
supplied Request targets with the exact per-chain target tuples.

### Instruction exact fields

```text
schema_version
document_type
instruction_scope=GENERATED_REFERENCE_CURRENT_STATUS_ASSESSMENT_ONLY
instruction_id
instruction_sha256
policy_id
policy_version
policy_document_sha256
request_id
request_sha256
subject_closure
status_preparer_identity_ref_sha256
status_preparer_action_sha256
status_checker_identity_ref_sha256
status_checker_action_sha256
requested_at
request_valid_until
evaluated_at
category_results
checker_basis
status=GENERATED_CURRENT_STATUS_INSTRUCTION_RECORDED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

`category_results` has exactly nine entries in policy order. Across them, every Request target
reference is accounted for exactly once by category; every relied-on target reference is a subset
of that category's Request targets. Ancestors remain bound through each target `chain_sha256` and
the complete explicit-chain-set digest rather than being duplicated in the Instruction.
`category_observation_refs` is the stable subsequence of the Request's `observation_refs` filtered
by that category. `relied_on_observation_refs` is a stable subsequence of
`category_observation_refs` and contains every and only member whose freshly replayed complete-chain
claim is not `NOT_ASSESSED` and whose exact half-open validity interval contains `evaluated_at`.
Neither tuple is independently sorted, caller-reordered, favorably selected or reduced to a
purportedly sufficient subset.

### Decision exact fields

```text
schema_version
document_type
decision_scope=GENERATED_REFERENCE_CURRENT_STATUS_ASSESSMENT_ONLY
decision_id
decision_sha256
policy_id
policy_version
policy_document_sha256
request_id
request_sha256
instruction_id
instruction_sha256
subject_closure
evaluated_at
decision_at
status_valid_until
category_results
revoked_categories
held_categories
indeterminate_categories
recorded_status
status=GENERATED_CURRENT_STATUS_DECISION_RECORDED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

`evaluated_at == decision_at`. The category tuple is exactly nine. `revoked_categories` contains
exactly `REVOCATION_EFFECTIVE` when and only when that result is `ADVERSE_PRESENT`.
`held_categories` contains every and only `HOLD_ACTIVE`, `COMPLAINT_OPEN` and `DISPUTE_OPEN` result
that is `ADVERSE_PRESENT`, plus every and only positive-category result that is `POSITIVE_ABSENT`.
`indeterminate_categories` contains every and only category whose result is `INDETERMINATE`.
All three are stable subsequences of full policy order. They retain all matching categories even
when a higher-precedence final status wins; final status reduction never clears a lower-precedence
diagnostic tuple. Cardinalities are therefore 0..1, 0..8 and 0..9 respectively.

### Evidence Record exact fields

```text
schema_version
document_type
record_scope=GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_CLOSURE_ONLY
record_id
record_sha256
policy_id
policy_version
policy_document_sha256
subject_closure
request
instruction
decision
status=GENERATED_CURRENT_STATUS_EVIDENCE_RECORDED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

The Record embeds exactly one exact typed Request, one Instruction and one Decision. Their own
semantic ID/SHA fields are authoritative, so the Record does not add duplicate module-SHA fields.
It embeds no Source Observation bytes and performs no discovery.

### As-of Receipt exact fields

```text
schema_version
document_type
receipt_scope=GENERATED_REFERENCE_CURRENT_STATUS_HISTORICAL_AS_OF_EVIDENCE_ONLY
receipt_id
receipt_sha256
policy_id
policy_version
policy_document_sha256
record_id
record_sha256
request_id
request_sha256
decision_id
decision_sha256
subject_closure
explicit_chain_set_sha256
coverage_set_sha256
joint_replay_sha256
as_of_assessment_sha256
as_of
evaluated_at
status_valid_until
window_semantics=EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE
recorded_status
as_of_status
recorded_revoked_categories
recorded_held_categories
recorded_indeterminate_categories
record_replay_consistent=true
same_call_assessment_verified=true
historical_assessment_only=true
present_currentness_asserted=false
limitation_codes
status=GENERATED_CURRENT_STATUS_AS_OF_RECEIPT_RECORDED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

The Receipt embeds neither the Record nor a Result. It carries exactly seven limitation codes in
the frozen order and no private provenance field.

### Closed inline definitions

The following named inline definitions may appear in generated Schema `$defs` but never in
`sdc.schemas.MODELS`:

```text
GeneratedReferenceRightsManifestEvidenceReferenceV1:
  ordinal
  category
  record_id
  document_profile
  document_sha256
  document_size_bytes
  media_type
  observed_at
  effective_from
  effective_until
  evidence_valid_until

GeneratedReferenceRightsManifestGateResultV1:
  ordinal
  gate
  result
  evidence_record_ids
  basis

GeneratedReferenceRightsScopeProposalV1:
  territory_scope
  allowed_use_scope
  proposed_scope_valid_until

GeneratedReferenceReviewedRightsScopeV1:
  territory_scope
  allowed_use_scope
  reviewed_scope_valid_until
  output_copyright_and_commercial_scope_basis
  likeness_privacy_and_sensitive_data_basis
  brand_and_protected_content_basis
  retention_and_deletion_basis
  training_use_prohibition_basis
  review_basis

GeneratedReferenceCurrentStatusSubjectClosureV1:
  closure_profile=sdc.generated-reference-current-status-subject-closure.v1
  closure_id
  closure_sha256
  policy_id
  policy_version
  policy_document_sha256
  reference_prompt_artifact_sha256
  provider_attempt_outcome_id
  provider_attempt_outcome_sha256
  candidate_id
  candidate_sha256
  qualification_request_id
  qualification_request_sha256
  qualification_decision_id
  qualification_decision_sha256
  manifest_id
  manifest_sha256
  subject_id
  asset_purpose
  media_content_sha256
  manifest_at
  manifest_valid_until

GeneratedReferenceCurrentStatusObservationRefV1:
  ordinal
  observation_id
  observation_sha256
  category
  source_identity_ref_sha256
  chain_scope_sha256
  chain_sha256
  valid_from
  valid_until

GeneratedReferenceCurrentStatusChainHeadRefV1:
  observation_id
  observation_sha256
  chain_sha256

GeneratedReferenceCurrentStatusChainLinkV1:
  link_kind
  chain_scope_sha256
  predecessor_heads

GeneratedReferenceCurrentStatusCategoryResultV1:
  ordinal
  category
  claim_value
  deterministic_effect
  category_observation_refs
  relied_on_observation_refs
  result_valid_until
```

Subject closure ID stem is `generated_reference_current_status_subject_closure_v1_`; its projection
excludes only `closure_id` and `closure_sha256`. A chain scope is exactly
`(subject_closure_id, subject_closure_sha256, category, source_identity_ref_sha256, source_kind,
observation_profile, policy_version)`. A `GENESIS` link has zero
predecessor heads, `SUCCESSOR` has exactly one, and `RECONCILIATION` has 2..8 unique canonical
heads. Category `deterministic_effect` is exactly one of `ADVERSE_PRESENT`, `ADVERSE_ABSENT`,
`POSITIVE_PRESENT`, `POSITIVE_ABSENT` or `INDETERMINATE`.

The mapping is exact: an adverse `PRESENT`/`ABSENT_WITH_EVIDENCE` becomes
`ADVERSE_PRESENT`/`ADVERSE_ABSENT`; a positive `PRESENT`/`ABSENT_WITH_EVIDENCE` becomes
`POSITIVE_PRESENT`/`POSITIVE_ABSENT`; and `UNKNOWN`, `NOT_ASSESSED` or `CONFLICT` becomes
`INDETERMINATE` for either category class.

Manifest evidence references have exactly nine entries; Manifest gate results exactly eleven;
territory scope has 1..64 unique canonical codes; allowed-use scope has 1..32; both tuples are in
strict ascending UTF-8 byte order. Every human basis is 1..1000 NFC characters. All source/status
tuples obey the explicit maxima in the resource section.
`proposed_rights_scope` uses `GeneratedReferenceRightsScopeProposalV1` and contains no Checker
basis. `reviewed_rights_scope` uses `GeneratedReferenceReviewedRightsScopeV1` and is carried in full
by the Checker action. Its five specialized basis fields exactly equal gate-result bases at
zero-based indices 4, 5, 6, 8 and 9 respectively; `review_basis` is the Checker's bounded overall
summary. Evidence-reference, Observation-reference and category-result `ordinal` fields are
zero-based indices in their respective frozen canonical tuples; they are never caller-selected
rankings.
The review payload, retained action records, policy constants and replay/coverage/joint/as-of
Results are private process values rather than portable models. An indeterminate or negative
Manifest review produces only retained Checker evidence and no portable Manifest.

## Canonical bytes and digest domains

Persistent formal documents use the ADR-040 canonical-document codec:

- UTF-8 without BOM;
- every key and string already NFC;
- recursive key sorting;
- two-space indentation;
- `ensure_ascii=false` and `allow_nan=false`;
- LF only; and
- exactly one terminal LF.

Semantic projections use the ADR-040 compact codec:

- UTF-8 without BOM;
- every key and string already NFC;
- recursive key sorting;
- compact separators;
- no CR and no terminal LF;
- arrays preserve their frozen validated order; and
- no floats, NaN, coercion, duplicate keys, extra fields or implicit nulls.

Prompt, PNG, retained identity/action and external evidence file SHA-256 values remain undomained
raw byte digests. Semantic identities use explicit projected values and distinct NUL-terminated
domains.

The Proposed domains are:

```text
sdc:generated-reference-rights-manifest-review-payload:v1\0
sdc:generated-reference-rights-manifest:v1\0
sdc:generated-reference-current-status-subject-closure:v1\0
sdc:generated-reference-current-status-source-observation:v1\0
sdc:generated-reference-current-status-chain-scope:v1\0
sdc:generated-reference-current-status-chain:v1\0
sdc:generated-reference-current-status-observation-set:v1\0
sdc:generated-reference-current-status-request:v1\0
sdc:generated-reference-current-status-instruction:v1\0
sdc:generated-reference-current-status-decision:v1\0
sdc:generated-reference-current-status-evidence-record:v1\0
sdc:generated-reference-current-status-explicit-chain-set:v1\0
sdc:generated-reference-current-status-coverage-set:v1\0
sdc:generated-reference-current-status-joint-replay:v1\0
sdc:generated-reference-current-status-record-as-of-assessment:v1\0
sdc:generated-reference-current-status-record-as-of-assessment-provenance:v1\0
sdc:generated-reference-current-status-record-as-of-assessment-receipt:v1\0
```

Every self ID and semantic SHA is excluded only from its own projection. The full 64-hex digest is
the authoritative identity. Any 20-hex ID suffix is a deterministic handle derived from that full
digest. No generic `stable_id`, implicit `model_dump`, dataclass walk or reused ADR-043/real-asset
domain defines a new identity.

`chain_scope_sha256` projects exactly `(subject_closure_id, subject_closure_sha256, category,
source_identity_ref_sha256, source_kind, observation_profile, policy_version)` under the
chain-scope domain. After an Observation ID/SHA has been
derived, `chain_sha256` projects exactly `(chain_scope_sha256, observation_id,
observation_sha256, link_kind, predecessor_heads)` under the chain domain. Predecessor heads remain
in their frozen order. Neither projection uses incidental model serialization.

The four public replay/assessment digests retained by the Receipt also have closed projections.
First, one logical chain input derives `observation_set_sha256` under the observation-set domain
from exactly:

```text
chain_scope_sha256
genesis_observation_id
target_observation_refs
observation_occurrences
```

`target_observation_refs` preserves Request order. `observation_occurrences` is the complete unique
ancestor-closed tuple in ascending `observation_id` order, with each occurrence containing exactly
`observation_id`, `observation_sha256` and `chain_sha256`.

`explicit_chain_set_sha256` uses the explicit-chain-set domain over exactly:

```text
policy_document_sha256
subject_closure_id
subject_closure_sha256
request_id
request_sha256
chain_inputs
```

Each `chain_inputs` member contains exactly `chain_scope_sha256`, `genesis_observation_id`,
`observation_set_sha256` and `target_observation_refs`. Members are ordered by
`(chain_scope_sha256, genesis_observation_id)`. That exact tuple is the logical-chain key. Equal
keys fail as `DUPLICATE_LOGICAL_CHAIN`; the same `chain_scope_sha256` with a different
`genesis_observation_id` is a distinct logical chain.

`coverage_set_sha256` uses the coverage-set domain over exactly:

```text
record_id
record_sha256
request_id
request_sha256
subject_closure_sha256
explicit_chain_set_sha256
target_coverage
```

`target_coverage` has exactly one entry per Request target in Request order. Each entry contains the
complete target Observation reference, `chain_scope_sha256`, `genesis_observation_id` and
`observation_set_sha256`. No target can be omitted or covered twice.

`joint_replay_sha256` uses the joint-replay domain over exactly:

```text
record_id
record_sha256
subject_closure_id
subject_closure_sha256
explicit_chain_set_sha256
coverage_set_sha256
request_id
request_sha256
instruction_id
instruction_sha256
decision_id
decision_sha256
category_results
recorded_status
```

`as_of_assessment_sha256` uses the record-as-of-assessment domain over exactly:

```text
record_id
record_sha256
decision_id
decision_sha256
subject_closure_id
subject_closure_sha256
joint_replay_sha256
as_of
evaluated_at
status_valid_until
manifest_valid_until
recorded_status
as_of_status
recorded_revoked_categories
recorded_held_categories
recorded_indeterminate_categories
limitation_codes
present_currentness_asserted=false
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

Every tuple above is already validated and uses the specified order. These public digests are
deterministic evidence anchors, not private verifier provenance. The private provenance domain
remains process-local and its value is never serialized.

## Complete zero-authority surface

Each of the seven future top-level Contracts directly carries
`evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY`. It is a required scope literal, not permission and
not a claim that external evidence is globally complete.

Each of the seven future top-level Contracts must directly carry this complete explicit surface:

```text
authority_scope=THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY
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
grants_rights=false
grants_qualification=false
grants_execution_authority=false
eligible_for_asset_promotion=false
replaces_rights_manifest=false
usage_restriction=MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION
```

These fields are required literal projection fields, not omitted defaults. Exact scalar types are
validated. Manifest creation, a positive Rights review, `CURRENT`, a valid hash or a passing test
never changes them.

The Manifest may record `rights_review_performed=true` and
`eligible_for_separate_generated_current_status_review=true`. Those facts only describe the
completed scoped process and next manual review route. They do not grant legal rights, current
eligibility, commercial use, promotion, Provider capability or execution.

## Prompt, QC, Catalog and Provider isolation

- Prompt text and `PromptRenderReceipt` remain process inputs and evidence, not Rights decisions.
- Profile Prompt constraints cannot be promoted to image facts.
- QC expectations and QC results cannot satisfy a Rights or current-status gate.
- Catalog `qualification`, `rights` and `compatibility` values remain zero-authority metadata.
- Provider/model/region and terms anchors describe the reviewed historical Attempt only.
- `PROVIDER_TERMS_COMPATIBILITY_CURRENT` is a bounded evidence predicate, not proof that a Provider
  is available, capable, entitled, affordable or authorized.
- No Resolver may recommend, select or call a Provider.
- No generated Candidate, Manifest, Record or Receipt may validate as current `InputMaterial` or
  `ProviderRequest`.

## Runtime, promotion and publication isolation

This boundary must not import, call or modify:

- `GenerationJob`, `JobGraph`, `ProviderRequest` or `InputMaterial`;
- Runtime, Worker, Temporal, PostgreSQL or persistence rows;
- Provider submit, inspect, download, cancel or Retry;
- network, credentials, cost reservation or paid service;
- `CharacterAssetVersion`, `SceneAssetVersion` or any Bible binding;
- QC automation, publication, posting or release;
- retention/deletion automation or training controls; or
- migration or backfill code.

No new value may be added to current AssetVersion provenance. Generated bytes remain permanently
ineligible for `IMPORTED_APPROVED_MEDIA`.

Even an exact `CURRENT` Receipt leaves `eligible_for_asset_promotion=false`. A separate promotion
ADR must choose a truthful generated AssetVersion/Bible V2 or typed eligible-asset sidecar. A later
Multi-Reference Role Binding / Provider Input Material V2 ADR must consume only post-promotion
values. A still later execution ADR must govern Provider, Runtime, network, credentials, cost and
Retry.

The dependency order remains:

```text
Candidate/Qualification
  -> Rights Manifest/current-status
  -> promotion
  -> multi-reference role/Provider input
  -> Runtime/Provider execution
```

## Resource, privacy and retained-evidence boundary

Every formal JSON document is bounded before decoding or parsing. The exact inclusive V1 limits
are:

| Resource | Limit |
| --- | ---: |
| Rights Manifest document | 262,144 bytes |
| One Source Observation document | 262,144 bytes |
| One Request, Instruction, Decision or Evidence Record document | 2,097,152 bytes |
| One As-of Receipt document | 65,536 bytes |
| Manifest review payload or retained action record | 262,144 bytes |
| Retained identity-reference record | 16,384 bytes |
| One retained review/source evidence document | 262,144 bytes |
| Prompt bytes | 65,536 bytes |
| Exact PNG bytes | 67,108,864 bytes |
| Top-level formal object members | 128 |
| Nested object or array members | 64 |
| Observation references in one Request | 32 |
| Source Observations in one explicit chain input | 64 |
| Explicit chain inputs in one coverage operation | 32 |
| Request targets in one explicit chain input | 32 |
| Aggregate canonical Observation occurrence bytes per coverage operation | 16,777,216 bytes |
| Reconciliation branch heads | 8 |
| Manifest review evidence references | exactly 9 |
| Manifest gate results | exactly 11 |
| Current-status category results | exactly 9 |
| Territory codes | 64 |
| Allowed-use codes | 32 |
| Human basis text | 1,000 Unicode code points |
| Portable reference or code text | 256 Unicode code points |
| JSON nesting depth | 32 |

Every JSON document is at least one byte. A limit crossing is rejected before deeper traversal. No
operation truncates, samples, drops or repairs a value. Aggregate coverage bytes count every
supplied occurrence before any uniqueness check; repeated occurrences are charged repeatedly and
cannot evade the limit through deduplication. The external PNG retains the ADR-043
technical, dimension and chunk limits in addition to the byte maximum.

Portable Contracts must not contain:

- local paths, URLs, signed URLs or raw Provider task identifiers;
- credentials, access tokens, account identifiers or response bodies;
- raw identity documents, reviewer names, legal documents or sensitive personal data;
- unbounded Provider errors, metadata or arbitrary policy text; or
- raw PNG bytes.

Retained Provider, reviewer, rights, privacy, retention, deletion and training records remain
outside portable Contracts. Portable values bind only privacy-minimized references, canonical raw
SHA-256 values, bounded reason codes and bounded human basis text.

Binding a retained-record digest does not authorize retaining that record. Retention and deletion
authority must already exist independently.

If a later trusted-local finalizer is proposed, it requires its own ADR or explicit BUILD scope.
This ADR does not authorize filesystem discovery, directory enumeration, remote paths, writes,
overwrite, repair, quarantine or real private evidence processing.

## Validation and future implementation gates

A future BUILD may proceed only after this ADR is Accepted and a separate explicit implementation
approval is recorded. It must:

1. begin from the exact newly verified authoritative `main`;
2. use an isolated `codex/` branch and modify only the reviewed allowlist;
3. create a reviewed full committed-Git-blob path/size/SHA-256 baseline for all 76 existing Schemas
   and all 14 existing fixtures before any generation, then recompute it from Git blobs after every
   generator and at final review;
4. prove `MODELS[:76]` name/order and all 76 committed Schema bytes unchanged;
5. append only the exact approved top-level models in the frozen order;
6. keep every inline definition out of the top-level Registry;
7. implement explicit projection functions and every NUL-terminated domain;
8. provide every-field mutation tests, self-field exclusion tests and cross-domain non-aliasing
   tests;
9. test exact upper-bound expiry for Qualification, Manifest, Observation, Request, Record and
   Receipt;
10. test every five-value result and every nine-category evidence condition;
11. test missing/cyclic/non-ancestor-closed chains as failures, stale evidence as `NOT_ASSESSED`,
    and structurally complete unreconciled forks as `CONFLICT`;
12. test `SUPERSEDED`, privacy complaint, dispute, Provider terms drift, retention/deletion
    violation and prohibited training;
13. prove an unauthorized historical submission cannot be cured by later review;
14. prove Manifest Checker/Qualifier and all Maker/Checker separation rules;
15. prove a Receipt parser cannot substitute for complete replay;
16. prove no Candidate mutation, promotion, AssetVersion/Bible output or Provider/Runtime import;
17. use only first-party synthetic text, evidence and media;
18. provide a complete human known-answer review packet before Draft-to-Ready; and
19. keep all authority fields exact false/zero in positive and negative cases.

Committed-byte comparison on Windows must use Git blob or canonical-LF bytes. A CRLF working-tree
checkout is not evidence that committed Schema bytes changed or remained unchanged.

The baseline starts from commit `a3a200bab2f70203d3cdc743054eb20f035f91b2`. In addition to the
complete 76-entry reviewed manifest, these four ADR-043 tail Schema Git blobs are explicit canaries:

| Schema | Committed byte size | SHA-256 |
| --- | ---: | --- |
| `CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1.schema.json` | 17,183 | `5c26b4755967f276038a60e725965497b53384d406989e1b186e27701cb4ce88` |
| `CreativeSampleGeneratedReferenceCandidateV1.schema.json` | 11,445 | `58a322669c7aeec8dcefafafdffea11757cfd3512a40acccf56722be5f5fd565` |
| `CreativeSampleGeneratedReferenceCandidateQualificationRequestV1.schema.json` | 9,926 | `192e41657d55a4d48287938462a323071cb5678fcc521d01edab16ee88d652dd` |
| `CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1.schema.json` | 11,371 | `fe38cc03c0544e49bb08ca00827df80fbba01e5541479bcf5b49599bc513c0e1` |

The complete 76-Schema/14-fixture baseline remains required; the canaries never substitute for it.

## Future codegen boundary

If code generation is separately approved:

- the implementation module is fixed as
  `src/sdc/generated_reference_rights_current_status_codegen.py` and its codegen test as
  `tests/test_generated_reference_rights_current_status_codegen.py`;
- the human source path is fixed as
  `tests/fixtures/visual_prompt_profiles/generated-reference-rights-current-status/reviewed-known-answer-source-v1.json`;
- the only derived update target is fixed as
  `tests/fixtures/visual_prompt_profiles/generated-reference-rights-current-status/generated-known-answer-v1.json`;
- the reviewed source is at most 2,097,152 bytes, the derived fixture at most 4,194,304 bytes, both
  have maximum nesting depth 24 and each generic container has at most 256 items;
- repository root is derived only from the codegen module's fixed location; `--root`, current
  directory and environment overrides are prohibited;
- the CLI requires exactly one of `--check` or `--update`; neither or both fails before fixture
  admission, and no third mode is accepted;
- `--check` must be fully read-only and must not share any reachable write path;
- `--update` may create or replace bytes only through one direct file descriptor for that exact
  derived target after path admission; an absent target uses create-exclusive admission, an
  existing target must be one regular single-link non-aliased file, and both paths use no
  temporary/rename target. The writer flushes and revalidates path, file identity, link count, size
  and final bytes through pre/post `lstat`/`fstat`-equivalent checks;
- human source fixtures, old fixtures, PNGs, Schemas, ADRs and Catalog files must never be
  overwritten by `--update`;
- after final human source review, the BUILD freezes that exact source byte size and raw SHA-256 as
  code constants and both modes verify them before derivation; any source drift invalidates the
  human approval and cannot be repaired by running `--update`;
- generated fixtures must carry that source raw SHA and both policy digests;
- both modes must reject a symlink, junction, ReparsePoint, non-regular target or non-regular
  ancestor, hard link, source/target alias or path escape, must anchor the resolved target inside
  the exact repository root, and must not discover files recursively;
- `--check` must compare the would-be canonical bytes entirely in memory and must not create a
  temporary file, directory, lock, cache or timestamp update;
- independent known-answer calculators must not call the production projection/hash helper being
  tested; and
- codegen grants no Rights, status, Provider or execution authority.

After adding exactly the reviewed source and derived files, the tracked
`tests/fixtures/visual_prompt_profiles` file count would be the frozen old 14 plus these two exact
paths, or 16. The new read-only check must enter both `make check` and Windows CI. This count is a
path allowlist assertion, not authority to regenerate or modify any old fixture.

The current two expired ADR-043 positive cases must appear only as historical verification or
expiry rejection cases. Any future positive Manifest/current-status known answer requires a new
first-party synthetic Request/Decision timeline inside all exclusive windows.

## Failure behavior

Manifest and formal-document construction uses these stable umbrella codes in this exact priority
order:

```text
EXACT_INPUT_TYPE_REQUIRED
DOCUMENT_RESOURCE_LIMIT_EXCEEDED
CANONICAL_JSON_REQUIRED
CONTRACT_FIELD_INVALID
POLICY_IDENTITY_MISMATCH
SEMANTIC_ID_OR_DIGEST_MISMATCH
UPSTREAM_CLOSURE_MISMATCH
TIME_WINDOW_INVALID_OR_EXPIRED
ROLE_SEPARATION_VIOLATION
MANIFEST_GATE_NOT_PASS
CHAIN_STRUCTURE_INVALID
EVIDENCE_SCOPE_INCOMPLETE
REPLAY_MISMATCH
AUTHORITY_SURFACE_NONZERO
PROHIBITED_BOUNDARY_CONNECTION
```

Generated chain replay, coverage, joint replay, as-of assessment and Receipt build/verify use the
exact per-layer ordered code arrays embedded in the current-status policy projection; the umbrella
list does not replace them. Generated-specific enum and exception types own these values; they do
not alias or broaden imported-real-asset public error types. The coverage error carries optional `replay_code`; joint replay carries
optional `coverage_code` and `replay_code`; as-of assessment carries optional
`joint_replay_code`, `coverage_code` and `replay_code`; Receipt operations carry optional
`assessment_code`, `joint_replay_code`, `coverage_code` and `replay_code`. A wrapper preserves the
exact nested code without parsing or rewriting exception text.

An exact-type error includes subclasses. Contract-field failure includes missing/extra fields,
coercion, scalar substitution, invalid enum/cardinality/order and illegal basis/source pairing.
Closure failure includes subject, purpose, Profile, Prompt, Receipt, media and technical-record
drift. Time failure includes a non-positive/expired Qualification, invalid half-open interval or
caller-overridden deadline during construction. For as-of assessment,
`as_of < evaluated_at` is the ordered `AS_OF_PRECEDES_RECORD_EVALUATION` error, while
`as_of >= status_valid_until` or `as_of >= manifest_valid_until` is a successful `EXPIRED` result,
never `TIME_WINDOW_INVALID_OR_EXPIRED`. Chain-structure failure includes a missing referenced predecessor,
non-ancestor-closed set, cycle, illegal link or malformed reconciliation. Evidence-scope failure
includes category omission, missing explicit referenced closure or favorable-subset selection.

Nested operation errors are preserved before the next outer phase. No outer builder rewrites a
specific nested error into a later generic code. A valid but stale Observation is not a structural
error; it is unusable evidence and yields `NOT_ASSESSED`. A structurally complete unresolved
multi-head fork yields `CONFLICT`. Either can therefore produce `INDETERMINATE` after successful
structural replay.

Structural or replay failure does not become `INDETERMINATE`. `INDETERMINATE` is available only
after the exact Contracts and complete explicitly supplied replay structure are valid but the
policy evidence is unusable, unknown, not assessed or conflicting.

This is the exact replacement for the undifferentiated ADR-043 chain sentence: missing substantive
evidence represented by a structurally valid `NOT_ASSESSED` claim, a stale but structurally valid
target, or a structurally complete unreconciled fork can reduce to `INDETERMINATE`; a missing
referenced document or predecessor, incomplete ancestor closure, malformed fork, cycle or omitted
required Request target is an operation failure and produces no status or Receipt.

No operation may auto-repair, coerce, select another head, refresh a deadline, retry, waive a gate
or create a partial output.

## Rejected alternatives

### Reuse the imported Rights Manifest or Fresh Status types

Rejected because their subject, scope, policy and identity bind imported assets and an imported
Pack/use-plan chain. A union or renamed alias would corrupt released semantics.

### Embed a current-status Receipt in the Manifest

Rejected because the status subject must bind the Manifest. Reverse binding creates an identity
cycle and prevents append-only reassessment.

### Let the Checker action bind the final Manifest SHA

Rejected because the final Manifest binds the Checker action SHA. The independent review-payload
digest is required to avoid an indirect cycle.

### Compress Request, Instruction and Decision into one Record

Rejected for V1 because it obscures Maker/Checker responsibilities and makes independent canonical
review artifacts unavailable merely to reduce Schema count.

### Reuse a positive Qualification Boolean after expiry

Rejected because eligibility is valid only inside the exact Decision interval. A historical
Boolean is not an as-of check.

### Interpret no revocation record as CURRENT

Rejected because absence of a supplied record proves neither absence of an event nor completeness
of sources. Every adverse predicate needs explicit absence evidence.

### Return REVOKED or HELD after the Record window expires

Rejected because stale bounded evidence cannot make a current claim. Historical adverse facts stay
in the Record; the as-of status becomes `EXPIRED` until new evidence is assessed.

### Promote directly into current AssetVersion or Provider input

Rejected because current AssetVersion IDs bind `IMPORTED_APPROVED_MEDIA` and no truthful generated
promotion or multi-role input type exists.

## Risks and treatment

| Severity | Risk | Required treatment |
| --- | --- | --- |
| Blocking | Manifest and status values form a direct digest cycle | Freeze Manifest-first DAG; status binds Manifest; Manifest never binds status |
| Blocking | Manifest action records form an indirect digest cycle | Bind actions to a pre-action review-payload SHA, then bind action SHAs in Manifest |
| Blocking | Expired Qualification is reused or renewed | Enforce the exact half-open Decision interval and require a new Request/Decision |
| Blocking | Later review retroactively cures unauthorized submission, retention or training | Require the historical submission-time gates and state that later review cannot cure absence |
| Blocking | CURRENT is read as global real-world currentness | Require complete finite evidence, limitations and `present_currentness_asserted=false` |
| Blocking | Adverse, expiry and indeterminate precedence drifts | Freeze `EXPIRED > REVOKED > HELD > INDETERMINATE > CURRENT` |
| Blocking | One generic policy category hides missing retention/training evidence | Keep Provider terms, retention/deletion and training as separate required predicates |
| Blocking | Manifest reviewer is not independent of Qualification | Require distinct Manifest Checker and qualifier semantic identities |
| Blocking | No truthful generated promotion type exists | Keep promotion false and defer to a separate ADR |
| Important | Imported Manifest/Fresh Status types are reused | Add generated-specific models, policies and domains only |
| Important | Existing 76 Schemas or 14 fixtures drift | Establish Git-blob baselines and prove byte/order preservation before append |
| Important | Raw byte SHA and semantic digest domains are mixed | Keep raw bytes undomained and every semantic projection independently domain-separated |
| Important | Receipt parsing is treated as replay | Require fresh joint replay for construction and historical verification |
| Important | Reviewer digests are treated as identity authentication | Limit claims to exact retained record separation |
| Important | Private Provider, legal or identity material leaks into Contracts | Store only bounded privacy-minimized refs/digests in portable values |
| Important | QC, Prompt or Catalog metadata grants rights/status | Exclude them from gate and resolver authority |
| Important | Codegen overwrites human or released inputs | Separate read-only check and fixed derived update allowlist |
| Minor | CurrentStatus and imported FreshStatus terminology is confused | Use generated `CurrentStatus` public names and explicit operator documentation |
| Minor | Shared helper refactor changes old validation behavior | Keep first BUILD isolated; consider private refactor only after byte/behavior equivalence |
| Minor | UI or localization changes semantic identities | Keep presentation labels outside projections |

## Non-goals

This Proposed ADR does not approve or specify:

- implementation through proposal or acceptance alone;
- any current Contract, Schema, Registry, fixture or code-generator change;
- real Rights review, real current-status assessment or private evidence processing;
- legal sufficiency, ownership, licensing or commercial-use determination;
- external Provider, reviewer or source authentication;
- a generated AssetVersion, Bible V2, eligible-asset sidecar or promotion decision;
- role-specific media splitting or multi-reference role binding;
- Provider Input Material V2;
- Runtime, Worker, Temporal, PostgreSQL or event integration;
- network, credentials, Provider calls, paid operations, Retry or generation;
- QC automation, publication, posting or release;
- retention/deletion automation or training controls;
- discovery or automatic selection of current/latest/best records;
- automatic renewal, migration, backfill or mutation of historical values;
- a trusted-local filesystem finalizer;
- external Prompt, image, brand, real-person, third-party character, protected-work or sensitive-data
  fixtures; or
- modification of imported-real-asset v2/v3 paths.

## Permitted claims and explicit non-proofs

Only after separate accepted design, implementation, human known-answer review and merge may SDC
claim that:

- one exact positive unexpired Candidate Qualification closure produced one immutable generated
  Rights Manifest under a fixed Maker/Checker policy;
- the Manifest binds exact reviewed scope, evidence and action-record digests without changing the
  Candidate or Decision;
- one exact finite append-only observation set produced one deterministic current-status Record;
- one exact freshly replayed Record produced one historical Receipt at one explicit `as_of`; and
- all documents remain offline and grant zero Provider, Runtime, rights, promotion, publication or
  execution authority.

Even then, SDC may not claim that:

- the Provider Attempt Outcome is externally authenticated;
- the Maker, Checker, qualifier or source identity is a verified real person;
- the Prompt, input, output or retained evidence is owned, licensed or commercially usable beyond
  the exact reviewed record;
- `rights_review_performed=true` grants a legal right;
- `CURRENT` proves global reality or remains current after its exact `as_of`;
- absence of supplied revocation evidence proves no revocation exists;
- a Receipt is an approval, current-status oracle or execution token;
- a Manifest or Receipt makes the Candidate an AssetVersion or Provider input;
- a Profile constraint or QC expectation was achieved in the PNG;
- Provider compatibility proves capability, entitlement, availability or authorization;
- promotion, Retry, retention, training, publication or execution is permitted; or
- equal PNG bytes from another Candidate occurrence inherit this closure.

## Consequences

Positive consequences:

- generated media gains a rights-review boundary without corrupting imported-asset semantics;
- Manifest and status identities form a computable append-only DAG;
- review payload, human action and final Manifest identities remain non-circular;
- historical Qualification, Manifest scope and current-status windows remain distinct;
- explicit absence evidence is required before `CURRENT`;
- stale evidence cannot silently remain current;
- Maker/Checker and replay/Receipt responsibilities stay independently reviewable;
- existing 76 Schemas and released products remain append-only compatibility anchors; and
- promotion and execution remain visibly separate future decisions.

Costs and limitations:

- V1 Manifest validity is intentionally capped at 24 hours;
- a new Manifest after expiry requires a new Qualification and review;
- seven new top-level Schemas and multiple replay layers add review overhead;
- every current assessment requires a complete explicit chain set;
- CURRENT remains a finite supplied-evidence conclusion with permanent limitations;
- the Manifest Checker cannot be the Qualification qualifier;
- negative Manifest review creates no portable Manifest;
- no output is promotion eligible or executable; and
- any policy, category, role, time, field, domain or cardinality change requires a versioned decision
  and renewed compatibility review.

## Current task boundary

This task may add only this Proposed ADR file. It must not:

- change the status to Accepted;
- modify any Contract, Schema, fixture, test, source or codegen file;
- create a branch, commit, PR or release;
- run schema generation, tests, formatting or code generation;
- create a Manifest, status document, Receipt or promoted value; or
- begin BUILD, promotion, Provider-input or Runtime work.
