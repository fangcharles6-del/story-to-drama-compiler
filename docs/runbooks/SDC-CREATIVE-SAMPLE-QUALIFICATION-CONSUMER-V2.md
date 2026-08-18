# Creative Sample Pack-level Human Review v2 qualification consumer

This runbook describes the inert, purely local consumer that evaluates one exact Pack-level Human
Review v2 closure against one exact qualification policy. It does not operate the private Frozen
Pack used during development of the contract, and it does not authorize generation, publication,
Provider access or any other execution.

## Permanent safety state

Every input and output in this runbook retains:

```text
HUMAN_GATE
NOT_AUTHORIZED
execution_authorized=false
posts_allowed=0
provider_requests=0
rights_manifest_created=false
eligible_for_real_generation=false
```

No entitlement or authorization record is created or modified.

`READY_FOR_SEPARATE_QUALIFICATION_REVIEW` is a zero-permission PairCheck status.
`PASS_ASSET_INTAKE_ONLY` is a zero-permission, scoped qualification decision. The request carries
`rights_qualification_performed=false`; a completed decision carries
`rights_qualification_performed=true` because this consumer really did perform that scoped
assessment. Neither status is a rights manifest, v1 qualification-path result, entitlement,
authorization, publication approval or Runtime instruction.

Do not provide private media, real evidence, reviewer records, account data, an API Key, Ark or
console access, Provider tasks, PostgreSQL data, Temporal history or Atomic Ledger material during
this contract-development stage. Do not start Runtime, Worker, Provider, PostgreSQL or Temporal;
do not use a network, upload, POST, purchase, recharge or claim a trial. Do not modify a positive
entitlement or authorization registry, migration or production safety boundary.

## Delivery boundary

This version adds only:

- one immutable qualification-request contract;
- one immutable qualification-decision contract;
- committed JSON Schemas for those new contracts;
- one deterministic, side-effect-free local compiler; and
- synthetic offline tests and documentation.

There is no operational CLI, workspace generator, private-file loader, rights-manifest builder or
authorization bridge in this delivery. The pure API accepts already validated in-memory contracts
and an explicit UTC-seconds evaluation value. It does not read a clock or filesystem, and it does
not publish a file. Real private operation requires a later, separately approved stage that adds
and audits an appropriate trusted local boundary.

The current real private PairCheck and its evidence/reviewer files are not inputs to this PR. Do
not use them to demonstrate, smoke-test or manually invoke the new consumer. All implementation
tests use synthetic fixtures created under the repository's existing test boundary.

Existing v1 and v2 contracts and schemas remain unchanged. In particular, this consumer must not
call the v1 `qualify_real_asset_candidate_pack` path and must not manufacture the 28 independent
per-asset records expected by that profile.

## Roles and retained records

Reviewer A and Reviewer B remain the two people who completed the exact Pack-level reviews. The
Evidence Preparer is explicitly identified because the unchanged evidence-bundle contract does
not carry that role. A Qualifier is a separate fourth role that applies the bound qualification
policy. `evidence_preparer_ref_sha256`, both reviewer references and `qualifier_ref_sha256` must be
four distinct role references. Together with `evidence_retained_record_sha256` and
`qualifier_record_sha256`, all six retained digests must be pairwise distinct and must not reuse a
Pack-member, provenance, technical, review-record, policy or canonical-contract digest.

The contract can compare identifiers and SHA-256 values, but SHA-256 proves only byte identity.
It does not authenticate a human, prove that four people acted independently or establish that a
policy is legally sufficient. The responsible organization must enforce those controls outside
this pure compiler.

## Exact input closure

A qualification request is admissible only when all of the following exact canonical documents
are available and mutually consistent:

