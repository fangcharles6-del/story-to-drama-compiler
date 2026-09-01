# SDC-ADR-047: Generated Reference Bounded Supplied Role-Binding Set Boundary

- Status: Accepted R2
- Date: 2026-09-01
- Acceptance date: 2026-09-01
- Prior revision: Accepted R1 on 2026-08-31
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
- Atomic Role-Binding dependency: SDC-ADR-046 / Generated Reference Eligible-Asset Role-Binding
  Boundary
- Accepted R1 drafting baseline: `0671b24b8c0c135228ed35d99df92364f517ae99`
- Accepted R2 drafting authoritative-main baseline: `7bd96010f498d537e86e2eb2268d6df34a2e4c75`
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: one explicitly supplied bounded tuple of exact positive ADR-046 Role-Binding
  occurrences under one exact common Artifact/Profile/subject/purpose/primary-binding/Rights frame;
  complete explicitly supplied predecessor and fresh-status closures, exact local whole PNG bytes
  and privacy-minimized retained Set review records; first-party synthetic review data only
- Network/spend boundary: zero network calls, zero credential reads, zero Provider requests, zero
  authorized Attempts and zero authorized cost

## Accepted R2 revision record and BUILD stop-gate resolution

Accepted R1 remains the historical record of the bounded supplied Set architecture. During the
separately authorized first partial BUILD, two frozen R1 constraints proved unable to close together:

1. the R1 Set error tuple claimed an exceptionless global first-failure order, while each released
   ADR-046 Request/finalization verifier already selects one failure in its own frozen internal order,
   including PNG admission before later Role/Purpose, primary-binding, current-status, Rights,
   separation, action, time, authority and atomicity checks; and
2. the R1 25-path allowlist required a complete executable Set known-answer packet while permitting
   Set codegen to import only the Set core and standard library, even though the fixed upstream
   technical fixtures can be reconstructed without private cross-module access only through the two
   released upstream codegen modules.

Accepted R2 carries forward every Accepted R1 decision, Contract shape, Registry target, 89-Schema/
20-fixture compatibility anchor, future 92-Schema/22-fixture target, resource limit, identity rule and
zero-authority value except where this revision explicitly replaces R1. It makes exactly these two
semantic boundary changes:

- the closed 21-code Set tuple remains unchanged, but it is the Set-owned/direct-call-site order, not
  an instruction to reorder a failure already selected inside an ADR-046 verifier; and
- the future BUILD changed-file allowlist expands from 25 to 27 paths solely to add one typed,
  read-only fixed-fixture support API to each of the ADR-045 Promotion and ADR-046 Role-Binding
  codegen modules.

This Accepted R2 records architecture acceptance only. It does not resume the stopped partial BUILD,
authorize reuse of its outputs or authorize any Contract, Schema, Registry, fixture, source, test,
codegen, CI, Makefile, Provider-input or Runtime change.

## Context

SDC now has accepted and implemented offline boundaries for deterministic Visual Prompt Profiles,
one Character or Scene reference Prompt Artifact, one generated Candidate occurrence, human
Qualification, generated Rights/current-status evidence, append-only Eligible-Asset Sidecar
Promotion and one atomic Eligible-Asset Role Binding.

ADR-046 deliberately stops before a multi-reference BindingSet, Provider Input Material,
`InputMaterial`, `ProviderRequest` or execution. One positive
`CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1` is an immutable historical,
non-exclusive association between one exact Sidecar occurrence's unchanged whole PNG and one exact
purpose-compatible role. It directly retains:

```text
provider_input_eligible=false
present_currentness_asserted=false
role_binding_exclusivity_asserted=false
complete_role_set_asserted=false
global_role_uniqueness_asserted=false
current_role_binding_asserted=false
supersedes_role_binding=false
```

Those fields prevent one atomic Binding from proving a complete, current, exclusive or executable
set. ADR-046 therefore requires any later consumer to accept an explicitly supplied finite tuple of
exact Bindings and independently define role uniqueness, Sidecar-occurrence reuse, duplicate-byte
behavior, canonical order, partial/full semantics and fresh replay.

The current Registry contains exactly 89 top-level models. ADR-046 appended only its Request,
Decision and positive Binding at indices 86 through 88. The tracked
`tests/fixtures/visual_prompt_profiles` tree contains exactly 20 files. Every existing model name,
Registry position, committed Schema byte, fixture byte and released Compiler identity is an upstream
compatibility boundary.

The current `InputMaterial` has only `reference` and `sha256`. It has no role, Candidate occurrence,
Sidecar, Rights, fresh-status, primary-binding, selection-order or authority closure. A
`ProviderRequest` carries an ordered tuple of those values, and current Provider code may interpret
each `reference` directly as an `image_url`. Neither current type can truthfully represent or consume
an ADR-046 Binding or the bounded set defined here.

Accepted R1, carried forward by Accepted R2 except for the two explicit revisions above, closes only
the missing portable supplied-set boundary. It deliberately stops
before role-aware Provider materialization, Provider-specific slot/order/duplicate rules, final
request authorization or execution.

## Decision summary

Accepted R1, as carried forward and narrowly revised by Accepted R2, constrains any separately
authorized BUILD to:

1. represent one immutable historical bounded Set over one explicitly supplied canonical non-empty
   tuple of exact positive ADR-046 Bindings;
2. add exactly three top-level formal Contracts only after separate BUILD authorization: Set
   Request, Set Decision and positive Set, with target/member/gate definitions kept inline;
3. restrict one Set to one exact ADR-042 Artifact, Profile/Catalog identity, subject, purpose, one
   primary AssetVersion binding recorded identically by every historical member and revalidated as
   active at Request/final time, and field-for-field equal reviewed Rights scope;
4. allow Character cardinality `1..3` and Scene cardinality `1..4`, with requested roles forming an
   already canonical non-empty subset of the frozen purpose role tuple;
5. distinguish an explicit proper subset from the exact full purpose role tuple without claiming
   global completeness, exclusivity, latest, best or currentness;
6. require exactly one distinct positive Binding for each requested role and reject duplicate roles
   or duplicate Binding identities;
7. allow one Sidecar occurrence to serve different requested roles only through separate exact
   positive atomic Bindings, while never deduplicating different Candidate/Sidecar occurrences merely
   because their raw PNG bytes are equal;
8. require one Set Maker/Selector to prepare the exact member tuple and one independent Set Checker
   to record the final decision without changing members, roles, order or coverage mode;
9. revalidate every complete ADR-046 predecessor closure and exact whole PNG, then perform complete
   per-member fresh current-status replay at Request preparation and again at exact `set_at`;
10. rebuild and compare the one common imported primary binding at both operations and retain every
    member's exact reviewed Rights anchors without union, intersection, renewal or expansion;
11. make a positive Decision and Set one atomic pure result; valid negative or indeterminate policy
    outcomes would produce Decision-only results; and
12. preserve complete zero Provider, Runtime, network, credential, cost, Retry, asset-use,
    publication, retention and training authority.

A conforming positive R2 Set would mean only:

> At one explicit historical `set_at`, one independent Set Checker approved that one explicitly
> supplied canonical tuple contained exactly one revalidated positive atomic Binding for every
> explicitly requested role under one closed common frame, after complete per-member fresh replay
> and exact whole-PNG verification.

It would not mean that the Set is globally complete or exclusive, remains current, contains distinct
media per role, has Provider slot order, can become an `InputMaterial` or authorizes asset use,
Provider execution, publication or training.

## Accepted R1/R2 record and implementation gate

Accepted R1 records human acceptance of the architecture decisions frozen in that revision. Accepted
R2 records human acceptance of exactly the two replacements and new policy identity frozen here.
Neither acceptance authorizes any Contract, Schema, Registry, fixture, source, test, codegen, CI,
Makefile or implementation change, actual Set selection, media review, Provider input or execution.

R2 acceptance does not authorize BUILD. Any restart requires Accepted R2 first to be merged into
authoritative `main`, then separate explicit BUILD-restart authorization, a newly verified clean
authoritative `main`, a new isolated `codex/` implementation branch and a newly recorded immutable
89-Schema/20-fixture baseline. Human known-answer acceptance, Draft-to-Ready conversion and merge
authorization remain later separate gates.

The Accepted R1 review confirmed:

1. the bounded supplied historical Set representation and conservative common-frame restriction;
2. the exact three-model top-level family and inline target/member/gate shapes;
3. Character `1..3` and Scene `1..4` cardinality and canonical subset admission;
4. exact partial/full coverage meanings and all explicit non-proofs;
5. role uniqueness, Binding uniqueness, Sidecar reuse and equal-byte occurrence rules;
6. complete supplied closure, exact whole-PNG admission and two fresh replays per member;
7. common primary-binding equality and field-for-field common Rights-scope equality;
8. Maker/Selector and Checker responsibility and identity-separation matrix;
9. target, Request, Decision and Set identity DAG and domain-separated projections;
10. gate order, issue order, failure priority and positive pair atomicity;
11. resource, privacy, canonical-codec and complete zero-authority limits;
12. Provider-input, Compiler, Runtime and persistence isolation;
13. the 89-Schema/20-fixture compatibility gate and frozen future 92-Schema/22-fixture target; and
14. the exact future BUILD changed-file allowlist.

The R2 human acceptance confirms exactly:

1. each exact ADR-046 Request/finalization verifier remains one atomic delegated stage that inherits
   the released ADR-046 internal first-failure order;
2. only exact `GeneratedReferenceRoleBindingError.code == "PNG_ADMISSION_INVALID"` at either exact
   verifier call site maps to `RAW_MEDIA_MISMATCH`, while the other 18 frozen ADR-046 codes map to
   `ROLE_BINDING_FINALIZATION_INVALID` without message parsing;
3. Accepted R1's 25-path BUILD allowlist expands to exactly 27 paths solely for the two frozen typed,
   read-only fixed-fixture codegen support APIs;
4. the exact policy identity is version `1.1.0`, 38,481 canonical compact bytes and SHA-256
   `77bdbb2f8845af02ab72e70ad1c74276e218f27410ff4384547d3868ec1a8c9e`; and
5. the stopped partial BUILD cannot restart except through the separately authorized clean-worktree
   gate frozen below.

This section is the R1/R2 architecture acceptance record and complete zero-authority boundary. It is
not a BUILD authorization.

## Frozen upstream compatibility boundary

Neither Accepted R1 nor Accepted R2 narrows, supersedes or reinterprets ADR-039 through ADR-046. In
particular:

- ADR-042 continues to admit only one complete Character three-role or Scene four-role reference
  Prompt Artifact; its roles remain Prompt/layout semantics, not pixel proof or Provider slots;
- an ADR-045 Sidecar remains historical, supplemental to one unchanged imported primary
  AssetVersion and neither role-bound nor Provider-input eligible;
- every ADR-046 Binding remains one immutable atomic, non-exclusive, occurrence-specific historical
  value and keeps every false completeness/currentness/exclusivity field unchanged;
- Set construction cannot mutate or refresh a Binding, Sidecar, Manifest, Qualification, status
  Record, AssetVersion or Bible;
- current Character/Scene AssetVersion provenance remains `IMPORTED_APPROVED_MEDIA` and no generated
  bytes validate as a V1 AssetVersion;
- current Compiler, Storyboard, NIR, PIR, Compilation, JobGraph and AssemblyPlan identities remain
  unchanged;
- all existing zero-authority literals remain exact required values;
- the first 89 Registry entries and all 89 committed Schema bytes remain unchanged;
- all 20 current tracked visual-prompt fixture paths and bytes remain unchanged; and
- historical 83-Schema/16-fixture and 86-Schema/18-fixture prefix assertions remain in force in
  addition to the new 89/20 baseline.

The dependency order remains:

```text
Candidate / Qualification
  -> Generated Rights Manifest / current status
  -> Promotion
  -> atomic Role Binding
  -> bounded supplied Role-Binding Set
  -> separate Provider Input Material V2 / final request authorization
  -> Runtime / Provider execution
```

No existing Contract would gain an optional field, union member, enum literal, conversion method or
duck-typed compatibility route.

## Terminology and lifecycle

Accepted R1 and Accepted R2 use these terms narrowly:

1. **Atomic Binding**: one exact positive ADR-046 association between one Sidecar occurrence's whole
   PNG and one exact role.
2. **Common frame**: the exact Artifact, Profile/Catalog identity, subject, purpose, imported primary
   binding recorded identically in every historical member, and reviewed Rights scope shared by
   every member; the primary binding is separately revalidated as active at Request and final time.
3. **Set Maker/Selector**: one retained human review identity that explicitly supplies the requested
   role tuple and exact positive Binding tuple and prepares the Set Request.
4. **Set Checker**: one independent retained human review identity that reviews the unchanged
   supplied tuple after final replay and records the Set Decision.
5. **Requested roles**: one explicit non-empty canonical subset of the exact complete purpose role
   tuple carried by every member Binding target.
6. **PARTIAL**: the requested-role tuple is a proper non-empty subset of the full frozen purpose
   tuple.
7. **FULL**: the requested-role tuple equals the exact complete frozen purpose tuple.
8. **Member occurrence**: one exact Role-Binding Request/Decision/Binding and its complete
   Candidate/Sidecar/upstream/raw-PNG closure; raw-byte equality does not merge occurrences.
9. **Positive Set**: immutable historical evidence that every requested role had exactly one positive
   revalidated supplied member and the one Set-level 13-gate tuple over the complete exact ordered
   member tuple passed under the closed common frame at exact `set_at`.
10. **Fresh replay**: reconstruction from complete explicitly supplied status evidence; parsing a
    retained Receipt, copying `CURRENT` or checking an old deadline is not replay.

The frozen lifecycle is append-only:

```text
positive atomic Bindings
  -> explicit Set Maker/Selector member proposal
  -> per-member Request-time fresh replay
  -> Set Request
  -> per-member final fresh replay + Set Checker review
  -> Set Decision
  -> positive Set only when every gate passes
```

A later adverse record or changed member selection would require a new Set closure. A changed
Manifest identity or reviewed scope, changed Qualification or changed active primary AssetVersion
would first require a new complete upstream Promotion and atomic Role-Binding lifecycle; a new Set
could not substitute a renewed Manifest into an old Binding. No old Binding or Set would be mutated,
refreshed, superseded or deleted.

## Bounded supplied-set representation choice

Accepted R2 carries forward R1's choice of one portable ordered Set, not a database view, filesystem
directory, query result,
mutable pack or active pointer. The complete set boundary would be carried by the formal values and
their explicitly supplied predecessors.

The Set would allow a singleton. This avoids a second mechanism for one selected role and makes the
same uniqueness, replay and authority rules apply uniformly. The term `Set` would therefore mean a
bounded ordered finite selection, not a mathematical unordered collection and not proof of multiple
distinct media values.

One positive Set would directly carry:

```text
explicit_requested_role_subset_satisfied=true
complete_role_set_asserted=false
global_role_uniqueness_asserted=false
role_binding_exclusivity_asserted=false
present_currentness_asserted=false
current_set_asserted=false
supersedes_role_binding_set=false
provider_input_eligible=false
provider_order_asserted=false
```

`complete_role_set_asserted` remains false even for `FULL`. `FULL` states only that the exact
purpose-specific role vocabulary is represented once in this explicitly supplied Set. It does not
prove that no other Binding or Set exists, that the members are exclusive, or that the Set remains
complete after `set_at`.

## Exact common frame

Every member would have to reproduce one exact common frame:

```text
reference_prompt_artifact_sha256
asset_purpose
subject_id
profile_id
profile_version
profile_sha256
catalog_version
catalog_sha256
reference_asset_types
reviewed_rights_scope
primary_asset_binding
```

The full `reference_asset_types` tuple would equal the exact complete Character or Scene tuple. The
exact ADR-042 Artifact SHA, rather than only Profile identity, would also be common. Accepted R2 would
reject cross-Artifact, cross-Profile, cross-Catalog, cross-subject, cross-purpose,
mixed-primary-binding or different-Rights-scope tuples.

Different members could still carry different Provider Attempt Outcome, Candidate, Sidecar,
Promotion and Role-Binding identities, provided all common-frame fields match exactly. Requiring
field-for-field equal reviewed Rights scopes would be an admission restriction, not a Set-level
Rights union or legal conclusion. Each member's Manifest and Rights anchors would remain explicit.

## Exact set purpose, role vocabulary and cardinality

The exact role orders remain:

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

Character requested roles would contain `1..3` values. Scene requested roles would contain `1..4`.
They must be a unique non-empty subsequence in the exact frozen order. A caller-supplied reversed,
sorted-differently, duplicated, unknown or cross-purpose tuple would fail; code would not sort,
repair, infer or expand it.

Coverage would be derived uniquely:

```text
requested roles == full purpose tuple
  -> EXACT_FULL_PURPOSE_ROLE_TUPLE

requested roles == non-empty proper canonical subset
  -> EXPLICIT_PARTIAL_PURPOSE_ROLE_SUBSET
```

The caller could not choose a contradictory coverage literal. FULL would not require distinct media
bytes, Candidate occurrences or Sidecars for each role; it would require one distinct positive
revalidated atomic Binding per role.

## Exact supplied member closure and admission

For every member, the future pure operation would receive and fully revalidate:

- exact ADR-046 Role-Binding Request, positive Decision and positive Binding;
- the complete ADR-045 Promotion Request/Decision/Sidecar closure;
- complete ADR-042/043/044 Artifact, Outcome, Candidate, Qualification, Manifest and historical
  status predecessors required by ADR-046 verification;
- exact Role-Binding Request-time and final status closures;
- exact historical and newly caller-supplied primary Bible/AssetVersion snapshots;
- exact Role-Binding Maker/Checker identity and action records;
- the exact original whole PNG bytes matching the Candidate/Sidecar/Binding occurrence; and
- all explicit request/final times, human results and bounded bases needed for deterministic
  reconstruction.

The Set operation would then additionally receive:

- one explicit requested-role tuple and one same-length ordered member tuple;
- one complete Set Request-time current-status closure per member;
- one complete Set-final current-status closure per member;
- exact common Request-time and final primary Bible/AssetVersion snapshots;
- exact Set Maker/Selector and Set Checker identity/action records; and
- caller-supplied canonical UTC-second `requested_at` and `set_at` values.

An ID, digest, object reference, retained Receipt, copied `CURRENT` literal, path, URL, thumbnail or
Provider reference could not replace any required complete value or raw byte sequence. Every input
would be exact-type revalidated; subclasses, coercion, unknown fields and duck-typed objects would
fail closed.

## Canonical order, uniqueness and duplicate-occurrence rules

The member tuple would have the same length and role order as `requested_reference_roles`.
`selection_ordinal` values would be consecutive from zero and enter every target and outer identity.
For every ordinal:

```text
member.selected_reference_role == requested_reference_roles[ordinal]
member Binding target selected_reference_role == member.selected_reference_role
```

Accepted R2 retains these exact duplicate rules:

- each requested role occurs exactly once;
- each exact `binding_id`/`binding_sha256` pair occurs exactly once;
- a repeated Decision/Binding pair is structural failure even if used under a different ordinal;
- the same Sidecar occurrence may appear under different roles only when each role has its own exact
  positive atomic Binding;
- different Sidecar/Candidate occurrences remain distinct when `media_content_sha256` and raw bytes
  are equal;
- raw media hash, Sidecar ID, Candidate ID, time or storage order is never a deduplication or
  selection key;
- repeated historical reviews for one role require the Maker to name exactly one supplied Binding;
  there is no latest/best resolver; and
- canonical Set order is a semantic identity order only and never Provider slot order.

A structural failure in any member would produce no formal result. A structurally valid final
adverse or indeterminate policy result would decide the exact original requested tuple. The
implementation could not remove, replace or reorder a failed member and return a favorable smaller
Set.

## Partial/full-set and completeness semantics

PARTIAL and FULL would describe only role vocabulary coverage within the common frame:

| Coverage | Exact proof | Explicit non-proofs |
| --- | --- | --- |
| `EXPLICIT_PARTIAL_PURPOSE_ROLE_SUBSET` | Every explicitly requested proper-subset role has exactly one positive revalidated member, and the one Set-level 13-gate tuple over the complete exact ordered member tuple passed at `set_at` | No omitted role exists or is unsuitable; the subset is best/current; Provider accepts partial input |
| `EXACT_FULL_PURPOSE_ROLE_TUPLE` | Every role in the frozen Character three-role or Scene four-role tuple has exactly one positive revalidated member, and the one Set-level 13-gate tuple over the complete exact ordered member tuple passed at `set_at` | Global completeness, uniqueness, exclusivity, distinct media, Provider count/order or future currentness |

The positive Set would always retain `complete_role_set_asserted=false` and
`global_role_uniqueness_asserted=false`. Consumer-facing words such as “complete pack”, “active set”
or “ready references” could not appear in semantic literals or permitted claims.

## Fresh current-status replay and evidence horizon

Each member would form this monotonic chain:

