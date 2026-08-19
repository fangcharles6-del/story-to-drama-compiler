# Creative Sample Rights Manifest Consumer v2.4

## Purpose and stage boundary

This runbook describes the pure in-memory Pack-level Human Review v2 rights-manifest consumer.
It is a contract and compiler development boundary only. It does not describe how to locate, open,
write or operationally use a real Manifest.

The only admitted development data is synthetic and offline. Do not substitute the current real
private Qualification Decision, Request, Qualifier instruction, Qualifier reference, Frozen Pack,
media, Evidence, Reviews, PairCheck or identity records into a test, example or manual invocation.
Do not read repository `output/` or `tmp/`.

The consumer remains deliberately inert:

```text
HUMAN_GATE
NOT_AUTHORIZED
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

Building a synthetic Manifest records that one Manifest model was deterministically formed. It
does not approve real generation, publication, a Provider call or a later local operation.

## Public surface

The implementation module is `sdc.real_asset_rights_manifest_v24`. It exposes one immutable
versioned model, one fail-closed exception type and three public operations:

```python
class RealAssetRightsManifestV24Error(RuntimeError): ...

def build_real_asset_rights_manifest_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    request: CreativeSampleRealAssetQualificationRequestV2,
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
    decision: CreativeSampleRealAssetQualificationDecisionV2,
    manifest_at: str,
) -> CreativeSampleRealAssetRightsManifestV2: ...

def parse_real_asset_rights_manifest_v2_json(
    raw: bytes,
) -> CreativeSampleRealAssetRightsManifestV2: ...

def verify_real_asset_rights_manifest_closure_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    request: CreativeSampleRealAssetQualificationRequestV2,
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
    decision: CreativeSampleRealAssetQualificationDecisionV2,
    manifest: CreativeSampleRealAssetRightsManifestV2,
) -> CreativeSampleRealAssetRightsManifestV2: ...
```

The module also exports the four immutable identity constants
`RIGHTS_MANIFEST_V2_PROFILE`, `RIGHTS_MANIFEST_V2_POLICY_ID`,
`RIGHTS_MANIFEST_V2_POLICY_VERSION` and `RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256` for audit and
Schema verification. They are not configurable inputs.

The reviewed function signatures and exact contract fields are documented below. There is no
`__main__` launcher, CLI subcommand, filesystem loader, path argument, workspace, local finalizer,
output option, network adapter or service endpoint. Callers provide already constructed in-memory
models and an explicit UTC second.

The module must not call the v1 `build_real_asset_rights_manifest` or
`qualify_real_asset_candidate_pack` functions. It must not adapt two Pack reviews into 28 v1
per-asset review records.

## Complete in-memory closure

The build and verify APIs accept the following complete closure explicitly:

| Input | Required condition | Manifest binding |
|---|---|---|
| Frozen Pack manifest | Strict fourteen-member `CreativeSampleFrozenRealAssetPackManifest`. | `pack_id` and canonical Pack-manifest SHA-256. |
| Rights Evidence | Strict `CreativeSampleRealAssetRightsEvidenceBundleV2` bound to the Pack. | Bundle ID and canonical contract SHA-256. |
| Reviewer A | Strict finalized `CreativeSampleRealAssetHumanPackReviewV2` with role `REVIEWER_A`. | Review ID and canonical contract SHA-256. |
| Reviewer B | Strict finalized `CreativeSampleRealAssetHumanPackReviewV2` with role `REVIEWER_B`. | Review ID and canonical contract SHA-256. |
| PairCheck | Exact deterministic A/B PairCheck, ready and issue-free. | PairCheck ID and canonical contract SHA-256. |
| Qualification Request | Exact canonical Request reproducible from the preceding closure. | Request ID and canonical contract SHA-256. |
| Qualifier instruction | Exact canonical v2.2 instruction bound to the Request and Qualifier. | Instruction ID and canonical contract SHA-256. |
| Qualification Decision | Exact canonical Decision reproducible from the Request and instruction. | Decision ID and canonical contract SHA-256. |
| `manifest_at` | Explicit canonical UTC second; never supplied by a clock. | Stored verbatim after strict time checks. |

Supplying only a Decision is insufficient. Its copied IDs and hashes are not treated as proof that
the upstream closure is present or consistent. The consumer strictly revalidates each model and
uses the existing pure qualification closure verifier before building a Manifest.

## Positive admission gate

The consumer accepts exactly this completed Decision state:

```text
decision=PASS_ASSET_INTAKE_ONLY
qualification_scope=ASSET_INTAKE_ONLY
status=QUALIFICATION_COMPLETE
rights_qualification_performed=true
eligible_for_separate_manifest_design_review=true
rights_manifest_created=false
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

