# SDC-ADR-028: Trusted-local Use Plan and single Review Record finalization v2.7

- **Status:** Accepted
- **Date:** 2026-08-20
- **ADR release:** 1.0
- **Operational boundary version:** 2.7.0
- **Consumed contract Schema version:** 1.0.0
- **Inherited consumer and policy version:** 2.6.0

## Context

SDC-ADR-027 added five immutable v1 artifact contracts and pure v2.6 consumers for one
manifest-bound, provider-neutral Use Plan and one Maker/Checker Use Scope Review Record. The pure
boundary can reconstruct the complete nine-model Manifest closure, compile a deterministic Plan,
form immutable Request and Instruction modules, derive a Decision and historically verify the
single outer Record. It deliberately accepts no path and performs no file, network, clock,
Provider, Runtime or authorization operation.

The next useful boundary is a trusted-local authoring and finalization layer. It must safely bind
explicit repository-external files, preserve the Maker -> Checker -> compiler responsibility
chain, create at most one canonical Plan and one canonical outer Review Record, and historically
verify those artifacts. It must not turn an in-memory PASS, a planning envelope or a written file
into production permission.

The outer Record creates an unusual operational constraint. Request, Instruction and Decision
are independently typed physical modules with independent stable IDs and canonical-document
SHA-256 values, but they are not three separately persisted operational artifacts. A trusted-local
boundary therefore needs an auditable handoff between the Maker and Checker without a Request
file, Instruction file, mutable draft workspace, receipt cache or progressively edited Record.

This ADR is accepted for synthetic-only implementation. That acceptance authorizes source and test
work against isolated synthetic fixtures only. It does not authorize private-data access, a real
artifact operation, commit, push, PR publication, merge or any Provider operation.

## Decision

Design two separate trusted-local operational boundaries:

1. a Use Plan boundary that may inspect readiness, create exactly one canonical
   `CreativeSampleRealAssetUsePlanV1`, and historically verify one existing Plan; and
2. a Use Scope Review boundary that preserves the three pure construction stages, may create
   exactly one canonical `CreativeSampleRealAssetUseScopeReviewRecordV1`, and historically verify
   one existing Record.

The Python modules are:

```text
sdc.real_asset_use_plan_finalizer_v27
sdc.real_asset_use_scope_review_finalizer_v27
```

The operator operations are:

```text
inspect-use-plan-ready
finalize-use-plan
verify-use-plan

preflight-review-request
preflight-review-instruction
finalize-review-record
verify-review-record
```

`preflight` is used for the two human-owned modules because each operation must actually invoke
the corresponding pure builder in memory to produce a canonical approval fingerprint.
`inspect-use-plan-ready` similarly constructs a deterministic candidate Plan in memory but writes
nothing. The companion runbook defines the exact CLI, source table, byte limits and bounded
summaries.

There is no automatic continuation between operations. Approval to inspect or preflight does not
approve finalization. Approval to finalize does not approve verification. Maker preflight does
not approve Checker preflight, and Checker preflight does not approve Record creation.

V2.7 exposes no current-window command in this release. The existing pure
`verify_use_scope_review_current_v1` remains unchanged, but a trusted-local currentness operation
is deferred until a later ADR also defines fresh hold, revocation, complaint and dispute status
evidence. Historical verification must not be presented as current rights clearance.

## Version and Schema compatibility

V2.7 is an operational boundary version. It consumes the existing v1 artifacts,
`schema_version=1.0.0`, and the fixed v2.6.0 Use Plan and Review policies. It must not rename,
extend or reinterpret those contracts or policies.

The implementation adds no production contract and no committed Schema. All 62 existing
Schemas must remain normalized-LF byte-identical. Inspection summaries, path envelopes, source
captures and expected-fingerprint guards are local operational types, not versioned artifacts and
not bearer tokens.

## Artifact topology

The only persisted artifacts created by this boundary are:

```text
one complete CreativeSampleRealAssetUsePlanV1
one complete CreativeSampleRealAssetUseScopeReviewRecordV1
```

The Record contains exactly three nested physical modules and their independent digests:

```text
request + request_sha256
instruction + instruction_sha256
decision + decision_sha256
record_id
```

