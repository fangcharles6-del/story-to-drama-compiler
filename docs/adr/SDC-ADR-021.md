# SDC-ADR-021: Pack-level human review v2 qualification consumer

- **Status:** Proposed
- **Date:** 2026-08-18
- **Version:** V02

## Context

SDC-ADR-020 ends at `CreativeSampleRealAssetReviewPairCheckV2`. Its strongest state,
`READY_FOR_SEPARATE_QUALIFICATION_REVIEW`, proves only that two complete, structurally compatible
Pack-level reviews are available for a later consumer. The PairCheck explicitly says that rights
qualification was not performed and that no rights manifest was created. It remains
`HUMAN_GATE / NOT_AUTHORIZED` and grants no execution, publication, Provider, entitlement or
authorization capability.

The existing Real Asset Intake v1 qualification path consumes 28 independent per-asset human
review records. The two Pack-level v2 reviews are materially different evidence: each human makes
one Pack decision covering the exact fourteen-member closure. Expanding those two documents into
28 apparent v1 reviews would invent records that no human made, erase the distinction between the
two audit profiles and violate the byte-compatibility boundary of the existing v1 contracts and
schemas.

A later policy owner nevertheless needs a deterministic way to record whether this exact v2
review closure satisfies one explicit qualification policy. That consumer must be a new,
zero-authority contract boundary rather than an extension or reinterpretation of v1.

## Decision

Add a separate Pack-level Human Review v2 qualification consumer. It introduces only versioned,
immutable request and decision contracts plus a pure local compiler. It does not alter
SDC-ADR-020, the v2 evidence/review/PairCheck records, the v1 rights manifest or any existing
contract or schema.

The qualification request binds the exact canonical bytes and stable IDs of all of its inputs:

- the fourteen-member frozen Pack manifest;
- the Pack-level rights evidence bundle;
- Reviewer A's finalized Pack review;
- Reviewer B's finalized Pack review;
- the `READY_FOR_SEPARATE_QUALIFICATION_REVIEW` PairCheck;
- the exact qualification policy identifier, version and committed normative policy-payload
  SHA-256; and
- one explicit Evidence Preparer reference.

The consumer must reconstruct and revalidate the complete closure rather than trusting identifiers
copied into the request. The pure functions strictly revalidate every supplied model, and the new
request/decision in-memory JSON parsers reject duplicate keys and unknown fields. Every canonical
document SHA-256 is recomputed, every stable ID is re-derived, every cross-reference is compared
and every ordered fourteen-member binding is checked against the frozen Pack. A future operational
boundary must use strict existing loaders for upstream private files. Malformed input, digest
drift, a stale or non-ready PairCheck, missing evidence, expired rights or an inconsistent review
is a hard stop.

This pure in-memory delivery recomputes canonical contract digests and binds the committed policy
triple, but it does not open the retained Preparer, evidence, reviewer, Qualifier-identity or
Qualifier-decision files named by their SHA-256 fields. For those private records it validates
format, separation and exact transitive binding only. A future operational boundary must hash each
explicitly selected ordinary local file immediately before use and compare the observed value;
until then the digest cannot prove current availability or authorship.

The Qualifier is a fourth human or organizational role, not Reviewer A, Reviewer B, the Evidence
Preparer or an automatic alias for any of them. The request adds an explicit
`evidence_preparer_ref_sha256` because the existing evidence-bundle contract does not identify its
preparer and remains unchanged. The decision's Qualifier record must be distinct from the
Preparer, both reviewer references, all retained evidence/review records, canonical contracts and
frozen asset records. SHA-256 establishes byte identity and can detect those collisions; it does
not authenticate a person, prove how independently the four people acted or interpret policy.
Those remain explicit organizational controls.

The request and decision each have a content-derived stable ID. The request's `evaluated_at` must
equal the PairCheck evaluation time; its later `requested_at` records when the immutable closure
was presented for qualification. The decision binds the complete canonical request by request ID
and SHA-256, repeats the exact policy identity, records a `decision_at` UTC second supplied to the
pure API, and records the Qualifier's actual decision and basis. The required order is every human
review time at or before PairCheck `evaluated_at`, then `evaluated_at <= requested_at <=
decision_at`. Tests supply fixed times; compiled artifacts never consult a wall clock. The
decision cannot rewrite, reconcile or infer any human answer.

`decision_at` neutrally names the time at which the Qualifier recorded any of the three scoped
outcomes. Every request has a fixed 24-hour maximum lifetime. For finite evidence,
`request_valid_until` is `min(evidence.valid_until, requested_at + 24 hours)`; for `PERPETUAL`
evidence it is `requested_at + 24 hours`. A decision requires `decision_at <
request_valid_until`; the boundary is exclusive.

