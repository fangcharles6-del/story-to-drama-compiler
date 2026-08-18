# SDC-ADR-022: Trusted local preparation of Pack-level qualification requests v2.1

- **Status:** Proposed
- **Date:** 2026-08-18
- **Version:** V01

## Context

SDC-ADR-021 introduced an append-only Pack-level Human Review v2 qualification request and
decision contract plus a pure, in-memory compiler. That delivery deliberately had no operational
file boundary. It never opened the real Frozen Pack, evidence, retained records, reviews or
PairCheck, and it did not provide a CLI that could safely move private records from an external
workspace into the pure request builder.

The next useful boundary is narrower than qualification. An operator needs a deterministic local
way to establish that one exact, explicitly selected, repository-external closure is ready to be
presented to a later Qualifier and to create or verify the corresponding zero-authority
`CreativeSampleRealAssetQualificationRequestV2`. This cannot be implemented by directory
discovery or by trusting filenames and copied SHA-256 values. Every selected private byte source
must be re-opened under a fail-closed local path policy, read within a fixed bound, hashed and
matched to the transitive contract closure.

Creating that request is not a rights qualification. In particular, accepting a Qualifier's
identity, decision, basis, decision record or time and invoking the ADR-021 Decision Finalizer
would perform a real qualification. That is outside this stage even if the resulting decision
would still carry zero Runtime authority.

## Decision

Add one trusted, local request-preparation boundary with exactly three operator-facing
subcommands:

- `inspect-ready` performs the complete readiness check and makes no filesystem change;
- `prepare-request` performs the same check and creates exactly one new canonical
  `CreativeSampleRealAssetQualificationRequestV2`; and
- `verify-request` performs the same check, reconstructs the request from its bound sources and
  requires byte-for-byte equivalence with one explicitly selected existing request, without
  changing it.

The package launcher and final option spellings must match the reviewed implementation and its
generated `--help`; this ADR does not invent a second Python API or alternate command spelling.
The three subcommand names and their semantic boundaries are normative.

No subcommand imports, calls, wraps or indirectly exposes the ADR-021 Decision Finalizer. No
command accepts a Qualifier reference, Qualifier decision record, `decision_at`, decision,
qualification basis or qualification issue code. There is no hidden decision mode, interactive
prompt, waiver, repair, `--force` or automatic continuation. A later real Decision invocation
requires a separate approval, security review and delivery.

## Explicit input closure

The caller must provide a separate, absolute local path for every required input. The trusted
boundary never scans a directory to discover candidates, expands a glob, selects a newest file,
follows a mutable alias, consults a `latest` pointer or infers a missing path from a sibling
filename. The only directory enumeration is the existing bounded exact-tree verification of the
caller-selected `--pack-root`: it rejects extra Frozen Pack members and reproduces the fourteen
technical evidence records, but it never adopts an enumerated path as an input. All fourteen media
paths remain separately required and are rebound to manifest order after that verification. The
exact closure includes:

1. the Frozen Pack manifest through explicit `--pack-manifest`, whose admitted path must be
   exactly `<pack-root>/asset-pack.json`;
2. all fourteen media objects, in the manifest's canonical ordinal binding;
3. the Pack-level rights Evidence contract;
4. Reviewer A's finalized Pack-review contract;
5. Reviewer B's finalized Pack-review contract;
6. the exact review PairCheck;
7. the retained Evidence record;
8. the Evidence Preparer reference record;
9. Reviewer A's retained reference record; and
10. Reviewer B's retained reference record.

Those four retained records are the complete request-stage private-record set: Evidence record,
Evidence Preparer reference, Reviewer A reference and Reviewer B reference. The v2 review
contracts' `review_record_sha256` fields are canonical review-content digests and do not name two
additional files. Treating them as discoverable filenames would change existing contract
semantics and is forbidden.

The implementation may require further explicit record paths only where they are necessary to
prove a digest already committed by that closure. Such paths must be named individually in the
reviewed command interface; they must never be discovered. The final runbook input table and
option spelling must be kept aligned with the implementation tests before this ADR is accepted.
Qualifier identity and decision-stage records are categorically not request-stage inputs.

`inspect-ready` and `prepare-request` each require one explicit `--requested-at` in canonical
whole-second UTC form. `verify-request` retains the immutable `requested_at` in the selected
request and requires one explicit `--observed-at` in the same form to reject a request from the
future or one at or beyond its exclusive expiry. These values are caller-supplied audit anchors,
not timestamps generated by the program. There is no default, clock read, environment fallback or
automatic “now”. The resulting 24-hour maximum request lifetime and evidence-expiry rules remain
exactly those of ADR-021.

## Local path and byte trust boundary

Every private input and output must be outside the Git repository. A path is admissible only when
it is a fully qualified, ordinary local path selected by the caller. The boundary rejects relative
paths, empty paths, network/UNC paths, device or extended-device namespaces, alternate data
streams, symbolic links, junctions, mount/reparse points, hard-linked files, non-regular files and
case-folded aliases. It inspects every existing lexical component without following a redirection
and compares lexical and resolved identities.

Repository, source and Request trust areas must not intersect in a way that lets Request creation
or verification cross an input boundary. Multiple explicitly selected source files may share
their intended private source directory; source parents are not required to be distinct from one
another, and that sharing does not authorize traversal or discovery.

For `prepare-request`, the direct parent of `--output` must already exist and must be neither equal
to, an ancestor of nor a descendant of the Frozen Pack root or the direct parent of any of the
eight external inputs: Evidence, Reviewer A, Reviewer B, PairCheck, Evidence retained record,
Evidence Preparer reference, Reviewer A retained reference and Reviewer B retained reference.
`verify-request` applies the identical rule to the direct parent of its existing `--request`.
Prepare an independent sibling Request trust area before invocation; neither command creates that
directory. If any external private input is stored directly in a private aggregate root, a Request
directory created below that same root is its descendant and must be rejected. The operator must
instead place the Request area as a non-intersecting sibling, or first organize all sources under a
separate sibling source area under an independently approved procedure. The Request file itself
must not alias an input by path identity, physical identity or byte digest.

