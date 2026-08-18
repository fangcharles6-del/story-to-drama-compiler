# Creative Sample qualification request preparation v2.1

This runbook describes the trusted local boundary that can inspect, create and verify one
Pack-level Human Review v2 qualification **request**. It does not perform qualification and must
not be used with real private records during this implementation stage.

## Current stage: synthetic development only

Use only synthetic fixtures created inside the offline test boundary for this PR. Do not supply
the current real private Frozen Pack, fourteen media files, rights Evidence, retained records,
Reviewer A/B records or PairCheck. Do not paste real private paths into a test, shell history,
issue, commit or PR description.

Real private operation requires a later explicit approval that identifies every input path and
the create-new destination. That later approval still authorizes only request preparation. It
does not authorize a Decision Finalizer call.

## Permanent safety state

Every request created or verified here is fixed to:

```text
status=QUALIFICATION_REQUESTED
rights_qualification_performed=false
rights_manifest_created=false
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
eligible_for_real_generation=false
execution_authorized=false
posts_allowed=0
provider_requests=0
```

`READY_FOR_SEPARATE_QUALIFICATION_REVIEW` is a zero-permission PairCheck handoff.
`QUALIFICATION_REQUESTED` is a zero-permission proposal. Neither means that rights are qualified,
that a manifest exists, or that generation, publication, Provider use, entitlement or
authorization is permitted.

## Exactly three commands

The delivery exposes only these subcommands:

| Subcommand | Filesystem effect | Meaning |
|---|---:|---|
| `inspect-ready` | None | Revalidate the exact selected closure at explicit `--requested-at`; report only `READY_FOR_REQUEST_PREPARATION`, never a request ID or request status. |
| `prepare-request` | Create exactly one new request | Repeat full validation at explicit `--requested-at` and write canonical `CreativeSampleRealAssetQualificationRequestV2` bytes to one explicit external target. |
| `verify-request` | None | Rebuild from the same exact sources and require an existing request to match exactly and be current at explicit `--observed-at`. |

The reviewed offline module launcher is:

```text
uv run --offline python -m sdc.real_asset_qualification_preparer_v21 <subcommand> <options>
```

Do not invent an alternate Python one-liner or call internal functions directly.

There is no command to finalize a decision. The interface must not accept or prompt for:

- a Qualifier identity or retained identity record;
- a Qualifier decision record;
- `decision_at`;
- `PASS_ASSET_INTAKE_ONLY`, `REJECTED` or `NEEDS_HUMAN_REVIEW`;
- `qualification_basis`; or
- qualification issue codes.

If an interface exposes any of these, stop: it is not this request-preparation boundary. Any call
to `build_real_asset_qualification_decision_v2`, directly or indirectly, is a real qualification
operation and requires separate approval.

## Inputs the operator must name

Every path is supplied separately as an absolute, ordinary local path. The command does not scan
a folder to discover candidates, expand a wildcard, choose the newest candidate, follow `latest`,
infer a filename or repair a missing selection.

There is one narrow verification-only enumeration: the existing Frozen Pack verifier walks the
explicitly supplied `--pack-root` to require its filesystem tree to contain exactly
`asset-pack.json` and the fourteen manifest-bound objects and to reproduce their technical
evidence. An extra entry causes failure; it is never selected or consumed as an alternate input.
This does not replace the fourteen required, ordered, absolute `--media-path` occurrences, which
are read and rebound independently. No other source directory is enumerated.

The final tested command interface must map explicit options to this closure:

| Input role / option | Count | Required binding |
|---|---:|---|
| Frozen Pack root / `--pack-root` | 1 | Existing absolute directory containing only the exact selected frozen Pack boundary; no discovery of another Pack root. |
| Frozen Pack manifest / `--pack-manifest` | 1 | Admitted path is exactly `<pack-root>/asset-pack.json`; strict `CreativeSampleFrozenRealAssetPackManifest`, stable Pack ID and canonical SHA-256. |
| Frozen media object / repeated `--media-path` | 14 | Exactly fourteen occurrences in canonical ordinal order; every path equals `<pack-root>/<object_path>` and its size and SHA-256 match the descriptor. |
| Rights Evidence contract / `--evidence` | 1 | Strict `CreativeSampleRealAssetRightsEvidenceBundleV2`; exact Pack and fourteen-binding closure. |
| Reviewer A contract / `--reviewer-a` | 1 | Strict finalized `CreativeSampleRealAssetHumanPackReviewV2` with role `REVIEWER_A`. |
| Reviewer B contract / `--reviewer-b` | 1 | Strict finalized `CreativeSampleRealAssetHumanPackReviewV2` with role `REVIEWER_B`. |
| PairCheck contract / `--pair-check` | 1 | Strict `CreativeSampleRealAssetReviewPairCheckV2` over the exact A/B contracts. |
| Retained Evidence record / `--evidence-retained-record` | 1 | File SHA-256 equals `evidence_record_sha256`. |
| Evidence Preparer reference / `--evidence-preparer-ref` | 1 | File SHA-256 becomes `evidence_preparer_ref_sha256` and is independent of Evidence and A/B records. |
| Reviewer A retained reference / `--reviewer-a-retained-record` | 1 | File SHA-256 equals Reviewer A `reviewer_ref_sha256`. |
| Reviewer B retained reference / `--reviewer-b-retained-record` | 1 | File SHA-256 equals Reviewer B `reviewer_ref_sha256`. |
| Existing request / `--request` (`verify-request` only) | 1 | Strict `CreativeSampleRealAssetQualificationRequestV2` to rebuild and compare. |
| New request target / `--output` (`prepare-request` only) | 1 | Explicit absent repository-external `.json` filename; create-new only. |
| Request audit anchor / `--requested-at` (`inspect-ready`, `prepare-request`) | 1 value | Caller-supplied canonical whole-second UTC `YYYY-MM-DDTHH:MM:SSZ`; no default or clock read. |
| Verification audit anchor / `--observed-at` (`verify-request` only) | 1 value | Caller-supplied canonical whole-second UTC used to reject a future or expired request; no default or clock read. |

The four rows named “retained ... record” are the complete request-stage private-record set. The
`review_record_sha256` inside each review contract is a canonical content digest derived under the
existing v2 review-record domain; it is not a fifth or sixth retained file path. Do not try to
locate a file by that digest.

The fourteen media selections are fourteen ordered repetitions of the final `--media-path`
option. Their command-line order must match manifest ordinals `0..13`; each remains individually
auditable. A repeated path, byte identity or case-insensitive alias cannot satisfy two roles.

The program never reads the wall clock. `--requested-at` and `--observed-at` are explicit audit
anchors supplied by the caller in canonical UTC seconds. They have no default and cannot be
inferred from a file, environment variable, local timezone or filesystem timestamp. The operator
must obtain and record the appropriate trusted UTC value under the separately approved procedure;
the preparer only validates and binds it.

The exact common option skeleton below is documentation only during this synthetic-development
stage. Angle-bracketed values mean individually supplied absolute paths; they are not literal
shell values and must never be replaced by a wildcard:

```text
--pack-root <absolute-pack-root>
--pack-manifest <absolute-pack-root>/asset-pack.json
--media-path <absolute-media-ordinal-00>
...repeat --media-path once for each ordinal through 13...
--evidence <absolute-evidence-contract>
--reviewer-a <absolute-reviewer-a-contract>
--reviewer-b <absolute-reviewer-b-contract>
--pair-check <absolute-pair-check-contract>
--evidence-retained-record <absolute-evidence-record>
--evidence-preparer-ref <absolute-preparer-reference-record>
--reviewer-a-retained-record <absolute-reviewer-a-reference-record>
--reviewer-b-retained-record <absolute-reviewer-b-reference-record>
```

