# Trusted-local Use Scope Review authoring preparer v2.9

## Status and authority boundary

This runbook freezes the trusted-local v2.9 preparation boundary for the two private authoring
inputs consumed by the immutable v2.7 Use Scope Review finalizer. The preparer reduces JSON
formatting and owner-only file-creation mistakes. It does not act as a Maker or Checker, decide a
gate, authenticate an identity, invoke a finalizer or grant authority.

Every operation remains:

```text
current_gate=HUMAN_GATE
execution_authorized=false
provider_state=NOT_AUTHORIZED
provider_requests=0
posts_allowed=0
```

An inspect result is comparison material for a later, separately approved create-new operation. A
created authoring input is still hostile, non-authoritative input to a later, separately approved
v2.7 preflight. Neither result authorizes generation, execution, publication, Provider access,
remote processing, retention, training, purchase, upload, submission or contact.

Implementation, tests and demonstrations use synthetic temporary data only. This design does not
authorize a real draft read, real authoring-file creation, commit, push, PR, merge, deployment or
Provider operation.

## Module and frozen command surface

The module is:

```text
sdc.real_asset_use_scope_review_authoring_preparer_v29
```

It exposes exactly four CLI operations:

```text
python -m sdc.real_asset_use_scope_review_authoring_preparer_v29 \
  inspect-maker-authoring \
  --draft <absolute-existing-maker.maker-authoring-draft-v29.json> \
  --output-parent <absolute-existing-output-parent>

python -m sdc.real_asset_use_scope_review_authoring_preparer_v29 \
  inspect-checker-authoring \
  --draft <absolute-existing-checker.checker-authoring-draft-v29.json> \
  --output-parent <absolute-existing-output-parent>

python -m sdc.real_asset_use_scope_review_authoring_preparer_v29 \
  finalize-maker-authoring \
  --draft <absolute-existing-maker.maker-authoring-draft-v29.json> \
  --output <absolute-new-output-json> \
  --expected-draft-sha256 <lowercase-64-hex> \
  --expected-authoring-sha256 <lowercase-64-hex> \
  --expected-output-parent-seal-sha256 <lowercase-64-hex>

python -m sdc.real_asset_use_scope_review_authoring_preparer_v29 \
  finalize-checker-authoring \
  --draft <absolute-existing-checker.checker-authoring-draft-v29.json> \
  --output <absolute-new-output-json> \
  --expected-draft-sha256 <lowercase-64-hex> \
  --expected-authoring-sha256 <lowercase-64-hex> \
  --expected-output-parent-seal-sha256 <lowercase-64-hex>
```

Every option is required exactly once. Abbreviations, positional alternatives, response files,
standard-input JSON, inline JSON, environment defaults, default roots and directory-discovery
options are rejected. The CLI has no `--force`, `--overwrite`, `--repair`, `--chmod`, `--execute`,
`--finalizer`, `--provider`, `--latest`, `--current`, `--newest`, `--clock`, `--approve` or
pass-through argument.

There is no helper verification command. Successful finalization performs same-handle byte and
permission verification before commit. A later v2.7 preflight independently reopens and validates
the created authoring input under a new explicit approval.

## Draft envelope

The draft is an explicitly selected, repository-external, non-authoritative transport object. Its
top-level JSON object contains exactly six members:

```json
{
  "authoring_role": "MAKER",
  "document_type": "sdc.trusted-local-use-scope-review-authoring-draft",
  "draft_format_version": "1.0.0",
  "payload": {
    "request_basis": "synthetic example only"
  },
  "target_finalizer_module": "sdc.real_asset_use_scope_review_finalizer_v27",
  "target_finalizer_version": "v2.7"
}
```

The fixed envelope values are:

| Member | Required value |
|---|---|
| `document_type` | `sdc.trusted-local-use-scope-review-authoring-draft` |
| `draft_format_version` | `1.0.0` |
| `authoring_role` | `MAKER` or `CHECKER`, matching the selected command |
| `target_finalizer_module` | `sdc.real_asset_use_scope_review_finalizer_v27` |
| `target_finalizer_version` | `v2.7` |
| `payload` | The exact role-specific object below |

These version and role fields are comparison-only selectors. They do not confer authority, locate
a finalizer dynamically or allow interface introspection. Any unknown version, module, role,
member or role/command mismatch fails closed.