It additionally requires the exact built-in qualification policy triple already bound by the
Request and Decision, and adds a separate fixed Manifest-policy triple. It does not accept a
caller-selected policy alias, waiver, updated digest or environment override.

The following always fail closed:

- `REJECTED` or `NEEDS_HUMAN_REVIEW`;
- `eligible_for_separate_manifest_design_review=false`;
- a PairCheck status other than `READY_FOR_SEPARATE_QUALIFICATION_REVIEW`;
- any PairCheck issue;
- any drifted ID, digest, role, ordinal, reference or policy component;
- an incomplete, non-canonical or causally invalid closure, or finite Evidence expired at
  `manifest_at`; or
- any non-zero execution, Provider, generation or post authority.

No API infers or edits the Decision, qualification basis or issue codes. No exception path can
turn an ineligible Decision into a Manifest.

## Two fixed policy bindings

The admitted Request, instruction and Decision retain the SDC-ADR-021 qualification-policy
triple:

```text
qualification_policy_id=creative-sample-real-asset-qualification-policy
qualification_policy_version=2.0.0
qualification_policy_document_sha256=f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031
```

The Manifest additionally binds its own v2.4 policy triple:

```text
manifest_policy_id=creative-sample-real-asset-rights-manifest-policy
manifest_policy_version=2.4.0
manifest_policy_document_sha256=ac31acb7faf86d08752ec37a585d12754af7611d252e8112b41088f3ed71d912
```

The Manifest-policy digest is SHA-256 over the literal domain bytes
`sdc:creative-sample-real-asset-rights-manifest-policy:v2.4\0` followed by compact canonical JSON
for this payload (sorted object keys, UTF-8, no insignificant whitespace). Here `\0` denotes one
NUL byte (`0x00`), not the two printable bytes backslash and `0`:

```json
{
  "policy_id": "creative-sample-real-asset-rights-manifest-policy",
  "policy_version": "2.4.0",
  "positive_decision": "PASS_ASSET_INTAKE_ONLY",
  "qualification_scope": "ASSET_INTAKE_ONLY",
  "rules": [
    "EXACT_V2_UPSTREAM_CANONICAL_CLOSURE",
    "EXACT_RETAINED_INSTRUCTION_BINDING",
    "MANIFEST_AT_NOT_BEFORE_DECISION",
    "EVIDENCE_VALID_AT_MANIFEST",
    "MANIFEST_RECORDS_RIGHTS_ONLY",
    "NO_GENERATION_NO_EXECUTION_NO_PROVIDER_AUTHORIZATION"
  ]
}
```

The displayed indentation is for reading; digest calculation uses the compact canonical form.
Neither policy is a mutable alias or operator input.

## Manifest contract

`CreativeSampleRealAssetRightsManifestV2` is an immutable strict Pydantic v2 model. Unknown
fields are forbidden, strings are strict and the content-derived Manifest ID binds every other
field. Its fixed identity is:

```text
schema_version=2.4.0
document_type=sdc.creative-sample-real-asset-rights-manifest-v2
profile=creative-sample-real-asset-rights-manifest-consumer-v2.4
manifest_id=stable_id("real_asset_rights_manifest_v2", every other field)
```

The field groups are closed:

| Fields | Binding or fixed rule |
|---|---|
| `schema_version`, `document_type`, `profile` | Exact v2.4 identity above. |
| `manifest_id` | Content-derived stable ID over every other Manifest field. |
| `manifest_at` | Explicit caller-supplied canonical UTC second. |
| `manifest_policy_id`, `manifest_policy_version`, `manifest_policy_document_sha256` | Exact built-in v2.4 Manifest-policy triple. |
| `pack_id`, `pack_manifest_sha256` | Exact Pack stable ID and canonical model SHA-256. |
| `rights_evidence_bundle_id`, `rights_evidence_bundle_sha256` | Exact Evidence stable ID and canonical model SHA-256. |
| `evidence_valid_until` | Exact Evidence validity value; UTC second or `PERPETUAL`. |
| `evidence_retained_record_sha256`, `evidence_preparer_ref_sha256` | Exact two Evidence-stage retained-content bindings from the Request. |
| `review_a_id`, `review_a_contract_sha256` | Exact Reviewer A stable ID and canonical contract SHA-256. |
| `review_a_record_sha256`, `reviewer_a_retained_record_sha256` | Exact Reviewer A review-content and retained-reference bindings. |
| `review_b_id`, `review_b_contract_sha256` | Exact Reviewer B stable ID and canonical contract SHA-256. |
| `review_b_record_sha256`, `reviewer_b_retained_record_sha256` | Exact Reviewer B review-content and retained-reference bindings. |
| `pair_check_id`, `pair_check_sha256` | Exact ready, issue-free PairCheck ID and canonical SHA-256. |
| `request_id`, `request_sha256` | Exact Qualification Request ID and canonical SHA-256. |
| `instruction_id`, `instruction_sha256` | Exact Qualifier instruction ID and canonical SHA-256. |
| `decision_id`, `decision_sha256` | Exact Qualification Decision ID and canonical SHA-256. |
| `qualification_policy_id`, `qualification_policy_version`, `qualification_policy_document_sha256` | Exact built-in v2.0 qualification policy triple. |
| `qualifier_ref_sha256`, `qualifier_record_sha256` | Exact Qualifier-reference and complete canonical instruction-record bindings. |
| `decision_at`, `qualification_decision`, `qualification_scope` | Exact positive Decision facts; `PASS_ASSET_INTAKE_ONLY / ASSET_INTAKE_ONLY`. |
| `eligible_for_separate_manifest_design_review` | Fixed `true`, inherited only from the exact positive Decision. |
| `status` | Fixed `RIGHTS_MANIFEST_CREATED`. |
| `rights_qualification_performed`, `rights_manifest_created` | Fixed `true` audit facts. |
| `current_gate`, `provider_state` | Fixed `HUMAN_GATE / NOT_AUTHORIZED`. |
| `eligible_for_real_generation`, `execution_authorized` | Fixed `false`. |
| `posts_allowed`, `provider_requests` | Fixed `0`. |

