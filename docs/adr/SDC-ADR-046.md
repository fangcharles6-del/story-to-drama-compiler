# SDC-ADR-046: Generated Reference Eligible-Asset Role-Binding Boundary

- Status: Accepted
- Date: 2026-08-31
- Depends on: SDC-ADR-039 / Deterministic Visual Prompt Profiles
- Projection dependency: SDC-ADR-040 / Visual Prompt Profiles Phase 1 Projection Manifest
- Compiler-boundary dependency: SDC-ADR-041 / Visual Prompt Profiles Compiler Integration
- Reference-Prompt dependency: SDC-ADR-042 / Character and Scene Reference Prompt Compiler Input
  Boundary
- Candidate/Qualification dependency: SDC-ADR-043 / Generated Reference Candidate Provenance and
  Qualification Boundary
- Rights/current-status dependency: SDC-ADR-044 / Generated Reference Rights Manifest and
  Current-Status Evidence Boundary
- Promotion dependency: SDC-ADR-045 / Generated Reference Eligible-Asset Sidecar Promotion
  Boundary
- Baseline: `cd78be1ea713ba6ae275963a7e5df9743d3dc8d2`
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: one exact explicitly supplied post-promotion Eligible-Asset Sidecar occurrence, the
  same exact locally supplied PNG bytes, one exact purpose-compatible reference-role literal, one
  complete explicitly supplied upstream and fresh-status closure, exact caller-supplied primary
  Bible/AssetVersion snapshots and privacy-minimized retained Role-Binding review records;
  first-party synthetic review data only
- Network/spend boundary: zero network calls, zero credential reads, zero Provider requests, zero
  authorized Attempts and zero authorized cost

## Context

SDC now has accepted and implemented offline boundaries for deterministic Visual Prompt Profiles,
reference Prompt compilation, one generated-reference Candidate occurrence, human Qualification,
generated Rights Manifest/current-status evidence and an Eligible-Asset Sidecar Promotion.

The accepted ADR-045 Promotion output is deliberately historical and role-free. A positive
`CreativeSampleGeneratedReferenceEligibleAssetSidecarV1` records that one exact generated Candidate
occurrence passed one scoped Promotion review at one exact `promotion_at`. It retains the exact raw
PNG identity and upstream closure, supplements one unchanged active imported primary AssetVersion
and routes the exact Sidecar to a later manual role-binding review. It does not state that any
Profile role is present in the pixels, does not create a role-specific media slot and is not
Provider-input eligible.

The current Registry contains exactly 86 top-level models. The first 83 entries and committed
Schema bytes predate ADR-045; ADR-045 appended only its Request, Decision and Eligible-Asset
Sidecar. The tracked `tests/fixtures/visual_prompt_profiles` tree contains exactly 18 paths: the 16
pre-ADR-045 frozen paths plus the two ADR-045 Promotion known-answer paths. All existing Contract,
Schema, fixture and deterministic identity bytes are released compatibility boundaries.

ADR-039 through ADR-042 define seven reference-role literals. A Character reference Profile carries
the complete ordered tuple:

```text
CHARACTER_IDENTITY_SHEET
CHARACTER_POSE_REFERENCE
CHARACTER_EXPRESSION_REFERENCE
```

A Scene reference Profile carries the complete ordered tuple:

```text
SCENE_ESTABLISHING_REFERENCE
SCENE_LIGHTING_REFERENCE
SCENE_MATERIAL_REFERENCE
SCENE_PROP_PLACEMENT_REFERENCE
```

Those tuples describe Prompt and reference-sheet layout semantics. They do not prove that an output
contains a corresponding view, do not identify a crop or panel and do not create three Character or
four Scene media values. Profile membership, Prompt text, Prompt receipts, QC expectations, file
names and image layout are therefore not role-assignment evidence.

ADR-045 defines the remaining role-binding step as a later, separate human and Contract boundary.
It also requires every later consumer to perform its own fresh current-status evaluation. This
Accepted ADR defines that missing role-binding-only boundary. It deliberately stops before a
multi-reference BindingSet, Provider Input Material, Provider request or execution design.

## Decision summary

This Accepted decision constrains any separately authorized first BUILD to:

1. represent one atomic, non-exclusive historical association between one exact positive
   ADR-045 Eligible-Asset Sidecar occurrence, its same whole unsplit PNG occurrence and one exact
   purpose-compatible reference role;
2. add exactly three new top-level formal Contracts only after separate BUILD authorization:
   Role-Binding Request, Role-Binding Decision and positive Eligible-Asset Role Binding;
3. require one human Role-Binding Maker to prepare the exact Request and one independent human
   Role-Binding Checker to record the final decision;
4. require complete fresh ADR-044 current-status joint replay twice: once at Request preparation and
   again at the exact final `binding_at`;
5. require safe re-admission and exact byte verification of bytes equal to the original Candidate
   PNG at both operations; no thumbnail, URL, alternate bytes, crop or derived media may substitute
   for them;
6. require the requested role to be an explicit human-selected member of the exact full
   purpose-compatible role tuple already bound by the exact ADR-042 Artifact;
7. separate compiler-verifiable role membership from human review of whether the exact whole PNG is
   suitable for the requested role;
8. rebuild the exact active imported primary AssetVersion binding at Request time and finalization,
   require Request-time equality with the ADR-045 Sidecar, map valid final drift to a negative gate,
   require final equality only for a positive Binding and never replace or mutate it;
9. copy the exact Manifest-reviewed Rights scope without widening, narrowing, reordering, extending
   or reinterpreting it, and require a separate bounded human acknowledgement of the role/scope
   association without granting Rights;
10. make every positive Binding immutable, append-only, occurrence-specific, historical and
    explicitly non-exclusive;
11. create no global uniqueness, complete role-set, latest, best, current, supersession or
    Provider-slot claim; and
12. preserve complete zero Provider, Runtime, network, credential, cost, Retry, asset-use,
    publication, retention and training authority.

A conforming positive V1 output would mean only:

> At one explicit historical `binding_at`, one independent human Role-Binding Checker approved an
> occurrence-specific, non-exclusive association between one exact post-promotion Eligible-Asset
> Sidecar's unchanged whole PNG occurrence and one exact purpose-compatible reference-role literal,
> after complete supplied-evidence replay and exact byte verification.

It would not mean that the PNG was cropped or split, that the role is exclusive, that a complete
Character or Scene role set exists, that the Binding remains current, that the media became a V1
AssetVersion or active Bible binding, or that any Provider input, execution, publication or asset-use
authority exists.

## Acceptance record and implementation gate

This ADR records acceptance of exactly the architecture decisions explicitly recorded here. This
acceptance authorizes no Contract, Schema, Registry, fixture, source, test, codegen, CI, Makefile or
implementation change. It authorizes no Role-Binding Request, Decision or Binding, and no actual
media review or role assignment.

Acceptance does not authorize BUILD. A BUILD would require separate explicit authorization, a newly
verified authoritative clean `main`, an isolated `codex/` implementation branch and the closed
changed-file allowlist below.

Human review confirms:

1. the atomic non-exclusive one-Sidecar/one-role representation;
2. the exact seven role literals, purpose partition and canonical order;
3. the exact three-model family and Registry append order;
4. the complete supplied closure and two-replay time rules;
5. the exact primary-binding and Rights-scope rules;
6. the Maker/Checker identity-separation matrix;
7. the target, review-payload, Request, Decision and Binding identity DAG;
8. the policy projection, policy SHA-256, gate order, issue order and failure behavior;
9. positive pair atomicity and negative/indeterminate Decision-only behavior;
10. resource, privacy, canonical-codec and digest-domain limits;
11. the complete zero-authority surface, Provider-input isolation and non-goals;
12. the 86-Schema and 18-fixture compatibility gates; and
13. the exact future BUILD changed-file allowlist.

This section is the acceptance record for the 13 choices above, the exact policy projection and the
complete zero-authority boundary. It is not a BUILD authorization.

## Frozen upstream compatibility boundary

This Accepted ADR does not narrow, supersede or reinterpret ADR-039 through ADR-045. In particular,
a conforming future BUILD must not change the behavior, serialized value, Schema or deterministic
identity of:

- `compile_story`, `compile_creative_sample` or any existing compiler product;
- `CreativeSampleSpec`, `CreativeSampleCompilation`, `NIRV2`, `PIRV2`, `StoryboardShotV2`,
  `GenerationJob`, `JobGraph` or `AssemblyPlan`;
- `CharacterAssetVersion`, `CharacterBible`, `SceneAssetVersion`, `SceneBible` or
  `CharacterAssetBinding`;
- any existing Visual Prompt Profile, Catalog, Snapshot, render input, Prompt, Prompt Receipt,
  Catalog Receipt, narrative Prompt sidecar or reference Prompt Artifact;
- every ADR-043 Provider Attempt Outcome, Candidate, Qualification Request and Qualification
  Decision;
- every ADR-044 Rights Manifest, current-status Observation, Request, Instruction, Decision, Record,
  Receipt, replay, coverage or assessment value;
- every ADR-045 Promotion Request, Promotion Decision, Eligible-Asset Sidecar, primary-binding
  projection, review payload, gate, ID or digest domain;
- any v1 or Creative Sample v2 Prompt, ID, idempotency key, fixture or frozen regression byte;
- the first 86 `sdc.schemas.MODELS` entries and all 86 current committed JSON Schema bytes;
- all 18 current tracked `tests/fixtures/visual_prompt_profiles` paths and their bytes;
- Temporal/PostgreSQL workflow ownership, Runtime state or persistence;
- Provider submit, inspect, download or cancel behavior;
- `SUBMISSION_UNKNOWN -> HUMAN_GATE`, `STOP-2` or any Retry decision;
- QC technical PASS/FAIL or advisory semantic-QC behavior; or
- publication, retention, deletion or training controls.

No existing Contract may gain an optional field, union member, enum literal or duck-typed
compatibility path. The existing `ReferenceAssetType` literals retain their Profile-recipe meaning;
this decision would copy the exact closed literal set into a new downstream role-binding target and
would not change that enum.

Generated bytes remain permanently ineligible for the existing
`provenance=IMPORTED_APPROVED_MEDIA` literal. A Role Binding would not validate as an AssetVersion,
Bible binding, `InputMaterial`, `ProviderRequest`, Provider route or executable asset.

## Terminology and lifecycle

This Accepted decision uses the following terms narrowly:

1. **Eligible-Asset Sidecar occurrence**: one exact positive ADR-045 Sidecar, including its exact
   Promotion Decision, Candidate occurrence and raw PNG identity. It is historical and is not
   presently current by itself.
2. **Reference role**: one of the exact seven frozen literals above, admitted only for its exact
   Character or Scene purpose. It is not a Provider slot, crop label or generated-media identity.
