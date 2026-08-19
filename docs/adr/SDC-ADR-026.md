# SDC-ADR-026: Trusted local finalization of Pack-level rights manifests v2.5

- **Status:** Proposed
- **Date:** 2026-08-19
- **Version:** V01

## Context

SDC-ADR-025 added the immutable
`CreativeSampleRealAssetRightsManifestV2` contract and a pure in-memory v2.4 consumer. That
consumer can build, parse and verify one deterministic Manifest from an exact positive Pack-level
Human Review v2 closure. It deliberately opens no file, accepts no path, writes no artifact and
uses only synthetic offline fixtures during development.

The next useful boundary is narrower than authorization. An operator needs a deterministic local
way to establish that one exact, explicitly selected, repository-external closure is ready for
Manifest finalization, create at most one canonical Manifest file, and historically verify an
existing Manifest. A copied digest, filename or already-positive Decision is insufficient. Every
private byte source must be reopened, strictly parsed, bounded, hashed and rebound to the complete
closure under the trusted-local path and TOCTOU rules established by SDC-ADR-022 and SDC-ADR-023.

Creating a v2 Manifest records `rights_manifest_created=true`, but it does not grant legal
sufficiency, entitlement, authorization, generation, publication, Runtime or Provider authority.
The boundary must not become an authorization bridge merely because it writes a file called a
rights manifest.

## Decision

Add one trusted local Rights Manifest finalization boundary with exactly three operator-facing
subcommands:

- `inspect-manifest-ready` performs the complete read-only readiness check, writes nothing and
  must not call `build_real_asset_rights_manifest_v2`;
- `finalize-manifest` repeats the complete check, calls the existing pure v2.4 builder exactly
  once, and creates exactly one new canonical `CreativeSampleRealAssetRightsManifestV2`; and
- `verify-manifest` reopens the full bound closure, historically reconstructs one explicitly
  selected existing Manifest and requires exact canonical equivalence, with zero writes and no
  clock read.

The package launcher and every option spelling must match the reviewed implementation and its
generated `--help`. The three command names and their semantic separation are normative. There is
no fourth command, hidden automatic continuation, interactive prompt, waiver, `--force`, repair,
overwrite, entitlement or authorization mode.
Long-option abbreviations and repeated singleton options are rejected; only the fourteen
separately required `--media-path` occurrences use a repeatable option.

The Python module is:

```text
sdc.real_asset_rights_manifest_finalizer_v25
```

Its public path envelope and operations are:

```text
TrustedLocalRightsManifestPaths(
    decision_inputs: TrustedLocalDecisionPaths,
    decision: Path,
)

inspect_manifest_ready(paths, *, manifest_at) -> Literal["READY_FOR_MANIFEST_FINALIZATION"]
finalize_manifest(paths, output_path, *, manifest_at) -> CreativeSampleRealAssetRightsManifestV2
verify_manifest(paths, manifest_path) -> CreativeSampleRealAssetRightsManifestV2
```

The public failure hierarchy is
`TrustedLocalRightsManifestFinalizationError` with the dedicated
`TrustedLocalRightsManifestQuarantineRequired` subclass. The module also exports `main` for the
exact CLI. Ordinary failure and quarantine remain distinguishable without disclosing private
inputs.

Inspection returns only the fixed non-secret readiness literal after internally verifying the
existing Decision. It does not return that Decision, construct a candidate Manifest or expose any
source content. Finalization is the only v2.5 operation that may create new Manifest bytes.

This development PR is **synthetic-only**. Tests and examples use only isolated synthetic local
fixtures. They must not read or invoke the current real private Pack, media, Evidence, Reviews,
PairCheck, retained records, Request, Qualifier reference, Instruction, Decision or Manifest. Any
real invocation is a later operation requiring a new explicit approval and an exact path list.
Approval to inspect does not approve finalization; approval to finalize does not approve later
verification.

## Exact 28-path source closure

Every source is named by an individual absolute local path. The finalizer never scans a directory
for candidates, expands a glob, chooses the newest file, follows a mutable alias, consults a
`latest` pointer or infers a missing sibling. The complete source closure has exactly 28 path
entries:

1. the explicitly selected Frozen Pack root;
2. its separate Pack Manifest path, which must be exactly `<pack-root>/asset-pack.json`;
3. through 16. all fourteen media objects, separately supplied in canonical ordinal order and
   exactly rebound to their manifest descriptors;
17. the Pack-level Rights Evidence Bundle;
18. Reviewer A's finalized Pack-review contract;
19. Reviewer B's finalized Pack-review contract;
20. their exact ready, issue-free PairCheck;
21. the retained Evidence record;
22. the retained Evidence Preparer reference;
23. Reviewer A's retained reference;
24. Reviewer B's retained reference;
25. the exact canonical Qualification Request;
26. the retained Qualifier reference;
27. the exact canonical v2.2 Qualification Decision Instruction; and
28. the exact canonical Qualification Decision.

`verify-manifest` additionally requires one explicit existing Manifest path.
`finalize-manifest` additionally requires one explicit absent output path. Neither extra path is a
source-path replacement or a discoverable candidate.

The v2 Review contracts' `review_record_sha256` values are canonical review-content digests. They
do not name two extra retained files. The v2.2 Instruction is itself the retained Qualifier
decision record; its complete canonical file SHA-256 must equal the Decision's
`qualifier_record_sha256`. The implementation must not discover, invent or request three
additional record files for those bindings.

The boundary does not enumerate the selected Frozen Pack root. It verifies only the explicitly
named `asset-pack.json` and the fourteen separately required media paths, in manifest ordinal
order, including their object locations, digests, sizes and reproduced technical evidence. It
does not discover inputs or search for extra members, and no directory may be enumerated.

## Positive admission and exact transitive binding

Every command strictly revalidates and historically reconstructs the complete v2 closure. The
Decision must be the exact canonical positive Decision bound to the Request and Instruction and
must retain:

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

`REJECTED`, `NEEDS_HUMAN_REVIEW`, an unready PairCheck, a non-empty PairCheck issue tuple, an
expired finite Evidence boundary at the proposed Manifest time, any drifted path, byte, digest,
stable ID, policy, role, ordinal, record binding or non-zero authority fact is a hard failure.
V2.5 does not reinterpret the Qualifier's outcome or basis, infer a waiver or determine legal
sufficiency.

The boundary recomputes the canonical SHA-256 and stable identity of the Pack Manifest, Evidence,
Reviewer A, Reviewer B, PairCheck, Request, Instruction and Decision. It reopens and hashes the
five independently retained files: Evidence record, Evidence Preparer reference, Reviewer A
reference, Reviewer B reference and Qualifier reference. It also proves the Instruction's exact
whole-file binding as the Qualifier decision record and preserves the two canonical review-content
digests without treating them as file paths.

The fourteen media, fourteen provenance records and fourteen technical records contribute exactly
42 Pack-record digests. They must be fully distinct and must not alias a contract, policy or
retained-record digest. The only permitted equality across the complete Manifest closure is the
intentional identity between the canonical Instruction SHA-256 and the Decision's retained
`qualifier_record_sha256`; every other digest alias fails closed.

The whole-file digest of either a newly created or an existing Manifest must also be outside the
same reserved closure set: all explicitly selected source-file digests, both policy digests, both
review-content digests and all 42 Pack-record digests. Finalization and historical verification
apply this rule symmetrically; an existing Manifest is not trusted merely because its model
fields reconstruct correctly.

Every fixed v2.0 qualification-policy component and v2.4 Manifest-policy component is rebuilt and
matched. Copied IDs or SHA-256 strings are never accepted in place of the exact selected bytes.

## Explicit Manifest time

`inspect-manifest-ready` and `finalize-manifest` each require one caller-supplied `manifest_at` in
canonical whole-second UTC form:

```text
YYYY-MM-DDTHH:MM:SSZ
```

There is no default and no wall-clock, local-timezone, filesystem-time, environment or network
fallback. Both commands enforce:

```text
decision.decision_at <= manifest_at
```

For finite Evidence, they additionally require:

```text
manifest_at < evidence.valid_until
```

The finite Request deadline proved whether the historical Decision was timely. It is not a new
Manifest deadline. V2.5 must not pass `manifest_at` to `inspect-decision-ready`, refresh the
Request, reopen qualification or reject a Manifest merely because
`manifest_at >= request.request_valid_until`. The original Request and Decision are still
reconstructed under their historical rules, including
`decision.decision_at < request.request_valid_until`.