1. one verified fourteen-member `CreativeSampleFrozenRealAssetPackManifest`;
2. one `CreativeSampleRealAssetRightsEvidenceBundleV2` bound to that Pack;
3. one finalized `CreativeSampleRealAssetHumanPackReviewV2` for `REVIEWER_A`;
4. one finalized `CreativeSampleRealAssetHumanPackReviewV2` for `REVIEWER_B`;
5. one `CreativeSampleRealAssetReviewPairCheckV2` over those exact reviews whose status is
   `READY_FOR_SEPARATE_QUALIFICATION_REVIEW` and whose issue list is empty;
6. one explicit Evidence Preparer reference; and
7. the consumer's exact built-in policy identifier, version and normative policy-document
   SHA-256.

The request binds the Pack manifest SHA-256; evidence bundle ID, canonical document SHA-256 and
retained evidence-record SHA-256; review IDs, review-record SHA-256 values and retained reviewer
record SHA-256 values; PairCheck ID and canonical document SHA-256; exact Evidence Preparer
reference; exact policy triple; PairCheck evaluation time; request time; and derived finite
`request_valid_until`. A path, filename, mutable environment variable or "latest" alias is not an
identity.

Before building a request, the caller must revalidate every source contract strictly and recompute
all canonical document digests. The following conditions are hard stops:

- an unknown or duplicate JSON field;
- any malformed or non-canonical contract;
- a stable-ID, SHA-256 or cross-reference mismatch;
- anything other than exactly fourteen ordered Frozen Pack members;
- anything other than one role-correct, distinct A/B review pair;
- a missing, rejected, excepted, inconsistent or future-dated review;
- an `INCOMPLETE`, `DISAGREEMENT`, stale or issue-bearing PairCheck;
- unavailable or changed retained records;
- an Evidence Preparer collision with either reviewer;
- a Qualifier collision with the Preparer or either reviewer when recording a decision;
- missing, ambiguous or unbound policy bytes; or
- expired evidence at the evaluation time.

Do not repair, merge, reinterpret or backfill a failed closure. A corrected source produces a new
canonical source, request and decision.

The pure API does not open an Evidence Preparer, evidence, reviewer, Qualifier-identity or
Qualifier-decision record. It can validate each supplied private-record SHA-256's shape,
independence and binding, but it cannot prove that the underlying file is currently available or
unchanged. The availability items above are operational preconditions, not a claim that this
contract-only PR re-hashes private files. A later trusted local boundary must re-read each
explicitly selected ordinary file and compare its observed digest without discovering directories
or following links.

## Policy binding

The policy identity is a closed three-part binding:

| Part | Meaning |
|---|---|
| `policy_id` | `creative-sample-real-asset-qualification-policy` |
| `policy_version` | `2.0.0` |
| `policy_document_sha256` | `f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031` |
| profile | `creative-sample-real-asset-qualification-assessment-v2` |
| maximum request age | 86,400 seconds (24 hours) |

All three values are fixed by the consumer, included in the request's content-derived ID and
repeated or transitively bound in the decision. They are not free caller input. Changing any
policy byte, identifier or version requires code review, a new fixed triple, and a new request and
decision. A policy cannot widen the evidence bundle's territory, use scope or validity, waive an
A/B disagreement, or convert incomplete review evidence into approval.

The pure compiler binds the built-in `policy_document_sha256`; it does not accept an arbitrary
external policy file or dynamically interpret policy bytes. The digest identifies this version's
committed normative payload and makes a policy change part of the reviewed contract change.

The normative compact canonical JSON payload is exactly the following UTF-8 byte string, with
sorted keys, compact `,` and `:` separators, and no trailing newline:

```json
{"policy_id":"creative-sample-real-asset-qualification-policy","policy_version":"2.0.0","positive_decision":"PASS_ASSET_INTAKE_ONLY","qualification_scope":"ASSET_INTAKE_ONLY","request_max_age_seconds":86400,"rules":["EXACT_UPSTREAM_CANONICAL_CLOSURE","PAIR_READY_WITHOUT_ISSUES","EVIDENCE_VALID_AT_REQUEST_AND_DECISION","PREPARER_REVIEWERS_QUALIFIER_DISTINCT","RETAINED_RECORD_DIGESTS_NON_ALIASING","NO_MANIFEST_NO_GENERATION_NO_AUTHORIZATION"]}
```

