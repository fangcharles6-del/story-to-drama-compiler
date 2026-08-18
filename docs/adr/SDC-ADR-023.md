# SDC-ADR-023: Trusted local finalization of Pack-level qualification decisions v2.2

- **Status:** Proposed
- **Date:** 2026-08-18
- **Version:** V01

## Context

SDC-ADR-021 added immutable Pack-level Human Review v2 qualification Request and Decision
contracts plus a pure in-memory compiler. SDC-ADR-022 then added a trusted local boundary that can
inspect, create and verify a zero-authority Request. Request preparation deliberately accepts no
Qualifier input and never invokes the Decision builder.

The next boundary must consume one exact Request, one separately retained Qualifier reference and
one explicit Qualifier decision record without weakening either earlier boundary. Unlike Request
preparation, finalizing a Decision from real private records performs the scoped rights
qualification recorded by SDC-ADR-021. A successful positive outcome is still only
`PASS_ASSET_INTAKE_ONLY`; it is not a rights manifest, entitlement, authorization, publication
approval or Runtime approval.

A filename, copied digest or CLI-supplied conclusion cannot establish this boundary. The local
consumer must reopen and reconstruct the entire upstream closure, bind the Qualifier's actual
canonical instruction bytes, enforce the Request's finite time window and create at most one new
canonical Decision. Inspection must remain distinguishable from qualification, and later
verification must remain a historical byte-closure check rather than a fresh wall-clock decision.

## Decision

Add one trusted local Decision-finalization boundary with exactly three operator-facing
subcommands:

- `inspect-decision-ready` performs the complete read-only readiness check, but must not call
  `build_real_asset_qualification_decision_v2` or emit a Decision;
- `finalize-decision` repeats the complete check, invokes the existing pure Decision builder once
  and creates exactly one new canonical `CreativeSampleRealAssetQualificationDecisionV2`; and
- `verify-decision` reopens the full bound closure, historically reconstructs one explicitly
  selected existing Decision and requires exact canonical equivalence, with zero filesystem
  writes.

The package launcher and every option spelling must match the reviewed implementation and its
generated `--help`. The three subcommand names and their semantic boundaries are normative. There
is no fourth command, hidden automatic continuation, interactive decision prompt, waiver,
`--force`, repair mode or manifest mode.

This development PR uses only synthetic temporary fixtures. It must not read or invoke the
current real private Pack, Evidence, Reviews, PairCheck, Request, Qualifier reference, instruction
or Decision. Any invocation over real private paths is a later operation requiring its own
explicit approval and exact path list. In particular, an approval to inspect must not be treated
as approval to finalize.

## Canonical Qualifier instruction

Add the append-only
`CreativeSampleRealAssetQualificationDecisionInstructionV22` contract and its committed Schema.
The instruction is a private, canonical UTF-8 JSON record authored under the independent
Qualifier procedure. It is also the retained Qualifier decision record; there is no separate
discoverable “record” file. Its SHA-256 is calculated over the complete canonical file bytes and
is passed to the existing Decision builder as `qualifier_record_sha256`. The instruction cannot
contain its own file SHA-256.

The instruction binds:

- `schema_version=2.2.0`,
  `document_type=sdc.creative-sample-real-asset-qualification-decision-instruction-v2.2` and
  `profile=creative-sample-real-asset-qualification-decision-finalization-v2.2`, plus a
  content-derived `instruction_id`;
- the exact Request ID and canonical Request SHA-256;
- the fixed SDC-ADR-021 policy ID, version and policy-document SHA-256;
- `qualifier_role=INDEPENDENT_QUALIFIER`;
- the exact retained Qualifier-reference SHA-256;
- one explicit canonical `decision_at` UTC second;
- one explicit Decision outcome, non-empty qualification basis and canonical issue-code tuple;
- `qualification_scope=ASSET_INTAKE_ONLY`; and
- the fixed zero-authority instruction state:
  `status=DECISION_INSTRUCTION_RECORDED`, `rights_qualification_performed=false`,
  `eligible_for_separate_manifest_design_review=false`, `rights_manifest_created=false`,
  `HUMAN_GATE`, `NOT_AUTHORIZED`, `eligible_for_real_generation=false`,
  `execution_authorized=false`, `posts_allowed=0` and `provider_requests=0`.

The CLI does not accept `decision_at`, `decision`, `qualification_basis` or
`qualification_issue_codes`. It must never infer them from the PairCheck, Request, filename,
environment, current time or operator prompt. It accepts only the path to the complete canonical
instruction and the separate path to the Qualifier reference. Duplicate or unknown JSON fields,
non-canonical text or time, malformed values, a copied binding or a non-canonical whole document
are hard failures.

The existing SDC-ADR-021 outcome rules remain unchanged:

- `PASS_ASSET_INTAKE_ONLY` requires an empty issue-code tuple;
- `REJECTED` requires a non-empty tuple containing
  `QUALIFIER_REJECTED_ASSET_INTAKE`;
- `NEEDS_HUMAN_REVIEW` requires a non-empty tuple that excludes that rejection code; and
- every outcome requires a trimmed, non-empty human `qualification_basis`.