Append exactly `--requested-at <YYYY-MM-DDTHH:MM:SSZ>` for `inspect-ready`; append exactly
`--requested-at <YYYY-MM-DDTHH:MM:SSZ> --output <absolute-new-request.json>` for
`prepare-request`; or append exactly
`--observed-at <YYYY-MM-DDTHH:MM:SSZ> --request <absolute-existing-request.json>` for
`verify-request`. These operation-specific options must not be exchanged or omitted.

## Path admission checks

Before reading any content, the command applies the same path policy to every selected source and
to the destination:

1. require a fully qualified local path;
2. reject a relative, UNC/network, device, extended-device or alternate-data-stream path;
3. inspect every lexical component without following a symbolic link, junction, mount or reparse
   point;
4. require an ordinary regular file for every source;
5. reject hard links, path aliases and duplicate file identities;
6. reject any source or destination inside the Git repository, including repository `output/`
   and `tmp/`;
7. for both a new `--output` and an existing `--request`, require its direct parent to be neither
   equal to, an ancestor of nor a descendant of the Pack root or any of the eight external-input
   direct parents; and
8. require the `prepare-request` target not to exist and require either Request file not to alias
   any source.

Explicit source files may share the intended private source directory. That is not permission to
enumerate the directory or consume unlisted siblings.

Pre-create one independent sibling Request trust area before invoking `prepare-request`; the
command does not create directories. Reuse that same non-intersecting area when selecting the
existing `--request` for `verify-request`. The eight external-input parents used in this comparison
are the direct parents of Evidence, Reviewer A, Reviewer B, PairCheck, Evidence retained record,
Evidence Preparer reference, Reviewer A retained reference and Reviewer B retained reference.
Source parents may equal one another; only the Request trust area must remain separate from every
one of them and from the Pack root.

For example, sibling `source-records` and `request-output` directories under an approved private
container can pass when all eight external files are below `source-records` and the Pack root is a
different sibling. By contrast, if even one of the eight files is stored directly in the private
container root, `private-container/request-output` is a descendant of that file's direct parent
and is rejected. In that layout, use a Request directory outside the aggregate root as its sibling,
or reorganize the inputs under a separate sibling source area through an independently approved
local operation. Do not move or rewrite private inputs merely as an unreviewed workaround.

Do not move private files into the repository to make a path pass. Correct the invocation or stop.

## Bounded reads and drift protection

The implementation owns these fixed maximum byte counts:

| Artifact class | Maximum bytes per explicitly selected file |
|---|---:|
| Canonical JSON contract or request | 1,048,576 |
| Retained private record | 67,108,864 |
| Frozen media object | 67,108,864 |

The limits are not configurable by environment variable, user config or command-line flag. A file
at or below its applicable bound must still satisfy every expected size and digest; a file beyond
the bound fails before parsing or use.

For every selected source the command:

1. records the admitted lexical and file identity state;
2. opens the exact ordinary local file without following a redirection;
3. compares the opened handle with the admitted path;
4. reads no more than the fixed limit and detects extra bytes;
5. computes SHA-256 from the bytes actually read;
6. rechecks the opened file and path identity after the read; and
7. repeats a complete closure drift check before success or output creation.

Any missing byte, extra byte, replacement, relink, hard-link count change, size/time/identity
change, hash mismatch or path redirection is a hard failure. Do not retry by automatically
selecting another file. A human must review the cause and start a new invocation with explicit
paths.

JSON parsing rejects duplicate and unknown fields. The command recomputes stable IDs, canonical
document SHA-256 values, all fourteen ordered bindings, record digests, roles, policy identity and
cross-references. A filename or a digest copied into another JSON field is not proof that its file
was read.

## Readiness requirements

All of the following must hold before `inspect-ready` succeeds or `prepare-request` creates a
request:

- the Frozen Pack contains exactly fourteen canonical, distinct members;
- every selected media file matches its exact descriptor size and SHA-256;
- Evidence, Reviewer A, Reviewer B and PairCheck strictly bind that same Pack closure;
- the two reviews are complete, independently identified, role-correct and approved under their
  existing v2 contract rules;
- all selected retained-record SHA-256 values match their committed fields and satisfy the
  existing non-aliasing rules;