Prefix those bytes with the ASCII domain
`sdc:creative-sample-real-asset-qualification-policy:v2` plus one NUL byte, then calculate
SHA-256. The result must equal the public
`QUALIFICATION_V2_POLICY_DOCUMENT_SHA256` constant shown in the table. The fixed payload lives in
`src/sdc/real_asset_qualification_v2.py`: `_QUALIFICATION_POLICY_PAYLOAD` holds the object,
`_POLICY_DIGEST_DOMAIN` holds the NUL-terminated domain bytes, and `_canonical_payload` applies
UTF-8 JSON with `sort_keys=True` and compact separators. Changing its domain, canonical bytes or
rule list requires a reviewed policy/version update.

This version is not a general policy engine. It has no override, waiver, repair, administrator
escape hatch, `--force` mode or fallback policy.

## Contract field closure

The request's exact field groups are:

| Group | Fields |
|---|---|
| Contract identity | `schema_version`, `document_type`, `profile`, `request_id` |
| Policy | `policy_id`, `policy_version`, `policy_document_sha256` |
| Time | `requested_at`, `evaluated_at`, `request_valid_until`, `evidence_valid_until` |
| Pack and evidence | `pack_id`, `pack_manifest_sha256`, `rights_evidence_bundle_id`, `rights_evidence_bundle_sha256`, `evidence_retained_record_sha256`, `evidence_preparer_ref_sha256` |
| Reviewer A | `review_a_id`, `review_a_contract_sha256`, `review_a_record_sha256`, `reviewer_a_retained_record_sha256` |
| Reviewer B | `review_b_id`, `review_b_contract_sha256`, `review_b_record_sha256`, `reviewer_b_retained_record_sha256` |
| PairCheck | `pair_check_id`, `pair_check_sha256` |
| State | `status=QUALIFICATION_REQUESTED`, `rights_manifest_created=false`, `rights_qualification_performed=false`, `current_gate=HUMAN_GATE`, `provider_state=NOT_AUTHORIZED`, `eligible_for_real_generation=false`, `execution_authorized=false`, `posts_allowed=0`, `provider_requests=0` |

The decision binds the request rather than shortening it into an untraceable conclusion:

| Group | Fields |
|---|---|
| Contract identity | `schema_version`, `document_type`, `profile`, `decision_id`, `request_id`, `request_sha256` |
| Transitive closure | `policy_id`, `policy_version`, `policy_document_sha256`, `pack_id`, `rights_evidence_bundle_id`, `review_a_id`, `review_b_id`, `pair_check_id`, `requested_at`, `evaluated_at`, `request_valid_until` |
| Retained records | `evidence_retained_record_sha256`, `evidence_preparer_ref_sha256`, `reviewer_a_retained_record_sha256`, `reviewer_b_retained_record_sha256`, `qualifier_ref_sha256`, `qualifier_record_sha256` |
| Human conclusion | `decision_at`, `qualification_issue_codes`, `qualification_basis`, `decision`, `qualification_scope=ASSET_INTAKE_ONLY`, `eligible_for_separate_manifest_design_review` |
| State | `status=QUALIFICATION_COMPLETE`, `rights_manifest_created=false`, `rights_qualification_performed=true`, `current_gate=HUMAN_GATE`, `provider_state=NOT_AUTHORIZED`, `eligible_for_real_generation=false`, `execution_authorized=false`, `posts_allowed=0`, `provider_requests=0` |

All document SHA-256 fields use the repository's canonical document bytes: UTF-8 JSON with
`ensure_ascii=False`, `indent=2`, `sort_keys=True` and one trailing newline. Request and decision
IDs use `stable_id` over the complete JSON-mode payload excluding only their own ID, with domains
`real_asset_qualification_request_v2` and `real_asset_qualification_decision_v2`. The policy
digest uses its separate domain-separated compact rule above.