There is no Request output path, Instruction output path or Decision output path. The boundary
must not create a partial Record, progressively append modules, rewrite an earlier module, flatten
the three modules into shared fields or create a generated draft, workspace, receipt, cache,
pointer or latest/current alias. The single Record appears only after all three modules are fully
reconstructed and validated in memory.

The existing pure extractors may expose any one module and its canonical bytes only after the
complete Record and upstream closure have passed historical verification. Extraction is read-only
and does not authorize writing three operational files. A damaged or partially valid Record is
not eligible for extraction through the accepted path.

## Fingerprint-bound Maker and Checker handoff

The absence of intermediate module files must not erase the human-stage boundary.

`preflight-review-request` reconstructs the exact Maker Request in memory and reports a bounded,
non-authoritative fingerprint containing only:

```text
status=REVIEW_REQUEST_READY_FOR_CHECKER_PREFLIGHT
request_id
request_sha256
```

`preflight-review-instruction` receives the separately approved Request ID and SHA-256 as expected
guards. It first reopens the complete current source closure and independently reconstructs the
Request. Only after the calculated ID and canonical-document SHA-256 exactly equal both expected
values may it construct the Checker Instruction. It then deterministically builds a candidate
Decision and complete outer Record in memory so the write approval can name their exact content.
It reports:

```text
status=REVIEW_INSTRUCTION_READY_FOR_RECORD_FINALIZATION
instruction_id
instruction_sha256
decision_id
decision_sha256
record_id
record_sha256
```

`finalize-review-record` receives the separately approved Request, Instruction, Decision and Record
fingerprints as expected guards. It again reconstructs the Request, compares the Request guards,
constructs the Instruction against that exact immutable Request, compares the Instruction guards,
and only then invokes the existing deterministic Record builder. It computes and compares the
Decision ID/SHA and Record ID/SHA before opening the output. The Decision accepts no caller-supplied
decision, issue code, deadline, eligibility value or authority override.

Expected fingerprints are equality gates only. They must be compared after construction from the
complete selected bytes. Caller-supplied expected copies are never passed to a pure builder; after
the comparison succeeds, the builders still derive and bind the calculated Request and Instruction
values normally. Expected copies never locate or load a module, enter a stable-ID payload, replace
a computed value, repair drift, skip a read, substitute for a closure, prove human identity or
grant authority. A mismatch fails closed before output creation.

The CLI may display the calculated Plan, Request, Instruction, Decision and Record ID/SHA pairs
because separate human approval must be able to name the exact handoff. It must not display private
paths, basis text, gate notes, identity contents, Decision reasoning or source bytes. It creates no
fingerprint file.

## Maker and Checker identity references

The Maker and Checker are represented by two explicitly selected, repository-external
identity-reference files. Every applicable operation safely reopens and hashes the exact files and
enforces separation by lexical path, resolved path, opened-file identity and whole-file SHA-256.
Each identity reference must also be distinct from every admitted contract, media, retained,
policy, Plan, Record and human-input digest in the same operation.

The Request binds the Maker identity-reference whole-file SHA-256. The Instruction and Decision
bind both references through the existing pure builders. Paths themselves are not embedded in the
artifact.

Path, file-identity and digest inequality prove only procedural reference separation. They do not
authenticate a natural person, verify a signature, prove custody of a Key or prove that two people
acted independently. No diagnostic, success status, API name or test may claim otherwise.

## Human-authored input transport

The pure Request and Instruction builders require human-authored text and the Checker requires six
ordered gate results and their policy-required notes. Passing that text directly on a command line
exposes it to process listings, shell history and quoting ambiguity. Persisting complete Request or
Instruction JSON would violate the single-Record design.

V2.7 uses two explicitly selected, repository-external, hostile, non-authoritative authoring input
files:

```text
Maker input:   request_basis
Checker input: six ordered gate results, disposition, checker_basis
```

They are not Request or Instruction contracts and carry no module ID, digest, policy, derived field,
eligibility or authority value. They are never accepted downstream as already validated modules or
authority. Every applicable operation reparses their exact bytes and independently reconstructs
the human-owned module. Only the outer Record is a finalized review artifact.

`requested_at` and `evaluated_at` remain separate explicit CLI values. The Request expected ID/SHA
pair and every later expected pair are separate comparison-only CLI guards; they are not stored in
either authoring input.