3. **Role-Binding target**: one digest-closed inline association proposal over one exact Sidecar
   occurrence, the same whole PNG occurrence and one exact reference role. It is non-exclusive and
   does not claim a complete role set.
4. **Role-Binding Maker**: the retained semantic identity that prepares one exact Request. The term
   does not authenticate a real person, competence, employment or organizational authority.
5. **Role-Binding Checker**: the independent retained semantic identity that records the final
   scoped decision after viewing a rendering decoded from the exact admitted PNG bytes. The term
   does not authenticate legal or organizational authority.
6. **Role-Binding Request**: one immutable finite packet prepared for review over one exact target,
   exact upstream closure, Request-time current-status replay, exact primary binding and exact
   reviewed Rights scope.
7. **Role-Binding Decision**: one immutable positive, negative or indeterminate human decision over
   one exact Request after final replay at `binding_at`.
8. **Eligible-Asset Role Binding**: one immutable positive historical value created only together
   with a positive Decision. It supplements but never mutates the Sidecar or primary AssetVersion.
9. **Non-exclusive association**: the Binding makes no claim that the Sidecar is absent from another
   independently reviewed Binding or that another Sidecar is absent for the same role.
10. **Binding evidence horizon**: the earliest exclusive upstream deadline copied into a positive
    Binding. It never asserts present currentness.

The accepted lifecycle is:

```text
positive ADR-045 Eligible-Asset Sidecar
  -> exact Role-Binding target for one role
  -> fresh CURRENT replay at requested_at
  -> Role-Binding Request
  -> fresh status replay at binding_at; CURRENT is required only for approval
  -> Role-Binding Decision
       -> REJECT / INDETERMINATE: Decision only
       -> APPROVE: Decision + Eligible-Asset Role Binding
  -> no Provider-input or execution transition in this ADR
```

No state would mutate an earlier document.

## Atomic non-exclusive representation choice

This Accepted decision chooses one atomic historical Binding per
`(exact Sidecar occurrence, exact role)` review. It does not choose a bounded BindingSet.

The same Sidecar occurrence could therefore appear in another independently reviewed historical
Binding for another role, or in a later re-review of the same role. V1 could neither discover nor
prove that no such document exists. Every portable positive Binding would directly carry:

```text
binding_exclusivity_asserted=false
complete_role_set_asserted=false
global_role_uniqueness_asserted=false
current_role_binding_asserted=false
supersedes_role_binding=false
```

Those exact false values are part of the semantic identity. They prevent a consumer from treating
one stateless document as evidence of global uniqueness, completeness, currentness or supersession.

A future multi-reference consumer would have to accept an explicitly supplied finite set of exact
Bindings and define its own role uniqueness, Sidecar-occurrence uniqueness, duplicate-byte,
canonical-order and partial/full-set rules. This decision defines none of those rules and grants no
permission to begin that work.

If exclusivity were required instead, this ADR would have to be revised or superseded by a
separately reviewed bounded BindingSet design. A database uniqueness constraint, filesystem scan or
latest-record lookup cannot repair the absence of portable set closure.

## Exact role vocabulary and purpose mapping

The Role-Binding target would use this exact closed purpose mapping:

```text
CHARACTER_REFERENCE_ASSET:
  0 CHARACTER_IDENTITY_SHEET
  1 CHARACTER_POSE_REFERENCE
  2 CHARACTER_EXPRESSION_REFERENCE

SCENE_REFERENCE_ASSET:
  0 SCENE_ESTABLISHING_REFERENCE
  1 SCENE_LIGHTING_REFERENCE
  2 SCENE_MATERIAL_REFERENCE
  3 SCENE_PROP_PLACEMENT_REFERENCE
```

The target would carry the exact complete tuple for its purpose and one exact
`selected_reference_role` member. Character/Scene crossing, unknown literals, a reordered tuple,
a subset tuple or a duplicate role would fail before Request construction.

The Request operation would receive `selected_reference_role` as one explicit caller-supplied value
proposed by the Maker. The builder would receive the exact ADR-042 Artifact, fully revalidate its
released identity, Profile Snapshot, recipe and complete role tuple, and construct the target from
that explicit value. It would derive the purpose-compatible tuple from the exact Artifact; the
caller could not replace or narrow it. The subsequent Maker action would confirm and bind the same
selected member and exact target. Code could verify purpose and membership but could not select,
recommend, infer or rank the role.

Profile membership would produce only a compiler-derived membership gate. It would not establish
pixel meaning. A separate Checker result would decide whether the exact whole PNG occurrence is
suitable for the selected role.

## Future inline Role-Binding target

The three top-level Contracts would share one strict frozen inline target definition:

```text
GeneratedReferenceEligibleAssetRoleBindingTargetV1
```

Its exact fields would be:

```text
target_profile=sdc.generated-reference-eligible-asset-role-binding-target.v1
target_sha256: LowerSha256
eligible_asset_sidecar_id: PortableId
eligible_asset_sidecar_sha256: LowerSha256
promotion_decision_id: PortableId
promotion_decision_sha256: LowerSha256
reference_prompt_artifact_sha256: LowerSha256
provider_attempt_outcome_id: PortableId
provider_attempt_outcome_sha256: LowerSha256
candidate_id: PortableId
candidate_sha256: LowerSha256
output_ordinal=0
media_type=image/png
media_content_sha256: LowerSha256
media_size_bytes: exact integer in 1..67108864
media_technical_record_sha256: LowerSha256
asset_purpose: CHARACTER_REFERENCE_ASSET | SCENE_REFERENCE_ASSET
subject_id: PortableId
profile_id: PortableId
profile_version: SemanticVersion
profile_sha256: LowerSha256
catalog_version: SemanticVersion
catalog_sha256: LowerSha256
reference_asset_types: exact purpose-derived complete tuple
selected_reference_role: exact purpose-compatible member
media_binding_scope=WHOLE_UNSPLIT_UNTRANSFORMED_COMPOSITE_PNG_OCCURRENCE
binding_exclusivity_asserted=false
complete_role_set_asserted=false
global_role_uniqueness_asserted=false
crop_applied=false
split_applied=false
transform_applied=false
derived_media_created=false
provider_slot_embedded=false
```

The target semantic projection would exclude only `target_sha256`. It would include every other
field in the documentation order above, with canonical JSON object-key sorting. Its identity would
remain occurrence-specific even when another Candidate has equal PNG bytes.

The target contains no path, URL, crop box, panel coordinate, Provider task identifier, Provider
slot, route, current/latest pointer or human action.

Copying the exact Profile and Catalog identities from the Artifact would preserve traceability only.
It would not re-prove historical Profile admission unless the exact historical Catalog were
separately available under its released resolver boundary. Role membership validation against the
Artifact Snapshot would not make that stronger claim.

## Role-Binding review payload

The digest-only review payload would contain exactly:

```text
policy_id
policy_version
policy_document_sha256=fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233
requested_role_binding_target: GeneratedReferenceEligibleAssetRoleBindingTargetV1

promotion_request_id
promotion_request_sha256
promotion_decision_id
promotion_decision_sha256
eligible_asset_sidecar_id
eligible_asset_sidecar_sha256
promotion_at
promotion_evidence_valid_until

qualification_request_id
qualification_request_sha256
qualification_decision_id
qualification_decision_sha256
qualification_valid_until
manifest_id
manifest_sha256
manifest_valid_until
reviewed_rights_scope
requested_primary_asset_binding

status_subject_closure_id
status_subject_closure_sha256
requested_status_record_id
requested_status_record_sha256
requested_status_receipt_id
requested_status_receipt_sha256
requested_explicit_chain_set_sha256
requested_coverage_set_sha256
requested_joint_replay_sha256
requested_as_of_assessment_sha256
requested_as_of
requested_as_of_status=CURRENT
requested_status_valid_until

requested_at
request_valid_until
media_binding_scope=WHOLE_UNSPLIT_UNTRANSFORMED_COMPOSITE_PNG_OCCURRENCE
explicit_human_role_selection=true
profile_role_membership_verified=true
role_binding_exclusivity_asserted=false
complete_role_set_asserted=false
global_role_uniqueness_asserted=false
crop_requested=false
split_requested=false
transform_requested=false
derived_media_requested=false
provider_input_requested=false
complete zero-authority surface
```

The payload would contain no Maker/Checker identity, action, Request, Decision or Binding field. Its
digest would bind the complete finite packet presented to the Maker while keeping the identity DAG
acyclic. The Request would reproduce every payload field exactly and add only its own identity,
Maker action/identity anchors, bounded basis and request state.

## Exact offline supplied closure

Request preparation would receive only explicitly supplied values:

- one exact ADR-042 `CreativeSampleReferenceVisualPromptArtifactV1`;
- one exact ADR-043 Provider Attempt Outcome, Candidate, Qualification Request and positive
  unexpired Qualification Decision;
- the same exact caller-designated local PNG bytes closed by that Candidate;
- one exact ADR-044 generated Rights Manifest and its exact retained Rights review records;
- one complete Request-time ADR-044 current-status closure, including every exact supplied
  Observation, branch, Request, Instruction, Decision, Record, Receipt and retained role record;
- one exact ADR-045 Promotion Request, positive Promotion Decision and Eligible-Asset Sidecar plus
  all exact retained Promotion role records needed for full verification;
- one exact caller-supplied CharacterBible/CharacterAssetVersion or SceneBible/SceneAssetVersion
  pair matching the Sidecar's primary binding;
- one privacy-minimized Role-Binding Maker identity record and exact Maker action;
- one explicit `requested_at` UTC second and bounded Request basis; and
- no storage lookup, Catalog discovery, environment configuration, credential, network, clock,
  randomness or mutable global selection policy.

Decision finalization would receive the same exact upstream closure, exact PNG bytes, exact Request,
a complete final current-status closure at `binding_at`, exact final caller-supplied Bible and
AssetVersion snapshots, one privacy-minimized Role-Binding Checker identity record and exact Checker
action. It could not accept an ID-only, digest-only, Receipt-only or copied-`CURRENT` substitute.

Every formal value would be exact-type revalidated under its released type. Every released semantic
projection and digest needed by the closure would be recomputed under its original domain. A
matching outer SHA could not bypass an invalid nested value.

## Exact PNG admission and no-derived-media boundary

The local PNG path would be transport-only input. Both Request preparation and finalization would:

1. accept one explicitly named local path only;
2. reject directories, symlinks and Windows ReparsePoints;
3. resolve and open the exact file under the accepted safe-file procedure;
4. hold one handle while checking file identity, bounded size and drift;
5. read at most 67,108,864 bytes;
6. validate the frozen PNG technical record;
7. recompute exact raw PNG SHA-256 and size;
8. require equality with the Outcome, Candidate, Promotion Request/Decision, Sidecar and target; and
9. provide the Checker a rendering decoded from those exact admitted bytes rather than a thumbnail,
   URL or independently supplied rendering.

