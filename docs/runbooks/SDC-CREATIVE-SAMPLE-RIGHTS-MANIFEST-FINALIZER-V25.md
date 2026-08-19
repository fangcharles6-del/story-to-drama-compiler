# Trusted Local Rights Manifest Finalizer v2.5

## Purpose and stage boundary

This runbook describes the synthetic-only development and future controlled operation of the
trusted local Pack-level Human Review v2 Rights Manifest boundary. It bridges one exact positive
v2 qualification closure to the pure in-memory v2.4 Manifest consumer. It does not grant or
describe generation, publication, entitlement, authorization, Runtime or Provider access.

During this development stage use only fixed synthetic offline fixtures in isolated test
directories. Do not substitute any current real private Pack, media, Evidence, Reviews, PairCheck,
retained records, Request, Qualifier reference, Instruction, Decision or Manifest into tests,
examples or manual commands. Do not read repository `output/` or `tmp/`.

Every operation remains:

```text
HUMAN_GATE
NOT_AUTHORIZED
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

`rights_qualification_performed=true` and, after finalization,
`rights_manifest_created=true` are audit facts only. They do not authorize another action.

## Public surface

The implementation module is:

```text
sdc.real_asset_rights_manifest_finalizer_v25
```

Its public path envelope and operations are:

```python
class TrustedLocalRightsManifestPaths:
    decision_inputs: TrustedLocalDecisionPaths
    decision: Path

def inspect_manifest_ready(
    paths: TrustedLocalRightsManifestPaths,
    *,
    manifest_at: str,
) -> Literal["READY_FOR_MANIFEST_FINALIZATION"]: ...

def finalize_manifest(
    paths: TrustedLocalRightsManifestPaths,
    output_path: Path,
    *,
    manifest_at: str,
) -> CreativeSampleRealAssetRightsManifestV2: ...

def verify_manifest(
    paths: TrustedLocalRightsManifestPaths,
    manifest_path: Path,
) -> CreativeSampleRealAssetRightsManifestV2: ...
```

The module exposes `TrustedLocalRightsManifestFinalizationError`, its dedicated
`TrustedLocalRightsManifestQuarantineRequired` subclass, and `main` for the exact three-command
CLI. There is no alternate loader, filesystem API, fourth command, hidden automatic continuation,
interactive prompt, repair mode, authorization mode or service endpoint.

Inspection deliberately returns only the fixed non-secret readiness literal to Python callers.
It does not return the verified Decision or a candidate Manifest and must not call the v2.4
builder. Finalization returns the one new Manifest. Verification returns the exact historically
verified existing Manifest.

## Exact CLI commands

Every command has these common options:

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
--request <absolute-request.json>
--qualifier-ref <absolute-qualifier-reference>
--instruction <absolute-instruction.json>
--decision <absolute-decision.json>
```

Together with the Pack root, these 27 explicitly named files form the exact 28-entry source
closure. The commands add only these command-specific options:

```text
inspect-manifest-ready:
  --manifest-at <YYYY-MM-DDTHH:MM:SSZ>

finalize-manifest:
  --manifest-at <YYYY-MM-DDTHH:MM:SSZ>
  --output <absolute-absent-manifest.json>

verify-manifest:
  --manifest-file <absolute-existing-manifest.json>
```

The complete invocation starts with
`python -m sdc.real_asset_rights_manifest_finalizer_v25 <command>`, followed by every common and
command-specific option above. The generated `--help` is authoritative. No command accepts a
policy override, digest override, stable ID, outcome, qualification basis, issue code,
current-time flag, directory-discovery option, glob, `--force`, overwrite or repair flag.
Option abbreviations and repeated singleton options are rejected. Only `--media-path` repeats,
and it must occur exactly fourteen times in manifest ordinal order.

## The 28 explicit source entries

All commands require the same complete source closure:

| Ordinal | Source | Required binding |
|---:|---|---|
| 1 | Frozen Pack root | Explicit absolute directory used only to bind the named manifest and fourteen named media paths; it is not enumerated. |
| 2 | `asset-pack.json` | Must be exactly the manifest inside the selected Pack root. |
| 3–16 | Fourteen frozen media paths | Fourteen separate options in exact Pack ordinal order; each SHA-256, size and object location must agree. |
| 17 | Rights Evidence Bundle | Exact canonical Pack-bound v2 contract. |
| 18 | Reviewer A Pack review | Exact finalized `REVIEWER_A` contract. |
| 19 | Reviewer B Pack review | Exact finalized `REVIEWER_B` contract. |
| 20 | PairCheck | Exact deterministic `READY_FOR_SEPARATE_QUALIFICATION_REVIEW` contract with no issues. |
| 21 | Evidence retained record | Whole-file SHA-256 must match the Request and Decision closure. |
| 22 | Evidence Preparer reference | Whole-file SHA-256 must match the bound reference. |
| 23 | Reviewer A retained reference | Whole-file SHA-256 must match the bound A reference. |
| 24 | Reviewer B retained reference | Whole-file SHA-256 must match the bound B reference. |
| 25 | Qualification Request | Exact canonical Request reconstructed from entries 1–24. |
| 26 | Qualifier reference | Exact whole-file SHA-256 bound by the Instruction and Decision. |
| 27 | Qualification Decision Instruction | Exact canonical v2.2 Instruction; also the retained Qualifier decision record. |
| 28 | Qualification Decision | Exact canonical positive Decision reconstructed from the complete historical closure. |

The two Review `review_record_sha256` fields are canonical review-content digests, not two more
files. The Instruction's complete canonical file digest is the Qualifier decision-record digest,
not a third discoverable record. Do not add paths, infer names or scan for any of them.

No directory enumeration is allowed. The boundary reads only the explicitly named manifest and
fourteen separately supplied media paths, then verifies their manifest order, locations, digests,
sizes and technical evidence. It does not discover inputs or search for extra Pack members.

## Readiness admission gate

Every command must reconstruct the complete qualification closure and accept only:

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

The Decision's Request, Instruction, Qualifier reference, policy, outcome, issue-code tuple, basis
and time must replay exactly. The PairCheck must be exactly
`READY_FOR_SEPARATE_QUALIFICATION_REVIEW` with an empty issue tuple. `REJECTED`,
`NEEDS_HUMAN_REVIEW`, a copied binding, a non-canonical file or any non-zero authority claim fails
closed.

The boundary recomputes every stable ID and canonical SHA-256. It does not trust hashes copied
from a Manifest candidate, filename, command line, environment or operator summary.

The fourteen media, fourteen provenance records and fourteen technical records form 42 distinct
Pack-record digests. All 42 must be mutually distinct and outside the contract, policy and
retained-record digest sets. The sole allowed cross-binding equality is:

```text
canonical Instruction SHA-256 == decision.qualifier_record_sha256
```

Every other digest alias is a hard failure.

The exact whole-file digest of the Manifest is checked against the complete reserved closure set:
all selected source-file digests, both policy digests, both review-content digests and the 42
Pack-record digests. This check is symmetric: it applies both to a newly created Manifest and to
an existing Manifest selected for verification.

## Explicit time policy

Inspection and finalization require a human/caller-supplied canonical UTC second:

```text
manifest_at=YYYY-MM-DDTHH:MM:SSZ
```

There is no default and no wall-clock, timezone, filesystem timestamp, environment or network
fallback. The value must satisfy:

```text
decision.decision_at <= manifest_at
```

For finite Evidence it must also satisfy the exclusive boundary:

```text
manifest_at < evidence.valid_until
```

`PERPETUAL` is the only non-timestamp Evidence validity value.

Do not apply the Request expiry as a Manifest deadline. The historical Decision must still prove:

```text
decision.decision_at < request.request_valid_until
```

but a legitimate `manifest_at` may be later than `request.request_valid_until`. The Manifest
boundary must not call `inspect-decision-ready` with the Manifest time, refresh a Request or
perform qualification again.

Verification accepts no time argument and reads no clock. It reuses the existing Manifest's
immutable `manifest_at` and proves historical validity at that instant. A later current date or
Evidence expiry does not invalidate a historically valid Manifest and does not permit a new one
after the finite deadline.

## Path admission and trust-area isolation

Every argument must be an explicit absolute ordinary local path outside every Git tree. Reject:

- relative or empty paths;
- UNC/network paths, device or extended-device namespaces and alternate data streams;
- symbolic links, junctions, mount/reparse points and any redirected lexical component;
- hard-linked or non-regular files;
- case-folded, resolved-path, physical-identity or whole-file aliases;
- mutable alias tokens `latest`, `current` or `newest`; and
- outcome-bearing basename tokens `pass`, `rejected` or `needs` for the Instruction, Decision and
  Manifest artifacts.

Linux additionally performs a bounded read of the explicit system metadata file
`/proc/self/mountinfo` so same-filesystem bind mounts are not missed by `ismount`. It does not list
a directory or discover inputs; unavailable, malformed or oversized metadata fails closed.