The bound review policy remains `2.6.0`. V2.9 does not accept a policy path, policy version option
or caller-supplied gate order and does not modify the immutable v2.6 policy or v2.7 finalizer.

### Maker payload

The Maker payload contains exactly one member:

```json
{
  "request_basis": "synthetic example only"
}
```

`request_basis` is a non-empty human string of at most 2,000 characters.

### Checker payload

The Checker payload contains exactly three members:

```json
{
  "checker_basis": "synthetic example only",
  "disposition": "NEEDS_REVISION",
  "gate_results": [
    {
      "approved": false,
      "gate": "COPYRIGHT_USE_SCOPE",
      "note": "synthetic note"
    },
    {
      "approved": true,
      "gate": "LIKENESS_USE_SCOPE",
      "note": null
    },
    {
      "approved": true,
      "gate": "PRIVACY_USE_SCOPE",
      "note": null
    },
    {
      "approved": true,
      "gate": "TERRITORY_USE_SCOPE",
      "note": null
    },
    {
      "approved": true,
      "gate": "CONTENT_ROLE_USE_SCOPE",
      "note": null
    },
    {
      "approved": true,
      "gate": "OFFLINE_ONLY_RESTRICTIONS",
      "note": null
    }
  ]
}
```

The six gates appear exactly once in the displayed order. `approved` is an exact JSON boolean. An
approved gate has a null `note`; a failed gate has a non-empty human note of at most 1,000
characters. `checker_basis` is non-empty and at most 2,000 characters. `disposition` is exactly one
of:

```text
PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY
NEEDS_REVISION
REJECTED
```

`PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY` requires all six gates to pass. Either negative
disposition requires at least one failed gate. The preparer validates these combinations but never
chooses, completes or repairs them.

Every human string must already be NFC, equal its own `strip()`, and contain no C0 or DEL control
character. The preparer never trims, normalizes, paraphrases, generates or defaults human text.

## Draft transport and admission

The draft is bounded at 65,536 bytes. It must be strict UTF-8 without a BOM and parse as one JSON
object with no duplicate keys, non-finite constants, coercion, defaulting, missing member or unknown
member. Ordinary JSON whitespace, key reordering and either LF or CRLF transport whitespace are
accepted. The draft itself need not use canonical indentation because it is not the v2.7 authoring
input.

`draft_sha256` is the lowercase SHA-256 of the exact raw draft bytes, including their whitespace
and line endings. It is intentionally distinct from the canonical candidate digest.

The draft path must be one explicit, absolute, local path to an ordinary single-link file owned by
the current effective user. Every lexical component is admitted without following redirection.
The preparer rejects:

- relative or empty paths;
- UNC, network, device and extended-device namespaces;
- alternate data streams;
- symbolic links, junctions, reparse points and mount crossings;
- hard-linked drafts;
- repository paths, including repository `output/` and `tmp/`;
- a component token `latest`, `current` or `newest`;
- directory scans, globs, sibling inference and filename searches.

On POSIX, ownership means `st_uid == geteuid()`. On Windows, the file owner SID equals the current
effective token-user SID. Unlike the finalized authoring input, the draft is deliberately not
required to have an owner-only mode or DACL. It is untrusted transport, and the helper cannot undo
any exposure that occurred before invocation. A real draft must therefore still be placed in a
separately reviewed private source area.

Every operation captures the exact draft at least twice using a bounded handle read and requires
stable path, resolved path, physical identity, single-link count, size, metadata and raw digest.
Replacement or mutation during one invocation fails closed. An identical-byte replacement between
inspect and finalize is not treated as the same inode; the later operation still performs fresh
admission and binds the approved bytes through `expected-draft-sha256`.

The draft basename must have the role-specific complete suffix, compared case-insensitively:

```text
.maker-authoring-draft-v29.json
.checker-authoring-draft-v29.json
```

The selected command, complete filename suffix, envelope `authoring_role` and role-specific payload
shape must agree in all four dimensions. A Maker command rejects a Checker suffix, Checker role or
Checker payload, and the Checker command rejects the corresponding Maker forms. No role is inferred
from only one of these values and no mismatch is repaired.

## Candidate authoring bytes

The candidate authoring input is the role-specific `payload`, not the six-member draft envelope.
It is serialized as:

```text
UTF-8 without BOM
ensure_ascii=false
keys sorted recursively
two-space indentation
one and only one final LF
```