`verify-manifest` accepts no `manifest_at` or observation time and reads no clock. It reuses the
existing Manifest's immutable `manifest_at` and verifies that the artifact was valid at that
recorded instant. Historical verification after a later Evidence expiry does not make expired
Evidence current and does not authorize creating a new Manifest at or after the finite deadline.

## Local path and byte boundary

Every source and Manifest path must be outside every Git tree. Only fully qualified, ordinary
local paths are admitted. Relative or empty paths, UNC/network paths, device and extended-device
namespaces, alternate data streams, symbolic links, junctions, mount/reparse points, hard-linked
files, non-regular files, case-folded aliases and physical aliases are rejected. Every existing
lexical component is inspected without following redirection, and lexical, resolved, path and
opened-handle identities must agree. A mount at any existing non-anchor directory component is a
hard failure; only the platform path anchor itself may be a mount boundary.
On Linux, a bounded read of the explicit system metadata file `/proc/self/mountinfo` supplements
`ismount` so same-filesystem bind mounts are also rejected; this is not input discovery or a
directory scan, and any unavailable, malformed or oversized metadata fails closed.

Source files may share an intended private source directory, but that sharing does not authorize
discovery or traversal. The selected Request and Decision must continue to satisfy their existing
trusted-local source-area rules. The direct parent of a new Manifest output, or of an existing
Manifest selected for verification, must already exist and must be neither equal to, an ancestor
of nor a descendant of the Frozen Pack root or the direct parent of any external source. The
Manifest path must not alias any source by lexical path, resolved path, opened-file identity or
whole-file digest.

The new output and existing Manifest basename must be neutral. Mutable tokens `latest`, `current`
and `newest`, and outcome-bearing tokens `pass`, `rejected` and `needs`, are forbidden. An absent
output parent is a hard failure; the command creates no directory, workspace, receipt, cache,
temporary authority artifact or pointer.

Every read is bounded by fixed implementation limits. The boundary admits each path, opens the
exact non-linked object without following redirection, compares path and opened-handle identities,
reads only within its bound, hashes the bytes, and checks identity again. JSON contracts must be
strict canonical UTF-8 bytes with no duplicate, unknown, missing or defaulted fields. Media bytes
must match all fourteen Manifest SHA-256 and size bindings.

The complete source closure is captured more than once. Any replacement, relink, hard-link-count
change, short or extra read, size/time/file-identity change or digest difference is a TOCTOU
failure. No command emits a successful result from a partially stable closure.

## Command semantics

`inspect-manifest-ready` performs all path, byte, canonical-document, closure, positive-gate,
policy and time checks twice and requires the captures to agree. It must not call
`build_real_asset_rights_manifest_v2`, construct a Manifest model or write a file. Its only
operator success status is:

```text
READY_FOR_MANIFEST_FINALIZATION
```

That success retains `rights_manifest_created=false` because no Manifest exists. It must not print
a Manifest ID, Decision outcome or basis, issue codes, SHA-256, private path or source content.

`finalize-manifest` repeats the complete validation rather than reusing prior inspection state.
Only after stable pre-write captures may it call `build_real_asset_rights_manifest_v2` exactly
once. It writes the returned model as exact canonical bytes to one explicit absent output using
exclusive create-new semantics. It must retain the exact created descriptor through write, flush,
reread, strict parse, canonical byte comparison and final source-drift verification. A successful
Python call returns the new Manifest, while the bounded CLI summary reports no ID, SHA-256 or path
and has status:

```text
RIGHTS_MANIFEST_CREATED
```

It must not print the Manifest body, Decision details, record hashes, source paths or private
contents.

`verify-manifest` strictly loads one explicitly selected existing canonical Manifest, reopens the
complete source closure, invokes the existing pure v2.4 historical verifier and requires exact
canonical byte equivalence. It does not repair, normalize, rewrite, refresh or reissue the
Manifest. It creates no receipt, consults no current time and prints no Manifest ID, SHA-256 or
path.

All argument and runtime failures use bounded, non-secret diagnostics and fail closed on missing,
extra, ambiguous, aliased, malformed, expired, changed, conflicting or unbound input.

