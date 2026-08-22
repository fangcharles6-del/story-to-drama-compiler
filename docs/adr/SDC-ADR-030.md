# SDC-ADR-030: Trusted-local Use Scope Review authoring input preparation v2.9

- **Status:** Accepted
- **Date:** 2026-08-22
- **ADR release:** 1.0
- **Operational boundary version:** 2.9.0
- **Bound finalizer module:** `sdc.real_asset_use_scope_review_finalizer_v27`
- **Bound finalizer version:** v2.7
- **Consumed contract Schema version:** none

## Context

SDC-ADR-028 introduced a trusted-local v2.7 boundary for forming one immutable Maker Request,
one immutable Checker Instruction, one compiler-derived Decision and one complete outer Review
Record. The finalizer deliberately accepts the Maker and Checker human choices through two
separately selected, repository-external authoring input files. Those files are hostile transport
inputs, not Request or Instruction artifacts, but v2.7 still requires their exact current bytes to
use strict canonical UTF-8 JSON and their opened descriptors to satisfy an owner-only permission
predicate before any human text is read.

That boundary is correct. It prevents process-list and shell-history disclosure of human prose,
keeps the Maker and Checker physically separate, and prevents a convenient local text file from
becoming an authority object. It also exposes a practical Windows failure mode for a small team:
an editor may emit CRLF, a BOM, unsorted keys, a missing final LF or an inherited DACL broader than
the exact protected owner-only form required by v2.7. Manually repairing those details is
error-prone and can accidentally overwrite the only reviewed input.

SDC-ADR-029 reduced a different source of operator error by rendering fixed, parameter-labelled
path checklists. It deliberately forbids checklist-to-finalizer execution, receipt caches and
automatic orchestration. A path checklist cannot solve authoring byte or permission preparation,
and v2.9 must not weaken that separation.

This ADR therefore defines a narrow inspect-then-create boundary. It converts one explicitly
selected, non-authoritative Maker or Checker draft into the exact canonical authoring input bytes
accepted by v2.7. Inspection writes nothing and reports three comparison-only approval anchors.
Finalization repeats every read and calculation, requires all three exact anchors, and creates one
new owner-only authoring input. It never invokes v2.7 or approves a later preflight.

Acceptance of this ADR authorizes synthetic-only source and test implementation on a separately
approved v2.9 branch. It does not authorize reading a real draft, creating a real authoring input,
commit, push, PR publication, merge, deployment, a v2.7 operation or any Provider action.

## Decision

Add one independent operational module:

```text
sdc.real_asset_use_scope_review_authoring_preparer_v29
```

Its exact CLI operations are four role-specific commands:

```text
inspect-maker-authoring
inspect-checker-authoring
finalize-maker-authoring
finalize-checker-authoring
```

There is no generic command with `--role`. Role is fixed by the selected parser and Python
function before a private path is opened. A Maker draft cannot be accepted by a Checker command,
and a Checker draft cannot be accepted by a Maker command.

The exact CLI shape is:

```text
inspect-maker-authoring
  --draft <absolute-existing-maker-draft.json>
  --output-parent <absolute-existing-output-parent>

inspect-checker-authoring
  --draft <absolute-existing-checker-draft.json>
  --output-parent <absolute-existing-output-parent>

finalize-maker-authoring
  --draft <absolute-existing-maker-draft.json>
  --output <absolute-absent-maker-authoring-input.json>
  --expected-draft-sha256 <separately-approved-lowercase-sha256>
  --expected-authoring-sha256 <separately-approved-lowercase-sha256>
  --expected-output-parent-seal-sha256 <separately-approved-lowercase-sha256>

finalize-checker-authoring
  --draft <absolute-existing-checker-draft.json>
  --output <absolute-absent-checker-authoring-input.json>
  --expected-draft-sha256 <separately-approved-lowercase-sha256>
  --expected-authoring-sha256 <separately-approved-lowercase-sha256>
  --expected-output-parent-seal-sha256 <separately-approved-lowercase-sha256>
```

Only the two `finalize-*` operations may write. An `inspect-*` operation cannot create a draft,
directory, authoring input, cache, receipt or other file. A successful inspection stops so a human
can separately review the draft content, intended role, exact output trust area and the three
reported anchors. It cannot automatically call finalization.

## Version and compatibility binding

V2.9 is hard-bound to:

```text
target_finalizer_module=sdc.real_asset_use_scope_review_finalizer_v27
target_finalizer_version=v2.7
review_policy_version=2.6.0
```

The binding is compiled into the role descriptors and repeated in the draft envelope and bounded
success summary. It is not selected dynamically and is not an import target supplied by a caller.
The implementation must not introspect a finalizer parser and silently adapt to a renamed field,
new role, reordered gate, changed byte rule or later version. Such a change requires a new reviewed
descriptor or later preparer version.

V2.9 adds no Pydantic production artifact and no committed Schema. Its draft values, path seals,
approval summaries and frozen operational dataclasses are local operational types. All existing
62 committed Schemas remain normalized-LF byte-identical. V2.7 and v2.8 APIs, CLIs, contracts,
policies and behavior remain unchanged.

## Trust split and data flow

The fixed flow is:

```text
human-authored repository-external draft
  -> role-specific v2.9 inspection
  -> exact draft / candidate / parent approval anchors
  -> separate human create approval
  -> role-specific v2.9 finalization
  -> one create-new canonical owner-only authoring input
  -> stop
```

Any later use is a different operation:

```text
explicit v2.9 output path
  -> separate human approval for one exact v2.7 command
  -> v2.7 independently reopens and validates current bytes
```

The v2.9 result is not a Request, Instruction, Decision, Record, approval, receipt or bearer token.
It does not preserve a trusted snapshot between operations. Finalization reconstructs the same
candidate from current draft bytes and current parent identity rather than consuming an inspection
cache.

## Draft envelope

The draft is an explicitly selected repository-external JSON transport object. It is untrusted,
non-authoritative and not retained by v2.9. It is not a contract and has no committed Schema.

Every Maker draft contains exactly:

```text
authoring_role
document_type
draft_format_version
payload
target_finalizer_module
target_finalizer_version
```

Every Checker draft contains exactly:

```text
authoring_role
document_type
draft_format_version
payload
target_finalizer_module
target_finalizer_version
```

The common fixed values are:

```text
document_type=sdc.trusted-local-use-scope-review-authoring-draft
draft_format_version=1.0.0
target_finalizer_module=sdc.real_asset_use_scope_review_finalizer_v27
target_finalizer_version=v2.7
```

`authoring_role` is exactly `MAKER` or `CHECKER` and must match the selected command. `payload` is
one exact JSON object whose members are fixed by that role. A missing, unknown, defaulted, coerced
or mismatched envelope or payload member fails closed. Human-authored fields are never permitted at
the envelope top level.

The draft parser accepts ordinary JSON whitespace, key reordering and either LF or CRLF transport
line endings. Those differences are permitted only because the draft is not the v2.7 authoring
input. It rejects a UTF-8 BOM, malformed UTF-8, duplicate keys at any depth, non-finite constants,
unknown or missing fields, a top-level non-object, non-string paths, type coercion and oversized or
empty input. Raw draft bytes are never normalized or rewritten in place.

Each draft is an ordinary, single-link file of at most 65,536 bytes. It remains sensitive human
input and must be held in an explicitly approved private source area. V2.9 never changes its ACL,
moves it, deletes it or claims to remediate disclosure that occurred before the explicit read.

## Maker authoring rules

The Maker draft's `payload` contains only:

```json
{
  "request_basis": "synthetic example only"
}
```

The example shows shape only and is not a default. `request_basis` is human-authored, non-empty and
at most 2,000 characters. It must already be NFC, equal its own `strip()` and contain no C0 or DEL
control character. V2.9 never trims, normalizes, translates, expands or supplies the text.

The canonical candidate produced from an accepted Maker draft is the exact payload object and
contains exactly the one `request_basis` member. No draft envelope member, including
`authoring_role` or `draft_format_version`, enters the candidate.

## Checker authoring rules

The Checker draft's `payload` contains only:

```text
checker_basis
disposition
gate_results
```

`gate_results` contains exactly six objects in this fixed order:

```text
COPYRIGHT_USE_SCOPE
LIKENESS_USE_SCOPE
PRIVACY_USE_SCOPE
TERRITORY_USE_SCOPE
CONTENT_ROLE_USE_SCOPE
OFFLINE_ONLY_RESTRICTIONS
```