Each authoring input is at most 65,536 bytes and uses the standard canonical JSON document form:
strict UTF-8 without BOM, sorted keys, two-space indentation, unescaped Unicode where JSON permits
it and one final LF. Its filename has a case-insensitive exact `.json` suffix. Duplicate, unknown,
missing, defaulted, coerced and non-finite values fail
closed. Basis strings retain the existing 2,000-character limit; gate notes retain the existing
1,000-character limit. Every human string must already be NFC, equal its own `strip()`, and contain
no C0 or DEL control character. The boundary never trims, normalizes or repairs it.

Both authoring inputs come from separately approved private source areas. On POSIX the effective
user owns each file and its mode is exactly `0600`. On Windows each file satisfies the protected
owner-only DACL predicate defined for v2.7 outputs. A broader or unverifiable permission set fails
closed before any human text is read.

The implementation accepts no standard-input, environment-variable, implicit-default,
shell-evaluated, discovered or combined mutable-draft alternative.

## Exact full physical closure

V2.7 uses the full physical closure. This choice is based on an explicit per-operation source
mapping, not a fallback from a smaller contract-only mode. The common Plan closure contains the
complete 28 entries defined by v2.5 plus one explicitly selected existing Rights Manifest. It
therefore freshly re-proves every media and retained-byte fact rather than treating the Manifest as
a bearer token.

The exact existing-source counts are:

| Operation | Existing sources |
|---|---:|
| `inspect-use-plan-ready` | 29 |
| `finalize-use-plan` | 29 |
| `verify-use-plan` | 30, including the Plan |
| `preflight-review-request` | 32, adding Plan, Maker identity and Maker input |
| `preflight-review-instruction` | 34, adding both identities and both inputs |
| `finalize-review-record` | 34 |
| `verify-review-record` | 33, adding both identities and Record but no authoring input |

An absent finalization output is not an existing source. Pack root remains one explicit anchor and
is never enumerated. The fourteen media files remain fourteen separately supplied ordinal paths.
No operation has a Request, Instruction or Decision path. No reduced closure profile exists.

## Common trusted-local path and byte boundary

Every filesystem source and output must be individually supplied as a fully qualified ordinary local path
outside every Git tree. The boundary never scans a directory, expands a glob, selects newest,
follows a latest/current pointer, discovers a sibling or reads repository `output/` or `tmp/`.

Relative and empty paths, UNC/network paths, device and extended-device namespaces, alternate data
streams, symbolic links, junctions, reparse points, non-anchor mounts, bind mounts, hard-linked
files, non-regular files, case-folded aliases and physical aliases fail closed. Every existing
lexical component is inspected without following redirection. Lexical, resolved, path and opened
handle identities must agree.

Output and existing-artifact trust areas must be mutually isolated. A source trust area means the
Pack root, every external source direct parent, the Rights Manifest parent, the Plan parent, both
identity-reference parents and both authoring-input parents admitted by the operation table. The
Manifest parent is isolated from all 28 upstream entries; the Plan parent is isolated from those
entries and the Manifest. `finalize-review-record` isolates the new Record parent from every
preceding area, both identities and both authoring inputs. Historical Record verification does not
reopen the authoring inputs; it isolates the existing Record from every source in its 33-entry
verification closure. Preflight checks only the sources it actually receives. Equality and
ancestor/descendant overlap fail closed. Plan and Record input/output filenames have a
case-insensitive exact `.json` suffix. For every path component, Unicode `casefold()` is split on
runs outside ASCII `[a-z0-9]`; a component token `latest`, `current` or `newest` is rejected. The
same tokenization of the filename stem rejects `pass`, `needs`, `rejected`, `revision`, `approved`
or `authorized`.

The inherited fixed bounds are 1,048,576 bytes for each upstream JSON or retained/private reference,
67,108,864 bytes for each media member and 1,048,576 bytes for fixed platform mount metadata. A
Plan is at most 4,194,304 canonical bytes, a Record at most 2,097,152 canonical bytes and each
authoring input at most 65,536 canonical bytes. Candidate size is checked before output open. No
option, environment setting or configuration may increase a limit.

JSON is strict canonical UTF-8 without BOM, duplicate keys, non-finite constants, unknown fields
or coercion. Identity references are hashed as exact bounded bytes and are not interpreted as
identity proof.

