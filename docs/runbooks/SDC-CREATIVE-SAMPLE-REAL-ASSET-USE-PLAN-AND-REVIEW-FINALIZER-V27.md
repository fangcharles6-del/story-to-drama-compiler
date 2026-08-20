# Trusted Local Real Asset Use Plan and Review Finalizer v2.7

## Purpose and status

This runbook is the accepted operational design for SDC-ADR-028. It defines a trusted-local
boundary that can:

1. inspect, create-new and historically verify one exact
   `CreativeSampleRealAssetUsePlanV1`; and
2. preserve the Maker -> Checker -> compiler chain while create-new finalizing and historically
   verifying one exact `CreativeSampleRealAssetUseScopeReviewRecordV1`.

The boundary is approved for synthetic-only source and test implementation. Availability of these
commands in a checkout does not authorize substituting real private paths, creating real authoring
inputs or artifacts, or running any real operation. Commit, push, PR publication, merge and every
real command remain separately controlled.

The boundary consumes the existing v1 artifact contracts and v2.6.0 policies. It adds no contract
or Schema. The strongest positive Review result remains eligibility to design a separate Provider
proposal. It is not Provider approval, entitlement, generation readiness, execution authority or
publication permission.

## Modules and command set

The modules are:

```text
sdc.real_asset_use_plan_finalizer_v27
sdc.real_asset_use_scope_review_finalizer_v27
```

The Use Plan operations are:

```text
inspect-use-plan-ready
finalize-use-plan
verify-use-plan
```

The Review operations are:

```text
preflight-review-request
preflight-review-instruction
finalize-review-record
verify-review-record
```

Request preflight builds only the immutable Maker-owned Request and exposes its approval anchor.
Instruction preflight rebuilds and guards that Request, builds the immutable Checker-owned
Instruction, and transiently derives compiler-owned Decision and Record anchors for exact write
approval. It persists none of them. There is no combined Request/Instruction file, no Decision
input, no mutable session file and no automatically invoked next command.

This release deliberately omits a recorded-window currentness command. If a later fresh-status ADR
adds one, it must be a separate operation with explicit `observed_at`, full historical closure
verification and fresh hold/revocation/status evidence. It must not be an optional mode of
historical verification.

## Python public surface

The Use Plan module exposes frozen operational dataclasses only; none is a Pydantic artifact or
committed Schema:

```text
TrustedLocalUsePlanPaths(
  manifest_sources: TrustedLocalRightsManifestPaths,
  rights_manifest: Path,
)
UsePlanReadinessV27(status, plan_id, plan_sha256)

inspect_use_plan_ready(paths) -> UsePlanReadinessV27
finalize_use_plan(
  paths, output_path, *, expected_plan_id, expected_plan_sha256
) -> CreativeSampleRealAssetUsePlanV1
verify_use_plan(
  paths, use_plan_path
) -> CreativeSampleRealAssetUsePlanV1
```

Its failure types are `TrustedLocalUsePlanFinalizationError` and the dedicated
`TrustedLocalUsePlanQuarantineRequired` subclass. Its exact `__all__` is:

```text
TrustedLocalUsePlanPaths
UsePlanReadinessV27
TrustedLocalUsePlanFinalizationError
TrustedLocalUsePlanQuarantineRequired
inspect_use_plan_ready
finalize_use_plan
verify_use_plan
main
```

The Review module exposes these frozen operational path and summary dataclasses:

```text
TrustedLocalUsePlanArtifactPaths(
  sources: TrustedLocalUsePlanPaths,
  use_plan: Path,
)
TrustedLocalUseScopeReviewRequestPaths(
  plan: TrustedLocalUsePlanArtifactPaths,
  maker_identity_ref: Path,
  maker_input: Path,
)
TrustedLocalUseScopeReviewInstructionPaths(
  request: TrustedLocalUseScopeReviewRequestPaths,
  checker_identity_ref: Path,
  checker_input: Path,
)
TrustedLocalUseScopeReviewVerificationPaths(
  plan: TrustedLocalUsePlanArtifactPaths,
  maker_identity_ref: Path,
  checker_identity_ref: Path,
)
UseScopeReviewRequestPreflightV27(status, request_id, request_sha256)
UseScopeReviewInstructionPreflightV27(
  status,
  instruction_id,
  instruction_sha256,
  decision_id,
  decision_sha256,
  record_id,
  record_sha256,
)
```

The exact operations are:

```text
preflight_review_request(
  paths, *, requested_at
) -> UseScopeReviewRequestPreflightV27
preflight_review_instruction(
  paths, *, requested_at, evaluated_at,
  expected_request_id, expected_request_sha256
) -> UseScopeReviewInstructionPreflightV27
finalize_review_record(
  paths, output_path, *, requested_at, evaluated_at,
  expected_request_id, expected_request_sha256,
  expected_instruction_id, expected_instruction_sha256,
  expected_decision_id, expected_decision_sha256,
  expected_record_id, expected_record_sha256
) -> CreativeSampleRealAssetUseScopeReviewRecordV1
verify_review_record(
  paths, record_path
) -> CreativeSampleRealAssetUseScopeReviewRecordV1
```

Its failure types are `TrustedLocalUseScopeReviewFinalizationError` and the dedicated
`TrustedLocalUseScopeReviewQuarantineRequired` subclass. Its exact `__all__` is:

```text
TrustedLocalUsePlanArtifactPaths
TrustedLocalUseScopeReviewRequestPaths
TrustedLocalUseScopeReviewInstructionPaths
TrustedLocalUseScopeReviewVerificationPaths
UseScopeReviewRequestPreflightV27
UseScopeReviewInstructionPreflightV27
TrustedLocalUseScopeReviewFinalizationError
TrustedLocalUseScopeReviewQuarantineRequired
preflight_review_request
preflight_review_instruction
finalize_review_record
verify_review_record
main
```

No convenience API accepts a caller-supplied Request, Instruction or Decision model. The
trusted-local operations always reconstruct them from the exact physical closure and authoring
inputs in the fixed pure-builder order.

## CLI invocation and serialization

The exact launch prefixes are:

```text
python -m sdc.real_asset_use_plan_finalizer_v27 <command>
python -m sdc.real_asset_use_scope_review_finalizer_v27 <command>
```

Success writes exactly one compact, sorted-key, UTF-8 JSON object plus one LF to stdout and writes
nothing to stderr. Every success object includes:

```json
{
  "current_gate": "HUMAN_GATE",
  "execution_authorized": false,
  "posts_allowed": 0,
  "provider_requests": 0,
  "provider_state": "NOT_AUTHORIZED"
}
```

The command-specific `operation`, `status` and approval-anchor members shown below are added to
that object. Success exits `0`.

Failure writes nothing to stdout and exactly one bounded compact sorted-key JSON object plus LF to
stderr. Ordinary failure uses `{"error":"FAILED_CLOSED"}` and exits `2`; uncertain rollback uses
`{"error":"ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"}` and exits `3`. No diagnostic includes a
private path, human text, identity content, artifact content or variable exception string.

All expected SHA-256 values must match lowercase `[0-9a-f]{64}`. Expected stable IDs must match the
exact existing contract pattern for their type:

```text
real_asset_use_plan_v1_[0-9a-f]{20}
real_asset_use_scope_request_v1_[0-9a-f]{20}
real_asset_use_scope_instruction_v1_[0-9a-f]{20}
real_asset_use_scope_decision_v1_[0-9a-f]{20}
real_asset_use_scope_review_record_v1_[0-9a-f]{20}
```

Malformed expected values fail during argument parsing before any private path is opened.

## Decisions already fixed

The following constraints are not open:

- only `finalize-use-plan` and `finalize-review-record` may write;
- a successful Plan finalization creates exactly one complete canonical Plan;
- a successful Review finalization creates exactly one complete canonical outer Record;
- Request, Instruction and Decision remain three nested physical modules with independent stable
  IDs and standard canonical-document SHA-256 values;
- no Request, Instruction or Decision operational file is created;
- no Record path is progressively appended, rewritten or used as workflow state;
- every operation performs a fresh complete path and byte capture;
- cross-stage approval uses recomputed expected ID/SHA equality guards, never a cache or receipt;
- Plan operations add no time and historical verification reads no clock;
- Maker and Checker use two explicitly selected repository-external identity-reference files;
- every write uses exclusive create-new with exact-handle rollback and quarantine semantics;
- valid PASS, NEEDS_REVISION and REJECTED Records may be retained as audit facts; and
- every state remains zero-authority.

## Full physical closure

The v2.7 boundary freezes `FULL_PHYSICAL_CLOSURE`. It reuses every explicitly named v2.5
physical source entry and adds one explicitly selected existing Rights Manifest. Every operation
therefore re-proves the current identity and bytes of the Pack anchor, Pack Manifest, fourteen
media objects, Evidence, two Reviews, PairCheck, five retained or identity references,
Qualification Request, Qualification Instruction, Qualification Decision and Rights Manifest.

There is no reduced contract-only profile or missing-path fallback. The table is the normative
normative source-count contract. It assumes the two bounded authoring files
specified below.

| Operation | Existing explicit sources | Absent output | Source count |
|---|---:|---:|---:|
| `inspect-use-plan-ready` | v2.5 physical 28 + Rights Manifest | 0 | 29 |
| `finalize-use-plan` | v2.5 physical 28 + Rights Manifest | Plan | 29 |
| `verify-use-plan` | v2.5 physical 28 + Rights Manifest + Plan | 0 | 30 |
| `preflight-review-request` | preceding 30 + Maker identity + Maker authoring input | 0 | 32 |
| `preflight-review-instruction` | preceding 30 + two identities + two authoring inputs | 0 | 34 |
| `finalize-review-record` | same 34 | Record | 34 |
| `verify-review-record` | preceding 30 + two identities + Record | 0 | 33 |

Pack root is one explicit anchor entry, not a file and not a directory-enumeration request. The
fourteen media paths remain fourteen separately supplied entries in exact Pack ordinal order.

## Common physical-closure options

The exact common options are:

```text
--pack-root <absolute-pack-root>
--pack-manifest <absolute-asset-pack.json>
--media-path <absolute-media-ordinal-0>
--media-path <absolute-media-ordinal-1>
--media-path <absolute-media-ordinal-2>
--media-path <absolute-media-ordinal-3>
--media-path <absolute-media-ordinal-4>
--media-path <absolute-media-ordinal-5>
--media-path <absolute-media-ordinal-6>
--media-path <absolute-media-ordinal-7>
--media-path <absolute-media-ordinal-8>
--media-path <absolute-media-ordinal-9>
--media-path <absolute-media-ordinal-10>
--media-path <absolute-media-ordinal-11>
--media-path <absolute-media-ordinal-12>
--media-path <absolute-media-ordinal-13>
--evidence <absolute-evidence.json>
--reviewer-a <absolute-reviewer-a.json>
--reviewer-b <absolute-reviewer-b.json>
--pair-check <absolute-pair-check.json>
--evidence-retained-record <absolute-evidence-record>
--evidence-preparer-ref <absolute-evidence-preparer-reference>
--reviewer-a-retained-record <absolute-reviewer-a-reference>
--reviewer-b-retained-record <absolute-reviewer-b-reference>
--qualification-request <absolute-qualification-request.json>
--qualifier-ref <absolute-qualifier-reference>
--qualification-instruction <absolute-qualification-instruction.json>
--qualification-decision <absolute-qualification-decision.json>
--rights-manifest-file <absolute-rights-manifest.json>
```

The `qualification-*` spelling avoids ambiguity with the new Use Scope Request and Instruction.
Only `--media-path` repeats, exactly fourteen times in ordinal order. Every singleton option rejects
duplication and abbreviation. No operation accepts a directory-discovery option, glob, `--force`,
overwrite, repair, policy override, ID override, digest override, Decision override, default time
or authority flag.

The exact comparison-only `--expected-*` guards defined below are the only ID/SHA inputs. They can
never override a calculated value.

## Human-input transport

### Threat

`request_basis`, `checker_basis` and failed-gate notes must not appear directly in command-line
arguments. Doing so exposes human text to process listings and shell history and creates platform
quoting and Unicode ambiguity. A combined mutable review draft would also erase the Maker/Checker
boundary.

### Bounded authoring files

The exact transport uses two explicitly selected repository-external canonical UTF-8 JSON sources.
They are hostile authoring inputs, not versioned contracts, not authority artifacts and not outputs
of this boundary.

The Maker authoring input contains only:

```json
{
  "request_basis": "synthetic example only"
}
```

`requested_at` remains a separate required canonical UTC-second option so every approval draft
shows it prominently.

The Checker authoring input contains only:

```json
{
  "checker_basis": "synthetic example only",
  "disposition": "NEEDS_REVISION",
  "gate_results": [
    {"approved": false, "gate": "COPYRIGHT_USE_SCOPE", "note": "synthetic note"},
    {"approved": true, "gate": "LIKENESS_USE_SCOPE", "note": null},
    {"approved": true, "gate": "PRIVACY_USE_SCOPE", "note": null},
    {"approved": true, "gate": "TERRITORY_USE_SCOPE", "note": null},
    {"approved": true, "gate": "CONTENT_ROLE_USE_SCOPE", "note": null},
    {"approved": true, "gate": "OFFLINE_ONLY_RESTRICTIONS", "note": null}
  ]
}
```

`evaluated_at` remains a separate explicit UTC-second option. The expected Request pair is also a
separate comparison-only CLI input; it is not part of the Checker authoring file.

Each authoring source is an ordinary, single-link file of at most 65,536 bytes. It uses strict
canonical UTF-8 JSON with no BOM, duplicate keys, non-finite constants, unknown fields, defaulting
or coercion. Keys are sorted, indentation is two spaces, Unicode is unescaped where JSON permits it
and the document has exactly one final LF. Its filename has a case-insensitive exact `.json`
suffix.

Basis strings are non-empty and at most 2,000 characters. Gate notes are at most 1,000 characters.
Every human string must already be NFC, equal its own `strip()`, and contain no C0 or DEL control
character. An approved gate has a null note; a failed gate has a non-empty note. The parser never
trims, normalizes, repairs or supplies a default.

Both files must be inside separately approved private source areas. On POSIX the effective user
owns each file and its mode is exactly `0600`. On Windows the owner is the effective token-user SID
and the file has the same exact protected owner-only DACL predicate required for v2.7 outputs. The
boundary verifies permissions before reading any human text and fails closed if they are broader or
cannot be established.

There is no standard-input, interactive, environment-variable or combined mutable-draft fallback.

## Approval-anchor rules

Each preflight builds from exact current bytes before it reports an anchor:

```text
Plan anchor        = plan_id + SHA256(canonical complete Plan)
Request anchor     = request_id + SHA256(canonical complete Request)
Instruction anchor = instruction_id + SHA256(canonical complete Instruction)
Decision anchor    = decision_id + SHA256(canonical complete Decision)
Record anchor      = record_id + SHA256(canonical complete Record)
```

An expected anchor is accepted only as a comparison value. The operation must:

1. read and verify the complete current operation closure;
2. invoke the existing pure builder for the applicable value;
3. derive the stable ID and canonical-document SHA-256 from that value;
4. compare both calculated values with the separately approved expected pair; and
5. fail closed on either mismatch before performing the next stage or opening an output.

An expected anchor must not:

- identify a file or select a candidate;
- replace any source read;
- enter a builder payload as the caller-supplied expected copy;
- override, repair or normalize a calculated field;
- skip Manifest, Plan or identity verification;
- be written to a receipt or cache;
- prove human identity; or
- grant Provider, generation, execution or publication authority.