```text
ADR-046 final status Record
  -> Set Request-time status Record
  -> Set-final status Record
```

Both new stages must use complete explicitly supplied evidence and preserve the same Candidate,
Qualification Decision, Manifest, subject, purpose and status policy. Each successor Record must
cover every target, branch and predecessor required by the prior stage. Omitted branches,
favorable-subset replay, replaced targets and copied Receipts are structural failures.

Request preparation would require every member to replay as `CURRENT` at the exact common
`requested_at`. `CURRENT` would admit that member. A valid complete `REVOKED`, `HELD` or
`INDETERMINATE` replay would deterministically raise
`REQUEST_MEMBER_STATUS_NOT_CURRENT` and create no Request. `EXPIRED` would be
`TIME_OR_VALIDITY_INVALID`; an incomplete, copied or mismatched replay would be
`CURRENT_STATUS_REPLAY_INVALID`. None of those paths could create a Request.

Finalization would replay every member at the exact common `set_at`. Valid deterministic adverse
status within all applicable validity bounds (`REVOKED` or `HELD`) would map to a negative Decision.
Valid `INDETERMINATE` status with no deterministic failure would map to an indeterminate Decision.
`EXPIRED` at the exact final `as_of` would contradict the required half-open Manifest/final-status
bounds and therefore map deterministically to `TIME_OR_VALIDITY_INVALID` with no Decision. A
supplied Receipt that differed from fresh replay would instead be `CURRENT_STATUS_REPLAY_INVALID`.
Any other replay construction, linkage or coverage failure would likewise produce no formal result.

Time equality would be exact:

```text
every member.binding_at <= requested_at
maker_prepared_at == requested_at
every Request-time Receipt.as_of == requested_at
requested_at < every member Qualification valid_until
requested_at < every member Manifest valid_until
requested_at < every Request-time status_valid_until
requested_at < request_valid_until

requested_at <= set_at < request_valid_until

checker_reviewed_at == decision_at == set_at
every final Receipt.as_of == set_at
set_at < every member Qualification valid_until
set_at < every member Manifest valid_until
set_at < every final status_valid_until
set_at < set_evidence_valid_until
```

`request_valid_until` would be the minimum of `requested_at + 86400 seconds` and every member's
Qualification, Manifest and Request-time status exclusive upper bound. Equality with any upper
bound would fail.

`set_evidence_valid_until` would be the minimum of every member's Qualification, Manifest and final
status exclusive upper bound. It would describe only the historical evidence horizon at
construction. An old `binding_evidence_valid_until` could not replace new replay, and the positive
Set would retain `present_currentness_asserted=false`. Every later consumer would have to replay
again at its own explicit `as_of`.

No wall clock, timezone default, environment value, filesystem timestamp, random value, database
state or network result could provide any semantic time.

## Primary binding and Rights preservation

One caller-supplied Character or Scene Bible snapshot and active imported AssetVersion would be
fully revalidated at Request preparation. The rebuilt `requested_primary_asset_binding` must equal
every member Binding's historical `primary_asset_binding`. A second explicitly supplied snapshot
would be rebuilt at finalization; the rebuilt `final_primary_asset_binding` must equal the requested
binding and every member's historical binding for a positive Set.

One valid same-subject/purpose active-binding drift at finalization would produce a negative gate and
no positive Set. A malformed, cross-subject, cross-purpose, forged or ambiguous snapshot would be
structural failure. Set construction would never replace or mutate an AssetVersion or Bible.

Every member's exact Manifest identity and reviewed Rights scope would be retained. Accepted R2 would
also require all reviewed scope objects to be field-for-field equal as a common-frame admission rule.
Code could not union, intersect, narrow, reorder, renew, extend or reinterpret scopes. Set Checker
acknowledgement would mean only that the unchanged per-member scopes and exact member tuple were
jointly presented; it would not decide that a role lies within a legal scope or grant Rights.

Every completely revalidated member closure would retain all five historical literals:

```text
grants_rights=false
replaces_rights_manifest=false
primary_asset_binding_replaced=false
bible_active_binding_changed=false
asset_version_v1_created=false
```

The future Set top-level Contracts would directly carry `grants_rights=false` and
`replaces_rights_manifest=false` through the shared zero-authority suffix below. The other three
literals would remain inside each fully retained member Role-Binding closure and would be
revalidated there; they would not be duplicated as Set top-level fields.

## Human review and retained identity separation

Set selection would be an explicit Set Maker/Selector responsibility. Accepted R2 would not create a
free-floating selector decision, recommendation record or automatic selector. The Maker/Selector
action would bind the
exact target, ordered requested roles, ordered member tuple, coverage literal, common primary
binding, per-member Request Receipts, `requested_at` and bounded basis.

The Set Checker could record only `PASS`, `FAIL` or `INDETERMINATE` findings over that exact unchanged
proposal after final replay; the frozen policy would derive the approve/reject/indeterminate
Decision. The Checker could not add, remove, replace, reorder or relabel a member. Any change would
require a new Maker/Selector action and Request.

The Set Checker semantic identity tuple would have to differ from:

```text
SET_MAKER_SELECTOR
every member QUALIFICATION_QUALIFIER
every member MANIFEST_CHECKER
every member PROMOTION_REQUEST_STATUS_CHECKER
every member PROMOTION_FINAL_STATUS_CHECKER
every member PROMOTION_CHECKER
every member ROLE_BINDING_CHECKER
every member ROLE_BINDING_REQUEST_STATUS_CHECKER
every member ROLE_BINDING_FINAL_STATUS_CHECKER
every member SET_REQUEST_STATUS_CHECKER
every member SET_FINAL_STATUS_CHECKER
```

The Set Maker/Selector could not equal the Set Checker. Its exact permitted upstream overlaps and
the exact cross-member/status-stage reuse rule are the closed lists below; no unlisted or future role
would gain permission automatically. All comparisons would use the exact admitted
`(identity_namespace, identity_ref)` tuple, never merely hash inequality.

The Set Maker/Selector could equal exactly these supplied upstream roles:

```text
QUALIFICATION_REQUEST_PREPARER
QUALIFICATION_QUALIFIER
MANIFEST_MAKER
MANIFEST_CHECKER
PROMOTION_REQUEST_STATUS_PREPARER
PROMOTION_REQUEST_STATUS_CHECKER
PROMOTION_FINAL_STATUS_PREPARER
PROMOTION_FINAL_STATUS_CHECKER
PROMOTION_MAKER
PROMOTION_CHECKER
ROLE_BINDING_REQUEST_STATUS_PREPARER
ROLE_BINDING_REQUEST_STATUS_CHECKER
ROLE_BINDING_FINAL_STATUS_PREPARER
ROLE_BINDING_FINAL_STATUS_CHECKER
ROLE_BINDING_MAKER
ROLE_BINDING_CHECKER
SET_REQUEST_STATUS_PREPARER
SET_REQUEST_STATUS_CHECKER
SET_FINAL_STATUS_PREPARER
SET_FINAL_STATUS_CHECKER
```

One status Preparer or Checker identity could be reused across members and across Request/final
Set stages when all relevant upstream role rules permit that reuse. Every reused status Checker
would still have to differ from the Set Checker. The Set Maker/Selector permission list and the
status-reuse rule are exhaustive for R2; a later role would require an ADR revision.

Maker/Selector and Checker action-record raw digests would have to differ from one another and from
every formal semantic digest, raw Prompt/PNG digest and external evidence digest. An identity-record
raw digest could repeat only for roles whose exact tuple equality the closed matrix permits.

Retained identity records would prove only that supplied semantic references differ. They would not
authenticate a natural person, organization, account, competence, employment, ACL, legal authority
or signature.

### Exact retained identity and action records

Every privacy-minimized human identity record would be canonical compact JSON with exactly:

```text
document_profile=sdc.privacy-minimized-human-reference.v1
identity_namespace: PortableId
identity_ref: PortableId
```

The Set Maker/Selector action would be canonical compact JSON with exactly:

```text
document_profile=sdc.generated-reference-bounded-supplied-role-binding-set-maker-action.v1
action=PREPARED_BOUNDED_SUPPLIED_ROLE_BINDING_SET_REQUEST
actor_ref_sha256: raw LowerSha256 of the exact Maker/Selector identity record
policy_id: exact Set policy ID
policy_version: exact Set policy version
policy_document_sha256: exact Set policy raw digest
set_review_payload_sha256: LowerSha256
target_sha256: LowerSha256
ordered_member_binding_sha256s: tuple[LowerSha256, 1..4]
requested_reference_roles: canonical purpose-specific tuple[ReferenceRole, 1..4]
role_coverage: EXPLICIT_PARTIAL_PURPOSE_ROLE_SUBSET | EXACT_FULL_PURPOSE_ROLE_TUPLE
requested_primary_asset_binding_sha256: LowerSha256
requested_status_receipt_sha256s: tuple[LowerSha256, 1..4]
prepared_at: canonical UTC seconds
request_basis: HumanBasis(1..1000)
```

The Set Checker action would be canonical compact JSON with exactly:

```text
document_profile=sdc.generated-reference-bounded-supplied-role-binding-set-checker-action.v1
action=RECORDED_BOUNDED_SUPPLIED_ROLE_BINDING_SET_DECISION
actor_ref_sha256: raw LowerSha256 of the exact Set Checker identity record
policy_id: exact Set policy ID
policy_version: exact Set policy version
policy_document_sha256: exact Set policy raw digest
request_id: PortableId
request_sha256: LowerSha256
target_sha256: LowerSha256
ordered_member_binding_sha256s: tuple[LowerSha256, 1..4]
final_status_receipt_sha256s: tuple[LowerSha256, 1..4]
final_primary_asset_binding_sha256: LowerSha256
rights_presentation_result: PASS | FAIL | INDETERMINATE
rights_presentation_basis: HumanBasis(1..1000)
selection_order_coverage_result: PASS | FAIL | INDETERMINATE
selection_order_coverage_basis: HumanBasis(1..1000)
non_exclusive_no_provider_boundary_result: PASS | FAIL | INDETERMINATE
non_exclusive_no_provider_boundary_basis: HumanBasis(1..1000)
gate_results: exact ordered tuple[GeneratedReferenceRoleBindingSetGateResultV1, 13]
set_issue_codes: canonical tuple[SetIssueCode, 0..5]
decision_basis: HumanBasis(1..1000)
decision: APPROVE_BOUNDED_SUPPLIED_ROLE_BINDING_SET |
          REJECT_BOUNDED_SUPPLIED_ROLE_BINDING_SET |
          INDETERMINATE_BOUNDED_SUPPLIED_ROLE_BINDING_SET
set_materialization_allowed: bool derived from the complete gate tuple
reviewed_at: canonical UTC seconds
```

Every per-member action array (`ordered_member_binding_sha256s` and the Request/final Receipt digest
arrays) would have length `member_count` and match exact target order. `requested_reference_roles`
would equal the target role tuple. The Checker `gate_results` would instead have exactly 13 entries
and `set_issue_codes` would have `0..5` entries under their own closed orders. The admitted raw bytes,
not a reconstructed equivalent document, would be hashed into the Request or Decision.
Unknown/missing fields, noncanonical JSON, action/actor mismatch or any action-to-formal-field
mismatch would be structural failure.

## Future inline Role-Binding Set target

If separately authorized, the Set target would be a strict frozen inline model, not a top-level
Registry entry. It would carry only bounded identity fields and no raw documents or bytes.

The inline type would be named
`GeneratedReferenceEligibleAssetRoleBindingSetTargetV1` and have exactly these required fields in
semantic projection order:

```text
target_sha256: LowerSha256
reference_prompt_artifact_sha256: LowerSha256
asset_purpose: CHARACTER_REFERENCE_ASSET | SCENE_REFERENCE_ASSET
subject_id: PortableId
profile_id: PortableId
profile_version: SemanticVersion
profile_sha256: LowerSha256
catalog_version: SemanticVersion
catalog_sha256: LowerSha256
reference_asset_types: exact full purpose tuple[ReferenceRole, 3 | 4]
requested_reference_roles: canonical tuple[ReferenceRole, Character 1..3 | Scene 1..4]
role_coverage: EXPLICIT_PARTIAL_PURPOSE_ROLE_SUBSET | EXACT_FULL_PURPOSE_ROLE_TUPLE
member_count: int, Character 1..3 | Scene 1..4
members: tuple[GeneratedReferenceEligibleAssetRoleBindingSetMemberV1, Character 1..3 | Scene 1..4]
common_reviewed_rights_scope: GeneratedReferenceReviewedRightsScopeV1
common_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
selection_scope=EXPLICIT_BOUNDED_SUPPLIED_ROLE_BINDING_SET_ONLY
provider_order_asserted=false
```

The inline member type would be named
`GeneratedReferenceEligibleAssetRoleBindingSetMemberV1` and have exactly these required fields in
semantic projection order:

```text
selection_ordinal: int 0..3
selected_reference_role: ReferenceRole
role_binding_request_id: PortableId
role_binding_request_sha256: LowerSha256
role_binding_decision_id: PortableId
role_binding_decision_sha256: LowerSha256
binding_id: PortableId
binding_sha256: LowerSha256
role_binding_target_sha256: LowerSha256
eligible_asset_sidecar_id: PortableId
eligible_asset_sidecar_sha256: LowerSha256
reference_prompt_artifact_sha256: LowerSha256
provider_attempt_outcome_id: PortableId
provider_attempt_outcome_sha256: LowerSha256
candidate_id: PortableId
candidate_sha256: LowerSha256
media_type=image/png
media_content_sha256: LowerSha256
media_size_bytes: int 1..67108864
media_technical_record_sha256: LowerSha256
binding_at: canonical UTC seconds
binding_evidence_valid_until: canonical UTC seconds
manifest_id: PortableId
manifest_sha256: LowerSha256
reviewed_rights_scope: GeneratedReferenceReviewedRightsScopeV1
primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
```

Those anchors could not substitute for the complete supplied predecessor values. Every field would
be reconstructed from and compared with the fully verified Binding closure before target
construction. Exact cross-field closure would require:

```text
member_count == len(requested_reference_roles) == len(members)
members[i].selection_ordinal == i
members[i].selected_reference_role == requested_reference_roles[i]
every member.reference_prompt_artifact_sha256 == target.reference_prompt_artifact_sha256
every member.reviewed_rights_scope == target.common_reviewed_rights_scope
every member.primary_asset_binding == target.common_primary_asset_binding
```

No field would be optional and no default value would repair missing input. `target_sha256` would be
the only self field excluded from the target semantic projection; every other target and complete
ordered member field would enter it.

## Future inline replay and gate types

`GeneratedReferenceRoleBindingSetMemberReplayV1` would be a strict frozen inline type with exactly:

```text
selection_ordinal: int 0..3
binding_id: PortableId
binding_sha256: LowerSha256
qualification_decision_id: PortableId
qualification_decision_sha256: LowerSha256
qualification_valid_until: canonical UTC seconds
manifest_id: PortableId
manifest_sha256: LowerSha256
manifest_valid_until: canonical UTC seconds
status_subject_closure_id: PortableId
status_subject_closure_sha256: LowerSha256
status_record_id: PortableId
status_record_sha256: LowerSha256
status_receipt_id: PortableId
status_receipt_sha256: LowerSha256
explicit_chain_set_sha256: LowerSha256
coverage_set_sha256: LowerSha256
joint_replay_sha256: LowerSha256
as_of_assessment_sha256: LowerSha256
as_of: canonical UTC seconds
as_of_status: CURRENT | EXPIRED | REVOKED | HELD | INDETERMINATE
status_valid_until: canonical UTC seconds
replay_scope: SET_REQUEST_ENTRY | SET_FINALIZATION
```

The tuple order and each ordinal would equal the target member order. Request replay values would all
use `SET_REQUEST_ENTRY`; final values would all use `SET_FINALIZATION`. An exact member Binding's
Candidate, Qualification, Manifest, status subject and prior Record closure would be fully
reconstructed rather than inferred from these anchors.

`EXPIRED` remains in the replay enum so an exact supplied Receipt can be represented and rejected;
it is not a reachable final gate value or negative Decision branch under the required strict
Manifest and final-status upper bounds.

`GeneratedReferenceRoleBindingSetGateResultV1` would be a strict frozen inline type with exactly:

```text
ordinal: int 0..12
gate: one exact member of the 13-value final gate order
result: PASS | FAIL | INDETERMINATE
basis: HumanBasis(1..1000)
```

The gate literal must equal the policy gate at the same ordinal. Compiler-derived gates would use
fixed compiler bases and could not be overridden by caller text. The three human gate results/bases
would equal the exact Checker action fields.

`SetIssueCode` would be the exact five-value closed literal set, in canonical tuple order:

```text
MEMBER_STATUS_NOT_CURRENT_AT_SET
COMMON_PRIMARY_BINDING_NO_LONGER_ACTIVE
PER_MEMBER_RIGHTS_PRESENTATION_NOT_ACKNOWLEDGED
EXPLICIT_SELECTION_ORDER_AND_COVERAGE_NOT_ACKNOWLEDGED
NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_NOT_ACKNOWLEDGED
```

`SetDecision` would be the exact closed literal set:

```text
APPROVE_BOUNDED_SUPPLIED_ROLE_BINDING_SET
REJECT_BOUNDED_SUPPLIED_ROLE_BINDING_SET
INDETERMINATE_BOUNDED_SUPPLIED_ROLE_BINDING_SET
```

None of these inline definitions would enter `sdc.schemas.MODELS`.

## Acyclic identity DAG

The frozen identity DAG is one-way and includes every retained human-action and replay dependency:

```text
complete positive atomic Binding closures + exact whole PNG bytes
  -> ordered inline member projections
  -> common Set target

common Set target + exact Request-time member replays
  + requested common primary binding + requested_at + zero-authority values
  -> Set review payload

Set review payload + Set Maker/Selector identity
  -> Set Maker/Selector action
  -> Set Request

Set Request + exact final member replays + final common primary binding
  + three human findings + deterministic gate/issue derivation
  -> final Decision values

final Decision values + Set Checker identity
  -> Set Checker action
  -> Set Decision

positive Set Decision + exact Set Request
  -> positive Set
```

Raw PNG SHA-256 values would remain undomained hashes of exact bytes. Every semantic projection would
use a unique literal NUL-terminated domain. The Maker/Selector action would contain the exact target,
review-payload and preparation inputs but no future Request, Decision or Set ID/SHA. A Request would
not contain a future Decision or Set identity. The Checker action would contain the exact Request
ID/SHA and final findings but no future Decision or Set ID/SHA. A Decision would contain the Request
identity but not a future Set identity. A positive Set would be last and contain both exact Request
and positive Decision identities.

No identity could depend on mutable storage, path, URL, ambient time, Provider response, Python
object traversal or later document discovery.

## Accepted R2 frozen policy projection

Accepted R2 freezes one new canonical compact JSON policy document and raw SHA-256. It carries every
unchanged R1 policy field forward, changes the policy version, freezes the delegated ADR-046
priority rule, freezes both support APIs and embeds the exact 27-path BUILD allowlist. The accepted
semantic policy is:

```json
{
  "adr_046_verifier_priority_rule": "EACH_EXACT_ADR_046_REQUEST_OR_FINALIZATION_VERIFIER_CALL_INHERITS_RELEASED_ADR_046_INTERNAL_FIRST_FAILURE_ORDER_WITH_NO_SET_LEVEL_PREFLIGHT_REORDERING_SECOND_PROBE_OR_LATER_FAULT_SEARCH",
  "build_changed_file_allowlist": [
    ".github/workflows/ci.yml",
    "Makefile",
    "schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetRequestV1.schema.json",
    "schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetDecisionV1.schema.json",
    "schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetV1.schema.json",
    "src/sdc/generated_reference_asset_promotion_codegen.py",
    "src/sdc/generated_reference_role_binding_codegen.py",
    "src/sdc/generated_reference_role_binding_set.py",
    "src/sdc/generated_reference_role_binding_set_codegen.py",
    "src/sdc/schemas.py",
    "tests/test_generated_reference_role_binding_set.py",
    "tests/test_generated_reference_role_binding_set_codegen.py",
    "tests/test_generated_reference_role_binding.py",
    "tests/test_generated_reference_candidate.py",
    "tests/test_generated_reference_rights_current_status_codegen.py",
    "tests/test_real_asset_fresh_status_chain_replay_v30.py",
    "tests/test_real_asset_fresh_status_record_as_of_assessment_receipt_codec_v30.py",
    "tests/test_real_asset_fresh_status_record_as_of_assessment_receipt_v30.py",
    "tests/test_real_asset_fresh_status_record_as_of_assessment_v30.py",
    "tests/test_real_asset_fresh_status_record_chain_coverage_v30.py",
    "tests/test_real_asset_fresh_status_record_joint_replay_v30.py",
    "tests/test_schemas.py",
    "tests/test_visual_prompt_compiler_integration.py",
    "tests/test_visual_prompt_profile_codegen.py",
    "tests/test_visual_reference_prompt_compiler.py",
    "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json",
    "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/generated-known-answer-v1.json"
  ],
  "codec_rule": {
    "formal_documents": "UTF8_NFC_SORTED_KEYS_TWO_SPACE_INDENT_EXACTLY_ONE_TERMINAL_LF",
    "semantic_and_retained_records": "UTF8_NFC_SORTED_KEYS_COMPACT_NO_TERMINAL_LF"
  },
  "common_frame_rule": "ONE_EXACT_ARTIFACT_PROFILE_CATALOG_SUBJECT_PURPOSE_HISTORICAL_PRIMARY_BINDING_AND_FIELD_EQUAL_RIGHTS_SCOPE_REVALIDATED_AT_REQUEST_AND_FINAL",
  "contract_rule": "EXACTLY_THREE_TOP_LEVEL_REQUEST_DECISION_SET_MODELS_AT_REGISTRY_INDICES_89_90_91_WITH_INLINE_TARGET_MEMBER_REPLAY_AND_GATE_TYPES",
  "coverage_rule": {
    "EXACT_FULL_PURPOSE_ROLE_TUPLE": "REQUESTED_ROLES_EQUAL_EXACT_COMPLETE_PURPOSE_TUPLE_WITH_NO_GLOBAL_COMPLETENESS_CLAIM",
    "EXPLICIT_PARTIAL_PURPOSE_ROLE_SUBSET": "REQUESTED_ROLES_ARE_NONEMPTY_CANONICAL_PROPER_SUBSET"
  },
  "decision_mapping": {
    "ALL_GATES_PASS": "APPROVE_BOUNDED_SUPPLIED_ROLE_BINDING_SET",
    "ANY_GATE_FAIL": "REJECT_BOUNDED_SUPPLIED_ROLE_BINDING_SET",
    "NO_FAIL_ANY_GATE_INDETERMINATE": "INDETERMINATE_BOUNDED_SUPPLIED_ROLE_BINDING_SET"
  },
  "decision_precedence": "STRUCTURAL_FAILURE_NO_OUTPUT_THEN_FAIL_THEN_INDETERMINATE_THEN_PASS",
  "digest_domains": {
    "decision": "sdc:generated-reference-bounded-supplied-role-binding-set-decision:v1\u0000",
    "request": "sdc:generated-reference-bounded-supplied-role-binding-set-request:v1\u0000",
    "review_payload": "sdc:generated-reference-bounded-supplied-role-binding-set-review-payload:v1\u0000",
    "set": "sdc:generated-reference-bounded-supplied-role-binding-set:v1\u0000",
    "target": "sdc:generated-reference-bounded-supplied-role-binding-set-target:v1\u0000"
  },
  "duplicate_rule": {
    "duplicate_binding": "STRUCTURAL_FAILURE_NO_OUTPUT",
    "duplicate_role": "STRUCTURAL_FAILURE_NO_OUTPUT",
    "equal_bytes_distinct_occurrence": "KEEP_DISTINCT",
    "same_sidecar_distinct_role_distinct_binding": "ALLOW"
  },
  "error_code_count": 21,
  "error_code_order": [
    "RESOURCE_LIMIT_EXCEEDED",
    "CANONICAL_DOCUMENT_INVALID",
    "PROHIBITED_BOUNDARY_CONNECTION",
    "CONTRACT_FIELD_INVALID",
    "TIME_OR_VALIDITY_INVALID",
    "POLICY_IDENTITY_MISMATCH",
    "UPSTREAM_CLOSURE_MISMATCH",
    "ROLE_BINDING_FINALIZATION_INVALID",
    "COMMON_FRAME_MISMATCH",
    "DUPLICATE_ROLE_OR_BINDING",
    "ROLE_SELECTION_INVALID",
    "CANONICAL_ORDER_INVALID",
    "RAW_MEDIA_MISMATCH",
    "CURRENT_STATUS_REPLAY_INVALID",
    "REQUEST_MEMBER_STATUS_NOT_CURRENT",
    "PRIMARY_BINDING_INVALID",
    "RIGHTS_SCOPE_MISMATCH",
    "IDENTITY_RECORD_INVALID",
    "ACTION_RECORD_INVALID",
    "IDENTITY_SEPARATION_INVALID",
    "DECISION_OR_SET_REVALIDATION_FAILED"
  ],
  "error_condition_rules": [
    {
      "code": "RESOURCE_LIMIT_EXCEEDED",
      "condition": "ANY_FROZEN_SET_OWNED_DOCUMENT_CONTAINER_DEPTH_SEMANTIC_CAPSULE_RAW_LEAF_PNG_RECORD_ACTION_IDENTITY_BASIS_BYTE_OR_COUNT_LIMIT_EXCEEDED_BEFORE_DECODE"
    },
    {
      "code": "CANONICAL_DOCUMENT_INVALID",
      "condition": "BOUNDED_JSON_DOCUMENT_OR_RETAINED_RECORD_BYTES_NOT_EXACT_UTF8_NFC_DUPLICATE_FREE_JSON_CODEC_OR_TERMINAL_LF_OR_NOT_EQUAL_EXACT_CANONICAL_REENCODING_EXCLUDING_RAW_PNG"
    },
    {
      "code": "PROHIBITED_BOUNDARY_CONNECTION",
      "condition": "ANY_ZERO_AUTHORITY_LITERAL_DRIFT_OR_PROHIBITED_TYPE_FIELD_LOCATOR_PATH_URL_PROVIDER_RUNTIME_NETWORK_PERSISTENCE_IMPORT_OR_CALL_CONNECTION"
    },
    {
      "code": "CONTRACT_FIELD_INVALID",
      "condition": "EXACT_TYPE_SUBCLASS_COERCION_MISSING_UNKNOWN_LITERAL_PATTERN_SCALAR_OR_CARDINALITY_INVALID_AFTER_RESOURCE_CANONICAL_BOUNDARY_AND_TIME_EXCLUSIONS"
    },
    {
      "code": "TIME_OR_VALIDITY_INVALID",
      "condition": "UTC_SECONDS_TIME_EQUALITY_ORDER_HALF_OPEN_BOUND_QUALIFICATION_MANIFEST_OR_FINAL_EXPIRED_RULE_FAILED_EXCLUDING_COPIED_OR_MISMATCHED_RECEIPT"
    },
    {
      "code": "POLICY_IDENTITY_MISMATCH",
      "condition": "POLICY_ID_VERSION_DOCUMENT_BYTES_OR_DOCUMENT_SHA256_DIFFERS_FROM_FROZEN_POLICY"
    },
    {
      "code": "UPSTREAM_CLOSURE_MISMATCH",
      "condition": "ADR_042_THROUGH_ADR_045_FORMAL_PROJECTION_LINKAGE_OR_PREDECESSOR_REPLAY_FAILED_EXCLUDING_SET_FRESH_STATUS_PRIMARY_RAW_MEDIA_AND_ADR_046_SPECIALIZATIONS"
    },
    {
      "code": "ROLE_BINDING_FINALIZATION_INVALID",
      "condition": "AT_EXACT_ADR_046_REQUEST_OR_FINALIZATION_VERIFIER_CALL_SITE_ANY_FROZEN_NON_PNG_GENERATED_REFERENCE_ROLE_BINDING_ERROR_OR_ANY_ALLOWLISTED_RIGHTS_CURRENT_STATUS_ERROR_OR_SUPPLIED_POSITIVE_REQUEST_DECISION_BINDING_RESULT_DID_NOT_REBUILD_EXACTLY"
    },
    {
      "code": "COMMON_FRAME_MISMATCH",
      "condition": "ARTIFACT_PROFILE_CATALOG_SUBJECT_PURPOSE_OR_FULL_ROLE_VOCABULARY_DIFFERS_EXCLUDING_PRIMARY_BINDING_AND_RIGHTS"
    },
    {
      "code": "DUPLICATE_ROLE_OR_BINDING",
      "condition": "REQUESTED_ROLE_REPEATED_OR_EXACT_BINDING_ID_SHA256_IDENTITY_PAIR_REPEATED"
    },
    {
      "code": "ROLE_SELECTION_INVALID",
      "condition": "NONEMPTY_PURPOSE_SUBSET_CARDINALITY_MEMBER_ROLE_OR_DERIVED_COVERAGE_CLOSURE_FAILED_EXCLUDING_DUPLICATE_AND_ORDER"
    },
    {
      "code": "CANONICAL_ORDER_INVALID",
      "condition": "REQUESTED_ROLES_NOT_FROZEN_SUBSEQUENCE_OR_MEMBER_TUPLE_ORDINAL_ROLE_ORDER_DIFFERS_FROM_TARGET_WITH_NO_SORT_OR_REPAIR"
    },
    {
      "code": "RAW_MEDIA_MISMATCH",
      "condition": "AT_EXACT_ADR_046_REQUEST_OR_FINALIZATION_VERIFIER_CALL_SITE_GENERATED_REFERENCE_ROLE_BINDING_ERROR_CODE_EQUALS_PNG_ADMISSION_INVALID_OR_DIRECT_WHOLE_PNG_BYTES_SIZE_TECHNICAL_RAW_DIGEST_OUTCOME_CANDIDATE_SIDECAR_BINDING_OR_MEMBER_MEDIA_ANCHOR_DIFFERS"
    },
    {
      "code": "CURRENT_STATUS_REPLAY_INVALID",
      "condition": "SET_REQUEST_OR_FINAL_FRESH_REPLAY_BUILD_COVERAGE_LINKAGE_OR_RECEIPT_EXACT_VALUE_BYTE_EQUALITY_FAILED_EXCLUDING_VALID_REVOKED_HELD_OR_INDETERMINATE_OUTCOME"
    },
    {
      "code": "REQUEST_MEMBER_STATUS_NOT_CURRENT",
      "condition": "VALID_COMPLETE_SET_REQUEST_REPLAY_RESULT_IS_REVOKED_HELD_OR_INDETERMINATE_NO_REQUEST"
    },
    {
      "code": "PRIMARY_BINDING_INVALID",
      "condition": "REQUEST_OR_FINAL_BIBLE_ASSET_VERSION_REBUILD_DIGEST_OR_ACTIVE_EQUALITY_FAILED_EXCLUDING_VALID_ACTIVE_FINAL_DRIFT_GATE_FAIL"
    },
    {
      "code": "RIGHTS_SCOPE_MISMATCH",
      "condition": "MEMBER_MANIFEST_BINDING_MEMBER_OR_COMMON_SCOPE_NOT_FIELD_EQUAL_OR_WAS_NARROWED_EXPANDED_REORDERED_SUBSTITUTED_UNIONED_INTERSECTED_OR_RENEWED"
    },
    {
      "code": "IDENTITY_RECORD_INVALID",
      "condition": "IDENTITY_RAW_RECORD_CODEC_PROFILE_FIELDS_TYPE_OR_DIGEST_INVALID"
    },
    {
      "code": "ACTION_RECORD_INVALID",
      "condition": "MAKER_OR_CHECKER_ACTION_CODEC_PROFILE_FIELDS_DIGEST_ACTOR_ANCHOR_OR_FORMAL_GATE_ISSUE_DECISION_COPY_DIFFERS_EXCLUDING_IDENTITY_EQUALITY_POLICY"
    },
    {
      "code": "IDENTITY_SEPARATION_INVALID",
      "condition": "PROHIBITED_ACTOR_TUPLE_EQUALITY_UNLISTED_OVERLAP_OR_ACTION_FORMAL_RAW_DIGEST_NON_ALIAS_RULE_FAILED"
    },
    {
      "code": "DECISION_OR_SET_REVALIDATION_FAILED",
      "condition": "CALLER_DECISION_OR_SET_IDENTITY_PROJECTION_DOCUMENT_LINKAGE_OR_POSITIVE_PAIR_ATOMIC_MATERIALIZATION_REVALIDATION_INVARIANT_FAILED"
    }
  ],
  "error_tie_break_rule": "SET_OWNED_AND_DIRECT_CALL_SITES_USE_FIRST_APPLICABLE_ERROR_CODE_ORDER_THEN_COMMON_INPUTS_THEN_MEMBER_SELECTION_ORDINAL_THEN_FROZEN_PREDECESSOR_ORDER_ADR_046_VERIFIER_CALLS_INHERIT_RELEASED_INTERNAL_FIRST_FAILURE_STOP_AT_FIRST_REQUEST_SKIPS_FINAL_ONLY_CHECKS",
  "final_status_mapping": {
    "CURRENT": "PASS",
    "EXPIRED": "TIME_OR_VALIDITY_INVALID_NO_DECISION",
    "HELD": "FAIL",
    "INDETERMINATE": "INDETERMINATE",
    "REVOKED": "FAIL"
  },
  "fresh_replay_rule": "EVERY_MEMBER_FULL_REQUEST_AND_FINAL_REPLAY_NO_RECEIPT_OR_COPIED_CURRENT_SUBSTITUTION",
  "gate_order": [
    "EXACT_POSITIVE_ATOMIC_BINDING_CLOSURES",
    "COMMON_ARTIFACT_SUBJECT_PURPOSE_PROFILE_AND_CATALOG_EXACT",
    "CANONICAL_REQUESTED_ROLE_SUBSET_AND_COVERAGE_EXACT",
    "ONE_DISTINCT_BINDING_PER_REQUESTED_ROLE",
    "EXACT_CANDIDATE_OCCURRENCES_AND_RAW_WHOLE_MEDIA",
    "POSITIVE_UNEXPIRED_QUALIFICATIONS_AND_VALID_MANIFESTS",
    "EVERY_MEMBER_CURRENT_STATUS_AT_SET",
    "COMMON_PRIMARY_BINDING_EXACT",
    "PER_MEMBER_RIGHTS_SCOPES_UNCHANGED_AND_COMMON",
    "HUMAN_PER_MEMBER_RIGHTS_SCOPES_AND_EXACT_MEMBER_TUPLE_PRESENTED_WITHOUT_AGGREGATION_ACKNOWLEDGED",
    "HUMAN_EXPLICIT_SELECTION_ORDER_AND_COVERAGE_ACKNOWLEDGED",
    "HUMAN_NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_ACKNOWLEDGED",
    "SET_REVIEWER_SEPARATION"
  ],
  "gate_source_rules": [
    {
      "basis": "COMPILER_REVALIDATED_POSITIVE_ATOMIC_BINDING_CLOSURES",
      "gate": "EXACT_POSITIVE_ATOMIC_BINDING_CLOSURES",
      "ordinal": 0,
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    {
      "basis": "COMPILER_REVALIDATED_COMMON_ARTIFACT_SUBJECT_PURPOSE_PROFILE_CATALOG",
      "gate": "COMMON_ARTIFACT_SUBJECT_PURPOSE_PROFILE_AND_CATALOG_EXACT",
      "ordinal": 1,
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    {
      "basis": "COMPILER_REVALIDATED_CANONICAL_REQUESTED_ROLE_SUBSET_AND_COVERAGE",
      "gate": "CANONICAL_REQUESTED_ROLE_SUBSET_AND_COVERAGE_EXACT",
      "ordinal": 2,
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    {
      "basis": "COMPILER_REVALIDATED_DISTINCT_BINDING_PER_REQUESTED_ROLE",
      "gate": "ONE_DISTINCT_BINDING_PER_REQUESTED_ROLE",
      "ordinal": 3,
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    {
      "basis": "COMPILER_REVALIDATED_EXACT_CANDIDATE_OCCURRENCES_AND_WHOLE_MEDIA",
      "gate": "EXACT_CANDIDATE_OCCURRENCES_AND_RAW_WHOLE_MEDIA",
      "ordinal": 4,
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    {
      "basis": "COMPILER_REVALIDATED_UNEXPIRED_QUALIFICATIONS_AND_VALID_MANIFESTS",
      "gate": "POSITIVE_UNEXPIRED_QUALIFICATIONS_AND_VALID_MANIFESTS",
      "ordinal": 5,
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    {
      "basis": "COMPILER_REPLAYED_EVERY_MEMBER_STATUS_AT_SET",
      "gate": "EVERY_MEMBER_CURRENT_STATUS_AT_SET",
      "member_aggregation": "ANY_REVOKED_OR_HELD_FAIL_ELSE_ANY_INDETERMINATE_INDETERMINATE_ELSE_PASS",
      "ordinal": 6,
      "result_mapping_ref": "final_status_mapping",
      "source": "COMPILER_DERIVED_STATUS_AGGREGATION"
    },
    {
      "basis": "COMPILER_REVALIDATED_FINAL_COMMON_PRIMARY_BINDING",
      "gate": "COMMON_PRIMARY_BINDING_EXACT",
      "ordinal": 7,
      "result_mapping": {
        "EXACT_MATCH": "PASS",
        "VALID_ACTIVE_BINDING_DRIFT": "FAIL"
      },
      "source": "COMPILER_DERIVED_PRIMARY_BINDING_COMPARISON"
    },
    {
      "basis": "COMPILER_REVALIDATED_COMMON_UNCHANGED_PER_MEMBER_RIGHTS_SCOPES",
      "gate": "PER_MEMBER_RIGHTS_SCOPES_UNCHANGED_AND_COMMON",
      "ordinal": 8,
      "source": "COMPILER_DERIVED_PASS_ONLY"
    },
    {
      "basis_field": "rights_presentation_basis",
      "gate": "HUMAN_PER_MEMBER_RIGHTS_SCOPES_AND_EXACT_MEMBER_TUPLE_PRESENTED_WITHOUT_AGGREGATION_ACKNOWLEDGED",
      "ordinal": 9,
      "result_field": "rights_presentation_result",
      "source": "CHECKER_ACTION_EXACT_FIELD_PAIR"
    },
    {
      "basis_field": "selection_order_coverage_basis",
      "gate": "HUMAN_EXPLICIT_SELECTION_ORDER_AND_COVERAGE_ACKNOWLEDGED",
      "ordinal": 10,
      "result_field": "selection_order_coverage_result",
      "source": "CHECKER_ACTION_EXACT_FIELD_PAIR"
    },
    {
      "basis_field": "non_exclusive_no_provider_boundary_basis",
      "gate": "HUMAN_NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_ACKNOWLEDGED",
      "ordinal": 11,
      "result_field": "non_exclusive_no_provider_boundary_result",
      "source": "CHECKER_ACTION_EXACT_FIELD_PAIR"
    },
    {
      "basis": "COMPILER_REVALIDATED_SET_REVIEWER_SEPARATION",
      "gate": "SET_REVIEWER_SEPARATION",
      "ordinal": 12,
      "source": "COMPILER_DERIVED_PASS_ONLY"
    }
  ],
  "human_gate_order": [
    "HUMAN_PER_MEMBER_RIGHTS_SCOPES_AND_EXACT_MEMBER_TUPLE_PRESENTED_WITHOUT_AGGREGATION_ACKNOWLEDGED",
    "HUMAN_EXPLICIT_SELECTION_ORDER_AND_COVERAGE_ACKNOWLEDGED",
    "HUMAN_NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_ACKNOWLEDGED"
  ],
  "human_gate_source_rule": "CHECKER_ACTION_PRIMITIVE_PAIRS_ONLY_DERIVED_COPIES_EXACT_NO_SECOND_SOURCE",
  "id_stems": {
    "decision": "generated_reference_eligible_asset_role_binding_set_decision_v1_",
    "request": "generated_reference_eligible_asset_role_binding_set_request_v1_",
    "set": "generated_reference_eligible_asset_role_binding_set_v1_"
  },
  "identity_rule": "ORDERED_MEMBERS_AND_ORDINALS_ENTER_UNIQUE_NUL_TERMINATED_DOMAIN_PROJECTIONS_SELF_FIELDS_EXCLUDED_ONLY_FROM_OWN_PROJECTION",
  "issue_code_order": [
    "MEMBER_STATUS_NOT_CURRENT_AT_SET",
    "COMMON_PRIMARY_BINDING_NO_LONGER_ACTIVE",
    "PER_MEMBER_RIGHTS_PRESENTATION_NOT_ACKNOWLEDGED",
    "EXPLICIT_SELECTION_ORDER_AND_COVERAGE_NOT_ACKNOWLEDGED",
    "NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_NOT_ACKNOWLEDGED"
  ],
  "issue_mapping": {
    "COMMON_PRIMARY_BINDING_EXACT": "COMMON_PRIMARY_BINDING_NO_LONGER_ACTIVE",
    "EVERY_MEMBER_CURRENT_STATUS_AT_SET": "MEMBER_STATUS_NOT_CURRENT_AT_SET",
    "HUMAN_EXPLICIT_SELECTION_ORDER_AND_COVERAGE_ACKNOWLEDGED": "EXPLICIT_SELECTION_ORDER_AND_COVERAGE_NOT_ACKNOWLEDGED",
    "HUMAN_NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_ACKNOWLEDGED": "NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_NOT_ACKNOWLEDGED",
    "HUMAN_PER_MEMBER_RIGHTS_SCOPES_AND_EXACT_MEMBER_TUPLE_PRESENTED_WITHOUT_AGGREGATION_ACKNOWLEDGED": "PER_MEMBER_RIGHTS_PRESENTATION_NOT_ACKNOWLEDGED"
  },
  "known_answer_codegen_support_apis": {
    "sdc.generated_reference_asset_promotion_codegen": {
      "callable": "build_generated_reference_asset_promotion_fixed_fixture_support",
      "case_id_literals": [
        "character-same-status-record-v1",
        "scene-successor-reconciliation-v1"
      ],
      "parameters": [
        {
          "kind": "POSITIONAL_OR_KEYWORD",
          "name": "repository_root",
          "type": "pathlib.Path"
        },
        {
          "kind": "KEYWORD_ONLY",
          "name": "case_id",
          "type": "Literal[character-same-status-record-v1,scene-successor-reconciliation-v1]"
        }
      ],
      "return_dataclass": "GeneratedReferenceAssetPromotionFixedFixtureSupportV1",
      "return_field_types": {
        "case_id": "Literal[character-same-status-record-v1,scene-successor-reconciliation-v1]",
        "checker_action_bytes": "bytes",
        "checker_identity_bytes": "bytes",
        "composite_unsplit_role_deferral_basis": "str",
        "composite_unsplit_role_deferral_result": "GateResult",
        "final_status": "GeneratedReferenceAssetPromotionStatusClosureInput",
        "maker_action_bytes": "bytes",
        "maker_identity_bytes": "bytes",
        "primary_asset_version": "CharacterAssetVersion|SceneAssetVersion",
        "primary_bible": "CharacterBible|SceneBible",
        "primary_sidecar_association_basis": "str",
        "primary_sidecar_association_result": "GateResult",
        "promotion_at": "str",
        "promotion_basis": "str",
        "request": "CreativeSampleGeneratedReferenceAssetPromotionRequestV1",
        "request_status": "GeneratedReferenceAssetPromotionStatusClosureInput",
        "result": "GeneratedReferenceAssetPromotionFinalizationResult",
        "sidecar": "CreativeSampleGeneratedReferenceEligibleAssetSidecarV1",
        "upstream": "GeneratedReferenceAssetPromotionUpstreamClosureInput"
      },
      "return_fields": [
        "case_id",
        "upstream",
        "request_status",
        "final_status",
        "primary_bible",
        "primary_asset_version",
        "request",
        "result",
        "sidecar",
        "maker_identity_bytes",
        "maker_action_bytes",
        "checker_identity_bytes",
        "checker_action_bytes",
        "promotion_at",
        "primary_sidecar_association_result",
        "primary_sidecar_association_basis",
        "composite_unsplit_role_deferral_result",
        "composite_unsplit_role_deferral_basis",
        "promotion_basis"
      ],
      "return_invariants": "FROZEN_SLOTS_EXACT_POSITIVE_ADR_045_REQUEST_DECISION_SIDECAR_PAIR_VERIFIED_SIDECAR_IS_RESULT_SIDECAR_PRIMARY_PAIR_USED_FOR_REQUESTED_AND_PROMOTION_FORMAL_BYTES_VERIFIED"
    },
    "sdc.generated_reference_role_binding_codegen": {
      "callable": "build_generated_reference_role_binding_positive_fixed_fixture_support",
      "parameters": [
        {
          "kind": "POSITIONAL_OR_KEYWORD",
          "name": "promotion_support",
          "type": "GeneratedReferenceAssetPromotionFixedFixtureSupportV1"
        },
        {
          "kind": "KEYWORD_ONLY",
          "name": "selected_reference_role",
          "type": "Literal[CHARACTER_IDENTITY_SHEET,CHARACTER_POSE_REFERENCE,CHARACTER_EXPRESSION_REFERENCE,SCENE_ESTABLISHING_REFERENCE,SCENE_LIGHTING_REFERENCE,SCENE_MATERIAL_REFERENCE,SCENE_PROP_PLACEMENT_REFERENCE]"
        },
        {
          "kind": "KEYWORD_ONLY",
          "name": "maker_identity_bytes",
          "type": "bytes"
        },
        {
          "kind": "KEYWORD_ONLY",
          "name": "checker_identity_bytes",
          "type": "bytes"
        },
        {
          "kind": "KEYWORD_ONLY",
          "name": "request_basis",
          "type": "str"
        },
        {
          "kind": "KEYWORD_ONLY",
          "name": "exact_role_and_reviewed_rights_scope_presented_without_expansion_basis",
          "type": "str"
        },
        {
          "kind": "KEYWORD_ONLY",
          "name": "whole_composite_role_suitability_basis",
          "type": "str"
        },
        {
          "kind": "KEYWORD_ONLY",
          "name": "non_exclusive_no_transform_boundary_basis",
          "type": "str"
        },
        {
          "kind": "KEYWORD_ONLY",
          "name": "decision_basis",
          "type": "str"
        }
      ],
      "return_dataclass": "GeneratedReferenceRoleBindingPositiveFixedFixtureSupportV1",
      "return_field_types": {
        "admitted_png": "GeneratedReferenceRoleBindingAdmittedPng",
        "binding": "CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1",
        "checker_action_bytes": "bytes",
        "checker_identity_bytes": "bytes",
        "exact_role_and_reviewed_rights_scope_presented_without_expansion_basis": "str",
        "exact_role_and_reviewed_rights_scope_presented_without_expansion_result": "Literal[PASS]",
        "maker_action_bytes": "bytes",
        "maker_identity_bytes": "bytes",
        "non_exclusive_no_transform_boundary_basis": "str",
        "non_exclusive_no_transform_boundary_result": "Literal[PASS]",
        "primary_asset_version": "CharacterAssetVersion|SceneAssetVersion",
        "primary_bible": "CharacterBible|SceneBible",
        "promotion": "GeneratedReferenceRoleBindingPromotionClosureInput",
        "role_binding_at": "str",
        "role_binding_decision_basis": "str",
        "role_binding_final_status": "GeneratedReferenceAssetPromotionStatusClosureInput",
        "role_binding_request": "CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1",
        "role_binding_request_status": "GeneratedReferenceAssetPromotionStatusClosureInput",
        "role_binding_result": "GeneratedReferenceRoleBindingFinalizationResult",
        "selected_reference_role": "Literal[CHARACTER_IDENTITY_SHEET,CHARACTER_POSE_REFERENCE,CHARACTER_EXPRESSION_REFERENCE,SCENE_ESTABLISHING_REFERENCE,SCENE_LIGHTING_REFERENCE,SCENE_MATERIAL_REFERENCE,SCENE_PROP_PLACEMENT_REFERENCE]",
        "whole_composite_role_suitability_basis": "str",
        "whole_composite_role_suitability_result": "Literal[PASS]"
      },
      "return_fields": [
        "selected_reference_role",
        "promotion",
        "admitted_png",
        "role_binding_request",
        "role_binding_result",
        "binding",
        "role_binding_request_status",
        "role_binding_final_status",
        "primary_bible",
        "primary_asset_version",
        "maker_identity_bytes",
        "maker_action_bytes",
        "checker_identity_bytes",
        "checker_action_bytes",
        "role_binding_at",
        "exact_role_and_reviewed_rights_scope_presented_without_expansion_result",
        "exact_role_and_reviewed_rights_scope_presented_without_expansion_basis",
        "whole_composite_role_suitability_result",
        "whole_composite_role_suitability_basis",
        "non_exclusive_no_transform_boundary_result",
        "non_exclusive_no_transform_boundary_basis",
        "role_binding_decision_basis"
      ],
      "return_invariants": "FROZEN_SLOTS_REQUESTED_AT_EQUALS_BINDING_AT_EQUALS_PROMOTION_AT_ROLE_BINDING_REQUEST_AND_FINAL_STATUS_EQUAL_PROMOTION_FINAL_STATUS_PRIMARY_PAIR_FROM_PROMOTION_SUPPORT_THREE_HUMAN_RESULTS_EXACT_PASS_IN_MEMORY_PNG_FROM_PROMOTION_SUPPORT_ONLY_REQUEST_AND_POSITIVE_DECISION_BINDING_PAIR_VERIFIED_BINDING_IS_RESULT_BINDING_FORMAL_BYTES_VERIFIED"
    }
  },
  "known_answer_codegen_support_rule": "SET_CODEGEN_DIRECT_IMPORTS_ONLY_BUILD_GENERATED_REFERENCE_ASSET_PROMOTION_FIXED_FIXTURE_SUPPORT_AND_BUILD_GENERATED_REFERENCE_ROLE_BINDING_POSITIVE_FIXED_FIXTURE_SUPPORT_FROM_OLD_CODEGEN_NO_OLD_CODEGEN_MODULE_ALIAS_PRIVATE_DYNAMIC_REFLECTION_MAIN_PARSER_BUILD_EXPECTED_CLOSURE_UPDATE_OR_WRITER_ACCESS_SUPPORT_CALL_GRAPH_READS_ONLY_FROZEN_FIXTURE_PATHS_AND_NEVER_WRITES_NO_PRODUCTION_CORE_COMPILER_PROVIDER_RUNTIME_WORKER_QC_OR_PERSISTENCE_IMPORT",
  "member_cardinality": {
    "CHARACTER_REFERENCE_ASSET": [1, 3],
    "SCENE_REFERENCE_ASSET": [1, 4]
  },
  "member_rule": "EXACTLY_ONE_DISTINCT_POSITIVE_ATOMIC_BINDING_PER_EXPLICIT_REQUESTED_ROLE",
  "module_import_allowlist": {
    "sdc.contracts": [
      "CharacterAssetVersion",
      "CharacterBible",
      "SceneAssetVersion",
      "SceneBible"
    ],
    "sdc.generated_reference_asset_promotion": [
      "GeneratedReferenceAssetPromotionError",
      "GeneratedReferenceAssetPromotionStatusClosureInput",
      "GeneratedReferencePromotionPrimaryAssetBindingV1",
      "build_generated_reference_promotion_primary_asset_binding",
      "generated_reference_promotion_primary_asset_binding_sha256"
    ],
    "sdc.generated_reference_rights_current_status": [
      "CreativeSampleGeneratedReferenceCurrentStatusDecisionV1",
      "CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1",
      "CreativeSampleGeneratedReferenceCurrentStatusInstructionV1",
      "CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1",
      "CreativeSampleGeneratedReferenceCurrentStatusRequestV1",
      "CreativeSampleGeneratedReferenceRightsManifestV1",
      "GeneratedReferenceAsOfAssessmentError",
      "GeneratedReferenceChainCoverageError",
      "GeneratedReferenceChainReplayError",
      "GeneratedReferenceCurrentStatusExplicitChainInput",
      "GeneratedReferenceCurrentStatusSubjectClosureV1",
      "GeneratedReferenceJointReplayError",
      "GeneratedReferenceReceiptError",
      "GeneratedReferenceReviewedRightsScopeV1",
      "GeneratedReferenceRightsCurrentStatusError",
      "build_generated_reference_current_status_subject_closure",
      "generated_reference_contract_document_bytes",
      "process_generated_reference_current_status_record_as_of_assessment",
      "verify_generated_reference_current_status_evidence_record",
      "verify_generated_reference_current_status_record_as_of_assessment_receipt"
    ],
    "sdc.generated_reference_role_binding": [
      "CHARACTER_REFERENCE_ROLE_ORDER",
      "CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1",
      "CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1",
      "CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1",
      "GeneratedReferenceEligibleAssetRoleBindingTargetV1",
      "GeneratedReferenceRoleBindingAdmittedPng",
      "GeneratedReferenceRoleBindingError",
      "GeneratedReferenceRoleBindingFinalizationResult",
      "GeneratedReferenceRoleBindingPromotionClosureInput",
      "SCENE_REFERENCE_ROLE_ORDER",
      "creative_sample_generated_reference_eligible_asset_role_binding_decision_sha256",
      "creative_sample_generated_reference_eligible_asset_role_binding_request_sha256",
      "creative_sample_generated_reference_eligible_asset_role_binding_sha256",
      "generated_reference_role_binding_contract_document_bytes",
      "generated_reference_role_binding_target_sha256",
      "verify_generated_reference_eligible_asset_role_binding_finalization",
      "verify_generated_reference_eligible_asset_role_binding_request"
    ]
  },
  "module_isolation_rule": "CORE_IMPORTS_ONLY_EXACT_NAMED_PUBLIC_UPSTREAM_SYMBOLS_NO_OTHER_SDC_PRIVATE_DYNAMIC_OR_REVERSE_COMPILER_PROVIDER_RUNTIME_IMPORT",
  "opaque_upstream_resource_rule": "RELEASED_HIGH_LEVEL_VERIFIER_AND_FROZEN_UPSTREAM_POLICY_OWNS_MODEL_RESOURCE_VALIDATION_NO_SET_RESOURCE_RESERIALIZATION_OR_RESOURCE_REMEASUREMENT",
  "policy_id": "sdc.generated-reference-bounded-supplied-role-binding-set-policy",
  "policy_version": "1.1.0",
  "positive_atomicity_rule": "POSITIVE_DECISION_AND_SET_SAME_PURE_CALL_NO_PARTIAL_OUTPUT",
  "primary_binding_rule": "ONE_COMMON_IMPORTED_PRIMARY_BINDING_REBUILT_AT_REQUEST_AND_FINAL_NO_MUTATION_POSITIVE_REQUIRES_EQUALITY",
  "provider_input_rule": "NO_INPUT_MATERIAL_PROVIDER_SLOT_PROVIDER_ORDER_ROUTE_REQUEST_IDEMPOTENCY_OR_EXECUTION_CLAIM",
  "raw_byte_leaf_ledger": {
    "evidence_occurrences_per_member": {
      "MANIFEST": 9,
      "QUALIFICATION": 10
    },
    "final": {
      "action_occurrences_per_member": 20,
      "aggregate_all_raw_bytes_max": 512524288,
      "aggregate_non_png_raw_bytes_max": 244088832,
      "common_non_png_bytes_max": 557056,
      "common_non_png_leaf_occurrences": 4,
      "identity_occurrences_per_member": 20,
      "non_png_leaf_occurrences_max": 1776,
      "per_member_non_png_bytes_max": 60882944,
      "per_member_non_png_leaf_occurrences_max": 443,
      "png_inclusive_leaf_occurrences_max": 1780,
      "status_stages_per_member": 6
    },
    "human_action_or_evidence_leaf_bytes_max": 262144,
    "human_identity_leaf_bytes_max": 16384,
    "observation_document_bytes_per_status_stage_max": 8388608,
    "observation_document_occurrences_per_status_stage_max": 64,
    "request": {
      "action_occurrences_per_member": 18,
      "aggregate_all_raw_bytes_max": 476463104,
      "aggregate_non_png_raw_bytes_max": 208027648,
      "common_non_png_bytes_max": 278528,
      "common_non_png_leaf_occurrences": 2,
      "identity_occurrences_per_member": 18,
      "non_png_leaf_occurrences_max": 1502,
      "per_member_non_png_bytes_max": 51937280,
      "per_member_non_png_leaf_occurrences_max": 375,
      "png_inclusive_leaf_occurrences_max": 1506,
      "status_stages_per_member": 5
    },
    "status_stage_order": [
      "PROMOTION_REQUEST_STATUS",
      "PROMOTION_FINAL_STATUS",
      "ROLE_BINDING_REQUEST_STATUS",
      "ROLE_BINDING_FINAL_STATUS",
      "SET_REQUEST_STATUS",
      "SET_FINAL_STATUS"
    ]
  },
  "raw_byte_leaf_path_owners": {
    "C03_SET_MAKER_IDENTITY": [
      "set_maker_identity_bytes"
    ],
    "C04_SET_MAKER_ACTION": [
      "set_maker_action_bytes"
    ],
    "C08_SET_CHECKER_IDENTITY": [
      "set_checker_identity_bytes"
    ],
    "C09_SET_CHECKER_ACTION": [
      "set_checker_action_bytes"
    ],
    "M01_COMPLETE_PROMOTION_CLOSURE": [
      "role_binding_promotion_closure.upstream.qualification_evidence_documents[*].document_bytes",
      "role_binding_promotion_closure.upstream.qualification_preparer_identity_bytes",
      "role_binding_promotion_closure.upstream.qualification_preparer_action_bytes",
      "role_binding_promotion_closure.upstream.qualifier_identity_bytes",
      "role_binding_promotion_closure.upstream.qualifier_action_bytes",
      "role_binding_promotion_closure.upstream.manifest_review_evidence_documents[*].document_bytes",
      "role_binding_promotion_closure.upstream.manifest_maker_identity_bytes",
      "role_binding_promotion_closure.upstream.manifest_maker_action_bytes",
      "role_binding_promotion_closure.upstream.manifest_checker_identity_bytes",
      "role_binding_promotion_closure.upstream.manifest_checker_action_bytes",
      "role_binding_promotion_closure.request_status.<STATUS_CLOSURE_RAW_LEAVES>",
      "role_binding_promotion_closure.final_status.<STATUS_CLOSURE_RAW_LEAVES>",
      "role_binding_promotion_closure.maker_identity_bytes",
      "role_binding_promotion_closure.maker_action_bytes",
      "role_binding_promotion_closure.checker_identity_bytes",
      "role_binding_promotion_closure.checker_action_bytes"
    ],
    "M02_COMPLETE_ROLE_BINDING_CLOSURE_EXCLUDING_OWNED_M01": [
      "role_binding_request_status.<STATUS_CLOSURE_RAW_LEAVES>",
      "role_binding_final_status.<STATUS_CLOSURE_RAW_LEAVES>",
      "role_binding_maker_identity_bytes",
      "role_binding_maker_action_bytes",
      "role_binding_checker_identity_bytes",
      "role_binding_checker_action_bytes"
    ],
    "M03_EXACT_WHOLE_PNG_OCCURRENCE": [
      "role_binding_promotion_closure.upstream.png_bytes"
    ],
    "M04_SET_REQUEST_STATUS_CLOSURE": [
      "set_request_status.<STATUS_CLOSURE_RAW_LEAVES>"
    ],
    "M05_SET_FINAL_STATUS_CLOSURE": [
      "set_final_status.<STATUS_CLOSURE_RAW_LEAVES>"
    ],
    "STATUS_CLOSURE_RAW_LEAVES": [
      "chain_inputs[*].observation_inputs[*].document_bytes",
      "status_preparer_identity_bytes",
      "status_preparer_action_bytes",
      "status_checker_identity_bytes",
      "status_checker_action_bytes"
    ]
  },
  "raw_byte_leaf_rule": "COUNT_EACH_CALLER_SUPPLIED_BYTES_OCCURRENCE_NO_OBJECT_DIGEST_OR_CONTENT_DEDUP_STRUCTURAL_REFERENCE_TO_ONE_EXACT_FIELD_OWNED_ONCE_DIFFERENT_STAGE_MEMBER_OR_BUFFER_COUNTS_AGAIN",
  "raw_leaf_extraction_rule": "CLOSED_EXPLICIT_PUBLIC_FIELD_PATHS_ONLY_NO_MODEL_DUMP_REFLECTION_DATACLASS_WALK_OR_DYNAMIC_NAME",
  "raw_png_source_rule": "ONE_CALLER_SUPPLIED_MEMBER_ROLE_BINDING_PROMOTION_CLOSURE_UPSTREAM_PNG_BYTES_FIELD_NO_SECOND_PNG_PARAMETER_ADMITTED_WRAPPER_REBUILT_FROM_SAME_EXACT_BYTES",
  "request_entry_order": [
    "EXACT_POSITIVE_ATOMIC_BINDING_CLOSURES",
    "COMMON_ARTIFACT_SUBJECT_PURPOSE_PROFILE_AND_CATALOG_EXACT",
    "CANONICAL_REQUESTED_ROLE_SUBSET_AND_COVERAGE_EXACT",
    "ONE_DISTINCT_BINDING_PER_REQUESTED_ROLE",
    "EXACT_CANDIDATE_OCCURRENCES_AND_RAW_WHOLE_MEDIA",
    "POSITIVE_UNEXPIRED_QUALIFICATIONS_AND_VALID_MANIFESTS",
    "EVERY_MEMBER_CURRENT_STATUS_AT_REQUEST",
    "COMMON_PRIMARY_BINDING_EXACT_AT_REQUEST",
    "PER_MEMBER_RIGHTS_SCOPES_UNCHANGED_AND_COMMON",
    "SET_MAKER_SELECTOR_ACTION_AND_IDENTITY_VALID"
  ],
  "request_status_mapping": {
    "CURRENT": "ADMIT_REQUEST_STATUS",
    "EXPIRED": "TIME_OR_VALIDITY_INVALID_NO_REQUEST",
    "HELD": "REQUEST_MEMBER_STATUS_NOT_CURRENT_NO_REQUEST",
    "INDETERMINATE": "REQUEST_MEMBER_STATUS_NOT_CURRENT_NO_REQUEST",
    "REVOKED": "REQUEST_MEMBER_STATUS_NOT_CURRENT_NO_REQUEST"
  },
  "resource_count_rule": "STABLE_SEMANTIC_OWNER_LEDGER_V1_WRAPPER_ALIASES_ARE_NOT_SLOTS_CROSS_MEMBER_OR_STAGE_OCCURRENCES_NEVER_DEDUP_BY_OBJECT_DIGEST_OR_BYTES",
  "resource_limits": {
    "aggregate_raw_bytes_max": 512524288,
    "aggregate_supplied_png_bytes_max": 268435456,
    "human_action_record_bytes_max": 262144,
    "human_basis_characters_max": 1000,
    "human_identity_record_bytes_max": 16384,
    "members_max": 4,
    "png_bytes_max_per_member": 67108864,
    "raw_byte_leaf_occurrences_max": 1780,
    "raw_retained_document_bytes_max": 262144,
    "semantic_capsules_max_per_operation": 31,
    "set_owned_formal_document_bytes_max": 262144,
    "set_owned_generic_container_items_max": 64,
    "set_owned_nesting_depth_max": 16,
    "status_chain_inputs_max_per_closure": 32,
    "status_observation_document_bytes_max_per_closure": 8388608,
    "status_observation_document_occurrences_max_per_closure": 64
  },
  "reviewer_rule": {
    "future_role_auto_expansion": false,
    "retained_identity_claim": "RECORD_SEPARATION_ONLY_NOT_IDENTITY_AUTHENTICATION",
    "set_checker_must_differ_from": [
      "SET_MAKER_SELECTOR",
      "QUALIFICATION_QUALIFIER",
      "MANIFEST_CHECKER",
      "PROMOTION_REQUEST_STATUS_CHECKER",
      "PROMOTION_FINAL_STATUS_CHECKER",
      "PROMOTION_CHECKER",
      "ROLE_BINDING_CHECKER",
      "ROLE_BINDING_REQUEST_STATUS_CHECKER",
      "ROLE_BINDING_FINAL_STATUS_CHECKER",
      "SET_REQUEST_STATUS_CHECKER",
      "SET_FINAL_STATUS_CHECKER"
    ],
    "set_maker_selector_may_equal_exactly": [
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
      "ROLE_BINDING_FINAL_STATUS_CHECKER",
      "ROLE_BINDING_MAKER",
      "ROLE_BINDING_CHECKER",
      "SET_REQUEST_STATUS_PREPARER",
      "SET_REQUEST_STATUS_CHECKER",
      "SET_FINAL_STATUS_PREPARER",
      "SET_FINAL_STATUS_CHECKER"
    ],
    "status_reuse_rule": "CROSS_MEMBER_AND_REQUEST_FINAL_REUSE_ALLOWED_ONLY_WHEN_UPSTREAM_RULES_ALLOW_AND_SET_CHECKER_REMAINS_DISTINCT"
  },
  "rights_rule": "PER_MEMBER_EXACT_SCOPE_RETAINED_ALL_SCOPES_FIELD_EQUAL_NO_UNION_INTERSECTION_RENEWAL_OR_GRANT",
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
  "selection_rule": "EXPLICIT_HUMAN_SET_MAKER_SELECTOR_CANONICAL_TUPLE_NO_DISCOVERY_INFERENCE_SORTING_REPAIR_LATEST_OR_BEST",
  "semantic_capsule_ledger": {
    "common_order": [
      "C01_REQUEST_PRIMARY_BIBLE",
      "C02_REQUEST_PRIMARY_ASSET_VERSION",
      "C03_SET_MAKER_IDENTITY",
      "C04_SET_MAKER_ACTION",
      "C05_SET_REQUEST",
      "C06_FINAL_PRIMARY_BIBLE",
      "C07_FINAL_PRIMARY_ASSET_VERSION",
      "C08_SET_CHECKER_IDENTITY",
      "C09_SET_CHECKER_ACTION",
      "C10_EXPECTED_SET_DECISION",
      "C11_EXPECTED_POSITIVE_SET"
    ],
    "finalization_build_count_max": 29,
    "member_order": [
      "M01_COMPLETE_PROMOTION_CLOSURE",
      "M02_COMPLETE_ROLE_BINDING_CLOSURE_EXCLUDING_OWNED_M01",
      "M03_EXACT_WHOLE_PNG_OCCURRENCE",
      "M04_SET_REQUEST_STATUS_CLOSURE",
      "M05_SET_FINAL_STATUS_CLOSURE"
    ],
    "negative_finalization_verifier_count_max": 30,
    "positive_finalization_verifier_count_max": 31,
    "request_build_count_max": 20,
    "request_verifier_count_max": 21,
    "version": 1
  },
  "semantic_capsule_rule": "COUNT_BY_FROZEN_SEMANTIC_OWNERSHIP_NOT_WRAPPER_OR_ARGUMENT_PROMOTION_OWNED_ONCE_IN_M01_PNG_ALIAS_OWNED_ONCE_IN_M03",
  "set_rule": "IMMUTABLE_APPEND_ONLY_HISTORICAL_BOUNDED_SUPPLIED_SELECTION_NOT_ACTIVE_SET",
  "time_rule": {
    "final_equalities": "CHECKER_REVIEWED_AT_EQUALS_DECISION_AT_EQUALS_SET_AT_EQUALS_EVERY_FINAL_RECEIPT_AS_OF",
    "member_preexistence": "EVERY_MEMBER_BINDING_AT_LE_REQUESTED_AT",
    "request_equalities": "MAKER_PREPARED_AT_EQUALS_REQUESTED_AT_EQUALS_EVERY_REQUEST_RECEIPT_AS_OF",
    "request_valid_until": "MIN_REQUESTED_AT_PLUS_86400_AND_EVERY_QUALIFICATION_MANIFEST_REQUEST_STATUS_EXCLUSIVE_BOUND",
    "set_evidence_valid_until": "MIN_EVERY_QUALIFICATION_MANIFEST_FINAL_STATUS_EXCLUSIVE_BOUND",
    "upper_bound_rule": "REQUESTED_AT_AND_SET_AT_STRICTLY_BEFORE_EVERY_APPLICABLE_HALF_OPEN_UPPER_BOUND"
  },
  "upstream_call_allowlist": {
    "sdc.generated_reference_asset_promotion": [
      "build_generated_reference_promotion_primary_asset_binding",
      "generated_reference_promotion_primary_asset_binding_sha256"
    ],
    "sdc.generated_reference_rights_current_status": [
      "build_generated_reference_current_status_subject_closure",
      "generated_reference_contract_document_bytes",
      "process_generated_reference_current_status_record_as_of_assessment",
      "verify_generated_reference_current_status_evidence_record",
      "verify_generated_reference_current_status_record_as_of_assessment_receipt"
    ],
    "sdc.generated_reference_role_binding": [
      "GeneratedReferenceRoleBindingAdmittedPng",
      "creative_sample_generated_reference_eligible_asset_role_binding_decision_sha256",
      "creative_sample_generated_reference_eligible_asset_role_binding_request_sha256",
      "creative_sample_generated_reference_eligible_asset_role_binding_sha256",
      "generated_reference_role_binding_contract_document_bytes",
      "generated_reference_role_binding_target_sha256",
      "verify_generated_reference_eligible_asset_role_binding_finalization",
      "verify_generated_reference_eligible_asset_role_binding_request"
    ]
  },
  "upstream_role_binding_error_code_rule": "ONLY_EXACT_TYPED_GENERATED_REFERENCE_ROLE_BINDING_ERROR_CODE_EQUALITY_NO_MESSAGE_PARSE_PNG_ADMISSION_INVALID_MAPS_RAW_MEDIA_MISMATCH_EACH_OTHER_FROZEN_RELEASED_CODE_MAPS_ROLE_BINDING_FINALIZATION_INVALID_UNKNOWN_OR_FUTURE_CODE_IS_COMPATIBILITY_STOP_MODULE_BUG",
  "upstream_typed_cause_rules": [
    {
      "call_site": "ADR_046_REQUEST_OR_FINALIZATION_VERIFIER",
      "set_code": "RAW_MEDIA_MISMATCH",
      "upstream_codes": [
        "PNG_ADMISSION_INVALID"
      ],
      "upstream_types": [
        "GeneratedReferenceRoleBindingError"
      ]
    },
    {
      "call_site": "ADR_046_REQUEST_OR_FINALIZATION_VERIFIER",
      "set_code": "ROLE_BINDING_FINALIZATION_INVALID",
      "upstream_codes": [
        "INPUT_RESOURCE_LIMIT_EXCEEDED",
        "INPUT_DOCUMENT_INVALID",
        "CONTRACT_FIELD_INVALID",
        "POLICY_IDENTITY_MISMATCH",
        "FORMAL_IDENTITY_MISMATCH",
        "UPSTREAM_CLOSURE_MISMATCH",
        "PROMOTION_CLOSURE_INVALID",
        "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
        "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
        "CURRENT_STATUS_REPLAY_INVALID",
        "RIGHTS_SCOPE_MISMATCH",
        "ROLE_SEPARATION_VIOLATION",
        "ACTION_RECORD_INVALID",
        "TIME_OR_VALIDITY_INVALID",
        "AUTHORITY_SURFACE_NONZERO",
        "PROHIBITED_BOUNDARY_CONNECTION",
        "BINDING_GATE_NOT_PASS",
        "ATOMIC_OUTPUT_INVARIANT_VIOLATION"
      ],
      "upstream_types": [
        "GeneratedReferenceRoleBindingError"
      ]
    },
    {
      "call_site": "ADR_046_REQUEST_OR_FINALIZATION_VERIFIER",
      "set_code": "ROLE_BINDING_FINALIZATION_INVALID",
      "upstream_types": [
        "GeneratedReferenceAsOfAssessmentError",
        "GeneratedReferenceChainCoverageError",
        "GeneratedReferenceChainReplayError",
        "GeneratedReferenceJointReplayError",
        "GeneratedReferenceReceiptError",
        "GeneratedReferenceRightsCurrentStatusError"
      ]
    },
    {
      "call_site": "ADR_046_REQUEST_OR_FINALIZATION_VERIFIER",
      "set_code": "UPSTREAM_CLOSURE_MISMATCH",
      "upstream_types": [
        "GeneratedReferenceAssetPromotionError"
      ]
    },
    {
      "call_site": "ADR_046_SHA_OR_DOCUMENT_BYTE_REVALIDATION",
      "set_code": "ROLE_BINDING_FINALIZATION_INVALID",
      "upstream_types": [
        "GeneratedReferenceRoleBindingError"
      ]
    },
    {
      "call_site": "IN_MEMORY_ADMITTED_PNG_CONSTRUCTION_OR_WHOLE_PNG_COMPARISON",
      "set_code": "RAW_MEDIA_MISMATCH",
      "upstream_types": [
        "GeneratedReferenceRoleBindingError"
      ]
    },
    {
      "call_site": "SET_REQUEST_OR_FINAL_FRESH_STATUS_BUILD_PROCESS_VERIFY_OR_DOCUMENT_BYTE_EQUALITY",
      "set_code": "CURRENT_STATUS_REPLAY_INVALID",
      "upstream_types": [
        "GeneratedReferenceAsOfAssessmentError",
        "GeneratedReferenceChainCoverageError",
        "GeneratedReferenceChainReplayError",
        "GeneratedReferenceJointReplayError",
        "GeneratedReferenceReceiptError",
        "GeneratedReferenceRightsCurrentStatusError"
      ]
    },
    {
      "call_site": "COMMON_PRIMARY_BINDING_REBUILD_OR_HASH",
      "set_code": "PRIMARY_BINDING_INVALID",
      "upstream_types": [
        "GeneratedReferenceAssetPromotionError"
      ]
    }
  ],
  "upstream_typed_cause_target_groups": {
    "ADR_046_REQUEST_OR_FINALIZATION_VERIFIER": [
      "verify_generated_reference_eligible_asset_role_binding_finalization",
      "verify_generated_reference_eligible_asset_role_binding_request"
    ],
    "ADR_046_SHA_OR_DOCUMENT_BYTE_REVALIDATION": [
      "creative_sample_generated_reference_eligible_asset_role_binding_decision_sha256",
      "creative_sample_generated_reference_eligible_asset_role_binding_request_sha256",
      "creative_sample_generated_reference_eligible_asset_role_binding_sha256",
      "generated_reference_role_binding_contract_document_bytes",
      "generated_reference_role_binding_target_sha256"
    ],
    "COMMON_PRIMARY_BINDING_REBUILD_OR_HASH": [
      "build_generated_reference_promotion_primary_asset_binding",
      "generated_reference_promotion_primary_asset_binding_sha256"
    ],
    "IN_MEMORY_ADMITTED_PNG_CONSTRUCTION_OR_WHOLE_PNG_COMPARISON": [
      "GeneratedReferenceRoleBindingAdmittedPng"
    ],
    "SET_REQUEST_OR_FINAL_FRESH_STATUS_BUILD_PROCESS_VERIFY_OR_DOCUMENT_BYTE_EQUALITY": [
      "build_generated_reference_current_status_subject_closure",
      "generated_reference_contract_document_bytes",
      "process_generated_reference_current_status_record_as_of_assessment",
      "verify_generated_reference_current_status_evidence_record",
      "verify_generated_reference_current_status_record_as_of_assessment_receipt"
    ]
  },
  "zero_authority_rule": "ALL_PROVIDER_RUNTIME_ASSET_USE_PUBLICATION_RETENTION_TRAINING_AUTHORITY_FALSE_OR_ZERO",
  "zero_authority_surface": [
    "authority_scope=THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY",
    "current_gate=HUMAN_GATE",
    "provider_state=NOT_AUTHORIZED",
    "generation_authorized=false",
    "execution_authorized=false",
    "publication_authorized=false",
    "remote_processing_allowed=false",
    "retention_allowed=false",
    "training_allowed=false",
    "publication_allowed=false",
    "automated_execution_allowed=false",
    "authorized_attempts=0",
    "authorized_cost_cny=0",
    "posts_allowed=0",
    "provider_requests=0",
    "grants_rights=false",
    "grants_qualification=false",
    "grants_execution_authority=false",
    "eligible_for_asset_promotion=false",
    "replaces_rights_manifest=false",
    "usage_restriction=MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION",
    "provider_input_requested=false",
    "provider_input_eligible=false",
    "input_material_created=false",
    "provider_slot_embedded=false",
    "provider_order_asserted=false",
    "provider_request_created=false",
    "role_binding_exclusivity_asserted=false",
    "complete_role_set_asserted=false",
    "global_role_uniqueness_asserted=false",
    "present_currentness_asserted=false",
    "current_set_asserted=false",
    "supersedes_role_binding_set=false"
  ]
}
```