The resulting document is at most 65,536 bytes and must be accepted byte-for-byte by the matching
v2.7 authoring parser. `candidate_authoring_sha256` and `authoring_input_sha256` are the lowercase
SHA-256 of those complete canonical bytes, including the final LF.

The candidate contains no draft metadata, path, role label, module name, version, ID, digest,
filename, timestamp, identity reference, expected guard, authority value or Provider fact. It is
not a Request or Instruction contract and has no committed Schema.

## Digest-derived filename without a naming cycle

After constructing the canonical candidate, inspect derives exactly one required basename from the
first 20 lowercase hexadecimal characters of the full candidate SHA-256:

```text
maker_use_scope_review_authoring_input_v27_<candidate-sha256-first-20>.json
checker_use_scope_review_authoring_input_v27_<candidate-sha256-first-20>.json
```

For example, a Maker candidate beginning with `0123456789abcdefabcd` requires:

```text
maker_use_scope_review_authoring_input_v27_0123456789abcdefabcd.json
```

The full digest, not the 20-character prefix, remains the finalization equality guard. The candidate
bytes contain neither their digest nor filename, so no recursive digest or naming loop exists.
Inspect computes candidate bytes first, then the digest, then the required basename. Finalize
repeats that order and requires the explicit `--output` basename to equal the derived name exactly.

The preparer never chooses a numeric suffix, resolves a prefix collision, substitutes a new name or
overwrites an existing path. If the required path exists in any form, the operation fails closed.

## Output-parent admission and separation

`--output-parent` names one explicit, pre-existing absolute local directory. Finalize derives the
parent from the explicit `--output`; it accepts no separate parent override. No command creates a
directory or changes a directory owner, mode or DACL.

The parent must be owned by the current effective user at every capture: POSIX requires
`st_uid == geteuid()`, while Windows requires the named owner SID to equal the effective
token-user SID. This is an admission predicate, not a permission-repair step and not proof that
the directory is private from every other principal.

The output parent and draft parent must be separate at all of these layers:

- normalized lexical path;
- Windows case-insensitive comparison where applicable;
- fully resolved path;
- physical directory identity.

Neither may be an ancestor or descendant of the other. The required output must also be distinct
from the draft under lexical, case-folded, resolved and physical checks. Repository paths and all
unsafe path classes rejected for drafts are also rejected for the output parent and output.

Inspect verifies that the exact parent is safe and that `parent / required_output_filename` is
absent. This is not a reservation. Finalize redoes every check and relies on native create-new to
resolve any concurrent winner.

## Output-parent seal

The output-parent seal binds the inspected path and physical directory without using timestamps
that legitimately change when a child is created. Its exact payload is:

```json
{
  "normalized_absolute_path": "C:\\synthetic\\maker-authoring",
  "physical_identity": [123, 456],
  "platform": "WINDOWS",
  "st_file_attributes": 16,
  "st_gid": 0,
  "st_mode": 16895,
  "st_uid": 0
}
```

The members and types are fixed:

| Member | Type and rule |
|---|---|
| `normalized_absolute_path` | Exact normalized absolute string |
| `physical_identity` | Two-integer array `[st_dev, st_ino]` |
| `platform` | Literal `WINDOWS` or `POSIX` |
| `st_file_attributes` | Exact integer, or `0` when unavailable |
| `st_gid` | Exact integer |
| `st_mode` | Exact integer including the directory type bits |
| `st_uid` | Exact integer |

Windows paths use backslashes, remove a non-root trailing separator and preserve the submitted
case. POSIX paths use `/` and remove a non-root trailing separator. Neither platform case-folds the
value stored in the seal.

The payload is encoded as compact, sorted-key, `ensure_ascii=false` UTF-8 JSON with no final LF.
The digest is:

```text
SHA256(
  b"sdc:v29:output-parent-seal\0"
  + compact_sorted_parent_payload_utf8
)
```

`output_parent_seal_sha256` is the resulting lowercase 64-hex digest. Modification time, creation
time and link count are excluded because ordinary create-new changes directory metadata. The
physical identity, path, mode, owner/group and file attributes remain bound.

Finalize recomputes the seal from current metadata and compares it with
`--expected-output-parent-seal-sha256` during its initial capture, in the last pre-create capture
before the live direct-parent guard is acquired, and after creation before commit. A mismatch cannot
be repaired by caller values and requires a new inspection and approval.