No local path would enter a portable projection. Failure would return no Request, Decision or
Binding and would write no file.

The implementation boundary would have two explicit layers. A safe bounded admission adapter would
perform the path and handle I/O above and return immutable admitted PNG bytes plus the verified
technical/raw-byte result. A pure construction core would receive only those admitted values, the
exact formal closure, retained records and explicit times; it would perform no path lookup or file
I/O. "Same-call" positive pair atomicity below refers to one invocation of that pure construction
core after final admission, not to the outer I/O adapter.

This boundary could prove exact byte equality with the Candidate closure and stable identity of the
opened file during each individual admission operation. It could not prove that a filesystem object
was never copied between operations, nor distinguish two regular files containing the same exact
bytes. Here, "PNG occurrence" would therefore identify the Candidate-bound raw-media occurrence in
the evidence closure, not a unique physical storage object. No physical-file originality or
copy-history claim would be emitted.

No crop, split, mask, panel extraction, resize, transcode, recompression, color conversion or other
derived media may be accepted or created. Derived bytes would be a new media occurrence requiring a
separate provenance, Candidate, Qualification, Rights, Promotion and role-binding lifecycle. They
cannot inherit the original Sidecar or Binding.

## Explicit time, validity and fresh-status replay

All times would be explicit caller-supplied canonical UTC seconds. No ambient clock, grace period,
automatic refresh or deadline extension would exist.

Request preparation would require:

```text
sidecar.promotion_at <= requested_at
request status Receipt as_of == requested_as_of == requested_at
maker_prepared_at == requested_at
requested_at < qualification_valid_until
requested_at < manifest_valid_until
requested_at < requested_status_valid_until
request_valid_until = min(
  requested_at + 86400 seconds,
  qualification_valid_until,
  manifest_valid_until,
  requested_status_valid_until
)
```

Finalization would require:

```text
requested_at <= binding_at < request_valid_until
checker_reviewed_at == binding_at
decision_at == binding_at
final status Receipt as_of == binding_at
binding_at < qualification_valid_until
binding_at < manifest_valid_until
binding_at < final_status_valid_until
```

Every upper bound is exclusive. Equality with any `*_valid_until` value is expired.

The copied `promotion_evidence_valid_until` is an ADR-045 historical traceability horizon only. It
is not a Role-Binding Request or Decision deadline, and crossing it would not by itself require a
new Promotion. A later Request may occur after that historical horizon only when the exact positive
Sidecar still revalidates, Qualification and Manifest remain unexpired, the new Request-time and
final current-status closures both replay under their own exact `as_of` values, and every other
Role-Binding gate passes. The old horizon could never substitute for either fresh replay.

The exact ADR-045 Promotion-final Record, the Role-Binding Request-time Record and the Role-Binding
final Record would form one explicit three-stage monotonic chain over the same exact Status Subject
Closure: the same Candidate, Qualification Decision, Manifest, subject, asset purpose and
current-status policy identity. Each Record would be completely replayed from explicitly supplied
evidence. The
Request-time Record could equal the Promotion-final Record or be one complete monotonic
successor/reconciliation closure; the final Record could equal the Request-time Record or be one
complete monotonic successor/reconciliation closure.

At both transitions, a prior target anchor would be exactly
`(observation_id, observation_sha256, chain_sha256)` with its prior zero-based target ordinal
excluded. Every prior target would have to remain a next-stage target or its exact Observation would
have to be a complete ancestor of an explicitly supplied successor/reconciliation target that
closes every prior branch. Thus Request construction would first prove that no Promotion-final
target, occurrence or branch was omitted, substituted, rewritten or detached; finalization would
then prove the same property from Request-time to `binding_at`. Each later Record would derive its
own canonical target ordinals. Additional occurrences could enter only as complete explicitly
supplied chains. No Receipt, Sidecar ID/SHA, storage lookup or favorable-subset selection could
substitute for either cross-Record coverage proof.

Only final `CURRENT` status could support a positive Binding. `EXPIRED`, `REVOKED` or `HELD` would
produce a valid negative gate; `INDETERMINATE` would produce an indeterminate gate. Structural
replay failure would produce no formal result.

## Primary binding and Rights-scope preservation

Request preparation and finalization would each rebuild the exact
`GeneratedReferencePromotionPrimaryAssetBindingV1` from the exact supplied Bible and active
AssetVersion. The Request-time value would have to equal the Sidecar's exact `primary_asset_binding`.
The final value would have to retain the same subject and purpose and would be compared to the
Request and Sidecar.

A malformed, forged or cross-subject binding would be structural failure. A valid final Bible whose
same-subject/purpose active AssetVersion differs from the Request would produce
`PRIMARY_BINDING_NO_LONGER_ACTIVE`, no positive Binding and no mutation.

The exact ADR-044 `reviewed_rights_scope` would be copied from the Manifest through the Promotion
values into every new formal value without change. Tuple expansion, narrowing, reordering, renewal,
deadline extension or reinterpretation would fail closed.

Because allowed-use codes are bounded portable codes rather than machine-understood role
permissions, code could not infer that a selected role falls within the reviewed scope. The Checker
would record a separate bounded
`HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED` result and
basis. A positive acknowledgement would mean only that the exact selected role and exact supplied
scope were presented together and that this Role Binding claims no scope expansion. It would not
mean the role is legally "within" that scope and would not create, authenticate or grant Rights or
legal sufficiency.

## Human review and retained identity separation

The accepted design uses two new retained roles:

```text
Role-Binding Maker
Role-Binding Checker
```

Each privacy-minimized identity record would be canonical JSON with exactly:

```text
document_profile=sdc.privacy-minimized-human-reference.v1
identity_namespace: PortableId
identity_ref: PortableId
```

The Role-Binding Maker action would be `1..262144` canonical JSON bytes with exactly:

```text
document_profile=sdc.generated-reference-eligible-asset-role-binding-request-preparation-action.v1
action=PREPARED_GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_REQUEST
policy_id
policy_version
policy_document_sha256=fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233
role_binding_review_payload_sha256
target_sha256
selected_reference_role
requested_primary_asset_binding_sha256
requested_status_receipt_sha256
actor_ref_sha256: raw SHA-256 of the Maker identity record
prepared_at == requested_at
request_basis: bounded human text
```

The Role-Binding Checker action would be `1..262144` canonical JSON bytes with exactly:

```text
document_profile=sdc.generated-reference-eligible-asset-role-binding-decision-action.v1
action=RECORDED_GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_DECISION
policy_id
policy_version
policy_document_sha256=fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233
request_id
request_sha256
target_sha256
selected_reference_role
final_status_receipt_sha256
final_primary_asset_binding_sha256
actor_ref_sha256: raw SHA-256 of the Checker identity record
reviewed_at == binding_at
exact_role_and_reviewed_rights_scope_presented_without_expansion_result: PASS | FAIL | INDETERMINATE
exact_role_and_reviewed_rights_scope_presented_without_expansion_basis: bounded human text
whole_composite_role_suitability_result: PASS | FAIL | INDETERMINATE
whole_composite_role_suitability_basis: bounded human text
non_exclusive_no_transform_boundary_result: PASS | FAIL | INDETERMINATE
non_exclusive_no_transform_boundary_basis: bounded human text
gate_results: exact ordered tuple of 12 GeneratedReferenceRoleBindingGateResultV1 values
binding_issue_codes: exact ordered tuple with 0..5 items
decision_basis: bounded human text
decision:
  APPROVE_ELIGIBLE_ASSET_ROLE_BINDING
  | REJECT_ELIGIBLE_ASSET_ROLE_BINDING
  | INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING
binding_materialization_allowed: exact boolean derived from decision
```

Before the Checker action could be admitted, the compiler would derive every compiler-sourced gate
from the exact final closure and combine those results with the three bounded Checker findings. The
action's complete gate tuple, issue tuple, decision and materialization flag would have to equal the
policy derivation exactly. The formal Decision would copy all four values and `decision_basis`
exactly from the admitted Checker action. Any mismatch would be structural failure and produce no
Decision or Binding. Thus the Checker would record the final scoped decision without being able to
override a compiler-derived gate or issue mapping.

The Checker could not change the target or selected role. A different role would require a new
Maker action and Request.

The exact `(identity_namespace, identity_ref)` tuple of the Role-Binding Checker would have to differ
from every one of:

- the Role-Binding Maker;
- the ADR-043 Qualification Qualifier;
- the ADR-044 Manifest Checker;
- the ADR-045 Request-time Status Checker;
- the ADR-045 final Status Checker;
- the ADR-045 Promotion Checker;
- the Role-Binding Request-time Status Checker; and
- the Role-Binding final Status Checker.

The Role-Binding Maker would have no required separation from exactly these baseline upstream
retained roles: ADR-043 Qualification Request Preparer and Qualifier; ADR-044 Manifest Maker and
Checker; ADR-045 Request-time Status Preparer and Checker, final Status Preparer and Checker,
Promotion Maker and Promotion Checker; and this Role-Binding operation's Request-time Status
Preparer and Checker and final Status Preparer and Checker. This closed V1 permission would not
automatically expand if a future ADR introduced another role. The Maker could never equal the
Role-Binding Checker. Every supplied identity and action record would be admitted, canonicalized
and rehashed. Semantic tuple equality, not hash inequality alone, would enforce role separation.

Action digests would have to be distinct from one another and from every formal semantic digest,
Prompt/PNG raw digest and external evidence digest. An identity-record raw digest could repeat only
when byte-identical identity records are deliberately reused by roles whose tuple equality the
matrix permits.

These rules prove only deterministic separation among supplied retained records. They do not
authenticate a natural person, legal identity, competence, employer, ACL, organizational approval
or signing authority.

Likewise, positive fields such as `explicit_human_role_selection=true`,
`role_binding_review_performed=true` and `role_binding_performed=true`, and the presence of a
Checker action tied to an exact-byte rendering, would prove only that the supplied retained-record
closure makes those bounded claims. They could not prove that a natural person actually selected a
role, viewed a rendering or exercised authenticated authority. Operational identity and review
assurance remain outside this Contract boundary.

## Acyclic identity DAG

The accepted identity graph is one-way:

```text
exact ADR-042/043/044/045 closure + exact whole PNG + selected role
  -> Role-Binding target
  -> Request-time status replay + exact primary binding + exact Rights scope
  -> Role-Binding review payload
  -> Role-Binding Maker action
  -> Role-Binding Request
  -> final status replay + final primary binding + Role-Binding Checker action
  -> Role-Binding Decision
  -> positive Eligible-Asset Role Binding
```