After the Request comparison succeeds, the Instruction builder still derives and binds the
calculated Request ID/SHA from the rebuilt immutable Request. That normal computed binding is not
the caller-supplied expected copy and is required by the existing v2.6 contract.

## `inspect-use-plan-ready`

Inputs are the complete 29-source Plan closure. No output path or time is accepted.

The operation:

1. admits every exact path and captures the complete physical closure;
2. strictly parses and historically reconstructs the Rights Manifest;
3. calls `build_real_asset_use_plan_v1` in memory;
4. verifies every fixed policy, known vector, fourteen-member mapping, planned specification,
   compilation and zero-authority field;
5. computes the candidate Plan ID and standard canonical-document SHA-256;
6. captures the complete source closure again and requires exact equality; and
7. writes nothing and stops.

In addition to the five common zero-authority members, its command-specific success members are:

```text
operation=inspect-use-plan-ready
status=READY_FOR_USE_PLAN_FINALIZATION
plan_id=<calculated-plan-id>
plan_sha256=<calculated-canonical-document-sha256>
```

The summary is an approval anchor, not a Plan file or authorization. It prints no private path,
source content, Manifest detail or media fact.

## `finalize-use-plan`

Required additional inputs are:

```text
--expected-plan-id <separately-approved-plan-id>
--expected-plan-sha256 <separately-approved-plan-sha256>
--output <absolute-absent-use-plan.json>
```

Finalization does not consume an inspection cache. It repeats the complete closure capture and
Plan build, requires both calculated Plan anchor values to match, and only then opens the one
absent output using exclusive create-new semantics. It writes the complete canonical Plan, flushes,
rereads through the retained exact handle, strictly parses and compares it, repeats the complete
source capture and checks every close.

Its command-specific success members are:

```text
operation=finalize-use-plan
status=USE_PLAN_FINALIZED
```

The operation never overwrites or repairs an existing path. It does not automatically verify,
preflight a Review or create a Record.

## `verify-use-plan`

Required additional input is:

```text
--use-plan-file <absolute-existing-use-plan.json>
```

Historical verification strictly reads the Plan and the complete accepted upstream closure,
invokes `verify_real_asset_use_plan_closure_v1`, requires exact canonical equivalence and repeats
the source capture. It reads no clock, does not assess current rights status, creates no receipt
and writes nothing.

Its command-specific success members are:

```text
operation=verify-use-plan
status=USE_PLAN_HISTORICALLY_VERIFIED
```

## `preflight-review-request`

Required additional inputs are:

```text
--use-plan-file <absolute-existing-use-plan.json>
--maker-identity-ref <absolute-maker-identity-reference>
--maker-input <absolute-maker-authoring-input.json>
--requested-at <YYYY-MM-DDTHH:MM:SSZ>
```

The operation verifies the complete Plan closure, safely reads the Maker reference and Maker
authoring source, and calls only `build_use_scope_review_request_v1`. It accepts no Checker field,
expected Instruction value, Decision field or output path.

Its command-specific success members are:

```text
operation=preflight-review-request
status=REVIEW_REQUEST_READY_FOR_CHECKER_PREFLIGHT
request_id=<calculated-request-id>
request_sha256=<calculated-canonical-document-sha256>
```

The operation writes nothing and stops. A human must separately approve the exact Request anchor
before preparing the Checker authoring input.

## `preflight-review-instruction`

Required additional inputs are the complete Request-preflight inputs plus:

```text
--expected-request-id <separately-approved-request-id>
--expected-request-sha256 <separately-approved-request-sha256>
--checker-identity-ref <absolute-checker-identity-reference>
--checker-input <absolute-checker-authoring-input.json>
--evaluated-at <YYYY-MM-DDTHH:MM:SSZ>
```

The operation fresh reconstructs the Plan and Request, compares both Request anchor values,
enforces identity path, file and digest separation, and then calls
`build_use_scope_review_instruction_v1`. It next calls `build_use_scope_review_record_v1` in memory
to derive the exact candidate Decision and complete Record for write approval.

Its command-specific success members are:

```text
operation=preflight-review-instruction
status=REVIEW_INSTRUCTION_READY_FOR_RECORD_FINALIZATION
instruction_id=<calculated-instruction-id>
instruction_sha256=<calculated-canonical-document-sha256>
decision_id=<calculated-decision-id>
decision_sha256=<calculated-canonical-document-sha256>
record_id=<calculated-record-id>
record_sha256=<calculated-canonical-document-sha256>
```

It writes nothing and stops. It does not persist a Decision or Record. A human must separately
approve the exact Instruction, Decision and Record anchors before Record finalization.

## `finalize-review-record`

Required additional inputs are all Instruction-preflight inputs plus:

```text
--expected-instruction-id <separately-approved-instruction-id>
--expected-instruction-sha256 <separately-approved-instruction-sha256>
--expected-decision-id <separately-approved-decision-id>
--expected-decision-sha256 <separately-approved-decision-sha256>
--expected-record-id <separately-approved-record-id>
--expected-record-sha256 <separately-approved-record-sha256>
--output <absolute-absent-review-record.json>
```

The operation performs this fixed sequence:

```text
fresh complete closure capture
  -> build immutable Request
  -> compare expected Request ID and SHA
  -> build immutable Instruction against that Request
  -> compare expected Instruction ID and SHA
  -> build deterministic Decision and complete outer Record exactly once
  -> compare expected Decision ID/SHA and complete Record ID/SHA
  -> create-new one complete canonical Record
  -> same-handle verify and complete post-write source capture
```

The finalizer accepts no Decision, issue-code, deadline, eligibility or authority override. The
existing pure compiler derives the Decision solely from the exact Request, Instruction and fixed
policy.

PASS, NEEDS_REVISION and REJECTED may all be finalized when their gates, notes and dispositions
form a valid pure closure. Negative Records remain important audit facts. They do not become
current proposal-design eligibility.

Its command-specific success members are:

```text
operation=finalize-review-record
status=USE_SCOPE_REVIEW_RECORD_FINALIZED
```

No Request, Instruction, Decision, draft, receipt, cache or pointer is created by the operation.

## `verify-review-record`

Required additional inputs are:

```text
--use-plan-file <absolute-existing-use-plan.json>
--maker-identity-ref <absolute-maker-identity-reference>
--checker-identity-ref <absolute-checker-identity-reference>
--review-record-file <absolute-existing-review-record.json>
```

The Maker and Checker authoring sources are not required. Their accepted text and choices are
already bound inside the nested Request and Instruction modules. The two identity files are still
required so their exact current whole-file digests can be matched against the embedded references.

The operation:

1. verifies the complete Manifest and Plan closure;
2. verifies identity path, file and whole-file digest separation;
3. strictly parses the complete outer Record;
4. invokes `verify_use_scope_review_record_closure_v1`;
5. invokes each existing pure extractor to re-establish the three canonical module byte streams;
6. requires all module IDs, digests, downstream bindings and outer `record_id` to match; and
7. repeats the complete source capture and writes nothing.

It reads no wall clock and makes no current hold/revocation claim. Historical verification remains
possible after recorded deadlines.

Its command-specific success members are:

```text
operation=verify-review-record
status=USE_SCOPE_REVIEW_RECORD_HISTORICALLY_VERIFIED
```

## Time rules

Plan inspection, finalization and historical verification accept no time and read no clock.

Review formation requires two explicitly approved canonical UTC seconds:

```text
requested_at
evaluated_at
```

They must satisfy:

```text
manifest_at <= requested_at <= evaluated_at < requested_at + 86400 seconds
```

For finite Evidence:

```text
requested_at < evidence_valid_until
evaluated_at < evidence_valid_until
```

The pure compiler sets:

```text
decision_at = evaluated_at
review_valid_until = evaluated_at + 2592000 seconds
```

and truncates the latter to a finite Evidence deadline when earlier. Every upper bound is
exclusive. No operation defaults to `now`, local timezone, filesystem time, environment time or
network time. Historical verification accepts neither a new time nor `observed_at`.

## Path admission and trust-area isolation

Every input and output path must be explicit, absolute, local and outside every Git tree. Reject:

- empty or relative paths;
- UNC/network, device, extended-device and alternate-data-stream paths;
- symbolic links, junctions, reparse points, non-anchor mounts and bind mounts;
- hard-linked or non-regular files;
- case-folded, resolved-path, opened-identity or whole-file aliases;
- directory, glob, `latest`, `current` or `newest` discovery; and
- any attempt to read repository `output/` or `tmp/`.

The isolation rule applies both to new outputs and to existing Manifest, Plan and Record artifacts
selected for preflight or verification. The Manifest parent is separate from all 28 upstream
entries. The Plan parent is separate from those entries and the Manifest.
`finalize-review-record` isolates the new Record parent from every preceding area, both identities
and both authoring-input areas. Historical Record verification does not reopen the authoring
inputs; it isolates the existing Record from every source in its 33-entry verification closure.
Preflight checks only the sources it actually receives. Equality and ancestor/descendant overlap
are rejected. Every new or existing Plan/Record filename has a case-insensitive exact `.json`
suffix. For each path component, Unicode `casefold()` is split on runs outside ASCII `[a-z0-9]`;
the component tokens `latest`, `current` and `newest` are rejected. The same tokenization of the
filename stem rejects `pass`, `needs`, `rejected`, `revision`, `approved` and `authorized`.

## Bounded reads and composite snapshots

Every existing file is admitted without following redirection, opened as the exact expected
ordinary single-link object, read within a compile-time bound, hashed and identity-checked before
and after reading. Inspect, preflight and verify capture their entire source set at least twice.
Each finalizer captures the complete set before build, immediately before create-new and after
same-handle output verification. The first two captures must agree before output open and the final
capture must still agree. Every capture compares path, handle, volume/device, file-ID/inode,
link-count, size, time and digest facts.

Any short or extra read, replacement, relink, handle/path disagreement or capture drift fails
closed. No command emits success from a partially stable closure.

The implementation must not create a split snapshot by calling the v2.5 verifier and later
reopening only the nine model files. All reads used to construct a Plan or Record must be sealed to
the same composite snapshot, followed by a complete post-operation capture.

The inherited compile-time bounds are 1,048,576 bytes for each upstream JSON or retained/private
reference, 67,108,864 bytes per media object and 1,048,576 bytes for fixed platform mount metadata.
Each authoring input is at most 65,536 bytes. The candidate Plan is at most 4,194,304 canonical
bytes and the candidate Record at most 2,097,152 canonical bytes; candidate size is checked before
output open.