The canonical compact encoding of the exact JSON object above has the byte count and raw SHA-256
recorded below. This acceptance freezes that exact policy identity. The policy digest cannot be
invented during BUILD or derived from a runtime serializer.

```text
policy_document_bytes=38481
policy_document_sha256=77bdbb2f8845af02ab72e70ad1c74276e218f27410ff4384547d3868ec1a8c9e
```

The policy ID remains
`sdc.generated-reference-bounded-supplied-role-binding-set-policy`; the accepted version is exactly
`1.1.0`. Accepted R1's historical identity remains `1.0.0`, 28,797 compact bytes and
`7b22f26df2a6ab31ee45e8a10dc83c56e22a065d87ee099ef3e678d72511f1d6`; it is not silently
relabelled. A Request, Decision or Set carrying the R1 version or digest would fail the R2 exact
policy-identity gate.

## Gate derivation and result mapping

Request construction would use this exact structural admission order and would retain no gate-result
tuple when admission failed:

```text
0 EXACT_POSITIVE_ATOMIC_BINDING_CLOSURES
1 COMMON_ARTIFACT_SUBJECT_PURPOSE_PROFILE_AND_CATALOG_EXACT
2 CANONICAL_REQUESTED_ROLE_SUBSET_AND_COVERAGE_EXACT
3 ONE_DISTINCT_BINDING_PER_REQUESTED_ROLE
4 EXACT_CANDIDATE_OCCURRENCES_AND_RAW_WHOLE_MEDIA
5 POSITIVE_UNEXPIRED_QUALIFICATIONS_AND_VALID_MANIFESTS
6 EVERY_MEMBER_CURRENT_STATUS_AT_REQUEST
7 COMMON_PRIMARY_BINDING_EXACT_AT_REQUEST
8 PER_MEMBER_RIGHTS_SCOPES_UNCHANGED_AND_COMMON
9 SET_MAKER_SELECTOR_ACTION_AND_IDENTITY_VALID
```