The review payload would contain no Maker or Checker action. The Maker action would bind the review
payload and target. The Request would bind both. The Checker action would bind the exact Request,
target, final Receipt, final primary binding, human results, complete gate tuple, issue tuple,
decision and materialization flag, but no Decision or Binding identity. The Decision would bind the
Checker action and copy those decision fields exactly. The positive Binding would bind the
Decision.

The Request and Decision would not embed a future Binding ID. After the final safe admission adapter
returned exact bytes, the positive Decision and Binding would be constructed and revalidated
together in one pure-core in-memory call. No placeholder identity, post-construction mutation or
second-pass identity rewrite would exist.

## Frozen accepted policy projection

The following JSON object and its compact canonical bytes received human review as part of this
acceptance. Object keys are sorted by the ADR-040 compact canonical codec; array order is semantic:

```json
{
  "binding_cardinality_rule": "ONE_EXACT_SIDECAR_OCCURRENCE_TO_ONE_ROLE_PER_DOCUMENT_NON_EXCLUSIVE",
  "binding_request_max_age_seconds": 86400,
  "binding_scope": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SINGLE_ROLE_BINDING_ONLY",
  "canonical_codec": "ADR_040_PERSISTENT_AND_COMPACT_CANONICAL_JSON",
  "catalog_rule": "COPY_EXACT_ARTIFACT_SNAPSHOT_IDENTITY_NO_HISTORICAL_CATALOG_READMISSION_CLAIM",
  "checker_action_rule": "FULL_GATE_ISSUE_DECISION_AND_MATERIALIZATION_VALUES_EXACTLY_COPIED_TO_FORMAL_DECISION",
  "cross_document_linkage_rule": "ALL_SHARED_REQUEST_DECISION_AND_POSITIVE_BINDING_FIELDS_EXACTLY_EQUAL_UNDER_CLOSED_MATRIX",
  "decision_mapping": {
    "all_pass": "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
    "any_fail": "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
    "otherwise": "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING"
  },
  "file_admission_layer_rule": "SAFE_BOUNDED_PATH_IO_ADAPTER_THEN_NO_IO_PURE_CONSTRUCTION_CORE",
  "final_record_prior_target_anchor": "OBSERVATION_ID_PLUS_OBSERVATION_SHA256_PLUS_CHAIN_SHA256_ORDINAL_EXCLUDED",
  "final_record_prior_target_coverage_rule": "EACH_PRIOR_TARGET_REMAINS_FINAL_TARGET_OR_IS_COMPLETE_ANCESTOR_OF_FINAL_SUCCESSOR_OR_RECONCILIATION_TARGET_WITH_EVERY_PRIOR_BRANCH_COVERED",
  "final_record_rule": "SAME_OR_NEW_COMPLETE_RECORD_SAME_STATUS_SUBJECT_MONOTONIC_OCCURRENCE_AND_BRANCH_CLOSURE_NO_DISCOVERY",
  "gate_order": [
    "EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR",
    "EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
    "POSITIVE_UNEXPIRED_QUALIFICATION",
    "VALID_GENERATED_RIGHTS_MANIFEST",
    "CURRENT_STATUS_AT_ROLE_BINDING",
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT",
    "ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP_EXACT",
    "REVIEWED_RIGHTS_SCOPE_UNCHANGED",
    "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED",
    "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED",
    "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED",
    "ROLE_BINDING_REVIEWER_SEPARATION"
  ],
  "gate_source_result_mapping": {
    "CURRENT_STATUS_AT_ROLE_BINDING": {
      "basis": "COMPILER_REPLAYED_GENERATED_CURRENT_STATUS_AT_ROLE_BINDING",
      "result_mapping": {
        "CURRENT": "PASS",
        "EXPIRED": "FAIL",
        "HELD": "FAIL",
        "INDETERMINATE": "INDETERMINATE",
        "REVOKED": "FAIL"
      },
      "source": "COMPILER_DERIVED"
    },
    "EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA": {
      "basis": "COMPILER_REVALIDATED_EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR": {
      "basis": "COMPILER_REVALIDATED_EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED": {
      "allowed_results": ["PASS", "FAIL", "INDETERMINATE"],
      "basis": "BOUNDED_CHECKER_TEXT",
      "source": "CHECKER_ACTION"
    },
    "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED": {
      "allowed_results": ["PASS", "FAIL", "INDETERMINATE"],
      "basis": "BOUNDED_CHECKER_TEXT",
      "source": "CHECKER_ACTION"
    },
    "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED": {
      "allowed_results": ["PASS", "FAIL", "INDETERMINATE"],
      "basis": "BOUNDED_CHECKER_TEXT",
      "source": "CHECKER_ACTION"
    },
    "POSITIVE_UNEXPIRED_QUALIFICATION": {
      "basis": "COMPILER_REVALIDATED_POSITIVE_UNEXPIRED_QUALIFICATION",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "REVIEWED_RIGHTS_SCOPE_UNCHANGED": {
      "basis": "COMPILER_REVALIDATED_EXACT_MANIFEST_REVIEWED_RIGHTS_SCOPE",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "ROLE_BINDING_REVIEWER_SEPARATION": {
      "basis": "COMPILER_REVALIDATED_ROLE_BINDING_REVIEWER_SEPARATION",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP_EXACT": {
      "basis": "COMPILER_REVALIDATED_ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT": {
      "basis": "COMPILER_REVALIDATED_FINAL_SUPPLIED_PRIMARY_ASSET_BINDING",
      "result_mapping": {
        "DIFFERENT_ACTIVE_BINDING": "FAIL",
        "EXACT_MATCH": "PASS"
      },
      "source": "COMPILER_DERIVED"
    },
    "VALID_GENERATED_RIGHTS_MANIFEST": {
      "basis": "COMPILER_REVALIDATED_VALID_GENERATED_RIGHTS_MANIFEST",
      "source": "COMPILER_DERIVED_PASS_ONLY"
    }
  },
  "human_gate_order": [
    "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED",
    "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED",
    "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED"
  ],
  "issue_code_order": [
    "STATUS_NOT_CURRENT_AT_ROLE_BINDING",
    "PRIMARY_BINDING_NO_LONGER_ACTIVE",
    "EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTATION_NOT_ACKNOWLEDGED",
    "WHOLE_COMPOSITE_ROLE_SUITABILITY_NOT_APPROVED",
    "NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_NOT_ACKNOWLEDGED"
  ],
  "idempotency_rule": "IDENTICAL_EXPLICIT_INPUTS_ACTION_BYTES_AND_TIMES_PRODUCE_IDENTICAL_VALUES_NO_EXTERNAL_KEY",
  "issue_mapping": {
    "CURRENT_STATUS_AT_ROLE_BINDING": "STATUS_NOT_CURRENT_AT_ROLE_BINDING",
    "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED": "EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTATION_NOT_ACKNOWLEDGED",
    "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED": "NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_NOT_ACKNOWLEDGED",
    "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED": "WHOLE_COMPOSITE_ROLE_SUITABILITY_NOT_APPROVED",
    "SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT": "PRIMARY_BINDING_NO_LONGER_ACTIVE"
  },
  "maker_action_linkage_rule": "REQUEST_MAKER_IDENTITY_ACTION_PAYLOAD_TARGET_ROLE_PRIMARY_STATUS_TIME_AND_BASIS_FIELDS_ALL_EXACTLY_EQUAL",
  "media_rule": "EXACT_WHOLE_UNSPLIT_UNTRANSFORMED_CANDIDATE_PNG_OCCURRENCE_ONLY",
  "multi_binding_rule": "ATOMIC_BINDING_IS_NON_EXCLUSIVE_AND_MAKES_NO_GLOBAL_UNIQUENESS_OR_COMPLETE_SET_CLAIM",
  "policy_id": "sdc.generated-reference-eligible-asset-role-binding-policy",
  "policy_version": "1.0.0",
  "positive_binding_atomicity_rule": "POSITIVE_DECISION_AND_BINDING_SAME_PURE_CALL_NO_PARTIAL_OUTPUT",
  "primary_binding_rule": "REQUEST_BINDING_MUST_EQUAL_SIDECAR_FINAL_BINDING_REBUILT_AND_COMPARED_DIFFERENCE_IS_FAIL_NO_MUTATION",
  "provider_input_rule": "NO_INPUT_MATERIAL_PROVIDER_SLOT_EXECUTABLE_ROUTE_REQUEST_ELIGIBILITY_OR_ROUTING_CLAIM",
  "request_deadline_rule": "MIN_REQUESTED_AT_PLUS_86400_QUALIFICATION_MANIFEST_AND_REQUEST_STATUS_EXCLUSIVE",
  "request_record_prior_promotion_target_anchor": "OBSERVATION_ID_PLUS_OBSERVATION_SHA256_PLUS_CHAIN_SHA256_ORDINAL_EXCLUDED",
  "request_record_prior_promotion_target_coverage_rule": "EACH_PROMOTION_FINAL_TARGET_REMAINS_REQUEST_TARGET_OR_IS_COMPLETE_ANCESTOR_OF_REQUEST_SUCCESSOR_OR_RECONCILIATION_TARGET_WITH_EVERY_PROMOTION_BRANCH_COVERED",
  "request_record_rule": "SAME_AS_PROMOTION_FINAL_OR_NEW_COMPLETE_RECORD_SAME_STATUS_SUBJECT_MONOTONIC_OCCURRENCE_AND_BRANCH_CLOSURE_NO_DISCOVERY",
  "request_status_rule": "FRESH_JOINT_REPLAY_CURRENT_AT_REQUESTED_AS_OF_EQUALS_REQUESTED_AT",
  "resource_limits": {
    "formal_document_max_bytes": 262144,
    "formal_document_min_bytes": 1,
    "generic_container_max_items": 64,
    "human_basis_max_characters": 1000,
    "human_basis_min_characters": 1,
    "human_identity_max_bytes": 16384,
    "human_identity_min_bytes": 1,
    "nesting_depth_max": 16,
    "png_max_bytes": 67108864,
    "png_min_bytes": 1,
    "retained_record_max_bytes": 262144,
    "retained_record_min_bytes": 1,
    "roles_per_binding": 1
  },
  "reviewer_rule": {
    "role_binding_checker_must_differ_from": [
      "ROLE_BINDING_MAKER",
      "QUALIFICATION_QUALIFIER",
      "MANIFEST_CHECKER",
      "PROMOTION_REQUEST_STATUS_CHECKER",
      "PROMOTION_FINAL_STATUS_CHECKER",
      "PROMOTION_CHECKER",
      "ROLE_BINDING_REQUEST_STATUS_CHECKER",
      "ROLE_BINDING_FINAL_STATUS_CHECKER"
    ],
    "role_binding_maker_future_role_auto_expansion": false,
    "role_binding_maker_no_required_separation_from": [
      "QUALIFICATION_REQUEST_PREPARER",
      "QUALIFICATION_QUALIFIER",
      "MANIFEST_MAKER",
      "MANIFEST_CHECKER",
      "PROMOTION_REQUEST_STATUS_PREPARER",
      "PROMOTION_REQUEST_STATUS_CHECKER",
      "PROMOTION_FINAL_STATUS_PREPARER",
      "PROMOTION_FINAL_STATUS_CHECKER",
      "PROMOTION_MAKER",
      "PROMOTION_CHECKER",
      "ROLE_BINDING_REQUEST_STATUS_PREPARER",
      "ROLE_BINDING_REQUEST_STATUS_CHECKER",
      "ROLE_BINDING_FINAL_STATUS_PREPARER",
      "ROLE_BINDING_FINAL_STATUS_CHECKER"
    ],
    "retained_identity_claim": "RECORD_SEPARATION_ONLY_NOT_IDENTITY_AUTHENTICATION"
  },
  "rights_scope_rule": "EXACT_SCOPE_NO_CHANGE_HUMAN_ACKNOWLEDGES_JOINT_PRESENTATION_WITHOUT_EXPANSION_NOT_ROLE_WITHIN_SCOPE_OR_RIGHTS_GRANT",
  "role_order": {
    "CHARACTER_REFERENCE_ASSET": [
      "CHARACTER_IDENTITY_SHEET",
      "CHARACTER_POSE_REFERENCE",
      "CHARACTER_EXPRESSION_REFERENCE"
    ],
    "SCENE_REFERENCE_ASSET": [
      "SCENE_ESTABLISHING_REFERENCE",
      "SCENE_LIGHTING_REFERENCE",
      "SCENE_MATERIAL_REFERENCE",
      "SCENE_PROP_PLACEMENT_REFERENCE"
    ]
  },
  "role_source_rule": "EXPLICIT_HUMAN_MAKER_SELECTION_COMPILER_VALIDATES_PURPOSE_AND_PROFILE_MEMBERSHIP_NO_PIXEL_INFERENCE",
  "sidecar_horizon_rule": "PROMOTION_EVIDENCE_VALID_UNTIL_IS_HISTORICAL_TRACEABILITY_ONLY_NOT_A_ROLE_BINDING_DEADLINE",
  "status_subject_chain_rule": "PROMOTION_FINAL_REQUEST_AND_BINDING_FINAL_RECORDS_SHARE_EXACT_CANDIDATE_QUALIFICATION_MANIFEST_SUBJECT_PURPOSE_AND_POLICY",
  "status_rule": "FRESH_JOINT_REPLAY_AT_EXACT_BINDING_AT_CURRENT_REQUIRED_ONLY_FOR_POSITIVE",
  "supersession_rule": "NO_SUPERSESSION_CURRENT_LATEST_BEST_OR_GLOBAL_UNIQUENESS_SELECTION_IN_V1",
  "time_rule": "REQUEST_RECEIPT_AS_OF_EQUALS_REQUESTED_AS_OF_EQUALS_REQUESTED_AT_EQUALS_MAKER_PREPARED_AT_AND_DECISION_AT_EQUALS_CHECKER_REVIEWED_AT_EQUALS_BINDING_AT_EQUALS_FINAL_RECEIPT_AS_OF",
  "zero_authority_rule": "ALL_PROVIDER_RUNTIME_ASSET_USE_PUBLICATION_RETENTION_TRAINING_AUTHORITY_FALSE_OR_ZERO"
}
```