## Inspect operations

`inspect-maker-authoring` and `inspect-checker-authoring` perform this sequence:

1. Admit and capture the exact draft.
2. Strictly parse the six-member envelope and require the selected role and v2.7 target.
3. Validate every human-owned payload value without normalization or repair.
4. Build the exact canonical candidate bytes twice.
5. Compute the raw draft SHA, full candidate SHA and candidate byte count.
6. Derive the exact role-specific output basename.
7. Admit the explicit output parent and enforce draft/output-area separation.
8. Compute the exact output-parent seal.
9. Require the derived output target to be absent.
10. Recapture the draft and parent and require all bytes, identities and the seal to remain stable.
11. Emit one bounded comparison-only success object and stop.

Inspect creates no directory, authoring input, receipt, cache, lock, temporary file or permission
change. It does not reserve the output path and does not invoke v2.7.

## Separate approval handoff

A later finalize approval must independently name:

- the exact role-specific finalize operation;
- the exact draft path;
- the exact create-new output path assembled from the reviewed parent and required filename;
- `expected-draft-sha256` from inspect;
- `expected-authoring-sha256` from inspect; and
- `expected-output-parent-seal-sha256` from inspect.

The approval must not replace the paths with a digest or authorize both roles implicitly. An
inspect approval is consumed by inspect only and cannot be reused for finalize. A Maker approval
does not authorize Checker preparation, and neither authorizes a v2.7 preflight.

## Finalize operations

`finalize-maker-authoring` and `finalize-checker-authoring` perform this sequence:

1. Validate all three expected values as exact lowercase SHA-256 strings.
2. Admit and capture the exact draft from scratch.
3. Require the raw draft digest to equal `expected-draft-sha256`.
4. Reparse the exact envelope and rebuild the canonical candidate.
5. Require its full digest to equal `expected-authoring-sha256`.
6. Derive the required basename and require the explicit `--output` to match it exactly.
7. Admit the output parent, enforce trust-area separation and recompute its seal.
8. Require the current seal to equal `expected-output-parent-seal-sha256` and the target to be
   absent.
9. Recapture the draft and rebuild the candidate immediately before create.
10. Acquire the live platform-specific direct-parent guard and revalidate the guarded parent
    identity and target absence.
11. Perform exactly one native create-new with private permissions in effect at creation time.
12. Before writing any human text, prove the new handle, target name, direct-parent guard, owner and
    permissions are bound to the approved target.
13. Write all canonical bytes, flush, reread through the same retained handle, strictly parse and
    compare exact bytes, model, size and digest.
14. Recapture the draft, candidate and parent; require every approval anchor and live identity to
    remain unchanged.
15. Flush required file and directory metadata, close the checked direct-parent guard and output
    handle, emit one bounded success object and stop.

Expected digests and the parent seal are equality gates only. They never supply content, repair a
draft, select a path, prove identity, skip a read or grant authority.

## Common create-new state machine

The candidate is complete and bounded before native create. The target parent is pre-existing and
the target name is absent. The writer retains the exact output descriptor or handle and the live
direct-parent guard through:

```text
native CREATE_NEW
empty-file identity and private-permission verification
complete write
file flush
same-handle bounded reread
strict parse and canonical-byte comparison
draft and parent recapture
final name/handle/parent binding check
required directory flush
checked direct-parent-guard close
checked output-handle close
```

There is no overwrite, append, truncate-existing, rename-as-current, retry, backup-as-authority or
post-hoc permission repair mode. A native `already exists` result before a successful handle is
retained means an independent winner; that object is never opened, modified or deleted.

Any `BaseException` after creation may have begun enters exact-handle rollback. If native create
was entered but the implementation cannot prove whether it returned a retained handle, the result
is quarantine-required rather than an ordinary failure.

## Public Python surface

The public Python surface is limited to these frozen operational types and role-specific entry
points:

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

`AuthoringInspectionV29` is a frozen operational dataclass with exactly these fields: `status`,
`authoring_role`, `draft_sha256`, `candidate_authoring_sha256`,
`candidate_authoring_size_bytes`, `required_output_filename` and
`output_parent_seal_sha256`.

`PreparedAuthoringInputV29` is a frozen operational dataclass with exactly these fields: `status`,
`authoring_role`, `draft_sha256`, `authoring_input_sha256` and
`authoring_input_size_bytes`.