The instruction's fixed
`eligible_for_separate_manifest_design_review=false` is intentional: an instruction is not a
completed Decision and cannot grant even the next design-gate eligibility. The final Decision
derives that field as `true` only for `PASS_ASSET_INTAKE_ONLY`; even then it grants no manifest or
execution authority.

## Explicit input closure

Every source is named by an individual absolute local path. The finalizer never scans for a Pack,
contract, record, Request, instruction or Decision; expands a glob; chooses the newest file;
follows a `latest`, `current` or `newest` alias; or infers a sibling filename. Its complete source
closure consists of:

1. the explicitly selected Frozen Pack root;
2. its manifest through a separate path that must equal `<pack-root>/asset-pack.json`;
3. all fourteen media objects through fourteen ordered paths, each exactly rebound to its
   manifest descriptor;
4. the Pack-level Rights Evidence contract;
5. Reviewer A's finalized Pack-review contract;
6. Reviewer B's finalized Pack-review contract;
7. the exact issue-free, ready PairCheck;
8. the retained Evidence record;
9. the retained Evidence Preparer reference;
10. Reviewer A's retained reference;
11. Reviewer B's retained reference;
12. the exact existing Qualification Request;
13. the retained Qualifier reference; and
14. the canonical v2.2 Qualifier decision instruction.

`verify-decision` additionally requires the exact existing Decision. `finalize-decision`
additionally requires one explicit absent output filename. The v2 Reviews'
`review_record_sha256` fields remain canonical review-content digests and do not name two more
files.

The one permitted enumeration is the existing bounded exact-tree verification of the explicitly
selected Frozen Pack root. It may reject extra Pack members and reproduce the fourteen technical
evidence records. It must not discover, choose or substitute an input. All fourteen media paths
remain separately required and ordered. No other directory may be enumerated.

The Evidence Preparer, Reviewer A, Reviewer B and Qualifier are four independent roles. The four
retained Request-stage records, Qualifier reference and complete instruction-file digest must be
pairwise distinct and must not alias an upstream contract, policy, Request, media, provenance or
technical record. SHA-256 proves byte distinction, not personal identity or organizational
independence; those remain human controls outside this compiler.

## Time semantics

`inspect-decision-ready` and `finalize-decision` each require one explicit `--observed-at` in
canonical whole-second UTC form. The program does not read the wall clock and provides no
default, environment fallback or filesystem-time inference. The instruction provides the only
`decision_at`.

Readiness and finalization require:

```text
request.requested_at <= instruction.decision_at <= observed_at < request.request_valid_until
```

The existing evidence-validity and causal-order rules still apply. The exclusive Request expiry
cannot be extended, rounded or replaced. A future-dated decision, a finalization observed at or
after expiry, or a positive decision based on expired evidence fails closed.

`verify-decision` accepts no observed time and reads no clock. It verifies the historical closure
using the immutable Request and Decision times. A Decision that was finalized within its original
validity window remains verifiable after that window has elapsed; later expiry does not rewrite a
historically timely Decision.

## Local path and byte boundary

Every source, instruction and Decision must be outside the Git repository. Only fully qualified,
ordinary local paths are admitted. Relative, UNC/network, device or extended-device, alternate
data stream, symbolic-link, junction, mount/reparse-point, hard-linked, non-regular and
case-folded alias paths are rejected. Every existing lexical component is inspected without
following redirection, and lexical, resolved and opened-file identities must agree.
The Qualifier-instruction basename and both new and existing Decision basenames must not contain
the outcome tokens `pass`, `rejected` or `needs`; conclusions remain inside canonical private
bytes rather than process lists or shell history.

Ordinary source files may share an intended source directory. That sharing does not authorize
discovery or traversal. The selected Request must still satisfy the SDC-ADR-022 trust-area rule:
its direct parent is neither equal to, an ancestor of nor a descendant of the Frozen Pack root or
the direct parent of the original eight external Request inputs. The Qualifier reference and
instruction may share an otherwise admissible source parent; that does not weaken any byte- or
file-identity separation rule.

The direct parent of a new Decision output, or of the existing Decision selected for
verification, must already exist and must be neither equal to, an ancestor of nor a descendant of:

- the Frozen Pack root; or
- the direct parent of Evidence, Reviewer A, Reviewer B, PairCheck, retained Evidence, retained
  Evidence Preparer reference, retained Reviewer A reference, retained Reviewer B reference,
  Request, Qualifier reference or Qualifier instruction.

The operator must therefore pre-create an independent sibling Decision trust area. The command
creates no directory, template, receipt, cache, temporary workspace, log or mutable alias. If any
source file is directly under an aggregate private root, a Decision directory below that root is
its descendant and must be rejected; use a genuinely non-intersecting sibling trust area under a
separately approved arrangement.

Every read is bounded by fixed implementation limits. Each source is admitted, opened without
following redirection, identified from its exact handle, read and SHA-256 hashed within its bound,
then checked again by handle and path. The complete closure is checked again before success or
output creation. Any replacement, relink, hard-link-count change, short or extra read, size/time
or file-identity drift, or digest difference is a TOCTOU failure.