The canonical-document hashes are `pack_manifest_sha256`,
`rights_evidence_bundle_sha256`, `review_a_contract_sha256`, `review_b_contract_sha256`,
`pair_check_sha256` and `request_sha256`. By contrast, `review_a_record_sha256` and
`review_b_record_sha256` retain the existing v2 review-record digest semantics; they are not the
two private reviewer files. The private retained identities are
`evidence_retained_record_sha256 == evidence.evidence_record_sha256`,
`reviewer_a_retained_record_sha256 == reviewer_a.reviewer_ref_sha256` and the corresponding B
value, plus the separately supplied Preparer and Qualifier fields. Do not substitute one digest
category for another merely because each has 64 lowercase hexadecimal characters.

## Deterministic request and decision

The compiler receives the complete closure and exact caller-supplied UTC-seconds values. It:

1. strictly revalidates all input contracts;
2. reconstructs the evidence and two review closures from the exact Frozen Pack;
3. reconstructs the PairCheck and requires byte-equivalent identity and a ready state;
4. checks role, retained-record and canonical-contract independence;
5. binds the exact policy and Evidence Preparer reference;
6. derives `CreativeSampleRealAssetQualificationRequestV2` and its stable content ID;
7. binds an independent Qualifier reference, Qualifier record, actual basis and actual decision;
   and
8. derives `CreativeSampleRealAssetQualificationDecisionV2` and its stable content ID.

Tests use fixed UTC values. The pure compiler never reads wall-clock time. UTC values must use
whole-second `YYYY-MM-DDTHH:MM:SSZ` form. The required order is `reviewed_at <= evaluated_at ==
PairCheck.evaluated_at <= requested_at <= decision_at < request_valid_until`. Evidence must remain
valid throughout that interval. A future, expired or boundary-equal value fails closed.

`decision_at` is the neutral contract time for all three outcomes. Every request has a fixed
24-hour maximum lifetime. For finite evidence, `request_valid_until` is
`min(evidence.valid_until, requested_at + 24 hours)`; for `PERPETUAL` evidence it is
`requested_at + 24 hours`. The exclusive upper bound is a versioned contract rule, not an operator
choice or environment setting.

The Qualifier's decision must be explicit. The compiler never recommends, preselects, infers or
changes it. `PASS_ASSET_INTAKE_ONLY` requires every mechanical closure constraint plus the
Qualifier's explicit positive conclusion against the built-in policy identity. It does not mean
that the compiler established legal sufficiency. `REJECTED` and
`NEEDS_HUMAN_REVIEW` remain non-qualified and preserve the actual human-authored
`qualification_basis`. Malformed, ambiguous or inconsistent input raises a closed validation
error; it does not emit a partial or optimistically repaired decision.

`qualification_basis` is required for all outcomes. The allowed issue codes, in canonical order,
are:

1. `EVIDENCE_SCOPE_UNCLEAR`;
2. `POLICY_REQUIREMENT_NOT_MET`;
3. `QUALIFIER_REJECTED_ASSET_INTAKE`; and
4. `OTHER_BLOCKING_ISSUE`.

`PASS_ASSET_INTAKE_ONLY` requires no issue code. `REJECTED` requires at least one code and must
include `QUALIFIER_REJECTED_ASSET_INTAKE`. `NEEDS_HUMAN_REVIEW` requires at least one code and
must not include that rejection code. Every list is unique and follows the order above. Only the
positive outcome derives
`eligible_for_separate_manifest_design_review=true`; that flag is another separate design gate,
not a rights manifest or execution authority.

The public pure functions are `build_real_asset_qualification_request_v2`,
`build_real_asset_qualification_decision_v2` and `verify_real_asset_qualification_closure_v2`.
The public parsers `parse_real_asset_qualification_request_v2_json` and
`parse_real_asset_qualification_decision_v2_json` reject duplicate keys before contract
validation. Callers must use the committed contracts and Schemas rather than hand-building a
lookalike document. Because this PR deliberately provides no operational file boundary, do not
paste private paths into a Python one-liner or treat an in-memory unit-test example as an approved
production command.