Neither dataclass is a Pydantic contract, receipt, persisted state or bearer authorization. The
ordered `__all__` is exactly the nine-item list above. No public generic role dispatcher, JSON
canonicalizer, ACL repair helper, byte writer, finalizer wrapper or checklist converter is exposed.

## POSIX creation

Every existing path component is admitted and later recaptured under the full no-redirection path
rules. Publication does not retain one descriptor per component. It retains only the direct output
parent descriptor, opened with `O_RDONLY | O_DIRECTORY | O_CLOEXEC`; `fstat` must bind that
descriptor to the approved direct-parent physical identity. The exact target descriptor is then
retained alongside it. Ancestor changes are detected by the required path recaptures; the design
does not claim to keep every ancestor open or prevent every ancestor rename or deletion.

The only target creation is parent-relative:

```text
openat(
  parent_fd,
  exact_basename,
  O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC,
  0600,
)
```

Before writing, direct-parent `fstat`, created-descriptor `fstat` and exact-path `lstat` must prove:

- the opened and named objects have the same device and inode;
- both are ordinary files and not links;
- owner is the effective user;
- mode is exactly `0600`;
- link count is exactly one; and
- size is zero.

The process does not change global `umask`. If the created file does not have exact mode `0600`, it
fails before human text is written. After writing, the same descriptor is rewound and read to EOF
under the fixed bound; pre/post descriptor metadata, name identity, owner, mode and link count must
remain stable. The file and retained parent directory are `fsync`ed before successful close.

## Windows creation

The preparer uses documented Win32 APIs only. It does not use an undocumented NT parent-relative
create primitive.

Every existing path component is admitted and later recaptured under the full local,
non-redirection path rules. Publication retains only one non-inheritable HANDLE for the direct
output parent. The frozen v2.7 writer uses these exact access, share, disposition and flag values
for that direct-parent guard:

```text
OPEN_EXISTING
FILE_READ_ATTRIBUTES
FILE_SHARE_READ | FILE_SHARE_WRITE
FILE_FLAG_BACKUP_SEMANTICS
```

`FILE_SHARE_DELETE` is deliberately absent, while `FILE_FLAG_OPEN_REPARSE_POINT` is not used for
this direct-parent guard. Its volume/file identity must match the admitted direct-parent identity.
The direct-parent HANDLE remains live until commit or rollback; other existing components remain
subject to admission and recapture but do not have retained handles. The design therefore does not
claim to prevent every ancestor rename or deletion.

The target is created exactly once with `CreateFileW`:

```text
desired access:
  GENERIC_READ | GENERIC_WRITE | DELETE

share mode:
  0

creation disposition:
  CREATE_NEW

flags and attributes:
  FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT
```

The current effective token-user SID is obtained by the frozen v2.7 writer.
`SECURITY_ATTRIBUTES` contains a security descriptor with:

- owner equal to that SID;
- a present, protected DACL;
- exactly one non-inherited `ACCESS_ALLOWED_ACE`;
- the same SID as ACE trustee; and
- an access mask that normalizes exactly to `FILE_ALL_ACCESS`.

`bInheritHandle` is false. The protected owner-only descriptor is supplied to `CreateFileW`, so no
broadly readable interval exists between creation and validation. The preparer never creates with
inherited permissions and then calls `icacls`, `SetNamedSecurityInfo` or an equivalent repair.

Before converting the raw HANDLE to a CRT descriptor, handle inspection must prove the exact owner,
DACL, ACE and non-inheritable state. After conversion and before writing any content,
created-descriptor inspection, exact-path inspection and direct-parent HANDLE inspection must prove
the normal non-reparse file type, single-link count, zero size and agreement among the opened file,
named path and guarded direct-parent identities. Full path-component admission and recapture must
also remain stable. Permission and binding checks are repeated after writing and before commit.

FAT, exFAT or any filesystem on which the exact owner-only predicate cannot be established fails
closed. No weaker ACL is accepted.

## Rollback and quarantine

Rollback operates only through the exact retained object handle. It never deletes a pathname after
merely observing matching metadata.

### POSIX rollback

Portable POSIX has no safe unlink-by-open-file-descriptor primitive. Rollback therefore:

1. invalidates the exact open inode by truncating and, where required, writing a fixed invalid
   poison through the retained descriptor;