Each object contains exactly `approved`, `gate` and `note`. `approved` is an exact JSON Boolean. An
approved gate has a null note. A failed gate has a non-empty Checker-authored note of at most 1,000
characters. Notes satisfy the same NFC, strip and control-character boundary as the basis.

`checker_basis` is non-empty and at most 2,000 characters. `disposition` is exactly one of:

```text
PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY
NEEDS_REVISION
REJECTED
```

A PASS requires all six gates to pass. A non-PASS disposition requires at least one failed gate.
V2.9 does not infer whether a negative result is NEEDS_REVISION or REJECTED and does not derive an
issue code, conclusion or Provider eligibility. Those remain the exact human choice and later
v2.7 pure-compiler behavior.

The canonical Checker candidate is the exact payload object and contains only the three v2.7
authoring members. No envelope role, version, identity, time, approval anchor, policy or authority
field is added.

## Canonical authoring bytes

Both role candidates use the exact v2.7 canonical-document representation:

```text
UTF-8
no BOM
ensure_ascii=false
sorted object keys
two-space indentation
one LF after the final closing brace
no CRLF
```

The candidate is bounded to 65,536 bytes. V2.9 validates semantic values first and then serializes
the exact accepted value. It may normalize draft JSON whitespace, key order and line endings only
by creating a different absent output. It never normalizes human text and never edits the draft.

Synthetic compatibility tests must feed the exact generated bytes into the unchanged v2.7
role-specific authoring parser and complete synthetic preflight paths. Value equivalence without
byte equivalence is not sufficient.

## Inspection anchors

Inspection calculates and emits exactly three comparison anchors and one bounded candidate-size
field:

```text
draft_sha256
candidate_authoring_sha256
output_parent_seal_sha256
candidate_authoring_size_bytes
```

`draft_sha256` is the lowercase SHA-256 of the exact raw draft bytes read during the stable bounded
capture. Formatting or LF/CRLF drift therefore changes this anchor even when it would reconstruct
the same candidate.

`candidate_authoring_sha256` is the lowercase SHA-256 of the exact canonical v2.7 authoring
candidate bytes. It identifies the human payload and canonical transport that finalization must
reproduce. `candidate_authoring_size_bytes` is the exact positive candidate-byte count and is not
an approval guard. Neither field is a Request or Instruction digest or accepted by v2.7 as an
expected guard.

`output_parent_seal_sha256` binds the one admitted existing output parent without disclosing its
path. Its exact internal payload is:

```text
normalized_absolute_path=<exact normalized absolute string>
physical_identity=[st_dev, st_ino]
platform=WINDOWS|POSIX
st_file_attributes=<exact integer, or zero when unavailable>
st_gid=<exact integer>
st_mode=<exact integer including directory type bits>
st_uid=<exact integer>
```

The payload is compact sorted-key `ensure_ascii=false` UTF-8 JSON with no final LF. The seal is:

```text
SHA256(b"sdc:v29:output-parent-seal\0" + compact-parent-payload)
```

Windows normalized paths use backslashes, remove a non-root trailing separator and preserve the
submitted case. POSIX uses `/` and removes a non-root trailing separator. The stored value is never
case-folded. Modification time, creation time and link count are excluded because ordinary
create-new legitimately changes directory metadata. Physical identity, path, mode, owner/group
and file attributes remain bound. Directory enumeration, child names and directory contents are
not included.

The parent seal is comparison-only. It does not grant permission to create a child, prove parent
privacy, freeze directory contents or replace finalization-time parent revalidation.

Every expected SHA option accepts only lowercase `[0-9a-f]{64}` and is lexically rejected before a
private draft is opened. The three expected values never enter the output payload and cannot
override a calculated value.

## `inspect-maker-authoring` and `inspect-checker-authoring`

An inspection performs this fixed sequence:

```text
admit exact draft and existing output parent
  -> capture exact bounded draft bytes
  -> validate role-specific envelope and human fields
  -> build exact canonical authoring candidate
  -> calculate draft and candidate-authoring SHA-256 values
  -> derive the exact required output filename from candidate SHA-256
  -> require output-parent / required-output-filename to be absent
  -> capture the output parent seal
  -> repeat draft and parent capture
  -> require exact equality
  -> emit bounded summary and stop
```

It creates no file and makes no permission change. The operation accepts no output filename,
expected guard, identity path, timestamp, Request, Instruction, Decision, Record or closure path.

Its fixed status is:

```text
AUTHORING_CANDIDATE_INSPECTED_FOR_SEPARATE_CREATE_APPROVAL_ONLY
```

The human must separately approve the exact role, draft path, reported required output filename,
intended absent output path and all three anchors. Inspection does not reserve the name, approve
finalization or invoke it.

## `finalize-maker-authoring` and `finalize-checker-authoring`

Finalization derives the direct parent from the explicit absent `--output`; it accepts no separate
parent path. That derived parent must produce the exact approved parent seal. The complete fixed
sequence is:

```text
lexically validate three expected lowercase SHA-256 values
  -> admit exact draft, absent output and existing direct parent
  -> require the current parent seal to match
  -> capture exact bounded draft bytes
  -> require the current draft SHA-256 to match
  -> revalidate the role-specific envelope and human fields
  -> rebuild the exact canonical candidate
  -> require the current authoring SHA-256 to match
  -> recapture draft and parent
  -> exclusive owner-only create-new
  -> write, flush and same-handle bounded reread
  -> strict role-specific parse and exact-byte comparison
  -> verify opened-file identity and owner-only permissions
  -> recapture draft and parent again
  -> close all retained handles with checked results
  -> commit and emit bounded summary
```

Any expected mismatch fails before output creation. Expected values are not caches and do not skip
a draft read, semantic validation, canonical reconstruction, parent check or post-write recapture.

The fixed success status is:

```text
AUTHORING_INPUT_CREATED_FOR_SEPARATE_MANUAL_V27_PREFLIGHT_ONLY
```

The output remains a hostile authoring input. A later v2.7 command must be separately approved with
the exact output path and every other applicable closure path, timestamp and approval anchor. V2.9
never invokes that command.

## Role isolation

Role separation is structural rather than caller-selected:

- four distinct command parsers exist;
- four distinct Python functions exist;
- no public `role` parameter or `--role` option exists;
- each inspector accepts only its exact envelope and payload members;
- each finalizer repeats the same role-specific parse and candidate build;
- Maker output cannot contain Checker fields;
- Checker output cannot contain Maker fields; and
- no command reads or writes both role inputs.

V2.9 does not authenticate a natural person, prove independence, create identity-reference files or
implement role substitution. Later v2.7 path, physical-file and digest inequality remain procedural
separation checks only. Human governance must ensure one person does not approve their own
candidate within one stage.

## Path admission and trust areas

Every supplied path is explicit, fully qualified, local and repository-external. The boundary
rejects:

- relative, empty, UNC, network, device and extended-device paths;
- alternate data streams;
- environment, home-directory or shell expansion;
- symbolic links, junctions and reparse points in an existing component;
- non-anchor mounts and bind mounts;
- hard-linked or non-regular draft files;
- wrong existing/missing file or directory kinds;
- lexical, Windows-case-folded, resolved or physical aliases;
- any path in a Git tree, including repository `output/` and `tmp/`; and
- mutable alias components such as `latest`, `current` or `newest`.

The draft and output parent are separate trust areas. The output parent must be neither equal to,
an ancestor of nor a descendant of the draft parent. Finalization requires the output to be absent
and its direct parent to be the exact inspected parent. The program never scans a directory,
selects a sibling or creates a missing parent.

The draft file and the pre-existing output parent must each be owned by the current effective
user on every capture. POSIX requires `st_uid == geteuid()`; Windows requires the named owner SID
to equal the effective token-user SID. This ownership check does not claim that the draft has an
owner-only ACL, and the preparer never repairs either object's permissions.

Role admission has four mutually reinforcing checks:

1. the selected command is Maker-specific or Checker-specific;
2. the draft basename ends, case-insensitively, with the exact applicable suffix;
3. the envelope `authoring_role` equals the selected role; and
4. `payload` contains exactly that role's members and policy shape.

The exact draft suffixes are:

```text
MAKER:   .maker-authoring-draft-v29.json
CHECKER: .checker-authoring-draft-v29.json
```

Finalization also derives and requires one exact output basename from the calculated candidate
digest:

```text
MAKER:   maker_use_scope_review_authoring_input_v27_<candidate-authoring-sha256-first-20>.json
CHECKER: checker_use_scope_review_authoring_input_v27_<candidate-authoring-sha256-first-20>.json
```