Every Request-time status must be `CURRENT`; its Receipt `as_of` and the rebuilt common primary
binding must satisfy the exact Request fields. Valid `REVOKED`/`HELD`/`INDETERMINATE` would be
`REQUEST_MEMBER_STATUS_NOT_CURRENT`; `EXPIRED` would be `TIME_OR_VALIDITY_INVALID`; malformed replay
would be `CURRENT_STATUS_REPLAY_INVALID`. An invalid Maker/Selector action or any other admission
mismatch would likewise create no Request under its exact first-failure code.

Finalization would use this exact 13-value gate order:

```text
0 EXACT_POSITIVE_ATOMIC_BINDING_CLOSURES
1 COMMON_ARTIFACT_SUBJECT_PURPOSE_PROFILE_AND_CATALOG_EXACT
2 CANONICAL_REQUESTED_ROLE_SUBSET_AND_COVERAGE_EXACT
3 ONE_DISTINCT_BINDING_PER_REQUESTED_ROLE
4 EXACT_CANDIDATE_OCCURRENCES_AND_RAW_WHOLE_MEDIA
5 POSITIVE_UNEXPIRED_QUALIFICATIONS_AND_VALID_MANIFESTS
6 EVERY_MEMBER_CURRENT_STATUS_AT_SET
7 COMMON_PRIMARY_BINDING_EXACT
8 PER_MEMBER_RIGHTS_SCOPES_UNCHANGED_AND_COMMON
9 HUMAN_PER_MEMBER_RIGHTS_SCOPES_AND_EXACT_MEMBER_TUPLE_PRESENTED_WITHOUT_AGGREGATION_ACKNOWLEDGED
10 HUMAN_EXPLICIT_SELECTION_ORDER_AND_COVERAGE_ACKNOWLEDGED
11 HUMAN_NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_ACKNOWLEDGED
12 SET_REVIEWER_SEPARATION
```

The exact compiler basis literals and sources, in the same order, would be:

```text
0  PASS-only  COMPILER_REVALIDATED_POSITIVE_ATOMIC_BINDING_CLOSURES
1  PASS-only  COMPILER_REVALIDATED_COMMON_ARTIFACT_SUBJECT_PURPOSE_PROFILE_CATALOG
2  PASS-only  COMPILER_REVALIDATED_CANONICAL_REQUESTED_ROLE_SUBSET_AND_COVERAGE
3  PASS-only  COMPILER_REVALIDATED_DISTINCT_BINDING_PER_REQUESTED_ROLE
4  PASS-only  COMPILER_REVALIDATED_EXACT_CANDIDATE_OCCURRENCES_AND_WHOLE_MEDIA
5  PASS-only  COMPILER_REVALIDATED_UNEXPIRED_QUALIFICATIONS_AND_VALID_MANIFESTS
6  status aggregation  COMPILER_REPLAYED_EVERY_MEMBER_STATUS_AT_SET
7  primary-binding comparison  COMPILER_REVALIDATED_FINAL_COMMON_PRIMARY_BINDING
8  PASS-only  COMPILER_REVALIDATED_COMMON_UNCHANGED_PER_MEMBER_RIGHTS_SCOPES
9  Checker rights_presentation_result + rights_presentation_basis
10 Checker selection_order_coverage_result + selection_order_coverage_basis
11 Checker non_exclusive_no_provider_boundary_result + non_exclusive_no_provider_boundary_basis
12 PASS-only  COMPILER_REVALIDATED_SET_REVIEWER_SEPARATION
```

For gate 6, any final member `REVOKED` or `HELD` would produce `FAIL`; otherwise any
`INDETERMINATE` would produce `INDETERMINATE`; otherwise all members are `CURRENT` and the result
would be `PASS`. `EXPIRED` is the structural no-Decision case already defined above. Gate 7 would be
`PASS` only for exact final common-primary equality and `FAIL` for one otherwise valid active binding
drift. Gates 0 through 5, 8 and 12 could exist only as `PASS` after structural admission. Their basis
literals above would be invariant across member count, IDs, digests and time.

The three human primitive result/basis pairs would have one source only: the exact canonical Checker
action fields named above. No same-named function argument, `decision_basis`, Request basis or other
text could override them. The implementation would derive gates 9 through 11 from those primitive
pairs, derive the complete gate tuple/issues/Decision, require the copies carried inside the Checker
action to be exact-equal, then hash that action and build the Decision. This derivation order is not
an identity cycle.