Before output open and after same-handle reread, the candidate digest must not alias any source,
identity, authoring input, policy, retained, media, provenance or technical digest. The only
inherited file-digest equality exception is the canonical Qualification Instruction file SHA-256
equaling `qualification_decision.qualifier_record_sha256`. Expected-guard equality is not a source
alias exception.

## Create-new commit, rollback and quarantine

Only the two finalizers open outputs. An output parent must already exist and the output must be
absent. Admission retains a guarded physical identity for the parent and revalidates it immediately
before create-new. A swap detected by that check fails before open. A rename or swap racing after
the check is detected before commit and triggers exact-handle rollback; the boundary does not claim
an impossible race-free pathname precheck. The implementation uses exclusive create-new and
retains the exact file descriptor through:

```text
write complete canonical bytes
flush file and required directory metadata
same-handle bounded reread
strict parse and exact canonical/model comparison
complete source recapture
checked descriptor and parent-guard close
```

There is no overwrite, append, truncate-existing, repair, automatic retry, backup-as-authority or
rename-as-latest mode.

On POSIX creation uses `openat` relative to the guarded parent directory descriptor with
`O_NOFOLLOW|O_CREAT|O_EXCL|O_CLOEXEC` and mode `0600`; `fstat` verifies the effective-user owner and
exact mode. On Windows creation uses `CreateFileW` on the guarded normalized full path with desired
access `GENERIC_READ|GENERIC_WRITE|DELETE`, share mode `0`, creation disposition `CREATE_NEW`,
`FILE_ATTRIBUTE_NORMAL`, a non-inheritable handle and an explicit protected security descriptor.
`FILE_SHARE_DELETE` is therefore never granted while the retained output handle is live. The owner
is the effective token-user SID and the DACL contains exactly one non-inherited allow ACE for that
SID with `FILE_ALL_ACCESS`; no other ACE is admitted. `GetSecurityInfo` verifies that owner,
protected DACL and normalized access mask. Windows rechecks the guarded parent and full-path
identity after create and before commit because this boundary does not use an undocumented NT
parent-relative create primitive.

If any failure or `BaseException` occurs after creation begins and the retained descriptor is
provably live, rollback first invalidates the exact created object through that descriptor. If a
descriptor-close side effect cannot be determined, rollback must not retry, reuse or operate
through that descriptor number. It returns the dedicated quarantine-required result; any
parseable remnant is quarantined and is not an artifact or authority.

On POSIX, rollback performs no pathname unlink. It poisons through the retained file descriptor
and, while retaining the guarded parent directory descriptor, proves after close that the name is
absent or still identifies the exact invalidated inode. On Windows, rollback requests deletion only
through the exact OS handle, checks the `CloseHandle` result and treats delete-pending as confirmed
only after close succeeds and the target name is absent. An independent replacement is never
deleted. A file-handle or parent-guard close failure after creation may have occurred is
quarantine-required.

If exact invalidation or deletion cannot be proven, report:

```text
ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED
```

and require isolation of the complete exact output trust area. A zero-byte or otherwise invalid
remnant is not an artifact and must not be repaired or overwritten. Ordinary failures report
`FAILED_CLOSED`.

## Bounded diagnostics

Success exits `0`, ordinary failed-closed input or runtime failure exits `2`, and unconfirmed
rollback/quarantine exits `3`. Diagnostics are bounded and must not disclose private paths, basis
text, gate notes, identity contents, source bytes, Manifest details or Decision reasoning.

The only variable success values are the Plan, Request, Instruction, Decision and Record IDs and
canonical SHA-256 values required for explicit cross-stage approval. These values are not written
to files and are not authority tokens.

## Zero-authority assertions

Every accepted artifact must retain:

```text
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
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
authorized_attempts=0
authorized_cost_cny=0
posts_allowed=0
provider_requests=0
```

A valid PASS may set only `eligible_for_separate_provider_proposal=true`. A valid NEEDS_REVISION or
REJECTED Record keeps that value false. The Plan's 20 proposed requests and CNY 450 cost ceiling
remain planning facts, never authorization.

Every bounded CLI summary includes the five common zero-authority members plus the fixed operation,
status and explicitly listed approval anchors. Other contract false/zero fields remain in the
artifact and no summary may state or imply an authority-bearing positive conclusion.

## Synthetic-only test plan

The implementation PR must reuse only synthetic v2.5 closure and v2.6 pure-model fixtures inside
isolated temporary directories. It must not read a current private path, repository `output/` or
`tmp/`, a Key, environment-selected policy/time or any remote service.

### Artifact and responsibility-chain tests