- PairCheck status equals exactly `READY_FOR_SEPARATE_QUALIFICATION_REVIEW`;
- PairCheck `issue_codes` is exactly empty;
- every stable ID and canonical document SHA-256 is reproducible;
- the fixed ADR-021 qualification-policy ID, version and document SHA-256 are unchanged;
- the explicit `--requested-at` is not before PairCheck evaluation and is before finite Evidence
  expiry; and
- every request state field remains at the zero-authority constants above.

The fixed request deadline remains
`min(evidence.valid_until, requested_at + 24 hours)` for finite Evidence and
`requested_at + 24 hours` for `PERPETUAL` Evidence. The upper boundary is exclusive for a later
decision. Readiness does not promise that a later independent Qualifier will decide positively.

## `inspect-ready`

Use `inspect-ready` first in a later approved real operation. Provide the complete explicit source
closure and one explicit audited `--requested-at`. The command performs the same validation that
`prepare-request` would perform, including in-memory request derivation, but discards that
candidate and does not create or expose a request.

Success prints only a bounded non-secret summary whose status is
`READY_FOR_REQUEST_PREPARATION`. It must not print a request ID, a request body or
`QUALIFICATION_REQUESTED`; those would misleadingly represent inspection as request creation. It
must not write a file, cache, receipt, generated index, corrected record or log. Failure must
identify a safe error class without dumping private record bodies or absolute private paths into
persistent output.

Do not interpret a successful inspection as qualification or authorization. It says only that the
selected bytes can form a zero-authority request at the supplied time.

## `prepare-request`

After a successful inspection and within the same separately approved local-operation scope,
invoke `prepare-request` with the complete explicit source closure and one explicit absent
destination. Supply an intentionally audited canonical `--requested-at`; the program never
generates or defaults it. Reusing an earlier inspection anchor is an explicit operator choice, not
an automatic continuation.

The command must re-read and revalidate every source; it must not reuse an unauthenticated cache
from `inspect-ready`. It calls only `build_real_asset_qualification_request_v2` and writes its
canonical UTF-8 JSON document. Creation is exclusive:

- an existing target is a hard stop;
- no overwrite, append, truncate, merge, repair or in-place normalization is allowed;
- no `latest`, `current`, `newest`, shortcut, pointer or mutable alias is created, and an output
  stem containing one of those mutable-alias tokens is rejected;
- a failure cannot publish partial bytes as a completed Request; and
- rollback operates only on the exact open inode exclusively created by that invocation and never
  uses a path-only delete that could remove a replacement.

### Failure cleanup boundary

The create path keeps the exact file descriptor and its guarded parent open until the Request has
passed byte, contract, digest and post-source checks. On any later failure, rollback first
invalidates that exact inode through the retained descriptor, then attempts deletion:

- on Windows it requests deletion through the exact open OS handle and never falls back to
  deleting the pathname;
- on POSIX it compares the pathname under the guarded parent `dirfd` with the open inode and
  unlinks only that match; a replacement inode is left untouched; and
- normal tested write, flush, parse and post-create failures leave no target.

If the operating system refuses the final delete operation after exact-inode invalidation was
verified, this invocation's inode may remain as a zero-byte or otherwise unparseable fail-closed
remnant. It is not a `CreativeSampleRealAssetQualificationRequestV2`, the command returns failure,
and it must not be passed to `verify-request`, renamed as a Request, automatically repaired or
overwritten.

If neither exact-inode invalidation nor safe deletion can be confirmed, the command explicitly
reports `rollback failed closed`. In that exceptional branch, make no claim about remaining bytes:
quarantine the entire Request trust area, do not select any file from it, and arrange a separately
approved human audit and cleanup. The tool still never path-deletes a different replacement.

Record the new target path and its SHA-256 outside Git according to the separately approved local
procedure. Do not stage, commit, push, upload or paste the private request.

## `verify-request`