2. flushes the invalidation;
3. performs one checked descriptor close;
4. uses the still-valid parent descriptor only to confirm the name is absent or still names the
   exact invalidated inode; and
5. performs one checked parent-guard close.

It does not call pathname `unlink` after a stat check. A zero-length or poisoned remnant is not an
authoring input, must not be repaired or overwritten, and blocks later create-new until separately
isolated.

### Windows rollback

Rollback invalidates the exact open file, flushes it, requests delete-pending through that exact
HANDLE, closes it once, and confirms the name is absent or still identifies the exact invalidated
file. It never calls `DeleteFileW` against a replacement path. An independently created winner or
replacement survives.

### Uncertain cleanup

A descriptor or HANDLE number whose close side effect is uncertain is never called again or reused
for rollback. The same rule applies to the direct-parent guard. Any of these conditions produce the
dedicated quarantine result:

```text
ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED
```

The operator must isolate the complete exact output trust area named in the approval. The preparer
does not automatically retry, move, delete, chmod, change a DACL or widen the quarantine scope.
Diagnosis and remediation require a new explicit authorization.

## Success-output protocol

Success writes exactly one compact, sorted-key, UTF-8 JSON object plus one LF to standard output
and nothing to standard error. It never prints a private path, human text, gate note, draft bytes,
output bytes, identity SID, filesystem identity or parent-seal preimage.

Every success object includes these fixed fields:

```json
{
  "automated_execution_allowed": false,
  "current_gate": "HUMAN_GATE",
  "execution_authorized": false,
  "manual_confirmation_required": true,
  "posts_allowed": 0,
  "preparer_version": "v2.9",
  "provider_requests": 0,
  "provider_state": "NOT_AUTHORIZED",
  "target_finalizer_module": "sdc.real_asset_use_scope_review_finalizer_v27",
  "target_finalizer_version": "v2.7",
  "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
}
```

It also includes the exact `operation`, `status` and `authoring_role`.

### Inspect success

The role-specific inspect status is always:

```text
AUTHORING_CANDIDATE_INSPECTED_FOR_SEPARATE_CREATE_APPROVAL_ONLY
```

The only additional variable fields are:

```text
draft_sha256
candidate_authoring_sha256
candidate_authoring_size_bytes
required_output_filename
output_parent_seal_sha256
```

The exact shape is:

```json
{"authoring_role":"MAKER","automated_execution_allowed":false,"candidate_authoring_sha256":"<lowercase-64-hex>","candidate_authoring_size_bytes":123,"current_gate":"HUMAN_GATE","draft_sha256":"<lowercase-64-hex>","execution_authorized":false,"manual_confirmation_required":true,"operation":"inspect-maker-authoring","output_parent_seal_sha256":"<lowercase-64-hex>","posts_allowed":0,"preparer_version":"v2.9","provider_requests":0,"provider_state":"NOT_AUTHORIZED","required_output_filename":"maker_use_scope_review_authoring_input_v27_<20-hex>.json","status":"AUTHORING_CANDIDATE_INSPECTED_FOR_SEPARATE_CREATE_APPROVAL_ONLY","target_finalizer_module":"sdc.real_asset_use_scope_review_finalizer_v27","target_finalizer_version":"v2.7","usage_restriction":"MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"}
```

Checker uses `authoring_role=CHECKER`, `operation=inspect-checker-authoring` and the Checker
required filename. No inspect field claims that a file exists or that v2.7 will pass later.

### Finalize success

The role-specific finalize status is always:

```text
AUTHORING_INPUT_CREATED_FOR_SEPARATE_MANUAL_V27_PREFLIGHT_ONLY
```

The only additional variable fields are:

```text
draft_sha256
authoring_input_sha256
authoring_input_size_bytes
```

The exact shape is:

```json
{"authoring_input_sha256":"<lowercase-64-hex>","authoring_input_size_bytes":123,"authoring_role":"MAKER","automated_execution_allowed":false,"current_gate":"HUMAN_GATE","draft_sha256":"<lowercase-64-hex>","execution_authorized":false,"manual_confirmation_required":true,"operation":"finalize-maker-authoring","posts_allowed":0,"preparer_version":"v2.9","provider_requests":0,"provider_state":"NOT_AUTHORIZED","status":"AUTHORING_INPUT_CREATED_FOR_SEPARATE_MANUAL_V27_PREFLIGHT_ONLY","target_finalizer_module":"sdc.real_asset_use_scope_review_finalizer_v27","target_finalizer_version":"v2.7","usage_restriction":"MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"}
```