The accepted exact raw SHA-256 over those compact canonical policy bytes is:

```text
fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233
```

This digest is the accepted policy anchor. It was computed over the exact 9,046 compact canonical
UTF-8 bytes of the JSON object above. Any policy-byte change would require the digest to change and
receive a separately accepted ADR revision. No BUILD may choose, repair or reinterpret the policy.

The Decision would use one strict frozen inline gate-result definition rather than a fourth
top-level model:

```text
GeneratedReferenceRoleBindingGateResultV1

ordinal: exact integer in 0..11
gate: exact ordinal-matched member of the frozen gate_order
result: PASS | FAIL | INDETERMINATE
basis: bounded human-or-compiler basis text
```

The ordinal and gate literal would have to match the policy order exactly. No optional metadata,
timestamp, reviewer value or downstream Binding identity would enter a gate result.

## Gate derivation and decision mapping

The future Decision would contain exactly 12 ordered gate results:

| Ordinal | Gate | Source |
| ---: | --- | --- |
| 0 | `EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR` | compiler-derived pass-only |
| 1 | `EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA` | compiler-derived pass-only |
| 2 | `POSITIVE_UNEXPIRED_QUALIFICATION` | compiler-derived pass-only |
| 3 | `VALID_GENERATED_RIGHTS_MANIFEST` | compiler-derived pass-only |
| 4 | `CURRENT_STATUS_AT_ROLE_BINDING` | final fresh replay |
| 5 | `SUBJECT_PURPOSE_AND_PRIMARY_BINDING_EXACT` | final supplied Bible/AssetVersion comparison |
| 6 | `ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP_EXACT` | compiler-derived pass-only |
| 7 | `REVIEWED_RIGHTS_SCOPE_UNCHANGED` | compiler-derived pass-only |
| 8 | `HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED` | Checker action |
| 9 | `HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED` | Checker action |
| 10 | `HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED` | Checker action |
| 11 | `ROLE_BINDING_REVIEWER_SEPARATION` | compiler-derived pass-only |

Compiler-derived pass-only failure would be structural and would return no formal result, except:

- `CURRENT` maps to `PASS`; `EXPIRED`, `REVOKED` and `HELD` map to `FAIL`;
  `INDETERMINATE` maps to `INDETERMINATE`;
- an exactly reconstructed but different final active primary binding maps to `FAIL`; and
- each bounded human result may be `PASS`, `FAIL` or `INDETERMINATE`.

The exact issue-code order would be:

```text
STATUS_NOT_CURRENT_AT_ROLE_BINDING
PRIMARY_BINDING_NO_LONGER_ACTIVE
EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTATION_NOT_ACKNOWLEDGED
WHOLE_COMPOSITE_ROLE_SUITABILITY_NOT_APPROVED
NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_NOT_ACKNOWLEDGED
```

Issue codes would appear in that order exactly for every `FAIL` gate with a mapping. An all-`PASS`
tuple, no issue code, final `CURRENT` and exact time/validity closure would map only to
`APPROVE_ELIGIBLE_ASSET_ROLE_BINDING`. Any valid `FAIL` would map to
`REJECT_ELIGIBLE_ASSET_ROLE_BINDING`. With no `FAIL` and at least one `INDETERMINATE`, the result
would be `INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING`.

A negative or indeterminate finalization would return the Decision only. A positive finalization
would return the Decision and Binding together. If either positive value could not be built and
fully revalidated, the call would return neither.

## Future Role-Binding Request Contract

Only under a separately authorized future BUILD, the first top-level Contract would be:

```text
CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1
```

It would be strict, frozen and extra-forbid. Every field would be required with no default
insertion. Its persistent document would contain exactly:

```text
schema_version=1.0.0
document_type=sdc.creative-sample-generated-reference-eligible-asset-role-binding-request-v1
request_scope=GENERATED_REFERENCE_ELIGIBLE_ASSET_SINGLE_ROLE_BINDING_ONLY
request_id: PortableId
request_sha256: LowerSha256
policy_id=sdc.generated-reference-eligible-asset-role-binding-policy
policy_version=1.0.0
policy_document_sha256=fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233
role_binding_review_payload_sha256: LowerSha256
requested_role_binding_target: GeneratedReferenceEligibleAssetRoleBindingTargetV1

promotion_request_id: PortableId
promotion_request_sha256: LowerSha256
promotion_decision_id: PortableId
promotion_decision_sha256: LowerSha256
eligible_asset_sidecar_id: PortableId
eligible_asset_sidecar_sha256: LowerSha256
promotion_at: UTC seconds
promotion_evidence_valid_until: UTC seconds

qualification_request_id: PortableId
qualification_request_sha256: LowerSha256
qualification_decision_id: PortableId
qualification_decision_sha256: LowerSha256
qualification_valid_until: UTC seconds
manifest_id: PortableId
manifest_sha256: LowerSha256
manifest_valid_until: UTC seconds
reviewed_rights_scope: exact GeneratedReferenceReviewedRightsScopeV1
requested_primary_asset_binding: exact GeneratedReferencePromotionPrimaryAssetBindingV1

status_subject_closure_id: PortableId
status_subject_closure_sha256: LowerSha256
requested_status_record_id: PortableId
requested_status_record_sha256: LowerSha256
requested_status_receipt_id: PortableId
requested_status_receipt_sha256: LowerSha256
requested_explicit_chain_set_sha256: LowerSha256
requested_coverage_set_sha256: LowerSha256
requested_joint_replay_sha256: LowerSha256
requested_as_of_assessment_sha256: LowerSha256
requested_as_of: UTC seconds
requested_as_of_status=CURRENT
requested_status_valid_until: UTC seconds

maker_identity_ref_sha256: raw LowerSha256
maker_action_sha256: raw LowerSha256
maker_prepared_at: UTC seconds
requested_at: UTC seconds
request_valid_until: UTC seconds
request_basis: bounded human text

media_binding_scope=WHOLE_UNSPLIT_UNTRANSFORMED_COMPOSITE_PNG_OCCURRENCE
explicit_human_role_selection=true
profile_role_membership_verified=true
role_binding_exclusivity_asserted=false
complete_role_set_asserted=false
global_role_uniqueness_asserted=false
crop_requested=false
split_requested=false
transform_requested=false
derived_media_requested=false
provider_input_requested=false
role_binding_performed=false
binding_materialized=false
provider_input_eligible=false
status=GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_REQUESTED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

The Request semantic projection would contain the same fields except `request_id` and
`request_sha256`. Its short ID would derive from the first 20 lower-hex characters of the full
semantic SHA-256.

## Future Role-Binding Decision Contract

The second top-level Contract would be:

```text
CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1
```

It would contain exactly:

```text
schema_version=1.0.0
document_type=sdc.creative-sample-generated-reference-eligible-asset-role-binding-decision-v1
decision_scope=GENERATED_REFERENCE_ELIGIBLE_ASSET_SINGLE_ROLE_BINDING_ONLY
decision_id: PortableId
decision_sha256: LowerSha256
policy_id=sdc.generated-reference-eligible-asset-role-binding-policy
policy_version=1.0.0
policy_document_sha256=fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233
role_binding_review_payload_sha256: LowerSha256
request_id: PortableId
request_sha256: LowerSha256
requested_role_binding_target: GeneratedReferenceEligibleAssetRoleBindingTargetV1

