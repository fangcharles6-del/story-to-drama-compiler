# SDC-ADR-025: Pack-level Human Review v2 rights-manifest consumer v2.4

- **Status:** Proposed
- **Date:** 2026-08-19
- **Version:** V01

## Context

SDC-ADR-021 introduced an independent Pack-level Human Review v2 qualification consumer. Its
positive `CreativeSampleRealAssetQualificationDecisionV2` outcome is deliberately narrow:
`PASS_ASSET_INTAKE_ONLY` means that one exact fourteen-member Pack closure passed the scoped
asset-intake assessment under one fixed policy. SDC-ADR-023 and SDC-ADR-024 added separately
controlled local boundaries for recording and finalizing that Decision. Even a completed positive
Decision remains `HUMAN_GATE / NOT_AUTHORIZED`, creates no rights manifest and grants no Runtime,
Provider, publication or generation authority.

The existing Real Asset Intake v1 rights manifest is not an admissible next step for the v2
closure. V1 requires 28 actual per-asset human-review records. V2 contains two actual Pack-level
reviews. Expanding those two Pack-level contracts into 28 apparent v1 records would invent human
acts that did not occur, erase the v2 role and evidence model, and weaken both audit profiles.
Calling the v1 manifest builder or v1 qualification path would therefore be a semantic conversion,
not compatibility.

A later design reviewer nevertheless needs an immutable, deterministic artifact that binds a
positive v2 Decision to the exact contracts it assessed. That artifact must be append-only and
zero-authority. It must not become a filesystem finalizer, a real-data operating procedure or an
authorization bridge merely because its name contains “rights manifest”.

## Decision

Add one immutable Pydantic v2 contract,
`CreativeSampleRealAssetRightsManifestV2`, its committed JSON Schema and a pure in-memory
compiler module. The module exposes only build, strict parse and deterministic verification APIs.
It opens no file, accepts no path, has no command-line interface and writes no bytes.

This PR is **synthetic-only**. Tests construct synthetic Pack, Evidence, Reviewer A, Reviewer B,
PairCheck, Request, Qualifier instruction and Decision models in memory. The implementation,
tests, documentation and examples must not read the current real private Decision, Request,
Qualifier instruction, Qualifier reference, Pack, media, Evidence, Reviews, PairCheck or retained
identity records. A future trusted local consumer is a separate design and PR requiring another
explicit approval.

The builder admits only the complete Pack-level v2 closure:

1. one exact fourteen-member `CreativeSampleFrozenRealAssetPackManifest`;
2. one exact `CreativeSampleRealAssetRightsEvidenceBundleV2`;
3. one finalized `CreativeSampleRealAssetHumanPackReviewV2` for Reviewer A;
4. one finalized `CreativeSampleRealAssetHumanPackReviewV2` for Reviewer B;
5. their exact issue-free `CreativeSampleRealAssetReviewPairCheckV2`;
6. the exact `CreativeSampleRealAssetQualificationRequestV2` reconstructed from that closure;
7. the exact canonical `CreativeSampleRealAssetQualificationDecisionInstructionV22` bound to
   that Request and Qualifier; and
8. the exact `CreativeSampleRealAssetQualificationDecisionV2` reconstructed from the Request and
   instruction.

It first uses the existing pure qualification closure verifier. It then requires all of the
following Decision facts without waiver or fallback:

```text
decision=PASS_ASSET_INTAKE_ONLY
qualification_scope=ASSET_INTAKE_ONLY
status=QUALIFICATION_COMPLETE
rights_qualification_performed=true
eligible_for_separate_manifest_design_review=true
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
rights_manifest_created=false
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

`REJECTED`, `NEEDS_HUMAN_REVIEW`, an invalid closure, finite Evidence that is expired at
`manifest_at`, an ineligible Decision, an unready PairCheck, a non-empty PairCheck issue tuple or
any non-zero authority claim is a hard failure. The consumer does not reinterpret the Qualifier's
basis, infer a better outcome, waive an issue or determine legal sufficiency.

## Exact transitive binding

The Manifest binds both the stable identifier and canonical SHA-256 of every contract boundary in
the admitted closure: Pack manifest, Evidence Bundle, Reviewer A, Reviewer B, PairCheck,
Qualification Request, Qualifier instruction and Qualification Decision. It also repeats the
fixed qualification policy identity, its own fixed Manifest-policy identity and the relevant
stable cross-reference IDs. The builder recomputes these values from the strictly revalidated
models; no caller supplies a digest or ID as an independent assertion.

The Manifest policy is a separate built-in triple:

```text
manifest_policy_id=creative-sample-real-asset-rights-manifest-policy
manifest_policy_version=2.4.0
manifest_policy_document_sha256=ac31acb7faf86d08752ec37a585d12754af7611d252e8112b41088f3ed71d912
```

It fixes exact v2 closure binding, retained-instruction binding, time and Evidence-validity rules
and the no-generation/no-execution/no-Provider boundary. It is not selectable from a caller or
environment. A Manifest-policy change requires a reviewed version and digest change.

The instruction is not accepted merely because its ID has the right shape. Its canonical SHA-256
must equal the Decision's `qualifier_record_sha256`, and its Request, policy, Qualifier-reference,
decision time, outcome, issue-code and basis fields must replay the Decision exactly. The Manifest
also carries the eight retained-content digests already bound transitively by the Request,
Reviews, instruction and Decision: retained Evidence, Evidence Preparer reference, Reviewer A
review content and retained reference, Reviewer B review content and retained reference,
Qualifier reference and Qualifier instruction record.

These are digest bindings only at this pure boundary. The compiler does not open the retained
private records and cannot assert their current availability, file identity or authorship. A
future trusted local boundary must receive each exact path, safely reopen and hash each retained
file, and compare the observed bytes before it may publish a real Manifest.

Canonical contract bytes are deterministic UTF-8 JSON derived from `model_dump(mode="json")`
with sorted keys, two-space indentation, unescaped Unicode where JSON permits it and one final LF.
The Manifest's content-derived stable ID is computed over every field except that ID. Changing an
upstream model, its canonical bytes, the policy identity, the explicit Manifest time or any
zero-authority fact therefore produces a different or invalid Manifest.

The strict parser rejects malformed UTF-8, duplicate object keys, unknown or missing fields,
non-canonical timestamps and all contract-validation failures. Parsing a value-equivalent JSON
object does not establish byte identity; a later file boundary must separately require canonical
bytes and hash the exact selected file.

The verifier revalidates and deterministically reconstructs the complete upstream qualification
closure, rebuilds the expected Manifest with its recorded explicit creation time and requires
exact model equality. It is not a shallow signature check and cannot trust copied stable IDs or
digests in place of the supplied upstream models.

## Explicit time and validity policy

The build API requires a caller-supplied whole-second UTC `manifest_at`:

```text
YYYY-MM-DDTHH:MM:SSZ
```

There is no default and no call to a wall clock, local timezone, filesystem timestamp,
environment variable or “current time” helper. Verification reuses the Manifest's immutable
`manifest_at` and likewise reads no clock.

Creation preserves the historical causal and validity chain:

```text
pair_check.evaluated_at <= request.requested_at
request.requested_at <= instruction.decision_at
instruction.decision_at == decision.decision_at
decision.decision_at <= manifest.manifest_at
```

The Request and Decision are still reconstructed under their original rules, including
`decision.decision_at < request.request_valid_until`. That deadline proves the historical Decision
was timely; it does not become a new wall-clock deadline for consuming an already completed,
immutable Decision. The consumer never refreshes or reopens qualification merely because
`manifest_at` is later than the Request deadline.

Evidence validity remains separately binding at Manifest creation. For a finite
`evidence.valid_until`, `manifest_at` must precede that instant; `PERPETUAL` remains the only
non-timestamp value. The Manifest records the exact inherited validity value but cannot extend,
round, renew or replace it.

A later historical verification can reproduce a Manifest from its fixed `manifest_at` without
consulting today's time. That property does not make expired Evidence current again and does not
authorize creating a new Manifest at or after a finite Evidence deadline.

## Manifest fact without authority

A successfully built synthetic Manifest truthfully records:

```text
status=RIGHTS_MANIFEST_CREATED
rights_qualification_performed=true
rights_manifest_created=true
```

The first is inherited from the already completed scoped Decision; the second records that the
pure Manifest model was formed. Neither means that legal sufficiency was established, and neither
is an entitlement, authorization, publication approval or runtime capability. Every Manifest,
including one derived from `PASS_ASSET_INTAKE_ONLY`, fixes:

```text
HUMAN_GATE
NOT_AUTHORIZED
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

No field can express a Provider credential, Provider request budget, post allowance, entitlement,
authorization token, Runtime routing instruction or generation eligibility. A downstream system
must not treat the existence of a Manifest, `rights_manifest_created=true` or
`rights_qualification_performed=true` as authority.

## No v1 conversion and no operational boundary

The v2.4 compiler must not import or call `build_real_asset_rights_manifest`,
`qualify_real_asset_candidate_pack` or any other v1 qualification or manifest path. It must not
synthesize, clone, split or imply 28 per-asset review records. The two v2 Pack-level reviews remain
the only two reviews that humans actually made, and the new Manifest binds them as Pack-level
contracts.

This stage intentionally provides none of the following:

- filesystem reads or writes, paths, directory scanning, glob expansion or alias selection;
- a CLI, workspace, browser UI, loader, local finalizer or create-new publication routine;
- real Manifest creation or verification;
- a rights-manifest-to-entitlement or rights-manifest-to-authorization bridge;
- Runtime, Worker, Provider, PostgreSQL, Temporal, Ark, Atomic Ledger or migration integration;
  or
- networking, Key access, upload, POST, purchase, recharge, trial or service startup.

Repository `output/` and `tmp/` are outside this design and its tests. Private artifacts must not
be copied, staged, committed, uploaded or embedded in a fixture.

## Compatibility

The 56 committed Schemas that predate v2.4 remain byte-identical. The new append-only Manifest
Schema, `CreativeSampleRealAssetRightsManifestV2.schema.json`, increases the committed total to
57. Existing models, schemas, public qualification and Decision Finalizer Python APIs,
serialization behavior and production safety boundaries are not modified or reinterpreted.

Compatibility tests retain a normalized-LF byte lock over the 56-schema baseline and verify the
new Schema independently. A schema-regeneration step may add the one new file but must not rewrite
the baseline files. Entitlement and authorization registries remain untouched.

## Consequences

The Pack-level v2 path gains a precise, reproducible design artifact after a positive Decision.
The Manifest makes substitution or drift across the eight-contract closure visible while
preserving the actual two-review audit profile and fixed policy identity.

The cost is intentional separation. A positive Decision does not automatically build a Manifest,
and a pure synthetic Manifest cannot be used as a real filesystem artifact. After this PR is
merged, using the real private Decision remains prohibited. A trusted local operation boundary,
if approved later, needs its own explicit-path, bounded-read, TOCTOU, create-new and verification
design. Any entitlement or authorization consumer is later still and requires a separate policy
review, approval and PR.
