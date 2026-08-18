# SDC-ADR-024: Trusted local Qualifier-instruction preparation v2.3

- **Status:** Proposed
- **Date:** 2026-08-18
- **Version:** V01

## Context

SDC-ADR-021 defined the immutable Pack-level Human Review v2 Qualification Request and Decision
contracts. SDC-ADR-022 added trusted local Request preparation, and SDC-ADR-023 added trusted local
Decision inspection, finalization and historical verification. The v2.2 Decision finalizer
deliberately accepts the Qualifier's conclusion only through one already-complete canonical
`CreativeSampleRealAssetQualificationDecisionInstructionV22` file. It provides no authoring
command and must never infer a conclusion.

Manually calculating the Request bindings, Qualifier-reference digest, content-derived
`instruction_id` and canonical JSON bytes is error-prone. Putting the human outcome or basis on a
command line is worse: process listings and shell history can disclose it, and a CLI default can
silently become a false human conclusion. A browser form can improve the local authoring
experience, but browser output is not a trusted contract and must not become a new authority
boundary.

The required bridge is therefore a local, two-boundary preparation workflow:

1. trusted Python prepares a finite, repository-external static workspace from one exact Request
   and one exact Qualifier-reference file;
2. a human Qualifier enters exactly four conclusion fields in a static `file://` page and exports
   an explicitly untrusted draft; and
3. trusted Python reopens every source, distrusts and strictly checks the draft, mechanically
   constructs the existing v2.2 Instruction, and writes it through create-new semantics.

This bridge prepares an instruction only. It does not inspect Decision readiness, invoke the
Decision builder, perform qualification, create a Decision or create a rights manifest.

## Decision

Add one trusted local Qualifier-instruction preparer with exactly three operator-facing commands:

- `prepare-workspace` verifies the exact Request and Qualifier reference and creates one new,
  fixed five-file static workspace;
- `finalize-instruction` consumes that exact workspace and one explicitly selected untrusted
  draft, then creates one new canonical v2.2 Instruction; and
- `verify-instruction` historically reopens the same sources, workspace, draft and existing
  Instruction and requires exact deterministic equivalence, with zero writes.

The Python module is:

```text
sdc.real_asset_qualification_instruction_preparer_v23
```

Its public Python API is:

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

The three commands and their separation are normative. There is no automatic continuation from
workspace preparation to finalization, no interactive Python prompt, no fourth command, no
`--force`, overwrite, repair, waiver, Decision or manifest mode.

This development PR is **synthetic-only**. Tests and examples use only synthetic temporary
fixtures. They must not read the current real private Request, Qualifier reference, workspace,
draft, Instruction, Pack, Evidence, Reviews, PairCheck or Decision. A later real invocation
requires a new explicit approval naming each exact absolute path. Approval to prepare a workspace
does not approve instruction finalization, and neither approval authorizes v2.2 Decision
inspection or finalization.

## Existing contract, no new authority contract

V2.3 reuses the existing
`CreativeSampleRealAssetQualificationDecisionInstructionV22` contract and its committed Schema
unchanged. It introduces no new Pydantic production contract and no new committed Schema. The
workspace context and untrusted browser draft are private operational envelopes with strict
v2.3 shapes; neither is registered in `sdc.schemas.MODELS`, neither is an Instruction, and neither
is evidence that qualification occurred.

The canonical output of `finalize-instruction` is still the exact v2.2 Instruction specified by
SDC-ADR-023. Its complete file SHA-256 is not stored inside itself. A later, separately approved
v2.2 Decision finalizer derives `qualifier_record_sha256` from those complete canonical bytes.

All 56 Schemas that predate v2.3 remain byte-identical. The compatibility baseline must include a
fixed normalized-LF byte lock for all 56, including
`CreativeSampleRealAssetQualificationDecisionInstructionV22.schema.json`, in addition to the
existing model-versus-committed-schema drift check. No v2.3 implementation change may regenerate
or edit a Schema.

## Exact command interface

The CLI surface is:

```text
python -m sdc.real_asset_qualification_instruction_preparer_v23 prepare-workspace \
  --request <absolute-request.json> \
  --qualifier-ref <absolute-qualifier-reference> \
  --workspace <absolute-absent-workspace-directory> \
  --observed-at <YYYY-MM-DDTHH:MM:SSZ>

python -m sdc.real_asset_qualification_instruction_preparer_v23 finalize-instruction \
  --request <absolute-request.json> \
  --qualifier-ref <absolute-qualifier-reference> \
  --workspace <absolute-existing-workspace-directory> \
  --draft <absolute-untrusted-draft.json> \
  --output <absolute-absent-instruction.json> \
  --observed-at <YYYY-MM-DDTHH:MM:SSZ>

python -m sdc.real_asset_qualification_instruction_preparer_v23 verify-instruction \
  --request <absolute-request.json> \
  --qualifier-ref <absolute-qualifier-reference> \
  --workspace <absolute-existing-workspace-directory> \
  --draft <absolute-untrusted-draft.json> \
  --instruction <absolute-existing-instruction.json>
```

There are deliberately no CLI arguments for `decision_at`, `decision`,
`qualification_issue_codes`, `qualification_basis`, `instruction_id`, Request digests or
Qualifier-reference digests. The program does not accept those values through environment
variables, stdin, a config file, an operator prompt or a wall clock.

## Trusted Python and untrusted `file://` boundary

`prepare-workspace` creates exactly this five-file tree and no other member:

```text
<workspace>/
  index.html
  app.js
  style.css
  instruction-context.json
  instruction-context.js
```

The three static assets are audited package resources. `instruction-context.json` is a bounded,
strict, canonical mechanical context generated from the exact Request, the exact
Qualifier-reference bytes and the explicit preparation observation time. Its fixed identity is:

```text
schema_version=2.3.0
document_type=sdc.creative-sample-real-asset-qualification-instruction-workspace-context-v2.3
profile=creative-sample-real-asset-qualification-instruction-preparation-v2.3
```

Its `context_id` is `stable_id("real_asset_qualification_instruction_context_v23", payload)` over
every other context field. The JavaScript context contains the same mechanical data and exposes
it only as the read-only
`globalThis.SDC_QUALIFICATION_INSTRUCTION_CONTEXT`. It contains no file path, raw
Qualifier-reference content, human conclusion, basis, API key or execution permission.

The workspace is an exact closure. The only allowed enumeration is a bounded enumeration of the
explicitly selected workspace root for the sole purpose of proving that the five fixed names are
present and no extra member exists. The program never scans a parent directory, discovers a
workspace, chooses a newest draft or follows a mutable alias. All workspace paths are reconstructed
only from the supplied root and the five fixed names.

The page is opened directly with `file://`. It is presentation and collection code, not a trusted
validator. Its Content Security Policy denies all network connections and admits only its own
local script and style. It must not use `fetch`, XHR, WebSocket, EventSource, beacon, workers,
service workers, local or session storage, IndexedDB, cookies, environment values or a clock. It
must not import a file or upload content. It may only display the read-only mechanical context,
collect the four human fields and trigger a local browser download of an untrusted JSON draft.

The browser draft is never parsed as a v2.2 Instruction and must not contain an `instruction_id`,
`qualifier_record_sha256`, completed-qualification flag, Decision, manifest or authorization
claim. Its fixed identity is:

```text
schema_version=2.3.0
document_type=sdc.creative-sample-real-asset-qualification-decision-instruction-draft-v2.3
profile=creative-sample-real-asset-qualification-instruction-preparation-v2.3
status=UNTRUSTED_DRAFT
```

The neutral local download name is `qualification-instruction-draft-v23.json`. These constants
identify it as untrusted authoring input; they do not promote it to an Instruction.

## Four explicit human inputs

The page collects exactly four non-mechanical fields:

1. `decision_at`;
2. `decision`;
3. `qualification_issue_codes`; and
4. `qualification_basis`.

All four are required in the draft. There is no default, inferred value, recommendation,
placeholder conclusion, current-time button, local-time conversion or preselected outcome. The
page must initially leave the decision and time unselected, must require explicit issue-code
handling even when the human chooses an empty list, and must refuse draft export until the basis
is actually entered. Browser convenience validation does not replace trusted Python validation.

`decision_at` is human-entered canonical UTC to whole seconds:

```text
YYYY-MM-DDTHH:MM:SSZ
```

The outcome rules are closed and unchanged from SDC-ADR-021 and SDC-ADR-023:

- `PASS_ASSET_INTAKE_ONLY` requires an explicitly supplied empty issue-code tuple;
- `REJECTED` requires a non-empty tuple containing
  `QUALIFIER_REJECTED_ASSET_INTAKE`;
- `NEEDS_HUMAN_REVIEW` requires a non-empty tuple that excludes that rejection code; and
- every outcome requires a 1..1000-character, trimmed, NFC, control-free human basis.

The permitted issue codes, in canonical order, are:

```text
EVIDENCE_SCOPE_UNCLEAR
POLICY_REQUIREMENT_NOT_MET
QUALIFIER_REJECTED_ASSET_INTAKE
OTHER_BLOCKING_ISSUE
```

The program does not authenticate a person, establish independence or assess legal sufficiency.
Those are human controls. It only proves that the exact selected Qualifier-reference bytes and
the explicit human draft are mechanically bound to the exact selected Request.

## Mechanical bindings and distrust of the draft

The untrusted draft contains exactly thirteen fields: its four fixed v2.3 identity/status fields,
the exact `context_id` and `context_sha256`, the `request_id` and canonical `request_sha256`, the
whole-file `qualifier_ref_sha256`, and the four required human fields. Unknown, duplicate,
missing or defaulted fields are hard failures.

`finalize-instruction` never trusts a draft binding merely because the browser emitted it. Trusted
Python reopens and strictly reparses the Request, reopens and hashes the Qualifier reference,
reconstructs and verifies all five workspace members, recomputes the context ID and digest, and
requires every mechanical draft field to match. It independently enforces the human-field
contract and constructs the v2.2 Instruction using:

- the exact Request ID and canonical Request-file SHA-256;
- the Request's fixed SDC-ADR-021 policy ID, version and policy-document SHA-256;
- `qualifier_role=INDEPENDENT_QUALIFIER`;
- the exact Qualifier-reference whole-file SHA-256;
- the four explicit human fields;
- `qualification_scope=ASSET_INTAKE_ONLY`;
- a content-derived `instruction_id`; and
- the complete fixed zero-authority v2.2 Instruction state.

No browser-supplied stable ID, digest, policy value, permission value or canonical output byte is
accepted in place of this reconstruction.

## Explicit time semantics

`prepare-workspace` requires one caller-supplied `--observed-at`, stored mechanically as the
workspace context's `prepared_at`. `finalize-instruction` requires a second caller-supplied
`--observed-at`. Both use canonical UTC seconds. Neither command reads a wall clock, filesystem
timestamp, timezone, environment default or browser time.

Preparation requires:

```text
request.requested_at <= prepared_at < request.request_valid_until
```

Finalization requires:

```text
request.requested_at <= prepared_at <= draft.decision_at <= observed_at
observed_at < request.request_valid_until
```

The Request's exclusive expiry, its 24-hour maximum age and any earlier Evidence-derived deadline
remain immutable. The preparer cannot extend, round, renew or repair them.

`verify-instruction` deliberately accepts no observed time and reads no clock. It historically
requires:

```text
request.requested_at <= prepared_at <= draft.decision_at < request.request_valid_until
```

An Instruction correctly prepared within its original window remains historically verifiable
after that window has elapsed. Verification does not make an expired Request current again.

## Path, trust-area and alias boundary

Every supplied path must be an absolute, ordinary local path outside every Git tree. The boundary
rejects relative and empty paths, UNC/network and device paths, extended-device forms, alternate
data streams, symbolic links, junctions, mount/reparse points, hard-linked or non-regular files,
case-folded or physical aliases, and any component using `latest`, `current` or `newest` as a
mutable alias token.

The Request and Qualifier reference must be distinct by lexical path, resolved path, opened-file
identity and whole-file SHA-256. The draft must be distinct from both sources and every workspace
member. An existing Instruction selected for verification must also be distinct. Matching bytes
under a different name do not establish independence.

The direct parent of the new workspace must not intersect the Request or Qualifier-reference
source trust areas. For instruction finalization, the output parent must already exist and be
neither equal to, an ancestor of nor a descendant of the Request parent, Qualifier-reference
parent, workspace root or draft parent. The target Instruction path must not overlap any source.
An existing Instruction admitted for verification must use the same independent trust-area rule.