promotion_request_id: PortableId
promotion_request_sha256: LowerSha256
promotion_decision_id: PortableId
promotion_decision_sha256: LowerSha256
eligible_asset_sidecar_id: PortableId
eligible_asset_sidecar_sha256: LowerSha256
promotion_at: UTC seconds
promotion_evidence_valid_until: UTC seconds

qualification_decision_id: PortableId
qualification_decision_sha256: LowerSha256
qualification_valid_until: UTC seconds
manifest_id: PortableId
manifest_sha256: LowerSha256
manifest_valid_until: UTC seconds
reviewed_rights_scope: exact GeneratedReferenceReviewedRightsScopeV1
requested_primary_asset_binding: exact GeneratedReferencePromotionPrimaryAssetBindingV1
binding_primary_asset_binding: exact GeneratedReferencePromotionPrimaryAssetBindingV1

status_subject_closure_id: PortableId
status_subject_closure_sha256: LowerSha256
binding_status_record_id: PortableId
binding_status_record_sha256: LowerSha256
binding_status_receipt_id: PortableId
binding_status_receipt_sha256: LowerSha256
binding_explicit_chain_set_sha256: LowerSha256
binding_coverage_set_sha256: LowerSha256
binding_joint_replay_sha256: LowerSha256
binding_as_of_assessment_sha256: LowerSha256
binding_as_of_status: CURRENT | EXPIRED | REVOKED | HELD | INDETERMINATE
binding_status_valid_until: UTC seconds

checker_identity_ref_sha256: raw LowerSha256
checker_action_sha256: raw LowerSha256
checker_reviewed_at: UTC seconds
decision_at: UTC seconds
binding_at: UTC seconds
gate_results: exact ordered tuple of 12 GeneratedReferenceRoleBindingGateResultV1 values
binding_issue_codes: exact ordered tuple with 0..5 items
decision_basis: bounded human text
decision:
  APPROVE_ELIGIBLE_ASSET_ROLE_BINDING
  | REJECT_ELIGIBLE_ASSET_ROLE_BINDING
  | INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING
binding_materialization_allowed: exact boolean derived from decision
role_binding_review_performed=true
binding_id_embedded=false

role_binding_exclusivity_asserted=false
complete_role_set_asserted=false
global_role_uniqueness_asserted=false
crop_applied=false
split_applied=false
transform_applied=false
derived_media_created=false
provider_input_eligible=false
status=GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_DECISION_RECORDED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

The Decision semantic projection would exclude only `decision_id` and `decision_sha256`. A positive
Decision would permit only same-call pure construction of the exact historical Binding below; it
would grant no Rights, currentness, Provider input or execution.

## Future positive Eligible-Asset Role Binding Contract

The third top-level Contract would be:

```text
CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1
```

It would exist only for a positive Decision and would contain exactly:

```text
schema_version=1.0.0
document_type=sdc.creative-sample-generated-reference-eligible-asset-role-binding-v1
binding_scope=POST_PROMOTION_SINGLE_ROLE_BINDING_HISTORICAL_EVIDENCE_ONLY
binding_id: PortableId
binding_sha256: LowerSha256
policy_id=sdc.generated-reference-eligible-asset-role-binding-policy
policy_version=1.0.0
policy_document_sha256=fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233
request_id: PortableId
request_sha256: LowerSha256
decision_id: PortableId
decision_sha256: LowerSha256
role_binding_target: GeneratedReferenceEligibleAssetRoleBindingTargetV1

promotion_request_id: PortableId
promotion_request_sha256: LowerSha256
promotion_decision_id: PortableId
promotion_decision_sha256: LowerSha256
eligible_asset_sidecar_id: PortableId
eligible_asset_sidecar_sha256: LowerSha256
promotion_at: UTC seconds
promotion_evidence_valid_until: UTC seconds

qualification_decision_id: PortableId
qualification_decision_sha256: LowerSha256
qualification_valid_until: UTC seconds
manifest_id: PortableId
manifest_sha256: LowerSha256
manifest_valid_until: UTC seconds
reviewed_rights_scope: exact GeneratedReferenceReviewedRightsScopeV1
primary_asset_binding: exact GeneratedReferencePromotionPrimaryAssetBindingV1

status_subject_closure_id: PortableId
status_subject_closure_sha256: LowerSha256
binding_status_record_id: PortableId
binding_status_record_sha256: LowerSha256
binding_status_receipt_id: PortableId
binding_status_receipt_sha256: LowerSha256
binding_explicit_chain_set_sha256: LowerSha256
binding_coverage_set_sha256: LowerSha256
binding_joint_replay_sha256: LowerSha256
binding_as_of_assessment_sha256: LowerSha256
binding_as_of_status=CURRENT
binding_at: UTC seconds
binding_status_valid_until: UTC seconds
binding_evidence_valid_until: UTC seconds

binding_state=GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_RECORDED
role_binding_performed=true
provider_input_eligible=false
present_currentness_asserted=false
perpetual_role_suitability_asserted=false
role_binding_exclusivity_asserted=false
complete_role_set_asserted=false
global_role_uniqueness_asserted=false
current_role_binding_asserted=false
supersedes_role_binding=false
primary_asset_binding_replaced=false
bible_active_binding_changed=false
asset_version_v1_created=false
whole_composite_media_bound=true
crop_applied=false
split_applied=false
transform_applied=false
derived_media_created=false
provider_slot_embedded=false
status=GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_RECORDED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete zero-authority surface
```

`binding_evidence_valid_until` would be the exact minimum of the Qualification, Manifest and final
fresh-status exclusive upper bounds. The copied Sidecar `promotion_evidence_valid_until` would not
participate. The new value would describe only the historical evidence window at construction. The
Binding would still set
`present_currentness_asserted=false`.

The Binding would carry no positive Provider-input review-routing field. Any later proposal would
have to define its own entry condition, explicitly supplied finite set rules and fresh replay; this
ADR neither names nor authorizes that route.

## Exact cross-document linkage matrix

Every constructor and verifier would receive the complete predecessor values, revalidate their
exact released types and identities, and enforce this closed equality matrix. An ID or digest alone
could not satisfy a row.

| Destination | Exact required linkage |
| --- | --- |
| Request from review payload | Every review-payload field is reproduced exactly; the target, Policy identity, Promotion/Sidecar anchors, Qualification/Manifest anchors and deadlines, Rights scope, requested primary binding, Request-time status anchors/times, role/boundary literals and zero-authority surface are field-for-field equal. The Request adds only its identity, admitted Maker identity/action anchors, bounded basis and Request state. |
| Request from Maker records | `maker_identity_ref_sha256` equals the raw digest of the exact admitted three-field Maker identity record. `maker_action_sha256` equals the raw digest of the exact admitted Maker action, whose actor-ref digest, Policy identity, review-payload SHA, target SHA, selected role, requested primary-binding SHA, requested status-Receipt SHA, `prepared_at` and `request_basis` equal the corresponding identity, payload and Request fields exactly. `maker_prepared_at == action.prepared_at == requested_at`; the Request `request_basis` equals the action basis exactly. |
| Request from Promotion-final status closure | The supplied Promotion Decision/Sidecar and complete Promotion-final Record are fully revalidated. Promotion-final and Request-time status closures have the same exact Candidate, Qualification Decision, Manifest, subject, asset purpose and current-status policy. Every Promotion-final target anchor and branch is covered by the Request-time Record under the frozen same-target-or-complete-successor/reconciliation rule; omission, substitution, rewrite or favorable-subset replay is structural failure. |
| Decision from Request | `request_id` and `request_sha256` revalidate the complete supplied Request. Policy identity, review-payload SHA, target, Promotion Request/Decision/Sidecar IDs and SHAs, `promotion_at`, historical `promotion_evidence_valid_until`, Qualification Decision identity/deadline, Manifest identity/deadline, exact reviewed Rights scope and requested primary binding equal the Request fields exactly. Request-time status and Maker fields remain closed by the revalidated Request rather than being independently restated. |
| Decision final evidence | The final status-subject closure identity must equal the Request subject closure. Every final Record/Receipt/chain/coverage/joint-replay/assessment field must equal the exact recomputed final replay. Receipt `as_of`, `binding_at`, `checker_reviewed_at` and `decision_at` are equal. `binding_primary_asset_binding` is rebuilt from the final supplied Bible/AssetVersion; exact equality with the requested/Sidecar binding yields `PASS`, while one valid same-subject/purpose active-binding difference yields the frozen negative gate. |
| Decision from Checker action | Checker identity/action SHAs close the exact admitted records. Target, selected role, Request, final status Receipt, final primary binding, three human results/bases, complete gate tuple, issue tuple, `decision_basis`, decision literal and materialization boolean equal the Checker action exactly. Compiler-derived gates and the issue/decision mapping must also independently recompute to those same values. |
| Positive Binding from Decision | Policy identity, Request identity, positive Decision identity, target, every Promotion/Sidecar anchor/time, Qualification Decision anchor/deadline, Manifest anchor/deadline, exact Rights scope, final primary binding, complete final status anchors/result/time, `binding_at`, all non-exclusive/no-derived-media literals and the complete zero-authority surface equal the positive Decision and its revalidated Request exactly. `binding_evidence_valid_until` alone is newly derived as the exact minimum specified above. |

The positive Decision must have all 12 gates `PASS`, an empty issue tuple,
`decision=APPROVE_ELIGIBLE_ASSET_ROLE_BINDING` and
`binding_materialization_allowed=true`. The Binding and Decision would be returned only as one
fully revalidated pair. Any omitted predecessor, copied-field mismatch, recomputation mismatch or
attempt to pair a Binding with another Request or Decision would be structural failure with no
positive output.

## Complete zero-authority surface

Every future top-level Contract would directly carry this required literal surface:

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

These would be required projection fields, not omitted defaults. Role-Binding-specific positive
historical flags could not override or weaken them.

## Provider, Runtime, Compiler and persistence isolation

A conforming future role-binding module must not import, call or modify:

- `GenerationJob`, `JobGraph`, `InputMaterial`, `ProviderRequest` or Provider profiles;
- Runtime, Worker, Temporal, PostgreSQL, persistence rows, migrations or events;
- Provider selection, submit, inspect, download, cancel or Retry;
- network, credentials, environment configuration, capability discovery, cost reservation or paid
  service;
- current compiler entrypoints, Storyboard, NIR, PIR, Compilation or AssemblyPlan;
- any AssetVersion or Bible mutation path;
- QC automation, publication, posting or release;
- retention/deletion automation or training controls; or
- filesystem discovery, current/latest lookup, migration or backfill.

Current Compiler, Provider, Runtime, Worker, QC and persistence modules must not import the future
role-binding module. The downstream module could exact-type revalidate explicitly supplied upstream
values and call their released pure verification helpers only.