## TOCTOU and complete-closure replay

Every operation admits the exact paths, opens each non-linked object without following
redirection, compares path and handle identity, performs a bounded read, hashes exact bytes and
checks identity again. Inspect, preflight and verify capture the complete operation-specific
closure at least twice. Each finalizer captures it before build, immediately before create-new and
again after same-handle output verification. The first two captures must agree before output open;
the final capture must still agree. Any replacement, relink, link-count change, short or extra
read, size, time, identity or digest drift fails closed.

The v2.7 implementation must not call the v2.5 `verify_manifest` operation and then independently
reopen only a subset of inputs without a common identity seal. That would create a split snapshot.
It must either capture the selected physical closure as one composite snapshot or prove that every
later model read belongs to the exact already captured file identity and digest, followed by a
complete post-operation capture.

No inspection or preflight result is cached or trusted by a later operation. Expected module
fingerprints detect an approval-object change; they do not replace fresh path and byte capture.
Identical-byte replacement between separate operations is not claimed to preserve inode identity;
the approval guard binds reconstructed canonical content. Replacement during one operation is
caught by that operation's composite captures.

Before output open and again after same-handle reread, the candidate output digest must not alias
any selected source, identity, authoring input, policy, retained, media, provenance or technical
digest. The inherited intentional equality between the canonical Qualification Instruction file
SHA-256 and `qualification_decision.qualifier_record_sha256` is the only file-digest equality
exception. Expected-guard comparison is not a source-digest alias exception.

## Use Plan operation semantics

`inspect-use-plan-ready` performs the complete path, byte, Manifest closure, policy, known-vector,
fourteen-mapping and zero-authority checks. It constructs the deterministic candidate Plan in
memory, produces its stable ID and canonical-document SHA-256 for a later exact approval, writes
nothing and ends. Its status must not say that a Plan was created.

`finalize-use-plan` repeats the complete validation, independently rebuilds the exact candidate,
requires the separately approved expected Plan ID and canonical-document SHA-256 to both match,
and uses exclusive create-new semantics to create one canonical Plan. Both guards are mandatory.
It cannot overwrite, repair, append or reuse an inspection cache.

`verify-use-plan` strictly reads one explicitly selected canonical Plan, reopens the accepted
upstream closure, calls the existing pure historical closure verifier, and requires exact model
and canonical-byte equivalence. It writes nothing and reads no clock.

The Plan operations introduce no time and accept no `now`, `observed_at` or filesystem-time
fallback. They inherit the immutable Manifest time through the pure model.

## Review operation semantics

`preflight-review-request` verifies the full Plan closure, reads the Maker reference and accepted
Maker input, invokes only the pure Request builder, reports the Request approval fingerprint and
writes nothing. It accepts no Checker field.

`preflight-review-instruction` repeats the complete closure and Request build, applies the expected
Request guards, then reads the distinct Checker reference and accepted Checker input and invokes
the pure Instruction builder. It next invokes the deterministic Record builder in memory to derive
the candidate Decision and complete Record anchors. It reports the Instruction, Decision and
Record approval fingerprints and writes nothing. It cannot change a Request field or accept an
operator-supplied Decision.

`finalize-review-record` repeats every source capture and both pure human-module builds in fixed
order, applies the Request and Instruction expected pairs, invokes the deterministic Record builder
exactly once, applies the Decision and complete Record expected pairs, and creates one complete
outer Record through create-new semantics. It does not write a module, draft or receipt before the
complete Record is known.

`verify-review-record` strictly reads one explicitly selected outer Record, reopens and verifies
the complete Manifest and Plan closure, verifies both identity-reference whole-file digests,
invokes the full pure historical Record verifier and requires exact canonical equivalence. It may
exercise all three existing pure extractors internally. It does not need human-input sources,
because their accepted content is already bound inside the nested modules. It writes nothing and
reads no clock.

Valid `NEEDS_REVISION` and `REJECTED` Records may be finalized and historically verified. They are
important audit facts and retain zero authority. Only a future current-window assessment requires
a PASS.

## Explicit time boundaries

Use Plan operations read no current time. Maker input supplies one canonical UTC-second
`requested_at`; Checker input supplies one canonical UTC-second `evaluated_at`. Finalization
reconstructs those exact approved values. The deterministic Decision sets
`decision_at=evaluated_at` and derives its review horizon.