## Artifact semantics

| Artifact | Meaning | Authority |
|---|---|---|
| `CreativeSampleRealAssetReviewPairCheckV2` in `READY_FOR_SEPARATE_QUALIFICATION_REVIEW` | Exact A/B structural handoff | Zero |
| `CreativeSampleRealAssetQualificationRequestV2` / `QUALIFICATION_REQUESTED` | Immutable proposal binding Pack, evidence, reviews, PairCheck, Preparer, policy and time; `rights_qualification_performed=false` | Zero |
| `CreativeSampleRealAssetQualificationDecisionV2` / `QUALIFICATION_COMPLETE` with `REJECTED` or `NEEDS_HUMAN_REVIEW` | Qualifier's completed negative or unresolved scoped assessment; `rights_qualification_performed=true` | Zero |
| `CreativeSampleRealAssetQualificationDecisionV2` / `QUALIFICATION_COMPLETE` with `PASS_ASSET_INTAKE_ONLY` | Qualifier explicitly recorded a positive Asset Intake-only conclusion; `eligible_for_separate_manifest_design_review=true`, but manifest and execution remain false | Zero |

No artifact in this table may be renamed to `rights-manifest.json`, placed into a positive
registry, passed to Runtime or treated as permission to publish.

## What this consumer does not do

This consumer must not:

- generate `CreativeSampleRealAssetRightsManifest` or another rights manifest;
- invoke v1 qualification or translate two Pack reviews into 28 v1 records;
- derive a qualified real-asset revision or change Frozen Pack bytes;
- add entitlement or authorization records;
- write an Atomic Ledger claim or migration;
- import or call Runtime, Worker, Provider, PostgreSQL, Temporal or Ark behavior;
- read a Key, contact a console, issue HTTP/Provider/POST requests or upload private material; or
- buy, recharge, activate or claim a trial.

A future manifest consumer requires a separate ADR, versioned contracts, security review and
independent PR. A future authorization or entitlement bridge requires another independent PR
after that. Qualification output alone is never standing or live authority.

## Development verification

Only synthetic fixtures may be used in this PR. Verification must demonstrate at least:

- strict schema validation and rejection of unknown fields;
- stable ID and canonical document SHA-256 binding;
- exact Pack/evidence/review/PairCheck closure reconstruction;
- distinct Evidence Preparer, Reviewer A, Reviewer B and Qualifier identities and records;
- exact policy identifier/version/SHA-256 binding;
- explicit UTC-seconds and validity-boundary behavior;
- positive-empty, rejected-with-rejection-code and needs-review-without-rejection-code canonical
  `qualification_issue_codes` behavior;
- fail-closed behavior for every drift, collision, disagreement and expiry case;
- `PASS_ASSET_INTAKE_ONLY` still carries every zero-authority constant despite `rights_qualification_performed=true`; and
- no import or mutation of Runtime, Worker, Provider, database, ledger, migration, Ark,
  entitlement or authorization boundaries.

Regenerate committed Schemas only through the repository's normal schema target and confirm every
one of the 53 pre-existing Schemas remains byte-identical. Only the two append-only qualification
Schemas may increase the committed total to 55. Run the repository's offline checks without
contacting any paid or remote generation service.

## Stop conditions

Stop without output on any missing, extra, expired, malformed, aliased, future-dated, changed or
conflicting input; any digest, ID, role, policy or time mismatch; any non-ready PairCheck; any
request to fabricate v1 reviews or a rights manifest; or any nonzero execution, publication,
Provider, entitlement or authorization state.

Retain the original source contracts and private records unchanged. Never overwrite a request or
decision. Operational use of real private material is not authorized by this runbook version.