The twenty-character suffix is the first twenty lowercase hexadecimal characters of the exact
calculated candidate authoring SHA-256. `--output` must use that basename byte-for-byte; a
value-equivalent spelling, different prefix, different digest fragment or role mismatch fails
before create. The tool derives no directory and emits no path in its summary.

All names remain neutral and may not separately encode `approved`, `authorized`, `pass`,
`rejected`, `needs` or `revision` as a token.

## Owner-only create-new boundary

Only finalization opens an output for writing. Output creation retains a guarded identity for the
direct parent and one exact created descriptor or handle throughout publication.

On POSIX, creation uses `openat` relative to a guarded parent descriptor with
`O_NOFOLLOW|O_CREAT|O_EXCL|O_CLOEXEC` and exact mode `0600`. `fstat` verifies the effective-user
owner, regular-file kind, single-link state and exact mode.

On Windows, creation uses `CreateFileW` on the guarded normalized path with
`GENERIC_READ|GENERIC_WRITE|DELETE`, share mode `0`, `CREATE_NEW`, `FILE_ATTRIBUTE_NORMAL`, a
non-inheritable handle and an explicit protected security descriptor. The owner is the effective
token-user SID. The DACL contains exactly one non-inherited allow ACE for that SID with
`FILE_ALL_ACCESS`; no inherited or additional ACE is accepted. The handle, full path and guarded
parent identities are rechecked before commit.

No operation offers overwrite, append, truncate-existing, rename-as-latest, backup, permission
repair, chmod, ACL widening or best-effort mode. An existing target fails closed and is never read,
modified or removed.

## Same-handle verification, rollback and quarantine

After output creation begins, finalization retains the exact descriptor or handle through:

```text
complete canonical write
flush file and required directory metadata
same-handle bounded reread
exact candidate-byte comparison
strict role-specific semantic parse
file identity and owner-only permission verification
complete draft and parent recapture
checked descriptor and parent-guard close
```

If a failure occurs before create, no output exists. If a failure or `BaseException` occurs after
create and the retained descriptor is provably live, rollback first invalidates the exact created
object through that descriptor. It must not delete through an unguarded pathname or harm an
independent replacement.

On POSIX, rollback poisons through the retained descriptor and uses the guarded parent descriptor
and exact inode relationship; it performs no unguarded pathname unlink. On Windows, rollback
requests deletion only through the exact retained OS handle and treats deletion as confirmed only
after checked close and name absence. Close uncertainty is never retried through a reused handle
number.

If exact invalidation or safe deletion cannot be proven, the operation reports:

```text
ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED
```

The one exact output trust area must then be isolated for a separate human audit. A zero-byte,
poisoned or otherwise invalid remnant is not an authoring input and must not be repaired,
overwritten, verified or passed to v2.7. There is no automatic retry.

## Public Python surface

The public surface consists only of frozen operational types and role-specific functions:

```text
AuthoringInspectionV29
PreparedAuthoringInputV29
TrustedLocalReviewAuthoringPreparationError
TrustedLocalReviewAuthoringQuarantineRequired
finalize_checker_authoring
finalize_maker_authoring
inspect_checker_authoring
inspect_maker_authoring
main
```

`AuthoringInspectionV29` carries the role, inspection status, `draft_sha256`,
`candidate_authoring_sha256`, `candidate_authoring_size_bytes`, `required_output_filename` and
`output_parent_seal_sha256`. `PreparedAuthoringInputV29` carries the role, finalization status,
recalculated `draft_sha256`, `authoring_input_sha256` and `authoring_input_size_bytes`. These are
not Pydantic models, contracts, receipts or authorization artifacts. The ordered `__all__` is
exactly the list above. No public generic JSON canonicalizer, ACL repair function, role dispatcher,
writer adapter or v2.7 path-dataclass converter is exposed.

The implementation may contain a narrowly scoped module-private owner-only byte writer. It must
not change v2.7 or treat v2.7 private functions as a newly supported public filesystem API.

## Bounded success summaries

Every success emits exactly one compact, sorted-key UTF-8 JSON object plus one LF to stdout and
nothing to stderr. Common fields are:

```text
automated_execution_allowed=false
authoring_role=MAKER|CHECKER
current_gate=HUMAN_GATE
execution_authorized=false
manual_confirmation_required=true
operation=<exact selected operation>
posts_allowed=0
preparer_version=v2.9
provider_requests=0
provider_state=NOT_AUTHORIZED
target_finalizer_module=sdc.real_asset_use_scope_review_finalizer_v27
target_finalizer_version=v2.7
usage_restriction=MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION
```

