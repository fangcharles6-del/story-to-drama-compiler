# Creative Sample Qualification Instruction Preparation v2.3

## Purpose and present-stage restriction

This runbook defines the trusted local authoring boundary for one Pack-level Human Review v2
Qualifier Instruction. It has exactly three commands:

```text
prepare-workspace
finalize-instruction
verify-instruction
```

This development PR is **synthetic-only**. Do not substitute the current real private Request,
Qualifier reference, workspace, draft, Instruction or any upstream Pack material into an example,
test or manual check. Do not read repository `output/` or `tmp/`. A real operation is a later stage
requiring a new explicit approval and individually named absolute paths.

This boundary prepares the existing v2.2
`CreativeSampleRealAssetQualificationDecisionInstructionV22`. It does not inspect Decision
readiness, invoke the Decision builder, perform qualification, create a Decision, create a rights
manifest or grant permission. Keep this state throughout all three commands:

```text
HUMAN_GATE
NOT_AUTHORIZED
rights_qualification_performed=false
rights_manifest_created=false
eligible_for_separate_manifest_design_review=false
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

## Trust split at a glance

```text
exact Request + exact Qualifier reference
                 |
                 v
     trusted Python prepare-workspace
                 |
                 v
 exact five-file static file:// workspace
                 |
                 v
 human enters four fields; browser downloads UNTRUSTED draft
                 |
                 v
 trusted Python finalize-instruction reopens and rebuilds everything
                 |
                 v
      canonical v2.2 Instruction, still zero authority
```

The browser is never trusted to calculate a stable ID, establish a digest, validate legal
sufficiency or create canonical Instruction bytes. Trusted Python never chooses the four human
fields.

## Exact command interface

The launcher is:

```text
python -m sdc.real_asset_qualification_instruction_preparer_v23 <subcommand> <options>
```

The exact CLI is:

```text
prepare-workspace
  --request <absolute-request.json>
  --qualifier-ref <absolute-qualifier-reference>
  --workspace <absolute-absent-workspace-directory>
  --observed-at <YYYY-MM-DDTHH:MM:SSZ>

finalize-instruction
  --request <absolute-request.json>
  --qualifier-ref <absolute-qualifier-reference>
  --workspace <absolute-existing-workspace-directory>
  --draft <absolute-untrusted-draft.json>
  --output <absolute-absent-instruction.json>
  --observed-at <YYYY-MM-DDTHH:MM:SSZ>

verify-instruction
  --request <absolute-request.json>
  --qualifier-ref <absolute-qualifier-reference>
  --workspace <absolute-existing-workspace-directory>
  --draft <absolute-untrusted-draft.json>
  --instruction <absolute-existing-instruction.json>
```

Every path is explicit. The program never scans for a Request, reference, workspace, draft or
Instruction; expands a glob; chooses a newest download; follows `latest`, `current` or `newest`;
or infers a sibling path. There are no conclusion-bearing CLI options and no environment, stdin,
config-file or interactive fallback.

The corresponding Python API is:

```text
prepare_workspace(request_path, qualifier_ref_path, workspace_root, *, observed_at)
finalize_instruction(
    request_path,
    qualifier_ref_path,
    workspace_root,
    draft_path,
    output_path,
    *,
    observed_at,
)
verify_instruction(
    request_path,
    qualifier_ref_path,
    workspace_root,
    draft_path,
    instruction_path,
)
```

## Inputs and outputs by command

| Command | Reads | Creates | Must not do |
|---|---|---|---|
| `prepare-workspace` | Exact Request and exact Qualifier reference. | One absent workspace with exactly five files. | Create a draft or Instruction; choose any human value. |
| `finalize-instruction` | Exact Request, Qualifier reference, workspace and explicitly selected draft. | One absent canonical v2.2 Instruction. | Trust browser bindings; invoke a Decision consumer. |
| `verify-instruction` | Exact Request, Qualifier reference, workspace, draft and existing Instruction. | Nothing. | Repair, rewrite, refresh or issue a receipt. |

The Qualifier reference is an already-complete private human/organizational reference record. This
tool does not create it, infer a person's identity or certify independence. Its whole-file bytes
are only read, bounded and hashed for mechanical binding.

## Workspace exact closure

`prepare-workspace` requires an absent workspace path and creates exactly:

```text
<workspace>/
  index.html
  app.js
  style.css
  instruction-context.json
  instruction-context.js