| ID | Scenario | Required result |
|---|---|---|
| A01 | Positive Plan inspect/finalize/verify | Inspect writes zero; finalize writes one canonical Plan; verify returns the exact model. |
| A02 | Positive Request -> Instruction -> Record | Final output contains three nested modules and three independent canonical digests. |
| A03 | A cross-command mutation changes rebuilt Request content or identity digest | Request anchor mismatch fails before Checker construction. |
| A04 | A cross-command mutation changes rebuilt Instruction content or identity digest | Instruction anchor mismatch fails before output creation. |
| A05 | Well-formed but wrong expected ID or SHA for any anchor | Failure; calculated values are never overwritten or repaired. |
| A06 | Builder call trace | Exact Request -> Request guard -> Instruction -> Instruction guard -> Record -> Decision/Record guards order. |
| A07 | Output inventory | Exactly one Plan or Record output; no module, draft, receipt, cache or pointer output. |
| A08 | Valid NEEDS_REVISION and REJECTED | Both finalize and historically verify with all authority fields false/zero. |
| A09 | One-byte mutation in each embedded module | Module ID/SHA or downstream chain fails; no partial acceptance. |
| A10 | Extract each module | Full closure first; exact canonical bytes; zero writes; damaged Record rejected. |
| A11 | A different internally valid closure follows Plan inspection | Old expected Plan ID/SHA fails before output open; test ID-only, SHA-only and pair mismatch. |
| A12 | Authoring inputs removed, replaced with open traps or made unreadable after finalization | Record verify still succeeds, traces exactly its 33 sources and never opens either input; its CLI rejects input/expected/time flags. |

### Path, byte and TOCTOU tests

| ID | Scenario | Required result |
|---|---|---|
| P01 | Missing, extra, duplicate or out-of-order source | Failure before pure builder invocation. |
| P02 | Relative, UNC, device, ADS or empty path | Rejected. |
| P03 | Symlink, junction, reparse, nested/bind mount | Rejected. |
| P04 | Hard link, directory, FIFO, case/resolved/physical alias | Rejected. |
| P05 | Glob, directory scan, newest/latest/current or environment default | No discovery path exists. |
| P06 | Input/output inside a Git tree or repository output/tmp | Rejected. |
| P07 | Output area overlaps a source or its parent is renamed/swapped around create | Precheck detection prevents open; a later race is detected before commit and triggers exact-handle rollback/quarantine. |
| P08 | Bound-1, bound, bound+1, short read and extra byte for every source class | Only values within the fixed exact policy pass. |
| P09 | BOM, invalid UTF-8, duplicate key, NaN/Inf, coercion, unknown field or non-canonical JSON | Rejected without repair. |
| P10 | Replace/relink/change link count, size, time, identity or digest during read | Failed closed. |
| P11 | Replace any input between full captures | No success; no output remains valid. |
| P12 | Replace a model after Manifest verification but before Plan build | Composite-snapshot seal detects drift. |
| P13 | Digest aliases identity, authoring input, source, policy, Plan or Record | Rejected except Instruction file SHA == Decision qualifier-record SHA. |

### Create-new and rollback tests

| ID | Scenario | Required result |
|---|---|---|
| W01 | Output already exists in any form | No overwrite, truncate or delete. |
| W02 | Another process creates output after absence check | Independent winner remains untouched. |
| W03 | Output name replaced while retained descriptor is open | No pathname trust; operation fails. |
| W04 | Failure at open/write/flush/reread/parse/post-capture/close | A provably live descriptor is invalidated first; close uncertainty follows W07 and any remnant is not accepted as an artifact. |
| W05 | `KeyboardInterrupt` or `SystemExit` after create | Same rollback rule applies before propagation/mapping. |
| W06 | Output name refers to a replacement during rollback | Replacement is never deleted; quarantine required. |
| W07 | Invalidate/delete/close/name inspection cannot be confirmed | Dedicated quarantine-required result. |
| W08 | Delete fails after exact object is invalidated | Remnant cannot pass Plan/Record parsing and is never repaired. |
| W09 | POSIX create under permissive umask or mode drift | Retained descriptor proves exact `0600`; otherwise rollback/fail closed. |
| W10 | Windows output ACL or handle inheritance broadens access | Rejected or rolled back before commit. |
| W11 | POSIX output name changes to a replacement inode during rollback | No pathname unlink; replacement survives; quarantine required. |
| W12 | Windows delete-pending close or parent-guard close fails | Quarantine-required exit `3`. |
| W13 | Windows peer attempts output rename, replacement or deletion while the retained handle is live, or races a parent rename/swap | Share mode `0` denies output delete-sharing; every parent/path drift is caught before commit and triggers exact-handle rollback or quarantine. |

### Identity, human input and policy tests

| ID | Scenario | Required result |
|---|---|---|
| I01 | Maker/Checker same path, hard link, bytes or digest | Rejected. |
| I02 | Identity aliases any closure/policy/Plan/human-input digest | Rejected. |
| I03 | Maker preflight receives Checker field or Checker changes Request | CLI/parser rejects or pure builder fails. |
| I04 | Missing, duplicate, reordered gate or inferred/default PASS | Rejected before Instruction build. |
| I05 | Approved gate with note or failed gate without note | Rejected by exact pure policy. |
| I06 | Six-gate/disposition combinations | Only the three existing policy combinations pass; issue codes are derived. |
| I07 | Documentation, diagnostics and test names | No claim of identity authentication, signature or proof of two humans. |
| I08 | Human input BOM, whitespace ambiguity, non-NFC or overlong text | Behavior exactly matches the accepted transport policy; never normalizes silently. |
| I09 | Authoring input has broad POSIX mode, wrong owner or non-owner-only Windows DACL | Rejected before human text is read. |

### Time and authority tests