Inspection additionally emits:

```text
status=AUTHORING_CANDIDATE_INSPECTED_FOR_SEPARATE_CREATE_APPROVAL_ONLY
draft_sha256=<lowercase-64-hex>
candidate_authoring_sha256=<lowercase-64-hex>
output_parent_seal_sha256=<lowercase-64-hex>
candidate_authoring_size_bytes=<bounded-positive-integer>
required_output_filename=<exact-role-and-candidate-bound-basename>
```

Finalization independently recalculates the draft and parent anchors, rebuilds the approved
candidate, creates and same-handle verifies the exact output, and emits:

```text
status=AUTHORING_INPUT_CREATED_FOR_SEPARATE_MANUAL_V27_PREFLIGHT_ONLY
draft_sha256=<lowercase-64-hex>
authoring_input_sha256=<lowercase-64-hex>
authoring_input_size_bytes=<bounded-positive-integer>
```

No success or failure output includes a path, basis, gate result, note, disposition, draft content,
identity content, operating-system exception string or Provider fact. The SHA values are audit and
comparison fingerprints only. They are not identity proof, Request/Instruction anchors or
authority tokens.

Ordinary failure writes nothing to stdout, writes exactly this compact object plus LF to stderr and
exits `2`:

```json
{"error":"FAILED_CLOSED"}
```

Unconfirmed rollback writes nothing to stdout, writes exactly this object plus LF to stderr and
exits `3`:

```json
{"error":"ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"}
```

The filesystem commit and delivery of the final stdout line cannot be one atomic operation. If a
caller loses, truncates or cannot decode the success line after finalization may have committed,
the result is uncertain: it must not retry or infer failure from missing stdout. A human must
separately inspect the exact approved output trust area under new read-only authority before any
later step. This reporting uncertainty does not authorize deletion, repair, v2.7 preflight or
reuse of the consumed approval.

Argument parsing is fail-closed, disables abbreviation and rejects duplicate singleton options.
Malformed expected hashes fail before a private draft is opened. No failure triggers a retry,
fallback role, broader path or permission repair.

## Separate approval sequence

Every real operation remains independently approved:

1. one approval names one exact role-specific draft and output parent and permits one inspection;
2. inspection stops and exposes only the bounded candidate anchors;
3. a human reviews the exact draft, role, intended absent output and all three anchors;
4. a new approval names the same exact draft, exact absent output and expected anchor triple and
   permits one role-specific finalization;
5. finalization creates one authoring input and stops; and
6. any later v2.7 preflight requires a new approval naming the complete applicable closure,
   identity, authoring path, explicit time and expected anchors where applicable.

No approval flows automatically to the next line. The output-parent seal and authoring digest may
be quoted to identify what a human reviewed, but neither may be passed to v2.7 as a substitute for
the exact path and current bytes.

## Synthetic-only implementation requirements

Implementation and tests use only generated temporary directories, synthetic draft text and
synthetic identities. They must not inspect, hash or process a real Pack, Manifest, media object,
Evidence, qualification record, Rights Manifest, Use Plan, identity reference, authoring input or
Review Record. They must not read or modify repository `output/` or `tmp/`.

The test suite must prove at least:

- exact public API and four-command CLI snapshots, with no generic `--role`;
- exact Maker and Checker draft envelope fields and role rejection;
- LF, CRLF, key-order and indentation variants producing the same canonical authoring bytes while
  retaining distinct raw draft anchors where raw bytes differ;
- BOM, invalid UTF-8, duplicate key, non-finite value, unknown/missing field and coercion rejection;
- exact human-text NFC, strip, control-character and size boundaries;
- fixed six-gate order, exact Boolean type, note rules and all disposition combinations;
- exact canonical output bytes and acceptance by the unchanged v2.7 role parsers and synthetic
  preflight flows;