Every existing non-anchor directory component is checked for mount status and rejected when it is
a mount point. The platform path anchor may itself be the filesystem mount boundary; a nested
mount cannot silently cross the selected trust area.

Source files may share an approved private source parent, but that never authorizes discovery.
The Manifest output parent for finalization must already exist and must be neither equal to, an
ancestor of nor a descendant of the Pack root or any external source parent. The same rule applies
to the parent of an existing Manifest admitted for verification. The Manifest itself must not
alias any source by path, opened identity or digest.

Finalization does not create a parent directory. Prepare a genuinely independent Manifest trust
area through a separate approved procedure before invocation. An output stored below a private
aggregate root that directly contains an input may intersect that input's trust area and must be
rejected.

## Bounded canonical reads and TOCTOU

Every artifact class has a fixed compile-time byte bound that cannot be relaxed by arguments,
environment or configuration. For each selected source the implementation:

1. validates every lexical component without following redirection;
2. opens the exact ordinary local object without following links;
3. compares lexical, resolved, path and opened-handle identities;
4. reads within its fixed bound and rejects a short or extra read;
5. computes the exact whole-file SHA-256;
6. strictly parses and, for JSON contracts, requires exact canonical bytes; and
7. checks path, handle, link count, size, time and identity again.

It reconstructs the fourteen-member Pack, all cross-references, stable IDs, canonical contract
digests, retained-record hashes and both fixed policy triples. A complete capture is repeated
before success. Finalization performs another stable capture immediately before output creation
and another source-drift check after the exact created bytes have been flushed and reread.

Any replacement, relink, hard-link-count change, file-identity change, size/time drift, digest
difference or closure disagreement fails closed. No previous inspection result is cached or
trusted by finalization.

## `inspect-manifest-ready`

Inspection performs all path, byte, historical closure, positive Decision, policy, explicit-time
and finite-Evidence checks twice. The two complete captures must agree.

It must not:

- call `build_real_asset_rights_manifest_v2`;
- construct, serialize or write a Manifest;
- create a receipt, log, cache, workspace or corrected input; or
- print a Manifest ID, Decision outcome or basis, issue codes, hashes, private paths or content.

Its bounded success result is:

```text
status=READY_FOR_MANIFEST_FINALIZATION
rights_qualification_performed=true
rights_manifest_created=false
HUMAN_GATE
NOT_AUTHORIZED
execution_authorized=false
posts_allowed=0
provider_requests=0
```

Inspection approval ends with this result. It is not approval to finalize.

## `finalize-manifest`

Finalization starts from a fresh complete validation; it never consumes an inspection cache or
receipt. After stable pre-write captures, it calls the existing pure
`build_real_asset_rights_manifest_v2` exactly once with the explicit `manifest_at`.

The output path must be absent. The command opens it exclusively with create-new semantics and
never overwrites, appends, repairs, updates, swaps or normalizes an existing target. Through the
retained exact file descriptor it:

1. writes canonical UTF-8 JSON bytes;
2. flushes the exact created file;
3. rereads the same opened identity;
4. strictly parses and compares exact canonical bytes and model equality; and
5. performs the final complete source-drift check.

Only then may the Python API return the new Manifest. The CLI summary never prints its ID,
SHA-256 or path and reports:

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

The output body, Decision details, issue codes, basis, hashes and private paths are not printed.

## Rollback and quarantine

If failure occurs after output creation starts, cleanup acts only through the retained exact
created identity and first truncates or poisons that exact inode so it is not a valid Manifest.
Windows may then delete through the exact OS handle and never falls back to a pathname delete;
delete-pending is complete only after the descriptor closes successfully and the target name is
absent. POSIX never unlinks by pathname. After the exact descriptor close attempt, it retains the
guarded parent directory descriptor to prove that the target name is absent or still names the
exact invalidated inode, avoiding a
stat-to-unlink race that could delete a replacement.

Rollback may leave a zero-byte or otherwise unparseable remnant, especially on POSIX. It is not a
Manifest and must not be repaired or overwritten. A different named inode, an uninspectable target
name, or failure to confirm exact invalidation/deletion raises the quarantine-required exception
and reports:

```text
ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED
```

Immediately isolate the entire exact output trust area. Do not verify, reuse, repair, replace or
delete a path by name until a separately approved human audit establishes the exact remaining
identity. Ordinary failures report `FAILED_CLOSED`.