Checker uses `authoring_role=CHECKER` and `operation=finalize-checker-authoring`. The output path and
filename are deliberately absent from the success object; they remain explicit in the approval and
CLI invocation.

## Failure-output protocol

An ordinary parser, input, path, anchor, race, permission or runtime rejection writes no standard
output, writes exactly this object plus one LF to standard error, and exits `2`:

```json
{"error":"FAILED_CLOSED"}
```

An unconfirmed post-create rollback writes no standard output, writes exactly this object plus one
LF to standard error, and exits `3`:

```json
{"error":"ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"}
```

Diagnostics never include a path, basis, note, payload, SID, file identity, digest mismatch value,
exception text, Provider fact or partial success object. Parser help and usage errors must not echo
a private option value.

Filesystem commit and final stdout delivery are not atomic. If finalization may have committed but
the success line is missing, truncated or unreadable, the operator must treat the result as
uncertain and must not retry. A new, read-only human authorization is required to inspect the exact
approved output trust area. Missing stdout does not authorize cleanup, repair, a v2.7 preflight or
reuse of the one-time finalization approval.

## Mandatory manual workflow

A permitted future real operation still requires distinct stages:

1. A human prepares and reviews one exact role-labelled draft in a separately approved private
   area.
2. A one-time inspect approval names the exact draft and exact pre-existing output parent.
3. Inspect emits comparison-only digests, byte count, required filename and parent seal, then stops.
4. A human reviews the role, full candidate anchor, required filename and output-parent seal.
5. A new one-time finalize approval names every exact path and all three expected SHA guards.
6. Finalize creates one private authoring input and stops.
7. A human separately approves the applicable v2.7 preflight with its complete physical closure,
   explicit time and other required guards.
8. The v2.7 finalizer independently reopens and validates the authoring input.

No stage automatically triggers the next. Neither digest nor required filename may replace an
explicit path in a later approval. The preparer has no integration that converts its output into a
v2.7 argument array or invokes a v2.7 command.

## Prohibited integration and claims

Project code and operating procedures must not:

- place human basis, gate notes or complete draft JSON in command-line arguments;
- mutate, chmod, rewrite, normalize or delete the draft;
- create a mutable Request, Instruction, Decision or Review Record workspace;
- use inspect output as a bearer authorization or cached workflow state;
- parse preparer stdout into a finalizer invocation;
- generate a shell command, PowerShell array, response file or executable `argv` for v2.7;
- monitor a directory and finalize or preflight automatically;
- create an output directory or choose an alternative filename;
- treat role labelling, path separation or digest inequality as natural-person authentication;
- select an identity reference, role substitute, time, gate answer, disposition or human text;
- infer current rights, revocation status, policy, entitlement or Provider availability;
- read a Key, network, implicit clock, filesystem-selected time or environment-selected policy;
- select or contact a Provider, model, account, region, operation or price;
- upload, POST, purchase, recharge, claim a trial, generate, execute or publish;
- modify entitlement, authorization, Runtime, Worker, database, Temporal, Ark, ledger or migration
  state; or
- modify a v2.6/v2.7 contract, policy or committed Schema.

## Threat and test matrix

All tests use generated synthetic temporary data. The suite must prove the following categories.

### Envelope, role and canonical-byte tests

- Both accepted envelopes produce only their exact role-specific canonical payload.
- BOM, malformed UTF-8, duplicate/unknown/missing keys, non-finite values, coercion and oversize
  drafts fail.
- Reordered keys and LF/CRLF draft whitespace may differ in `draft_sha256` while producing the same
  canonical candidate and candidate digest.
- Human strings reject non-NFC, surrounding whitespace and C0/DEL controls without repair.
- Gate order, boolean exactness, note rules and all disposition combinations match v2.7.
- Candidate bytes are strict UTF-8 without BOM, sorted, two-space indented and have one final LF.
- The complete six-member envelope never appears in the finalized authoring input.

### Digest, filename and parent-seal tests

- Raw draft and canonical candidate hashes bind their exact documented byte domains.
- Maker and Checker filename templates use the first 20 lowercase hex characters exactly.
- Full candidate SHA remains the guard; prefix collision handling never selects a new filename.
- Output name case, suffix, prefix, role or digest-prefix drift fails.
- Parent-seal JSON has the exact seven fields and types, compact sorted encoding, no LF and exact
  domain prefix.