The eight retained/review digest fields are bindings, not fresh file observations: retained
Evidence, Evidence Preparer reference, A review content, A retained reference, B review content,
B retained reference, Qualifier reference and Qualifier instruction record. This pure module
does not open those private files. A later trusted local boundary must independently reopen and
hash every explicitly selected retained record before publishing a real Manifest.

The contract requires the eight canonical contract digests, two policy digests and two review
content digests to be pairwise distinct. Its six retained-record digests must also be pairwise
distinct. `qualifier_record_sha256` must equal `instruction_sha256` because the complete canonical
instruction is the retained Qualifier decision record; this is the one required cross-set
identity. Every other retained digest must remain outside the contract/review set. These
byte-separation checks detect a copied record; they do not authenticate a person or prove
organizational independence.

The completed Manifest truthfully fixes:

```text
status=RIGHTS_MANIFEST_CREATED
rights_qualification_performed=true
rights_manifest_created=true
HUMAN_GATE
NOT_AUTHORIZED
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

`rights_qualification_performed=true` is inherited from the completed scoped Decision.
`rights_manifest_created=true` is an audit fact about this pure deterministic artifact. Neither
is an entitlement, authorization, publication approval, Provider credential or executable
routing instruction. Do not map either fact to any such state.

The committed `CreativeSampleRealAssetRightsManifestV2.schema.json` is append-only. The 56
earlier Schemas remain byte-identical and this one new Schema brings the total to 57.

## Canonical identity and strict parse

Canonical model bytes use:

```text
UTF-8 without BOM
object keys sorted
two-space indentation
unescaped Unicode where JSON permits it
one final LF
```

All upstream contract digests are SHA-256 over their canonical model bytes. The builder computes
them from the supplied strict models; the API does not accept caller-provided replacement hashes.
The `manifest_id` is the repository `stable_id` over the complete Manifest payload excluding only
that ID.

`parse_real_asset_rights_manifest_v2_json` accepts in-memory JSON bytes only. It rejects:

- empty input or input larger than the fixed 1,048,576-byte bound;
- malformed UTF-8 or a byte-order mark;
- a top-level value other than one JSON object, or non-finite `NaN`/`Infinity` constants;
- duplicate keys at any object depth;
- missing or unknown fields;
- type coercion, malformed SHA-256, invalid fixed values or a stale stable ID;
- fractional, offset, local or otherwise non-canonical timestamps; and
- any state that violates the closed zero-authority contract.

Parsing proves that one value satisfies the Manifest contract. It does not prove that a file is
canonical, that upstream files still exist or that a human is authenticated. Those are duties of
a possible later operational boundary.

## Build semantics

`build_real_asset_rights_manifest_v2` performs these steps in memory:

1. strictly revalidate the eight supplied upstream models;
2. deterministically rebuild and compare the PairCheck, Request and Decision closure;
3. require the instruction's canonical SHA-256 and all Request, policy, Qualifier, outcome,
   issue-code, basis and time fields to replay the Decision exactly;
4. require the exact positive admission gate and fixed policy triple;
5. recompute every upstream stable ID and canonical SHA-256 binding;
6. validate the caller-supplied `manifest_at` and all validity boundaries;
7. construct the fixed zero-authority Manifest payload;
8. derive its content-addressed stable ID; and
9. strictly validate and return the immutable Manifest model.

It does not serialize to a path, create a directory, write a receipt or automatically continue to
another step. An exception means no Manifest model is returned.

## Time and Evidence validity

The build caller supplies `manifest_at` exactly as a whole-second UTC string:

```text
YYYY-MM-DDTHH:MM:SSZ
```

The function has no time default and must not read a wall clock, local timezone, filesystem time,
environment variable or network time. It enforces:

```text
pair_check.evaluated_at <= request.requested_at
request.requested_at <= instruction.decision_at
instruction.decision_at == decision.decision_at
decision.decision_at <= manifest_at
```

The consumer reconstructs the original Decision and therefore still proves that
`decision.decision_at < request.request_valid_until`. The exclusive Request deadline governs when
the qualification Decision could be made; it does not impose a second deadline on later
deterministic consumption of that completed Decision.

The consumer independently revalidates the Evidence Bundle and requires
`manifest_at < evidence.valid_until` when that field is not `PERPETUAL`. That finite Evidence
upper bound is exclusive. `PERPETUAL` imposes no additional Manifest timestamp bound.

The Manifest cannot extend, renew, round or replace Evidence validity. Verification reuses the
Manifest's immutable `manifest_at` and reads no current time. Historical verification after
expiry does not authorize building a fresh Manifest at or after finite Evidence expiry.

## Verification semantics

`verify_real_asset_rights_manifest_closure_v2` accepts the complete upstream closure and one
in-memory Manifest. It:

1. strictly revalidates the supplied Manifest;
2. revalidates and deterministically reconstructs the full qualification closure;
3. rebuilds the expected Manifest using the Manifest's recorded `manifest_at`; and
4. requires exact model equality before returning the verified Manifest.

It does not repair, normalize, replace or reissue the supplied value. It reads no wall clock and
writes nothing. A valid Manifest cannot be replayed against another Pack, Evidence contract,
review pair, PairCheck, Request, Decision, policy version or creation time because those identities
are all bound transitively.

## Synthetic offline test procedure

Use only fixed synthetic fixtures built inside the test suite. Tests must not contain a real ID,
digest, path, private record excerpt or copied real contract.

The minimum positive test creates a synthetic fourteen-member Pack closure, issue-free PairCheck,
finite Evidence, positive Request, exact Qualifier instruction and `PASS_ASSET_INTAKE_ONLY`
Decision, then supplies a fixed `manifest_at` after the Decision and before the finite Evidence
expiry. It checks deterministic model equality, stable ID, canonical parse and complete
verification.

One positive finite-Evidence case intentionally places `manifest_at` after
`request.request_valid_until` but before `evidence.valid_until`. This locks the distinction between
historical Decision timeliness and current Evidence validity.

Negative tests cover at least:

- each missing or drifted upstream binding;
- reversed reviewer roles, PairCheck disagreement and non-empty issues;
- a Request or Decision that cannot be reproduced from the exact closure;
- `REJECTED`, `NEEDS_HUMAN_REVIEW` and false manifest-design eligibility;
- changed qualification policy components;
- creation before the Decision, at the finite Evidence deadline and after finite Evidence expiry;
- malformed UTC, duplicate JSON keys, unknown fields, coercion and a stale Manifest ID;
- changed Pack ordinals, asset count, canonical digest or stable ID;
- every attempted non-zero authority value; and
- proof that no v1 builder or qualification function is invoked.

Run repository non-integration checks after adding the Schema. The audit must confirm P0/P1/P2 are
zero and that the normalized-LF bytes of all 56 baseline Schemas are unchanged.

## Explicit prohibitions

This stage must not:

- provide a filesystem CLI, trusted path loader, workspace or Manifest finalizer;
- read or generate the current real private Manifest or any current real upstream artifact;
- scan directories, expand globs, select aliases or write repository `output/` or `tmp/`;
- call a v1 rights-manifest or qualification path or invent 28 v1 review records;
- change entitlement or authorization state;
- touch Runtime, Worker, Provider, PostgreSQL, Temporal, Ark, Atomic Ledger or migration code; or
- use a network, Key, upload, POST, purchase, recharge, trial or service.

## Later stages

Merging this PR authorizes no real-data operation. A trusted local Manifest boundary, if desired,
requires a separate ADR and PR covering explicit absolute paths, repository-external isolation,
bounded reads, strict canonical files, no links or aliases, TOCTOU detection, create-new output,
rollback and read-only historical verification. It must receive a new explicit approval before it
reads the real private Decision.

Even such a future real Manifest would remain `HUMAN_GATE / NOT_AUTHORIZED`. Any entitlement,
authorization, generation or publication bridge is a distinct later policy and engineering stage;
it cannot infer permission from `PASS_ASSET_INTAKE_ONLY`,
`rights_qualification_performed=true` or `rights_manifest_created=true`.
