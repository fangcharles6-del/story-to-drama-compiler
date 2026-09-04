# SDC-ADR-047: Generated Reference Bounded Supplied Role-Binding Set Boundary

- Status: Accepted R5
- Date: 2026-09-03
- Latest accepted revision: Accepted R5 on 2026-09-03
- Prior revisions: Accepted R4 on 2026-09-02; Accepted R3 on 2026-09-01; Accepted R2 on 2026-09-01; Accepted R1 on 2026-08-31
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
- Accepted R3 drafting authoritative-main baseline: `96dc22258044fb2dbdcbce1e8dfe185e340747a2`
- Accepted R4 drafting authoritative-main baseline: `bd0a40ef7625c272a0b9d91f1dcbd31ac37a6383`
- Accepted R5 drafting authoritative-main baseline: `8737c49bb949900432ed86074a7dff2c90769ace`
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: one explicitly supplied bounded tuple of exact positive ADR-046 Role-Binding
  occurrences under one exact common Artifact/Profile/subject/purpose/primary-binding/Rights frame;
  complete explicitly supplied predecessor and fresh-status closures, exact local whole PNG bytes
  and privacy-minimized retained Set review records; first-party synthetic review data only
- Network/spend boundary: zero network calls, zero credential reads, zero Provider requests, zero
  authorized Attempts and zero authorized cost

## Accepted R5 executable-evidence contradiction remediation record

The separately authorized R4 BUILD remains uncommitted working material and has not received Human
known-answer acceptance. Its strict packet closure stopped before writing a derived Set fixture
because three Accepted R4 evidence descriptions cannot be satisfied honestly by their named public
operations:

1. `expired-qualification-manifest-v1--001--qualification-expired` and
   `expired-qualification-manifest-v1--002--manifest-expired` are classified as
   `PUBLIC_API_EXECUTION` / `PUBLIC_FINALIZE`, but a valid Request freezes
   `request_valid_until` as no later than every member Qualification, Manifest and Request-status
   exclusive bound. Setting either named final bound equal to `set_at` therefore makes the earlier
   Request half-open guard fail before the named final guard can run. A returned
   `TIME_OR_VALIDITY_INVALID` cannot be represented as evidence that the named final guard ran; and
2. `resource-limit-exceeded-v1--012--semantic-capsules-31-admit` is classified as
   `PUBLIC_FINALIZE`, while the frozen capsule ledger permits that builder to own at most 29
   capsules. The 31-capsule positive boundary belongs only to the released public finalization
   verifier.

The same stopped R4 codegen also passes `scene_singleton_baseline` to `_execute_public_probe` while
the callee signature does not declare that parameter. That signature gap is an implementation
defect inside the existing allowlisted Set-codegen path; it does not change the architecture
decision and cannot be repaired by this document-only architecture acceptance.

Accepted R5 carries forward every Accepted R4 Contract shape, scenario ID and order, probe ID and
order, support callable, input-anchor category, 21-code direct error order, five-code issue order,
resource boundary, cross-Catalog vector, 27-path total allowlist, nine-path Set-specific ceiling,
89-Schema/20-fixture compatibility anchor, 92-Schema/22-fixture target and zero-authority value
except for the exact evidence corrections and Policy identity frozen below. It records exactly
these accepted changes:

1. retain exactly 48 top-level scenarios and 217 ordered evidence units without renaming or
   reordering any scenario or probe;
2. retain both expired-bound probe IDs and their `CHARACTER_PRIMARY_R3` anchor, split their former
   shared family into two independent families, and classify both units as
   `STRUCTURAL_UNREACHABILITY_PROOF` under the new
   `STRUCTURAL_TIME_VALIDITY_DOMINANCE_PROOF` operation;
3. assign the exact tagged outcomes
   `PROVED_UNREACHABLE:QUALIFICATION_FINAL_BOUND_EQUALITY_INDEPENDENT_REACH` and
   `PROVED_UNREACHABLE:MANIFEST_FINAL_BOUND_EQUALITY_INDEPENDENT_REACH`, with one probe-local proof
   vector per named bound and one shared structural rule proving that Request validity necessarily
   dominates either equality case;
4. remove `expired-qualification-manifest-v1` only from the `TIME_OR_VALIDITY_INVALID` executable
   error-evidence row. The closed error ledger remains exactly 21 rows and that code remains covered
   by two public units in `request-expired-status-v1` and `final-expired-status-v1`; the proof units
   are not relabelled as executions of that code;
5. change only the operation and callgraph ledger of
   `resource-limit-exceeded-v1--012--semantic-capsules-31-admit` to
   `PUBLIC_FINALIZATION_VERIFY` and `frozen positive finalization verifier`. Its ID, input anchor,
   four-member/31-capsule vector and `DECISION_AND_SET_APPROVE` outcome remain exact. The existing
   Scene FULL positive execution already covers the 29-capsule finalizer boundary, so no 218th unit
   is added;
6. freeze evidence-kind counts at exactly 135 public, 58 hermetic and 24 structural units; freeze
   operation counts at 67 `PUBLIC_FINALIZE`, four `PUBLIC_FINALIZATION_VERIFY`, two
   `STRUCTURAL_TIME_VALIDITY_DOMINANCE_PROOF` and every other Accepted R4 operation count unchanged;
7. assign Policy version `1.4.0` and the exact 234,946-byte canonical identity below, including four
   future-anchor values and three structural source labels mechanically retargeted from R4 to R5;
   stable `POLICY_R3` and `*_R3` keys remain historical identifiers and do not describe the current
   Policy version; and
8. retain exactly the two existing support callable symbols. The correction adds no support case,
   public/private/dynamic API, production seam, input-anchor category, PNG or path. A future
   separately authorized R5 BUILD must remove the two now-dead expired-bound executable recipes and
   repair the `scene_singleton_baseline` signature gap only inside the existing allowlisted Set
   codegen path.

Accepted R5 supersedes only the three contradictory Accepted R4 evidence descriptions and Policy
identity explicitly frozen above. It records Human architecture acceptance of exactly those
evidence corrections, the Policy identity, seven mechanical stage-label retargets and the unchanged
zero-authority boundary. It does not accept, resume, repair, regenerate or validate the R4 or R3
partial BUILD; authorize any Contract, Schema, Registry, fixture, source, test, generator, staging,
commit, push, PR, review, Ready or merge action; grant Human known-answer acceptance; or grant
Provider-input, Runtime, network, credentials, spend, Retry, rights, asset use, execution,
publication, retention, training or commercial authority.

## Accepted R4 cross-catalog executable-evidence remediation record

The separately authorized R3 BUILD remains uncommitted working material and has not received Human
known-answer acceptance. Its strict no-write packet closure stopped at
`cross-catalog-attack-v1--001--cross-catalog`: the accepted R3 vector required member ordinal 1 to
take its Catalog version/digest "from the other fixed case", but both exact released fixed cases
carry Catalog version `1.0.0` and digest
`cbf0e0baa8ca1bc63f8643b6e9f0982134a9bf2386e8d8c1db8adc31e7cf2fc2`. Copying that pair was a
semantic no-op, so the public Target builder correctly returned a Target rather than
`COMMON_FRAME_MISMATCH`. No derived Set fixture was written after that stop.

Accepted R4 carries forward every Accepted R3 Set shape, scenario and probe identity, evidence-kind
count, operation, expected outcome, support surface, resource boundary, error/issue order,
27-path allowlist, 89-Schema/20-fixture compatibility anchor, 92-Schema/22-fixture target and
zero-authority value except for the one unsatisfiable cross-Catalog mutation vector, the Policy
identity necessarily changed by that vector and the seven mechanical R3-to-R4 stage-label retargets
enumerated in item 6 below. It records exactly these accepted changes:

1. keep `cross-catalog-attack-v1--001--cross-catalog` under `SCENE_PRIMARY_R3` as one
   `PUBLIC_TARGET_BUILD` execution expecting `TYPED_ERROR:COMMON_FRAME_MISMATCH`;
2. replace only the phrase "from the other fixed case" with one complete probe-local fixed mutation
   that directly changes supplied Binding tuple index 1's `catalog_version` and `catalog_sha256`
   while preserving every other field, including the pre-mutation Target and Binding identities;
3. bind the replacement pair to the full `prompt_profile_catalog_projection` of the frozen
   first-party Catalog after changing only `catalog_version` to `1.0.1` and `source_revision` to
   `sdc.adr-047-r4.cross-catalog-probe.first-party-fictional-test-only.1`; every other projection
   field remains exact and the complete object is embedded in the probe vector below. Its UTF-8
   `json.dumps` encoding uses `sort_keys=True`, separators `,` and `:`, `ensure_ascii=False` and
   `allow_nan=False`, with no BOM and no terminal LF, and is exactly 2,656 bytes with raw SHA-256
   `bbbf2d1cdf993e14bd252baaf4547ba2e5c635a72eb47891f3695e20724201c5`. The Catalog semantic
   digest is SHA-256 over the exact 29-byte domain
   `sdc:visual-prompt-catalog:v1\0` followed by those 2,656 bytes and equals
   `d02bf1e1a06da6f44fb57d3c998e349eefc32a3f00eb688c89c9c00a97a83178`. This is a deterministic
   adversarial Catalog projection for one negative test; it does not claim that a separately
   published or currently eligible Catalog exists and grants no Provider, Runtime, rights,
   asset-use or commercial authority;
4. require the exact mutated pair to differ from both released fixed-case Catalog identities before
   the public call, and require the execution descriptor to retain the mutation-document bytes,
   digest, exact two-field ledger and no-identity-rehash assertion;
5. assign Policy version `1.3.0` and the new canonical byte count and digest recorded below, without
   adding a sixth input anchor, third support API, private/dynamic access, production seam, PNG or
   BUILD path; and
6. update only four carried-forward future-anchor rule values and three structural-proof source
   labels from R3 to R4, while retaining their stable `*_R3` keys/anchor IDs and every operation,
   proof requirement and probe binding unchanged.

The existing `POLICY_R3` and `*_R3` input-anchor strings remain stable evidence identifiers so that
this correction does not relabel 217 probes or create a sixth anchor. Under Accepted R4 they bind
the current `1.3.0` Policy and future R4 byte anchors; their suffix is historical nomenclature, not
a claim that the corrected Policy still has the R3 identity.

Accepted R4 records Human architecture acceptance of exactly the remediation, Policy identity,
seven mechanical stage-label retargets and zero-authority boundary frozen here. It does not
authorize implementation, resumption or validation of the stopped R3 BUILD,
Contract/Schema/Registry/fixture generation, Human
known-answer acceptance, staging, commit, push, PR, Provider-input, Runtime, network, credentials,
spend, Retry, asset use, publication, retention or training.

## Accepted R3 executable-packet remediation record

The separately authorized R2 BUILD remains uncommitted working material and has not received Human
known-answer acceptance. Its final technical review found that the frozen 37-scenario source shape
could express only one scalar expected outcome per scenario, covered only 11 of the closed 21 Set
error codes and omitted the Selection-human-gate `FAIL` issue. It also found that sealed-policy and
dominated resource guards are not honestly caller-input reachable, while injected Set-construction
failure is not a generated-fixture public-input result.

Accepted R3 carries forward every Accepted R2 Set Contract shape, 21-code priority tuple, 13-gate
order, five-code issue tuple, resource limit, identity rule, 27-path BUILD allowlist, 89-Schema/
20-fixture compatibility anchor, 92-Schema/22-fixture target and zero-authority value except where
this revision explicitly replaces R2's known-answer evidence model and fixed support-case surface.
It makes exactly these architecture changes:

1. preserve the exact first 37 scenario IDs and their order, append 10 previously absent typed-error
   scenarios and one Selection-human-gate `FAIL` scenario, and freeze exactly 48 top-level scenarios;
2. replace the ambiguous scenario-level executable flag and scalar expected error with a complete
   ordered probe ledger in which every independent evidence unit has its own stable identity,
   evidence kind, input or mutation anchor and tagged expected outcome;
3. distinguish public API execution, hermetic test-only fault injection and structural
   unreachability proof without representing the latter two as public executable fixture results;
4. retain exactly two public fixed-fixture support callable symbols while extending the Promotion
   callable by one bounded first-party fictional equal-PNG/distinct-occurrence case; and
5. assign a new policy version and identity because the exact support signature and known-answer
   evidence policy change.

Accepted R3 records Human architecture acceptance only. It does not resume or validate either
partial BUILD worktree, authorize implementation or Schema/fixture generation, grant Human
known-answer acceptance, or authorize Provider-input, Runtime, network, credentials, spend, Retry,
asset use, publication, retention or training.

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

A conforming positive R5 Set, only after separate BUILD authorization and conforming
implementation, would mean only:

> At one explicit historical `set_at`, one independent Set Checker approved that one explicitly
> supplied canonical tuple contained exactly one revalidated positive atomic Binding for every
> explicitly requested role under one closed common frame, after complete per-member fresh replay
> and exact whole-PNG verification.

It would not mean that the Set is globally complete or exclusive, remains current, contains distinct
media per role, has Provider slot order, can become an `InputMaterial` or authorizes asset use,
Provider execution, publication or training.

## Accepted R1/R2/R3/R4 architecture record

Accepted R1 records human acceptance of the architecture decisions frozen in that revision. Accepted
R2 records human acceptance of exactly the two replacements and new policy identity frozen in the
Accepted R2 revision record below.
Neither acceptance authorizes any Contract, Schema, Registry, fixture, source, test, codegen, CI,
Makefile or implementation change, actual Set selection, media review, Provider input or execution.

Accepted R3 records Human architecture acceptance of exactly the 48-scenario/217-unit evidence
model, bounded third Promotion support case and Policy `1.2.0` identity frozen in this revision.
This acceptance is not Human known-answer acceptance and grants no BUILD or execution authority.

R3 architecture acceptance does not authorize BUILD. Any R3 BUILD requires this exact Accepted R3
first to be committed and merged into authoritative `main`, then separate explicit BUILD
authorization, a newly verified clean authoritative `main`, a new isolated `codex/` implementation
branch and a newly recorded immutable 89-Schema/20-fixture baseline. Human known-answer acceptance,
Draft-to-Ready conversion and merge authorization remain later separate gates.

The separately authorized R3 BUILD satisfied those entry gates but exposed the unsatisfiable
cross-Catalog vector recorded above. It remains stopped and uncommitted. Accepted R4 neither accepts
that working material nor authorizes its repair, regeneration or reuse. If Accepted R4 is later
separately committed and merged, implementation would still require a separate BUILD authorization
and exact revalidation of the existing R3 BUILD worktree or a newly authorized clean replacement.

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

The R3 Human architecture acceptance confirms exactly:

1. the first 37 scenario IDs and order remain exact and the 10 absent typed-error scenarios plus
   `human-selection-fail-v1` append at the tail, producing exactly 48 top-level scenarios;
2. the ordered evidence ledger contains exactly 217 independently identified probes: 137 public API
   executions, 58 hermetic test-only fault injections and 22 structural unreachability proofs;
3. every probe owns its input or mutation anchor, evidence kind and tagged expected outcome, while
   the exact 21-row error-code and five-row issue-code ledgers remain closed;
4. sealed Policy identity and dominated aggregate resource boundaries use explicit structural proof,
   while reachable equality and narrower resource boundaries use public execution evidence;
5. Set-construction failure evidence is test-local, deterministic, automatically restored and
   confined to Set construction, with no production factory, callback or public test seam;
6. exactly two support callable symbols remain; the Promotion callable adds only the fixed
   first-party fictional in-memory equal-PNG/distinct-Candidate/Sidecar occurrence case, with no new
   PNG path, private/dynamic access or third API;
7. delegated PNG dual-fault evidence retains the two support APIs, the ADR-046 order anchor and
   Set-call-site typed injection rules;
8. the accepted Policy identity is version `1.2.0`, 227,888 canonical compact bytes and SHA-256
   `4075b6e0bb6a5a5c1e2f949bfd640f94eda974c3f09987e56820a787dda7a308`;
9. the future BUILD allowlist remains exactly 27 paths, the old 89 Schema and 20 fixture bytes remain
   immutable, and any future R3 BUILD must regenerate and newly anchor the three Set Schemas and two
   Set fixtures while both fixtures remain `human_known_answer_acceptance=NOT_GRANTED`; and
10. Human known-answer, Provider-input, Runtime, rights, asset use, execution and commercial-use
    permission remain independent and ungranted.

The R4 Human architecture acceptance confirms exactly:

1. all 48 scenario IDs, 217 probe IDs, 137/58/22 evidence-kind counts, operation IDs, tagged outcomes
   and error/issue ledgers remain unchanged;
2. `cross-catalog-attack-v1--001--cross-catalog` alone replaces its unsatisfiable source relation
   with the exact probe-local Catalog projection, semantic digest and ordinal/field ledger frozen in
   Policy `1.3.0`;
3. the mutated Catalog pair must differ from the exact baseline Catalog identity of both released
   fixed cases before the public Target call, and no unanchored sentinel or hidden test value may
   substitute for it;
4. `SCENE_PRIMARY_R3`, the five-anchor total, the two support callable symbols, the 27 BUILD paths
   and every production/core API remain unchanged; and
5. the Catalog mutation is deterministic negative-test material only and proves no real Catalog,
   current eligibility, Provider/Runtime authority, rights, asset-use or commercial permission.

This section is the R1/R2/R3/R4 architecture acceptance record and complete zero-authority boundary.
Accepted R4 remains architecture-only and is not a BUILD authorization.

## Accepted R5 architecture record and implementation gate

Accepted R5 accepts none of the R4 partial BUILD bytes. It freezes only the following architecture
corrections:

1. the 48 scenario IDs, their order, all 217 probe IDs and their order remain exact;
2. the two expired-bound units become independent structural proofs with the exact named-bound tags,
   vectors and common Request-validity dominance rule in Policy `1.4.0`;
3. the 31-capsule unit remains public and positive but is assigned to the public finalization
   verifier, while the public finalizer retains its 29-capsule build maximum;
4. evidence-kind counts become exactly 135/58/24, the exact 15-operation ledger becomes the one
   frozen below, and the 21-code/5-code ledger row order remains unchanged;
5. Policy identity becomes exactly version `1.4.0`, 234,946 compact canonical bytes and SHA-256
   `e2b9aacd7eb3de7e54c238b5d698e7a5abf48fee2931300576309eec4ec5dac0`;
6. the exact two support callables, five stable input anchors, existing in-memory synthetic PNGs,
   27-path total allowlist and nine-path Set-specific ceiling remain unchanged; and
7. a future implementation must delete the two dead public expired-bound recipes and repair the
   `scene_singleton_baseline` call/signature mismatch within the existing Set-codegen path, without
   interpreting either mechanical correction as a new API or evidence rule.

Accepted R5 is now the latest architecture authority, while the stopped R4 BUILD remains
nonconforming working material. Accepted R5 itself does not authorize BUILD. Before implementation,
this accepted document must be separately staged, committed, pushed, reviewed and merged under
explicit authorizations, followed by a separate BUILD authorization, exact authoritative-main and
immutable 89-Schema/20-fixture revalidation, and an expressly selected clean or hunk-reviewed
implementation worktree. Human known-answer acceptance and every Provider/Runtime or rights/use
authority remain later independent gates.

## Frozen upstream compatibility boundary

Neither Accepted R1, Accepted R2, Accepted R3 nor Accepted R4 narrows, supersedes or reinterprets
ADR-039 through ADR-046. In particular:

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

Accepted R5 does not change, narrow or reinterpret any of those upstream boundaries.

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

## Accepted R5 frozen policy projection