- lowercase expected-hash validation before any draft content read;
- wrong draft, candidate or output-parent expected anchor failure before create;
- absolute local path, repository exclusion, alias, hard-link, reparse and mount admission;
- output-parent separation, absence, identity swap and create-new race behavior;
- POSIX owner/mode `0600` behavior;
- native Windows protected owner-only DACL and non-inheritable handle behavior;
- write, flush, reread, parse, permission, recapture and close fault injection;
- exact-handle rollback, independent replacement survival and quarantine-required outcomes;
- exact bounded stdout/stderr bytes without paths or human conclusions;
- no clock, network, Key, Provider, Runtime, database, ledger or finalizer invocation;
- no directory creation, receipt, cache, log, permission repair or draft mutation;
- all existing committed Schema bytes remaining unchanged; and
- v2.7 and v2.8 public surfaces and behavior remaining unchanged.

Full offline `make check` must pass in a fresh LF-preserving isolated worktree that excludes the
repository `output/` and `tmp/` directories. Because the feature exists primarily to enforce
Windows owner-only semantics, synthetic validation is incomplete without a native Windows-focused
DACL/create-new/rollback run; mocked Linux coverage cannot replace it.

## Explicit non-goals and prohibitions

V2.9 must not:

- create, edit, verify or authenticate a Maker or Checker identity file;
- prove two natural people acted or implement role substitution;
- combine Maker and Checker fields in one draft or output;
- accept a generic role switch or let one command fall back to the other role;
- create or modify a Request, Instruction, Decision or Review Record;
- compute or accept requested/evaluated times or v2.7 expected module anchors;
- inspect or verify the complete v2.7 physical closure;
- invoke a v2.7 finalizer or turn output into executable arguments;
- consume or update a v2.8 seed or checklist;
- generate a shell command, response file, pipeline, watcher, queue or orchestration function;
- combine inspection and creation under one automatic operation;
- infer, recommend, default or translate a Gate, note, disposition or basis;
- trim, NFC-normalize or otherwise repair human text;
- overwrite, append, mutate in place, repair an ACL or chmod an existing file;
- create a missing directory, discover a sibling or select latest/current/newest;
- read a wall clock, filesystem-selected time or environment-selected policy;
- create an entitlement, authorization, permit, task, ledger row or registry entry;
- select or contact a Provider, model, account, region, operation or price;
- read a Key, use a network, upload, POST, retain, train, process, generate, purchase or publish;
- claim present-day rights, hold/revocation clearance, identity validity or legal sufficiency; or
- interpret an authoring digest, successful create or later PASS as execution authority.

## Alternatives rejected

### Put human text directly on the command line

Rejected because process listings, shell history, quoting and Unicode handling would recreate the
threat that v2.7's authoring-file transport was designed to avoid.

### Accept one generic command with `--role`

Rejected because a runtime role switch weakens physical responsibility separation and increases
the chance that a Checker payload is prepared through a Maker path or vice versa. Four exact
commands keep role-specific parsers, summaries and tests visible.

### Canonicalize or chmod the draft in place

Rejected because repair would overwrite the human-reviewed source, blur raw-draft and prepared
bytes, create rollback ambiguity and encourage reusing a path whose prior permissions were broad.
Only a distinct absent output may be created.

### Combine inspection and finalization

Rejected because a single operation would erase the human opportunity to review the exact raw
draft, canonical candidate and output-parent anchors before creation. It would also conflict with
the explicit per-operation approval structure retained by v2.7 and v2.8.

### Let v2.7 consume a v2.9 receipt or digest

Rejected because a digest cannot replace current exact bytes and would turn an inert preparation
summary into a bearer object. V2.7 must continue to receive an explicit authoring path and perform
its own owner-only, byte and semantic validation.

### Add a browser UI or mutable workspace in this slice

Deferred because canonical create-new and Windows permissions are the immediate bounded problem.
A UI would add static-asset, download and workspace trust questions and requires a separate design.
V2.9 neither prevents nor approves a future separately reviewed non-technical authoring surface.

## Consequences

The two-person team gains a deterministic way to turn one explicitly reviewed Maker or Checker
draft into the exact bytes and Windows/POSIX permissions that v2.7 requires. CRLF, key order and
indentation stop being manual publication hazards, while raw draft changes, canonical candidate
changes and output-parent replacement remain visible through separate approval anchors.

The deliberate cost is two commands and two approvals per created authoring input. The tool does
not reduce v2.7's Request, Instruction or Record gates and does not automate role handoff. That
ceremony is intentional: safe byte and permission preparation must not become an implicit review,
identity, workflow or execution service.

Every state remains:

```text
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
automated_execution_allowed=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```