| ID | Scenario | Required result |
|---|---|---|
| T01 | Clock/timezone/env changes, or mtime changes only between two separately stable invocations | Plan bytes and historical behavior unchanged; mtime drift within one capture still fails. |
| T02 | Fractional seconds, offsets, lowercase z or invalid date | Rejected. |
| T03 | `requested_at` before/equal/after Manifest time | Before fails; equality and after may pass. |
| T04 | Request at finite Evidence deadline | Equality fails; one second before may pass. |
| T05 | Checker before Request, at Request, one second before expiry and at expiry | Only the two in-window values pass. |
| T06 | Checker at finite Evidence deadline | Equality fails. |
| T07 | PERPETUAL and finite Review horizons | Exact +2592000 seconds or finite minimum; no calendar-month arithmetic. |
| T08 | Historical verification after all deadlines | Still historical, with no clock or currentness claim. |
| T09 | Mutate every false/zero authority field | Every mutation rejected. |
| T10 | PASS Record | Only separate Provider-proposal design eligibility may be true. |
| T11 | Human gates all pass but machine closure is damaged | Human choice cannot override machine failure. |
| T12 | Network, Key, Provider, Runtime, database, ledger or authorization hooks patched to fail | No hook is touched. |

### Compatibility and determinism tests

| ID | Scenario | Required result |
|---|---|---|
| C01 | Schema byte-lock suite | All existing 62 Schema files remain byte-identical. |
| C02 | Exact public API snapshot | Both ordered `__all__` values, function signatures, frozen operational dataclasses and exception subclass relationships match this runbook byte-for-byte; no extra public helper exists. |
| C03 | Repeated process builds from identical inputs | Plan, modules and Record canonical bytes are identical. |
| C04 | Unsupported platform safety primitive or malformed mount metadata | Fail closed rather than weaken admission. |
| C05 | Test filesystem/network monitor | Reads only explicit synthetic sources, their path components and fixed bounded platform safety metadata such as `/proc/self/mountinfo`; no private source, repo output/tmp or network. |
| C06 | Exact CLI parser snapshot | Only the seven reviewed commands and their exact options exist; duplicate singleton options, abbreviations and every force/repair/override/combined bypass are rejected. |
| C07 | Success and failure serialization for every command | Success stdout is exact sorted compact UTF-8 JSON plus LF, stderr is empty and exit is `0`; it contains the five common zero-authority members and only the documented command members. Ordinary and quarantine failures have the exact documented stderr bytes, empty stdout and exits `2` and `3`. |
| C08 | Malformed expected ID/SHA or malformed CLI value | Lexical validation fails before any private path or output parent is opened; lowercase SHA and type-specific stable-ID boundaries are exhaustively covered. |
| C09 | Artifact filename admission table | Exact case-insensitive `.json` suffix, ordinary-file/no-alternate-stream rule, Unicode `casefold()` tokenization and every accepted/rejected mutable/outcome token boundary match the normative rule. |

## Separate approvals for any later real operation

Merging an implementation would authorize no real-data operation. Each command requires a
new, exact and single-operation approval:

1. Plan inspection names the complete 29-source physical closure and approves only
   `inspect-use-plan-ready` once.
2. Plan finalization later repeats the closure, exact approved Plan anchor and one absent output.
3. Plan verification later repeats the closure and names the exact existing Plan.
4. Maker Request preflight names the Plan closure, Maker identity, accepted Maker input and explicit
   `requested_at`.
5. Checker Instruction preflight repeats the Maker inputs, names the Checker inputs, explicit
   `evaluated_at` and exact expected Request anchor, then reports Instruction, Decision and Record
   anchors.
6. Record finalization repeats all applicable inputs, exact expected Request, Instruction, Decision
   and Record anchors and one absent output.
7. Record historical verification repeats the closure, two identity references and exact existing
   Record.

No approval flows automatically to the next line. No real operation may select a Provider, read a
Key, use a network, upload, generate, execute, publish or create an entitlement, permit, ledger row
or task.

## Explicit prohibitions

The v2.7 implementation and every operator procedure must not:

- run against private data during development;
- infer a path, discover a sibling or accept an incomplete closure;
- persist Request, Instruction or Decision separately;
- use an output file as mutable workflow state;
- accept a caller-created Decision or authority override;
- trust an expected fingerprint before rebuilding from current bytes;
- treat identity inequality as natural-person authentication;
- expose basis text, gate notes, identity contents or private paths in summaries;
- read a wall clock during Plan or historical verification;
- imply fresh hold/revocation clearance from historical contracts;
- select or contact any Provider/model/account/region/operation;
- upload, POST, purchase, recharge, claim a trial, generate or publish;
- modify entitlement, authorization, Runtime, Worker, Provider, database, Temporal, Ark, ledger or
  migration behavior;
- invoke v1 rights, qualification or real-revision conversion; or
- treat a Manifest, Plan, PASS, proposed request count or cost ceiling as authority.

## Implementation and real-operation approval gate

This accepted runbook freezes one full physical closure, two bounded canonical authoring files, the
exact per-operation path table, comparison-only approval anchors, byte limits, CLI surface and
complete synthetic test matrix. Synthetic-only source and test implementation is approved. That
approval does not extend to commit, push, PR publication, merge, real authoring inputs, real output
artifacts or execution of any command against real data; each remains a separate explicit gate.