The new Binding could not validate as, convert to or be duck-typed as current `InputMaterial`, whose
existing fields do not close role, Rights, currentness or authority. Provider syntax-compatibility
metadata, Profile recipe data and QC expectations would grant no role or Provider authority.

## Canonical projections, IDs and digest domains

Persistent formal documents would use UTF-8 without BOM, NFC keys and strings, recursively sorted
object keys, two-space indentation, `ensure_ascii=false`, `allow_nan=false`, LF-only line endings
and exactly one terminal LF. Semantic projections would use the same validated values with
recursively sorted keys, compact separators, `ensure_ascii=false`, `allow_nan=false`, no CR and no
terminal LF. Arrays would preserve their defined semantic order. No locale, path or platform
normalization would enter identity.

Raw SHA-256 would remain undomained only for exact external byte records such as PNG and retained
human/evidence JSON. Every semantic projection would use a unique NUL-terminated domain:

```text
sdc:generated-reference-eligible-asset-role-binding-target:v1\0
sdc:generated-reference-eligible-asset-role-binding-review-payload:v1\0
sdc:generated-reference-eligible-asset-role-binding-request:v1\0
sdc:generated-reference-eligible-asset-role-binding-decision:v1\0
sdc:generated-reference-eligible-asset-role-binding:v1\0
```

The exact ID stems would be:

```text
generated_reference_eligible_asset_role_binding_request_v1_
generated_reference_eligible_asset_role_binding_decision_v1_
generated_reference_eligible_asset_role_binding_v1_
```

Each portable ID suffix would be the first 20 characters of the corresponding full lower-hex
semantic SHA-256. Target and review-payload projections would be digest-only inline values with no
portable ID.

Every field mutation, self-field exclusion, full-hash/short-ID agreement and cross-domain
non-aliasing would require direct tests before a future BUILD could be accepted.

## Resource and privacy boundary

The accepted inclusive limits are:

| Resource | Limit |
| --- | ---: |
| Formal persistent JSON document | `1..262144` bytes |
| Retained canonical JSON record | `1..262144` bytes |
| Human identity JSON | `1..16384` bytes |
| Local PNG | `1..67108864` bytes |
| Human basis | `1..1000` Unicode code points |
| Generic container | at most 64 items |
| Generic JSON nesting depth | at most 16 |
| Roles per target/Request/Decision/Binding | exactly 1 |

Portable formal documents would contain only bounded privacy-minimized references and digests.
They would prohibit raw external or Provider task/request IDs, signed URLs, credentials, account
identifiers, contact data, biometric data, filesystem paths, HTTP bodies and unbounded error text.
The bounded portable IDs explicitly defined by these Contracts are not external request IDs.

The source and generated known-answer fixtures would contain only first-party fictional synthetic
subjects, synthetic PNGs and synthetic human-reference records. No real person, place, brand,
third-party character, protected work, Provider response, credential or sensitive data would be
admitted.

## Failure behavior and priority

A future module would use exactly these stable Role-Binding umbrella codes in this exact
first-failure priority order:

```text
INPUT_RESOURCE_LIMIT_EXCEEDED
INPUT_DOCUMENT_INVALID
CONTRACT_FIELD_INVALID
POLICY_IDENTITY_MISMATCH
FORMAL_IDENTITY_MISMATCH
UPSTREAM_CLOSURE_MISMATCH
PROMOTION_CLOSURE_INVALID
PNG_ADMISSION_INVALID
ROLE_PURPOSE_OR_MEMBERSHIP_INVALID
PRIMARY_ASSET_BINDING_CLOSURE_INVALID
CURRENT_STATUS_REPLAY_INVALID
RIGHTS_SCOPE_MISMATCH
ROLE_SEPARATION_VIOLATION
ACTION_RECORD_INVALID
TIME_OR_VALIDITY_INVALID
AUTHORITY_SURFACE_NONZERO
PROHIBITED_BOUNDARY_CONNECTION
BINDING_GATE_NOT_PASS
ATOMIC_OUTPUT_INVARIANT_VIOLATION
```

Request preparation and Decision finalization would evaluate applicable stages only in that order;
Request preparation would skip finalization-only gate/pair stages rather than reorder them. Within
an upstream-closure stage, exact released ADR-042/043/044/045 nested errors would remain visible
before the next Role-Binding umbrella code, matching the existing upstream precedence. No wrapper
would parse exception text or replace an earlier specific nested code with a later generic code.

`BINDING_GATE_NOT_PASS` would apply only if a caller attempted to construct or verify a Binding
from a non-positive Decision. Normal valid `FAIL` or `INDETERMINATE` finalization would return only
the corresponding Decision and no error. `ATOMIC_OUTPUT_INVARIANT_VIOLATION` would apply only after
all earlier stages passed and the positive pair could not be constructed and revalidated together.

A malformed input, policy drift, digest mismatch, cross-purpose role, action alias, incomplete
replay, forged primary binding or prohibited field would return no formal output.

No operation could coerce, repair, select another role, refresh a deadline, discover a replacement,
retry a Provider operation or create a partial positive output.

## Contract and Schema Registry impact

This Accepted ADR changes no current Contract or Schema.

If a separate BUILD were later authorized and implemented, it would append exactly:

```text
MODELS[86] = CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1
MODELS[87] = CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1
MODELS[88] = CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1
```

The Registry would then contain exactly 89 models and committed Schema files. The inline target and
gate result definitions would remain nested and would not add top-level Schema files.

No existing model could be reordered. `MODELS[:86]`, all 86 current committed Schema Git blobs and
all 18 current tracked visual-prompt fixture bytes would remain exact. Historical 83-Schema and
16-fixture byte assertions would also remain intact rather than being replaced by the new prefix
assertions.

## Validation and future implementation gates

A future BUILD could proceed only under separate explicit authorization. It would have to:

1. begin from a newly verified authoritative clean `main` in an isolated `codex/` branch;
2. record Git-blob path, size and SHA-256 baselines for all 86 current Schemas and all 18 current
   visual-prompt fixtures before generation;
3. prove `MODELS[:86]`, every existing committed Schema byte and every existing fixture byte
   unchanged at the final reviewed commit;
4. append only the exact three approved top-level models in the exact approved order;
5. keep the target and gate-result definitions inline;
6. implement explicit projection functions and every unique NUL-terminated domain;
7. test every-field mutation, self-field exclusion, full-hash/short-ID agreement and cross-domain
   non-aliasing;
8. test exact full revalidation of ADR-042/043/044/045 values and raw PNG bytes;
9. test Request-time and `binding_at` fresh replay, exact
   `Receipt.as_of == requested_as_of == requested_at == maker_prepared_at`, prior-target
   monotonicity across both Promotion-final-to-Request and Request-to-final transitions,
   Promotion-target omission, favorable-subset and omitted/replaced-branch attacks, exact
   Status-Subject equality across all three Records and every half-open upper-bound equality; also
   test before/equal/after the historical Sidecar horizon while Qualification, Manifest and newly
   replayed status remain unexpired, proving that the old horizon is copied but is not a deadline;
10. test the exact seven role literals, purpose partition, canonical tuple order, subset/reorder,
    unknown-role and cross-purpose attacks;
11. test that Profile/Prompt/QC/file-name/layout data cannot create or change a role;
12. test exact whole-PNG review and reject crop, split, transform, resize, transcode and derived-byte
    injection;
13. test equal PNG bytes from distinct Candidate/Attempt occurrences and require distinct closure;
14. test the non-exclusive policy, repeated Sidecar/role reviews and all false uniqueness/completeness
    fields without introducing set semantics;
15. test exact Rights-scope equality and reject expansion, narrowing, reorder, renewal or extension;
16. test Request-time/final primary-binding equality, active-binding drift, forged bindings and
    Character/Scene crossing;
17. test the complete identity-separation matrix by semantic tuple, not hash inequality;
18. test Checker-action equality with the complete gate/issue/decision/materialization tuple, every
    Request-to-Decision-to-Binding linkage row, positive Decision+Binding atomicity,
    negative/indeterminate Decision-only behavior and injected Binding-construction failure;
19. test every zero-authority field and reject positive Provider-review routing, Provider slot,
    InputMaterial, ProviderRequest, executable route, Runtime, credential, cost, Retry, publication,
    retention and training injection;
20. prove current Compiler, Provider, Runtime, Worker, QC and persistence modules do not import the
    new module;
21. prohibit wall-clock lookup, filesystem discovery, environment selection, randomness, network or
    database state in identity;
22. use only first-party synthetic Prompt, PNG, evidence and human-reference data;
23. create a complete human known-answer review packet before Draft-to-Ready;
24. run full repository validation in a frozen or isolated worktree; and
25. compare the final Schema and fixture Git blobs with the start baseline before merge review.

Passing those gates would prove only deterministic implementation conformance over supplied bytes.
It would not prove pixel truth beyond the bounded human decision, identity authentication, legal
Rights, present currentness, Provider eligibility, execution authority or commercial use.

## Future codegen and known-answer boundary

If separately authorized, the new codegen CLI would require exactly one of `--check` or `--update`.
`--check` would be completely read-only. `--update` would write only one fixed derived fixture path
after the source fixture received separate human review and a fixed byte-size/SHA anchor. It would
never alter Schemas, ADRs, source fixtures, PNGs or old fixtures.

The future fixture paths would be exactly:

```text
tests/fixtures/visual_prompt_profiles/generated-reference-role-binding/
  reviewed-known-answer-source-v1.json
  generated-known-answer-v1.json
```

The new codegen would freeze the complete 18-path pre-BUILD fixture map. Adding the two exact new
paths would take the tracked visual-prompt fixture count from 18 to 20. That count would not
authorize discovery, regeneration or alteration of an old fixture.

The source fixture would contain at least one first-party fictional Character case and one
first-party fictional Scene case. The derived known answer would cover positive, rejected and
indeterminate Decisions; exact Request/Decision/Binding bytes; every role/purpose mapping; the
non-exclusive policy; both fresh replays; identity separation; primary-binding drift; Rights-scope
attacks; equal bytes/different Candidate occurrences; and prohibited crop/split/Provider fields.

Synthetic positive Bindings would be technical known answers only. They would not represent a real
role assignment, Provider-input qualification, current legal entitlement or actual asset use.

## Exact future BUILD changed-file allowlist

If a separate BUILD were later authorized without an intervening ADR revision, its closed
changed-file allowlist would be exactly:

```text
.github/workflows/ci.yml
Makefile
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1.schema.json
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1.schema.json
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1.schema.json
src/sdc/generated_reference_role_binding.py
src/sdc/generated_reference_role_binding_codegen.py
src/sdc/schemas.py
tests/test_generated_reference_role_binding.py
tests/test_generated_reference_role_binding_codegen.py
tests/test_generated_reference_candidate.py
tests/test_generated_reference_rights_current_status_codegen.py
tests/test_real_asset_fresh_status_chain_replay_v30.py
tests/test_real_asset_fresh_status_record_as_of_assessment_receipt_codec_v30.py
tests/test_real_asset_fresh_status_record_as_of_assessment_receipt_v30.py
tests/test_real_asset_fresh_status_record_as_of_assessment_v30.py
tests/test_real_asset_fresh_status_record_chain_coverage_v30.py
tests/test_real_asset_fresh_status_record_joint_replay_v30.py
tests/test_schemas.py
tests/test_visual_prompt_compiler_integration.py
tests/test_visual_prompt_profile_codegen.py
tests/test_visual_reference_prompt_compiler.py
tests/fixtures/visual_prompt_profiles/generated-reference-role-binding/reviewed-known-answer-source-v1.json
tests/fixtures/visual_prompt_profiles/generated-reference-role-binding/generated-known-answer-v1.json
```

The exact allowlist contains 24 unique repository-relative paths. Workflow and Makefile changes
would be limited to the new read-only codegen check and its Windows validation job. Registry and
historical Schema-test changes would be limited to the exact append from 86 to 89 while retaining
all historical prefix and byte assertions. Existing live Registry-cardinality assertions could
change only from 86 to 89. Historical reverse-import allowlists could add only the two new isolated
role-binding modules. The ADR-044 historical fixture-set test could exclude only the new fixed
role-binding fixture directory while retaining its own frozen historical count.

The ADR file is deliberately absent from the future BUILD allowlist. Any need to change this ADR,
another path or another semantic assertion would stop the BUILD and require a separately reviewed
ADR revision or architecture decision before work resumed.

## Rejected alternatives

This Accepted decision rejects:

- modifying or adding a role field to the ADR-045 Eligible-Asset Sidecar;
- mutating an old Promotion Decision or Binding after review;
- treating the Profile's complete role tuple as proof of pixel content;
- machine, agent, filename, layout or QC inference of the selected role;
- one implicit multi-role Binding over a composite PNG;
- a BindingSet, full three-role/four-role pack or Provider ordering in V1;
- an exclusivity or global uniqueness claim from a stateless atomic document;
- treating one Sidecar as absent from all other role Bindings;
- crop, split, mask, panel extraction, transformation or derived-media creation;
- assigning derived bytes without a new provenance/Candidate/Promotion lifecycle;
- reusing or expanding current AssetVersion, Bible, `CharacterAssetBinding` or `InputMaterial`;
- adding a Provider slot, route, model, request, idempotency key or execution field;
- accepting a Sidecar, Receipt, ID, digest or copied `CURRENT` string without full replay;
- changing, narrowing, widening, reordering, renewing or interpreting Rights scope by code;
- selecting latest, best or current Binding from storage or filesystem order;
- superseding, deleting, refreshing or mutating an old Binding in V1;
- deduplicating equal media bytes across distinct Candidate/Attempt occurrences;
- using wall clock, environment, random values, database state or network data in identity;
- importing the role-binding module from current Compiler, Provider, Runtime, Worker, QC or
  persistence paths; and
- treating a synthetic known answer as real role, Rights, Provider or execution authority.

## Risks and treatment

| Severity | Risk | Required treatment |
| --- | --- | --- |
| Blocking | One stateless Binding is misread as globally exclusive | Carry exact false exclusivity/completeness/currentness fields and define the atomic association as non-exclusive |
| Blocking | Profile/Prompt/QC semantics are treated as pixel-role proof | Use them only for purpose/member validation; require independent human review of exact admitted PNG bytes |
| Blocking | Crop or split bypasses Candidate occurrence identity | Admit only the original whole PNG; any derived bytes require a new full lifecycle |
| Blocking | A historical Sidecar or Receipt is treated as current | Require complete Request-time and `binding_at` replay; reject Receipt/ID/digest-only substitution |
| Blocking | Rights scope is widened or role review is treated as a Rights grant | Copy exact scope unchanged, use a separate human acknowledgement and retain `grants_rights=false` |
| Blocking | Primary Bible binding silently changes | Rebuild it twice; a valid final drift creates no positive Binding |
| Blocking | One reviewer controls Qualification, Rights, Promotion, status and role assignment | Enforce the exact Checker separation matrix by semantic identity tuple |
| Blocking | A Binding is accepted as Provider input or execution authority | Keep `provider_input_eligible=false`, complete zero authority and no Provider/InputMaterial fields |
| Blocking | Positive Decision or Binding exists without the other | Construct and fully revalidate the positive pair atomically; return neither on failure |
| Important | Equal PNG bytes from another Candidate inherit the Binding | Bind exact Outcome/Candidate/Sidecar occurrence in the target and every outer projection |
| Important | Multiple historical Bindings are treated as latest or complete | Define no resolver, supersession, completeness or global uniqueness in V1 |
| Important | Raw hashes and semantic domains alias | Keep raw SHA undomained and use unique NUL-terminated domains with cross-domain tests |
| Important | Portable documents leak private or Provider data | Admit bounded privacy-minimized refs/digests and prohibit paths, URLs, credentials and raw Provider IDs |
| Important | Character and Scene roles cross or tuple order drifts | Freeze exact purpose mapping, complete tuples and canonical order |
| Important | New Schemas or fixtures drift released products | Freeze all 86 Schema and 18 fixture Git blobs; append exactly three Schemas and two fixtures only after authorization |
| Minor | Eligible, promoted, role-bound, current and Provider-input terminology is confused | Keep exact literals and put display labels outside semantic projections |
| Minor | UI, visualization, localization, CLI and persistence are absent | Defer presentation and storage until after the semantic boundary is accepted and implemented |
| Minor | Non-exclusive atomic Bindings require later supplied-set work | State the limitation; do not predesign the later set or Provider boundary here |

## Non-goals

This Accepted ADR does not approve or specify:

- implementation through this acceptance alone;
- any current Contract, Schema, Registry, fixture, test, source, codegen, CI or Makefile change;
- creation of a real Role-Binding Request, Decision or Binding;
- mutation of an Artifact, Outcome, Candidate, Qualification, Manifest, status value, Promotion value,
  AssetVersion or Bible;
- a generated AssetVersion or Bible V2;
- changing any current Compiler, Storyboard, NIR, PIR, Job or Compilation identity;
- role-specific cropping, splitting, transformation or derived media;
- a multi-role BindingSet, pack, role completeness or exclusivity claim;
- Provider Input Material V2, Provider slots, ordering, duplicate policy or idempotency;
- Provider selection, submission, inspection, download, cancellation or Retry;
- Runtime, Worker, Temporal, PostgreSQL, storage, migration or event integration;
- network, credentials, remote processing, paid service or cost reservation;
- real Rights review, legal sufficiency, ownership, licensing or commercial-use determination;
- reviewer, source or organizational identity authentication;
- QC automation, publication, posting or release;
- retention/deletion automation or training controls;
- current/latest/best discovery, automatic renewal, migration, backfill or mutation;
- supersession or deletion of an existing Binding;
- a trusted-local filesystem finalizer; or
- external Prompt, image, brand, real-person, third-party character, protected-work or sensitive-data
  fixtures.

## Permitted claims and explicit non-proofs

At this Accepted documentation state, SDC may claim only that the exact architecture boundary and
policy bytes recorded here received human acceptance. It may not claim that any Contract, Schema,
implementation or actual Role-Binding output exists.

Only after separate BUILD authorization, implementation, first-party synthetic known-answer review
and merge could SDC claim that:

- one exact Request closed one exact positive Eligible-Asset Sidecar occurrence, whole PNG,
  purpose-compatible role, Rights, current-status and primary-binding packet;
- one independent Role-Binding Checker recorded one deterministic Decision after fresh replay at
  exact `binding_at`;
- one positive Decision produced one immutable non-exclusive historical Binding without changing
  the Sidecar, primary AssetVersion or Compiler output; and
- all new values remained offline and granted zero Provider, Runtime, asset-use, publication,
  retention, training or execution authority.

Even then, SDC could not claim that:

- a Profile role, Prompt constraint or QC expectation proved pixel content;
- the PNG contains a separable panel, crop or role-specific derived image;
- the role is exclusive, globally unique, latest, best, current or part of a complete role set;
- the Binding remains current after `binding_at`;
- absence of supplied adverse evidence proves no adverse evidence exists;
- a retained identity reference authenticates a person, competence or authority;
- the reviewed Rights scope proves ownership, license, commercial use or legal sufficiency;
- the generated bytes became an AssetVersion or active Bible binding;
- the Binding is Provider-input eligible, executable or suitable for any actual Provider;
- Provider capability, entitlement, availability, route or cost exists;
- Runtime, Retry, network, credentials, payment, publication, retention or training is permitted; or
- equal bytes from another Candidate occurrence inherit the Binding.

## Consequences

Positive consequences if separately authorized and implemented would include:

- generated media could gain one truthful, occurrence-specific role association without corrupting
  imported-media provenance;
- Profile membership and human pixel-role review would remain visibly separate;
- every positive role association would be tied to exact whole bytes and fresh status;
- Rights scope and primary binding could not be silently changed;
- the final Role-Binding Checker would be independent of the upstream decision chain;
- the Sidecar and all earlier values would remain immutable;
- one-way deterministic identities and positive pair atomicity would remain testable;
- non-exclusive semantics would avoid a false global uniqueness claim; and
- Provider-input and execution would remain visibly separate future decisions.

Costs and limitations would include:

- Request and Decision would each require complete fresh replay and exact PNG re-admission;
- the final Checker would need to be independent of eight supplied role identities;
- one whole composite image would remain unsplit;
- an atomic Binding would not prove role-set completeness or exclusivity;
- repeated reviews could create multiple historical Bindings with no built-in resolver;
- three new top-level Schemas and extensive synthetic known-answer/negative tests would be required;
- every later consumer would still need its own fresh replay; and
- no current Provider or Runtime path could consume the result.

## Accepted R1 task boundary

This ADR-only Accepted R1 formalization may modify only:

```text
docs/adr/SDC-ADR-046.md
```

It must not:

- change any accepted architecture choice, policy JSON byte or digest, Contract design, the current
  86-Schema/18-fixture compatibility boundary, future Registry/fixture target, exact 24-path future
  BUILD allowlist or zero-authority claim while recording this acceptance;
- modify ADR-039 through ADR-045 or any current Contract, Schema, Registry, fixture, test, source,
  codegen, CI, Makefile or README file;
- run Schema generation, code generation or fixture update;
- create an implementation commit, implementation PR or release; the only permitted commit and PR
  are this documentation-only Accepted R1;
- create a Role-Binding Request, Decision or Binding;
- inspect or assign a role to any actual asset;
- connect Compiler, Provider, Runtime, network, credentials, cost, Retry or persistence; or
- begin Provider-input, publication, retention or training work.