Provide the same complete source closure plus the exact existing request path. The command parses
the request strictly, preserves its immutable request time, re-reads every source, rebuilds the
request and requires byte-for-byte canonical equivalence. Supply an explicit canonical
`--observed-at`; the command requires `requested_at <= observed_at < request_valid_until` and does
not consult a clock.

Verification must fail on any difference in bytes, request ID, source digest, policy triple, time,
expiry or zero-authority state. It never fixes or rewrites the request and creates no verification
receipt. A failed or expired request is retained unchanged for audit; a corrected closure produces
a separately created request under a separately approved operation.

## Stop conditions

Stop with no request output on any:

- missing, extra, malformed, oversized, expired, future-dated or changed input;
- non-absolute, network/device, linked, reparsed, hard-linked, aliased or intersecting path;
- unknown or duplicate JSON field;
- stable-ID, byte count, SHA-256, role, ordinal, record or cross-reference mismatch;
- PairCheck state other than exact issue-free
  `READY_FOR_SEPARATE_QUALIFICATION_REVIEW`;
- destination that exists or cannot be exclusively created;
- TOCTOU or rollback identity uncertainty;
- nonzero execution, publication or Provider state;
- request to infer, preselect or finalize a qualification decision;
- request to create a rights manifest or translate the two Pack reviews into 28 v1 records; or
- attempt to read or write repository `output/`, `tmp/`, a registry, Ledger or migration.

Never use an override, waiver, repair or “best effort” mode to continue.

## Prohibited operations

This stage must not:

- call or expose the qualification Decision Finalizer;
- perform a real qualification or generate a rights manifest;
- modify entitlement or authorization state;
- start Runtime, Worker, Provider, PostgreSQL or Temporal;
- access Ark or another console;
- read an API Key;
- use a network, upload, POST or Provider request;
- purchase, recharge or claim a trial;
- write an Atomic Ledger entry or migration;
- convert two v2 Pack reviews into 28 fictitious v1 reviews; or
- read or modify repository `output/` or `tmp/`.

All 55 existing committed Schemas, existing contracts and the ADR-021 Finalizer Python API remain
byte-compatible. This stage adds no Schema and grants no execution authority.

## Offline development verification

The implementation PR uses synthetic temporary fixtures only. Its offline tests must cover at
least:

- exact explicit-path closure and rejection of scanning, globbing or mutable aliases;
- repository-external path enforcement and rejection of UNC/device paths, links, junctions,
  reparse points, hard links, alternate data streams and intersecting trust areas;
- fixed read limits and oversize failures for every artifact class;
- fourteen individually selected media bindings and all retained-record hashes;
- duplicate/unknown JSON fields and canonical stable-ID/SHA-256 reconstruction;
- pre-read, opened-handle, post-read and pre-output TOCTOU failures;
- exact issue-free `READY_FOR_SEPARATE_QUALIFICATION_REVIEW` enforcement;
- required canonical `--requested-at` and `--observed-at`, absence of clock/default behavior,
  finite/PERPETUAL expiry and 24-hour request deadline behavior;
- exclusive create-new output, existing-target refusal and safe failure cleanup;
- exact request reconstruction by `verify-request` with zero filesystem changes;
- absence of Decision Finalizer inputs, imports and calls;
- absence of Runtime, Provider, Ark, database, Ledger, migration, entitlement and authorization
  dependencies; and
- byte identity of all 55 pre-existing Schemas and compatibility of existing contracts and public
  Finalizer API.

Run only the repository's non-integration offline checks. Do not start services or contact paid or
remote generation systems to test this boundary. Complete a P0/P1/P2 review before opening the
independent Draft PR.

## Later stages remain separate

After this PR is reviewed and merged, a user may separately approve an exact real-path
`inspect-ready`, `prepare-request` and `verify-request` operation. That approval must not be
silently extended to a Decision call.

A real qualification invocation is a separate stage because it accepts a fourth human role and
records an actual decision. A future rights-manifest consumer is another stage with its own ADR,
contracts, policy and PR. Any authorization or entitlement bridge is later still. No stage may
infer its approval from the successful completion of this request-preparation runbook.