- Windows path case is preserved rather than case-folded in the seal.
- Parent identity, path, mode, uid, gid or file-attribute drift fails.
- Directory mtime/ctime changes caused solely by create-new do not alter the seal.

### Path and snapshot attacks

- Relative, UNC, device, ADS, network, repository, `output/`, `tmp/`, symlink, junction, reparse,
  mount and hardlink inputs fail.
- Glob, recursive glob, directory enumeration, sibling inference and latest/current/newest lookup
  are never called.
- Draft mutation or replacement at every capture boundary fails.
- Output-parent replacement between inspect and finalize fails the expected seal.
- Draft/output lexical, case-folded, resolved, physical or ancestor/descendant overlap fails.
- A concurrent create-new winner survives unchanged and no retry occurs.

### POSIX create and rollback tests

- Parent-relative `openat` uses all required no-follow, exclusive and close-on-exec flags.
- Output owner, exact `0600`, regular type, single link, empty initial size and fd/name identity are
  checked before write and after reread.
- Short write, zero write, flush, reread, parser, canonical, digest and parent-fsync failures roll
  back.
- Replacement races are never deleted through a pathname.
- Rollback leaves only an absent name or the exact invalidated inode.
- Descriptor or parent-guard close uncertainty is exit `3`, and the numeric descriptor is never
  reused.

### Windows create, ACL and rollback tests

- The direct-parent HANDLE binds the expected volume/file ID and uses `FILE_READ_ATTRIBUTES`,
  `FILE_SHARE_READ | FILE_SHARE_WRITE`, `OPEN_EXISTING` and `FILE_FLAG_BACKUP_SEMANTICS`, with no
  delete sharing.
- Full path-component admission and recapture detect ancestor or parent rename, swap or reparse
  injection at the defined capture boundaries; only the direct-parent HANDLE is retained.
- `CreateFileW` uses `CREATE_NEW`, share mode `0`, DELETE access, a non-inheritable handle and the
  explicit security descriptor.
- Wrong owner, absent/NULL/unprotected DACL, extra or inherited ACE, wrong SID, non-normalized mask,
  inheritable handle, reparse output or multiple links fail before text is written.
- A failure after `CreateFileW` returns but before raw HANDLE storage requires exact raw-handle
  cleanup or quarantine.
- Raw HANDLE to CRT descriptor conversion failures cannot leak a live output.
- Delete-pending, file-close and directory-guard-close failures produce quarantine and never reuse
  an uncertain handle value.
- A replacement target is never deleted.

### Cross-operation and authority tests

- Inspect performs no write, mkdir, ACL change, clock read, network access or v2.7 invocation.
- Finalize replays draft parsing, candidate construction, filename and parent seal rather than
  trusting inspect output.
- Every expected SHA is compared only after current values are rebuilt.
- Success and failure JSON have exact sorted fields, one LF and no private data.
- No authoring success result changes any HUMAN_GATE or NOT_AUTHORIZED value.
- Generated synthetic authoring bytes are independently accepted by the matching immutable v2.7
  parser.
- All committed Schema bytes remain unchanged.
- Full offline `make check` passes in a fresh LF-preserving isolated worktree that excludes current
  repository `output/` and `tmp/` material.

Fault injection covers `Exception`, `RuntimeError`, `KeyboardInterrupt` and `SystemExit` across every
native-call/store gap, write boundary, recapture, validation, flush, rollback and checked close.

## Real-operation approval gate

Merging an implementation proves synthetic behavior only. A real inspect approval must name one
exact command, draft and output parent and authorize only the bounded reads needed for that
inspection. A real finalize approval must be issued later and name the exact command, draft,
create-new output and all three expected digests. Each approval is single-use and expires after its
one attempted operation.

Failure never authorizes a retry, a broader path, permission repair, directory creation, alternate
filename or changed draft. Quarantine never authorizes automatic cleanup. Every remediation and
every later v2.7 operation requires a new explicit approval.

Even after successful v2.9 preparation and later historical v2.7 verification, the result does not
prove present-day rights, evidence, identity, policy, capability, pricing, terms, availability,
revocation status or Provider acceptance. `PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY` remains limited
to a separately reviewed proposal-design step and grants no Provider or production authority.