Gates 0 through 5 and gate 8 would be compiler-derived pass-only gates after structural
reconstruction. Because `set_at < request_valid_until` and that bound already includes every
Qualification and Manifest deadline, an expired Qualification or Manifest would be
`TIME_OR_VALIDITY_INVALID` with no Decision rather than a reachable negative issue. Gate 6 would map
final `CURRENT` to `PASS`, `REVOKED/HELD` to `FAIL` and `INDETERMINATE` to `INDETERMINATE`.
`EXPIRED` cannot be a valid gate result under the frozen final half-open bounds; it would instead be
`TIME_OR_VALIDITY_INVALID` with no Decision and no issue. A malformed or copied Receipt remains
`CURRENT_STATUS_REPLAY_INVALID`. Gate 7 would map one valid common-primary drift to `FAIL`. Gates 9
through 11 would equal the Checker action's three human result/basis pairs. Gate 12 would be
compiler-derived and pass-only after exact identity comparison.

Only a `FAIL` at a mapped gate would add one issue. `INDETERMINATE` would affect the Decision but
would not add a FAIL issue. The exact issue order is:

```text
MEMBER_STATUS_NOT_CURRENT_AT_SET
COMMON_PRIMARY_BINDING_NO_LONGER_ACTIVE
PER_MEMBER_RIGHTS_PRESENTATION_NOT_ACKNOWLEDGED
EXPLICIT_SELECTION_ORDER_AND_COVERAGE_NOT_ACKNOWLEDGED
NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_NOT_ACKNOWLEDGED
```

Mapping would be deterministic:

```text
malformed, incomplete, noncanonical or linkage/replay failure
  -> operation failure; no formal Request, Decision or Set

valid Request-time REVOKED, HELD or INDETERMINATE member
  -> REQUEST_MEMBER_STATUS_NOT_CURRENT; no Request

Request-time or final EXPIRED under an applicable strict upper bound
  -> TIME_OR_VALIDITY_INVALID; no Request or Decision

any valid final deterministic FAIL or human FAIL
  -> REJECT_BOUNDED_SUPPLIED_ROLE_BINDING_SET; Decision only

no FAIL and at least one valid INDETERMINATE
  -> INDETERMINATE_BOUNDED_SUPPLIED_ROLE_BINDING_SET; Decision only

all gates PASS and issue tuple empty
  -> APPROVE_BOUNDED_SUPPLIED_ROLE_BINDING_SET; positive Decision and Set atomically
```

`FAIL` would take priority over `INDETERMINATE`. Missing evidence, an omitted branch, a duplicate,
reorder, common-frame mismatch or failed reconstruction could never be downgraded to a human
indeterminate outcome. The issue tuple would contain `0..5` values in the exact order above and no
duplicate.

## Future Role-Binding Set Contract family

Only under a separately authorized future BUILD would R2 add exactly these top-level models in this
exact Registry order:

```text
89 CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetRequestV1
90 CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetDecisionV1
91 CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetV1
```

The Registry would increase from 89 to 92. Target, member, per-member replay and gate-result helpers
would remain inline Schema definitions and would not enter `sdc.schemas.MODELS`.

### Future Set Request

The exact Set review-payload projection, before Maker/Selector fields exist, would contain exactly in
this order:

```text
policy_id
policy_version
policy_document_sha256
requested_set_target
requested_primary_asset_binding
requested_member_replays
requested_at
request_valid_until
explicit_human_member_selection=true
canonical_member_order_verified=true
requested_role_coverage_verified=true
automatic_member_discovery_performed=false
role_binding_set_performed=false
set_materialized=false
complete Set-specific and shared zero-authority surface in its frozen order
```

`CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetRequestV1` would have exactly these
required fields in semantic projection order:

```text
schema_version=1.0.0
document_type=sdc.creative-sample-generated-reference-eligible-asset-role-binding-set-request-v1
request_scope=GENERATED_REFERENCE_ELIGIBLE_ASSET_BOUNDED_SUPPLIED_ROLE_BINDING_SET_REQUEST_ONLY
request_id: PortableId
request_sha256: LowerSha256
policy_id=sdc.generated-reference-bounded-supplied-role-binding-set-policy
policy_version=1.1.0
policy_document_sha256: exact frozen policy LowerSha256
set_review_payload_sha256: LowerSha256
requested_set_target: GeneratedReferenceEligibleAssetRoleBindingSetTargetV1
requested_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
requested_member_replays: tuple[GeneratedReferenceRoleBindingSetMemberReplayV1, 1..4]
maker_identity_ref_sha256: raw LowerSha256
maker_action_sha256: raw LowerSha256
maker_prepared_at: canonical UTC seconds
requested_at: canonical UTC seconds
request_valid_until: canonical UTC seconds
request_basis: HumanBasis(1..1000)
explicit_human_member_selection=true
canonical_member_order_verified=true
requested_role_coverage_verified=true
automatic_member_discovery_performed=false
role_binding_set_performed=false
set_materialized=false
status=GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_SET_REQUESTED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete Set-specific and shared zero-authority surface in its frozen order
```

Every requested replay would use `SET_REQUEST_ENTRY`, have status `CURRENT`, use
`as_of == requested_at`, and match the target member at the same ordinal. The requested primary
binding would equal the target common binding. `maker_prepared_at == requested_at`; the exact Maker
action and Request basis would match field-for-field.

### Future Set Decision

`CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetDecisionV1` would have exactly these
required fields in semantic projection order:

```text
schema_version=1.0.0
document_type=sdc.creative-sample-generated-reference-eligible-asset-role-binding-set-decision-v1
decision_scope=GENERATED_REFERENCE_ELIGIBLE_ASSET_BOUNDED_SUPPLIED_ROLE_BINDING_SET_DECISION_ONLY
decision_id: PortableId
decision_sha256: LowerSha256
policy_id=sdc.generated-reference-bounded-supplied-role-binding-set-policy
policy_version=1.1.0
policy_document_sha256: exact frozen policy LowerSha256
set_review_payload_sha256: LowerSha256
request_id: PortableId
request_sha256: LowerSha256
requested_set_target: GeneratedReferenceEligibleAssetRoleBindingSetTargetV1
requested_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
final_primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
final_member_replays: tuple[GeneratedReferenceRoleBindingSetMemberReplayV1, 1..4]
checker_identity_ref_sha256: raw LowerSha256
checker_action_sha256: raw LowerSha256
checker_reviewed_at: canonical UTC seconds
decision_at: canonical UTC seconds
set_at: canonical UTC seconds
gate_results: tuple[GeneratedReferenceRoleBindingSetGateResultV1, exactly 13]
set_issue_codes: tuple[SetIssueCode, 0..5]
decision_basis: HumanBasis(1..1000)
decision: SetDecision
set_materialization_allowed: bool
set_review_performed=true
set_id_embedded=false
status=GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_SET_DECISION_RECORDED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete Set-specific and shared zero-authority surface in its frozen order
```

Every final replay would use `SET_FINALIZATION`, match its target member ordinal and have
`as_of == set_at`. The Checker fields would satisfy the exact action record. Gate/issue/decision and
materialization values would be independently recomputed; caller values could not override them.

### Future positive Set

`CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetV1` would have exactly these required
fields in semantic projection order:

```text
schema_version=1.0.0
document_type=sdc.creative-sample-generated-reference-eligible-asset-role-binding-set-v1
set_scope=POST_ROLE_BINDING_BOUNDED_SUPPLIED_SET_HISTORICAL_EVIDENCE_ONLY
set_id: PortableId
set_sha256: LowerSha256
policy_id=sdc.generated-reference-bounded-supplied-role-binding-set-policy
policy_version=1.1.0
policy_document_sha256: exact frozen policy LowerSha256
request_id: PortableId
request_sha256: LowerSha256
decision_id: PortableId
decision_sha256: LowerSha256
role_binding_set_target: GeneratedReferenceEligibleAssetRoleBindingSetTargetV1
primary_asset_binding: GeneratedReferencePromotionPrimaryAssetBindingV1
final_member_replays: tuple[GeneratedReferenceRoleBindingSetMemberReplayV1, 1..4]
set_at: canonical UTC seconds
set_evidence_valid_until: canonical UTC seconds
set_state=GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_SET_RECORDED
role_binding_set_performed=true
explicit_requested_role_subset_satisfied=true
role_coverage: EXPLICIT_PARTIAL_PURPOSE_ROLE_SUBSET | EXACT_FULL_PURPOSE_ROLE_TUPLE
member_count: int, Character 1..3 | Scene 1..4
whole_composite_media_members_bound=true
status=GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_SET_RECORDED
evidence_scope=EXPLICIT_FINITE_BOUND_SET_ONLY
complete Set-specific and shared zero-authority surface in its frozen order
```

All final replay statuses would be `CURRENT`; `primary_asset_binding` would equal the target common,
requested and final binding; `role_coverage` and `member_count` would equal the target. The Set would
contain no media locator, Provider slot/order, upload reference, request fingerprint or idempotency
value.

A negative or indeterminate Decision would have no Set identity, no placeholder Set and no materialized
member tuple outside its reviewed target. Positive Decision and Set construction, complete
revalidation and return would be atomic. Every top-level field is required; no field has a semantic
default. The only projection exclusions would be `request_id/request_sha256` from the Request's own
projection, `decision_id/decision_sha256` from the Decision's own projection and
`set_id/set_sha256` from the Set's own projection. Every other field, including every ordered nested
field and false/zero authority value, would enter identity.

## Exact member and cross-document linkage matrix

Every future constructor and verifier would receive the complete predecessor values and enforce this
closed matrix. ID/digest-only values could not satisfy a row.

| Destination | Exact required linkage |
| --- | --- |
| Target member from Binding closure | Every member anchor equals the fully reverified exact positive Role-Binding Request/Decision/Binding and its Outcome/Candidate/Sidecar/raw-PNG closure. Ordinal and role equal the requested-role tuple position. |
| Common target frame | Artifact/Profile/Catalog/subject/purpose/full role tuple/primary binding are field-for-field equal across all members. Reviewed Rights scopes are field-for-field equal while each Manifest identity remains explicit. |
| Request from review payload | Policy, target, ordered members, coverage, per-member Request replay anchors, common primary binding, time and zero-authority fields reproduce the payload exactly. Request adds only identity, admitted Maker identity/action, bounded basis and Request state. |
| Request from Maker action | Actor identity, target SHA, ordered member Binding SHAs, requested roles, coverage, common primary-binding SHA, ordered Request Receipt SHAs, prepared time and basis equal the Request exactly. |
| Request status from ADR-046 final Records | Every member preserves exact Candidate/Qualification/Manifest/status subject and covers every prior target and branch through complete same-target/successor/reconciliation closure. |
| Decision from Request | Policy, Request, target, members, common frame, Rights anchors, requested primary binding and immutable request values equal exactly. |
| Decision final evidence | Every final replay covers its exact member's Request Record; every final Receipt `as_of` equals common `set_at`; the rebuilt final primary binding is common and exact. |
| Decision from Checker action | Actor identity, Request, target, ordered members, final Receipts, final primary binding, human results, gates, issues, decision, materialization boolean, time and basis equal exactly. |
| Positive Set from Decision | All policy, Request, positive Decision, target/member/common-frame/Rights/final-status/time and false-authority fields equal exactly; only `set_evidence_valid_until` is newly derived. |

Any copied-field mismatch, member removal, replacement, reorder, cross-member replay substitution or
failure to reconstruct one predecessor would fail before positive output.

## Complete zero-authority surface

Every future top-level Contract would directly carry the existing required zero-authority surface:

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

Set-specific top-level values would additionally require:

```text
provider_input_requested=false
provider_input_eligible=false
input_material_created=false
provider_slot_embedded=false
provider_order_asserted=false
provider_request_created=false
role_binding_exclusivity_asserted=false
complete_role_set_asserted=false
global_role_uniqueness_asserted=false
present_currentness_asserted=false
current_set_asserted=false
supersedes_role_binding_set=false
```

Every value would be required and enter the corresponding semantic projection. A positive Set or
FULL coverage literal could not override them. The 21 shared fields followed by the 12 Set-specific
fields, in the exact displayed order, form the `complete Set-specific and shared zero-authority surface`
suffix referenced by every top-level field map and the review-payload projection. No field would be
inherited only as an omitted default.

## Provider-input, Runtime, Compiler and persistence isolation

A conforming future Set module must not import, call, construct, validate as or modify:

- `InputMaterial`, `ProviderRequest`, Provider profiles or Provider authorization values;
- Provider slots, locators, URLs, uploads, media references, request fingerprints or idempotency;
- Runtime, Worker, Temporal, PostgreSQL, persistence rows, migrations or events;
- Provider selection, submit, inspect, download, cancel or Retry;
- network, credentials, environment capability discovery, cost reservation or paid service;
- current Compiler entrypoints, Storyboard, NIR, PIR, Compilation, JobGraph or AssemblyPlan;
- AssetVersion or Bible mutation paths;
- QC automation, publication, posting, release, retention/deletion automation or training controls;
  or
- filesystem/database discovery, current/latest lookup, ranking, migration or backfill.

Current Compiler, Provider, Runtime, Worker, QC and persistence modules must not import the future
Set module. The Set module could import and exact-type revalidate only the released pure upstream
role-binding/evidence modules needed for complete supplied reconstruction.

The future core Set module's repository-local import allowlist would be exactly the following
released public symbols, and no module-level wildcard, `__all__` expansion or public-name discovery
would enlarge it:

```text
sdc.contracts:
  CharacterAssetVersion
  CharacterBible
  SceneAssetVersion
  SceneBible
sdc.generated_reference_asset_promotion:
  GeneratedReferenceAssetPromotionError
  GeneratedReferenceAssetPromotionStatusClosureInput
  GeneratedReferencePromotionPrimaryAssetBindingV1
  build_generated_reference_promotion_primary_asset_binding
  generated_reference_promotion_primary_asset_binding_sha256
sdc.generated_reference_rights_current_status:
  CreativeSampleGeneratedReferenceCurrentStatusDecisionV1
  CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1
  CreativeSampleGeneratedReferenceCurrentStatusInstructionV1
  CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1
  CreativeSampleGeneratedReferenceCurrentStatusRequestV1
  CreativeSampleGeneratedReferenceRightsManifestV1
  GeneratedReferenceAsOfAssessmentError
  GeneratedReferenceChainCoverageError
  GeneratedReferenceChainReplayError
  GeneratedReferenceCurrentStatusExplicitChainInput
  GeneratedReferenceCurrentStatusSubjectClosureV1
  GeneratedReferenceJointReplayError
  GeneratedReferenceReceiptError
  GeneratedReferenceReviewedRightsScopeV1
  GeneratedReferenceRightsCurrentStatusError
  build_generated_reference_current_status_subject_closure
  generated_reference_contract_document_bytes
  process_generated_reference_current_status_record_as_of_assessment
  verify_generated_reference_current_status_evidence_record
  verify_generated_reference_current_status_record_as_of_assessment_receipt
sdc.generated_reference_role_binding:
  CHARACTER_REFERENCE_ROLE_ORDER
  CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1
  CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1
  CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1
  GeneratedReferenceEligibleAssetRoleBindingTargetV1
  GeneratedReferenceRoleBindingAdmittedPng
  GeneratedReferenceRoleBindingError
  GeneratedReferenceRoleBindingFinalizationResult
  GeneratedReferenceRoleBindingPromotionClosureInput
  SCENE_REFERENCE_ROLE_ORDER
  creative_sample_generated_reference_eligible_asset_role_binding_decision_sha256
  creative_sample_generated_reference_eligible_asset_role_binding_request_sha256
  creative_sample_generated_reference_eligible_asset_role_binding_sha256
  generated_reference_role_binding_contract_document_bytes
  generated_reference_role_binding_target_sha256
  verify_generated_reference_eligible_asset_role_binding_finalization
  verify_generated_reference_eligible_asset_role_binding_request
```

The corresponding upstream call-target allowlist would be narrower than the import allowlist and
exactly:

```text
sdc.generated_reference_asset_promotion:
  build_generated_reference_promotion_primary_asset_binding
  generated_reference_promotion_primary_asset_binding_sha256
sdc.generated_reference_rights_current_status:
  build_generated_reference_current_status_subject_closure
  generated_reference_contract_document_bytes
  process_generated_reference_current_status_record_as_of_assessment
  verify_generated_reference_current_status_evidence_record
  verify_generated_reference_current_status_record_as_of_assessment_receipt
sdc.generated_reference_role_binding:
  GeneratedReferenceRoleBindingAdmittedPng
  creative_sample_generated_reference_eligible_asset_role_binding_decision_sha256
  creative_sample_generated_reference_eligible_asset_role_binding_request_sha256
  creative_sample_generated_reference_eligible_asset_role_binding_sha256
  generated_reference_role_binding_contract_document_bytes
  generated_reference_role_binding_target_sha256
  verify_generated_reference_eligible_asset_role_binding_finalization
  verify_generated_reference_eligible_asset_role_binding_request
```

No other `sdc` module or private underscore-prefixed upstream symbol would be imported by the core
module. The four `sdc.contracts` types are allowed only to rebuild and compare the existing imported
primary binding; `InputMaterial`, `ProviderRequest` and every Compiler/Job/Provider type remain
outside the allowlist. Under Accepted R2, the future Set codegen module could import the core Set
module, standard-library filesystem primitives solely for its fixed offline fixture check/update
workflow, and exactly the two public fixed-fixture support callables frozen below. It could import no
other symbol from either old codegen module.

The three allowlisted `build_*`/`process_*` callables are limited to deterministic in-memory
reconstruction of the already supplied primary binding, status subject closure and fresh as-of
status Receipt. They do not admit discovery or persistence and cannot create a Rights Manifest,
Promotion Request/Decision/Sidecar or Role-Binding Request/Decision/Binding. In particular, the core
module must not import or call `build_generated_reference_rights_manifest`,
`prepare_generated_reference_asset_promotion_request`,
`finalize_generated_reference_asset_promotion`,
`admit_generated_reference_role_binding_png`,
`build_generated_reference_eligible_asset_role_binding_target`, either Role-Binding review-payload
`build_*` helper, `prepare_generated_reference_eligible_asset_role_binding_request` or
`finalize_generated_reference_eligible_asset_role_binding`. Any future upstream public symbol is
denied unless a separately reviewed ADR revision adds its exact name and updates the frozen policy
identity.

All imported upstream Contract, process-input, result and error classes other than the exact
`GeneratedReferenceRoleBindingAdmittedPng` in-memory wrapper are annotation, exact-type-check,
exception-match or field-read surfaces only. The core must not call those classes or any upstream
class/instance `model_validate`, `model_validate_json`, `model_construct`, parse, copy, replace or
update surface. It must not use callable aliases, `getattr` or reflection to bypass the exact call
list. The admitted-PNG wrapper call must receive already supplied exact bytes and their supplied
anchors; the filesystem admission function remains denied.

Future AST/import tests would have to prove both directions: the core Set module imports only this
exact symbol-by-symbol allowlist, never resolves an upstream module or name dynamically, and existing
Compiler/Provider/Runtime/Worker/QC/persistence modules never import the Set module. The tests would
also assert that every allowlisted name in the three generated-reference modules still exists in
that module's released public `__all__`. Because `sdc.contracts` has no public `__all__`, its four
allowlisted classes would instead be asserted as exact direct top-level public attributes with the
same module/name identity. Every upstream call target must be in the narrower exact call allowlist,
and no denied class, constructor, validator, copy/update or helper could appear as a direct, aliased
or reflected call target. String indirection, aliasing a whole upstream module or dynamic import
could not satisfy the test.

No Binding or Set could validate as, convert to or be duck-typed as current `InputMaterial`. Set
canonical order would not be Provider order. Any later Provider Input Material V2 proposal would
need its own entry condition, exact Set replay, role-to-material mapping, byte-to-locator proof,
Provider slot/cardinality/order/duplicate rules, privacy/Rights handling, request fingerprint,
idempotency and independent Provider authorization.

## Canonical projections, IDs and digest domains

Semantic projections and retained identity/action records would use compact canonical JSON: UTF-8,
NFC strings and keys, lexicographic object-key order by Unicode code point, compact separators, JSON
arrays for tuples, no NaN/Infinity, no duplicate keys and no terminal LF.

Persistent formal Request, Decision and Set document bytes would use the existing ADR-045/046
formal codec: the same admitted JSON tree, lexicographic keys, UTF-8, `ensure_ascii=false`, two-space
indentation and exactly one terminal LF. Source semantic arrays would be validated in required order;
neither codec would sort or repair them.

Every projection would list exact keys explicitly. Generic `model_dump`, dataclass walking,
`__dict__`, reflection or reusable catch-all serialization could not define semantic identity.

The future implementation would reserve exactly these unique NUL-terminated semantic domains:

```text
sdc:generated-reference-bounded-supplied-role-binding-set-target:v1\0
sdc:generated-reference-bounded-supplied-role-binding-set-review-payload:v1\0
sdc:generated-reference-bounded-supplied-role-binding-set-request:v1\0
sdc:generated-reference-bounded-supplied-role-binding-set-decision:v1\0
sdc:generated-reference-bounded-supplied-role-binding-set:v1\0
```

Each semantic SHA-256 would hash its exact domain plus exact canonical projection. Each portable ID
would use its own type-specific stem plus the first 20 lowercase hex characters of the corresponding
full semantic digest. The exact stems would be:

```text
generated_reference_eligible_asset_role_binding_set_request_v1_
generated_reference_eligible_asset_role_binding_set_decision_v1_
generated_reference_eligible_asset_role_binding_set_v1_
```

A projection would exclude only its own self ID/SHA fields and include every other semantic field,
member ordinal and ordered nested projection.

Raw retained-record, formal-document and PNG SHA-256 values would remain exact undomained byte
hashes. Tests would have to prove both codecs, full-hash/short-ID agreement, every-field mutation,
self-field exclusion and cross-domain non-aliasing.

## Resource and privacy boundary

The Accepted R2 frozen policy projection above defines these exact limits:

```text
members per Set: Character 1..3; Scene 1..4
one exact whole PNG per member occurrence: 1..67,108,864 bytes
aggregate supplied member PNG bytes: <=268,435,456 bytes
one Set-owned Request/Decision/Set formal document: 1..262,144 bytes
one raw retained evidence/action/observation document leaf: 1..262,144 bytes
one retained human identity record: 1..16,384 bytes
one retained human action record: 1..262,144 bytes
one human basis: 1..1,000 Unicode scalar values
Set-owned generic bounded container: <=64 items
Set-owned JSON nesting depth: <=16
status chain inputs per status closure: <=32
status observation-document leaves per status closure: <=64
status observation-document bytes per status closure: <=8,388,608
semantic capsules per operation: <=31
explicit raw-byte leaves per operation: <=1,780
aggregate supplied raw bytes per operation: <=512,524,288
```

Opaque already-materialized upstream formal models would retain their released per-model/container
resource validation and have to pass their released high-level verifier. The Set core would not
serialize or remeasure those models for resource accounting, and it would make no claim that their
formal bytes fit the Set-owned 262,144-byte limit. The two exact allowlisted upstream document-byte
serializers would still be called where required for canonical value/byte equality; their outputs
would not enter the Set resource-byte ledger. This avoids additional deep serializer imports and
keeps historical upstream policy responsible for its own model resources.

Instead of wrapper- or function-argument slots, Accepted R2 would use this exact semantic-owner
capsule ledger:

```text
common owner order:
C01_REQUEST_PRIMARY_BIBLE
C02_REQUEST_PRIMARY_ASSET_VERSION
C03_SET_MAKER_IDENTITY
C04_SET_MAKER_ACTION
C05_SET_REQUEST
C06_FINAL_PRIMARY_BIBLE
C07_FINAL_PRIMARY_ASSET_VERSION
C08_SET_CHECKER_IDENTITY
C09_SET_CHECKER_ACTION
C10_EXPECTED_SET_DECISION
C11_EXPECTED_POSITIVE_SET

per-member owner order:
M01_COMPLETE_PROMOTION_CLOSURE
M02_COMPLETE_ROLE_BINDING_CLOSURE_EXCLUDING_OWNED_M01
M03_EXACT_WHOLE_PNG_OCCURRENCE
M04_SET_REQUEST_STATUS_CLOSURE
M05_SET_FINAL_STATUS_CLOSURE
```

Request construction would count `C01..C04 + each M01..M04`, at most 20 capsules. Request
verification would add `C05`, at most 21. Finalization would count `C01..C09 + each M01..M05`, at
most 29. Negative final verification would add `C10`, at most 30; positive final verification would
also add `C11`, at most 31. Wrapping one owner in another does not create a second capsule: embedded
Promotion belongs to `M01`, not `M02`, and aliased PNG paths belong to `M03`. Different owners,
members or status stages always count again even when Python object identity, digest or bytes are
equal.

`M03` would have one caller-supplied raw source only:
`member.role_binding_promotion_closure.upstream.png_bytes`. The Set core would construct
`GeneratedReferenceRoleBindingAdmittedPng` from that same exact bytes value and supplied anchors; no
second `png_bytes` parameter is allowed. A structural wrapper reference to the same exact field is
owned once. Two independently supplied buffers would be two physical raw-leaf occurrences even if
their content, digest and value equality matched, and would require a revised ledger rather than
deduplication. The same rule applies to retained JSON bytes.

Only raw `bytes` leaves reachable through closed explicit public field paths would be measured; no
`model_dump`, reflection, generic dataclass walk or dynamic name lookup is allowed. The
`raw_byte_leaf_path_owners` paths frozen in the policy projection are the exact future internal
process-input field names and extraction order. `STATUS_CLOSURE_RAW_LEAVES` expands only to its five
listed paths. Those names are not portable Contract fields or Registry models, but BUILD could not
rename, add or discover one without ADR revision. With those paths, the exact per-member raw-byte
ledger is:

```text
qualification evidence documents: exactly 10
Manifest evidence documents: exactly 9
Request path status stages: exactly 5 in order
  Promotion request, Promotion final, Role-Binding request, Role-Binding final, Set request
Final path status stages: exactly 6, adding Set final
each status stage: <=32 chain inputs; <=64 observation document leaves; <=8,388,608 observation bytes
Request path identities/actions per member: exactly 18 / 18
Final path identities/actions per member: exactly 20 / 20
```

The Request per-member non-PNG maximum would be
`19*262,144 + 18*16,384 + 18*262,144 + 5*8,388,608 = 51,937,280` bytes and 375
leaves. The final per-member maximum would be
`19*262,144 + 20*16,384 + 20*262,144 + 6*8,388,608 = 60,882,944` bytes and 443
leaves. Request common Maker identity/action would add two leaves and 278,528 bytes. Final common
Maker+Checker identity/action would add four leaves and 557,056 bytes.

At four members, Request non-PNG raw input would therefore be at most 1,502 leaves and 208,027,648
bytes; including four PNGs, 1,506 leaves and 476,463,104 bytes. Final non-PNG raw input would be at
most 1,776 leaves and 244,088,832 bytes; including four PNGs, 1,780 leaves and 512,524,288 bytes.
Every occurrence would contribute `len(bytes)` before decode or semantic verification. An upstream
wrapper field addition/rename, upstream policy-identity change or need for another raw leaf would be a
compatibility stop requiring ADR revision, not automatic traversal.

Portable Contracts would retain only bounded canonical IDs, digests, exact scopes, times and
privacy-minimized human-reference digests. They would contain no raw evidence document, raw PNG,
path, URL, credential, token, Provider payload, account identifier, unrestricted free-form metadata
or authenticated identity claim.

## Failure behavior and priority

The future module would expose one typed error family with stable machine-readable error codes.
Human-readable messages would not be compatibility interfaces. Accepted R2 retains exactly the
closed R1 21-code ordered tuple and no other public code. The Request-status code remains deliberate:
it separates a valid fail-closed non-current Request outcome from malformed replay.

```text
RESOURCE_LIMIT_EXCEEDED
CANONICAL_DOCUMENT_INVALID
PROHIBITED_BOUNDARY_CONNECTION
CONTRACT_FIELD_INVALID
TIME_OR_VALIDITY_INVALID
POLICY_IDENTITY_MISMATCH
UPSTREAM_CLOSURE_MISMATCH
ROLE_BINDING_FINALIZATION_INVALID
COMMON_FRAME_MISMATCH
DUPLICATE_ROLE_OR_BINDING
ROLE_SELECTION_INVALID
CANONICAL_ORDER_INVALID
RAW_MEDIA_MISMATCH
CURRENT_STATUS_REPLAY_INVALID
REQUEST_MEMBER_STATUS_NOT_CURRENT
PRIMARY_BINDING_INVALID
RIGHTS_SCOPE_MISMATCH
IDENTITY_RECORD_INVALID
ACTION_RECORD_INVALID
IDENTITY_SEPARATION_INVALID
DECISION_OR_SET_REVALIDATION_FAILED
```

That tuple is the exact first-failure priority only for Set-owned validation and direct allowlisted
call sites. It does not reorder a failure already selected inside either released ADR-046 Request or
finalization verifier. Each invocation of either exact verifier is one atomic delegated validation
stage and inherits ADR-046's released internal first-failure order. The closed portable condition
assignment is:

| Code | First applicable condition after exclusions |
| --- | --- |
| `RESOURCE_LIMIT_EXCEEDED` | Any frozen Set-owned document/container/depth, semantic-capsule, explicit raw-leaf, PNG, record, action, identity or basis byte/count limit fails; bounded raw-size checks precede decode |
| `CANONICAL_DOCUMENT_INVALID` | Bounded JSON document/retained-record bytes are not exact UTF-8/NFC/duplicate-free JSON with the required codec/LF rules, or differ from required canonical re-encoding; raw PNG bytes are excluded |
| `PROHIBITED_BOUNDARY_CONNECTION` | A zero-authority literal drifts or a prohibited type, field, locator, path, URL, Provider/Runtime/network/persistence import or call connection appears |
| `CONTRACT_FIELD_INVALID` | Exact type/subclass/coercion, missing/unknown field, literal, pattern, scalar or cardinality is invalid after resource, canonical, boundary and time exclusions |
| `TIME_OR_VALIDITY_INVALID` | Canonical UTC seconds, required equality/order, half-open upper bound, Qualification/Manifest validity or final `EXPIRED` rule fails; copied/mismatched Receipt is excluded |
| `POLICY_IDENTITY_MISMATCH` | Policy ID, version, exact policy bytes or policy SHA-256 differs |
| `UPSTREAM_CLOSURE_MISMATCH` | ADR-042 through ADR-045 formal/projection/linkage/predecessor replay fails outside the Set-fresh-status, common-primary, raw-media and ADR-046 specializations below |
| `ROLE_BINDING_FINALIZATION_INVALID` | At either exact ADR-046 verifier call site, a frozen non-`PNG_ADMISSION_INVALID` `GeneratedReferenceRoleBindingError` or one of the six allowed Rights/current-status error classes is selected, or the supplied positive Request/Decision/Binding/result does not rebuild exactly |
| `COMMON_FRAME_MISMATCH` | Artifact, Profile, Catalog, subject, purpose or full role vocabulary differs; primary binding and Rights use their specialized codes |
| `DUPLICATE_ROLE_OR_BINDING` | A requested role or exact `binding_id`/`binding_sha256` identity pair repeats |
| `ROLE_SELECTION_INVALID` | Non-empty purpose subset, cardinality, member-role or derived coverage closure fails outside duplicate/order rules |
| `CANONICAL_ORDER_INVALID` | Requested roles are not the frozen subsequence or member tuple/ordinal/role order differs; no sorting or repair occurs |
| `RAW_MEDIA_MISMATCH` | Either exact ADR-046 verifier selects `GeneratedReferenceRoleBindingError.code == "PNG_ADMISSION_INVALID"`, or direct Set whole-PNG bytes/size/technical/raw digest or Outcome/Candidate/Sidecar/Binding/member media anchors differ |
| `CURRENT_STATUS_REPLAY_INVALID` | Set Request/final fresh replay build, coverage, linkage or Receipt exact value/byte equality fails; valid `REVOKED`/`HELD`/`INDETERMINATE` is a policy outcome |
| `REQUEST_MEMBER_STATUS_NOT_CURRENT` | A valid complete Request-time replay is `REVOKED`, `HELD` or `INDETERMINATE`; no Request is created |
| `PRIMARY_BINDING_INVALID` | Request/final Bible+AssetVersion rebuild, digest, active-state or required equality fails; one otherwise valid active final drift remains gate 7 `FAIL` |
| `RIGHTS_SCOPE_MISMATCH` | Manifest/Binding/member/common scope is not field-equal or was narrowed, expanded, reordered, substituted, unioned, intersected or renewed |
| `IDENTITY_RECORD_INVALID` | Identity raw-record codec, profile, fields, type or digest is invalid |
| `ACTION_RECORD_INVALID` | Maker/Checker action codec, profile, fields, digest, actor anchor or exact formal/gate/issue/Decision copy differs, excluding actor-separation policy |
| `IDENTITY_SEPARATION_INVALID` | A prohibited actor tuple equals, an unlisted overlap occurs or required action/formal/raw digest non-aliasing fails |
| `DECISION_OR_SET_REVALIDATION_FAILED` | Caller Decision/Set identity, projection, document, linkage or positive-pair atomic materialization/revalidation invariant fails |

Released upstream typed failures would be wrapped at their exact call sites, never mapped by message:

| Call site | Exact Set code |
| --- | --- |
| Either exact ADR-046 verifier raising exact `GeneratedReferenceRoleBindingError` with exact `.code == "PNG_ADMISSION_INVALID"` | `RAW_MEDIA_MISMATCH` |
| Either exact ADR-046 verifier raising exact `GeneratedReferenceRoleBindingError` with any one of the other 18 frozen released ADR-046 codes | `ROLE_BINDING_FINALIZATION_INVALID` |
| Either exact ADR-046 verifier raising any of the six allowlisted Rights/current-status error classes while reconstructing its historical Promotion/Role-Binding status closures | `ROLE_BINDING_FINALIZATION_INVALID` |
| Either ADR-046 verifier raising `GeneratedReferenceAssetPromotionError` from its historical ADR-045 Promotion closure | `UPSTREAM_CLOSURE_MISMATCH` |
| Direct ADR-046 Request/Decision/Binding/target SHA helper or Role-Binding document-byte serializer raising `GeneratedReferenceRoleBindingError` during exact revalidation | `ROLE_BINDING_FINALIZATION_INVALID` |
| `GeneratedReferenceRoleBindingAdmittedPng` construction or Set whole-PNG comparison | `RAW_MEDIA_MISMATCH` |
| Set core directly calling its allowlisted Request/final fresh-status build/process/verify or status document-byte-equality targets and receiving one of those same six status error classes | `CURRENT_STATUS_REPLAY_INVALID` |
| Common-primary rebuild/hash call raising `GeneratedReferenceAssetPromotionError` or failing | `PRIMARY_BINDING_INVALID` |

The five exact target groups above partition all 15 names in the upstream call-target allowlist:
two common-primary targets, five fresh-status targets and eight Role-Binding targets. No name may
appear in two target groups or remain outside them. The two ADR-046 verifier targets deliberately
have different portable mappings by exact exception type and, only for
`GeneratedReferenceRoleBindingError`, exact frozen `.code`; grouping target names therefore does not
collapse the typed-cause rows.

The six status classes in both call-site rows are exactly
`GeneratedReferenceRightsCurrentStatusError`, `GeneratedReferenceChainReplayError`,
`GeneratedReferenceChainCoverageError`, `GeneratedReferenceJointReplayError`,
`GeneratedReferenceAsOfAssessmentError` and `GeneratedReferenceReceiptError`. The same class therefore
maps by frozen direct call site, not by class alone.

The wrapper would be `GeneratedReferenceRoleBindingSetError(SetErrorCode, stable_message)` with the
exact original exception retained only as `__cause__`. No message would be parsed. The exact
ADR-046 `.code` is inspected only at the two verifier call sites for the frozen PNG/non-PNG split and
does not enter Set identity. An unknown or future ADR-046 code, unlisted call target or reflected call
is a compatibility stop/module bug and cannot fall through to a guessed portable code; the boundary
connection itself remains `PROHIBITED_BOUNDARY_CONNECTION` when that condition is detected by a
Set-owned check.

Set-owned/direct-call validation priority would be:

1. resource limits;
2. canonical documents/records;
3. prohibited boundary, Contract-field and time/validity checks;
4. policy identity, ADR-042..045 predecessor closure and one atomic delegated ADR-046
   Request/finalization verifier invocation;
5. common frame, duplicates, role selection and canonical order;
6. exact whole-PNG occurrence verification;
7. Set fresh status, primary binding and Rights scope;
8. identity record, action record and identity separation; and
9. complete Decision/Set revalidation and positive atomicity.

Within one Set-owned/direct-call stage the code order above wins, followed by common inputs, then
canonical member `selection_ordinal`, then that member's frozen predecessor order. Validation stops
at the first failure and does not collect or reorder errors. Request preparation skips final-only
checks without changing the remaining order.

At the delegated ADR-046 stage, Set code must call the exact released verifier once and map the one
exception it selected. It must not run a Set-side preflight before the call, call the verifier again,
probe for a later fault or otherwise impose the Set tuple inside the verifier. ADR-046 retains its
released Promotion-closure then PNG then Role/Purpose, primary-binding, current-status, Rights,
separation, action, time, authority and atomicity order. Consequently a dual fault consisting of PNG
admission failure plus any post-PNG ADR-046 failure maps to `RAW_MEDIA_MISMATCH`, because ADR-046
selects `PNG_ADMISSION_INVALID` first.

Any exception, mismatch or resource failure would return no partial value, mutate no object and
perform no external action. Only a structurally valid policy evaluation could create a negative or
indeterminate Decision.

## Contract and Schema Registry impact

Accepted R2 changes no current Contract, Schema or Registry entry. If separately authorized for
BUILD, it would append exactly three top-level models at indices 89 through 91 and
increase the Registry from 89 to 92. It would not modify current model fields, `$defs`, titles,
required sets, enum values, references or bytes.

The future committed Schema paths would be exactly:

```text
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetRequestV1.schema.json
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetDecisionV1.schema.json
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetV1.schema.json
```

Schema generation would remain explicit. This Accepted R2 generates nothing.

## Validation and future implementation gates

A future BUILD could proceed only under separate explicit authorization. It would have to:

1. begin from a newly verified authoritative clean `main` in a new isolated `codex/` branch;
2. record path, Git blob, size and SHA-256 for all 89 current Schemas and all 20 current fixtures
   before any generation;
3. prove `MODELS[:89]`, all 89 existing Schema bytes and all 20 existing fixture bytes unchanged at
   the final reviewed commit, while preserving older 83/16 and 86/18 historical assertions;
4. append only the exact three approved top-level models in exact Registry order;
5. keep target/member/replay/gate helpers inline rather than Registry entries;
6. fully reconstruct every supplied ADR-046 finalization and verify exact original whole PNG bytes;
7. test common Artifact/Profile/Catalog/subject/purpose/primary-binding/Rights equality;
8. test Character `1..3`, Scene `1..4`, canonical subsets, singleton, PARTIAL and FULL;
9. test duplicate roles, duplicate Bindings, member reorder, ordinal mutation, same-Sidecar
   cross-role allowance and equal-bytes distinct occurrences;
10. test that one bad member cannot be omitted, replaced or converted into a favorable subset;
11. test Request-time and final per-member replay, all prior-target/branch coverage, copied Receipt,
    copied `CURRENT`, stale closure attacks, Request-time expired/non-current no-Request outcomes,
    exact Request `TIME_OR_VALIDITY_INVALID`/`REQUEST_MEMBER_STATUS_NOT_CURRENT` codes, final expired
    no-Decision time failure, final revoked/held Reject and final indeterminate Decision;
12. test every `member.binding_at <= requested_at <= set_at`, all exact time equalities, half-open
    bounds and minimum validity calculations;
13. test Request-time/final primary-binding equality and valid final drift;
14. test exact per-member Rights retention and reject unequal, expanded, narrowed, reordered,
    renewed, intersected or unioned scopes;
15. test every prohibited Set Checker equality, every exact permitted Set Maker/Selector overlap and
    every allowed/forbidden cross-member status reuse by semantic identity tuple;
16. test the exact Request-admission order, final 13-gate order, five-code FAIL-only issue mapping,
    human Rights gate, FAIL-over-INDETERMINATE priority, closed Set-owned/direct-call order, inherited
    ADR-046 verifier order, PNG-plus-post-PNG dual faults, every call-site typed-cause mapping and
    Decision mapping; enumerate every narrower allowlisted callable by exact
    symbol name and prove each of its allowlisted typed failures maps to exactly one portable Set code;
17. test positive Decision+Set atomicity, injected Set-construction failure and no placeholder Set;
18. test every semantic projection field, self-field exclusion, full/short identity agreement and
    cross-domain non-aliasing;
19. test compact semantic/retained JSON and two-space-plus-terminal-LF formal JSON independently,
    duplicate-key rejection, bounds, tuple immutability and deterministic equality across CWD, hash
    seed, timezone, locale and supported host OS;
20. test the exact semantic-owner capsule and closed raw-leaf ledger, structural alias ownership,
    cross-member/stage/non-aliased-buffer no-dedup, 31-capsule/1,780-leaf/512,524,288-byte final
    limits and 268,435,456-byte aggregate PNG limit;
21. reject every Provider/InputMaterial/ProviderRequest/Runtime/URL/slot/order/idempotency,
    credential, cost, Retry, publication, retention and training injection;
22. prove by AST/import inspection that the core Set module imports only the exact allowed upstream
    modules/symbol classes and never imports `InputMaterial`, `ProviderRequest`, Provider, Compiler,
    Runtime, Worker, QC or persistence code;