JSON is strict UTF-8 and rejects duplicate and unknown fields. The finalizer reconstructs every
stable ID, canonical document digest, role, ordinal, fourteen-member Pack binding, retained-record
binding, PairCheck result, policy triple and Request field. It requires PairCheck status to equal
exactly `READY_FOR_SEPARATE_QUALIFICATION_REVIEW` with an empty issue tuple. The selected Request
must be the exact canonical output reproducible from these upstream bytes.

## Command and output semantics

`inspect-decision-ready` performs all path, byte, strict parsing, closure, instruction-binding and
time checks but intentionally stops before the pure Decision builder. Its success summary says
only `READY_FOR_DECISION_FINALIZATION`, reports `rights_qualification_performed=false` and keeps
all zero-authority state. It emits no Decision ID, outcome, basis, issue codes, SHA-256, private
path or instruction body. It writes nothing.

`finalize-decision` reopens and rechecks the entire closure rather than reusing inspection state.
Only after every check passes may it call `build_real_asset_qualification_decision_v2` and create
one canonical Decision through exclusive create-new semantics. An existing target is a hard stop;
there is no overwrite, append, repair, truncation, rename-as-latest or automatic retry. The
created bytes are reread from the exact open handle, strictly parsed, compared with the in-memory
Decision and checked again against every source before success.

`verify-decision` reopens all sources plus the exact existing Decision, reconstructs the historical
closure and requires canonical byte equivalence. It never repairs, normalizes or rewrites the
Decision, and it creates no verification receipt.

After output creation begins, rollback retains the exact created file descriptor. It first makes
that exact inode unusable and then deletes only the same identity. On Windows, deletion uses the
exact OS handle and never falls back to a pathname delete. On POSIX, deletion is guarded by the
parent directory descriptor and inode identity so a replacement is not removed. Normal tested
failures leave no target. If the operating system refuses safe deletion after exact-inode
invalidation, only a zero-byte or otherwise unparseable fail-closed remnant may remain; it is not
a Decision and requires separate human audit. If neither exact-inode invalidation nor safe
deletion can be confirmed, the command reports the fixed zero-authority status
`ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED` without making any claim about remaining bytes. The
operator must isolate the exact `--output` trust area and must not verify, use, repair or overwrite
anything in it until a separate human audit resolves the incident. Ordinary failures continue to
report `FAILED_CLOSED`.

All argument and runtime failures use bounded, non-secret diagnostics. Successful finalization or
verification may identify the resulting `decision_id` and
`rights_qualification_performed=true`, but must not print the outcome, basis, issue codes, record
hashes, private paths or source contents.

## Zero-authority completed Decision

A successfully finalized Decision truthfully fixes
`rights_qualification_performed=true`, including for `PASS_ASSET_INTAKE_ONLY`, `REJECTED` and
`NEEDS_HUMAN_REVIEW`. That field records that this scoped qualification consumer ran. Every
Decision nevertheless remains:

```text
HUMAN_GATE
NOT_AUTHORIZED
execution_authorized=false
posts_allowed=0
provider_requests=0
rights_manifest_created=false
eligible_for_real_generation=false
```

A positive Decision sets only `eligible_for_separate_manifest_design_review=true`. It does not
create a manifest, establish legal sufficiency, authorize generation, add an entitlement, approve
publication or permit a Provider call. Negative or review-needed Decisions set that eligibility
to false and remain equally non-authorizing.

The finalizer must not call `build_real_asset_rights_manifest`,
`qualify_real_asset_candidate_pack` or any v1 rights path; synthesize 28 v1 review records; update
an entitlement or authorization registry; touch Runtime, Worker, Provider, PostgreSQL, Temporal,
Ark, Atomic Ledger or migration code; read a Key; or perform network I/O, upload, POST, purchase,
recharge or trial.

## Compatibility and later stages

The 55 Schemas that existed before this change remain byte-identical. The single append-only v2.2
Qualifier-instruction Schema increases the committed total to 56. Existing Evidence, Review,
PairCheck, Request and Decision contracts, the public SDC-ADR-021 pure Finalizer Python API and all
production safety boundaries remain byte-compatible.

This PR supplies design, the local boundary and synthetic offline tests only. A later user may
separately approve exact real paths for inspection, then separately approve finalization and
historical verification. No approval flows automatically from one command to the next.

Even after a real positive Decision, a rights-manifest consumer remains a separate future design,
contract, policy review and PR. Any entitlement or authorization bridge is later still. Neither
stage may infer permission merely because `rights_qualification_performed=true` or the scoped
Decision is positive.

## Consequences

The Qualifier's decision becomes an explicit, retained and byte-bound input instead of an
unreviewable CLI value. Read-only readiness cannot accidentally perform qualification, and an
existing Decision can be audited after expiry without consulting a mutable clock. Full path,
byte, role and time closure makes silent substitution or discovery visible while preserving the
zero-authority safety state.

The stricter boundary adds operational ceremony: every private path must be supplied explicitly,
the Decision trust area must be pre-arranged, and any drift requires a fresh, human-reviewed
invocation. That cost is deliberate because this is the first local command in the v2 chain that
can record a real qualification outcome.