Every operating-system handle close result is checked. On Windows this includes the Boolean
result from `CloseHandle`; it must never be silently ignored. A close failure is fail-closed and,
after output creation may have occurred, requires quarantine unless the exact created artifact is
proven absent or irreversibly invalid.

## `verify-manifest`

Verification requires the same 28 source entries plus one explicit existing Manifest. It accepts
no `manifest_at`, `observed_at` or current-time option. It:

1. strictly loads exact canonical Manifest bytes;
2. captures and reconstructs the full historical qualification closure;
3. invokes the existing pure v2.4 closure verifier using the Manifest's recorded `manifest_at`;
4. requires exact model and canonical byte equality; and
5. repeats the complete capture and rejects any drift.

It writes nothing and does not normalize, repair, refresh, reissue or copy the Manifest. The
Python API returns the verified Manifest; the CLI summary reports `RIGHTS_MANIFEST_CREATED` but no
Manifest ID, SHA-256 or path and grants no authority.

## Failure diagnostics

Missing, extra, unsafe, ambiguous, aliased, malformed, non-canonical, expired, changed,
conflicting or unbound inputs fail closed. Diagnostics are bounded and must not include:

- private paths or source contents;
- Decision outcome, qualification basis or issue codes;
- full SHA-256 values or retained identity content;
- Manifest JSON; or
- environment, Key or Provider information.

Argument and ordinary runtime failures report `FAILED_CLOSED` and exit with code 2. Only an
unconfirmed exact-output rollback reports `ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED` and exits
with code 3. Successful commands exit with code 0.

## Compatibility and prohibited operations

This boundary adds no production contract and no Schema. All 57 existing committed Schemas remain
byte-identical. The following remain byte-compatible and unmodified:

- `CreativeSampleRealAssetRightsManifestV2` and its committed Schema;
- the v2.4 build, parse and verify APIs;
- all Pack, Evidence, Review, PairCheck, Request, Instruction and Decision contracts;
- existing trusted-local Request and Decision Finalizer public APIs; and
- entitlement, authorization and production safety registries.

V2.5 must not:

- call the v1 rights-manifest builder or v1 qualification;
- convert two Pack reviews into 28 apparent v1 per-asset records;
- modify entitlement or authorization;
- touch Runtime, Worker, Provider, PostgreSQL, Temporal, Ark, Atomic Ledger or migration;
- read a Key, use a network, upload, POST, purchase, recharge, claim a trial or start a service;
- scan or enumerate any directory, including the Pack root;
- create directories, workspaces, receipts, caches or mutable aliases; or
- read or write repository `output/` or `tmp/`.

Private sources and Manifests must never be staged, committed, pushed, uploaded or embedded in a
test fixture.

## Synthetic offline test expectations

Tests use only synthetic closures and isolated temporary directories. They cover at minimum:

- positive inspect, finalize and historical verify paths;
- proof that inspection never calls the Manifest builder and writes nothing;
- proof that finalization calls the builder exactly once and uses create-new only;
- all 28 explicit path bindings and fourteen media ordinals;
- rejection of `REJECTED`, `NEEDS_HUMAN_REVIEW`, PairCheck issues and Decision drift;
- canonical document, stable-ID, digest, policy and retained-record substitution failures;
- `decision_at <= manifest_at`, finite Evidence exclusivity, `PERPETUAL`, and a valid Manifest time
  later than Request expiry;
- historical verification with no wall clock;
- relative, UNC/device, ADS, link, junction/reparse, mount, hard-link, alias and trust-area attacks;
- bounded reads, before/after replacement and TOCTOU failures;
- existing-output refusal, exact-handle reread and safe rollback;
- forced cleanup failures and quarantine-required reporting;
- every zero-authority constant and attempted non-zero authority value;
- no v1 conversion or production dependency; and
- byte compatibility of all 57 pre-existing Schemas and existing public APIs.

Run the complete non-integration suite and repository checks. P0, P1 and P2 must all be zero before
the Draft PR can be considered for Ready status.

## Separate approvals for real operation

Merging the development PR authorizes no real private read and no real Manifest. Real use requires
three independent approvals:

1. `inspect-manifest-ready`: name all exact 28 source paths and one explicit `manifest_at`;
2. `finalize-manifest`: later name the exact closure again, one absent output path and explicit
   `manifest_at`; and
3. `verify-manifest`: later name the complete closure and exact existing Manifest path.

Each approval ends at the named command. No successful result automatically authorizes the next
command. A verified Manifest still does not authorize entitlement, generation, publication,
Runtime, Provider or POST. Any such consumer requires a separate design, policy review, approval
and PR.