The Qualifier records exactly one of `PASS_ASSET_INTAKE_ONLY`, `REJECTED` or
`NEEDS_HUMAN_REVIEW`; every incomplete, expired, conflicting or unrecognized condition remains
non-qualified or raises a closed validation error as defined by the versioned contract. The
deliberately narrow positive name means only that the exact request closure met the exact bound
mechanical admission constraints and that the Qualifier explicitly recorded a positive conclusion
against the built-in policy identity at `decision_at` for the Real Asset Intake boundary. The pure
compiler does not turn those admission constraints into proof of legal sufficiency. This is a
completed, scoped qualification assessment, but it is not the v1 qualification path, a rights
manifest, an entitlement, an authorization, a publish approval or a live execution approval.

Every decision includes a non-empty human `qualification_basis`. `PASS_ASSET_INTAKE_ONLY`
requires an empty `qualification_issue_codes`; `REJECTED` requires at least one issue and must
include `QUALIFIER_REJECTED_ASSET_INTAKE`; `NEEDS_HUMAN_REVIEW` requires at least one issue and
must exclude that rejection code. Every list is unique and canonically ordered. A positive
decision alone derives
`eligible_for_separate_manifest_design_review=true`; that field names another design gate and
grants no manifest or execution permission.

## Policy boundary

Policy is bound by the consumer's built-in `policy_id`, `policy_version` and
`policy_document_sha256` triple; it is not chosen from the local environment or supplied as a
floating alias. The SHA-256 identifies the version's committed normative policy payload. A
decision for one policy identity cannot be replayed under a new version, extended territory,
changed use scope, later Pack or different evidence bundle. A policy update requires code review,
a new fixed triple, and a new request and decision.

The normative payload, domain separator, compact canonical-JSON rule and public digest constant
are fixed in `src/sdc/real_asset_qualification_v2.py` as `_QUALIFICATION_POLICY_PAYLOAD`,
`_POLICY_DIGEST_DOMAIN`, `_canonical_payload` and
`QUALIFICATION_V2_POLICY_DOCUMENT_SHA256`. They are reproduced in the qualification runbook so
the policy SHA-256 can be independently recalculated. The v2 digest is
`f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031`.

This delivery defines the closed minimum policy needed to consume the v2 review closure. It does
not provide a general policy language, waiver mechanism, administrator override, repair mode or
`--force` option. It cannot turn `DISAGREEMENT` or `INCOMPLETE` into a qualification. It cannot
weaken the Pack evidence's territory, use scope or validity boundary, and it must reject an
evaluation at or after a non-perpetual expiry.

Qualification input is never synthesized from v1. Likewise, the consumer must not synthesize 28
v1 reviewer records from two v2 Pack reviews, call `build_real_asset_rights_manifest`, call
`qualify_real_asset_candidate_pack`, or emit a `CreativeSampleRealAssetRightsManifest`.

## Zero-authority decision

Every request and decision, including `PASS_ASSET_INTAKE_ONLY`, remains:

```text
HUMAN_GATE
NOT_AUTHORIZED
execution_authorized=false
posts_allowed=0
provider_requests=0
rights_manifest_created=false
eligible_for_real_generation=false
```

The request fixes `rights_qualification_performed=false`. A completed decision fixes
`rights_qualification_performed=true`, accurately recording that this new scoped consumer ran.
That historical fact grants no authority. No entitlement or authorization record is created or
modified.

The consumer has no Runtime, Worker, Provider, PostgreSQL, Temporal, Ark, entitlement,
authorization, Atomic Ledger or migration dependency. It performs no network I/O, file discovery,
service startup, API-Key access, upload, Provider request, POST, purchase, recharge or trial. This
stage uses no private Pack, evidence or reviewer data; contract examples and tests use only local
synthetic fixtures.

A later rights-manifest consumer requires its own ADR, versioned contracts, policy review and
independent PR. A later authorization or entitlement bridge requires another independent approval
and PR. Neither may infer permission merely because a decision says `PASS_ASSET_INTAKE_ONLY`.

## Consequences

Pack-level v2 evidence gains an explicit, auditable handoff to one policy decision without
weakening or changing the v1 28-record profile. Canonical byte identities, exact time and policy
binding make replay or silent substitution visible. Independent Qualifier identity and fail-closed
validation keep the two-review closure from becoming self-authorizing.

The 53 pre-existing committed Schemas remain byte-identical. The two append-only request and
decision Schemas increase the committed total to 55; they do not migrate or reinterpret an old
document.

This delivery is deliberately inert. Its tests show only that a synthetic closure can be assessed
against a named qualification policy; the current real private PairCheck is not supplied to the
consumer in this PR. The consumer cannot publish a rights manifest or create any execution
capability. Operational use with real private records is outside this PR and requires a separately
approved local invocation stage.