The existing pure rules remain normative:

```text
manifest_at <= requested_at <= evaluated_at < requested_at + 86400 seconds

for finite Evidence:
requested_at < evidence_valid_until
evaluated_at < evidence_valid_until

review_valid_until = min(evaluated_at + 2592000 seconds, finite evidence_valid_until)
review_valid_until = evaluated_at + 2592000 seconds for PERPETUAL Evidence
```

All upper bounds are exclusive. There is no default to wall clock, local timezone, filesystem
timestamp, environment value or network time. Historical verification accepts no new time and
remains historical after a recorded deadline.

## Create-new rollback and quarantine

Only `finalize-use-plan` and `finalize-review-record` may write. Each operates on one explicit
absent path whose parent already exists. Admission retains a guarded physical identity for that
parent and revalidates it immediately before create-new. A swap detected by that revalidation fails
before open. A rename or swap racing after the check must be detected by the pre-commit parent/path
identity check and trigger exact-handle rollback; the boundary does not claim an impossible
race-free pathname precheck. It creates no directory and uses no overwrite, append,
truncate-existing, repair, backup-as-authority or automatic retry mode.

On POSIX creation uses `openat` relative to the guarded parent directory descriptor with
`O_NOFOLLOW|O_CREAT|O_EXCL|O_CLOEXEC` and mode `0600`; `fstat` verifies the exact descriptor owner
and mode. On Windows creation uses `CreateFileW` on the guarded normalized full path with desired
access `GENERIC_READ|GENERIC_WRITE|DELETE`, share mode `0`, creation disposition `CREATE_NEW`,
`FILE_ATTRIBUTE_NORMAL`, a non-inheritable handle and an explicit protected security descriptor.
In particular, `FILE_SHARE_DELETE` is never granted while the retained output handle is live. The
owner is the effective token-user SID and the DACL contains exactly one non-inherited allow ACE for
that SID with `FILE_ALL_ACCESS`; no other ACE is admitted. `GetSecurityInfo` must verify that exact
owner, protected DACL and normalized access mask before commit. Windows rechecks the guarded parent
and full-path identity immediately after create and before commit because `CreateFileW` has no
parent directory-handle-relative contract equivalent to POSIX `openat` here.

After output creation begins, the implementation retains the exact descriptor through write,
flush, same-handle reread, strict parse, canonical comparison, full post-write source recapture and
checked close. When the retained descriptor is provably live, any failure first makes the exact
created inode unparseable. If a descriptor-close side effect cannot be determined, the
implementation must not retry, reuse or operate through that descriptor number; it returns the
dedicated quarantine-required result instead. Any parseable remnant in that state is quarantined
and is not an artifact or authority.

On POSIX, rollback poisons through the retained file descriptor and performs no pathname unlink.
While retaining the guarded parent directory descriptor, it closes the file descriptor and proves
that the target name is absent or still names the exact invalidated inode. On Windows, rollback
requests deletion only through the exact OS handle, checks the `CloseHandle` result, and treats
delete-pending as confirmed only after close succeeds and the target name is absent. A name that
now refers to an independent inode is never deleted and always requires quarantine. Failure to
close the file or parent guard is also quarantine-required once output creation may have occurred.

If exact invalidation or deletion cannot be proven, the operation raises a dedicated quarantine
exception and reports:

```text
ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED
```

The complete exact output trust area must then be isolated until a separately approved human audit
resolves the incident. An invalid remnant is not a Plan or Record and must not be repaired or
overwritten. Ordinary failures report `FAILED_CLOSED`.

## Zero-authority state

A finalized Plan remains an offline planning candidate. A finalized Review Record reports one of
the three existing dispositions. Even the strongest PASS changes only:

```text
eligible_for_separate_provider_proposal=true
```

Provider approval, remote processing, retention, training, generation, execution and publication
remain false. Authorized attempts, authorized cost, posts and Provider requests remain zero. The
planning ceilings of 20 proposed requests and CNY 450 remain non-authoritative ceilings and must
not be copied into authorization fields.

No v2.7 success status or prose conclusion may characterize the result as `generation-ready`,
`provider-approved`, `authorized`, `entitled` or an equivalent authority-bearing finding. Exact
negative contract fields such as `execution_authorized=false` remain valid audit facts.