The workspace path and new Instruction output must be absent. There is no overwrite, merge,
repair, append, in-place normalization, backup-as-authority, automatic retry or mutable alias.
Outcome-bearing draft and Instruction basenames must be neutral and must not disclose `pass`,
`rejected` or `needs` in a process list or shell history.

## Bounded reads, TOCTOU and create-new publication

Every private read is bounded by a fixed implementation limit. Trusted Python admits each path,
opens the exact non-linked file, compares lexical, resolved, path and opened-handle identities,
reads only within its bound, hashes the bytes read, and rechecks identity after reading. The
Request, Qualifier reference, five workspace members, draft and existing Instruction are captured
again before success. Any replacement, relink, hard-link-count change, short or extra read,
size/time/identity drift or digest mismatch fails closed.

Workspace and Instruction publication use create-new semantics. The writer retains exact opened
descriptors through write, flush, reread, strict parse and final source-drift verification. A
normal failure removes the exact new target. If deletion is unavailable, the exact created file is
first truncated or poisoned through its retained descriptor so it cannot be parsed as a valid
artifact. Windows cleanup uses the exact OS handle and never a pathname fallback; POSIX cleanup
uses the guarded parent descriptor and matching inode so a replacement is never deleted.

If neither exact-artifact invalidation nor identity-safe deletion can be confirmed, the operation
reports the fixed zero-authority status:

```text
ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED
```

The entire affected output trust area must then be isolated. Nothing in it may be verified,
reused, repaired or overwritten until a separate human audit resolves the incident. Ordinary
failures report a bounded, non-secret zero-authority summary whose status is `FAILED_CLOSED`.

## Command semantics

`prepare-workspace` verifies the Request, Qualifier reference, paths, time and byte separation,
then creates the exact five-file workspace. Its bounded zero-authority success summary has:

```text
status=AWAITING_EXPLICIT_QUALIFIER_INPUT
```

It does not create a draft, choose a decision, generate an Instruction or perform qualification.

`finalize-instruction` reopens every source and the exact untrusted draft. Only after two complete
stable captures and all human-field, binding and time checks pass may it mechanically construct
and exclusively create the canonical v2.2 Instruction. Its bounded zero-authority success summary
has:

```text
status=DECISION_INSTRUCTION_RECORDED
```

It does not call `build_real_asset_qualification_decision_v2` directly or indirectly.

`verify-instruction` writes nothing. It reopens the complete workspace and draft closure,
historically reconstructs the v2.2 Instruction and requires exact canonical byte equivalence.
Success also reports `DECISION_INSTRUCTION_RECORDED`; it does not refresh, repair or reissue the
Instruction.

No success or failure summary prints the human outcome, basis, issue codes, private paths, raw
reference contents or full SHA-256 values.

## Zero-authority invariant

Workspace preparation, draft export, Instruction finalization and Instruction verification all
remain:

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

An Instruction records an explicit human input for a possible later consumer. It is not a
completed qualification and does not mean that any outcome has been accepted by SDC. This
boundary must not invoke `inspect-decision-ready`, `finalize-decision`, `verify-decision`,
`build_real_asset_qualification_decision_v2`, a v1 rights path or a rights-manifest builder.

It must not read a real Pack or its fourteen media, Evidence, Reviews or PairCheck; synthesize 28
v1 review records; modify entitlement or authorization; touch Runtime, Worker, Provider,
PostgreSQL, Temporal, Ark, Atomic Ledger or migration code; read a Key; or use a network, upload,
POST, purchase, recharge, trial or service start. It must never read or write repository
`output/` or `tmp/`, and private workspaces, drafts, references and Instructions must never be
staged, committed, pushed or uploaded.

## Consequences and later stages

The human Qualifier gets a local, non-technical authoring surface without making JavaScript or a
downloaded draft authoritative. Mechanical bindings and canonical bytes remain the responsibility
of trusted Python, while the four judgment fields remain explicitly human and have no defaults.
The cost is an additional create-new workspace, an explicit browser export and strict
trust-area/path ceremony.

After this PR is merged, real use still requires separate approvals. One approval may authorize
preparing a workspace from one exact Request and Qualifier reference. A later approval may name
the exact workspace, draft and absent Instruction output for finalization. Creating or verifying
an Instruction does not authorize v2.2 Decision inspection. Decision inspection, Decision
finalization and any later manifest-design review each remain separately approved stages.