```

The audited static assets are packaged at:

```text
src/sdc/real_asset_qualification_instruction_preparer_v23_assets/
```

The workspace verifier performs one narrow, bounded enumeration of the explicitly supplied
workspace root only to require these five exact names and reject every missing, extra, linked or
non-regular member. It does not enumerate any parent directory. All five paths are derived only
from the fixed names above; the operator does not supply member paths.

Save the browser draft outside the workspace. A downloaded draft inside the workspace is a sixth
member and makes the workspace invalid. Do not rename the workspace to `latest`, create a pointer
to it or add notes, screenshots, receipts or backups inside it.

## Mechanical workspace context

`instruction-context.json` is strict canonical UTF-8 JSON with this fixed identity:

```text
schema_version=2.3.0
document_type=sdc.creative-sample-real-asset-qualification-instruction-workspace-context-v2.3
profile=creative-sample-real-asset-qualification-instruction-preparation-v2.3
```

It contains exactly the mechanical context needed by the page and trusted finalizer:

```text
schema_version
document_type
profile
context_id
request_id
request_sha256
requested_at
request_valid_until
prepared_at
policy_id
policy_version
policy_document_sha256
qualification_scope
qualifier_role
qualifier_ref_sha256
draft_document_type
status
rights_manifest_created
rights_qualification_performed
eligible_for_separate_manifest_design_review
current_gate
provider_state
eligible_for_real_generation
execution_authorized
posts_allowed
provider_requests
```

The fixed mechanical values include:

```text
qualification_scope=ASSET_INTAKE_ONLY
qualifier_role=INDEPENDENT_QUALIFIER
status=AWAITING_EXPLICIT_QUALIFIER_INPUT
HUMAN_GATE
NOT_AUTHORIZED
rights_qualification_performed=false
rights_manifest_created=false
eligible_for_separate_manifest_design_review=false
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

The `context_id` must match:

```text
real_asset_qualification_instruction_context_v23_[0-9a-f]{20}
```

It is calculated with:

```text
stable_id("real_asset_qualification_instruction_context_v23", every other context field)
```

`instruction-context.js` carries the same data and sets only:

```text
globalThis.SDC_QUALIFICATION_INSTRUCTION_CONTEXT
```

The value is read-only. Neither context file includes source paths, raw Qualifier-reference
contents, a human outcome, issue choice, basis, API key, Decision, manifest or execution
permission. Trusted Python compares both context representations with the exact Request and
Qualifier-reference bytes; JavaScript is not the authority for either representation.

## Static `file://` page boundary

Open only the exact workspace `index.html` as a local `file://` page. The page has a restrictive
Content Security Policy: network connections are denied, and script/style sources are limited to
the local workspace assets. The implementation must not use:

- `fetch`, XMLHttpRequest, WebSocket, EventSource or beacon;
- a worker or service worker;
- local storage, session storage, IndexedDB, cookies or a cache;
- browser, filesystem or network time;
- file import, drag-and-drop import, clipboard inference or upload; or
- any external font, image, script, stylesheet or analytics endpoint.

The page only displays the mechanical Request/Qualifier binding, collects four explicit human
fields and creates one local browser download. Browser validation is usability feedback only. It
cannot make a draft trusted, canonical or qualified.

## Exactly four human fields

The human Qualifier must explicitly supply:

| Field | Required rule |
|---|---|
| `decision_at` | Canonical human-recorded UTC second, `YYYY-MM-DDTHH:MM:SSZ`. |
| `decision` | Exactly one closed outcome; no preselection. |
| `qualification_issue_codes` | Explicit canonical array, including an explicitly supplied empty array for PASS. |
| `qualification_basis` | Actual human basis, 1..1000 characters, trimmed NFC and control-free. |

There is no default, suggestion, recommended decision, inferred issue, generated basis, “use
current time” control or automatic timezone conversion. The page begins without a selected
outcome or time and must not export until all four fields have been explicitly handled. Placeholder
text is an instruction, never a value.

The closed rules are:

| `decision` | Required issue array |
|---|---|
| `PASS_ASSET_INTAKE_ONLY` | Explicit `[]` only. |
| `REJECTED` | Non-empty and contains `QUALIFIER_REJECTED_ASSET_INTAKE`. |
| `NEEDS_HUMAN_REVIEW` | Non-empty and excludes `QUALIFIER_REJECTED_ASSET_INTAKE`. |

Issue codes are unique and may appear only in this canonical order:

```text
EVIDENCE_SCOPE_UNCLEAR
POLICY_REQUIREMENT_NOT_MET
QUALIFIER_REJECTED_ASSET_INTAKE
OTHER_BLOCKING_ISSUE
```

The page does not authenticate the operator or judge whether the basis is true or legally
sufficient. A human process outside the software establishes identity, independence and the
substantive conclusion.

## Untrusted draft exact shape

The neutral browser download name is:

```text
qualification-instruction-draft-v23.json
```

The draft is strict UTF-8 JSON with exactly thirteen required fields and no defaults or extras:

```text
schema_version
document_type
profile
status
context_id
context_sha256
request_id
request_sha256
qualifier_ref_sha256
decision_at
decision
qualification_issue_codes
qualification_basis
```

Its fixed identity is:

```text
schema_version=2.3.0
document_type=sdc.creative-sample-real-asset-qualification-decision-instruction-draft-v2.3
profile=creative-sample-real-asset-qualification-instruction-preparation-v2.3
status=UNTRUSTED_DRAFT
```

`context_sha256` is the SHA-256 of the exact canonical `instruction-context.json` bytes. The
browser copies mechanical binding values for later comparison; it does not establish them.

The draft intentionally omits:

- `instruction_id` and `qualifier_record_sha256`;
- policy and fixed Instruction permission fields;
- any claim that qualification was performed;
- Decision or manifest identifiers; and
- paths, raw reference contents or credentials.

Changing `UNTRUSTED_DRAFT`, renaming the file, or copying its fields into another JSON object does
not make it an Instruction. `finalize-instruction` treats every draft byte as hostile input.

## Trusted mechanical finalization

Before constructing an Instruction, trusted Python independently:

1. strictly reparses the exact canonical Request and verifies its stable ID, policy and
   zero-authority state;
2. reopens and hashes the exact Qualifier-reference bytes;
3. admits and reconstructs the exact five workspace paths;
4. strictly parses the canonical context and verifies its content-derived ID;
5. proves that the JavaScript context and JSON context carry the same mechanical values;
6. hashes the exact context JSON bytes;
7. strictly parses the explicitly selected thirteen-field draft;
8. compares every draft mechanical binding with independently reconstructed values;
9. validates all four human fields and their cross-field rules; and
10. repeats the complete stable input capture before create-new publication.

It then constructs the existing v2.2 Instruction mechanically. The output binds:

- exact Request ID and canonical Request-file SHA-256;
- exact fixed SDC-ADR-021 policy triple;
- `qualification_scope=ASSET_INTAKE_ONLY`;
- `qualifier_role=INDEPENDENT_QUALIFIER`;
- exact Qualifier-reference whole-file SHA-256;
- the four explicit human draft fields;
- content-derived v2.2 `instruction_id`; and
- the complete v2.2 zero-authority state.

The complete Instruction-file SHA-256 is deliberately not a field inside the Instruction. A later
v2.2 Decision finalizer, under a separate approval, hashes the admitted canonical file as the
retained `qualifier_record_sha256`.

## Time gates and no clocks

`prepare-workspace` and `finalize-instruction` each require a separately supplied canonical
`--observed-at`. The program never supplies “now”, reads a wall clock, uses local timezone,
accepts fractional seconds or derives time from a filesystem or browser.

Workspace preparation stores its explicit observation as `prepared_at` and requires:

```text
request.requested_at <= prepared_at < request.request_valid_until
```

Instruction finalization requires:

```text
request.requested_at <= prepared_at <= decision_at <= observed_at
observed_at < request.request_valid_until
```

All equality and exclusivity signs are normative. The Request's original expiry cannot be
extended, renewed, rounded or replaced. If the Request expires, stop and obtain a separately
approved new Request through the v2.1 create-new workflow; do not repair it in v2.3.

`verify-instruction` has no `--observed-at` and reads no clock. Historical verification requires:

```text
request.requested_at <= prepared_at <= decision_at < request.request_valid_until
```

Later wall-clock expiry does not invalidate an Instruction that was correctly prepared inside the
original window, and historical verification does not make that Request current for a new action.

## Path admission and trust areas

Every supplied path must be a fully qualified, ordinary repository-external local path. Reject:

- relative, empty, UNC/network, device or extended-device paths;
- alternate data streams;
- symbolic links, junctions, mounts and reparse points;
- hard-linked and non-regular files;
- lexical, resolved, case-folded, physical or digest aliases;
- paths in any Git tree, including repository `output/` and `tmp/`; and
- mutable alias components such as `latest`, `current` or `newest`.