## Synthetic-only implementation separation

Any later implementation PR must use only synthetic fixtures in isolated temporary directories.
It must not read, inspect, hash or invoke a current private Pack, media file, Evidence, identity
reference, qualification record, Manifest, Plan or Review Record. It must not read or modify
repository `output/` or `tmp/`.

Passing tests would establish the behavior of the boundary, not the readiness of any real closure.
After a separately reviewed implementation is merged, every real inspect, preflight, finalize and
verify operation still requires a new explicit approval naming its complete exact inputs and, where
applicable, expected fingerprints, times and absent output.

## Required tests

The later implementation must include synthetic tests for:

- positive Plan inspect/finalize/verify and Review preflight/finalize/verify flows;
- proof that only the two finalize operations write and each creates exactly one artifact;
- Plan, Request, Instruction, Decision and Record expected-guard mismatch after every mutation that
  changes reconstructed canonical content or an identity-reference digest;
- proof that expected guards are comparison-only and never enter constructed payloads;
- fixed Request -> Request guard -> Instruction -> Instruction guard -> Record -> Decision/Record
  guards call order;
- valid PASS, NEEDS_REVISION and REJECTED Records with exact zero-authority fields;
- complete path-count, order, alias, hard-link, reparse, mount, bounded-read and TOCTOU failures;
- strict canonical JSON and human-input byte policy;
- output trust-area and parent-identity separation, private output permissions, create-new races,
  exact-handle reread and replacement-safe OS-specific rollback;
- fault injection at create, write, flush, reread, parse, post-capture and close boundaries;
- explicit UTC-second and exclusive time boundaries with no clock fallback;
- identity path, file and digest separation without authentication claims;
- zero network, Key, Provider, Runtime, entitlement, authorization, ledger, database or migration
  dependency;
- no Request, Instruction, Decision, draft, receipt, cache or pointer output;
- proof that Record verification never accepts or opens either authoring input and still succeeds
  after those inputs are removed;
- all 62 committed Schemas remaining byte-identical; and
- identical inputs producing identical canonical artifacts across repeated processes.

The companion runbook contains the normative synthetic-only implementation matrix.

## Explicit prohibitions

V2.7 must not:

- discover, scan, glob, auto-select or infer a private input;
- accept a digest, ID, Manifest or Plan in place of exact selected bytes;
- persist Request, Instruction or Decision as a standalone operational artifact;
- incrementally edit a Review Record or create a mutable workflow workspace;
- treat expected fingerprints as artifact payload fields, reconstructed source content, repair
  values, receipts or bearer authorization;
- authenticate a person from path, file or digest inequality;
- select or contact a Provider, model, account, region, operation or price;
- upload, POST, purchase, recharge, claim a trial, generate or publish;
- create an entitlement, authorization, permit, task, ledger row or registry entry;
- read a Key, network, implicit clock, filesystem-selected time or environment-selected policy;
- import Runtime, Worker, Provider, Ark, database, Temporal, ledger or migration code;
- invoke a v1 rights, qualification or revision conversion;
- add or mutate a production contract, Schema or v2.6 policy; or
- infer authority from a Manifest, Plan, PASS, proposed request count or planning cost ceiling.

## Implementation and real-operation approval boundary

This accepted design freezes the physical closure, authoring-file transport, byte rules, command
set and currentness deferral. Synthetic-only source and test implementation has been separately
approved. Commit, push, PR publication, merge and every real-data operation remain outside that
approval and require separate explicit authorization.

No design can select real identity files, real times, human bases, gate results, disposition,
output paths or any Provider fact. After an implementation is independently reviewed and merged,
each real command still requires its own complete exact approval.

## Consequences

The design preserves a lightweight two-person workflow without erasing the responsibility chain.
The Maker and Checker can approve exact immutable module fingerprints while only one complete
Review Record is ever persisted. Fresh reconstruction and expected guards close the cross-command
drift gap without introducing a hidden cache or three intermediate files.

The cost is deliberate ceremony. Every stage repeats the full physical closure, two human-input
files have strict privacy and canonical-byte rules, and every write needs exact prior fingerprints.
That cost keeps a convenient local writer from becoming an implicit discovery, identity, Provider
or authorization service.