23. prove the two support callable signatures, typed return dataclass fields/invariants and complete
    public call graph; prove Set codegen imports exactly those two old-codegen function symbols and
    never accesses an old-codegen module alias, private/dynamic/reflected name, CLI, update or writer;
24. prove current Compiler, Provider, Runtime, Worker, QC and persistence modules do not import the
    future Set module;
25. prohibit wall clock, filesystem/database discovery, environment selection, randomness and
    network state in identity or selection;
26. use only first-party fictional synthetic Prompt, PNG, evidence and human-reference material;
27. create a complete human known-answer packet and obtain separate explicit acceptance before
    Draft-to-Ready; and
28. run full repository validation in a frozen or isolated worktree and compare final Git blobs with
    the start baseline before review or merge.

Passing those gates would prove only deterministic implementation conformance over supplied values
and bytes. It would not prove real pixel truth beyond prior bounded reviews, identity authentication,
legal sufficiency, present currentness, Provider eligibility, execution authority or commercial use.

## Future codegen and known-answer boundary

If separately authorized, one isolated codegen CLI would require exactly one of `--check` or
`--update`. `--check` would be read-only. `--update` would write only one fixed derived fixture after
the reviewed source fixture received a separate byte-size/SHA-256 anchor. It would never alter old
fixtures, Schemas, ADRs, source fixtures or PNGs.

### Accepted R2 public fixed-fixture support APIs

Accepted R2 adds exactly one public typed support callable to each of two already released codegen
modules. The Promotion codegen callable and signature would be exactly:

```python
def build_generated_reference_asset_promotion_fixed_fixture_support(
    repository_root: Path,
    *,
    case_id: Literal[
        "character-same-status-record-v1",
        "scene-successor-reconciliation-v1",
    ],
) -> GeneratedReferenceAssetPromotionFixedFixtureSupportV1
```

`GeneratedReferenceAssetPromotionFixedFixtureSupportV1` would be an exact frozen `slots` dataclass
with these fields in this order:

```text
case_id
upstream
request_status
final_status
primary_bible
primary_asset_version
request
result
sidecar
maker_identity_bytes
maker_action_bytes
checker_identity_bytes
checker_action_bytes
promotion_at
primary_sidecar_association_result
primary_sidecar_association_basis
composite_unsplit_role_deferral_result
composite_unsplit_role_deferral_basis
promotion_basis
```

The callable would read only the Promotion codegen module's already frozen paths and exact
fingerprints, rebuild and verify one positive ADR-045 Request/Decision/Sidecar closure and verify its
formal bytes before returning. `sidecar` would be non-optional and would be the exact Sidecar in
`result`; `primary_bible` and `primary_asset_version` would be the exact pair used in both requested
and Promotion-final closure positions. It would return no dictionary, path, file handle or writer.

The Role-Binding codegen callable and signature would be exactly:

```python
def build_generated_reference_role_binding_positive_fixed_fixture_support(
    promotion_support: GeneratedReferenceAssetPromotionFixedFixtureSupportV1,
    *,
    selected_reference_role: Literal[
        "CHARACTER_IDENTITY_SHEET",
        "CHARACTER_POSE_REFERENCE",
        "CHARACTER_EXPRESSION_REFERENCE",
        "SCENE_ESTABLISHING_REFERENCE",
        "SCENE_LIGHTING_REFERENCE",
        "SCENE_MATERIAL_REFERENCE",
        "SCENE_PROP_PLACEMENT_REFERENCE",
    ],
    maker_identity_bytes: bytes,
    checker_identity_bytes: bytes,
    request_basis: str,
    exact_role_and_reviewed_rights_scope_presented_without_expansion_basis: str,
    whole_composite_role_suitability_basis: str,
    non_exclusive_no_transform_boundary_basis: str,
    decision_basis: str,
) -> GeneratedReferenceRoleBindingPositiveFixedFixtureSupportV1
```

`GeneratedReferenceRoleBindingPositiveFixedFixtureSupportV1` would be an exact frozen `slots`
dataclass with these fields in this order:

```text
selected_reference_role
promotion
admitted_png
role_binding_request
role_binding_result
binding
role_binding_request_status
role_binding_final_status
primary_bible
primary_asset_version
maker_identity_bytes
maker_action_bytes
checker_identity_bytes
checker_action_bytes
role_binding_at
exact_role_and_reviewed_rights_scope_presented_without_expansion_result
exact_role_and_reviewed_rights_scope_presented_without_expansion_basis
whole_composite_role_suitability_result
whole_composite_role_suitability_basis
non_exclusive_no_transform_boundary_result
non_exclusive_no_transform_boundary_basis
role_binding_decision_basis
```

The Role-Binding callable would derive `requested_at == binding_at ==
promotion_support.promotion_at`; fix all three human result fields to exact `PASS`; construct the
in-memory admitted PNG only from `promotion_support.upstream.png_bytes`; prepare and verify the exact
Request; finalize and verify the exact positive Decision/Binding pair; verify formal bytes; and fail
unless the non-optional `binding` is the exact Binding in `role_binding_result`. It would accept no
path, second PNG, caller-selected gate result, current time, environment value or authority input.
Both Role-Binding status fields would be the exact `promotion_support.final_status`, and its primary
pair would be the exact Promotion support primary pair.

The Set codegen module could direct-import from the two old codegen modules only these two function
symbols. It would call the Promotion support function, pass that exact typed result into the
Role-Binding support function and explicitly construct Set-owned member inputs from the returned
typed fields. Static return typing would propagate without directly importing either return dataclass.
The Set codegen must not import either old codegen module as an alias, access any private or
underscore-prefixed name, use dynamic import/`getattr`/reflection, or call `main`, an argument parser,
`_build_expected_closure`, `--update` or any writer. Its remaining imports would be the Set core and
standard library only.

No production/core, Compiler, Provider, Runtime, Worker, QC or persistence module may import either
support callable or either old codegen module. The Role-Binding codegen support implementation may
consume the exact typed Promotion support value but may not expose or call a Set type.

Both support call graphs would be deterministic and read-only. They would perform no recursive
discovery and no write, would leave both old codegen CLIs and old derived fixtures byte-exact, and
would expose no production Runtime or core construction authority. The existing Set test paths would
prove exact signatures, dataclass field order/types, fixed positive invariants, direct-import/call
allowlists and absence of private, alias, dynamic, CLI, update and writer access. No third codegen
support API or additional test path is allowed.

The frozen future fixture paths are:

```text
tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/
  reviewed-known-answer-source-v1.json
  generated-known-answer-v1.json
```

The codegen would freeze the complete 20-path pre-BUILD fixture map and append only those two paths,
increasing the tracked fixture count from 20 to 22.

The source packet would contain at least one first-party fictional Character case and one
first-party fictional Scene case. The derived packet would cover:

- Character and Scene singleton, canonical proper-subset and exact full-tuple cases;
- same Sidecar under different roles through distinct positive Bindings;
- equal bytes under distinct Candidate/Sidecar occurrences;
- duplicate role, duplicate Binding, reorder, ordinal and cross-purpose attacks;
- cross-Artifact/Profile/Catalog/subject/primary-binding and unequal-Rights rejection;
- request/final stale closure attacks, Request-time expired/non-current no-Request outcomes, final
  expired no-Decision time failure, final revoked/held negative Decisions, final indeterminate
  Decisions, and expired Qualification/Manifest no-output time failures;
- omitted-branch and favorable-subset attacks;
- every forbidden and permitted identity equality;
- positive, rejected and indeterminate Decisions and positive atomicity; and
- prohibited Provider/InputMaterial/ProviderRequest/Runtime fields and imports.

Synthetic Sets would be technical known answers only. They would not represent real selection,
current legal entitlement, Provider-input qualification or asset use.

## Exact future BUILD changed-file allowlist

If a separate BUILD were later authorized without intervening semantic revision, the closed
changed-file allowlist would be exactly:

```text
.github/workflows/ci.yml
Makefile
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetRequestV1.schema.json
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetDecisionV1.schema.json
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetV1.schema.json
src/sdc/generated_reference_asset_promotion_codegen.py
src/sdc/generated_reference_role_binding_codegen.py
src/sdc/generated_reference_role_binding_set.py
src/sdc/generated_reference_role_binding_set_codegen.py
src/sdc/schemas.py
tests/test_generated_reference_role_binding_set.py
tests/test_generated_reference_role_binding_set_codegen.py
tests/test_generated_reference_role_binding.py
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
tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json
tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/generated-known-answer-v1.json
```

The Accepted R2 future allowlist has exactly 27 unique paths. The two paths added to Accepted R1's
25-path list are only `src/sdc/generated_reference_asset_promotion_codegen.py` and
`src/sdc/generated_reference_role_binding_codegen.py`. Changes in those old modules would be limited
to the exact support APIs above and their internal deterministic read-only reuse; their frozen
fixtures, derived bytes, fingerprints and existing CLI behavior must not change. Workflow and
Makefile changes would be limited to the new offline read-only Set codegen check. Historical test
changes would be limited to support-API/isolation enforcement, new 89/20 prefix protection and exact
92/22 append assertions. The ADR itself is deliberately absent from a future BUILD allowlist.

Any need for another path, top-level model, Registry order, fixture or policy rule would stop BUILD
and require a separately reviewed ADR revision or architecture decision. Accepted R2 does not
authorize any allowlist path to change without separate BUILD authorization.

## Rejected alternatives

Accepted R2 carries forward Accepted R1's rejected alternatives and continues to reject:

- treating one atomic Binding as a complete or executable set;
- defining supplied-set rules only inside current `InputMaterial` or `ProviderRequest`;
- a database query, filesystem scan, active pointer, latest/best ranking or mutable pack;
- machine or agent selection, role inference, sorting repair or automatic missing-role completion;
- cross-Artifact, cross-Profile, cross-Catalog, cross-subject, cross-purpose, mixed-primary-binding or
  unequal-Rights-scope Sets in R2;
- duplicate roles or reuse of the same exact Binding under multiple members;
- rejecting same-Sidecar cross-role use when separate positive revalidated atomic Bindings exist;
- deduplicating equal PNG bytes across different Candidate/Sidecar occurrences;
- describing FULL as global completeness, uniqueness, exclusivity or future currentness;
- deleting a failing member and silently returning a smaller positive Set;
- mutating, refreshing, superseding or deleting old Bindings or Sets;
- unioning, intersecting, narrowing, expanding, reordering or renewing Rights scopes;
- crop, split, panel extraction, transformation or derived-media creation;
- Provider slots, order, model, route, locator, URL, upload, request fingerprint or idempotency;
- current `InputMaterial`, `ProviderRequest`, AssetVersion, Bible or Compiler model reuse;
- Runtime, network, credentials, environment, cost, Retry, persistence or paid-service integration;
- copying the ADR-042 through ADR-046 reconstruction chain into Set codegen to preserve the old
  25-path allowlist;
- adding fixed-fixture reconstruction authority to the production Set core or weakening the complete
  executable known-answer packet into a declarative scenario matrix;
- Set-side preflight/retry/probing that attempts to reorder an ADR-046 verifier's selected failure;
  and
- treating synthetic known answers as real assets, Rights, Provider or execution authority.

## Risks and treatment

| Severity | Risk | Required treatment |
| --- | --- | --- |
| Blocking | Set error order attempts to reorder an ADR-046 atomic verifier | Inherit the released verifier order and map exact `PNG_ADMISSION_INVALID` by typed `.code` only |
| Blocking | Complete known answers require private upstream codegen access | Add only the two frozen typed read-only support APIs and stop on any private/dynamic/third API access |
| Blocking | One atomic Binding is treated as a complete Set | Require explicit finite target, exact requested roles and one member per role |
| Blocking | Members are discovered, ranked or repaired implicitly | Require Maker-supplied exact canonical tuple and reject storage/latest/best/sorting behavior |
| Blocking | A failing member is omitted to obtain a favorable partial result | Bind the original requested tuple into every identity and fail or decide that exact tuple only |
| Blocking | Historical Binding or Receipt is treated as current | Perform complete per-member Request and final replay; retain present-currentness false |
| Blocking | Rights are aggregated or expanded | Require field-equal scopes, retain per-member anchors and prohibit union/intersection/renewal |
| Blocking | Mixed primary bindings silently enter one Set | Rebuild one common binding twice; valid final drift produces no positive Set |
| Blocking | Duplicate roles or Bindings make cardinality ambiguous | Require role and Binding uniqueness and consecutive role-ordered ordinals |
| Blocking | Equal bytes cause distinct Candidate occurrences to merge | Keep exact Outcome/Candidate/Sidecar/Binding anchors; never deduplicate by media hash |
| Blocking | FULL is read as global completeness or exclusivity | Keep all global/exclusive assertions false and define FULL only against the frozen purpose tuple |
| Blocking | Set Checker controls upstream decisions or changes selection | Enforce exact identity matrix; Checker may decide only the unchanged Maker proposal |
| Blocking | Positive Decision or Set exists without the other | Construct, revalidate and return the positive pair atomically |
| Blocking | Set becomes Provider input or execution authority | Keep provider-input false, include no locator/slot/order and prohibit conversion/import paths |
| Important | Canonical Set order is read as Provider order | Name it selection identity order and defer Provider mapping to another ADR |
| Important | Equal-scope common-frame restriction is mistaken for legal sufficiency | State it is structural equality only and retain `grants_rights=false` |
| Important | Large repeated closures exhaust resources | Freeze member, PNG, document, aggregate byte and depth limits before BUILD |
| Important | Raw/semantic digests or member ordinals alias | Use explicit fields and unique domains; test mutation and cross-domain non-aliasing |
| Important | Portable values leak paths, URLs, credentials or identity data | Retain only bounded privacy-minimized refs/digests and exact reviewed scopes |
| Important | New Schemas or fixtures drift released bytes | Freeze 89/20, preserve historical prefixes and append exactly 3 Schemas/2 fixtures |
| Minor | Historical Sets accumulate without resolver or supersession | State the limitation and defer storage/current-set policy |
| Minor | PARTIAL/FULL terminology is confused in UI | Keep exact semantic literals and defer display labels/localization |
| Minor | Provider later requires a different order or duplicate policy | Treat future Provider materialization as a separate decision, not a Set mutation |

## Non-goals

Accepted R2 does not approve or specify:

- implementation through this architecture acceptance alone;
- any current Contract, Schema, Registry, fixture, source, test, codegen, CI or Makefile change;
- creation or review of a real Request, Decision, Set, Binding, Sidecar or asset;
- Provider Input Material V2 or any `InputMaterial`/`ProviderRequest` conversion;
- Provider slot, order, locator, URL, upload, model, route, request fingerprint or idempotency;
- Provider selection, submission, inspection, download, cancellation or Retry;
- Runtime, Worker, Temporal, PostgreSQL, persistence, migration or event integration;
- network, credentials, remote processing, paid service or cost reservation;
- changing Compiler, Storyboard, NIR, PIR, Job, Compilation or AssemblyPlan identity;
- AssetVersion/Bible creation, activation, replacement or mutation;
- cross-Artifact/Profile/Catalog/subject/purpose/primary-binding or unequal-Rights-scope Sets;
- same-role multi-candidate ranking, latest/best/current resolver or active-set pointer;
- global role completeness, exclusivity, uniqueness, supersession or absence proof;
- crop, split, mask, panel extraction, transformation or derived media;
- a new Qualification, Rights decision, Rights union/intersection or legal-sufficiency claim;
- reviewer, source, account or organizational identity authentication;
- QC automation, publication, posting, release, retention/deletion automation or training controls;
- wall-clock lookup, database/filesystem discovery, automatic renewal, migration or backfill;
- a trusted-local filesystem finalizer; or
- external Prompt, image, brand, real-person, third-party character, protected-work or sensitive-data
  fixtures.

## Permitted claims and explicit non-proofs

At this Accepted R2 documentation state, SDC may claim only that the exact R2 error-mapping remedy,
27-path allowlist, support-API boundary, restart gate and policy identity recorded here received
human architecture acceptance. It may not claim that any R2-conforming Contract, Schema,
implementation, known-answer packet or actual Set output exists or is available.

Only after separate BUILD authorization, implementation, first-party synthetic known-answer
acceptance and merge could SDC claim that:

- one pure offline operation fully revalidated an explicitly supplied bounded tuple of positive
  atomic Bindings and their original whole PNG occurrences;
- every member shared one exact common frame and had complete fresh replay at Request and `set_at`;
- one independent Set Checker recorded one deterministic Decision over the unchanged Maker tuple;
- one positive Decision produced one immutable historical Set atomically; and
- all existing Schema/fixture bytes and complete zero-authority boundaries remained unchanged.

Even then, SDC could not claim that:

- the Set remains current after `set_at`;
- a PARTIAL tuple is sufficient for any consumer;
- FULL proves global completeness, uniqueness, exclusivity or absence of other Bindings/Sets;
- different roles use different media or separable crops;
- common reviewed scope proves ownership, license, legal sufficiency or commercial use;
- retained references authenticate a person, organization, competence or authority;
- absence of supplied adverse evidence proves that none exists;
- the Set is Provider-input eligible, is an `InputMaterial`, has Provider order or can execute;
- Provider capability, entitlement, availability, route, cost or authorization exists;
- Runtime, Retry, network, credentials, payment, publication, retention or training is permitted; or
- equal bytes from another Candidate occurrence inherit a member Binding or Set identity.

## Consequences

Positive consequences of Accepted R2, if separately authorized and implemented, would include:

- explicit finite selection would replace implicit discovery or one-Binding completeness guesses;
- canonical role coverage, duplicate behavior and occurrence identity would become portable and
  deterministic;
- PARTIAL/FULL could be stated narrowly without granting global completeness;
- every member would retain exact whole-media, Rights, primary-binding and fresh-status closure;
- one failing member could not be hidden through favorable-subset repair;
- human selection and final review would remain independent and auditable by retained references;
- old Bindings and Compiler artifacts would remain immutable;
- Provider-input and execution would remain visibly separate later decisions; and
- the Registry could remain append-only from 89 to 92 in a future authorized BUILD.

Costs and limitations would include:

- every member requires complete ADR-046 reconstruction, exact PNG re-admission and two new status
  replays;
- R2 cannot combine different Artifacts, Profiles, Rights scopes or primary bindings;
- same-Sidecar cross-role reuse means FULL does not imply distinct media;
- no active/latest/best Set resolver or supersession exists;
- no Provider slot/order/materialization or Runtime path exists;
- three new Schemas, two fixed fixtures and extensive synthetic negative tests would be required;
  and
- every later consumer would still need its own fresh replay and authority decision.

## Accepted R2 partial-BUILD restart gate

The dirty partial BUILD on `codex/generated-reference-role-binding-set-r1` is preserved historical
working material only. This R2 acceptance does not validate, adopt, resume, rebase, merge, amend or
authorize it. BUILD could restart only after all of the following separate gates close:

1. this exact Accepted R2 is committed and merged into authoritative `main`;
2. a separate explicit BUILD-restart authorization is granted;
3. a new clean isolated BUILD worktree/branch is created from authoritative `main` containing R2;
4. the complete 89-Schema/20-fixture path, Git blob, size and SHA-256 baseline is recorded again;
5. the current partial 22-path worktree is audited read-only and only individually reviewed changes
   conforming to the R2 27-path allowlist are ported into the new clean BUILD worktree;
6. all old 89 Schema and 20 fixture bytes remain exact and the implemented policy identity equals
   the Accepted R2 identity frozen above; and
7. any 28th path, historical-byte change, private/dynamic codegen access or support-API authority
   expansion stops BUILD and requires another architecture decision.

The dirty partial branch must not be rebased, merged, amended or used to continue BUILD implicitly.
Its existence grants no authority and no partial test result may be represented as R2 conformance.

## Accepted R2 acceptance-record task boundary

The current authorized Accepted-R2 acceptance-record documentation work is confined to the isolated
worktree on this branch, and only this file may be modified:

```text
codex/adr-047-r2-role-binding-set-boundary
docs/adr/SDC-ADR-047.md
```

It must not:

- claim this architecture acceptance authorizes staging, commit, push, PR, Ready, merge, BUILD,
  implementation or Human known-answer acceptance;
- alter Accepted R1 history outside the explicit R2 replacements, weaken the 89-Schema/20-fixture
  compatibility gate, future 92-Schema/22-fixture target or any zero-authority rule;
- modify ADR-039 through ADR-046 or any current Contract, Schema, Registry, fixture, source, test,
  codegen, CI, Makefile or README file;
- calculate implementation outputs, run Schema generation, code generation or fixture update;
- modify or resume the current partial BUILD worktree;
- stage, commit, push, create a PR, request review, mark Ready or merge;
- create or review a real Set, Binding, Sidecar, Provider input or asset;
- connect Compiler, Provider, Runtime, network, credentials, cost, Retry or persistence; or
- begin BUILD, Provider-input, publication, retention or training work.