Request and Qualifier reference must be distinct by path, opened-file identity and whole-file
digest. Workspace members, draft and Instruction must not alias either source or one another.
Names for the draft and Instruction must be opaque and must not disclose `pass`, `rejected` or
`needs` in the basename.

For `prepare-workspace`, the absent workspace and its direct parent must use a trust area that does
not intersect the direct parent of the Request or Qualifier reference. The command creates the
workspace itself; it does not create a broad private root or silently reorganize source files.

For `finalize-instruction`, the Instruction output parent must already exist and be neither equal
to, an ancestor of nor a descendant of:

- the Request parent;
- the Qualifier-reference parent;
- the exact workspace root; or
- the draft parent.

The existing Instruction supplied to `verify-instruction` must obey the same independent
trust-area rule. If a source is stored directly in an aggregate private root, an output directory
below that root is a descendant and is rejected. Select an independently approved sibling trust
area instead.

## Bounded reads and TOCTOU

The implementation uses fixed, non-configurable byte limits for Request JSON, Qualifier reference,
each workspace member, draft and Instruction. No CLI flag, environment variable or config file can
raise them.

For every source, trusted Python:

1. validates the lexical and resolved absolute path;
2. records the non-linked file or directory identity;
3. opens the exact ordinary file and confirms handle identity;
4. reads no more than the fixed bound and detects extra bytes;
5. calculates SHA-256 over bytes actually read;
6. checks path, handle, size, link count and modification identity after the read; and
7. repeats the complete closure before success or publication.

Any replacement, relink, hard-link-count change, short/extra read, size/time/identity drift,
digest mismatch or parent-identity change is a hard stop. The command never retries by selecting a
different file.

## Create-new and rollback boundary

Workspace and Instruction publication are create-new only:

- the target must not exist;
- no overwrite, append, repair, merge or in-place normalization is allowed;
- no temp-as-latest, sidecar, pointer, receipt, cache or log is created; and
- exact created descriptors and guarded parent identities are retained through write, flush,
  reread, strict verification and final source-drift checking.

Normal failures remove the exact newly created target. If deletion is unavailable, cleanup first
invalidates the exact created file through its retained descriptor so any remnant is unparseable.
Windows uses exact-handle deletion without a pathname fallback. POSIX uses a guarded directory
descriptor and matching inode and never deletes a replacement.

If neither invalidation nor safe deletion can be confirmed, the fixed status is:

```text
ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED
```

Immediately isolate the affected workspace or Instruction trust area. Do not open, verify, reuse,
repair or overwrite anything in it until a separate human audit resolves the incident. Ordinary
failures emit a fixed zero-authority summary whose status is `FAILED_CLOSED`.

## `prepare-workspace`

Preparation is a trusted Python operation, not a UI action. It verifies the exact Request,
Qualifier reference, paths, byte separation and explicit time before any output. It then creates
only the exact five-file workspace.

Success reports a bounded zero-authority summary with:

```text
status=AWAITING_EXPLICIT_QUALIFIER_INPUT
rights_qualification_performed=false
```

It must not create a draft, fill a human field, construct a v2.2 Instruction, call a Decision
builder or claim readiness for Decision finalization.

## `finalize-instruction`

Finalization requires a new invocation with the exact workspace, exact downloaded draft, one
absent output and a new explicit observed time. It does not reuse a prior Python object or browser
state. Only after the complete closure is stable may it create one canonical v2.2 Instruction.

Success reports:

```text
status=DECISION_INSTRUCTION_RECORDED
rights_qualification_performed=false
```

The success summary does not print the Instruction ID, outcome, basis, issues, private paths, full
digests or draft body. It must not automatically call `inspect-decision-ready`.

## `verify-instruction`

Verification is historical and read-only. It reopens the Request, Qualifier reference, all five
workspace members, exact draft and exact existing Instruction; reconstructs the canonical v2.2
Instruction; and requires byte-for-byte equivalence.

It creates no receipt, normalization, repaired copy or refreshed workspace. Success reports
`DECISION_INSTRUCTION_RECORDED` and the zero-authority state. Failure never changes any source.

## Stop conditions

Stop without a trusted Instruction on any:

- missing, extra, malformed, oversized, linked, aliased or changed source;
- relative, network/device, Git-contained or mutable-alias path;
- intersecting workspace, draft, source or Instruction trust area;
- existing create-new target;
- workspace member other than the exact five fixed names;
- asset byte, context JSON/JavaScript, context ID or context digest mismatch;
- Request ID, policy, canonical bytes, expiry or zero-authority mismatch;
- Qualifier-reference path, identity or digest mismatch;
- unknown, duplicate, missing or defaulted draft field;
- missing or inferred human time, decision, issue selection or basis;
- invalid outcome/issue combination, duplicate issue or non-canonical order;
- `prepared_at` or `decision_at` outside the original Request window;
- finalization observation before the decision or at/after Request expiry;
- any TOCTOU, parent-identity or rollback uncertainty;
- any attempt to use a browser draft as an Instruction;
- any request to continue automatically into Decision inspection/finalization; or
- any nonzero execution, publication, Provider, manifest or qualification state.

There is no override, waiver, best-effort, repair or force option.

## Prohibited operations

This v2.3 boundary must not:

- run against real private data during this synthetic development PR;
- infer, recommend, translate or auto-fill a human conclusion;
- read a real Pack, fourteen media files, Evidence, Reviews, PairCheck or Decision;
- invoke `inspect-decision-ready`, `finalize-decision`, `verify-decision` or a Decision builder;
- perform rights qualification or create a Decision or rights manifest;
- call a v1 rights path or synthesize 28 v1 reviewer records;
- modify entitlement or authorization state;
- touch Runtime, Worker, Provider, PostgreSQL, Temporal, Ark, Atomic Ledger or migration code;
- read an API key or another credential;
- use a network, upload, POST, purchase, recharge or claim a trial;
- start a service; or
- read or write repository `output/` or `tmp/`.

Private references, workspaces, drafts and Instructions remain outside Git and must never be
staged, committed, pushed or uploaded.

## Synthetic offline verification

The implementation PR must use only synthetic temporary fixtures and non-integration checks. Test
at least:

- exact Python and CLI surface with only the three named commands;
- absence of CLI/env/stdin/default values for the four human fields;
- exact five-file workspace and rejection of every missing or extra member;
- byte identity of packaged assets and exact context JSON/JavaScript equivalence;
- restrictive CSP and absence of browser network, storage, clock, import and service-worker APIs;
- no preselected decision/time and explicit empty-issue handling for PASS;
- exact thirteen-field `UNTRUSTED_DRAFT` shape and rejection of unknown, duplicate or missing
  fields;
- strict UTF-8/canonical JSON, request binding, context ID/SHA and Qualifier-reference SHA checks;
- tampered mechanical draft fields never being trusted;
- all three outcome/issue combinations and human-basis validation;
- explicit `prepared_at` and finalization `observed_at`, with no wall clock;
- all inclusive/exclusive time boundaries and historical verification after expiry;
- absolute repository-external path, link/reparse/hard-link/UNC/device/ADS/alias rejection;
- non-intersecting workspace and Instruction trust areas;
- bounded reads plus pre-read, opened-handle, post-read and pre-publication drift;
- workspace and Instruction create-new refusal, exact-handle rollback and replacement safety;
- fixed Quarantine status when invalidation and deletion are both unconfirmed;
- redacted success/failure output with no outcome, basis, issue, path or full digest;
- zero-authority state for preparation, finalization and verification;
- no Decision, manifest, qualification, production, network or registry dependency;
- normalized-LF byte locks for all 56 existing Schemas; and
- zero additions or changes to contracts, committed Schemas and production safety boundaries.

Run the complete non-integration repository check and perform a P0/P1/P2 audit before opening the
independent Draft PR. Do not start services or contact paid or remote systems.

## Compatibility and later real stages

V2.3 adds implementation, static assets, documentation and synthetic offline tests only. It does
not add a Schema. All 56 existing Schemas, all existing contracts, the v2.1 Request preparer, the
v2.2 Decision finalizer API and production safety boundaries remain byte-compatible.

After merge, a user may explicitly approve preparing one real workspace from one exact Request
and Qualifier reference. A later, separate approval may authorize finalizing one exact downloaded
draft to one absent Instruction path. Verification also requires an explicitly selected real
closure. None of these approvals authorizes `inspect-decision-ready`.

A further separate approval must provide the complete v2.2 27-path Decision-inspection closure
and `observed_at`. Decision finalization is separate again. No success in this runbook creates a
rights manifest, entitlement, authorization, publication permission or Provider permission.