Accepted R5 carries every unchanged Accepted R4 policy field forward, changes only the two
final-bound evidence classifications and proof vectors, their shared structural rule and operation,
the 31-capsule probe operation/callgraph label, the directly affected evidence/error ledgers, the
Policy identity required by those semantic changes, and seven mechanical R4-to-R5 stage labels. It
retains the delegated ADR-046 priority rule, all 48 scenario IDs, all 217 probe IDs, the exact two-
callable support surface and the exact 27-path BUILD allowlist. The accepted semantic policy is:

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
        "scene-successor-reconciliation-v1",
        "character-equal-png-distinct-occurrence-v1"
      ],
      "case_rules": {
        "character-equal-png-distinct-occurrence-v1": {
          "base_case_id": "character-same-status-record-v1",
          "construction": "FIXED_FIRST_PARTY_FICTIONAL_IN_MEMORY_COMPLETE_OUTCOME_CANDIDATE_QUALIFICATION_MANIFEST_STATUS_PROMOTION_SIDECAR_OCCURRENCE",
          "distinct_identity_fields": [
            "provider_attempt_outcome_id",
            "candidate_id",
            "promotion_request_id",
            "promotion_decision_id",
            "eligible_asset_sidecar_id"
          ],
          "equal_fields": [
            "png_bytes",
            "media_content_sha256",
            "media_size_bytes",
            "media_technical_record_sha256",
            "reference_prompt_artifact_sha256",
            "profile_id",
            "profile_version",
            "profile_sha256",
            "catalog_version",
            "catalog_sha256",
            "subject_id",
            "asset_purpose",
            "primary_asset_binding",
            "reviewed_rights_scope"
          ],
          "new_path_allowed": false,
          "old_fixture_write_allowed": false,
          "provider_or_runtime_authority": false
        }
      },
      "parameters": [
        {
          "kind": "POSITIONAL_OR_KEYWORD",
          "name": "repository_root",
          "type": "pathlib.Path"
        },
        {
          "kind": "KEYWORD_ONLY",
          "name": "case_id",
          "type": "Literal[character-same-status-record-v1,scene-successor-reconciliation-v1,character-equal-png-distinct-occurrence-v1]"
        }
      ],
      "return_dataclass": "GeneratedReferenceAssetPromotionFixedFixtureSupportV1",
      "return_field_types": {
        "case_id": "Literal[character-same-status-record-v1,scene-successor-reconciliation-v1,character-equal-png-distinct-occurrence-v1]",
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
      "return_invariants": "FROZEN_SLOTS_EXACT_POSITIVE_ADR_045_REQUEST_DECISION_SIDECAR_PAIR_VERIFIED_SIDECAR_IS_RESULT_SIDECAR_PRIMARY_PAIR_USED_FOR_REQUESTED_AND_PROMOTION_FORMAL_BYTES_VERIFIED_TWO_RELEASED_FIXTURE_CASES_BYTE_EXACT_ONE_FIXED_IN_MEMORY_EQUAL_PNG_DISTINCT_OCCURRENCE_CASE_NO_OLD_FIXTURE_WRITE"
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
  "known_answer_codegen_support_rule": "EXACTLY_TWO_CALLABLE_SYMBOLS_SET_CODEGEN_DIRECT_IMPORTS_ONLY_BUILD_GENERATED_REFERENCE_ASSET_PROMOTION_FIXED_FIXTURE_SUPPORT_AND_BUILD_GENERATED_REFERENCE_ROLE_BINDING_POSITIVE_FIXED_FIXTURE_SUPPORT_FROM_OLD_CODEGEN_PROMOTION_SUPPORT_HAS_TWO_RELEASED_FIXTURE_CASES_AND_ONE_FIXED_IN_MEMORY_EQUAL_PNG_DISTINCT_OCCURRENCE_CASE_NO_OLD_CODEGEN_MODULE_ALIAS_PRIVATE_DYNAMIC_REFLECTION_MAIN_PARSER_BUILD_EXPECTED_CLOSURE_UPDATE_OR_WRITER_ACCESS_SUPPORT_CALL_GRAPH_READS_ONLY_FROZEN_PATHS_AND_NEVER_WRITES_NO_PRODUCTION_CORE_COMPILER_PROVIDER_RUNTIME_WORKER_QC_OR_PERSISTENCE_IMPORT",
  "known_answer_compatibility_stop_rule": {
    "packet_evidence_unit_count": 0,
    "required_external_conformance_test_count": 2,
    "rule": "UNKNOWN_OR_FUTURE_ADR_046_ERROR_CODE_AT_REQUEST_AND_FINALIZATION_CALL_SITES_IS_A_MODULE_COMPATIBILITY_STOP_NEVER_A_GUESSED_SET_ERROR_OR_PACKET_EXPECTED_OUTCOME"
  },
  "known_answer_coverage_ledger_rule": {
    "error_row_count": 21,
    "error_row_probe_selector": "Within each listed scenario select only probes tagged TYPED_ERROR:code, NO_RESULT_TYPED_ERROR:code or PROVED_UNREACHABLE:code. Zero matches or a different claimed code stops BUILD.",
    "issue_row_count": 5,
    "issue_row_probe_selector": "Within each listed scenario select only probes tagged DECISION_ONLY_REJECT:issue_code, optionally followed only by :FAIL_OVER_INDETERMINATE. Zero matches or a different first issue stops BUILD."
  },
  "known_answer_delegated_png_dual_fault_rule": {
    "adr_046_order_anchor": "tests/test_generated_reference_role_binding.py::test_representative_promotion_png_role_primary_status_stage_priority",
    "adr_046_selected_error_code": "PNG_ADMISSION_INVALID",
    "fixed_post_png_fault": "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID_BY_SCENE_LIGHTING_REFERENCE_ON_CHARACTER_PURPOSE",
    "set_call_site_probe_ids": [
      "raw-media-mismatch-v1--006--request-png-plus-post-png-dual-fault",
      "raw-media-mismatch-v1--007--finalization-png-plus-post-png-dual-fault"
    ],
    "set_mapping": "EXACT_TYPED_GENERATED_REFERENCE_ROLE_BINDING_ERROR_CODE_PNG_ADMISSION_INVALID_TO_RAW_MEDIA_MISMATCH_NO_MESSAGE_PARSE_PREFLIGHT_SECOND_CALL_OR_LATER_FAULT_SEARCH",
    "support_callable_symbols": [
      "build_generated_reference_asset_promotion_fixed_fixture_support",
      "build_generated_reference_role_binding_positive_fixed_fixture_support"
    ],
    "third_private_or_dynamic_support_allowed": false
  },
  "known_answer_error_code_evidence_ledger": [
    {
      "code": "RESOURCE_LIMIT_EXCEEDED",
      "scenario_ids": [
        "resource-limit-exceeded-v1"
      ]
    },
    {
      "code": "CANONICAL_DOCUMENT_INVALID",
      "scenario_ids": [
        "canonical-document-invalid-v1"
      ]
    },
    {
      "code": "PROHIBITED_BOUNDARY_CONNECTION",
      "scenario_ids": [
        "prohibited-authority-injection-v1"
      ]
    },
    {
      "code": "CONTRACT_FIELD_INVALID",
      "scenario_ids": [
        "contract-field-invalid-v1"
      ]
    },
    {
      "code": "TIME_OR_VALIDITY_INVALID",
      "scenario_ids": [
        "request-expired-status-v1",
        "final-expired-status-v1"
      ]
    },
    {
      "code": "POLICY_IDENTITY_MISMATCH",
      "scenario_ids": [
        "policy-identity-mismatch-v1"
      ]
    },
    {
      "code": "UPSTREAM_CLOSURE_MISMATCH",
      "scenario_ids": [
        "upstream-closure-mismatch-v1"
      ]
    },
    {
      "code": "ROLE_BINDING_FINALIZATION_INVALID",
      "scenario_ids": [
        "role-binding-finalization-invalid-v1"
      ]
    },
    {
      "code": "COMMON_FRAME_MISMATCH",
      "scenario_ids": [
        "cross-purpose-attack-v1",
        "cross-artifact-attack-v1",
        "cross-profile-attack-v1",
        "cross-catalog-attack-v1",
        "cross-subject-attack-v1"
      ]
    },
    {
      "code": "DUPLICATE_ROLE_OR_BINDING",
      "scenario_ids": [
        "duplicate-role-attack-v1",
        "duplicate-binding-attack-v1"
      ]
    },
    {
      "code": "ROLE_SELECTION_INVALID",
      "scenario_ids": [
        "omitted-branch-member-attack-v1",
        "favorable-subset-attack-v1",
        "role-selection-invalid-v1"
      ]
    },
    {
      "code": "CANONICAL_ORDER_INVALID",
      "scenario_ids": [
        "member-reorder-attack-v1"
      ]
    },
    {
      "code": "RAW_MEDIA_MISMATCH",
      "scenario_ids": [
        "raw-media-mismatch-v1"
      ]
    },
    {
      "code": "CURRENT_STATUS_REPLAY_INVALID",
      "scenario_ids": [
        "request-stale-closure-attack-v1",
        "final-stale-closure-attack-v1",
        "omitted-branch-member-attack-v1"
      ]
    },
    {
      "code": "REQUEST_MEMBER_STATUS_NOT_CURRENT",
      "scenario_ids": [
        "request-non-current-status-v1"
      ]
    },
    {
      "code": "PRIMARY_BINDING_INVALID",
      "scenario_ids": [
        "request-primary-binding-attack-v1"
      ]
    },
    {
      "code": "RIGHTS_SCOPE_MISMATCH",
      "scenario_ids": [
        "unequal-rights-attack-v1"
      ]
    },
    {
      "code": "IDENTITY_RECORD_INVALID",
      "scenario_ids": [
        "identity-record-invalid-v1"
      ]
    },
    {
      "code": "ACTION_RECORD_INVALID",
      "scenario_ids": [
        "action-record-invalid-v1"
      ]
    },
    {
      "code": "IDENTITY_SEPARATION_INVALID",
      "scenario_ids": [
        "forbidden-identity-equality-v1"
      ]
    },
    {
      "code": "DECISION_OR_SET_REVALIDATION_FAILED",
      "scenario_ids": [
        "favorable-subset-attack-v1",
        "positive-atomicity-injection-v1"
      ]
    }
  ],
  "known_answer_evidence_kind_order": [
    "PUBLIC_API_EXECUTION",
    "HERMETIC_TEST_ONLY_FAULT_INJECTION",
    "STRUCTURAL_UNREACHABILITY_PROOF"
  ],
  "known_answer_evidence_kind_unit_counts": {
    "HERMETIC_TEST_ONLY_FAULT_INJECTION": 58,
    "PUBLIC_API_EXECUTION": 135,
    "STRUCTURAL_UNREACHABILITY_PROOF": 24
  },
  "known_answer_issue_code_evidence_ledger": [
    {
      "issue_code": "MEMBER_STATUS_NOT_CURRENT_AT_SET",
      "scenario_ids": [
        "final-revoked-held-status-v1"
      ]
    },
    {
      "issue_code": "COMMON_PRIMARY_BINDING_NO_LONGER_ACTIVE",
      "scenario_ids": [
        "final-primary-binding-drift-v1"
      ]
    },
    {
      "issue_code": "PER_MEMBER_RIGHTS_PRESENTATION_NOT_ACKNOWLEDGED",
      "scenario_ids": [
        "human-rights-fail-v1"
      ]
    },
    {
      "issue_code": "EXPLICIT_SELECTION_ORDER_AND_COVERAGE_NOT_ACKNOWLEDGED",
      "scenario_ids": [
        "human-selection-fail-v1"
      ]
    },
    {
      "issue_code": "NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_NOT_ACKNOWLEDGED",
      "scenario_ids": [
        "fail-over-indeterminate-v1"
      ]
    }
  ],
  "known_answer_packet_closure_rule": "COMPLETE_PACKET_EQUALS_REVIEWED_SOURCE_FIXTURE_DERIVED_PUBLIC_EXECUTION_AND_PROOF_DESCRIPTORS_EXACT_POLICY_EXACT_HERMETIC_TEST_NODES_AND_FINAL_VALIDATION_RESULTS_DERIVED_FIXTURE_MAY_NOT_CLAIM_A_HERMETIC_TEST_RAN_OR_HUMAN_ACCEPTANCE_WAS_GRANTED_SCENARIO_EVIDENCE_CLOSES_ONLY_WHEN_EVERY_REQUIRED_PUBLIC_RESULT_TEST_VECTOR_AND_STRUCTURAL_PROOF_MATCHES_AT_ONE_FROZEN_COMMIT",
  "known_answer_packet_probe_shapes": {
    "derived_probe_field_order": [
      "probe_id",
      "scenario_id",
      "evidence_kind",
      "operation",
      "input_anchor",
      "mutation_or_fault_vector",
      "expected_outcome",
      "actual_outcome_or_proof",
      "evidence_anchor",
      "descriptor_status",
      "probe_sha256"
    ],
    "descriptor_status_order": [
      "PUBLIC_EXECUTION_MATCHED",
      "HERMETIC_TEST_NODE_ANCHORED_EXECUTION_REQUIRED",
      "STRUCTURAL_PROOF_VALIDATED"
    ],
    "evidence_anchor_fields": [
      "source_path_or_test_node",
      "git_blob_or_source_sha256",
      "size_bytes_or_call_count",
      "result_document_sha256s_or_proof_sha256"
    ],
    "expected_outcome_rule": "Exactly one tagged string. DECISION_AND_SET_APPROVE and DECISION_ONLY_INDETERMINATE have no suffix. DECISION_ONLY_REJECT has one exact issue suffix, except the exact FAIL_OVER_INDETERMINATE suffix form. TYPED_ERROR, NO_RESULT_TYPED_ERROR and RESOURCE_GUARD_ADMITTED_THEN_TYPED_ERROR have one exact Set error-code suffix. PROVED_UNREACHABLE has one exact proof-ID suffix. PROVED_PUBLIC_SURFACE_ABSENT has no suffix. The resource-guard tag proves only equality admission followed by the named fixed downstream error.",
    "expected_outcome_tag_order": [
      "DECISION_AND_SET_APPROVE",
      "DECISION_ONLY_REJECT",
      "DECISION_ONLY_INDETERMINATE",
      "TYPED_ERROR",
      "NO_RESULT_TYPED_ERROR",
      "RESOURCE_GUARD_ADMITTED_THEN_TYPED_ERROR",
      "PROVED_UNREACHABLE",
      "PROVED_PUBLIC_SURFACE_ABSENT"
    ],
    "input_anchor_fields": [
      "anchor_id",
      "case_ids",
      "source_paths_or_in_memory_case_ids",
      "r2_source_fixture_baseline",
      "future_r3_path_size_raw_sha256_and_semantic_identities"
    ],
    "source_probe_field_order": [
      "probe_id",
      "scenario_id",
      "probe_slug",
      "evidence_kind",
      "operation_id",
      "input_anchor_id",
      "mutation_or_fault_vector",
      "expected_outcome"
    ]
  },
  "known_answer_probe_count": 217,
  "known_answer_probe_ledger": [
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "character-cardinality-1"
          ]
        }
      ],
      "scenario_id": "character-singleton-positive-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "character-cardinality-2-partial"
          ]
        }
      ],
      "scenario_id": "character-partial-positive-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "character-cardinality-3-full"
          ]
        }
      ],
      "scenario_id": "character-full-positive-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "scene-cardinality-1"
          ]
        }
      ],
      "scenario_id": "scene-singleton-positive-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "scene-cardinality-3-partial"
          ]
        }
      ],
      "scenario_id": "scene-partial-positive-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "scene-cardinality-4-full"
          ]
        }
      ],
      "scenario_id": "scene-full-positive-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "same-sidecar-two-roles-distinct-bindings"
          ]
        }
      ],
      "scenario_id": "same-sidecar-cross-role-distinct-bindings-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "equal-png-distinct-candidate-sidecar"
          ]
        }
      ],
      "scenario_id": "equal-bytes-distinct-candidate-sidecar-occurrences-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:DUPLICATE_ROLE_OR_BINDING",
          "ordered_probe_slugs": [
            "duplicate-requested-role"
          ]
        }
      ],
      "scenario_id": "duplicate-role-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:DUPLICATE_ROLE_OR_BINDING",
          "ordered_probe_slugs": [
            "duplicate-binding-identity"
          ]
        }
      ],
      "scenario_id": "duplicate-binding-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:CANONICAL_ORDER_INVALID",
          "ordered_probe_slugs": [
            "reversed-member-tuple"
          ]
        }
      ],
      "scenario_id": "member-reorder-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_UNREACHABLE:CALLER_SUPPLIED_SELECTION_ORDINAL",
          "ordered_probe_slugs": [
            "selection-ordinal-is-builder-owned"
          ]
        }
      ],
      "scenario_id": "ordinal-mutation-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:COMMON_FRAME_MISMATCH",
          "ordered_probe_slugs": [
            "character-target-scene-role"
          ]
        }
      ],
      "scenario_id": "cross-purpose-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:COMMON_FRAME_MISMATCH",
          "ordered_probe_slugs": [
            "cross-artifact"
          ]
        }
      ],
      "scenario_id": "cross-artifact-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:COMMON_FRAME_MISMATCH",
          "ordered_probe_slugs": [
            "cross-profile"
          ]
        }
      ],
      "scenario_id": "cross-profile-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:COMMON_FRAME_MISMATCH",
          "ordered_probe_slugs": [
            "cross-catalog"
          ]
        }
      ],
      "scenario_id": "cross-catalog-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:COMMON_FRAME_MISMATCH",
          "ordered_probe_slugs": [
            "cross-subject"
          ]
        }
      ],
      "scenario_id": "cross-subject-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:PRIMARY_BINDING_INVALID",
          "ordered_probe_slugs": [
            "final-cross-subject-purpose-primary"
          ]
        }
      ],
      "scenario_id": "request-primary-binding-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_ONLY_REJECT:COMMON_PRIMARY_BINDING_NO_LONGER_ACTIVE",
          "ordered_probe_slugs": [
            "final-active-binding-drift"
          ]
        }
      ],
      "scenario_id": "final-primary-binding-drift-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:RIGHTS_SCOPE_MISMATCH",
          "ordered_probe_slugs": [
            "substituted",
            "expanded",
            "narrowed",
            "reordered",
            "renewed",
            "unioned",
            "intersected"
          ]
        }
      ],
      "scenario_id": "unequal-rights-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:CURRENT_STATUS_REPLAY_INVALID",
          "ordered_probe_slugs": [
            "stale-closure",
            "copied-receipt",
            "copied-current"
          ]
        }
      ],
      "scenario_id": "request-stale-closure-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:TIME_OR_VALIDITY_INVALID",
          "ordered_probe_slugs": [
            "request-expired"
          ]
        }
      ],
      "scenario_id": "request-expired-status-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:REQUEST_MEMBER_STATUS_NOT_CURRENT",
          "ordered_probe_slugs": [
            "request-revoked",
            "request-held",
            "request-indeterminate"
          ]
        }
      ],
      "scenario_id": "request-non-current-status-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:CURRENT_STATUS_REPLAY_INVALID",
          "ordered_probe_slugs": [
            "stale-closure",
            "copied-receipt",
            "copied-current"
          ]
        }
      ],
      "scenario_id": "final-stale-closure-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:TIME_OR_VALIDITY_INVALID",
          "ordered_probe_slugs": [
            "final-expired"
          ]
        }
      ],
      "scenario_id": "final-expired-status-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_ONLY_REJECT:MEMBER_STATUS_NOT_CURRENT_AT_SET",
          "ordered_probe_slugs": [
            "final-revoked",
            "final-held"
          ]
        }
      ],
      "scenario_id": "final-revoked-held-status-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_ONLY_INDETERMINATE",
          "ordered_probe_slugs": [
            "final-indeterminate"
          ]
        }
      ],
      "scenario_id": "final-indeterminate-status-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_UNREACHABLE:QUALIFICATION_FINAL_BOUND_EQUALITY_INDEPENDENT_REACH",
          "ordered_probe_slugs": [
            "qualification-expired"
          ]
        },
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_UNREACHABLE:MANIFEST_FINAL_BOUND_EQUALITY_INDEPENDENT_REACH",
          "ordered_probe_slugs": [
            "manifest-expired"
          ]
        }
      ],
      "scenario_id": "expired-qualification-manifest-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:CURRENT_STATUS_REPLAY_INVALID",
          "ordered_probe_slugs": [
            "omitted-prior-target-branch"
          ]
        },
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:ROLE_SELECTION_INVALID",
          "ordered_probe_slugs": [
            "omitted-member-from-original-request"
          ]
        }
      ],
      "scenario_id": "omitted-branch-member-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:ROLE_SELECTION_INVALID",
          "ordered_probe_slugs": [
            "omit-failed-member-from-original-request"
          ]
        },
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:DECISION_OR_SET_REVALIDATION_FAILED",
          "ordered_probe_slugs": [
            "replace-failed-member-on-original-request",
            "attach-fabricated-subset-set-to-adverse-decision"
          ]
        }
      ],
      "scenario_id": "favorable-subset-attack-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
          "ordered_probe_slugs": [
            "set-maker-selector",
            "qualification-qualifier",
            "manifest-checker",
            "promotion-request-status-checker",
            "promotion-final-status-checker",
            "promotion-checker",
            "role-binding-checker",
            "role-binding-request-status-checker",
            "role-binding-final-status-checker",
            "set-request-status-checker",
            "set-final-status-checker"
          ]
        }
      ],
      "scenario_id": "forbidden-identity-equality-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "qualification-request-preparer",
            "qualification-qualifier",
            "manifest-maker",
            "manifest-checker",
            "promotion-request-status-preparer",
            "promotion-request-status-checker",
            "promotion-final-status-preparer",
            "promotion-final-status-checker",
            "promotion-maker",
            "promotion-checker",
            "role-binding-request-status-preparer",
            "role-binding-request-status-checker",
            "role-binding-final-status-preparer",
            "role-binding-final-status-checker",
            "role-binding-maker",
            "role-binding-checker",
            "set-request-status-preparer",
            "set-request-status-checker",
            "set-final-status-preparer",
            "set-final-status-checker"
          ]
        }
      ],
      "scenario_id": "permitted-maker-overlap-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_ONLY_REJECT:PER_MEMBER_RIGHTS_PRESENTATION_NOT_ACKNOWLEDGED",
          "ordered_probe_slugs": [
            "rights-presentation-fail"
          ]
        }
      ],
      "scenario_id": "human-rights-fail-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_ONLY_INDETERMINATE",
          "ordered_probe_slugs": [
            "selection-indeterminate"
          ]
        }
      ],
      "scenario_id": "human-selection-indeterminate-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_ONLY_REJECT:NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_NOT_ACKNOWLEDGED:FAIL_OVER_INDETERMINATE",
          "ordered_probe_slugs": [
            "provider-boundary-fail-selection-indeterminate"
          ]
        }
      ],
      "scenario_id": "fail-over-indeterminate-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:DECISION_OR_SET_REVALIDATION_FAILED",
          "ordered_probe_slugs": [
            "positive-decision-without-set",
            "adverse-decision-with-set"
          ]
        },
        {
          "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
          "expected_outcome": "NO_RESULT_TYPED_ERROR:DECISION_OR_SET_REVALIDATION_FAILED",
          "ordered_probe_slugs": [
            "set-construction-failure"
          ]
        }
      ],
      "scenario_id": "positive-atomicity-injection-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:PROHIBITED_BOUNDARY_CONNECTION",
          "ordered_probe_slugs": [
            "final-only-status-input-at-request"
          ]
        },
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
          "ordered_probe_slugs": [
            "provider",
            "input-material",
            "provider-request",
            "runtime",
            "url",
            "slot",
            "order",
            "idempotency",
            "credential",
            "cost",
            "retry",
            "publication",
            "retention",
            "training"
          ]
        }
      ],
      "scenario_id": "prohibited-authority-injection-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "member-count-1-admit",
            "member-count-4-admit"
          ]
        },
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:RESOURCE_LIMIT_EXCEEDED",
          "ordered_probe_slugs": [
            "member-count-5-error"
          ]
        },
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "RESOURCE_GUARD_ADMITTED_THEN_TYPED_ERROR:UPSTREAM_CLOSURE_MISMATCH",
          "ordered_probe_slugs": [
            "per-member-png-exact-cap-guard-admit",
            "aggregate-png-exact-cap-guard-admit"
          ]
        },
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:RESOURCE_LIMIT_EXCEEDED",
          "ordered_probe_slugs": [
            "per-member-png-cap-plus-1-error"
          ]
        },
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_UNREACHABLE:AGGREGATE_PNG_STRICT_EXCEED",
          "ordered_probe_slugs": [
            "aggregate-png-strict-exceed-dominated"
          ]
        },
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "RESOURCE_GUARD_ADMITTED_THEN_TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
          "ordered_probe_slugs": [
            "raw-leaf-count-1780-guard-admit",
            "aggregate-raw-exact-cap-guard-admit"
          ]
        },
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:RESOURCE_LIMIT_EXCEEDED",
          "ordered_probe_slugs": [
            "raw-leaf-count-1781-error"
          ]
        },
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_UNREACHABLE:AGGREGATE_RAW_STRICT_EXCEED",
          "ordered_probe_slugs": [
            "aggregate-raw-strict-exceed-dominated"
          ]
        },
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_AND_SET_APPROVE",
          "ordered_probe_slugs": [
            "semantic-capsules-31-admit"
          ]
        },
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:RESOURCE_LIMIT_EXCEEDED",
          "ordered_probe_slugs": [
            "maker-action-bytes-cap-plus-1-error"
          ]
        }
      ],
      "scenario_id": "resource-limit-exceeded-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:CANONICAL_DOCUMENT_INVALID",
          "ordered_probe_slugs": [
            "utf8-bom",
            "carriage-return",
            "compact-retained-terminal-lf",
            "invalid-utf8",
            "nonfinite-json",
            "duplicate-key",
            "noncanonical-key-order",
            "noncanonical-whitespace"
          ]
        }
      ],
      "scenario_id": "canonical-document-invalid-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:CONTRACT_FIELD_INVALID",
          "ordered_probe_slugs": [
            "bindings-list",
            "wrong-binding-model",
            "binding-subclass",
            "requested-roles-list",
            "requested-role-non-string",
            "zero-bindings",
            "wrong-member-closure",
            "maker-identity-nonbytes",
            "empty-request-basis"
          ]
        }
      ],
      "scenario_id": "contract-field-invalid-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_UNREACHABLE:POLICY_IDENTITY_MISMATCH",
          "ordered_probe_slugs": [
            "sealed-policy-no-caller-input"
          ]
        }
      ],
      "scenario_id": "policy-identity-mismatch-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:UPSTREAM_CLOSURE_MISMATCH",
          "ordered_probe_slugs": [
            "promotion-maker-action-canonical-drift",
            "promotion-checker-action-canonical-drift"
          ]
        },
        {
          "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
          "expected_outcome": "TYPED_ERROR:UPSTREAM_CLOSURE_MISMATCH",
          "ordered_probe_slugs": [
            "promotion-error-at-request-verifier",
            "promotion-error-at-finalization-verifier"
          ]
        }
      ],
      "scenario_id": "upstream-closure-mismatch-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
          "ordered_probe_slugs": [
            "positive-binding-rebuild-drift"
          ]
        },
        {
          "axis_order": [
            "call_site",
            "upstream_code"
          ],
          "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
          "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
          "ordered_axis_product": {
            "call_site": [
              "request",
              "finalization"
            ],
            "upstream_code": [
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
            ]
          },
          "probe_slug_prefix": "role-binding-code"
        },
        {
          "axis_order": [
            "call_site",
            "upstream_type"
          ],
          "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
          "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
          "ordered_axis_product": {
            "call_site": [
              "request",
              "finalization"
            ],
            "upstream_type": [
              "GeneratedReferenceAsOfAssessmentError",
              "GeneratedReferenceChainCoverageError",
              "GeneratedReferenceChainReplayError",
              "GeneratedReferenceJointReplayError",
              "GeneratedReferenceReceiptError",
              "GeneratedReferenceRightsCurrentStatusError"
            ]
          },
          "probe_slug_prefix": "status-error-type"
        },
        {
          "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
          "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
          "ordered_probe_slugs": [
            "decision-sha256-target",
            "request-sha256-target",
            "binding-sha256-target",
            "contract-document-bytes-target",
            "target-sha256-target"
          ]
        }
      ],
      "scenario_id": "role-binding-finalization-invalid-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:ROLE_SELECTION_INVALID",
          "ordered_probe_slugs": [
            "empty-requested-subset",
            "outside-purpose-role",
            "binding-count-role-count-mismatch"
          ]
        }
      ],
      "scenario_id": "role-selection-invalid-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_UNREACHABLE:WHOLE_PNG_MUTATION_REACHES_SET_RAW_MEDIA",
          "ordered_probe_slugs": [
            "whole-png-mutation-dominated-by-promotion"
          ]
        },
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_UNREACHABLE:SIZE_ANCHOR_MUTATION_REACHES_SET_RAW_MEDIA",
          "ordered_probe_slugs": [
            "size-anchor-mutation-dominated-by-adr046"
          ]
        },
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_UNREACHABLE:CONTENT_SHA256_MUTATION_REACHES_SET_RAW_MEDIA",
          "ordered_probe_slugs": [
            "content-sha256-mutation-dominated-by-adr046"
          ]
        },
        {
          "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
          "expected_outcome": "PROVED_UNREACHABLE:SET_ADMITTED_PNG_CONSTRUCTION_FAILURE",
          "ordered_probe_slugs": [
            "admitted-png-construction-failure-unreachable"
          ]
        },
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:RAW_MEDIA_MISMATCH",
          "ordered_probe_slugs": [
            "technical-record-anchor-mismatch"
          ]
        },
        {
          "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
          "expected_outcome": "TYPED_ERROR:RAW_MEDIA_MISMATCH",
          "ordered_probe_slugs": [
            "request-png-plus-post-png-dual-fault",
            "finalization-png-plus-post-png-dual-fault"
          ]
        }
      ],
      "scenario_id": "raw-media-mismatch-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:IDENTITY_RECORD_INVALID",
          "ordered_probe_slugs": [
            "empty-object",
            "missing-identity-ref",
            "unknown-field",
            "profile-mismatch",
            "namespace-nonportable",
            "identity-ref-nonportable",
            "identity-ref-wrong-scalar"
          ]
        }
      ],
      "scenario_id": "identity-record-invalid-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
          "ordered_probe_slugs": [
            "maker-requested-roles-wrong-scalar",
            "maker-missing-target-sha256",
            "maker-unknown-field",
            "maker-target-sha256-drift",
            "checker-gates-wrong-scalar",
            "checker-missing-gate-results",
            "checker-unknown-field",
            "checker-request-sha256-drift",
            "checker-gate-result-drift",
            "checker-issue-codes-drift",
            "checker-decision-drift"
          ]
        }
      ],
      "scenario_id": "action-record-invalid-v1"
    },
    {
      "probe_families": [
        {
          "evidence_kind": "PUBLIC_API_EXECUTION",
          "expected_outcome": "DECISION_ONLY_REJECT:EXPLICIT_SELECTION_ORDER_AND_COVERAGE_NOT_ACKNOWLEDGED",
          "ordered_probe_slugs": [
            "selection-gate-fail"
          ]
        }
      ],
      "scenario_id": "human-selection-fail-v1"
    }
  ],
  "known_answer_probe_rule": "Expand scenarios in known_answer_scenario_id_order. Within a scenario expand families in list order; literal slugs retain list order; axis products use axis_order with leftmost axis outermost. Axis slug equals prefix plus hyphen plus hyphen-joined lower-ASCII axis values after underscore-to-hyphen conversion. Probe ID equals scenario_id, two hyphens, three-digit one-based local ordinal, two hyphens and slug. Each expanded ID occurs exactly once in probe_spec_by_id with exact repeated fields. Any invalid axis character, slug, ID, vector-ID or catalog collision stops BUILD.",
  "known_answer_probe_spec_catalog": {
    "input_anchor_catalog": {
      "CHARACTER_EQUAL_PNG_PAIR_R3": {
        "distinct_occurrence_case_ids": [
          "character-same-status-record-v1",
          "character-equal-png-distinct-occurrence-v1"
        ],
        "equal_relation": "PNG_BYTES_SIZE_CONTENT_SHA256_TECHNICAL_RECORD_SHA256_EQUAL_CANDIDATE_AND_SIDECAR_IDENTITIES_DISTINCT",
        "future_r3_anchor_rule": "R5 BUILD records generated source path, exact size, raw SHA-256 and referenced semantic identities; absence or mismatch stops BUILD.",
        "r2_source_fixture_baseline": {
          "path": "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json",
          "raw_sha256": "f27d6dd3ccf03b405f4fffd35ea7af7a83e2c2ebe18c33e726b49d911cf7bb76",
          "size_bytes": 30668
        },
        "reference_roles": [
          "CHARACTER_IDENTITY_SHEET",
          "CHARACTER_POSE_REFERENCE"
        ],
        "role_binding_support_callable": "build_generated_reference_role_binding_positive_fixed_fixture_support",
        "source_fixture_path": "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json"
      },
      "CHARACTER_PRIMARY_R3": {
        "future_r3_anchor_rule": "R5 BUILD records generated source path, exact size, raw SHA-256 and referenced semantic identities; absence or mismatch stops BUILD.",
        "promotion_support_case_ids": [
          "character-same-status-record-v1"
        ],
        "r2_source_fixture_baseline": {
          "path": "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json",
          "raw_sha256": "f27d6dd3ccf03b405f4fffd35ea7af7a83e2c2ebe18c33e726b49d911cf7bb76",
          "size_bytes": 30668
        },
        "reference_roles": [
          "CHARACTER_IDENTITY_SHEET",
          "CHARACTER_POSE_REFERENCE",
          "CHARACTER_EXPRESSION_REFERENCE"
        ],
        "role_binding_support_callable": "build_generated_reference_role_binding_positive_fixed_fixture_support",
        "source_fixture_path": "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json"
      },
      "POLICY_R3": {
        "canonical_identity_source": "EXACT_EXTERNAL_POLICY_IDENTITY_RECORD_IMMEDIATELY_AFTER_THIS_JSON_CODE_BLOCK",
        "policy_id": "sdc.generated-reference-bounded-supplied-role-binding-set-policy",
        "policy_version": "1.4.0"
      },
      "RESOURCE_IN_MEMORY_R3": {
        "base_anchor_id": "SCENE_PRIMARY_R3",
        "construction": "FIRST_PARTY_FICTIONAL_IN_MEMORY_ONLY_NO_TRACKED_PNG_PATH_SHARED_IMMUTABLE_BYTE_OBJECTS_COUNT_BY_OCCURRENCE_TESTS_MAY_USE_RELEASED_PUBLIC_ADR039_TO_ADR046_BUILDERS_NO_THIRD_SUPPORT_CALLABLE",
        "future_r3_anchor_rule": "R5 BUILD records generated source path, exact size, raw SHA-256 and referenced semantic identities; absence or mismatch stops BUILD.",
        "r2_source_fixture_baseline": {
          "path": "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json",
          "raw_sha256": "f27d6dd3ccf03b405f4fffd35ea7af7a83e2c2ebe18c33e726b49d911cf7bb76",
          "size_bytes": 30668
        },
        "source_fixture_path": "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json"
      },
      "SCENE_PRIMARY_R3": {
        "future_r3_anchor_rule": "R5 BUILD records generated source path, exact size, raw SHA-256 and referenced semantic identities; absence or mismatch stops BUILD.",
        "promotion_support_case_ids": [
          "scene-successor-reconciliation-v1"
        ],
        "r2_source_fixture_baseline": {
          "path": "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json",
          "raw_sha256": "f27d6dd3ccf03b405f4fffd35ea7af7a83e2c2ebe18c33e726b49d911cf7bb76",
          "size_bytes": 30668
        },
        "reference_roles": [
          "SCENE_ESTABLISHING_REFERENCE",
          "SCENE_LIGHTING_REFERENCE",
          "SCENE_MATERIAL_REFERENCE",
          "SCENE_PROP_PLACEMENT_REFERENCE"
        ],
        "role_binding_support_callable": "build_generated_reference_role_binding_positive_fixed_fixture_support",
        "source_fixture_path": "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json"
      }
    },
    "operation_catalog": {
      "HERMETIC_FINAL_ROLE_VERIFIER": {
        "automatic_restore": true,
        "patch_scope": "tests/test_generated_reference_role_binding_set.py::pytest.MonkeyPatch.context",
        "patch_target": "sdc.generated_reference_role_binding_set.verify_generated_reference_eligible_asset_role_binding_finalization",
        "positive_byte_replay_after_restore": true,
        "public_entry": "PUBLIC_REVIEW_PAYLOAD"
      },
      "HERMETIC_REQUEST_ROLE_VERIFIER": {
        "automatic_restore": true,
        "patch_scope": "tests/test_generated_reference_role_binding_set.py::pytest.MonkeyPatch.context",
        "patch_target": "sdc.generated_reference_role_binding_set.verify_generated_reference_eligible_asset_role_binding_request",
        "positive_byte_replay_after_restore": true,
        "public_entry": "PUBLIC_REVIEW_PAYLOAD"
      },
      "HERMETIC_ROLE_HELPER_REVALIDATION": {
        "automatic_restore": true,
        "patch_scope": "tests/test_generated_reference_role_binding_set.py::pytest.MonkeyPatch.context",
        "patch_target_from_probe": true,
        "positive_byte_replay_after_restore": true,
        "public_entry": "PUBLIC_REVIEW_PAYLOAD"
      },
      "HERMETIC_SET_CONSTRUCTION": {
        "automatic_restore": true,
        "patch_scope": "tests/test_generated_reference_role_binding_set.py::pytest.MonkeyPatch.context",
        "patch_target": "sdc.generated_reference_role_binding_set._build_identity",
        "positive_byte_replay_after_restore": true,
        "production_seam_allowed": false,
        "public_entry": "PUBLIC_FINALIZE",
        "trigger_exact_model_type": "CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetV1"
      },
      "PUBLIC_FINALIZATION_VERIFY": {
        "callable": "sdc.generated_reference_role_binding_set.verify_generated_reference_eligible_asset_role_binding_set_finalization",
        "patching_allowed": false
      },
      "PUBLIC_FINALIZE": {
        "callable": "sdc.generated_reference_role_binding_set.finalize_generated_reference_eligible_asset_role_binding_set",
        "patching_allowed": false
      },
      "PUBLIC_REQUEST_PREPARE": {
        "callable": "sdc.generated_reference_role_binding_set.prepare_generated_reference_eligible_asset_role_binding_set_request",
        "patching_allowed": false
      },
      "PUBLIC_REVIEW_PAYLOAD": {
        "callable": "sdc.generated_reference_role_binding_set.build_generated_reference_role_binding_set_review_payload_projection",
        "patching_allowed": false
      },
      "PUBLIC_TARGET_BUILD": {
        "callable": "sdc.generated_reference_role_binding_set.build_generated_reference_eligible_asset_role_binding_set_target",
        "patching_allowed": false
      },
      "STRUCTURAL_AUTHORITY_PROOF": {
        "private_or_dynamic_execution_allowed": false,
        "proof_inputs": [
          "exact R5 Set-core Git blob",
          "public signatures and return types",
          "imports and calls",
          "exact zero-authority inventory"
        ]
      },
      "STRUCTURAL_ORDINAL_PROOF": {
        "private_or_dynamic_execution_allowed": false,
        "proof_inputs": [
          "exact R5 Set-core Git blob",
          "target-builder signature and enumerate call",
          "public target validation behavior"
        ]
      },
      "STRUCTURAL_POLICY_PROOF": {
        "private_or_dynamic_execution_allowed": false,
        "proof_inputs": [
          "exact R5 Set-core Git blob",
          "public signatures",
          "Contract Policy literals",
          "compiled Policy canonical bytes and SHA",
          "self-check call graph"
        ]
      },
      "STRUCTURAL_RAW_MEDIA_DOMINANCE_PROOF": {
        "private_or_dynamic_execution_allowed": false,
        "proof_inputs": [
          "exact ADR-045 and ADR-046 verifier order",
          "Set _admitted_png_from_member derivation",
          "exact public signatures and call graph"
        ]
      },
      "STRUCTURAL_RESOURCE_DOMINANCE_PROOF": {
        "private_or_dynamic_execution_allowed": false,
        "proof_inputs": [
          "exact resource constants",
          "closed ownership/cardinality ledger",
          "integer dominance equation",
          "named public equality-guard result"
        ]
      },
      "STRUCTURAL_TIME_VALIDITY_DOMINANCE_PROOF": {
        "private_or_dynamic_execution_allowed": false,
        "proof_inputs": [
          "exact R5 Set-core Git blob",
          "request_valid_until minimum rule",
          "PUBLIC_FINALIZE guard order",
          "named Qualification and Manifest equality vectors"
        ]
      }
    },
    "probe_spec_by_id": {
      "action-record-invalid-v1--001--maker-requested-roles-wrong-scalar": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "maker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "replace requested_reference_roles array by string",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "maker-requested-roles-wrong-scalar",
          "vector_id": "action-record-invalid-v1::maker-requested-roles-wrong-scalar"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "maker-requested-roles-wrong-scalar",
        "scenario_id": "action-record-invalid-v1"
      },
      "action-record-invalid-v1--002--maker-missing-target-sha256": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "maker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "remove target_sha256",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "maker-missing-target-sha256",
          "vector_id": "action-record-invalid-v1::maker-missing-target-sha256"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "maker-missing-target-sha256",
        "scenario_id": "action-record-invalid-v1"
      },
      "action-record-invalid-v1--003--maker-unknown-field": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "maker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "add x_r3_unknown=false",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "maker-unknown-field",
          "vector_id": "action-record-invalid-v1::maker-unknown-field"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "maker-unknown-field",
        "scenario_id": "action-record-invalid-v1"
      },
      "action-record-invalid-v1--004--maker-target-sha256-drift": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "maker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "replace target_sha256 by 64 zeros",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "maker-target-sha256-drift",
          "vector_id": "action-record-invalid-v1::maker-target-sha256-drift"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "maker-target-sha256-drift",
        "scenario_id": "action-record-invalid-v1"
      },
      "action-record-invalid-v1--005--checker-gates-wrong-scalar": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "checker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "replace gate_results array by string",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "checker-gates-wrong-scalar",
          "vector_id": "action-record-invalid-v1::checker-gates-wrong-scalar"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "checker-gates-wrong-scalar",
        "scenario_id": "action-record-invalid-v1"
      },
      "action-record-invalid-v1--006--checker-missing-gate-results": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "checker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "remove gate_results",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "checker-missing-gate-results",
          "vector_id": "action-record-invalid-v1::checker-missing-gate-results"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "checker-missing-gate-results",
        "scenario_id": "action-record-invalid-v1"
      },
      "action-record-invalid-v1--007--checker-unknown-field": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "checker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "add x_r3_unknown=false",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "checker-unknown-field",
          "vector_id": "action-record-invalid-v1::checker-unknown-field"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "checker-unknown-field",
        "scenario_id": "action-record-invalid-v1"
      },
      "action-record-invalid-v1--008--checker-request-sha256-drift": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "checker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "replace request_sha256 by 64 zeros",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "checker-request-sha256-drift",
          "vector_id": "action-record-invalid-v1::checker-request-sha256-drift"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "checker-request-sha256-drift",
        "scenario_id": "action-record-invalid-v1"
      },
      "action-record-invalid-v1--009--checker-gate-result-drift": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "checker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "replace gate_results[0].basis by R3_DRIFT",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "checker-gate-result-drift",
          "vector_id": "action-record-invalid-v1::checker-gate-result-drift"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "checker-gate-result-drift",
        "scenario_id": "action-record-invalid-v1"
      },
      "action-record-invalid-v1--010--checker-issue-codes-drift": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "checker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "replace set_issue_codes by MEMBER_STATUS_NOT_CURRENT_AT_SET",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "checker-issue-codes-drift",
          "vector_id": "action-record-invalid-v1::checker-issue-codes-drift"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "checker-issue-codes-drift",
        "scenario_id": "action-record-invalid-v1"
      },
      "action-record-invalid-v1--011--checker-decision-drift": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ACTION_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "action_role": "checker",
          "codec": "compact canonical JSON without terminal LF",
          "definition": "replace decision by REJECT_BOUNDED_SUPPLIED_ROLE_BINDING_SET",
          "kind": "SET_ACTION_CANONICAL_OBJECT_MUTATION",
          "probe_slug": "checker-decision-drift",
          "vector_id": "action-record-invalid-v1::checker-decision-drift"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "checker-decision-drift",
        "scenario_id": "action-record-invalid-v1"
      },
      "canonical-document-invalid-v1--001--utf8-bom": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CANONICAL_DOCUMENT_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "field": "set_maker_identity_bytes",
          "kind": "MAKER_IDENTITY_RAW_BYTES_MUTATION",
          "mutation": "prepend EFBBBF",
          "probe_slug": "utf8-bom",
          "vector_id": "canonical-document-invalid-v1::utf8-bom"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "utf8-bom",
        "scenario_id": "canonical-document-invalid-v1"
      },
      "canonical-document-invalid-v1--002--carriage-return": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CANONICAL_DOCUMENT_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "field": "set_maker_identity_bytes",
          "kind": "MAKER_IDENTITY_RAW_BYTES_MUTATION",
          "mutation": "append 0D",
          "probe_slug": "carriage-return",
          "vector_id": "canonical-document-invalid-v1::carriage-return"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "carriage-return",
        "scenario_id": "canonical-document-invalid-v1"
      },
      "canonical-document-invalid-v1--003--compact-retained-terminal-lf": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CANONICAL_DOCUMENT_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "field": "set_maker_identity_bytes",
          "kind": "MAKER_IDENTITY_RAW_BYTES_MUTATION",
          "mutation": "append 0A",
          "probe_slug": "compact-retained-terminal-lf",
          "vector_id": "canonical-document-invalid-v1::compact-retained-terminal-lf"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "compact-retained-terminal-lf",
        "scenario_id": "canonical-document-invalid-v1"
      },
      "canonical-document-invalid-v1--004--invalid-utf8": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CANONICAL_DOCUMENT_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "field": "set_maker_identity_bytes",
          "kind": "MAKER_IDENTITY_RAW_BYTES_MUTATION",
          "mutation": "replace first ASCII byte by FF",
          "probe_slug": "invalid-utf8",
          "vector_id": "canonical-document-invalid-v1::invalid-utf8"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "invalid-utf8",
        "scenario_id": "canonical-document-invalid-v1"
      },
      "canonical-document-invalid-v1--005--nonfinite-json": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CANONICAL_DOCUMENT_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "field": "set_maker_identity_bytes",
          "kind": "MAKER_IDENTITY_RAW_BYTES_MUTATION",
          "mutation": "replace identity_ref string token by unquoted NaN",
          "probe_slug": "nonfinite-json",
          "vector_id": "canonical-document-invalid-v1::nonfinite-json"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "nonfinite-json",
        "scenario_id": "canonical-document-invalid-v1"
      },
      "canonical-document-invalid-v1--006--duplicate-key": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CANONICAL_DOCUMENT_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "field": "set_maker_identity_bytes",
          "kind": "MAKER_IDENTITY_RAW_BYTES_MUTATION",
          "mutation": "duplicate first object member",
          "probe_slug": "duplicate-key",
          "vector_id": "canonical-document-invalid-v1::duplicate-key"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "duplicate-key",
        "scenario_id": "canonical-document-invalid-v1"
      },
      "canonical-document-invalid-v1--007--noncanonical-key-order": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CANONICAL_DOCUMENT_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "field": "set_maker_identity_bytes",
          "kind": "MAKER_IDENTITY_RAW_BYTES_MUTATION",
          "mutation": "swap first two object members",
          "probe_slug": "noncanonical-key-order",
          "vector_id": "canonical-document-invalid-v1::noncanonical-key-order"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "noncanonical-key-order",
        "scenario_id": "canonical-document-invalid-v1"
      },
      "canonical-document-invalid-v1--008--noncanonical-whitespace": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CANONICAL_DOCUMENT_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "field": "set_maker_identity_bytes",
          "kind": "MAKER_IDENTITY_RAW_BYTES_MUTATION",
          "mutation": "insert one ASCII space after first colon",
          "probe_slug": "noncanonical-whitespace",
          "vector_id": "canonical-document-invalid-v1::noncanonical-whitespace"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "noncanonical-whitespace",
        "scenario_id": "canonical-document-invalid-v1"
      },
      "character-full-positive-v1--001--character-cardinality-3-full": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Finalize the exact three-role Character tuple in canonical order with all human gates PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "character-cardinality-3-full",
          "vector_id": "character-full-positive-v1::character-cardinality-3-full"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "character-cardinality-3-full",
        "scenario_id": "character-full-positive-v1"
      },
      "character-partial-positive-v1--001--character-cardinality-2-partial": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Finalize the exact first two Character roles/members in canonical order with all human gates PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "character-cardinality-2-partial",
          "vector_id": "character-partial-positive-v1::character-cardinality-2-partial"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "character-cardinality-2-partial",
        "scenario_id": "character-partial-positive-v1"
      },
      "character-singleton-positive-v1--001--character-cardinality-1": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Finalize the exact first Character role/member with all human gates PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "character-cardinality-1",
          "vector_id": "character-singleton-positive-v1::character-cardinality-1"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "character-cardinality-1",
        "scenario_id": "character-singleton-positive-v1"
      },
      "contract-field-invalid-v1--001--bindings-list": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CONTRACT_FIELD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "entry": "PUBLIC_TARGET_BUILD",
          "field_or_argument": "bindings",
          "kind": "EXACT_PUBLIC_CONTRACT_INPUT",
          "probe_slug": "bindings-list",
          "value": "list instead of tuple",
          "vector_id": "contract-field-invalid-v1::bindings-list"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "bindings-list",
        "scenario_id": "contract-field-invalid-v1"
      },
      "contract-field-invalid-v1--002--wrong-binding-model": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CONTRACT_FIELD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "entry": "PUBLIC_TARGET_BUILD",
          "field_or_argument": "bindings[0]",
          "kind": "EXACT_PUBLIC_CONTRACT_INPUT",
          "probe_slug": "wrong-binding-model",
          "value": "exact Set target model",
          "vector_id": "contract-field-invalid-v1::wrong-binding-model"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "wrong-binding-model",
        "scenario_id": "contract-field-invalid-v1"
      },
      "contract-field-invalid-v1--003--binding-subclass": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CONTRACT_FIELD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "entry": "PUBLIC_TARGET_BUILD",
          "field_or_argument": "bindings[0]",
          "kind": "EXACT_PUBLIC_CONTRACT_INPUT",
          "probe_slug": "binding-subclass",
          "value": "Binding model subclass instance",
          "vector_id": "contract-field-invalid-v1::binding-subclass"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "binding-subclass",
        "scenario_id": "contract-field-invalid-v1"
      },
      "contract-field-invalid-v1--004--requested-roles-list": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CONTRACT_FIELD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "entry": "PUBLIC_TARGET_BUILD",
          "field_or_argument": "requested_reference_roles",
          "kind": "EXACT_PUBLIC_CONTRACT_INPUT",
          "probe_slug": "requested-roles-list",
          "value": "list instead of tuple",
          "vector_id": "contract-field-invalid-v1::requested-roles-list"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "requested-roles-list",
        "scenario_id": "contract-field-invalid-v1"
      },
      "contract-field-invalid-v1--005--requested-role-non-string": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CONTRACT_FIELD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "entry": "PUBLIC_TARGET_BUILD",
          "field_or_argument": "requested_reference_roles[0]",
          "kind": "EXACT_PUBLIC_CONTRACT_INPUT",
          "probe_slug": "requested-role-non-string",
          "value": "integer 0",
          "vector_id": "contract-field-invalid-v1::requested-role-non-string"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "requested-role-non-string",
        "scenario_id": "contract-field-invalid-v1"
      },
      "contract-field-invalid-v1--006--zero-bindings": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CONTRACT_FIELD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "entry": "PUBLIC_TARGET_BUILD",
          "field_or_argument": "bindings",
          "kind": "EXACT_PUBLIC_CONTRACT_INPUT",
          "probe_slug": "zero-bindings",
          "value": "empty tuple",
          "vector_id": "contract-field-invalid-v1::zero-bindings"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "zero-bindings",
        "scenario_id": "contract-field-invalid-v1"
      },
      "contract-field-invalid-v1--007--wrong-member-closure": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CONTRACT_FIELD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "entry": "PUBLIC_REVIEW_PAYLOAD",
          "field_or_argument": "members[0]",
          "kind": "EXACT_PUBLIC_CONTRACT_INPUT",
          "probe_slug": "wrong-member-closure",
          "value": "exact positive Binding instead of Set closure input",
          "vector_id": "contract-field-invalid-v1::wrong-member-closure"
        },
        "operation_id": "PUBLIC_REVIEW_PAYLOAD",
        "probe_slug": "wrong-member-closure",
        "scenario_id": "contract-field-invalid-v1"
      },
      "contract-field-invalid-v1--008--maker-identity-nonbytes": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CONTRACT_FIELD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "entry": "PUBLIC_REQUEST_PREPARE",
          "field_or_argument": "set_maker_identity_bytes",
          "kind": "EXACT_PUBLIC_CONTRACT_INPUT",
          "probe_slug": "maker-identity-nonbytes",
          "value": "string",
          "vector_id": "contract-field-invalid-v1::maker-identity-nonbytes"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "maker-identity-nonbytes",
        "scenario_id": "contract-field-invalid-v1"
      },
      "contract-field-invalid-v1--009--empty-request-basis": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CONTRACT_FIELD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "entry": "PUBLIC_REQUEST_PREPARE",
          "field_or_argument": "request_basis",
          "kind": "EXACT_PUBLIC_CONTRACT_INPUT",
          "probe_slug": "empty-request-basis",
          "value": "empty string",
          "vector_id": "contract-field-invalid-v1::empty-request-basis"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "empty-request-basis",
        "scenario_id": "contract-field-invalid-v1"
      },
      "cross-artifact-attack-v1--001--cross-artifact": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:COMMON_FRAME_MISMATCH",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Replace only member 1 reference_prompt_artifact_sha256 from the other fixed case.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "cross-artifact",
          "vector_id": "cross-artifact-attack-v1::cross-artifact"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "cross-artifact",
        "scenario_id": "cross-artifact-attack-v1"
      },
      "cross-catalog-attack-v1--001--cross-catalog": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:COMMON_FRAME_MISMATCH",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "authority_nonproofs": [
            "NO_REAL_CATALOG_EXISTENCE_PROOF",
            "NO_CURRENT_ELIGIBILITY_PROOF",
            "NO_PROVIDER_OR_RUNTIME_AUTHORITY",
            "NO_RIGHTS_OR_ASSET_USE_PERMISSION",
            "NO_COMMERCIAL_USE_PERMISSION"
          ],
          "baseline_catalog_identity_by_fixed_case_id": {
            "character-same-status-record-v1": {
              "catalog_sha256": "cbf0e0baa8ca1bc63f8643b6e9f0982134a9bf2386e8d8c1db8adc31e7cf2fc2",
              "catalog_version": "1.0.0"
            },
            "scene-successor-reconciliation-v1": {
              "catalog_sha256": "cbf0e0baa8ca1bc63f8643b6e9f0982134a9bf2386e8d8c1db8adc31e7cf2fc2",
              "catalog_version": "1.0.0"
            }
          },
          "baseline_catalog_document_bytes": 2632,
          "baseline_catalog_document_raw_sha256": "c44cd699f2eb2be60de852c4d6194375ae965bc6af79dd40ed43cc9ced8260a7",
          "binding_tuple_index": 1,
          "catalog_document": {
            "authorized_attempts": 0,
            "authorized_cost_cny": 0,
            "automated_execution_allowed": false,
            "catalog_reviewed_at": "2026-08-27T03:06:32Z",
            "catalog_reviewer_ref": "github.fangcharles6-del",
            "catalog_version": "1.0.1",
            "current_gate": "HUMAN_GATE",
            "execution_authorized": false,
            "generation_authorized": false,
            "posts_allowed": 0,
            "profile_entries": [
              {
                "description": "Offline deterministic character reference-sheet profile for identity, pose, and expression continuity.",
                "display_name": "Cinematic Character Reference",
                "eligible_for_asset_promotion": false,
                "grants_execution_authority": false,
                "grants_qualification": false,
                "grants_rights": false,
                "offline_render_admission_status": "HUMAN_REVIEWED_FOR_OFFLINE_RENDER",
                "profile_ref": {
                  "profile_id": "sdc.character-reference.cinematic.v1",
                  "profile_sha256": "54901f50bc718eb6f51d866c842c70791c7d341e7f9c20c37281ee0bc840434d",
                  "profile_version": "1.0.0"
                },
                "profile_text_provenance_status": "FIRST_PARTY_TEXT_REVIEWED",
                "provider_syntax_compatibility_observations": []
              },
              {
                "description": "Offline deterministic cinematic storyboard profile for one narrative shot.",
                "display_name": "Cinematic Narrative Shot",
                "eligible_for_asset_promotion": false,
                "grants_execution_authority": false,
                "grants_qualification": false,
                "grants_rights": false,
                "offline_render_admission_status": "HUMAN_REVIEWED_FOR_OFFLINE_RENDER",
                "profile_ref": {
                  "profile_id": "sdc.narrative-shot.cinematic.v1",
                  "profile_sha256": "3da25632ad7798921a88200c591cd8774b65e533b6dd54a35be4c96802365181",
                  "profile_version": "1.0.0"
                },
                "profile_text_provenance_status": "FIRST_PARTY_TEXT_REVIEWED",
                "provider_syntax_compatibility_observations": []
              },
              {
                "description": "Offline deterministic scene reference-sheet profile for layout, light, materials, and prop continuity.",
                "display_name": "Cinematic Scene Reference",
                "eligible_for_asset_promotion": false,
                "grants_execution_authority": false,
                "grants_qualification": false,
                "grants_rights": false,
                "offline_render_admission_status": "HUMAN_REVIEWED_FOR_OFFLINE_RENDER",
                "profile_ref": {
                  "profile_id": "sdc.scene-reference.cinematic.v1",
                  "profile_sha256": "ea62abd6c0f35da2fa2ccc0d79ecc5e629aed84f14378dce0e14d88f49f11b0d",
                  "profile_version": "1.0.0"
                },
                "profile_text_provenance_status": "FIRST_PARTY_TEXT_REVIEWED",
                "provider_syntax_compatibility_observations": []
              }
            ],
            "provider_requests": 0,
            "provider_state": "NOT_AUTHORIZED",
            "publication_allowed": false,
            "publication_authorized": false,
            "remote_processing_allowed": false,
            "renderer_id": "sdc.visual-prompt-renderer",
            "renderer_version": "1.0.0",
            "retention_allowed": false,
            "source_revision": "sdc.adr-047-r4.cross-catalog-probe.first-party-fictional-test-only.1",
            "training_allowed": false,
            "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
          },
          "catalog_document_base_projection_rule": "FROZEN_ADR_040_CATALOG_PROJECTION_WITH_ONLY_CATALOG_VERSION_AND_SOURCE_REVISION_CHANGED",
          "catalog_document_bytes": 2656,
          "catalog_document_canonicalization": "UTF8_JSON_DUMPS_SORT_KEYS_TRUE_SEPARATORS_COMMA_COLON_ENSURE_ASCII_FALSE_ALLOW_NAN_FALSE_NO_BOM_NO_TERMINAL_LF",
          "catalog_document_raw_sha256": "bbbf2d1cdf993e14bd252baaf4547ba2e5c635a72eb47891f3695e20724201c5",
          "catalog_document_status": "FIRST_PARTY_FICTIONAL_TEST_ONLY",
          "catalog_sha256": "d02bf1e1a06da6f44fb57d3c998e349eefc32a3f00eb688c89c9c00a97a83178",
          "catalog_sha256_derivation": "SHA256(CATALOG_SHA256_DOMAIN_BYTES_THEN_CATALOG_DOCUMENT_CANONICAL_BYTES)",
          "catalog_sha256_domain_bytes": 29,
          "catalog_sha256_domain_hex": "7364633a76697375616c2d70726f6d70742d636174616c6f673a763100",
          "catalog_version": "1.0.1",
          "changed_fields_ledger": {
            "direct_mutations": [
              "supplied_bindings[1].role_binding_target.catalog_version",
              "supplied_bindings[1].role_binding_target.catalog_sha256"
            ],
            "every_other_field": "EXACTLY_PRESERVED_INCLUDING_TARGET_SHA256_BINDING_ID_AND_BINDING_SHA256"
          },
          "construction_kind": "TEST_SIDE_EXACT_TYPE_MODEL_COPY_NO_REVALIDATION_NO_IDENTITY_REHASH",
          "definition": "Replace only member ordinal 1 Catalog version/digest with the exact probe-local pair below and preserve every other field including all pre-mutation identities.",
          "derived_member_selection_ordinal": 1,
          "kind": "EXACT_RELATIONAL_VECTOR",
          "member_ordinal": 1,
          "member_ordinal_basis": "ZERO_BASED_SECOND_MEMBER",
          "must_differ_from_baseline_fixed_case_ids": [
            "character-same-status-record-v1",
            "scene-successor-reconciliation-v1"
          ],
          "probe_slug": "cross-catalog",
          "recomputed_identity_fields": [],
          "requested_reference_roles": [
            "SCENE_ESTABLISHING_REFERENCE",
            "SCENE_LIGHTING_REFERENCE"
          ],
          "selected_reference_role": "SCENE_LIGHTING_REFERENCE",
          "unchanged_tuple_rule": "MEMBER_0_AND_REQUESTED_REFERENCE_ROLES_EXACT_MEMBER_1_ALL_FIELDS_EXCEPT_TWO_DIRECT_CATALOG_MUTATIONS_EXACT",
          "vector_id": "cross-catalog-attack-v1::cross-catalog"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "cross-catalog",
        "scenario_id": "cross-catalog-attack-v1"
      },
      "cross-profile-attack-v1--001--cross-profile": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:COMMON_FRAME_MISMATCH",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Replace only member 1 Profile ID/version/digest from the other fixed case.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "cross-profile",
          "vector_id": "cross-profile-attack-v1::cross-profile"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "cross-profile",
        "scenario_id": "cross-profile-attack-v1"
      },
      "cross-purpose-attack-v1--001--character-target-scene-role": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:COMMON_FRAME_MISMATCH",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Combine a Character Binding and Scene Binding so asset_purpose is the first common-frame difference.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "character-target-scene-role",
          "vector_id": "cross-purpose-attack-v1::character-target-scene-role"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "character-target-scene-role",
        "scenario_id": "cross-purpose-attack-v1"
      },
      "cross-subject-attack-v1--001--cross-subject": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:COMMON_FRAME_MISMATCH",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Replace only member 1 subject_id from the other fixed case.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "cross-subject",
          "vector_id": "cross-subject-attack-v1::cross-subject"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "cross-subject",
        "scenario_id": "cross-subject-attack-v1"
      },
      "duplicate-binding-attack-v1--001--duplicate-binding-identity": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:DUPLICATE_ROLE_OR_BINDING",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Make member 1 reuse member 0 Binding ID and digest before requested-role processing.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "duplicate-binding-identity",
          "vector_id": "duplicate-binding-attack-v1::duplicate-binding-identity"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "duplicate-binding-identity",
        "scenario_id": "duplicate-binding-attack-v1"
      },
      "duplicate-role-attack-v1--001--duplicate-requested-role": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:DUPLICATE_ROLE_OR_BINDING",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Pass the Character identity role twice with two supplied positive Bindings.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "duplicate-requested-role",
          "vector_id": "duplicate-role-attack-v1::duplicate-requested-role"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "duplicate-requested-role",
        "scenario_id": "duplicate-role-attack-v1"
      },
      "equal-bytes-distinct-candidate-sidecar-occurrences-v1--001--equal-png-distinct-candidate-sidecar": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_EQUAL_PNG_PAIR_R3",
        "mutation_or_fault_vector": {
          "definition": "Use base and auxiliary Character occurrences: PNG anchors equal; Candidate, Sidecar and Binding identities distinct.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "equal-png-distinct-candidate-sidecar",
          "vector_id": "equal-bytes-distinct-candidate-sidecar-occurrences-v1::equal-png-distinct-candidate-sidecar"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "equal-png-distinct-candidate-sidecar",
        "scenario_id": "equal-bytes-distinct-candidate-sidecar-occurrences-v1"
      },
      "expired-qualification-manifest-v1--001--qualification-expired": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_UNREACHABLE:QUALIFICATION_FINAL_BOUND_EQUALITY_INDEPENDENT_REACH",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "conclusion": "request validity selects TIME_OR_VALIDITY_INVALID before the named final Qualification guard",
          "kind": "TIME_VALIDITY_DOMINANCE_PROOF",
          "named_bound": "qualification_valid_until",
          "premises": [
            "request_valid_until<=qualification_valid_until",
            "qualification_valid_until=set_at",
            "PUBLIC_FINALIZE requires set_at<request_valid_until before named final bound checks"
          ],
          "probe_slug": "qualification-expired",
          "vector_id": "expired-qualification-manifest-v1::qualification-expired"
        },
        "operation_id": "STRUCTURAL_TIME_VALIDITY_DOMINANCE_PROOF",
        "probe_slug": "qualification-expired",
        "scenario_id": "expired-qualification-manifest-v1"
      },
      "expired-qualification-manifest-v1--002--manifest-expired": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_UNREACHABLE:MANIFEST_FINAL_BOUND_EQUALITY_INDEPENDENT_REACH",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "conclusion": "request validity selects TIME_OR_VALIDITY_INVALID before the named final Manifest guard",
          "kind": "TIME_VALIDITY_DOMINANCE_PROOF",
          "named_bound": "manifest_valid_until",
          "premises": [
            "request_valid_until<=manifest_valid_until",
            "manifest_valid_until=set_at",
            "PUBLIC_FINALIZE requires set_at<request_valid_until before named final bound checks"
          ],
          "probe_slug": "manifest-expired",
          "vector_id": "expired-qualification-manifest-v1::manifest-expired"
        },
        "operation_id": "STRUCTURAL_TIME_VALIDITY_DOMINANCE_PROOF",
        "probe_slug": "manifest-expired",
        "scenario_id": "expired-qualification-manifest-v1"
      },
      "fail-over-indeterminate-v1--001--provider-boundary-fail-selection-indeterminate": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_ONLY_REJECT:NON_EXCLUSIVE_NO_PROVIDER_BOUNDARY_NOT_ACKNOWLEDGED:FAIL_OVER_INDETERMINATE",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set gate 10 INDETERMINATE and gate 11 FAIL with distinct fixed nonempty fictional bases.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "provider-boundary-fail-selection-indeterminate",
          "vector_id": "fail-over-indeterminate-v1::provider-boundary-fail-selection-indeterminate"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "provider-boundary-fail-selection-indeterminate",
        "scenario_id": "fail-over-indeterminate-v1"
      },
      "favorable-subset-attack-v1--001--omit-failed-member-from-original-request": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ROLE_SELECTION_INVALID",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Call finalization with the original three-role Request and omit the failed member.",
          "kind": "NO_FAVORABLE_REPAIR",
          "probe_slug": "omit-failed-member-from-original-request",
          "vector_id": "favorable-subset-attack-v1::omit-failed-member-from-original-request"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "omit-failed-member-from-original-request",
        "scenario_id": "favorable-subset-attack-v1"
      },
      "favorable-subset-attack-v1--002--replace-failed-member-on-original-request": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:DECISION_OR_SET_REVALIDATION_FAILED",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Keep the original Request, replace the failed member with one fixed distinct positive same-role occurrence and rebuild supplied Maker action for the replacement input.",
          "kind": "NO_FAVORABLE_REPAIR",
          "probe_slug": "replace-failed-member-on-original-request",
          "vector_id": "favorable-subset-attack-v1::replace-failed-member-on-original-request"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "replace-failed-member-on-original-request",
        "scenario_id": "favorable-subset-attack-v1"
      },
      "favorable-subset-attack-v1--003--attach-fabricated-subset-set-to-adverse-decision": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:DECISION_OR_SET_REVALIDATION_FAILED",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Call public finalization verifier with the exact adverse Decision and an exact-type fabricated positive subset Set attached.",
          "kind": "NO_FAVORABLE_REPAIR",
          "probe_slug": "attach-fabricated-subset-set-to-adverse-decision",
          "vector_id": "favorable-subset-attack-v1::attach-fabricated-subset-set-to-adverse-decision"
        },
        "operation_id": "PUBLIC_FINALIZATION_VERIFY",
        "probe_slug": "attach-fabricated-subset-set-to-adverse-decision",
        "scenario_id": "favorable-subset-attack-v1"
      },
      "final-expired-status-v1--001--final-expired": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:TIME_OR_VALIDITY_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set member 0 final status_valid_until equal to set_at.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "final-expired",
          "vector_id": "final-expired-status-v1::final-expired"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "final-expired",
        "scenario_id": "final-expired-status-v1"
      },
      "final-indeterminate-status-v1--001--final-indeterminate": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_ONLY_INDETERMINATE",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Rebuild member 0 final replay INDETERMINATE; all human gates PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "final-indeterminate",
          "vector_id": "final-indeterminate-status-v1::final-indeterminate"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "final-indeterminate",
        "scenario_id": "final-indeterminate-status-v1"
      },
      "final-primary-binding-drift-v1--001--final-active-binding-drift": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_ONLY_REJECT:COMMON_PRIMARY_BINDING_NO_LONGER_ACTIVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Keep the exact Request primary pair and supply the fixed active same-subject/purpose successor pair only at finalization.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "final-active-binding-drift",
          "vector_id": "final-primary-binding-drift-v1::final-active-binding-drift"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "final-active-binding-drift",
        "scenario_id": "final-primary-binding-drift-v1"
      },
      "final-revoked-held-status-v1--001--final-revoked": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_ONLY_REJECT:MEMBER_STATUS_NOT_CURRENT_AT_SET",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Rebuild member 0 final replay with the exact state named by probe_slug; all human gates PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "final-revoked",
          "vector_id": "final-revoked-held-status-v1::final-revoked"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "final-revoked",
        "scenario_id": "final-revoked-held-status-v1"
      },
      "final-revoked-held-status-v1--002--final-held": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_ONLY_REJECT:MEMBER_STATUS_NOT_CURRENT_AT_SET",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Rebuild member 0 final replay with the exact state named by probe_slug; all human gates PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "final-held",
          "vector_id": "final-revoked-held-status-v1::final-held"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "final-held",
        "scenario_id": "final-revoked-held-status-v1"
      },
      "final-stale-closure-attack-v1--001--stale-closure": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CURRENT_STATUS_REPLAY_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the final replay mutation named by probe_slug to member 0.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "stale-closure",
          "vector_id": "final-stale-closure-attack-v1::stale-closure"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "stale-closure",
        "scenario_id": "final-stale-closure-attack-v1"
      },
      "final-stale-closure-attack-v1--002--copied-receipt": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CURRENT_STATUS_REPLAY_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the final replay mutation named by probe_slug to member 0.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "copied-receipt",
          "vector_id": "final-stale-closure-attack-v1::copied-receipt"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "copied-receipt",
        "scenario_id": "final-stale-closure-attack-v1"
      },
      "final-stale-closure-attack-v1--003--copied-current": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CURRENT_STATUS_REPLAY_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the final replay mutation named by probe_slug to member 0.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "copied-current",
          "vector_id": "final-stale-closure-attack-v1::copied-current"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "copied-current",
        "scenario_id": "final-stale-closure-attack-v1"
      },
      "forbidden-identity-equality-v1--001--set-maker-selector": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "set-maker-selector",
          "vector_id": "forbidden-identity-equality-v1::set-maker-selector"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "set-maker-selector",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "forbidden-identity-equality-v1--002--qualification-qualifier": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "qualification-qualifier",
          "vector_id": "forbidden-identity-equality-v1::qualification-qualifier"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "qualification-qualifier",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "forbidden-identity-equality-v1--003--manifest-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "manifest-checker",
          "vector_id": "forbidden-identity-equality-v1::manifest-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "manifest-checker",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "forbidden-identity-equality-v1--004--promotion-request-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "promotion-request-status-checker",
          "vector_id": "forbidden-identity-equality-v1::promotion-request-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "promotion-request-status-checker",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "forbidden-identity-equality-v1--005--promotion-final-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "promotion-final-status-checker",
          "vector_id": "forbidden-identity-equality-v1::promotion-final-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "promotion-final-status-checker",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "forbidden-identity-equality-v1--006--promotion-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "promotion-checker",
          "vector_id": "forbidden-identity-equality-v1::promotion-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "promotion-checker",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "forbidden-identity-equality-v1--007--role-binding-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "role-binding-checker",
          "vector_id": "forbidden-identity-equality-v1::role-binding-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "role-binding-checker",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "forbidden-identity-equality-v1--008--role-binding-request-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "role-binding-request-status-checker",
          "vector_id": "forbidden-identity-equality-v1::role-binding-request-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "role-binding-request-status-checker",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "forbidden-identity-equality-v1--009--role-binding-final-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "role-binding-final-status-checker",
          "vector_id": "forbidden-identity-equality-v1::role-binding-final-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "role-binding-final-status-checker",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "forbidden-identity-equality-v1--010--set-request-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "set-request-status-checker",
          "vector_id": "forbidden-identity-equality-v1::set-request-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "set-request-status-checker",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "forbidden-identity-equality-v1--011--set-final-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_SEPARATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Checker identity equal to the exact member-0 actor named by probe_slug; rebuild only Checker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "set-final-status-checker",
          "vector_id": "forbidden-identity-equality-v1::set-final-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "set-final-status-checker",
        "scenario_id": "forbidden-identity-equality-v1"
      },
      "human-rights-fail-v1--001--rights-presentation-fail": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_ONLY_REJECT:PER_MEMBER_RIGHTS_PRESENTATION_NOT_ACKNOWLEDGED",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set human gate 9 FAIL with fixed nonempty fictional basis; gates 10/11 PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "rights-presentation-fail",
          "vector_id": "human-rights-fail-v1::rights-presentation-fail"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "rights-presentation-fail",
        "scenario_id": "human-rights-fail-v1"
      },
      "human-selection-fail-v1--001--selection-gate-fail": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_ONLY_REJECT:EXPLICIT_SELECTION_ORDER_AND_COVERAGE_NOT_ACKNOWLEDGED",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set human gate 10 FAIL with fixed nonempty fictional basis; gates 9/11 PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "selection-gate-fail",
          "vector_id": "human-selection-fail-v1::selection-gate-fail"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "selection-gate-fail",
        "scenario_id": "human-selection-fail-v1"
      },
      "human-selection-indeterminate-v1--001--selection-indeterminate": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_ONLY_INDETERMINATE",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set human gate 10 INDETERMINATE with fixed nonempty fictional basis; gates 9/11 PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "selection-indeterminate",
          "vector_id": "human-selection-indeterminate-v1::selection-indeterminate"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "selection-indeterminate",
        "scenario_id": "human-selection-indeterminate-v1"
      },
      "identity-record-invalid-v1--001--empty-object": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "compact_canonical_object": {},
          "kind": "SET_MAKER_IDENTITY_CANONICAL_OBJECT",
          "probe_slug": "empty-object",
          "terminal_lf": false,
          "vector_id": "identity-record-invalid-v1::empty-object"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "empty-object",
        "scenario_id": "identity-record-invalid-v1"
      },
      "identity-record-invalid-v1--002--missing-identity-ref": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "compact_canonical_object": {
            "document_profile": "sdc.privacy-minimized-human-reference.v1",
            "identity_namespace": "r3-reviewer"
          },
          "kind": "SET_MAKER_IDENTITY_CANONICAL_OBJECT",
          "probe_slug": "missing-identity-ref",
          "terminal_lf": false,
          "vector_id": "identity-record-invalid-v1::missing-identity-ref"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "missing-identity-ref",
        "scenario_id": "identity-record-invalid-v1"
      },
      "identity-record-invalid-v1--003--unknown-field": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "compact_canonical_object": {
            "document_profile": "sdc.privacy-minimized-human-reference.v1",
            "identity_namespace": "r3-reviewer",
            "identity_ref": "r3-maker",
            "x_r3_unknown": false
          },
          "kind": "SET_MAKER_IDENTITY_CANONICAL_OBJECT",
          "probe_slug": "unknown-field",
          "terminal_lf": false,
          "vector_id": "identity-record-invalid-v1::unknown-field"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "unknown-field",
        "scenario_id": "identity-record-invalid-v1"
      },
      "identity-record-invalid-v1--004--profile-mismatch": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "compact_canonical_object": {
            "document_profile": "x.r3.invalid",
            "identity_namespace": "r3-reviewer",
            "identity_ref": "r3-maker"
          },
          "kind": "SET_MAKER_IDENTITY_CANONICAL_OBJECT",
          "probe_slug": "profile-mismatch",
          "terminal_lf": false,
          "vector_id": "identity-record-invalid-v1::profile-mismatch"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "profile-mismatch",
        "scenario_id": "identity-record-invalid-v1"
      },
      "identity-record-invalid-v1--005--namespace-nonportable": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "compact_canonical_object": {
            "document_profile": "sdc.privacy-minimized-human-reference.v1",
            "identity_namespace": "",
            "identity_ref": "r3-maker"
          },
          "kind": "SET_MAKER_IDENTITY_CANONICAL_OBJECT",
          "probe_slug": "namespace-nonportable",
          "terminal_lf": false,
          "vector_id": "identity-record-invalid-v1::namespace-nonportable"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "namespace-nonportable",
        "scenario_id": "identity-record-invalid-v1"
      },
      "identity-record-invalid-v1--006--identity-ref-nonportable": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "compact_canonical_object": {
            "document_profile": "sdc.privacy-minimized-human-reference.v1",
            "identity_namespace": "r3-reviewer",
            "identity_ref": ""
          },
          "kind": "SET_MAKER_IDENTITY_CANONICAL_OBJECT",
          "probe_slug": "identity-ref-nonportable",
          "terminal_lf": false,
          "vector_id": "identity-record-invalid-v1::identity-ref-nonportable"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "identity-ref-nonportable",
        "scenario_id": "identity-record-invalid-v1"
      },
      "identity-record-invalid-v1--007--identity-ref-wrong-scalar": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:IDENTITY_RECORD_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "compact_canonical_object": {
            "document_profile": "sdc.privacy-minimized-human-reference.v1",
            "identity_namespace": "r3-reviewer",
            "identity_ref": 0
          },
          "kind": "SET_MAKER_IDENTITY_CANONICAL_OBJECT",
          "probe_slug": "identity-ref-wrong-scalar",
          "terminal_lf": false,
          "vector_id": "identity-record-invalid-v1::identity-ref-wrong-scalar"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "identity-ref-wrong-scalar",
        "scenario_id": "identity-record-invalid-v1"
      },
      "member-reorder-attack-v1--001--reversed-member-tuple": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CANONICAL_ORDER_INVALID",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Reverse the first two Scene Bindings while requested roles remain canonical.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "reversed-member-tuple",
          "vector_id": "member-reorder-attack-v1::reversed-member-tuple"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "reversed-member-tuple",
        "scenario_id": "member-reorder-attack-v1"
      },
      "omitted-branch-member-attack-v1--001--omitted-prior-target-branch": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CURRENT_STATUS_REPLAY_INVALID",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Remove the fixed predecessor target branch from member 0 Request replay.",
          "kind": "OMISSION",
          "probe_slug": "omitted-prior-target-branch",
          "vector_id": "omitted-branch-member-attack-v1::omitted-prior-target-branch"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "omitted-prior-target-branch",
        "scenario_id": "omitted-branch-member-attack-v1"
      },
      "omitted-branch-member-attack-v1--002--omitted-member-from-original-request": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ROLE_SELECTION_INVALID",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Call finalization with the original two-role Request and truncate the supplied members to ordinal 0.",
          "kind": "OMISSION",
          "probe_slug": "omitted-member-from-original-request",
          "vector_id": "omitted-branch-member-attack-v1::omitted-member-from-original-request"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "omitted-member-from-original-request",
        "scenario_id": "omitted-branch-member-attack-v1"
      },
      "ordinal-mutation-attack-v1--001--selection-ordinal-is-builder-owned": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_UNREACHABLE:CALLER_SUPPLIED_SELECTION_ORDINAL",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "conclusion": "caller-supplied ordinal cannot reach CANONICAL_ORDER_INVALID",
          "kind": "CALLER_SURFACE_PROOF",
          "premises": [
            "target builder accepts only exact positive Binding tuple and requested-role tuple",
            "selection_ordinal is generated by enumerate",
            "constructed invalid target is only admitted to public validation as CONTRACT_FIELD_INVALID"
          ],
          "probe_slug": "selection-ordinal-is-builder-owned",
          "vector_id": "ordinal-mutation-attack-v1::selection-ordinal-is-builder-owned"
        },
        "operation_id": "STRUCTURAL_ORDINAL_PROOF",
        "probe_slug": "selection-ordinal-is-builder-owned",
        "scenario_id": "ordinal-mutation-attack-v1"
      },
      "permitted-maker-overlap-v1--001--qualification-request-preparer": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "qualification-request-preparer",
          "vector_id": "permitted-maker-overlap-v1::qualification-request-preparer"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "qualification-request-preparer",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--002--qualification-qualifier": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "qualification-qualifier",
          "vector_id": "permitted-maker-overlap-v1::qualification-qualifier"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "qualification-qualifier",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--003--manifest-maker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "manifest-maker",
          "vector_id": "permitted-maker-overlap-v1::manifest-maker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "manifest-maker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--004--manifest-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "manifest-checker",
          "vector_id": "permitted-maker-overlap-v1::manifest-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "manifest-checker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--005--promotion-request-status-preparer": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "promotion-request-status-preparer",
          "vector_id": "permitted-maker-overlap-v1::promotion-request-status-preparer"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "promotion-request-status-preparer",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--006--promotion-request-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "promotion-request-status-checker",
          "vector_id": "permitted-maker-overlap-v1::promotion-request-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "promotion-request-status-checker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--007--promotion-final-status-preparer": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "promotion-final-status-preparer",
          "vector_id": "permitted-maker-overlap-v1::promotion-final-status-preparer"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "promotion-final-status-preparer",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--008--promotion-final-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "promotion-final-status-checker",
          "vector_id": "permitted-maker-overlap-v1::promotion-final-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "promotion-final-status-checker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--009--promotion-maker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "promotion-maker",
          "vector_id": "permitted-maker-overlap-v1::promotion-maker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "promotion-maker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--010--promotion-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "promotion-checker",
          "vector_id": "permitted-maker-overlap-v1::promotion-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "promotion-checker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--011--role-binding-request-status-preparer": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "role-binding-request-status-preparer",
          "vector_id": "permitted-maker-overlap-v1::role-binding-request-status-preparer"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "role-binding-request-status-preparer",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--012--role-binding-request-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "role-binding-request-status-checker",
          "vector_id": "permitted-maker-overlap-v1::role-binding-request-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "role-binding-request-status-checker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--013--role-binding-final-status-preparer": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "role-binding-final-status-preparer",
          "vector_id": "permitted-maker-overlap-v1::role-binding-final-status-preparer"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "role-binding-final-status-preparer",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--014--role-binding-final-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "role-binding-final-status-checker",
          "vector_id": "permitted-maker-overlap-v1::role-binding-final-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "role-binding-final-status-checker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--015--role-binding-maker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "role-binding-maker",
          "vector_id": "permitted-maker-overlap-v1::role-binding-maker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "role-binding-maker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--016--role-binding-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "role-binding-checker",
          "vector_id": "permitted-maker-overlap-v1::role-binding-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "role-binding-checker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--017--set-request-status-preparer": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "set-request-status-preparer",
          "vector_id": "permitted-maker-overlap-v1::set-request-status-preparer"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "set-request-status-preparer",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--018--set-request-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "set-request-status-checker",
          "vector_id": "permitted-maker-overlap-v1::set-request-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "set-request-status-checker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--019--set-final-status-preparer": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "set-final-status-preparer",
          "vector_id": "permitted-maker-overlap-v1::set-final-status-preparer"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "set-final-status-preparer",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "permitted-maker-overlap-v1--020--set-final-status-checker": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set Maker identity equal to the exact member-0 actor named by probe_slug; rebuild only Maker action.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "set-final-status-checker",
          "vector_id": "permitted-maker-overlap-v1::set-final-status-checker"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "set-final-status-checker",
        "scenario_id": "permitted-maker-overlap-v1"
      },
      "policy-identity-mismatch-v1--001--sealed-policy-no-caller-input": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_UNREACHABLE:POLICY_IDENTITY_MISMATCH",
        "input_anchor_id": "POLICY_R3",
        "mutation_or_fault_vector": {
          "kind": "SEALED_POLICY_PROOF",
          "premises": [
            "no public Policy argument",
            "Contract Policy fields are fixed literals",
            "compiled Policy ID/version/bytes/SHA self-check"
          ],
          "private_dynamic_or_human_substitution": false,
          "probe_slug": "sealed-policy-no-caller-input",
          "vector_id": "policy-identity-mismatch-v1::sealed-policy-no-caller-input"
        },
        "operation_id": "STRUCTURAL_POLICY_PROOF",
        "probe_slug": "sealed-policy-no-caller-input",
        "scenario_id": "policy-identity-mismatch-v1"
      },
      "positive-atomicity-injection-v1--001--positive-decision-without-set": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:DECISION_OR_SET_REVALIDATION_FAILED",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "construction": "exact GeneratedReferenceRoleBindingSetFinalizationResult instance assembled without invoking its guard",
          "decision": "positive",
          "kind": "INVALID_ATOMIC_PAIR",
          "probe_slug": "positive-decision-without-set",
          "role_binding_set": "None",
          "vector_id": "positive-atomicity-injection-v1::positive-decision-without-set"
        },
        "operation_id": "PUBLIC_FINALIZATION_VERIFY",
        "probe_slug": "positive-decision-without-set",
        "scenario_id": "positive-atomicity-injection-v1"
      },
      "positive-atomicity-injection-v1--002--adverse-decision-with-set": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:DECISION_OR_SET_REVALIDATION_FAILED",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "construction": "exact GeneratedReferenceRoleBindingSetFinalizationResult instance assembled without invoking its guard",
          "decision": "adverse",
          "kind": "INVALID_ATOMIC_PAIR",
          "probe_slug": "adverse-decision-with-set",
          "role_binding_set": "fixed exact positive Set",
          "vector_id": "positive-atomicity-injection-v1::adverse-decision-with-set"
        },
        "operation_id": "PUBLIC_FINALIZATION_VERIFY",
        "probe_slug": "adverse-decision-with-set",
        "scenario_id": "positive-atomicity-injection-v1"
      },
      "positive-atomicity-injection-v1--003--set-construction-failure": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "NO_RESULT_TYPED_ERROR:DECISION_OR_SET_REVALIDATION_FAILED",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "kind": "TEST_LOCAL_SET_CONSTRUCTION_FAULT",
          "message": "injected exact R3 Set construction failure",
          "patch_target": "sdc.generated_reference_role_binding_set._build_identity",
          "post_restore_positive_bytes_equal": true,
          "probe_slug": "set-construction-failure",
          "raise_type": "ValueError",
          "trigger_exact_model_type": "CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetV1",
          "vector_id": "positive-atomicity-injection-v1::set-construction-failure"
        },
        "operation_id": "HERMETIC_SET_CONSTRUCTION",
        "probe_slug": "set-construction-failure",
        "scenario_id": "positive-atomicity-injection-v1"
      },
      "prohibited-authority-injection-v1--001--final-only-status-input-at-request": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:PROHIBITED_BOUNDARY_CONNECTION",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "field": "members[0].set_final_status",
          "kind": "REQUEST_FINAL_ONLY_INPUT",
          "probe_slug": "final-only-status-input-at-request",
          "value": "EXACT_NON_NONE_FIXED_FINAL_STATUS",
          "vector_id": "prohibited-authority-injection-v1::final-only-status-input-at-request"
        },
        "operation_id": "PUBLIC_REVIEW_PAYLOAD",
        "probe_slug": "final-only-status-input-at-request",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--002--provider": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "provider",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "provider",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::provider"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "provider",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--003--input-material": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "input-material",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "input-material",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::input-material"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "input-material",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--004--provider-request": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "provider-request",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "provider-request",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::provider-request"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "provider-request",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--005--runtime": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "runtime",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "runtime",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::runtime"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "runtime",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--006--url": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "url",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "url",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::url"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "url",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--007--slot": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "slot",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "slot",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::slot"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "slot",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--008--order": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "order",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "order",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::order"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "order",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--009--idempotency": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "idempotency",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "idempotency",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::idempotency"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "idempotency",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--010--credential": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "credential",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "credential",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::credential"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "credential",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--011--cost": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "cost",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "cost",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::cost"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "cost",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--012--retry": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "retry",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "retry",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::retry"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "retry",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--013--publication": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "publication",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "publication",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::publication"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "publication",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--014--retention": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "retention",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "retention",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::retention"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "retention",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "prohibited-authority-injection-v1--015--training": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_PUBLIC_SURFACE_ABSENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "allow_exact_zero_boundary_fields_and_tokens": true,
          "capability": "training",
          "kind": "NONEXECUTING_AUTHORITY_SURFACE_PROOF",
          "probe_slug": "training",
          "prove_absent": [
            "authority-bearing public parameter",
            "authority-bearing return",
            "production import or call",
            "positive executable value"
          ],
          "vector_id": "prohibited-authority-injection-v1::training"
        },
        "operation_id": "STRUCTURAL_AUTHORITY_PROOF",
        "probe_slug": "training",
        "scenario_id": "prohibited-authority-injection-v1"
      },
      "raw-media-mismatch-v1--001--whole-png-mutation-dominated-by-promotion": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_UNREACHABLE:WHOLE_PNG_MUTATION_REACHES_SET_RAW_MEDIA",
        "input_anchor_id": "CHARACTER_EQUAL_PNG_PAIR_R3",
        "mutation_or_fault_vector": {
          "conclusion": "whole-PNG change fails Promotion closure before Set RAW mapping",
          "kind": "RAW_MEDIA_DOMINANCE_PROOF",
          "premise": "ADR045_PREDECESSOR_DOMINANCE",
          "probe_slug": "whole-png-mutation-dominated-by-promotion",
          "vector_id": "raw-media-mismatch-v1::whole-png-mutation-dominated-by-promotion"
        },
        "operation_id": "STRUCTURAL_RAW_MEDIA_DOMINANCE_PROOF",
        "probe_slug": "whole-png-mutation-dominated-by-promotion",
        "scenario_id": "raw-media-mismatch-v1"
      },
      "raw-media-mismatch-v1--002--size-anchor-mutation-dominated-by-adr046": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_UNREACHABLE:SIZE_ANCHOR_MUTATION_REACHES_SET_RAW_MEDIA",
        "input_anchor_id": "CHARACTER_EQUAL_PNG_PAIR_R3",
        "mutation_or_fault_vector": {
          "conclusion": "size anchor change fails ADR046 formal/rebuild before Set RAW mapping",
          "kind": "RAW_MEDIA_DOMINANCE_PROOF",
          "premise": "ADR046_FORMAL_REBUILD_DOMINANCE",
          "probe_slug": "size-anchor-mutation-dominated-by-adr046",
          "vector_id": "raw-media-mismatch-v1::size-anchor-mutation-dominated-by-adr046"
        },
        "operation_id": "STRUCTURAL_RAW_MEDIA_DOMINANCE_PROOF",
        "probe_slug": "size-anchor-mutation-dominated-by-adr046",
        "scenario_id": "raw-media-mismatch-v1"
      },
      "raw-media-mismatch-v1--003--content-sha256-mutation-dominated-by-adr046": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_UNREACHABLE:CONTENT_SHA256_MUTATION_REACHES_SET_RAW_MEDIA",
        "input_anchor_id": "CHARACTER_EQUAL_PNG_PAIR_R3",
        "mutation_or_fault_vector": {
          "conclusion": "content SHA change fails ADR046 formal/rebuild before Set RAW mapping",
          "kind": "RAW_MEDIA_DOMINANCE_PROOF",
          "premise": "ADR046_FORMAL_REBUILD_DOMINANCE",
          "probe_slug": "content-sha256-mutation-dominated-by-adr046",
          "vector_id": "raw-media-mismatch-v1::content-sha256-mutation-dominated-by-adr046"
        },
        "operation_id": "STRUCTURAL_RAW_MEDIA_DOMINANCE_PROOF",
        "probe_slug": "content-sha256-mutation-dominated-by-adr046",
        "scenario_id": "raw-media-mismatch-v1"
      },
      "raw-media-mismatch-v1--004--admitted-png-construction-failure-unreachable": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_UNREACHABLE:SET_ADMITTED_PNG_CONSTRUCTION_FAILURE",
        "input_anchor_id": "CHARACTER_EQUAL_PNG_PAIR_R3",
        "mutation_or_fault_vector": {
          "conclusion": "Set derives raw size/SHA and accepts only a syntactically valid target technical SHA, so constructor failure is unreachable after preflight",
          "kind": "RAW_MEDIA_DOMINANCE_PROOF",
          "premise": "SET_DERIVATION_PROOF",
          "probe_slug": "admitted-png-construction-failure-unreachable",
          "vector_id": "raw-media-mismatch-v1::admitted-png-construction-failure-unreachable"
        },
        "operation_id": "STRUCTURAL_RAW_MEDIA_DOMINANCE_PROOF",
        "probe_slug": "admitted-png-construction-failure-unreachable",
        "scenario_id": "raw-media-mismatch-v1"
      },
      "raw-media-mismatch-v1--005--technical-record-anchor-mismatch": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RAW_MEDIA_MISMATCH",
        "input_anchor_id": "CHARACTER_EQUAL_PNG_PAIR_R3",
        "mutation_or_fault_vector": {
          "field": "role_binding_request.requested_role_binding_target.media_technical_record_sha256",
          "kind": "PUBLIC_ADR046_TECHNICAL_ANCHOR_MUTATION",
          "probe_slug": "technical-record-anchor-mismatch",
          "reanchor": "exact ADR046 Request self identity",
          "retained": "verified Promotion Sidecar technical record",
          "value": "1111111111111111111111111111111111111111111111111111111111111111",
          "vector_id": "raw-media-mismatch-v1::technical-record-anchor-mismatch"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "technical-record-anchor-mismatch",
        "scenario_id": "raw-media-mismatch-v1"
      },
      "raw-media-mismatch-v1--006--request-png-plus-post-png-dual-fault": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:RAW_MEDIA_MISMATCH",
        "input_anchor_id": "CHARACTER_EQUAL_PNG_PAIR_R3",
        "mutation_or_fault_vector": {
          "adr046_order_anchor": "tests/test_generated_reference_role_binding.py::test_representative_promotion_png_role_primary_status_stage_priority",
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "ADR046_DELEGATED_PNG_DUAL_FAULT",
          "later_fault": "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID by Scene-lighting role on Character purpose",
          "probe_slug": "request-png-plus-post-png-dual-fault",
          "selected_fault": "GeneratedReferenceRoleBindingError:PNG_ADMISSION_INVALID",
          "vector_id": "raw-media-mismatch-v1::request-png-plus-post-png-dual-fault"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "request-png-plus-post-png-dual-fault",
        "scenario_id": "raw-media-mismatch-v1"
      },
      "raw-media-mismatch-v1--007--finalization-png-plus-post-png-dual-fault": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:RAW_MEDIA_MISMATCH",
        "input_anchor_id": "CHARACTER_EQUAL_PNG_PAIR_R3",
        "mutation_or_fault_vector": {
          "adr046_order_anchor": "tests/test_generated_reference_role_binding.py::test_representative_promotion_png_role_primary_status_stage_priority",
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "ADR046_DELEGATED_PNG_DUAL_FAULT",
          "later_fault": "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID by Scene-lighting role on Character purpose",
          "probe_slug": "finalization-png-plus-post-png-dual-fault",
          "selected_fault": "GeneratedReferenceRoleBindingError:PNG_ADMISSION_INVALID",
          "vector_id": "raw-media-mismatch-v1::finalization-png-plus-post-png-dual-fault"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "finalization-png-plus-post-png-dual-fault",
        "scenario_id": "raw-media-mismatch-v1"
      },
      "request-expired-status-v1--001--request-expired": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:TIME_OR_VALIDITY_INVALID",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Set member 0 Request status_valid_until equal to requested_at.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "request-expired",
          "vector_id": "request-expired-status-v1::request-expired"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "request-expired",
        "scenario_id": "request-expired-status-v1"
      },
      "request-non-current-status-v1--001--request-revoked": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:REQUEST_MEMBER_STATUS_NOT_CURRENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Rebuild member 0 Request replay with the exact state named by probe_slug.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "request-revoked",
          "vector_id": "request-non-current-status-v1::request-revoked"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "request-revoked",
        "scenario_id": "request-non-current-status-v1"
      },
      "request-non-current-status-v1--002--request-held": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:REQUEST_MEMBER_STATUS_NOT_CURRENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Rebuild member 0 Request replay with the exact state named by probe_slug.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "request-held",
          "vector_id": "request-non-current-status-v1::request-held"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "request-held",
        "scenario_id": "request-non-current-status-v1"
      },
      "request-non-current-status-v1--003--request-indeterminate": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:REQUEST_MEMBER_STATUS_NOT_CURRENT",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Rebuild member 0 Request replay with the exact state named by probe_slug.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "request-indeterminate",
          "vector_id": "request-non-current-status-v1::request-indeterminate"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "request-indeterminate",
        "scenario_id": "request-non-current-status-v1"
      },
      "request-primary-binding-attack-v1--001--final-cross-subject-purpose-primary": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:PRIMARY_BINDING_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "final_primary_pair": "FIXED_SCENE_PAIR_CROSS_SUBJECT_OR_PURPOSE",
          "kind": "FINAL_PRIMARY_PAIR_REPLACEMENT",
          "probe_slug": "final-cross-subject-purpose-primary",
          "request": "ORIGINAL_EXACT_CHARACTER_REQUEST",
          "requested_primary_pair": "ORIGINAL_CHARACTER_PAIR",
          "vector_id": "request-primary-binding-attack-v1::final-cross-subject-purpose-primary"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "final-cross-subject-purpose-primary",
        "scenario_id": "request-primary-binding-attack-v1"
      },
      "request-stale-closure-attack-v1--001--stale-closure": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CURRENT_STATUS_REPLAY_INVALID",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the Request replay mutation named by probe_slug to member 0.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "stale-closure",
          "vector_id": "request-stale-closure-attack-v1::stale-closure"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "stale-closure",
        "scenario_id": "request-stale-closure-attack-v1"
      },
      "request-stale-closure-attack-v1--002--copied-receipt": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CURRENT_STATUS_REPLAY_INVALID",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the Request replay mutation named by probe_slug to member 0.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "copied-receipt",
          "vector_id": "request-stale-closure-attack-v1::copied-receipt"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "copied-receipt",
        "scenario_id": "request-stale-closure-attack-v1"
      },
      "request-stale-closure-attack-v1--003--copied-current": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:CURRENT_STATUS_REPLAY_INVALID",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the Request replay mutation named by probe_slug to member 0.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "copied-current",
          "vector_id": "request-stale-closure-attack-v1::copied-current"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "copied-current",
        "scenario_id": "request-stale-closure-attack-v1"
      },
      "resource-limit-exceeded-v1--001--member-count-1-admit": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "human_gates": "ALL_PASS",
          "kind": "RESOURCE_EXECUTION",
          "members": 1,
          "probe_slug": "member-count-1-admit",
          "vector_id": "resource-limit-exceeded-v1::member-count-1-admit"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "member-count-1-admit",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--002--member-count-4-admit": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "human_gates": "ALL_PASS",
          "kind": "RESOURCE_EXECUTION",
          "members": 4,
          "probe_slug": "member-count-4-admit",
          "vector_id": "resource-limit-exceeded-v1::member-count-4-admit"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "member-count-4-admit",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--003--member-count-5-error": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RESOURCE_LIMIT_EXCEEDED",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "kind": "RESOURCE_EXECUTION",
          "members": 5,
          "probe_slug": "member-count-5-error",
          "vector_id": "resource-limit-exceeded-v1::member-count-5-error"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "member-count-5-error",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--004--per-member-png-exact-cap-guard-admit": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "RESOURCE_GUARD_ADMITTED_THEN_TYPED_ERROR:UPSTREAM_CLOSURE_MISMATCH",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "guard": "ADMIT",
          "kind": "GUARD_THEN_ERROR",
          "members": 1,
          "next_fixed_fault": "ADR045_PREDECESSOR_LINK_DRIFT",
          "png": "fixed first-party fictional in-memory PNG; no path",
          "png_bytes_each": 67108864,
          "probe_slug": "per-member-png-exact-cap-guard-admit",
          "vector_id": "resource-limit-exceeded-v1::per-member-png-exact-cap-guard-admit"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "per-member-png-exact-cap-guard-admit",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--005--aggregate-png-exact-cap-guard-admit": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "RESOURCE_GUARD_ADMITTED_THEN_TYPED_ERROR:UPSTREAM_CLOSURE_MISMATCH",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "guard": "ADMIT",
          "kind": "GUARD_THEN_ERROR",
          "logical_aggregate_png_bytes": 268435456,
          "members": 4,
          "next_fixed_fault": "ADR045_PREDECESSOR_LINK_DRIFT",
          "occurrences_count_independently": true,
          "png": "fixed first-party fictional in-memory PNG; no path",
          "probe_slug": "aggregate-png-exact-cap-guard-admit",
          "shared_immutable_png_bytes": 67108864,
          "vector_id": "resource-limit-exceeded-v1::aggregate-png-exact-cap-guard-admit"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "aggregate-png-exact-cap-guard-admit",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--006--per-member-png-cap-plus-1-error": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RESOURCE_LIMIT_EXCEEDED",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "kind": "RESOURCE_EXECUTION",
          "members": 1,
          "png_bytes_each": 67108865,
          "probe_slug": "per-member-png-cap-plus-1-error",
          "vector_id": "resource-limit-exceeded-v1::per-member-png-cap-plus-1-error"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "per-member-png-cap-plus-1-error",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--007--aggregate-png-strict-exceed-dominated": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_UNREACHABLE:AGGREGATE_PNG_STRICT_EXCEED",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "equation": "4*67108864=268435456",
          "kind": "DOMINANCE_PROOF",
          "premises": [
            "members<=4",
            "PNG bytes/member<=67108864"
          ],
          "probe_slug": "aggregate-png-strict-exceed-dominated",
          "rejection_operator": ">",
          "vector_id": "resource-limit-exceeded-v1::aggregate-png-strict-exceed-dominated"
        },
        "operation_id": "STRUCTURAL_RESOURCE_DOMINANCE_PROOF",
        "probe_slug": "aggregate-png-strict-exceed-dominated",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--008--raw-leaf-count-1780-guard-admit": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "RESOURCE_GUARD_ADMITTED_THEN_TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "closed_filler_construction": "FOUR_FIRST_PARTY_FICTIONAL_IN_MEMORY_MEMBER_CLOSURES_PLUS_THE_FOUR_SET_LEVEL_MAKER_CHECKER_IDENTITY_ACTION_RECORDS_POPULATE_EVERY_FROZEN_RAW_LEAF_OWNER_SLOT_TO_EXACTLY_1780_OCCURRENCES_WITH_EACH_BYTES_VALUE_NONEMPTY_AND_AT_OR_BELOW_ITS_OWNER_MAXIMUM",
          "expected_nested_code": "INPUT_DOCUMENT_INVALID",
          "expected_nested_type": "GeneratedReferenceRoleBindingError",
          "field": "members[0].role_binding_maker_identity_bytes",
          "fill_byte_hex": "78",
          "guard": "ADMIT",
          "kind": "GUARD_THEN_ERROR",
          "next_fixed_fault": "ADR046_REQUEST_RETAINED_MAKER_IDENTITY_DOCUMENT_INVALID_BEFORE_PROMOTION_OR_STATUS_REPLAY",
          "probe_slug": "raw-leaf-count-1780-guard-admit",
          "raw_leaf_occurrences": 1780,
          "replacement_size_bytes": 1,
          "vector_id": "resource-limit-exceeded-v1::raw-leaf-count-1780-guard-admit"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "raw-leaf-count-1780-guard-admit",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--009--aggregate-raw-exact-cap-guard-admit": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "RESOURCE_GUARD_ADMITTED_THEN_TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "closed_filler_construction": "FOUR_FIRST_PARTY_FICTIONAL_IN_MEMORY_MEMBER_CLOSURES_PLUS_THE_FOUR_SET_LEVEL_MAKER_CHECKER_IDENTITY_ACTION_RECORDS_POPULATE_ALL_1780_FROZEN_RAW_LEAF_OWNER_SLOTS_AND_SET_EACH_BYTES_VALUE_TO_ITS_EXACT_OWNER_MAXIMUM_SO_THE_LOGICAL_SUM_IS_EXACTLY_512524288",
          "expected_nested_code": "INPUT_DOCUMENT_INVALID",
          "expected_nested_type": "GeneratedReferenceRoleBindingError",
          "field": "members[0].role_binding_maker_identity_bytes",
          "fill_byte_hex": "78",
          "guard": "ADMIT",
          "kind": "GUARD_THEN_ERROR",
          "logical_aggregate_raw_bytes": 512524288,
          "next_fixed_fault": "ADR046_REQUEST_RETAINED_MAKER_IDENTITY_DOCUMENT_INVALID_BEFORE_PROMOTION_OR_STATUS_REPLAY",
          "probe_slug": "aggregate-raw-exact-cap-guard-admit",
          "replacement_size_bytes": 16384,
          "vector_id": "resource-limit-exceeded-v1::aggregate-raw-exact-cap-guard-admit"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "aggregate-raw-exact-cap-guard-admit",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--010--raw-leaf-count-1781-error": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RESOURCE_LIMIT_EXCEEDED",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "construction": "add exact eleventh Qualification evidence leaf within the closed four-member process graph",
          "kind": "RESOURCE_EXECUTION",
          "probe_slug": "raw-leaf-count-1781-error",
          "raw_leaf_occurrences": 1781,
          "vector_id": "resource-limit-exceeded-v1::raw-leaf-count-1781-error"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "raw-leaf-count-1781-error",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--011--aggregate-raw-strict-exceed-dominated": {
        "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
        "expected_outcome": "PROVED_UNREACHABLE:AGGREGATE_RAW_STRICT_EXCEED",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "kind": "DOMINANCE_PROOF",
          "maximum_logical_raw_bytes": 512524288,
          "premises": [
            "all 1780 owner slots closed",
            "every leaf at or below exact owner maximum"
          ],
          "probe_slug": "aggregate-raw-strict-exceed-dominated",
          "rejection_operator": ">",
          "vector_id": "resource-limit-exceeded-v1::aggregate-raw-strict-exceed-dominated"
        },
        "operation_id": "STRUCTURAL_RESOURCE_DOMINANCE_PROOF",
        "probe_slug": "aggregate-raw-strict-exceed-dominated",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--012--semantic-capsules-31-admit": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "callgraph_ledger": "frozen positive finalization verifier",
          "human_gates": "ALL_PASS",
          "kind": "RESOURCE_EXECUTION",
          "members": 4,
          "probe_slug": "semantic-capsules-31-admit",
          "semantic_capsules": 31,
          "vector_id": "resource-limit-exceeded-v1::semantic-capsules-31-admit"
        },
        "operation_id": "PUBLIC_FINALIZATION_VERIFY",
        "probe_slug": "semantic-capsules-31-admit",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "resource-limit-exceeded-v1--013--maker-action-bytes-cap-plus-1-error": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RESOURCE_LIMIT_EXCEEDED",
        "input_anchor_id": "RESOURCE_IN_MEMORY_R3",
        "mutation_or_fault_vector": {
          "field": "set_maker_action_bytes",
          "kind": "RESOURCE_EXECUTION",
          "probe_slug": "maker-action-bytes-cap-plus-1-error",
          "size_bytes": 262145,
          "vector_id": "resource-limit-exceeded-v1::maker-action-bytes-cap-plus-1-error"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "maker-action-bytes-cap-plus-1-error",
        "scenario_id": "resource-limit-exceeded-v1"
      },
      "role-binding-finalization-invalid-v1--001--positive-binding-rebuild-drift": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "exact_outer_process_types_retained": true,
          "field": "role_binding_result.decision.decision_sha256",
          "kind": "ADR046_EXPECTED_RESULT_TAMPER",
          "probe_slug": "positive-binding-rebuild-drift",
          "value": "0000000000000000000000000000000000000000000000000000000000000000",
          "vector_id": "role-binding-finalization-invalid-v1::positive-binding-rebuild-drift"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "positive-binding-rebuild-drift",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--002--role-binding-code-request-input-resource-limit-exceeded": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-input-resource-limit-exceeded",
          "raise_code": "INPUT_RESOURCE_LIMIT_EXCEEDED",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-input-resource-limit-exceeded"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-input-resource-limit-exceeded",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--003--role-binding-code-request-input-document-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-input-document-invalid",
          "raise_code": "INPUT_DOCUMENT_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-input-document-invalid"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-input-document-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--004--role-binding-code-request-contract-field-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-contract-field-invalid",
          "raise_code": "CONTRACT_FIELD_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-contract-field-invalid"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-contract-field-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--005--role-binding-code-request-policy-identity-mismatch": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-policy-identity-mismatch",
          "raise_code": "POLICY_IDENTITY_MISMATCH",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-policy-identity-mismatch"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-policy-identity-mismatch",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--006--role-binding-code-request-formal-identity-mismatch": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-formal-identity-mismatch",
          "raise_code": "FORMAL_IDENTITY_MISMATCH",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-formal-identity-mismatch"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-formal-identity-mismatch",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--007--role-binding-code-request-upstream-closure-mismatch": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-upstream-closure-mismatch",
          "raise_code": "UPSTREAM_CLOSURE_MISMATCH",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-upstream-closure-mismatch"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-upstream-closure-mismatch",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--008--role-binding-code-request-promotion-closure-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-promotion-closure-invalid",
          "raise_code": "PROMOTION_CLOSURE_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-promotion-closure-invalid"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-promotion-closure-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--009--role-binding-code-request-role-purpose-or-membership-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-role-purpose-or-membership-invalid",
          "raise_code": "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-role-purpose-or-membership-invalid"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-role-purpose-or-membership-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--010--role-binding-code-request-primary-asset-binding-closure-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-primary-asset-binding-closure-invalid",
          "raise_code": "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-primary-asset-binding-closure-invalid"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-primary-asset-binding-closure-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--011--role-binding-code-request-current-status-replay-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-current-status-replay-invalid",
          "raise_code": "CURRENT_STATUS_REPLAY_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-current-status-replay-invalid"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-current-status-replay-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--012--role-binding-code-request-rights-scope-mismatch": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-rights-scope-mismatch",
          "raise_code": "RIGHTS_SCOPE_MISMATCH",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-rights-scope-mismatch"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-rights-scope-mismatch",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--013--role-binding-code-request-role-separation-violation": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-role-separation-violation",
          "raise_code": "ROLE_SEPARATION_VIOLATION",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-role-separation-violation"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-role-separation-violation",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--014--role-binding-code-request-action-record-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-action-record-invalid",
          "raise_code": "ACTION_RECORD_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-action-record-invalid"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-action-record-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--015--role-binding-code-request-time-or-validity-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-time-or-validity-invalid",
          "raise_code": "TIME_OR_VALIDITY_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-time-or-validity-invalid"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-time-or-validity-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--016--role-binding-code-request-authority-surface-nonzero": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-authority-surface-nonzero",
          "raise_code": "AUTHORITY_SURFACE_NONZERO",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-authority-surface-nonzero"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-authority-surface-nonzero",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--017--role-binding-code-request-prohibited-boundary-connection": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-prohibited-boundary-connection",
          "raise_code": "PROHIBITED_BOUNDARY_CONNECTION",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-prohibited-boundary-connection"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-prohibited-boundary-connection",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--018--role-binding-code-request-binding-gate-not-pass": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-binding-gate-not-pass",
          "raise_code": "BINDING_GATE_NOT_PASS",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-binding-gate-not-pass"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-binding-gate-not-pass",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--019--role-binding-code-request-atomic-output-invariant-violation": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-request-atomic-output-invariant-violation",
          "raise_code": "ATOMIC_OUTPUT_INVARIANT_VIOLATION",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-request-atomic-output-invariant-violation"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-request-atomic-output-invariant-violation",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--020--role-binding-code-finalization-input-resource-limit-exceeded": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-input-resource-limit-exceeded",
          "raise_code": "INPUT_RESOURCE_LIMIT_EXCEEDED",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-input-resource-limit-exceeded"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-input-resource-limit-exceeded",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--021--role-binding-code-finalization-input-document-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-input-document-invalid",
          "raise_code": "INPUT_DOCUMENT_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-input-document-invalid"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-input-document-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--022--role-binding-code-finalization-contract-field-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-contract-field-invalid",
          "raise_code": "CONTRACT_FIELD_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-contract-field-invalid"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-contract-field-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--023--role-binding-code-finalization-policy-identity-mismatch": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-policy-identity-mismatch",
          "raise_code": "POLICY_IDENTITY_MISMATCH",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-policy-identity-mismatch"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-policy-identity-mismatch",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--024--role-binding-code-finalization-formal-identity-mismatch": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-formal-identity-mismatch",
          "raise_code": "FORMAL_IDENTITY_MISMATCH",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-formal-identity-mismatch"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-formal-identity-mismatch",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--025--role-binding-code-finalization-upstream-closure-mismatch": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-upstream-closure-mismatch",
          "raise_code": "UPSTREAM_CLOSURE_MISMATCH",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-upstream-closure-mismatch"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-upstream-closure-mismatch",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--026--role-binding-code-finalization-promotion-closure-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-promotion-closure-invalid",
          "raise_code": "PROMOTION_CLOSURE_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-promotion-closure-invalid"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-promotion-closure-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--027--role-binding-code-finalization-role-purpose-or-membership-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-role-purpose-or-membership-invalid",
          "raise_code": "ROLE_PURPOSE_OR_MEMBERSHIP_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-role-purpose-or-membership-invalid"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-role-purpose-or-membership-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--028--role-binding-code-finalization-primary-asset-binding-closure-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-primary-asset-binding-closure-invalid",
          "raise_code": "PRIMARY_ASSET_BINDING_CLOSURE_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-primary-asset-binding-closure-invalid"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-primary-asset-binding-closure-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--029--role-binding-code-finalization-current-status-replay-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-current-status-replay-invalid",
          "raise_code": "CURRENT_STATUS_REPLAY_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-current-status-replay-invalid"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-current-status-replay-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--030--role-binding-code-finalization-rights-scope-mismatch": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-rights-scope-mismatch",
          "raise_code": "RIGHTS_SCOPE_MISMATCH",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-rights-scope-mismatch"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-rights-scope-mismatch",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--031--role-binding-code-finalization-role-separation-violation": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-role-separation-violation",
          "raise_code": "ROLE_SEPARATION_VIOLATION",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-role-separation-violation"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-role-separation-violation",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--032--role-binding-code-finalization-action-record-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-action-record-invalid",
          "raise_code": "ACTION_RECORD_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-action-record-invalid"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-action-record-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--033--role-binding-code-finalization-time-or-validity-invalid": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-time-or-validity-invalid",
          "raise_code": "TIME_OR_VALIDITY_INVALID",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-time-or-validity-invalid"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-time-or-validity-invalid",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--034--role-binding-code-finalization-authority-surface-nonzero": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-authority-surface-nonzero",
          "raise_code": "AUTHORITY_SURFACE_NONZERO",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-authority-surface-nonzero"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-authority-surface-nonzero",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--035--role-binding-code-finalization-prohibited-boundary-connection": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-prohibited-boundary-connection",
          "raise_code": "PROHIBITED_BOUNDARY_CONNECTION",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-prohibited-boundary-connection"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-prohibited-boundary-connection",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--036--role-binding-code-finalization-binding-gate-not-pass": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-binding-gate-not-pass",
          "raise_code": "BINDING_GATE_NOT_PASS",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-binding-gate-not-pass"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-binding-gate-not-pass",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--037--role-binding-code-finalization-atomic-output-invariant-violation": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 typed verifier failure",
          "probe_slug": "role-binding-code-finalization-atomic-output-invariant-violation",
          "raise_code": "ATOMIC_OUTPUT_INVARIANT_VIOLATION",
          "raise_type": "GeneratedReferenceRoleBindingError",
          "vector_id": "role-binding-finalization-invalid-v1::role-binding-code-finalization-atomic-output-invariant-violation"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "role-binding-code-finalization-atomic-output-invariant-violation",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--038--status-error-type-request-generatedreferenceasofassessmenterror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-request-generatedreferenceasofassessmenterror",
          "raise_code": "AS_OF_CONTRACT_INVALID",
          "raise_type": "GeneratedReferenceAsOfAssessmentError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-request-generatedreferenceasofassessmenterror"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "status-error-type-request-generatedreferenceasofassessmenterror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--039--status-error-type-request-generatedreferencechaincoverageerror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-request-generatedreferencechaincoverageerror",
          "raise_code": "CHAIN_COLLECTION_CONTRACT_INVALID",
          "raise_type": "GeneratedReferenceChainCoverageError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-request-generatedreferencechaincoverageerror"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "status-error-type-request-generatedreferencechaincoverageerror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--040--status-error-type-request-generatedreferencechainreplayerror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-request-generatedreferencechainreplayerror",
          "raise_code": "COUNT_OUT_OF_RANGE",
          "raise_type": "GeneratedReferenceChainReplayError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-request-generatedreferencechainreplayerror"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "status-error-type-request-generatedreferencechainreplayerror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--041--status-error-type-request-generatedreferencejointreplayerror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-request-generatedreferencejointreplayerror",
          "raise_code": "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
          "raise_type": "GeneratedReferenceJointReplayError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-request-generatedreferencejointreplayerror"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "status-error-type-request-generatedreferencejointreplayerror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--042--status-error-type-request-generatedreferencereceipterror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-request-generatedreferencereceipterror",
          "raise_code": "RECEIPT_CONTRACT_INVALID",
          "raise_type": "GeneratedReferenceReceiptError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-request-generatedreferencereceipterror"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "status-error-type-request-generatedreferencereceipterror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--043--status-error-type-request-generatedreferencerightscurrentstatuserror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-request-generatedreferencerightscurrentstatuserror",
          "raise_code": "EXACT_INPUT_TYPE_REQUIRED",
          "raise_type": "GeneratedReferenceRightsCurrentStatusError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-request-generatedreferencerightscurrentstatuserror"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "status-error-type-request-generatedreferencerightscurrentstatuserror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--044--status-error-type-finalization-generatedreferenceasofassessmenterror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-finalization-generatedreferenceasofassessmenterror",
          "raise_code": "AS_OF_CONTRACT_INVALID",
          "raise_type": "GeneratedReferenceAsOfAssessmentError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-finalization-generatedreferenceasofassessmenterror"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "status-error-type-finalization-generatedreferenceasofassessmenterror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--045--status-error-type-finalization-generatedreferencechaincoverageerror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-finalization-generatedreferencechaincoverageerror",
          "raise_code": "CHAIN_COLLECTION_CONTRACT_INVALID",
          "raise_type": "GeneratedReferenceChainCoverageError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-finalization-generatedreferencechaincoverageerror"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "status-error-type-finalization-generatedreferencechaincoverageerror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--046--status-error-type-finalization-generatedreferencechainreplayerror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-finalization-generatedreferencechainreplayerror",
          "raise_code": "COUNT_OUT_OF_RANGE",
          "raise_type": "GeneratedReferenceChainReplayError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-finalization-generatedreferencechainreplayerror"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "status-error-type-finalization-generatedreferencechainreplayerror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--047--status-error-type-finalization-generatedreferencejointreplayerror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-finalization-generatedreferencejointreplayerror",
          "raise_code": "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
          "raise_type": "GeneratedReferenceJointReplayError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-finalization-generatedreferencejointreplayerror"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "status-error-type-finalization-generatedreferencejointreplayerror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--048--status-error-type-finalization-generatedreferencereceipterror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-finalization-generatedreferencereceipterror",
          "raise_code": "RECEIPT_CONTRACT_INVALID",
          "raise_type": "GeneratedReferenceReceiptError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-finalization-generatedreferencereceipterror"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "status-error-type-finalization-generatedreferencereceipterror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--049--status-error-type-finalization-generatedreferencerightscurrentstatuserror": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 status verifier failure",
          "probe_slug": "status-error-type-finalization-generatedreferencerightscurrentstatuserror",
          "raise_code": "EXACT_INPUT_TYPE_REQUIRED",
          "raise_type": "GeneratedReferenceRightsCurrentStatusError",
          "vector_id": "role-binding-finalization-invalid-v1::status-error-type-finalization-generatedreferencerightscurrentstatuserror"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "status-error-type-finalization-generatedreferencerightscurrentstatuserror",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--050--decision-sha256-target": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "behavior": {
            "return": "0000000000000000000000000000000000000000000000000000000000000000"
          },
          "call_count": 1,
          "kind": "TEST_LOCAL_IMPORTED_HELPER_FAULT",
          "patch_target": "sdc.generated_reference_role_binding_set.creative_sample_generated_reference_eligible_asset_role_binding_decision_sha256",
          "probe_slug": "decision-sha256-target",
          "vector_id": "role-binding-finalization-invalid-v1::decision-sha256-target"
        },
        "operation_id": "HERMETIC_ROLE_HELPER_REVALIDATION",
        "probe_slug": "decision-sha256-target",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--051--request-sha256-target": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "behavior": {
            "return": "0000000000000000000000000000000000000000000000000000000000000000"
          },
          "call_count": 1,
          "kind": "TEST_LOCAL_IMPORTED_HELPER_FAULT",
          "patch_target": "sdc.generated_reference_role_binding_set.creative_sample_generated_reference_eligible_asset_role_binding_request_sha256",
          "probe_slug": "request-sha256-target",
          "vector_id": "role-binding-finalization-invalid-v1::request-sha256-target"
        },
        "operation_id": "HERMETIC_ROLE_HELPER_REVALIDATION",
        "probe_slug": "request-sha256-target",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--052--binding-sha256-target": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "behavior": {
            "return": "0000000000000000000000000000000000000000000000000000000000000000"
          },
          "call_count": 1,
          "kind": "TEST_LOCAL_IMPORTED_HELPER_FAULT",
          "patch_target": "sdc.generated_reference_role_binding_set.creative_sample_generated_reference_eligible_asset_role_binding_sha256",
          "probe_slug": "binding-sha256-target",
          "vector_id": "role-binding-finalization-invalid-v1::binding-sha256-target"
        },
        "operation_id": "HERMETIC_ROLE_HELPER_REVALIDATION",
        "probe_slug": "binding-sha256-target",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--053--contract-document-bytes-target": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "behavior": {
            "message": "injected exact R3 contract-document revalidation failure",
            "raise_code": "FORMAL_IDENTITY_MISMATCH",
            "raise_type": "GeneratedReferenceRoleBindingError"
          },
          "call_count": 1,
          "kind": "TEST_LOCAL_IMPORTED_HELPER_FAULT",
          "patch_target": "sdc.generated_reference_role_binding_set.generated_reference_role_binding_contract_document_bytes",
          "probe_slug": "contract-document-bytes-target",
          "vector_id": "role-binding-finalization-invalid-v1::contract-document-bytes-target"
        },
        "operation_id": "HERMETIC_ROLE_HELPER_REVALIDATION",
        "probe_slug": "contract-document-bytes-target",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-binding-finalization-invalid-v1--054--target-sha256-target": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:ROLE_BINDING_FINALIZATION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "behavior": {
            "return": "0000000000000000000000000000000000000000000000000000000000000000"
          },
          "call_count": 1,
          "kind": "TEST_LOCAL_IMPORTED_HELPER_FAULT",
          "patch_target": "sdc.generated_reference_role_binding_set.generated_reference_role_binding_target_sha256",
          "probe_slug": "target-sha256-target",
          "vector_id": "role-binding-finalization-invalid-v1::target-sha256-target"
        },
        "operation_id": "HERMETIC_ROLE_HELPER_REVALIDATION",
        "probe_slug": "target-sha256-target",
        "scenario_id": "role-binding-finalization-invalid-v1"
      },
      "role-selection-invalid-v1--001--empty-requested-subset": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ROLE_SELECTION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Invoke target builder with exactly the requested-role mutation named by probe_slug and otherwise positive Bindings.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "empty-requested-subset",
          "vector_id": "role-selection-invalid-v1::empty-requested-subset"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "empty-requested-subset",
        "scenario_id": "role-selection-invalid-v1"
      },
      "role-selection-invalid-v1--002--outside-purpose-role": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ROLE_SELECTION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Invoke target builder with exactly the requested-role mutation named by probe_slug and otherwise positive Bindings.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "outside-purpose-role",
          "vector_id": "role-selection-invalid-v1::outside-purpose-role"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "outside-purpose-role",
        "scenario_id": "role-selection-invalid-v1"
      },
      "role-selection-invalid-v1--003--binding-count-role-count-mismatch": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:ROLE_SELECTION_INVALID",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Invoke target builder with exactly the requested-role mutation named by probe_slug and otherwise positive Bindings.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "binding-count-role-count-mismatch",
          "vector_id": "role-selection-invalid-v1::binding-count-role-count-mismatch"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "binding-count-role-count-mismatch",
        "scenario_id": "role-selection-invalid-v1"
      },
      "same-sidecar-cross-role-distinct-bindings-v1--001--same-sidecar-two-roles-distinct-bindings": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Use one exact Sidecar occurrence for two Character roles through distinct positive Binding identities.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "same-sidecar-two-roles-distinct-bindings",
          "vector_id": "same-sidecar-cross-role-distinct-bindings-v1::same-sidecar-two-roles-distinct-bindings"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "same-sidecar-two-roles-distinct-bindings",
        "scenario_id": "same-sidecar-cross-role-distinct-bindings-v1"
      },
      "scene-full-positive-v1--001--scene-cardinality-4-full": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Finalize the exact four-role Scene tuple in canonical order with all human gates PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "scene-cardinality-4-full",
          "vector_id": "scene-full-positive-v1::scene-cardinality-4-full"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "scene-cardinality-4-full",
        "scenario_id": "scene-full-positive-v1"
      },
      "scene-partial-positive-v1--001--scene-cardinality-3-partial": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Finalize the exact first three Scene roles/members in canonical order with all human gates PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "scene-cardinality-3-partial",
          "vector_id": "scene-partial-positive-v1::scene-cardinality-3-partial"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "scene-cardinality-3-partial",
        "scenario_id": "scene-partial-positive-v1"
      },
      "scene-singleton-positive-v1--001--scene-cardinality-1": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "DECISION_AND_SET_APPROVE",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Finalize the exact first Scene role/member with all human gates PASS.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "scene-cardinality-1",
          "vector_id": "scene-singleton-positive-v1::scene-cardinality-1"
        },
        "operation_id": "PUBLIC_FINALIZE",
        "probe_slug": "scene-cardinality-1",
        "scenario_id": "scene-singleton-positive-v1"
      },
      "unequal-rights-attack-v1--001--substituted": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RIGHTS_SCOPE_MISMATCH",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the rights-scope relation named by probe_slug to member 1; retain every other common-frame value.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "substituted",
          "vector_id": "unequal-rights-attack-v1::substituted"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "substituted",
        "scenario_id": "unequal-rights-attack-v1"
      },
      "unequal-rights-attack-v1--002--expanded": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RIGHTS_SCOPE_MISMATCH",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the rights-scope relation named by probe_slug to member 1; retain every other common-frame value.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "expanded",
          "vector_id": "unequal-rights-attack-v1::expanded"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "expanded",
        "scenario_id": "unequal-rights-attack-v1"
      },
      "unequal-rights-attack-v1--003--narrowed": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RIGHTS_SCOPE_MISMATCH",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the rights-scope relation named by probe_slug to member 1; retain every other common-frame value.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "narrowed",
          "vector_id": "unequal-rights-attack-v1::narrowed"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "narrowed",
        "scenario_id": "unequal-rights-attack-v1"
      },
      "unequal-rights-attack-v1--004--reordered": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RIGHTS_SCOPE_MISMATCH",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the rights-scope relation named by probe_slug to member 1; retain every other common-frame value.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "reordered",
          "vector_id": "unequal-rights-attack-v1::reordered"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "reordered",
        "scenario_id": "unequal-rights-attack-v1"
      },
      "unequal-rights-attack-v1--005--renewed": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RIGHTS_SCOPE_MISMATCH",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the rights-scope relation named by probe_slug to member 1; retain every other common-frame value.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "renewed",
          "vector_id": "unequal-rights-attack-v1::renewed"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "renewed",
        "scenario_id": "unequal-rights-attack-v1"
      },
      "unequal-rights-attack-v1--006--unioned": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RIGHTS_SCOPE_MISMATCH",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the rights-scope relation named by probe_slug to member 1; retain every other common-frame value.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "unioned",
          "vector_id": "unequal-rights-attack-v1::unioned"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "unioned",
        "scenario_id": "unequal-rights-attack-v1"
      },
      "unequal-rights-attack-v1--007--intersected": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:RIGHTS_SCOPE_MISMATCH",
        "input_anchor_id": "SCENE_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "definition": "Apply only the rights-scope relation named by probe_slug to member 1; retain every other common-frame value.",
          "kind": "EXACT_RELATIONAL_VECTOR",
          "probe_slug": "intersected",
          "vector_id": "unequal-rights-attack-v1::intersected"
        },
        "operation_id": "PUBLIC_TARGET_BUILD",
        "probe_slug": "intersected",
        "scenario_id": "unequal-rights-attack-v1"
      },
      "upstream-closure-mismatch-v1--001--promotion-maker-action-canonical-drift": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:UPSTREAM_CLOSURE_MISMATCH",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "expected_nested_code": "UPSTREAM_CLOSURE_MISMATCH",
          "expected_nested_type": "GeneratedReferenceAssetPromotionError",
          "field": "role_binding_promotion_closure.maker_action_bytes",
          "kind": "PROMOTION_ACTION_PERSISTENT_CANONICAL_TARGET_DRIFT",
          "mutation_steps": [
            "decode the exact baseline Promotion Maker action object",
            "replace only promotion_review_payload_sha256 with 64 lower-case zero characters",
            "re-encode with ADR-045 persistent canonical JSON: UTF-8, sorted keys, two-space indent and exactly one terminal LF"
          ],
          "probe_slug": "promotion-maker-action-canonical-drift",
          "replacement_value": "0000000000000000000000000000000000000000000000000000000000000000",
          "vector_id": "upstream-closure-mismatch-v1::promotion-maker-action-canonical-drift"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "promotion-maker-action-canonical-drift",
        "scenario_id": "upstream-closure-mismatch-v1"
      },
      "upstream-closure-mismatch-v1--002--promotion-checker-action-canonical-drift": {
        "evidence_kind": "PUBLIC_API_EXECUTION",
        "expected_outcome": "TYPED_ERROR:UPSTREAM_CLOSURE_MISMATCH",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "expected_nested_code": "UPSTREAM_CLOSURE_MISMATCH",
          "expected_nested_type": "GeneratedReferenceAssetPromotionError",
          "field": "role_binding_promotion_closure.checker_action_bytes",
          "kind": "PROMOTION_ACTION_PERSISTENT_CANONICAL_TARGET_DRIFT",
          "mutation_steps": [
            "decode the exact baseline Promotion Checker action object",
            "replace only request_sha256 with 64 lower-case zero characters",
            "re-encode with ADR-045 persistent canonical JSON: UTF-8, sorted keys, two-space indent and exactly one terminal LF"
          ],
          "probe_slug": "promotion-checker-action-canonical-drift",
          "replacement_value": "0000000000000000000000000000000000000000000000000000000000000000",
          "vector_id": "upstream-closure-mismatch-v1::promotion-checker-action-canonical-drift"
        },
        "operation_id": "PUBLIC_REQUEST_PREPARE",
        "probe_slug": "promotion-checker-action-canonical-drift",
        "scenario_id": "upstream-closure-mismatch-v1"
      },
      "upstream-closure-mismatch-v1--003--promotion-error-at-request-verifier": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:UPSTREAM_CLOSURE_MISMATCH",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "request",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 Promotion closure failure",
          "probe_slug": "promotion-error-at-request-verifier",
          "raise_code": "UPSTREAM_CLOSURE_MISMATCH",
          "raise_type": "GeneratedReferenceAssetPromotionError",
          "vector_id": "upstream-closure-mismatch-v1::promotion-error-at-request-verifier"
        },
        "operation_id": "HERMETIC_REQUEST_ROLE_VERIFIER",
        "probe_slug": "promotion-error-at-request-verifier",
        "scenario_id": "upstream-closure-mismatch-v1"
      },
      "upstream-closure-mismatch-v1--004--promotion-error-at-finalization-verifier": {
        "evidence_kind": "HERMETIC_TEST_ONLY_FAULT_INJECTION",
        "expected_outcome": "TYPED_ERROR:UPSTREAM_CLOSURE_MISMATCH",
        "input_anchor_id": "CHARACTER_PRIMARY_R3",
        "mutation_or_fault_vector": {
          "automatic_restore": true,
          "call_count": 1,
          "call_site": "finalization",
          "kind": "TEST_LOCAL_TYPED_FAULT",
          "message": "injected exact R3 Promotion closure failure",
          "probe_slug": "promotion-error-at-finalization-verifier",
          "raise_code": "UPSTREAM_CLOSURE_MISMATCH",
          "raise_type": "GeneratedReferenceAssetPromotionError",
          "vector_id": "upstream-closure-mismatch-v1::promotion-error-at-finalization-verifier"
        },
        "operation_id": "HERMETIC_FINAL_ROLE_VERIFIER",
        "probe_slug": "promotion-error-at-finalization-verifier",
        "scenario_id": "upstream-closure-mismatch-v1"
      }
    },
    "spec_closure_rule": "The key set of probe_spec_by_id must equal the 217 IDs expanded from known_answer_probe_ledger in scenario/family/axis order. Each record repeats exact scenario_id, probe_slug, evidence_kind and expected_outcome; names one catalog input and operation; and owns one probe-local vector. Missing, extra, duplicate or mismatched records stop BUILD. No selector, scenario-level expected_error_code or free-text mapping DSL is evaluated."
  },
  "known_answer_scenario_count": 48,
  "known_answer_scenario_id_order": [
    "character-singleton-positive-v1",
    "character-partial-positive-v1",
    "character-full-positive-v1",
    "scene-singleton-positive-v1",
    "scene-partial-positive-v1",
    "scene-full-positive-v1",
    "same-sidecar-cross-role-distinct-bindings-v1",
    "equal-bytes-distinct-candidate-sidecar-occurrences-v1",
    "duplicate-role-attack-v1",
    "duplicate-binding-attack-v1",
    "member-reorder-attack-v1",
    "ordinal-mutation-attack-v1",
    "cross-purpose-attack-v1",
    "cross-artifact-attack-v1",
    "cross-profile-attack-v1",
    "cross-catalog-attack-v1",
    "cross-subject-attack-v1",
    "request-primary-binding-attack-v1",
    "final-primary-binding-drift-v1",
    "unequal-rights-attack-v1",
    "request-stale-closure-attack-v1",
    "request-expired-status-v1",
    "request-non-current-status-v1",
    "final-stale-closure-attack-v1",
    "final-expired-status-v1",
    "final-revoked-held-status-v1",
    "final-indeterminate-status-v1",
    "expired-qualification-manifest-v1",
    "omitted-branch-member-attack-v1",
    "favorable-subset-attack-v1",
    "forbidden-identity-equality-v1",
    "permitted-maker-overlap-v1",
    "human-rights-fail-v1",
    "human-selection-indeterminate-v1",
    "fail-over-indeterminate-v1",
    "positive-atomicity-injection-v1",
    "prohibited-authority-injection-v1",
    "resource-limit-exceeded-v1",
    "canonical-document-invalid-v1",
    "contract-field-invalid-v1",
    "policy-identity-mismatch-v1",
    "upstream-closure-mismatch-v1",
    "role-binding-finalization-invalid-v1",
    "role-selection-invalid-v1",
    "raw-media-mismatch-v1",
    "identity-record-invalid-v1",
    "action-record-invalid-v1",
    "human-selection-fail-v1"
  ],
  "known_answer_structural_unreachability_rules": {
    "aggregate_raw_bytes_strict_exceed": {
      "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
      "premises": [
        "closed raw-leaf owners and counts",
        "each leaf at or below exact owner maximum",
        "sum of all owner maxima=512524288",
        "rejection_operator=>"
      ],
      "proof": "Strict aggregate exceed must first violate a narrower owner/count bound.",
      "required_public_boundary_probe": "resource-limit-exceeded-v1--009--aggregate-raw-exact-cap-guard-admit"
    },
    "aggregate_supplied_png_strict_exceed": {
      "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
      "premises": [
        "member_count<=4",
        "each_member_png_bytes<=67108864",
        "aggregate_limit=268435456",
        "rejection_operator=>"
      ],
      "proof": "4*67108864=268435456; strict exceed cannot survive the per-member limit.",
      "required_public_boundary_probe": "resource-limit-exceeded-v1--005--aggregate-png-exact-cap-guard-admit"
    },
    "caller_supplied_selection_ordinal": {
      "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
      "proof": "Target builder owns selection_ordinal through enumerate; no caller ordinal parameter exists. Invalid constructed targets reach public validation as CONTRACT_FIELD_INVALID.",
      "required_public_order_probe": "member-reorder-attack-v1--001--reversed-member-tuple"
    },
    "policy_identity_mismatch": {
      "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
      "human_acceptance_substitution_allowed": false,
      "private_or_dynamic_execution_allowed": false,
      "proof": "No public Policy argument exists; Contract Policy fields are fixed literals; module ID, version, canonical bytes and SHA are compiled and self-checked."
    },
    "qualification_manifest_final_guard_dominance": {
      "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
      "premises": [
        "request_valid_until is the per-member minimum of requested_at plus 86400 seconds, qualification_valid_until, manifest_valid_until and request_status_valid_until",
        "PUBLIC_FINALIZE requires requested_at<=set_at<request_valid_until before reading final Qualification, Manifest or status bounds",
        "setting the named Qualification or Manifest bound equal to set_at implies request_valid_until<=set_at"
      ],
      "proof": "The Request half-open validity guard deterministically returns TIME_OR_VALIDITY_INVALID before either named final bound guard; matching error-code equality is not evidence that the named final guard ran.",
      "required_probe_ids": [
        "expired-qualification-manifest-v1--001--qualification-expired",
        "expired-qualification-manifest-v1--002--manifest-expired"
      ]
    },
    "raw_media_direct_mutations": {
      "evidence_kind": "STRUCTURAL_UNREACHABILITY_PROOF",
      "proof": "Whole-PNG mutation is selected by ADR-045 predecessor verification; size/content target mutations are selected by ADR-046 formal/rebuild verification; Set derives admitted raw size/SHA and receives a syntactically valid technical SHA after preflight. These four structures cannot independently reach Set RAW_MEDIA_MISMATCH.",
      "required_public_mapping_probe": "raw-media-mismatch-v1--005--technical-record-anchor-mismatch"
    }
  },
  "known_answer_test_only_fault_injection_rule": {
    "allowed_path": "tests/test_generated_reference_role_binding_set.py",
    "codegen_or_fixture_private_access_allowed": false,
    "production_factory_callback_or_seam_allowed": false,
    "rule": "PYTEST_MONKEYPATCH_CONTEXT_AUTOMATICALLY_RESTORES_EXACT_MODULE_LOCAL_BUILD_IDENTITY_BINDING_WRAPPER_DELEGATES_ALL_CALLS_EXCEPT_MODEL_TYPE_EXACTLY_CREATIVE_SAMPLE_GENERATED_REFERENCE_ELIGIBLE_ASSET_ROLE_BINDING_SET_V1_WHERE_ONE_FIXED_VALUE_ERROR_IS_RAISED_AFTER_DECISION_CONSTRUCTION_PUBLIC_FINALIZER_MAPS_TO_DECISION_OR_SET_REVALIDATION_FAILED_NO_RESULT_OR_PLACEHOLDER_ESCAPES_CALL_COUNT_EXACT_RESTORED_POSITIVE_DECISION_AND_SET_FORMAL_BYTES_EQUAL_BASELINE"
  },
  "member_cardinality": {
    "CHARACTER_REFERENCE_ASSET": [
      1,
      3
    ],
    "SCENE_REFERENCE_ASSET": [
      1,
      4
    ]
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
  "policy_version": "1.4.0",
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

The canonical compact UTF-8 `json.dumps` encoding of the exact JSON object above uses
`sort_keys=True`, separators `,` and `:`, `ensure_ascii=False` and `allow_nan=False`, with no BOM and
no terminal LF. Its accepted R5 byte count and raw SHA-256 are:

```text
policy_document_bytes=234946
policy_document_sha256=e2b9aacd7eb3de7e54c238b5d698e7a5abf48fee2931300576309eec4ec5dac0
```

The Policy ID remains
`sdc.generated-reference-bounded-supplied-role-binding-set-policy`; the Accepted R5 version is
exactly `1.4.0`. Accepted R4 remains the historical `1.3.0`, 233,029 compact bytes and
`5186be89ed0de72dac55ae7f363291225998a41dd7082a12db848c914152dce8`. Accepted R3 remains the
historical `1.2.0`, 227,888 compact bytes and
`4075b6e0bb6a5a5c1e2f949bfd640f94eda974c3f09987e56820a787dda7a308`. Accepted R2 remains the
historical `1.1.0`, 38,481 compact bytes and
`77bdbb2f8845af02ab72e70ad1c74276e218f27410ff4384547d3868ec1a8c9e`. Accepted R1 remains the
historical `1.0.0`, 28,797 compact bytes and
`7b22f26df2a6ab31ee45e8a10dc83c56e22a065d87ee099ef3e678d72511f1d6`. No historical policy is
relabelled. If Accepted R5 is later separately implemented, a Request, Decision or
Set carrying any historical version or digest would fail the exact current policy-identity gate.
The R5 digest cannot be invented during BUILD or derived from a runtime serializer.

## Accepted R5 complete known-answer evidence model

The `known_answer_scenario_id_order` and `known_answer_probe_ledger` inside the accepted policy are
the authoritative ordered ledger. Accepted R5 preserves every Accepted R4
scenario and probe identity; the
first 37 scenario IDs remain byte-for-byte and ordinal-exact, followed by the same R3-appended IDs
in this order:

```text
38 resource-limit-exceeded-v1
39 canonical-document-invalid-v1
40 contract-field-invalid-v1
41 policy-identity-mismatch-v1
42 upstream-closure-mismatch-v1
43 role-binding-finalization-invalid-v1
44 role-selection-invalid-v1
45 raw-media-mismatch-v1
46 identity-record-invalid-v1
47 action-record-invalid-v1
48 human-selection-fail-v1
```

The ledger expands to exactly 217 required evidence units:

```text
PUBLIC_API_EXECUTION=135
HERMETIC_TEST_ONLY_FAULT_INJECTION=58
STRUCTURAL_UNREACHABILITY_PROOF=24
required_evidence_unit_count=217
declared_scenario_count=48
evidence_complete_scenario_count=48
```

One evidence unit is exactly one independent public invocation, one isolated typed-fault vector or
one closed structural proof. Every source probe must have its own stable `probe_id`, operation,
evidence kind, input byte anchor or exact mutation/fault vector and complete tagged expected
outcome. Every derived probe must add the actual outcome or proof object, relevant byte/source/test
anchors and its semantic SHA-256. A scenario is evidence-complete only when every required expanded
probe is present and satisfied. No scenario-level `expected_error_code`, aggregate `executable`
boolean or shared outcome may stand in for multiple probes.

The Policy's `known_answer_probe_spec_catalog` closes the ledger rather than leaving BUILD to choose
evidence. Its exact `probe_spec_by_id` key set equals all 217 IDs expanded from the 48 scenarios and
binds each ID directly to one catalog input, one exact public operation, test-local call site or
proof operation, one probe-local relational mutation or typed fault and one tagged outcome. The literal probe ID uses the exact ASCII
formula frozen by `known_answer_probe_rule`; axis components use one hyphen and the scenario-local
ordinal uses exactly three zero-padded digits. No selector or mini-DSL is interpreted. Any missing,
extra or mismatched keyed spec, invalid axis character, slug collision or full probe-ID collision
stops BUILD.

The catalog input IDs freeze the two released support cases, the one new in-memory equal-PNG case,
their exact role tuples and the one source-fixture path. A future R5 BUILD must add the newly
generated source path/size/SHA-256 and semantic identities to every copied input anchor. That later
byte anchoring is mechanical evidence, not permission to select a different input or vector. The
current R2 source fixture remains an exact 30,668-byte /
`f27d6dd3ccf03b405f4fffd35ea7af7a83e2c2ebe18c33e726b49d911cf7bb76` construction baseline only;
it is not relabelled as an R3, R4 or R5 generated-fixture byte anchor.

### Accepted R5 time-validity dominance and capsule-verifier evidence

The two expired-bound probes retain their scenario/probe IDs, order and Character input anchor but
become separate structural families. For each valid member Request:

For the exact strings retained in the Policy rule, `per-member minimum` means the one Request-wide
minimum over the Request lifetime and every member's Qualification, Manifest and Request-status
bounds, not one independently stored minimum per member. The phrase `before reading final
Qualification, Manifest or status bounds` is a guard-stage label meaning before evaluating the named
final-bound comparisons; it does not assert that fresh Request reconstruction avoids reading those
same fields while recomputing the Request-wide minimum.

```text
request_valid_until <= qualification_valid_until
request_valid_until <= manifest_valid_until
PUBLIC_FINALIZE requires set_at < request_valid_until before named final-bound checks
named-bound equality requires qualification_valid_until = set_at
                       or manifest_valid_until = set_at
therefore set_at < request_valid_until <= named_bound = set_at is impossible
```

The conclusion is limited to independent reach of the named final Qualification or Manifest guard.
The earlier Request-validity guard remains publicly reachable and may return the same
`TIME_OR_VALIDITY_INVALID` code, but that equality of code is not evidence that either later named
guard ran. No private model mutation, invalid upstream closure, alternate fixed support case or
Human assertion may substitute for the two exact structural proofs.

The 31-capsule positive probe remains a public execution, but it invokes the exact released
finalization verifier rather than the finalizer builder. The frozen ownership equations are:

```text
PUBLIC_FINALIZE: C01..C09 + 4 * (M01..M05) = 29
PUBLIC_FINALIZATION_VERIFY positive: C01..C11 + 4 * (M01..M05) = 31
```

The exact R5 operation ledger is:

```text
HERMETIC_FINAL_ROLE_VERIFIER=26
HERMETIC_REQUEST_ROLE_VERIFIER=26
HERMETIC_ROLE_HELPER_REVALIDATION=5
HERMETIC_SET_CONSTRUCTION=1
PUBLIC_FINALIZATION_VERIFY=4
PUBLIC_FINALIZE=67
PUBLIC_REQUEST_PREPARE=38
PUBLIC_REVIEW_PAYLOAD=2
PUBLIC_TARGET_BUILD=24
STRUCTURAL_AUTHORITY_PROOF=14
STRUCTURAL_ORDINAL_PROOF=1
STRUCTURAL_POLICY_PROOF=1
STRUCTURAL_RAW_MEDIA_DOMINANCE_PROOF=4
STRUCTURAL_RESOURCE_DOMINANCE_PROOF=2
STRUCTURAL_TIME_VALIDITY_DOMINANCE_PROOF=2
```

These 15 operation counts sum to the same 217 evidence units. The 21-code error ledger and five-code
issue ledger retain their exact row order; only the `TIME_OR_VALIDITY_INVALID` row drops the expired-
bound scenario and consequently retains two executable units rather than four. No expected outcome
is inferred or shared at scenario scope.

### Accepted R4 cross-Catalog probe execution

The Accepted R4 cross-Catalog probe remains one public Target-build execution over
`SCENE_PRIMARY_R3`; Accepted R5 does not change its vector and does not create another input-anchor
category. A future separately authorized R5 BUILD would have to:

1. reconstruct the two exact positive Scene Bindings through the same released support callables;
2. prove that both released fixed cases and Scene member ordinals 0 and 1 carry the frozen baseline
   Catalog pair `1.0.0` /
   `cbf0e0baa8ca1bc63f8643b6e9f0982134a9bf2386e8d8c1db8adc31e7cf2fc2`;
3. take the complete Catalog projection only from this probe's Policy vector, canonicalize it by the
   exact recorded codec, verify 2,656 bytes and raw SHA-256
   `bbbf2d1cdf993e14bd252baaf4547ba2e5c635a72eb47891f3695e20724201c5`, then verify the exact
   29-byte Catalog domain and semantic digest
   `d02bf1e1a06da6f44fb57d3c998e349eefc32a3f00eb688c89c9c00a97a83178`;
4. require the resulting version/digest pair to differ from both released fixed-case identities;
5. create one exact-type test-side shallow model copy that changes only supplied Binding tuple index
   1's two Catalog fields, performs no validation and no identity rehash, and proves `target_sha256`,
   `binding_id`, `binding_sha256`, member 0, the requested-role tuple and every other field remain
   equal to the baseline values;
6. invoke `build_generated_reference_eligible_asset_role_binding_set_target` once and require exact
   typed `COMMON_FRAME_MISMATCH`; and
7. retain in the derived evidence descriptor the complete vector, baseline comparisons, canonical
   document byte/hash checks, changed-field ledger and actual typed result.

This deliberate adversarial copy exercises the public Target builder's frozen order: common-frame
comparison precedes downstream formal-identity revalidation, so the required first result is
`COMMON_FRAME_MISMATCH`. It is not a valid positive Binding construction, a hermetic fault
injection or a production construction seam.

No codegen constant outside the Policy/source vector may supply the mutation. No source-fixture
input category, sixth anchor, support callable, production parameter, callback, private/dynamic
lookup, filesystem Catalog path or network input is permitted.

The exact 21-row error-code ledger follows the existing Set error priority. The exact five-row issue
ledger follows the final gate/issue order. Every row points to at least one exact scenario whose
probes carry the relevant tagged outcome. `human-selection-indeterminate-v1` remains a pure
INDETERMINATE Decision without a FAIL issue. `fail-over-indeterminate-v1` retains FAIL priority, and
the new `human-selection-fail-v1` supplies the previously absent
`EXPLICIT_SELECTION_ORDER_AND_COVERAGE_NOT_ACKNOWLEDGED` FAIL issue.

Unknown or future ADR-046 error codes are deliberately outside the 217-unit closed-outcome ledger.
Two mandatory hermetic conformance tests, one at each exact verifier call site, must prove they stop
as a module compatibility error. They may never be guessed, mapped to a portable Set code or counted
as known-answer evidence.

### Structural unreachability evidence

`POLICY_IDENTITY_MISMATCH` is a sealed integrity guard, not a caller-selected scenario input. Public
APIs have no Policy parameter; Contract Policy fields are fixed literals; and the module validates
its compiled Policy ID, version, canonical bytes and digest. Its evidence unit must therefore bind
the exact public signatures, Contract literals, module call graph, source Git blob and exact frozen
Policy bytes/hash in one structural proof. Private mutation, dynamic access or Human acceptance may
not substitute for that proof or be described as public execution.

The two final Qualification/Manifest equality probes are also structurally unreachable at their
named final guards. `request_valid_until` is the minimum of the Request lifetime and all applicable
Qualification, Manifest and Request-status bounds, while the public finalizer checks
`set_at < request_valid_until` before reading any named final bound. Setting either named bound equal
to `set_at` therefore guarantees the Request guard wins. The two independently identified proof
units retain their exact vectors and must bind the exact R5 Set-core source, minimum rule and guard
order; they may not be described as public execution of the later guard.

An independently reachable aggregate-PNG strict exceed is algebraically impossible under the
unchanged limits:

```text
member_count <= 4
each member PNG <= 67,108,864 bytes
4 * 67,108,864 = 268,435,456 bytes
aggregate rejection condition: sum > 268,435,456
```

Accepted R5 carries forward the requirement for one dominance proof and one public equality-boundary
probe. The latter may
reuse one immutable 67,108,864-byte synthetic PNG buffer across four independently counted member
occurrences; no new PNG path or tracked byte asset is allowed. Other reachable resource failures, including a five-member input, a per-member PNG cap plus one
byte, a 1,781st raw leaf and a 262,145-byte Maker action, remain actual public executions returning
`RESOURCE_LIMIT_EXCEEDED`. Exact per-member/aggregate PNG, raw-leaf and logical raw-byte equality
probes record guard admission followed by one named downstream typed error; they do not claim full
positive finalization. Strict aggregate raw exceed is separately dominated by the closed owner
limits. A structural proof is separately counted and can never be marked executable.

### Hermetic Set-construction failure evidence

Accepted R5 carries forward R3's rejection of a production factory, callback parameter, public test
seam and third support API. The one
allowed construction-failure probe is confined to
`tests/test_generated_reference_role_binding_set.py` and an automatically restored
`monkeypatch.context()`. Its wrapper delegates every `_build_identity` call except the call whose
model type is exactly `CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetV1`; that exact
Set-construction call raises one fixed `ValueError` after Decision construction. The public
finalizer must map it to `DECISION_OR_SET_REVALIDATION_FAILED`, return no result or placeholder, make
the injected call exactly once and expose no mutation. After restoration, the same positive input
must reproduce baseline Decision and Set formal bytes exactly.

This test-local exception does not authorize Set codegen, either fixture or any production caller to
import, reflect on or call `_build_identity`. Public positive-Decision-without-Set and adverse-Decision-with-Set verification remain two
separate public atomicity probes; neither can be used to claim that Set construction itself failed.

The other 57 hermetic units are also closed. They patch only the exact Set-module local binding of a
released public verifier or SHA/document helper under one automatically restored
`monkeypatch.context()`. The Policy freezes both verifier call sites, all 18 released ADR-046 codes,
all six named status exception types and their fixed first-priority constructor codes, all five
named SHA/document targets, fixed messages or returns, exact call counts, and the no-second-call/
no-later-fault-search rule. Baseline positive formal bytes must match again after every restoration.

The two delegated PNG dual-fault units additionally bind the exact existing ADR-046 priority test
node, its changed-PNG plus Character-purpose/Scene-role fault, the two existing support callable
symbols and the Request/final Set call-site typed injections. ADR-046 must select
`PNG_ADMISSION_INVALID`; Set maps only that exact typed code to `RAW_MEDIA_MISMATCH`. This evidence
does not add an API, permit private/dynamic support access or re-run a Set-side probe for the later
fault.

### Packet and Human-review separation

The reviewed source and derived fixture remain first-party fictional synthetic packets. Both must
retain `human_known_answer_acceptance=NOT_GRANTED` until a later independent Human acceptance task.
The complete review packet is composite: those two fixtures, the exact Policy, the frozen hermetic
test nodes, the structural proof descriptors and validation results at one frozen commit. The
derived fixture may record `PUBLIC_EXECUTION_MATCHED` or `STRUCTURAL_PROOF_VALIDATED`; for a
test-only unit it may record only `HERMETIC_TEST_NODE_ANCHORED_EXECUTION_REQUIRED`. It must not claim
that a test ran. Test execution and final evidence closure remain review-time facts and are never
written back as Human acceptance by codegen.

Deterministic bytes, tests, public executions, hermetic injections and structural proofs establish
only implementation conformance to the bounded supplied-input policy. They do not prove real asset
selection, legal Rights, present currentness, Provider eligibility, execution authority or
commercial-use permission.

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
policy_version=1.4.0
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
policy_version=1.4.0
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
policy_version=1.4.0
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

Schema generation would remain explicit. This R5 Human architecture acceptance generates nothing.

## Validation and future implementation gates

A future R5 BUILD could proceed only after this exact Accepted R5 is separately staged, committed,
pushed, reviewed and merged under explicit authorizations, followed by a separate explicit BUILD
authorization. It would have to:

1. begin from a newly verified authoritative clean `main` in a new isolated `codex/` branch;
2. record path, Git blob, size and SHA-256 for all 89 current Schemas and all 20 current fixtures
   before any generation;
3. prove `MODELS[:89]`, all 89 existing Schema bytes and all 20 existing fixture bytes unchanged at
   the final reviewed commit, while preserving older 83/16 and 86/18 historical assertions;
4. append only the exact three approved top-level models in exact Registry order;
5. keep target/member/replay/gate helpers inline rather than Registry entries;
6. fully reconstruct every supplied ADR-046 finalization and verify exact original whole PNG bytes;
7. test common Artifact/Profile/Catalog/subject/purpose/primary-binding/Rights equality, including
   the exact R4 cross-Catalog fixed-case baseline assertions, canonical mutation-document digest,
   two-field mutation ledger, no identity rehash, all-other-fields equality and exact public
   `COMMON_FRAME_MISMATCH` result;
8. test Character `1..3`, Scene `1..4`, canonical subsets, singleton, PARTIAL and FULL;
9. test duplicate roles, duplicate Bindings, member reorder, ordinal mutation, same-Sidecar
   cross-role allowance and equal-bytes distinct occurrences;
10. test that one bad member cannot be omitted, replaced or converted into a favorable subset;
11. test Request-time and final per-member replay, all prior-target/branch coverage, copied Receipt,
    copied `CURRENT`, stale closure attacks, Request-time expired/non-current no-Request outcomes,
    exact Request `TIME_OR_VALIDITY_INVALID`/`REQUEST_MEMBER_STATUS_NOT_CURRENT` codes, final expired
    no-Decision time failure, final revoked/held Reject and final indeterminate Decision; separately
    validate both named final-bound structural proofs without claiming the earlier Request guard hit
    either named final guard;
12. test every `member.binding_at <= requested_at <= set_at`, all exact time equalities, half-open
    bounds and minimum validity calculations, including the exact Request-validity dominance
    contradiction frozen by the two expired-bound proof vectors;
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
    cross-member/stage/non-aliased-buffer no-dedup, the 29-capsule public-finalizer build maximum,
    the 31-capsule positive-finalization-verifier boundary, 1,780-leaf/512,524,288-byte final limits
    and 268,435,456-byte aggregate PNG limit;
21. reject every Provider/InputMaterial/ProviderRequest/Runtime/URL/slot/order/idempotency,
    credential, cost, Retry, publication, retention and training injection;
22. prove by AST/import inspection that the core Set module imports only the exact allowed upstream
    modules/symbol classes and never imports `InputMaterial`, `ProviderRequest`, Provider, Compiler,
    Runtime, Worker, QC or persistence code;
23. prove the two support callable signatures, typed return dataclass fields/invariants and complete
    public call graph; prove Set codegen imports exactly those two old-codegen function symbols and
    never accesses an old-codegen module alias, private/dynamic/reflected name, CLI, update or writer;
    repair and test the `scene_singleton_baseline` call/signature mismatch only inside the existing
    Set-codegen path;
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

### Accepted R3 fixed support-case replacement

Accepted R3 retains exactly the same two callable symbols and leaves the Role-Binding callable
signature, both return dataclass names and both return field orders unchanged. It replaces only the
Promotion callable's closed `case_id` Literal with:

```python
def build_generated_reference_asset_promotion_fixed_fixture_support(
    repository_root: Path,
    *,
    case_id: Literal[
        "character-same-status-record-v1",
        "scene-successor-reconciliation-v1",
        "character-equal-png-distinct-occurrence-v1",
    ],
) -> GeneratedReferenceAssetPromotionFixedFixtureSupportV1
```

The first two literals remain the exact released fixture reconstructions. The third is a fixed
in-memory derivative of `character-same-status-record-v1`; it must:

- reuse the exact same Character PNG bytes, raw SHA-256, size and technical record;
- retain the same Artifact, Profile, Catalog, subject, purpose, primary binding and field-equal
  reviewed Rights frame;
- construct a complete first-party fictional Outcome, Candidate, Qualification, Manifest, status,
  Promotion and Sidecar closure;
- differ from the base in at least Outcome, Candidate, Promotion Request, Promotion Decision and
  Sidecar semantic identities; and
- write no fixture, add no PNG or path, return no writer or authority value and make no Provider or
  Runtime call.

Equal output bytes do not require a different `output_set_sha256` when the frozen descriptor is
itself equal. Occurrence distinction must instead be proved by the exact formal identities above.
The Set codegen may invoke the new literal only for the frozen equal-byte/distinct-occurrence probe,
then pass the typed result to the unchanged Role-Binding support callable. It still may not use an
old-codegen module alias, private or dynamic name, reflection, CLI, update or writer. The test-local
Set-construction injection described above is not a support API exception and is unreachable from
codegen and production code.

The frozen future fixture paths are:

```text
tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/
  reviewed-known-answer-source-v1.json
  generated-known-answer-v1.json
```

The codegen would freeze the complete 20-path pre-BUILD fixture map and append only those two paths,
increasing the tracked fixture count from 20 to 22.

The source packet would retain exactly two primary first-party fictional cases, one Character and one
Scene, plus the fixed auxiliary equal-PNG/distinct-occurrence support identity described above. The
auxiliary occurrence is evidence input, not a third target case or tracked fixture. Under Accepted
R4 it was intended to materialize every public probe in the 217-unit ledger and reference the
separately anchored test-only and structural-proof units. Under Accepted R5 it must instead follow
the corrected 135/58/24 classification and exact 15-operation ledger. It would cover:

- Character and Scene singleton, canonical proper-subset and exact full-tuple cases;
- same Sidecar under different roles through distinct positive Bindings;
- equal bytes under distinct Candidate/Sidecar occurrences;
- duplicate role, duplicate Binding, reorder, ordinal and cross-purpose attacks;
- cross-Artifact/Profile/Catalog/subject/primary-binding and unequal-Rights rejection;
- request/final stale closure attacks, Request-time expired/non-current no-Request outcomes, final
  expired no-Decision time failure, final revoked/held negative Decisions, final indeterminate
  Decisions, and the two independent expired Qualification/Manifest named-final-guard structural
  dominance proofs;
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

Accepted R5 retains the Accepted R4 future allowlist at exactly 27 unique paths. The two paths added
to Accepted R1's
25-path list are only `src/sdc/generated_reference_asset_promotion_codegen.py` and
`src/sdc/generated_reference_role_binding_codegen.py`. Changes in those old modules would be limited
to the exact R3 support surfaces above and their internal deterministic read-only reuse; their frozen
fixtures, derived bytes, fingerprints and existing CLI behavior must not change. Workflow and
Makefile changes would be limited to the new offline read-only Set codegen check. Historical test
changes would be limited to support-API/isolation enforcement, new 89/20 prefix protection and exact
92/22 append assertions. The ADR itself is deliberately absent from a future BUILD allowlist.

Accepted R4 defined a nine-path Set-specific delta inside that unchanged 27-path ceiling. Accepted
R5 retains the same nine-path ceiling. Its additional remediation is limited to the Set core Policy
literal/constants, Set codegen proof/verifier dispatch and dead-recipe/signature correction, the
three regenerated Set Schemas, the reviewed source and derived Set fixtures, and the Set core/codegen
tests that bind those bytes. The Promotion and Role-Binding support callables and their modules
receive no R5-specific change. Any claimed need to alter a support case or API, add another source-
input category or modify another upstream module stops BUILD for a new architecture decision.

The exact shared R4/R5 Set-specific synchronization paths within that ceiling are:

```text
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetRequestV1.schema.json
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetDecisionV1.schema.json
schemas/CreativeSampleGeneratedReferenceEligibleAssetRoleBindingSetV1.schema.json
src/sdc/generated_reference_role_binding_set.py
src/sdc/generated_reference_role_binding_set_codegen.py
tests/test_generated_reference_role_binding_set.py
tests/test_generated_reference_role_binding_set_codegen.py
tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/reviewed-known-answer-source-v1.json
tests/fixtures/visual_prompt_profiles/generated-reference-role-binding-set/generated-known-answer-v1.json
```

These nine paths constrain both the historical R4 delta and any future R5 remediation delta. They do
not authorize reuse of either partial BUILD or reduce the complete 27-path ceiling needed to build
the entire feature from authoritative `main`. A need for a tenth Set-specific path must stop.

Any need for another path, top-level model, Registry order, fixture or policy rule would stop BUILD
and require a separately reviewed ADR revision or architecture decision. The third support case must
reuse the existing frozen synthetic Character PNG bytes in memory. No new PNG or 28th path is
authorized. Neither Accepted R4 nor Accepted R5 itself authorizes any allowlist path to change.

Any later separately authorized R5 BUILD must keep all pre-ADR-047 89 Schema paths and bytes and all
20 prior fixture paths and bytes exact. Registry and fixture counts remain 92 and 22. Because the
Set Policy, two proof units and one verifier operation change, neither the current R4 Set Schemas nor
the R4 source-fixture byte nor the unmaterialized R4 derived-fixture expectation is an R5 byte anchor;
all three Schemas and both fixtures would have to be regenerated offline and receive new path/size/
SHA-256 anchors. The old 89 Schema and old
20 fixture manifests remain immutable. Both Set fixtures must still retain
`human_known_answer_acceptance=NOT_GRANTED`. No historical ADR-045 or ADR-046 fixture may change.

## Rejected alternatives

Accepted R5 carries forward all Accepted R4 rejected alternatives and additionally rejects:

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
- reusing one scenario-level `expected_error_code` for multiple independent probes or treating a
  declaration-only scenario as evidence-complete;
- claiming a sealed or dominated guard was publicly executed, or replacing a technical
  unreachability proof with Human boundary acceptance;
- adding a public Set-construction factory/callback seam, a third support API, a new PNG path or a
  28th BUILD path for packet remediation;
- copying an equal Catalog identity and claiming a cross-Catalog execution, inventing an unanchored
  Catalog SHA, reading the mutation from a hidden codegen constant, or adding a sixth input anchor;
- describing the earlier Request half-open guard's `TIME_OR_VALIDITY_INVALID` as proof that a named
  final Qualification or Manifest guard ran;
- claiming a 31-capsule positive verifier vector was executed by the 29-capsule finalizer, or adding
  a redundant 218th evidence unit instead of correcting the frozen operation; and
- changing a support case/API, adding a tenth Set-specific path or introducing private/dynamic or
  production test access to repair either evidence contradiction;
- treating synthetic known answers as real assets, Rights, Provider or execution authority.

## Risks and treatment

| Severity | Risk | Required treatment |
| --- | --- | --- |
| Blocking | Set error order attempts to reorder an ADR-046 atomic verifier | Inherit the released verifier order and map exact `PNG_ADMISSION_INVALID` by typed `.code` only |
| Blocking | Complete known answers require private upstream codegen access | Add only the two frozen typed read-only support APIs and stop on any private/dynamic/third API access |
| Blocking | Cross-Catalog evidence copies an equal pair or uses an unanchored digest | Verify both exact baseline pairs, derive the distinct pair from the frozen canonical probe-local Catalog projection and retain the complete changed-field ledger |
| Blocking | A returned time error is attributed to a later named final bound that the Request guard dominates | Use the two exact structural dominance proofs and never equate error-code equality with named-guard execution |
| Blocking | The 31-capsule positive vector is assigned to the 29-capsule finalizer | Invoke the released public finalization verifier and retain the existing 31-capsule vector and 217-unit total |
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

Neither Accepted R2, Accepted R3, Accepted R4 nor Accepted R5 approves or specifies:

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

At this Accepted R5 architecture-only state, SDC may claim only that Accepted R1 through Accepted R5
are Human-accepted architecture records; that the separately authorized R3 and R4 BUILDs remain
stopped, uncommitted working material without derived fixtures or Human known-answer acceptance; and
that Accepted R5 freezes the exact remediation and Policy identity recorded here. No current
Contract, Schema, implementation, fixture, known-answer packet or actual Set output may be claimed
to conform to R5.

Only after separate R5 document promotion, a separate BUILD authorization, conforming
implementation, first-party synthetic known-answer acceptance and implementation merge could SDC
claim that:

- one pure offline operation fully revalidated an explicitly supplied bounded tuple of positive
  atomic Bindings and their original whole PNG occurrences;
- every member shared one exact common frame and had complete fresh replay at Request and `set_at`;
- one independent Set Checker recorded one deterministic Decision over the unchanged Maker tuple;
- one positive Decision produced one immutable historical Set atomically; and
- all pre-ADR-047 89 Schema bytes, 20 fixture bytes and complete zero-authority boundaries remained
  unchanged.

Even then, SDC could not claim that:

- the probe-local mutated Catalog projection is a published, real, current or Provider-eligible
  Catalog;
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

Positive consequences of Accepted R5, only if separately authorized and implemented, would include:

- explicit finite selection would replace implicit discovery or one-Binding completeness guesses;
- canonical role coverage, duplicate behavior and occurrence identity would become portable and
  deterministic;
- each error, issue, hermetic fault and structural proof would have a distinct auditable evidence
  identity rather than an ambiguous scenario-level declaration;
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
- R5 could not combine different Artifacts, Profiles, Rights scopes or primary bindings;
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

## Accepted R3 BUILD restart stop gate

The current uncommitted 25-path R2 BUILD worktree on
`codex/generated-reference-role-binding-set-r2` remains frozen working material only. Accepted R3
does not validate, adopt, resume, merge, amend, regenerate or authorize it. A future R3 BUILD could
begin only after all of these independent gates close:

1. this exact Accepted R3 architecture record remains content-exact through document promotion;
2. the Accepted R3 document is separately staged, committed, pushed, reviewed and merged under
   explicit authorizations;
3. a separate R3 BUILD authorization is granted from newly verified authoritative `main`;
4. a new clean isolated R3 BUILD worktree records the complete 89-Schema/20-fixture byte baseline;
5. any reuse from either partial BUILD is reviewed and ported hunk-by-hunk only within the unchanged
   27-path allowlist;
6. the exact implemented Policy identity equals Accepted R3 version `1.2.0`, 227,888 canonical bytes
   and SHA-256 `4075b6e0bb6a5a5c1e2f949bfd640f94eda974c3f09987e56820a787dda7a308` frozen by this acceptance;
7. all 217 packet units and two separate unknown-code compatibility-stop tests close without
   mislabelling injection or structural proof as public execution; and
8. any 28th path, old 89/20 byte change, third API, new PNG, production construction seam,
   private/dynamic codegen access or authority expansion stops BUILD.

No current R2 Schema or Set fixture byte is an R3 acceptance anchor, and neither partial worktree may
be silently rebased or used as the R3 branch.

Those gates were subsequently authorized from authoritative main
`bd0a40ef7625c272a0b9d91f1dcbd31ac37a6383`. The isolated
`codex/generated-reference-role-binding-set-r3` BUILD reached 24 changed paths within the 27-path
allowlist, outside `0`, staged `0`, preserved the old 89-Schema/20-fixture manifests and generated
its three Set Schemas plus reviewed source fixture. Its source remained
`human_known_answer_acceptance=NOT_GRANTED` at 1,583,052 bytes / SHA-256
`804dee0bdb33ebec12fbee790bb82f3c40c3db7880240550997b843d140d1aa5`. Strict no-write closure
then stopped on the cross-Catalog vector above before the derived fixture was written. Its status is
therefore exactly:

```text
BUILD_R3_IMPLEMENTATION_BLOCKED
```

Passing R3 tests or retaining partial files cannot override that Policy/input contradiction, and the
R3 branch may not be repaired or resumed under this Accepted R4 architecture-only authority.

## Accepted R4 BUILD restart stop gate

Accepted R4 grants no BUILD authority. A future R4 BUILD could begin only after all of these
independent gates close:

1. this exact Accepted R4 remains without semantic drift;
2. the accepted R4 document is separately staged, committed, pushed, reviewed and merged under
   explicit authorizations;
3. a separate R4 BUILD authorization identifies whether the existing stopped R3 worktree may be
   reused hunk-by-hunk or requires a new clean isolated R4 worktree;
4. authoritative `main`, branch/worktree cleanliness and the complete 89-Schema/20-fixture path,
   Git blob, size and SHA-256 baselines are reverified before any implementation write;
5. the exact implemented Policy identity equals Accepted R4 version `1.3.0`, 233,029 canonical
   bytes and SHA-256
   `5186be89ed0de72dac55ae7f363291225998a41dd7082a12db848c914152dce8`;
6. the cross-Catalog handler reads the exact vector from the Policy/source packet, verifies the
   baseline and mutation Catalog anchors, changes exactly two scalar leaves with no identity rehash
   and obtains the required public typed result;
7. all 217 packet units and the two separate unknown-code compatibility-stop tests close, the three
   Set Schemas and two Set fixtures receive new R4 anchors, and both fixtures remain `NOT_GRANTED`;
8. all old 89 Schema and 20 fixture bytes remain exact, overall changed paths remain within the
   existing 27-path allowlist and the R4-specific delta remains within the exact nine paths above;
   and
9. any sixth anchor, tenth R4-specific path, 28th overall path, third API, new PNG, production
   construction seam, private/dynamic access, unanchored Catalog value or authority expansion stops
   BUILD.

Human known-answer acceptance, Draft-to-Ready conversion and merge remain later independent gates.
No stopped partial worktree is itself an R4 byte anchor.

## Accepted R4 document-acceptance task boundary

The current authorized Accepted-R4 document update is confined to the isolated worktree
`C:\Users\Administrator\Documents\Codex\story-to-drama-compiler-adr-047-r4-cross-catalog-remediation`
on this branch, and only this file may be modified:

```text
codex/adr-047-r4-cross-catalog-remediation
docs/adr/SDC-ADR-047.md
```

It must not:

- treat this Human architecture acceptance as authorization for staging, commit, push, PR, Ready,
  merge, BUILD, implementation, partial-worktree reuse or Human known-answer acceptance;
- alter Accepted R1/R2/R3 history, any Accepted R3 technical constraint other than the one explicit
  unsatisfiable vector supersession accepted here, the 89-Schema/20-fixture compatibility gate,
  future 92-Schema/22-fixture target or any zero-authority rule;
- modify ADR-039 through ADR-046 or any current Contract, Schema, Registry, fixture, source, test,
  codegen, CI, Makefile or README file;
- calculate Contract/Schema/fixture implementation outputs, run Schema generation, code generation
  or fixture update;
- modify, repair or resume any current partial BUILD worktree;
- stage, commit, push, create a PR, request review, mark Ready or merge;
- create or review a real Set, Binding, Sidecar, Provider input or asset;
- connect Compiler, Provider, Runtime, network, credentials, cost, Retry or persistence; or
- begin BUILD, Provider-input, publication, retention or training work.

## Accepted R5 BUILD restart stop gate

The separately authorized R4 BUILD remains frozen in
`C:\Users\Administrator\Documents\Codex\story-to-drama-compiler-generated-reference-role-binding-set-r4`
on `codex/generated-reference-role-binding-set-r4` at
`8737c49bb949900432ed86074a7dff2c90769ace`. At the R5 acceptance gate it has exactly 24 changed paths
inside the 27-path allowlist, outside `0`, staged `0`, and eight of the nine Set-specific paths. It
retains 92 Schema files and 21 fixture files because no derived Set fixture was written. Its old
89-Schema and old 20-fixture manifests remain respectively:

```text
f10c0249b02638b4f5d34aaffdaf0244f9b2e8f25fa1b33a2f24f1ca2b83cdb1
64b0d9c6dc84418be2c97a6dbb679a29a19d16338f23135ab346531a31bf8e3f
```

Its partial Policy remains Accepted R4 `1.3.0`, 233,029 canonical bytes and SHA-256
`5186be89ed0de72dac55ae7f363291225998a41dd7082a12db848c914152dce8`. Its reviewed source fixture
remains `human_known_answer_acceptance=NOT_GRANTED` at 1,589,809 bytes / SHA-256
`39292c2dcd8f8311215c319b7cd98c50f639d09469875273a15dab81257afdfd`; the derived fixture is absent.
The two isolation tests remain byte-identical to their authoritative Git blobs. None of those partial
bytes is an R5 acceptance anchor, and Accepted R5 does not authorize modifying or resuming that
worktree. The stopped R3 BUILD likewise remains frozen at its previously recorded 24/27 paths,
outside `0`, staged `0`, source/derived state and byte anchors.

A future R5 BUILD could begin only after all of these independent gates close:

1. this exact Human-accepted R5 remains semantically unchanged through document promotion;
2. the accepted R5 document is separately staged, committed, pushed, reviewed and merged under
   explicit authorizations;
3. a separate R5 BUILD authorization identifies a clean isolated implementation worktree and any
   individually reviewed hunk reuse from the stopped R4 worktree;
4. authoritative `main`, branch/worktree cleanliness and the complete 89-Schema/20-fixture path,
   Git blob, size and SHA-256 baselines are reverified before any implementation write;
5. the exact implemented Policy identity equals R5 version `1.4.0`, 234,946 canonical bytes and
   SHA-256 `e2b9aacd7eb3de7e54c238b5d698e7a5abf48fee2931300576309eec4ec5dac0`;
6. all 48 scenarios and 217 evidence units close under the exact 135/58/24 evidence-kind and
   15-operation ledgers, including both named-bound dominance proofs and the 31-capsule positive
   finalization-verifier execution;
7. the two obsolete public expired-bound recipes are absent and the
   `scene_singleton_baseline` call/signature mismatch is repaired and tested only in the existing
   Set-codegen path;
8. the three Set Schemas and two Set fixtures are generated from R5 and receive new exact anchors;
   both fixtures retain `human_known_answer_acceptance=NOT_GRANTED`;
9. all old 89 Schema and 20 fixture bytes remain exact, overall changed paths remain within the
   existing 27-path allowlist and the R5 delta remains within the same exact nine Set-specific paths;
   and
10. any sixth input anchor, tenth Set-specific path, 28th overall path, third support API, support-
    case change, new PNG, production seam, private/dynamic access, unknown-code guess or authority
    expansion stops BUILD for a new architecture decision.

Human known-answer acceptance, Draft-to-Ready conversion and merge remain later independent gates.
No partial worktree, passing test or deterministic byte result grants Provider-input, Runtime,
rights, asset-use, execution or commercial authority.

## Accepted R5 document-acceptance task boundary

The current authorized Accepted-R5 document update is confined to the isolated worktree
`C:\Users\Administrator\Documents\Codex\story-to-drama-compiler-adr-047-r5-executable-evidence-remediation`
on this branch, and only this file may be modified:

```text
codex/adr-047-r5-executable-evidence-remediation
docs/adr/SDC-ADR-047.md
```

It must not:

- treat this Human architecture acceptance as authorization for staging, commit, push, PR, review
  request, Ready, merge, BUILD, implementation, partial-worktree reuse or Human known-answer
  acceptance;
- alter Accepted R1/R2/R3/R4 history, the Accepted R5 evidence corrections or Policy identity, the
  frozen cross-Catalog vector, the 27-path/nine-path ceilings, the two-support-callable boundary, the
  89-Schema/20-fixture compatibility gate, future 92-Schema/22-fixture target or any zero-authority
  rule;
- modify ADR-039 through ADR-046 or any Contract, Schema, Registry, fixture, source, test, codegen,
  CI, Makefile or README file;
- calculate Contract/Schema/fixture implementation outputs, run Schema generation, code generation,
  fixture update or any test that writes cache/output;
- modify, repair, resume, stage or delete anything in a partial BUILD worktree;
- stage, commit, amend, push, create or update a PR, request review, mark Ready or merge;
- create or review a real Set, Binding, Sidecar, Provider input or asset;
- connect Compiler, Provider, Runtime, network, credentials, cost, Retry or persistence; or
- begin BUILD, Provider-input, publication, retention or training work.