Reading is bounded by reviewed, compile-time limits per artifact class. Environment variables,
configuration files and command-line overrides cannot relax those limits. JSON input is decoded
strictly, with duplicate and unknown fields rejected through the existing versioned models. Media
bytes are matched to all fourteen manifest SHA-256 and size bindings; contract stable IDs,
canonical document SHA-256 values, roles, ordered Pack closure, retained-record hashes and every
cross-reference are recomputed rather than trusted.

Each source is checked before opening, identified through the opened handle, read within its
bound, hashed, and checked again after reading. The complete closure is then checked again before
the command returns or creates an output. Any replacement, relink, size/time/file-identity change,
short/extra read or digest drift is a TOCTOU failure. No partially validated summary or request is
emitted after such a failure.

## Command semantics

`inspect-ready` performs all path, byte, strict parsing, identity, closure, policy and time checks.
It requires PairCheck status to equal exactly
`READY_FOR_SEPARATE_QUALIFICATION_REVIEW` and `issue_codes` to be empty. Its only permissible
operator result is a bounded `READY_FOR_REQUEST_PREPARATION` diagnostic on the process streams;
it must not print a request ID, request body or `QUALIFICATION_REQUESTED` status. It creates no
file, cache, workspace, receipt, log or corrected source. The implementation may derive and
validate the candidate request in memory, but discards it rather than representing inspection as
request creation.

`prepare-request` repeats the same validation and calls only the pure ADR-021 request builder.
It writes canonical request bytes to one explicit repository-external `--output` target using
create-new semantics. It must fail if that target already exists. It never
overwrites, appends, repairs or updates an artifact and never creates a `latest` or `current` file
or pointer. A target whose basename contains a mutable alias token `latest`, `current` or `newest`
is rejected.
An unsuccessful operation must not leave a completed-looking Request. Rollback retains the exact
descriptor opened by this invocation and first irreversibly invalidates that exact inode before
attempting deletion. On Windows, deletion uses the exact open OS handle and never falls back to a
path delete. If the platform refuses the delete mark after exact-inode invalidation was verified,
a zero-byte or otherwise unparseable fail-closed remnant may remain; it is not a Request, the
command has failed, and the tool must neither repair nor overwrite it. On POSIX, deletion is
attempted through the guarded parent `dirfd` only after matching the named inode to the open inode;
a different replacement is never deleted. Normal tested failures remove the target. If neither
invalidation nor safe deletion can be confirmed, the operation raises `rollback failed closed`;
it makes no claim about the pathname's remaining bytes, and the entire Request trust area is
unresolved until a separately approved human audit and cleanup.

`verify-request` strictly loads one explicitly selected existing request, rebuilds it from all
explicit sources and requires the exact canonical bytes, request ID, SHA-256 bindings, policy
triple, time values and zero-authority state to agree. It cannot normalize a near match or rewrite
the request. It produces no filesystem output.

All three subcommands fail closed on missing, extra, ambiguous, aliased, malformed, expired,
future-dated, changed, conflicting or unbound input. They never infer that a request is approved
because all mechanical checks pass.

## Zero-authority request

Every prepared or verified request must retain exactly:

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

The request means only that exact local bytes were presented as one finite candidate input for a
future, separately approved qualification decision. It is not proof of legal sufficiency, a
rights manifest, qualification result, entitlement, authorization, publication permission or
Runtime instruction. It must never be renamed or placed where another component treats it as one
of those artifacts.

## Immutable compatibility and prohibited dependencies

This delivery adds no versioned contract and changes no Schema. All 55 existing committed Schema
files, every existing contract and the ADR-021 Finalizer Python API must remain byte-compatible.
The trusted preparation boundary may depend on the existing strict contracts and pure request
builder, but it must not alter or call the decision builder.

The boundary has no Runtime, Worker, Provider, PostgreSQL, Temporal, Ark, Atomic Ledger,
entitlement, authorization or migration dependency. It does not read an API Key, access a
console, use a network, upload private bytes, issue a Provider request or POST, start a service,
purchase, recharge or claim a trial. It does not call v1 qualification, synthesize 28 v1 review
records or create any rights manifest. It does not read or modify repository `output/` or `tmp/`.

## Development and operational separation

This implementation PR must exercise the boundary only with synthetic files in isolated local
test directories. It must not read, inspect, hash or invoke the current real private Pack,
Evidence, retained records, A/B reviews or PairCheck. Passing tests establishes behavior of the
local boundary; it does not establish that a real closure is ready.

Operating these commands on real private paths is a later stage requiring explicit approval and
an exact path manifest. Calling any Decision Finalizer on a prepared real request is a still later
stage because that act is real qualification. Designing or generating a rights manifest, and any
authorization or entitlement bridge, remain further independent stages and PRs.

## Consequences

The project gains a narrow bridge from explicitly selected private bytes to a reproducible,
finite, zero-authority request without weakening the contract-only separation in ADR-021.
Directory discovery, path redirection, unbounded reads and silent source drift become hard
failures at the local boundary. Operators can inspect readiness and reproduce a request without
making a qualification decision.

This design intentionally adds friction at the trust boundary: every input is named, every byte
identity is re-established and every output is create-new. That friction is limited to the one
operation that crosses from private files into a contract. It prevents a convenient request
preparer from becoming an implicit decision engine or a mutable authorization channel.