## Create-new rollback and quarantine

There is no overwrite, append, truncate-existing, repair, rename-as-latest, backup-as-authority or
automatic retry. If finalization fails after output creation begins, rollback retains the exact
created file descriptor and first makes that exact inode unparseable. Windows cleanup may then
delete through the exact OS handle and never uses a pathname fallback; delete-pending counts as
complete only after the exact descriptor closes successfully and the target name is absent.
POSIX deliberately performs no pathname unlink: after the exact descriptor close attempt and
while retaining the guarded parent directory descriptor, it proves that the target name is absent
or still refers to the exact invalidated inode. This
avoids a stat-to-unlink race that could delete a replacement.

Rollback may therefore leave a zero-byte or otherwise unparseable fail-closed remnant, especially
on POSIX. It is not a Manifest and must not be repaired or overwritten. A different named inode,
an uninspectable target name, or failure to confirm exact invalidation/deletion requires the
dedicated quarantine exception and report:

```text
ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED
```

The entire exact Manifest output trust area must then be isolated. Nothing in it may be verified,
reused, repaired, overwritten or treated as authority until a separately approved human audit
resolves the incident. Ordinary failures report `FAILED_CLOSED`.

Every operating-system handle close is itself checked. In particular, Windows `CloseHandle`
return values must not be ignored. A close failure fails closed and, once an output may exist,
must enter quarantine unless the implementation can still prove that no valid created Manifest
remains.

## Zero-authority Manifest

A successfully finalized or verified Manifest truthfully records:

```text
status=RIGHTS_MANIFEST_CREATED
rights_qualification_performed=true
rights_manifest_created=true
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

The first two Boolean facts record that the scoped qualification and Manifest compiler ran. They
are not an entitlement, authorization, publication approval, legal opinion, Provider credential,
generation capability or Runtime route. No v2.5 command may map them to any such state.

## Immutable compatibility and prohibited dependencies

V2.5 adds no versioned production contract and no Schema. All 57 committed Schemas that predate
this boundary must remain byte-identical. The v2.4 Manifest contract, its build/parse/verify Python
API, all Request, Instruction and Decision contracts and Finalizer APIs, serialization behavior,
entitlement and authorization registries and production safety boundaries must remain
byte-compatible.

The boundary must not import or call the v1 `build_real_asset_rights_manifest`, v1 qualification
or any conversion path. It must not synthesize, clone, split or imply 28 v1 per-asset review
records from two Pack-level reviews.

It must not modify entitlement or authorization; touch Runtime, Worker, Provider, PostgreSQL,
Temporal, Ark, Atomic Ledger or migration code; read a Key; use a network; upload; POST; purchase;
recharge; claim a trial; or start a service. It must not read or modify repository `output/` or
`tmp/`. Private artifacts must never be copied, staged, committed, pushed, uploaded or embedded in
a fixture.

## Development and operational separation

This implementation PR exercises the trusted-local boundary only with synthetic files in isolated
test directories. It must not read, inspect, hash or invoke any current real private source or
Manifest. Passing tests establishes the behavior of the boundary, not the readiness of a real
closure.

After merge, three real operations remain independently gated:

1. real `inspect-manifest-ready` requires a new explicit approval naming the exact 28 source
   paths and `manifest_at`;
2. real `finalize-manifest` requires a later explicit approval naming the same complete closure,
   one absent output and `manifest_at`; and
3. real `verify-manifest` requires another explicit approval naming the complete closure and the
   exact existing Manifest.

No approval flows automatically from one command to the next. Even after a real Manifest is
verified, any entitlement, authorization, generation, publication or Provider consumer remains a
separate future design, policy review, approval and PR.

## Consequences

The project gains a narrow, reproducible bridge from one exact positive private Decision closure
to one canonical zero-authority Manifest without weakening the pure v2.4 compiler. Readiness can
be checked without creating a Manifest, finalization is one create-new act, and historical
verification uses immutable time rather than a wall clock.

The cost is deliberate operational ceremony: 28 source entries are explicit, every byte identity
is re-established, the Manifest trust area is independent and each real command needs its own
approval. That friction prevents a convenient local writer from becoming an implicit discovery,
qualification or authorization engine.
